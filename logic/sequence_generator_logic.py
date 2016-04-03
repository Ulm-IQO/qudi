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
import importlib

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
    def __init__(self, init_length_bins, analog_channels, digital_channels,
                 increment_bins = 0, pulse_function = None,
                 marker_active = None, parameters=[], use_as_tick=False):
        """ The constructor for a Pulse_Block_Element needs to have:

        @param int init_length_bins: an initial length of a bins, this
                                 parameters should not be zero but must have a
                                 finite value.
        @param int analog_channels: number of analog channels
        @param int digital_channels: number of digital channels
        @param int increment_bins: the number which will be incremented during
                               each repetition of this object
        @param str pulse_function: name of the sampling function how to
                               alter the points, the name of the function will
                               be one of the sampling functions
        @param list marker_active: list of digital channels, which are for the
                              length of this Pulse_Block_Element are set either
                              to True (high) or to False (low). The length of
                              the marker list depends on the number of (active)
                              digital channels. For 4 digital channel it may
                              look like:
                              [True, False, False, False]
        @param list parameters: a list of dictionaries. The number of dictionaries
                           depends on the number of analog channels. The
                           number of entries within a dictionary depends on the
                           chosen sampling function. The key words of the
                           dictionary for the parameters will be those of the
                           sampling functions.
        @param bool use_as_tick: bool, indicates, whether the set length should
                           be used as a tick (i.e. the parameter for the x axis)
                           for the later plot in the analysis.
        """

        self.init_length_bins   = init_length_bins
        self.analog_channels  = analog_channels
        self.digital_channels   = digital_channels
        self.increment_bins     = increment_bins
        self.pulse_function     = pulse_function
        self.marker_active      = marker_active
        self.parameters         = parameters
        self.use_as_tick         = use_as_tick


class Pulse_Block(object):
    """ Collection of Pulse_Block_Elements which is called a Pulse_Block. """

    def __init__(self, name, element_list, laser_channel_index):
        """ The constructor for a Pulse_Block needs to have:

        @param str name: chosen name for the Pulse_Block
        @param list element_list: which contains the Pulse_Block_Element
                             Objects forming a Pulse_Block, e.g.
                             [Pulse_Block_Element, Pulse_Block_Element, ...]
        @param int laser_channel_index: The index of the digital channel representing the laser
        """
        self.name = name
        self.element_list = element_list
        self.laser_channel = laser_channel_index
        self.refresh_parameters()

    def refresh_parameters(self):
        """ Initialize the parameters which describe this Pulse_Block object.

        The information is gained from all the Pulse_Block_Element objects,
        which are attached in the element_list.
        """

        # the Pulse_Block parameter
        self.init_length_bins = 0
        self.increment_bins = 0
        self.analog_channels = 0
        self.digital_channels = 0
        self.number_of_lasers = 0

        # calculate the tick value for the whole block. Basically sum all the
        # init_length_bins which have the use_as_tick attribute set to True.
        self.measurement_tick = 0
        # make the same thing for the increment, to obtain the total increment
        # number for the block. This facilitates in calculating the measurement tick list.
        self.measurement_tick_increment = 0

        for elem in self.element_list:
            self.init_length_bins += elem.init_length_bins
            self.increment_bins += elem.increment_bins

            if elem.marker_active[self.laser_channel]:
                self.number_of_lasers += 1


            if elem.use_as_tick:
                self.measurement_tick = self.measurement_tick + elem.init_length_bins
                self.measurement_tick_increment = self.measurement_tick_increment + elem.increment_bins

            if elem.analog_channels > self.analog_channels:
                self.analog_channels = elem.analog_channels
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

    def append_element(self, element, at_beginning=False):
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

    def __init__(self, name, block_list, laser_channel_index, measurement_ticks_list=[],
                 rotating_frame=True):
        """ The constructor for a Pulse_Block_Ensemble needs to have:

        @param str name: chosen name for the Pulse_Block_Ensemble
        @param list block_list: contains the Pulse_Block Objects with their number of repetitions,
                                e.g.
                                    [(Pulse_Block, repetitions), (Pulse_Block, repetitions), ...])
        @param list measurement_ticks_list: the x-axis of the measurement.
        @param int laser_channel_index: the index of the digital channel representing the laser
        @param bool rotating_frame: indicates whether the phase should be preserved for all the
                                    functions.
        """

        self.name = name                    # Pulse_Block_Ensemble name
        self.block_list = block_list
        self.measurement_ticks_list = np.array(measurement_ticks_list)
        self.laser_channel = laser_channel_index
        self.rotating_frame = rotating_frame
        self.refresh_parameters()

    def refresh_parameters(self):
        self.length_bins = 0
        self.analog_channels = 0
        self.digital_channels = 0
        self.number_of_lasers = 0

        for block, reps in self.block_list:
            if block.laser_channel != self.laser_channel:
                block.laser_channel = self.laser_channel
                block.refresh_parameters()
            if block.analog_channels > self.analog_channels:
                self.analog_channels = block.analog_channels
                block.refresh_parameters()
            if block.digital_channels > self.digital_channels:
                self.digital_channels = block.digital_channels
                block.refresh_parameters()
            self.number_of_lasers += (reps+1)*block.number_of_lasers
            self.length_bins += (block.init_length_bins * (reps+1) + block.increment_bins * (reps*(reps+1)/2))
        self.estimated_bytes = self.length_bins * (self.analog_channels * 4 + self.digital_channels)
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

# one crucial thing about a list is that you needed to know the correspondance
# i.e. in which entry which information is situated. Dictionaries assign to a
# keyword a value, which is much more descriptive and which enables us to carry
# a bigger information content.


