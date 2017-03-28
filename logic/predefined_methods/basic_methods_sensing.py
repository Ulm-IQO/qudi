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
                       delay_length=0.7e-6, wait_time=1.0e-6, seq_trig_channel='d_ch1', gate_count_channel=''):
    """
    """

    # pre-computations

    period=1/frequency

    rabi_period=self._adjust_to_samplingrate(rabi_period,4)
    tau=self._adjust_to_samplingrate(tau,2)
    laser_length=self._adjust_to_samplingrate(laser_length,1)
    delay_length=self._adjust_to_samplingrate(delay_length,1)

    #trigger + 8*N tau + 2*pi/2 pulse + 2*tauhalf_excess + laser_length + aom_delay + wait_time
    sequence_length=20.0e-9 + 8*xy8_order*tau + rabi_period/2 + laser_length + delay_length + wait_time
    if (sequence_length%period)==0:
        extra_time=0
    else:
        extra_time=period-(sequence_length%period)
    extra_time=self._adjust_to_samplingrate(extra_time,1)


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
    real_start_tauhalf = tau / 2 -  rabi_period / 4
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
    pihalf_element = self._get_mw_element(rabi_period / 4.0, 0.0, mw_channel, False, mw_amp, mw_freq,
                                          0.0)
    # get -x pihalf (3pihalf) element
    pi3half_element = self._get_mw_element(rabi_period / 4.0, 0.0, mw_channel, False, mw_amp,
                                           mw_freq, 180.)
    # get pi elements
    pix_element = self._get_mw_element(rabi_period / 2.0, 0.0, mw_channel, False, mw_amp, mw_freq,
                                       0.0)
    piy_element = self._get_mw_element(rabi_period / 2.0, 0.0, mw_channel, False, mw_amp, mw_freq,
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
    elem_list = []

    elem_list.append(laser_element)
    elem_list.append(delay_element)
    elem_list.append(waiting_element)

    # actual Qdyne XY8 sequence
    elem_list.append(pihalf_element)
    elem_list.append(tauhalf_element)

    for n in range(xy8_order):

        elem_list.append(pix_element)
        elem_list.append(tau_element)
        elem_list.append(piy_element)
        elem_list.append(tau_element)
        elem_list.append(pix_element)
        elem_list.append(tau_element)
        elem_list.append(piy_element)
        elem_list.append(tau_element)
        elem_list.append(piy_element)
        elem_list.append(tau_element)
        elem_list.append(pix_element)
        elem_list.append(tau_element)
        elem_list.append(piy_element)
        elem_list.append(tau_element)
        elem_list.append(pix_element)
        if n != xy8_order-1:
            elem_list.append(tau_element)
    elem_list.append(tauhalf_element)
    elem_list.append(pi3half_element)



    # create XY8-N block object
    block = PulseBlock(name, elem_list)
    self.save_block(name, block)

    # create block list and ensemble object
    block_list = [(block, 0)]
    if seq_trig_channel is not None:
        block_list.append((seq_block, 0))

    # create ensemble out of the block(s)
    block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=True)
    # add metadata to invoke settings later on
    block_ensemble.sample_rate = self.sample_rate
    block_ensemble.activation_config = self.activation_config
    block_ensemble.amplitude_dict = self.amplitude_dict
    block_ensemble.laser_channel = self.laser_channel
    block_ensemble.alternating = False
    block_ensemble.laser_ignore_list = []
    # save ensemble
    self.save_ensemble(name, block_ensemble)
    return block_ensemble


def generate_cpmg_tau(self, name='CPMG_tau', rabi_period=1.0e-8, mw_freq=2870.0e6, mw_amp=0.1,
                     start_tau=0.5e-6, incr_tau=0.01e-6, num_of_points=50, cpmg_order=4,
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
    real_start_tau = start_tau - rabi_period / 2
    real_start_tauhalf = start_tau / 2 - 3 * rabi_period / 8
    if real_start_tau < 0.0 or real_start_tauhalf < 0.0:
        self.log.error('CPMG generation failed! Rabi period of {0:.3e} s is too long for start tau '
                       'of {1:.3e} s.'.format(rabi_period, start_tau))
        return

    # get waiting element
    waiting_element = self._get_idle_element(wait_time, 0.0, False)
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
    piy_element = self._get_mw_element(rabi_period / 2, 0.0, mw_channel, False, mw_amp, mw_freq,
                                       90.0)
    # get tauhalf element
    tauhalf_element = self._get_idle_element(real_start_tauhalf, incr_tau / 2, False)
    # get tau element
    tau_element = self._get_idle_element(real_start_tau, incr_tau, False)

    if seq_trig_channel is not None:
        # get sequence trigger element
        seqtrig_element = self._get_trigger_element(20.0e-9, 0.0, seq_trig_channel, amp=channel_amp)
        # Create its own block out of the element
        seq_block = PulseBlock('seq_trigger', [seqtrig_element])
        # save block
        self.save_block('seq_trigger', seq_block)

    # create CPMG-N block element list
    cpmg_elem_list = []
    # actual CPMG-N sequence
    cpmg_elem_list.append(pihalf_element)
    cpmg_elem_list.append(tauhalf_element)

    for n in range(cpmg_order):
        if n==0:
            cpmg_elem_list.append( self._get_mw_element(rabi_period / 2, 0.0, mw_channel, True, mw_amp,
                                                       mw_freq,0.0))
            cpmg_elem_list.append(self._get_idle_element(real_start_tau, incr_tau, True))
        else:
            cpmg_elem_list.append(piy_element)
            if n != cpmg_order-1:
                cpmg_elem_list.append(tau_element)
    cpmg_elem_list.append(tauhalf_element)
    cpmg_elem_list.append(pihalf_element)
    cpmg_elem_list.append(laser_element)
    cpmg_elem_list.append(delay_element)
    cpmg_elem_list.append(waiting_element)

    if alternating:
        cpmg_elem_list.append(pihalf_element)
        cpmg_elem_list.append(tauhalf_element)
        for n in range(cpmg_order):
            cpmg_elem_list.append(piy_element)
            if n !=cpmg_order - 1:
                cpmg_elem_list.append(tau_element)
        cpmg_elem_list.append(tauhalf_element)
        cpmg_elem_list.append(pi3half_element)
        cpmg_elem_list.append(laser_element)
        cpmg_elem_list.append(delay_element)
        cpmg_elem_list.append(waiting_element)

    # create CPMG-N block object
    cpmg_block = PulseBlock(name, cpmg_elem_list)
    self.save_block(name, cpmg_block)

    # create block list and ensemble object
    block_list = [(cpmg_block, num_of_points - 1)]
    if seq_trig_channel is not None:
        block_list.append((seq_block, 0))

    # create ensemble out of the block(s)
    block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=True)
    # add metadata to invoke settings later on
    block_ensemble.sample_rate = self.sample_rate
    block_ensemble.activation_config = self.activation_config
    block_ensemble.amplitude_dict = self.amplitude_dict
    block_ensemble.laser_channel = self.laser_channel
    block_ensemble.alternating = alternating
    block_ensemble.laser_ignore_list = []
    block_ensemble.controlled_vals_array = tau_array
    # save ensemble
    self.save_ensemble(name, block_ensemble)
    return block_ensemble


