# -*- coding: utf-8 -*-
"""

"""

import os
import sys
import importlib
import inspect
from PySide2 import QtCore, QtGui, QtWidgets
from qudi.core.configoption import MissingOption
from qudi.core.paths import get_main_dir, get_default_config_dir
from qudi.core.logger import get_logger
from qudi.core.module import Base, LogicBase, GuiBase
from qudi.core.config import Configuration

from qudi.tools.config_editor.module_selector import ModuleSelector
from qudi.tools.config_editor.tree_widgets import ConfigModulesTreeWidget

import matplotlib
matplotlib.use('agg')

log = get_logger(__name__)


class ConfigError(Exception):
    pass


class ModuleFinder:
    """
    """
    @staticmethod
    def _remove_search_paths_from_path(module_search_paths):
        for path in module_search_paths:
            if path in sys.path:
                sys.path.remove(path)

    @staticmethod
    def _add_search_paths_to_path(module_search_paths):
        for path in reversed(module_search_paths):
            if path in sys.path:
                sys.path.remove(path)
            sys.path.insert(0, path)

    @staticmethod
    def is_qudi_module(obj):
        base_classes = (Base, LogicBase, GuiBase)
        return inspect.isclass(obj) and not inspect.isabstract(obj) and issubclass(obj, Base) and \
            obj not in base_classes

    @classmethod
    def get_qudi_classes_in_module(cls, module):
        return dict(m for m in inspect.getmembers(module, cls.is_qudi_module) if
                    m[1].__module__ == module.__name__)

    @classmethod
    def get_qudi_modules(cls, search_paths):
        if isinstance(search_paths, str):
            search_paths = [search_paths]

        invalid_paths = {path for path in search_paths if not os.path.isdir(path)}
        if invalid_paths:
            log.error(f'Non-existent paths found to search in. Ignoring: {invalid_paths}.')
        search_paths = [path for path in search_paths if path not in invalid_paths]

        cls._add_search_paths_to_path(search_paths)
        try:
            found_modules = dict()
            for path in search_paths:
                # Find qudi modules
                for base in ('gui', 'logic', 'hardware'):
                    for root, _, files in os.walk(os.path.join(path, base)):
                        for file in (f for f in files if f.endswith('.py')):
                            module_name_comp = os.path.normpath(root).split(os.sep)
                            index = module_name_comp.index(base)
                            module_name_comp.append(file[:-3])
                            module_name = '.'.join(module_name_comp[index:])
                            try:
                                module = importlib.import_module(module_name)
                            except:
                                log.exception(f'Error during import of module "{module_name}".')
                                continue
                            classes = cls.get_qudi_classes_in_module(module)
                            found_modules.update(
                                {f'{module_name}.{c_name}': c for c_name, c in classes.items()}
                            )
        finally:
            cls._remove_search_paths_from_path(search_paths)
        return found_modules


class QudiModules:
    """
    """

    def __init__(self, additional_search_paths=None):
        # Import all modules available in qudi installation directory and additional search paths
        module_search_paths = [get_main_dir()]
        if additional_search_paths:
            module_search_paths.extend(module_search_paths)

        # import all qudi module classes from search paths
        self._qudi_modules = ModuleFinder.get_qudi_modules(module_search_paths)
        # Collect all connectors for all modules
        self._module_connectors = {
            mod: tuple(cls._module_meta['connectors'].values()) for mod, cls in self._qudi_modules.items()
        }
        # Get for each connector in each module compatible modules to connect to
        self._module_connectors_compatible_modules = {
            mod: self._modules_for_connectors(mod) for mod in self._qudi_modules
        }
        # Get all ConfigOptions for all modules
        self._module_config_options = {
            mod: tuple(cls._module_meta['config_options'].values()) for mod, cls in self._qudi_modules.items()
        }

    def _modules_for_connectors(self, module):
        return {
            conn.name: self._modules_for_connector(conn) for conn in self._module_connectors[module]
        }

    def _modules_for_connector(self, connector):
        interface = connector.interface
        bases = {mod: {c.__name__ for c in cls.mro()} for mod, cls in self._qudi_modules.items()}
        return tuple(mod for mod, base_names in bases.items() if interface in base_names)

    @property
    def available_modules(self):
        return tuple(self._qudi_modules)

    def module_connectors(self, module):
        return self._module_connectors[module]

    def module_connector_targets(self, module):
        return self._module_connectors_compatible_modules[module].copy()

    def module_config_options(self, module):
        return self._module_config_options[module]


