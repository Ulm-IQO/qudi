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
from core.module import StatusVar
from core.util.modules import get_home_dir
from core.util.modules import get_main_dir

from logic.pulse_objects import PulseBlockElement
from logic.pulse_objects import PulseBlock
from logic.pulse_objects import PulseBlockEnsemble
from logic.pulse_objects import PulseSequence
from logic.generic_logic import GenericLogic
# from logic.sampling_functions import SamplingFunctions
from logic.samples_write_methods import SamplesWriteMethods


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
    pulse_generator = Connector(interface='PulserInterface')

    # status vars
    laser_channel = StatusVar('laser_channel', 'd_ch1')

    # define signals
    sigBlockDictUpdated = QtCore.Signal(dict)
    sigEnsembleDictUpdated = QtCore.Signal(dict)
    sigSequenceDictUpdated = QtCore.Signal(dict)
    sigSampleEnsembleComplete = QtCore.Signal(str, dict, dict)
    sigSampleSequenceComplete = QtCore.Signal(str, list)
    sigCurrentBlockUpdated = QtCore.Signal(object)
    sigCurrentEnsembleUpdated = QtCore.Signal(object)
    sigCurrentSequenceUpdated = QtCore.Signal(object)
    sigSettingsUpdated = QtCore.Signal(dict)
    sigPredefinedSequencesUpdated = QtCore.Signal(dict)
    sigPredefinedSequenceGenerated = QtCore.Signal(str)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.debug('The following configuration was found.')
        # checking for the right configuration
        for key in config.keys():
            self.log.debug('{0}: {1}'.format(key, config[key]))

        if 'pulsed_file_dir' in config.keys():
            self.pulsed_file_dir = config['pulsed_file_dir']
            if not os.path.exists(self.pulsed_file_dir):
                homedir = get_home_dir()
                self.pulsed_file_dir = os.path.join(homedir, 'pulsed_files')
                self.log.warning('The directort defined in "pulsed_file_dir" in the config for '
                                 'SequenceGeneratorLogic class does not exist! The default home '
                                 'directory\n{0}'
                                 '\nwill be taken instead.'.format(self.pulsed_file_dir))
        else:
            homedir = get_home_dir()
            self.pulsed_file_dir = os.path.join(homedir, 'pulsed_files')
            self.log.warning('No directory with the attribute "pulsed_file_dir" is defined for the '
                             'SequenceGeneratorLogic! The default home directory\n{0}\nwill be '
                             'taken instead.'.format(self.pulsed_file_dir))

        # Byte size of the max. memory usage during sampling/write-to-file process
        if 'overhead_bytes' in config.keys():
            self.sampling_overhead_bytes = config['overhead_bytes']
        else:
            self.sampling_overhead_bytes = None
            self.log.warning('No max. memory overhead specified in config.\nIn order to avoid '
                             'memory overflow during sampling/writing of Pulse objects you must '
                             'set "overhead_bytes".')

        # directory for additional generate methods to import
        # (other than qudi/logic/predefined_methods)
        if 'additional_methods_dir' in config.keys():
            if os.path.exists(config['additional_methods_dir']):
                self.additional_methods_dir = config['additional_methods_dir']
            else:
                self.additional_methods_dir = None
                self.log.error('Specified path "{0}" for import of additional generate methods '
                               'does not exist.'.format(config['additional_methods_dir']))
        else:
            self.additional_methods_dir = None

        # The created pulse objects (PulseBlock, PulseBlockEnsemble, PusleSequence) are saved in
        # these dictionaries. The keys are the names.
        self.saved_pulse_blocks = OrderedDict()
        self.saved_pulse_block_ensembles = OrderedDict()
        self.saved_pulse_sequences = OrderedDict()

        self.block_dir = self._get_dir_for_name('pulse_block_objects')
        self.ensemble_dir = self._get_dir_for_name('pulse_ensemble_objects')
        self.sequence_dir = self._get_dir_for_name('sequence_objects')

        # a dictionary with all predefined generator methods and measurement sequence names
        self.generate_methods = None

        # current pulse generator parameters that are frequently used by this logic.
        # Save them here since reading them from device every time they are used may take some time.
        self.activation_config = ('', set())
        self.sample_rate = 0.0
        self.analog_pp_amplitude = dict()
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # Get connector to pulse generator hardware
        self._pulse_generator = self.get_connector('pulse_generator')

        # Read saved pulse objects from file
        self._get_blocks_from_file()
        self._get_ensembles_from_file()
        self._get_sequences_from_file()

        # Get method definitions for prefined pulse sequences from seperate modules and attach them
        # to this module.
        self._attach_predefined_methods()

        # Read activation_config from device.
        channel_state = self._pulse_generator.get_active_channels()
        current_config = {chnl for chnl in channel_state if channel_state[chnl]}
        avail_configs = self._pulse_generator.get_constraints().activation_config
        # Set first available config if read config is not valid.
        if current_config not in avail_configs.values():
            config_to_set = avail_configs[list(avail_configs)[0]]
            for chnl in channel_state:
                if chnl in config_to_set:
                    channel_state[chnl] = True
                else:
                    channel_state[chnl] = False
            set_channel_state = self._pulse_generator.set_active_channels(channel_state)
            set_config = {chnl for chnl in set_channel_state if set_channel_state[chnl]}
            if set_config != config_to_set:
                self.activation_config = ('', set_config)
                self.log.error('Error during activation.\n'
                               'Unable to set activation_config that was taken from pulse '
                               'generator constraints.\n'
                               'Probably one or more activation_configs in constraints invalid.')
            else:
                self.activation_config = (list(avail_configs)[0], set_config)
        else:
            for name, config in avail_configs.items():
                if config == current_config:
                    self.activation_config = (name, current_config)
                    break

        # Information on used channel configuration for sequence generation
        self.analog_channels = len([chnl for chnl in self.activation_config if 'a_ch' in chnl])
        self.digital_channels = len([chnl for chnl in self.activation_config if 'd_ch' in chnl])

        # Read sample rate from device
        self.sample_rate = self._pulse_generator.get_sample_rate()

        # Read pp-voltages from device

        settings = dict()
        settings['activation_config'] = self.activation_config
        settings['laser_channel'] = self.laser_channel
        settings['sample_rate'] = self.sample_rate
        settings['analog_pp_amplitude'] = self.analog_pp_amplitude
        self.sigSettingsUpdated.emit(settings)

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        return

    def _attach_predefined_methods(self):
        """
        Retrieve in the folder all files for predefined methods and attach their methods to the

        @return:
        """
        self.generate_methods = OrderedDict()
        filenames_list = []
        additional_filenames_list = []
        # The assumption is that in the directory predefined_methods, there are
        # *.py files, which contain only methods!
        path = os.path.join(get_main_dir(), 'logic', 'predefined_methods')
        for entry in os.listdir(path):
            filepath = os.path.join(path, entry)
            if os.path.isfile(filepath) and entry.endswith('.py'):
                filenames_list.append(entry[:-3])
        # Also attach methods from the non-default additional methods directory if defined in config
        if self.additional_methods_dir is not None:
            # attach to path
            sys.path.append(self.additional_methods_dir)
            for entry in os.listdir(self.additional_methods_dir):
                filepath = os.path.join(self.additional_methods_dir, entry)
                if os.path.isfile(filepath) and entry.endswith('.py'):
                    additional_filenames_list.append(entry[:-3])

        for filename in filenames_list:
            mod = importlib.import_module('logic.predefined_methods.{0}'.format(filename))
            # To allow changes in predefined methods during runtime by simply reloading
            # sequence_generator_logic.
            importlib.reload(mod)
            for method in dir(mod):
                try:
                    # Check for callable function or method:
                    ref = getattr(mod, method)
                    if callable(ref) and (inspect.ismethod(ref) or inspect.isfunction(ref)):
                        # Bind the method as an attribute to the Class
                        setattr(SequenceGeneratorLogic, method, getattr(mod, method))
                        # Add method to dictionary if it is a generator method
                        if method.startswith('generate_'):
                            self.generate_methods[method[9:]] = eval('self.'+method)
                except:
                    self.log.error('It was not possible to import element {0} from {1} into '
                                   'SequenceGenerationLogic.'.format(method, filename))

        for filename in additional_filenames_list:
            mod = importlib.import_module(filename)
            for method in dir(mod):
                try:
                    # Check for callable function or method:
                    ref = getattr(mod, method)
                    if callable(ref) and (inspect.ismethod(ref) or inspect.isfunction(ref)):
                        # Bind the method as an attribute to the Class
                        setattr(SequenceGeneratorLogic, method, getattr(mod, method))
                        # Add method to dictionary if it is a generator method
                        if method.startswith('generate_'):
                            self.generate_methods[method[9:]] = eval('self.'+method)
                except:
                    self.log.error('It was not possible to import element {0} from {1} into '
                                   'SequenceGenerationLogic.'.format(method, filepath))

        self.sigPredefinedSequencesUpdated.emit(self.generate_methods)
        return

    def _get_dir_for_name(self, name):
        """ Get the path to the pulsed sub-directory 'name'.

        @param str name: name of the folder
        @return: str, absolute path to the directory with folder 'name'.
        """
        path = os.path.join(self.pulsed_file_dir, name)
        if not os.path.exists(path):
            os.makedirs(os.path.abspath(path))
        return os.path.abspath(path)

    # def request_init_values(self):
    #     """
    #
    #     @return:
    #     """
    #     self.sigBlockDictUpdated.emit(self.saved_pulse_blocks)
    #     self.sigEnsembleDictUpdated.emit(self.saved_pulse_block_ensembles)
    #     self.sigSequenceDictUpdated.emit(self.saved_pulse_sequences)
    #     self.sigCurrentBlockUpdated.emit(self.current_block)
    #     self.sigCurrentEnsembleUpdated.emit(self.current_ensemble)
    #     self.sigCurrentSequenceUpdated.emit(self.current_sequence)
    #     self.sigSettingsUpdated.emit(self.activation_config, self.laser_channel, self.sample_rate,
    #                                  self.amplitude_dict, self.waveform_format)
    #     self.sigPredefinedSequencesUpdated.emit(self.generate_methods)
    #     return

    def set_settings(self, settings_dict):
        """
        Sets all settings for the generator logic.

        @param settings_dict: dict, A dictionary containing the settings to change.

        @return dict: A dictionary containing the actually set values for all changed settings
        """
        # The returned dictionary. It will contain the actually set parameter values.
        actual_settings = dict()

        # Try to set new activation config.
        if 'activation_config' in settings_dict:
            avail_configs = self._pulse_generator.get_constraints().activation_config
            # If activation_config is not within pulser constraints, do not change it.
            if settings_dict['activation_config'] not in avail_configs:
                self.log.error('Unable to set activation_config "{0}" since it can not be found in '
                               'pulser constraints.\nPrevious config "{1}" will stay in effect.'
                               ''.format(settings_dict['activation_config'],
                                         self.activation_config[0]))

            else:
                channels_to_activate = avail_configs[settings_dict['activation_config']]
                channel_state = self._pulse_generator.get_active_channels()
                for chnl in channel_state:
                    if chnl in channels_to_activate:
                        channel_state[chnl] = True
                    else:
                        channel_state[chnl] = False
                set_channel_states = self._pulse_generator.set_active_channels(channel_state)
                set_activation_config = {chnl for chnl in set_channel_states if
                                         set_channel_states[chnl]}
                for name, config in avail_configs.items():
                    if config == set_activation_config:
                        self.activation_config = (name, config)
                        break
                if self.activation_config[1] != set_activation_config:
                    self.activation_config[0] = ''
                    self.log.error('Setting activation_config "{0}" failed.\n'
                                   'Reload module to avoid undexpected behaviour.'
                                   ''.format(settings_dict['activation_config']))

                self.analog_channels = len(
                    [chnl for chnl in self.activation_config[1] if 'a_ch' in chnl])
                self.digital_channels = len(
                    [chnl for chnl in self.activation_config[1] if 'd_ch' in chnl])

                # Check if the laser channel is being set at the same time. If not, check if a
                # change of laser channel is necessary due to the changed activation_config.
                # If the laser_channel needs to be changed add it to settings_dict.
                if 'laser_channel' not in settings_dict and self.laser_channel not in self.activation_config[1]:
                    settings_dict['laser_channel'] = self.laser_channel
            actual_settings['activation_config'] = self.activation_config[0]

        # Try to set new laser_channel. Check if it's part of the current activation_config and
        # adjust to first valid digital channel if not.
        if 'laser_channel' in settings_dict:
            if settings_dict['laser_channel'] in self.activation_config[1]:
                self.laser_channel = settings_dict['laser_channel']
            elif self.digital_channels > 0:
                for chnl in self.activation_config[1]:
                    if 'd_ch' in chnl:
                        new_laser_channel = chnl
                        break
                self.log.warning('Unable to set laser_channel "{0}" since it is not in current '
                                 'activation_config.\nLaser_channel set to "{1}" instead.'
                                 ''.format(self.laser_channel, new_laser_channel))
                self.laser_channel = new_laser_channel
            else:
                self.log.error('Unable to set new laser_channel "{0}". '
                               'No digital channel in current activation_config.'
                               ''.format(settings_dict['laser_channel']))
                self.laser_channel = ''
            actual_settings['laser_channel'] = self.laser_channel

        # Try to set the sample rate
        if 'sample_rate' in settings_dict:
            # If sample rate already set, do nothing
            if settings_dict['sample_rate'] != self.sample_rate:
                sample_rate_constr = self._pulse_generator.get_constraints().sample_rate
                # Check boundaries with constraints
                if settings_dict['sample_rate'] > sample_rate_constr.max:
                    self.log.warning('Sample rate to set ({0}) larger than allowed maximum ({1}).\n'
                                     'New sample rate will be set to maximum value.'
                                     ''.format(settings_dict['sample_rate'],
                                               sample_rate_constr.max))
                    settings_dict['sample_rate'] = sample_rate_constr.max
                elif settings_dict['sample_rate'] < sample_rate_constr.min:
                    self.log.warning('Sample rate to set ({0}) smaller than allowed minimum ({1}).'
                                     '\nNew sample rate will be set to minimum value.'
                                     ''.format(settings_dict['sample_rate'],
                                               sample_rate_constr.min))
                    settings_dict['sample_rate'] = sample_rate_constr.min

                self.sample_rate = self._pulse_generator.set_sample_rate(
                    settings_dict['sample_rate'])
            actual_settings['sample_rate'] = self.sample_rate

        # Try to set the pp-amplitudes for analog channels
        if 'analog_pp_amplitude' in settings_dict:
            # if no change is needed, do nothing
            if settings_dict['analog_pp_amplitude'] != self.analog_pp_amplitude:
                analog_constr = self._pulse_generator.get_constraints().a_ch_amplitude
                # Get currently set pp-amplitudes
                current_analog_amp = self._pulse_generator.get_analog_level(
                    amplitude=list(settings_dict['analog_pp_amplitude']))
                # Check boundaries with constraints
                for chnl, value in settings_dict['analog_pp_amplitude'].items():
                    if value > analog_constr.max:
                        self.log.warning('pp-amplitude to set ({0}) larger than allowed maximum '
                                         '({1}).\nNew pp-amplitude will be set to maximum value.'
                                         ''.format(value, analog_constr.max))
                        settings_dict['analog_pp_amplitude'][chnl] = analog_constr.max
                    elif settings_dict['sample_rate'] < sample_rate_constr.min:
                        self.log.warning('pp-amplitude to set ({0}) smaller than allowed minimum '
                                         '({1}).\nNew pp-amplitude will be set to minimum value.'
                                         ''.format(value, analog_constr.min))
                        settings_dict['analog_pp_amplitude'][chnl] = analog_constr.min
                    if chnl not in current_analog_amp:
                        self.log.error('Trying to set pp-amplitude for non-existent channel "{0}"!'
                                       ''.format(chnl))

                self.analog_pp_amplitude, dummy = self._pulse_generator.set_analog_level(
                    amplitude=settings_dict['analog_pp_amplitude'])

            actual_settings['analog_pp_amplitude'] = self.analog_pp_amplitude

        self.sigSettingsUpdated.emit(actual_settings)
        return actual_settings

