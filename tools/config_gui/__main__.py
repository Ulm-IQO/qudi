# -*- coding: utf-8 -*-

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
from menu import ModMenu


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
        self.testGraph()
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
        self.mmroot = ModMenu()
        self.actionAdd_Module.setMenu(self.mmroot)

    def testGraph(self):
        g = self.graphView
        node1 = Node(g, 'Short')
        node1.setColor(palette.c1)
        node1.addPort(InputPort(node1, g, 'InPort1', QtGui.QColor(128, 170, 170, 255), 'MyDataX'))
        node1.addPort(InputPort(node1, g, 'InPort2', QtGui.QColor(128, 170, 170, 255), 'MyDataX'))
        node1.addPort(OutputPort(node1, g, 'OutPort', QtGui.QColor(32, 255, 32, 255), 'MyDataY'))
        node1.addPort(IOPort(node1, g, 'IOPort1', QtGui.QColor(32, 255, 32, 255), 'MyDataY'))
        node1.addPort(IOPort(node1, g, 'IOPort2', QtGui.QColor(32, 255, 32, 255), 'MyDataY'))
        node1.setGraphPos(QtCore.QPointF( -100, 0 ))

        g.addNode(node1)

    def openConfigFile(self):
        defaultconfigpath = ''
        filename = QtGui.QFileDialog.getOpenFileName(
            self,
            'Load Configration',
            defaultconfigpath ,
            'Configuration files (*.cfg)')
        print('Open:', filename)

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

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mw = ConfigMainWindow()
    app.exec_()

