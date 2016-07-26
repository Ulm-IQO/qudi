# -*- coding: utf-8 -*-

"""
This file contains the QuDi sequence generator logic for general sequence structure.

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

import numpy as np
import pickle
import os
import time
from pyqtgraph.Qt import QtCore
from collections import OrderedDict
import inspect
import importlib

from logic.pulse_objects import Pulse_Block_Element, Pulse_Block, Pulse_Block_Ensemble, Pulse_Sequence
from logic.generic_logic import GenericLogic
from logic.sampling_functions import SamplingFunctions
from logic.samples_write_methods import SamplesWriteMethods

class SequenceGeneratorLogic(GenericLogic, SamplingFunctions, SamplesWriteMethods):
    """unstable: Nikolas Tomek
    This is the Logic class for the pulse (sequence) generation.

    The basis communication with the GUI should be done as follows:
    The logic holds all the created objects in its internal lists. The GUI is
    able to view this list and get the element of this list.

    How the logic will contruct its objects according to configuration dicts.
    The configuration dicts contain essentially, which parameters of either the
    Pulse_Block_Element objects or the Pulse_Block objects can be changed and
    set via the GUI.

    In the end the information transfer happend through lists (read by the GUI)
    and dicts (set by the GUI). The logic sets(creats) the objects in the list
    and read the dict, which tell it which parameters to expect from the GUI.
    """

    _modclass = 'sequencegeneratorlogic'
    _modtype = 'logic'

    ## declare connectors
    _out = {'sequencegenerator': 'SequenceGeneratorLogic'}


    # define signals
    signal_block_list_updated = QtCore.Signal()
    signal_ensemble_list_updated = QtCore.Signal()
    signal_sequence_list_updated = QtCore.Signal()
    sigLoadedAssetUpdated = QtCore.Signal()
    sigSampleEnsembleComplete = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions

        state_actions = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{}: {}'.format(key,config[key]))

        # Get all the attributes from the SamplingFunctions module:
        SamplingFunctions.__init__(self)
        # Get all the attributes from the SamplesWriteMethods module:
        SamplesWriteMethods.__init__(self)

        # here the currently shown data objects of the editors should be stored
        self.current_block = None
        self.current_ensemble = None
        self.current_sequence = None

        # The string names of the created Pulse_Block objects are saved here:
        self.saved_pulse_blocks = []
        # The string names of the created Pulse_Block_Ensemble objects are saved here:
        self.saved_pulse_block_ensembles = []
        # The string names of the created Sequence objects are saved here:
        self.saved_pulse_sequences = []

        if 'pulsed_file_dir' in config.keys():
            self.pulsed_file_dir = config['pulsed_file_dir']
            if not os.path.exists(self.pulsed_file_dir):
                homedir = self.get_home_dir()
                self.pulsed_file_dir = os.path.join(homedir, 'pulsed_files')
                self.log.warning('The directort defined in "pulsed_file_dir" '
                        'in the config for SequenceGeneratorLogic class does '
                        'not exist!\n'
                        'The default home directory\n{0}\n will be '
                        'taken instead.'.format(self.pulsed_file_dir))
        else:
            homedir = self.get_home_dir()
            self.pulsed_file_dir = os.path.join(homedir, 'pulsed_files')
            self.log.warning('No directory with the attribute '
                    '"pulsed_file_dir" is defined for the '
                    'SequenceGeneratorLogic!\n'
                    'The default home directory\n{0}\n will be taken '
                    'instead.'.format(self.pulsed_file_dir))


        self.block_dir = self._get_dir_for_name('pulse_block_objects')
        self.ensemble_dir = self._get_dir_for_name('pulse_ensemble_objects')
        self.sequence_dir = self._get_dir_for_name('sequence_objects')
        self.waveform_dir = self._get_dir_for_name('sampled_hardware_files')
        self.temp_dir = self._get_dir_for_name('temporary_files')

        # Information on used channel configuration for sequence generation
        # IMPORTANT: THIS CONFIG DOES NOT REPRESENT THE ACTUAL SETTINGS ON THE HARDWARE
        self.analog_channels = 2
        self.digital_channels = 4
        self.activation_config = ['a_ch1', 'd_ch1', 'd_ch2', 'a_ch2', 'd_ch3', 'd_ch4']
        self.laser_channel = 'd_ch1'
        self.amplitude_list = OrderedDict()
        self.amplitude_list['a_ch1'] = 0.5
        self.amplitude_list['a_ch2'] = 0.5
        self.amplitude_list['a_ch3'] = 0.5
        self.amplitude_list['a_ch4'] = 0.5
        self.sample_rate = 25e9
        # The file format for the sampled hardware-compatible waveforms and sequences
        self.waveform_format = 'wfmx' # can be 'wfmx', 'wfm' or 'fpga'
        self.sequence_format = 'seqx' # can be 'seqx' or 'seq'

    def activation(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """
        self.refresh_block_list()
        self.refresh_ensemble_list()
        self.refresh_sequence_list()

        self._attach_predefined_methods()

        if 'activation_config' in self._statusVariables:
            self.set_activation_config(self._statusVariables['activation_config'])
        if 'laser_channel' in self._statusVariables:
            self.set_laser_channel(self._statusVariables['laser_channel'])
        if 'amplitude_list' in self._statusVariables:
            self.set_amplitude_list(self._statusVariables['amplitude_list'])
        if 'sample_rate' in self._statusVariables:
            self.set_sample_rate(self._statusVariables['sample_rate'])
        if 'waveform_format' in self._statusVariables:
            self.waveform_format = self._statusVariables['waveform_format']
        if 'sequence_format' in self._statusVariables:
            self.sequence_format = self._statusVariables['sequence_format']

    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        self._statusVariables['activation_config'] = self.activation_config
        self._statusVariables['laser_channel'] = self.laser_channel
        self._statusVariables['amplitude_list'] = self.amplitude_list
        self._statusVariables['sample_rate'] = self.sample_rate
        self._statusVariables['waveform_format'] = self.waveform_format
        self._statusVariables['sequence_format'] = self.sequence_format

    def _attach_predefined_methods(self):
        """ Retrieve in the folder all files for predefined methods and attach
            their methods to the

        @return:
        """
        self.predefined_method_list = []
        filename_list = []
        # The assumption is that in the directory predefined_methods, there are
        # *.py files, which contain only methods!
        path = os.path.join(self.get_main_dir(), 'logic', 'predefined_methods')
        for entry in os.listdir(path):
            if os.path.isfile(os.path.join(path, entry)) and entry.endswith('.py'):
                filename_list.append(entry[:-3])

        for filename in filename_list:
            mod = importlib.import_module('logic.predefined_methods.{}'.format(filename))

            for method in dir(mod):
                try:
                    # Check for callable function or method:
                    ref = getattr(mod, method)
                    if callable(ref) and (inspect.ismethod(ref) or inspect.isfunction(ref)):
                        # Bind the method as an attribute to the Class
                        setattr(SequenceGeneratorLogic, method, getattr(mod, method))

                        self.predefined_method_list.append(eval('self.'+method))
                except:
                    self.log.error('It was not possible to import element '
                            '{0} from {1} into SequenceGenerationLogic.'
                            ''.format(
                                method,filename))

    def _get_dir_for_name(self, name):
        """ Get the path to the pulsed sub-directory 'name'.

        @param str name: name of the folder
        @return: str, absolute path to the directory with folder 'name'.
        """

        path = os.path.join(self.pulsed_file_dir, name)
        if not os.path.exists(path):
            os.makedirs(os.path.abspath(path))

        return os.path.abspath(path)

    def set_activation_config(self, activation_config):
        """
        Sets the currently active channel activation config in this logic module
        and calculates related parameters (like number of d and a channels).
        This method will NOT set the active channels in the hardware.

        @param activation_config: The activation_config dict to be set
        @return: int, error code (0:OK, -1:error)
        """
        # check input for default action and errors
        self.activation_config = activation_config
        # calculate derived parameters
        self.analog_channels = len([chnl for chnl in activation_config if 'a_ch' in chnl])
        self.digital_channels = len([chnl for chnl in activation_config if 'd_ch' in chnl])
        # check if the currently chosen laser channel is part of the config and adjust if this
        # is not the case. Choose first digital channel in that case.
        if self.laser_channel not in activation_config:
            d_ch_present = False
            for channel in activation_config:
                if 'd_ch' in channel:
                    self.set_laser_channel(channel)
                    d_ch_present = True
                    break
            if not d_ch_present:
                self.set_laser_channel(activation_config[0])
                self.log.warning('No digital channel present in sequence '
                        'generator activation config.')
        return 0

    def set_sample_rate(self, sample_rate):
        """
        Sets the sample rate for the sequence generation

        @param sample_rate: float, the sampling frequency in Hz
        @return: float, the actually set sampling frequency in Hz
        """
        self.sample_rate = sample_rate
        return sample_rate

    def set_amplitude_list(self, amplitude_list):
        """
        Sets the amplitude list for the analogue channels

        @param amplitude_list:  dict, a dictionary containing the peak-to-peak
                                amplitude for each analogue channel in V
                                Example: {'a_ch1': 0.5, 'a_ch2': 0.25}
        @return: dict, the actually set amplitude list
        """
        self.amplitude_list = amplitude_list
        return amplitude_list

    def set_laser_channel(self, laser_channel):
        """
        Sets the string descriptor for the laser channel

        @param laser_channel: string, a string descriptor for the laser channel, i.e. 'd_ch1'
        @return: string, the actually set laser channel
        """
        self.laser_channel = laser_channel
        return laser_channel

