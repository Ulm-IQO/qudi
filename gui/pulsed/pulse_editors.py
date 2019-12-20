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

from core.util.helpers import natural_sort
from qtpy import QtCore, QtGui, QtWidgets
from gui.pulsed.pulsed_item_delegates import ScienDSpinBoxItemDelegate, ComboBoxItemDelegate
from gui.pulsed.pulsed_item_delegates import MultipleCheckboxItemDelegate, CheckBoxItemDelegate
from gui.pulsed.pulsed_item_delegates import SpinBoxItemDelegate, AnalogParametersItemDelegate
from logic.pulsed.pulse_objects import PulseBlockElement, PulseBlock, PulseBlockEnsemble
from logic.pulsed.pulse_objects import PulseSequence
from logic.pulsed.sampling_functions import SamplingFunctions


class BlockEditorTableModel(QtCore.QAbstractTableModel):
    """

    """
    # signals
    sigColumnWidthChanged = QtCore.Signal(int, int)

    # User defined roles for model data access
    lengthRole = QtCore.Qt.UserRole + 1
    incrementRole = QtCore.Qt.UserRole + 2
    laserRole = QtCore.Qt.UserRole + 3
    digitalStateRole = QtCore.Qt.UserRole + 4
    analogFunctionRole = QtCore.Qt.UserRole + 5
    analogShapeRole = QtCore.Qt.UserRole + 6
    analogParameterRole = QtCore.Qt.UserRole + 7
    analogChannelSetRole = QtCore.Qt.UserRole + 8
    digitalChannelSetRole = QtCore.Qt.UserRole + 9
    channelSetRole = QtCore.Qt.UserRole + 10
    blockElementRole = QtCore.Qt.UserRole + 11
    pulseBlockRole = QtCore.Qt.UserRole + 12

    def __init__(self):
        super().__init__()

        self.digital_channels = list()
        self.analog_channels = list()
        self.activation_config = set()

        # The actual model data container.
        self._pulse_block = PulseBlock('EDITOR CONTAINER')
        # The default PulseBlockElement
        self.__default_element = PulseBlockElement()

        self._laser_channel_is_digital = True

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
        self._h_header_data = ['length\nin s', 'increment\nin s', 'laser\nchannel']
        if self.digital_channels:
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
            if 0 <= column < len(self._col_widths):
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
            elif column == 2:
                if not self._laser_channel_is_digital:
                    width = 50
                else:
                    width = 0
            elif column == 3 and has_digital:
                width = 30 * len(self.digital_channels)
            else:
                a_ch_offset = 3 + int(has_digital)
                if (column - a_ch_offset) % 2 == 0:
                    width = 80
                else:
                    channel = self.analog_channels[(column - a_ch_offset) // 2]
                    max_param_number = 0
                    for element in self._pulse_block:
                        tmp_size = len(element.pulse_function[channel].params)
                        if tmp_size > max_param_number:
                            max_param_number = tmp_size
                    width = 90 * max_param_number

            return width
        else:
            return -1

    def set_laser_channel_is_digital(self, laser_channel_is_digital):
        self._laser_channel_is_digital = bool(laser_channel_is_digital)

        # The fact that the widths are stored in the model saves a huge amount of computational
        # time when resizing columns due to item changes.
        self._col_widths = self._get_column_widths()
        # Notify the QTableView about a change in column widths
        self._notify_column_width()

        return self._laser_channel_is_digital

    def set_activation_config(self, activation_config):
        """

        @param activation_config:
        @return:
        """
        if isinstance(activation_config, list):
            activation_config = set(activation_config)

        # Do nothing if the activation config has not changed or is wrong data type
        if not isinstance(activation_config, set) or activation_config == self.activation_config:
            return

        self.beginResetModel()

        self.activation_config = activation_config
        self.digital_channels = natural_sort(
            (chnl for chnl in activation_config if chnl.startswith('d')))
        self.analog_channels = natural_sort(
            (chnl for chnl in activation_config if chnl.startswith('a')))

        analog_shape = {chnl: SamplingFunctions.Idle() for chnl in self.analog_channels}
        digital_state = {chnl: False for chnl in self.digital_channels}
        self.__default_element = PulseBlockElement(pulse_function=analog_shape,
                                                   digital_high=digital_state)

        # The actual model data container with a single default element
        self._pulse_block = PulseBlock(name='EDITOR CONTAINER',
                                       element_list=[self.__default_element])

        self._col_widths = self._get_column_widths()
        self._create_header_data()

        self.endResetModel()

        self._notify_column_width()
        return

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._pulse_block)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 3 + int(len(self.digital_channels) > 0) + 2 * len(self.analog_channels)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            return None

        if role == self.pulseBlockRole:
            self._pulse_block.refresh_parameters()
            return self._pulse_block
        if role == self.analogChannelSetRole:
            return self._pulse_block.analog_channels
        if role == self.digitalChannelSetRole:
            return self._pulse_block.digital_channels
        if role == self.channelSetRole:
            return self._pulse_block.channel_set

        if not index.isValid():
            return None

        if role == self.lengthRole:
            return self._pulse_block[index.row()].init_length_s
        if role == self.incrementRole:
            return self._pulse_block[index.row()].increment_s
        if role == self.laserRole:
            return self._pulse_block[index.row()].laser_on
        if role == self.digitalStateRole:
            data = self._pulse_block[index.row()].digital_high
            data = {chnl.split('d_ch', 1)[1]: value for chnl, value in data.items()}
            return data
        if role == self.analogFunctionRole:
            element = self._pulse_block[index.row()]
            if len(self.digital_channels) > 0:
                col_offset = 4
            else:
                col_offset = 3
            analog_chnl = self.analog_channels[(index.column() - col_offset) // 2]
            return element.pulse_function[analog_chnl]
        if role == self.analogShapeRole:
            element = self._pulse_block[index.row()]
            if len(self.digital_channels) > 0:
                col_offset = 4
            else:
                col_offset = 3
            analog_chnl = self.analog_channels[(index.column() - col_offset) // 2]
            return element.pulse_function[analog_chnl].__class__.__name__
        if role == self.analogParameterRole:
            element = self._pulse_block[index.row()]
            if len(self.digital_channels) > 0:
                col_offset = 4
            else:
                col_offset = 3
            analog_chnl = self.analog_channels[(index.column() - col_offset) // 2]
            return vars(element.pulse_function[analog_chnl])
        if role == self.blockElementRole:
            return self._pulse_block[index.row()]

        return None

    def setData(self, index, data, role=QtCore.Qt.DisplayRole):
        """
        """
        if isinstance(data, PulseBlockElement):
            self._pulse_block[index.row()] = copy.deepcopy(data)
            return

        if role == self.lengthRole and isinstance(data, (int, float)):
            old_elem = self._pulse_block[index.row()]
            if data != old_elem.init_length_s:
                new_elem = PulseBlockElement(init_length_s=max(0, data),
                                             increment_s=old_elem.increment_s,
                                             pulse_function=old_elem.pulse_function,
                                             digital_high=old_elem.digital_high,
                                             laser_on=old_elem.laser_on)
                self._pulse_block[index.row()] = new_elem
        elif role == self.incrementRole and isinstance(data, (int, float)):
            old_elem = self._pulse_block[index.row()]
            if data != old_elem.increment_s:
                new_elem = PulseBlockElement(init_length_s=old_elem.init_length_s,
                                             increment_s=data,
                                             pulse_function=old_elem.pulse_function,
                                             digital_high=old_elem.digital_high,
                                             laser_on=old_elem.laser_on)
                self._pulse_block[index.row()] = new_elem
        elif role == self.laserRole and isinstance(data, bool):
            old_elem = self._pulse_block[index.row()]
            if data != old_elem.laser_on:
                new_elem = PulseBlockElement(init_length_s=old_elem.init_length_s,
                                             increment_s=old_elem.increment_s,
                                             pulse_function=old_elem.pulse_function,
                                             digital_high=old_elem.digital_high,
                                             laser_on=data)
                self._pulse_block[index.row()] = new_elem
        elif role == self.digitalStateRole and isinstance(data, dict):
            data = {'d_ch' + chnl: value for chnl, value in data.items()}
            old_elem = self._pulse_block[index.row()]
            if data != old_elem.digital_high:
                new_elem = PulseBlockElement(init_length_s=old_elem.init_length_s,
                                             increment_s=old_elem.increment_s,
                                             pulse_function=old_elem.pulse_function,
                                             digital_high=data.copy(),
                                             laser_on=old_elem.laser_on)
                self._pulse_block[index.row()] = new_elem
        elif role == self.analogShapeRole and isinstance(data, str):
            if self.data(index=index, role=self.analogShapeRole) != data:
                old_elem = self._pulse_block[index.row()]

                sampling_func = getattr(SamplingFunctions, data)
                col_offset = 4 if self.digital_channels else 3
                chnl = self.analog_channels[(index.column() - col_offset) // 2]

                pulse_function = old_elem.pulse_function.copy()
                pulse_function[chnl] = sampling_func()

                new_elem = PulseBlockElement(init_length_s=old_elem.init_length_s,
                                             increment_s=old_elem.increment_s,
                                             pulse_function=pulse_function,
                                             digital_high=old_elem.digital_high,
                                             laser_on=old_elem.laser_on)
                self._pulse_block[index.row()] = new_elem

                new_column_width = self._get_column_width(index.column()+1)
                if new_column_width >= 0 and new_column_width != self._col_widths[index.column()+1]:
                    self._col_widths[index.column() + 1] = new_column_width
                    self._notify_column_width(index.column()+1)

        elif role == self.analogParameterRole and isinstance(data, dict):
            col_offset = 4 if self.digital_channels else 3
            chnl = self.analog_channels[(index.column() - col_offset) // 2]
            self._pulse_block[index.row()].pulse_function[chnl].__init__(**data)
        elif role == self.pulseBlockRole and isinstance(data, PulseBlock):
            self._pulse_block = copy.deepcopy(data)
            self._pulse_block.name = 'EDITOR CONTAINER'
            self._pulse_block.refresh_parameters()
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

        for i in range(count):
            self._pulse_block.insert(position=row, element=self.__default_element)

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

        del self._pulse_block[row:row + count]

        self._col_widths = self._get_column_widths()
        self._notify_column_width()

        self.endRemoveRows()
        return True

    def set_pulse_block(self, pulse_block):
        """

        @param pulse_block:
        @return:
        """
        if not isinstance(pulse_block, PulseBlock):
            return False
        elif pulse_block.channel_set != self.activation_config:
            return False
        self.beginResetModel()
        self.setData(QtCore.QModelIndex(), pulse_block, self.pulseBlockRole)
        self._col_widths = self._get_column_widths()
        self._notify_column_width()
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
        length_item_dict = {'unit': 's',
                            'init_val': '10.0e-9',
                            'min': 0,
                            'max': np.inf,
                            'dec': 6}
        self.setItemDelegateForColumn(
            0, ScienDSpinBoxItemDelegate(self, length_item_dict, self.model().lengthRole))
        increment_item_dict = {'unit': 's',
                               'init_val': 0,
                               'min': -np.inf,
                               'max': np.inf,
                               'dec': 6}
        self.setItemDelegateForColumn(
            1, ScienDSpinBoxItemDelegate(self, increment_item_dict, self.model().incrementRole))

        self.setItemDelegateForColumn(
            2, CheckBoxItemDelegate(self, self.model().laserRole))

        # If any digital channels are present, set item delegate (custom multi-CheckBox widget)
        # for digital channels column.
        if len(self.model().digital_channels) > 0:
            chnl_labels = natural_sort(chnl.split('d_ch')[1] for chnl in self.model().digital_channels)
            self.setItemDelegateForColumn(
                3, MultipleCheckboxItemDelegate(self, chnl_labels, self.model().digitalStateRole))
            offset_index = 4  # to indicate which column comes next.
        else:
            offset_index = 3  # to indicate which column comes next.

        # loop through all analog channels and set two item delegates for each channel.
        # First a ComboBox delegate for the analog shape column and second a custom
        # composite widget widget for the analog parameters column.
        for num, chnl in enumerate(self.model().analog_channels):
            self.setItemDelegateForColumn(
                offset_index + 2 * num, ComboBoxItemDelegate(
                    self, natural_sort(SamplingFunctions.parameters), self.model().analogShapeRole))
            self.setItemDelegateForColumn(
                offset_index + 2 * num + 1,
                AnalogParametersItemDelegate(
                    self, [self.model().analogFunctionRole, self.model().analogParameterRole]))
        return

    def set_laser_channel_is_digital(self, laser_channel_is_digital):
        return self.model().set_laser_channel_is_digital(laser_channel_is_digital)

    def set_activation_config(self, activation_config):
        """

        @param activation_config:
        @return:
        """
        # Remove item delegates
        for column in range(self.model().columnCount()):
            self.setItemDelegateForColumn(column, None)
        # Set new activation config in model (perform model reset)
        self.model().set_activation_config(activation_config)
        # Set new item delegates
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
        if success:
            self.add_elements(1, 0)
        return success

    def get_block(self):
        """
        Returns a (deep)copy of the PulseBlock instance serving as model for this editor.

        @return: PulseBlock, an instance of PulseBlock
        """
        block_copy = copy.deepcopy(
            self.model().data(QtCore.QModelIndex(), self.model().pulseBlockRole))
        block_copy.name = ''
        block_copy.refresh_parameters()
        return block_copy

    def load_block(self, pulse_block):
        """
        Load an instance of PulseBlock into the model in order to view/edit it.

        @param pulse_block: PulseBlock, the PulseBlock instance to load into the model/view
        @return: bool, operation success
        """
        return self.model().set_pulse_block(pulse_block)


class EnsembleEditorTableModel(QtCore.QAbstractTableModel):
    """

    """
    # User defined roles for model data access
    repetitionsRole = QtCore.Qt.UserRole + 1
    blockNameRole = QtCore.Qt.UserRole + 2
    blockEnsembleRole = QtCore.Qt.UserRole + 3
    blockElementRole = QtCore.Qt.UserRole + 4

    def __init__(self):
        super().__init__()

        # set containing available block names
        self.available_pulse_blocks = None

        # The actual model data container.
        self._block_ensemble = PulseBlockEnsemble('EDITOR CONTAINER')
        # The default block name
        self.__default_block = ''
        return

    def set_available_pulse_blocks(self, blocks):
        """

        @param blocks: list|dict|set, list/dict/set containing all available PulseBlock names
        @return: int, error code (>=0: OK, <0: ERR)
        """
        # Convert to set
        if isinstance(blocks, (list, dict)):
            blocks = set(blocks)
        elif not isinstance(blocks, set):
            return -1

        # Do nothing if available blocks are unchanged
        if self.available_pulse_blocks == blocks:
            return 0

        self.available_pulse_blocks = blocks

        # Set default block
        if len(self.available_pulse_blocks) > 0:
            self.__default_block = natural_sort(self.available_pulse_blocks)[0]
        else:
            self.__default_block = ''

        # Remove blocks from list that are not there anymore
        for row, (block_name, reps) in enumerate(self._block_ensemble):
            if block_name not in blocks:
                self.removeRows(row, 1)

        # Check if the PulseBlockEnsemble model instance is empty and set a single block if True.
        if self.rowCount() == 0:
            self.insertRows(0, 1)

        return 0

    def set_rotating_frame(self, rotating_frame=True):
        """

        @param rotating_frame:
        @return:
        """
        if isinstance(rotating_frame, bool):
            self._block_ensemble.rotating_frame = rotating_frame
        return

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._block_ensemble)

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
            return self._block_ensemble[index.row()][1]
        if role == self.blockNameRole:
            return self._block_ensemble[index.row()][0]
        if role == self.blockElementRole:
            return self._block_ensemble[index.row()]
        return None

    def setData(self, index, data, role=QtCore.Qt.DisplayRole):
        """
        """
        if role == self.repetitionsRole and isinstance(data, int):
            block_name = self._block_ensemble[index.row()][0]
            self._block_ensemble[index.row()] = (block_name, data)
        elif role == self.blockNameRole and isinstance(data, str):
            reps = self._block_ensemble[index.row()][1]
            self._block_ensemble[index.row()] = (data, reps)
        elif role == self.blockElementRole and isinstance(data, tuple):
            self._block_ensemble[index.row()] = data
        elif role == self.blockEnsembleRole and isinstance(data, PulseBlockEnsemble):
            self._block_ensemble = copy.deepcopy(data)
            self._block_ensemble.name = 'EDITOR CONTAINER'
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
        # Do nothing if no blocks are available
        if len(self.available_pulse_blocks) == 0:
            return False

        # Sanity/range checking
        if row < 0 or row > self.rowCount() or not self.available_pulse_blocks:
            return False

        if parent is None:
            parent = QtCore.QModelIndex()

        self.beginInsertRows(parent, row, row + count - 1)

        for i in range(count):
            self._block_ensemble.insert(position=row, element=(self.__default_block, 0))

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

        del self._block_ensemble[row:row + count]

        self.endRemoveRows()
        return True

    def set_block_ensemble(self, block_ensemble):
        """

        @param block_ensemble:
        @return:
        """
        if not isinstance(block_ensemble, PulseBlockEnsemble):
            return False
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

        # Set item selection and editing behaviour
        self.setEditTriggers(
            QtGui.QAbstractItemView.CurrentChanged | QtGui.QAbstractItemView.SelectedClicked)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)

        # Set item delegate (ComboBox) for PulseBlock column
        self.setItemDelegateForColumn(0, ComboBoxItemDelegate(self, list(),
                                                              self.model().blockNameRole,
                                                              QtCore.QSize(100, 50)))
        # Set item delegate (SpinBoxes) for repetition column
        repetition_item_dict = {'init_val': 0, 'min': 0, 'max': (2**31)-1}
        self.setItemDelegateForColumn(1, SpinBoxItemDelegate(self, repetition_item_dict,
                                                             self.model().repetitionsRole))

        # Set header sizes
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        # self.horizontalHeader().setDefaultSectionSize(100)
        # self.horizontalHeader().setStyleSheet('QHeaderView { font-weight: 400; }')
        self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.verticalHeader().setDefaultSectionSize(50)
        for col in range(self.columnCount()):
            width = self.itemDelegateForColumn(col).sizeHint().width()
            self.setColumnWidth(col, width)
        self.setColumnWidth(0, 400)
        return

    def set_available_pulse_blocks(self, blocks):
        """

        @param list|set blocks:
        @return: int, error code (>=0: OK, <0: ERR)
        """
        if isinstance(blocks, (list, dict, set)):
            blocks = natural_sort(blocks)
        else:
            return -1

        err_code = self.model().set_available_pulse_blocks(blocks)
        self.setItemDelegateForColumn(
            0,
            ComboBoxItemDelegate(self, blocks, self.model().blockNameRole))
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
        return index.row() if index.isValid() else 0

    def currentColumn(self):
        index = self.currentIndex()
        return index.column() if index.isValid() else 0

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
        self.add_blocks(1, 0)
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
        return self.model().set_block_ensemble(block_ensemble)


class SequenceEditorTableModel(QtCore.QAbstractTableModel):
    """

    """
    # User defined roles for model data access
    repetitionsRole = QtCore.Qt.UserRole + 1
    ensembleNameRole = QtCore.Qt.UserRole + 2
    goToRole = QtCore.Qt.UserRole + 4
    eventJumpToRole = QtCore.Qt.UserRole + 5
    eventTriggerRole = QtCore.Qt.UserRole + 6
    waitForRole = QtCore.Qt.UserRole + 7
    flagTriggerRole = QtCore.Qt.UserRole + 8
    flagHighRole = QtCore.Qt.UserRole + 9
    sequenceRole = QtCore.Qt.UserRole + 10

    def __init__(self):
        super().__init__()

        # set containing available ensemble names
        self.available_block_ensembles = set()
        # set containing available flag names
        self.available_flags = set()

        # The actual model data container.
        self._pulse_sequence = PulseSequence('EDITOR CONTAINER')
        # The default ensemble name for sequence steps
        self.__default_ensemble = ''
        # The headers for each column
        self.__horizontal_headers = ['BlockEnsemble',
                                     'Repetitions',
                                     'Go To',
                                     'Event Jump To',
                                     'Event Trigger',
                                     'Wait For',
                                     'Flag Trigger',
                                     'Flag High']
        return

    def set_available_block_ensembles(self, ensembles):
        """

        @param ensembles: list|set, list/set containing all available PulseBlockEnsemble names
        @return: int, error code (>=0: OK, <0: ERR)
        """
        # Convert to set
        if isinstance(ensembles, (list, dict)):
            ensembles = set(ensembles)
        elif not isinstance(ensembles, set):
            return -1

        # Do nothing if available ensembles have not changed
        if self.available_block_ensembles == ensembles:
            return 0

        self.available_block_ensembles = ensembles

        # Set default ensemble name
        if len(self.available_block_ensembles) > 0:
            self.__default_ensemble = natural_sort(self.available_block_ensembles)[0]
        else:
            self.__default_ensemble = ''

        # Remove ensembles from list that are not there anymore
        rows_to_remove = list()
        for row, seq_step in enumerate(self._pulse_sequence):
            if seq_step.ensemble not in ensembles:
                rows_to_remove.append(row)
        for row in reversed(rows_to_remove):
            self.removeRows(row, 1)

        # Check if the PulseSequence model instance is empty and set a single ensemble if True.
        if len(self._pulse_sequence) == 0:
            self.insertRows(0, 1)

        return 0

    def set_available_flags(self, flags):
        """

        @param flags: list|set, list/set containing all available flag names
        @return: int, error code (>=0: OK, <0: ERR)
        """
        # Convert to set
        if isinstance(flags, (list, dict)):
            flags = set(flags)
        elif not isinstance(flags, set):
            return -1

        # Do nothing if available flags have not changed
        if self.available_flags == flags:
            return 0

        # save new set of flags but temporarily remember flags that have been removed/added
        removed_flags = self.available_flags - flags
        self.available_flags = flags

        # Remove flags from sequence steps that are not there anymore
        for row, seq_step in enumerate(self._pulse_sequence):
            # remove old flags
            for flag in removed_flags:
                if flag in seq_step.flag_trigger:
                    seq_step.flag_trigger.remove(flag)
                if flag in seq_step.flag_high:
                    seq_step.flag_high.remove(flag)
        return 0

    def set_rotating_frame(self, rotating_frame=True):
        """

        @param rotating_frame:
        @return:
        """
        if isinstance(rotating_frame, bool):
            self._pulse_sequence.rotating_frame = rotating_frame
        return

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._pulse_sequence)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.__horizontal_headers)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            return None

        if role == self.sequenceRole:
            return self._pulse_sequence

        if not index.isValid():
            return None

        if role == self.repetitionsRole:
            return self._pulse_sequence[index.row()].repetitions
        elif role == self.ensembleNameRole:
            return self._pulse_sequence[index.row()].ensemble
        elif role == self.goToRole:
            return self._pulse_sequence[index.row()].go_to
        elif role == self.eventJumpToRole:
            return self._pulse_sequence[index.row()].event_jump_to
        elif role == self.eventTriggerRole:
            return self._pulse_sequence[index.row()].event_trigger
        elif role == self.waitForRole:
            return self._pulse_sequence[index.row()].wait_for
        elif role == self.flagTriggerRole:
            data = {flag: False for flag in self.available_flags}
            for flag in self._pulse_sequence[index.row()].flag_trigger:
                data[flag] = True
            return data
        elif role == self.flagHighRole:
            data = {flag: False for flag in self.available_flags}
            for flag in self._pulse_sequence[index.row()].flag_high:
                data[flag] = True
            return data
        else:
            return None

    def setData(self, index, data, role=QtCore.Qt.DisplayRole):
        """
        """
        if role == self.ensembleNameRole and isinstance(data, str):
            self._pulse_sequence[index.row()].ensemble = data
        elif role == self.repetitionsRole and isinstance(data, int):
            self._pulse_sequence[index.row()].repetitions = data
        elif role == self.goToRole and isinstance(data, int):
            self._pulse_sequence[index.row()].go_to = data
        elif role == self.eventJumpToRole and isinstance(data, int):
            self._pulse_sequence[index.row()].event_jump_to = data
        elif role == self.eventTriggerRole and isinstance(data, str):
            self._pulse_sequence[index.row()].event_trigger = data
        elif role == self.waitForRole and isinstance(data, str):
            self._pulse_sequence[index.row()].wait_for = data
        elif role == self.flagTriggerRole and isinstance(data, dict):
            list_data = [flag for flag, value in data.items() if value]
            self._pulse_sequence[index.row()].flag_trigger = list_data
        elif role == self.flagHighRole and isinstance(data, dict):
            list_data = [flag for flag, value in data.items() if value]
            self._pulse_sequence[index.row()].flag_high = list_data
        elif role == self.sequenceRole and isinstance(data, PulseSequence):
            self._pulse_sequence = PulseSequence('EDITOR CONTAINER')
            self._pulse_sequence.extend(data.ensemble_list)
        return

    def headerData(self, section, orientation, role):
        # Horizontal header
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole and (0 <= section < len(self.__horizontal_headers)):
                return self.__horizontal_headers[section]
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
        # Do nothing if no ensembles are available
        if len(self.available_block_ensembles) == 0:
            return False

        # Sanity/range checking
        if row < 0 or row > self.rowCount() or not self.available_block_ensembles:
            return False

        if parent is None:
            parent = QtCore.QModelIndex()

        self.beginInsertRows(parent, row, row + count - 1)

        for i in range(count):
            self._pulse_sequence.insert(position=row, element=self.__default_ensemble)

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

        del self._pulse_sequence[row:row + count]

        self.endRemoveRows()
        return True

    def set_pulse_sequence(self, pulse_sequence):
        """

        @param pulse_sequence:
        @return:
        """
        if not isinstance(pulse_sequence, PulseSequence):
            return False
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
        self.setItemDelegateForColumn(1, SpinBoxItemDelegate(self, {'init_val': 1, 'min': -1,
                                                                    'max': 2 ** 31 - 1},
                                                             self.model().repetitionsRole))
        # Set item delegate (SpinBoxes) for go_to column
        self.setItemDelegateForColumn(2, SpinBoxItemDelegate(self, {'init_val': -1, 'min': -1,
                                                                    'max': 2 ** 31 - 1},
                                                             self.model().goToRole))
        # Set item delegate (SpinBoxes) for event_jump_to column
        self.setItemDelegateForColumn(3, SpinBoxItemDelegate(self, {'init_val': -1, 'min': -1,
                                                                    'max': 2 ** 31 - 1},
                                                             self.model().eventJumpToRole))
        # Set item delegate (ComboBox) for event_trigger column
        self.setItemDelegateForColumn(4, ComboBoxItemDelegate(self, ['OFF'],
                                                              self.model().eventTriggerRole))
        # Set item delegate (ComboBox) for wait_for column
        self.setItemDelegateForColumn(5, ComboBoxItemDelegate(self, ['OFF'],
                                                              self.model().waitForRole))
        # Set item delegate (ComboBox) for flag_trigger column
        self.setItemDelegateForColumn(6, MultipleCheckboxItemDelegate(self, None, self.model().flagTriggerRole))
        # Set item delegate (ComboBox) for flag_high column
        self.setItemDelegateForColumn(7, MultipleCheckboxItemDelegate(self, None, self.model().flagHighRole))

        # Set header sizes
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        # self.horizontalHeader().setDefaultSectionSize(100)
        # self.horizontalHeader().setStyleSheet('QHeaderView { font-weight: 400; }')
        self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.verticalHeader().setDefaultSectionSize(50)

        # automatically set the width for the columns
        for col in range(self.columnCount()):
            width = self.itemDelegateForColumn(col).sizeHint().width()
            self.setColumnWidth(col, width)
        self.setColumnWidth(0, 400)
        return

    def set_available_block_ensembles(self, ensembles):
        """

        @param ensembles:
        @return: int, error code (>=0: OK, <0: ERR)
        """
        err_code = self.model().set_available_block_ensembles(ensembles)
        if err_code >= 0:
            delegate = ComboBoxItemDelegate(
                self, natural_sort(self.model().available_block_ensembles), self.model().ensembleNameRole)
            self.setItemDelegateForColumn(0, delegate)
        return err_code

    def set_rotating_frame(self, rotating_frame=True):
        """

        @param rotating_frame:
        @return:
        """
        self.model().set_rotating_frame(rotating_frame)
        return

    def set_available_triggers(self, trigger_list):
        """

        @param list trigger_list: List of strings describing the available pulse generator trigger
                                  input channels.
        """
        if not isinstance(trigger_list, list):
            return
        trigger_list.insert(0, 'OFF')
        # Set item delegate (ComboBox) for event_trigger column
        self.setItemDelegateForColumn(4, ComboBoxItemDelegate(self, trigger_list,
                                                              self.model().eventTriggerRole))
        # Set item delegate (ComboBox) for wait_for column
        self.setItemDelegateForColumn(5, ComboBoxItemDelegate(self, trigger_list,
                                                              self.model().waitForRole))
        return

    def set_available_flags(self, flag_set):
        """

        @param list flag_set: Set of strings describing the available pulse generator flag output channels.
        """
        if not isinstance(flag_set, set):
            return

        # Do nothing if available flags have not changed
        if self.model().available_flags == flag_set:
            return 0

        # Remove delegates
        self.setItemDelegateForColumn(6, None)
        self.setItemDelegateForColumn(7, None)

        # Set available flags in model
        self.model().set_available_flags(flag_set)

        # Set item delegate (FlagStates) for flagTrigger column
        self.setItemDelegateForColumn(6, MultipleCheckboxItemDelegate(self, sorted(flag_set),
                                                                      self.model().flagTriggerRole))
        # Set item delegate (FlagStates) for flagHigh column
        self.setItemDelegateForColumn(7, MultipleCheckboxItemDelegate(self, sorted(flag_set),
                                                                      self.model().flagHighRole))

        # Change column widths
        self.setColumnWidth(6, self.itemDelegateForColumn(6).sizeHint().width())
        self.setColumnWidth(7, self.itemDelegateForColumn(7).sizeHint().width())
        return

    def rowCount(self):
        return self.model().rowCount()

    def columnCount(self):
        return self.model().columnCount()

    def currentRow(self):
        index = self.currentIndex()
        return index.row() if index.isValid() else 0

    def currentColumn(self):
        index = self.currentIndex()
        return index.column() if index.isValid() else 0

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
        if success:
            self.add_steps(1, 0)
        return success

    def get_sequence(self):
        """
        Returns a (deep)copy of the PulseSequence instance serving as model for this editor.

        @return: object, an instance of PulseSequence
        """
        data_container = self.model().data(QtCore.QModelIndex(), self.model().sequenceRole)
        sequence_copy = PulseSequence('', ensemble_list=data_container.ensemble_list)
        return sequence_copy

    def load_sequence(self, pulse_sequence):
        """
        Load an instance of PulseSequence into the model in order to view/edit it.

        @param pulse_sequence: object, the PulseSequence instance to load into the model/view
        @return: bool, operation success
        """
        return self.model().set_pulse_sequence(pulse_sequence)
