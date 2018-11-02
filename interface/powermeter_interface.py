# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interface file for control wavemeter hardware.

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
from core.util.interfaces import InterfaceMetaclass


class PowermeterInterface(metaclass=InterfaceMetaclass):
    """ Define the controls for a wavemeter hardware."""

    _modclass = 'PowermeterInterface'
    _modtype = 'interface'



    @abc.abstractmethod
    def get_wavelength(self):
        """ This method returns the current wavelength.

        @param str kind: can either be "air" or "vac" for the wavelength in air
                         or vacuum, respectively.

        @return float: wavelength (or negative value for errors)
        """
        pass

    @abc.abstractmethod
    def get_power(self):
        """ Get the timing of the internal measurement thread.

        @return float: clock length in second
        """
        pass

    @abc.abstractmethod
    def set_wavelength(self, wavelength):
        """ Set the wavelength of the internal measurement thread.

        @param float timing: clock length in second

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def set_range(self, range):
        """ Set the timing of the internal measurement thread.

        @param float timing: clock length in second

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def disconnect(self):
        """ Set the timing of the internal measurement thread.

        @param float timing: clock length in second

        @return int: error code (0:OK, -1:error)
        """
        pass