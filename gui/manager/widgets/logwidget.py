# -*- coding: utf-8 -*-
"""
This file contains the Qudi log widget class.

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

Derived form ACQ4:
Copyright 2010  Luke Campagnola
Originally distributed under MIT/X11 license. See documentation/MITLicense.txt for more infomation.
"""

from qtpy import QtCore, QtGui, QtWidgets


class LogTableModel(QtCore.QAbstractTableModel):
    """ This is a Qt model that represents the log for display in a QTableView.
    """

    def __init__(self, parent=None, **kwargs):
        """ Set up the model.
        """
        super().__init__(parent, **kwargs)
        self.header = ('Name', 'Time', 'Level', 'Message')
        self.color_map = {
            'debug':   QtGui.QColor('#77F'),
            'info':     QtGui.QColor('#1F1'),
            'warning':  QtGui.QColor('#F90'),
            'error':    QtGui.QColor('#F11'),
            'critical': QtGui.QColor('#FF00FF')
        }
        self.entries = list()

    def rowCount(self, parent=None):
        """
        Gives th number of log entries stored in the model.

        @return int: number of log entries stored
        """
        return len(self.entries)

    def columnCount(self, parent=None):
        """
        Gives the number of columns each log entry has.

        @return int: number of log entry columns
        """
        return len(self.header)

    def flags(self, index):
        """
        Determines what can be done with log entry cells in the table view.

        @param QModelIndex index: cell fo which the flags are requested

        @return Qt.ItemFlags: actions allowed for this cell
        """
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable

    def data(self, index, role):
        """
        Get data from model for a given cell. Data can have a role that affects display.

        @param QModelIndex index: cell for which data is requested
        @param ItemDataRole role: role for which data is requested

        @return QVariant: data for given cell and role
        """
        if not index.isValid():
            return None
        elif role == QtCore.Qt.TextColorRole:
            try:
                return self.color_map[self.entries[index.row()][2]]
            except KeyError:
                return QtGui.QColor('#FFF')
        elif role == QtCore.Qt.DisplayRole:
            return self.entries[index.row()][index.column()]
        elif role == QtCore.Qt.EditRole:
            return self.entries[index.row()][index.column()]
        else:
            return None

    def setData(self, index, value, role=None):
        """
        Set data in model for a given cell. Data can have a role that affects display.

        @param QModelIndex index: cell for which data is requested
        @param QVariant value: data tht is set in the cell
        @param ItemDataRole role: role for which data is requested

        @return bool: True if setting data succeeded, False otherwise
        """
        if role is None or role == QtCore.Qt.EditRole:
            try:
                self.entries[index.row()][index.column()] = value
            except Exception:
                return False
            topleft = self.createIndex(index.row(), 0)
            bottomright = self.createIndex(index.row(), 3)
            self.dataChanged.emit(topleft, bottomright)
            return True

    def headerData(self, section, orientation, role=None):
        """
        Data for the table view headers.

        @param int section: number of the column to get header data for
        @param Qt.Orientation orientation: orientation of header (horizontal or vertical)
        @param ItemDataRole role: role for which to get data

        @return QVariant: header data for given column and role
        """
        if not(0 <= section < len(self.header)):
            return None
        elif role is not None and role != QtCore.Qt.DisplayRole:
            return None
        elif orientation != QtCore.Qt.Horizontal:
            return None
        return self.header[section]

    def insert_entry(self, row, data):
        """
        Helper method to add a single log entry to the model.
        Invokes insert_entries.

        @param int row: row before which to insert log entry
        @param list[4] data: log entry in list format

        @return bool: True if adding entry succeeded, False otherwise
        """
        return self.insert_entries(row, [data])

    def insert_entries(self, row, data):
        """
        Helper method to add multiple log entries to the model by inserting rows and filling them
        with data.

        @param int row: row before which to insert log entry
        @param list data: log entries in list format (list of list of 4 elements)

        @return bool: True if adding entry succeeded, False otherwise
        """
        self.beginInsertRows(QtCore.QModelIndex(), row, row + len(data) - 1)
        self.entries[row:row] = data
        self.endInsertRows()
        top_left = self.createIndex(row, 0)
        bottom_right = self.createIndex(row, 3)
        self.dataChanged.emit(top_left, bottom_right)
        return True

    def removeRow(self, row, parent=None):
        """
        Remove single row (log entry) from model.
        Invokes removeRows.

        @param int row: from which row on to remove rows
        @param QModelIndex parent: parent model index

        @return bool: True if removal succeeded, False otherwise
        """
        return self.removeRows(row, 1, parent)

    def removeRows(self, row, count, parent=None):
        """
        Remove rows (log entries) from model.

        @param int row: from which row on to remove rows
        @param int count: how many rows to remove
        @param QModelIndex parent: parent model index

        @return bool: True if removal succeeded, False otherwise
        """
        if parent is None:
            parent = QtCore.QModelIndex()
        self.beginRemoveRows(parent, row, row + count - 1)
        del self.entries[row:row + count]
        self.endRemoveRows()
        return True


