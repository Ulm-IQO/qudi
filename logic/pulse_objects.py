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


class PulseBlockElement:
    """
    Object representing a single atomic element in a pulse block.

    This class can build waiting times, sine waves, etc. The pulse block may
    contain many Pulse_Block_Element Objects. These objects can be displayed in
    a GUI as single rows of a Pulse_Block.
    """
    def __init__(self, init_length_s, increment_s=0, pulse_function=None, digital_high=None,
                 parameters=None, use_as_tick=False):
        """
        The constructor for a Pulse_Block_Element needs to have:

        @param int init_length_s: an initial length of the element, this
                                 parameters should not be zero but must have a
                                 finite value.
        @param int increment_s: the number which will be incremented during
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
        self.init_length_s  = init_length_s
        self.increment_s    = increment_s
        self.pulse_function = pulse_function
        self.digital_high   = digital_high
        self.parameters     = parameters
        self.use_as_tick    = use_as_tick
        # calculate number of digital and analogue channels
        if pulse_function is not None:
            self.analog_channels = len(pulse_function)
        else:
            self.analog_channels = 0
        if digital_high is not None:
            self.digital_channels = len(digital_high)
        else:
            self.digital_channels = 0


class PulseBlock:
    """
    Collection of Pulse_Block_Elements which is called a Pulse_Block.
    """
    def __init__(self, name, element_list):
        """
        The constructor for a Pulse_Block needs to have:

        @param str name: chosen name for the Pulse_Block
        @param list element_list: which contains the Pulse_Block_Element Objects forming a
                                  Pulse_Block, e.g. [Pulse_Block_Element, Pulse_Block_Element, ...]
        """
        self.name = name
        self.element_list = element_list
        self.init_length_s = None
        self.increment_s = None
        self.analog_channels = None
        self.digital_channels = None
        self.use_as_tick = None
        self._refresh_parameters()

    def _refresh_parameters(self):
        """ Initialize the parameters which describe this Pulse_Block object.

        The information is gained from all the Pulse_Block_Element objects,
        which are attached in the element_list.
        """
        # the Pulse_Block parameter
        self.init_length_s = 0.0
        self.increment_s = 0.0
        self.analog_channels = 0
        self.digital_channels = 0
        self.use_as_tick = False

        # calculate the tick value for the whole block. Basically sum all the
        # init_length_bins which have the use_as_tick attribute set to True.
        self.controlled_vals_start = 0.0
        # make the same thing for the increment, to obtain the total increment
        # number for the block. This facilitates in calculating the measurement tick list.
        self.controlled_vals_increment = 0.0

        for elem in self.element_list:
            self.init_length_s += elem.init_length_s
            self.increment_s += elem.increment_s
            if elem.use_as_tick:
                self.use_as_tick = True
                self.controlled_vals_start += elem.init_length_s
                self.controlled_vals_increment += elem.increment_s

            if elem.analog_channels > self.analog_channels:
                self.analog_channels = elem.analog_channels
            if elem.digital_channels > self.digital_channels:
                self.digital_channels = elem.digital_channels

    def replace_element(self, position, element):
        self.element_list[position] = element
        self._refresh_parameters()
        return

    def delete_element(self, position):
        del(self.element_list[position])
        self._refresh_parameters()
        return

    def append_element(self, element, at_beginning=False):
        if at_beginning:
            self.element_list.insert(0, element)
        else:
            self.element_list.append(element)
        self._refresh_parameters()
        return


class PulseBlockEnsemble:
    """
    Represents a collection of Pulse_Block objects which is called a Pulse_Block_Ensemble.

    This object is used as a construction plan to create one sampled file.
    """
    def __init__(self, name, block_list, rotating_frame=True):
        """
        The constructor for a Pulse_Block_Ensemble needs to have:

        @param str name: chosen name for the Pulse_Block_Ensemble
        @param list block_list: contains the Pulse_Block Objects with their number of repetitions,
                                e.g. [(Pulse_Block, repetitions), (Pulse_Block, repetitions), ...])
        @param bool rotating_frame: indicates whether the phase should be preserved for all the
                                    functions.
        """
        # FIXME: Sanity checking needed here
        self.name = name                    # Pulse_Block_Ensemble name
        self.block_list = block_list
        self.rotating_frame = rotating_frame
        self.length_s = 0
        self.analog_channels = 0
        self.digital_channels = 0
        self.controlled_vals_array = np.array([])
        self._refresh_parameters()
        # these parameters can be set manually by the logic to recall the pulser settings upon
        # loading into channels. They are not crucial for waveform generation.
        self.sample_rate = None
        self.activation_config = None
        self.amplitude_dict = None
        self.laser_channel = None
        self.alternating = None
        self.laser_ignore_list = None
        self.length_bins = None
        self.length_elements_bins = None
        self.number_of_elements = None
        self.digital_rising_bins = None
        return

    def _refresh_parameters(self):
        self.length_s = 0
        self.analog_channels = 0
        self.digital_channels = 0
        # calculate the tick values for the whole block_ensemble.
        self.controlled_vals_array = np.array([])
        for block, reps in self.block_list:
            # Get number of channels from the block information
            if block.analog_channels > self.analog_channels:
                self.analog_channels = block.analog_channels
            if block.digital_channels > self.digital_channels:
                self.digital_channels = block.digital_channels

            # Get and set information about the length of the ensemble
            self.length_s += (block.init_length_s * (reps+1) + block.increment_s * (reps*(reps+1)/2))

            # Calculate the measurement ticks list for this ensemble
            if block.use_as_tick:
                start = block.controlled_vals_start
                incr = block.controlled_vals_increment
                if incr == 0.0:
                    arr = np.array([])
                else:
                    arr = np.arange(start, start+(reps+1)*incr, incr)
                self.controlled_vals_array = np.append(self.controlled_vals_array, arr)
        return

    def replace_block(self, position, block):
        self.block_list[position] = block
        self._refresh_parameters()
        return

    def delete_block(self, position):
        del(self.block_list[position])
        self._refresh_parameters()
        return

    def append_block(self, block, at_beginning=False):
        if at_beginning:
            self.block_list.insert(0, block)
        else:
            self.block_list.append(block)
        self._refresh_parameters()
        return


class PulseSequence:
    """
    Higher order object for sequence capability.

    Represents a playback procedure for a number of Pulse_Block_Ensembles. Unused for pulse
    generator hardware without sequencing functionality.
    """
    def __init__(self, name, ensemble_param_list, rotating_frame=True):
        """
        The constructor for a Pulse_Sequence objects needs to have:

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
        self.length_s = 0.0
        self.analog_channels = 0
        self.digital_channels = 0
        self.controlled_vals_array = np.array([])
        self._refresh_parameters()
        self.sampled_ensembles = OrderedDict()
        # these parameters can be set manually by the logic to recall the pulser settings upon
        # loading into channels. They are not crucial for waveform generation.
        self.sample_rate = None
        self.activation_config = None
        self.amplitude_dict = None
        self.laser_channel = None
        self.alternating = None
        self.laser_ignore_list = None
        self.length_bins = None
        self.length_elements_bins = None
        self.number_of_elements = None
        self.digital_rising_bins = None
        return

    def _refresh_parameters(self):
        """ Generate the needed parameters from the passed object.

        Baiscally, calculate the length_bins and number of analog and digital
        channels.
        """
        self.length_bins = 0
        self.analog_channels = 0
        self.digital_channels = 0
        # here all DIFFERENT kind of ensembles will be saved in, i.e. with different names.
        self.different_ensembles_dict = dict()
        # here the measurement ticks will be saved:
        self.controlled_vals_array = np.array([])

        # to make a resonable measurement tick list, the last biggest tick value after all
        # the repetitions of a block is used as the offset_time for the next block.
        offset_tick_bin = 0
        for ensemble, seq_dict in self.ensemble_param_list:
            for param in seq_dict:
                if 'reps' in param.lower() or 'repetition' in param.lower():
                    reps = seq_dict[param]
                    break
                else:
                    reps = 0
            self.length_s += (ensemble.length_s * (reps+1))

            if ensemble.analog_channels > self.analog_channels:
                self.analog_channels = ensemble.analog_channels
            if ensemble.digital_channels > self.digital_channels:
                self.digital_channels = ensemble.digital_channels

            if self.different_ensembles_dict.get(ensemble.name) is None:
                self.different_ensembles_dict[ensemble.name] = ensemble

            if hasattr(ensemble, 'controlled_vals_array'):
                self.controlled_vals_array = np.append(self.controlled_vals_array,
                                                       offset_tick_bin +
                                                       ensemble.controlled_vals_array)

            # for the next repetition or pulse_block_ensemble, add last number from the
            # controlled_vals_array as offset_tick_bin. Otherwise the controlled_vals_array will
            # be a mess:
            if len(self.controlled_vals_array) > 0:
                offset_tick_bin = self.controlled_vals_array[-1]
        return

    def replace_ensemble(self, position, ensemble_param):
        """ Replace an ensemble at a given position.

        @param int position: position in a the ensemble list
        @param list ensemble_param: with entries
                                        (Pulse_Block_Ensemble, seq_param)
                                    which will replace the old one.
        """
        self.ensemble_param_list[position] = ensemble_param
        self._refresh_parameters()
        return

    def delete_ensemble(self, position):
        """ Delete an ensemble at a given position

        @param int position: position within the list self.ensemble_param_list.
        """
        del(self.ensemble_list[position])
        self._refresh_parameters()

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
        self._refresh_parameters()
