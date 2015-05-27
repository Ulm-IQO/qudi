# -*- coding: utf-8 -*-
# unstable: Nikolas Tomek

from logic.GenericLogic import GenericLogic
#from pyqtgraph.Qt import QtCore
#from core.util.Mutex import Mutex
from collections import OrderedDict
import numpy as np
import time

class SequenceGeneratorLogic(GenericLogic):
    """unstable: Nikolas Tomek
    This is the Logic class for the pulse sequence generator.
    """    
    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)
        self._modclass = 'sequencegeneratorlogic'
        self._modtype = 'logic'

        ## declare connectors
#        self.connector['in']['pulsegenerator'] = OrderedDict()
#        self.connector['in']['pulsegenerator']['class'] = 'PulseGeneratorInterface'
#        self.connector['in']['pulsegenerator']['object'] = None
        
        self.connector['out']['sequencegenerator'] = OrderedDict()
        self.connector['out']['sequencegenerator']['class'] = 'SequenceGeneratorLogic'        

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
        
#        self._sequence_names = None
#        
#        self._binwidth_ns = 1.
#        self._number_of_laser_pulses = 100
#        
#        self.fluorescence_signal_start_bin = 0
#        self.fluorescence_signal_width_bins = 200
#        self.norm_start_bin = 2000
#        self.norm_width_bins = 200
#        
        self.pg_frequency_MHz = 950
        self.current_matrix = None
        self.current_sequence = []
        self.current_sequence_name = ''
        self.current_sequence_reps = 1
        self._saved_sequences = {}
        self._saved_matrices = {}
        self._saved_repetitions = {}
        
#        self.threadlock = Mutex()
#        
#        self.stopRequested = False
                      
                      
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """        
#        self._pulse_generator_device = self.connector['in']['pulsegenerator']['object']
#        self._save_logic = self.connector['in']['savelogic']['object']
      
    
    def save_sequence(self, matrix, name, repetitions):
        ''' Saves the matrix, name and number of repetitions in matrix_info into the class variable dictionary "_saved_sequences" after encoding it in a proper sequence block list.
        '''
        sequence = self.encode_matrix(matrix, repetitions)
        self._saved_sequences[name] = sequence
        self._saved_matrices[name] = matrix
        self._saved_repetitions[name] = repetitions
        return
    
    
    def encode_matrix(self, matrix, repetitions):
        ''' Encodes the current matrix coming from the GUI into a proper pulse sequence with blocks etc and create the tau_vector.
        '''
        # Create empty sequence
        sequence = []
        
        # First create a nested list "repeat_blocks" of block indices with corresponding repeat flags ([True/False, [1,2,3,...]]), i.e. sort out what part to repeat and what not. 
        repeat_indices = np.nonzero(matrix[:,10])[0]
        temp_index_list = []
        repeat_blocks = []
        for index in range(matrix.shape[0]):
            current_flag = index in repeat_indices
            if index == 0:
                last_flag = current_flag                
            if (current_flag != last_flag):
                repeat_blocks.append([last_flag, temp_index_list])
                temp_index_list = [index]
            else:
                temp_index_list.append(index)
            last_flag = current_flag
        repeat_blocks.append([current_flag, temp_index_list])
        
        # Run through the matrix according to the indices in "repeat_blocks" and create the sequence.
        for rep_flag, indices in repeat_blocks:
            # create the first iteration of the current block set
            # get active channel lists for the current block set
            active_channels = []
            for row in matrix[indices]:
                active_channels.append(np.nonzero(row[0:8])[0])
            # get starting lengths for the current block set
            block_length = matrix[indices, 8]
            # check if the current block set is set as repeat.
            if rep_flag:
                # get increment values for the current block set
                increments = matrix[indices, 9]
                # repeat the current block set and increment each individual block length
                for rep in range(repetitions):
                    for blocknum, channel_list in enumerate(active_channels):
                        # calculate current block length for this repetition
                        temp_length = block_length[blocknum] + (rep * increments[blocknum])
                        # append the list of active channels and the current block length to the sequence
                        sequence.append([channel_list, temp_length])
            else:
                # run through the current blocks and append them to the sequence
                for blocknum, channel_list in enumerate(active_channels):
                    sequence.append([channel_list, block_length[blocknum]])
        return sequence
    
    
    def delete_sequence(self, name):
        # remove the sequence "name" from the dictionary of saved sequences
        del self._saved_sequences[name]
        del self._saved_matrices[name]
        del self._saved_repetitions[name]
        return
     

    def update_current_sequence(self, name):
        if (name in self._saved_sequences):
            self.current_sequence_name = name
            self.current_sequence = self._saved_sequences[name]
            self.current_matrix = self._saved_matrices[name]
            self.current_sequence_reps = self._saved_repetitions[name]
        else:
            self.current_sequence_name = None
            self.current_sequence = None
            self.current_matrix = None
            self.current_sequence_reps = None
     
    def calculate_sequence_parameters(self, matrix, repetitions):
        # Calculate sequence length in bins.
        # Calculate the sum over all "length" entries
        sequence_length_bins = np.sum(matrix[:,8])
        # Add the increments and repetitions when the repeat-flag is checked
        for length, increment, flag in matrix[:,8:11]:
            if flag:
                for i in range(repetitions-1):
                    sequence_length_bins += length + (increment*(i+1))
                    
        # Calculate sequence length in ms
        sequence_length_ms = sequence_length_bins / (950. * 1000.)
        return (sequence_length_bins, sequence_length_ms)
       
    
    def get_sequence(self, name):
        sequence = None
        if (name in self._saved_sequences):
            sequence = self._saved_sequences[name]
        return sequence
        
    
    def get_sequence_names(self):
        names = list(self._saved_sequences.keys())
        return names
            
     
    def pulse_generator_on(self):
        time.sleep(1)
        return
        
        
    def pulse_generator_off(self):
        time.sleep(1)
        return

        
    def get_binwidth(self):
        binwidth_ns = 1000./950.
        return binwidth_ns

        
    def get_number_of_laser_pulses(self):
        numberoflasers = 100
        return numberoflasers
        
        
    def get_tau_vector(self):
        tau_vector = range(100)
        return tau_vector

        
    def get_laser_length(self):
        laser_length = 3800 # 4 us
        return laser_length

        