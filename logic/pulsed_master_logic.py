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

from collections import OrderedDict
from core.module import Connector, ConfigOption, StatusVar
from logic.generic_logic import GenericLogic
from qtpy import QtCore
import numpy as np


class PulsedMasterLogic(GenericLogic):
    """
    This logic module controls the sequence/waveform generation and management via
    sequence_generator_logic and pulsed measurements via pulsed_measurement_logic.
    Basically glue logic to pass information between logic modules.
    """

    _modclass = 'pulsedmasterlogic'
    _modtype = 'logic'

    # declare connectors
    pulsedmeasurementlogic = Connector(interface='PulsedMeasurementLogic')
    sequencegeneratorlogic = Connector(interface='SequenceGeneratorLogic')

    # config options
    direct_write = ConfigOption('direct_write', False, missing='warn')

    # status vars
    invoke_settings = StatusVar('invoke_settings', False)
    couple_generator_hw = StatusVar('couple_generator_hw', True)

    # pulsed_measurement_logic signals
    sigLaserToShowChanged = QtCore.Signal(int, bool)
    sigDoFit = QtCore.Signal(str)
    sigStartMeasurement = QtCore.Signal(str)
    sigStopMeasurement = QtCore.Signal(str)
    sigPauseMeasurement = QtCore.Signal()
    sigContinueMeasurement = QtCore.Signal()
    sigStartPulser = QtCore.Signal()
    sigStopPulser = QtCore.Signal()
    sigFastCounterSettingsChanged = QtCore.Signal(float, float)
    sigMeasurementSequenceSettingsChanged = QtCore.Signal(np.ndarray, int, float, list, bool)
    sigPulseGeneratorSettingsChanged = QtCore.Signal(float, str, dict, bool)
    sigUploadAsset = QtCore.Signal(str)
    sigDirectWriteEnsemble = QtCore.Signal(str, np.ndarray, np.ndarray)
    sigDirectWriteSequence = QtCore.Signal(str, list)
    sigLoadAsset = QtCore.Signal(str, dict)
    sigClearPulseGenerator = QtCore.Signal()
    sigExtMicrowaveSettingsChanged = QtCore.Signal(float, float, bool)
    sigExtMicrowaveStartStop = QtCore.Signal(bool)
    sigTimerIntervalChanged = QtCore.Signal(float)
    sigAnalysisSettingsChanged = QtCore.Signal(dict)
    sigManuallyPullData = QtCore.Signal()
    sigRequestMeasurementInitValues = QtCore.Signal()
    sigExtractionSettingsChanged = QtCore.Signal(dict)

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
    sigSampleBlockEnsemble = QtCore.Signal(str, bool)
    sigSampleSequence = QtCore.Signal(str, bool)
    sigGeneratorSettingsChanged = QtCore.Signal(list, str, float, dict, str)
    sigRequestGeneratorInitValues = QtCore.Signal()
    sigGeneratePredefinedSequence = QtCore.Signal(str, dict)

    # signals for master module (i.e. GUI)
    sigSavedPulseBlocksUpdated = QtCore.Signal(dict)
    sigSavedBlockEnsemblesUpdated = QtCore.Signal(dict)
    sigSavedSequencesUpdated = QtCore.Signal(dict)
    sigCurrentPulseBlockUpdated = QtCore.Signal(object)
    sigCurrentBlockEnsembleUpdated = QtCore.Signal(object, dict)
    sigCurrentSequenceUpdated = QtCore.Signal(object, dict)
    sigEnsembleSaUpComplete = QtCore.Signal(str)
    sigSequenceSaUpComplete = QtCore.Signal(str)
    sigGeneratorSettingsUpdated = QtCore.Signal(str, list, float, dict, str, str)
    sigPredefinedSequencesUpdated = QtCore.Signal(dict)
    sigPredefinedSequenceGenerated = QtCore.Signal(str)

    sigSignalDataUpdated = QtCore.Signal(np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray,
                                         np.ndarray, np.ndarray, np.ndarray)
    sigLaserDataUpdated = QtCore.Signal(np.ndarray, np.ndarray)
    sigLaserToShowUpdated = QtCore.Signal(int, bool)
    sigElapsedTimeUpdated = QtCore.Signal(float, str)
    sigFitUpdated = QtCore.Signal(str, np.ndarray, np.ndarray, object)
    sigMeasurementStatusUpdated = QtCore.Signal(bool, bool)
    sigPulserRunningUpdated = QtCore.Signal(bool)
    sigFastCounterSettingsUpdated = QtCore.Signal(float, float)
    sigMeasurementSequenceSettingsUpdated = QtCore.Signal(np.ndarray, int, float, list, bool)
    sigPulserSettingsUpdated = QtCore.Signal(float, str, list, dict, bool)
    sigUploadedAssetsUpdated = QtCore.Signal(list)
    sigLoadedAssetUpdated = QtCore.Signal(str, str)
    sigExtMicrowaveSettingsUpdated = QtCore.Signal(float, float, bool)
    sigExtMicrowaveRunningUpdated = QtCore.Signal(bool)
    sigTimerIntervalUpdated = QtCore.Signal(float)
    sigAnalysisSettingsUpdated = QtCore.Signal(dict)
    sigAnalysisMethodsUpdated = QtCore.Signal(dict)
    sigExtractionSettingsUpdated = QtCore.Signal(dict)
    sigExtractionMethodsUpdated = QtCore.Signal(dict)

    def __init__(self, config, **kwargs):
        """ Create PulsedMasterLogic object with connectors.

          @param dict kwargs: optional parameters
        """
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._measurement_logic = self.get_connector('pulsedmeasurementlogic')
        self._generator_logic = self.get_connector('sequencegeneratorlogic')

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
        self.sigAnalysisSettingsChanged.connect(self._measurement_logic.analysis_settings_changed,
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
        self.sigContinueMeasurement.connect(self._measurement_logic.continue_pulsed_measurement,
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
        self.sigDirectWriteEnsemble.connect(self._measurement_logic.direct_write_ensemble,
                                            QtCore.Qt.QueuedConnection)
        self.sigDirectWriteSequence.connect(self._measurement_logic.direct_write_sequence,
                                            QtCore.Qt.QueuedConnection)
        self.sigLaserToShowChanged.connect(self._measurement_logic.set_laser_to_show,
                                           QtCore.Qt.QueuedConnection)
        self.sigExtractionSettingsChanged.connect(self._measurement_logic.extraction_settings_changed,
                                                  QtCore.Qt.QueuedConnection)

        # Signals controlling the sequence_generator_logic
        self.sigRequestGeneratorInitValues.connect(self._generator_logic.request_init_values,
                                                   QtCore.Qt.QueuedConnection)
        self.sigSavePulseBlock.connect(self._generator_logic.save_block, QtCore.Qt.QueuedConnection)
        self.sigSaveBlockEnsemble.connect(self._generator_logic.save_ensemble,
                                          QtCore.Qt.QueuedConnection)
        self.sigSaveSequence.connect(self._generator_logic.save_sequence,
                                     QtCore.Qt.QueuedConnection)
        self.sigLoadPulseBlock.connect(self._generator_logic.load_block, QtCore.Qt.QueuedConnection)
        self.sigLoadBlockEnsemble.connect(self._generator_logic.load_ensemble,
                                          QtCore.Qt.QueuedConnection)
        self.sigLoadSequence.connect(self._generator_logic.load_sequence,
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
        self.sigGeneratePredefinedSequence.connect(
            self._generator_logic.generate_predefined_sequence, QtCore.Qt.QueuedConnection)

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
        self._measurement_logic.sigAnalysisSettingsUpdated.connect(self.analysis_settings_updated,
                                                                   QtCore.Qt.QueuedConnection)
        self._measurement_logic.sigAnalysisMethodsUpdated.connect(self.analysis_methods_updated,
                                                                  QtCore.Qt.QueuedConnection)
        self._measurement_logic.sigExtractionSettingsUpdated.connect(self.extraction_settings_updated,
                                                                     QtCore.Qt.QueuedConnection)
        self._measurement_logic.sigExtractionMethodsUpdated.connect(self.extraction_methods_updated,
                                                                    QtCore.Qt.QueuedConnection)

        # connect signals coming from the sequence_generator_logic
        self._generator_logic.sigBlockDictUpdated.connect(self.saved_pulse_blocks_updated,
                                                          QtCore.Qt.QueuedConnection)
        self._generator_logic.sigEnsembleDictUpdated.connect(self.saved_block_ensembles_updated,
                                                             QtCore.Qt.QueuedConnection)
        self._generator_logic.sigSequenceDictUpdated.connect(self.saved_sequences_updated,
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
        self._generator_logic.sigPredefinedSequencesUpdated.connect(
            self.predefined_sequences_updated, QtCore.Qt.QueuedConnection)
        self._generator_logic.sigPredefinedSequenceGenerated.connect(
            self.predefined_sequence_generated, QtCore.Qt.QueuedConnection)

        self.status_dict = OrderedDict()
        self.status_dict['sauplo_ensemble_busy'] = False
        self.status_dict['sauplo_sequence_busy'] = False
        self.status_dict['saup_ensemble_busy'] = False
        self.status_dict['saup_sequence_busy'] = False
        self.status_dict['sampling_busy'] = False
        self.status_dict['upload_busy'] = False
        self.status_dict['loading_busy'] = False

        self.status_dict['pulser_running'] = False
        self.status_dict['measurement_running'] = False
        self.status_dict['microwave_running'] = False

    def on_deactivate(self):
        """

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
        self.sigAnalysisSettingsChanged.disconnect()
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
        self.sigDirectWriteEnsemble.disconnect()
        self.sigDirectWriteSequence.disconnect()
        self.sigLaserToShowChanged.disconnect()
        self.sigExtractionSettingsChanged.disconnect()
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
        self.sigGeneratePredefinedSequence.disconnect()
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
        self._measurement_logic.sigUploadAssetComplete.disconnect()
        self._measurement_logic.sigUploadedAssetsUpdated.disconnect()
        self._measurement_logic.sigLoadedAssetUpdated.disconnect()
        self._measurement_logic.sigExtMicrowaveSettingsUpdated.disconnect()
        self._measurement_logic.sigExtMicrowaveRunningUpdated.disconnect()
        self._measurement_logic.sigTimerIntervalUpdated.disconnect()
        self._measurement_logic.sigAnalysisSettingsUpdated.disconnect()
        self._measurement_logic.sigAnalysisMethodsUpdated.disconnect()
        self._measurement_logic.sigExtractionSettingsUpdated.disconnect()
        self._measurement_logic.sigExtractionMethodsUpdated.disconnect()
        # Signals coming from the sequence_generator_logic
        self._generator_logic.sigBlockDictUpdated.disconnect()
        self._generator_logic.sigEnsembleDictUpdated.disconnect()
        self._generator_logic.sigSequenceDictUpdated.disconnect()
        self._generator_logic.sigSampleEnsembleComplete.disconnect()
        self._generator_logic.sigSampleSequenceComplete.disconnect()
        self._generator_logic.sigCurrentBlockUpdated.disconnect()
        self._generator_logic.sigCurrentEnsembleUpdated.disconnect()
        self._generator_logic.sigCurrentSequenceUpdated.disconnect()
        self._generator_logic.sigSettingsUpdated.disconnect()
        self._generator_logic.sigPredefinedSequencesUpdated.disconnect()
        self._generator_logic.sigPredefinedSequenceGenerated.disconnect()
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

    def measurement_sequence_settings_changed(self, controlled_vals, number_of_lasers,
                                              sequence_length_s, laser_ignore_list, alternating):
        """

        @param controlled_vals:
        @param number_of_lasers:
        @param sequence_length_s:
        @param laser_ignore_list:
        @param alternating:
        @return:
        """
        self.sigMeasurementSequenceSettingsChanged.emit(controlled_vals, number_of_lasers,
                                                        sequence_length_s, laser_ignore_list,
                                                        alternating)
        return

    def measurement_sequence_settings_updated(self, controlled_vals, number_of_lasers,
                                              sequence_length_s, laser_ignore_list, alternating):
        """

        @param controlled_vals:
        @param number_of_lasers:
        @param sequence_length_s:
        @param laser_ignore_list:
        @param alternating:
        @return:
        """
        self.sigMeasurementSequenceSettingsUpdated.emit(controlled_vals, number_of_lasers,
                                                        sequence_length_s, laser_ignore_list,
                                                        alternating)
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
        self.status_dict['microwave_running'] = is_running
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
        if self.couple_generator_hw:
            self.generator_settings_changed(activation_config_name,
                                            self._generator_logic.laser_channel,
                                            sample_rate_hz, analogue_amplitude,
                                            self._generator_logic.waveform_format)
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
        # FIXME: This is just a temporary fix to avoid mismatch of pp-amplitude in measurement
        # and generator logic. Later on the pp-amplitude is a field in the GUI just like activation
        # config and sample rate
        self._generator_logic.amplitude_dict = analogue_amplitude

        constraints = self._measurement_logic.get_pulser_constraints()
        activation_config = constraints.activation_config[activation_config_name]
        self.sigPulserSettingsUpdated.emit(sample_rate_hz, activation_config_name,
                                           activation_config, analogue_amplitude, interleave_on)
        return

    def analysis_settings_changed(self, analysis_settings):
        """

        @param dict analysis_settings
        @return:
        """
        self.sigAnalysisSettingsChanged.emit(analysis_settings)
        return

    def analysis_settings_updated(self, analysis_settings):
        """

        @param dict: analysis_settings:
        @return:
        """
        self.sigAnalysisSettingsUpdated.emit(analysis_settings)
        return

    def analysis_methods_updated(self, methods_dict):
        """

        @param methods_dict:
        @return:
        """
        self.sigAnalysisMethodsUpdated.emit(methods_dict)
        return

    def do_fit(self, fit_function):
        """

        @param fit_function:
        @return:
        """
        self.sigDoFit.emit(fit_function)
        return

    def fit_updated(self, fit_function, fit_data_x, fit_data_y, result_dict):
        """

        @param fit_function:
        @param fit_data_x:
        @param fit_data_y:
        @param result_dict:
        @return:
        """
        self.sigFitUpdated.emit(fit_function, fit_data_x, fit_data_y, result_dict)
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

    def start_measurement(self, stashed_raw_data_tag=''):
        """

        @return:
        """
        self.sigStartMeasurement.emit(stashed_raw_data_tag)
        return

    def stop_measurement(self, stash_raw_data_tag=''):
        """

        @return:
        """
        self.sigStopMeasurement.emit(stash_raw_data_tag)
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
        self.status_dict['measurement_running'] = is_running
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
        self.status_dict['pulser_running'] = is_running
        self.sigPulserRunningUpdated.emit(is_running)
        return

    def save_measurement_data(self, controlled_val_unit, tag, with_error, save_ft):
        """ Prepare data to be saved and create a proper plot of the data.
        This is just handed over to the measurement logic.

        @param str controlled_val_unit: unit of the x axis of the plot
        @param str tag: a filetag which will be included in the filename
        @param bool with_error: select whether errors should be saved/plotted
        @param bool save_ft: select wether the Fourier Transform is plotted

        @return str: filepath where data were saved
        """
        return self._measurement_logic.save_measurement_data(controlled_val_unit=controlled_val_unit,
                                                      tag=tag,
                                                      with_error=with_error,
                                                      save_ft=save_ft)

    def clear_pulse_generator(self):
        """

        @return:
        """
        self.sigClearPulseGenerator.emit()
        return

    def upload_ensemble(self, ensemble_name, analog_samples=None, digital_samples=None):
        """

        @param ensemble_name:
        @param analog_samples:
        @param digital_samples:
        @return:
        """
        if self.direct_write and (analog_samples is None or digital_samples is None):
            self.log.error('Upload ensemble failed because direct write is enabled but no sample '
                           'arrays are given.')
            return
        self.status_dict['upload_busy'] = True
        if self.direct_write:
            self.sigDirectWriteEnsemble.emit(ensemble_name, analog_samples, digital_samples)
        else:
            self.sigUploadAsset.emit(ensemble_name)
        return

    def upload_sequence(self, sequence_name, sequence_params=None):
        """

        @param sequence_name:
        @param sequence_params:
        @return:
        """
        if self.direct_write and sequence_params is None:
            self.log.error('Upload sequence failed because direct write is enabled but no '
                           'sequence_params dict is given.')
            return
        self.status_dict['upload_busy'] = True
        if self.direct_write:
            self.sigDirectWriteSequence.emit(sequence_name, sequence_params)
        else:
            self.sigUploadAsset.emit(sequence_name)
        return

    def upload_asset_finished(self, asset_name):
        """

        @param asset_name:
        @return:
        """
        if asset_name in self._generator_logic.saved_pulse_sequences:
            if self.status_dict['sauplo_sequence_busy']:
                self.load_asset_into_channels(asset_name)
            self.log.debug('Sequence "{0}" uploaded to pulse generator device!'.format(asset_name))
            self.status_dict['upload_busy'] = False
            if self.status_dict['saup_sequence_busy']:
                self.status_dict['saup_sequence_busy'] = False
                self.sigSequenceSaUpComplete.emit(asset_name)
        elif asset_name in self._generator_logic.saved_pulse_block_ensembles:
            if self.status_dict['sauplo_ensemble_busy']:
                self.load_asset_into_channels(asset_name)
            self.log.debug('Ensemble "{0}" uploaded to pulse generator device!'.format(asset_name))
            self.status_dict['upload_busy'] = False
            if self.status_dict['saup_ensemble_busy']:
                self.status_dict['saup_ensemble_busy'] = False
                self.sigEnsembleSaUpComplete.emit(asset_name)
        return

    def uploaded_assets_updated(self, asset_names_list):
        """

        @param asset_names_list:
        @return:
        """
        self.sigUploadedAssetsUpdated.emit(asset_names_list)
        return

    def load_asset_into_channels(self, asset_name, load_dict=None):
        """

        @param asset_name:
        @param load_dict:
        @param bool invoke_settings: Specifies whether the measurement parameters should be chosen
                                     according to the loaded assets metadata.
        @return:
        """
        if load_dict is None:
            load_dict = dict()
        # invoke measurement parameters from asset object
        if self.invoke_settings:
            # get asset object
            if asset_name in self._generator_logic.saved_pulse_sequences:
                self.log.debug('Invoking measurement settings from PulseSequence object.')
                asset_obj = self._generator_logic.saved_pulse_sequences[asset_name]
            elif asset_name in self._generator_logic.saved_pulse_block_ensembles:
                self.log.debug('Invoking measurement settings from PulseBlockEnsemble object.')
                asset_obj = self._generator_logic.saved_pulse_block_ensembles[asset_name]
            else:
                asset_obj = None
                self.log.error('No PulseBlockEnsemble or PulseSequence object by name "{0}" found '
                               'in saved assets. Will not invoke measurement settings.'
                               ''.format(asset_name))

            # Only invoke settings if an asset object has been found in the sequence_generator_logic
            if asset_obj is not None:
                # Get parameters from asset object
                asset_params = self._get_asset_parameters(asset_obj)
                # Only invoke settings if asset_params are valid
                if asset_params['err_code'] >= 0:
                    interleave = self._measurement_logic.interleave_on
                    fc_binwidth_s = self._measurement_logic.fast_counter_binwidth
                    if self._measurement_logic.fast_counter_gated:
                        fc_record_length_s = asset_params['max_laser_length']
                    else:
                        fc_record_length_s = asset_params['sequence_length']
                    self.fast_counter_settings_changed(fc_binwidth_s, fc_record_length_s)
                    self.pulse_generator_settings_changed(asset_params['sample_rate'],
                                                          asset_params['config_name'],
                                                          asset_params['amplitude_dict'],
                                                          interleave)
                    self.measurement_sequence_settings_changed(asset_params['controlled_vals_arr'],
                                                               asset_params['num_of_lasers'],
                                                               asset_params['sequence_length'],
                                                               asset_params['laser_ignore_list'],
                                                               asset_params['is_alternating'])
        # Load asset into channel
        self.status_dict['loading_busy'] = True
        self.sigLoadAsset.emit(asset_name, load_dict)
        return

    def loaded_asset_updated(self, asset_name):
        """

        @param asset_name:
        @return:
        """
        if asset_name is not None and asset_name != '' and asset_name != str(None):
            asset_object = self._generator_logic.get_saved_asset(asset_name)
            asset_type = type(asset_object).__name__
        else:
            asset_type = 'No asset loaded'
        self.log.debug('Asset "{0}" of type "{1}" loaded into pulse generator channel(s)!'
                       ''.format(asset_name, asset_type))
        self.status_dict['sauplo_ensemble_busy'] = False
        self.status_dict['sauplo_sequence_busy'] = False
        self.status_dict['loading_busy'] = False
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

    def signal_data_updated(self, signal_data_x, signal_data_y, signal_data_y2, error_data_y,
                            error_data_y2, signal_fft_x, signal_fft_y, signal_fft_y2):
        """

        @param signal_data_x:
        @param signal_data_y:
        @param signal_data_y2:
        @param error_data_y:
        @param error_data_y2:
        @return:
        """
        self.sigSignalDataUpdated.emit(signal_data_x, signal_data_y, signal_data_y2, error_data_y,
                                       error_data_y2, signal_fft_x, signal_fft_y, signal_fft_y2)
        return

    def extraction_settings_changed(self, extraction_settings):
        """

        @param dict extraction_settings:
        @return:
        """
        self.sigExtractionSettingsChanged.emit(extraction_settings)
        return

    def extraction_settings_updated(self, extraction_settings):
        """

        @param dict extraction_settings:
        @return:
        """
        self.sigExtractionSettingsUpdated.emit(extraction_settings)
        return

    def extraction_methods_updated(self, methods_dict):
        """

        @param methods_dict:
        @return:
        """
        self.sigExtractionMethodsUpdated.emit(methods_dict)
        return


    #######################################################################
    ###             Sequence generator methods                          ###
    #######################################################################
    def request_generator_init_values(self):
        """

        @return:
        """
        self.sigRequestGeneratorInitValues.emit()
        self.sigEnsembleSaUpComplete.emit('')
        self.sigSequenceSaUpComplete.emit('')
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
        # add non-crucial parameters. Metadata for pulser settings upon load into channels.
        ensemble_object.sample_rate = self._generator_logic.sample_rate
        ensemble_object.activation_config = self._generator_logic.activation_config
        ensemble_object.amplitude_dict = self._generator_logic.amplitude_dict
        ensemble_object.laser_channel = self._generator_logic.laser_channel
        self.sigSaveBlockEnsemble.emit(ensemble_name, ensemble_object)
        return

    def save_sequence(self, sequence_name, sequence_object):
        """

        @param sequence_name:
        @param sequence_object:
        @return:
        """
        sequence_object.sample_rate = self._generator_logic.sample_rate
        sequence_object.activation_config = self._generator_logic.activation_config
        sequence_object.amplitude_dict = self._generator_logic.amplitude_dict
        sequence_object.laser_channel = self._generator_logic.laser_channel
        self.sigSaveSequence.emit(sequence_name, sequence_object)
        return

    def load_pulse_block(self, block_name):
        """

        @param block_name:
        @return:
        """
        self.sigLoadPulseBlock.emit(block_name)
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
        if ensemble_object is not None:
            ensemble_params = self._get_asset_parameters(ensemble_object)
            if ensemble_params['err_code'] < 0:
                ensemble_params = {}
        else:
            ensemble_params = {}
        self.sigCurrentBlockEnsembleUpdated.emit(ensemble_object, ensemble_params)
        return

    def current_sequence_updated(self, sequence_object):
        """

        @param sequence_object:
        @return:
        """
        if sequence_object is not None:
            sequence_params = self._get_asset_parameters(sequence_object)
            if sequence_params['err_code'] < 0:
                sequence_params = {}
        else:
            sequence_params = {}
        self.sigCurrentSequenceUpdated.emit(sequence_object, sequence_params)
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

    def saved_pulse_blocks_updated(self, block_dict):
        """

        @param block_dict:
        @return:
        """
        self.sigSavedPulseBlocksUpdated.emit(block_dict)
        return

    def saved_block_ensembles_updated(self, ensemble_dict):
        """

        @param ensemble_dict:
        @return:
        """
        self.sigSavedBlockEnsemblesUpdated.emit(ensemble_dict)
        return

    def saved_sequences_updated(self, sequence_dict):
        """

        @param sequence_dict:
        @return:
        """
        self.sigSavedSequencesUpdated.emit(sequence_dict)
        return

    def sample_block_ensemble(self, ensemble_name, with_load=False):
        """

        @param ensemble_name:
        @param with_load:
        @return:
        """
        if with_load:
            self.status_dict['sauplo_ensemble_busy'] = True
        else:
            self.status_dict['saup_ensemble_busy'] = True
        self.status_dict['sampling_busy'] = True
        self.sigSampleBlockEnsemble.emit(ensemble_name, not self.direct_write)
        return

    def sample_sequence(self, sequence_name, with_load=False):
        """

        @param sequence_name:
        @param with_load:
        @return:
        """
        if with_load:
            self.status_dict['sauplo_sequence_busy'] = True
        else:
            self.status_dict['saup_sequence_busy'] = True
        self.status_dict['sampling_busy'] = True
        self.sigSampleSequence.emit(sequence_name, not self.direct_write)
        return

    def sample_ensemble_finished(self, ensemble_name, analog_samples, digital_samples):
        """

        @return:
        """
        self.upload_ensemble(ensemble_name, analog_samples, digital_samples)
        self.log.debug('Sampling of ensemble "{0}" finished!'.format(ensemble_name))
        if self.status_dict['saup_ensemble_busy'] or self.status_dict['sauplo_ensemble_busy']:
            self.status_dict['sampling_busy'] = False
        return

    def sample_sequence_finished(self, sequence_name, sequence_params):
        """

        @return:
        """
        self.upload_sequence(sequence_name, sequence_params)
        self.log.debug('Sampling of sequence "{0}" finished!'.format(sequence_name))
        self.status_dict['sampling_busy'] = False
        return

    def generator_settings_changed(self, activation_config_name, laser_channel, sample_rate,
                                   amplitude_dict, sampling_format):
        """

        @param activation_config_name:
        @param laser_channel:
        @param sample_rate:
        @param amplitude_dict:
        @param sampling_format:
        @return:
        """
        # get pulser constraints
        pulser_constraints = self._measurement_logic.get_pulser_constraints()
        # activation config
        config_constraint = pulser_constraints.activation_config
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
        samplerate_constraint = pulser_constraints.sample_rate
        if sample_rate < samplerate_constraint.min or sample_rate > samplerate_constraint.max:
            self.log.warning('Sample rate of {0} MHz lies not within pulse generator constraints. '
                             'Using max. allowed sample rate of {1} MHz instead.'
                             ''.format(sample_rate, samplerate_constraint.max))
            sample_rate = samplerate_constraint.max
        # amplitude dictionary
        # FIXME: check with pulser constraints
        self.sigGeneratorSettingsChanged.emit(activation_config, laser_channel, sample_rate,
                                              amplitude_dict, sampling_format)
        return

    def generator_settings_updated(self, activation_config, laser_channel, sample_rate,
                                   amplitude_dict, waveform_format):
        """

        @param activation_config:
        @param sample_rate:
        @param amplitude_dict:
        @param laser_channel:
        @param sampling_format:
        @return:
        """
        # retrieve hardware constraints
        pulser_constraints = self._measurement_logic.get_pulser_constraints()
        # check activation_config
        config_dict = pulser_constraints.activation_config
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
                                            amplitude_dict, waveform_format)
        else:
            self.sigGeneratorSettingsUpdated.emit(activation_config_name, activation_config,
                                                  sample_rate, amplitude_dict, laser_channel,
                                                  waveform_format)
            if self.couple_generator_hw:
                self.sigPulserSettingsUpdated.emit(sample_rate, activation_config_name,
                                                   activation_config, amplitude_dict,
                                                   self._measurement_logic.interleave_on)
        return

    def generate_predefined_sequence(self, generator_method_name, kwarg_dict):
        """

        @param generator_method_name:
        @param kwarg_dict:
        @return:
        """
        self.sigGeneratePredefinedSequence.emit(generator_method_name, kwarg_dict)
        return

    def predefined_sequence_generated(self, generator_method_name):
        """

        @param generator_method_name:
        @return:
        """
        self.sigPredefinedSequenceGenerated.emit(generator_method_name)
        return

    def predefined_sequences_updated(self, generator_methods_dict):
        """

        @param generator_methods_dict:
        @return:
        """
        self.sigPredefinedSequencesUpdated.emit(generator_methods_dict)
        return

    #######################################################################
    ###             Helper  methods                                     ###
    #######################################################################
    def _get_asset_parameters(self, asset_obj):
        """

        @param asset_obj:
        @return:
        """
        if type(asset_obj).__name__ == 'PulseSequence':
            self.log.warning('Calculation of measurement sequence parameters not implemented yet '
                             'for PulseSequence objects.')
            return {'err_code': -1}
        # Create return dictionary
        return_params = {'err_code': 0}

        # Get activation config and name
        if asset_obj.activation_config is None:
            return_params['activation_config'] = self._generator_logic.activation_config
            self.log.warning('No activation config specified in asset "{0}" metadata. Choosing '
                             'currently set activation config "{1}" from sequence_generator_logic.'
                             ''.format(asset_obj.name, return_params['activation_config']))
        else:
            return_params['activation_config'] = asset_obj.activation_config
        config_name = None
        avail_configs = self._measurement_logic.get_pulser_constraints().activation_config
        for config in avail_configs:
            if return_params['activation_config'] == avail_configs[config]:
                config_name = config
                break
        if config_name is None:
            self.log.error('Activation config {0} is not part of the allowed activation '
                           'configs in the pulse generator hardware.'
                           ''.format(return_params['activation_config']))
            return_params['err_code'] = -1
            return return_params
        else:
            return_params['config_name'] = config_name

        # Get analogue voltages
        if asset_obj.amplitude_dict is None:
            return_params['amplitude_dict'] = self._generator_logic.amplitude_dict
            self.log.warning('No amplitude dictionary specified in asset "{0}" metadata. Choosing '
                             'currently set amplitude dict "{1}" from sequence_generator_logic.'
                             ''.format(asset_obj.name, return_params['amplitude_dict']))
        else:
            return_params['amplitude_dict'] = asset_obj.amplitude_dict

        # Get sample rate
        if asset_obj.sample_rate is None:
            return_params['sample_rate'] = self._generator_logic.sample_rate
            self.log.warning('No sample rate specified in asset "{0}" metadata. Choosing '
                             'currently set sample rate "{1:.2e}" from sequence_generator_logic.'
                             ''.format(asset_obj.name, return_params['sample_rate']))
        else:
            return_params['sample_rate'] = asset_obj.sample_rate

        # Get sequence length
        return_params['sequence_length'] = asset_obj.length_s
        return_params['sequence_length_bins'] = asset_obj.length_s*self._generator_logic.sample_rate

        # Get number of laser pulses and max laser length
        if asset_obj.laser_channel is None:
            laser_chnl = self._generator_logic.laser_channel
            self.log.warning('No laser channel specified in asset "{0}" metadata. Choosing '
                             'currently set laser channel "{1}" from sequence_generator_logic.'
                             ''.format(asset_obj.name, laser_chnl))
        else:
            laser_chnl = asset_obj.laser_channel
        num_of_lasers = 0
        max_laser_length = 0.0
        tmp_laser_on = False
        tmp_laser_length = 0.0
        for block, reps in asset_obj.block_list:
            tmp_lasers_num = 0
            for element in block.element_list:
                if 'd_ch' in laser_chnl:
                    d_channels = [ch for ch in return_params['activation_config'] if 'd_ch' in ch]
                    chnl_index = d_channels.index(laser_chnl)
                    if not tmp_laser_on and element.digital_high[chnl_index]:
                        tmp_laser_on = True
                        tmp_lasers_num += 1
                    elif not element.digital_high[chnl_index]:
                        tmp_laser_on = False
                    if tmp_laser_on:
                        if element.increment_s > 1.0e-15:
                            tmp_laser_length += (element.init_length_s + reps * element.increment_s)
                        else:
                            tmp_laser_length += element.init_length_s
                        if tmp_laser_length > max_laser_length:
                            max_laser_length = tmp_laser_length
                    else:
                        tmp_laser_length = 0.0
                else:
                    self.log.error('Invoke measurement settings from a PulseBlockEnsemble with '
                                   'analogue laser channel is not implemented yet.')
                    return_params['err_code'] = -1
                    return
            num_of_lasers += (tmp_lasers_num * (reps + 1))
        return_params['num_of_lasers'] = num_of_lasers
        return_params['max_laser_length'] = max_laser_length

        # Get laser ignore list
        if asset_obj.laser_ignore_list is None:
            return_params['laser_ignore_list'] = []
            self.log.warning('No laser ignore list specified in asset "{0}" metadata. '
                             'Assuming that no lasers should be ignored.'.format(asset_obj.name))
        else:
            return_params['laser_ignore_list'] = asset_obj.laser_ignore_list

        # Get alternating
        if asset_obj.alternating is None:
            return_params['is_alternating'] = self._measurement_logic.alternating
            self.log.warning('No alternating specified in asset "{0}" metadata. Choosing '
                             'currently set state "{1}" from pulsed_measurement_logic.'
                             ''.format(asset_obj.name, return_params['is_alternating']))
        else:
            return_params['is_alternating'] = asset_obj.alternating

        # Get controlled variable values
        if len(asset_obj.controlled_vals_array) < 1:
            ana_lasers = num_of_lasers - len(return_params['laser_ignore_list'])
            controlled_vals_array = np.arange(1, ana_lasers + 1)
            self.log.warning('No measurement ticks specified in asset "{0}" metadata. Choosing '
                             'laser indices instead.'.format(asset_obj.name))
            if return_params['is_alternating']:
                controlled_vals_array = controlled_vals_array[0:ana_lasers//2]
        else:
            controlled_vals_array = asset_obj.controlled_vals_array
        return_params['controlled_vals_arr'] = controlled_vals_array

        # return all parameters
        return return_params
