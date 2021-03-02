# -*- coding: utf-8 -*-
"""

"""

import pprint
import os
import sys
import importlib
import inspect
from collections import OrderedDict
from functools import partial
from PySide2 import QtCore, QtGui, QtWidgets
from qudi.util.mutex import RecursiveMutex
from qudi.core.connector import Connector
from qudi.core.configoption import ConfigOption, MissingOption
from qudi.core.paths import get_main_dir, get_default_config_dir
from qudi.core.logger import get_logger
from qudi.core.module import Base, LogicBase, GuiBase
from qudi.core.config import save, load

from module_selector import ModuleSelector
from tree_widgets import ConfigModulesTreeWidget

import matplotlib
matplotlib.use('agg')

log = get_logger(__name__)


class ConfigError(Exception):
    pass


class QudiEnvironment:
    """
    """
    def __init__(self, module_search_paths=None):
        # Import all modules available in qudi installation directory and given search paths
        if module_search_paths is None:
            module_search_paths = [get_main_dir()]
        else:
            module_search_paths = [get_main_dir(), *module_search_paths]
        self.module_finder = ModuleFinder(module_search_paths)

        # Find for each connector in each module compatible modules to connect to
        self._module_valid_modules_to_connect = dict()
        for module_key in self.module_finder.module_classes:
            self.find_available_modules_for_module_connectors(module_key)

    def find_available_modules_for_module_connectors(self, module_key):
        compatible_dict = dict()
        for conn_name, conn in self.module_finder.module_connectors[module_key].items():
            valid_modules = self.find_available_modules_for_connector(conn)
            compatible_dict[conn_name] = valid_modules
        self._module_valid_modules_to_connect[module_key] = compatible_dict

    def find_available_modules_for_connector(self, connector):
        compatible_modules = list()
        if isinstance(connector.interface, str):
            interface_name = connector.interface
            interface_class = self.get_interface_class_by_name(interface_name)
        else:
            interface_class = connector.interface
            interface_name = interface_class.__name__

        for module, cls in self.module_finder.module_classes.items():
            if interface_class is None and cls.__name__ == interface_name:
                compatible_modules.append(module)
            elif interface_class is not None and issubclass(cls, interface_class):
                compatible_modules.append(module)
        return compatible_modules

    def get_interface_class_by_name(self, cls_name):
        for module, cls in self.module_finder.interface_classes.items():
            if cls.__name__ == cls_name:
                return cls
        return None

    @property
    def compatible_module_connector_targets(self):
        return self._module_valid_modules_to_connect

    @property
    def available_module_connectors(self):
        return self.module_finder.module_connectors

    @property
    def available_module_config_options(self):
        return self.module_finder.module_config_options


