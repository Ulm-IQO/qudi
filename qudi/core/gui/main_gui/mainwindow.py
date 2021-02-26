# -*- coding: utf-8 -*-
"""
This file contains the QMainWindow class for the Qudi main GUI.

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
from PySide2 import QtCore, QtGui, QtWidgets
from qudi.core.gui.main_gui.logwidget import LogWidget
from qudi.core.gui.main_gui.remotewidget import RemoteWidget
from qudi.core.gui.main_gui.aboutqudidialog import AboutQudiDialog
from qudi.core.gui.main_gui.consolesettingsdialog import ConsoleSettingsDialog
from qudi.core.gui.main_gui.modulewidget import ModuleWidget
from qudi.core.paths import get_artwork_dir
from qudi.core.gui.qtwidgets.advanced_dockwidget import AdvancedDockWidget
from qtconsole.rich_jupyter_widget import RichJupyterWidget


class QudiMainWindow(QtWidgets.QMainWindow):
    """
    Main Window definition for the manager GUI.
    """
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.setWindowTitle('qudi: Manager')
        screen_size = QtWidgets.QApplication.instance().primaryScreen().availableSize()
        width = (screen_size.width() * 3) // 4
        height = (screen_size.height() * 3) // 4
        self.resize(width, height)

        self.module_widget = ModuleWidget()
        self.module_widget.setObjectName('moduleTabWidget')
        self.setCentralWidget(self.module_widget)

        # Create actions
        # Toolbar actions
        icon_path = os.path.join(get_artwork_dir(), 'icons', 'oxygen', '22x22')
        self.action_load_configuration = QtWidgets.QAction()
        self.action_load_configuration.setIcon(
            QtGui.QIcon(os.path.join(icon_path, 'document-open.png')))
        self.action_load_configuration.setText('Load configuration')
        self.action_load_configuration.setToolTip('Load configuration')
        self.action_save_configuration = QtWidgets.QAction()
        self.action_save_configuration.setIcon(
            QtGui.QIcon(os.path.join(icon_path, 'document-save.png')))
        self.action_save_configuration.setText('Save configuration')
        self.action_save_configuration.setToolTip('Save configuration')
        self.action_reload_qudi = QtWidgets.QAction()
        self.action_reload_qudi.setIcon(
            QtGui.QIcon(os.path.join(icon_path, 'view-refresh.png')))
        self.action_reload_qudi.setText('Reload current configuration')
        self.action_reload_qudi.setToolTip('Reload current configuration')
        self.action_load_all_modules = QtWidgets.QAction()
        self.action_load_all_modules.setIcon(
            QtGui.QIcon(os.path.join(icon_path, 'dialog-warning.png')))
        self.action_load_all_modules.setText('Load all modules')
        self.action_load_all_modules.setToolTip('Load all available modules found in configuration')
        # quit action
        self.action_quit = QtWidgets.QAction()
        self.action_quit.setIcon(QtGui.QIcon(os.path.join(icon_path, 'application-exit.png')))
        self.action_quit.setText('Quit qudi')
        self.action_quit.setToolTip('Quit qudi')
        self.action_quit.setShortcut(QtGui.QKeySequence('Ctrl+Q'))
        # view actions
        self.action_view_console = QtWidgets.QAction()
        self.action_view_console.setCheckable(True)
        self.action_view_console.setChecked(True)
        self.action_view_console.setText('Show console')
        self.action_view_console.setToolTip('Show IPython console')
        self.action_view_log = QtWidgets.QAction()
        self.action_view_log.setCheckable(True)
        self.action_view_log.setChecked(True)
        self.action_view_log.setText('Show log')
        self.action_view_log.setToolTip('Show log dockwidget')
        self.action_view_config = QtWidgets.QAction()
        self.action_view_config.setCheckable(True)
        self.action_view_config.setChecked(False)
        self.action_view_config.setText('Show configuration')
        self.action_view_config.setToolTip('Show configuration dockwidget')
        self.action_view_remote = QtWidgets.QAction()
        self.action_view_remote.setCheckable(True)
        self.action_view_remote.setChecked(False)
        self.action_view_remote.setText('Show remote')
        self.action_view_remote.setToolTip('Show remote connections dockwidget')
        self.action_view_threads = QtWidgets.QAction()
        self.action_view_threads.setCheckable(True)
        self.action_view_threads.setChecked(False)
        self.action_view_threads.setText('Show threads')
        self.action_view_threads.setToolTip('Show threads dockwidget')
        self.action_view_default = QtWidgets.QAction()
        self.action_view_default.setText('Restore default')
        self.action_view_default.setToolTip('Restore default view')
        # Dialog actions
        self.action_console_settings = QtWidgets.QAction()
        self.action_console_settings.setIcon(
            QtGui.QIcon(os.path.join(icon_path, 'configure.png')))
        self.action_console_settings.setText('Console')
        self.action_console_settings.setToolTip('Open IPython console settings')
        self.action_about_qudi = QtWidgets.QAction()
        self.action_about_qudi.setIcon(
            QtGui.QIcon(os.path.join(icon_path, 'go-home.png')))
        self.action_about_qudi.setText('About qudi')
        self.action_about_qudi.setToolTip('Read up about qudi')
        self.action_about_qt = QtWidgets.QAction()
        self.action_about_qt.setIcon(
            QtGui.QIcon(os.path.join(icon_path, 'go-home.png')))
        self.action_about_qt.setText('About Qt')
        self.action_about_qt.setToolTip('Read up about Qt')

        # Create toolbar
        self.toolbar = QtWidgets.QToolBar()
        self.toolbar.setOrientation(QtCore.Qt.Horizontal)
        self.toolbar.addAction(self.action_load_configuration)
        self.toolbar.addAction(self.action_save_configuration)
        self.toolbar.addAction(self.action_reload_qudi)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_load_all_modules)
        self.addToolBar(self.toolbar)

        # Create menu bar
        self.menubar = QtWidgets.QMenuBar()
        menu = QtWidgets.QMenu('File')
        menu.addAction(self.action_load_configuration)
        menu.addAction(self.action_save_configuration)
        menu.addAction(self.action_reload_qudi)
        menu.addSeparator()
        menu.addAction(self.action_load_all_modules)
        menu.addSeparator()
        menu.addAction(self.action_quit)
        self.menubar.addMenu(menu)
        menu = QtWidgets.QMenu('View')
        menu.addAction(self.action_view_console)
        menu.addAction(self.action_view_log)
        menu.addAction(self.action_view_config)
        menu.addAction(self.action_view_remote)
        menu.addAction(self.action_view_threads)
        menu.addSeparator()
        menu.addAction(self.action_view_default)
        self.menubar.addMenu(menu)
        menu = QtWidgets.QMenu('Settings')
        menu.addAction(self.action_console_settings)
        self.menubar.addMenu(menu)
        menu = QtWidgets.QMenu('About')
        menu.addAction(self.action_about_qudi)
        menu.addAction(self.action_about_qt)
        self.menubar.addMenu(menu)
        self.setMenuBar(self.menubar)

        # Create status bar
        self.statusbar = QtWidgets.QStatusBar()
        self.setStatusBar(self.statusbar)
        self.version_label = QtWidgets.QLabel()
        self.version_label.setOpenExternalLinks(True)
        self.statusbar.addWidget(self.version_label)

        # Create dialogues
        self.about_qudi_dialog = AboutQudiDialog()
        self.about_qudi_dialog.setWindowTitle('About qudi')
        self.console_settings_dialog = ConsoleSettingsDialog()

        # Create dockwidgets
        self.config_widget = QtWidgets.QTreeWidget()
        self.config_dockwidget = AdvancedDockWidget('Configuration')
        self.config_dockwidget.setWidget(self.config_widget)
        self.config_dockwidget.setAllowedAreas(
            QtCore.Qt.BottomDockWidgetArea | QtCore.Qt.LeftDockWidgetArea)
        self.log_widget = LogWidget(max_entries=10000)
        self.log_dockwidget = AdvancedDockWidget('Log')
        self.log_dockwidget.setWidget(self.log_widget)
        self.log_dockwidget.setAllowedAreas(QtCore.Qt.BottomDockWidgetArea)
        self.remote_widget = RemoteWidget()
        self.remote_dockwidget = AdvancedDockWidget('Remote modules')
        self.remote_dockwidget.setWidget(self.remote_widget)
        self.remote_dockwidget.setAllowedAreas(QtCore.Qt.BottomDockWidgetArea)
        self.threads_widget = QtWidgets.QListView()
        self.threads_dockwidget = AdvancedDockWidget('Threads')
        self.threads_dockwidget.setWidget(self.threads_widget)
        self.threads_dockwidget.setAllowedAreas(QtCore.Qt.BottomDockWidgetArea)
        self.console_widget = RichJupyterWidget()
        self.console_dockwidget = AdvancedDockWidget('Console')
        self.console_dockwidget.setWidget(self.console_widget)
        self.console_dockwidget.setAllowedAreas(
            QtCore.Qt.RightDockWidgetArea | QtCore.Qt.LeftDockWidgetArea)

        # Add dockwidgets to main window
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.config_dockwidget)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.log_dockwidget)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.remote_dockwidget)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.threads_dockwidget)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.console_dockwidget)

        # Synchronize dockwidget visibility change signals
        self.config_dockwidget.sigClosed.connect(lambda: self.action_view_config.setChecked(False))
        self.log_dockwidget.sigClosed.connect(
            lambda: self.action_view_log.setChecked(False))
        self.remote_dockwidget.sigClosed.connect(
            lambda: self.action_view_remote.setChecked(False))
        self.threads_dockwidget.sigClosed.connect(
            lambda: self.action_view_threads.setChecked(False))
        self.console_dockwidget.sigClosed.connect(
            lambda: self.action_view_console.setChecked(False))
        self.action_view_config.toggled.connect(self.config_dockwidget.setVisible)
        self.action_view_log.toggled.connect(self.log_dockwidget.setVisible)
        self.action_view_remote.toggled.connect(self.remote_dockwidget.setVisible)
        self.action_view_threads.toggled.connect(self.threads_dockwidget.setVisible)
        self.action_view_console.toggled.connect(self.console_dockwidget.setVisible)

        # Connect dialog open signals
        self.action_about_qudi.triggered.connect(self.about_qudi_dialog.open)
        self.action_about_qt.triggered.connect(QtWidgets.QApplication.aboutQt)
        self.action_console_settings.triggered.connect(self.console_settings_dialog.exec_)  # modal
        return
