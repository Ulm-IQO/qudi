# -*- coding: utf-8 -*-

from core.Base import Base
from hardware.slowcounterinterface import SlowCounterInterface
import random

import PyDAQmx as daq
import numpy as np

class niinterface(Base,SlowCounterInterface):
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    
    def __init__(self, manager, name, config, **kwargs):
        Base.__init__(self, manager, name, configuation=config)
        self._modclass = 'niinterface'
        self._modtype = 'slowcounterinterface'
        
        self.logMsg('The following configuration was found.', 
                    messageType='status')
                    
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        messageType='status')
                        
        self._MaxCounts = 1e7
        self._RWTimeout = 5
        self._counter_daq_task = None
        self._clock_daq_task = None
        
        if 'clock_channel' in config.keys():
            self._clock_channel=config['clock_channel']
        else:
            self.logMsg('No clock_channel configured.', messageType='error')
            
        if 'counter_channel' in config.keys():
            self._counter_channel=config['counter_channel']
        else:
            self.logMsg('No counter_channel configured.', messageType='error')
            
        if 'photon_source' in config.keys():
            self._photon_source=config['photon_source']
        else:
            self.logMsg('No photon_source configured.', messageType='error')
            
        if 'clock_frequency' in config.keys():
            self._clock_frequency=config['clock_frequency']
        else:
            self._clock_frequency=100
            self.logMsg('No clock_frequency configured tanking 100 Hz instead.', \
            messageType='warning')
            
        if 'samples_number' in config.keys():
            self._samples_number=config['samples_number']
        else:
            self._samples_number=10
            self.logMsg('No samples_number configured tanking 10 instead.', \
            messageType='warning')
                                    
        self.testing()
        
    def testing(self):
        self.set_up_clock(clock_frequency = self._clock_frequency, clock_channel = '/Dev1/Ctr0')
        self.set_up_counter(counter_channel = '/Dev1/Ctr1', photon_source= '/Dev1/PFI8')
        for i in range(5):
            print(self.get_counter(samples=self._samples_number))
        self.close_counter()
        self.close_clock()
        
    def set_up_clock(self, clock_frequency = None, clock_channel = None):
        """ Configures the hardware clock of the NiDAQ card to give the timing. 
        <blank line>
        @param float clock_frequency: if defined, this sets the frequency of the clock
        @param string clock_channel: if defined, this is the physical channel of the clock
        <blank line>
        @return int: error code (0:OK, -1:error)
        """ 
        
        if self._clock_daq_task != None:            
            self.logMsg('Another clock is already running, close this one first.', \
            messageType='error')
            return -1
        
        self._clock_daq_task = daq.TaskHandle()  # create handle for task, this task will generate pulse signal for photon counting
        if clock_frequency != None:
            self._clock_frequency = float(clock_frequency)
        if clock_channel != None:
            self._clock_channel = clock_channel
        
        daq.DAQmxCreateTask('', daq.byref(self._clock_daq_task))    # create task for pulse_out, here the parameter self.pulse_out_task has to be passed by reference (passing a pointer) 
        daq.DAQmxCreateCOPulseChanFreq( self._clock_daq_task,      # the task to which to add the channels that this function creates
                            		    self._clock_channel,  # use this counter; the name to assign to the created channel
										'Clock Task',    # name to assign to channel (NIDAQ uses by default the physical channel name as the virtual channel name. If name is specified, then you must use the name when you refer to that channel in other NIDAQ functions)
										daq.DAQmx_Val_Hz, #units
										daq.DAQmx_Val_Low, #idle state
										0, #initial delay
										self._clock_frequency / 2.,   #pulse frequency, divide by 2 such that length of semi period = count_interval
										0.5 ) #duty cycle of pulses, 0.5 such that high and low duration are both = count_interval
        
        # set timing to continuous, i.e. set only the number of samples to 
        # acquire or generate without specifying timing
        daq.DAQmxCfgImplicitTiming( self._clock_daq_task,  #define task
                                    daq.DAQmx_Val_ContSamps,  #continuous running
                                    1000) #buffer length
                                    
        daq.DAQmxStartTask(self._clock_daq_task) 
                           
        return 0
    
    def set_up_counter(self, counter_channel = None, photon_source = None, clock_channel = None):
        """ Configures the actual counter with a given clock. 
        <blank line>
        @param string counter_channel: if defined, this is the physical channel of the counter
        @param string photon_source: if defined, this is the physical channel where the photons are to count from
        @param string clock_channel: if defined, this specifies the clock for the counter
        <blank line>
        @return int: error code (0:OK, -1:error)
        """
        
        if self._clock_daq_task == None and clock_channel == None:            
            self.logMsg('No clock running, call set_up_clock before starting the counter.', \
            messageType='error')
            return -1
        if self._counter_daq_task != None:            
            self.logMsg('Another counter is already running, close this one first.', \
            messageType='error')
            return -1
            
        self._counter_daq_task = daq.TaskHandle()  # this task will count photons with binning defined by pulse_out_task
        if counter_channel != None:
            self._counter_channel = counter_channel
        if photon_source != None:
            self._photon_source = photon_source
        
        if clock_channel != None:
            my_clock_channel = clock_channel
        else: 
            my_clock_channel = self._clock_channel
        
        daq.DAQmxCreateTask('', daq.byref(self._counter_daq_task))  # create task for counter_in, here the parameter self.counter_in_task has to be passed by reference (passing a pointer) 
        
        # set up semi period width measurement in photon ticks, i.e. the width
        # of each pulse (high and low) generated by pulse_out_task is measured
        # in photon ticks.
        #   (this task creates a channel to measure the time between state 
        #    transitions of a digital signal and adds the channel to the task 
        #    you choose)
        daq.DAQmxCreateCISemiPeriodChan(self._counter_daq_task,    # The task to which to add the channels that this function creates
                                        self._counter_channel,  # use this counter; the name to assign to the created channel
                                        'Counting Task',  #name
                                        0,  #expected minimum value
                                        self._MaxCounts/2./self._clock_frequency,    #expected maximum value
                                        daq.DAQmx_Val_Ticks, #units of width measurement, here photon ticks
                                        '')   
        
        # set the pulses to counter self._trace_counter_in
        daq.DAQmxSetCISemiPeriodTerm( self._counter_daq_task, self._counter_channel, my_clock_channel+'InternalOutput')
        # set the timebase for width measurement as self._photon_source
        daq.DAQmxSetCICtrTimebaseSrc( self._counter_daq_task, self._counter_channel, self._photon_source )  
        
        daq.DAQmxCfgImplicitTiming( self._counter_daq_task,
                                    daq.DAQmx_Val_ContSamps, 
                                    1000)
        # read most recent samples
        daq.DAQmxSetReadRelativeTo(self._counter_daq_task, daq.DAQmx_Val_CurrReadPos) 
        daq.DAQmxSetReadOffset(self._counter_daq_task, 0) 
        
        #unread data in buffer will be overwritten
        daq.DAQmxSetReadOverWrite(self._counter_daq_task, daq.DAQmx_Val_DoNotOverwriteUnreadSamps) 
        
        daq.DAQmxStartTask(self._counter_daq_task) 
        
        return -1
        
    def get_counter(self, samples=None):
        """ Returns the current counts per second of the counter. 
        <blank line>
        @param int samples: if defined, number of samples to read in one go
        <blank line>
        @return float: the photon counts per second
        """
        
        if self._counter_daq_task == None:            
            self.logMsg('No counter running, call set_up_counter before reading it.', \
            messageType='error')
            return np.ones((samples,), dtype=np.uint32) * -1.
            
        if samples == None:
            samples = int(self._samples_number)
        else:
            samples = int(samples)
        
        count_data = np.empty((samples,), dtype=np.uint32) # count data will be written here in the NumPy array
        
        n_read_samples = daq.int32() #number of samples which were read will be stored here
        
        daq.DAQmxReadCounterU32(self._counter_daq_task,               #read from this task
                                samples,          #number of samples to read
                                self._RWTimeout,
                                count_data,     # write into this array (the suffix .ctypes.data is an attribute of the NumPy array, see NumPy doc for more info) 
                                samples,         # length of array to write into
                                daq.byref(n_read_samples),     # number of samples which were read (should be 1 obviously)
                                None)                           # Reserved for future use. Pass NULL(here None) to this parameter
        return count_data * self._clock_frequency   #normalize to counts per second
    
    def close_counter(self):
        """ Closes the counter and cleans up afterwards. 
        <blank line>
        @return int: error code (0:OK, -1:error)
        """
        
        daq.DAQmxStopTask(self._counter_daq_task)
        daq.DAQmxClearTask(self._counter_daq_task)
        self._counter_daq_task = None
        
        return 0
        
    def close_clock(self):
        """ Closes the clock and cleans up afterwards. 
        <blank line>
        @return int: error code (0:OK, -1:error)
        """
        
        daq.DAQmxStopTask(self._clock_daq_task)
        daq.DAQmxClearTask(self._clock_daq_task)
        self._clock_daq_task = None
        
        return 0