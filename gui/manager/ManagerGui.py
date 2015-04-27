# -*- coding: utf-8 -*-
# Manager gui (test)

from core.Base import Base
from pyqtgraph.Qt import QtCore, QtGui
from .ManagerWindowTemplate import Ui_MainWindow

class ManagerGui(Base):
    sigStartAll = QtCore.Signal()
    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.activation}
        Base.__init__(self, manager, name, config, c_dict)

    def activation(self, e=None):
        self._mw = ManagerMainWindow()
        # Connect up the buttons.
        self._mw.loadAllButton.clicked.connect(self._manager.startAllConfiguredModules)
        self._mw.actionQuit.triggered.connect(self._manager.quit)
        self._mw.action_Load_all_modules.triggered.connect(self._manager.startAllConfiguredModules)
        self._mw.show()

class ManagerMainWindow(QtGui.QMainWindow,Ui_MainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)

class ModuleList(QtCore.AbstractItemModel):
    def __init__(self):
        super().__init__()

class ModuleItemDelegate(QtGui.QAbstractItemDelegate):
    def __init__(self):
        super().__init__()
