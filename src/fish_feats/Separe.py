import numpy as np
import cv2
import scipy.ndimage as ndimage
from napari.utils.notifications import show_info
import time
import fish_feats.Utils as ut
from napari.utils import progress
from importlib import resources
import appose

def share_as_ndarray(img: np.ndarray) -> appose.NDArray:
    """Copies a NumPy array into a same-sized newly allocated block of shared memory."""
    shared = appose.NDArray(str(img.dtype), img.shape)
    shared.ndarray()[:] = img
    return shared

def sepanet( img, sepdir, patchsize=256 ):
    """ Separate junctions and nuclei with trained DL """
    print("sepaNet with models in "+str(sepdir))
    try:
        pixi_file = resources.files("fish_feats.resources").joinpath("pixi.toml")
        ut.show_info("Build/Load tensorflow environment")
        env = appose.pixi( pixi_file ).log_debug()
        env = env.subscribe_output( lambda line: print("OUT:", line, end="") )
        env = env.build()
        ut.show_info(f"Environment built at: {env.base()}")
        python = env.python().init("import numpy as np; import tensorflow as tf;")
        #python.debug(lambda msg: print("[DBG]", msg))
        progress_bar = ut.start_progress( None, total=1, descr="SepaNet separation" )
        
        def log_listener(event):
            """ Transfer appose task message to the main logger """
            if event.current and event.maximum:
                print( f"Separating slice {event.current}/{event.maximum}" )
                #ut.show_info( f"Separiting slice {event.current}/{event.maximum}" )
                #progress_bar.update( cur )
                #progress_bar.total = total 
            else:
                if event.message:
                    print( f"[task] {event.message} " )

        try:
            sepanet_script = resources.files("fish_feats.resources").joinpath("run_sepanet.py")
            sepanet_script = sepanet_script.read_text()
            result_junc = None
            result_nuc = None
            with share_as_ndarray(img) as image:
                task = python.task( sepanet_script )
                task.listen( log_listener )
                task.inputs["img"] = image 
                task.inputs["patchsize"] = patchsize
                task.inputs["model_directory"] = sepdir
                task.wait_for()
                result_junc = np.uint8( task.outputs["junctions"].ndarray().copy() )
                result_nuc = np.uint8( task.outputs["nuclei"].ndarray().copy() )
            return result_junc, result_nuc 
        except Exception as e:
            raise RuntimeError("Running SepaNet in separated environement failed") from e
        finally:
            python.close()
            ut.close_progress( None, progress_bar=progress_bar )
    except Exception as e:
        raise RuntimeError("SepaNet in separated environement failed") from e



### Separation based on filterings
def junctionsCoherence(img, medblur=3, quant=0.98, dsig=3, cornersig=5, ratio=0.5, niter=4):
    ## Coherence enhancing diffusion, Weickert et al.
    #from skimage import exposure
    height, width = img.shape[:2]
    qmax = np.quantile(img, quant)
    qmin = np.min(img)
    img = np.uint8( (img-qmax)/(qmax-qmin)*255 )
    #img = cv2.normalize(src=img, dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    img = cv2.medianBlur(img,medblur)
    #img = exposure.adjust_gamma(img, 0.7)

    for i in range(niter):
        ## get the features: eigen values
        cur = cv2.normalize(src=img, dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        eigenV = cv2.cornerEigenValsAndVecs(cur, cornersig, 3)  ## block size, eigen val and vec to edge/croner detection
        eigenV = eigenV.reshape(height, width, 3, 2)  # [[e1, e2], v1, v2]
        x1, y1 = eigenV[:,:,1,0], eigenV[:,:,1,1]

        ## derivatives
        gxx = cv2.Sobel(cur, cv2.CV_32F, 2, 0, ksize=dsig)
        gxy = cv2.Sobel(cur, cv2.CV_32F, 1, 1, ksize=dsig)
        gyy = cv2.Sobel(cur, cv2.CV_32F, 0, 2, ksize=dsig)
        gvv = x1*x1*gxx + 2*x1*y1*gxy + y1*y1*gyy
        m = gvv < 0
        
        ## combine results
        eroded = cv2.erode(img, None)
        dilated = cv2.dilate(img, None)
        imgt = eroded
        imgt[m] = dilated[m]
        img = (img*(1.0 - ratio) + imgt*ratio)
    return img

def anisoDiff(img, iterations=1):
    from medpy.filter.smoothing import anisotropic_diffusion
    return anisotropic_diffusion(img, niter=iterations)

def topHat(img, xyrad):
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (xyrad,xyrad))
    resimg = np.copy(img)
    i = 0
    for zimg in img:
        resimg[i] = cv2.morphologyEx(zimg, cv2.MORPH_TOPHAT, kernel)
        i = i + 1
    return resimg

