# Step-by-step example 

Here, we propose step-by-step examples of possible usage of the pipeline.
You can download test data from the zenodo repository to follow it.

All the examples here are done with the image `AB3-HG-AQUCISITION-4CHANNELS-SHRNActrl-filtered_minicrop.ims`.

## Open the image and check/set the metadata

Open `Napari` and start FishFeats with `Plugins>FISHFEATS>Start fishfeats`.

A window dialog appears to select the image to analyse. 
Browse your folders and select the downloaded image `AB3-HG-AQUCISITION-4CHANNELS-SHRNActrl-filtered_minicrop.ims` (or another one on which you want to do this test).

The image is loaded and is displayed with its color channels side by side. 
At the right of the interface, you can set the metadata of the image.

Check that the scaling metadata were correctly loaded and correct them if needed (see image below).

![metadata image](./imgs/step_metadata.png)

Then, check that the 3D direcion of the image is correct (the higher Z slices correspond to the apical cells = `top high z`).

Set the channels number that contains the junction staining (Zo1) and/or the nuclei staining (DAPI, PCNA, Sox2). 
In our example image, the first channel contains the junction (Zo1), which correspond to number `0 (originalChannel0`), in red.
The nuclei channel is the last channel, `originalChannel3`.

Finally click on `Update` to set these properties for the image. 
All this set-up will be saved in the configuration file `AB3-HG-AQUCISITION-4CHANNELS-SHRNActrl-filtered_minicrop.cfg` associated with this image.
When you reload this image in FishFeats, it will read this configuration file and load it back. 
This file can also be useful if you don't remember which option and parameters you selected for a given step. 
You can open this file and you will see the list of steps and parameter values used.

You can then choose which steps to perform depending of your analysis by selecting the step in the `Main` panel in the right side of the window.

### Segment epithelia cells

To segment the apical contour of the cells, choose `Get cells` option.

If you have already done this step, the plugin will write `Found projection file` and/or `Found cell file` if it found the corresponding files with the default names. 
You can then choose the option `Load preivous files` to directly load them and go to the manual curation step.

Else, select `do projection and segmentation`.

An interface opens to perform the projection.
You can either load a file of the projected junction staining if ou have done it with another external software (e.g. CARE, LocalZProjector), by clicking on `choose file`. 

Otherwise, click on `Project now` to calculates the local projection with FishFeats.
The projected results will be overlaid in white in your window (image below).
If you are not satified with the results, you can click on `Advanced` to change the parameters and `Project now` again.

![Image after projection](./imgs/step_projed.png)

Then click on `Projection done` to perform the segmentation on the projected channel.


Choose `Epyseg` in the `Method` interface to perform cell apical segmentation (or CellPose).
If you haven't installed `Epyseg` (not mandatory), you will get an error message. 
Install it in your virtual environement by typing `pip install epyseg`.

Click on `segment cells` and wait for the segmentation to be calculated (0.105 min on this test image with 1 GPU).

![Image after segmentation](./imgs/step_seged.png)

You can manually correct the segmentation with shortcuts that are indicated at the top left of your window.

Click on `Cells done` to finish this step and save the results.
Wait while the program save the data and replace the projected cells in 3D.
This can take a little time as it is looking for the best Z-position for each cell.
