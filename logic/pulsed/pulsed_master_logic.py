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

from core.connector import Connector
from logic.generic_logic import GenericLogic
from qtpy import QtCore
import numpy as np


class PulsedMasterLogic(GenericLogic):
    """
    This logic module combines the functionality of two modules.

    It can be used to generate pulse sequences/waveforms and to control the settings for the pulse
    generator via SequenceGeneratorLogic. Essentially this part controls what is played on the
    pulse generator.
    Furthermore it can be used to set up a pulsed measurement with an already set-up pulse generator
    together with a fast counting device via PulsedMeasurementLogic.

    The main purpose for this module is to provide a single interface while maintaining a modular
    structure for complex pulsed measurements. Each of the sub-modules can be used without this
    module but more care has to be taken in that case.
    Automatic transfer of information from one sub-module to the other for convenience is also
    handled here.
    Another important aspect is the use of this module in scripts (e.g. jupyter notebooks).
    All calls to sub-module setter functions (PulsedMeasurementLogic and SequenceGeneratorLogic)
    are decoupled from the calling thread via Qt queued connections.
    This ensures a more intuitive and less error prone use of scripting.
    """

    # declare connectors
    pulsedmeasurementlogic = Connector(interface='PulsedMeasurementLogic')
    sequencegeneratorlogic = Connector(interface='SequenceGeneratorLogic')

    # PulsedMeasurementLogic control signals
    sigDoFit = QtCore.Signal(str, bool)
    sigToggleMeasurement = QtCore.Signal(bool, str)
    sigToggleMeasurementPause = QtCore.Signal(bool)
    sigTogglePulser = QtCore.Signal(bool)
    sigToggleExtMicrowave = QtCore.Signal(bool)
    sigFastCounterSettingsChanged = QtCore.Signal(dict)
    sigMeasurementSettingsChanged = QtCore.Signal(dict)
    sigExtMicrowaveSettingsChanged = QtCore.Signal(dict)
    sigAnalysisSettingsChanged = QtCore.Signal(dict)
    sigExtractionSettingsChanged = QtCore.Signal(dict)
    sigTimerIntervalChanged = QtCore.Signal(float)
    sigAlternativeDataTypeChanged = QtCore.Signal(str)
    sigManuallyPullData = QtCore.Signal()

    # signals for master module (i.e. GUI) coming from PulsedMeasurementLogic
    sigMeasurementDataUpdated = QtCore.Signal()
    sigTimerUpdated = QtCore.Signal(float, int, float, float)
    sigFitUpdated = QtCore.Signal(str, np.ndarray, object, bool)
    sigMeasurementStatusUpdated = QtCore.Signal(bool, bool)
    sigPulserRunningUpdated = QtCore.Signal(bool)
    sigExtMicrowaveRunningUpdated = QtCore.Signal(bool)
    sigExtMicrowaveSettingsUpdated = QtCore.Signal(dict)
    sigFastCounterSettingsUpdated = QtCore.Signal(dict)
    sigMeasurementSettingsUpdated = QtCore.Signal(dict)
    sigAnalysisSettingsUpdated = QtCore.Signal(dict)
    sigExtractionSettingsUpdated = QtCore.Signal(dict)

    # SequenceGeneratorLogic control signals
    sigSavePulseBlock = QtCore.Signal(object)
    sigSaveBlockEnsemble = QtCore.Signal(object)
    sigSaveSequence = QtCore.Signal(object)
    sigDeletePulseBlock = QtCore.Signal(str)
    sigDeleteBlockEnsemble = QtCore.Signal(str)
    sigDeleteSequence = QtCore.Signal(str)
    sigLoadBlockEnsemble = QtCore.Signal(str)
    sigLoadSequence = QtCore.Signal(str)
    sigSampleBlockEnsemble = QtCore.Signal(str)
    sigSampleSequence = QtCore.Signal(str)
    sigClearPulseGenerator = QtCore.Signal()
    sigGeneratorSettingsChanged = QtCore.Signal(dict)
    sigSamplingSettingsChanged = QtCore.Signal(dict)
    sigGeneratePredefinedSequence = QtCore.Signal(str, dict)

    # signals for master module (i.e. GUI) coming from SequenceGeneratorLogic
    sigBlockDictUpdated = QtCore.Signal(dict)
    sigEnsembleDictUpdated = QtCore.Signal(dict)
    sigSequenceDictUpdated = QtCore.Signal(dict)
    sigAvailableWaveformsUpdated = QtCore.Signal(list)
    sigAvailableSequencesUpdated = QtCore.Signal(list)
    sigSampleEnsembleComplete = QtCore.Signal(object)
    sigSampleSequenceComplete = QtCore.Signal(object)
    sigLoadedAssetUpdated = QtCore.Signal(str, str)
    sigGeneratorSettingsUpdated = QtCore.Signal(dict)
    sigSamplingSettingsUpdated = QtCore.Signal(dict)
    sigPredefinedSequenceGenerated = QtCore.Signal(object, bool)

    def __init__(self, config, **kwargs):
        """ Create PulsedMasterLogic object with connectors.

          @param dict kwargs: optional parameters
        """
        super().__init__(config=config, **kwargs)

        # Dictionary servings as status register
        self.status_dict = dict()
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        # Initialize status register
        self.status_dict = {'sampling_ensemble_busy': False,
                            'sampling_sequence_busy': False,
                            'sampload_busy': False,
                            'loading_busy': False,
                            'pulser_running': False,
                            'measurement_running': False,
                            'microwave_running': False,
                            'predefined_generation_busy': False,
                            'fitting_busy': False}

        # Connect signals controlling PulsedMeasurementLogic
        self.sigDoFit.connect(
            self.pulsedmeasurementlogic().do_fit, QtCore.Qt.QueuedConnection)
        self.sigToggleMeasurement.connect(
            self.pulsedmeasurementlogic().toggle_pulsed_measurement, QtCore.Qt.QueuedConnection)
        self.sigToggleMeasurementPause.connect(
            self.pulsedmeasurementlogic().toggle_measurement_pause, QtCore.Qt.QueuedConnection)
        self.sigTogglePulser.connect(
            self.pulsedmeasurementlogic().toggle_pulse_generator, QtCore.Qt.QueuedConnection)
        self.sigToggleExtMicrowave.connect(
            self.pulsedmeasurementlogic().toggle_microwave, QtCore.Qt.QueuedConnection)
        self.sigFastCounterSettingsChanged.connect(
            self.pulsedmeasurementlogic().set_fast_counter_settings, QtCore.Qt.QueuedConnection)
        self.sigMeasurementSettingsChanged.connect(
            self.pulsedmeasurementlogic().set_measurement_settings, QtCore.Qt.QueuedConnection)
        self.sigExtMicrowaveSettingsChanged.connect(
            self.pulsedmeasurementlogic().set_microwave_settings, QtCore.Qt.QueuedConnection)
        self.sigAnalysisSettingsChanged.connect(
            self.pulsedmeasurementlogic().set_analysis_settings, QtCore.Qt.QueuedConnection)
        self.sigExtractionSettingsChanged.connect(
            self.pulsedmeasurementlogic().set_extraction_settings, QtCore.Qt.QueuedConnection)
        self.sigTimerIntervalChanged.connect(
            self.pulsedmeasurementlogic().set_timer_interval, QtCore.Qt.QueuedConnection)
        self.sigAlternativeDataTypeChanged.connect(
            self.pulsedmeasurementlogic().set_alternative_data_type, QtCore.Qt.QueuedConnection)
        self.sigManuallyPullData.connect(
            self.pulsedmeasurementlogic().manually_pull_data, QtCore.Qt.QueuedConnection)

        # Connect signals coming from PulsedMeasurementLogic
        self.pulsedmeasurementlogic().sigMeasurementDataUpdated.connect(
            self.sigMeasurementDataUpdated, QtCore.Qt.QueuedConnection)
        self.pulsedmeasurementlogic().sigTimerUpdated.connect(
            self.sigTimerUpdated, QtCore.Qt.QueuedConnection)
        self.pulsedmeasurementlogic().sigFitUpdated.connect(
            self.fit_updated, QtCore.Qt.QueuedConnection)
        self.pulsedmeasurementlogic().sigMeasurementStatusUpdated.connect(
            self.measurement_status_updated, QtCore.Qt.QueuedConnection)
        self.pulsedmeasurementlogic().sigPulserRunningUpdated.connect(
            self.pulser_running_updated, QtCore.Qt.QueuedConnection)
        self.pulsedmeasurementlogic().sigExtMicrowaveRunningUpdated.connect(
            self.ext_microwave_running_updated, QtCore.Qt.QueuedConnection)
        self.pulsedmeasurementlogic().sigExtMicrowaveSettingsUpdated.connect(
            self.sigExtMicrowaveSettingsUpdated, QtCore.Qt.QueuedConnection)
        self.pulsedmeasurementlogic().sigFastCounterSettingsUpdated.connect(
            self.sigFastCounterSettingsUpdated, QtCore.Qt.QueuedConnection)
        self.pulsedmeasurementlogic().sigMeasurementSettingsUpdated.connect(
            self.sigMeasurementSettingsUpdated, QtCore.Qt.QueuedConnection)
        self.pulsedmeasurementlogic().sigAnalysisSettingsUpdated.connect(
            self.sigAnalysisSettingsUpdated, QtCore.Qt.QueuedConnection)
        self.pulsedmeasurementlogic().sigExtractionSettingsUpdated.connect(
            self.sigExtractionSettingsUpdated, QtCore.Qt.QueuedConnection)

        # Connect signals controlling SequenceGeneratorLogic
        self.sigSavePulseBlock.connect(
            self.sequencegeneratorlogic().save_block, QtCore.Qt.QueuedConnection)
        self.sigSaveBlockEnsemble.connect(
            self.sequencegeneratorlogic().save_ensemble, QtCore.Qt.QueuedConnection)
        self.sigSaveSequence.connect(
            self.sequencegeneratorlogic().save_sequence, QtCore.Qt.QueuedConnection)
        self.sigDeletePulseBlock.connect(
            self.sequencegeneratorlogic().delete_block, QtCore.Qt.QueuedConnection)
        self.sigDeleteBlockEnsemble.connect(
            self.sequencegeneratorlogic().delete_ensemble, QtCore.Qt.QueuedConnection)
        self.sigDeleteSequence.connect(
            self.sequencegeneratorlogic().delete_sequence, QtCore.Qt.QueuedConnection)
        self.sigLoadBlockEnsemble.connect(
            self.sequencegeneratorlogic().load_ensemble, QtCore.Qt.QueuedConnection)
        self.sigLoadSequence.connect(
            self.sequencegeneratorlogic().load_sequence, QtCore.Qt.QueuedConnection)
        self.sigSampleBlockEnsemble.connect(
            self.sequencegeneratorlogic().sample_pulse_block_ensemble, QtCore.Qt.QueuedConnection)
        self.sigSampleSequence.connect(
            self.sequencegeneratorlogic().sample_pulse_sequence, QtCore.Qt.QueuedConnection)
        self.sigClearPulseGenerator.connect(
            self.sequencegeneratorlogic().clear_pulser, QtCore.Qt.QueuedConnection)
        self.sigGeneratorSettingsChanged.connect(
            self.sequencegeneratorlogic().set_pulse_generator_settings, QtCore.Qt.QueuedConnection)
        self.sigSamplingSettingsChanged.connect(
            self.sequencegeneratorlogic().set_generation_parameters, QtCore.Qt.QueuedConnection)
        self.sigGeneratePredefinedSequence.connect(
            self.sequencegeneratorlogic().generate_predefined_sequence, QtCore.Qt.QueuedConnection)

        # Connect signals coming from SequenceGeneratorLogic
        self.sequencegeneratorlogic().sigBlockDictUpdated.connect(
            self.sigBlockDictUpdated, QtCore.Qt.QueuedConnection)
        self.sequencegeneratorlogic().sigEnsembleDictUpdated.connect(
            self.sigEnsembleDictUpdated, QtCore.Qt.QueuedConnection)
        self.sequencegeneratorlogic().sigSequenceDictUpdated.connect(
            self.sigSequenceDictUpdated, QtCore.Qt.QueuedConnection)
        self.sequencegeneratorlogic().sigAvailableWaveformsUpdated.connect(
            self.sigAvailableWaveformsUpdated, QtCore.Qt.QueuedConnection)
        self.sequencegeneratorlogic().sigAvailableSequencesUpdated.connect(
            self.sigAvailableSequencesUpdated, QtCore.Qt.QueuedConnection)
        self.sequencegeneratorlogic().sigGeneratorSettingsUpdated.connect(
            self.sigGeneratorSettingsUpdated, QtCore.Qt.QueuedConnection)
        self.sequencegeneratorlogic().sigSamplingSettingsUpdated.connect(
            self.sigSamplingSettingsUpdated, QtCore.Qt.QueuedConnection)
        self.sequencegeneratorlogic().sigPredefinedSequenceGenerated.connect(
            self.predefined_sequence_generated, QtCore.Qt.QueuedConnection)
        self.sequencegeneratorlogic().sigSampleEnsembleComplete.connect(
            self.sample_ensemble_finished, QtCore.Qt.QueuedConnection)
        self.sequencegeneratorlogic().sigSampleSequenceComplete.connect(
            self.sample_sequence_finished, QtCore.Qt.QueuedConnection)
        self.sequencegeneratorlogic().sigLoadedAssetUpdated.connect(
            self.loaded_asset_updated, QtCore.Qt.QueuedConnection)
        return

    def on_deactivate(self):
        """

        @return:
        """
        # Disconnect all signals
        # Disconnect signals controlling PulsedMeasurementLogic
        self.sigDoFit.disconnect()
        self.sigToggleMeasurement.disconnect()
        self.sigToggleMeasurementPause.disconnect()
        self.sigTogglePulser.disconnect()
        self.sigToggleExtMicrowave.disconnect()
        self.sigFastCounterSettingsChanged.disconnect()
        self.sigMeasurementSettingsChanged.disconnect()
        self.sigExtMicrowaveSettingsChanged.disconnect()
        self.sigAnalysisSettingsChanged.disconnect()
        self.sigExtractionSettingsChanged.disconnect()
        self.sigTimerIntervalChanged.disconnect()
        self.sigAlternativeDataTypeChanged.disconnect()
        self.sigManuallyPullData.disconnect()
        # Disconnect signals coming from PulsedMeasurementLogic
        self.pulsedmeasurementlogic().sigMeasurementDataUpdated.disconnect()
        self.pulsedmeasurementlogic().sigTimerUpdated.disconnect()
        self.pulsedmeasurementlogic().sigFitUpdated.disconnect()
        self.pulsedmeasurementlogic().sigMeasurementStatusUpdated.disconnect()
        self.pulsedmeasurementlogic().sigPulserRunningUpdated.disconnect()
        self.pulsedmeasurementlogic().sigExtMicrowaveRunningUpdated.disconnect()
        self.pulsedmeasurementlogic().sigExtMicrowaveSettingsUpdated.disconnect()
        self.pulsedmeasurementlogic().sigFastCounterSettingsUpdated.disconnect()
        self.pulsedmeasurementlogic().sigMeasurementSettingsUpdated.disconnect()
        self.pulsedmeasurementlogic().sigAnalysisSettingsUpdated.disconnect()
        self.pulsedmeasurementlogic().sigExtractionSettingsUpdated.disconnect()

        # Disconnect signals controlling SequenceGeneratorLogic
        self.sigSavePulseBlock.disconnect()
        self.sigSaveBlockEnsemble.disconnect()
        self.sigSaveSequence.disconnect()
        self.sigDeletePulseBlock.disconnect()
        self.sigDeleteBlockEnsemble.disconnect()
        self.sigDeleteSequence.disconnect()
        self.sigLoadBlockEnsemble.disconnect()
        self.sigLoadSequence.disconnect()
        self.sigSampleBlockEnsemble.disconnect()
        self.sigSampleSequence.disconnect()
        self.sigClearPulseGenerator.disconnect()
        self.sigGeneratorSettingsChanged.disconnect()
        self.sigSamplingSettingsChanged.disconnect()
        self.sigGeneratePredefinedSequence.disconnect()
        # Disconnect signals coming from SequenceGeneratorLogic
        self.sequencegeneratorlogic().sigBlockDictUpdated.disconnect()
        self.sequencegeneratorlogic().sigEnsembleDictUpdated.disconnect()
        self.sequencegeneratorlogic().sigSequenceDictUpdated.disconnect()
        self.sequencegeneratorlogic().sigAvailableWaveformsUpdated.disconnect()
        self.sequencegeneratorlogic().sigAvailableSequencesUpdated.disconnect()
        self.sequencegeneratorlogic().sigGeneratorSettingsUpdated.disconnect()
        self.sequencegeneratorlogic().sigSamplingSettingsUpdated.disconnect()
        self.sequencegeneratorlogic().sigPredefinedSequenceGenerated.disconnect()
        self.sequencegeneratorlogic().sigSampleEnsembleComplete.disconnect()
        self.sequencegeneratorlogic().sigSampleSequenceComplete.disconnect()
        self.sequencegeneratorlogic().sigLoadedAssetUpdated.disconnect()
        return

    #######################################################################
    ###             Pulsed measurement properties                       ###
    #######################################################################
    @property
    def fast_counter_constraints(self):
        return self.pulsedmeasurementlogic().fast_counter_constraints

    @property
    def fast_counter_settings(self):
        return self.pulsedmeasurementlogic().fast_counter_settings

    @property
    def elapsed_sweeps(self):
        return self.pulsedmeasurementlogic().elapsed_sweeps

    @property
    def trigger_ratio(self):
        return self.pulsedmeasurementlogic().trigger_ratio

    @property
    def elapsed_time(self):
        return self.pulsedmeasurementlogic().elapsed_time

    @property
    def ext_microwave_constraints(self):
        return self.pulsedmeasurementlogic().ext_microwave_constraints

    @property
    def ext_microwave_settings(self):
        return self.pulsedmeasurementlogic().ext_microwave_settings

    @property
    def measurement_settings(self):
        return self.pulsedmeasurementlogic().measurement_settings

    @property
    def timer_interval(self):
        return self.pulsedmeasurementlogic().timer_interval

    @property
    def analysis_methods(self):
        return self.pulsedmeasurementlogic().analysis_methods

    @property
    def extraction_methods(self):
        return self.pulsedmeasurementlogic().extraction_methods

    @property
    def analysis_settings(self):
        return self.pulsedmeasurementlogic().analysis_settings

    @property
    def extraction_settings(self):
        return self.pulsedmeasurementlogic().extraction_settings

    @property
    def signal_data(self):
        return self.pulsedmeasurementlogic().signal_data

    @property
    def signal_alt_data(self):
        return self.pulsedmeasurementlogic().signal_alt_data

    @property
    def measurement_error(self):
        return self.pulsedmeasurementlogic().measurement_error

    @property
    def raw_data(self):
        return self.pulsedmeasurementlogic().raw_data

    @property
    def laser_data(self):
        return self.pulsedmeasurementlogic().laser_data

    @property
    def alternative_data_type(self):
        return self.pulsedmeasurementlogic().alternative_data_type

    @property
    def fit_container(self):
        return self.pulsedmeasurementlogic().fc

    #######################################################################
    ###             Pulsed measurement methods                          ###
    #######################################################################
    @QtCore.Slot(dict)
    def set_measurement_settings(self, settings_dict=None, **kwargs):
        """

        @param settings_dict:
        @param kwargs:
        """
        if isinstance(settings_dict, dict):
            self.sigMeasurementSettingsChanged.emit(settings_dict)
        else:
            self.sigMeasurementSettingsChanged.emit(kwargs)
        return

    @QtCore.Slot(dict)
    def set_fast_counter_settings(self, settings_dict=None, **kwargs):
        """

        @param settings_dict:
        @param kwargs:
        """
        if isinstance(settings_dict, dict):
            self.sigFastCounterSettingsChanged.emit(settings_dict)
        else:
            self.sigFastCounterSettingsChanged.emit(kwargs)
        return

    @QtCore.Slot(dict)
    def set_ext_microwave_settings(self, settings_dict=None, **kwargs):
        """

        @param settings_dict:
        @param kwargs:
        """
        if isinstance(settings_dict, dict):
            self.sigExtMicrowaveSettingsChanged.emit(settings_dict)
        else:
            self.sigExtMicrowaveSettingsChanged.emit(kwargs)
        return

    @QtCore.Slot(dict)
    def set_analysis_settings(self, settings_dict=None, **kwargs):
        """

        @param settings_dict:
        @param kwargs:
        """
        if isinstance(settings_dict, dict):
            self.sigAnalysisSettingsChanged.emit(settings_dict)
        else:
            self.sigAnalysisSettingsChanged.emit(kwargs)
        return

    @QtCore.Slot(dict)
    def set_extraction_settings(self, settings_dict=None, **kwargs):
        """

        @param settings_dict:
        @param kwargs:
        """
        if isinstance(settings_dict, dict):
            self.sigExtractionSettingsChanged.emit(settings_dict)
        else:
            self.sigExtractionSettingsChanged.emit(kwargs)
        return

    @QtCore.Slot(int)
    @QtCore.Slot(float)
    def set_timer_interval(self, interval):
        """

        @param int|float interval: The timer interval to set in seconds.
        """
        if isinstance(interval, (int, float)):
            self.sigTimerIntervalChanged.emit(interval)
        return

    @QtCore.Slot(str)
    def set_alternative_data_type(self, alt_data_type):
        """

        @param alt_data_type:
        @return:
        """
        if isinstance(alt_data_type, str):
            self.sigAlternativeDataTypeChanged.emit(alt_data_type)
        return

    @QtCore.Slot()
    def manually_pull_data(self):
        """
        """
        self.sigManuallyPullData.emit()
        return

    @QtCore.Slot(bool)
    def toggle_ext_microwave(self, switch_on):
        """

        @param switch_on:
        """
        if isinstance(switch_on, bool):
            self.sigToggleExtMicrowave.emit(switch_on)
        return

    @QtCore.Slot(bool)
    def ext_microwave_running_updated(self, is_running):
        """

        @param is_running:
        """
        if isinstance(is_running, bool):
            self.status_dict['microwave_running'] = is_running
            self.sigExtMicrowaveRunningUpdated.emit(is_running)
        return

    @QtCore.Slot(bool)
    def toggle_pulse_generator(self, switch_on):
        """

        @param switch_on:
        """
        if isinstance(switch_on, bool):
            self.sigTogglePulser.emit(switch_on)
        return

    @QtCore.Slot(bool)
    def pulser_running_updated(self, is_running):
        """

        @param is_running:
        """
        if isinstance(is_running, bool):
            self.status_dict['pulser_running'] = is_running
            self.sigPulserRunningUpdated.emit(is_running)
        return

    @QtCore.Slot(bool)
    @QtCore.Slot(bool, str)
    def toggle_pulsed_measurement(self, start, stash_raw_data_tag=''):
        """

        @param bool start:
        @param str stash_raw_data_tag:
        """
        if isinstance(start, bool) and isinstance(stash_raw_data_tag, str):
            self.sigToggleMeasurement.emit(start, stash_raw_data_tag)
        return

    @QtCore.Slot(bool)
    def toggle_pulsed_measurement_pause(self, pause):
        """

        @param pause:
        """
        if isinstance(pause, bool):
            self.sigToggleMeasurementPause.emit(pause)
        return

    @QtCore.Slot(bool, bool)
    def measurement_status_updated(self, is_running, is_paused):
        """

        @param is_running:
        @param is_paused:
        """
        if isinstance(is_running, bool) and isinstance(is_paused, bool):
            self.status_dict['measurement_running'] = is_running
            self.sigMeasurementStatusUpdated.emit(is_running, is_paused)
        return

    @QtCore.Slot(str)
    @QtCore.Slot(str, bool)
    def do_fit(self, fit_function, use_alternative_data=False):
        """

        @param str fit_function:
        @param bool use_alternative_data:
        """
        if isinstance(fit_function, str) and isinstance(use_alternative_data, bool):
            self.status_dict['fitting_busy'] = True
            self.sigDoFit.emit(fit_function, use_alternative_data)
        return

    @QtCore.Slot(str, np.ndarray, object, bool)
    def fit_updated(self, fit_name, fit_data, fit_result, use_alternative_data):
        """

        @return:
        """
        self.status_dict['fitting_busy'] = False
        self.sigFitUpdated.emit(fit_name, fit_data, fit_result, use_alternative_data)
        return

    def save_measurement_data(self, tag=None, with_error=True, save_laser_pulses=True, save_pulsed_measurement=True,
                              save_figure=True):
        """
        Prepare data to be saved and create a proper plot of the data.
        This is just handed over to the measurement logic.

        @param str tag: a filetag which will be included in the filename
        @param bool with_error: select whether errors should be saved/plotted
        @param bool save_laser_pulses: select whether extracted lasers should be saved
        @param bool save_pulsed_measurement: select whether final measurement should be saved
        @param bool save_figure: select whether png and pdf should be saved

        @return str: filepath where data were saved
        """
        self.pulsedmeasurementlogic().save_measurement_data(tag, with_error, save_laser_pulses, save_pulsed_measurement,
                                                            save_figure)
        return

    #######################################################################
    ###             Sequence generator properties                       ###
    #######################################################################
    @property
    def pulse_generator_constraints(self):
        return self.sequencegeneratorlogic().pulse_generator_constraints

    @property
    def pulse_generator_settings(self):
        return self.sequencegeneratorlogic().pulse_generator_settings

    @property
    def generation_parameters(self):
        return self.sequencegeneratorlogic().generation_parameters

    @property
    def analog_channels(self):
        return self.sequencegeneratorlogic().analog_channels

    @property
    def digital_channels(self):
        return self.sequencegeneratorlogic().digital_channels

    @property
    def saved_pulse_blocks(self):
        return self.sequencegeneratorlogic().saved_pulse_blocks

    @property
    def saved_pulse_block_ensembles(self):
        return self.sequencegeneratorlogic().saved_pulse_block_ensembles

    @property
    def saved_pulse_sequences(self):
        return self.sequencegeneratorlogic().saved_pulse_sequences

    @property
    def sampled_waveforms(self):
        return self.sequencegeneratorlogic().sampled_waveforms

    @property
    def sampled_sequences(self):
        return self.sequencegeneratorlogic().sampled_sequences

    @property
    def loaded_asset(self):
        return self.sequencegeneratorlogic().loaded_asset

    @property
    def generate_methods(self):
        return getattr(self.sequencegeneratorlogic(), 'generate_methods', dict())

    @property
    def generate_method_params(self):
        return getattr(self.sequencegeneratorlogic(), 'generate_method_params', dict())

    #######################################################################
    ###             Sequence generator methods                          ###
    #######################################################################
    @QtCore.Slot()
    def clear_pulse_generator(self):
        still_busy = self.status_dict['sampling_ensemble_busy'] or self.status_dict[
            'sampling_sequence_busy'] or self.status_dict['loading_busy'] or self.status_dict[
                                   'sampload_busy']
        if still_busy:
            self.log.error('Can not clear pulse generator. Sampling/Loading still in progress.')
        elif self.status_dict['measurement_running']:
            self.log.error('Can not clear pulse generator. Measurement is still running.')
        else:
            if self.status_dict['pulser_running']:
                self.log.warning('Can not clear pulse generator while it is still running. '
                                 'Turned off.')
                self.pulsedmeasurementlogic().pulse_generator_off()
            self.sigClearPulseGenerator.emit()
        return

    @QtCore.Slot(str)
    @QtCore.Slot(str, bool)
    def sample_ensemble(self, ensemble_name, with_load=False):
        already_busy = self.status_dict['sampling_ensemble_busy'] or self.status_dict[
            'sampling_sequence_busy'] or self.sequencegeneratorlogic().module_state() == 'locked'
        if already_busy:
            self.log.error('Sampling of a different asset already in progress.\n'
                           'PulseBlockEnsemble "{0}" not sampled!'.format(ensemble_name))
        else:
            if with_load:
                self.status_dict['sampload_busy'] = True
            self.status_dict['sampling_ensemble_busy'] = True
            self.sigSampleBlockEnsemble.emit(ensemble_name)
        return

    @QtCore.Slot(object)
    def sample_ensemble_finished(self, ensemble):
        self.status_dict['sampling_ensemble_busy'] = False
        self.sigSampleEnsembleComplete.emit(ensemble)
        if self.status_dict['sampload_busy'] and not self.status_dict['sampling_sequence_busy']:
            if ensemble is None:
                self.status_dict['sampload_busy'] = False
                self.sigLoadedAssetUpdated.emit(*self.loaded_asset)
            else:
                self.load_ensemble(ensemble.name)
        return

    @QtCore.Slot(str)
    @QtCore.Slot(str, bool)
    def sample_sequence(self, sequence_name, with_load=False):
        already_busy = self.status_dict['sampling_ensemble_busy'] or self.status_dict[
            'sampling_sequence_busy'] or self.sequencegeneratorlogic().module_state() == 'locked'
        if already_busy:
            self.log.error('Sampling of a different asset already in progress.\n'
                           'PulseSequence "{0}" not sampled!'.format(sequence_name))
        else:
            if with_load:
                self.status_dict['sampload_busy'] = True
            self.status_dict['sampling_sequence_busy'] = True
            self.sigSampleSequence.emit(sequence_name)
        return

    @QtCore.Slot(object)
    def sample_sequence_finished(self, sequence):
        self.status_dict['sampling_sequence_busy'] = False
        self.sigSampleSequenceComplete.emit(sequence)
        if self.status_dict['sampload_busy']:
            if sequence is None:
                self.status_dict['sampload_busy'] = False
                self.sigLoadedAssetUpdated.emit(*self.loaded_asset)
            else:
                self.load_sequence(sequence.name)
        return

    @QtCore.Slot(str)
    def load_ensemble(self, ensemble_name):
        if self.status_dict['loading_busy']:
            self.log.error('Loading of a different asset already in progress.\n'
                           'PulseBlockEnsemble "{0}" not loaded!'.format(ensemble_name))
            self.loaded_asset_updated(*self.loaded_asset)
        elif self.status_dict['measurement_running']:
            self.log.error('Loading of ensemble not possible while measurement is running.\n'
                           'PulseBlockEnsemble "{0}" not loaded!'.format(ensemble_name))
            self.loaded_asset_updated(*self.loaded_asset)
        else:
            self.status_dict['loading_busy'] = True
            if self.status_dict['pulser_running']:
                self.log.warning('Can not load new asset into pulse generator while it is still '
                                 'running. Turned off.')
                self.pulsedmeasurementlogic().pulse_generator_off()
            self.sigLoadBlockEnsemble.emit(ensemble_name)
        return

    @QtCore.Slot(str)
    def load_sequence(self, sequence_name):
        if self.status_dict['loading_busy']:
            self.log.error('Loading of a different asset already in progress.\n'
                           'PulseSequence "{0}" not loaded!'.format(sequence_name))
            self.loaded_asset_updated(*self.loaded_asset)
        elif self.status_dict['measurement_running']:
            self.log.error('Loading of sequence not possible while measurement is running.\n'
                           'PulseSequence "{0}" not loaded!'.format(sequence_name))
            self.loaded_asset_updated(*self.loaded_asset)
        else:
            self.status_dict['loading_busy'] = True
            if self.status_dict['pulser_running']:
                self.log.warning('Can not load new asset into pulse generator while it is still '
                                 'running. Turned off.')
                self.pulsedmeasurementlogic().pulse_generator_off()
            self.sigLoadSequence.emit(sequence_name)
        return

    @QtCore.Slot(str, str)
    def loaded_asset_updated(self, asset_name, asset_type):
        """

        @param asset_name:
        @param asset_type:
        @return:
        """
        self.status_dict['sampload_busy'] = False
        self.status_dict['loading_busy'] = False
        self.sigLoadedAssetUpdated.emit(asset_name, asset_type)
        # Transfer sequence information from PulseBlockEnsemble or PulseSequence to
        # PulsedMeasurementLogic to be able to invoke measurement settings from them
        if not asset_type:
            # If no asset loaded or asset type unknown, clear sequence_information dict

            object_instance = None
        elif asset_type == 'PulseBlockEnsemble':
            object_instance = self.saved_pulse_block_ensembles.get(asset_name)
        elif asset_type == 'PulseSequence':
            object_instance = self.saved_pulse_sequences.get(asset_name)
        else:
            object_instance = None

        if object_instance is None:
            self.pulsedmeasurementlogic().sampling_information = dict()
            self.pulsedmeasurementlogic().measurement_information = dict()
        else:
            self.pulsedmeasurementlogic().sampling_information = object_instance.sampling_information
            self.pulsedmeasurementlogic().measurement_information = object_instance.measurement_information
        return

    @QtCore.Slot(object)
    def save_pulse_block(self, block_instance):
        """

        @param block_instance:
        @return:
        """
        self.sigSavePulseBlock.emit(block_instance)
        return

    @QtCore.Slot(object)
    def save_block_ensemble(self, ensemble_instance):
        """


        @param ensemble_instance:
        @return:
        """
        self.sigSaveBlockEnsemble.emit(ensemble_instance)
        return

    @QtCore.Slot(object)
    def save_sequence(self, sequence_instance):
        """

        @param sequence_instance:
        @return:
        """
        self.sigSaveSequence.emit(sequence_instance)
        return

    @QtCore.Slot(str)
    def delete_pulse_block(self, block_name):
        """

        @param block_name:
        @return:
        """
        self.sigDeletePulseBlock.emit(block_name)
        return

    @QtCore.Slot()
    def delete_all_pulse_blocks(self):
        """
        Helper method to delete all pulse blocks at once.
        """
        to_delete = tuple(self.saved_pulse_blocks)
        for block_name in to_delete:
            self.sigDeletePulseBlock.emit(block_name)
        return

    @QtCore.Slot(str)
    def delete_block_ensemble(self, ensemble_name):
        """

        @param ensemble_name:
        @return:
        """
        if self.status_dict['pulser_running'] and self.loaded_asset[0] == ensemble_name and self.loaded_asset[1] == 'PulseBlockEnsemble':
            self.log.error('Can not delete PulseBlockEnsemble "{0}" since the corresponding '
                           'waveform(s) is(are) currently loaded and running.'
                           ''.format(ensemble_name))
        else:
            self.sigDeleteBlockEnsemble.emit(ensemble_name)
        return

    @QtCore.Slot()
    def delete_all_block_ensembles(self):
        """
        Helper method to delete all pulse block ensembles at once.
        """
        if self.status_dict['pulser_running'] or self.status_dict['measurement_running']:
            self.log.error('Can not delete all PulseBlockEnsembles. Pulse generator is currently '
                           'running or measurement is in progress.')
        else:
            to_delete = tuple(self.saved_pulse_block_ensembles)
            for ensemble_name in to_delete:
                self.sigDeleteBlockEnsemble.emit(ensemble_name)
        return

    @QtCore.Slot(str)
    def delete_sequence(self, sequence_name):
        """

        @param sequence_name:
        @return:
        """
        if self.status_dict['pulser_running'] and self.loaded_asset[0] == sequence_name and self.loaded_asset[1] == 'PulseSequence':
            self.log.error('Can not delete PulseSequence "{0}" since the corresponding sequence is '
                           'currently loaded and running.'.format(sequence_name))
        else:
            self.sigDeleteSequence.emit(sequence_name)
        return

    @QtCore.Slot()
    def delete_all_pulse_sequences(self):
        """
        Helper method to delete all pulse sequences at once.
        """
        if self.status_dict['pulser_running'] or self.status_dict['measurement_running']:
            self.log.error('Can not delete all PulseSequences. Pulse generator is currently '
                           'running or measurement is in progress.')
        else:
            to_delete = tuple(self.saved_pulse_sequences)
            for sequence_name in to_delete:
                self.sigDeleteSequence.emit(sequence_name)
        return

    @QtCore.Slot(dict)
    def set_pulse_generator_settings(self, settings_dict=None, **kwargs):
        """
        Either accept a settings dictionary as positional argument or keyword arguments.
        If both are present both are being used by updating the settings_dict with kwargs.
        The keyword arguments take precedence over the items in settings_dict if there are
        conflicting names.

        @param settings_dict:
        @param kwargs:
        @return:
        """
        if not isinstance(settings_dict, dict):
            settings_dict = kwargs
        else:
            settings_dict.update(kwargs)
        self.sigGeneratorSettingsChanged.emit(settings_dict)
        return

    @QtCore.Slot(dict)
    def set_generation_parameters(self, settings_dict=None, **kwargs):
        """
        Either accept a settings dictionary as positional argument or keyword arguments.
        If both are present both are being used by updating the settings_dict with kwargs.
        The keyword arguments take precedence over the items in settings_dict if there are
        conflicting names.

        @param settings_dict:
        @param kwargs:
        @return:
        """
        if not isinstance(settings_dict, dict):
            settings_dict = kwargs
        else:
            settings_dict.update(kwargs)

        # Force empty gate channel if fast counter is not gated
        if 'gate_channel' in settings_dict and not self.fast_counter_settings.get('is_gated'):
            settings_dict['gate_channel'] = ''
        self.sigSamplingSettingsChanged.emit(settings_dict)
        return

    @QtCore.Slot(str)
    @QtCore.Slot(str, dict)
    @QtCore.Slot(str, dict, bool)
    def generate_predefined_sequence(self, generator_method_name, kwarg_dict=None, sample_and_load=False):
        """

        @param generator_method_name:
        @param kwarg_dict:
        @param sample_and_load:
        @return:
        """
        if not isinstance(kwarg_dict, dict):
            kwarg_dict = dict()
        self.status_dict['predefined_generation_busy'] = True
        if sample_and_load:
            self.status_dict['sampload_busy'] = True
        self.sigGeneratePredefinedSequence.emit(generator_method_name, kwarg_dict)
        return

    @QtCore.Slot(object, bool)
    def predefined_sequence_generated(self, asset_name, is_sequence):
        self.status_dict['predefined_generation_busy'] = False
        if asset_name is None:
            self.status_dict['sampload_busy'] = False
        self.sigPredefinedSequenceGenerated.emit(asset_name, is_sequence)
        if self.status_dict['sampload_busy']:
            if is_sequence:
                self.sample_sequence(asset_name, True)
            else:
                self.sample_ensemble(asset_name, True)
        return

    def get_ensemble_info(self, ensemble):
        """
        This helper method is just there for backwards compatibility. Essentially it will call the
        method "analyze_block_ensemble".

        Will return information like length in seconds and bins (with currently set sampling rate)
        as well as number of laser pulses (with currently selected laser/gate channel)

        @param PulseBlockEnsemble ensemble: The PulseBlockEnsemble instance to analyze
        @return (float, int, int): length in seconds, length in bins, number of laser/gate pulses
        """
        return self.sequencegeneratorlogic().get_ensemble_info(ensemble=ensemble)

    def get_sequence_info(self, sequence):
        """
        This helper method will analyze a PulseSequence and return information like length in
        seconds and bins (with currently set sampling rate), number of laser pulses (with currently
        selected laser/gate channel)

        @param PulseSequence sequence: The PulseSequence instance to analyze
        @return (float, int, int): length in seconds, length in bins, number of laser/gate pulses
        """
        return self.sequencegeneratorlogic().get_sequence_info(sequence=sequence)

    def analyze_block_ensemble(self, ensemble):
        """
        This helper method runs through each element of a PulseBlockEnsemble object and extracts
        important information about the Waveform that can be created out of this object.
        Especially the discretization due to the set self.sample_rate is taken into account.
        The positions in time (as integer time bins) of the PulseBlockElement transitions are
        determined here (all the "rounding-to-best-match-value").
        Additional information like the total number of samples, total number of PulseBlockElements
        and the timebins for digital channel low-to-high transitions get returned as well.

        This method assumes that sanity checking has been already performed on the
        PulseBlockEnsemble (via _sampling_ensemble_sanity_check). Meaning it assumes that all
        PulseBlocks are actually present in saved blocks and the channel activation matches the
        current pulse settings.

        @param ensemble: A PulseBlockEnsemble object (see logic.pulse_objects.py)
        @return: number_of_samples (int): The total number of samples in a Waveform provided the
                                              current sample_rate and PulseBlockEnsemble object.
                 total_elements (int): The total number of PulseBlockElements (incl. repetitions) in
                                       the provided PulseBlockEnsemble.
                 elements_length_bins (1D numpy.ndarray[int]): Array of number of timebins for each
                                                               PulseBlockElement in chronological
                                                               order (incl. repetitions).
                 digital_rising_bins (dict): Dictionary with keys being the digital channel
                                             descriptor string and items being arrays of
                                             chronological low-to-high transition positions
                                             (in timebins; incl. repetitions) for each digital
                                             channel.
        """
        return self.sequencegeneratorlogic().analyze_block_ensemble(ensemble=ensemble)

    def analyze_sequence(self, sequence):
        """
        This helper method runs through each step of a PulseSequence object and extracts
        important information about the Sequence that can be created out of this object.
        Especially the discretization due to the set self.sample_rate is taken into account.
        The positions in time (as integer time bins) of the PulseBlockElement transitions are
        determined here (all the "rounding-to-best-match-value").
        Additional information like the total number of samples, total number of PulseBlockElements
        and the timebins for digital channel low-to-high transitions get returned as well.

        This method assumes that sanity checking has been already performed on the
        PulseSequence (via _sampling_ensemble_sanity_check). Meaning it assumes that all
        PulseBlocks are actually present in saved blocks and the channel activation matches the
        current pulse settings.

        @param sequence: A PulseSequence object (see logic.pulse_objects.py)
        @return: number_of_samples (int): The total number of samples in a Waveform provided the
                                              current sample_rate and PulseBlockEnsemble object.
                 total_elements (int): The total number of PulseBlockElements (incl. repetitions) in
                                       the provided PulseBlockEnsemble.
                 elements_length_bins (1D numpy.ndarray[int]): Array of number of timebins for each
                                                               PulseBlockElement in chronological
                                                               order (incl. repetitions).
                 digital_rising_bins (dict): Dictionary with keys being the digital channel
                                             descriptor string and items being arrays of
                                             chronological low-to-high transition positions
                                             (in timebins; incl. repetitions) for each digital
                                             channel.
        """
        return self.sequencegeneratorlogic().analyze_sequence(sequence=sequence)

    #######################################################################
    ###             Helper  methods                                     ###
    #######################################################################
    # def _get_asset_parameters(self, asset_obj):
    #     """
    #
    #     @param asset_obj:
    #     @return:
    #     """
    #     if type(asset_obj).__name__ == 'PulseSequence':
    #         self.log.warning('Calculation of measurement sequence parameters not implemented yet '
    #                          'for PulseSequence objects.')
    #         return {'err_code': -1}
    #     # Create return dictionary
    #     return_params = {'err_code': 0}
    #
    #     # Get activation config and name
    #     if asset_obj.activation_config is None:
    #         return_params['activation_config'] = self._generator_logic.activation_config
    #         self.log.warning('No activation config specified in asset "{0}" metadata. Choosing '
    #                          'currently set activation config "{1}" from sequence_generator_logic.'
    #                          ''.format(asset_obj.name, return_params['activation_config']))
    #     else:
    #         return_params['activation_config'] = asset_obj.activation_config
    #     config_name = None
    #     avail_configs = self._measurement_logic.get_pulser_constraints().activation_config
    #     for config in avail_configs:
    #         if return_params['activation_config'] == avail_configs[config]:
    #             config_name = config
    #             break
    #     if config_name is None:
    #         self.log.error('Activation config {0} is not part of the allowed activation '
    #                        'configs in the pulse generator hardware.'
    #                        ''.format(return_params['activation_config']))
    #         return_params['err_code'] = -1
    #         return return_params
    #     else:
    #         return_params['config_name'] = config_name
    #
    #     # Get analogue voltages
    #     if asset_obj.amplitude_dict is None:
    #         return_params['amplitude_dict'] = self._generator_logic.amplitude_dict
    #         self.log.warning('No amplitude dictionary specified in asset "{0}" metadata. Choosing '
    #                          'currently set amplitude dict "{1}" from sequence_generator_logic.'
    #                          ''.format(asset_obj.name, return_params['amplitude_dict']))
    #     else:
    #         return_params['amplitude_dict'] = asset_obj.amplitude_dict
    #
    #     # Get sample rate
    #     if asset_obj.sample_rate is None:
    #         return_params['sample_rate'] = self._generator_logic.sample_rate
    #         self.log.warning('No sample rate specified in asset "{0}" metadata. Choosing '
    #                          'currently set sample rate "{1:.2e}" from sequence_generator_logic.'
    #                          ''.format(asset_obj.name, return_params['sample_rate']))
    #     else:
    #         return_params['sample_rate'] = asset_obj.sample_rate
    #
    #     # Get sequence length
    #     return_params['sequence_length'] = asset_obj.length_s
    #     return_params['sequence_length_bins'] = asset_obj.length_s*self._generator_logic.sample_rate
    #
    #     # Get number of laser pulses and max laser length
    #     if asset_obj.laser_channel is None:
    #         laser_chnl = self._generator_logic.laser_channel
    #         self.log.warning('No laser channel specified in asset "{0}" metadata. Choosing '
    #                          'currently set laser channel "{1}" from sequence_generator_logic.'
    #                          ''.format(asset_obj.name, laser_chnl))
    #     else:
    #         laser_chnl = asset_obj.laser_channel
    #     num_of_lasers = 0
    #     max_laser_length = 0.0
    #     tmp_laser_on = False
    #     tmp_laser_length = 0.0
    #     for block, reps in asset_obj.block_list:
    #         tmp_lasers_num = 0
    #         for element in block.element_list:
    #             if 'd_ch' in laser_chnl:
    #                 d_channels = [ch for ch in return_params['activation_config'] if 'd_ch' in ch]
    #                 chnl_index = d_channels.index(laser_chnl)
    #                 if not tmp_laser_on and element.digital_high[chnl_index]:
    #                     tmp_laser_on = True
    #                     tmp_lasers_num += 1
    #                 elif not element.digital_high[chnl_index]:
    #                     tmp_laser_on = False
    #                 if tmp_laser_on:
    #                     if element.increment_s > 1.0e-15:
    #                         tmp_laser_length += (element.init_length_s + reps * element.increment_s)
    #                     else:
    #                         tmp_laser_length += element.init_length_s
    #                     if tmp_laser_length > max_laser_length:
    #                         max_laser_length = tmp_laser_length
    #                 else:
    #                     tmp_laser_length = 0.0
    #             else:
    #                 self.log.error('Invoke measurement settings from a PulseBlockEnsemble with '
    #                                'analogue laser channel is not implemented yet.')
    #                 return_params['err_code'] = -1
    #                 return
    #         num_of_lasers += (tmp_lasers_num * (reps + 1))
    #     return_params['num_of_lasers'] = num_of_lasers
    #     return_params['max_laser_length'] = max_laser_length
    #
    #     # Get laser ignore list
    #     if asset_obj.laser_ignore_list is None:
    #         return_params['laser_ignore_list'] = []
    #         self.log.warning('No laser ignore list specified in asset "{0}" metadata. '
    #                          'Assuming that no lasers should be ignored.'.format(asset_obj.name))
    #     else:
    #         return_params['laser_ignore_list'] = asset_obj.laser_ignore_list
    #
    #     # Get alternating
    #     if asset_obj.alternating is None:
    #         return_params['is_alternating'] = self._measurement_logic.alternating
    #         self.log.warning('No alternating specified in asset "{0}" metadata. Choosing '
    #                          'currently set state "{1}" from pulsed_measurement_logic.'
    #                          ''.format(asset_obj.name, return_params['is_alternating']))
    #     else:
    #         return_params['is_alternating'] = asset_obj.alternating
    #
    #     # Get controlled variable values
    #     if len(asset_obj.controlled_vals_array) < 1:
    #         ana_lasers = num_of_lasers - len(return_params['laser_ignore_list'])
    #         controlled_vals_array = np.arange(1, ana_lasers + 1)
    #         self.log.warning('No measurement ticks specified in asset "{0}" metadata. Choosing '
    #                          'laser indices instead.'.format(asset_obj.name))
    #         if return_params['is_alternating']:
    #             controlled_vals_array = controlled_vals_array[0:ana_lasers//2]
    #     else:
    #         controlled_vals_array = asset_obj.controlled_vals_array
    #     return_params['controlled_vals_arr'] = controlled_vals_array
    #
    #     # return all parameters
    #     return return_params
