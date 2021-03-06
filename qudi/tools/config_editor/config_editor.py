# -*- coding: utf-8 -*-
"""

"""

import os
import sys
import copy
import importlib
import inspect
from functools import partial
from PySide2 import QtCore, QtGui, QtWidgets
from qudi.util.mutex import RecursiveMutex
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


# class QudiConfiguration:
#     """
#     """
#     _remote_options = ('remote_url', 'certfile', 'keyfile')
#
#     def __init__(self, available_module_config_options, available_module_connectors):
#         self._lock = RecursiveMutex()
#         self._available_module_config_options = available_module_config_options
#         self._available_module_connectors = available_module_connectors
#         self.included_module_configs = dict()
#         self.stashed_module_configs = dict()
#
#     def include_module(self, module_name, module, connections=None, config_options=None):
#         with self._lock:
#             if module not in self._available_module_config_options:
#                 raise ConfigError('No module "{0}" found in qudi environment.'.format(module))
#             if module_name in self.stashed_module_configs and self.stashed_module_configs[
#                 module_name].module == module:
#                 self.included_module_configs[module_name] = self.stashed_module_configs.pop(
#                     module_name)
#             elif module_name not in self.included_module_configs or self.included_module_configs[
#                 module_name].module != module:
#                 self.included_module_configs[module_name] = ModuleConfiguration(module_name, module)
#             module_config = self.included_module_configs[module_name]
#             if connections is not None:
#                 for connector, module_name in connections.items():
#                     module_config.set_connection(connector, module_name)
#             if config_options is not None:
#                 for cfg_option, option_value in config_options.items():
#                     module_config.set_config_option(cfg_option, option_value)
#
#     def exclude_module(self, module_name):
#         with self._lock:
#             if module_name in self.included_module_configs:
#                 self.stashed_module_configs[module_name] = self.included_module_configs.pop(
#                     module_name)
#
#     def set_module_connection(self, module_name, connector, target_module, ignore_missing=False):
#         with self._lock:
#             module_config = self.included_module_configs.get(module_name, None)
#             if module_config is None:
#                 raise ConfigError(
#                     'No module with name "{0}" included in configuration.'.format(module_name))
#             if connector not in self._available_module_connectors[module_config.module]:
#                 raise ConfigError(
#                     'Connector "{0}" not found in module "{1}".'.format(connector, module_name))
#             if target_module == 'Not Connected':
#                 target_module = None
#             elif not ignore_missing and target_module not in self.included_module_configs:
#                 raise ConfigError('Module to connect with name "{0}" is not included in config.'
#                                   ''.format(target_module))
#             module_config.set_connection(connector, target_module)
#
#     def set_module_config_option(self, module_name, cfg_option, option_value):
#         with self._lock:
#             print('set_module_config_option:', module_name, cfg_option, option_value)
#             module_config = self.included_module_configs.get(module_name, None)
#             if module_config is None:
#                 raise ConfigError(
#                     'No module with name "{0}" included in configuration.'.format(module_name))
#             if cfg_option not in self._available_module_config_options[module_config.module]:
#                 if cfg_option not in self._remote_options:
#                     raise ConfigError('ConfigOption "{0}" invalid for module "{1}".'
#                                       ''.format(cfg_option, module_name))
#             module_config.set_config_option(cfg_option, option_value)
#
#     def get_missing_module_connectors(self, module_name):
#         with self._lock:
#             module_config = self.included_module_configs.get(module_name, None)
#             if module_config is None:
#                 raise ConfigError(
#                     'No module with name "{0}" included in configuration.'.format(module_name))
#             module_connectors = self._available_module_connectors[module_config.module]
#             mandatory = {name for name, conn in module_connectors.items() if not conn.optional}
#             return sorted(conn for conn in mandatory if conn not in module_config.connections)
#
#     def get_missing_module_cfg_options(self, module_name):
#         with self._lock:
#             module_config = self.included_module_configs.get(module_name, None)
#             if module_config is None:
#                 raise ConfigError(
#                     'No module with name "{0}" included in configuration.'.format(module_name))
#             module_cfg_options = self._available_module_config_options[module_config.module]
#             mandatory = {name for name, opt in module_cfg_options.items() if
#                          opt.missing == MissingOption.error}
#             return sorted(opt for opt in mandatory if opt not in module_config.config_options)
#
#     def get_module_config(self, module_name, ignore_incomplete=False):
#         with self._lock:
#             if module_name not in self.included_module_configs:
#                 raise ConfigError(
#                     'No module with name "{0}" included in configuration.'.format(module_name))
#             if not ignore_incomplete:
#                 missing_conn = self.get_missing_module_connectors(module_name)
#                 missing_opt = self.get_missing_module_cfg_options(module_name)
#                 if missing_conn or missing_opt:
#                     msg = 'Configuration for module "{0}" incomplete.'.format(module_name)
#                     if missing_conn:
#                         msg += '\nMissing mandatory connectors: {0}'.format(missing_conn)
#                     if missing_opt:
#                         msg += '\nMissing mandatory ConfigOptions: {0}'.format(missing_opt)
#                     raise ConfigError(msg)
#
#             module_config = self.included_module_configs[module_name].copy()
#             # Complete missing optional config options
#             module_cfg_options = self._available_module_config_options[module_config.module]
#             for name, opt in module_cfg_options.items():
#                 if name not in module_config.config_options and opt.missing != MissingOption.error:
#                     module_config.config_options[name] = opt.default
#             return module_config
#
#     def reset(self):
#         self.included_module_configs = dict()
#         self.stashed_module_configs = dict()
#
#     def save_config_to_file(self, file_path, ignore_incomplete=False):
#         with self._lock:
#             # ToDo: Global section missing
#             # Piece together config dict
#             config_dict = {'gui': dict(), 'logic': dict(), 'hardware': dict()}
#             for module_name, mod_config in self.included_module_configs.items():
#                 if not ignore_incomplete:
#                     missing_conn = self.get_missing_module_connectors(module_name)
#                     missing_opt = self.get_missing_module_cfg_options(module_name)
#                     if missing_conn or missing_opt:
#                         msg = 'Configuration for module "{0}" incomplete.'.format(module_name)
#                         if missing_conn:
#                             msg += '\nMissing mandatory connectors: {0}'.format(missing_conn)
#                         if missing_opt:
#                             msg += '\nMissing mandatory ConfigOptions: {0}'.format(missing_opt)
#                         raise ConfigError(msg)
#                 base, module_class = mod_config.module.split('.', 1)
#                 module_dict = {'module.Class': module_class}
#                 for opt_name, opt_value in mod_config.config_options.items():
#                     try:
#                         module_dict[opt_name] = eval(opt_value)
#                     except:
#                         module_dict[opt_name] = opt_value
#                 if mod_config.connections:
#                     module_dict['connect'] = mod_config.connections.copy()
#                 config_dict[base][module_name] = module_dict
#             # write config to file
#             import pprint
#             pprint.pprint(config_dict)
#             save(file_path, config_dict)
#
#     def load_config_from_file(self, file_path):
#         with self._lock:
#             config_dict = load(file_path)
#             self.reset()
#             modules_ignored = False
#             for base in ('gui', 'logic', 'hardware'):
#                 if not config_dict.get(base, None):
#                     continue
#                 for module_name, mod_dict in config_dict[base].items():
#                     module_class = mod_dict.pop('module.Class')
#                     module = '{0}.{1}'.format(base, module_class)
#                     connections = mod_dict.pop('connect', None)
#                     cfg_options = {opt: repr(val).strip('\'') for opt, val in
#                                    mod_dict.items()} if mod_dict else None
#                     try:
#                         self.include_module(module_name, module, connections, cfg_options)
#                     except ConfigError:
#                         modules_ignored = True
#             if modules_ignored:
#                 log.error('Some modules failed to load from file, probably because module.Class '
#                           'could not be found in Qudi search paths.')
#
#     @property
#     def included_modules(self):
#         with self._lock:
#             return {name: cfg.module for name, cfg in self.included_module_configs.items()}


