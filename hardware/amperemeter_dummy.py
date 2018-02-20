# -*- coding: utf-8 -*-
"""
This module controls an Amperemeter.

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

from core.module import Base, ConfigOption
from interface.amperemeter_interface import AmperemeterInterface
import numpy as np
import time

class Amperemeter(Base, AmperemeterInterface):
    """
    This module implements communication with Picoamperemeter.

    This module is untested and very likely broken.
    """
    _modclass = 'picoamperemeter'
    _modtype = 'dummy'

    # config options
    _interface = ConfigOption('interface', missing='error')

    def on_activate(self):
        """ Activate module
        """
        self.connect(self._interface)

    def on_deactivate(self):
        """ Deactivate module
        """
        self.disconnect()

    def connect(self, interface):
        """ Connect to Instrument.

            @param str interface: visa interface identifier

            @return bool: connection success
        """
        self.log.debug("Connected to: {0:s}".format(interface))
        return True

    def disconnect(self):
        """ Close the connection to the instrument.
        """
        self.log.debug("Disconnected")

    def get_value(self):
        """ Get a value reading from the controller.

            @return str: reading from the controller
        """
        time.sleep(0.03)
        return np.random.uniform()

    def get_device_status(self):
        """ Check if the device is ready again.

            @return bool: True if ready, False if not
        """
        return True
