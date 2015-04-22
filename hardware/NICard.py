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
        self._modclass = 'nicard'
        self._modtype = 'slowcounterinterface'
        
        self.connector['out']['counter'] = OrderedDict()
        self.connector['out']['counter']['class'] = 'SlowCounterInterface'
        
        self.connector['out']['confocalscanner'] = OrderedDict()
        self.connector['out']['confocalscanner']['class'] = 'ConfocalScannerInterface'
        
#        # checking for the right configuration
#        for key in config.keys():
#            print('{}: {}'.format(key,config[key]))
                        
        self._max_counts = 3e7
        self._RWTimeout = 5
        self._counter_daq_task = None
        self._clock_daq_task = None
        self._scanner_clock_daq_task = None
        self._scanner_ao_task = None
        self._scanner_counter_daq_task = None
        self._line_length = None
        self._voltage_range = [-10., 10.]
        
        self._position_range=[[0., 100.], [0., 100.], [0., 100.], [0., 100.]]
        
        self._current_position = [0., 0., 0., 0.]
        
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
            self.logMsg('No clock_frequency configured tanking 100 Hz instead.', \
            msgType='warning')
            
        if 'scanner_clock_frequency' in config.keys():
            self._scanner_clock_frequency=config['scanner_clock_frequency']
        else:
            self._scanner_clock_frequency=100
            self.logMsg('No scanner_clock_frequency configured tanking 100 Hz instead.', \
            msgType='warning')
            
        if 'samples_number' in config.keys():
            self._samples_number=config['samples_number']
        else:
            self._samples_number=10
            self.logMsg('No samples_number configured tanking 10 instead.', \
            msgType='warning')
            
        if 'scanner_ao_channels' in config.keys():
            self._scanner_ao_channels=config['scanner_ao_channels']
        else:
            self.logMsg('No scanner_ao_channels configured.', msgType='error')
            
        if 'x_range' in config.keys():
            if float(config['x_range'][0]) < float(config['x_range'][1]):
                self._position_range[0]=[float(config['x_range'][0]),float(config['x_range'][1])]
            else:
                self.logMsg('Configuration ({}) of x_range incorrect, tanking [0,100] instead.'.format(config['x_range']), \
                msgType='warning')                
        else:
            self.logMsg('No x_range configured tanking [0,100] instead.', \
            msgType='warning')
            
        if 'y_range' in config.keys():
            if float(config['y_range'][0]) < float(config['y_range'][1]):
                self._position_range[1]=[float(config['y_range'][0]),float(config['y_range'][1])]
            else:
                self.logMsg('Configuration ({}) of y_range incorrect, tanking [0,100] instead.'.format(config['y_range']), \
                msgType='warning')                
        else:
            self.logMsg('No y_range configured tanking [0,100] instead.', \
            msgType='warning')
            
        if 'z_range' in config.keys():
            if float(config['z_range'][0]) < float(config['z_range'][1]):
                self._position_range[2]=[float(config['z_range'][0]),float(config['z_range'][1])]
            else:
                self.logMsg('Configuration ({}) of z_range incorrect, tanking [0,100] instead.'.format(config['z_range']), \
                msgType='warning')                
        else:
            self.logMsg('No z_range configured tanking [0,100] instead.', \
            msgType='warning')
            
        if 'a_range' in config.keys():
            if float(config['a_range'][0]) < float(config['a_range'][1]):
                self._position_range[3]=[float(config['a_range'][0]),float(config['a_range'][1])]
            else:
                self.logMsg('Configuration ({}) of a_range incorrect, tanking [0,100] instead.'.format(config['a_range']), \
                msgType='warning')                
        else:
            self.logMsg('No a_range configured tanking [0,100] instead.', \
            msgType='warning')
            
        if 'voltage_range' in config.keys():
            if float(config['voltage_range'][0]) < float(config['voltage_range'][1]):
                self._voltage_range=[float(config['voltage_range'][0]),float(config['voltage_range'][1])]
            else:
                self.logMsg('Configuration ({}) of voltage_range incorrect, tanking [-10,10] instead.'.format(config['voltage_range']), \
                msgType='warning')                
        else:
            self.logMsg('No voltage_range configured tanking [-10,10] instead.', \
            msgType='warning')
            