# -----------------------------------------------------------------------------
#                    BEGIN sequence/block generation
# -----------------------------------------------------------------------------
    def get_saved_asset(self, name):
        """
        Returns the data object for a saved Ensemble/Sequence with name "name". Searches in the
        saved assets for a Sequence object first. If no Sequence by that name could be found search
        for Ensembles instead. If neither could be found return None.
        @param name: Name of the Sequence/Ensemble
        @return: Pulse_Sequence | Pulse_Block_Ensemble | None
        """
        if name in self.saved_pulse_sequences:
            asset_obj = self.get_pulse_sequence(name)
        elif name in self.saved_pulse_block_ensembles:
            asset_obj = self.get_pulse_block_ensemble(name)
        else:
            asset_obj = None
            self.log.warning('No Pulse_Sequence or Pulse_Block_Ensemble by '
                    'the name "{0}" could be found in '
                    'pulsed_files_directory. Returning None.'.format(name))
        return asset_obj


    def save_block(self, name, block):
        """ Serialize a Pulse_Block object to a *.blk file.

        @param name: string, name of the block to save
        @param block: Pulse_Block object which will be serialized
        """

        # TODO: Overwrite handling
        block.name = name
        with open(os.path.join(self.block_dir, name + '.blk'), 'wb') as outfile:
            pickle.dump(block, outfile)
        self.refresh_block_list()
        self.current_block = block
        self.log.debug('Pulse_Block object "{0}" serialized to harddisk in:\n'
                    '{1}'.format(name, self.block_dir))
        return

    def get_pulse_block(self, name, set_as_current_block=False):
        """ Deserialize a *.blk file into a Pulse_Block object.

        @param name: string, name of the *.blk file.
        @param set_as_current_ensemble: bool, set the retained Pulse_Block
               object as the current ensemble.

        @return: Pulse_Block object which belongs to the given name.
        """
        if name in self.saved_pulse_blocks:
            with open(os.path.join(self.block_dir, name + '.blk'), 'rb') as infile:
                block = pickle.load(infile)
        else:
            self.log.warning('The Pulse_Block object with name "{0}" could '
                    'not be found and serialized in:\n'
                    '{1}'.format(name, self.block_dir))
            block = None

        if set_as_current_block:
            self.current_block = block
        return block

    def delete_block(self, name):
        """ Remove the serialized object "name" from the block list and HDD.

        @param name: string, name of the Pulse_Block object to be removed.
        """

        if name in self.saved_pulse_blocks:
            os.remove(os.path.join(self.block_dir, name + '.blk'))

            # if a block is removed, then check whether the current_block is
            # actually the removed block and if so set current_block to None
            if hasattr(self.current_block, 'name'):
                if self.current_block.name == name:
                    self.current_block = None
            self.refresh_block_list()
        else:
            self.log.warning('Pulse_Block object with name "{0}" not found '
                    'in\n{1}\nTherefore nothing is '
                    'removed.'.format(name, self.block_dir))

    def refresh_block_list(self):
        """ Refresh the list of available (saved) blocks """

        block_files = [f for f in os.listdir(self.block_dir) if '.blk' in f]
        blocks = []
        for filename in block_files:
            blocks.append(filename[:-4])
        blocks.sort()
        self.saved_pulse_blocks = blocks
        self.signal_block_list_updated.emit()

    def save_ensemble(self, name, ensemble):
        """ Saves a Pulse_Block_Ensemble with name name to file.

        @param str name: name of the ensemble, which will be serialized.
        @param obj ensemble: a Pulse_Block_Ensemble object
        """

        # TODO: Overwrite handling
        ensemble.name = name
        with open(os.path.join(self.ensemble_dir, name + '.ens'), 'wb') as outfile:
            pickle.dump(ensemble, outfile)
        self.refresh_ensemble_list()
        self.current_ensemble = ensemble

    def get_pulse_block_ensemble(self, name, set_as_current_ensemble=False):
        """ Deserialize a *.ens file into a Pulse_Block_Ensemble object.

        @param name: string, name of the *.ens file.
        @param set_as_current_ensemble: bool, set the retained
               Pulse_Block_Ensemble object as the current ensemble.

        @return: Pulse_Block_Ensemble object which belongs to the given name.
        """

        if name in self.saved_pulse_block_ensembles:
            with open( os.path.join(self.ensemble_dir, name + '.ens'), 'rb') as infile:
                ensemble = pickle.load(infile)
        else:
            self.log.warning('The Pulse_Block_Ensemble object with name '
                    '"{0}" could not be found and serialized in:\n'
                    '{1}'.format(name, self.ensemble_dir))

            ensemble = None

        if set_as_current_ensemble:
            self.current_ensemble = ensemble

        return ensemble

    def delete_ensemble(self, name):
        """ Remove the ensemble with 'name' from the ensemble list and HDD. """

        if name in self.saved_pulse_block_ensembles:
            os.remove( os.path.join(self.ensemble_dir, name + '.ens'))

            # if a ensemble is removed, then check whether the current_ensemble
            # is actually the removed ensemble and if so set current_ensemble to
            # None.
            if hasattr(self.current_ensemble, 'name'):
                if self.current_ensemble.name == name:
                    self.current_ensemble = None

            self.refresh_ensemble_list()
        else:
            self.log.warning('Pulse_Block_Ensemble object with name "{0}" '
                    'not found in\n{1}\nTherefore nothing is removed.'.format(
                        name, self.ensemble_dir))
        return

    def refresh_ensemble_list(self):
        """ Refresh the list of available (saved) ensembles. """

        ensemble_files = [f for f in os.listdir(self.ensemble_dir) if '.ens' in f]
        ensembles = []
        for filename in ensemble_files:
            ensembles.append(filename.rsplit('.', 1)[0])
        ensembles.sort()
        self.saved_pulse_block_ensembles = ensembles

        self.signal_ensemble_list_updated.emit()

    def save_sequence(self, name, sequence):
        """ Serialize the Pulse_Sequence object with name 'name' to file.

        @param str name: name of the sequence object.
        @param object sequence: a Pulse_Sequence object, which is going to be
                                serialized to file.

        @return: str: name of the serialized object, if needed.
        """

        # TODO: Overwrite handling
        sequence.name = name
        with open( os.path.join(self.sequence_dir, name + '.se'), 'wb') as outfile:
            pickle.dump(sequence, outfile)
        self.refresh_sequence_list()
        self.current_sequence = sequence
        return sequence

    def get_pulse_sequence(self, name, set_as_current_sequence=False):
        """ Deserialize a *.se file into a Sequence object.

        @param name: string, name of the *.se file.
        @param set_as_current_sequence: bool, set the retained
               Sequence object as the current ensemble.

        @return: Sequence object which belongs to the given name.
        """

        if name in self.saved_pulse_sequences:
            with open( os.path.join(self.sequence_dir, name + '.se'), 'rb') as infile:
                sequence = pickle.load(infile)
        else:
            self.log.warning('The Sequence object with name "{0}" could not '
                    'be found and serialized in:\n'
                    '{1}'.format(name, self.sequence_dir))
            sequence = None

        if set_as_current_sequence:
            self.current_sequence = sequence

        return sequence

    def delete_sequence(self, name):
        """ Remove the sequence "name" from the sequence list and HDD.

        @param str name: name of the sequence object, which should be deleted.
        """

        if name in self.saved_pulse_sequences:
            os.remove( os.path.join(self.sequence_dir, name + '.se'))
            self.refresh_sequence_list()
        else:
            self.log.warning('Sequence object with name "{0}" not found '
                    'in\n{1}\nTherefore nothing is '
                    'removed.'.format(name, self.sequence_dir))

    def refresh_sequence_list(self):
        """ Refresh the list of available (saved) sequences. """

        sequence_files = [f for f in os.listdir(self.sequence_dir) if '.se' in f]
        sequences = []
        for filename in sequence_files:
            sequences.append(filename[:-3])
        sequences.sort()
        self.saved_pulse_sequences = sequences
        self.signal_sequence_list_updated.emit()
        return

    #---------------------------------------------------------------------------
    #                    END sequence/block generation
    #---------------------------------------------------------------------------


    #---------------------------------------------------------------------------
    #                    BEGIN sequence/block sampling
    #---------------------------------------------------------------------------
    def sample_pulse_block_ensemble(self, ensemble_name, write_to_file=True, chunkwise=True,
                                    offset_bin=0, name_tag=''):
        """ General sampling of a Pulse_Block_Ensemble object, which serves as the construction plan.

        @param str ensemble_name: Name, which should correlate with the name of on of the displayed
                                  ensembles.
        @param bool write_to_file: Write either to RAM or to File (depends on the available space
                                   in RAM). If set to FALSE, this method will return the samples
                                   (digital and analog) as numpy arrays
        @param bool chunkwise: Decide, whether you want to write chunkwise, which will reduce
                               memory usage but will increase vastly the amount of time needed.
        @param int offset_bin: If many pulse ensembles are samples sequentially, then the
                               offset_bin of the previous sampling can be passed to maintain
                               rotating frame across pulse_block_ensembles
        @param str name_tag: a name tag, which is used to keep the sampled files together, which
                             where sampled from the same Pulse_Block_Ensemble object but where
                             different offset_bins were used.

        @return tuple: of length 4 with
                       (analog_samples, digital_samples, [<created_files>], offset_bin).
                        analog_samples:
                            numpy arrays containing the sampled voltages
                        digital_samples:
                            numpy arrays containing the sampled logic levels
                        [<created_files>]:
                            list of strings, with the actual created files through the pulsing
                            device
                        offset_bin:
                            integer, which is used for maintaining the rotation frame.

        This method is creating the actual samples (voltages and logic states) for each time step
        of the analog and digital channels specified in the Pulse_Block_Ensemble.
        Therefore it iterates through all blocks, repetitions and elements of the ensemble and
        calculates the exact voltages (float64) according to the specified math_function. The
        samples are later on stored inside a float32 array.
        So each element is calculated with high precision (float64) and then down-converted to
        float32 to be stored.

        To preserve the rotating frame, an offset counter is used to indicate the absolute time
        within the ensemble. All calculations are done with time bins (dtype=int) to avoid rounding
        errors. Only in the last step when a single Pulse_Block_Element object is sampled  these
        integer bin values are translated into a floating point time.

        The chunkwise write mode is used to save memory usage at the expense of time. Here for each
        Pulse_Block_Element the write_to_file method in the HW module is called to avoid large
        arrays inside the memory. In other words: The whole sample arrays are never created at any
        time. This results in more function calls and general overhead causing the much longer time
        to complete.
        """

        # check for old files associated with the new ensemble and delete them from host PC
        # if write_to_file = True
        if write_to_file:
            # get sampled filenames on host PC referring to the same ensemble
            filename_list = [f for f in os.listdir(self.waveform_dir) if
                             f.startswith(ensemble_name + '_ch')]
            # delete all filenames in the list
            for file in filename_list:
                os.remove(os.path.join(self.waveform_dir, file))

            if len(filename_list) != 0:
                self.log.warning('Found old sampled ensembles for name '
                        '"{0}". Files deleted before sampling: '
                        '{1}'.format(ensemble_name, filename_list))

        start_time = time.time()
        # get ensemble
        ensemble = self.get_pulse_block_ensemble(ensemble_name)
        # Ensemble parameters to determine the shape of sample arrays
        number_of_samples = ensemble.length_bins
        ana_channels = ensemble.analog_channels
        dig_channels = ensemble.digital_channels
        ana_chnl_names = [chnl for chnl in ensemble.activation_config if 'a_ch' in chnl]

        # The time bin offset for each element to be sampled to preserve rotating frame.
        # offset_bin = 0

        if chunkwise and write_to_file:
            # Flags and counter for chunkwise writing
            is_first_chunk = True
            is_last_chunk = False
            number_of_elements = 0
            for block, reps in ensemble.block_list:
                number_of_elements += (reps+1)*len(block.element_list)
            element_count = 0
        else:
            # Allocate huge sample arrays if chunkwise writing is disabled.
            analog_samples = np.empty([ana_channels, number_of_samples], dtype = 'float32')
            digital_samples = np.empty([dig_channels, number_of_samples], dtype = bool)
            # Starting index for the sample array entrys
            entry_ind = 0

        # Iterate over all blocks within the Pulse_Block_Ensemble object
        for block, reps in ensemble.block_list:
            # Iterate over all repertitions of the current block
            for rep_no in range(reps+1):
                # Iterate over the Block_Elements inside the current block
                for block_element in block.element_list:
                    parameters = block_element.parameters
                    init_length_bins = block_element.init_length_bins
                    increment_bins = block_element.increment_bins
                    digital_high = block_element.digital_high
                    pulse_function = block_element.pulse_function
                    element_length_bins = init_length_bins + (rep_no*increment_bins)

                    # create floating point time array for the current element inside rotating frame
                    time_arr = (offset_bin + np.arange(element_length_bins, dtype='float64')) / self.sample_rate

                    if chunkwise and write_to_file:
                        # determine it the current element is the last one to be sampled.
                        # Toggle the is_last_chunk flag accordingly.
                        element_count += 1
                        if element_count == number_of_elements:
                            is_last_chunk = True

                        # allocate temporary sample arrays to contain the current element
                        analog_samples = np.empty([ana_channels, element_length_bins], dtype='float32')
                        digital_samples = np.empty([dig_channels, element_length_bins], dtype=bool)

                        # actually fill the allocated sample arrays with values.
                        for i, state in enumerate(digital_high):
                            digital_samples[i] = np.full(element_length_bins, state, dtype=bool)
                        for i, func_name in enumerate(pulse_function):
                            analog_samples[i] = np.float32(self._math_func[func_name](time_arr, parameters[i])/self.amplitude_list[ana_chnl_names[i]])

                        # write temporary sample array to file
                        created_files = self._write_to_file[self.waveform_format](
                            ensemble.name + name_tag, analog_samples, digital_samples,
                            number_of_samples, is_first_chunk, is_last_chunk)
                        # set flag to FALSE after first write
                        is_first_chunk = False
                    else:
                        # if the ensemble should be sampled as a whole (chunkwise = False) fill the
                        # entries in the huge sample arrays
                        for i, state in enumerate(digital_high):
                            digital_samples[i, entry_ind:entry_ind+element_length_bins] = np.full(element_length_bins, state, dtype=bool)
                        for i, func_name in enumerate(pulse_function):
                            analog_samples[i, entry_ind:entry_ind+element_length_bins] = np.float32(self._math_func[func_name](time_arr, parameters[i])/self.amplitude_list[ana_chnl_names[i]])

                        # increment the index offset of the overall sample array for the next
                        # element
                        entry_ind += element_length_bins

                    # if the rotating frame should be preserved (default) increment the offset
                    # counter for the time array.
                    if ensemble.rotating_frame:
                        offset_bin += element_length_bins

        if not write_to_file:
            # return a status message with the time needed for sampling the entire ensemble as a
            # whole without writing to file.
            self.log.info('Time needed for sampling and writing '
                    'Pulse_Block_Ensemble to file as a whole: "{0}" sec'
                    ''.format(str(int(np.rint(time.time() - start_time)))))
            self.sigSampleEnsembleComplete.emit()
            # return the sample arrays for write_to_file was set to FALSE
            return analog_samples, digital_samples, created_files, offset_bin
        elif chunkwise:
            # return a status message with the time needed for sampling and writing the ensemble
            # chunkwise.
            self.log.info('Time needed for sampling and writing to file '
                    'chunkwise: "{0}" sec'.format(
                        str(int(np.rint(time.time()-start_time)))))
            self.sigSampleEnsembleComplete.emit()
            return [], [], created_files, offset_bin
        else:
            # If the sampling should not be chunkwise and write to file is enabled call the
            # write_to_file method only once with both flags set to TRUE
            is_first_chunk = True
            is_last_chunk = True
            created_files = self._write_to_file[self.waveform_format](ensemble.name + name_tag,
                                                                      analog_samples,
                                                                      digital_samples,
                                                                      number_of_samples,
                                                                      is_first_chunk, is_last_chunk)
            # return a status message with the time needed for sampling and writing the ensemble as
            # a whole.
            self.log.info('Time needed for sampling and writing '
                    'Pulse_Block_Ensemble to file as a whole: "{0}" sec'
                    ''.format(str(int(np.rint(time.time()-start_time)))))
            self.sigSampleEnsembleComplete.emit()
            return [], [], created_files, offset_bin

    def sample_pulse_sequence(self, sequence_name, write_to_file=True, chunkwise=True):
        """ Samples the Pulse_Sequence object, which serves as the construction plan.

        @param str ensemble_name: Name, which should correlate with the name of on of the displayed
                                  ensembles.
        @param bool write_to_file: Write either to RAM or to File (depends on the available space
                                   in RAM). If set to FALSE, this method will return the samples
                                   (digital and analog) as numpy arrays
        @param bool chunkwise: Decide, whether you want to write chunkwise, which will reduce
                               memory usage but will increase vastly the amount of time needed.

        The sequence object is sampled by call subsequently the sampling routine for the
        Pulse_Block_Ensemble objects and passing if needed the rotating frame option.

        Only those Pulse_Block_Ensemble object where sampled that are different! These can be
        directly obtained from the internal attribute different_ensembles_dict of a Pulse_Sequence.

        Right now two 'simple' methods of sampling where implemented, which reuse the sample
        function for the Pulse_Block_Ensembles. One, which samples by preserving the phase (i.e.
        staying in the rotating frame) and the other which samples without keep a phase
        relationship between the different entries of the Pulse_Sequence object.

        More sophisticated sequence sampling method can be implemented here.
        """

        if write_to_file:
            # get sampled filenames on host PC referring to the same ensemble
            filename_list = [f for f in os.listdir(self.sequence_dir) if
                             f.startswith(sequence_name + '.seq')]
            # delete all filenames in the list
            for file in filename_list:
                os.remove(os.path.join(self.sequence_dir, file))

            if len(filename_list) != 0:
                self.log.warning('Found old sequence for name "{0}". '
                        'Files deleted before sampling: '
                        '{1}'.format(sequence_name, filename_list))

        start_time = time.time()
        # get ensemble
        sequence_obj = self.get_pulse_sequence(sequence_name, set_as_current_sequence=True)
        sequence_param_dict_list = []

        # Here all the sampled ensembles with their result file name will be locally stored:
        sampled_ensembles = OrderedDict()

        # if all the Pulse_Block_Ensembles should be in the rotating frame, then each ensemble
        # will be created in general with a different offset_bin. Therefore, in order to keep track
        # of the sampled Pulse_Block_Ensembles one has to introduce a running number as an
        # additional name tag, so keep the sampled files separate.
        if sequence_obj.rotating_frame:

            ensemble_index = 0  # that will indicate the ensemble index
            offset_bin = 0      # that will be used for phase preserving
            for ensemble_obj, seq_param in sequence_obj.ensemble_param_list:

                name_tag = '_' + str(ensemble_index).zfill(3)  # to make something like 001

                a_samples, \
                d_samples, \
                created_files, \
                offset_bin_return = self.sample_pulse_block_ensemble(ensemble_obj.name,
                                                                     write_to_file,
                                                                     chunkwise,
                                                                     offset_bin=offset_bin,
                                                                     name_tag=name_tag)

                # the temp_dict is a format how the sequence parameter will be saved
                temp_dict = dict()
                temp_dict['name'] = created_files

                # relate the created_files to a name identifier. Maybe this information will be
                # needed later on about that sequence object
                sampled_ensembles[ensemble_obj.name + name_tag] = created_files
                # update the sequence parameter to the temp dict:
                temp_dict.update(seq_param)
                # add the whole dict to the list of dicts, containing information about how to
                # write the sequence properly in the hardware file:
                sequence_param_dict_list.append(temp_dict)

                # for the next run, the returned offset_bin will serve as starting point for
                # phase preserving.
                offset_bin = offset_bin_return
                ensemble_index += 1

        else:

            # if phase prevervation between the sequence entries is not needed, then only the
            # different ensembles will be sampled, since the offset_bin does not matter for them:
            for ensemble_name in sequence_obj.different_ensembles_dict:
                ensemble_obj = self.get_pulse_block_ensemble(ensemble_name)

                a_samples, \
                d_samples, \
                created_files, \
                offset_bin = self.sample_pulse_block_ensemble(ensemble_name, write_to_file,
                                                              chunkwise, offset_bin=0, name_tag='')

                # contains information about which file(s) was/were created for the specified
                # ensemble:
                sampled_ensembles[ensemble_name] = created_files

            # go now through the sequence list and replace all the entries with the output of the
            # sampled ensemble file:
            for ensemble_obj, seq_param  in sequence_obj.ensemble_param_list:

                temp_dict = dict()
                temp_dict['name'] = sampled_ensembles[ensemble_obj.name]
                # update the sequence parameter to the temp dict:
                temp_dict.update(seq_param)

                sequence_param_dict_list.append(temp_dict)

        # FIXME: That is most propably not a good idea!!! But let's see whether that will work out
        #        and whether it will be necessary (for the upload method it is!)

        sequence_obj.set_sampled_ensembles(sampled_ensembles)
        # save the current object, since it has now a different attribute:
        self.save_sequence(sequence_name, sequence_obj)

        # pass the whole information to the sequence creation method in the hardware:
        self._write_to_file[self.sequence_format](sequence_name, sequence_param_dict_list)

        self.log.info('Time needed for sampling and writing Pulse Sequence '
                'to file as a whole: "{0}" sec'.format(
                    str(int(np.rint(time.time() - start_time)))))
        return

    def write_seq_to_file(self, a, b):
        pass

    #---------------------------------------------------------------------------
    #                    END sequence/block sampling
    #---------------------------------------------------------------------------

    # ========================================================================

    # def get_func_config(self):
    #     """ Retrieve func_config dict of the logic, including hardware constraints.
    #
    #     @return dict: with all the defined functions and their corresponding
    #                   parameters and constraints.
    #
    #     The contraints from the hardware are now also included in the dict. How
    #     the returned dict is looking like is defined in the inherited class
    #     SamplingFunctions.
    #     """
    #     func_config = self.func_config
    #
    #     # set the max amplitude from the hardware:
    #     # ampl_max = const['amplitude_analog'][1]
    #     # FIXME: You see it... below should be the actual amplitude constraint instead of 0.5
    #     ampl_max = 0.5/2.0
    #     if ampl_max is not None:
    #         for func in func_config:
    #             for param in func_config[func]:
    #                 if 'amplitude' in param:
    #                     func_config[func][param]['max'] = ampl_max
    #
    #     return func_config
