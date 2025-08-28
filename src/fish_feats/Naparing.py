import napari
import os, pathlib
import numpy as np
import time
from magicgui import magicgui
from napari.qt import create_worker, thread_worker
from qtpy.QtWidgets import QApplication, QWidget, QVBoxLayout
from skimage.measure import regionprops_table
import fish_feats.MainImage as mi
import fish_feats.Configuration as cf
import fish_feats.Utils as ut
from fish_feats.NapaRNA import NapaRNA
from fish_feats.NapaCells import GetCells, Projection
from fish_feats.NapaNuclei import MeasureNuclei, NucleiWidget 
from fish_feats.FishGrid import FishGrid
from fish_feats.NapaMix import CheckScale, CropImage
from fish_feats import ClassifyCells as cc
import fish_feats.FishWidgets as fwid

"""
    Handle the UI through napari plugin

    Fish&Feats proposes several actions from cell/nuclei segmentation, association, mRNA-Fish segmentation/association and quantitative measurements.

    Available under BSD License
    If you use the code or part of it, please cite associated work.

    Author: Gaëlle Letort, DSCB, Institut Pasteur/CNRS
"""

## start without viewer for tests
def initZen():
    """ Initialize the plugin with the current viewer """
    global viewer, cfg
    cfg = None
    viewer = napari.current_viewer()
    viewer.title = "Fish&Feats"
    init_viewer( viewer )

#### Start
def init_viewer( viewer ):
    """ Launch the plugin, initialize all """

    global mig, my_cmap, persp  
    mig = mi.MainImage( talkative=True )
    my_cmap = ut.create_labelmap()
    persp = 45
    viewer.scale_bar.visible = True
    
    @viewer.bind_key('h', overwrite=True)
    def show_help(layer):
        ut.showHideOverlayText(viewer)
        
    @viewer.bind_key('F1', overwrite=True)
    def show_layer(viewer):
        show_hide( 0 )
        
    @viewer.bind_key('F2', overwrite=True)
    def show_layer(viewer):
        show_hide( 1 )
        
    @viewer.bind_key('F3', overwrite=True)
    def show_layer(viewer):
        show_hide( 2 )
        
    @viewer.bind_key('F4', overwrite=True)
    def show_layer(viewer):
        show_hide( 3 )
        
    @viewer.bind_key('F5', overwrite=True)
    def show_layer(viewer):
        show_hide( 4 )
        
    @viewer.bind_key('F6', overwrite=True)
    def show_layer(viewer):
        show_hide( 5 )
    
    @viewer.bind_key('F7', overwrite=True)
    def show_layer(viewer):
        show_hide( 6 )
    
    @viewer.bind_key('F8', overwrite=True)
    def show_layer(viewer):
        show_hide( 7 )
    
    def show_hide( intlayer ):
        """ Show/hide the ith-layer """
        if intlayer < len( viewer.layers ):
            viewer.layers[intlayer].visible = not viewer.layers[intlayer].visible

    @viewer.bind_key('Ctrl-h', overwrite=True)
    def show_shortcuts(layer):
        ut.main_shortcuts(viewer)
    
    @viewer.bind_key('g', overwrite=True)
    def show_grid(layer):
        addGrid()

    @viewer.bind_key('Ctrl-v', overwrite=True)
    def set_vispymode(viewer):
        global persp
        pers = viewer.camera.perspective
        if pers > 0:
            persp = pers
            viewer.camera.perspective = 0
        else:
            viewer.camera.perspective = persp

def startZen():
    """ Start the pipeline: open the image, get the scaling infos """
    global cfg
    initZen()
    
    ## get and open the image
    filename = ut.dialog_filename()
    if filename is None:
        print("No file selected")
        return
    ut.showOverlayText(viewer,  "Opening image...")
    mig.open_image( filename=filename )
    ut.update_history(mig.imagedir)
    cfg = cf.Configuration( mig.save_filename(), show=False )
    
    ## display the different channels
    display_channels()
    return endInit()

def convert_previous_results():
    """ Convert the previous results to the new format """
    global cfg, mig
    filename = ut.dialog_filename()
    if filename is None:
        print("No file selected")
        return
    mig = mi.MainImage( talkative=True )
    mig.set_imagename( filename )
    global cfg
    ## read the config file to extract the scaling and the direction
    cfg = cf.Configuration(mig.save_filename(), show=False)
    if cfg.has_config():
        cfg.read_scale(mig)
    
    ## load cell file
    results_filename = mig.get_filename( endname = "_results.csv", ifexist=True )
    if results_filename != "":
        mig.load_from_results( results_filename )
    else:
        loadfilename = mig.junction_filename(dim=2,ifexist=True)
        if loadfilename != "":
            print("Load junctions from file "+loadfilename)
            mig.loadCellsFromSegmentation( loadfilename )

        nucleifilename = mig.nuclei_filename(ifexist=True)
        if nucleifilename != "":
            print("Load nuclei from file "+str(nucleifilename))
            mig.load_segmentation_nuclei(nucleifilename, load_stain=False)
            mig.popNucleiFromMask()

    ## Load the RNA files if found some
    for chan in range(30):
        ## image was not read so todn't know how many channels are possible
        ## if find RNA file, load it
        rnafile = mig.rna_filename(chan=chan, how=".csv", ifexist=True)
        if rnafile == "":
            rnafile = mig.rna_filename(chan=chan, how=".tif", ifexist=True)
        if rnafile != "":
            mig.load_rnafile(rnafile, chan, topop=True)

    ## Load cytoplasmic results file if found some
    cytofile = mig.get_filename(endname="_cytoplasmic.csv", ifexist=True)
    if cytofile != "":
        mig.loadCytoplasmicTable( cytofile )
    
    ## Load features files if found some
    featfile = mig.get_filename(endname="_features.csv", ifexist=True)
    if featfile != "":
        mig.loadFeatureTable( featfile )

    ## Save the new results file
    mig.save_results()
    return QWidget() 

def display_channels():
    """ Display the different channels of the image """
    global viewer, mig
    if viewer is None or mig is None:
        return
    cmaps = ut.colormaps()
    ncmaps = len(cmaps)
    for channel in range(mig.nbchannels):
        cmap = cmaps[(channel%ncmaps)]
        img = mig.get_channel(channel)
        viewer.add_image( img, name="originalChannel"+str(channel), blending="additive", scale=(mig.scaleZ, mig.scaleXY, mig.scaleXY), colormap=cmap, contrast_limits=ut.quantiles(img), gamma=0.9 )
    viewer.axes.visible = True

def startFromLayers():
    """ Starts the plugin on already opened image """
    global viewer, mig
    initZen()
    if viewer is None:
        ut.show_error("No viewer found")
        return
    ut.show_info("Loading all opened layers as channels of one image in FishFeats...")
    mig = mi.MainImage(talkative=True)
    if len(viewer.layers) == 0:
        ut.show_error("No layer(s) found")
        return None
    scale = viewer.layers[0].scale
    imshape = viewer.layers[0].data.shape
    mig.set_scales(scale[0], scale[1])

    ## single layer with all the channels
    if len(viewer.layers[0].data.shape) == 4:
        img = viewer.layers[0].data
        img = ut.arrange_dims( img, verbose=True )
        mig.set_image( img )
        ut.remove_all_layers( viewer )
        display_channels()
        return getImagePath()
        
    ## Or load all opened layer in the image and rename them in FishFeats style
    img = [] 
    for lay in viewer.layers:
        if len(lay.data.shape) == 3:
            if lay.data.shape != imshape:
                ut.show_error("All layers should have the same shape")
                return
            img.append( lay.data )
    mig.set_image(img)
    ut.remove_all_layers( viewer )
    display_channels()
    return getImagePath()

def startMultiscale():
    """ Open the main image as multiscale for performance """
    global cfg
    initZen()

    filename = ut.dialog_filename()
    if filename is None:
        ut.show_error("No file selected, try again")
        return
    ut.showOverlayText(viewer,  "Opening image...")
    mig.open_image( filename=filename )
    ut.update_history(mig.imagedir)
    cfg = cf.Configuration(mig.save_filename(), show=False)
    
    for channel in range(mig.nbchannels):
        cmap = ut.colormapname(channel)
        img = mig.get_channel(channel)
        cview = viewer.add_image( [img, img[:,::2,::2], img[:,::4,::4] ], name="originalChannel"+str(channel), blending="additive", scale=(mig.scaleZ, mig.scaleXY, mig.scaleXY), colormap=cmap )
        cview.contrast_limits=ut.quantiles(img)
        cview.gamma=0.95
    viewer.axes.visible = True

    return endInit()

