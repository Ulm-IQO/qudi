# -*- coding: utf-8 -*-
# unstable: Christoph Müller

from logic.GenericLogic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.Mutex import Mutex
from collections import OrderedDict
import numpy as np

class ConfocalLogic(GenericLogic):
    """unstable: Christoph Müller
    This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    signal_scan_lines_next = QtCore.Signal()
    signal_image_updated = QtCore.Signal()
    
    ## counter for scan_image    
    _scan_counter = 0

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
        
        self.zscan = False
        
        #locking for thread safety
        self.lock = Mutex()
        self.running = False
        self.stopRequested = False
                    
                       
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
        self.xy_resolution = 10
        self.z_resolution = 10
        
        self._scan_counter = 0         
        self.signal_scan_lines_next.connect(self.scan_line, QtCore.Qt.QueuedConnection)
        
        self.testing()
        
        # self.sigImageNext noch einbinden

    def testing(self):
        """ Debug method. """
        self.start_scanner()
        self.set_position(x = 1., y = 2., z = 3., a = 4.)
        self.start_scanning()
        self.kill_scanner()
        
    def set_clock_frequency(self):
        return 0
        
    def start_scanning(self):
        self._scan_counter = 0
        self.initialize_image()
        self.signal_scan_lines_next.emit()
        
    def initialize_image(self):
        
        x1, x2 = self.image_x_range[0], self.image_x_range[1]
        y1, y2 = self.image_y_range[0], self.image_y_range[1]
        z1, z2 = self.image_z_range[0], self.image_z_range[1]
        
        if x2 < x1:
            print('x2 should be larger than x1')
            return -1
        if self.zscan:
            self.X = np.linspace(x1, x2, self.xy_resolution)
            if z2 < z1:
                print('z2 should be larger than z1')
                return -1
            self.Z = np.linspace(z1, z2, self.z_resolution)
        else:
            if y2 < y1:
                print('y2 should be larger than y1')
                return -1
            if (x2-x1) >= (y2-y1):
                self.X = np.linspace(x1, x2, self.xy_resolution)
                self.Y = np.linspace(y1, y2, int(self.xy_resolution*(y2-y1)/(x2-x1)))
            else:
                self.Y = np.linspace(y1, y2, self.xy_resolution)
                self.X = np.linspace(x1, x2, int(self.xy_resolution*(x2-x1)/(y2-y1)))
        
        self.XL = self.X
        self.AL = np.zeros(self.XL.shape)
        self.return_XL = np.linspace(self.XL[-1], self.XL[0], self.return_slowness)
        self.return_AL = np.zeros(self.return_XL.shape)
        
        if self.zscan:
            self.image_vert_axis = self.Z
            self.xz_image = np.zeros((len(self.image_vert_axis), len(self.X)))
        else:
            self.image_vert_axis = self.Y
            self.xy_image = np.zeros((len(self.image_vert_axis), len(self.X)))        

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
        
        
    def scan_line(self):
        """scanning an image in either xz or xy
        
        @param bool zscan: (True: xz_scan, False: xy_scan) 
        
        """
        

#        self.return_image = np.zeros((len(image_vert_axis), len(X)))
#        self.signal_image_updated.emit()
        self.running = True
        
        if self.stopRequested:
            with self.lock:
                self.running = False
                self.stopRequested = False
                self.signal_image_updated.emit()
                return

        if self.zscan:
            YL = self._current_y * np.ones(self.X.shape)
            ZL = self._scan_counter * np.ones(self.X.shape)           #todo: tilt_correction
            return_YL = self._current_y * np.ones(self.return_XL.shape)
            return_ZL = ZL = self._scan_counter * np.ones(self.return_XL.shape)
        else:
            YL = self._scan_counter * np.ones(self.X.shape)
            ZL = self._current_z * np.ones(self.X.shape)      #todo: tilt_correction
            return_YL = self._scan_counter * np.ones(self.return_XL.shape)
            return_ZL = self._current_z * np.ones(self.return_XL.shape)
                
        line = np.vstack( (self.XL, YL, ZL, self.AL) )
            
        line_counts = self._scanning_device.scan_line(line)
        return_line = np.vstack( (self.return_XL, return_YL, return_ZL, self.return_AL) )
        return_line_counts = self._scanning_device.scan_line(return_line)
            
        if self.zscan:
                self.xz_image[self._scan_counter,:] = line_counts #position mit abspeichern noch implementieren
        else:
                self.xy_image[self._scan_counter,:] = line_counts #position mit abspeichern noch implementieren
        print('image update')
#            self.return_image[i,:] = return_line_counts
            #self.sigImageNext.emit()
        # call this again from event loop
        self.signal_image_updated.emit()
        self._scan_counter += 1
        
        if self._scan_counter < np.size(self.image_vert_axis):            
            self.signal_scan_lines_next.emit()
        else:
            self.running = False
            self.signal_image_updated.emit()
            self._scan_counter = 0 
            self.set_position(x = self._current_x, y = self._current_y, z = self._current_z, a = 0.)