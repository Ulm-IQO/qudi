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

from gui.guibase import GUIBase
from pyqtgraph.Qt import QtCore, QtGui, uic
from IPython.qt.inprocess import QtInProcessKernelManager
from collections import OrderedDict
import svn.local
import threading
import pyqtgraph as pg
import numpy as np
import os

# Rather than import the ui*.py file here, the ui*.ui file itself is loaded by uic.loadUI in the QtGui classes below.


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
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, c_dict)
        self.modlist = list()
        self.modules = set()

    def activation(self, e=None):
        """ Activation method called on change to active state.
            
          @param e: Fysom state change information

            This method creates the Manager main window.
        """
        self._mw = ManagerMainWindow()
        self.restoreWindowPos(self._mw)
        self._about = AboutDialog()
        version = self.getSoftwareVersion()
        self._about.label.setText('<a href=\"{0}\" style=\"color: cyan;\"> {0} </a>, Revision {1}.'.format(version[0], version[1]))
        self.versionLabel = QtGui.QLabel()
        self.versionLabel.setText('<a href=\"{0}\" style=\"color: cyan;\"> {0} </a>, Revision {1}.'.format(version[0], version[1]))
        self.versionLabel.setOpenExternalLinks(True)
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

        self._manager.sigShowManager.connect(self.show)
        self._manager.sigConfigChanged.connect(self.updateConfigWidgets)
        self._manager.sigModulesChanged.connect(self.updateConfigWidgets)
        self._manager.logger.sigLoggedMessage.connect(self._mw.logwidget.addEntry)
        
        self.sigStartModule.connect(self._manager.startModule)
        self.sigReloadModule.connect(self._manager.restartModuleSimple)
        self.sigStopModule.connect(self._manager.deactivateModule)
        self.sigLoadConfig.connect(self._manager.loadConfig)
        self.sigSaveConfig.connect(self._manager.saveConfig)

        # Module state display
        self.checkTimer = QtCore.QTimer()
        self.checkTimer.start(1000)
        self.updateModuleList()

        # IPython console
        self.startIPython()
        self.updateIPythonModuleList()
        self.startIPythonWidget()

        self._mw.config_display_dockWidget.hide()
        self._mw.menuUtilities.addAction(self._mw.config_display_dockWidget.toggleViewAction() )
        self._mw.show()

    def deactivation(self,e):
        """Close window and remove connections.

          @param object eFysom state change notification
        """
        self.stopIPythonWidget()
        self.stopIPython()
        self.checkTimer.stop()
        self.checkTimer.timeout.disconnect()
        self.sigStartModule.disconnect()
        self.sigReloadModule.disconnect()
        self.sigStopModule.disconnect()
        self.sigLoadConfig.disconnect()
        self.sigSaveConfig.disconnect()
        self._mw.loadAllButton.clicked.disconnect()
        self._mw.actionQuit.triggered.disconnect()
        self._mw.actionLoad_configuration.triggered.disconnect()
        self._mw.actionSave_configuration.triggered.disconnect()
        self._mw.action_Load_all_modules.triggered.disconnect()
        self._mw.actionLog.triggered.disconnect()
        self._mw.actionConsole.triggered.disconnect()
        self._mw.actionAbout_Qt.triggered.disconnect()
        self._mw.actionAbout_QuDi.triggered.disconnect()
        self.saveWindowPos(self._mw)
        self._mw.close()

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

    def startIPython(self):
        self.logMsg('IPy activation in thread {0}'.format(threading.get_ident()), msgType='thread')
        self.kernel_manager = QtInProcessKernelManager()
        self.kernel_manager.start_kernel()
        self.kernel = self.kernel_manager.kernel
        self.namespace = self.kernel.shell.user_ns
        self.namespace.update({
            'pg': pg,
            'np': np,
            'config': self._manager.tree['defined'],
            'manager': self._manager
            })
        self.updateModuleList()
        self.kernel.gui = 'qt4'
        self.logMsg('IPython has kernel {0}'.format(self.kernel_manager.has_kernel))
        self.logMsg('IPython kernel alive {0}'.format(self.kernel_manager.is_alive()))
        self._manager.sigModulesChanged.connect(self.updateModuleList)

    def startIPythonWidget(self):
        banner = """
This is an interactive IPython console. The numpy and pyqtgraph modules have already been imported as 'np' and 'pg'.
Configuration is in 'config', the manager is 'manager' and all loaded modules are in this namespace with their configured name.
View the current namespace with dir().
Go, play.
"""
        self._mw.consolewidget.banner = banner
        self._mw.consolewidget.kernel_manager = self.kernel_manager
        self._mw.consolewidget.kernel_client = self._mw.consolewidget.kernel_manager.client()
        self._mw.consolewidget.kernel_client.start_channels()
        # the linux style theme which is basically the monokai theme
        self._mw.consolewidget.set_default_style(colors='linux')

    def stopIPython(self):
        self.logMsg('IPy deactivation'.format(threading.get_ident()), msgType='thread')
        self.kernel_manager.shutdown_kernel()

    def stopIPythonWidget(self):
        self._mw.consolewidget.kernel_client.stop_channels()

    def updateIPythonModuleList(self):
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
            widget = ModuleListItem(self._manager, base, module)
            self.modlist.append(widget)
            layout.addWidget(widget)
            widget.sigActivateThis.connect(self.sigStartModule)
            widget.sigReloadThis.connect(self.sigReloadModule)
            self.checkTimer.timeout.connect(widget.checkModuleState)

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


class ManagerMainWindow(QtGui.QMainWindow):
    """ This class represents the Manager Window.
    """
    def __init__(self):
        """ Create the Manager Window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_manager_window.ui')

        # Load it
        super(ManagerMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

        # Set up the layout
        # this really cannot be done in Qt designer, you cannot set a layout on an empty widget
        self.guilayout = QtGui.QVBoxLayout(self.guiscroll)
        self.logiclayout = QtGui.QVBoxLayout(self.logicscroll)
        self.hwlayout = QtGui.QVBoxLayout(self.hwscroll)

class AboutDialog(QtGui.QDialog):
    """ This class represents the QuDi About dialog.
    """
    def __init__(self):
        """ Create QuDi About Dialog.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'aboutdialog.ui')

        # Load it
        super(AboutDialog, self).__init__()
        uic.loadUi(ui_file, self)

class ModuleListItem(QtGui.QFrame):
    """ This class represents a module widget in the QuDi module list.

      @signal str str sigActivateThis: gives signal with base and name of module to be loaded
      @signal str str sigReloadThis: gives signal with base and name of module to be reloaded
      @signal str str sigStopThis: gives signal with base and name of module to be deactivated
    """

    sigActivateThis = QtCore.Signal(str, str)
    sigReloadThis = QtCore.Signal(str, str)
    sigStopThis = QtCore.Signal(str, str)

    def __init__(self, manager, basename, modulename):
        """ Create a module widget.

          @param str basename: module category
          @param str modulename: unique module name
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_module_widget.ui')

        # Load it
        super(ModuleListItem, self).__init__()
        uic.loadUi(ui_file, self)

        # FIXME: comments
        self.manager = manager
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

    def checkModuleState(self):
        state = ''
        try:
            if self.base in self.manager.tree['loaded'] and self.name in self.manager.tree['loaded'][self.base]:
                state = self.manager.tree['loaded'][self.base][self.name].getState()
            else:
                state = 'not loaded'
        except:
            self.manager.logger.logExc('Exception while querying module state.')
            state = 'exception, cannot get state'
        
        self.statusLabel.setText(state)

