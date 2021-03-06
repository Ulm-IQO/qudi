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

import numpy
import os
import copy
import ruamel.yaml as yaml
from io import BytesIO
from warnings import warn
from collections import OrderedDict
from PySide2 import QtCore

import qudi.core.paths as qudi_paths


def qudi_load(stream, loader_base=yaml.Loader):
    """ Loads a YAML formatted data from stream and puts it into a dict

    @param Stream stream: stream the data is read from
    @param yaml.Loader loader_base: YAML Loader base class

    @return dict: Dict containing data. If stream is empty then an empty dict is returned
    """
    class QudiLoader(loader_base):
        """ Custom loader.
        """
        pass

    def construct_ndarray(loader, node):
        """
        The ndarray constructor, correctly saves a numpy array inside the config file as a string.
        """
        value = loader.construct_yaml_binary(node)
        with BytesIO(bytes(value)) as f:
            arrays = numpy.load(f)
            return arrays['array']

    def construct_external_ndarray(loader, node):
        """
        The constructor for an numpy array that is saved in an external file.
        """
        filename = loader.construct_yaml_str(node)
        arrays = numpy.load(filename)
        return arrays['array']

    def construct_frozenset(loader, node):
        """
        The frozenset constructor.
        """
        data = tuple(loader.construct_yaml_set(node))
        return frozenset(data[0]) if data else frozenset()

    def construct_str(loader, node):
        """
        construct strings but if the string starts with 'array(' it tries
        to evaluate it as numpy array.

        TODO: This behaviour should be deprecated at some point.
        """
        value = loader.construct_yaml_str(node)
        # if a string could be an array, we try to evaluate the string
        # to reconstruct a numpy array. If it fails we return the string.
        if value.startswith('array('):
            try:
                local = {"array": numpy.array}
                for dtype in ['int8', 'uint8', 'int16', 'uint16', 'float16', 'int32', 'uint32',
                              'float32', 'int64', 'uint64', 'float64']:
                    local[dtype] = getattr(numpy, dtype)
                return eval(value, local)
            except SyntaxError:
                return value
        else:
            return value

    # add constructors
    QudiLoader.add_constructor('!ndarray', construct_ndarray)
    QudiLoader.add_constructor('!extndarray', construct_external_ndarray)
    QudiLoader.add_constructor('!frozenset', construct_frozenset)
    QudiLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_SCALAR_TAG, construct_str)

    # load config file
    config = yaml.load(stream, QudiLoader)
    # yaml returns None if the config file was empty
    return dict() if config is None else config


def qudi_dump(data, stream=None, dumper_base=yaml.Dumper, **kwargs):
    """ Dumps dict data into a YAML format stream

    @param dict data: the data to dump
    @param Stream stream: stream to dump the data into (in YAML)
    @param yaml.Dumper dumper_base: The dumper that is used as a base class
    """
    class QudiDumper(dumper_base):
        """ Custom dumper
        """
        external_ndarray_counter = 0

        def ignore_aliases(self, ignore_data):
            """
            ignore aliases and anchors
            """
            return True

    def represent_int(dumper, data):
        """
        Representer for numpy int dtypes
        """
        return dumper.represent_int(numpy.asscalar(data))

    def represent_float(dumper, data):
        """
        Representer for numpy float dtypes
        """
        return dumper.represent_float(numpy.asscalar(data))

    def represent_frozenset(dumper, data):
        """
        Representer for frozenset
        """
        node = dumper.represent_set(set(data))
        node.tag = '!frozenset'
        return node

    def represent_ndarray(dumper, data):
        """
        Representer for numpy ndarrays
        """
        try:
            filename = os.path.splitext(os.path.basename(stream.name))[0]
            configdir = os.path.dirname(stream.name)
            newpath = '{0}-{1:06}.npz'.format(os.path.join(configdir, filename),
                                              dumper.external_ndarray_counter)
            numpy.savez_compressed(newpath, array=data)
            node = dumper.represent_str(newpath)
            node.tag = '!extndarray'
            dumper.external_ndarray_counter += 1
        except:
            with BytesIO() as f:
                numpy.savez_compressed(f, array=data)
                compressed_string = f.getvalue()
            node = dumper.represent_binary(compressed_string)
            node.tag = '!ndarray'
        return node

    # add representers
    QudiDumper.add_representer(numpy.uint8, represent_int)
    QudiDumper.add_representer(numpy.uint16, represent_int)
    QudiDumper.add_representer(numpy.uint32, represent_int)
    QudiDumper.add_representer(numpy.uint64, represent_int)
    QudiDumper.add_representer(numpy.int8, represent_int)
    QudiDumper.add_representer(numpy.int16, represent_int)
    QudiDumper.add_representer(numpy.int32, represent_int)
    QudiDumper.add_representer(numpy.int64, represent_int)
    QudiDumper.add_representer(numpy.float16, represent_float)
    QudiDumper.add_representer(numpy.float32, represent_float)
    QudiDumper.add_representer(numpy.float64, represent_float)
    # QudiDumper.add_representer(numpy.float128, represent_float)
    QudiDumper.add_representer(numpy.ndarray, represent_ndarray)
    QudiDumper.add_representer(frozenset, represent_frozenset)
    # Treat OrderedDict as native dict
    QudiDumper.add_representer(OrderedDict, yaml.Representer.represent_dict)

    # dump data
    return yaml.dump(data, stream, QudiDumper, **kwargs)


