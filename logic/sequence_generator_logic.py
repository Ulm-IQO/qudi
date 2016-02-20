# -*- coding: utf-8 -*-

"""
This file contains the QuDi hardware interface dummy for pulsing devices.

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

Copyright (C) 2015 Nikolas Tomek nikolas.tomek@uni-ulm.de
Copyright (C) 2015 Alexander Stark alexander.stark@uni-ulm.de
"""

import numpy as np
import pickle
import os
import sys
import time

from logic.generic_logic import GenericLogic
from logic.sampling_functions import SamplingFunctions
from pyqtgraph.Qt import QtCore
from collections import OrderedDict

class Pulse_Block_Element(object):
    """ Object representing a single atomic element in a pulse block.

    This class can build waiting times, sine waves, etc. The pulse block may
    contain many Pulse_Block_Element Objects. These objects can be displayed in
    a GUI as single rows of a Pulse_Block.
    """
    def __init__(self, init_length_bins, analogue_channels, digital_channels,
                 increment_bins = 0, pulse_function = None,
                 marker_active = None, parameters={}, use_as_tau=False):
        """ The constructor for a Pulse_Block_Element needs to have:

        @param init_length_bins: int, an initial length of a bins, this
                                 parameters should not be zero but must have a
                                 finite value.
        @param analogue_channels: int, number of analogue channels
        @param digital_channels: int, number of digital channels
        @param increment_bins: int, the number which will be incremented during
                               each repetition of this object
        @param pulse_function: sting, name of the sampling function how to
                               alter the points, the name of the function will
                               be one of the sampling functions
        @param marker_active: list of digital channels, which are for the
                              length of this Pulse_Block_Element are set either
                              to True (high) or to False (low). The length of
                              the marker list depends on the number of (active)
                              digital channels. For 4 digital channel it may
                              look like:
                              [True, False, False, False]
        @param parameters: a list of dictionaries. The number of dictionaries
                           depends on the number of analogue channels. The
                           number of entries within a dictionary depends on the
                           chosen sampling function. The key words of the
                           dictionary for the parameters will be those of the
                           sampling functions.
        @param use_as_tau: bool, indicates, whether the set length should
                           be used as tau (i.e. the parameter for the x axis)
                           for the later plot in the analysis.
        """


        self.init_length_bins   = init_length_bins
        self.analogue_channels  = analogue_channels
        self.digital_channels   = digital_channels
        self.increment_bins     = increment_bins
        self.pulse_function     = pulse_function
        self.markers_on         = marker_active
        self.parameters         = parameters
        self.use_as_tau         = use_as_tau


class Pulse_Block(object):
    """ Represents one collection of Pulse_Block_Elements which is called a
        Pulse_Block.
    """

    def __init__(self, name, element_list, num_laser_pulses=None):
        """ The constructor for a Pulse_Block needs to have:

        @param name: str, chosen name for the Pulse_Block
        @param element_list: list, which contains the Pulse_Block_Element
                             Objects forming a Pulse_Block, e.g.
                             [Pulse_Block_Element, Pulse_Block_Element, ...]
        """
        self.name = name
        self.element_list = element_list
        self.num_laser_pulses = num_laser_pulses
        self.refresh_parameters()

    def refresh_parameters(self):
        """ Initialize the parameters which describe this Pulse_Block object.

        The information is gained from all the Pulse_Block_Element objects,
        which are attached in the element_list.
        """

        # the Pulse_Block parameter
        self.init_length_bins = 0
        self.increment_bins = 0
        self.analogue_channels = 0
        self.digital_channels = 0


        # calculate the tau value for the whole block. Basically sum all the
        # init_length_bins which have the use_as_tau attribute set to True.
        self.block_tau = 0

        # make the same thing for the increment, to obtain the total increment
        # number for the block. This facilitates in calculating the tau list.
        self.block_tau_increment = 0

        for elem in self.element_list:
            self.init_length_bins += elem.init_length_bins
            self.increment_bins += elem.increment_bins

            if elem.use_as_tau:
                self.block_tau = self.block_tau + elem.init_length_bins
                self.block_tau_increment = self.block_tau_increment + elem.increment_bins

            if elem.analogue_channels > self.analogue_channels:
                self.analogue_channels = elem.analogue_channels
            if elem.digital_channels > self.digital_channels:
                self.digital_channels = elem.digital_channels

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
    """ Represents a collection of Pulse_Block objects which is called a
        Pulse_Block_Ensemble.

    This object is used as a construction plan to create one sampled file.
    """

    def __init__(self, name, block_list, tau_array, number_of_lasers,
                 rotating_frame=True):
        """ The constructor for a Pulse_Block_Ensemble needs to have:

        @param name: name: str, chosen name for the Pulse_Block_Ensemble
        @param block_list: list, which contains the Pulse_Block Objects with
                           their number of repetitions, e.g.
                           [(Pulse_Block, repetitions), (Pulse_Block, repetitions), ...])
        #FIXME: Here I am not quite sure about the description for the tau_array.
        @param tau_array:
        @param number_of_lasers: int, number of laser pulses
        @param rotating_frame: bool, indicates whether the phase should be
                               preserved for all the functions.
        """


        self.name = name                        # block name
        self.block_list = block_list        # List of AWG_Block objects with repetition number
        self.tau_array = tau_array
        self.number_of_lasers = number_of_lasers
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


