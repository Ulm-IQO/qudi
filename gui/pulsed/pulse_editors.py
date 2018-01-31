from qtpy import QtCore
from qtpy import QtWidgets
import numpy as np
from collections import OrderedDict
import re

from logic.pulse_objects import PulseBlockElement
from logic.pulse_objects import PulseBlock
from logic.pulse_objects import PulseBlockEnsemble
from logic.pulse_objects import PulseSequence
from logic.sampling_functions import SamplingFunctions

from .spinbox_delegate import SpinBoxDelegate
from .scientificspinbox_delegate import ScienDSpinBoxDelegate
from .combobox_delegate import ComboBoxDelegate
from .checkbox_delegate import CheckBoxDelegate

import logging
logger = logging.getLogger(__name__)


class BlockEditor:
    """
    The QTableWidget has already an underlying model, where the data are saved.
    The view widgets are handeled by the delegates.

    Access to the view object:

    Each element (in the table) of a QTableWidget is called a QTableItemWidget,
    where the reference to each item can be obtained via

        item = be_widget.item(row, column)

    This is in general the view object, which will be seen on the editor. The
    kind of object can be changed by modifying the createEditor method of the
    delegate.
    To get the reference to the delegated (parent) object use
        c = be_widget.itemDelegate(index)

    Access to the model object:
    To access the model object, i.e. the object where the actual data is stored,
    a reference to the model needs to be obtained:

        model = be_widget.model()

    and the index object to the data, which holds the reference to get the data,
    will be obtained by selecting the proper row and column number (starting
    from 0):

        index = model.index(row, column)

    """
    def __init__(self, block_editor_widget):
        self.be_widget = block_editor_widget
        self.parameter_dict = OrderedDict()
        self.parameter_dict['length'] = {'unit': 's', 'init_val': 0.0, 'min': 0.0, 'max': np.inf,
                                         'view_stepsize': 1e-9, 'dec': 15, 'type': float}
        self.parameter_dict['increment'] = {'unit': 's', 'init_val': 0.0, 'min': -np.inf,
                                            'max': np.inf, 'view_stepsize': 1e-9, 'dec': 15,
                                            'type': float}
        self.parameter_dict['use as tick?'] = {'unit': '', 'init_val': 0, 'min': 0, 'max': 1,
                                               'view_stepsize': 1, 'dec': 0, 'type': bool}
        self.activation_config = None
        self.function_config = SamplingFunctions().func_config
        self._cfg_param_pbe = None

        # this behaviour should be customized for the combobox, since you need
        # 3 clicks in the default settings to open it.
        # self.be_widget.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)

        return

    def initialize_cells(self, start_row, stop_row=None, start_col=None, stop_col=None):
        """ Initialize the desired cells in the block editor table.

        @param start_row: int, index of the row, where the initialization
                          should start
        @param stop_row: int, optional, index of the row, where the
                         initalization should end.
        @param start_col: int, optional, index of the column where the
                          initialization should start
        @param stop_col: int, optional, index of the column, where the
                         initalization should end.

        With this function it is possible to reinitialize specific elements or
        part of a row or even the whole row. If start_row is set to 0 the whole
        row is going to be initialzed to the default value.
        """
        if stop_row is None:
            stop_row = start_row + 1
        if start_col is None:
            start_col = 0
        if stop_col is None:
            stop_col = self.be_widget.columnCount()
        for col_num in range(start_col, stop_col):
            for row_num in range(start_row, stop_row):
                # get the model, here are the data stored:
                model = self.be_widget.model()
                # get the corresponding index of the current element:
                index = model.index(row_num, col_num)
                # get the initial values of the delegate class which was uses for this column:
                ini_values = self.be_widget.itemDelegateForColumn(col_num).get_initial_value()
                # set initial values:
                model.setData(index, ini_values[0], ini_values[1])
        return

    def _get_list(self):
        return list(self.function_config)

    def _set_columns(self):
        self.be_widget.blockSignals(True)
        # Determine the function with the most parameters. Use also that function as a construction plan to create all
        # the needed columns for the parameters.
        num_max_param = 0
        for func in self.function_config:
            if num_max_param < len(self.function_config[func]):
                num_max_param = len(self.function_config[func])
                biggest_func = func

        # Erase the delegate from the column, pass a None reference:
        for column in range(self.be_widget.columnCount()):
            self.be_widget.setItemDelegateForColumn(column, None)
        # clear the number of columns:
        self.be_widget.setColumnCount(0)
        # total number of analog and digital channels:
        num_of_columns = 0
        for channel in self.activation_config:
            if 'd_ch' in channel:
                num_of_columns += 1
            elif 'a_ch' in channel:
                num_of_columns += num_max_param + 1
        self.be_widget.setColumnCount(num_of_columns)

        column_count = 0
        for channel in self.activation_config:
            if 'a_ch' in channel:
                self.be_widget.setHorizontalHeaderItem(column_count, QtWidgets.QTableWidgetItem())
                self.be_widget.horizontalHeaderItem(column_count).setText('ACh{0}\nfunction'
                                                                          ''.format(channel.split('ch')[-1]))
                self.be_widget.setColumnWidth(column_count, 70)

                item_dict = {'get_list_method': self._get_list}
                delegate = ComboBoxDelegate(self.be_widget, item_dict)
                self.be_widget.setItemDelegateForColumn(column_count, delegate)

                column_count += 1
                # fill here all parameter columns for the current analogue channel
                for parameter in self.function_config[biggest_func]:
                    # initial block:
                    item_dict = self.function_config[biggest_func][parameter]
                    self.be_widget.setHorizontalHeaderItem(column_count, QtWidgets.QTableWidgetItem())
                    self.be_widget.horizontalHeaderItem(column_count).setText('ACh{0}\n{1} ({2})'
                                                                              ''.format(channel.split('ch')[-1],
                                                                                        parameter, item_dict['unit']))
                    self.be_widget.setColumnWidth(column_count, 100)

                    # extract the classname from the _param_a_ch list to be able to delegate:
                    delegate = ScienDSpinBoxDelegate(self.be_widget, item_dict)
                    self.be_widget.setItemDelegateForColumn(column_count, delegate)
                    column_count += 1

            elif 'd_ch' in channel:
                self.be_widget.setHorizontalHeaderItem(column_count, QtWidgets.QTableWidgetItem())
                self.be_widget.horizontalHeaderItem(column_count).setText('DCh{0}'.format(channel.split('ch')[-1]))
                self.be_widget.setColumnWidth(column_count, 40)

                # itemlist for checkbox
                item_dict = {'init_val': QtCore.Qt.Unchecked}
                checkDelegate = CheckBoxDelegate(self.be_widget, item_dict)
                self.be_widget.setItemDelegateForColumn(column_count, checkDelegate)

                column_count += 1

        # Insert the additional parameters (length etc.)

        for column, parameter in enumerate(self.parameter_dict):
            # add the new properties to the whole column through delegate:
            item_dict = self.parameter_dict[parameter]

            self.be_widget.insertColumn(num_of_columns + column)
            self.be_widget.setHorizontalHeaderItem(num_of_columns + column, QtWidgets.QTableWidgetItem())
            self.be_widget.horizontalHeaderItem(num_of_columns + column).setText('{0} ({1})'.format(parameter,
                                                                                                    item_dict['unit']))
            self.be_widget.setColumnWidth(num_of_columns + column, 90)

            # Use only DoubleSpinBox as delegate:
            if item_dict['type'] is bool:
                delegate = CheckBoxDelegate(self.be_widget, item_dict)
            else:
                delegate = ScienDSpinBoxDelegate(self.be_widget, item_dict)
            self.be_widget.setItemDelegateForColumn(num_of_columns + column, delegate)

            # initialize the whole row with default values:
            for row_num in range(self.be_widget.rowCount()):
                # get the model, here are the data stored:
                model = self.be_widget.model()
                # get the corresponding index of the current element:
                index = model.index(row_num, num_of_columns + column)
                # get the initial values of the delegate class which was uses for this column:
                ini_values = delegate.get_initial_value()
                # set initial values:
                model.setData(index, ini_values[0], ini_values[1])

        self.initialize_cells(0, self.be_widget.rowCount())
        self._set_cfg_param()
        self.be_widget.blockSignals(False)
        return

    def _set_cfg_param(self):
        """ Set the parameter configuration of the Pulse_Block according to the
        current table configuration and updates the dict.
        """
        cfg_param_pbe = OrderedDict()
        for column in range(self.be_widget.columnCount()):
            text = self.be_widget.horizontalHeaderItem(column).text()
            split_text = text.split()
            if 'DCh' in split_text[0]:
                cfg_param_pbe['digital_' + split_text[0][3]] = column
            elif 'ACh' in split_text[0]:
                cfg_param_pbe[split_text[1] + '_' + split_text[0][3]] = column
            else:
                cfg_param_pbe[split_text[0]] = column
        self._cfg_param_pbe = cfg_param_pbe
        return

    def _get_headernames(self):
        """ Get the names of the current header.

        @return: dict with keys being the header names and items being the column number
        """
        headers = OrderedDict()
        for column in range(self.be_widget.columnCount()):
            text = self.be_widget.horizontalHeaderItem(column).text()
            headers[text] = column
        return headers

    def set_displayed_analog_amplitude(self, ampl_dict):
        """ Update the maximal amplitudes of the current pulse block editor.

        @param dict ampl_dict:
        @return: list, with integers representing the column indices which have
                 changed
        """

        if ampl_dict == {}:
            return

        headers = self._get_headernames()
        columns_changes = []

        for amplitude in ampl_dict:
            chan_name = amplitude.replace('_','')
            found_cols = []
            for entry in headers:
                check = re.search('.*'+chan_name+'.*amplitude', entry, re.IGNORECASE | re.DOTALL)

                if check is not None:
                    found_cols.append(headers[entry])

            for col in found_cols:
                delegate = self.be_widget.itemDelegateForColumn(col)
                delegate.item_dict['max'] = ampl_dict[amplitude]/2.0

            columns_changes.extend(found_cols)


        return columns_changes


    def set_activation_config(self, activation_config):
        """

        @param activation_config:
        @return:
        """
        self.activation_config = activation_config
        self._set_columns()
        return

    def set_function_config(self, function_config):
        """

        @param function_config:
        @return:
        """
        self.function_config = function_config
        self._set_columns()
        return

    def clear_table(self):
        """ Delete all rows in the block editor table. """
        self.be_widget.blockSignals(True)
        self.be_widget.setRowCount(1)
        self.be_widget.clearContents()
        self.initialize_cells(start_row=0)
        self.be_widget.blockSignals(False)
        # FIXME: Implement a proper way to update the current block ensemble parameters
        return

    def delete_row(self, index):
        """ Delete row number 'index' """
        if self.be_widget.rowCount() == 1 and index == 0:
            return
        self.be_widget.blockSignals(True)
        self.be_widget.removeRow(index)
        self.be_widget.blockSignals(False)
        # FIXME: Implement a proper way to update the current block ensemble parameters
        return

    def insert_rows(self, index, number_to_add=1):
        """ Add 'number_to_add' rows after row number 'index' """
        self.be_widget.blockSignals(True)
        for i in range(number_to_add):
            self.be_widget.insertRow(index)
        self.initialize_cells(start_row=index, stop_row=index + number_to_add)
        self.be_widget.blockSignals(False)
        # FIXME: Implement a proper way to update the current block ensemble parameters
        return

    def set_element(self, row, column, value):
        """ Simplified wrapper function to set the data to a specific cell in the table.

        @param int row: row index
        @param int column: column index

        Note that the order of the arguments in this function (first row index
        and then column index) was taken from the Qt convention.
        A type check will be performed for the passed value argument. If the
        type does not correspond to the delegate, then the value will not be
        changed. You have to ensure that
        """
        model = self.be_widget.model()
        access = self.be_widget.itemDelegateForColumn(column).model_data_access
        data = model.index(row, column).data(access)
        if isinstance(data, float) and isinstance(value, float):
            model.setData(model.index(row, column), value, access)
            return value
        elif isinstance(data, int) and isinstance(value, int):
            model.setData(model.index(row, column), value, access)
            return value
        elif isinstance(data, bool) and isinstance(value, bool):
            model.setData(model.index(row, column), value, access)
            return value
        elif isinstance(data, str) and isinstance(value, str):
            model.setData(model.index(row, column), value, access)
            return value
        else:
            return data

    def get_element(self, row, column):
        """ Simplified wrapper function to get the data from a specific cell in the table.

        @param int row: row index
        @param int column: column index
        @return: the value of the corresponding cell, which can be a string, a
                 float or an integer. Remember that the checkbox state
                 unchecked corresponds to 0 and check to 2. That is Qt
                 convention.

        Note that the order of the arguments in this function (first row index
        and then column index) was taken from the Qt convention.
        """
        # Get from the corresponding delegate the data access model
        access = self.be_widget.itemDelegateForColumn(column).model_data_access
        data = self.be_widget.model().index(row, column).data(access)
        return data

    def get_column_delegate(self, column):
        """ Get the delegate object, which is responsible for the specific column

        @param int column: column index

        @return: QDelegate
        """
        return self.be_widget.itemDelegate(column)

    def load_pulse_block(self, block):
        """

        @param block:
        @return:
        """
        if block is None:
            return
        # seperate active analog and digital channels in lists
        active_analog = [chnl for chnl in self.activation_config if 'a_ch' in chnl]
        active_digital = [chnl for chnl in self.activation_config if 'd_ch' in chnl]

        # clear table
        self.clear_table()
        # get amout of rows needed for display
        rows = len(block.element_list)
        # since one is already present
        self.insert_rows(1, rows - 1)

        for row_index, elem in enumerate(block.element_list):
            # set at first all digital channels:
            for digital_ch in range(elem.digital_channels):
                column = self._cfg_param_pbe['digital_' + active_digital[digital_ch].split('ch')[-1]]
                value = elem.digital_high[digital_ch]
                if value:
                    value = 2
                else:
                    value = 0
                self.set_element(row_index, column, value)

            # now set all parameters for the analog channels:
            for analog_ch in range(elem.analog_channels):
                # the function text:
                column = self._cfg_param_pbe['function_' + active_analog[analog_ch].split('ch')[-1]]
                func_text = elem.pulse_function[analog_ch]
                self.set_element(row_index, column, func_text)
                # then the parameter dictionary:
                parameter_dict = elem.parameters[analog_ch]
                for parameter in parameter_dict:
                    column = self._cfg_param_pbe[parameter + '_' + active_analog[analog_ch].split('ch')[-1]]
                    value = np.float(parameter_dict[parameter])
                    self.set_element(row_index, column, value)

            # now set use as tick parameter:
            column = self._cfg_param_pbe['use']
            value = elem.use_as_tick
            # the ckeckbox has a special input value, it is 0, 1 or 2. (tri-state)
            if value:
                value = 2
            else:
                value = 0
            self.set_element(row_index, column, value)

            # and set the init_length:
            column = self._cfg_param_pbe['length']
            value = elem.init_length_s
            self.set_element(row_index, column, value)

            # and set the increment parameter
            column = self._cfg_param_pbe['increment']
            value = elem.increment_s
            self.set_element(row_index, column, value)
        return

    def generate_block_object(self, pb_name):
        """ Generates from an given table block_matrix a block_object.

        @param pb_name: string, Name of the created Pulse_Block Object
        """

        # list of all the pulse block element objects
        pbe_obj_list = [None] * self.be_widget.rowCount()

        # seperate digital and analogue channels
        analog_chnl_names = [chnl for chnl in self.activation_config if 'a_ch' in chnl]
        digital_chnl_names = [chnl for chnl in self.activation_config if 'd_ch' in chnl]

        for row_index in range(self.be_widget.rowCount()):
            # get length:
            init_length_s = self.get_element(row_index, self._cfg_param_pbe['length'])
            # get increment:
            increment_s = self.get_element(row_index, self._cfg_param_pbe['increment'])

            # get the proper pulse_functions and its parameters:
            pulse_function = [None] * len(analog_chnl_names)
            parameter_list = [None] * len(analog_chnl_names)
            for chnl_index, chnl in enumerate(analog_chnl_names):
                # get the number of the analogue channel according to the channel activation_config
                a_chnl_number = chnl.split('ch')[-1]
                pulse_function[chnl_index] = self.get_element(row_index, self._cfg_param_pbe['function_' + a_chnl_number])

                # search for this function in the dictionary and get all the parameter with their names in list:
                param_dict = self.function_config[pulse_function[chnl_index]]
                parameters = {}
                for entry in list(param_dict):
                    # Obtain how the value is displayed in the table:
                    param_value = self.get_element(row_index,
                                                   self._cfg_param_pbe[entry + '_' + a_chnl_number])
                    parameters[entry] = param_value
                parameter_list[chnl_index] = parameters

            digital_high = [None] * len(digital_chnl_names)
            for chnl_index, chnl in enumerate(digital_chnl_names):
                # get the number of the digital channel according to the channel activation_config
                d_chnl_number = chnl.split('ch')[-1]
                digital_high[chnl_index] = bool(self.get_element(row_index, self._cfg_param_pbe['digital_' + d_chnl_number]))

            use_as_tick = bool(self.get_element(row_index, self._cfg_param_pbe['use']))

            # create here actually the object with all the obtained information:
            pbe_obj_list[row_index] = PulseBlockElement(init_length_s=init_length_s,
                                                          increment_s=increment_s,
                                                          pulse_function=pulse_function,
                                                          digital_high=digital_high,
                                                          parameters=parameter_list,
                                                          use_as_tick=use_as_tick)
        pb_obj = PulseBlock(pb_name, pbe_obj_list)
        return pb_obj


