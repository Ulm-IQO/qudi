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

class RightClickMenu(QtGui.QMenu):
    def __init__(self, parent=None):
        QtGui.QMenu.__init__(self, "Edit", parent)
        self.icon = QtGui.QIcon.fromTheme("edit-cut")
        self.addAction(QtGui.QAction(self.icon, "&Cut", self))

class LeftClickMenu(QtGui.QMenu):
    def __init__(self, parent=None):
        QtGui.QMenu.__init__(self, "Edit", parent)
        self.icon = QtGui.QIcon.fromTheme("document-new")
        self.addAction(QtGui.QAction(self.icon, "&New", self))

class SystemTrayIcon(QtGui.QSystemTrayIcon):
    def __init__(self, parent=None):
        QtGui.QSystemTrayIcon.__init__(self, parent)
        self.logo=QtGui.QIcon('artwork/qudi_trayicon.png')
        self.setIcon(self.logo)
        self.right_menu = RightClickMenu()
        self.left_menu = LeftClickMenu()
        self.setContextMenu(self.right_menu)
        self.activated.connect(self.click_trap)

    def click_trap(self, value):
        if value == self.Trigger:
            self.left_menu.exec_(QtGui.QCursor.pos())

    def welcome(self):
        self.showMessage("Hello World")
