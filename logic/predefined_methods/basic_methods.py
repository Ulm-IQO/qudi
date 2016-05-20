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


"""
General Pulse Creation Procedure:
=================================
- Create at first each Pulse_Block_Element object
- add all Pulse_Block_Element object to a list and combine them to a
  Pulse_Block object.
- Create all needed Pulse_Block object with that idea, that means
  Pulse_Block_Element objects which are grouped to Pulse_Block objects.
- Create from the Pulse_Block objects a Pulse_Block_Ensemble object.
- If needed and if possible, combine the created Pulse_Block_Ensemble objects
  to the highest instance together in a Pulse_Sequence object.
"""


def generate_laser_on(self, name='Laser_On', laser_time_bins=3000,
                      laser_channel=1, laser_amp_V=1.0):
    """ Generates Laser on.

    @param str name: Name of the Pulse
    @param int laser_time_bins: number of bins
    @param int laser_channel: channel number, positive number are digitals,
                              negative number are positive channels

    @return object: the generated Pulse_Block_Ensemble object.
    """
    # laser_time_bins = self.get_sample_rate()*3e-6 #3mus
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

    return block_ensemble

def generate_laser_mw_on(self, name='Laser_MW_On', time_bins=3000,
                         laser_channel=1, laser_amp_V=1, mw_channel=-1,
                         mw_freq_MHz=100, mw_amp_V=1.0):
    """ General generation method for laser on and microwave on generation.

    @param self:
    @param name:
    @param time_bins:
    @param laser_channel:
    @param laser_amp_V:
    @param mw_channel:
    @param mw_freq_MHz:
    @param mw_amp_V:

    @return object: the generated Pulse_Block_Ensemble object.
    """

    if laser_channel == mw_channel:
        self.logMsg('Laser and Microwave channel cannot be the same. Change '
                    'that!', msgType='error')
        return

    # -- laser element --

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
        analog_params[abs(mw_channel)-1] = {'amplitude1':mw_amp_V, 'frequency1':mw_freq, 'phase1': 0.0}
    else:
        self.logMsg('A value "{0}" is not a proper mw channel. Digital laser '
                    'channels are positive values 1=d_ch1, 2=d_ch2, '
                    '... and analog channel numbers are chosen by a negative '
                    'number -1=a_ch1, -2=a_ch2, ... where number 0 is an '
                    'invalid input. Make your choise!'.format(mw_channel),
                    msgType='error')
        return

    laser_element = Pulse_Block_Element(init_length_bins=time_bins,
                                        analog_channels=self.analog_channels,
                                        digital_channels=self.digital_channels,
                                        increment_bins=0,
                                        pulse_function=pulse_function,
                                        marker_active=laser_markers,
                                        parameters=analog_params)

    # -------------------

    # Create the Pulse_Block_Element objects and append them to the element
    # list.
    element_list = [laser_element]

    #FIXME: that has to be fixed in the generation
    laser_channel_index = abs(laser_channel)-1

    # create the Pulse_Block object.
    block = Pulse_Block(name, element_list, laser_channel_index)
    # put block in a list with repetitions
    block_list = [(block, 0)]
    # save block
    self.save_block(name, block)
    # set current block
    self.current_block = block

    # create ensemble out of the block(s)
    block_ensemble = Pulse_Block_Ensemble(name, block_list,
                                          laser_channel_index,
                                          rotating_frame=False)
    # save ensemble
    self.save_ensemble(name, block_ensemble)
    # set current block ensemble
    self.current_ensemble = block_ensemble
    # update ensemble list
    self.refresh_ensemble_list()

    return block_ensemble


def generate_idle_ens(self, name='Idle', idle_time_ns=1500, laser_channel=2):
    """ Converter function to use ns input instead of bins.

    @param str name:
    @param int idle_time_bins:
    @param int laser_channel:
    @return:
    """

    idle_time_bins = int(self.get_sample_rate()/1e9 * idle_time_ns)

    return self.generate_idle_ens_bins(name=name,idle_time_bins=idle_time_bins,
                                       laser_channel=laser_channel)


