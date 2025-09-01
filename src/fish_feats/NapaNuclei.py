
import fish_feats.Utils as ut
import fish_feats.FishWidgets as fwid
from fish_feats.NapaMix import Separation
import numpy as np
from qtpy.QtWidgets import QVBoxLayout, QWidget 
from napari.utils.translations import trans

class MeasureNuclei( QWidget ):
    """ Measure intensity inside segmented nuclei """

    def __init__( self, viewer, mig, cfg ):
        """ Interface to measure nuclear intensities """

        self.viewer = viewer
        self.mig = mig
        self.cfg = cfg
        self.results = None
        
        super().__init__()
        layout = QVBoxLayout()

        ## choose channel to measure
        chan_line, self.channel_spin = fwid.spinner_line( "Channel: ", 0, self.mig.nbchannels, 1, 0, changefunc=self.show_layer, descr="Choose which channel to measure" )
        layout.addLayout( chan_line )

        ## Go, measure
        measure_btn = fwid.add_button( "Measure", btn_func=self.go_measure, descr="Measure intensity in nuclei in selected channel" )
        layout.addWidget( measure_btn )

        ## show or save the results
        table_btn = fwid.add_button( "Show measure table", btn_func=self.show_results, descr="Open a window with the results table with all nuclei measured" )
        table_save_btn = fwid.add_button( "Save all nuclei measures", self.save_table, descr="Save a table file with the measure of ALL nuclei (even not associated)" )
        double_line = fwid.double_widget( table_btn, table_save_btn )
        layout.addLayout( double_line )

        
        ## Done, save and quit
        done_btn = fwid.add_button( "Save and stop", btn_func=self.done, descr="Add measurements to the Results file and quit the option", color=ut.get_color("done") )
        layout.addWidget( done_btn )

        self.setLayout( layout )

        text = "Measure intensity inside segmented nuclei \n"
        ut.showOverlayText( self.viewer, text )
        print("******** Measure nuclear intensity ******")

    def show_layer( self ):
        """ Change currently visible layer based on the current channel selection """
        for lay in self.viewer.layers:
            lay.visible = False 
        chan = self.channel_spin.value()
        if "originalChannel"+str(chan) in self.viewer.layers:
            self.viewer.layers["originalChannel"+str(chan)].visible = True

    def go_measure( self ):
        """ Do the intensity measurement """
        start_time = ut.get_time()
        pbar = ut.start_progress( self.viewer, total=None, descr="Measuring nuclei..." ) 
        chan = self.channel_spin.value()
        self.results = self.mig.measure_nuclear_intensity( chan )
        ut.show_info("Measure done")
        ut.close_progress( self.viewer, pbar )
        ut.show_duration( start_time, "Nuclear intensities measured in " )

    def save_table( self ):
        """ Save the results of all nuclei measures """
        if self.results is None:
            ut.show_warning("No measurement done yet")
            return
        chan = self.channel_spin.value()
        outname = self.mig.build_filename( "_allnuclei_C"+str(chan)+".csv" )
        ut.write_dict( outname, self.results )
        ut.show_info("Results saved in file "+str(outname))


    def show_results( self ):
        """ Show the table of resutls of all nuclei """
        if self.results is None:
            ut.show_warning("No measurement done yet")
            return
        ut.show_table( self.results )

    def done( self ):
        """ Save results and quit option """
        self.mig.save_results()
        ut.remove_widget( self.viewer, "Measure nuclei" )


