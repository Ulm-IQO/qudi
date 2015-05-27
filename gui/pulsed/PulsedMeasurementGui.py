#from PyQt4 import QtCore, QtGui
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import numpy as np
import time

from collections import OrderedDict
from gui.GUIBase import GUIBase
from gui.pulsed.PulsedMeasurementGuiUI import Ui_MainWindow

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
        c_dict = {'onactivate': self.initUI}
        super().__init__(
                    manager,
                    name,
                    config,
                    c_dict)
        
        ## declare connectors
        self.connector['in']['pulseanalysislogic'] = OrderedDict()
        self.connector['in']['pulseanalysislogic']['class'] = 'PulseAnalysisLogic'
        self.connector['in']['pulseanalysislogic']['object'] = None
        
        self.connector['in']['sequencegeneratorlogic'] = OrderedDict()
        self.connector['in']['sequencegeneratorlogic']['class'] = 'SequenceGeneratorLogic'
        self.connector['in']['sequencegeneratorlogic']['object'] = None
        
#        self.connector['in']['savelogic'] = OrderedDict()
#        self.connector['in']['savelogic']['class'] = 'SaveLogic'
#        self.connector['in']['savelogic']['object'] = None

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')  
                        
    def initUI(self, e=None):
        """ Definition, configuration and initialisation of the pulsed measurement GUI.
          
          @param class e: event class from Fysom


        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """
        self._pulse_analysis_logic = self.connector['in']['pulseanalysislogic']['object']
        self._sequence_generator_logic = self.connector['in']['sequencegeneratorlogic']['object']
#        self._save_logic = self.connector['in']['savelogic']['object']  
        
        # Use the inherited class 'Ui_ODMRGuiUI' to create now the 
        # GUI element:
        self._mw = PulsedMeasurementMainWindow()
        
        
        # Get the image from the logic
        self.signal_image = pg.PlotDataItem(self._pulse_analysis_logic.signal_plot_x, self._pulse_analysis_logic.signal_plot_y)
        self.lasertrace_image = pg.PlotDataItem(self._pulse_analysis_logic.laser_plot_x, self._pulse_analysis_logic.laser_plot_y)
        
        
        # Add the display item to the xy VieWidget, which was defined in
        # the UI file.
        self._mw.signal_plot_ViewWidget.addItem(self.signal_image)
        self._mw.lasertrace_plot_ViewWidget.addItem(self.lasertrace_image)
    
        
        # Set the state button as ready button as default setting.
        self._mw.idle_radioButton.click()
        
        # Configuration of the comboWidget
        self._mw.binning_comboBox.addItem(str(self._pulse_analysis_logic._binwidth_ns))
        self._mw.binning_comboBox.addItem(str(self._pulse_analysis_logic._binwidth_ns*2.))
        
        self.sequence_list_changed()
        
        
        #######################################################################
        ##                Configuration of the InputWidgets                  ##
        #######################################################################
        
#        # Add Validators to InputWidgets 
        validator = QtGui.QDoubleValidator()
        validator2 = QtGui.QIntValidator()
        
        self._mw.frequency_InputWidget.setValidator(validator)
        self._mw.power_InputWidget.setValidator(validator)
        self._mw.pg_frequency_lineEdit.setValidator(validator2)
#        
#        # Fill in default values:
        self._mw.frequency_InputWidget.setText(str(-1.))     
        self._mw.power_InputWidget.setText(str(-1.))
        self._mw.pg_frequency_lineEdit.setText(str(self._sequence_generator_logic.pg_frequency_MHz))
        
        self._mw.repetitions_lineEdit.setText(str(1))
#        
#        # Update the inputed/displayed numbers if return key is hit:
#
#        self._mw.frequency_InputWidget.returnPressed.connect(self.change_frequency)
#        self._mw.power_InputWidget.returnPressed.connect(self.change_start_freq)
#        self._mw.pg_frequency_lineEdit.returnPressed.connect(self.change_step_freq)
#        
#        # Update the inputed/displayed numbers if the cursor has left the field:
#
#        self._mw.frequency_InputWidget.editingFinished.connect(self.change_frequency)
#        self._mw.power_InputWidget.editingFinished.connect(self.change_power)
#        self._mw.pg_frequency_lineEdit.editingFinished.connect(self.change_pg_frequency)
        
        
        #######################################################################
        ##                  Configuration of the TableWidget                 ##
        #######################################################################
        # insert first empty row 
        self.create_row()
        
        # adjust table format
        header = self._mw.sequence_tableWidget.horizontalHeader()
        for i in range(8):
            header.resizeSection(i, 50)
            
        header.resizeSection(8, 100)
        header.resizeSection(9, 100)
        header.resizeSection(10, 70)
        header.resizeSection(11, 70)
