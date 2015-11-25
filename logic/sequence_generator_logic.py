# -*- coding: utf-8 -*-
"""
Created on Fri Oct 23 16:00:38 2015

@author: s_ntomek
"""

# unstable: Nikolas Tomek

from logic.generic_logic import GenericLogic
from logic.sampling_functions import SamplingFunctions
from pyqtgraph.Qt import QtCore
from collections import OrderedDict

#from core.util.mutex import Mutex
import numpy as np
import pickle
import glob
import os

class Pulse_Block_Element(object):
    """ Object representing a single atomic element of an AWG sequence, i.e. a
        waiting time, a sine wave, etc.
    """
    def __init__(self, init_length_bins, analogue_channels, digital_channels, increment_bins = 0, pulse_function = None, marker_active = None, parameters={}):
        self.pulse_function = pulse_function
        self.init_length_bins = init_length_bins
        self.markers_on = marker_active
        self.increment_bins = increment_bins
        self.parameters = parameters
        self.analogue_channels = analogue_channels
        self.digital_channels = digital_channels


class Pulse_Block(object):
    """ Represents one sequence block in the AWG.

    Needs name and element_list
    (=[Pulse_Block_Element, Pulse_Block_Element, ...]) for initialization.
    """

    def __init__(self, name, element_list):
        self.name = name                        # block name
        self.element_list = element_list        # List of AWG_Block_Element objects
        self.refresh_parameters()

    def refresh_parameters(self):

        # Initialize at first all parameters, which are going to be initialized
        # with a default value and then assign the value from the element_list.
        self.init_length_bins = 0
        self.increment_bins = 0
        self.analogue_channels = 0
        self.digital_channels = 0

        for elem in self.element_list:
            self.init_length_bins += elem.init_length_bins
            self.increment_bins += elem.increment_bins
            if elem.analogue_channels > self.analogue_channels:
                self.analogue_channels = elem.analogue_channels
            if elem.digital_channels > self.digital_channels:
                self.digital_channels = elem.digital_channels
        return

    def replace_element(self, position, element):
        self.element_list[position] = element
        self.refresh_parameters()
        return

    def delete_element(self, position):
        del(self.element_list[position])
        self.refresh_parameters()
        return

    def append_element(self, element, at_beginning = False):
        if at_beginning:
            self.element_list.insert(0, element)
        else:
            self.element_list.append(element)
        self.refresh_parameters()
        return


class Pulse_Block_Ensemble(object):
    """
    Represents an ensemble of pulse blocks.
    Needs name and block_list (=[(Pulse_Block, repetitions), ...]) for initialization
    This instance describes the content of a waveform (no sequenced triggered/conditional stuff).
    """
    def __init__(self, name, block_list, tau_array, analyse_laser_ind, rotating_frame = True):
        self.name = name                        # block name
        self.block_list = block_list        # List of AWG_Block objects with repetition number
        self.tau_array = tau_array
        self.analyse_laser_ind = analyse_laser_ind
        self.rotating_frame = rotating_frame
        self.refresh_parameters()

    def refresh_parameters(self):
        self.length_bins = 0
        self.analogue_channels = 0
        self.digital_channels = 0
        for block, reps in self.block_list:
            self.length_bins += (block.init_length_bins * (reps+1) + block.increment_bins * (reps*(reps+1)/2))
            if block.analogue_channels > self.analogue_channels:
                self.analogue_channels = block.analogue_channels
            if block.digital_channels > self.digital_channels:
                self.digital_channels = block.digital_channels
        self.estimated_bytes = self.length_bins * (self.analogue_channels * 4 + self.digital_channels)
        return

    def replace_block(self, position, block):
        self.block_list[position] = block
        self.refresh_parameters()
        return

    def delete_block(self, position):
        del(self.block_list[position])
        self.refresh_parameters()
        return

    def append_block(self, block, at_beginning = False):
        if at_beginning:
            self.block_list.insert(0, block)
        else:
            self.block_list.append(block)
        self.refresh_parameters()
        return


