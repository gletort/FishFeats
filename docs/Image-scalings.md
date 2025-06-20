!!! abstract "Set the image properties (scaling informations, color channels)" 
	_Choose the option `Image scalings` in `fishfeats` main step choices interface to do this step._ (1) 
    { .annotate }

    1. This step is loaded by default when you open the image on which to work on.

![start_scale_anoot](imgs/start_scale_anoot.png)

On the right panel, you have a parameter dialog called `Scale` on which you can set-up the image global parameters:

* `scaleXY`: the size in µm of 1 voxel in the XY direction.

* `scaleZ`: the size in µm of 1 voxel in the Z direction.

* `direction`: direction of imaging, if junctions are above the nuclei when you move in Z, then select `top high z`, else if the junctions are towards the smaller z, select `top low z`

* `junction channel`: number of the color channel image in which junction staining is. The number is indicated in the name of each layers in the left panel: `originalChannel0`, `originalChannel1`...

* `nuclei channel`: number of the color channel image in which nuclei staining is. 
!!! warning "Channel separation"
    If the nuclei staining is in the same channel as the junction staining, put the same values for the two parameters and the program will [separate the two signals](./Separate-junctions-and-nuclei) later on. If not, be sure to put different numbers, otherwise it will try to separate the two staining.

The plugin reads the metadata of your image and will prefill the scaling parameters based on that. However, there can be some mistakes depending on the metadata format, so it's important to always check that the scaling is correct.

A configuration file is created in the `results` folder when you launch the pipeline. It records some information on your current step and the parameters that you selected. If you quit the plugin with the option `Quit plugin` it will then saved this file that can be read the next time you used `fishfeats` on the same image. It will then pre-select the parameters to the one you filled the first time. The recorded file is saved in the `results` folder, named as the image but with a `.cfg` extension.

Click `Update` when you have selected all the parameters to choose the next analysis step to perform.
