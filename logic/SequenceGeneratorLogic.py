# -*- coding: utf-8 -*-
# unstable: Nikolas Tomek

from logic.GenericLogic import GenericLogic
#from pyqtgraph.Qt import QtCore
#from core.util.Mutex import Mutex
from collections import OrderedDict
#import numpy as np
import time

class SequenceGeneratorLogic(GenericLogic):
    """unstable: Nikolas Tomek
    This is the Logic class for the pulse sequence generator.
    """    
    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)
        self._modclass = 'sequencegeneratorlogic'
        self._modtype = 'logic'

        ## declare connectors
#        self.connector['in']['pulsegenerator'] = OrderedDict()
#        self.connector['in']['pulsegenerator']['class'] = 'PulseGeneratorInterface'
#        self.connector['in']['pulsegenerator']['object'] = None
        
        self.connector['out']['sequencegenerator'] = OrderedDict()
        self.connector['out']['sequencegenerator']['class'] = 'SequenceGeneratorLogic'        

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
        
#        self._sequence_names = None
#        
#        self._binwidth_ns = 1.
#        self._number_of_laser_pulses = 100
#        
#        self.fluorescence_signal_start_bin = 0
#        self.fluorescence_signal_width_bins = 200
#        self.norm_start_bin = 2000
#        self.norm_width_bins = 200
#        
#        self.threadlock = Mutex()
#        
#        self.stopRequested = False
                      
                      
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """        
#        self._pulse_generator_device = self.connector['in']['pulsegenerator']['object']
#        self._save_logic = self.connector['in']['savelogic']['object']
        
        
    def pulse_generator_on(self):
        time.sleep(1)
        return
        
        
    def pulse_generator_off(self):
        time.sleep(1)
        return

    
    def get_sequence_names(self):
        names = ['rabi', 'hahn', 'xy8']
        return names

        
    def get_binwidth(self):
        binwidth_ns = 1000./950.
        return binwidth_ns

        
    def get_number_of_laser_pulses(self):
        numberoflasers = 100
        return numberoflasers
        
        
    def get_tau_vector(self):
        tau_vector = range(100)
        return tau_vector

        
    def get_laser_length(self):
        laser_length = 3800 # 4 us
        return laser_length

        