class ModuleFinder:

    def __init__(self, module_search_paths):
        self.search_paths = set()
        self.module_classes = dict()
        self.module_connectors = dict()
        self.module_config_options = dict()
        self.interface_classes = dict()

        self.add_search_paths_to_path(module_search_paths)
        self.find_modules(module_search_paths)

    def __del__(self):
        try:
            self.remove_search_paths_from_path()
        except:
            pass

    def remove_search_paths_from_path(self):
        for path in self.search_paths:
            if path in sys.path:
                sys.path.remove(path)
        self.search_paths = set()

    def add_search_paths_to_path(self, module_search_paths):
        for path in reversed(module_search_paths):
            if path in sys.path:
                sys.path.remove(path)
            sys.path.insert(1, path)
            self.search_paths.add(path)

    def find_modules(self, search_paths):
        self.module_classes = dict()
        self.module_connectors = dict()
        self.module_config_options = dict()
        self.interface_classes = dict()

        if isinstance(search_paths, str):
            search_paths = [search_paths]
        search_paths = list(search_paths)

        invalid_paths = list()
        for path in search_paths:
            if not os.path.isdir(path):
                invalid_paths.append(path)
                log.error('Non-existent path "{0}" to search in. Ignoring this path.'.format(path))
        if invalid_paths:
            for path in invalid_paths:
                search_paths.remove(path)

        for path in search_paths:
            # Find qudi modules and interfaces
            for base in ('gui', 'logic', 'hardware', 'interface'):
                for root, _, files in os.walk(os.path.join(path, base)):
                    for file in files:
                        if not file.endswith('.py'):
                            continue
                        module_name_comp = os.path.normpath(root).split(os.sep)
                        index = module_name_comp.index(base)
                        module_name_comp.append(file[:-3])
                        module_name = '.'.join(module_name_comp[index:])
                        try:
                            module = importlib.import_module(module_name)
                        except:
                            log.exception(
                                'Error during import of module "{0}":'.format(module_name))
                            continue
                        if base == 'interface':
                            for cls_name, cls in self.find_qudi_interfaces_in_module(
                                    module).items():
                                if cls_name in self.interface_classes:
                                    log.warning(
                                        'Qudi interface "{0}" overwritten by newly found occurrence'
                                        ' in search path "{1}".'.format(cls_name, path))
                                self.interface_classes[cls_name] = cls
                        else:
                            for cls_name, cls in self.find_qudi_classes_in_module(module).items():
                                mod_class_name = '{0}.{1}'.format(module_name, cls_name)
                                if mod_class_name in self.module_classes:
                                    log.warning(
                                        'Qudi module "{0}" (module.Class) overwritten by newly '
                                        'found occurrence in search path "{1}".'
                                        ''.format(mod_class_name, path))
                                self.module_classes[mod_class_name] = cls
                                self.module_config_options[
                                    mod_class_name] = self.get_module_config_options(cls)
                                self.module_connectors[mod_class_name] = self.get_module_connectors(
                                    cls)

    @classmethod
    def find_qudi_classes_in_module(cls, module):
        return dict(m for m in inspect.getmembers(module, cls.is_qudi_class) if
                    m[1].__module__ == module.__name__)

    @classmethod
    def find_qudi_interfaces_in_module(cls, module):
        return dict(m for m in inspect.getmembers(module, cls.is_qudi_interface) if
                    m[1].__module__ == module.__name__)

    @classmethod
    def get_module_connectors(cls, mod_class):
        connectors = dict()
        for attr_name, conn in inspect.getmembers(mod_class, cls.is_connector):
            if conn.name is None:
                connectors[attr_name] = conn
            else:
                connectors[conn.name] = conn
        return connectors

    @classmethod
    def get_module_config_options(cls, mod_class):
        config_options = dict()
        for attr_name, cfg_opt in inspect.getmembers(mod_class, cls.is_config_option):
            if cfg_opt.name is None:
                config_options[attr_name] = cfg_opt
            else:
                config_options[cfg_opt.name] = cfg_opt
        config_options['remoteaccess'] = ConfigOption('remoteaccess')
        return config_options

    @staticmethod
    def is_connector(obj):
        return isinstance(obj, Connector)

    @staticmethod
    def is_config_option(obj):
        return isinstance(obj, ConfigOption)

    @classmethod
    def is_qudi_interface(cls, obj):
        return cls.is_qudi_class(obj) and inspect.isabstract(obj) and \
               not issubclass(obj, (LogicBase, GuiBase))

    @staticmethod
    def is_qudi_class(obj):
        base_classes = (Base, LogicBase, GuiBase)
        return inspect.isclass(obj) and issubclass(obj, Base) and obj not in base_classes


