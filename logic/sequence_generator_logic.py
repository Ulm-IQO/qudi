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
import pickle
import glob
import os

class Pulse_Block_Element():
    """Object representing a single atomic element of an AWG sequence, i.e. a waiting time, a sine wave, etc.
    """
    def __init__(self, init_length_bins, is_tau, pulse_function = None, marker_active = None, parameters={}):
        self.pulse_function = pulse_function
        self.init_length_bins = init_length_bins
        self.marker_active = marker_active
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
    def __init__(self, name, block_list, tau_array, digital_channels, analogue_channels, rotating_frame = True):
        self.name = name                        # block name
        self.block_list = block_list        # List of AWG_Block objects with repetition number
        self.tau_array = tau_array
        self.rotating_frame = rotating_frame
        self.refresh_parameters()
        self.analogue_channels = analogue_channels 
        self.digital_channels = digital_channels

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
        self.analogue_channels = 2
        self.digital_channels = 4
        self.current_sequence = None
        self.current_block = None
        
        self.saved_blocks = []
        self.saved_sequences = []
        self.block_dir = ''
        self.sequence_dir = ''

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
        ''' loads a sequence from a .blk-file into the sequence editor
        '''
        if name in self.saved_sequences:
            with open(self.sequence_dir + name + '.seq', 'rb') as infile:
                sequence = pickle.load(infile)
            return sequence
        else:
            # TODO: implement proper error
            print('Error: No sequence with name "' + name + '" in saved sequences.')
            return
        
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
        return
        
        
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
            return block
        else:
            # TODO: implement proper error
            print('Error: No block with name "' + name + '" in saved blocks.')
            return

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
        
    
    def generate_block_object(self, name, gui_matrix):
        ''' reads out the gui matrix of the block generator and generates a Pulse_Block() object out of it.
        '''
        # each line in the matrix corresponds to one Pulse_Block_Element
        # Here these elements are created
        element_list = []        
        for line in gui_matrix:
            analogue_func = line[0:self.analogue_channels]
            init_length_bins = np.round(line[self.analogue_channels+self.digital_channels] * 1e9 * self.sampling_freq)
            is_tau = line[self.analogue_channels+self.digital_channels+1]
            marker_active = line[self.analogue_channels:self.digital_channels]
            parameters = {}
            parameters['increment_bins'] = np.round(line[self.analogue_channels+self.digital_channels+2] * 1e9 * self.sampling_freq)
            parameters['frequency'] = line[self.analogue_channels+self.digital_channels+3]
            parameters['amplitude'] = line[self.analogue_channels+self.digital_channels+4]
            parameters['phase'] = line[self.analogue_channels+self.digital_channels+5]
            element_list.append(Pulse_Block_Element(init_length_bins, is_tau, analogue_func, marker_active, parameters))
        # generate the Pulse_Block() object
        block_obj = Pulse_Block(name, element_list)
        return block_obj
        
    def generate_sequence_object(self, name, gui_matrix, tau_list, rotating_frame):
        ''' reads out the gui matrix of the sequence generator and generates a Pulse_Sequence() object out of it.
        '''
        # each line in the matrix corresponds to one Pulse_Block with number of repetitions
        # Here a nested list for the Pulse_Sequence() object is created
        block_list = []        
        for line in gui_matrix:
            block = self.load_block(line[0])
            repetitions = line[1]
            block_list.append((block, repetitions))
        # generate the Pulse_Sequence() object
        sequence_obj = Pulse_Sequence(name, block_list, tau_list, rotating_frame, self.analogue_channels)
        return sequence_obj
    
    def refresh_block_list(self):
        ''' refresh the list of available (saved) blocks
        '''
        block_files = glob.glob(self.block_dir + '*.blk')
        blocks = []
        for filename in block_files:
            blocks.append(filename[:-4])
        blocks.sort()
        self.saved_blocks = blocks
        return

            
    # TODO: Properly implement a predefined sequence... this here is deprecated
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

