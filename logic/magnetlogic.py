# -*- coding: utf-8 -*-

from logic.GenericLogic import GenericLogic
from collections import OrderedDict
import threading
import numpy as np
import time

class MagnetLogic(GenericLogic):
    """This is the Interface class to define the controls for the simple 
    magnet hardware.
    """
    
    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)
        self._modclass = 'magnetlogic'
        self._modtype = 'logic'
        ## declare connectors
        self.connector['in']['magnet'] = OrderedDict()
        self.connector['in']['magnet']['class'] = 'magnetstageinterface'
        self.connector['in']['magnet']['object'] = None
        
        self.connector['out']['magnetlogic'] = OrderedDict()
        self.connector['out']['magnetlogic']['class'] = 'MagnetLogic'
        

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')

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
        self.testing()
        
    
    def testing(self):
        """ Testing method only relevant for debugging.
        """
        self._magnet_device.step_x(10)
        print(self._magnet_device.get_pos())
        
    
    def runme(self):
        """ The actual measurement method which is run in a thread.
        """        
        pass