#        self._mw.sequence_tableWidget.resizeRowsToContents()
#        self._mw.sequence_tableWidget.resizeColumnToContents(i)
        
        
        #######################################################################
        ##                      Connect signals                              ##
        #######################################################################
       
        # Connect the RadioButtons and connect to the events if they are clicked:
        self._mw.idle_radioButton.toggled.connect(self.idle_clicked)
        self._mw.run_radioButton.toggled.connect(self.run_clicked)
                
        self._pulse_analysis_logic.signal_laser_plot_updated.connect(self.refresh_lasertrace_plot)
        self._pulse_analysis_logic.signal_signal_plot_updated.connect(self.refresh_signal_plot)
        
        # Connect the PushButtons and connect to the corresponding events.
        self._mw.addrow_pushButton.clicked.connect(self.create_row)
        self._mw.deleterow_pushButton.clicked.connect(self.delete_row)
        self._mw.clear_list_pushButton.clicked.connect(self.clear_list)
        self._mw.save_sequence_pushButton.clicked.connect(self.save_sequence)
        self._mw.delete_sequence_pushButton.clicked.connect(self.delete_sequence)
        
        # Connect the TableWidget to events when changed
        self._mw.sequence_tableWidget.itemChanged.connect(self.sequence_parameters_changed)
        
        # Connect the ComboBox to events when changed
        self._mw.sequence_list_comboBox.activated.connect(self.current_sequence_changed)
        # Show the Main ODMR GUI:

        self._mw.show()

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

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
        # check if a current row is selected. Select last row if not.
        current_row = self._mw.sequence_tableWidget.currentRow()
        if current_row == -1:
            current_row = self._mw.sequence_tableWidget.rowCount()
            
        # delete current row and all its items
        self._mw.sequence_tableWidget.removeRow(current_row)
        
        # decrement current row and update parameters
        self._mw.sequence_tableWidget.setCurrentCell(current_row-1, 8)
        self.update_sequence_parameters()
        return
        
    
    def clear_list(self):
        ''' This method deletes all rows in the TableWidget.
        '''
        # clear the TableWidget
        number_of_rows = self._mw.sequence_tableWidget.rowCount()
        
        while number_of_rows >= 0:
            self._mw.sequence_tableWidget.removeRow(number_of_rows)
            number_of_rows -= 1
        
        # create a single row to start with and update parameters
        self.create_row()
        self.update_sequence_parameters()
        return
    
    
    def sequence_parameters_changed(self, item):
        ''' This method calculates and updates all parameters (size, length etc.) upon a change of a sequence entry.
        
        @param QTableWidgetItem item: Table item that has been changed
        '''
        # Check if the changed item is of importance for the parameters
        if (item.column() != 8) and (item.column() != 9) and (item.column() != 10):
            return
            
        # calculate the current sequence parameters
        self.update_sequence_parameters()
        return

    def update_sequence_parameters(self):
        # calculate the current sequence parameters
        repetitions = int(self._mw.repetitions_lineEdit.text())
        matrix = self.get_matrix()
        sequence_length_bins, sequence_length_ms = self._sequence_generator_logic.calculate_sequence_parameters(matrix, repetitions)
        
        # update the DisplayWidgets
        self._mw.length_bins_lcdNumber.display(sequence_length_bins)
        self._mw.length_s_lcdNumber.display(sequence_length_ms)
        return


    def save_sequence(self):
        ''' This method encodes the currently edited sequence into a matrix for passing it to the logic module. 
            There the sequence will be created and saved.
        '''
        # Create matrix to pass the data to the logic module where it will be saved
        matrix = self.get_matrix()
        name = str(self._mw.sequence_name_lineEdit.text())
        repetitions = int(self._mw.repetitions_lineEdit.text())
        self._sequence_generator_logic.save_sequence(matrix, name, repetitions)
        # update sequence combo boxes
        self.sequence_list_changed()
        return
        
        
    def get_matrix(self):
        ''' This method creates a matrix out of the current TableWidget to be further processed by the logic module.
        '''
        # get the number of rows and columns
        num_of_rows = self._mw.sequence_tableWidget.rowCount()
        num_of_columns = self._mw.sequence_tableWidget.columnCount()
        
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
            
        # Pass matrix, sequence name and number of repetitions to the logic module
#        self._sequence_generator_logic.current_matrix = matrix
#        self._sequence_generator_logic.current_sequence_name = str(self._mw.sequence_name_lineEdit.text())
#        self._sequence_generator_logic.current_sequence_reps = int(self._mw.repetitions_lineEdit.text())
#        name_matrix_reps = [str(self._mw.sequence_name_lineEdit.text()), matrix, int(self._mw.repetitions_lineEdit.text())]
        return matrix
      
      
    def create_table(self):
        ''' This method creates a TableWidget out of a matrix passed from the logic module.
        '''
        # get matrix from the sequence generator logic
        matrix = self._sequence_generator_logic.current_matrix
        # clear current table widget
        self.clear_list()
        self.delete_row()
        # create as many rows in the table widget as the matrix has and fill them with entries
        for row_number, row in enumerate(matrix):
            # create the row
            self.create_row()
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
        self._sequence_generator_logic.update_current_sequence(name)
        self.create_table()
        self._mw.repetitions_lineEdit.setText(str(self._sequence_generator_logic.current_sequence_reps))
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
