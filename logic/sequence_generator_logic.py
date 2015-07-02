# -*- coding: utf-8 -*-
# unstable: Nikolas Tomek

from logic.generic_logic import GenericLogic
#from pyqtgraph.Qt import QtCore
#from core.util.mutex import Mutex
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
        self._pg_frequency_MHz = 950
        self._current_matrix = None
        self._current_sequence = []
        self._current_sequence_parameters = {}
        self._current_sequence_parameters['length_bins'] = 0
        self._current_sequence_parameters['length_ms'] = 0
        self._current_sequence_parameters['number_of_lasers'] = 100
        self._current_sequence_parameters['tau_vector'] = np.array(range(100))
        self._current_sequence_parameters['laser_length_vector'] = np.full(100, 3800, int)
        self._current_sequence_parameters['repetitions'] = 1
#        self._current_sequence_reps = 1
#        self._current_number_of_lasers = 0
        self._saved_sequences = {}
        self._saved_matrices = {}
        self._saved_sequence_parameters = {}

#        self.threadlock = Mutex()
#
#        self.stopRequested = False


    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """
#        self._pulse_generator_device = self.connector['in']['pulsegenerator']['object']
#        self._save_logic = self.connector['in']['savelogic']['object']


    def save_sequence(self, name):
        ''' Saves the current sequence under name "name" into the class variable dictionarys "_saved_*" after encoding it in a proper sequence block list.
        '''
        sequence = self.encode_matrix(self._current_matrix, self._current_sequence_parameters['repetitions'])
        self._saved_sequences[name] = sequence
        self._saved_matrices[name] = self._current_matrix.copy()
        self._saved_sequence_parameters[name] = self._current_sequence_parameters.copy()
        return


#    def encode_matrix_nestedlist(self, matrix, repetitions):
#        ''' Encodes the current matrix coming from the GUI into a proper pulse sequence with blocks etc and create the tau_vector.
#        '''
#        # Create empty sequence
#        sequence = []
#
#        # First create a nested list "repeat_blocks" of block indices with corresponding repeat flags ([True/False, [1,2,3,...]]), i.e. sort out what part to repeat and what not.
#        repeat_indices = np.nonzero(matrix[:,10])[0]
#        temp_index_list = []
#        repeat_blocks = []
#        for index in range(matrix.shape[0]):
#            current_flag = index in repeat_indices
#            if index == 0:
#                last_flag = current_flag
#            if (current_flag != last_flag):
#                repeat_blocks.append([last_flag, temp_index_list])
#                temp_index_list = [index]
#            else:
#                temp_index_list.append(index)
#            last_flag = current_flag
#        repeat_blocks.append([current_flag, temp_index_list])
#
#        # Run through the matrix according to the indices in "repeat_blocks" and create the sequence.
#        for rep_flag, indices in repeat_blocks:
#            # create the first iteration of the current block set
#            # get active channel lists for the current block set
#            active_channels = []
#            for row in matrix[indices]:
#                active_channels.append(np.nonzero(row[0:8])[0])
#            # get starting lengths for the current block set
#            block_length = matrix[indices, 8]
#            # check if the current block set is set as repeat.
#            if rep_flag:
#                # get increment values for the current block set
#                increments = matrix[indices, 9]
#                # repeat the current block set and increment each individual block length
#                for rep in range(repetitions):
#                    for blocknum, channel_list in enumerate(active_channels):
#                        # calculate current block length for this repetition
#                        temp_length = block_length[blocknum] + (rep * increments[blocknum])
#                        # append the list of active channels and the current block length to the sequence
#                        sequence.append([channel_list, temp_length])
#            else:
#                # run through the current blocks and append them to the sequence
#                for blocknum, channel_list in enumerate(active_channels):
#                    sequence.append([channel_list, block_length[blocknum]])
#        return sequence

    def encode_matrix(self, matrix, repetitions):
        ''' Encodes the current matrix coming from the GUI into a proper pulse sequence with blocks etc.
        '''
        # Create empty sequence
        sequence = []

        # First create a nested list "repeat_blocks" of block indices with
        # corresponding repeat flags ([True/False, [1,2,3,...]]), i.e. sort out
        # what part to repeat and what not.

        repeat_indices = np.nonzero(matrix[:,10])[0]# Return the INDICES of
                                                    # the elements in
                                                    # matrix[:,10] that are
                                                    # non-zero.
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

        # Run through the matrix according to the indices in "repeat_blocks"
        # and create the sequence.
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
                        # create empty dictionary for this block
                        temp_dict = {}
                        # calculate current block length for this repetition and write into the dictionary
                        temp_dict['length'] = block_length[blocknum] + (rep * increments[blocknum])
                        # write active channel list into dictionary and set is_laser flag
                        temp_dict['active_channels'] = channel_list
                        if (0 in channel_list):
                            temp_dict['is_laser'] = True
                        else:
                            temp_dict['is_laser'] = False
                        # append the list of active channels and the current block length to the sequence
                        sequence.append(temp_dict)
            else:
                # run through the current blocks and append them to the sequence
                for blocknum, channel_list in enumerate(active_channels):
                    # create empty dictionary for this block
                    temp_dict = {}
                    # set length in the dictionary
                    temp_dict['length'] = block_length[blocknum]
                    # write active channels into dictionary
                    temp_dict['active_channels'] = channel_list
                    # set is_laser flag in the dictionary
                    if (0 in channel_list):
                        temp_dict['is_laser'] = True
                    else:
                        temp_dict['is_laser'] = False
                    sequence.append(temp_dict)
        return sequence


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


    def update_sequence_parameters(self, matrix, repetitions):
        """ Calulate sequence


        This method calculates all sequence parameters from a
        given matrix and number of repetitions.
        """
        # Calculate sequence length in bins.
        # Calculate the sum over all "length" entries
        sequence_length_bins = np.sum(matrix[:,8])
        # Add the increments and repetitions when the repeat-flag is checked
        for length, increment, flag in matrix[:,8:11]:
            if flag:
                for i in range(repetitions-1):
                    sequence_length_bins += length + (increment*(i+1))

        # Calculate sequence length in ms
        sequence_length_ms = sequence_length_bins / (self._pg_frequency_MHz * 1000.)

        # Calculate number of laser pulses
        number_of_lasers = 0
        # iterate through all row indices with laser channel (chnl 0) set to True (or 1)
        for row_number in np.nonzero(matrix[:,0])[0]:
            # check if the current laser pulse is in a repeat block
            if matrix[row_number, 10]:
                number_of_lasers += repetitions
            else:
                number_of_lasers += 1

        # find the rows with "use_as_tau" enabled.
        tau_rows = np.nonzero(matrix[:,11])[0]
        # Check if just one row is set as tau
        if tau_rows.size > 1:
            print('Uuuuuh, big mistake! Use only one row as tau!')
        if tau_rows.size == 0:
            print('No block set as tau. Using laser pulses as index.')
            tau_vector = np.array(range(number_of_lasers))
        else:
            tau_row_index = tau_rows[0]
            # create tau_vector
            if matrix[tau_row_index,10]:
                tau_vector = np.zeros(repetitions)
                for i in range(repetitions):
                    start_length = matrix[tau_row_index,8]
                    tau_increment = matrix[tau_row_index,9]
                    tau_vector[i] = (start_length + (i * tau_increment)) * (1000. / self._pg_frequency_MHz)
            else:
                tau_vector = np.array([matrix[tau_row_index,8]]) * (1000. / self._pg_frequency_MHz)

        # use the longest laser pulse as laser_length
        laser_indices = np.nonzero(matrix[:,0])[0]
        max_laser_length = np.max(matrix[laser_indices, 8])
        laser_length_vector = np.empty(number_of_lasers)
        laser_length_vector.fill(max_laser_length)

        # update current parameters
        self._current_sequence_parameters['length_bins'] = sequence_length_bins
        self._current_sequence_parameters['length_ms'] = sequence_length_ms
        self._current_sequence_parameters['number_of_lasers'] = number_of_lasers
        self._current_sequence_parameters['tau_vector'] = tau_vector
        self._current_sequence_parameters['laser_length_vector'] = laser_length_vector
        self._current_sequence_parameters['repetitions'] = repetitions
        self._current_matrix = matrix
        return


    def get_sequence(self, name):
        """ Retrieve the sequence for the corresponding name.

        This method returns for a sequence with name "name"
        in all saved sequences and returns it if found.
        """
        sequence = None
        if (name in self._saved_sequences):
            sequence = self._saved_sequences[name]
        return sequence


    def get_sequence_parameters(self, name):
        """ Retrieve

        This method searches for a sequence with name "name" in all saved sequences and returns the parameters dictionary
        """
        if (name in self._saved_sequence_parameters):
            parameter_dict = self._saved_sequence_parameters[name].copy()
        return parameter_dict


    def get_sequence_names(self):
        names = list(self._saved_sequences.keys())
        return names


    def get_binwidth(self):
        binwidth_ns = 1000./self.pg_frequency_MHz
        return binwidth_ns


#    def get_number_of_laser_pulses(self, matrix, repetitions):
#        ''' returns the number of laser pulses in given sequence generator matrix
#        '''
#        number_of_lasers = 0
#        # iterate through all row indices with laser channel (chnl 0) set to True (or 1)
#        for row_number in np.nonzero(matrix[:,0])[0]:
#            # check if the current laser pulse is in a repeat block
#            if matrix[row_number, 10]:
#                number_of_lasers += repetitions
#            else:
#                number_of_lasers += 1
#        return number_of_lasers


#    def get_tau_vector(self):
#        tau_vector = np.array(range(100))
#        return tau_vector


#    def get_laser_length(self):
#        laser_length = 3800 # 4 us
#        return laser_length

