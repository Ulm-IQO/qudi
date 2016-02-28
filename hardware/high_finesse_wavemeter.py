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

from pyqtgraph.Qt import QtGui, QtCore
import ctypes   # is a foreign function library for Python. It provides C
                # compatible data types, and allows calling functions in DLLs
                # or shared libraries. It can be used to wrap these libraries
                # in pure Python.

from interface.wavemeter_interface import WavemeterInterface
from core.base import Base
from core.util.mutex import Mutex


class HardwarePull(QtCore.QObject):
    """ Helper class for running the hardware communication in a separate thread. """

    # signal to deliver the wavelength to the parent class
    sig_wavelength = QtCore.Signal(float, float)

    def __init__(self, parentclass):
        super().__init__()

        # remember the reference to the parent class to access functions ad settings
        self._parentclass = parentclass


    def handle_timer(self, state_change):
        """ Threaded method that can be called by a signal from outside to start the timer.

        @param bool state: (True) starts timer, (False) stops it.
        """

        if state_change:
            self.timer = QtCore.QTimer()
            self.timer.timeout.connect(self._measure_thread)
            self.timer.start(self._parentclass._measurement_timing)
        else:
            if hasattr(self, 'timer'):
                self.timer.stop()

    def _measure_thread(self):
        """ The threaded method querying the data from the wavemeter.
        """

        # update as long as the state is busy
        if self._parentclass.getState() == 'running':
            # get the current wavelength from the wavemeter
            temp1=float(self._parentclass._wavemeterdll.GetWavelength(0))
            temp2=float(self._parentclass._wavemeterdll.GetWavelength(0))

            # send the data to the parent via a signal
            self.sig_wavelength.emit(temp1, temp2)



class HighFinesseWavemeter(Base,WavemeterInterface):

    _modclass = 'HighFinesseWavemeter'
    _modtype = 'hardware'

    ## declare connectors
    _out = {'highfinessewavemeter': 'WavemeterInterface'}

    sig_handle_timer = QtCore.Signal(bool)

    #############################################
    # Flags for the external DLL
    #############################################

    # define constants as flags for the wavemeter
    _cCtrlStop                   = ctypes.c_uint16(0x00)
    # this following flag is modified to override every existing file
    _cCtrlStartMeasurment        = ctypes.c_uint16(0x1002)
    _cReturnWavelangthAir        = ctypes.c_long(0x0001)
    _cReturnWavelangthVac        = ctypes.c_long(0x0000)


    def __init__(self, manager, name, config = {}, **kwargs):
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, configuration=config, callbacks = c_dict, **kwargs)

        #locking for thread safety
        self.threadlock = Mutex()

        # the current wavelength read by the wavemeter in nm (vac)
        self._current_wavelength=0.0
        self._current_wavelength2=0.0

        # time between two measurement points of the wavemeter in milliseconds
        if 'measurement_timing' in config.keys():
            self._measurement_timing=config['measurement_timing']
        else:
            self._measurement_timing = 10.
            self.logMsg('No measurement_timing configured, '\
                        'using {} instead.'.format(self._measurement_timing),
                        msgType='warning')


    def activation(self, e):
        #############################################
        # Initialisation to access external DLL
        #############################################
        try:
            # imports the spectrometer specific function from dll
            self._wavemeterdll = ctypes.windll.LoadLibrary('wlmData.dll')

        except:
            self.logMsg('There is no Wavemeter installed on this Computer.\n Please install a High Finesse Wavemeter and try again.',
                    msgType='error')

        # define the use of the GetWavelength function of the wavemeter
#        self._GetWavelength2 = self._wavemeterdll.GetWavelength2
        # return data type of the GetWavelength function of the wavemeter
        self._wavemeterdll.GetWavelength2.restype = ctypes.c_double
        # parameter data type of the GetWavelength function of the wavemeter
        self._wavemeterdll.GetWavelength2.argtypes = [ctypes.c_double]

        # define the use of the GetWavelength function of the wavemeter
#        self._GetWavelength = self._wavemeterdll.GetWavelength
        # return data type of the GetWavelength function of the wavemeter
        self._wavemeterdll.GetWavelength.restype = ctypes.c_double
        # parameter data type of the GetWavelength function of the wavemeter
        self._wavemeterdll.GetWavelength.argtypes = [ctypes.c_double]

        # define the use of the ConvertUnit function of the wavemeter
