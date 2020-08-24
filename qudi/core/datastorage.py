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
import re
import csv
import copy
import numpy as np
import matplotlib.pyplot as plt
from abc import ABCMeta, abstractmethod
from enum import Enum
from datetime import datetime
from matplotlib.backends.backend_pdf import PdfPages
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
    """ Image format to use for saving data thumbnails.
    """
    PNG = '.png'
    PDF = '.pdf'


class DataFormat(Enum):
    """ File format for saving data to disk.
    """
    TEXT = 0
    CSV = 1
    NPY = 2
    XML = 3
    HDF5 = 4


class DataStorageBase(metaclass=ABCMeta):
    """ Base helper class to store (measurement)data on disk in a daily directory.
    Data will always be saved in a tabular format with column headers. With most file formats rows
    are appendable.
    """
    __global_parameters = dict()

    # __int_regex = re.compile(r'\A[+-]?\d+\Z')
    # __float_regex = re.compile(r'\A[+-]?\d+.\d+([eE][+-]?\d+)?\Z')

    def __init__(self, root_dir=None, sub_directory=None, column_headers='', number_format='%.15e',
                 comments='# ', delimiter='\t', data_format=DataFormat.TEXT,
                 image_format=ImageFormat.PNG):
        """
        @param str root_dir: optional, root-directory path for daily directory tree
        @param tuple|str column_headers: optional, iterable of strings containing column headers.
                                         If a single string is given, write it to file header
                                         without formatting.
        @param str sub_directory: optional, sub-directory name to use within daily data directory
        @param str|tuple number_format: optional, number format specifier (mini-language) for text
                                        files. Can be iterable of format specifiers for each column.
        @param str comments: optional, string to put at the beginning of comment and header lines
        @param str delimiter: optional, column delimiter used in text files
        @param DataFormat data_format: optional, data file format Enum
        @param ImageFormat image_format: optional, image file format Enum
        """
        if not isinstance(data_format, DataFormat):
            raise TypeError('data_format must be DataFormat Enum')
        if not isinstance(image_format, ImageFormat):
            raise TypeError('image_format must be ImageFormat Enum')
        if isinstance(column_headers, str):
            self.column_headers = str(column_headers)
        elif any(not isinstance(header, str) for header in column_headers):
            raise TypeError('Data headers must be str type.')
        else:
            self.column_headers = tuple(column_headers)
        if root_dir is None:
            self.root_dir = get_default_data_dir(create_missing=False)
        else:
            self.root_dir = root_dir
        self.sub_directory = sub_directory
        self.number_format = number_format
        self.comments = str(comments) if isinstance(comments, str) else None
        self.delimiter = delimiter
        self.data_format = data_format
        self.image_format = image_format
        return

    def get_daily_data_directory(self, timestamp=None, create_missing=True):
        """ Create and return daily directory to save data in.

        @param datetime.datetime timestamp: optional, Timestamp for which to create daily directory
        @param bool create_missing: optional, indicate if a directory should be created (True) or
                                    not (False)
        """
        daily = get_daily_data_directory(root=self.root_dir,
                                         timestamp=timestamp,
                                         create_missing=create_missing)
        path = daily if self.sub_directory is None else os.path.join(daily, self.sub_directory)
        if not os.path.isdir(path):
            if create_missing:
                os.makedirs(path, exist_ok=True)
            else:
                raise NotADirectoryError('Data directory not found: {0}'.format(path))
        return path

    def create_header(self, parameters, timestamp, include_global_parameters=True,
                      include_column_header=True):
        """
        """
        # Gather all parameters (both global and provided) into a single dict if needed
        if include_global_parameters:
            all_parameters = self.__global_parameters.copy()
            all_parameters.update(parameters)
        else:
            all_parameters = parameters.copy()

        header_lines = list()
        header_lines.append('Saved Data on {0}'.format(timestamp.strftime('%d.%m.%Y at %Hh%Mm%Ss')))
        header_lines.append('')
        header_lines.append('Parameters:')
        header_lines.append('===========')
        for param, value in all_parameters.items():
            if isinstance(value, (float, np.floating)):
                header_lines.append('{0}: {1:.16e}'.format(param, value))
            elif isinstance(value, (int, np.integer)):
                header_lines.append('{0}: {1:d}'.format(param, value))
            else:
                header_lines.append('{0}: {1}'.format(param, value))
        header_lines.append('')
        header_lines.append('Data:')
        header_lines.append('=====')
        if include_column_header:
            if isinstance(self.column_headers, str):
                header_lines.append(self.column_headers)
            else:
                header_lines.append(self.delimiter.join(self.column_headers))
        header_lines.append('')

        line_sep = '\n' if self.comments is None else '\n{0}'.format(self.comments)
        return line_sep.join(header_lines)

    def create_file_path(self, timestamp=None, filename=None, nametag=None, file_extension=None):
        """
        """
        if filename is None:
            if timestamp is None:
                timestamp = datetime.now()
            if nametag is None:
                filename = timestamp.strftime('%Y%m%d-%H%M-%S')
            else:
                filename = '{0}_{1}'.format(timestamp.strftime('%Y%m%d-%H%M-%S'), nametag)
        if file_extension is not None and not filename.endswith(file_extension):
            filename += file_extension if file_extension.startswith('.') else '.{0}'.format(
                file_extension)
        return os.path.join(self.get_daily_data_directory(timestamp=timestamp, create_missing=True),
                            filename)

    @abstractmethod
    def save_data(self, *args, **kwargs):
        pass

    def save_thumbnail(self, mpl_figure, timestamp=None, filename=None, nametag=None):
        # Create file path
        file_path = self.create_file_path(timestamp=timestamp,
                                          filename=filename,
                                          nametag=nametag,
                                          file_extension=self.image_format.value())

        if self.image_format is ImageFormat.PDF:
            # Create the PdfPages object to which we will save the pages:
            with PdfPages(file_path) as pdf:
                pdf.savefig(mpl_figure, bbox_inches='tight', pad_inches=0.05)
        elif self.image_format is ImageFormat.PNG:
            # save the image as PNG
            mpl_figure.savefig(file_path, bbox_inches='tight', pad_inches=0.05)
        else:
            raise Exception('Unknown image format selected: "{0}"'.format(self.image_format))

        # close matplotlib figure and return
        plt.close(mpl_figure)
        return file_path

    @abstractmethod
    def load_data(self, *args, **kwargs):
        """
        @return np.ndarray, dict, tuple: Data as numpy array, extracted parameters, column headers
        """
        pass
        # FIXME: This is not in a satisfying condition yet. Please improve, test and remove error.
        # raise Exception('Loading data is not fully implemented, yet.')
        # parameters = dict()
        # column_header = ''
        # if self.data_format in (DataFormat.TEXT, DataFormat.CSV):
        #     index = 0
        #     in_params = False
        #     in_data = False
        #     with open(file_path, 'r', newline='') as file:
        #         for line in file:
        #             if not line.startswith(self.comments):
        #                 file.seek(index)
        #                 break
        #             if line.endswith('Parameters:\n'):
        #                 in_params = True
        #             elif line.endswith('Data:\n'):
        #                 in_data = True
        #             if in_data and not line[len(self.comments):].startswith('====='):
        #                 column_header += line[len(self.comments):]
        #             elif in_params and ': ' in line:
        #                 clean_param = line[len(self.comments):].strip()
        #                 name, value_str = clean_param.rsplit(': ', 1)
        #                 if self.__int_regex.match(value_str):
        #                     parameters[name] = int(value_str)
        #                 elif self.__float_regex.match(value_str):
        #                     parameters[name] = float(value_str)
        #                 else:
        #                     parameters[name] = str(value_str)
        #         reader = csv.reader(file, delimiter=self.delimiter)
        #         data_array = np.asarray([data for data in reader])
        #         if data_array.ndim > 1:
        #             if data_array.shape[1] == 1:
        #                 data_array = data_array[:, 0]
        #                 headers = (column_header.strip(),) if column_header else tuple()
        #             else:
        #                 headers = tuple(
        #                     it.strip() for it in column_header.split(self.delimiter) if it.strip())
        #                 if len(headers) != data_array.shape[1]:
        #                     headers = (column_header.strip(),) if column_header else tuple()
        # return data_array, parameters, headers

    @classmethod
    def get_global_parameters(cls):
        """ Return a copy of the global parameters dict.
        """
        return cls._global_parameters.copy()

    @classmethod
    def set_global_parameter(cls, name, value, overwrite=False):
        """ Set a single global parameter to save in all data file headers during this qudi session.
        """
        if not isinstance(name, str):
            raise TypeError('global parameter name must be str type.')
        if not overwrite and name in cls.__global_parameters:
            raise KeyError('global parameter "{0}" already set while overwrite flag is False.'
                           ''.format(name))
        cls.__global_parameters[name] = copy.deepcopy(value)
        return

    @classmethod
    def set_global_parameters(cls, params, overwrite=False):
        """ Set multiple global parameters to save in all data file headers during this qudi
        session.
        """
        if any(not isinstance(name, str) for name in params):
            raise TypeError('global parameter name must be str type.')
        if not overwrite and any(name in cls.__global_parameters for name in params):
            raise KeyError('global parameter already set while overwrite flag is False.')
        for name, value in params.items():
            cls.__global_parameters[name] = copy.deepcopy(value)
        return

    @classmethod
    def remove_global_parameter(cls, name):
        """ Remove a global parameter. Does not raise an error.
        """
        cls.__global_parameters.pop(name, None)
        return


