from qtpy.QtWidgets import QPushButton, QHBoxLayout, QVBoxLayout, QWidget, QGroupBox, QCheckBox, QSpinBox, QSlider, QDoubleSpinBox, QLabel, QComboBox, QLineEdit, QFileDialog, QTabWidget, QListWidget, QAbstractItemView
from qtpy.QtCore import Qt
import fish_feats.Utils as ut
import fish_feats.FishWidgets as fwid
import os 
import numpy as np
from magicgui.widgets import Table
import time

def unremove(layer):
    ut.show_info("Removing layer locked, throw an error ")
    return

def unmove_selection(layer, selection, coord):
    return

class NapaRNA():
    """ Main interface for RNA options in Napari """

    def __init__(self, viewer, mig, cfg):
        """ Initialize widget """
        self.viewer = viewer
        self.mig = mig
        self.cfg = cfg
        
        print("********** Detecting/Counting RNAs ********")
        text = "Choose RNA channel to segment/assign \n"
        text += "RNA can be detected using Big-Fish or loaded from previous file \n"
        text += "Segmented RNA are all non assigned (label=1), assigned RNA are colored by their label = assigned cell \n"
        ut.showOverlayText(viewer, text)
        paras = {}
        for chan in range(self.mig.nbchannels):
            self.viewer.layers["originalChannel"+str(chan)].visible = False
            paras = self.load_RNA_parameters(chan, paras)
    
        rnachannel = self.mig.free_channel()
        defmeth = "Segment with BigFish"
        rnafilename = self.mig.rna_filename(rnachannel, how=".csv", ifexist=True)
        if rnafilename == "":
            rnafilename = self.mig.rna_filename(rnachannel, how=".tif", ifexist=True)
        if rnafilename != "":
            defmeth = "Load segmented file"

        ## add main interface
        self.rna_wid = MainRNA( viewer, mig, cfg, rnachannel, defmeth, rnafilename, paras)
        viewer.window.add_dock_widget( self.rna_wid, name="RNAs" )
    

    def load_RNA_parameters(self, channel, paras):
        """ default or loaded RNA parameters """
        paras["RNA"+str(channel)+"_spotZRadiusNm"] = 1000
        paras["RNA"+str(channel)+"_spotXYRadiusNm"] = 250
        paras["RNA"+str(channel)+"_removeSpotInExtremeZ"] = True
        #paras["RNA"+str(channel)+"_drawing_spot_size"] = 3
        paras["RNA"+str(channel)+"_threshold"] = self.mig.get_rna_threshold(channel)
        paras["RNA"+str(channel)+"_automatic_threshold"] = True
        paras["RNA_spot_disp_size"] = 30
    
        load_paras = self.cfg.read_parameter_set("RNA"+str(channel))
        if load_paras is not None:
            intvars = ["RNA"+str(channel)+"_spotZRadiusNm", "RNA"+str(channel)+"_spotXYRadiusNm", "RNA"+str(channel)+"_drawing_spot_size"]
            for var in intvars:
                if var in load_paras:
                    paras[var] = int(float(load_paras[var]))
            var = "RNA"+str(channel)+"_threshold"
            if var in load_paras:
                paras[var] = float(load_paras[var])
            var = "RNA"+str(channel)+"_automatic_threshold"
            if var in load_paras:
                paras[var] = load_paras[var].strip() == "True"
            var = "RNA"+str(channel)+"_removeSpotInExtremeZ"
            if var in load_paras:
                paras[var] = load_paras[var].strip() == "True"
        load_paras_gen = self.cfg.read_parameter_set("RNAs")
        if load_paras_gen is not None:
            var = "RNA_spot_disp_size"
            if var in load_paras_gen:
                paras[var] = int(float(load_paras_gen[var]))
        return paras