def generate_idle_ens_bins(self, name='Idle', idle_time_bins=1500, laser_channel=2):
    """ Generate just a simple idle ensemble element.

    @param str name:
    @param int idle_time_bins:

    @return object: the generated Pulse_Block_Ensemble object.
    """

    # all this arrays have to be filled with the appropriate values. Fill them
    # with default values:
    analog_params = [{}]*self.analog_channels
    markers = [False]*self.digital_channels
    pulse_function = ['Idle']*self.analog_channels

    idle_element = Pulse_Block_Element(idle_time_bins, self.analog_channels,
                                          self.digital_channels, 0,
                                          pulse_function, markers,
                                          analog_params)

    #FIXME: that has to be fixed in the generation
    laser_channel_index = abs(laser_channel)-1

    elem_list = [idle_element]

    wait_block = Pulse_Block(name, elem_list, laser_channel_index)
    # save block
    self.save_block(name, wait_block)
    # set current block
    self.current_block = wait_block

    # remember number_of_taus=0 also counts as first round
    block_list = [(wait_block, 0)]

    # create ensemble out of the block(s)
    block_ensemble = Pulse_Block_Ensemble(name, block_list, laser_channel_index,
                                          rotating_frame=False)
    # save ensemble
    self.save_ensemble(name, block_ensemble)

    # set current block ensemble
    self.current_ensemble = block_ensemble

    return block_ensemble

def generate_rabi(self, name='Rabi', tau_start_ns=5, tau_step_ns=10,
                  number_of_taus=50, mw_freq_MHz=2800, mw_amp_V=1.0,
                  mw_channel=-1, laser_time_ns=3000, laser_channel=2,
                  channel_amp_V=1, aom_delay_ns=500, open_count_channel=3,
                  seq_channel=4, wait_time_ns=1500):
    """ Converter function to use ns input instead of bins. """

    tau_start_bins = int(self.get_sample_rate()/1e9 * tau_start_ns)
    tau_step_bins = int(self.get_sample_rate()/1e9 * tau_step_ns)
    laser_time_bins = int(self.get_sample_rate()/1e9 * laser_time_ns)
    aom_delay_bins = int(self.get_sample_rate()/1e9 * aom_delay_ns)
    wait_time_bin = int(self.get_sample_rate()/1e9 * wait_time_ns)

    self.generate_rabi_bins(name, tau_start_bins, tau_step_bins, number_of_taus,
                            mw_freq_MHz, mw_amp_V, mw_channel, laser_time_bins,
                            laser_channel, channel_amp_V, aom_delay_bins,
                            open_count_channel, seq_channel, wait_time_bin)


def generate_rabi_bins(self, name='Rabi', tau_start_bins=7, tau_step_bins=70,
                  number_of_taus=50, mw_freq_MHz=7784.13,  mw_amp_V=1.0,
                  mw_channel=-1, laser_time_bins=3000, laser_channel=2,
                  channel_amp_V=1, aom_delay_bins=50, open_count_channel=3,
                  seq_channel=4, wait_time_bins=500):

    if laser_channel == mw_channel:
        self.logMsg('Laser and Microwave channel cannot be the same. Change '
                    'that!', msgType='error')
        return

    # --- mw element ----

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
        analog_params[abs(mw_channel)-1] = {'amplitude1': mw_amp_V, 'frequency1': mw_freq, 'phase1': 0.0}
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

    # -------------------

    # -- laser element --

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

    # -------------------

    # -- aom delay element --

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

    # -------------------

    # -- wait time element --

    analog_params = [{}]*self.analog_channels
    pulse_function = ['Idle']*self.analog_channels
    markers = [False]*self.digital_channels

    waiting_element = Pulse_Block_Element(wait_time_bins, self.analog_channels,
                                          self.digital_channels, 0,
                                          pulse_function, markers,
                                          analog_params)

    # -------------------

    # -- seq trigger element --

    analog_params = [{}]*self.analog_channels
    pulse_function = ['Idle']*self.analog_channels
    markers = [False]*self.digital_channels

    if seq_channel > 0 and seq_channel <= self.digital_channels:
        markers[seq_channel-1] = True
    elif seq_channel < 0 and seq_channel >= -self.analog_channels:
        pulse_function[abs(seq_channel)-1] = 'DC'
        analog_params[abs(seq_channel)-1] = {'amplitude1': channel_amp_V}


    seqtrig_element = Pulse_Block_Element(100, self.analog_channels,
                                          self.digital_channels, 0,
                                          pulse_function,
                                          markers,
                                          analog_params)

    # -------------------

    element_list = [mw_element, laser_element, aomdelay_element, waiting_element]

    #FIXME: that has to be fixed in the generation
    laser_channel_index = abs(laser_channel)-1

    rabi_block = Pulse_Block(name, element_list, laser_channel_index)
    # save block
    self.save_block(name, rabi_block)
    # set current block
    self.current_block = rabi_block

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

    # save ensemble
    self.save_ensemble(name, block_ensemble)
    # set current block ensemble
    self.current_ensemble = block_ensemble
    # update ensemble list
    self.refresh_ensemble_list()
    return

