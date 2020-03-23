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
import time
import visa

from core.module import Base
from core.configoption import ConfigOption
from interface.process_control_interface import ProcessControlInterface


class PowerSupply(Base, ProcessControlInterface):
    """ Hardware module for power supply Teledyne T3PS3000.

    The ProcessControlInterface only controls channel 1 for now.

    Example config :
        voltage_generator:
            module.Class: 'power_supply.Teledyne_T3PS3000.PowerSupply'
            address: 'ASRL9::INSTR'
            current_max_1: 1
            current_max_2: 0

    """

    _address = ConfigOption('address', missing='error')

    _voltage_max_channel_1 = ConfigOption('voltage_max_channel_1', 30)
    _voltage_max_channel_2 = ConfigOption('voltage_max_channel_2', 30)
    _current_max_1 = ConfigOption('current_max_1', missing='error')
    _current_max_2 = ConfigOption('current_max_2', missing='error')

    _inst = None
    model = ''

    def on_activate(self):
        """ Startup the module """

        rm = visa.ResourceManager()
        try:
            self._inst = rm.open_resource(self._address, write_termination='\n', read_termination='\n')
        except visa.VisaIOError:
            self.log.error('Could not connect to hardware. Please check the wires and the address.')

        self.model = self._query('*IDN?').split(',')[2]

        self._write("OUTPut:TRACK 0")  # independent mode

        self._write("CH1:VOLTage 0")
        self._write("CH2:VOLTage 0")

        self._write("CH1:CURRent {}".format(self._current_max_1))
        self._write("CH2:CURRent {}".format(self._current_max_2))

        time.sleep(0.1)

        self._write("OUTPut CH1,ON")
        self._write("OUTPut CH2,ON")

    def on_deactivate(self):
        """ Stops the module """
        self._write("OUTPut CH1,OFF")
        self._write("OUTPut CH2,OFF")
        self._inst.close()

    def _write(self, cmd):
        """ Function to write command to hardware"""
        self._inst.write(cmd)

    def _query(self, cmd):
        """ Function to query hardware"""
        return self._inst.query(cmd)

    def set_control_value(self, value):
        """ Set control value, here heating power.

            @param flaot value: control value
        """
        mini, maxi = self.get_control_limit()
        if mini <= value <= maxi:
            self._write("CH1:VOLTage {}".format(value))
        else:
            self.log.error('Voltage value {} out of range'.format(value))

    def get_control_value(self):
        """ Get current control value, here heating power

            @return float: current control value
        """
        return float(self._query("MEASure:VOLTage? CH1").split('\r')[0])

    def get_control_unit(self):
        """ Get unit of control value.

            @return tuple(str): short and text unit of control value
        """
        return 'V', 'Volt'

    def get_control_limit(self):
        """ Get minimum and maximum of control value.

            @return tuple(float, float): minimum and maximum of control value
        """
        return 0, self._voltage_max_channel_1
