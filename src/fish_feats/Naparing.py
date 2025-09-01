import napari
import numpy as np
from qtpy.QtWidgets import QWidget, QVBoxLayout
import fish_feats.MainImage as mi
import fish_feats.Configuration as cf
import fish_feats.Utils as ut
from fish_feats.NapaRNA import NapaRNA, OverlapRNA
from fish_feats.NapaCells import MainCells, Position3D, EndCells 
from fish_feats.NapaNuclei import MeasureNuclei, NucleiWidget, PreprocessNuclei 
from fish_feats.FishGrid import FishGrid
from fish_feats.NapaMix import CheckScale, CropImage, Association, Separation, CytoplasmMeasure
from fish_feats import ClassifyCells as cc
import fish_feats.FishWidgets as fwid

"""
    Handle the UI through napari plugin

    Fish&Feats proposes several actions from cell/nuclei segmentation, association, mRNA-Fish segmentation/association and quantitative measurements.

    Available under BSD License
    If you use the code or part of it, please cite associated work.

    Author: Gaëlle Letort, DSCB, Institut Pasteur/CNRS
"""

def show_documentation():
    """ Open the documentation page """
    ut.show_documentation_page("")
    return

## start without viewer for tests
def initZen():
    """ Initialize the plugin with the current viewer """
    ffeats = FishFeats()
    ffeats.init_viewer()

def startZen():
    """ Start the pipeline: open the image, get the scaling infos """
    ffeats = FishFeats()
    ffeats.init_viewer()
    return ffeats.open()

def startFromLayers():
    """ Starts the plugin on already opened image """
    ffeats = FishFeats()
    ffeats.init_viewer()
    if ffeats.viewer is None:
        ut.show_error("No viewer found")
        return
    return ffeats.openFromLayers()

def startMultiscale():
    """ Starts with multiscale view """
    ffeats = FishFeats()
    ffeats.init_viewer()
    return ffeats.startMultiscale()
    
def convert_previous_results():
    """ Convert the previous results to the new format """
    filename = ut.dialog_filename()
    if filename is None:
        print("No file selected")
        return
    ffeats = FishFeats()
    return ffeats.convert_previous_results( filename )
    

def unremove(layer):
    ut.show_info("Removing layer locked, throw an error ")
    #print(str(error))
    return

