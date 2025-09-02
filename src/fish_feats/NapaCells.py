
import os
import fish_feats.Utils as ut
import fish_feats.FishWidgets as fwid
from fish_feats.NapaMix import Separation
import numpy as np
from qtpy.QtWidgets import QVBoxLayout, QWidget 

class MainCells( QWidget ):
    """ Main interface for cell (junctions) segmentation """

    def __init__( self, ffeats ):
        """ Interface to choose loading or proj and seg """
        super().__init__()
        self.viewer = ffeats.viewer
        self.mig = ffeats.mig
        self.cfg = ffeats.cfg
        self.ffeats = ffeats
        self.proj = None
    
        methods = ["", "Do projection and segmentation"]
        ind = 0
        self.projname = self.mig.build_filename( "_junction_projection.tif")
        self.cellsname = self.mig.build_filename( "_cells2D.tif")
        msg = ""
        if os.path.exists( self.projname ):
            msg = "Found projection file"
        if os.path.exists( self.cellsname ):
            methods.append( "Load previous files" )
            ind = 1
            msg += "\nFound cell file"
        msg += "\nChoose load to use those file(s)"

        if len(methods) == 2:
            ## there is nothing to load, go directly to projection and segmentation
            self.proj = Projection( self.ffeats )
            return

        layout = QVBoxLayout()
        ## Add message of found files
        info_msg = fwid.add_label( ""+msg, descr="Show info if found default files that can be loaded or not" )
        layout.addWidget( info_msg )
        ## Add choice of action
        do_line, self.methodChoice = fwid.list_line( "", descr="Choose to do projection and segmentation or load previous files", func=self.go_segmentation )
        self.methodChoice.addItems( methods )
        layout.addLayout( do_line )
        self.setLayout( layout )

    def go_segmentation( self ):
        """ Start the process according to selected method """
        method = self.methodChoice.currentText()
        if method == "Do projection and segmentation":
            ## go to projection plugin
            proj = Projection( self.ffeats )
            self.viewer.window.add_dock_widget( proj, name="JunctionProjection2D" )
        elif method == "Load previous files":
            ## load and show the projection
            if os.path.exists( self.projname ):
                ut.remove_layer( self.viewer, "2DJunctions" )
                roijunc = self.mig.load_image( self.projname )
                self.viewer.add_image( roijunc, name="2DJunctions", scale=(self.mig.scaleXY, self.mig.scaleXY), blending="additive" )
            ## load the cells and edit them
            self.mig.load_segmentation( self.cellsname )
            #get_cells = GetCells( self.ffeats )
            self.ffeats.correction_junctions()
            self.close()

