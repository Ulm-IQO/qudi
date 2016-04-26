# -*- coding: utf-8 -*-
"""
This file contains the QuDi console app class.

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
"""

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui

class Gui(QtCore.QObject):

    def __init__(self):
        super().__init__()

    def makePyQtGraphQApplication(self):
        # Every Qt application must have ONE AND ONLY ONE QApplication object. The 
        # command mkQpp makes a QApplication object, which is a class to manage the GUI
        # application's control flow, events and main settings:
        return pg.mkQApp()

    def setAppIcon(self):
        iconpath = 'artwork/logo/logo-qudi-'
        self.appIcon = QtGui.QIcon()
        self.appIcon.addFile('{0}16x16.png'.format(iconpath), QtCore.QSize(16,16))
        self.appIcon.addFile('{0}24x24.png'.format(iconpath), QtCore.QSize(24,24))
        self.appIcon.addFile('{0}32x32.png'.format(iconpath), QtCore.QSize(32,32))
        self.appIcon.addFile('{0}48x48.png'.format(iconpath), QtCore.QSize(48,48))
        self.appIcon.addFile('{0}256x256.png'.format(iconpath), QtCore.QSize(256,256))
        QtGui.QApplication.instance().setWindowIcon(self.appIcon)

    def setTheme(self):
        # Make icons work on non-X11 platforms, set custom theme
        #if not sys.platform.startswith('linux') and not sys.platform.startswith('freebsd'):
        #
        # To enable the use of custom action icons, for now the above if statement has been
        # removed and the QT theme is being set to our artwork/icons folder for all OSs.
        themepaths = pg.Qt.QtGui.QIcon.themeSearchPaths()
        themepaths.append('artwork/icons')
        pg.Qt.QtGui.QIcon.setThemeSearchPaths(themepaths)
        pg.Qt.QtGui.QIcon.setThemeName('qudiTheme')

    def setStyleSheet(self, stylesheet):
        QtGui.QApplication.instance().setStyleSheet(stylesheet)
        testwidget = QtGui.QWidget()
        testwidget.ensurePolished()
        bgcolor = testwidget.palette().color(QtGui.QPalette.Normal, testwidget.backgroundRole())
        # set manually the background color in hex code according to our color scheme: 
        pg.setConfigOption('background', bgcolor)   

    def closeWindows(self):
        QtGui.QApplication.instance().closeAllWindows()

