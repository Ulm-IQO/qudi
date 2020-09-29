# -*- coding: utf-8 -*-
""" This module contains the

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

import os
import logging
import numpy as np

from collections import OrderedDict
from qudi.core.statusvariable import StatusVar
from qudi.core.threadmanager import ThreadManager
from qudi.core.util.paths import get_main_dir, get_default_config_dir
from qudi.core.util.helpers import has_pyqtgraph
from qudi.core.remote import get_remote_modules_model
from qudi.core.gui.main_gui.errordialog import ErrorDialog
from qudi.core.gui.main_gui.mainwindow import QudiMainWindow
from qudi.core.module import GuiBase
from PySide2 import QtCore, QtWidgets, QtGui

try:
    from qtconsole.inprocess import QtInProcessKernelManager
except ImportError:
    from IPython.qt.inprocess import QtInProcessKernelManager

try:
    from git import Repo, InvalidGitRepositoryError
except ImportError:
    Repo = None

if has_pyqtgraph:
    import pyqtgraph as pg


class QudiMainGui(GuiBase):
    """
    This class provides a GUI to the qudi main application object.
    """
    # status vars
    _console_font_size = StatusVar('console_font_size', 10)

    def __init__(self, *args, **kwargs):
        """Create an instance of the module.

          @param object manager:
          @param str name:
          @param dict config:
        """
        super().__init__(*args, **kwargs)
        self._ipython_module_names = set()
        self.error_dialog = None
        self._kernel_manager = None
        self.mw = None

    def on_activate(self):
        """ Activation method called on change to active state.

        This method creates the Manager main window.
        """
        # Create main window and restore position
        self.mw = QudiMainWindow()
        self._restore_window_pos(self.mw)
        # Create error dialog for error message popups
        self.error_dialog = ErrorDialog(self)

        # Get qudi version number and configure statusbar and "about qudi" dialog
        version = self.get_qudi_version()
        if isinstance(version, str):
            self.mw.about_qudi_dialog.version_label.setText('version {0}'.format(version))
            self.mw.version_label.setText(
                '<a style=\"color: cyan;\"> version {0} </a>  configured from {1}'
                ''.format(version, self._qudi_main.configuration.config_file))
        else:
            self.mw.about_qudi_dialog.version_label.setText(
                '<a href=\"https://github.com/Ulm-IQO/qudi/commit/{0}\" style=\"color: cyan;\"> {0}'
                ' </a>, on branch {1}.'.format(version[0], version[1]))
            self.mw.version_label.setText(
                '<a href=\"https://github.com/Ulm-IQO/qudi/commit/{0}\" style=\"color: cyan;\"> {0}'
                ' </a>, on branch {1}, configured from {2}'
                ''.format(version[0], version[1], self._qudi_main.configuration.config_file))

        self._connect_signals()

        self.console_keep_settings()
        self.update_configured_modules()
        self.update_config_widget()

        # IPython console widget
        self.start_ipython()
        self.start_ipython_widget()

        # Configure thread widget
        self.mw.threads_widget.setModel(ThreadManager.instance())

        # Configure remotemodules widget
        self._init_remote_modules_widget()

        self.reset_default_layout()
        self.show()

    def on_deactivate(self):
        """Close window and remove connections.
        """
        self._disconnect_signals()
        self.stop_ipython_widget()
        self.stop_ipython()
        self._save_window_pos(self.mw)
        self.mw.close()

    @property
    def _qudi_main(self):
        qudi_main = super()._qudi_main
        if qudi_main is None:
            raise Exception('Unexpected missing qudi main instance. It has either been deleted or '
                            'garbage collected.')
        return qudi_main

    def _connect_signals(self):
        qudi_main = self._qudi_main
        # Connect up the main windows actions
        self.mw.action_quit.triggered.connect(qudi_main.prompt_quit, QtCore.Qt.QueuedConnection)
        self.mw.action_load_configuration.triggered.connect(self.load_configuration)
        self.mw.action_reload_qudi.triggered.connect(
            qudi_main.prompt_restart, QtCore.Qt.QueuedConnection)
        self.mw.action_save_configuration.triggered.connect(self.save_configuration)
        self.mw.action_load_all_modules.triggered.connect(
            qudi_main.module_manager.start_all_modules)
        self.mw.action_view_default.triggered.connect(self.reset_default_layout)
        # Connect signals from manager
        qudi_main.configuration.sigConfigChanged.connect(self.update_config_widget)
        qudi_main.module_manager.sigManagedModulesChanged.connect(self.update_configured_modules)
        qudi_main.module_manager.sigModuleStateChanged.connect(self.update_module_state)
        qudi_main.module_manager.sigModuleAppDataChanged.connect(self.update_module_app_data)
        # Console settings
        self.mw.console_settings_dialog.accepted.connect(self.console_apply_settings)
        self.mw.console_settings_dialog.rejected.connect(self.console_keep_settings)
        # Modules list
        self.mw.module_widget.sigActivateModule.connect(qudi_main.module_manager.activate_module)
        self.mw.module_widget.sigReloadModule.connect(qudi_main.module_manager.reload_module)
        self.mw.module_widget.sigDeactivateModule.connect(
            qudi_main.module_manager.deactivate_module)
        self.mw.module_widget.sigCleanupModule.connect(
            qudi_main.module_manager.clear_module_app_data)

    def _disconnect_signals(self):
        qudi_main = self._qudi_main
        # Disconnect the main windows actions
        self.mw.action_quit.triggered.disconnect()
        self.mw.action_load_configuration.triggered.disconnect()
        self.mw.action_reload_qudi.triggered.disconnect()
        self.mw.action_save_configuration.triggered.disconnect()
        self.mw.action_load_all_modules.triggered.disconnect()
        self.mw.action_view_default.triggered.disconnect()
        # Disconnect signals from manager
        qudi_main.configuration.sigConfigChanged.disconnect(self.update_config_widget)
        qudi_main.module_manager.sigManagedModulesChanged.disconnect(self.update_configured_modules)
        qudi_main.module_manager.sigModuleStateChanged.disconnect(self.update_module_state)
        qudi_main.module_manager.sigModuleAppDataChanged.disconnect(self.update_module_app_data)
        # Console settings
        self.mw.console_settings_dialog.accepted.disconnect()
        self.mw.console_settings_dialog.rejected.disconnect()
        # Modules list
        self.mw.module_widget.sigActivateModule.disconnect()
        self.mw.module_widget.sigReloadModule.disconnect()
        self.mw.module_widget.sigDeactivateModule.disconnect()
        self.mw.module_widget.sigCleanupModule.disconnect()

    def _init_remote_modules_widget(self):
        remote_server = self._qudi_main.remote_server
        # hide remote modules menu action if RemoteModuleServer is not available
        if remote_server is None:
            self.mw.remote_widget.setVisible(False)
            self.mw.remote_dockwidget.setVisible(False)
            self.mw.action_view_remote.setVisible(False)
        else:
            self.mw.remote_widget.setVisible(True)
            self.mw.remote_widget.server_label.setText(
                'Server URL: rpyc://{0}:{1}/'.format(remote_server.host, remote_server.port))
            self.mw.remote_widget.shared_module_listview.setModel(get_remote_modules_model())

    def show(self):
        """Show the window and bring it t the top.
        """
        self.mw.show()
        self.mw.activateWindow()
        self.mw.raise_()

    def reset_default_layout(self):
        """
        Return the dockwidget layout and visibility to its default state
        """
        self.mw.config_dockwidget.setVisible(False)
        self.mw.console_dockwidget.setVisible(True)
        self.mw.remote_dockwidget.setVisible(False)
        self.mw.threads_dockwidget.setVisible(False)
        self.mw.log_dockwidget.setVisible(True)

        self.mw.config_dockwidget.setFloating(False)
        self.mw.console_dockwidget.setFloating(False)
        self.mw.remote_dockwidget.setFloating(False)
        self.mw.threads_dockwidget.setFloating(False)
        self.mw.log_dockwidget.setFloating(False)

        self.mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.mw.config_dockwidget)
        self.mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.mw.log_dockwidget)
        self.mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.mw.remote_dockwidget)
        self.mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.mw.threads_dockwidget)
        self.mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.mw.console_dockwidget)
        return

    def handle_log_entry(self, entry):
        """
        Forward log entry to log widget and show an error popup if it is an error message.

        @param dict entry: Log entry
        """
        self.mw.log_widget.add_entry(entry)
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
        self._kernel_manager.kernel.shell.user_ns.update(
            {'np': np,
             'config': self._qudi_main.configuration.config_dict,
             'qudi': self._qudi_main})
        if has_pyqtgraph:
            self._kernel_manager.kernel.shell.user_ns['pg'] = pg
        self.update_ipython_all_modules()
        self._kernel_manager.kernel.gui = 'qt4'
        self.log.info('IPython has kernel {0}'.format(self._kernel_manager.has_kernel))
        self.log.info('IPython kernel alive {0}'.format(self._kernel_manager.is_alive()))
        self._qudi_main.module_manager.sigModuleStateChanged.connect(
            self.update_ipython_single_module, QtCore.Qt.QueuedConnection)
        self._qudi_main.module_manager.sigManagedModulesChanged.connect(
            self.update_ipython_all_modules, QtCore.Qt.QueuedConnection)

    def start_ipython_widget(self):
        """
        Create an IPython console widget and connect it to an IPython kernel.
        """
        if has_pyqtgraph:
            banner_modules = 'The numpy and pyqtgraph modules have already been imported as "np" ' \
                             'and "pg".'
        else:
            banner_modules = 'The numpy module has already been imported as "np".'
        banner = 'This is an interactive IPython console. {0} Configuration is in "config", the ' \
                 'manager is "manager" and all loaded modules are in this namespace with their ' \
                 'configured name. View the current namespace with dir(). Go, play.\n' \
                 ''.format(banner_modules)
        self.mw.console_widget.banner = banner
        # font size
        self.console_apply_settings()

        self.mw.console_widget.kernel_manager = self._kernel_manager
        self.mw.console_widget.kernel_client = self.mw.console_widget.kernel_manager.client()
        self.mw.console_widget.kernel_client.start_channels()
        # use the linux style theme which is basically the monokai theme
        self.mw.console_widget.set_default_style(colors='linux')
        return

    def stop_ipython(self):
        """ Stop the IPython kernel.
        """
        self.log.debug('IPython deactivation: {0}'.format(QtCore.QThread.currentThread()))
        self._kernel_manager.shutdown_kernel()
        self._qudi_main.module_manager.sigModuleStateChanged.disconnect(
            self.update_ipython_single_module)
        self._qudi_main.module_manager.sigManagedModulesChanged.disconnect(
            self.update_ipython_all_modules)

    def stop_ipython_widget(self):
        """ Disconnect the IPython widget from the kernel.
        """
        self.mw.console_widget.kernel_client.stop_channels()

    @QtCore.Slot(str, str, str)
    def update_ipython_single_module(self, base, name, state):
        """Remove deactivated module from namespace or add it if activated.
        """
        if state != 'deactivated':
            self._kernel_manager.kernel.shell.user_ns[name] = self._qudi_main.module_manager[
                name].instance
        else:
            self._kernel_manager.kernel.shell.user_ns.pop(name, None)
        return

    @QtCore.Slot()
    @QtCore.Slot(dict)
    def update_ipython_all_modules(self, modules_dict=None):
        """
        Remove non-existing modules from namespace, add new modules to namespace.

        @param dict modules_dict: Dictionary containing all configured ManagedModule instances
        """
        if modules_dict is None:
            modules_dict = self._qudi_main.module_manager
        new_namespace = {name: mod.instance for name, mod in modules_dict.items() if
                         mod.is_active and mod.instance is not None}
        new_namespace_set = set(new_namespace)
        discard = self._ipython_module_names - new_namespace_set
        self._kernel_manager.kernel.shell.user_ns.update(new_namespace)
        for name in discard:
            self._kernel_manager.kernel.shell.user_ns.pop(name, None)
        self._ipython_module_names = new_namespace_set

    def console_keep_settings(self):
        """ Write old values into config dialog.
        """
        self.mw.console_settings_dialog.font_size_spinbox.setValue(self._console_font_size)

    def console_apply_settings(self):
        """ Apply values from config dialog to console.
        """
        fontsize = self.mw.console_settings_dialog.font_size_spinbox.value()
        self.mw.console_widget.font_size = fontsize
        self._console_font_size = fontsize
        self.mw.console_widget.reset_font()

    @QtCore.Slot()
    @QtCore.Slot(dict)
    def update_config_widget(self, config=None):
        """ Clear and refill the tree widget showing the configuration.
        """
        if config is None:
            config = self._qudi_main.configuration.config_dict
        self.mw.config_widget.clear()
        self.fill_tree_item(self.mw.config_widget.invisibleRootItem(), config)

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

    @QtCore.Slot()
    @QtCore.Slot(dict)
    def update_configured_modules(self, modules=None):
        """ Clear and refill the module list widget
        """
        if modules is None:
            modules = self._qudi_main.module_manager
        self.mw.module_widget.update_modules(modules)

    @QtCore.Slot(str, str, str)
    def update_module_state(self, base, name, state):
        self.mw.module_widget.update_module_state(base, name, state)
        return

    @QtCore.Slot(str, str, bool)
    def update_module_app_data(self, base, name, exists):
        self.mw.module_widget.update_module_app_data(base, name, exists)

    def get_qudi_version(self):
        """ Try to determine the software version in case the program is in a git repository.
        """
        # Try to get repository information if qudi has been checked out as git repo
        if Repo is not None:
            try:
                repo = Repo(os.path.dirname(get_main_dir()))
                branch = repo.active_branch
                rev = str(repo.head.commit)
                return rev, str(branch)
            except InvalidGitRepositoryError:
                pass
            except:
                self.log.exception('Unexpected error while trying to get git repo:')

        # Get core version number from VERSION.txt
        try:
            with open(os.path.join(get_main_dir(), 'core', 'VERSION.txt'), 'r') as file:
                return file.read().strip()
        except:
            self.log.exception('Unexpected error while trying to get qudi version:')
        return 'unknown'

    def load_configuration(self):
        """ Ask the user for a file where the configuration should be loaded from
        """
        filename = QtWidgets.QFileDialog.getOpenFileName(self.mw,
                                                         'Load Configuration',
                                                         get_default_config_dir(True),
                                                         'Configuration files (*.cfg)')[0]
        if filename:
            reply = QtWidgets.QMessageBox.question(
                self.mw,
                'Restart',
                'Do you want to restart to use the configuration?\n'
                'Choosing "No" will use the selected config file for the next start of Qudi.',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.Cancel:
                return
            self._qudi_main.configuration.set_default_config_path(filename)
            if reply == QtWidgets.QMessageBox.Yes:
                self._qudi_main.restart()

    def save_configuration(self):
        """ Ask the user for a file where the configuration should be saved
            to.
        """
        filename = QtWidgets.QFileDialog.getSaveFileName(self.mw,
                                                         'Save Configuration',
                                                         get_default_config_dir(True),
                                                         'Configuration files (*.cfg)')[0]
        if filename:
            if not filename.endswith('.cfg'):
                filename += '.cfg'
            self._qudi_main.configuration.save_config(filename)
