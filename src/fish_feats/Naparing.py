import napari
import os, pathlib
import numpy as np
import time
from magicgui import magicgui
from napari.qt import create_worker, thread_worker
from qtpy.QtWidgets import QApplication, QWidget, QVBoxLayout
import fish_feats.MainImage as mi
import fish_feats.Configuration as cf
import fish_feats.Utils as ut
from fish_feats.NapaRNA import NapaRNA
from fish_feats.NapaCells import MainCells, Position3D 
from fish_feats.NapaNuclei import MeasureNuclei, NucleiWidget, PreprocessNuclei 
from fish_feats.FishGrid import FishGrid
from fish_feats.NapaMix import CheckScale, CropImage, Association
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

    image_path = fwid.file_dialog( "Select image path", "All files (*)", directory=mig.get_image_path() )
    
    global cfg 
    mig.set_image_path(image_path)
    ut.update_history(mig.imagedir)
    if cfg is None:
        cfg = cf.Configuration(mig.save_filename(), show=False)
    return endInit()

def checkScale():
    """ Interface to choose the image scales and channels """
    global cfg

    cs = CheckScale( viewer, mig, cfg, load_all_previous_files, divorceJunctionsNuclei, getChoices )
    wid = viewer.window.add_dock_widget(cs, name="Scale")
    cfg = cs.cfg
    return wid


#### Action choice
def getChoices(default_action='Get cells'):
    """ Launch the interface of Main step """
    choice = GetChoices( default_action, action_launcher )
    ut.remove_widget( viewer, "Main" )
    viewer.window.add_dock_widget(choice, name="Main")
    return choice

def action_launcher( action ):
    """ Launch the specified action """
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

    main_cells = MainCells( viewer, mig, cfg, divorceJunctionsNuclei, showCellsWidget, getChoices ) 
    if main_cells.proj is not None:
        viewer.window.add_dock_widget( main_cells.proj, name="JunctionProjection2D" )
    else:
        viewer.window.add_dock_widget( main_cells, name="Get cells" )


#######################################################################
###### Show cell in 3D and possibility to edit the Z position of cells
def show3DCells():
    """ Cells in 3D and update Z position of cells """
    cells_3D = Position3D( viewer, mig, cfg )
    viewer.window.add_dock_widget(cells_3D, name="Cells in 3D")


####################################################################
##### preprocessing functions
def preprocNuclei():
    """ Preprocess the nuclei before segmentation """
    preproc_nuclei = PreprocessNuclei( viewer, mig, cfg )
    viewer.window.add_dock_widget(preproc_nuclei, name="Preprocess Nuclei")


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

    do_association = Association( viewer, mig, cfg )
    viewer.window.add_dock_widget(do_association, name="Associating")


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
            ut.get_bblayer(layer, shapeName, dim, viewer, mig)
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

