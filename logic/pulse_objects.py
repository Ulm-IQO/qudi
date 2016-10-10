# -*- coding: utf-8 -*-

"""
This file contains the Qudi data object classes needed for pulse sequence generation.

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

import numpy as np
from collections import OrderedDict


class Pulse_Block_Element:
    """ Object representing a single atomic element in a pulse block.

    This class can build waiting times, sine waves, etc. The pulse block may
    contain many Pulse_Block_Element Objects. These objects can be displayed in
    a GUI as single rows of a Pulse_Block.
    """
    def __init__(self, init_length_bins, increment_bins=0, pulse_function=None, digital_high=None,
                 parameters=None, use_as_tick=False):
        """ The constructor for a Pulse_Block_Element needs to have:

        @param int init_length_bins: an initial length of a bins, this
                                 parameters should not be zero but must have a
                                 finite value.
        @param int increment_bins: the number which will be incremented during
                               each repetition of this object
        @param list pulse_function: list of strings with name of the sampling
                                    function how to alter the points, the name
                                    of the function will be one of the sampling
                                    functions
        @param list digital_high: list of digital channels, which are for the
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
        if parameters is None:
            parameters = []
        # FIXME: Sanity checks need to be implemented here
        self.init_length_bins   = init_length_bins
        self.increment_bins     = increment_bins
        self.pulse_function     = pulse_function
        self.digital_high       = digital_high
        self.parameters         = parameters
        self.use_as_tick        = use_as_tick

        # calculate number of digital and analogue channels
        if pulse_function is not None:
            self.analog_channels = len(pulse_function)
        else:
            self.analog_channels = 0
        if digital_high is not None:
            self.digital_channels = len(digital_high)
        else:
            self.digital_channels = 0


class Pulse_Block:
    """ Collection of Pulse_Block_Elements which is called a Pulse_Block. """

    def __init__(self, name, element_list):
        """ The constructor for a Pulse_Block needs to have:

        @param str name: chosen name for the Pulse_Block
        @param list element_list: which contains the Pulse_Block_Element
                             Objects forming a Pulse_Block, e.g.
                             [Pulse_Block_Element, Pulse_Block_Element, ...]
        """
        self.name = name
        self.element_list = element_list
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
        self.use_as_tick = False

        # calculate the tick value for the whole block. Basically sum all the
        # init_length_bins which have the use_as_tick attribute set to True.
        self.measurement_tick_start = 0
        # make the same thing for the increment, to obtain the total increment
        # number for the block. This facilitates in calculating the measurement tick list.
        self.measurement_tick_increment = 0

        for elem in self.element_list:
            self.init_length_bins += elem.init_length_bins
            self.increment_bins += elem.increment_bins

            if elem.use_as_tick:
                self.use_as_tick = True
                self.measurement_tick_start += elem.init_length_bins
                self.measurement_tick_increment += elem.increment_bins

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


class Pulse_Block_Ensemble:
    """ Represents a collection of Pulse_Block objects which is called a
        Pulse_Block_Ensemble.

    This object is used as a construction plan to create one sampled file.
    """

    def __init__(self, name, block_list, activation_config, sample_rate, laser_channel=None, rotating_frame=True):
        """ The constructor for a Pulse_Block_Ensemble needs to have:

        @param str name: chosen name for the Pulse_Block_Ensemble
        @param list block_list: contains the Pulse_Block Objects with their number of repetitions,
                                e.g.
                                    [(Pulse_Block, repetitions), (Pulse_Block, repetitions), ...])
        @param list activation_config: A list of strings representing the channel configuration
                                        e.g. ['a_ch1', 'd_ch1', 'd_ch2', 'a_ch2']
        @param float sample_rate: The sample rate in Hz the ensemble was created for.
        @param str laser_channel: The string descriptor for the laser channel.
                                    Must be contained by the passed activation_config.
        @param bool rotating_frame: indicates whether the phase should be preserved for all the
                                    functions.
        """
        # FIXME: Sanity checking needed here
        self.name = name                    # Pulse_Block_Ensemble name
        self.block_list = block_list
        self.activation_config = activation_config
        self.sample_rate = sample_rate
        self.rotating_frame = rotating_frame
        self.length_bins = 0
        self.analog_channels = 0
        self.digital_channels = 0
        self.number_of_lasers = 0
        self.laser_length_bins = 0
        self.measurement_ticks_list = np.array([])
        if laser_channel in activation_config:
            self.laser_channel = laser_channel
        else:
            self.laser_channel = None
        self.refresh_parameters()

    def refresh_parameters(self):
        self.length_bins = 0
        self.analog_channels = 0
        self.digital_channels = 0
        self.number_of_lasers = 0
        self.laser_length_bins = 0
        # calculate the tick values for the whole block_ensemble.
        self.measurement_ticks_list = np.array([])

        for block, reps in self.block_list:
            # Get number of channels from the block information
            if block.analog_channels > self.analog_channels:
                self.analog_channels = block.analog_channels
            if block.digital_channels > self.digital_channels:
                self.digital_channels = block.digital_channels

            # Get and set information about the length of the ensemble
            self.length_bins += (block.init_length_bins * (reps+1) + block.increment_bins * (reps*(reps+1)/2))

            # Calculate the measurement ticks list for this ensemble
            if block.use_as_tick:
                start = block.measurement_tick_start
                incr = block.measurement_tick_increment
                if incr == 0:
                    arr = np.array([])
                else:
                    arr = np.arange(start, start+(reps+1)*incr, incr)
                self.measurement_ticks_list = np.append(self.measurement_ticks_list, arr)

            # Calculate the number of laser pulses for this ensemble
            if self.laser_channel is None:
                self.number_of_lasers = 0
                self.laser_length_bins = 0
            elif 'd_ch' in self.laser_channel:
                # determine the laser channel index for the corresponding channel
                digital_chnl_list = [chnl for chnl in self.activation_config if 'd_ch' in chnl]
                laser_index = digital_chnl_list.index(self.laser_channel)
                # Iterate through the elements and count laser on state changes (no double counting)
                # Also accumulate the length of the laser pulse in bins and determine the longest
                laser_on = False
                tmp_laser_length = 0
                for elem in block.element_list:
                    if elem.digital_high[laser_index]:
                        if not laser_on:
                            self.number_of_lasers += 1 + reps
                            laser_on = True
                            tmp_laser_length = elem.init_length_bins + elem.increment_bins * reps
                        else:
                            tmp_laser_length += elem.init_length_bins + elem.increment_bins * reps
                    else:
                        laser_on = False
                        tmp_laser_length = 0
                    if self.laser_length_bins < tmp_laser_length:
                        self.laser_length_bins = tmp_laser_length
            elif 'a_ch' in self.laser_channel:
                # determine the laser channel index for the corresponding channel
                analog_chnl_list = [chnl for chnl in self.activation_config if 'a_ch' in chnl]
                laser_index = analog_chnl_list.index(self.laser_channel)
                # Iterate through the elements and count laser on state changes (no double counting)
                # Also accumulate the length of the laser pulse in bins and determine the longest
                laser_on = False
                tmp_laser_length = 0
                for elem in block.element_list:
                    if elem.pulse_function[laser_index] == 'DC':
                        if not laser_on:
                            self.number_of_lasers += 1 + reps
                            laser_on = True
                            tmp_laser_length = elem.init_length_bins + elem.increment_bins * reps
                        else:
                            tmp_laser_length += elem.init_length_bins + elem.increment_bins * reps
                    else:
                        laser_on = False
                        tmp_laser_length = 0
                    if self.laser_length_bins < tmp_laser_length:
                        self.laser_length_bins = tmp_laser_length
        return

    def replace_block(self, position, block):
        self.block_list[position] = block
        self.refresh_parameters()
        return

    def delete_block(self, position):
        del(self.block_list[position])
        self.refresh_parameters()
        return

    def append_block(self, block, at_beginning=False):
        if at_beginning:
            self.block_list.insert(0, block)
        else:
            self.block_list.append(block)
        self.refresh_parameters()
        return


