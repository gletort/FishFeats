import deprojpy as dpp
import fish_feats.Utils as ut
import fish_feats.FishWidgets as fwid
from qtpy.QtWidgets import QWidget
import os
from qtpy.QtWidgets import QPushButton, QHBoxLayout, QVBoxLayout, QWidget, QGroupBox, QLineEdit, QComboBox, QLabel, QSpinBox, QCheckBox, QTabWidget, QFileDialog, QTableWidget, QTableWidgetItem, QGridLayout
from qtpy.QtCore import Qt
import numpy as np

class NapaDeProject( QWidget ):
    """
    GUI to correct the errors in measure of cell area/curvatures/perimeters... due to the 2D projection of 3D cells, relying on Deproj

    Deproj: https://github.com/Image-Analysis-Hub/DeProj, Herbert et al. 2021

    Deproj has been translated to python through deprojpy https://github.com/zen-laboratory/DeProjPy
    """

    def __init__( self, ffeats ):
        """ Interface to choose measures to correct """
        super().__init__()
        self.viewer = ffeats.viewer
        self.ffeats = ffeats
        heightmap_path = ffeats.mig.get_filename( "_heightmap.tif", ifexist=True )
        if heightmap_path == "":
            heightmap_path = ffeats.mig.get_filename( "_zmap.tif", ifexist=True )

        ## Widget interface
        layout = fwid.get_layout()

        # height map file
        heightfile_line, self.heightmap_file = fwid.file_line( title="Heightmap_file:", default_path=heightmap_path, dial_msg="Choose height map file", descr="Choose the height map image, provided by the projection algorithm or reconstructed, see https://github.com/Image-Analysis-Hub/DeProj#the-height-map" )
        layout.addLayout( heightfile_line )

        deproj_btn = fwid.add_button("Deproj", self.deproj_measure, descr="Run deproj analysis")
        layout.addWidget( deproj_btn )
        self.setLayout( layout )

    def deproj_measure( self ):
        """ Perform the corrected measure with deprojpy """
        
        labels = self.ffeats.mig.getCellSegmentation() 
        if labels is None:
            ut.show_error( "No cell segmentation found. Do Cell:segment before to load a segmentation file or do the segmentation" )
            return
        heightmap_path = self.heightmap_file.text()
        print(heightmap_path)
        if not os.path.exists( heightmap_path ):
            ut.show_error( "Heightmap file "+heightmap_path+" not found. Select the correct heightmap file or generate. See https://github.com/Image-Analysis-Hub/DeProj#the-height-map for more" ) 
            return
        heightmap, _, _, _ = ut.open_image( heightmap_path )
        import labelimage_tools as lit
        labels = lit.dilate_labels(labels)
        result = dpp.from_labels( labels, heightmap,
    pixel_size=self.ffeats.mig.scaleXY, voxel_depth=self.ffeats.mig.scaleZ, units="µm",
    invert_z=(self.ffeats.mig.zdirection<0), inpaint_zeros=True, prune_zeros=True, drop_border_cells=False)
        dfresult = result.to_dataframe()
        dfresult.rename( columns={"source_label": "CellLabel"}, inplace=True)
        deproj_table = DeProjTable( self.viewer, self.ffeats.mig, dfresult, labels )
        self.viewer.window.add_dock_widget(deproj_table, name="Deproj results")


class DeProjTable(QWidget):
    """ Widget to visualize and interact with the corrected measurement table """

    def __init__( self, napari_viewer, mig, df, labels ):
        super().__init__()
        self.viewer = napari_viewer
        self.mig = mig
        self.labels = labels
        self.df = df

        self.wid_table = QTableWidget()
        self.wid_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout = fwid.get_layout()
        grid_layout = QGridLayout()
        grid_layout.addWidget(self.wid_table)
        layout.addLayout( grid_layout )
        #self.wid_table.clicked.connect(self.show_label)
        self.wid_table.setSortingEnabled(True)
        self.set_table(df)

        featmap, self.show_deproj_features = fwid.list_line( "Draw feature map:", descr="Add a layer with the cells colored by the selected feature value", func=self.show_feature )
        layout.addLayout(featmap)
        self.setLayout( layout )
        self.list_deproj_features()

    def list_deproj_features(self):
        """ List all possible features returned by Deproj """
        self.show_deproj_features.clear()
        self.show_deproj_features.addItem("")
        deproj_features = self.get_features_list()
        for feat in deproj_features:
            self.show_deproj_features.addItem(feat)

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
                if value == "" or value < 0:
                    value = "0"
                item.setData( Qt.EditRole, float(value))
                self.wid_table.setItem(r, c, item)
    
    def draw_map(self, featname, labels, values ):
        """ Add image layer of values by label """
        self.viewer.window._status_bar._toggle_activity_dock(True)
        labels = np.array(labels)
        values = np.array(values)
            
        segdata = self.labels
        mapping = np.zeros(segdata.max()+1, dtype="float16")
        mapping[:] = np.nan
        mapping[labels] = values 
        mapfeat = mapping[segdata] 
        
        ut.remove_layer(self.viewer, "Deproj_"+featname)
        self.viewer.add_image(mapfeat, name="Deproj_"+featname, scale=(self.mig.scaleXY, self.mig.scaleXY) )
        self.viewer.window._status_bar._toggle_activity_dock(False)

    def show_feature(self):
        """ Add the image map of the selected feature """
        feat = self.show_deproj_features.currentText()
        if (feat is not None) and (feat != ""):
            feats = self.get_features_list()
            if feat in feats:
                values = list(self.df[feat])
                labels = list(self.df["CellLabel"])
                self.draw_map( feat, labels, values )