class BlockOrganizer:
    def __init__(self, block_organizer_widget):
        self.bo_widget = block_organizer_widget
        self.parameter_dict = OrderedDict()
        self.parameter_dict['repetitions'] = {'unit': '#', 'init_val': 0, 'min': 0,
                                              'max': (2 ** 31 - 1), 'view_stepsize': 1, 'dec': 0,
                                              'type': int}
        self._cfg_param_pb = None
        self.block_dict = None

        self.bo_widget.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)
        return

    def set_block_dict(self, block_dict):
        if self.block_dict is None:
            self.block_dict = block_dict
            self._set_columns()
        else:
            self.block_dict = block_dict

        for row in range(self.bo_widget.rowCount()):
            data = self.get_element(row, 0)
            if data not in list(self.block_dict):
                self.initialize_cells(start_row=row, stop_row=row+1, start_col=0, stop_col=1)
        return

    def _get_list(self):
        return list(self.block_dict)

    def initialize_cells(self, start_row, stop_row=None, start_col=None, stop_col=None):
        """ Initialize the desired cells in the block organizer table.

        @param start_row: int, index of the row, where the initialization
                          should start
        @param stop_row: int, optional, index of the row, where the
                         initalization should end.
        @param start_col: int, optional, index of the column where the
                          initialization should start
        @param stop_col: int, optional, index of the column, where the
                         initalization should end.

        With this function it is possible to reinitialize specific elements or
        part of a row or even the whole row. If start_row is set to 0 the whole
        row is going to be initialzed to the default value.
        """
        if stop_row is None:
            stop_row = start_row +1
        if start_col is None:
            start_col = 0
        if stop_col is None:
            stop_col = self.bo_widget.columnCount()
        for col_num in range(start_col, stop_col):
            for row_num in range(start_row,stop_row):
                # get the model, here are the data stored:
                model = self.bo_widget.model()
                # get the corresponding index of the current element:
                index = model.index(row_num, col_num)
                # get the initial values of the delegate class which was uses for this column:
                ini_values = self.bo_widget.itemDelegateForColumn(col_num).get_initial_value()
                # set initial values:
                model.setData(index, ini_values[0], ini_values[1])
        return

    def _set_columns(self):
        # Erase the delegate from the column, i.e. pass a None reference:
        for column in range(self.bo_widget.columnCount()):
            self.bo_widget.setItemDelegateForColumn(column, None)
        # clear the number of columns and set them to 1:
        self.bo_widget.setColumnCount(1)
        self.bo_widget.setHorizontalHeaderItem(0, QtWidgets.QTableWidgetItem())
        self.bo_widget.horizontalHeaderItem(0).setText('Pulse Block')
        self.bo_widget.setColumnWidth(0, 100)

        item_dict = {}
        item_dict['get_list_method'] = self._get_list
        comboDelegate = ComboBoxDelegate(self.bo_widget, item_dict)
        self.bo_widget.setItemDelegateForColumn(0, comboDelegate)

        for column, parameter in enumerate(self.parameter_dict):
            # add the new properties to the whole column through delegate:
            item_dict = self.parameter_dict[parameter]
            unit_text = item_dict['unit']
            self.bo_widget.insertColumn(1+column)
            self.bo_widget.setHorizontalHeaderItem(1+column, QtWidgets.QTableWidgetItem())
            self.bo_widget.horizontalHeaderItem(1+column).setText('{0} ({1})'.format(parameter,unit_text))
            self.bo_widget.setColumnWidth(1+column, 80)
            # Use only DoubleSpinBox as delegate:
            if item_dict['type'] is bool:
                delegate = CheckBoxDelegate(self.bo_widget, item_dict)
            elif item_dict['type'] is int:
                delegate = SpinBoxDelegate(self.bo_widget, item_dict)
            else:
                delegate = ScienDSpinBoxDelegate(self.bo_widget, item_dict)
            self.bo_widget.setItemDelegateForColumn(1+column, delegate)

        self.initialize_cells(start_row=0, stop_row=self.bo_widget.rowCount())
        self._set_cfg_param()
        # FIXME: Implement a proper way to update the current block ensemble parameters
        return

    def _set_cfg_param(self):
        """ Set the parameter configuration of the Pulse_Block according to the
        current table configuration and updates the dict.
        """
        cfg_param_pb = OrderedDict()
        for column in range(self.bo_widget.columnCount()):
            text = self.bo_widget.horizontalHeaderItem(column).text()
            if 'Pulse Block' in text:
                cfg_param_pb['pulse_block'] = column
            elif 'repetitions' in text:
                cfg_param_pb['repetitions'] = column
            else:
                print('text:', text)
                raise NotImplementedError
        self._cfg_param_pb = cfg_param_pb
        return

    def clear_table(self):
        """ Delete all rows in the block editor table. """
        self.bo_widget.blockSignals(True)
        self.bo_widget.setRowCount(1)
        self.bo_widget.clearContents()
        self.initialize_cells(start_row=0)
        self.bo_widget.blockSignals(False)
        # FIXME: Implement a proper way to update the current block ensemble parameters
        return

    def delete_row(self, index):
        """ Delete row number 'index' """
        if self.bo_widget.rowCount() == 1 and index == 0:
            return
        self.bo_widget.blockSignals(True)
        self.bo_widget.removeRow(index)
        self.bo_widget.blockSignals(False)
        # FIXME: Implement a proper way to update the current block ensemble parameters
        return

    def insert_rows(self, index, number_to_add=1):
        """ Add 'number_to_add' rows after row number 'index' """
        self.bo_widget.blockSignals(True)
        for i in range(number_to_add):
            self.bo_widget.insertRow(index)
        self.initialize_cells(start_row=index, stop_row=index + number_to_add)
        self.bo_widget.blockSignals(False)
        # FIXME: Implement a proper way to update the current block ensemble parameters
        return

    def set_element(self, row, column, value):
        """ Simplified wrapper function to set the data to a specific cell in the table.

        @param int row: row index
        @param int column: column index

        Note that the order of the arguments in this function (first row index and then column
        index) was taken from the Qt convention. A type check will be performed for the passed
        value argument. If the type does not correspond to the delegate, then the value will not be
        changed. You have to ensure that.
        """
        model = self.bo_widget.model()
        access = self.bo_widget.itemDelegateForColumn(column).model_data_access
        data = self.bo_widget.model().index(row, column).data(access)
        if isinstance(data, float) and isinstance(value, float):
            model.setData(model.index(row, column), value, access)
            return value
        elif isinstance(data, int) and isinstance(value, int):
            model.setData(model.index(row, column), value, access)
            return value
        elif isinstance(data, bool) and isinstance(value, bool):
            model.setData(model.index(row, column), value, access)
            return value
        elif isinstance(data, str) and isinstance(value, str):
            model.setData(model.index(row, column), value, access)
            return value
        else:
            return data

    def get_element(self, row, column):
        """ Simplified wrapper function to get the data from a specific cell in the table.

        @param int row: row index
        @param int column: column index
        @return: the value of the corresponding cell, which can be a string, a
                 float or an integer. Remember that the checkbox state
                 unchecked corresponds to 0 and check to 2. That is Qt
                 convention.

        Note that the order of the arguments in this function (first row index
        and then column index) was taken from the Qt convention.
        """
        # Get from the corresponding delegate the data access model
        access = self.bo_widget.itemDelegateForColumn(column).model_data_access
        data = self.bo_widget.model().index(row, column).data(access)
        return data

    def load_pulse_block_ensemble(self, ensemble):
        """

        @param ensemble:
        """
        # Sanity checks:
        if ensemble is None:
            return
        # clear the block organizer table
        self.clear_table()
        # get amout of rows needed for display
        rows = len(ensemble.block_list)
        # add as many rows as there are blocks in the ensemble minus 1 because a single row is
        # already present after clear
        self.insert_rows(1, rows - 1)
        # run through all blocks in the block_elements block_list to fill in the row informations
        for row_index, (pulse_block, repetitions) in enumerate(ensemble.block_list):
            column = self._cfg_param_pb['pulse_block']
            self.set_element(row_index, column, pulse_block.name)
            print(pulse_block.name)
            column = self._cfg_param_pb['repetitions']
            self.set_element(row_index, column, int(repetitions))
        return

    def generate_ensemble_object(self, ensemble_name, rotating_frame=True):
        """
        Generates from an given table ensemble_matrix a ensemble object.

        @param str ensemble_name: Name of the created PulseBlockEnsemble object
        @param bool rotating_frame: optional, whether the phase preservation is mentained
                                    throughout the sequence.
        """
        # list of all the pulse block element objects
        pb_obj_list = [None] * self.bo_widget.rowCount()

        for row_index in range(self.bo_widget.rowCount()):
            pulse_block_name = self.get_element(row_index, self._cfg_param_pb['pulse_block'])
            pulse_block_reps = self.get_element(row_index, self._cfg_param_pb['repetitions'])
            # Fetch previously saved block object
            block = self.block_dict[pulse_block_name]
            # Append block object along with repetitions to the block list
            pb_obj_list[row_index] = (block, pulse_block_reps)

        # Create the Pulse_Block_Ensemble object
        pulse_block_ensemble = PulseBlockEnsemble(name=ensemble_name, block_list=pb_obj_list,
                                                    rotating_frame=rotating_frame)
        return pulse_block_ensemble


