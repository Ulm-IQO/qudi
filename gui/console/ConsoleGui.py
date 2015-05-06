# -*- coding: utf-8 -*-
# Cosole from pyqtgraph

from core.Base import Base
import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.console

class ConsoleGui(Base):
    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.initUI}
        Base.__init__(self, manager, name, config, c_dict)

    def initUI(self, e=None):
        namespace = {'pg': pg, 'np': np}
        text = """
This is an interactive python console. The numpy and pyqtgraph modules have already been imported 
as 'np' and 'pg'. 
Go, play.
"""
        self._cw = pyqtgraph.console.ConsoleWidget(namespace=namespace, text=text)
        self._cw.setWindowTitle('QuDi: Console')
        self._cw.show()
