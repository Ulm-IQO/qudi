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

class FastCounterFGAPiP3(Base, FastCounterInterface):
    _modclass = 'FastCounterFGAPiP3'
    _modtype = 'hardware'

    ## declare connectors
    _out = {'fastcounter': 'FastCounterInterface'}

    signal_get_data_next = QtCore.Signal()

    def __init__(self, manager, name, config = {}, **kwargs):
        callback_dict = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, callback_dict)


    def activation(self, e):
        """ Connect and configure the access to the FPGA.

                @param object e: Event class object from Fysom.
                                 An object created by the state machine module Fysom,
                                 which is connected to a specific event (have a look in
                                 the Base Class). This object contains the passed event
                                 the state before the event happens and the destination
                                 of the state which should be reached after the event
                                 has happen.
                """

        config = self.getConfiguration()
        if 'fpgacounter_serial' in config.keys():
            self._fpgacounter_serial=config['fpgacounter_serial']
        else:
            self.logMsg('No serial number defined for fpga counter',
                        msgType='warning')

        if 'fpgacounter_channel_apd_0' in config.keys():
            self._channel_apd_0 = config['fpgacounter_channel_apd_0']
        else:
            self.logMsg('No apd0 channel defined for fpga counter',
                        msgType='warning')

        if 'fpgacounter_channel_apd_1' in config.keys():
            self._channel_apd_1 = config['fpgacounter_channel_apd_1']
        else:
            self.logMsg('No apd1 channel defined for fpga counter',
                        msgType='warning')

        if 'fpgacounter_channel_detect' in config.keys():
            self._channel_detect = config['fpgacounter_channel_detect']
        else:
            self.logMsg('No no detect channel defined for fpga counter',
                        msgType='warning')

        if 'fpgacounter_channel_sequence' in config.keys():
            self._channel_sequence = config['fpgacounter_channel_sequence']
        else:
            self.logMsg('No sequence channel defined for fpga counter',
                        msgType='warning')

        tt._Tagger_setSerial(self._fpgacounter_serial)

        self._number_of_gates = int(100)
        self._bin_width = 1
        self._record_length = int(4000)

        self.configure(self._bin_width*1e-9,self._record_length*1e-9,self._number_of_gates)

        self.count_data = None

        self.stopRequested = False

        self.statusvar = 0

        self.threadlock = Mutex()

        self.signal_get_data_next.connect(self._get_data_next,
                                          QtCore.Qt.QueuedConnection)
        print('fpga_counter end of activation:')

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
        constraints['hardware_binwidth_list'] = [1 / 1000e6]

        # TODO: think maybe about a software_binwidth_list, which will
        #      postprocess the obtained counts. These bins must be integer
        #      multiples of the current hardware_binwidth

        return constraints

    def deactivation(self, e):
        """ Deactivate the FPGA.

                @param object e: Event class object from Fysom. A more detailed
                                 explanation can be found in method activation.
                """
        pass

    def configure(self, bin_width_s, record_length_s, number_of_gates=0):

        """ Configuration of the fast counter.

                @param float bin_width_s: Length of a single time bin in the time trace
                                          histogram in seconds.
                @param float record_length_s: Total length of the timetrace/each single
                                              gate in seconds.
                @param int number_of_gates: optional, number of gates in the pulse
                                            sequence. Ignore for not gated counter.
                """

        self._number_of_gates = number_of_gates
        self._bin_width = bin_width_s * 1e9
        self._record_length = int(self.record_length_s / self._bin_width_s)
        self.statusvar = 1

        self.pulsed = tt.Pulsed(
            self._record_length,
            int(np.round(self._bin_width*1000)),
            self._number_of_gates,
            self._channel_apd_0,
            self._channel_detect,
            self._channel_sequence
        )
        print('fpga_counter end of configure:')
        return (bin_width_s, record_length_s, number_of_gates)

    def _get_data_next(self):
        """ Read new count_data and add to existing count_data
                        """
        if self.stopRequested:
            with self.threadlock:
                self.stopRequested = False
                self.unlock()
                return
        np.add(self.count_data, self.pulsed.getData())

        self.signal_get_data_next.emit()

    def start_measure(self):
        """ Start the fast counter. """

        self.lock()
        self.count_data = np.zeros([self._number_of_gates,
                                    self._gate_length_bins])
        self.pulsed.start()
        self.statusvar = 2
        self.signal_get_data_next.emit()
        return 0

    def stop_measure(self):
        """ Stop the fast counter. """

        with self.threadlock:
            if self.getState() == 'locked':
                self.stopRequested = True
        self.pulsed.stop()
        self.statusvar = 1
        self.unlock()
        return 0

    def pause_measure(self):
        """ Pauses the current measurement.

                Fast counter must be initially in the run state to make it pause.
                """

        self.stop_measure()
        self.statusvar = 3
        return 0

    def continue_measure(self):
        """ Continues the current measurement.

                If fast counter is in pause state, then fast counter will be continued.
                """
        # exit the pause state in the FPGA

        self.signal_get_data_next.emit()
        self.statusvar = 2
        return 0

    def is_gated(self):
        """ Check the gated counting possibility.

                Boolean return value indicates if the fast counter is a gated counter
                (TRUE) or not (FALSE).
                """

        return True

    def get_data_trace(self):
        """ Polls the current timetrace data from the fast counter.

                @return numpy.array: 2 dimensional array of dtype = int64. This counter
                                     is gated the the return array has the following
                                     shape:
                                        returnarray[gate_index, timebin_index]

                The binning, specified by calling configure() in forehand, must be taken
                care of in this hardware class. A possible overflow of the histogram
                bins must be caught here and taken care of.
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
        return self.statusvar

    def get_binwidth(self):
        """ Returns the width of a single timebin in the timetrace in seconds
            """

        width_in_seconds = self._binwidth * 1e-9
        return width_in_seconds