class Pulse_Sequence:
    """ Higher order object for sequence capability.

    Represents a playback procedure for a number of Pulse_Block_Ensembles.
    Unused for pulse generator hardware without sequencing functionality.
    """

    def __init__(self, name, ensemble_param_list, rotating_frame=True):
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
        @param bool rotating_frame: indicates, whether the phase has to be preserved in all
                                    oscillating functions.
        """

        self.name = name
        self.ensemble_param_list = ensemble_param_list
        self.rotating_frame = rotating_frame
        self.refresh_parameters()
        self.sampled_ensembles = OrderedDict()

    def refresh_parameters(self):
        """ Generate the needed parameters from the passed object.

        Baiscally, calculate the length_bins and number of analog and digital
        channels.
        """
        self.length_bins = 0
        self.analog_channels = 0
        self.digital_channels = 0
        # here all DIFFERENT kind of ensembles will be saved in, i.e. with different names.
        # REMEMBER: A dict is hashable, that means, you will get its entry with the complexity of 1
        #           without searching through the whole dict!
        self.different_ensembles_dict = dict()

        # here the measurement ticks will be saved:
        self.measurement_ticks_list = []

        self.number_of_lasers = 0
        # to make a resonable measurement tick list, the last biggest tick value after all
        # the repetitions of a block is used as the offset_time for the next
        # block.
        offset_tick_bin = 0

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

            if self.different_ensembles_dict.get(ensemble.name) is None:
                self.different_ensembles_dict[ensemble.name] = ensemble

            self.measurement_ticks_list = np.append(self.measurement_ticks_list,
                                                   (offset_tick_bin + ensemble.measurement_ticks_list))

            self.number_of_lasers += ensemble.number_of_lasers

            # for the next repetition or pulse_block_ensemble, add last number
            # from the measurement_ticks_list as offset_tick_bin. Otherwise the
            # measurement_ticks_list will be a mess:
            if len(self.measurement_ticks_list) > 0:
                offset_tick_bin = self.measurement_ticks_list[-1]

        self.estimated_bytes = self.length_bins * (self.analog_channels * 4 + self.digital_channels)

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
            self.ensemble_list.insert(0, ensemble_param)
        else:
            self.ensemble_list.append(ensemble_param)
        self.refresh_parameters()

    #TODO: Experimental, check how necessary that method is and replace by other idea if needed:
    def set_sampled_ensembles(self, sampled_dict):
        """ Set the dict, containing the sampled ensembles of the sequence.

        @param dict sampled_dict: the ordered dictionary with a list of strings telling about the
                                  actual names of the created sequences
        """
        self.sampled_ensembles = sampled_dict

    # TODO: Experimental, check how necessary that method is and replace by other idea if needed:
    def get_sampled_ensembles(self):
        """ Retrieve the dict, which tells into which names the ensembles have been sampled

        @return dict: a dict with keys being the ensemble names and items being a list of string
                      names, which were created by the hardware.
        """
        return self.sampled_ensembles