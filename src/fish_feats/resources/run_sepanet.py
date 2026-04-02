import numpy as np
import logging
from math import floor
import tensorflow as tf
import keras
import scipy.ndimage as ndimage

appose_mode = 'task' in globals()

if not appose_mode:
    print("not implemented")
    exit

class ApposeLogHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        task.update( message=msg )

def setup_logger( name="" ):
    logger = logging.getLogger(name)
    handler = ApposeLogHandler()
    formatter = logging.Formatter('[FishFeats-SepaNet]-%(message)s')
    handler.setFormatter( formatter )
    logger.addHandler(handler)
    logger.setLevel( 20 )
    return logger

logger = setup_logger()    
logger.info("Starting separation")

def run_on_image(imgtest, model, patchsize, step=50):
    imgtest = np.array( imgtest.ndarray(), dtype="float" )
    #imgtest.astype(float)
    imgtest = normalise(imgtest)
    imgtest = smooth(imgtest)

    ## handle case of very small image, smaller than the patchsize
    smallimg = None
    if (imgtest.shape[1] < patchsize) or (imgtest.shape[2] < patchsize):
        smallimg = np.copy(imgtest)
        imgtest = np.zeros((imgtest.shape[0], patchsize, patchsize)) 
        imgtest[:,:smallimg.shape[1], :smallimg.shape[2] ] = smallimg

    ## split in patches
    imshape = imgtest.shape
    shapey = imshape[1]
    shapex = imshape[2]
    resimg = np.zeros(imshape+(2,), dtype="float")

    #for z, zimg in enumerate(imgtest):
    for z in (range(imgtest.shape[0])):
        task.update( current=z, maximum = imgtest.shape[0], message="Separating staining" )
        zimg = imgtest[z]
        patchs = []
        nimg = np.zeros(imshape[1:3]+(2,), dtype="uint8")
        inds = []
        for y in range(floor(shapey/step)):
            ey = min(y*step+patchsize, shapey)
            sy = ey - patchsize
            for x in range(floor(shapex/step)):
                ex = x*step+patchsize
                ex = min(ex, shapex)
                sx = ex - patchsize
                patch = zimg[sy:ey, sx:ex]
                nimg[sy:ey, sx:ex,0] = nimg[sy:ey, sx:ex,0] + 1
                nimg[sy:ey, sx:ex,1] = nimg[sy:ey, sx:ex,1] + 1
                patchs.append(patch)
                inds.append((sy, ey, sx, ex))
        patchs = np.array(patchs)
        res = model.predict(patchs)
        for ind, (sy, ey, sx, ex) in enumerate(inds):
            resimg[z,sy:ey, sx:ex,:] += res[ind]/nimg[sy:ey,sx:ex]

    ## get back the original image if it was too small
    if smallimg is not None:
        resimg = resimg[:, :smallimg.shape[1], :smallimg.shape[2]]
    resimg = np.uint8(resimg*255)
    return resimg

def normalise(img):
    quants = np.quantile(img, [0.1, 0.99])
    img = (img - quants[0]) / (quants[1]-quants[0])
    img = np.clip(img, 0, 1)
    return img

def smooth(img):
    for z in range(img.shape[0]):
        img[z,] = ndimage.gaussian_filter(img[z,], 1)
    return img

def both_MSE( y_true, y_pred ):
    acc0 = keras.metrics.mean_squared_error(y_true[:,:,:,0], y_pred[:,:,:,0])
    acc1 = keras.metrics.mean_squared_error(y_true[:,:,:,1], y_pred[:,:,:,1])
    return acc0 + acc1

def both_MSE_percent_0( y_true, y_pred ):
    acc0 = keras.metrics.mean_absolute_percentage_error(y_true[:,:,:,0], y_pred[:,:,:,0])
    return acc0
def both_MSE_percent_1( y_true, y_pred ):
    acc0 = keras.metrics.mean_absolute_percentage_error(y_true[:,:,:,1], y_pred[:,:,:,1])
    return acc0


def mse_two(y_true, y_pred):
    y_true = tf.reshape(y_true, [-1])
    y_pred = tf.reshape(y_pred, [-1])
    mse = tf.keras.losses.MeanSquaredError()
    return mse(y_true, y_pred)

def share_as_ndarray(img):
    """Copies a NumPy array into a same-sized newly allocated block of shared memory"""
    from appose import NDArray
    shared = NDArray(str(img.dtype), img.shape)
    shared.ndarray()[:] = img
    return shared

""" Separate junctions and nuclei with trained DL """
print( "SepaNet with models in "+str(model_directory) )

# to allocate more gpus, try
logger.info( "Tensorflow with cuda: "+str(tf.test.is_built_with_cuda()) )
logger.info( "Tensorflow version: "+str(tf.__version__) )
logger.info( "Num GPUs Available: " + str(len(tf.config.list_physical_devices('GPU')) ) )

# load model
model = tf.keras.models.load_model(model_directory, custom_objects={"mse_two":mse_two, "both_MSE":both_MSE, "both_MSE_percent_0":both_MSE_percent_0, "both_MSE_percent_1":both_MSE_percent_1})
res = run_on_image( img, model, patchsize, step=50 )
    
if res is not None:
    ## Write the results on the shared memory object
    task.outputs["junctions"] = share_as_ndarray( res[:,:,:,0] )
    task.outputs["nuclei"] = share_as_ndarray( res[:,:,:,1] )
logger.info( "Separation finished" )