# -*- coding: utf-8 -*-
# Manager gui (test)

from core.Base import Base
from pyqtgraph.Qt import QtCore, QtGui
from .ManagerWindowTemplate import Ui_MainWindow

class ManagerGui(Base):
    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.activation}
        Base.__init__(self,
                    manager,
                    name,
                    config,
                    c_dict)

    def activation(self, e=None):
        self._mw = ManagerMainWindow()
        # Connect up the buttons.
        self._mw.loadAllButton.clicked.connect(self.handleLoadAllButton)
        self._mw.show()
        

    def handleLoadAllButton(self):
        self._manager.startAllConfiguredModules()

class ManagerMainWindow(QtGui.QMainWindow,Ui_MainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)