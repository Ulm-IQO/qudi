# -*- coding: utf-8 -*-
# unstable: Kay Jahnke

from core.Base import Base
from hardware.SlowCounterInterface import SlowCounterInterface
from hardware.ConfocalScannerInterface import ConfocalScannerInterface
from collections import OrderedDict

import PyDAQmx as daq
import numpy as np

class NICard(Base,SlowCounterInterface,ConfocalScannerInterface):
    """unstable: Kay Jahnke
	This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    
    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.testing}
        Base.__init__(self,
                    manager,
                    name,
                    config,
                    c_dict)
        self._modclass = 'niinterface'
        self._modtype = 'slowcounterinterface'
        
        self.connector['out']['counter'] = OrderedDict()
        self.connector['out']['counter']['class'] = 'SlowCounterInterface'
        
        self.connector['out']['confocalscanner'] = OrderedDict()
        self.connector['out']['confocalscanner']['class'] = 'ConfocalScannerInterface'
        
        
        self.logMsg('The following configuration was found.', 
                    msgType='status')
                    
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
                        
        self._max_counts = 1e7
        self._RWTimeout = 5
        self._counter_daq_task = None
        self._clock_daq_task = None
        self._scanner_clock_daq_task = None
        self._scanner_ao_task = None
        self._scanner_counter_daq_task = None
        self._line_length = None
        self._min_voltage = -10.
        self._max_voltage = 10.
        
        self.current_x = 0.
        self.current_y = 0.
        self.current_z = 0.
        self.current_a = 0.
        
        if 'clock_channel' in config.keys():
            self._clock_channel=config['clock_channel']
        else:
            self.logMsg('No clock_channel configured.', msgType='error')
            
        if 'counter_channel' in config.keys():
            self._counter_channel=config['counter_channel']
        else:
            self.logMsg('No counter_channel configured.', msgType='error')
            
        if 'photon_source' in config.keys():
            self._photon_source=config['photon_source']
        else:
            self.logMsg('No photon_source configured.', msgType='error')
            
        if 'clock_frequency' in config.keys():
            self._clock_frequency=config['clock_frequency']
        else:
            self._clock_frequency=100
            self.logMsg('No clock_frequency configured tanking 100 Hz instead.', \
            msgType='warning')
            
        if 'samples_number' in config.keys():
            self._samples_number=config['samples_number']
        else:
            self._samples_number=10
            self.logMsg('No samples_number configured tanking 10 instead.', \
            msgType='warning')
            
#        self.testing()
        
    def testing(self, e=None):
        print('Testing the NIInterface')
        self.set_up_scanner_clock(clock_frequency = self._clock_frequency, clock_channel = '/Dev1/Ctr0')
        self.set_up_scanner(counter_channel = '/Dev1/Ctr1', photon_source= '/Dev1/PFI8', scanner_ao_channels = '/Dev1/ao0:3')
        
#        print(self.scan_line(voltages=1))
        
        minv=-10
        maxv=10
        res=40
        line = np.vstack((np.linspace(minv,maxv,res),
                          np.linspace(minv,maxv,res), 
                          np.linspace(minv,maxv,res),
                          np.linspace(minv,maxv,res)) )
        for i in range(5):
            print(self.scan_line(voltages=line))
        self.close_scanner()
        self.close_scanner_clock()
        
################################## Counter ###################################
        
    def set_up_clock(self, clock_frequency = None, clock_channel = None):
        """ Configures the hardware clock of the NiDAQ card to give the timing. 
        
        @param float clock_frequency: if defined, this sets the frequency of the clock
        @param string clock_channel: if defined, this is the physical channel of the clock
        
        @return int: error code (0:OK, -1:error)
        """ 
        
        if self._clock_daq_task != None:            
            self.logMsg('Another clock is already running, close this one first.', \
            msgType='error')
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
        
        @param string counter_channel: if defined, this is the physical channel of the counter
        @param string photon_source: if defined, this is the physical channel where the photons are to count from
        @param string clock_channel: if defined, this specifies the clock for the counter
        
        @return int: error code (0:OK, -1:error)
        """
        
        if self._clock_daq_task == None and clock_channel == None:            
            self.logMsg('No clock running, call set_up_clock before starting the counter.', \
            msgType='error')
            return -1
        if self._counter_daq_task != None:            
            self.logMsg('Another counter is already running, close this one first.', \
            msgType='error')
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
                                        self._max_counts/2./self._clock_frequency,    #expected maximum value
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
        
        @param int samples: if defined, number of samples to read in one go
        
        @return float: the photon counts per second
        """
        
        if self._counter_daq_task == None:            
            self.logMsg('No counter running, call set_up_counter before reading it.', \
            msgType='error')
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
        
        @return int: error code (0:OK, -1:error)
        """
        
        daq.DAQmxStopTask(self._counter_daq_task)
        daq.DAQmxClearTask(self._counter_daq_task)
        self._counter_daq_task = None
        
        return 0
        
    def close_clock(self):
        """ Closes the clock and cleans up afterwards. 
        
        @return int: error code (0:OK, -1:error)
        """
        
        daq.DAQmxStopTask(self._clock_daq_task)
        daq.DAQmxClearTask(self._clock_daq_task)
        self._clock_daq_task = None
        
        return 0
        
