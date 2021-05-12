# -*- coding: utf-8 -*-

"""
This file contains the Qudi configuration file module.

A configuration file is saved in YAML format. This module provides a custom loader and a dumper
using PyYAML.
Additionally, it fixes a bug in PyYAML with scientific notation and allows
to dump numpy dtypes and numpy ndarrays.

The fix of the scientific notation is applied globally at module import.


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

__all__ = ('Configuration', 'QudiSafeRepresenter', 'QudiSafeConstructor', 'QudiYAML', 'load',
           'save', 'yaml_load', 'yaml_dump')

import os
import re
import copy
import numpy as np
import ruamel.yaml as _yaml
from warnings import warn
from collections import OrderedDict
from io import BytesIO, TextIOWrapper
from PySide2 import QtCore

import qudi.core.paths as _paths


class QudiSafeRepresenter(_yaml.SafeRepresenter):
    """ Custom YAML representer for qudi config files
    """
    ndarray_max_size = 20

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._extndarray_count = 0

    def ignore_aliases(self, ignore_data):
        """ Ignore aliases and anchors. Overwrites base class implementation.
        """
        return True

    def represent_numpy_int(self, data):
        """ Representer for numpy int scalars
        """
        return self.represent_int(data.item())

    def represent_numpy_float(self, data):
        """ Representer for numpy float scalars
        """
        return self.represent_float(data.item())

    def represent_numpy_complex(self, data):
        """ Representer for numpy complex scalars
        """
        return self.represent_complex(data.item())

    def represent_dict_no_sort(self, data):
        """ Representer for dict and OrderedDict to prevent ruamel.yaml from sorting keys
        """
        return self.represent_dict(data.items())

    def represent_complex(self, data):
        """ Representer for builtin complex type
        """
        return self.represent_scalar(tag='tag:yaml.org,2002:complex', value=str(data))

    def represent_frozenset(self, data):
        """ Representer for builtin frozenset type
        """
        node = self.represent_set(data)
        node.tag = 'tag:yaml.org,2002:frozenset'
        return node

    def represent_ndarray(self, data):
        """ Representer for numpy.ndarrays.
        Will represent the array in binary representation as ASCII-encoded string by default.
        If the output stream to dump to is a "regular" open text file handle (io.TextIOWrapper) and
        the array size exceeds the specified maximum ndarray size, it is dumped into a separate
        binary .npy file and is represented in YAML as file path string.
        """
        # Write to separate file if possible and required (array size > self.ndarray_max_size)
        # FIXME: Find a better way... this is a mean hack to get the file path to dump,
        if isinstance(self.dumper._output, TextIOWrapper) and data.size > self.ndarray_max_size:
            try:
                out_stream_path = self.dumper._output.name
                dir_path = os.path.dirname(out_stream_path)
                file_name = os.path.splitext(os.path.basename(out_stream_path))[0]
                file_path = f'{os.path.join(dir_path, file_name)}-{self._extndarray_count:06}.npy'
                np.save(file_path, data, allow_pickle=False, fix_imports=False)
                self._extndarray_count += 1
                return self.represent_scalar(tag='tag:yaml.org,2002:extndarray', value=file_path)
            except:
                pass

        # Represent as binary stream (ASCII-encoded) by default
        with BytesIO() as f:
            np.save(f, data, allow_pickle=False, fix_imports=False)
            binary_repr = f.getvalue()
        node = self.represent_binary(binary_repr)
        node.tag = 'tag:yaml.org,2002:ndarray'
        return node


# register custom representers
QudiSafeRepresenter.add_representer(frozenset, QudiSafeRepresenter.represent_frozenset)
QudiSafeRepresenter.add_representer(complex, QudiSafeRepresenter.represent_complex)
QudiSafeRepresenter.add_representer(dict, QudiSafeRepresenter.represent_dict_no_sort)
QudiSafeRepresenter.add_representer(OrderedDict, QudiSafeRepresenter.represent_dict_no_sort)
QudiSafeRepresenter.add_representer(np.ndarray, QudiSafeRepresenter.represent_ndarray)
QudiSafeRepresenter.add_multi_representer(np.integer, QudiSafeRepresenter.represent_numpy_int)
QudiSafeRepresenter.add_multi_representer(np.floating, QudiSafeRepresenter.represent_numpy_float)
QudiSafeRepresenter.add_multi_representer(np.complexfloating,
                                          QudiSafeRepresenter.represent_numpy_complex)


class QudiSafeConstructor(_yaml.SafeConstructor):
    """ Custom YAML constructor for qudi config files
    """

    def construct_ndarray(self, node):
        """ The constructor for a numpy array that is saved as binary string with ASCII-encoding
        """
        value = self.construct_yaml_binary(node)
        with BytesIO(value) as f:
            return np.load(f)

    def construct_extndarray(self, node):
        """ The constructor for a numpy array that is saved in a separate file.
        """
        return np.load(self.construct_yaml_str(node), allow_pickle=False, fix_imports=False)

    def construct_frozenset(self, node):
        """ The frozenset constructor.
        """
        try:
            # FIXME: The returned generator does not properly work with iteration using next()
            return frozenset(tuple(self.construct_yaml_set(node))[0])
        except IndexError:
            return frozenset()

    def construct_complex(self, node):
        """ The complex constructor.
        """
        return complex(self.construct_yaml_str(node))


# register custom constructors
QudiSafeConstructor.add_constructor('tag:yaml.org,2002:frozenset',
                                    QudiSafeConstructor.construct_frozenset)
QudiSafeConstructor.add_constructor('tag:yaml.org,2002:complex',
                                    QudiSafeConstructor.construct_complex)
QudiSafeConstructor.add_constructor('tag:yaml.org,2002:ndarray',
                                    QudiSafeConstructor.construct_ndarray)
QudiSafeConstructor.add_constructor('tag:yaml.org,2002:extndarray',
                                    QudiSafeConstructor.construct_extndarray)


class QudiYAML(_yaml.YAML):
    """ ruamel.yaml.YAML subclass to be used by qudi for all loading/dumping purposes.
    Will always use the 'safe' option without round-trip functionality.
    """

    def __init__(self, **kwargs):
        """
        @param kwargs: Keyword arguments accepted by ruamel.yaml.YAML(), excluding "typ"
        """
        kwargs['typ'] = 'safe'
        super().__init__(**kwargs)
        self.default_flow_style = False
        self.Representer = QudiSafeRepresenter
        self.Constructor = QudiSafeConstructor


def yaml_load(stream):
    """ Loads YAML formatted data from stream and puts it into a dict.
    Uses the custom QudiYAML class.

    @param stream: stream the data is read from. Must be compatible to ruamel.yaml.YAML.load().

    @return dict: Dict containing data. If stream is empty then an empty dict is returned
    """
    data = QudiYAML().load(stream)
    # yaml returns None if the stream was empty
    return dict() if data is None else data


def yaml_dump(data, stream):
    """ Dumps dict data into a YAML formatted stream.

    @param dict data: the data to dump
    @param stream: stream to dump the data into. Must be compatible to ruamel.yaml.YAML.dump().
    """
    return QudiYAML().dump(data, stream)


def load(file_path, ignore_missing=False):
    """ Loads a qudi style YAML file. Throws a FileNotFoundError if the file does not exist

    @param str file_path: path to config file
    @param bool ignore_missing: optional, flag to suppress FileNotFoundError

    @return dict: The data as python/numpy objects in a dict
    """
    try:
        with open(file_path, 'r') as f:
            return yaml_load(f)
    except FileNotFoundError:
        if ignore_missing:
            return dict()
        else:
            raise


def save(file_path, data):
    """ Saves data to file_path in qudi style YAML format. Creates subdirectories if needed.

    @param str file_path: path to YAML file to save data into
    @param dict data: Dict containing the data to save to file
    """
    file_dir = os.path.dirname(file_path)
    if file_dir:
        try:
            os.makedirs(file_dir)
        except FileExistsError:
            pass
    with open(file_path, 'w') as f:
        yaml_dump(data, f)


class Configuration(QtCore.QObject):
    """
    """

    sigConfigChanged = QtCore.Signal(object)

    _forbidden_options = {
        'module.Class', 'allow_remote', 'connect', 'remote_url', 'keyfile', 'certfile'
    }
    _allowed_remote_bases = {'logic', 'hardware'}  # ToDo: Should logic modules be excluded here?

    _module_name_regex = re.compile(r'^\w+(\s\w+)*$')

    def __init__(self, *args, file_path=None, **kwargs):
        super().__init__(*args, **kwargs)
        assert file_path is None or file_path.endswith('.cfg'), \
            'Config file must have ".cfg" file extension.'

        self._file_path = file_path

        # main config fields
        self._global_config = dict()
        self._module_config = {'hardware': dict(), 'logic': dict(), 'gui': dict()}
        self._unhandled_config = dict()

    @property
    def config_file(self):
        return self._file_path

    @property
    def global_config(self):
        return self._global_config

    @property
    def module_config(self):
        return self._module_config

    @property
    def unhandled_config(self):
        return self._unhandled_config

    @unhandled_config.setter
    def unhandled_config(self, cfg_dict):
        if cfg_dict is None:
            cfg_dict = dict()
        assert isinstance(cfg_dict, dict), 'unhandled_config must be None or dict type'
        assert all(key not in cfg_dict for key in ('global', *self._module_config)), \
            'Reserved top-level config key(s) encountered in unhandled_config dict'
        self._unhandled_config = copy.deepcopy(cfg_dict)
        self.sigConfigChanged.emit(self)

    @property
    def config_dict(self):
        conf_dict = dict()
        if self._global_config:
            conf_dict['global'] = self._global_config
        conf_dict.update(self._module_config)
        conf_dict.update(self._unhandled_config)
        return conf_dict

    @property
    def module_names(self):
        return (*self._module_config['hardware'],
                *self._module_config['logic'],
                *self._module_config['gui'])

    @property
    def startup_modules(self):
        """ List of module names to automatically activate when starting qudi.

        @return list|None: List of module names to activate when starting qudi.
        """
        return self._global_config.get('startup', list()).copy()

    @startup_modules.setter
    def startup_modules(self, modules):
        """ Setter for list of module names to automatically activate when starting qudi.

        @param list|None modules: List of module names to activate when starting qudi.
        """
        if not modules:
            self._global_config.pop('startup', None)
            return

        if isinstance(modules, str):
            modules = [modules]

        assert all(isinstance(mod, str) and mod for mod in modules), \
            'Startup modules must be non-empty strings'
        self._global_config['startup'] = list(modules)
        self.sigConfigChanged.emit(self)

    @property
    def remote_modules_server(self):
        if 'remote_modules_server' not in self._global_config:
            return None
        return copy.deepcopy(self._global_config['remote_modules_server'])

    @remote_modules_server.setter
    def remote_modules_server(self, server_settings):
        # ToDo: Sanity checks
        if not server_settings:
            self._global_config.pop('remote_modules_server', None)
            return
        self._global_config['remote_modules_server'] = copy.deepcopy(server_settings)
        self.sigConfigChanged.emit(self)

    @property
    def namespace_server_port(self):
        return self._global_config.get('namespace_server_port', 18861)

    @namespace_server_port.setter
    def namespace_server_port(self, port):
        port = int(port)
        assert 0 <= port <= 65535
        self._global_config['namespace_server_port'] = port
        self.sigConfigChanged.emit(self)

    @property
    def stylesheet(self):
        """ Absolute .qss file path used as stylesheet for qudi Qt application.

        @return str|None: Absolute file path to stylesheet file, None if not configured
        """
        stylesheet = self._global_config.get('stylesheet', None)
        if not os.path.dirname(stylesheet):
            stylesheet = os.path.join(_paths.get_artwork_dir(), 'styles', stylesheet)
        return os.path.abspath(stylesheet)

    @stylesheet.setter
    def stylesheet(self, file_path):
        """ Setter for .qss file path used as stylesheet for qudi Qt application.
        Can either be a relative path to <qudi>/artwork/styles/ or an absolute path.

        If stylesheet path is set to None, it will be removed from config. This will cause the
        application to fall back to platform dependent Qt defaults.

        @param str|None file_path: Absolute file path to stylesheet or file name
        """
        assert file_path is None or isinstance(file_path, str), 'stylesheet must be None or str'

        if not file_path:
            self._global_config.pop('stylesheet', None)
            return

        assert file_path.endswith('.qss'), 'stylesheet file must have ".qss" extension'
        if not os.path.isabs(file_path):
            assert not os.path.dirname(file_path), \
                'stylesheet must either be file name or absolute path'

        self._global_config['stylesheet'] = file_path
        self.sigConfigChanged.emit(self)

    @property
    def default_data_dir(self):
        """ Absolute path to qudi default data root directory to save (measurement) data into.

        @return str|None: Absolute file path to data directory, None if not configured
        """
        return self._global_config.get('default_data_dir', None)

    @default_data_dir.setter
    def default_data_dir(self, dir_path):
        """ Setter for qudi default data root directory. Must be specified as absolute path.

        If default_data_dir path is set to None, it will be removed from config. This will cause
        qudi to fall back to <user home>/qudi/data/.

        @param str|None dir_path: absolute or relative path to data directory
        """
        assert dir_path is None or isinstance(dir_path, str), 'default_data_dir must be None or str'

        if not dir_path:
            self._global_config.pop('default_data_dir', None)
            return

        assert os.path.isabs(dir_path), 'default_data_dir must be absolute path to directory'

        self._global_config['default_data_dir'] = os.path.abspath(dir_path)
        self.sigConfigChanged.emit(self)

    @property
    def extension_paths(self):
        """ List of absolute paths to extend qudi module search paths with.

        @return list: List of absolute directory paths to search for qudi modules.
        """
        return self._global_config.get('extensions', list()).copy()

    @extension_paths.setter
    def extension_paths(self, paths):
        """ Setter for absolute paths to extend qudi module search paths with.

        If extension_paths is set to None, it will be removed from config. This will cause
        qudi to only consider modules within the qudi package.

        @param list|None paths: absolute paths to extend qudi search paths with
        """
        if not paths:
            self._global_config.pop('extensions', None)
            return

        if isinstance(paths, str):
            paths = [paths]

        assert all(os.path.isabs(path) for path in paths), 'extension_paths must be absolute paths'

        self._global_config['extensions'] = list(paths)
        self.sigConfigChanged.emit(self)

    def add_local_module(self, name, base, module, cls):
        self.check_module_name(name)
        assert isinstance(module, str) and module, 'qudi module config module must be non-empty str'
        assert isinstance(cls, str) and cls, 'qudi module config cls must be non-empty str'
        assert base in self._module_config, f'module base must be in {tuple(self._module_config)}'
        assert name not in self.module_names, f'Module by name "{name}" already defined in config'
        self._module_config[base][name] = {'module.Class': f'{module}.{cls}', 'allow_remote': False}
        self.sigConfigChanged.emit(self)

    def add_remote_module(self, name, base, remote_url):
        self.check_module_name(name)
        assert isinstance(remote_url, str) and remote_url, \
            'qudi module config remote_url must be non-empty str'
        assert base in self._allowed_remote_bases, \
            f'module base must be one of {self._allowed_remote_bases}'
        assert name not in self.module_names, f'Module by name "{name}" already defined in config'
        # ToDo: Sanity checking on remote_url string
        self._module_config[base][name] = {'remote_url': remote_url,
                                           'keyfile': None,
                                           'certfile': None}
        self.sigConfigChanged.emit(self)

    def rename_module(self, old_name, new_name):
        if old_name == new_name:
            return
        self.check_module_name(new_name)
        assert new_name not in self.module_names, \
            f'Module by name "{new_name}" already defined in config'
        cfg_dict = self.get_module_config(old_name)
        for module_cfg in self._module_config.values():
            if old_name in module_cfg:
                del module_cfg[old_name]
                module_cfg[new_name] = cfg_dict
                break

    def set_module_connections(self, name, connections):
        if connections is None:
            connections = dict()
        assert isinstance(connections, dict), 'Connections must be dict type or None'
        assert self.is_local_module(name), \
            'Module connections can only be set for local (non-remote) modules.'
        assert all(isinstance(conn, str) and conn for conn in connections), \
            'Connectors must be non-empty strings'
        assert all(isinstance(target, str) and target for target in connections.values()), \
            'Connector targets must be non-empty strings'

        module_cfg = self.get_module_config(name)
        if connections:
            module_cfg['connect'] = connections.copy()
        else:
            module_cfg.pop('connect', None)
        self.sigConfigChanged.emit(self)

    def set_module_options(self, name, options):
        if options is None:
            options = dict()
        assert isinstance(options, dict), 'Options must be dict type or None'
        assert self.is_local_module(name), \
            'Module options can only be set for local (non-remote) modules.'
        assert all(isinstance(opt, str) and opt for opt in options), \
            'Options must be non-empty strings'
        assert not any(key in options for key in self._forbidden_options), \
            f'Invalid keys encountered in config options for module "{name}".\n' \
            f'Avoid using config options with any name in:\n{self._forbidden_options}.'

        keep_first = ('module.Class', 'allow_remote')
        keep_last = ('connect',)
        for base, cfg_dict in self._module_config.items():
            module_cfg = cfg_dict.get(name, None)
            if module_cfg is not None:
                cfg_dict[name] = {key: val for key, val in module_cfg.items() if key in keep_first}
                cfg_dict[name].update(options)
                cfg_dict[name].update(
                    {key: val for key, val in module_cfg.items() if key in keep_last}
                )
                break
        self.sigConfigChanged.emit(self)

    def set_module_allow_remote(self, name, allow_remote):
        assert isinstance(allow_remote, bool), 'Module allow_remote flag must be bool'
        assert self.is_local_module(name), \
            'Module allow_remote flag can only be set for local (non-remote) modules.'

        module_cfg = self.get_module_config(name)
        module_cfg['allow_remote'] = allow_remote
        self.sigConfigChanged.emit(self)

    def set_module_remote_url(self, name, url):
        assert isinstance(url, str) and url, 'Module remote_url must be non-empty str'
        assert self.is_remote_module(name), \
            'Module remote_url can only be set for remote (non-local) modules.'

        module_cfg = self.get_module_config(name)
        module_cfg['remote_url'] = url
        self.sigConfigChanged.emit(self)

    def set_module_remote_certificate(self, name, keyfile, certfile):
        assert keyfile is None or isinstance(keyfile, str), 'Module keyfile must be str or None'
        assert certfile is None or isinstance(certfile, str), 'Module certfile must be str or None'
        assert self.is_remote_module(name), \
            'Module certificate can only be set for remote (non-local) modules.'

        module_cfg = self.get_module_config(name)
        module_cfg['keyfile'] = keyfile
        module_cfg['certfile'] = certfile
        self.sigConfigChanged.emit(self)

    def remove_module(self, name):
        for cfg_dict in self._module_config.values():
            if cfg_dict.pop(name, None) is not None:
                self.sigConfigChanged.emit(self)
                break

    def get_module_config(self, name):
        self.check_module_name(name)
        for module_cfg in self._module_config.values():
            try:
                return module_cfg[name]
            except KeyError:
                pass
        raise KeyError(f'No module configuration found for module name "{name}"')

    def clear_config(self):
        """ Delete the entire config content and start with an empty clean config.
        The currently set file_path is preserved.
        """
        self._global_config = dict()
        self._module_config = {'hardware': dict(), 'logic': dict(), 'gui': dict()}
        self._unhandled_config = dict()
        self.sigConfigChanged.emit(self)

    def load_config(self, file_path=None, set_default=False):
        if file_path is None:
            file_path = self._file_path
            if file_path is None:
                raise ValueError('Not file path defined for config to load')

        # Load YAML file from disk
        config = load(file_path, ignore_missing=False)

        # prepare a new Configuration instance to fill with loaded data first
        new_config = Configuration()

        # Configure global settings
        global_cfg = config.pop('global', dict())
        new_config.startup_modules = global_cfg.pop('startup', None)
        new_config.extension_paths = global_cfg.pop('extensions', None)
        new_config.stylesheet = global_cfg.pop('stylesheet', None)
        new_config.default_data_dir = global_cfg.pop('default_data_dir', None)
        new_config.namespace_server_port = global_cfg.pop('namespace_server_port', 18861)
        new_config.remote_modules_server = global_cfg.pop('remote_modules_server', None)
        if global_cfg:
            warn(f'Found additional entries in global config. The following entries will be '
                 f'ignored:\n{global_cfg}')

        # Configure modules
        for base in ('hardware', 'logic', 'gui'):
            base_cfg = config.pop(base, dict())
            for name, module_cfg in base_cfg.items():
                is_remote = 'remote_url' in module_cfg
                if is_remote:
                    remote_url = module_cfg.pop('remote_url')
                    keyfile = module_cfg.pop('keyfile', None)
                    certfile = module_cfg.pop('certfile', None)
                    if module_cfg:
                        warn(f'Found additional entries in config for remote module "{name}". The '
                             f'following entries will be ignored:\n{module_cfg}')
                    new_config.add_remote_module(name, base, remote_url)
                    new_config.set_module_remote_certificate(name, keyfile, certfile)
                else:
                    module, cls = module_cfg.pop('module.Class').rsplit('.', 1)
                    allow_remote = module_cfg.pop('allow_remote', None)
                    connections = module_cfg.pop('connect', None)
                    new_config.add_local_module(name, base, module, cls)
                    if allow_remote is not None:
                        new_config.set_module_allow_remote(name, allow_remote)
                    new_config.set_module_options(name, module_cfg)
                    new_config.set_module_connections(name, connections)

        # Configure "unhandled" config parts
        new_config.unhandled_config = config

        # If there are no exceptions raised up until here, assume the config is valid and actually
        # update this instance file path and config data.
        self._global_config = new_config.global_config
        self._module_config = new_config.module_config
        self._unhandled_config = new_config.unhandled_config
        self._file_path = file_path
        # Write current config file path to load.cfg in AppData if requested
        if set_default:
            self.set_default_config_path(file_path)
        self.sigConfigChanged.emit(self)

    def save_config(self, file_path=None):
        if file_path is None:
            file_path = self._file_path
            if file_path is None:
                raise ValueError('Not file path defined for qudi config to save into')
        save(file_path, self.config_dict)
        self._file_path = file_path

    def is_remote_module(self, name):
        module_cfg = self.get_module_config(name)
        return 'remote_url' in module_cfg and 'module.Class' not in module_cfg

    def is_local_module(self, name):
        module_cfg = self.get_module_config(name)
        return 'module.Class' in module_cfg and 'remote_url' not in module_cfg

    def check_module_name(self, name):
        if self._module_name_regex.match(name) is None:
            raise ValueError('qudi module config name must be non-empty str containing only '
                             'unicode word characters and spaces.')

    @staticmethod
    def set_default_config_path(path):
        # Write current config file path to load.cfg
        save(file_path=os.path.join(_paths.get_appdata_dir(create_missing=True), 'load.cfg'),
             data={'load_config_path': path})

    @staticmethod
    def get_saved_config():
        # Try loading config file path from last session
        try:
            load_cfg = load(os.path.join(_paths.get_appdata_dir(), 'load.cfg'), ignore_missing=True)
        except:
            load_cfg = dict()
        file_path = load_cfg.get('load_config_path', '')
        if os.path.isfile(file_path) and file_path.endswith('.cfg'):
            return file_path
        return None

    @staticmethod
    def get_default_config():
        # Try default.cfg in user home directory
        file_path = os.path.join(_paths.get_default_config_dir(), 'default.cfg')
        if os.path.isfile(file_path):
            return file_path

        # Fall back to default.cfg in qudi core directory
        file_path = os.path.join(_paths.get_main_dir(), 'core', 'default.cfg')
        if os.path.isfile(file_path):
            return file_path

        # Raise error if no config file could be found
        raise FileNotFoundError('No config file could be found in default directories.')

    @staticmethod
    def relative_to_absolute_path(path):
        # absolute or relative path? Existing?
        if os.path.isabs(path) and os.path.isdir(path):
            return path

        # relative path? Try relative to userdata dir, user home dir and relative to main dir
        search_dirs = (_paths.get_userdata_dir(),
                       _paths.get_home_dir(),
                       _paths.get_main_dir())
        for search_dir in search_dirs:
            new_path = os.path.abspath(os.path.join(search_dir, path))
            if os.path.isdir(new_path):
                return new_path

        # Raise exception if no existing path can be determined
        raise FileNotFoundError(
            f'Qudi relative path "{path}" can not be resolved or does not exist.'
        )
