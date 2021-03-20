# -*- coding: utf-8 -*-
"""
This file contains a custom QAbstractTableModel object providing text data for all logged records.

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

__all__ = ('LogRecordsTableModel',)

import traceback
from datetime import datetime
from collections import deque
from PySide2 import QtCore, QtGui


class LogRecordsTableModel(QtCore.QAbstractTableModel):
    """ This is a Qt model that represents textual information about all logged records.
    Can be displayed with a QTableView for example.
    """

    _color_map = {'debug'   : QtGui.QColor('#77F'),
                  'info'    : QtGui.QColor('#1F1'),
                  'warning' : QtGui.QColor('#F90'),
                  'error'   : QtGui.QColor('#F11'),
                  'critical': QtGui.QColor('#FF00FF'),
                  }
    _fallback_color = QtGui.QColor('#FFF')
    _header = ('Time', 'Level', 'Source', 'Message')

    def __init__(self, *args, max_records=10000, **kwargs):
        super().__init__(*args, **kwargs)

        self._max_records = max(int(max_records), 1)
        self._records = list()
        self._begin = 0
        self._end = 0
        self._fill_count = 0

    def rowCount(self, parent=None):
        """ Returns the number of log records stored in the model.

        @return int: number of log records stored
        """
        return self._fill_count

    def columnCount(self, parent=None):
        """ Returns the number of columns each log record has.

        @return int: number of log record columns
        """
        return len(self._header)

    def flags(self, index):
        """ Determines what can be done with log record cells in the table view.

        @param QModelIndex index: cell for which the flags are requested

        @return Qt.ItemFlags: actions allowed for this cell
        """
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable

    def data(self, index, role):
        """ Get data from model for a given cell. Data can have a role that affects display.

        @param QModelIndex index: cell for which data is requested
        @param ItemDataRole role: role for which data is requested

        @return QVariant: data for given cell and role
        """
        if index.isValid():
            record = self._records[(self._begin + index.row()) % self._max_records]
            if role == QtCore.Qt.TextColorRole:
                return self._color_map.get(record[1], self._fallback_color)
            if role in (QtCore.Qt.DisplayRole, QtCore.Qt.ToolTipRole, QtCore.Qt.EditRole):
                return record[index.column()]

    def headerData(self, section, orientation, role=None):
        """ Data for the table view headers.

        @param int section: number of the column to get header data for
        @param Qt.Orientation orientation: orientation of header (horizontal or vertical)
        @param ItemDataRole role: role for which to get data

        @return QVariant: header data for given column and role
        """
        if (role is None or role == QtCore.Qt.DisplayRole) and orientation == QtCore.Qt.Horizontal:
            try:
                return self._header[section]
            except IndexError:
                pass
        return

    @QtCore.Slot(object)
    def add_record(self, data):
        """ Add a single log entry to the end of the table model.

        @param logging.LogRecord data: log record as returned from logging module
        @return bool: True if adding entry succeeded, False otherwise
        """
        if self._fill_count < self._max_records:
            self.beginInsertRows(QtCore.QModelIndex(), self._end, self._end)
            self._records.append(self._format_log_record(data))
            self._fill_count += 1
            self._end = (self._end + 1) % self._max_records
            self.endInsertRows()
        else:
            row = self._max_records - 1
            self.beginRemoveRows(QtCore.QModelIndex(), 0, 0)
            self._begin = (self._begin + 1) % self._max_records
            self._fill_count -= 1
            self.endRemoveRows()

            self.beginInsertRows(QtCore.QModelIndex(), row, row)
            self._records[self._end] = self._format_log_record(data)
            self._end = (self._end + 1) % self._max_records
            self._fill_count += 1
            self.endInsertRows()

    @QtCore.Slot()
    def clear(self):
        self.beginResetModel()
        self._begin = 0
        self._end = 0
        self._fill_count = 0
        self._records = list()
        self.endResetModel()

    @property
    def max_size(self):
        return self._max_records

    @staticmethod
    def _format_log_record(record):
        # Compose message to display
        message = record.getMessage()  # message if hasattr(record, 'message') else record.msg
        if record.exc_info is not None:
            message += '\n\n{0}'.format(traceback.format_exception(*record.exc_info)[-1][:-1])
            tb = '\n'.join(traceback.format_exception(*record.exc_info)[:-1])
            if tb:
                message += '\n{0}'.format(tb)

        # Create human-readable timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')

        # return 4 element tuple (timestamp, level, name, message)
        return timestamp, record.levelname, record.name, message
