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

__all__ = ('get_timestamp_filename', 'format_column_headers', 'format_header', 'CsvDataStorage',
           'DataStorageBase', 'ImageFormat', 'NpyDataStorage', 'TextDataStorage')

import os
import re
import copy
import numpy as np
import matplotlib.pyplot as plt

from enum import Enum
from datetime import datetime
from abc import ABCMeta, abstractmethod
from matplotlib.backends.backend_pdf import PdfPages

from qudi.util.mutex import Mutex


class ImageFormat(Enum):
    """ Image format to use for saving data thumbnails.
    """
    PNG = '.png'
    PDF = '.pdf'


def get_timestamp_filename(timestamp, nametag=None):
    """ Returns a qudi standard filename used for saving measurement data to file.
    Not including any file extension.

    @param datetime.datetime timestamp: Timestamp used to create the filename from
    @param str nametag: optional, additional string to include in the file name

    @return str: Generated file name without file extension
    """
    # Start of the filename contains the timestamp, i.e. "20210130-1130-59"
    datetime_str = timestamp.strftime('%Y%m%d-%H%M-%S')
    if nametag:
        nametag = nametag.strip()
        # Replace unicode whitespaces with underscores.
        # Consecutive whitespaces are replaced by single underscore.
        nametag = re.sub(r'[\s]+', '_', nametag)
        # ToDo: More character sequence checking needed. Raise exception if bad.
    # Separate nametag and timestamp string with an underscore
    return f'{datetime_str}_{nametag}' if nametag else datetime_str


def format_column_headers(column_headers, delimiter='\t'):
    if not column_headers:
        return None
    if isinstance(column_headers, str):
        return column_headers
    if any(not isinstance(header, str) for header in column_headers):
        raise TypeError('column_headers must be iterable of str.')
    return delimiter.join(column_headers)


def format_header(timestamp=None, metadata=None, notes=None, column_header_str=None, comments=None):
    """
    """
    # Gather all lines in a list of strings (NOT including line separation chars)
    header_lines = list()
    if timestamp is not None:
        header_lines.append(timestamp.strftime('Saved Data on %d.%m.%Y at %Hh%Mm%Ss'))
        header_lines.append('')

    if notes:
        header_lines.extend(notes.splitlines())
        header_lines.append('')

    if metadata:
        header_lines.append('Metadata:')
        header_lines.append('=========')
        for param, value in metadata.items():
            if isinstance(value, (float, np.floating)):
                header_lines.append(f'{param}: {value:.18e}')
            elif isinstance(value, (int, np.integer)):
                header_lines.append(f'{param}: {value:d}')
            else:
                header_lines.append(f'{param}: {value}')
        header_lines.append('')

    header_lines.append('Data:')
    header_lines.append('=====')

    if column_header_str:
        header_lines.append(column_header_str)

    line_sep = '\n' if comments is None else f'\n{comments}'
    return f'{line_sep[1:]}{line_sep.join(header_lines)}'


