#from PyQt4 import QtCore, QtGui
from pyqtgraph.Qt import QtCore, QtGui, uic
import pyqtgraph as pg
import numpy as np
import time
import os

from collections import OrderedDict
from gui.guibase import GUIBase

# Rather than import the ui*.py file here, the ui*.ui file itself is loaded by uic.loadUI in the QtGui classes below.


class PulsedMeasurementMainWindow(QtGui.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pulsed_measurement_gui.ui')

        # Load it
        super(PulsedMeasurementMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

class PulsedMeasurementGui(GUIBase):
    """
    This is the GUI Class for pulsed measurements
    """
    _modclass = 'PulsedMeasurementGui'
    _modtype = 'gui'

    ## declare connectors
    _in = { 'pulseanalysislogic': 'PulseAnalysisLogic',
            'sequencegeneratorlogic': 'SequenceGeneratorLogic'
            }

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.initUI}
        super().__init__(manager, name, config, c_dict)

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
        self._mw.binning_comboBox.addItem(str(self._pulse_analysis_logic.fast_counter_status['binwidth_ns']))
        self._mw.binning_comboBox.addItem(str(self._pulse_analysis_logic.fast_counter_status['binwidth_ns']*2.))

        #######################################################################
        ##                Configuration of the InputWidgets                  ##
        #######################################################################

#        # Add Validators to InputWidgets
        validator = QtGui.QDoubleValidator()
        validator2 = QtGui.QIntValidator()

        self._mw.frequency_InputWidget.setValidator(validator)
        self._mw.power_InputWidget.setValidator(validator)
        self._mw.numlaser_InputWidget.setValidator(validator2)
        self._mw.taustart_InputWidget.setValidator(validator)
        self._mw.tauincrement_InputWidget.setValidator(validator)
#
#        # Fill in default values:
        self._mw.frequency_InputWidget.setText(str(2870.))
        self._mw.power_InputWidget.setText(str(-30.))
        self._mw.numlaser_InputWidget.setText(str(100))
        self._mw.taustart_InputWidget.setText(str(1))
        self._mw.tauincrement_InputWidget.setText(str(1))
        self._mw.lasertoshow_spinBox.setRange(0, 100)
        self._mw.lasertoshow_spinBox.setPrefix("#")
        self._mw.lasertoshow_spinBox.setSpecialValueText("sum")
        self._mw.lasertoshow_spinBox.setValue(0)

        #######################################################################
        ##                      Connect signals                              ##
        #######################################################################

        # Connect the RadioButtons and connect to the events if they are clicked:
        self._mw.idle_radioButton.toggled.connect(self.idle_clicked)
        self._mw.run_radioButton.toggled.connect(self.run_clicked)

        self._pulse_analysis_logic.signal_laser_plot_updated.connect(self.refresh_lasertrace_plot)
        self._pulse_analysis_logic.signal_signal_plot_updated.connect(self.refresh_signal_plot)
        
        # Connect InputWidgets to events
        self._mw.numlaser_InputWidget.editingFinished.connect(self.seq_parameters_changed)
        self._mw.lasertoshow_spinBox.valueChanged.connect(self.seq_parameters_changed)
        self._mw.taustart_InputWidget.editingFinished.connect(self.seq_parameters_changed)
        self._mw.tauincrement_InputWidget.editingFinished.connect(self.seq_parameters_changed)
        
        # Show the Main GUI:
        self._mw.show()
        
    def deactivation(self, e):
        """ Undo the Definition, configuration and initialisation of the pulsed measurement GUI.

          @param class e: event class from Fysom

        This deactivation disconnects all the graphic modules, which were
        connected in the initUI method.
        """
        # disconnect signals
        self._mw.idle_radioButton.toggled.disconnect()
        self._mw.run_radioButton.toggled.disconnect()
        self._pulse_analysis_logic.signal_laser_plot_updated.disconnect()
        self._pulse_analysis_logic.signal_signal_plot_updated.disconnect()
        self._mw.numlaser_InputWidget.editingFinished.disconnect()
        self._mw.lasertoshow_spinBox.valueChanged.disconnect()
        # close main window
        self._mw.close()

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
        """ Manages what happens if scan is started.

        @param bool enabled: start scan if that is possible
        """

        #Firstly stop any scan that might be in progress
        self._pulse_analysis_logic.stop_pulsed_measurement()
        #Then if enabled. start a new scan.
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
        
    
    def seq_parameters_changed(self):
        laser_num = int(self._mw.numlaser_InputWidget.text())
        tau_start = int(self._mw.taustart_InputWidget.text())
        tau_incr = int(self._mw.tauincrement_InputWidget.text())
        self._mw.lasertoshow_spinBox.setRange(0, laser_num)
        laser_show = self._mw.lasertoshow_spinBox.value()
        if (laser_show > laser_num):
            self._mw.lasertoshow_spinBox.setValue(0)
            laser_show = self._mw.lasertoshow_spinBox.value()
        tau_vector = np.array(range(tau_start, tau_start + tau_incr*laser_num, tau_incr))
        self._pulse_analysis_logic.running_sequence_parameters['tau_vector'] = tau_vector
        self._pulse_analysis_logic.running_sequence_parameters['number_of_lasers'] = laser_num
        self._pulse_analysis_logic.display_pulse_no = laser_show
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