class QudiConfiguration:
    """
    """
    _remote_options = ('remote', 'certfile', 'keyfile')

    def __init__(self, available_module_config_options, available_module_connectors):
        self._lock = RecursiveMutex()
        self._available_module_config_options = available_module_config_options
        self._available_module_connectors = available_module_connectors
        self.included_module_configs = dict()
        self.stashed_module_configs = dict()

    def include_module(self, module_name, module, connections=None, config_options=None):
        with self._lock:
            if module not in self._available_module_config_options:
                raise ConfigError('No module "{0}" found in qudi environment.'.format(module))
            if module_name in self.stashed_module_configs and self.stashed_module_configs[
                module_name].module == module:
                self.included_module_configs[module_name] = self.stashed_module_configs.pop(
                    module_name)
            elif module_name not in self.included_module_configs or self.included_module_configs[
                module_name].module != module:
                self.included_module_configs[module_name] = ModuleConfiguration(module_name, module)
            module_config = self.included_module_configs[module_name]
            if connections is not None:
                for connector, module_name in connections.items():
                    module_config.set_connection(connector, module_name)
            if config_options is not None:
                for cfg_option, option_value in config_options.items():
                    module_config.set_config_option(cfg_option, option_value)

    def exclude_module(self, module_name):
        with self._lock:
            if module_name in self.included_module_configs:
                self.stashed_module_configs[module_name] = self.included_module_configs.pop(
                    module_name)

    def set_module_connection(self, module_name, connector, target_module, ignore_missing=False):
        with self._lock:
            module_config = self.included_module_configs.get(module_name, None)
            if module_config is None:
                raise ConfigError(
                    'No module with name "{0}" included in configuration.'.format(module_name))
            if connector not in self._available_module_connectors[module_config.module]:
                raise ConfigError(
                    'Connector "{0}" not found in module "{1}".'.format(connector, module_name))
            if target_module == 'Not Connected':
                target_module = None
            elif not ignore_missing and target_module not in self.included_module_configs:
                raise ConfigError('Module to connect with name "{0}" is not included in config.'
                                  ''.format(target_module))
            module_config.set_connection(connector, target_module)

    def set_module_config_option(self, module_name, cfg_option, option_value):
        with self._lock:
            module_config = self.included_module_configs.get(module_name, None)
            if module_config is None:
                raise ConfigError(
                    'No module with name "{0}" included in configuration.'.format(module_name))
            if cfg_option not in self._available_module_config_options[module_config.module]:
                if cfg_option not in self._remote_options:
                    raise ConfigError('ConfigOption "{0}" invalid for module "{1}".'
                                      ''.format(cfg_option, module_name))
            module_config.set_config_option(cfg_option, option_value)

    def get_missing_module_connectors(self, module_name):
        with self._lock:
            module_config = self.included_module_configs.get(module_name, None)
            if module_config is None:
                raise ConfigError(
                    'No module with name "{0}" included in configuration.'.format(module_name))
            module_connectors = self._available_module_connectors[module_config.module]
            mandatory = {name for name, conn in module_connectors.items() if not conn.optional}
            return sorted(conn for conn in mandatory if conn not in module_config.connections)

    def get_missing_module_cfg_options(self, module_name):
        with self._lock:
            module_config = self.included_module_configs.get(module_name, None)
            if module_config is None:
                raise ConfigError(
                    'No module with name "{0}" included in configuration.'.format(module_name))
            module_cfg_options = self._available_module_config_options[module_config.module]
            mandatory = {name for name, opt in module_cfg_options.items() if
                         opt.missing == MissingOption.error}
            return sorted(opt for opt in mandatory if opt not in module_config.config_options)

    def get_module_config(self, module_name, ignore_incomplete=False):
        with self._lock:
            if module_name not in self.included_module_configs:
                raise ConfigError(
                    'No module with name "{0}" included in configuration.'.format(module_name))
            if not ignore_incomplete:
                missing_conn = self.get_missing_module_connectors(module_name)
                missing_opt = self.get_missing_module_cfg_options(module_name)
                if missing_conn or missing_opt:
                    msg = 'Configuration for module "{0}" incomplete.'.format(module_name)
                    if missing_conn:
                        msg += '\nMissing mandatory connectors: {0}'.format(missing_conn)
                    if missing_opt:
                        msg += '\nMissing mandatory ConfigOptions: {0}'.format(missing_opt)
                    raise ConfigError(msg)

            module_config = self.included_module_configs[module_name].copy()
            # Complete missing optional config options
            module_cfg_options = self._available_module_config_options[module_config.module]
            for name, opt in module_cfg_options.items():
                if name not in module_config.config_options and opt.missing != MissingOption.error:
                    module_config.config_options[name] = opt.default
            return module_config

    def reset(self):
        self.included_module_configs = dict()
        self.stashed_module_configs = dict()

    def save_config_to_file(self, file_path, ignore_incomplete=False):
        with self._lock:
            # ToDo: Global section missing
            # Piece together config dict
            config_dict = OrderedDict(
                (('gui', OrderedDict()), ('logic', OrderedDict()), ('hardware', OrderedDict()),)
            )
            for module_name, mod_config in self.included_module_configs.items():
                if not ignore_incomplete:
                    missing_conn = self.get_missing_module_connectors(module_name)
                    missing_opt = self.get_missing_module_cfg_options(module_name)
                    if missing_conn or missing_opt:
                        msg = 'Configuration for module "{0}" incomplete.'.format(module_name)
                        if missing_conn:
                            msg += '\nMissing mandatory connectors: {0}'.format(missing_conn)
                        if missing_opt:
                            msg += '\nMissing mandatory ConfigOptions: {0}'.format(missing_opt)
                        raise ConfigError(msg)
                base, module_class = mod_config.module.split('.', 1)
                module_dict = OrderedDict((('module.Class', module_class),))
                for opt_name, opt_value in mod_config.config_options.items():
                    try:
                        module_dict[opt_name] = eval(opt_value)
                    except:
                        module_dict[opt_name] = opt_value
                if mod_config.connections:
                    module_dict['connect'] = OrderedDict(mod_config.connections)
                config_dict[base][module_name] = module_dict
            # write config to file
            save(file_path, config_dict)

    def load_config_from_file(self, file_path):
        with self._lock:
            config_dict = load(file_path)
            self.reset()
            modules_ignored = False
            for base in ('gui', 'logic', 'hardware'):
                if not config_dict.get(base, None):
                    continue
                for module_name, mod_dict in config_dict[base].items():
                    module_class = mod_dict.pop('module.Class')
                    module = '{0}.{1}'.format(base, module_class)
                    connections = mod_dict.pop('connect', None)
                    cfg_options = {opt: repr(val).strip('\'') for opt, val in
                                   mod_dict.items()} if mod_dict else None
                    try:
                        self.include_module(module_name, module, connections, cfg_options)
                    except ConfigError:
                        modules_ignored = True
            if modules_ignored:
                log.error('Some modules failed to load from file, probably because module.Class '
                          'could not be found in Qudi search paths.')

    @property
    def included_modules(self):
        with self._lock:
            return {name: cfg.module for name, cfg in self.included_module_configs.items()}