def endInit():
    viewer.grid.enabled = True
    ut.removeOverlayText(viewer)
    return checkScale()

def byebye():
    """ Quit the pipeline """
    global mig
    viewer.window.remove_dock_widget("all")
    viewer.title = "napari"
    ut.removeOverlayText(viewer)
    if cfg.blabla.shown():
        cfg.blabla.close()
    cfg.write_parameterfile()
    ut.remove_all_layers( viewer )
    print("Bye bye")
    #del mig

def shortcuts_window():
    """ Open a separate text window with the main steps and shortcuts """
    vie = napari.current_viewer()
    ut.main_shortcuts(vie)

def show_documentation():
    ut.show_documentation_page("")
    return

def getImagePath():
    """ Get the image path when it was open from layers """

    @magicgui(call_button="Set path",)
    def get_image_path( image_path=pathlib.Path(mig.get_image_path())):
        """ Get the image path when it was open from layers """
        global cfg 
        mig.set_image_path(image_path)
        ut.update_history(mig.imagedir)
        if cfg is None:
            cfg = cf.Configuration(mig.save_filename(), show=False)
        ut.remove_widget( viewer, "ImagePath" )
        endInit()

    wid = viewer.window.add_dock_widget( get_image_path, name="ImagePath" )
    return wid

def checkScale():
    """ Interface to choose the image scales and channels """
    global cfg

    cs = CheckScale( viewer, mig, cfg, load_all_previous_files, divorceJunctionsNuclei, getChoices )
    wid = viewer.window.add_dock_widget(cs, name="Scale")
    cfg = cs.cfg
    return wid


#### Action choice
def getChoices(default_action='Get cells'):
    """ Main widget with all the action choices """
    @magicgui(call_button="GO",
        action={"choices": ['Get cells', 'Get nuclei', 'Associate junctions and nuclei', 'Get RNA', 'Get overlapping RNAs', 'Measure cytoplasmic staining', 'Measure nuclear intensity', 'Image scalings', 'Separate junctions and nuclei', 'Preprocess nuclei', '3D cell positions', 'Quit plugin', 'Classify cells', 'Touching labels', 'Add grid', 'Crop image']},
            )
    def get_choices(action=default_action):
        launch_action()

    def launch_action():
        action = get_choices.action.value
        cfg.addSectionText(action)
        if action == "Get cells":
                goJunctions()
        elif action == "Load cells from default file":
                loadJunctionsFile()
        elif action == "Get nuclei":
                getNuclei()
        elif action == "Get RNA":
                getRNA()
        elif action == "Get overlapping RNAs":
                getOverlapRNA()
        elif action == "Associate junctions and nuclei":
                doCellAssociation()
        elif action == "Quit plugin":
                byebye()
        elif action == "Image scalings":
                checkScale()
        elif action == "Separate junctions and nuclei":
                divorceJunctionsNuclei()
        elif action == "Preprocess nuclei":
                preprocNuclei()
        elif action == "Measure nuclear intensity":
                measureNuclearIntensity()
        elif action == "Measure cytoplasmic staining":
                cytoplasmicStaining()
        elif action == "Crop image":
            crop_image()
        elif action == "test":
                test()
        elif action == "Classify cells":
                if not mig.hasCells():
                    ut.show_info("No cells - segment/load it before")
                else:
                    cc.classify_cells(mig, viewer)
        elif action == "Touching labels":
            touching_labels()
        elif action == "3D cell positions":
            show3DCells()
        elif action == "Add grid":
            addGrid()

    ut.remove_widget( viewer, "Main" )
    viewer.window.add_dock_widget(get_choices, name="Main")
    get_choices.action.changed.connect(launch_action)

def crop_image():
    """ Interface to crop the image and associated segmentations/results """
    crop = CropImage( viewer, mig, cfg )
    viewer.window.add_dock_widget( crop, name="CropImage" )


def load_all_previous_files():
    """ Load all the previous files with default name that it can find and init the objects accordingly """
    ## try to load separated staining
    if mig.should_separate():
        separated_junctionsfile = mig.separated_junctions_filename(ifexist=True)
        separated_nucleifile = mig.separated_nuclei_filename(ifexist=True)
        if (separated_junctionsfile != "") and (separated_nucleifile != ""):
            load_separated( separated_junctionsfile, separated_nucleifile, end_dis=False )
    
    loadfilename = mig.junction_filename(dim=2,ifexist=True)
    if loadfilename != "":
        cfg.addText("Load junctions from file "+loadfilename)
        mig.load_segmentation( loadfilename )
        mig.popFromJunctions()

    nucleifilename = mig.nuclei_filename(ifexist=True)
    if nucleifilename != "":
        cfg.addText("Load nuclei from file "+str(nucleifilename))
        mig.load_segmentation_nuclei(nucleifilename)
        mig.popNucleiFromMask()

    for chan in mig.potential_rnas():
        ## if find RNA file, load it
        rnafile = mig.rna_filename(chan=chan, how=".csv", ifexist=True)
        if rnafile == "":
            rnafile = mig.rna_filename(chan=chan, how=".tif", ifexist=True)
        if rnafile != "":
            mig.load_rnafile(rnafile, chan, topop=True)

    viewer.window.remove_dock_widget("all")
    getChoices(default_action="Classify cells")

def loadJunctionsFile():
    """ Load the segmentation from given file and directly init the cells """
    loadfilename = mig.junction_filename(dim=2,ifexist=True)
    cfg.addText("Load junctions from file "+loadfilename)
    mig.load_segmentation( loadfilename )
    mig.popFromJunctions()
    viewer.window.remove_dock_widget("all")
    getChoices(default_action="Get nuclei")

def goJunctions():
    """ Choose between loading projection and cells files or recalculating """
    if mig.junchan is None:
        ut.show_warning( "No junction channel selected in the configuration. Go back to Image Scalings to select one." )
        return
    methods = ["Do projection and segmentation"]
    ind = 0
    projname = mig.build_filename( "_junction_projection.tif")
    cellsname = mig.build_filename( "_cells2D.tif")
    msg = ""
    if os.path.exists( projname ):
        msg = "Found projection file"
    if os.path.exists( cellsname ):
        methods.append( "Load previous files" )
        ind = 1
        msg += "\nFound cell file"
        msg += "\nChoose load to use those file(s)"
    
    @magicgui( call_button="Get cells",
        _ = {"widget_type": "Label"},
        action={"choices": methods},
        )
    def get_cells( 
        _ = msg,
        action = methods[ind] 
        ):
        """ choose method to use to get/load cells """
        if action == "Load previous files":
            ## load and show the projection
            if os.path.exists( projname ):
                ut.remove_layer(viewer, "2DJunctions")
                roijunc = mig.load_image( projname )
                viewer.add_image( roijunc, name="2DJunctions", scale=(mig.scaleXY, mig.scaleXY), blending="additive" )
            ## load the cells and edit them
            mig.load_segmentation( cellsname )
            ut.remove_widget( viewer, "Get cells" )
            get_cells = GetCells( viewer, mig, cfg, showCellsWidget, getChoices )
            get_cells.end_segmentation()

        if action == "Do projection and segmentation":
            ut.remove_widget( viewer, "Get cells" )
            proj = Projection( viewer, mig, cfg, divorceJunctionsNuclei, showCellsWidget, getChoices )
            viewer.window.add_dock_widget( proj, name="JunctionProjection2D" )
    
    viewer.window.add_dock_widget(get_cells, name="Get cells")


