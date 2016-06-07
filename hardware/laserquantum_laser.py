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
import visa

PSUTYPES = {
    'FPU': 0,
    'MPC6000': 1,
    'MPC3000': 2,
    'SMD12': 3,
    'SMD6000': 4
}


class LaserQuantumLaser(Base):
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
        Base.__init__(self, manager, name, configuration=config, callbacks = c_dict)

    def activation(self, e):
        config = self.getConfiguration()
        self.psu = PSUTYPES[config['psu']]
        self.connect(config['interface'])

    def deactivation(self, e):
        self.disconnect()

    def connect(self, interface):
        """ Connect to Instrument.
        
            @param str interface: visa interface identifier

            @return bool: connection success
        """
        try:
            self.rm = visa.ResourceManager()
            rate = 9600 if self.psu == PSUTYPES['SMD6000'] else 19200
            self.inst = self.rm.open_resource(interface, baud_rate=rate, term_chars='\n', send_end=True)
        except visa.VisaIOError as e:
            self.logExc()
            return False
        else:
            return True

    def disconnect(self):
        """ 
        Close the connection to the instrument.
        """
        self.inst.close()
        self.rm.close()


    def get_firmware_version(self):
        if self.psu == PSUTYPES['SMD6000']:
            return self.inst.ask('VERSION')
        else:
            return self.inst.ask('SOFTVER?')

    def get_control_mode(self):
        if self.psu == PSUTYPES['FPU']:
            return 'MIXED'
        elif self.psu == PSUTYPES('SMD6000'):
            power = self.get_power()
            if '0000' in power:
                return 'CURRENT'
            else:
                return 'POWER'
        else:
            return self.inst.ask('CONTROL?')

    def set_control_mode(self, mode):
        if self.psu == PSUTYPES['FPU']:
            return 'MIXED'
        elif self.psu == PSUTYPES['SMD6000']:
            if mode == 'POWER':
                power = 
                self.inst.ask('POWER={}'.format(power))
            else:
                self.inst.ask('POWER=0')
        else:
            if mode == 'POWER':
                self.inst.ask('PFB=OFF')
                self.inst.ask('CONTROL=POWER')
            else:
                self.inst.ask('PFB=ON')
                self.inst.ask('CONTROL=CURRENT')


    def get_power(self):
        return self.inst.ask('POWER?')

    def get_power_setpoint(self):
        if self.psu != PSUTYPES('SMD6000'):
            return self.inst.ask('SETPOWER?')

    def set_power_setpoint(self, power):
        return self.inst.ask('POWER={:f}'.format(power))

    def get_current_percent(self):
        if self.psu == PSUTYPES['MPC3000'] or self.psu == PSUTYPES['MPC6000']:
            return self.inst.ask('SETCURRENT1?')
        else:
            return self.inst.ask('CURRENT?')

    def set_current_percent(self, current_percent):
        return self.inst.ask('CURRENT={}'.format(current_percent))

    def get_shutter(self):
        if self.psu == PSUTYPES['FPU']:
            return self.inst.ask('SHUTTER?')
        else:
            return None

    def set_shutter(self, state):
        if self.psu == PSUTYPES['FPU']:
            actstate = "SHUTTER OPEN" in self.inst.ask('SHUTTER?')
            if state != actstate:
                if state:
                    self.inst.ask('SHUTTER OPEN')
                else:
                    self.inst.ask('SHUTTER CLOSE')
        else:
            return None

    def get_psu_temperature(self):
        return self.inst.ask('PSUTEMP?')

    def get_laser_temperature(self):
        return self.inst.ask('LASTEMP')

    def get_lcd(self):
        if self.psu == PSUTYPE['SMD12'] or self.psu == PSUTYPE['SMD6000']:
            return ''
        else:
            return self.inst.ask('STATUSLCD?')

    def get_status(self):
        if self.psu == PSUTYPES('SMD6000'):
            return self.inst.ask('STAT?')
        else:
            return self.inst.ask('STATUS?')

    def set_status(self, status):
        actstat = 'ENABLED' in self.get_status()
        if actstat != status:
            if status:
                self.inst.ask('ON')
            else:
                self.inst.ask('OFF')
        return self.get_status()
                

    def dump(self):
        return self.inst.ask('DUMP ')

    def timers(self):
        return self.inst.ask('TIMERS')
