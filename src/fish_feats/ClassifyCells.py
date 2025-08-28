import numpy as np
import napari
from magicgui import magicgui
from napari.utils.notifications import show_info
from magicgui.widgets import Table
import fish_feats.MainImage as mi
import fish_feats.Utils as ut
import fish_feats.FishWidgets as fwid
import pathlib
from qtpy.QtWidgets import QPushButton, QHBoxLayout, QVBoxLayout, QWidget, QGroupBox, QLineEdit, QComboBox, QLabel, QSpinBox, QCheckBox, QTabWidget, QFileDialog, QTableWidget, QTableWidgetItem, QGridLayout
from qtpy.QtCore import Qt
import time

""" 
Widget to directly use the ClassifyCells option without going again through all the pipeline.
Needs the segmented cells file.
"""

def get_image():
    """ Load and initialize the desired file """
    mig = mi.MainImage( talkative=True )
    viewer = napari.current_viewer()
    viewer.title = "Fish&Feats"
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

    
    filename = ut.dialog_filename()
    if filename is None:
        print("No file selected")
        return
    
    mig.open_image( filename=filename )
    ut.update_history(mig.imagedir)
    
    for channel in range(mig.nbchannels):
        cmap = ut.colormapname(channel)
        img = mig.get_channel(channel)
        cview = viewer.add_image( img, name="originalChannel"+str(channel), blending="additive", scale=(mig.scaleZ, mig.scaleXY, mig.scaleXY), colormap=cmap )
        dint = np.max(img)-np.min(img)
        cview.contrast_limits=(np.min(img), np.max(img)-0.75*dint)
    viewer.axes.visible = True

    return getScales(mig, viewer)

def getScales(mig, viewer):
    @magicgui(call_button="Update", 
            scaleXY={"widget_type": "LiteralEvalLineEdit"},
            scaleZ={"widget_type": "LiteralEvalLineEdit"},
            )
    def get_scale( scaleXY= mig.scaleXY, scaleZ= mig.scaleZ,
                   segmented_cells=pathlib.Path(mig.junction_filename(dim=2,ifexist=True)),
                   #load_features_table = True,
        ):
        mig.scaleXY = scaleXY
        mig.scaleZ = scaleZ
        for chan in range(mig.nbchannels):
            viewer.layers['originalChannel'+str(chan)].scale = [mig.scaleZ, mig.scaleXY, mig.scaleXY]
        ut.remove_all_widgets(viewer)
        mig.load_segmentation( segmented_cells )
        done = mig.popFromJunctions()
        if done < 0:
            return
        #if load_features_table:
        #    mig.loadFeaturesTable(endname="_features.csv")
        classify_cells(mig, viewer)
    
    wid = viewer.window.add_dock_widget(get_scale, name="Scale")
    return wid

################ attribute cells
def classify_cells(mig, viewer):
    """ Load main interface of classify cells option """ 
    print("************ Classify cells by user-defined category **************")

    def showHelp():
        """ Open wiki documentation page """
        ut.show_documentation_page("Classify-cells")
    
    def saveTable():
        """ Save the table of features, in the results file """
        ## update the table with edited feature
        featTable.set_table()
        mig.save_results()

    def endMain():
        """ Close all widgets and save results """
        mig.save_results()
        ut.remove_layer(viewer, "Cells")
        for feat in mig.getFeaturesList():
            ut.remove_layer(viewer, "ProjC"+feat)
            ut.remove_layer(viewer, feat+"Cells")
        wids = []
        for wid in ut.list_widgets(viewer):
            if wid.startswith("Feat_"):
                wids.append(wid)
            if wid.startswith("Edit Feat_"):
                wids.append(wid)
        for wid in wids:
            ut.remove_widget(viewer, wid)
        ut.remove_widget(viewer, "Main")
        ut.removeOverlayText(viewer)

    ut.remove_layer(viewer, "Cells")
    labimg = viewer.add_labels( mig.pop.imgcell, name="Cells", scale=(mig.scaleXY, mig.scaleXY), opacity=0.4, blending="additive" )
    labimg.contour = 1

    if not ut.has_widget( viewer, "Classify cells"):
        main_widget = QWidget()
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        
        btn_line = QHBoxLayout()
        ## save table option
        save_table = fwid.add_button( "Update/Save table", saveTable, descr="Update the displayed table with the modified feature and save it in the results file", color=ut.get_color("save") )
        #save_table = QPushButton("Update/Save table")
        btn_line.addWidget(save_table)
        
        helpb = QPushButton("Help")
        btn_line.addWidget(helpb)
        helpb.setStyleSheet( 'QPushButton {background-color: '+ut.get_color("help")+' } ')
        helpb.clicked.connect(showHelp)
        
        ## finish classify option
        end_main = QPushButton("Stop and Save")
        btn_line.addWidget(end_main)
        end_main.clicked.connect(endMain)
        end_main.setStyleSheet( 'QPushButton {background-color: '+ut.get_color("done")+'} ')
        layout.addLayout(btn_line)
        
        tabs = QTabWidget()
        tabs.setObjectName("Classify cells")
        layout.addWidget(tabs)

        ## Fetures table        
        featTable = FeaturesTable(viewer, mig)
        tabs.addTab( featTable, "Feature table" )
        add_feat = AddFeature(viewer, mig, labimg, featTable)
        tabs.addTab( add_feat, "Add/Edit a feature" )
        

        viewer.window.add_dock_widget( main_widget, name="Main" )
        text = "Classify manually cells into categories \n"
        text += ut.help_shortcut("classify")
        ut.showOverlayText(viewer, text)
        
        