#######################################################################
###### Show cell in 3D and possibility to edit the Z position of cells
def show3DCells():
    """ Cells in 3D and update Z position of cells """
    print("******** Cells Z position viewing/editing ******")
    header = ut.helpHeader(viewer, "CellContours")
    help_text = ut.help_shortcut("pos3d")
    ut.showOverlayText(viewer, header+help_text)
    paras = cfg.read_parameter_set("ZCells")
    zmapres = 200
    zmaplocsize = 300

    if paras is not None:
        if "zmap_resolution" in paras:
            zmapres = int(paras["zmap_resolution"])
        if "zmap_localsize" in paras:
            zmaplocsize = int(paras["zmap_localsize"])
    
    def drawCells3D():
        """ Draw the cells in 3D """
        ready = mig.cellsHaveZPos()
        if not ready:
            ## more than half the cells don't have Z position, so recompute it
            ut.show_info("Many cells don't have Z position yet, computing it")
            mig.updateCellsZPos( step_size=zmapres, window_size=zmaplocsize, save=False )
        cells3D = mig.getJunctionsImage3D()
        ut.remove_layer(viewer, "CellContours")
        layer = viewer.add_labels( cells3D, name="CellContours", blending="additive", scale=(mig.scaleZ, mig.scaleXY, mig.scaleXY) )
        
        @layer.mouse_drag_callbacks.append
        def clicks_label(layer, event):
            if event.type == "mouse_press":
                if len(event.modifiers) == 0:
                    if event.button == 2:
                        # right-click, select the label value
                        label = layer.get_value(position=event.position, view_direction = event.view_direction, dims_displayed=event.dims_displayed, world=True)
                        if label > 0:
                            cells_3D.cell_label.value = label
                    return
                if "Control" in event.modifiers:
                    if event.button == 1:
                        ## Control left-click, set the z position
                        zpos = viewer.dims.current_step[0]
                        cells_3D.place_at_z.value = zpos
                        update_cell_zpos()
                        return

    def update_cell_zpos():
        """ Update current cell to current z position """
        cell = int(cells_3D.cell_label.value)
        zpos = int(cells_3D.place_at_z.value)
        if (zpos >= 0) and (zpos < mig.get_image_shape(in2d=False)[0]):
            img = viewer.layers["CellContours"].data
            mig.updateCellZPos(cell, zpos, img)
            #viewer.layers["CellContours"].data = img
            viewer.layers["CellContours"].refresh()
            cells_3D.cell_label.value = 0

    def calculate_zmap():
        """ recalculate the zmap and update cells positions """
        step_size = int(cells_3D.zmap_resolution.value)
        window_size = int(cells_3D.zmap_localsize.value)
        mig.updateCellsZPos( step_size=step_size, window_size=window_size, save=cells_3D.save_zmap.value )
        drawCells3D()
        ut.show_info("Cell Z positions updated")


    @magicgui(call_button="Save updated cells", 
            _ = {"widget_type": "Label"},
            zmap_resolution = {"widget_type": "LiteralEvalLineEdit"},
            zmap_localsize = {"widget_type": "LiteralEvalLineEdit"},
            save_zmap = { "widget_type":"CheckBox", "value": False, "name": "save_zmap"}, 
            recalculate_zmap = {"widget_type":"PushButton", "value": False, "name": "recalculate_zmap"}, 
            __={"widget_type":"EmptyWidget", "value": False},
            ___ = {"widget_type": "Label"},
            cell_label = {"widget_type": "LiteralEvalLineEdit"},
            place_at_z = {"widget_type": "LiteralEvalLineEdit"},
            update_cell = {"widget_type":"PushButton", "value": False, "name": "update_cell"}, 
            ____={"widget_type":"EmptyWidget", "value": False},
            )
    def cells_3D( _ = "Map of cell Z positions",
                  zmap_resolution = zmapres,
                  zmap_localsize = zmaplocsize,
                  save_zmap = False,
                  recalculate_zmap = False,
                  __=False,
                  ___ = "Edit cell Z position",
                  cell_label = 0,
                  place_at_z = 0,
                  update_cell = False,
                  ____ = False,
                ):
        #filename = mig.zcell_filename(ifexist=False)
        #mig.save_zcells(filename)
        mig.save_results()
        ut.remove_widget(viewer, "Cells in 3D")
        ut.remove_layer(viewer, "CellContours")
        cfg.addGroupParameter("ZCells")
        cfg.addParameter("ZCells", "zmap_resolution", zmap_resolution)
        cfg.addParameter("ZCells", "zmap_localsize", zmap_localsize)
        cfg.write_parameterfile()
        ut.removeOverlayText(viewer)

    drawCells3D()
    cells_3D.recalculate_zmap.clicked.connect(calculate_zmap)
    cells_3D.update_cell.clicked.connect(update_cell_zpos)
    viewer.window.add_dock_widget(cells_3D, name="Cells in 3D")


#######################################################################
##### preprocessing functions

def preprocJunctions2D(imgjun):
    """ Preprocessing the projection (filters, denoising)"""

    saveimg = np.copy(imgjun)
    if "2DJunctions" not in viewer.layers:
        viewer.add_image( imgjun, name="2DJunctions", blending="additive", scale=(mig.scaleXY, mig.scaleXY), colormap="red" )

    def update_parameters():
        removebg_parameters(preprocess.remove_background.value)
        tophat_parameters(preprocess.tophat_filter.value)
        n2v_parameters(preprocess.noise2void.value)
    
    def reset_junc():
        ut.remove_layer(viewer,"2DJunctions")
        imgjun = saveimg
        viewer.add_image( imgjun, name="2DJunctions", blending="additive", scale=(mig.scaleXY, mig.scaleXY), colormap="red" )
    
    def n2v_parameters(booly):
        preprocess.denoising_done.visible = booly

    def end_denoising():
        if "Denoised" in viewer.layers:
            ut.remove_widget(viewer, "Dock widget 1")
            ut.remove_layer(viewer, "2DJunctions")
            viewer.layers["Denoised"].name = "2DJunctions"
        viewer.layers["2DJunctions"].refresh()

    def removebg_parameters(booly):
        preprocess.remove_background_radius.visible = booly
    
    def tophat_parameters(booly):
        preprocess.tophat_filter_radius.visible = booly

    @magicgui(call_button="Preprocess", 
            reset_junction_staining={"widget_type":"PushButton", "value": False, "name": "reset_junction_staining"}, 
            denoising_done={"widget_type":"PushButton", "value": False, "name": "denoising_done"}, )
    def preprocess(
            remove_background=False,
            remove_background_radius = 50,
            tophat_filter=False,
            tophat_filter_radius = 5,
            noise2void = False,
            reset_junction_staining=False,
            denoising_done = False,
            ):
        cfg.addText("Preprocess 2D junction staining")
        
        imgjun = viewer.layers["2DJunctions"].data
        if remove_background:
            #cfg.addTextParameter("Preprocess", "remove_background_radius", remove_background_radius)
            imgjun = mig.preprocess_junction2D_removebg( imgjun, remove_background_radius )
            ut.show_info("background removed")
        
        if tophat_filter:
            #cfg.addTextParameter("Preprocess", "tophat_filter_radius", tophat_filter_radius)
            imgjun = mig.preprocess_junction2D_tophat( imgjun, tophat_filter_radius )
            ut.show_info("Tophat filter applied")
        
        if "2DJunctions" in viewer.layers:
            viewer.layers["2DJunctions"].data = imgjun
            viewer.layers["junctionsStaining"].refresh()
        
        if noise2void:
            #mig.prepare_junctions()
            from napari_n2v import PredictWidgetWrapper
            viewer.window.add_dock_widget(PredictWidgetWrapper(viewer))

        if not "2DJunctions" in viewer.layers:
            viewer.add_image( imgjun, name="2DJunctions", blending="additive", scale=(mig.scaleXY, mig.scaleXY), colormap="blue" )
        viewer.layers["2DJunctions"].data = imgjun
        viewer.layers["2DJunctions"].refresh()
    
    removebg_parameters(False)
    tophat_parameters(False)
    n2v_parameters(False)
    preprocess.remove_background.changed.connect(update_parameters)
    preprocess.tophat_filter.changed.connect(update_parameters)
    preprocess.noise2void.changed.connect(update_parameters)
    preprocess.reset_junction_staining.clicked.connect(reset_junc)
    preprocess.denoising_done.clicked.connect(end_denoising)
    ut.hide_color_layers(viewer, mig)
    if "junctionsStaining" in viewer.layers:
        viewer.layers["junctionsStaining"].visible = True
    viewer.window.add_dock_widget(preprocess, name="Preprocess2D")

