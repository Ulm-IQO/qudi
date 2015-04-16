# -*- coding: utf-8 -*-

from logic.genericlogic import genericlogic
from collections import OrderedDict
import threading
import numpy as np
import time

class magnetlogic(genericlogic):
    """This is the Interface class to define the controls for the simple 
    magnet hardware.
    """
    
    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation}
        genericlogic.__init__(self, manager, name, config, state_actions, **kwargs)
        self._modclass = 'magnetlogic'
        self._modtype = 'logic'
        ## declare connectors
        self.connector['in']['magnet'] = OrderedDict()
        self.connector['in']['magnet']['class'] = 'magnetstageinterface'
        self.connector['in']['magnet']['object'] = None
        
        self.connector['out']['magnetlogic'] = OrderedDict()
        self.connector['out']['magnetlogic']['class'] = 'magnetlogic'
        

        self.logMsg('The following configuration was found.', 
                    messageType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        messageType='status')

#       Borders of magnet have to be defined in config                   
        self._x_min = 0.
        self._x_max = 100.
        self._y_min = 0.
        self._y_max = 100.
        self._z_min = 0.
        self._z_max = 100.        
        
        self._vel_x = 12
        self._vel_y = 12
        self._vel_z = 12
        self._vel_phi = 12


        
                        
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """
        
        self._magnet_device = self.connector['in']['magnet']['object']
        print("Magnet device is", self._magnet_device)
        
    
    def testing(self):
        """ Testing method only relevant for debugging.
        """
        self.startme()
        for i in range (10):
            print (self.countdata[self._counting_samples-1:])
        self.stopme()
        
    
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
