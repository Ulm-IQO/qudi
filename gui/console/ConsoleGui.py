# -*- coding: utf-8 -*-
"""
This file contains the QuDi console GUI module.

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

from gui.GUIBase import GUIBase
import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtCore, QtGui
from . import Console

class ConsoleGui(GUIBase):
    """
    """
    def __init__(self, manager, name, config, **kwargs):
        """Create the console gui object.
          @param object manager: Manager object that this module was loaded from
          @param str name: Unique module name
          @param dict config: Module configuration
          @param dict kwargs: Optional arguments as a dict
        """
        c_dict = {'onactivate': self.initUI}
        super().__init__(manager, name, config, c_dict)

    def initUI(self, e=None):
        """Create all UI objects and show the window.
          @param object e: Fysom state change notice
        """
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
        """Make sure that the window is visible and at the top.
        """
        QtGui.QMainWindow.show(self._cw)
        self._cw.activateWindow()
        self._cw.raise_()