def preprocNuclei():
    """ Preprocessing of the 3D nuclei (filters, denoising) """
    print("********** Preprocessing nuclei signal *************")
    rm_bg = False
    rm_bg_rad = 20
    medfilt = False
    medfilt_rad = 2
    paras = cfg.read_parameter_set("PreprocessNuclei")
    if paras is not None:
        if "remove_background" in paras:
            rm_bg = (paras["remove_background"].strip() == "True")
        if "median_filter" in paras:
            medfilt = (paras["median_filter"].strip() == "True")
        if "remove_background_radius" in paras:
            rm_bg_rad = int(paras["remove_background_radius"])
        if "median_filter_radius" in paras:
            medfilt_rad = int(paras["median_filter_radius"])

    def update_parameters():
        median_parameters(preprocess.median_filter.value)
        removebg_parameters(preprocess.remove_background.value)
        n2v_parameters(preprocess.noise2void.value)
    
    def reset_nuc():
        ut.show_info("Reset nuclei staining")
        mig.nucstain = None
        mig.prepare_segmentation_nuclei()
        ut.remove_layer(viewer,"nucleiStaining")
        viewer.add_image( mig.nucstain, name="nucleiStaining", blending="additive", scale=(mig.scaleZ, mig.scaleXY, mig.scaleXY), colormap="blue" )

    def median_parameters(booly):
        preprocess.median_radius.visible = booly
    
    def n2v_parameters(booly):
        preprocess.denoising_done.visible = booly

    def end_denoising():
        if "Denoised" in viewer.layers:
            ut.remove_widget(viewer, "Dock widget 1")
            ut.remove_layer(viewer, "nucleiStaining")
            viewer.layers["Denoised"].name = "nucleiStaining"
            mig.nucstain = viewer.layers["nucleiStaining"].data
        viewer.layers["nucleiStaining"].refresh()

    def removebg_parameters(booly):
        preprocess.remove_background_radius.visible = booly

    @magicgui(call_button="Preprocess", 
            reset_nuclei_staining={"widget_type":"PushButton", "value": False, "name": "reset_nuclei_staining"}, 
            denoising_done={"widget_type":"PushButton", "value": False, "name": "denoising_done"}, )
    def preprocess(median_filter=medfilt, median_radius = medfilt_rad,
            remove_background=rm_bg,
            remove_background_radius = rm_bg_rad,
            noise2void = False,
            reset_nuclei_staining=False,
            denoising_done = False,
            ):
        cfg.addGroupParameter("PreprocessNuclei")
        cfg.addParameter("PreprocessNuclei", "remove_background_radius", remove_background_radius)
        cfg.addParameter("PreprocessNuclei", "median_filter_radius", median_radius)
        cfg.addParameter("PreprocessNuclei", "remove_background", remove_background)
        cfg.addParameter("PreprocessNuclei", "median_filter", median_filter)
        cfg.write_parameterfile()

        if remove_background:
            mig.preprocess_nuclei_removebg( remove_background_radius )
        if median_filter:
            mig.preprocess_nuclei_median( median_radius )
        if noise2void:
            mig.prepare_nuclei()
            from napari_n2v import PredictWidgetWrapper
            viewer.window.add_dock_widget(PredictWidgetWrapper(viewer))

        if not "nucleiStaining" in viewer.layers:
            viewer.add_image( mig.nucstain, name="nucleiStaining", blending="additive", scale=(mig.scaleZ, mig.scaleXY, mig.scaleXY), colormap="blue" )
        viewer.layers["nucleiStaining"].refresh()
    
    update_parameters()
    preprocess.median_filter.changed.connect(update_parameters)
    preprocess.remove_background.changed.connect(update_parameters)
    preprocess.noise2void.changed.connect(update_parameters)
    preprocess.reset_nuclei_staining.clicked.connect(reset_nuc)
    preprocess.denoising_done.clicked.connect(end_denoising)
    ut.hide_color_layers(viewer, mig)
    if "nucleiStaining" in viewer.layers:
        viewer.layers["nucleiStaining"].visible = True
    viewer.window.add_dock_widget(preprocess, name="Preprocess")


#######################################################################
################### Junction and nuclei separation functions

def divorceJunctionsNuclei():
    """ Separate the junctions and nuclei staining if they are in the same channel """
    
    text = "Separate the junction and nuclei staining that are in the same channel \n"
    text += "Creates two new layers, junctionStaining and nucleiStaining \n"
    text += "Tophat filter option separate the signals based on morphological filtering \n"
    text += "Check the \'close layers\' box if you want the two created layers to be closed at the end of this step \n"
    text += "SepaNet option separate the signals with trained neural networks \n"
    ut.showOverlayText(viewer, text)
    ut.show_info("********** Separating the junction and nuclei staining ***********")

    paras = {}
    paras["tophat_radxy"] = 4
    paras["tophat_radz"] = 1
    paras["outlier_thres"] = 40
    paras["smooth_nucleixy"] = 2
    paras["smooth_nucleiz"] = 2
    paras["sepanet_path"] = os.path.join(".", "sepaNet")
    
    load_paras = cfg.read_parameter_set("Separate")
    if load_paras is not None:
        if "method" in load_paras:
            paras["method"] = load_paras["method"]
        if "tophat_radxy" in load_paras:
            paras["tophat_radxy"] = int(load_paras["tophat_radxy"])
        if "tophat_radz" in load_paras:
            paras["tophat_radz"] = int(load_paras["tophat_radz"])
        if "outlier_thres" in load_paras:
            paras["outlier_thres"] = int(load_paras["outlier_thres"])
        if "smooth_nucleixy" in load_paras:
            paras["smooth_nucleixy"] = int(load_paras["smooth_nucleixy"])
        if "smooth_nucleiz" in load_paras:
            paras["smooth_nucleiz"] = int(load_paras["smooth_nucleiz"])
        if "sepanet_path" in load_paras:
            paras["sepanet_path"] = load_paras["sepanet_path"]
    
    defmethod = "SepaNet"
    if "method" in paras:
        defmethod = paras["method"]
    separated_junctionsfile = mig.separated_junctions_filename(ifexist=True)
    if separated_junctionsfile != "":
        defmethod = "Load"

    def sep_para(booly):
        """ Parameters visibility """
        separate.tophat_radxy.visible = booly
        separate.tophat_radz.visible = booly
        separate.outlier_thres.visible = booly
        separate.smooth_nucleixy.visible = booly
        separate.smooth_nucleiz.visible = booly
    
    def choose_method():
        separate.sepanet_path.visible = (separate.method.value=="SepaNet")
        sep_para( separate.method.value == "Tophat filter" )
        separate.separated_junctions_path.visible = (separate.method.value == "Load")
        separate.separated_nuclei_path.visible = (separate.method.value == "Load")
    
    def save_separated_staining():
        """ Save the two result images """
        if "junctionsStaining" in viewer.layers:
            outname = mig.separated_junctions_filename()
            mig.save_image( viewer.layers["junctionsStaining"].data, outname, hasZ=True, imtype="uint8" )
        if "nucleiStaining" in viewer.layers:
            outname = mig.separated_nuclei_filename()
            mig.save_image( viewer.layers["nucleiStaining"].data, outname, hasZ=True, imtype="uint8" )
    
    def separate_help():
        """ Open the documentation page """
        ut.show_documentation_page("Separate-junctions-and-nuclei")

    def separate_go():
        """ Perform separation with selected method and parameters """
        ut.showOverlayText(viewer, "Discriminating between nuclei and junctions...")
        ut.hide_color_layers(viewer, mig)
        ut.remove_layer(viewer,"junctionsStaining")
        ut.remove_layer(viewer,"nucleiStaining")
        if separate.method.value == "Tophat filter":
            discriminating(separate.tophat_radxy.value, separate.tophat_radz.value, separate.outlier_thres.value, separate.smooth_nucleixy.value, separate.smooth_nucleiz.value )
        if separate.method.value == "SepaNet":
            sepaneting( separate.sepanet_path.value )
        if separate.method.value == "Load":
            load_separated(separate.separated_junctions_path.value, separate.separated_nuclei_path.value, end_dis=True)

    @magicgui(call_button="Separation done",
            method={"choices": ["Load", "SepaNet", "Tophat filter"]},
            sepanet_path={'mode': 'd'},
            Separate={"widget_type":"PushButton", "value": False},
            _={"widget_type":"EmptyWidget", "value": False},
            Save_separated={"widget_type":"PushButton", "value": False},
            Help={"widget_type":"PushButton", "value": False},)
    def separate( method = defmethod,
            separated_junctions_path=pathlib.Path(separated_junctionsfile),
            separated_nuclei_path=pathlib.Path(mig.separated_nuclei_filename(ifexist=True)),
            sepanet_path=pathlib.Path(os.path.join(paras["sepanet_path"])),
            tophat_radxy=paras["tophat_radxy"],
            tophat_radz=paras["tophat_radz"],
            outlier_thres=paras["outlier_thres"],
            smooth_nucleixy=paras["smooth_nucleixy"],
            smooth_nucleiz=paras["smooth_nucleiz"],
            close_layers = False,
            Separate = False,
            _ = False,
            Save_separated = False,
            Help = False,
            ):
        ut.remove_widget(viewer, "Separate")
        cfg.addGroupParameter("Separate")
        cfg.addParameter("Separate", "method", method)
        cfg.addParameter("Separate", "sepanet_path", sepanet_path)
        cfg.addParameter("Separate", "tophat_radxy", tophat_radxy)
        cfg.addParameter("Separate", "tophat_radz", tophat_radz)
        cfg.addParameter("Separate", "outlier_thres", outlier_thres)
        cfg.addParameter("Separate", "smooth_nucleixy", smooth_nucleixy)
        cfg.addParameter("Separate", "smooth_nucleiz", smooth_nucleiz)
        cfg.write_parameterfile()
        if close_layers:
            ut.remove_layer(viewer, "junctionsStaining")
            ut.remove_layer(viewer, "nucleiStaining")
        return 1

    choose_method()
    separate.method.changed.connect(choose_method)
    separate.Save_separated.clicked.connect(save_separated_staining)
    separate.Separate.clicked.connect(separate_go)
    separate.Help.clicked.connect(separate_help)
    viewer.window.add_dock_widget(separate, name="Separate")

