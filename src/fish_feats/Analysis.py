"""
   To handle post pipeline analysis
   - Hierarchical clustering: from csv results file and segmented cells, perform and display clustering.

"""

import numpy as np
import pathlib, os, csv

import matplotlib as mpl
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
        
from scipy.cluster.hierarchy import dendrogram
from scipy.cluster.hierarchy import fcluster
from scipy.spatial.distance import pdist, squareform 
from scipy.cluster.hierarchy import ward
from skimage.io import imsave
from sklearn.preprocessing import scale

import napari
from magicgui import magicgui
from napari.utils.notifications import show_info

import fish_feats.Utils as ut
import fish_feats.MainImage as mi

## disable scipy cluster warning
from scipy.cluster.hierarchy import ClusterWarning
from warnings import simplefilter
simplefilter("ignore", ClusterWarning)

def do_hierarchy():
    mig = mi.MainImage( talkative=True )
    viewer = napari.current_viewer()
    viewer.title = "ZENnapari"
    
    filename = ut.dialog_filename()
    if filename is None:
        print("No file selected")
        return
    
    mig.open_image( filename=filename )
    ut.update_history(mig.imagedir)
    
    for chanel in range(mig.nbchannels):
        cmap = ut.colormapname(chanel)
        img = mig.get_channel(chanel)
        cview = viewer.add_image( img, name="originalChannel"+str(chanel), blending="additive", scale=(mig.scaleZ, mig.scaleXY, mig.scaleXY), colormap=cmap )
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
        ):
        mig.scaleXY = scaleXY
        mig.scaleZ = scaleZ
        for chan in range(mig.nbchannels):
            viewer.layers['originalChannel'+str(chan)].scale = [mig.scaleZ, mig.scaleXY, mig.scaleXY]
        ut.remove_all_widgets(viewer)
        mig.load_segmentation( segmented_cells )
        mig.popFromJunctions()
        
        hiera = HierAnalysis()
        hiera.set(mig, viewer)
        hiera.get_data()
    
    wid = viewer.window.add_dock_widget(get_scale, name="Scale")
    return wid