# -----------------------------------------------------------------------------
#                    BEGIN sequence/block generation
# -----------------------------------------------------------------------------
    def get_saved_asset(self, name):
        """
        Returns the data object for a saved Ensemble/Sequence with name "name". Searches in the
        saved assets for a Sequence object first. If no Sequence by that name could be found search
        for Ensembles instead. If neither could be found return None.
        @param name: Name of the Sequence/Ensemble
        @return: PulseSequence | PulseBlockEnsemble | None
        """
        if name == '':
            asset_obj = None
        elif name in list(self.saved_pulse_sequences):
            asset_obj = self.saved_pulse_sequences[name]
        elif name in list(self.saved_pulse_block_ensembles):
            asset_obj = self.saved_pulse_block_ensembles[name]
        else:
            asset_obj = None
            self.log.warning('No PulseSequence or PulseBlockEnsemble by the name "{0}" could be '
                             'found in saved assets. Returning None.'.format(name))
        return asset_obj


    def save_block(self, name, block):
        """ Serialize a PulseBlock object to a *.blk file.

        @param name: string, name of the block to save
        @param block: PulseBlock object which will be serialized
        """
        # TODO: Overwrite handling
        block.name = name
        self.current_block = block
        self.saved_pulse_blocks[name] = block
        self._save_blocks_to_file()
        self.sigBlockDictUpdated.emit(self.saved_pulse_blocks)
        return

    def load_block(self, name):
        """

        @param name:
        @return:
        """
        if name not in self.saved_pulse_blocks:
            self.log.error('PulseBlock "{0}" could not be found in saved pulse blocks. Load failed.'
                           ''.format(name))
            return
        block = self.saved_pulse_blocks[name]
        self.current_block = block
        self.sigCurrentBlockUpdated.emit(self.current_block)
        return

    def delete_block(self, name):
        """ Remove the serialized object "name" from the block list and HDD.

        @param name: string, name of the PulseBlock object to be removed.
        """
        if name in list(self.saved_pulse_blocks):
            del(self.saved_pulse_blocks[name])
            if hasattr(self.current_block, 'name'):
                if self.current_block.name == name:
                    self.current_block = None
                    self.sigCurrentBlockUpdated.emit(self.current_block)
            self._save_blocks_to_file()
            self.sigBlockDictUpdated.emit(self.saved_pulse_blocks)
        else:
            self.log.warning('PulseBlock object with name "{0}" not found in saved '
                             'blocks.\nTherefore nothing is removed.'.format(name))
        return

    def _get_blocks_from_file(self):
        """ Update the saved_pulse_block dict from file """
        block_files = [f for f in os.listdir(self.block_dir) if 'block_dict.blk' in f]
        if len(block_files) == 0:
            self.log.info('No serialized block dict was found in {0}.'.format(self.block_dir))
            self.saved_pulse_blocks = OrderedDict()
            self.sigBlockDictUpdated.emit(self.saved_pulse_blocks)
            return
        # raise error if more than one file is present
        if len(block_files) > 1:
            self.log.error('More than one serialized block dict was found in {0}.\n'
                           'Using {1}.'.format(self.block_dir, block_files[-1]))
        block_files = block_files[-1]
        try:
            with open(os.path.join(self.block_dir, block_files), 'rb') as infile:
                self.saved_pulse_blocks = pickle.load(infile)
        except:
            self.saved_pulse_blocks = OrderedDict()
            self.log.error('Failed to deserialize ensemble dict "{0}" from "{1}".'
                           ''.format(block_files, self.block_dir))
        self.sigBlockDictUpdated.emit(self.saved_pulse_blocks)
        return

    def _save_blocks_to_file(self):
        """ Saves the saved_pulse_block dict to file """
        try:
            with open(os.path.join(self.block_dir, 'block_dict.blk.tmp'), 'wb') as outfile:
                pickle.dump(self.saved_pulse_blocks, outfile)
        except:
            self.log.error('Failed to serialize ensemble dict in "{0}".'
                           ''.format(os.path.join(self.block_dir, 'block_dict.blk.tmp')))
            return
        # remove old file and rename temp file
        try:
            os.rename(os.path.join(self.block_dir, 'block_dict.blk.tmp'),
                      os.path.join(self.block_dir, 'block_dict.blk'))
        except WindowsError:
            os.remove(os.path.join(self.block_dir, 'block_dict.blk'))
            os.rename(os.path.join(self.block_dir, 'block_dict.blk.tmp'),
                      os.path.join(self.block_dir, 'block_dict.blk'))
        return

    def save_ensemble(self, name, ensemble):
        """ Saves a PulseBlockEnsemble with name name to file.

        @param str name: name of the ensemble, which will be serialized.
        @param obj ensemble: a PulseBlockEnsemble object
        """
        # TODO: Overwrite handling
        ensemble.name = name
        self.current_ensemble = ensemble
        self.saved_pulse_block_ensembles[name] = ensemble
        self._save_ensembles_to_file()
        self.sigEnsembleDictUpdated.emit(self.saved_pulse_block_ensembles)
        return

    def load_ensemble(self, name):
        """

        @param name:
        @return:
        """
        if name not in self.saved_pulse_block_ensembles:
            self.log.error('PulseBlockEnsemble "{0}" could not be found in saved pulse block '
                           'ensembles. Load failed.'.format(name))
            return
        ensemble = self.saved_pulse_block_ensembles[name]
        # set generator settings if found in ensemble metadata
        if ensemble.sample_rate is not None:
            self.sample_rate = ensemble.sample_rate
        if ensemble.amplitude_dict is not None:
            self.amplitude_dict = ensemble.amplitude_dict
        if ensemble.activation_config is not None:
            self.activation_config = ensemble.activation_config
        if ensemble.laser_channel is not None:
            self.laser_channel = ensemble.laser_channel
        self.sigSettingsUpdated.emit(self.activation_config, self.laser_channel, self.sample_rate,
                                     self.amplitude_dict, self.waveform_format)
        self.current_ensemble = ensemble
        self.sigCurrentEnsembleUpdated.emit(ensemble)
        return

    def delete_ensemble(self, name):
        """ Remove the ensemble with 'name' from the ensemble list and HDD. """
        if name in list(self.saved_pulse_block_ensembles):
            del(self.saved_pulse_block_ensembles[name])
            if hasattr(self.current_ensemble, 'name'):
                if self.current_ensemble.name == name:
                    self.current_ensemble = None
                    self.sigCurrentEnsembleUpdated.emit(self.current_ensemble)
            self._save_ensembles_to_file()
            self.sigEnsembleDictUpdated.emit(self.saved_pulse_block_ensembles)
        else:
            self.log.warning('PulseBlockEnsemble object with name "{0}" not found in saved '
                             'ensembles.\nTherefore nothing is removed.'.format(name))
        return

    def _get_ensembles_from_file(self):
        """ Update the saved_pulse_block_ensembles dict from file """
        ensemble_files = [f for f in os.listdir(self.ensemble_dir) if 'ensemble_dict.ens' in f]
        if len(ensemble_files) == 0:
            self.log.info('No serialized ensembles dict was found in {0}.'
                          ''.format(self.ensemble_dir))
            self.saved_pulse_block_ensembles = OrderedDict()
            self.sigEnsembleDictUpdated.emit(self.saved_pulse_block_ensembles)
            return
        # raise error if more than one file is present
        if len(ensemble_files) > 1:
            self.log.error('More than one serialized ensemble dict was found in {0}.\n'
                           'Using {1}.'.format(self.ensemble_dir, ensemble_files[-1]))
        ensemble_files = ensemble_files[-1]
        try:
            with open(os.path.join(self.ensemble_dir, ensemble_files), 'rb') as infile:
                self.saved_pulse_block_ensembles = pickle.load(infile)
        except:
            self.saved_pulse_block_ensembles = OrderedDict()
            self.log.error('Failed to deserialize ensemble dict "{0}" from "{1}".'
                           ''.format(ensemble_files, self.ensemble_dir))
        self.sigEnsembleDictUpdated.emit(self.saved_pulse_block_ensembles)
        return

    def _save_ensembles_to_file(self):
        """ Saves the saved_pulse_block_ensembles dict to file """
        try:
            with open(os.path.join(self.ensemble_dir, 'ensemble_dict.ens.tmp'), 'wb') as outfile:
                pickle.dump(self.saved_pulse_block_ensembles, outfile)
        except:
            self.log.error('Failed to serialize ensemble dict in "{0}".'
                           ''.format(os.path.join(self.ensemble_dir, 'ensemble_dict.ens.tmp')))
            return
        # remove old file and rename temp file
        try:
            os.rename(os.path.join(self.ensemble_dir, 'ensemble_dict.ens.tmp'),
                      os.path.join(self.ensemble_dir, 'ensemble_dict.ens'))
        except WindowsError:
            os.remove(os.path.join(self.ensemble_dir, 'ensemble_dict.ens'))
            os.rename(os.path.join(self.ensemble_dir, 'ensemble_dict.ens.tmp'),
                      os.path.join(self.ensemble_dir, 'ensemble_dict.ens'))
        return

    def save_sequence(self, name, sequence):
        """ Serialize the PulseSequence object with name 'name' to file.

        @param str name: name of the sequence object.
        @param object sequence: a PulseSequence object, which is going to be
                                serialized to file.

        @return: str: name of the serialized object, if needed.
        """
        # TODO: Overwrite handling
        sequence.name = name
        self.current_sequence = sequence
        self.saved_pulse_sequences[name] = sequence
        self._save_sequences_to_file()
        self.sigSequenceDictUpdated.emit(self.saved_pulse_sequences)
        return

    def load_sequence(self, name):
        """

        @param name:
        @return:
        """
        if name not in self.saved_pulse_sequences:
            self.log.error('PulseSequence "{0}" could not be found in saved pulse sequences. '
                           'Load failed.'.format(name))
            return
        sequence = self.saved_pulse_sequences[name]
        # set generator settings if found in seqeunce metadata
        if sequence.sample_rate is not None:
            self.sample_rate = sequence.sample_rate
        if sequence.amplitude_dict is not None:
            self.amplitude_dict = sequence.amplitude_dict
        if sequence.activation_config is not None:
            self.activation_config = sequence.activation_config
        if sequence.laser_channel is not None:
            self.laser_channel = sequence.laser_channel
        self.sigSettingsUpdated.emit(self.activation_config, self.laser_channel, self.sample_rate,
                                     self.amplitude_dict, self.waveform_format)
        self.current_sequence = sequence
        self.sigCurrentSequenceUpdated.emit(sequence)
        return

    def delete_sequence(self, name):
        """ Remove the sequence "name" from the sequence list and HDD.

        @param str name: name of the sequence object, which should be deleted.
        """
        if name in list(self.saved_pulse_sequences):
            del(self.saved_pulse_sequences[name])
            if hasattr(self.current_sequence, 'name'):
                if self.current_sequence.name == name:
                    self.current_sequence = None
                    self.sigCurrentSequenceUpdated.emit(self.current_sequence)
            self._save_sequences_to_file()
            self.sigSequenceDictUpdated.emit(self.saved_pulse_sequences)
        else:
            self.log.warning('PulseBlockEnsemble object with name "{0}" not found in saved '
                             'ensembles.\nTherefore nothing is removed.'.format(name))
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

    def _get_sequences_from_file(self):
        """ Update the saved_pulse_sequences dict from file """
        sequence_files = [f for f in os.listdir(self.sequence_dir) if 'sequence_dict.sequ' in f]
        if len(sequence_files) == 0:
            self.log.info('No serialized sequence dict was found in {0}.'.format(self.sequence_dir))
            self.saved_pulse_sequences = OrderedDict()
            self.sigSequenceDictUpdated.emit(self.saved_pulse_sequences)
            return
        # raise error if more than one file is present
        if len(sequence_files) > 1:
            self.log.error('More than one serialized sequence dict was found in {0}.\n'
                           'Using {1}.'.format(self.sequence_dir, sequence_files[-1]))
        sequence_files = sequence_files[-1]
        try:
            with open(os.path.join(self.sequence_dir, sequence_files), 'rb') as infile:
                self.saved_pulse_sequences = pickle.load(infile)
        except:
            self.saved_pulse_sequences = OrderedDict()
            self.log.error('Failed to deserialize sequence dict "{0}" from "{1}".'
                           ''.format(sequence_files, self.sequence_dir))
        self.sigSequenceDictUpdated.emit(self.saved_pulse_sequences)
        return

    def _save_sequences_to_file(self):
        """ Saves the saved_pulse_sequences dict to file """
        try:
            with open(os.path.join(self.sequence_dir, 'sequence_dict.sequ.tmp'), 'wb') as outfile:
                pickle.dump(self.saved_pulse_sequences, outfile)
        except:
            self.log.error('Failed to serialize ensemble dict in "{0}".'
                           ''.format(os.path.join(self.sequence_dir, 'sequence_dict.sequ.tmp')))
            return
        # remove old file and rename temp file
        try:
            os.rename(os.path.join(self.sequence_dir, 'sequence_dict.sequ.tmp'),
                      os.path.join(self.sequence_dir, 'sequence_dict.sequ'))
        except WindowsError:
            os.remove(os.path.join(self.sequence_dir, 'sequence_dict.sequ'))
            os.rename(os.path.join(self.sequence_dir, 'sequence_dict.sequ.tmp'),
                      os.path.join(self.sequence_dir, 'sequence_dict.sequ'))
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
        # dict containing the bins where the digital channels are rising (one arr for each channel)
        digital_rising_bins = dict()
        # memorize the channel state of the previous element
        tmp_digital_high = dict()
        for chnl in ensemble.digital_channels:
            digital_rising_bins[chnl] = list()
            # memorize the channel state of the previous element
            tmp_digital_high[chnl] = False
        # number of elements including repetitions and the length of each element in bins
        total_elements = 0
        elements_length_bins = np.array([], dtype=int)

        for block, reps in ensemble.block_list:
            # Total number of elements in the current block including all repetitions
            unrolled_elements = (reps+1) * len(block.element_list)
            # Add this number to the total number of unrolled elements in the ensemble
            total_elements += unrolled_elements
            # Temporary array to hold the length for each element (including reps) in bins
            tmp_length_bins = np.zeros(unrolled_elements, dtype=int)

            # Iterate over all repetitions of the current block
            unrolled_element_index = 0
            for rep_no in range(reps+1):
                # Iterate over the Block_Elements inside the current block
                for elem_index, block_element in enumerate(block.element_list):
                    # save bin position if a transition from low to high has occured in a digital
                    # channel
                    for chnl in block_element.digital_high:
                        if tmp_digital_high[chnl] != block_element.digital_high[chnl]:
                            if not tmp_digital_high[chnl] and block_element.digital_high[chnl]:
                                digital_rising_bins[chnl].append(current_start_bin)
                            tmp_digital_high[chnl] = block_element.digital_high[chnl]

                    # Get length and increment for this element
                    init_length_s = block_element.init_length_s
                    increment_s = block_element.increment_s
                    # element length of the current element with current repetition count in sec
                    element_length_s = init_length_s + (rep_no * increment_s)
                    # ideal end time for the sequence up until this point in sec
                    current_end_time += element_length_s
                    # Nearest possible match including the discretization in bins
                    current_end_bin = int(np.rint(current_end_time * self.sample_rate))
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

        # convert digital rising indices to numpy.ndarrays
        for chnl in digital_rising_bins:
            digital_rising_bins[chnl] = np.array(digital_rising_bins[chnl], dtype=int)

        return number_of_samples, total_elements, elements_length_bins, digital_rising_bins

    def _analyze_pulse_sequence(self, sequence):
        """
        This helper method runs through each step of a PulseSequence object and extracts
        important information about the Sequence that can be created out of this object.
        Especially the discretization due to the set self.sample_rate is taken into account.
        The positions in time (as integer time bins) of the PulseBlockElement transitions are
        determined here (all the "rounding-to-best-match-value").
        Additional information like the total number of samples, total number of PulseBlockElements
        and the timebins for digital channel low-to-high transitions get returned as well.

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
        # TODO: Implement _analyze_pulse_sequence method.
        pass

    def sample_pulse_block_ensemble(self, ensemble_name, offset_bin=0, name_tag=None):
        """ General sampling of a PulseBlockEnsemble object, which serves as the construction plan.

        @param str ensemble_name: Name, which should correlate with the name of on of the displayed
                                  ensembles.
        @param int offset_bin: If many pulse ensembles are samples sequentially, then the
                               offset_bin of the previous sampling can be passed to maintain
                               rotating frame across pulse_block_ensembles
        @param str name_tag: a name tag, which is used to keep the sampled files together, which
                             where sampled from the same PulseBlockEnsemble object but where
                             different offset_bins were used.

        @return tuple: of length 4 with
                       (analog_samples, digital_samples, offset_bin, created_waveforms).
                        analog_samples:
                            numpy arrays containing the sampled voltages
                        digital_samples:
                            numpy arrays containing the sampled logic levels
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
        # lock module if it's not already locked (sequence sampling in progress)
        if self.module_state() == 'idle':
            self.module_state.lock()
            sequence_sampling_in_progress = False
        else:
            sequence_sampling_in_progress = True

        # determine if chunkwise writing is enabled (the overhead byte size is set)
        chunkwise = self.sampling_overhead_bytes is not None

        # get ensemble
        ensemble = self.saved_pulse_block_ensembles.get(ensemble_name)
        if ensemble is None:
            if not sequence_sampling_in_progress:
                self.module_state.unlock()
            self.sigSampleEnsembleComplete.emit('', dict(), dict())
            return dict(), dict(), -1, []

        # Check if number of channels in PulseBlockEnsemble matches the hardware settings
        ana_channels = ensemble.analog_channels
        dig_channels = ensemble.digital_channels
        if self.digital_channels != len(dig_channels) or self.analog_channels != len(ana_channels):
            self.log.error('Sampling of PulseBlockEnsemble "{0}" failed!\nMismatch in number of '
                           'analog and digital channels between hardware ({1}, {2}) and '
                           'PulseBlockEnsemble ({3}, {4}).'
                           ''.format(ensemble_name, self.analog_channels, self.digital_channels,
                                     len(ana_channels), len(dig_channels)))
            if not sequence_sampling_in_progress:
                self.module_state.unlock()
            self.sigSampleEnsembleComplete.emit('', dict(), dict())
            return dict(), dict(), -1, []
        elif ana_channels.union(dig_channels) != self.activation_config[1]:
            self.log.error('Sampling of PulseBlockEnsemble "{0}" failed!\nMismatch in activation '
                           'config in logic ({1}) and active channels in PulseBlockEnsemble ({2}).'
                           ''.format(ensemble_name, self.activation_config[1],
                                     ana_channels.union(dig_channels)))
            if not sequence_sampling_in_progress:
                self.module_state.unlock()
            self.sigSampleEnsembleComplete.emit('', dict(), dict())
            return dict(), dict(), -1, []

        # Set the filename (excluding the channel naming suffix, i.e. '_ch1')
        if name_tag is None:
            filename = ensemble_name
        else:
            filename = name_tag

        # check for old waveforms associated with the ensemble and delete them from pulse generator.
        uploaded_waveforms = self._pulse_generator.get_waveform_names()
        wfm_regex = re.compile(r'\b' + filename + r'_ch\d+$')
        for wfm_name in uploaded_waveforms:
            if wfm_regex.match(wfm_name):
                self._pulse_generator.delete_waveform(wfm_name)
                self.log.debug('Old waveform deleted from pulse generator: "{0}".'.format(wfm_name))

        start_time = time.time()

        # get important parameters from the ensemble and save some to the ensemble objects
        # sampling_information container.
        number_of_samples, number_of_elements, length_elements_bins, digital_rising_bins = self._analyze_block_ensemble(ensemble)
        ensemble.sampling_information = dict()
        ensemble.sampling_information['length_bins'] = number_of_samples
        ensemble.sampling_information['length_elements_bins'] = length_elements_bins
        ensemble.sampling_information['number_of_elements'] = number_of_elements
        ensemble.sampling_information['digital_rising_bins'] = digital_rising_bins
        ensemble.sampling_information['sample_rate'] = self.sample_rate
        ensemble.sampling_information['activation_config'] = self.activation_config[1]
        ensemble.sampling_information['analog_pp_amplitude'] = self.analog_pp_amplitude
        self.save_ensemble(ensemble_name, ensemble)

        # The time bin offset for each element to be sampled to preserve rotating frame.
        if chunkwise:
            # Flags and counter for chunkwise writing
            is_first_chunk = True
            is_last_chunk = False
        else:
            is_first_chunk = True
            is_last_chunk = True
            # Allocate huge sample arrays if chunkwise writing is disabled.
            analog_samples = dict()
            digital_samples = dict()
            for chnl in ana_channels:
                analog_samples[chnl] = np.empty(number_of_samples, dtype='float32')
            for chnl in dig_channels:
                digital_samples[chnl] = np.empty(number_of_samples, dtype=bool)
            # Starting index for the sample array entrys
            entry_ind = 0

        element_count = 0
        # Iterate over all blocks within the PulseBlockEnsemble object
        for block, reps in ensemble.block_list:
            # Iterate over all repertitions of the current block
            for rep_no in range(reps+1):
                # Iterate over the Block_Elements inside the current block
                for block_element in block.element_list:
                    digital_high = block_element.digital_high
                    pulse_function = block_element.pulse_function
                    element_length_bins = length_elements_bins[element_count]
                    element_count += 1

                    # create floating point time array for the current element inside rotating frame
                    time_arr = (offset_bin + np.arange(element_length_bins, dtype='float64')) / self.sample_rate

                    if chunkwise:
                        # determine it the current element is the last one to be sampled.
                        # Toggle the is_last_chunk flag accordingly.
                        if element_count == number_of_elements:
                            is_last_chunk = True

                        # allocate temporary sample dictionaries to contain the current elements.
                        analog_samples = dict()
                        digital_samples = dict()

                        # actually fill the sample dictionaries with arrays.
                        for chnl in digital_high:
                            digital_samples[chnl] = np.full(element_length_bins, digital_high[chnl],
                                                            dtype=bool)
                        for chnl in pulse_function:
                            analog_samples[chnl] = np.float32(pulse_function[chnl].get_samples(time_arr)/self.analog_pp_amplitude[chnl])
                        # write temporary sample array to file
                            written_samples, wfm_list = self._pulse_generator.write_waveform(
                                name=filename,
                                analog_samples=analog_samples,
                                digital_samples=digital_samples,
                                is_first_chunk=is_first_chunk,
                                is_last_chunk=is_last_chunk)
                        # check if write process was successful
                        if written_samples != element_length_bins:
                            self.log.error('Sampling of block "{0}" in ensemble "{1}" failed. Write'
                                           ' to device was unsuccessful.'.format(block.name,
                                                                                 ensemble.name))
                            if not sequence_sampling_in_progress:
                                self.module_state.unlock()
                            self.sigSampleEnsembleComplete.emit(filename, dict(), dict())
                            return dict(), dict(), -1, []
                        # set flag to FALSE after first write
                        is_first_chunk = False
                    else:
                        # if the ensemble should be sampled as a whole (chunkwise = False) fill the
                        # entries in the huge sample arrays
                        for chnl in digital_high:
                            digital_samples[chnl][entry_ind:entry_ind+element_length_bins] = np.full(element_length_bins, digital_high[chnl], dtype=bool)
                        for chnl in pulse_function:
                            analog_samples[chnl][entry_ind:entry_ind+element_length_bins] = np.float32(pulse_function[chnl].get_samples(time_arr)/self.analog_pp_amplitude[chnl])

                        # increment the index offset of the overall sample array for the next
                        # element
                        entry_ind += element_length_bins

                    # if the rotating frame should be preserved (default) increment the offset
                    # counter for the time array.
                    if ensemble.rotating_frame:
                        offset_bin += element_length_bins

        if chunkwise:
            # return a status message with the time needed for sampling and writing the ensemble
            # chunkwise.
            self.log.info('Time needed for sampling and writing to device chunkwise: {0} sec'
                          ''.format(int(np.rint(time.time()-start_time))))
            if not sequence_sampling_in_progress:
                self.module_state.unlock()
            self.sigSampleEnsembleComplete.emit(filename, dict(), dict())
            return dict(), dict(), offset_bin, wfm_list
        else:
            # If the sampling should not be chunkwise call the write_waveform method only once.
            written_samples, wfm_list = self._pulse_generator.write_waveform(
                name=filename,
                analog_samples=analog_samples,
                digital_samples=digital_samples,
                is_first_chunk=is_first_chunk,
                is_last_chunk=is_last_chunk)
            # check if write process was successful
            if written_samples != number_of_samples:
                self.log.error('Sampling of ensemble "{0}" failed. Write to device was '
                               'unsuccessful.'.format(ensemble.name))
                if not sequence_sampling_in_progress:
                    self.module_state.unlock()
                self.sigSampleEnsembleComplete.emit(filename, dict(), dict())
                return dict(), dict(), -1, []
            # return a status message with the time needed for sampling and writing the ensemble.
            self.log.info('Time needed for sampling and writing PulseBlockEnsemble to device as a '
                          'whole: {0} sec'.format(int(np.rint(time.time()-start_time))))

            if not sequence_sampling_in_progress:
                self.module_state.unlock()
            self.sigSampleEnsembleComplete.emit(filename, dict(), dict())
            return analog_samples, digital_samples, offset_bin, wfm_list

    def sample_pulse_sequence(self, sequence_name):
        """ Samples the PulseSequence object, which serves as the construction plan.

        @param str ensemble_name: Name, which should correlate with the name of on of the displayed
                                  ensembles.

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
        # lock module
        if self.module_state() == 'idle':
            self.module_state.lock()
        else:
            self.log.error('Cannot sample sequence "{0}" because the sequence generator logic is '
                           'still busy (locked).\nFunction call ignored.'.format(sequence_name))
            self.sigSampleSequenceComplete.emit(sequence_name, [])
            return []

        # delete already written sequences on the device memory that have the same name
        if sequence_name in self._pulse_generator.get_sequence_names():
            self._pulse_generator.delete_sequence(sequence_name)
            self.log.debug('Old sequence deleted from pulse generator: "{0}".'
                           ''.format(sequence_name))

        start_time = time.time()

        # get ensemble
        sequence = self.saved_pulse_sequences.get(sequence_name)
        if sequence is None:
            self.log.error('No sequence by the name "{0}" found in saved sequences. '
                           'Sequence sampling failed.'.format(sequence_name))
            self.module_state.unlock()
            self.sigSampleSequenceComplete.emit(sequence_name, [])
            return []

        # Produce a list of created waveforms
        created_waveforms_list = list()

        # Create a list in the process with each element holding the created wavfeorm names as a
        # tuple and the corresponding sequence parameters as defined in the PulseSequence object
        # Example: [(('waveform1', 'waveform2'), seq_param_dict1),
        #           (('waveform3', 'waveform4'), seq_param_dict2)]
        sequence_param_dict_list = list()

        # if all the Pulse_Block_Ensembles should be in the rotating frame, then each ensemble
        # will be created in general with a different offset_bin. Therefore, in order to keep track
        # of the sampled Pulse_Block_Ensembles one has to introduce a running number as an
        # additional name tag, so keep the sampled files separate.
        if sequence.rotating_frame:
            offset_bin = 0  # that will be used for phase preservation
            for ensemble_index, (ensemble, seq_param) in enumerate(sequence.ensemble_param_list):
                # to make something like 001
                name_tag = sequence_name + '_' + str(ensemble_index).zfill(3)

                dummy1, \
                dummy2, \
                offset_bin_return, \
                created_waveforms = self.sample_pulse_block_ensemble(ensemble.name,
                                                                     offset_bin=offset_bin,
                                                                     name_tag=name_tag)

                if len(created_waveforms) == 0:
                    self.log.error('Sampling of PulseBlockEnsemble "{0}" failed during sampling of '
                                   'PulseSequence "{1}".\nFailed to create waveforms on device.'
                                   ''.format(ensemble.name, sequence_name))
                    self.module_state.unlock()
                    self.sigSampleSequenceComplete.emit(sequence_name, [])
                    return []

                created_waveforms_list.extend(created_waveforms)

                sequence_param_dict_list.append((tuple(created_waveforms), seq_param))

                # for the next run, the returned offset_bin will serve as starting point for
                # phase preserving.
                offset_bin = offset_bin_return
        else:
            # if phase prevervation between the sequence entries is not needed, then only the
            # different ensembles will be sampled, since the offset_bin does not matter for them.

            # Use a list to keep track of already sampled ensembles
            sampled_ensembles = list()

            for ensemble, seq_param in sequence.ensemble_param_list:
                if ensemble.name not in sampled_ensembles:
                    dummy1, \
                    dummy2, \
                    dummy3, \
                    created_waveforms = self.sample_pulse_block_ensemble(ensemble.name)
                    sampled_ensembles.append(ensemble.name)

                if len(created_waveforms) == 0:
                    self.log.error('Sampling of PulseBlockEnsemble "{0}" failed during sampling of '
                                   'PulseSequence "{1}".\nFailed to create waveforms on device.'
                                   ''.format(ensemble.name, sequence_name))
                    self.module_state.unlock()
                    self.sigSampleSequenceComplete.emit(sequence_name, [])
                    return []

                created_waveforms_list.extend(created_waveforms)

                sequence_param_dict_list.append((tuple(created_waveforms), seq_param))

        # get important parameters from the sequence and save some to the sequence object
        # TODO: Get information from _analyze_pulse_sequence as soon as it's implemented.
        # self._analyze_pulse_sequence(sequence_obj)
        sequence.sampling_information = dict()
        sequence.sampling_information['sample_rate'] = self.sample_rate
        sequence.sampling_information['activation_config'] = self.activation_config
        sequence.sampling_information['amplitude_dict'] = self.amplitude_dict
        self.save_sequence(sequence_name, sequence)

        # pass the whole information to the sequence creation method:
        self._pulse_generator.write_sequence(sequence_name, sequence_param_dict_list)
        self.log.info('Time needed for sampling and writing Pulse Sequence to device: {0} sec.'
                      ''.format(int(np.rint(time.time() - start_time))))
        # unlock module
        self.module_state.unlock()
        self.sigSampleSequenceComplete.emit(sequence_name, sequence_param_dict_list)
        return sequence_param_dict_list

    #---------------------------------------------------------------------------
    #                    END sequence/block sampling
    #---------------------------------------------------------------------------