class SequenceEditor:
    def __init__(self, sequence_editor_widget):
        self.se_widget = sequence_editor_widget
        self.parameter_dict = OrderedDict()
        self.parameter_dict['repetitions'] = {'unit': '#', 'init_val': 0, 'min': -1,
                                              'max': (2 ** 31 - 1), 'view_stepsize': 1, 'dec': 0,
                                              'type': int}
        self.parameter_dict['trigger_wait'] = {'unit': '', 'init_val': False, 'min': 0,
                                               'max': 1, 'view_stepsize': 1, 'dec': 0,
                                               'type': bool}
        self.parameter_dict['go_to'] = {'unit': '', 'init_val': 0, 'min': -1,
                                        'max': (2 ** 31 - 1), 'view_stepsize': 1, 'dec': 0,
                                        'type': int}
        self.parameter_dict['event_jump_to'] = {'unit': '', 'init_val': 0, 'min': -1,
                                                'max': (2 ** 31 - 1), 'view_stepsize': 1, 'dec': 0,
                                                'type': int}
        self._cfg_param_ps = None
        self.ensemble_dict = None
        self.se_widget.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)
        return

    def set_ensemble_dict(self, ensemble_dict):
        if self.ensemble_dict is None:
            self.ensemble_dict = ensemble_dict
            self._set_columns()
        else:
            self.ensemble_dict = ensemble_dict

        for row in range(self.se_widget.rowCount()):
            data = self.get_element(row, 0)
            if data not in list(self.ensemble_dict):
                self.initialize_cells(start_row=row, stop_row=row+1, start_col=0, stop_col=1)
        return

    def _get_list(self):
        return list(self.ensemble_dict)

    def initialize_cells(self, start_row, stop_row=None, start_col=None, stop_col=None):
        """ Initialize the desired cells in the sequence editor table.

        @param start_row: int, index of the row, where the initialization
                          should start
        @param stop_row: int, optional, index of the row, where the
                         initalization should end.
        @param start_col: int, optional, index of the column where the
                          initialization should start
        @param stop_col: int, optional, index of the column, where the
                         initalization should end.

        With this function it is possible to reinitialize specific elements or
        part of a row or even the whole row. If start_row is set to 0 the whole
        row is going to be initialzed to the default value.
        """
        if stop_row is None:
            stop_row = start_row +1
        if start_col is None:
            start_col = 0
        if stop_col is None:
            stop_col = self.se_widget.columnCount()
        for col_num in range(start_col, stop_col):
            for row_num in range(start_row,stop_row):
                # get the model, here are the data stored:
                model = self.se_widget.model()
                # get the corresponding index of the current element:
                index = model.index(row_num, col_num)
                # get the initial values of the delegate class which was uses for this column:
                ini_values = self.se_widget.itemDelegateForColumn(col_num).get_initial_value()
                # set initial values:
                model.setData(index, ini_values[0], ini_values[1])
        return

    def _set_columns(self):
        # Erase the delegate from the column, i.e. pass a None reference:
        for column in range(self.se_widget.columnCount()):
            self.se_widget.setItemDelegateForColumn(column, None)
        # clear the number of columns and set them to 1:
        self.se_widget.setColumnCount(1)
        self.se_widget.setHorizontalHeaderItem(0, QtWidgets.QTableWidgetItem())
        self.se_widget.horizontalHeaderItem(0).setText('Block Ensemble')
        self.se_widget.setColumnWidth(0, 100)

        item_dict = {}
        item_dict['get_list_method'] = self._get_list
        comboDelegate = ComboBoxDelegate(self.se_widget, item_dict)
        self.se_widget.setItemDelegateForColumn(0, comboDelegate)

        for column, parameter in enumerate(self.parameter_dict):
            # add the new properties to the whole column through delegate:
            item_dict = self.parameter_dict[parameter]
            unit_text = item_dict['unit']
            self.se_widget.insertColumn(1+column)
            self.se_widget.setHorizontalHeaderItem(1+column, QtWidgets.QTableWidgetItem())
            if item_dict['unit'] == '':
                self.se_widget.horizontalHeaderItem(1 + column).setText('{0}'.format(parameter))
            else:
                self.se_widget.horizontalHeaderItem(1+column).setText('{0} ({1})'.format(parameter,
                                                                                         unit_text))
            self.se_widget.setColumnWidth(1+column, 100)
            # Use only DoubleSpinBox as delegate:
            if item_dict['type'] is bool:
                delegate = CheckBoxDelegate(self.se_widget, item_dict)
            elif item_dict['type'] is int:
                delegate = SpinBoxDelegate(self.se_widget, item_dict)
            else:
                delegate = ScienDSpinBoxDelegate(self.se_widget, item_dict)
            self.se_widget.setItemDelegateForColumn(1+column, delegate)

        self.initialize_cells(start_row=0, stop_row=self.se_widget.rowCount())
        self._set_cfg_param()
        # FIXME: Implement a proper way to update the current block ensemble parameters
        return

    def _set_cfg_param(self):
        """ Set the parameter configuration of the Pulse_Block according to the
        current table configuration and updates the dict.
        """
        cfg_param_ps = OrderedDict()
        for column in range(self.se_widget.columnCount()):
            text = self.se_widget.horizontalHeaderItem(column).text()
            if 'Block Ensemble' in text:
                cfg_param_ps['block_ensemble'] = column
            elif 'repetitions' in text:
                cfg_param_ps['repetitions'] = column
            elif 'trigger_wait' in text:
                cfg_param_ps['trigger_wait'] = column
            elif 'go_to' in text:
                cfg_param_ps['go_to'] = column
            elif 'event_jump_to' in text:
                cfg_param_ps['event_jump_to'] = column
            else:
                print('text:', text)
                raise NotImplementedError
        self._cfg_param_ps = cfg_param_ps
        return

    def clear_table(self):
        """ Delete all rows in the sequence editor table. """
        self.se_widget.blockSignals(True)
        self.se_widget.setRowCount(1)
        self.se_widget.clearContents()
        self.initialize_cells(start_row=0)
        self.se_widget.blockSignals(False)
        # FIXME: Implement a proper way to update the current block ensemble parameters
        return

    def delete_row(self, index):
        """ Delete row number 'index' """
        if self.se_widget.rowCount() == 1 and index == 0:
            return
        self.se_widget.blockSignals(True)
        self.se_widget.removeRow(index)
        self.se_widget.blockSignals(False)
        # FIXME: Implement a proper way to update the current block ensemble parameters
        return

    def insert_rows(self, index, number_to_add=1):
        """ Add 'number_to_add' rows after row number 'index' """
        self.se_widget.blockSignals(True)
        for i in range(number_to_add):
            self.se_widget.insertRow(index)
        self.initialize_cells(start_row=index, stop_row=index + number_to_add)
        self.se_widget.blockSignals(False)
        # FIXME: Implement a proper way to update the current block ensemble parameters
        return

    def set_element(self, row, column, value):
        """ Simplified wrapper function to set the data to a specific cell in the table.

        @param int row: row index
        @param int column: column index

        Note that the order of the arguments in this function (first row index and then column
        index) was taken from the Qt convention. A type check will be performed for the passed
        value argument. If the type does not correspond to the delegate, then the value will not be
        changed. You have to ensure that.
        """
        model = self.se_widget.model()
        access = self.se_widget.itemDelegateForColumn(column).model_data_access
        data = self.se_widget.model().index(row, column).data(access)
        if isinstance(data, float) and isinstance(value, float):
            model.setData(model.index(row, column), value, access)
            return value
        elif isinstance(data, int) and isinstance(value, int):
            model.setData(model.index(row, column), value, access)
            return value
        elif isinstance(data, bool) and isinstance(value, bool):
            model.setData(model.index(row, column), value, access)
            return value
        elif isinstance(data, str) and isinstance(value, str):
            model.setData(model.index(row, column), value, access)
            return value
        else:
            return data

    def get_element(self, row, column):
        """ Simplified wrapper function to get the data from a specific cell in the table.

        @param int row: row index
        @param int column: column index
        @return: the value of the corresponding cell, which can be a string, a float or an integer.
                 Remember that the checkbox state unchecked corresponds to 0 and check to 2.
                 That is Qt convention.

        Note that the order of the arguments in this function (first row index
        and then column index) was taken from the Qt convention.
        """
        # Get from the corresponding delegate the data access model
        access = self.se_widget.itemDelegateForColumn(column).model_data_access
        data = self.se_widget.model().index(row, column).data(access)
        return data

    def load_pulse_sequence(self, sequence):
        """

        @param sequence:
        """
        # Sanity checks:
        if sequence is None:
            return
        # clear the block organizer table
        self.clear_table()
        # get amout of rows needed for display
        rows = len(sequence.ensemble_param_list)
        # add as many rows as there are block ensembles in the sequence minus 1 because a single
        # row is already present after clear
        self.insert_rows(1, rows - 1)
        # run through all ensembles in the pulse_sequence to fill in the row informations
        for row_index, (block_ensemble, seq_param) in enumerate(sequence.ensemble_param_list):
            column = self._cfg_param_ps['block_ensemble']
            self.set_element(row_index, column, block_ensemble.name)
            column = self._cfg_param_ps['repetitions']
            self.set_element(row_index, column, int(seq_param['repetitions']))
            column = self._cfg_param_ps['trigger_wait']
            self.set_element(row_index, column, bool(seq_param['trigger_wait']))
            column = self._cfg_param_ps['go_to']
            self.set_element(row_index, column, int(seq_param['go_to']))
            column = self._cfg_param_ps['event_jump_to']
            self.set_element(row_index, column, int(seq_param['event_jump_to']))
        return

    def generate_sequence_object(self, sequence_name, rotating_frame=True):
        """
        Generates from an given sequence editor table a PulseSequence object.

        @param str sequence_name: Name of the created PulseSequence object
        @param bool rotating_frame: optional, whether the phase preservation is maintained
                                    throughout the sequence.
        """
        # list of all the pulse block ensemble objects
        pbe_obj_list = []

        for row_index in range(self.se_widget.rowCount()):
            # Fetch previously saved ensemble object
            block_ensemble_name = self.get_element(row_index, self._cfg_param_ps['block_ensemble'])
            ensemble = self.ensemble_dict[block_ensemble_name]

            # parameter dictionary for pulse sequences
            seq_param = dict()
            seq_param['repetitions'] = self.get_element(row_index,
                                                        self._cfg_param_ps['repetitions'])
            seq_param['trigger_wait'] = int(self.get_element(row_index,
                                                             self._cfg_param_ps['trigger_wait']))
            seq_param['go_to'] = self.get_element(row_index, self._cfg_param_ps['go_to'])
            seq_param['event_jump_to'] = self.get_element(row_index,
                                                          self._cfg_param_ps['event_jump_to'])
            # Append ensemble object along with repetitions to the ensemble list
            pbe_obj_list.append((ensemble, seq_param))

        # Create the PulseSequence object
        pulse_sequence = PulseSequence(name=sequence_name, ensemble_param_list=pbe_obj_list,
                                       rotating_frame=rotating_frame)
        return pulse_sequence
