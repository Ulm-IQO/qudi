# -*- coding: utf-8 -*-
"""
Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

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
from port import QudiPortType
from config_model import ModuleConfigModel
from collections import OrderedDict
import listmods
import logging
import argparse

class ModNode:

    def __init__(self, module, node):
        self.module = module
        self.node = node

class ConfigMainWindow(QtWidgets.QMainWindow):
    """ This class represents the Manager Window.
    """
    def __init__(self, loadfile=None):
        """ Create the Manager Window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_config_window.ui')
        self.log = logging.getLogger(__name__)

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)

        self.modules = dict()
        self.globalsection = OrderedDict()
        self.currentFile = ''

        # palette
        self.colors = {
            'hardware': palette.c2,
            'logic': palette.c1,
            'gui': palette.c4,
            '': palette.c3
        }

        # init
        self.setupUi()
        self.show()

        if loadfile is not None:
            self.loadConfigFile(loadfile)

    def setupUi(self):
        self.actionNew_configuration.triggered.connect(self.newConfigFile)
        self.actionSave_configuration.triggered.connect(self.saveConfigFile)
        self.actionSave_configuration_as.triggered.connect(self.saveConfigFileAs)
        self.actionOpen_configuration.triggered.connect(self.openConfigFile)
        self.actionDelete_selected_nodes.triggered.connect(self.graphView.deleteSelectedNodes)
        self.actionFrame_selected_nodes.triggered.connect(self.graphView.frameSelectedNodes)
        self.actionFrame_all_nodes.triggered.connect(self.graphView.frameAllNodes)

        # add module menu
        self.findModules()
        self.mmroot = ModMenu(self.m)
        for mod in self.mmroot.modules:
            mod.sigAddModule.connect(self.addModule)
        self.actionAdd_Module.setMenu(self.mmroot)

        # node change signals
        self.graphView.nodeAdded.connect(self.nodeAdded)
        self.graphView.nodeRemoved.connect(self.nodeRemoved)
        self.graphView.nodeNameChanged.connect(self.nodeNameChanged)
        self.graphView.selectionChanged.connect(self.selectedNodesChanged)

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

    def addModule(self, module, name=None, pos=(0,0)):
        """ Add a module to the GraphView
        """

        # sort out the module name
        if name is None:
            name = 'new_module'
        n = 1
        if self.graphView.hasNode(name):
            while self.graphView.hasNode('{}{}'.format(name, n)):
                n += 1
            name = '{}{}'.format(name, n)

        # chart view
        g = self.graphView

        # new node in chart
        node = Node(g, name)

        # coloring
        node.setColor(self.colors[module.base])

        # check where the module belongs and what it can connect to
        for cname, conn in module.connections.items():
            port_type = QudiPortType('in', module.base, [conn.ifname])
            node.addPort(InputPort(node, g, conn.name, palette.c3, port_type))

        if module.base != 'gui':
            port_type = QudiPortType('out', module.base, module.interfaces)
            node.addPort(OutputPort(node, g, 'out', palette.c3, port_type))

        # set position in view
        node.setGraphPos(QtCore.QPointF(pos[0], pos[1]))

        # save the module instance and node relatonship
        self.modules[name] = ModNode(module, node)
        # add node to view
        g.addNode(node)

    def openConfigFile(self):
        defaultconfigpath = ''
        filename = QtWidgets.QFileDialog.getOpenFileName(
            self,
            'Load Configration',
            defaultconfigpath ,
            'Configuration files (*.cfg)')[0]
        if len(filename) > 0:
            print('Open:', filename)
            self.loadConfigFile(filename)

    def loadConfigFile(self, filename):
        config = core.config.load(filename)
        self.configToNodes(config)
        self.currentFile = filename
        self.graphView.frameAllNodes()

    def newConfigFile(self):
        self.graphView.reset()
        self.configFileName = 'New configuration'
        self.updateWindowTitle(self.configFileName, extra='*')

    def saveConfigFile(self):
        if os.path.isfile(self.currentFile):
            config = self.nodesToConfig()
            core.config.save(self.currentFile, config)
        else:
             self.saveConfigFileAs()

    def saveConfigFileAs(self):
        defaultconfigpath = os.path.dirname(self.currentFile)
        filename = QtWidgets.QFileDialog.getSaveFileName(
            self,
            'Save Configration As',
            defaultconfigpath ,
            'Configuration files (*.cfg)')[0]
        if len(filename) > 0:
            print('Save:', filename)
            config = self.nodesToConfig()
            core.config.save(filename, config)
            self.currentFile = filename

    def updateWindowTitle(self, filename, extra=''):
        self.setWindowTitle('{}{} - Qudi configuration editor'.format(filename, extra))

    def configToNodes(self, config):
        self.addNodes(config)
        self.connectNodes(config)

    def addNodes(self, config):
        pos = [0, 0]
        for base, conf_modules in config.items():
            if base not in ['hardware', 'logic', 'gui']:
                continue
            for mod_conf_name, mod_conf_values in conf_modules.items():
                mc = 'module.Class'
                #print(base, mod_conf_name, mod_conf_values)
                if mc in mod_conf_values and self.mmroot.hasModule(base + '.' + mod_conf_values[mc]):
                    mod = self.mmroot.getModule(base + '.' + mod_conf_values[mc])
                    self.addModule(mod, mod_conf_name, pos)
                pos[1] += 100
            pos[0] += 600
            pos[1] = 0

    def connectNodes(self, config):
        for base, conf_modules in config.items():
            if base not in ['hardware', 'logic', 'gui']:
                continue
            for conf_mod_name, conf_mod_values in conf_modules.items():
                if 'connect' in conf_mod_values:
                    dst_mod_name = conf_mod_name
                    for conn_in, conn_out in conf_mod_values['connect'].items():
                        src_mod_name = conn_out
                        if conf_mod_name not in self.modules:
                            self.log.error(
                                'Target module {} not present while connecting {} to {}'
                                ''.format(dst_mod_name, conn_in, src_mod_name))
                            continue
                        conn_names_dst = [c.name for cn, c in self.modules[dst_mod_name].module.connections.items()]
                        if conn_in not in conn_names_dst:
                            self.log.error(
                                'Target connector {} not present while connecting {} to {}.{}'
                                ''.format(conn_in, src_mod_name, dst_mod_name, conn_in))
                            continue
                        if src_mod_name not in self.modules:
                            self.log.error(
                                'Source module {} not present while connecting it to {}.{}'
                                ''.format(src_mod_name, dst_mod_name, conn_in))
                            continue

                        try:
                            self.graphView.connectPorts(
                                self.modules[src_mod_name].node,
                                'out',
                                self.modules[dst_mod_name].node,
                                conn_in)
                        except:
                            self.log.exception(
                                'pyflowgraph failed while connecting {} to {}.{}'
                                ''.format(src_mod_name, dst_mod_name, conn_in))

        self.globalsection = config['global']

    def nodesToConfig(self):
        """ Convert nodes into OrderedDict for saving.
        """
        config = OrderedDict()
        config['global'] = OrderedDict()
        config['hardware'] = OrderedDict()
        config['logic'] = OrderedDict()
        config['gui'] = OrderedDict()

        for key, value in self.globalsection.items():
            config['global'][key] = value

        for mod_name, mod in self.modules.items():
            entry = OrderedDict()
            path = mod.module.path.split('.')

            if len(path) > 1 and path[0] in ('hardware', 'logic', 'gui'):
                config[path[0]][mod_name] = entry
                entry['module.Class'] = '.'.join(path[1:])

                portin = (mod.node.getPort(x[0]) for x in mod.module.conn)
                conndict = OrderedDict()
                for port in portin:
                    conns = port.inCircle().getConnections()
                    if len(conns) == 1:
                        c = tuple(conns)[0]
                        src = c.getSrcPort()
                        node = src.getNode()
                        conndict[port.getName()] = '{}.{}'.format(node.getName(), src.getName())
                if len(conndict) > 0:
                    entry['connect'] = conndict
                # FIXME: rest of the configuration
            print(entry)
        return config

    def nodeAdded(self, node):
        pass

    def nodeRemoved(self, node):
        pass

    def nodeNameChanged(self, oldName, newName):
        pass

    @QtCore.Slot(list, list)
    def selectedNodesChanged(self, oldSelection, newSelection):
        self.tableView.setModel()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='config_gui')
    parser.add_argument('-c', '--config', default=None, help='configuration file')
    args = parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)
    mw = ConfigMainWindow(loadfile=args.config)
    app.exec_()

