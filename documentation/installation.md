# Installation        {#installation}

## Windows

Get Git for Windows from https://git-for-windows.github.io/ 
and TortoiseGIT from https://tortoisegit.org/ and install it.

Get the Anaconda Python 3.x distribution from https://www.continuum.io/downloads .
Choose Install for all users and register Python in the system.

Get PyCharm from https://www.jetbrains.com/pycharm/download and install it.

Do a git clone of https://github.com/Ulm-IQO/qudi.git

In the checked out folder, go to the `tools` folder and execute the `install-python-modules-windows.bat` file.

Open the checked out folder in PyCharm and configure the project interpreter to be `C:\Anaconda3\envs\qudi\python.exe`.

Configuring the project interpreter is described on this site:
https://www.jetbrains.com/pycharm/help/configuring-python-interpreter-for-a-project.html .

Now you can open `start.py` in the PyCharm project and execute it by right clicking the file tab and choosing execute.

## Linux (Debian-based)

Install subversion, do `git clone https://github.com/Ulm-IQO/qudi.git` .

Install all packages listed in the file `tools/debian-jessie-packages.txt`.

Install all Python packages listed in the file `tools/debian-jessie-pip.txt` with pip3.

You should now be able to run `python3 start.py` in the qudi folder.

## PyDAQmx fix

PyDAQMX does not need to be fixed anymore since version 1.3.2 .


