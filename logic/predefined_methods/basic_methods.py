# -*- coding: utf-8 -*-

"""
This file contains the QuDi Predefined Methods for sequence generator

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

Copyright (C) 2016 Alexander Stark alexander.stark@uni-ulm.de
"""


from logic.sequence_generator_logic import Pulse_Block_Element
from logic.sequence_generator_logic import Pulse_Block
from logic.sequence_generator_logic import Pulse_Block_Ensemble
from logic.sequence_generator_logic import Pulse_Sequence


def generate_laser_on(self, name='Laser_On', laser_time_bins=3000,
                      laser_channel=1, laser_amp_V=1.0):
    """ Generates Laser on.

    @param str name: Name of the Pulse
    @param int laser_time_bins: number of bins
    @param int laser_channel: channel number, positive number are digitals,
                              negative number are positive channels
    """
    # laser_time_bins = self.sample_rate*3e-6 #3mus
    analog_params = [{}]*self.analog_channels
    laser_markers = [False]*self.digital_channels
    pulse_function = ['Idle']*self.analog_channels

    # Choose digital channesl to be positive, analog channels negative
    # Zero is not defined.
    if laser_channel > 0 and laser_channel <= self.digital_channels:
        laser_markers[laser_channel-1] = True
    elif laser_channel < 0 and laser_channel >= -self.analog_channels:
        pulse_function[abs(laser_channel)-1] = 'DC'
        analog_params[abs(laser_channel)-1] = {'amplitude1': laser_amp_V}
    else:
        self.logMsg('Value of {0} is not a proper laser channel. Digital laser '
                    'channels are positive values 1=d_ch1, 2=d_ch2, '
                    '... and analog channel numbers are chosen by a negative '
                    'number -1=a_ch1, -2=a_ch2, ... where number 0 is an '
                    'invalid input. Make your choice!', msgType='error')
        return

    # generate elements parameters of a Pulse_Block_Element:

    laser_element = Pulse_Block_Element(init_length_bins=laser_time_bins,
                                        analog_channels=self.analog_channels,
                                        digital_channels=self.digital_channels,
                                        increment_bins=0,
                                        pulse_function=pulse_function,
                                        marker_active=laser_markers,
                                        parameters=analog_params)

    # Create the Pulse_Block_Element objects and append them to the element
    # list.
    element_list = []
    element_list.append(laser_element)

    #FIXME: that has to be fixed in the generation
    laser_channel_index = abs(laser_channel)

    # create the Pulse_Block object.
    block = Pulse_Block(name, element_list, laser_channel_index)
    # put block in a list with repetitions
    block_list = [(block, 0)]
    # create ensemble out of the block(s)
    block_ensemble = Pulse_Block_Ensemble(name, block_list,
                                          laser_channel_index,
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

def generate_laser_mw_on(self, name='Laser_MW_On', time_bins=3000,
                         laser_channel=1, laser_amp_V=1, mw_channel=-1,
                         mw_freq_MHz=100, mw_amp_V=1.0):
    if laser_channel == mw_channel:
        self.logMsg('Laser and Microwave channel cannot be the same. Change '
                    'that!', msgType='error')
        return

    analog_params = [{}]*self.analog_channels
    laser_markers = [False]*self.digital_channels
    pulse_function = ['Idle']*self.analog_channels

    # Choose digital channel to be positive, analog channels negative
    # Zero is not defined.
    if laser_channel > 0 and laser_channel <= self.digital_channels:
        laser_markers[laser_channel-1] = True
    elif laser_channel < 0 and laser_channel >= -self.analog_channels:
        pulse_function[abs(laser_channel)-1] = 'DC'
        analog_params[abs(laser_channel)-1] = {'amplitude1': laser_amp_V}
    else:
        self.logMsg('Value of {0} is not a proper laser channel. Digital laser '
                    'channels are positive values 1=d_ch1, 2=d_ch2, '
                    '... and analog channel numbers are chosen by a negative '
                    'number -1=a_ch1, -2=a_ch2, ... where number 0 is an '
                    'invalid input. Make your choise!', msgType='error')
        return

    if mw_channel > 0 and mw_channel <= self.digital_channels:
        laser_markers[mw_channel-1] = True
    elif mw_channel < 0 and mw_channel >= -self.analog_channels:
        pulse_function[abs(mw_channel)-1] = 'Sin'
        mw_freq = mw_freq_MHz*1e6
        analog_params[abs(mw_channel)-1] = {'amplitude1':mw_amp_V, 'frequency1':mw_freq}
    else:
        self.logMsg('Value of {0} is not a proper mw channel. Digital laser '
                    'channels are positive values 1=d_ch1, 2=d_ch2, '
                    '... and analog channel numbers are chosen by a negative '
                    'number -1=a_ch1, -2=a_ch2, ... where number 0 is an '
                    'invalid input. Make your choise!', msgType='error')
        return

    # generate elements parameters of a Pulse_Block_Element:

    laser_element = Pulse_Block_Element(init_length_bins=time_bins,
                                        analog_channels=self.analog_channels,
                                        digital_channels=self.digital_channels,
                                        increment_bins=0,
                                        pulse_function=pulse_function,
                                        marker_active=laser_markers,
                                        parameters=analog_params)

    # Create the Pulse_Block_Element objects and append them to the element
    # list.
    element_list = []
    element_list.append(laser_element)

    #FIXME: that has to be fixed in the generation
    laser_channel_index = abs(laser_channel)

    # create the Pulse_Block object.
    block = Pulse_Block(name, element_list, laser_channel_index)
    # put block in a list with repetitions
    block_list = [(block, 0)]
    # create ensemble out of the block(s)
    block_ensemble = Pulse_Block_Ensemble(name, block_list,
                                          laser_channel_index,
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

def generate_rabi(self, name='Rabi', tau_start_ns=5, tau_step_ns=10,
                  number_of_taus=50, mw_freq_MHz=2800, mw_amp_V=1.0,
                  mw_channel=-1, laser_time_ns=3000, laser_channel=1,
                  channel_amp_V=1, aom_delay_ns=500, open_count_channel=2,
                  seq_channel=3, wait_time_ns=1500):
    """ Converter function to use ns input instead of bins. """

    tau_start_bins = int(self.sample_rate/1e9 * tau_start_ns)
    tau_step_bins = int(self.sample_rate/1e9 * tau_step_ns)
    laser_time_bins = int(self.sample_rate/1e9 * laser_time_ns)
    aom_delay_bin = int(self.sample_rate/1e9 * aom_delay_ns)
    wait_time_bin = int(self.sample_rate/1e9 * wait_time_ns)

    self.generate_rabi_bins(name, tau_start_bins, tau_step_bins, number_of_taus,
                            mw_freq_MHz, mw_amp_V, mw_channel, laser_time_bins,
                            laser_channel, channel_amp_V, aom_delay_bin,
                            open_count_channel, seq_channel, wait_time_bin)


def generate_rabi_bins(self, name='Rabi', tau_start_bins=7, tau_step_bins=70,
                  number_of_taus=50, mw_freq_MHz=7784.13,  mw_amp_V=1.0,
                  mw_channel=-1, laser_time_bins=3000, laser_channel=1,
                  channel_amp_V=1, aom_delay_bins=50, open_count_channel=2,
                  seq_channel=3, wait_time_bins=500):

    if laser_channel == mw_channel:
        self.logMsg('Laser and Microwave channel cannot be the same. Change '
                    'that!', msgType='error')
        return

    analog_params = [{}]*self.analog_channels
    markers = [False]*self.digital_channels
    pulse_function = ['Idle']*self.analog_channels

    # Choose digital channel to be positive, analog channels negative
    # Zero is not defined.
    if mw_channel > 0 and mw_channel <= self.digital_channels:
        markers[mw_channel-1] = True
    elif mw_channel < 0 and mw_channel >= -self.analog_channels:
        pulse_function[abs(mw_channel)-1] = 'Sin'
        mw_freq = mw_freq_MHz*1e6
        analog_params[abs(mw_channel)-1] = {'amplitude1':mw_amp_V, 'frequency1':mw_freq}
    else:
        self.logMsg('Value of {0} is not a proper mw_channel. Digital laser '
                    'channels are positive values 1=d_ch1, 2=d_ch2, '
                    '... and analog channel numbers are chosen by a negative '
                    'number -1=a_ch1, -2=a_ch2, ... where number 0 is an '
                    'invalid input. Make your choice!', msgType='error')
        return

    mw_element = Pulse_Block_Element(init_length_bins=tau_start_bins,
                                     analog_channels=self.analog_channels,
                                     digital_channels=self.digital_channels,
                                     increment_bins=tau_step_bins,
                                     pulse_function=pulse_function,
                                     marker_active=markers,
                                     parameters=analog_params,
                                     use_as_tick=True)

    analog_params = [{}]*self.analog_channels
    markers = [False]*self.digital_channels
    pulse_function = ['Idle']*self.analog_channels

    # Choose digital channel to be positive, analog channels negative
    # Zero is not defined.
    if laser_channel > 0 and laser_channel <= self.digital_channels:
        markers[laser_channel-1] = True
    elif laser_channel < 0 and laser_channel >= -self.analog_channels:
        pulse_function[abs(laser_channel)-1] = 'DC'
        analog_params[abs(laser_channel)-1] = {'amplitude1': channel_amp_V}
    else:
        self.logMsg('Value of {0} is not a proper laser channel. Digital laser '
                    'channels are positive values 1=d_ch1, 2=d_ch2, '
                    '... and analog channel numbers are chosen by a negative '
                    'number -1=a_ch1, -2=a_ch2, ... where number 0 is an '
                    'invalid input. Make your choice!', msgType='error')
        return

    if open_count_channel > 0 and open_count_channel <= self.digital_channels:
        markers[open_count_channel-1] = True
    elif open_count_channel < 0 and open_count_channel >= -self.analog_channels:
        pulse_function[abs(open_count_channel)-1] = 'DC'
        analog_params[abs(open_count_channel)-1] = {'amplitude1': channel_amp_V}

    laser_element = Pulse_Block_Element(laser_time_bins, self.analog_channels,
                                        self.digital_channels, 0,
                                        pulse_function, markers,
                                        analog_params)

    analog_params = [{}]*self.analog_channels
    pulse_function = ['Idle']*self.analog_channels
    markers = [False]*self.digital_channels

    if open_count_channel > 0 and open_count_channel <= self.digital_channels:
        markers[open_count_channel-1] = True
    elif open_count_channel < 0 and open_count_channel >= -self.analog_channels:
        pulse_function[abs(open_count_channel)-1] = 'DC'
        analog_params[abs(open_count_channel)-1] = {'amplitude1': channel_amp_V}

    aomdelay_element = Pulse_Block_Element(aom_delay_bins, self.analog_channels,
                                           self.digital_channels, 0,
                                           pulse_function, markers,
                                           analog_params)

    analog_params = [{}]*self.analog_channels
    pulse_function = ['Idle']*self.analog_channels
    markers = [False]*self.digital_channels

    waiting_element = Pulse_Block_Element(wait_time_bins, self.analog_channels,
                                          self.digital_channels, 0,
                                          pulse_function, markers,
                                          analog_params)

    analog_params = [{}]*self.analog_channels
    pulse_function = ['Idle']*self.analog_channels
    markers = [False]*self.digital_channels

    if seq_channel > 0 and seq_channel <= self.digital_channels:
        markers[open_count_channel-1] = True
    elif seq_channel < 0 and seq_channel >= -self.analog_channels:
        pulse_function[abs(seq_channel)-1] = 'DC'
        analog_params[abs(seq_channel)-1] = {'amplitude1': channel_amp_V}


    seqtrig_element = Pulse_Block_Element(100, self.analog_channels,
                                          self.digital_channels, 0,
                                          pulse_function,
                                          markers,
                                          analog_params)

    element_list = [mw_element, laser_element, aomdelay_element, waiting_element]

    #FIXME: that has to be fixed in the generation
    laser_channel_index = abs(laser_channel)

    rabi_block = Pulse_Block(name, element_list, laser_channel_index)

    # remember number_of_taus=0 also counts as first round

    block_list = [(rabi_block, number_of_taus-1)]
    if seq_channel != 0:
        seq_block = Pulse_Block('seq_trigger', [seqtrig_element], laser_channel_index)
        block_list.append((seq_block, 0))
        # save block
        self.save_block('seq_trigger', seq_block)

    # create ensemble out of the block(s)
    block_ensemble = Pulse_Block_Ensemble(name, block_list, laser_channel_index,
                                          rotating_frame=False)

    # save block
    self.save_block(name, rabi_block)
    # save ensemble
    self.save_ensemble(name, block_ensemble)
    # set current block
    self.current_block = rabi_block
    # set current block ensemble
    self.current_ensemble = block_ensemble
    # update ensemble list
    self.refresh_ensemble_list()
    return

def generate_pulsedodmr(self, name='PulsedODMR', mw_time_ns=1000,
                        mw_freq_MHz=100.0,  mw_amp_V=1.0, mw_channel=-1,
                        laser_time_ns=3000, laser_channel=1, laser_amp_V=1,
                        wait_time_ns=1500):

    mw_time_bins = int(self.sample_rate/1e9 * mw_time_ns)
    laser_time_bins = int(self.sample_rate/1e9 * laser_time_ns)
    wait_time_bins = int(self.sample_rate/1e9 * wait_time_ns)

    self.generate_pulsedodmr_bins(name, mw_time_bins, mw_freq_MHz, mw_amp_V,
                                  mw_channel, laser_time_bins, laser_channel,
                                  laser_amp_V, wait_time_bins)
    """ Converter function to use ns input instead of bins. """

def generate_pulsedodmr_bins(self, name='PulsedODMR', mw_time_bins=1000,
                        mw_freq_MHz=100.0,  mw_amp_V=1.0, mw_channel=-1,
                        laser_time_bins=3000, laser_channel=1, laser_amp_V=1,
                        wait_time_bins=1500):


    if laser_channel == mw_channel:
        self.logMsg('Laser and Microwave channel cannot be the same. Change '
                    'that!', msgType='error')
        return

    analog_params = [{}]*self.analog_channels
    markers = [False]*self.digital_channels
    pulse_function = ['Idle']*self.analog_channels

    # Choose digital channel to be positive, analog channels negative
    # Zero is not defined.
    if mw_channel > 0 and mw_channel <= self.digital_channels:
        markers[mw_channel-1] = True
    elif mw_channel < 0 and mw_channel >= -self.analog_channels:
        pulse_function[abs(mw_channel)-1] = 'Sin'
        mw_freq = mw_freq_MHz*1e6
        analog_params[abs(mw_channel)-1] = {'amplitude1': mw_amp_V, 'frequency1': mw_freq}
    else:
        self.logMsg('Value of {0} is not a proper mw_channel. Digital laser '
                    'channels are positive values 1=d_ch1, 2=d_ch2, '
                    '... and analog channel numbers are chosen by a negative '
                    'number -1=a_ch1, -2=a_ch2, ... where number 0 is an '
                    'invalid input. Make your choice!', msgType='error')
        return

    mw_element = Pulse_Block_Element(init_length_bins=mw_time_bins,
                                     analog_channels=self.analog_channels,
                                     digital_channels=self.digital_channels,
                                     increment_bins=0,
                                     pulse_function=pulse_function,
                                     marker_active=markers,
                                     parameters=analog_params,
                                     use_as_tick=True)

    analog_params = [{}]*self.analog_channels
    markers = [False]*self.digital_channels
    pulse_function = ['Idle']*self.analog_channels

    # Choose digital channel to be positive, analog channels negative
    # Zero is not defined.
    if laser_channel > 0 and laser_channel <= self.digital_channels:
        markers[laser_channel-1] = True
    elif laser_channel < 0 and laser_channel >= -self.analog_channels:
        pulse_function[abs(laser_channel)-1] = 'DC'
        analog_params[abs(laser_channel)-1] = {'amplitude1': laser_amp_V}
    else:
        self.logMsg('Value of {0} is not a proper laser channel. Digital laser '
                    'channels are positive values 1=d_ch1, 2=d_ch2, '
                    '... and analog channel numbers are chosen by a negative '
                    'number -1=a_ch1, -2=a_ch2, ... where number 0 is an '
                    'invalid input. Make your choice!', msgType='error')
        return

    laser_element = Pulse_Block_Element(laser_time_bins, self.analog_channels,
                                        self.digital_channels, 0,
                                        pulse_function, markers,
                                        analog_params)

    analog_params = [{}]*self.analog_channels
    pulse_function = ['Idle']*self.analog_channels
    markers = [False]*self.digital_channels

    waiting_element = Pulse_Block_Element(wait_time_bins, self.analog_channels,
                                          self.digital_channels, 0,
                                          pulse_function, markers,
                                          analog_params)

    element_list = [mw_element, laser_element, waiting_element]

    #FIXME: that has to be fixed in the generation
    laser_channel_index = abs(laser_channel)

    pulsed_odmr_block = Pulse_Block(name, element_list, laser_channel_index)
    # save block
    self.save_block(name, pulsed_odmr_block)
    # set current block
    self.current_block = pulsed_odmr_block

    block_list = [(pulsed_odmr_block, 0)]

    # create ensemble out of the block(s)
    block_ensemble = Pulse_Block_Ensemble(name, block_list, laser_channel_index,
                                          rotating_frame=False)
    # save ensemble
    self.save_ensemble(name, block_ensemble)

    # set current block ensemble
    self.current_ensemble = block_ensemble
    # update ensemble list
    self.refresh_ensemble_list()




# def generate_pulsedodmr(self, name='PulsedODMR', start_freq=0.0, stop_freq=0.0,
#                         number_of_points=0, amp_V=0.0, pi_bins=0,
#                         aom_delay_bins=0, laser_time_bins=0,
#                         use_seqtrig=True):
#
#     # create parameter dictionary list for MW signal
#     mw_params = [{},{}]
#     mw_params[0]['amplitude1'] = amp_V
#     mw_params[0]['phase1'] = 0
#     no_analog_params = [{},{}]
#     laser_markers = [True, True, False, False]
#     gate_markers = [False, True, False, False]
#     idle_markers = [False, False, False, False]
#     seqtrig_markers = [False, False, True, False]
#
#     # create frequency list
#     freq_list = np.linspace(start_freq, stop_freq, number_of_points)
#
#     # generate elements
#     laser_element = Pulse_Block_Element(laser_time_bins, 2, 4, 0, ['Idle', 'Idle'], laser_markers, no_analog_params)
#     aomdelay_element = Pulse_Block_Element(aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], gate_markers, no_analog_params)
#     waiting_element = Pulse_Block_Element((1e-6*self.sample_rate)-aom_delay_bins, 2, 4, 0, ['Idle', 'Idle'], idle_markers, no_analog_params)
#     seqtrig_element = Pulse_Block_Element(250, 2, 4, 0, ['Idle', 'Idle'], seqtrig_markers, no_analog_params)
#     # put elements in a list to create the block
#     element_list = []
#     for freq in freq_list:
#         # create copy of parameter dict to use for this frequency
#         temp_params = [mw_params[0].copy(),{}]
#         temp_params[0]['frequency1'] = freq
#         # create actual pi-pulse element
#         pi_element = Pulse_Block_Element(pi_bins, 2, 4, 0, ['Sin', 'Idle'], idle_markers, temp_params)
#         # create measurement elements for this frequency
#         element_list.append(laser_element)
#         element_list.append(aomdelay_element)
#         element_list.append(waiting_element)
#         element_list.append(pi_element)
#     if use_seqtrig:
#         element_list.append(seqtrig_element)
#
#     # create block
#     block = Pulse_Block(name, element_list)
#     # put block in a list with repetitions
#     block_list = [(block, 0),]
#     # create ensemble out of the block(s)
#     block_ensemble = Pulse_Block_Ensemble(name, block_list, freq_list, number_of_points, False)
#     # save block
#     # self.save_block(name, block)
#     # save ensemble
#     self.save_ensemble(name, block_ensemble)
#     # set current block
#     self.current_block = block
#     # set current block ensemble
#     self.current_ensemble = block_ensemble
#     # update ensemble list
#     self.refresh_ensemble_list()
#     return

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
    # name = 'XY8_' + str(N) + '_taustart_' + str(measurement_ticks_list[0]) + '_tauend_' + str(measurement_ticks_list[-1]) + '_numtaus_' + str(len(measurement_ticks_list))
    XY8_ensemble = Pulse_Block_Ensemble(name, block_list, measurement_ticks_list, number_of_taus, True)
    # save ensemble
    self.save_ensemble(name, XY8_ensemble)
    # set current block ensemble
    self.current_ensemble = XY8_ensemble
    # set first XY8-N tau block as current block
    self.current_block = blocks[0]
    # update ensemble list
    self.refresh_ensemble_list()