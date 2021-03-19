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

    def __init__(self, *args, max_entries=1000, **kwargs):
        super().__init__(*args, **kwargs)

        self.max_entries = max(int(max_entries), 1)
        self._entries = list()

    def rowCount(self, parent=None):
        """ Returns the number of log entries stored in the model.

        @return int: number of log entries stored
        """
        return len(self._entries)

    def columnCount(self, parent=None):
        """ Returns the number of columns each log entry has.

        @return int: number of log entry columns
        """
        return len(self._header)

    def flags(self, index):
        """ Determines what can be done with log entry cells in the table view.

        @param QModelIndex index: cell fo which the flags are requested

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
            if role == QtCore.Qt.TextColorRole:
                return self._color_map.get(self._entries[index.row()][1], self._fallback_color)
            if role in (QtCore.Qt.DisplayRole, QtCore.Qt.ToolTipRole, QtCore.Qt.EditRole):
                return self._entries[index.row()][index.column()]
        return

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

    @QtCore.Slot(object)
    def add_entry(self, data):
        """ Add a single log entry to the end of the table model.

        @param logging.LogRecord data: log record as returned from logging module
        @return bool: True if adding entry succeeded, False otherwise
        """
        if self.free_slots < 1:
            self.beginRemoveRows(QtCore.QModelIndex(), 0, 0)
            self._entries.pop(0)
            self.endRemoveRows()

        row = len(self._entries)
        self.beginInsertRows(QtCore.QModelIndex(), row, row)
        self._entries.append(self._format_log_record(data))
        self.endInsertRows()

    @property
    def free_slots(self):
        """ Read-Only property representing the number of free log entry slots that can be filled
        before entries are discarded from the top of the table.

        @return int: Number of free entry slots
        """
        return self.max_entries - len(self._entries)
