# -*- coding: utf-8 -*-

from logic.GenericLogic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.Mutex import Mutex
from collections import OrderedDict
import numpy as np
import time

class CounterLogic(GenericLogic):
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    sigCounterUpdated = QtCore.Signal()
    sigCountNext = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)
        self._modclass = 'counterlogic'
        self._modtype = 'logic'

        ## declare connectors
        self.connector['in']['counter1'] = OrderedDict()
        self.connector['in']['counter1']['class'] = 'SlowCounterInterface'
        self.connector['in']['counter1']['object'] = None
        
        self.connector['out']['counterlogic'] = OrderedDict()
        self.connector['out']['counterlogic']['class'] = 'CounterLogic'
        
        self.connector['in']['savelogic'] = OrderedDict()
        self.connector['in']['savelogic']['class'] = 'SaveLogic'
        self.connector['in']['savelogic']['object'] = None
        
        #locking for thread safety
        self.threadlock = Mutex()

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
                        
        self._count_length = 300
        self._count_frequency = 50
        self._counting_samples = 1
        self._smooth_window_length = 10
        self._binned_counting = True
        
                        
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """
        self.countdata = np.zeros((self._count_length,))
        self.countdata_smoothed=np.zeros((self._count_length,))
        self.rawdata=np.zeros((self._counting_samples,))
        
        self.running = False
        self.stopRequested = False
        self._saving = False
        
        self._counting_device = self.connector['in']['counter1']['object']
#        print("Counting device is", self._counting_device)

        self._save_logic = self.connector['in']['savelogic']['object']

        #QSignals
        self.sigCountNext.connect(self.countLoopBody, QtCore.Qt.QueuedConnection)
        
    
    def set_counting_samples(self, samples = 1):
        """ Sets the length of the counted bins.
        
        @param int length: the length of the array to be set.
        
        @return int: error code (0:OK, -1:error)
        
        This makes sure, the counter is stopped first and restarted afterwards.
        """
        
        # do I need to restart the counter?
        restart = False
        
        # if the counter is running, stop it
        if self.getState() == 'locked':
            restart = True
            self.stopCount()
            while self.getState() == 'locked':
                time.sleep(0.01)
                
        self._counting_samples = int(samples)
        
        # if the counter was running, restart it
        if restart:
            self.startCount()
        
        return 0
        
    def set_count_length(self, length = 300):
        """ Sets the length of the counted bins.
        
        @param int length: the length of the array to be set.
        
        @return int: error code (0:OK, -1:error)
        
        This makes sure, the counter is stopped first and restarted afterwards.
        """
        
        # do I need to restart the counter?
        restart = False
        
        # if the counter is running, stop it
        if self.getState() == 'locked':
            restart = True
            self.stopCount()
            while self.getState() == 'locked':
                time.sleep(0.01)
                
        self._count_length = int(length)
        
        # if the counter was running, restart it
        if restart:
            self.startCount()
        
        return 0
        
    def set_count_frequency(self, frequency = 50):
        """ Sets the frequency with which the data is acquired.
        
        @param int frequency: the frequency of counting in Hz.
        
        @return int: error code (0:OK, -1:error)
        
        This makes sure, the counter is stopped first and restarted afterwards.
        """
        
        # do I need to restart the counter?
        restart = False
        
        # if the counter is running, stop it
        if self.getState() == 'locked':
            restart = True
            self.stopCount()
            while self.getState() == 'locked':
                time.sleep(0.01)
                
        self._count_frequency = int(frequency)
        
        # if the counter was running, restart it
        if restart:
            self.startCount()
        
        return 0
        
    def get_count_length(self):
        """ Returns the currently set length of the counting array.
        
        @return int: count_length
        """
        return self._count_length
    
    def get_count_frequency(self):
        """ Returns the currently set frequency of counting (resolution).
        
        @return int: count_frequency
        """
        return self._count_frequency
        
    def get_counting_samples(self):
        """ Returns the currently set number of samples counted per readout.
        
        @return int: counting_samples
        """
        return self._counting_samples
        
    def get_saving_state(self):
        """ Returns if the data is saved in the moment.
        
        @return bool: saving state
        """
        
        return self._saving
        
    def start_saving(self):
        """ Starts saving the data in a list.
        
        @return int: error code (0:OK, -1:error)
        """
        
        self._data_to_save=[]
        self._saving_start_time=time.time()
        self._saving=True
        return 0
    
    def save_data(self):
        """ Stops saving the data and writes it to a file.
        
        @return int: error code (0:OK, -1:error)
        """
        
        self._saving=False
        self._saving_stop_time=time.time()


        filepath = self._save_logic.get_path_for_module(module_name='Counter')
        filename = time.strftime('%Y-%m-%d_trace_from_%Hh%Mm%Ss.dat')
        
        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data = {'Time (s),Signal (Mcounts/s)':self._data_to_save}        

        # write the parameters:
        parameters = OrderedDict() 
        parameters['Start counting time (s)'] = self._saving_start_time
        parameters['Stop counting time (s)'] = self._saving_stop_time
        parameters['Stop counting time (s)'] = self._count_length
        parameters['Count frequency (Hz)'] = self._count_frequency
        parameters['Oversampling (Samples)'] = self._counting_samples
        parameters['Smooth Window Length (# of events)'] = self._smooth_window_length       
        
        self._save_logic.save_data(data, filepath, parameters=parameters, 
                                   filename=filename, as_text=True)#, as_xml=False, precision=None, delimiter=None)
                  
        self.logMsg('Counter Trace saved to:\n{0}'.format(filepath), msgType='status', importance=3)

        #print ('Want to save data of length {0:d}, please implement'.format(len(self._data_to_save)))
        
        return 0

    def startCount(self):
        
        # setting up the counter
        self._counting_device.set_up_clock(clock_frequency = self._count_frequency)
        self._counting_device.set_up_counter()
        
        # initialising the data arrays
        self.countdata=np.zeros((self._count_length,))
        self.countdata_smoothed=np.zeros((self._count_length,))
        self.rawdata=np.zeros((self._counting_samples,))
        self._sampling_data=np.ones((self._counting_samples,2))
        
        # set a lock, to signify the measurment is running
        self.lock()
        self.sigCountNext.emit()
 
    def stopCount(self):
        with self.threadlock:
            self.stopRequested = True

    def countLoopBody(self):
        """ The actual measurement method which is run in a thread.
        """
        
        # check for aborts of the thread in break if necessary 
        if self.stopRequested:
            with self.threadlock:
                # close off the actual counter
                self._counting_device.close_counter()
                self._counting_device.close_clock()
                # switch the state variable off again
                self.unlock()
                self.stopRequested = False
                return
        
        # read the current counter value
        self.rawdata = self._counting_device.get_counter(samples=self._counting_samples)
       
        # remember the new count data in circular array
        self.countdata[0] = np.average(self.rawdata)
        # move the array to the left to make space for the new data
        self.countdata=np.roll(self.countdata, -1)
        # also move the smoothing array
        self.countdata_smoothed = np.roll(self.countdata_smoothed, -1)
        # calculate the median and save it
        self.countdata_smoothed[-int(self._smooth_window_length/2)-1:]=np.median(self.countdata[-self._smooth_window_length:])
        
        # save the data if necessary
        if self._saving:
             # if oversampling is necessary
            if self._counting_samples > 1:
                self._sampling_data[:,0]=time.time()-self._saving_start_time
                self._sampling_data[:,1]=self.rawdata
                self._data_to_save.extend(list(self._sampling_data))
            # if we don't want to use oversampling
            else:
                # append tuple to data stream (timestamp, average counts)
                self._data_to_save.append(np.array((time.time()-self._saving_start_time, self.countdata[-1])))
        # call this again from event loop
        self.sigCounterUpdated.emit()
        self.sigCountNext.emit()
