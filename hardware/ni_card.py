# -*- coding: utf-8 -*-
"""
This file contains the QuDi Hardware module NICard class.

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

Copyright (C) 2015 Kay Jahnke kay.jahnke@alumni.uni-ulm.de
Copyright (C) 2015 Alexander Stark alexander.stark@uni-ulm.de
"""

from core.base import Base
from hardware.slow_counter_interface import SlowCounterInterface
from hardware.confocal_scanner_interface import ConfocalScannerInterface
from hardware.odmr_counter_interface import ODMRCounterInterface

import PyDAQmx as daq
import numpy as np
import re

class NICard(Base,SlowCounterInterface,ConfocalScannerInterface,ODMRCounterInterface):
    """unstable: Kay Jahnke, Alexander Stark
	
	A National Instruments device that can count and control microvave generators.

    Basic procedure how the NI card is configurated:
      * At first you have to define a channel, where the APD clicks will be
        received. That can be any PFI input, which is specified to record TTL
        pulses.
      * Then two counter channels have to be configured.
      * One counter channel serves as a timing device, i.e. basically a clock
        which runs at a certain given frequency.
      * The second counter channel will be used as a gated counting device,
        which will, dependent on the clock, count within the clock interval. The faster
        the clock channel is configured, the smaller is the gated counting 
        interval and the less counts per clock periode you will count.
    
    Therefore the whole issue is to establish a time based gated-counting 
    channel.
    
    Text Based NI-DAQmx Data Acquisition Examples:
    http://www.ni.com/example/6999/en/#ANSIC
    
    Explanation of the termology, which is used in the NI Card and useful to
    know in connection with our implementation:
    
    Hardware-Timed Counter Tasks:
        Use hardware-timed counter input operations to drive a control loop. A
        really good explanation can be found in:
        
        http://zone.ni.com/reference/en-XX/help/370466V-01/mxcncpts/controlappcase4/
    
    Terminals:  
        A terminal is a named location where a signal is either generated 
        (output or produced) or acquired (input or consumed). A terminal that 
        can output only one signal is often named after that signal. A terminal 
        with an input that can be used only for one signal is often named after 
        the clock or trigger that the signal is used for. Terminals that are 
        used for many signals have generic names such as RTSI, PXITrig, or PFI.
        
        http://zone.ni.com/reference/en-XX/help/370466W-01/mxcncpts/terminal/
        http://zone.ni.com/reference/en-XX/help/370466V-01/mxcncpts/termnames/
    
    Ctr0Out, Ctr1Out, Ctr2Out, Ctr3Out:
        Terminals at the I/O connector where the output of counter 0, 
        counter 1, counter 2, or counter 3 can be emitted. You also can use 
        Ctr0Out as a terminal for driving an external signal onto the RTSI bus.
        
    Ctr0Gate, Ctr1Gate, Ctr2Gate, Ctr3Gate:
        Terminals within a device whose purpose depends on the application. 
        Refer to Counter Parts in NI-DAQmx for more information on how the gate 
        terminal is used in various applications. 
        
    Ctr0Source, Ctr1Source, Ctr2Source, Ctr3Source:
        Terminals within a device whose purpose depends on the application. 
        Refer to Counter Parts in NI-DAQmx for more information on how the 
        source terminal is used in various applications. 
        
    Ctr0InternalOutput, Ctr1InternalOutput, Ctr2InternalOutput, 
    Ctr3InternalOutput:
        Terminals within a device where you can choose the pulsed or toggled 
        output of the counters. Refer to Counter Parts in NI-DAQmx (or MAX) 
        for more information on internal output terminals.
        
    Device limitations:
        Keep in mind that ONLY the X-series of the NI cards is capable of doing
        a Counter Output Pulse Frequency Train with finite numbers of samples
        by using ONE internal device channel clock (that is the function 
        DAQmxCreateCOPulseChanFreq or CO Pulse Freq in Labview)! All other card
        series have to use two counters to generate that!
        Check out the description of NI which tells you 'How Many Counters Does
        Each Type of Counter Input or Output Task Take':
        
        http://digital.ni.com/public.nsf/allkb/9D1780F448D10F4686257590007B15A8        
        
        This code was tested with NI 6323 and NI 6229, where the first one is
        an X-series device and the latter one is a Low-Cost M Series device.
        With the NI 6229 it is not possible at all to perform the scanning 
        task unless you have two of that cards. The limitation came from a lack
        of internal counters.
        The NI 6323 was taken as a basis for this hardware module and thus all
        the function are working on that card.
    """
    
    _modtype = 'NICard'
    _modclass = 'hardware'

    # connectors
    _out = {'counter': 'SlowCounterInterface',
            'confocalscanner': 'ConfocalScannerInterface',
            'odmrcounter': 'ODMRCounterInterface'
            }
    
    def __init__(self, manager, name, config, **kwargs):
        # declare actions for state transitions
        c_dict = {'onactivate': self.activation}
        Base.__init__(self, manager, name, config, c_dict)
        
        #FIXME: What are the variables doing (i.e. RWTimeout)?            
        self._max_counts = 3e7  # used as a default for expected maximum counts
        #FIXME: Read-Write timeout
        self._RWTimeout = 5
        self._counter_daq_task = None
        self._clock_daq_task = None
        self._scanner_clock_daq_task = None
        self._scanner_ao_task = None
        self._scanner_counter_daq_task = None
        self._line_length = None
        self._odmr_length = None
        self._gated_counter_daq_task = None
        
        # FIXME: Here you assign a value to some variables. For _sample_number, 
        # _clock_frequency, _scanner_clock_frequency you are doing this later.
        # Wouldn't it be more convenient to also put the default values for 
        # _sample_number, _clock_frequency, _scanner_clock_frequency here. 
        # Then it is also a bit simpler to change...
        self._voltage_range = [-10., 10.]        
        self._position_range=[[0., 100.], [0., 100.], [0., 100.], [0., 100.]]        
        self._current_position = [0., 0., 0., 0.]
        
        # handle all the parameters given by the config
        #FIXME: Suggestion: and  partially set the parameters to default values
        #if not given by the config
        if 'scanner_ao_channels' in config.keys():
            self._scanner_ao_channels=config['scanner_ao_channels']
        else:
            self.logMsg('No scanner_ao_channels found in the configuration!',
                        msgType='error')
            
        if 'odmr_trigger_channel' in config.keys():
            self._odmr_trigger_channel=config['odmr_trigger_channel']
        else:
            self.logMsg('No odmr_trigger_channel found in configuration!',
                        msgType='error')
            
        if 'clock_channel' in config.keys():
            self._clock_channel=config['clock_channel']
        else:
            self.logMsg('No clock_channel configured.', msgType='error')
            
        if 'counter_channel' in config.keys():
            self._counter_channel=config['counter_channel']
        else:
            self.logMsg('No counter_channel configured.', msgType='error')
            
        if 'scanner_clock_channel' in config.keys():
            self._scanner_clock_channel=config['scanner_clock_channel']
        else:
            self.logMsg('No scanner_clock_channel configured.', msgType='error')
            
        if 'scanner_counter_channel' in config.keys():
            self._scanner_counter_channel=config['scanner_counter_channel']
        else:
            self.logMsg('No scanner_counter_channel configured.', msgType='error')
            
        if 'photon_source' in config.keys():
            self._photon_source=config['photon_source']
        else:
            self.logMsg('No photon_source configured.', msgType='error')

        if 'clock_frequency' in config.keys():
            self._clock_frequency=config['clock_frequency']
        else:
            self._clock_frequency=100
            self.logMsg('No clock_frequency configured taking 100 Hz instead.',
                        msgType='warning')

        if 'gate_in_channel' in config.keys():
            self._gate_in_channel = config['gate_in_channel']
        else:
            self.logMsg('No gate_in_channel configured.', msgType='error')

        if 'counting_edge_rising' in config.keys():
            if config['counting_edge_rising']:
                self._counting_edge = daq.DAQmx_Val_Rising
            else:
                self._counting_edge = daq.DAQmx_Val_Falling
        else:
            self.logMsg('No counting_edge_rising configured.', msgType='error')

        if 'scanner_clock_frequency' in config.keys():
            self._scanner_clock_frequency=config['scanner_clock_frequency']
        else:
            self._scanner_clock_frequency=100
            self.logMsg('No scanner_clock_frequency configured taking '
                        '100 Hz instead.', msgType='warning')
            
        if 'samples_number' in config.keys():
            self._samples_number=config['samples_number']
        else:
            self._samples_number=10
            self.logMsg('No samples_number configured taking 10 instead.',
                        msgType='warning')
            
        if 'x_range' in config.keys():
            if float(config['x_range'][0]) < float(config['x_range'][1]):
                self._position_range[0] = [float(config['x_range'][0]),
                                           float(config['x_range'][1])]
            else:
                self.logMsg('Configuration ({}) of x_range incorrect, taking '
                            '[0,100] instead.'.format(config['x_range']),
                            msgType='warning')                
        else:
            self.logMsg('No x_range configured taking [0,100] instead.',
                        msgType='warning')
            
        if 'y_range' in config.keys():
            if float(config['y_range'][0]) < float(config['y_range'][1]):
                self._position_range[1] = [float(config['y_range'][0]),
                                           float(config['y_range'][1])]
            else:
                self.logMsg('Configuration ({}) of y_range incorrect, taking '
                            '[0,100] instead.'.format(config['y_range']),
                            msgType='warning')                
        else:
            self.logMsg('No y_range configured taking [0,100] instead.',
                        msgType='warning')
            
        if 'z_range' in config.keys():
            if float(config['z_range'][0]) < float(config['z_range'][1]):
                self._position_range[2] = [float(config['z_range'][0]),
                                           float(config['z_range'][1])]
            else:
                self.logMsg('Configuration ({}) of z_range incorrect, taking '
                            '[0,100] instead.'.format(config['z_range']),
                            msgType='warning')                
        else:
            self.logMsg('No z_range configured taking [0,100] instead.',
                        msgType='warning')
            
        if 'a_range' in config.keys():
            if float(config['a_range'][0]) < float(config['a_range'][1]):
                self._position_range[3] = [float(config['a_range'][0]),
                                           float(config['a_range'][1])]
            else:
                self.logMsg('Configuration ({}) of a_range incorrect, taking '
                            '[0,100] instead.'.format(config['a_range']),
                            msgType='warning')                
        else:
            self.logMsg('No a_range configured taking [0,100] instead.',
                        msgType='warning')
            
        if 'voltage_range' in config.keys():
            if float(config['voltage_range'][0]) < float(config['voltage_range'][1]):
                self._voltage_range = [float(config['voltage_range'][0]),
                                       float(config['voltage_range'][1])]
            else:
                self.logMsg('Configuration ({}) of voltage_range incorrect, '
                            'taking [-10,10] instead.'.format(config['voltage_range']),
                            msgType='warning')                
        else:
            self.logMsg('No voltage_range configured taking [-10,10] instead.',
                        msgType='warning')
         
         #FIXME: Noch rausnehmen?
