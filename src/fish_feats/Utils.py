import numpy as np
import os, csv, time
import glob
import matplotlib as plt
from napari.utils.translations import trans
from napari.utils.history import get_save_history, update_save_history 
from qtpy.QtWidgets import QFileDialog
from magicgui.widgets import TextEdit
from magicgui.widgets import Table
import vispy.color
from napari.utils import notifications as nt
from napari.utils import progress # type: ignore
import webbrowser
from packaging.version import Version
import napari
from skimage.segmentation import find_boundaries
from skimage.morphology import binary_closing, binary_dilation, disk
import gc

"""
    Set of common functions for Fish&Feats pipeline
"""

#### Napari plugin functions
def show_info(message):
    """ Display information window in napari """
    nt.show_info(message)

def show_warning(message):
    """ Display a warning in napari (napari function show_warning doesn't work) """
    mynot = nt.Notification(message, nt.NotificationSeverity.WARNING)
    nt.notification_manager.dispatch(mynot)

def show_error(message):
    """ Display an error in napari (napari function show_error doesn't work) """
    mynot = nt.Notification(message, nt.NotificationSeverity.ERROR)
    nt.notification_manager.dispatch(mynot)

def show_debug(message):
    """ Display an info for debug in napari (napari function show_debug doesn't work) """
    mynot = nt.Notification(message, nt.NotificationSeverity.DEBUG)
    nt.notification_manager.dispatch(mynot)

def show_progress( viewer, show ):
    """ Show.hide the napari activity bar to see processing progress """
    viewer.window._status_bar._toggle_activity_dock( show )

def start_progress( viewer, total, descr=None ):
    """ Start the progress bar """
    show_progress( viewer, True)
    progress_bar = progress( total )
    if descr is not None:
        progress_bar.set_description( descr )
    return progress_bar

def close_progress( viewer, progress_bar ):
    """ Close the progress bar """
    progress_bar.close()
    show_progress( viewer, False)

def get_time():
    """ Returns current time"""
    return time.time()

def show_duration(start_time, header=None):
    if header is None:
        header = "Processed in "
    #show_info(header+"{:.3f}".format((time.time()-start_time)/60)+" min")
    print(header+"{:.3f}".format((time.time()-start_time)/60)+" min")


def show_documentation_page(page):
    """ Open the wiki documentation """
    webbrowser.open_new_tab("https://gletort.github.io/FishFeats/"+page)

def get_color( obj ):
    """ Returns the color of the object """
    if obj == "help":
        return "#665071"
    if obj == "save":
        return "#455873" #"#5F6BFA"
    if obj == "load":
        return "#1D3658" #"#5F6BFA"
    if obj == "done":
        return "#7A0FF5"
    if obj == "go":
        return "#2C78B692"
    if obj == "light":
        return "#B1B7F8"
    if obj == "group1":
        return "#384f54" #"#4c617f"
    if obj == "group2":
        return "#363650"
    if obj == "group3":
        return "#212a37"
    return "#000000"

def dialog_filename():
    dialog = QFileDialog()
    hist = get_save_history()
    dialog.setHistory(hist)
    dialog.setFileMode(QFileDialog.ExistingFile)
    dialog.setDirectory(hist[0])
    if dialog.exec_():
        filename = dialog.selectedFiles()
    if filename:
        return filename[0]
    else:
        return None

def do_nothing(viewer):
    return

def update_history(mdir):
    update_save_history(mdir)

def quantiles(img):
    """ Returns quantiles for contrast setting """
    return tuple(np.quantile(img, [0.01, 0.9999]))

def main_shortcuts(viewer):
    """ Open a new text window with the main shortcuts and help """
    blabla = TextEdit()
    blabla.name = "Fish&Feats shortcuts"
    text = "-------------------------- Fish&Feats -------------------------- \n"
    text += view_shortcuts()
    text += labels_shortcuts( level = 1 )
    text += association_shortcuts()
    text += rnas_shortcuts()
    text += pos3d_shortcuts()
    text += classify_shortcuts()
    blabla.value = text
    blabla.show()
    return blabla

