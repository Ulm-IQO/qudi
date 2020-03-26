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

import copy
import os
import sys
import inspect
import importlib
import numpy as np
from collections import OrderedDict

from logic.pulsed.sampling_functions import SamplingFunctions
from core.util.modules import get_main_dir
from core.util.helpers import natural_sort


class PulseBlockElement(object):
    """
    Object representing a single atomic element in a pulse block.

    This class can build waiting times, sine waves, etc. The pulse block may
    contain many Pulse_Block_Element Objects. These objects can be displayed in
    a GUI as single rows of a Pulse_Block.
    """

    def __init__(self, init_length_s=10e-9, increment_s=0, pulse_function=None, digital_high=None, laser_on=False):
        """
        The constructor for a Pulse_Block_Element needs to have:

        @param float init_length_s: an initial length of the element, this parameters should not be
                                    zero but must have a finite value.
        @param float increment_s: the number which will be incremented during each repetition of
                                  this element.
        @param dict pulse_function: dictionary with keys being the qudi analog channel string
                                    descriptors ('a_ch1', 'a_ch2' etc.) and the corresponding
                                    objects being instances of the mathematical function objects
                                    provided by SamplingFunctions class.
        @param dict digital_high: dictionary with keys being the qudi digital channel string
                                  descriptors ('d_ch1', 'd_ch2' etc.) and the corresponding objects
                                  being boolean values describing if the channel should be logical
                                  low (False) or high (True).
                                  For 3 digital channel it may look like:
                                  {'d_ch1': True, 'd_ch2': False, 'd_ch5': False}
        @param bool laser_on: boolean indicating if the laser is on during this block.
                              This is required for laser channels, that are not digital channels.
        """
        # FIXME: Sanity checks need to be implemented here
        self.init_length_s = init_length_s
        self.increment_s = increment_s
        self.laser_on = laser_on
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

    def __repr__(self):
        repr_str = 'PulseBlockElement(init_length_s={0}, increment_s={1}, laser_on={2}, pulse_function='.format(
            self.init_length_s, self.increment_s, self.laser_on)
        repr_str += '{'
        for ind, (channel, sampling_func) in enumerate(self.pulse_function.items()):
            repr_str += '\'{0}\': {1}'.format(channel, 'SamplingFunctions.' + repr(sampling_func))
            if ind < len(self.pulse_function) - 1:
                repr_str += ', '
        repr_str += '}, '
        repr_str += 'digital_high={0})'.format(repr(dict(self.digital_high)))
        return repr_str

    def __str__(self):
        pulse_func_dict = {chnl: type(func).__name__ for chnl, func in self.pulse_function.items()}
        return_str = 'PulseBlockElement\n\tinitial length: {0}s\n\tlength increment: {1}s\n\tlaser_on : {2],' \
                     'analog channels: {3}\n\tdigital channels: {4}'.format(self.init_length_s,
                                                                            self.increment_s,
                                                                            self.laser_on,
                                                                            pulse_func_dict,
                                                                            dict(self.digital_high))
        return return_str

    def __eq__(self, other):
        if not isinstance(other, PulseBlockElement):
            return False
        if self is other:
            return True
        if self.channel_set != other.channel_set:
            return False
        if (self.init_length_s, self.increment_s, self.laser_on) != (
                other.init_length_s, other.increment_s, other.laser_on):
            return False
        if set(self.digital_high.items()) != set(other.digital_high.items()):
            return False
        for chnl, func in self.pulse_function:
            if func != other.pulse_function[chnl]:
                return False
        return True

    def get_dict_representation(self):
        dict_repr = dict()
        dict_repr['init_length_s'] = self.init_length_s
        dict_repr['increment_s'] = self.increment_s
        dict_repr['laser_on'] = self.laser_on
        dict_repr['digital_high'] = self.digital_high
        dict_repr['pulse_function'] = dict()
        for chnl, func in self.pulse_function.items():
            dict_repr['pulse_function'][chnl] = func.get_dict_representation()
        return dict_repr

    @staticmethod
    def element_from_dict(element_dict):
        for chnl, sample_dict in element_dict['pulse_function'].items():
            sf_class = getattr(SamplingFunctions, sample_dict['name'])
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
        self.element_list = list() if element_list is None else element_list
        self.init_length_s = 0.0
        self.increment_s = 0.0
        self.analog_channels = set()
        self.digital_channels = set()
        self.channel_set = set()
        self.refresh_parameters()
        return

    def __repr__(self):
        repr_str = 'PulseBlock(name=\'{0}\', element_list=['.format(self.name)
        repr_str += ', '.join((repr(elem) for elem in self.element_list)) + '])'
        return repr_str

    def __str__(self):
        return_str = 'PulseBlock "{0}"\n\tnumber of elements: {1}\n\t'.format(
            self.name, len(self.element_list))
        return_str += 'initial length: {0}s\n\tlength increment: {1}s\n\t'.format(
            self.init_length_s, self.increment_s)
        return_str += 'active analog channels: {0}\n\tactive digital channels: {1}'.format(
            natural_sort(self.analog_channels), natural_sort(self.digital_channels))
        return return_str

    def __len__(self):
        return len(self.element_list)

    def __getitem__(self, key):
        if not isinstance(key, (slice, int)):
            raise TypeError('PulseBlock indices must be int or slice, not {0}'.format(type(key)))
        return self.element_list[key]

    def __setitem__(self, key, value):
        if isinstance(key, int):
            if not isinstance(value, PulseBlockElement):
                raise TypeError('PulseBlock element list entries must be of type PulseBlockElement,'
                                ' not {0}'.format(type(value)))
            if not self.channel_set:
                self.channel_set = value.channel_set.copy()
                self.analog_channels = {chnl for chnl in self.channel_set if chnl.startswith('a')}
                self.digital_channels = {chnl for chnl in self.channel_set if chnl.startswith('d')}
            elif value.channel_set != self.channel_set:
                raise ValueError('Usage of different sets of analog and digital channels in the '
                                 'same PulseBlock is prohibited. Used channel sets are:\n{0}\n{1}'
                                 ''.format(self.channel_set, value.channel_set))

            self.init_length_s -= self.element_list[key].init_length_s
            self.increment_s -= self.element_list[key].increment_s
            self.init_length_s += value.init_length_s
            self.increment_s += value.increment_s
        elif isinstance(key, slice):
            add_length = 0
            add_increment = 0
            for element in value:
                if not isinstance(element, PulseBlockElement):
                    raise TypeError('PulseBlock element list entries must be of type '
                                    'PulseBlockElement, not {0}'.format(type(value)))
                if not self.channel_set:
                    self.channel_set = element.channel_set.copy()
                    self.analog_channels = {chnl for chnl in self.channel_set if
                                            chnl.startswith('a')}
                    self.digital_channels = {chnl for chnl in self.channel_set if
                                             chnl.startswith('d')}
                elif element.channel_set != self.channel_set:
                    raise ValueError(
                        'Usage of different sets of analog and digital channels in the '
                        'same PulseBlock is prohibited. Used channel sets are:\n{0}\n{1}'
                        ''.format(self.channel_set, element.channel_set))

                add_length += element.init_length_s
                add_increment += element.increment_s

            for element in self.element_list[key]:
                self.init_length_s -= element.init_length_s
                self.increment_s -= element.increment_s

            self.init_length_s += add_length
            self.increment_s += add_increment
        else:
            raise TypeError('PulseBlock indices must be int or slice, not {0}'.format(type(key)))
        self.element_list[key] = copy.deepcopy(value)
        return

    def __delitem__(self, key):
        if not isinstance(key, (slice, int)):
            raise TypeError('PulseBlock indices must be int or slice, not {0}'.format(type(key)))

        if isinstance(key, int):
            items_to_delete = [self.element_list[key]]
        else:
            items_to_delete = self.element_list[key]

        for element in items_to_delete:
            self.init_length_s -= element.init_length_s
            self.increment_s -= element.increment_s
        del self.element_list[key]
        if len(self.element_list) == 0:
            self.init_length_s = 0.0
            self.increment_s = 0.0
        return

    def __eq__(self, other):
        if not isinstance(other, PulseBlock):
            return False
        if self is other:
            return True
        if self.channel_set != other.channel_set:
            return False
        if (self.init_length_s, self.increment_s) != (other.init_length_s, other.increment_s):
            return False
        if len(self) != len(other):
            return False
        for i, element in enumerate(self.element_list):
            if element != other[i]:
                return False
        return True

    def refresh_parameters(self):
        """ Initialize the parameters which describe this Pulse_Block object.

        The information is gained from all the Pulse_Block_Element objects,
        which are attached in the element_list.
        """
        # the Pulse_Block parameters
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
        self.analog_channels = {chnl for chnl in self.channel_set if chnl.startswith('a')}
        self.digital_channels = {chnl for chnl in self.channel_set if chnl.startswith('d')}
        return

    def pop(self, position=None):
        if len(self.element_list) == 0:
            raise IndexError('pop from empty PulseBlock')

        if position is None:
            self.init_length_s -= self.element_list[-1].init_length_s
            self.increment_s -= self.element_list[-1].increment_s
            return self.element_list.pop()

        if not isinstance(position, int):
            raise TypeError('PulseBlock.pop position argument expects integer, not {0}'
                            ''.format(type(position)))

        if position < 0:
            position = len(self.element_list) + position

        if len(self.element_list) <= position or position < 0:
            raise IndexError('PulseBlock element list index out of range')

        self.init_length_s -= self.element_list[position].init_length_s
        self.increment_s -= self.element_list[position].increment_s
        return self.element_list.pop(position)

    def insert(self, position, element):
        """ Insert a PulseBlockElement at the given position. The old element at this position and
        all consecutive elements after that will be shifted to higher indices.

        @param int position: position in the element list
        @param PulseBlockElement element: PulseBlockElement instance
        """
        if not isinstance(element, PulseBlockElement):
            raise ValueError('PulseBlock elements must be of type PulseBlockElement, not {0}'
                             ''.format(type(element)))

        if position < 0:
            position = len(self.element_list) + position

        if len(self.element_list) < position or position < 0:
            raise IndexError('PulseBlock element list index out of range')

        if not self.channel_set:
            self.channel_set = element.channel_set.copy()
            self.analog_channels = {chnl for chnl in self.channel_set if chnl.startswith('a')}
            self.digital_channels = {chnl for chnl in self.channel_set if chnl.startswith('d')}
        elif element.channel_set != self.channel_set:
            raise ValueError('Usage of different sets of analog and digital channels in the '
                             'same PulseBlock is prohibited. Used channel sets are:\n{0}\n{1}'
                             ''.format(self.channel_set, element.channel_set))

        self.init_length_s += element.init_length_s
        self.increment_s += element.increment_s

        self.element_list.insert(position, copy.deepcopy(element))
        return

    def append(self, element):
        """
        """
        self.insert(position=len(self.element_list), element=element)
        return

    def extend(self, iterable):
        for element in iterable:
            self.append(element=element)
        return

    def clear(self):
        del self.element_list[:]
        self.init_length_s = 0.0
        self.increment_s = 0.0
        self.analog_channels = set()
        self.digital_channels = set()
        self.channel_set = set()
        return

    def reverse(self):
        self.element_list.reverse()
        return

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

    def __repr__(self):
        repr_str = 'PulseBlockEnsemble(name=\'{0}\', block_list={1}, rotating_frame={2})'.format(
            self.name, repr(self.block_list), self.rotating_frame)
        return repr_str

    def __str__(self):
        return_str = 'PulseBlockEnsemble "{0}"\n\trotating frame: {1}\n\t' \
                     'has been sampled: {2}\n\t<block name>\t<repetitions>\n\t'.format(
            self.name, self.rotating_frame, bool(self.sampling_information))
        return_str += '\n\t'.join(('{0}\t{1}'.format(name, reps) for name, reps in self.block_list))
        return return_str

    def __eq__(self, other):
        if not isinstance(other, PulseBlockEnsemble):
            return False
        if self is other:
            return True
        if (self.name, self.rotating_frame) != (other.name, other.rotating_frame):
            return False
        if self.block_list != other.block_list:
            return False
        if self.measurement_information != other.measurement_information:
            return False
        return True

    def __len__(self):
        return len(self.block_list)

    def __getitem__(self, key):
        if not isinstance(key, (slice, int)):
            raise TypeError('PulseBlockEnsemble indices must be int or slice, not {0}'
                            ''.format(type(key)))
        return self.block_list[key]

    def __setitem__(self, key, value):
        if isinstance(key, int):
            if not isinstance(value, (tuple, list)) or len(value) != 2:
                raise TypeError('PulseBlockEnsemble block list entries must be a tuple or list of '
                                'length 2')
            elif not isinstance(value[0], str):
                raise ValueError('PulseBlockEnsemble element tuple index 0 must contain str, '
                                 'not {0}'.format(type(value[0])))
            elif not isinstance(value[1], int) or value[1] < 0:
                raise ValueError('PulseBlockEnsemble element tuple index 1 must contain int >= 0')
        elif isinstance(key, slice):
            for element in value:
                if not isinstance(element, (tuple, list)) or len(value) != 2:
                    raise TypeError('PulseBlockEnsemble block list entries must be a tuple or list '
                                    'of length 2')
                elif not isinstance(element[0], str):
                    raise ValueError('PulseBlockEnsemble element tuple index 0 must contain str, '
                                     'not {0}'.format(type(element[0])))
                elif not isinstance(element[1], int) or element[1] < 0:
                    raise ValueError('PulseBlockEnsemble element tuple index 1 must contain int >= '
                                     '0')
        else:
            raise TypeError('PulseBlockEnsemble indices must be int or slice, not {0}'
                            ''.format(type(key)))
        self.block_list[key] = tuple(value)
        self.sampling_information = dict()
        self.measurement_information = dict()
        return

    def __delitem__(self, key):
        if not isinstance(key, (slice, int)):
            raise TypeError('PulseBlockEnsemble indices must be int or slice, not {0}'
                            ''.format(type(key)))

        del self.block_list[key]
        self.sampling_information = dict()
        self.measurement_information = dict()
        return

    def pop(self, position=None):
        if len(self.block_list) == 0:
            raise IndexError('pop from empty PulseBlockEnsemble')

        if position is None:
            self.sampling_information = dict()
            self.measurement_information = dict()
            return self.block_list.pop()

        if not isinstance(position, int):
            raise TypeError('PulseBlockEnsemble.pop position argument expects integer, not {0}'
                            ''.format(type(position)))

        if position < 0:
            position = len(self.block_list) + position

        if len(self.block_list) <= position or position < 0:
            raise IndexError('PulseBlockEnsemble block list index out of range')

        self.sampling_information = dict()
        self.measurement_information = dict()
        return self.block_list.pop(position)

    def insert(self, position, element):
        """ Insert a (PulseBlock.name, repetitions) tuple at the given position. The old element
        at this position and all consecutive elements after that will be shifted to higher indices.

        @param int position: position in the element list
        @param tuple element: (PulseBlock name (str), repetitions (int))
        """
        if not isinstance(element, (tuple, list)) or len(element) != 2:
            raise TypeError('PulseBlockEnsemble block list entries must be a tuple or list of '
                            'length 2')
        elif not isinstance(element[0], str):
            raise ValueError('PulseBlockEnsemble element tuple index 0 must contain str, '
                             'not {0}'.format(type(element[0])))
        elif not isinstance(element[1], int) or element[1] < 0:
            raise ValueError('PulseBlockEnsemble element tuple index 1 must contain int >= 0')

        if position < 0:
            position = len(self.block_list) + position
        if len(self.block_list) < position or position < 0:
            raise IndexError('PulseBlockEnsemble block list index out of range')

        self.block_list.insert(position, tuple(element))
        self.sampling_information = dict()
        self.measurement_information = dict()
        return

    def append(self, element):
        """
        """
        self.insert(position=len(self), element=element)
        return

    def extend(self, iterable):
        for element in iterable:
            self.append(element=element)
        return

    def clear(self):
        del self.block_list[:]
        self.sampling_information = dict()
        self.measurement_information = dict()
        return

    def reverse(self):
        self.block_list.reverse()
        self.sampling_information = dict()
        self.measurement_information = dict()
        return

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