class ConfigurationEditor(QtWidgets.QMainWindow):
    """
    """
    def __init__(self, qudi_environment, **kwargs):
        assert isinstance(qudi_environment, QudiModules)

        super().__init__(**kwargs)
        self.setWindowTitle('Qudi Config Editor')
        screen_size = QtWidgets.QApplication.instance().primaryScreen().availableSize()
        self.resize((screen_size.width() * 3) // 4, (screen_size.height() * 3) // 4)

        self.qudi_environment = qudi_environment
        self.configuration = Configuration()
        self.selector_dialog = ModuleSelector(
            self,
            available_modules=self.qudi_environment.available_modules
        )

        self.module_tree_widget = ConfigModulesTreeWidget()
        self.module_config_widget = ModuleConfigurationWidget()
        self.module_config_widget.sigModuleConfigFinished.connect(self.write_module_config)
        self.module_config_widget.sigRemoteConfigFinished.connect(self.write_remote_module_config)
        self.global_config_widget = GlobalConfigurationWidget()

        label = QtWidgets.QLabel('Included Modules')
        label.setAlignment(QtCore.Qt.AlignCenter)
        font = label.font()
        font.setBold(True)
        font.setPointSize(10)
        label.setFont(font)
        hline = QtWidgets.QFrame()
        hline.setFrameShape(QtWidgets.QFrame.HLine)
        hline.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label)
        layout.addWidget(self.module_tree_widget)
        layout.addWidget(hline)
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
        self.module_tree_widget.itemClicked.connect(self.module_clicked)

        # Main window actions
        icon_dir = os.path.join(get_main_dir(), 'core', 'artwork', 'icons', 'oxygen', '22x22')
        quit_icon = QtGui.QIcon(os.path.join(icon_dir, 'application-exit.png'))
        self.quit_action = QtWidgets.QAction(quit_icon, 'Quit')
        self.quit_action.setShortcut(QtGui.QKeySequence('Ctrl+Q'))
        load_icon = QtGui.QIcon(os.path.join(icon_dir, 'document-open.png'))
        self.load_action = QtWidgets.QAction(load_icon, 'Load configuration')
        self.load_action.setShortcut(QtGui.QKeySequence('Ctrl+L'))
        save_icon = QtGui.QIcon(os.path.join(icon_dir, 'document-save.png'))
        self.save_action = QtWidgets.QAction(save_icon, 'Save configuration')
        self.save_action.setShortcut(QtGui.QKeySequence('Ctrl+S'))
        self.save_as_action = QtWidgets.QAction(save_icon, 'Save configuration as ...')
        new_icon = QtGui.QIcon(os.path.join(icon_dir, 'document-new.png'))
        self.new_action = QtWidgets.QAction(new_icon, 'New configuration')
        self.new_action.setShortcut(QtGui.QKeySequence('Ctrl+N'))
        select_icon = QtGui.QIcon(os.path.join(icon_dir, 'configure.png'))
        self.select_modules_action = QtWidgets.QAction(select_icon, 'Select Modules')
        # Connect actions
        self.quit_action.triggered.connect(self.close)
        self.new_action.triggered.connect(self.clear_config)
        self.load_action.triggered.connect(self.prompt_load_config)
        self.save_action.triggered.connect(self.save_config)
        self.save_as_action.triggered.connect(self.prompt_save_config)
        self.select_modules_action.triggered.connect(self.select_modules)

        # Create menu bar
        menu_bar = QtWidgets.QMenuBar()
        file_menu = QtWidgets.QMenu('File')
        file_menu.addAction(self.new_action)
        file_menu.addSeparator()
        file_menu.addAction(self.load_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)
        file_menu.addAction(self.select_modules_action)
        menu_bar.addMenu(file_menu)
        self.setMenuBar(menu_bar)

        # Create toolbar
        toolbar = QtWidgets.QToolBar()
        toolbar.addAction(self.new_action)
        toolbar.addAction(self.load_action)
        toolbar.addAction(self.save_action)
        toolbar.addSeparator()
        toolbar.addAction(self.select_modules_action)
        toolbar.setFloatable(False)
        self.addToolBar(toolbar)

    def module_clicked(self, item, column):
        if item is None or item.parent() is None or not 0 <= column <= 2:
            return
        base = item.parent().text(0).lower()
        module = f'{base}.{item.text(2)}'
        module_name = item.text(1)
        if self.module_config_widget.currently_edited_module != module_name:
            # Sort out available connectors and targets
            compatible_targets = self.qudi_environment.module_connector_targets(module)
            selected_modules = self.selector_dialog.selected_modules
            mandatory_connectors = dict()
            optional_connectors = dict()
            for conn in self.qudi_environment.module_connectors(module):
                targets = compatible_targets[conn.name]
                avail_mods = (name for name, mod in selected_modules.items() if mod in targets)
                if conn.optional:
                    optional_connectors[conn.name] = tuple(avail_mods)
                else:
                    mandatory_connectors[conn.name] = tuple(avail_mods)
            # Sort out config options
            options = self.qudi_environment.module_config_options(module)
            mandatory_options = {
                opt.name: '' for opt in options if opt.missing == MissingOption.error
            }
            optional_options = {
                opt.name: opt.default for opt in options if opt.name not in mandatory_options
            }
            # Recall already set config options and connections
            try:
                module_cfg = self.configuration.get_module_config(module_name)
                for opt_name, value in module_cfg.items():
                    if opt_name in mandatory_options:
                        mandatory_options[opt_name] = value
                    elif opt_name in optional_options:
                        optional_options[opt_name] = value
                connections = module_cfg.get('connect', dict())
                connections = {
                    conn: mod for conn, mod in connections.items() if mod in selected_modules
                }
            except KeyError:
                connections = dict()
            self.module_config_widget.open_module_editor(module_name=module_name,
                                                         mandatory_connectors=mandatory_connectors,
                                                         optional_connectors=optional_connectors,
                                                         connections=connections,
                                                         mandatory_cfg_options=mandatory_options,
                                                         optional_cfg_options=optional_options)

    def select_modules(self):
        self.module_config_widget.commit_module_config()
        if self.selector_dialog.exec_():
            if self.module_config_widget.currently_edited_module is not None:
                self.module_config_widget.close_module_editor()
            new_selection = self.selector_dialog.selected_modules
            # Set modules in main window
            self.module_tree_widget.set_modules(new_selection)
            # Throw out all modules that are no longer present or have changed module <-> name
            # correspondence
            old_modules = self.get_modules_from_config()
            remove_modules = {
                name for name, mod in old_modules.items() if new_selection.get(name, None) != mod
            }
            for name in remove_modules:
                del old_modules[name]
                self.configuration.remove_module(name)
            # Add new modules to config (without connections and options of course)
            for name, module in new_selection.items():
                if name not in old_modules:
                    base, module_class = module.split('.', 1)
                    cfg_opt = self.qudi_environment.module_config_options(module)
                    default_opt = {
                        op.name: op.default for op in cfg_opt if op.missing != MissingOption.error
                    }
                    self.configuration.set_local_module(name,
                                                        base,
                                                        module_class,
                                                        options=default_opt)

    def write_module_config(self, name, connections, config_options):
        module = self.module_tree_widget.get_modules()[name]
        base, module_class = module.split('.', 1)
        remoteaccess = config_options.pop('remoteaccess', True)
        self.configuration.set_local_module(name,
                                            base,
                                            module_class,
                                            connections,
                                            config_options,
                                            remoteaccess)

    def write_remote_module_config(self, name, config_options):
        # ToDo: implement
        raise NotImplementedError
        # module = self.module_tree_widget.get_modules()[name]
        # base, module_class = module.split('.', 1)
        # self.configuration.set_remote_module(name,
        #                                     base,
        #                                     module_class,
        #                                     connections,
        #                                     config_options,
        #                                     remoteaccess)

    def clear_config(self):
        self.module_config_widget.close_module_editor()
        self.configuration = Configuration()
        self.module_tree_widget.set_modules(dict())
        self.selector_dialog.setParent(None)
        self.selector_dialog.deleteLater()
        self.selector_dialog = ModuleSelector(
            self,
            available_modules=self.qudi_environment.available_modules
        )

    def prompt_load_config(self):
        file_path = QtWidgets.QFileDialog.getOpenFileName(
            self,
            'Qudi Config Editor: Load Configuration...',
            get_default_config_dir(),
            'Config files (*.cfg)')[0]
        if file_path:
            self.configuration.load_config(file_path, set_default=False)
            modules = self.get_modules_from_config()
            self.module_tree_widget.set_modules(modules)
            self.selector_dialog.setParent(None)
            self.selector_dialog.deleteLater()
            self.selector_dialog = ModuleSelector(
                self,
                available_modules=self.qudi_environment.available_modules,
                selected_modules=modules
            )

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
            QtWidgets.QMessageBox.No)
        return answer == QtWidgets.QMessageBox.Yes

    def closeEvent(self, event):
        if self.prompt_close():
            event.accept()
        else:
            event.ignore()

    def get_modules_from_config(self):
        modules = dict()
        # ToDo: Handle remote modules
        module_config = self.configuration.module_config
        if module_config is not None:
            for base, cfg_dict in module_config.items():
                modules.update(
                    {name: '.'.join((base, cfg['module.Class'])) for name, cfg in cfg_dict.items()
                     if 'module.Class' in cfg}
                )
        return modules


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    qudi_env = QudiModules()
    # qudi_config = QudiConfiguration(qudi_env.available_module_config_options,
    #                                 qudi_env.available_module_connectors)
    # qudi_config.load_config_from_file('C:\\Users\\neverhorst\\qudi\\config\\test.cfg')
    # qudi_config.save_config_to_file('C:\\Users\\neverhorst\\qudi\\config\\test2.cfg')
    mw = ConfigurationEditor(qudi_env)
    mw.show()
    sys.exit(app.exec_())