class FishFeats:
    """ Handle main interface of fishfeats """

    def __init__( self, viewer=None ):
        self.viewer = viewer
        self.cfg = None
        self.mig = None
        self.main_wid = None

        if self.viewer is None:
            self.viewer = napari.current_viewer()
            self.viewer.title = "Fish&Feats"


    #### Start
    def init_viewer( self ):
        """ Launch the plugin, initialize all """
        self.mig = mi.MainImage( talkative=True )
        self.my_cmap = ut.create_labelmap()
        self.persp = 45
        self.viewer.scale_bar.visible = True

        @self.viewer.bind_key('h', overwrite=True)
        def show_help(layer):
            ut.showHideOverlayText(self.viewer)

        @self.viewer.bind_key('F1', overwrite=True)
        def show_layer(viewer):
            self.show_hide( 0 )

        @self.viewer.bind_key('F2', overwrite=True)
        def show_layer(viewer):
            self.show_hide( 1 )

        @self.viewer.bind_key('F3', overwrite=True)
        def show_layer(viewer):
            self.show_hide( 2 )

        @self.viewer.bind_key('F4', overwrite=True)
        def show_layer(viewer):
            self.show_hide( 3 )

        @self.viewer.bind_key('F5', overwrite=True)
        def show_layer(viewer):
            self.show_hide( 4 )

        @self.viewer.bind_key('F6', overwrite=True)
        def show_layer(viewer):
            self.show_hide( 5 )

        @self.viewer.bind_key('F7', overwrite=True)
        def show_layer(viewer):
            self.show_hide( 6 )

        @self.viewer.bind_key('F8', overwrite=True)
        def show_layer(viewer):
            self.show_hide( 7 )

        def show_hide( self, intlayer ):
            """ Show/hide the ith-layer """
            if 0 <= intlayer < len( self.viewer.layers ):
                self.viewer.layers[intlayer].visible = not self.viewer.layers[intlayer].visible

        @self.viewer.bind_key('Ctrl-h', overwrite=True)
        def show_shortcuts(layer):
            ut.main_shortcuts(self.viewer)

        @self.viewer.bind_key('g', overwrite=True)
        def show_grid(layer):
            self.addGrid()

        @self.viewer.bind_key('Ctrl-v', overwrite=True)
        def set_vispymode(viewer):
            pers = self.viewer.camera.perspective
            if pers > 0:
                self.persp = pers
                self.viewer.camera.perspective = 0
            else:
                self.viewer.camera.perspective = self.persp

    def open( self ):
        """ Start the pipeline: open the image, get the scaling infos """

        ## get and open the image
        filename = ut.dialog_filename()
        if filename is None:
            print("No file selected")
            return
        ut.showOverlayText(self.viewer,  "Opening image...")
        self.mig.open_image( filename=filename )
        ut.update_history(self.mig.imagedir)
        self.cfg = cf.Configuration( self.mig.save_filename(), show=False )

        ## display the different channels
        self.display_channels()
        self.endInit()
        return self.main_wid

    def openFromLayers( self ):
        """ Open from already opened layers in napari """
        ut.show_info("Loading all opened layers as channels of one image in FishFeats...")
        self.mig = mi.MainImage(talkative=True)
        if len(self.viewer.layers) == 0:
            ut.show_error("No layer(s) found")
            return None
        scale = self.viewer.layers[0].scale
        imshape = self.viewer.layers[0].data.shape
        self.mig.set_scales(scale[0], scale[1])

        ## single layer with all the channels
        if len(self.viewer.layers[0].data.shape) == 4:
            img = self.viewer.layers[0].data
            img = ut.arrange_dims( img, verbose=True )
            self.mig.set_image( img )
            ut.remove_all_layers( self.viewer )
            self.display_channels()
            return self.getImagePath()
        
        ## Or load all opened layer in the image and rename them in FishFeats style
        img = [] 
        for lay in self.viewer.layers:
            if len(lay.data.shape) == 3:
                if lay.data.shape != imshape:
                    ut.show_error("All layers should have the same shape")
                    return
                img.append( lay.data )
        self.mig.set_image(img)
        ut.remove_all_layers( self.viewer )
        self.display_channels()
        return self.getImagePath()

    def convert_previous_results(self, filename):
        """ Convert the previous results to the new format """
        self.mig = mi.MainImage( talkative=True )
        self.mig.set_imagename( filename )
    
        ## read the config file to extract the scaling and the direction
        self.cfg = cf.Configuration(self.mig.save_filename(), show=False)
        if self.cfg.has_config():
            self.cfg.read_scale(self.mig)

        ## load cell file
        results_filename = self.mig.get_filename( endname = "_results.csv", ifexist=True )
        if results_filename != "":
            self.mig.load_from_results( results_filename )
        else:
            loadfilename = self.mig.junction_filename(dim=2,ifexist=True)
            if loadfilename != "":
                print("Load junctions from file "+loadfilename)
                self.mig.loadCellsFromSegmentation( loadfilename )

            nucleifilename = self.mig.nuclei_filename(ifexist=True)
            if nucleifilename != "":
                print("Load nuclei from file "+str(nucleifilename))
                self.mig.load_segmentation_nuclei(nucleifilename, load_stain=False)
                self.mig.popNucleiFromMask()

        ## Load the RNA files if found some
        for chan in range(30):
            ## image was not read so todn't know how many channels are possible
            ## if find RNA file, load it
            rnafile = self.mig.rna_filename(chan=chan, how=".csv", ifexist=True)
            if rnafile == "":
                rnafile = self.mig.rna_filename(chan=chan, how=".tif", ifexist=True)
            if rnafile != "":
                self.mig.load_rnafile(rnafile, chan, topop=True)

        ## Load cytoplasmic results file if found some
        cytofile = self.mig.get_filename(endname="_cytoplasmic.csv", ifexist=True)
        if cytofile != "":
            self.mig.loadCytoplasmicTable( cytofile )
    
        ## Load features files if found some
        featfile = self.mig.get_filename(endname="_features.csv", ifexist=True)
        if featfile != "":
            self.mig.loadFeatureTable( featfile )

        ## Save the new results file
        self.mig.save_results()
        return QWidget() 

    def display_channels(self):
        """ Display the different channels of the image """
        if self.viewer is None or self.mig is None:
            return
        cmaps = ut.colormaps()
        ncmaps = len(cmaps)
        for channel in range(self.mig.nbchannels):
            cmap = cmaps[(channel%ncmaps)]
            img = self.mig.get_channel(channel)
            self.viewer.add_image( img, name="originalChannel"+str(channel), blending="additive", scale=(self.mig.scaleZ, self.mig.scaleXY, self.mig.scaleXY), colormap=cmap, contrast_limits=ut.quantiles(img), gamma=0.9 )
        self.viewer.axes.visible = True

    def endInit(self):
        """ Finish, go to metadata step """
        self.viewer.grid.enabled = True
        ut.removeOverlayText(self.viewer)
        self.checkScale()
        return self.main_wid

    def shortcuts_window(self):
        """ Open a separate text window with the main steps and shortcuts """
        vie = napari.current_viewer()
        ut.main_shortcuts(vie)


    def getImagePath(self):
        """ Get the image path when it was open from layers """

        image_path = fwid.file_dialog( "Select image path", "All files (*)", directory=self.mig.get_image_path() )

        self.mig.set_image_path(image_path)
        ut.update_history(self.mig.imagedir)
        if self.cfg is None:
            self.cfg = cf.Configuration(self.mig.save_filename(), show=False)
        self.endInit()
        return self.main_wid


    ### Grid tools: regular grid for spatial repere
    def addGrid(self):
        """ Interface to create/load a grid for repere """
        if "FishGrid" not in self.viewer.layers:
            grid = FishGrid(self.viewer, self.mig)
            self.viewer.window.add_dock_widget(grid, name="FishGrid")
        else:
            gridlay = self.viewer.layers["FishGrid"]
            gridlay.visible = not gridlay.visible


    def startMultiscale(self):
        """ Open the main image as multiscale for performance """
        filename = ut.dialog_filename()
        if filename is None:
            ut.show_error("No file selected, try again")
            return
        ut.showOverlayText(self.viewer,  "Opening image...")
        self.mig.open_image( filename=filename )
        ut.update_history(self.mig.imagedir)
        self.cfg = cf.Configuration(self.mig.save_filename(), show=False)
    
        for channel in range(self.mig.nbchannels):
            cmap = ut.colormapname(channel)
            img = self.mig.get_channel(channel)
            cview = self.viewer.add_image( [img, img[:,::2,::2], img[:,::4,::4] ], name="originalChannel"+str(channel), blending="additive", scale=(self.mig.scaleZ, self.mig.scaleXY, self.mig.scaleXY), colormap=cmap )
            cview.contrast_limits=ut.quantiles(img)
            cview.gamma=0.95
        self.viewer.axes.visible = True
        self.endInit()
        return self.main_wid

    def byebye( self ):
        """ Quit the pipeline """
        ut.remove_all_layers( self.viewer )
        self.viewer.title = "napari"
        ut.removeOverlayText( self.viewer )
        if self.cfg.blabla.shown():
            self.cfg.blabla.close()
        self.cfg.write_parameterfile()
        #ut.remove_widget( viewer, "Main" )
        print("Bye bye")
        #del mig
        self.main_wid.close()
        #ut.remove_all_widget( self.viewer ) 
        del self.mig
        del self.cfg

    def checkScale(self):
        """ Interface to choose the image scales and channels """
        cs = CheckScale(self)
        wid = self.viewer.window.add_dock_widget(cs, name="Scale")
        self.cfg = cs.cfg
        self.main_wid = wid

    #### Action choice
    def getChoices( self, default_action='Get cells'):
        """ Launch the interface of Main step """
        choice_wid = GetChoices( default_action, self.action_launcher )
        ut.remove_widget( self.viewer, "Main" )
        wid = self.viewer.window.add_dock_widget(choice_wid, name="Main")
        self.main_wid = wid

    def action_launcher( self, action ):
        """ Launch the specified action """
        self.cfg.addSectionText(action)
        if action == "Get cells":
            self.goJunctions()
        elif action == "Load cells from default file":
            self.loadJunctionsFile()
        elif action == "Get nuclei":
            self.getNuclei()
        elif action == "Get RNA":
            self.getRNA()
        elif action == "Get overlapping RNAs":
            self.getOverlapRNA()
        elif action == "Associate junctions and nuclei":
            self.doCellAssociation()
        elif action == "Quit plugin":
            self.byebye()
        elif action == "Image scalings":
            self.checkScale()
        elif action == "Separate junctions and nuclei":
            self.divorceJunctionsNuclei()
        elif action == "Preprocess nuclei":
            self.preprocNuclei()
        elif action == "Measure nuclear intensity":
            self.measureNuclearIntensity()
        elif action == "Measure cytoplasmic staining":
            self.cytoplasmicStaining()
        elif action == "Crop image":
            self.crop_image()
        elif action == "test":
            test()
        elif action == "Classify cells":
            if not self.mig.hasCells():
                ut.show_info("No cells - segment/load it before")
            else:
                cc.classify_cells(self.mig, self.viewer)
        elif action == "Touching labels":
            self.touching_labels()
        elif action == "3D cell positions":
            self.show3DCells()
        elif action == "Add grid":
            self.addGrid()

    def crop_image(self):
        """ Interface to crop the image and associated segmentations/results """
        crop = CropImage(self)
        self.viewer.window.add_dock_widget( crop, name="CropImage" )

    def load_all_previous_files(self):
        """ Load all the previous files with default name that it can find and init the objects accordingly """
        ## try to load separated staining
        if self.mig.should_separate():
            separated_junctionsfile = self.mig.separated_junctions_filename(ifexist=True)
            separated_nucleifile = self.mig.separated_nuclei_filename(ifexist=True)
            if (separated_junctionsfile != "") and (separated_nucleifile != ""):
                self.load_separated( separated_junctionsfile, separated_nucleifile )
    
        loadfilename = self.mig.junction_filename(dim=2,ifexist=True)
        if loadfilename != "":
            self.cfg.addText("Load junctions from file "+loadfilename)
            self.mig.load_segmentation( loadfilename )
            self.mig.popFromJunctions()

        nucleifilename = self.mig.nuclei_filename(ifexist=True)
        if nucleifilename != "":
            self.cfg.addText("Load nuclei from file "+str(nucleifilename))
            self.mig.load_segmentation_nuclei(nucleifilename)
            self.mig.popNucleiFromMask()

        for chan in self.mig.potential_rnas():
            ## if find RNA file, load it
            rnafile = self.mig.rna_filename(chan=chan, how=".csv", ifexist=True)
            if rnafile == "":
                rnafile = self.mig.rna_filename(chan=chan, how=".tif", ifexist=True)
            if rnafile != "":
                self.mig.load_rnafile(rnafile, chan, topop=True)

        ut.remove_all_widget( self.viewer )
        self.getChoices(default_action="Classify cells")

    def load_separated( self, juncfile, nucfile ):
        """ load the separated files """
        self.mig.load_separated_staining( juncfile, nucfile )
        ut.show_info("Separated stainings loaded")

    def loadJunctionsFile(self):
        """ Load the segmentation from given file and directly init the cells """
        loadfilename = self.mig.junction_filename(dim=2,ifexist=True)
        self.cfg.addText("Load junctions from file "+loadfilename)
        self.mig.load_segmentation( loadfilename )
        self.mig.popFromJunctions()
        ut.remove_all_widget( self.viewer )
        self.getChoices(default_action="Get nuclei")

    def goJunctions(self):
        """ Choose between loading projection and cells files or recalculating """
        if self.mig.junchan is None:
            ut.show_warning( "No junction channel selected in the configuration. Go back to Image Scalings to select one." )
            return

        main_cells = MainCells( self ) 
        if main_cells.proj is not None:
            self.viewer.window.add_dock_widget( main_cells.proj, name="JunctionProjection2D" )
        else:
            self.viewer.window.add_dock_widget( main_cells, name="Get cells" )


    ################################
    ###### Show cell in 3D and possibility to edit the Z position of cells
    def show3DCells(self):
        """ Cells in 3D and update Z position of cells """
        cells_3D = Position3D( self )
        self.viewer.window.add_dock_widget(cells_3D, name="Cells in 3D")

    ##### preprocessing functions
    def preprocNuclei(self):
        """ Preprocess the nuclei before segmentation """
        preproc_nuclei = PreprocessNuclei( self.viewer, self.mig, self.cfg )
        self.viewer.window.add_dock_widget(preproc_nuclei, name="Preprocess Nuclei")

    ################### Junction and nuclei separation functions

    def divorceJunctionsNuclei(self):
        """ Separate the junctions and nuclei staining if they are in the same channel """
        separation = Separation( self ) 
        self.viewer.window.add_dock_widget(separation, name="Separate")

    ################ Nuclei segmentation
    def getNuclei(self):
        """ 3D segmentation and correction of nuclei """
        print("******* 3D segmentation of nuclei ******")
        text = "Choose method and parameters to segment nuclei in 3D \n"
        text += "The nuclei are segmented from the original nuclei channel if the stainings are separate \n"
        text += "Or from the nucleiStaining image if the staining were originally mixed \n"
        ut.showOverlayText(self.viewer, text)

        ut.hide_color_layers(self.viewer, self.mig)
        ut.show_layer(self.viewer, self.mig.nucchan)
        
        nuclei_widget = NucleiWidget( self )
        self.viewer.window.add_dock_widget( nuclei_widget, name="Get nuclei" )

    ######################### Association of 2D cells with nuclei
    def doCellAssociation(self):
        """ Association of nuclei with corresponding apical junction cells """
        do_association = Association( self.viewer, self.mig, self.cfg )
        self.viewer.window.add_dock_widget(do_association, name="Associating")

    ######################### RNA
    def getOverlapRNA(self):
        """ Find RNAs overlapping in several channels (non specific signal) """
        over = OverlapRNA(self.viewer, self.mig, self.cfg)
        self.viewer.window.add_dock_widget( over, name="Overlapping RNAs" )

    def getRNA(self):
        """ Segment the RNA dots in selected channels """
        if not ut.has_widget( self.viewer, "RNAs"):
            rnaGUI = NapaRNA(self.viewer, self.mig, self.cfg)


    ######## Labels edition
    def showCellsWidget(self, layerName, shapeName='CellNames', dim=3):
        """ option to show and edit cell segmentation """
        layer = self.viewer.layers[layerName]
        
        @layer.bind_key('Control-c', overwrite=True)
        def contour_increase(layer):
            if layer is not None:
                layer.contour = layer.contour + 1
        
        @layer.bind_key('Control-d', overwrite=True)
        def contour_decrease(layer):
            if layer is not None:
                if layer.contour > 0:
                    layer.contour = layer.contour - 1
        
    
        @layer.mouse_drag_callbacks.append
        def clicks_label(layer, event):
            if event.type == "mouse_press":
                if len(event.modifiers) == 0:
                    if event.button == 2:
                        label = layer.get_value(position=event.position, view_direction = event.view_direction, dims_displayed=event.dims_displayed, world=True)
                        layer.selected_label = label
                        layer.refresh()
                    return
        
                if 'Control' in event.modifiers:
                    if event.button == 2:
                        ### Erase a label
                        label = layer.get_value(position=event.position, view_direction = event.view_direction, dims_displayed=event.dims_displayed, world=True)
                        layer.data[layer.data==label] = 0
                        layer.refresh()
                        return

                    if event.button == 1:
                        ## Merge two labels
                        start_label = layer.get_value(position=event.position, view_direction = event.view_direction, dims_displayed=event.dims_displayed, world=True)
                        yield
                        while event.type == 'mouse_move':
                            yield
                        end_label = layer.get_value(position=event.position, view_direction = event.view_direction, dims_displayed=event.dims_displayed, world=True)
                        # Control left-click: merge labels at each end of the click
                        print("Merge label "+str(start_label)+" with "+str(end_label))
                        frame = None
                        if layer.ndim == 3:
                            frame = int(self.viewer.dims.current_step[0])
                        ut.merge_labels( layer, frame, start_label, end_label )
    

        @layer.bind_key('m', overwrite=True)
        def set_maxlabel(layer):
            mess = "Max label on image "+shapeName+": "+str(np.max(layer.data)) 
            mess += "\n "
            mess += "Number of labels used: "+str(len(np.unique(layer.data)))
            ut.show_info( mess )
            layer.mode = "PAINT"
            layer.selected_label = np.max(layer.data)+1
            if layer.selected_label == 1:
                layer.selected_label = 2
            layer.refresh()
            return

        @layer.bind_key('l', overwrite=True)
        def switch_show_lab(layer):
            if shapeName in self.viewer.layers:
                self.viewer.layers.remove(shapeName)
            else:
                ut.get_bblayer(layer, shapeName, dim, self.viewer, self.mig)
            return
    
        def relabel_layer():
            maxlab = np.max(layer.data)
            used = np.unique(layer.data)
            nlabs = len(used)
            if nlabs == maxlab:
                print("already relabelled")
                return
            for j in range(2, nlabs+1):
                if j not in used:
                    layer.data[layer.data==maxlab] = j
                    maxlab = np.max(layer.data)
            layer.refresh()

        def show_names():
            if shapeName in self.viewer.layers:
                self.viewer.layers.remove(shapeName)

        help_text = ut.labels_shortcuts( level = 0 )
        header = ut.helpHeader(self.viewer, layerName)
        ut.showOverlayText(self.viewer, header+help_text)
    
        print( "\n #########################################\n Labels correction options:\n " + help_text + self.textCellsWidget() )

        if "Junctions" in self.viewer.layers:
            self.viewer.layers["Junctions"].preserve_labels = True

    def textCellsWidget(self):
        text = "  <Control+left click> from one label to another to merge them (the label kept will be the last one) \n"
        text += "'show_cellnames' (<l>) add a new layer showing the label (number) around each object position. \n"
        #text += "'relabel update' the cell labels to have consecutives numbers from 2 to number_of_cells.\n"
        text += "\n For 3D: \n"
        text += "In 3D, most label actions wont work if Vispy perspective is ON. Switch it off with 'Ctrl-v' before.\n"
        text += "If n_edit_dim is set on 3 (top left panel), edition will affect all or several z (slices) \n"
        text += "If n_edit_dim is set on 2, edition will only affect the active slice \n"
        return text
    
    def correction_junctions( self ):
        """ Manual correction of segmentation step """
        ut.removeOverlayText( self.viewer )
        maskview = self.viewer.add_labels( self.mig.junmask, blending='additive', scale=(self.mig.scaleXY, self.mig.scaleXY), name="Junctions" )
        maskview.contour = 3
        maskview.selected_label = 2
        self.showCellsWidget( "Junctions", shapeName="JunctionsName", dim=2 )
        #ut.remove_widget( self.viewer, "Get cells" )
        # saving and finishing
        endcells = EndCells( self )
        self.viewer.window.add_dock_widget( endcells, name="EndCells" )


    def measureNuclearIntensity(self):
        """ Measure intensity inside segmented nuclei """
        if not self.mig.hasNuclei():
            ut.show_warning( "Segment/Load nuclei before" )
            return
        meas_nuc = MeasureNuclei( self.viewer, self.mig, self.cfg )
        self.viewer.window.add_dock_widget(meas_nuc, name="Measure nuclei")

    ############ measure cyto
    def cytoplasmicStaining(self):
        """ Measure the cytoplasmic signal close to the apical surface """
        cytoMeas = CytoplasmMeasure( self.viewer, self.mig, self.cfg )
        self.viewer.window.add_dock_widget(cytoMeas, name="Measure cytos")

    def helpMessageEditContours(self, dim=2):
        text = '- To see the cells as filled area, put 0 in the *contour* field. Else to see the contours, in *contour* field, put 1 or more (will be thicker if >1) \n'
        text = text + '- To erase one label entirely, put *0* in the *label* field, select the *fill* tool and click on the label \n'
        text = text + '- To add one label, choose a label value higher than all the ones in the image,'
        text = text + ' put it in the *label* field, select the *drawing* tool and draw it.'
        text = text + ' Fill the contour you have drawn to finish the new cell \n'
        text = text + '- To draw, choose the label value in the *label* field, and click and drag to paint.'
        text += ' If *preserve labels* is selected, drawing above another label doesn t affect it \n'
        text += '- Holding space to zoom/unzoom \n'
        #text += 'You can set the selected label to be one larger than the current largest label by pressing M.\n'
        if dim == 3:
            text += '- Check n_edit_dimensions box to modify all 3D nuclei at once (else work only on the current slice) \n'
        return text

