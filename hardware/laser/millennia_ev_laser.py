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

from core.module import Base, ConfigOption
from interface.simple_laser_interface import SimpleLaserInterface
from interface.simple_laser_interface import ControlMode
from interface.simple_laser_interface import ShutterState
from interface.simple_laser_interface import LaserState
from enum import Enum
import visa


class Models(Enum):
    """ Model numbers for Millennia lasers
    """
    MilEV = 0


class MillenniaeVLaser(Base, SimpleLaserInterface):
    """
    Spectra Physics Millennia diode pumped solid state laser
    """
    _modclass = 'millenniaevlaser'
    _modtype = 'hardware'

    serial_interface = ConfigOption('interface', 'ASRL1::INSTR', missing='warn')
    maxpower = ConfigOption('maxpower', 25.0, missing='warn')

    def on_activate(self):
        """ Activate Module.
        """
        self.connect_laser(self.serial_interface)

    def on_deactivate(self):
        """ Deactivate module
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
            self.inst.timeout = 1000
            idn = self.inst.query('*IDN?')
            (self.mfg, self.model, self.serial, self.version) = idn.split(',')
        except visa.VisaIOError as e:
            self.log.exception('Communication Failure:')
            return False
        else:
            return True

    def disconnect_laser(self):
        """ Close the connection to the instrument.
        """
        self.inst.close()
        self.rm.close()

    def allowed_control_modes(self):
        """ Control modes for this laser

            @return ControlMode: available control modes
        """
        return [ControlMode.MIXED]

    def get_control_mode(self):
        """ Get active control mode

        @return ControlMode: active control mode
        """
        return ControlMode.MIXED

    def set_control_mode(self, mode):
        """ Set actve control mode

        @param ControlMode mode: desired control mode
        @return ControlMode: actual control mode
        """
        return ControlMode.MIXED

    def get_power(self):
        """ Current laser power

        @return float: laser power in watts
        """
        answer = self.inst.query('?P')
        return float(answer)

    def get_power_setpoint(self):
        """ Current laser power setpoint

        @return float: power setpoint in watts
        """
        answer = self.inst.query('?PSET')
        return float(answer)

    def get_power_range(self):
        """ Laser power range

        @return (float, float): laser power range
        """
        return 0, self.maxpower

    def set_power(self, power):
        """ Set laser power setpoint

        @param float power: desired laser power

        @return float: actual laser power setpoint
        """
        self.inst.query('P:{0:f}'.format(power))
        return self.get_power_setpoint()

    def get_current_unit(self):
        """ Get unit for current

            return str: unit for laser current
        """
        return 'A'

    def get_current_range(self):
        """ Get range for laser current

            @return (float, float): range for laser current
        """
        maxcurrent = float(self.inst.query('?DCL'))
        return (0, maxcurrent)

    def get_current(self):
        """ Get current laser current

        @return float: current laser current
        """
        return float(self.inst.query('?C1'))

    def get_current_setpoint(self):
        """ Get laser current setpoint

        @return float: laser current setpoint
        """
        return float(self.inst.query('?CS1'))

    def set_current(self, current_percent):
        """ Set laser current setpoint

        @param float current_percent: desired laser current setpoint
        @return float: actual laer current setpoint
        """
        self.inst.query('C:{0}'.format(current_percent))
        return self.get_current_setpoint()

    def get_shutter_state(self):
        """ Get laser shutter state

        @return ShutterState: current laser shutter state
        """
        state = self.inst.query('?SHT')
        if 'OPEN' in state:
            return ShutterState.OPEN
        elif 'CLOSED' in state:
            return ShutterState.CLOSED
        else:
            return ShutterState.UNKNOWN

    def set_shutter_state(self, state):
        """ Set laser shutter state.

        @param ShuterState state: desired laser shutter state
        @return ShutterState: actual laser shutter state
        """
        actstate = self.get_shutter_state()
        if state != actstate:
            if state == ShutterState.OPEN:
                self.inst.query('SHT:1')
            elif state == ShutterState.CLOSED:
                self.inst.query('SHT:0')
        return self.get_shutter_state()

    def get_crystal_temperature(self):
        """ Get SHG crystal temerpature.

            @return float: SHG crystal temperature in degrees Celsius
        """
        return float(self.inst.query('?SHG'))

    def get_diode_temperature(self):
        """ Get laser diode temperature.

            @return float: laser diode temperature in degrees Celsius
        """
        return float(self.inst.query('?T'))

    def get_tower_temperature(self):
        """ Get SHG tower temperature

            @return float: SHG tower temperature in degrees Celsius
        """
        return float(self.inst.query('?TT'))

    def get_cab_temperature(self):
        """ Get cabinet temperature

            @return float: get laser cabinet temperature in degrees Celsius
        """
        return float(self.inst.query('?CABTEMP'))

    def get_temperatures(self):
        """ Get all available temperatures

            @return dict: tict of temperature names and values
        """
        return {
            'crystal': self.get_crystal_temperature(),
            'diode': self.get_diode_temperature(),
            'tower': self.get_tower_temperature(),
            'cab': self.get_cab_temperature(),
            }

    def set_temperatures(self, temps):
        """ Set temperatures for lasers wth tunable temperatures

        """
        return {}

    def get_temperature_setpoints(self):
        """ Get tepmerature setpoints.

            @return dict: setpoint name and value
        """
        shgset = int(self.inst.query('?SHGS'))
        return {'shg': shgset}

    def get_laser_state(self):
        """ Get laser state.

        @return LaserState: current laser state
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
        """ Set laser state

        @param LaserState status: desited laser state
        @return LaserState: actual laser state
        """
        actstat = self.get_laser_state()
        if actstat != status:
            if status == LaserState.ON:
                self.inst.query('ON')
            elif status == LaserState.OFF:
                self.inst.query('OFF')
        return self.get_laser_state()

    def on(self):
        """ Turn laser on.

            @return LaserState: actual laser state
        """
        return self.set_laser_state(LaserState.ON)

    def off(self):
        """ Turn laser off.

            @return LaserState: actual laser state
        """
        return self.set_laser_state(LaserState.OFF)

    def dump(self):
        """ Dump laser information.

        @return str: laser information
        """
        lines = ''
        lines += 'Didoe Serial: {0}\n'.format(self.inst.query('?DSN'))
        return lines

    def timers(self):
        """ Laser component runtimes

        @return str: laser component run times
        """
        lines = ''
        lines += 'Diode ON: {0}\n'.format(self.inst.query('?DH'))
        lines += 'Head ON: {0}\n'.format(self.inst.query('?HEADHRS'))
        lines += 'PSU ON: {0}\n'.format(self.inst.query('?PSHRS'))
        return lines

    def get_extra_info(self):
        """ Formatted information about the laser.

            @return str: Laser information
        """
        extra = ''
        extra += '{0}\n{1}\n{2}\n{3}\n'.format(self.mfg, self.model, self.serial, self.version)
        extra += '\n'
        extra += '\n {0}'.format(self.timers())
        extra += '\n'
        return extra