def generate_cpmg_nsweep(self, name='CPMG_Nsweep', rabi_period=1.0e-8, mw_freq=2870.0e6, mw_amp=0.1,
                     tau=0.5e-6,start_n=1, incr_n=1, num_of_points=50,
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
    # get pulse number array for measurement ticks
    n_array = start_n + np.arange(num_of_points) * incr_n
    n_array.astype(int)
    # calculate "real" start length of the waiting times (tau and tauhalf)
    real_tau = tau - rabi_period / 2
    real_tauhalf = tau / 2 - 3 * rabi_period / 8
    if real_tau < 0.0 or real_tauhalf < 0.0:
        self.log.error('CPMG-N-sweep generation failed! Rabi period of {0:.3e} s is too long for start tau '
                       'of {1:.3e} s.'.format(rabi_period, tau))
        return

    # get waiting element
    waiting_element = self._get_idle_element(wait_time, 0.0, False)
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
    piy_element = self._get_mw_element(rabi_period / 2, 0.0, mw_channel, False, mw_amp, mw_freq,
                                       90.0)
    # get tauhalf element
    tauhalf_element = self._get_idle_element(real_tauhalf, 0, False)
    # get tau element
    tau_element = self._get_idle_element(real_tau, 0, False)

    if seq_trig_channel is not None:
        # get sequence trigger element
        seqtrig_element = self._get_trigger_element(20.0e-9, 0.0, seq_trig_channel, amp=channel_amp)
        # Create its own block out of the element
        seq_block = PulseBlock('seq_trigger', [seqtrig_element])
        # save block
        self.save_block('seq_trigger', seq_block)

    # create CPMG-N block element list
    elem_list = []
    # actual CPMG-N-sweep sequence

    for outer_counter, outer_element in enumerate(n_array):
        elem_list.append(pihalf_element)
        elem_list.append(tauhalf_element)
        for n in range(outer_element):
            elem_list.append(piy_element)
            if n != outer_element-1:
                elem_list.append(tau_element)
        elem_list.append(tauhalf_element)
        elem_list.append(pihalf_element)
        elem_list.append(laser_element)
        elem_list.append(delay_element)
        elem_list.append(waiting_element)
        if alternating:
            elem_list.append(pihalf_element)
            elem_list.append(tauhalf_element)
            for n in range(outer_element):
                elem_list.append(piy_element)
                if n != outer_element - 1:
                    elem_list.append(tau_element)
            elem_list.append(tauhalf_element)
            elem_list.append(pi3half_element)
            elem_list.append(laser_element)
            elem_list.append(delay_element)
            elem_list.append(waiting_element)

    # create CPMG-N block object
    block = PulseBlock(name, elem_list)
    self.save_block(name, block)

    # create block list and ensemble object
    block_list = [(block, 0)]
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
    block_ensemble.controlled_vals_array = n_array
    # save ensemble
    self.save_ensemble(name, block_ensemble)
    return block_ensemble


def _adjust_to_samplingrate(self,value,divisibility):
    '''
    @param self: Every pulsing device has a sampling rate which is most of the time adjustable
    but always limited. Thus it is not possible to generate any arbitrary time value. This function
    should check if the timing value is generateable with the current sampling rate and if nout round
    it to the next possible value...
    @param value: the desired timing value
    @param divisibility: Takes into account that vonly parts of variables might be used (for example for a pi/2 pulse...)
    @return: value matching to the current sampling rate of pulser
    '''
    resolution=1/self.sample_rate*divisibility
    mod=value%(resolution)
    if mod<resolution/2:
        value=value-mod
    else:
        value=value+resolution-mod
    # correct for computational errors
    value=np.around(value,13)
    return float(value)



