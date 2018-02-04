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


class PSUTypes(Enum):
    """ LaserQuantum power supply types.
    """
    FPU = 0
    MPC6000 = 1
    MPC3000 = 2
    SMD12 = 3
    SMD6000 = 4


class LaserCobolt(Base, SimpleLaserInterface):
    """
    This module implements communication with the Edwards turbopump and
    vacuum equipment.
    """
    _modclass = 'claser'
    _modtype = 'hardware'

    serial_interface = ConfigOption('interface', 'COM1', missing='warn')
    maxpower = ConfigOption('maxpower', 0.250, missing='warn')

    def on_activate(self):
        """ Activate module.
        """
        self.control_mode = ControlMode.POWER
        self.connect_laser(self.serial_interface)

    def on_deactivate(self):
        """ Deactivate module.
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
                write_termination='\r\n',
                read_termination='\r\n',
                send_end=True)
            # give laser 2 seconds maximum to reply
            self.inst.timeout = 2000
        except visa.VisaIOError:
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
        """
        return [ControlMode.POWER, ControlMode.CURRENT]

    def get_control_mode(self):
        """ Get current laser control mode.
        @return ControlMode: current laser control mode
        """

        return self.control_mode

    def set_control_mode(self, mode):
        """ Set laser control mode.
        @param ControlMode mode: desired control mode
        @return ControlMode: actual control mode
        """

        if mode == ControlMode.POWER:
            reply1 = self.inst.query('cp')
            self.log.debug("Set POWER control mode {0}.".format(reply1))
        else:
            reply1 = self.inst.query('ci')
            self.log.debug("Set CURRENT control mode {0}.".format(reply1))
        self.control_mode=mode
        return mode

    def get_power(self):
        """ Get laser power.
            @return float: laser power in watts
        """
        answer = self.inst.query('pa?')
        try:
            return float(answer)
        except ValueError:
            self.log.exception("Answer was {0}.".format(answer))
            return -1

    def get_power_setpoint(self):
        """ Get the laser power setpoint.
        @return float: laser power setpoint in watts
        """
        answer = self.inst.query('ps?')
        try:
            return float(answer)
        except ValueError:
            self.log.exception("Answer was {0}.".format(answer))
            return -1


    def get_power_range(self):
        """ Get laser power range.
        @return tuple(float, float): laser power range
        """

        answer = self.inst.query('gmlp?')
        try:
            return 0, float(answer)/1000
        except ValueError:
            return 0, 500e-3

    def set_power(self, power):
        """ Set laser power
        @param float power: desired laser power in watts
        """

        self.inst.query('p {0}'.format(power))

    def get_current_unit(self):
        """ Get unit for laser current.
            @return str: unit for laser current
        """
        return 'A'

    def get_current_range(self):
        """ Get range for laser current.
            @return tuple(flaot, float): range for laser current
        """
        return 0, 100

    def get_current(self):
        """ Cet current laser current
        @return float: current laser current
        """
        return float(self.inst.query('i?'))

    def get_current_setpoint(self):
        """ Current laser current setpoint.
        @return float: laser current setpoint
        """
        return float(self.inst.query('i?'))


    def set_current(self, current):
        """ Set laser current setpoint.
        @param float current_percent: laser current setpoint
        """
        self.inst.query('slc'.format(current))
        return self.get_current()

    def get_shutter_state(self):
        """ Get laser shutter state.
        @return ShutterState: laser shutter state
        """
        return ShutterState.NOSHUTTER

    def set_shutter_state(self, state):
        """ Set the desired laser shutter state.
        @param ShutterState state: desired laser shutter state
        @return ShutterState: actual laser shutter state
        """
        return self.get_shutter_state()

    def get_psu_temperature(self):
        """ Get power supply temperature
        @return float: power supply temperature
        """
        return 0

    def get_laser_temperature(self):
        """ Get laser head temperature
        @return float: laser head temperature
        """
        return 0

    def get_temperatures(self):
        """ Get all available temperatures.
            @return dict: dict of temperature names and value
        """
        return {
            'psu': self.get_psu_temperature(),
            'laser': self.get_laser_temperature()
            }

    def set_temperatures(self, temps):
        """ Set temperature for lasers with adjustable temperature for tuning
            @return dict: dict with new temperature setpoints
        """
        return {}

    def get_temperature_setpoints(self):
        """ Get temperature setpints.
            @return dict: dict of temperature name and setpoint value
        """
        return {}

    def get_lcd(self):
        """ Get the text displayed on the PSU display.
            @return str: text on power supply display
        """
        return ''


    def get_laser_state(self):
        """ Get laser operation state
        @return LaserState: laser state
        """
        state = self.inst.query('l?')
        if '1' in state:
            return LaserState.ON
        elif '0' in state:
            return LaserState.OFF
        else:
            return LaserState.UNKNOWN

    def set_laser_state(self, status):
        """ Set desited laser state.
        @param LaserState status: desired laser state
        @return LaserState: actual laser state
        """
        actstat = self.get_laser_state()
        if actstat != status:
            if status == LaserState.ON:
                self.inst.query('l1')
            elif status == LaserState.OFF:
                self.inst.query('l0')
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

    def get_firmware_version(self):
        """ Ask the laser for ID.
        @return str: what the laser tells you about itself
        """
        self.inst.write('ver?')
        lines = []
        try:
            while True:
                lines.append(self.inst.read())
        except:
            pass
        return lines

    def dump(self):
        """ Return  information dump
        @return str: diagnostic information dump from laser
        """
        self.inst.write('?')
        lines = []
        try:
            while True:
                lines.append(self.inst.read())
        except:
            pass
        return lines

    def timers(self):
        """ Return information about component runtimes.
            @return str: runtimes of components
        """
        self.inst.write('leds?')
        lines = []
        try:
            while True:
                lines.append(self.inst.read())
        except:
            pass
        return lines

    def get_extra_info(self):
        """ Extra information from laser.
            @return str: multiple lines of text with information about laser
            For LaserQuantum devices, this is the firmware version, dump and timers information
        """
        extra = ''
        extra += '\n'.join(self.get_firmware_version())
        extra += '\n'
        extra += '\n'.join(self.timers())
        extra += '\n'
        return extra