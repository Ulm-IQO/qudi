# -*- coding: utf-8 -*-

"""
This file contains Qudi Predefined Methods for sequence generator

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


from logic.pulse_objects import PulseBlockElement
from logic.pulse_objects import PulseBlock
from logic.pulse_objects import PulseBlockEnsemble
from logic.pulse_objects import PulseSequence
import numpy as np


"""
General Pulse Creation Procedure:
=================================
- Create at first each PulseBlockElement object
- add all PulseBlockElement object to a list and combine them to a
  PulseBlock object.
- Create all needed PulseBlock object with that idea, that means
  PulseBlockElement objects which are grouped to PulseBlock objects.
- Create from the PulseBlock objects a PulseBlockEnsemble object.
- If needed and if possible, combine the created PulseBlockEnsemble objects
  to the highest instance together in a PulseSequence object.
"""


def generate_superres_seq(self, name='Superres', pi_length_1=1.0e-7, pi_length_2=1.0e-7,
                          mw_freq_1=2.77e9, mw_freq_2=2.97e9, mw_amp_1=0.1, mw_amp_2=0.1,
                          mw_channel='a_ch1', laser_length=3.0e-7, channel_amp=1.0,
                          wait_time=1.5e-6):
    """

    """
    # get waiting element
    waiting_element = self._get_idle_element(wait_time, 0.0, False)
    # get laser element
    laser_element, dummy = self._get_laser_element(laser_length, 0.0, False, amp_V=channel_amp)
    # get dummy element and both mw elements for pi pulses
    pi0_element = self._get_idle_element(pi_length_1, 0.0, False)
    pi1_element = self._get_mw_element(pi_length_1, 0.0, mw_channel, False, mw_amp_1, mw_freq_1,
                                       0.0)
    pi2_element = self._get_mw_element(pi_length_2, 0.0, mw_channel, False, mw_amp_2, mw_freq_2,
                                       0.0)

    # Create element lists for Superres PulseBlock
    # Dummy block
    element_list_0 = []
    element_list_0.append(pi0_element)
    element_list_0.append(laser_element)
    element_list_0.append(waiting_element)
    # pi pulse 1 block
    element_list_1 = []
    element_list_1.append(pi1_element)
    element_list_1.append(laser_element)
    element_list_1.append(waiting_element)
    # pi pulse 2 block
    element_list_2 = []
    element_list_2.append(pi2_element)
    element_list_2.append(laser_element)
    element_list_2.append(waiting_element)

    # Create PulseBlock objects
    dummy_block = PulseBlock(name + '_dummy', element_list_0)
    pi1_block = PulseBlock(name + '_pi1', element_list_1)
    pi2_block = PulseBlock(name + '_pi2', element_list_2)
    # save blocks
    self.save_block(name + '_dummy', dummy_block)
    self.save_block(name + '_pi1', pi1_block)
    self.save_block(name + '_pi2', pi2_block)

    # create ensembles out of the blocks. remember number_of_taus=0 also counts as first round.
    dummy_ensemble = PulseBlockEnsemble(name=name + '_dummy', block_list=[(dummy_block, 0)],
                                        rotating_frame=False)
    pi1_ensemble = PulseBlockEnsemble(name=name + '_pi1', block_list=[(pi1_block, 0)],
                                      rotating_frame=False)
    pi2_ensemble = PulseBlockEnsemble(name=name + '_pi2', block_list=[(pi2_block, 0)],
                                      rotating_frame=False)
    # save ensembles
    self.save_ensemble(name + '_dummy', dummy_ensemble)
    self.save_ensemble(name + '_pi1', pi1_ensemble)
    self.save_ensemble(name + '_pi2', pi2_ensemble)

    # Create sequence out of the ensembles
    seq_param_list = []
    seq_param_init = {'repetitions': 0, 'trigger_wait': 1, 'go_to': 0, 'event_jump_to': 3}
    seq_param = {'repetitions': 0, 'trigger_wait': 0, 'go_to': 0, 'event_jump_to': 0}
    seq_param_last = {'repetitions': 0, 'trigger_wait': 0, 'go_to': 0, 'event_jump_to': 2}
    seq_param_list.append((dummy_ensemble, seq_param_init))
    seq_param_list.append((dummy_ensemble, seq_param))
    seq_param_list.append((pi1_ensemble, seq_param))
    seq_param_list.append((pi2_ensemble, seq_param_last))
    pulse_sequence = PulseSequence(name, seq_param_list, False)

    # add metadata to invoke settings later on
    pulse_sequence.controlled_vals_array = np.array([0.0, mw_freq_1, mw_freq_2])
    pulse_sequence.sample_rate = self.sample_rate
    pulse_sequence.activation_config = self.activation_config
    pulse_sequence.amplitude_dict = self.amplitude_dict
    pulse_sequence.laser_channel = self.laser_channel
    pulse_sequence.alternating = False
    pulse_sequence.laser_ignore_list = []

    # save sequence
    self.save_sequence(name, pulse_sequence)
    return pulse_sequence
