"""
Segments detected regions in a chunked dask array.

Uses overlapping chunks during segmentation, and determines how to link segments
between neighboring chunks by examining the overlapping border regions.

Heavily based on dask_image.ndmeasure.label, which uses non-overlapping blocks
with a structuring element that links segments at the chunk boundaries.

Adapted from: https://github.com/MouseLand/cellpose/blob/main/cellpose/contrib/distributed_segmentation.py
"""
import functools
import operator

import dask
import dask.array as da
import numpy as np
from dask_image.ndmeasure._utils import _label
from sklearn import metrics as sk_metrics
import os, shutil



def run_dasked_epyseg(
    image,
    imagedir, 
    imagename,
    tmpfile,
    overlap=200,
    iou_depth=1,
    iou_threshold=0.05,
    chunksize = (1000,1000),  
):
    """Use epyseg with dask to segment junctions 

    Parameters
    ----------
    image : array of shape (z, y, x, channel)
    iou_depth: dask depth parameter
        Number of pixels of overlap to use in intersection-over-union calculation when
        linking segments across neighboring, overlapping dask chunk regions.
    iou_threshold: float
        Minimum intersection-over-union in neighboring, overlapping dask chunk regions
        to be considered the same segment.  The region for calculating IOU is given by the
        iou_depth parameter.

    Returns:
        segments : array of int32 with same shape as input
            Each segmented cell is assigned a number and all its pixels contain that value (0 is background)
    """
    assert image.ndim == 2, image.ndim
    image = da.asarray(image, chunks=chunksize)  ## prepare the distribution of the image in chunks 
    image = image.rechunk({}) 
    
    ## put an overlap between the tiles, quite big as epyseg doesn't seg on boundaries
    depth = tuple((overlap, overlap))
    boundary = "reflect"
    image = da.overlap.overlap(image, depth, boundary)

    block_iter = zip(
        np.ndindex(*image.numblocks),
        map(
            functools.partial(operator.getitem, image),
            da.core.slices_from_chunks(image.chunks),
        ),
    )

    #labeled_blocks = np.empty(image.numblocks[:-1], dtype=object)
    labeled_blocks = np.empty(image.numblocks, dtype=object)
    print(labeled_blocks.shape)
    total = None
    for index, input_block in block_iter:
        labeled_block, n = dask.delayed(segment_chunk, nout=2)(
            input_block,
            imagedir,
            imagename, 
            index
        )

        shape = input_block.shape#[:-1]
        labeled_block = da.from_delayed(labeled_block, shape=shape, dtype=np.int32)

        #n = dask.delayed(np.int32)(n)
        n = da.from_delayed(n, shape=(), dtype=np.int32)

        total = n if total is None else total + n

        block_label_offset = da.where(labeled_block > 0, total, np.int32(0))
        labeled_block += block_label_offset

        #labeled_blocks[index[:-1]] = labeled_block
        labeled_blocks[index] = labeled_block
        total += n

    # Put all the blocks together
    block_labeled = da.block(labeled_blocks.tolist())
    
    block_labeled = block_labeled.to_zarr(
       tmpfile,
       return_stored=False,
       compute=False,
       )
    _, total = dask.compute([block_labeled, total])[0]
    block_labeled = da.from_zarr(tmpfile)

    depth = da.overlap.coerce_depth(len(depth), depth)

    if np.prod(block_labeled.numblocks) > 1:
        iou_depth = da.overlap.coerce_depth(len(depth), iou_depth)

        if any(iou_depth[ax] > depth[ax] for ax in depth.keys()):
            raise DistSegError("iou_depth (%s) > depth (%s)" % (iou_depth, depth))

        trim_depth = {k: depth[k] - iou_depth[k] for k in depth.keys()}
        block_labeled = da.overlap.trim_internal(
            block_labeled, trim_depth, boundary=boundary
        )
        block_labeled = link_labels(
            block_labeled,
            total,
            iou_depth,
            iou_threshold=iou_threshold,
        )

        block_labeled = da.overlap.trim_internal(
            block_labeled, iou_depth, boundary=boundary
        )

    else:
        block_labeled = da.overlap.trim_internal(
            block_labeled, depth, boundary=boundary
        )

    return block_labeled


