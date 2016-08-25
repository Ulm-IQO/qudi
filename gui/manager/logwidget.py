# -*- coding: utf-8 -*-
"""
This file contains the QuDi log widget class.

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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>

Derived form ACQ4:
Copyright 2010  Luke Campagnola
Originally distributed under MIT/X11 license. See documentation/MITLicense.txt for more infomation.
"""

import qtpy
from qtpy import QtCore, QtGui, QtWidgets, uic
import os
import html

import sys


class LogModel(QtCore.QAbstractTableModel):
    """ This is a Qt model that represents the log for dislpay in a QTableView.
    """

    def __init__(self, **kwargs):
        """ Set up the model.
        """
        super().__init__(**kwargs)
        self.header = ['Name', 'Time', 'Level', 'Message']
        self.fgColor = {
            'debug':   QtGui.QColor('#11F'),
            'info':     QtGui.QColor('#1F1'),
            'warning':  QtGui.QColor('#F90'),
            'error':    QtGui.QColor('#F11'),
            'critical': QtGui.QColor('#FF00FF')
        }
        self.entries = list()

    def rowCount(self, parent=QtCore.QModelIndex()):
        """ Gives th number of log entries  stored in the model.

          @return int: number of log entries stored
        """
        return len(self.entries)

    def columnCount(self, parent=QtCore.QModelIndex()):
        """ Gives the number of columns each log entry has.

          @return int: number of log entry columns
        """
        return len(self.header)

    def flags(self, index):
        """ Determines what can be done with log entry cells in the table view.

          @param QModelIndex index: cell fo which the flags are requested

          @return Qt.ItemFlags: actins allowed fotr this cell
        """
        return QtCore.Qt.ItemIsEnabled |  QtCore.Qt.ItemIsSelectable | \
            QtCore.Qt.ItemIsEditable

    def data(self, index,  role):
        """ Get data from model for a given cell. Data can have a role that
            affects display.

          @param QModelIndex index: cell for which data is requested
          @param ItemDataRole role: role for which data is requested

          @return QVariant: data for given cell and role
        """
        if not index.isValid():
            return None
        elif role == QtCore.Qt.TextColorRole:
            try:
                return self.fgColor[self.entries[index.row()][2]]
            except KeyError:
                print('fgcolor', self.entries[index.row()][2])
                return QtGui.QColor('#FFF')
        elif role == QtCore.Qt.DisplayRole:
            return self.entries[index.row()][index.column()]
        elif role == QtCore.Qt.EditRole:
            return self.entries[index.row()][index.column()]
        else:
            return None

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        """ Set data in model for a given cell. Data can have a role that
            affects display.

          @param QModelIndex index: cell for which data is requested
          @param QVariant value: data tht is set in the cell
          @param ItemDataRole role: role for which data is requested

          @return bool: True if setting data succeeded, False otherwise
        """
        if role == QtCore.Qt.EditRole:
            try:
                self.entries[index.row()][index.column()] = value
            except Exception as e:
                print(e)
                return False
            topleft = self.createIndex(index.row(), 0)
            bottomright = self.createIndex(index.row(), 3)
            self.dataChanged.emit(topleft, bottomright)
            return True

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        """ Data for the table view headers.

          @param int section: number of the column to get header data for
          @param Qt.Orientation: orientation of header (horizontal or vertical)
          @param ItemDataRole: role for which to get data

          @return QVariant: header data for given column and role
          """
        if section < 0 and section > len(self.header) - 1:
            return None
        elif role != QtCore.Qt.DisplayRole:
            return None
        elif orientation != QtCore.Qt.Horizontal:
            return None
        else:
            return self.header[section]

    def insertRows(self, row, count, parent=QtCore.QModelIndex()):
        """ Insert empty rows (log entries) into the model.

          @param int row: before which row to insert new rows
          @param int count: how many rows to insert
          @param QModelIndex parent: patent model index

          @return bool: True if insertion succeeded, False otherwise
        """
        self.beginInsertRows(parent, row, row + count - 1)
        insertion = list()
        for ii in range(count):
            insertion.append([None, None, None, None])
        self.entries[row:row] = insertion
        self.endInsertRows()
        return True

    def addRow(self, row, data, parent=QtCore.QModelIndex()):
        """ Add a single log entry to model.
          @param int row: row before which to insert log entry
          @param list data: log entry in list format (5 elements)
          @param QModelIndex parent: parent model index

          @return bool: True if adding entry succeede, False otherwise
        """
        return self.addRows(row, [data], parent)

    def addRows(self, row, data, parent=QtCore.QModelIndex()):
        """ Add a log entries to model.
          @param int row: row before which to insert log entry
          @param list data: log entries in list format (list of lists of
                            4 elements)
          @param QModelIndex parent: parent model index

          @return bool: True if adding entry succeede, False otherwise
        """
        count = len(data)
        self.beginInsertRows(parent, row, row + count - 1)
        self.entries[row:row] = data
        self.endInsertRows()
        topleft = self.createIndex(row, 0)
        bottomright = self.createIndex(row, 3)
        self.dataChanged.emit(topleft, bottomright)
        return True

    def removeRows(self, row, count, parent=QtCore.QModelIndex()):
        """ Remove rows (log entries) from model.

          @param int row: from which row on to remove rows
          @param int count: how many rows to remove
          @param QModelIndex parent: parent model index

          @return bool: True if removal succeeded, False otherwise
        """
        self.beginRemoveRows(parent, row, row + count - 1)
        self.entries[row:row + count] = []
        self.endRemoveRows()
        return True