############ hierarchical analysis
class HierAnalysis:
    """ Perform and display hierarchical analysis based on selected features """

    def __init__(self):
        self.nclusters = 4
        self.wid = None
        self.clustward = None

    def set(self, mig, viewer):
        self.mig = mig
        self.viewer = viewer
        self.cluster_img = np.zeros(mig.get_image_shape(in2d=True), np.uint8)
        self.featlayer = self.viewer.add_labels(self.cluster_img, name="ClusteredCells", scale=(mig.scaleXY, mig.scaleXY), opacity=1)

    def get_data(self):
        """ Interface to select the file and the parameters """
        def load_file():
            """ Load the excel/csv file """
            with open(get_columns.load_file.value, 'r') as infile:
                csvreader = csv.DictReader(infile)
                print(csvreader.fieldnames)
                get_columns.use_column.choices = csvreader.fieldnames
        
        def load_table():
            """ Load the specific columns """
            keep = get_columns.use_column.value
            self.prepare_data( get_columns.load_file.value, keep )
            self.show_clusters()
        
        def update_clusters():
            """ Update all with the new number of clusters chosen """
            self.nclusters = int(get_columns.nb_clusters.value)
            self.show_clusters()

        def save_cluscells():
            """ Save image of cells colored by cluster """
            ccells = self.featlayer.data
            outname = self.mig.build_filename( endname="_ClusteredCells_nclus_"+str(self.nclusters)+".png" )
            vis = []
            for lay in self.viewer.layers:
                vis.append(lay.visible)
                lay.visible = False
            self.featlayer.visible = True
            screenshot = self.viewer.screenshot()
            for visib, lay in zip(vis, self.viewer.layers):
                lay.visible = visib

            imsave(outname, screenshot)
            show_info("Saved in "+outname)

        def save_dendrogram_img():
            """ Save image of dendrogram to file """
            outname = self.mig.build_filename(endname="_ClusterDendrogram_nclus_"+str(self.nclusters)+".png")
            self.fig.savefig(outname)
            show_info("Saved in "+outname)


        @magicgui(call_button="Cluster from selected columns", 
            use_column = dict(widget_type="Select", choices=[]), 
            nb_clusters={"widget_type": "Slider", "min":1, "max": 50},
            save_clustered_cells={"widget_type":"PushButton", "value": False},
            save_dendrogram={"widget_type":"PushButton", "value": False},
            )
        def get_columns( 
            #load_file=pathlib.Path(self.mig.rnacount_filename(ifexist=True)),
            load_file=pathlib.Path(self.mig.resdir),
            use_column = [],
            nb_clusters = 4,
            save_clustered_cells=False, save_dendrogram=False,
            ):
            load_table()
        
        get_columns.load_file.changed.connect(load_file)
        get_columns.nb_clusters.changed.connect(update_clusters)
        get_columns.save_clustered_cells.clicked.connect(save_cluscells)
        get_columns.save_dendrogram.clicked.connect(save_dendrogram_img)
        self.viewer.window.add_dock_widget( get_columns, name="Load data" )
        

    def get_cluster_colors(self):
        """ To have same color between the label layer and the matplotlib plot """
        return [0] + [mpl.colors.rgb2hex(self.featlayer.get_color(i+1)) for i in range(self.nclusters)]

    def check_label(self, columns, lab):
        """ Check if a label is in the list that should not """
        if lab in columns:
            ut.show_warning("Warning, "+lab+" is in the selected features list, that's weird")

    def prepare_data(self, filename, columns):
        """ normalisation of the data """
        res = []
        self.labels = []
        self.check_label(columns, "CellLabel")
        self.check_label(columns, "CellID")
        self.check_label(columns, "NucleusID")
        self.check_label(columns, "NucleusLabel")
        with open(filename, 'r') as infile:
            csvreader = csv.DictReader(infile)
            for row in csvreader:
                cres = []
                clab = int(row["CellLabel"])
                for col in columns:
                    cres.append(float(row[col])+1)
                res.append(cres)
                self.labels.append(clab)
            tab = np.array(res)    
            nans = np.isnan( res ).any( axis=1 )
            kinds = [ind for ind in range(tab.shape[0]) if not nans[ind] ] 
            tab = tab[ kinds ]
            self.labels = [ self.labels[ind] for ind in kinds]
            negs = ( tab<0 ).any( axis=1 )
            kinds = [ind for ind in range(tab.shape[0]) if not negs[ind] ] 
            tab = tab[ kinds ]
            self.labels = [ self.labels[ind] for ind in kinds]
            tab = np.log(tab)
            tab = scale(tab)
            print(tab.shape)

        dist_tab = pdist(tab, metric='euclidean')
        dist_tab = squareform(dist_tab)
        self.clustward = ward(dist_tab)

       
    def show_clusters(self):
        """ Show dendogram and classified cells """
        if self.clustward is None:
            return
        clustered = fcluster(self.clustward, t=self.nclusters, criterion="maxclust")
        
        self.mig.set_cells(self.cluster_img, clustered, self.labels)
        self.featlayer.refresh()
        #self.cmap = self.featlayer.colormap.colors 
        if self.wid is None:
            self.wid = self.create_plotwidget()
        self.update_plotwidget(clustered)
        if not ut.has_widget( self.viewer, "Dendrogram" ):
            self.viewer.window.add_dock_widget( self.wid, name="Dendrogram" )

    def create_plotwidget(self):
        mpl_widget = FigureCanvas( Figure(figsize=(6,6) ) )
        self.fig = mpl_widget.figure
        self.ax = mpl_widget.figure.subplots()
        return mpl_widget

    def update_plotwidget(self, clustered):
        clus_str = [ f"cluster #{l}: n={c}\n" for (l,c) in zip(*np.unique(clustered, return_counts=True)) ]

        cluster_colors = self.get_cluster_colors()
        cluster_colors_array = [cluster_colors[cl] for cl in clustered]
        link_cols = {}
        for i, i12 in enumerate(self.clustward[:,:2].astype(int)):
            c1, c2 = (link_cols[x] if x > len(self.clustward) else cluster_colors_array[x] for x in i12)
            link_cols[i+1+len(self.clustward)] = c1 if c1 == c2 else 'k'
    
        self.ax.cla()
        dend = dendrogram(self.clustward, p=8, truncate_mode='level', no_labels=True, ax=self.ax, link_color_func=lambda x: link_cols[x] )
        self.fig.canvas.draw_idle()
        #plt.show()