def generate_pulsedodmr(self, name='PulsedODMR', mw_time_ns=1000,
                        mw_freq_MHz=100.0,  mw_amp_V=1.0, mw_channel=-1,
                        laser_time_ns=3000, laser_channel=1, laser_amp_V=1,
                        wait_time_ns=1500):
    """ Converter function to use ns input instead of bins. """

    mw_time_bins = int(self.get_sample_rate()/1e9 * mw_time_ns)
    laser_time_bins = int(self.get_sample_rate()/1e9 * laser_time_ns)
    wait_time_bins = int(self.get_sample_rate()/1e9 * wait_time_ns)

    self.generate_pulsedodmr_bins(name, mw_time_bins, mw_freq_MHz, mw_amp_V,
                                  mw_channel, laser_time_bins, laser_channel,
                                  laser_amp_V, wait_time_bins)


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
        analog_params[abs(mw_channel)-1] = {'amplitude1': mw_amp_V, 'frequency1': mw_freq, 'phase1': 0.0}
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


def generate_ramsey(self, name='Ramsey', tau_start_ns=50, tau_step_ns=50,
                  number_of_taus=50, mw_freq_MHz=100.0, mw_rabi_period_ns=200,
                  mw_amp_V=1.0,
                  mw_channel=-1, laser_time_ns=3000, laser_channel=1,
                  channel_amp_V=1, aom_delay_ns=500, open_count_channel=2,
                  seq_channel=3, wait_time_ns=1500):
    """ Converter function to use ns input instead of bins. """

    tau_start_bins = int(self.get_sample_rate()/1e9 * tau_start_ns)
    tau_step_bins = int(self.get_sample_rate()/1e9 * tau_step_ns)
    mw_rabi_period_bins = int(self.get_sample_rate()/1e9 * mw_rabi_period_ns)
    laser_time_bins = int(self.get_sample_rate()/1e9 * laser_time_ns)
    aom_delay_bins = int(self.get_sample_rate()/1e9 * aom_delay_ns)
    wait_time_bins = int(self.get_sample_rate()/1e9 * wait_time_ns)

    self.generate_ramsey_bins(name, tau_start_bins, tau_step_bins,
                  number_of_taus, mw_freq_MHz, mw_rabi_period_bins, mw_amp_V,
                  mw_channel, laser_time_bins, laser_channel, channel_amp_V,
                  aom_delay_bins, open_count_channel, seq_channel,
                  wait_time_bins)

