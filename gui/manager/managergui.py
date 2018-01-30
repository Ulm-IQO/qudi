# -*- coding: utf-8 -*-
""" This module contains a GUI through which the Manager core class can be controlled.
It can load and reload modules, show the configuration, and re-open closed windows.

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

import core.logger
import logging
import numpy as np
import os

from collections import OrderedDict
from core.module import StatusVar
from core.util.modules import get_main_dir
from .errordialog import ErrorDialog
from gui.guibase import GUIBase
from qtpy import QtCore, QtWidgets, uic
from qtpy.QtGui import QPalette
from qtpy.QtWidgets import QWidget

try:
    from qtconsole.inprocess import QtInProcessKernelManager
except ImportError:
    from IPython.qt.inprocess import QtInProcessKernelManager

try:
    from git import Repo
except:
    pass

try:
    import pyqtgraph as pg
    _has_pyqtgraph = True
except:
    _has_pyqtgraph = False

# Rather than import the ui*.py file here, the ui*.ui file itself is
# loaded by uic.loadUI in the QtGui classes below.


class ManagerGui(GUIBase):

    """This class provides a GUI to the Qudi manager.

      @signal sigStartAll: sent when all modules should be loaded
      @signal str str sigStartThis: load a specific module
      @signal str str sigReloadThis reload a specific module from Python code
      @signal str str sigStopThis: stop all actions of a module and remove
                                   references
      It supports module loading, reloading, logging and other
      administrative tasks.
    """

    # status vars
    consoleFontSize = StatusVar('console_font_size', 10)

    # signals
    sigStartAll = QtCore.Signal()
    sigStartModule = QtCore.Signal(str, str)
    sigReloadModule = QtCore.Signal(str, str)
    sigCleanupStatus = QtCore.Signal(str, str)
    sigStopModule = QtCore.Signal(str, str)
    sigLoadConfig = QtCore.Signal(str, bool)
    sigSaveConfig = QtCore.Signal(str)
    sigRealQuit = QtCore.Signal()

    def __init__(self, **kwargs):
        """Create an instance of the module.

          @param object manager:
          @param str name:
          @param dict config:
        """
        super().__init__(**kwargs)
        self.modlist = list()
        self.modules = set()

    def on_activate(self):
        """ Activation method called on change to active state.

        This method creates the Manager main window.
        """
        if _has_pyqtgraph:
            # set background of pyqtgraph
            testwidget = QWidget()
            testwidget.ensurePolished()
            bgcolor = testwidget.palette().color(QPalette.Normal,
                                                 testwidget.backgroundRole())
            # set manually the background color in hex code according to our
            # color scheme:
            pg.setConfigOption('background', bgcolor)

            # opengl usage
            if 'useOpenGL' in self._manager.tree['global']:
                pg.setConfigOption('useOpenGL',
                                   self._manager.tree['global']['useOpenGL'])
        self._mw = ManagerMainWindow()
        self.restoreWindowPos(self._mw)
        self.errorDialog = ErrorDialog(self)
        self._about = AboutDialog()
        version = self.getSoftwareVersion()
        configFile = self._manager.configFile
        self._about.label.setText(
            '<a href=\"https://github.com/Ulm-IQO/qudi/commit/{0}\"'
            ' style=\"color: cyan;\"> {0} </a>, on branch {1}.'.format(
                version[0], version[1]))
        self.versionLabel = QtWidgets.QLabel()
        self.versionLabel.setText(
            '<a href=\"https://github.com/Ulm-IQO/qudi/commit/{0}\"'
            ' style=\"color: cyan;\"> {0} </a>,'
            ' on branch {1}, configured from {2}'.format(
                version[0], version[1], configFile))
        self.versionLabel.setOpenExternalLinks(True)
        self._mw.statusBar().addWidget(self.versionLabel)
        # Connect up the buttons.
        self._mw.actionQuit.triggered.connect(self._manager.quit)
        self._mw.actionLoad_configuration.triggered.connect(self.getLoadFile)
        self._mw.actionReload_current_configuration.triggered.connect(self.reloadConfig)
        self._mw.actionSave_configuration.triggered.connect(self.getSaveFile)
        self._mw.action_Load_all_modules.triggered.connect(self._manager.startAllConfiguredModules)
        self._mw.actionAbout_Qt.triggered.connect(QtWidgets.QApplication.aboutQt)
        self._mw.actionAbout_Qudi.triggered.connect(self.showAboutQudi)
        self._mw.actionReset_to_default_layout.triggered.connect(self.resetToDefaultLayout)

        self._manager.sigShowManager.connect(self.show)
        self._manager.sigConfigChanged.connect(self.updateConfigWidgets)
        self._manager.sigModulesChanged.connect(self.updateConfigWidgets)
        self._manager.sigShutdownAcknowledge.connect(self.promptForShutdown)
        # Log widget
        self._mw.logwidget.setManager(self._manager)
        for loghandler in logging.getLogger().handlers:
            if isinstance(loghandler, core.logger.QtLogHandler):
                loghandler.sigLoggedMessage.connect(self.handleLogEntry)
        # Module widgets
        self.sigStartModule.connect(self._manager.startModule)
        self.sigReloadModule.connect(self._manager.restartModuleRecursive)
        self.sigCleanupStatus.connect(self._manager.removeStatusFile)
        self.sigStopModule.connect(self._manager.deactivateModule)
        self.sigLoadConfig.connect(self._manager.loadConfig)
        self.sigSaveConfig.connect(self._manager.saveConfig)
        self.sigRealQuit.connect(self._manager.realQuit)
        # Module state display
        self.checkTimer = QtCore.QTimer()
        self.checkTimer.start(1000)
        self.updateGUIModuleList()
        # IPython console widget
        self.startIPython()
        self.updateIPythonModuleList()
        self.startIPythonWidget()
        # thread widget
        self._mw.threadWidget.threadListView.setModel(self._manager.tm)
        # remote widget
        # hide remote menu item if rpyc is not available
        self._mw.actionRemoteView.setVisible(self._manager.rm is not None)
        if (self._manager.rm is not None):
            self._mw.remoteWidget.remoteModuleListView.setModel(self._manager.rm.remoteModules)
            if (self._manager.remote_server):
                self._mw.remoteWidget.hostLabel.setText('Server URL:')
                self._mw.remoteWidget.portLabel.setText(
                    'rpyc://{0}:{1}/'.format(self._manager.rm.server.host,
                                             self._manager.rm.server.port))
                self._mw.remoteWidget.sharedModuleListView.setModel(
                    self._manager.rm.sharedModules)
            else:
                self._mw.remoteWidget.hostLabel.setVisible(False)
                self._mw.remoteWidget.portLabel.setVisible(False)
                self._mw.remoteWidget.sharedModuleListView.setVisible(False)

        self._mw.configDisplayDockWidget.hide()
        self._mw.remoteDockWidget.hide()
        self._mw.threadDockWidget.hide()
        self._mw.show()

    def on_deactivate(self):
        """Close window and remove connections.
        """
        self.stopIPythonWidget()
        self.stopIPython()
        self.checkTimer.stop()
        if len(self.modlist) > 0:
            self.checkTimer.timeout.disconnect()
        self.sigStartModule.disconnect()
        self.sigReloadModule.disconnect()
        self.sigStopModule.disconnect()
        self.sigLoadConfig.disconnect()
        self.sigSaveConfig.disconnect()
        self._mw.actionQuit.triggered.disconnect()
        self._mw.actionLoad_configuration.triggered.disconnect()
        self._mw.actionSave_configuration.triggered.disconnect()
        self._mw.action_Load_all_modules.triggered.disconnect()
        self._mw.actionAbout_Qt.triggered.disconnect()
        self._mw.actionAbout_Qudi.triggered.disconnect()
        self.saveWindowPos(self._mw)
        self._mw.close()

    def show(self):
        """Show the window and bring it t the top.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def showAboutQudi(self):
        """Show a dialog with details about Qudi.
        """
        self._about.show()

    @QtCore.Slot(bool, bool)
    def promptForShutdown(self, locked, broken):
        """ Display a dialog, asking the user to confirm shutdown. """
        text = "Some modules are locked right now, really quit?"
        result = QtWidgets.QMessageBox.question(
            self._mw,
            'Qudi: Really Quit?',
            text,
            QtWidgets.QMessageBox.Yes,
            QtWidgets.QMessageBox.No
        )
        if result == QtWidgets.QMessageBox.Yes:
            self.sigRealQuit.emit()

    def resetToDefaultLayout(self):
        """ Return the dockwidget layout and visibility to its default state """
        self._mw.configDisplayDockWidget.setVisible(False)
        self._mw.consoleDockWidget.setVisible(True)
        self._mw.remoteDockWidget.setVisible(False)
        self._mw.threadDockWidget.setVisible(False)
        self._mw.logDockWidget.setVisible(True)

        self._mw.actionConfigurationView.setChecked(False)
        self._mw.actionConsoleView.setChecked(True)
        self._mw.actionRemoteView.setChecked(False)
        self._mw.actionThreadsView.setChecked(False)
        self._mw.actionLogView.setChecked(True)

        self._mw.configDisplayDockWidget.setFloating(False)
        self._mw.consoleDockWidget.setFloating(False)
        self._mw.remoteDockWidget.setFloating(False)
        self._mw.threadDockWidget.setFloating(False)
        self._mw.logDockWidget.setFloating(False)

        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8), self._mw.configDisplayDockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(2), self._mw.consoleDockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8), self._mw.remoteDockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8), self._mw.threadDockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8), self._mw.logDockWidget)

    def handleLogEntry(self, entry):
        """ Forward log entry to log widget and show an error popup if it is
            an error message.

            @param dict entry: Log entry
        """
        self._mw.logwidget.addEntry(entry)
        if entry['level'] == 'error' or entry['level'] == 'critical':
            self.errorDialog.show(entry)

    def startIPython(self):
        """ Create an IPython kernel manager and kernel.
            Add modules to its namespace.
        """
        # make sure we only log errors and above from ipython
        logging.getLogger('ipykernel').setLevel(logging.WARNING)
        self.log.debug('IPy activation in thread {0}'.format(
            QtCore.QThread.currentThreadId()))
        self.kernel_manager = QtInProcessKernelManager()
        self.kernel_manager.start_kernel()
        self.kernel = self.kernel_manager.kernel
        self.namespace = self.kernel.shell.user_ns
        self.namespace.update({
            'np': np,
            'config': self._manager.tree['defined'],
            'manager': self._manager
        })
        if _has_pyqtgraph:
            self.namespace['pg'] = pg
        self.updateIPythonModuleList()
        self.kernel.gui = 'qt4'
        self.log.info('IPython has kernel {0}'.format(
            self.kernel_manager.has_kernel))
        self.log.info('IPython kernel alive {0}'.format(
            self.kernel_manager.is_alive()))
        self._manager.sigModulesChanged.connect(self.updateIPythonModuleList)

    def startIPythonWidget(self):
        """ Create an IPython console widget and connect it to an IPython
        kernel.
        """
        if (_has_pyqtgraph):
            banner_modules = 'The numpy and pyqtgraph modules have already ' \
                             'been imported as ''np'' and ''pg''.'
        else:
            banner_modules = 'The numpy module has already been imported ' \
                             'as ''np''.'
        banner = """
This is an interactive IPython console. {0}
Configuration is in 'config', the manager is 'manager' and all loaded modules are in this namespace with their configured name.
View the current namespace with dir().
Go, play.
""".format(banner_modules)
        self._mw.consolewidget.banner = banner
        # font size
        self.consoleSetFontSize(self.consoleFontSize)
        # settings
        self._csd = ConsoleSettingsDialog()
        self._csd.accepted.connect(self.consoleApplySettings)
        self._csd.rejected.connect(self.consoleKeepSettings)
        self._csd.buttonBox.button(
            QtWidgets.QDialogButtonBox.Apply).clicked.connect(
                self.consoleApplySettings)
        self._mw.actionConsoleSettings.triggered.connect(self._csd.exec_)
        self.consoleKeepSettings()

        self._mw.consolewidget.kernel_manager = self.kernel_manager
        self._mw.consolewidget.kernel_client = \
            self._mw.consolewidget.kernel_manager.client()
        self._mw.consolewidget.kernel_client.start_channels()
        # the linux style theme which is basically the monokai theme
        self._mw.consolewidget.set_default_style(colors='linux')

    def stopIPython(self):
        """ Stop the IPython kernel.
        """
        self.log.debug('IPy deactivation: {0}'.format(QtCore.QThread.currentThreadId()))
        self.kernel_manager.shutdown_kernel()

    def stopIPythonWidget(self):
        """ Disconnect the IPython widget from the kernel.
        """
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
                newNamespace[module] = self._manager.tree[
                    'loaded'][base][module]
        discard = self.modules - currentModules
        self.namespace.update(newNamespace)
        for module in discard:
            self.namespace.pop(module, None)
        self.modules = currentModules

    def consoleKeepSettings(self):
        """ Write old values into config dialog.
        """
        self._csd.fontSizeBox.setProperty('value', self.consoleFontSize)

    def consoleApplySettings(self):
        """ Apply values from config dialog to console.
        """
        self.consoleSetFontSize(self._csd.fontSizeBox.value())

    def consoleSetFontSize(self, fontsize):
        self._mw.consolewidget.font_size = fontsize
        self.consoleFontSize = fontsize
        self._mw.consolewidget.reset_font()

    def updateConfigWidgets(self):
        """ Clear and refill the tree widget showing the configuration.
        """
        self.fillTreeWidget(self._mw.treeWidget, self._manager.tree)

    def updateGUIModuleList(self):
        """ Clear and refill the module list widget
        """
        # self.clearModuleList(self)
        self.fillModuleList(self._mw.guilayout, 'gui')
        self.fillModuleList(self._mw.logiclayout, 'logic')
        self.fillModuleList(self._mw.hwlayout, 'hardware')

    def fillModuleList(self, layout, base):
        """ Fill the module list widget with module widgets for defined gui
            modules.

          @param QLayout layout: layout of th module list widget where
                                 module widgest should be addad
          @param str base: module category to fill
        """
        for module in self._manager.tree['defined'][base]:
            if module not in self._manager.tree['global']['startup']:
                widget = ModuleListItem(self._manager, base, module)
                self.modlist.append(widget)
                layout.addWidget(widget)
                widget.sigLoadThis.connect(self.sigStartModule)
                widget.sigReloadThis.connect(self.sigReloadModule)
                widget.sigDeactivateThis.connect(self.sigStopModule)
                widget.sigCleanupStatus.connect(self.sigCleanupStatus)
                self.checkTimer.timeout.connect(widget.checkModuleState)

    def fillTreeItem(self, item, value):
        """ Recursively fill a QTreeWidgeItem with the contents from a
            dictionary.

          @param QTreeWidgetItem item: the widget item to fill
          @param (dict, list, etc) value: value to fill in
        """
        item.setExpanded(True)
        if type(value) is OrderedDict or type(value) is dict:
            for key in value:
                child = QtWidgets.QTreeWidgetItem()
                child.setText(0, key)
                item.addChild(child)
                self.fillTreeItem(child, value[key])
        elif type(value) is list:
            for val in value:
                child = QtWidgets.QTreeWidgetItem()
                item.addChild(child)
                if type(val) is dict:
                    child.setText(0, '[dict]')
                    self.fillTreeItem(child, val)
                elif type(val) is OrderedDict:
                    child.setText(0, '[odict]')
                    self.fillTreeItem(child, val)
                elif type(val) is list:
                    child.setText(0, '[list]')
                    self.fillTreeItem(child, val)
                else:
                    child.setText(0, str(val))
                child.setExpanded(True)
        else:
            child = QtWidgets.QTreeWidgetItem()
            child.setText(0, str(value))
            item.addChild(child)

    def getSoftwareVersion(self):
        """ Try to determine the software version in case the program is in
            a git repository.
        """
        try:
            repo = Repo(get_main_dir())
            branch = repo.active_branch
            rev = str(repo.head.commit)
            return (rev, str(branch))

        except Exception as e:
            print('Could not get git repo because:', e)
            return ('unknown', -1)

    def fillTreeWidget(self, widget, value):
        """ Fill a QTreeWidget with the content of a dictionary

          @param QTreeWidget widget: the tree widget to fill
          @param dict,OrderedDict value: the dictionary to fill in
        """
        widget.clear()
        self.fillTreeItem(widget.invisibleRootItem(), value)

    def reloadConfig(self):
        """  Reload the current config. """

        reply = QtWidgets.QMessageBox.question(
            self._mw,
            'Restart',
            'Do you want to restart the current configuration?',
            QtWidgets.QMessageBox.Yes,
            QtWidgets.QMessageBox.No
        )

        configFile = self._manager._getConfigFile()
        restart = (reply == QtWidgets.QMessageBox.Yes)
        self.sigLoadConfig.emit(configFile, restart)

    def getLoadFile(self):
        """ Ask the user for a file where the configuration should be loaded
            from
        """
        defaultconfigpath = os.path.join(get_main_dir(), 'config')
        filename = QtWidgets.QFileDialog.getOpenFileName(
            self._mw,
            'Load Configration',
            defaultconfigpath,
            'Configuration files (*.cfg)')[0]
        if filename != '':
            reply = QtWidgets.QMessageBox.question(
                self._mw,
                'Restart',
                'Do you want to restart to use the configuration?',
                QtWidgets.QMessageBox.Yes,
                QtWidgets.QMessageBox.No
            )
            restart = (reply == QtWidgets.QMessageBox.Yes)
            self.sigLoadConfig.emit(filename, restart)

    def getSaveFile(self):
        """ Ask the user for a file where the configuration should be saved
            to.
        """
        defaultconfigpath = os.path.join(get_main_dir(), 'config')
        filename = QtWidgets.QFileDialog.getSaveFileName(
            self._mw,
            'Save Configration',
            defaultconfigpath,
            'Configuration files (*.cfg)')[0]
        if filename != '':
            self.sigSaveConfig.emit(filename)