class SequenceGeneratorLogic(GenericLogic, SamplingFunctions):
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

        # Get all the attributes from the SamplingFunctions module:
        SamplingFunctions.__init__(self)

        self.sample_rate = 25e9
        self.pp_voltage = 0.5
        self.analogue_channels = 2
        self.digital_channels = 4
        self.current_block = None
        self.current_ensemble = None
        self.current_sequence = None

        # The string names of the created Pulse_Block objects are saved here:
        self.saved_pulse_blocks = []
        # The string names of the created Pulse_Block_Ensemble objects are
        # saved here:
        self.saved_pulse_block_ensembles = []
        # The string names of the created Sequence objects are saved here:
        self.saved_sequences = []

        if 'pulsed_file_dir' in config.keys():
            self.pulsed_file_dir = config['pulsed_file_dir']

            if not os.path.exists(self.pulsed_file_dir):

                homedir = self.get_home_dir()
                self.pulsed_file_dir =os.path.join(homedir, 'pulsed_files\\')
                self.logMsg('The directort defined in "pulsed_file_dir" in the'
                        'config for SequenceGeneratorLogic class does not '
                        'exist!\nThe default home directory\n{0}\n will be '
                        'taken instead.'.format(self.pulsed_file_dir),
                        msgType='warning')
        else:
            homedir = self.get_home_dir()
            self.pulsed_file_dir = os.path.join(homedir, 'pulsed_files\\')
            self.logMsg('No directory with the attribute "pulsed_file_dir"'
                        'is defined for the SequenceGeneratorLogic!\nThe '
                        'default home directory\n{0}\n will be taken '
                        'instead.'.format(self.pulsed_file_dir),
                        msgType='warning')


        self.block_dir = self._get_dir_for_name('pulse_block_objects')
        self.ensemble_dir = self._get_dir_for_name('pulse_ensemble_objects')
        self.sequence_dir = self._get_dir_for_name('sequence_objects')

        # =============== Setting the additional parameters ==================

        #FIXME: For now on, this settings will be done here, but a better
        #       and more intuitive solution has to be found for the future!

        # Definition of this parameter. See fore more explanation in file
        # sampling_functions.py
        length_def = {'unit': 's', 'init_val': 0.0, 'min': 0.0, 'max': np.inf,
                      'view_stepsize': 1e-9, 'dec': 8, 'unit_prefix': 'n'}

        rep_def = {'unit': '#', 'init_val': 0, 'min': 0, 'max': (2**31 -1),
                   'view_stepsize': 1, 'dec': 0, 'unit_prefix': ''}
        bool_def = {'unit': 'bool', 'init_val': 0, 'min': 0, 'max': 1,
                   'view_stepsize': 1, 'dec': 0, 'unit_prefix': ''}

        # make a parameter constraint dict for the additional parameters of the
        # Pulse_Block_Ensemble objects:
        self._add_pbe_param = OrderedDict()
        self._add_pbe_param['length'] = length_def
        self._add_pbe_param['increment'] = length_def
        self._add_pbe_param['use as tau?'] = bool_def
        # self._add_pbe_param['repeat?'] = bool_def


        self._add_pb_param = OrderedDict()
        self._add_pb_param['repetition'] = rep_def
        # =====================================================================

        # An abstract dictionary, which tells the logic the configuration of a
        # Pulse_Block_Element, i.e. how many parameters are used for a
        # Pulse_Block_Element (pbe) object. In principle, the way how the GUI
        # is displaying the pbe object should be irrelavent for the logic.
        # That configuration here will actually not be taken but overwritten,
        # depending on the attached hardware. It serves as an example for the
        # logic to show how the cfg_param_pbe is looking like.

        self.cfg_param_pbe = {'function_0':    0, 'frequency1_0':  1,
                                   'amplitude1_0':  2, 'phase1_0':      3,
                                   'digital_0':     4, 'digital_1':     5,
                                   'function_1':    6, 'frequency1_1':  7,
                                   'amplitude1_1':  8, 'phase1_1':      9,
                                   'digital_2':    10, 'digital_3':     11,
                                   'length':       12, 'increment':     13}

        # the same idea for Pulse_Block (pb) objects:
        self.cfg_param_pb = {'pulse_block' :    0, 'length':    1}

    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """
        self.refresh_block_list()
        self.refresh_ensemble_list()
        self.refresh_sequence_list()

        self._pulse_generator_device = self.connector['in']['pulser']['object']

        self.set_pp_voltage(0, self._pulse_generator_device.get_pp_voltage(0))
        self.set_pp_voltage(1, self._pulse_generator_device.get_pp_voltage(1))


        # Append to this list all methods, which should be used for automated
        # parameter generation.
        # ALL THE ARGUMENTS IN THE METHODS MUST BE ASSIGNED TO DEFAULT VALUES!
        # Otherwise it is not possible to determine the proper viewbox.
        config = self.getConfiguration()
        self.prepared_method_list=[]
        if 'prepared_methods' in config.keys():
            prep_methods_list = config['prepared_methods']
            self.prepared_method_list = [None]*len(prep_methods_list)

            # evaluate the name of the method to get the reference to it.
            for index, method in enumerate(prep_methods_list):
                self.prepared_method_list[index] = eval('self.'+method)

        else:
            self.logMsg('None prepared Methods are chosen, therefore none will'
                        ' be displayed!', msgType='status')


    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.
        """
        pass

    def _get_dir_for_name(self, name):
        """ Get the path to the pulsed sub-directory 'name'.

        @param name: string, name of the folder
        @return: string, absolute path to the directory with folder 'name'.
        """

        path = self.pulsed_file_dir + name
        if not os.path.exists(path):
            os.makedirs(os.path.abspath(path))

        return os.path.abspath(path) + '\\'


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

    def get_add_pbe_param(self):
        """ Return the additional parameters for Pulse_Block_Element objects.

        @return: dict with the configurations for the additional parameters.
        """

        return self._add_pbe_param

    def get_add_pb_param(self):
        """ Return the additional parameters for Pulse_Block objects.

        @return: dict with the configurations for the additional parameters.
        """

        return self._add_pb_param


    def set_sample_rate(self, freq_Hz):
        """ Sets the sampling frequency of the pulse generator device in Hz.

        Additionally this value is updated in this logic.
        """

        self._pulse_generator_device.set_sample_rate(freq_Hz)
        self.sample_rate = freq_Hz
        return 0

    def set_pp_voltage(self, channel, voltage):
        """ Sets the peak-to-peak output voltage of the pulse generator device.

        Additionally this value is updated in this logic. Only of importance
        if the device has analogue channels with adjustable
        peak-to-peak voltage.
        """

        self._pulse_generator_device.set_pp_voltage(channel, voltage)
        self.pp_voltage = voltage
        return 0

    def set_active_channels(self, digital, analogue):
        """ Sets the number of active channels in the pulse generator device.

        Additionally the variables which hold this values are updated in the
        logic.
        """

        self._pulse_generator_device.set_active_channels(digital, analogue)
        self.analogue_channels = analogue
        self.digital_channels = digital
        return 0

    def load_asset(self, name, channel = None):
        assets_on_device = self._pulse_generator_device.uploaded_assets_list
        if name in assets_on_device:
            self._pulse_generator_device.load_asset(name, channel)

