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


class PulseBlockElement(object):
    """
    Object representing a single atomic element in a pulse block.

    This class can build waiting times, sine waves, etc. The pulse block may
    contain many Pulse_Block_Element Objects. These objects can be displayed in
    a GUI as single rows of a Pulse_Block.
    """
    def __init__(self, init_length_s=10e-9, increment_s=0, pulse_function=None, digital_high=None,
                 use_as_tick=False):
        """
        The constructor for a Pulse_Block_Element needs to have:

        @param float init_length_s: an initial length of the element, this parameters should not be
                                    zero but must have a finite value.
        @param float increment_s: the number which will be incremented during each repetition of
                                  this element.
        @param dict pulse_function: dictionary with keys being the qudi analog channel string
                                    descriptors ('a_ch1', 'a_ch2' etc.) and the corresponding
                                    objects being instances of the mathematical function objects
                                    found in "sampling_functions.py".
        @param dict digital_high: dictionary with keys being the qudi digital channel string
                                  descriptors ('d_ch1', 'd_ch2' etc.) and the corresponding objects
                                  being boolean values describing if the channel should be logical
                                  low (False) or high (True).
                                  For 3 digital channel it may look like:
                                  {'d_ch1': True, 'd_ch2': False, 'd_ch5': False}
        @param bool use_as_tick: Indicates, whether the set length should be used as a tick
                                 (i.e. the parameter for the x axis) for the later plot in the
                                 pulse analysis.
        """
        # FIXME: Sanity checks need to be implemented here
        self.init_length_s = init_length_s
        self.increment_s = increment_s
        self.use_as_tick = use_as_tick
        if pulse_function is None:
            self.pulse_function = OrderedDict()
        else:
            self.pulse_function = pulse_function
        if digital_high is None:
            self.digital_high = OrderedDict()
        else:
            self.digital_high = digital_high

        # calculate number of digital and analogue channels
        if pulse_function is not None:
            self.analog_channels = len(pulse_function)
        else:
            self.analog_channels = 0
        if digital_high is not None:
            self.digital_channels = len(digital_high)
        else:
            self.digital_channels = 0


class PulseBlock(object):
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
        self.analog_channels = None
        self.digital_channels = None
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

            if elem.pulse_function is not None:
                if self.analog_channels is None:
                    self.analog_channels = list(elem.pulse_function)
                elif self.analog_channels != list(elem.pulse_function):
                    raise ValueError('Usage of different sets of analog channels in the same PulseBlock'
                                     ' is prohibited.\nPulseBlock creation failed!\nUsed analog channel'
                                     ' sets are:\n{0}\n{1}'.format(self.analog_channels,
                                                                   list(elem.pulse_function)))
                    return

            if elem.digital_high is not None:
                if self.digital_channels is None:
                    self.digital_channels = list(elem.digital_high)
                elif self.digital_channels != list(elem.digital_high):
                    raise ValueError('Usage of different sets of digital channels in the same '
                                     'PulseBlock is prohibited.\nPulseBlock creation failed!\n'
                                     'Used digital channel sets are:\n'
                                     '{0}\n{1}'.format(self.digital_channels, list(elem.digital_high)))
                    return

    def replace_element(self, position, element):
        if isinstance(element, PulseBlockElement) and (len(self.element_list) > position):
            self.element_list[position] = element
            self._refresh_parameters()
            return 0
        else:
            return -1

    def delete_element(self, position):
        if len(self.element_list) > position:
            del(self.element_list[position])
            self._refresh_parameters()
            return 0
        else:
            return -1

    def append_element(self, element, at_beginning=False):
        if isinstance(element, PulseBlockElement):
            if at_beginning:
                self.element_list.insert(0, element)
            else:
                self.element_list.append(element)
            self._refresh_parameters()
            return 0
        else:
            return -1


