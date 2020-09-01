# -*- coding: utf-8 -*-

"""
This file contains the Qudi configuration file module.

A configuration file is saved in YAML format. This module provides a loader
and a dumper using an OrderedDict instead of the regular dict used by PyYAML.
Additionally, it fixes a bug in PyYAML with scientific notation and allows
to dump numpy dtypes and numpy ndarrays.

The fix of the scientific notation is applied globally at module import.

The idea of the implementation of the OrderedDict was taken from
http://stackoverflow.com/questions/5121931/in-python-how-can-you-load-yaml-mappings-as-ordereddicts


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

from collections import OrderedDict
import numpy
import os
import copy
import ruamel.yaml as yaml
from io import BytesIO
from PySide2 import QtCore
from qudi.core.util.paths import get_main_dir, get_default_config_dir, get_appdata_dir, get_home_dir
from qudi.core.util.paths import get_artwork_dir
from warnings import warn


def ordered_load(stream, loader_base=yaml.Loader):
    """
    Loads a YAML formatted data from stream and puts it into an OrderedDict

    @param Stream stream: stream the data is read from
    @param yaml.Loader loader_base: YAML Loader base class

    @return OrderedDict: Dict containing data. If stream is empty then an empty dict is returned
    """
    class OrderedLoader(loader_base):
        """
        Loader using an OrderedDict
        """
        pass

    def construct_mapping(loader, node):
        """
        The OrderedDict constructor.
        """
        loader.flatten_mapping(node)
        return OrderedDict(loader.construct_pairs(node))

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
    OrderedLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
    OrderedLoader.add_constructor('!ndarray', construct_ndarray)
    OrderedLoader.add_constructor('!extndarray', construct_external_ndarray)
    OrderedLoader.add_constructor('!frozenset', construct_frozenset)
    OrderedLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_SCALAR_TAG, construct_str)

    # load config file
    config = yaml.load(stream, OrderedLoader)
    # yaml returns None if the config file was empty
    return OrderedDict() if config is None else config


def ordered_dump(data, stream=None, dumper_base=yaml.Dumper, **kwargs):
    """
    Dumps OrderedDict data into a YAML format stream

    @param OrderedDict data: the data to dump
    @param Stream stream: stream to dump the data into (in YAML)
    @param yaml.Dumper dumper_base: The dumper that is used as a base class
    """
    class OrderedDumper(dumper_base):
        """
        A Dumper using an OrderedDict
        """
        external_ndarray_counter = 0

        def ignore_aliases(self, ignore_data):
            """
            ignore aliases and anchors
            """
            return True

    def represent_ordereddict(dumper, data):
        """
        Representer for OrderedDict
        """
        return dumper.represent_mapping(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                                        data.items())

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
    OrderedDumper.add_representer(OrderedDict, represent_ordereddict)
    OrderedDumper.add_representer(numpy.uint8, represent_int)
    OrderedDumper.add_representer(numpy.uint16, represent_int)
    OrderedDumper.add_representer(numpy.uint32, represent_int)
    OrderedDumper.add_representer(numpy.uint64, represent_int)
    OrderedDumper.add_representer(numpy.int8, represent_int)
    OrderedDumper.add_representer(numpy.int16, represent_int)
    OrderedDumper.add_representer(numpy.int32, represent_int)
    OrderedDumper.add_representer(numpy.int64, represent_int)
    OrderedDumper.add_representer(numpy.float16, represent_float)
    OrderedDumper.add_representer(numpy.float32, represent_float)
    OrderedDumper.add_representer(numpy.float64, represent_float)
    # OrderedDumper.add_representer(numpy.float128, represent_float)
    OrderedDumper.add_representer(numpy.ndarray, represent_ndarray)
    OrderedDumper.add_representer(frozenset, represent_frozenset)

    # dump data
    return yaml.dump(data, stream, OrderedDumper, **kwargs)


def load(file_path, ignore_missing=False):
    """
    Loads a config file. Throws a FileNotFoundError if the file does not exist

    @param str file_path: path to config file
    @param bool ignore_missing: Optional flag to suppress FileNotFoundError

    @return OrderedDict: The data as python/numpy objects in an OrderedDict
    """
    if os.path.isfile(file_path):
        with open(file_path, 'r') as f:
            return ordered_load(f, yaml.SafeLoader)
    elif ignore_missing:
        return OrderedDict()
    raise FileNotFoundError('Could not load config file "{0}". File not found'.format(file_path))


def save(file_path, data):
    """
    Saves data to file_path in yaml format. Creates subdirectories if not already present.

    @param str file_path: path to config file to save
    @param OrderedDict data: config values
    """
    file_dir = os.path.dirname(file_path)
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    with open(file_path, 'w') as f:
        ordered_dump(data, stream=f, dumper_base=yaml.SafeDumper, default_flow_style=False)


class Configuration(QtCore.QObject):
    """
    """

    sigConfigChanged = QtCore.Signal(object)

    def __init__(self, file_path=None):
        super().__init__()
        # determine and check path for config file
        if file_path is None:
            self._file_path = self.get_saved_config()
        else:
            if os.path.isfile(file_path) and file_path.endswith('.cfg'):
                self._file_path = file_path
            else:
                self._file_path = None
        # Fall back to default config if no valid config file could be found
        if self._file_path is None:
            self._file_path = self.get_default_config()
            warn('No valid config file path given. Using default config file path: {0}'
                 ''.format(self._file_path))

        # extracted fields from config file
        self._global_config = dict()
        self._module_config = {'hardware': dict(), 'logic': dict(), 'gui': dict()}
        self.unknown_config = dict()

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
    def config_dict(self):
        conf_dict = dict()
        if self._global_config:
            conf_dict['global'] = self.global_config
        conf_dict.update(self.module_config)
        return conf_dict

    @property
    def startup_modules(self):
        return self._global_config.get('startup', list()).copy()

    @property
    def module_server(self):
        if 'module_server' not in self._global_config:
            return None
        return copy.deepcopy(self._global_config['module_server'])

    @property
    def stylesheet(self):
        return self._global_config.get('stylesheet', None)

    @property
    def default_data_dir(self):
        return self._global_config.get('default_data_dir', None)

    @property
    def extension_paths(self):
        return self._global_config.get('extensions', list()).copy()

    def load_config(self, file_path=None, set_default=True):
        if file_path is None:
            file_path = self._file_path
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
            self.unknown_config = config
        else:
            self.unknown_config = dict()

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
                self._global_config[key] = os.path.join(get_artwork_dir(),
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
                    # absolute or relative path? Existing?
                    if os.path.isabs(path) and os.path.isdir(path):
                        abs_paths.append(path)
                    else:
                        # relative path? Try relative to user home dir and relative to main dir
                        new_path = os.path.abspath(os.path.join(get_home_dir(), path))
                        if not os.path.isdir(new_path):
                            new_path = os.path.abspath(os.path.join(get_main_dir(), path))
                            if not os.path.isdir(new_path):
                                warn('Qudi extension path "{0}" does not exist.'.format(path))
                                continue
                        abs_paths.append(new_path)
                if abs_paths:
                    self._global_config[key] = abs_paths
                else:
                    del self._global_config[key]

        self._file_path = file_path
        if set_default:
            self.set_default_config_path(file_path)  # Write current config file path to load.cfg
        self.sigConfigChanged.emit(self)

    def save_config(self, file_path):
        save(file_path, self.config_dict)

    @staticmethod
    def set_default_config_path(path):
        # Write current config file path to load.cfg
        save(file_path=os.path.join(get_appdata_dir(create_missing=True), 'load.cfg'),
             data={'load_config_path': path})

    @staticmethod
    def get_saved_config():
        # Try loading config file path from last session
        try:
            load_cfg = load(os.path.join(get_appdata_dir(), 'load.cfg'), ignore_missing=True)
        except:
            load_cfg = dict()
        file_path = load_cfg.get('load_config_path', '')
        if os.path.isfile(file_path) and file_path.endswith('.cfg'):
            return file_path
        return None

    @staticmethod
    def get_default_config():
        # Try default.cfg in user home directory
        file_path = os.path.join(get_default_config_dir(), 'default.cfg')
        if os.path.isfile(file_path):
            return file_path

        # Fall back to default.cfg in qudi core directory
        file_path = os.path.join(get_main_dir(), 'core', 'default.cfg')
        if os.path.isfile(file_path):
            return file_path

        # Raise error if no config file could be found
        raise FileNotFoundError('No config file could be found in default directories.')
