!!! abstract "Segment the junction staining to detect the cells apical area."
    _Choose <span style="background-color:#b60c00">Cells:Segment</span> in the main interface to run it._ (1)
    { .annotate }

    1.  Nb: in previous version of FishFeats, this step is called `Get junctions` in the interface

!!! example "See the typical workflow of this step [here](./FishFeatsFlowchartv5.pdf#page=2)"

## Segmentation process

**1/ 3D->2D:** The segmentation of the cellular junctions is performed in **2D**. First the junction staining will be [projected in a 2D](#2d-projection) plane by taking a local average of the slices around the maximum intensity signal. If the nuclei staining is in the same channel, the signals will be separated first. In that case, when you click on `Get junctions` the interface to [separate junctions and nuclei](Separate-junctions-and-nuclei.md) will appear and you must execute it before to be able to do the segmentation. A layer called `2DJunctions` will appears when the projection will be finished/loaded.

**2/ 2D segmentation:** The plugin proposes several options to perform the segmentation from the 2D images of junctions:

* [Epyseg](https://github.com/baigouy/EPySeg): tool for epithelial segmentation from Aigouy et al. 2020.
* [CellPose](https://www.cellpose.org/): tool for cellular segmentation from Stringer et al. 2021.
* Load an already segmented file (should be a file of labelled cell). If you choose this option, the plugin will look for the labelled file of cell, named _imagename_`_cells2D.tif` in the results folder, but you can select another file.

**3/ Manual correction:** When the computation of the segmentation is finished, `fishfeats` will show you the results in a `label` layer called `Junctions`. You can then perform manual correction if needed before to save the results.

**4/ 2D->3D:** At the end of the process, when you click on `Junctions done`, the pipeline creates the cells from the segmentation. The shape will be the label shape and the [cell position in Z](3d-cell-positions.md) will be back-projected into the junction staining. Thus this step can take a few minutes to calculate the back-projection. 

![get_juncs](imgs/get_juncs.png)

### 2D projection 

The junction staining will be segmented in 2D. 

If you have already calculated the projection previously or with another pipeline, you can load here the image of the projection and directly use it. Else, the pipeline will calculate the projection by looking at local maximum intensities.

![projecting](imgs/projection.png)

The projection will be displayed in a new layer, shown in white, and called `2DJunctions`.
The pipeline will by default save the calculated projection in the `results` folder, except if you don't check the `save projection` option. When this step is done, you can now performs the segmentation of this projected image.

#### Loading projection

Click on `Load default` if you have already saved the projection with the default name (`yourimagename_junction_projection.tif`).

If you have calculated the projection in an other software (e.g with [LocalZProjector](https://gitlab.pasteur.fr/iah-public/localzprojector) in Fiji), you can choose the file of the projected junction channel and load it directly. 
If the option `save projection` is selected, the loaded file will be copied and saved in the main `results` folder, with the pipeline's default name for the projection.

#### Calculating the projection

The junction staining will be projected in 2D, by looking at the local maxima positions in Z in the neighboring of each pixels.
The intensity around this local maxima position will then be projected in 2D for each pixel.

You can directly try to click on `Project now` to calculate the projection with the default parameters.
If the result is not satisfying, then several parameters can be tuned by checking the `Advanced` option:
* Local size: size of the local window around each pixel to look for local maxima
* Smoothing size: amount of smoothing of the projected pixels
* Do local enhancement: performs local contrast enhancement with CLAHE method. This is useful if the illumination is quite variable in the image to uniformize it before segmentation
* CLAHE grid size: if performing local enhancement, size of the grid use to locally improve contrast

Click on `Project now` to recalultes with the new parameters.

If this algorithm don't succeed even with tuning the parameters, you can use dedicated software to local projection as [LocalZProjector](https://gitlab.pasteur.fr/iah-public/localzprojector) and then load the results in `fishfeats`.


## Manual correction

The result of the segmentation is saved and displayed as labelled apical cells: each cell is assigned a unique number (the label) that is put in all the pixels inside the cell surface. The colors reflect the values (labels) of each cell. 0 indicates background pixels (no cell). In `fishfeats` the label `1` is reserved to indicate unassigned elements, so should not be used to label cells.

To correct eventual segmentation errors, on the left top panel, you have the napari tools to edit labels and on the right panel additional `fishfeats` editing options.

???+ tip "Shortcut/options"
    
     _See Napari Label layer [documentation](https://napari.org/0.5.0/howtos/layers/labels.html) for more information on the label edition tools available by default in Napari (and accessible in the top left panel of the interface)_

	=== "Visualization"
	
		|   |     |	
		| ---------- | ------------------------------------ |
		| <kbd>F1,F2,F3</kbd>... | Show/Hide the first, 2nd, 3th.. layer (ordered in the bottom left panel from bottom to top) |
		| `contour` | Labels (cells) can be displayed as filled areas (put `contour` to 0) or only with the contour lines (`contour`>0). |
		| `show selected` | Display only the current label (the pixels which ahve the value that is currently acitve in the `label` field). |
		| ++l++ | Show/Hide all the labels value as a text overlay. _Or check/uncheck `show cellnames` in the right panel_ |
		| ++5++ | Switch between zoom/moving mode |
		| ++v++ | Show/hide the current layer (the `Junctions` layer) |
		| <kbd>Ctrl+c</kbd>/<kbd>Ctrl+d</kbd> | Increase/Decrease the labels contour width (will be filled if reaches 0) |

	=== "Label (cell) editing"

		|   |     |	
		| ---------- | ------------------------------------ |
		| ++2++ | Select drawing modes (or click on :fontawesome-solid-paintbrush:). When it's active, it will draw with the current `brush stroke` size|
		| ++3++ | Select filling mode: it replaces a whole label at one by the current value (:fontawesome-solid-fill-drip:) |
		|:material-mouse-right-click-outline:|Select the label under the mouse. Or ++4++ to switch to picker mode, then click on it|
		|<kbd>Ctrl</kbd>+:material-mouse-right-click-outline: | Delete the whole label (cell) below the click |
		| <kbd>Ctrl</kbd>+:material-mouse-left-click-outline:| Merge two neighboring labels into one cell. You should keep the mouse button clicked when dragging from one to another.|
		| `Relabel` | Reorder the cell names (labels) with consecutive values from 2 to the number of cells |
		| ++m++ | Draw a new cell: select unused value and switch to drawing mode |
		| `preserve labels` | If checked, other labels than the currently active one cannot be modified when you are drawing (so even if you touch them they will not be edited) |


## Save corrected results

To save the manual corrections, click on `save junctions`. It will save a file called _imagename_`_cells2D.tif` in the `results` folder that contained the labelled cells.

## Measures
You can display a table of measurements of the cells position, area and label. Click on the button `Show measures` to perform the measurement. A new window containing the table of all the cells and their area will appear.

![get_cells_measures](imgs/measurecells.png)

This table will be automatically saved when the cell segmentation is saved, in the _imagename_`_results.csv` output file and will be completed during the pipeline by other measurements (cytoplasmic measures, nuclei measure, RNA counts...)

## Junctions analysis finished

When you have finished the segmentation and manual correction steps, click on `Junctions done` to quit this step and go back to the main step choices.

If `save when done` is checked, the segmentation will be saved as a `.tif` file that can reloaded later, as well as the table of the cell coordinates and area in the _imagename_`_results.csv` output file.
