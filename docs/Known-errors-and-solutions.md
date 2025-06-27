## Encountered errors and solutions:

### Module versions

* `skimage.morphology.selem` module not found error => Problem of compatibility between big-fish and scikit-image versions. Ideally, chooses a recent version of skimage (scikit-image==0.19.3) and big-fish (big-fish==0.6.2).
* 

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

Here we proposed the list of package versions that were installed on several python environment, with the corresponding operating system, that worked fine for us.

For each set-up, we list first the graphical info that we get with `napari --info`, then the link to the full yaml file.

???+ example "Environment lists"

	=== "Windows"

		<details><summary> Windows 10, python 3.9.21 </summary>

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

		yaml file with all python packages installed in the environment [here](./environnements_list/windows10_fishfeats_1.1.11_py39.yaml)
		</details>	
		
		<details><summary> Windows 10, python 3.10.18 </summary>
			
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

	=== "Linux"
