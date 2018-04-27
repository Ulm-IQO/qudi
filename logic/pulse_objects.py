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
import logic.sampling_functions as sf


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

        # determine set of used digital and analog channels
        self.analog_channels = set(self.pulse_function)
        self.digital_channels = set(self.digital_high)
        self.channel_set = self.analog_channels.union(self.digital_channels)

    def get_dict_representation(self):
        dict_repr = dict()
        dict_repr['init_length_s'] = self.init_length_s
        dict_repr['increment_s'] = self.increment_s
        dict_repr['digital_high'] = self.digital_high
        dict_repr['use_as_tick'] = self.use_as_tick
        dict_repr['pulse_function'] = dict()
        for chnl, func in self.pulse_function.items():
            dict_repr['pulse_function'][chnl] = func.get_dict_representation()
        return dict_repr

    @staticmethod
    def element_from_dict(element_dict):
        for chnl, sample_dict in element_dict['pulse_function'].items():
            sf_class = getattr(sf, sample_dict['name'])
            element_dict['pulse_function'][chnl] = sf_class(**sample_dict['params'])
        return PulseBlockElement(**element_dict)


class PulseBlock(object):
    """
    Collection of Pulse_Block_Elements which is called a Pulse_Block.
    """
    def __init__(self, name, element_list=None):
        """
        The constructor for a Pulse_Block needs to have:

        @param str name: chosen name for the Pulse_Block
        @param list element_list: which contains the Pulse_Block_Element Objects forming a
                                  Pulse_Block, e.g. [Pulse_Block_Element, Pulse_Block_Element, ...]
        """
        self.name = name
        if element_list is None:
            self.element_list = list()
        else:
            self.element_list = element_list
        self.init_length_s = None
        self.increment_s = None
        self.analog_channels = None
        self.digital_channels = None
        self.channel_set = None
        self.refresh_parameters()

    def refresh_parameters(self):
        """ Initialize the parameters which describe this Pulse_Block object.

        The information is gained from all the Pulse_Block_Element objects,
        which are attached in the element_list.
        """
        # the Pulse_Block parameter
        self.init_length_s = 0.0
        self.increment_s = 0.0
        self.channel_set = set()

        for elem in self.element_list:
            self.init_length_s += elem.init_length_s
            self.increment_s += elem.increment_s

            if not self.channel_set:
                self.channel_set = elem.channel_set
            elif self.channel_set != elem.channel_set:
                raise ValueError('Usage of different sets of analog and digital channels in the '
                                 'same PulseBlock is prohibited.\nPulseBlock creation failed!\n'
                                 'Used channel sets are:\n{0}\n{1}'.format(self.channel_set,
                                                                           elem.channel_set))
                break
        self.analog_channels = {chnl for chnl in self.channel_set if chnl.startswith('a')}
        self.digital_channels = {chnl for chnl in self.channel_set if chnl.startswith('d')}
        return

    def replace_element(self, position, element):
        if isinstance(element, PulseBlockElement) and len(self.element_list) > position:
            self.element_list[position] = element
            self.refresh_parameters()
            return 0
        else:
            return -1

    def delete_element(self, position):
        if len(self.element_list) > position:
            del(self.element_list[position])
            self.refresh_parameters()
            return 0
        else:
            return -1

    def append_element(self, element, at_beginning=False):
        if isinstance(element, PulseBlockElement):
            if at_beginning:
                self.element_list.insert(0, element)
            else:
                self.element_list.append(element)
            self.refresh_parameters()
            return 0
        else:
            return -1

    def get_dict_representation(self):
        dict_repr = dict()
        dict_repr['name'] = self.name
        dict_repr['element_list'] = list()
        for element in self.element_list:
            dict_repr['element_list'].append(element.get_dict_representation())
        return dict_repr

    @staticmethod
    def block_from_dict(block_dict):
        for ii, element_dict in enumerate(block_dict['element_list']):
            block_dict['element_list'][ii] = PulseBlockElement.element_from_dict(element_dict)
        return PulseBlock(**block_dict)


