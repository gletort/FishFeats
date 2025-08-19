import os
import napari
from magicgui import magicgui, magic_factory
import fish_feats.MainImage as mi
import fish_feats.Configuration as cf
from napari.utils.translations import trans

def get_directory(title=""):
    try:
        from tkinter import Tk
        from tkFileDialog import askopenfilenames
    except:
        from tkinter import Tk
        from tkinter import filedialog

    Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
    filenames = filedialog.askdirectory(title=title) # show an "Open" dialog box and return the path to the selected file
    return filenames

def get_filename(mdir, title=""):
    try:
        from tkinter import Tk
        from tkFileDialog import askopenfilenames
    except:
        from tkinter import Tk
        from tkinter import filedialog

    Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
    filenames = filedialog.askopenfilenames(initialdir=mdir, title=title) # show an "Open" dialog box and return the path to the selected file
    return filenames[0]

def start():
    global viewer
    viewer = napari.current_viewer()
    viewer.title = "ZENnapari"
    thedirname = get_directory("Select folder to process")
    print(thedirname)

    configname = get_filename(mdir=thedirname, title="Select config file (.fishfeats)")
    cfg = cf.Configuration(configname, show=False)
    mig = mi.MainImage( talkative=True )
    listfiles = os.listdir(thedirname)
    
    dofiles = []
    for cfile in listfiles:
        if cfile.endswith(".tif") or cfile.endswith(".czi") or cfile.endswith(".ims"):
            dofiles.append(cfile)

    return check_files(dofiles, mig, cfg, thedirname)

def check_files(filelist, mig, cfg, mpath):
     
    @magicgui(call_button = "Go",
            select_files=dict(widget_type="Select", choices=filelist))
    def get_files( select_files ):
        for cfile in select_files:
            showOverlayText( "Doing file "+cfile, size=14 )
            fullfile = os.path.join(mpath, cfile)
            go_one_file( fullfile, mig, cfg)

    widg = viewer.window.add_dock_widget(get_files, name="Choose files")
    return widg

def go_one_file(fullfile, mig, cfg):
    mig.open_image(filename=fullfile)
    cfg.read_scale(mig)
    paras = cfg.param_junctions()
    roijunc = mig.prepare_segmentation_junctions()
    mig.do_segmentation_junctions( paras["Junc_method"], roijunc )
    filename = mig.junction_filename(dim=2, ifexist=False)
    mig.save_image( mig.junmask, filename, hasZ=False )
    print("Segmented file "+filename+" saved")

def showOverlayText( text, size=12 ):
    viewer.text_overlay.text = trans._(text)
    viewer.text_overlay.visible = True
    viewer.text_overlay.font_size = size
