# Fish&Feats ![snap](./docs/imgs/snap.png)

[![License BSD-3](https://img.shields.io/pypi/l/fishfeats.svg?color=green)](https://github.com/gletort/FishFeats/-/blob/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/fishfeats.svg?color=green)](https://pypi.org/project/fishfeats)
[![Python Version](https://img.shields.io/pypi/pyversions/fishfeats.svg?color=green)](https://python.org)

[Napari](https://napari.org/stable/) plugin to quantify 3D cells in a tissue and their smRNA-Fish or other RNA contents.

[main.webm](https://github.com/user-attachments/assets/7eda5fa8-3241-4af8-b392-bc3e64aa31b9)


FishFeats offers several flexible options to analyse 3D cells and RNA counts, from segmentation of apical cells and nuclei to hierarchical clustering of cells based on their RNA contents. 
Installation/Usage are all described in the [documentation](https://gletort.github.io/FishFeats/).

![main interface](./docs/imgs/Main_snapshot.png)

## Installation

Please refer to our [documentation page](https://gletort.github.io/FishFeats/Installation/) for more details on the installation.

`FishFeats` is distributed as a pip module on pypi.
It can be installed by typing in a python virtual environement:
```
pip install fishfeats
``` 

Some options of `Fishfeats` rely on dependencies that are not required by default, so to not force a lot of dependencies installation.
If you want to do directly the installation with **all dependencies**, type:
``` 
pip install `fishfeats[full]`
```

## Usage

You can launch `fishfeats` in Napari by going to `Plugins>fishfeats>Start`.
It will open a file dialog box asking you to select the image that you want to analyze. 
Refer to the [documentation](https://gletort.github.io/FishFeats/) for presentation of the different steps possible in the pipeline.


## License

Fishfeats is distributed freely under the BSD-3 license.


[napari]: https://github.com/napari/napari
[BSD-3]: http://opensource.org/licenses/BSD-3-Clause
[tox]: https://tox.readthedocs.io/en/latest/
[pip]: https://pypi.org/project/pip/
[PyPI]: https://pypi.org/
