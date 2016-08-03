# -*- coding: utf-8 -*-
"""
QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>

Distributed under the MIT license, see documentation/MITLicense.md.
PyQtGraph - Scientific Graphics and GUI Library for Python
www.pyqtgraph.org
Copyright:
  2012  University of North Carolina at Chapel Hill
        Luke Campagnola    <luke.campagnola@gmail.com>
"""

import os, sys
import atexit
import pyqtgraph

## Optional function for exiting immediately (with some manual teardown)
def exit(exitcode=0):
    """
    Causes python to exit without garbage-collecting any objects, and thus avoids
    calling object destructor methods. This is a sledgehammer workaround for 
    a variety of bugs in PyQt and Pyside that cause crashes on exit.
    
    This function does the following in an attempt to 'safely' terminate
    the process:
    
    * Invoke atexit callbacks
    * Close all open file handles
    * os._exit()
    
    Note: there is some potential for causing damage with this function if you
    are using objects that _require_ their destructors to be called (for example,
    to properly terminate log files, disconnect from devices, etc). Situations
    like this are probably quite rare, but use at your own risk.

    @param int exitcode: system exit code
    """
    
    ## first disable our own cleanup function; won't be needing it.
    pyqtgraph.setConfigOptions(exitCleanup=False)
    
    ## invoke atexit callbacks
    atexit._run_exitfuncs()
    
    ## close file handles
    if sys.platform == 'darwin':
        for fd in xrange(3, 4096):
            if fd not in [7]:  # trying to close 7 produces an illegal instruction on the Mac.
                os.close(fd)
    else:
        os.closerange(3, 4096) ## just guessing on the maximum descriptor count..

    os._exit(exitcode)
