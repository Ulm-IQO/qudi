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
from core.util.Mutex import Mutex

from pyqtgraph.Qt import QtGui, QtCore

import random



class HighFinesseWavemeter(Base,WavemeterInterface):
        
    # the current wavelength read by the wavemeter in nm (vac)
    _current_wavelenght=0.0
    _current_wavelenght2=0.0
    # time between two measurement points of the wavemeter in milliseconds
    _measurement_timing=10
    
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
        pass

    def deactivation(self, e):
        pass
                        
    #############################################
    # Methods of the main class
    #############################################
    def start_acqusition(self):
        """ Method to start the wavemeter software. 
        
        @return int: error code (0:OK, -1:error)
        
        Also the actual threaded method for getting the current wavemeter reading is started.
        """
        
        # first check its status
        if self.getStatus() is 'running':
            self.logMsg('Wavemeter busy', 
                    msgType='error')
            return -1
        
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self._measure_thread)
        
        self.run()
        # actually start the wavemeter
        self.logMsg('starting Wavemeter', 
                msgType='warning')       
        
        # start the measuring thread
        self._timer.start(self._measurement_timing)
        
        return 0
        
    def stop_acqusition(self):
        """ Stops the Wavemeter from measuring and kills the thread that queries the data.
        
        @return int: error code (0:OK, -1:error)
        """
        # check status just for a sanity check
        if self.getStatus() == 'idle':
            self.logMsg('Wavemeter was already stopped, stopping it anyway!', 
                    msgType='warning')
                
        # stop the measurement thread
        self._timer.stop()
                
        # Stop the actual wavemeter measurement
        self.logMsg('stopping Wavemeter', 
                msgType='warning')       
        
        # set status to idle again
        self.stop()
        
        return 0
        
    def get_current_wavelength(self, kind="air"):
        """ This method returns the current wavelength.
        
        @param string kind: can either be "air" or "vac" for the wavelength in air or vacuum, respectively.
        
        @return float: wavelength (or negative value for errors)
        """
        if kind in "air":
            # for air we need the convert the current wavelength. T
            return float(self._current_wavelenght)
        if kind in "vac":
            # for vacuum just return the current wavelength
            return float(self._current_wavelenght)
        return -2.0
        
    def get_current_wavelength2(self, kind="air"):
        """ This method returns the current wavelength of the second input channel.
        
        @param string kind: can either be "air" or "vac" for the wavelength in air or vacuum, respectively.
        
        @return float: wavelength (or negative value for errors)
        """
        if kind in "air":
            # for air we need the convert the current wavelength. 
            return float(self._current_wavelenght2)
        if kind in "vac":
            # for vacuum just return the current wavelength
            return float(self._current_wavelenght2)
        return -2.0
            
    def get_timing(self):
        """ Get the timing of the internal measurement thread.
        
        @return float: clock length in second
        """
        return self._measurement_timing
        
    def set_timing(self, timing):
        """ Set the timing of the internal measurement thread.
        
        @param float timing: clock length in second
        
        @return int: error code (0:OK, -1:error)
        """
        self._measurement_timing=float(timing)
        return 0
    
    def _measure_thread(self):
        """ The threaded method querying the data from the wavemeter.
        """
        
        # update as long as the status is busy
        if self.getStatus() == 'running':
            # get the current wavelength from the wavemeter
            self.current_wavelenght  += random.uniform(-1, 1)
            self.current_wavelenght2 += random.uniform(-1, 1)
            