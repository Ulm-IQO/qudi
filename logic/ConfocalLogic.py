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
        
        self._clock_frequency = 500.
        self.return_slowness = 100
                    
                       
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """        
        self._scanning_device = self.connector['in']['confocalscanner1']['object']
        print("Scanning device is", self._scanning_device)
        
        self.x_range = self._scanning_device.get_position_range()[0]
        self.y_range = self._scanning_device.get_position_range()[1]
        self.z_range = self._scanning_device.get_position_range()[2]
        
        self._current_x = (self.x_range[0] + self.x_range[1]) / 2.
        self._current_y = (self.y_range[0] + self.y_range[1]) / 2.
        self._current_z = (self.z_range[0] + self.z_range[1]) / 2.
        self.image_x_range = self.x_range
        self.image_y_range = self.y_range
        self.image_z_range = self.z_range
        self.res = 100
        self.zres = 100
        
        self.testing()
        
        # self.sigImageNext noch einbinden

    def testing(self):
        """ Debug method. """
        self.start_scanner()
        self.set_position(x = 1, y = 2, z = 3)
        self.scan_image()
        self.kill_scanner()
        
    def set_clock_frequency(self):
        return 0

    def start_scanner(self):
        """setting up the scanner device
        """
        self._scanning_device.set_up_scanner_clock(clock_frequency = self._clock_frequency)
        self._scanning_device.set_up_scanner()
    
    
    def kill_scanner(self):
        """Closing the scanner device
        """
        self._scanning_device.close_scanner()
        self._scanning_device.close_scanner_clock()
        
        
    def set_position(self, x = None, y = None, z = None, a = None):
        """Forwarding the desired new position from the GUI to the scanning device.
        
        @param float x: postion in x-direction (microns)
        @param float y: postion in y-direction (microns)
        @param float z: postion in z-direction (microns)
        @param float a: postion in a-direction (microns)
        """
        self._scanning_device.scanner_set_position(x = x, y = y, z = z, a = a)
        
    
    def get_position(self):
        """Forwarding the desired new position from the GUI to the scanning device.
        
        """
        return [self._current_x, self._current_y, self._current_z]
        
        
    def scan_image(self, zscan = False):
        """scanning an image in either xz or xy
        
        @param bool zscan: (True: xz_scan, False: xy_scan) 
        """
       
        x1, x2 = self.image_x_range[0], self.image_x_range[1]
        y1, y2 = self.image_y_range[0], self.image_y_range[1]
        z1, z2 = self.image_z_range[0], self.image_z_range[1]
        
        if x2 < x1:
            print('x2 should be larger than x1')
            return -1
        if zscan:
            X = np.linspace(x1, x2, self.res)
            if z2 < z1:
                print('z2 should be larger than z1')
                return -1
            Z = np.linspace(z1, z2, self.zres)
        else:
            if y2 < y1:
                print('y2 should be larger than y1')
                return -1
            if (x2-x1) >= (y2-y1):
                X = np.linspace(x1, x2, self.res)
                Y = np.linspace(y1, y2, int(self.res*(y2-y1)/(x2-x1)))
            else:
                Y = np.linspace(y1, y2, self.res)
                X = np.linspace(x1, x2, int(self.res*(x2-x1)/(y2-y1)))
        
        if zscan:
            image_vert_axis = Z
        else:
            image_vert_axis = Y

        XL = X
        AL = np.zeros(X.shape)
        
        self.image = np.zeros((len(image_vert_axis), len(X)))
#        self.return_image = np.zeros((len(image_vert_axis), len(X)))
        
        for i,q in enumerate(image_vert_axis):
            # here threading?
        
            if zscan:
                YL = self._current_y * np.ones(X.shape)
                ZL = q * np.ones(X.shape)           #todo: tilt_correction
            else:
                YL = q * np.ones(X.shape)
                ZL = self._current_z * np.ones(X.shape)      #todo: tilt_correction
                
            line = np.vstack( (XL, YL, ZL, AL) )
            
            line_counts = self._scanning_device.scan_line(line)
            return_XL = np.linspace(XL[-1], XL[0], self.return_slowness)   #passt das so?
            return_line = np.vstack( (return_XL, YL, ZL, AL) )
            return_line_counts=self._scanning_device.scan_line(return_line)
            
            self.image[i,:] = line_counts
            print('image update')
#            self.return_image[i,:] = return_line_counts
            #self.sigImageNext.emit()
        
        self.set_position(x = self._current_x, y = self._current_y, z = self._current_z, a = 0.)