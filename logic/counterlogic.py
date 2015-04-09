# -*- coding: utf-8 -*-

from logic.genericlogic import genericlogic
import threading
import numpy as np

class counterlogic(genericlogic):
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    
    def __init__(self, manager, name, config, **kwargs):
        genericlogic.__init__(self, manager, name, configuation=config, **kwargs)
        self._modclass = 'counterlogic'
        self._modtype = 'logic'
        
        self.logMsg('The following configuration was found.', 
                    messageType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        messageType='status')
                        
        self._count_length = 300
        self._counting_samples = 10
        self.countdata=np.zeros((self._count_length,))
                        
        # very buggy and quite horrible way to get the niinterface class
        # Jan, please fix this
        from hardware.niinterface import niinterface
        self._counting_device=niinterface(manager, name, config)
        
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
            self.countdata[-self._counting_samples-1:] = \
            self._counting_device.get_counter(samples=self._counting_samples)
            
        self._counting_device.close_counter()
        self._counting_device.close_clock()