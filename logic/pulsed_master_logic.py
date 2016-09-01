# -*- coding: utf-8 -*-
"""
Master logic to combine sequence_generator_logic and pulsed_measurement_logic to be
used with a single GUI.

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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from logic.generic_logic import GenericLogic
from pyqtgraph.Qt import QtCore
from collections import OrderedDict
import numpy as np


class PulsedMasterLogic(GenericLogic):
    """
    This logic module controls the sequence/waveform generation and management via
    sequence_generator_logic and pulsed measurements via pulsed_measurement_logic.
    Basically glue logic to pass information between logic modules.
    """
    # pulsed_measurement_logic signals
    sigNumOfLasersChanged = QtCore.Signal(int)
    sigFcBinningChanged = QtCore.Signal(float)
    sigXAxisChanged = QtCore.Signal(np.ndarray)
    sigExtMicrowaveChanged = QtCore.Signal(float, float, bool)
    sigAnalysisWindowsChanged = QtCore.Signal(int, int, int, int)
    sigLaserTriggerDelayChanged = QtCore.Signal(float)
    sigAlternatingChanged = QtCore.Signal(bool)
    sigIgnoreLaserIndicesChanged = QtCore.Signal(list)
    sigDoFit = QtCore.Signal(str, np.ndarray, np.ndarray)
    sigAnalysisIntervalChanged = QtCore.Signal(float)
    sigManuallyPullData = QtCore.Signal()
    sigStartMeasurement = QtCore.Signal()
    sigStopMeasurement = QtCore.Signal()
    sigPauseMeasurement = QtCore.Signal()
    sigContinueMeasurement = QtCore.Signal()
    sigClearPulseGenerator = QtCore.Signal()
    sigTogglePulseGenerator = QtCore.Signal(bool)
    sigPulserActivationConfigChanged = QtCore.Signal(str)
    sigPulserSampleRateChanged = QtCore.Signal(float)
    sigPulserAmplitudeChanged = QtCore.Signal(dict)
    sigUploadAssetToPulser = QtCore.Signal(str)
    sigLoadAssetIntoChannels = QtCore.Signal(str, dict)
    sigRequestLaserPulse = QtCore.Signal(int, bool)

    # sequence_generator_logic signals
    sigSavePulseBlock = QtCore.Signal(str, object)
    sigSaveBlockEnsemble = QtCore.Signal(str, object)
    sigDeletePulseBlock = QtCore.Signal(str)
    sigDeleteBlockEnsemble = QtCore.Signal(str)
    sigLoadPulseBlock = QtCore.Signal(str)
    sigLoadBlockEnsemble = QtCore.Signal(str)
    sigSampleBlockEnsemble = QtCore.Signal(str)
    sigGeneratorChannelConfigChanged = QtCore.Signal(list)
    sigGeneratorLaserChannelChanged = QtCore.Signal(str)
    sigGeneratorSampleRateChanged = QtCore.Signal(float)
    sigGeneratorAmplitudeChanged = QtCore.Signal(dict)

    # signals for master module (i.e. GUI)
    sigPulserSettingsUpdated = QtCore.Signal(str, list, float, dict)
    sigPulserRunningUpdated = QtCore.Signal(bool)
    sigMeasurementStatusUpdated = QtCore.Signal(str)
    sigMeasurementDataUpdated = QtCore.Signal(np.ndarray, np.ndarray, np.ndarray)
    sigFitUpdated = QtCore.Signal(np.ndarray, np.ndarray, dict)
    sigPulseBlocksUpdated = QtCore.Signal(list)
    sigBlockEnsemblesUpdated = QtCore.Signal(list)
    sigCurrentPulseBlockUpdated = QtCore.Signal(object)
    sigCurrentBlockEnsembleUpdated = QtCore.Signal(object)
    sigBlockEnsembleSampled = QtCore.Signal()
    sigGeneratorSettingsUpdated = QtCore.Signal(str, list, float, dict, str)
    sigUploadedAssetsUpdated = QtCore.Signal(list)
    sigLoadedAssetUpdated = QtCore.Signal(str)
    sigLaserPulseUpdated = QtCore.Signal(np.ndarray)

    _modclass = 'pulsedmasterlogic'
    _modtype = 'logic'

    # declare connectors
    _in = {'pulsedmeasurementlogic': 'PulsedMeasurementLogic',
           'sequencegenerator': 'SequenceGeneratorLogic',
           }
    _out = {'pulsedmasterlogic': 'PulsedMasterLogic'}

    def __init__(self, **kwargs):
        """ Create PulsedMasterLogic object with connectors.

          @param dict kwargs: optional parameters
        """
        super().__init__(**kwargs)

    def on_activate(self, e):
        """ Initialisation performed during activation of the module.

          @param object e: Fysom state change event
        """
        self._measurement_logic = self.connector['in']['pulsedmeasurementlogic']['object']
        self._generator_logic = self.connector['in']['sequencegenerator']['object']

        # Signals controlling the pulsed_measurement_logic
        self.sigNumOfLasersChanged.connect(self._measurement_logic.set_num_of_lasers,
                                           QtCore.Qt.QueuedConnection)
        self.sigFcBinningChanged.connect(self._measurement_logic.set_fc_binning,
                                         QtCore.Qt.QueuedConnection)
        self.sigXAxisChanged.connect(self._measurement_logic.set_measurement_ticks_list,
                                     QtCore.Qt.QueuedConnection)
        self.sigExtMicrowaveChanged.connect(self._measurement_logic.set_microwave_params,
                                            QtCore.Qt.QueuedConnection)
        self.sigPulserActivationConfigChanged.connect(self._measurement_logic.set_activation_config,
                                                      QtCore.Qt.QueuedConnection)
        self.sigPulserSampleRateChanged.connect(self._measurement_logic.set_sample_rate,
                                                QtCore.Qt.QueuedConnection)
        self.sigPulserAmplitudeChanged.connect(self._measurement_logic.set_amplitude_dict,
                                               QtCore.Qt.QueuedConnection)
        self.sigAnalysisWindowsChanged.connect(self._measurement_logic.set_analysis_windows,
                                               QtCore.Qt.QueuedConnection)
        self.sigLaserTriggerDelayChanged.connect(self._measurement_logic.set_laser_trigger_delay,
                                                 QtCore.Qt.QueuedConnection)
        self.sigAlternatingChanged.connect(self._measurement_logic.set_alternating,
                                           QtCore.Qt.QueuedConnection)
        self.sigIgnoreLaserIndicesChanged.connect(self._measurement_logic.set_ignore_laser_indices,
                                                  QtCore.Qt.QueuedConnection)
        self.sigDoFit.connect(self._measurement_logic.do_fit, QtCore.Qt.QueuedConnection)
        self.sigAnalysisIntervalChanged.connect(self._measurement_logic.set_timer_interval,
                                                QtCore.Qt.QueuedConnection)
        self.sigManuallyPullData.connect(self._measurement_logic.manually_pull_data,
                                         QtCore.Qt.QueuedConnection)
        self.sigStartMeasurement.connect(self._measurement_logic.start_pulsed_measurement,
                                         QtCore.Qt.QueuedConnection)
        self.sigStopMeasurement.connect(self._measurement_logic.stop_pulsed_measurement,
                                        QtCore.Qt.QueuedConnection)
        self.sigPauseMeasurement.connect(self._measurement_logic.pause_pulsed_measurement,
                                         QtCore.Qt.QueuedConnection)
        self.sigContinueMeasurement.connect(self._measurement_logic.continue_pulsed_measurement,
                                            QtCore.Qt.QueuedConnection)
        self.sigTogglePulseGenerator.connect(self._measurement_logic.switch_pulse_generator_on_off,
                                             QtCore.Qt.QueuedConnection)
        self.sigClearPulseGenerator.connect(self._measurement_logic.clear_pulser,
                                            QtCore.Qt.QueuedConnection)
        self.sigUploadAssetToPulser.connect(self._measurement_logic.upload_asset,
                                            QtCore.Qt.QueuedConnection)
        self.sigLoadAssetIntoChannels.connect(self._measurement_logic.load_asset,
                                              QtCore.Qt.QueuedConnection)
        self.sigRequestLaserPulse.connect(self._measurement_logic.get_laserpulse,
                                          QtCore.Qt.QueuedConnection)


        self.sigSavePulseBlock.connect(self._generator_logic.save_block, QtCore.Qt.QueuedConnection)
        self.sigSaveBlockEnsemble.connect(self._generator_logic.save_ensemble,
                                          QtCore.Qt.QueuedConnection)
        self.sigLoadPulseBlock.connect(self._generator_logic.get_pulse_block,
                                       QtCore.Qt.QueuedConnection)
        self.sigLoadBlockEnsemble.connect(self._generator_logic.get_pulse_block_ensemble,
                                          QtCore.Qt.QueuedConnection)
        self.sigSampleBlockEnsemble.connect(self._generator_logic.sample_pulse_block_ensemble,
                                            QtCore.Qt.QueuedConnection)
        self.sigGeneratorChannelConfigChanged.connect(self._generator_logic.set_activation_config,
                                                      QtCore.Qt.QueuedConnection)
        self.sigGeneratorLaserChannelChanged.connect(self._generator_logic.set_laser_channel,
                                                     QtCore.Qt.QueuedConnection)
        self.sigGeneratorSampleRateChanged.connect(self._generator_logic.set_sample_rate,
                                                   QtCore.Qt.QueuedConnection)
        self.sigGeneratorAmplitudeChanged.connect(self._generator_logic.set_amplitude_list,
                                                  QtCore.Qt.QueuedConnection)

        self.manual_xaxis_def = False
        self.xaxis_start = 0.
        self.xaxis_increment = 1.
        self.manual_laser_def = False

    #######################################################################
    ###             Pulsed measurement methods                          ###
    #######################################################################

    def num_laserpulses_changed(self, num_of_laserpulses):
        """
        Sets the number of laserpulses via pulsed_measurement_logic
        """
        self.sigNumOfLasersChanged.emit(num_of_laserpulses)
        if manual_xaxis_def:
            self.x_axis_changed()
        return

    def fc_binwidth_changed(self, binwidth_s):
        """
        Sets the fast counter binwidth via pulsed_measurement_logic
        """
        self.sigFcBinningChanged.emit(binwidth_s)
        return

    def x_axis_changed(self, x_array=None):
        """
        Sets the measurement x-axis via pulsed_measurement_logic

        @param x_array:
        @return:
        """
        if manual_xaxis_def:
            laser_num = self._measurement_logic.number_of_lasers
            x_array = np.linspace(self.xaxis_start,
                                  self.xaxis_start + (self.xaxis_increment * (laser_num - 1)),
                                  laser_num)
        elif x_array is None:
            self.log.warning('x_axis_changed was called without optional "x_array" argument and '
                           'without setting attribute "manual_xaxis_def" to True. So x-axis is not '
                           'properly defined and will default to laser pulse indexing.')
            laser_num = self._measurement_logic.number_of_lasers
            x_array = np.linspace(0., laser_num - 1, laser_num)
        self.sigXAxisChanged.emit(x_array)
        return

    def ext_microwave_changed(self, use_ext_mw, mw_freq_hz, mw_power_dbm):
        """
        Sets the external microwave parameters via pulsed_measurement_logic

        @param use_ext_mw:
        @param mw_freq_hz:
        @param mw_power_dbm:
        @return:
        """
        self.sigExtMicrowaveChanged.emit(mw_freq_hz, mw_power_dbm, use_ext_mw)
        return

    def pulser_activation_config_changed(self, activation_config_name):
        """
        Sets the current pulse generator activation config via pulsed_measurement_logic

        @param activation_config_name:
        @return:
        """
        self.sigPulserActivationConfigChanged.emit(activation_config_name)
        return

    def pulser_sample_rate_changed(self, sample_rate_hz):
        """
        Sets the pulse generator sample rate via pulsed_measurement_logic

        @param sample_rate_hz:
        @return:
        """
        self.sigPulserSampleRateChanged.emit(sample_rate_hz)
        return

    def pulser_amplitude_changed(self, amplitude_dict):
        """

        @param amplitude_dict:
        @return:
        """
        self.sigPulserAmplitudeChanged.emit(amplitude_dict)
        return

    def pulser_settings_updated(self, activation_config_name, activation_config, sample_rate,
                                amplitude_dict):
        """

        @param activation_config_name:
        @param activation_config:
        @param sample_rate:
        @param amplitude_dict:
        @return:
        """
        self.sigPulserSettingsUpdated.emit(activation_config_name, activation_config, sample_rate,
                                           amplitude_dict)
        return

    def analysis_windows_changed(self, signal_start_bin, signal_width_bins, reference_start_bin,
                                 reference_width_bins):
        """

        @param signal_start_bin:
        @param signal_width_bins:
        @param reference_start_bin:
        @param reference_width_bins:
        @return:
        """
        self.sigAnalysisWindowsChanged.emit(signal_start_bin, signal_width_bins,
                                            reference_start_bin,
                                            reference_width_bins)
        return

    def laser_trigger_delay_changed(self, laser_trig_delay_s):
        """

        @param laser_trig_delay_s:
        @return:
        """
        self.sigLaserTriggerDelayChanged.emit(laser_trig_delay_s)
        return

    def alternating_changed(self, is_alternating):
        """

        @param is_alternating:
        @return:
        """
        self.sigAlternatingChanged.emit(is_alternating)
        return

    def ignore_laser_indices_changed(self, index_list):
        """

        @param index_list:
        @return:
        """
        if type(index_list) is not list:
            index_list = [int(index_list)]
        self.sigIgnoreLaserIndicesChanged.emit(index_list)
        return

    def do_fit(self, fit_function, x_data=None, y_data=None):
        """

        @param fit_function:
        @param x_data:
        @param y_data:
        @return:
        """
        self.sigDoFit.emit(fit_function, x_data, y_data)
        return

    def fit_updated(self, fit_data_x, fit_data_y, result_dict):
        """

        @param fit_data_x:
        @param fit_data_y:
        @param result_dict:
        @return:
        """
        self.sigFitUpdated.emit(fit_data_x, fit_data_y, result_dict)
        return

    def analysis_interval_changed(self, analysis_interval_s):
        """

        @param analysis_interval_s:
        @return:
        """
        self.sigAnalysisIntervalChanged.emit(analysis_interval_s)
        return

    def manually_pull_data(self):
        """

        @return:
        """
        self.sigManuallyPullData.emit()
        return

    def start_measurement(self):
        """

        @return:
        """
        if self.manual_xaxis_def:

        if self.manual_laser_def:


        self.sigStartMeasurement.emit()
        return

    def stop_measurement(self):
        """

        @return:
        """
        self.sigStopMeasurement.emit()
        return

    def pause_measurement(self):
        """

        @return:
        """
        self.sigPauseMeasurement.emit()
        return

    def continue_measurement(self):
        """

        @return:
        """
        self.sigContinueMeasurement.emit()
        return

    def measurement_status_updated(self, measurement_status):
        """

        @param measurement_status:
        @return:
        """
        self.sigMeasurementStatusUpdated.emit(measurement_status)
        return

    def toggle_pulse_generator(self, switch_on):
        """

        @param switch_on:
        @return:
        """
        self.sigTogglePulseGenerator.emit(switch_on)
        return

    def pulser_running_updated(self, is_running):
        """

        @param is_running:
        @return:
        """
        self.sigPulserRunningUpdated.emit(is_running)
        return

    def clear_pulse_generator(self):
        """

        @return:
        """
        self.sigClearPulseGenerator.emit()
        return

    def upload_asset(self, asset_name):
        """

        @param asset_name:
        @return:
        """
        self.sigUploadAssetToPulser.emit(asset_name)
        return

    def load_asset_into_channels(self, asset_name, load_dict={}):
        """

        @param asset_name:
        @param load_dict:
        @return:
        """
        self.sigLoadAssetIntoChannels.emit(asset_name, load_dict)
        return

    def uploaded_assets_updated(self, asset_list):
        """

        @param asset_list:
        @return:
        """
        self.sigUploadedAssetsUpdated.emit(asset_list)
        return

    def loaded_asset_updated(self, asset_name):
        """

        @param asset_name:
        @return:
        """
        self.sigLoadedAssetUpdated.emit(asset_name)
        return

    def request_laser_pulse(self, laser_pulse_index, get_raw_pulse):
        """

        @param laser_pulse_index:
        @param get_raw_pulse:
        @return:
        """
        self.sigRequestLaserPulse.emit(laser_pulse_index, get_raw_pulse)
        return

    def laser_pulse_updated(self, laser_data):
        """

        @param laser_data:
        @return:
        """
        self.sigLaserPulseUpdated.emit(laser_data)
        return


    #######################################################################
    ###             Sequence generator methods                          ###
    #######################################################################

    def save_pulse_block(self, block_name, block_object):
        """

        @param block_name:
        @param block_object:
        @return:
        """
        self.sigSavePulseBlock.emit(block_name, block_object)
        return

    def save_block_ensemble(self, ensemble_name, ensemble_object):
        """

        @param ensemble_name:
        @param ensemble_object:
        @return:
        """
        self.sigSaveBlockEnsemble.emit(ensemble_name, ensemble_object)
        return

    def load_pulse_block(self, block_name):
        """

        @param block_name:
        @return:
        """
        self.sigLoadPulseBlock.emit(block_name)
        return

    def pulse_block_loaded(self, block_object):
        """

        @param block_object:
        @return:
        """
        self.sigPulseBlockLoaded.emit(block_object)
        return

    def load_block_ensemble(self, ensemble_name):
        """

        @param ensemble_name:
        @return:
        """
        self.sigLoadBlockEnsemble.emit(ensemble_name)
        return

    def block_ensemble_loaded(self, ensemble_object):
        """

        @param ensemble_object:
        @return:
        """
        self.sigBlockEnsembleLoaded.emit(ensemble_object)
        return

    def delete_pulse_block(self, block_name):
        """

        @param block_name:
        @return:
        """
        self.sigDeletePulseBlock.emit(block_name)
        return

    def delete_block_ensemble(self, ensemble_name):
        """

        @param ensemble_name:
        @return:
        """
        self.sigDeleteBlockEnsemble.emit(ensemble_name)
        return

    def pulse_blocks_updated(self, block_list):
        """

        @param block_list:
        @return:
        """
        self.PulseBlocksUpodated.emit(block_list)
        return

    def block_ensembles_updated(self, ensemble_list):
        """

        @param ensemble_list:
        @return:
        """
        self.BlockEnsemblesUpodated.emit(ensemble_list)
        return

    def sample_block_ensemble(self, ensemble_name):
        """

        @param ensemble_name:
        @return:
        """
        self.SampleBlockEnsemble.emit(ensemble_name)
        return

    def generator_channel_config_changed(self, config_name):
        """

        @param config_name:
        @return:
        """
        channel_config = self._measurement_logic.get_pulser_constraints()['activation_config'][
            config_name]
        self.sigGeneratorChannelConfigChanged.emit(channel_config)
        return

    def generator_settings_updated(self, activation_config_name, activation_config, sample_rate,
                                   amplitude_dict, laser_channel):
        """

        @param activation_config_name:
        @param activation_config:
        @param sample_rate:
        @param amplitude_dict:
        @param laser_channel:
        @return:
        """
        self.sigGeneratorSettingsUpdated.emit(activation_config_name, activation_config,
                                              sample_rate, amplitude_dict, laser_channel)
        return

    def generator_laser_channel_changed(self, laser_channel):

    def generator_sample_rate_changed(self, sample_rate):

    def generator_amplitude_changed(self, amplitude_dict):