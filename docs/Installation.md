# Installation

[**Standard installation**](#standard-installation): You can install Napari and `FishFeats` by creating/using a python virtual environment (**recommended**).

[**Easier installation**](#easier-installation): If you have no python virtual environment experience and want to avoid it, you can install Napari through the "bundle" distribution. 
The bundles come with an installer program for Windows and MacOS systemso this allow for an easy installation (everything will be done through graphical interfaces), but allows for less control/flexibility. 

## Standard installation
### From Napari interface
FishFeats is a Napari plugin, in python. You can install it either through an already installed Napari instance by going in Napari to `Plugins>Install/Uninstall`, search for `FishFeats` and click `Install`.
You could have version issues between the different modules installed in your environment and FishFeats dependencies, in this case it is recommended to create a new virtual environnement specific for FishFeats.

### From virtual environnement
To install FishFeats, you should create a new virtual environnement or activate an exisiting compatible one.

#### Create a new virtual environement
 You can create a virtual environement [with venv](https://www.geeksforgeeks.org/create-virtual-environment-using-venv-python/) or anaconda (you may need to install anaconda, see here: [on windows](https://www.geeksforgeeks.org/how-to-install-anaconda-on-windows/), [on macOS](https://www.geeksforgeeks.org/installation-guide/how-to-install-anaconda-on-macos/?ref=ml_lbp) or [on linux](https://www.geeksforgeeks.org/how-to-install-anaconda-on-linux/) ). 

Then use the Anaconda interface to create a new virtual environement with the desired python version, or [through the Terminal](https://www.geeksforgeeks.org/set-up-virtual-environment-for-python-using-anaconda/).

For example, in a terminal, once conda is installed, you can create a new environnement by typing:
```
conda create -n fishfeats_env python=3.10
```

#### Install FishFeats
Once you have created/identified a virtual environnement, type in the terminal:
``` 
conda activate fishfeats_env
```
to activate it (and start working in that environnement).

Type in the activated environnement window:

```
pip install fishfeats
```
to install FishFeats.

!!! warning "Installation of dependencies"
	As the plugin relies on several different python modules and for flexibilit, we don't enforce the install of **all dependencies** on the basic installation of FishFeats.
	It is up to the user to install the extra dependencies that will be usefull for her/his project.
	However, it is possible to install directly most of the main dependencies by installing `fishfeats` with the `full` option: ```pip install `fishfeats[full]` ```, or ```pip install fishfeats[full]``` depending on the operating system.


#### Update FishFeats

To get the latest version of FishFeats when it is updated, type
``` 
pip install -U fishfeats
```
in your activated environment. 
If FishFeats was updated since you last installed/updated it, the latest version will be downloaded.

#### Start FishFeats

Open Napari by typing
```
napari
```
in the activated environnement and goes to `Plugins>FishFeats>Start fishfeats`

## Compatibility/Dependencies

`FishFeats` depends on several python modules to allow different tasks. It is not necessary to install all the dependencies to run it, only the ones listed in `setup.cfg` configuration file. When installing the plugin, the listed dependencies will be automatically installed. 

Other dependencies can be installed individually if the corresponding option will be used (e.g. install cellpose: `pip install cellpose`).
They can also be all installed by installing FishFeats in full mode `pip install `fishfeats[full]` `.

### Operating System
The plugin has been developped on a Linux environment and is used on Windows and MacOS distributions. It should thus be compatible with all these OS provided to have the adequate python environments.

??? warning "Windows GPU card nvidia A6000"
	We encountered an unsolved yet error only on Windows with some specific nvidia drivers/GPU card. During plugin usage, it returns this error:`OSError: exception: access violation reading 0x0000000000000034`. See [here](Known-errors-and-solutions.md/#Access-violation-reading) for more infos.


### Python version
We tested the plugin with python 3.9, 3.10, 3.11 with Napari 0.4.19, 0.6.1. 
In [Trouble shooting](Known-errors-and-solutions.md), we listed some environnement that worked for given operating system/python version. 
You can also create your environment directly from these `.yaml` files.

There is an incompability with Napari 0.4.17 (strongly not recommended) for point edition in 3D.

Please refers to [Trouble shooting](Known-errors-and-solutions.md) if you encounter issues at the installation/usage or to the repository issues. Finally if you don't find any information on your error, open a [new issue](https://github.com/gletort/FishFeats/issues) in this repository.

### Full working configuration

We listed examples of fully working configuration in `Windows`, `MacOS` and `Ubuntu` operating systems in the [Trouble shooting](Known-errors-and-solutions.md#tested-and-working-configurations) page.
You can compare the version of the dependencies to the ones in your environment in case of issue.

## Easier installation

Download the bundle version of Napari 0.5.4:

* [Linux version](https://github.com/napari/napari/releases/download/v0.5.4/napari-0.5.4-Linux-x86_64.sh)
* [MacOS arm64](https://github.com/napari/napari/releases/download/v0.5.4/napari-0.5.4-macOS-arm64.pkg)
* [MacOS x86](https://github.com/napari/napari/releases/download/v0.5.4/napari-0.5.4-macOS-x86_64.pkg)
* [Windows x86](https://github.com/napari/napari/releases/download/v0.5.4/napari-0.5.4-Windows-x86_64.exe)

All these bundle come from Napari github, [release of version 0.5.4](https://github.com/napari/napari/releases/tag/v0.5.4). 
The installation steps for each OS are described [here](https://napari.org/stable/tutorials/fundamentals/installation_bundle_conda.html).


??? note "Why Napari version 0.5.4" 
	We chose this version as it is the last one in python 3.9, the following ones are with python > 3.11, to have all FishFeats options available (including epyseg which is limited to version <3.11).
	You can still download the latest bundle of Napari if you wish, and then use the Napari console Terminal to fix dependencies install, or not use some options (epyseg, and eventually stardist and SepaNet which are based on tensorflow).