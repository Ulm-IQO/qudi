# -*- coding: utf-8 -*-
"""
Scan Matisse laser with Arduin Due. 

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

from core.module import Base, ConfigOption
from interface.simple_data_interface import SimpleDataInterface


class MatisseDuePID(Base, SimpleDataInterface):
    """ Read human readable numbers from serial port.
    """
    _modclass = 'simple'
    _modtype = 'hardware'

    data_resource = ConfigOption('data_interface', 'ASRL1::INSTR', missing='warn')
    control_resource = ConfigOption('control_interface', 'ASRL2::INSTR', missing='warn')
    data_baudrate = ConfigOption('data_baudrate', 115200, missing='warn')
    control_baudrate = ConfigOption('control_baudrate', 9600, missing='warn')

    def on_activate(self):
        """ Activate module.
        """
        self.rm = visa.ResourceManager()
        self.log.debug('Resources: {0}'.format(self.rm.list_resources()))
        self.control_instr = self.rm.open_resource(
            self.control_resource,
            baud_rate=self.control_baudrate,
            read_termination='\r\n',
            write_termination='\n')
        self.data_instr = self.rm.open_resource(
            self.data_resource,
            baud_rate=self.data_baudrate,
            read_termination='\r\n',
            write_termination='\n')

        r = self.control_instr.query('*IDN?').rstrip().split(',')
        self.mfg, self.model, self.revision, self.fwver = r

    def on_deactivate(self):
        """ Deactivate module.
        """
        self.set_data_output(0)
        self.control_instr.close()
        self.data_instr.close()
        self.rm.close()

    def get_data(self):
        """ Read one value from serial port.

            @return int: vaue form serial port
        """
        try:
            return list(
                map(
                    int,
                    self.my_instrument.read_raw().decode('utf-8').rstrip().split())
            )
        except:
            return [-1] * 4

    def set_volt_range(self, low, high):
        r = self.control_instr.query(':SOUR:RL {0} {1}'.format(low, high))
        return list(map(int, r.rstrip().split(' ')))

    def get_volt_range(self):
        return list(
            map(int, self.control_instr.query(':SOUR:RL?').rstrip().split(','))
        )

    def set_scan(self, direction):
        r = self.control_instr.query(':SOUR:R {0}'.format(direction))
        return int(r)

    def get_scan(self):
        return int(self.control_instr.query(':SOUR:R?'))

    def get_scan_speed(self):
        return int(self.control_instr.query(':SOUR:RS?'))

    def set_scan_speed(self, speed):
        return int(self.control_instr.query(':SOUR:RS {0}'.format(speed)))

    def get_pos(self):
        return int(self.control_instr.query(':SOUR:VOLT?'))

    def get_data_output(self):
        return int(self.control_instr.query(':P?'))

    def set_data_output(self, out):
        self.control_instr.write(':P {0}'.format(out))
        return self.get_data_output()

    def get_cavity(self):
        vals = list(map(int, self.control_instr.query(':MEAS:VAL?').rstrip().split(' ')))
        stats = list(map(int, self.control_instr.read().rstrip().split(' ')))
        return vals, stats

    def pid_get_p(self, mode):
        return float(self.control_instr.query(':PID:{0}:KP?'.format(mode)))

    def pid_get_i(self, mode):
        return float(self.control_instr.query(':PID:{0}:KI?'.format(mode)))

    def pid_get_d(self, mode):
        return float(self.control_instr.query(':PID:{0}:KD?'.format(mode)))

    def pid_get_setpoint(self, mode):
        return float(self.control_instr.query(':PID:{0}:SP?'.format(mode)))

    def pid_get_cv(self, mode):
        return float(self.control_instr.query(':PID:{0}:CV?'.format(mode)))

    def pid_set_p(self, mode, value):
        return float(self.control_instr.query(':PID:{0}:KP {1}'.format(mode, value)))

    def pid_set_i(self, mode, value):
        return float(self.control_instr.query(':PID:{0}:KP {1}'.format(mode, value)))

    def pid_set_d(self, mode, value):
        return float(self.control_instr.query(':PID:{0}:KP {1}'.format(mode, value)))

    def pid_set_setpoint(self, mode, value):
        return float(self.control_instr.query(':PID:{0}:SP {1}'.format(mode, value)))

    def getData(self):
        """ Read one value from serial port.

            @return int: vaue form serial port
        """
        try:
            return list(
                map(
                    int,
                    self.data_instr.read_raw().decode('utf-8').rstrip().split()[2:3])
            )
        except:
            return [0] * 1

    def getChannels(self):
        """ Number of channels.

            @return int: number of channels
        """
        return 1
