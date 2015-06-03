# -*- coding: utf-8 -*-
"""
This module contains a POI Manager core class which gives capability to mark 
points of interest, re-optimise their position, and keep track of sample drift 
over time.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2015 Kay D. Jahnke  kay.jahnke@alumni.uni-ulm.de
"""

from core.Base import Base
from hardware.WavemeterInterface import WavemeterInterface
from collections import OrderedDict
import random
import time

import ctypes   # is a foreign function library for Python. It provides C 
                # compatible data types, and allows calling functions in DLLs 
                # or shared libraries. It can be used to wrap these libraries 
                # in pure Python.
import threading



class HighFinesseWavemeter(Base,WavemeterInterface):
    
    #############################################
    # Flags for the external DLL
    #############################################
    
    # define constants as flags for the wavemeter
    _cCtrlStop                   = ctypes.c_uint16(0x00)
    # this following flag is modified to override every existing file
    _cCtrlStartMeasurment        = ctypes.c_uint16(0x1002)
    _cReturnWavelangthAir        = ctypes.c_long(0x0001)
    _cReturnWavelangthVac        = ctypes.c_long(0x0000)

    #############################################
    # Class parameters
    #############################################
    
    # the current wavelength read by the wavemeter in nm (vac)
    current_wavelenght=0.0
    # time between two measurement points of the wavemeter in seconds
    measurement_timing=0.001
    
    def __init__(self, manager, name, config = {}, **kwargs):
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, configuation=config, callbacks = c_dict, **kwargs)
        self._modclass = 'HighFinesseWavemeter'
        self._modtype = 'wavemeter'
        
        ## declare connectors        
        self.connector['out']['highhinessewavemeter'] = OrderedDict()
        self.connector['out']['highhinessewavemeter']['class'] = 'HighFinesseWavemeter' 
        
        #locking for thread safety
        self.threadlock = Mutex()


    def activation(self, e):
        #############################################
        # Initialisation to access external DLL
        #############################################
        try:
            #imports the spectrometer specific function from dll
            wavemeterdll = ctypes.windll.LoadLibrary('wlmData.dll') 
            
            # define the use of the GetWavelength function of the wavemeter
            self._GetWavelength2 = wavemeterdll.GetWavelength2
            # return data type of the GetWavelength function of the wavemeter
            self._GetWavelength2.restype = ctypes.c_double
            # parameter data type of the GetWavelength function of the wavemeter
            self._GetWavelength2.argtypes = [ctypes.c_double]
            
            # define the use of the GetWavelength function of the wavemeter
            self._GetWavelength = wavemeterdll.GetWavelength
            # return data type of the GetWavelength function of the wavemeter
            self._GetWavelength.restype = ctypes.c_double
            # parameter data type of the GetWavelength function of the wavemeter
            self._GetWavelength.argtypes = [ctypes.c_double]
            
            # define the use of the ConvertUnit function of the wavemeter
            self._ConvertUnit = wavemeterdll.ConvertUnit
            # return data type of the ConvertUnit function of the wavemeter
            self._ConvertUnit.restype = ctypes.c_double
            # parameter data type of the ConvertUnit function of the wavemeter
            self._ConvertUnit.argtypes = [ctypes.c_double,ctypes.c_long,ctypes.c_long]
            
            # manipulate perdefined operations with simple flags
            self._Operation= wavemeterdll.Operation
            
        except:
            print ('There is no Wavemeter installed on this Computer.\n Please install a High Finesse Wavemeter and try again.')


    def deactivation(self, e):
        pass
                        
    #############################################
    # Methods of the main class
    #############################################
    def start_acqusition(self):
        """
            Method to start the wavemeter software. 
            Also the actual threaded method for getting the current wavemeter reading is started.
        """
        # first check its status
        if self.getStatus() is 'running':
            print ('Wavemeter busy')
            return -1
        
        # define a thread to query the data
        self.measthread = threading.Thread(target=self.measure_thread)
        self.measthread.stop_request = threading.Event()
        
        self.run()
        # actually start the wavemeter
        self._Operation(self._cCtrlStartMeasurment) #starts measurement 
        
        # start the measuring thread
        self.measthread.start()
        # wait a bit, so it has time to actually start
        time.sleep(0.01)
        return 0
        
    def stop_acqusition(self):
        """
            Stops the Wavemeter from measuring and kills the thread that queries the data
        """
        # check status just for a sanity check
        if self.getStatus() == 'idle':
            print ('Wavemeter was already stopped, stopping it anyway!')
        
        # set status to idle again
        self.stop()
        
        # stop the measurement thread
        self.measthread.stop_request.set()
        # Stop the actual wavemeter measurement
        self._Operation(self._cCtrlStop) 
        return 0
        
    def get_current_wavelength(self, kind="air"):
        """
            This method returns the current wavelength.
            kind can either be "air" or "vac" for the wavelength in air or vacuum, respectively.
        """
        if kind in "air":
            # for air we need the convert the current wavelength. The Wavemeter DLL already gives us a nice tool do do so.
            return float(self._ConvertUnit(self.current_wavelenght,self._cReturnWavelangthVac,self._cReturnWavelangthAir))
        if kind in "vac":
            # for vacuum just return the current wavelength
            return float(self.current_wavelenght)
        return -2.0
        
    def get_current_wavelength2(self, kind="air"):
        """
            This method returns the current wavelength.
            kind can either be "air" or "vac" for the wavelength in air or vacuum, respectively.
        """
        if kind in "air":
            # for air we need the convert the current wavelength. The Wavemeter DLL already gives us a nice tool do do so.
            return float(self._ConvertUnit(self.current_wavelenght2,self._cReturnWavelangthVac,self._cReturnWavelangthAir))
        if kind in "vac":
            # for vacuum just return the current wavelength
            return float(self.current_wavelenght2)
        return -2.0
            
    def get_timing(self):
        """
            Get the timing of the measurement
        """
        return self.measurement_timing
        
    def set_timing(self, timing):
        """
            Set the timing of the measurement, parameter should be a float.
        """
        self.measurement_timing=float(timing)
        return 0
    
    def _measure_thread(self):
        """
            The threaded method querying the data from the wavemeter.
        """
        
        # run as long as the status is busy
        while self.getStatus() == 'running':
            # get the current wavelength from the wavemeter
            self.current_wavelenght = self._GetWavelength(ctypes.c_double(0))
            self.current_wavelenght2 = self._GetWavelength2(ctypes.c_double(0))
            
            # if there is a stop request break out of the loop
            if threading.current_thread().stop_request.isSet():
                break
            
            # wait befor the next measurement
            time.sleep(self.measurement_timing)