class Pulse_Sequence(object):
    """ Higher order object for sequence capability.

    Represents a playback procedure for a number of Pulse_Block_Ensembles.
    Unused for pulse generator hardware without sequencing functionality.
    """


    def __init__(self, name, ensemble_param_list, measurement_ticks_list=[],
                 rotating_frame=True):
        """ The constructor for a Pulse_Sequence objects needs to have:

        @param str name: the actual name of the sequence
        @param list ensemble_param_list: list containing a tuple of two entries:
                    (Pulse_Block_Ensemble, seq_param), (Pulse_Block_Ensemble, seq_param), ...
                                          The seq_param is a dictionary, where the various sequence
                                          parameters are saved with their keywords and the
                                          according parameter (as item). What parameter will be in
                                          this dictionary will completely depend on the sequence
                                          parameter set of the pulsing device. But most certain the
                                          parameter 'reps' meaning repetitions will be presesnt in
                                          the sequence parameters.
                                          If only 'reps' are in the dictionary, than the dict will
                                          look like
                                                seq_param = {'reps': 12}
                                          if 12 was chosen as the number of repetitions.
        @param list measurement_ticks_list: 1d list, where each entry corresponds to an tick on an
                                            the x-axis of the measurement.
                                            Note, that the x-axis does not have to be always a time
                                            axis! The entry can also be voltages or other stuffm
                                            which varies between the different entries!
        @param bool rotating_frame: indicates, whether the phase has to be preserved in all
                                    oscillating functions.
        """

        self.name = name
        self.ensemble_param_list = ensemble_param_list
        self.measurement_ticks_list = np.array(measurement_ticks_list)
        self.rotating_frame = rotating_frame
        self.refresh_parameters()

    def refresh_parameters(self):
        """ Generate the needed parameters from the passed object.

        Baiscally, calculate the length_bins and number of analog and digital
        channels.
        """
        self.length_bins = 0
        self.analog_channels = 0
        self.digital_channels = 0

        for ensemble, seq_dict in self.ensemble_param_list:

            for param in seq_dict:
                if 'reps' in param.lower() or 'repetition' in param.lower():
                    reps = seq_dict[param]
                    break
                else:
                    reps = 0

            self.length_bins += (ensemble.length_bins * (reps+1))

            if ensemble.analog_channels > self.analog_channels:
                self.analog_channels = ensemble.analog_channels
            if ensemble.digital_channels > self.digital_channels:
                self.digital_channels = ensemble.digital_channels

        self.estimated_bytes = self.length_bins * (self.analog_channels * 4 + self.digital_channels)

        # make a list with all DIFFERENT Pulse_Block_Ensemble objects


    def replace_ensemble(self, position, ensemble_param):
        """ Replace an ensemble at a given position.

        @param int position: position in a the ensemble list
        @param list ensemble_param: with entries
                                        (Pulse_Block_Ensemble, seq_param)
                                    which will replace the old one.
        """
        self.ensemble_param_list[position] = ensemble_param
        self.refresh_parameters()
        return

    def delete_ensemble(self, position):
        """ Delete an ensemble at a given position

        @param int position: position within the list self.ensemble_param_list.
        """
        del(self.ensemble_list[position])
        self.refresh_parameters()

    def append_ensemble(self, ensemble_param, at_beginning=False):
        """ Append either at the front or at the back an ensemble_param

        @param tuple ensemble_param: containing two entries:
                                        (Pulse_Block_Ensemble, seq_param)
                                     where Pulse_Block_Ensemble is the object
                                     and seq_param is the parameter set for that
                                     ensemble.
        @param bool at_beginning: If flase append to end (default), if true then
                                  inset at beginning.
        """

        if at_beginning:
            self.ensemble_list.insert(0, ensemble)
        else:
            self.ensemble_list.append(ensemble)
        self.refresh_parameters()


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

        self.current_block = None
        self.current_ensemble = None
        self.current_sequence = None

        # The string names of the created Pulse_Block objects are saved here:
        self.saved_pulse_blocks = []
        # The string names of the created Pulse_Block_Ensemble objects are
        # saved here:
        self.saved_pulse_block_ensembles = []
        # The string names of the created Sequence objects are saved here:
        self.saved_pulse_sequences = []

        if 'pulsed_file_dir' in config.keys():
            self.pulsed_file_dir = config['pulsed_file_dir']

            if not os.path.exists(self.pulsed_file_dir):

                homedir = self.get_home_dir()
                self.pulsed_file_dir = os.path.join(homedir, 'pulsed_files')
                self.logMsg('The directort defined in "pulsed_file_dir" in the'
                        'config for SequenceGeneratorLogic class does not '
                        'exist!\nThe default home directory\n{0}\n will be '
                        'taken instead.'.format(self.pulsed_file_dir),
                        msgType='warning')
        else:
            homedir = self.get_home_dir()
            self.pulsed_file_dir = os.path.join(homedir, 'pulsed_files')
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
                      'view_stepsize': 1e-9, 'dec': 8, 'unit_prefix': 'n', 'type': float}

        rep_def = {'unit': '#', 'init_val': 0, 'min': 0, 'max': (2**31 -1),
                   'view_stepsize': 1, 'dec': 0, 'unit_prefix': '', 'type':int}
        bool_def = {'unit': 'bool', 'init_val': 0, 'min': 0, 'max': 1,
                    'view_stepsize': 1, 'dec': 0, 'unit_prefix': '', 'type': bool}

        # make a parameter constraint dict for the additional parameters of the
        # Pulse_Block_Ensemble objects:
        self._add_pbe_param = OrderedDict()
        self._add_pbe_param['length'] = length_def
        self._add_pbe_param['increment'] = length_def
        self._add_pbe_param['use as tick?'] = bool_def
        # self._add_pbe_param['repeat?'] = bool_def


        self._add_pb_param = OrderedDict()
        self._add_pb_param['repetition'] = rep_def

        # Contains the Sequence parameter, but these are set in during the activation depending on
        # the hardware configuration
        self._seq_param = OrderedDict()
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

        self.cfg_param_seq = {'ensemble' : 0}

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

        self._pulse_generator_device = self.connector['in']['pulser']['object']

        self.sample_rate = self._pulse_generator_device.get_sample_rate()

        # make together with the hardware a proper dictionary for the sequence parameter:
        # self.cfg_param_seq =
        self._seq_param =  self._create_seq_param()

        constraints = self.get_hardware_constraints()

        # at least this configuration should always be available, if other
        # configuration are available, they can be chosen and set from the GUI.
        channel_config = constraints['channel_config']['conf1']
        self.analog_channels =  channel_config.count('a_ch')
        self.digital_channels =  channel_config.count('d_ch')

        # lists with the pp-voltages and offsets corresponding to the analog channels
        self.amplitude_list, self.offset_list = self._pulse_generator_device.get_analog_level()

        config = self.getConfiguration()

        # Append to this list all methods, which should be used for automated
        # parameter generation.
        # ALL THE ARGUMENTS IN THE METHODS MUST BE ASSIGNED TO DEFAULT VALUES!
        # Otherwise it is not possible to determine the proper viewbox.

        self.prepared_method_list=[]
        if 'prepared_methods' in config.keys():
            prep_methods_list = config['prepared_methods']
            self.prepared_method_list = [None]*len(prep_methods_list)

            # evaluate the name of the method to get the reference to it.
            for index, method in enumerate(prep_methods_list):
                self.prepared_method_list[index] = eval('self.'+method)
        else:
            self.logMsg('No prepared Methods are chosen, therefore none will '
                        'be displayed!', msgType='status')


    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        pass

    def _create_seq_param(self):
        """ Create a dictionary for sequence parameters.

        @return dict: the parameter dictionary for the sequence mode

        Based on the information from the hardware, the logic will create an rather abstract
        configuration dictionary, so that the GUI has no problems to build from that the proper
        viewwidgets.
        """

        # predefined definition dicts:
        float_def = {'unit': 's', 'init_val': 0.0, 'min': 0.0, 'max': np.inf,
                      'view_stepsize': 1e-9, 'dec': 8, 'unit_prefix': 'n', 'type': float}

        int_def = {'unit': '#', 'init_val': 0, 'min': 0, 'max': (2 ** 31 - 1),
                   'view_stepsize': 1, 'dec': 0, 'unit_prefix': '', 'type': int}

        bool_def = {'unit': 'bool', 'init_val': 0, 'min': 0, 'max': 1,
                    'view_stepsize': 1, 'dec': 0, 'unit_prefix': '', 'type': bool}

        seq_param_hardware = self.get_hardware_constraints()['sequence_param']
        seq_param = OrderedDict()

        # What follows now is a converion algorithm, which takes one of the valid above definition
        # dicts. Then the keywords, which are given by the contraints are replaced with their
        # proper value from the constraints. Furthermore an bool entry has to be converted to an
        # integer expression (True=1, False=0). Then the parameter definition is appended to the
        # sequence configuration parameters

        for entry in seq_param_hardware:
            param = {}

            # check the type of the sequence parameter:
            if type(seq_param_hardware[entry]['min']) == bool:
                dict_def = bool_def
            elif type(seq_param_hardware[entry]['min']) == int:
                dict_def = int_def
            elif type(seq_param_hardware[entry]['min']) == float:
                dict_def = float_def
            else:
                self.logMsg('The configuration dict for sequence parameter could not be created, '
                            'since the keyword "min" in the parameter {0} does not correspond to '
                            'type of "bool", "int" nor "float" but has a type {1}. Cannot handle '
                            'that, therefore this parameter is '
                            'neglected.'.format(entry,type(seq_param_hardware[entry]['min'])),
                            msgType='error')
                dict_def = {}


            # go through the dict_def and replace all given entries by the sequence parameter
            # constraints from the hardware.
            for element in dict_def:

                if element == 'view_stepsize':
                    param['view_stepsize'] = seq_param_hardware[entry]['step']
                elif element == 'init_value':
                    # convert an bool value into an integer value:
                    if type(element) is bool:
                        param[element] = int(seq_param_hardware[entry]['min'])
                    else:
                        param[element] = seq_param_hardware[entry]['min']
                elif element in seq_param_hardware[entry]:
                    # convert an bool value into an integer value:
                    if type(seq_param_hardware[entry][element]) is bool:
                        param[element] = int(seq_param_hardware[entry][element])
                    else:
                        param[element] = seq_param_hardware[entry][element]
                else:
                    param[element] = dict_def[element]

            seq_param[entry] = param

        return seq_param

    def get_seq_param(self):
        """ Retrieve the configuration parameters for sequences.

        @return dict: with keywords being the sequence parameters and items their configuration
                      dicts.
        """
        return self._seq_param

    def _get_dir_for_name(self, name):
        """ Get the path to the pulsed sub-directory 'name'.

        @param str name: name of the folder
        @return: str, absolute path to the directory with folder 'name'.
        """

        path = os.path.join(self.pulsed_file_dir, name)
        if not os.path.exists(path):
            os.makedirs(os.path.abspath(path))

        return os.path.abspath(path)

    def _insert_predefined_methods(self):
        """ Add the predefined methods to the main sequence object

        Procedure:
            The file is imported, so that its name space becomes accessable to
            this object. Then all callables function (also called methods)
            are attached to the main object self.
        """


        # make here the import directory, going from trunk dir.
        module = importlib.import_module('logic.pulsed.predefined_methods')

        setattr(self, 'generate_laser_on',
                module.generate_laser_on)
        return module


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
        # ampl_max = const['amplitude_analog'][1]

        ampl_max = const['a_ch_amplitude']['max']/2.0
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


    def pulser_on(self, a_ch={}, d_ch={}):
        """ Switch on the output of the Pulse Generator and activates the
            appropriate channels.

        @param dict a_ch: dictionary with keys being the analog channel numbers
                          and items being boolean values.
        @param dict d_ch: dictionary with keys being the digital channel numbers
                          and items being boolean values.

        @return int: error code (0:OK, -1:error)

        Example for possible input:
            a_ch={2: True}, d_ch={1:False, 3:True, 4:True}
        to activate analog channel 2 digital channel 3 and 4 and to deactivate
        digital channel 1.

        If nothing is passed, no channel activation is performed and the pulser
        is just switched on.
        """

        self._pulse_generator_device.set_active_channels(a_ch, d_ch)
        self._pulse_generator_device.pulser_on()
        return 0


    def pulser_off(self, a_ch={}, d_ch={}):
        """ Switch off the output of the Pulse Generator and deactivates the
            appropriate channels.

        @param dict a_ch: dictionary with keys being the analog channel numbers
                          and items being boolean values.
        @param dict d_ch: dictionary with keys being the digital channel numbers
                          and items being boolean values.

        @return int: error code (0:OK, -1:error)

        If nothing is passed, no channel deactivation is performed and the
        pulser is just switched off.
        """

        self._pulse_generator_device.pulser_off()
        self._pulse_generator_device.set_active_channels(a_ch, d_ch)
        return 0

    # These methods are not needed, since other logic does not need to access
    # the activation or deactivation of channels!
    # Do not confuse the activation/deactivation of channels with the actual
    # channels being used in the specified pulse_block_ensemble!
    #
    # THESE METHODS WILL (AND SHOULD) BE REMOVED WITHIN THE REVIEW PROCESS.
    #
    # def set_active_channels(self, a_ch={}, d_ch={}):
    #     """ Set the active channels for the pulse generator hardware.
    #
    #     @param dict a_ch: dictionary with keys being the analog channel numbers
    #                       and items being boolean values.
    #     @param dict d_ch: dictionary with keys being the digital channel numbers
    #                       and items being boolean values.
    #
    #     @return int: error code (0:OK, -1:error)
    #
    #     Example for possible input:
    #         a_ch={2: True}, d_ch={1:False, 3:True, 4:True}
    #     to activate analog channel 2 digital channel 3 and 4 and to deactivate
    #     digital channel 1.
    #
    #     Additionally the variables which hold this values are updated in the
    #     logic.
    #     """
    #
    #     self._pulse_generator_device.set_active_channels(a_ch, d_ch)
    #     # count all channels that are set to True
    #     # self.analog_channels = len([x for x in a_ch.values() if x == True])
    #     # self.digital_channels = len([x for x in d_ch.values() if x == True])
    #     return 0
    #
    # def get_active_channels(self):
    #     """ Get the currently active channels from the pulse generator hardware.
    #
    #     @return dict tuple: (a_ch, d_ch) dictionary with keys being the channel numbers
    #                         and items being boolean values.
    #
    #     Additionally the variables which hold this values are updated in the
    #     logic.
    #     """
    #
    #     active_channels = self._pulse_generator_device.get_active_channels()
    #     # self.analog_channels = len([x for x in active_channels[0].values() if x == True])
    #     # self.digital_channels = len([x for x in active_channels[1].values() if x == True])
    #     return active_channels
    #
    # def load_file(self, load_dict={}):
    #     """ Load an already sampled PulseBlockEnsemble object to the device.
    #
    #     @param: dict load_dict: a dictionary with keys being one of the
    #                             available channel numbers and items being the
    #                             name of the already sampled
    #                             Pulse_Block_Ensemble.
    #
    #     Example:
    #         If the Pulse_Block_Ensemble with name 'my-funny-stuff' is going to
    #         be loaded on channel 1 and 2 then it has to be passed like:
    #             upload_dict = {1: 'my-funny-stuff', 2: 'my-funny-stuff'}
    #         The pulse device should choose the proper file (which belongs to
    #         channel 1 and 2) and load it.
    #         You can e.g. also load just the file on channel two with:
    #             upload_dict = {2: 'my-funny-stuff'}
    #     """
    #
    #     self._pulse_generator_device.load_asset(load_dict)


    def clear_pulser(self):
        """ Delete all loaded files in the device's current memory. """
        self._pulse_generator_device.clear_all()


    def get_interleave(self):
        """ Get the interleave state.

        @return bool, state of the interleave, True=Interleave On, False=OFF
        """
        return self._pulse_generator_device.get_interleave()

    def set_interleave(self,interleave_state=False):
        """ Set the interleave state.

        @param bool interleave_state: If nothing passed, interleave will be switched off.
        """
        self._pulse_generator_device.set_interleave(interleave_state)

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
        with open(os.path.join(self.block_dir, name + '.blk'), 'wb') as outfile:
            pickle.dump(block, outfile)
        self.refresh_block_list()
        self.current_block = block
        self.logMsg('Pulse_Block object "{0}" serialized to harddisk in:\n'
                    '{1}'.format(name, self.block_dir), msgType='status',
                    importance=0)
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
            os.remove(os.path.join(self.block_dir, name + '.blk'))
            self.refresh_block_list()
        else:
            self.logMsg('Pulse_Block object with name "{0}" not found '
                        'in\n{1}\nTherefore nothing is '
                        'removed.'.format(name, self.block_dir),
                        msgType='warning')

    def refresh_block_list(self):
        """ Refresh the list of available (saved) blocks """

        block_files = [f for f in os.listdir(self.block_dir) if '.blk' in f]
        blocks = []
        for filename in block_files:
            blocks.append(filename[:-4])
        # blocks.sort()
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
            self.logMsg('The Pulse_Block_Ensemble object with name "{0}" '
                        'could not be found and serialized in:\n'
                        '{1}'.format(name, self.ensemble_dir),
                        msgType='warning')

            ensemble = None

        if set_as_current_ensemble:
            self.current_ensemble = ensemble

        return ensemble

    def delete_ensemble(self, name):
        """ Remove the ensemble with 'name' from the ensemble list and HDD. """

        if name in self.saved_pulse_block_ensembles:
            os.remove( os.path.join(self.ensemble_dir, name + '.ens'))
            self.refresh_ensemble_list()
        else:
            self.logMsg('Pulse_Block_Ensemble object with name "{0}" not found '
                        'in\n{1}\nTherefore nothing is '
                        'removed.'.format(name, self.ensemble_dir),
                        msgType='warning')
        return

    def refresh_ensemble_list(self):
        """ Refresh the list of available (saved) ensembles. """

        ensemble_files = [f for f in os.listdir(self.ensemble_dir) if '.ens' in f]
        ensembles = []
        for filename in ensemble_files:
            ensembles.append(filename.rsplit('.', 1)[0])
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
            self.logMsg('The Sequence object with name "{0}" could not be '
                        'found and serialized in:\n'
                        '{1}'.format(name, self.sequence_dir),
                        msgType='warning')
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
            self.logMsg('Sequence object with name "{0}" not found '
                        'in\n{1}\nTherefore nothing is '
                        'removed.'.format(name, self.sequence_dir),
                        msgType='warning')

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

    def upload_asset(self, asset_name):
        """ Upload an already sampled Ensemble or Sequence object to the device.
            Does NOT load it into channels.

        @param asset_name: string, name of the ensemble/sequence to upload
        """
        err = self._pulse_generator_device.upload_asset(asset_name)
        return err

    def has_sequence_mode(self):
        """ Retrieve from the hardware, whether sequence mode is present or not.

        @return bool: Sequence mode present = True, no sequence mode = False
        """
        return self._pulse_generator_device.has_sequence_mode()

    def load_asset(self, asset_name, load_dict={}):
        """ Loads a sequence or waveform to the specified channel of the pulsing device.

        @param str asset_name: The name of the asset to be loaded
        @param dict load_dict:  a dictionary with keys being one of the available channel numbers
                                and items being the name of the already sampled waveform/sequence
                                files. Examples:
                                    {1: rabi_Ch1, 2: rabi_Ch2}
                                    {1: rabi_Ch2, 2: rabi_Ch1}
                                This parameter is optional. If an empty dict is given then the
                                channel association should be invoked from the sequence generation,
                                i.e. the filename appendix (_Ch1, _Ch2 etc.). Note that is not in
                                general an ambigous procedure!

        @return int: error code (0:OK, -1:error)
        """
        err = self._pulse_generator_device.load_asset(asset_name, load_dict)
        return err

    # =========================================================================
    # Depricated method, will be remove soon.

    def generate_block(self, name, block_matrix):
        """
        @param block_matrix: stuctured numpy array
        Generates a Pulse_Block object out of the corresponding editor table/matrix.
        """
        # each line in the matrix corresponds to one Pulse_Block_Element
        # Here these elements are created
        analog_func = [None]*self.analog_channels
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

        for chnl_num in range(self.analog_channels):
            # Save all function names for channel number "chnl_num" in one
            # column of "analog_func". Also convert them to strings
            analog_func[chnl_num] = np.array(
                [ x[self.cfg_param_pbe['function_'+str(chnl_num)]].decode('utf-8')
                for x in block_matrix]  )

        # convert to numpy ndarray
        analog_func = np.array(analog_func)


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
            elem_func = analog_func[:, elem_num]
            elem_marker = digital_flags[:, elem_num]
            elem_incr = increments[elem_num]
            elem_length = lengths[elem_num]
            elem_parameters = [None]*self.analog_channels

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
                                analog_channels=len(analog_func),
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

        analog_channels=self.analog_channels
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
            pulse_function=[None]*self.analog_channels

            parameter_list =[None]*self.analog_channels

            for num in range(self.analog_channels):
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

            use_as_tick = bool(row[self.cfg_param_pbe['use']])

            # create here actually the object with all the obtained information:

            pbe_obj_list[row_index] = Pulse_Block_Element(
                        init_length_bins=init_length_bins,
                        analog_channels=analog_channels,
                        digital_channels=digital_channels,
                        increment_bins=increment_bins,
                        pulse_function=pulse_function,
                        marker_active=marker_active,
                        parameters=parameter_list,
                        use_as_tick=use_as_tick)

        pb_obj = Pulse_Block(pb_name, pbe_obj_list, num_laser_pulses)
        self.save_block(pb_name, pb_obj)
        self.current_block = pb_obj


    def generate_pulse_block_ensemble(self, ensemble_name, ensemble_matrix, laser_channel,
                                      rotating_frame=True):
        """
        Generates from an given table ensemble_matrix a ensemble object.

        @param str ensemble_name: Name of the created Pulse_Block_Ensemble object
        @param np.array ensemble_matrix: structured 2D np.array, matrix, in which the construction
                                         plan for Pulse_Block objects are displayed as rows.
        @param str laser_channel: the channel controlling the laser
        @param bool rotating_frame: optional, whether the phase preservation is mentained
                                    throughout the sequence.

        The dict cfg_param_pb (configuration parameter declaration dict for Pulse_Block) stores how
        the objects are related to each other in a sequencial way. That relationship is used in the
        GUI, where the parameters appear in columns.
        This dict enables the proper access to the desired element in the GUI.
        """


        # list of all the pulse block element objects
        pb_obj_list = [None]*len(ensemble_matrix)

        #FIXME: The whole measurement tick array can be created much more convenient using the
        #       built-in metadata inside the Pulse_Block and Pulse_Block_Ensemble objects.
        #       Maybe it is even better to automatically calculate the measurement_ticks_list inside
        #       the objects refresh_parameters() method

        # here the measurement ticks will be saved:
        measurement_ticks_list = []

        # to make a resonable measurement tick list, the last biggest tick value after all
        # the repetitions of a block is used as the offset_time for the next
        # block.
        offset_tick_bin = 0

        for row_index, row in enumerate(ensemble_matrix):

            pulse_block_name = row[self.cfg_param_pb['pulse_block']].decode('UTF-8')
            pulse_block_reps = row[self.cfg_param_pb['repetition']]

            block = self.get_pulse_block(pulse_block_name)

            for num in range(pulse_block_reps+1):
                measurement_ticks_list.append(offset_tick_bin + block.init_length_bins + num*block.increment_bins)

            # for the next block, add the biggest time as offset_tick_bin.
            # Otherwise the measurement_ticks_list will be a mess.
            offset_tick_bin = offset_tick_bin + block.init_length_bins + (pulse_block_reps)*block.increment_bins
            pb_obj_list[row_index] = (block, pulse_block_reps)



        laser_channel_index = int(laser_channel[-1]) - 1
        if 'A' in laser_channel:
            self.logMsg('Use of analog channels as laser trigger not implemented yet.', msgType='error')
            laser_channel_index = 0

        pulse_block_ensemble = Pulse_Block_Ensemble(name=ensemble_name,
                                                    block_list=pb_obj_list,
                                                    measurement_ticks_list=measurement_ticks_list,
                                                    laser_channel_index=laser_channel_index,
                                                    rotating_frame=rotating_frame)
        # set current block ensemble
        self.current_ensemble = pulse_block_ensemble
        # save ensemble
        self.save_ensemble(ensemble_name, pulse_block_ensemble)



    def generate_pulse_sequence(self, sequence_name, sequence_matrix, rotating_frame=True):
        """ Generates a Pulse_Sequence object out of the corresponding editor table/matrix.

        @param str sequence_name: name of the created Pulse_Sequence object
        @param np.array sequence_matrix: structured 2D np.array, matrix, in which the construction
                                         plan for Pulse_Block_Ensemble objects are displayed as
                                         rows.
        @param bool rotating_frame: optional, whether the phase preservation is mentained
                                    throughout the sequence.

        Creates a collection of Pulse_Block_Ensemble objects.
        """

        # list of all the Pulse_Block_Ensemble objects and their parameters
        ensemble_param_list = [None] * len(sequence_matrix)


        # calculate the measurement ticks from all the previous measurement ticks in the
        # Pulse_Block_Ensemble objects:
        measurement_ticks_list = []


        # to make a resonable measurement tick list, the last biggest tick value after all
        # the repetitions of a block is used as the offset_time for the next
        # block.
        offset_tick_bin = 0

        for row_index, row in enumerate(sequence_matrix):

            # the ensemble entry must be always (!) present, therefore this entry in the
            # configuration dict for the sequence parameter are taken for granted. Get from the
            # cfg_param_seq the relative situation to the other parameters (which is in the table
            # the column number)

            column_index = self.cfg_param_seq['ensemble']
            pulse_block_ensemble_name = row[column_index].decode('UTF-8')

            # the rest must be obtained together with the actual sequence configuration parameter
            # dict cfg_param_seq and the hardware constraints:
            seq_param_hardware = self.get_hardware_constraints()['sequence_param']

            # here the actual configuration will be save:
            seq_param = dict()

            for param in seq_param_hardware:
                # get the the relative situation to the other parameters (which is in the table
                # the column number):
                column_index = self.cfg_param_seq[param]
                # save in the sequenc parameter dict:
                seq_param[param] = row[column_index]

            # small and simple search routine, which tries to extract a repetition parameter
            # (but the presence of such parameter is not assumed!):
            # All the sequence parameter keywords are string identifiers.
            for param in seq_param:
                if 'reps' in param.lower() or 'repetition' in param.lower():
                    pulse_block_ensemble_reps = seq_param[param]
                    break
                else:
                    pulse_block_ensemble_reps = 0

            # get the reference on the Pulse_Block_Ensemble object:
            pulse_block_ensemble = self.get_pulse_block_ensemble(pulse_block_ensemble_name)

            # append the measurement_ticks_list from the present pulse_block_ensemble depending
            # on the amount of repetitions. Take also care about the offset_tick_bin.
            for num in range(pulse_block_ensemble_reps + 1):
                measurement_ticks_list = np.append(measurement_ticks_list,
                                                   (offset_tick_bin + pulse_block_ensemble.measurement_ticks_list))

                # for the next repetition or pulse_block_ensemble, add last number form the
                # measurement_ticks_list as offset_tick_bin. Otherwise the measurement_ticks_list
                # will be a mess.
                offset_tick_bin = measurement_ticks_list[-1]

            # save in the list the object and sequence parameter
            ensemble_param_list[row_index] = (pulse_block_ensemble, seq_param)

        pulse_sequence = Pulse_Sequence(name=sequence_name,
                                        ensemble_param_list=ensemble_param_list,
                                        measurement_ticks_list=measurement_ticks_list,
                                        rotating_frame=rotating_frame)

        # set current block ensemble
        self.current_sequence = pulse_sequence
        # save ensemble
        self.save_sequence(sequence_name, pulse_sequence)