def create_dir_for_file(file_path):
    """ Helper method to create the directory (recursively) for a given file path.
    Will NOT raise an error if the directory already exists.

    @param str file_path: File path to create the directory for
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)


class DataStorageBase(metaclass=ABCMeta):
    """ Base helper class to store/load (measurement)data to/from disk.
    Subclasses handle saving and loading of measurement data (including metadata) for specific file
    formats.
    Metadata is represented as dictionary (key-value pairs).
    It is also possible to set so called "global metadata" using this or any subclass of this class.
    Global metadata is shared and accessible throughout all instances of these storage objects
    within the Python process.

    If the storage type is file based and root_dir is not initialized, each call to save_data must
    provide the full save path information and not just a file name or name tag.
    """
    _global_metadata = dict()
    _global_metadata_lock = Mutex()

    def __init__(self, *, root_dir=None, include_global_metadata=True,
                 image_format=ImageFormat.PNG):
        """
        @param str root_dir: optional, root-directory for this storage instance to work in
        @param bool include_global_metadata: optional, flag indicating saving of global metadata
        @param ImageFormat image_format: optional, image file format Enum for saving thumbnails
        """
        if not isinstance(image_format, ImageFormat):
            raise TypeError('image_format must be ImageFormat Enum')

        self.root_dir = root_dir  # ToDo: Maybe some sanity checking for correct path syntax?
        self.include_global_metadata = bool(include_global_metadata)
        self.image_format = image_format

    def save_thumbnail(self, mpl_figure, file_path):
        """ Save a matplotlib figure visualizing the saved data in the image format configured.
        It is recommended to use the same file_path as the corresponding data file (if applicable)
        and exclude the file extension (will be added according to image format).

        @param matplotlib.figure.Figure mpl_figure: The matplotlib figure object to save as image
        @param str file_path: full file path to use without file extension

        @return str: Full absolute path of the saved image
        """
        file_path += self.image_format.value

        if self.image_format is ImageFormat.PDF:
            with PdfPages(file_path) as pdf:
                pdf.savefig(mpl_figure, bbox_inches='tight', pad_inches=0.05)
        elif self.image_format is ImageFormat.PNG:
            mpl_figure.savefig(file_path, bbox_inches='tight', pad_inches=0.05)
        else:
            raise RuntimeError(f'Unknown image format selected: "{self.image_format}"')

        # close matplotlib figure and return
        plt.close(mpl_figure)
        return file_path

    def get_unified_metadata(self, local_metadata=None):
        """ Helper method to return a dict containing provided local_metadata as well as global
        metadata depending on include_global_metadata flag.

        @param dict local_metadata: Metadata to include in addition to global metadata

        @return dict: New dict containing local_metadata and global metadata
        """
        metadata = self.get_global_metadata() if self.include_global_metadata else dict()
        if local_metadata is not None:
            metadata.update(local_metadata)
        return metadata

    @abstractmethod
    def save_data(self, data, *, metadata=None, notes=None, nametag=None, timestamp=None):
        """ This method must be implemented in a subclass. It should provide the facility to save an
        entire measurement as a whole along with experiment metadata (to include e.g. in the file
        header). The user can either specify an explicit filename or a generic one will be created.
        If optional nametag and/or timestamp is provided, this will be used to create the generic
        filename (only if filename parameter is omitted).

        @param numpy.ndarray data: data array to be saved (must be 1D or 2D for text files)
        @param str notes: optional, string that is included in the metadata "as-is" without a key
        @param dict metadata: optional, named metadata to be saved in the data header / metadata
        @param str nametag: optional, nametag to include in the generic filename
        @param datetime.datetime timestamp: optional, timestamp to construct a generic filename from

        @return (str, datetime.datetime, tuple): Full file path, timestamp used, saved data shape
        """
        pass

    @abstractmethod
    def load_data(self, *args, **kwargs):
        """ This method must be implemented in a subclass. It should provide the facility to load a
        saved data set including the metadata/experiment parameters and column headers
        (if possible).

        @return np.ndarray, dict, tuple, str: Data as numpy array, extracted metadata,
                                              column headers, notes
        """
        pass

    @classmethod
    def get_global_metadata(cls):
        """ Return a copy of the global metadata dict.
        """
        with cls._global_metadata_lock:
            return cls._global_metadata.copy()

    @classmethod
    def add_global_metadata(cls, name, value=None, *, overwrite=False):
        """ Set a single global metadata key-value pair or alternatively multiple ones as dict.
        Metadata added this way will persist for all data storage instances in this process until
        being selectively removed by calls to "remove_global_metadata".
        """
        if isinstance(name, str):
            metadata = {name: copy.deepcopy(value)}
        elif isinstance(name, dict):
            if any(not isinstance(key, str) for key in name):
                TypeError('Metadata dict must contain only str type keys.')
            metadata = copy.deepcopy(name)
        else:
            raise TypeError('add_global_metadata expects either a single dict as first argument or '
                            'a str key and a value as first two arguments.')

        with cls._global_metadata_lock:
            if not overwrite:
                duplicate_keys = set(metadata).intersection(cls._global_metadata)
                if duplicate_keys:
                    raise KeyError(f'global metadata keys "{duplicate_keys}" already set while '
                                   f'overwrite flag is False.')
            cls._global_metadata.update(metadata)

    @classmethod
    def remove_global_metadata(cls, names):
        """ Remove a global metadata key-value pair by key. Does not raise an error if the key is
        not found.
        """
        if isinstance(names, str):
            names = [names]
        with cls._global_metadata_lock:
            for name in names:
                cls._global_metadata.pop(name, None)


class TextDataStorage(DataStorageBase):
    """ Helper class to store (measurement)data on disk as text file.
    Data will always be saved in a tabular format with column headers. Single/Multiple rows are
    appendable.
    """

    # Regular expressions to automatically determine number format
    # __int_regex = re.compile(r'\A[+-]?\d+\Z')
    # __float_regex = re.compile(r'\A[+-]?\d+.\d+([eE][+-]?\d+)?\Z')

    def __init__(self, *, root_dir, number_format='%.18e', comments='# ', delimiter='\t',
                 file_extension='.dat', **kwargs):
        """
        @param tuple|str column_headers: optional, iterable of strings containing column headers.
                                         If a single string is given, write it to file header
                                         without formatting.
        @param str|tuple number_format: optional, number format specifier (mini-language) for text
                                        files. Can be iterable of format specifiers for each column.
        @param str comments: optional, string to put at the beginning of comment and header lines
        @param str delimiter: optional, column delimiter used in text files
        @param kwargs: optional, for additional keyword arguments see DataStorageBase.__init__
        """
        super().__init__(root_dir=root_dir, **kwargs)

        if not delimiter or not isinstance(delimiter, str):
            raise ValueError('Parameter "delimiter" must be non-empty string.')

        self._file_extension = ''
        self.file_extension = file_extension
        self.number_format = number_format
        self.comments = comments if isinstance(comments, str) else None
        self.delimiter = delimiter

    @property
    def file_extension(self):
        return self._file_extension

    @file_extension.setter
    def file_extension(self, value):
        if (value is not None) and (not isinstance(value, str)):
            raise TypeError('file_extension must be str or None')
        if not value:
            self._file_extension = ''
        elif value.startswith('.'):
            self._file_extension = value
        else:
            self._file_extension = '.' + value

    def create_header(self, timestamp, metadata=None, notes=None, column_headers=None):
        """
        """
        # Gather all metadata (both global and locally provided) into a single dict
        metadata = self.get_unified_metadata(metadata)
        # Format column headers into a single string
        column_header_str = format_column_headers(column_headers, self.delimiter)
        return format_header(timestamp=timestamp,
                             metadata=metadata,
                             notes=notes,
                             column_header_str=column_header_str,
                             comments=self.comments)

    def new_file(self, *, metadata=None, notes=None, nametag=None, timestamp=None,
                 column_headers=None, filename=None):
        """ Create a new data file on disk and write header string to it. Will overwrite old files
        silently if they have the same path.

        @param dict metadata: optional, named metadata values to be saved in the data header
        @param str notes: optional, string that is included in the file header "as-is"
        @param str nametag: optional, nametag to include in the generic filename
        @param datetime.datetime timestamp: optional, timestamp to construct a generic filename from
        @param str filename: optional, filename to use (nametag, timestamp and
                             configured file_extension will not be included)
        @param str|list column_headers: optional, data column header strings or single string

        @return (str, datetime.datetime): Full file path, timestamp used
        """
        # Create timestamp if missing
        if timestamp is None:
            timestamp = datetime.now()
        # Construct file name if none is given explicitly
        if filename is None:
            filename = get_timestamp_filename(timestamp=timestamp,
                                              nametag=nametag) + self.file_extension
        # Create header
        header = self.create_header(timestamp=timestamp,
                                    metadata=metadata,
                                    notes=notes,
                                    column_headers=column_headers)
        # Determine full file path and create containing directories if needed
        file_path = os.path.join(self.root_dir, filename)
        create_dir_for_file(file_path)
        # Write to file. Overwrite silently.
        with open(file_path, 'w') as file:
            file.write(header + '\n')
        return file_path, timestamp

    def append_file(self, data, file_path):
        """ Append single or multiple rows to an existing data file.

        @param numpy.ndarray data: data array to be appended (1D: single row, 2D: multiple rows)
        @param str file_path: file path to append to

        @return (int, int): Number of rows written, Number of columns written
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(
                'File to append data to not found. '
                'Create a new file to append to by calling "new_file".'
            )
        # Append data to file
        with open(file_path, 'a') as file:
            # Write numpy data array
            if data.ndim == 1:
                np.savetxt(file,
                           np.expand_dims(data, axis=0),
                           delimiter=self.delimiter,
                           fmt=self.number_format)
            else:
                np.savetxt(file, data, delimiter=self.delimiter, fmt=self.number_format)
        return (1, data.shape[0]) if data.ndim == 1 else data.shape

    def save_data(self, data, *, metadata=None, notes=None, nametag=None, timestamp=None,
                  column_headers=None, filename=None):
        """ See: DataStorageBase.save_data() for more information

        @param str|list column_headers: optional, data column header strings or single string
        """
        # Create new data file (overwrite old one if it exists)
        file_path, timestamp = self.new_file(metadata=metadata,
                                             notes=notes,
                                             nametag=nametag,
                                             timestamp=timestamp,
                                             column_headers=column_headers,
                                             filename=filename)
        # Append data to file
        rows_columns = self.append_file(data, file_path=file_path)
        return file_path, timestamp, rows_columns

    def load_data(self, file_path):
        """ See: DataStorageBase.load_data()

        @param str file_path: optional, path to file to load data from
        """
        raise NotImplementedError
        # FIXME: This is not in a satisfying condition yet. Please improve, test and remove error.
        # metadata = dict()
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
        #             if line.endswith('Metadata:\n'):
        #                 in_params = True
        #             elif line.endswith('Data:\n'):
        #                 in_data = True
        #             if in_data and not line[len(self.comments):].startswith('====='):
        #                 column_header += line[len(self.comments):]
        #             elif in_params and ': ' in line:
        #                 clean_param = line[len(self.comments):].strip()
        #                 name, value_str = clean_param.rsplit(': ', 1)
        #                 if self.__int_regex.match(value_str):
        #                     metadata[name] = int(value_str)
        #                 elif self.__float_regex.match(value_str):
        #                     metadata[name] = float(value_str)
        #                 else:
        #                     metadata[name] = str(value_str)
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
        # return data_array, metadata, headers