class PulseBlockEnsemble(object):
    """
    Represents a collection of Pulse_Block objects which is called a Pulse_Block_Ensemble.

    This object is used as a construction plan to create one sampled file.
    """
    def __init__(self, name, block_list, rotating_frame=True):
        """
        The constructor for a Pulse_Block_Ensemble needs to have:

        @param str name: chosen name for the PulseBlockEnsemble
        @param list block_list: contains the PulseBlock objects with their number of repetitions,
                                e.g. [(PulseBlock, repetitions), (PulseBlock, repetitions), ...])
        @param bool rotating_frame: indicates whether the phase should be preserved for all the
                                    functions.
        """
        # FIXME: Sanity checking needed here
        self.name = name                    # Pulse_Block_Ensemble name
        self.block_list = block_list
        self.rotating_frame = rotating_frame
        self.length_s = 0
        self.analog_channels = None
        self.digital_channels = None
        self.controlled_vals_array = np.array([])
        self._refresh_parameters()

        # Dictionary container to store information related to the actually sampled
        # Waveform like pulser settings used during sampling (sample_rate, activation_config etc.)
        # and additional information about the discretization of the waveform (timebin positions of
        # the PulseBlockElement transitions etc.)
        # This container is not necessary for the sampling process but serves only the purpose of
        # holding optional information for different modules.
        self.sampling_information = dict()
        # self.sample_rate = None
        # self.activation_config = None
        # self.amplitude_dict = None
        # self.laser_channel = None
        # self.alternating = None
        # self.laser_ignore_list = None
        # self.length_bins = None
        # self.length_elements_bins = None
        # self.number_of_elements = None
        # self.digital_rising_bins = None
        return

    def _refresh_parameters(self):
        self.length_s = 0
        self.analog_channels = None
        self.digital_channels = None
        # calculate the tick values for the whole block_ensemble.
        self.controlled_vals_array = np.array([])
        for block, reps in self.block_list:
            # Get channels from the block information
            if self.analog_channels is None:
                self.analog_channels = block.analog_channels
            elif self.analog_channels != block.analog_channels:
                raise ValueError('Usage of different sets of analog channels in the same '
                                 'PulseBlockEnsemble is prohibited.\n'
                                 'PulseBlockEnsemble creation failed!\n'
                                 'Used analog channel sets are:\n'
                                 '{0}\n{1}'.format(self.analog_channels, block.analog_channels))
                return

            if self.digital_channels is None:
                self.digital_channels = block.digital_channels
            elif self.digital_channels != block.digital_channels:
                raise ValueError('Usage of different sets of digital channels in the same '
                                 'PulseBlockEnsemble is prohibited.\n'
                                 'PulseBlockEnsemble creation failed!\n'
                                 'Used digital channel sets are:\n'
                                 '{0}\n{1}'.format(self.digital_channels, block.digital_channels))
                return

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

    def replace_block(self, position, block, reps=0):
        if isinstance(block, PulseBlock) and (len(self.block_list) > position):
            self.block_list[position] = (block, reps)
            self._refresh_parameters()
            return 0
        else:
            return -1

    def delete_block(self, position):
        if len(self.block_list) > position:
            del(self.block_list[position])
            self._refresh_parameters()
            return 0
        else:
            return -1

    def append_block(self, block, reps=0, at_beginning=False):
        if isinstance(block, PulseBlock):
            if at_beginning:
                self.block_list.insert(0, (block, reps))
            else:
                self.block_list.append((block, reps))
            self._refresh_parameters()
            return 0
        else:
            return -1