def generate_ramsey_bins(self, name='Ramsey', tau_start_bins=50, tau_step_bins=50,
                  number_of_taus=50, mw_freq_MHz=100.0, mw_rabi_period_bins=200,
                  mw_amp_V=1.0, mw_channel=-1, laser_time_bins=3000,
                  laser_channel=1, channel_amp_V=1, aom_delay_bins=500,
                  open_count_channel=2, seq_channel=3, wait_time_bins=500):

    if laser_channel == mw_channel:
        self.logMsg('Laser and Microwave channel cannot be the same. Change '
                    'that!', msgType='error')
        return

    # --- mw element ----

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
        analog_params[abs(mw_channel)-1] = {'amplitude1': mw_amp_V, 'frequency1': mw_freq, 'phase1': 0.0}
    else:
        self.logMsg('Value of {0} is not a proper mw_channel. Digital laser '
                    'channels are positive values 1=d_ch1, 2=d_ch2, '
                    '... and analog channel numbers are chosen by a negative '
                    'number -1=a_ch1, -2=a_ch2, ... where number 0 is an '
                    'invalid input. Make your choice!', msgType='error')
        return

    pi_2_time_bins = int(mw_rabi_period_bins/4)

    mw_element = Pulse_Block_Element(init_length_bins=pi_2_time_bins,
                                     analog_channels=self.analog_channels,
                                     digital_channels=self.digital_channels,
                                     increment_bins=0,
                                     pulse_function=pulse_function,
                                     marker_active=markers,
                                     parameters=analog_params,
                                     use_as_tick=False)

    # -------------------

    # -- Ramsey interaction time element ---

    analog_params = [{}]*self.analog_channels
    markers = [False]*self.digital_channels
    pulse_function = ['Idle']*self.analog_channels

    ramsey_int_time_element = Pulse_Block_Element(tau_start_bins,
                                                  self.analog_channels,
                                                  self.digital_channels,
                                                  tau_step_bins,
                                                  pulse_function, markers,
                                                  analog_params, True)

    # -------------------

    # -- laser element --

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
    # -------------------

    # -- aom delay element --

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

    # -------------------

    # -- wait time element --

    analog_params = [{}]*self.analog_channels
    pulse_function = ['Idle']*self.analog_channels
    markers = [False]*self.digital_channels

    waiting_element = Pulse_Block_Element(wait_time_bins, self.analog_channels,
                                          self.digital_channels, 0,
                                          pulse_function, markers,
                                          analog_params)

    # -------------------

    # -- seq trigger element --

    analog_params = [{}]*self.analog_channels
    pulse_function = ['Idle']*self.analog_channels
    markers = [False]*self.digital_channels

    if seq_channel > 0 and seq_channel <= self.digital_channels:
        markers[seq_channel-1] = True
    elif seq_channel < 0 and seq_channel >= -self.analog_channels:
        pulse_function[abs(seq_channel)-1] = 'DC'
        analog_params[abs(seq_channel)-1] = {'amplitude1': channel_amp_V}


    seqtrig_element = Pulse_Block_Element(100, self.analog_channels,
                                          self.digital_channels, 0,
                                          pulse_function,
                                          markers,
                                          analog_params)

    # -------------------

    element_list = [mw_element, ramsey_int_time_element, mw_element,
                    laser_element, aomdelay_element, waiting_element]

    #FIXME: that has to be fixed in the generation
    laser_channel_index = abs(laser_channel)-1

    ramsey_block = Pulse_Block(name, element_list, laser_channel_index)
    # save block
    self.save_block(name, ramsey_block)
    # set current block
    self.current_block = ramsey_block

    # remember number_of_taus=0 also counts as first round
    block_list = [(ramsey_block, number_of_taus-1)]
    if seq_channel != 0:
        seq_block = Pulse_Block('seq_trigger', [seqtrig_element], laser_channel_index)
        block_list.append((seq_block, 0))
        # save block
        self.save_block('seq_trigger', seq_block)

    # create ensemble out of the block(s)
    block_ensemble = Pulse_Block_Ensemble(name, block_list, laser_channel_index,
                                          rotating_frame=True)
    # save ensemble
    self.save_ensemble(name, block_ensemble)
    # set current block ensemble
    self.current_ensemble = block_ensemble
    # update ensemble list
    self.refresh_ensemble_list()
    return

def generate_hahn(self, name='Hahn Echo', tau_start_ns=500,
                  tau_step_ns=500, number_of_taus=50, mw_freq_MHz=2700.0,
                  mw_rabi_period_ns=200, mw_amp_V=1.0, mw_channel=-1,
                  laser_time_ns=3000, laser_channel=1, channel_amp_V=1,
                  aom_delay_ns=500, open_count_channel=2, seq_channel=3,
                  wait_time_ns=500):
    """ Converter function to use ns input instead of bins. """

    tau_start_bins = int(self.get_sample_rate()/1e9 * tau_start_ns)
    tau_step_bins = int(self.get_sample_rate()/1e9 * tau_step_ns)
    mw_rabi_period_bins = int(self.get_sample_rate()/1e9 * mw_rabi_period_ns)
    laser_time_bins = int(self.get_sample_rate()/1e9 * laser_time_ns)
    aom_delay_bins = int(self.get_sample_rate()/1e9 * aom_delay_ns)
    wait_time_bins = int(self.get_sample_rate()/1e9 * wait_time_ns)

    self.generate_hahn_bins(name, tau_start_bins, tau_step_bins, number_of_taus,
                            mw_freq_MHz, mw_rabi_period_bins, mw_amp_V,
                            mw_channel, laser_time_bins, laser_channel,
                            channel_amp_V, aom_delay_bins, open_count_channel,
                            seq_channel, wait_time_bins)