class Projection( QWidget ):
    """ Get the 2D projection (local) of the junctions image """

    def __init__( self, ffeats ):
        """ Interface to handle local projection """
        super().__init__()
        self.viewer = ffeats.viewer
        self.mig = ffeats.mig
        self.cfg = ffeats.cfg
        self.ffeats = ffeats
        self.projection_filename = None
        self.projection_filename = self.mig.junction_projection_filename( ifexist=True )

        print("******** Junction staining 2D projection for segmentation ******")
        help_text = ut.help_shortcut( "projection" )
        ut.showOverlayText( self.viewer, help_text )

        layout = QVBoxLayout()

        ## Path to projection image file
        self.file_group, filename_layout = fwid.group_layout( "Load projection file", "Options to load projection image file" )
        load_btn = fwid.add_button( "Load default", self.load_projection_file, descr="Load the projection of junctions image", color=ut.get_color("load") )
        choose_file = fwid.add_button( "or choose file", self.get_projection_filename, descr="Choose a file with projected junctions image", color=None )
        load_line = fwid.double_widget( load_btn, choose_file )
        filename_layout.addLayout( load_line )
        self.file_group.setLayout( filename_layout )
        layout.addWidget( self.file_group )
        if (self.projection_filename is None) or ( self.projection_filename == "" ):
            load_btn.setEnabled( False )

        ## Additional options: projection parameters
        grp_line, ad_check, self.advanced = fwid.checkgroup_help( "Advanced", True, "Options for the projection calculation", help_link="Get-cells#2d-projection" )
        adv_layout = QVBoxLayout() 
        # local size
        wsize_line, self.local_size = fwid.value_line( "Local size", 40, descr="Size of the local projection in pixels" )
        ## smoothing size
        smooth_line, self.smooth_size = fwid.value_line( "Smoothing size", 3, descr="Smoothing of the local projection in pixels" )
        ## local contrast
        self.do_clahe = fwid.add_check( "Do local enhancement", False, None, descr="Apply local enhancement CLAHE to the projection image" )
        clahe_size, self.clahe_size = fwid.value_line( "CLAHE grid size", 20, descr="Grid size for the local enhancement CLAHE" )
        adv_layout.addLayout( wsize_line )
        adv_layout.addLayout( smooth_line )
        adv_layout.addWidget( self.do_clahe )
        adv_layout.addLayout( clahe_size )
        self.advanced.setLayout( adv_layout )
        layout.addLayout( grp_line )
        layout.addWidget( self.advanced )
        ad_check.setChecked( False )

        ## Launch calculation of the projection
        proj_btn = fwid.add_button( "Project now", self.do_projection, descr="Calculate the projection of junctions image", color=ut.get_color("go") )
        layout.addWidget( proj_btn )
        
        ## Save the projection to file after calculation
        self.save_proj = fwid.add_check( "Save projection", True, None, descr="Save the projection to file after calculation" )
        layout.addWidget( self.save_proj )

        ## Finish the step
        done_btn = fwid.add_button( "Projection done", self.finish_projection, descr="Finish the projection step and go to segmentation", color=ut.get_color("done") )
        layout.addWidget( done_btn )
        self.setLayout(layout)

    def do_projection( self ):
        """ Load/Calculate the projection, save and go to next step. Separate the signals if necessary before """
        ut.remove_layer( self.viewer, "2DJunctions" )
        ## separate if necessary the signals
        if self.mig.should_separate():
            ut.show_info("Junctions and nuclei staining in the same channel, separate them first")
            separation = Separation( self.viewer, self.mig, self.cfg ) 
            self.viewer.window.add_dock_widget(separation, name="Separate")
            return
        else:
            ## calculates the projection
            projxy = int( float( self.local_size.text() ) )
            smooth = int( float( self.smooth_size.text() ) )
            do_clahe = self.do_clahe.isChecked()
            clahe_grid = int( float( self.clahe_size.text() ) )
            roijunc = self.mig.prepare_segmentation_junctions( projxy=projxy, projsmooth=smooth, do_clahe=do_clahe, clahe_grid=clahe_grid )
            self.viewer.add_image( roijunc, name="2DJunctions", scale=(self.mig.scaleXY, self.mig.scaleXY), blending="additive" )

    def finish_projection( self ):
        """ Projection done, go to the next step (segmentation) """
        ## save the results if option is on
        if self.save_proj.isChecked():
            if "2DJunctions" not in self.viewer.layers:
                ut.show_warning( "Projected layer 2DJunctions not found" )
                return
            roijunc = self.viewer.layers["2DJunctions"].data
            outname = self.mig.build_filename( "_junction_projection.tif")
            self.mig.save_image( roijunc, imagename=outname )

        ut.removeOverlayText(self.viewer)
        ut.remove_layer( self.viewer, "junctionsStaining" )
        ut.remove_layer( self.viewer, "nucleiStaining" )
        ut.remove_widget( self.viewer, "Get cells" )
        ut.remove_widget( self.viewer, "JunctionProjection2D" )
        self.go_segmentation()
    
    def go_segmentation( self ):
        """ Segmentation then correction of the apical junctions """
        ut.show_info("******** Segmentation of junctions 2D projection ******")
        get_cell = GetCells( self.ffeats )
        self.viewer.window.add_dock_widget( get_cell, name="Segment cells" )

    def load_projection_file( self ):
        """ Load the projection file (default or selected) """
        ut.remove_layer( self.viewer, "2DJunctions" )
        roijunc = self.mig.load_image( self.projection_filename )
        self.viewer.add_image( roijunc, name="2DJunctions", scale=( self.mig.scaleXY, self.mig.scaleXY), blending="additive" )
        self.finish_projection()

    def get_projection_filename( self ):
        """ Open a file dialog to choose a file with projection of junctions """
        filename = fwid.file_dialog( "Choose projected junctions file", "*.tif", directory=self.mig.resdir )
        if filename is not None:
            self.projection_filename = filename
            #self.filename_label.setText(filename)
            self.load_projection_file()

