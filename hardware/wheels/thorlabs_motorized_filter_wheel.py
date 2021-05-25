# -*- coding: utf-8 -*-
"""
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
from core.module import Base
from core.configoption import ConfigOption


class ThorlabsMotorizedFilterWheel(Base):
    """ This class is implements communication with Thorlabs Motorized Filter Wheels

    Example config for copy-paste:

    thorlabs_wheel:
        module.Class: 'wheels.thorlabs_motorized_filter_wheel.ThorlabsMotorizedFilterWheel'
        interface: 'COM6'

    Description of the hardware provided by Thorlabs:
        These stepper-motor-driven filter wheels are designed for use in a host of automated applications including
        color CCD photography, fluorescence microscopy, and photometry. Each unit consists of a motorized housing
        and a preinstalled filter wheel with either 6 positions for Ø1" (Ø25 mm) optics or 12 positions
        for Ø1/2" (Ø12.5 mm) optics. Filter wheels of either type can also be purchased separately and installed
        by the user.
    """

    interface = ConfigOption('interface', 'COM3', missing='error')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rm = None
        self._inst = None

    def on_activate(self):
        """ Module activation method """
        self._rm = visa.ResourceManager()
        try:
            self._inst = self._rm.open_resource(self.interface, baud_rate=115200, write_termination='\r',
                                                read_termination='\r')
            idn = self._query('*idn?')
            self.log.debug('Connected to : {}'.format(idn))
        except visa.VisaIOError:
            self.log.error('Could not connect to device')

    def on_deactivate(self):
        """ Disconnect from hardware on deactivation. """
        self._inst.close()
        self._rm.close()

    def _query(self, text):
        """ Send query, get and return answer """
        echo = self._write(text)
        answer = self._inst.read()
        return answer

    def _write(self, text):
        """ Write command, do not expect answer """
        self._inst.write(text)
        echo = self._inst.read()
        return echo

    def get_position(self):
        """ Get the current position, from 1 to 6 (or 12) """
        position = self._query('pos?')
        return int(position)

    def set_position(self, value):
        """ Set the position to a given value

        The wheel will take the shorter path. If upward or downward are equivalent, the wheel take the upward path.
        """
        res = self._write("pos={}".format(int(value)))
