# -*- coding: utf-8 -*-
# unstable: Kay Jahnke

from logic.GenericLogic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.Mutex import Mutex
from collections import OrderedDict
import numpy as np
               

class OptimiserLogic(GenericLogic):
    """unstable: Christoph Müller
    This is the Logic class for refocussing on and tracking bright features in the confocal scan.
    """
    signal_scan_xy_line_next = QtCore.Signal()
    signal_image_updated = QtCore.Signal()
    signal_refocus_finished = QtCore.Signal()
    signal_refocus_started = QtCore.Signal()
    

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
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
        
        self.connector['out']['optimiserlogic'] = OrderedDict()
        self.connector['out']['optimiserlogic']['class'] = 'OptimiserLogic'
        

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                            
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
                                
        #default values for clock frequency and slowness
        #slowness: steps during retrace line
        self._clock_frequency = 200
        self.return_slowness = 20
        
        #setting standard parameter for refocus
        self.refocus_XY_size =  0.6
        self.refocus_XY_step = 0.06
        self.refocus_Z_size = 2
        self.refocus_Z_step = 0.1
        self.fit_Z_step = 0.01
        
        #locking for thread safety
        self.threadlock = Mutex()
        
        self.stopRequested = False
        self.is_crosshair = True
                       
    def activation(self, e):
        """ Initialisation performed during activation of the module.
        @param e: error code
        @return int: error code (0:OK, -1:error)
        """        
        self._scanning_device = self.connector['in']['confocalscanner1']['object']