#        self.testing()
        
    def activation(self, e=None): 
        """ Starts up the NI Card at activation.
        
        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event
                         the state before the event happens and the destination
                         of the state which should be reached after the event
                         has happen.
                
        @return int: error code (0:OK, -1:error)
        """
        
        #FIXME: Where is the error code returned?
        
        # Analoque output is always needed and it does not interfere with the 
        # rest, so start it always and leave it running
        self._start_analoque_output()

    def deactivation(self, e=None):
        """ Shut down the NI card.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event
                         the state before the event happens and the destination
                         of the state which should be reached after the event
                         has happened.
        """
        self.reset_hardware()
        
    def reset_hardware(self):
        """ Resets the NI hardware, so the connection is lost and other 
            programs can access it.
        
        @return int: error code (0:OK, -1:error)
        """
        match = re.match('^.?(?P<device>Dev\d+).*',self._clock_channel)
        if match:
            device = match.group('device')
            self.logMsg('NI Device "{}" will be reset.'.format(device), 
                        msgType='warning')
            daq.DAQmxResetDevice(device)
            return 0
        else:
            self.logMsg('Did not find device name '
                        'in {}.'.format(self._clock_channel), vmsgType='error')
            return -1
              
    # =========================== Counter =====================================
        
    def set_up_clock(self, clock_frequency = None, clock_channel = None,
                     scanner=False, idle = False):
        """ Configures the hardware clock of the NiDAQ card to give the timing. 
        
        @param float clock_frequency: if defined, this sets the frequency of 
                                      the clock in Hz
        @param string clock_channel: if defined, this is the physical channel
                                     of the clock within the NI card.
        @param bool scanner: if set to True method will set up a clock function
                             for the scanner, otherwise a clock function for a 
                             counter will be set.
        
        @return int: error code (0:OK, -1:error)
        """ 
        
        if not scanner and self._clock_daq_task is not None:            
            self.logMsg('Another counter clock is already running, close this '
                        'one first.', msgType='error')
            return -1
            
        
        if scanner and self._scanner_clock_daq_task is not None:            
            self.logMsg('Another scanner clock is already running, close this '
                        'one first.', msgType='error')
            return -1
        
        # Create handle for task, this task will generate pulse signal for 
        # photon counting
        my_clock_daq_task = daq.TaskHandle()
        
        # assing the clock frequency, if given
        if clock_frequency is not None:
            if not scanner:
                self._clock_frequency = float(clock_frequency)
            else:
                self._scanner_clock_frequency = float(clock_frequency)
                
        # use the correct clock in this method
        if scanner:
            my_clock_frequency = self._scanner_clock_frequency*2.
        else:
            my_clock_frequency = self._clock_frequency
            
        # assing the clock channel, if given
        if clock_channel is not None:
            if not scanner:
                self._clock_channel = clock_channel
            else:
                self._scanner_clock_channel = clock_channel
        
        # use the correct clock channel in this method
        if scanner:
            my_clock_channel = self._scanner_clock_channel
        else:
            my_clock_channel = self._clock_channel
            
        # check whether only one clock pair is available, since some NI cards
        # only one clock channel pair.
        if self._scanner_clock_channel == self._clock_channel:
            if not ((self._clock_daq_task is None) and (self._scanner_clock_daq_task is None)):
                self.logMsg('Only one clock channel is available!\n'
                            'Another clock is already running, close this one '
                            'first in order to use it for your purpose!',
                            msgType='error')
                return -1
        
        # Adjust the idle state if neseccary
        if idle:
            my_idle = daq.DAQmx_Val_High
        else:
            my_idle = daq.DAQmx_Val_Low
        
        # create task for clock
        daq.DAQmxCreateTask('', daq.byref(my_clock_daq_task))
        
        # create a digital clock channel with specific clock frequency:
        daq.DAQmxCreateCOPulseChanFreq( #
                my_clock_daq_task,      # The task to which to add the channels
                my_clock_channel,       # which channel is used?
                'Clock Producer',       # Name to assign to task (NIDAQ uses by
                                        # default the physical channel name as 
                                        # the virtual channel name. If name is 
                                        # specified, then you must use the name
                                        # when you refer to that channel in 
                                        # other NIDAQ functions)
                daq.DAQmx_Val_Hz,       # units, Hertz in our case
                my_idle,                # idle state
                0,                      # initial delay
                my_clock_frequency / 2.,# pulse frequency, divide by 2 such 
                                        # that length of 
                                        # semi period = count_interval
                0.5 )                   # duty cycle of pulses, 0.5 such that 
                                        # high and low duration are 
                                        # both = count_interval
                
        # Configure Implicit Timing.
        # Set timing to continuous, i.e. set only the number of samples to 
        # acquire or generate without specifying timing:
        daq.DAQmxCfgImplicitTiming(     #
                my_clock_daq_task,      # Define task
                daq.DAQmx_Val_ContSamps,# Sample Mode: set the task to generate
                                        # a continuous amount of running samples
                1000)                   # buffer length which stores 
                                        # temporarily the number of generated 
                                        # samples
        
        if scanner:
            self._scanner_clock_daq_task=my_clock_daq_task
        else:
            # actually start the preconfigured clock task
            daq.DAQmxStartTask(my_clock_daq_task)
            self._clock_daq_task=my_clock_daq_task
                           
        return 0
    
    def set_up_counter(self, counter_channel = None, photon_source = None,
                       clock_channel = None):
        """ Configures the actual counter with a given clock. 
        
        @param string counter_channel: if defined, this is the physical channel
                                       of the counter within the NI card
        @param string photon_source: if defined, this is the physical channel
                                     where the photons are to count from
        @param string clock_channel: if defined, this specifies the clock
                                     channel for the counter.
        
        @return int: error code (0:OK, -1:error)
        """
        
        if self._clock_daq_task is None and clock_channel is None:            
            self.logMsg('No clock running, call set_up_clock before starting '
                        'the counter.', msgType='error')
            return -1
        if self._counter_daq_task is not None:            
            self.logMsg('Another counter is already running, close this one '
                        'first.', msgType='error')
            return -1
            
        # This task will count photons with binning defined by the clock_channel
        self._counter_daq_task = daq.TaskHandle()   # Initialize a Task
        
        if counter_channel is not None:
            self._counter_channel = counter_channel
        if photon_source is not None:
            self._photon_source = photon_source
        
        if clock_channel is not None:
            my_clock_channel = clock_channel
        else: 
            my_clock_channel = self._clock_channel
        
        # Create task for the counter
        daq.DAQmxCreateTask('', daq.byref(self._counter_daq_task))  
        
        # Create a Counter Input which samples with Semi Perides the Channel.
        # set up semi period width measurement in photon ticks, i.e. the width
        # of each pulse (high and low) generated by pulse_out_task is measured
        # in photon ticks.
        #   (this task creates a channel to measure the time between state 
        #    transitions of a digital signal and adds the channel to the task 
        #    you choose)
        daq.DAQmxCreateCISemiPeriodChan(#
                self._counter_daq_task, # define to which task to connect 
                                        # this function
                self._counter_channel,  # use this counter channel
                'Counting Procedure',    # name to assing to it
                0,                      # expected minimum count value
                self._max_counts/2./self._clock_frequency,  # Expected maximum
                                                            # count value
                daq.DAQmx_Val_Ticks,    # units of width measurement,
                                        # here photon ticks
                '')   
        
        # Set the Counter Input to a Semi Period input Terminal.
        # Connect the pulses from the counter clock to the counter channel
        daq.DAQmxSetCISemiPeriodTerm(       #
                self._counter_daq_task,     # The task to which to add 
                                            # the counter channel.
                self._counter_channel,      # use this counter channel
                my_clock_channel+'InternalOutput')  # assign a name Terminal
                                                    # Name

                                    
        # Set a Counter Input Control Timebase Source.
        # Specify the terminal of the timebase which is used for the counter:
        # Define the source of ticks for the counter as self._photon_source for
        # the Scanner Task. 
        daq.DAQmxSetCICtrTimebaseSrc(   #
                self._counter_daq_task, # define to which task to connect 
                                        # this function
                self._counter_channel,  # counterchannel
                self._photon_source )   # counter channel to ouput the counting
                                        #  results
        
        # Configure Implicit Timing.
        # Set timing to continuous, i.e. set only the number of samples to 
        # acquire or generate without specifying timing:
        daq.DAQmxCfgImplicitTiming( 
                self._counter_daq_task, # define to which task to connect 
                                        # this function
                daq.DAQmx_Val_ContSamps,# Sample Mode: Acquire or generate 
                                        # samples until you stop the task.
                1000)                   # buffer length which stores 
                                        # temporarily the number of generated 
                                        # samples
                
        # Set the Read point Relative To an operation.
        # Specifies the point in the buffer at which to begin a read operation.
        # Here we read most recent recorded samples:
        daq.DAQmxSetReadRelativeTo(
                self._counter_daq_task,     # define to which task to connect 
                                            # this function
                daq.DAQmx_Val_CurrReadPos)  # Start reading samples relative to
                                            # the last sample returned by the
                                            # previous read.
        # Set the Read Offset.
        # Specifies an offset in samples per channel at which to begin a read 
        # operation. This offset is relative to the location you specify with 
        # RelativeTo. Here we set the Offset to 0 for multiple samples:
        daq.DAQmxSetReadOffset(self._counter_daq_task, 0) 
        
        # Set Read OverWrite Mode.
        # Specifies whether to overwrite samples in the buffer that you have 
        # not yet read. Unread data in buffer will be overwritten:
        daq.DAQmxSetReadOverWrite(self._counter_daq_task, 
                                  daq.DAQmx_Val_DoNotOverwriteUnreadSamps) 
        
        # Actually start the preconfigured counter task
        daq.DAQmxStartTask(self._counter_daq_task) 
        
        return 0
        
    def get_counter(self, samples=None):
        """ Returns the current counts per second of the counter. 
        
        @param int samples: if defined, number of samples to read in one go. 
                            How many samples are read per readout cycle. The 
                            readout frequency was defined in the counter setup.
                            That sets also the length of the readout array.
        
        @return float [samples]: array with entries as photon counts per second
        """
        
        if self._counter_daq_task is None:            
            self.logMsg('No counter running, call set_up_counter before '
                        'reading it.', msgType='error')
            #in case of error return a lot of -1
            return np.ones((samples,), dtype=np.uint32) * -1.
            
        if samples is None:
            samples = int(self._samples_number)
        else:
            samples = int(samples)
        
        # count data will be written here in the NumPy array of length samples
        count_data = np.empty((samples,), dtype=np.uint32) 
        
        # number of samples which were actually read, will be stored here
        n_read_samples = daq.int32() 
        
        # read the counter value: This function is blocking and waits for the
        # counts to be all filled:
        daq.DAQmxReadCounterU32(        
                self._counter_daq_task, # read from this task
                samples,                # number of samples to read
                self._RWTimeout,        # maximal timeout for the read process
                count_data,             # write the readout into this array 
                samples,                # length of array to write into
                daq.byref(n_read_samples),  # number of samples which were read
                None)                   # Reserved for future use. Pass NULL
                                        # (here None) to this parameter
        
        # normalize to counts per second and return data
        return count_data * self._clock_frequency 
    
    def close_counter(self, scanner=False):
        #FIXME: scanner: True means for scanner and False counter
        #FIXME: Does function indicate that???
    
        #FIXME: Cannot find a way to set up scanner_counter. In 
        #FIXME: def set_up_counter(self, counter_channel = None, photon_source = None, clock_channel = None):
        #FIXME: there is no 'scanner'-option
        """ Closes the counter or scanner and cleans up afterwards. 
        
        @param bool scanner: specifies if the counter- or scanner- function 
                             will be excecuted to close the device.
        
        @return int: error code (0:OK, -1:error)
        """
        
        if scanner:
            my_task=self._scanner_counter_daq_task
        else:
            my_task=self._counter_daq_task
        
        # stop the counter task
        daq.DAQmxStopTask(my_task)
        
        # after stopping delete all the configuration of the counter
        daq.DAQmxClearTask(my_task)
        
        # set the task handle to None as a safety
        if scanner:
            self._scanner_counter_daq_task = None
        else:
            self._counter_daq_task=None
        
        return 0
        
    def close_clock(self, scanner=False):
        #FIXME: scanner: True means for scanner and False counter
        #FIXME: Does function indicate that???
        """ Closes the clock and cleans up afterwards. 
        
        @param bool scanner: specifies if the counter- or scanner- function 
                             should be used to close the device.
        
        @return int: error code (0:OK, -1:error)
        """
        
        if scanner:
            my_task=self._scanner_clock_daq_task
        else:
            my_task=self._clock_daq_task
            
        # Stop the clock task:
        daq.DAQmxStopTask(my_task)
        
        # After stopping delete all the configuration of the clock:
        daq.DAQmxClearTask(my_task)
        
        # Set the task handle to None as a safety
        if scanner:
            self._scanner_clock_daq_task = None
        else:
            self._clock_daq_task = None

        return 0
        
    # ====================== Confocal Scanner =================================

    def get_position_range(self):
        """ Returns the physical range of the scanner.
        
        @return float [4][2]: array of 4 ranges with an array containing lower
                              and upper limit. The unit of the scan range is
                              micrometer.
        """ 
        return self._position_range
    
    #FIXME: Why not NONE here?  
    #FIXME: Why set to [0,1],[0,1],[0,1],[0,1]? In the beginning it was
    #       [0., 100.], [0., 100.], [0., 100.], [0., 100.]
    #FIXME: Aren't there dots missing after the 0s and 1s
    def set_position_range(self, myrange=[[0,1],[0,1],[0,1],[0,1]]):
        """ Sets the physical range of the scanner.
        
        @param float [4][2] myrange: array of 4 ranges with an array containing
                                     lower and upper limit. The unit of the 
                                     scan range is micrometer.
        
        @return int: error code (0:OK, -1:error)
        """ 
        
        if not isinstance( myrange, (frozenset, list, set, tuple, np.ndarray, ) ):
            self.logMsg('Given range is no array type.', msgType='error')
            return -1
            
        if len(myrange) != 4:
            self.logMsg('Given range should have dimension 4, but has {0:d} '
                        'instead.'.format(len(myrange)), msgType='error')
            return -1
            
        for pos in myrange:
            if len(pos) != 2:
                self.logMsg('Given range limit {1:d} should have dimension 2, '
                            'but has {0:d} instead.'.format(len(pos),pos),
                            msgType='error')
                return -1
            if pos[0]>pos[1]:
                self.logMsg('Given range limit {0:d} has the wrong order.'.format(pos),
                            msgType='error')
                return -1
                
        self._position_range = myrange    
            
        return 0
        
    def set_voltage_range(self, myrange=[-10.,10.]):
        """ Sets the voltage range of the NI Card.
        
        @param float [2] myrange: array containing lower and upper limit
        
        @return int: error code (0:OK, -1:error)
        """ 
        
        if not isinstance( myrange, (frozenset, list, set, tuple, np.ndarray, ) ):
            self.logMsg('Given range is no array type.', msgType='error')
            return -1
            
        if len(myrange) != 2:
            self.logMsg('Given range should have dimension 2, but has {0:d} '
                        'instead.'.format(len(myrange)), msgType='error')
            return -1
            
        if myrange[0]>myrange[1]:
            self.logMsg('Given range limit {0:d} has the '
                        'wrong order.'.format(myrange), msgType='error')
            return -1
                
        if self.getState() == 'locked' or self._scanner_counter_daq_task is not None:            
            self.logMsg('A Scanner is already running, close this one first.',
                        msgType='error')
            return -1
            
        self._voltage_range = myrange
            
        return 0
        
    def _start_analoque_output(self):
        """ Starts or restarts the analoque output.
        
        @return int: error code (0:OK, -1:error)
        """
        
        if self.getState() == 'locked' or self._scanner_counter_daq_task is not None:            
            self.logMsg('A Scanner is already running, close this one first.',
                        msgType='error')
            return -1
            
        # If an analoque task is already running, kill that one first
        if self._scanner_ao_task is not None:
            # stop the analoque output task
            daq.DAQmxStopTask(self._scanner_ao_task)
            
            # delete the configuration of the analoque output
            daq.DAQmxClearTask(self._scanner_ao_task)
            
            # set the task handle to None as a safety
            self._scanner_ao_task = None
    
        # initialize ao channels / task for scanner, should always be active.
        # Define at first the type of the variable as a Task:
        self._scanner_ao_task = daq.TaskHandle()
        
        # create the actual analoque output task on the hardware device. Via
        # byref you pass the pointer of the object to the TaskCreation function:
        daq.DAQmxCreateTask('',
                            daq.byref(self._scanner_ao_task))
        
        # Assign and configure the created task to an analog output voltage 
        # channel. 
        daq.DAQmxCreateAOVoltageChan(
                self._scanner_ao_task,      # The AO voltage operation function
                                            # is assigned to this task.
                self._scanner_ao_channels,  # use (all) sanncer ao_channels for
                                            # the output
                'Analog Control',           # assign a name for that task
                self._voltage_range[0],     # minimum possible voltage
                self._voltage_range[1],     # maximum possible voltage
                daq.DAQmx_Val_Volts,        # units is Volt
                '')                         # empty for future use
                                     
        return 0
        
        
    def set_up_scanner_clock(self, clock_frequency = None, clock_channel = None):
        """ Configures the hardware clock of the NiDAQ card to give the timing. 
        
        @param float clock_frequency: if defined, this sets the frequency of
                                      the clock
        @param string clock_channel: if defined, this is the physical channel 
                                     of the clock
        
        @return int: error code (0:OK, -1:error)
        """ 
        # The clock for the scanner is created on the same principle as it is
        # for the counter. Just to keep consistency, this function is a wrapper
        # around the set_up_clock.
        return self.set_up_clock(clock_frequency = clock_frequency,
                                 clock_channel = clock_channel, scanner = True)
        
    
    def set_up_scanner(self, counter_channel = None, photon_source = None, 
                       clock_channel = None, scanner_ao_channels = None):
        """ Configures the actual scanner with a given clock. 
        
        The scanner works pretty much like the counter. Here you connect a 
        created clock with a counting task. That can be seen as a gated 
        counting, where the counts where sampled by the underlying clock. 
        
        @param string counter_channel: optional, if defined, this is the 
                                       physical channel of the counter
        @param string photon_source: optional, if defined, this is the physical
                                     channel where the photons are to count from
        @param string clock_channel: optional, if defined, this specifies the 
                                     clock for the counter
        @param string scanner_ao_channels: optional, if defined, this specifies
                                           the analoque output channels
        
        @return int: error code (0:OK, -1:error)
        """
        
        if self._scanner_clock_daq_task is None and clock_channel is None:            
            self.logMsg('No clock running, call set_up_clock before starting '
                        'the counter.', msgType='error')
            return -1
        if self.getState() == 'locked' or self._scanner_counter_daq_task is not None:            
            self.logMsg('Another scanner is already running, close this one '
                        'first.', msgType='error')
            return -1
                    
        if counter_channel is not None:
            self._scanner_counter_channel = counter_channel
        if photon_source is not None:
            self._photon_source = photon_source
        
        if clock_channel is not None:
            self._my_scanner_clock_channel = clock_channel
        else: 
            self._my_scanner_clock_channel = self._scanner_clock_channel
            
        if scanner_ao_channels is not None:
            self._scanner_ao_channels = scanner_ao_channels
            self._start_analoque_output()
            
        # Set the Sample Timing Type. Task timing to use a sampling clock:
        # specify how the Data of the selected task is collected, i.e. set it
        # now to be sampled on demand for the analoque output, i.e. when 
        # demanded by software.
        daq.DAQmxSetSampTimingType(self._scanner_ao_task, daq.DAQmx_Val_OnDemand)
        
        # create handle for task, this task will do the photon counting for the
        # scanner.
        self._scanner_counter_daq_task = daq.TaskHandle()
        
        # actually create the scanner counting task
        daq.DAQmxCreateTask('', 
                            daq.byref(self._scanner_counter_daq_task))
        
        # Create a Counter Input which samples with Semi Perides the Channel.
        # set up semi period width measurement in photon ticks, i.e. the width
        # of each pulse (high and low) generated by pulse_out_task is measured
        # in photon ticks.
        #   (this task creates a channel to measure the time between state 
        #    transitions of a digital signal and adds the channel to the task 
        #    you choose)
        daq.DAQmxCreateCISemiPeriodChan(
                self._scanner_counter_daq_task, # The task to which to add the 
                                                # channels
                self._scanner_counter_channel,  # use this counter channel
                'Scanner Counter',              # name to assing to it
                0,                              # expected minimum value
                self._max_counts/self._scanner_clock_frequency, # Expected 
                                                                # maximum count
                                                                # value
                daq.DAQmx_Val_Ticks,            # units of width measurement, 
                                                # here Timebase photon ticks
                '')
                
        # Set the Counter Input to a Semi Period input Terminal.
        # Connect the pulses from the scanner clock to the scanner counter
        daq.DAQmxSetCISemiPeriodTerm(
                self._scanner_counter_daq_task,     # The task to which to add 
                                                    # the counter channel.
                self._scanner_counter_channel,      # use this counter channel
#                '100kHzTimebase')    # assign a
                self._my_scanner_clock_channel+'InternalOutput')    # assign a
                                                                    # Terminal
                                                                    # Name
        # Set a CounterInput Control Timebase Source.
        # Specify the terminal of the timebase which is used for the counter:
        # Define the source of ticks for the counter as self._photon_source for
        # the Scanner Task. 
        daq.DAQmxSetCICtrTimebaseSrc(
                self._scanner_counter_daq_task, # define to which task to
                                                # connect this function
                self._scanner_counter_channel,  # counter channel to ouput the
                                                # counting results
                self._photon_source )           # which channel to count  
    
        
        return 0
    
    def scanner_set_position(self, x = None, y = None, z = None, a = None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).
        
        #FIXME: No volts
        @param float x: postion in x-direction (volts)
        @param float y: postion in y-direction (volts)
        @param float z: postion in z-direction (volts)
        @param float a: postion in a-direction (volts)
        
        @return int: error code (0:OK, -1:error)
        """
        
        if self.getState() == 'locked':            
            self.logMsg('Another scan_line is already running, close this '
                        'one first.', msgType='error')
            return -1
            
        if x is not None:
            if x < self._position_range[0][0] or x > self._position_range[0][1]:                
                self.logMsg('You want to set x out of range: {0:f}.'.format(x), 
                            msgType='error')
                return -1
            self._current_position[0] = np.float(x)
            
        if y is not None:
            if y < self._position_range[1][0] or y > self._position_range[1][1]:                
                self.logMsg('You want to set y out of range: {0:f}.'.format(y), 
                            msgType='error')
                return -1
            self._current_position[1] = np.float(y)
            
        if z is not None:
            if z < self._position_range[2][0] or z > self._position_range[2][1]:                
                self.logMsg('You want to set z out of range: {0:f}.'.format(z), 
                            msgType='error')
                return -1
            self._current_position[2] = np.float(z)
            
        if a is not None:
            if a < self._position_range[3][0] or a > self._position_range[3][1]:                
                self.logMsg('You want to set a out of range: {0:f}.'.format(a), 
                            msgType='error')
                return -1
            self._current_position[3] = np.float(a)
            
        # the position has to be a vstack
        my_position = np.vstack(self._current_position)
        
        # then directly write the position to the hardware
        self._write_scanner_ao(voltages=self._scanner_position_to_volt(my_position), 
                               start=True)
        
        return 0
        
    def _write_scanner_ao(self, voltages, length=1, start=False):
        """Writes a set of voltages to the analoque outputs.
        
        @param float[][4] voltages: array of 4-part tuples defining the voltage
                                    points
        @param int length: number of tuples to write
        @param bool start: write imediately (True) 
                           or wait for start of task (False)
        
        @return int: error code (0:OK, -1:error)
        """
        
        # Number of samples which were actually written, will be stored here.
        # The error code of this variable can be asked with .value to check
        # whether all channels have been written successfully.
        self._AONwritten = daq.int32()
        
        # write the voltage instructions for the analoque output to the hardware
        daq.DAQmxWriteAnalogF64(
                self._scanner_ao_task,      # write to this task
                length,                     # length of the command (points)
                start,                      # start task immediately (True), or
                                            # wait for software start (False)
                self._RWTimeout,            # maximal timeout in seconds for 
                                            # the write process
                daq.DAQmx_Val_GroupByChannel, # Specify how the samples are 
                                              # arranged: each pixel is grouped
                                              # by channel number
                voltages,                   # the voltages to be written
                daq.byref(self._AONwritten),# The actual number of samples per 
                                            # channel successfully written to 
                                            # the buffer.
                None)                       # Reserved for future use. Pass 
                                            # NULL(here None) to this parameter
        
        #FIXME: Is that error code? Or what does that .value mean/do?
        return self._AONwritten.value
    
    def _scanner_position_to_volt(self, positions = None):
        """ Converts a set of position pixels to acutal voltages.
        
        @param float[][4] positions: array of 4-part tuples defining the pixels
        
        @return float[][4]: array of 4-part tuples of corresponing voltages
        
        The positions is actually a matrix like
            [[x_values],[y_values],[z_values],[counts]]
        where the count values will be overwritten by the scanning routine.
        
        """
        
        if not isinstance(positions, (frozenset, list, set, tuple, np.ndarray, ) ):
            self.logMsg('Given position list is no array type.',
                        msgType='error')
            return np.array([-1.,-1.,-1.,-1.])
        
        # Calculate the voltages from the positions, their ranges and stack 
        # them together:
        volts = np.vstack(( \
            (self._voltage_range[1]-self._voltage_range[0])\
                / (self._position_range[0][1]-self._position_range[0][0])\
                * (positions[0]-self._position_range[0][0])\
                    + self._voltage_range[0],\
           (self._voltage_range[1]-self._voltage_range[0])\
               / (self._position_range[1][1]-self._position_range[1][0])\
               * (positions[1]-self._position_range[1][0])\
               + self._voltage_range[0],\
            (self._voltage_range[1]-self._voltage_range[0])\
                / (self._position_range[2][1]-self._position_range[2][0])\
                * (positions[2]-self._position_range[2][0])\
                    + self._voltage_range[0],\
            (self._voltage_range[1]-self._voltage_range[0])\
                / (self._position_range[3][1]-self._position_range[3][0])\
                * (positions[3]-self._position_range[3][0])\
                    + self._voltage_range[0] ) )
  
        if volts.min() < self._voltage_range[0] or volts.max() > self._voltage_range[1]:
            self.logMsg('Voltages exceed the limit, the positions have to be '
                        'adjusted to stay in the given range.',msgType='error')
            return np.array([-1.,-1.,-1.,-1.])
            
        return volts
        
    def get_scanner_position(self):
        """ Get the current position of the scanner hardware.

        @return float[]: current position in (x, y, z, a).
        """
        
        return self._current_position
        
        
    def set_up_line(self, length=100):
        """ Sets up the analoque output for scanning a line.
        
        Connect the timing of the Analog scanning task with the timing of the
        counting task.
        
        @param int length: length of the line in pixel
        
        @return int: error code (0:OK, -1:error)
        """
        
        if self._scanner_counter_daq_task is None:            
            self.logMsg('No counter is running, cannot scan a line '
                        'without one.', msgType='error')
            return -1
            
        self._line_length = length
        
        # Just a formal check whether length is not a too huge number
        if length < np.inf:
            
            # Configure the Sample Clock Timing.
            # Set up the timing of the scanner counting while the voltages are
            # being scanned (i.e. that you go through each voltage, which 
            # corresponds to a position. How fast the voltages are being 
            # changed is combined with obtaining the counts per voltage peak).
            daq.DAQmxCfgSampClkTiming(
                    self._scanner_ao_task,          # add to this task
                    self._my_scanner_clock_channel+'InternalOutput', # use this
                                                                     # channel 
                                                                     # as clock
                    self._scanner_clock_frequency,  # Maximum expected clock 
                                                    # frequency
                    daq.DAQmx_Val_Falling,          # Generate sample on 
                                                    # falling edge
                    daq.DAQmx_Val_FiniteSamps,      # generate finite number of
                                                    # samples
                    self._line_length)              # number of samples to 
                                                    # generate
        # Configure Implicit Timing for the clock.
        # Set timing for scanner clock task to the number of pixel.
        daq.DAQmxCfgImplicitTiming(
                self._scanner_clock_daq_task,   # define task
                daq.DAQmx_Val_FiniteSamps,      # only a limited number of 
                                                # counts
                self._line_length+1)          # count twice for each voltage
                                                # +1 for safety
                              
        # Configure Implicit Timing for the scanner counting task.
        # Set timing for scanner count task to the number of pixel.
        daq.DAQmxCfgImplicitTiming(
                self._scanner_counter_daq_task, # define task
                daq.DAQmx_Val_FiniteSamps,      # only a limited number of 
                                                # counts
                2*self._line_length+1)          # count twice for each voltage
                                                # +1 for safety
                                 
        # Set the Read point Relative To an operation.
        # Specifies the point in the buffer at which to begin a read operation,
        # here we read samples from beginning of acquisition and do not overwrite
        daq.DAQmxSetReadRelativeTo(
                self._scanner_counter_daq_task, # define to which task to
                                                # connect this function
                daq.DAQmx_Val_CurrReadPos)      # Start reading samples 
                                                # relative to the last sample 
                                                # returned by the previous read.
         
        # Set the Read Offset.
        # Specifies an offset in samples per channel at which to begin a read 
        # operation. This offset is relative to the location you specify with 
        # RelativeTo. Here we do not read the first sample.
        daq.DAQmxSetReadOffset(
                self._scanner_counter_daq_task, # connect to this taks
                1)                              # Offset after which to read
        
        # Set Read OverWrite Mode.
        # Specifies whether to overwrite samples in the buffer that you have 
        # not yet read. Unread data in buffer will be overwritten:
        daq.DAQmxSetReadOverWrite(self._scanner_counter_daq_task, 
                                  daq.DAQmx_Val_DoNotOverwriteUnreadSamps) 
        
        return 0
        
    def scan_line(self, line_path = None):
        """ Scans a line and return the counts on that line. 
        
        @param float[][4] line_path: array of 4-part tuples defining the 
                                    voltage points
        
        @return float[]: the photon counts per second
        
        The input array looks for a xy scan of 5x5 points at the position z=-2
        like the following:
            [ [1,2,3,4,5],[1,1,1,1,],[-2,-2,-2,-2],[0,0,0,0]]
            
        
        
        """
        
        if self.getState() == 'locked':            
            self.logMsg('Another scan_line is already running, close this '
                        'one first.', msgType='error')
            #FIXME: Here you just return -1 and below you return np.array([-1.])
            #Is there a difference? If not make consistent.
            return -1
            
        if self._scanner_counter_daq_task is None:            
            self.logMsg('No counter is running, cannot scan a line without '
                        'one.', msgType='error')
            return np.array([-1.])
            
        if not isinstance( line_path, (frozenset, list, set, tuple, np.ndarray, ) ):
            self.logMsg('Given voltage list is no array type.',msgType='error')
            return np.array([-1.])
        
        self.lock() # lock this thread so others cannot call
        
        # set task timing to use a sampling clock:
        # specify how the Data of the selected task is collected, i.e. set it
        # now to be sampled by a hardware (clock) signal.
        daq.DAQmxSetSampTimingType(self._scanner_ao_task, daq.DAQmx_Val_SampClk)
        
        #if np.shape(line_path)[1] is not self._line_length:
        self.set_up_line(np.shape(line_path)[1])
        
        # write the positions to the analoque output
        written_voltages = self._write_scanner_ao(voltages=
                                                  self._scanner_position_to_volt(line_path), 
                                                  length=self._line_length, 
                                                  start=False)
        
        # start the timed analoque output task
        daq.DAQmxStartTask(self._scanner_ao_task)
        
        daq.DAQmxStopTask(self._scanner_counter_daq_task)
        daq.DAQmxStopTask(self._scanner_clock_daq_task)        
        
        # start the scanner counting task that acquires counts synchroneously
        daq.DAQmxStartTask(self._scanner_counter_daq_task)
        daq.DAQmxStartTask(self._scanner_clock_daq_task)
        
        # wait for the scanner counter to finish
        daq.DAQmxWaitUntilTaskDone(
                self._scanner_counter_daq_task,     # define task
                self._RWTimeout*2*self._line_length)# maximal timeout for the 
                                                    # counter times the 
                                                    # positions. Unit is second
        # wait for the scanner clock to finish
        daq.DAQmxWaitUntilTaskDone(
                self._scanner_clock_daq_task,       # define task
                self._RWTimeout*2*self._line_length)# maximal timeout for the 
                                                    # counter times the positions 
                
#        self._line_length = 100
        # count data will be written here
        self._scan_data = np.empty((2*self._line_length,), dtype=np.uint32)
        
        # number of samples which were read will be stored here
        n_read_samples = daq.int32()
        
        # actually read the counted photons
        daq.DAQmxReadCounterU32(
                self._scanner_counter_daq_task, # read from this task
                2*self._line_length,            # read number of double the 
                                                # number of samples
                self._RWTimeout,                # maximal timeout for the read 
                                                # process
                self._scan_data,                # write into this array
                2*self._line_length,            # length of array to write into
                daq.byref(n_read_samples),      # number of samples which were
                                                # actually read
                None)                           # Reserved for future use. Pass 
                                                # NULL(here None) to this parameter
        
        # stop the counter task
        daq.DAQmxStopTask(self._scanner_counter_daq_task)
        daq.DAQmxStopTask(self._scanner_clock_daq_task)
        
        #stop the analoque output taks
        daq.DAQmxStopTask(self._scanner_ao_task)
#        
        # set task timing to on demand, i.e. when demanded by software
        daq.DAQmxSetSampTimingType(
                self._scanner_ao_task,  # define task
                daq.DAQmx_Val_OnDemand) # sampling directly when a voltage 
                                        # is written
        
        # create a new array for the final data (this time of the length 
        # number of samples):
        self._real_data = np.empty((self._line_length,), dtype=np.uint32)
        
        # add upp adjoint pixels to also get the counts from the low time of
        # the clock:
        self._real_data = self._scan_data[::2]
        self._real_data += self._scan_data[1::2]        
        
        self.unlock()   # unlock the thread
        
        return self._real_data*(self._scanner_clock_frequency)
        
        
    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards. 
        
        @return int: error code (0:OK, -1:error)
        """
        
        return self.close_counter(scanner=True)
        
    def close_scanner_clock(self):
        """ Closes the clock and cleans up afterwards. 
        
        @return int: error code (0:OK, -1:error)
        """     
        
        return self.close_clock(scanner=True)

