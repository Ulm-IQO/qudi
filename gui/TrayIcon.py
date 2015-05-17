# -*- coding: utf-8 -*-
""" This module contains a tray icon implementation for QuDi.
When this module is loaded into QuDi, it will show the QuDi icon in the system tray.
Left-clicking this icon will show an action menu that lets you bring the Manager window to the front.
Right-clicking this icon will bring up a Quit button that will colse the whole application.
"""

from core.Base import Base
from pyqtgraph.Qt import QtCore, QtGui

class TrayIcon(Base):
    """ The QuDi modlue class for the tray icon.
    """
    def __init__(self, manager, name, config = {}, **kwargs):
        """ Constructor for QuDi tray icon module.
          @param object manager: the manager object that this tray icon belongs to
          @param string name: the unique name of the module
          @param dict config: the configuration dict for the module
          @param dict kwargs: further named arguments
        """
        callback = {'onactivate': self.initUI}
        Base.__init__(self,
                    manager,
                    name,
                    config,
                    callback
                    )

    def initUI(self, e=None):
        """ Set up tray icon UI .

          @param e: Fysom state change

            This method is automatically called by changing the Base state through activate().
        """
        self._tray = SystemTrayIcon()
        self._tray.show()
        self._tray.quitAction.triggered.connect(self._manager.quit)
        self._tray.managerAction.triggered.connect(lambda: self._manager.sigShowManager.emit())

class SystemTrayIcon(QtGui.QSystemTrayIcon):
    """Tray icon class subclassing QSystemTrayIcon for custom functionality.
    """
    def __init__(self):
        """Tray icon constructor.
        Adds all the appropriate menus and actions.
        """
        QtGui.QSystemTrayIcon.__init__(self)
        self.logo=QtGui.QIcon('artwork/qudi_trayicon.png')
        self.setIcon(self.logo)
        self.right_menu = QtGui.QMenu('Quit')
        self.left_menu = QtGui.QMenu('Manager')
        self.managericon = QtGui.QIcon.fromTheme("go-home")
        self.exiticon = QtGui.QIcon.fromTheme("application-exit")
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