class LogFilter(QtCore.QSortFilterProxyModel):
    """ A subclass of QProxyFilterModel that determines which log entries
        contained in the log model are shown in the view.
    """

    def __init__(self, parent=None):
        """ Create the LogFilter.

          @param QObject parent: parent object of filter
        """
        super().__init__(parent)
        self.show_levels = ['info', 'warning', 'error', 'critical']

    def filterAcceptsRow(self, sourceRow, sourceParent):
        """ Determine wheter row (log entry) should be shown.

          @param QModelIndex sourceRow: the row in the source model that we
                 need to judege
          @param QModelIndex sourceParent: parent model index

          @return bool: True if row (log entry) should be shown, False
                        otherwise
        """
        indexLevel = self.sourceModel().index(sourceRow, 2)
        level = self.sourceModel().data(indexLevel,
                                        QtCore.Qt.DisplayRole)
        if level is None:
            return False
        return level in self.show_levels

    def lessThan(self, left, right):
        """ Comparison function for sorting rows (log entries)

          @param QModelIndex left: index pointing to the first cell for
                             comparison
          @param QModelIndex right: index pointing to the second cell for
                             comparison

          @return bool: result of comparison left data < right data
        """
        leftData = self.sourceModel().data(self.sourceModel().index(
            left.row(), 0), QtCore.Qt.DisplayRole)
        rightData = self.sourceModel().data(self.sourceModel().index(
            right.row(), 0), QtCore.Qt.DisplayRole)
        return leftData < rightData

    def setLevels(self, levels):
        """ Set which types of messages are shown through the filter.

          @param list(str) levels: list of all levels that should be shown
        """
        self.show_levels = levels
        self.invalidateFilter()


class AutoToolTipDelegate(QtWidgets.QStyledItemDelegate):
    """ A subclass of QStyledItemDelegate to display a tooltip if the text
        doesn't fit into the cell.
    """

    def helpEvent(self, e, view, option, index):
        """ The method responsible for displaying the tooltip. It ignores
            custom tooltips.

          @param QHelpEvent e: the help event
          @param QAbstractItemView view: the view
          @param QStyleOptionViewItem option: the options
          @param QModelIndex index: the model index
        """

        if e is None or view is None:
            return False

        if e.type() == QtCore.QEvent.ToolTip:
            rect = view.visualRect(index)
            size = self.sizeHint(option, index)
            if rect.width() < size.width():
                tooltip = index.data(QtCore.Qt.DisplayRole)
                QtWidgets.QToolTip.showText(
                    e.globalPos(),
                    '<div>{0}</div>'.format(html.escape(tooltip)),
                    view)
            else:
                QtWidgets.QToolTip.hideText()
            return True
        return super().helpEvent(e, view, option, index)


