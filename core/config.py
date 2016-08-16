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



QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from collections import OrderedDict
import numpy
import re
import ruamel.yaml as yaml
from io import BytesIO

def ordered_load(stream, Loader=yaml.Loader):
    """
    Loads a YAML formatted data from stream and puts it into an OrderedDict

    @param stream Stream: stream the data is read from
    @param Loader Loader: Loader base class

    Returns OrderedDict with data. If stream is empty then an empty
    OrderedDict is returned.
    """
    class OrderedLoader(Loader):
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
        The ndarray constructor.
        """
        value = loader.construct_yaml_binary(node)
        with BytesIO(bytes(value)) as f:
            arrays = numpy.load(f)
            return arrays['array']

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
                for dtype in ['int8', 'uint8', 'int16', 'uint16', 'float16',
                        'int32', 'uint32', 'float32', 'int64', 'uint64',
                        'float64']:
                    local[dtype] = getattr(numpy, dtype)
                return eval(value, local)
            except SyntaxError:
                return value
        else:
            return value

    # add constructor
    OrderedLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            construct_mapping)
    OrderedLoader.add_constructor(
            '!ndarray',
            construct_ndarray)
    OrderedLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_SCALAR_TAG,
            construct_str)

    # load config file
    config = yaml.load(stream, OrderedLoader)
    # yaml returns None if the config file was empty
    if config is not None:
        return config
    else:
        return OrderedDict()


def ordered_dump(data, stream=None, Dumper=yaml.Dumper, **kwds):
    """
    dumps (OrderedDict) data in YAML format

    @param data OrderedDict: the data
    @param stream Stream: where the data in YAML is dumped
    @param Dumper Dumper: The dumper that is used as a base class
    """
    class OrderedDumper(Dumper):
        """
        A Dumper using an OrderedDict
        """
        def ignore_aliases(self, data):
            """
            ignore aliases and anchors
            """
            return True

    def represent_ordereddict(dumper, data):
        """
        Representer for OrderedDict
        """
        return dumper.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
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

    def represent_ndarray(dumper, data):
        """
        Representer for numpy ndarrays
        """
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
    OrderedDumper.add_representer(numpy.float128, represent_float)
    OrderedDumper.add_representer(numpy.ndarray, represent_ndarray)

    # dump data
    return yaml.dump(data, stream, OrderedDumper, **kwds)


def load(filename):
    """
    Loads a config file

    @param filename str: filename of config file

    Returns OrderedDict
    """
    with open(filename, 'r') as f:
        return ordered_load(f, yaml.SafeLoader)

def save(filename, data):
    """
    saves data to filename in yaml format.

    @param filename str: filename of config file
    @param data OrderedDict: config values
    """
    with open(filename, 'w') as f:
        ordered_dump(data, stream=f, Dumper=yaml.SafeDumper,
                default_flow_style=False)
