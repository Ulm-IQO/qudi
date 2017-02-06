# -*- coding: utf-8 -*-

"""
This file contains the Qudi Predefined Methods for sequence generator

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




def generate_xy8_qdyne(self, name='XY8_Qdyne', rabi_period=1.0e-8, mw_freq=2870.0e6, mw_amp=0.5, tau=0.5e-6,
                       xy8_order=4, frequency=1.0e6, mw_channel='a_ch1', laser_length=3.0e-7, channel_amp=1.0,
                       delay_length=0.7e-6, wait_time=1.0e-6, seq_trig_channel='', gate_count_channel=''):
    """
    """

    # pre-computations

    period=1/frequency
    print(period)

    #trigger + 8*N tau + 2*pi/2 pulse + 2*tauhalf_excess + laser_length + aom_delay + wait_time
    sequence_length=20.0e-9 + 8*xy8_order*tau + rabi_period/2 + 2*rabi_period/8.0 + laser_length + delay_length + wait_time
    print(sequence_length)
    if (sequence_length%period)==0:
        extra_time=0
    else:
        extra_time=period-(sequence_length%period)
    print(extra_time)


    # Sanity checks
    if gate_count_channel == '':
        gate_count_channel = None
    if seq_trig_channel == '':
        seq_trig_channel = None
    err_code = self._do_channel_sanity_checks(mw_channel=mw_channel,
                                              gate_count_channel=gate_count_channel,
                                              seq_trig_channel=seq_trig_channel)
    if err_code != 0:
        return

    # calculate "real" start length of the waiting times (tau and tauhalf)
    real_start_tau = tau - rabi_period / 2
    real_start_tauhalf = tau / 2 - 3 * rabi_period / 8
    if real_start_tau < 0.0 or real_start_tauhalf < 0.0:
        self.log.error('XY8_Qdyne generation failed! Rabi period of {0:.3e} s is too long for start tau '
                       'of {1:.3e} s.'.format(rabi_period, tau))
        return

    # get waiting element
    waiting_element = self._get_idle_element(wait_time+extra_time, 0.0, False)
    # get laser and delay element
    laser_element, delay_element = self._get_laser_element(laser_length, 0.0, False, delay_length,
                                                           channel_amp, gate_count_channel)
    # get pihalf element
    pihalf_element = self._get_mw_element(rabi_period / 4, 0.0, mw_channel, False, mw_amp, mw_freq,
                                          0.0)
    # get -x pihalf (3pihalf) element
    pi3half_element = self._get_mw_element(rabi_period / 4, 0.0, mw_channel, False, mw_amp,
                                           mw_freq, 180.)
    # get pi elements
    pix_element = self._get_mw_element(rabi_period / 2, 0.0, mw_channel, False, mw_amp, mw_freq,
                                       0.0)
    piy_element = self._get_mw_element(rabi_period / 2, 0.0, mw_channel, False, mw_amp, mw_freq,
                                       90.0)
    # get tauhalf element
    tauhalf_element = self._get_idle_element(real_start_tauhalf, 0, False)
    # get tau element
    tau_element = self._get_idle_element(real_start_tau, 0, False)

    if seq_trig_channel is not None:
        # get sequence trigger element
        seqtrig_element = self._get_trigger_element(20.0e-9, 0.0, seq_trig_channel, amp=channel_amp)
        # Create its own block out of the element
        seq_block = PulseBlock('seq_trigger', [seqtrig_element])
        # save block
        self.save_block('seq_trigger', seq_block)

    # create XY8-N_qdyne block element list
    xy8_qdyne_elem_list = []
    # actual XY8-N sequence
    xy8_qdyne_elem_list.append(pihalf_element)
    xy8_qdyne_elem_list.append(tauhalf_element)

    for n in range(xy8_order):

        xy8_qdyne_elem_list.append(pix_element)
        xy8_qdyne_elem_list.append(tau_element)
        xy8_qdyne_elem_list.append(piy_element)
        xy8_qdyne_elem_list.append(tau_element)
        xy8_qdyne_elem_list.append(pix_element)
        xy8_qdyne_elem_list.append(tau_element)
        xy8_qdyne_elem_list.append(piy_element)
        xy8_qdyne_elem_list.append(tau_element)
        xy8_qdyne_elem_list.append(piy_element)
        xy8_qdyne_elem_list.append(tau_element)
        xy8_qdyne_elem_list.append(pix_element)
        xy8_qdyne_elem_list.append(tau_element)
        xy8_qdyne_elem_list.append(piy_element)
        xy8_qdyne_elem_list.append(tau_element)
        xy8_qdyne_elem_list.append(pix_element)
        if n != xy8_order-1:
            xy8_qdyne_elem_list.append(tau_element)
    xy8_qdyne_elem_list.append(tauhalf_element)
    xy8_qdyne_elem_list.append(pi3half_element)
    xy8_qdyne_elem_list.append(laser_element)
    xy8_qdyne_elem_list.append(delay_element)
    xy8_qdyne_elem_list.append(waiting_element)


    # create XY8-N block object
    xy8_qdyne_block = PulseBlock(name, xy8_qdyne_elem_list)
    self.save_block(name, xy8_qdyne_block)

    # create block list and ensemble object
    block_list = [(xy8_qdyne_block, 0)]
    if seq_trig_channel is not None:
        block_list.append((seq_block, 0))

    # create ensemble out of the block(s)
    block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=True)
    # add metadata to invoke settings later on
    block_ensemble.sample_rate = self.sample_rate
    block_ensemble.activation_config = self.activation_config
    block_ensemble.amplitude_dict = self.amplitude_dict
    block_ensemble.laser_channel = self.laser_channel
    block_ensemble.alternating = True
    block_ensemble.laser_ignore_list = []
    # save ensemble
    self.save_ensemble(name, block_ensemble)
    return block_ensemble


def generate_xy8_freq(self, name='XY8_freq', rabi_period=1.0e-6, mw_freq=2870.0e6, mw_amp=0.1,
                      start_freq=0.1e6, incr_freq=0.01e6, num_of_points=50, xy8_order=4,
                      mw_channel='a_ch1', laser_length=3.0e-6, channel_amp=1.0, delay_length=0.7e-6,
                      wait_time=1.0e-6, seq_trig_channel='', gate_count_channel=''):
    """

    """
    # Sanity checks
    if gate_count_channel == '':
        gate_count_channel = None
    if seq_trig_channel == '':
        seq_trig_channel = None
    err_code = self._do_channel_sanity_checks(mw_channel=mw_channel,
                                              gate_count_channel=gate_count_channel,
                                              seq_trig_channel=seq_trig_channel)
    if err_code != 0:
        return

    # get frequency array for measurement ticks
    freq_array = start_freq + np.arange(num_of_points) * incr_freq
    # get tau array from freq array
    tau_array = 1 / (2 * freq_array)
    # calculate "real" tau and tauhalf arrays
    real_tau_array = tau_array - rabi_period / 2
    real_tauhalf_array = tau_array / 2 - 3 * rabi_period / 8
    if True in (real_tau_array < 0.0) or True in (real_tauhalf_array < 0.0):
        self.log.error('XY8 generation failed! Rabi period of {0:.3e} s is too long for start tau '
                       'of {1:.3e} s.'.format(rabi_period, real_tau_array[0]))
        return

    # get waiting element
    waiting_element = self._get_idle_element(wait_time, 0.0, False)
    # get laser and delay element
    laser_element, delay_element = self._get_laser_element(laser_length, 0.0, False, delay_length,
                                                           channel_amp, gate_count_channel)
    # get pihalf element
    pihalf_element = self._get_mw_element(rabi_period / 4, 0.0, mw_channel, False, mw_amp, mw_freq,
                                          0.0)
    # get 3pihalf element
    pi3half_element = self._get_mw_element(3 * rabi_period / 4, 0.0, mw_channel, False, mw_amp,
                                           mw_freq, 0.0)
    # get pi elements
    pix_element = self._get_mw_element(rabi_period / 2, 0.0, mw_channel, False, mw_amp, mw_freq,
                                       0.0)
    piy_element = self._get_mw_element(rabi_period / 2, 0.0, mw_channel, False, mw_amp, mw_freq,
                                       90.0)

    if seq_trig_channel is not None:
        # get sequence trigger element
        seqtrig_element = self._get_trigger_element(20.0e-9, 0.0, seq_trig_channel, amp=channel_amp)
        # Create its own block out of the element
        seq_block = PulseBlock('seq_trigger', [seqtrig_element])
        # save block
        self.save_block('seq_trigger', seq_block)

    # create XY8-N block element list
    xy8_elem_list = []
    # actual XY8-N sequence
    for i in range(num_of_points):
        # get tau element
        tau_element = self._get_idle_element(real_tau_array[i], 0.0, False)
        # get tauhalf element
        tauhalf_element = self._get_idle_element(real_tauhalf_array[i], 0.0, False)

        xy8_elem_list.append(pihalf_element)
        xy8_elem_list.append(tauhalf_element)
        for n in range(xy8_order):
            xy8_elem_list.append(pix_element)
            xy8_elem_list.append(tau_element)
            xy8_elem_list.append(piy_element)
            xy8_elem_list.append(tau_element)
            xy8_elem_list.append(pix_element)
            xy8_elem_list.append(tau_element)
            xy8_elem_list.append(piy_element)
            xy8_elem_list.append(tau_element)
            xy8_elem_list.append(piy_element)
            xy8_elem_list.append(tau_element)
            xy8_elem_list.append(pix_element)
            xy8_elem_list.append(tau_element)
            xy8_elem_list.append(piy_element)
            xy8_elem_list.append(tau_element)
            xy8_elem_list.append(pix_element)
            if n != xy8_order-1:
                xy8_elem_list.append(tau_element)
        xy8_elem_list.append(tauhalf_element)
        xy8_elem_list.append(pihalf_element)
        xy8_elem_list.append(laser_element)
        xy8_elem_list.append(delay_element)
        xy8_elem_list.append(waiting_element)

        xy8_elem_list.append(pihalf_element)
        xy8_elem_list.append(tauhalf_element)
        for n in range(xy8_order):
            xy8_elem_list.append(pix_element)
            xy8_elem_list.append(tau_element)
            xy8_elem_list.append(piy_element)
            xy8_elem_list.append(tau_element)
            xy8_elem_list.append(pix_element)
            xy8_elem_list.append(tau_element)
            xy8_elem_list.append(piy_element)
            xy8_elem_list.append(tau_element)
            xy8_elem_list.append(piy_element)
            xy8_elem_list.append(tau_element)
            xy8_elem_list.append(pix_element)
            xy8_elem_list.append(tau_element)
            xy8_elem_list.append(piy_element)
            xy8_elem_list.append(tau_element)
            xy8_elem_list.append(pix_element)
            if n != xy8_order - 1:
                xy8_elem_list.append(tau_element)
        xy8_elem_list.append(tauhalf_element)
        xy8_elem_list.append(pi3half_element)
        xy8_elem_list.append(laser_element)
        xy8_elem_list.append(delay_element)
        xy8_elem_list.append(waiting_element)

    # create XY8-N block object
    xy8_block = PulseBlock(name, xy8_elem_list)
    self.save_block(name, xy8_block)

    # create block list and ensemble object
    block_list = [(xy8_block, num_of_points - 1)]
    if seq_trig_channel is not None:
        block_list.append((seq_block, 0))

    # create ensemble out of the block(s)
    block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=True)
    # add metadata to invoke settings later on
    block_ensemble.sample_rate = self.sample_rate
    block_ensemble.activation_config = self.activation_config
    block_ensemble.amplitude_dict = self.amplitude_dict
    block_ensemble.laser_channel = self.laser_channel
    block_ensemble.alternating = True
    block_ensemble.laser_ignore_list = []
    block_ensemble.controlled_vals_array = freq_array
    # save ensemble
    self.save_ensemble(name, block_ensemble)
    return block_ensemble

def generate_Pol20(self, name='Pol 2.0', rabi_period=1.0e-6, mw_freq=2870.0e6, mw_amp=0.1,
                     start_tau=0.5e-6, incr_tau=0.01e-6, num_of_points=50, order=8,
                     mw_channel='a_ch1', laser_length=3.0e-6, channel_amp=1.0, delay_length=0.7e-6,
                     wait_time=1.0e-6, seq_trig_channel='', gate_count_channel='',alternating=True):
    """

    """
    # Sanity checks
    if gate_count_channel == '':
        gate_count_channel = None
    if seq_trig_channel == '':
        seq_trig_channel = None
    err_code = self._do_channel_sanity_checks(mw_channel=mw_channel,
                                              gate_count_channel=gate_count_channel,
                                              seq_trig_channel=seq_trig_channel)
    if err_code != 0:
        return

    # get tau array for measurement ticks
    tau_array = start_tau + np.arange(num_of_points) * incr_tau
    # calculate "real" start length of the waiting times (tau and tauhalf)
    real_start_tau = start_tau - 2.*rabi_period
    if real_start_tau < 0.0 :
        self.log.error('Pol 2.0 generation failed! Rabi period of {0:.3e} s is too long for start tau '
                       'of {1:.3e} s.'.format(rabi_period, start_tau))
        return

    # get waiting element
    waiting_element = self._get_idle_element(wait_time, 0.0, False)
    # get laser and delay element
    laser_element, delay_element = self._get_laser_element(laser_length, 0.0, False, delay_length,
                                                           channel_amp, gate_count_channel)
    # get -x pihalf element
    pihalfminusx_element = self._get_mw_element(rabi_period / 4, 0.0, mw_channel, False, mw_amp, mw_freq,
                                          180.)
    pihalfminusx_element_first = self._get_mw_element(rabi_period / 4, 0.0, mw_channel, True, mw_amp, mw_freq,
                                          180.)
    # get y pihalf element
    pihalfy_element = self._get_mw_element(rabi_period / 4, 0.0, mw_channel, False, mw_amp,
                                           mw_freq, 90.)
    pihalfy_element_first = self._get_mw_element(rabi_period / 4, 0.0, mw_channel, True, mw_amp,
                                           mw_freq, 90.)
    # get pi elements
    pix_element = self._get_mw_element(rabi_period / 2, 0.0, mw_channel, False, mw_amp, mw_freq,
                                       0.0)
    pix_element_first = self._get_mw_element(rabi_period / 2, 0.0, mw_channel, True, mw_amp, mw_freq,
                                       0.0)
    piy_element = self._get_mw_element(rabi_period / 2, 0.0, mw_channel, False, mw_amp, mw_freq,
                                       90.0)
    piy_element_first = self._get_mw_element(rabi_period / 2, 0.0, mw_channel, True, mw_amp, mw_freq,
                                       90.0)
    # get tau/4 element
    tau_element = self._get_idle_element(real_start_tau/4., incr_tau/4., False)
    tau_element_first = self._get_idle_element(real_start_tau/4., incr_tau/4., True)

    if seq_trig_channel is not None:
        # get sequence trigger element
        seqtrig_element = self._get_trigger_element(20.0e-9, 0.0, seq_trig_channel, amp=channel_amp)
        # Create its own block out of the element
        seq_block = PulseBlock('seq_trigger', [seqtrig_element])
        # save block
        self.save_block('seq_trigger', seq_block)

    # create Pol 2.0 block element list
    pol20_elem_list = []
    # actual (Pol 2.0)_2N sequence
    for n in range(2*order):
        if n==0:
            pol20_elem_list.append(pihalfminusx_element_first)
            pol20_elem_list.append(tau_element_first)
            pol20_elem_list.append(piy_element_first)
            pol20_elem_list.append(tau_element_first)
            pol20_elem_list.append(pihalfminusx_element_first)

            pol20_elem_list.append(pihalfy_element_first)
            pol20_elem_list.append(tau_element_first)
            pol20_elem_list.append(pix_element_first)
            pol20_elem_list.append(tau_element_first)
            pol20_elem_list.append(pihalfy_element_first)
        else:
            pol20_elem_list.append(pihalfminusx_element)
            pol20_elem_list.append(tau_element)
            pol20_elem_list.append(piy_element)
            pol20_elem_list.append(tau_element)
            pol20_elem_list.append(pihalfminusx_element)

            pol20_elem_list.append(pihalfy_element)
            pol20_elem_list.append(tau_element)
            pol20_elem_list.append(pix_element)
            pol20_elem_list.append(tau_element)
            pol20_elem_list.append(pihalfy_element)
    pol20_elem_list.append(laser_element)
    pol20_elem_list.append(delay_element)
    pol20_elem_list.append(waiting_element)

    if alternating:
        pol20_elem_list.append(pihalfy_element)
        pol20_elem_list.append(tau_element)
        pol20_elem_list.append(pix_element)
        pol20_elem_list.append(tau_element)
        pol20_elem_list.append(pihalfy_element)

        pol20_elem_list.append(pihalfminusx_element)
        pol20_elem_list.append(tau_element)
        pol20_elem_list.append(piy_element)
        pol20_elem_list.append(tau_element)
        pol20_elem_list.append(pihalfminusx_element)

        pol20_elem_list.append(laser_element)
        pol20_elem_list.append(delay_element)
        pol20_elem_list.append(waiting_element)


    # create Pol 2.0 block object
    pol20_block = PulseBlock(name, pol20_elem_list)
    self.save_block(name, pol20_block)

    # create block list and ensemble object
    block_list = [(pol20_block, num_of_points - 1)]
    if seq_trig_channel is not None:
        block_list.append((seq_block, 0))

    # create ensemble out of the block(s)
    block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=True)
    # add metadata to ensemble object
    block_ensemble.measurement_ticks_list = tau_array
    # save ensemble
    self.save_ensemble(name, block_ensemble)
    return block_ensemble

####################################################################################################
#                                   Helper methods                                              ####
####################################################################################################
def _get_channel_lists(self):
    """
    @return: two lists with the names of digital and analog channels
    """
    # split digital and analogue channels
    digital_channels = [chnl for chnl in self.activation_config if 'd_ch' in chnl]
    analog_channels = [chnl for chnl in self.activation_config if 'a_ch' in chnl]
    return digital_channels, analog_channels


def _get_idle_element(self, length, increment, use_as_tick):
    """
    Creates an idle pulse PulseBlockElement

    @param float length: idle duration in seconds
    @param float increment: idle duration increment in seconds
    @param bool use_as_tick: use as tick flag of the PulseBlockElement

    @return: PulseBlockElement, the generated idle element
    """
    # input params for MW element generation
    idle_params = [{}] * self.analog_channels
    idle_digital = [False] * self.digital_channels
    idle_function = ['Idle'] * self.analog_channels

    # Create idle element
    idle_element = PulseBlockElement(init_length_s=length, increment_s=increment,
                                     pulse_function=idle_function, digital_high=idle_digital,
                                     parameters=idle_params, use_as_tick=use_as_tick)
    return idle_element


def _get_trigger_element(self, length, increment, channel, use_as_tick=False, amp=None):
    """
    Creates a trigger PulseBlockElement

    @param float length: trigger duration in seconds
    @param float increment: trigger duration increment in seconds
    @param string channel: The pulser channel to be triggered.
    @param bool use_as_tick: use as tick flag of the PulseBlockElement
    @param float amp: analog amplitude in case of analog channel in V

    @return: PulseBlockElement, the generated trigger element
    """
    # get channel lists
    digital_channels, analog_channels = self._get_channel_lists()

    # input params for trigger element generation
    trig_params = [{}] * self.analog_channels
    trig_digital = [False] * self.digital_channels
    trig_function = ['Idle'] * self.analog_channels

    # Determine analogue or digital trigger channel and set parameters accordingly.
    if 'd_ch' in channel:
        trig_index = digital_channels.index(channel)
        trig_digital[trig_index] = True
    elif 'a_ch' in channel:
        trig_index = analog_channels.index(channel)
        trig_function[trig_index] = 'DC'
        trig_params[trig_index] = {'amplitude1': amp}

    # Create trigger element
    trig_element = PulseBlockElement(init_length_s=length, increment_s=increment,
                                     pulse_function=trig_function, digital_high=trig_digital,
                                     parameters=trig_params, use_as_tick=use_as_tick)
    return trig_element


def _get_laser_element(self, length, increment, use_as_tick, delay_time=None, amp_V=None, gate_count_chnl=None):
    """
    Creates laser and gate trigger PulseBlockElements

    @param float length: laser pulse duration in seconds
    @param float increment: laser pulse duration increment in seconds
    @param bool use_as_tick: use as tick flag of the PulseBlockElement
    @param float delay_time: (aom-) delay after the laser trigger in seconds
                             (only for gated fast counter)
    @param float amp_V: Analog voltage for laser and gate trigger (if those channels are analog)
    @param string gate_count_chnl: the channel descriptor string for the gate trigger

    @return: PulseBlockElement, two elements for laser and gate trigger (delay element)
    """
    # get channel lists
    digital_channels, analog_channels = self._get_channel_lists()

    # input params for laser element generation
    laser_params = [{}] * self.analog_channels
    laser_digital = [False] * self.digital_channels
    laser_function = ['Idle'] * self.analog_channels
    # input params for delay element generation (for gated fast counter)
    delay_params = [{}] * self.analog_channels
    delay_digital = [False] * self.digital_channels
    delay_function = ['Idle'] * self.analog_channels

    # Determine analogue or digital laser channel and set parameters accordingly.
    if 'd_ch' in self.laser_channel:
        laser_index = digital_channels.index(self.laser_channel)
        laser_digital[laser_index] = True
    elif 'a_ch' in self.laser_channel:
        laser_index = analog_channels.index(self.laser_channel)
        laser_function[laser_index] = 'DC'
        laser_params[laser_index] = {'amplitude1': amp_V}
    # add gate trigger for gated fast counters
    if gate_count_chnl is not None:
        # Determine analogue or digital gate trigger and set parameters accordingly.
        if 'd_ch' in gate_count_chnl:
            gate_index = digital_channels.index(gate_count_chnl)
            laser_digital[gate_index] = True
            delay_digital[gate_index] = True
        elif 'a_ch' in gate_count_chnl:
            gate_index = analog_channels.index(gate_count_chnl)
            laser_function[gate_index] = 'DC'
            laser_params[gate_index] = {'amplitude1': amp_V}
            delay_function[gate_index] = 'DC'
            delay_params[gate_index] = {'amplitude1': amp_V}

    # Create laser element
    laser_element = PulseBlockElement(init_length_s=length, increment_s=increment,
                                      pulse_function=laser_function, digital_high=laser_digital,
                                      parameters=laser_params, use_as_tick=use_as_tick)
    # Create delay element
    delay_element = PulseBlockElement(init_length_s=delay_time, increment_s=0.0,
                                      pulse_function=delay_function, digital_high=delay_digital,
                                      parameters=delay_params, use_as_tick=use_as_tick)
    return laser_element, delay_element


def _get_mw_element(self, length, increment, mw_channel, use_as_tick, amp=None, freq=None,
                    phase=None):
    """
    Creates a MW pulse PulseBlockElement

    @param float length: MW pulse duration in seconds
    @param float increment: MW pulse duration increment in seconds
    @param string mw_channel: The pulser channel controlling the MW. If set to 'd_chX' this will be
                              interpreted as trigger for an external microwave source. If set to
                              'a_chX' the pulser (AWG) will act as microwave source.
    @param bool use_as_tick: use as tick flag of the PulseBlockElement
    @param float freq: MW frequency in case of analogue MW channel in Hz
    @param float amp: MW amplitude in case of analogue MW channel in V
    @param float phase: MW phase in case of analogue MW channel in deg

    @return: PulseBlockElement, the generated MW element
    """
    # get channel lists
    digital_channels, analog_channels = self._get_channel_lists()

    # input params for MW element generation
    mw_params = [{}] * self.analog_channels
    mw_digital = [False] * self.digital_channels
    mw_function = ['Idle'] * self.analog_channels

    # Determine analogue or digital MW channel and set parameters accordingly.
    if 'd_ch' in mw_channel:
        mw_index = digital_channels.index(mw_channel)
        mw_digital[mw_index] = True
    elif 'a_ch' in mw_channel:
        mw_index = analog_channels.index(mw_channel)
        mw_function[mw_index] = 'Sin'
        mw_params[mw_index] = {'amplitude1': amp, 'frequency1': freq, 'phase1': phase}

    # Create MW element
    mw_element = PulseBlockElement(init_length_s=length, increment_s=increment,
                                   pulse_function=mw_function, digital_high=mw_digital,
                                   parameters=mw_params, use_as_tick=use_as_tick)
    return mw_element


def _get_mw_laser_element(self, length, increment, mw_channel, use_as_tick, delay_time=None,
                          laser_amp=None, mw_amp=None, mw_freq=None, mw_phase=None,
                          gate_count_chnl=None):
    """

    @param length:
    @param increment:
    @param mw_channel:
    @param use_as_tick:
    @param delay_time:
    @param laser_amp:
    @param mw_amp:
    @param mw_freq:
    @param mw_phase:
    @param gate_count_chnl:
    @return:
    """
    # get channel lists
    digital_channels, analog_channels = self._get_channel_lists()

    # input params for laser/mw element generation
    laser_mw_params = [{}] * self.analog_channels
    laser_mw_digital = [False] * self.digital_channels
    laser_mw_function = ['Idle'] * self.analog_channels
    # input params for delay element generation (for gated fast counter)
    delay_params = [{}] * self.analog_channels
    delay_digital = [False] * self.digital_channels
    delay_function = ['Idle'] * self.analog_channels

    # Determine analogue or digital laser channel and set parameters accordingly.
    if 'd_ch' in self.laser_channel:
        laser_index = digital_channels.index(self.laser_channel)
        laser_mw_digital[laser_index] = True
    elif 'a_ch' in self.laser_channel:
        laser_index = analog_channels.index(self.laser_channel)
        laser_mw_function[laser_index] = 'DC'
        laser_mw_params[laser_index] = {'amplitude1': laser_amp}
    # add gate trigger for gated fast counters
    if gate_count_chnl is not None:
        # Determine analogue or digital gate trigger and set parameters accordingly.
        if 'd_ch' in gate_count_chnl:
            gate_index = digital_channels.index(gate_count_chnl)
            laser_mw_digital[gate_index] = True
            delay_digital[gate_index] = True
        elif 'a_ch' in gate_count_chnl:
            gate_index = analog_channels.index(gate_count_chnl)
            laser_mw_function[gate_index] = 'DC'
            laser_mw_params[gate_index] = {'amplitude1': laser_amp}
            delay_function[gate_index] = 'DC'
            delay_params[gate_index] = {'amplitude1': laser_amp}
    # Determine analogue or digital MW channel and set parameters accordingly.
    if 'd_ch' in mw_channel:
        mw_index = digital_channels.index(mw_channel)
        laser_mw_digital[mw_index] = True
    elif 'a_ch' in mw_channel:
        mw_index = analog_channels.index(mw_channel)
        laser_mw_function[mw_index] = 'Sin'
        laser_mw_params[mw_index] = {'amplitude1': mw_amp, 'frequency1': mw_freq,
                                     'phase1': mw_phase}

    # Create laser/mw element
    laser_mw_element = PulseBlockElement(init_length_s=length, increment_s=increment,
                                         pulse_function=laser_mw_function,
                                         digital_high=laser_mw_digital, parameters=laser_mw_params,
                                         use_as_tick=use_as_tick)
    # Create delay element
    delay_element = PulseBlockElement(init_length_s=delay_time, increment_s=0.0,
                                      pulse_function=delay_function, digital_high=delay_digital,
                                      parameters=delay_params, use_as_tick=False)
    return laser_mw_element, delay_element


def _do_channel_sanity_checks(self, **kwargs):
    """
    Does sanity checks of specified channels

    @param string kwargs: all channel descriptors to be checked (except laser channel)

    @return: error code (0: specified channels OK, -1: specified channels not OK)
    """
    # sanity checks
    error_code = 0
    for channel in kwargs:
        if kwargs[channel] is not None and kwargs[channel] != '':
            if kwargs[channel] not in self.activation_config:
                self.log.error('{0} "{1}" is not part of current activation_config!'
                               ''.format(channel, kwargs[channel]))
                error_code = -1
    return error_code