def segment_chunk( chunk, imagedir, imagename, index, ):
    """Perform segmentation on an individual chunk."""
    np.random.seed(index)

    from fish_feats.SegmentObj import run_epyseg_onimage

    segments, tmpdir_path = run_epyseg_onimage( chunk, imagedir, imagename, verbose=False )
    if tmpdir_path is not None:
        if os.path.exists(tmpdir_path):
            os.chmod(tmpdir_path, stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH|stat.S_IWUSR|stat.S_IWGRP|stat.S_IWOTH|stat.S_IXUSR)
            shutil.rmtree(tmpdir_path, ignore_errors=True)

    return segments.astype(np.int32), segments.max()


def link_labels(block_labeled, total, depth, iou_threshold=1):
    """
    Build a label connectivity graph that groups labels across blocks,
    use this graph to find connected components, and then relabel each
    block according to those.
    """
    label_groups = label_adjacency_graph(block_labeled, total, depth, iou_threshold)
    new_labeling = _label.connected_components_delayed(label_groups)
    return _label.relabel_blocks(block_labeled, new_labeling)

def label_adjacency_graph(labels, nlabels, depth, iou_threshold):
    all_mappings = [da.empty((2, 0), dtype=np.int32, chunks=1)]

    slices_and_axes = get_slices_and_axes(labels.chunks, labels.shape, depth)
    for face_slice, axis in slices_and_axes:
        face = labels[face_slice]
        mapped = _across_block_iou_delayed(face, axis, iou_threshold)
        all_mappings.append(mapped)

    i, j = da.concatenate(all_mappings, axis=1)
    result = _label._to_csr_matrix(i, j, nlabels + 1)
    return result


def _across_block_iou_delayed(face, axis, iou_threshold):
    """Delayed version of :func:`_across_block_label_grouping`."""
    _across_block_label_grouping_ = dask.delayed(_across_block_label_iou)
    grouped = _across_block_label_grouping_(face, axis, iou_threshold)
    return da.from_delayed(grouped, shape=(2, np.nan), dtype=np.int32)


def _across_block_label_iou(face, axis, iou_threshold):
    unique = np.unique(face)
    face0, face1 = np.split(face, 2, axis)

    intersection = sk_metrics.confusion_matrix(face0.reshape(-1), face1.reshape(-1))
    sum0 = intersection.sum(axis=0, keepdims=True)
    sum1 = intersection.sum(axis=1, keepdims=True)

    # Note that sum0 and sum1 broadcast to square matrix size.
    union = sum0 + sum1 - intersection

    # Ignore errors with divide by zero, which the np.where sets to zero.
    with np.errstate(divide="ignore", invalid="ignore"):
        iou = np.where(intersection > 0, intersection / union, 0)

    labels0, labels1 = np.nonzero(iou >= iou_threshold)

    labels0_orig = unique[labels0]
    labels1_orig = unique[labels1]
    grouped = np.stack([labels0_orig, labels1_orig])

    valid = np.all(grouped != 0, axis=0)  # Discard any mappings with bg pixels
    return grouped[:, valid]


def get_slices_and_axes(chunks, shape, depth):
    ndim = len(shape)
    depth = da.overlap.coerce_depth(ndim, depth)
    slices = da.core.slices_from_chunks(chunks)
    slices_and_axes = []
    for ax in range(ndim):
        for sl in slices:
            if sl[ax].stop == shape[ax]:
                continue
            slice_to_append = list(sl)
            slice_to_append[ax] = slice(
                sl[ax].stop - 2 * depth[ax], sl[ax].stop + 2 * depth[ax]
            )
            slices_and_axes.append((tuple(slice_to_append), ax))
    return slices_and_axes