def help_shortcut( step ):
    """ Main shortcuts to display for each step"""
    if step == "view":
        help_text = "<h> show/hide this message \n"
        help_text += "<Ctrl-h> open main shortcuts list \n"
        help_text += "<F1>, <F2>... show/hide the first/second... layer \n"
        return help_text
    if step == "pos3d":
        help_text = "<Right-click> on a cell to get its label in the cell_label parameter \n"
        help_text = help_text + "<Control+left-click> when the viewer is at the correct Z position to set it in the place_at_z parameter \n"
        return help_text
    if step == "classify":
        text = "Press <i>/<d> to increase/decrease the filling value (category)\n"
        text += "<Control+Left-click> on a cell to assign it the current filling value \n"
        text += "<Right-click> on a cell to select it and get its value \n" 
        text += "<F1>, <F2>... show/hide the first/second... layer \n"
        return text
    if step == "projection":
        text = "<h> to show/hide this message \n"
        text += "<F1>, <F2>... show/hide the first/second... layer \n"
        text += "Junctions are segmented in 2D and then back-projected to their Z location \n"
        text += "Load a file of the 2D projection or calculate it now \n"
        return text

def scale_shortcuts():
    """ Help message for metadata interface """
    help_text = "Check and correct the scaling information \n"
    help_text += "Choose the color channels in which the junction and nuclei staining are (the channel numbers should be the same as the layer names originalChannel*) \n"
    help_text += "\'load previous\' option will load all saved files (in results folder) for the current images \n"
    return help_text

def view_shortcuts():
    """ Viewing shortcuts list """
    text = "---------- Main viewing shortcuts, always active \n"
    text += "  <Ctrl+Y> switch 2D/3D view mode \n"
    text += "  <Ctrl-v> in 3D, switch vispy mode ON/OFF \n"
    text += "  <v> show/hide current selected layer \n"
    text += "  <Ctrl+R> reset view \n"
    text += "  <left arrow> go to previous frame \n"
    text += "  <right arrow> go to next frame \n"
    text += "  <Ctrl+G> switch Grid/Overlay view mode \n"
    text += "  <g> show/hide fish grid \n"
    text += help_shortcut("view")
    text += "\n"
    return text

def classify_shortcuts():
    """ Shortcuts for cell classification """
    text = " ---------- Cell classification shortcuts (the feature layer should be active) \n"
    text += help_shortcut("classify")
    text += "\n"
    return text

def pos3d_shortcuts():
    """ Shortcuts for 3D positionning of cells """
    text = " ---------- 3D positionning shortcuts, active on CellContours layer \n"
    text = text + help_shortcut("pos3d")
    text += "\n"
    return text

def labels_shortcuts( level=1 ):
    text = ""
    if level >= 1:
        text += " ---------- labels options (for cells and nuclei) \n"
        text += "  <2> painting brush mode \n"
        text += "  <3> fill mode \n"
        text += "  <4> select label mode \n"
        text += "  <5> Swith to zoom/moving mode \n"
        text += "  <[> or <]> increase/decrease the paint brush size \n"
    text += "  <p> activate/deactivate preserve labels option \n"
    text += "  <m> to set current label to max+1 value \n"
    text += "  <l> to show/hide cell/nuclei labels. "
    if level >= 1:
        text += "It creates a new layer with the object label (number) around each object position. \n"
    else:
        text += "\n"
    text += "  <Ctrl-c>/<Ctrl-d> increase/decrease label contour size (0=full)\n"
    text += "  <Control+left click> from one label to another to merge them (the label kept will be the last one) \n"
    text += "  <Control+right-click> on a label to erase it \n" 
    if level >= 1:
        text += " Double <Left-click> to zoom in \n"
        text += "\n"
        text += "For 3D: \n"
        text += "In 3D, most label actions wont work if Vispy perspective is ON. Switch it off with 'Ctrl-v' before.\n"
        text += "If n_edit_dim is set on 3 (top left panel), edition will affect all or several z (slices) \n"
        text += "If n_edit_dim is set on 2, edition will only affect the active slice \n"
        text += "\n"
    return text

