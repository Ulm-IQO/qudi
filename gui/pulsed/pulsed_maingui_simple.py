# -*- coding: utf-8 -*-

"""
This file contains the QuDi GUI module base class.

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

Copyright (C) 2015 Alexander Stark alexander.stark@uni-ulm.de
"""

from PyQt4 import QtGui, QtCore, uic

import numpy as np
import os
from collections import OrderedDict
import pyqtgraph as pg
from gui.guibase import GUIBase
from core.util.mutex import Mutex

# Rather than import the ui*.py file here, the ui*.ui file itself is loaded by uic.loadUI in the QtGui classes below.

class PulsedMeasurementMainWindow(QtGui.QMainWindow):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pulsed_maingui_simple.ui')

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
            'sequencegeneratorlogic': 'SequenceGeneratorLogic',
            'savelogic': 'SaveLogic',
            'pulsedmeasurementlogic': 'PulsedMeasurementLogic'
            }

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, c_dict)

        self.logMsg('The following configuration was found.',
                    msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')

        #locking for thread safety
        self.threadlock = Mutex()

    def activation(self, e=None):
        """ Initialize, connect and configure the pulsed measurement GUI.

        @param Fysom.event e: Event Object of Fysom

        Establish general connectivity and activate the different tabs of the
        GUI.
        """
        self._pulse_analysis_logic = self.connector['in']['pulseanalysislogic']['object']
        self._pulsed_measurement_logic = self.connector['in']['pulsedmeasurementlogic']['object']
        self._seq_gen_logic = self.connector['in']['sequencegeneratorlogic']['object']
        self._save_logic = self.connector['in']['savelogic']['object']

        self._mw = PulsedMeasurementMainWindow()

        self._activate_analysis_settings_ui(e)
        self._activate_analysis_ui(e)

        self._activate_pulse_generator_ui(e)

        self._activate_pulse_extraction_settings_ui(e)
        self._activate_pulse_extraction_ui(e)

        self.show()


    def deactivation(self, e):
        """ Undo the Definition, configuration and initialisation of the pulsed
            measurement GUI.

        @param Fysom.event e: Event Object of Fysom

        This deactivation disconnects all the graphic modules, which were
        connected in the initUI method.
        """
        self._deactivate_analysis_settings_ui(e)
        self._deactivate_analysis_ui(e)

        self._deactivate_pulse_generator_ui(e)

        self._deactivate_pulse_extraction_settings_ui(e)
        self._deactivate_pulse_extraction_ui(e)


        self._mw.close()

    def show(self):
        """Make main window visible and put it above all other windows. """
        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()


    ###########################################################################
    ###   Methods related to Tab 'Pulse Generator' in the Pulsed Window:    ###
    ###########################################################################

    def _activate_pulse_generator_ui(self, e):
        """ Initialize, connect and configure the 'Pulse Generator' Tab.

        @param Fysom.event e: Event Object of Fysom
        """
        # connect the signals upon changes of the LineEdits and Spinboxes
        self._mw.sample_freq_DSpinBox.editingFinished.connect(self.sample_frequency_changed)
        self._mw.gen_aomdelay_LineEdit.editingFinished.connect(self.aom_delay_changed)
        self._mw.gen_laserlength_LineEdit.editingFinished.connect(self.laser_length_changed)

        # connect the signals for the predefined sequence buttons
        self._mw.gen_rabi_PushButton.clicked.connect(self.generate_rabi_clicked)
        self._mw.gen_xy8_PushButton.clicked.connect(self.generate_xy8_clicked)
        self._mw.gen_pulsedodmr_PushButton.clicked.connect(self.generate_pulsedodmr_clicked)

        # connect the signals for the "Upload on device" section
        # self._mw.upload_on_ch1_PushButton.clicked.connect(self.upload_on_ch1_clicked)
        # self._mw.upload_on_ch2_PushButton.clicked.connect(self.upload_on_ch2_clicked)
        self._mw.upload_PushButton.clicked.connect(self.upload_clicked)

        # connect update signals of the sequence_generator_logic
        self._seq_gen_logic.signal_ensemble_list_updated.connect(self.update_ensemble_list)

        # Add Validators to InputWidgets
        validator = QtGui.QDoubleValidator()
        validator2 = QtGui.QIntValidator()
        self._mw.gen_rabi_freq_LineEdit.setValidator(validator)
        self._mw.gen_rabi_amp_LineEdit.setValidator(validator)
        self._mw.gen_rabi_taustart_LineEdit.setValidator(validator)
        self._mw.gen_rabi_tauend_LineEdit.setValidator(validator)
        self._mw.gen_rabi_points_LineEdit.setValidator(validator2)
        self._mw.gen_aomdelay_LineEdit.setValidator(validator)
        self._mw.gen_laserlength_LineEdit.setValidator(validator)
        self._mw.gen_xy8_freq_LineEdit.setValidator(validator)
        self._mw.gen_xy8_amp_LineEdit.setValidator(validator)
        self._mw.gen_xy8_taustart_LineEdit.setValidator(validator)
        self._mw.gen_xy8_tauend_LineEdit.setValidator(validator)
        self._mw.gen_xy8_points_LineEdit.setValidator(validator2)
        self._mw.gen_xy8_pihalf_LineEdit.setValidator(validator)
        self._mw.gen_xy8_pi_LineEdit.setValidator(validator)
        self._mw.gen_xy8_N_LineEdit.setValidator(validator2)
        self._mw.gen_pulsedodmr_startfreq_LineEdit.setValidator(validator)
        self._mw.gen_pulsedodmr_stopfreq_LineEdit.setValidator(validator)
        self._mw.gen_pulsedodmr_points_LineEdit.setValidator(validator2)
        self._mw.gen_pulsedodmr_amp_LineEdit.setValidator(validator)
        self._mw.gen_pulsedodmr_pi_LineEdit.setValidator(validator2)

        # fill in default values
        self._mw.sample_freq_DSpinBox.setValue(25000)
        self._mw.gen_rabi_freq_LineEdit.setText(str(2870))
        self._mw.gen_rabi_amp_LineEdit.setText(str(0.25))
        self._mw.gen_rabi_taustart_LineEdit.setText(str(1))
        self._mw.gen_rabi_tauend_LineEdit.setText(str(100))
        self._mw.gen_rabi_points_LineEdit.setText(str(100))
        self._mw.gen_rabi_name_LineEdit.setText('Rabi')
        self._mw.gen_xy8_freq_LineEdit.setText(str(2870))
        self._mw.gen_xy8_amp_LineEdit.setText(str(0.25))
        self._mw.gen_xy8_taustart_LineEdit.setText(str(1))
        self._mw.gen_xy8_tauend_LineEdit.setText(str(100))
        self._mw.gen_xy8_points_LineEdit.setText(str(100))
        self._mw.gen_xy8_pihalf_LineEdit.setText(str(25))
        self._mw.gen_xy8_pi_LineEdit.setText(str(50))
        self._mw.gen_xy8_N_LineEdit.setText(str(64))
        self._mw.gen_xy8_name_LineEdit.setText('XY8')
        self._mw.gen_pulsedodmr_startfreq_LineEdit.setText(str(2000))
        self._mw.gen_pulsedodmr_stopfreq_LineEdit.setText(str(3000))
        self._mw.gen_pulsedodmr_points_LineEdit.setText(str(100))
        self._mw.gen_pulsedodmr_amp_LineEdit.setText(str(0.25))
        self._mw.gen_pulsedodmr_pi_LineEdit.setText(str(50))
        self._mw.gen_aomdelay_LineEdit.setText(str(700))
        self._mw.gen_laserlength_LineEdit.setText(str(3000))
        self._mw.gen_pulsedodmr_name_LineEdit.setText('PulsedODMR')

        # initialize the lists of available blocks, ensembles and sequences
        self.update_ensemble_list()

        self.lasernum_changed()
        self.aom_delay_changed()
        self.laser_length_changed()

    def _deactivate_pulse_generator_ui(self, e):
        """ Disconnects the configuration for 'Pulse Generator Tab.

        @param Fysom.event e: Event Object of Fysom
        """
        #FIXME: implement a proper deactivation for that.
        pass

    def sample_frequency_changed(self):
        """
        This method is called when the user enters a new sample frequency in the SpinBox
        """
        freq = 1e6*self._mw.sample_freq_DSpinBox.value()
        self._seq_gen_logic.set_sample_rate(freq)
        return

    # def upload_on_ch1_clicked(self):
    #     """
    #     This method is called when the user clicks on "Upload on Ch1"
    #     """
    #     # Get the ensemble name to be uploaded from the ComboBox
    #     ensemble_name = self._mw.upload_ensemble_ComboBox.currentText()
    #     # Sample and upload the ensemble via logic module
    #     self._seq_gen_logic.download_ensemble(ensemble_name)
    #     # Load the ensemble/waveform into channel 1 (or multiple channels if specified in the ensemble)
    #     self._seq_gen_logic.load_asset(ensemble_name, 1)
    #     return
    #
    # def upload_on_ch2_clicked(self):
    #     """
    #     This method is called when the user clicks on "Upload on Ch2"
    #     """
    #     # Get the ensemble name to be uploaded from the ComboBox
    #     ensemble_name = self._mw.upload_ensemble_ComboBox.currentText()
    #     # Sample and upload the ensemble via logic module
    #     self._seq_gen_logic.download_ensemble(ensemble_name)
    #     # Load the ensemble/waveform into channel 1 (or multiple channels if specified in the ensemble)
    #     self._seq_gen_logic.load_asset(ensemble_name, 2)
    #     return

    def upload_clicked(self):
        """
        This method is called when the user clicks on "Upload"
        """
        # Get the ensemble name to be uploaded from the ComboBox
        ensemble_name = self._mw.upload_ensemble_ComboBox.currentText()
        # Sample and upload the ensemble via logic module
        self._seq_gen_logic.download_ensemble(ensemble_name)
        # Load the ensemble/waveform into channel 1 (or multiple channels if specified in the ensemble)
        self._seq_gen_logic.load_asset(ensemble_name, 1)
        # retrieve important sequence parameters from the sequence_generator_logic and pass it to the pulsed_measurement_logic
        self._pulsed_measurement_logic.sequence_length_s = self._seq_gen_logic.current_ensemble.length_bins / self._seq_gen_logic.sample_rate
        self._pulsed_measurement_logic.number_of_lasers = self._seq_gen_logic.current_ensemble.number_of_lasers
        self._pulsed_measurement_logic.tau_array = self._seq_gen_logic.current_ensemble.tau_array/self._seq_gen_logic.sample_rate
        # update the number of lasers in the analysis tab
        self._mw.numlaser_InputWidget.setText(str(self._seq_gen_logic.current_ensemble.number_of_lasers))
        self.lasernum_changed()
        return

    def update_ensemble_list(self):
        """
        This method is called upon signal_ensemble_list_updated emit of the sequence_generator_logic.
        Updates all ComboBoxes showing generated block_ensembles.
        """
        # updated list of all generated ensembles
        new_list = self._seq_gen_logic.saved_pulse_block_ensembles
        # update upload_ensemble_ComboBox items
        self._mw.upload_ensemble_ComboBox.clear()
        self._mw.upload_ensemble_ComboBox.addItems(new_list)
        return

    def laser_length_changed(self):
        length_s = float(self._mw.gen_laserlength_LineEdit.text())/1e9
        self._pulsed_measurement_logic.laser_length_s = length_s
        self._pulsed_measurement_logic.configure_fast_counter()

    def aom_delay_changed(self):
        aomdelay_s = float(self._mw.gen_aomdelay_LineEdit.text())/1e9
        self._pulsed_measurement_logic.aom_delay_s = aomdelay_s
        self._pulsed_measurement_logic.configure_fast_counter()

    def generate_rabi_clicked(self):
        freq = 1e6*float(self._mw.gen_rabi_freq_LineEdit.text())
        amp = float(self._mw.gen_rabi_amp_LineEdit.text())
        tau_start_bins = np.int(np.rint((1e-9)*float(self._mw.gen_rabi_taustart_LineEdit.text())*self._seq_gen_logic.sample_rate))
        tau_end_bins = np.int(np.rint((1e-9)*float(self._mw.gen_rabi_tauend_LineEdit.text())*self._seq_gen_logic.sample_rate))
        number_of_taus = int(self._mw.gen_rabi_points_LineEdit.text())
        laser_time_bins = np.int(np.rint((1e-9)*float(self._mw.gen_laserlength_LineEdit.text())*self._seq_gen_logic.sample_rate))
        waiting_time_bins = np.int(np.rint((1e-9)*float(self._mw.gen_aomdelay_LineEdit.text())*self._seq_gen_logic.sample_rate))
        name = self._mw.gen_rabi_name_LineEdit.text()
        self._seq_gen_logic.generate_rabi(name, freq, amp, waiting_time_bins, laser_time_bins, tau_start_bins, tau_end_bins, number_of_taus, True)
        return

    def generate_xy8_clicked(self):
        freq = 1e6*float(self._mw.gen_xy8_freq_LineEdit.text())
        amp = float(self._mw.gen_xy8_amp_LineEdit.text())
        tau_start_bins = np.int(np.rint((1e-9)*float(self._mw.gen_xy8_taustart_LineEdit.text())*self._seq_gen_logic.sample_rate))
        tau_end_bins = np.int(np.rint((1e-9)*float(self._mw.gen_xy8_tauend_LineEdit.text())*self._seq_gen_logic.sample_rate))
        number_of_taus = int(self._mw.gen_xy8_points_LineEdit.text())
        N = int(self._mw.gen_xy8_N_LineEdit.text())
        pihalf_bins = np.int(np.rint((1e-9)*float(self._mw.gen_xy8_pihalf_LineEdit.text())*self._seq_gen_logic.sample_rate))
        pi_bins = np.int(np.rint((1e-9)*float(self._mw.gen_xy8_pi_LineEdit.text())*self._seq_gen_logic.sample_rate))
        laser_time_bins = np.int(np.rint((1e-9)*float(self._mw.gen_laserlength_LineEdit.text())*self._seq_gen_logic.sample_rate))
        waiting_time_bins = np.int(np.rint((1e-9)*float(self._mw.gen_aomdelay_LineEdit.text())*self._seq_gen_logic.sample_rate))
        name = self._mw.gen_xy8_name_LineEdit.text()
        self._seq_gen_logic.generate_xy8(name, freq, amp, waiting_time_bins, laser_time_bins, tau_start_bins, tau_end_bins, number_of_taus, pihalf_bins, pi_bins, N, True)
        return

    def generate_pulsedodmr_clicked(self):
        start_freq = 1e6*float(self._mw.gen_pulsedodmr_startfreq_LineEdit.text())
        stop_freq = 1e6*float(self._mw.gen_pulsedodmr_stopfreq_LineEdit.text())
        number_of_points = int(self._mw.gen_pulsedodmr_points_LineEdit.text())
        amp = float(self._mw.gen_pulsedodmr_amp_LineEdit.text())
        pi_bins = np.int(np.rint((1e-9)*float(self._mw.gen_pulsedodmr_pi_LineEdit.text())*self._seq_gen_logic.sample_rate))
        laser_time_bins = np.int(np.rint((1e-9)*float(self._mw.gen_laserlength_LineEdit.text())*self._seq_gen_logic.sample_rate))
        waiting_time_bins = np.int(np.rint((1e-9)*float(self._mw.gen_aomdelay_LineEdit.text())*self._seq_gen_logic.sample_rate))
        name = self._mw.gen_pulsedodmr_name_LineEdit.text()
        self._seq_gen_logic.generate_pulsedodmr(name, start_freq, stop_freq, number_of_points, amp, pi_bins, waiting_time_bins, laser_time_bins, True)
        return




    ###########################################################################
    ###        Methods related to Settings for the 'Analysis' Tab:          ###
    ###########################################################################

    #FIXME: Implement the setting for 'Analysis' tab.

    def _activate_analysis_settings_ui(self, e):
        """ Initialize, connect and configure the Settings of 'Analysis' Tab.

        @param Fysom.event e: Event Object of Fysom
        """

        pass

    def _deactivate_analysis_settings_ui(self, e):
        """ Disconnects the configuration of the Settings for 'Analysis' Tab.

        @param Fysom.event e: Event Object of Fysom
        """

        pass


    ###########################################################################
    ###     Methods related to the Tab 'Analysis' in the Pulsed Window:     ###
    ###########################################################################

    def _activate_analysis_ui(self, e):
        """ Initialize, connect and configure the 'Analysis' Tab.

        @param Fysom.event e: Event Object of Fysom
        """
        # Get the image from the logic
        # pulsed measurement tab
        self.signal_image = pg.PlotDataItem(self._pulsed_measurement_logic.signal_plot_x, self._pulsed_measurement_logic.signal_plot_y)
        self.signal_image_error_bars=pg.ErrorBarItem(x=self._pulsed_measurement_logic.signal_plot_x, y=self._pulsed_measurement_logic.signal_plot_y, top=self._pulsed_measurement_logic.measuring_error_plot_y, bottom=self._pulsed_measurement_logic.measuring_error_plot_y,pen='b')
        self.fft_image = pg.PlotDataItem(self._pulsed_measurement_logic.signal_plot_x, self._pulsed_measurement_logic.signal_plot_y)
        self.lasertrace_image = pg.PlotDataItem(self._pulsed_measurement_logic.laser_plot_x, self._pulsed_measurement_logic.laser_plot_y)
        self.measuring_error_image = pg.PlotDataItem(self._pulsed_measurement_logic.measuring_error_plot_x, self._pulsed_measurement_logic.measuring_error_plot_y*1000)

        self.fit_image = pg.PlotDataItem(self._pulsed_measurement_logic.signal_plot_x, self._pulsed_measurement_logic.signal_plot_y)

        self.sig_start_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(QtGui.QColor(255,0,0,255)))
        self.sig_end_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(QtGui.QColor(255,0,0,255)))
        self.ref_start_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(QtGui.QColor(0,255,0,255)))
        self.ref_end_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(QtGui.QColor(0,255,0,255)))
