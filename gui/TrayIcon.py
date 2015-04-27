# -*- coding: utf-8 -*-
# a tray Icon for QuDi

from core.Base import Base
from pyqtgraph.Qt import QtCore, QtGui

class TrayIcon(Base):
    def __init__(self, manager, name, config = {}, **kwargs):
        callback = {'onactivate': self.initUI}
        Base.__init__(self,
                    manager,
                    name,
                    config,
                    callback
                    )

    def initUI(self, e=None):
        self._tray = SystemTrayIcon()
        self._tray.show()
        #self._tray.

class RightClickMenu(QtGui.QMenu):
    def __init__(self, parent=None):
        QtGui.QMenu.__init__(self, "quit", parent)
        self.icon = QtGui.QIcon.fromTheme("quit")

class LeftClickMenu(QtGui.QMenu):
    def __init__(self, parent=None):
        QtGui.QMenu.__init__(self, "Edit", parent)

class SystemTrayIcon(QtGui.QSystemTrayIcon):
    def __init__(self, parent=None):
        QtGui.QSystemTrayIcon.__init__(self, parent)
        self.logo=QtGui.QIcon('artwork/qudi_trayicon.png')
        self.setIcon(self.logo)
        #self.right_menu = QtGui.QMenu('Quit')
        #self.left_menu = QtGui.QMenu('Manager')
        #self.managericon = QtGui.QIcon.fromTheme("document-new")
        #self.exiticon = QtGui.QIcon.fromTheme("exit")
        #self.left_menu.addAction(QtGui.QAction(self.managericon, "&Manager", self.left_menu))
        #self.right_menu.addAction(QtGui.QAction(self.icon, "&Quit", self))
        #self.setContextMenu(self.right_menu)
        #self.activated.connect(self.click_trap)

    def click_trap(self, value):
        if value == self.Trigger:
            self.left_menu.exec_(QtGui.QCursor.pos())

    def welcome(self):
        self.showMessage("Hello World")
