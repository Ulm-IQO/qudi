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
from gui.GUIBase import GUIBase
import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtCore, QtGui
from . import ConsoleWidget
from . import ConsoleWindowUI

class SimpleConsole(GUIBase):
    """
    """
    def __init__(self, manager, name, config, **kwargs):
        """Create the console gui object.
          @param object manager: Manager object that this module was loaded from
          @param str name: Unique module name
          @param dict config: Module configuration
          @param dict kwargs: Optional arguments as a dict
        """
        c_dict = {'onactivate': self.initUI, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, c_dict)
        self.modules = set()

    def initUI(self, e=None):
        """Create all UI objects and show the window.
          @param object e: Fysom state change notice
        """
        if 'stylesheet' in self.getConfiguration():
            stylesheetpath = os.path.join(self.get_main_dir(), 'artwork', 'styles', 'console', self.getConfiguration()['stylesheet'])
        else:
            stylesheetpath = os.path.join(self.get_main_dir(), 'artwork', 'styles', 'console', 'conDark.qss')
        if not os.path.isfile(stylesheetpath):
            self.logMsg('Stylesheet not found at {0}'.format(stylesheetpath), importance=6, msgType='warning')
            self.stylesheet = ''
        else:
            stylesheetfile = open(stylesheetpath)
            self.stylesheet = stylesheetfile.read()
            stylesheetfile.close()

        self.namespace = {
            'pg': pg,
            'np': np,
            'config': self._manager.tree['defined'],
            'manager': self._manager
            }
        text = """
This is an interactive python console. The numpy and pyqtgraph modules have already been imported as 'np' and 'pg'. 
Configuration is in 'config', the manager is 'manager' and all loaded modules are in this namespace with their configured name.
View the current namespace with dir().
Go, play.
"""
        self.updateModuleList()
        self._mw = ConsoleMainWindow()
        self._cw = ConsoleWidget.ConsoleWidget(namespace=self.namespace, text=text)
        self._cw.applyStyleSheet(self.stylesheet)
        self.fontsize = 10
        if 'fontsize' in self._statusVariables:
            self.fontsize = self._statusVariables['fontsize']
            doc = self._cw.output.document()
            font = doc.defaultFont()
            font.setPointSize(self.fontsize)
            doc.setDefaultFont(font)
            #fnt = self._cw.input.font()
            #metric = QtGui.QFontMetrics(fnt)
            #self._cw.input.setFixedHeight(2*metric.lineSpacing())
            #fnt.setPointSize(self.fontsize+2)
            self._cw.input.setStyleSheet('font-size: {0}pt'.format(self.fontsize))
        self._mw.layout.addWidget(self._cw)
        self._manager.sigShowConsole.connect(self.show)
        self._manager.sigModulesChanged.connect(self.updateModuleList)
        self._mw.show()

    def deactivation(self, e):
        """ Close window and remove connections.

          @param object e: Fysom state change notification
        """
        self._cw.close()
        self._statusVariables['fontsize'] = self.fontsize

    def updateModuleList(self):
        """Remove non-existing modules from namespace, 
            add new modules to namespace, update reloaded modules
        """
        currentModules = set()
        newNamespace = dict()
        for base in ['hardware', 'logic', 'gui']:
            for module in self._manager.tree['loaded'][base]:
                currentModules.add(module)
                newNamespace[module] = self._manager.tree['loaded'][base][module]
        discard = self.modules - currentModules
        self.namespace.update(newNamespace)
        for module in discard:
            self.namespace.pop(module, None)
        self.modules = currentModules

    def show(self):
        """Make sure that the window is visible and at the top.
        """
        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()


class ConsoleMainWindow(QtGui.QMainWindow, ConsoleWindowUI.Ui_MainWindow):
    def __init__(self):
        """ Create the Console window.
        """
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)
        self.layout = QtGui.QVBoxLayout(self.centralwidget)

