# Required Packages  {#required-python-packages}

# Do not use this list to install Qudi for normal use. Check the Installation page to see how to do that.
[Installation page with full install instructions](@ref installation)

These package have to be installed in order to run Qudi (easily installed with Anaconda console: pip install "packagename"):

| Package  | Minimum Version | URL  | Needed by |
| ------------- | ---------- | ------------------------------------------- | ----------- |
| Fysom         | 2.1        | https://pypi.python.org/pypi/fysom          | all         |
| qtpy          | 1.1.2      | https://pypi.python.org/pypi/qtpy           | all         |
| RPyC          | 3.3.0      | https://pypi.python.org/pypi/rpyc           | all         |
| ruamel.yaml   | 0.11       | https://pypi.python.org/pypi/ruamel.yaml    | all         |
| pyqtgraph     | 0.10.0     | http://www.pyqtgraph.org/                   | Lots        |
| pyvisa        | 1.8        | https://pypi.python.org/pypi/PyVISA         | Lots        |
| lmfit         | 0.9.2      | https://pypi.python.org/pypi/lmfit/         | fitlogic    |
| jupyter       | 1.0.0      | https://pypi.python.org/pypi/jupyter        | Manager gui, Notebook features|
| git           | 2.0.0      | https://pypi.python.org/pypi/GitPython      | Manager GUI |
| PyDAQmx       | 1.3.2      | https://pypi.python.org/pypi/PyDAQmx        | NI card     |
| hdf5storage   | ???        | https://pypi.python.org/pypi/hdf5storage    | awg70k      |
| comtypes      | 1.1        | https://pypi.python.org/pypi/comtypes       | winspec_spectrometer (hardware) |
| pythonnet     | 2.1.0.dev1 | https://pypi.python.org/pypi/pythonnet      | lightfield_spectrometer |
| pillow        | 4.0.0      | https://python-pillow.org/                  | Save-Logic for Metadata |

# How to install additional packages

Additional packages can be installed either via `conda` or via `pip` from command line (you might need admin rights).

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

