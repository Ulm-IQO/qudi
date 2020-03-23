# -*- coding: utf-8 -*-
"""
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

class ModuleConfigModel(QtCore.QAbstractTableModel):

    def __init__(self, module):
        super().__init__()
        self.headers = ['Option', 'Value']
        self.storage = module.options

    def getKeyByNumber(self, n):
        """ Get a dict key by index number

            @param n int: index number for element

            @return key: key at index
        """
        i = 0
        if not(0 <= n < len(self.storage)):
            raise IndexError
        it = iter(self.storage)
        key = next(it)
        while i<n:
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
                return self.storage[key].name
            elif index.column() == 1:
                return self.storage[key].default
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
        if not(0 <= section < len(self.headers)):
            return None
        elif role != QtCore.Qt.DisplayRole:
            return None
        elif orientation != QtCore.Qt.Horizontal:
            return None
        else:
            return self.headers[section]

