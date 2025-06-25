Encountered errors and solutions:

## Module versions

* `skimage.morphology.selem` module not found error => Problem of compatibility between big-fish and scikit-image versions. Ideally, chooses a recent version of skimage (scikit-image==0.19.3) and big-fish (big-fish==0.6.2).
* 

## Acces violation reading


`OSError: exception: access violation reading 0x0000000000000034`.

This error happened only in Windows with specific nvidia card (A6000).
It happens when adding or deleting Shape layers, quite often in `cytoplasmic measure` option.
It seems to be an error external to the plugin or napari. 
We haven't found a solution yet, but please refer to [this discussion](https://forum.image.sc/t/napari-crash-problem-with-opengl-and-or-vispy-and-or-nvidia-and-or-windows/113859) on imagesc forum for more infos/updates.