def association_shortcuts():
    """ Shorcuts for junction-nuclei association manual correction """
    help_text = " ---------- Association options (link nucleus to corresponding cell) \n"
    help_text += "<Double-click> to select a nucleus to correct \n"
    help_text = help_text + "<Right-click> to choose the cell to associate with \n"
    help_text = help_text + "<c> to apply current association \n"
    help_text = help_text + "<l> to show/hide cell labels \n"
    help_text = help_text + "<s> to synchronize junctions and nuclei view \n"
    help_text = help_text + "<u> to unsynchronize junctions and nuclei view \n"
    help_text += "  <Ctrl-c>/<Ctrl-d> increase/decrease NUCLEI label contour (0: full) \n"
    help_text += "  <Alt-c>/<Alt-d> increase/decrease JUNCTIONS label contour (0: full) \n"
    help_text += "\n"
    return help_text


def rnas_shortcuts():
    text = " -------------- Points options (for RNA dots) \n"
    text += "  <2> add points mode \n"
    text += "  <3> select points mode \n"
    text += "  <4> Pan/zoom \n"
    text += "  <A> select all visible points \n" 
    text += "  <v> to show/hide cell contours \n"
    text += "  <Right-click> on a cell to set the assignement value \n"
    text += "  <c> assign selected points to the current assignement value \n"
    text += "  <u> select all unsassigned points \n"
    text += "  <s> select points with current assignement value\n"
    text += "  <o> show only selected points \n"
    text += "  <r> reset, show all points \n"
    text += "  <l> switch show only selected cell/all cells \n"
    text += "  <Ctrl-v> switch Vispy perspective mode on/off \n"
    text += "\n"
    return text

def helpHeader(viewer, layname = None):
    text = "------------- ShortCuts ---------------- \n"
    if layname is not None:
        text = text + "If layer "+layname+" is active: \n"
    text = text + "<h> show/hide this help message \n"
    return text

def removeOverlayText(viewer):
    viewer.text_overlay.text = trans._("")
    viewer.text_overlay.visible = False

def showOverlayText(viewer, text, size=13, col="white" ):
    viewer.text_overlay.text = trans._(text)
    viewer.text_overlay.visible = True
    viewer.text_overlay.font_size = size
    viewer.text_overlay.color = col
    viewer.text_overlay.position = "top_left"

def showHideOverlayText(viewer, vis=None):
    """ Show on/off overlay text """
    if vis is None:
        viewer.text_overlay.visible = not viewer.text_overlay.visible
    else:
        viewer.text_overlay.visible = vis

def get_layer(viewer, layname):
    if layname in viewer.layers:
        return viewer.layers[layname]
    return None

def set_active_layer(viewer, layname):
    """ Set the current Napari active layer """
    if layname in viewer.layers:
        viewer.layers.selection.active = viewer.layers[layname]

def view_3D( viewer ):
    """ Put the viewer in 3D mode """
    viewer.dims.ndisplay = 3

def remove_all_layers( viewer ):
    """ Remove all open layers """
    viewer.layers.clear()

def remove_layer(viewer, layname):
    if layname in viewer.layers:
        viewer.layers.remove(layname)

def remove_all_widget( viewer ):
    """ Remove all widgets """
    viewer.window.remove_dock_widget("all")

def list_widgets( viewer ):
    """ List all open widgets """
    if not version_napari_above("0.6.1"):
        return list(viewer.window._dock_widgets.keys())
    return list(viewer.window.dock_widgets.keys())

def has_widget( viewer, widname ):
    """ Check if given widget is open """
    if not version_napari_above("0.6.1"):
        return widname in viewer.window._dock_widgets
    return widname in viewer.window.dock_widgets

def remove_widget(viewer, widname):
    """ Remove a widget from the viewer """
    if not version_napari_above("0.6.1"):
        ## functions changed in recent version
        if widname in viewer.window._dock_widgets:
            wid = viewer.window._dock_widgets[widname]
            wid.setDisabled(True)
            try:
                wid.disconnect()
            except:
                #print("Widget "+widname+" deleted but not disconnected (pyside2)")
                pass
            del viewer.window._dock_widgets[widname]
            wid.destroyOnClose()
    else:
        if widname in viewer.window.dock_widgets:
            if not version_napari_above("0.6.2"):
                wid = viewer.window.dock_widgets[widname]
                wid.setDisabled(True)
                try:
                    wid.disconnect()
                except:
                    #print("Widget "+widname+" deleted but not disconnected (pyside2)")
                    pass
                del viewer.window._dock_widgets[widname]
                wid.destroyOnClose()
            else:
                viewer.window.remove_dock_widget( viewer.window.dock_widgets[widname] )

