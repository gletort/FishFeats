!!! abstract "Threshold a chosen channel/layer"
	_Select `Misc:Threshold channel` in the main pipeline interface to choose a channel/layer and the threshold to apply_

This option opens a panel to let you choose which channel you want to threshold.
For flexibility, we let you choose any layer among the ones currently opened so that you could also threshold something else than the raw channel images.

In `Threshold layer:` select the layer (from its name) that you want to threshold.
The plugin will only show this layer and add a new layer called `Threshold`*layername* that contains the binary image after applying the threshold.
The threshold layer is shown in white with transparency on top of the selected layer.

Then slide the `Threshold` layer to choose the value of the threshold to apply.
The display will change automatically as you slide it so you directly see the effect of your threshold choice.
By default, the value is put to the mean of the image.

![Threshold channel](./imgs/threshold_channel.png)

If you change the layer to threshold, or quit this option, the plugin doesn't close the threshold layer, so that it can be used in other part of the plugin. 
If you wish to close it, do so manually by selecting it in the layers list and click on the trash icon.