class HandleTable(QWidget):
    """ Handle the table of all the features """
    def __init__(self, napari_viewer, mig, featTable):
        super().__init__()
        self.viewer = napari_viewer
        self.mig = mig
        self.table = featTable
        layout = QVBoxLayout()

        self.setLayout(layout)
    


def do_features_table(mig, viewer):
    @magicgui(call_button="Table done",
            reset_table={"widget_type":"PushButton", "value": False}, 
            load_table={"widget_type":"PushButton", "value": False}, 
            save_table={"widget_type":"PushButton", "value": False}, 
            show_table={"widget_type":"PushButton", "value": False},)
    def result_table(
            show_table_options = False,
            reset_table = False, load_table = False,
            load_file=pathlib.Path(mig.features_filename(ifexist=True)),
            save_table=False, show_table=False):
            ut.remove_widget(viewer, "Features table")
            ut.remove_widget(viewer, "Add feature")
            ut.remove_layer(viewer,"Cells")

    def show_options():
        """ Show additional options or not """
        booly = result_table.show_table_options.value
        result_table.show_table.visible = booly
        result_table.reset_table.visible = booly
        result_table.load_table.visible = booly
        result_table.load_file.visible = booly


    def showTable():
        tab = mig.getFeaturesTable()
        Table(tab).show()

    def resetTable():
        """ Erase all measured features """
        mig.initFeatureCells()
        
    def loadTable():
        """ Load features from a table file """
        filename = result_table.load_file.value
        mig.loadFeatureTable(filename)

    result_table.save_table.clicked.connect(saveTable)
    result_table.show_table.clicked.connect(showTable)
    result_table.reset_table.clicked.connect(resetTable)
    result_table.load_table.clicked.connect(loadTable)
    result_table.show_table_options.changed.connect(show_options)
    show_options()
    viewer.window.add_dock_widget(result_table, name="Features table")


