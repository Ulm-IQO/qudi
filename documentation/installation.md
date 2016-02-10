Installation			{#installation}
============
Windows
-------
Get TortoiseSVN from https://tortoisesvn.net/downloads.html and install it.
Pay attention to install the command line tools.

Get the Anaconda Python 3.5 distribution from https://www.continuum.io/downloads .
Choose Install for all users and register Python in the system.

Get PyCharm from https://www.jetbrains.com/pycharm/download and install it.

Do an SVN checkout of QuDi from https://qosvn2.physik.uni-ulm.de/svn/qudi/trunk

In the checked out folder, go to the `tools` folder and execute the `install-python-modules-windows.bat` file.

Open the checked out folder in PyCharm and configure the project interpreter to be `C:\Anaconda3\envs\qudi\python.exe`.

Configuring the project interpreter is described on this site: https://www.jetbrains.com/pycharm/help/configuring-python-interpreter-for-a-project.html .

Now you can open `start.py` in the PyCharm project and execute it by right clicking the file tab and choosing execute.

Linux (Debian-based)
--------------------

Install subversion, do `svn co https://qosvn2.physik.uni-ulm.de/svn/qudi/trunk qudi` .

Install all packages listed in the file `tools/debian-jessie-packages.txt`.

Install all Python packages listed in the file `tools/debian-jessie-pip.txt` with pip3.

You should now be able to run `python3 start.py` in the qudi folder.

PyDAQmx fix
-----------
PyDAQMX does not need to be fixed anymore since version 1.3.2 .


