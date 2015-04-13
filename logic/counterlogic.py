# -*- coding: utf-8 -*-

from logic.genericlogic import genericlogic
from collections import OrderedDict
import threading
import numpy as np

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
        self._counting_samples = 10
                        
    def activation(self, e):
        self.countdata = np.zeros((self._count_length,))
        self._counting_device = self.connector['in']['counter1']['object']
        print("Counting device is", self._counting_device)
        
        self.testing()
    
    def testing(self):
        self.startme()
        for i in range (10):
            print (self.countdata[self._counting_samples-1:])
        self.stopme()
    
    def runme(self):
        
        self._counting_device.set_up_clock(clock_frequency = 100, clock_channel = '/Dev1/Ctr0')
        self._counting_device.set_up_counter(counter_channel = '/Dev1/Ctr1', photon_source= '/Dev1/PFI8')
        
        self.countdata=np.zeros((self._count_length,))
        
        while True:
            if threading.current_thread().stop_request.isSet():
                break
            self.countdata=np.roll(self.countdata, -self._counting_samples)
            self.countdata[-self._counting_samples:] = self._counting_device.get_counter(samples=self._counting_samples)
            
        self._counting_device.close_counter()
        self._counting_device.close_clock()
