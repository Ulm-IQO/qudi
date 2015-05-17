# -*- coding: utf-8 -*-
# Cosole from pyqtgraph

from core.Base import Base
import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtCore, QtGui
from . import Console

class ConsoleGui(Base):
    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.initUI}
        Base.__init__(self, manager, name, config, c_dict)

    def initUI(self, e=None):
        namespace = {
            'pg': pg,
            'np': np,
            'mod': self._manager.tree['loaded'],
            'gui': self._manager.tree['loaded']['gui'],
            'logic': self._manager.tree['loaded']['logic'],
            'hardware': self._manager.tree['loaded']['hardware'],
            'config': self._manager.tree['defined']
            }
        text = """
This is an interactive python console. The numpy and pyqtgraph modules have already been imported 
as 'np' and 'pg'. 
Configuration is in 'config', loaded modules in 'mod' and in 'hardware', 'logic' and 'gui'.
Go, play.
"""
        self._cw = Console.ConsoleWidget(namespace=namespace, text=text)
        self._cw.setWindowTitle('qudi: Console')
        self._manager.sigShowConsole.connect(self.show)
        self._cw.show()

    def show(self):
        QtGui.QMainWindow.show(self._cw)
        self._cw.activateWindow()
        self._cw.raise_()
