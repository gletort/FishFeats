## Encountered errors and solutions:

### Module versions

* `skimage.morphology.selem` module not found error => Problem of compatibility between big-fish and scikit-image versions. Ideally, chooses a recent version of skimage (scikit-image==0.19.3) and big-fish (big-fish==0.6.2).
* `numpy.core.multiarray failed to import` (on python 3.11, when calling stardist) => Problem of compatibility between numpy version and stardist. You can downgrade numpy to 1.26, tensorflow to 2.14 
* `DNN library is not found.
	 [[{{node model/down_level_0_no_0/Relu}}]] [Op:__inference_predict_function_14500]` (on python 3.10, when calling stardist, epyseg or SepaNet) => Problem of tensorflow version compatibility with your cuda drivers installation. See here for the compatible versions [cuda-tensorflow](https://www.tensorflow.org/install/source?hl=pl#gpu). See also this [discussion](https://forum.image.sc/t/dnn-library-is-not-found-problem-with-tensorflow/81673) about this problem.

### Weird point selection

We encountered a weird point selection on a version of Napari, where the selected points did not correspond at all to the drawn selection rectangle.
This is due to Napari version 0.4.19, we strongly recommend to avoid this version.

### Acces violation reading


`OSError: exception: access violation reading 0x0000000000000034`.

This error happened only in Windows with specific nvidia card (A6000).
It happens when adding or deleting Shape layers, quite often in `cytoplasmic measure` option.
It seems to be an error external to the plugin or napari. 
We haven't found a solution yet, but please refer to [this discussion](https://forum.image.sc/t/napari-crash-problem-with-opengl-and-or-vispy-and-or-nvidia-and-or-windows/113859) on imagesc forum for more infos/updates.

### Other issue

You can also check on the [issues](https://github.com/gletort/FishFeats/issues) page of the repository if your problem has already been reported and has a solution. 
Otherwise, open a new one in this page and we will do our best to answer fast.


## Tested and working configurations

Here we proposed the list of versions that worked fine for us. For some versions, we provide the full list of package versions that were installed on several python environment, with the corresponding operating system, that worked fine for us.

For each set-up, we list first the graphical info that we get with `napari --info`, then the link to the full yaml file.

Note that `Epyseg` cannot be install on python versions above 3.10. 
Thus, to use the full pipeline with all options, we recommend python 3.10. 
However, if you don't intend to use Epyseg or use it separatly, the pipeline and the other dependencies are compatible with more recent python versions.

???+ example "Environment lists"

	=== "Windows"

		<details><summary> Windows 10, python 3.9.21, napari 0.4.18 </summary>

			fishfeats: 1.1.11				
			napari: 0.4.18
			Platform: Windows-10-10.0.19045-SP0
			Python: 3.9.21 | packaged by conda-forge | [MSC v.1929 64 bit (AMD64)]
			Qt: 5.15.2
			PyQt5: 5.15.11
			NumPy: 1.26.4
			SciPy: 1.13.1
			Dask: 2024.8.0
			VisPy: 0.12.2
			magicgui: 0.9.1
			superqt: 0.6.7
			in-n-out: 0.2.1
			app-model: 0.2.8
			npe2: 0.7.7

			OpenGL:
				 - GL version:  4.6.0 NVIDIA 571.59
				 - MAX_TEXTURE_SIZE: 32768 

		yaml file with all python packages installed in the environment [here](./environnements_list/windows10_fishfeats1.1.11_py39.yaml)
		</details>	
		
		<details><summary> Windows 10, python 3.10.18, napari 0.6.1 </summary>
			
			napari: 0.6.1
			Platform: Windows-10-10.0.19045-SP0
			Python: 3.10.18 | packaged by conda-forge | MSC v.1943 64 bit (AMD64)
			Qt: 5.15.2
			PyQt5: 5.15.11
			NumPy: 1.26.4
			SciPy: 1.15.3
			Dask: 2025.5.1
			VisPy: 0.15.2
			magicgui: 0.10.1
			superqt: 0.7.5
			in-n-out: 0.2.1
			app-model: 0.3.2
			psygnal: 0.13.0
			npe2: 0.7.8
			pydantic: 2.11.7

			OpenGL:
				 - PyOpenGL: 3.1.9
				 - GL version:  4.6.0 NVIDIA 571.59
				 - MAX_TEXTURE_SIZE: 32768
				 - GL_MAX_3D_TEXTURE_SIZE: 16384
			
			Optional:
				  - numba: 0.61.2
				  - triangle: 20250106
				  - napari-plugin-manager: 0.1.6
				  - bermuda: 0.1.4
				  - PartSegCore not installed

			Experimental Settings:
				  - Async: False
				  - Autoswap buffers: False
				  - Triangulation backend: Fastest available


			fishfeats: 1.1.11				
		
		yaml file with all python packages installed in the environment [here](./environnements_list/windows10_fishfeats_1.1.11_py310.yaml)
		</details>	
	

	=== "MacOS"
		
		<details><summary> MacBook pro M1, python 3.10.14, napari 0.4.19 </summary>

			napari: 0.4.19
			Platform: macOS-15.5-arm64-arm-64bit
			System: MacOS 15.5
			Python: 3.10.14 | packaged by conda-forge | (main, Mar 20 2024, 12:51:49) [Clang 16.0.6 ]
			Qt: 5.15.8
			PyQt5: 5.15.9
			NumPy: 1.26.4
			SciPy: 1.13.1
			Dask: 2025.5.1
			VisPy: 0.14.3
			magicgui: 0.10.1
			superqt: 0.7.5
			in-n-out: 0.2.1
			app-model: 0.2.8
			npe2: 0.7.8

			OpenGL:
			GL version:    2.1 Metal - 89.4
			MAX_TEXTURE_SIZE: 16384
			
			fishfeats: 1.1.11				
		yaml file with all python packages installed in the environment [here](./environnements_list/macbook_pro_M1_fishfeats_1.1_py310.yaml)
		</details>	
		
		<details><summary> MacBook pro M1, python 3.10.14, napari 0.5.5 </summary>
		</details>	
		
		<details><summary> MacBook pro M1, python 3.10.14, napari 0.6.2 </summary>
		</details>	

	=== "Linux"
		
		<details><summary> Ubuntu 20.04.6, python 3.10.0, napari 0.6.1 </summary>

			napari: 0.6.1
			Platform: Linux-5.15.0-139-generic-x86_64-with-glibc2.31
			System: Ubuntu 20.04.6 LTS
			Python: 3.10.0 | packaged by conda-forge | (default, Nov 20 2021, 02:24:10) [GCC 9.4.0]
			Qt: 5.15.2
			PySide2: 5.15.2.1
			NumPy: 1.24.2
			SciPy: 1.15.3
			Dask: 2025.5.1
			VisPy: 0.15.2
			magicgui: 0.10.0
			superqt: 0.7.3
			in-n-out: 0.2.1
			app-model: 0.3.1
			psygnal: 0.13.0
			npe2: 0.7.8
			pydantic: 2.11.5

			OpenGL:
				- PyOpenGL: 3.1.9
				- GL version:  4.6.0 NVIDIA 545.29.06
				- MAX_TEXTURE_SIZE: 32768
				- GL_MAX_3D_TEXTURE_SIZE: 16384


			Optional:
			- numba: 0.61.2
			- triangle not installed
			- napari-plugin-manager not installed
			- bermuda not installed
			- PartSegCore not installed

			Experimental Settings:
			- Async: False
			- Autoswap buffers: False
			- Triangulation backend: Fastest available

			fishfeats: 1.1.3
		yaml file with all python packages installed in the environment [here](./environnements_list/ubuntu_20.04_fishfeats_1.1_py310.yaml)
		</details>
	
		<details><summary> Ubuntu 20.04.6, python 3.11, napari 0.6.2 - No EPYSEG </summary>
			
			napari: 0.6.2
			Platform: Linux-5.15.0-139-generic-x86_64-with-glibc2.31
			System: Ubuntu 20.04.6 LTS
			Python: 3.11.13 | packaged by conda-forge | (main, Jun  4 2025, 14:48:23) [GCC 13.3.0]
			Qt: 5.15.14
			PyQt5: 5.15.11
			NumPy: 1.26.0
			SciPy: 1.16.0
			Dask: 2025.7.0
			VisPy: 0.15.2
			magicgui: 0.10.1
			superqt: 0.7.5
			in-n-out: 0.2.1
			app-model: 0.4.0
			psygnal: 0.14.0
			npe2: 0.7.9
			pydantic: 2.11.7

			OpenGL:
				- PyOpenGL: 3.1.9
				- GL version:  4.6.0 NVIDIA 545.29.06
				- MAX_TEXTURE_SIZE: 32768
				- GL_MAX_3D_TEXTURE_SIZE: 16384

			Optional:
			 - numba: 0.61.2
			 - triangle not installed
			 - napari-plugin-manager not installed
			 - bermuda not installed
			 - PartSegCore not installed

			Experimental Settings:
			  - Async: False
			  - Autoswap buffers: False
			  - Triangulation backend: Fastest available

			fishfeats: 1.1.15 
		yaml file with all python packages installed in the environment [here](./environnements_list/ubuntu20.04_fishfeats1.1_py3.11.yaml)

		</details>	
		
		<details><summary> Ubuntu 20.04.6, python 3.9, napari 0.4.19 </summary>
			
			napari: 0.4.19
			Platform: Linux-5.15.0-139-generic-x86_64-with-glibc2.31
			System: Ubuntu 20.04.6 LTS
			Python: 3.9.19 | packaged by conda-forge | (main, Mar 20 2024, 12:50:21) [GCC 12.3.0]
			Qt: 5.15.2
			PySide2: 5.15.2.1
			NumPy: 1.24.3
			SciPy: 1.13.0
			Dask: 2024.8.0
			VisPy: 0.14.3
			magicgui: 0.10.0
			superqt: 0.7.3
			in-n-out: 0.2.1
			app-model: 0.2.8
			npe2: 0.7.8

			OpenGL:
			- GL version: 4.6.0 NVIDIA 545.29.06
			- MAX_TEXTURE_SIZE: 32768

			fishfeats: 1.1.31
		yaml file with all python packages installed in the environment [here](./environnements_list/ubuntu20.04_fishfeats1.1_py39.yaml)
		</details>	