class Pulse_Sequence(object):
    """
    Represents a playback procedure for a number of Pulse_Block_Ensembles.
    Unused for pulse generator hardware without sequencing functionality.
    """
    def __init__(self, name, ensemble_list, tau_array, analyse_laser_ind, rotating_frame = True):
        self.name = name
        self.ensemble_list = ensemble_list
        self.tau_array = tau_array
        self.analyse_laser_ind = analyse_laser_ind
        self.rotating_frame = rotating_frame
        self.refresh_parameters()

    def refresh_parameters(self):
        self.length_bins = 0
        self.analogue_channels = 0
        self.digital_channels = 0
        for ensemble, reps in self.ensemble_list:
            self.length_bins += (ensemble.length_bins * reps)
            if ensemble.analogue_channels > self.analogue_channels:
                self.analogue_channels = ensemble.analogue_channels
            if ensemble.digital_channels > self.digital_channels:
                self.digital_channels = ensemble.digital_channels
        self.estimated_bytes = self.length_bins * (self.analogue_channels * 4 + self.digital_channels)
        return

    def replace_ensemble(self, position, ensemble):
        self.ensemble_list[position] = ensemble
        self.refresh_parameters()
        return

    def delete_ensemble(self, position):
        del(self.ensemble_list[position])
        self.refresh_parameters()
        return

    def append_ensemble(self, ensemble, at_beginning = False):
        if at_beginning:
            self.ensemble_list.insert(0, ensemble)
        else:
            self.ensemble_list.append(ensemble)
        self.refresh_parameters()
        return


class Waveform(object):
    """
    Represents a sampled Pulse_Block_Ensemble() object.
    Holds analogue and digital samples and important parameters.
    """
    def __init__(self, block_ensemble, sampling_freq, pp_voltage, analogue_samples, digital_samples):
        self.name = block_ensemble.name
        self.sampling_freq = sampling_freq
        self.pp_voltage = pp_voltage
        self.block_ensemble = block_ensemble
        self.analogue_samples = analogue_samples
        self.digital_samples = digital_samples


