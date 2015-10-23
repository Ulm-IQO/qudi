# -*- coding: utf-8 -*-
"""
Created on Fri Oct 23 16:00:38 2015

@author: s_ntomek
"""

# unstable: Nikolas Tomek

from logic.generic_logic import GenericLogic
#from pyqtgraph.Qt import QtCore
#from core.util.mutex import Mutex
from collections import OrderedDict
import numpy as np
import time

class Pulse_Block_Element():
    """Object representing a single atomic element of an AWG sequence, i.e. a waiting time, a sine wave, etc.
    """
    def __init__(self, pulse_function, init_length_bins, markers_on, is_tau, parameters={}):
        self.pulse_function = pulse_function
        self.init_length_bins = init_length_bins
        self.markers_on = markers_on
        self.is_tau = is_tau
        self.parameters = parameters


class Pulse_Block():
    """Represents one sequence block in the AWG.
    Needs name and element_list (=[Pulse_Block_Element, Pulse_Block_Element, ...]) for initialization"""
    def __init__(self, name, element_list):
        self.name = name                        # block name
        self.element_list = element_list        # List of AWG_Block_Element objects
        self.refresh_parameters()

    def refresh_parameters(self):
        self.init_length_bins = 0
        self.increment_bins = 0
        for elem in self.element_list:
            self.init_length_bins += elem.init_length_bins
            if elem.is_tau:
                self.increment_bins += elem.parameters['increment_bins']
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
        

class Pulse_Sequence():
    """Represents a sequence of Blocks in the AWG.
    Needs name and block_list (=[(Pulse_Block, repetitions), ...]) for initialization"""
    def __init__(self, name, block_list, tau_array, rotating_frame = True):
        self.name = name                        # block name
        self.block_list = block_list        # List of AWG_Block objects with repetition number
        self.tau_array = tau_array
        self.rotating_frame = rotating_frame
        self.refresh_parameters()

    def refresh_parameters(self):
        self.length_bins = 0
        for block, reps in self.block_list:
            self.length_bins += (block.init_length_bins * (reps+1) + block.increment_bins * (reps*(reps+1)/2))
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

class SequenceGeneratorLogic(GenericLogic):
    """unstable: Nikolas Tomek
    This is the Logic class for the pulse sequence generator.
    """
    _modclass = 'sequencegeneratorlogic'
    _modtype = 'logic'

    ## declare connectors
    _out = {'sequencegenerator': 'SequenceGeneratorLogic'}

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
                        
        self.sampling_freq = 50e9
        self.current_sequence = None

#        self._current_sequence_reps = 1
#        self._current_number_of_lasers = 0
        self.saved_sequences = {}
        self.saved_matrices = {}
        self.saved_sequence_parameters = {}

#        self.threadlock = Mutex()
#
#        self.stopRequested = False


    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """
#        self._pulse_generator_device = self.connector['in']['pulsegenerator']['object']
#        self._save_logic = self.connector['in']['savelogic']['object']

    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.
        """
        return

    def save_sequence(self, name):
        ''' Saves the current sequence under name "name" into the class variable dictionarys "_saved_*" after encoding it in a proper sequence block list.
        '''
        sequence = self.encode_matrix(self._current_matrix, self._current_sequence_parameters['repetitions'])
        self._saved_sequences[name] = sequence
        self._saved_matrices[name] = self._current_matrix.copy()
        self._saved_sequence_parameters[name] = self._current_sequence_parameters.copy()
        return


    def delete_sequence(self, name):
        # remove the sequence "name" from the dictionary of saved sequences
        del self._saved_sequences[name]
        del self._saved_matrices[name]
        del self._saved_sequence_parameters[name]
        return


    def set_current_sequence(self, name):
        if (name in self._saved_sequences):
            self._current_sequence = self._saved_sequences[name]
            self._current_matrix = self._saved_matrices[name]
            self._current_sequence_parameters = self._saved_sequence_parameters[name]
        else:
            self._current_sequence = None
            self._current_matrix = None
            self._current_sequence_parameters = None
            
    def generate_rabi(self, mw_freq_Hz, mw_power_V, waiting_time_bins, laser_time_bins, tau_start_bins, tau_end_bins, tau_incr_bins):
        # create parameter dictionary for MW signal
        params = {}
        params['frequency'] = mw_freq_Hz
        params['amplitude'] = mw_power_V
        params['phase'] = 0
        params['increment_bins'] = tau_incr_bins
        # generate elements
        laser_element = Pulse_Block_Element('idle', laser_time_bins, [True, False], False)
        waiting_element = Pulse_Block_Element('idle', waiting_time_bins, [False, False], False)
        mw_element = Pulse_Block_Element('sin', tau_start_bins, [False, False], True, params)
        # put elements in a list to create the block
        element_list = [laser_element, waiting_element, mw_element]
        # create block
        block = Pulse_Block('rabi_block', element_list)
        # create tau_array
        tau_array = np.arange(tau_start_bins, tau_end_bins+1, tau_incr_bins)
        # put block(s) in a list with repetitions to create the sequence
        repetitions = int(tau_end_bins - tau_start_bins)
        block_list = [(block, repetitions)]
        # create sequence out of the block(s)
        sequence = Pulse_Sequence('Rabi', block_list, tau_array, False)
        return sequence