################################# ODMR ######################################

    def set_up_odmr_clock(self, clock_frequency = None, clock_channel = None):
        """ Configures the hardware clock of the NiDAQ card to give the timing. 
        
        @param float clock_frequency: if defined, this sets the frequency of 
                                      the clock
        @param string clock_channel: if defined, this is the physical channel 
                                     of the clock
        
        @return int: error code (0:OK, -1:error)
        """ 
        
        return self.set_up_clock(clock_frequency = clock_frequency, 
                                 clock_channel = clock_channel, 
                                 scanner = True,
                                 idle=True)
        
    
    def set_up_odmr(self, counter_channel = None, photon_source = None, 
                    clock_channel = None, odmr_trigger_channel = None):
        """ Configures the actual counter with a given clock. 
        
        @param string counter_channel: if defined, this is the physical channel
                                       of the counter
        @param string photon_source: if defined, this is the physical channel 
                                     where the photons are to count from
        @param string clock_channel: if defined, this specifies the clock for 
                                     the counter
        @param string odmr_trigger_channel: if defined, this specifies the 
                                            trigger output for the microwave
        
        @return int: error code (0:OK, -1:error)
        """
        
        if self._scanner_clock_daq_task is None and clock_channel is None:            
            self.logMsg('No clock running, call set_up_clock before starting '
                        'the counter.', msgType='error')
            return -1
        if self._scanner_counter_daq_task is not None:            
            self.logMsg('Another counter is already running, close this '
                        'one first.', msgType='error')
            return -1
            
        # this task will count photons with binning defined by the clock_channel
        self._scanner_counter_daq_task = daq.TaskHandle()
        if counter_channel is not None:
            self._scanner_counter_channel = counter_channel
        if photon_source is not None:
            self._photon_source = photon_source
        
        if clock_channel is not None:
            my_clock_channel = clock_channel
        else: 
            my_clock_channel = self._scanner_clock_channel
        
        # create task for the counter
        daq.DAQmxCreateTask('', daq.byref(self._scanner_counter_daq_task))  
        
        # set up semi period width measurement in photon ticks, i.e. the width
        # of each pulse (high and low) generated by pulse_out_task is measured
        # in photon ticks.
        #   (this task creates a channel to measure the time between state 
        #    transitions of a digital signal and adds the channel to the task 
        #    you choose)
        daq.DAQmxCreateCISemiPeriodChan(
                self._scanner_counter_daq_task, # define to which task to  
                                                # connect this function
                self._scanner_counter_channel,  # use this counter channel
                'Counting Task',                # name to assing to it
                0,                              # Expected minimum count value
                self._max_counts/2./self._scanner_clock_frequency,# Expected 
                                                                  # maximum 
                                                                  # count value
                daq.DAQmx_Val_Ticks,            # units of width measurement,
                                                # here photon ticks
                '')

        # connect the pulses from the clock to the counter
        daq.DAQmxSetCISemiPeriodTerm(self._scanner_counter_daq_task, 
                                     self._scanner_counter_channel, 
                                     my_clock_channel+'InternalOutput')
                                     
        # define the source of ticks for the counter as self._photon_source
        daq.DAQmxSetCICtrTimebaseSrc( self._scanner_counter_daq_task, 
                                     self._scanner_counter_channel, 
                                     self._photon_source )
                                     
        
        #start and stop pulse task to correctly initiate idle state high voltage.
        daq.DAQmxStartTask(self._scanner_clock_daq_task)  
        #otherwise, it will be low until task starts, and MW will receive wrong pulses.
        daq.DAQmxStopTask(self._scanner_clock_daq_task)   
        
        # connect the clock to the trigger channel to give triggers for the
        # microwave
        daq.DAQmxConnectTerms(self._scanner_clock_channel+'InternalOutput', 
                              self._odmr_trigger_channel, 
                              daq.DAQmx_Val_DoNotInvertPolarity )
        
        return 0
        
    def set_odmr_length(self,length = 100):
        """ Sets up the trigger sequence for the ODMR and the triggered microwave.
        
        @param int length: length of microwave sweep in pixel
        
        @return int: error code (0:OK, -1:error)
        """
        
        if self._scanner_counter_daq_task is None:            
            self.logMsg('No counter is running, cannot do ODMR without one.',
                        msgType='error')
            return -1
            
        self._odmr_length = length   
        
        # set timing for odmr clock task to the number of pixel.
        daq.DAQmxCfgImplicitTiming(             
                self._scanner_clock_daq_task,   # define task
                daq.DAQmx_Val_FiniteSamps,      # only a limited number of counts
                self._odmr_length+1)            # count twice for each voltage
                                                # +1 for starting this task. 
                                                # This first pulse will start 
                                                # the count task.
                                   
        # set timing for odmr count task to the number of pixel.
        daq.DAQmxCfgImplicitTiming(
                self._scanner_counter_daq_task, # define task
                daq.DAQmx_Val_FiniteSamps,      # only a limited number of counts
                2*self._odmr_length)            # count twice for each voltage 
                                                # +1 for starting this task. 
                                                # This first pulse will start 
                                                # the count task.
                                   
        # read samples from beginning of acquisition, do not overwrite
        daq.DAQmxSetReadRelativeTo(self._scanner_counter_daq_task, 
                                   daq.DAQmx_Val_CurrReadPos) 
                                   
        # do not read first sample
        daq.DAQmxSetReadOffset(self._scanner_counter_daq_task, 0)
        
        # unread data in buffer will be overwritten
        daq.DAQmxSetReadOverWrite(self._scanner_counter_daq_task, 
                                  daq.DAQmx_Val_DoNotOverwriteUnreadSamps) 
        
        return 0
        
    def count_odmr(self, length = 100):
        """ Sweeps the microwave and returns the counts on that sweep. 
        
        @param int length: length of microwave sweep in pixel
        
        @return float[]: the photon counts per second
        """
        
        if self.getState() == 'locked':            
            self.logMsg('Another scan_line is already running, close this '
                        'one first.', msgType='error')
            return np.array([-1.])
            
        
        if self._scanner_counter_daq_task is None:            
            self.logMsg('No counter is running, cannot scan a line without '
                        'one.', msgType='error')
            return np.array([-1.])
            
        self.lock()
            
        # check if length setup is correct, if not, adjust.