class PulseBlockEnsemble(object):
    """
    Represents a collection of PulseBlock objects which is called a PulseBlockEnsemble.

    This object is used as a construction plan to create one sampled file.
    """
    def __init__(self, name, block_list=None, rotating_frame=True):
        """
        The constructor for a Pulse_Block_Ensemble needs to have:

        @param str name: chosen name for the PulseBlockEnsemble
        @param list block_list: contains the PulseBlock names with their number of repetitions,
                                e.g. [(name, repetitions), (name, repetitions), ...])
        @param bool rotating_frame: indicates whether the phase should be preserved for all the
                                    functions.
        """
        # FIXME: Sanity checking needed here
        self.name = name
        self.rotating_frame = rotating_frame
        if isinstance(block_list, list):
            self.block_list = block_list
        else:
            self.block_list = list()

        # Dictionary container to store information related to the actually sampled
        # Waveform like pulser settings used during sampling (sample_rate, activation_config etc.)
        # and additional information about the discretization of the waveform (timebin positions of
        # the PulseBlockElement transitions etc.) as well as the names of the created waveforms.
        # This container will be populated during sampling and will be emptied upon deletion of the
        # corresponding waveforms from the pulse generator
        self.sampling_information = dict()
        # Dictionary container to store additional information about for measurement settings
        # (ignore_lasers, controlled_variable, alternating etc.).
        # This container needs to be populated by the script creating the PulseBlockEnsemble
        # before saving it. (e.g. in generate methods in PulsedObjectGenerator class)
        self.measurement_information = dict()
        return

    def replace_block(self, position, block_name, reps=0):
        if isinstance(block_name, str) and len(self.block_list) > position and reps >= 0:
            self.block_list[position] = (block_name, reps)
            return 0
        else:
            return -1

    def delete_block(self, position):
        if len(self.block_list) > position:
            del self.block_list[position]
            return 0
        else:
            return -1

    def append_block(self, block_name, reps=0, at_beginning=False):
        if isinstance(block_name, str) and reps >= 0:
            if at_beginning:
                self.block_list.insert(0, (block_name, reps))
            else:
                self.block_list.append((block_name, reps))
            return 0
        else:
            return -1

    def get_dict_representation(self):
        dict_repr = dict()
        dict_repr['name'] = self.name
        dict_repr['rotating_frame'] = self.rotating_frame
        dict_repr['block_list'] = self.block_list
        dict_repr['sampling_information'] = self.sampling_information
        dict_repr['measurement_information'] = self.measurement_information
        return dict_repr

    @staticmethod
    def ensemble_from_dict(ensemble_dict):
        new_ens = PulseBlockEnsemble(name=ensemble_dict['name'],
                                     block_list=ensemble_dict['block_list'],
                                     rotating_frame=ensemble_dict['rotating_frame'])
        new_ens.sampling_information = ensemble_dict['sampling_information']
        new_ens.measurement_information = ensemble_dict['measurement_information']
        return new_ens


class PulseSequence(object):
    """
    Higher order object for sequence capability.

    Represents a playback procedure for a number of PulseBlockEnsembles. Unused for pulse
    generator hardware without sequencing functionality.
    """
    def __init__(self, name, ensemble_list=None, rotating_frame=False):
        """
        The constructor for a PulseSequence objects needs to have:

        @param str name: the actual name of the sequence
        @param list ensemble_list: list containing a tuple of two entries:
                                          [(PulseBlockEnsemble name, seq_param),
                                           (PulseBlockEnsemble name, seq_param), ...]
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
                                            seq_param = {'repetitions': 41}
                                          and so the respective sequence step will play 42 times.
        @param bool rotating_frame: indicates, whether the phase has to be preserved in all
                                    analog signals ACROSS different waveforms
        """
        self.name = name
        self.rotating_frame = rotating_frame
        if ensemble_list is None:
            self.ensemble_list = list()
        else:
            self.ensemble_list = ensemble_list

        # self.sampled_ensembles = OrderedDict()
        # Dictionary container to store information related to the actually sampled
        # Waveforms like pulser settings used during sampling (sample_rate, activation_config etc.)
        # and additional information about the discretization of the waveform (timebin positions of
        # the PulseBlockElement transitions etc.)
        # This container is not necessary for the sampling process but serves only the purpose of
        # holding optional information for different modules.
        self.sampling_information = dict()
        # Dictionary container to store additional information about for measurement settings
        # (ignore_lasers, controlled_values, alternating etc.).
        # This container needs to be populated by the script creating the PulseSequence
        # before saving it.
        self.measurement_information = dict()
        return

    def replace_ensemble(self, position, ensemble_name, seq_param=None):
        """ Replace a sequence step at a given position.

        @param int position: position in the ensemble list
        @param str ensemble_name: PulseBlockEnsemble name
        @param dict seq_param: Sequence step parameter dictionary. Use present one if None.
        """
        if isinstance(ensemble_name, str) and len(self.ensemble_list) > position:
            if seq_param is None:
                self.ensemble_list[position][0] = ensemble_name
            else:
                self.ensemble_list[position] = (ensemble_name, seq_param)
            return 0
        else:
            return -1

    def delete_ensemble(self, position):
        """ Delete an ensemble at a given position

        @param int position: position within the list self.ensemble_list.
        """
        if len(self.ensemble_list) > position:
            del self.ensemble_list[position]
            return 0
        else:
            return -1

    def append_ensemble(self, ensemble_name, seq_param, at_beginning=False):
        """ Append either at the front or at the back an ensemble_param

        @param str ensemble_name: PulseBlockEnsemble name
        @param dict seq_param: Sequence step parameter dictionary.
        @param bool at_beginning: If flase append to end (default), if true then
                                  inset at beginning.
        """
        if isinstance(ensemble_name, str):
            if at_beginning:
                self.ensemble_list.insert((ensemble_name, seq_param))
            else:
                self.ensemble_list.append((ensemble_name, seq_param))
            return 0
        else:
            return -1

    def get_dict_representation(self):
        dict_repr = dict()
        dict_repr['name'] = self.name
        dict_repr['rotating_frame'] = self.rotating_frame
        dict_repr['ensemble_list'] = self.ensemble_list
        dict_repr['sampling_information'] = self.sampling_information
        dict_repr['measurement_information'] = self.measurement_information
        return dict_repr

    @staticmethod
    def sequence_from_dict(sequence_dict):
        new_seq = PulseSequence(name=sequence_dict['name'],
                                ensemble_list=sequence_dict['ensemble_list'],
                                rotating_frame=sequence_dict['rotating_frame'])
        new_seq.sampling_information = sequence_dict['sampling_information']
        new_seq.measurement_information = sequence_dict['measurement_information']
        return new_seq