class GetRNA(QWidget):
    """ Get (segment or load) one RNA channel - Interface to choose options """

    def __init__( self, napari_viewer, parameters, nchan, mig, cfg, defmethod, rnafilename, main ):
        super().__init__()
        self.viewer = napari_viewer
        self.mig = mig
        self.cfg = cfg
        self.rnachannel = nchan
        self.paras = parameters
        self.main = main
        #self.index_assign = None
        self.index_edit = None
        self.edition = None
        self.measure_intensity = None
        ## define interface
        layout = QVBoxLayout()
        
        ## Choose rna channel to process
        lay_chan = QHBoxLayout()
        chan_lab = QLabel()
        chan_lab.setText("RNA channel")
        lay_chan.addWidget(chan_lab)
        self.nchan = QSpinBox()
        self.nchan.setMinimum(0)
        self.nchan.setMaximum(self.mig.nbchannels-1)
        self.nchan.setSingleStep(1)
        self.nchan.setValue(self.rnachannel)
        lay_chan.addWidget(self.nchan)
        layout.addLayout(lay_chan)

        ## Choose segmentation/loading method
        self.method = QComboBox()
        layout.addWidget(self.method)
        methods = ["Load segmented file", "Segment with BigFish"]
        for i in range(len(methods)):
            self.method.addItem(methods[i])
        self.method.setCurrentIndex(methods.index(defmethod))

        ## Loading file options
        self.widget_loading = QGroupBox("Loading RNA file")
        loading_layout = QVBoxLayout()
        filelayout = QHBoxLayout()
        file_lab = QLabel()
        file_lab.setText("Load file:")
        filelayout.addWidget(file_lab)
        self.filename = QLineEdit()
        self.filename.setText(rnafilename)
        filelayout.addWidget(self.filename)
        browse = QPushButton("Browse", parent=self)
        filelayout.addWidget(browse)
        browse.clicked.connect(self.load_file)
        loading_layout.addLayout(filelayout)
        self.widget_loading.setLayout(loading_layout)
        layout.addWidget(self.widget_loading)

        ## BigFish options
        self.widget_bigfish = QGroupBox("Segment with BigFish")
        bigfish_layout = QVBoxLayout()
        ## spot z radius
        spotz_line = QHBoxLayout()
        spotz_lab = QLabel()
        spotz_lab.setText("Spot Z radius (nm):")
        spotz_line.addWidget(spotz_lab)
        self.spotz_radius = QLineEdit()
        self.spotz_radius.setText(str(self.paras["RNA"+str(self.rnachannel)+"_spotZRadiusNm"]))
        spotz_line.addWidget(self.spotz_radius)
        bigfish_layout.addLayout(spotz_line)
        ## spot xy radius
        spotxy_line = QHBoxLayout()
        spotxy_lab = QLabel()
        spotxy_lab.setText("Spot X,Y radius (nm):")
        spotxy_line.addWidget(spotxy_lab)
        self.spotxy_radius = QLineEdit()
        self.spotxy_radius.setText(str(self.paras["RNA"+str(self.rnachannel)+"_spotXYRadiusNm"]))
        spotxy_line.addWidget(self.spotxy_radius)
        bigfish_layout.addLayout(spotxy_line)
        ## big-fish threshold 
        threshold_line = QHBoxLayout()
        threshold_lab = QLabel()
        threshold_lab.setText("Threshold:")
        threshold_line.addWidget(threshold_lab)
        self.threshold = QLineEdit()
        self.threshold.setText(str(self.paras["RNA"+str(self.rnachannel)+"_threshold"]))
        threshold_line.addWidget(self.threshold)
        self.automatic_threshold = QCheckBox("Automatic")
        self.automatic_threshold.setChecked(True)
        self.threshold.setEnabled(False)
        self.automatic_threshold.stateChanged.connect(self.autothres_changed)
        threshold_line.addWidget(self.automatic_threshold)
        
        bigfish_layout.addLayout(threshold_line)

        self.remove_extrem = QCheckBox("Remove spots in extremes Z")
        self.remove_extrem.setChecked(False)
        bigfish_layout.addWidget(self.remove_extrem)

        self.widget_bigfish.setLayout(bigfish_layout)
        layout.addWidget(self.widget_bigfish)

        ## Actions when parameters are changed
        self.method.currentIndexChanged.connect(self.method_choice)
        self.nchan.valueChanged.connect(self.channel_choice)
        self.method_choice()
        self.channel_choice()

        btn_go = QPushButton("Get RNA channel", parent=self)
        layout.addWidget(btn_go)
        btn_go.clicked.connect(self.go_rna)
        self.setLayout(layout)

    def autothres_changed(self):
        """ Update interface when automatic threshold option is changed """
        self.threshold.setText(str(self.mig.get_rna_threshold(self.rnachannel)))
        self.threshold.setEnabled(not self.automatic_threshold.isChecked())

    def load_file(self):
        """ Select file to load containing segmented/assigned RNA """
        cdir = os.path.dirname(self.filename.text())
        fileName = QFileDialog.getOpenFileName(self,
    "Choose RNA file", cdir, "RNA Files (*.tif *.csv)")
        self.filename.setText(fileName[0])

    def go_rna(self):
        """ Start processing RNA channel with current selected parameters """

        ## if RNA edition is open, refuse to work
        if self.rnachannel in self.main.edition:
            ut.show_warning( "RNA "+str(self.rnachannel)+" edition is already open, finish and close it before")
            return
        ut.remove_layer( self.viewer, "assignedRNA"+str(self.rnachannel) ) 
        
        self.cfg.addGroupParameter("RNA"+str(self.rnachannel))
        self.cfg.addParameter("RNA"+str(self.rnachannel), "RNA"+str(self.rnachannel)+"_method", self.method.currentText())
        self.cfg.addParameter( "RNA"+str(self.rnachannel), "RNA"+str(self.rnachannel)+"_spotZRadiusNm", int(self.spotz_radius.text()) )
        self.cfg.addParameter( "RNA"+str(self.rnachannel), "RNA"+str(self.rnachannel)+"_spotXYRadiusNm", int(self.spotxy_radius.text()) )
        self.cfg.addParameter( "RNA"+str(self.rnachannel), "RNA"+str(self.rnachannel)+"_threshold", float(self.threshold.text()) )
        self.cfg.addParameter( "RNA"+str(self.rnachannel), "RNA"+str(self.rnachannel)+"_removeSpotInExtremeZ", self.remove_extrem.isChecked() )
        #cfg.addParameter( "RNA"+str(rna_channel), "RNA"+str(rna_channel)+"_drawing_spot_size", drawing_spot_size )
        self.cfg.addParameter( "RNA"+str(self.rnachannel), "RNA"+str(self.rnachannel)+"_automatic_threshold", self.automatic_threshold.isChecked() )
        self.cfg.addGroupParameter("RNAs")
        self.cfg.addParameter( "RNAs", "RNA_spot_disp_size", self.main.spot_disp_size )
        self.cfg.write_parameterfile()
        
        start_time = ut.get_time()
        pbar = ut.start_progress( self.viewer, total=2, descr="Getting RNA, drawing cells in 3D and segment" )
        if self.method.currentText() == "Segment with BigFish":
            ut.showOverlayText(self.viewer, "Doing segmentation of RNA points in channel "+str(self.rnachannel)+"..." )
            rna_channel = self.rnachannel
            ut.show_layer(self.viewer, rna_channel)
            if ("assignedRNA"+str(rna_channel)) in self.viewer.layers:
                self.viewer.layers.remove("assignedRNA"+str(rna_channel))
                ut.remove_widget(self.viewer, "Save RNA"+str(rna_channel))
            thresh = float(self.threshold.text())
            if thresh <= 0.0:
                thresh = None
            if self.automatic_threshold.isChecked():
                thresh = None
            print("------- Segmenting RNA "+str(rna_channel)+" with big-fish ------ ")
            self.segment_rna(thresh)
            pbar.update(1)
        else:
            self.main.add_cell_contours()
            pbar.update(1)
            print("-------- Loading segmented/assigned RNA "+str(self.rnachannel)+" from file -------")
            self.load_segmentationfile_rna()
        ut.close_progress( self.viewer, pbar )
        ut.show_duration( start_time, "RNAs loaded/segmented in " )

    def channel_choice(self):
        """ Update the parameters in the interface for the selected channel """
        self.rnachannel = self.nchan.value()
        rnafilename = self.mig.rna_filename(self.rnachannel, how=".csv", ifexist=True)
        if rnafilename == "":
            rnafilename = self.mig.rna_filename(self.rnachannel, how=".tif", ifexist=True)
        self.filename.setText(rnafilename)
        self.spotz_radius.setText(str(self.paras["RNA"+str(self.rnachannel)+"_spotZRadiusNm"]))
        self.spotxy_radius.setText(str(self.paras["RNA"+str(self.rnachannel)+"_spotXYRadiusNm"]))
        self.threshold.setText(str(self.paras["RNA"+str(self.rnachannel)+"_threshold"]))
        self.automatic_threshold.setChecked( self.paras["RNA"+str(self.rnachannel)+"_automatic_threshold"] )
        self.remove_extrem.setChecked( self.paras["RNA"+str(self.rnachannel)+"_removeSpotInExtremeZ"] )
        #self.drawing_spot_size.value = paras["RNA"+str(self.rnachannel)+"_drawing_spot_size"]

    def method_choice(self):
        """ Change visibility of parameters according to current selected method """
        self.widget_loading.setVisible(self.method.currentText() == "Load segmented file")
        self.widget_bigfish.setVisible(self.method.currentText() == "Segment with BigFish")


    def load_segmentationfile_rna(self ):
        """ Load segmented RNA file """
        self.mig.load_rnafile(self.filename.text(), self.rnachannel, topop=False)
        self.end_segmented_rna()

    def segment_rna(self, threshold):
        chanel = self.rnachannel
        start_time = time.time()
        self.mig.find_rna( self.rnachannel, int(self.spotz_radius.text()), int(self.spotxy_radius.text()), self.remove_extrem.isChecked(), threshold )
        print("RNA big-fish segmentation finished in {:.3f}".format((time.time()-start_time)/60)+" min")
        self.end_segmented_rna()

    def end_segmented_rna(self):
        """ Create points from segmented spots and call editing/assignement widget """
        nchan = self.rnachannel 
        #ut.removeOverlayText(self.viewer)
        spots, labs, scores = self.mig.get_spots(nchan)
        points = np.array(spots)
        labels = np.array(labs, dtype="int")
        scores = np.array(scores, dtype="float")
        unassigned = (labels==-1) + (labels==1)
        labels[unassigned] = 1
        point_properties = { 'label': labels, 'score':scores, 'unassigned': unassigned, 'intensity': np.array([0.0]*len(labs)) }
        fcolor = []
        if "CellContours" in self.viewer.layers:
            for lab in labels:
                fcolor.append( self.viewer.layers["CellContours"].get_color(lab) )
        else:
            fcolor = "white"

        size = self.main.spot_disp_size
        ut.add_point_layer( self.viewer, points, fcolor, layer_name="assignedRNA"+str(nchan), mig=self.mig, size=size, pts_properties=point_properties ) 
        ut.view_3D( self.viewer )
    
        self.main.go_edition( self.rnachannel )
        self.main.go_measure_intensity( self.rnachannel )
    

    def finish_assign(self):
        """ Close the assign/edit tabs """
        #if self.index_edit is not None:
        #    self.tabs.removeTab(self.index_edit)
        #if self.index_assign is not None:
        #    self.tabs.removeTab(self.index_assign)
        self.edition = None
        self.measure_intensity = None