#
#        # Add the display item to the xy VieWidget, which was defined in
#        # the UI file.
        #self._mw.signal_plot_ViewWidget.clear()
        self._mw.signal_plot_ViewWidget.addItem(self.signal_image)

        #self._mw.signal_plot_ViewWidget.addItem(self.signal_image_error_bars)
        #self._mw.signal_plot_ViewWidget.addItem(self.fit_image)
        self._mw.fft_PlotWidget.addItem(self.fft_image)
        self._mw.lasertrace_plot_ViewWidget.addItem(self.lasertrace_image)

        self._mw.lasertrace_plot_ViewWidget.addItem(self.sig_start_line)
        self._mw.lasertrace_plot_ViewWidget.addItem(self.sig_end_line)
        self._mw.lasertrace_plot_ViewWidget.addItem(self.ref_start_line)
        self._mw.lasertrace_plot_ViewWidget.addItem(self.ref_end_line)
        self._mw.measuring_error_PlotWidget.addItem(self.measuring_error_image)
        self._mw.signal_plot_ViewWidget.showGrid(x=True, y=True, alpha=0.8)
        self._mw.fft_PlotWidget.showGrid(x=True, y=True, alpha=0.8)
        self._mw.signal_plot_ViewWidget.setLabel('left', 'Signal', units='a.u.')
        self._mw.signal_plot_ViewWidget.setLabel('bottom', 'tau', units='s')
        self._mw.lasertrace_plot_ViewWidget.setLabel('left', 'Counts')
        self._mw.lasertrace_plot_ViewWidget.setLabel('bottom', 'time', units='s')
        self._mw.measuring_error_PlotWidget.setLabel('left', 'measuring error', units='a.u.')
        self._mw.measuring_error_PlotWidget.setLabel('bottom', 'tau')
        #self._mw.measuring_error_PlotWidget.showGrid(x=True, y=True, alpha=0.8)


        ##### is needed for the errorbars, but there has to be a better solution
        self.errorbars_present=False

        # Initialize  what is visible and what not
        self._mw.mw_frequency_Label.setVisible(False)
        self._mw.mw_frequency_InputWidget.setVisible(False)
        self._mw.mw_power_Label.setVisible(False)
        self._mw.mw_power_InputWidget.setVisible(False)

        self._mw.tau_start_Label.setVisible(False)
        self._mw.tau_start_InputWidget.setVisible(False)
        self._mw.tau_increment_Label.setVisible(False)
        self._mw.tau_increment_InputWidget.setVisible(False)

        self._mw.fft_PlotWidget.setVisible(False)


        # Set the state button as ready button as default setting.

        self._mw.action_continue_pause.setEnabled(False)

        self._mw.action_pull_data.setEnabled(False)

