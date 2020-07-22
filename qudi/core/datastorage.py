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

import os
import csv
import copy
import numpy as np
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


class DataStorageBase:
    """ Base helper class to store (measurement)data on disk in a daily directory.
    """
    def __init__(self, sub_directory=None):
        """
        @param str sub_directory: optional, Sub-directory name to use within daily data directory
        """
        self.sub_directory = sub_directory

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


class CsvDataStorage(DataStorageBase):
    pass
