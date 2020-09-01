# -*- coding: utf-8 -*-
"""
This file contains Qt models for Python data structures.

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

from PySide2 import QtCore
from collections import OrderedDict
from qudi.core.util.mutex import RecursiveMutex

__all__ = ('DictTableModel', 'ListTableModel')


class DictTableModel(QtCore.QAbstractTableModel):
    """ Qt model storing a table in dictionaries
    """
    def __init__(self, headers):
        super().__init__()
        self._lock = RecursiveMutex()
        if isinstance(headers, str):
            self._headers = [headers]
        elif len(headers) > 2:
            raise Exception(
                'DictTableModel can only support up to 2 columns and associated headers.')
        elif not all(isinstance(h, str) for h in headers):
            raise TypeError('DictTableModel header entries must be str type.')
        else:
            self._headers = list(headers)
        self._storage = OrderedDict()

    def rowCount(self, parent=QtCore.QModelIndex()):
        """ Gives the number of stored items.

          @return int: number of items
        """
        with self._lock:
            return len(self._storage)

    def columnCount(self, parent=QtCore.QModelIndex()):
        """ Gives the number of data fields.

          @return int: number of data fields
        """
        with self._lock:
            return len(self._headers)

    def flags(self, index):
        """ Determines what can be done with entry cells in the table view.

        @param QModelIndex index: cell fo which the flags are requested

        @return Qt.ItemFlags: actions allowed for this cell
        """
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self, index, role):
        """ Get data from model for a given cell. Data can have a role that affects display.

        @param QModelIndex index: cell for which data is requested
        @param ItemDataRole role: role for which data is requested

        @return QVariant: data for given cell and role
        """
        with self._lock:
            if not index.isValid():
                return None
            elif role == QtCore.Qt.DisplayRole:
                key = self.get_key_by_index(index.row())
                if index.column() == 0:
                    return key
                elif index.column() == 1:
                    return self._storage[key]
                else:
                    return None
            return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        """ Data for the table view headers.

        @param int section: number of the column to get header data for
        @param Qt.Orientation orientation: orientation of header (horizontal or vertical)
        @param ItemDataRole role: role for which to get data

        @return QVariant: header data for given column and role
        """
        with self._lock:
            if not(0 <= section < len(self._headers)):
                return None
            elif role != QtCore.Qt.DisplayRole:
                return None
            elif orientation != QtCore.Qt.Horizontal:
                return None
            return self._headers[section]

    def get_key_by_index(self, n):
        """ Get a dict key by index number

        @param int n: index number for element

        @return key: key at index
        """
        with self._lock:
            if not(0 <= n < len(self._storage)):
                raise IndexError
            i = 0
            it = iter(self._storage)
            key = next(it)
            while i < n:
                key = next(it)
                i += 1
            return key

    def get_index_by_key(self, key):
        """ Get index number for dict key.

        @param key: dict key

        @return int: index number for key

        Warning: index number for a key changes when keys with lower numbers are removed.
        """
        with self._lock:
            if key not in self._storage or len(self._storage) < 1:
                raise KeyError
            i = 0
            it = iter(self._storage)
            newkey = next(it)
            while key != newkey:
                newkey = next(it)
                i += 1
            return i

    def __setitem__(self, key, value):
        with self._lock:
            if key in self._storage:
                row = self.get_index_by_key(key)
                self._storage[key] = value
                index = self.index(row, 1)
                self.dataChanged.emit(index, index)
            else:
                row = len(self._storage)
                self.beginInsertRows(QtCore.QModelIndex(), row, row)
                self._storage[key] = value
                self.endInsertRows()

    def __getitem__(self, item):
        with self._lock:
            return self._storage.__getitem__(item)

    def __repr__(self):
        with self._lock:
            return repr(self._storage)

    def __len__(self):
        with self._lock:
            return len(self._storage)

    def __delitem__(self, key):
        with self._lock:
            if key not in self._storage:
                raise KeyError
            self.pop(key)

    def __iter__(self):
        with self._lock:
            return self._storage.__iter__()

    def __contains__(self, item):
        with self._lock:
            return self._storage.__contains__(item)

    def clear(self):
        with self._lock:
            self.beginResetModel()
            self._storage.clear()
            self.endResetModel()

    def copy(self):
        model = DictTableModel(self._headers.copy())
        model._storage = self._storage.copy()
        return model

    def update(self, *args, **kwargs):
        with self._lock:
            update_dict = dict(*args, **kwargs)
            for key, value in update_dict.items():
                self.__setitem__(key, value)

    def pop(self, *args):
        """ Remove key from dictionary.

        @param args: dict key to remove, optional default return value

        @return value: value removed from dict
        """
        with self._lock:
            if args[0] in self._storage:
                row = self.get_index_by_key(args[0])
                self.beginRemoveRows(QtCore.QModelIndex(), row, row)
                ret = self._storage.pop(args[0])
                self.endRemoveRows()
                return ret
            elif len(args) > 1:
                return args[1]

    def get(self, *args):
        """ Get value for key from dictionary.

        @param args: value for key, optional default return value

        @return value: value for key from dict
        """
        with self._lock:
            return self._storage.get(*args)

    def values(self):
        with self._lock:
            return self._storage.values()

    def keys(self):
        with self._lock:
            return self._storage.keys()

    def items(self):
        with self._lock:
            return self._storage.items()


class ListTableModel(QtCore.QAbstractTableModel):
    """ Qt model storing a table in lists.
    """

    def __init__(self, header):
        super().__init__()
        self._lock = RecursiveMutex()
        if isinstance(header, str):
            self._header = header
        elif len(header) > 1:
            raise IndexError(
                'ListTableModel can only support a single column with associated header.')
        else:
            self._header = str(header[0])
        self._storage = list()

    def rowCount(self, parent=QtCore.QModelIndex()):
        """ Gives the number of stored items.

        @return int: number of items
        """
        with self._lock:
            return len(self._storage)

    def columnCount(self, parent=QtCore.QModelIndex()):
        """ Gives the number of data fields.

        @return int: number of data fields
        """
        return 1

    def flags(self, index):
        """ Determines what can be done with entry cells in the table view.

        @param QModelIndex index: cell fo which the flags are requested

        @return Qt.ItemFlags: actins allowed fotr this cell
        """
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self, index, role):
        """ Get data from model for a given cell. Data can have a role that affects display.

        @param QModelIndex index: cell for which data is requested
        @param ItemDataRole role: role for which data is requested

        @return QVariant: data for given cell and role
        """
        with self._lock:
            if not index.isValid() or role != QtCore.Qt.DisplayRole:
                return None
            if index.column() == 0:
                return self._storage[index.row()]
            return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        """ Data for the table view headers.

        @param int section: number of the column to get header data for
        @param Qt.Orientation orientation: orientation of header (horizontal or vertical)
        @param ItemDataRole role: role for which to get data

        @return QVariant: header data for given column and role
        """
        if section != 0 or role != QtCore.Qt.DisplayRole or orientation != QtCore.Qt.Horizontal:
            return None
        return self._header

    def __setitem__(self, key, value):
        with self._lock:
            if key < 0:
                key = key + len(self._storage)
            if 0 <= key < len(self._storage):
                self._storage[key] = value
                index = self.index(key, 0)
                self.dataChanged.emit(index, index)
                return
            raise IndexError

    def __getitem__(self, item):
        with self._lock:
            return self._storage.__getitem__(item)

    def __repr__(self):
        with self._lock:
            return repr(self._storage)

    def __len__(self):
        with self._lock:
            return len(self._storage)

    def __delitem__(self, key):
        with self._lock:
            if key < 0:
                key = key + len(self._storage)
            if 0 <= key < len(self._storage):
                self.pop(key)
                return
            raise IndexError

    def __iter__(self):
        with self._lock:
            return self._storage.__iter__()

    def __contains__(self, item):
        with self._lock:
            return item in self._storage

    def insert(self, n, data):
        """ Insert a row into table.

        @param int n: insert before nth element
        @param data: row to insert
        """
        with self._lock:
            if 0 <= n <= len(self._storage):
                self.beginInsertRows(QtCore.QModelIndex(), n, n)
                self._storage.insert(n, data)
                self.endInsertRows()
            else:
                raise IndexError

    def append(self, data):
        """ Append row to table.
            
        @param data: row to append
        """
        with self._lock:
            n = len(self._storage)
            self.beginInsertRows(QtCore.QModelIndex(), n, n)
            self._storage.append(data)
            self.endInsertRows()

    def pop(self, n):
        """ Remove nth row from table.

        @param int n: index of row to remove

        @return data: removed row
        """
        with self._lock:
            if 0 <= n < len(self._storage):
                self.beginRemoveRows(QtCore.QModelIndex(), n, n)
                ret = self.storage.pop(n)
                self.endRemoveRows()
                return ret
            else:
                raise IndexError

    def extend(self, seq):
        with self._lock:
            seq = list(seq)
            n = len(self._storage)
            m = n + len(seq)
            self.beginInsertRows(QtCore.QModelIndex(), n, m)
            self._storage.extend(seq)
            self.endInsertRows()

    def remove(self, value):
        with self._lock:
            row = self._storage.index(value)
            self.pop(row)

    def count(self, value):
        with self._lock:
            return self._storage.count(value)

    def copy(self):
        model = ListTableModel(self._header)
        model._storage = self._storage.copy()
        return model
