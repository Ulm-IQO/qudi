# Installation        {#installation}

## Quick Start

1. Get a Python 3 version of the conda package manager (eg Anaconda, miniconda, etc).
2. Clone https://github.com/Ulm-IQO/qudi.git
3. Install the qudi conda environment suitable for your operating system (located in the `tools` directory of the qudi code).
4. Run `start.py` in this conda environment.

See below for more specific instructions.

## The options

#### Anaconda vs Manual
Qudi is a Python 3 program that need some modules to work. In order to use Python version 3 and theses
dependencies, Qudi might be used with [Anaconda](https://en.wikipedia.org/wiki/Anaconda_(Python_distribution)),
 a free open source tool that let your computer have multiples "environments"
installed at the same time, and just switch from one to another in a command terminal.

This tool also ease the installation as you can create an environment for Qudi with all the modules needed by importing 
them from the ``.yml`` file in the ``tool`` folder.

It is highly recommended you use this option. If however you want to go mannual, you can find more information 
[here](@ref required_python_packages)

#### Git vs Download

If you just want to run Qudi as is, you can download the source code from GitHub and use this installation guide to run
it.

However, Qudi is in constant development for new features and bug fixes, so it is highly recommended to use Git,
even for production environment.

[Git](https://en.wikipedia.org/wiki/Git) is a very popular free and open source version control system that let developers track changes
in the source code and keep things organized. It is also a tool that can let you set up and update your production 
environment easily. GitHub, the website that host the Git repository is an tool built on top of Git to add some 
capabilities and a more user friendly interface.

#### PyCharm vs others

PyCharm is a 
[integrated development environment (IDE)](https://en.wikipedia.org/wiki/Integrated_development_environment)
built for Python. It has a Community Edition that is free and open source.

PyCharm is a very good code editor for Python that will help you dive into the code and modify it efficiently.
It is compatible with Anaconda environments to detect available modules.
It is great for wringing documentation as it has an real time rendering  tool.

If you intend to use Qudi, it is recommended to setup Pycharm on your machine.

## Windows installation

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

#### Desktop shortcut

You can create a Desktop shortcut to launch Qudi easily on your machine.

- On your Desktop, right click and go to ``New->Shortcut``
- For the location you need to copy the following target :
    - %windir%\System32\cmd.exe "/K" C:\ProgramData\Miniconda3\Scripts\activate.bat
    "C:\Users\username\Miniconda3\envs\qudi" &#65120;&#65120; python "start.py"
        - The &#65120; might cause troube when copy/pasting, you might need to add it by hand
        - ``C:\ProgramData\Miniconda3\Scripts\activate.bat`` is the Anaconda activation file, it might be in another
        location depending on your installation
        - ``C:\Users\username\Miniconda3\envs\qudi`` is the environment folder for Qudi. You can find it by typing
        ``conda info`` in the terminal while qudi is activated
- Click ``Next``
- Give the name you want fot the shortcut : ``Qudi``
- Click ``Finish``
- Right click on the newly created shortcut and go to `Proprerties`
- In the ``Start in :`` line, write the path to to Qudi folder where the ``start.py`` can be found
- (Optionally) Click ``Change Icon...`` and browse for the ``artwork\logo\logo_qudi.ico`` logo


## Linux installation

1. Install git using system package manager.

2. Do `git clone https://github.com/Ulm-IQO/qudi.git` .

3. Install a conda package manager.  [Miniconda](https://conda.io/miniconda.html) is nice and easy.

4. Install the qudi conda environment from `tools/conda-env-linx64-qt5.yml` .

5. Activate the qudi conda environment.

6. Change to the qudi code directory and run start.py using `./start.py` or `python3 start.py` or similar.
