# -*- coding: utf-8 -*-

from logic.GenericLogic import GenericLogic
from pyqtgraph.Qt import QtCore
from collections import OrderedDict
import numpy as np

class ConfocalTestLogic(GenericLogic):
    """This is the Interface class to define the controls for the simple 
    microwave hardware.
    """

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)
        self._modclass = 'counterlogic'
        self._modtype = 'logic'

        ## declare connectors
        self.connector['in']['confocalscanner1'] = OrderedDict()
        self.connector['in']['confocalscanner1']['class'] = 'ConfocalScannerInterface'
        self.connector['in']['confocalscanner1']['object'] = None
        
        self.connector['out']['scannerlogic'] = OrderedDict()
        self.connector['out']['scannerlogic']['class'] = 'ConfocalTestLogic'
        
        
        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
                        
        
                        
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """        
        self._scanning_device = self.connector['in']['confocalscanner1']['object']
        print("Scanning device is", self._scanning_device)

    def start_scanner(self):
        # setting up the scanner
        self._scanning_device.set_up_scanner_clock(clock_frequency = 50., clock_channel = '/Dev1/Ctr2')
        self._scanning_device.set_up_scanner(counter_channel = '/Dev1/Ctr3', photon_source= '/Dev1/PFI8', scanner_ao_channels = '/Dev1/AO0:3')
    
    
    def kill_scanner(self):
        self._scanning_device.close_scanner()
        self._scanning_device.close_scanner_clock()
        
    def scan_line(self):
        minv=-10
        maxv=10
        res=100
        line = np.vstack((np.linspace(minv,maxv,res),
                          np.linspace(minv,maxv,res), 
                          np.linspace(minv,maxv,res),
                          np.linspace(minv,maxv,res)) )
        self.counts_from_line = self._scanning_device.scan_line(voltages=line)
        
    def go_to_pos(self, x = None, y = None, z = None, a = None):
        self._scanning_device.scanner_set_position(x = x, y = y, z = z, a = a)