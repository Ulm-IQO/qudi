# -*- coding: utf-8 -*-

"""
This file contains the Qudi sequence generator logic for general sequence structure.

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
import pickle
import time
import copy
import traceback

from qtpy import QtCore
from collections import OrderedDict
from core.statusvariable import StatusVar
from core.connector import Connector
from core.configoption import ConfigOption
from core.util.modules import get_main_dir, get_home_dir
from core.util.helpers import natural_sort
from core.util.network import netobtain
from logic.generic_logic import GenericLogic
from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble, PulseSequence
from logic.pulsed.pulse_objects import PulseObjectGenerator, PulseBlockElement
from logic.pulsed.sampling_functions import SamplingFunctions
from interface.pulser_interface import SequenceOption


class SequenceGeneratorLogic(GenericLogic):
    """
    This is the Logic class for the pulse (sequence) generation.

    It is responsible for creating the theoretical (ideal) contruction plan for a pulse sequence or
    waveform (digital and/or analog) by creating PulseBlockElements, PulseBlocks,
    PulseBlockEnsembles and PulseSequences.
    Based on these objects the logic can sample waveforms according to the underlying hardware
    constraints (especially the sample rate) and upload these samples to the connected pulse
    generator hardware.

    This logic is also responsible to manipulate and read back hardware settings for
    waveform/sequence playback (pp-amplitude, sample rate, active channels etc.).
    """

    # declare connectors
    pulsegenerator = Connector(interface='PulserInterface')

    # configuration options
    _assets_storage_dir = ConfigOption(name='assets_storage_path',
                                       default=os.path.join(get_home_dir(), 'saved_pulsed_assets'),
                                       missing='warn')
    _overhead_bytes = ConfigOption(name='overhead_bytes', default=0, missing='nothing')
    # Optional additional paths to import from
    _additional_methods_import_path = ConfigOption(name='additional_predefined_methods_path',
                                                   default=None,
                                                   missing='nothing')
    _sampling_functions_import_path = ConfigOption(name='additional_sampling_functions_path',
                                                   default=None,
                                                   missing='nothing')

    # status vars
    # Global parameters describing the channel usage and common parameters used during pulsed object
    # generation for predefined methods.
    _generation_parameters = StatusVar(default=OrderedDict([('laser_channel', 'd_ch1'),
                                                            ('sync_channel', ''),
                                                            ('gate_channel', ''),
                                                            ('microwave_channel', 'a_ch1'),
                                                            ('microwave_frequency', 2.87e9),
                                                            ('microwave_amplitude', 0.0),
                                                            ('rabi_period', 100e-9),
                                                            ('laser_length', 3e-6),
                                                            ('laser_delay', 500e-9),
                                                            ('wait_time', 1e-6),
                                                            ('analog_trigger_voltage', 0.0)]))

    # The created pulse objects (PulseBlock, PulseBlockEnsemble, PulseSequence) are saved in
    # these dictionaries. The keys are the names.
    # _saved_pulse_blocks = StatusVar(default=OrderedDict())
    # _saved_pulse_block_ensembles = StatusVar(default=OrderedDict())
    # _saved_pulse_sequences = StatusVar(default=OrderedDict())

    # define signals
    sigBlockDictUpdated = QtCore.Signal(dict)
    sigEnsembleDictUpdated = QtCore.Signal(dict)
    sigSequenceDictUpdated = QtCore.Signal(dict)
    sigSampleEnsembleComplete = QtCore.Signal(object)
    sigSampleSequenceComplete = QtCore.Signal(object)
    sigLoadedAssetUpdated = QtCore.Signal(str, str)
    sigGeneratorSettingsUpdated = QtCore.Signal(dict)
    sigSamplingSettingsUpdated = QtCore.Signal(dict)
    sigAvailableWaveformsUpdated = QtCore.Signal(list)
    sigAvailableSequencesUpdated = QtCore.Signal(list)

    sigPredefinedSequenceGenerated = QtCore.Signal(object, bool)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.debug('The following configuration was found.')
        for key in config.keys():
            self.log.debug('{0}: {1}'.format(key, config[key]))

        # current pulse generator settings that are frequently used by this logic.
        # Save them here since reading them from device every time they are used may take some time.
        self.__activation_config = ('', set())  # Activation config name and set of active channels
        self.__sample_rate = 0.0  # Sample rate in samples/s
        self.__analog_levels = (dict(), dict())  # Tuple of two dict (<pp_amplitude>, <offset>)
        # Dict keys are analog channel descriptors
        self.__digital_levels = (dict(), dict())  # Tuple of two dict (<low_volt>, <high_volt>)
        # Dict keys are digital channel descriptors
        self.__interleave = False  # Flag to indicate use of interleave
        # Set of available flags
        self.__flags = set()

        # A flag indicating if sampling of a sequence is in progress
        self.__sequence_generation_in_progress = False

        # Get instance of PulseObjectGenerator which takes care of collecting all predefined methods
        self._pog = None

        # The created pulse objects (PulseBlock, PulseBlockEnsemble, PulseSequence) are saved in
        # these dictionaries. The keys are the names.
        self._saved_pulse_blocks = OrderedDict()
        self._saved_pulse_block_ensembles = OrderedDict()
        self._saved_pulse_sequences = OrderedDict()
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        if not os.path.exists(self._assets_storage_dir):
            os.makedirs(self._assets_storage_dir)

        # directory for additional generate methods to import
        # import path for generator modules from default dir (logic.predefined_generate_methods)
        self._predefined_path_list = [os.path.join(get_main_dir(), 'logic', 'pulsed', 'predefined_generate_methods')]

        if self._additional_methods_import_path:
            if isinstance(self._additional_methods_import_path, str):
                self._additional_methods_import_path = [self._additional_methods_import_path]

            if isinstance(self._additional_methods_import_path, (list, tuple, set)):
                for method_import_path in self._additional_methods_import_path:
                    if not os.path.exists(method_import_path):
                        self.log.error('Specified path "{0}" for import of additional generate methods '
                                       'does not exist.'.format(method_import_path))
                    else:
                        self._predefined_path_list.append(method_import_path)
            else:
                self.log.error('ConfigOption additional_predefined_methods_path needs to either be a string or '
                               'a list of strings.')

        # Initialize SamplingFunctions class by handing over a list of paths to import
        # sampling functions from.
        sf_path_list = [os.path.join(get_main_dir(), 'logic', 'pulsed', 'sampling_function_defs')]
        if self._sampling_functions_import_path:
            if isinstance(self._sampling_functions_import_path, str):
                self._sampling_functions_import_path = [self._sampling_functions_import_path]

            if isinstance(self._sampling_functions_import_path, (list, tuple, set)):
                for functions_import_path in self._sampling_functions_import_path:
                    if not os.path.exists(functions_import_path):
                        self.log.error('Specified path "{0}" for import of additional_sampling_functions_path '
                                       'does not exist.'.format(functions_import_path))
                    else:
                        sf_path_list.append(functions_import_path)
            else:
                self.log.error('ConfigOption additional_sampling_functions_path needs to either be a string or '
                               'a list of strings.')
        SamplingFunctions.import_sampling_functions(sf_path_list)

        # Read back settings from device and update instance variables accordingly
        self._read_settings_from_device()

        # Update saved blocks/ensembles/sequences from serialized files
        self._saved_pulse_blocks = OrderedDict()
        self._saved_pulse_block_ensembles = OrderedDict()
        self._saved_pulse_sequences = OrderedDict()
        self._update_blocks_from_file()
        self._update_ensembles_from_file()
        self._update_sequences_from_file()

        # Get instance of PulseObjectGenerator which takes care of collecting all predefined methods
        self._pog = PulseObjectGenerator(sequencegeneratorlogic=self)

        self.__sequence_generation_in_progress = False
        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        return

    # @_saved_pulse_blocks.constructor
    # def _restore_saved_blocks(self, block_list):
    #     return_block_dict = OrderedDict()
    #     if block_list is not None:
    #         for block_dict in block_list:
    #             return_block_dict[block_dict['name']] = PulseBlock.block_from_dict(block_dict)
    #     return return_block_dict
    #
    #
    # @_saved_pulse_blocks.representer
    # def _convert_saved_blocks(self, block_dict):
    #     if block_dict is None:
    #         return None
    #     else:
    #         block_list = list()
    #         for block in block_dict.values():
    #             block_list.append(block.get_dict_representation())
    #         return block_list
    #
    # @_saved_pulse_block_ensembles.constructor
    # def _restore_saved_ensembles(self, ensemble_list):
    #     return_ensemble_dict = OrderedDict()
    #     if ensemble_list is not None:
    #         for ensemble_dict in ensemble_list:
    #             return_ensemble_dict[ensemble_dict['name']] = PulseBlockEnsemble.ensemble_from_dict(
    #                 ensemble_dict)
    #     return return_ensemble_dict
    #
    # @_saved_pulse_block_ensembles.representer
    # def _convert_saved_ensembles(self, ensemble_dict):
    #     if ensemble_dict is None:
    #         return None
    #     else:
    #         ensemble_list = list()
    #         for ensemble in ensemble_dict.values():
    #             ensemble_list.append(ensemble.get_dict_representation())
    #         return ensemble_list
    #
    # @_saved_pulse_sequences.constructor
    # def _restore_saved_sequences(self, sequence_list):
    #     return_sequence_dict = OrderedDict()
    #     if sequence_list is not None:
    #         for sequence_dict in sequence_list:
    #             return_sequence_dict[sequence_dict['name']] = PulseBlockEnsemble.ensemble_from_dict(
    #                 sequence_dict)
    #     return return_sequence_dict
    #
    # @_saved_pulse_sequences.representer
    # def _convert_saved_sequences(self, sequence_dict):
    #     if sequence_dict is None:
    #         return None
    #     else:
    #         sequence_list = list()
    #         for sequence in sequence_dict.values():
    #             sequence_list.append(sequence.get_dict_representation())
    #         return sequence_list

    ############################################################################
    # Pulse generator control methods and properties
    ############################################################################
    @property
    def predefined_methods_import_path(self):
        return self._predefined_path_list

    @property
    def pulse_generator_settings(self):
        settings_dict = dict()
        settings_dict['activation_config'] = tuple(self.__activation_config)
        settings_dict['sample_rate'] = float(self.__sample_rate)
        settings_dict['analog_levels'] = tuple(self.__analog_levels)
        settings_dict['digital_levels'] = tuple(self.__digital_levels)
        settings_dict['interleave'] = bool(self.__interleave)
        settings_dict['flags'] = set(self.__flags)
        return settings_dict

    @pulse_generator_settings.setter
    def pulse_generator_settings(self, settings_dict):
        if isinstance(settings_dict, dict):
            self.set_pulse_generator_settings(settings_dict)
        return

    @property
    def pulse_generator_constraints(self):
        return self.pulsegenerator().get_constraints()

    @property
    def sampled_waveforms(self):
        return netobtain(self.pulsegenerator().get_waveform_names())

    @property
    def sampled_sequences(self):
        return netobtain(self.pulsegenerator().get_sequence_names())

    @property
    def analog_channels(self):
        return {chnl for chnl in self.__activation_config[1] if chnl.startswith('a_ch')}

    @property
    def digital_channels(self):
        return {chnl for chnl in self.__activation_config[1] if chnl.startswith('d_ch')}

    @property
    def loaded_asset(self):
        asset_names, asset_type = self.pulsegenerator().get_loaded_assets()
        name_list = list(asset_names.values())
        if asset_type == 'waveform' and len(name_list) > 0:
            return_type = 'PulseBlockEnsemble'
            return_name = name_list[0].rsplit('_', 1)[0]
            for name in name_list:
                if name.rsplit('_', 1)[0] != return_name:
                    return '', ''
        elif asset_type == 'sequence' and len(name_list) > 0:
            return_type = 'PulseSequence'
            return_name = name_list[0].rsplit('_', 1)[0]
            for name in name_list:
                if name.rsplit('_', 1)[0] != return_name:
                    return '', ''
        else:
            return '', ''
        return return_name, return_type

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
        # Check if pulse generator is running and do nothing if that is the case
        pulser_status, status_dict = self.pulsegenerator().get_status()
        if pulser_status == 0:
            # Determine complete settings dictionary
            if not isinstance(settings_dict, dict):
                settings_dict = kwargs
            else:
                settings_dict.update(kwargs)

            # Set parameters if present
            if 'activation_config' in settings_dict:
                activation_config = settings_dict['activation_config']
                available_configs = self.pulse_generator_constraints.activation_config
                set_config = None
                # Allow argument types str, set and tuple
                if isinstance(activation_config, str):
                    if activation_config in available_configs.keys():
                        set_config = self._apply_activation_config(
                            available_configs[activation_config])
                        self.__activation_config = (activation_config, set_config)
                    else:
                        self.log.error('Unable to set activation config by name.\n'
                                       '"{0}" not found in pulser constraints.'
                                       ''.format(activation_config))
                elif isinstance(activation_config, set):
                    if activation_config in available_configs.values():
                        set_config = self._apply_activation_config(activation_config)
                        config_name = list(available_configs)[
                            list(available_configs.values()).index(activation_config)]
                        self.__activation_config = (config_name, set_config)
                    else:
                        self.log.error('Unable to set activation config "{0}".\n'
                                       'Not found in pulser constraints.'.format(activation_config))
                elif isinstance(activation_config, tuple):
                    if activation_config in available_configs.items():
                        set_config = self._apply_activation_config(activation_config[1])
                        self.__activation_config = (activation_config[0], set_config)
                    else:
                        self.log.error('Unable to set activation config "{0}".\n'
                                       'Not found in pulser constraints.'.format(activation_config))
                # Check if the ultimately set config is part of the constraints
                if set_config is not None and set_config not in available_configs.values():
                    self.log.error('Something went wrong while setting new activation config.')
                    self.__activation_config = ('', set_config)

                # search the generation_parameters for channel specifiers and adjust them if they
                # are no longer valid
                changed_settings = dict()
                ana_chnls = natural_sort(self.analog_channels)
                digi_chnls = natural_sort(self.digital_channels)
                for name in [setting for setting in self.generation_parameters if
                             setting.endswith('_channel')]:
                    channel = self.generation_parameters[name]
                    if isinstance(channel, str) and channel not in self.__activation_config[1]:
                        if channel.startswith('a'):
                            new_channel = ana_chnls[0] if ana_chnls else digi_chnls[0]
                        elif channel.startswith('d'):
                            new_channel = digi_chnls[0] if digi_chnls else ana_chnls[0]
                        else:
                            continue

                        if new_channel is not None:
                            self.log.warning('Change of activation config caused sampling_setting '
                                             '"{0}" to be changed to "{1}".'.format(name,
                                                                                    new_channel))
                            changed_settings[name] = new_channel

            if 'sample_rate' in settings_dict:
                self.__sample_rate = self.pulsegenerator().set_sample_rate(
                    float(settings_dict['sample_rate']))

            if 'analog_levels' in settings_dict:
                self.__analog_levels = self.pulsegenerator().set_analog_level(
                    *settings_dict['analog_levels'])

            if 'digital_levels' in settings_dict:
                self.__digital_levels = self.pulsegenerator().set_digital_level(
                    *settings_dict['digital_levels'])

            if 'interleave' in settings_dict:
                self.__interleave = self.pulsegenerator().set_interleave(
                    bool(settings_dict['interleave']))

        elif len(kwargs) != 0 or isinstance(settings_dict, dict):
            # Only throw warning when arguments have been passed to this method
            self.log.warning('Pulse generator is not idle (status: {0:d}, "{1}").\n'
                             'Unable to apply new settings.'.format(pulser_status,
                                                                    status_dict[pulser_status]))

        # emit update signal for master (GUI or other logic module)
        self.sigGeneratorSettingsUpdated.emit(self.pulse_generator_settings)
        # Apply potential changes to generation_parameters
        try:
            if changed_settings:
                self.generation_parameters = changed_settings
        except UnboundLocalError:
            pass
        return self.pulse_generator_settings

    @QtCore.Slot()
    def clear_pulser(self):
        """
        """
        if self.pulsegenerator().get_status()[0] > 0:
            self.log.error('Can´t clear the pulser as it is running. Switch off the pulser and try again.')
            return -1
        self.pulsegenerator().clear_all()
        # Delete all sampling information from all PulseBlockEnsembles and PulseSequences
        for seq_name in self.saved_pulse_sequences:
            seq = self.saved_pulse_sequences[seq_name]
            seq.sampling_information = dict()
            self.save_sequence(seq)
        for ens_name in self.saved_pulse_block_ensembles:
            ens = self.saved_pulse_block_ensembles[ens_name]
            ens.sampling_information = dict()
            self.save_ensemble(ens)
        self.sigAvailableWaveformsUpdated.emit(self.sampled_waveforms)
        self.sigAvailableSequencesUpdated.emit(self.sampled_sequences)
        self.sigLoadedAssetUpdated.emit('', '')
        return 0

    @QtCore.Slot(str)
    @QtCore.Slot(object)
    def load_ensemble(self, ensemble):
        """

        @param str|PulseBlockEnsemble ensemble:
        """
        # If str has been passed, get the ensemble object from saved ensembles
        if isinstance(ensemble, str):
            ensemble = self.saved_pulse_block_ensembles[ensemble]
            if ensemble is None:
                self.sigLoadedAssetUpdated.emit(*self.loaded_asset)
                return
        if not isinstance(ensemble, PulseBlockEnsemble):
            self.log.error('Unable to load PulseBlockEnsemble into pulser channels.\nArgument ({0})'
                           ' is no instance of PulseBlockEnsemble.'.format(type(ensemble)))
            self.sigLoadedAssetUpdated.emit(*self.loaded_asset)
            return

        # Check if the PulseBlockEnsemble has been sampled already.
        if ensemble.sampling_information:
            # Check if the corresponding waveforms are present in the pulse generator memory
            ready_waveforms = self.sampled_waveforms
            for waveform in ensemble.sampling_information['waveforms']:
                if waveform not in ready_waveforms:
                    self.log.error('Waveform "{0}" associated with PulseBlockEnsemble "{1}" not '
                                   'found on pulse generator device.\nPlease re-generate the '
                                   'PulseBlockEnsemble.'.format(waveform, ensemble.name))
                    self.sigLoadedAssetUpdated.emit(*self.loaded_asset)
                    return

            if self.pulsegenerator().get_status()[0] > 0:
                self.log.error('Can´t load a waveform, because pulser running. Switch off the pulser and try again.')
                return -1
            # Actually load the waveforms to the generic channels
            self.pulsegenerator().load_waveform(ensemble.sampling_information['waveforms'])
        else:
            self.log.error('Loading of PulseBlockEnsemble "{0}" failed.\n'
                           'It has not been generated yet.'.format(ensemble.name))
        self.sigLoadedAssetUpdated.emit(*self.loaded_asset)
        return 0

    @QtCore.Slot(str)
    @QtCore.Slot(object)
    def load_sequence(self, sequence):
        """

        @param str|PulseSequence sequence:
        """
        # If str has been passed, get the sequence object from saved sequences
        if isinstance(sequence, str):
            sequence = self.saved_pulse_sequences.get(sequence)
            if sequence is None:
                self.sigLoadedAssetUpdated.emit(*self.loaded_asset)
                return
        if not isinstance(sequence, PulseSequence):
            self.log.error('Unable to load PulseSequence into pulser channels.\nArgument ({0})'
                           ' is no instance of PulseSequence.'.format(type(sequence)))
            self.sigLoadedAssetUpdated.emit(*self.loaded_asset)
            return

        # Check if the PulseSequence has been sampled already.
        if sequence.sampling_information and sequence.name in self.sampled_sequences:
            # Check if the corresponding waveforms are present in the pulse generator memory
            ready_waveforms = self.sampled_waveforms
            for waveform in sequence.sampling_information['waveforms']:
                if waveform not in ready_waveforms:
                    self.log.error('Waveform "{0}" associated with PulseSequence "{1}" not '
                                   'found on pulse generator device.\nPlease re-generate the '
                                   'PulseSequence.'.format(waveform, sequence.name))
                    self.sigLoadedAssetUpdated.emit(*self.loaded_asset)
                    return

            if self.pulsegenerator().get_status()[0] > 0:
                self.log.error('Can´t load a sequence, because pulser running. Switch off the pulser and try again.')
                return -1
            # Actually load the sequence to the generic channels
            self.pulsegenerator().load_sequence(sequence.name)
        else:
            self.log.error('Loading of PulseSequence "{0}" failed.\n'
                           'It has not been generated yet.'.format(sequence.name))
        self.sigLoadedAssetUpdated.emit(*self.loaded_asset)
        return 0

    def _read_settings_from_device(self):
        """
        """
        # Read activation_config from device.
        channel_state = self.pulsegenerator().get_active_channels()
        current_config = {chnl for chnl in channel_state if channel_state[chnl]}

        # Check if the read back config is a valid config in constraints
        avail_configs = self.pulse_generator_constraints.activation_config
        if current_config in avail_configs.values():
            # Read config found in constraints
            config_name = list(avail_configs)[list(avail_configs.values()).index(current_config)]
            self.__activation_config = (config_name, current_config)
        else:
            # Set first valid config if read config is not valid.
            config_to_set = list(avail_configs.items())[0]
            set_config = self._apply_activation_config(config_to_set[1])
            if set_config != config_to_set[1]:
                self.__activation_config = ('', set_config)
                self.log.error('Error during activation.\n'
                               'Unable to set activation_config that was taken from pulse '
                               'generator constraints.\n'
                               'Probably one or more activation_configs in constraints invalid.')
            else:
                self.__activation_config = config_to_set

        # Read sample rate from device
        self.__sample_rate = float(self.pulsegenerator().get_sample_rate())

        # Read analog levels from device
        self.__analog_levels = self.pulsegenerator().get_analog_level()

        # Read digital levels from device
        self.__digital_levels = self.pulsegenerator().get_digital_level()

        # Read interleave flag from device
        self.__interleave = self.pulsegenerator().get_interleave()

        # Read available flags from device
        self.__flags = set(self.pulsegenerator().get_constraints().flags)

        # Notify new settings to listening module
        self.set_pulse_generator_settings()
        return

    def _apply_activation_config(self, activation_config):
        """

        @param set activation_config: A set of channels to set active (all others inactive)
        """
        channel_state = self.pulsegenerator().get_active_channels()
        for chnl in channel_state:
            if chnl in activation_config:
                channel_state[chnl] = True
            else:
                channel_state[chnl] = False
        set_state = self.pulsegenerator().set_active_channels(channel_state)
        set_config = set([chnl for chnl in set_state if set_state[chnl]])
        return set_config

    ############################################################################
    # Waveform/Sequence generation control methods and properties
    ############################################################################
    @property
    def generate_methods(self):
        return self._pog.predefined_generate_methods

    @property
    def generate_method_params(self):
        return self._pog.predefined_method_parameters

    @property
    def generation_parameters(self):
        return self._generation_parameters.copy()

    @generation_parameters.setter
    def generation_parameters(self, settings_dict):
        if isinstance(settings_dict, dict):
            self.set_generation_parameters(settings_dict)
        return

    @property
    def saved_pulse_blocks(self):
        return self._saved_pulse_blocks

    @property
    def saved_pulse_block_ensembles(self):
        return self._saved_pulse_block_ensembles

    @property
    def saved_pulse_sequences(self):
        return self._saved_pulse_sequences

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
        # Check if generation is in progress and do nothing if that is the case
        if self.module_state() != 'locked':
            # Determine complete settings dictionary
            if not isinstance(settings_dict, dict):
                settings_dict = kwargs
            else:
                settings_dict.update(kwargs)

            # Notify if new keys have been added
            for key in settings_dict:
                if key not in self._generation_parameters:
                    self.log.warning('Setting by name "{0}" not present in generation_parameters.\n'
                                     'Will add it but this could lead to unwanted effects.'
                                     ''.format(key))
            # Sanity checks
            if settings_dict.get('laser_channel'):
                if settings_dict['laser_channel'] not in self.__activation_config[1]:
                    self.log.error('Unable to set laser channel "{0}".\nChannel to set is not part '
                                   'of the current channel activation config ({1}).'
                                   ''.format(settings_dict['laser_channel'],
                                             self.__activation_config[1]))
                    del settings_dict['laser_channel']
            if settings_dict.get('sync_channel'):
                if settings_dict['sync_channel'] not in self.__activation_config[1]:
                    self.log.error('Unable to set sync channel "{0}".\nChannel to set is not part '
                                   'of the current channel activation config ({1}).'
                                   ''.format(settings_dict['sync_channel'],
                                             self.__activation_config[1]))
                    del settings_dict['sync_channel']
            if settings_dict.get('gate_channel'):
                if settings_dict['gate_channel'] not in self.__activation_config[1]:
                    self.log.error('Unable to set gate channel "{0}".\nChannel to set is not part '
                                   'of the current channel activation config ({1}).'
                                   ''.format(settings_dict['gate_channel'],
                                             self.__activation_config[1]))
                    del settings_dict['gate_channel']
            if settings_dict.get('microwave_channel'):
                if settings_dict['microwave_channel'] not in self.__activation_config[1]:
                    self.log.error('Unable to set microwave channel "{0}".\nChannel to set is not '
                                   'part of the current channel activation config ({1}).'
                                   ''.format(settings_dict['microwave_channel'],
                                             self.__activation_config[1]))
                    del settings_dict['microwave_channel']

            # update settings dict
            self._generation_parameters.update(settings_dict)
        else:
            self.log.error('Unable to apply new sampling settings.\n'
                           'SequenceGeneratorLogic is busy generating a waveform/sequence.')

        self.sigSamplingSettingsUpdated.emit(self.generation_parameters)
        return self.generation_parameters

    def save_block(self, block):
        """ Saves a PulseBlock instance

        @param PulseBlock block: PulseBlock instance to save
        """
        self._saved_pulse_blocks[block.name] = block
        self._save_block_to_file(block)
        self.sigBlockDictUpdated.emit(self._saved_pulse_blocks)
        return

    def get_block(self, name):
        """

        @param str name:
        @return PulseBlock:
        """
        if name not in self._saved_pulse_blocks:
            self.log.warning('PulseBlock "{0}" could not be found in saved pulse blocks.\n'
                             'Returning None.'.format(name))
        return self._saved_pulse_blocks.get(name)

    def delete_block(self, name):
        """ Remove the serialized object "name" from the block list and HDD.

        @param name: string, name of the PulseBlock object to be removed.
        """
        # Delete from dict
        if name in self.saved_pulse_blocks:
            del (self._saved_pulse_blocks[name])

        # Delete from disk
        filepath = os.path.join(self._assets_storage_dir, '{0}.block'.format(name))
        if os.path.exists(filepath):
            os.remove(filepath)

        self.sigBlockDictUpdated.emit(self.saved_pulse_blocks)
        return

    def _load_block_from_file(self, block_name):
        """
        De-serializes a PulseBlock instance from file.

        @param str block_name: The name of the PulseBlock instance to de-serialize
        @return PulseBlock: The de-serialized PulseBlock instance
        """
        block = None
        filepath = os.path.join(self._assets_storage_dir, '{0}.block'.format(block_name))
        if os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as file:
                    block = pickle.load(file)
            except pickle.UnpicklingError:
                self.log.error('Failed to de-serialize PulseBlock "{0}" from file.'
                               ''.format(block_name))
                os.remove(filepath)
            except ModuleNotFoundError:
                self.log.error('Failed to de-serialize PulseBlock "{0}" from file because of missing dependencies.\n'
                               'For better debugging I dumped the traceback to debug.'.format(block_name))
                self.log.debug('{0!s}'.format(traceback.format_exc()))
        return block

    def _update_blocks_from_file(self):
        """
        Update the saved_pulse_blocks dict by de-serializing stored file.
        """
        # Get all files in asset directory ending on ".block" and extract a sorted list of
        # PulseBlock names
        with os.scandir(self._assets_storage_dir) as scan:
            names = natural_sort(f.name[:-6] for f in scan if f.is_file and f.name.endswith('.block'))

        # Load all blocks from file
        for block_name in names:
            block = self._load_block_from_file(block_name)
            if block is not None:
                self._saved_pulse_blocks[block_name] = block

        self.sigBlockDictUpdated.emit(self._saved_pulse_blocks)
        return

    def _save_block_to_file(self, block):
        """
        Saves a single PulseBlock instance to file by serialization using pickle.

        @param PulseBlock block: The PulseBlock instance to be saved
        """
        filename = '{0}.block'.format(block.name)
        try:
            with open(os.path.join(self._assets_storage_dir, filename), 'wb') as file:
                pickle.dump(block, file)
        except:
            self.log.error('Failed to serialize PulseBlock "{0}" to file.'.format(block.name))
        return

    def _save_blocks_to_file(self):
        """
        Saves the saved_pulse_blocks dict items to files.
        """
        for block in self._saved_pulse_blocks.values():
            self._save_block_to_file(block)
        return

    def save_ensemble(self, ensemble):
        """ Saves a PulseBlockEnsemble instance

        @param PulseBlockEnsemble ensemble: PulseBlockEnsemble instance to save
        """
        self._saved_pulse_block_ensembles[ensemble.name] = ensemble
        self._save_ensemble_to_file(ensemble)
        self.sigEnsembleDictUpdated.emit(self.saved_pulse_block_ensembles)
        return

    def get_ensemble(self, name):
        """

        @param name:
        @return:
        """
        if name not in self._saved_pulse_block_ensembles:
            self.log.warning('PulseBlockEnsemble "{0}" could not be found in saved pulse block '
                             'ensembles.\nReturning None.'.format(name))
        return self._saved_pulse_block_ensembles.get(name)

    def delete_ensemble(self, name):
        """
        Remove the ensemble with 'name' from the ensemble dict and all associated waveforms
        from the pulser memory.
        """
        # Delete from dict
        if name in self.saved_pulse_block_ensembles:
            # check if ensemble has already been sampled and delete associated waveforms
            if self.saved_pulse_block_ensembles[name].sampling_information:
                self._delete_waveform(
                    self.saved_pulse_block_ensembles[name].sampling_information['waveforms'])
                self.sigAvailableWaveformsUpdated.emit(self.sampled_waveforms)
            # delete PulseBlockEnsemble
            del self._saved_pulse_block_ensembles[name]

        # Delete from disk
        filepath = os.path.join(self._assets_storage_dir, '{0}.ensemble'.format(name))
        if os.path.exists(filepath):
            os.remove(filepath)

        self.sigEnsembleDictUpdated.emit(self.saved_pulse_block_ensembles)
        return

    def _load_ensemble_from_file(self, ensemble_name):
        """
        De-serializes a PulseBlockEnsemble instance from file.

        @param str ensemble_name: The name of the PulseBlockEnsemble instance to de-serialize
        @return PulseBlockEnsemble: The de-serialized PulseBlockEnsemble instance
        """
        ensemble = None
        filepath = os.path.join(self._assets_storage_dir, '{0}.ensemble'.format(ensemble_name))
        if os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as file:
                    ensemble = pickle.load(file)
            except pickle.UnpicklingError:
                self.log.error('Failed to de-serialize PulseBlockEnsemble "{0}" from file. '
                               'Deleting broken file.'.format(ensemble_name))
                os.remove(filepath)
        return ensemble

    def _update_ensembles_from_file(self):
        """
        Update the saved_pulse_block_ensembles dict from temporary file.
        """
        # Get all files in asset directory ending on ".ensemble" and extract a sorted list of
        # PulseBlockEnsemble names
        with os.scandir(self._assets_storage_dir) as scan:
            names = natural_sort(f.name[:-9] for f in scan if f.is_file and f.name.endswith('.ensemble'))

        # Get all waveforms currently stored on pulser hardware in order to delete outdated
        # sampling_information dicts
        sampled_waveforms = set(self.sampled_waveforms)

        # Load all ensembles from file
        for ensemble_name in names:
            ensemble = self._load_ensemble_from_file(ensemble_name)
            if ensemble is not None:
                if ensemble.sampling_information.get('waveforms'):
                    waveform_set = set(ensemble.sampling_information['waveforms'])
                    if not sampled_waveforms.issuperset(waveform_set):
                        ensemble.sampling_information = dict()
                self._saved_pulse_block_ensembles[ensemble_name] = ensemble

        self.sigEnsembleDictUpdated.emit(self.saved_pulse_block_ensembles)
        return

    def _save_ensemble_to_file(self, ensemble):
        """
        Saves a single PulseBlockEnsemble instance to file by serialization using pickle.

        @param PulseBlockEnsemble ensemble: The PulseBlockEnsemble instance to be saved
        """
        filename = '{0}.ensemble'.format(ensemble.name)
        try:
            with open(os.path.join(self._assets_storage_dir, filename), 'wb') as file:
                pickle.dump(ensemble, file)
        except:
            self.log.error('Failed to serialize PulseBlockEnsemble "{0}" to file.'
                           ''.format(ensemble.name))
        return

    def _save_ensembles_to_file(self):
        """
        Saves the saved_pulse_block_ensembles dict items to files.
        """
        for ensemble in self.saved_pulse_block_ensembles.values():
            self._save_ensemble_to_file(ensemble)
        return

    def save_sequence(self, sequence):
        """ Saves a PulseSequence instance

        @param object sequence: a PulseSequence object, which is going to be
                                serialized to file.

        @return: str: name of the serialized object, if needed.
        """
        self._saved_pulse_sequences[sequence.name] = sequence
        self._save_sequence_to_file(sequence)
        self.sigSequenceDictUpdated.emit(self.saved_pulse_sequences)
        return

    def get_sequence(self, name):
        """

        @param name:
        @return:
        """
        if name not in self._saved_pulse_sequences:
            self.log.warning('PulseSequence "{0}" could not be found in saved pulse sequences.\n'
                             'Returning None.'.format(name))
        return self._saved_pulse_sequences.get(name)

    def delete_sequence(self, name):
        """
        Remove the sequence with 'name' from the sequence dict and all associated waveforms
        from the pulser memory.
        """
        if name in self.saved_pulse_sequences:
            # check if sequence has already been sampled and delete associated sequence from pulser.
            # Also delete associated waveforms if sequence has been sampled within rotating frame.
            if self.saved_pulse_sequences[name].sampling_information:
                self._delete_sequence(name)
                if self.saved_pulse_sequences[name].rotating_frame:
                    self._delete_waveform(
                        self.saved_pulse_sequences[name].sampling_information['waveforms'])
                    self.sigAvailableWaveformsUpdated.emit(self.sampled_waveforms)
            # delete PulseSequence
            del self._saved_pulse_sequences[name]

        # Delete from disk
        filepath = os.path.join(self._assets_storage_dir, '{0}.sequence'.format(name))
        if os.path.exists(filepath):
            os.remove(filepath)

        self.sigSequenceDictUpdated.emit(self.saved_pulse_sequences)
        return

    def _load_sequence_from_file(self, sequence_name):
        """
        De-serializes a PulseSequence instance from file.

        @param str sequence_name: The name of the PulseSequence instance to de-serialize
        @return PulseSequence: The de-serialized PulseSequence instance
        """
        filepath = os.path.join(self._assets_storage_dir, '{0}.sequence'.format(sequence_name))
        if os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as file:
                    sequence = pickle.load(file)
                # FIXME: Due to the pickling the dict namespace merging gets lost on the way.
                # Restored it here but a better way needs to be found.
                for step in range(len(sequence)):
                    sequence[step].__dict__ = sequence[step]
            except pickle.UnpicklingError:
                self.log.error('Failed to de-serialize PulseSequence "{0}" from file.'
                               ''.format(sequence_name))
                os.remove(filepath)
                return None

        # Conversion for backwards compatibility
        if len(sequence) > 0 and not isinstance(sequence[0].flag_high, list):
            self.log.warning('Loading deprecated PulseSequence instances from disk. '
                             'Attempting conversion to new format.\nIf you keep getting this '
                             'message after reloading SequenceGeneratorLogic or restarting qudi, '
                             'please regenerate the affected PulseSequence "{0}".'
                             ''.format(sequence_name))
            for step_no, step_params in enumerate(sequence):
                # Try to convert "flag_high" step parameter
                if isinstance(step_params.flag_high, str):
                    if step_params.flag_high.upper() == 'OFF':
                        sequence[step_no].flag_high = list()
                    else:
                        sequence[step_no].flag_high = [step_params.flag_high]
                elif isinstance(step_params.flag_high, dict):
                    sequence[step_no].flag_high = [flag for flag, state in
                                                   step_params.flag_high.items() if state]
                else:
                    self.log.error('Failed to de-serialize PulseSequence "{0}" from file.'
                                   '"flag_high" step parameter is of unknown type'
                                   ''.format(sequence_name))
                    os.remove(filepath)
                    return None

                # Try to convert "flag_trigger" step parameter
                if isinstance(step_params.flag_trigger, str):
                    if step_params.flag_trigger.upper() == 'OFF':
                        sequence[step_no].flag_trigger = list()
                    else:
                        sequence[step_no].flag_trigger = [step_params.flag_trigger]
                elif isinstance(step_params.flag_trigger, dict):
                    sequence[step_no].flag_trigger = [flag for flag, state in
                                                      step_params.flag_trigger.items() if state]
                else:
                    self.log.error('Failed to de-serialize PulseSequence "{0}" from file.'
                                   '"flag_trigger" step parameter is of unknown type'
                                   ''.format(sequence_name))
                    os.remove(filepath)
                    return None
            self._save_sequence_to_file(sequence)
        return sequence

    def _update_sequences_from_file(self):
        """
        Update the saved_pulse_sequences dict from files.
        """
        # Get all files in asset directory ending on ".sequence" and extract a sorted list of
        # PulseSequence names
        with os.scandir(self._assets_storage_dir) as scan:
            names = natural_sort(f.name[:-9] for f in scan if f.is_file and f.name.endswith('.sequence'))

        # Get all waveforms and sequences currently stored on pulser hardware in order to delete
        # outdated sampling_information dicts
        sampled_waveforms = set(self.sampled_waveforms)
        sampled_sequences = set(self.sampled_sequences)

        # Load all sequences from file
        for sequence_name in names:
            sequence = self._load_sequence_from_file(sequence_name)
            if sequence is not None:
                if sequence.name not in sampled_sequences:
                    sequence.sampling_information = dict()
                elif sequence.sampling_information:
                    waveform_set = set(sequence.sampling_information['waveforms'])
                    if not sampled_waveforms.issuperset(waveform_set):
                        sequence.sampling_information = dict()
                self._saved_pulse_sequences[sequence_name] = sequence

        self.sigSequenceDictUpdated.emit(self.saved_pulse_sequences)
        return

    def _save_sequence_to_file(self, sequence):
        """
        Saves a single PulseSequence instance to file by serialization using pickle.

        @param PulseSequence sequence: The PulseSequence instance to be saved
        """
        filename = '{0}.sequence'.format(sequence.name)
        try:
            with open(os.path.join(self._assets_storage_dir, filename), 'wb') as file:
                pickle.dump(sequence, file)
        except:
            self.log.error('Failed to serialize PulseSequence "{0}" to file.'.format(sequence.name))
        return

    def _save_sequences_to_file(self):
        """
        Saves the saved_pulse_sequences dict items to files.
        """
        for sequence in self.saved_pulse_sequences.values():
            self._save_sequence_to_file(sequence)
        return

    def generate_predefined_sequence(self, predefined_sequence_name, kwargs_dict):
        """

        @param predefined_sequence_name:
        @param kwargs_dict:
        @return:
        """
        gen_method = self.generate_methods[predefined_sequence_name]
        gen_params = self.generate_method_params[predefined_sequence_name]
        if 'name' not in gen_params:
            self.log.error('Mandatory generation parameter "name" not found in generate method '
                           '"{0}" arguments. Generation failed.'.format(predefined_sequence_name))
            self.sigPredefinedSequenceGenerated.emit(None, False)
            return

        # match parameters to method and throw out unwanted ones
        thrown_out_params = [param for param in kwargs_dict if param not in gen_params]
        for param in thrown_out_params:
            del kwargs_dict[param]
        if thrown_out_params:
            self.log.debug('Unused params during predefined sequence generation "{0}":\n'
                           '{1}'.format(predefined_sequence_name, thrown_out_params))

        try:
            blocks, ensembles, sequences = gen_method(**kwargs_dict)
        except:
            self.log.exception('Generation of predefined sequence "{0}" failed with exception:'
                               ''.format(predefined_sequence_name))
            self.sigPredefinedSequenceGenerated.emit(None, False)
            return

        # Save objects
        for block in blocks:
            self.save_block(block)
        for ensemble in ensembles:
            ensemble.sampling_information = dict()
            self.save_ensemble(ensemble)

        if self.pulse_generator_constraints.sequence_option == SequenceOption.FORCED and len(sequences) < 1:
            self.log.info('Adding default sequence for: {0:s}'.format(predefined_sequence_name))
            self._add_default_sequence(ensembles, sequences)
            if len(sequences) > 0:
                self.log.debug('New default PulseSequence is: {0:s} length {1:d}'
                               ''.format(sequences[0].name, len(sequences)))

        for sequence in sequences:
            sequence.sampling_information = dict()
            self.save_sequence(sequence)

        created_name = gen_params.get('name') if 'name' not in kwargs_dict else kwargs_dict['name']
        self.sigPredefinedSequenceGenerated.emit(created_name, len(sequences) > 0)
        return

    def _add_default_sequence(self, ensembles, sequences):
        if not isinstance(ensembles, (list, tuple)) or len(ensembles) < 1:
            self.log.error('It is not possible to create a default sequence, '
                           'because there is no Ensemble to create it from.')
            return
        if len(ensembles) > 1:
            self.log.warn('More then one Ensemble available for the default sequence. '
                          'They will be chained together with one repetition each.')

        measurement_info = ensembles[0].measurement_information.copy()
        sequence = PulseSequence(name=ensembles[0].name, rotating_frame=False)
        for ensemble in ensembles:
            sequence.append(ensemble.name)
            sequence[-1].repetitions = 0

        sequence[-1].go_to = 1

        # Trigger the calculation of parameters in the PulseSequence instance
        sequence.refresh_parameters()
        sequence.measurement_information = measurement_info

        # Append PulseSequence to created_sequences list
        sequences.append(sequence)

    # ---------------------------------------------------------------------------
    #                    END sequence/block generation
    # ---------------------------------------------------------------------------

    # ---------------------------------------------------------------------------
    #                    BEGIN sequence/block sampling
    # ---------------------------------------------------------------------------
    def get_ensemble_info(self, ensemble):
        """
        This helper method is just there for backwards compatibility. Essentially it will call the
        method "analyze_block_ensemble".

        Will return information like length in seconds and bins (with currently set sampling rate)
        as well as number of laser pulses (with currently selected laser/gate channel)

        @param PulseBlockEnsemble ensemble: The PulseBlockEnsemble instance to analyze
        @return (float, int, int): length in seconds, length in bins, number of laser/gate pulses
        """
        # Return if the ensemble is empty
        if len(ensemble) == 0:
            return 0.0, 0, 0

        info_dict = self.analyze_block_ensemble(ensemble=ensemble)
        # print(info_dict)
        ens_bins = info_dict['number_of_samples']
        ens_length = ens_bins / self.__sample_rate
        ens_lasers = min(len(info_dict['laser_rising_bins']), len(info_dict['laser_falling_bins']))
        return ens_length, ens_bins, ens_lasers

    def get_sequence_info(self, sequence):
        """
        This helper method will analyze a PulseSequence and return information like length in
        seconds and bins (with currently set sampling rate), number of laser pulses (with currently
        selected laser/gate channel)

        @param PulseSequence sequence: The PulseSequence instance to analyze
        @return (float, int, int): length in seconds, length in bins, number of laser/gate pulses
        """
        # Determine the right laser channel to choose. For gated counting it should be the gate
        # channel instead of the laser trigger.
        laser_channel = self.generation_parameters['gate_channel'] if self.generation_parameters[
            'gate_channel'] else self.generation_parameters['laser_channel']

        info_dict = self.analyze_sequence(sequence=sequence)
        length_bins = info_dict['number_of_samples']
        length_s = length_bins / self.__sample_rate if sequence.is_finite else np.inf

        if len(laser_channel) > 0 and laser_channel[0] == 'd' and sequence.is_finite:
            number_of_lasers = len(info_dict['digital_rising_bins'][laser_channel])
        elif sequence.is_finite:
            self.log.debug('Analog or no laser channel used. '
                           'Given laser_channel: "{0}"'.format(laser_channel))
            number_of_lasers = min(len(info_dict['laser_rising_bins']), len(info_dict['laser_falling_bins']))
        else:
            number_of_lasers = -1
        return length_s, length_bins, number_of_lasers

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

        @param ensemble: A PulseBlockEnsemble object (see logic.pulse_objects.py) or the name of one
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
        if isinstance(ensemble, str):
            if ensemble not in self._saved_pulse_block_ensembles:
                self.log.error('No saved PulseBlockEnsemble instance by the name "{0}" found. '
                               'Returning empty dict.'.format(ensemble))
                return dict()
            ensemble = self.get_ensemble(ensemble)
        elif not isinstance(ensemble, PulseBlockEnsemble):
            self.log.error('Ensemble to analyze must either be of type PulseBlockEnsemble or the '
                           'name of the ensemble. Returning empty dict')
            return dict()

        # Determine the right laser channel to choose. For gated counting it should be the gate
        # channel instead of the laser trigger.
        laser_channel = self.generation_parameters['gate_channel'] if self.generation_parameters[
            'gate_channel'] else self.generation_parameters['laser_channel']

        # memorize the digital channel state of the previous element
        tmp_digital_high = dict()
        # memorize the laser_on flag of the previous element (in case of non-digital laser channel)
        tmp_laser_on = False
        # Set of used analog and digital channels
        digital_channels = set()
        analog_channels = set()
        # check for active channels and initialize tmp_digital_high/tmp_laser_on with the state of
        # the very last element in the ensemble
        if len(ensemble) > 0:
            block = self.get_block(ensemble[0][0])
            digital_channels = block.digital_channels
            analog_channels = block.analog_channels
            block = self.get_block(ensemble[-1][0])
            if len(block) > 0:
                tmp_digital_high = block[-1].digital_high.copy()
                tmp_laser_on = block[-1].laser_on
            else:
                tmp_digital_high = {chnl: False for chnl in digital_channels}
                tmp_laser_on = False

        # dicts containing the bins where the digital channels are rising/falling
        digital_rising_bins = {chnl: list() for chnl in digital_channels}
        digital_falling_bins = {chnl: list() for chnl in digital_channels}
        laser_rising_bins = list()
        laser_falling_bins = list()

        # Array to store the length in bins for all elements including repetitions in the order
        # they are occuring in the waveform later on.
        elements_length_bins = list()

        # variables to keep track of the current timeframe
        current_end_time = 0.0
        current_start_bin = 0

        # Loop through all blocks in the ensemble
        for block_name, reps in ensemble:
            # Get the stored PulseBlock instance
            block = self.get_block(block_name)

            # Iterate over all repetitions of the current block
            for rep_no in range(reps + 1):
                # Iterate over the Block_Elements inside the current block
                for element in block:
                    # save bin position if a transition from low to high or vice versa has occurred
                    # in a digital channel
                    if tmp_digital_high != element.digital_high:
                        for chnl, state in element.digital_high.items():
                            if not tmp_digital_high[chnl] and state:
                                digital_rising_bins[chnl].append(current_start_bin)
                            elif tmp_digital_high[chnl] and not state:
                                digital_falling_bins[chnl].append(current_start_bin)
                        tmp_digital_high = element.digital_high.copy()

                    if not laser_channel.startswith('d') and tmp_laser_on != element.laser_on:
                        if not tmp_laser_on and element.laser_on:
                            laser_rising_bins.append(current_start_bin)
                        else:
                            laser_falling_bins.append(current_start_bin)
                        tmp_laser_on = element.laser_on

                    # Calculate length of the current element with current repetition count in sec
                    # and add this to the ideal end time for the sequence up until this point.
                    current_end_time += element.init_length_s + rep_no * element.increment_s

                    # Nearest possible match including the discretization in bins
                    current_end_bin = int(np.rint(current_end_time * self.__sample_rate))

                    # append current element length in discrete bins to temporary array
                    elements_length_bins.append(current_end_bin - current_start_bin)

                    # advance bin offset for next element
                    current_start_bin = current_end_bin

        elements_length_bins = np.array(elements_length_bins, dtype='int64')

        # convert rising/falling indices to numpy.ndarrays. Remove duplicates.
        for chnl in digital_channels:
            digital_rising_bins[chnl] = sorted(set(digital_rising_bins[chnl]))
            digital_falling_bins[chnl] = sorted(set(digital_falling_bins[chnl]))
            digital_rising_bins[chnl] = np.array(digital_rising_bins[chnl], dtype='int64')
            digital_falling_bins[chnl] = np.array(digital_falling_bins[chnl], dtype='int64')
        if laser_channel.startswith('d'):
            laser_rising_bins = digital_rising_bins[laser_channel]
            laser_falling_bins = digital_falling_bins[laser_channel]
        else:
            laser_rising_bins = np.array(sorted(set(laser_rising_bins)), dtype='int64')
            laser_falling_bins = np.array(sorted(set(laser_falling_bins)), dtype='int64')

        return_dict = dict()
        return_dict['number_of_samples'] = np.sum(elements_length_bins)
        return_dict['number_of_elements'] = len(elements_length_bins)
        return_dict['elements_length_bins'] = elements_length_bins
        return_dict['digital_rising_bins'] = digital_rising_bins
        return_dict['digital_falling_bins'] = digital_falling_bins
        return_dict['analog_channels'] = analog_channels
        return_dict['digital_channels'] = digital_channels
        return_dict['channel_set'] = analog_channels.union(digital_channels)
        return_dict['generation_parameters'] = self.generation_parameters.copy()
        return_dict['ideal_length'] = current_end_time
        return_dict['laser_rising_bins'] = laser_rising_bins
        return_dict['laser_falling_bins'] = laser_falling_bins
        return return_dict

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

        @param sequence: A PulseSequence object (see logic.pulse_objects.py) or the name of one
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
        if isinstance(sequence, str):
            if sequence not in self._saved_pulse_sequences:
                self.log.error('No saved PulseSequence instance by the name "{0}" found. '
                               'Returning empty dict.'.format(sequence))
                return dict()
            sequence = self.get_sequence(sequence)
        elif not isinstance(sequence, PulseSequence):
            self.log.error('Sequence to analyze must either be of type PulseSequence or the name '
                           'of the sequence. Returning empty dict')
            return dict()

        # Determine the right laser channel to choose. For gated counting it should be the gate
        # channel instead of the laser trigger.
        laser_channel = self.generation_parameters['gate_channel'] if self.generation_parameters[
            'gate_channel'] else self.generation_parameters['laser_channel']

        # Determine channel activation and the channel states of the very first and last element
        digital_channels = set()
        analog_channels = set()
        last_digital_channel_state = {chnl: False for chnl in digital_channels}
        last_laser_on_state = False

        if len(sequence) > 0:
            ensemble = self.get_ensemble(sequence[0].ensemble)
            if len(ensemble) > 0:
                block = self.get_block(ensemble[0][0])
                digital_channels = block.digital_channels
                analog_channels = block.analog_channels
            ensemble = self.get_ensemble(sequence[-1].ensemble)
            if len(ensemble) > 0:
                block = self.get_block(ensemble[-1][0])
                if len(block) > 0:
                    last_digital_channel_state = block[-1].digital_high.copy()
                    last_laser_on_state = block[-1].laser_on

        # Current bin offset with respect to the expected real time signal
        starting_bin = 0

        # If the sequence does not contain infinite loop steps, determine the remaining parameters
        step_length_bins = np.zeros(len(sequence), dtype='int64')
        ideal_step_length = np.zeros(len(sequence), dtype='float64')
        number_of_step_elements = np.zeros(len(sequence), dtype='int64')
        step_elements_length_bins = list()
        laser_rising_bins = list()
        laser_falling_bins = list()
        digital_rising_bins = {chnl: list() for chnl in digital_channels}
        digital_falling_bins = {chnl: list() for chnl in digital_channels}
        ensemble_name_set = set()
        # Initialize the last channel state of the first sequence step as last channel state in the
        # entire sequence.
        step_last_digital_state = last_digital_channel_state
        step_last_laser_on_state = last_laser_on_state

        for step_no, seq_step in enumerate(sequence):
            is_finite = seq_step.repetitions >= 0
            # Get the PulseBlockEnsemble instance associated with this sequence step
            ensemble = self.get_ensemble(seq_step.ensemble)
            # Get information about the current PulseBlockEnsemble instance
            info_dict = self.analyze_block_ensemble(ensemble=ensemble)
            # Set tmp helper variables
            ensemble_name_set.add(ensemble.name)
            reps = seq_step.repetitions + 1
            ens_bins = info_dict['number_of_samples']
            # Keep track of channel states at sequence step boundaries
            prev_step_digital_state = step_last_digital_state.copy()
            prev_step_laser_on_state = step_last_laser_on_state
            tmp_block = self.get_block(ensemble[0][0])
            step_first_digital_state = tmp_block[0].digital_high.copy()
            step_first_laser_on_state = tmp_block[0].laser_on
            tmp_block = self.get_block(ensemble[-1][0])
            step_last_digital_state = tmp_block[-1].digital_high.copy()
            step_last_laser_on_state = tmp_block[-1].laser_on
            # Calculate sequence step information
            step_length_bins[step_no] = ens_bins * reps if is_finite else -1
            number_of_step_elements[step_no] = info_dict['number_of_elements'] * reps if is_finite else -1
            ideal_step_length[step_no] = info_dict['ideal_length'] * reps if is_finite else np.inf
            step_elements_length_bins.append(
                [seq_step.repetitions, info_dict['elements_length_bins']])

            # Get the digital channel rising/falling bin positions and concatenate them according
            # to sequence step repetition count considering bin offsets.
            # This will result in a sequence of rising and falling bins representing the real-time
            # signal with all repetitions taken into account.
            # Do that for every digital channel and only if the sequence is finite
            if sequence.is_finite:
                for chnl in digital_channels:
                    # Append rising/falling bin arrays for each step to a list in order to merge
                    # them all later on into a single array. This is more efficient than having
                    # an intermediate array.
                    # Pay special attention to transitions from one sequence step to another.
                    for iteration in range(reps):
                        bin_offset = iteration * ens_bins + starting_bin
                        rising_bins = info_dict['digital_rising_bins'][chnl] + bin_offset
                        falling_bins = info_dict['digital_falling_bins'][chnl] + bin_offset
                        if iteration == 0 and prev_step_digital_state[chnl] != step_last_digital_state[chnl]:
                            if prev_step_digital_state[chnl] and not step_first_digital_state[chnl]:
                                falling_bins = np.append(bin_offset, falling_bins)
                            elif not prev_step_digital_state[chnl] and step_first_digital_state[chnl]:
                                rising_bins = np.append(bin_offset, rising_bins)
                            elif prev_step_digital_state[chnl] == step_first_digital_state[chnl]:
                                if step_last_digital_state[chnl]:
                                    falling_bins = falling_bins[1:]
                                else:
                                    rising_bins = rising_bins[1:]

                        digital_rising_bins[chnl].append(rising_bins)
                        digital_falling_bins[chnl].append(falling_bins)

                # Append laser_bins arrays with bin offsets for each repetition analogous to the
                # digital channels above.
                if not laser_channel.startswith('d'):
                    for iteration in range(reps):
                        bin_offset = iteration * ens_bins + starting_bin
                        rising_bins = info_dict['laser_rising_bins'] + bin_offset
                        falling_bins = info_dict['laser_falling_bins'] + bin_offset
                        if iteration == 0 and prev_step_laser_on_state != step_last_laser_on_state:
                            if prev_step_laser_on_state and not step_first_laser_on_state:
                                falling_bins = np.append(bin_offset, falling_bins)
                            elif not prev_step_laser_on_state and step_first_laser_on_state:
                                rising_bins = np.append(bin_offset, rising_bins)
                            elif prev_step_laser_on_state == step_first_laser_on_state:
                                if step_last_laser_on_state:
                                    falling_bins = falling_bins[1:]
                                else:
                                    rising_bins = rising_bins[1:]
                        laser_rising_bins.append(rising_bins)
                        laser_falling_bins.append(falling_bins)

                # Increment the current starting bin offset for the next sequence step
                starting_bin += ens_bins * reps

        # Concatenate all bin arrays in the respective lists to a single large array.
        for channel in digital_channels:
            if digital_rising_bins[channel]:
                digital_rising_bins[channel] = np.unique(np.concatenate(digital_rising_bins[channel]))
            else:
                digital_rising_bins[channel] = np.empty(0, dtype='int64')
            if digital_falling_bins[channel]:
                digital_falling_bins[channel] = np.unique(np.concatenate(digital_falling_bins[channel]))
            else:
                digital_falling_bins[channel] = np.empty(0, dtype='int64')

        if laser_channel.startswith('d'):
            laser_rising_bins = digital_rising_bins[laser_channel]
            laser_falling_bins = digital_falling_bins[laser_channel]
        else:
            laser_rising_bins = np.unique(np.concatenate(laser_rising_bins)) if laser_rising_bins else np.empty(0, dtype='int64')
            laser_falling_bins = np.unique(np.concatenate(laser_falling_bins)) if laser_falling_bins else np.empty(0, dtype='int64')

        # Sort out trailing or leading incomplete laser pulse
        while len(laser_rising_bins) != len(laser_falling_bins):
            if len(laser_rising_bins) > len(laser_falling_bins):
                if laser_rising_bins[-1] >= laser_falling_bins[-1]:
                    laser_rising_bins = laser_rising_bins[:-1]
                else:
                    laser_rising_bins = laser_rising_bins[1:]
            else:
                if laser_rising_bins[0] >= laser_falling_bins[0]:
                    laser_falling_bins = laser_falling_bins[1:]
                else:
                    laser_falling_bins = laser_falling_bins[:-1]
            self.log.warning('Incomplete trailing or leading laser pulses detected in sequence '
                             '"{0}". Removed corresponding unpaired rising/falling flank from '
                             'laser_rising/falling_bins array.\nThis can happen if the sequence '
                             'starts and ends with an active laser pulse'.format(sequence.name))

        return_dict = dict()
        return_dict['digital_channels'] = digital_channels
        return_dict['analog_channels'] = analog_channels
        return_dict['channel_set'] = analog_channels.union(digital_channels)
        return_dict['generation_parameters'] = self.generation_parameters.copy()
        return_dict['digital_rising_bins'] = digital_rising_bins
        return_dict['digital_falling_bins'] = digital_falling_bins
        return_dict['number_of_steps'] = len(sequence)
        return_dict['number_of_samples'] = np.sum(step_length_bins)
        return_dict['number_of_samples_per_step'] = step_length_bins
        return_dict['number_of_ensembles'] = len(ensemble_name_set)
        return_dict['ensemble_names'] = ensemble_name_set
        return_dict['number_of_elements'] = np.sum(number_of_step_elements)
        return_dict['number_of_elements_per_step'] = number_of_step_elements
        return_dict['elements_length_bins_per_step'] = step_elements_length_bins
        return_dict['ideal_length_per_step'] = ideal_step_length
        return_dict['ideal_length'] = np.sum(ideal_step_length)
        return_dict['laser_rising_bins'] = laser_rising_bins
        return_dict['laser_falling_bins'] = laser_falling_bins

        return return_dict

    def _sampling_ensemble_sanity_check(self, ensemble):
        blocks_missing = set()
        channel_activation_mismatch = False
        for block_name, reps in ensemble.block_list:
            block = self._saved_pulse_blocks.get(block_name)
            # Check if block is present
            if block is None:
                blocks_missing.add(block_name)
                continue
            # Check for matching channel activation
            if block.channel_set != self.__activation_config[1]:
                channel_activation_mismatch = True

        # print error messages
        if len(blocks_missing) > 0:
            self.log.error('Sampling of PulseBlockEnsemble "{0}" failed. Not all PulseBlocks found.'
                           '\nPlease generate the following PulseBlocks: {1}'
                           ''.format(ensemble.name, blocks_missing))
        if channel_activation_mismatch:
            self.log.error('Sampling of PulseBlockEnsemble "{0}" failed!\nMismatch of activation '
                           'config in logic ({1}) and used channels in PulseBlockEnsemble.'
                           ''.format(ensemble.name, self.__activation_config[1]))

        # Return error code
        return -1 if blocks_missing or channel_activation_mismatch else 0

    def _sampling_sequence_sanity_check(self, sequence):
        ensembles_missing = set()
        for seq_step in sequence:
            ensemble = self._saved_pulse_block_ensembles.get(seq_step.ensemble)
            # Check if ensemble is present
            if ensemble is None:
                ensembles_missing.add(seq_step.ensemble)
                continue

        # print error messages
        if len(ensembles_missing) > 0:
            self.log.error('Sampling of PulseSequence "{0}" failed. Not all PulseBlockEnsembles '
                           'found.\nPlease generate the following PulseBlockEnsembles: {1}'
                           ''.format(sequence.name, ensembles_missing))

        # Return error code
        return -1 if ensembles_missing else 0

    @QtCore.Slot(str)
    def sample_pulse_block_ensemble(self, ensemble, offset_bin=0, name_tag=None):
        """ General sampling of a PulseBlockEnsemble object, which serves as the construction plan.

        @param str|PulseBlockEnsemble ensemble: PulseBlockEnsemble instance or name of a saved
                                                PulseBlockEnsemble to sample
        @param int offset_bin: If many pulse ensembles are samples sequentially, then the
                               offset_bin of the previous sampling can be passed to maintain
                               rotating frame across pulse_block_ensembles
        @param str name_tag: a name tag, which is used to keep the sampled files together, which
                             where sampled from the same PulseBlockEnsemble object but where
                             different offset_bins were used.

        @return tuple: of length 3 with
                       (offset_bin, created_waveforms, ensemble_info).
                        offset_bin:
                            integer, which is used for maintaining the rotation frame
                        created_waveforms:
                            list, a list of created waveform names
                        ensemble_info:
                            dict, information about the ensemble returned by analyze_block_ensemble

        This method is creating the actual samples (voltages and logic states) for each time step
        of the analog and digital channels specified in the PulseBlockEnsemble.
        Therefore it iterates through all blocks, repetitions and elements of the ensemble and
        calculates the exact voltages (float64) according to the specified math_function. The
        samples are later on stored inside a float32 array.
        So each element is calculated with high precision (float64) and then down-converted to
        float32 to be stored.

        To preserve the rotating frame, an offset counter is used to indicate the absolute time
        within the ensemble. All calculations are done with time bins (dtype=int) to avoid rounding
        errors. Only in the last step when a single PulseBlockElement object is sampled  these
        integer bin values are translated into a floating point time.

        The chunkwise write mode is used to save memory usage at the expense of time.
        In other words: The whole sample arrays are never created at any time. This results in more
        function calls and general overhead causing much longer time to complete.

        In addition the pulse_block_ensemble gets analyzed and important parameters used during
        sampling get stored in the ensemble object "sampling_information" attribute.
        It is a dictionary containing:
        TODO: Add parameters that are stored
        """
        # Get PulseBlockEnsemble from saved ensembles if string has been passed as argument
        if isinstance(ensemble, str):
            ensemble = self.get_ensemble(ensemble)
            if not ensemble:
                self.log.error('Unable to sample PulseBlockEnsemble. Not found in saved ensembles.')
                self.sigSampleEnsembleComplete.emit(None)
                return -1, list(), dict()

        # Perform sanity checks on ensemble and corresponding blocks
        if self._sampling_ensemble_sanity_check(ensemble) < 0:
            self.sigSampleEnsembleComplete.emit(None)
            return -1, list(), dict()

        # lock module if it's not already locked (sequence sampling in progress)
        if self.module_state() == 'idle':
            self.module_state.lock()
        elif not self.__sequence_generation_in_progress:
            self.sigSampleEnsembleComplete.emit(None)
            return -1, list(), dict()

        # Set the waveform name (excluding the device specific channel naming suffix, i.e. '_ch1')
        waveform_name = name_tag if name_tag else ensemble.name

        # check for old waveforms associated with the ensemble and delete them from pulse generator.
        self._delete_waveform_by_nametag(waveform_name)

        # Take current time
        start_time = time.time()

        # get important parameters from the ensemble
        ensemble_info = self.analyze_block_ensemble(ensemble)

        # Make sure the length of the channel is a multiple of the step size.
        # This is done by appending an idle block
        granularity = self.pulse_generator_constraints.waveform_length.step
        self.log.debug('length: {0}, mod {1}'.format(
            ensemble_info['number_of_samples'], ensemble_info['number_of_samples'] % granularity))
        if ensemble_info['number_of_samples'] % granularity != 0:
            self.log.warn('Length {0} does not fulfil step constraint {1}.'.format(
                ensemble_info['number_of_samples'], granularity))
            # TODO: take care of rounding errors!
            extension_samples = granularity - ensemble_info['number_of_samples'] % granularity
            target_total_samples = ensemble_info['number_of_samples'] + extension_samples
            extension_seconds = (target_total_samples / self.__sample_rate) - ensemble_info[
                'ideal_length']

            pb_element = PulseBlockElement(
                init_length_s=extension_seconds,
                increment_s=0,
                pulse_function={chnl: SamplingFunctions.Idle() for chnl in self.analog_channels},
                digital_high={chnl: False for chnl in self.digital_channels})
            idle_extension = PulseBlock('idle_extension', element_list=[pb_element])
            temp_measurement_info = copy.deepcopy(ensemble.measurement_information)
            ensemble.append((idle_extension.name, 0))
            ensemble.measurement_information = temp_measurement_info

            self.save_block(idle_extension)
            self.save_ensemble(ensemble)

            # get important parameters from the ensemble
            ensemble_info = self.analyze_block_ensemble(ensemble)
            if ensemble_info['number_of_samples'] != target_total_samples:
                self.log.error('Expanding the PulseBlockEnsemble to match the waveform granularity '
                               'has failed.\nTarget number of samples was {0:d}.\nfinal number of '
                               'samples is {1:d}.\nThis is probably due to a rounding error in '
                               'SequenceGeneratorLogic.sample_pulse_block_ensemble.'
                               ''.format(target_total_samples, ensemble_info['number_of_samples']))
            else:
                self.log.warn('Extending waveform {0} by {2} bins. New length {1}.'.format(
                    ensemble.name, ensemble_info['number_of_samples'], extension_samples))

        # Calculate the byte size per sample.
        # One analog sample per channel is 4 bytes (np.float32) and one digital sample per channel
        # is 1 byte (np.bool).
        bytes_per_sample = len(ensemble_info['analog_channels']) * 4 + len(
            ensemble_info['digital_channels'])

        # Calculate the bytes estimate for the entire ensemble
        bytes_per_ensemble = bytes_per_sample * ensemble_info['number_of_samples']

        # Determine the size of the sample arrays to be written as a whole.
        if bytes_per_ensemble <= self._overhead_bytes or self._overhead_bytes == 0:
            array_length = ensemble_info['number_of_samples']
        else:
            array_length = self._overhead_bytes // bytes_per_sample

        # Allocate the sample arrays that are used for a single write command
        analog_samples = dict()
        digital_samples = dict()
        try:
            for chnl in ensemble_info['analog_channels']:
                analog_samples[chnl] = np.empty(array_length, dtype='float32')
            for chnl in ensemble_info['digital_channels']:
                digital_samples[chnl] = np.empty(array_length, dtype=bool)
        except MemoryError:
            self.log.error('Sampling of PulseBlockEnsemble "{0}" failed due to a MemoryError.\n'
                           'The sample array needed is too large to allocate in memory.\n'
                           'Try using the overhead_bytes ConfigOption to limit memory usage.'
                           ''.format(ensemble.name))
            if not self.__sequence_generation_in_progress:
                self.module_state.unlock()
            self.sigSampleEnsembleComplete.emit(None)
            return -1, list(), dict()

        # integer to keep track of the sampls already processed
        processed_samples = 0
        # Index to keep track of the samples written into the preallocated samples array
        array_write_index = 0
        # Keep track of the number of elements already written
        element_count = 0
        # set of written waveform names on the device
        written_waveforms = set()
        # Iterate over all blocks within the PulseBlockEnsemble object
        for block_name, reps in ensemble.block_list:
            block = self.get_block(block_name)
            # Iterate over all repetitions of the current block
            for rep_no in range(reps + 1):
                # Iterate over the PulseBlockElement instances inside the current block
                for element in block.element_list:
                    digital_high = element.digital_high
                    pulse_function = element.pulse_function
                    element_length_bins = ensemble_info['elements_length_bins'][element_count]

                    # Indicator on how many samples of this element have been written already
                    element_samples_written = 0

                    while element_samples_written != element_length_bins:
                        samples_to_add = min(array_length - array_write_index,
                                             element_length_bins - element_samples_written)
                        # create floating point time array for the current element inside rotating
                        # frame if analog samples are to be calculated.
                        if pulse_function:
                            time_arr = (offset_bin + np.arange(
                                samples_to_add, dtype='float64')) / self.__sample_rate

                        # Calculate respective part of the sample arrays
                        for chnl in digital_high:
                            digital_samples[chnl][array_write_index:array_write_index + samples_to_add] = digital_high[
                                chnl]
                        for chnl in pulse_function:
                            analog_samples[chnl][array_write_index:array_write_index + samples_to_add] = pulse_function[
                                                                                                             chnl].get_samples(
                                time_arr) / (self.__analog_levels[0][chnl] / 2)

                        # Free memory
                        if pulse_function:
                            del time_arr

                        element_samples_written += samples_to_add
                        array_write_index += samples_to_add
                        processed_samples += samples_to_add
                        # if the rotating frame should be preserved (default) increment the offset
                        # counter for the time array.
                        if ensemble.rotating_frame:
                            offset_bin += samples_to_add

                        # Check if the temporary sample array is full and write to the device if so.
                        if array_write_index == array_length:
                            # Set first/last chunk flags
                            is_first_chunk = array_write_index == processed_samples
                            is_last_chunk = processed_samples == ensemble_info['number_of_samples']
                            written_samples, wfm_list = self.pulsegenerator().write_waveform(
                                name=waveform_name,
                                analog_samples=analog_samples,
                                digital_samples=digital_samples,
                                is_first_chunk=is_first_chunk,
                                is_last_chunk=is_last_chunk,
                                total_number_of_samples=ensemble_info['number_of_samples'])

                            # Update written waveforms set
                            written_waveforms.update(wfm_list)

                            # check if write process was successful
                            if written_samples != array_length:
                                self.log.error('Sampling of block "{0}" in ensemble "{1}" failed. '
                                               'Write to device was unsuccessful.\nThe number of '
                                               'actually written samples ({2:d}) does not match '
                                               'the number of samples staged to write ({3:d}).'
                                               ''.format(block_name, ensemble.name, written_samples,
                                                         array_length))
                                if not self.__sequence_generation_in_progress:
                                    self.module_state.unlock()
                                self.sigAvailableWaveformsUpdated.emit(self.sampled_waveforms)
                                self.sigSampleEnsembleComplete.emit(None)
                                return -1, list(), dict()

                            # Reset array write start pointer
                            array_write_index = 0

                            # check if the temporary write array needs to be truncated for the next
                            # part. (because it is the last part of the ensemble to write which can
                            # be shorter than the previous chunks)
                            if array_length > ensemble_info['number_of_samples'] - processed_samples:
                                array_length = ensemble_info['number_of_samples'] - processed_samples
                                analog_samples = dict()
                                digital_samples = dict()
                                for chnl in ensemble_info['analog_channels']:
                                    analog_samples[chnl] = np.empty(array_length, dtype='float32')
                                for chnl in ensemble_info['digital_channels']:
                                    digital_samples[chnl] = np.empty(array_length, dtype=bool)

                    # Increment element index
                    element_count += 1

        # Save sampling related parameters to the sampling_information container within the
        # PulseBlockEnsemble.
        # This step is only performed if the resulting waveforms are named by the PulseBlockEnsemble
        # and not by a sequence nametag
        if waveform_name == ensemble.name:
            ensemble.sampling_information = dict()
            ensemble.sampling_information.update(ensemble_info)
            ensemble.sampling_information['pulse_generator_settings'] = self.pulse_generator_settings
            ensemble.sampling_information['waveforms'] = natural_sort(written_waveforms)
            self.save_ensemble(ensemble)

        self.log.info('Time needed for sampling and writing PulseBlockEnsemble {0} to device: {1} sec'
                      ''.format(ensemble.name, int(np.rint(time.time() - start_time))))
        if ensemble_info['number_of_samples'] == 0:
            self.log.warning('Empty waveform (0 samples) created from PulseBlockEnsemble "{0}".'
                             ''.format(ensemble.name))
        if not self.__sequence_generation_in_progress:
            self.module_state.unlock()
        self.sigAvailableWaveformsUpdated.emit(self.sampled_waveforms)
        self.sigSampleEnsembleComplete.emit(ensemble)
        return offset_bin, natural_sort(written_waveforms), ensemble_info

    @QtCore.Slot(str)
    def sample_pulse_sequence(self, sequence):
        """ Samples the PulseSequence object, which serves as the construction plan.

        @param str|PulseSequence sequence: Name or instance of the PulseSequence to be sampled.

        The sequence object is sampled by call subsequently the sampling routine for the
        PulseBlockEnsemble objects and passing if needed the rotating frame option.

        Right now two 'simple' methods of sampling where implemented, which reuse the sample
        function for the Pulse_Block_Ensembles. One, which samples by preserving the phase (i.e.
        staying in the rotating frame) and the other which samples without keep a phase
        relationship between the different entries of the PulseSequence object.
        ATTENTION: The phase preservation within a single PulseBlockEnsemble is NOT affected by
                   this method.

        More sophisticated sequence sampling method can be implemented here.
        """
        # Get PulseSequence from saved sequences if string has been passed as argument
        if isinstance(sequence, str):
            sequence = self.get_sequence(sequence)
            if not sequence:
                self.log.error('Unable to sample PulseSequence. Not found in saved sequences.')
                self.sigSampleSequenceComplete.emit(None)
                return

        # Perform sanity checks on sequence and corresponding ensembles
        if self._sampling_sequence_sanity_check(sequence) < 0:
            self.sigSampleSequenceComplete.emit(None)
            return

        # lock module and set sequence-generation-in-progress flag
        if self.module_state() == 'idle':
            self.__sequence_generation_in_progress = True
            self.module_state.lock()
        else:
            self.log.error('Cannot sample sequence "{0}" because the SequenceGeneratorLogic is '
                           'still busy (locked).\nFunction call ignored.'.format(sequence.name))
            self.sigSampleSequenceComplete.emit(None)
            return

        self._saved_pulse_sequences[sequence.name] = sequence

        # delete already written sequences on the device memory.
        if sequence.name in self.sampled_sequences:
            self.pulsegenerator().delete_sequence(sequence.name)

        # Make sure the PulseSequence is contained in the saved sequences dict
        sequence.sampling_information = dict()
        self.save_sequence(sequence)

        # Take current time
        start_time = time.time()

        # Produce a set of created waveforms
        written_waveforms = set()
        # Keep track of generated PulseBlockEnsembles and their corresponding ensemble_info dict
        generated_ensembles = dict()

        # Create a list in the process with each element holding the created waveform names as a
        # tuple and the corresponding sequence parameters as defined in the PulseSequence object
        # Example: [(('waveform1', 'waveform2'), seq_param_dict1),
        #           (('waveform3', 'waveform4'), seq_param_dict2)]
        sequence_param_dict_list = list()

        # if all the Pulse_Block_Ensembles should be in the rotating frame, then each ensemble
        # will be created in general with a different offset_bin. Therefore, in order to keep track
        # of the sampled Pulse_Block_Ensembles one has to introduce a running number as an
        # additional name tag, so keep the sampled files separate.
        offset_bin = 0  # that will be used for phase preservation
        for step_index, seq_step in enumerate(sequence):
            if sequence.rotating_frame:
                # to make something like 001
                name_tag = seq_step.ensemble + '_' + str(step_index).zfill(3)
            else:
                name_tag = seq_step.ensemble
                offset_bin = 0  # Keep the offset at 0

            # Only sample ensembles if they have not already been sampled
            if sequence.rotating_frame or \
                    not self.get_ensemble(name_tag).sampling_information or \
                    self.get_ensemble(name_tag).sampling_information['pulse_generator_settings'] != self.pulse_generator_settings:

                offset_bin, waveform_list, ensemble_info = self.sample_pulse_block_ensemble(
                    ensemble=seq_step.ensemble,
                    offset_bin=offset_bin,
                    name_tag=name_tag)

                if len(waveform_list) == 0:
                    self.log.error('Sampling of PulseBlockEnsemble "{0}" failed during sampling of '
                                   'PulseSequence "{1}".\nFailed to create waveforms on device.'
                                   ''.format(seq_step.ensemble, sequence.name))
                    self.module_state.unlock()
                    self.__sequence_generation_in_progress = False
                    self.sigSampleSequenceComplete.emit(None)
                    return

                # Add to generated ensembles
                ensemble_info['waveforms'] = waveform_list
                generated_ensembles[name_tag] = ensemble_info

                # Add created waveform names to the set
                written_waveforms.update(waveform_list)
            else:
                self.log.debug('Waveform already sampled: {0}'.format(name_tag))
                ensemble_info = self.get_ensemble(name_tag).sampling_information.copy()
                del(ensemble_info['pulse_generator_settings'])
                generated_ensembles[name_tag] = ensemble_info

                # Add created waveform names to the set
                written_waveforms.update(ensemble_info['waveforms'])

            # Append written sequence step to sequence_param_dict_list
            sequence_param_dict_list.append(
                (tuple(generated_ensembles[name_tag]['waveforms']), seq_step))

        # pass the whole information to the sequence creation method:
        steps_written = self.pulsegenerator().write_sequence(sequence.name,
                                                             sequence_param_dict_list)
        if steps_written != len(sequence_param_dict_list):
            self.log.error('Writing PulseSequence "{0}" to the device memory failed.\n'
                           'Returned number of sequence steps ({1:d}) does not match desired '
                           'number of steps ({2:d}).'.format(sequence.name,
                                                             steps_written,
                                                             len(sequence_param_dict_list)))

        # get important parameters from the sequence and save them to the sequence object
        sequence.sampling_information.update(self.analyze_sequence(sequence))
        sequence.sampling_information['ensemble_info'] = generated_ensembles
        sequence.sampling_information['pulse_generator_settings'] = self.pulse_generator_settings
        sequence.sampling_information['waveforms'] = natural_sort(written_waveforms)
        sequence.sampling_information['step_waveform_list'] = [step[0] for step in
                                                               sequence_param_dict_list]
        self.save_sequence(sequence)

        self.log.info('Time needed for sampling and writing PulseSequence {0} to device: {1} sec.'
                      ''.format(sequence.name, int(np.rint(time.time() - start_time))))

        # unlock module
        self.module_state.unlock()
        self.__sequence_generation_in_progress = False
        self.sigAvailableSequencesUpdated.emit(self.sampled_sequences)
        self.sigSampleSequenceComplete.emit(sequence)
        return

    def _delete_waveform(self, names):
        if isinstance(names, str):
            names = [names]
        current_waveforms = self.sampled_waveforms
        for wfm in names:
            if wfm in current_waveforms:
                self.pulsegenerator().delete_waveform(wfm)
        self.sigAvailableWaveformsUpdated.emit(self.sampled_waveforms)
        return

    def _delete_waveform_by_nametag(self, nametag):
        if not isinstance(nametag, str):
            return
        wfm_to_delete = [wfm for wfm in self.sampled_waveforms if
                         wfm.rsplit('_', 1)[0] == nametag]
        self._delete_waveform(wfm_to_delete)
        # Erase sampling information if a PulseBlockEnsemble by the same name can be found in saved
        # ensembles
        if nametag in self.saved_pulse_block_ensembles:
            ensemble = self.saved_pulse_block_ensembles[nametag]
            ensemble.sampling_information = dict()
            self.save_ensemble(ensemble)
        return

    def _delete_sequence(self, names):
        if isinstance(names, str):
            names = [names]
        current_sequences = self.sampled_sequences
        for seq in names:
            if seq in current_sequences:
                self.pulsegenerator().delete_sequence(seq)
        self.sigAvailableSequencesUpdated.emit(self.sampled_sequences)
        return
