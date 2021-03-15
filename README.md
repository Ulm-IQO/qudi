# qudi
Qudi is a suite of tools for operating multi-instrument and multi-computer laboratory experiments.
Originally built around a confocal fluorescence microscope experiments, it has grown to be a generally applicaple framework for controlling experiments.

## Installation of new core
First create a new environment with python 3.7 you want you core to live in and change into this environment. This can be done with the help of conda:
```bash
conda create -n qudicore python=3.7
conda activate qudicore
```

Create a new folder for the code to live in and change into it.
```bash
mkdir "C:\Software\qudicore"
cd "C:\Software\qudicore"
```

Install the qudi package in the right environment and folder (see above) using pip. This also installs a qudi-kernel for jupyter notebooks (be careful, this might overright an already existing qudi-kernel).
```bash
python -m pip install -e git+https://github.com/Ulm-IQO/qudi@core_pyside2#egg=qudi
```

Run your new qudi by just calling:
```bash
qudi
```

## Citation
If you are publishing scientific results, mentioning Qudi in your methods decscription is the least you can do as good scientific practice.
You should cite our paper [Qudi: A modular python suite for experiment control and data processing](http://doi.org/10.1016/j.softx.2017.02.001) for this purpose.

## Documentation
User and code documentation about Qudi is located at http://ulm-iqo.github.io/qudi-generated-docs/html-docs/ .

## Continuous integration 
[![Build Status](https://travis-ci.org/Ulm-IQO/qudi.svg?branch=master)](https://travis-ci.org/Ulm-IQO/qudi)
[![Build status](https://ci.appveyor.com/api/projects/status/ma1a125b31cbl6tu/branch/master?svg=true)](https://ci.appveyor.com/project/InstituteforQuantumOptics/qudi/branch/master)
[![Scrutinizer Code Quality](https://scrutinizer-ci.com/g/Ulm-IQO/qudi/badges/quality-score.png?b=master)](https://scrutinizer-ci.com/g/Ulm-IQO/qudi/?branch=master)

## Collaboration
For development-related questions and discussion, please use the [qudi-dev mailing list](http://www.freelists.org/list/qudi-dev).

If you just want updates about releases and breaking changes to Qudi without discussion or issue reports,
subscribe to the [qudi-announce mailing list](http://www.freelists.org/list/qudi-announce).

Feel free to add issues and pull requests for improvements on github at https://github.com/Ulm-IQO/qudi .

The code in pull requests should be clean, PEP8-compliant and commented, as with every academic institution in Germany,
our resources in the area of software development are quite limited.

Do not expect help, debugging efforts or other support.

## License
Almost all parts of Qudi are licensed under GPLv3 (see LICENSE.txt) with the exception of some files
that originate from the Jupyter/IPython project.
These are under BSD license, check the file headers and the documentation folder.

Check COPYRIGHT.txt for a list of authors and the git history for their individual contributions.
