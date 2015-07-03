# -*- coding: utf-8 -*-
"""
This file contains the QuDi Manager class.

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

Copyright (C) 2015 Jan M. Binder jan.binder@uni-ulm.de

Derived form ACQ4:
Copyright 2010  Luke Campagnola
Originally distributed under MIT/X11 license. See documentation/MITLicense.txt for more infomation.
"""

__version__ = '0.1'

import os
import sys

# If we are using PyQt, ACQ4 requires API version 2 for QString and QVariant. 
# Check for those here..
set_api = True
if 'PyQt4' in sys.modules:
    import sip
    for api in ['QString', 'QVariant']:
        try:
            v = sip.getapi(api)
            if v != 2:
                raise Exception("We require the usage of API version 2 for "
                                "QString and QVariant, but {0}={1}. "
                                "Correct this by calling\n\n import sip;\n "
                                "sip.setapi('QString', 2);\n "
                                "sip.setapi('QVariant', 2);\n\n "
                                "_before_ importing PyQt4.".format(str(api),str(v))
                                )
            else:
                set_api = False
        except ValueError:
            set_api = True
elif 'PySide' in sys.modules:
    set_api = False

if set_api:
    try:
        import sip
        sip.setapi('QString', 2)
        sip.setapi('QVariant', 2)
        # IPython needs this
        os.environ['QT_API'] = 'pyqt'
    except ImportError:
        print('Import Error in core/__init__.py: no sip module found. '
               'Implement the error handling!')
        pass  # no sip; probably pyside will be imported later..

# Import pyqtgraph
import pyqtgraph as pg

# Do not use scipy.weave to rescale data (FIXME: review why this is here)
pg.setConfigOptions(useWeave=False)

# Make icons work on non-X11 platforms, import a custom theme
print('Platform is', sys.platform)
if sys.platform == 'win32':
    try:
        import ctypes
        myappid = 'quantumoptics.quantumdiamond.mainapp' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except:
        print('SetCurrentProcessExplicitAppUserModelID failed! This is probably not Microsoft Windows!')

# rename any orphaned .pyc files -- these are probably leftover from 
# a module being moved and may interfere with expected operation.
compiledModuleDir = os.path.abspath(os.path.split(__file__)[0])
pg.renamePyc(compiledModuleDir)

# Install a simple message handler for Qt errors:
def messageHandler(msgType, msg):
    import traceback
    print("Qt Error: (traceback follows)")
    print(msg)
    traceback.print_stack()
    try:
        logf = "crash.log"
            
        fh = open(logf, 'a')
        fh.write(str(msg)+'\n')
        fh.write('\n'.join(traceback.format_stack()))
        fh.close()
    except:
        print("Failed to write crash log:")
        traceback.print_exc()

    if msgType == pg.Qt.QtCore.QtFatalMsg:
        try:
            print("Fatal error occurred; asking manager to quit.")
            global man
            man.quit()
            QtCore.QCoreApplication.instance().processEvents()
        except:
            pass

pg.QtCore.qInstallMsgHandler(messageHandler)
