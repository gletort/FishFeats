import logging
import numpy as np
appose_mode = 'task' in globals()

if not appose_mode:
    print("not implemented")
    exit
try:
    #from csbdeep.utils import Path, normalize
    from stardist.models import StarDist2D
except ModuleNotFoundError as e:
    print("ERR: Problem with Stardist2D installation")
    raise e 

class ApposeLogHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        task.update( message=msg )

def setup_logger( name="" ):
    logger = logging.getLogger(name)
    handler = ApposeLogHandler()
    formatter = logging.Formatter('[FishFeats-Stardist]-%(message)s')
    handler.setFormatter( formatter )
    logger.addHandler(handler)
    logger.setLevel( 20 )
    return logger

logger = setup_logger()    
logger.info("Starting segmentation")

image = img.ndarray()
logger.info("Starting")
    
model = StarDist2D.from_pretrained('2D_paper_dsb2018')  ## 2D_versatile_fluo, find more nuclei than paper_dsb2018
tiling = (int(image.shape[1]/2000)+1, int(image.shape[2]/2000)+1)
nuclei = np.zeros(image.shape, "uint16")
for ind, im in enumerate(image):
    task.update( current=ind, maximum=len(image), message="Stardist segmentation..." )
    labels, details = model.predict_instances(im, n_tiles=tiling, prob_thresh=stardist_probability, nms_thresh=stardist_overlap, show_tile_progress=False)
    nuclei[ind,] = labels
if nuclei is not None:
    ## Write the results on the shared memory object
    img.ndarray()[:] = nuclei 
logger.info( "Segmentation finished" )