class GetCells( QWidget ):
    """ Segment the cell contours from the image """

    def __init__( self, ffeats ):
        """ Interface to get the cell contours from the image """
        self.viewer = ffeats.viewer
        self.mig = ffeats.mig
        self.cfg = ffeats.cfg
        self.ffeats = ffeats
        self.junction_filename = None

        super().__init__()
        layout = QVBoxLayout()

        methods = [ "Epyseg", "CellPose", "Load segmented file", "Empty" ]
        defmeth = "Epyseg"
        celldiameter = 30
        self.chunksize = 1500
        self.paras = self.cfg.read_junctions()
        if self.paras is not None:
            if "chunk_size" in self.paras:
                self.chunksize = int(float(self.paras["chunk_size"]))
            if "cell_diameter" in self.paras:
                celldiameter = int(float(self.paras["cell_diameter"]))
            if "method" in self.paras:
                defmeth = self.paras["method"]
        if self.mig.junction_filename(dim=2, ifexist=True) != "":
            defmeth = "Load segmented file"
        self.junction_filename = self.mig.junction_filename(dim=2, ifexist=True)
        if self.junction_filename is None:
            self.junction_filename = self.mig.resdir

        ut.showOverlayText(self.viewer, "Choose cell junctions segmentation option", size=14)
        ut.hide_color_layers(self.viewer, self.mig)
        ut.show_layer(self.viewer, self.mig.junchan)

        ## choose the method
        meth_line, self.methodsChoice = fwid.list_line( "Method",  descr="Choose the method to segment the cell contours" )
        for meth in methods:
            self.methodsChoice.addItem( meth )
        layout.addLayout( meth_line )
        ## choose the cell diameter
        self.diam_group, diam_layout = fwid.group_layout( "", "" )
        diam_line, self.diameter = fwid.value_line( "Cell diameter", celldiameter, descr="Mean diameter of cell in pixels, used for segmentation" )
        diam_layout.addLayout( diam_line )
        self.diam_group.setLayout( diam_layout )
        layout.addWidget( self.diam_group )
        ## choose the chunk size
        #self.chunk_line, self.chunk_size = fwid.value_line( "Chunk size", chunksize, descr="Chunk size for the segmentation, used to avoid memory issues" )
        #layout.addLayout( self.chunk_line )
        ## choose loading filename
        self.file_group, filename_layout = fwid.group_layout( "", "" )
        filename_line, self.filename_label = fwid.file_line( "Choose file", self.junction_filename, dial_msg="Choose segmentation file", filetype="*.tif", descr="Choose the file containing the segmentation of the cells (labels)" )
        #filename_line, choose_filename, self.filename_label = fwid.label_button( "Choose file", self.get_junction_filename, label=self.junction_filename, descr="Choose a file with segmented junctions", color=None )
        filename_layout.addLayout( filename_line)
        self.file_group.setLayout( filename_layout )
        layout.addWidget( self.file_group )

        ## button to segment the cells
        segment_btn = fwid.add_button( "Segment cells", self.segment_cells, descr="Segment the cell contours from the image", color=ut.get_color("go") )
        layout.addWidget( segment_btn )
    
        self.methodsChoice.currentIndexChanged.connect( self.visibility )
        self.methodsChoice.setCurrentText( defmeth )
        self.visibility()
        self.setLayout( layout )

    def visibility( self ):
        """ Set the visibility of the parameters according to the method """
        self.diam_group.setVisible( self.methodsChoice.currentText() in ["CellPose"] )
        self.file_group.setVisible( self.methodsChoice.currentText() == "Load segmented file" )

    def get_junction_filename( self ):
        """ Open a file dialog to choose a file with segmented junctions """
        filename = fwid.file_dialog( "Choose segmented junctions file", "*.tif", directory=self.mig.resdir )
        if filename is not None:
            self.junction_filename = filename
            self.filename_label.setText(filename)

    def segment_cells( self ):
        """ Segment the cell contours from the image """
        ut.showOverlayText( self.viewer, """Doing segmentation of cell junctions...""", size=15 )
        self.cfg.addGroupParameter("JunctionSeg")
        method = self.methodsChoice.currentText()
        self.cfg.addParameter("JunctionSeg", "method", method)
        self.cfg.addParameter("JunctionSeg", "cell_diameter", int(self.diameter.text()))
        self.cfg.addParameter("JunctionSeg", "chunk_size", self.chunksize)
        self.cfg.write_parameterfile()
        ut.remove_layer( self.viewer, "Junctions" )
        if method == "Load segmented file":
            filename = self.filename_label.text()
            if os.path.exists( filename ):
                self.junction_filename = filename
            self.mig.load_segmentation( self.junction_filename )
            self.ffeats.correction_junctions()
            self.close()
        else:
            if "2DJunctions" in self.viewer.layers:
                roijunc = self.viewer.layers["2DJunctions"].data
                self.mig.do_segmentation_junctions( method, roijunc, int(self.diameter.text()), self.chunksize )
                self.ffeats.correction_junctions()
                self.close()
            else:
                ut.show_info("No projected junctions to segment, go to projection")
                ut.remove_widget(self.viewer, "Segment cells")
                ut.remove_widget( self.viewer, "Get cells" )
                proj = Projection( self.ffeats )
                self.viewer.window.add_dock_widget( proj, name="JunctionProjection2D" )


