from qtpy.QtWidgets import QPushButton, QHBoxLayout, QVBoxLayout, QWidget, QGroupBox, QCheckBox, QSpinBox, QSlider, QDoubleSpinBox, QLabel, QComboBox, QLineEdit, QFileDialog, QTabWidget, QListWidget, QAbstractItemView
import fish_feats.Utils as ut
import os, pathlib
import numpy as np
import napari
from napari.utils.translations import trans
import time
from math import ceil

class FishGrid(QWidget):
    """ Show/Load a grid to have a repere in space """

    def __init__(self, napari_viewer, mig):
        super().__init__()
        self.viewer = napari_viewer
        self.mig = mig
        
        ## define interface
        layout = QVBoxLayout()
        self.get_parameters()
        layout.addWidget(self.group_grid)
        self.setLayout(layout)

    def get_parameters(self):
        """ Get grid parameters """
        self.group_grid = QGroupBox("Grid setup")
        grid_layout = QVBoxLayout()
        ## nrows
        rows_line = QHBoxLayout()
        rows_lab = QLabel()
        rows_lab.setText("Nb rows:")
        rows_line.addWidget(rows_lab)
        self.nrows = QLineEdit()
        self.nrows.setText("4")
        rows_line.addWidget(self.nrows)
        grid_layout.addLayout(rows_line)
        ## ncols
        cols_line = QHBoxLayout()
        cols_lab = QLabel()
        cols_lab.setText("Nb columns:")
        cols_line.addWidget(cols_lab)
        self.ncols = QLineEdit()
        self.ncols.setText("4")
        cols_line.addWidget(self.ncols)
        grid_layout.addLayout(cols_line)
        ## go for grid
        btn_add_grid = QPushButton("Add grid", parent=self)
        grid_layout.addWidget(btn_add_grid)
        btn_add_grid.clicked.connect(self.add_grid)
        self.group_grid.setLayout(grid_layout)

    def add_grid(self):
        """ Create/Load a new grid and add it """
        ut.remove_layer(self.viewer, "FishGrid")
        imshape = self.mig.image_2dshape()
        if imshape is None:
            ut.show_error("Load the image first")
            return
        nrows = int(self.nrows.text())
        ncols = int(self.ncols.text())
        wid = ceil(imshape[0]/nrows)
        hei = ceil(imshape[1]/ncols)
        rects = []
        rects_names = []
        for x in range(nrows):
            for y in range(ncols):
                rect = np.array([[x*wid, y*hei], [(x+1)*wid, (y+1)*hei]])
                rects.append(rect)
                rects_names.append(chr(65+x)+"_"+str(y))
        self.viewer.add_shapes(rects, name="FishGrid", text=rects_names, face_color=[1,0,0,0], edge_color=[0.7,0.7,0.7,0.7], edge_width=3, scale=(self.mig.scaleXY, self.mig.scaleXY))