def end_discrimination():
    """ Show resulting separated stainings """
    viewer.add_image( mig.junstain, name="junctionsStaining", blending="additive", scale=(mig.scaleZ, mig.scaleXY, mig.scaleXY), colormap="red" )
    viewer.add_image( mig.nucstain, name="nucleiStaining", blending="additive", scale=(mig.scaleZ, mig.scaleXY, mig.scaleXY), colormap="blue" )
    ut.removeOverlayText(viewer)

#@thread_worker(connect={'yielded': end_discrimination})
def sepaneting( sepanet_dir ):
    """ Separate the junction and nuclei stainign with SepaNet trained networks """
    viewer.window._status_bar._toggle_activity_dock(True)
    mig.separate_with_sepanet( sepanet_dir )
    viewer.window._status_bar._toggle_activity_dock(False)
    end_discrimination()
    #yield 1

def load_separated( junfile, nucfile, end_dis=True ):
    """ Load the two separated staining from files """
    mig.load_separated_staining( junfile, nucfile )
    ut.show_info("Separated stainings loaded")
    if end_dis:
        end_discrimination()


@thread_worker(connect={'yielded': end_discrimination})
def discriminating( wthradxy, wthradz, outthres, smoothxy, smoothz):
    mig.separate_junctions_nuclei( wth_radxy=wthradxy,
                wth_radz = wthradz,
                rmoutlier_threshold=outthres,
                smoothnucxy=smoothxy,
                smoothnucz=smoothz )
    yield 1


#######################################################################
################ Nuclei segmentation


def getNuclei():
    """ 3D segmentation and correction of nuclei """
    print("******* 3D segmentation of nuclei ******")
    text = "Choose method and parameters to segment nuclei in 3D \n"
    text += "The nuclei are segmented from the original nuclei channel if the stainings are separate \n"
    text += "Or from the nucleiStaining image if the staining were originally mixed \n"
    ut.showOverlayText(viewer, text)

    ut.hide_color_layers(viewer, mig)
    ut.show_layer(viewer, mig.nucchan)
        
    nuclei_widget = NucleiWidget( viewer, mig, cfg, divorceJunctionsNuclei, showCellsWidget )
    viewer.window.add_dock_widget( nuclei_widget, name="Get nuclei" )

#######################################################################
######################### Association of 2D cells with nuclei

def doCellAssociation():
    """ Association of nuclei with corresponding apical junction cells """
    text = "Find the nucleus associated with each apical cell \n"
    print("******* Associate apical cells and nuclei together ******")
    ut.remove_widget(viewer, "Associating")
    ut.showOverlayText(viewer, text)
    ## load parameters
    defmethod = "Calculate association"
    distasso = 30.0
    assojuncfile = mig.junction_filename(dim=2, ifexist=True)
    assonucfile = mig.nuclei_filename(ifexist=True)
    paras = cfg.read_parameter_set("Association")
    if paras is not None:
        if "method" in paras:
            defmethod = paras["method"]
        if "distance_toassociate_micron" in paras:
            distasso = float(paras["distance_toassociate_micron"])
        if "associated_junctions" in paras:
            assojuncfile = paras["associated_junctions"]
        if "associated_nuclei" in paras:
            assonucfile = paras["associated_nuclei"]
    if os.path.exists(assojuncfile):
        defmethod = "Load association"

    def parameters_visibility():
        """ Handle which parameters to show """
        booly = (do_association.method.value=="Load association")
        do_association.associated_junctions.visible = booly
        do_association.associated_nuclei.visible = booly
        do_association.distance_toassociate_micron.visible = (not booly)
    
    def load_association():
        """ Load association from files """
        mig.load_segmentation(do_association.associated_junctions.value)
        mig.popFromJunctions()
        mig.load_segmentation_nuclei(do_association.associated_nuclei.value)
        mig.popNucleiFromMask()
        ut.remove_widget(viewer, "Associating")
        ut.removeOverlayText(viewer)
        end_association()

    def show_asso_doc():
        """ Open the Wiki documentation page """
        ut.show_documentation_page("Associate")

    @magicgui(call_button="Go", method={"choices": ["Load association", "Calculate association"]}, 
            _={"widget_type":"EmptyWidget", "value": False},
            Help ={"widget_type":"PushButton", "value": False},)
    def do_association(method = defmethod,
            associated_junctions=pathlib.Path(assojuncfile),
            associated_nuclei=pathlib.Path(assonucfile),
            distance_toassociate_micron=distasso,
            _ = False,
            Help = False, ):
        if not mig.hasCells():
            ut.show_error("No junctions were segmented/loaded. Do it before")
            return
        if not mig.hasNuclei():
            ut.show_error("No nuclei were segmented/loaded. Do it before")
            return
        
        cfg.addGroupParameter("Association")
        cfg.addParameter("Association", "method", method)
        cfg.addParameter("Association", "associated_junctions", associated_junctions)
        cfg.addParameter("Association", "associated_nuclei", associated_nuclei)
        cfg.addParameter("Association", "distance_toassociate_micron", distance_toassociate_micron)
        cfg.write_parameterfile()
        
        if method == "Calculate association":
            start_time = ut.get_time()
            ut.showOverlayText(viewer, "Doing junction-nuclei association...")
            ut.show_info("Associate "+str(mig.nbCells())+" junctions with nuclei...")
            pbar = ut.start_progress( viewer, total=2, descr="Calculating association..." )
            go_association(distance=distance_toassociate_micron, pbar=pbar)
            ut.close_progress( viewer, pbar )
            ut.show_duration( start_time, "Association calculated in ")
        else:
            ut.show_info("Load association from files")
            load_association()
    
    parameters_visibility()
    do_association.method.changed.connect(parameters_visibility)
    do_association.Help.clicked.connect(show_asso_doc)
    viewer.window.add_dock_widget(do_association, name="Associating")
    

