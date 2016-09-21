# -*- coding: utf-8 -*-
"""
This file contains the Qudi Manager class.

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
"""

__version__ = '0.1'

# import Qt
import os

if not 'QT_API' in os.environ:
    # use PyQt4 as default
    os.environ['QT_API'] = 'pyqt'
else:
    print('Specified Qt API:', os.environ['QT_API'])
    # if pyqt4 check environment variable is 'pyqt' and not 'pyqt4' (ipython,
    # matplotlib, etc)
    if os.environ['QT_API'].lower() == 'pyqt4':
        os.environ['QT_API'] = 'pyqt'

import qtpy
print('Used Qt API:', qtpy.API_NAME)

import sys
# Make icons work on non-X11 platforms, import a custom theme
if sys.platform == 'win32':
    try:
        import ctypes
        myappid = 'quantumoptics.quantumdiamond.mainapp'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except:
        print('SetCurrentProcessExplicitAppUserModelID failed! This is '
              'probably not Microsoft Windows!')
