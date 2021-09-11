# -*- coding: utf-8 -*-
"""
This file extends the ruamel.yaml package functionality to load and dump more data types needed by
qudi (mostly numpy array and number types).
Provides easy to use yaml_load and yaml_dump functions to read and write qudi YAML files.

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

__all__ = ('SafeRepresenter', 'SafeConstructor', 'YAML', 'yaml_load', 'yaml_dump')

import os
import numpy as np
import ruamel.yaml as _yaml
from collections import OrderedDict
from io import BytesIO, TextIOWrapper
from typing import Optional, Any, Mapping, Dict
from qudi.util.parameters import FilePath


class SafeRepresenter(_yaml.SafeRepresenter):
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
SafeRepresenter.add_representer(frozenset, SafeRepresenter.represent_frozenset)
SafeRepresenter.add_representer(complex, SafeRepresenter.represent_complex)
SafeRepresenter.add_representer(dict, SafeRepresenter.represent_dict_no_sort)
SafeRepresenter.add_representer(OrderedDict, SafeRepresenter.represent_dict_no_sort)
SafeRepresenter.add_representer(np.ndarray, SafeRepresenter.represent_ndarray)
SafeRepresenter.add_multi_representer(np.integer, SafeRepresenter.represent_numpy_int)
SafeRepresenter.add_multi_representer(np.floating, SafeRepresenter.represent_numpy_float)
SafeRepresenter.add_multi_representer(np.complexfloating, SafeRepresenter.represent_numpy_complex)


class SafeConstructor(_yaml.SafeConstructor):
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
SafeConstructor.add_constructor('tag:yaml.org,2002:frozenset', SafeConstructor.construct_frozenset)
SafeConstructor.add_constructor('tag:yaml.org,2002:complex', SafeConstructor.construct_complex)
SafeConstructor.add_constructor('tag:yaml.org,2002:ndarray', SafeConstructor.construct_ndarray)
SafeConstructor.add_constructor('tag:yaml.org,2002:extndarray',
                                SafeConstructor.construct_extndarray)


class YAML(_yaml.YAML):
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
        self.Representer = SafeRepresenter
        self.Constructor = SafeConstructor


def yaml_load(file_path: FilePath, ignore_missing: Optional[bool] = False) -> Dict[str, Any]:
    """ Loads a qudi style YAML file.
    Raises OSError if the file does not exist or can not be accessed.

    @param str file_path: path to config file
    @param bool ignore_missing: optional, flag to suppress FileNotFoundError

    @return dict: The data as python/numpy objects in a dict
    """
    try:
        with open(file_path, 'r') as f:
            data = YAML().load(f)
            # yaml returns None if the stream was empty
            return dict() if data is None else data
    except OSError:
        if ignore_missing:
            return dict()
        else:
            raise


def yaml_dump(file_path: FilePath, data: Mapping[str, Any]) -> None:
    """ Saves data to file_path in qudi style YAML format. Creates subdirectories if needed.

    @param str file_path: path to YAML file to save data into
    @param dict data: Dict containing the data to save to file
    """
    file_dir = os.path.dirname(file_path)
    if file_dir:
        os.makedirs(file_dir, exist_ok=True)
    with open(file_path, 'w') as f:
        YAML().dump(data, f)