class LogFilterProxy(QtCore.QSortFilterProxyModel):
    """
    A subclass of QProxyFilterModel that determines which log entries contained in the log model
    are shown in the view.
    """

    def __init__(self, parent=None):
        """
        Create the LogFilterProxy.

        @param QObject parent: parent object of filter
        """
        super().__init__(parent)
        self._show_levels = frozenset({'info', 'warning', 'error', 'critical'})

    def filterAcceptsRow(self, source_row, source_parent):
        """
        Determine whether row (log entry) should be shown.

        @param QModelIndex source_row: the row in the source model that we need to filter
        @param QModelIndex source_parent: parent model index

        @return bool: True if row (log entry) should be shown, False otherwise
        """
        index_level = self.sourceModel().index(source_row, 2)
        level = self.sourceModel().data(index_level, QtCore.Qt.DisplayRole)
        if level is None:
            return False
        return level in self._show_levels

    def lessThan(self, left, right):
        """
        Comparison function for sorting rows (log entries)

        @param QModelIndex left: index pointing to the first cell for comparison
        @param QModelIndex right: index pointing to the second cell for comparison

        @return bool: result of comparison left data < right data
        """
        model = self.sourceModel()
        left_data = model.data(self.sourceModel().index(left.row(), 0), QtCore.Qt.DisplayRole)
        right_data = model.data(self.sourceModel().index(right.row(), 0), QtCore.Qt.DisplayRole)
        return left_data < right_data

    def set_levels(self, levels):
        """
        Set which types of messages are shown through the filter.

        @param set(str) levels: Set of all levels that should be shown
        """
        self._show_levels = frozenset(levels)
        self.invalidateFilter()
        return


class AutoToolTipDelegate(QtWidgets.QStyledItemDelegate):
    """ A subclass of QStyledItemDelegate to display a tooltip if the text
        doesn't fit into the cell.
    """
    def createEditor(self, parent, option, index):
        """
        Overwrite method from base class QStyledItemDelegate to show a read-only QLineEdit widget.
        This is necessary to disable editing by the user but still be able to mark and copy text.

        @param QObject parent: The parent object for the editor to be created
        @param QStyleOptionViewItem option: Display options for the editor widget
        @param QModelIndex index: Data model index

        @return QLineEdit: QLineEdit instance configured as read-only
        """
        editor = QtWidgets.QLineEdit(parent)
        editor.setAlignment(option.displayAlignment)
        editor.setFont(option.font)
        editor.setReadOnly(True)
        return editor

    def setEditorData(self, editor, index):
        """
        Overwrite method from base class QStyledItemDelegate to fill the QLineEdit widget with data.

        @param QLineEdit editor: Editor widget to be populated with data
        @param QModelIndex index: Data model index
        """
        data = index.data(QtCore.Qt.EditRole)
        editor.setText(data)
        return

    def helpEvent(self, e, view, option, index):
        """
        The method responsible for displaying the tooltip. It ignores custom tooltips.

        @param QHelpEvent e: the help event
        @param QAbstractItemView view: the view
        @param QStyleOptionViewItem option: the display options
        @param QModelIndex index: the model index
        """
        if e is None or view is None:
            return False

        if e.type() == QtCore.QEvent.ToolTip:
            if index.isValid():
                text = index.data(QtCore.Qt.DisplayRole)
                QtWidgets.QToolTip.showText(e.globalPos(), text, view)
            else:
                QtWidgets.QToolTip.hideText()
            return True
        return super().helpEvent(e, view, option, index)


