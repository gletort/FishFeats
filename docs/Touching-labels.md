!!! abstract "Transforms the segmented cells to connected labels (touching)"
	_Select `Touching labels` in the action choice list to do this step_

In general after segmentation, the labels (the cells) are separated by one (or more) black pixels corresponding to the junctions. This option expands the labels so that they all touch, so that it can be used into other plugins like [Griottes](https://github.com/BaroudLab/napari-griottes) to generate the graph of the cells neighboring relationship.

![touchs](imgs/touchs.png)

## Napari-Griottes interoperability

This option allows to use the [napari-Griottes](https://github.com/BaroudLab/napari-griottes) plugin to generate spatial graph of cells relationship.

To install this plugin, do: 
```
	pip install napari-griottes
```
in your virtual environment.


To use the plugin, starts it in `Plugins>Griottes>Make graph`.
Choose the layer `TouchingCells` in the `label layer` parameter, and run it with the normal Griottes paramters.

When the computation is finished, Griottes displays the results in the **pixel scale**. 
As the images in `FishFeats` are scaled from their metadata, they might not be the same size in the display.
To adjust the output of Griottes to the same scale as your data, click the `Scale Griottes image` in the `Touching labels` panel of FishFeats.

![griotte](imgs/touch_griot.png)