# class CsvDataStorage(DataStorageBase):
#     """ Helper class to store (measurement)data on disk in a daily directory as CSV file.
#     """
#     def __init__(self, column_headers, sub_directory=None, number_format='%.15e', comments='# ',
#                  image_format=ImageFormat.PNG):
#         super().__init__(column_headers=column_headers,
#                          sub_directory=sub_directory,
#                          number_format=number_format,
#                          comments=comments,
#                          delimiter=',',
#                          data_format=DataFormat.CSV,
#                          image_format=image_format)
#
#     def save_data(self, data, parameters=None, filename=None, nametag=None, timestamp=None):
#         """
#         """
#         # Create timestamp if missing
#         if timestamp is None:
#             timestamp = datetime.now()
#         # Determine full file path and create containing directories if needed
#         file_path = self.create_file_path(timestamp,
#                                           filename=filename,
#                                           nametag=nametag,
#                                           file_extension='.csv')
#         # Create header but do not include column headers if possible
#         header = self.create_header(parameters=parameters,
#                                     timestamp=timestamp,
#                                     include_column_header=isinstance(self.column_headers, str))
#         # Write out file
#         with open(file_path, 'w') as file:
#             # Write (commented) header
#             file.write(header)
#             # Write column headers if not already included in header string
#             if not isinstance(self.column_headers, str):
#                 file.write(','.join(self.column_headers))
#             # Write numpy data array
#             np.savetxt(file, data, delimiter=self.delimiter, fmt=self.number_format)
#         return file_path, timestamp
#
#     def load_data(self, file_path):
#         pass
#
#
# class TextDataStorage(DataStorageBase):
#     """ Helper class to store (measurement)data on disk in a daily directory as text file.
#     """
#     def __init__(self, column_headers, sub_directory=None, number_format='%.15e', comments='# ',
#                  delimiter='\t', image_format=ImageFormat.PNG):
#         super().__init__(column_headers=column_headers,
#                          sub_directory=sub_directory,
#                          number_format=number_format,
#                          comments=comments,
#                          delimiter=',',
#                          data_format=DataFormat.TEXT,
#                          image_format=image_format)
#
#     def save_data(self, data, parameters=None, filename=None, nametag=None, timestamp=None):
#         """
#         """
#         # Create timestamp if missing
#         if timestamp is None:
#             timestamp = datetime.now()
#         # Determine full file path and create containing directories if needed
#         file_path = self.create_file_path(timestamp,
#                                           filename=filename,
#                                           nametag=nametag,
#                                           file_extension='.dat')
#         # Create header
#         header = self.create_header(parameters=parameters,
#                                     timestamp=timestamp,
#                                     include_column_header=True)
#         # Write out file
#         with open(file_path, 'w') as file:
#             # Write (commented) header
#             file.write(header)
#             # Write numpy data array
#             np.savetxt(file, data, delimiter=self.delimiter, fmt=self.number_format)
#         return file_path, timestamp
#
#     def load_data(self, file_path):
#         pass
#
#
# class NumpyDataStorage(DataStorageBase):
#     """ Helper class to store (measurement)data on disk in a daily directory as binary .npy or
#     compressed .npz file.
#     """
#     def __init__(self, sub_directory=None, image_format=ImageFormat.PNG):
#         super().__init__(sub_directory=sub_directory,
#                          data_format=DataFormat.NPY,
#                          image_format=image_format)
#
#     def save_data(self, data, parameters=None, filename=None, nametag=None, timestamp=None):
#         """
#         """
#         # Create timestamp if missing
#         if timestamp is None:
#             timestamp = datetime.now()
#         # Determine full file path and create containing directories if needed
#         file_path = self.create_file_path(timestamp,
#                                           filename=filename,
#                                           nametag=nametag,
#                                           file_extension='.npy')
#         param_file_path = file_path.rsplit('.npy', 1)[0] + '_parameters.txt'
#         # Create header to save in a separate text file
#         header = self.create_header(parameters=parameters,
#                                     timestamp=timestamp,
#                                     include_column_header=True)
#         with open(param_file_path, 'w') as file:
#             file.write(header)
#
#         # Write out data file
#         with open(file_path, 'wb') as file:
#             # Write numpy data array in binary format
#             np.save(file, data, allow_pickle=False, fix_imports=False)
#         return file_path, timestamp
#
#     def load_data(self, file_path):
#         pass
#
