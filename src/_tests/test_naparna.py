import numpy as np
import napari
from fish_feats.NapaRNA import PointEditing
import fish_feats.MainImage as mi
from fish_feats.Naparing import FishFeats
import fish_feats.Configuration as cf
import fish_feats.Utils as ut


class DummyContourLayer:
    def get_color(self, value):
        if value == 3:
            return "green"
        return "white"

def test_assign_selected2cell():
    ## initialize all project
    viewer = napari.Viewer(show=False)
    ffeats = FishFeats(viewer)
    test_img = "./src/_tests/files/imaris0_crop.tif"
    ffeats.mig = mi.MainImage()
    mig = ffeats.mig
    mig.open_image(test_img)
    ffeats.cfg = cf.Configuration(ffeats.mig.save_filename(), show=False)
    assert not mig.hasCells()
    ffeats.load_all_previous_files()
    ffeats.spot_disp_size = 2

    nchan = 1 
    #ut.removeOverlayText(self.viewer)
    spots, labs, scores = mig.get_spots(nchan)
    points = np.array(spots)
    labels = np.array(labs, dtype="int")
    scores = np.array(scores, dtype="float")
    unassigned = (labels==-1) + (labels==1)
    labels[unassigned] = 1
    point_properties = { 'label': labels, 'score':scores, 'unassigned': unassigned, 'intensity': np.array([0.0]*len(labs)) }
    ut.add_point_layer( viewer, points, "white", layer_name="assignedRNA"+str(nchan), mig=mig, size=3, pts_properties=point_properties ) 

    editor = PointEditing(1, viewer, mig, ffeats.cfg, ffeats)
    editor.layerrna.selected_data = {3}
    assert editor.layerrna.properties['label'][3] == 1
    editor.assign_selected2cell()
    assert editor.layerrna.properties['label'][3] == 2
    assert editor.layerrna.properties['score'][3] == 2


if __name__ == "__main__":
    test_assign_selected2cell()
