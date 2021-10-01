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
import sys
import logging
import subprocess

import jupyter_client.kernelspec
from PySide2 import QtCore, QtWidgets
from qtconsole.manager import QtKernelManager

from qudi.core.statusvariable import StatusVar
from qudi.core.threadmanager import ThreadManager
from qudi.util.paths import get_main_dir, get_default_config_dir
from qudi.core.gui.main_gui.errordialog import ErrorDialog
from qudi.core.gui.main_gui.mainwindow import QudiMainWindow
from qudi.core.config import Configuration
from qudi.core.module import GuiBase
from qudi.core.logger import get_signal_handler

try:
    from git import Repo, InvalidGitRepositoryError
except ImportError:
    Repo = None


class QudiMainGui(GuiBase):
    """
    This class provides a GUI to the qudi main application object.
    """
    # status vars
    _console_font_size = StatusVar(name='console_font_size', default=10)
    #_console_color_theme = StatusVar(name='console_color_theme', default='linux')
    _show_error_popups = StatusVar(name='show_error_popups', default=True)

    def __init__(self, *args, **kwargs):
        """Create an instance of the module.

          @param object manager:
          @param str name:
          @param dict config:
        """
        super().__init__(*args, **kwargs)
        self.error_dialog = None
        self.mw = None
        self._has_console = False  # Flag indicating if an IPython console is available
        self.configuration = self._qudi_main.configuration
        # TODO do this also for font size etc.
        self._console_color_theme = self.configuration.console_color_theme

        self.log.error(f'{self._console_color_theme}')

    def on_activate(self):
        """ Activation method called on change to active state.

        This method creates the Manager main window.
        """
        # Create main window and restore position
        self.mw = QudiMainWindow(debug_mode=self._qudi_main.debug_mode)
        self._restore_window_geometry(self.mw)
        # Create error dialog for error message popups
        self.error_dialog = ErrorDialog()
        self.error_dialog.set_enabled(self._show_error_popups)

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

        self.keep_settings()
        self.update_configured_modules()
        self.update_config_widget()

        # IPython console widget
        self.start_jupyter_widget()

        color_theme_combo_box = self.mw.settings_dialog.color_theme_combobox
        color_themes = [color_theme_combo_box.itemText(i) for i in range(color_theme_combo_box.count())]
        if self._console_color_theme in color_themes:
            self.log.error(self._console_color_theme)
            ind = color_themes.index(self._console_color_theme)
            color_theme_combo_box.setCurrentIndex(ind)

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
        self.stop_jupyter_widget()
        self._save_window_geometry(self.mw)
        self.mw.close()

    def _connect_signals(self):
        get_signal_handler().sigRecordLogged.connect(self.handle_log_record, QtCore.Qt.QueuedConnection)
        qudi_main = self._qudi_main
        # Connect up the main windows actions
        self.mw.action_quit.triggered.connect(qudi_main.prompt_quit, QtCore.Qt.QueuedConnection)
        self.mw.action_load_configuration.triggered.connect(self.load_configuration)
        self.mw.action_reload_qudi.triggered.connect(
            qudi_main.prompt_restart, QtCore.Qt.QueuedConnection)
        self.mw.action_open_configuration_editor.triggered.connect(self.new_configuration)
        self.mw.action_load_all_modules.triggered.connect(
            qudi_main.module_manager.start_all_modules)
        self.mw.action_view_default.triggered.connect(self.reset_default_layout)
        # Connect signals from manager
        qudi_main.configuration.sigConfigChanged.connect(self.update_config_widget)
        qudi_main.module_manager.sigManagedModulesChanged.connect(self.update_configured_modules)
        qudi_main.module_manager.sigModuleStateChanged.connect(self.update_module_state)
        qudi_main.module_manager.sigModuleAppDataChanged.connect(self.update_module_app_data)
        # Settings dialog
        self.mw.settings_dialog.accepted.connect(self.apply_settings)
        self.mw.settings_dialog.rejected.connect(self.keep_settings)
        self.error_dialog.disable_checkbox.clicked.connect(self._error_dialog_enabled_changed)
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
        self.mw.action_open_configuration_editor.triggered.disconnect()
        self.mw.action_load_all_modules.triggered.disconnect()
        self.mw.action_view_default.triggered.disconnect()
        # Disconnect signals from manager
        qudi_main.configuration.sigConfigChanged.disconnect(self.update_config_widget)
        qudi_main.module_manager.sigManagedModulesChanged.disconnect(self.update_configured_modules)
        qudi_main.module_manager.sigModuleStateChanged.disconnect(self.update_module_state)
        qudi_main.module_manager.sigModuleAppDataChanged.disconnect(self.update_module_app_data)
        # Settings dialog
        self.mw.settings_dialog.accepted.disconnect()
        self.mw.settings_dialog.rejected.disconnect()
        self.error_dialog.disable_checkbox.clicked.disconnect()
        # Modules list
        self.mw.module_widget.sigActivateModule.disconnect()
        self.mw.module_widget.sigReloadModule.disconnect()
        self.mw.module_widget.sigDeactivateModule.disconnect()
        self.mw.module_widget.sigCleanupModule.disconnect()

        get_signal_handler().sigRecordLogged.disconnect(self.handle_log_record)

    def _init_remote_modules_widget(self):
        remote_server = self._qudi_main.remote_modules_server
        # hide remote modules menu action if RemoteModuleServer is not available
        if remote_server is None:
            self.mw.remote_widget.setVisible(False)
            self.mw.remote_dockwidget.setVisible(False)
            self.mw.action_view_remote.setVisible(False)
        else:
            server_config = self._qudi_main.configuration.remote_modules_server
            host = server_config['address']
            port = server_config['port']
            self.mw.remote_widget.setVisible(True)
            self.mw.remote_widget.server_label.setText(f'Server URL: rpyc://{host}:{port}/')
            self.mw.remote_widget.shared_module_listview.setModel(
                remote_server.service.shared_modules
            )

    def show(self):
        """Show the window and bring it to the top.
        """
        self.mw.show()
        self.mw.activateWindow()
        self.mw.raise_()

    def reset_default_layout(self):
        """
        Return the dockwidget layout and visibility to its default state
        """
        self.mw.config_dockwidget.setVisible(False)
        self.mw.console_dockwidget.setVisible(self._has_console)
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

        self.mw.action_view_console.setChecked(self._has_console)
        self.mw.action_view_console.setVisible(self._has_console)
        return

    def handle_log_record(self, entry):
        """
        Show an error popup if the log entry is error level and above.

        @param logging.LogRecord entry: log record as returned from logging module
        """
        if entry.levelname in ('error', 'critical'):
            self.error_dialog.new_error(entry)
        return

    def start_jupyter_widget(self):
        """ Starts a qudi IPython kernel in a separate process and connects it to the console widget
        """
        self._has_console = False
        try:
            # Create and start kernel process
            kernel_manager = QtKernelManager(kernel_name='Qudi', autorestart=False)
            # kernel_manager.kernel.gui = 'qt4'
            kernel_manager.start_kernel()

            # create kernel client and connect to console widget
            banner = 'This is an interactive IPython console. A reference to the running qudi ' \
                     'instance can be accessed via "qudi". View the current namespace with dir().\n' \
                     'Go, play.\n'
            self.mw.console_widget.banner = banner
            self.mw.console_widget.font_size = self._console_font_size
            self.mw.console_widget.reset_font()
            self.mw.console_widget.set_default_style(colors=self._console_color_theme)
            kernel_client = kernel_manager.client()
            kernel_client.hb_channel.time_to_dead = 10.0
            kernel_client.hb_channel.kernel_died.connect(self.kernel_died_callback)
            kernel_client.start_channels()
            self.mw.console_widget.kernel_manager = kernel_manager
            self.mw.console_widget.kernel_client = kernel_client
            self._has_console = True
            self.log.info('IPython kernel for qudi main GUI successfully started.')
        except jupyter_client.kernelspec.NoSuchKernel:
            self.log.error(
                'Qudi IPython kernelspec not installed. IPython console not available. Please run '
                '"qudi-install-kernel" from within the qudi Python environment and restart qudi. '
            )
        except:
            self.log.exception(
                'Exception while trying to start IPython kernel for qudi main GUI. Qudi IPython '
                'console not available.'
            )

    @QtCore.Slot()
    def kernel_died_callback(self):
        """
        """
        try:
            self.mw.console_widget.kernel_client.stop_channels()
        except:
            pass
        if self._has_console:
            self._has_console = False
            self.log.error(
                'Qudi IPython kernel has unexpectedly died. This can be caused by a corrupt qudi '
                'kernelspec installation. Try to run "qudi-install-kernel" from within the qudi '
                'Python environment and restart qudi.'
            )

    def stop_jupyter_widget(self):
        """ Stops the qudi IPython kernel process and detaches it from the console widget
        """
        try:
            self.mw.console_widget.kernel_client.stop_channels()
        except:
            self.log.exception('Exception while trying to shutdown qudi IPython client:')
        try:
            self.mw.console_widget.kernel_manager.shutdown_kernel()
        except:
            self.log.exception('Exception while trying to shutdown qudi IPython kernel:')
        self._has_console = False
        self.log.info('IPython kernel process for qudi main GUI has shut down.')

    def keep_settings(self):
        """ Write old values into settings dialog.
        """
        self.mw.settings_dialog.font_size_spinbox.setValue(self._console_font_size)
        self.mw.settings_dialog.show_error_popups_checkbox.setChecked(self._show_error_popups)

    def apply_settings(self):
        """ Apply values from settings dialog.
        """
        # Console font size
        font_size = self.mw.settings_dialog.font_size_spinbox.value()
        self.mw.console_widget.font_size = font_size
        self.mw.console_widget.reset_font()
        self._console_font_size = font_size

        # Console color theme
        color_theme = self.mw.settings_dialog.color_theme_combobox.currentText()
        self.mw.console_widget.set_default_style(color_theme)
        self._console_color_theme = color_theme
        # Error popups
        error_popups = self.mw.settings_dialog.show_error_popups_checkbox.isChecked()
        self.error_dialog.set_enabled(error_popups)
        self._show_error_popups = error_popups

    @QtCore.Slot()
    def _error_dialog_enabled_changed(self):
        """ Callback for the error dialog disable checkbox
        """
        self._show_error_popups = self.error_dialog.enabled
        self.mw.settings_dialog.show_error_popups_checkbox.setChecked(self._show_error_popups)

    @QtCore.Slot()
    @QtCore.Slot(object)
    def update_config_widget(self, config=None):
        """ Clear and refill the tree widget showing the configuration.
        """
        if config is None:
            config = self._qudi_main.configuration
        self.mw.config_widget.clear()
        self.fill_tree_item(self.mw.config_widget.invisibleRootItem(), config.config_dict)

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
                if isinstance(val, dict):
                    child.setText(0, '[dict]')
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

    def new_configuration(self):
        """ Prompt the user to open the graphical config editor in a subprocess in order to
        edit/create config files for qudi.
        """
        reply = QtWidgets.QMessageBox.question(
                self.mw,
                'Open Configuration Editor',
                'Do you want open the graphical qudi configuration editor to create or edit qudi '
                'config files?\n',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes
        )
        if reply == QtWidgets.QMessageBox.Yes:
            process = subprocess.Popen(args=[sys.executable, '-m', 'tools.config_editor'],
                                       close_fds=False,
                                       env=os.environ.copy(),
                                       stdin=sys.stdin,
                                       stdout=sys.stdout,
                                       stderr=sys.stderr)
