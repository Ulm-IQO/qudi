# -*- coding: utf-8 -*-
"""
A hardware module for communicating with the fast counter FPGA.

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

Copyright (C) 2015 Jan M. Binder <jan.binder@uni-ulm.de>
"""

from interface.fast_counter_interface import FastCounterInterface
import numpy as np
from collections import OrderedDict
import thirdparty.stuttgart_counter.TimeTagger as tt
from core.base import Base
from core.util.mutex import Mutex
from pyqtgraph.Qt import QtCore

class FastCounterFPGAPi3(Base, FastCounterInterface):
    _modclass = 'fastcounterfpgapi3'
    _modtype = 'hardware'

    ## declare connectors
    _out = {'fastcounter': 'FastCounterInterface'}

    signal_get_data_next = QtCore.Signal()

    def __init__(self, manager, name, config = {}, **kwargs):
        callback_dict = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, callback_dict)


    def activation(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Fysom.event object from Fysom class.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """

        config = self.getConfiguration()
        if 'fpgacounter_serial' in config.keys():
            self._fpgacounter_serial=config['fpgacounter_serial']
        else:
            self.logMsg('No serial number defined for fpga counter',
                        msgType='warning')

        tt._Tagger_setSerial(self._fpgacounter_serial)

        self._binwidth = 1
        self._record_length = 4000
        self._N_read = 100

        self.channel_apd_1 = int(1)
        self.channel_apd_0 = int(1)
        self.channel_detect = int(2)
        self.channel_sequence = int(6)
        self.configure(1,1000,1)

        self.count_data = None

        self.stopRequested = False

        self.threadlock = Mutex()

        self.signal_get_data_next.connect(self._get_data_next,
                                          QtCore.Qt.QueuedConnection)

    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method activation.
        """
        pass

    def get_constraints(self):
        """ Retrieve the hardware constrains from the Fast counting device.

        @return dict: dict with keys being the constraint names as string and
                      items are the definition for the constaints.

         The keys of the returned dictionary are the str name for the constraints
        (which are set in this method).

                    NO OTHER KEYS SHOULD BE INVENTED!

        If you are not sure about the meaning, look in other hardware files to
        get an impression. If still additional constraints are needed, then they
        have to be added to all files containing this interface.

        The items of the keys are again dictionaries which have the generic
        dictionary form:
            {'min': <value>,
             'max': <value>,
             'step': <value>,
             'unit': '<value>'}

        Only the keys 'activation_config' and 'available_ch' differ, since they
        contain the channel name and configuration/activation information.

        If the constraints cannot be set in the fast counting hardware then
        write just zero to each key of the generic dicts.
        Note that there is a difference between float input (0.0) and
        integer input (0), because some logic modules might rely on that
        distinction.

        ALL THE PRESENT KEYS OF THE CONSTRAINTS DICT MUST BE ASSIGNED!
        """

        constraints = dict()

        # the unit of those entries are seconds per bin. In order to get the
        # current binwidth in seonds use the get_binwidth method.
        #FIXME: Enter here the proper numbers!
        constraints['hardware_binwidth_list'] = [1e-9, 2e-9, 4e-9, 8e-9]

        return constraints

    def configure(self, N_read, record_length, bin_width):
        """ Configuration of the fast counter.

        @param float bin_width_s: Length of a single time bin in the time trace
                                  histogram in seconds.
        @param float record_length_s: Total length of the timetrace/each single
                                      gate in seconds.
        @param int number_of_gates: optional, number of gates in the pulse
                                    sequence. Ignore for not gated counter.

        @return tuple(binwidth_s, gate_length_s, number_of_gates):
                    binwidth_s: float the actual set binwidth in seconds
                    gate_length_s: the actual set gate length in seconds
                    number_of_gates: the number of gated, which are accepted
        """

        self._N_read = N_read
        self._record_length = record_length
        self._bin_width = bin_width
        self.n_bins = int(self._record_length / self._bin_width)

        self.pulsed = tt.Pulsed(
            self.n_bins,
            int(np.round(self._bin_width*1000)),
            self._N_read,
            self.channel_apd_0,
            self.channel_detect,
            self.channel_sequence
        )

    def _get_data_next(self):
        if self.stopRequested:
            with self.threadlock:
                self.kill_scanner()
                self.stopRequested = False
                self.unlock()
                return
        self.count_data = self.count_data + self.pulsed.getData()
        self.signal_get_data_next.emit()

    def start_measure(self):
        """ Start the fast counter. """

        self.lock()
        self.count_data = np.zeros((self._N_read,self._record_length))
        self.pulsed.start()
        self.signal_get_data_next.emit()
        return 0

    def stop_measure(self):
        """ Stop the fast counter. """

        with self.threadlock:
            if self.getState() == 'locked':
                self.stopRequested = True
        self.pulsed.stop()
        self.unlock()
        return 0

    def pause_measure(self):
        """ Pauses the current measurement.

        Fast counter must be initially in the run state to make it pause.
        """
        self.stop_measure()
        return 0

    def continue_measure(self):
        """ Continues the current measurement.

        If fast counter is in pause state, then fast counter will be continued.
        """
        self.signal_get_data_next.emit()
        return 0

    def is_gated(self):
        """ Check the gated counting possibility.

        @return bool: Boolean value indicates if the fast counter is a gated
                      counter (TRUE) or not (FALSE).
        """

        return True

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
        return self.count_data

    def get_status(self):
        """ Receives the current status of the Fast Counter and outputs it as
            return value.

        0 = unconfigured
        1 = idle
        2 = running
        3 = paused
        -1 = error state
        """
        ready = self.pulsed.ready()
        return {'binwidth_ns': self._bin_width*1000, 'is_gated': True, 'is_ready': ready}

    def get_binwidth(self):
        """ Returns the width of a single timebin in the timetrace in seconds.

        @return float: current length of a single bin in seconds (seconds/bin)
        """
        return self._binwidth
