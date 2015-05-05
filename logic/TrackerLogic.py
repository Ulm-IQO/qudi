# -*- coding: utf-8 -*-
# unstable: Kay Jahnke

from logic.GenericLogic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.Mutex import Mutex
from collections import OrderedDict
import numpy as np
import time

class TrackPoint(object):
    """ unstable: Kay Jahnke    
    The actual individual trackpoint is saved in this generic object.
    """
    
    def __init__(self, point = None, name=None):
        self._position_time_trace=[]
        self._name = time.strftime('Point_%Y%m%d_%M%S')
        
        if point != None:
            if len(point) != 3:
                self.logMsg('Length of set trackpoint is not 3.', 
                             msgType='error')
            self._position_time_trace.append(np.array([time.time(),point[0],point[1],point[2]]))
        if name != None:
            self._name=name
                
    def set_next_point(self, point = None):
        """ Adds another trackpoint.
        
        @param float[3] point: position coordinates of the trackpoint
        
        @return int: error code (0:OK, -1:error)
        """
        if point != None:
            if len(point) != 3:
                self.logMsg('Length of set trackpoint is not 3.', 
                             msgType='error')
                return -1
            self._position_time_trace.append(np.array([time.time(),point[0],point[1],point[2]]))
        else:
            return -1
    
    def get_last_point(self):
        """ Returns the most current trackpoint.
        
        @return float[3]: the position of the last point
        """
        if len(self._position_time_trace) > 0:
            return self._position_time_trace[-1][1:]
        else:
            return [-1.,-1.,-1.]
            
    def set_name(self, name= None):
        """ Sets the name of the trackpoint.
        
        @param string name: name to be set.
        
        @return int: error code (0:OK, -1:error)
        """
        
        if len(self._position_time_trace) > 0:
            self._name = time.strftime('Point_%Y%m%d_%M%S%',self._position_time_trace[0][0])
        else:
            self._name = time.strftime('Point_%Y%m%d_%M%S%')
        if name != None:
            self._name=name
            
    def get_name(self):
        """ Returns the name of the trackpoint.
        
        @return string: name
        """
        return self._name
        
    def get_trace(self): #instead of "trace": drift_log, history, 
        """ Returns the whole position time trace as array.
        
        @return float[][4]: the whole position time trace
        """
        
        return np.array(self._position_time_trace)
        
    def delete_last_point(self):
        """ Delete the last poitn in the trace.
        
        @return float[4]: the point just deleted.
        """
        
        if len(self._position_time_trace) > 0:
            return self._position_time_trace.pop()
        else:
            return [-1.,-1.,-1.,-1.]
    
    
                

