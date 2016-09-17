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
    sigLaserToShowChanged = QtCore.Signal(int, bool)
    sigDoFit = QtCore.Signal(str)
    sigStartMeasurement = QtCore.Signal()
    sigStopMeasurement = QtCore.Signal()
    sigPauseMeasurement = QtCore.Signal()
    sigContinueMeasurement = QtCore.Signal()
    sigStartPulser = QtCore.Signal()
    sigStopPulser = QtCore.Signal()
    sigFastCounterSettingsChanged = QtCore.Signal(float, float)
    sigMeasurementSequenceSettingsChanged = QtCore.Signal(np.ndarray, int, float, list, bool, float)
    sigPulseGeneratorSettingsChanged = QtCore.Signal(float, str, dict, bool)
    sigUploadAsset = QtCore.Signal(str)
    sigLoadAsset = QtCore.Signal(str, dict)
    sigClearPulseGenerator = QtCore.Signal()
    sigExtMicrowaveSettingsChanged = QtCore.Signal(float, float, bool)
    sigExtMicrowaveStartStop = QtCore.Signal(bool)
    sigTimerIntervalChanged = QtCore.Signal(float)
    sigAnalysisWindowsChanged = QtCore.Signal(int, int, int, int)
    sigManuallyPullData = QtCore.Signal()
    sigRequestMeasurementInitValues = QtCore.Signal()
    sigAnalysisMethodChanged = QtCore.Signal(float)

    # sequence_generator_logic signals
    sigSavePulseBlock = QtCore.Signal(str, object)
    sigSaveBlockEnsemble = QtCore.Signal(str, object)
    sigSaveSequence = QtCore.Signal(str, object)
    sigDeletePulseBlock = QtCore.Signal(str)
    sigDeleteBlockEnsemble = QtCore.Signal(str)
    sigDeleteSequence = QtCore.Signal(str)
    sigLoadPulseBlock = QtCore.Signal(str)
    sigLoadBlockEnsemble = QtCore.Signal(str)
    sigLoadSequence = QtCore.Signal(str)
    sigSampleBlockEnsemble = QtCore.Signal(str, bool, bool)
    sigSampleSequence = QtCore.Signal(str, bool, bool)
    sigGeneratorSettingsChanged = QtCore.Signal(list, str, float, dict)
    sigRequestGeneratorInitValues = QtCore.Signal()

    # signals for master module (i.e. GUI)
    sigSavedPulseBlocksUpdated = QtCore.Signal(list)
    sigSavedBlockEnsemblesUpdated = QtCore.Signal(list)
    sigSavedSequencesUpdated = QtCore.Signal(list)
    sigCurrentPulseBlockUpdated = QtCore.Signal(object)
    sigCurrentBlockEnsembleUpdated = QtCore.Signal(object)
    sigCurrentSequenceUpdated = QtCore.Signal(object)
    sigBlockEnsembleSampled = QtCore.Signal(str)
    sigSequenceSampled = QtCore.Signal(str)
    sigGeneratorSettingsUpdated = QtCore.Signal(str, list, float, dict, str)

    sigSignalDataUpdated = QtCore.Signal(np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray)
    sigLaserDataUpdated = QtCore.Signal(np.ndarray, np.ndarray)
    sigLaserToShowUpdated = QtCore.Signal(int, bool)
    sigElapsedTimeUpdated = QtCore.Signal(float, str)
    sigFitUpdated = QtCore.Signal(str, np.ndarray, np.ndarray, dict, object)
    sigMeasurementStatusUpdated = QtCore.Signal(bool, bool)
    sigPulserRunningUpdated = QtCore.Signal(bool)
    sigFastCounterSettingsUpdated = QtCore.Signal(float, float)
    sigMeasurementSequenceSettingsUpdated = QtCore.Signal(np.ndarray, int, float, list, bool, float)
    sigPulserSettingsUpdated = QtCore.Signal(float, str, list, dict, bool)
    sigAssetUploaded = QtCore.Signal(str)
    sigUploadedAssetsUpdated = QtCore.Signal(list)
    sigLoadedAssetUpdated = QtCore.Signal(str, str)
    sigExtMicrowaveSettingsUpdated = QtCore.Signal(float, float, bool)
    sigExtMicrowaveRunningUpdated = QtCore.Signal(bool)
    sigTimerIntervalUpdated = QtCore.Signal(float)
    sigAnalysisWindowsUpdated = QtCore.Signal(int, int, int, int)
    sigAnalysisMethodUpdated = QtCore.Signal(float)

    _modclass = 'pulsedmasterlogic'
    _modtype = 'logic'

    # declare connectors
    _in = {'pulsedmeasurementlogic': 'PulsedMeasurementLogic',
           'sequencegeneratorlogic': 'SequenceGeneratorLogic',
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
        self._generator_logic = self.connector['in']['sequencegeneratorlogic']['object']

        # Signals controlling the pulsed_measurement_logic
        self.sigRequestMeasurementInitValues.connect(self._measurement_logic.request_init_values,
                                                     QtCore.Qt.QueuedConnection)
        self.sigMeasurementSequenceSettingsChanged.connect(
            self._measurement_logic.set_pulse_sequence_properties, QtCore.Qt.QueuedConnection)
        self.sigFastCounterSettingsChanged.connect(
            self._measurement_logic.set_fast_counter_settings, QtCore.Qt.QueuedConnection)
        self.sigExtMicrowaveSettingsChanged.connect(self._measurement_logic.set_microwave_params,
                                                    QtCore.Qt.QueuedConnection)
        self.sigExtMicrowaveStartStop.connect(self._measurement_logic.microwave_on_off,
                                              QtCore.Qt.QueuedConnection)
        self.sigPulseGeneratorSettingsChanged.connect(
            self._measurement_logic.set_pulse_generator_settings, QtCore.Qt.QueuedConnection)
        self.sigAnalysisWindowsChanged.connect(self._measurement_logic.set_analysis_windows,
                                               QtCore.Qt.QueuedConnection)
        self.sigDoFit.connect(self._measurement_logic.do_fit, QtCore.Qt.QueuedConnection)
        self.sigTimerIntervalChanged.connect(self._measurement_logic.set_timer_interval,
                                             QtCore.Qt.QueuedConnection)
        self.sigManuallyPullData.connect(self._measurement_logic.manually_pull_data,
                                         QtCore.Qt.QueuedConnection)
        self.sigStartMeasurement.connect(self._measurement_logic.start_pulsed_measurement,
                                         QtCore.Qt.QueuedConnection)
        self.sigStopMeasurement.connect(self._measurement_logic.stop_pulsed_measurement,
                                        QtCore.Qt.QueuedConnection)
        self.sigPauseMeasurement.connect(self._measurement_logic.pause_pulsed_measurement,
                                         QtCore.Qt.QueuedConnection)
        self.sigContinueMeasurement.connect(self._measurement_logic.pause_pulsed_measurement,
                                            QtCore.Qt.QueuedConnection)
        self.sigStartPulser.connect(self._measurement_logic.pulse_generator_on,
                                    QtCore.Qt.QueuedConnection)
        self.sigStopPulser.connect(self._measurement_logic.pulse_generator_off,
                                   QtCore.Qt.QueuedConnection)
        self.sigClearPulseGenerator.connect(self._measurement_logic.clear_pulser,
                                            QtCore.Qt.QueuedConnection)
        self.sigUploadAsset.connect(self._measurement_logic.upload_asset,
                                    QtCore.Qt.QueuedConnection)
        self.sigLoadAsset.connect(self._measurement_logic.load_asset, QtCore.Qt.QueuedConnection)
        self.sigLaserToShowChanged.connect(self._measurement_logic.set_laser_to_show,
                                           QtCore.Qt.QueuedConnection)
        self.sigAnalysisMethodChanged.connect(self._measurement_logic.analysis_method_changed,
                                              QtCore.Qt.QueuedConnection)

        # Signals controlling the sequence_generator_logic
        self.sigRequestGeneratorInitValues.connect(self._generator_logic.request_init_values,
                                                   QtCore.Qt.QueuedConnection)
        self.sigSavePulseBlock.connect(self._generator_logic.save_block, QtCore.Qt.QueuedConnection)
        self.sigSaveBlockEnsemble.connect(self._generator_logic.save_ensemble,
                                          QtCore.Qt.QueuedConnection)
        self.sigSaveSequence.connect(self._generator_logic.save_sequence,
                                     QtCore.Qt.QueuedConnection)
        self.sigLoadPulseBlock.connect(self._generator_logic.get_pulse_block,
                                       QtCore.Qt.QueuedConnection)
        self.sigLoadBlockEnsemble.connect(self._generator_logic.get_pulse_block_ensemble,
                                          QtCore.Qt.QueuedConnection)
        self.sigLoadSequence.connect(self._generator_logic.get_pulse_sequence,
                                     QtCore.Qt.QueuedConnection)
        self.sigDeletePulseBlock.connect(self._generator_logic.delete_block,
                                         QtCore.Qt.QueuedConnection)
        self.sigDeleteBlockEnsemble.connect(self._generator_logic.delete_ensemble,
                                            QtCore.Qt.QueuedConnection)
        self.sigDeleteSequence.connect(self._generator_logic.delete_sequence,
                                       QtCore.Qt.QueuedConnection)
        self.sigSampleBlockEnsemble.connect(self._generator_logic.sample_pulse_block_ensemble,
                                            QtCore.Qt.QueuedConnection)
        self.sigSampleSequence.connect(self._generator_logic.sample_pulse_sequence,
                                       QtCore.Qt.QueuedConnection)
        self.sigGeneratorSettingsChanged.connect(self._generator_logic.set_settings,
                                                 QtCore.Qt.QueuedConnection)

        # connect signals coming from the pulsed_measurement_logic
        self._measurement_logic.sigSignalDataUpdated.connect(self.signal_data_updated,
                                                             QtCore.Qt.QueuedConnection)
        self._measurement_logic.sigLaserDataUpdated.connect(self.laser_data_updated,
                                                            QtCore.Qt.QueuedConnection)
        self._measurement_logic.sigLaserToShowUpdated.connect(self.laser_to_show_updated,
                                                              QtCore.Qt.QueuedConnection)
        self._measurement_logic.sigElapsedTimeUpdated.connect(self.measurement_time_updated,
                                                              QtCore.Qt.QueuedConnection)
        self._measurement_logic.sigFitUpdated.connect(self.fit_updated, QtCore.Qt.QueuedConnection)
        self._measurement_logic.sigMeasurementRunningUpdated.connect(
            self.measurement_status_updated, QtCore.Qt.QueuedConnection)
        self._measurement_logic.sigPulserRunningUpdated.connect(self.pulser_running_updated,
                                                                QtCore.Qt.QueuedConnection)
        self._measurement_logic.sigFastCounterSettingsUpdated.connect(
            self.fast_counter_settings_updated, QtCore.Qt.QueuedConnection)
        self._measurement_logic.sigPulseSequenceSettingsUpdated.connect(
            self.measurement_sequence_settings_updated, QtCore.Qt.QueuedConnection)
        self._measurement_logic.sigPulseGeneratorSettingsUpdated.connect(
            self.pulse_generator_settings_updated, QtCore.Qt.QueuedConnection)
        self._measurement_logic.sigUploadAssetComplete.connect(self.upload_asset_finished,
                                                                 QtCore.Qt.QueuedConnection)
        self._measurement_logic.sigUploadedAssetsUpdated.connect(self.uploaded_assets_updated,
                                                                 QtCore.Qt.QueuedConnection)
        self._measurement_logic.sigLoadedAssetUpdated.connect(self.loaded_asset_updated,
                                                              QtCore.Qt.QueuedConnection)
        self._measurement_logic.sigExtMicrowaveSettingsUpdated.connect(
            self.ext_microwave_settings_updated, QtCore.Qt.QueuedConnection)
        self._measurement_logic.sigExtMicrowaveRunningUpdated.connect(
            self.ext_microwave_running_updated, QtCore.Qt.QueuedConnection)
        self._measurement_logic.sigTimerIntervalUpdated.connect(self.analysis_interval_updated,
                                                                QtCore.Qt.QueuedConnection)
        self._measurement_logic.sigAnalysisWindowsUpdated.connect(self.analysis_windows_updated,
                                                                  QtCore.Qt.QueuedConnection)
        self._measurement_logic.sigAnalysisMethodUpdated.connect(self.analysis_method_updated,
                                                                 QtCore.Qt.QueuedConnection)

        # connect signals coming from the sequence_generator_logic
        self._generator_logic.sigBlockListUpdated.connect(self.saved_pulse_blocks_updated,
                                                          QtCore.Qt.QueuedConnection)
        self._generator_logic.sigEnsembleListUpdated.connect(self.saved_block_ensembles_updated,
                                                             QtCore.Qt.QueuedConnection)
        self._generator_logic.sigSequenceListUpdated.connect(self.saved_sequences_updated,
                                                             QtCore.Qt.QueuedConnection)
        self._generator_logic.sigSampleEnsembleComplete.connect(self.sample_ensemble_finished,
                                                                QtCore.Qt.QueuedConnection)
        self._generator_logic.sigSampleSequenceComplete.connect(self.sample_sequence_finished,
                                                                QtCore.Qt.QueuedConnection)
        self._generator_logic.sigCurrentBlockUpdated.connect(self.current_pulse_block_updated,
                                                             QtCore.Qt.QueuedConnection)
        self._generator_logic.sigCurrentEnsembleUpdated.connect(self.current_block_ensemble_updated,
                                                                QtCore.Qt.QueuedConnection)
        self._generator_logic.sigCurrentSequenceUpdated.connect(self.current_sequence_updated,
                                                                QtCore.Qt.QueuedConnection)
        self._generator_logic.sigSettingsUpdated.connect(self.generator_settings_updated,
                                                         QtCore.Qt.QueuedConnection)

        self.sample_upload_load = False

    def on_deactivate(self, e):
        """

        @param e:
        @return:
        """
        # Disconnect all signals
        # Signals controlling the pulsed_measurement_logic
        self.sigRequestMeasurementInitValues.disconnect()
        self.sigMeasurementSequenceSettingsChanged.disconnect()
        self.sigFastCounterSettingsChanged.disconnect()
        self.sigExtMicrowaveSettingsChanged.disconnect()
        self.sigExtMicrowaveStartStop.disconnect()
        self.sigPulseGeneratorSettingsChanged.disconnect()
        self.sigAnalysisWindowsChanged.disconnect()
        self.sigDoFit.disconnect()
        self.sigTimerIntervalChanged.disconnect()
        self.sigManuallyPullData.disconnect()
        self.sigStartMeasurement.disconnect()
        self.sigStopMeasurement.disconnect()
        self.sigPauseMeasurement.disconnect()
        self.sigContinueMeasurement.disconnect()
        self.sigStartPulser.disconnect()
        self.sigStopPulser.disconnect()
        self.sigClearPulseGenerator.disconnect()
        self.sigUploadAsset.disconnect()
        self.sigLoadAsset.disconnect()
        self.sigLaserToShowChanged.disconnect()
        self.sigAnalysisMethodChanged.disconnect()
        # Signals controlling the sequence_generator_logic
        self.sigRequestGeneratorInitValues.disconnect()
        self.sigSavePulseBlock.disconnect()
        self.sigSaveBlockEnsemble.disconnect()
        self.sigSaveSequence.disconnect()
        self.sigLoadPulseBlock.disconnect()
        self.sigLoadBlockEnsemble.disconnect()
        self.sigLoadSequence.disconnect()
        self.sigDeletePulseBlock.disconnect()
        self.sigDeleteBlockEnsemble.disconnect()
        self.sigDeleteSequence.disconnect()
        self.sigSampleBlockEnsemble.disconnect()
        self.sigSampleSequence.disconnect()
        self.sigGeneratorSettingsChanged.disconnect()
        # Signals coming from the pulsed_measurement_logic
        self._measurement_logic.sigSignalDataUpdated.disconnect()
        self._measurement_logic.sigLaserDataUpdated.disconnect()
        self._measurement_logic.sigLaserToShowUpdated.disconnect()
        self._measurement_logic.sigElapsedTimeUpdated.disconnect()
        self._measurement_logic.sigFitUpdated.disconnect()
        self._measurement_logic.sigMeasurementRunningUpdated.disconnect()
        self._measurement_logic.sigPulserRunningUpdated.disconnect()
        self._measurement_logic.sigFastCounterSettingsUpdated.disconnect()
        self._measurement_logic.sigPulseSequenceSettingsUpdated.disconnect()
        self._measurement_logic.sigPulseGeneratorSettingsUpdated.disconnect()
        self._measurement_logic.sigUploadedAssetsUpdated.disconnect()
        self._measurement_logic.sigLoadedAssetUpdated.disconnect()
        self._measurement_logic.sigExtMicrowaveSettingsUpdated.disconnect()
        self._measurement_logic.sigExtMicrowaveRunningUpdated.disconnect()
        self._measurement_logic.sigTimerIntervalUpdated.disconnect()
        self._measurement_logic.sigAnalysisWindowsUpdated.disconnect()
        self._measurement_logic.sigAnalysisMethodUpdated.disconnect()
        # Signals coming from the sequence_generator_logic
        self._generator_logic.sigBlockListUpdated.disconnect()
        self._generator_logic.sigEnsembleListUpdated.disconnect()
        self._generator_logic.sigSequenceListUpdated.disconnect()
        self._generator_logic.sigSampleEnsembleComplete.disconnect()
        self._generator_logic.sigSampleSequenceComplete.disconnect()
        self._generator_logic.sigCurrentBlockUpdated.disconnect()
        self._generator_logic.sigCurrentEnsembleUpdated.disconnect()
        self._generator_logic.sigCurrentSequenceUpdated.disconnect()
        self._generator_logic.sigSettingsUpdated.disconnect()
        return

    #######################################################################
    ###             Pulsed measurement methods                          ###
    #######################################################################
    def request_measurement_init_values(self):
        """

        @return:
        """
        self.sigRequestMeasurementInitValues.emit()
        return

    def get_hardware_constraints(self):
        """

        @return:
        """
        fastcounter_constraints = self._measurement_logic.get_fastcounter_constraints()
        pulsegenerator_constraints = self._measurement_logic.get_pulser_constraints()
        return pulsegenerator_constraints, fastcounter_constraints

    def get_fit_functions(self):
        """

        @param functions_list:
        @return:
        """
        return self._measurement_logic.get_fit_functions()

    def measurement_sequence_settings_changed(self, measurement_ticks, number_of_lasers,
                                              sequence_length_s, laser_ignore_list, alternating,
                                              laser_trigger_delay):
        """

        @param measurement_ticks:
        @param number_of_lasers:
        @param sequence_length_s:
        @param laser_ignore_list:
        @param alternating:
        @param laser_trigger_delay:
        @return:
        """
        self.sigMeasurementSequenceSettingsChanged.emit(measurement_ticks, number_of_lasers,
                                                        sequence_length_s, laser_ignore_list,
                                                        alternating, laser_trigger_delay)
        return

    def measurement_sequence_settings_updated(self, measurement_ticks, number_of_lasers,
                                              sequence_length_s, laser_ignore_list, alternating,
                                              laser_trigger_delay):
        """

        @param measurement_ticks:
        @param number_of_lasers:
        @param sequence_length_s:
        @param laser_ignore_list:
        @param alternating:
        @param laser_trigger_delay:
        @return:
        """
        self.sigMeasurementSequenceSettingsUpdated.emit(measurement_ticks, number_of_lasers,
                                                        sequence_length_s, laser_ignore_list,
                                                        alternating, laser_trigger_delay)
        return

    def fast_counter_settings_changed(self, bin_width_s, record_length_s):
        """

        @param bin_width_s:
        @param record_length_s:
        @return:
        """
        self.sigFastCounterSettingsChanged.emit(bin_width_s, record_length_s)
        return

    def fast_counter_settings_updated(self, bin_width_s, record_length_s):
        """

        @param bin_width_s:
        @param record_length_s:
        @param number_of_lasers:
        @return:
        """
        self.sigFastCounterSettingsUpdated.emit(bin_width_s, record_length_s)
        return

    def ext_microwave_settings_changed(self, frequency_hz, power_dbm, use_ext_microwave):
        """

        @param frequency_hz:
        @param power_dbm:
        @param use_ext_microwave:
        @return:
        """
        self.sigExtMicrowaveSettingsChanged.emit(frequency_hz, power_dbm, use_ext_microwave)
        return

    def ext_microwave_settings_updated(self, frequency_hz, power_dbm, use_ext_microwave):
        """

        @param frequency_hz:
        @param power_dbm:
        @param use_ext_microwave:
        @return:
        """
        self.sigExtMicrowaveSettingsUpdated.emit(frequency_hz, power_dbm, use_ext_microwave)
        return

    def ext_microwave_toggled(self, output_on):
        """

        @param output_on:
        @return:
        """
        self.sigExtMicrowaveStartStop.emit(output_on)
        return

    def ext_microwave_running_updated(self, is_running):
        """

        @param is_running:
        @return:
        """
        self.sigExtMicrowaveRunningUpdated.emit(is_running)
        return

    def pulse_generator_settings_changed(self, sample_rate_hz, activation_config_name,
                                         analogue_amplitude, interleave_on):
        """

        @param sample_rate_hz:
        @param activation_config_name:
        @param analogue_amplitude:
        @param interleave_on:
        @return:
        """
        self.sigPulseGeneratorSettingsChanged.emit(sample_rate_hz, activation_config_name,
                                                   analogue_amplitude, interleave_on)
        return

    def pulse_generator_settings_updated(self, sample_rate_hz, activation_config_name,
                                         analogue_amplitude, interleave_on):
        """

        @param sample_rate_hz:
        @param activation_config_name:
        @param analogue_amplitude:
        @param interleave_on:
        @return:
        """
        activation_config = self._measurement_logic.get_pulser_constraints()['activation_config'][
            activation_config_name]
        self.sigPulserSettingsUpdated.emit(sample_rate_hz, activation_config_name,
                                           activation_config, analogue_amplitude, interleave_on)
        return

    def analysis_windows_changed(self, signal_start_bin, signal_width_bins, norm_start_bin,
                                 norm_width_bins):
        """

        @param signal_start_bin:
        @param signal_width_bins:
        @param norm_start_bin:
        @param norm_width_bins:
        @return:
        """
        self.sigAnalysisWindowsChanged.emit(signal_start_bin, signal_width_bins, norm_start_bin,
                                            norm_width_bins)
        return

    def analysis_windows_updated(self, signal_start_bin, signal_width_bins, norm_start_bin,
                                 norm_width_bins):
        """

        @param signal_start_bin:
        @param signal_width_bins:
        @param norm_start_bin:
        @param norm_width_bins:
        @return:
        """
        self.sigAnalysisWindowsUpdated.emit(signal_start_bin, signal_width_bins, norm_start_bin,
                                            norm_width_bins)
        return

    def do_fit(self, fit_function):
        """

        @param fit_function:
        @return:
        """
        self.sigDoFit.emit(fit_function)
        return

    def fit_updated(self, fit_function, fit_data_x, fit_data_y, param_dict, result_dict):
        """

        @param fit_function:
        @param fit_data_x:
        @param fit_data_y:
        @param param_dict:
        @param result_dict:
        @return:
        """
        self.sigFitUpdated.emit(fit_function, fit_data_x, fit_data_y, param_dict, result_dict)
        return

    def analysis_interval_changed(self, analysis_interval_s):
        """

        @param analysis_interval_s:
        @return:
        """
        self.sigTimerIntervalChanged.emit(analysis_interval_s)
        return

    def analysis_interval_updated(self, analysis_interval_s):
        """

        @param analysis_interval_s:
        @return:
        """
        self.sigTimerIntervalUpdated.emit(analysis_interval_s)
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
        #if self.manual_xaxis_def:

        #if self.manual_laser_def:

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

    def measurement_status_updated(self, is_running, is_paused):
        """

        @param is_running:
        @param is_paused:
        @return:
        """
        self.sigMeasurementStatusUpdated.emit(is_running, is_paused)
        return

    def measurement_time_updated(self, elapsed_time, elapsed_time_string):
        """

        @param elapsed_time:
        @param elapsed_time_string:
        @return:
        """
        self.sigElapsedTimeUpdated.emit(elapsed_time, elapsed_time_string)
        return

    def toggle_pulse_generator(self, switch_on):
        """

        @param switch_on:
        @return:
        """
        if switch_on:
            self.sigStartPulser.emit()
        else:
            self.sigStopPulser.emit()
        return

    def pulser_running_updated(self, is_running):
        """

        @param is_running:
        @return:
        """
        self.sigPulserRunningUpdated.emit(is_running)
        return

    def save_measurement_data(self, save_tag):
        """

        @param save_tag:
        @return:
        """
        self._measurement_logic.save_measurement_data(save_tag)
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
        self.sigUploadAsset.emit(asset_name)
        return

    def upload_asset_finished(self, asset_name):
        """

        @param asset_name:
        @return:
        """
        if self.sample_upload_load:
            self.load_asset_into_channels(asset_name)
        self.log.debug('PULSEDMASTER: Asset "{0}" uploaded!'.format(asset_name))
        self.sigAssetUploaded.emit(asset_name)
        return

    def uploaded_assets_updated(self, asset_names_list):
        """

        @param asset_names_list:
        @return:
        """
        self.sigUploadedAssetsUpdated.emit(asset_names_list)
        return

    def load_asset_into_channels(self, asset_name, load_dict={}, invoke_settings=False):
        """

        @param asset_name:
        @param load_dict:
        @param bool invoke_settings: Specifies whether the measurement parameters should be chosen
                                     according to the loaded assets metadata.
        @return:
        """
        # FIXME: implement that! Changes in Pulse objects and measurement logic parameters needed
        # invoke measurement parameters from asset object
        # if invoke_settings:
            # # get asset object
            # asset_obj = self._generator_logic.get_saved_asset(asset_name)
            # # Set proper activation config
            # activation_config = asset_obj.activation_config
            # config_name = None
            # avail_configs = self._measurement_logic.get_pulser_constraints()['activation_config']
            # for config in avail_configs:
            #     if activation_config == avail_configs[config]:
            #         config_name = config
            #         break
            #
            #
            # # set proper number of laser pulses
            # if self._measurement_logic.number_of_lasers != asset_obj.number_of_lasers:
            #     self.num_laserpulses_changed(asset_obj.number_of_lasers)
            # # set proper sequence length
            # self._measurement_logic.sequence_length_s = asset_obj.length_bins / asset_obj.sample_rate
            # self.pulse_generator_settings_changed(asset_obj.sample_rate, config_name, amplitude_dict, None)
            # self.measurement_sequence_settings_changed(asset_obj.measurement_ticks_list, sequence_length, laser_ignore_list, alternating, laser_trigger_delay)
        self.sigLoadAsset.emit(asset_name, load_dict)
        return

    def loaded_asset_updated(self, asset_name):
        """

        @param asset_name:
        @return:
        """
        if self.sample_upload_load:
            self.sample_upload_load = False
        if asset_name is not None:
            asset_object = self._generator_logic.get_saved_asset(asset_name)
            asset_type = type(asset_object).__name__
        else:
            asset_type = 'No asset loaded'
        self.sample_upload_load = False
        self.log.debug('PULSEDMASTER: Asset "{0}" of type "{1}" loaded into pulser channel(s)!'.format(asset_name, asset_type))
        self.sigLoadedAssetUpdated.emit(asset_name, asset_type)
        return asset_name, asset_type

    def laser_to_show_changed(self, laser_pulse_index, get_raw_pulse):
        """

        @param laser_pulse_index:
        @param get_raw_pulse:
        @return:
        """
        self.sigLaserToShowChanged.emit(laser_pulse_index, get_raw_pulse)
        return

    def laser_to_show_updated(self, laser_pulse_index, get_raw_pulse):
        """

        @param laser_pulse_index:
        @param get_raw_pulse:
        @return:
        """
        self.sigLaserToShowUpdated.emit(laser_pulse_index, get_raw_pulse)
        return

    def laser_data_updated(self, laser_data_x, laser_data_y):
        """

        @param laser_data_x:
        @param laser_data_y:
        @return:
        """
        self.sigLaserDataUpdated.emit(laser_data_x, laser_data_y)
        return

    def signal_data_updated(self, signal_data_x, signal_data_y, signal_data_y2, error_data_y, error_data_y2):
        """

        @param signal_data_x:
        @param signal_data_y:
        @param signal_data_y2:
        @param error_data_y:
        @param error_data_y2:
        @return:
        """
        self.sigSignalDataUpdated.emit(signal_data_x, signal_data_y, signal_data_y2, error_data_y, error_data_y2)
        return

    def analysis_method_changed(self, gaussfilt_std_dev):
        """

        @param gaussfilt_std_dev:
        @return:
        """
        self.sigAnalysisMethodChanged.emit(gaussfilt_std_dev)
        return

    def analysis_method_updated(self, gaussfilt_std_dev):
        """

        @param gaussfilt_std_dev:
        @return:
        """
        self.sigAnalysisMethodUpdated.emit(gaussfilt_std_dev)
        return


    #######################################################################
    ###             Sequence generator methods                          ###
    #######################################################################
    def request_generator_init_values(self):
        """

        @return:
        """
        self.sigRequestGeneratorInitValues.emit()
        return

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

    def save_sequence(self, sequence_name, sequence_object):
        """

        @param sequence_name:
        @param sequence_object:
        @return:
        """
        self.sigSaveSequence.emit(sequence_name, sequence_object)
        return

    def load_pulse_block(self, block_name):
        """

        @param block_name:
        @return:
        """
        self.sigLoadPulseBlock.emit(block_name, True)
        return

    def load_block_ensemble(self, ensemble_name):
        """

        @param ensemble_name:
        @return:
        """
        self.sigLoadBlockEnsemble.emit(ensemble_name)
        return

    def load_sequence(self, sequence_name):
        """

        @param sequence_name:
        @return:
        """
        self.sigLoadSequence.emit(sequence_name)
        return

    def current_pulse_block_updated(self, block_object):
        """

        @param block_object:
        @return:
        """
        self.sigCurrentPulseBlockUpdated.emit(block_object)
        return

    def current_block_ensemble_updated(self, ensemble_object):
        """

        @param ensemble_object:
        @return:
        """
        self.sigCurrentBlockEnsembleUpdated.emit(ensemble_object)
        return

    def current_sequence_updated(self, sequence_object):
        """

        @param sequence_object:
        @return:
        """
        self.sigCurrentSequenceUpdated.emit(sequence_object)
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

    def delete_sequence(self, sequence_name):
        """

        @param sequence_name:
        @return:
        """
        self.sigDeleteSequence.emit(sequence_name)
        return

    def saved_pulse_blocks_updated(self, block_list):
        """

        @param block_list:
        @return:
        """
        self.sigSavedPulseBlocksUpdated.emit(block_list)
        return

    def saved_block_ensembles_updated(self, ensemble_list):
        """

        @param ensemble_list:
        @return:
        """
        self.sigSavedBlockEnsemblesUpdated.emit(ensemble_list)
        return

    def saved_sequences_updated(self, sequence_list):
        """

        @param sequence_list:
        @return:
        """
        self.sigSavedSequencesUpdated.emit(sequence_list)
        return

    def sample_block_ensemble(self, ensemble_name, write_to_file, write_chunkwise, sample_upload_load = False):
        """

        @param ensemble_name:
        @return:
        """
        if sample_upload_load:
            self.sample_upload_load = True
        self.sigSampleBlockEnsemble.emit(ensemble_name, write_to_file, write_chunkwise)
        return

    def sample_sequence(self, sequence_name, write_to_file, write_chunkwise, sample_upload_load = False):
        """

        @param sequence_name:
        @return:
        """
        if sample_upload_load:
            self.sample_upload_load = True
        self.sigSampleSequence.emit(sequence_name, write_to_file, write_chunkwise)
        return

    def sample_ensemble_finished(self, ensemble_name):
        """

        @return:
        """
        if self.sample_upload_load:
            self.upload_asset(ensemble_name)
        self.log.debug('PULSEDMASTER: Sampling of ensemble "{0}" finished!'.format(ensemble_name))
        self.sigBlockEnsembleSampled.emit(ensemble_name)
        return

    def sample_sequence_finished(self, sequence_name):
        """

        @return:
        """
        if self.sample_upload_load:
            self.upload_asset(sequence_name)
        self.log.debug('PULSEDMASTER: Sampling of sequence "{0}" finished!'.format(sequence_name))
        self.sigSequenceSampled.emit(sequence_name)
        return

    def generator_settings_changed(self, activation_config_name, laser_channel, sample_rate,
                                   amplitude_dict):
        """

        @param activation_config_name:
        @param laser_channel:
        @param sample_rate:
        @param amplitude_dict:
        @return:
        """
        # get pulser constraints
        pulser_constraints = self._measurement_logic.get_pulser_constraints()
        # activation config
        config_constraint = pulser_constraints['activation_config']
        if activation_config_name not in config_constraint:
            new_config_name = list(config_constraint.keys())[0]
            self.log.warning('Activation config "{0}" could not be found in pulser constraints. '
                             'Choosing first valid config "{1}" '
                             'instead.'.format(activation_config_name, new_config_name))
            activation_config_name = new_config_name
        activation_config = config_constraint[activation_config_name]
        # laser channel
        if laser_channel not in activation_config:
            old_laser_chnl = laser_channel
            laser_channel = None
            for chnl in activation_config:
                if chnl.startswith('d_ch'):
                    laser_channel = chnl
                    break
            if laser_channel is None:
                for chnl in activation_config:
                    if chnl.startswith('a_ch'):
                        laser_channel = chnl
                        break
            self.log.warning('Laser channel "{0}" could not be found in generator activation '
                             'config "{1}". Using first valid channel "{2}" instead.'
                             ''.format(old_laser_chnl, activation_config, laser_channel))
        # sample rate
        samplerate_constraint = pulser_constraints['sample_rate']
        if sample_rate < samplerate_constraint['min'] or sample_rate > samplerate_constraint['max']:
            self.log.warning('Sample rate of {0} MHz lies not within pulse generator constraints. '
                             'Using max. allowed sample rate of {1} MHz instead.'
                             ''.format(sample_rate, samplerate_constraint['max']))
            sample_rate = samplerate_constraint['max']
        # amplitude dictionary
        # FIXME: check with pulser constraints
        self.sigGeneratorSettingsChanged.emit(activation_config, laser_channel, sample_rate,
                                              amplitude_dict)
        return

    def generator_settings_updated(self, activation_config, laser_channel, sample_rate,
                                   amplitude_dict):
        """

        @param activation_config:
        @param sample_rate:
        @param amplitude_dict:
        @param laser_channel:
        @return:
        """
        # retrieve hardware constraints
        pulser_constraints = self._measurement_logic.get_pulser_constraints()
        # check activation_config
        config_dict = pulser_constraints['activation_config']
        activation_config_name = ''
        for key in config_dict.keys():
            if config_dict[key] == activation_config:
                activation_config_name = key
        if activation_config_name == '':
            activation_config_name = list(config_dict.keys())[0]
            activation_config = config_dict[activation_config_name]
            self.log.warning('Activation config "{0}" could not be found in pulser constraints. '
                             'Taking first valid config "{1}" '
                             'instead.'.format(activation_config, activation_config_name))
            self.generator_settings_changed(activation_config_name, laser_channel, sample_rate,
                                            amplitude_dict)
        else:
            self.sigGeneratorSettingsUpdated.emit(activation_config_name, activation_config,
                                                  sample_rate, amplitude_dict, laser_channel)
        return