#        if self._odmr_length != length:
        self.set_odmr_length(length)
            
        # start the scanner counting task that acquires counts synchroneously
        daq.DAQmxStartTask(self._scanner_counter_daq_task)
        daq.DAQmxStartTask(self._scanner_clock_daq_task)
        
        # wait for the scanner counter to finish
        daq.DAQmxWaitUntilTaskDone(
                self._scanner_counter_daq_task,     # define task
                self._RWTimeout*2*self._odmr_length)# maximal timeout for the 
                                                    # counter times the positions
                
        # wait for the scanner clock to finish
        daq.DAQmxWaitUntilTaskDone(
                self._scanner_clock_daq_task,     # define task
                self._RWTimeout*2*self._odmr_length)# maximal timeout for the 
                                                    # counter times the positions
        
        # count data will be written here
        self._odmr_data = np.empty((2*self._odmr_length,), dtype=np.uint32)
        
        #number of samples which were read will be stored here
        n_read_samples = daq.int32()
        
        # actually read the counted photons
        daq.DAQmxReadCounterU32(
                self._scanner_counter_daq_task, # read from this task
                2*self._odmr_length,            # Read number of double the 
                                                # number of samples
                self._RWTimeout,                # Maximal timeout for the read 
                                                # process
                self._odmr_data,                # write into this array
                2*self._odmr_length,            # length of array to write into
                daq.byref(n_read_samples),      # number of samples which were 
                                                # actually read
                None)                           # Reserved for future use. Pass
                                                # NULL(here None) to this parameter
        # stop the counter task
        daq.DAQmxStopTask(self._scanner_counter_daq_task)
        daq.DAQmxStopTask(self._scanner_clock_daq_task)
        
        # create a new array for the final data (this time of the length 
        # number of samples)
        self._real_data = np.zeros((self._odmr_length,), dtype=np.uint32)
        
        # add upp adjoint pixels to also get the counts from the low time of 
        # the clock:
        self._real_data = self._odmr_data[::2]
        self._real_data += self._odmr_data[1::2]        
        
        self.unlock()
        
        return self._real_data*(self._scanner_clock_frequency)
        

    def close_odmr(self):
        """ Closes the odmr and cleans up afterwards. 
        
        @return int: error code (0:OK, -1:error)
        """
        
        # disconnect the trigger channel
        daq.DAQmxDisconnectTerms(self._scanner_clock_channel+'InternalOutput', 
                                 self._odmr_trigger_channel)
        
        return self.close_counter(scanner=True)
        
    def close_odmr_clock(self):
        """ Closes the odmr and cleans up afterwards. 
        
        @return int: error code (0:OK, -1:error)
        """     
        
        return self.close_clock(scanner=True)



    # ======================== Gated photon counting ==========================
    def set_up_gated_counter(self, buffer_length, read_available_samples=False):
        """ Initializes and starts task for external gated photon counting.
        
        @param int buffer_length: Defines how long the buffer to be filled with
                                  samples should be. If buffer is full, program
                                  crashes, so use upper bound. Some reference
                                  calculated with sample rate(S/s)\Buffer size:
                                      no rate\10kS, 
                                      0-100S/s\10kS
                                      101-10kS/s\1kS,
                                      10k-1MS/s\100kS, 
                                      >1MS/s\1Ms
        @param bool read_available_samples: if False, NiDaq waits for the 
                                            sample you asked for to be in the 
                                            buffer before, True it returns what
                                            is in buffer until 'samples' is full
        """
        
        if self._gated_counter_daq_task is not None:            
            self.logMsg('Another gated counter is already running, close this '
                        'one first.', msgType='error')
            return -1

        # This task will count photons with binning defined by pulse task
        self._gated_counter_daq_task = daq.TaskHandle()   # Initialize a Task

        daq.DAQmxCreateTask('', daq.byref(self._gated_counter_daq_task))

        # Set up pulse width measurement in photon ticks, i.e. the width of 
        # each pulse generated by pulse_out_task is measured in photon ticks:
        daq.DAQmxCreateCIPulseWidthChan(
                self._gated_counter_daq_task,   # add to this task:
                self._counter_channel,          # use this counter:
                'Gated Counting Task',          # name you assign to it              
                0,                              # expected minimum value        
                self._max_counts,               # expected maximum value
                daq.DAQmx_Val_Ticks,            # units of width measurement, 
                                                # here photon ticks.
                self._counting_edge,            # start pulse width measurement
                                                # on rising edge
                '')  

        # Set the pulses to counter self._function_counter_in
        daq.DAQmxSetCIPulseWidthTerm(self._gated_counter_daq_task, 
                                     self._counter_channel, 
                                     self._gate_in_channel)

        #  Define the source of ticks for the counter as self._photon_source.
        daq.DAQmxSetCICtrTimebaseSrc(self._gated_counter_daq_task, 
                                     self._counter_channel, 
                                     self._photon_source )

        # set timing to continuous
        daq.DAQmxCfgImplicitTiming(
                self._gated_counter_daq_task,   # define to which task to 
                                                # connect this function.
                daq.DAQmx_Val_ContSamps,        # Sample Mode: set the task to 
                                                # generate a continuous amount 
                                                # of running samples
                buffer_length)                  # buffer length which stores
                                                # temporarily the number of 
                                                # generated samples

        # Read samples from beginning of acquisition, do not overwrite
        daq.DAQmxSetReadRelativeTo(self._gated_counter_daq_task, 
                                   daq.DAQmx_Val_CurrReadPos)

        # If this is set to True, then the NiDaq will not wait for the sample 
        # you asked for to be in the buffer before read out but immediately 
        # hand back all samples until #samples is reached.
        if read_available_samples: 
            daq.DAQmxSetReadReadAllAvailSamp(self._gated_counter_daq_task,
                                             True)

        # Do not read first sample:
        daq.DAQmxSetReadOffset(self._gated_counter_daq_task, 0)

        # uUnread data in buffer is not overwritten
        daq.DAQmxSetReadOverWrite(self._gated_counter_daq_task,
                                  daq.DAQmx_Val_DoNotOverwriteUnreadSamps)

        # Actually start the preconfigured counter task
        daq.DAQmxStartTask(self._gated_counter_daq_task)

        return 0

    def get_gated_counts(self, samples = None, timeout=None, 
                         read_available_samples = False):
        """ Returns latest count samples acquired by gated photon counting.
        
        @param int samples: if defined, number of samples to read in one go.
                            How many samples are read per readout cycle. The
                            readout frequency was defined in the counter setup.
                            That sets also the length of the readout array.
        @param int timeout: Maximal timeout for the read process. Since nidaq
                            waits for all samples to be acquired, make sure 
                            this is long enough.
        @param bool read_available_samples : if False, NiDaq waits for the 
                                             sample you asked for to be in the 
                                             buffer before, True it returns 
                                             what is in buffer until 'samples'
                                             is full.
        """
        if samples is None:
            samples = int(self._samples_number)
        else:
            samples = int(samples)
        
        if timeout is None:
            timeout = self._RWTimeout

        # Count data will be written here
        _gated_count_data = np.empty((samples,), dtype=np.uint32)

        # Number of samples which were read will be stored here
        n_read_samples = int() 

        if read_available_samples:
            samples_2 = -1
        else: 
            samples_2 = samples

        daq.DAQmxReadCounterU32(
                self._gated_counter_daq_task,   # read from this task
                samples_2,                      # read number samples
                timeout,                        # maximal timeout for the read 
                                                # process
                _gated_count_data.ctypes.data,  # write into this array
               samples,                         # length of array to write into
               daq.byref(n_read_samples),       # number of samples which were
                                                # read.
               None)                            # Reserved for future use. Pass
                                                # NULL (here None) to this 
                                                # parameter

        # Chops the array or read sample to the length that it exactly returns
        # acquired data and not more
        if read_available_samples: 
            return _gated_count_data[:n_read_samples.value], n_read_samples
        else:
            return _gated_count_data[:]

    def close_gated_counter(self):
        """ Clear tasks, so that counters are not in use any more.
        
        @return int: error code (0:OK, -1:error)
        """
        
        daq.DAQmxStopTask(self._gated_counter_daq_task)     # stop the task
        daq.DAQmxClearTask(self._gated_counter_daq_task)    # clear the task
        self._gated_counter_daq_task = None
        
        return 0