class PulseSequence(object):
    """
    Higher order object for sequence capability.

    Represents a playback procedure for a number of PulseBlockEnsembles. Unused for pulse
    generator hardware without sequencing functionality.
    """
    def __init__(self, name, ensemble_list, rotating_frame=True):
        """
        The constructor for a PulseSequence objects needs to have:

        @param str name: the actual name of the sequence
        @param list ensemble_list: list containing a tuple of two entries:
                    [(PulseBlockEnsemble, seq_param), (PulseBlockEnsemble, seq_param), ...]
                                          The seq_param is a dictionary, where the various sequence
                                          parameters are saved with their keywords and the
                                          according parameter (as item).
                                          Available parameters are:
                                          'repetitions': The number of repetitions for that sequence
                                                         step. (Default 0)
                                                         0 meaning the step is played once.
                                                         Set to -1 for infinite looping.
                                          'go_to':   The sequence step index to jump to after
                                                     having played all repetitions or receiving a
                                                     jump trigger. (Default -1)
                                                     Indices starting at 0 for first step.
                                                     Set to -1 to follow up with the next step.
                                          'event_jump_to': The input trigger channel index used to
                                                          jump to the step defined in 'jump_to'.
                                                          (Default -1)
                                                          Indices starting at 0 for first trigger
                                                          input channel.
                                                          Set to -1 for not listening to triggers.

                                          If only 'repetitions' are in the dictionary, then the dict
                                          will look like:
                                            seq_param = {'reps': 12}
                                          and so the respective sequence step will play 13 times.
        @param bool rotating_frame: indicates, whether the phase has to be preserved in all
                                    oscillating functions.
        """
        self.name = name
        self.ensemble_list = ensemble_list
        self.rotating_frame = rotating_frame
        self.length_s = 0.0
        self.analog_channels = None
        self.digital_channels = None
        self.controlled_vals_array = np.array([])
        # here all DIFFERENT kind of ensembles will be saved in, i.e. with different names.
        self.different_ensembles = dict()
        self._refresh_parameters()
        # self.sampled_ensembles = OrderedDict()
        # Dictionary container to store information related to the actually sampled
        # Waveforms like pulser settings used during sampling (sample_rate, activation_config etc.)
        # and additional information about the discretization of the waveform (timebin positions of
        # the PulseBlockElement transitions etc.)
        # This container is not necessary for the sampling process but serves only the purpose of
        # holding optional information for different modules.
        self.sampling_information = dict()
        # self.sample_rate = None
        # self.activation_config = None
        # self.amplitude_dict = None
        # self.laser_channel = None
        # self.alternating = None
        # self.laser_ignore_list = None
        # self.length_bins = None
        # self.length_elements_bins = None
        # self.number_of_elements = None
        # self.digital_rising_bins = None
        return

    def _refresh_parameters(self):
        """

        @return:
        """
        self.length_s = 0
        self.analog_channels = None
        self.digital_channels = None
        self.different_ensembles = dict()
        self.controlled_vals_array = np.array([])

        # to make a reasonable measurement tick list, the last biggest tick value after all
        # the repetitions of a block is used as the offset_time for the next block.
        offset_tick_bin = 0
        for ensemble, seq_dict in self.ensemble_list:
            if self.length_s >= 0:
                if 'repetitions' in seq_dict:
                    reps = seq_dict['repetitions']
                else:
                    reps = 0

                if reps == -1:
                    self.length_s = -1
                else:
                    self.length_s += (ensemble.length_s * (reps+1))

            # Get channels from the block ensemble information
            if self.analog_channels is None:
                self.analog_channels = ensemble.analog_channels
            elif self.analog_channels != ensemble.analog_channels:
                raise ValueError('Usage of different sets of analog channels in the same '
                                 'PulseSequence is prohibited.\n'
                                 'PulseSequence creation failed!\n'
                                 'Used analog channel sets are:\n'
                                 '{0}\n{1}'.format(self.analog_channels,
                                                   ensemble.analog_channels))
                return

            if self.digital_channels is None:
                self.digital_channels = ensemble.digital_channels
            elif self.digital_channels != ensemble.digital_channels:
                raise ValueError('Usage of different sets of digital channels in the same '
                                 'PulseSequence is prohibited.\n'
                                 'PulseSequence creation failed!\n'
                                 'Used digital channel sets are:\n'
                                 '{0}\n{1}'.format(self.digital_channels,
                                                   ensemble.digital_channels))
                return

            if ensemble.name not in self.different_ensembles:
                self.different_ensembles[ensemble.name] = ensemble

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

    def replace_ensemble(self, position, ensemble, seq_param=None):
        """ Replace a sequence step at a given position.

        @param int position: position in the ensemble list
        @param object ensemble: PulseBlockEnsemble instance
        @param dict seq_param: Sequence step parameter dictionary. Use present one if None.
        """
        if isinstance(ensemble, PulseBlockEnsemble) and (len(self.ensemble_list) > position):
            if seq_param is None:
                self.ensemble_list[position][0] = ensemble
            else:
                self.ensemble_list[position] = (ensemble, seq_param)
            self._refresh_parameters()
            return 0
        else:
            return -1

    def delete_ensemble(self, position):
        """ Delete an ensemble at a given position

        @param int position: position within the list self.ensemble_list.
        """
        if len(self.ensemble_list) > position:
            del(self.ensemble_list[position])
            self._refresh_parameters()
            return 0
        else:
            return -1

    def append_ensemble(self, ensemble, seq_param, at_beginning=False):
        """ Append either at the front or at the back an ensemble_param

        @param object ensemble: PulseBlockEnsemble instance
        @param dict seq_param: Sequence step parameter dictionary.
        @param bool at_beginning: If flase append to end (default), if true then
                                  inset at beginning.
        """
        if isinstance(ensemble, PulseBlockEnsemble):
            if at_beginning:
                self.ensemble_list.insert((ensemble, seq_param))
            else:
                self.ensemble_list.append((ensemble, seq_param))
            self._refresh_parameters()
            return 0
        else:
            return -1