# -----------------------------------------------------------------------------
#                    BEGIN sequence/block generation
# -----------------------------------------------------------------------------

    def save_block(self, name, block):
        """ Serialize a Pulse_Block object to a *.blk file.

        @param name: string, name of the block to save
        @param block: Pulse_Block object which will be serialized
        """

        # TODO: Overwrite handling
        block.name = name
        with open(self.block_dir + name + '.blk', 'wb') as outfile:
            pickle.dump(block, outfile)
        self.refresh_block_list()
        self.current_block = block
        self.logMsg('Pulse_Block object "{0}" serialized to harddisk in:\n'
                    '{1}'.format(name, self.block_dir), msgType='status',
                    importance=0)
        return

    def get_block(self, name, set_as_current_block=False):
        """ Deserialize a *.blk file into a Pulse_Block object.

        @param name: string, name of the *.blk file.
        @param set_as_current_ensemble: bool, set the retained Pulse_Block
               object as the current ensemble.

        @return: Pulse_Block object which belongs to the given name.
        """

        if name in self.saved_pulse_blocks:
            with open(self.block_dir + name + '.blk', 'rb') as infile:
                block = pickle.load(infile)
        else:
            self.logMsg('The Pulse_Block object with name "{0}" could not be '
                        'found and serialized in:\n'
                        '{1}'.format(name, self.block_dir), msgType='warning')
            block = None

        if set_as_current_block:
            self.current_block = block
        return block

    def delete_block(self, name):
        """ Remove the serialized object "name" from the block list and HDD.

        @param name: string, name of the Pulse_Block object to be removed.
        """

        if name in self.saved_pulse_blocks:
            os.remove(self.block_dir + name + '.blk')
            self.refresh_block_list()
        else:
            self.logMsg('Pulse_Block object with name "{0}" not found '
                        'in\n{1}\nTherefore nothing is '
                        'removed.'.format(name, self.block_dir),
                        msgType='warning')

        return

    def refresh_block_list(self):
        ''' refresh the list of available (saved) blocks
        '''

        block_files = [f for f in os.listdir(self.block_dir) if '.blk' in f]
        blocks = []
        for filename in block_files:
            blocks.append(filename[:-4])
        blocks.sort()
        self.saved_pulse_blocks = blocks
        self.signal_block_list_updated.emit()
        return


    def save_ensemble(self, name, ensemble):
        ''' saves a block ensemble generated by the block ensemble editor into a file
        '''
        # TODO: Overwrite handling
        ensemble.name = name
        with open(self.ensemble_dir + name + '.ens', 'wb') as outfile:
            pickle.dump(ensemble, outfile)
        self.refresh_ensemble_list()
        self.current_ensemble = ensemble
        return

    def get_ensemble(self, name, set_as_current_ensemble=False):
        """ Deserialize a *.ens file into a Pulse_Block_Ensemble object.

        @param name: string, name of the *.ens file.
        @param set_as_current_ensemble: bool, set the retained
               Pulse_Block_Ensemble object as the current ensemble.

        @return: Pulse_Block_Ensemble object which belongs to the given name.
        """

        if name in self.saved_pulse_block_ensembles:
            with open(self.ensemble_dir + name + '.ens', 'rb') as infile:
                ensemble = pickle.load(infile)
        else:
            self.logMsg('The Pulse_Block_Ensemble object with name "{0}" '
                        'could not be found and serialized in:\n'
                        '{1}'.format(name, self.ensemble_dir),
                        msgType='warning')

            ensemble = None

        if set_as_current_ensemble:
            self.current_ensemble = ensemble

        return ensemble

    def delete_ensemble(self, name):
        ''' remove the ensemble "name" from the ensemble list and HDD
        '''
        if name in self.saved_pulse_block_ensembles:
            os.remove(self.ensemble_dir + name + '.ens')
            self.refresh_ensemble_list()
        else:
            # TODO: implement proper error
            print('Error: No ensemble with name "' + name + '" in saved ensembles.')
        return

    def refresh_ensemble_list(self):
        ''' Refresh the list of available (saved) ensembles.
        '''
        ensemble_files = [f for f in os.listdir(self.ensemble_dir) if '.ens' in f]
        ensembles = []
        for filename in ensemble_files:
            ensembles.append(filename[:-4])
        ensembles.sort()
        self.saved_pulse_block_ensembles = ensembles
        self.signal_ensemble_list_updated.emit()
        return


    def save_sequence(self, name, sequence):
        ''' saves a sequence generated by the sequence editor into a file
        '''
        # TODO: Overwrite handling
        sequence.name = name
        with open(self.sequence_dir + name + '.se', 'wb') as outfile:
            pickle.dump(sequence, outfile)
        self.refresh_sequence_list()
        self.current_sequence = sequence
        return

    def get_sequence(self, name, set_as_current_sequence=False):
        """ Deserialize a *.se file into a Sequence object.

        @param name: string, name of the *.se file.
        @param set_as_current_sequence: bool, set the retained
               Sequence object as the current ensemble.

        @return: Sequence object which belongs to the given name.
        """

        if name in self.saved_sequences:
            with open(self.sequence_dir + name + '.se', 'rb') as infile:
                sequence = pickle.load(infile)
        else:
            self.logMsg('The Sequence object with name "{0}" could not be '
                        'found and serialized in:\n'
                        '{1}'.format(name, self.sequence_dir),
                        msgType='warning')
            sequence = None

        if set_as_current_sequence:
            self.current_sequence = sequence

        return sequence

    def delete_sequence(self, name):
        ''' remove the sequence "name" from the sequence list and HDD
        '''
        if name in self.saved_sequences:
            os.remove(self.sequence_dir + name + '.se')
            self.refresh_sequence_list()
        else:
            # TODO: implement proper error
            print('Error: No sequence with name "' + name + '" in saved sequences.')
        return

    def refresh_sequence_list(self):
        ''' refresh the list of available (saved) sequences
        '''
        sequence_files = [f for f in os.listdir(self.sequence_dir) if '.se' in f]
        sequences = []
        for filename in sequence_files:
            sequences.append(filename[:-4])
        sequences.sort()
        self.saved_sequences = sequences
        self.signal_sequence_list_updated.emit()
        return


    # =========================================================================
    # Depricated method, will be remove soon.

    def generate_block(self, name, block_matrix):
        """
        @param block_matrix: stuctured numpy array
        Generates a Pulse_Block object out of the corresponding editor table/matrix.
        """
        # each line in the matrix corresponds to one Pulse_Block_Element
        # Here these elements are created
        analogue_func = [None]*self.analogue_channels
        digital_flags = [None]*self.digital_channels

        # make an array where the length of each Pulse_Block_Element will be
        # converted to number of bins:
        lengths = np.array(
            [np.round( x[self.cfg_param_pbe['length']]/(1e9/self.sample_rate))
            for x in block_matrix ])

        # make an array where the increment value of each Pulse_Block_Element
        #  will be converted to number of bins:
        increments = np.array(
            [ np.round( x[self.cfg_param_pbe['increment']]/(1e9/self.sample_rate))
            for x in block_matrix])

        for chnl_num in range(self.analogue_channels):
            # Save all function names for channel number "chnl_num" in one
            # column of "analogue_func". Also convert them to strings
            analogue_func[chnl_num] = np.array(
                [ x[self.cfg_param_pbe['function_'+str(chnl_num)]].decode('utf-8')
                for x in block_matrix]  )

        # convert to numpy ndarray
        analogue_func = np.array(analogue_func)


        for chnl_num in range(self.digital_channels):
            # Save the marker flag for channel number "chnl_num" in one column
            # of "digital_flags". Also convert them to bools
            digital_flags[chnl_num] = np.array(
                [bool(x[self.cfg_param_pbe['digital_'+str(chnl_num)]])
                for x in block_matrix ])

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
                        param_dict[param] = 1e6*block_matrix[elem_num][self.cfg_param_pbe[param+'_'+str(chnl_num)]]
                    else:
                        param_dict[param] = block_matrix[elem_num][self.cfg_param_pbe[param+'_'+str(chnl_num)]]
                elem_parameters[chnl_num] = param_dict

            block_element = Pulse_Block_Element(
                                init_length_bins=elem_length,
                                analogue_channels=len(analogue_func),
                                digital_channels=len(digital_flags),
                                increment_bins=elem_incr,
                                pulse_function=elem_func,
                                marker_active=elem_marker,
                                parameters=elem_parameters)

            block_element_list[elem_num] = block_element

        # generate the Pulse_Block() object
        block = Pulse_Block(name, block_element_list)
        # save block to a file
        self.save_block(name, block)
        # set current block
        self.current_block = block
        return

    # =========================================================================

    def generate_pulse_block_object(self, pb_name, block_matrix, num_laser_pulses):
        """ Generates from an given table block_matrix a block_object.

        @param pb_name: string, Name of the created Pulse_Block Object
        @param block_matrix: structured np.array, matrix, in which the
                             construction plan for Pulse_Block_Element objects
                             are displayed as rows.

        Three internal dict where used, to get all the needed information about
        how parameters, functions are defined (_add_pbe_param,func_config and
        _unit_prefix).
        The dict cfg_param_pbe (configuration parameter declaration dict for
        Pulse_Block_Element) stores how the objects are appearing in the GUI.
        This dict enables the proper access to the desired element in the GUI.
        """

        # list of all the pulse block element objects
        pbe_obj_list = [None]*len(block_matrix)

        analogue_channels=self.analogue_channels
        digital_channels=self.digital_channels

        for row_index, row in enumerate(block_matrix):

            #FIXME: The output parameters are now in SI units. A conversion to
            #       bins is still needed.

            # check how length is displayed and convert it to bins:
            length_time= row[self.cfg_param_pbe['length']]
            init_length_bins=int(np.round(length_time*self.sample_rate))

            # check how increment is displayed and convert it to bins:
            increment_time=row[self.cfg_param_pbe['increment']]
            increment_bins= int(np.round(increment_time*self.sample_rate))

            # get the dict with all possible functions and their parameters:
            func_dict = self.get_func_config()

            # get the proper pulse_functions and its parameters:
            pulse_function=[None]*self.analogue_channels

            parameter_list =[None]*self.analogue_channels

            for num in range(self.analogue_channels):
                pulse_function[num] = row[self.cfg_param_pbe['function_'+str(num)]].decode('UTF-8')

                # search for this function in the dictionary and get all the
                # parameter with their names in list:
                param_dict = func_dict[pulse_function[num]]

                parameters = {}
                for entry in list(param_dict):

                    # Obtain how the value is displayed in the table:
                    param_value = row[self.cfg_param_pbe[entry+'_'+str(num)]]

                    parameters[entry] = param_value
                parameter_list[num] = parameters

            marker_active = [None]*self.digital_channels
            for num in range(self.digital_channels):
                marker_active[num] = bool(row[self.cfg_param_pbe['digital_'+str(num)]])

            # create here actually the object with all the obtained information:

            pbe_obj_list[row_index] = Pulse_Block_Element(
                        init_length_bins=init_length_bins,
                        analogue_channels=analogue_channels,
                        digital_channels=digital_channels,
                        increment_bins=increment_bins,
                        pulse_function=pulse_function,
                        marker_active=marker_active,
                        parameters=parameter_list)

        pb_obj = Pulse_Block(pb_name, pbe_obj_list, num_laser_pulses)
        self.save_block(pb_name, pb_obj)
        self.current_block = pb_obj


    def generate_pulse_block_ensemble(self, ensemble_name, ensemble_matrix,
                                      rotating_frame=True):
        """
        Generates from an given table ensemble_matrix a ensemble object.

        @param ensemble_name: string, Name of the created Pulse_Block_Ensemble
                              Object
        @param ensemble_matrix: structured np.array, matrix, in which the
                                construction plan for Pulse_Block objects
                                are displayed as rows.
        @param rotating_frame: bool, optional, whether the phase preservation
                               is mentained throughout the sequence.

        Three internal dict where used, to get all the needed information about
        how parameters, functions are defined (_add_pb_param)

        The dict cfg_param_pb (configuration parameter declaration dict for
        Pulse_Block) stores how the objects are appearing in the GUI.
        This dict enables the proper access to the desired element in the GUI.
        """


        # list of all the pulse block element objects
        pb_obj_list = [None]*len(ensemble_matrix)

        #FIXME: Obtain the tau_list size before, and do not append to it.
        # it is not easy to estimate the tau_list. Therefore follow the simple
        # append to list approach. Later a nicer way can be implemented.
        tau_list = []

        # to make a resonable tau list, the last biggest tau value after all
        # the repetitions of a block is used as the offset_time for the next
        # block.
        offset_tau_bin = 0
        num_laser_pulse = 0

        for row_index, row in enumerate(ensemble_matrix):

            pulse_block_name = row[self.cfg_param_pb['pulse_block']].decode('UTF-8')
            pulse_block_reps = row[self.cfg_param_pb['repetition']]

            block = self.get_block(pulse_block_name)

            for num in range(pulse_block_reps+1):
                tau_list.append(offset_tau_bin + block.init_length_bins + num*block.increment_bins)

            num_laser_pulse =  num_laser_pulse + block.num_laser_pulses*(pulse_block_reps+1)

            # for the next block, add the biggest time as offset_tau_bin.
            # Otherwise the tau_list will be a mess.
            offset_tau_bin = offset_tau_bin + block.init_length_bins + (pulse_block_reps)*block.increment_bins
            pb_obj_list[row_index] = (block, pulse_block_reps)




        pulse_block_ensemble = Pulse_Block_Ensemble(name=ensemble_name,
                                              block_list=pb_obj_list,
                                              tau_array=tau_list,
                                              number_of_lasers=num_laser_pulse,
                                              rotating_frame=rotating_frame)
        # save block
        # self.save_block(name, block)
        # save ensemble
        self.save_ensemble(ensemble_name, pulse_block_ensemble)
        # set current block ensemble
        self.current_ensemble = pulse_block_ensemble





    def generate_sequence(self, sequence_matrix):
        """
        Generates a Pulse_Sequence object out of the corresponding editor
        table/matrix. Creates a whole new structure of Block_Elements, Blocks
        and Block_Ensembles so that the phase of the seqeunce is preserved.
        NOT EASY!
        """
        return
