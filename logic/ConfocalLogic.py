# -*- coding: utf-8 -*-
# unstable: Christoph Müller

from logic.GenericLogic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.Mutex import Mutex
from collections import OrderedDict
import numpy as np

class ConfocalLogic(GenericLogic):
    """unstable: Christoph Müller
    This is the Logic class for confocal scanning.
    """
    signal_scan_lines_next = QtCore.Signal()
    signal_image_updated = QtCore.Signal()
    
    # counter for scan_image    
    _scan_counter = 0

    def __init__(self, manager, name, config, **kwargs):
        # declare actions for state transitions
        state_actions = {'onactivate': self.activation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)
        self._modclass = 'confocallogic'
        self._modtype = 'logic'

        # declare connectors
        self.connector['in']['confocalscanner1'] = OrderedDict()
        self.connector['in']['confocalscanner1']['class'] = 'ConfocalScannerInterface'
        self.connector['in']['confocalscanner1']['object'] = None
        
        self.connector['out']['scannerlogic'] = OrderedDict()
        self.connector['out']['scannerlogic']['class'] = 'ConfocalLogic'
        

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
        
        #default values for clock frequency and slowness
        #slowness: steps during retrace line
        self._clock_frequency = 500.
        self.return_slowness = 100
        
        self._zscan = False
        
        #locking for thread safety
        self.lock = Mutex()
        
        self.running = False
        self.stopRequested = False
                    
                       
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        
        @parameter?????????
        """        
        self._scanning_device = self.connector['in']['confocalscanner1']['object']
        print("Scanning device is", self._scanning_device)
        
        
        #reads in the maximal scanning range
        self.x_range = self._scanning_device.get_position_range()[0]
        self.y_range = self._scanning_device.get_position_range()[1]
        self.z_range = self._scanning_device.get_position_range()[2]
        
        #sets the current position to the center of the maximal scanning range
        self._current_x = (self.x_range[0] + self.x_range[1]) / 2.
        self._current_y = (self.y_range[0] + self.y_range[1]) / 2.
        self._current_z = (self.z_range[0] + self.z_range[1]) / 2.
        self._current_a = 0.0
        
        #sets the size of the image to the maximal scanning range
        self.image_x_range = self.x_range
        self.image_y_range = self.y_range
        self.image_z_range = self.z_range
        
        #default values for the resolution of the scan
        self.xy_resolution = 10
        self.z_resolution = 10
        
          
        self._scan_counter=0
        #??????????   
        self.signal_scan_lines_next.connect(self._scan_line, QtCore.Qt.QueuedConnection)
        
        self.testing()
        
        
    def testing(self):
        """ Debug method. """
        pass
#        self.start_scanner()
#        self.set_position(x = 1., y = 2., z = 3., a = 4.)
#        self.start_scanning()
#        self.kill_scanner()
        
    def set_clock_frequency(self, clock_frequency):
        """Sets the frequency of the clock
        
        @param int clock_frequency: desired frequency of the clock 
        
        @return int: error code (0:OK, -1:error)
        """
        
        #checks if scanner is still running
        self._clock_frequency = int(clock_frequency)
        if not self.running:
            #Why kill scanner first?
            self.kill_scanner()
            self.start_scanner()
            return 0
        else:
            return -1
        
    def start_scanning(self, zscan = False):
        """Starts scanning
        
        @param bool zscan: zscan if true, xyscan if false
               
        """
        self._scan_counter = 0
        self._zscan=zscan
        self.initialize_image()
        self.start_scanner()
        self.signal_scan_lines_next.emit()
        
    def stop_scanning(self):
        """Stop the scan
        
        """
        with self.lock:
            self.stopRequested = True
        
    def initialize_image(self):
        """Initalization of the image           
        """
        
        #x1: x-start-value, x2: x-end-value
        x1, x2 = self.image_x_range[0], self.image_x_range[1]
        #y1: x-start-value, y2: x-end-value
        y1, y2 = self.image_y_range[0], self.image_y_range[1]
        #z1: x-start-value, z2: x-end-value
        z1, z2 = self.image_z_range[0], self.image_z_range[1]
        
        #Checks if the x-start and x-end value are ok    
        if x2 < x1:
            print('x2 should be larger than x1')
            return -1
         
            
        if self._zscan:
            #creates an array of evenly spaced numbers over the interval
            #x1, x2 and the spacing is equal to xy_resolution
            self._X = np.linspace(x1, x2, self.xy_resolution)
            #Checks if the z-start and z-end value are ok
            if z2 < z1:
                print('z2 should be larger than z1')
                return -1
            #creates an array of evenly spaced numbers over the interval
            #z1, z2 and the spacing is equal to z_resolution    
            self._Z = np.linspace(z1, z2, self.z_resolution)
        else:
            #Checks if the y-start and y-end value are ok
            if y2 < y1:
                print('y2 should be larger than y1')
                return -1
            
            #prevents distorion of the image
            if (x2-x1) >= (y2-y1):
                self._X = np.linspace(x1, x2, self.xy_resolution)
                self._Y = np.linspace(y1, y2, int(self.xy_resolution*(y2-y1)/(x2-x1)))
            else:
                self._Y = np.linspace(y1, y2, self.xy_resolution)
                self._X = np.linspace(x1, x2, int(self.xy_resolution*(x2-x1)/(y2-y1)))
        
        self._XL = self._X
        self._AL = np.zeros(self._XL.shape)
        
        #Arrays for retrace line
        self._return_XL = np.linspace(self._XL[-1], self._XL[0], self.return_slowness)
        self._return_AL = np.zeros(self._return_XL.shape)
        
        if self._zscan:
            self._image_vert_axis = self._Z
            #creats an image where each pixel will be [x,y,z,counts]
            self.xz_image = np.zeros((len(self._image_vert_axis), len(self._X), 4))  
        else:
            self._image_vert_axis = self._Y
            #creats an image where each pixel will be [x,y,z,counts]
            self.xy_image = np.zeros((len(self._image_vert_axis), len(self._X), 4))          

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
        
        @param float x: if defined, changes to postion in x-direction (microns)
        @param float y: if defined, changes to postion in y-direction (microns)
        @param float z: if defined, changes to postion in z-direction (microns)
        @param float a: if defined, changes to postion in a-direction (microns)
        
        @return int: error code (0:OK, -1:error)
        """
        
        #Changes the respective value
        if x != None:
            self._current_x = x
        if y != None:
            self._current_y = y
        if z != None:
            self._current_z = z
        
        #Checks if the scanner is still running
        if not self.running:
            self._scanning_device.scanner_set_position(x = self._current_x, 
                                                       y = self._current_y, 
                                                       z = self._current_z, 
                                                       a = self._current_a)
            return 0
        else:
            return -1
        
    
    def get_position(self):
        """Forwarding the desired new position from the GUI to the scanning device.
        
        @return int[]: Current position       
        """
        return [self._current_x, self._current_y, self._current_z]
        
        
    def _scan_line(self):
        """scanning an image in either xz or xy       
                
        """
        

