!!! abstract "Estimate or correct the Z position of each cell"
	_Choose <span style="background-color:#b60c00">Cells:3D position</span> in the main action choice interface to visualize and edit cells Z position._

Epithelial junction are segmented on the [2d projection](Get-cells.md) of the junction staining. From this segmentation, each cell is then back-projected in the 3D junction staining to estimate its position in Z. This information is saved in a file called *imagename_cellsZ.csv*. You can directly modify this file and put the desired Z value in the corresponding cell row, or use the plugin interface to modify it manually.

The pipeline draws the cells at their respective Z-position. You can visualize it in 3D by switching to the 3D mode at the left bottom of the napari interface, but editing should be done in the 2D view. 

## Z-map calculation
If the Z positions of the cells are mostly wrong, you can recalculate them by clicking on `recalculate zmap`.
This back-projects locally the junction staining by finding the Z that has the most similarity with the projected staining. 
This map precision depends on the parameters:
* `zmap resolution` which is the size (in pixels) of sliding windows on which the Z is estimated. A lower value will allow for more resoluted values but will take longer to calculate.  
* `zmap localsize` is the size of the neighboring area used to calculate the best similarity of the projected and original staining. If it's too small, it can influenced by local noise while too large values doesn't account for tissue high curvature (where the Z of the tissue varies rapidly).

## Individual cell correction
When the global Z positions are correct, you can then edit each individual Z position. For this:
* <kdb>Right-click</kbd> on the cell to edit. The value of its label will be put into `cell label` parameter
* Go to the correct Z slice
* <kbd>Control+left-click</kbd> to place the selected cell at the current Z position (visible slice). The value of the Z will be put into the `place at z` parameter and you will see the cell appaearing in the current slice.

These steps should be done in that order for the option to function correctly.

![zpos3d](imgs/zpos3d.png)

When all corrections are done, save the new positions by clicking `Save updated cells`.

## Export 3D segmentation

This option exports a 3D stack of the cell labels, placed in their 3D position as a `.tiff` file.
The exported file will be saved in the `results` folder, called *imagename_cells3D.tif*.
This file is not necessary for any other step of the pipeline, so click it only if you want to have the 3D segmentation exported to use in another software.

