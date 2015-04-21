# -*- coding: utf-8 -*-
# unstable: Christoph Müller

from logic.GenericLogic import GenericLogic
from pyqtgraph.Qt import QtCore
from collections import OrderedDict
import numpy as np

class ConfocalLogic(GenericLogic):
    """unstable: Christoph Müller
    This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    sigImageNext = QtCore.Signal()

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
        
        self._clock_frequency = 50.
        self._clock_channel = '/Dev1/Ctr2'
        self._counter_channel = '/Dev1/Ctr3'
        self._photon_source= '/Dev1/PFI8'
        self._scanner_ao_channels = '/Dev1/AO0:3'
        self.return_slowness = 10
                       
                       
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """        
        self._scanning_device = self.connector['in']['confocalscanner1']['object']
        print("Counting device is", self._scanning_device)
        
        # self.sigImageNext noch einbinden


    def start_scanner(self):
        """setting up the scanner device
        """
        self._scanning_device.set_up_scanner_clock(self._clock_frequency, self._clock_channel)
        self._scanning_device.set_up_scanner(self._counter_channel, self._photon_source, self._scanner_ao_channels)
    
    
    def kill_scanner(self):
        """Closing the scanner device
        """
        self._scanning_device.close_scanner()
        self._scanning_device.close_scanner_clock()
        
        
    def go_to_pos(self, x = None, y = None, z = None, a = None):
        """Forwarding the desired new position from the GUI to the scanning device.
        
        @param float x: postion in x-direction (microns)
        @param float y: postion in y-direction (microns)
        @param float z: postion in z-direction (microns)
        @param float a: postion in a-direction (microns)
        """
        self._scanning_device.scanner_set_pos(x = x, y = y, z = z, a = a)
        
        
#    def scan_line(self):
#        minv=-10
#        maxv=10
#        res=100
#        line = np.vstack((np.linspace(minv,maxv,res),
#                          np.linspace(minv,maxv,res), 
#                          np.linspace(minv,maxv,res),
#                          np.linspace(minv,maxv,res)) )
#        self.counts_from_line = self._scanning_device.scan_line(voltages=line)
        
    def scan_image(self, curr_x = None, curr_y = None, curr_z = None, x1 = None, x2 = None, y1 = None, y2 = None, z1 = None, z2 = None, res = None, zres = None):
        """scanning an image
        
        @param float curr_x: current x-position of the scanner (microns)
        @param float curr_y: current y-position of the scanner (microns)
        @param float curr_z: current z-position of the scanner (microns)
        @param float curr_a: current a-position of the scanner (microns)
        @param float x1: start value image in x-direction (microns)
        @param float x2: stop value image in x-direction (microns)
        @param float y1: start value image in y-direction (microns)
        @param float y2: stop value image in y-direction (microns)
        @param float z1: start value image in z-direction (microns)
        @param float z2: stop value image in z-direction (microns)
        @param int res: resolution in xy-direction
        @param int zres: resolution in z-direction 
        """
        zscan = False
        # if zres = None: perform xy scan    , ifn zres != None: perform xz scan 
        
        if x2 < x1:
            print('x2 should be larger than x1')
            return -1
        if zres != None and res != None:
            X = np.linspace(x1, x2, res)
            if z2 < z1:
                print('z2 should be larger than z1')
                return -1
            Z = np.linspace(z1, z2, zres)
            zscan = True
        elif res != None:
            if y2 < y1:
                print('y2 should be larger than y1')
                return -1
            if (x2-x1) >= (y2-y1):
                X = np.linspace(x1, x2, res)
                Y = np.linspace(y1, y2, int(res*(y2-y1)/(x2-x1)))
            else:
                Y = np.linspace(y1, y2, res)
                X = np.linspace(x1, x2, int(res*(x2-x1)/(y2-y1)))
        else:
            print('I do not know wether I should scan xy or xz')
            return -1    # should that be here?
        
        if zscan:
            image_vert_axis = Z
        else:
            image_vert_axis = Y
        
        self.image = np.zeros((len(image_vert_axis), len(X)))
#        self.return_image = np.zeros((len(image_vert_axis), len(X)))
        
        for i,q in enumerate(image_vert_axis):
            # here threading?
        
            XL = X
            AL = np.zeros(X.shape)
            if zscan:
                YL = curr_y * np.ones(X.shape)
                ZL = q * np.ones(X.shape)           #todo: tilt_correction
            else:
                YL = q * np.ones(X.shape)
                ZL = curr_z * np.ones(X.shape)      #todo: tilt_correction
                
            line = np.stack( (XL, YL, ZL, AL) )
            
#            self._scanning_device.set_up_line(length = len(XL))   #passt das so?
            line_counts = self._scanning_device.scan_line(line)
            return_XL = np.linspace(XL[-1], XL[0], self.return_slowness)   #passt das so?
            return_line = np.stack( (return_XL, YL, ZL, AL) )
#            self._scanning_device.set_up_line(length = len(return_line))
            return_line_counts=self._scanning_device.scan_line(return_line)
            
            self.image[i,:] = line_counts
#            self.return_image[i,:] = return_line_counts
            #self.sigImageNext.emit()
        
        self.go_to_pos(x = curr_x, y = curr_y, z = curr_z, a = 0.)