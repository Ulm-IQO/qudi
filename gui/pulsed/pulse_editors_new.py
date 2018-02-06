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

import numpy as np
import copy

from qtpy import QtCore, QtGui, QtWidgets
from collections import OrderedDict
from gui.pulsed.pulsed_item_delegates import ScienDSpinBoxItemDelegate, ComboBoxItemDelegate
from gui.pulsed.pulsed_item_delegates import DigitalStatesItemDelegate, AnalogParametersItemDelegate
from gui.pulsed.pulsed_item_delegates import SpinBoxItemDelegate
from logic.pulse_objects import PulseBlockElement, PulseBlock, PulseBlockEnsemble, PulseSequence
import logic.sampling_functions as sf


class BlockEditorTableModel(QtCore.QAbstractTableModel):
    """

    """
    # signals
    sigColumnWidthChanged = QtCore.Signal(int, int)

    # User defined roles for model data access
    lengthRole = QtCore.Qt.UserRole + 1
    incrementRole = QtCore.Qt.UserRole + 2
    digitalStateRole = QtCore.Qt.UserRole + 3
    analogFunctionRole = QtCore.Qt.UserRole + 4
    analogShapeRole = QtCore.Qt.UserRole + 5
    analogParameterRole = QtCore.Qt.UserRole + 6
    useAsTickRole = QtCore.Qt.UserRole + 7
    analogChannelsRole = QtCore.Qt.UserRole + 8
    digitalChannelsRole = QtCore.Qt.UserRole + 9
    blockElementRole = QtCore.Qt.UserRole + 10
    pulseBlockRole = QtCore.Qt.UserRole + 11

    def __init__(self):
        super().__init__()

        self.digital_channels = list()
        self.analog_channels = list()

        # The actual model data container.
        self._pulse_block = PulseBlock('EDITOR CONTAINER')

        # Create header strings
        self._create_header_data()

        # The current column widths.
        # The fact that the widths are stored in the model saves a huge amount of computational
        # time when resizing columns due to item changes.
        self._col_widths = self._get_column_widths()
        # Notify the QTableView about a change in column widths
        self._notify_column_width()
        return

    def _create_header_data(self):
        """

        @return:
        """
        # The horizontal header data
        self._h_header_data = ['length\nin s', 'increment\nin s']
        if len(self.digital_channels) > 0:
            self._h_header_data.append('digital\nchannels')
        for chnl in self.analog_channels:
            self._h_header_data.append('{0}\nshape'.format(chnl))
            self._h_header_data.append('{0}\nparameters'.format(chnl))
        return

    def _notify_column_width(self, column=None):
        """

        @param column:
        @return:
        """
        if column is None:
            for column, width in enumerate(self._col_widths):
                self.sigColumnWidthChanged.emit(column, width)
            return

        if isinstance(column, int):
            if column >= 0 and column < len(self._col_widths):
                self.sigColumnWidthChanged.emit(column, self._col_widths[column])
        return

    def _get_column_widths(self):
        """

        @return:
        """
        widths = list()
        for column in range(self.columnCount()):
            width = self._get_column_width(column)
            if width < 0:
                return -1
            widths.append(width)
        return widths

    def _get_column_width(self, column):
        """

        @return:
        """
        if not isinstance(column, int):
            return -1

        if column < self.columnCount():
            has_digital = bool(len(self.digital_channels))

            if column < 2:
                width = 90
            elif column == 2 and has_digital:
                width = 30 * len(self.digital_channels)
            else:
                a_ch_offset = 2 + int(has_digital)
                if (column - a_ch_offset) % 2 == 0:
                    width = 80
                else:
                    channel = self.analog_channels[(column - a_ch_offset) // 2]
                    max_param_number = 0
                    for element in self._pulse_block.element_list:
                        tmp_size = len(element.pulse_function[channel].params)
                        if tmp_size > max_param_number:
                            max_param_number = tmp_size
                    width = 90 * max_param_number

            return width
        else:
            return -1

    def set_activation_config(self, activation_config):
        """

        @param activation_config:
        @return:
        """
        self.beginResetModel()
        self.digital_channels = [chnl for chnl in activation_config if chnl.startswith('d_ch')]
                                 # activation_config[chnl] and chnl.startswith('d_ch')]
        self.analog_channels = [chnl for chnl in activation_config if chnl.startswith('a_ch')]
                                # activation_config[chnl] and chnl.startswith('a_ch')]

        analog_shape = OrderedDict()
        for chnl in self.analog_channels:
            analog_shape[chnl] = sf.Idle()

        digital_state = OrderedDict()
        for chnl in self.digital_channels:
            digital_state[chnl] = False

        elem_list = [PulseBlockElement(pulse_function=analog_shape, digital_high=digital_state)]

        # The actual model data container
        self._pulse_block = PulseBlock('EDITOR CONTAINER', elem_list)

        self._col_widths = [0] * self.columnCount()
        self._col_widths = self._get_column_widths()
        self._create_header_data()

        self.endResetModel()

        self._notify_column_width()
        return

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._pulse_block.element_list)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 2 + int(len(self.digital_channels) > 0) + 2 * len(self.analog_channels)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == self.pulseBlockRole:
            return self._pulse_block
        if role == self.analogChannelsRole:
            return self._pulse_block.analog_channels
        if role == self.digitalChannelsRole:
            return self._pulse_block.digital_channels

        if not index.isValid():
            return None
        if role == QtCore.Qt.DisplayRole:
            return None
        if role == self.lengthRole:
            return self._pulse_block.element_list[index.row()].init_length_s
        if role == self.incrementRole:
            return self._pulse_block.element_list[index.row()].increment_s
        if role == self.digitalStateRole:
            return self._pulse_block.element_list[index.row()].digital_high
        if role == self.analogFunctionRole:
            element = self._pulse_block.element_list[index.row()]
            if len(self.digital_channels) > 0:
                col_offset = 3
            else:
                col_offset = 2
            analog_chnl = self.analog_channels[(index.column() - col_offset) // 2]
            return element.pulse_function[analog_chnl]
        if role == self.analogShapeRole:
            element = self._pulse_block.element_list[index.row()]
            if len(self.digital_channels) > 0:
                col_offset = 3
            else:
                col_offset = 2
            analog_chnl = self.analog_channels[(index.column() - col_offset) // 2]
            return element.pulse_function[analog_chnl].__class__.__name__
        if role == self.analogParameterRole:
            element = self._pulse_block.element_list[index.row()]
            if len(self.digital_channels) > 0:
                col_offset = 3
            else:
                col_offset = 2
            analog_chnl = self.analog_channels[(index.column() - col_offset) // 2]
            return vars(element.pulse_function[analog_chnl])
        if role == self.useAsTickRole:
            return self._pulse_block.element_list[index.row()].use_as_tick
        if role == self.blockElementRole:
            return self._pulse_block.element_list[index.row()]

        return None

    def setData(self, index, data, role=QtCore.Qt.DisplayRole):
        """
        """
        if isinstance(data, PulseBlockElement):
            self._pulse_block.element_list[index.row()] = data
            print('setData:', data, 'at index', index.row())
            return

        if role == self.lengthRole and isinstance(data, (int, float)):
            self._pulse_block.element_list[index.row()].init_length_s = data
        elif role == self.incrementRole and isinstance(data, (int, float)):
            self._pulse_block.element_list[index.row()].increment_s = data
        elif role == self.digitalStateRole and isinstance(data, dict):
            self._pulse_block.element_list[index.row()].digital_high = data
        elif role == self.analogShapeRole and isinstance(data, str):
            if self.data(index=index, role=self.analogShapeRole) != data:
                sampling_func = getattr(sf, data)
                if len(self.digital_channels) > 0:
                    col_offset = 3
                else:
                    col_offset = 2
                chnl = self.analog_channels[(index.column() - col_offset) // 2]
                self._pulse_block.element_list[index.row()].pulse_function[chnl] = sampling_func()

                new_column_width = self._get_column_width(index.column()+1)
                if new_column_width >= 0 and new_column_width != self._col_widths[index.column()+1]:
                    self._col_widths[index.column() + 1] = new_column_width
                    self._notify_column_width(index.column()+1)

        elif role == self.analogParameterRole and isinstance(data, dict):
            if len(self.digital_channels) > 0:
                col_offset = 3
            else:
                col_offset = 2
            chnl = self.analog_channels[(index.column() - col_offset) // 2]
            self._pulse_block.element_list[index.row()].pulse_function[chnl].__init__(**data)
        elif role == self.useAsTickRole and isinstance(data, bool):
            self._pulse_block.element_list[index.row()].use_as_tick = data
        elif role == self.pulseBlockRole and isinstance(data, PulseBlock):
            self._pulse_block = data
        return

    def headerData(self, section, orientation, role):
        # Horizontal header
        if orientation == QtCore.Qt.Horizontal:
            # if role == QtCore.Qt.BackgroundRole:
            #     return QVariant(QBrush(QColor(Qt::green), Qt::SolidPattern))
            if role == QtCore.Qt.SizeHintRole:
                if section < len(self._col_widths):
                    return QtCore.QSize(self._col_widths[section], 40)

            if role == QtCore.Qt.DisplayRole:
                if section < len(self._h_header_data):
                    return self._h_header_data[section]

        # Vertical header
        # if orientation == QtCore.Qt.Vertical:
        #     if role == QtCore.Qt.BackgroundRole:
        #         return QtCore.Qt.QVariant(QtGui.Qt.QBrush(QtGui.Qt.QColor(QtCore.Qt.green),
        #                                                   QtCore.Qt.SolidPattern))
        return super().headerData(section, orientation, role)

    def flags(self, index):
        return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def insertRows(self, row, count, parent=None):
        """

        @param row:
        @param count:
        @param parent:
        @return:
        """
        # Sanity/range checking
        if row < 0 or row > self.rowCount():
            return False

        if parent is None:
            parent = QtCore.QModelIndex()

        self.beginInsertRows(parent, row, row + count - 1)

        analog_shape = OrderedDict()
        for chnl in self.analog_channels:
            analog_shape[chnl] = sf.Idle()

        digital_state = OrderedDict()
        for chnl in self.digital_channels:
            digital_state[chnl] = False

        for i in range(count):
            self._pulse_block.element_list.insert(
                row,
                PulseBlockElement(pulse_function=analog_shape.copy(), digital_high=digital_state))

        self._pulse_block._refresh_parameters()

        self.endInsertRows()
        return True

    def removeRows(self, row, count, parent=None):
        """

        @param row:
        @param count:
        @param parent:
        @return:
        """
        # Sanity/range checking
        if row < 0 or row >= self.rowCount():
            return False
        if (row + count) > self.rowCount():
            return False

        if parent is None:
            parent = QtCore.QModelIndex()

        self.beginRemoveRows(parent, row, row + count - 1)

        del(self._pulse_block.element_list[row:row+count])
        self._pulse_block._refresh_parameters()
        self._rescale_column_widths()

        self.endRemoveRows()
        return True

    def set_pulse_block(self, pulse_block):
        """

        @param pulse_block:
        @return:
        """
        if sorted(pulse_block.analog_channels) != sorted(self.analog_channels):
            return False
        if sorted(pulse_block.digital_channels) != sorted(self.digital_channels):
            return False
        self.beginResetModel()
        self.setData(QtCore.QModelIndex(), pulse_block, self.pulseBlockRole)
        self._rescale_column_widths()
        self.endResetModel()
        return True


class BlockEditor(QtWidgets.QTableView):
    """

    """
    def __init__(self, parent):
        # Initialize inherited QTableView
        super().__init__(parent)

        # Create custom data model and hand it to the QTableView.
        # (essentially it's a PulseBlock instance with QAbstractTableModel interface)
        model = BlockEditorTableModel()
        self.setModel(model)

        # Connect the custom signal sigColumnWidthChanged from the model to the setColumnWidth
        # slot of QTableView in order to resize the columns upon resizing.
        self.model().sigColumnWidthChanged.connect(self.setColumnWidth)

        # Set header sizes
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        # self.horizontalHeader().setStyleSheet('QHeaderView { font-weight: 400; }')
        self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.verticalHeader().setDefaultSectionSize(50)

        # Set item selection and editing behaviour
        self.setEditTriggers(
            QtGui.QAbstractItemView.CurrentChanged | QtGui.QAbstractItemView.SelectedClicked)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)

        # Set item delegates for all table columns
        self._set_item_delegates()
        return

    def _set_item_delegates(self):
        """

        @return:
        """
        # Set item delegates (scientific SpinBoxes) for length and increment column
        length_item_dict = {'unit': 's', 'init_val': 0.0, 'min': -np.inf, 'max': np.inf,
                            'view_stepsize': 1e-9, 'dec': 6}
        self.setItemDelegateForColumn(0, ScienDSpinBoxItemDelegate(self, length_item_dict,
                                                                   self.model().lengthRole))
        increment_item_dict = {'unit': 's', 'init_val': 0.0, 'min': -np.inf, 'max': np.inf,
                               'view_stepsize': 1e-9, 'dec': 6}
        self.setItemDelegateForColumn(1, ScienDSpinBoxItemDelegate(self, increment_item_dict,
                                                                   self.model().incrementRole))

        # If any digital channels are present, set item delegate (custom multi-CheckBox widget)
        # for digital channels column.
        if len(self.model().digital_channels) > 0:
            self.setItemDelegateForColumn(2,
                                          DigitalStatesItemDelegate(self,
                                                                    self.model().digitalStateRole))
            offset_index = 3  # to indicate which column comes next.
        else:
            offset_index = 2  # to indicate which column comes next.

        # loop through all analog channels and set two item delegates for each channel.
        # First a ComboBox delegate for the analog shape column and second a custom
        # composite widget widget for the analog parameters column.
        for num, chnl in enumerate(self.model().analog_channels):
            self.setItemDelegateForColumn(offset_index + 2 * num,
                                          ComboBoxItemDelegate(self, sf.__all__,
                                                               self.model().analogShapeRole))
            self.setItemDelegateForColumn(offset_index + 2 * num + 1,
                                          AnalogParametersItemDelegate(self, [
                                              self.model().analogFunctionRole,
                                              self.model().analogParameterRole]))
        return

    def set_activation_config(self, activation_config):
        """

        @param activation_config:
        @return:
        """
        for column in range(self.model().columnCount()):
            self.setItemDelegateForColumn(column, None)
        self.model().set_activation_config(activation_config)
        #self.setModel(self.model())
        self._set_item_delegates()
        return

    def setModel(self, model):
        """

        @param model:
        @return:
        """
        super().setModel(model)
        for column in range(model.columnCount()):
            width = model.headerData(column, QtCore.Qt.Horizontal, QtCore.Qt.SizeHintRole).width()
            self.setColumnWidth(column, width)
        return

    def rowCount(self):
        return self.model().rowCount()

    def columnCount(self):
        return self.model().columnCount()

    def currentRow(self):
        index = self.currentIndex()
        if index.isValid():
            return index.row()
        else:
            return 0

    def currentColumn(self):
        index = self.currentIndex()
        if index.isValid():
            return index.column()
        else:
            return 0

    def add_elements(self, count=1, at_position=None):
        """

        @param count:
        @param at_position:
        @return: bool, operation success
        """
        # Sanity checking
        if count < 1:
            return False

        if at_position is None:
            at_position = self.model().rowCount()

        # Insert new element(s) as row to the table model/view at the specified position.
        # Append new element(s) to the table model/view if no position was given.
        return self.model().insertRows(at_position, count)

    def remove_elements(self, count=1, at_position=None):
        """

        @param count:
        @param at_position:
        @return: bool, operation success
        """
        # Sanity checking
        if count < 1:
            return False

        if at_position is None:
            at_position = self.model().rowCount() - count

        # Remove rows/elements with index <at_position> to index <at_position + count - 1>
        # Remove last <count> number of elements if no at_position was given.
        return self.model().removeRows(at_position, count)

    def clear(self):
        """
        Removes all PulseBlockElements from the view/model and inserts a single afterwards.

        @return: bool, operation success
        """
        success = self.remove_elements(self.model().rowCount(), 0)
        if not success:
            return False
        self.add_elements(1, 0)
        return True

    def get_block(self):
        """
        Returns a (deep)copy of the PulseBlock instance serving as model for this editor.

        @return: PulseBlock, an instance of PulseBlock
        """
        block_copy = copy.deepcopy(self.model().data(QtCore.QModelIndex(),
                                                     self.model().pulseBlockRole))
        block_copy.name = ''
        return block_copy

    def load_block(self, pulse_block):
        """
        Load an instance of PulseBlock into the model in order to view/edit it.

        @param pulse_block: PulseBlock, the PulseBlock instance to load into the model/view
        @return: bool, operation success
        """
        if not isinstance(pulse_block, PulseBlock):
            return False
        block_copy = copy.deepcopy(pulse_block)
        block_copy.name = 'EDITOR CONTAINER'
        return self.model().set_pulse_block(block_copy)


class EnsembleEditorTableModel(QtCore.QAbstractTableModel):
    """

    """
    # User defined roles for model data access
    repetitionsRole = QtCore.Qt.UserRole + 1
    blockNameRole = QtCore.Qt.UserRole + 2
    blockRole = QtCore.Qt.UserRole + 3
    blockEnsembleRole = QtCore.Qt.UserRole + 4

    def __init__(self):
        super().__init__()

        # dictionary containing block names as keys and PulseBlock instances as items.
        self.available_pulse_blocks = None

        # The actual model data container.
        self._block_ensemble = PulseBlockEnsemble('EDITOR CONTAINER')
        return

    def set_available_pulse_blocks(self, blocks):
        """

        @param blocks: list|dict, list/dict containing all available PulseBlock instances
        @return: int, error code (>=0: OK, <0: ERR)
        """
        # Convert to dictionary
        if isinstance(blocks, list):
            tmp_dict = OrderedDict()
            for blk in blocks:
                if blk.name:
                    tmp_dict[blk.name] = blk
            blocks = tmp_dict

        if not isinstance(blocks, dict):
            return -1

        self.available_pulse_blocks = blocks

        # Check if the PulseBlockEnsemble model instance is empty and set a single block if True.
        if len(self._block_ensemble.block_list) == 0:
            self.insertRows(0, 1)
            return 0

        # Remove blocks from list that are not there anymore
        for row, (block, reps) in enumerate(self._block_ensemble.block_list):
            if block.name not in blocks:
                self.removeRows(row, 1)
        return 0

    def set_rotating_frame(self, rotating_frame=True):
        """

        @param rotating_frame:
        @return:
        """
        self._block_ensemble.rotating_frame = rotating_frame
        return

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._block_ensemble.block_list)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 2

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            return None

        if role == self.blockEnsembleRole:
            return self._block_ensemble

        if not index.isValid():
            return None

        if role == self.repetitionsRole:
            return self._block_ensemble.block_list[index.row()][1]
        if role == self.blockNameRole:
            return self._block_ensemble.block_list[index.row()][0].name
        if role == self.blockRole:
            return self._block_ensemble.block_list[index.row()][0]

        return None

    def setData(self, index, data, role=QtCore.Qt.DisplayRole):
        """
        """
        if role == self.repetitionsRole and isinstance(data, int):
            block = self._block_ensemble.block_list[index.row()][0]
            self._block_ensemble.block_list[index.row()] = (block, data)
        elif role == self.blockNameRole and isinstance(data, str):
            block = self.available_pulse_blocks[data]
            reps = self._block_ensemble.block_list[index.row()][1]
            self._block_ensemble.block_list[index.row()] = (block, reps)
        elif role == self.blockRole and isinstance(data, PulseBlock):
            reps = self._block_ensemble.block_list[index.row()][1]
            self._block_ensemble.block_list[index.row()] = (data, reps)
        elif role == self.blockEnsembleRole and isinstance(data, PulseBlockEnsemble):
            self._block_ensemble = data
        return

    def headerData(self, section, orientation, role):
        # Horizontal header
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                if section == 0:
                    return 'PulseBlock'
                if section == 1:
                    return 'repetitions'
            # if role == QtCore.Qt.BackgroundRole:
            #     return QVariant(QBrush(QColor(Qt::green), Qt::SolidPattern))
            # if role == QtCore.Qt.SizeHintRole:
            #     if section < len(self._col_widths):
            #         return QtCore.QSize(self._col_widths[section], 40)
        return super().headerData(section, orientation, role)

    def flags(self, index):
        return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def insertRows(self, row, count, parent=None):
        """

        @param row:
        @param count:
        @param parent:
        @return:
        """
        # Sanity/range checking
        if row < 0 or row > self.rowCount() or len(self.available_pulse_blocks) < 1:
            return False

        if parent is None:
            parent = QtCore.QModelIndex()

        self.beginInsertRows(parent, row, row + count - 1)

        block = self.available_pulse_blocks[list(self.available_pulse_blocks)[0]]
        for i in range(count):
            self._block_ensemble.block_list.insert(row, (block, 0))

        self._block_ensemble._refresh_parameters()

        self.endInsertRows()
        return True

    def removeRows(self, row, count, parent=None):
        """

        @param row:
        @param count:
        @param parent:
        @return:
        """
        # Sanity/range checking
        if row < 0 or row >= self.rowCount() or (row + count) > self.rowCount():
            return False

        if parent is None:
            parent = QtCore.QModelIndex()

        self.beginRemoveRows(parent, row, row + count - 1)

        del(self._block_ensemble.block_list[row:row+count])

        self._block_ensemble._refresh_parameters()

        self.endRemoveRows()
        return True

    def set_block_ensemble(self, block_ensemble):
        """

        @param block_ensemble:
        @return:
        """
        self.beginResetModel()
        self.setData(QtCore.QModelIndex(), block_ensemble, self.blockEnsembleRole)
        self.endResetModel()
        return True


class EnsembleEditor(QtWidgets.QTableView):
    """

    """
    def __init__(self, parent):
        # Initialize inherited QTableView
        super().__init__(parent)

        # Create custom data model and hand it to the QTableView.
        # (essentially it's a PulseBlockEnsemble instance with QAbstractTableModel interface)
        model = EnsembleEditorTableModel()
        self.setModel(model)

        # Set header sizes
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        # self.horizontalHeader().setDefaultSectionSize(100)
        # self.horizontalHeader().setStyleSheet('QHeaderView { font-weight: 400; }')
        self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.verticalHeader().setDefaultSectionSize(50)

        # Set item selection and editing behaviour
        self.setEditTriggers(
            QtGui.QAbstractItemView.CurrentChanged | QtGui.QAbstractItemView.SelectedClicked)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)

        # Set item delegate (ComboBox) for PulseBlock column
        self.setItemDelegateForColumn(0, ComboBoxItemDelegate(self, list(),
                                                              self.model().blockNameRole,
                                                              QtCore.QSize(100,50)))
        # Set item delegate (SpinBoxes) for repetition column
        repetition_item_dict = {'init_val': 0, 'min': 0, 'max': (2**31)-1}
        self.setItemDelegateForColumn(1, SpinBoxItemDelegate(self, repetition_item_dict,
                                                             self.model().repetitionsRole))
        self.resizeColumnsToContents()
        return

    def set_available_pulse_blocks(self, blocks):
        """

        @param blocks:
        @return: int, error code (>=0: OK, <0: ERR)
        """
        if isinstance(blocks, dict):
            name_list = list(blocks)
        elif isinstance(blocks, list):
            name_list = blocks
        else:
            return -1

        err_code = 0
        # Check if something needs to be changed at all and change if necessary
        if self.model().available_pulse_blocks is None:
            err_code = self.model().set_available_pulse_blocks(blocks.copy())
            new_delegate = ComboBoxItemDelegate(self, name_list, self.model().blockNameRole)
            self.setItemDelegateForColumn(0, new_delegate)
        elif sorted(name_list) != sorted(self.model().available_pulse_blocks):
            err_code = self.model().set_available_pulse_blocks(blocks.copy())
            new_delegate = ComboBoxItemDelegate(self, name_list, self.model().blockNameRole)
            self.setItemDelegateForColumn(0, new_delegate)
        return err_code

    def set_rotating_frame(self, rotating_frame=True):
        """

        @param rotating_frame:
        @return:
        """
        self.model().set_rotating_frame(rotating_frame)
        return

    def rowCount(self):
        return self.model().rowCount()

    def columnCount(self):
        return self.model().columnCount()

    def currentRow(self):
        index = self.currentIndex()
        if index.isValid():
            return index.row()
        else:
            return 0

    def currentColumn(self):
        index = self.currentIndex()
        if index.isValid():
            return index.column()
        else:
            return 0

    def add_blocks(self, count=1, at_position=None):
        """

        @param count:
        @param at_position:
        @return: bool, operation success
        """
        # Sanity checking
        if count < 1:
            return False

        # Insert new block(s) as row to the table model/view at the specified position.
        # Append new block(s) to the table model/view if no position was given.
        if at_position is None:
            at_position = self.model().rowCount()
        return self.model().insertRows(at_position, count)

    def remove_blocks(self, count=1, at_position=None):
        """

        @param count:
        @param at_position:
        @return: bool, operation success
        """
        # Sanity checking
        if count < 1:
            return False

        # Remove rows/blocks with index <at_position> to index <at_position + count - 1>
        # Remove last <count> number of blocks if no at_position was given.
        if at_position is None:
            at_position = self.model().rowCount() - count
        return self.model().removeRows(at_position, count)

    def clear(self):
        """
        Removes all PulseBlocks from the view/model and inserts a single one afterwards.

        @return: bool, operation success
        """
        success = self.remove_blocks(self.model().rowCount(), 0)
        if not success:
            return False
        self.add_elements(1, 0)
        return True

    def get_ensemble(self):
        """
        Returns a (deep)copy of the PulseBlockEnsemble instance serving as model for this editor.

        @return: PulseBlockEnsemble, an instance of PulseBlockEnsemble
        """
        data_container = self.model().data(QtCore.QModelIndex(), self.model().blockEnsembleRole)
        ensemble_copy = copy.deepcopy(data_container)
        ensemble_copy.name = ''
        return ensemble_copy

    def load_ensemble(self, block_ensemble):
        """
        Load an instance of PulseBlockEnsemble into the model in order to view/edit it.

        @param block_ensemble: PulseBlockEnsemble, the PulseBlockEnsemble instance to load into the
                               model/view
        @return: bool, operation success
        """
        if not isinstance(block_ensemble, PulseBlockEnsemble):
            return False
        ensemble_copy = copy.deepcopy(block_ensemble)
        ensemble_copy.name = 'EDITOR CONTAINER'
        return self.model().set_block_ensemble(ensemble_copy)


class SequenceEditorTableModel(QtCore.QAbstractTableModel):
    """

    """
    # User defined roles for model data access
    repetitionsRole = QtCore.Qt.UserRole + 1
    ensembleNameRole = QtCore.Qt.UserRole + 2
    ensembleRole = QtCore.Qt.UserRole + 3
    goToRole = QtCore.Qt.UserRole + 4
    eventJumpRole = QtCore.Qt.UserRole + 5
    sequenceRole = QtCore.Qt.UserRole + 6

    def __init__(self):
        super().__init__()

        # dictionary containing ensemble names as keys and PulseBlockEnsemble instances as items.
        self.available_block_ensembles = None

        # The actual model data container.
        self._pulse_sequence = PulseSequence('EDITOR CONTAINER')
        return

    def set_available_block_ensembles(self, ensembles):
        """

        @param ensembles: list|dict, list/dict containing all available PulseBlockEnsemble instances
        @return: int, error code (>=0: OK, <0: ERR)
        """
        # Convert to dictionary
        if isinstance(ensembles, list):
            tmp_dict = OrderedDict()
            for ens in ensembles:
                if ens.name:
                    tmp_dict[ens.name] = ens
            ensembles = tmp_dict

        if not isinstance(ensembles, dict):
            return -1

        self.available_block_ensembles = ensembles

        # Check if the PulseSequence model instance is empty and set a single ensemble if True.
        if len(self._pulse_sequence.ensemble_list) == 0:
            self.insertRows(0, 1)
            return 0

        # Remove ensembles from list that are not there anymore
        for row, (ensemble, reps) in enumerate(self._pulse_sequence.ensemble_list):
            if ensemble.name not in ensembles:
                self.removeRows(row, 1)
        return 0

    def set_rotating_frame(self, rotating_frame=True):
        """

        @param rotating_frame:
        @return:
        """
        self._pulse_sequence.rotating_frame = rotating_frame
        return

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._pulse_sequence.ensemble_list)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 4

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            return None

        if role == self.sequenceRole:
            return self._pulse_sequence

        if not index.isValid():
            return None

        if role == self.repetitionsRole:
            return self._pulse_sequence.ensemble_list[index.row()][1].get('repetitions')
        if role == self.ensembleNameRole:
            return self._pulse_sequence.ensemble_list[index.row()][0].name
        if role == self.ensembleRole:
            return self._pulse_sequence.ensemble_list[index.row()][0]
        if role == self.goToRole:
            return self._pulse_sequence.ensemble_list[index.row()][1].get('go_to')
        if role == self.eventJumpRole:
            return self._pulse_sequence.ensemble_list[index.row()][1].get('event_jump_to')

        return None

    def setData(self, index, data, role=QtCore.Qt.DisplayRole):
        """
        """
        if role == self.repetitionsRole and isinstance(data, int):
            ensemble = self._pulse_sequence.ensemble_list[index.row()][0]
            self._pulse_sequence.ensemble_list[index.row()] = (ensemble, data)
        elif role == self.ensembleNameRole and isinstance(data, str):
            ensemble = self.available_block_ensembles[data]
            reps = self._pulse_sequence.ensemble_list[index.row()][1]
            self._pulse_sequence.ensemble_list[index.row()] = (ensemble, reps)
        elif role == self.ensembleRole and isinstance(data, PulseBlockEnsemble):
            reps = self._pulse_sequence.ensemble_list[index.row()][1]
            self._pulse_sequence.ensemble_list[index.row()] = (data, reps)
        elif role == self.goToRole and isinstance(data, int):
            self._pulse_sequence.ensemble_list[index.row()][1]['go_to'] = data
        elif role == self.eventJumpRole and isinstance(data, int):
            self._pulse_sequence.ensemble_list[index.row()][1]['event_jump_to'] = data
        elif role == self.sequenceRole and isinstance(data, PulseSequence):
            self._pulse_sequence = data
        return

    def headerData(self, section, orientation, role):
        # Horizontal header
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                if section == 0:
                    return 'BlockEnsemble'
                if section == 1:
                    return 'Repetitions'
                if section == 2:
                    return 'Go To (#)'
                if section == 3:
                    return 'Event Trigger'
        return super().headerData(section, orientation, role)

    def flags(self, index):
        return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def insertRows(self, row, count, parent=None):
        """

        @param row:
        @param count:
        @param parent:
        @return:
        """
        # Sanity/range checking
        if row < 0 or row > self.rowCount() or len(self.available_block_ensembles) < 1:
            return False

        if parent is None:
            parent = QtCore.QModelIndex()

        self.beginInsertRows(parent, row, row + count - 1)

        ensemble = self.available_block_ensembles[list(self.available_block_ensembles)[0]]
        for i in range(count):
            seq_params = {'repetitions': 0, 'go_to': -1, 'event_jump_to': -1}
            self._pulse_sequence.ensemble_list.insert(row, (ensemble, seq_params))

        self._pulse_sequence._refresh_parameters()

        self.endInsertRows()
        return True

    def removeRows(self, row, count, parent=None):
        """

        @param row:
        @param count:
        @param parent:
        @return:
        """
        # Sanity/range checking
        if row < 0 or row >= self.rowCount() or (row + count) > self.rowCount():
            return False

        if parent is None:
            parent = QtCore.QModelIndex()

        self.beginRemoveRows(parent, row, row + count - 1)

        del(self._pulse_sequence.ensemble_list[row:row+count])

        self._pulse_sequence._refresh_parameters()

        self.endRemoveRows()
        return True

    def set_pulse_sequence(self, pulse_sequence):
        """

        @param pulse_sequence:
        @return:
        """
        self.beginResetModel()
        self.setData(QtCore.QModelIndex(), pulse_sequence, self.sequenceRole)
        self.endResetModel()
        return True


class SequenceEditor(QtWidgets.QTableView):
    """

    """
    def __init__(self, parent):
        # Initialize inherited QTableView
        super().__init__(parent)

        # Create custom data model and hand it to the QTableView.
        # (essentially it's a PulseSequence instance with QAbstractTableModel interface)
        model = SequenceEditorTableModel()
        self.setModel(model)

        # Set header sizes
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        # self.horizontalHeader().setDefaultSectionSize(100)
        # self.horizontalHeader().setStyleSheet('QHeaderView { font-weight: 400; }')
        self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.verticalHeader().setDefaultSectionSize(50)

        # Set item selection and editing behaviour
        self.setEditTriggers(
            QtGui.QAbstractItemView.CurrentChanged | QtGui.QAbstractItemView.SelectedClicked)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)

        # Set item delegate (ComboBox) for PulseBlockEnsemble column
        self.setItemDelegateForColumn(0, ComboBoxItemDelegate(self, list(),
                                                              self.model().ensembleNameRole,
                                                              QtCore.QSize(100, 50)))
        # Set item delegate (SpinBoxes) for repetition column
        repetition_item_dict = {'init_val': 0, 'min': -1, 'max': (2**31)-1}
        self.setItemDelegateForColumn(1, SpinBoxItemDelegate(self, repetition_item_dict,
                                                             self.model().repetitionsRole))
        # Set item delegate (SpinBoxes) for go_to column
        goto_item_dict = {'init_val': -1, 'min': -1, 'max': (2 ** 31) - 1}
        self.setItemDelegateForColumn(2, SpinBoxItemDelegate(self, goto_item_dict,
                                                             self.model().goToRole))
        # Set item delegate (SpinBoxes) for event_jump_to column
        eventjump_item_dict = {'init_val': -1, 'min': -1, 'max': (2 ** 31) - 1}
        self.setItemDelegateForColumn(3, SpinBoxItemDelegate(self, eventjump_item_dict,
                                                             self.model().eventJumpRole))
        self.resizeColumnsToContents()
        return

    def set_available_block_ensembles(self, ensembles):
        """

        @param ensembles:
        @return: int, error code (>=0: OK, <0: ERR)
        """
        if isinstance(ensembles, dict):
            name_list = list(ensembles)
        elif isinstance(ensembles, list):
            name_list = ensembles
        else:
            return -1

        err_code = 0
        # Check if something needs to be changed at all and change if necessary
        if self.model().available_block_ensembles is None:
            err_code = self.model().set_available_block_ensembles(ensembles.copy())
            new_delegate = ComboBoxItemDelegate(self, name_list, self.model().ensembleNameRole)
            self.setItemDelegateForColumn(0, new_delegate)
        elif sorted(name_list) != sorted(self.model().available_block_ensembles):
            err_code = self.model().set_available_block_ensembles(ensembles.copy())
            new_delegate = ComboBoxItemDelegate(self, name_list, self.model().ensembleNameRole)
            self.setItemDelegateForColumn(0, new_delegate)
        return err_code

    def set_rotating_frame(self, rotating_frame=True):
        """

        @param rotating_frame:
        @return:
        """
        self.model().set_rotating_frame(rotating_frame)
        return

    def rowCount(self):
        return self.model().rowCount()

    def columnCount(self):
        return self.model().columnCount()

    def currentRow(self):
        index = self.currentIndex()
        if index.isValid():
            return index.row()
        else:
            return 0

    def currentColumn(self):
        index = self.currentIndex()
        if index.isValid():
            return index.column()
        else:
            return 0

    def add_steps(self, count=1, at_position=None):
        """

        @param count:
        @param at_position:
        @return: bool, operation success
        """
        # Sanity checking
        if count < 1:
            return False

        # Insert new sequence step(s) as row to the table model/view at the specified position.
        # Append new sequence step(s) to the table model/view if no position was given.
        if at_position is None:
            at_position = self.model().rowCount()
        return self.model().insertRows(at_position, count)

    def remove_steps(self, count=1, at_position=None):
        """

        @param count:
        @param at_position:
        @return: bool, operation success
        """
        # Sanity checking
        if count < 1:
            return False

        # Remove rows/sequence steps with index <at_position> to index <at_position + count - 1>
        # Remove last <count> number of sequence steps if no at_position was given.
        if at_position is None:
            at_position = self.model().rowCount() - count
        return self.model().removeRows(at_position, count)

    def clear(self):
        """
        Removes all sequence steps from the view/model and inserts a single one afterwards.

        @return: bool, operation success
        """
        success = self.remove_steps(self.model().rowCount(), 0)
        if not success:
            return False
        self.add_steps(1, 0)
        return True

    def get_sequence(self):
        """
        Returns a (deep)copy of the PulseSequence instance serving as model for this editor.

        @return: object, an instance of PulseSequence
        """
        data_container = self.model().data(QtCore.QModelIndex(), self.model().sequenceRole)
        sequence_copy = copy.deepcopy(data_container)
        sequence_copy.name = ''
        return sequence_copy

    def load_sequence(self, pulse_sequence):
        """
        Load an instance of PulseSequence into the model in order to view/edit it.

        @param pulse_sequence: object, the PulseSequence instance to load into the model/view
        @return: bool, operation success
        """
        if not isinstance(pulse_sequence, PulseSequence):
            return False
        sequence_copy = copy.deepcopy(pulse_sequence)
        sequence_copy.name = 'EDITOR CONTAINER'
        return self.model().set_pulse_sequence(sequence_copy)