class EndCells( QWidget ):
    """ Handle the finishing of cell contour edition """

    def __init__( self, ffeats):
        """ Interface to save/finish the cell edition option """
        self.viewer = ffeats.viewer
        self.mig = ffeats.mig
        self.cfg = ffeats.cfg
        self.ffeats = ffeats
        
        super().__init__()
        layout = QVBoxLayout()

        ## show table button
        show_btn = fwid.add_button( "Show measures", self.show_measures, descr="Show the table of cell positions and areas" )
        layout.addWidget( show_btn )

        ## save current state of cells
        save_btn = fwid.add_button( "Save cells", self.save_all, descr="Save the current segmentation and cell measures", color=ut.get_color("save") )
        layout.addWidget( save_btn )

        ## options to save and do 3d position
        self.find_z_positions = fwid.add_check( "Find 3D positions", True, None, descr="Place the cell in 3D when finishing this step" )
        self.save_when_done = fwid.add_check( "Save when done", True, None, descr="Save the results and segmentation when this option is finished" )
        check_line = fwid.double_widget( self.find_z_positions, self.save_when_done )
        layout.addLayout( check_line )

        ## Final button, all done
        finish_btn = fwid.add_button( "Cells done", self.finish_junctions, descr="Finish this step, save if necessary", color=ut.get_color("done") )
        layout.addWidget( finish_btn )
    
        self.cfg.addText("'show_measures' open the table of cells measurement: area and position\n")
        self.setLayout( layout )

    def show_measures( self ):
        """ Display the measure table """
        self.mig.popFromJunctions()
        results = self.mig.measure_junctions()
        ut.show_table( results )
    
    def save_junc( self ):
        """ Save image of the labelled cells """
        filename = self.mig.junction_filename(dim=2, ifexist=False)
        self.mig.save_image( self.viewer.layers["Junctions"].data, filename, hasZ=False )
    
    def save_all( self ):
        """ Save the current image of the cells and the table results """
        self.save_junc()
        self.mig.save_results()

    def finish_junctions( self ):
        """ Finish the get cell option """
        self.mig.popFromJunctions( zpos = self.find_z_positions.isChecked() )
        if self.save_when_done.isChecked():
            self.save_all()
        self.viewer.window.remove_dock_widget("all")
        ut.removeOverlayText( self.viewer )
        ut.remove_layer( self.viewer, "Junctions" )
        ut.remove_layer( self.viewer, "2DJunctions" )
        ut.remove_layer( self.viewer, "JunctionsName" )
        self.cfg.removeTmpText()
        self.ffeats.getChoices( default_action = "Get nuclei" )


