# -*- coding: utf-8 -*-
"""
Hardware file for the Cryomagnetics power supply for superconducting magnet

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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""


import visa
from core.module import Base
from core.configoption import ConfigOption
import numpy as np
from collections import OrderedDict


class Cryomagnetics(Base):
    """ Hardware module to control one or two vector magnet via the power supply

    Example config for copy-paste:

    cryognatics_xy:
        module.Class: 'sc_magnet.cryomagnetics.Cryomagnetics'
        visa_address: 'tcpip0::192.168.0.254:4444:socket'

    """
    _visa_address = ConfigOption('visa_address', missing='error')
    _timeout = ConfigOption('timeout', 1)

    def __init__(self, **kwargs):
        """Here the connections to the power supplies and to the counter are established"""
        super().__init__(**kwargs)
        self._inst = None

    def on_activate(self):
        """ Connect to hardware """

        rm = visa.ResourceManager()
        try:
            self._inst = rm.open_resource(self._visa_address, timeout=self._timeout)
        except:
            self.log.error('Could not connect to hardware. Please check the wires and the address.')

    def on_deactivate(self):
        """ Disconnect from hardware """
        self._inst.close()

    def set_lower_limit(self, channel=1):
        self._inst.write('LL')