class AddFeature(QWidget):
    """ Options to add a feature to measure """

    def __init__(self, napari_viewer, mig, labimg, table):
        super().__init__()
        self.viewer = napari_viewer
        self.mig = mig
        self.labimg = labimg
        self.table = table
        self.nb_values = {}
        
        layout = QVBoxLayout()
        
        feature_line = QHBoxLayout()
        feat_btn = QPushButton( "Do feature" )
        feature_line.addWidget( feat_btn )
        feat_btn.setToolTip( "Click to create/edit the selected feature" )
        feat_btn.setStatusTip( "Click to create/edit the selected feature" )
        ## Show editable list of features
        self.features_list = QComboBox()
        if self.mig.getFeaturesList() is not None:
            for feat in mig.getFeaturesList():
                self.features_list.addItem(feat)
        feature_line.addWidget( self.features_list )
        self.features_list.setEditable(True)
        self.features_list.setToolTip("Select a feature to edit or write the name of a new feature")
        feat_btn.clicked.connect( self.do_feature )
        layout.addLayout( feature_line )        
            
        self.setLayout(layout)
        self.creator = CreateFeature( self )
       

    def do_feature( self ):
        """ Displays the correct GUI depending if creating new feature or editing one """
        if self.features_list.currentText() == "":
            ut.show_warning("Please select a feature to edit or write the name of a new feature")
            return
        if (self.features_list.currentText() in self.mig.getFeaturesList()) or ("Feat_"+self.features_list.currentText() in self.mig.getFeaturesList()):
            self.go_edit_feature()
        else:
            ## creating a new feature
            self.creator.set_name()
            self.creator.show()
    
    def create_editfeature(self):
        """ GUI of edit feature option """
        geditfeat_layout = QVBoxLayout()
        
        loadfile = QHBoxLayout()
        self.loadTableFile = QLineEdit()
        self.loadTableFile.setText(self.mig.features_filename(ifexist=True))
        loadfile.addWidget(self.loadTableFile)
        select_file = QPushButton("Load feature(s) from file", parent=self)
        loadfile.addWidget(select_file)
        select_file.clicked.connect(self.selectFile)
        geditfeat_layout.addLayout(loadfile)
        
        self.choose_feat = QComboBox()
        geditfeat_layout.addWidget(self.choose_feat)
        features_list = self.table.get_features_list()
        for feat in features_list:
            if (feat != "CellLabel") and (feat != "CellId"):
                self.choose_feat.addItem(feat)
        
        edit_feat = QPushButton("Edit selected feature", parent=self)
        geditfeat_layout.addWidget(edit_feat)
        edit_feat.clicked.connect(self.go_edit_feature)
        
        self.gEditFeat.setLayout(geditfeat_layout)
        self.gEditFeat.setStyleSheet("QGroupBox { color: #d6d4df; background-color: #363650; }")

    def update_editfeature(self):
        """ Update the list of loaded features """
        self.choose_feat.clear()
        features_list = self.table.get_features_list()
        for feat in features_list:
            if (feat != "CellLabel") and (feat != "CellId"):
                self.choose_feat.addItem(feat)


    def selectFile(self):
        self.loadTableFile.setText(QFileDialog.getOpenFileName()[0])
        self.loadTable()
    
    def loadTable(self):
        """ Load features from a table file """
        filename = self.loadTableFile.text()
        self.mig.loadFeatureFile(filename)
        self.table.set_table()
        self.update_editfeature()
    

    def go_edit_feature(self):
        """ Edit an already loaded feature """
        featname = self.features_list.currentText()
        if not featname.startswith("Feat_"):
            featname = "Feat_"+featname
        featlist = self.mig.getFeaturesList()

        featimg = self.mig.image_feature_from_table( featname )
        edit_feat = EditFeature(  self.viewer, self.mig, self.labimg, self.table, featimg, featname, nb_values=2 )
        self.viewer.window.add_dock_widget( edit_feat, name="Edit "+featname )


class FeaturesTable(QWidget):
    """ Widget to visualize and interact with the measurement table """

    def __init__(self, napari_viewer, mig):
        super().__init__()
        self.viewer = napari_viewer
        self.mig = mig

        self.wid_table = QTableWidget()
        self.wid_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setLayout(QGridLayout())
        self.layout().addWidget(self.wid_table)
        self.wid_table.clicked.connect(self.show_label)
        self.wid_table.setSortingEnabled(True)

        self.set_table()

    def show_label(self):
        """ When click on the table, show selected cell """
        if self.wid_table is not None:
            row = self.wid_table.currentRow()
            seglayer = self.viewer.layers["Cells"]
            seglayer.show_selected_label = False
            seglayer.visible = True
            headers = [self.wid_table.horizontalHeaderItem(ind).text() for ind in range(self.wid_table.columnCount()) ]
            labelind = None
            if "CellLabel" in headers:
                labelind = headers.index("CellLabel") 
            if labelind is not None and labelind >= 0:
                lab = int(self.wid_table.item(row, labelind).text())
                seglayer.selected_label = lab
                seglayer.show_selected_label = True
                #seglayer.refresh()


    def get_features_list(self):
        """ Return list of measured features """
        return [ self.wid_table.horizontalHeaderItem(ind).text() for ind in range(self.wid_table.columnCount()) ]

    def set_table(self, table=None, header=None):
        if table is None:
            table = self.mig.getFeaturesTable()
            header = self.mig.getFeaturesList()
        
        self.wid_table.clear()
        self.wid_table.setRowCount(len(table["CellLabel"]))
        self.wid_table.setColumnCount(len(table.keys()))

        for c, column in enumerate(table.keys()):
            column_name = column
            self.wid_table.setHorizontalHeaderItem(c, QTableWidgetItem(column_name))
            for r, value in enumerate(table.get(column)):
                item = QTableWidgetItem()
                if value == "":
                    value = "0"
                item.setData( Qt.EditRole, int(value))
                self.wid_table.setItem(r, c, item)