def hide_color_layers(viewer, mig):
    """ Hide all the originalChannel layers """
    for chan in range(mig.nbchannels):
        viewer.layers["originalChannel"+str(chan)].visible = False

def show_layer(viewer, chan):
    """ Show the color layer nchan """
    viewer.layers["originalChannel"+str(chan)].visible = True


def scale_layer( viewer, layer, scale_tuple ):
    """ Scale the layer to the scale_tuple """
    if layer in viewer.layers:
        viewer.layers[layer].scale = scale_tuple
        viewer.layers[layer].refresh()

### color maps
def colormaps():
    mixor = vispy.color.Colormap([[0.0, 0.0, 0.0], [0.9, 0.5, 0.6]])
    mixgr = vispy.color.Colormap([[0.0, 0.0, 0.0], [0.4, 0.75, 0.55]])
    mix5 = vispy.color.Colormap([[0.0, 0.0, 0.0], [0.45, 0.35, 0.25]])
    mixbl = vispy.color.Colormap([[0.0, 0.0, 0.0], [0.55, 0.45, 0.75]])
    mix4 = vispy.color.Colormap([[0.0, 0.0, 0.0], [0.65, 0.7, 0.85]])
    return ["red", "green", "blue", "yellow", "cyan", "gray", "magenta", "bop orange", "bop purple", "bop blue", mixor, mix5, mixbl, mixgr, mix4]


def colormapname( i ):
    colorsmaps = colormaps()
    ncolmaps = len(colorsmaps)
    return colorsmaps[(i%ncolmaps)]
    
def create_labelmap():
    cmap = plt.cm.gist_rainbow
    tabmap = np.arange(cmap.N)
    np.random.shuffle(tabmap)
    my_cmap = cmap(tabmap)
    alph = np.repeat(1, cmap.N)
    alph[0] = 0
    my_cmap[:, -1] = alph
    return my_cmap

#### opening/writing
def openims(imagepath, verbose=True):
    """ Open ims image """
    from imaris_ims_file_reader.ims import ims
    img = ims(imagepath, squeeze_output=True )
    image = np.array(img[0])
    scaleXY = img.resolution[1]
    if img.resolution[2] != scaleXY:
        print("Warning, scale is not the same in X and Y, not implemented yet")
    scaleZ = img.resolution[0]
    if verbose:
        print("Initial image shape: "+str(image.shape))    ## Y et X sont inverses, Z, Y, X
    nchan = img.Channels
    names = []
    try:
        if nchan > 0:
            for i in range(nchan):
                name = img.read_attribute("DataSetInfo/Channel "+str(i), 'DyeName')
                names.append(name)
    except:
        names = []
    img = None

    return (np.squeeze(image), scaleXY, scaleZ, names)