#        # Add Validators to InputWidgets
        validator = QtGui.QDoubleValidator()
        validator2 = QtGui.QIntValidator()

        # pulsed measurement tab
        self._mw.mw_frequency_InputWidget.setValidator(validator)
        self._mw.mw_power_InputWidget.setValidator(validator)
        self._mw.analysis_period_InputWidget.setValidator(validator)
        self._mw.numlaser_InputWidget.setValidator(validator2)
        self._mw.tau_start_InputWidget.setValidator(validator)
        self._mw.tau_increment_InputWidget.setValidator(validator)
        self._mw.signal_start_InputWidget.setValidator(validator2)
        self._mw.signal_length_InputWidget.setValidator(validator2)
        self._mw.reference_start_InputWidget.setValidator(validator2)
        self._mw.reference_length_InputWidget.setValidator(validator2)

        # Fill in default values:

        # pulsed measurement tab
        self._mw.mw_frequency_InputWidget.setText(str(2870.))
        self._mw.mw_power_InputWidget.setText(str(-30.))
        self._mw.numlaser_InputWidget.setText(str(50))
        self._mw.tau_start_InputWidget.setText(str(1))
        self._mw.tau_increment_InputWidget.setText(str(1))
#        self._mw.lasertoshow_spinBox.setRange(0, 50)
#        self._mw.lasertoshow_spinBox.setPrefix("#")
#        self._mw.lasertoshow_spinBox.setSpecialValueText("sum")
#        self._mw.lasertoshow_spinBox.setValue(0)

        self._mw.laser_to_show_ComboBox.clear()
        self._mw.laser_to_show_ComboBox.addItem('sum')
        for ii in range(50):
            self._mw.laser_to_show_ComboBox.addItem(str(1+ii))

        self._mw.signal_start_InputWidget.setText(str(5))
        self._mw.signal_length_InputWidget.setText(str(200))
        self._mw.reference_start_InputWidget.setText(str(500))
        self._mw.reference_length_InputWidget.setText(str(200))
        self._mw.expected_duration_TimeLabel.setText('00:00:00:03')
        self._mw.elapsed_time_label.setText('00:00:00:00')
        self._mw.elapsed_sweeps_LCDNumber.display(0)
        self._mw.analysis_period_InputWidget.setText(str(2))
        self._mw.refocus_interval_LineEdit.setText(str(500))
        self._mw.odmr_refocus_interval_LineEdit.setText(str(500))


        # Configuration of the fit ComboBox

        self._mw.fit_function_ComboBox.addItem('No Fit')
        self._mw.fit_function_ComboBox.addItem('Rabi Decay')
        self._mw.fit_function_ComboBox.addItem('Lorentian (neg)')
        self._mw.fit_function_ComboBox.addItem('Lorentian (pos)')
        self._mw.fit_function_ComboBox.addItem('N14')
        self._mw.fit_function_ComboBox.addItem('N15')
        self._mw.fit_function_ComboBox.addItem('Stretched Exponential')
        self._mw.fit_function_ComboBox.addItem('Exponential')
        self._mw.fit_function_ComboBox.addItem('XY8')


        # ---------------------------------------------------------------------
        #                         Connect signals
        # ---------------------------------------------------------------------

        # Connect the RadioButtons and connect to the events if they are clicked:
        # pulsed measurement tab
        #self._mw.idle_RadioButton.toggled.connect(self.idle_clicked)
        #self._mw.run_RadioButton.toggled.connect(self.run_clicked)
