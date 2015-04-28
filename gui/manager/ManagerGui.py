# -*- coding: utf-8 -*-
# Manager gui (test)

from core.Base import Base
from pyqtgraph.Qt import QtCore, QtGui
from .ManagerWindowTemplate import Ui_MainWindow
from collections import OrderedDict

class ManagerGui(Base):
    sigStartAll = QtCore.Signal()
    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.activation}
        Base.__init__(self, manager, name, config, c_dict)

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

    def updateConfigWidgets(self):
        self.fill_widget(self._mw.treeWidget, self._manager.tree)


    def fill_item(self, item, value):
        item.setExpanded(True)
        if type(value) is OrderedDict or type(value) is dict:
            for key in value:
                child = QtGui.QTreeWidgetItem()
                child.setText(0, key)
                item.addChild(child)
                self.fill_item(child, value[key])
        elif type(value) is list:
            for val in value:
                child = QtGui.QTreeWidgetItem()
                item.addChild(child)
                if type(val) is dict:
                    child.setText(0, '[dict]')
                    self.fill_item(child,val)
                elif type(val) is OrderedDict:
                    child.setText(0, '[odict]')
                    self.fill_item(child,val)
                elif type(val) is list:
                    child.setText(0, '[list]')
                    self.fill_item(child,val)
                else:
                    child.setText(0, str(val))
                child.setExpanded(True)
        else:
            child = QtGui.QTreeWidgetItem()
            child.setText(0, str(value))
            item.addChild(child)

    def fill_widget(self, widget, value):
        widget.clear()
        self.fill_item(widget.invisibleRootItem(), value)


class ManagerMainWindow(QtGui.QMainWindow,Ui_MainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)

#class ModuleList(QtCore.AbstractItemModel):
#    def __init__(self):
#        super().__init__()
#
#class ModuleItemDelegate(QtGui.QAbstractItemDelegate):
#    def __init__(self):
#        super().__init__()