def writeims(imagepath, img, verbose=True):
    ## libraries pb, must install hdf5, ImarisWriter
    from PyImarisWriter import PyImarisWriter as pw
    imshape = img.shape
    image_size = pw.ImageSize(x=imshape[2], y=imshape[1], z=imshape[0], c=1, t=1)
    dimension_sequence = pw.DimensionSequence('z', 'y', 'x', 'c', 't')
    block_size = image_size
    sample_size = pw.ImageSize(x=1, y=1, z=1, c=1, t=1)
    output_filename = 'outifle.ims'

    options = pw.Options()
    options.mNumberOfThreads = 12
    options.mCompressionAlgorithmType = pw.eCompressionAlgorithmGzipLevel2
    options.mEnableLogProgress = True

    application_name = 'PyImarisWriter'
    application_version = '1.0.0'

    #callback_class = MyCallbackClass()
    converter = pw.ImageConverter("uint8", image_size, sample_size, dimension_sequence, block_size,
                                  output_filename, options, application_name, application_version, None)

    num_blocks = image_size / block_size

    block_index = pw.ImageSize()
    for c in range(num_blocks.c):
        block_index.c = c
        for t in range(num_blocks.t):
            block_index.t = t
            for z in range(num_blocks.z):
                block_index.z = z
                for y in range(num_blocks.y):
                    block_index.y = y
                    for x in range(num_blocks.x):
                        block_index.x = x
                        if converter.NeedCopyBlock(block_index):
                            converter.CopyBlock(img, block_index)

    adjust_color_range = True
    image_extents = pw.ImageExtents(0, 0, 0, image_size.x, image_size.y, image_size.z)
    parameters = pw.Parameters()
    parameters.set_value('Image', 'ImageSizeInMB', 2400)
    parameters.set_value('Image', 'Info', 'Results Title')
    parameters.set_channel_name(0, 'My Channel 1')
    time_infos = [datetime.today()]
    color_infos = [pw.ColorInfo() for _ in range(image_size.c)]
    color_infos[0].set_color_table(configuration.mColor_table)

    converter.Finish(image_extents, parameters, time_infos, color_infos, adjust_color_range)

    converter.Destroy()
    print('Wrote file')

def writePng( img, imgname ):
    """ Save an image as png """
    import matplotlib.image
    matplotlib.image.imsave( imgname, img )

def writeTif(img, imgname, scaleXY, scaleZ, imtype):
    import tifffile
    ### channels and z
    if (scaleZ >= 0) and (len(img.shape)>3):
        arr = np.array( img, dtype=imtype )
        ## exhange C and Z axis for Fiji order
        arr = np.moveaxis( arr, 0, 1 )
        tifffile.imwrite(imgname, arr, imagej=True, resolution=[1./scaleXY, 1./scaleXY], dtype=imtype, metadata={'spacing': scaleZ, 'unit': 'um', 'axes': 'ZCYX'})
        return
    ### 2D
    if scaleZ < 0:
        tifffile.imwrite(imgname, np.array(img, dtype=imtype), imagej=True, dtype=imtype, resolution=[1./scaleXY, 1./scaleXY], metadata={'unit': 'um', 'axes': 'YX'})
    #### 3D
    else:
        tifffile.imwrite(imgname, np.array(img, dtype=imtype), imagej=True, dtype=imtype, resolution=[1./scaleXY, 1./scaleXY], metadata={'spacing': scaleZ, 'unit': 'um', 'axes': 'ZYX'})

def get_scale_of(racine, c):
    """ read scaling value from xml metadata """
    try:
        part = racine.xpath("//Distance [@Id = '%s']" % c)
        for neighbor in part[0].iter('Value'):
            pixel_in_meters = float(neighbor.text)
    except:
        pixel_in_meters = -1
    return pixel_in_meters*1000000

def get_fluo_names(racine):
    names = []
    try:
        for i in range(10):
            chans = racine.xpath("//Channel [@Id = \"Channel:%s\"]" % i)
            if len(chans) > 0:
                for j in range(len(chans)):
                    dyename = chans[j].findall("DyeName")
                    if len(dyename) > 0:
                        names.append(dyename[0].text)
    except:
        names = []
    return names

def openczi(imagepath, scene=0, verbose=True):
    """ Open czi image """
    import czifile
    from lxml import etree
    czi = czifile.CziFile(imagepath)
    image = czi.asarray()
    if verbose:
        print("Initial image shape: "+str(image.shape))

    if image.ndim >= 8:
        image = image[:,scene,:,:,:,:,:,:]  ## si contient 2 scenes

    # get scale
    root = etree.fromstring(czi.metadata())
    scaleXY = get_scale_of(root, "X")
    scaleXYcheck = get_scale_of(root, "Y")
    if scaleXY != scaleXYcheck:
        print("Warning, scale not the same in X and in Y, not implemented yet")
    scaleZ = get_scale_of(root, "Z")

    fluonames = get_fluo_names(root)
    return (np.squeeze(image), scaleXY, scaleZ, fluonames)