class LogWidget(QtWidgets.QWidget):
    """A widget to show log entries and filter them.
    """
    sigDisplayEntry = QtCore.Signal(object)  # for thread-safetyness
    sigAddEntry = QtCore.Signal(object)  # for thread-safetyness
    sigScrollToAnchor = QtCore.Signal(object)  # for internal use.

    def __init__(self, manager=None, **kwargs):
        """Creates the log widget.

        @param object parent: Qt parent object for log widet

        """
        super().__init__(**kwargs)
        self._manager = manager
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_logwidget.ui')

        # Load it
        uic.loadUi(ui_file, self)

        self.logLength = 1000

        # Set up data model and visibility filter
        self.model = LogModel()
        self.filtermodel = LogFilter()
        self.filtermodel.setSourceModel(self.model)
        self.output.setModel(self.filtermodel)

        # set up able view properties
        # setResizeMode is deprecated in Qt5 (and therefore not available
        # in pyqt5
        if qtpy.PYQT4 or qtpy.PYSIDE:
            self.output.horizontalHeader().setResizeMode(
                0, QtWidgets.QHeaderView.Interactive)
            self.output.horizontalHeader().setResizeMode(
                1, QtWidgets.QHeaderView.ResizeToContents)
            self.output.horizontalHeader().setResizeMode(
                2, QtWidgets.QHeaderView.ResizeToContents)
            self.output.horizontalHeader().setResizeMode(
                3, QtWidgets.QHeaderView.ResizeToContents)
            self.output.verticalHeader().setResizeMode(
                QtWidgets.QHeaderView.ResizeToContents)
        else:
            self.output.horizontalHeader().setSectionResizeMode(
                0, QtWidgets.QHeaderView.Interactive)
            self.output.horizontalHeader().setSectionResizeMode(
                1, QtWidgets.QHeaderView.ResizeToContents)
            self.output.horizontalHeader().setSectionResizeMode(
                2, QtWidgets.QHeaderView.ResizeToContents)
            self.output.horizontalHeader().setSectionResizeMode(
                3, QtWidgets.QHeaderView.ResizeToContents)
            self.output.verticalHeader().setSectionResizeMode(
                QtWidgets.QHeaderView.ResizeToContents)
        self.output.setTextElideMode(QtCore.Qt.ElideRight)
        self.output.setItemDelegate(AutoToolTipDelegate(self.output))

        # connect signals
        self.sigDisplayEntry.connect(self.displayEntry,
                                     QtCore.Qt.QueuedConnection)
        self.sigAddEntry.connect(self.addEntry, QtCore.Qt.QueuedConnection)
        self.filterTree.itemChanged.connect(self.setCheckStates)

    def setManager(self, manager):
        """
        @param object manager: the manager
        """
        self._manager = manager

    def setStylesheet(self, logStyleSheet):
        """
        @param str logStyleSheet: stylesheet for log view
        """
        self.stylesheet = logStyleSheet

    def loadFile(self, f):
        """Load a log file for display.

          @param str f: path to file that should be laoded.

        f must be able to be read by pyqtgraph configfile.py
        """
        pass

    def addEntry(self, entry):
        """Add a log entry to the log view.

          @param dict entry: log entry in dict format
        """
        # All incoming messages begin here
        # for thread-safetyness:
        isGuiThread = QtCore.QThread.currentThread(
        ) == QtCore.QCoreApplication.instance().thread()
        if not isGuiThread:
            self.sigAddEntry.emit(entry)
            return
        if self.model.rowCount() > self.logLength:
            self.model.removeRows(0, self.model.rowCount() - self.logLength)
        text = entry['message']
        if entry.get('exception', None) is not None:
            if 'reasons' in entry['exception']:
                text += '\n' + entry['exception']['reasons']
            if 'message' in entry['exception']:
                text += '\n' + entry['exception']['message']
            for line in entry['exception']['traceback']:
                text += '\n' + str(line)
        logEntry = [entry['name'], entry['timestamp'], entry['level'], text]
        self.model.addRow(self.model.rowCount(), logEntry)
        self.output.scrollToBottom()

    def displayEntry(self, entry):
        """ Scroll to entry in QTableView.

          @param int entry: entry to scroll the view to
        """
        self.output.scrollTo(self.model.index(entry, 0))

    def setLogLength(self, length):
        """ Set how many log entries will be stored by the model before
            discarding old entries when new entries are added.

          @param int length: maximum number of log entries to be stored in
                             model
        """
        if length > 0:
            self.logLength = length

    def setCheckStates(self, item, column):
        """ Set state of the checkbox in the filter list and update log view.

          @param int item: Item number
          @param int column: Column number
        """
        # check all / uncheck all
        if item == self.filterTree.topLevelItem(1):
            if item.checkState(0):
                for ii in range(item.childCount()):
                    item.child(ii).setCheckState(0, QtCore.Qt.Checked)
        elif item.parent() == self.filterTree.topLevelItem(1):
            if not item.checkState(0):
                self.filterTree.topLevelItem(1).setCheckState(0,
                                                              QtCore.Qt.Unchecked)

        # level filter
        levelFilter = []
        for ii in range(self.filterTree.topLevelItem(1).childCount()):
            child = self.filterTree.topLevelItem(1).child(ii)
            if self.filterTree.topLevelItem(1).checkState(0) \
                    or child.checkState(0):
                text = child.text(0)
                levelFilter.append(str(text))
        self.filtermodel.setLevels(levelFilter)
