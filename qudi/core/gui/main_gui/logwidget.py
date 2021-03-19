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
"""

from PySide2 import QtCore, QtGui, QtWidgets
from qudi.core.logger import record_table_model


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
        model = self.sourceModel()
        level = model.data(model.index(source_row, 1), QtCore.Qt.DisplayRole)
        if level is None:
            return False
        return level in self._show_levels

    def set_levels(self, levels):
        """
        Set which types of messages are shown through the filter.

        @param set(str) levels: Set of all levels that should be shown
        """
        self._show_levels = frozenset(levels)
        self.invalidateFilter()


class SelectableTextDelegate(QtWidgets.QStyledItemDelegate):
    """A subclass of QStyledItemDelegate to display a text editor for copying text fragments.
    """
    def createEditor(self, parent, option, index):
        """Overwrite method from base class QStyledItemDelegate to show a read-only QLabel widget.
        This is necessary to disable editing by the user but still be able to mark and copy text.

        @param QObject parent: The parent object for the editor to be created
        @param QStyleOptionViewItem option: Display options for the editor widget
        @param QModelIndex index: Data model index

        @return QLabel: QLabel instance
        """
        editor = QtWidgets.QLabel(parent)
        editor.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        editor.setAlignment(option.displayAlignment)
        return editor

    def setEditorData(self, editor, index):
        """
        Overwrite method from base class QStyledItemDelegate to fill the QLineEdit widget with data.

        @param QLineEdit editor: Editor widget to be populated with data
        @param QModelIndex index: Data model index
        """
        data = index.data(QtCore.Qt.EditRole)
        editor.setText(f' {data}')


class LogTableWidget(QtWidgets.QTableView):
    """ Customized QTableView including the model for display of logging entries
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.filter_model = LogFilterProxy()
        self.filter_model.setSourceModel(record_table_model)
        self.setModel(self.filter_model)

        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.setEditTriggers(QtWidgets.QTableView.DoubleClicked)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QtWidgets.QTableView.NoSelection)
        self.setHorizontalScrollMode(QtWidgets.QTableView.ScrollPerPixel)
        self.setVerticalScrollMode(QtWidgets.QTableView.ScrollPerPixel)
        self.setShowGrid(False)
        self.setCornerButtonEnabled(False)
        self.horizontalHeader().setCascadingSectionResizes(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().hide()
        self.setItemDelegate(SelectableTextDelegate())
        self.horizontalHeader().setMinimumSectionSize(50)
        self.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        # Set fixed with for "Time" and "Level" columns since they contain fixed width strings
        metrics = QtGui.QFontMetrics(self.font())
        self.setColumnWidth(0, metrics.horizontalAdvance(' 5555-55-55 55:55:55 '))
        self.setColumnWidth(1, metrics.horizontalAdvance(' warning '))
        # Estimate starting width of "Source" column
        self.setColumnWidth(2, metrics.horizontalAdvance(__name__ + __name__))

        self.filter_model.rowsInserted.connect(self._entry_added)

    @QtCore.Slot(QtCore.QModelIndex, int, int)
    def _entry_added(self, parent, first, last):
        while first <= last:
            self.resizeRowToContents(first)
            first += 1
        self.scrollToBottom()

    def set_level_filter(self, show_levels):
        self.filter_model.set_levels(show_levels)
        self.scrollToBottom()


class LogWidget(QtWidgets.QSplitter):
    """A widget to show log entries and filter them.
    """

    def __init__(self, parent=None, **kwargs):
        """
        Creates the log widget.

        @param QObject parent: Qt parent object for log widget
        @param Manager manager: Manager instance this widget belongs to
        """
        super().__init__(QtCore.Qt.Horizontal, parent, **kwargs)

        # Build GUI elements
        # Set up QTableView to display log entries
        self.log_tablewidget = LogTableWidget()
        self.log_tablewidget.setObjectName('log_table_widget')

        # Set up QTreeWidget for log filter ui
        self.filter_treewidget = QtWidgets.QTreeWidget()
        self.filter_treewidget.setObjectName('filter_treewidget')
        self.filter_treewidget.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                             QtWidgets.QSizePolicy.Preferred)
        self.filter_treewidget.setMinimumSize(210, 0)
        self.filter_treewidget.setEditTriggers(QtWidgets.QTreeWidget.NoEditTriggers)
        self.filter_treewidget.setDropIndicatorShown(False)
        self.filter_treewidget.setDragEnabled(False)
        self.filter_treewidget.setSelectionMode(QtWidgets.QTreeWidget.NoSelection)
        self.filter_treewidget.setSelectionBehavior(QtWidgets.QTreeWidget.SelectItems)
        self.filter_treewidget.setColumnCount(1)
        self.filter_treewidget.setHeaderLabels(('Display:',))
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
        self.filter_treewidget.expandItem(item)

        # embed log view and filter tree into QSplitter widget
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.addWidget(self.log_tablewidget)
        self.addWidget(self.filter_treewidget)
        self.setStretchFactor(0, 1)

        # connect signals
        self.filter_treewidget.itemChanged.connect(self.update_filter_state)

    @QtCore.Slot(object, int)
    def update_filter_state(self, item, column):
        """Update log view from filter widget check states and synchronize check box states.

        @param int item: Item number
        @param int column: Column number
        """
        # check all / uncheck all state
        show_all_item = self.filter_treewidget.topLevelItem(0)
        level_items = [show_all_item.child(ii) for ii in range(show_all_item.childCount())]
        if item is show_all_item:
            self.filter_treewidget.expandItem(item)
            if show_all_item.checkState(0):
                self.filter_treewidget.blockSignals(True)
                for it in level_items:
                    it.setCheckState(0, QtCore.Qt.Checked)
                self.filter_treewidget.blockSignals(False)
            else:
                # Prevent user from unchecking "show all"
                self.filter_treewidget.blockSignals(True)
                show_all_item.setCheckState(0, QtCore.Qt.Checked)
                self.filter_treewidget.blockSignals(False)
        else:
            show_all = all(it.checkState(0) for it in level_items)
            self.filter_treewidget.blockSignals(True)
            show_all_item.setCheckState(0, QtCore.Qt.Checked if show_all else QtCore.Qt.Unchecked)
            self.filter_treewidget.blockSignals(False)

        # set level filters
        level_filter = {str(it.text(0)) for it in level_items if it.checkState(0)}
        self.log_tablewidget.set_level_filter(level_filter)