class SequenceStep(dict):
    """
    This is basically a dictionary where each key can be accessed like an attribute.
    In addition it needs a mandatory key "ensemble" whose value must be a str containing the
    PulseBlockEnsemble name associated with this sequence step.
    You can initialize this the same way as a dict or pass the ensemble name as positional argument:
        mystep = SequenceStep(ensemble='myPulseBlockEnsembleName', repetitions=10, go_to=-1)
        mystep = SequenceStep(
            [('ensemble', 'myPulseBlockEnsembleName'), ('repetitions', 10), ('go_to', -1)])
        mystep = SequenceStep(
            {'ensemble': 'myPulseBlockEnsembleName', 'repetitions': 10, 'go_to': -1})
        mystep = SequenceStep('myPulseBlockEnsembleName', repetitions=10, go_to=-1)
        mystep = SequenceStep('myPulseBlockEnsembleName', {'repetitions': 10, 'go_to': -1})
    You have all the built-in dict methods, e.g. keys(), items() etc...
    You can access the keys/values in a dict-like way or like an attribute:
        mystep['repetitions'] = 0
        mystep.repetitions = 0
    """

    __default_parameters = {'repetitions': 0,
                            'go_to': -1,
                            'event_jump_to': -1,
                            'event_trigger': 'OFF',
                            'wait_for': 'OFF',
                            'flag_trigger': list(),
                            'flag_high': list()}

    def __init__(self, *args, **kwargs):
        if len(args) > 2:
            raise TypeError('SequenceStep expected at most 2 arguments, got {0}'.format(len(args)))
        # Allow the PulseBlockEnsemble name to be passed as positional argument
        for i, pos_arg in enumerate(args):
            if isinstance(pos_arg, str):
                kwargs['ensemble'] = pos_arg
                if len(args) == 2:
                    args = (args[0],) if i == 1 else (args[1],)
                else:
                    args = tuple()
                break

        # Initialize the dict.
        super().__init__(*args, **kwargs)
        # Check for allowed keys in order to avoid overwriting built-in dict methods and the
        # ensemble name.
        # Also check presence of a valid mandatory "ensemble" entry
        if not isinstance(self.get('ensemble'), str):
            raise KeyError('"ensemble" entry of type str must be present in SequenceStep. Either '
                           'include it as dict item or pass it as positional argument in the '
                           'constructor.')
        for attribute in dir(dict):
            if attribute in self:
                raise KeyError('It is not allowed to overwrite built-in dict attributes. '
                               'Please use another key than "{0}".'.format(attribute))

        # Merge namespaces (this is where the magic happens)
        self.__dict__ = self

        # Add missing default parameters
        for key, default_value in self.__default_parameters.items():
            if key not in self:
                self[key] = default_value

        if not isinstance(self.flag_trigger, list):
            raise KeyError('"flag_trigger" is only allowed to be a list.')
        if not isinstance(self.flag_high, list):
            raise KeyError('"flag_high" is only allowed to be a list.')
        return

    def __setitem__(self, key, value):
        """
        Overwrite this method in order to avoid namespace collision with the native dict
        members/attributes.
        """
        if key in dir(dict):
            raise KeyError('It is not allowed to overwrite built-in dict attributes. '
                           'Please use another key than "{0}".'.format(key))
        super().__setitem__(key, value)
        return

    def copy(self):
        return SequenceStep(super().copy())


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
                                                     having played all repetitions. (Default -1)
                                                     Indices starting at 1 for first step.
                                                     Set to 0 or -1 to follow up with the next step.
                                          'event_jump_to': The sequence step to jump to
                                                           (starting from 1) in case of a trigger
                                                           event (see event_trigger).
                                                           Setting it to 0 or -1 means jump to next
                                                           step. Ignored if event_trigger is 'OFF'.
                                          'event_trigger': The trigger input to listen to in order
                                                           to perform sequence jumps. Set to 'OFF'
                                                           (default) in order to ignore triggering.
                                          'wait_for': The trigger input to wait for before playing
                                                      this sequence step. Set to 'OFF' (default)
                                                      in order to play the current step immediately.
                                          'flag_trigger': List containing the flags (str) to
                                                          trigger when this sequence step starts
                                                          playing. Empty list (default) for no flag
                                                          trigger.
                                          'flag_high': List containing the flags (str) to set to
                                                       high when this sequence step is playing. All
                                                       others will be low (or triggered; see above).
                                                       Empty list (default) for all flags low.

                                          If only 'repetitions' are in the dictionary, then the dict
                                          will look like:
                                            seq_param = {'repetitions': 41}
                                          and so the respective sequence step will play 42 times.
        @param bool rotating_frame: indicates, whether the phase has to be preserved in all
                                    analog signals ACROSS different waveforms
        """
        self.name = name
        self.rotating_frame = rotating_frame
        self.ensemble_list = list()
        if ensemble_list is not None:
            self.extend(ensemble_list)
        self.is_finite = True
        self.refresh_parameters()

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

    def refresh_parameters(self):
        self.is_finite = True
        for sequence_step in self.ensemble_list:
            if sequence_step.repetitions < 0:
                self.is_finite = False
                break
        return

    def __repr__(self):
        repr_str = 'PulseSequence(name=\'{0}\', ensemble_list={1}, rotating_frame={2})'.format(
            self.name, self.ensemble_list, self.rotating_frame)
        return repr_str

    def __str__(self):
        return_str = 'PulseSequence "{0}"\n\trotating frame: {1}\n\t' \
                     'has finite length: {2}\n\thas been sampled: {3}\n\t<ensemble name>\t' \
                     '<sequence parameters>\n\t'.format(self.name,
                                                        self.rotating_frame,
                                                        self.is_finite,
                                                        bool(self.sampling_information))
        return_str += '\n\t'.join(('{0}\t{1}'.format(name, param) for name, param in self))
        return return_str

    def __eq__(self, other):
        if not isinstance(other, PulseSequence):
            return False
        if self is other:
            return True
        if (self.name, self.rotating_frame, self.is_finite) != (other.name, other.rotating_frame, other.is_finite):
            return False
        if self.ensemble_list != other.ensemble_list:
            return False
        if self.measurement_information != other.measurement_information:
            return False
        return True

    def __len__(self):
        return len(self.ensemble_list)

    def __getitem__(self, key):
        if not isinstance(key, (slice, int)):
            raise TypeError('PulseSequence indices must be int or slice, not {0}'.format(type(key)))
        return self.ensemble_list[key]

    def __setitem__(self, key, value):
        stage_refresh = False
        if isinstance(key, int):
            if isinstance(value, (str, dict)):
                value = SequenceStep(value)
            elif isinstance(value, (tuple, list)) and len(value) == 2:
                value = SequenceStep(*value)

            if not isinstance(value, SequenceStep):
                raise TypeError('PulseSequence ensemble list entries must be either:\n'
                                '\t- a tuple or list of length 2 with one entry being the '
                                'PulseBlockEnsemble name and the other being a sequence parameter '
                                'dictionary\n'
                                '\t- a str containing the PulseBlockEnsemble name\n'
                                '\t- a dict containing the sequence parameters including the '
                                'PulseBlockEnsemble name')

            if value.repetitions < 0:
                self.is_finite = False
            elif not self.is_finite and self[key].repetitions < 0:
                stage_refresh = True
        elif isinstance(key, slice):
            if isinstance(value[0], (str, dict)):
                tmp_value = list()
                for element in value:
                    tmp_value.append(SequenceStep(element))
                value = tmp_value
            elif isinstance(value[0], (tuple, list)) and len(value[0]) == 2:
                tmp_value = list()
                for element in value:
                    tmp_value.append(SequenceStep(*element))
                value = tmp_value
            for element in value:
                if not isinstance(element, SequenceStep):
                    raise TypeError('PulseSequence ensemble list entries must be either:\n'
                                    '\t- a tuple or list of length 2 with one entry being the '
                                    'PulseBlockEnsemble name and the other being a sequence parameter '
                                    'dictionary\n'
                                    '\t- a str containing the PulseBlockEnsemble name\n'
                                    '\t- a dict containing the sequence parameters including the '
                                    'PulseBlockEnsemble name')

                if element.repetitions < 0:
                    self.is_finite = False
                elif not self.is_finite:
                    stage_refresh = True
        else:
            raise TypeError('PulseSequence indices must be int or slice, not {0}'.format(type(key)))
        self.ensemble_list[key] = value
        self.sampling_information = dict()
        self.measurement_information = dict()
        if stage_refresh:
            self.refresh_parameters()
        return

    def __delitem__(self, key):
        if isinstance(key, slice):
            stage_refresh = False
            for element in self.ensemble_list[key]:
                if element.repetitions < 0:
                    stage_refresh = True
                    break
        elif isinstance(key, int):
            stage_refresh = self.ensemble_list[key].repetitions < 0
        else:
            raise TypeError('PulseSequence indices must be int or slice, not {0}'.format(type(key)))
        del self.ensemble_list[key]
        self.sampling_information = dict()
        self.measurement_information = dict()
        if stage_refresh:
            self.refresh_parameters()
        return

    def pop(self, position=None):
        stage_refresh = False
        if len(self.ensemble_list) == 0:
            raise IndexError('pop from empty PulseSequence')

        if position is None:
            position = len(self.ensemble_list) - 1

        if not isinstance(position, int):
            raise TypeError('PulseSequence.pop position argument expects integer, not {0}'
                            ''.format(type(position)))

        if position < 0:
            position = len(self.ensemble_list) + position

        if len(self.ensemble_list) <= position or position < 0:
            raise IndexError('PulseSequence ensemble list index out of range')

        self.sampling_information = dict()
        self.measurement_information = dict()
        if self.ensemble_list[position].repetitions < 0:
            stage_refresh = True
        popped_element = self.ensemble_list.pop(position)
        if stage_refresh:
            self.refresh_parameters()
        return popped_element

    def insert(self, position, element):
        """
        Insert a SequenceStep instance at the given position. The old element
        at this position and all consecutive elements after that will be shifted to higher indices.

        @param int position: position in the ensemble list
        @param tuple|list|str|dict|SequenceStep element:
            PulseBlockEnsemble name (str) |
            (PulseBlockEnsemble name, sequence parameters dict) (tuple|list) |
            sequence parameters dict including PulseBlockEnsemble name (dict) |
            SequenceStep instance (SequenceStep)
        """
        if isinstance(element, (str, dict)):
            element = SequenceStep(element)
        elif isinstance(element, (tuple, list)) and len(element) == 2:
            element = SequenceStep(*element)

        if not isinstance(element, SequenceStep):
            raise TypeError('PulseSequence ensemble list entries must be either:\n'
                            '\t- a tuple or list of length 2 with one entry being the '
                            'PulseBlockEnsemble name and the other being a sequence parameter '
                            'dictionary\n'
                            '\t- a str containing the PulseBlockEnsemble name\n'
                            '\t- a dict containing the sequence parameters including the '
                            'PulseBlockEnsemble name')

        if position < 0:
            position = len(self.ensemble_list) + position
        if len(self.ensemble_list) < position or position < 0:
            raise IndexError('PulseSequence ensemble list index out of range')

        self.ensemble_list.insert(position, element)
        if element.repetitions < 0:
            self.is_finite = False
        self.sampling_information = dict()
        self.measurement_information = dict()
        return

    def append(self, element):
        """
        """
        self.insert(position=len(self.ensemble_list), element=element)
        return

    def extend(self, iterable):
        for element in iterable:
            self.append(element=element)
        return

    def clear(self):
        del self.ensemble_list[:]
        self.sampling_information = dict()
        self.measurement_information = dict()
        self.is_finite = True
        return

    def reverse(self):
        self.ensemble_list.reverse()
        self.sampling_information = dict()
        self.measurement_information = dict()
        return

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


class PredefinedGeneratorBase:
    """
    Base class for PulseObjectGenerator and predefined generator classes containing the actual
    "generate_"-methods.

    This class holds a protected reference to the SequenceGeneratorLogic and provides read-only
    access via properties to various attributes of the logic module.
    SequenceGeneratorLogic logger is also accessible via this base class and can be used as in any
    qudi module (e.g. self.log.error(...)).
    Also provides helper methods to simplify sequence/ensemble generation.
    """

    def __init__(self, sequencegeneratorlogic):
        # Keep protected reference to the SequenceGeneratorLogic
        self.__sequencegeneratorlogic = sequencegeneratorlogic

    @property
    def log(self):
        return self.__sequencegeneratorlogic.log

    @property
    def analyze_block_ensemble(self):
        return self.__sequencegeneratorlogic.analyze_block_ensemble

    @property
    def analyze_sequence(self):
        return self.__sequencegeneratorlogic.analyze_sequence

    @property
    def pulse_generator_settings(self):
        return self.__sequencegeneratorlogic.pulse_generator_settings

    @property
    def save_block(self):
        return self.__sequencegeneratorlogic.save_block

    @property
    def save_ensemble(self):
        return self.__sequencegeneratorlogic.save_ensemble

    @property
    def save_sequence(self):
        return self.__sequencegeneratorlogic.save_sequence

    @property
    def generation_parameters(self):
        return self.__sequencegeneratorlogic.generation_parameters

    @property
    def pulse_generator_constraints(self):
        return self.__sequencegeneratorlogic.pulse_generator_constraints

    @property
    def channel_set(self):
        channels = self.pulse_generator_settings.get('activation_config')
        if channels is None:
            channels = ('', set())
        return channels[1]

    @property
    def analog_channels(self):
        return {chnl for chnl in self.channel_set if chnl.startswith('a')}

    @property
    def digital_channels(self):
        return {chnl for chnl in self.channel_set if chnl.startswith('d')}

    @property
    def laser_channel(self):
        return self.generation_parameters.get('laser_channel')

    @property
    def sync_channel(self):
        channel = self.generation_parameters.get('sync_channel')
        return None if channel == '' else channel

    @property
    def gate_channel(self):
        channel = self.generation_parameters.get('gate_channel')
        return None if channel == '' else channel

    @property
    def analog_trigger_voltage(self):
        return self.generation_parameters.get('analog_trigger_voltage')

    @property
    def laser_delay(self):
        return self.generation_parameters.get('laser_delay')

    @property
    def microwave_channel(self):
        channel = self.generation_parameters.get('microwave_channel')
        return None if channel == '' else channel

    @property
    def microwave_frequency(self):
        return self.generation_parameters.get('microwave_frequency')

    @property
    def microwave_amplitude(self):
        return self.generation_parameters.get('microwave_amplitude')

    @property
    def laser_length(self):
        return self.generation_parameters.get('laser_length')

    @property
    def wait_time(self):
        return self.generation_parameters.get('wait_time')

    @property
    def rabi_period(self):
        return self.generation_parameters.get('rabi_period')

    @property
    def sample_rate(self):
        return self.pulse_generator_settings.get('sample_rate')

    ################################################################################################
    #                                   Helper methods                                          ####
    ################################################################################################
    def _get_idle_element(self, length, increment):
        """
        Creates an idle pulse PulseBlockElement

        @param float length: idle duration in seconds
        @param float increment: idle duration increment in seconds

        @return: PulseBlockElement, the generated idle element
        """
        # Create idle element
        return PulseBlockElement(
            init_length_s=length,
            increment_s=increment,
            pulse_function={chnl: SamplingFunctions.Idle() for chnl in self.analog_channels},
            digital_high={chnl: False for chnl in self.digital_channels})

    def _get_trigger_element(self, length, increment, channels):
        """
        Creates a trigger PulseBlockElement

        @param float length: trigger duration in seconds
        @param float increment: trigger duration increment in seconds
        @param str|list channels: The pulser channel(s) to be triggered.

        @return: PulseBlockElement, the generated trigger element
        """
        if isinstance(channels, str):
            channels = [channels]

        # input params for element generation
        pulse_function = {chnl: SamplingFunctions.Idle() for chnl in self.analog_channels}
        digital_high = {chnl: False for chnl in self.digital_channels}

        # Determine analogue or digital trigger channel and set channels accordingly.
        for channel in channels:
            if channel.startswith('d'):
                digital_high[channel] = True
            elif channel.startswith('a'):
                pulse_function[channel] = SamplingFunctions.DC(voltage=self.analog_trigger_voltage)

        # return trigger element
        return PulseBlockElement(init_length_s=length,
                                 increment_s=increment,
                                 pulse_function=pulse_function,
                                 digital_high=digital_high)

    def _get_laser_element(self, length, increment):
        """
        Creates laser trigger PulseBlockElement

        @param float length: laser pulse duration in seconds
        @param float increment: laser pulse duration increment in seconds

        @return: PulseBlockElement, two elements for laser and gate trigger (delay element)
        """
        laser_element = self._get_trigger_element(length=length,
                                                  increment=increment,
                                                  channels=self.laser_channel)
        laser_element.laser_on = True
        return laser_element

    def _get_laser_gate_element(self, length, increment):
        """
        """
        laser_gate_element = self._get_laser_element(length=length,
                                                     increment=increment)
        if self.gate_channel:
            if self.gate_channel.startswith('d'):
                laser_gate_element.digital_high[self.gate_channel] = True
            elif self.gate_channel.startswith('a'):
                laser_gate_element.pulse_function[self.gate_channel] = SamplingFunctions.DC(
                    voltage=self.analog_trigger_voltage)
        return laser_gate_element

    def _get_delay_element(self):
        """
        Creates an idle element of length of the laser delay

        @return PulseBlockElement: The delay element
        """
        return self._get_idle_element(length=self.laser_delay,
                                      increment=0)

    def _get_delay_gate_element(self):
        """
        Creates a gate trigger of length of the laser delay.
        If no gate channel is specified will return a simple idle element.

        @return PulseBlockElement: The delay element
        """
        if self.gate_channel:
            return self._get_trigger_element(length=self.laser_delay,
                                             increment=0,
                                             channels=self.gate_channel)
        else:
            return self._get_delay_element()

    def _get_sync_element(self):
        """

        """
        return self._get_trigger_element(length=50e-9, increment=0, channels=self.sync_channel)

    def _get_mw_element(self, length, increment, amp=None, freq=None, phase=None):
        """
        Creates a MW pulse PulseBlockElement

        @param float length: MW pulse duration in seconds
        @param float increment: MW pulse duration increment in seconds
        @param float freq: MW frequency in case of analogue MW channel in Hz
        @param float amp: MW amplitude in case of analogue MW channel in V
        @param float phase: MW phase in case of analogue MW channel in deg

        @return: PulseBlockElement, the generated MW element
        """
        if self.microwave_channel.startswith('d'):
            mw_element = self._get_trigger_element(
                length=length,
                increment=increment,
                channels=self.microwave_channel)
        else:
            mw_element = self._get_idle_element(
                length=length,
                increment=increment)
            mw_element.pulse_function[self.microwave_channel] = SamplingFunctions.Sin(
                amplitude=amp,
                frequency=freq,
                phase=phase)
        return mw_element

    def _get_multiple_mw_element(self, length, increment, amps=None, freqs=None, phases=None):
        """
        Creates single, double or triple sine mw element.

        @param float length: MW pulse duration in seconds
        @param float increment: MW pulse duration increment in seconds
        @param amps: list containing the amplitudes
        @param freqs: list containing the frequencies
        @param phases: list containing the phases
        @return: PulseBlockElement, the generated MW element
        """
        if isinstance(amps, (int, float)):
            amps = [amps]
        if isinstance(freqs, (int, float)):
            freqs = [freqs]
        if isinstance(phases, (int, float)):
            phases = [phases]

        if self.microwave_channel.startswith('d'):
            mw_element = self._get_trigger_element(
                length=length,
                increment=increment,
                channels=self.microwave_channel)
        else:
            mw_element = self._get_idle_element(
                length=length,
                increment=increment)

            sine_number = min(len(amps), len(freqs), len(phases))

            if sine_number < 2:
                mw_element.pulse_function[self.microwave_channel] = SamplingFunctions.Sin(
                    amplitude=amps[0],
                    frequency=freqs[0],
                    phase=phases[0])
            elif sine_number == 2:
                mw_element.pulse_function[self.microwave_channel] = SamplingFunctions.DoubleSinSum(
                    amplitude_1=amps[0],
                    amplitude_2=amps[1],
                    frequency_1=freqs[0],
                    frequency_2=freqs[1],
                    phase_1=phases[0],
                    phase_2=phases[1])
            else:
                mw_element.pulse_function[self.microwave_channel] = SamplingFunctions.TripleSinSum(
                    amplitude_1=amps[0],
                    amplitude_2=amps[1],
                    amplitude_3=amps[2],
                    frequency_1=freqs[0],
                    frequency_2=freqs[1],
                    frequency_3=freqs[2],
                    phase_1=phases[0],
                    phase_2=phases[1],
                    phase_3=phases[2])
        return mw_element

    def _get_mw_laser_element(self, length, increment, amp=None, freq=None, phase=None):
        """

        @param length:
        @param increment:
        @param amp:
        @param freq:
        @param phase:
        @return:
        """
        mw_laser_element = self._get_mw_element(length=length,
                                                increment=increment,
                                                amp=amp,
                                                freq=freq,
                                                phase=phase)
        if self.laser_channel.startswith('d'):
            mw_laser_element.digital_high[self.laser_channel] = True
        elif self.laser_channel.startswith('a'):
            mw_laser_element.pulse_function[self.laser_channel] = SamplingFunctions.DC(
                voltage=self.analog_trigger_voltage)

        mw_laser_element.laser_on = True
        return mw_laser_element

    def _get_readout_element(self):

        waiting_element = self._get_idle_element(length=self.wait_time, increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length, increment=0)
        delay_element = self._get_delay_gate_element()
        return laser_element, delay_element, waiting_element

    def _add_trigger(self, created_blocks, block_ensemble):
        if self.sync_channel:
            sync_block = PulseBlock(name='sync_trigger')
            sync_block.append(self._get_sync_element())
            created_blocks.append(sync_block)
            block_ensemble.append((sync_block.name, 0))
        return created_blocks, block_ensemble

    def _add_metadata_to_settings(self, block_ensemble, created_blocks, alternating=False,
                                  laser_ignore_list=None, controlled_variable=None, units=('s', ''),
                                  labels=('Tau', 'Signal'), number_of_lasers=None, counting_length=None):

        block_ensemble.measurement_information['alternating'] = alternating
        block_ensemble.measurement_information[
            'laser_ignore_list'] = laser_ignore_list if laser_ignore_list is not None else list()
        block_ensemble.measurement_information[
            'controlled_variable'] = controlled_variable if controlled_variable is not None else [0, 1]
        block_ensemble.measurement_information['units'] = units
        block_ensemble.measurement_information['labels'] = labels
        if number_of_lasers is None:
            if alternating:
                block_ensemble.measurement_information['number_of_lasers'] = len(controlled_variable) * 2
            else:
                block_ensemble.measurement_information['number_of_lasers'] = len(controlled_variable)
        else:
            block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        if counting_length is None:
            block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
                ensemble=block_ensemble, created_blocks=created_blocks)
        else:
            block_ensemble.measurement_information['counting_length'] = counting_length

        return block_ensemble

    def _adjust_to_samplingrate(self, value, divisibility):
        """
        Every pulsing device has a sampling rate which is most of the time adjustable
        but always limited. Thus it is not possible to generate any arbitrary time value. This function
        should check if the timing value is generateable with the current sampling rate and if nout round
        it to the next possible value...

        @param value: the desired timing value
        @param divisibility: Takes into account that only parts of variables might be used
                             (for example for a pi/2 pulse...)
        @return: value matching to the current sampling rate of pulser
        """
        resolution = 1 / self.sample_rate * divisibility
        mod = value % resolution
        if mod < resolution / 2:
            self.log.debug('Adjusted to sampling rate:' + str(value) + ' to ' + str(value - mod))
            value = value - mod
        else:
            value = value + resolution - mod
        # correct for computational errors
        value = float(np.around(value, 13))
        return value

    def _get_ensemble_count_length(self, ensemble, created_blocks):
        """

        @param ensemble:
        @param created_blocks:
        @return:
        """
        if self.gate_channel:
            length = self.laser_length + self.laser_delay
        else:
            blocks = {block.name: block for block in created_blocks}
            length = 0.0
            for block_name, reps in ensemble.block_list:
                length += blocks[block_name].init_length_s * (reps + 1)
                length += blocks[block_name].increment_s * ((reps ** 2 + reps) / 2)
        return length


class PulseObjectGenerator(PredefinedGeneratorBase):
    """

    """

    def __init__(self, sequencegeneratorlogic):
        # Initialize base class
        super().__init__(sequencegeneratorlogic)

        # dictionary containing references to all generation methods imported from generator class
        # modules. The keys are the method names excluding the prefix "generate_".
        self._generate_methods = dict()
        # nested dictionary with keys being the generation method names and values being a
        # dictionary containing all keyword arguments as keys with their default value
        self._generate_method_parameters = dict()

        # Import predefined generator modules and get a list of generator classes
        generator_classes = self.__import_external_generators(
            paths=sequencegeneratorlogic.predefined_methods_import_path)

        # create an instance of each class and put them in a temporary list
        generator_instances = [cls(sequencegeneratorlogic) for cls in generator_classes]

        # add references to all generate methods in each instance to a dict
        self.__populate_method_dict(instance_list=generator_instances)

        # populate parameters dictionary from generate method signatures
        self.__populate_parameter_dict()

    @property
    def predefined_generate_methods(self):
        return self._generate_methods

    @property
    def predefined_method_parameters(self):
        return self._generate_method_parameters.copy()

    def __import_external_generators(self, paths):
        """
        Helper method to import all modules from directories contained in paths.
        Find all classes in those modules that inherit exclusively from PredefinedGeneratorBase
        class and return a list of them.

        @param iterable paths: iterable containing paths to import modules from
        @return list: A list of imported valid generator classes
        """
        class_list = list()
        for path in paths:
            if not os.path.exists(path):
                self.log.error('Unable to import generate methods from "{0}".\n'
                               'Path does not exist.'.format(path))
                continue
            # Get all python modules to import from.
            # The assumption is that in the path, there are *.py files,
            # which contain only generator classes!
            module_list = [name[:-3] for name in os.listdir(path) if
                           os.path.isfile(os.path.join(path, name)) and name.endswith('.py')]

            # append import path to sys.path
            if path not in sys.path:
                sys.path.append(path)

            # Go through all modules and create instances of each class found.
            for module_name in module_list:
                # import module
                mod = importlib.import_module('{0}'.format(module_name))
                importlib.reload(mod)
                # get all generator class references defined in the module
                tmp_list = [m[1] for m in inspect.getmembers(mod, self.is_generator_class)]
                # append to class_list
                class_list.extend(tmp_list)
        return class_list

    def __populate_method_dict(self, instance_list):
        """
        Helper method to populate the dictionaries containing all references to callable generate
        methods contained in generator instances passed to this method.

        @param list instance_list: List containing instances of generator classes
        """
        self._generate_methods = dict()
        for instance in instance_list:
            for method_name, method_ref in inspect.getmembers(instance, inspect.ismethod):
                if method_name.startswith('generate_'):
                    self._generate_methods[method_name[9:]] = method_ref
        return

    def __populate_parameter_dict(self):
        """
        Helper method to populate the dictionary containing all possible keyword arguments from all
        generate methods.
        """
        self._generate_method_parameters = dict()
        for method_name, method in self._generate_methods.items():
            method_signature = inspect.signature(method)
            param_dict = dict()
            for name, param in method_signature.parameters.items():
                param_dict[name] = None if param.default is param.empty else param.default

            self._generate_method_parameters[method_name] = param_dict
        return

    @staticmethod
    def is_generator_class(obj):
        """
        Helper method to check if an object is a valid generator class.

        @param object obj: object to check
        @return bool: True if obj is a valid generator class, False otherwise
        """
        if inspect.isclass(obj):
            return PredefinedGeneratorBase in obj.__bases__ and len(obj.__bases__) == 1
        return False