############################## Extra-tools

    ### Touching labels for Griottes
    def touching_labels(self):
        """ Dilate labels so that they all touch """
        ## perform the label expansion
        from skimage.morphology import binary_opening
        from skimage.segmentation import expand_labels
        print("********** Generate touching labels image ***********")
    
        ## get junctions img
        if "Cells" not in self.viewer.layers:
            if self.mig.pop is None or self.mig.pop.imgcell is None:
                ut.show_info("Load segmentation before!")
                return
            labimg = self.viewer.add_labels(self.mig.pop.imgcell, name="Cells", scale=(self.mig.scaleXY, self.mig.scaleXY), opacity=1, blending="additive")
            labimg.contour = 0

        ## skeletonize it
        img = self.viewer.layers["Cells"].data
        ext = np.zeros(img.shape, dtype="uint8")
        ext[img==0] = 1
        ext = binary_opening(ext, footprint=np.ones((2,2)))
        newimg = expand_labels(img, distance=4)
        newimg[ext>0] = 0
        newlay = self.viewer.add_labels(newimg, name="TouchingCells", scale=(self.mig.scaleXY, self.mig.scaleXY), opacity=1, blending="additive")
        newlay.contour = 0

        ## open the widget for options
        tlabel_wid = TouchingLabels( self.viewer, self.mig, self.cfg )
        self.viewer.window.add_dock_widget(tlabel_wid, name="Touching labels")