def generate_hahn_bins(self, name='Hahn Echo', tau_start_bins=500,
                       tau_step_bins=500, number_of_taus=50, mw_freq_MHz=2700.0,
                       mw_rabi_period_bins=200, mw_amp_V=1.0, mw_channel=-1,
                       laser_time_bins=3000, laser_channel=1, channel_amp_V=1,
                       aom_delay_bins=500, open_count_channel=2, seq_channel=3,
                       wait_time_bins=500):

    if laser_channel == mw_channel:
        self.logMsg('Laser and Microwave channel cannot be the same. Change '
                    'that!', msgType='error')
        return

    # --- mw element pi/2 ----

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
        analog_params[abs(mw_channel)-1] = {'amplitude1': mw_amp_V, 'frequency1': mw_freq, 'phase1': 0.0}
    else:
        self.logMsg('Value of {0} is not a proper mw_channel. Digital laser '
                    'channels are positive values 1=d_ch1, 2=d_ch2, '
                    '... and analog channel numbers are chosen by a negative '
                    'number -1=a_ch1, -2=a_ch2, ... where number 0 is an '
                    'invalid input. Make your choice!', msgType='error')
        return

    pi_2_time_bins = int(mw_rabi_period_bins/4)

    mw_element_pi2 = Pulse_Block_Element(init_length_bins=pi_2_time_bins,
                                     analog_channels=self.analog_channels,
                                     digital_channels=self.digital_channels,
                                     increment_bins=0,
                                     pulse_function=pulse_function,
                                     marker_active=markers,
                                     parameters=analog_params,
                                     use_as_tick=False)

    # -------------------

    # --- mw element pi ----

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
        analog_params[abs(mw_channel)-1] = {'amplitude1': mw_amp_V, 'frequency1': mw_freq, 'phase1': 0.0}
    else:
        self.logMsg('Value of {0} is not a proper mw_channel. Digital laser '
                    'channels are positive values 1=d_ch1, 2=d_ch2, '
                    '... and analog channel numbers are chosen by a negative '
                    'number -1=a_ch1, -2=a_ch2, ... where number 0 is an '
                    'invalid input. Make your choice!', msgType='error')
        return

    pi_time_bins = int(mw_rabi_period_bins/2)

    mw_element_pi = Pulse_Block_Element(init_length_bins=pi_time_bins,
                                     analog_channels=self.analog_channels,
                                     digital_channels=self.digital_channels,
                                     increment_bins=0,
                                     pulse_function=pulse_function,
                                     marker_active=markers,
                                     parameters=analog_params,
                                     use_as_tick=False)

    # -------------------

    # -- hahn interaction time element ---

    analog_params = [{}]*self.analog_channels
    markers = [False]*self.digital_channels
    pulse_function = ['Idle']*self.analog_channels

    hahn_int_time_element = Pulse_Block_Element(tau_start_bins,
                                                self.analog_channels,
                                                self.digital_channels,
                                                tau_step_bins,
                                                pulse_function, markers,
                                                analog_params, True)
    # -------------------

    # -- laser element --

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
    # -------------------

    # -- aom delay element --

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

    # -------------------

    # -- wait time element --

    analog_params = [{}]*self.analog_channels
    pulse_function = ['Idle']*self.analog_channels
    markers = [False]*self.digital_channels

    waiting_element = Pulse_Block_Element(wait_time_bins, self.analog_channels,
                                          self.digital_channels, 0,
                                          pulse_function, markers,
                                          analog_params)

    # -------------------

    # -- seq trigger element --

    analog_params = [{}]*self.analog_channels
    pulse_function = ['Idle']*self.analog_channels
    markers = [False]*self.digital_channels

    if seq_channel > 0 and seq_channel <= self.digital_channels:
        markers[seq_channel-1] = True
    elif seq_channel < 0 and seq_channel >= -self.analog_channels:
        pulse_function[abs(seq_channel)-1] = 'DC'
        analog_params[abs(seq_channel)-1] = {'amplitude1': channel_amp_V}


    seqtrig_element = Pulse_Block_Element(100, self.analog_channels,
                                          self.digital_channels, 0,
                                          pulse_function,
                                          markers,
                                          analog_params)

    # -------------------

    element_list = [mw_element_pi2, hahn_int_time_element, mw_element_pi,
                    hahn_int_time_element, mw_element_pi2, laser_element,
                    aomdelay_element, waiting_element]

    #FIXME: that has to be fixed in the generation
    laser_channel_index = abs(laser_channel)-1

    hahn_block = Pulse_Block(name, element_list, laser_channel_index)
    # save block
    self.save_block(name, hahn_block)
    # set current block
    self.current_block = hahn_block

    # remember number_of_taus=0 also counts as first round
    block_list = [(hahn_block, number_of_taus-1)]
    if seq_channel != 0:
        seq_block = Pulse_Block('seq_trigger', [seqtrig_element], laser_channel_index)
        block_list.append((seq_block, 0))
        # save block
        self.save_block('seq_trigger', seq_block)

    # create ensemble out of the block(s)
    block_ensemble = Pulse_Block_Ensemble(name, block_list, laser_channel_index,
                                          rotating_frame=True)
    # save ensemble
    self.save_ensemble(name, block_ensemble)
    # set current block ensemble
    self.current_ensemble = block_ensemble
    # update ensemble list
    self.refresh_ensemble_list()


