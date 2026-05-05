import logging
import numpy as np
appose_mode = 'task' in globals()

if not appose_mode:
    print("not implemented")
    exit
try:
    from cellpose import models
except ModuleNotFoundError as e:
    print("ERR: Problem with Cellpose3 installation")
    raise e 

class ApposeLogHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        task.update( message=msg )

def setup_logger( name="" ):
    logger = logging.getLogger(name)
    handler = ApposeLogHandler()
    formatter = logging.Formatter('[FishFeats-Cellpose3]-%(message)s')
    handler.setFormatter( formatter )
    logger.addHandler(handler)
    logger.setLevel( 20 )
    return logger

logger = setup_logger()    
logger.info("Starting segmentation")

image = np.array( img.ndarray() )
logger.info("Starting")
    
model = models.CellposeModel( gpu=True, model_type='cyto3' ) 
diamet = cell_diameter/scale_xy  
mask, flow, style = model.eval(image, invert=False, diameter=diamet, channels=[0,0], do_3D=False, cellprob_threshold=0.05)

if mask is not None:
    ## Write the results on the shared memory object
    img.ndarray()[:] = mask 
logger.info( "Segmentation finished" )