class CsvDataStorage(TextDataStorage):
    """ Helper class to store (measurement)data on disk as CSV file.
    This is a specialized sub-class of TextDataStorage that uses hard-coded commas as delimiter and
    includes column headers uncommented in the first row of data. This is the standard format for
    importing a table into e.g. MS Excel.
    """
    def __init__(self, *, file_extension='.csv', **kwargs):
        """ See: qudi.util.datastorage.TextDataStorage
        """
        super().__init__(file_extension=file_extension, **kwargs)

    @property
    def delimiter(self):
        return ','

    def create_header(self, timestamp, metadata=None, notes=None, column_headers=None):
        """ Include column_headers without line comment specifier.
        for more information see: qudi.util.datastorage.TextDataStorage.create_header()
        """
        # Create default header as specified in parent TextDataStorage object without column headers
        header = super().create_header(timestamp=timestamp,
                                       metadata=metadata,
                                       notes=notes,
                                       column_headers=None)
        # Append column headers if needed
        column_headers = format_column_headers(column_headers, self.delimiter)
        if column_headers is not None:
            header += f'\n{column_headers}'
        return header

    def load_data(self, file_path):
        """ See: DataStorageBase.load_data()

        @param str file_path: optional, path to file to load data from
        """
        raise NotImplementedError


