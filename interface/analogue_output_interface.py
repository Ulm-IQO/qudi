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

    @abc.abstractmethod
    def get_analogue_resolution(self):
        """"Returns the resolution of the analogue input resolution in bits
        @return int: input bit resolution """
        pass

    @abc.abstractmethod
    def set_up_analogue_output_clock(self, clock_frequency=None, clock_channel=None,
                                             set_up=True):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of
                                      the clock (in Hz). If not defined the scanner clock frequency will be used.
        @param string clock_channel: if defined, this is the physical channel
                                     of the clock
        @param bool set_up: If True, the function does nothing and assumes clock is already set up from different task
                                    using the same clock

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def analogue_scan_line(self, analogue_channel, voltages):
        pass

    @abc.abstractmethod
    def configure_analogue_timing(self, analogue_channel, length):
        pass

    @abc.abstractmethod
    def start_analogue_output(self, analogue_channel, start_clock=False):
        """
        Starts the preconfigured analogue out task

        @param  string analogue_channel: the representative name of the analogue channel for
                                        which the task is created
        @param  bool start_clock: default value false, bool that defines if clock for the task is
                                also started.

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def stop_analogue_output(self, analogue_channel):
        """"
        Stops the analogue voltage output task

        @analogue_channel str: one of the analogue channels for which the task to be stopped is
                            configured. If more than one channel uses this task,
                            all channel readings will be stopped.
        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def close_analogue_output_clock(self):
        """ Closes the analogue output clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        pass



