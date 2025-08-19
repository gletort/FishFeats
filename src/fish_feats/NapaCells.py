
import fish_feats.Utils as ut
import fish_feats.FishWidgets as fwid
import numpy as np
from qtpy.QtWidgets import QVBoxLayout, QWidget 

class Projection( QWidget ):
    """ Get the 2D projection (local) of the junctions image """

    def __init__( self, viewer, mig, cfg, separateFun, showCells, getChoices ):
        """ Interface to handle local projection """
        super().__init__()
        self.viewer = viewer
        self.mig = mig
        self.cfg = cfg
        self.show_cells = showCells
        self.get_choices = getChoices
        self.separate = separateFun
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
            self.separate()
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
        ut.remove_widget( self.viewer, "JunctionProjection2D" )
        self.go_segmentation()
    
    def go_segmentation( self ):
        """ Segmentation then correction of the apical junctions """
        ut.show_info("******** Segmentation of junctions 2D projection ******")
        get_cell = GetCells( self.viewer, self.mig, self.cfg, self.show_cells, self.get_choices )
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

    def __init__( self, viewer, mig, cfg, showCells, getChoices ):
        """ Interface to get the cell contours from the image """

        self.viewer = viewer
        self.mig = mig
        self.cfg = cfg
        self.junction_filename = None
        self.show_cells = showCells
        self.get_choices = getChoices

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
        filename_line, choose_filename, self.filename_label = fwid.label_button( "Choose file", self.get_junction_filename, label=self.junction_filename, descr="Choose a file with segmented junctions", color=None )
        filename_layout.addLayout( filename_line)
        self.file_group.setLayout( filename_layout )
        layout.addWidget( self.file_group )

        ## button to segment the cells
        segment_btn = fwid.add_button( "Segment cells", self.segment_cells, descr="Segment the cell contours from the image", color=ut.get_color("go") )
        layout.addWidget( segment_btn )
    
        self.methodsChoice.currentIndexChanged.connect( self.visibility )
        self.methodsChoice.setCurrentText( defmeth )
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

    def end_segmentation( self ):
        ut.removeOverlayText( self.viewer )
        ut.remove_widget( self.viewer, "Get junctions")
        self.correction_junctions()

    def correction_junctions( self ):
        """ Manual correction of segmentation step """
        maskview = self.viewer.add_labels( self.mig.junmask, blending='additive', scale=(self.mig.scaleXY, self.mig.scaleXY), name="Junctions" )
        maskview.contour = 3
        maskview.selected_label = 2
        self.show_cells( "Junctions", shapeName="JunctionsName", dim=2 )
        # saving and finishing
        endcells = EndCells( self.viewer, self.mig, self.cfg, self.get_choices )
        self.viewer.window.add_dock_widget( endcells, name="EndCells" )



    def segment_cells( self ):
        """ Segment the cell contours from the image """
        ut.showOverlayText( self.viewer, """Doing segmentation of cell junctions...""", size=15 )
        self.cfg.addGroupParameter("JunctionSeg")
        method = self.methodsChoice.currentText()
        self.cfg.addParameter("JunctionSeg", "method", method)
        self.cfg.addParameter("JunctionSeg", "cell_diameter", int(self.diameter.text()))
        self.cfg.addParameter("JunctionSeg", "chunk_size", self.chunksize)
        self.cfg.write_parameterfile()
        if method == "Load segmented file":
            self.mig.load_segmentation( self.junction_filename )
            self.end_segmentation()
        else:
            if "2DJunctions" in self.viewer.layers:
                roijunc = self.viewer.layers["2DJunctions"].data
                self.mig.do_segmentation_junctions( method, roijunc, int(self.diameter.text()), self.chunksize )
                self.end_segmentation()
            else:
                ut.show_info("No projected junctions to segment, go to projection")
                ut.remove_widget(self.viewer, "Segment cells")
                ut.remove_widget( self.viewer, "Get cells" )
                proj = Projection( self.viewer, self.mig, self.cfg )
                self.viewer.window.add_dock_widget( proj, name="JunctionProjection2D" )



class EndCells( QWidget ):
    """ Handle the finishing of cell contour edition """

    def __init__( self, viewer, mig, cfg, getChoices ):
        """ Interface to save/finish the cell edition option """

        self.viewer = viewer
        self.mig = mig
        self.cfg = cfg
        self.getChoices = getChoices
        
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
        self.getChoices( default_action = "Get nuclei" )