def topHat2D(img, xyrad):
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (xyrad,xyrad))
    return cv2.morphologyEx(img, cv2.MORPH_TOPHAT, kernel)

def removeOutliers(img, rz=2, rxy=4, threshold=50):
    ## find outliers
    nimg = cv2.normalize(src=img, dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    med = ndimage.median_filter(nimg, size=(rz,rxy,rxy) )
    outliers = nimg>(med+threshold)
    ## replace outliers by neighboring median value
    imedian = ndimage.median_filter(img, size=(rz,rxy,rxy) )
    img[outliers] = imedian[outliers]
    return img

def removeOutliersIn2D(img, rxy=3, threshold=50):
    ## find outliers
    resimg = np.copy(img)
    for z in range(img.shape[0]):
        zimg = img[z,]
        nimg = cv2.normalize(src=zimg, dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        med = ndimage.median_filter(nimg, size=(rxy,rxy) )
        outliers = nimg>(med+threshold)
        ## replace outliers by neighboring median value
        imedian = ndimage.median_filter(zimg, size=(rxy,rxy) )
        resimg[z][outliers] = imedian[outliers]
    return resimg


def separateNucleiJunc(img, outrz=1, outrxy=6, threshold=40, edge=5, space=100, zhatrad=1, hatrad=4):
    show_info("Discriminating between nuclei and junction staining...")
    # remove background
    img = cv2.normalize(src=img, dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    img = removeOutliers(img, rz=outrz, rxy=outrxy, threshold=threshold)

    ## smooth - edge preserving
    imgjun = np.copy(img)
    for im in range(imgjun.shape[0]):
        imgjun[im,] = cv2.bilateralFilter(imgjun[im,], edge, space, space)

    # get junctions: small structures but not too small (dots)
    imgjun = ndimage.white_tophat(input=imgjun, size=(zhatrad,hatrad,hatrad))
    imgdots = ndimage.white_tophat(input=imgjun, size=(0,2,2))
    imgjun = imgjun-1.5*imgdots
    imgjun[imgjun<0] = 0

    # get nuclei   
    #imgmin = ndimage.minimum_filter(img, size=(2,25,25))
    #img = img - imgmin
    #img = ndimage.median_filter(img, size=(zhatrad*1,hatrad*1,hatrad*1) )
    #imgblurjunc = cv2.normalize(src=imgjun, dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    imgblurjunc = ndimage.uniform_filter(imgjun, size=(int(zhatrad*2),int(hatrad*1),int(hatrad*1)) )
    #imgsmall = ndimage.white_tophat(input=img, size=(zhatrad,int(hatrad*2),int(hatrad*2)) )
    img = img - imgblurjunc*8
    img[img<0]=0
    img = ndimage.uniform_filter(img, size=(zhatrad*1,hatrad*1,hatrad*1) )
    print("Done")
    return img, imgjun

def separateNucleiJuncV0(img, rz, rxy, zhatrad, hatrad):
    print("Discriminating between nuclei and junction staining...")
    # remove background
    imgmin = ndimage.minimum_filter(img, size=(2,30,30))
    img = img - imgmin
    img = removeOutliers(img, rz=rz, rxy=rxy, threshold=100)
    # smooth image
    #img = ndimage.uniform_filter(img, size=(rz,rxy,rxy) )
    img = ndimage.median_filter(img, size=(rz,rxy,rxy) )
    #img = anisoDiff(img, iterations=5)
    #img = ndimage.uniform_filter(img, size=(rz,rxy,rxy) )
    #img = ndimage.gaussian_filter(img, sigma=(0.5, 1, 1))
    # Top-hat filter to separate small and big structures
    ##kernel = ndimage.generate_binary_structure(rank=3, connectivity=3)
    #imgjun = ndimage.white_tophat(input=img, size=(int(zhatrad/2),int(hatrad/2),int(hatrad/2)))
    imgjun = ndimage.white_tophat(input=img, size=(zhatrad,hatrad,hatrad))
    imgsmall = ndimage.white_tophat(input=img, size=(zhatrad,int(hatrad*1.5),int(hatrad*1.5)) )
    #img = exposure.adjust_gamma(img, 0.9)
    imgsmall = ndimage.gaussian_filter(imgsmall, sigma=(0.7, 1.2, 1.2))
    img = img - imgsmall*1.4
    img[img<0]=0
    imgjun = ndimage.gaussian_filter(imgjun, sigma=(0.7, 1.2, 1.2))
    #img = ndimage.gaussian_filter(img, sigma=(0.5, 1.5, 1.5))
    print("Done")
    return img, imgjun

def smoothNuclei(img, radxy, radz):
    return ndimage.uniform_filter(img, size=(radz,radxy,radxy) )


