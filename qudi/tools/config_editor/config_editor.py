# -*- coding: utf-8 -*-
"""

"""

__all__ = ('main', 'ConfigurationEditorMainWindow', 'ConfigurationEditor')

import os
import sys
from PySide2 import QtCore, QtGui, QtWidgets
from qudi.core.configoption import MissingOption
from qudi.util.paths import get_main_dir, get_default_config_dir, get_artwork_dir
from qudi.core.config import Configuration

from qudi.tools.config_editor.module_selector import ModuleSelector
from qudi.tools.config_editor.module_editor import ModuleConfigurationWidget
from qudi.tools.config_editor.global_editor import GlobalConfigurationWidget
from qudi.tools.config_editor.tree_widgets import ConfigModulesTreeWidget
from qudi.tools.config_editor.module_finder import QudiModules

try:
    import matplotlib
    matplotlib.use('agg')
except ImportError:
    pass


class ConfigurationEditorMainWindow(QtWidgets.QMainWindow):
    """
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('Qudi Config Editor')
        screen_size = QtWidgets.QApplication.instance().primaryScreen().availableSize()
        self.resize((screen_size.width() * 3) // 4, (screen_size.height() * 3) // 4)

        self.qudi_environment = QudiModules()
        self.configuration = Configuration()
        self.module_tree_widget = ConfigModulesTreeWidget()
        self.module_config_widget = ModuleConfigurationWidget(
            available_modules=self.qudi_environment.available_modules
        )
        self.global_config_widget = GlobalConfigurationWidget()

        label = QtWidgets.QLabel('Included Modules')
        label.setAlignment(QtCore.Qt.AlignCenter)
        font = label.font()
        font.setBold(True)
        font.setPointSize(10)
        label.setFont(font)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self.module_tree_widget)
        layout.addWidget(self.global_config_widget)
        layout.setStretch(1, 1)
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(widget)
        splitter.addWidget(self.module_config_widget)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        self.setCentralWidget(splitter)
        self.module_tree_widget.itemChanged.connect(self.module_name_changed)
        self.module_tree_widget.itemSelectionChanged.connect(self.module_selection_changed)

        # Main window actions
        icon_dir = os.path.join(get_main_dir(), 'artwork', 'icons', 'oxygen', '22x22')
        quit_icon = QtGui.QIcon(os.path.join(icon_dir, 'application-exit.png'))
        self.quit_action = QtWidgets.QAction(quit_icon, 'Quit')
        self.quit_action.setShortcut(QtGui.QKeySequence('Ctrl+Q'))
        load_icon = QtGui.QIcon(os.path.join(icon_dir, 'document-open.png'))
        self.load_action = QtWidgets.QAction(load_icon, 'Load')
        self.load_action.setShortcut(QtGui.QKeySequence('Ctrl+L'))
        self.load_action.setToolTip('Load a qudi configuration to edit from file.')
        save_icon = QtGui.QIcon(os.path.join(icon_dir, 'document-save.png'))
        self.save_action = QtWidgets.QAction(save_icon, 'Save')
        self.save_action.setShortcut(QtGui.QKeySequence('Ctrl+S'))
        self.save_action.setToolTip('Save the current qudi configuration to file.')
        self.save_as_action = QtWidgets.QAction('Save as ...')
        new_icon = QtGui.QIcon(os.path.join(icon_dir, 'document-new.png'))
        self.new_action = QtWidgets.QAction(new_icon, 'New')
        self.new_action.setShortcut(QtGui.QKeySequence('Ctrl+N'))
        self.new_action.setToolTip('Create a new qudi configuration from scratch.')
        select_icon = QtGui.QIcon(os.path.join(icon_dir, 'configure.png'))
        self.select_modules_action = QtWidgets.QAction(select_icon, 'Select Modules')
        self.select_modules_action.setShortcut(QtGui.QKeySequence('Ctrl+M'))
        self.select_modules_action.setToolTip(
            'Open an editor to select the modules to include in config.'
        )
        # Connect actions
        self.quit_action.triggered.connect(self.close)
        self.new_action.triggered.connect(self.new_config)
        self.load_action.triggered.connect(self.prompt_load_config)
        self.save_action.triggered.connect(self.save_config)
        self.save_as_action.triggered.connect(self.prompt_save_config)
        self.select_modules_action.triggered.connect(self.select_modules)

        # Create menu bar
        menu_bar = QtWidgets.QMenuBar()
        file_menu = QtWidgets.QMenu('File')
        menu_bar.addMenu(file_menu)
        file_menu.addAction(self.new_action)
        file_menu.addSeparator()
        file_menu.addAction(self.load_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)
        file_menu = QtWidgets.QMenu('Edit')
        menu_bar.addMenu(file_menu)
        file_menu.addAction(self.select_modules_action)
        self.setMenuBar(menu_bar)

        # Create toolbar
        toolbar = QtWidgets.QToolBar()
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        toolbar.addAction(self.new_action)
        toolbar.addAction(self.load_action)
        toolbar.addAction(self.save_action)
        toolbar.addSeparator()
        toolbar.addAction(self.select_modules_action)
        toolbar.setFloatable(False)
        self.addToolBar(toolbar)

        # Connect module editor signals
        self.module_config_widget.sigModuleConfigFinished.connect(self.update_module_config)

    @QtCore.Slot()
    def module_selection_changed(self):
        selected_items = self.module_tree_widget.selectedItems()
        if not selected_items:
            self.module_config_widget.close_module_editor()
            return

        item = selected_items[0]
        base = item.parent().text(0).lower()
        module = f'{base}.{item.text(2)}'
        name = item.text(1)

        # Get current module config dict from Configuration object
        try:
            config_dict = self.configuration.get_module_config(name)
        except (KeyError, ValueError):
            self.module_config_widget.show_invalid_module_label()
            self.module_tree_widget.editItem(item, 1)
            return

        # Sort out available connectors and targets as well as module config options
        if module in self.qudi_environment.available_modules:
            # Connectors
            compatible_targets = self.qudi_environment.module_connector_targets(module)
            available_targets, _ = self.module_tree_widget.get_modules()
            mandatory_connectors = dict()
            optional_connectors = dict()
            for conn in self.qudi_environment.module_connectors(module):
                targets = compatible_targets[conn.name]
                targets = tuple(name for name, mod in available_targets.items() if mod in targets)
                if conn.optional:
                    optional_connectors[conn.name] = tuple(targets)
                else:
                    mandatory_connectors[conn.name] = tuple(targets)

            # Config Options
            options = self.qudi_environment.module_config_options(module)
            mandatory_options = {
                opt.name: opt.default for opt in options if opt.missing == MissingOption.error
            }
            optional_options = {
                opt.name: opt.default for opt in options if opt.name not in mandatory_options
            }
        else:
            mandatory_connectors = None
            optional_connectors = None
            mandatory_options = None
            optional_options = None
        self.module_config_widget.open_module_editor(
            name,
            config_dict=config_dict,
            mandatory_conn_targets=mandatory_connectors,
            optional_conn_targets=optional_connectors,
            mandatory_options=mandatory_options,
            optional_options=optional_options,
            is_remote_module=self.configuration.is_remote_module(name)
        )

    @QtCore.Slot()
    def select_modules(self):
        self.module_config_widget.close_module_editor()
        available = self.qudi_environment.available_modules
        named_selected, unnamed_selected = self.module_tree_widget.get_modules()
        selected = list(named_selected.values())
        selected.extend(unnamed_selected)
        selector_dialog = ModuleSelector(available_modules=available, selected_modules=selected)
        if selector_dialog.exec_():
            new_selection = selector_dialog.get_selected_modules()
            new_named_selected = dict()
            remove_modules = list()
            # Recycle old module names if identical modules are selected
            for name, module in named_selected.items():
                try:
                    new_selection.remove(module)
                    new_named_selected[name] = module
                except ValueError:
                    remove_modules.append(name)

            # Set modules in main window
            self.module_tree_widget.set_modules(named_modules=new_named_selected,
                                                unnamed_modules=new_selection)
            self.module_config_widget.set_available_modules(new_named_selected)
            # Throw out all modules that are no longer present
            for name in remove_modules:
                self.configuration.remove_module(name)

    @QtCore.Slot(str, dict, dict, dict)
    def update_module_config(self, name, connections=None, options=None, meta=None):
        if self.configuration.is_remote_module(name):
            if meta:
                remote_url = meta.get('remote_url', None)
                certfile = meta.get('certfile', None)
                keyfile = meta.get('keyfile', None)
                if remote_url:
                    self.configuration.set_module_remote_url(name, remote_url)
                if certfile or keyfile:
                    self.configuration.set_module_remote_certificate(name, keyfile, certfile)
        else:
            self.configuration.set_module_connections(name, connections)
            self.configuration.set_module_options(name, options)
            self.configuration.set_module_allow_remote(
                name,
                meta.get('allow_remote', False) if meta else False
            )

    @QtCore.Slot(QtWidgets.QTreeWidgetItem, int)
    def module_name_changed(self, item, column):
        print('module_name_changed', item, column)
        if column != 1 or item is None or item.parent() is None:
            return
        base = item.parent().text(0).lower()
        name = item.text(1)
        module_class = item.text(2)
        if self.module_config_widget.currently_edited_module is None:
            try:
                if module_class == '<REMOTE MODULE>':
                    self.configuration.add_remote_module(name, base, '<remote URL>')
                else:
                    self.configuration.add_local_module(name, base, *module_class.rsplit('.', 1))
            except:
                item.setText(1, '<enter unique name>')
                raise
        else:
            old_name = self.module_config_widget.currently_edited_module
            try:
                self.module_config_widget.close_module_editor()
                self.configuration.rename_module(old_name=old_name, new_name=name)
            except:
                item.setText(1, old_name)
                raise
        self.module_selection_changed()

    def new_config(self):
        self.module_config_widget.close_module_editor()
        self.configuration.clear_config()
        self.module_tree_widget.set_modules(dict())
        self.global_config_widget.set_config(self.configuration.global_config)
        self.select_modules()

    def prompt_load_config(self):
        file_path = QtWidgets.QFileDialog.getOpenFileName(
            self,
            'Qudi Config Editor: Load Configuration...',
            get_default_config_dir(),
            'Config files (*.cfg)')[0]
        if file_path:
            self.configuration.load_config(file_path, set_default=False)
            modules = self.get_modules_from_config()
            global_cfg = self.configuration.global_config
            self.module_tree_widget.set_modules(named_modules=modules)
            self.module_config_widget.set_available_modules(modules)
            self.global_config_widget.set_config(global_cfg)

    def prompt_save_config(self):
        self.module_config_widget.commit_module_config()
        file_path = QtWidgets.QFileDialog.getSaveFileName(
            self,
            'Qudi Config Editor: Save Configuration...',
            get_default_config_dir(),
            'Config files (*.cfg)')[0]
        if file_path:
            self.configuration.save_config(file_path)

    def prompt_overwrite(self, file_path):
        answer = QtWidgets.QMessageBox.question(
            self,
            'Qudi Config Editor: Overwrite?',
            f'Do you really want to overwrite existing Qudi configuration at\n"{file_path}"?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No)
        return answer == QtWidgets.QMessageBox.Yes

    def save_config(self):
        # ToDo: Check for complete config
        self.module_config_widget.commit_module_config()
        current_path = self.configuration.config_file
        if current_path is None:
            self.prompt_save_config()
        elif os.path.exists(current_path):
            if self.prompt_overwrite(current_path):
                self.configuration.save_config()
            else:
                self.prompt_save_config()
        else:
            self.configuration.save_config()

    def prompt_close(self):
        answer = QtWidgets.QMessageBox.question(
            self,
            'Qudi Config Editor: Quit?',
            'Do you really want to quit the Qudi configuration editor?\nAll unsaved work will be '
            'lost.',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        return answer == QtWidgets.QMessageBox.Yes

    def closeEvent(self, event):
        if self.prompt_close():
            event.accept()
        else:
            event.ignore()

    def get_modules_from_config(self):
        modules = dict()
        module_config = self.configuration.module_config
        if module_config:
            for base, cfg_dict in module_config.items():
                modules.update(
                    {name: f'{base}.{cfg.get("module.Class", "<REMOTE MODULE>")}' for name, cfg in
                     cfg_dict.items()}
                )
        return modules


class ConfigurationEditor(QtWidgets.QApplication):
    """
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        icon_dir = os.path.join(get_artwork_dir(), 'logo')
        app_icon = QtGui.QIcon()
        app_icon.addFile(os.path.join(icon_dir, 'logo-qudi-16x16.png'), QtCore.QSize(16, 16))
        app_icon.addFile(os.path.join(icon_dir, 'logo-qudi-24x24.png'), QtCore.QSize(24, 24))
        app_icon.addFile(os.path.join(icon_dir, 'logo-qudi-32x32.png'), QtCore.QSize(32, 32))
        app_icon.addFile(os.path.join(icon_dir, 'logo-qudi-48x48.png'), QtCore.QSize(48, 48))
        app_icon.addFile(os.path.join(icon_dir, 'logo-qudi-256x256.png'), QtCore.QSize(256, 256))
        self.setWindowIcon(app_icon)


def main():
    app = ConfigurationEditor(sys.argv)
    # Init and open main window
    mw = ConfigurationEditorMainWindow()
    mw.show()
    # Start event loop
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
