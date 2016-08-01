# -*- coding: utf-8 -*-
"""
This file contains the QuDi GUI module base class.

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
"""

from gui.guibase import GUIBase
from pyqtgraph.Qt import QtCore, QtGui

class TrayIcon(GUIBase):
    """ This module contains a tray icon implementation for QuDi.
    When this module is loaded into QuDi, it will show the QuDi icon in the system tray.
    Left-clicking this icon will show an action menu that lets you bring the Manager window to the front.
    Right-clicking this icon will bring up a Quit button that will colse the whole application.
    """

    def on_activate(self, e=None):
        """ Set up tray icon UI .

          @param e: Fysom state change

            This method is automatically called by changing the Base state through activate().
        """
        self._tray = SystemTrayIcon()
        self._tray.show()
        self._tray.quitAction.triggered.connect(self._manager.quit)
        self._tray.managerAction.triggered.connect(lambda: self._manager.sigShowManager.emit())

    def on_deactivate(self, e):
        """ Remove all the stuff that we set up.

          @param object e: Fysom state change notification
        """
        self._tray.hide()
        self._tray.quitAction.triggered.disconnect()
        self._tray.managerAction.triggered.disconnect()

    def show(self):
        """Trayicon has no window to show.
        """
        pass

class SystemTrayIcon(QtGui.QSystemTrayIcon):
    """Tray icon class subclassing QSystemTrayIcon for custom functionality.
    """
    def __init__(self):
        """Tray icon constructor.
        Adds all the appropriate menus and actions.
        """
        QtGui.QSystemTrayIcon.__init__(self)
        self.setIcon(QtGui.QApplication.instance().windowIcon())
        self.right_menu = QtGui.QMenu('Quit')
        self.left_menu = QtGui.QMenu('Manager')
        iconpath = 'artwork/icons/oxygen'
        self.managericon = QtGui.QIcon()
        self.managericon.addFile('{0}/22x22/go-home.png'.format(iconpath), QtCore.QSize(16,16))
        self.exiticon = QtGui.QIcon()
        self.exiticon.addFile('{0}/22x22/application-exit.png'.format(iconpath), QtCore.QSize(16,16))
        self.quitAction = QtGui.QAction(self.exiticon, "&Quit", self.right_menu)
        self.managerAction = QtGui.QAction(self.managericon, "&Manager", self.left_menu)
        self.left_menu.addAction(self.managerAction)
        self.right_menu.addAction(self.quitAction)
        self.setContextMenu(self.right_menu)
        self.activated.connect(self.click_trap)

    def click_trap(self, value):
        """ Click handler.

          @param value: action that caused the activation

            This method is called when the tray icon is left-clicked and
            it opens a menu at the position of the left click.
        """
        if value == self.Trigger:
            self.left_menu.exec_(QtGui.QCursor.pos())