class SequenceGeneratorLogic(GenericLogic, SamplingFunctions):
    """unstable: Nikolas Tomek
    This is the Logic class for the pulse (sequence) generation.
    """
    _modclass = 'sequencegeneratorlogic'
    _modtype = 'logic'

    ## declare connectors
    _in = {'pulser':'PulserInterface'}
    _out = {'sequencegenerator': 'SequenceGeneratorLogic'}

    
    # define signals
    signal_block_list_updated = QtCore.Signal()
    signal_ensemble_list_updated = QtCore.Signal()
    signal_sequence_list_updated = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)

        self.logMsg('The following configuration was found.',
                    msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')
        SamplingFunctions.__init__(self)
        self.sampling_freq = 25e9
        self.pp_voltage = 0.5
        self.analogue_channels = 2
        self.digital_channels = 4
        self.current_block = None
        self.current_ensemble = None
        self.current_sequence = None
        self.saved_blocks = []
        self.saved_ensembles = []
        self.saved_sequences = []
        self.block_dir = ''
        self.ensemble_dir = ''
        self.sequence_dir = ''

        # Definition of this parameter. See fore more explanation in file
        # sampling_functions.py
        length_def = {'unit': 's', 'init_val': 0.0, 'min': 0.0, 'max': +1e12,
                      'view_stepsize': 1e-9, 'dec': 8, 'disp_unit': 'n'}

        # make a parameter constraint dict
        self.param_config = OrderedDict()
        self.param_config['length'] = length_def
        self.param_config['increment'] = length_def


        self.table_config = {'function_0': 0, 'frequency1_0': 1,
                             'amplitude1_0': 2, 'phase1_0': 3,
                             'digital_0': 4, 'digital_1': 5,
                             'function_1': 6, 'frequency1_1': 7,
                             'amplitude1_1': 8, 'phase1_1': 9,
                             'digital_2': 10,
                             'digital_3': 11,
                             'length': 12, 'increment': 13}

    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """
        self.refresh_block_list()
        self.refresh_ensemble_list()
        self.refresh_sequence_list()

        self._pulse_generator_device = self.connector['in']['pulser']['object']
        pass

    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.
        """
        pass

    def get_hardware_constraints(self):
        """ Request the constrains from the hardware, in order to pass them
            to the GUI if necessary.

        @return: dict where the keys in it are predefined in the interface.
        """
        return self._pulse_generator_device.get_constraints()

    def get_func_config(self):
        """ Retrieve func_config dict of the logic, including hardware constraints.


        @return dict: with all the defined functions and their corresponding
                      parameters and constraints.

        The contraints from the hardware are now also included in the dict. How
        the returned dict is looking like is defined in the inherited class
        SamplingFunctions.
        """
        const = self.get_hardware_constraints()

        func_config = self.func_config

        # set the max amplitude from the hardware:
        ampl_max = const['amplitude_analog'][1]
        if ampl_max is not None:
            for func in func_config:
                for param in func_config[func]:
                    if 'amplitude' in param:
                        func_config[func][param]['max'] = ampl_max

        return func_config

    def get_param_config(self):
        """ Pass the param_config.

        @return: dict with the configurations for the additional parameters.
        """
        return self.param_config


    def set_sampling_freq(self, freq_Hz):
        """
        Sets the sampling frequency of the pulse generator device and updates the corresponding value in this logic.
        """
        self._pulse_generator_device.set_sample_rate(freq_Hz)
        self.sampling_freq = freq_Hz
        return 0
        
    def set_pp_voltage(self, voltage):
        """
        Sets the peak-to-peak output voltage of the pulse generator device and updates the corresponding value in this logic.
        Only of importance if the device has analogue channels with adjustable peak-to-peak voltage.
        """
        self._pulse_generator_device.set_pp_voltage(voltage)
        self.pp_voltage = voltage
        return 0
        
    def set_active_channels(self, digital, analogue):
        """
        Sets the number of active channels in the pulse generator device and updates the corresponding variables in this logic.
        """
        self._pulse_generator_device.set_active_channels(digital, analogue)
        self.analogue_channels = analogue
        self.digital_channels = digital
        return 0
        
    def download_ensemble(self, ensemble_name):
        """
        Samples and downloads a saved Pulse_Block_Ensemble with name "ensemble_name" into the pulse generator internal memory.
        """
        ensemble = self.get_ensemble(ensemble_name)
        waveform = self.generate_waveform(ensemble)
        self._pulse_generator_device.download_waveform(waveform)
        return 0
        
    def load_asset(self, name, channel = None):
        assets_on_device = self._pulse_generator_device.get_sequence_names()
        if name in assets_on_device:
            self._pulse_generator_device.load_sequence(name, channel)
        
#-------------------------------------------------------------------------------
#                    BEGIN sequence/block generation
#-------------------------------------------------------------------------------
    def save_block(self, name, block):
        ''' saves a block generated by the block editor into a file
        '''
        # TODO: Overwrite handling
        block.name = name
        with open(self.block_dir + name + '.blk', 'wb') as outfile:
            pickle.dump(block, outfile)
        self.refresh_block_list()
        self.current_block = block
        return

    def load_block(self, name):
        ''' loads a block from a .blk-file into the block editor
        '''
        if name in self.saved_blocks:
            with open(self.block_dir + name + '.blk', 'rb') as infile:
                block = pickle.load(infile)
            self.current_block = block
        else:
            # TODO: implement proper error
            print('Error: No block with name "' + name + '" in saved blocks.')
        return
        
    def get_block(self, name):
        """
        Returns the saved Pulse_Block object by name without setting it as current block
        """
        if name in self.saved_blocks:
            with open(self.block_dir + name + '.blk', 'rb') as infile:
                block = pickle.load(infile)
        else:
            block = None
            # TODO: implement proper error
            print('Error: No block with name "' + name + '" in saved blocks.')
        return block

    def delete_block(self, name):
        ''' remove the block "name" from the block list and HDD
        '''
        if name in self.saved_blocks:
            os.remove(self.block_dir + name + '.blk')
            self.refresh_block_list()
        else:
            # TODO: implement proper error
            print('Error: No block with name "' + name + '" in saved blocks.')
        return

    def refresh_block_list(self):
        ''' refresh the list of available (saved) blocks
        '''
        block_files = glob.glob(self.block_dir + '*.blk')
        blocks = []
        for filename in block_files:
            blocks.append(filename[:-4])
        blocks.sort()
        self.saved_blocks = blocks
        self.signal_block_list_updated.emit()
        return


    def save_ensemble(self, name, ensemble):
        ''' saves a block ensemble generated by the block ensemble editor into a file
        '''
        # TODO: Overwrite handling
        ensemble.name = name
        with open(self.ensemble_dir + name + '.ben', 'wb') as outfile:
            pickle.dump(ensemble, outfile)
        self.refresh_ensemble_list()
        self.current_ensemble = ensemble
        return

    def load_ensemble(self, name):
        ''' loads a block ensemble from a .ben-file into the block ensemble editor
        '''
        if name in self.saved_ensembles:
            with open(self.ensemble_dir + name + '.ben', 'rb') as infile:
                ensemble = pickle.load(infile)
            self.current_ensemble = ensemble
        else:
            # TODO: implement proper error
            print('Error: No ensemble with name "' + name + '" in saved ensembles.')
        return
        
    def get_ensemble(self, name):
        """
        Returns the saved Pulse_Block_Ensemble object by name without setting it as current ensemble
        """
        if name in self.saved_ensembles:
            with open(self.ensemble_dir + name + '.ben', 'rb') as infile:
                ensemble = pickle.load(infile)
        else:
            ensemble = None
            # TODO: implement proper error
            print('Error: No ensemble with name "' + name + '" in saved ensembles.')
        return ensemble

    def delete_ensemble(self, name):
        ''' remove the ensemble "name" from the ensemble list and HDD
        '''
        if name in self.saved_ensembles:
            os.remove(self.ensemble_dir + name + '.ben')
            self.refresh_ensemble_list()
        else:
            # TODO: implement proper error
            print('Error: No ensemble with name "' + name + '" in saved ensembles.')
        return

    def refresh_ensemble_list(self):
        ''' refresh the list of available (saved) ensembles
        '''
        ensemble_files = glob.glob(self.ensemble_dir + '*.ben')
        ensembles = []
        for filename in ensemble_files:
            ensembles.append(filename[:-4])
        ensembles.sort()
        self.saved_ensembles = ensembles
        self.signal_ensemble_list_updated.emit()
        return


    def save_sequence(self, name, sequence):
        ''' saves a sequence generated by the sequence editor into a file
        '''
        # TODO: Overwrite handling
        sequence.name = name
        with open(self.sequence_dir + name + '.seq', 'wb') as outfile:
            pickle.dump(sequence, outfile)
        self.refresh_sequence_list()
        self.current_sequence = sequence
        return

    def load_sequence(self, name):
        ''' loads a sequence from a .seq-file into the sequence editor
        '''
        if name in self.saved_sequences:
            with open(self.sequence_dir + name + '.seq', 'rb') as infile:
                sequence = pickle.load(infile)
            self.current_sequence = sequence
        else:
            # TODO: implement proper error
            print('Error: No sequence with name "' + name + '" in saved sequences.')
        return
        
    def get_sequence(self, name):
        """
        Returns the saved Pulse_Sequence object by name without setting it as current sequence
        """
        if name in self.saved_sequences:
            with open(self.sequence_dir + name + '.seq', 'rb') as infile:
                sequence = pickle.load(infile)
        else:
            sequence = None
            # TODO: implement proper error
            print('Error: No sequence with name "' + name + '" in saved sequences.')
        return sequence

    def delete_sequence(self, name):
        ''' remove the sequence "name" from the sequence list and HDD
        '''
        if name in self.saved_sequences:
            os.remove(self.sequence_dir + name + '.seq')
            self.refresh_sequence_list()
        else:
            # TODO: implement proper error
            print('Error: No sequence with name "' + name + '" in saved sequences.')
        return

    def refresh_sequence_list(self):
        ''' refresh the list of available (saved) sequences
        '''
        sequence_files = glob.glob(self.sequence_dir + '*.seq')
        sequences = []
        for filename in sequence_files:
            sequences.append(filename[:-4])
        sequences.sort()
        self.saved_sequences = sequences
        self.signal_sequence_list_updated.emit()
        return


    def generate_block(self, name, block_matrix):
        """
        Generates a Pulse_Block object out of the corresponding editor table/matrix.
        """
        # each line in the matrix corresponds to one Pulse_Block_Element
        # Here these elements are created
        analogue_func = [None]*self.analogue_channels
        digital_flags = [None]*self.digital_channels

        lengths = np.array([np.round(x/(1e9/self.sampling_freq)) for x in block_matrix['f'+str(self.table_config['length'])]])
        increments = np.array([np.round(x/(1e9/self.sampling_freq)) for x in block_matrix['f'+str(self.table_config['increment'])]])

        for chnl_num in range(self.analogue_channels):
            # Save all function names for channel number "chnl_num" in one column of "analogue_func"
            # Also convert them to strings
            analogue_func[chnl_num] = np.array([x.decode('utf-8') for x in block_matrix['f'+str(self.table_config['function_'+str(chnl_num)])]])
        # convert to numpy ndarray
        analogue_func = np.array(analogue_func)

        for chnl_num in range(self.digital_channels):
            # Save the marker flag for channel number "chnl_num" in one column of "digital_flags"
            # Also convert them to bools
            digital_flags[chnl_num] = np.array([bool(x) for x in block_matrix['f'+str(self.table_config['digital_'+str(chnl_num)])]])
        # convert to numpy ndarray
        digital_flags = np.array(digital_flags)

        block_element_list = [None]*len(block_matrix)
        for elem_num in range(len(block_matrix)):
            elem_func = analogue_func[:, elem_num]
            elem_marker = digital_flags[:, elem_num]
            elem_incr = increments[elem_num]
            elem_length = lengths[elem_num]
            elem_parameters = [None]*self.analogue_channels

            # create parameter dictionarys for each channel
            for chnl_num, func in enumerate(elem_func):
                param_dict = {}
                for param in self.func_config[func]:
                    if 'frequency' in param:
                        param_dict[param] = 1e6*block_matrix[elem_num][self.table_config[param+'_'+str(chnl_num)]]
                    else:
                        param_dict[param] = block_matrix[elem_num][self.table_config[param+'_'+str(chnl_num)]]
                elem_parameters[chnl_num] = param_dict

            block_element = Pulse_Block_Element(elem_length, len(analogue_func), len(digital_flags), elem_incr, elem_func, elem_marker, elem_parameters)
            block_element_list[elem_num] = block_element

        # generate the Pulse_Block() object
        block = Pulse_Block(name, block_element_list)
        # save block to a file
        self.save_block(name, block)
        # set current block
        self.current_block = block
        return


    def generate_block_ensemble(self, ensemble_matrix):
        """
        Generates a Pulse_Block_Ensemble object out of the corresponding editor table/matrix.
        """

        return

    def generate_sequence(self, sequence_matrix):
        """
        Generates a Pulse_Sequence object out of the corresponding editor table/matrix.
        Creates a whole new structure of Block_Elements, Blocks and Block_Ensembles so that the phase of the seqeunce is preserved.
        NOT EASY!
        """
        return
#-------------------------------------------------------------------------------
#                    END sequence/block generation
#-------------------------------------------------------------------------------


#-------------------------------------------------------------------------------
#                    BEGIN sequence/block sampling
#-------------------------------------------------------------------------------
    def generate_waveform(self, block_ensemble):
        """
        Samples a Pulse_Block_Ensemble() object and creates a Waveform().
        The Waveform object can be really big so only create it if needed and delete it from memory asap.

        @param Pulse_Block_Ensemble() block_ensemble: The block ensemble object to be sampled

        @return Waveform(): A Waveform object containing the samples and metadata (sampling_freq etc)
        """
        analogue_samples, digital_samples = self._sample_ensemble(block_ensemble)
        waveform_obj = Waveform(block_ensemble, self.sampling_freq, self.pp_voltage, analogue_samples, digital_samples)
        return waveform_obj

    def sample_sequence(self, sequence):
        """
        Samples the sequence to obtain the needed waveforms.
        """
        pass

    def _sample_ensemble(self, ensemble):
        """
        Calculates actual sample points given a Pulse_Block_Ensemble object.

        @param Pulse_Block_Ensemble() ensemble: Block ensemble to be sampled.

        @return numpy_ndarrays[channel, sample]: The sampled analogue and digital channels
        """
        arr_len = np.round(ensemble.length_bins*1.01)
        ana_channels = ensemble.analogue_channels
        dig_channels = ensemble.digital_channels

        sample_arr = np.empty([ana_channels, arr_len])
        marker_arr = np.empty([dig_channels, arr_len], dtype = bool)

        entry = 0
        bin_offset = 0
        for block, reps in ensemble.block_list:
            for rep_no in range(reps+1):
                temp_sample_arr, temp_marker_arr = self._sample_block(block, rep_no, bin_offset)
                temp_len = temp_sample_arr.shape[1]
                sample_arr[:, entry:temp_len+entry] = temp_sample_arr
                marker_arr[:, entry:temp_len+entry] = temp_marker_arr
                entry += temp_len
                if ensemble.rotating_frame:
                    bin_offset = entry
        # slice the sample array to cut off uninitialized entrys at the end
        self.analogue_samples = sample_arr[:, :entry]
        self.digital_samples = marker_arr[:, :entry]
        return sample_arr[:, :entry], marker_arr[:, :entry]


    def _sample_block(self, block, iteration_no = 0, bin_offset = 0):
        """
        Calculates actual sample points given a Block.

        @param Pulse_Block() block: Block to be sampled.
        @param int iteration_no: Current number of repetition step.
        @param int bin_offset: The time bin offset, i.e. the position of the block inside the whole sample array.

        @return numpy_ndarrays[channel, sample]: The sampled analogue and digital channels
        """
        ana_channels = block.analogue_channels
        dig_channels = block.digital_channels
        block_length_bins = block.init_length_bins + (block.increment_bins * iteration_no)
        arr_len = np.round(block_length_bins*1.01)
        sample_arr = np.empty([ana_channels, arr_len])
        marker_arr = np.empty([dig_channels, arr_len], dtype = bool)
        entry = 0
        bin_offset_temp = bin_offset
        for block_element in block.element_list:
            temp_sample_arr, temp_marker_arr = self._sample_block_element(block_element, iteration_no, bin_offset_temp)
            temp_len = temp_sample_arr.shape[1]
            sample_arr[:, entry:temp_len+entry] = temp_sample_arr
            marker_arr[:, entry:temp_len+entry] = temp_marker_arr
            entry += temp_len
            bin_offset_temp = bin_offset + entry
        # slice the sample array to cut off uninitialized entrys at the end
        return sample_arr[:, :entry], marker_arr[:, :entry]


    def _sample_block_element(self, block_element, iteration_no = 0, bin_offset = 0):
        """
        Calculates actual sample points given a Block_Element.

        @param Pulse_Block_Element() block_element: Block element to be sampled.
        @param int iteration_no: Current number of repetition step.
        @param int bin_offset: The time bin offset, i.e. the position of the block_element inside the whole sample array.

        @return (numpy_ndarrays[channel, sample], numpy_ndarrays[channel, sample]): The sampled analogue and digital channels
        """
        ana_channels = block_element.analogue_channels
        dig_channels = block_element.digital_channels
        parameters = block_element.parameters
        init_length_bins = block_element.init_length_bins
        increment_bins = block_element.increment_bins
        markers_on = block_element.markers_on
        pulse_function = block_element.pulse_function

        element_length_bins = init_length_bins + (iteration_no*increment_bins)
        sample_arr = np.empty([ana_channels, element_length_bins])
        marker_arr = np.empty([dig_channels, element_length_bins], dtype = bool)
        time_arr = (bin_offset + np.arange(element_length_bins)) / self.sampling_freq

        for i, state in enumerate(markers_on):
            marker_arr[i] = np.full(element_length_bins, state, dtype = bool)
        for i, func_name in enumerate(pulse_function):
            sample_arr[i] = self._math_func[func_name](time_arr, parameters[i])

        return sample_arr, marker_arr
#-------------------------------------------------------------------------------
#                    END sequence/block sampling
#-------------------------------------------------------------------------------

    def generate_rabi(self, mw_freq_Hz, mw_amp_V, waiting_time_bins, laser_time_bins, tau_start_bins, tau_end_bins, tau_incr_bins):
        # create parameter dictionary for MW signal
        params = {}
        params['frequency'] = mw_freq_Hz
        params['amplitude'] = mw_amp_V
        params['phase'] = 0
        # generate elements
        laser_markers = [False]*self.digital_channels
        laser_markers[0] = True
        laser_element = Pulse_Block_Element(laser_time_bins, self.analogue_channels, self.digital_channels, 0, 'Idle', laser_markers)
        waiting_element = Pulse_Block_Element(waiting_time_bins, self.analogue_channels, self.digital_channels, 0, 'Idle', [False]*self.digital_channels)
        mw_element = Pulse_Block_Element(tau_start_bins, self.analogue_channels, self.digital_channels, tau_incr_bins, 'Sin', [False]*self.digital_channels, params)
        # put elements in a list to create the block
        element_list = [laser_element, waiting_element, mw_element]
        # create block
        block = Pulse_Block('Rabi_block', element_list)
        # create tau_array
        tau_array = np.arange(tau_start_bins, tau_end_bins+1, tau_incr_bins)
        # put block(s) in a list with repetitions to create the sequence
        repetitions = len(tau_array)-1
        block_list = [(block, repetitions)]
        # create sequence out of the block(s)
        block_ensemble = Pulse_Block_Ensemble('Rabi', block_list, tau_array, 0, self.pp_voltage, self.sampling_freq, False)
        # save block
        self.save_block('Rabi_block', block)
        # save ensemble
        self.save_ensemble('Rabi', block_ensemble)
        # set current block
        self.current_block = block
        # set current block ensemble
        self.current_ensemble = block_ensemble
        return

