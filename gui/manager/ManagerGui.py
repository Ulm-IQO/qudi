# -*- coding: utf-8 -*-
# Manager gui (test)

from core.Base import Base
from pyqtgraph.Qt import QtCore, QtGui
from .ManagerWindowTemplate import Ui_MainWindow
from .ModuleWidgetTemplate import Ui_ModuleWidget
from collections import OrderedDict

class ManagerGui(Base):
    sigStartAll = QtCore.Signal()
    sigStartThis = QtCore.Signal(str, str)
    sigReloadThis = QtCore.Signal(str, str)
    sigStopThis = QtCore.Signal(str, str)
    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.activation}
        Base.__init__(self, manager, name, config, c_dict)
        self.modlist = list()

    def activation(self, e=None):
        self._mw = ManagerMainWindow()
        # Connect up the buttons.
        self._mw.loadAllButton.clicked.connect(self._manager.startAllConfiguredModules)
        self._mw.actionQuit.triggered.connect(self._manager.quit)
        self._mw.action_Load_all_modules.triggered.connect(self._manager.startAllConfiguredModules)
        self._mw.show()
        self._manager.sigManagerShow.connect(self._mw.raise_)
        self._manager.sigConfigChanged.connect(self.updateConfigWidgets)
        self._manager.sigModulesChanged.connect(self.updateConfigWidgets)
        self.sigStartThis.connect(self._manager.startModule)
        self.updateModuleList()

    def updateConfigWidgets(self):
        self.fill_tree_widget(self._mw.treeWidget, self._manager.tree)
    
    def updateModuleList(self):
        #self.clearModuleList(self)
        self.fillModuleList(self._mw.scrollboxlayout)
        
    def fillModuleList(self, layout):
        base = 'gui'
        #for base in self._manager.tree['defined']:
        for module in self._manager.tree['defined'][base]:
            widget = ModuleListItem(base, module)
            self.modlist.append(widget)
            layout.addWidget(widget)
            widget.sigActivateThis.connect(self.sigStartThis)

    def fill_tree_item(self, item, value):
        """ Recursively fill a QTreeWidgeItem with the contents from a dictionary.
            
          @param QTreeWidgetItem item: the widget item to fill
          @param (dict, list, etc) value: value to fill in
        """
        item.setExpanded(True)
        if type(value) is OrderedDict or type(value) is dict:
            for key in value:
                child = QtGui.QTreeWidgetItem()
                child.setText(0, key)
                item.addChild(child)
                self.fill_tree_item(child, value[key])
        elif type(value) is list:
            for val in value:
                child = QtGui.QTreeWidgetItem()
                item.addChild(child)
                if type(val) is dict:
                    child.setText(0, '[dict]')
                    self.fill_tree_item(child,val)
                elif type(val) is OrderedDict:
                    child.setText(0, '[odict]')
                    self.fill_tree_item(child,val)
                elif type(val) is list:
                    child.setText(0, '[list]')
                    self.fill_tree_item(child,val)
                else:
                    child.setText(0, str(val))
                child.setExpanded(True)
        else:
            child = QtGui.QTreeWidgetItem()
            child.setText(0, str(value))
            item.addChild(child)

    def fill_tree_widget(self, widget, value):
        """ Fill a QTreeWidget with the content of a dictionary
           
          @param QTreeWidget widget: the tree widget to fill
          @param dict,OrderedDict value: the dictionary to fill in
        """
        widget.clear()
        self.fill_tree_item(widget.invisibleRootItem(), value)


class ManagerMainWindow(QtGui.QMainWindow,Ui_MainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)
        self.scrollboxlayout = QtGui.QVBoxLayout(self.scrollcontent)
        #self.test = QtGui.QPushButton('test')
        #self.scrollboxlayout.addWidget(self.test)

class ModuleListItem(QtGui.QFrame, Ui_ModuleWidget):

    sigActivateThis = QtCore.Signal(str, str)

    def __init__(self, basename, modulename):
        super().__init__()
        self.setupUi(self)
        self.name = modulename
        self.loadButton.setText('Load {0}'.format(self.name))
        self.loadButton.clicked.connect(self.activateButtonClicked)

    def activateButtonClicked(self):
        self.sigActivateThis.emit('gui', self.name)

    def reloadButtonClicked(self):
        self.sigReloadThis.emit('gui', self.name)

    def stopeButtonClicked(self):
        self.sigStopThis.emit('gui', self.name)
