import numpy as np
import cv2
import os
import random
import scipy.ndimage as ndimage
from skimage.measure import regionprops, label
from napari.utils.notifications import show_info
import fish_feats.Utils as ut
from fish_feats.Association import associateNucleus, associateNucleusOverlap
from skimage.filters import sato
from skimage.morphology import skeletonize, binary_closing
from skimage.segmentation import find_boundaries
from skimage.segmentation import clear_border
from skimage.measure import label
from skimage.exposure import adjust_gamma
import time
import tempfile

"""
    Functions to segment junctions or nuclei
"""

def run_epyseg(input_folder):
    import tensorflow as tf

    # libraries loaded checking epyseg to see if everything is functional
    try:
        from epyseg.img import Img
        from epyseg.deeplearning.deepl import EZDeepLearning
        from epyseg.deeplearning.augmentation.meta import MetaAugmenter
        from epyseg.deeplearning.augmentation.generators.data import DataGenerator
        deepTA = EZDeepLearning()
    except:
        print('EPySeg failed to load.')
    
    # Load a pre-trained model
    pretrained_model_name = 'Linknet-vgg16-sigmoid-v2'
    pretrained_model_parameters = deepTA.pretrained_models[pretrained_model_name]

    deepTA.load_or_build(model=None, model_weights=None,
                             architecture=pretrained_model_parameters['architecture'], backbone=pretrained_model_parameters['backbone'],
                             activation=pretrained_model_parameters['activation'], classes=pretrained_model_parameters['classes'],
                             input_width=pretrained_model_parameters['input_width'], input_height=pretrained_model_parameters['input_height'],
                             input_channels=pretrained_model_parameters['input_channels'],pretraining=pretrained_model_name)
    #epydir = os.path.join(os.path.abspath(".."), "epyseg_net")
    #deepTA.load_weights( os.path.join(epydir,'Linknet-vgg16-sigmoid-v2.h5') )

    input_val_width = 256
    input_val_height = 256
    
    input_shape = deepTA.get_inputs_shape()
    output_shape = deepTA.get_outputs_shape()
    if input_shape[0][-2] is not None:
        input_val_width=input_shape[0][-2]
    if input_shape[0][-3] is not None:
        input_val_height=input_shape[0][-3]
    #print(input_shape)
    deepTA.compile(optimizer='adam', loss='bce_jaccard_loss', metrics=['iou_score'])
      
    range_input = [0,1]
    input_normalization = {'method': 'Rescaling (min-max normalization)',
                        'individual_channels': True, 'range': range_input, 'clip': True} 

    predict_generator = deepTA.get_predict_generator(
            inputs=[input_folder], input_shape=input_shape,
            output_shape=output_shape, 
            default_input_tile_width=input_val_width, 
            default_input_tile_height=input_val_height,
            tile_width_overlap=32,
            tile_height_overlap=32, 
            input_normalization=input_normalization, 
            clip_by_frequency={'lower_cutoff': None, 'upper_cutoff': None, 'channel_mode': True} )

    post_process_parameters={}
    post_process_parameters['filter'] = None
    post_process_parameters['correction_factor'] = 1
    post_process_parameters['restore_safe_cells'] = False ## no eff
    post_process_parameters['cutoff_cell_fusion'] = None
    post_proc_method = 'Rescaling (min-max normalization)'
    post_process_parameters['post_process_algorithm'] = post_proc_method
    post_process_parameters['threshold'] = None  # None means autothrehsold # maybe add more options some day

    predict_output_folder = os.path.join(input_folder, 'predict')
    print("Starting segmentation with EpySeg.....")
    deepTA.predict(predict_generator, 
                output_shape, 
                predict_output_folder=predict_output_folder,
                batch_size=1, **post_process_parameters)
    
    deepTA.clear_mem()
    if not os.access(predict_output_folder, os.W_OK):
        os.chmod(predict_output_folder, stat.S_IWUSR)
    #deepTA = None
    del deepTA

