# -*- coding: utf-8 -*-

"""
This module serves as stand-alone control class for the Toptica iBeam Smart series laser.

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
import warnings
from threading import Lock


class IBeamSmart:
    """ Python wrapper class to control a Toptica iBeamSmart Laser system via serial interface.
    """

    def __init__(self, com_port, timeout=2000, max_power=0.1, num_channels=2):
        self.__max_power = max_power
        self.__num_channels = num_channels
        resource_manager = visa.ResourceManager()
        print(resource_manager.list_resources())
        try:
            self._instrument = resource_manager.open_resource('ASRL{0:d}'.format(com_port))
        except visa.VisaIOError:
            raise Exception('Unable to open serial connection on COM{0:d}'.format(com_port))
        self._instrument.timeout = int(timeout)
        self._thread_lock = Lock()
        self._serial = self.query('serial')
        self._firmware = self.query('version')

    def terminate(self):
        if self._instrument is not None:
            self._instrument.close()
            self._instrument.clear()
            self._instrument = None

    def query(self, question):
        with self._thread_lock:
            answer = self._instrument.query(question)
            error = self._instrument.query('err')
            print(error)
            return answer

    def write(self, command):
        with self._thread_lock:
            self._instrument.write(command)
            error = self._instrument.query('err')
            print(error)
            return

    @property
    def serial(self):
        return self._serial

    @property
    def firmware(self):
        return self._firmware

    @property
    def error(self):
        with self._thread_lock:
            return self._instrument.query('err')

    @property
    def channel_states(self):
        return tuple(self.get_channel_state(ch) for ch in range(self.__num_channels))

    @property
    def laser_driver_state(self):
        return bool(self.query('sta la'))

    @property
    def channel_powers(self):
        return tuple(self.get_power(ch) for ch in range(self.__num_channels))

    @property
    def fine_state(self):
        return self.query('sta fine')

    @property
    def diode_current(self):
        return self.query('sh cur')

    @property
    def diode_temperature(self):
        return self.query('sh temp')

    @property
    def base_temperature(self):
        return self.query('sh temp sys')

    @property
    def laser_power(self):
        return float(self.query('sh pow')) / 1e6

    @property
    def uptime(self):
        return self.query('sh timer')

    def reset(self):
        self.write('reset sys')

    def get_channel_state(self, channel):
        """

        :param channel:
        :return:
        """
        channel = int(channel)
        self.__check_channel_index(channel)
        return bool(self.query('sta ch {0:d}'.format(channel + 1)))

    def toggle_channel(self, channel, enable=None):
        """

        :param channel:
        :param enable:
        :return:
        """
        channel = int(channel)
        self.__check_channel_index(channel)
        if enable is None:
            enable = not self.get_channel_state(channel)
        elif not isinstance(enable, bool):
            raise TypeError('Parameter "enable" must be bool type or None.')

        cmd = 'en {0:d}' if enable else 'di {0:d}'
        self.write(cmd.format(channel + 1))
        return self.channel_states

    def toggle_laser_driver(self, enable=None):
        """

        :param enable:
        :return:
        """
        if enable is None:
            enable = not self.laser_driver_state
        elif not isinstance(enable, bool):
            raise TypeError('Parameter "enable" must be bool type or None.')
        self.write('la on' if enable else 'la off')
        return self.laser_driver_state

    def get_power(self, channel):
        """

        :param channel:
        :return:
        """
        channel = int(channel)
        self.__check_channel_index(channel)
        return 1

    def set_power(self, channel, power):
        """

        :param channel:
        :param power:
        :return:
        """
        channel = int(channel)
        self.__check_channel_index(channel)
        if power < 0:
            warnings.warn('Power level below 0W is no possible. Clipping to minimum value.')
            power = 0
        elif power > self.__max_power:
            warnings.warn('Power level above {0.3f}W is no possible. Clipping to maximum value.'
                          ''.format(self.__max_power))
            power = self.__max_power
        self.write('ch {0:d} pow {1:d} mic'.format(channel + 1, int(round(power * 1e6))))
        return self.get_power(channel)

    def configure_fine(self, enable=None, a=None, b=None):
        """

        :param enable:
        :param a:
        :param b:
        :return:
        """
        if a is not None:
            self.write('fine a {0:d}'.format(a))
        if b is not None:
            self.write('fine b {0:d}'.format(b))
        if enable is not None:
            self.write('fine on' if enable else 'fine off')
        return self.fine_state



    ################################################################################################
    #                             Utility/Helper methods below                                     #
    ################################################################################################
    def __check_channel_index(self, index):
        """

        :param index:
        :return:
        """
        if index >= self.__num_channels or index < 0:
            raise ValueError(
                'Channel index must be in range [0, {1:d}]'.format(self.__num_channels - 1))