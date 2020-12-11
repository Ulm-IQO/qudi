# -*- coding: utf-8 -*-
"""
Hardware file for the Cryomagnetics power supply for superconducting magnet

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


import visa
from core.module import Base
from core.configoption import ConfigOption


class Cryomagnetics(Base):
    """ Hardware module to control one or two vector magnet via the power supply.

    This hardware works by setting a lower and a higher limit. Then the sweep operation can be used to either go
    to lower limit, zero or upper limit.
    A security constraints can be set via panel but is independent of the limits set here.

    Example config for copy-paste:

    cryognatics_xy:
        module.Class: 'sc_magnet.cryomagnetics.Cryomagnetics'
        visa_address: 'tcpip0::192.168.0.254:4444:socket'


    """
    _visa_address = ConfigOption('visa_address', missing='error')
    _dual_supply = ConfigOption('dual_supply', False)
    _limits = ConfigOption('limits', missing='error')  # limits of field in Tesla. Ex: [-0.5, 0.5]

    def __init__(self, **kwargs):
        """Here the connections to the power supplies and to the counter are established"""
        super().__init__(**kwargs)
        self._inst = None

    def on_activate(self):
        """ Connect to hardware """

        rm = visa.ResourceManager()
        try:
            self._inst = rm.open_resource('TCPIP0::192.168.1.6::4444::SOCKET', write_termination='\r\n',
                                          read_termination='\r\n')
        except visa.VisaIOError:
            self.log.error('Could not connect to hardware. Please check the wires and the address.')

    def on_deactivate(self):
        """ Disconnect from hardware """
        self._inst.close()

    def _query(self, command, channel=None):
        """ Query a command to the hardware """
        if channel in [1, 2]:
            command = 'CHAN {};{}'.format(channel, command)
        return self._inst.query(command)

    def _write(self, command, channel=None):
        """ Write a command to the hardware """
        if channel in [1, 2]:
            command = 'CHAN {};{}'.format(channel, command)
        self._inst.write(command)

    def get_channels(self):
        """ Return a list of the channels keys """
        return 1, 2

    def set_channel(self, channel):
        """ Set the current active channel """
        if channel in [1, 2]:
            self._write('CHAN {}'.format(channel))

    def get_magnet_current(self, channel=None):
        """ Return the current magnet current in Tesla """
        response = self._query('IMAG?', channel=channel)
        if 'kG' in response:
            value = float(response[:-2]) * 0.1
        else:
            self.log.error('Can not read {} as field. Please use Gauss and not ampere.')
            value = None
        return value

    def set_lower_limit(self, value, channel=None):
        """ Set the lower limit of the field (in Tesla) """
        if not(self._limits[0] <= value <= 0):
            return self.log.error('Value {} is not in the limit interval [{}, 0]'.format(value, self._limits[0]))
        value_in_kG = value * 10
        self._write('REMOTE;LLIM {}'.format(value_in_kG), channel=channel)

    def get_lower_limit(self, channel=None):
        """ Get the lower limit of the field (in Tesla) """
        response = self._query('LLIM?', channel=channel)
        if 'kG' in response:
            value = float(response[:-2]) * 0.1
        return value

    def set_upper_limit(self, value, channel=None):
        """ Set the upper limit of the field (in Tesla) """
        if not (0 <= value <= self._limits[1]):
            return self.log.error('Value {} is not in the limit interval [0, {}]'.format(value, self._limits[1]))
        value_in_kG = value * 10
        self._write('REMOTE;ULIM {}'.format(value_in_kG), channel=channel)

    def get_upper_limit(self, channel=None):
        """ Get the upper limit of the field (in Tesla) """
        response = self._query('ULIM?', channel=channel)
        if 'kG' in response:
            value = float(response[:-2]) * 0.1
        return value

    def get_limits(self, channel=1):
        """ Get the field limits as a tuple (lower_limit, higher_limit) in Tesla """
        return tuple(self._limits)

    def sweep(self, mode, channel=None):
        """ Sweep to 'UP', 'DOWN', 'PAUSE' or 'ZERO' """
        if mode in ['UP', 'DOWN', 'PAUSE', 'ZERO']:
            self._write('REMOTE;SWEEP {}'.format(mode), channel=channel)

    def pause(self, channel=None):
        """ Pause the current sweep """
        self.sweep('PAUSE', channel=channel)

    def pause_all(self):
        """ Pause all sweeps """
        for channel in self.get_channels():
            self.pause(channel)