class LogWidget(QtWidgets.QSplitter):
    """A widget to show log entries and filter them.
    """
    _sigAddEntry = QtCore.Signal(object)

    def __init__(self, parent=None, **kwargs):
        """
        Creates the log widget.

        @param QObject parent: Qt parent object for log widget
        @param Manager manager: Manager instance this widget belongs to
        """
        super().__init__(QtCore.Qt.Horizontal, parent, **kwargs)
        self._log_length = 1000  # Number of max log model entries

        # Set up data model and visibility filter model
        self.log_model = LogTableModel()
        self.filter_model = LogFilterProxy()
        self.filter_model.setSourceModel(self.log_model)

        # Build GUI elements
        # Set up QTableView to display log entries
        self.output_tableview = QtWidgets.QTableView()
        self.output_tableview.setObjectName('output_tableview')
        self.output_tableview.setModel(self.filter_model)
        self.output_tableview.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                            QtWidgets.QSizePolicy.Preferred)
        self.output_tableview.setAutoScroll(False)
        self.output_tableview.setEditTriggers(QtWidgets.QTableView.DoubleClicked)
        self.output_tableview.setDropIndicatorShown(False)
        self.output_tableview.setDragDropOverwriteMode(False)
        self.output_tableview.setAlternatingRowColors(True)
        self.output_tableview.setSelectionMode(QtWidgets.QTableView.NoSelection)
        self.output_tableview.setTextElideMode(QtCore.Qt.ElideRight)
        self.output_tableview.setHorizontalScrollMode(QtWidgets.QTableView.ScrollPerPixel)
        self.output_tableview.setVerticalScrollMode(QtWidgets.QTableView.ScrollPerPixel)
        self.output_tableview.setShowGrid(False)
        self.output_tableview.setGridStyle(QtCore.Qt.NoPen)
        self.output_tableview.setCornerButtonEnabled(False)
        self.output_tableview.horizontalHeader().setCascadingSectionResizes(True)
        self.output_tableview.horizontalHeader().stretchLastSection()
        self.output_tableview.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.Interactive)
        self.output_tableview.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeToContents)
        self.output_tableview.horizontalHeader().setSectionResizeMode(
            2, QtWidgets.QHeaderView.ResizeToContents)
        self.output_tableview.horizontalHeader().setSectionResizeMode(
            3, QtWidgets.QHeaderView.ResizeToContents)
        self.output_tableview.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeToContents)
        self.output_tableview.verticalHeader().hide()
        self.output_tableview.setItemDelegate(AutoToolTipDelegate(self.output_tableview))

        # Set up QTreeWidget for log filter ui
        self.filter_treewidget = QtWidgets.QTreeWidget()
        self.filter_treewidget.setObjectName('filter_treewidget')
        self.filter_treewidget.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                             QtWidgets.QSizePolicy.Preferred)
        self.filter_treewidget.setMinimumSize(210, 0)
        self.filter_treewidget.setEditTriggers(QtWidgets.QTreeWidget.NoEditTriggers)
        self.filter_treewidget.setDropIndicatorShown(False)
        self.filter_treewidget.setDragEnabled(True)
        self.filter_treewidget.setSelectionMode(QtWidgets.QTreeWidget.NoSelection)
        self.filter_treewidget.setSelectionBehavior(QtWidgets.QTreeWidget.SelectItems)
        self.filter_treewidget.setColumnCount(1)
        self.filter_treewidget.setHeaderLabels(('Display:',))
        item = QtWidgets.QTreeWidgetItem()
        item.setText(0, 'Current directory only')
        item.setCheckState(0, QtCore.Qt.Unchecked)
        self.filter_treewidget.addTopLevelItem(item)
        item = QtWidgets.QTreeWidgetItem()
        item.setText(0, 'All message types:')
        item.setCheckState(0, QtCore.Qt.Unchecked)
        for text in ('debug', 'info', 'warning', 'error', 'critical'):
            child_item = QtWidgets.QTreeWidgetItem()
            child_item.setText(0, text)
            check_state = QtCore.Qt.Unchecked if text == 'debug' else QtCore.Qt.Checked
            child_item.setCheckState(0, check_state)
            item.addChild(child_item)
        self.filter_treewidget.addTopLevelItem(item)

        # embed log view and filter tree into QSplitter widget
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.addWidget(self.output_tableview)
        self.addWidget(self.filter_treewidget)

        # connect signals
        self._sigAddEntry.connect(self.add_entry, QtCore.Qt.QueuedConnection)
        self.filter_treewidget.itemChanged.connect(self.update_filter_state)

    @property
    def log_length(self):
        """
        Number of log entries that can be added to the model before discarding old entries.

        @return int: maximum number of log entries to be stored in model
        """
        return self._log_length

    @log_length.setter
    def log_length(self, length):
        """
        Set number of log entries that can be added to the model before discarding old entries.

        @param int length: maximum number of log entries to be stored in model
        """
        length = int(length)
        if length > 0:
            self._log_length = length
        return

    @QtCore.Slot(int)
    def set_log_length(self, length):
        """
        Set number of log entries that can be added to the model before discarding old entries.

        @param int length: maximum number of log entries to be stored in model
        """
        self.log_length = length

    def load_from_file(self, f):
        """Load a log file for display.

          @param str f: path to file that should be laoded.

        f must be able to be read by pyqtgraph configfile.py
        """
        raise NotImplementedError()

    @QtCore.Slot(object)
    def add_entry(self, entry):
        """
        Add a log entry to the log view.

        @param dict entry: log entry in dict format
        """
        # All incoming messages begin here
        # for thread safety:
        if QtCore.QThread.currentThread() != QtCore.QCoreApplication.instance().thread():
            self._sigAddEntry.emit(entry)
            return
        if self.log_model.rowCount() > self.log_length:
            self.log_model.removeRows(0, self.log_model.rowCount() - self.log_length)
        text = entry['message']
        if entry.get('exception') is not None:
            if 'reasons' in entry['exception']:
                text += '\n' + entry['exception']['reasons']
            if 'message' in entry['exception']:
                text += '\n' + entry['exception']['message']
            for line in entry['exception']['traceback']:
                text += '\n' + str(line)
        log_entry = [entry['name'], entry['timestamp'], entry['level'], text]
        self.log_model.insert_entry(self.log_model.rowCount(), log_entry)
        self.output_tableview.scrollToBottom()

    @QtCore.Slot(int)
    def scroll_to_entry(self, entry_index):
        """
        Scroll to row in QTableView.

        @param int entry_index: row index to scroll the view to
        """
        self.output_tableview.scrollTo(self.log_model.index(entry_index, 0))

    @QtCore.Slot(object, int)
    def update_filter_state(self, item, column):
        """
        Update log view from filter widget check states and synchronize check box states.

        @param int item: Item number
        @param int column: Column number
        """
        # check all / uncheck all
        if item is self.filter_treewidget.topLevelItem(1):
            if item.checkState(0):
                for ii in range(item.childCount()):
                    item.child(ii).setCheckState(0, QtCore.Qt.Checked)
        elif item.parent() is self.filter_treewidget.topLevelItem(1):
            if not item.checkState(0):
                self.filter_treewidget.topLevelItem(1).setCheckState(0, QtCore.Qt.Unchecked)

        # level filter
        level_filter = set()
        for ii in range(self.filter_treewidget.topLevelItem(1).childCount()):
            child = self.filter_treewidget.topLevelItem(1).child(ii)
            if self.filter_treewidget.topLevelItem(1).checkState(0) or child.checkState(0):
                level_filter.add(str(child.text(0)))
        self.filter_model.set_levels(level_filter)