#### Nuclei widget class
class NucleiWidget(QWidget):
    """ Widget to get nuclei options """

    def __init__( self, ffeats ):
        super().__init__()
        self.mig = ffeats.mig
        self.viewer = ffeats.viewer
        self.cfg = ffeats.cfg
        self.ffeats = ffeats

        ## Load default/configuration parameters
        self.load_parameters()
        self.nuclei_filename = self.mig.nuclei_filename(ifexist=True)
        if self.nuclei_filename is None:
            self.nuclei_filename = self.mig.resdir

        layout = QVBoxLayout()
        ## Method choice
        method_line, self.method_choice = fwid.list_line( "Method: ", descr="Choose method to get nuclei: load or segment", func=self.show_parameters_nuclei )
        layout.addLayout( method_line )

        ## Stardist parameters
        self.stardist_group, stardist_layout = fwid.group_layout( "Stardist parameters", descr="", color = ut.get_color("group1") )
        prob_line, self.stardist_probability_threshold = fwid.value_line( "Probability threshold: ", self.paras["Stardist_probability_threshold"], descr="Probability threshold to keep pixel in a nucleus (the lower the more/larger nuclei)" )
        stardist_layout.addLayout( prob_line )
        overlap_line, self.stardist_nuclei_overlap = fwid.value_line( "Nuclei overlap: ", self.paras["Stardist_nuclei_overlap"], descr="Overlap threshold to consider two nuclei as overlapping (the lower the more/larger nuclei)" )
        stardist_layout.addLayout( overlap_line )
        ##2D->3D association
        association_line, self.stardist_association_method = fwid.list_line( "3D reconstruction method: ", descr="Method to associate 2D Stardist nuclei into 3D nuclei in consecutive slices" )
        for method in ["Munkres", "Overlap"]:
            self.stardist_association_method.addItem( method )
        ind = self.stardist_association_method.findText( "Overlap" )
        if ind >= 0:
            self.stardist_association_method.setCurrentIndex( ind )
        stardist_layout.addLayout( association_line )
        distance_line, self.stardist_association_distance_limit_micron = fwid.value_line( "Max distance to associate (microns): ", self.paras["Stardist_association_distance_limit_micron"], descr="Distance limit to associate two 2D nuclei across consecutive slices" )
        stardist_layout.addLayout( distance_line )
        threshold_line, self.stardist_threshold_overlap = fwid.value_line( "Threshold overlap: ", self.paras["Stardist_threshold_overlap"], descr="Threshold to consider two nuclei as overlapping (high => small divided nuclei)" )
        stardist_layout.addLayout( threshold_line )
        self.stardist_group.setLayout( stardist_layout )
        layout.addWidget( self.stardist_group )
        
        ## CellPose3D parameters
        self.cp_detthreshold_div = 10
        self.cp_stitchthreshold_div = 100
        self.cellpose_group, cellpose_layout = fwid.group_layout( "CellPose3D parameters", descr="", color = ut.get_color("group2") )
        cp_diameter_line, self.cellpose_cell_diameter = fwid.value_line( "Cell diameter (pixels): ", self.paras["Cellpose_cell_diameter"], descr="Average diameter of the cells (in pixels)" )
        cellpose_layout.addLayout( cp_diameter_line )
        cp_detection_line, self.cellpose_detection_threshold = fwid.slider_line( "Detection threshold: ", minval=-6.0, maxval=6.0, step=0.2, value=self.paras["Cellpose_detection_threshold"], show_value=True, slidefunc=None, descr="Detection threshold for CellPose (the lower the more/larger nuclei)", div=self.cp_detthreshold_div )
        cellpose_layout.addLayout( cp_detection_line )
        self.cellpose_resample = fwid.add_check( "Resample: ",  checked=self.paras["Cellpose_resample"],
        check_func=None,
        descr="Resample CP output before to compute the cell contours (slower but more precise)" )
        cellpose_layout.addWidget( self.cellpose_resample )
        self.cellpose_in3D = fwid.add_check( "In 3D: ",  checked=self.paras["Cellpose_in3D"],
        check_func=None,
        descr="Use CellPose in 3D mode (XY, YZ, XZ), otherwise in 2D+stitching" )
        cellpose_layout.addWidget( self.cellpose_in3D )
        cp_stitch_line, self.cellpose_stitch_threshold = fwid.slider_line( "Stitching threshold: ", minval=0, maxval=1, step=0.01, value=self.paras["Cellpose_stitch_threshold"], show_value=True, slidefunc=None, descr="Threshold to stitch 2D CellPose nuclei into 3D nuclei (the lower the larger nuclei)", div=self.cp_stitchthreshold_div )
        cellpose_layout.addLayout( cp_stitch_line )

        ## dask line
        self.cellpose_dask = fwid.add_check( "Use dask with chunk size:", self.paras["Cellpose_dask"], None, descr="Use Cellpose-Dask version to compute faster or without memory issues" )
        self.cellpose_chunk_size = fwid.add_value( self.paras["Cellpose_chunk_size"], descr="Chunk size when using CellPose-dask" )
        dask_line = fwid.double_widget( self.cellpose_dask, self.cellpose_chunk_size )
        cellpose_layout.addLayout( dask_line )

        self.cellpose_group.setLayout( cellpose_layout )
        layout.addWidget( self.cellpose_group )

        ## Load segmented file parameters
        self.load_file_group, load_file_layout = fwid.group_layout( "Load segmented file", descr="Load a file with segmented nuclei", color = ut.get_color("group3") )
        filename_line, choose_filename, self.filename_label = fwid.label_button( "Choose file", self.get_nuclei_filename, label=self.nuclei_filename, descr="Choose a file with segmented nuclei", color=None )
        load_file_layout.addLayout( filename_line )
        self.load_file_group.setLayout( load_file_layout )
        layout.addWidget( self.load_file_group )

        go_line, go_btn = fwid.line_button_help( "Get nuclei",
            self.get_nuclei, 
            "Segment nuclei with CellPose3D/Stardist, or load a segmented file",
            help_link="Get-nuclei", 
            color = ut.get_color("go"),
            )
        layout.addLayout( go_line )
        for method in ["CellPose3D", "Stardist", "Load segmented file"]:
            self.method_choice.addItem( method )
        ind = self.method_choice.findText( self.defmeth )
        if ind >= 0:
            self.method_choice.setCurrentIndex( ind )
        self.show_parameters_nuclei()
        self.setLayout(layout)

    def get_nuclei_filename( self ):
        """ Open a file dialog to choose a file with segmented nuclei """
        filename = fwid.file_dialog( "Choose segmented nuclei file", "*.tif", directory=self.mig.resdir )
        if filename is not None:
            self.nuclei_filename = filename
            self.filename_label.setText(filename)

    def load_parameters( self ):
        """ Load default parameters and update from the configuration file """
        ## init/load parameters
        self.defmeth = "Stardist"
        self.paras = {}
        self.paras["Stardist_probability_threshold"] = 0.5
        self.paras["Stardist_nuclei_overlap"] = 0.1
        self.paras["Stardist_association_distance_limit_micron"] = 0.3
        self.paras["Stardist_threshold_overlap"] = 0.2
        self.paras["Cellpose_cell_diameter"] = 8
        self.paras["Cellpose_detection_threshold"] =0.0
        self.paras["Cellpose_resample"] = True 
        self.paras["Cellpose_in3D"] = True
        self.paras["Cellpose_dask"] = False 
        self.paras["Cellpose_stitch_threshold"] = 0.25
        self.paras["Cellpose_chunk_size"] = 1000
        load_paras = self.cfg.read_parameter_set("NucleiSeg")
        if load_paras is not None:
            float_paras = ["Cellpose_cell_diameter", 
                           "Cellpose_chunk_size",
                           "Cellpose_detection_threshold", "Cellpose_stitch_threshold", "Stardist_probability_threshold", "Stardist_threshold_overlap", "Stardist_nuclei_overlap", "Stardist_association_distance_limit_micron"]
            
            for cpara in float_paras:
                if cpara in load_paras:
                    self.paras[cpara] = float(load_paras[cpara])
            if "Cellpose_resample" in load_paras:
                self.paras["Cellpose_resample"] = load_paras["Cellpose_resample"].strip() == "True" 
            if "Cellpose_in3D" in load_paras:
                self.paras["Cellpose_in3D"] = load_paras["Cellpose_in3D"].strip() == "True" 
            if "Cellpose_dask" in load_paras:
                self.paras["Cellpose_dask"] = load_paras["Cellpose_dask"].strip() == "True" 
            if "method" in load_paras:
                self.paras["method"] = load_paras["method"]
                self.defmeth = load_paras["method"]
    
        if self.mig.nuclei_filename(ifexist=True) != "":
            self.defmeth = "Load segmented file"

    def show_parameters_nuclei( self ):
        """ Controls the visibility of paratemeters according to the method """
        self.stardist_group.setVisible( self.method_choice.currentText() == "Stardist" )
        self.cellpose_group.setVisible( self.method_choice.currentText() == "CellPose3D" )
        self.load_file_group.setVisible( self.method_choice.currentText() == "Load segmented file" )

    def nuclei_stardist( self ):
        """ Do segmentation with Stardist """
        self.viewer.text_overlay.text = trans._( """ Doing segmentation of cell nuclei with Stardist... \n Prepare nuclei image """ )
        self.cfg.addText("Segment nuclei with Stardist2D+3D association")
        self.cfg.addTextParameter( "Stardist", "probability_threshold", self.stardist_probability_threshold.text() )
        self.cfg.addTextParameter( "Stardist", "nuclei_overlap", self.stardist_nuclei_overlap.text() )
        self.cfg.addTextParameter( "Stardist", "association_distance_limit_micron", self.stardist_association_distance_limit_micron.text() )
        self.cfg.addTextParameter( "Stardist", "threshold_overlap", self.stardist_threshold_overlap.text() )
        self.mig.prepare_segmentation_nuclei()
        self.viewer.text_overlay.text = trans._( """ Doing segmentation of cell nuclei with Stardist... \n Do Stardist2D+assocation3D """ )
        self.go_segnuclei_stardist()
    
    def go_segnuclei_stardist( self ):
        """ Launch segmentation with StarDist """
        start_time = ut.get_time()
        pbar = ut.start_progress( self.viewer, total=None, descr="Segmenting with Stardist.." )
        self.mig.do_segmentation_stardist( float(self.stardist_probability_threshold.text() ), 
            float(self.stardist_nuclei_overlap.text()),
            self.stardist_association_method.currentText(), 
            float(self.stardist_association_distance_limit_micron.text()),
            float(self.stardist_threshold_overlap.text()) )
        if self.mig.nucmask is None:
            ut.close_progress( self.viewer, pbar )
            return
        self.end_segmentation_nuclei( start_time, pbar )

    
    def nuclei_cellpose( self ):
        """ Do segmentation with CellPose """
        self.viewer.text_overlay.text = trans._( """ Doing segmentation of cell nuclei with CellPose3D... \n Prepare nuclei image """ )
        self.mig.prepare_segmentation_nuclei()
        self.viewer.text_overlay.text = trans._( """ Doing segmentation of cell nuclei with CellPose3D... \n Doing Cellpose3D... """ )
        ## add parameters to the configuration file
        self.cfg.addText("Segment nuclei with CellPose 3D")
        self.cfg.addTextParameter( "CellPose", "cell_diameter", self.cellpose_cell_diameter.text() )
        self.cfg.addTextParameter( "CellPose", "detection_threshold", self.cellpose_detection_threshold.value()*1.0/self.cp_detthreshold_div )
        self.cfg.addTextParameter( "CellPose", "resample", self.cellpose_resample.isChecked())
        self.cfg.addTextParameter( "CellPose", "in3D", self.cellpose_in3D.isChecked() )
        self.cfg.addTextParameter( "CellPose", "dask", self.cellpose_dask.isChecked() )
        self.cfg.addTextParameter( "CellPose", "stitch_threshold", self.cellpose_stitch_threshold.value()*1.0/ self.cp_stitchthreshold_div )
        self.cfg.addTextParameter( "CellPose", "chunk_size", int(float(self.cellpose_chunk_size.text())) )
        self.go_segnuclei_cellpose()

    def go_segnuclei_cellpose( self):
        start_time = ut.get_time()
        pbar = ut.start_progress( self.viewer, total=None, descr="Segmenting with CellPose.." )
        self.mig.do_segmentation_cellpose( float(self.cellpose_cell_diameter.text()),
        float(self.cellpose_detection_threshold.value())/self.cp_detthreshold_div,
        self.cellpose_resample.isChecked(),
        self.cellpose_in3D.isChecked(),
        float(self.cellpose_stitch_threshold.value())/ self.cp_stitchthreshold_div,
         dask=self.cellpose_dask.isChecked(),
          chunk = int(float(self.cellpose_chunk_size.text())) )
        self.end_segmentation_nuclei( start_time, pbar )

    def load_segmentationfile_nuclei( self ):
        start_time = ut.get_time()
        pbar = ut.start_progress( self.viewer, total=None, descr="Loading nuclei file.." )
        self.mig.load_segmentation_nuclei( self.nuclei_filename )
        self.end_segmentation_nuclei( start_time, pbar )

    def get_nuclei( self ):
        """ Interface to choose parameters of 3d nuclei segmentation """
        ut.remove_layer( self.viewer, "segmentedNuclei" )
        self.cfg.addGroupParameter("NucleiSeg")
        self.cfg.addParameter( "NucleiSeg", "method", self.method_choice.currentText() )
        self.cfg.addParameter( "NucleiSeg", "Stardist_probability_threshold", self.stardist_probability_threshold.text() )
        self.cfg.addParameter( "NucleiSeg", "Stardist_nuclei_overlap", self.stardist_nuclei_overlap.text() )
        self.cfg.addParameter( "NucleiSeg", "Stardist_association_distance_limit_micron", 
            self.stardist_association_distance_limit_micron.text() )
        self.cfg.addParameter( "NucleiSeg", "Stardist_threshold_overlap", self.stardist_threshold_overlap.text() )
        self.cfg.addParameter( "NucleiSeg", "Cellpose_cell_diameter", self.cellpose_cell_diameter.text() )
        self.cfg.addParameter( "NucleiSeg", "Cellpose_detection_threshold", self.cellpose_detection_threshold.value()*1.0/self.cp_detthreshold_div )
        self.cfg.addParameter( "NucleiSeg", "Cellpose_resample", self.cellpose_resample.isChecked())
        self.cfg.addParameter( "NucleiSeg", "Cellpose_dask", self.cellpose_dask.isChecked())
        self.cfg.addParameter("NucleiSeg", "Cellpose_in3D", self.cellpose_in3D.isChecked() )
        self.cfg.addParameter( "NucleiSeg", "Cellpose_stitch_threshold", self.cellpose_stitch_threshold.value()*1.0/ self.cp_stitchthreshold_div )
        self.cfg.write_parameterfile()
        ut.removeOverlayText(self.viewer)

        if self.method_choice.currentText() == "Load segmented file":
            ut.show_info("Load nuclei from file "+str(self.nuclei_filename))
            self.load_segmentationfile_nuclei()
        else:
            if self.mig.should_separate():
                ut.show_info("Junctions and nuclei staining in the same channel, separate them first")
                separation = Separation( self.viewer, self.mig, self.cfg ) 
                self.viewer.window.add_dock_widget(separation, name="Separate")
            else:
                if self.method_choice.currentText() == "CellPose3D":
                    ut.showOverlayText( self.viewer, "Doing segmentation of cell nuclei...")
                    self.nuclei_cellpose()
                if self.method_choice.currentText() == "Stardist":
                    ut.showOverlayText( self.viewer, "Doing segmentation of cell nuclei...")
                    self.nuclei_stardist()


    def end_segmentation_nuclei( self, start_time, pbar ):
        """ Finished segmentation, go to manual correction step """
        ut.show_duration( start_time, "Nuclei segmentation/loading took " )
        ut.close_progress( self.viewer, pbar )
        ut.removeOverlayText(self.viewer)
        ut.remove_widget(self.viewer, "Get nuclei")
        self.correction_nuclei()

    def correction_nuclei( self ):
        """ Allows manual correction of the segmentation """
        ut.show_info("Correct nuclei segmentation if necessary")
        #self.viewer.add_image( self.mig.nucstain, name="nucleiStaining", scale=( self.mig.scaleZ,self.mig.scaleXY,self.mig.scaleXY), blending="additive" )
        maskview = self.viewer.add_labels( self.mig.nucmask, blending='additive', scale=( self.mig.scaleZ, self.mig.scaleXY, self.mig.scaleXY ), name="segmentedNuclei" )
        maskview.n_edit_dimensions = 3
        maskview.contour = 0
        filter_nuclei = FilterNuclei( self.viewer, self.mig, self.cfg )
        self.viewer.window.add_dock_widget( filter_nuclei, name="Filtering" )
        self.ffeats.showCellsWidget("segmentedNuclei", shapeName="NucleiName", dim=3)
        finish_nuc = FinishNuclei( self.viewer, self.mig, self.cfg )
        self.viewer.window.add_dock_widget( finish_nuc, name="End nuclei" )

