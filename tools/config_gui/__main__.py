# -*- coding: utf-8 -*-
"""
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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""
if __package__ is None:
    import __init__
    __package__ = 'config_gui'
else:
    import __init__

from qtpy import QtCore, QtGui, QtWidgets, uic

from pyflowgraph.graph_view import GraphView
from pyflowgraph.graph_view_widget import GraphViewWidget
from pyflowgraph.node import Node
from pyflowgraph.port import InputPort, OutputPort, IOPort

import sys
import os

sys.path.append(os.getcwd())
from gui.colordefs import QudiPalettePale as palette
import core.config
from menu import ModMenu
import listmods


class ConfigMainWindow(QtWidgets.QMainWindow):
    """ This class represents the Manager Window.
    """
    def __init__(self):
        """ Create the Manager Window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_config_window.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)

        # init 
        self.setupUi()
        self.show()

    def setupUi(self):
        self.actionNew_configuration.triggered.connect(self.newConfigFile)
        self.actionSave_configuration.triggered.connect(self.saveConfigFile)
        self.actionSave_configuration_as.triggered.connect(self.saveConfigFileAs)
        self.actionOpen_configuration.triggered.connect(self.openConfigFile)
        self.actionDelete_selected_nodes.triggered.connect(self.graphView.deleteSelectedNodes)
        self.actionFrame_selected_nodes.triggered.connect(self.graphView.frameSelectedNodes)
        self.actionFrame_all_nodes.activated.connect(self.graphView.frameAllNodes)

        # add module menu
        self.findModules()
        self.mmroot = ModMenu(self.m)
        for mod in self.mmroot.modules:
            mod.sigAddModule.connect(self.addModule)
        self.actionAdd_Module.setMenu(self.mmroot)

    def findModules(self):
        modules = listmods.find_pyfiles(os.getcwd())
        m, i_s, ie, oe = listmods.check_qudi_modules(modules)
        self.m = m

        if len(oe) > 0 or len(ie) > 0:
            print('\n==========  ERRORS:  ===========', file=sys.stderr)
            for e in oe:
                print(e[0], file=sys.stderr)
                print(e[1], file=sys.stderr)

            for e in ie:
                print(e[0], file=sys.stderr)
                print(e[1], file=sys.stderr)
       #  print(self.m)

    def addModule(self, module, pos=(0,0)):
        g = self.graphView
        node = Node(g, module.name)
        if module.name.startswith('hardware'):
            node.setColor(palette.c2)
        elif module.name.startswith('logic'):
            node.setColor(palette.c1)
        elif module.name.startswith('gui'):
            node.setColor(palette.c4)
        else:
            node.setColor(palette.c3)
        for conn in module.conn_in:
            node.addPort(InputPort(node, g, conn[0], palette.c3, conn[1]))

        for conn in module.conn_out:
            node.addPort(OutputPort(node, g, conn[0], palette.c3, conn[1]))

        node.setGraphPos(QtCore.QPointF(pos[0], pos[1]))

        g.addNode(node)

    def openConfigFile(self):
        defaultconfigpath = ''
        filename = QtWidgets.QFileDialog.getOpenFileName(
            self,
            'Load Configration',
            defaultconfigpath ,
            'Configuration files (*.cfg)')
        print('Open:', filename)
        config = core.config.load(filename)
        self.configToNodes(config)

    def newConfigFile(self):
        self.graphView.reset()
        self.configFileName = 'New configuration'
        self.updateWindowTitle(self.configFileName, extra='*')

    def saveConfigFile(self):
        pass

    def saveConfigFileAs(self):
        pass

    def updateWindowTitle(self, filename, extra=''):
        self.setWindowTitle('{}{} - QuDi configuration editor'.format(filename, extra))
    
    def getModuleInfo(self):
        modules = listmods.find_pyfiles(os.getcwd())
        m, i_s, ie, oe = listmods.check_qudi_modules(modules)

    def configToNodes(self, config):
        pos = [0, 0]
        for b,m in config.items():
            if b not in ['hardware', 'logic', 'gui']:
                continue
            for k,v in m.items():
                mc = 'module.Class'
                print(b, k, v)
                if mc in v and b + '.' + v[mc] in [mod.name for mod in self.mmroot.modules]:
                    mod = next(x for x in self.mmroot.modules if x.name ==  b + '.' + v[mc])
                    self.addModule(mod, pos)
                pos[1] += 100
            pos[0] += 600
            pos[1] = 0


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mw = ConfigMainWindow()
    app.exec_()