class NpyDataStorage(DataStorageBase):
    """ Helper class to store (measurement)data on disk as binary .npy file.
    """
    def __init__(self, *, root_dir, **kwargs):
        super().__init__(root_dir=root_dir, **kwargs)

    @property
    def file_extension(self):
        return '.npy'

    def create_header(self, timestamp, metadata=None, notes=None, column_headers=None):
        """
        """
        # Gather all metadata (both global and locally provided) into a single dict
        metadata = self.get_unified_metadata(metadata)
        # Format column headers into a single string
        column_header_str = format_column_headers(column_headers, ';;')
        return format_header(timestamp=timestamp,
                             metadata=metadata,
                             notes=notes,
                             column_header_str=column_header_str,
                             comments=None)

    def save_data(self, data, *, metadata=None, notes=None, nametag=None, timestamp=None,
                  column_headers=None, filename=None):
        """ Saves a binary file containing the data array.
        Also saves alongside a text file containing the notes, (global) metadata and column headers
        for this data set. The filename of the text file will be the same as for the binary file
        appended by "_metadata".

        For more information see: qudi.util.datastorage.DataStorageBase.save_data

        @param str|list column_headers: optional, data column header strings or single string
        """
        if timestamp is None:
            timestamp = datetime.now()
        # Construct file name if none is given explicitly
        if filename is None:
            filename = get_timestamp_filename(timestamp=timestamp,
                                              nametag=nametag) + self.file_extension
        # Create filename for separate metadata textfile
        param_filename = filename.rsplit('.', 1)[0] + '_metadata.txt'

        # Create header
        header = self.create_header(timestamp=timestamp,
                                    metadata=metadata,
                                    notes=notes,
                                    column_headers=column_headers)
        # Determine full file path and create containing directories if needed
        file_path = os.path.join(self.root_dir, filename)
        create_dir_for_file(file_path)
        param_file_path = os.path.join(self.root_dir, param_filename)
        # Write data and metadata to file. Overwrite silently.
        with open(file_path, 'wb') as file:
            # Write numpy data array in binary format
            np.save(file, data, allow_pickle=False, fix_imports=False)
        with open(param_file_path, 'w') as file:
            file.write(header + '\n')
        return file_path, timestamp, data.shape

    def load_data(self, file_path):
        """ See: DataStorageBase.load_data()

        @param str file_path: optional, path to file to load data from
        """
        raise NotImplementedError
