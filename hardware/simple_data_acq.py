# -*- coding: utf-8 -*-
"""
Simple data acquisition from serial port.

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

import visa

from core.base import Base
from interface.simple_data_interface import SimpleDataInterface


class SimpleAcq(Base, SimpleDataInterface):
    """
    """
    _modclass = 'simple'
    _modtype = 'hardware'

    # connectors
    _out = {'simple': 'Simple'}

    def on_activate(self, e):
        config = self.getConfiguration()
        if 'interface' in config:
            self.resource = config['interface']
        else:
            self.resource = 'ASRL1::INSTR'

        if 'baudrate' in config:
            self.baudrate = config['baudrate']
        else:
            self.baudrate = 115200

        self.rm = visa.ResourceManager()
        self.log.debug('Resources: {0}'.format(self.rm.list_resources()))
        self.my_instrument = self.rm.open_resource(self.resource, baud_rate=self.baudrate)

    def on_deactivate(self, e):
        self.my_instrument.close()
        self.rm.close()

    def getData(self):
        try:
            return int(self.my_instrument.read_raw().decode('utf-8').rstrip().split()[1])
        except:
            return 0

    def getChannels(self):
        return 1
