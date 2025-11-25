!!! abstract "Preprocess the nuclei channel for better segmentation"
	_To preprocess the nuclei staining image, choose the option <span style="background-color:#082cd1">Nuclei:Preprocess</span> in the main pipeline interface._

You can either apply filters to improve the image, or use noise2void, a deep learning method that reduces the noise in images.

!!! note "Applying preprocessing outside FishFeats"
	If you want to apply other preprocessing that are not yet available in FishFeats, you can either work with another software with the required softwares and save the preprocessed nuclei in the input image, or work other napari plugins and use the option to [start FishFeats from already opened layers](./Open-image.md#load-raw-images-from-fishfeats). 
	_You can also contact us ([filling an issue](https://github.com/gletort/FishFeats/issues/new/choose) in this repository) to ask for the possibility to add a given preprocessing algorithm in FishFeats_

![interface](./imgs/nuclei_preprocess.png)

## Filtering

FishFeats proposes several classic filters to improve the image quality for the segmentation task.
In some cases, this can help the segmentation process.

**Median filter**: If you have a lot of small noisy dots, you can apply a median filter that will locally smooth the image and get rid of small bright or dark dots.
Try to take a filter radius below the average size of a nuclei.
The filter is much slower for higher radii. 
Select the option `Median filtering` and click on `Apply preprocessing`.

**Remove background**: if you have an heterogeneous background in the image (eg a darker corner) and that it seems to impair the performance of the segmentation algorithm (it's not always the case if local normalization is applied), you can remove the background to have more homogeneous local intensities, and a background always close to 0. 
Select the option `Remove background` and click on `Apply preprocessing`.


If you are happy with the filtering, click on `Preprocessing done` to use this new version in the segmentation process. Otherwise, click on `Reset nuclei staining` to test other parameters.

## Noise2Void

Denoising with noise2void requires the napari plugin `napari-n2v` that you can install in the virtual environment: `pip install napari-n2v` or through the napari plugin interface.

Click the button `Noise2Void` to open the napari noise2void plugin interface. It will open an interface to perform denoising with a trained noise2void model.

If you don't have a trained noise2void model, you have to train one through the noise2void plugin, externally of FishFeats. 
Noise2void doesn't need annotated data to train, so you will only have to load your image in it and use the options to train it. 