class TouchingLabels( QWidget):
    """ Generate an image with touching labels from the junctions image, handle compability with Griottes """
    def __init__(self, viewer, mig, cfg):
        super().__init__()
        self.viewer = viewer
        self.mig = mig
        self.cfg = cfg

        layout = QVBoxLayout()
        ## save the image
        save_btn = fwid.add_button( "Save touching labels image", self.save_touching_labels_image, descr="Save the resulting image of expanded cell labels", color=ut.get_color("save") )  
        layout.addWidget( save_btn )
        
        ## if Griottes has run, adapt it to the scale
        scale_btn = fwid.add_button( "Scale Griottes image", self.scale_griottes, descr="Scale the images resulting from Griottes computing to the main image scale" )  
        layout.addWidget( scale_btn )
        self.setLayout(layout)
    
    def save_touching_labels_image( self ):
        """ Save the touching labels image """
        if "TouchingCells" not in self.viewer.layers:
            ut.show_error("No touching labels image to save")
            return
        outname = self.mig.build_filename( "_touching_labels.tif")
        self.mig.save_image(self.viewer.layers["TouchingCells"].data, imagename=outname)
        ut.show_info("Saved touching labels image as "+outname)

    def scale_griottes( self ):
        """ Scale the Griottes images to the main image scale """
        ut.scale_layer( self.viewer, "Centers", (self.mig.scaleXY, self.mig.scaleXY) )
        ut.scale_layer( self.viewer, "Contact graph", (self.mig.scaleXY, self.mig.scaleXY) )
        ut.scale_layer( self.viewer, "Graph", (self.mig.scaleXY, self.mig.scaleXY) )


