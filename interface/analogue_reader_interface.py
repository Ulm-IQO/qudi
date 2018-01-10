# -*- coding: utf-8 -*-

"""
This module contains the Qudi interface file for analog reader.

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


class AnalogueReaderInterface(metaclass=InterfaceMetaclass):
    """ This is the Interface class to define the controls for a simple
    analogue input hardware with single or multiple channels.
    """

    _modtype = 'AnalogReaderInterface'
    _modclass = 'interface'

    @abc.abstractmethod
    def set_up_analogue_voltage_reader_clock(self, clock_frequency=None, clock_channel=None,
                                             set_up=True):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of
                                      the clock (in Hz)
        @param string clock_channel: if defined, this is the physical channel
                                     of the clock
        @param bool set_up: If True, the function does nothing and assumes clock is already set up from different task
                                    using the same clock

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def set_up_analogue_voltage_reader(self, analogue_channel):
        """Initializes task for reading an a single analogue input voltage.

        @param string analogue_channel: the representative name of the analogue channel for
                                        which the task is created

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def set_up_analogue_voltage_reader_scanner(self, samples,
                                               analogue_channel,
                                               clock_channel=None):
        """Initializes task for reading an analogue input voltage for a finite
        number of samples at a given frequency.

        It reads a differentially connected voltage from the analogue inputs. For every period of
        time (given by the frequency) it reads the voltage at the analogue channel.

        @param int samples: Defines how many values are to be measured
        @param string analogue_channel: the representative name of the analogue channel for
                                        which the task is created
        @param string clock_channel: if defined, this specifies the clock for
                                     the analogue reader

        @return int: error code (0:OK, -1:error)"""
        pass

    @abc.abstractmethod
    def add_analogue_reader_channel_to_measurement(self, analogue_channel_orig,
                                                   analogue_channels):
        """
        This function adds additional channels to an already existing analogue reader task.
        Thereby many channels can be measured, read and stopped simultaneously.
        For this method another method needed to setup a task already.
        Use e.g. set_up_analogue_voltage_reader_scanner

        @param string analogue_channel_orig: the representative name of the analogue channel
                                    task to which this channel is to be added
        @param List(string) analogue_channels: The new channels to be added to the task

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def set_up_continuous_analog_reader(self, analogue_channel, clock_channel=None):
        pass

    @abc.abstractmethod
    def start_analogue_voltage_reader(self, analogue_channel, start_clock=False):
        """
        Starts the preconfigured analogue input task

        @param  string analogue_channel: the representative name of the analogue channel for
                                        which the task is created
        @param  bool start_clock: default value false, bool that defines if clock for the task is
                                also started.

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def get_analogue_voltage_reader(self, analogue_channels, read_samples=None):
        """"
        Returns the last voltages read by the analog input reader

        @param  List(string) analogue_channels: the representative name of the analogue channels
                                        for which channels are read.
                                        The first list element must be the one for which the
                                        task was created
        @param int read_samples: The amount of samples to be read from the buffer for a continuous mode acquisition. Not
                                        needed for finite amount of samples

        @return np.array, int:The photon counts per second (array) and the amount of samples read (int). For
                                error array with length 2 and entry -1, 0
        """
        pass

    @abc.abstractmethod
    def stop_analogue_voltage_reader(self, analogue_channel):
        """"
        Stops the analogue voltage input reader task

        @analogue_channel str: one of the analogue channels for which the task to be stopped is
                            configured. If more than one channel uses this task,
                            all channel readings will be stopped.
        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def close_analogue_voltage_reader(self, analogue_channel):
        """"
        Closes the analogue voltage input reader and clears up afterwards

        @analogue_channel str: one of the analogue channels for which the task to be closed is
                            configured. If more than one channel uses this task,
                            all channel readings will be closed.
        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def close_analogue_voltage_reader_clock(self):
        """ Closes the analogue voltage input reader clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def get_analogue_resolution(self):
        """"Returns the resolution of the analogue input resolution in bits
        @return int: input bit resolution """
        pass

    def start_ai_counter_reader(self, analogue_channel):
        """Starts task of reading analogue voltage and finite counts synchronised.

        @param  string analogue_channel: the representative name of the analogue channel for
                                        which the task is created
        @return int: error code (0:OK, -1:error)
        """
        pass