class FilterNuclei( QWidget ):
    """ Filter to remove/correct nuclei segmentation """

    def __init__( self, viewer, mig, cfg ):
        """ Interface to filter nuclei options """
        
        self.viewer = viewer
        self.mig = mig
        self.cfg = cfg
    
        paras = self.cfg.read_parameter_set("FilterNuclei")
        minvol = 50.0
        keepnz = 5
        rmsmall = True
        if paras is not None:
            if "minimum_volume" in paras:
                minvol = float(paras["minimum_volume"])
            if "keep_ifatleast_z" in paras:
                keepnz = int(paras["keep_ifatleast_z"])
            if "remove_small_nuclei" in paras:
                rmsmall = paras["remove_small_nuclei"].strip() == True
        
        super().__init__()
        layout = QVBoxLayout()

        ## remove small nuclei
        self.remove_small = fwid.add_check( "Remove nuclei smaller than ", rmsmall, None, descr="If checked, nuclei smaller than given threshold will be removed" )
        self.size_threshold = fwid.add_value( minvol, descr="Minimum volume (in pixels) to keep a nucleus" )
        small_line = fwid.double_widget( self.remove_small, self.size_threshold )
        layout.addLayout( small_line )

        ## keep if mim nb of Z
        nbline, self.min_nb_z = fwid.value_line( "Min nb of Z in nucleus", keepnz, descr="Keep only nuclei that are present in more Z slices than the minimal number" )
        layout.addLayout( nbline )

        ## Go
        go_btn = fwid.add_button( "Update nuclei", self.go_filter, descr="Filter nuclei based on current parameters" )
        layout.addWidget( go_btn )
        self.setLayout( layout )

    def go_filter( self ):
        """ Apply the filtering """
        if not self.remove_small.isChecked():
            mvol = -1
        else:
            mvol = int(float(self.size_threshold.text()))

        print("--- Filtering nuclei ---")
        start_time = ut.get_time()
        pbar = ut.start_progress( self.viewer, total=None, descr="Filtering nuclei..." )
        self.mig.filterNuclei( mvol, (float(self.min_nb_z.text())) )
        ut.close_progress( self.viewer, pbar )
        ut.show_duration( start_time, "Nuclei filtered took ")

        self.cfg.addGroupParameter("FilterNuclei")
        self.cfg.addParameter("FilterNuclei", "minimum_volume", (float(self.size_threshold.text())) )
        self.cfg.addParameter( "FilterNuclei", "keep_ifatleast_z", int(float(self.min_nb_z.text())) )
        self.cfg.addParameter("FilterNuclei", "remove_small_nuclei", self.remove_small.isChecked() )
        self.cfg.write_parameterfile()