#        self.return_image = np.zeros((len(image_vert_axis), len(X)))
#        self.signal_image_updated.emit()
        self.running = True
        
        
        #stops scanning
        if self.stopRequested:
            with self.lock:
                self.running = False
                self.stopRequested = False
                self.signal_image_updated.emit()
                return

        if self._zscan:
            YL = self._current_y * np.ones(self._X.shape)
            ZL = self._Z[self._scan_counter] * np.ones(self._X.shape)           #todo: tilt_correction
            return_YL = self._current_y * np.ones(self._return_XL.shape)
            return_ZL = ZL = self._scan_counter * np.ones(self._return_XL.shape)
        else:
            YL = self._Y[self._scan_counter] * np.ones(self._X.shape)
            ZL = self._current_z * np.ones(self._X.shape)      #todo: tilt_correction
            return_YL = self._scan_counter * np.ones(self._return_XL.shape)
            return_ZL = self._current_z * np.ones(self._return_XL.shape)
        
               
        line = np.vstack( (self._XL, YL, ZL, self._AL) )
            
        line_counts = self._scanning_device.scan_line(line)
        return_line = np.vstack( (self._return_XL, return_YL, return_ZL, self._return_AL) )
        return_line_counts = self._scanning_device.scan_line(return_line)
            
        if self._zscan:
                self.xz_image[self._scan_counter,:,0] = self._XL
                self.xz_image[self._scan_counter,:,1] = YL
                self.xz_image[self._scan_counter,:,2] = ZL
                self.xz_image[self._scan_counter,:,3] = line_counts
        else:
                self.xy_image[self._scan_counter,:,0] = self._XL
                self.xy_image[self._scan_counter,:,1] = YL
                self.xy_image[self._scan_counter,:,2] = ZL
                self.xy_image[self._scan_counter,:,3] = line_counts
        print('image update')
#            self.return_image[i,:] = return_line_counts
            #self.sigImageNext.emit()
        # call this again from event loop
        self.signal_image_updated.emit()
        self._scan_counter += 1
        
        if self._scan_counter < np.size(self._image_vert_axis):            
            self.signal_scan_lines_next.emit()
        else:
            self.running = False
            self.signal_image_updated.emit()
            self.set_position()
            