def generate_xy8(self, name='xy8', tau_start_ns=2000, tau_step_ns=20,
                 number_of_taus=10, xy8_number=8, mw_freq_MHz=100.0,
                 mw_rabi_period_ns=100, mw_amp_V=1.0, mw_channel=-1,
                 laser_time_ns=3000, laser_channel=1, channel_amp_V=1,
                 aom_delay_ns=500, open_count_channel=2, seq_channel=3,
                 wait_time_ns=1500):
    """ Converter function to use ns input instead of bins. """

    tau_start_bins = int(self.get_sample_rate()/1e9 * tau_start_ns)
    tau_step_bins = int(self.get_sample_rate()/1e9 * tau_step_ns)
    mw_rabi_period_bins = int(self.get_sample_rate()/1e9 * mw_rabi_period_ns)
    laser_time_bins = int(self.get_sample_rate()/1e9 * laser_time_ns)
    aom_delay_bins = int(self.get_sample_rate()/1e9 * aom_delay_ns)
    wait_time_bins = int(self.get_sample_rate()/1e9 * wait_time_ns)

    self.generate_xy8_bins(name, tau_start_bins, tau_step_bins, number_of_taus,
                           xy8_number, mw_freq_MHz, mw_rabi_period_bins,
                           mw_amp_V, mw_channel, laser_time_bins,
                           laser_channel, channel_amp_V, aom_delay_bins,
                           open_count_channel, seq_channel, wait_time_bins)

