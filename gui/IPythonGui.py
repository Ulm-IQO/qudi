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
import os
import numpy as np
from collections import OrderedDict
from gui.GUIBase import GUIBase
from pyqtgraph.Qt import QtCore, QtGui

from IPython.qt.console.rich_ipython_widget import RichIPythonWidget
#from IPython.lib.kernel import connect_qtconsole

class IPythonGui(GUIBase):
    """
    """
    _modclass = 'IPythonGui'
    _modtype = 'gui'
    def __init__(self, manager, name, config, **kwargs):
        """Create the console gui object.
          @param object manager: Manager object that this module was loaded from
          @param str name: Unique module name
          @param dict config: Module configuration
          @param dict kwargs: Optional arguments as a dict
        """
        c_dict = {'onactivate': self.initUI, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, c_dict)

        ## declare connectors
        self.connector['in']['ipythonlogic'] = OrderedDict()
        self.connector['in']['ipythonlogic']['class'] = 'IPythonLogic'
        self.connector['in']['ipythonlogic']['object'] = None

       # self.consoles = list()
        #self.clients = list()

    def initUI(self, e=None):
        """Create all UI objects and show the window.
          @param object e: Fysom state change notice
        """
        ipythonlogic = self.connector['in']['ipythonlogic']['object']
        banner = """
This is an interactive IPython console. The numpy and pyqtgraph modules have already been imported as 'np' and 'pg'.
Configuration is in 'config', the manager is 'manager' and all loaded modules are in this namespace with their configured name.
View the current namespace with dir().
Go, play.
"""
        self._mw = QtGui.QMainWindow()
        self._mw.setWindowTitle('qudi: IPython Console')
        self._central = QtGui.QWidget()
        self._mw.setCentralWidget(self._central)
        self._layout = QtGui.QVBoxLayout(self._central)
        self._pywid = RichIPythonWidget()
        self._pywid.banner = banner
        self._pywid.kernel_manager = ipythonlogic.kernel_manager
        self._pywid.kernel_client = self._pywid.kernel_manager.client()
        self._pywid.kernel_client.start_channels()
        self._layout.addWidget(self._pywid)
        self.restoreWindowPos(self._mw)
        # the linux style theme which is basically the monokai theme
        self._pywid.set_default_style(colors='linux')
        self._mw.show()

    def show(self):
        """Make sure that the window is visible and at the top.
        """
        self._mw.show()

    def deactivation(self, e=None):
        """ Hide window and stop ipython console.
          @param object e: Fysom state change notice
        """
        self._pywid.kernel_client.stop_channels()
        self.saveWindowPos(self._mw)
        self._mw.close()
