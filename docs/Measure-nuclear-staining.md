!!! abstract "Measure the intensity in one or more chanels in the nuclei of cells"
	_To measure nuclear intensity, choose the option <span style="background-color:#bda30f">Measure: nuclear intensity</span> in the main pipeline interface_

!!! example "See the typical workflow of this step [here](./FishFeatsFlowchartv5.pdf#page=5)"


To measure the intensity in the nuclei, they **must have been segmented** before. 
If you haven't done it yet, go to [Get nuclei](./Get-nuclei.md) step first.

This step allows to measure the nuclear intensity of a chosen staining inside each segmented nucleus.
Choose the channel to measure and click on `Measure` to launch the computation.
The measure can take time.

![nuclear measure](./imgs/nuc_measure.png)

Once the measure is done, you can visualize the table of measurement by clicking `Show measures table`.
A new window will pop up with the list of nucleus and their label, along with the measures in the selected channel.

Clicking `Save and stop` will save these results for all nuclei associated to one cell in the *_imagename_results.csv_* result file.
However, if you want to save the nuclear intensity in ALL nuclei (not only the ones that are linked to a cell), you can click on `Save all nuclei measures`.
This will create a new result file in the `results` folder, called *_imagename_nuclei.csv_* that contains the displayed table data.
