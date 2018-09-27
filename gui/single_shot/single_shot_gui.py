# -*- coding: utf-8 -*-

"""
This file contains the GUI for control of a Gated Counter.

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
import os
import pyqtgraph as pg

from core.module import Connector
from core.util import units
from gui.guibase import GUIBase
from gui.colordefs import QudiPalettePale as palette
from gui.colordefs import QudiPalette as palettedark
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic


class SingleShotMainWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_single_shot_gui.ui')

        # Load it
        super(SingleShotMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()



class SingleShotGui(GUIBase):
    """ Main GUI for the Gated Counting. """

    _modclass = 'SingleShotGui'
    _modtype = 'gui'

    ## declare connectors
    singleshotlogic = Connector(interface='SingleShotLogic')

    # Define the signals

    sigSaveMeasurement = QtCore.Signal(str)
    sigDoFit = QtCore.Signal(str)
    sigCounterSettingsChanged = QtCore.Signal(dict)
    sigAnalyzeModeChanged = QtCore.Signal(str)
    sigNumverBinsChanged = QtCore.Signal(int)
    sigSequenceLengthChanged = QtCore.Signal(float)
    sigAnalysisPeriodChanged = QtCore.Signal(float)
    sigNormalizedChanged = QtCore.Signal(bool)
    ThresholdChanged = QtCore.Signal(dict)
    sigToggleSSR = QtCore.Signal(bool)

    # FIXME: Add status variables here

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)


    def on_activate(self, e=None):
        """ Definition and initialisation of the GUI.

        @param object e: Fysom.event object from Fysom class.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """

        self._mw = SingleShotMainWindow()
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)

        self._gp = self._mw.count_trace_PlotWidget
        self._gp.setLabel('left', 'Counts', units='counts/s')
        self._gp.setLabel('bottom', 'time', units='s')

        # Create an empty plot curve to be filled later, set its pen
        self._trace1 = self._gp.plot()
        self._trace1.setPen(palette.c1)

        self._hp = self._mw.histogram_PlotWidget
        self._hp.setLabel('left', 'Occurrences', units='#')
        self._hp.setLabel('bottom', 'Counts', units='counts/s')

        self._histoplot1 = pg.PlotCurveItem()
        self._histoplot1.setPen(palette.c1)
        self._hp.addItem(self._histoplot1)


        # Configure the fit of the data in the main pulse analysis display:
        self._fit_image = pg.PlotCurveItem()
        self._hp.addItem(self._fit_image)

        # setting the x axis length correctly
        self._gp.setXRange(0, 10)
        self._mw.hist_bins_SpinBox.setRange(1, 50)

        # set up the slider with the values of the logic:
        self._mw.hist_bins_Slider.setRange(1,50)
        self._mw.hist_bins_Slider.setSingleStep(1)

        # Setting default parameters
        self._mw.count_length_SpinBox.setValue(self.singleshotlogic().countlength)
        self._mw.count_per_readout_SpinBox.setValue(self.singleshotlogic().counts_per_readout)
        self._mw.hist_bins_SpinBox.setValue(self.singleshotlogic().num_bins)
        self._mw.hist_bins_Slider.setValue(self.singleshotlogic().num_bins)
        self._mw.sequence_length_DSpinBox.setValue(self.singleshotlogic().sequence_length)
        self._mw.analysis_period_DSpinBox.setValue(self.singleshotlogic().timer_interval)
        self._mw.normalized_CheckBox.setChecked(self.singleshotlogic().normalized)

        self._mw.init_threshold0_DSpinBox.setValue(self.singleshotlogic().init_threshold0)
        self._mw.init_threshold1_DSpinBox.setValue(self.singleshotlogic().init_threshold1)
        self._mw.ana_threshold0_DSpinBox.setValue(self.singleshotlogic().ana_threshold0)
        self._mw.ana_threshold1_DSpinBox.setValue(self.singleshotlogic().ana_threshold1)



        #self._mw.action_pull_data.setEnabled(False)


        self._mw.analyze_mode_ComboBox.addItem('full')
        self._mw.analyze_mode_ComboBox.addItem('bright')
        self._mw.analyze_mode_ComboBox.addItem('dark')

        # Connecting user interactions
        # set at first the action buttons in the tab
        self._mw.action_run_stop.triggered.connect(self.start_stop_clicked)
        self._mw.action_pull_data.triggered.connect(self.pull_data_clicked)
        self._mw.save_measurement_Action.triggered.connect(self.save_clicked)

        self._mw.count_length_SpinBox.editingFinished.connect(self.ssr_counter_settings_changed)
        self._mw.count_per_readout_SpinBox.editingFinished.connect(self.ssr_counter_settings_changed)
        self._mw.analyze_mode_ComboBox.currentIndexChanged.connect(self.analyze_mode_changed)

        self._mw.hist_bins_Slider.valueChanged.connect(self.num_bins_slider_changed)
        self._mw.hist_bins_SpinBox.editingFinished.connect(self.num_bins_changed)
        self._mw.sequence_length_DSpinBox.editingFinished.connect(self.sequence_length_changed)
        self._mw.analysis_period_DSpinBox.editingFinished.connect(self.analysis_period_changed)
        self._mw.normalized_CheckBox.stateChanged.connect(self.normalized_changed)

        self._mw.init_threshold0_DSpinBox.editingFinished.connect(self.threshold_changed)
        self._mw.init_threshold1_DSpinBox.editingFinished.connect(self.threshold_changed)
        self._mw.ana_threshold0_DSpinBox.editingFinished.connect(self.threshold_changed)
        self._mw.ana_threshold1_DSpinBox.editingFinished.connect(self.threshold_changed)

        # Connect the signal
        self.sigCounterSettingsChanged.connect(self.singleshotlogic().set_ssr_counter_settings,
                                          QtCore.Qt.QueuedConnection)
        self.sigAnalyzeModeChanged.connect(self.singleshotlogic().set_analyze_mode,
                                               QtCore.Qt.QueuedConnection)
        self.sigNumverBinsChanged.connect(self.singleshotlogic().set_number_of_histogram_bins,
                                          QtCore.Qt.QueuedConnection)
        self.sigSequenceLengthChanged.connect(self.singleshotlogic().set_sequence_length,
                                          QtCore.Qt.QueuedConnection)
        self.sigAnalysisPeriodChanged.connect(self.singleshotlogic().set_analysis_period,
                                              QtCore.Qt.QueuedConnection)
        self.sigNormalizedChanged.connect(self.singleshotlogic().set_normalized,
                                          QtCore.Qt.QueuedConnection)
        self.ThresholdChanged.connect(self.singleshotlogic().set_threshold,
                                          QtCore.Qt.QueuedConnection)
        self.sigToggleSSR.connect(self.singleshotlogic().toggle_ssr_measurement,
                                  QtCore.Qt.QueuedConnection)
        self.sigSaveMeasurement.connect(self.singleshotlogic().save_measurement,
                                        QtCore.Qt.QueuedConnection)
        self.sigDoFit.connect(self.singleshotlogic().do_fit,
                                        QtCore.Qt.QueuedConnection)

        self.singleshotlogic().sigStatusSSRUpdated.connect(self.measurement_status_updated,
                                                     QtCore.Qt.QueuedConnection)
        self.singleshotlogic().sigSSRCounterSettingsUpdated.connect(self.ssr_counter_settings_updated,
                                                     QtCore.Qt.QueuedConnection)
        self.singleshotlogic().sigNumBinsUpdated.connect(self.num_bins_updated,
                                                     QtCore.Qt.QueuedConnection)
        self.singleshotlogic().sigSequenceLengthUpdated.connect(self.sequence_length_updated,
                                                         QtCore.Qt.QueuedConnection)
        self.singleshotlogic().sigAnalysisPeriodUpdated.connect(self.analysis_period_updated,
                                                                QtCore.Qt.QueuedConnection)
        self.singleshotlogic().sigNormalizedUpdated.connect(self.normalized_updated,
                                                                QtCore.Qt.QueuedConnection)
        self.singleshotlogic().sigThresholdUpdated.connect(self.threshold_updated,
                                                     QtCore.Qt.QueuedConnection)
        self.singleshotlogic().sigTraceUpdated.connect(self.trace_updated,
                                                     QtCore.Qt.QueuedConnection)
        self.singleshotlogic().sigHistogramUpdated.connect(self.histogram_updated,
                                                     QtCore.Qt.QueuedConnection)
        self.singleshotlogic().sigFitUpdated.connect(self.fit_updated,
                                                           QtCore.Qt.QueuedConnection)


    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._mw.action_run_stop.triggered.disconnect()
        self._mw.save_measurement_Action.triggered.disconnect()

        self._mw.count_length_SpinBox.editingFinished.disconnect()
        self._mw.count_per_readout_SpinBox.editingFinished.disconnect()
        self._mw.hist_bins_Slider.valueChanged.disconnect()
        self._mw.hist_bins_SpinBox.editingFinished.disconnect()
        self._mw.sequence_length_DSpinBox.editingFinished.disconnect()
        self._mw.analysis_period_DSpinBox.editingFinished.disconnect()
        self._mw.normalized_CheckBox.stateChanged.disconnect()
        self._mw.init_threshold0_DSpinBox.editingFinished.disconnect()
        self._mw.init_threshold1_DSpinBox.editingFinished.disconnect()
        self._mw.ana_threshold0_DSpinBox.editingFinished.disconnect()
        self._mw.ana_threshold1_DSpinBox.editingFinished.disconnect()

        # Connect the signal
        self.sigCounterSettingsChanged.disconnect()
        self.sigAnalyzeModeChanged.disconnect()
        self.sigNumverBinsChanged.disconnect()
        self.ThresholdChanged.disconnect()
        self.sigToggleSSR.disconnect()
        self.sigSaveMeasurement.disconnect()
        self.sigDoFit.disconnect()

        self.singleshotlogic().sigStatusSSRUpdated.disconnect()
        self.singleshotlogic().sigSSRCounterSettingsUpdated.disconnect()
        self.singleshotlogic().sigNumBinsUpdated.disconnect()
        self.singleshotlogic().sigThresholdUpdated.disconnect()
        self.singleshotlogic().sigTraceUpdated.disconnect()
        self.singleshotlogic().sigHistogramUpdated.disconnect()
        self._mw.close()

    def show(self):
        """ Make main window visible and put it above all other windows. """

        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

########################################### Send to Logic #########################################

    def start_stop_clicked(self, is_checked):
        if is_checked:
            self.sigToggleSSR.emit(True)
            self.measurement_status_updated(True)
        else:
            self.sigToggleSSR.emit(False)
            self.measurement_status_updated(False)
        return

    def pull_data_clicked(self):
        """ Pulls and analysis the data when the 'action_pull_data'-button is clicked. """
        self.singleshotlogic().manually_pull_data()
        return


    def save_clicked(self):
        """Saves the current data"""
        self._mw.save_measurement_Action.setEnabled(False)
        save_tag = self._mw.save_tag_LineEdit.text()
        self._mw.save_measurement_Action.setEnabled(True)
        self.sigSaveMeasurement.emit(save_tag)
        return


    def fit_clicked(self):
        """ Do the configured fit and show it in the sum plot """
        current_fit_function = self._mw.fit_methods_ComboBox.currentText()
        self.sigDoFit.emit(current_fit_function)
        return


    def ssr_counter_settings_changed(self):
        """ Handle the change of the count_length and send it to the measurement.
        """
        settings_dict = dict()
        settings_dict['countlength'] = self._mw.count_length_SpinBox.value()
        settings_dict['counts_per_readout'] = self._mw.count_per_readout_SpinBox.value()
        self.sigCounterSettingsChanged.emit(settings_dict)
        return

    def analyze_mode_changed(self):
        current_mode = self._mw.analyze_mode_ComboBox.currentText()
        self.sigAnalyzeModeChanged.emit(current_mode)
        return


    def num_bins_changed(self):
        """
        @param int num_bins: Number of bins to be set in the trace.

        This method is executed by both events, the valueChanged of the SpinBox
        and value changed in the Slider. Until now, there appears no infinite
        signal loop. It that occur one day, than this method has to be split
        in two seperate methods.
        """
        num_bins = self._mw.hist_bins_SpinBox.value()
        self.sigNumverBinsChanged.emit(num_bins)
        self._mw.hist_bins_SpinBox.blockSignals(True)
        self._mw.hist_bins_SpinBox.blockSignals(True)
        self._mw.hist_bins_Slider.setValue(num_bins)
        self._mw.hist_bins_SpinBox.blockSignals(False)
        self._mw.hist_bins_SpinBox.blockSignals(False)
        return


    def num_bins_slider_changed(self):
        """
        @param int num_bins: Number of bins to be set in the trace.

        This method is executed by both events, the valueChanged of the SpinBox
        and value changed in the Slider. Until now, there appears no infinite
        signal loop. It that occur one day, than this method has to be split
        in two seperate methods.
        """
        num_bins = self._mw.hist_bins_Slider.value()
        self.sigNumverBinsChanged.emit(num_bins)
        self._mw.hist_bins_SpinBox.blockSignals(True)
        self._mw.hist_bins_SpinBox.blockSignals(True)
        self._mw.hist_bins_SpinBox.setValue(num_bins)
        self._mw.hist_bins_SpinBox.blockSignals(False)
        self._mw.hist_bins_SpinBox.blockSignals(False)
        return

    def sequence_length_changed(self):
        self.sigSequenceLengthChanged.emit(self._mw.sequence_length_DSpinBox.value())
        return

    def analysis_period_changed(self):
        self.sigAnalysisPeriodChanged.emit(self._mw.analysis_period_DSpinBox.value())
        return

    def normalized_changed(self):
        self.sigNormalizedChanged.emit(self._mw.normalized_CheckBox.isChecked())
        return


    def threshold_changed(self):
        """
        @param int num_bins: Number of bins to be set in the trace.

        This method is executed by both events, the valueChanged of the SpinBox
        and value changed in the Slider. Until now, there appears no infinite
        signal loop. It that occur one day, than this method has to be split
        in two seperate methods.
        """
        threshold_dict = dict()
        threshold_dict['init_threshold0'] = self._mw.init_threshold0_DSpinBox.value()
        threshold_dict['init_threshold1'] = self._mw.init_threshold1_DSpinBox.value()
        threshold_dict['ana_threshold0'] = self._mw.ana_threshold0_DSpinBox.value()
        threshold_dict['ana_threshold1'] = self._mw.ana_threshold1_DSpinBox.value()
        self.ThresholdChanged.emit(threshold_dict)
        return


    ################################# Update Methods #############################

    def measurement_status_updated(self, is_running):
        # block signals
        self._mw.action_run_stop.blockSignals(True)
        if is_running:
            # clear the plots
            self._mw.fit_param_TextEdit.clear()
            self._trace1.clear()
            self._mw.count_length_SpinBox.setEnabled(False)
            self._mw.count_per_readout_SpinBox.setEnabled(False)
            #self._mw.action_pull_data.setEnabled(True)
            self._mw.action_run_stop.blockSignals(True)
            if not self._mw.action_run_stop.isChecked():
                self._mw.action_run_stop.toggle()

        else:
            self._mw.count_length_SpinBox.setEnabled(True)
            self._mw.count_per_readout_SpinBox.setEnabled(True)
            #self._mw.action_pull_data.setEnabled(False)
            if self._mw.action_run_stop.isChecked():
                self._mw.action_run_stop.toggle()
        self._mw.action_run_stop.blockSignals(False)
        return

    def ssr_counter_settings_updated(self, settings_dict):
        """ Handle the change of the count_length and send it to the measurement.
        """
        # block the signals
        self._mw.count_length_SpinBox.blockSignals(True)
        self._mw.count_per_readout_SpinBox.blockSignals(True)

        if 'countlength' in settings_dict:
            self._mw.count_length_SpinBox.setValue(settings_dict['countlength'])
        if 'counts_per_readout' in settings_dict:
            self._mw.count_per_readout_SpinBox.setValue(settings_dict['counts_per_readout'])

        # unblock the signals
        self._mw.count_length_SpinBox.blockSignals(False)
        self._mw.count_per_readout_SpinBox.blockSignals(False)
        return

    def analyze_mode_updated(self, mode):
        # block the signals
        self._mw.analyze_mode_ComboBox.blockSignals(True)
        index = self._mw.analyze_mode_ComboBox.findText(mode)
        self._mw.analyze_mode_ComboBox.setCurrentIndex(index)
        # unblock the signals
        self._mw.analyze_mode_ComboBox.blockSignals(False)
        return


    def num_bins_updated(self, num_bins):
        """
        @param int num_bins: Number of bins to be set in the trace.

        This method is executed by both events, the valueChanged of the SpinBox
        and value changed in the Slider. Until now, there appears no infinite
        signal loop. It that occur one day, than this method has to be split
        in two seperate methods.
        """
        #block the signals
        self._mw.hist_bins_SpinBox.blockSignals(True)
        self._mw.hist_bins_SpinBox.blockSignals(True)

        self._mw.hist_bins_SpinBox.setValue(num_bins)
        self._mw.hist_bins_Slider.setValue(num_bins)

        #unblock the signals
        self._mw.hist_bins_SpinBox.blockSignals(False)
        self._mw.hist_bins_SpinBox.blockSignals(False)
        return


    def sequence_length_updated(self, sequence_length):
        #block the signals
        self._mw.sequence_length_DSpinBox.blockSignals(True)
        self._mw.sequence_length_DSpinBox.setValue(sequence_length)
        #unblock the signals
        self._mw.sequence_length_DSpinBox.blockSignals(False)
        return


    def analysis_period_updated(self, analysis_period):
        #block the signals
        self._mw.analysis_period_DSpinBox.blockSignals(True)
        self._mw.analysis_period_DSpinBox.setValue(analysis_period)
        #unblock the signals
        self._mw.analysis_period_DSpinBox.blockSignals(False)
        return

    def normalized_updated(self, norm):
        # block the signals
        self._mw.normalized_CheckBox.blockSignals(True)
        self._mw.normalized_CheckBox.setChecked(norm)
        # unblock the signals
        self._mw.normalized_CheckBox.blockSignals(False)
        return

    def threshold_updated(self, threshold_dict):
        """
        @param int num_bins: Number of bins to be set in the trace.

        This method is executed by both events, the valueChanged of the SpinBox
        and value changed in the Slider. Until now, there appears no infinite
        signal loop. It that occur one day, than this method has to be split
        in two seperate methods.
        """
        # block the signals
        self._mw.init_threshold0_DSpinBox.blockSignals(True)
        self._mw.init_threshold1_DSpinBox.blockSignals(True)
        self._mw.ana_threshold0_DSpinBox.blockSignals(True)
        self._mw.ana_threshold1_DSpinBox.blockSignals(True)

        if 'init_threshold0' in threshold_dict:
            self._mw.init_threshold0_DSpinBox.setValue(threshold_dict['init_threshold0'])
        if 'init_threshold1' in threshold_dict:
            self._mw.init_threshold1_DSpinBox.setValue(threshold_dict['init_threshold1'])
        if 'ana_threshold0' in threshold_dict:
            self._mw.ana_threshold0_DSpinBox.setValue(threshold_dict['ana_threshold0'])
        if 'ana_threshold1' in threshold_dict:
            self._mw.ana_threshold1_DSpinBox.setValue(threshold_dict['ana_threshold1'])

        #unblock the signals
        self._mw.init_threshold0_DSpinBox.blockSignals(False)
        self._mw.init_threshold1_DSpinBox.blockSignals(False)
        self._mw.ana_threshold0_DSpinBox.blockSignals(False)
        self._mw.ana_threshold1_DSpinBox.blockSignals(False)
        return


    def trace_updated(self, x_data, y_data, spin_flip_prob, spin_flip_error,  lost_events):
        """ The function that grabs the data and sends it to the plot. """
        self._trace1.setData(x=x_data, y=y_data)
        self._mw.spin_flip_prob_DSpinBox.setValue(spin_flip_prob*100)
        self._mw.spin_flip_error_DSpinBox.setValue(spin_flip_error * 100)
        self._mw.lost_events_SpinBox.setValue(lost_events)
        # autorange the plot
        if len(x_data) > 2:
            self._gp.setXRange(x_data[0], x_data[-1])
        else:
            self._gp.setXRange(0, 10)
        return


    def results_updated(self, spin_flip_prob, fidelity_left, fidelity_right):
        """ Update the spin flip probability and the fidelities. """

        self._mw.spin_flip_prob_DSpinBox.setValue(spin_flip_prob*100)
        self._mw.fidelity_left_DSpinBox.setValue(fidelity_left*100)
        self._mw.fidelity_right_DSpinBox.setValue(fidelity_right*100)
        return

    def histogram_updated(self, hist_data):
        """ Update procedure for the histogram to display the new data. """

        self._histoplot1.setData(x=hist_data[0], y=hist_data[1],
                                 stepMode=True, fillLevel=0,
                                 brush=palettedark.c1)
        return


    def fit_updated(self, fit_param_dict):

        self._mw.fit_param_TextEdit.clear()
        self._fit_image.setData(x=fit_param_dict['fit_x'], y=fit_param_dict['fit_y'],
                                pen=pg.mkPen(palette.c2, width=2))
        if fit_param_dict['fit_result'] is None:
            fit_result = 'No Fit parameter passed.'
        else:
            fit_para = fit_param_dict['fit_result']
            fit_result = units.create_formatted_output(fit_para.result_str_dict)
        self._mw.fit_param_TextEdit.setPlainText(fit_result)
        self._mw.fidelity_right_DSpinBox.setValue(fit_param_dict['fidelity_right'] * 100)
        self._mw.fidelity_left_DSpinBox.setValue(fit_param_dict['fidelity_left'] * 100)
        self._mw.fidelity_total_DSpinBox.setValue(fit_param_dict['fidelity_total'] * 100)
        return