#        print("Scanning device is", self._scanning_device)
        self._fit_logic = self.connector['in']['fitlogic']['object']
        self._confocal_logic = self.connector['in']['scannerlogic']['object']
        
        self.x_range = self._scanning_device.get_position_range()[0]
        self.y_range = self._scanning_device.get_position_range()[1]
        self.z_range = self._scanning_device.get_position_range()[2]
                
        self._trackpoint_x = 0.
        self._trackpoint_y = 0.
        self._trackpoint_z = 0.
        self.refocus_x = self._trackpoint_x
        self.refocus_y = self._trackpoint_y
        self.refocus_z = self._trackpoint_z
        
        self._max_offset = 3.
        
        # Initialization of internal counter for scanning 
        self._scan_counter = 0
        
        # Sets connections between signals and functions  
        self.signal_scan_xy_line_next.connect(self._refocus_line, QtCore.Qt.QueuedConnection)

        self._initialize_xy_refocus_image()
        self._initialize_z_refocus_image()
        
        return 0
                
    def deactivation(self,e):
        
        """ Reverse steps of activation 
        
        @param e: error code
        @return int: error code (0:OK, -1:error)
        """        
        return 0    
        
    def testing(self):
        pass
        
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
            
    def start_refocus(self, trackpoint=None):
        """Starts refocus 
        @param trackpoint
        """
        print('start refocusing')
        # checking if refocus corresponding to crosshair or corresponding 
        # to trackpoint
        if isinstance(trackpoint, (np.ndarray,)) and trackpoint.size == 3:
            self.is_crosshair = False
            self._trackpoint_x, self._trackpoint_y, self._trackpoint_z = trackpoint
        elif isinstance(trackpoint, (list, tuple)) and len(trackpoint) == 3:
            self.is_crosshair = False
            self._trackpoint_x, self._trackpoint_y, self._trackpoint_z = trackpoint
        else:
            self.is_crosshair = True
            self._trackpoint_x, self._trackpoint_y, self._trackpoint_z = \
                    self._confocal_logic.get_position()
        
        self.lock()
        self.signal_refocus_started.emit()
        self._scan_counter = 0
        self._initialize_xy_refocus_image()
        self._initialize_z_refocus_image()
        
        self.start_scanner()                
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
        # defining center of refocus image
        x0 = self._trackpoint_x
        y0 = self._trackpoint_y
         # defining position intervals for refocus
        xmin = np.clip(x0 - 0.5 * self.refocus_XY_size, self.x_range[0], self.x_range[1])
        xmax = np.clip(x0 + 0.5 * self.refocus_XY_size, self.x_range[0], self.x_range[1])
        ymin = np.clip(y0 - 0.5 * self.refocus_XY_size, self.y_range[0], self.y_range[1])
        ymax = np.clip(y0 + 0.5 * self.refocus_XY_size, self.y_range[0], self.y_range[1])
        
        self._X_values = np.arange(xmin, xmax + self.refocus_XY_step, self.refocus_XY_step)
        self._Y_values = np.arange(ymin, ymax + self.refocus_XY_step, self.refocus_XY_step)
        self._Z_values = self._trackpoint_z * np.ones(self._X_values.shape)
        self._A_values = np.zeros(self._X_values.shape)
        self._return_X_values = np.arange(xmax, xmin - self.refocus_XY_step, -self.refocus_XY_step)
        self._return_A_values = np.zeros(self._return_X_values.shape)
        
        self.xy_refocus_image = np.zeros((len(self._Y_values), len(self._X_values), 4))
        self.xy_refocus_image[:,:,0] = np.full((len(self._Y_values), len(self._X_values)), self._X_values)
        y_value_matrix = np.full((len(self._X_values), len(self._Y_values)), self._Y_values)
        self.xy_refocus_image[:,:,1] = y_value_matrix.transpose()
        self.xy_refocus_image[:,:,2] = self._trackpoint_z * np.ones((len(self._Y_values), len(self._X_values)))

        
        
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
                self.signal_refocus_finished.emit()
                return
                
        self.refocus_x = self._trackpoint_x
        self.refocus_y = self._trackpoint_y
        self.refocus_z = self._trackpoint_z
        
        try:                         
            if self._scan_counter == 0:
                
                start_line = np.vstack( (np.linspace(self._trackpoint_x, \
                                                     self.xy_refocus_image[self._scan_counter,0,0], \
                                                     self.return_slowness), \
                                         np.linspace(self._trackpoint_y, \
                                                     self.xy_refocus_image[self._scan_counter,0,1], \
                                                     self.return_slowness), \
                                         np.linspace(self._trackpoint_z, \
                                                     self.xy_refocus_image[self._scan_counter,0,2], \
                                                     self.return_slowness), \
                                         np.linspace(0, \
                                                     0, \
                                                     self.return_slowness) ))
                
                start_line_counts = self._scanning_device.scan_line(start_line)
                
            line = np.vstack( (self.xy_refocus_image[self._scan_counter,:,0],
                               self.xy_refocus_image[self._scan_counter,:,1], 
                               self.xy_refocus_image[self._scan_counter,:,2],  
                               self._A_values) )
                
            line_counts = self._scanning_device.scan_line(line)
            
            return_line = np.vstack( (self._return_X_values, 
                                      self.xy_refocus_image[self._scan_counter,0,1] * np.ones(self._return_X_values.shape), 
                                      self.xy_refocus_image[self._scan_counter,0,2] * np.ones(self._return_X_values.shape), 
                                      self._return_A_values) )
            
            return_line_counts = self._scanning_device.scan_line(return_line)
        
        except Exception:
            self.logMsg('The scan went wrong, killing the scanner.', msgType='error')
            self.stop_refocus()           
            self.signal_scan_xy_line_next.emit()
        
        self.xy_refocus_image[self._scan_counter,:,3] = line_counts
        
        self.signal_image_updated.emit()
        self._scan_counter += 1
        
        if self._scan_counter < np.size(self._Y_values):   
            #calling next line scan in refocus procedure
            self.signal_scan_xy_line_next.emit()
        else:
            #x,y-fit when refocus is finished
            fit_x, fit_y = np.meshgrid(self._X_values, self._Y_values)
            xy_fit_data = self.xy_refocus_image[:,:,3].ravel()
            axes = np.empty((len(self._X_values)*len(self._Y_values),2))
            axes=(fit_x.flatten(),fit_y.flatten())
            result_2D_gaus = self._fit_logic.make_twoD_gaussian_fit(axis=axes,data=xy_fit_data)
#            print(result_2D_gaus.fit_report())
                        
            if result_2D_gaus.success == False:
                self.logMsg('error in 2D Gaussian Fit.', \
                            msgType='error')
                print('2D gaussian fit not successfull')
                self.refocus_x = self._trackpoint_x
                self.refocus_y = self._trackpoint_y
                #hier abbrechen
            else:
#                @reviewer: Do we need this. With constraints not one of these cases will be possible....
                if abs(self._trackpoint_x - result_2D_gaus.best_values['x_zero']) < self._max_offset and abs(self._trackpoint_x - result_2D_gaus.best_values['x_zero']) < self._max_offset:
                    if result_2D_gaus.best_values['x_zero'] >= self.x_range[0] and result_2D_gaus.best_values['x_zero'] <= self.x_range[1]:
                        if result_2D_gaus.best_values['y_zero'] >= self.y_range[0] and result_2D_gaus.best_values['y_zero'] <= self.y_range[1]:
                            self.refocus_x = result_2D_gaus.best_values['x_zero']
                            self.refocus_y = result_2D_gaus.best_values['y_zero']
                else:
                    self.refocus_x = self._trackpoint_x
                    self.refocus_y = self._trackpoint_y
                
            #xz scaning    
            self._scan_z_line()
                                              
            self.kill_scanner()            
            self.unlock()
            
            self.signal_image_updated.emit()

            #z-fit
            
            result = self._fit_logic.make_gaussian_fit(axis=self._zimage_Z_values, data=self.z_refocus_line)
            
            if result.success == False:
                self.logMsg('error in 1D Gaussian Fit.', \
                            msgType='error')
                self.refocus_z = self._trackpoint_z
                #hier abbrechen
            else: #move to new position
#                @reviewer: Do we need this. With constraints not one of these cases will be possible....
                if abs(self._trackpoint_z - result.best_values['center']) < self._max_offset: #checks if new pos is too far away
                    if result.best_values['center'] >= self.z_range[0] and result.best_values['center'] <= self.z_range[1]: #checks if new pos is within the scanner range
                        self.refocus_z = result.best_values['center']
                        gauss,params=self._fit_logic.make_gaussian_model()
                        self.z_fit_data = gauss.eval(x=self._fit_zimage_Z_values,params=result.params)
                    else: #new pos is too far away
                        if result.best_values['center'] > self._trackpoint_z: #checks if new pos is too high
                            if self._trackpoint_z + 0.5 * self.refocus_Z_size <= self.z_range[1]:
                                self.refocus_z = self._trackpoint_z + 0.5 * self.refocus_Z_size #moves to higher edge of scan range
                            else:
                                self.refocus_z = self.z_range[1] #moves to highest possible value
                        else:
                            if self._trackpoint_z + 0.5 * self.refocus_Z_size >= self.z_range[0]:
                                self.refocus_z = self._trackpoint_z + 0.5 * self.refocus_Z_size #moves to lower edge of scan range
                            else:
                                self.refocus_z = self.z_range[0] #moves to lowest possible value
                        
            
            self.logMsg('Moved from ({0:.3f},{1:.3f},{2:.3f}) to ({3:.3f},{4:.3f},{5:.3f}).'.format(\
            self._trackpoint_x, self._trackpoint_y, self._trackpoint_z,\
            self.refocus_x, self.refocus_y, self.refocus_z), \
                            msgType='status')
            #TODO: werte als neuen Trackpoint setzen
            
            if self.is_crosshair:
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
        self._fit_zimage_Z_values = np.arange(zmin, zmax + self.refocus_Z_step, self.fit_Z_step)
        self._zimage_A_values = np.zeros(self._zimage_Z_values.shape)
        #self._Z_values = np.clip(z0-0.5*self.ZSize, z0+0.5*self.ZSize, self.ZStep)
        self.z_refocus_line = np.zeros(len(self._zimage_Z_values))
        self.z_fit_data = np.zeros(len(self._fit_zimage_Z_values))
        
        
    def _scan_z_line(self):
        """Scans the z line for refocus
        """
        #defining trace of positions for z-refocus 
        Z_line = self._zimage_Z_values    #todo: tilt_correction
        X_line = self.refocus_x * np.ones(self._zimage_Z_values.shape)
        Y_line = self.refocus_y * np.ones(self._zimage_Z_values.shape)
        A_line = np.zeros(self._zimage_Z_values.shape)
        
        line = np.vstack( (X_line, Y_line, Z_line, A_line) )
        try:
            line_counts = self._scanning_device.scan_line(line)
        except Exception:
            self.logMsg('The scan went wrong, killing the scanner.', msgType='error')
            self.stop_refocus()           
            self.signal_scan_xy_line_next.emit()
        
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
