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
from core.statusvariable import StatusVar
from core.util.modules import get_main_dir
from .errordialog import ErrorDialog
from .managerwindow import ManagerMainWindow
from .moduleframewidget import ModuleFrameWidget
from gui.guibase import GUIBase
from qtpy import QtCore, QtWidgets, QtGui

try:
    from qtconsole.inprocess import QtInProcessKernelManager
except ImportError:
    from IPython.qt.inprocess import QtInProcessKernelManager

try:
    from git import Repo
except ImportError:
    pass

_has_pyqtgraph = False
# try:
#     import pyqtgraph as pg
#     _has_pyqtgraph = True
# except ImportError:
#     pass


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
    _console_font_size = StatusVar('console_font_size', 10)

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
        self.error_dialog = None
        self.version_label = None
        self._kernel_manager = None
        self._kernel = None
        self._namespace = None
        self._check_timer = None
        self._mw = None

    def on_activate(self):
        """ Activation method called on change to active state.

        This method creates the Manager main window.
        """
        # Configure pyqtgraph (if present)
        if _has_pyqtgraph:
            # test setting background of pyqtgraph
            testwidget = QtWidgets.QWidget()
            testwidget.ensurePolished()
            bgcolor = testwidget.palette().color(QtGui.QPalette.Normal, testwidget.backgroundRole())
            # set manually the background color in hex code according to our color scheme:
            pg.setConfigOption('background', bgcolor)

            # experimental opengl usage
            if 'useOpenGL' in self._manager.tree['global']:
                pg.setConfigOption('useOpenGL', self._manager.tree['global']['useOpenGL'])

        # Create main window and restore position
        self._mw = ManagerMainWindow()
        self.restoreWindowPos(self._mw)
        # Create error dialog for error message popups
        self.error_dialog = ErrorDialog(self)

        # Get qudi version number and configure statusbar and "about qudi" dialog
        version = self.get_qudi_version()
        config_file = self._manager.configFile
        self._mw.about_qudi_dialog.label.setText(
            '<a href=\"https://github.com/Ulm-IQO/qudi/commit/{0}\" style=\"color: cyan;\"> {0} '
            '</a>, on branch {1}.'.format(version[0], version[1]))
        self.version_label = QtWidgets.QLabel()
        self.version_label.setText(
            '<a href=\"https://github.com/Ulm-IQO/qudi/commit/{0}\" style=\"color: cyan;\"> {0} '
            '</a>, on branch {1}, configured from {2}'.format(version[0], version[1], config_file))
        self.version_label.setOpenExternalLinks(True)
        self._mw.statusbar.addWidget(self.version_label)

        # Connect up the main windows actions
        self._mw.action_quit.triggered.connect(self._manager.quit)
        self._mw.action_load_configuration.triggered.connect(self.get_load_file)
        self._mw.action_reload_qudi.triggered.connect(self.reload_qudi)
        self._mw.action_save_configuration.triggered.connect(self.get_save_file)
        self._mw.action_load_all_modules.triggered.connect(self._manager.startAllConfiguredModules)
        self._mw.action_view_default.triggered.connect(self.reset_default_layout)
        # Connect signals from manager
        self._manager.sigShowManager.connect(self.show)
        self._manager.sigConfigChanged.connect(self.update_config_widgets)
        self._manager.sigModulesChanged.connect(self.update_config_widgets)
        self._manager.sigShutdownAcknowledge.connect(self.prompt_shutdown)

        # Log widget
        for loghandler in logging.getLogger().handlers:
            if isinstance(loghandler, core.logger.QtLogHandler):
                loghandler.sigLoggedMessage.connect(self.handle_log_entry)

        # Console settings
        self._mw.console_settings_dialog.accepted.connect(self.console_apply_settings)
        self._mw.console_settings_dialog.rejected.connect(self.console_keep_settings)
        self.console_keep_settings()

        # Connect signals
        self.sigStartModule.connect(self._manager.startModule)
        self.sigReloadModule.connect(self._manager.restartModuleRecursive)
        self.sigCleanupStatus.connect(self._manager.removeStatusFile)
        self.sigStopModule.connect(self._manager.deactivateModule)
        self.sigLoadConfig.connect(self._manager.loadConfig)
        self.sigSaveConfig.connect(self._manager.saveConfig)
        self.sigRealQuit.connect(self._manager.realQuit)

        # Timer for module state display
        self._check_timer = QtCore.QTimer()
        self._check_timer.start(1000)
        self.update_gui_module_list()

        # IPython console widget
        self.start_ipython()
        self.update_ipython_module_list()
        self.start_ipython_widget()

        # Configure thread widget
        self._mw.threads_widget.setModel(self._manager.tm)

        # Configure remote widget
        # hide remote menu item if rpyc is not available
        if self._manager.rm is not None:
            self._mw.remote_widget.remote_module_listview.setModel(self._manager.rm.remoteModules)
            if self._manager.remote_server:
                self._mw.remote_widget.host_label.setText('Server URL:')
                self._mw.remote_widget.port_label.setText('rpyc://{0}:{1}/'.format(
                    self._manager.rm.server.host, self._manager.rm.server.port))
                self._mw.remote_widget.shared_module_listview.setModel(
                    self._manager.rm.sharedModules)
            else:
                self._mw.remote_widget.host_label.setVisible(False)
                self._mw.remote_widget.port_label.setVisible(False)
                self._mw.remote_widget.shared_module_listview.setVisible(False)
        else:
            self._mw.action_view_remote.hide()

        self.reset_default_layout()
        self._mw.show()

    def on_deactivate(self):
        """Close window and remove connections.
        """
        self.stop_ipython_widget()
        self.stop_ipython()
        self._check_timer.stop()
        if len(self.modlist) > 0:
            self._check_timer.timeout.disconnect()
        self.sigStartModule.disconnect()
        self.sigReloadModule.disconnect()
        self.sigStopModule.disconnect()
        self.sigLoadConfig.disconnect()
        self.sigSaveConfig.disconnect()
        self._mw.action_quit.triggered.disconnect()
        self._mw.action_load_configuration.triggered.disconnect()
        self._mw.action_save_configuration.triggered.disconnect()
        self._mw.action_load_all_modules.triggered.disconnect()
        self._mw.action_about_qt.triggered.disconnect()
        self._mw.action_about_qudi.triggered.disconnect()
        self.saveWindowPos(self._mw)
        self._mw.close()

    def show(self):
        """Show the window and bring it t the top.
        """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    @QtCore.Slot(bool, bool)
    def prompt_shutdown(self, locked, broken):
        """
        Display a dialog, asking the user to confirm shutdown.
        """
        result = QtWidgets.QMessageBox.question(self._mw,
                                                'Qudi: Really Quit?',
                                                'Some modules are locked right now, really quit?',
                                                QtWidgets.QMessageBox.Yes,
                                                QtWidgets.QMessageBox.No)
        if result == QtWidgets.QMessageBox.Yes:
            self.sigRealQuit.emit()
        return

    def reset_default_layout(self):
        """
        Return the dockwidget layout and visibility to its default state
        """
        self._mw.config_dockwidget.setVisible(False)
        self._mw.console_dockwidget.setVisible(True)
        self._mw.remote_dockwidget.setVisible(False)
        self._mw.threads_dockwidget.setVisible(False)
        self._mw.log_dockwidget.setVisible(True)

        self._mw.config_dockwidget.setFloating(False)
        self._mw.console_dockwidget.setFloating(False)
        self._mw.remote_dockwidget.setFloating(False)
        self._mw.threads_dockwidget.setFloating(False)
        self._mw.log_dockwidget.setFloating(False)

        self._mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self._mw.config_dockwidget)
        self._mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self._mw.log_dockwidget)
        self._mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self._mw.remote_dockwidget)
        self._mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self._mw.threads_dockwidget)
        self._mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._mw.console_dockwidget)
        return

    def handle_log_entry(self, entry):
        """
        Forward log entry to log widget and show an error popup if it is an error message.

        @param dict entry: Log entry
        """
        self._mw.log_widget.add_entry(entry)
        if entry['level'] == 'error' or entry['level'] == 'critical':
            self.error_dialog.show(entry)
        return

    def start_ipython(self):
        """ Create an IPython kernel manager and kernel.
            Add modules to its namespace.
        """
        # make sure we only log errors and above from ipython
        logging.getLogger('ipykernel').setLevel(logging.WARNING)
        self.log.debug('IPython activation in thread {0}'.format(QtCore.QThread.currentThread()))
        self._kernel_manager = QtInProcessKernelManager()
        self._kernel_manager.start_kernel()
        self._kernel = self._kernel_manager.kernel
        self._namespace = self._kernel.shell.user_ns
        self._namespace.update({'np': np,
                                'config': self._manager.tree['defined'],
                                'manager': self._manager})
        if _has_pyqtgraph:
            self._namespace['pg'] = pg
        self.update_ipython_module_list()
        self._kernel.gui = 'qt4'
        self.log.info('IPython has kernel {0}'.format(self._kernel_manager.has_kernel))
        self.log.info('IPython kernel alive {0}'.format(self._kernel_manager.is_alive()))
        self._manager.sigModulesChanged.connect(self.update_ipython_module_list)

    def start_ipython_widget(self):
        """
        Create an IPython console widget and connect it to an IPython kernel.
        """
        if _has_pyqtgraph:
            banner_modules = 'The numpy and pyqtgraph modules have already been imported as "np" ' \
                             'and "pg".'
        else:
            banner_modules = 'The numpy module has already been imported as "np".'
        banner = 'This is an interactive IPython console. {0} Configuration is in "config", the ' \
                 'manager is "manager" and all loaded modules are in this namespace with their ' \
                 'configured name. View the current namespace with dir(). Go, play.' \
                 ''.format(banner_modules)
        self._mw.console_widget.banner = banner
        # font size
        self.console_apply_settings()

        self._mw.console_widget.kernel_manager = self._kernel_manager
        self._mw.console_widget.kernel_client = self._mw.console_widget.kernel_manager.client()
        self._mw.console_widget.kernel_client.start_channels()
        # use the linux style theme which is basically the monokai theme
        self._mw.console_widget.set_default_style(colors='linux')
        return

    def stop_ipython(self):
        """ Stop the IPython kernel.
        """
        self.log.debug('IPython deactivation: {0}'.format(QtCore.QThread.currentThread()))
        self._kernel_manager.shutdown_kernel()

    def stop_ipython_widget(self):
        """ Disconnect the IPython widget from the kernel.
        """
        self._mw.console_widget.kernel_client.stop_channels()

    def update_ipython_module_list(self):
        """
        Remove non-existing modules from namespace, add new modules to namespace,
        update reloaded modules
        """
        current_modules = set()
        new_namespace = dict()
        for base in ('hardware', 'logic', 'gui'):
            for module in self._manager.tree['loaded'][base]:
                current_modules.add(module)
                new_namespace[module] = self._manager.tree['loaded'][base][module]
        discard = self.modules - current_modules
        self._namespace.update(new_namespace)
        for module in discard:
            self._namespace.pop(module, None)
        self.modules = current_modules

    def console_keep_settings(self):
        """ Write old values into config dialog.
        """
        self._mw.console_settings_dialog.font_size_spinbox.setValue(self._console_font_size)

    def console_apply_settings(self):
        """ Apply values from config dialog to console.
        """
        fontsize = self._mw.console_settings_dialog.font_size_spinbox.value()
        self._mw.console_widget.font_size = fontsize
        self._console_font_size = fontsize
        self._mw.console_widget.reset_font()

    def update_config_widgets(self):
        """ Clear and refill the tree widget showing the configuration.
        """
        self._mw.config_widget.clear()
        self.fill_tree_item(self._mw.config_widget.invisibleRootItem(), self._manager.tree)

    def fill_tree_item(self, item, value):
        """
        Recursively fill a QTreeWidgeItem with the contents from a dictionary.

        @param QTreeWidgetItem item: the widget item to fill
        @param (dict, list, etc) value: value to fill in
        """
        item.setExpanded(True)
        if isinstance(value, dict):
            for key in value:
                child = QtWidgets.QTreeWidgetItem()
                child.setText(0, key)
                item.addChild(child)
                self.fill_tree_item(child, value[key])
        elif isinstance(value, list):
            for val in value:
                child = QtWidgets.QTreeWidgetItem()
                item.addChild(child)
                if type(val) is dict:
                    child.setText(0, '[dict]')
                    self.fill_tree_item(child, val)
                elif type(val) is OrderedDict:
                    child.setText(0, '[odict]')
                    self.fill_tree_item(child, val)
                elif isinstance(val, list):
                    child.setText(0, '[list]')
                    self.fill_tree_item(child, val)
                else:
                    child.setText(0, str(val))
                child.setExpanded(True)
        else:
            child = QtWidgets.QTreeWidgetItem()
            child.setText(0, str(value))
            item.addChild(child)

    def update_gui_module_list(self):
        """ Clear and refill the module list widget
        """
        # self.clearModuleList(self)
        self.fill_module_list(self._mw.gui_scroll_area.layout(), 'gui')
        self.fill_module_list(self._mw.logic_scroll_area.layout(), 'logic')
        self.fill_module_list(self._mw.hardware_scroll_area.layout(), 'hardware')

    # TODO:
    def fill_module_list(self, layout, base):
        """ Fill the module list widget with module widgets for defined gui
            modules.

          @param QLayout layout: layout of th module list widget where
                                 module widgest should be addad
          @param str base: module category to fill
        """
        pass
        # for module in self._manager.tree['defined'][base]:
        #     if module not in self._manager.tree['global']['startup']:
        #         widget = ModuleFrameWidget(self._manager, base, module)
        #         self.modlist.append(widget)
        #         layout.addWidget(widget)
        #         widget.sigLoadThis.connect(self.sigStartModule)
        #         widget.sigReloadThis.connect(self.sigReloadModule)
        #         widget.sigDeactivateThis.connect(self.sigStopModule)
        #         widget.sigCleanupStatus.connect(self.sigCleanupStatus)
        #         self.checkTimer.timeout.connect(widget.checkModuleState)

    def get_qudi_version(self):
        """ Try to determine the software version in case the program is in
            a git repository.
        """
        try:
            repo = Repo(get_main_dir())
            branch = repo.active_branch
            rev = str(repo.head.commit)
            return rev, str(branch)
        except Exception as e:
            print('Could not get git repo because:', e)
            return 'unknown', -1

    def reload_qudi(self):
        """ Reload the current config. """
        reply = QtWidgets.QMessageBox.question(
            self._mw,
            'Restart',
            'Do you want to restart qudi with current configuration?',
            QtWidgets.QMessageBox.Yes,
            QtWidgets.QMessageBox.No
        )

        config_file = self._manager._getConfigFile()
        restart = reply == QtWidgets.QMessageBox.Yes
        self.sigLoadConfig.emit(config_file, restart)

    def get_load_file(self):
        """ Ask the user for a file where the configuration should be loaded from
        """
        default_config_path = os.path.join(get_main_dir(), 'config')
        filename = QtWidgets.QFileDialog.getOpenFileName(self._mw,
                                                         'Load Configration',
                                                         default_config_path,
                                                         'Configuration files (*.cfg)')[0]
        if filename:
            reply = QtWidgets.QMessageBox.question(
                self._mw,
                'Restart',
                'Do you want to restart to use the configuration?',
                QtWidgets.QMessageBox.Yes,
                QtWidgets.QMessageBox.No
            )
            restart = reply == QtWidgets.QMessageBox.Yes
            self.sigLoadConfig.emit(filename, restart)

    def get_save_file(self):
        """ Ask the user for a file where the configuration should be saved
            to.
        """
        default_config_path = os.path.join(get_main_dir(), 'config')
        filename = QtWidgets.QFileDialog.getSaveFileName(self._mw,
                                                         'Save Configration',
                                                         default_config_path,
                                                         'Configuration files (*.cfg)')[0]
        if filename:
            self.sigSaveConfig.emit(filename)


