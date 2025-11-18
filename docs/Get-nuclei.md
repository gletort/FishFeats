!!! abstract "Segment nuclei in 3D from the nuclei staining chanel"
	_To segment nuclei in 3D, choose the option <span style="background-color:#082cd1">Nuclei:Segment</span> in the main pipeline interface._

!!! example "See the typical workflow of this step [here](./FishFeatsFlowchartv5.pdf#page=3)"

For some images, preprocessing of the nuclei chanels (to smooth, denoise..) can improve the performance. In these cases, first execute the [preprocess nuclei](./Preprocess-nuclei.md) step.

## Segmentation methods

Two segmentation tools are proposed to perform the 3D segmentation:

* [Stardist](#stardist)
* [CellPose3D](#cellpose)


### Stardist 
_Stardist run in 2D + 3D reconstruction._
 
Each z-slice will be segmented in 2D for individual nuclei with [stardist](https://github.com/stardist/stardist) (Schmidt et al., 2018). Then the 3D nuclei will be reconstructed by associating the nuclei from each consecutive slices, either with the `Munkres` method (Hungarian algorithm, optimization of the pairing of the ojects) or with the `overlap` method (associating overlapping object, faster).


??? example "Stardist parameters"

	- `probability threshold`: threshold of stardist output probability to keep a detected nuclei. Increase it will decrease the number/size of nuclei found.
	- `nuclei overlap`: stardist parameter of how much nuclei overlap in general. Increasing it to split more nuclei, decreasing to have bigger objects.
	- `association method`: how to reconstruct 3D nuclei from the 2D slice nuclei, either by combinataion (optimization of the distance between nuclei in two consecutives slices), `Munkres` method, or by associating nuclei from consecutive slices that overlap enough `Overlap` method (faster). 
	- `threshold overlap`: for the `overlap` method, associate two nuclei from consecutive slices as one if they overlap by at least more % than the threshold.
	- `association distance limit micron`: For the `Munkres` method, can associate nuclei from consecutive slices only if they are closer than the distance limit (in microns). 


### CellPose
[CellPose](https://www.cellpose.org/) segments the objects in 2D in the xy, yz and xz directions and reconstruct the 3D objects.

CellPose uses an isotropic image for the segmentation (same scaling in x, y, and z), so if your image is not isotropic (usually) it will resize it as a first step based on the image scaling parameters. However, results might be better if the isotropic rescaling is done before CellPose, so you might consider doing the rescaling as a preprocessing step.


??? example "CellPose parameters"

	- `cell diameter`: CellPose needs to know the average size of a nuclei (in pixels). This parameter is the average diameter of a nuclei, in pixels, and will be used to rescale the image to the corresponding size (it needs the average nuclei diameter to be around 18 pixels).
	- `detection threshold`: varies between -6 and 6. Pixels within objects are detected with a detection probability and will be removed if below the threshold. Decrease it to keep more/bigger objects
	- `resample`: run CellPose 3D reconstruction in the resized scale: slower but more precise if the nuclei are smaller than 18 pixels diameter, faster but less precise if the nuclei are bigger than 18 pixels.  


When the segmentation is finished, the labelled nuclei will be displayed in napari, and can be manually corrected.

#### Dask option

This option combines [CellPose](https://www.cellpose.org/) segmentation with the [Dask](https://www.dask.org/) library for parallel computing. This option is inspired from the [distributed segmentation script](https://github.com/MouseLand/cellpose/blob/main/cellpose/contrib/distributed_segmentation.py) for CellPose. 

It allows to run CellPose on very large images when the non distributed version will crash due to lack of memory or be much too slow.

#### Remark

Since May 2025, the latest version of CellPose is based on [CellPoseSAM](https://www.biorxiv.org/content/10.1101/2025.04.28.651001v1). Some parameters are not anymore relevant with this version, and it might not be optimal for nuclei segmentation (it is more specialized for cell segmentation). Additionally, this version is **much slower** to run, especially if you don't have GPU. 

To use the previous CellPose version with the `nuclei` trained model (more specialized), you must install it in your python environement instead of the latest version. In a terminal, or in the napari Terminal interface (:material-console-line: icon at the bottom left of napari window), type:
```
pip install cellpose[distributed]==3.0
```
(or select the version 3 or less in the Anaconda interface).


## Nuclei editing

### Automatic correction

You can remove all nuclei that are smaller than a given volume, or detected only in very few consecutive slices, with the panel `Filtering` that appears when the segmentation is finished.


To filter, check the `remove small nuclei` option, and choose a threshold volume below which nuclei will be considered as segmentation errors and not kept with the `minimum volume` parameter. 
To remove nuclei that are not detected in several slices, fix the parameter `keep ifatleast z` to the minimum of z slices in which one nuclei should be present to not be an error.

Click on `Update nuclei` to perform the automatic filtering and get rid of "too small" nuclei. You can close this panel when you don't want to use it anymore.


### Nuclei: manual correction

Here we also use a label layer to edit the nuclei segmentation.
_See napari Label layer [documentation](https://napari.org/0.5.0/howtos/layers/labels.html) for more information on the label edition tools available by default in napari (and accessible in the top left panel of the interface)_

???+ tip "Shortcut/options"

	=== "Visualization"
	
		|   |     |	
		| ---------- | ------------------------------------ |
		| <kbd>F1,F2,F3</kbd>... | Show/hide the 1st,2nd,3rd.. layer (ordered as visibile in the bottom left panel) |
		| :fontawesome-regular-square: | _(bottom left)_ Switch between 2D/3D view | 
		| <kbd>Ctrl-v</kbd> | In 3D view, (de-)activate vispy visualization mode. It allows to set the view perspective, by right-cliking and holding it. **Note that in vispy active mode, selecting a label doesn't always work (click coordinates are unprecised)** |
		| `show selected` | _(top left panel)_ Show only the current label (pixels which have the value taht is currently active the label field) |
		| :fontawesome-solid-eye: | _(bottom left panel)_ Show/hide the corresponding layer | 
		| <kbd>v</kbd> | Show/hide the current layer |
		| <kbd>l</kbd>, `show cellnames` | _(right panel)_ Show/hide the label of the nuclei (in 2D only) |
	
	=== "Label (nuclei) editing"

		|   |     |	
		| ---------- | ------------------------------------ |
		| `ndim=2` | _(top left panel)_ Modifying a label affects only the current z-slice (2D) |
		| `ndim=3` | _(top left panel)_ Modification in one z-slice will be propagated to its neighboring slices |
		| <kbd>2</kbd> | Switch to drawing mode (:fontawesome-solid-paintbrush:). Draw the current label under the clicks. The precision of the drawing brush is controled by `brush stroke` parameter _(top left panel)_ | 
		| <kbd>3</kbd> | Switch to fill mode (:fontawesome-solid-fill-drip:). Replace a whole label (clicked nuclei) by the new value (active label). |
		| <kbd>4</kbd> | Switch to picking mode (:fontawesome-solid-syringe:) to select a label. When you click on a label (nuclei), it will set the active label to its value (in `label` field). |
		| <kbd>Ctrl</kbd>+:material-mouse-right-click-outline: | Remove the label (nuclei) under the click |
		| <kbd>m</kbd> | Set the active label to the maximum label + 1 (to be sure to create a new nuclei) |
		| `relabel` | Renumber all the nuclei from 2 to the number of nuclei. |

As for junctions, the labels should be unique for each nuclei. 
Thus if you want to add a new nuclei don't forget to **get the max label + 1 by pressing <kbd>m</kbd>**. 

You can see the value of the label of a nuclei by selecting it with the picker tool, or by hovering the mouse pointer on top of it. It displays the value of the current layer intensity below your pointer in the left bottom panel of the napari window, see image below:

![nucleilab](imgs/nucleilab.png)

If you are in vispy active mode, the value below your pointer is "0" which means that in this view mode, the reading of the position of the pointer is not working well.



## Save/load nuclei file

When you click on `save nuclei`, it will save the current nuclei segmentation as a labelled image in the file called _imagename_`nuclei.tif` in the results folder.
You can load this file to re-edit it later or load the nuclei with the `Load segmented file` option in the `Get nuclei` interface. 

When you have finished the nuclei segmentation, click on `Nuclei done` to quit this step of the pipeline and go back to the main pipeline.