# class ModuleConfiguration:
#     """
#     """
#     def __init__(self, module_name, module):
#         self.module_name = module_name
#         self.module = module
#         self.connections = dict()
#         self.config_options = dict()
#
#     def __copy__(self):
#         return self.copy()
#
#     def __deepcopy__(self, memodict={}):
#         return self.copy()
#
#     def set_connection(self, connector, module_name):
#         if module_name:
#             self.connections[connector] = module_name
#         else:
#             self.connections.pop(connector, None)
#
#     def set_config_option(self, cfg_option, option_value):
#         if option_value:
#             self.config_options[cfg_option] = copy.deepcopy(option_value)
#         else:
#             self.config_options.pop(cfg_option, None)
#
#     def copy(self):
#         obj = ModuleConfiguration(self.module_name, self.module)
#         obj.connections = copy.deepcopy(self.connections)
#         obj.config_options = copy.deepcopy(self.config_options)
#         return obj


class ModuleConfigurationWidget(QtWidgets.QWidget):
    """
    """
    sigModuleConfigFinished = QtCore.Signal(str, dict, dict)
    sigRemoteConfigFinished = QtCore.Signal(str, dict)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.currently_edited_module = None

        self.cfg_opt_widgets = dict()
        self.conn_widgets = dict()

        self.header_label = QtWidgets.QLabel()
        self.header_label.setAlignment(QtCore.Qt.AlignCenter)
        font = self.header_label.font()
        font.setPointSize(16)
        font.setBold(True)
        font2 = QtGui.QFont(font)
        font2.setPointSize(10)
        self.header_label.setFont(font)
        self.placeholder_label = QtWidgets.QLabel(
            'Select a module from the module tree to include and configure.')
        self.placeholder_label.setFont(font2)
        self.placeholder_label.setAlignment(QtCore.Qt.AlignCenter)
        self.placeholder_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                             QtWidgets.QSizePolicy.Expanding)
        self.footnote_label = QtWidgets.QLabel('* Mandatory Connector/ConfigOption')

        cfg_opt_headers = (QtWidgets.QLabel('Option'), QtWidgets.QLabel('Value'))
        conn_headers = (QtWidgets.QLabel('Connector'), QtWidgets.QLabel('Connect To'))
        cfg_opt_headers[0].setFont(font2)
        cfg_opt_headers[1].setFont(font2)
        conn_headers[0].setFont(font2)
        conn_headers[1].setFont(font2)
        hlines = (QtWidgets.QFrame(), QtWidgets.QFrame())
        hlines[0].setFrameShape(QtWidgets.QFrame.HLine)
        hlines[1].setFrameShape(QtWidgets.QFrame.HLine)
        hlines[0].setFrameShadow(QtWidgets.QFrame.Sunken)
        hlines[1].setFrameShadow(QtWidgets.QFrame.Sunken)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.header_label)
        layout.addWidget(self.placeholder_label)
        layout.addWidget(self.splitter)
        layout.addWidget(self.footnote_label)

        layout.setStretch(1, 1)
        layout.setStretch(2, 1)
        self.setLayout(layout)
        self.splitter.setVisible(False)

        self.left_layout = QtWidgets.QGridLayout()
        self.left_layout.setColumnStretch(1, 1)
        left_scroll = QtWidgets.QScrollArea()
        left_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        left_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        left_scroll.setLayout(self.left_layout)
        left_scroll.setMinimumWidth(200)
        self.right_layout = QtWidgets.QGridLayout()
        self.right_layout.setColumnStretch(1, 1)
        right_scroll = QtWidgets.QScrollArea()
        right_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        right_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        right_scroll.setLayout(self.right_layout)
        right_scroll.setMinimumWidth(200)
        self.splitter.addWidget(left_scroll)
        self.splitter.addWidget(right_scroll)
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        self.left_layout.addWidget(conn_headers[0], 0, 0)
        self.left_layout.addWidget(conn_headers[1], 0, 1)
        self.left_layout.addWidget(hlines[0], 1, 0, 1, 2)
        self.right_layout.addWidget(cfg_opt_headers[0], 0, 0)
        self.right_layout.addWidget(cfg_opt_headers[1], 0, 1)
        self.right_layout.addWidget(hlines[1], 1, 0, 1, 2)
        self.list_spacers = (
            QtWidgets.QSpacerItem(
                1, 1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding),
            QtWidgets.QSpacerItem(
                1, 1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

    def open_module_editor(self, module_name, mandatory_connectors=None, optional_connectors=None,
                           connections=None, mandatory_cfg_options=None, optional_cfg_options=None):
        """
        """
        if module_name != self.currently_edited_module:
            self.commit_module_config()
            if mandatory_connectors is None:
                mandatory_connectors = dict()
            if optional_connectors is None:
                optional_connectors = dict()
            if mandatory_cfg_options is None:
                mandatory_cfg_options = dict()
            if optional_cfg_options is None:
                optional_cfg_options = dict()
            self._clear_layout()
            self.placeholder_label.setVisible(False)
            self.splitter.setVisible(True)
            self.cfg_opt_widgets = dict()
            self.conn_widgets = dict()

            self.header_label.setText(f'Configuration for module "{module_name}"')
            offset = 2
            for ii, (conn_name, compatible) in enumerate(mandatory_connectors.items(), offset):
                label = QtWidgets.QLabel(f'* {conn_name}:')
                label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                combobox = QtWidgets.QComboBox()
                combobox.addItem('Not Connected')
                combobox.addItems(compatible)
                if connections is not None and conn_name in connections:
                    target = connections[conn_name]
                    if target in compatible:
                        combobox.setCurrentText(target)
                self.left_layout.addWidget(label, ii, 0)
                self.left_layout.addWidget(combobox, ii, 1)
                self.conn_widgets[conn_name] = (label, combobox)
            offset += len(mandatory_connectors)
            for ii, (conn_name, compatible) in enumerate(optional_connectors.items(), offset):
                label = QtWidgets.QLabel(f'* {conn_name}:')
                label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                combobox = QtWidgets.QComboBox()
                combobox.addItem('Not Connected')
                combobox.addItems(compatible)
                if connections is not None and conn_name in connections:
                    target = connections[conn_name]
                    if target in compatible:
                        combobox.setCurrentText(target)
                self.left_layout.addWidget(label, ii, 0)
                self.left_layout.addWidget(combobox, ii, 1)
                self.conn_widgets[conn_name] = (label, combobox)
            offset += len(optional_connectors)
            self.left_layout.addItem(self.list_spacers[0], offset, 0, 1, 1)
            offset = 2
            for ii, (opt_name, opt_value) in enumerate(mandatory_cfg_options.items(), offset):
                label = QtWidgets.QLabel(f'* {opt_name}:')
                label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                # value_str = 'null' if opt_value is None else str(opt_value)
                text_editor = QtWidgets.QLineEdit(str(opt_value))
                self.right_layout.addWidget(label, ii, 0)
                self.right_layout.addWidget(text_editor, ii, 1)
                self.cfg_opt_widgets[opt_name] = (label, text_editor)
            offset += len(mandatory_cfg_options)
            for ii, (opt_name, opt_value) in enumerate(optional_cfg_options.items(), offset):
                label = QtWidgets.QLabel(f'{opt_name}:')
                label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                # value_str = 'null' if opt_value is None else str(opt_value)
                text_editor = QtWidgets.QLineEdit(str(opt_value))
                self.right_layout.addWidget(label, ii, 0)
                self.right_layout.addWidget(text_editor, ii, 1)
                self.cfg_opt_widgets[opt_name] = (label, text_editor)
            offset += len(optional_cfg_options)
            self.right_layout.addItem(self.list_spacers[1], offset, 0, 1, 1)
            self.currently_edited_module = module_name

    def commit_module_config(self):
        if self.currently_edited_module is not None:
            connections = {
                conn: combo.currentText() for conn, (_, combo) in self.conn_widgets.items()
            }
            connections = {
                conn: target for conn, target in connections.items() if target != 'Not Connected'
            }
            cfg_option_strings = {
                opt: editor.text().strip() for opt, (_, editor) in self.cfg_opt_widgets.items()
            }
            cfg_options = dict()
            for opt, text in cfg_option_strings.items():
                try:
                    value = None if text == 'null' else eval(text)
                except:
                    value = text
                cfg_options[opt] = value
            self.sigModuleConfigFinished.emit(self.currently_edited_module,
                                              connections,
                                              cfg_options)

    def close_module_editor(self):
        self.commit_module_config()
        self._clear_layout()
        self.placeholder_label.setVisible(True)
        self.splitter.setVisible(False)
        self.header_label.setText('')
        self.currently_edited_module = None

    def _clear_layout(self):
        for label, widget in self.cfg_opt_widgets.values():
            label.setParent(None)
            widget.setParent(None)
            label.deleteLater()
            widget.deleteLater()
        for label, widget in self.conn_widgets.values():
            label.setParent(None)
            widget.setParent(None)
            label.deleteLater()
            widget.deleteLater()
        self.cfg_opt_widgets = dict()
        self.conn_widgets = dict()
        if self.currently_edited_module is not None:
            self.left_layout.removeItem(self.list_spacers[0])
            self.right_layout.removeItem(self.list_spacers[1])


class GlobalConfigurationWidget(QtWidgets.QWidget):
    """
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QtWidgets.QGridLayout()
        layout.setColumnStretch(2, 1)
        self.setLayout(layout)

        header = QtWidgets.QLabel('Global configuration')
        header.setAlignment(QtCore.Qt.AlignCenter)
        font = header.font()
        font.setBold(True)
        font.setPointSize(10)
        header.setFont(font)
        layout.addWidget(header, 0, 0, 1, 3)

        label = QtWidgets.QLabel('Module Server')
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label, 1, 0, 4, 1)
        label = QtWidgets.QLabel('Host address:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.host_lineedit = QtWidgets.QLineEdit('localhost')
        self.host_lineedit.setToolTip('The host address to share Qudi modules with remote machines')
        layout.addWidget(label, 1, 1)
        layout.addWidget(self.host_lineedit, 1, 2)
        label = QtWidgets.QLabel('Port:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.port_spinbox = QtWidgets.QSpinBox()
        self.port_spinbox.setToolTip('Port number for the remote module server')
        self.port_spinbox.setRange(0, 65535)
        self.port_spinbox.setValue(12345)
        layout.addWidget(label, 2, 1)
        layout.addWidget(self.port_spinbox, 2, 2)
        label = QtWidgets.QLabel('Certfile:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.certfile_lineedit = QtWidgets.QLineEdit()
        self.certfile_lineedit.setToolTip('Certificate file path for the remote module server')
        layout.addWidget(label, 3, 1)
        layout.addWidget(self.certfile_lineedit, 3, 2)
        label = QtWidgets.QLabel('Keyfile:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.keyfile_lineedit = QtWidgets.QLineEdit()
        self.keyfile_lineedit.setToolTip('Key file path for the remote module server')
        layout.addWidget(label, 4, 1)
        layout.addWidget(self.keyfile_lineedit, 4, 2)

        label = QtWidgets.QLabel('Startup Modules:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.startup_lineedit = QtWidgets.QLineEdit()
        self.startup_lineedit.setToolTip('Modules to be automatically activated on Qudi startup.\n'
                                         'Separate multiple module names with commas.')
        layout.addWidget(label, 5, 0)
        layout.addWidget(self.startup_lineedit, 5, 1, 1, 2)

        label = QtWidgets.QLabel('Stylesheet:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.stylesheet_lineedit = QtWidgets.QLineEdit('qdark.qss')
        self.stylesheet_lineedit.setToolTip('File name or path for Qudi stylesheet')
        layout.addWidget(label, 6, 0)
        layout.addWidget(self.stylesheet_lineedit, 6, 1, 1, 2)

        label = QtWidgets.QLabel('Extension Paths:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.extensions_lineedit = QtWidgets.QLineEdit()
        self.extensions_lineedit.setToolTip('Extension module search paths for Qudi.\nSeparate '
                                            'multiple paths with commas.')
        layout.addWidget(label, 7, 0)
        layout.addWidget(self.extensions_lineedit, 7, 1, 1, 2)


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
