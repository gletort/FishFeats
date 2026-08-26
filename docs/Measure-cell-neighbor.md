!!! abstract "Measure the number of cell neighbors"
	_To measure the cell neighborhood, choose the <span style="background-color:#bda30f">Measures:Cell neighbors</span> in the main pipeline interface._

This step allows you to measure the number of neighbors of each cell (after segmentation).
It assumes that the cell junction are less than 3-pixel wide to consider cells as neighbors. 
If there are situations where this threshold should be increased (thicker junctions), please contact us to add the option to choose the maximum distance to consider cell as neighbors.

After selecting this option, the plugin will directly compute the Region Adjancy Graph of the labeled image and returns for each label (cell), its number of neighbors and the labels of these neighbors in a table displayed in the right side of the interface.
The resulting table contains the label of the cell `CellLabel`, the number of direct neighbors of this cell `NbNeighbors`, not considering the background, and the list of the label of the cells that are counted as neighbors `Neighbors`.

A map of the cells, colored by their number of neighbors is also displayed and added as a layer in the left side interface, called `NbNeighbors`.
You can change the display properties of this layer with the napari default options, as for all the other layers.

To add these informations to the main `FishFeats`table results that is saved in the `results.csv` file and reloaded everytime, press the button `Add to results` before to close this step.