class FinishNuclei( QWidget ):
    """ Filter to remove/correct nuclei segmentation """

    def __init__( self, viewer, mig, cfg ):
        """ Interface to filter nuclei options """
        
        self.viewer = viewer
        self.mig = mig
        self.cfg = cfg
    
        super().__init__()
        layout = QVBoxLayout()

        ## save button
        save_btn = fwid.add_button( "Save nuclei", self.save_nuclei, descr="Save the current nuclei segmentation", color=ut.get_color("save") )
        ## done btn
        done_btn = fwid.add_button( "Nuclei done", self.nuclei_done, descr="Finish this step, close everything related", color=ut.get_color("done") )
        line = fwid.double_widget( save_btn, done_btn )
        layout.addLayout( line )

        self.setLayout( layout )

    def save_nuclei( self ):
        """ Save the current segmentation of nuclei to file """
        if 'segmentedNuclei' in self.viewer.layers:
            outname = self.mig.nuclei_filename(ifexist=False)
            self.mig.save_image( self.viewer.layers["segmentedNuclei"].data, outname, hasZ=True )

    def nuclei_done( self ):
        """ Finish the nuclei editing step, close everything """
        ut.remove_layer( self.viewer,"nucleiStaining" )
        ut.remove_layer( self.viewer,"segmentedNuclei" )
        ut.remove_layer( self.viewer,"NucleiName" )
        ut.removeOverlayText( self.viewer )
        #addText("")
        ut.remove_widget(self.viewer, "Filtering")
        ut.remove_widget(self.viewer, "CellPose3D")
        ut.remove_widget(self.viewer, "Stardist")
        ut.remove_widget(self.viewer, "Edit labels")
        ut.remove_widget(self.viewer, "End nuclei")



