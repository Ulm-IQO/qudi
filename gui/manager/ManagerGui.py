# -*- coding: utf-8 -*-
""" This module contains a GUI through which the Manager core class can be controlled.
It can load and reload modules, show the configuration, and re-open closed windows.
"""

from core.Base import Base
from pyqtgraph.Qt import QtCore, QtGui
from .ManagerWindowTemplate import Ui_MainWindow
from .ModuleWidgetTemplate import Ui_ModuleWidget
from .aboutdialog import Ui_Dialog
from collections import OrderedDict

class ManagerGui(Base):
    """This class provides a GUI to the QuDi manager.

      @signal sigStartAll: sent when all modules should be loaded
      @signal str str sigStartThis: load a specific module
      @signal str str sigReloadThis reload a specific module from Python code
      @signal str str sigStopThis: stop all actions of a module and remove references

        It supports module loading, reloading, logging and other administrative tasks.
    """
    sigStartAll = QtCore.Signal()
    sigStartThis = QtCore.Signal(str, str)
    sigReloadThis = QtCore.Signal(str, str)
    sigStopThis = QtCore.Signal(str, str)

    def __init__(self, manager, name, config, **kwargs):
        """Create an instance of the module.

          @param object manager:
          @param str name:
          @param dict config:
        """
        c_dict = {'onactivate': self.activation}
        Base.__init__(self, manager, name, config, c_dict)
        self.modlist = list()

    def activation(self, e=None):
        """ Activation method called on change to active state.
            
          @param e: Fysom state change information

            This method creates the Manager main window.
        """
        self._mw = ManagerMainWindow()
        self._about = AboutDialog()
        # Connect up the buttons.
        self._mw.loadAllButton.clicked.connect(self._manager.startAllConfiguredModules)
        self._mw.actionQuit.triggered.connect(self._manager.quit)
        self._mw.action_Load_all_modules.triggered.connect(self._manager.startAllConfiguredModules)
        self._mw.actionLog.triggered.connect(lambda: self._manager.sigShowLog.emit())
        self._mw.actionConsole.triggered.connect(lambda: self._manager.sigShowConsole.emit())
        self._mw.actionAbout_Qt.triggered.connect(QtGui.QApplication.aboutQt)
        self._mw.actionAbout_QuDi.triggered.connect(self.showAboutQuDi)
        self._mw.show()
        self._manager.sigShowManager.connect(self.show)
        self._manager.sigConfigChanged.connect(self.updateConfigWidgets)
        self._manager.sigModulesChanged.connect(self.updateConfigWidgets)
        self.sigStartThis.connect(self._manager.startModule)
        self.sigReloadThis.connect(self._manager.restartModuleSimple)
        self.updateModuleList()

    def show(self):
        """Show the window and bring it t the top.
        """
        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def showAboutQuDi(self):
        """Show a dialog with details about QuDi.
        """
        self._about.show()

    def updateConfigWidgets(self):
        """ Clear and refill the tree widget showing the configuration.
        """
        self.fill_tree_widget(self._mw.treeWidget, self._manager.tree)
    
    def updateModuleList(self):
        """ Clear and refill the module list widget
        """
        #self.clearModuleList(self)
        self.fillModuleList(self._mw.guilayout, 'gui')
        self.fillModuleList(self._mw.logiclayout, 'logic')
        self.fillModuleList(self._mw.hwlayout, 'hardware')
        
    def fillModuleList(self, layout, base):
        """ Fill the module list widget with module widgets for defined gui modules.

          @param QLayout layout: layout of th module list widget where module widgest should be addad
          @param str base: module category to fill
        """
        for module in self._manager.tree['defined'][base]:
            widget = ModuleListItem(base, module)
            self.modlist.append(widget)
            layout.addWidget(widget)
            widget.sigActivateThis.connect(self.sigStartThis)
            widget.sigReloadThis.connect(self.sigReloadThis)

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


class ManagerMainWindow(QtGui.QMainWindow, Ui_MainWindow):
    """ This class represents the Manager Window.
    """
    def __init__(self):
        """ Create the Manager Window.
        """
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)
        self.guilayout = QtGui.QVBoxLayout(self.guiscroll)
        self.logiclayout = QtGui.QVBoxLayout(self.logicscroll)
        self.hwlayout = QtGui.QVBoxLayout(self.hwscroll)

class AboutDialog(QtGui.QDialog, Ui_Dialog):
    """ This class represents the QuDi About dialog.
    """
    def __init__(self):
        """ Create QuDi About Dialog.
        """
        QtGui.QDialog.__init__(self)
        self.setupUi(self)

class ModuleListItem(QtGui.QFrame, Ui_ModuleWidget):
    """ This class represents a module widget in the QuDi module list.

      @signal str str sigActivateThis: gives signal with base and name of module to be loaded
      @signal str str sigReloadThis: gives signal with base and name of module to be reloaded
      @signal str str sigStopThis: gives signal with base and name of module to be deactivated
    """

    sigActivateThis = QtCore.Signal(str, str)
    sigReloadThis = QtCore.Signal(str, str)
    sigStopThis = QtCore.Signal(str, str)

    def __init__(self, basename, modulename):
        """ Create a module widget.

          @param str basename: module category
          @param str modulename: unique module name
        """
        super().__init__()
        self.setupUi(self)
        self.name = modulename
        self.base = basename
        self.loadButton.setText('Load {0}'.format(self.name))
        self.loadButton.clicked.connect(self.activateButtonClicked)
        self.reloadButton.clicked.connect(self.reactivateButtonClicked)
        self.unloadButton.clicked.connect(self.stopButtonClicked)

    def activateButtonClicked(self):
        """Send activation singal for module.
        """
        self.sigActivateThis.emit(self.base, self.name)

    def reactivateButtonClicked(self):
        """ Send reload signal for module.
        """
        self.sigReloadThis.emit(self.base, self.name)

    def stopButtonClicked(self):
        """ Send stop singal for module.
        """
        self.sigStopThis.emit(self.base , self.name)

