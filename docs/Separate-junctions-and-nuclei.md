!!! abstract "Separate junctions and nuclei staining acquired in the same chanel"
	_Choose `separate junctions and nuclei` in the main pipeline interface to do this step and change the separation parameters._ (1) 
	{ .annotate }

	1. If you do directly the junction or nuclei segmentation, the plugin will automatically do this step with the default parameters. When the separation is not good, then it is necessary to follow this step to choose better parameters.


When the `junction channel` and `nuclei channel` parameters from the [Image scalings interface](Image-scalings.md) are set to the same value, the program will try to separate automatically the two stainings to have one only-junction signal and one only-nuclei. If this step is not called before, the `Cells:Segment` and `Nuclei:Segment` steps will call it. 

⚠️ The separated images are artificial. Be careful if you plan to do intensity measurement, the value of the pixel in these separated images are not relevant ! The separated images are useful for segmentation purposes, for measurement you should use the original image.

## Separation methods

Three options to separate are proposed:

- `sepaNet`: [SepaNet](#sepanet) uses a neural network trained to separate junctions and nuclei staining. 

- `Tophat filter`: [Tophat](#tophat-filtering) uses several filtering to separe line structures to large roundish structures.

- `Load`: if the separated files had been previously saved, you can directly load them and avoid to do the separation again. The pipeline proposes the `Load` option by default when the files are presents.

![separated](./imgs/separated.png)

 When the separation is finished, two new layers will appear, called `nucleiStaining` in blue and `junctionsStaining` in red. You can check that the separation worked well enough and re-run it with new parameters if not.  

### SepaNet
When using this method, you must give it the location of the trained neural network (SepaNet), by selecting it through the `sepanet_path` parameter. Go inside the network folder to select it (you should see the `assets` and `variable` folders). Then the plugin will directly run the prediction with the selected network.

SepaNet has been trained on several images of zebrafish, stained for nuclei with PCNA or DAPI and for junctions with ZO1. The two staining were separated and sometimes we also had the mixed staining acquisition, otherwise there were mixed artificially for the training.



### Tophat filtering
With this method, several parameters need to be tuned to your image scaling:

- `tophat radxy`: to favors junctions over nuclei (lines compared to full spheres), a top hat filter is applied to the image. This parameter is the size of this filter in the xy direction. It will keep as junctions the structures (lines) that are smaller in width than the xy radius.

- `tophat radz`: size of the top hat filter in the z direction.

- `outlier thres`: outliers point are removed before to apply the filtering, to not be too influenced by small bright points. Decrease this threshold to remove more small bright points, increase it if it removes too much signal.

- `smooth nucleixy`: after applying the separation, apply a smooth filter on the nuclei signal, size in xy

- `smooth nucleiz`: size in z of the smoothing filter for the nuclei signal

## Other parameters

* `close_layers`: if checked the two created layers `nucleiStaining` and `junctionStaining` will be closed at the end of this step, when clicking on `Separation done`.
*  `Save separated`: save the two separated images in the `results` folder. This is advised to reload the process later and avoid to do the separation again. 