#-------------------------------------------------------------------------------
#                    END sequence/block generation
#-------------------------------------------------------------------------------


#-------------------------------------------------------------------------------
#                    BEGIN sequence/block sampling
#-------------------------------------------------------------------------------


    def sample_pulse_block_ensemble(self, ensemble_name, write_to_file=True, chunkwise=True,
                                    offset_bin=0):
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

        This method is creating the actual samples (voltages and logic states)
        for each time step of the analog and digital channels specified in
        the Pulse_Block_Ensemble.
        Therefore it iterates through all blocks, repetitions and elements of the
        ensemble and calculates the exact voltages (float64) according to the
        specified math_function. The samples are later on stored inside a float32 array.
        So each element is calculated with high precision (float64) and then
        down-converted to float32 to be stored.

        To preserve the rotating frame, an offset counter is used to indicate
        the absolute time within the ensemble.
        All calculations are done with time bins (dtype=int) to avoid rounding errors.
        Only in the last step when a single Pulse_Block_Element object is sampled
        these integer bin values are translated into a floating point time.

        The chunkwise write mode is used to save memory usage at the expense of time.
        Here for each Pulse_Block_Element the write_to_file method in the HW module
        is called to avoid large arrays inside the memory. In other words: The whole
        sample arrays are never created at any time. This results in more function
        calls and general overhead causing the much longer time to complete.
        """

        start_time = time.time()
        # get ensemble
        ensemble = self.get_pulse_block_ensemble(ensemble_name)
        # Ensemble parameters to determine the shape of sample arrays
        number_of_samples = ensemble.length_bins
        ana_channels = ensemble.analog_channels
        dig_channels = ensemble.digital_channels

        # The time bin offset for each element to be sampled to preserve rotating frame.
        # bin_offset = 0

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
                    marker_active = block_element.marker_active
                    pulse_function = block_element.pulse_function
                    element_length_bins = init_length_bins + (rep_no*increment_bins)

                    # create floating point time array for the current element inside rotating frame
                    time_arr = (bin_offset + np.arange(element_length_bins, dtype='float64')) / self.sample_rate

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
                        for i, state in enumerate(marker_active):
                            digital_samples[i] = np.full(element_length_bins, state, dtype=bool)
                        for i, func_name in enumerate(pulse_function):
                            analog_samples[i] = np.float32(self._math_func[func_name](time_arr, parameters[i])/self.amplitude_list[i+1])

                        # write temporary sample array to file
                        created_files = self._pulse_generator_device.write_samples_to_file(ensemble.name,
                                                                                           analog_samples,
                                                                                           digital_samples,
                                                                                           number_of_samples,
                                                                                           is_first_chunk,
                                                                                           is_last_chunk)
                        # set flag to FALSE after first write
                        is_first_chunk = False
                    else:

                        # if the ensemble should be sampled as a whole (chunkwise = False) fill the
                        # entries in the huge sample arrays
                        for i, state in enumerate(marker_active):
                            digital_samples[i, entry_ind:entry_ind+element_length_bins] = np.full(element_length_bins, state, dtype=bool)
                        for i, func_name in enumerate(pulse_function):
                            analog_samples[i, entry_ind:entry_ind+element_length_bins] = np.float32(self._math_func[func_name](time_arr, parameters[i])/self.amplitude_list[i+1])

                        # increment the index offset of the overall sample array for the next
                        # element
                        entry_ind += element_length_bins

                    # if the rotating frame should be preserved (default) increment the offset
                    # counter for the time array.
                    if ensemble.rotating_frame:
                        bin_offset += element_length_bins

        if not write_to_file:
            # return a status message with the time needed for sampling the entire ensemble as a
            # whole without writing to file.
            self.logMsg('Time needed for sampling as a whole without writing to file: "{0}" '
                        'sec'.format(str(int(np.rint(time.time()-start_time)))), msgType='status')
            # return the sample arrays for write_to_file was set to FALSE


            return analog_samples, digital_samples, created_files, offset_bin
        elif chunkwise:
            # return a status message with the time needed for sampling and writing the ensemble
            # chunkwise.
            self.logMsg('Time needed for sampling and writing to file chunkwise: "{0}" '
                        'sec'.format(str(int(np.rint(time.time()-start_time)))), msgType='status')
            return analog_samples, digital_samples, created_files, offset_bin
        else:
            # If the sampling should not be chunkwise and write to file is enabled call the
            # write_to_file method only once with both flags set to TRUE
            is_first_chunk = True
            is_last_chunk = True
            created_files = self._pulse_generator_device.write_samples_to_file(ensemble.name,
                                                                               analog_samples,
                                                                               digital_samples,
                                                                               number_of_samples,
                                                                               is_first_chunk,
                                                                               is_last_chunk)
            # return a status message with the time needed for sampling and writing the ensemble as
            # a whole.
            self.logMsg('Time needed for sampling and writing to file as a whole: "{0}" '
                        'sec'.format(str(int(np.rint(time.time()-start_time)))), msgType='status')
            return analog_samples, digital_samples, created_files, offset_bin


    def sample_pulse_sequence(self, sequence_name, write_to_file=True, chunkwise=True):
        """ Samples the Pulse_Sequence object, which serves as the construction plan.

        @param str ensemble_name: Name, which should correlate with the name of on of the displayed
                                  ensembles.
        @param bool write_to_file: Write either to RAM or to File (depends on the available space
                                   in RAM). If set to FALSE, this method will return the samples
                                   (digital and analog) as numpy arrays
        @param bool chunkwise: Decide, whether you want to write chunkwise, which will reduce
                               memory usage but will increase vastly the amount of time needed.

        The sequence object is sampled by call subsequently the sampling routine of the
        pulse_block_element routine.
        """



        pass


    #---------------------------------------------------------------------------
    #                    END sequence/block sampling
    #---------------------------------------------------------------------------


    # --------------------------------------------------------------------------
    #                    BEGIN predefined methods
    # --------------------------------------------------------------------------

    #Fixme: This method has to be fixed
    #Question: How can I gate the samle_rate here.
    def generate_laser_on(self, name='Laser_On'):

        laser_time_bins = self.sample_rate*3e-6 #3mus
        no_analog_params = [{},{}]

        #Fixme: Check for channels
        laser_markers = [False, True, False, False]

        # generate elements
        # parameters of a Pulse_Block_Element:
        #init_length_bins, analog_channels, digital_channels,
        #         increment_bins = 0, pulse_function = None,
        #         marker_active = None, parameters={}, use_as_tick=False
        laser_element = Pulse_Block_Element(laser_time_bins, 2, 4, 0,
                                            ['Idle', 'Idle'], laser_markers,
                                            no_analog_params)

        # Create the Pulse_Block_Element objects and append them to the element
        # list.
        element_list = [ ]
        element_list.append(laser_element)

        measurement_ticks_list = [laser_time_bins]

        # create the Pulse_Block object.
        block = Pulse_Block(name, element_list)
        # put block in a list with repetitions
        block_list = [(block, 0),]
        # create ensemble out of the block(s)
        block_ensemble = Pulse_Block_Ensemble(name, block_list, measurement_ticks_list,
                                              len(measurement_ticks_list),
                                              rotating_frame=False)
        # save block
        self.save_block(name, block)
        # save ensemble
        self.save_ensemble(name, block_ensemble)
        # set current block
        self.current_block = block
        # set current block ensemble
        self.current_ensemble = block_ensemble
        # update ensemble list
        self.refresh_ensemble_list()
        return


    def generate_rabi(self, name='rabi', mw_freq_Hz=7784.13, mw_amp_V=1.0, aom_delay_bins=50,
                      laser_time_bins=3000, tau_start_bins=7, tau_end_bins=350,
                      number_of_taus=49, use_seqtrig=True):

        # create parameter dictionary list for MW signal
        mw_params = [{},{}]
        mw_params[0]['frequency1'] = mw_freq_Hz
        mw_params[0]['amplitude1'] = mw_amp_V
        mw_params[0]['phase1'] = 0

        no_analog_params = [{},{}]
        laser_markers = [True, True, False, False]
        gate_markers = [False, True, False, False]
        idle_markers = [False, False, False, False]
        seqtrig_markers = [False, False, True, False]

        # create tau list
        measurement_ticks_list = np.linspace(tau_start_bins, tau_end_bins, number_of_taus,
                               dtype=int)

        # generate elements
        laser_element = Pulse_Block_Element(laser_time_bins, 2, 4, 0,
                                            ['Idle', 'Idle'], laser_markers,
                                            no_analog_params)
        aomdelay_element = Pulse_Block_Element(aom_delay_bins, 2, 4, 0,
                                               ['Idle', 'Idle'], gate_markers,
                                               no_analog_params)
        waiting_element = Pulse_Block_Element((1e-6*self.sample_rate)-
                                              aom_delay_bins, 2, 4, 0,
                                              ['Idle', 'Idle'], idle_markers,
                                              no_analog_params)
        seqtrig_element = Pulse_Block_Element(250, 2, 4, 0, ['Idle', 'Idle'],
                                              seqtrig_markers,
                                              no_analog_params)

        # Create the Pulse_Block_Element objects and append them to the element
        # list.
        element_list = []
        for tau in measurement_ticks_list:
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
        block_ensemble = Pulse_Block_Ensemble(name, block_list, measurement_ticks_list,
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
        no_analog_params = [{},{}]
        laser_markers = [True, True, False, False]
        gate_markers = [False, True, False, False]
        idle_markers = [False, False, False, False]
        seqtrig_markers = [False, False, True, False]

        # create frequency list
        freq_list = np.linspace(start_freq, stop_freq, number_of_points)

        # generate elements
        laser_element = Pulse_Block_Element(laser_time_bins, 2, 4, 0, ['Idle', 'Idle'], laser_markers, no_analog_params)
        aomdelay_element = Pulse_Block_Element(aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], gate_markers, no_analog_params)
        waiting_element = Pulse_Block_Element((1e-6*self.sample_rate)-aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analog_params)
        seqtrig_element = Pulse_Block_Element(250, 2, 4, 0, ['Idle', 'Idle'], seqtrig_markers, no_analog_params)
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
        no_analog_params = [{},{}]
        laser_markers = [True, True, False, False]
        gate_markers = [False, True, False, False]
        idle_markers = [False, False, False, False]
        seqtrig_markers = [False, False, True, False]

        # create tau lists
        measurement_ticks_list = np.linspace(tau_start_bins, tau_end_bins, number_of_taus)
        tauhalf_list = measurement_ticks_list/2
        # correct taus for nonzero-length pi- and pi/2-pulses
        measurement_ticks_list_corr = measurement_ticks_list - pi_bins
        tauhalf_list_corr = tauhalf_list - (pi_bins/2) - (pihalf_bins/2)
        # round lists to nearest integers
        measurement_ticks_list_corr = np.array(np.rint(measurement_ticks_list), dtype=int)
        tauhalf_list_corr = np.array(np.rint(tauhalf_list), dtype=int)
        measurement_ticks_list = np.array(np.rint(measurement_ticks_list), dtype=int)
        tauhalf_list = np.array(np.rint(tauhalf_list), dtype=int)

        # generate elements
        laser_element = Pulse_Block_Element(laser_time_bins, 2, 4, 0, ['Idle', 'Idle'], laser_markers, no_analog_params)
        aomdelay_element = Pulse_Block_Element(aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], gate_markers, no_analog_params)
        waiting_element = Pulse_Block_Element((1e-6*self.sample_rate)-aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analog_params)
        seqtrig_element = Pulse_Block_Element(250, 2, 4, 0, ['Idle', 'Idle'], seqtrig_markers, no_analog_params)
        pihalf_element = Pulse_Block_Element(pihalf_bins, 2, 4, 0, ['Sin', 'Idle'], idle_markers, pihalf_pix_params)
        pi_x_element = Pulse_Block_Element(pi_bins, 2, 4, 0, ['Sin', 'Idle'], idle_markers, pihalf_pix_params)
        pi_y_element = Pulse_Block_Element(pi_bins, 2, 4, 0, ['Sin', 'Idle'], idle_markers, piy_params)

        # generate block list
        blocks = []
        for tau_ind in range(len(measurement_ticks_list_corr)):
            # create tau and tauhalf elements
            tau_element = Pulse_Block_Element(measurement_ticks_list_corr[tau_ind], 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analog_params)
            tauhalf_element = Pulse_Block_Element(tauhalf_list_corr[tau_ind], 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analog_params)

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
            blocks.append(Pulse_Block('XY8_' + str(N) + '_taubins_' + str(measurement_ticks_list[tau_ind]), elements))

        # seqeunce trigger for FPGA counter
        if use_seqtrig:
            tail_elements = [seqtrig_element]
            blocks.append(Pulse_Block('XY8_' + str(N) + '_tail', tail_elements))

        # generate block ensemble (the actual whole measurement sequence)
        block_list = []
        for block in blocks:
            block_list.append((block, 0))
        # name = 'XY8_' + str(N) + '_taustart_' + str(measurement_ticks_list[0]) + '_tauend_' +
        # str(measurement_ticks_list[-1]) + '_numtaus_' + str(len(measurement_ticks_list))
        XY8_ensemble = Pulse_Block_Ensemble(name, block_list, measurement_ticks_list, number_of_taus, True)
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
        no_analog_params = [{},{}]
        laser_markers = [False, False, True, False]
        # gate_markers = [False, False, False, False]
        idle_markers = [False, False, False, False]
        seqtrig_markers = [False, False, False, True]

        # create amplitude list
        amp_list = np.linspace(spinlock_start_V, spinlock_stop_V, number_of_points, dtype=int)

        # generate elements
        laser_element = Pulse_Block_Element(laser_time_bins, 2, 4, 0, ['Idle', 'Idle'], laser_markers, no_analog_params)
        aomdelay_element = Pulse_Block_Element(aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analog_params)
        waiting_element = Pulse_Block_Element((1e-6*self.sampling_freq)-aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analog_params)
        seqtrig_element = Pulse_Block_Element(250, 2, 4, 0, ['Idle', 'Idle'], seqtrig_markers, no_analog_params)
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
        no_analog_params = [{},{}]
        laser_markers = [False, False, True, False]
        # gate_markers = [False, False, False, False]
        idle_markers = [False, False, False, False]
        seqtrig_markers = [False, False, False, True]

        # create tau list
        measurement_ticks_list = np.linspace(spinlock_start_bins, spinlock_stop_bins, number_of_taus, dtype=int)

        # generate elements
        laser_element = Pulse_Block_Element(laser_time_bins, 2, 4, 0, ['Idle', 'Idle'], laser_markers, no_analog_params)
        aomdelay_element = Pulse_Block_Element(aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analog_params)
        waiting_element = Pulse_Block_Element((1e-6*self.sampling_freq)-aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analog_params)
        seqtrig_element = Pulse_Block_Element(250, 2, 4, 0, ['Idle', 'Idle'], seqtrig_markers, no_analog_params)
        pihalf_element = Pulse_Block_Element(pihalf_bins, 2, 4, 0, ['Sin', 'Idle'], idle_markers, pihalf_params)
        pi3half_element = Pulse_Block_Element(pi3half_bins, 2, 4, 0, ['Sin', 'Idle'], idle_markers, pihalf_params)
        # put elements in a list to create the block
        element_list = []
        for tau in measurement_ticks_list:
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
        block_ensemble = Pulse_Block_Ensemble(name, block_list, measurement_ticks_list, number_of_taus*2, True)
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
        no_analog_params = [{},{}]
        laser_markers = [False, False, True, False]
        # gate_markers = [False, False, False, False]
        idle_markers = [False, False, False, False]
        seqtrig_markers = [False, False, False, True]

        # create tau list
        measurement_ticks_list = np.linspace(tau_start_bins, tau_end_bins, number_of_taus, dtype=int)

        # generate elements
        laser_element = Pulse_Block_Element(laser_time_bins, 2, 4, 0, ['Idle', 'Idle'], laser_markers, no_analog_params)
        aomdelay_element = Pulse_Block_Element(aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analog_params)
        waiting_element = Pulse_Block_Element((1e-6*self.sampling_freq)-aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analog_params)
        seqtrig_element = Pulse_Block_Element(250, 2, 4, 0, ['Idle', 'Idle'], seqtrig_markers, no_analog_params)
        pihalf_element = Pulse_Block_Element(pihalf_bins, 2, 4, 0, ['Sin', 'Idle'], idle_markers, pihalf_params)
        # put elements in a list to create the block
        element_list = []
        for tau in measurement_ticks_list:
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
        block_ensemble = Pulse_Block_Ensemble(name, block_list, measurement_ticks_list, number_of_taus, True)
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
        no_analog_params = [{},{}]
        laser_markers = [False, False, True, False]
        gate_markers = [False, False, False, False]
        idle_markers = [False, False, False, False]
        seqtrig_markers = [False, False, False, True]

        # create tau list
        measurement_ticks_list = np.linspace(tau_start_bins, tau_end_bins, number_of_taus, dtype=int)

        # generate elements
        laser_element = Pulse_Block_Element(laser_time_bins, 2, 4, 0, ['Idle', 'Idle'], laser_markers, no_analog_params)
        aomdelay_element = Pulse_Block_Element(aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], gate_markers, no_analog_params)
        waiting_element = Pulse_Block_Element((1e-6*self.sampling_freq)-aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analog_params)
        seqtrig_element = Pulse_Block_Element(250, 2, 4, 0, ['Idle', 'Idle'], seqtrig_markers, no_analog_params)
        # put elements in a list to create the block
        element_list = []
        for tau in measurement_ticks_list:
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
        block_ensemble = Pulse_Block_Ensemble(name, block_list, measurement_ticks_list, number_of_taus, False)
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

    # --------------------------------------------------------------------------
    #                    END  predefined methods
    # --------------------------------------------------------------------------