def end_association():
    """ Automatic association finished, go to manual correction step """
    ut.show_info("Correct association if necessary")
    ut.removeOverlayText(viewer)
    ut.remove_layer(viewer, "CellContours")
    ut.remove_layer(viewer, "CellNuclei")
    viewer.add_labels( mig.getJunctionsImage3D(), name="CellContours", blending="additive", scale=(mig.scaleZ, mig.scaleXY, mig.scaleXY) )
    viewer.layers["CellContours"].editable = False
    viewer.add_labels( mig.nucmask, name="CellNuclei", blending="additive", scale=(mig.scaleZ, mig.scaleXY, mig.scaleXY) )
    viewer.layers["CellNuclei"].n_edit_dimensions = 3
    showAssociationWidget( viewer.layers["CellContours"], viewer.layers["CellNuclei"], shapeName="JunctionNames", dim=3 )
    associateCNWidget( viewer.layers["CellContours"], viewer.layers["CellNuclei"] )
    saveAssociation()

def go_association( distance, pbar=None ):
    mig.go_association(distance=distance, pbar=pbar)
    ut.remove_widget(viewer, "Associating")
    end_association()

def saveAssociation():
    """ Finish and save cells-nuclei association """
    @magicgui(call_button="Assocation done",
              save_association={"widget_type":"PushButton", "value": False}, )
    def end_association( 
            juncfilename=pathlib.Path(mig.junction_filename(dim=2, ifexist=False)),
            nucfilename=pathlib.Path(mig.nuclei_filename(ifexist=False)),
            save_association=False,):
        junc3D = viewer.layers["CellContours"].data
        mig.junmask = np.max(junc3D, axis=0)
        ut.remove_layer(viewer,"CellContours")
        ut.remove_layer(viewer,"CellNuclei")
        ut.remove_layer(viewer,"JunctionNames")
        ut.remove_widget(viewer, "End association")
        ut.remove_widget(viewer, "Edit association")
        ut.remove_widget(viewer, "CellNuc association")
        ut.removeOverlayText(viewer)

    def save_asso():
        mig.save_image( mig.nucmask, end_association.nucfilename.value, hasZ=True )
        mig.popNucleiFromMask( associate=True )
        mig.save_results()

    end_association.save_association.clicked.connect(save_asso)
    viewer.window.add_dock_widget( end_association, name="End association" )


#######################################################################
######################### RNA

def getOverlapRNA():
    """ Find RNAs overlapping in several channels (non specific signal) """
    chanlist = mig.potential_rnas()

    def find_over_rnas():
        """ Detect RNAs present in all the selected channels """
        channels = over_rnas.in_channels.value
        mixed = mig.mixchannels(channels)
        for lay in viewer.layers:
            lay.visible = False
        for chan in channels:
            lay = ut.get_layer(viewer, "originalChannel"+str(chan))
            if lay is not None:
                lay.visible = True
        if over_rnas.show_mixed_image.value:
            viewer.add_image(mixed, name="Mixchannels"+str(channels), scale=(mig.scaleZ, mig.scaleXY, mig.scaleXY), blending="additive")
    
        spots = mig.find_blobs_in_image( mixed, channels, over_rnas.spot_sigma.value, over_rnas.threshold.value )
        points = np.array(spots)
        fcolor = "white"
        ut.remove_layer(viewer, "OverlapRNA"+str(channels))
        ut.add_point_layer( viewer=viewer, pts=points, colors=fcolor, layer_name="OverlapRNA"+str(channels), mig=mig, size=7 )


        
    @magicgui(call_button="Overlapping RNAs done", 
              in_channels = dict(widget_type="Select", choices=chanlist),
              spot_sigma = {"widget_type": "LiteralEvalLineEdit"},
              threshold = {"widget_type": "LiteralEvalLineEdit"},
              find_overlapping_rnas={"widget_type":"PushButton", "value": False},
              )
    def over_rnas(
            in_channels = [],
            show_advanced = False,
            spot_sigma = 1.5,
            threshold = 0.25,
            show_mixed_image = False,
            save_overlapping_rnas = True,
            find_overlapping_rnas = False,
            ):
        channels = in_channels
        layerrna = ut.get_layer(viewer, "OverlapRNA"+str(channels))
        spots = layerrna.data
        labels = [1]*len(spots)
        scores = [0]*len(spots)
        mig.set_spots(str(channels), spots)
        if save_overlapping_rnas:
            outname = mig.get_filename( "_RNA_over_"+str(channels)+".csv" )
            mig.save_spots(spots.astype(int), np.array(labels).astype(int), np.array(scores).astype(int), str(channels), outname)
        ut.remove_layer(viewer, "OverlapRNA"+str(channels))
        ut.remove_widget(viewer, "Overlapping RNAs")
        ut.remove_widget(viewer, "Main")
        getChoices(default_action="Get RNA")
    
    def show_advanced_changed():
        booly = over_rnas.show_advanced.value
        over_rnas.threshold.visible = booly
        over_rnas.spot_sigma.visible = booly
        over_rnas.show_mixed_image.visible = booly
        over_rnas.save_overlapping_rnas.visible = booly

    show_advanced_changed()
    over_rnas.find_overlapping_rnas.clicked.connect(find_over_rnas)
    over_rnas.show_advanced.changed.connect(show_advanced_changed)
    viewer.window.add_dock_widget( over_rnas, name="Overlapping RNAs" )



def getRNA():
    """ Segment the RNA dots in selected channels """
    if not ut.has_widget( viewer, "RNAs"):
        rnaGUI = NapaRNA(viewer, mig, cfg)
            #drawing_spot_size = paras["RNA"+str(rnachannel)+"_drawing_spot_size"] ):

def unremove(layer):
    ut.show_info("Removing layer locked, throw an error ")
    #print(str(error))
    return

######## Labels edition

def showCellsWidget(layerName, shapeName='CellNames', dim=3):
    layer = viewer.layers[layerName]
        
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
                        frame = int(viewer.dims.current_step[0])
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
        if shapeName in viewer.layers:
            viewer.layers.remove(shapeName)
        else:
            get_bblayer(layer, shapeName, dim)
        return
    
    def relabel_layer():
        i = 2
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
        if shapeName in viewer.layers:
            viewer.layers.remove(shapeName)
        #if addnamelayer.show_cellnames.value==True:
        #    get_bblayer(layer, shapeName, dim)

    #@layer.bind_key('h', overwrite=True)
    #def show_help(layer):
    #    ut.showHideOverlayText(viewer)

    #@magicgui(call_button="Relabel",)
    #def addnamelayer(show_cellnames: bool, ):
    #    relabel_layer()
    #    return

    #addnamelayer.show_cellnames.changed.connect(show_names)
    help_text = ut.labels_shortcuts( level = 0 )
    header = ut.helpHeader(viewer, layerName)
    ut.showOverlayText(viewer, header+help_text)
    
    print( "\n #########################################\n Labels correction options:\n " + help_text + textCellsWidget() )

    if "Junctions" in viewer.layers:
        viewer.layers["Junctions"].preserve_labels = True
    #viewer.window.add_dock_widget(addnamelayer, add_vertical_stretch=True, name="Edit labels")

def textCellsWidget():
    text = "  <Control+left click> from one label to another to merge them (the label kept will be the last one) \n"
    text += "'show_cellnames' (<l>) add a new layer showing the label (number) around each object position. \n"
    #text += "'relabel update' the cell labels to have consecutives numbers from 2 to number_of_cells.\n"
    text += "\n For 3D: \n"
    text += "In 3D, most label actions wont work if Vispy perspective is ON. Switch it off with 'Ctrl-v' before.\n"
    text += "If n_edit_dim is set on 3 (top left panel), edition will affect all or several z (slices) \n"
    text += "If n_edit_dim is set on 2, edition will only affect the active slice \n"
    return text