class ManagerMainWindow(QtWidgets.QMainWindow):

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
        # this really cannot be done in Qt designer, you cannot set a layout
        # on an empty widget
        self.guilayout = QtWidgets.QVBoxLayout(self.guiscroll)
        self.logiclayout = QtWidgets.QVBoxLayout(self.logicscroll)
        self.hwlayout = QtWidgets.QVBoxLayout(self.hwscroll)


class AboutDialog(QtWidgets.QDialog):

    """ This class represents the Qudi About dialog.
    """

    def __init__(self):
        """ Create Qudi About Dialog.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_about.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)


class ConsoleSettingsDialog(QtWidgets.QDialog):

    """ Create the SettingsDialog window, based on the corresponding *.ui
        file.
    """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_console_settings.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)


class ModuleListItem(QtWidgets.QFrame):

    """ This class represents a module widget in the Qudi module list.

      @signal str str sigLoadThis: gives signal with base and name of module
                                   to be loaded
      @signal str str sigReloadThis: gives signal with base and name of
                                     module to be reloaded
      @signal str str sigStopThis: gives signal with base and name of module
                                   to be deactivated
    """

    sigLoadThis = QtCore.Signal(str, str)
    sigReloadThis = QtCore.Signal(str, str)
    sigDeactivateThis = QtCore.Signal(str, str)
    sigCleanupStatus = QtCore.Signal(str, str)

    def __init__(self, manager, basename, modulename):
        """ Create a module widget.

          @param str basename: module category
          @param str modulename: unique module name
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_module_widget.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)

        self.manager = manager
        self.name = modulename
        self.base = basename

        self.loadButton.setText('Load {0}'.format(self.name))
        # connect buttons
        self.loadButton.clicked.connect(self.loadButtonClicked)
        self.reloadButton.clicked.connect(self.reloadButtonClicked)
        self.deactivateButton.clicked.connect(self.deactivateButtonClicked)
        self.cleanupButton.clicked.connect(self.cleanupButtonClicked)

    def loadButtonClicked(self):
        """ Send signal to load and activate this module.
        """
        self.sigLoadThis.emit(self.base, self.name)
        
        # Instant return to checked to prevent visual lag before checkModuleState completes
        self.loadButton.setChecked(True)

    def reloadButtonClicked(self):
        """ Send signal to reload this module.
        """
        self.sigReloadThis.emit(self.base, self.name)

    def deactivateButtonClicked(self):
        """ Send signal to deactivate this module.
        """
        self.sigDeactivateThis.emit(self.base, self.name)

    def cleanupButtonClicked(self):
        """ Send signal to deactivate this module.
        """
        self.sigCleanupStatus.emit(self.base, self.name)

    def checkModuleState(self):
        """ Get the state of this module and update visual indications in the GUI.

            Modules cannot be unloaded, but they can be deactivated.

            Once loaded, the "load <module>" button will remain checked and its text
            will be updated to indicate that loading is no longer possible.
        """
        state = ''
        if self.statusLabel.text() != 'exception, cannot get state':
            try:
                if (self.base in self.manager.tree['loaded']
                        and self.name in self.manager.tree['loaded'][self.base]):
                    state = self.manager.tree['loaded'][self.base][self.name].module_state()

                    if state != 'deactivated':
                        self.reloadButton.setEnabled(True)
                        self.deactivateButton.setEnabled(True)
                        self.cleanupButton.setEnabled(False)
                        self.loadButton.setChecked(True)

                        if self.base == 'gui':
                            self.loadButton.setText('Show {0}'.format(self.name))
                        else:
                            self.loadButton.setText(self.name)
                    else:
                        self.reloadButton.setEnabled(True)
                        self.deactivateButton.setEnabled(False)
                        self.cleanupButton.setEnabled(True)
                        self.loadButton.setChecked(True)

                        self.loadButton.setText('Activate {0}'.format(self.name))

                else:
                    state = 'not loaded'
                    self.reloadButton.setEnabled(False)
                    self.deactivateButton.setEnabled(False)
                    self.cleanupButton.setEnabled(True)
            except:
                state = 'exception, cannot get state'
                self.reloadButton.setEnabled(False)
                self.deactivateButton.setEnabled(True)
                self.cleanupButton.setEnabled(True)

            self.statusLabel.setText(state)
