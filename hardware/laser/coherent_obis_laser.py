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

from core.module import Base, ConfigOption
from interface.simple_laser_interface import SimpleLaserInterface
from interface.simple_laser_interface import LaserState
from interface.simple_laser_interface import ShutterState

import serial
import time

        
class OBISLaser(Base, SimpleLaserInterface):

    """ Implements the Coherent OBIS laser.

    Example configuration:
    ```
    # obis:
    #     module.Class: 'SimpleLaserInterface.OBISLaser'
    ```
    """

    _modclass = 'laser'
    _modtype = 'hardware'

    eol = '\r'
    _model_name = 'UNKNOWN'

    def on_activate(self):
        """ Activate module.
        """
        self.obis = serial.Serial('COM3', timeout=1)

        connected = self.connect_laser()

        if not connected:
            self.log.error('Laser does not seem to be connected.')
            return -1
        else:
            self._model_name = self._communicate('SYST:INF:MOD?')
            return 0

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
        self.off()
        self.obis.close()

    def allowed_control_modes(self):
        """ Control modes for this laser
        """
        self.log.warning(self._model_name + ' does not have control modes')

    def get_control_mode(self):
        """ Get current laser control mode.

        @return ControlMode: current laser control mode
        """
        self.log.warning(self._model_name + ' does not have control modes, cannot get current mode.')

    def set_control_mode(self, mode):
        """ Set laser control mode.

        @param ControlMode mode: desired control mode
        @return ControlMode: actual control mode
        """
        self.log.warning(self._model_name + ' does not have control modes, '
                         'cannot set to mode {}'.format(mode)
                        )

    def get_power(self):
        """ Get laser power.

            @return float: laser power in watts
        """
        # The present laser output power in watts
        response = self._communicate('SOUR:POW:LEV?')

        return float(response)

    def get_power_setpoint(self):
        """ Get the laser power setpoint.

        @return float: laser power setpoint in watts
        """
        # The present laser power level setting in watts (set level)
        response = self._communicate('SOUR:POW:LEV:IMM:AMPL?')
        return float(response)

    def get_power_range(self):
        """ Get laser power range.

        @return tuple(float, float): laser power range
        """

        minpower = float(self._communicate('SOUR:POW:LIM:LOW?'))
        maxpower = float(self._communicate('SOUR:POW:LIM:HIGH?'))
        return (minpower, maxpower)

    def set_power(self, power):
        """ Set laser power

        @param float power: desired laser power in watts
        """
        self._communicate('SOUR:POW:LEV:IMM:AMPL {}'.format(power))

    def get_current_unit(self):
        """ Get unit for laser current.

        @return str: unit for laser curret
        """
        return 'A'  # amps

    def get_current_range(self):
        """ Get range for laser current.

        @return tuple(flaot, float): range for laser current
        """
        low = self._communicate('SOUR:CURR:LIM:LOW?')
        high = self._communicate('SOUR:CURR:LIM:HIGH?')

        return (float(low), float(high))

    def get_current(self):
        """ Cet current laser current

        @return float: current laser current in amps
        """
        return float(self._communicate('SOUR:POW:CURR?'))

    def get_current_setpoint(self):
        """ Current laser current setpoint.

        @return float: laser current setpoint
        """
        self.log.warning('Getting the current setpoint is not supported by the ' + self._model_name)
        return -1

    def set_current(self, current_percent):
        """ Set laser current setpoint.

        @param float current_percent: laser current setpoint
        """
        self._communicate('SOUR:POW:CURR {}'.format(current_percent))
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
        self.log.warning(self._model_name + ' does not have a shutter')
        return self.get_shutter_state()

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

    def get_temperatures(self):
        """ Get all available temperatures.

            @return dict: dict of temperature names and value
        """
        return {
            'Diode': self._get_diode_temperature(),
            'Internal': self._get_internal_temperature(),
            'Base Plate': self._get_baseplate_temperature()
        }

    def set_temperatures(self, temps):
        """ Set temperature for lasers with adjustable temperature for tuning

        @return dict: dict with new temperature setpoints
        """
        self.log.warning(self._model_name + ' cannot set temperatures.')
        return {}

    def get_temperature_setpoints(self):
        """ Get temperature setpints.

        @return dict: dict of temperature name and setpoint value
        """
        self.log.warning(self._model_name + ' has no temperature setpoints.')
        return {}

    def get_laser_state(self):
        """ Get laser operation state

        @return LaserState: laser state
        """
        state = self._communicate('SOUR:AM:STAT?')
        if 'ON' in state:
            return LaserState.ON
        elif 'OFF' in state:
            return LaserState.OFF
        else:
            return LaserState.UNKNOWN

    def set_laser_state(self, status):
        """ Set desited laser state.

        @param LaserState status: desired laser state
        @return LaserState: actual laser state
        """
        # TODO: this is big. cannot be called without having LaserState, 
        #       which is only defined in the simple laser interface.
        #       I think this shoudl be a private method.
        actstat = self.get_laser_state()
        if actstat != status:

            if status == LaserState.ON:
                self._communicate('SOUR:AM:STAT ON')
                #return self.get_laser_state()
            elif status == LaserState.OFF:
                self._communicate('SOUR:AM:STAT OFF')
                #return self.get_laser_state()
            return self.get_laser_state()

    def on(self):
        """ Turn laser on.

            @return LaserState: actual laser state
        """
        status = self.get_laser_state()
        if status == LaserState.OFF:
            self._communicate('SOUR:AM:STAT ON')
            return self.get_laser_state()
        else:
            return self.get_laser_state()

        # """return self.set_laser_state(LaserState.ON)"""

    def off(self):
        """ Turn laser off.

            @return LaserState: actual laser state
        """
        self.set_laser_state(LaserState.OFF)
        return self.get_laser_state()

    def get_extra_info(self):
        """ Extra information from laser.

        @return str: multiple lines of text with information about laser
        """

        extra = ('System Model Name: '      + self._communicate('SYST:INF:MOD?')    + '\n'
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

        return extra

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

    def _set_laser_to_11(self):
        """ Set the laser power to 11
        """
        self.set_power(0.165)

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