def associateCNWidget(layerJun, layerNuc):

    @magicgui(call_button="Associate now", nucleus={"widget_type":"LineEdit"}, associate={"widget_type":"Label"}, cell={"widget_type":"LineEdit"})
    def associateCN(nucleus=0, associate="with", cell=0):
        print("Associate nucleus "+str(nucleus)+" with cell "+str(cell))
        mig.associateCN(int(nucleus), int(cell))
        viewer.layers["CellNuclei"].refresh()
    
    @layerNuc.bind_key('c', overwrite=True)
    def associateBis(layer):
        nucleus = int(associateCN.nucleus.value)
        cell = int(associateCN.cell.value)
        if nucleus == 0 or cell == 0:
            print("One value is zero, ignore association")
            return
        print("Associate nucleus "+str(nucleus)+" with cell "+str(cell))
        mig.associateCN(nucleus, cell)
        viewer.layers["CellNuclei"].refresh()
     


    # Handle click or drag events separately
    @layerNuc.mouse_drag_callbacks.append
    def click(layer, event):
        if event.type == "mouse_press":
            if event.button == 2:
                # right click
                value = layerJun.get_value(position=event.position, view_direction = event.view_direction, dims_displayed=event.dims_displayed, world=True)
                associateCN.cell.value = value
            if (event.button == 1) and ("Control" in event.modifiers): 
                ## associate nucleus with cell
                value = layerNuc.get_value(position=event.position, view_direction = event.view_direction, dims_displayed=event.dims_displayed, world=True)
                associateCN.nucleus.value = value 
                layerNuc.selected_label = value
            
    viewer.window.add_dock_widget(associateCN, name="CellNuc association")

def showAssociationWidget(layerJun, layerNuc, shapeName='CellNames', dim=3):
    @magicgui(call_button="Update")
    def addnamelayer(show_cellnames=False, sync_cellsNuclei=False):
        if sync_cellsNuclei:
            synchronizeLayers(viewer) 
        else:
            unsynchronizeLayers(viewer)
        
        if show_cellnames:
            if not shapeName in viewer.layers:
                showCellNames(viewer)
        else:
            ut.remove_layer(viewer, shapeName)
        return

    @layerNuc.bind_key('l', overwrite=True)
    @layerJun.bind_key('l', overwrite=True)
    def showCellNames(layer):
        if shapeName in viewer.layers:
            ut.remove_layer(viewer, shapeName)
        else:
            get_bblayer(layerJun, shapeName, dim)

    @layerNuc.bind_key('s', overwrite=True)
    @layerJun.bind_key('s', overwrite=True)
    def synchronizeLayers(layer):
        viewer.layers.link_layers((layerJun, layerNuc), ('selected_label', 'n_edit_dimensions', 'visible', 'refresh', 'mode', 'contiguous'))
        layerJun.show_selected_label = True
        layerNuc.show_selected_label = True
    
    @layerNuc.bind_key('Control-c', overwrite=True)
    @layerJun.bind_key('Control-c', overwrite=True)
    def contour_increase(layer):
        if layerNuc is not None:
            layerNuc.contour = layerNuc.contour + 1
    
    @layerNuc.bind_key('Alt-c', overwrite=True)
    @layerJun.bind_key('Alt-c', overwrite=True)
    def contour_increase(layer):
        if layerJun is not None:
            layerJun.contour = layerJun.contour + 1
    
    @layerNuc.bind_key('Alt-d', overwrite=True)
    @layerJun.bind_key('Alt-d', overwrite=True)
    def contour_decrease(layer):
        if layerJun is not None:
            if layerJun.contour > 0:
                layerJun.contour = layerJun.contour - 1
        
    @layerNuc.bind_key('Control-d', overwrite=True)
    @layerJun.bind_key('Control-d', overwrite=True)
    def contour_decrease(layer):
        if layerNuc is not None:
            if layerNuc.contour > 0:
                layerNuc.contour = layerNuc.contour - 1
    
    @layerNuc.bind_key('u', overwrite=True)
    @layerJun.bind_key('u', overwrite=True)
    def unsynchronizeLayers(layer):
        viewer.layers.unlink_layers()
        layerJun.show_selected_label = False
        layerNuc.show_selected_label = False

    help_text = "<Control+Left-click> to select a nucleus value \n"
    help_text = help_text + "<Right-click> to choose the cell to associate with \n"
    help_text = help_text + "<c> to apply current association \n"
    help_text = help_text + "<l> to show/hide cell labels \n"
    help_text = help_text + "<s> to synchronize junctions and nuclei view \n"
    help_text = help_text + "<u> to unsynchronize junctions and nuclei view \n"
    help_text += "  <Ctrl-c>/<Ctrl-d> increase/decrease NUCLEI label contour \n"
    help_text += "  <Alt-c>/<Alt-d> increase/decrease JUNCTIONS label contour \n"
    header = ut.helpHeader(viewer, "CellNuclei")
    ut.showOverlayText(viewer, header+help_text)
    print("\n ---- Association editing ---- ")
    viewer.window.add_dock_widget(addnamelayer, name="Edit association")


def make_bbox2D(bbox_extents):
    """Get the coordinates of the corners of a
    bounding box from the extents

    Parameters
    ----------
    bbox_extents : list (4xN)
        List of the extents of the bounding boxes for each of the N regions.
        Should be ordered: [min_row, min_column, max_row, max_column]

    Returns
    -------
    bbox_rect : np.ndarray
        The corners of the bounding box. Can be input directly into a
        napari Shapes layer.
    """
    minc = bbox_extents[0]*mig.scaleXY
    mint = bbox_extents[1]*mig.scaleXY
    maxc = bbox_extents[2]*mig.scaleXY
    maxt = bbox_extents[3]*mig.scaleXY
    
    bbox_rect = np.array(
        [[minc, mint], [minc, maxt], [maxc, maxt], [maxc,mint]]
    )
    bbox_rect = np.moveaxis(bbox_rect, 2, 0)
    return bbox_rect

def make_bbox3D(bbox_extents):
    """Get the coordinates of the corners of a
    bounding box from the extents

    Parameters
    ----------
    bbox_extents : list (4xN)
        List of the extents of the bounding boxes for each of the N regions.
        Should be ordered: [min_row, min_column, max_row, max_column]

    Returns
    -------
    bbox_rect : np.ndarray
        The corners of the bounding box. Can be input directly into a
        napari Shapes layer.
    """
    minr = bbox_extents[0]*mig.scaleZ
    minc = bbox_extents[1]*mig.scaleXY
    mint = bbox_extents[2]*mig.scaleXY
    maxr = bbox_extents[3]*mig.scaleZ
    maxc = bbox_extents[4]*mig.scaleXY
    maxt = bbox_extents[5]*mig.scaleXY
    limr = (minr+maxr)/2
    
    
    bbox_rect = np.array(
        [[limr, minc, mint], [limr, minc, maxt], [limr, maxc, maxt], [limr, maxc,mint]]
    )
    bbox_rect = np.moveaxis(bbox_rect, 2, 0)

    return bbox_rect

def get_bblayer(lablayer, name, dim):
    """ Show the cell names """
    # create the properties dictionary
    properties = regionprops_table(
        lablayer.data, properties=('label', 'bbox')
    )

    # create the bounding box rectangles
    if dim == 2:
        bbox_rects = make_bbox2D([properties[f'bbox-{i}'] for i in range(4)])
    if dim == 3:
        bbox_rects = make_bbox3D([properties[f'bbox-{i}'] for i in range(6)])
    if viewer.dims.ndisplay == 2:
        transl = [0,0]
    else:
        transl = [0,0,0]

    # specify the display parameters for the text
    text_parameters = {
        'text': '{label}',
        'size': 18,
        'color': 'white',
        'anchor': 'center',
        #'translation': transl,
    }

    namelayer = viewer.add_shapes(
    bbox_rects,
    face_color='transparent',
    edge_color='gray',
    edge_width = 0,
    properties=properties,
    text=text_parameters,
    name=name,
    )
    viewer.layers.select_previous()
    return namelayer

def measureNuclearIntensity():
    """ Measure intensity inside segmented nuclei """
    if not mig.hasNuclei():
        ut.show_warning( "Segment/Load nuclei before" )
        return
    meas_nuc = MeasureNuclei( viewer, mig, cfg )
    viewer.window.add_dock_widget(meas_nuc, name="Measure nuclei")