def run_epyseg_onimage(img, filedir, filename, verbose=True):
    from PIL import Image
    import os

    binimg = None
    tmpdir_path = None
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            print("tmp dir "+str(tmpdir))

            ### empty directory if exists
            inputname = filename+"_junctions.tif"
            with Image.fromarray(img) as im:
                im.save(os.path.join(tmpdir,inputname))
            try:
                predict_output_folder = os.path.join(tmpdir, 'predict')
                os.makedirs(predict_output_folder, exist_ok=True)
            except:
                print("Warning, issue in creating "+predict_output_folder+" folder")
    
            ## run Epyseg on tmp directory (contains current image)
            run_epyseg(tmpdir)
    
            ## return result and delete files
            im = Image.open(os.path.join(tmpdir,"predict",inputname)) 
            binimg = np.copy(im)
            os.chmod(os.path.join(tmpdir, "predict", inputname), 0o777)
            im.close()
            os.remove( os.path.join(tmpdir, "predict", inputname) )
    except BaseException as e:
        print("Error in running EpySeg: "+str(e))
        print("Warning, folder not deleted")
        tmpdir_path = tmpdir
        pass

    return junctions_to_label(binimg), tmpdir_path

def run_epyseg_onimage_fold(img, filedir, filename, verbose=True):
    from PIL import Image
    import os
    import shutil
    import stat
    
     ## prepare data
    tmpdir = os.path.join(filedir,"TmpEpySegDir_"+str(random.randint(0,5000)))

    ### empty directory if exists
    if os.path.exists(tmpdir):
        os.chmod(tmpdir, stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH|stat.S_IWUSR|stat.S_IWGRP|stat.S_IWOTH|stat.S_IXUSR)
        shutil.rmtree(tmpdir, ignore_errors=True)
    os.mkdir(tmpdir)
    inputname = filename+"_junctions.tif"
    im = Image.fromarray(img)
    im.save(os.path.join(tmpdir,inputname))
    try:
        predict_output_folder = os.path.join(tmpdir, 'predict')
        os.makedirs(predict_output_folder, exist_ok=True)
    except:
        print("Warning, issue in creating "+predict_output_folder+" folder")
    
    ## run Epyseg on tmp directory (contains current image)
    run_epyseg(tmpdir)
    
    ## return result and delete files
    im = Image.open(os.path.join(tmpdir,"predict",inputname))
    try:
        os.chmod(predict_output_folder, stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH|stat.S_IWUSR|stat.S_IWGRP|stat.S_IWOTH|stat.S_IXUSR)
        shutil.rmtree(predict_output_folder, ignore_errors=True)
        os.chmod(tmpdir, stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH|stat.S_IWUSR|stat.S_IWGRP|stat.S_IWOTH|stat.S_IXUSR)
        shutil.rmtree(tmpdir, ignore_errors=True)
    except:
        print("Folder "+tmpdir+" not deleted, you can delete it manually")

    return junctions_to_label(im)

def junctions_to_label(img):
    """ convert junctions result to labels map """
    return( label(np.invert(img), background=0, connectivity=1) )

def run_cellpose(img, scaleXY, diameter=7, verbose=True):
    from cellpose import models
    model = models.CellposeModel(gpu=True, model_type='cyto3') 
    diamet = diameter/scaleXY   ## increase it ?
    mask, flow, style = model.eval(img, invert=False, diameter=diamet, channels=[0,0], do_3D=False, cellprob_threshold=0.05)
    ## convert cellpose result to label image (cellpose result are not touching border, make it as junctions)
    return fromcellpose_tojunctions(mask)

def fromcellpose_tojunctions(mask):
    bined = binary_closing( find_boundaries(mask), footprint=np.ones((10,10)) )
    return junctions_to_label( skeletonize( bined ) )

def segmentJunctions(img, mode, scaleXY, imagedir, imagename, diameter=7, chunking=1000, verbose=True):
    """ segment junctions from ZO1 signal, either with EpySeg or CellPose """
    if (mode == 0) or (isinstance(mode, str) and mode.lower() == "epyseg"):
        show_info("Starting segmentation with Epyseg...")
        seged, tmpdir_path = run_epyseg_onimage(img, imagedir, imagename, verbose)
        if tmpdir_path is not None:
            if os.path.exists(tmpdir_path):
                os.chmod(tmpdir_path, stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH|stat.S_IWUSR|stat.S_IWGRP|stat.S_IWOTH|stat.S_IXUSR)
                shutil.rmtree(tmpdir_path, ignore_errors=True)
    if (isinstance(mode, str) and mode.lower() == "cellpose"):
        show_info("Starting segmentation with CellPose...")
        seged = run_cellpose(img, scaleXY, diameter=diameter, verbose=verbose)
    if (isinstance(mode, str) and mode.lower() == "epyseg-dask"):
        from fish_feats.DaskedEpyseg import run_dasked_epyseg
        show_info("Starting segmentation with dasked Epyseg...")
        overlap = diameter/scaleXY*0.25
        tmp_dir = tempfile.TemporaryDirectory()
        tmp_file = os.path.join( tmp_dir.name, "tmp.zarr" ),
        dask_seg = run_dasked_epyseg( img, imagedir, imagename, overlap=overlap, iou_depth=2, iou_threshold=0.1, chunksize=(chunking, chunking), tmpfile=tmp_file )
        seged = dask_seg.compute()
    return clear_border(seged)