# class ModuleListItem(QtWidgets.QFrame):
#
#     """ This class represents a module widget in the Qudi module list.
#
#       @signal str str sigLoadThis: gives signal with base and name of module
#                                    to be loaded
#       @signal str str sigReloadThis: gives signal with base and name of
#                                      module to be reloaded
#       @signal str str sigStopThis: gives signal with base and name of module
#                                    to be deactivated
#     """
#
#     sigLoadThis = QtCore.Signal(str, str)
#     sigReloadThis = QtCore.Signal(str, str)
#     sigDeactivateThis = QtCore.Signal(str, str)
#     sigCleanupStatus = QtCore.Signal(str, str)
#
#     def __init__(self, manager, basename, modulename):
#         """ Create a module widget.
#
#           @param str basename: module category
#           @param str modulename: unique module name
#         """
#         # Get the path to the *.ui file
#         this_dir = os.path.dirname(__file__)
#         ui_file = os.path.join(this_dir, 'ui_module_widget.ui')
#
#         # Load it
#         super().__init__()
#         uic.loadUi(ui_file, self)
#
#         self.manager = manager
#         self.name = modulename
#         self.base = basename
#
#         self.loadButton.setText('Load {0}'.format(self.name))
#         # connect buttons
#         self.loadButton.clicked.connect(self.loadButtonClicked)
#         self.reloadButton.clicked.connect(self.reloadButtonClicked)
#         self.deactivateButton.clicked.connect(self.deactivateButtonClicked)
#         self.cleanupButton.clicked.connect(self.cleanupButtonClicked)
#
#     def loadButtonClicked(self):
#         """ Send signal to load and activate this module.
#         """
#         self.sigLoadThis.emit(self.base, self.name)
#
#         # Instant return to checked to prevent visual lag before checkModuleState completes
#         self.loadButton.setChecked(True)
#
#     def reloadButtonClicked(self):
#         """ Send signal to reload this module.
#         """
#         self.sigReloadThis.emit(self.base, self.name)
#
#     def deactivateButtonClicked(self):
#         """ Send signal to deactivate this module.
#         """
#         self.sigDeactivateThis.emit(self.base, self.name)
#
#     def cleanupButtonClicked(self):
#         """ Send signal to deactivate this module.
#         """
#         self.sigCleanupStatus.emit(self.base, self.name)
#
#     def checkModuleState(self):
#         """ Get the state of this module and update visual indications in the GUI.
#
#             Modules cannot be unloaded, but they can be deactivated.
#
#             Once loaded, the "load <module>" button will remain checked and its text
#             will be updated to indicate that loading is no longer possible.
#         """
#         state = ''
#         if self.statusLabel.text() != 'exception, cannot get state':
#             try:
#                 if (self.base in self.manager.tree['loaded']
#                         and self.name in self.manager.tree['loaded'][self.base]):
#                     state = self.manager.tree['loaded'][self.base][self.name].module_state()
#
#                     if state != 'deactivated':
#                         self.reloadButton.setEnabled(True)
#                         self.deactivateButton.setEnabled(True)
#                         self.cleanupButton.setEnabled(False)
#                         self.loadButton.setChecked(True)
#
#                         if self.base == 'gui':
#                             self.loadButton.setText('Show {0}'.format(self.name))
#                         else:
#                             self.loadButton.setText(self.name)
#                     else:
#                         self.reloadButton.setEnabled(True)
#                         self.deactivateButton.setEnabled(False)
#                         self.cleanupButton.setEnabled(True)
#                         self.loadButton.setChecked(True)
#
#                         self.loadButton.setText('Activate {0}'.format(self.name))
#
#                 else:
#                     state = 'not loaded'
#                     self.reloadButton.setEnabled(False)
#                     self.deactivateButton.setEnabled(False)
#                     self.cleanupButton.setEnabled(True)
#             except:
#                 state = 'exception, cannot get state'
#                 self.reloadButton.setEnabled(True)
#                 self.deactivateButton.setEnabled(True)
#                 self.cleanupButton.setEnabled(True)
#
#             self.statusLabel.setText(state)
