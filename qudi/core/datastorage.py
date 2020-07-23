# -*- coding: utf-8 -*-

"""
This file contains data storage utilities for Qudi.

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
import csv
import copy
import numpy as np
from enum import Enum
from datetime import datetime
from qudi.core.util.paths import get_userdata_dir
from qudi.core.application import Qudi


def get_default_data_dir(create_missing=False):
    """ Returns the qudi default data root directory. Will first try to interface with the running
    qudi instance and extract the desired root directory from the loaded config. If this fails, fall
    back to the default qudi userdata directory (usually user home dir).

    @property:
    """
    qudi = Qudi.instance()
    if qudi is None:
        path = os.path.join(get_userdata_dir(create_missing=create_missing), 'Data')
    else:
        path = qudi.configuration.default_data_dir
        if path is None:
            path = os.path.join(get_userdata_dir(create_missing=create_missing), 'Data')
    if create_missing and not os.path.exists(path):
        os.makedirs(path)
    return path


def get_daily_data_directory(root=None, timestamp=None, create_missing=True):
    """ Returns a path to a directory for storing data from today.

    The directory structure will have the form: <root>/<YYYY>/<MM>/<YYYYMMDD>/

    If not root directory is given, this method will first try to interface with a running qudi
    instance and extract the desired root directory from the loaded config. If this fails, it will
    fall back to the default qudi userdata directory (usually user home dir).

    @param str root: optional, explicit root path for daily directory structure
    @param datetime.datetime timestamp: optional, Timestamp for which to create daily directory
    @param bool create_missing: optional, indicate if a directory should be created (True) or not
                                (False)
    """
    # Determine root directory
    if root is None:
        root = get_default_data_dir(create_missing=create_missing)

    # Create timestamp if omitted
    if not isinstance(timestamp, datetime):
        timestamp = datetime.now()

    # Determine daily directory path
    leaf_dir = '{0:d}{1:d}{2:d}'.format(timestamp.year, timestamp.month, timestamp.day)
    daily_dir = os.path.join(root, str(timestamp.year), str(timestamp.month), leaf_dir)

    # Create directory if necessary
    if not os.path.exists(daily_dir):
        if create_missing:
            os.makedirs(daily_dir, exist_ok=True)
        else:
            raise NotADirectoryError('Daily directory not found.')
    return daily_dir


class ImageFormat(Enum):
    PNG = 0
    PDF = 1


class DataFormat(Enum):
    TEXT = 0
    NPY = 1
    NPZ = 2
    XML = 3
    HDF5 = 4


class DataStorageBase:
    """ Base helper class to store (measurement)data on disk in a daily directory.
    Data will always be saved in a tabular format with column headers. With most file formats rows
    are appendable.
    """
    __global_parameters = dict()

    def __init__(self, data_headers=None, sub_directory=None, number_format='%.15e', delimiter='\t',
                 data_format=DataFormat.TEXT, image_format=ImageFormat.PNG):
        """
        @param tuple data_headers: optional, iterable of strings containing column headers
        @param str sub_directory: optional, sub-directory name to use within daily data directory
        @param str number_format: optional, number format specifier (mini-language) for text files
        @param str delimiter: optional, column delimiter used in text files
        @param DataFormat data_format: optional, data file format Enum
        @param ImageFormat image_format: optional, image file format Enum
        """
        if any(not isinstance(header, str) for header in data_headers):
            raise TypeError('Data headers must be str type.')
        if not isinstance(data_format, DataFormat):
            raise TypeError('data_format must be DataFormat Enum')
        if not isinstance(image_format, ImageFormat):
            raise TypeError('image_format must be ImageFormat Enum')
        self.data_headers = tuple(data_headers)
        self.sub_directory = sub_directory
        self.number_format = number_format
        self.delimiter = delimiter
        self.data_format = data_format
        self.image_format = image_format
        return

    def get_data_directory(self, timestamp=None, create_missing=True):
        """ Create and return daily directory to save data in.

        @param datetime.datetime timestamp: optional, Timestamp for which to create daily directory
        @param bool create_missing: optional, indicate if a directory should be created (True) or
                                    not (False)
        """
        daily = get_daily_data_directory(timestamp=timestamp, create_missing=create_missing)
        if self.sub_directory is None:
            path = daily
        else:
            path = os.path.join(daily, self.sub_directory)
        if not os.path.exists(path):
            if create_missing:
                os.makedirs(path, exist_ok=True)
            else:
                raise NotADirectoryError('Data directory not found: {0}'.format(path))
        return path

    def save_data(self, *args, **kwargs):
        raise Exception('save_data not implemented! Do not use DataStorageBase class directly.')

    @classmethod
    def get_global_parameters(cls):
        """ Return a copy of the global parameters dict.
        """
        return cls._global_parameters.copy()

    @classmethod
    def set_global_parameter(cls, name, value, overwrite=False):
        """ Set a single global parameter to save in all data file headers during this qudi session.
        Parameter value is typecast into str.
        """
        if not isinstance(name, str):
            raise TypeError('global parameter name must be str type.')
        if not overwrite and name in cls.__global_parameters:
            raise KeyError('global parameter "{0}" already set while overwrite flag is False.'
                           ''.format(name))
        cls.__global_parameters[name] = str(value)
        return

    @classmethod
    def set_global_parameters(cls, params, overwrite=False):
        """ Set multiple global parameters to save in all data file headers during this qudi
        session.
        Parameter value is typecast into str.
        """
        if any(not isinstance(name, str) for name in params):
            raise TypeError('global parameter name must be str type.')
        if not overwrite and any(name in cls.__global_parameters for name in params):
            raise KeyError('global parameter already set while overwrite flag is False.')
        cls.__global_parameters.update({name: str(value) for name, value in params.items()})
        return

    @classmethod
    def remove_global_parameter(cls, name):
        """ Remove a global parameter. Does not raise an error.
        """
        cls.__global_parameters.pop(name, None)
        return


class CsvDataStorage(DataStorageBase):
    """ Helper class to store (measurement)data on disk in a daily directory as CSV file.
    """
    def __init__(self, data_headers, sub_directory=None, number_format='%.15e',
                 image_format=ImageFormat.PNG):
        super().__init__(data_headers=data_headers,
                         sub_directory=sub_directory,
                         number_format=number_format,
                         delimiter=',',
                         data_format=DataFormat.TEXT,
                         image_format=image_format)

    def save_data(self, data, parameters=None, filename=None, nametag=None, timestamp=None):
        pass