def getBestZ( img, verbose=True ):
    proj = np.sum(img, axis=1)  ## sum les x
    proj = np.sum(proj, axis=1) ## sum les y
    zref = np.where(proj==np.max(proj))[0][0]
    if verbose:
        print("Reference z: "+str(zref))
    return zref

def get_filename():
    try:
        from tkinter import Tk
        from tkFileDialog import askopenfilenames
    except:
        from tkinter import Tk
        from tkinter import filedialog

    Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
    filenames = filedialog.askopenfilenames() # show an "Open" dialog box and return the path to the selected file
    return filenames

def get_filelist(pattern):
    return glob.glob(pattern)


def opentif(imagepath, verbose=True):
    import tifffile as tif
    img = tif.TiffFile(imagepath)
    metadata = img.imagej_metadata
    names = []
    scaleXY = 1
    scaleZ = 1
    try:
        if metadata is not None:
            info = img.imagej_metadata["Info"]
            for i in range(10):
                ind = info.find("channels_channel_"+str(i)+"_dyename")
                if ind >= 0:
                    keep = info[ind:]
                    indend = keep.find("\n")
                    names.append(info[ind+28:ind+indend].strip())
     
            metadata = (img.imagej_metadata['Info']).splitlines()
            scaleXY = float(metadata[-4].split()[2])*1000000
            scaleZ = float(metadata[-2].split()[2])*1000000
    except:
        scaleXY = 0.25
        scaleZ = 1
    image = img.asarray()
    img.close()
    return image, scaleXY, scaleZ, names

def opentif_nonames(imagepath, verbose=True):
    import tifffile as tif
    img = tif.TiffFile(imagepath)
    metadata = img.imagej_metadata
    #print(metadata)
    scaleXY = 1
    scaleZ = 1
    names = []
    if metadata is not None:
        try:
            info = metadata["Info"]
            if info is not None: 
                metadatas = (info).splitlines()
                scaleXY = float(metadatas[-4].split()[2])*1000000
                scaleZ = float(metadatas[-2].split()[2])*1000000
        except:
            metadatas = None
        try:
            if metadata['spacing'] is not None:
                scaleZ = float(metadata['spacing'])
        except:
            metadatas = None
        try:
            if metadata['physicalsizex'] is not None:
                scaleXY = float(metadata['physicalsizex'])
        except:
            metadatas = None
            #print(info)
    image = img.asarray()
    img.close()
    return image, scaleXY, scaleZ, names

def arrange_dims(image, verbose=True):
    ## test if there is a channel dimension. If yes, put it first in the order
    if len(image.shape)>3:
        chanpos = np.where(image.shape==np.min(image.shape))[0][0]
        if chanpos != 0:
            image = image.swapaxes(chanpos, 0)

    ## if there is no channel dimension, add one to always have one
    if len(image.shape)<=3:
        image = np.expand_dims(image, axis=0)

    if verbose:
        print("Image dimensions: "+str(image.shape))

        return image

def extract_names(imagepath, subname="results"):
    """ From the image name, get specific paths """
    imgname = os.path.splitext(os.path.basename(imagepath))[0]
    imgdir = os.path.dirname(imagepath)
    resdir = os.path.join(imgdir, subname)
    if not os.path.exists(resdir):
        os.makedirs(resdir)
    return imgname, imgdir, resdir

def open_image(imagepath, verbose=True):
    """ Open an image from different format """
    ext = os.path.splitext(imagepath)[1]
    if ext == ".ims":
        return openims(imagepath, verbose)
    elif ext == ".czi":
        return openczi(imagepath, verbose)
    elif (ext == ".tif") or (ext == ".tiff"):
        return opentif_nonames(imagepath, verbose)
    else: 
        print("Image format not implemented yet")

def get_table_header(filepath):
    """ read the header of the csv file """
    with open(filepath, 'r') as infile:
        csvreader = csv.DictReader(infile)
        return csvreader.fieldnames

def show_table(results):
    """ Show the results in a table """
    tab = {}
    for k in results[0].keys():
        tab[k] = []
        for row in results:
            tab[k].append(row[k])
    Table(tab).show()

