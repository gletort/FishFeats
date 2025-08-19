import numpy as np
import os
import fish_feats.MainImage as mi
import napari

def starting():
    """ test initialization of the napari plugin """
    viewer = napari.Viewer( show=False )
    from fish_feats.Naparing import init_viewer
    init_viewer(viewer)


mig = mi.MainImage(talkative=True)
    
def test_load_image():
    test_img = "./_tests/files/imaris0.ims"
    mig.open_image(test_img)
    assert mig.image is not None
    assert mig.nbchannels == 4 
    assert mig.free_channel() == 1
    assert mig.build_filename("_end.tif") == os.path.join( ".", "_tests", "files", "results", "imaris0_end.tif" )

def read_config():
    """ read the configuration file """
    import fish_feats.Configuration as cf
    cfg = cf.Configuration( mig.save_filename(), show=False )
    ## check that scale was read from the file metatdata
    assert mig.scaleZ == 0.19
    if cfg.has_config():
        cfg.read_scale( mig )
        assert mig.zdirection == -1 
        ## check taht the scale was read from the config file
        assert mig.scaleXY == 0.166
        assert mig.scaleZ == 0.2

        #" Cehck reading a parameter set from the config file"
        paras = cfg.read_parameter_set("JunctionSeg")
        assert paras is not None
        assert "method" in paras


def test_junctions_separation():
    assert mig.should_separate() == True
    mig.separate_junctions_nuclei()
    assert mig.nucstain is not None
    assert mig.should_separate() == False

def test_load_segfile():
    """ test loading from the segmentation file """
    assert mig.hasCells() == False
    segfile = os.path.join( ".", "_tests", "files", "results", "imaris0_cells2D.tif" )
    mig.load_segmentation( segfile )
    mig.popFromJunctions()
    assert mig.hasCells() == True
    assert mig.nbCells() == 58

def test_load_nucleifile():
    """ Test loading nuclei segmentation """
    nucfile = os.path.join( ".", "_tests", "files", "results", "imaris0_nuclei.tif" )
    mig.load_segmentation_nuclei(nucfile)
    assert mig.nucstain is not None
    assert mig.pop.imgnuc is not None

def test_nuclei_filter():
    mig.popNucleiFromMask(associate=False)
    assert mig.hasNuclei() == True 
    assert mig.nbNuclei() == 48
    mig.pop.relabelNuclei()
    assert mig.nbNuclei() == 48
    mig.filterNuclei( 100 )
    assert mig.nbNuclei() == 39

def test_load_rnafile():
    rnafile = os.path.join( ".", "_tests", "files", "results", "imaris0_RNA1.csv" )
    mig.load_rnafile( rnafile, 1 )
    assert mig.rnas[1].nspots() >= 1200

def test_association():
    mig.go_association( distance = 10 )
    assert len(mig.pop.association.keys()) == 20

def test_rna_segmentation():
    mig.find_rna( 2, 1000, 250, True, None )
    assert mig.rnas[2].nspots() >= 1000
    assert mig.rnas[2].nspots() <= 2500
    assert mig.get_rna_threshold(2) >= 3.5 
    assert mig.get_rna_threshold(2) <= 4.5 

def test_rna_assignement():
    mig.assign_rna(2, "Projection", 10, 0)
    assert len(np.unique(mig.rnas[2].labels)) >= 40

if __name__ == "__main__":
    starting()
    test_load_image()
    read_config()
    test_junctions_separation()
    test_load_nucleifile()
    test_load_segfile()
    test_nuclei_filter()
    test_association()
    test_rna_segmentation()
    test_rna_assignement()
    test_load_rnafile()
    print("Everything passed")