#-------------------------------------------------------------------------------
#                    END sequence/block generation
#-------------------------------------------------------------------------------


#-------------------------------------------------------------------------------
#                    BEGIN sequence/block sampling
#-------------------------------------------------------------------------------
    def sample_sequence(self, sequence):
        """
        Samples the sequence to obtain the needed waveforms.
        """
        pass

    def sample_ensemble(self, ensemble_name, write_to_file = True, chunkwise = True):
        """

        @param ensemble_name:
        @param write_to_file:
        @param chunkwise:
        @return:
        """
        start_time = time.time()
        # get ensemble
        ensemble = self.get_ensemble(ensemble_name)
        # Ensemble parameters to determine the shape of sample arrays
        number_of_samples = ensemble.length_bins
        ana_channels = ensemble.analogue_channels
        dig_channels = ensemble.digital_channels

        # The time bin offset for each element to be sampled to preserve rotating frame.
        bin_offset = 0

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
            analogue_samples = np.empty([ana_channels, number_of_samples], dtype = 'float32')
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
                    markers_on = block_element.markers_on
                    pulse_function = block_element.pulse_function
                    element_length_bins = init_length_bins + (rep_no*increment_bins)

                    time_arr = (bin_offset + np.arange(element_length_bins)) / self.sample_rate

                    if chunkwise and write_to_file:
                        element_count += 1
                        if element_count == number_of_elements:
                            is_last_chunk = True

                        analogue_samples = np.empty([ana_channels, element_length_bins], dtype = 'float32')
                        digital_samples = np.empty([dig_channels, element_length_bins], dtype = bool)

                        for i, state in enumerate(markers_on):
                            digital_samples[i] = np.full(element_length_bins, state, dtype = bool)
                        for i, func_name in enumerate(pulse_function):
                            analogue_samples[i] = np.float32(self._math_func[func_name](time_arr, parameters[i]))

                        self._pulse_generator_device.write_chunk_to_file(ensemble.name, analogue_samples, digital_samples, number_of_samples, is_first_chunk, is_last_chunk, self.sample_rate, self.pp_voltage)
                        is_first_chunk = False
                    else:
                        for i, state in enumerate(markers_on):
                            digital_samples[i, entry_ind:entry_ind+element_length_bins] = np.full(element_length_bins, state, dtype = bool)
                        for i, func_name in enumerate(pulse_function):
                            analogue_samples[i, entry_ind:entry_ind+element_length_bins] = np.float32(self._math_func[func_name](time_arr, parameters[i]))

                        entry_ind += element_length_bins

                    if ensemble.rotating_frame:
                        bin_offset += element_length_bins

        if not write_to_file:
            print('Time needed for sampling only: ', time.time()-start_time, ' sec')
            return analogue_samples, digital_samples
        elif chunkwise:
            print('Time needed for write chunkwise: ', time.time()-start_time, ' sec')
            return
        else:
            self._pulse_generator_device.write_to_file(ensemble.name, analogue_samples, digital_samples, self.sample_rate, self.pp_voltage)
            print('Time needed for write in whole: ', time.time()-start_time, ' sec')
            return


    def upload_file(self, name):
        self._pulse_generator_device.upload_asset(name)
        pass

    # def _sample_ensemble(self, ensemble):
    #     """
    #     Calculates actual sample points given a Pulse_Block_Ensemble object.
    #
    #     @param Pulse_Block_Ensemble() ensemble: Block ensemble to be sampled.
    #
    #     @return numpy_ndarrays[channel, sample]: The sampled analogue and digital channels
    #     """
    #     arr_len = np.round(ensemble.length_bins*1.01)
    #     ana_channels = ensemble.analogue_channels
    #     dig_channels = ensemble.digital_channels
    #
    #     sample_arr = np.empty([ana_channels, arr_len], dtype = 'float32')
    #     marker_arr = np.empty([dig_channels, arr_len], dtype = bool)
    #
    #     entry = 0
    #     bin_offset = 0
    #     for block, reps in ensemble.block_list:
    #         for rep_no in range(reps+1):
    #             temp_sample_arr, temp_marker_arr = self._sample_block(block, rep_no, bin_offset, ensemble.rotating_frame)
    #             temp_len = temp_sample_arr.shape[1]
    #             sample_arr[:, entry:temp_len+entry] = temp_sample_arr
    #             marker_arr[:, entry:temp_len+entry] = temp_marker_arr
    #             entry += temp_len
    #             if ensemble.rotating_frame:
    #                 bin_offset = entry
    #     # slice the sample array to cut off uninitialized entrys at the end
    #     return sample_arr[:, :entry], marker_arr[:, :entry]

    # def _sample_block(self, block, rotating_frame = True):
    #     """
    #     Calculates actual sample points given a Block.
    #
    #     @param Pulse_Block() block: Block to be sampled.
    #     @return:
    #     """
    #     number_of_samples = block.init_length_bins
    #     ana_channels = block.analogue_channels
    #     dig_channels = block.digital_channels
    #
    #     # Allocate sample arrays
    #     analogue_samples = np.empty([ana_channels, number_of_samples], dtype = 'float32')
    #     digital_samples = np.empty([dig_channels, number_of_samples], dtype = bool)
    #
    #     bin_offset = 0
    #     entry = 0
    #     for block_element in block.element_list:
    #         parameters = block_element.parameters
    #         element_length_bins = block_element.init_length_bins
    #         markers_on = block_element.markers_on
    #         pulse_function = block_element.pulse_function
    #
    #         time_arr = (bin_offset + np.arange(element_length_bins)) / self.sample_rate
    #
    #         for i, state in enumerate(markers_on):
    #             digital_samples[i, entry:entry+element_length_bins] = np.full(element_length_bins, state, dtype = bool)
    #         for i, func_name in enumerate(pulse_function):
    #             analogue_samples[i, entry:entry+element_length_bins] = np.float32(self._math_func[func_name](time_arr, parameters[i]))
    #
    #         entry += element_length_bins
    #         if rotating_frame:
    #             bin_offset = entry
    #     return analogue_samples, digital_samples

    # def _sample_block(self, block, iteration_no = 0, bin_offset = 0, rotating_frame = False):
    #     """
    #     Calculates actual sample points given a Block.
    #
    #     @param Pulse_Block block: Block to be sampled.
    #     @param int iteration_no: Current number of repetition step.
    #     @param int bin_offset: The time bin offset, i.e. the position of the
    #                            block inside the whole sample array.
    #
    #     @return numpy_ndarrays[channel, sample]: The sampled analogue and
    #                                              digital channels.
    #     """
    #     ana_channels = block.analogue_channels
    #     dig_channels = block.digital_channels
    #     block_length_bins = block.init_length_bins + (block.increment_bins * iteration_no)
    #     arr_len = np.round(block_length_bins*1.01)
    #     sample_arr = np.empty([ana_channels, arr_len], dtype = 'float32')
    #     marker_arr = np.empty([dig_channels, arr_len], dtype = bool)
    #     entry = 0
    #     bin_offset_temp = bin_offset
    #     for block_element in block.element_list:
    #         temp_sample_arr, temp_marker_arr = self._sample_block_element(block_element, iteration_no, bin_offset_temp)
    #         temp_len = temp_sample_arr.shape[1]
    #         sample_arr[:, entry:temp_len+entry] = temp_sample_arr
    #         marker_arr[:, entry:temp_len+entry] = temp_marker_arr
    #         entry += temp_len
    #         if rotating_frame:
    #             bin_offset_temp = bin_offset + entry
    #     # slice the sample array to cut off uninitialized entrys at the end
    #     return sample_arr[:, :entry], marker_arr[:, :entry]

    # def _sample_block_element(self, block_element):
    #     """
    #
    #     @param block_element:
    #     @return:
    #     """
    #     number_of_samples = block_element.init_length_bins
    #     ana_channels = block_element.analogue_channels
    #     dig_channels = block_element.digital_channels
    #
    #     # Allocate sample arrays
    #     analogue_samples = np.empty([ana_channels, number_of_samples], dtype = 'float32')
    #     digital_samples = np.empty([dig_channels, number_of_samples], dtype = bool)
    #
    #     parameters = block_element.parameters
    #     markers_on = block_element.markers_on
    #     pulse_function = block_element.pulse_function
    #
    #     time_arr = (np.arange(number_of_samples)) / self.sample_rate
    #
    #     for i, state in enumerate(markers_on):
    #         digital_samples[i, :] = np.full(number_of_samples, state, dtype = bool)
    #     for i, func_name in enumerate(pulse_function):
    #         analogue_samples[i, :] = np.float32(self._math_func[func_name](time_arr, parameters[i]))
    #
    #     return analogue_samples, digital_samples

    # def _sample_block_element(self, block_element, iteration_no=0, bin_offset=0):
    #     """
    #     Calculates actual sample points given a Block_Element.
    #
    #     @param Pulse_Block_Element block_element: Block element to be sampled.
    #     @param int iteration_no: Current number of repetition step.
    #     @param int bin_offset: The time bin offset, i.e. the position of the
    #                            block_element inside the whole sample array.
    #
    #     @return (numpy_ndarrays[channel, sample], numpy_ndarrays[channel, sample]):
    #             The sampled analogue and digital channels
    #     """
    #     ana_channels = block_element.analogue_channels
    #     dig_channels = block_element.digital_channels
    #     parameters = block_element.parameters
    #     init_length_bins = block_element.init_length_bins
    #     increment_bins = block_element.increment_bins
    #     markers_on = block_element.markers_on
    #     pulse_function = block_element.pulse_function
    #
    #     element_length_bins = init_length_bins + (iteration_no*increment_bins)
    #     sample_arr = np.empty([ana_channels, element_length_bins], dtype = 'float32')
    #     marker_arr = np.empty([dig_channels, element_length_bins], dtype = bool)
    #     time_arr = (bin_offset + np.arange(element_length_bins)) / self.sample_rate
    #     print(time_arr[0])
    #     print(bin_offset)
    #
    #     for i, state in enumerate(markers_on):
    #         marker_arr[i] = np.full(element_length_bins, state, dtype = bool)
    #     for i, func_name in enumerate(pulse_function):
    #         sample_arr[i] = np.float32(self._math_func[func_name](time_arr, parameters[i]))
    #
    #     return sample_arr, marker_arr