def load_table(filepath, column_names, verbose=True):
    """ Load a table results from a .csv file - Get only columns that are within column_names """
    res  = []
    with open(filepath, 'r') as infile:
        csvreader = csv.DictReader(infile)
        for row in csvreader:
            cres = []
            for col in column_names:
                cres.append(float(row[col]))
            res.append(cres)
    #print(res)
    return res

def load_dictlist(filepath, verbose=True):
    """ Load a list of dict results from a .csv file """
    res  = []
    with open(filepath, 'r') as infile:
        csvreader = csv.DictReader(infile)
        for row in csvreader:
            res.append(row)
    #print(res)
    return res

def load_dict_int(filepath, columns, verbose=True):
    """ Load a dict results from a .csv file, put value as int """
    res  = {}
    for col in columns:
        res[col] = []
    with open(filepath, 'r') as infile:
        csvreader = csv.DictReader(infile)
        for row in csvreader:
            for col in columns:
                res[col].append(int(row[col]))
    return res

def strip_keys( indict ):
    """ Ensures that all keys doens't have unnecessary spaces"""
    outdict = {}
    for key, value in indict.items():
        skey = key.strip()
        outdict[skey] = value
    return outdict

def write_dict(resfilepath, resdict):
    """ Write the content of resdict into a csv file """
    if isinstance(resdict, dict):
        with open(resfilepath, 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(resdict.keys())
            writer.writerows(zip(*resdict.values()))
    if isinstance(resdict, list):
        ## get list of possible keys
        allkeys = []
        for row in resdict:
            if isinstance(row, dict):
                keys = row.keys()
                for key in keys:
                    if key not in allkeys:
                        allkeys.append(key)
        with open(resfilepath, 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(allkeys)
            for row in resdict:
                wrow = []
                for key in allkeys:
                    if key not in row.keys():
                        wrow.append( -99999 )
                    else:
                        wrow.append(row[key])
                writer.writerow( wrow )

def select_slices(image, bestz, scaleZ, zmargin=10, rm_empty=True, verbose=True):
    """ Keep only slices around bestz and slices that contain signal """
    
    dz = int(zmargin/scaleZ)    ## keep 10 microns under and above reference z
    limLz = max(bestz-int(dz),0)  
    limHz = min(bestz+dz, (image[0,:,0,0].size))
    if verbose:
        print("Z limits "+str(limLz)+" "+str(limHz))

    ## Remove slices with nearly nothing
    if rm_empty:
        simage = np.sum(image, axis=0)
        zsimage = np.sum(simage, axis=1)
        zsimage = np.sum(zsimage, axis=1)
        empty = zsimage<np.mean(zsimage)-1*np.std(zsimage)
        while empty[limLz] and limLz<limHz:
            limLz += 1
        while empty[limHz-1] and limHz>limLz:
            limHz = limHz - 1

    if verbose:
        print("Final Z limits "+str(limLz)+" "+str(limHz))

    image = image[:,limLz:limHz,:,:]
    bestz = bestz-limLz
    if verbose:
        print('Global reference z: '+str(bestz))
    return image, bestz

def normalize_img(img, newmax=1):
    """ Return a normalised version of img """
    quantiles = np.quantile(img, [0.01,0.999])
    resimg = np.clip(img, quantiles[0], quantiles[1])
    resimg = (resimg*1.0-quantiles[0])/(quantiles[1]-quantiles[0])*newmax
    return resimg

#### Handle versions of napari
def version_napari_above( compare_version ):
    """ Get the current version of napari """
    return Version(napari.__version__) > Version(compare_version)

def add_point_layer( viewer, pts, colors, layer_name, mig, size=7, pts_properties=None ):
    """ Add a points layer to the viewer """
    if not version_napari_above("0.4.19"):
        points_layer = viewer.add_points( pts,
            face_color=colors, 
            size = size, 
            edge_width=0, 
            properties = pts_properties,
            name=layer_name,
            scale=(mig.scaleZ, mig.scaleXY, mig.scaleXY),
            out_of_slice_display = True, 
            blending="additive"
            )
    else:
        points_layer = viewer.add_points( pts,
            face_color=colors, 
            size = size, 
            border_width=0, 
            properties = pts_properties,
            name=layer_name,
            scale=(mig.scaleZ, mig.scaleXY, mig.scaleXY),
            out_of_slice_display = True, 
            blending="additive"
            )

### Labels edition

def neighbor_labels(img, lab, olab):
    """ Check if the two labels are neighbors or not """
    
    flab = find_boundaries(img==lab)
    folab = find_boundaries(img==olab)
    return np.sum(np.logical_and(flab, folab))>0

def where_to_modif(img, startlab, endlab):
    """ Merge two labels in one slice (2D)"""
    tmp = np.copy(img)
    initlab = tmp==startlab
    tmp[initlab] = endlab
    joinlab = (tmp==endlab)
    footprint = disk(radius=4)
    joinlab = binary_closing(joinlab, footprint)
    tomodif = ((tmp==0)*joinlab+initlab)
    return tomodif

def merge_labels(layer, frame, startlab, endlab, extend=10):
    """ Merge the two given labels """
    img = layer.data
    if frame is not None:
        img = layer.data[frame,]
    if not neighbor_labels(img, startlab, endlab):
        print("Labels not touching, I refuse to merge them")
        return
    
    if layer.ndim == 2:
        tomodif = where_to_modif(layer.data, startlab, endlab)
        layer.data[tomodif] = endlab
    else:
        for ind, islice in enumerate(layer.data):
            tomodif = where_to_modif(islice, startlab, endlab)
            layer.data[ind,][tomodif] = endlab
    layer.refresh()

def insideBoundingBox(pt, bbox, margin=0):
    """ Test if a point is inside a bounding box with a given extra margin"""
    if pt[0] < bbox[0]-margin:
        return False
    if pt[0] > bbox[2]+margin:
        return False
    if pt[1] < bbox[1]-margin:
        return False
    if pt[1] > bbox[3]+margin:
        return False
    return True

def cropBbox( img, bbox ):
    """ Crop the image following bounding box"""
    if len(img.shape) == 2:
        ## 2D
        return img[bbox[0]:(bbox[2]+1), bbox[1]:(bbox[3]+1)]
    if len(img.shape) == 3:
        #" 3D"
        if len(bbox) == 6:
            # 3D bbox
            return img[bbox[0]:(bbox[3]+1), bbox[1]:(bbox[4]+1), bbox[2]:(bbox[5]+1)]
        if len(bbox) == 4:
            # 2D bbox
            return img[:, bbox[0]:(bbox[2]+1), bbox[1]:(bbox[3]+1)]
    
def mergeBoundingBox( cell_bbox, cell_z, nuc_bbox ):
    """ Merge cell and nucleus bounding boxes """
    bbox = [0, 0, 0, 0, 0, 0]
    bbox[0] = min(cell_z, nuc_bbox[0])
    bbox[3] = max(cell_z+1, nuc_bbox[3])
    for i in range(2):
        bbox[1+i] = min(cell_bbox[i], nuc_bbox[1+i])
        bbox[3+1+i] = max(cell_bbox[2+i], nuc_bbox[3+1+i])
    return bbox

def get_boundary_cells( img, ndil=3 ):
    """ Return cells on tissu boundary in current image """ 
    dilated = binary_dilation( img > 0, disk(ndil) ) ## close small gaps, junctions
    zero = np.invert( dilated )
    zero = binary_dilation( zero, disk(ndil+2) )
    ## get pixels close to 0 and their cell value
    touching = np.unique( img[ zero ] ).tolist()
    if 0 in touching:
        touching.remove(0)
    return touching
    
def get_border_cells( img, margin=2 ):
    """ Return cells on border in current image """ 
    height = img.shape[1]
    width = img.shape[0]
    labels = list( np.unique( img[ :, 0:margin ] ) )   ## top border
    labels += list( np.unique( img[ :, (height-margin): ] ) )   ## bottom border
    labels += list( np.unique( img[ 0:margin,:] ) )   ## left border
    labels += list( np.unique( img[ (width-margin):,:] ) )   ## right border
    while 0 in labels:
        labels.remove(0)
    return labels