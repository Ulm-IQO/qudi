# -*- coding: utf-8 -*-
"""
This file contains Qt models for Python data structures.

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

Copyright (C) 2015 Jan M. Binder jan.binder@uni-ulm.de
"""

from pyqtgraph.Qt import QtCore
from collections import OrderedDict
from .mutex import Mutex

class DictTableModel(QtCore.QAbstractTableModel):

    def __init__(self):
        super().__init__()
        self.lock = Mutex()
        self.headers = ['Name']
        self.storage = OrderedDict()

    def getKeyByNumber(self, n):
        i = 0
        length = len(self.storage)
        if n < 0 or n >= length:
            raise IndexError
        it = iter(self.storage)
        key = next(it)
        while(i<n):
            key = next(it)
            i += 1
        return key

    def getNumberByKey(self, key):
        i = 0
        it = iter(self.storage)
        newkey = next(it)
        while(key != newkey):
            newkey = next(it)
            i += 1
        return i

    def rowCount(self, parent = QtCore.QModelIndex()):
        """ Gives the number of stored items.

          @return int: number of items
        """
        return len(self.storage)

    def columnCount(self, parent = QtCore.QModelIndex()):
        """ Gives the number of data fields.

          @return int: number of data fields
        """
        return len(self.headers)

    def flags(self, index):
        """ Determines what can be done with entry cells in the table view.

          @param QModelIndex index: cell fo which the flags are requested

          @return Qt.ItemFlags: actins allowed fotr this cell
        """
        return QtCore.Qt.ItemIsEnabled |  QtCore.Qt.ItemIsSelectable

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

    def headerData(self, section, orientation, role = QtCore.Qt.DisplayRole):
        """ Data for the table view headers.
        
          @param int section: number of the column to get header data for
          @param Qt.Orientation: orientation of header (horizontal or vertical)
          @param ItemDataRole: role for which to get data

          @return QVariant: header data for given column and role
        """
        if section < 0 and section > len(self.headers):
            return None
        elif role != QtCore.Qt.DisplayRole:
            return None
        elif orientation != QtCore.Qt.Horizontal:
            return None
        else:
            return self.headers[section]

    def add(self, key, data):
        with self.lock:
            if key in self.storage:
                return None
            row = len(self.storage)
            self.beginInsertRows(QtCore.QModelIndex(), row, row)
            self.storage[key] = data
            self.endInsertRows()
            return key

    def pop(self, key):
        with self.lock:
            if key in self.storage:
                row = self.getNumberByKey(key)
                self.beginRemoveRows(QtCore.QModelIndex(), row, row)
                ret = self.storage.pop(key)
                self.endRemoveRows()
                return ret


class ListTableModel(QtCore.QAbstractTableModel):

    def __init__(self):
        super().__init__()
        self.lock = Mutex()
        self.headers = ['Name']
        self.storage = list()

    def rowCount(self, parent = QtCore.QModelIndex()):
        """ Gives the number of stored items.

          @return int: number of items
        """
        return len(self.storage)

    def columnCount(self, parent = QtCore.QModelIndex()):
        """ Gives the number of data fields.

          @return int: number of data fields
        """
        return len(self.headers)

    def flags(self, index):
        """ Determines what can be done with entry cells in the table view.

          @param QModelIndex index: cell fo which the flags are requested

          @return Qt.ItemFlags: actins allowed fotr this cell
        """
        return QtCore.Qt.ItemIsEnabled |  QtCore.Qt.ItemIsSelectable

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
            #elif index.column() == 1:
            #    return item[1].thread
            else:
                return None
        else:
            return None

    def headerData(self, section, orientation, role = QtCore.Qt.DisplayRole):
        """ Data for the table view headers.

          @param int section: number of the column to get header data for
          @param Qt.Orientation: orientation of header (horizontal or vertical)
          @param ItemDataRole: role for which to get data

          @return QVariant: header data for given column and role
        """
        if section < 0 and section > len(self.headers):
            return None
        elif role != QtCore.Qt.DisplayRole:
            return None
        elif orientation != QtCore.Qt.Horizontal:
            return None
        else:
            return self.headers[section]

    def insert(self, n, data):
        with self.lock:
            if n >= 0 and n <= len(self.storage):
                self.beginInsertRows(QtCore.QModelIndex(), n, n)
                self.storage.insert(n, data)
                self.endInsertRows()

    def append(self, data):
        with self.lock:
            n = len(self.storage)
            self.beginInsertRows(QtCore.QModelIndex(), n, n)
            self.storage.append(data)
            self.endInsertRows()

    def pop(self, n):
        with self.lock:
            if n >= 0 and n < len(self.storage):
                self.beginRemoveRows(QtCore.QModelIndex(), n, n)
                ret = self.storage.pop(n)
                self.endRemoveRows()
                return ret

