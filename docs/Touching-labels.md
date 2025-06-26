!!! abstract "Transforms the segmented cells to connected labels (touching)"
	_Select `Touching labels` in the action choice list to do this step_

In general after segmentation, the labels (the cells) are separated by one (or more) black pixels corresponding to the junctions. This option expands the labels so that they all touch, so that it can be used into other plugins like [Griottes](https://github.com/BaroudLab/napari-griottes) to generate the graph of the cells neighboring relationship.

![touchs](docs/touchs.png)