class PointEditing(QWidget):
    """ Handle RNA assignement + manual correction of RNA segmentation and assignement """

    def __init__(self, chan, viewer, mig, cfg, main):
        super().__init__()
        self.viewer = viewer
        self.channel = chan
        self.mig = mig
        self.cfg = cfg
        self.main = main
        paras = self.cfg.read_parameter_set("RNA"+str(self.channel)+"_Assignement")
        layout = QVBoxLayout()
        disp_settings = {}
        disp_settings["Help button"] = ut.get_color("help")
        disp_settings["auto"] = ut.get_color("group1")
        disp_settings["group2"] = ut.get_color("group2")
        disp_settings["group3"] = ut.get_color("group3")
        ## Assignement options
        auto_line, auto_cbox, self.group_assign = fwid.checkgroup_help( "Automatic assignement", False, "Show/hide automatic assignement options", "Get-rnas", display_settings=disp_settings, groupnb="auto" )
        self.point_editing(paras)
        layout.addLayout( auto_line )
        layout.addWidget( self.group_assign )
        ## Correction options
        corr_line, group_cbox, self.group_correction = fwid.checkgroup_help( "Point correction", False, "Show/hide RNA correction options", "Get-rnas", display_settings=disp_settings, groupnb="group2" )
        self.interface_corrections()
        layout.addLayout( corr_line )
        layout.addWidget( self.group_correction )
        ## Display options
        disp_line, group_cbox_disp, self.group_display = fwid.checkgroup_help( "Point display", False, "Show.hide options to change points display", "Get-rnas", display_settings=disp_settings, groupnb="group3" )
        self.interface_display()
        layout.addLayout( disp_line )
        layout.addWidget( self.group_display )
        
        ## Save/finish the current RNA
        btn_draw_counts = fwid.add_button( "Draw RNA "+str(self.channel)+" counts", self.draw_rna_counts, "Create a new layer containing the cells colored by their number of assigned RNAs" )
        btn_save_draw = fwid.add_button( "Save drawn RNA "+str(self.channel)+" counts", self.save_draw_rna_counts, "Save the layer CountsRNA"+str(self.channel)+" if it was created" )
        fline = fwid.double_button( btn_draw_counts, btn_save_draw )
        layout.addLayout(fline)
        btn_finish_rna = fwid.add_button( "Save and quit RNA "+str(self.channel)+"", self.finish_rna, "RNA assignement is finished, close this panel", color=ut.get_color("done") )
        layout.addWidget( btn_finish_rna )

        self.setLayout(layout)
        self.active_shortcuts()
        self.show_help_text()
        funcType = type(self.layerrna._move)
        self.layerrna._move = funcType(unmove_selection, self.layerrna)
        #self.viewer.layers.events.removing.connect(lambda event: unremove(self.layerrna))


    def interface_corrections(self):
        """ RNA segmentation/assignement manual correction parameters """
        group_correction_layout = QVBoxLayout()

        ## parameters of cell to assign to
        tocell_line = QHBoxLayout()
        tocell_lab = QLabel()
        tocell_lab.setText("Assign selected points to cell:")
        tocell_line.addWidget(tocell_lab)
        self.assign_tocell = QLineEdit()
        self.assign_tocell.setText("2")
        tocell_line.addWidget(self.assign_tocell)
        group_correction_layout.addLayout(tocell_line)
        sc_lab = QLabel()
        sc_lab.setText( "<Right-click> on a cell to get to its value" )
        group_correction_layout.addWidget(sc_lab)
        ## go assign current points
        btn_assign_selected = QPushButton("Assign selected points", parent=self)
        group_correction_layout.addWidget(btn_assign_selected)
        btn_assign_selected.clicked.connect(self.assign_selected2cell)
        scn_lab = QLabel()
        scn_lab.setText( "<c> to assign selected points" )
        group_correction_layout.addWidget(scn_lab)
        self.group_correction.setLayout( group_correction_layout )

        
    def interface_display(self):
        """ RNA display parameters """
        ## Points display parameters
        disp_layout = QVBoxLayout()

        ## Dislay size of the point
        line = QHBoxLayout()
        ## Add the name of the slider
        lab = QLabel()
        lab.setText( "Display point size" )
        lab.setToolTip( "Change the displayed size of all the RNA points" )
        line.addWidget( lab )
        ## Ranged-value widget
        self.display_size = QSlider( Qt.Horizontal )
        self.display_size.setMinimum( 1 )
        self.display_size.setMaximum( 100 )
        self.display_size.setSingleStep( 1 ) 
        self.display_size.setValue( self.main.spot_disp_size )
        line.addWidget( self.display_size )
        disp_layout.addLayout( line )
        self.display_size.valueChanged.connect( self.change_display_size )

        ## choice of display mode
        displaymode_line = QHBoxLayout()
        displaymode_lab = QLabel("Point size from: ")
        displaymode_line.addWidget(displaymode_lab)
        self.display_mode = QComboBox()
        self.display_mode.setToolTip( "Display only points whose value is within a selected range" )
        displaymode_line.addWidget(self.display_mode)
        disp_layout.addLayout(displaymode_line)
        
        self.display_mode.addItem("None (all same size)")
        
        ## Choose range of scores to display
        self.display_mode.addItem("assignement score")
        self.display_score_layout()
        disp_layout.addWidget(self.score_range_group)
        
        ## Choose range of intensities to display
        self.display_mode.addItem("point intensity")
        self.display_intensity_layout()
        disp_layout.addWidget(self.intensity_range_group)

        ## set visibility of displaying mode interfaces
        self.display_mode.currentIndexChanged.connect(self.display_mode_selected)
        self.display_mode_selected()

        ## reset display: show all the points colored by cell label
        btn_reset = QPushButton("Reset point display", parent=self)
        btn_reset.clicked.connect(self.reset_display)
        disp_layout.addWidget(btn_reset)
        self.group_display.setLayout( disp_layout )

    def display_mode_selected(self):
        """ Set visibility of display mode interfaces from current selection """
        self.score_range_group.setVisible( self.display_mode.currentText() == "assignement score")
        self.intensity_range_group.setVisible( self.display_mode.currentText() == "point intensity")

    def display_intensity_layout(self):
        """ Interface for display point by intensity """
        self.intensity_range_group = QGroupBox("Intensity")
        intensity_layout = QVBoxLayout()
        
        ## Choose channel to measure intensity
        lay_chan = QHBoxLayout()
        chan_lab = QLabel()
        chan_lab.setText("Intensity channel")
        lay_chan.addWidget(chan_lab)
        self.nchan = QSpinBox()
        self.nchan.setMinimum(0)
        self.nchan.setMaximum(self.mig.nbchannels-1)
        self.nchan.setSingleStep(1)
        self.nchan.setValue(self.channel)
        lay_chan.addWidget(self.nchan)
        intensity_layout.addLayout(lay_chan)

        self.nchan.valueChanged.connect(self.measure_point_intensity)

        ## min value
        minint_layout = QHBoxLayout()
        minint_lab = QLabel()
        minint_lab.setText("From:")
        minint_layout.addWidget(minint_lab)
        self.min_intensity = QDoubleSpinBox()
        self.min_intensity.setMinimum(0)
        self.min_intensity.setMaximum(1)
        self.min_intensity.setSingleStep(0.05)
        self.min_intensity.setValue(0)
        minint_layout.addWidget(self.min_intensity)
        intensity_layout.addLayout(minint_layout)
        
        ## max value
        maxintensity_layout = QHBoxLayout()
        maxintensity_lab = QLabel()
        maxintensity_lab.setText("To:")
        maxintensity_layout.addWidget(maxintensity_lab)
        self.max_intensity = QDoubleSpinBox()
        self.max_intensity.setMinimum(0)
        self.max_intensity.setMaximum(1)
        self.max_intensity.setSingleStep(0.05)
        self.max_intensity.setValue(1)
        maxintensity_layout.addWidget(self.max_intensity)
        intensity_layout.addLayout(maxintensity_layout)
        
        self.min_intensity.valueChanged.connect( self.changed_minintensity )
        self.max_intensity.valueChanged.connect( self.changed_maxintensity )
        self.intensity_range_group.setLayout(intensity_layout)


    def display_score_layout(self):
        """ Interface for display point range from score """
        self.score_range_group = QGroupBox("Assignement score")
        score_range_layout = QVBoxLayout() 
        
        ## min value
        minscore_layout = QHBoxLayout()
        minscore_lab = QLabel()
        minscore_lab.setText("From:")
        minscore_layout.addWidget(minscore_lab)
        self.min_score = QDoubleSpinBox()
        self.min_score.setMinimum(0)
        self.min_score.setMaximum(2)
        self.min_score.setSingleStep(0.05)
        self.min_score.setValue(0)
        minscore_layout.addWidget(self.min_score)
        score_range_layout.addLayout(minscore_layout)
        ## max value
        maxscore_layout = QHBoxLayout()
        maxscore_lab = QLabel()
        maxscore_lab.setText("To:")
        maxscore_layout.addWidget(maxscore_lab)
        self.max_score = QDoubleSpinBox()
        self.max_score.setMinimum(0)
        self.max_score.setMaximum(2)
        self.max_score.setSingleStep(0.05)
        self.max_score.setValue(2)
        maxscore_layout.addWidget(self.max_score)
        score_range_layout.addLayout(maxscore_layout)

        self.min_score.valueChanged.connect( self.changed_minscore )
        self.max_score.valueChanged.connect( self.changed_maxscore )
        self.score_range_group.setLayout(score_range_layout)

    def changed_minscore(self, i):
        """ Display min score has been changed """
        ## ensures that max score > min score
        if i > self.max_score.value():
            self.max_score.setValue(min(i+0.05,2))
        ## now update points display from range
        self.change_display_fromscore()

    def changed_maxscore(self, i):
        """ Display max score has been changed """
        ## ensures that max score > min score
        if i < self.min_score.value():
            self.min_score.setValue(max(i-0.05,0))
        ## now update points display from range
        self.change_display_fromscore()

    def change_display_fromscore(self):
        """ Show only points that have a score in the given range """
        self.layerrna.size = 0.1
        ## select corresponding points
        minscore = self.min_score.value()
        maxscore = self.max_score.value()
        self.layerrna.selected_data = {}
        for ind, score in enumerate(self.layerrna.properties['score']):
            if (score >= minscore) and (score <= maxscore):
                self.layerrna.selected_data.add(ind)
        selection = self.layerrna.selected_data
        drawsize = self.layerrna.current_size
        for ind in selection:
            self.layerrna.size[ind] = drawsize
        self.layerrna.selected_data = {}
        self.layerrna.refresh()
    
    def change_display_size(self):
        """ Change the displayed size of all points """
        self.layerrna.size = int( self.display_size.value() )
        self.main.spot_disp_size = int( self.display_size.value() )
        self.layerrna.refresh()

    def measure_point_intensity(self):
        """ Measure the intensity in the points in the current channel """
        nchan = self.nchan.value()
        self.mig.set_spots(self.channel, self.layerrna.data)
        intens = self.mig.measure_spots( self.channel, nchan )
        ## normalize the intensity by its max
        intens = intens/np.max(intens)
        for ind, inte in enumerate(intens):
            self.layerrna.properties['intensity'][ind] = inte
    
    def change_display_fromintensity(self):
        """ Show only points that have intensity in the given range """
        self.measure_point_intensity()
        self.layerrna.size = 0.1
        ## select corresponding points
        minintensity = self.min_intensity.value()
        maxintensity = self.max_intensity.value()
        self.layerrna.selected_data = {}
        for ind, intensity in enumerate(self.layerrna.properties['intensity']):
            if (intensity >= minintensity) and (intensity <= maxintensity):
                self.layerrna.selected_data.add(ind)
        selection = self.layerrna.selected_data
        drawsize = self.layerrna.current_size
        for ind in selection:
            self.layerrna.size[ind] = drawsize
        self.layerrna.selected_data = {}
        self.layerrna.refresh()
    
    def changed_minintensity(self, i):
        """ Display min intensity has been changed """
        ## ensures that max intensity > min intensity
        if i > self.max_intensity.value():
            self.max_intensity.setValue(min(i+0.05,1))
        ## now update points display from range
        self.change_display_fromintensity()
    
    def changed_maxintensity(self, i):
        """ Display max intensity has been changed """
        ## ensures that max intensity > min intensity
        if i < self.min_intensity.value():
            self.min_intensity.setValue(max(i-0.05,0))
        ## now update points display from range
        self.change_display_fromintensity()

    def save_draw_rna_counts( self ):
        """ Save the layer CountRNA if it was created """
        if "CountRNA"+str(self.channel) not in self.viewer.layers:
            ut.show_warning("No count image created yet. Click on Draw RNA counts before" )
            return
        layer = self.viewer.layers["CountRNA"+str(self.channel)]
        #outname = self.mig.build_filename( endname="_RNA"+str(self.channel)+"Counts.png" )
        #actlayer = self.viewer.layers.selection.active.name
        #ut.set_active_layer( self.viewer, "CountRNA"+str(self.channel) )
        #self.viewer.export_figure( outname )
        #ut.set_active_layer( self.viewer, actlayer)
        self.mig.save_image( layer.data, endname="_CountRNA"+str(self.channel)+".tif" )

    
    def draw_rna_counts( self ):
        """ Draw cells with their RNA counts """
        self.main.measure_rna( self.channel )
        countName = self.mig.get_measure_name( self.channel )
        countimg = self.mig.image_count_from_table( countName )
        cmap = "gray"
        if "originalChannel"+str(self.channel) in self.viewer.layers:
            layer = self.viewer.layers["originalChannel"+str(self.channel)]
            cmap = layer.colormap
        ut.remove_layer(self.viewer, "CountRNA"+str(self.channel))
        self.viewer.add_image( countimg, name="CountRNA"+str(self.channel), blending="additive", scale=(self.mig.scaleXY, self.mig.scaleXY), colormap=cmap )


    
    def finish_rna(self):
        """ Assignement and edition of RNA is finished, close everything """
            
        ## save last parameters
        self.cfg.addGroupParameter("RNA"+str(self.channel)+"_Assignement")
        self.cfg.addParameter("RNA"+str(self.channel)+"_Assignement", "assignement_method", self.method.currentText())
        self.cfg.addParameter("RNA"+str(self.channel)+"_Assignement", "limit_distance_to_assign", float(self.limit_distance.text()))
        self.cfg.addParameter("RNA"+str(self.channel)+"_Assignement", "nb_closest_rnas", int(self.nclosest.text()))
        self.cfg.addParameter("RNA"+str(self.channel)+"_Assignement", "assign_when_above", self.keep_above.isChecked())
        self.cfg.addParameter("RNA"+str(self.channel)+"_Assignement", "nb_z_above", int(self.naboveZ.text()))
        self.cfg.write_parameterfile()
            
        self.main.close_edit( self.channel, save=True )

    def save_rnafile(self):
        """ Save current points to RNA file """
        spots = self.layerrna.data
        labels = self.layerrna.properties['label']
        scores = self.layerrna.properties['score']
        filename = self.mig.rna_filename(chan=self.channel, ifexist=False)
        self.mig.save_spots(spots, labels, scores, self.channel, filename)

    def show_help_text(self):
        """ Show help text for RNA editing """
        help_text = "<v> to show/hide cell contours \n"
        help_text += "<f> show/hide the current RNA layer \n"
        help_text += "<d> increase/decrease the RNA opacity \n"
        help_text += "<F1>, <F2>... show/hide the first/second... layer \n"
        help_text = help_text + "<Right-click> on a cell to set the assignement value \n"
        help_text = help_text + "<c> assign selected points to the current assignement value \n"
        help_text += "<u> select all unsassigned points \n"
        help_text += "<s> select points with current assignement value\n"
        help_text += "<a> select all visible points \n"
        help_text += "<o> show only selected points \n"
        help_text += "<r> reset: show all points \n"
        help_text += "<l> show only selected cell \n"
        help_text += "<Control-left click> to select points \n"
        help_text += "<Control-right click> unselect \n"
        help_text += "<Shift-s> shuffle the colors of cells and points \n"
        help_text += "<Alt>+<Left-click> zoom on the clicked position \n"
        help_text += "<Alt>+<Right-click> unzoom \n"
        header = ut.helpHeader(self.viewer, None)
        ut.showOverlayText(self.viewer, header+help_text)
        print( "############ Edit RNA assignement where necessary" )

    def assign_selected2cell(self):
        """ Assign all selected points to the current cell value """
        selection = self.layerrna.selected_data
        assignement = int(self.assign_tocell.text())
        col = self.viewer.layers["CellContours"].get_color( assignement )
        for ind in selection:
            self.layerrna.properties['label'][ind] = assignement 
            self.layerrna.properties['score'][ind] = 2 ## manually assigned = sure
            self.layerrna.properties['unassigned'][ind] = (assignement <= 1) 
            self.layerrna.face_color[ind] = col
        self.layerrna.selected_data = {}
        self.layerrna.refresh()

    def reset_display(self):
        """ Reset points display """
        self.layerrna.size = self.layerrna.current_size
        self.layerrna.refresh()
        self.min_score.setValue(0)
        self.max_score.setValue(2)
        self.min_intensity.setValue(0)
        self.max_intensity.setValue(1)

    def show_hide( self, intlayer ):
        """ Show/hide the ith-layer """
        if intlayer < len( self.viewer.layers ):
            self.viewer.layers[intlayer].visible = not self.viewer.layers[intlayer].visible

    def active_shortcuts(self):
        """ Define shortcuts for point/assignement editing """ 
        @self.layerrna.bind_key('v', overwrite=True)
        def set_label(layerrna):
            if "CellContours" in self.viewer.layers:
                contlay = self.viewer.layers["CellContours"]
                contlay.visible = not contlay.visible
        
        @self.layerrna.bind_key('f', overwrite=True)
        def show_points(layerrna):
            self.layerrna.visible = not self.layerrna.visible
        
        @self.layerrna.bind_key('d', overwrite=True)
        def show_points_opacity(layerrna):
            op = self.layerrna.opacity
            if op >= 0.99:
                self.layerrna.opacity = 0.3
            if op <= 0.5:
                self.layerrna.opacity = 1.0
        
        
        @self.layerrna.bind_key('r', overwrite=True)
        def show_reset(layer):
            self.reset_display()
        
        @self.layerrna.bind_key('l', overwrite=True)
        def show_only_selected_cell(layer):
            contlay = self.viewer.layers["CellContours"]
            contlay.selected_label = int(self.assign_tocell.text())
            contlay.show_selected_label = not contlay.show_selected_label
        
        @self.layerrna.mouse_drag_callbacks.append
        def click(layer, event):
            if event.type == "mouse_press":
                if (event.button == 2) and ("Control" in event.modifiers):
                    self.layerrna.selected_data = {}

                if (event.button == 1) and ("Control" in event.modifiers):
                    modes = ["select", "pan_zoom"]
                    self.layerrna.mode = "select"
                    while event.type == "mouse_press":
                        yield
                    self.layerrna.mode = "pan_zoom"
                    #if self.layerrna.mode in modes:
                    #    self.layerrna.mode = modes[ (modes.index(self.layerrna.mode)+1)%2 ]
                    #else:
                    #    self.layerrna.mode = "pan_zoom"
            if event.type == "mouse_press":
                if (event.button == 2) and (len(event.modifiers) <= 0):
                    # right click pur
                    if "CellContours" not in self.viewer.layers:
                        self.main.add_cell_contours()
                    if "Cells" not in self.viewer.layers:
                        self.main.add_cell_contours()
                    ut.set_active_layer( self.viewer, self.layerrna.name )

                    contlay = self.viewer.layers["Cells"]
                    contlay.visible = True
                    value = contlay.get_value(position=event.position, view_direction = event.view_direction, dims_displayed=event.dims_displayed, world=True)
                    self.assign_tocell.setText(str(value))
                
                if (event.button == 1) and ("Alt" in event.modifiers):
                    ## Zoom on clicked area
                    self.viewer.camera.center = event.position 
                    self.viewer.camera.zoom = self.viewer.camera.zoom * 4
                
                if (event.button == 2) and ("Alt" in event.modifiers):
                    ## Unzoom
                    self.viewer.camera.zoom = self.viewer.camera.zoom *0.5
        
        
        @self.layerrna.bind_key('u', overwrite=True)
        def select_unassigned(layer):
            self.layerrna.selected_data = {}
            for ind, unass in enumerate(self.layerrna.properties['unassigned']):
                if unass:
                    self.layerrna.selected_data.add(ind)
            self.layerrna.refresh()
        
        @self.layerrna.bind_key('s', overwrite=True)
        def select_value(layer):
            self.layerrna.selected_data = {}
            assignement = int(self.assign_tocell.text())
            for ind, lab in enumerate(self.layerrna.properties['label']):
                if lab == assignement:
                    self.layerrna.selected_data.add(ind)
            self.layerrna.refresh()
        
        @self.layerrna.bind_key('o', overwrite=True)
        def show_only_selected(layer):
            self.layerrna.size = 0.1
            selection = self.layerrna.selected_data
            drawsize = self.layerrna.current_size
            for ind in selection:
                self.layerrna.size[ind] = drawsize
            self.layerrna.refresh()
        
        @self.layerrna.bind_key('c', overwrite=True)
        def updateBis(layer):
            self.assign_selected2cell()
        
        @self.layerrna.bind_key('Shift-s', overwrite=True)
        def shuffle_colors(layer):
            contlay = self.viewer.layers["CellContours"]
            contlay.new_colormap()

            fcolor = []
            for ind, lab in enumerate(self.layerrna.properties["label"]):
                fcolor.append( contlay.get_color(lab) )
            self.layerrna.face_color = fcolor
            self.layerrna.refresh()

    def point_editing(self, paras):
        """ RNA assignement, auto and manual correction """
        self.layerrna = self.viewer.layers["assignedRNA"+str(self.channel)]
        saved_layer_data = None
        saved_layer_prop = None
        
        refrnas = self.mig.get_done_rnalist()
        if refrnas is None:
            refrnas = [0]
        if len(refrnas) <= 0:
            refrnas = [0]

        layout = QVBoxLayout()

        ## Assignment method choice
        meth_line = QHBoxLayout()
        meth_lab = QLabel()
        meth_lab.setText("Assignement method:")
        meth_line.addWidget(meth_lab)
        self.method = QComboBox()
        meth_line.addWidget(self.method)
        methods = ["Projection", "ClosestNucleus", "MixProjClosest", "FromNClosest", "Hull"]
        for i in range(len(methods)):
            self.method.addItem(methods[i])
        ## default method 
        if (paras is not None) and ("assignement_method" in paras):
            self.method.setCurrentIndex(methods.index(paras["assignement_method"]))
        layout.addLayout(meth_line)
        ## assignemnet with nclosest specific parameters
        self.parameters_nclosest(paras)
        layout.addWidget(self.group_nclosest)

        ## advanced assignement parameters, common to all methods
        self.show_advanced = QCheckBox("Show advanced parameters")
        self.show_advanced.setChecked(False)
        layout.addWidget(self.show_advanced)
        self.parameters_advanced(paras)
        layout.addWidget(self.group_advanced)
        ## visibility of the panels
        self.show_advanced_parameters()
        self.parameters_assign_visibility()
        self.show_advanced.stateChanged.connect(self.show_advanced_parameters)
        self.method.currentIndexChanged.connect(self.parameters_assign_visibility)

        ## Apply assignement
        btn_apply = QPushButton("Apply assignment", parent=self)
        layout.addWidget(btn_apply)
        btn_apply.clicked.connect(self.assign_rna)
        ## Remove overlapped points
        btn_remover = QPushButton("Remove overlapping points", parent=self)
        layout.addWidget(btn_remover)
        btn_remover.clicked.connect(self.remove_overlapping)
        space = QLabel()
        space.setText("")
        layout.addWidget(space)

        self.group_assign.setLayout(layout)


    def parameters_assign_visibility(self):
        """ Handle assignement method parameters visibility """
        self.group_nclosest.setVisible(self.method.currentText()=="FromNClosest")

    def show_advanced_parameters(self):
        """ Show/Hide advanced parameters layout """
        self.group_advanced.setVisible(self.show_advanced.isChecked())

    def parameters_advanced(self, parameters):
        """ Interface for setting advanced assignement parameters """
        self.group_advanced = QGroupBox("Advanced parameters")
        layout = QVBoxLayout()
        ## Parameter distance limit
        limitdis_line = QHBoxLayout()
        limitdis_lab = QLabel()
        limitdis_lab.setText("Distance limit to assign (µm):")
        limitdis_line.addWidget(limitdis_lab)
        self.limit_distance = QLineEdit()
        assign_dist = 10.0
        if parameters is not None:
            if "limit_distance_to_assign" in parameters:
                assign_dist = parameters["limit_distance_to_assign"]
        self.limit_distance.setText(str(assign_dist))
        limitdis_line.addWidget(self.limit_distance)
        layout.addLayout(limitdis_line)
        ## Parameter assign above cells or not
        self.keep_above = QCheckBox("Assign also RNA above cells")
        assign_when_above = False
        if parameters is not None:
            if "assign_when_above" in parameters:
                assign_when_above = parameters["assign_when_above"].strip() == "True"
        self.keep_above.setChecked(assign_when_above)
        layout.addWidget(self.keep_above)
        ## Parameter nb Z above cells to keep
        nabove_line = QHBoxLayout()
        nabove_lab = QLabel()
        nabove_lab.setText("Keep nb Z above cell:")
        nabove_line.addWidget(nabove_lab)
        self.naboveZ = QLineEdit()
        nb_z_above = 0
        if parameters is not None:
            if "nb_z_above" in parameters:
                nb_z_above = parameters["nb_z_above"]
        self.naboveZ.setText(str(nb_z_above))
        nabove_line.addWidget(self.naboveZ)
        layout.addLayout(nabove_line)
        self.group_advanced.setStyleSheet("QGroupBox { color: #c3c0df; background-color: #54547d; }")
        self.group_advanced.setLayout(layout)

    def parameters_nclosest(self, parameters):
        """ Interface for FromNClosest assignement method """
        self.group_nclosest = QGroupBox("NClosest method")
        layout = QVBoxLayout()
        ## Parameter of number of closest RNAs to consider
        nclos_line = QHBoxLayout()
        nclos_lab = QLabel()
        nb_closest = 10
        if parameters is not None:
            if "nb_closest_rnas" in parameters:
                nb_closest = parameters["nb_closest_rnas"]
        nclos_lab.setText("Nb closest RNAs:")
        nclos_line.addWidget(nclos_lab)
        self.nclosest = QLineEdit()
        self.nclosest.setText(str(nb_closest))
        nclos_line.addWidget(self.nclosest)
        layout.addLayout(nclos_line)
        ## Add reference RNAs channels choice
        refchans_line = QHBoxLayout()
        refchans_lab = QLabel()
        refchans_lab.setText("Reference (assigned) RNAs:")
        refchans_line.addWidget(refchans_lab)
        self.reference_rnas = QListWidget()
        self.reference_rnas.setSelectionMode(QAbstractItemView.ExtendedSelection)
        refrnas = self.mig.get_done_rnalist()
        if refrnas is None:
            refrnas = [0]
        if len(refrnas) <= 0:
            refrnas = [0]
        for ref in refrnas:
            if ref != self.channel:
                self.reference_rnas.addItem(str(ref))
        self.reference_rnas.selectAll()
        refchans_line.addWidget(self.reference_rnas)
        layout.addLayout(refchans_line)
        self.group_nclosest.setLayout(layout)

    def assign_fromclosest( self, method, limDisAsso, assign_even_above, nAbove, nbclose, refrnas, start_time, pbar ):
        """ Assign RNA from same cell as their closest neighbors """
        if assign_even_above:
            above = None
        else:
            above = nAbove
        self.mig.assign_fromclosestrna( self.channel, method, limDisAsso, above, refrnas, nbclose )
        ut.show_duration( start_time, "Spots assigned in " )
        ut.close_progress( self.viewer, pbar )
        self.end_one_rna(method)

    def assign_spots( self, method, limDisAsso, assign_if_above, nAbove, start_time, pbar ):
        """ Assign RNA to cells with the selected method """
        if assign_if_above:
            above = None
        else:
            above = nAbove
        self.mig.assign_rna( self.channel, method, limDisAsso, above )
        pbar.update(1)
        ut.show_duration( start_time, "Spots assigned in " )
        ut.close_progress( self.viewer, pbar )
        self.end_one_rna( method )

    def assign_rna(self):
        """ Automatic assignement of RNA to cell with chosen parameters """
        self.main.add_cell_contours()
        self.mig.set_spots(self.channel, self.layerrna.data)
        self.layerrna.face_color = "white"
        self.layerrna.refresh()
        ut.show_info("assigning spots...")
        start_time = ut.get_time()
        pbar = ut.start_progress( self.viewer, total=2, descr="Assigning spots with "+self.method.currentText() )
        if self.method.currentText() == "FromNClosest":
            reflist = []
            for item in self.reference_rnas.selectedItems():
                reflist.append(int(item.text()))
            self.assign_fromclosest( self.method.currentText(), float(self.limit_distance.text()), self.keep_above.isChecked(), int(self.naboveZ.text()), int(self.nclosest.text()), reflist, start_time, pbar )
        else:
            self.assign_spots( self.method.currentText(), float(self.limit_distance.text()), self.keep_above.isChecked(), int(self.naboveZ.text()), start_time, pbar )

    def end_one_rna(self, method):
        """ Go to manual correction step """
        #ut.removeOverlayText(self.viewer)
        self.correction_rna(method=method)
    
    def correction_rna( self, method ):
        """ Manual correction step, udpate points display """
        #layerrna = self.viewer.layers["assignedRNA"+str(self.channel)]
        self.viewer.layers.selection.select_only(self.layerrna)
        spots, labs, scores = self.mig.get_spots(self.channel)
        labels = np.array(labs, dtype="int")
        unassigned = (labels==-1) + (labels==1)
        labels[unassigned] = 1
        fcolor = []
        for ind, lab in enumerate(labels):
            fcolor.append( self.viewer.layers["CellContours"].get_color(lab) )
            self.layerrna.properties['unassigned'][ind] = unassigned[ind]
            self.layerrna.properties["label"][ind] = lab
            self.layerrna.properties["score"][ind] = scores[ind]
        self.layerrna.face_color = fcolor
        self.layerrna.size = self.main.spot_disp_size
        self.layerrna.refresh()
        
    def remove_overlapping(self):
        """ Remove spots that had been detected as overlapping in several channels """
        channels = self.mig.get_overlapping_channels( channel = self.channel )
        if channels is None:
            ut.show_warning("No overlapping points found. Redo option Overlapping RNA if necessary")
        else:
            nremoved = 0
            self.layerrna.selected_data.clear()
            for ind, pt in enumerate(self.layerrna.data):
                if self.mig.find_spot(channels, pt, distance=0.5):
                    self.layerrna.selected_data.add(ind)
                    nremoved += 1
            self.layerrna.remove_selected()
            self.layerrna.refresh()
            self.layerrna.selected_data.clear()
            ut.show_info(str(nremoved)+" overlapping spots removed")