#        self._ConvertUnit = self._wavemeterdll.ConvertUnit
        # return data type of the ConvertUnit function of the wavemeter
        self._wavemeterdll.ConvertUnit.restype = ctypes.c_double
        # parameter data type of the ConvertUnit function of the wavemeter
        self._wavemeterdll.ConvertUnit.argtypes = [ctypes.c_double, ctypes.c_long, ctypes.c_long]

        # manipulate perdefined operations with simple flags
#        self._Operation = self._wavemeterdll.Operation
        # return data type of the Operation function of the wavemeter
        self._wavemeterdll.Operation.restype = ctypes.c_long
        # parameter data type of the Operation function of the wavemeter
        self._wavemeterdll.Operation.argtypes = [ctypes.c_ushort]

        # create an indepentent thread for the hardware communication
        self.hardware_thread = QtCore.QThread()

        # create an object for the hardware communication and let it live on the new thread
        self._hardware_pull = HardwarePull(self)
        self._hardware_pull.moveToThread(self.hardware_thread)

        # connect the signals in and out of the threaded object
        self.sig_handle_timer.connect(self._hardware_pull.handle_timer)
        self._hardware_pull.sig_wavelength.connect(self.handle_wavelength)

        # start the event loop for the hardware
        self.hardware_thread.start()


    def deactivation(self, e):
        if self.getState() != 'idle' and self.getState() != 'deactivated':
            self.stop_acqusition()
        self.hardware_thread.quit()
        self.sig_handle_timer.disconnect()
        self._hardware_pull.sig_wavelength.disconnect()

        try:
            # clean up by removing reference to the ctypes library object
            del self._wavemeterdll
            return 0
        except:
            self.logMsg('Could not unload the wlmData.dll of the wavemeter.',
                    msgType='error')


    #############################################
    # Methods of the main class
    #############################################

    def handle_wavelength(self, wavelength1, wavelength2):
        """ Function to save the wavelength, when it comes in with a signal.
        """
        self._current_wavelength = wavelength1
        self._current_wavelength2 = wavelength2

    def start_acqusition(self):
        """ Method to start the wavemeter software.

        @return int: error code (0:OK, -1:error)

        Also the actual threaded method for getting the current wavemeter reading is started.
        """

        # first check its status
        if self.getState() == 'running':
            self.logMsg('Wavemeter busy',
                    msgType='error')
            return -1


        self.run()
        # actually start the wavemeter
        self._wavemeterdll.Operation(self._cCtrlStartMeasurment) #starts measurement

        # start the measuring thread
        self.sig_handle_timer.emit(True)

        return 0

    def stop_acqusition(self):
        """ Stops the Wavemeter from measuring and kills the thread that queries the data.

        @return int: error code (0:OK, -1:error)
        """
        # check status just for a sanity check
        if self.getState() == 'idle':
            self.logMsg('Wavemeter was already stopped, stopping it anyway!',
                    msgType='warning')
        else:
            # stop the measurement thread
            self.sig_handle_timer.emit(True)
            # set status to idle again
            self.stop()

        # Stop the actual wavemeter measurement
        self._wavemeterdll.Operation(self._cCtrlStop)

        return 0

    def get_current_wavelength(self, kind="air"):
        """ This method returns the current wavelength.

        @param string kind: can either be "air" or "vac" for the wavelength in air or vacuum, respectively.

        @return float: wavelength (or negative value for errors)
        """
        if kind in "air":
            # for air we need the convert the current wavelength. The Wavemeter DLL already gives us a nice tool do do so.
            return float(self._wavemeterdll.ConvertUnit(self._current_wavelength,self._cReturnWavelangthVac,self._cReturnWavelangthAir))
        if kind in "vac":
            # for vacuum just return the current wavelength
            return float(self._current_wavelength)
        return -2.0

    def get_current_wavelength2(self, kind="air"):
        """ This method returns the current wavelength of the second input channel.

        @param string kind: can either be "air" or "vac" for the wavelength in air or vacuum, respectively.

        @return float: wavelength (or negative value for errors)
        """
        if kind in "air":
            # for air we need the convert the current wavelength. The Wavemeter DLL already gives us a nice tool do do so.
            return float(self._wavemeterdll.ConvertUnit(self._current_wavelength2,self._cReturnWavelangthVac,self._cReturnWavelangthAir))
        if kind in "vac":
            # for vacuum just return the current wavelength
            return float(self._current_wavelength2)
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

