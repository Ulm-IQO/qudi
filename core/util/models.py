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

from qtpy import QtCore
from collections import OrderedDict
from .mutex import Mutex


class DictTableModel(QtCore.QAbstractTableModel):
    """ Qt model storing a table in dictionaries
    """

    def __init__(self):
        super().__init__()
        self.lock = Mutex()
        self.headers = ['Name']
        self.storage = OrderedDict()

    def getKeyByNumber(self, n):
        """ Get a dict key by index number

            @param int n: index number for element

            @return key: key at index
        """
        i = 0
        if not(0 <= n < len(self.storage)):
            raise IndexError
        it = iter(self.storage)
        key = next(it)
        while i < n:
            key = next(it)
            i += 1
        return key

    def getNumberByKey(self, key):
        """ Get index number for dict key.

            @param key: dict key

            @return int: index numer for key

            Warning: index number for a key changes when keys with lower numbers are removed.
        """
        i = 0
        it = iter(self.storage)
        newkey = next(it)
        while key != newkey:
            newkey = next(it)
            i += 1
        return i

    def rowCount(self, parent=QtCore.QModelIndex()):
        """ Gives the number of stored items.

          @return int: number of items
        """
        return len(self.storage)

    def columnCount(self, parent=QtCore.QModelIndex()):
        """ Gives the number of data fields.

          @return int: number of data fields
        """
        return len(self.headers)

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
        if not index.isValid():
            return None
        elif role == QtCore.Qt.DisplayRole:
            key = self.getKeyByNumber(index.row())
            if index.column() == 0:
                return key
            elif index.column() == 1:
                return self.storage[key]
            else:
                return None
        else:
            return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        """ Data for the table view headers.

          @param int section: number of the column to get header data for
          @param Qt.Orientation orientation: orientation of header (horizontal or vertical)
          @param ItemDataRole role: role for which to get data

          @return QVariant: header data for given column and role
        """
        if not(0 <= section < len(self.headers)):
            return None
        elif role != QtCore.Qt.DisplayRole:
            return None
        elif orientation != QtCore.Qt.Horizontal:
            return None
        else:
            return self.headers[section]

    def add(self, key, data):
        """ Append key and data to dictionary, update model.

            @param key: dict key
            @param data: dict data

            @return key: dict key
        """
        with self.lock:
            if key in self.storage:
                return None
            row = len(self.storage)
            self.beginInsertRows(QtCore.QModelIndex(), row, row)
            self.storage[key] = data
            self.endInsertRows()
            return key

    def pop(self, key):
        """ Remove key from dictionary.

            @param key: dict key to remove

            @return value: value removed from dict
        """
        with self.lock:
            if key in self.storage:
                row = self.getNumberByKey(key)
                self.beginRemoveRows(QtCore.QModelIndex(), row, row)
                ret = self.storage.pop(key)
                self.endRemoveRows()
                return ret


class ListTableModel(QtCore.QAbstractTableModel):
    """ Qt model storing a table in lists.
    """

    def __init__(self):
        super().__init__()
        self.lock = Mutex()
        self.headers = ['Name']
        self.storage = list()

    def rowCount(self, parent=QtCore.QModelIndex()):
        """ Gives the number of stored items.

          @return int: number of items
        """
        return len(self.storage)

    def columnCount(self, parent=QtCore.QModelIndex()):
        """ Gives the number of data fields.

          @return int: number of data fields
        """
        return len(self.headers)

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
        if not index.isValid():
            return None
        elif role == QtCore.Qt.DisplayRole:
            if index.column() == 0:
                return self.storage[index.row()]
            # elif index.column() == 1:
            #     return item[1].thread
            else:
                return None
        else:
            return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        """ Data for the table view headers.

          @param int section: number of the column to get header data for
          @param Qt.Orientation orientation: orientation of header (horizontal or vertical)
          @param ItemDataRole role: role for which to get data

          @return QVariant: header data for given column and role
        """
        if not(0 <= section < len(self.headers)):
            return None
        elif role != QtCore.Qt.DisplayRole:
            return None
        elif orientation != QtCore.Qt.Horizontal:
            return None
        else:
            return self.headers[section]

    def insert(self, n, data):
        """ Insert a row into table.

            @param int n: insert before nth element
            @param data: row to insert
        """
        with self.lock:
            if 0 <= n <= len(self.storage):
                self.beginInsertRows(QtCore.QModelIndex(), n, n)
                self.storage.insert(n, data)
                self.endInsertRows()

    def append(self, data):
        """ Append row to table.
            
            @param data: row to append
        """
        with self.lock:
            n = len(self.storage)
            self.beginInsertRows(QtCore.QModelIndex(), n, n)
            self.storage.append(data)
            self.endInsertRows()

    def pop(self, n):
        """ Remove nth row from table.

            @param int n: index of row to remove

            @return data: removed row
        """
        with self.lock:
            if 0 <= n < len(self.storage):
                self.beginRemoveRows(QtCore.QModelIndex(), n, n)
                ret = self.storage.pop(n)
                self.endRemoveRows()
                return ret