#        self.testing()
        
    def testing(self, e=None):
        pass
#        minv=0
#        maxv=100
#        res=20
#        line = np.vstack((np.linspace(minv,maxv,res),
#                          np.linspace(minv,maxv,res), 
#                          np.linspace(minv,maxv,res),
#                          np.linspace(minv,maxv,res)) )
#        print (line)
#        print(self._scanner_position_to_volt(positions = line))
        
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
        
        return 0
        
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

    def get_position_range(self):
        """ Returns the physical range of the scanner.
        
        @return float [4][2]: array of 4 ranges with an array containing lower and upper limit
        """ 
        return self._position_range
        
    def set_position_range(self, myrange=[[0,1],[0,1],[0,1],[0,1]]):
        """ Sets the physical range of the scanner.
        
        @param float [4][2] myrange: array of 4 ranges with an array containing lower and upper limit
        
        @return int: error code (0:OK, -1:error)
        """ 
        
        if not isinstance( myrange, (frozenset, list, set, tuple, np.ndarray, ) ):
            self.logMsg('Given range is no array type.', \
            msgType='error')
            return -1
            
        if len(myrange) != 4:
            self.logMsg('Given range should have dimension 4, but has {0:d} instead.'.format(len(myrange)), \
            msgType='error')
            return -1
            
        for pos in myrange:
            if len(pos) != 2:
                self.logMsg('Given range limit {1:d} should have dimension 2, but has {0:d} instead.'.format(len(pos),pos), \
                msgType='error')
                return -1
            if pos[0]>pos[1]:
                self.logMsg('Given range limit {0:d} has the wrong order.'.format(pos), \
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
            self.logMsg('Given range is no array type.', \
            msgType='error')
            return -1
            
        if len(myrange) != 2:
            self.logMsg('Given range should have dimension 2, but has {0:d} instead.'.format(len(myrange)), \
            msgType='error')
            return -1
            
        if myrange[0]>myrange[1]:
            self.logMsg('Given range limit {0:d} has the wrong order.'.format(myrange), \
            msgType='error')
            return -1
                
        self._voltage_range = myrange    
            
        return 0

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
        @param string scanner_ao_channels: if defined, this specifies the analoque output channels
        
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
                                     self._voltage_range[0],          # min voltage
                                     self._voltage_range[1],           # max voltage
                                     daq.DAQmx_Val_Volts,'')       # units is Volt
        
        # set task timing to on demand, i.e. when demanded by software
        daq.DAQmxSetSampTimingType(self._scanner_ao_task, daq.DAQmx_Val_OnDemand)
        #self.set_scanner_command_length(self._DefaultAOLength)
        
        self._scanner_counter_daq_task = daq.TaskHandle()
        daq.DAQmxCreateTask('', daq.byref(self._scanner_counter_daq_task))
        
        # TODO: change this to DAQmxCreateCISemiPeriodChan
        daq.DAQmxCreateCISemiPeriodChan(self._scanner_counter_daq_task,    #add to this task
                                        self._scanner_counter_channel,  #use this counter
                                        '',  #name
                                        0,  #expected minimum value
                                        self._max_counts/self._scanner_clock_frequency,    #expected maximum value
                                        daq.DAQmx_Val_Ticks,     #units of width measurement, here photon ticks
                                        '')

        #set the pulses to counter self._trace_counter_in
        daq.DAQmxSetCISemiPeriodTerm(self._scanner_counter_daq_task, 
                                     self._scanner_counter_channel, 
                                     self._my_scanner_clock_channel+'InternalOutput')
                                     
        #set the timebase for width measurement as self._photon_source
        daq.DAQmxSetCICtrTimebaseSrc(self._scanner_counter_daq_task, 
                                     self._scanner_counter_channel, 
                                     self._photon_source )
        
        return 0
    
    def scanner_set_position(self, x = None, y = None, z = None, a = None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).
        
        @param float x: postion in x-direction (volts)
        @param float y: postion in y-direction (volts)
        @param float z: postion in z-direction (volts)
        @param float a: postion in a-direction (volts)
        
        @return int: error code (0:OK, -1:error)
        """
        
        if x != None:
            if x < self._position_range[0][0] or x > self._position_range[0][1]:                
                self.logMsg('You want to set x out of range: {0:f}.'.format(x), 
                            msgType='error')
                return -1
            self._current_position[0] = np.float(x)
            
        if y != None:
            if y < self._position_range[1][0] or y > self._position_range[1][1]:                
                self.logMsg('You want to set y out of range: {0:f}.'.format(y), 
                            msgType='error')
                return -1
            self._current_position[1] = np.float(y)
            
        if z != None:
            if z < self._position_range[2][0] or z > self._position_range[2][1]:                
                self.logMsg('You want to set z out of range: {0:f}.'.format(z), 
                            msgType='error')
                return -1
            self._current_position[2] = np.float(z)
            
        if a != None:
            if a < self._position_range[3][0] or a > self._position_range[3][1]:                
                self.logMsg('You want to set a out of range: {0:f}.'.format(a), 
                            msgType='error')
                return -1
            self._current_position[3] = np.float(a)
            
        my_position = np.vstack(self._current_position)
        self._write_scanner_ao(voltages = \
            self._scanner_position_to_volt(my_position), 
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
                                length,  # length of command
                                start, # start task immediately (True), or wait for software start (False)
                                self._RWTimeout,
                                daq.DAQmx_Val_GroupByChannel,
                                voltages,
                                daq.byref(self._AONwritten), None)
        
        return self._AONwritten.value
    
    def _scanner_position_to_volt(self, positions = None):
        """ Converts a set of position pixels to acutal voltages.
        
        @param float[][4] positions: array of 4-part tuples defining the pixels
        
        @return float[][4]: array of 4-part tuples of corresponing voltages
        """
        
        if not isinstance( positions, (frozenset, list, set, tuple, np.ndarray, ) ):
            self.logMsg('Given voltage list is no array type.', \
            msgType='error')
            return np.array([-1.,-1.,-1.,-1.])
        
        volts = np.vstack( ( \
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
        return volts
        
        
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
                                   2*self._line_length+1)
                                   
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
        
        if np.shape(voltages)[1] != self._line_length:
            self.set_up_line(np.shape(voltages)[1])
            
        # set task timing to use a sampling clock
        daq.DAQmxSetSampTimingType( self._scanner_ao_task, daq.DAQmx_Val_SampClk)
        
        written_voltages = self._write_scanner_ao(voltages=\
            self._scanner_position_to_volt(voltages), 
            length=self._line_length, 
            start=False)
        
        print('written samples: {0:d} of {1:d}'.format(written_voltages,np.shape(voltages)[1]))
        
        #start tasks
        daq.DAQmxStartTask(self._scanner_ao_task)
        daq.DAQmxStartTask(self._scanner_counter_daq_task)
        
        daq.DAQmxWaitUntilTaskDone(self._scanner_counter_daq_task, self._RWTimeout*self._line_length)
        
        # count data will be written here
        self._scan_data = np.empty((2*self._line_length,), dtype=np.uint32)
        #number of samples which were read will be stored here
        n_read_samples = daq.int32() 
        daq.DAQmxReadCounterU32(self._scanner_counter_daq_task,   #read from this task
                                2*self._line_length,    #read number of "line_points" samples
                                self._RWTimeout,
                                self._scan_data, #write into this array
                                2*self._line_length,   #length of array to write into
                                daq.byref(n_read_samples), None)  #number of samples which were read

        daq.DAQmxStopTask(self._scanner_counter_daq_task)
        daq.DAQmxStopTask(self._scanner_ao_task)
        
        # set task timing to on demand, i.e. when demanded by software
        daq.DAQmxSetSampTimingType(self._scanner_ao_task, daq.DAQmx_Val_OnDemand)
        
        
        self._real_data = np.empty((self._line_length,), dtype=np.uint32)
        self._real_data = self._scan_data[::2]
        self._real_data += self._scan_data[1::2]
        
        return self._real_data*(self._scanner_clock_frequency*0.5)
        
        
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
