# -*- coding: utf-8 -*-
"""
This module controls the Coherent OBIS laser.

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

# FIXME: Use PyVisa module instead of serial. Needs general cleanup and rework.
import serial
import time

from qudi.core.module import Base
from qudi.core.configoption import ConfigOption
from qudi.interface.simple_laser_interface import SimpleLaserInterface
from qudi.interface.simple_laser_interface import LaserState, ShutterState, ControlMode


class OBISLaser(Base, SimpleLaserInterface):

    """ Implements the Coherent OBIS laser.

    Example config for copy-paste:

    obis_laser:
        module.Class: 'laser.coherent_obis_laser.OBISLaser'
        com_port: 'COM3'

    """

    eol = '\r'
    _model_name = 'UNKNOWN'

    _com_port = ConfigOption('com_port', missing='error')

    def on_activate(self):
        """ Activate module.
        """
        self.obis = serial.Serial(self._com_port, timeout=1)

        if not self.connect_laser():
            raise Exception('Laser does not seem to be connected.')

        self._model_name = self._communicate('SYST:INF:MOD?')
        self._current_setpoint = self.get_current()

    def on_deactivate(self):
        """ Deactivate module.
        """

        self.disconnect_laser()

    def connect_laser(self):
        """ Connect to Instrument.

        @return bool: connection success
        """
        response = self._communicate('*IDN?')[0]

        if response.startswith('ERR-100'):
            return False
        else:
            return True

    def disconnect_laser(self):
        """ Close the connection to the instrument.
        """
        self.set_laser_state(LaserState.OFF)
        self.obis.close()

    def allowed_control_modes(self):
        """ Control modes for this laser
        """
        return frozenset({ControlMode.UNKNOWN})

    def get_control_mode(self):
        """ Get current laser control mode.

        @return ControlMode: current laser control mode
        """
        return ControlMode.UNKNOWN

    def set_control_mode(self, mode):
        """ Set laser control mode.

        @param ControlMode mode: desired control mode
        @return ControlMode: actual control mode
        """
        if mode != ControlMode.UNKNOWN:
            self.log.warning(self._model_name + ' does not have control modes, '
                             'cannot set to mode {}'.format(mode))

    def get_power(self):
        """ Get laser power.

        @return float: laser power in watts
        """
        # The present laser output power in watts
        return float(self._communicate('SOUR:POW:LEV?'))

    def get_power_setpoint(self):
        """ Get the laser power setpoint.

        @return float: laser power setpoint in watts
        """
        # The present laser power level setting in watts (set level)
        return float(self._communicate('SOUR:POW:LEV:IMM:AMPL?'))

    def get_power_range(self):
        """ Get laser power range.

        @return float[2]: laser power range
        """
        minpower = float(self._communicate('SOUR:POW:LIM:LOW?'))
        maxpower = float(self._communicate('SOUR:POW:LIM:HIGH?'))
        return minpower, maxpower

    def set_power(self, power):
        """ Set laser power

        @param float power: desired laser power in watts
        """
        self._communicate('SOUR:POW:LEV:IMM:AMPL {}'.format(power))

    def get_current_unit(self):
        """ Get unit for laser current.

        @return str: unit for laser current
        """
        return 'A'

    def get_current_range(self):
        """ Get range for laser current.

        @return float[2]: range for laser current
        """
        low = self._communicate('SOUR:CURR:LIM:LOW?')
        high = self._communicate('SOUR:CURR:LIM:HIGH?')
        return float(low), float(high)

    def get_current(self):
        """ Cet current laser current

        @return float: current laser current in amps
        """
        return float(self._communicate('SOUR:POW:CURR?'))

    def get_current_setpoint(self):
        """ Current laser current setpoint.

        @return float: laser current setpoint
        """
        return self._current_setpoint

    def set_current(self, current_percent):
        """ Set laser current setpoint.

        @param float current_percent: laser current setpoint
        """
        self._communicate('SOUR:POW:CURR {}'.format(current_percent))
        self._current_setpoint = current_percent

    def get_shutter_state(self):
        """ Get laser shutter state.

        @return ShutterState: laser shutter state
        """
        return ShutterState.NO_SHUTTER

    def set_shutter_state(self, state):
        """ Set the desired laser shutter state.

        @param ShutterState state: desired laser shutter state
        """
        if state not in (ShutterState.NO_SHUTTER, ShutterState.UNKNOWN):
            self.log.warning(self._model_name + ' does not have a shutter')

    def get_temperatures(self):
        """ Get all available temperatures.

        @return dict: dict of temperature names and value
        """
        return {
            'Diode': self._get_diode_temperature(),
            'Internal': self._get_internal_temperature(),
            'Base Plate': self._get_baseplate_temperature()
        }

    def get_laser_state(self):
        """ Get laser operation state

        @return LaserState: laser state
        """
        state = self._communicate('SOUR:AM:STAT?')
        if 'ON' in state:
            return LaserState.ON
        elif 'OFF' in state:
            return LaserState.OFF
        return LaserState.UNKNOWN

    def set_laser_state(self, status):
        """ Set desited laser state.

        @param LaserState status: desired laser state
        @return LaserState: actual laser state
        """
        if self.get_laser_state() != status:
            if status == LaserState.ON:
                self._communicate('SOUR:AM:STAT ON')
            elif status == LaserState.OFF:
                self._communicate('SOUR:AM:STAT OFF')

    def get_extra_info(self):
        """ Extra information from laser.

        @return str: multiple lines of text with information about laser
        """
        return ('System Model Name: '       + self._communicate('SYST:INF:MOD?')    + '\n'
                'System Manufacture Date: ' + self._communicate('SYST:INF:MDAT?')   + '\n'
                'System Calibration Date: ' + self._communicate('SYST:INF:CDAT?')   + '\n'
                'System Serial Number: '    + self._communicate('SYST:INF:SNUM?')   + '\n'
                'System Part Number: '      + self._communicate('SYST:INF:PNUM?')   + '\n'
                'Firmware version: '        + self._communicate('SYST:INF:FVER?')   + '\n'
                'System Protocol Version: ' + self._communicate('SYST:INF:PVER?')   + '\n'
                'System Wavelength: '       + self._communicate('SYST:INF:WAV?')    + '\n'
                'System Power Rating: '     + self._communicate('SYST:INF:POW?')    + '\n'
                'Device Type: '             + self._communicate('SYST:INF:TYP?')    + '\n'
                'System Power Cycles: '     + self._communicate('SYST:CYCL?')       + '\n'
                'System Power Hours: '      + self._communicate('SYST:HOUR?')       + '\n'
                'Diode Hours: '             + self._communicate('SYST:DIOD:HOUR?')
                )

########################## communication methods ###############################

    def _send(self, message):
        """ Send a message to to laser

        @param string message: message to be delivered to the laser
        """
        new_message = message + self.eol
        self.obis.write(new_message.encode())

    def _communicate(self, message):
        """ Send a receive messages with the laser

        @param string message: message to be delivered to the laser

        @returns string response: message received from the laser
        """
        self._send(message)
        time.sleep(0.1)
        response_len = self.obis.inWaiting()
        response = []

        while response_len > 0:
            this_response_line = self.obis.readline().decode().strip()
            if (response_len == 4) and (this_response_line == 'OK'):
                response.append('')
            else:
                response.append(this_response_line)
            response_len = self.obis.inWaiting()

        # Potentially multi-line responses - need to be joined into string
        full_response = ''.join(response)

        if full_response == 'ERR-100':
            self.log.warning(self._model_name + ' does not support the command ' + message)
            return '-1'

        return full_response

########################## internal methods ####################################

    def _get_diode_temperature(self):
        """ Get laser diode temperature

        @return float: laser diode temperature
        """
        response = float(self._communicate('SOUR:TEMP:DIOD?').split('C')[0])
        return response

    def _get_internal_temperature(self):
        """ Get internal laser temperature

        @return float: internal laser temperature
        """
        return float(self._communicate('SOUR:TEMP:INT?').split('C')[0])

    def _get_baseplate_temperature(self):
        """ Get laser base plate temperature

        @return float: laser base plate temperature
        """
        return float(self._communicate('SOUR:TEMP:BAS?').split('C')[0])

    def _get_interlock_status(self):
        """ Get the status of the system interlock

        @returns bool interlock: status of the interlock
        """
        response = self._communicate('SYST:LOCK?')

        if response.lower() == 'ok':
            return True
        elif response.lower() == 'off':
            return False
        else:
            return False

    def _set_laser_to_11(self):
        """ Set the laser power to 11
        """
        self.set_power(0.165)