class ModuleConfiguration:
    """
    """
    def __init__(self, module_name, module):
        self.module_name = module_name
        self.module = module
        self.connections = dict()
        self.config_options = dict()

    def set_connection(self, connector, module_name):
        if module_name:
            self.connections[connector] = module_name
        else:
            self.connections.pop(connector, None)

    def set_config_option(self, cfg_option, option_value):
        if option_value:
            self.config_options[cfg_option] = option_value
        else:
            self.config_options.pop(cfg_option, None)

    def copy(self):
        obj = ModuleConfiguration(self.module_name, self.module)
        obj.connections = self.connections.copy()
        obj.config_options = self.config_options.copy()
        return obj


class ModuleConfigurationWidget(QtWidgets.QWidget):
    """
    """
    sigSetConfigOption = QtCore.Signal(str, str, str)
    sigSetConnection = QtCore.Signal(str, str, str)

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

    def open_module_editor(self, module_name, avail_connectors, avail_cfg_options, module_cfg=None):
        """
        """
        if module_name != self.currently_edited_module:
            self._clear_layout()
            self.placeholder_label.setVisible(False)
            self.splitter.setVisible(True)
            self.cfg_opt_widgets = dict()
            self.conn_widgets = dict()

            self.header_label.setText('Configuration for module "{0}"'.format(module_name))
            for ii, (conn_name, compatible) in enumerate(avail_connectors.items(), 2):
                label = QtWidgets.QLabel('{0}:'.format(conn_name))
                label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                combobox = QtWidgets.QComboBox()
                combobox.addItem('Not Connected')
                combobox.addItems(compatible)
                self.left_layout.addWidget(label, ii, 0)
                self.left_layout.addWidget(combobox, ii, 1)
                combobox.currentIndexChanged[str].connect(partial(self._set_connection, conn_name))
                self.conn_widgets[conn_name] = (label, combobox)
            self.left_layout.addItem(self.list_spacers[0], len(avail_connectors) + 2, 0, 1, 1)
            for ii, cfg_option in enumerate(avail_cfg_options, 2):
                label = QtWidgets.QLabel('{0}:'.format(cfg_option))
                label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                text_editor = QtWidgets.QLineEdit()
                self.right_layout.addWidget(label, ii, 0)
                self.right_layout.addWidget(text_editor, ii, 1)
                text_editor.textEdited.connect(partial(self._set_config_option, cfg_option))
                self.cfg_opt_widgets[cfg_option] = (label, text_editor)
            self.right_layout.addItem(self.list_spacers[1], len(avail_cfg_options) + 2, 0, 1, 1)
            self.currently_edited_module = module_name

        if module_cfg is not None:
            for cfg_opt, opt_value in module_cfg.config_options.items():
                self.cfg_opt_widgets[cfg_opt][1].setText(opt_value)
            for conn, target in module_cfg.connections.items():
                self.conn_widgets[conn][1].setCurrentText(target)

    def close_module_editor(self):
        self._clear_layout()
        self.placeholder_label.setVisible(True)
        self.splitter.setVisible(False)
        self.header_label.setText('')
        self.currently_edited_module = None
        self.cfg_opt_widgets = dict()
        self.conn_widgets = dict()

    def _clear_layout(self):
        for label, widget in self.cfg_opt_widgets.values():
            widget.textEdited.disconnect()
            label.setParent(None)
            widget.setParent(None)
        for label, widget in self.conn_widgets.values():
            widget.currentIndexChanged[str].disconnect()
            label.setParent(None)
            widget.setParent(None)
        if self.currently_edited_module is not None:
            self.left_layout.removeItem(self.list_spacers[0])
            self.right_layout.removeItem(self.list_spacers[1])

    def _set_config_option(self, cfg_option, value):
        self.sigSetConfigOption.emit(self.currently_edited_module, cfg_option, value.strip())

    def _set_connection(self, connector, target):
        if target:
            self.sigSetConnection.emit(self.currently_edited_module, connector, target)


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
    def __init__(self, qudi_environment, qudi_configuration, **kwargs):
        super().__init__(**kwargs)
        self.qudi_environment = qudi_environment
        self.qudi_configuration = qudi_configuration
        self.config_save_path = None

        self.setWindowTitle('Qudi Config Editor')
        screen_size = QtWidgets.QApplication.instance().primaryScreen().availableSize()
        width = (screen_size.width() * 3) // 4
        height = (screen_size.height() * 3) // 4
        self.resize(width, height)

        self.module_tree_widget = ConfigModulesTreeWidget()
        self.module_config_widget = ModuleConfigurationWidget()
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
        self.module_config_widget.sigSetConfigOption.connect(
            self.qudi_configuration.set_module_config_option)
        self.module_config_widget.sigSetConnection.connect(
            self.qudi_configuration.set_module_connection)

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
        module = '{0}.{1}'.format(item.parent().text(0).lower(), item.text(2))
        module_name = item.text(1)
        if self.module_config_widget.currently_edited_module != module_name:
            compatible_conn = self.qudi_environment.compatible_module_connector_targets[module]
            avail_conn = dict()
            for conn, compatible_modules in compatible_conn.items():
                avail_conn[conn] = [name for name, module in
                                    self.qudi_configuration.included_modules.items() if
                                    module in compatible_modules]
            avail_cfg_opt = self.qudi_environment.available_module_config_options[module]
            module_config = self.qudi_configuration.get_module_config(module_name, ignore_incomplete=True)
            self.module_config_widget.open_module_editor(module_name=module_name,
                                                         avail_connectors=avail_conn,
                                                         avail_cfg_options=avail_cfg_opt,
                                                         module_cfg=module_config)

    def select_modules(self):
        dialog = ModuleSelector(
            self,
            available_modules=tuple(self.qudi_environment.compatible_module_connector_targets),
            selected_modules=self.qudi_configuration.included_modules)
        if dialog.exec():
            if self.module_config_widget.currently_edited_module is not None:
                self.module_config_widget.close_module_editor()
            new_selection = dialog.selected_modules
            # Throw out all modules that are no longer present
            for module_name in self.qudi_configuration.included_modules:
                if module_name not in new_selection:
                    self.qudi_configuration.exclude_module(module_name)
            # Add new modules or overwrite
            for module_name, module in new_selection.items():
                self.qudi_configuration.include_module(module_name, module)
            self.module_tree_widget.set_modules(self.qudi_configuration.included_modules)

    def clear_config(self):
        self.config_save_path = None
        self.module_config_widget.close_module_editor()
        self.qudi_configuration.reset()
        self.module_tree_widget.set_modules(dict())

    def prompt_load_config(self):
        file_path = QtWidgets.QFileDialog.getOpenFileName(
            self,
            'Qudi Config Editor: Load Configuration...',
            get_default_config_dir(),
            'Config files (*.cfg)')[0]
        if file_path:
            self.clear_config()
            self.config_save_path = file_path
            self.qudi_configuration.load_config_from_file(file_path)
            self.module_tree_widget.set_modules(self.qudi_configuration.included_modules)

    def prompt_save_config(self):
        file_path = QtWidgets.QFileDialog.getSaveFileName(
            self,
            'Qudi Config Editor: Save Configuration...',
            get_default_config_dir(),
            'Config files (*.cfg)')[0]
        if file_path:
            self.config_save_path = file_path
            self.save_config()

    def save_config(self):
        # ToDo: Check for complete config
        if self.config_save_path is None:
            self.prompt_save_config()
        else:
            self.qudi_configuration.save_config_to_file(self.config_save_path)

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


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    qudi_env = QudiEnvironment()
    qudi_config = QudiConfiguration(qudi_env.available_module_config_options,
                                    qudi_env.available_module_connectors)
    # qudi_config.load_config_from_file('C:\\Users\\neverhorst\\qudi\\config\\test.cfg')
    # qudi_config.save_config_to_file('C:\\Users\\neverhorst\\qudi\\config\\test2.cfg')
    mw = ConfigurationEditor(qudi_env, qudi_config)
    mw.show()
    sys.exit(app.exec_())