############################ Confocal Scanner ################################

    def set_up_scanner_clock(self, clock_frequency = None, clock_channel = None):
        """ Configures the hardware clock of the NiDAQ card to give the timing. 
        
        @param float clock_frequency: if defined, this sets the frequency of the clock
        @param string clock_channel: if defined, this is the physical channel of the clock
        
        @return int: error code (0:OK, -1:error)
        """ 
        
        if self._scanner_clock_daq_task != None:            
            self.logMsg('Another clock is already running, close this one first.', \
            msgType='error')
            return -1
        
        self._scanner_clock_daq_task = daq.TaskHandle()  # create handle for task, this task will generate pulse signal for photon counting
        if clock_frequency != None:
            self._scanner_clock_frequency = float(clock_frequency)
        if clock_channel != None:
            self._scanner_clock_channel = clock_channel
        
        daq.DAQmxCreateTask('', daq.byref(self._scanner_clock_daq_task))    # create task for pulse_out, here the parameter self.pulse_out_task has to be passed by reference (passing a pointer) 
        daq.DAQmxCreateCOPulseChanFreq( self._scanner_clock_daq_task,      # the task to which to add the channels that this function creates
                            		    self._scanner_clock_channel,  # use this counter; the name to assign to the created channel
										'Clock Task',    # name to assign to channel (NIDAQ uses by default the physical channel name as the virtual channel name. If name is specified, then you must use the name when you refer to that channel in other NIDAQ functions)
										daq.DAQmx_Val_Hz, #units
										daq.DAQmx_Val_Low, #idle state
										0, #initial delay
										self._scanner_clock_frequency / 2.,   #pulse frequency, divide by 2 such that length of semi period = count_interval
										0.5 ) #duty cycle of pulses, 0.5 such that high and low duration are both = count_interval
        
        # set timing to continuous, i.e. set only the number of samples to 
        # acquire or generate without specifying timing
        daq.DAQmxCfgImplicitTiming( self._scanner_clock_daq_task,  #define task
                                    daq.DAQmx_Val_ContSamps,  #continuous running
                                    1000) #buffer length
                                    
        daq.DAQmxStartTask(self._scanner_clock_daq_task) 
                       
        return 0
        
    
    def set_up_scanner(self, counter_channel = None, photon_source = None, clock_channel = None, scanner_ao_channels = None):
        """ Configures the actual scanner with a given clock. 
        
        @param string counter_channel: if defined, this is the physical channel of the counter
        @param string photon_source: if defined, this is the physical channel where the photons are to count from
        @param string clock_channel: if defined, this specifies the clock for the counter
        
        @return int: error code (0:OK, -1:error)
        """
        
        if self._scanner_clock_daq_task == None and clock_channel == None:            
            self.logMsg('No clock running, call set_up_clock before starting the counter.', \
            msgType='error')
            return -1
        if self._scanner_counter_daq_task != None:            
            self.logMsg('Another counter is already running, close this one first.', \
            msgType='error')
            return -1
            
        if counter_channel != None:
            self._scanner_counter_channel = counter_channel
        if photon_source != None:
            self._photon_source = photon_source
        
        if clock_channel != None:
            self._my_scanner_clock_channel = clock_channel
        else: 
            self._my_scanner_clock_channel = self._scanner_clock_channel
            
        if scanner_ao_channels != None:
            self._scanner_ao_channels = scanner_ao_channels
        
        # init ao channels / task for scanner, should always be active
        # the type definition for the task, an unsigned integer datatype (uInt32):
        self._scanner_ao_task = daq.TaskHandle()
        
        daq.DAQmxCreateTask('', daq.byref(self._scanner_ao_task))
        
        # Assign the created task to an analog output voltage channel
        daq.DAQmxCreateAOVoltageChan(self._scanner_ao_task,           # add to this task
                                     self._scanner_ao_channels, 
                                     '',  # use sanncer ao_channels, name = ''
                                     self._min_voltage,          # min voltage
                                     self._max_voltage,           # max voltage
                                     daq.DAQmx_Val_Volts,'')       # units is Volt
        
        # set task timing to on demand, i.e. when demanded by software
        daq.DAQmxSetSampTimingType(self._scanner_ao_task, daq.DAQmx_Val_OnDemand)
        #self.set_scanner_command_length(self._DefaultAOLength)
        
        self._scanner_counter_daq_task = daq.TaskHandle()
        daq.DAQmxCreateTask('', daq.byref(self._scanner_counter_daq_task))
        
        daq.DAQmxCreateCIPulseWidthChan(self._scanner_counter_daq_task,    #add to this task
                                        self._scanner_counter_channel,  #use this counter
                                        '',  #name
                                        0,  #expected minimum value
                                        self._max_counts*self._scanner_clock_frequency,    #expected maximum value
                                        daq.DAQmx_Val_Ticks,     #units of width measurement, here photon ticks
                                        daq.DAQmx_Val_Rising, '') #start pulse width measurement on rising edge

        #set the pulses to counter self._trace_counter_in
        daq.DAQmxSetCIPulseWidthTerm(self._scanner_counter_daq_task, 
                                     self._scanner_counter_channel, 
                                     self._my_scanner_clock_channel+'InternalOutput')
                                     
        #set the timebase for width measurement as self._photon_source
        daq.DAQmxSetCICtrTimebaseSrc(self._scanner_counter_daq_task, 
                                     self._scanner_counter_channel, 
                                     self._photon_source )
                                     
        # set task timing to use a sampling clock
        daq.DAQmxSetSampTimingType( self._scanner_ao_task, daq.DAQmx_Val_SampClk)
        
        return 0
    
    def scanner_set_pos(self, x = None, y = None, z = None, a = None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).
        
        @param float x: postion in x-direction (volts)
        @param float y: postion in y-direction (volts)
        @param float z: postion in z-direction (volts)
        @param float a: postion in a-direction (volts)
        
        @return int: error code (0:OK, -1:error)
        """
        
        if x != None:
            self.current_x = x
        if y != None:
            self.current_y = y
        if z != None:
            self.current_z = z
        if a != None:
            self.current_a = a
            
        self._write_scanner_ao(voltages = \
            self.scanner_position_to_volt((self.current_x,
                                           self.current_y,
                                           self.current_z,
                                           self.current_a)), 
            start=True)
        
        return 0
        
    def _write_scanner_ao(self, voltages, length=1 ,start=False):
        """Writes a set of voltages to the analoque outputs.
        
        @param float[][4] voltages: array of 4-part tuples defining the voltage points
        @param int length: number of tuples to write
        @param bool start: write imediately (True) or wait for start of task (False)
        
        @return int: error code (0:OK, -1:error)
        """
        self._AONwritten = daq.int32()
        
        daq.DAQmxWriteAnalogF64(self._scanner_ao_task,
                                self._line_length,  # length of command
                                start, # start task immediately (True), or wait for software start (False)
                                self._RWTimeout,
                                daq.DAQmx_Val_GroupByChannel,
                                voltages,
                                daq.byref(self._AONwritten), None)
        
        return self._AONwritten.value
    
    def scanner_position_to_volt(self, positions = None):
        """ Converts a set of position pixels to acutal voltages.
        
        @param float[][4] positions: array of 4-part tuples defining the pixels
        
        @return float[][4]: array of 4-part tuples of corresponing voltages
        """
        
        if not isinstance( positions, (frozenset, list, set, tuple, np.ndarray, ) ):
            self.logMsg('Given voltage list is no array type.', \
            msgType='error')
            return np.array([-1.])
            
        return positions
        
        
    def set_up_line(self, length=100):
        """ Sets up the analoque output for scanning a line.
        
        @param int length: length of the line in pixel
        
        @return int: error code (0:OK, -1:error)
        """

        self._line_length = length
        
        if length < np.inf:
            daq.DAQmxCfgSampClkTiming(self._scanner_ao_task,   # set up sample clock for task timing
                                      self._my_scanner_clock_channel+'InternalOutput',       # use these pulses as clock
                                      self._scanner_clock_frequency, # maximum expected clock frequency
                                      daq.DAQmx_Val_Falling, 
                                      daq.DAQmx_Val_FiniteSamps, # generate sample on falling edge, generate finite number of samples
                                      self._line_length) # samples to generate
        
        # set timing for scanner pulse and count task.
        daq.DAQmxCfgImplicitTiming(self._scanner_counter_daq_task, 
                                   daq.DAQmx_Val_FiniteSamps, 
                                   self._line_length+1)
                                   
        # read samples from beginning of acquisition, do not overwrite
        daq.DAQmxSetReadRelativeTo(self._scanner_counter_daq_task, 
                                   daq.DAQmx_Val_CurrReadPos) 
        # do not read first sample
        daq.DAQmxSetReadOffset(self._scanner_counter_daq_task, 1)
        daq.DAQmxSetReadOverWrite(self._scanner_counter_daq_task, 
                                  daq.DAQmx_Val_DoNotOverwriteUnreadSamps) 
        
        return 0
        
    def scan_line(self, voltages = None):
        """ Scans a line and returns the counts on that line. 
        
        @param float[][4] voltages: array of 4-part tuples defining the voltage points
        
        @return float[]: the photon counts per second
        """
        
        if not isinstance( voltages, (frozenset, list, set, tuple, np.ndarray, ) ):
            self.logMsg('Given voltage list is no array type.', \
            msgType='error')
            return np.array([-1.])
                
        if len(voltages) != self._line_length:
            self.set_up_line(length=len(voltages))
        
        written_voltages = self._write_scanner_ao(voltages=\
            self.scanner_position_to_volt(voltages), 
            length=self._line_length, 
            start=False)
        
        #start tasks
        daq.DAQmxStartTask(self._scanner_ao_task)
        daq.DAQmxStartTask(self._scanner_counter_daq_task)
        
        daq.DAQmxWaitUntilTaskDone(self._scanner_counter_daq_task, self._RWTimeout)
        
        # count data will be written here
        self._scan_data = np.empty((self._line_length,), dtype=np.uint32)
        #number of samples which were read will be stored here
        n_read_samples = daq.int32() 
        daq.DAQmxReadCounterU32(self._scanner_counter_daq_task,   #read from this task
                                self._line_length,    #read number of "line_points" samples
                                self._RWTimeout,
                                self._scan_data, #write into this array
                                self._line_length,   #length of array to write into
                                daq.byref(n_read_samples), None)  #number of samples which were read

        daq.DAQmxStopTask(self._scanner_counter_daq_task)
        daq.DAQmxStopTask(self._scanner_ao_task)
        
        return self._scan_data
        
        
    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards. 
        
        @return int: error code (0:OK, -1:error)
        """
        
        daq.DAQmxStopTask(self._scanner_counter_daq_task)
        daq.DAQmxClearTask(self._scanner_counter_daq_task)
        self._scanner_counter_daq_task = None
        
        daq.DAQmxStopTask(self._scanner_ao_task)
        daq.DAQmxClearTask(self._scanner_ao_task)
        self._scanner_ao_task = None
        
        return 0
        
    def close_scanner_clock(self,power=0):
        """ Closes the clock and cleans up afterwards. 
        
        @return int: error code (0:OK, -1:error)
        """        
        
        daq.DAQmxStopTask(self._scanner_clock_daq_task)
        daq.DAQmxClearTask(self._scanner_clock_daq_task)
        self._scanner_clock_daq_task = None
        
        return 0
