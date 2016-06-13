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

Copyright (C) 2016 Jan M. Binder jan.binder@uni-ulm.de
"""

from core.base import Base
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from interface.simple_laser_interface import SimpleLaserInterface, ControlModes
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
            return ControlModes['MIXED']
        elif self.psu == PSUTypes['SMD6000']:
            #power = self.inst.ask('POWER?')
            #if '0000' in power:
            #    return ControlModes['CURRENT']
            #else:
            return ControlModes['POWER']
        else:
            return ControlModes[self.inst.ask('CONTROL?')]

    def set_control_mode(self, mode):
        """

        @param mode:
        @return:
        """
        if self.psu == PSUTypes['FPU']:
            return ControlModes['MIXED']
        elif self.psu == PSUTypes['SMD6000']:
            #if mode == ControlModes['POWER']:
            #    power = self.inst.ask('POWER?')
            #    self.inst.ask('POWER={}'.format(power))
            #else:
            #    self.inst.ask('POWER=0')
            return ControlModes['POWER']
        else:
            if mode == ControlModes['POWER']:
                self.inst.ask('PFB=OFF')
                self.inst.ask('CONTROL=POWER')
            else:
                self.inst.ask('PFB=ON')
                self.inst.ask('CONTROL=CURRENT')
        return self.get_control_mode()

    def get_power(self):
        """

        @return:
        """
        answer = self.inst.ask('POWER?')
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
            return self.inst.ask('SETPOWER?')
        else:
            return self.get_power()

    def set_power_setpoint(self, power):
        """

        @param power:
        @return:
        """
        if self.psu == PSUTypes['FPU']:
            self.inst.ask('POWER={:f}'.format(power))
        else:
            self.inst.ask('POWER={:f}'.format(power*1000))
    def get_current(self):
        """

        @return:
        """
        if self.psu == PSUTypes['MPC3000'] or self.psu == PSUTypes['MPC6000']:
            return float(self.inst.ask('SETCURRENT1?').split('%')[0])
        else:
            return float(self.inst.ask('CURRENT?').split('%')[0])

    def set_current(self, current_percent):
        """

        @param current_percent:
        @return:
        """
        self.inst.ask('CURRENT={}'.format(current_percent))
        return self.get_current()

    def get_shutter_state(self):
        """

        @return:
        """
        if self.psu == PSUTypes['FPU']:
            state = self.inst.ask('SHUTTER?')
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
                    self.inst.ask('SHUTTER OPEN')
                else if state == ShutterState['CLOSED']::
                    self.inst.ask('SHUTTER CLOSE')
        return self.get_shutter_state()

    def get_psu_temperature(self):
        """

        @return:
        """
        return float(self.inst.ask('PSUTEMP?').split('C')[0])

    def get_laser_temperature(self):
        """

        @return:
        """
        return float(self.inst.ask('LASTEMP?').split('C')[0])

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
            return self.inst.ask('STATUSLCD?')

    def get_laser_state(self):
        """

        @return:
        """
        if self.psu == PSUTypes['SMD6000']:
            state = self.inst.ask('STAT?')
        else:
            state = self.inst.ask('STATUS?')
        if 'ENABLED' in state:
            return LaserState['ENABLED']
        elif 'DISABLED' in state:
            return LaserState['DISABLED']
        else:
            return LaserState['UNKNOWN']

    def set_laser_state(self, status):
        """

        @param status:
        @return:
        """
        actstat = self.get_laser_state()
        if actstat != status:
            if status == LaserState['ENABLED']:
                self.inst.ask('ON')
            elif status == LaserState['DISABLED']:
                self.inst.ask('OFF')
        return self.get_laser_state()

    def on(self):
        return self.set_laser_state(LaserState['ENABLED'])

    def off(self):
        return self.set_laser_state(LaserState['DISABLED'])

    def get_firmware_version(self):
        """ Ask the laser for ID.

        @return str: what the laser tells you about itself
        """
        if self.psu == PSUTypes['SMD6000']:
            self.inst.write'VERSION')
            line1 = self.inst.read()
            line2 = self.inst.read()
            return line1+line2
        else:
            self.inst.write('SOFTVER?')
            line1 = self.inst.read()
            line2 = self.inst.read()
            return line1+line2

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
        extra += get_firmware_version()
        extra += '\r\n'
        extra += '\r\n'.join(dump())
        extra += '\r\n'
        extra += '\r\n'.join(timers())
        extra += '\r\n'
        return extra