#class Projections(QWidget):
#    """ Widget to visualize projected chanels, can help to classify """

#    def __init__(self, napari_viewer):
#        self.viewer = napari_viewer

class EditFeature( QWidget ):
    """ GUI and shortcuts to edit a feature """

    def __init__( self, viewer, mig, labimg, table, featimg, featname, nb_values, channel=None ):
        """ Interface to edit a feature """
        super().__init__()
        self.viewer = viewer
        self.mig = mig
        self.featname = featname
        self.nb_values = nb_values
        self.labimg = labimg
        self.channel = channel
        self.table = table

        layout = QVBoxLayout()
        lab = fwid.add_label( "Press 'i'/'d' to increase/decrease the value" )
        layout.addWidget( lab )

        ## slider
        value_line, self.new_value = fwid.slider_line( "Class value", 1, maxval=nb_values, step=1, value=1, show_value=True, slidefunc=None, descr="Choose the value to set clicked cells", div=1 )
        layout.addLayout( value_line )

        msg = fwid.add_label( "Right-click get the class value under the click \n [Control]+Left click set the clicked cell to the current class value" )
        layout.addWidget( msg )

        ## save feature image
        save_feat = fwid.add_button( "Export feature image", self.export_feature_image, descr="Save the image of cells colored by feature value" )
        add_class = fwid.add_button( "Add one class", self.add_one_class, descr="Add one possible class in the current feature")
        line = fwid.double_button( save_feat, add_class )
        layout.addLayout( line )

        ## finish the feature
        feat_done = fwid.add_button( str(self.featname)+" done", self.finish, descr="Close the edit interface for this feature", color=ut.get_color("done") )
        layout.addWidget( feat_done )

        self.setLayout( layout ) 
        self.add_one_feature( featimg, channel=channel )

    def finish( self ):
        """ Close this interface, close what should be closed """
        ut.remove_widget(self.viewer, "Edit "+self.featname)
        ut.remove_layer(self.viewer, self.featname+"Cells")
        if self.channel is not None:
            ut.remove_layer(self.viewer, "ProjC"+str(self.channel))
        if ut.has_widget(self.viewer, "Feature table"):
            self.table.set_table()

    
    def add_one_feature(self, featimg, channel=None):
        """ Launch editor of new feature """
        ## check that the nb of values is sufficient if the feature is already present
        featlist = self.mig.getFeaturesList()
        if (featlist is not None) and len(featlist)>0:
            if self.featname in featlist:
                maxval = self.mig.getFeatureMax( self.featname )
                if (maxval) > self.nb_values:
                    self.nb_values = maxval 
                    self.new_value.setMaximum( int(self.nb_values ) )

        ut.remove_layer(self.viewer, self.featname+"Cells")
        for layer in self.viewer.layers:
            layer.visible = False
        self.featlayer = self.viewer.add_labels(featimg, name=self.featname+"Cells", scale=(self.mig.scaleXY, self.mig.scaleXY), opacity=0.7, blending="additive")
        self.featlayer.contour = 5
        self.labimg.visible = True
        if (channel is not None) and ("ProjC"+str(channel) in self.viewer.layers):
            self.viewer.layers["ProjC"+str(channel)].visible = True
        
        self.active_bindings()

    def active_bindings( self ):
        """ Active the bindings for the layer """

        @self.featlayer.bind_key('i', overwrite=True)
        def increase_value(layer):
            self.new_value.setValue( int(self.new_value.value())%(self.nb_values) + 1 )
        
        @self.featlayer.bind_key('d', overwrite=True)
        def decrease_value(layer):
            self.new_value.setValue( (int(self.new_value.value()) - 2)%(self.nb_values) + 1 )
        
        @self.featlayer.mouse_drag_callbacks.append
        def click(layer, event):
            if event.type == "mouse_press":
                if event.button == 2:
                    # right click
                    pos = self.mig.get_coordinates(event.position)
                    value = self.featlayer.data[pos[0], pos[1]]
                    self.new_value.setValue( value )
                    return
                ## Set value to the cell under the cursor
                if (event.button == 1) and ("Control" in event.modifiers):
                    pos = self.mig.get_coordinates(event.position)
                    label = self.labimg.data[pos[0], pos[1]]
                    newvalue = int( self.new_value.value() )
                    self.setCellValue(label, newvalue)
                    return
        
    def setCellValue( self, label, newvalue ):
        """ Set the selected label to newvalue for the current feature """
        self.mig.change_cell_feature( self.featname, label, newvalue, self.featlayer.data )
        self.featlayer.refresh()
        
    def export_feature_image( self ):
        """ Save an image of the classified cells for the feature """
        self.mig.save_image( self.featlayer.data, endname="_feat_"+self.featname+".tif", imtype="uint8" ) 
        ## update the table with edited feature
        self.table.set_table()

    def add_one_class( self ):
        """ Add a new class to the feature """
        self.new_value.setMaximum( int(self.nb_values )  + 1 )
        self.nb_values = self.nb_values + 1
        ut.show_info("New class added to feature "+self.featname+" ("+str(self.nb_values)+" classes)")