#        self._mw.pause_RadioButton.toggled.connect(self.pause_clicked)
#        self._mw.continue_RadioButton.toggled.connect(self.continue_clicked)

        self._mw.action_run_stop.triggered.connect(self.run_stop_clicked)

        self._mw.action_continue_pause.triggered.connect(self.continue_pause_clicked)

        self._mw.action_save.toggled.connect(self.save_clicked)

#        self._mw.pull_data_pushButton.clicked.connect(self.pull_data_clicked)
        self._mw.action_pull_data.toggled.connect(self.pull_data_clicked)


        self._pulsed_measurement_logic.signal_laser_plot_updated.connect(self.refresh_lasertrace_plot)
        self._pulsed_measurement_logic.signal_signal_plot_updated.connect(self.refresh_signal_plot)
        self._pulsed_measurement_logic.measuring_error_plot_updated.connect(self.refresh_measuring_error_plot)
        self._pulsed_measurement_logic.signal_time_updated.connect(self.refresh_elapsed_time)

        # sequence generator tab

        # Connect the CheckBoxes
        # anaylsis tab

        self._mw.turn_off_external_mw_source_CheckBox.stateChanged.connect(self.show_external_mw_source_checked)
        self._mw.tau_defined_in_sequence_CheckBox.stateChanged.connect(self.show_tau_editor)
        self._mw.show_fft_plot_CheckBox.stateChanged.connect(self.show_fft_plot)

        # Connect InputWidgets to events
        # pulsed measurement tab
        self._mw.numlaser_InputWidget.editingFinished.connect(self.lasernum_changed)
        self._mw.binning_doubleSpinBox.editingFinished.connect(self.binning_changed)
        self._mw.laser_to_show_ComboBox.activated.connect(self.seq_parameters_changed)
        self._mw.tau_start_InputWidget.editingFinished.connect(self.seq_parameters_changed)
        self._mw.tau_increment_InputWidget.editingFinished.connect(self.seq_parameters_changed)
        self._mw.signal_start_InputWidget.editingFinished.connect(self.analysis_parameters_changed)
        self._mw.signal_length_InputWidget.editingFinished.connect(self.analysis_parameters_changed)
        self._mw.reference_start_InputWidget.editingFinished.connect(self.analysis_parameters_changed)
        self._mw.reference_length_InputWidget.editingFinished.connect(self.analysis_parameters_changed)
        self._mw.analysis_period_InputWidget.editingFinished.connect(self.analysis_parameters_changed)
        self._mw.refocus_interval_LineEdit.editingFinished.connect(self.analysis_parameters_changed)
        self._mw.odmr_refocus_interval_LineEdit.editingFinished.connect(self.analysis_parameters_changed)

        self.seq_parameters_changed()
        self.analysis_parameters_changed()
        self.binning_changed()