#### Measure RNA widget

class MainRNA(QWidget):
    """ Main RNA widget, containing the tab interface, save and finish options """

    def __init__( self, napari_viewer, mig, cfg, rnachannel, defmethod, rnafilename, parameters ):
        super().__init__()
        self.viewer = napari_viewer
        self.mig = mig
        self.cfg = cfg
        self.results = None
        self.edition = {}
        self.measure_intensity = {}
        self.spot_disp_size = parameters["RNA_spot_disp_size"] 

        ## GUI parameters
        layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.tabs.setObjectName("RNAs")
        layout.addWidget(self.tabs)
        ## add save and finish buttons
        btn_save = fwid.add_button( "Save RNAs", self.save_rnas, descr="Save current RNA file and all RNA measures", color=ut.get_color("save") )
        btn_done = fwid.add_button( "RNAS done", None, descr="Close the RNA interface and layers", color=ut.get_color("done") )
        btns_line = fwid.double_button( btn_save, btn_done )
        layout.addLayout( btns_line )


        ## add les onglets        
        wid_get = GetRNA( self.viewer, parameters, rnachannel, self.mig, self.cfg, defmethod, rnafilename, self )
        self.tabs.addTab( wid_get, "Get RNAs" )

        btn_done.clicked.connect( self.rnas_done )

        #show_table = QPushButton("Show measures table")
        #layout.addWidget(show_table)
        #show_table.clicked.connect(self.show_measures)
        
        #save_table = QPushButton("Save measures table")
        #layout.addWidget(save_table)
        #save_table.clicked.connect(self.save_measures)

        ## drawing RNA counts
        #draw_line = QHBoxLayout()
        #draw_cell_counts = QPushButton("Draw cell counts of ")
        #self.rna_todraw = QComboBox()
        #draw_line.addWidget(draw_cell_counts)
        #draw_line.addWidget(self.rna_todraw)
        #layout.addLayout(draw_line)
        #draw_cell_counts.clicked.connect(self.draw_measures)
        #self.update_drawing_rna_choices()
        
        #finish = QPushButton("RNAs done")
        #layout.addWidget(finish)
        #finish.clicked.connect(self.finish_rnas)
        
        self.setLayout(layout)

    def go_edition( self, chanel ):
        """ Launch edition and interface of given chanel """
        self.edition[chanel] = PointEditing( chanel, self.viewer, self.mig, self.cfg, self )
        self.tabs.addTab(self.edition[chanel], "EditRNA"+str(chanel))
        self.tabs.setCurrentWidget( self.edition[chanel] )
    
    def go_measure_intensity( self, chanel ):
        """ Launch measure intensity interface of given chanel """
        self.measure_intensity[chanel] = PointMeasuring( chanel, self.viewer, self.mig, self.cfg, self )
        self.tabs.addTab(self.measure_intensity[chanel], "MeasureIntensity"+str(chanel))

    def add_cell_contours( self ):
        """ Add cell contours and cells layer if not already present """
        if (self.mig.pop is None) or (self.mig.pop.imgcell is None):
            print("No cells found, will not be able to assign.")
            return
        if "CellContours" not in self.viewer.layers:
            celllab = self.viewer.add_labels(self.mig.getJunctionsImage3D(full=False, thick=2), name="CellContours", blending="additive", scale=(self.mig.scaleZ, self.mig.scaleXY, self.mig.scaleXY))
            celllab.opacity = 0.6
            celllab.editable = False
        if "Cells" not in self.viewer.layers:
            cells = self.viewer.add_labels(self.mig.getJunctionsImage3D(), name="Cells", blending="additive", scale=(self.mig.scaleZ, self.mig.scaleXY, self.mig.scaleXY))
            cells.opacity = 0
            cells.editable = False
    
    
    def close_edit( self, chanel, save=True ):
        """ Remove the edition option of given RNA channel """
        ## remove widget and layer visibility
        if save:
            self.save_rnas()
        self.viewer.layers["originalChannel"+str(chanel)].visible=False
        ut.remove_layer( self.viewer, "assignedRNA"+str(chanel) )
        if chanel in self.edition:
            tabindex = self.tabs.indexOf( self.edition[chanel] )
            self.tabs.removeTab( tabindex )
        if chanel in self.measure_intensity:
            tabindex = self.tabs.indexOf( self.measure_intensity[chanel] )
            self.tabs.removeTab( tabindex )
        del self.edition[chanel]

    
    def save_rnas(self):
        """ Measure cells and RNA counts """
        for rnac in range( self.mig.nbchannels ):
            if ("assignedRNA"+str(rnac)) in self.viewer.layers:
                player = self.viewer.layers["assignedRNA"+str(rnac)]
                rnalabpoints = player.data
                rnaprops = player.properties
                rnalablabels = player.properties['label']
                rnalabscores = player.properties['score']
                self.mig.update_spotsAndCountFromPoints( rnalabpoints, rnalablabels, rnalabscores, rnac )
                filename = self.mig.rna_filename( chan=rnac, ifexist=False )
                self.mig.save_spots( rnalabpoints, rnaprops, rnac, filename )
        self.mig.measure_counts()
        self.mig.save_results()

    def rnas_done( self ):
        """ Finish the option, close all RNA related interface/layer """
        #self.viewer.layers.events.removing.disconnect(unremove)
        for rnac in range(self.mig.nbchannels):
            ut.remove_widget(self.viewer, "Assign RNA"+str(rnac))
            if "assignedRNA"+str(rnac) in self.viewer.layers:
                self.viewer.layers.remove("assignedRNA"+str(rnac))
        ut.remove_widget(self.viewer, "RNAs")
        ut.remove_layer(self.viewer,"CellContours")
        ut.remove_layer(self.viewer,"Cells")
        ut.removeOverlayText(self.viewer)
        self.cfg.removeTmpText()
    
    def measure_rna( self, rnac ):
        """ Measure RNA counts in cells for given chanel """
        if ("assignedRNA"+str(rnac)) in self.viewer.layers:
            player = self.viewer.layers["assignedRNA"+str(rnac)]
            rnalabpoints = player.data
            rnalablabels = player.properties['label']
            rnalabscores = player.properties['score']
            self.mig.update_spotsAndCountFromPoints( rnalabpoints, rnalablabels, rnalabscores, rnac )
        method = self.mig.rnas[rnac].countName
        self.mig.measure_count( rnac, method )

    def measure_rnas(self):
        """ Measure cells and RNA counts """
        rnalist = self.mig.get_rnalist()
        for rnac in rnalist:
            if ("assignedRNA"+str(rnac)) in self.viewer.layers:
                player = self.viewer.layers["assignedRNA"+str(rnac)]
                rnalabpoints = player.data
                rnalablabels = player.properties['label']
                rnalabscores = player.properties['score']
                self.mig.update_spotsAndCountFromPoints( rnalabpoints, rnalablabels, rnalabscores, rnac)
        self.mig.measure_counts()
        self.results = self.mig.get_counts()

    def save_measures(self):
        self.measure_rnas()
        self.update_drawing_rna_choices()
        self.mig.save_results()
    
    def show_measures(self):
        """ Show a table containing all cell measures """
        self.measure_rnas()
        self.update_drawing_rna_choices()
        if (self.results is None) or len(self.results[0].keys())==0:
            ut.show_info("Nothing measured yet")
            return
        tab = {}
        for k in self.results[0].keys():
            tab[k] = []
            for row in self.results:
                if k not in row:
                    tab[k].append(0)
                else:
                    if row[k] is None:
                        tab[k].append(-9999)
                    else:
                        tab[k].append(row[k])
        Table(tab).show()

    def update_drawing_rna_choices(self):
        """ Update the list of RNA choices to be drawn """
        rnachoices = self.mig.get_done_rnalist()
        self.rna_todraw.clear()
        for rna in rnachoices:
            self.rna_todraw.addItem("RNA"+str(rna))

