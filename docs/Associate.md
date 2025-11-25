#Associate to cell
!!! abstract "Associate segmented apical cell with segmented nuclei"
	_Choose <span style="background-color:#082cd1">Nuclei: Associate to cells</span> in the main pipeline interface to run this step._ The cell junctions and the nuclei must have been segmented/loaded before to do this step.

Once you have separately segmented the cells (their surface) and the nuclei, this step allows for the cells and nuclei to be paried together to define the full cell. At the end of it, you will have for each segmented cell a corresponding nucleus (indicated by its label) or none if no close enough nuclei corresponded.

You have to first run an [automatic association](#computing-association) that will try to find the best pairing (nucleus, cell) combinations. Then you will get a step to [manually correct the association](#manual-correction). 

## Computing association

The algorithm to do the association is the Hungarian algorithm that finds an optimal pairing of nuclei and cells based on a linking cost. This cost, the distance between the nuclei and the cell is taken as the distance in 3D between the cell surface center and the nuclei center , plus the distance in the (x,y) plane between those two centers (this addition allows to penalize more for distance in XY as nuclei are more vertically below the cell surface).

The parameter `distance toassociate micron` defines a threshold distance (the distance3D+distance2D) above which a nucleus is considered to far to correspond to the cell. This reduces the number of candidate nuclei and the searching range to do the association, thereby speeding-up the computation, but may leave some nuclei unassociated with cells.

Once the association have been computed, you obtain two new layers on the left panel, `CellNuclei` and `CellContours` that contain the cell labels and the updated cell nuclei label. The nuclei labels are changed so that their labels match with each associated cell (thus a nuclei and cell with the same value are associated). In general, the colors should match as well, but it is not always the case, so check the label value by hovering over the nuclei and right-clicking on the cell surface to get the cell label.


## Manual correction

![assoe](imgs/assoe.png)

???+ tip "Shortcut/options"

	- To see the value of a nucleus label, you can _put the mouse on top of it_ and you will see its label on the bottom left panel (except if vispy visualisation mode is on, disable it to get the value). Or you can _double-left click_ on it to put its value on the `nucleus` parameter in the `CellNuc association` panel.
	- _Right-click on a cell_ to get its label and have it put to the `cell` parameter in the `CellNuc association` panel.
	- _Click on `Associate now`_ to associate the nucleus with label `nucleus` with the cell with label `cell`. If another nucleus has already the same label of the cell to associate with, its value will be changed to the maximum label + 1. _Shortcut: press on <kbd>c</kbd> to do the association_. The selected nuclei should change its color and label value to the `cell` one.
	
	Additional options:
	
	- `show_cellnames` add the value of each cell label in the image.
	- `sync cellsNuclei` synchronize the `CellNuclei` and `CellContours` layers, so that visualisation options set on one layer are also set on the second layer. This is usefull to see only one label (with the `show selected` option in the top left panel) in both layers at the same time. 

![assosync](imgs/assosync.png)

# Outputs

When the association is finished and corrected, save the two label files to be able to reload them later. By default, the cell surface will be saved in a 2D label image called `_imagename_\_cells2D.tif` in the `results` folder,the same as for the junctions segmentation. The nuclei will be saved as a 3D label stack, containing each nuclei with its associated label in a file called `_imagename_\_nuclei.tif`. 
The `save also3D junctions` option saves another file of the cell surface labels at their corresponding slice (Z) for each cell.

Click on `save association` to save these files and you can click on `Association done` to finish this step.
