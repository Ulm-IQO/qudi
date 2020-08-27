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

from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass


class WavemeterInterface(metaclass=InterfaceMetaclass):
    """ Define the controls for a wavemeter hardware.

    Note: This interface is very similar in feature with slow counter
    """

    @abstract_interface_method
    def start_acqusition(self):
        """ Method to start the wavemeter software.

        @return (int): error code (0:OK, -1:error)

        Also the actual threaded method for getting the current wavemeter
        reading is started.
        """
        pass

    @abstract_interface_method
    def stop_acqusition(self):
        """ Stops the Wavemeter from measuring and kills the thread that queries the data.

        @return (int): error code (0:OK, -1:error)
        """
        pass

    @abstract_interface_method
    def get_current_wavelength(self, kind="air"):
        """ This method returns the current wavelength.

        @param (str) kind: can either be "air" or "vac" for the wavelength in air or vacuum, respectively.

        @return (float): wavelength (or negative value for errors)
        """
        pass

    @abstract_interface_method
    def get_current_wavelength2(self, kind="air"):
        """ This method returns the current wavelength of the second input channel.

        @param (str) kind: can either be "air" or "vac" for the wavelength in air or vacuum, respectively.

        @return float: wavelength (or negative value for errors)
        """
        pass

    @abstract_interface_method
    def get_timing(self):
        """ Get the timing of the internal measurement thread.

        @return (float): clock length in second
        """
        pass

    @abstract_interface_method
    def set_timing(self, timing):
        """ Set the timing of the internal measurement thread.

        @param (float) timing: clock length in second

        @return (int): error code (0:OK, -1:error)
        """
        pass