def generate_xy8_bins(self, name='xy8', tau_start_bins=50, tau_step_bins=50,
                      number_of_taus=10, xy8_number=8, mw_freq_MHz=100.0,
                      mw_rabi_period_bins=200,
                      mw_amp_V=1.0, mw_channel=-1, laser_time_bins=3000,
                      laser_channel=1, channel_amp_V=1, aom_delay_bins=500,
                      open_count_channel=2, seq_channel=3, wait_time_bins=500):

    if laser_channel == mw_channel:
        self.logMsg('Laser and Microwave channel cannot be the same. Change '
                    'that!', msgType='error')
        return

    # --- mw element pi/2 ----

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
        analog_params[abs(mw_channel)-1] = {'amplitude1': mw_amp_V, 'frequency1': mw_freq, 'phase1': 0.0}
    else:
        self.logMsg('Value of {0} is not a proper mw_channel. Digital laser '
                    'channels are positive values 1=d_ch1, 2=d_ch2, '
                    '... and analog channel numbers are chosen by a negative '
                    'number -1=a_ch1, -2=a_ch2, ... where number 0 is an '
                    'invalid input. Make your choice!', msgType='error')
        return

    pi_2_time_bins = int(mw_rabi_period_bins/4)

    mw_elem_pi2 = Pulse_Block_Element(init_length_bins=pi_2_time_bins,
                                     analog_channels=self.analog_channels,
                                     digital_channels=self.digital_channels,
                                     increment_bins=0,
                                     pulse_function=pulse_function,
                                     marker_active=markers,
                                     parameters=analog_params,
                                     use_as_tick=False)

    # -------------------

    # --- mw element pi x ----

    pi_time_bins = int(mw_rabi_period_bins/2)

    mw_elem_pi_x = Pulse_Block_Element(init_length_bins=pi_time_bins,
                                     analog_channels=self.analog_channels,
                                     digital_channels=self.digital_channels,
                                     increment_bins=0,
                                     pulse_function=pulse_function,
                                     marker_active=markers,
                                     parameters=analog_params,
                                     use_as_tick=False)

    # -------------------

    # --- mw element pi x,  marked as tick ----

    mw_elem_pi_x_tick = Pulse_Block_Element(init_length_bins=pi_time_bins,
                                     analog_channels=self.analog_channels,
                                     digital_channels=self.digital_channels,
                                     increment_bins=0,
                                     pulse_function=pulse_function,
                                     marker_active=markers,
                                     parameters=analog_params,
                                     use_as_tick=True)

    # -------------------

    # --- mw element pi y ----

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
        analog_params[abs(mw_channel)-1] = {'amplitude1': mw_amp_V, 'frequency1': mw_freq, 'phase1': 90.0}
    else:
        self.logMsg('Value of {0} is not a proper mw_channel. Digital laser '
                    'channels are positive values 1=d_ch1, 2=d_ch2, '
                    '... and analog channel numbers are chosen by a negative '
                    'number -1=a_ch1, -2=a_ch2, ... where number 0 is an '
                    'invalid input. Make your choice!', msgType='error')
        return

    pi_time_bins = int(mw_rabi_period_bins/2)

    mw_elem_pi_y = Pulse_Block_Element(init_length_bins=pi_time_bins,
                                     analog_channels=self.analog_channels,
                                     digital_channels=self.digital_channels,
                                     increment_bins=0,
                                     pulse_function=pulse_function,
                                     marker_active=markers,
                                     parameters=analog_params,
                                     use_as_tick=False)

    # -------------------

    # -- xy8 half interaction time element ---

    analog_params = [{}]*self.analog_channels
    markers = [False]*self.digital_channels
    pulse_function = ['Idle']*self.analog_channels

    tau_2 = tau_start_bins/2
    tau_2_inc = tau_step_bins/2

    xy8_half_int_time_element = Pulse_Block_Element(tau_2,
                                                self.analog_channels,
                                                self.digital_channels,
                                                tau_2_inc,
                                                pulse_function, markers,
                                                analog_params, False)
    # -------------------


    # -- xy8 interaction time element, marked as tick ---

    analog_params = [{}]*self.analog_channels
    markers = [False]*self.digital_channels
    pulse_function = ['Idle']*self.analog_channels

    xy8_int_time_elem_tick = Pulse_Block_Element(tau_start_bins,
                                                self.analog_channels,
                                                self.digital_channels,
                                                tau_step_bins,
                                                pulse_function, markers,
                                                analog_params, True)
    # -------------------

    # -- xy8 interaction time element, not marked as tick ---

    analog_params = [{}]*self.analog_channels
    markers = [False]*self.digital_channels
    pulse_function = ['Idle']*self.analog_channels

    xy8_int_time_elem = Pulse_Block_Element(tau_start_bins,
                                                self.analog_channels,
                                                self.digital_channels,
                                                tau_step_bins,
                                                pulse_function, markers,
                                                analog_params, False)
    # -------------------


    # -- laser element --

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

    laser_elem = Pulse_Block_Element(laser_time_bins, self.analog_channels,
                                        self.digital_channels, 0,
                                        pulse_function, markers,
                                        analog_params)
    # -------------------

    # -- aom delay element --

    analog_params = [{}]*self.analog_channels
    pulse_function = ['Idle']*self.analog_channels
    markers = [False]*self.digital_channels

    if open_count_channel > 0 and open_count_channel <= self.digital_channels:
        markers[open_count_channel-1] = True
    elif open_count_channel < 0 and open_count_channel >= -self.analog_channels:
        pulse_function[abs(open_count_channel)-1] = 'DC'
        analog_params[abs(open_count_channel)-1] = {'amplitude1': channel_amp_V}

    aomdelay_elem = Pulse_Block_Element(aom_delay_bins, self.analog_channels,
                                           self.digital_channels, 0,
                                           pulse_function, markers,
                                           analog_params)

    # -------------------

    # -- wait time element --

    analog_params = [{}]*self.analog_channels
    pulse_function = ['Idle']*self.analog_channels
    markers = [False]*self.digital_channels

    waiting_elem = Pulse_Block_Element(wait_time_bins, self.analog_channels,
                                          self.digital_channels, 0,
                                          pulse_function, markers,
                                          analog_params)

    # -------------------

    # -- seq trigger element --

    analog_params = [{}]*self.analog_channels
    pulse_function = ['Idle']*self.analog_channels
    markers = [False]*self.digital_channels

    if seq_channel > 0 and seq_channel <= self.digital_channels:
        markers[seq_channel-1] = True
    elif seq_channel < 0 and seq_channel >= -self.analog_channels:
        pulse_function[abs(seq_channel)-1] = 'DC'
        analog_params[abs(seq_channel)-1] = {'amplitude1': channel_amp_V}


    seqtrig_elem = Pulse_Block_Element(100, self.analog_channels,
                                          self.digital_channels, 0,
                                          pulse_function,
                                          markers,
                                          analog_params)

    # -------------------

    elem_list = [mw_elem_pi2, xy8_half_int_time_element,
                            mw_elem_pi_x_tick, xy8_int_time_elem_tick,
                            mw_elem_pi_y, xy8_int_time_elem, mw_elem_pi_x,
                            xy8_int_time_elem, mw_elem_pi_y, xy8_int_time_elem,
                            mw_elem_pi_y, xy8_int_time_elem, mw_elem_pi_x,
                            xy8_int_time_elem, mw_elem_pi_y, xy8_int_time_elem,
                            mw_elem_pi_x, xy8_half_int_time_element]


    rep_elem_list = [xy8_half_int_time_element, mw_elem_pi_x, xy8_int_time_elem,
                     mw_elem_pi_y, xy8_int_time_elem, mw_elem_pi_x,
                     xy8_int_time_elem, mw_elem_pi_y, xy8_int_time_elem,
                     mw_elem_pi_y, xy8_int_time_elem, mw_elem_pi_x,
                     xy8_int_time_elem, mw_elem_pi_y, xy8_int_time_elem,
                     mw_elem_pi_x, xy8_half_int_time_element]

    last_elem_list = [xy8_half_int_time_element, laser_elem, aomdelay_elem,
                      waiting_elem]

    # -1 because the first elem list is already created:
    for num_xy8 in range(xy8_number-1):
        elem_list.extend(rep_elem_list)

    elem_list.extend(last_elem_list)

    #FIXME: that has to be fixed in the generation
    laser_channel_index = abs(laser_channel)-1

    xy8_block = Pulse_Block(name, elem_list, laser_channel_index)
    # save block
    self.save_block(name, xy8_block)
    # set current block
    self.current_block = xy8_block

    # remember number_of_taus=0 also counts as first round
    block_list = [(xy8_block, number_of_taus-1)]
    if seq_channel != 0:
        seq_block = Pulse_Block('seq_trigger', [seqtrig_elem], laser_channel_index)
        block_list.append((seq_block, 0))
        # save block
        self.save_block('seq_trigger', seq_block)

    # create ensemble out of the block(s)
    block_ensemble = Pulse_Block_Ensemble(name, block_list, laser_channel_index,
                                          rotating_frame=True)
    # save ensemble
    self.save_ensemble(name, block_ensemble)
    # set current block ensemble
    self.current_ensemble = block_ensemble
    # update ensemble list
    self.refresh_ensemble_list()
