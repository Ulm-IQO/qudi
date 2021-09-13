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

__all__ = ['DictTableModel', 'ListTableModel']

from PySide2 import QtCore
from typing import Any, Optional, Union, Sequence
from qudi.util.mutex import RecursiveMutex


class DictTableModel(QtCore.QAbstractTableModel):
    """ Qt model storing a table in dictionaries
    """
    def __init__(self, headers: Union[str, Sequence[str]]):
        super().__init__()
        self._lock = RecursiveMutex()
        if isinstance(headers, str):
            self._headers = [headers]
        elif not all(isinstance(h, str) for h in headers):
            raise TypeError('DictTableModel header entries must be str type.')
        else:
            self._headers = list(headers)
        self._storage = dict()

    def rowCount(self, parent: Optional[QtCore.QModelIndex] = None) -> int:
        """ Returns the number of stored items (rows)
        """
        with self._lock:
            return len(self._storage)

    def columnCount(self, parent: Optional[QtCore.QModelIndex] = None) -> int:
        """ Returns the number of data fields (columns)
        """
        with self._lock:
            return len(self._headers)

    def flags(self, index: Optional[QtCore.QModelIndex] = None) -> QtCore.Qt.ItemFlags:
        """ Determines what can be done with the given indexed cell.
        """
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self, index: QtCore.QModelIndex, role: QtCore.Qt.ItemDataRole) -> Any:
        """ Get data from model for a given cell. Data can have a role that affects display.
        Re-Implement in subclass in order to support anything else than the 2 default columns.
        """
        with self._lock:
            if index.isValid() and role == QtCore.Qt.DisplayRole:
                key = self.get_key_by_index(index.row())
                if index.column() == 0:
                    return key
                elif index.column() == 1:
                    return self._storage[key]
            return None

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation,
                   role: Optional[QtCore.Qt.ItemDataRole] = QtCore.Qt.DisplayRole) -> Any:
        """ Data for the table view headers """
        with self._lock:
            if role == QtCore.Qt.DisplayRole:
                if orientation == QtCore.Qt.Horizontal:
                    return self._headers[section]
            return None

    def get_key_by_index(self, n: int) -> Any:
        """ Get a dict key by index number """
        with self._lock:
            it = iter(self._storage)
            key = None
            try:
                for i in range(n):
                    key = next(it)
            except StopIteration:
                pass
            if key is None:
                raise IndexError
            return key

    def get_index_by_key(self, key: Any) -> int:
        """ Get row index for dict key.

        Warning: Row index for a key changes when keys with lower index are removed.
        """
        with self._lock:
            for i, storage_key in enumerate(self._storage.keys()):
                if key == storage_key:
                    return i
            raise KeyError

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

    def __init__(self, headers: Union[str, Sequence[str]]):
        super().__init__()
        self._lock = RecursiveMutex()
        if isinstance(headers, str):
            self._headers = headers
        elif not all(isinstance(h, str) for h in headers):
            raise TypeError('DictTableModel header entries must be str type.')
        else:
            self._headers = list(headers)
        self._storage = list()

    def rowCount(self, parent: Optional[QtCore.QModelIndex] = None):
        """ Gives the number of stored items (rows)
        """
        with self._lock:
            return len(self._storage)

    def columnCount(self, parent: Optional[QtCore.QModelIndex] = None):
        """ Gives the number of data fields (columns)
        """
        return len(self._headers)

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        """ Determines what can be done with entry cells in the table view.
        """
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self, index: QtCore.QModelIndex, role: QtCore.Qt.ItemDataRole) -> Any:
        """ Get data from model for a given cell. Data can have a role that affects display.
        """
        with self._lock:
            if index.isValid() and role == QtCore.Qt.DisplayRole:
                return self._storage[index.row()]
            return None

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation,
                   role: Optional[QtCore.Qt.ItemDataRole] = QtCore.Qt.DisplayRole) -> Any:
        """ Data for the table view headers
        """
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self._headers[section]
        return None

    def __setitem__(self, key, value):
        with self._lock:
            if key < 0:
                key = key + len(self._storage)
            self._storage[key] = value
            self.dataChanged.emit(self.index(key, 0), self.index(key, len(self._headers) - 1))

    def __getitem__(self, key):
        with self._lock:
            return self._storage[key]

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
            self.pop(key)

    def __iter__(self):
        with self._lock:
            return iter(self._storage)

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
                ret = self._storage.pop(n)
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
        model = ListTableModel(self._headers)
        model._storage = self._storage.copy()
        return model
