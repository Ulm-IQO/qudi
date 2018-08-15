# Manual installation of a python environment with conda for Qudi {#manual-package-installation}

This section will provide you with information to establish a python environment
in order to develop qudi.

# Do not use the following installtion quide, if you want to install Qudi for normal use. Check the Installation page to see how to do that.
[Installation page with full install instructions](@ref installation)

# How to install packages in python

Additional packages can be installed either via `conda` or via `pip` from 
command line (you might need admin rights).

Try at first to use the `conda` package manager (which comes together with the
Anaconda distribution):

    conda install <modulename>

That is the most elegant way, since `conda` will handle all cross dependencies
with other packages, will download all needed packages for that module and will
try to resolve appearing issues. If `<modulename>` is not in the repository list
of Anaconda, you can try to install the module via pip, the internal package
manager for python:

    pip install <modulename>

Note that pip will not look for cross dependencies but just simply install and
expand the desired package.


## Pre-requisition 

It is assumed, that  you have already selected the a conda environment, for 
which the package installation will be performed. All the listed commands are 
executed in the terminal or cmd (for windows) with administrator privileges (!).

For more information concerning the conda environment see: 
https://conda.io/docs/user-guide/tasks/manage-environments.html

By default, if anaconda is installed on your machine, the installation will 
happen in the environment "base". In order to create a separate environment with 
the name "qudi" perform

    conda create -n qudi python=3.6

You can choose also a different name than 'qudi' for the environment (and the 
desired python version), but you have to replace then 'qudi' by your custom name 
in the following process.


## Conda package installation

You can install each package separately

    conda install -n qudi cycler
    conda install -n qudi cython
    conda install -n qudi ipython
    conda install -n qudi jupyter
    conda install -n qudi lxml
    conda install -n qudi matplotlib
    conda install -n qudi numpy
    conda install -n qudi pillow

or all bundled all in one command:

    conda install -n qudi cycler cython ipython jupyter lxml matplotlib numpy pillow

Those are the packages, which are precompiled and/or distributed from the 
Anaconda package index via the conda package tool. Note that all related 
packages (e.g. pyqt and qt bindings,...) will be automatically installed during
this procedure.

## Pip package installation

Pip will install now specific packages, which are required for qudi.
Before you perform the installation with the internal package manager, you have 
to activate the "qudi" environment. In the CMD perform

    activate qudi

For linux users, the command would be

    source activate qudi

Now you can perform either an installation of each package

    pip install asteval
    pip install fysom
    pip install gitpython    
    pip install lmfit
    pip install pydaqmx
    pip install pyflowgraph-qo
    pip install pyqtgraph-qo 
    pip install pyvisa
    pip install rpyc
    pip install ruamel.yaml
    pip install serial
    pip install typing

or install all in one run

    pip install asteval fysom gitpython lmfit pydaqmx pyflowgraph-qo pyqtgraph-qo pyvisa rpyc ruamel.yaml serial typing


This should install the correct environment for qudi.


## Extract current environment to file

If you want to extract the current conda environment 'qudi' to file, just perform

    conda-env export -n qudi > my-env.yml
    
Note that in the file 'my-env.yml', there will be at the bottom the section 
'prefix', which identifies the path to the conda environment. Make sure to 
delete the section 'prefix', if you want to use this file to install the 'qudi' 
environment elsewhere, to prevent confusions about the location of the 
conda environment. Then, in the installation procedure, the default location of 
the conda environment will be taken, which can be different on every machine.

## Install conda environment from file

If you have a conda environment file 'my-env.yml' present, you can use that to 
create manually the conda environment. All the required information should be 
written in the file 'my-env.yml'.

    conda env create -f my-env.yml

## Remove environment

If you want to remove the environment with the name 'qudi', just perform

    conda-env remove --yes --name qudi