def prepJunctions( img, do_clahe=True, clahe_grid=10 ):
    img = cv2.normalize(src=img, dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    if do_clahe:
        clahe = cv2.createCLAHE( clipLimit=2.0, tileGridSize=(clahe_grid, clahe_grid) )
        img = clahe.apply(img)
    return img

def prepJunctions_sharp(img, medBlur, sharp):
    #from skimage import restoration
    junc = np.max(img, axis=0)
    junc = cv2.normalize(src=junc, dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    junc = cv2.medianBlur(junc,medBlur)
    #rad = 2.0/scaleXY
    #juncbg = restoration.rolling_ball(junc, radius=rad)
    #res = junc-juncbg
    res = junc
    #res[res<0] = 0
    #res = cv2.normalize(src=res, dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    #b1 = cv2.GaussianBlur(res, (0,0), 20,20,0)
    #b2 = cv2.GaussianBlur(res, (0,0), 1,1,0)
    #res = b1-b2
    #res[res<0] = 0
    #res = cv2.fastNlMeansDenoising(res,None, 7, 21, 7)
    #res = cv2.bilateralFilter(res, 9, 31,31)
    sharpen_kernel = np.array( [[-1,-1,-1],[-1,sharp,-1],[-1,-1,-1]])
    res = cv2.filter2D(res, -1, sharpen_kernel)
    #res = cv2.normalize(src=res, dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    return res

def fill_posmax(array, meanimg, meanmax):
    for z in range(meanimg.shape[0]):
        array += z * (meanimg[z,]==meanmax) * (array==0)
    return array

def uniform_filtering( array, smooth ):
    return ndimage.uniform_filter( array, size=(smooth, smooth) )

def maximum_filtering( array, sizexy ):
    filted = ndimage.maximum_filter(array, size=(1, sizexy, sizexy))
    return filted

def local_max_proj_parallel(img, largexy=40, smooth=2):
    """ Apply local max in parallel """
    from skimage.util import apply_parallel
    meanimg = ndimage.maximum_filter(img, size=(1, largexy, largexy))
    meanmax = np.max(meanimg, axis=0)
    posmax = np.zeros(meanimg.shape[1:3])
    for z in range(meanimg.shape[0]):
        posmax += z * (meanimg[z,]==meanmax) * (posmax==0)
    
    posmax = apply_parallel( uniform_filtering, posmax, depth=10, extra_arguments=(int(largexy*1.5),), compute=True )
    
    projimg = np.zeros(posmax.shape)
    for z in range(img.shape[0]):
        projimg += img[z,] / (1+np.abs(posmax-z)) * (np.abs(posmax-z)<=3)/7

    return apply_parallel( uniform_filtering, projimg, depth=10, extra_arguments=(smooth,), compute=True )

def local_max_proj(img, largexy=40, smooth=2):
    """ Do local max projection of junctions """

    ## get position of local maxima
    meanimg = ndimage.maximum_filter(img, size=(1, largexy, largexy))
    posmax = np.argmax(meanimg, axis=0)
    posmax = ndimage.uniform_filter(posmax, size=(int(largexy*1.5), int(largexy*1.5)))
    
    ## project the intensity values around the local max
    projimg = np.zeros(posmax.shape)
    nz = 2
    for dz in range(-nz, nz):
        curpos = np.uint8(posmax+dz)
        curpos[curpos<0] = 0
        curpos[curpos >= img.shape[0]] = img.shape[0]-1
        projimg += np.take_along_axis(img, curpos[np.newaxis], axis=0)[0]/(1+abs(dz)) * 0.1

    #for z, zimg in enumerate(img):
    #    dist2max = np.abs(posmax-z)
    #    within = (dist2max <= 3)
    #    if np.sum(within) > 0:
    #        projimg += zimg / (1+dist2max) * (within)/7

    projimg = ndimage.uniform_filter(projimg, size=(smooth, smooth))
    return projimg


def image_tubeness(img):
    img = sato(img, sigmas=range(1, 10, 2), black_ridges=False, mode='reflect', cval=0)
    return ndimage.uniform_filter(img, size=(10,10)) 


def normalizeQuantile(img, qmin=0.001, qmax=0.99, vmax=255):
    quants = np.quantile(img, [qmin, qmax])
    img = (img-quants[0])/(quants[1]-quants[0])*vmax
    img = np.clip(img, 0, quants[1])
    return img

def gaussBlur(im, rad):
    return cv2.GaussianBlur(im, (0,0), rad, rad, 0)


def preprocessNucleiMedianFilter(img, radxy, radz):
    return ndimage.median_filter(img, size=(radz, radxy, radxy) )

def preprocessRemoveBg(img, radxy, radz):
    bg = ndimage.uniform_filter(img, size=(radz, radxy, radxy) )
    img = img - bg
    img[img<0] = 0
    return img

def preprocessRemoveBg2D(img, radxy):
    bg = ndimage.uniform_filter(img, size=(radxy, radxy) )
    img = np.float32(img)
    img = img - bg
    img[img<0] = 0
    img = np.uint8(img)
    return img

def prepNuclei(img):
    """ Normalize by quantiles """
    #img[img<0] = 0
    img = adjust_gamma(img, 1.05)
    quants  = np.quantile(img, [0.001, 0.99])
    img = np.clip(img, quants[0], quants[1])
    img = (img-quants[0])/(quants[1]-quants[0])
    return img

def stardist2D(img, prob, over):
    """ run stardist model, segment nuclei in 2D """
    try:
        from csbdeep.utils import Path, normalize
        from stardist.models import StarDist2D
    except ModuleNotFoundError:
        ut.show_error("Stardist2D not installed, please install stardist with pip install stardist")
        return None
    
    model = StarDist2D.from_pretrained('2D_paper_dsb2018')  ## 2D_versatile_fluo, find more nuclei than paper_dsb2018
    axis_norm = None ## normalize jointly
    labs = []
    tiling = (int(img.shape[1]/2000)+1, int(img.shape[2]/2000)+1)
    nuclei = np.zeros(img.shape, "uint16")
    for ind, im in enumerate(img):
        #if np.mean(im)<0.1:    ## nearly empty slice, makes it bug
        #    labels = np.zeros(im.shape)
        #else:
        #    im = normalize(im, 1, 99.8, axis=axis_norm)
        labels, details = model.predict_instances(im, n_tiles=tiling, prob_thresh=prob, nms_thresh=over, show_tile_progress=True)
        nuclei[ind,] = labels
    return nuclei

def getNuclei_stardist2DAsso3D(nucimg, scaleXY, proba=0.55, overlap=0.1, assoMode="Munkres", assolim=3, threshold_overlap=0.25, verbose=True):
    """ Segment nuclei with Stardist2D and reconstruct in 3D - return the nuclei list """
    
    ## segment 2D
    labnuc = stardist2D(nucimg, prob=proba, over=overlap)
    if labnuc is None:
        return None
    ## reconstruct 3D
    if assoMode == "Munkres":
        labels = associateNucleus(labnuc, dlimit=assolim, scaleXY=scaleXY)  ## distance 2D in micrcons  -2.5
    if assoMode == "Overlap":
        labels = associateNucleusOverlap(labnuc, threshold_overlap=threshold_overlap)
    return finishNuclei(labels, 2, False, verbose)


def finishNuclei( nuclab, minz=2, convexify=False, verbose=True ):
    start_time = time.time()
    regions = regionprops( nuclab )
    for r in regions:
        ## in less than minz slices, too small, remove
        if (r.bbox[3]-r.bbox[0]) < minz:
            nuclab[nuclab==r.label] = 0
        else:
            if convexify:
                nuclab[r.bbox[0]:r.bbox[3], r.bbox[1]:r.bbox[4], r.bbox[2]:r.bbox[5]][r.image_convex] = r.label

    if verbose:
        print("Nb nuclei found: "+str(len(np.unique(nuclab))))
        print("Post-processing nuclei took {:.3f}".format((time.time()-start_time)/60)+" min")
    return nuclab
    

def initialize_cellpose():
    from cellpose import models 
    model = models.CellposeModel(gpu=True, model_type='nuclei') 
    return model

def run_cellpose_nuclei(model, nucimg, norm, diameter, scaleXY, scaleZ, threshold, flow_threshold, resample=True, in3D=True, stitch_threshold=0.25, verbose=True):
    diamet = diameter/scaleXY
    if verbose:
        print("Starting 3D nuclei segmentation with CellPose3D...")
    if in3D:
        anisotropy = scaleZ/scaleXY
    else:
        anisotropy = 1.0
    mask, flow, style = model.eval(nucimg, invert=False, normalize=norm, diameter=diamet, channels=[0,0], channel_axis=0, z_axis=1, resample=resample, do_3D=in3D, stitch_threshold=stitch_threshold, anisotropy=anisotropy, flow_threshold=flow_threshold, cellprob_threshold=threshold)
    if verbose:
        print("3D nuclei segmentation done")
    return mask

def run_cellpose_nuclei_dask( model, nucimg, norm, diameter, scaleXY, scaleZ, threshold, flow_threshold, resample=True, in3D=True, stitch_threshold=0.25, chunk=1000, verbose=True ):
    from fish_feats.cellpose_dask import dask_segment
    diamet = diameter/scaleXY
    if verbose:
        print("Starting 3D nuclei segmentation with CellPose3D...")
    if in3D:
        anisotropy = scaleZ/scaleXY
    else:
        anisotropy = 1.0
    
    tmp_dir = tempfile.TemporaryDirectory()
    nucimg = np.moveaxis( nucimg, 0, 3 )
    dasky = dask_segment(
        nucimg, channels=[0,0], 
        diameter = [diamet, diamet], fast_mode=True,
        use_anisotropy=in3D, iou_depth = 10, 
        iou_threshold=0.4,
        chunksize=(chunk, chunk, chunk, 1),
        dim = 4,
        do_3D=in3D,
        stitch_threshold = stitch_threshold,
        resample = resample,
        cellprob_threshold = threshold,
        flow_threshold = flow_threshold,
        model = model,
        z_axis=0,
        tmp_file = os.path.join( tmp_dir.name, "tmp.zarr" ),
    )
    print(dasky)

    mask = dasky.compute()
    print("done")
    if verbose:
        print("3D nuclei segmentation done")
    return mask


def getNuclei_cellpose3D(model, nucimg, diameter, scaleXY, scaleZ, threshold=0.1, flow_threshold=0.4, resample=True, in3D=True, stitch_threshold=0.25, dask=False, chunk=1000, verbose=True):
    ## pretreat
    if not dask:
        mask = run_cellpose_nuclei(model, nucimg, False, diameter, scaleXY, scaleZ, threshold, flow_threshold, resample, in3D, stitch_threshold, verbose)
    else:
        mask = run_cellpose_nuclei_dask(model, nucimg, False, diameter, scaleXY, scaleZ, threshold, flow_threshold, resample, in3D, stitch_threshold, chunk=chunk, verbose=verbose)
    return finishNuclei( mask, 2, convexify=True, verbose=verbose )

def prepElectroporation(img, radxy, radz):
    from skimage import exposure
    img = exposure.adjust_gamma(img, 0.9)
    imin = np.quantile(img, 0.001)
    imax = np.quantile(img, 0.999)
    img = (img-imin)/(imax-imin)*255
    img[img<0] = 0
    img = np.uint8(img)
    img = ndimage.median_filter(img, size=(radxy, radxy, radz) )
    #img = ndimage.gaussian_filter(img, (radxy,radxy,radz) )
    return img

def getElectroporated(img):
    bins = []
    msig = np.mean(img)*0.95#+0.5*np.std(img)  ## signal is sparse, so mean is low
    #print(str(np.mean(img))+" "+str(np.std(img)))
    for im in img:
        #print(np.mean(im))
        if np.mean(im) > msig:   ## contains some signal
            th, bim = cv2.threshold(im, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        else:
            bim = np.zeros(im.shape)
        bins.append(bim)
    bins = np.array(bins)
    s = ndimage.generate_binary_structure(3,3)
    labels, num = ndimage.label(bins, structure=s)
    vols = ndimage.sum(bins, labels, range(num))
    centers = ndimage.center_of_mass(bins, labels, range(num))
    return labels, vols, centers
