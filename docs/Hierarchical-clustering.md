!!! abstract "Performs hierarchical clustering of the segmented cells from FishFeats results "
	_click on `Plugins>fishfeats>Hierarchical clustering` to start this option_

From a data table where rows are the segmented cells and columns are measures from FishFeats (e.g. RNA counts, cell area..), it displays the resulting clustering on the segmented cells, colored by cluster.

## Requirements

First, this analysis uses the segmentation of the cells, in 2D, as can be saved from `fishfeats` main pipeline in the [Get cells](Get-cells.md) step.

Second, it requires a table file (.csv) that contains the measures to be clustered, as can be saved in the `_results.csv` file from `fishfeats` main pipeline in the [Get RNAs](Get-RNAs.md) or [Measure cytoplasmic staining](Measure-cytoplasmic-staining.md) steps.

## Usage

When you click on `Plugins>fishfeats>Hierarchical clustering`, the plugin will ask you to choose the image that you are analysing, as it is done in `fishfeats` main pipeline. Then the interface let you check and update the scale of the image (not important here) and the file that contains the segmentation of the cells in 2D. By default, it will propose you the file in the `results` folder named `*imagename*_cells2D.tif` if it exists.

When you click on `Update` you get to the main part of the plugin. 
First, you have to choose the `.csv` table file that contains your features to use for the clustering. The file must contains one column named `CellLabel` that indicates the corresponding cell in the segmentation file. This column must not be selected in the features to use for clustering, only be present in the file.
Each row should contains the feature values of the corresponding cell. 

When you have selected the file, the plugin will automatically load the names of the columns and show them in the `use column` parameter. Select the columns (features) you want to use to perform the cell clustering.
The unselected columns will not be used. Click on `Cluster from selected columns` when you have selected the columns of interest. The program will calculate the clustering based on the Ward hierarchical clustering algorithm, then show you the resulting clustering on the segmented cells (one color = one cluster) with the corresponding dendrogram in the right side.

![hier_analysis](imgs/hier_analysis.png)


You can vary the number of clusters to create with the `nb clusters` parameter. As soon as you change its value, it will update the display. If you want to change the columns to use in the clustering, you can still change your selection in the `use column` parameter but have to click on `Cluster from selected columns` again.

Finally, you can save the resulting images with the two buttons `save clustered cells`and `save dendrogram`. The images will be saved in the `results` folder, and named `*imagename*_ClusteredCells_nclus_*n*.png` or `*imagename*_ClusteredDendrogram_nclus_*n*.png`, with *n* being the current number of clusters.

