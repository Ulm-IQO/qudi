# -*- coding: utf-8 -*-

"""
This module contains the Qudi interface file for analogue output channel.

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


import abc
from core.util.interfaces import InterfaceMetaclass


class AnalogueOutputInterface(metaclass=InterfaceMetaclass):
    """ This is the Interface class to define the controls for the simple
    microwave hardware.
    """

    _modtype = 'AnalogueOutputInterface'
    _modclass = 'interface'

    @abc.abstractmethod
    def set_voltage_range(self, myrange=None):
        """ Sets the voltage range of the NI Card.

        @param float [n][2] myrange: array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def _start_analog_output(self):
        """ Starts or restarts the analog output.

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def _stop_analog_output(self):
        """ Stops the analog output.

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def set_up_analogue_output(self, analogue_channels=None, scanner=False):
        """ Starts or restarts the analog output.

        @param List(string) analogue_channels: the representative names  of the analogue channel for
                                        which the task is created in a list

        @param Bool scanner: Defines if a scanner analogue output is to be setup of if single
                                    channels are to be configured

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def close_analogue_output(self):
        """Closes the analog output task.

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def _write_scanner_ao(self, voltages, length=1, start=False):
        """Writes a set of voltages to the analog outputs.

        @param float[][n] voltages: array of n-part tuples defining the voltage
                                    points
        @param int length: number of tuples to write
        @param bool start: write immediately (True)
                           or wait for start of task (False)

        n depends on how many channels are configured for analog output
        """
        pass

    @abc.abstractmethod
    def write_ao(self, analogue_channel, voltages, length=1, start=False, time_out=0):
        """Writes a set of voltages to the analog outputs.

        @param  string analogue_channel: the representative name of the analogue channel for
                                        which the voltages are written

        @param float[][n] voltages: array of n-part tuples defining the voltage points

        @param int length: number of tuples to write

        @param bool start: write immediately (True) or wait for start of task (False)

        @param float time_out: default 0, value how long the program should maximally take two write the samples
                                0 returns an error if program fails to write immediately.

        @return int: how many values were acutally written
        """
        pass



