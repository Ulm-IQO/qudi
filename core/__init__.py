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

__version__ = '0.0.1'

import os
import sys

# Set up a list of paths to search for configuration files 
# (used if no config is explicitly specified).

# First we check the parent directory of the current module.
# This path is used when running directly from a source checkout
modpath = os.path.dirname(os.path.abspath(__file__))
CONFIGPATH = [
    os.path.normpath(os.path.join(modpath, '..', 'config')),
    ]

# Next check for standard system install locations
if 'linux' in sys.platform or sys.platform == 'darwin':
    CONFIGPATH.append('/etc/qudi')

# Finally, look for an example config..
CONFIGPATH.extend([
    os.path.normpath(os.path.join(modpath, '..', 'config', 'example')),
    os.path.normpath(os.path.join(modpath, 'config', 'example')),
    ])


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

# Import pyqtgraph, get QApplication instance
import pyqtgraph as pg
# Make icons work on non-X11 platforms, import a custom theme
print('Platform is', sys.platform)
pg.setConfigOptions(useWeave=False)


# Every Qt application must have ONE AND ONLY ONE QApplication object. The 
# command mkQpp makes a QApplication object, which is a class to manage the GUI
# application's control flow, events and main settings:

app = pg.mkQApp()

# Make icons work on non-X11 platforms, set custom theme
if not sys.platform.startswith('linux') and not sys.platform.startswith('freebsd'):
    themepaths = pg.Qt.QtGui.QIcon.themeSearchPaths()
    themepaths.append('artwork/icons')
    pg.Qt.QtGui.QIcon.setThemeSearchPaths(themepaths)
    pg.Qt.QtGui.QIcon.setThemeName('qudiTheme')

# rename any orphaned .pyc files -- these are probably leftover from 
# a module being moved and may interfere with expected operation.
modDir = os.path.abspath(os.path.split(__file__)[0])
pg.renamePyc(modDir)

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
            global man, app
            man.quit()
            app.processEvents()
        except:
            pass

pg.QtCore.qInstallMsgHandler(messageHandler)
