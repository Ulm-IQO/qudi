# Installation        {#installation}

## Quick Start

1. Get a Python 3 version of the conda package manager (eg Anaconda, miniconda, etc).
2. Clone https://github.com/Ulm-IQO/qudi.git
3. Install the qudi conda environment suitable for your operating system (located in the `tools` directory of the qudi code).
4. Run `start.py` in this conda environment.

See below for more specific instructions.

## Windows

1. Get Git for Windows from https://git-for-windows.github.io/ 
and TortoiseGIT from https://tortoisegit.org/ and install it.

2. Get the Anaconda Python 3.x distribution from https://www.continuum.io/downloads .
Choose Install for all users and register Python in the system.

3. Get PyCharm from https://www.jetbrains.com/pycharm/download and install it.

4. Do a git clone of https://github.com/Ulm-IQO/qudi.git

5. In the checked out folder, go to the `tools` folder and execute the `install-python-modules-windows.bat` file.

6. Open the checked out folder in PyCharm and configure the project interpreter to be `C:\Anaconda3\envs\qudi\python.exe`.

7. Configuring the project interpreter is described on this site:
https://www.jetbrains.com/pycharm/help/configuring-python-interpreter-for-a-project.html .

8. Now you can open `start.py` in the PyCharm project and execute it by right clicking the file tab and choosing execute.

## Linux

1. Install git using system package manager.

2. Do `git clone https://github.com/Ulm-IQO/qudi.git` .

3. Install a conda package manager.  [Miniconda](https://conda.io/miniconda.html) is nice and easy.

4. Install the qudi conda environment from `tools/conda-env-linx64-qt5.yml` .

5. Activate the qudi conda environment.

6. Change to the qudi code directory and run start.py using `./start.py` or `python3 start.py` or similar.
