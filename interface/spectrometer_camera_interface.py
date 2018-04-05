# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interface for Slow counter.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import abc
from enum import Enum
from core.util.interfaces import InterfaceMetaclass


class SpectrometerCameraInterface(metaclass=InterfaceMetaclass):
    """ Define the interface with a camera use for spectroscopy.
    These camera can be cooled, used in image mode or Full Vertical Binning
    """

    _modtype = 'SpectrometerCameraInterface'
    _modclass = 'interface'

    @abc.abstractmethod
    def get_name(self):
        """ Retrieve an identifier of the camera that the GUI can print
        Maker, model, serial number, etc.
        @return string: name for the camera
        """
        pass

    @abc.abstractmethod
    def get_constraints(self):
        """ Retrieve the hardware constrains

        @return SpectrometerCameraConstraints: object with constraints for the camera
        """
        pass

    @abc.abstractmethod
    def set_read_mode(self, mode):
        """ Set the read mode of the camera.

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def get_read_mode(self):
        """ Get the read mode of the camera.

        @return ReadMode: current readMode
        """
        pass

    @abc.abstractmethod
    def set_image(self, hbin, vbin, hstart, hend, vstart, vend):
        """ Set the pixel the camera is going to read and how in image read mode
        hbin : int : number of real horizontal pixel for 1 superpixel
        vbin : int : number of real vertical pixel for 1 superpixel
        hstart : int : start colomn (inclusive)
        hend : int : end column (inclusive)
        vstart : int : start row (inclusive)
        vend : int : end row (inclusive)

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def start_acqusition(self):
        """

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def get_aquired_data(self):
        """

        @return: aquired data, 2d array of float
            [[track]] in FVB/SINGLE_TRACK
            [[track],[track]...] in MULTI_TRACK/RANDOM_TRACK
            [[row],[row]...] in IMAGE
        """
        pass

    @abc.abstractmethod
    def set_exposure(self, time):
        """ Set the exposure time in seconds

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def get_exposure(self):
        """ Get the exposure time in seconds

        @return float: exposure time
        """
        pass

    @abc.abstractmethod
    def set_cooler_on_state(self, on_state):
        """ Set the coller on or off

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def get_cooler_on_state(self):
        """ Get the state of the cooler

        @return float: exposure time
        """
        pass

    @abc.abstractmethod
    def get_measured_temperature(self):
        """
        Get the temperature measured by the camera
        @return: float : temperature in Celsius
        """
        pass

    @abc.abstractmethod
    def set_setpoint_temperature(self, temperature):
        """ Set the temperature the system is going to try to achieve

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def get_measured_temperature(self):
        """ Get the temperature the system is going to try to achieve

        @return: float : temperature in Celsius
        """
        pass

    @abc.abstractmethod
    def get_ready_state(self):
        """ Is the camera ready for an acquisition ?

        @return: bool
        """
        pass

    ### To be compatible with simple spectro interface
    @abc.abstractmethod
    def recordSpectrum(self):
        """
        Launch acquisition and return acquired data
        :return:
        """
        pass

    @abc.abstractmethod
    def setExposure(self, exposureTime):
        pass

    @abc.abstractmethod
    def getExposure(self):
        pass

#TODO : the methods for all readmode should be described (only FVB and image currently)

# The following classes constant are inspired by Andor cameras

class ReadMode(Enum):
    FVB = 0
    MULTI_TRACK = 1
    RANDOM_TRACK = 2
    SINGLE_TRACK = 3
    IMAGE = 4


class SpectrometerCameraConstraints:

    def __init__(self):
        # maximum numer of possible detectors for slow counter
        self.read_mode = []
        self.cooling = False
        self.max_cooling = -50.0
        self.width = 0
        self.height = 0