class PointMeasuring(QWidget):
    """ Handle measuring intensity of RNA segmentation """

    def __init__(self, chan, viewer, mig, cfg, main):
        super().__init__()
        self.viewer = viewer
        self.channel = chan
        self.mig = mig
        self.cfg = cfg
        self.main = main
        self.layerrna = self.viewer.layers["assignedRNA"+str(self.channel)]

        layout = QVBoxLayout()
        inside_line, inside_check, self.inside_gr = fwid.checkgroup_help( "Inside segmented nuclei", True, descr="Measure if points are inside segmented nuclei or not", help_link="Get-RNAS#measure-intensity" )
        inside_layout = QVBoxLayout()
        ## title to explain
        inside_lab = fwid.add_label("Which points are inside segmented nuclei")
        inside_layout.addWidget(inside_lab)
        ## measure inside button
        go_inside = fwid.add_button( "Measure points inside nuclei", self.mark_points_inside_nuclei, descr="Measure if points are inside segmented nuclei or not", color=ut.get_color("go") )
        inside_layout.addWidget(go_inside)
        self.inside_gr.setLayout(inside_layout)
        layout.addLayout(inside_line)
        layout.addWidget( self.inside_gr )

        intensity_line, intensity_check, self.intensity_gr = fwid.checkgroup_help( "Measure raw intensity", True, descr="Measure raw intensity of selected channel into the spots", help_link="Get-RNAS#measure-intensity" )
        intensity_layout = QVBoxLayout()
        # choose layer to measure intensity
        line, self.layer_choice = fwid.list_line( "From layer:", descr="Choose opened layer to measure", func=None )
        self.update_layers_list()
        intensity_layout.addLayout(line)
        measure_button = fwid.add_button( "Measure intensity", self.measure_intensity, descr="Measure intensity of selected layer", color=ut.get_color("go") )
        intensity_layout.addWidget(measure_button)
        self.intensity_gr.setLayout(intensity_layout)
        layout.addLayout(intensity_line)
        layout.addWidget( self.intensity_gr )

        ## reset display button
        reset_button = fwid.add_button( "Reset display", self.reset_display, descr="Reset the display of RNA spots" )
        ## update button
        update_list = fwid.add_button( "Update layers list", self.update_layers_list, descr="Update the list of opened layers" )
        res_line = fwid.double_button( reset_button, update_list )
        layout.addLayout(res_line)
        ## run the measure button
        self.setLayout(layout)

    def mark_points_inside_nuclei( self ):
        """ Mark if points are inside segmented nuclei or not """
        if "segmentedNuclei" in self.viewer.layers:
            nuc = self.viewer.layers["segmentedNuclei"].data
        else:
            nuc = self.mig.get_segmented_nuclei()
        if nuc is None:
            ut.show_warning("No segmented nuclei found. Do Get nuclei before to segment them")
            return
        
        nuc = 1*(nuc > 0) ## dont keep the labels
        ## update spots list
        self.mig.set_spots(self.channel, self.layerrna.data)
        
        ## measure spots
        self.mig.measure_spots( self.channel, measureimg = nuc, name="InsideSegmentedNuclei" )
        self.mig.threshold_spots_measure( self.channel, "InsideSegmentedNuclei", threshold=0.5 )
        self.display_by_intensity( "InsideSegmentedNuclei", 0, 2 )

    def reset_display( self ):
        """ Reset point colors to cell label """ 
        self.layerrna.face_color = 'label'
        self.layerrna.refresh()

    def update_layers_list( self ):
        """ Update list of opened layers """
        self.layer_choice.clear()
        layers = self.viewer.layers
        for lay in layers:
            if not lay.name.startswith("assignedRNA"):
                self.layer_choice.addItem(lay.name)

    def measure_intensity( self ):
        """ Measure intensity of selected layer """
        layer_name = self.layer_choice.currentText()
        if layer_name not in self.viewer.layers:
            ut.show_warning("Layer "+layer_name+" not found")
            return
        ## update spots list
        self.mig.set_spots(self.channel, self.layerrna.data)
        ## measure spots
        self.mig.measure_spots( self.channel, measureimg = self.viewer.layers[layer_name].data, name="Int_"+layer_name )
        minint = np.min(self.viewer.layers[layer_name].data)
        maxint = np.max(self.viewer.layers[layer_name].data)
        self.display_by_intensity( "Int_"+layer_name, minint, maxint )

    def display_by_intensity( self, intensity_name, minint, maxint ):
        """ Color points by intensity measure """
        self.layerrna.selected_data = {}
        intensities = self.mig.get_spots_measure( self.channel, intensity_name )
        self.layerrna.features[intensity_name] = intensities
        self.layerrna.features['intensity'] = intensities
        self.layerrna.refresh()
        self.layerrna.face_color = 'intensity'
        minint = min( np.min(intensities), minint*1.25 )
        maxint = max( np.max(intensities), maxint*0.75 )
        self.layerrna.contrast_limits = (minint, maxint)
        self.layerrna.refresh_colors()