############ measure cyto
def cytoplasmicStaining():
    """ Measure the cytoplasmic signal close to the apical surface """
    import ast
    text = "Measure cytoplasmic intensity close to the apical surface \n"
    text += "Choose the channel to measure in the \'cyto_channels\' parameter \n"
    text += "z_thickness is the number of z slices below the apical surface used for the measure \n "
    text += "Use the rectangle to estimate background intensity. The value will be averaged from the z_thickness slices below the rectangle \n"
    ut.showOverlayText(viewer, text)
    print("********** Measure cytoplasmic intensities **************")

    for layer in viewer.layers:
        layer.visible = False
    meanz = mig.getAverageCellZ()
    paras = {}
    paras["cytoplasmic_channels"] = [mig.free_channel()]
    paras["save_measures_table"] = True
    #paras["keep_previous_measures"] = True
    paras["show_measures_image"] = True
    paras["z_thickness"] = 3
    load_paras = cfg.read_parameter_set("MeasureCytoplasmic")
    if load_paras is not None:
        if "z_thickness" in load_paras:
            paras["z_thickness"] = int(load_paras["z_thickness"])
        if "save_measures_table" in load_paras:
            paras["save_measures_table"] = (load_paras["save_measures_table"].strip()) == "True"
        #if "keep_previous_measures" in load_paras:
        #    paras["keep_previous_measures"] = (load_paras["keep_previous_measures"].strip()) == "True"
        if "show_measures_image" in load_paras:
            paras["show_measures_image"] = (load_paras["show_measures_image"].strip()) == "True"
        if "cytoplasmic_channels" in load_paras:
            paras["cytoplasmic_channels"] = ast.literal_eval( load_paras["cytoplasmic_channels"].strip() )


    def update_cytochannels():
        dep = 20
        size = 50
        step = 30
        for layer in viewer.layers:
            layer.visible = False
        for pchan in range(mig.nbchannels):
            ut.remove_layer(viewer, "backgroundRectangle_"+str(pchan))
            QApplication.instance().processEvents()
        ## add this for removing layer bug in some windows (seems similar to that: https://github.com/napari/napari/issues/6472)
        QApplication.instance().processEvents()
        for chan in np.unique(cytochan.cyto_channels.value):
            polygon = np.array([[meanz, dep, dep], [meanz, dep, dep+size], [meanz, dep+size, dep+size], [meanz, dep+size, dep]])
            colname = ut.colormapname(chan)
            if not isinstance(colname, str):
                colname = colname.map(np.array([0.99]))
            try:
                QApplication.instance().processEvents()
                viewer.add_shapes( polygon, name="backgroundRectangle_"+str(chan), ndim=3, shape_type='rectangle', edge_width=0, face_color=colname, scale=(mig.scaleZ, mig.scaleXY, mig.scaleXY) )
                ut.show_layer(viewer, chan)
            except:
                ut.show_error( "Error while adding shape layer "+str(chan)+" \nPlease retry" )
                for pchan in range(mig.nbchannels):
                    ut.remove_layer(viewer, "backgroundRectangle_"+str(pchan))
                return
            dep += step
        viewer.dims.ndisplay = 2
        viewer.dims.set_point(0,meanz*mig.scaleZ)

    def show_cytomeas_doc():
        """ Open the wiki page on cytoplasmic measures """
        ut.show_documentation_page("Measure-cytoplasmic-staining")

    @magicgui(call_button="Cytoplasmic measure done", 
            measure_cyto={"widget_type":"PushButton", "value": False},
            cyto_channels={"widget_type": "ListEdit",}, 
            _={"widget_type":"EmptyWidget", "value": False},
            Help={"widget_type":"PushButton", "value": False}, )
    def cytochan( cyto_channels=paras["cytoplasmic_channels"], 
            show_measures_image=paras["show_measures_image"], save_measures_table=paras["save_measures_table"], 
            #keep_previous_measures=paras["keep_previous_measures"], 
            z_thickness=paras["z_thickness"], measure_cyto=False,
            _ = False,
            Help = False, ):
        measure_done()

    def measure():
        cytochans = np.unique(cytochan.cyto_channels.value)
        bgrois = []
        for chan in cytochans:
            layer = viewer.layers["backgroundRectangle_"+str(chan)]
            bgrois.append(layer.data)
            layer.visible = False
        
        cfg.addGroupParameter("MeasureCytoplasmic")
        cfg.addParameter("MeasureCytoplasmic", "cytoplasmic_channels", list(cytochans))
        cfg.addParameter("MeasureCytoplasmic", "save_measures_table", cytochan.save_measures_table.value)
        #cfg.addParameter("MeasureCytoplasmic", "keep_previous_measures", cytochan.keep_previous_measures.value)
        cfg.addParameter("MeasureCytoplasmic", "show_measures_image", cytochan.show_measures_image.value)
        cfg.addParameter("MeasureCytoplasmic", "z_thickness", cytochan.z_thickness.value)
        cfg.write_parameterfile()
        ut.removeOverlayText(viewer)

        results = mig.measureCytoplasmic(cytochans, bgrois, int(cytochan.z_thickness.value))
        if cytochan.save_measures_table.value:
            mig.save_results()
        
        if cytochan.show_measures_image.value:
            for i, chan in enumerate(cytochans):
                if "CytoplasmicNormalisedIntensity"+str(chan) in viewer.layers:
                    ut.remove_layer(viewer, "CytoplasmicNormalisedIntensity"+str(chan))
                cytomes = mig.drawCytoplasmicMeasure( chan, results )
                print(np.unique(cytomes))
                cproj = viewer.add_image(cytomes, name="CytoplasmicNormalisedIntensity"+str(chan), scale=(mig.scaleXY, mig.scaleXY), colormap=ut.colormapname(chan), blending="additive")
                cproj.contrast_limits=ut.quantiles(cytomes)
        #if cytochan.show_measures_table.value:
        #    show_table(results)
        
    def measure_done():
        ut.removeOverlayText(viewer)
        ut.remove_widget(viewer, "Measure cytos")
        for chan in range(mig.nbchannels):
            ut.remove_layer(viewer, "backgroundRectangle_"+str(chan))
            ut.remove_layer(viewer, "CytoplasmicNormalisedIntensity"+str(chan))

    update_cytochannels()
    cytochan.cyto_channels.changed.connect(update_cytochannels)
    cytochan.measure_cyto.clicked.connect(measure)
    cytochan.Help.clicked.connect(show_cytomeas_doc)
    viewer.window.add_dock_widget(cytochan, name="Measure cytos")


def helpMessageEditContours(dim=2):
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

### Grid tools: regular grid for spatial repere
def addGrid():
    """ Interface to create/load a grid for repere """
    if "FishGrid" not in viewer.layers:
        grid = FishGrid(viewer, mig)
        viewer.window.add_dock_widget(grid, name="FishGrid")
    else:
        gridlay = viewer.layers["FishGrid"]
        gridlay.visible = not gridlay.visible

### Touching labels for Griottes
def touching_labels():
    """ Dilate labels so that they all touch """
    ## perform the label expansion
    from skimage.morphology import binary_opening
    from skimage.segmentation import expand_labels
    print("********** Generate touching labels image ***********")
    
    ## get junctions img
    if "Cells" not in viewer.layers:
        if mig.pop is None or mig.pop.imgcell is None:
            ut.show_info("Load segmentation before!")
            return
        labimg = viewer.add_labels(mig.pop.imgcell, name="Cells", scale=(mig.scaleXY, mig.scaleXY), opacity=1, blending="additive")
        labimg.contour = 0

    ## skeletonize it
    img = viewer.layers["Cells"].data
    ext = np.zeros(img.shape, dtype="uint8")
    ext[img==0] = 1
    ext = binary_opening(ext, footprint=np.ones((2,2)))
    newimg = expand_labels(img, distance=4)
    newimg[ext>0] = 0
    newlay = viewer.add_labels(newimg, name="TouchingCells", scale=(mig.scaleXY, mig.scaleXY), opacity=1, blending="additive")
    newlay.contour = 0

    ## open the widget for options
    tlabel_wid = TouchingLabels( viewer, mig, cfg )
    viewer.window.add_dock_widget(tlabel_wid, name="Touching labels")

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
    img = mig.tryDiffusion( nchan=2 )
    viewer.add_image(img, name="test", scale=(mig.scaleZ, mig.scaleXY, mig.scaleXY), colormap=my_cmap, blending="additive")
