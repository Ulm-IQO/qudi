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

import importlib
import inspect
import numpy as np
import os
import pickle
import sys
import time

from qtpy import QtCore
from collections import OrderedDict
from core.module import StatusVar, Connector, ConfigOption
from core.util.modules import get_main_dir
from logic.generic_logic import GenericLogic
from logic.pulse_objects import PulseBlock, PulseBlockEnsemble, PulseSequence


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

    _modclass = 'sequencegeneratorlogic'
    _modtype = 'logic'

    # declare connectors
    pulsegenerator = Connector(interface='PulserInterface')

    # configuration options
    _additional_methods_dir = ConfigOption('additional_methods_dir', default='', missing='nothing')
    _overhead_bytes = ConfigOption('overhead_bytes', default=0, missing='nothing')

    # status vars
    # Descriptor to indicate the laser channel
    _laser_channel = StatusVar(default='d_ch1')
    # The created pulse objects (PulseBlock, PulseBlockEnsemble, PusleSequence) are saved in
    # these dictionaries. The keys are the names.
    _saved_pulse_blocks = StatusVar(default=OrderedDict())
    _saved_pulse_block_ensembles = StatusVar(default=OrderedDict())
    _saved_pulse_sequences = StatusVar(default=OrderedDict())

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

    sigPredefinedSequenceGenerated = QtCore.Signal(object)  # TODO: Needed???

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.debug('The following configuration was found.')
        # checking for the right configuration
        for key in config.keys():
            self.log.debug('{0}: {1}'.format(key, config[key]))

        # Additional handling of config options
        # Byte size of the max. memory usage during sampling process
        if 'overhead_bytes' not in config.keys():
            self.log.warning('No max. memory overhead specified in config.\nIn order to avoid '
                             'memory overflow during sampling/writing of Pulse objects you must '
                             'set "overhead_bytes".')
        # directory for additional generate methods to import
        # (other than qudi/logic/predefined_methods)
        if 'additional_methods_dir' in config.keys():
            if not os.path.exists(config['additional_methods_dir']):
                self.additional_methods_dir = None
                self.log.error('Specified path "{0}" for import of additional generate methods '
                               'does not exist.'.format(config['additional_methods_dir']))

        # a dictionary with all predefined generator methods and measurement sequence names
        self.__generate_methods = None

        # current pulse generator settings that are frequently used by this logic.
        # Save them here since reading them from device every time they are used may take some time.
        self.__activation_config = ('', set())  # Activation config name and set of active channels
        self.__sample_rate = 0.0  # Sample rate in samples/s
        self.__analog_levels = (dict(), dict())  # Tuple of two dict (<pp_amplitude>, <offset>)
                                                 # Dict keys are analog channel descriptors
        self.__digital_levels = (dict(), dict())  # Tuple of two dict (<low_volt>, <high_volt>)
                                                  # Dict keys are digital channel descriptors
        self.__interleave = False  # Flag to indicate use of interleave

        # A flag indicating if sampling of a sequence is in progress
        self.__sequence_generation_in_progress = False
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # Get method definitions for prefined pulse sequences from seperate modules and attach them
        # to this module.
        self._attach_predefined_methods()

        # Read back settings from device and update instance variables accordingly
        self._read_settings_from_device()

        # Update saved blocks/ensembles/sequences from temporary pre-crash file if present
        self._update_blocks_from_tmp_file()
        self._update_ensembles_from_tmp_file()
        self._update_sequences_from_tmp_file()

        self.__sequence_generation_in_progress = False
        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        # Cleanup temporary backup files
        #self._cleanup_tmp_files()
        return

    @_saved_pulse_blocks.constructor
    def _restore_saved_blocks(self, block_list):
        return_block_dict = OrderedDict()
        if block_list is not None:
            for block_dict in block_list:
                return_block_dict[block_dict['name']] = PulseBlock.block_from_dict(block_dict)
        return return_block_dict


    @_saved_pulse_blocks.representer
    def _convert_saved_blocks(self, block_dict):
        if block_dict is None:
            return None
        else:
            block_list = list()
            for block in block_dict.values():
                block_list.append(block.get_dict_representation())
            return block_list

    @_saved_pulse_block_ensembles.constructor
    def _restore_saved_ensembles(self, ensemble_list):
        return_ensemble_dict = OrderedDict()
        if ensemble_list is not None:
            for ensemble_dict in ensemble_list:
                return_ensemble_dict[ensemble_dict['name']] = PulseBlockEnsemble.ensemble_from_dict(
                    ensemble_dict)
        return return_ensemble_dict

    @_saved_pulse_block_ensembles.representer
    def _convert_saved_ensembles(self, ensemble_dict):
        if ensemble_dict is None:
            return None
        else:
            ensemble_list = list()
            for ensemble in ensemble_dict.values():
                ensemble_list.append(ensemble.get_dict_representation())
            return ensemble_list

    @_saved_pulse_sequences.constructor
    def _restore_saved_sequences(self, sequence_list):
        return_sequence_dict = OrderedDict()
        if sequence_list is not None:
            for sequence_dict in sequence_list:
                return_sequence_dict[sequence_dict['name']] = PulseBlockEnsemble.ensemble_from_dict(
                    sequence_dict)
        return return_sequence_dict

    @_saved_pulse_sequences.representer
    def _convert_saved_sequences(self, sequence_dict):
        if sequence_dict is None:
            return None
        else:
            sequence_list = list()
            for sequence in sequence_dict.values():
                sequence_list.append(sequence.get_dict_representation())
            return sequence_list

    ############################################################################
    # Pulse generator control methods and properties
    ############################################################################
    @property
    def pulse_generator_settings(self):
        settings_dict = dict()
        settings_dict['activation_config'] = tuple(self.__activation_config)
        settings_dict['sample_rate'] = float(self.__sample_rate)
        settings_dict['analog_levels'] = tuple(self.__analog_levels)
        settings_dict['digital_levels'] = tuple(self.__digital_levels)
        settings_dict['interleave'] = bool(self.__interleave)
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
        return self.pulsegenerator().get_waveform_names()

    @property
    def sampled_sequences(self):
        return self.pulsegenerator().get_sequence_names()

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
            return_name = name_list[0]
            for name in name_list:
                if name != return_name:
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
        return self.pulse_generator_settings

    @QtCore.Slot()
    def clear_pulser(self):
        """
        """
        self.pulsegenerator().clear_all()
        # Delete all sampling information from all PulseBlockEnsembles and PulseSequences
        for seq in self._saved_pulse_sequences.values():
            seq.sampling_information = dict()
        for ens in self._saved_pulse_block_ensembles.values():
            ens.sampling_information = dict()
        self.sigAvailableWaveformsUpdated.emit(self.sampled_waveforms)
        self.sigAvailableSequencesUpdated.emit(self.sampled_sequences)
        self.sigLoadedAssetUpdated.emit('', '')
        return

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
            # Actually load the waveforms to the generic channels
            self.pulsegenerator().load_waveform(ensemble.sampling_information['waveforms'])
        else:
            self.log.error('Loading of PulseBlockEnsemble "{0}" failed.\n'
                           'It has not been generated yet.'.format(ensemble.name))
        self.sigLoadedAssetUpdated.emit(*self.loaded_asset)
        return

    @QtCore.Slot(str)
    @QtCore.Slot(object)
    def load_sequence(self, sequence):
        """

        @param str|PulseSequence sequence:
        """
        # If str has been passed, get the sequence object from saved sequences
        if isinstance(sequence, str):
            sequence = self.saved_pulse_sequences[sequence]
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
            # Actually load the sequence to the generic channels
            self.pulsegenerator().load_sequence(sequence.name)
        else:
            self.log.error('Loading of PulseSequence "{0}" failed.\n'
                           'It has not been generated yet.'.format(sequence.name))
        self.sigLoadedAssetUpdated.emit(*self.loaded_asset)
        return

    def _attach_predefined_methods(self):
        """
        Retrieve in the folder all files for predefined methods and attach their methods
        """
        self.__generate_methods = OrderedDict()

        # The assumption is that in the directory predefined_methods, there are
        # *.py files, which contain only methods!
        path = os.path.join(get_main_dir(), 'logic', 'predefined_methods')
        filename_list = [name[:-3] for name in os.listdir(path) if
                         os.path.isfile(os.path.join(path, name)) and name.endswith('.py')]

        # Also attach methods from the non-default additional methods directory if defined in config
        if self._additional_methods_dir:
            # attach to path
            sys.path.append(self._additional_methods_dir)
            path = self._additional_methods_dir
            filename_list.extend([name[:-3] for name in os.listdir(path) if
                                 os.path.isfile(os.path.join(path, name)) and name.endswith('.py')])

        # Import and attach methods to self
        for filename in filename_list:
            mod = importlib.import_module('logic.predefined_methods.{0}'.format(filename))
            # To allow changes in predefined methods during runtime by simply reloading the module.
            importlib.reload(mod)
            for method in dir(mod):
                try:
                    # Check for callable function or method:
                    ref = getattr(mod, method)
                    if callable(ref) and (inspect.ismethod(ref) or inspect.isfunction(ref)):
                        # Bind the method as an attribute to self
                        setattr(self, method, ref)
                        # Add method to dictionary if it is a generator method
                        if method.startswith('generate_'):
                            self.__generate_methods[method[9:]] = getattr(self, method)
                except:
                    self.log.error('It was not possible to import element {0} from {1} into '
                                   'SequenceGenerationLogic.'.format(method, filename))
        return

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
        return self.__generate_methods

    @property
    def sampling_settings(self):
        settings_dict = dict()
        settings_dict['laser_channel'] = self._laser_channel
        return settings_dict

    @sampling_settings.setter
    def sampling_settings(self, settings_dict):
        if isinstance(settings_dict, dict):
            self.set_sampling_settings(settings_dict)
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
    def set_sampling_settings(self, settings_dict=None, **kwargs):
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

            # Set laser channel if present
            if 'laser_channel' in settings_dict:
                if settings_dict['laser_channel'] not in self.__activation_config[1]:
                    self.log.error('Unable to set laser channel "{0}".\nLaser channel to set is '
                                   'not part of the current channel activation config ({1}).'
                                   ''.format(settings_dict['laser_channel'],
                                             self.__activation_config[1]))
                else:
                    self._laser_channel = settings_dict['laser_channel']

        else:
            self.log.error('Unable to apply new sampling settings.\n'
                           'SequenceGeneratorLogic is busy generating a waveform/sequence.')

        self.sigSamplingSettingsUpdated.emit(self.sampling_settings)
        return self.sampling_settings

    def save_block(self, block):
        """ Serialize a PulseBlock object to a *.blk file.

        @param name: string, name of the block to save
        @param block: PulseBlock object which will be serialized
        """
        if block.name in self._saved_pulse_blocks:
            self.log.info('Found old PulseBlock with name "{0}".\nOld PulseBlock overwritten by '
                          'new PulseBlock with the same name.'.format(block.name))
        self._saved_pulse_blocks[block.name] = block
        self._save_blocks_to_tmp_file()
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
        if name in self._saved_pulse_blocks:
            del(self._saved_pulse_blocks[name])
            self._save_blocks_to_tmp_file()
            self.sigBlockDictUpdated.emit(self._saved_pulse_blocks)
        else:
            self.log.warning('PulseBlock object with name "{0}" not found in saved '
                             'blocks.\nTherefore nothing is removed.'.format(name))
        return

    def _update_blocks_from_tmp_file(self):
        """
        Update the saved_pulse_blocks dict from temporary file.
        """
        block_file = None
        for file in os.listdir():
            if file.endswith('tmp_block_dict'):
                block_file = file
                break

        if not block_file:
            self.log.debug('No temporary serialized block dict was found.')
            return

        try:
            with open(block_file, 'rb') as infile:
                tmp_block_dict = pickle.load(infile)
            self._saved_pulse_blocks.update(tmp_block_dict)
        except:
            self.log.error('Failed to deserialize block dict from tmp file.')

        self._save_blocks_to_tmp_file()
        self.sigBlockDictUpdated.emit(self._saved_pulse_blocks)
        return

    def _save_blocks_to_tmp_file(self):
        """
        Saves the saved_pulse_blocks dict to a temporary file so they are not lost upon a qudi
        crash.
        """
        try:
            with open('tmp_block_dict.tmp', 'wb') as outfile:
                pickle.dump(self._saved_pulse_blocks, outfile)
        except:
            self.log.error('Failed to serialize block dict in "tmp_block_dict.tmp".')
            return

        # remove old file and rename temp file
        try:
            os.rename('tmp_block_dict.tmp', 'tmp_block_dict')
        except WindowsError:
            os.remove('tmp_block_dict')
            os.rename('tmp_block_dict.tmp', 'tmp_block_dict')
        return

    def save_ensemble(self, ensemble):
        """ Saves a PulseBlockEnsemble with name name to file.

        @param str name: name of the ensemble, which will be serialized.
        @param obj ensemble: a PulseBlockEnsemble object
        """
        if ensemble.name in self._saved_pulse_blocks:
            self.log.info('Found old PulseBlockEnsemble with name "{0}".\nOld PulseBlockEnsemble '
                          'overwritten by new PulseBlockEnsemble with the same name.'
                          ''.format(ensemble.name))

        # Make sure no sampling information is present upon saving the object instance
        ensemble.sampling_information = dict()

        self._saved_pulse_block_ensembles[ensemble.name] = ensemble
        self._save_ensembles_to_tmp_file()
        self.sigEnsembleDictUpdated.emit(self._saved_pulse_block_ensembles)
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
        Remove the ensemble with 'name' from the ensemble list and all associated waveforms
        from the pulser memory.
        """
        if name in self.saved_pulse_block_ensembles:
            ensemble = self.get_ensemble(name)
            # check if ensemble has already been sampled and delete associated waveforms
            if ensemble.sampling_information:
                self._delete_waveform(ensemble.sampling_information['waveforms'])
                self.sigAvailableWaveformsUpdated.emit(self.sampled_waveforms)
            # delete PulseBlockEnsemble
            del(self._saved_pulse_block_ensembles[name])
            self._save_ensembles_to_tmp_file()
            self.sigEnsembleDictUpdated.emit(self._saved_pulse_block_ensembles)
        else:
            self.log.warning('PulseBlockEnsemble object with name "{0}" not found in saved '
                             'block ensembles.\nTherefore nothing is removed.'.format(name))
        return

    def _update_ensembles_from_tmp_file(self):
        """
        Update the saved_pulse_block_ensembles dict from temporary file.
        """
        ensemble_file = None
        for file in os.listdir():
            if file.endswith('tmp_ensemble_dict'):
                ensemble_file = file
                break

        if not ensemble_file:
            self.log.debug('No temporary serialized block ensemble dict was found.')
            return

        try:
            with open(ensemble_file, 'rb') as infile:
                tmp_ensemble_dict = pickle.load(infile)
            self._saved_pulse_block_ensembles.update(tmp_ensemble_dict)
        except:
            self.log.error('Failed to deserialize block ensemble dict from tmp file.')

        self._save_ensembles_to_tmp_file()
        self.sigEnsembleDictUpdated.emit(self._saved_pulse_block_ensembles)
        return

    def _save_ensembles_to_tmp_file(self):
        """
        Saves the saved_pulse_block_ensembles dict to a temporary file so they are not lost upon a
        qudi crash.
        """
        try:
            with open('tmp_ensemble_dict.tmp', 'wb') as outfile:
                pickle.dump(self._saved_pulse_block_ensembles, outfile)
        except:
            if 'tmp_ensemble_dict.tmp' in os.listdir():
                os.remove('tmp_ensemble_dict.tmp')
            self.log.error('Failed to serialize block ensemble dict in "tmp_ensemble_dict.tmp".')
            return

        # remove old file and rename temp file
        try:
            os.rename('tmp_ensemble_dict.tmp', 'tmp_ensemble_dict')
        except WindowsError:
            os.remove('tmp_ensemble_dict')
            os.rename('tmp_ensemble_dict.tmp', 'tmp_ensemble_dict')
        return

    def save_sequence(self, sequence):
        """ Serialize the PulseSequence object with name 'name' to file.

        @param str name: name of the sequence object.
        @param object sequence: a PulseSequence object, which is going to be
                                serialized to file.

        @return: str: name of the serialized object, if needed.
        """
        if sequence.name in self._saved_pulse_sequences:
            self.log.info('Found old PulseSequence with name "{0}".\nOld PulseSequence '
                          'overwritten by new PulseSequence with the same name.'
                          ''.format(sequence.name))

        # Make sure no sampling information is present upon saving the object instance
        sequence.sampling_information = dict()

        self._saved_pulse_sequences[sequence.name] = sequence
        self._save_sequences_to_tmp_file()
        self.sigSequenceDictUpdated.emit(self._saved_pulse_sequences)
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
        Remove the sequence with 'name' from the sequence list and all associated waveforms
        from the pulser memory.
        """
        if name in self.saved_pulse_sequences:
            sequence = self.get_sequence(name)
            # check if sequence has already been sampled and delete associated sequence from pulser.
            # Also delete associated waveforms if sequence has been sampled within rotating frame.
            if sequence.sampling_information:
                self._delete_sequence(name)
                if sequence.rotating_frame:
                    self._delete_waveform(sequence.sampling_information['waveforms'])
            # delete PulseSequence
            del(self._saved_pulse_sequences[name])
            self._save_sequences_to_tmp_file()
            self.sigSequenceDictUpdated.emit(self.saved_pulse_sequences)
        else:
            self.log.warning('PulseSequence object with name "{0}" not found in saved sequences.\n'
                             'Therefore nothing is removed.'.format(name))
        return

    def _update_sequences_from_tmp_file(self):
        """ Update the saved_pulse_sequences dict from file """
        sequence_file = None
        for file in os.listdir():
            if file.endswith('tmp_sequence_dict'):
                sequence_file = file
                break

        if not sequence_file:
            self.log.debug('No temporary serialized sequence dict was found.')
            return

        try:
            with open(sequence_file, 'rb') as infile:
                tmp_sequence_dict = pickle.load(infile)
            self._saved_pulse_sequences.update(tmp_sequence_dict)
        except:
            self.log.error('Failed to deserialize sequence dict from tmp file.')

        self._save_sequences_to_tmp_file()
        self.sigSequenceDictUpdated.emit(self._saved_pulse_sequences)
        return

    def _save_sequences_to_tmp_file(self):
        """ Saves the saved_pulse_sequences dict to file """
        try:
            with open('tmp_sequence_dict.tmp', 'wb') as outfile:
                pickle.dump(self._saved_pulse_sequences, outfile)
        except:
            if 'tmp_sequence_dict.tmp' in os.listdir():
                os.remove('tmp_sequence_dict.tmp')
            self.log.error('Failed to serialize sequence dict in "tmp_sequence_dict.tmp".')
            return

        # remove old file and rename temp file
        try:
            os.rename('tmp_sequence_dict.tmp', 'tmp_sequence_dict')
        except WindowsError:
            os.remove('tmp_sequence_dict')
            os.rename('tmp_sequence_dict.tmp', 'tmp_sequence_dict')
        return

    def generate_predefined_sequence(self, predefined_sequence_name, kwargs_dict):
        """

        @param predefined_sequence_name:
        @param kwargs_dict:
        @return:
        """
        gen_method = self.generate_methods[predefined_sequence_name]
        # match parameters to method and throw out unwanted ones
        method_params = inspect.signature(gen_method).parameters
        thrown_out_params = list()
        for param in kwargs_dict:
            if param not in method_params:
                thrown_out_params.append(param)
        for param in thrown_out_params:
            del kwargs_dict[param]
        if len(thrown_out_params) > 0:
            self.log.debug('Unused params during predefined sequence generation "{0}":\n'
                           '{1}'.format(predefined_sequence_name, thrown_out_params))
        try:
            gen_method(**kwargs_dict)
        except:
            self.log.error('Generation of predefined sequence "{0}" failed.'
                           ''.format(predefined_sequence_name))
            return
        self.sigPredefinedSequenceGenerated.emit(predefined_sequence_name)
        return

    def _cleanup_tmp_files(self):
        """
        Delete all temporary files containing saved PulseBlock/PulseBlockEnsemble/PulseSequence
        instances.
        They will still be saved to StatusVar.
        """
        dir_content = os.listdir()
        for file in ('tmp_block_dict', 'tmp_ensemble_dict', 'tmp_sequence_dict'):
            if file in dir_content:
                os.remove(file)
        return

    #---------------------------------------------------------------------------
    #                    END sequence/block generation
    #---------------------------------------------------------------------------


    #---------------------------------------------------------------------------
    #                    BEGIN sequence/block sampling
    #---------------------------------------------------------------------------
    def _analyze_block_ensemble(self, ensemble):
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
        # variables to keep track of the current timeframe
        current_end_time = 0.0
        current_start_bin = 0
        # dict containing the bins where the digital channels are rising/falling
        # (one arr for each channel)
        digital_rising_bins = dict()
        digital_falling_bins = dict()
        # memorize the channel state of the previous element
        tmp_digital_high = dict()

        # check for active channels
        digital_channels = set()
        analog_channels = set()
        if len(ensemble.block_list) > 0:
            block = self.get_block(ensemble.block_list[0][0])
            digital_channels = block.digital_channels
            analog_channels = block.analog_channels

        for chnl in digital_channels:
            digital_rising_bins[chnl] = list()
            digital_falling_bins[chnl] = list()
            # memorize the channel state of the previous element
            tmp_digital_high[chnl] = False

        # number of elements including repetitions and the length of each element in bins
        total_elements = 0
        elements_length_bins = np.array([], dtype='int64')

        for block_name, reps in ensemble.block_list:
            block = self.get_block(block_name)
            # Total number of elements in the current block including all repetitions
            unrolled_elements = (reps+1) * len(block.element_list)
            # Add this number to the total number of unrolled elements in the ensemble
            total_elements += unrolled_elements
            # Temporary array to hold the length for each element (including reps) in bins
            tmp_length_bins = np.zeros(unrolled_elements, dtype='int64')

            # Iterate over all repetitions of the current block
            unrolled_element_index = 0
            for rep_no in range(reps+1):
                # Iterate over the Block_Elements inside the current block
                for elem_index, block_element in enumerate(block.element_list):
                    # save bin position if a transition from low to high has occured in a digital
                    # channel
                    for chnl, state in block_element.digital_high.items():
                        if tmp_digital_high[chnl] != state:
                            if not tmp_digital_high[chnl] and state:
                                digital_rising_bins[chnl].append(current_start_bin)
                            else:
                                digital_falling_bins[chnl].append(current_start_bin)
                            tmp_digital_high[chnl] = state

                    # element length of the current element with current repetition count in sec
                    element_length_s = block_element.init_length_s + (
                                rep_no * block_element.increment_s)
                    # ideal end time for the sequence up until this point in sec
                    current_end_time += element_length_s
                    # Nearest possible match including the discretization in bins
                    current_end_bin = int(np.rint(current_end_time * self.__sample_rate))
                    # current element length in discrete bins
                    element_length_bins = current_end_bin - current_start_bin
                    tmp_length_bins[unrolled_element_index] = element_length_bins
                    # advance bin offset for next element
                    current_start_bin += element_length_bins
                    # increment element counter
                    unrolled_element_index += 1

            # append element lengths (in bins) to array
            elements_length_bins = np.append(elements_length_bins, tmp_length_bins)

        # calculate total number of samples
        number_of_samples = np.sum(elements_length_bins)

        # convert digital rising/falling indices to numpy.ndarrays
        for chnl in digital_channels:
            digital_rising_bins[chnl] = np.array(digital_rising_bins[chnl], dtype='int64')
            digital_falling_bins[chnl] = np.array(digital_falling_bins[chnl], dtype='int64')

        return_dict = dict()
        return_dict['number_of_samples'] = number_of_samples
        return_dict['total_elements'] = total_elements
        return_dict['length_elements_bins'] = elements_length_bins
        return_dict['digital_rising_bins'] = digital_rising_bins
        return_dict['digital_falling_bins'] = digital_falling_bins
        return_dict['analog_channels'] = analog_channels
        return_dict['digital_channels'] = digital_channels
        return_dict['channel_set'] = analog_channels.union(digital_channels)
        return return_dict

    def _analyze_sequence(self, sequence):
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
        # Determine channel activation
        digital_channels = set()
        analog_channels = set()
        if len(sequence.ensemble_list) > 0:
            ensemble = self.get_ensemble(sequence.ensemble_list[0][0])
            if len(ensemble.block_list) > 0:
                block = self.get_block(ensemble.block_list[0][0])
                digital_channels = block.digital_channels
                analog_channels = block.analog_channels

        # Check if any sequence step is running infinitely since this would render the
        # parameters meaningless.
        non_deterministic = False
        for ensemble_name, seq_params in sequence.ensemble_list:
            if seq_params['repetitions'] < 0:
                non_deterministic = True
                break
        # If the sequence does not contain infinite loop steps, determine the remaining parameters
        # TODO: Implement this!

        return_dict = dict()
        return_dict['digital_channels'] = digital_channels
        return_dict['analog_channels'] = analog_channels
        return_dict['channel_set'] = analog_channels.union(digital_channels)
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
        if len(blocks_missing) > 0 or channel_activation_mismatch:
            return -1
        else:
            return 0

    def _sampling_sequence_sanity_check(self, sequence):
        ensembles_missing = set()
        for ensemble_name, seq_params in sequence.ensemble_list:
            ensemble = self._saved_pulse_block_ensembles.get(ensemble_name)
            # Check if ensemble is present
            if ensemble is None:
                ensembles_missing.add(ensemble_name)
                continue

        # print error messages
        if len(ensembles_missing) > 0:
            self.log.error('Sampling of PulseSequence "{0}" failed. Not all PulseBlockEnsembles '
                           'found.\nPlease generate the following PulseBlockEnsembles: {1}'
                           ''.format(sequence.name, ensembles_missing))

        # Return error code
        if len(ensembles_missing) > 0:
            return -1
        else:
            return 0

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

        @return tuple: of length 2 with
                       (offset_bin, created_waveforms).
                        offset_bin:
                            integer, which is used for maintaining the rotation frame
                        created_waveforms:
                            list, a list of created waveform names

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
                return -1, list()

        # Perform sanity checks on ensemble and corresponding blocks
        if self._sampling_ensemble_sanity_check(ensemble) < 0:
            self.sigSampleEnsembleComplete.emit(None)
            return -1, list()

        # lock module if it's not already locked (sequence sampling in progress)
        if self.module_state() == 'idle':
            self.module_state.lock()
        elif not self.__sequence_generation_in_progress:
            self.sigSampleEnsembleComplete.emit(None)
            return -1, list()

        # Make sure the PulseBlockEnsemble is contained in the saved ensembles dict
        self._saved_pulse_block_ensembles[ensemble.name] = ensemble

        # Set the waveform name (excluding the device specific channel naming suffix, i.e. '_ch1')
        waveform_name = name_tag if name_tag else ensemble.name

        # check for old waveforms associated with the ensemble and delete them from pulse generator.
        # Also delete the sampling information afterwards since it is no longer valid.
        self._delete_waveform_by_nametag(waveform_name)
        if waveform_name == ensemble.name:
            ensemble.sampling_information = dict()
            self._saved_pulse_block_ensembles[ensemble.name] = ensemble

        start_time = time.time()

        # get important parameters from the ensemble
        ensemble_info = self._analyze_block_ensemble(ensemble)

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
            return -1, list()

        # Index to keep track of the sample array entries already processed
        processed_samples = 0
        # Index to keep track of the samples written into the preallocated samples array
        array_write_index = 0
        # Keep track of the element index written
        element_count = 0
        # set of written waveform names on the device
        written_waveforms = set()
        # Iterate over all blocks within the PulseBlockEnsemble object
        for block_name, reps in ensemble.block_list:
            block = self.get_block(block_name)
            # Iterate over all repetitions of the current block
            for rep_no in range(reps+1):
                # Iterate over the Block_Elements inside the current block
                for block_element in block.element_list:
                    digital_high = block_element.digital_high
                    pulse_function = block_element.pulse_function
                    element_length_bins = ensemble_info['length_elements_bins'][element_count]
                    # Increment element index
                    element_count += 1

                    # Indicator on how many samples of this element have been written already
                    element_samples_written = 0

                    while element_samples_written != element_length_bins:
                        samples_to_add = min(array_length - array_write_index, element_length_bins - element_samples_written)
                        # create floating point time array for the current element inside rotating
                        # frame if analog samples are to be calculated.
                        if pulse_function:
                            time_arr = (offset_bin + np.arange(samples_to_add,
                                                               dtype='float64')) / self.__sample_rate

                        # Calculate respective part of the sample arrays
                        for chnl in digital_high:
                            digital_samples[chnl][array_write_index:array_write_index+samples_to_add] = np.full(samples_to_add, digital_high[chnl], dtype=bool)
                        for chnl in pulse_function:
                            analog_samples[chnl][array_write_index:array_write_index+samples_to_add] = np.float32(pulse_function[chnl].get_samples(time_arr)/self.__analog_levels[0][chnl])

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
                                is_last_chunk=is_last_chunk)

                            # Update written waveforms set
                            written_waveforms.update(wfm_list)

                            # check if write process was successful
                            if written_samples != array_length:
                                self.log.error('Sampling of block "{0}" in ensemble "{1}" failed. '
                                               'Write to device was unsuccessful.'
                                               ''.format(block_name, ensemble.name))
                                if not self.__sequence_generation_in_progress:
                                    self.module_state.unlock()
                                self.sigAvailableWaveformsUpdated.emit(self.sampled_waveforms)
                                self.sigSampleEnsembleComplete.emit(None)
                                return -1, list()

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

        # Save sampling related parameters to the sampling_information container within the
        # PulseBlockEnsemble.
        # This step is only performed if the resulting waveforms are named by the PulseBlockEnsemble
        # and not by a sequence nametag
        if waveform_name == ensemble.name:
            ensemble.sampling_information.update(ensemble_info)
            ensemble.sampling_information['sample_rate'] = self.__sample_rate
            ensemble.sampling_information['activation_config'] = self.__activation_config
            ensemble.sampling_information['analog_levels'] = self.__analog_levels
            ensemble.sampling_information['digital_levels'] = self.__digital_levels
            ensemble.sampling_information['interleave'] = self.__interleave
            ensemble.sampling_information['waveforms'] = list(written_waveforms)
            self._saved_pulse_block_ensembles[ensemble.name] = ensemble

        self.log.info('Time needed for sampling and writing PulseBlockEnsemble to device: {0} sec'
                      ''.format(int(np.rint(time.time() - start_time))))
        if not self.__sequence_generation_in_progress:
            self.module_state.unlock()
        self.sigAvailableWaveformsUpdated.emit(self.sampled_waveforms)
        self.sigSampleEnsembleComplete.emit(ensemble)
        return offset_bin, list(written_waveforms)

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

        # Clear sampling_information container.
        sequence.sampling_information = dict()
        # Make sure the PulseSequence is contained in the saved sequences dict
        self._saved_pulse_sequences[sequence.name] = sequence

        # delete already written sequences on the device memory.
        if sequence.name in self.sampled_sequences:
            self.pulsegenerator().delete_sequence(sequence.name)

        start_time = time.time()

        # Produce a set of created waveforms
        written_waveforms = set()
        # Keep track of generated PulseBlockEnsembles
        generated_ensembles = set()

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
        for ensemble_index, (ensemble_name, seq_param) in enumerate(sequence.ensemble_list):
            if sequence.rotating_frame:
                # to make something like 001
                name_tag = sequence.name + '_' + str(ensemble_index).zfill(3)
            else:
                name_tag = None
                offset_bin = 0  # Keep the offset at 0

            # Only sample ensembles if they have not already been sampled
            if sequence.rotating_frame or ensemble_name not in generated_ensembles:
                offset_bin, waveform_list = self.sample_pulse_block_ensemble(ensemble=ensemble_name,
                                                                             offset_bin=offset_bin,
                                                                             name_tag=name_tag)

            if len(waveform_list) == 0:
                self.log.error('Sampling of PulseBlockEnsemble "{0}" failed during sampling of '
                               'PulseSequence "{1}".\nFailed to create waveforms on device.'
                               ''.format(ensemble_name, sequence.name))
                self.module_state.unlock()
                self.__sequence_generation_in_progress = False
                self.sigSampleSequenceComplete.emit(None)
                return

            # Add created waveform names to the set
            written_waveforms.update(waveform_list)
            # Add generated ensemble name to the set
            generated_ensembles.add(ensemble_name)

            # Append written sequence step to sequence_param_dict_list
            sequence_param_dict_list.append((tuple(waveform_list), seq_param))

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
        sequence.sampling_information.update(self._analyze_sequence(sequence))
        sequence.sampling_information['sample_rate'] = self.__sample_rate
        sequence.sampling_information['activation_config'] = self.__activation_config
        sequence.sampling_information['analog_levels'] = self.__analog_levels
        sequence.sampling_information['digital_levels'] = self.__digital_levels
        sequence.sampling_information['interleave'] = self.__interleave
        sequence.sampling_information['waveforms'] = list(written_waveforms)
        self._saved_pulse_sequences[sequence.name] = sequence

        self.log.info('Time needed for sampling and writing PulseSequence to device: {0} sec.'
                      ''.format(int(np.rint(time.time() - start_time))))

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

    #---------------------------------------------------------------------------
    #                    END sequence/block sampling
    #---------------------------------------------------------------------------
    # def set_settings(self, settings_dict):
    #     """
    #     Sets all settings for the generator logic.
    #
    #     @param settings_dict: dict, A dictionary containing the settings to change.
    #
    #     @return dict: A dictionary containing the actually set values for all changed settings
    #     """
    #     # The returned dictionary. It will contain the actually set parameter values.
    #     actual_settings = dict()
    #
    #     # Try to set new activation config.
    #     if 'activation_config' in settings_dict:
    #         avail_configs = self.pulsegenerator().get_constraints().activation_config
    #         # If activation_config is not within pulser constraints, do not change it.
    #         if settings_dict['activation_config'] not in avail_configs:
    #             self.log.error('Unable to set activation_config "{0}" since it can not be found in '
    #                            'pulser constraints.\nPrevious config "{1}" will stay in effect.'
    #                            ''.format(settings_dict['activation_config'],
    #                                      self.activation_config[0]))
    #
    #         else:
    #             channels_to_activate = avail_configs[settings_dict['activation_config']]
    #             channel_state = self.pulsegenerator().get_active_channels()
    #             for chnl in channel_state:
    #                 if chnl in channels_to_activate:
    #                     channel_state[chnl] = True
    #                 else:
    #                     channel_state[chnl] = False
    #             set_channel_states = self.pulsegenerator().set_active_channels(channel_state)
    #             set_activation_config = {chnl for chnl in set_channel_states if
    #                                      set_channel_states[chnl]}
    #             for name, config in avail_configs.items():
    #                 if config == set_activation_config:
    #                     self.activation_config = (name, config)
    #                     break
    #             if self.activation_config[1] != set_activation_config:
    #                 self.activation_config[0] = ''
    #                 self.log.error('Setting activation_config "{0}" failed.\n'
    #                                'Reload module to avoid undexpected behaviour.'
    #                                ''.format(settings_dict['activation_config']))
    #
    #             self.analog_channels = len(
    #                 [chnl for chnl in self.activation_config[1] if 'a_ch' in chnl])
    #             self.digital_channels = len(
    #                 [chnl for chnl in self.activation_config[1] if 'd_ch' in chnl])
    #
    #             # Check if the laser channel is being set at the same time. If not, check if a
    #             # change of laser channel is necessary due to the changed activation_config.
    #             # If the laser_channel needs to be changed add it to settings_dict.
    #             if 'laser_channel' not in settings_dict and self.laser_channel not in self.activation_config[1]:
    #                 settings_dict['laser_channel'] = self.laser_channel
    #         actual_settings['activation_config'] = self.activation_config[0]
    #
    #     # Try to set new laser_channel. Check if it's part of the current activation_config and
    #     # adjust to first valid digital channel if not.
    #     if 'laser_channel' in settings_dict:
    #         if settings_dict['laser_channel'] in self.activation_config[1]:
    #             self.laser_channel = settings_dict['laser_channel']
    #         elif self.digital_channels > 0:
    #             for chnl in self.activation_config[1]:
    #                 if 'd_ch' in chnl:
    #                     new_laser_channel = chnl
    #                     break
    #             self.log.warning('Unable to set laser_channel "{0}" since it is not in current '
    #                              'activation_config.\nLaser_channel set to "{1}" instead.'
    #                              ''.format(self.laser_channel, new_laser_channel))
    #             self.laser_channel = new_laser_channel
    #         else:
    #             self.log.error('Unable to set new laser_channel "{0}". '
    #                            'No digital channel in current activation_config.'
    #                            ''.format(settings_dict['laser_channel']))
    #             self.laser_channel = ''
    #         actual_settings['laser_channel'] = self.laser_channel
    #
    #     # Try to set the sample rate
    #     if 'sample_rate' in settings_dict:
    #         # If sample rate already set, do nothing
    #         if settings_dict['sample_rate'] != self.sample_rate:
    #             sample_rate_constr = self.pulsegenerator().get_constraints().sample_rate
    #             # Check boundaries with constraints
    #             if settings_dict['sample_rate'] > sample_rate_constr.max:
    #                 self.log.warning('Sample rate to set ({0}) larger than allowed maximum ({1}).\n'
    #                                  'New sample rate will be set to maximum value.'
    #                                  ''.format(settings_dict['sample_rate'],
    #                                            sample_rate_constr.max))
    #                 settings_dict['sample_rate'] = sample_rate_constr.max
    #             elif settings_dict['sample_rate'] < sample_rate_constr.min:
    #                 self.log.warning('Sample rate to set ({0}) smaller than allowed minimum ({1}).'
    #                                  '\nNew sample rate will be set to minimum value.'
    #                                  ''.format(settings_dict['sample_rate'],
    #                                            sample_rate_constr.min))
    #                 settings_dict['sample_rate'] = sample_rate_constr.min
    #
    #             self.sample_rate = self.pulsegenerator().set_sample_rate(
    #                 settings_dict['sample_rate'])
    #         actual_settings['sample_rate'] = self.sample_rate
    #
    #     # Try to set the pp-amplitudes for analog channels
    #     if 'analog_pp_amplitude' in settings_dict:
    #         # if no change is needed, do nothing
    #         if settings_dict['analog_pp_amplitude'] != self.analog_pp_amplitude:
    #             analog_constr = self.pulsegenerator().get_constraints().a_ch_amplitude
    #             # Get currently set pp-amplitudes
    #             current_analog_amp = self.pulsegenerator().get_analog_level(
    #                 amplitude=list(settings_dict['analog_pp_amplitude']))
    #             # Check boundaries with constraints
    #             for chnl, value in settings_dict['analog_pp_amplitude'].items():
    #                 if value > analog_constr.max:
    #                     self.log.warning('pp-amplitude to set ({0}) larger than allowed maximum '
    #                                      '({1}).\nNew pp-amplitude will be set to maximum value.'
    #                                      ''.format(value, analog_constr.max))
    #                     settings_dict['analog_pp_amplitude'][chnl] = analog_constr.max
    #                 elif settings_dict['sample_rate'] < sample_rate_constr.min:
    #                     self.log.warning('pp-amplitude to set ({0}) smaller than allowed minimum '
    #                                      '({1}).\nNew pp-amplitude will be set to minimum value.'
    #                                      ''.format(value, analog_constr.min))
    #                     settings_dict['analog_pp_amplitude'][chnl] = analog_constr.min
    #                 if chnl not in current_analog_amp:
    #                     self.log.error('Trying to set pp-amplitude for non-existent channel "{0}"!'
    #                                    ''.format(chnl))
    #
    #             self.analog_pp_amplitude, dummy = self.pulsegenerator().set_analog_level(
    #                 amplitude=settings_dict['analog_pp_amplitude'])
    #
    #         actual_settings['analog_pp_amplitude'] = self.analog_pp_amplitude
    #
    #     self.sigSettingsUpdated.emit(actual_settings)
    #     return actual_settings