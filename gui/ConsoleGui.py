# -*- coding: utf-8 -*-
# Cosole from pyqtgraph

from core.Base import Base
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.console

class ConsoleGui(Base):
    def __init__(self, manager, name, config, **kwargs):
        self._cw = pyqtgraph.console.ConsoleWidget()
        Base.__init__(self, manager, name, configuration=config)
        self.initUI()

    def initUI(self):
        self._cw.show()