#
#        self._mw.actionSave_Data.triggered.connect(self.save_clicked)

        self._mw.fit_PushButton.clicked.connect(self.fit_clicked)


    def _deactivate_analysis_ui(self, e):
        """ Disconnects the configuration for 'Analysis' Tab.

        @param Fysom.event e: Event Object of Fysom
        """

        self.run_stop_clicked(False)

        # disconnect signals
#        self._mw.idle_RadioButton.toggled.disconnect()
#        self._mw.run_RadioButton.toggled.disconnect()
        self._pulsed_measurement_logic.signal_laser_plot_updated.disconnect()
        self._pulsed_measurement_logic.signal_signal_plot_updated.disconnect()
        self._pulsed_measurement_logic.measuring_error_plot_updated.disconnect()
        self._mw.numlaser_InputWidget.editingFinished.disconnect()
        #self._mw.lasertoshow_spinBox.valueChanged.disconnect()
        self._mw.laser_to_show_ComboBox.activated.disconnect()

#    def idle_clicked(self):
#        """ Stopp the scan if the state has switched to idle. """
#        self._pulsed_measurement_logic.stop_pulsed_measurement()
#        self._mw.mw_frequency_InputWidget.setEnabled(True)
#        self._mw.mw_power_InputWidget.setEnabled(True)
#        self._mw.binning_doubleSpinBox.setEnabled(True)
#        self._mw.pull_data_pushButton.setEnabled(False)

    def run_stop_clicked(self,isChecked):
        """ Manages what happens if pulsed measurement is started or stopped.

        @param bool enabled: start scan if that is possible
        """

        #Firstly stop any scan that might be in progress
        self._pulsed_measurement_logic.stop_pulsed_measurement()
        #Then if enabled. start a new scan.

        if isChecked:
            #self._mw.signal_plot_ViewWidget.clear()
            self._mw.mw_frequency_InputWidget.setEnabled(False)
            self._mw.mw_power_InputWidget.setEnabled(False)
            self._mw.binning_doubleSpinBox.setEnabled(False)
            self._mw.action_pull_data.setEnabled(True)
            self._pulsed_measurement_logic.start_pulsed_measurement()
            self._mw.action_continue_pause.setEnabled(True)
            if not self._mw.action_continue_pause.isChecked():
                self._mw.action_continue_pause.toggle()

        else:
            self._pulsed_measurement_logic.stop_pulsed_measurement()
            self._mw.mw_frequency_InputWidget.setEnabled(True)
            self._mw.mw_power_InputWidget.setEnabled(True)
            self._mw.binning_doubleSpinBox.setEnabled(True)
            self._mw.action_pull_data.setEnabled(False)
            self._mw.action_continue_pause.setEnabled(False)



    def continue_pause_clicked(self,isChecked):
        """ Continues and pauses the measurement. """

        if isChecked:
            #self._mw.action_continue_pause.toggle()

            self._mw.action_run_stop.setChecked(True)


        else:
            #self._mw.action_continue_pause.toggle

            self._mw.action_run_stop.setChecked(False)


    def pull_data_clicked(self):
        self._pulsed_measurement_logic.manually_pull_data()
        return

    def save_clicked(self):
        self._pulsed_measurement_logic._save_data()
        return

    def fit_clicked(self):
		# clear old fit results in the text box        self._mw.fit_result_TextBrowser.clear()
        # remove old fit from the graph
        self._mw.signal_plot_ViewWidget.removeItem(self.fit_image)
        # get selected fit function from the ComboBox
        current_fit_function = self._mw.fit_function_ComboBox.currentText()

        fit_x, fit_y, fit_result = self._pulsed_measurement_logic.do_fit(current_fit_function)

        # plot the fit only if there is data available

        if fit_x != [] and fit_x != []:

            self.fit_image = pg.PlotDataItem(fit_x, fit_y,pen='r')
            self._mw.signal_plot_ViewWidget.addItem(self.fit_image,pen='r')

        self._mw.fit_result_TextBrowser.setPlainText(fit_result)

        return
    def refresh_lasertrace_plot(self):
        ''' This method refreshes the xy-plot image
        '''
        self.lasertrace_image.setData(self._pulsed_measurement_logic.laser_plot_x, self._pulsed_measurement_logic.laser_plot_y)

    def refresh_signal_plot(self):
        ''' This method refreshes the xy-matrix image
        '''

        #### dealing with the error bars
        if self._mw.show_errorbars_CheckBox.isChecked():
            # calculate optimal beam width for the error bars
            beamwidth = 1e99
            for i in range(len(self._pulsed_measurement_logic.tau_array)-1):
                width = self._pulsed_measurement_logic.tau_array[i+1] - self._pulsed_measurement_logic.tau_array[i]
                width = width/10
                if width <= beamwidth:
                    beamwidth = width
            # create ErrorBarItem
            self.signal_image_error_bars.setData(x=self._pulsed_measurement_logic.signal_plot_x, y=self._pulsed_measurement_logic.signal_plot_y, top=self._pulsed_measurement_logic.measuring_error,bottom=self._pulsed_measurement_logic.measuring_error,beam=beamwidth)
            if not self.errorbars_present:
                #print ('add erro')
                self._mw.signal_plot_ViewWidget.addItem(self.signal_image_error_bars)
                self.errorbars_present = True
        else:
            if self.errorbars_present:
                #print ('remove eror')
                self._mw.signal_plot_ViewWidget.removeItem(self.signal_image_error_bars)
                self.errorbars_present = False
            else:
                pass


        self.signal_image.setData(self._pulsed_measurement_logic.signal_plot_x, self._pulsed_measurement_logic.signal_plot_y)
        self.fft_image.setData(self._pulsed_measurement_logic.signal_plot_x, self._pulsed_measurement_logic.signal_plot_y)




    def refresh_measuring_error_plot(self):

        #print(self._pulsed_measurement_logic.measuring_error)
        self.measuring_error_image.setData(self._pulsed_measurement_logic.signal_plot_x, self._pulsed_measurement_logic.measuring_error)
    def refresh_elapsed_time(self):
        ''' This method refreshes the elapsed time and sweeps of the measurement
        '''
        self._mw.elapsed_time_label.setText(self._pulsed_measurement_logic.elapsed_time_str)
        self._mw.elapsed_sweeps_LCDNumber.display(self._pulsed_measurement_logic.elapsed_sweeps)

    def show_external_mw_source_checked(self):
        if self._mw.turn_off_external_mw_source_CheckBox.isChecked():

            self._mw.mw_frequency_Label.setVisible(False)
            self._mw.mw_frequency_InputWidget.setVisible(False)
            self._mw.mw_power_Label.setVisible(False)
            self._mw.mw_power_InputWidget.setVisible(False)
        else:
            self._mw.mw_frequency_Label.setVisible(True)
            self._mw.mw_frequency_InputWidget.setVisible(True)
            self._mw.mw_power_Label.setVisible(True)
            self._mw.mw_power_InputWidget.setVisible(True)


    def show_tau_editor(self):
        if self._mw.tau_defined_in_sequence_CheckBox.isChecked():
            self._mw.tau_start_Label.setVisible(False)
            self._mw.tau_start_InputWidget.setVisible(False)
            self._mw.tau_increment_Label.setVisible(False)
            self._mw.tau_increment_InputWidget.setVisible(False)
        else:
            self._mw.tau_start_Label.setVisible(True)
            self._mw.tau_start_InputWidget.setVisible(True)
            self._mw.tau_increment_Label.setVisible(True)
            self._mw.tau_increment_InputWidget.setVisible(True)

    def show_fft_plot(self):
        if self._mw.show_fft_plot_CheckBox.isChecked():
            self._mw.fft_PlotWidget.setVisible(True)
        else:
            self._mw.fft_PlotWidget.setVisible(False)

    def binning_changed(self):
        binning_s = self._mw.binning_doubleSpinBox.value()/1e9
        self._pulsed_measurement_logic.fast_counter_binwidth = binning_s
        self._pulsed_measurement_logic.configure_fast_counter()
        self._mw.binning_doubleSpinBox.setValue(self._pulsed_measurement_logic.fast_counter_binwidth*1e9)

    def lasernum_changed(self):
        self._mw.laser_to_show_ComboBox.clear()
        self._mw.laser_to_show_ComboBox.addItem('sum')
        for ii in range(int(self._mw.numlaser_InputWidget.text())):
            self._mw.laser_to_show_ComboBox.addItem(str(1+ii))
        laser_num = int(self._mw.numlaser_InputWidget.text())
        self._pulsed_measurement_logic.number_of_lasers = laser_num
        self._pulsed_measurement_logic.configure_fast_counter()
        self.seq_parameters_changed()

    def seq_parameters_changed(self):
        laser_num = int(self._mw.numlaser_InputWidget.text())
        tau_start = int(self._mw.tau_start_InputWidget.text())
        tau_incr = int(self._mw.tau_increment_InputWidget.text())
        mw_frequency = float(self._mw.mw_frequency_InputWidget.text())
        mw_power = float(self._mw.mw_power_InputWidget.text())
        #self._mw.lasertoshow_spinBox.setRange(0, laser_num)

        current_laser = self._mw.laser_to_show_ComboBox.currentText()

        if current_laser == 'sum':
            laser_show = 0
        else:
            laser_show = int(current_laser)

        if (laser_show > laser_num):
            self._mw.laser_to_show_ComboBox.setEditText('sum')
            laser_show = 0

        tau_array = np.array(range(tau_start, tau_start + tau_incr*laser_num, tau_incr))
        self._pulsed_measurement_logic.tau_array = tau_array
        self._pulsed_measurement_logic.number_of_lasers = laser_num
        self._pulsed_measurement_logic.display_pulse_no = laser_show
        self._pulsed_measurement_logic.mykrowave_freq = mw_frequency
        self._pulsed_measurement_logic.mykrowave_power = mw_power
        return


    def analysis_parameters_changed(self):
        sig_start = int(self._mw.signal_start_InputWidget.text())
        sig_length = int(self._mw.signal_length_InputWidget.text())
        ref_start = int(self._mw.reference_start_InputWidget.text())
        ref_length = int(self._mw.reference_length_InputWidget.text())
        timer_interval = float(self._mw.analysis_period_InputWidget.text())
        refocus_timer_interval = float(self._mw.refocus_interval_LineEdit.text())
        odmr_refocus_timer_interval = float(self._mw.odmr_refocus_interval_LineEdit.text())
        self.signal_start_bin = sig_start
        self.signal_width_bins = sig_length
        self.norm_start_bin = ref_start
        self.norm_width_bins = ref_length
        self.sig_start_line.setValue(sig_start*self._pulsed_measurement_logic.fast_counter_binwidth)
        self.sig_end_line.setValue((sig_start+sig_length)*self._pulsed_measurement_logic.fast_counter_binwidth)
        self.ref_start_line.setValue(ref_start*self._pulsed_measurement_logic.fast_counter_binwidth)
        self.ref_end_line.setValue((ref_start+ref_length)*self._pulsed_measurement_logic.fast_counter_binwidth)
        self._pulsed_measurement_logic.signal_start_bin = sig_start
        self._pulsed_measurement_logic.signal_width_bin = sig_length
        self._pulsed_measurement_logic.norm_start_bin = ref_start
        self._pulsed_measurement_logic.norm_width_bin = ref_length
        self._pulsed_measurement_logic.change_timer_interval(timer_interval)
        self._pulsed_measurement_logic.change_refocus_timer_interval(refocus_timer_interval)
        self._pulsed_measurement_logic.change_odmr_refocus_timer_interval(odmr_refocus_timer_interval)
        return

    def check_input_with_samplerate(self):
        pass





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

    ###########################################################################
    ###    Methods related to Settings for the 'Pulse Extraction' Tab:      ###
    ###########################################################################

    #FIXME: Implement the setting for 'Pulse Extraction' tab.

    def _activate_pulse_extraction_settings_ui(self, e):
        """ Initialize, connect and configure the Settings of the
        'Sequence Generator' Tab.

        @param Fysom.event e: Event Object of Fysom
        """

        pass

    def _deactivate_pulse_extraction_settings_ui(self, e):
        """ Disconnects the configuration of the Settings for the
        'Sequence Generator' Tab.

        @param Fysom.event e: Event Object of Fysom
        """

        pass


    ###########################################################################
    ###          Methods related to the Tab 'Pulse Extraction':             ###
    ###########################################################################

    #FIXME: Implement the 'Pulse Extraction' tab.

    def _activate_pulse_extraction_ui(self, e):
        """ Initialize, connect and configure the 'Pulse Extraction' Tab.

        @param Fysom.event e: Event Object of Fysom
        """
        pass

    def _deactivate_pulse_extraction_ui(self, e):
        """ Disconnects the configuration for 'Pulse Extraction' Tab.

        @param Fysom.event e: Event Object of Fysom
        """
        pass