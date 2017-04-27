# -*- coding: utf-8 -*-
"""
Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>

Distributed under the MIT license, see documentation/MITLicense.md.
PyQtGraph - Scientific Graphics and GUI Library for Python
www.pyqtgraph.org
Copyright:
  2012  University of North Carolina at Chapel Hill
        Luke Campagnola    <luke.campagnola@gmail.com>
"""

import os
import sys
import atexit
has_pyqtgraph = False
try:
    import pyqtgraph
    has_pyqtgraph = True
except ImportError:
    pass

import importlib
import logging
logger = logging.getLogger(__name__)

# Optional function for exiting immediately (with some manual teardown)


def exit(exitcode=0):
    """
    Causes python to exit without garbage-collecting any objects, and thus
    avoids calling object destructor methods. This is a sledgehammer
    workaround for a variety of bugs in PyQt and Pyside that cause crashes
    on exit.

    This function does the following in an attempt to 'safely' terminate
    the process:

    * Invoke atexit callbacks
    * Close all open file handles
    * os._exit()

    Note: there is some potential for causing damage with this function if you
    are using objects that _require_ their destructors to be called (for
    example, to properly terminate log files, disconnect from devices, etc).
    Situations like this are probably quite rare, but use at your own risk.

    @param int exitcode: system exit code
    """

    if has_pyqtgraph:
        # first disable our pyqtgraph's cleanup function; won't be needing it.
        pyqtgraph.setConfigOptions(exitCleanup=False)

    # invoke atexit callbacks
    atexit._run_exitfuncs()

    # close file handles
    if sys.platform == 'darwin':
        for fd in range(3, 4096):
            # trying to close 7 produces an illegal instruction on the Mac.
            if fd not in [7]:
                os.close(fd)
    else:
        # just guessing on the maximum descriptor count..
        os.closerange(3, 4096)

    os._exit(exitcode)



def import_check():
    """ Checks whether all the necessary modules are present upon start of qudi.
    
    @return: int, error code either 0 or 4.
    
    Check also whether some recommended packages exists. Return err_code=0 if
    all vital packages are installed and err_code=4 if vital packages are
    missing. Make a warning about missing packages.
    """
    err_code = 0

    # encode like: (python-package-name, repository-name)
    vital_pkg = [('ruamel.yaml','ruamel.yaml'), ('rpyc','rpyc'), ('fysom','fysom')]
    opt_pkg = [('pyqtgraph','pyqtgraph'), ('git','gitpython')]

    for pkg_name, repo_name in vital_pkg:
        try:
            importlib.import_module(pkg_name)
        except ImportError:
            logger.error('No Package "{0}" installed! Perform e.g.\n\n'
                         '    pip install {1}\n\n'
                         'in the console to install the missing package.'.format(pkg_name, repo_name))
            err_code = err_code | 4

    try:
        from qtpy.QtCore import Qt
    except ImportError:
        logger.error('No Qt bindungs detected! Perform e.g.\n\n'
                     '    pip install PyQt5\n\n'
                     'in the console to install the missing package.')
        err_code = err_code | 4

    for pkg_name, repo_name in opt_pkg:
        try:
            importlib.import_module(pkg_name)
        except ImportError:
            logger.warning('No Package "{0}" installed! It is recommended to '
                           'have this package installed. Perform e.g.\n\n'
                           '    pip install {1}\n\n'
                           'in the console to install the missing package.'.format(pkg_name, repo_name))

    return err_code
