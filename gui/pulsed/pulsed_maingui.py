# -*- coding: utf-8 -*-
"""
Created on Mon Jun 29 17:06:00 2015

@author: astark
"""

#from PyQt4 import QtCore, QtGui
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import numpy as np

from collections import OrderedDict
from gui.guibase import GUIBase
from gui.pulsed.ui_pulsed_maingui import Ui_MainWindow
from core.util.mutex import Mutex

# To convert the *.ui file to a raw PulsedMeasurementsGuiUI.py file use the python script
# in the Anaconda directory, which you can find in:
#
# "<Installation-dir of Anacona>\Anaconda3\Lib\site-packages\PyQt4\uic\pyuic.py".
#
# Then use that script like
#
# "<Installation-dir of Anacona>\Anaconda3\Lib\site-packages\PyQt4\uic\pyuic.py PulsedMeasurementsGuiUI.ui > PulsedMeasurementsGuiUI.py

class PulsedMeasurementMainWindow(QtGui.QMainWindow,Ui_MainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setupUi(self)

class PulsedMeasurementGui(GUIBase):
    """
    This is the GUI Class for pulsed measurements
    """
    _modclass = 'PulsedMeasurementGui'
    _modtype = 'gui'

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.initUI, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, c_dict)

        ## declare connectors
        self.connector['in']['pulseanalysislogic'] = OrderedDict()
        self.connector['in']['pulseanalysislogic']['class'] = 'PulseAnalysisLogic'
        self.connector['in']['pulseanalysislogic']['object'] = None

        self.connector['in']['sequencegeneratorlogic'] = OrderedDict()
        self.connector['in']['sequencegeneratorlogic']['class'] = 'SequenceGeneratorLogic'
        self.connector['in']['sequencegeneratorlogic']['object'] = None

        self.connector['in']['savelogic'] = OrderedDict()
        self.connector['in']['savelogic']['class'] = 'SaveLogic'
        self.connector['in']['savelogic']['object'] = None

        self._pulse_analysis_logic = self.connector['in']['pulseanalysislogic']['object']
        self._sequence_generator_logic = self.connector['in']['sequencegeneratorlogic']['object']
        self._save_logic = self.connector['in']['savelogic']['object']

        self.logMsg('The following configuration was found.',
                    msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')

        #locking for thread safety
        self.threadlock = Mutex()

    def initUI(self, e=None):
        """ Definition, configuration and initialisation of the pulsed measurement GUI.

          @param class e: event class from Fysom

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """


        self._mw = PulsedMeasurementMainWindow()


        self._mw.add_init_row_PushButton.clicked.connect(self.add_init_row)
        self._mw.del_init_row_PushButton.clicked.connect(self.del_init_row)
        self._mw.clear_init_table_PushButton.clicked.connect(self.clear_init_table)

        self._mw.add_repeat_row_PushButton.clicked.connect(self.add_repeat_row)
        self._mw.del_repeat_row_PushButton.clicked.connect(self.del_repeat_row)
        self._mw.clear_repeat_table_PushButton.clicked.connect(self.clear_repeat_table)


        self._count_analog_channels()
        self._count_digital_channels()
        self.analog_channel_parameter = ['Function', 'Freq (GHz)',
                                         'Ampl. (V)', 'Phase(°)']
        self.block_parameter = ['Length (ns)', 'Inc. (ns)', 'Repeat?',
                                'Use as tau?']

        self._mw.show()


    def deactivation(self, e):
        """ Undo the Definition, configuration and initialisation of the pulsed measurement GUI.

          @param class e: event class from Fysom

        This deactivation disconnects all the graphic modules, which were
        connected in the initUI method.
        """
        self._mw.add_init_row_PushButton.clicked.disconnect()
        self._mw.del_init_row_PushButton.clicked.disconnect()
        self._mw.clear_init_table_PushButton.clicked.disconnect()

        self._mw.add_repeat_row_PushButton.clicked.disconnect()
        self._mw.del_repeat_row_PushButton.clicked.disconnect()
        self._mw.clear_repeat_table_PushButton.clicked.disconnect()

        self._mw.close()


    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()


    def add_init_row(self):
        """
        """

    def del_init_row(self):
        """
        """
        self.update_sequence_parameters()

    def clear_init_table(self):
        """
        """

        self._mw.init_block_TableWidget.setRowCount(1)
        self._mw.init_block_TableWidget.clearContents()

    def add_repeat_row(self):
        """
        """

    def del_repeat_row(self):
        """
        """
        self.update_sequence_parameters()

    def clear_repeat_table(self):
        """
        """

        self._mw.repeat_block_TableWidget.setRowCount(1)
        self._mw.repeat_block_TableWidget.clearContents()

    def _count_digital_channels(self):
        """
        """
        count_dch = 0
        for column in range(self._mw.init_block_TableWidget.columnCount()):
            if 'DCh' in self._mw.init_block_TableWidget.horizontalHeaderItem(column).text():
                count_dch = count_dch + 1

        self.num_d_ch = count_dch
        return count_dch

    def _use_digital_ch(self, num_d_ch):
        """

        @param int num_d_ch:

        This method is based on the idea that digital channels are added or
        removed subsequently and not at once, therefore you have to ensure that
        this function is called by changing num_digital_channels
        subsequentially. It should also be ensured that the number of channels
        are not falling below 2 (that number is more or less arbitrary).
        """

        #self.lock()
        #self._count_digital_channels()

        if (self.num_a_ch == 1) and (num_d_ch != 2):
            self.logMsg('For one analog channel the number of digital '
                        'channels must be set to 2!\nTherefore the number of '
                        'digital channels is set to 2 in the following.',
                        msgType='warning')
            num_d_ch = 2

        if (self.num_a_ch == 2) and (num_d_ch != 4):
            self.logMsg('For two analog channels the number of digital '
                        'channels must be set to 4!\nTherefore the number of '
                        'digital channels is set to 4 in the following.',
                        msgType='warning')
            num_d_ch = 4

        if self.num_d_ch < num_d_ch:
            position_list = []

            if self.num_a_ch == 0:
                for channel in range(self.num_d_ch, num_d_ch):
                    position_list.append(channel)

            if self.num_a_ch == 1:
                for channel in range(self.num_d_ch, num_d_ch):
                    position_list.append(channel+len(self.analog_channel_parameter))

            if self.num_a_ch == 2:
                for channel in range(self.num_d_ch, num_d_ch):
                    if channel < 2:
                        position_list.append(len(self.analog_channel_parameter) + channel)
                    else:
                        position_list.append(len(self.analog_channel_parameter)*2 + channel)

            for appended_channel, channel_pos in enumerate(position_list):

                self._mw.init_block_TableWidget.insertColumn(channel_pos)
                self._mw.init_block_TableWidget.setHorizontalHeaderItem(channel_pos, QtGui.QTableWidgetItem())
                self._mw.init_block_TableWidget.horizontalHeaderItem(channel_pos).setText('DCh{0}'.format(self.num_d_ch+appended_channel) )
                self._mw.init_block_TableWidget.setColumnWidth(channel_pos, 40)

            self.num_d_ch = self.num_d_ch + len(position_list)

        elif self.num_d_ch > num_d_ch:
            position_list = []
            #if self.num_a_ch == 0:

            for column in range(self.num_d_ch, num_d_ch-1, -1):
                position_list.append(column)


            for channel_pos in position_list:
                aimed_ch = 'DCh{0}'.format(channel_pos)

                for column in range(self._mw.init_block_TableWidget.columnCount()-1, -1, -1):
                    if aimed_ch in self._mw.init_block_TableWidget.horizontalHeaderItem(column).text():
                        self._mw.init_block_TableWidget.removeColumn(column)
                        break
#
            self.num_d_ch = num_d_ch
#        if num_d_ch == self.num_d_ch:
#            # then there is no need to create channels
#            return
#
#        if self.num_a_ch == 0:
#            channelpos = num_d_ch
#        if num_d_ch > self.num_d_ch:
#            # that means create digital channels.
#            self._mw.init_block_Tab
#
#leWidget.insertColumn(channelpos-1)
#            self._mw.init_block_TableWidget.setHorizontalHeaderItem(channelpos, QtGui.QTableWidgetItem())
#            self._mw.init_block_TableWidget.horizontalHeaderItem(channelpos).setText('DCh{0}'.format(self.num_d_ch+1) )
#            self._mw.init_block_TableWidget.setColumnWidth(channelpos, 30)
#        else:
#            self._mw.init_block_TableWidget.removeColumn(channelpos)


        #self.unlock()



    def _count_analog_channels(self):
        """
        """
        ana1 = 0
        ana2 = 0
        for column in range(self._mw.init_block_TableWidget.columnCount()):
            if 'ACh0' in self._mw.init_block_TableWidget.horizontalHeaderItem(column).text():
                ana1 = 1
            if 'ACh1' in self._mw.init_block_TableWidget.horizontalHeaderItem(column).text():
                ana2 = 1

        self.num_a_ch = ana1 + ana2     # count the found channels together
        return self.num_a_ch

    def _use_analog_channel(self, num_a_ch):
        """

        @param int num_a_ch: number of analog channels. Possible values are
                             0, 1 and 2, where 0 specifies no channels.
        """

        #self.lock()

        if not ((type(num_a_ch) is int) and (0 <= num_a_ch) and (num_a_ch <= 2)):
            self.logMsg('The number for the analog channels was expected to '
                        'be either 0, 1 or 2, but a number of {0} was '
                        'passed.'.format(num_a_ch), msgType='warning')

        if num_a_ch == 0:
            # count backwards and remove from the back the analog parameters:
            for column in range(self._mw.init_block_TableWidget.columnCount()-1, -1, -1):
                if 'ACh0' in self._mw.init_block_TableWidget.horizontalHeaderItem(column).text():
                   self._mw.init_block_TableWidget.removeColumn(column)
                if 'ACh1' in self._mw.init_block_TableWidget.horizontalHeaderItem(column).text():
                   self._mw.init_block_TableWidget.removeColumn(column)
            self.num_a_ch = 0

        elif (num_a_ch == 1) and (self.num_a_ch == 2):
            for column in range(self._mw.init_block_TableWidget.columnCount()-1, -1, -1):
                if 'ACh1' in self._mw.init_block_TableWidget.horizontalHeaderItem(column).text():
                   self._mw.init_block_TableWidget.removeColumn(column)
            self.num_a_ch = 1
            self._use_digital_ch(2)
        elif (num_a_ch > 0) and (self.num_a_ch < 2):
            # repeat the channel creating for the number of channels:
            column_pos = 0

            for channel in range(self.num_a_ch, num_a_ch):

                column_pos = (len(self.analog_channel_parameter) + 2)*channel # for two digital marker channels of the AWG
                # append each parameter like specified in the analog_channel_parameter list:
                for column, parameter in enumerate(self.analog_channel_parameter):
                    self._mw.init_block_TableWidget.insertColumn(column_pos+column)
                    self._mw.init_block_TableWidget.setHorizontalHeaderItem(column_pos+column, QtGui.QTableWidgetItem())
                    self._mw.init_block_TableWidget.horizontalHeaderItem(column_pos+column).setText('ACh{0}\n'.format(channel) + parameter)
                    self._mw.init_block_TableWidget.setColumnWidth(column_pos+column, 70)


                self.num_a_ch = channel+1 # tell how many analog channel has been created
                self._use_digital_ch(2)

        #self.unlock()


    def idle_clicked(self):
        """ Stopp the scan if the state has switched to idle. """
        self._pulse_analysis_logic.stop_pulsed_measurement()


    def run_clicked(self, enabled):
        """ Manages what happens if odmr scan is started.

        @param bool enabled: start scan if that is possible
        """

        #Firstly stop any scan that might be in progress
        self._pulse_analysis_logic.stop_pulsed_measurement()
        #Then if enabled. start a new odmr scan.
        if enabled:
            self._pulse_analysis_logic.start_pulsed_measurement()
    def refresh_lasertrace_plot(self):
        ''' This method refreshes the xy-plot image
        '''
        self.lasertrace_image.setData(self._pulse_analysis_logic.laser_plot_x, self._pulse_analysis_logic.laser_plot_y)

    def refresh_signal_plot(self):
        ''' This method refreshes the xy-matrix image
        '''
        self.signal_image.setData(self._pulse_analysis_logic.signal_plot_x, self._pulse_analysis_logic.signal_plot_y)


    def create_row(self):
        ''' This method creates a new row in the TableWidget at the current cursor position.
        '''
        # block all signals from the TableWidget
        self._mw.sequence_tableWidget.blockSignals(True)
        # insert empty row after current cursor position
        current_row = self._mw.sequence_tableWidget.currentRow()+1
        if current_row == 0:
            current_row = self._mw.sequence_tableWidget.rowCount()

        self._mw.sequence_tableWidget.insertRow(current_row)

        # create the checkbox item to fill the channel rows and the "use as tau" row with
        chkBoxItem  = QtGui.QTableWidgetItem()
        chkBoxItem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        chkBoxItem.setCheckState(QtCore.Qt.Unchecked)

        # fill channel rows with the checkbox item
        for i in range(8):
            self._mw.sequence_tableWidget.setItem(current_row, i, chkBoxItem.clone())

        # create text field item and put it in the "length" and "increment" column
        textItem = QtGui.QTableWidgetItem('0')
        textItem.setFlags(QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled)
        self._mw.sequence_tableWidget.setItem(current_row, 8, textItem)
        self._mw.sequence_tableWidget.setItem(current_row, 9, textItem.clone())

        # put checkbox items into "repeat?" and "use as tau?" column
        self._mw.sequence_tableWidget.setItem(current_row, 10, chkBoxItem.clone())
        self._mw.sequence_tableWidget.setItem(current_row, 11, chkBoxItem.clone())

        # increment current row
        self._mw.sequence_tableWidget.setCurrentCell(current_row, 0)
        # unblock all signals from the TableWidget
        self._mw.sequence_tableWidget.blockSignals(False)
        return


    def delete_row(self):
        ''' This method deletes a row in the TableWidget at the current cursor position.
        '''
        # block all signals from the TableWidget
        self._mw.sequence_tableWidget.blockSignals(True)

        # check if a current row is selected. Select last row if not.
        current_row = self._mw.sequence_tableWidget.currentRow()
        if current_row == -1:
            current_row = self._mw.sequence_tableWidget.rowCount()

        # delete current row and all its items
        self._mw.sequence_tableWidget.removeRow(current_row)

        # decrement current row
        self._mw.sequence_tableWidget.setCurrentCell(current_row-1, 8)

        # unblock all signals from the TableWidget
        self._mw.sequence_tableWidget.blockSignals(False)
        return


    def clear_list(self):
        ''' This method deletes all rows in the TableWidget.
        '''
        # block all signals from the TableWidget
        self._mw.sequence_tableWidget.blockSignals(True)

        # clear the TableWidget
        number_of_rows = self._mw.sequence_tableWidget.rowCount()

        while number_of_rows >= 0:
            self._mw.sequence_tableWidget.removeRow(number_of_rows)
            number_of_rows -= 1

        # unblock all signals from the TableWidget
        self._mw.sequence_tableWidget.blockSignals(False)
        return


    def sequence_parameters_changed(self, item):
        ''' This method calculates and updates all parameters (size, length etc.) upon a change of a sequence entry.

        @param QTableWidgetItem item: Table item that has been changed
        '''
        # Check if the changed item is of importance for the parameters
        if (item.column() in [0,8,9,10]):
            # calculate the current sequence parameters
            self.update_sequence_parameters()
        return


    def update_sequence_parameters(self):
        """ Initialize the matrix creation and update the logic. """
        # calculate the current sequence parameters
        repetitions = int(self._mw.repetitions_lineEdit.text())
        matrix = self.get_matrix()
        self._sequence_generator_logic.update_sequence_parameters(matrix, repetitions)

        # get updated values from SequenceGeneratorLogic
        length_bins = self._sequence_generator_logic._current_sequence_parameters['length_bins']
        length_ms = self._sequence_generator_logic._current_sequence_parameters['length_ms']
        number_of_lasers = self._sequence_generator_logic._current_sequence_parameters['number_of_lasers']

        # update the DisplayWidgets
        self._mw.length_bins_lcdNumber.display(length_bins)
        self._mw.length_s_lcdNumber.display(length_ms)
        self._mw.laser_number_lcdNumber.display(number_of_lasers)
        return


#    def reset_parameters(self):
#        ''' This method resets all GUI parameters to the default state.
#        '''
#        # update the DisplayWidgets
#        self._mw.length_bins_lcdNumber.display(0)
#        self._mw.length_s_lcdNumber.display(0)
#        self._mw.laser_number_lcdNumber.display(0)


    def save_sequence(self):
        ''' This method encodes the currently edited sequence into a matrix for passing it to the logic module.
            There the sequence will be created and saved.
        '''
        # Create matrix to pass the data to the logic module where it will be saved
        name = str(self._mw.sequence_name_lineEdit.text())
        # update current sequence parameters in the logic
        self.update_sequence_parameters()
        # save current sequence under name "name"
        self._sequence_generator_logic.save_sequence(name)
        # update sequence combo boxes
        self.sequence_list_changed()
        return


    def get_matrix(self):
        """ Create a Matrix from the GUI's TableWidget.

        This method creates a matrix out of the current TableWidget to be
        further processed by the logic module.
        """
        # get the number of rows and columns
        num_of_rows = self._mw.sequence_tableWidget.rowCount()
        num_of_columns = self._mw.sequence_tableWidget.columnCount()

        #FIXME: the matrix should not be in the future not an integer type
        #       since the length of a pulse can and have sometimes to be an
        #       float value.

        # Initialize a matrix of proper size and integer data type
        matrix = np.empty([num_of_rows, num_of_columns], dtype=int)
        # Loop through all matrix entries and fill them with the data of the TableWidgetItems
        for row in range(num_of_rows):
            for column in range(num_of_columns):
                # Get the item of the current row and column
                item = self._mw.sequence_tableWidget.item(row, column)
                # check if the current column is a checkbox or a textfield
                if (int(item.flags()) & 16):
                    matrix[row, column] = int(bool(item.checkState()))
                else:
                    matrix[row, column] = int(item.data(0))
        return matrix


    def create_table(self):
        ''' This method creates a TableWidget out of the current matrix passed from the logic module.
        '''
        # get matrix from the sequence generator logic
        matrix = self._sequence_generator_logic._current_matrix
        # clear current table widget
        self.clear_list()
        # create as many rows in the table widget as the matrix has and fill them with entries
        for row_number, row in enumerate(matrix):
            # create the row
            self.create_row()
            # block all signals from the TableWidget
            self._mw.sequence_tableWidget.blockSignals(True)
            # edit all items in the row
            for column_number in range(matrix.shape[1]):
                item = self._mw.sequence_tableWidget.item(row_number, column_number)
                # is the current item a checkbox or a number?
                if (int(item.flags()) & 16):
                    # check ckeckbox if the corresponding matrix entry is "1"
                    if matrix[row_number, column_number] == 1:
                        item.setCheckState(QtCore.Qt.Checked)
                else:
                    item.setText(str(matrix[row_number, column_number]))
        # unblock all signals from the TableWidget
        self._mw.sequence_tableWidget.blockSignals(False)
        return


    def delete_sequence(self):
        ''' This method completely removes the currently selected sequence.
        '''
        # call the delete method in the sequence generator logic
        name = self._mw.sequence_list_comboBox.currentText()
        self._sequence_generator_logic.delete_sequence(name)
        # update the combo boxes
        self.sequence_list_changed()
        self.clear_list()
        return


    def sequence_list_changed(self):
        ''' This method updates the Seqeuence combo boxes upon the adding or removal of a sequence
        '''
        # get the names of all saved sequences from the sequence generator logic
        names = self._sequence_generator_logic.get_sequence_names()
        # clear combo boxes
        self._mw.sequence_name_comboBox.clear()
        self._mw.sequence_list_comboBox.clear()
        # fill combo boxes with current names
        self._mw.sequence_name_comboBox.addItems(names)
        self._mw.sequence_list_comboBox.addItems(names)
        return


    def current_sequence_changed(self):
        ''' This method updates the current sequence variables in the sequence generator logic.
        '''
        name = self._mw.sequence_list_comboBox.currentText()
        self._sequence_generator_logic.set_current_sequence(name)
        self.create_table()
        repetitions = self._sequence_generator_logic._current_sequence_parameters['repetitions']
        self._mw.repetitions_lineEdit.setText(str(repetitions))
        return


    def sequence_to_run_changed(self):
        ''' This method updates the parameter set of the sequence to run in the PulseAnalysisLogic.
        '''
        name = self._mw.sequence_name_comboBox.currentText()
        self._pulse_analysis_logic.update_sequence_parameters(name)
        return


    def clear_list_clicked(self):
        ''' This method clears the current tableWidget, inserts a single empty row and updates the sequence parameters in the GUI and SequenceGeneratorLogic
        '''
        self.clear_list()
        self.create_row()
        self.update_sequence_parameters()
        return





    def test(self):
        print('called test function!')
        print(str(self._mw.sequence_list_comboBox.currentText()))
        return
#
#
#
#    ###########################################################################
#    ##                         Change Methods                                ##
#    ###########################################################################
#
#    def change_frequency(self):
#        self._pulse_analysis_logic.MW_frequency = float(self._mw.frequency_InputWidget.text())
#
#    def change_power(self):
#        self._pulse_analysis_logic.MW_power = float(self._mw.power_InputWidget.text())
#
#    def change_pg_frequency(self):
#        self._pulse_analysis_logic.pulse_generator_frequency = float(self._mw.pg_frequency_lineEdit.text())
#
#    def change_runtime(self):
#        pass
