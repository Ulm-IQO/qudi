# -*- coding: utf-8 -*-

from logic.genericlogic import genericlogic
from collections import OrderedDict
import threading
import numpy as np
import time

class counterlogic(genericlogic):
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    
    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation}
        genericlogic.__init__(self, manager, name, config, state_actions, **kwargs)
        self._modclass = 'counterlogic'
        self._modtype = 'logic'
        ## declare connectors
        self.connector['in']['counter1'] = OrderedDict()
        self.connector['in']['counter1']['class'] = 'slowcounterinterface'
        self.connector['in']['counter1']['object'] = None
        
        self.connector['out']['counterlogic'] = OrderedDict()
        self.connector['out']['counterlogic']['class'] = 'counterlogic'
        

        self.logMsg('The following configuration was found.', 
                    messageType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        messageType='status')
                        
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
        self._saving = False
        
        self._counting_device = self.connector['in']['counter1']['object']
        print("Counting device is", self._counting_device)
        
#        self.testing()
    
    def testing(self):
        """ Testing method only relevant for debugging.
        """
        self.startme()
        for i in range (10):
            print (self.countdata[self._counting_samples-1:])
        self.stopme()
        
    def set_count_length(self, length = 300):
        """ Sets the length of the counted bins.
        
        @param int length: the length of the array to be set.
        
        @return int: error code (0:OK, -1:error)
        
        This makes sure, the counter is stopped first and restarted afterwards.
        """
        
        # do I need to restart the counter?
        restart = False
        
        # if the counter is running, stop it
        if self.running:
            restart = True
            self.stopme()
            while self.running:
                time.sleep(0.01)
                
        self._count_length = int(length)
        
        # if the counter was running, restart it
        if restart:
            self.startme()
        
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
        if self.running:
            restart = True
            self.stopme()
            while self.running:
                time.sleep(0.01)
                
        self._count_frequency = int(frequency)
        
        # if the counter was running, restart it
        if restart:
            self.startme()
        
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
        
        self._saving=True
        self._saving_stop_time=time.time()
        
        print ('Want to save data of length {0:d}, please implement'.format(len(self._data_to_save)))
        return 0
    
    def runme(self):
        """ The actual measurement method which is run in a thread.
        """
        
        # setting up the counter
        self._counting_device.set_up_clock(clock_frequency = self._count_frequency, clock_channel = '/Dev1/Ctr0')
        self._counting_device.set_up_counter(counter_channel = '/Dev1/Ctr1', photon_source= '/Dev1/PFI8')
        
        # initialising the data arrays
        self.countdata=np.zeros((self._count_length,))
        self.countdata_smoothed=np.zeros((self._count_length,))
        self.rawdata=np.zeros((self._counting_samples,))
        
        while True:
            # set a status variable, to signify the measurment is running
            self.running = True
            
            # check for aborts of the thread in break if necessary
            if self._my_stop_request.isSet():
                break
            
            # read the current counter value
            self.rawdata = self._counting_device.get_counter(samples=self._counting_samples)
            
            # if we don't want to use oversampling
            if self._binned_counting:
                # remember the new count data in circular array
                self.countdata[0] = np.average(self.rawdata)
                # move the array to the left to make space for the new data
                self.countdata=np.roll(self.countdata, -1)
                # also move the smoothing array
                self.countdata_smoothed = np.roll(self.countdata_smoothed, -1)
                # calculate the median and save it
                self.countdata_smoothed[-int(self._smooth_window_length/2)-1:]=np.median(self.countdata[-self._smooth_window_length:])
            # if oversampling is necessary
            else:
                self.countdata=np.roll(self.countdata, -self._counting_samples)
                self.countdata[-self._counting_samples:] = self.rawdata
                self.countdata_smoothed = np.roll(self.countdata_smoothed, -self._counting_samples)
                self.countdata_smoothed[-int(self._smooth_window_length/2)-1:]=np.median(self.countdata[-self._smooth_window_length:])
                
            # save the data if necessary
            if self._saving:
                # append tuple to data stream (timestamp, average counts)
                self._data_to_save.append(np.array((time.time()-self._saving_start_time, np.average(self.rawdata))))
        # switch the state variable off again
        self.running = False
        
        # close off the actual counter
        self._counting_device.close_counter()
        self._counting_device.close_clock()
