!!! abstract "Measure the intensity in one or more chanels in the cytoplasm of cells"
	_To measure cytoplasmic intensity, choose the <span style="background-color:#bda30f">Measures:Cytoplasmic intensity</span> in the main pipeline interface._

!!! example "See the typical workflow of this step [here](./FishFeatsFlowchartv5.pdf#page=5)"

This step allows you to measure the average intensity (normalised or not) in the cells (after segmentation) in a few z slices close to the cell junctions. You can measure the intensity in several chanels. By default, one is initally proposed, click on the <kbd>+</kbd> sign next to the `cyto chanels` parameter to augment the number of chanels to measure (or <kbd>-</kbd> to remove one). Then, for each chanels to measure, set its number to the corresponding `originalChanel*` staining that you want to measure with the `cyto chanels` parameter(s). When you change the value of this parameter, the plugin shows you directly which chanel you are measuring. 

![cytomes](imgs/cytomes.png)

The parameter `z_thickness`controls the number of slices below the cell surface will be used in the measurement. In the image below, the intensity will be averaged on 3 slices starting from each cell surface.

## Background rectangle

When you choose a chanel or add a new one, a layer `backgroundRectangle*` appears in the left panel. Its number at the end of the name corresponds to the number of the chanel to analyse. This rectangle will be used to normalise the intensity in this chanel by dividing by its mean intensity. So you must place this rectangle in a background area of your staining, and in the typical z slice where you are going to measure the signal (should be there by default). You can move it or change its size. 

## Output

You can set the parameters to either pop-up the measurement table, or add a new layer with the cells filled by the measured intensities or save the measurement table to an excel file. The image of measurement intensity shows the normalised intensity measured in each cell, in the same color as the original chanel, ranging from dark for low value of normalised intensity to bright for high intensity. There will one image for each measurement chanel asked.

![measureIm](imgs/measureIm.png)

The measurement table gives you the list of all cells with their label and position. The last columns are the measured intensity in each measurement chanel asked. For each chanel, 4 values are given: the mean intensity, its standard deviation, the normalised mean intensity and its standard deviation. The columns are named `Cyto*_MeanIntensity`... where the number after `Cyto` is the number of the measured chanel (staining).
