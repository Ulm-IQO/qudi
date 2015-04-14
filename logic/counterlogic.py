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
        self._counting_samples = 1
        self._smooth_window_length = 10
        self._binned_counting = True
        
        self.running = False
                        
    def activation(self, e):
        self.countdata = np.zeros((self._count_length,))
        self.countdata_smoothed=np.zeros((self._count_length,))
        self._counting_device = self.connector['in']['counter1']['object']
        print("Counting device is", self._counting_device)
        
#        self.testing()
    
    def testing(self):
        self.startme()
        for i in range (10):
            print (self.countdata[self._counting_samples-1:])
        self.stopme()
        
    def set_count_length(self, length = 300):
        
        # do I need to restart the counter?
        restart = False
        
        # if the counter is running, stop it
        if self.running:
            restart = True
            self.stopme()
            while self.running:
                time.sleep(0.01)
                
        self._count_length = length
        
        # if the counter was running, restart it
        if restart:
            self.startme()
        
        return 0
        
    def get_count_length(self):
        return self._count_length
    
    def runme(self):
        
        self._counting_device.set_up_clock(clock_frequency = 50, clock_channel = '/Dev1/Ctr0')
        self._counting_device.set_up_counter(counter_channel = '/Dev1/Ctr1', photon_source= '/Dev1/PFI8')
        
        self.countdata=np.zeros((self._count_length,))
        self.countdata_smoothed=np.zeros((self._count_length,))
        
        while True:
            self.running = True
            if self._my_stop_request.isSet():
                break
            if self._binned_counting:
                self.countdata=np.roll(self.countdata, -1)
                self.countdata[-self._counting_samples:] = np.average(self._counting_device.get_counter(samples=self._counting_samples))
                self.countdata_smoothed = np.roll(self.countdata_smoothed, -1)
                self.countdata_smoothed[-int(self._smooth_window_length/2)-1:]=np.median(self.countdata[-self._smooth_window_length:])
            else:
                self.countdata=np.roll(self.countdata, -self._counting_samples)
                self.countdata[-self._counting_samples:] = self._counting_device.get_counter(samples=self._counting_samples)
                self.countdata_smoothed = np.roll(self.countdata_smoothed, -self._counting_samples)
                self.countdata_smoothed[-int(self._smooth_window_length/2)-1:]=np.median(self.countdata[-self._smooth_window_length:])
                
            
        self.running = False
        self._counting_device.close_counter()
        self._counting_device.close_clock()