class PreprocessNuclei( QWidget ):
    """ Preprocessing of the 3D nuclei (filters, denoising) """

    def __init__( self, viewer, mig, cfg ):
        self.viewer = viewer
        self.mig = mig
        self.cfg = cfg
        super().__init__()
    
        print("********** Preprocessing nuclei signal *************")
        ## load default parameters
        rm_bg = False
        rm_bg_rad = 20
        medfilt = False
        medfilt_rad = 4
        paras = self.cfg.read_parameter_set("PreprocessNuclei")
        if paras is not None:
            if "remove_background" in paras:
                rm_bg = (paras["remove_background"].strip() == "True")
            if "median_filter" in paras:
                medfilt = (paras["median_filter"].strip() == "True")
            if "remove_background_radius" in paras:
                rm_bg_rad = int(paras["remove_background_radius"])
            if "median_filter_radius" in paras:
                medfilt_rad = int(paras["median_filter_radius"])

        layout = QVBoxLayout()
        ## median filtering option
        median_line, self.median_filtering, self.median_radius = fwid.check_value_line( "Median filtering", medfilt, "with radius ", medfilt_rad, descr="Apply median filtering to the nuclei raw image with the given radius" ) 
        layout.addLayout( median_line )
        ## remove background option
        bg_line, self.remove_background, self.remove_background_radius = fwid.check_value_line( "Remove background", rm_bg, "with radius ", rm_bg_rad, descr="Remove background with a rolling ball algorithm with the given radius" )
        layout.addLayout( bg_line )

        ## go preprocess
        apply_btn = fwid.add_button( "Apply preprocessing", btn_func=self.preprocess_go, descr="Apply the selected preprocessing steps", color=ut.get_color("go") )
        layout.addWidget( apply_btn )
        
        ## noise2void btn
        self.noise2void = fwid.add_button( "Noise2Void", self.noise2void_show, descr="Apply Noise2Void denoising" )
        self.end_n2v = fwid.add_button( "Noise2void done", self.noise2void_close, descr="Finish the noise2void step and go back to preprocessing", color=ut.get_color("done") )
        n2v_line = fwid.double_widget( self.noise2void, self.end_n2v )
        layout.addLayout( n2v_line )

        ## reset staining btn
        reset_btn = fwid.add_button( "Reset nuclei staining", btn_func=self.reset_nuclei, descr="Reset the nuclei staining to the original raw image", color=ut.get_color("reset") )
        ## done button
        done_btn = fwid.add_button( "Preprocessing done", btn_func=self.preprocess_done, descr="Finish the nuclei preprocessing", color=ut.get_color("done") )
        btn_line = fwid.double_widget( reset_btn, done_btn )
        layout.addLayout( btn_line )

        self.setLayout( layout )
    
        self.mig.prepare_segmentation_nuclei()
        ut.remove_layer( self.viewer, "nucleiStaning" )
        self.viewer.add_image( self.mig.nucstain, name="nucleiStaining", blending="additive", scale=(self.mig.scaleZ, self.mig.scaleXY, self.mig.scaleXY), colormap="blue" )
        ut.hide_color_layers( self.viewer, self.mig )

    def preprocess_go( self ):
        """ Launch the preprocessing steps """
        print("Applying preprocessing")
        self.cfg.addGroupParameter("PreprocessNuclei")
        self.cfg.addParameter("PreprocessNuclei", "remove_background_radius", int(float(self.remove_background_radius.text())))
        self.cfg.addParameter("PreprocessNuclei", "median_filter_radius", int(float(self.median_radius.text())))
        self.cfg.addParameter("PreprocessNuclei", "remove_background", self.remove_background.isChecked())
        self.cfg.addParameter("PreprocessNuclei", "median_filter", self.median_filtering.isChecked())
        self.cfg.write_parameterfile()

        if self.remove_background.isChecked():
            self.mig.preprocess_nuclei_removebg( int(float(self.remove_background_radius.text())) )
        if self.median_filtering.isChecked():
            self.mig.preprocess_nuclei_median( int(float(self.median_radius.text())) )

        ut.remove_layer( self.viewer, "nucleiStaining" )
        self.viewer.add_image( self.mig.nucstain, name="nucleiStaining", blending="additive", scale=(self.mig.scaleZ, self.mig.scaleXY, self.mig.scaleXY), colormap="blue" )
        print("Preprocessing applied")

    def noise2void_show( self ):
        """ Opens noise2void plugin """
        self.mig.prepare_nuclei()
        try:
            from napari_n2v import PredictWidgetWrapper
            self.viewer.window.add_dock_widget(PredictWidgetWrapper(self.viewer))
        except ImportError:
            ut.show_error("Please install napari-n2v to use this feature.")

    def noise2void_close( self ):
        """ Closes noise2void plugin """
        if "Denoised" in self.viewer.layers:
            ut.remove_widget(self.viewer, "Dock widget 1")
            ut.remove_layer(self.viewer, "nucleiStaining")
            self.viewer.layers["Denoised"].name = "nucleiStaining"
            self.mig.nucstain = self.viewer.layers["nucleiStaining"].data
        if "nucleiStaining" in self.viewer.layers:
            self.viewer.layers["nucleiStaining"].refresh()

    def reset_nuclei( self ):
        ut.show_info("Reset nuclei staining")
        self.mig.nucstain = None
        self.mig.prepare_segmentation_nuclei()
        ut.remove_layer( self.viewer, "nucleiStaining" )
        self.viewer.add_image( self.mig.nucstain, name="nucleiStaining", blending="additive", scale=(self.mig.scaleZ, self.mig.scaleXY, self.mig.scaleXY), colormap="blue" )

    def preprocess_done( self ):
        """ Finish the step """
        ut.remove_layer(self.viewer, "nucleiStaining")
        self.noise2void_close()
        ut.remove_widget( self.viewer, "Preprocess Nuclei" )


