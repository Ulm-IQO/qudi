# -*- coding: utf-8 -*-
""" This module contains a GUI through which the Manager core class can be controlled.
It can load and reload modules, show the configuration, and re-open closed windows.

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

Copyright (C) 2015 Jan M. Binder jan.binder@uni-ulm.d
"""

from gui.GUIBase import GUIBase
from pyqtgraph.Qt import QtCore, QtGui
from .ManagerWindowTemplate import Ui_MainWindow
from .ModuleWidgetTemplate import Ui_ModuleWidget
from .aboutdialog import Ui_AboutDialog
from collections import OrderedDict
import svn.local
import os

class ManagerGui(GUIBase):
    """This class provides a GUI to the QuDi manager.

      @signal sigStartAll: sent when all modules should be loaded
      @signal str str sigStartThis: load a specific module
      @signal str str sigReloadThis reload a specific module from Python code
      @signal str str sigStopThis: stop all actions of a module and remove references

        It supports module loading, reloading, logging and other administrative tasks.
    """
    sigStartAll = QtCore.Signal()
    sigStartModule = QtCore.Signal(str, str)
    sigReloadModule = QtCore.Signal(str, str)
    sigStopModule = QtCore.Signal(str, str)
    sigLoadConfig = QtCore.Signal(str)
    sigSaveConfig = QtCore.Signal(str)

    def __init__(self, manager, name, config, **kwargs):
        """Create an instance of the module.

          @param object manager:
          @param str name:
          @param dict config:
        """
        c_dict = {'onactivate': self.activation}
        super().__init__(manager, name, config, c_dict)
        self.modlist = list()

    def activation(self, e=None):
        """ Activation method called on change to active state.
            
          @param e: Fysom state change information

            This method creates the Manager main window.
        """
        self._mw = ManagerMainWindow()
        self._about = AboutDialog()
        version = self.getSoftwareVersion()
        self._about.label.setText('<a href=\"{0}\" style=\"color: cyan;\"> {0} </a>, Revision {1}.'.format(version[0], version[1]))
        self.versionLabel = QtGui.QLabel()
        self.versionLabel.setText('<a href=\"{0}\" style=\"color: cyan;\"> {0} </a>, Revision {1}.'.format(version[0], version[1]))
        self._mw.statusBar().addWidget(self.versionLabel)
        # Connect up the buttons.
        self._mw.loadAllButton.clicked.connect(self._manager.startAllConfiguredModules)
        self._mw.actionQuit.triggered.connect(self._manager.quit)
        self._mw.actionLoad_configuration.triggered.connect(self.getLoadFile)
        self._mw.actionSave_configuration.triggered.connect(self.getSaveFile)
        self._mw.action_Load_all_modules.triggered.connect(self._manager.startAllConfiguredModules)
        self._mw.actionLog.triggered.connect(lambda: self._manager.sigShowLog.emit())
        self._mw.actionConsole.triggered.connect(lambda: self._manager.sigShowConsole.emit())
        self._mw.actionAbout_Qt.triggered.connect(QtGui.QApplication.aboutQt)
        self._mw.actionAbout_QuDi.triggered.connect(self.showAboutQuDi)
        self._mw.show()
        self._manager.sigShowManager.connect(self.show)
        self._manager.sigConfigChanged.connect(self.updateConfigWidgets)
        self._manager.sigModulesChanged.connect(self.updateConfigWidgets)
        self.sigStartModule.connect(self._manager.startModule)
        self.sigReloadModule.connect(self._manager.restartModuleSimple)
        self.sigStopModule.connect(self._manager.stopModule)
        self.sigLoadConfig.connect(self._manager.loadConfig)
        self.sigSaveConfig.connect(self._manager.saveConfig)
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
        self.fillTreeWidget(self._mw.treeWidget, self._manager.tree)
    
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
            widget.sigActivateThis.connect(self.sigStartModule)
            widget.sigReloadThis.connect(self.sigReloadModule)

    def fillTreeItem(self, item, value):
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
                self.fillTreeItem(child, value[key])
        elif type(value) is list:
            for val in value:
                child = QtGui.QTreeWidgetItem()
                item.addChild(child)
                if type(val) is dict:
                    child.setText(0, '[dict]')
                    self.fillTreeItem(child,val)
                elif type(val) is OrderedDict:
                    child.setText(0, '[odict]')
                    self.fillTreeItem(child,val)
                elif type(val) is list:
                    child.setText(0, '[list]')
                    self.fillTreeItem(child,val)
                else:
                    child.setText(0, str(val))
                child.setExpanded(True)
        else:
            child = QtGui.QTreeWidgetItem()
            child.setText(0, str(value))
            item.addChild(child)

    def getSoftwareVersion(self):
        try:
            repo = svn.local.LocalClient('.')
            info = repo.info()
            return (info['url'], info['commit#revision'])
        except:
            return ('unknown', -1)
            

    def fillTreeWidget(self, widget, value):
        """ Fill a QTreeWidget with the content of a dictionary
           
          @param QTreeWidget widget: the tree widget to fill
          @param dict,OrderedDict value: the dictionary to fill in
        """
        widget.clear()
        self.fillTreeItem(widget.invisibleRootItem(), value)

    def getLoadFile(self):
        defaultconfigpath = os.path.join(self.get_main_dir(), 'config')
        filename = QtGui.QFileDialog.getOpenFileName(
                self._mw,
                'Load Configration',
                defaultconfigpath , 
                'Configuration files (*.cfg)')
        if filename != '':
            self.sigLoadConfig.emit(filename)

    def getSaveFile(self):
        defaultconfigpath = os.path.join(self.get_main_dir(), 'config')
        filename = QtGui.QFileDialog.getSaveFileName(
                self._mw,
                'Save Configration',
                defaultconfigpath , 
                'Configuration files (*.cfg)')
        if filename != '':
            self.sigSaveConfig.emit(filename)


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

class AboutDialog(QtGui.QDialog, Ui_AboutDialog):
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
        if self.base == 'gui':
            self.loadButton.setText('Show {0}'.format(self.name))

    def reactivateButtonClicked(self):
        """ Send reload signal for module.
        """
        self.sigReloadThis.emit(self.base, self.name)

    def stopButtonClicked(self):
        """ Send stop singal for module.
        """
        self.sigStopThis.emit(self.base , self.name)

