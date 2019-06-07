# -*- coding: utf-8 -*-

"""
This hardware module implement the pid interfaces to interact with a Cryo-Con

This module have been developed with model 22C
---

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

import time
import socket
from core.module import Base, ConfigOption
import numpy as np

# from interface.process_interface import ProcessInterface


class SocketInstrument:
    """ General class for a socket instrument, this should go elsewhere ! """
    def __init__(self, host, port):
        """ Initialise the connection with the instrument """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        self.sock = sock

    def write(self, cmd):
        """Sends a command over the socket"""
        cmd_string = cmd + '\n'
        sent = self.sock.sendall(cmd_string.encode())
        if sent != None:
            raise RuntimeError('Transmission failed')

    def query(self, cmd):
        """sends the question and receives the answer"""
        self.write(cmd)
        answer = self.sock.recv(2048)  # 2000
        return answer[:-2]

    def close(self):
        self.sock.close()


class Cryocon(Base):
    """
    Main class for the Cryo-Con hardware
    """

    _modtype = 'cryocon'
    _modclass = 'hardware'

    _ip_address = ConfigOption('ip_address')
    _ip_port = ConfigOption('port', 5000)
    _main_channel = ConfigOption('main_channel', 'A')

    _socket = None

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._socket = SocketInstrument(self._ip_address, self._ip_port)

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        try:
            if self._socket:
                self._socket.close()
        except:
            self.log.warning('Crycon connexion has not been closed properly.')

    def get_temperature(self, channel=None):
        """ Cryocon function to get one temperature """
        channel = channel if channel is not None else self._main_channel
        try:
            temperature = float(self._socket.query('INPUT? {}'.format(channel)).decode())
        except:
            temperature = np.NaN
        return temperature

    def set_temperature(self, temperature, channel=None, turn_on=False):
        """ Function to set the temperature setpoint """
        channel = channel if channel is not None else self._main_channel
        loop = 1 if channel == 'A' else 2
        self._socket.write('loop {}:setp {}'.format(loop, temperature))
        if turn_on:
            self.control()

    def get_process_value(self):
        """ Get measured value of the temperature """
        return self.get_temperature()

    def get_process_unit(self):
        """ Return the unit of measured temperature """
        return 'K', 'Kelvin'

    def stop(self):
        """  Function to stop the heating of the Cryocon """""
        self._socket.write('stop')

    def control(self):
        """ Function to turn the heating on """
        self._socket.write('control')

    def set_control_value(self, value):
        """ Set the value of the controlled process variable """
        self.set_temperature(temperature=value)

    def wait_for_temperature(self, temperature, delta=0.1, timeout=60*60):
        """ Set the temperature and wait until the setpoint temperature is reached

        @param temperature: The new setpoint
        @param delta: The error margin between the measured value and the setpoint to stop
        @param timeout: The maximum time to wait
        @return (bool): True if successful, False if timeout

        Warning, this pausing function can be usefull but can also cause Qudi to not respond if executed from the
        manager.
        """
        self.set_temperature(temperature, turn_on=True)
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_temperature = self.get_temperature()
            if temperature - delta < current_temperature < temperature + delta:
                        return True
            time.sleep(1)
        return False