def load(file_path, ignore_missing=False):
    """
    Loads a config file. Throws a FileNotFoundError if the file does not exist

    @param str file_path: path to config file
    @param bool ignore_missing: Optional flag to suppress FileNotFoundError

    @return dict: The data as python/numpy objects in a dict
    """
    if os.path.isfile(file_path):
        with open(file_path, 'r') as f:
            return qudi_load(f, yaml.SafeLoader)
    elif ignore_missing:
        return dict()
    raise FileNotFoundError('Could not load config file "{0}". File not found'.format(file_path))


def save(file_path, data):
    """
    Saves data to file_path in yaml format. Creates subdirectories if not already present.

    @param str file_path: path to config file to save
    @param dict data: config values
    """
    file_dir = os.path.dirname(file_path)
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    with open(file_path, 'w') as f:
        qudi_dump(data, stream=f, dumper_base=yaml.SafeDumper, default_flow_style=False)


class Configuration(QtCore.QObject):
    """
    """

    sigConfigChanged = QtCore.Signal(object)

    def __init__(self, *args, file_path=None, **kwargs):
        super().__init__(*args, **kwargs)

        # determine and check path for config file if given
        if file_path is None:
            self._file_path = None
        elif file_path.endswith('.cfg'):
            self._file_path = file_path
        else:
            warn('Config file path given is invalid.')
            self._file_path = None

        # extracted fields from config file
        self._global_config = dict()
        self._module_config = {'hardware': dict(), 'logic': dict(), 'gui': dict()}
        self._unknown_config = dict()

    @property
    def config_file(self):
        return self._file_path

    @property
    def global_config(self):
        return copy.deepcopy(self._global_config)

    @property
    def module_config(self):
        return copy.deepcopy(self._module_config)

    @property
    def unknown_config(self):
        return copy.deepcopy(self._unknown_config)

    @property
    def config_dict(self):
        conf_dict = dict()
        if self._global_config:
            conf_dict['global'] = self.global_config
        conf_dict.update(self.module_config)
        return conf_dict

    @property
    def startup_modules(self):
        return self._global_config.get('startup', list()).copy()

    @startup_modules.setter
    def startup_modules(self, modules):
        if not modules:
            self._global_config.pop('startup', None)
            return

        if isinstance(modules, str):
            modules = [modules]

        assert all(isinstance(mod, str) for mod in modules), 'Startup modules must be strings'
        self._global_config['startup'] = list(modules)

    @property
    def module_server(self):
        if 'module_server' not in self._global_config:
            return None
        return copy.deepcopy(self._global_config['module_server'])

    @module_server.setter
    def module_server(self, server_settings):
        # ToDo: Sanity checks
        if not server_settings:
            self._global_config.pop('module_server', None)
            return
        self._global_config['module_server'] = copy.deepcopy(server_settings)

    @property
    def stylesheet(self):
        return self._global_config.get('stylesheet', None)

    @stylesheet.setter
    def stylesheet(self, stylesheet_file):
        # FIXME: How should stylesheets be declared in config?
        if not stylesheet_file:
            self._global_config.pop('stylesheet', None)
            return
        self._global_config['stylesheet'] = stylesheet_file

    @property
    def default_data_dir(self):
        return self._global_config.get('default_data_dir', None)

    @default_data_dir.setter
    def default_data_dir(self, path):
        if not path:
            self._global_config.pop('default_data_dir', None)
            return

        # Convert relative path into absolute path and raise exception if non-existent
        self._global_config['default_data_dir'] = self.relative_to_absolute_path(path)

    @property
    def extension_paths(self):
        return self._global_config.get('extensions', list()).copy()

    @extension_paths.setter
    def extension_paths(self, paths):
        if not paths:
            self._global_config.pop('extensions', None)
            return

        if isinstance(paths, str):
            paths = [paths]

        # Convert all relative paths into absolute paths and raise exception if non-existent
        abs_paths = [self.relative_to_absolute_path(p) for p in paths]
        self._global_config['extensions'] = abs_paths

    def set_local_module(self, name, base, module_class, connect=None, options=None, remoteaccess=True):
        assert isinstance(name, str) and name, 'name must be non-empty str'
        assert base in ('hardware', 'logic', 'gui'), \
            'base must be one of "hardware", "logic" or "gui"'
        assert isinstance(module_class, str) and module_class, 'module_class must be non-empty str'
        assert connect is None or isinstance(connect, dict), 'connect must be dict type or None'
        assert options is None or isinstance(options, dict), 'options must be dict type or None'
        assert isinstance(remoteaccess, bool), 'remoteaccess must be bool'
        assert not self._module_in_other_base(name, base), \
            f'Module by name "{name}" already present different module base config'

        module_dict = {'module.Class': module_class, 'remoteaccess': remoteaccess}
        if options:
            invalid_options = {'module.Class', 'connect', 'remoteaccess'}
            assert not any(key in invalid_options for key in options), \
                f'Invalid module options to set. Avoid using {invalid_options}.'
            module_dict.update(options)
        if connect:
            module_dict['connect'] = connect

        # Attach module_dict to config
        self._module_config[base][name] = module_dict

    def set_remote_module(self, name, base, remote_url, keyfile=None, certfile=None):
        assert isinstance(name, str) and name, 'name must be non-empty str'
        assert base in ('hardware', 'logic', 'gui'), \
            'base must be one of "hardware", "logic" or "gui"'
        assert isinstance(remote_url, str) and remote_url, 'remote_url must be non-empty str'
        assert keyfile is None or isinstance(keyfile, str), 'keyfile must be str or None'
        assert certfile is None or isinstance(certfile, dict), 'certfile must be dict type or None'
        assert not self._module_in_other_base(name, base), \
            f'Module by name "{name}" already present different module base config'

        module_dict = {'remote_url': remote_url}
        if keyfile:
            module_dict['keyfile'] = keyfile
        if certfile:
            module_dict['certfile'] = certfile

        # Attach module_dict to config
        self._module_config[base][name] = module_dict

    def remove_module(self, name):
        assert isinstance(name, str), 'name must be str type'
        for base in ('hardware', 'logic', 'gui'):
            self._module_config[base].pop(name, None)

    def get_module_config(self, name):
        assert isinstance(name, str) and name, 'name must be non-empty str'
        for base in ('hardware', 'logic', 'gui'):
            try:
                return self._module_config[base][name]
            except KeyError:
                pass
        raise KeyError(f'No module configuration found for module name "{name}"')

    def load_config(self, file_path=None, set_default=False):
        if file_path is None:
            file_path = self._file_path
            if file_path is None:
                raise ValueError('Not file path defined for config to load')

        config = load(file_path)
        self._global_config = config.pop('global', dict())
        self._module_config = dict()
        for base in ('hardware', 'logic', 'gui'):
            self._module_config[base] = config.pop(base, dict())
            # Remove empty module config entries
            for mod_name in tuple(self._module_config[base]):
                if not self._module_config[base][mod_name]:
                    del self._module_config[base][mod_name]
        if config:
            warn('Unknown config file section(s) encountered:\n{0}'.format(config))
            self._unknown_config = config
        else:
            self._unknown_config = dict()

        # Clean up global config
        for key in tuple(self._global_config):
            if not self._global_config[key] and not isinstance(self._global_config[key], bool):
                del self._global_config[key]
                continue
            if key == 'startup':
                if isinstance(self._global_config[key], str):
                    self._global_config[key] = [self._global_config[key]]
            elif key == 'stylesheet':
                # FIXME: How should stylesheets be declared in config?
                self._global_config[key] = os.path.join(qudi_paths.get_artwork_dir(),
                                                        'styles',
                                                        'application',
                                                        self._global_config[key])
                if not os.path.isfile(self._global_config[key]):
                    warn('Stylesheet file not found in specified path: {0}'
                         ''.format(self._global_config[key]))
                    del self._global_config[key]
            elif key == 'extensions':
                if isinstance(self._global_config[key], str):
                    self._global_config[key] = [self._global_config[key]]

                # Convert all relative paths into absolute paths and ignore if path is non-existent
                abs_paths = list()
                for path in self._global_config[key]:
                    try:
                        abs_paths.append(self.relative_to_absolute_path(path))
                    except FileNotFoundError as err:
                        warn(str(err) + ' Extension path ignored.')
                if abs_paths:
                    self._global_config[key] = abs_paths
                else:
                    del self._global_config[key]
            elif key == 'default_data_dir':
                # Convert relative path into absolute path and ignore if path is non-existent
                path = self._global_config[key]
                try:
                    self._global_config[key] = self.relative_to_absolute_path(path)
                except FileNotFoundError as err:
                    del self._global_config[key]
                    warn(str(err) + ' Default data directory path ignored.')

        self._file_path = file_path
        if set_default:
            self.set_default_config_path(file_path)  # Write current config file path to load.cfg
        self.sigConfigChanged.emit(self)

    def save_config(self, file_path=None):
        if file_path is None:
            file_path = self._file_path
            if file_path is None:
                raise ValueError('Not file path defined for config to save into')

        save(file_path, self.config_dict)
        self._file_path = file_path

    def _module_in_other_base(self, name, exclude_base):
        """ Checks if a module by the name <name> is already present in another base than
        <exclude_base>.
        """
        assert isinstance(name, str), 'name must be str type'
        assert exclude_base in ('hardware', 'logic', 'gui'), \
            'exclude_base must be one of "hardware", "logic" or "gui"'
        check_bases = {'hardware', 'logic', 'gui'}
        check_bases.discard(exclude_base)
        return any(name in self.module_config[base] for base in check_bases)

    @staticmethod
    def set_default_config_path(path):
        # Write current config file path to load.cfg
        save(file_path=os.path.join(qudi_paths.get_appdata_dir(create_missing=True), 'load.cfg'),
             data={'load_config_path': path})

    @staticmethod
    def get_saved_config():
        # Try loading config file path from last session
        try:
            load_cfg = load(os.path.join(qudi_paths.get_appdata_dir(), 'load.cfg'),
                            ignore_missing=True)
        except:
            load_cfg = dict()
        file_path = load_cfg.get('load_config_path', '')
        if os.path.isfile(file_path) and file_path.endswith('.cfg'):
            return file_path
        return None

    @staticmethod
    def get_default_config():
        # Try default.cfg in user home directory
        file_path = os.path.join(qudi_paths.get_default_config_dir(), 'default.cfg')
        if os.path.isfile(file_path):
            return file_path

        # Fall back to default.cfg in qudi core directory
        file_path = os.path.join(qudi_paths.get_main_dir(), 'core', 'default.cfg')
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
        search_dirs = (qudi_paths.get_userdata_dir(),
                       qudi_paths.get_home_dir(),
                       qudi_paths.get_main_dir())
        for search_dir in search_dirs:
            new_path = os.path.abspath(os.path.join(search_dir, path))
            if os.path.isdir(new_path):
                return new_path

        # Raise exception if no existing path can be determined
        raise FileNotFoundError(
            f'Qudi relative path "{path}" can not be resolved or does not exist.'
        )