#-------------------------------------------------------------------------------
#                    END sequence/block sampling
#-------------------------------------------------------------------------------

    def generate_rabi(self, name='', mw_freq_Hz=0.0, mw_amp_V=0.0, aom_delay_bins=0,
                      laser_time_bins=0, tau_start_bins=0, tau_end_bins=0,
                      number_of_taus=0, use_seqtrig = True):

        # create parameter dictionary list for MW signal
        mw_params = [{},{}]
        mw_params[0]['frequency1'] = mw_freq_Hz
        mw_params[0]['amplitude1'] = mw_amp_V
        mw_params[0]['phase1'] = 0

        no_analogue_params = [{},{}]
        laser_markers = [True, True, False, False]
        gate_markers = [False, True, False, False]
        idle_markers = [False, False, False, False]
        seqtrig_markers = [False, False, True, False]

        # create tau list
        tau_list = np.linspace(tau_start_bins, tau_end_bins, number_of_taus,
                               dtype=int)

        # generate elements
        laser_element = Pulse_Block_Element(laser_time_bins, 2, 4, 0,
                                            ['Idle', 'Idle'], laser_markers,
                                            no_analogue_params)
        aomdelay_element = Pulse_Block_Element(aom_delay_bins, 2, 4, 0,
                                               ['Idle', 'Idle'], gate_markers,
                                               no_analogue_params)
        waiting_element = Pulse_Block_Element((1e-6*self.sample_rate)-
                                              aom_delay_bins, 2, 4, 0,
                                              ['Idle', 'Idle'], idle_markers,
                                              no_analogue_params)
        seqtrig_element = Pulse_Block_Element(250, 2, 4, 0, ['Idle', 'Idle'],
                                              seqtrig_markers,
                                              no_analogue_params)

        # Create the Pulse_Block_Element objects and append them to the element
        # list.
        element_list = []
        for tau in tau_list:
            mw_element = Pulse_Block_Element(tau, 2, 4, 0, ['Sin', 'Idle'],
                                             idle_markers, mw_params)
            element_list.append(laser_element)
            element_list.append(aomdelay_element)
            element_list.append(waiting_element)
            element_list.append(mw_element)
        if use_seqtrig:
            element_list.append(seqtrig_element)

        # create the Pulse_Block object.
        block = Pulse_Block(name, element_list)
        # put block in a list with repetitions
        block_list = [(block, 0),]
        # create ensemble out of the block(s)
        block_ensemble = Pulse_Block_Ensemble(name, block_list, tau_list,
                                              number_of_taus,
                                              rotating_frame=False)
        # save block
        # self.save_block(name, block)
        # save ensemble
        self.save_ensemble(name, block_ensemble)
        # set current block
        self.current_block = block
        # set current block ensemble
        self.current_ensemble = block_ensemble
        # update ensemble list
        self.refresh_ensemble_list()
        return

    def generate_pulsedodmr(self, name='', start_freq=0.0, stop_freq=0.0,
                            number_of_points=0, amp_V=0.0, pi_bins=0,
                            aom_delay_bins=0, laser_time_bins=0,
                            use_seqtrig=True):

        # create parameter dictionary list for MW signal
        mw_params = [{},{}]
        mw_params[0]['amplitude1'] = amp_V
        mw_params[0]['phase1'] = 0
        no_analogue_params = [{},{}]
        laser_markers = [True, True, False, False]
        gate_markers = [False, True, False, False]
        idle_markers = [False, False, False, False]
        seqtrig_markers = [False, False, True, False]

        # create frequency list
        freq_list = np.linspace(start_freq, stop_freq, number_of_points)

        # generate elements
        laser_element = Pulse_Block_Element(laser_time_bins, 2, 4, 0, ['Idle', 'Idle'], laser_markers, no_analogue_params)
        aomdelay_element = Pulse_Block_Element(aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], gate_markers, no_analogue_params)
        waiting_element = Pulse_Block_Element((1e-6*self.sample_rate)-aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analogue_params)
        seqtrig_element = Pulse_Block_Element(250, 2, 4, 0, ['Idle', 'Idle'], seqtrig_markers, no_analogue_params)
        # put elements in a list to create the block
        element_list = []
        for freq in freq_list:
            # create copy of parameter dict to use for this frequency
            temp_params = [mw_params[0].copy(),{}]
            temp_params[0]['frequency1'] = freq
            # create actual pi-pulse element
            pi_element = Pulse_Block_Element(pi_bins, 2, 4, 0, ['Sin', 'Idle'], idle_markers, temp_params)
            # create measurement elements for this frequency
            element_list.append(laser_element)
            element_list.append(aomdelay_element)
            element_list.append(waiting_element)
            element_list.append(pi_element)
        if use_seqtrig:
            element_list.append(seqtrig_element)

        # create block
        block = Pulse_Block(name, element_list)
        # put block in a list with repetitions
        block_list = [(block, 0),]
        # create ensemble out of the block(s)
        block_ensemble = Pulse_Block_Ensemble(name, block_list, freq_list, number_of_points, False)
        # save block
        # self.save_block(name, block)
        # save ensemble
        self.save_ensemble(name, block_ensemble)
        # set current block
        self.current_block = block
        # set current block ensemble
        self.current_ensemble = block_ensemble
        # update ensemble list
        self.refresh_ensemble_list()
        return

    def generate_xy8(self, name='', mw_freq_Hz=0.0, mw_amp_V=0.0,
                     aom_delay_bins=0, laser_time_bins=0, tau_start_bins=0,
                     tau_end_bins=0, number_of_taus=0, pihalf_bins=0,
                     pi_bins=0, N=0, use_seqtrig=True):


        pihalf_pix_params = [{},{}]
        pihalf_pix_params[0]['frequency1'] = mw_freq_Hz
        pihalf_pix_params[0]['amplitude1'] = mw_amp_V
        pihalf_pix_params[0]['phase1'] = 0
        piy_params = [{},{}]
        piy_params[0]['frequency1'] = mw_freq_Hz
        piy_params[0]['amplitude1'] = mw_amp_V
        piy_params[0]['phase1'] = 90
        no_analogue_params = [{},{}]
        laser_markers = [True, True, False, False]
        gate_markers = [False, True, False, False]
        idle_markers = [False, False, False, False]
        seqtrig_markers = [False, False, True, False]

        # create tau lists
        tau_list = np.linspace(tau_start_bins, tau_end_bins, number_of_taus)
        tauhalf_list = tau_list/2
        # correct taus for nonzero-length pi- and pi/2-pulses
        tau_list_corr = tau_list - pi_bins
        tauhalf_list_corr = tauhalf_list - (pi_bins/2) - (pihalf_bins/2)
        # round lists to nearest integers
        tau_list_corr = np.array(np.rint(tau_list), dtype=int)
        tauhalf_list_corr = np.array(np.rint(tauhalf_list), dtype=int)
        tau_list = np.array(np.rint(tau_list), dtype=int)
        tauhalf_list = np.array(np.rint(tauhalf_list), dtype=int)

        # generate elements
        laser_element = Pulse_Block_Element(laser_time_bins, 2, 4, 0, ['Idle', 'Idle'], laser_markers, no_analogue_params)
        aomdelay_element = Pulse_Block_Element(aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], gate_markers, no_analogue_params)
        waiting_element = Pulse_Block_Element((1e-6*self.sample_rate)-aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analogue_params)
        seqtrig_element = Pulse_Block_Element(250, 2, 4, 0, ['Idle', 'Idle'], seqtrig_markers, no_analogue_params)
        pihalf_element = Pulse_Block_Element(pihalf_bins, 2, 4, 0, ['Sin', 'Idle'], idle_markers, pihalf_pix_params)
        pi_x_element = Pulse_Block_Element(pi_bins, 2, 4, 0, ['Sin', 'Idle'], idle_markers, pihalf_pix_params)
        pi_y_element = Pulse_Block_Element(pi_bins, 2, 4, 0, ['Sin', 'Idle'], idle_markers, piy_params)

        # generate block list
        blocks = []
        for tau_ind in range(len(tau_list_corr)):
            # create tau and tauhalf elements
            tau_element = Pulse_Block_Element(tau_list_corr[tau_ind], 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analogue_params)
            tauhalf_element = Pulse_Block_Element(tauhalf_list_corr[tau_ind], 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analogue_params)

            # actual XY8-N sequence
            # generate element list
            elements = []
            elements.append(pihalf_element)
            elements.append(tauhalf_element)
            # repeat xy8 N times
            for i in range(N):
                elements.append(pi_x_element)
                elements.append(tau_element)
                elements.append(pi_y_element)
                elements.append(tau_element)
                elements.append(pi_x_element)
                elements.append(tau_element)
                elements.append(pi_y_element)
                elements.append(tau_element)
                elements.append(pi_y_element)
                elements.append(tau_element)
                elements.append(pi_x_element)
                elements.append(tau_element)
                elements.append(pi_y_element)
                elements.append(tau_element)
                elements.append(pi_x_element)
                elements.append(tau_element)
            # remove last tau waiting time and replace it with readout
            del elements[-1]
            elements.append(tauhalf_element)
            elements.append(pihalf_element)
            elements.append(laser_element)
            elements.append(aomdelay_element)
            elements.append(waiting_element)

            # create a new block for this XY8-N sequence with fixed tau and add it to the block list
            blocks.append(Pulse_Block('XY8_' + str(N) + '_taubins_' + str(tau_list[tau_ind]), elements))

        # seqeunce trigger for FPGA counter
        if use_seqtrig:
            tail_elements = [seqtrig_element]
            blocks.append(Pulse_Block('XY8_' + str(N) + '_tail', tail_elements))

        # generate block ensemble (the actual whole measurement sequence)
        block_list = []
        for block in blocks:
            block_list.append((block, 0))
        # name = 'XY8_' + str(N) + '_taustart_' + str(tau_list[0]) + '_tauend_' + str(tau_list[-1]) + '_numtaus_' + str(len(tau_list))
        XY8_ensemble = Pulse_Block_Ensemble(name, block_list, tau_list, number_of_taus, True)
        # save ensemble
        self.save_ensemble(name, XY8_ensemble)
        # set current block ensemble
        self.current_ensemble = XY8_ensemble
        # set first XY8-N tau block as current block
        self.current_block = blocks[0]
        # update ensemble list
        self.refresh_ensemble_list()

    def generate_HHamp_sweep(self, name='', pihalf_V=0.0, pihalf_bins=0,
                             pi3half_bins=0, spinlock_start_V=0.0,
                             spinlock_stop_V=0.0, number_of_points=0,
                             freq1=0.0, freq2=0.0, freq3=0.0, slphase_deg=0.0,
                             spinlock_bins=0, aom_delay_bins=0,
                             laser_time_bins=0, use_seqtrig=True):
        # create parameter dictionary list for MW signal
        pihalf_params = [{},{}]
        pihalf_params[0]['amplitude1'] = pihalf_V
        pihalf_params[0]['frequency1'] = freq1
        pihalf_params[0]['phase1'] = 0
        spinlock_params = [{},{}]
        spinlock_params[0]['frequency1'] = freq1
        spinlock_params[0]['phase1'] = slphase_deg
        no_analogue_params = [{},{}]
        laser_markers = [False, False, True, False]
        # gate_markers = [False, False, False, False]
        idle_markers = [False, False, False, False]
        seqtrig_markers = [False, False, False, True]

        # create amplitude list
        amp_list = np.linspace(spinlock_start_V, spinlock_stop_V, number_of_points, dtype=int)

        # generate elements
        laser_element = Pulse_Block_Element(laser_time_bins, 2, 4, 0, ['Idle', 'Idle'], laser_markers, no_analogue_params)
        aomdelay_element = Pulse_Block_Element(aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analogue_params)
        waiting_element = Pulse_Block_Element((1e-6*self.sampling_freq)-aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analogue_params)
        seqtrig_element = Pulse_Block_Element(250, 2, 4, 0, ['Idle', 'Idle'], seqtrig_markers, no_analogue_params)
        pihalf_element = Pulse_Block_Element(pihalf_bins, 2, 4, 0, ['Sin', 'Idle'], idle_markers, pihalf_params)
        pi3half_element = Pulse_Block_Element(pi3half_bins, 2, 4, 0, ['Sin', 'Idle'], idle_markers, pihalf_params)
        # put elements in a list to create the block
        element_list = []
        for voltage in amp_list:
            # create copy of parameter dict to use for this amplitude
            temp_params = [spinlock_params[0].copy(),{}]
            temp_params[0]['amplitude1'] = voltage
            # create actual spinlock-pulse element
            spinlock_element = Pulse_Block_Element(spinlock_bins, 2, 4, 0, ['Sin', 'Idle'], idle_markers, temp_params)
            # create measurement elements for this frequency
            # polarize in one direction
            element_list.append(laser_element)
            element_list.append(aomdelay_element)
            element_list.append(waiting_element)
            element_list.append(pihalf_element)
            element_list.append(spinlock_element)
            element_list.append(pihalf_element)
            # polarize in other direction
            element_list.append(laser_element)
            element_list.append(aomdelay_element)
            element_list.append(waiting_element)
            element_list.append(pi3half_element)
            element_list.append(spinlock_element)
            element_list.append(pi3half_element)
        if use_seqtrig:
            element_list.append(seqtrig_element)

        # create block
        block = Pulse_Block(name, element_list)
        # put block in a list with repetitions
        block_list = [(block, 0),]
        # create ensemble out of the block(s)
        block_ensemble = Pulse_Block_Ensemble(name, block_list, amp_list, number_of_points*2, True)
        # save block
        # self.save_block(name, block)
        # save ensemble
        self.save_ensemble(name, block_ensemble)
        # set current block
        self.current_block = block
        # set current block ensemble
        self.current_ensemble = block_ensemble
        # update ensemble list
        self.refresh_ensemble_list()
        return

    def generate_HHtau_sweep(self, name='', pihalf_V=0.0, pihalf_bins=0,
                             pi3half_bins=0, spinlock_start_bins=0,
                             spinlock_stop_bins=0, number_of_taus=0,
                             freq1=0.0, freq2=0.0, freq3=0.0, slphase_deg=0.0,
                             spinlock_V=0.0, aom_delay_bins=0,
                             laser_time_bins=0, use_seqtrig=True):

        # create parameter dictionary list for MW signal
        pihalf_params = [{},{}]
        pihalf_params[0]['amplitude1'] = pihalf_V
        pihalf_params[0]['frequency1'] = freq1
        pihalf_params[0]['phase1'] = 0
        spinlock_params = [{},{}]
        spinlock_params[0]['frequency1'] = freq1
        spinlock_params[0]['amplitude1'] = spinlock_V
        spinlock_params[0]['phase1'] = slphase_deg
        no_analogue_params = [{},{}]
        laser_markers = [False, False, True, False]
        # gate_markers = [False, False, False, False]
        idle_markers = [False, False, False, False]
        seqtrig_markers = [False, False, False, True]

        # create tau list
        tau_list = np.linspace(spinlock_start_bins, spinlock_stop_bins, number_of_taus, dtype=int)

        # generate elements
        laser_element = Pulse_Block_Element(laser_time_bins, 2, 4, 0, ['Idle', 'Idle'], laser_markers, no_analogue_params)
        aomdelay_element = Pulse_Block_Element(aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analogue_params)
        waiting_element = Pulse_Block_Element((1e-6*self.sampling_freq)-aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analogue_params)
        seqtrig_element = Pulse_Block_Element(250, 2, 4, 0, ['Idle', 'Idle'], seqtrig_markers, no_analogue_params)
        pihalf_element = Pulse_Block_Element(pihalf_bins, 2, 4, 0, ['Sin', 'Idle'], idle_markers, pihalf_params)
        pi3half_element = Pulse_Block_Element(pi3half_bins, 2, 4, 0, ['Sin', 'Idle'], idle_markers, pihalf_params)
        # put elements in a list to create the block
        element_list = []
        for tau in tau_list:
            # create actual spinlock-pulse element
            spinlock_element = Pulse_Block_Element(tau, 2, 4, 0, ['Sin', 'Idle'], idle_markers, spinlock_params)
            # create measurement elements for this frequency
            # polarize in one direction
            element_list.append(laser_element)
            element_list.append(aomdelay_element)
            element_list.append(waiting_element)
            element_list.append(pihalf_element)
            element_list.append(spinlock_element)
            element_list.append(pihalf_element)
            # polarize in other direction
            element_list.append(laser_element)
            element_list.append(aomdelay_element)
            element_list.append(waiting_element)
            element_list.append(pi3half_element)
            element_list.append(spinlock_element)
            element_list.append(pi3half_element)
        if use_seqtrig:
            element_list.append(seqtrig_element)

        # create block
        block = Pulse_Block(name, element_list)
        # put block in a list with repetitions
        block_list = [(block, 0),]
        # create ensemble out of the block(s)
        block_ensemble = Pulse_Block_Ensemble(name, block_list, tau_list, number_of_taus*2, True)
        # save block
        # self.save_block(name, block)
        # save ensemble
        self.save_ensemble(name, block_ensemble)
        # set current block
        self.current_block = block
        # set current block ensemble
        self.current_ensemble = block_ensemble
        # update ensemble list
        self.refresh_ensemble_list()
        return

    def generate_spinlock_N14(self, name='', pihalfamp_V=0.0, pihalf_bins=0,
                              spinlockamp_V=0.0, freq1=0.0, freq2=0.0,
                              freq3=0.0, slphase_deg=0.0, tau_start_bins=0,
                              tau_end_bins=0, number_of_taus=0,
                              aom_delay_bins=0, laser_time_bins=0,
                              use_seqtrig=True):
        # create parameter dictionary list for MW signal
        pihalf_params = [{},{}]
        pihalf_params[0]['amplitude1'] = pihalfamp_V
        pihalf_params[0]['frequency1'] = freq1
        pihalf_params[0]['phase1'] = 0
        spinlock_params = [{},{}]
        spinlock_params[0]['amplitude1'] = spinlockamp_V
        spinlock_params[0]['frequency1'] = freq1
        spinlock_params[0]['phase1'] = slphase_deg
        no_analogue_params = [{},{}]
        laser_markers = [False, False, True, False]
        # gate_markers = [False, False, False, False]
        idle_markers = [False, False, False, False]
        seqtrig_markers = [False, False, False, True]

        # create tau list
        tau_list = np.linspace(tau_start_bins, tau_end_bins, number_of_taus, dtype=int)

        # generate elements
        laser_element = Pulse_Block_Element(laser_time_bins, 2, 4, 0, ['Idle', 'Idle'], laser_markers, no_analogue_params)
        aomdelay_element = Pulse_Block_Element(aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analogue_params)
        waiting_element = Pulse_Block_Element((1e-6*self.sampling_freq)-aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analogue_params)
        seqtrig_element = Pulse_Block_Element(250, 2, 4, 0, ['Idle', 'Idle'], seqtrig_markers, no_analogue_params)
        pihalf_element = Pulse_Block_Element(pihalf_bins, 2, 4, 0, ['Sin', 'Idle'], idle_markers, pihalf_params)
        # put elements in a list to create the block
        element_list = []
        for tau in tau_list:
            # create actual spinlock-pulse element
            spinlock_element = Pulse_Block_Element(tau, 2, 4, 0, ['Sin', 'Idle'], idle_markers, spinlock_params)
            # create measurement elements for this frequency
            element_list.append(laser_element)
            element_list.append(aomdelay_element)
            element_list.append(waiting_element)
            element_list.append(pihalf_element)
            element_list.append(spinlock_element)
            element_list.append(pihalf_element)
        if use_seqtrig:
            element_list.append(seqtrig_element)

        # create block
        block = Pulse_Block(name, element_list)
        # put block in a list with repetitions
        block_list = [(block, 0),]
        # create ensemble out of the block(s)
        block_ensemble = Pulse_Block_Ensemble(name, block_list, tau_list, number_of_taus, True)
        # save block
        # self.save_block(name, block)
        # save ensemble
        self.save_ensemble(name, block_ensemble)
        # set current block
        self.current_block = block
        # set current block ensemble
        self.current_ensemble = block_ensemble
        # update ensemble list
        self.refresh_ensemble_list()
        return

    def generate_rabi_triple(self, name='', mw_freq_Hz_1=0.0,
                             mw_freq_Hz_2=0.0, mw_freq_Hz_3=0.0,
                             mw_amp_V=0.0, aom_delay_bins=0,
                             laser_time_bins=0, tau_start_bins=0,
                             tau_end_bins=0, number_of_taus=0,
                             use_seqtrig=True):
        # create parameter dictionary list for MW signal
        mw_params = [{},{}]
        mw_params[0]['frequency1'] = mw_freq_Hz_1
        mw_params[0]['frequency2'] = mw_freq_Hz_2
        mw_params[0]['frequency3'] = mw_freq_Hz_3
        mw_params[0]['amplitude1'] = mw_amp_V
        mw_params[0]['amplitude2'] = mw_amp_V
        mw_params[0]['amplitude3'] = mw_amp_V
        mw_params[0]['phase1'] = 0
        mw_params[0]['phase2'] = 0
        mw_params[0]['phase3'] = 0
        no_analogue_params = [{},{}]
        laser_markers = [False, False, True, False]
        gate_markers = [False, False, False, False]
        idle_markers = [False, False, False, False]
        seqtrig_markers = [False, False, False, True]

        # create tau list
        tau_list = np.linspace(tau_start_bins, tau_end_bins, number_of_taus, dtype=int)

        # generate elements
        laser_element = Pulse_Block_Element(laser_time_bins, 2, 4, 0, ['Idle', 'Idle'], laser_markers, no_analogue_params)
        aomdelay_element = Pulse_Block_Element(aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], gate_markers, no_analogue_params)
        waiting_element = Pulse_Block_Element((1e-6*self.sampling_freq)-aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analogue_params)
        seqtrig_element = Pulse_Block_Element(250, 2, 4, 0, ['Idle', 'Idle'], seqtrig_markers, no_analogue_params)
        # put elements in a list to create the block
        element_list = []
        for tau in tau_list:
            mw_element = Pulse_Block_Element(tau, 2, 4, 0, ['TripleSin', 'Idle'], idle_markers, mw_params)
            element_list.append(laser_element)
            element_list.append(aomdelay_element)
            element_list.append(waiting_element)
            element_list.append(mw_element)
        if use_seqtrig:
            element_list.append(seqtrig_element)

        # create block
        block = Pulse_Block(name, element_list)
        # put block in a list with repetitions
        block_list = [(block, 0),]
        # create ensemble out of the block(s)
        block_ensemble = Pulse_Block_Ensemble(name, block_list, tau_list, number_of_taus, False)
        # save block
        # self.save_block(name, block)
        # save ensemble
        self.save_ensemble(name, block_ensemble)
        # set current block
        self.current_block = block
        # set current block ensemble
        self.current_ensemble = block_ensemble
        # update ensemble list
        self.refresh_ensemble_list()
        return