def test():
    print("for test")
    #img = mig.tryDiffusion( nchan=2 )
    #viewer.add_image(img, name="test", scale=(mig.scaleZ, mig.scaleXY, mig.scaleXY), colormap=my_cmap, blending="additive")


class GetChoices( QWidget ):
    """ Main widget with all the action choices """

    def __init__( self, default_action, action_fnc ):
        """ Initialiaze the Main interface with the choice of action to perform """
        super().__init__()
        self.default_action = default_action
        self.action_fnc = action_fnc

        layout = QVBoxLayout()
        ## Choice list
        action_line, self.action = fwid.list_line( "Action: ", descr="Choose which action (step) to perform now", func=None )
        choices = ['Get cells', 'Get nuclei', 'Associate junctions and nuclei', 'Get RNA', 'Get overlapping RNAs', 'Measure cytoplasmic staining', 'Measure nuclear intensity', 'Image scalings', 'Separate junctions and nuclei', 'Preprocess nuclei', '3D cell positions', 'Quit plugin', 'Classify cells', 'Touching labels', 'Add grid', 'Crop image']
        for choice in choices:
            self.action.addItem(choice)
        self.action.setCurrentText( self.default_action )
        layout.addLayout( action_line )
        ## button go
        go_btn = fwid.add_button( "GO", self.launch_action, descr="Launch the selected action", color=ut.get_color("go") )
        layout.addWidget(go_btn)
        self.setLayout(layout)
        self.action.currentTextChanged.connect( self.launch_action )

    def launch_action(self):
        """ Launch next step with selected action """
        action = self.action.currentText()
        self.action_fnc( action )

