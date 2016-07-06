# -*- coding: utf-8 -*-
"""
This module controls LaserQuantum lasers.

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

from core.base import Base
from interface.simple_laser_interface import *
from enum import Enum
import visa


class PSUTypes(Enum):
    FPU = 0
    MPC6000 = 1
    MPC3000 = 2
    SMD12 = 3
    SMD6000 = 4


class LaserQuantumLaser(Base, SimpleLaserInterface):
    """
    This module implements communication with the Edwards turbopump and
    vacuum equipment.
    """
    _modclass = 'lqlaser'
    _modtype = 'hardware'

    # connectors
    _out = {'laser': 'Laser'}

    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, configuration=config, callbacks=c_dict)

    def activation(self, e):
        """

        @param e:
        @return:
        """
        config = self.getConfiguration()
        self.psu = PSUTypes[config['psu']]
        self.connect_laser(config['interface'])

    def deactivation(self, e):
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
            rate = 9600 if self.psu == PSUTypes['SMD6000'] else 19200
            self.inst = self.rm.open_resource(
                interface,
                baud_rate=rate,
                write_termination='\r\n',
                read_termination='\r\n',
                send_end=True)
            self.inst.timeout = 50
        except visa.VisaIOError as e:
            self.logExc()
            return False
        else:
            return True

    def disconnect_laser(self):
        """
        Close the connection to the instrument.
        """
        self.inst.close()
        self.rm.close()

    def get_control_mode(self):
        """

        @return:
        """
        if self.psu == PSUTypes['FPU']:
            return ControlMode['MIXED']
        elif self.psu == PSUTypes['SMD6000']:
            return ControlMode['POWER']
        else:
            return ControlMode[self.inst.query('CONTROL?')]

    def set_control_mode(self, mode):
        """

        @param mode:
        @return:
        """
        if self.psu == PSUTypes['FPU']:
            return ControlMode['MIXED']
        elif self.psu == PSUTypes['SMD6000']:
            return ControlMode['POWER']
        else:
            if mode == ControlMode['POWER']:
                self.inst.query('PFB=OFF')
                self.inst.query('CONTROL=POWER')
            else:
                self.inst.query('PFB=ON')
                self.inst.query('CONTROL=CURRENT')
        return self.get_control_mode()

    def get_power(self):
        """

        @return:
        """
        answer = self.inst.query('POWER?')
        if "mW" in answer:
            return float(answer.split('mW')[0])/1000
        elif 'W' in answer:
            return float(answer.split('W')[0])
        else:
            return float(answer)

    def get_power_setpoint(self):
        """

        @return:
        """
        if self.psu != PSUTypes['SMD6000']:
            answer = self.inst.query('SETPOWER?')
            if "mW" in answer:
                return float(answer.split('mW')[0]) / 1000
            elif 'W' in answer:
                return float(answer.split('W')[0])
            else:
                return float(answer)
        else:
            return self.get_power()

    def set_power_setpoint(self, power):
        """

        @param power:
        @return:
        """
        if self.psu == PSUTypes['FPU']:
            self.inst.query('POWER={:f}'.format(power))
        else:
            self.inst.query('POWER={:f}'.format(power*1000))

    def get_current(self):
        """

        @return:
        """
        if self.psu == PSUTypes['MPC3000'] or self.psu == PSUTypes['MPC6000']:
            return float(self.inst.query('SETCURRENT1?').split('%')[0])
        else:
            return float(self.inst.query('CURRENT?').split('%')[0])

    def get_current_setpoint(self):
        """

        @return:
        """
        if self.psu == PSUTypes['MPC3000'] or self.psu == PSUTypes['MPC6000']:
            return float(self.inst.query('SETCURRENT1?').split('%')[0])
        else:
            return float(self.inst.query('SETCURRENT?').split('%')[0])

    def set_current(self, current_percent):
        """

        @param current_percent:
        @return:
        """
        self.inst.query('CURRENT={}'.format(current_percent))
        return self.get_current()

    def get_shutter_state(self):
        """

        @return:
        """
        if self.psu == PSUTypes['FPU']:
            state = self.inst.query('SHUTTER?')
            if 'OPEN' in state:
                return ShutterState['OPEN']
            elif 'CLOSED' in state:
                return ShutterState['CLOSED']
            else:
                return ShutterState['UNKNOWN']
        else:
            return ShutterState['NOSHUTTER']

    def set_shutter_state(self, state):
        """

        @param state:
        @return:
        """
        if self.psu == PSUTypes['FPU']:
            actstate = self.get_shutter_state()
            if state != actstate:
                if state == ShutterState['OPEN']:
                    self.inst.query('SHUTTER OPEN')
                elif state == ShutterState['CLOSED']:
                    self.inst.query('SHUTTER CLOSE')
        return self.get_shutter_state()

    def get_psu_temperature(self):
        """

        @return:
        """
        return float(self.inst.query('PSUTEMP?').split('C')[0])

    def get_laser_temperature(self):
        """

        @return:
        """
        return float(self.inst.query('LASTEMP?').split('C')[0])

    def get_temperatures(self):
        return {
            'psu': self.get_psu_temperature(),
            'laser': self.get_laser_temperature()
            }

    def set_temperatures(self, temps):
        return {}

    def get_lcd(self):
        """

        @return:
        """
        if self.psu == PSUTypes['SMD12'] or self.psu == PSUTypes['SMD6000']:
            return ''
        else:
            return self.inst.query('STATUSLCD?')

    def get_laser_state(self):
        """

        @return:
        """
        if self.psu == PSUTypes['SMD6000']:
            state = self.inst.query('STAT?')
        else:
            state = self.inst.query('STATUS?')
        if 'ENABLED' in state:
            return LaserState['ON']
        elif 'DISABLED' in state:
            return LaserState['OFF']
        else:
            return LaserState['UNKNOWN']

    def set_laser_state(self, status):
        """

        @param status:
        @return:
        """
        actstat = self.get_laser_state()
        if actstat != status:
            if status == LaserState['ON']:
                self.inst.query('ON')
            elif status == LaserState['OFF']:
                self.inst.query('OFF')
        return self.get_laser_state()

    def on(self):
        return self.set_laser_state(LaserState['ON'])

    def off(self):
        return self.set_laser_state(LaserState['OFF'])

    def get_firmware_version(self):
        """ Ask the laser for ID.

        @return str: what the laser tells you about itself
        """
        if self.psu == PSUTypes['SMD6000']:
            self.inst.write('VERSION')
        else:
            self.inst.write('SOFTVER?')
        lines = []
        try:
            while True:
                lines.append(self.inst.read())
        except:
            pass
        return lines

    def dump(self):
        """

        @return:
        """
        self.inst.write('DUMP ')
        lines = []
        try:
            while True:
                lines.append(self.inst.read())
        except:
            pass
        return lines

    def timers(self):
        """

        @return:
        """
        self.inst.write('TIMERS')
        lines = []
        try:
            while True:
                lines.append(self.inst.read())
        except:
            pass
        return lines

    def get_extra_info(self):
        extra = ''
        extra += '\n'.join(self.get_firmware_version())
        extra += '\n'
        extra += '\n'.join(self.dump())
        extra += '\n'
        extra += '\n'.join(self.timers())
        extra += '\n'
        return extra