class TrackerLogic(GenericLogic):
    """unstable: Christoph Müller
    This is the Logic class for refocussing on and tracking bright features in the confocal scan.
    """
    signal_scan_xy_line_next = QtCore.Signal()
    signal_image_updated = QtCore.Signal()
    signal_refocus_finished = QtCore.Signal()
    

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)
        self._modclass = 'trackerlogic'
        self._modtype = 'logic'

        ## declare connectors
        self.connector['in']['confocalscanner1'] = OrderedDict()
        self.connector['in']['confocalscanner1']['class'] = 'ConfocalScannerInterface'
        self.connector['in']['confocalscanner1']['object'] = None
        self.connector['in']['fitlogic'] = OrderedDict()
        self.connector['in']['fitlogic']['class'] = 'FitLogic'
        self.connector['in']['fitlogic']['object'] = None
        self.connector['in']['scannerlogic'] = OrderedDict()
        self.connector['in']['scannerlogic']['class'] = 'ConfocalLogic'
        self.connector['in']['scannerlogic']['object'] = None
        
        self.connector['out']['trackerlogic'] = OrderedDict()
        self.connector['out']['trackerlogic']['class'] = 'TrackerLogic'
        

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
        
        self.track_point_list = dict()
                                
        #default values for clock frequency and slowness
        #slowness: steps during retrace line
        self._clock_frequency = 200
        self.return_slowness = 20
        
        self.refocus_XY_size =  2
        self.refocus_XY_step = 0.2
        self.refocus_Z_size = 5
        self.refocus_Z_step = 0.5
        
        #locking for thread safety
        self.threadlock = Mutex()
        
        self.running = False
        self.stopRequested = False
                       
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """        
        self._scanning_device = self.connector['in']['confocalscanner1']['object']
        print("Scanning device is", self._scanning_device)
        self._fit_logic = self.connector['in']['fitlogic']['object']
        self._confocal_logic = self.connector['in']['scannerlogic']['object']
        
        self.x_range = self._scanning_device.get_position_range()[0]
        self.y_range = self._scanning_device.get_position_range()[1]
        self.z_range = self._scanning_device.get_position_range()[2]
        
        crosshair=TrackPoint(point=[0,0,0], name='crosshair')
        self.track_point_list[crosshair.get_name()] = crosshair
        
        self._trackpoint_x = 0.
        self._trackpoint_y = 0.
        self._trackpoint_z = 0.
        
        self._max_offset = 3.
        
        self._scan_counter = 0
        
        self.signal_scan_xy_line_next.connect(self._refocus_line, QtCore.Qt.QueuedConnection)

        self._initialize_xy_refocus_image()
        self._initialize_z_refocus_image()
        
#        self.testing()
        
    def testing(self):
        self.start_refocus()
        name=self.add_trackpoint()
        print (name)
        
        self.start_refocus(trackpointname=name)
        
    def set_clock_frequency(self, clock_frequency):
        """Sets the frequency of the clock
        
        @param int clock_frequency: desired frequency of the clock 
        
        @return int: error code (0:OK, -1:error)
        """
        
        self._clock_frequency = int(clock_frequency)
        #checks if scanner is still running
        if self.getState() == 'locked':
            return -1
        else:
            return 0
            
    def add_trackpoint(self):
        
        new_track_point=TrackPoint(point=self._confocal_logic.get_position())
        self.track_point_list[new_track_point.get_name()] = new_track_point
        
        return new_track_point.get_name()
        
    def start_refocus(self, trackpointname=None):
        """Starts refocus        
        """
        print('start refocusing')
        if trackpointname != None:
            print (trackpointname)
            if trackpointname in self.track_point_list.keys():
                self._trackpoint_x, self._trackpoint_y, self._trackpoint_z = \
                    self.track_point_list[trackpointname].get_last_point()
            else:
                self.logMsg('The requested Trackpoint ({}) does not exist.'.format(trackpointname), 
                msgType='error')
                self.signal_refocus_finished.emit()
                return -1
        else:
            self._trackpoint_x, self._trackpoint_y, self._trackpoint_z = \
                    self._confocal_logic.get_position()
        print (self._trackpoint_x, self._trackpoint_y, self._trackpoint_z)
        self.lock()
        self._scan_counter = 0
        self._initialize_xy_refocus_image()
        self._initialize_z_refocus_image()
        self.start_scanner()
        
#        self.unlock()
#        return -1
        
        self.signal_scan_xy_line_next.emit()
        
        
    def stop_refocus(self):
        """Stops refocus        
        """
        with self.threadlock:
            self.stopRequested = True
        
        
    def _initialize_xy_refocus_image(self):
        """Initialisation of the xy refocus image
        """
        self._scan_counter = 0
        
        x0 = self._trackpoint_x
        y0 = self._trackpoint_y
        
        xmin = np.clip(x0 - 0.5 * self.refocus_XY_size, self.x_range[0], self.x_range[1])
        xmax = np.clip(x0 + 0.5 * self.refocus_XY_size, self.x_range[0], self.x_range[1])
        ymin = np.clip(y0 - 0.5 * self.refocus_XY_size, self.y_range[0], self.y_range[1])
        ymax = np.clip(y0 + 0.5 * self.refocus_XY_size, self.y_range[0], self.y_range[1])
        
        self._X_values = np.arange(xmin, xmax + self.refocus_XY_step, self.refocus_XY_step)
        self._Y_values = np.arange(ymin, ymax + self.refocus_XY_step, self.refocus_XY_step)
        self._Z_values = self._trackpoint_z * np.ones(self._X_values.shape)
        self._A_values = np.zeros(self._X_values.shape)
        self._return_X_values = np.arange(xmax, xmin - self.refocus_XY_step, -self.refocus_XY_step)
        
        self.xy_refocus_image = np.zeros((len(self._Y_values), len(self._X_values), 4))

        
        
    def _refocus_line(self):
        """Scanning one line of the xy refocus image
        """
        
        #stops scanning
        if self.stopRequested:
            with self.threadlock:
                self.stopRequested = False
                self.kill_scanner()
                self.unlock()
                self.signal_image_updated.emit()
                return
                
        self.refocus_x = self._trackpoint_x
        self.refocus_y = self._trackpoint_y
                
        X_line = self._X_values
        Y_line = self._Y_values[self._scan_counter] * np.ones(X_line.shape)
        Z_line = self._Z_values    #todo: tilt_correction
        A_line = self._A_values
        return_X_line = self._return_X_values
        
        if self._scan_counter == 0:
            start_line = np.vstack( (np.linspace(self._trackpoint_x, \
                                                 self._X_values[0], \
                                                 self.return_slowness), \
                                     np.linspace(self._trackpoint_y, \
                                                 self._Y_values[0], \
                                                 self.return_slowness), \
                                     np.linspace(self._trackpoint_z, \
                                                 self._Z_values[0], \
                                                 self.return_slowness), \
                                     np.linspace(0, \
                                                 self._A_values[0], \
                                                 self.return_slowness) ))
            
            start_line_counts = self._scanning_device.scan_line(start_line)
            
        line = np.vstack( (X_line, Y_line, Z_line, A_line) )            
        line_counts = self._scanning_device.scan_line(line)
        return_line = np.vstack( (return_X_line, Y_line, Z_line, A_line) )
        return_line_counts = self._scanning_device.scan_line(return_line)                
        
        self.xy_refocus_image[self._scan_counter,:,0] = self._X_values
        self.xy_refocus_image[self._scan_counter,:,1] = Y_line
        self.xy_refocus_image[self._scan_counter,:,2] = self._Z_values
        self.xy_refocus_image[self._scan_counter,:,3] = line_counts
        
        self.signal_image_updated.emit()
        self._scan_counter += 1
        
        if self._scan_counter < np.size(self._Y_values):            
            self.signal_scan_xy_line_next.emit()
        else:
            #x,y-fit
            fit_x, fit_y = np.meshgrid(self._X_values, self._Y_values)
            xy_fit_data = self.xy_refocus_image[:,:,3].ravel()
            error,amplitude,x_zero,y_zero,sigma_x,sigma_y,theta,offset = self._fit_logic.twoD_gaussian_estimator(x_axis=fit_x, y_axis=fit_y,  data=xy_fit_data)
            if error == -1:
                self.logMsg('error in initial_guess xy fit.', \
                            msgType='error')
                #hier abbrechen
            else:
                initial_guess_xy = (amplitude, x_zero, y_zero, sigma_x, sigma_y, theta, offset)
            
            error, twoD_values = self._fit_logic.make_fit(function=self._fit_logic.twoD_gaussian_function,axes=(fit_x, fit_y),data=xy_fit_data,initial_guess=initial_guess_xy)
            if error == -1:
                self.logMsg('error in 2D Gaussian Fit.', \
                            msgType='error')
                self.refocus_x = self._trackpoint_x
                self.refocus_y = self._trackpoint_y
                #hier abbrechen
            else:
                if abs(self._trackpoint_x - twoD_values[1]) < self._max_offset and abs(self._trackpoint_x - twoD_values[1]) < self._max_offset:
                    if twoD_values[1] >= self.x_range[0] and twoD_values[1] <= self.x_range[1]:
                        if twoD_values[2] >= self.y_range[0] and twoD_values[2] <= self.y_range[1]:
                            self.refocus_x = twoD_values[1]
                            self.refocus_y = twoD_values[2]
#                            print('xy fit is',self.refocus_x,self.refocus_y)
                else:
                    self.refocus_x = self._trackpoint_x
                    self.refocus_y = self._trackpoint_y
                
            #xz scaning    
            self._scan_z_line()
                                              
            self.kill_scanner()            
            self.unlock()
            
            self.signal_image_updated.emit()
            
            #z-fit
            error, amplitude_z, x_zero_z, sigma_z, offset_z=self._fit_logic.gaussian_estimator(x_axis=self._zimage_Z_values,data=self.z_refocus_line)
            if error == -1:
                self.logMsg('error in initial_guess z fit.', \
                            msgType='error')
                #hier abbrechen
            else:
                initial_guess_z = (amplitude_z, x_zero_z, sigma_z, offset_z)
            
            error, oneD_values = self._fit_logic.make_fit(function=self._fit_logic.gaussian_function, axes=self._zimage_Z_values, data=self.z_refocus_line,initial_guess=initial_guess_z)
            if error == -1:
                self.logMsg('error in 1D Gaussian Fit.', \
                            msgType='error')
                self.refocus_z = self._trackpoint_z
                #hier abbrechen
            else: #move to new position
                if abs(self._trackpoint_z - oneD_values[1]) < self._max_offset: #checks if new pos is too far away
                    if oneD_values[1] >= self.z_range[0] and oneD_values[1] <= self.z_range[1]: #checks if new pos is within the scanner range
                        self.refocus_z = oneD_values[1]
                        self.z_fit_data = self._fit_logic.gaussian_function(x_data=self._zimage_Z_values,amplitude=oneD_values[0], x_zero=oneD_values[1], sigma=oneD_values[2], offset=oneD_values[3])
                else: #new pos is too far away
                    if oneD_values[1] > self._trackpoint_z: #checks if new pos is too high
                        if self._trackpoint_z + 0.5 * self.refocus_Z_size <= self.z_range[1]:
                            self.refocus_z = self._trackpoint_z + 0.5 * self.refocus_Z_size #moves to higher edge of scan range
                        else:
                            self.refocus_z = self.z_range[1] #moves to highest possible value
                    else:
                        if self._trackpoint_z + 0.5 * self.refocus_Z_size >= self.z_range[0]:
                            self.refocus_z = self._trackpoint_z + 0.5 * self.refocus_Z_size #moves to lower edge of scan range
                        else:
                            self.refocus_z = self.z_range[0] #moves to lowest possible value
                    
                
            #TODO: werte als neuen Trackpoint setzen
            
            self._confocal_logic.set_position(x = self.refocus_x, 
                                              y = self.refocus_y, 
                                              z = self.refocus_z, 
                                              a = 0.)
                                              
            self.signal_refocus_finished.emit()
        
    
    def _initialize_z_refocus_image(self):
        """Initialisation of the z refocus image
        """
        self._scan_counter = 0
        z0 = self._trackpoint_z  #falls tilt correction, dann hier aufpassen
        zmin = np.clip(z0 - 0.5 * self.refocus_Z_size, self.z_range[0], self.z_range[1])
        zmax = np.clip(z0 + 0.5 * self.refocus_Z_size, self.z_range[0], self.z_range[1])
        
        self._zimage_Z_values = np.arange(zmin, zmax + self.refocus_Z_step, self.refocus_Z_step)
        self._zimage_A_values = np.zeros(self._zimage_Z_values.shape)
        #self._Z_values = np.clip(z0-0.5*self.ZSize, z0+0.5*self.ZSize, self.ZStep)
        self.z_refocus_line = np.zeros(len(self._zimage_Z_values))
        self.z_fit_data = np.zeros(len(self._zimage_Z_values))
        
        
    def _scan_z_line(self):
        """Scans the z line for refocus
        """
        Z_line = self._zimage_Z_values    #todo: tilt_correction
        X_line = self.refocus_x * np.ones(self._zimage_Z_values.shape)
        Y_line = self.refocus_y * np.ones(self._zimage_Z_values.shape)
        A_line = np.zeros(self._zimage_Z_values.shape)
        
        line = np.vstack( (X_line, Y_line, Z_line, A_line) )            
        line_counts = self._scanning_device.scan_line(line)
        
        self.z_refocus_line = line_counts
        
    def start_scanner(self):
        """Setting up the scanner device.
        
        @return int: error code (0:OK, -1:error)
        """
        
        self._scanning_device.set_up_scanner_clock(clock_frequency = self._clock_frequency)
        self._scanning_device.set_up_scanner()
        
        return 0
    
    
    def kill_scanner(self):
        """Closing the scanner device.
        
        @return int: error code (0:OK, -1:error)
        """
        self._scanning_device.close_scanner()
        self._scanning_device.close_scanner_clock()
        
        return 0