class Position3D( QWidget ):
    """ Interface to set/correct the cell 3D position """

    def __init__( self, ffeats ):
        """ GUI to handle cell 3D position """
        super().__init__()
        self.viewer = ffeats.viewer
        self.mig = ffeats.mig
        self.cfg = ffeats.cfg
    
        print("******** Cells Z position viewing/editing ******")
        header = ut.helpHeader(self.viewer, "CellContours")
        help_text = ut.help_shortcut("pos3d")
        ut.showOverlayText( self.viewer, header+help_text)
        paras = self.cfg.read_parameter_set("ZCells")
        zmapres = 200
        zmaplocsize = 300
        if paras is not None:
            if "zmap_resolution" in paras:
                zmapres = int(paras["zmap_resolution"])
            if "zmap_localsize" in paras:
                zmaplocsize = int(paras["zmap_localsize"])

        layout = QVBoxLayout()
        ## calculate map
        map_lab = fwid.add_label( "Map of cell Z position", descr="Paramters to calculate the local height map of cell positions")
        layout.addWidget( map_lab )
        ## choose resolution
        res_line, self.resolution = fwid.value_line(" Zmap resolution:", zmapres, descr="Resolution of the resulting Zmap after calculation (local neighborhood of same Z size)" )
        layout.addLayout( res_line )
        ## choose localsize 
        loc_line, self.localsize = fwid.value_line(" Zmap local size:", zmaplocsize, descr="Size of the local neighborhood to calculate the Z position" )
        layout.addLayout( loc_line )
        ## save option
        self.save_map = fwid.add_check( "Save Zmap", True, None, descr="Save the Zmap after calculation" )
        layout.addWidget( self.save_map )
        ##btn go calculate
        calc_btn = fwid.add_button( "(Re)calculate Zmap", self.calculate_zmap, descr="Calculate the Zmap with the selected parameters", color=ut.get_color("go") )
        layout.addWidget( calc_btn )

        ## add a blank space
        space = fwid.add_label( " ", descr="" )
        layout.addWidget( space )

        ### Edit map part
        ## Name of the part
        edit_lab = fwid.add_label( "Edit cell Z position", descr="Edit the Z position of a cell parameters" )
        layout.addWidget( edit_lab )
        ## cell label choice
        celllab_line, self.cell_label = fwid.value_line( "Cell label:", 0, descr="Label of the cell to edit" )
        layout.addLayout( celllab_line )
        ## new position
        position_line, self.new_position = fwid.value_line( "New Z position:", 0, descr="New Z position to place the cell" )
        layout.addLayout( position_line )
        ## btn go for the cell
        poscell_btn = fwid.add_button( "Update selected cell position", self.update_cell_zpos, descr="Update the cell to the new Z position", color=ut.get_color("go") )
        layout.addWidget( poscell_btn )

        ## Space
        space2 = fwid.add_label( " ", descr="" )
        layout.addWidget( space2 )

        ## Save all button
        saveall_btn = fwid.add_button( "Save updated cells", self.save_all, descr="Save the current cell Z positions", color=ut.get_color("save") )
        ## finish button
        end_btn = fwid.add_button( "3D Position done", self.end_position, descr="Finish this step, save and close the panel", color=ut.get_color("done") )
        btn_line = fwid.double_button( saveall_btn, end_btn )
        layout.addLayout( btn_line ) 
        self.setLayout( layout )

        self.drawCells3D()
    
    def calculate_zmap( self ):
        """ recalculate the zmap and update cells positions """
        step_size = int( float(self.resolution.text() ) )
        window_size = int( float(self.localsize.text() ) )
        self.mig.updateCellsZPos( step_size=step_size, window_size=window_size, save=self.save_map.isChecked() )
        self.drawCells3D()
        ut.show_info("Cell Z positions updated")

    def drawCells3D(self):
        """ Draw the cells in 3D """
        ready = self.mig.cellsHaveZPos()
        if not ready:
            ## more than half the cells don't have Z position, so recompute it
            ut.show_info("Many cells don't have Z position yet, computing it")
            self.save_map.setChecked( False )
            self.calculate_zmap()
        cells3D = self.mig.getJunctionsImage3D()
        ut.remove_layer(self.viewer, "CellContours")
        layer = self.viewer.add_labels( cells3D, name="CellContours", blending="additive", scale=(self.mig.scaleZ, self.mig.scaleXY, self.mig.scaleXY) )

        @layer.mouse_drag_callbacks.append
        def clicks_label(layer, event):
            if event.type == "mouse_press":
                if len(event.modifiers) == 0:
                    if event.button == 2:
                        # right-click, select the label value
                        label = layer.get_value(position=event.position, view_direction = event.view_direction, dims_displayed=event.dims_displayed, world=True)
                        if label > 0:
                            self.cell_label.setText( str(label) )
                    return
                if "Control" in event.modifiers:
                    if event.button == 1:
                        ## Control left-click, set the z position
                        zpos = self.viewer.dims.current_step[0]
                        self.new_position.setText( str(zpos) )
                        self.update_cell_zpos()
                        return

    def update_cell_zpos(self):
        """ Update current cell to current z position """
        cell = int( self.cell_label.text() )
        zpos = int( self.new_position.text() )
        if (zpos >= 0) and (zpos < self.mig.get_image_shape(in2d=False)[0]):
            img = self.viewer.layers["CellContours"].data
            self.mig.updateCellZPos(cell, zpos, img)
            #self.viewer.layers["CellContours"].data = img
            self.viewer.layers["CellContours"].refresh()
            self.cell_label.setText( "0" )

    def save_all( self ):
        """ Save all updated cell positions """
        self.mig.save_results()
        self.cfg.addGroupParameter( "ZCells" )
        self.cfg.addParameter( "ZCells", "zmap_resolution", int( float(self.resolution.text()) ) )
        self.cfg.addParameter( "ZCells", "zmap_window_size", int( float(self.localsize.text()) ) )
        self.cfg.write_parameterfile()

    def end_position( self ):
        """ Finish and save this step """
        self.save_all()
        ut.remove_widget( self.viewer, "Cells in 3D" )
        ut.remove_layer( self.viewer, "CellContours" )
        ut.removeOverlayText( self.viewer )

"""
def preprocJunctions2D(imgjun):
    "" Preprocessing the projection (filters, denoising)""

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
"""