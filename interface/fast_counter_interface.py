# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware interface for fast counting devices.

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
from core.util.interfaces import InterfaceMetaclass, ScalarConstraint


class FastCounterInterface(metaclass=InterfaceMetaclass):
    """ Interface class to define the controls for fast counting devices. """

    _modtype = 'FastCounterInterface'
    _modclass = 'interface'

    @abc.abstractmethod
    def get_constraints(self):
        """ Retrieve the hardware constrains from the Fast counting device.

        @return constraint object: object with fast counter constraints as
                                   attributes

        dict: dict with keys being the constraint names as string and
                      items are the definition for the constraints.

        USE ONLY THE CONSTRAINTS DEFINED IN THE CLASS FastCounterConstrains
        NO OTHER ATTRIBUTES SHOULD BE INVENTED!

        If you are not sure about the meaning, look in other hardware files to
        get an impression. If still additional constraints are needed, then they
        have to be added to all files containing this interface.


        Note that there is a difference between float input (0.0) and
        integer input (0), because some logic modules might rely on that
        distinction.


        # Example for configuration with default values:

        constraints = FastCounterConstrains()
        constraints.hardware_binwidth_list = [0.25e-9, 0.5e-9, 1e-9]

        constraints.count_length.min = 0.25e-9  # in seconds
        constraints.count_length.max = 6
        constraints.count_length.step = 0.25e-9

        constraints.continuous_measurement = True
        constraints.is_gated = False
        """
        pass

    @abc.abstractmethod
    def configure(self, bin_width_s, record_length_s, number_of_gates=0):
        """ Configuration of the fast counter.

        @param float bin_width_s: Length of a single time bin in the time
                                  trace histogram in seconds.
        @param float record_length_s: Total length of the timetrace/each
                                      single gate in seconds.
        @param int number_of_gates: optional, number of gates in the pulse
                                    sequence. Ignore for not gated counter.

        @return tuple(binwidth_s, record_length_s, number_of_gates):
                    binwidth_s: float the actual set binwidth in seconds
                    gate_length_s: the actual record length in seconds
                    number_of_gates: the number of gated, which are accepted, None if not-gated
        """
        pass

    @abc.abstractmethod
    def get_status(self):
        """ Receives the current status of the Fast Counter and outputs it as
            return value.

        0 = unconfigured
        1 = idle
        2 = running
        3 = paused
      -1 = error state
        """
        pass

    @abc.abstractmethod
    def start_measure(self):
        """ Start the fast counter.
        Note, if the fast counter can only count in a finite scheme, then you
        need also to start internally a data_poller method, which reads out the
        data und saves it temporally, so that the method get_data_trace can get
        from time to time the data.

        A possibility to start a data_poller is via a QtSignal:

                sigFiniteMeasLoop = QtCore.Signal() # define as class attribute

        Then create a method self._poll_data() which should return and change
        the status of the fast counter if the method has pulled all data from
        the device:

            def _poll_data(self):
                # get the data, post process it and save to internal array
                self.status = 1
                return

            # in the activation:
            self.sigFiniteMeasLoop.connect(self._poll_data)

        within this method, the signal will be eventually emited
            self.sigFiniteMeasLoop.emit()
        """
        pass

    @abc.abstractmethod
    def stop_measure(self):
        """ Stop the fast counter. """
        pass

    @abc.abstractmethod
    def pause_measure(self):
        """ Pauses the current measurement.

        Fast counter must be initially in the run state to make it pause.
        """
        pass

    @abc.abstractmethod
    def continue_measure(self):
        """ Continues the current measurement.

        If fast counter is in pause state, then fast counter will be continued.
        """
        pass

    @abc.abstractmethod
    def is_gated(self):
        """ Check the gated counting possibility.

        @return bool: Boolean value indicates if the fast counter is a gated
                      counter (TRUE) or not (FALSE).
        """
        pass

    @abc.abstractmethod
    def get_binwidth(self):
        """ Returns the width of a single timebin in the timetrace in seconds.

        @return float: current length of a single bin in seconds (seconds/bin)
        """
        pass

    @abc.abstractmethod
    def get_data_trace(self):
        """ Polls the current timetrace data from the fast counter.

        Return value is a numpy array (dtype = int64).
        The binning, specified by calling configure() in forehand, must be
        taken care of in this hardware class. A possible overflow of the
        histogram bins must be caught here and taken care of.
        If the counter is NOT GATED it will return a 1D-numpy-array with
            returnarray[timebin_index]
        If the counter is GATED it will return a 2D-numpy-array with
            returnarray[gate_index, timebin_index]
        """
        pass


class FastCounterConstraints:
    def __init__(self):
        self.hardware_binwidth_list = list()
        # the minimal and maximal count length for the device (for gated
        # devices it is the length of the gate, for ungated devices, it is the
        # total length of the sequence)
        self.count_length = ScalarConstraint(unit='s')
        # indicate whether continuous measurement is possible, this measurement
        # will be preferred it is possible.
        self.continuous_measurement = True
        self.is_gated = True