class CreateFeature( QWidget ):
    """ GUI to create a new feature """
        
    def __init__(self, cc):
        """ Interface to create new feature """
        super().__init__()
        self.cc = cc
        #self.gNewFeat = QGroupBox("Create new feature")
        gnewfeat_layout = QVBoxLayout()
        ## name of the new feature
        self.feat_name = QLabel()
        self.feat_name.setText("")
        self.feat_name.setText("Feature name: "+self.cc.features_list.currentText())
        gnewfeat_layout.addWidget(self.feat_name)
        ## nb class of the new feature
        nvals = QHBoxLayout()
        nvals_lab = QLabel()
        nvals_lab.setText("Nb classes:")
        nvals.addWidget(nvals_lab)
        self.nbclass = QSpinBox()
        self.nbclass.setMinimum(2)
        self.nbclass.setMaximum(25)
        self.nbclass.setSingleStep(1)
        self.nbclass.setValue(2)
        nvals.addWidget(self.nbclass)
        gnewfeat_layout.addLayout(nvals)

        ## initialization method
        self.prefill = QComboBox()
        gnewfeat_layout.addWidget(self.prefill)
        self.prefill.addItem("Initialize all cells at 1")
        ## option to project and classify from that
        self.prefill.addItem("channel projection+threshold")
        self.create_projthreshold()
        gnewfeat_layout.addWidget(self.gProj)
        ## option to classify from touching the boundary or border
        self.prefill.addItem("Boundary cells")
        self.gui_boundary()
        gnewfeat_layout.addWidget(self.gBound)
        self.prefill.currentIndexChanged.connect(self.show_initoptions)

        ## show projection of a channel
        self.show_projection = QCheckBox(text="Show projected channel")
        gnewfeat_layout.addWidget(self.show_projection)
        self.show_projection.setChecked(True)
        self.show_projection.stateChanged.connect(self.show_initoptions)

        ## channel to project
        self.nchan = QHBoxLayout()
        self.nchan_lab = QLabel()
        self.nchan_lab.setText("channel to project:")
        self.nchan.addWidget(self.nchan_lab)
        self.nchannel = QSpinBox()
        self.nchannel.setMinimum(0)
        self.nchannel.setMaximum(self.cc.mig.nbchannels - 1)
        self.nchannel.setSingleStep(1)
        self.nchannel.setValue(0)
        self.nchan.addWidget(self.nchannel)
        gnewfeat_layout.addLayout(self.nchan)

        ## Button go to create new feature
        newfeat_go = QPushButton("Create new feature", parent=self)
        newfeat_go.setStyleSheet( 'QPushButton {background-color: #4a754d} ')
        gnewfeat_layout.addWidget(newfeat_go)
        self.show_initoptions()
        newfeat_go.clicked.connect(self.create_feature)

        self.setLayout(gnewfeat_layout)

    def set_name( self ):
        """ Update the name of the feature to create """
        self.feat_name.setText("Feature name: "+self.cc.features_list.currentText())


    def show_initoptions(self):
        """ Set visible parameters """
        self.gProj.setVisible( self.prefill.currentText() == "channel projection+threshold" )
        self.gBound.setVisible( self.prefill.currentText() == "Boundary cells" )
        show_nchan = (self.show_projection.isChecked()) or (self.prefill.currentText()=="channel projection+threshold") 
        self.nchannel.setVisible(show_nchan)
        self.nchan_lab.setVisible(show_nchan)
        if self.prefill.currentText() == "channel projection+threshold":
            text = "Initialize cells classification by mean projection of the selected channel \n"
            text += "Projected intensity is thresholded by: mean(intensites)*\'Threshold\' \n"
            text += "Cells are classified >0 if their proportion of positive pixels is greater than \'Prop area above threshold\' \n"
            ut.showOverlayText(self.cc.viewer, text)
        else:
            ut.removeOverlayText(self.cc.viewer)

    def gui_boundary( self ):
        """ GUI for boundary cells classification """
        self.gBound = QGroupBox( "Boundary classification" )
        gbound_layout = QVBoxLayout()

        ## option to get border cells or boundary cells
        self.border_cells = fwid.add_check( "Image border", False, None, descr="Class cells that are on image border as 2 or 3" ) 
        self.boundary_cells = fwid.add_check( "Tissue boundaries", True, None, descr="Class cells that are on tissue edges as 2 " ) 

        gbound_layout.addWidget( self.boundary_cells )
        gbound_layout.addWidget( self.border_cells )
        self.gBound.setLayout( gbound_layout )

    
    def create_projthreshold(self):
        """ GUI of projection initialization """
        self.gProj = QGroupBox("Projection+threshold")

        gproj_layout = QVBoxLayout()

        thres, self.thres_mean = fwid.value_line( "Threshold:", 1.5, descr="Threshold of mean projected intensity to consider a pixel positive" )
        gproj_layout.addLayout(thres)

        areaprop, self.area_prop = fwid.value_line( "Prop area above threshold:", 0.25, descr="Proportion of cell area that has to be positive (above threhsolde) to consider the cell as positive" ) 
        gproj_layout.addLayout(areaprop)

        self.gProj.setLayout(gproj_layout)
    
    def create_feature(self):
        """ Create a new feature classification and open edition widget """
        prefill_img = None
        feature_name = self.cc.features_list.currentText()
        if not feature_name.startswith("Feat_"):
            feature_name = "Feat_"+feature_name
            
        if feature_name+"Cells" in self.cc.viewer.layers:
            show_info("Feature "+feature_name+" already present, close it or choose another name")
            return
        
        ## Apply selected initialization  
        if self.prefill.currentText() == "Initialize all cells at 1":
            prefill_img = np.zeros(self.cc.mig.get_image_shape(in2d=True), np.uint8)
            prefill_img[self.cc.labimg.data>0] = 1
            self.cc.mig.fillFeature( feature_name, 1 )

        if self.prefill.currentText() == "channel projection+threshold":
            prefill_img = self.project_and_threshold(feature_name)

        if self.prefill.currentText() == "Boundary cells":
            prefill_img = self.class_boundary_cells( feature_name )
        
        channel = int(self.nchannel.text())
        if self.show_projection.isChecked():
            ## Show projection image if option is selected
            if "ProjC"+str(channel) not in self.cc.viewer.layers:
                img = self.cc.mig.get_channel(channel)
                proj = np.mean(img, axis=0)
                colmap = self.cc.viewer.layers["originalChannel"+str(channel)].colormap
                projlay = self.cc.viewer.add_image(proj, name="ProjC"+str(channel), scale=(self.cc.mig.scaleXY, self.cc.mig.scaleXY), colormap=colmap, blending="additive")
                projlay.contrast_limits = ut.quantiles(proj) 
                projlay.gamme = 0.95
            
        nb_values = int(self.nbclass.text())
        channel = int(self.nchannel.text())
        edit_feat = EditFeature(  self.cc.viewer, self.cc.mig, self.cc.labimg, self.cc.table, prefill_img, feature_name, nb_values, channel )
        self.cc.viewer.window.add_dock_widget( edit_feat, name="Edit "+feature_name )
        #self.cc.add_one_feature(feature_name, prefill_img, nb_values, channel)
        self.cc.features_list.addItem( feature_name )
        self.hide()
    
    def project_and_threshold(self, featname):
        """ Calculate the projection and initialize classification by thresholding it """
        chan = int(self.nchannel.text())
        threshold_mean = float(self.thres_mean.text())
        threshold_fill = float(self.area_prop.text()) 
        return self.cc.mig.classifyCells( featname, chan, threshold_mean, threshold_fill )

    def class_boundary_cells( self, featname ):
        """ Class the cells according to touching boundary/edge or not """
        boundary = int(self.boundary_cells.isChecked() * 2) 
        border = int(self.border_cells.isChecked() * 2 + boundary / 2)
        return self.cc.mig.classifyBoundaryCells( featname, border, boundary ) 
