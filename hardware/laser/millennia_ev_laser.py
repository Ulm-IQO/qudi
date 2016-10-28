# -*- coding: utf-8 -*-
"""
This module controls LaserQuantum lasers.

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

from core.base import Base
from interface.simple_laser_interface import SimpleLaserInterface
from interface.simple_laser_interface import ControlMode
from interface.simple_laser_interface import ShutterState
from interface.simple_laser_interface import LaserState
from enum import Enum
import visa


class Models(Enum):
    MilEV = 0


class MillenniaeVLaser(Base, SimpleLaserInterface):
    """
    This module implements communication with the Edwards turbopump and
    vacuum equipment.
    """
    _modclass = 'millenniaevlaser'
    _modtype = 'hardware'

    # connectors
    _out = {'laser': 'Laser'}

    def on_activate(self, e):
        """

        @param e:
        @return:
        """
        config = self.getConfiguration()
        self.connect_laser(config['interface'])

    def on_deactivate(self, e):
        """
        @param e:
        @return:
        """
        self.disconnect_laser()

    def connect_laser(self, interface):
        """ Connect to Instrument.

            @param str interface: visa interface identifier

            @return bool: connection success
        """
        try:
            self.rm = visa.ResourceManager()
            rate = 115200
            self.inst = self.rm.open_resource(
                interface,
                baud_rate=rate,
                write_termination='\n',
                read_termination='\n',
                send_end=True)
            self.inst.timeout = 500
            (self.mfg, self.model, self.serial) = self.inst.query('*IDN?').split(',')
        except visa.VisaIOError as e:
            self.log.exception('Communication Failure:')
            return False
        else:
            return True

    def disconnect_laser(self):
        """
        Close the connection to the instrument.
        """
        self.inst.close()
        self.rm.close()

    def allowed_control_modes(self):
        """ Control modes for this laser"""
        return [ControlMode.POWER]

    def get_control_mode(self):
        """

        @return:
        """
        return ControlMode.MIXED

    def set_control_mode(self, mode):
        """

        @param mode:
        @return:
        """
        return ControlMode.MIXED

    def get_power(self):
        """

        @return:
        """
        answer = self.inst.query('?P')
        return float(answer)

    def get_power_setpoint(self):
        """

        @return:
        """
        answer = self.inst.query('?PSET')
        return float(answer)

    def get_power_range(self):
        """

        @return:
        """
        return tuple([0, 25])

    def set_power(self, power):
        """

        @param power:
        @return:
        """
        self.inst.query('P:{0:f}'.format(power))
        return self.get_power_setpoint()

    def get_current(self):
        """

        @return:
        """
        return float(self.inst.query('?C'))

    def get_current_setpoint(self):
        """

        @return:
        """
        return float(self.inst.query('?CS'))

    def set_current(self, current_percent):
        """

        @param current_percent:
        @return:
        """
        self.inst.query('C:{0}'.format(current_percent))
        return self.get_current_setpoint()

    def get_shutter_state(self):
        """

        @return:
        """
        state = self.inst.query('?SHT')
        if 'OPEN' in state:
            return ShutterState.OPEN
        elif 'CLOSED' in state:
            return ShutterState.CLOSED
        else:
            return ShutterState.UNKNOWN

    def set_shutter_state(self, state):
        """

        @param state:
        @return:
        """
        actstate = self.get_shutter_state()
        if state != actstate:
            if state == ShutterState.OPEN:
                self.inst.query('SHT:1')
            elif state == ShutterState.CLOSED:
                self.inst.query('SHT:0')
        return self.get_shutter_state()

    def get_baseplate_temperature(self):
        return float(self.inst.query('?HS'))

    def get_crystal_temperature(self):
        return float(self.inst.query('?SHG'))

    def get_diode_temperature(self):
        return float(self.inst.query('?T'))

    def get_chassis_temperature(self):
        return float(self.inst.query('?TC'))

    def get_tower_temperature(self):
        return float(self.inst.query('?TT'))

    def get_cab_temperature(self):
        return float(self.inst.query('?CABTEMP'))

    def get_temperatures(self):
        return {
            'base': self.get_base_temperature(),
            'crystal': self.get_crystal_temperature(),
            'diode': self.get_diode_temperature(),
            'chassis': self.get_chassis_temperature(),
            'tower': self.get_tower_temperature(),
            'cab': self.get_cab_temperature(),
            }

    def set_temperatures(self, temps):
        return {}

    def get_temperature_setpoints(self):
        shgset int(self.inst.query('?SHGS'))
        return {'shg': shgset}

    def get_laser_state(self):
        """

        @return:
        """
        diode = int(self.inst.query('?D'))
        state = self.inst.query('?F')

        if state in ('SYS ILK', 'KEY ILK'):
            return LaserState.LOCKED
        elif state == 'SYSTEM OK':
            if diode == 1:
                return LaserState.ON
            elif diode == 0:
                return LaserState.OFF
            else:
                return LaserState.UNKNOWN
        else:
            return LaserState.UNKNOWN

    def set_laser_state(self, status):
        """

        @param status:
        @return:
        """
        actstat = self.get_laser_state()
        if actstat != status:
            if status == LaserState.ON:
                self.inst.query('ON')
            elif status == LaserState.OFF:
                self.inst.query('OFF')
        return self.get_laser_state()

    def on(self):
        return self.set_laser_state(LaserState.ON)

    def off(self):
        return self.set_laser_state(LaserState.OFF)

    def dump(self):
        """

        @return:
        """
        lines = ''
        lines += 'Didoe Serial: {0}\n'.format(self.inst.query('?DSN'))
        return lines

    def timers(self):
        """

        @return:
        """
        lines = ''
        lines += 'Diode ON: {0}\n'.format(self.inst.query('?DH'))
        lines += 'Head ON: {0}\n'.format(self.inst.query('?HEADHRS'))
        lines += 'PSU ON: {0}\n'.format(self.inst.query('?PSHRS'))
        return lines

    def get_extra_info(self):
        extra = ''
        extra += '\n'.join((self.mfg, self.model, self.serial))
        extra += '\n'
        extra += '\n'.join(self.timers())
        extra += '\n'
        return extra

