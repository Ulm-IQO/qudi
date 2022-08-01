# -*- coding: utf-8 -*-
"""
A hardware module for communicating with the Swabian Instruments fast counter FPGA.

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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at thes
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import okfrontpanel
from interface.fast_counter_interface import FastCounterInterface
import numpy as np
import TimeTagger as TimeTagger
from core.module import Base
from core.configoption import ConfigOption

class TimeTaggerFastCounter(Base, FastCounterInterface):
    """ Hardware class to controls a Time Tagger from Swabian Instruments.

    Example config for copy-paste:

    fastcounter_timetagger:
        module.Class: 'swabian_instruments.TimeTagger_ungated_Fastcounter.TimeTaggerFastCounter'
        network: True
        address: '134.60.31.152:5353'
        channel_trigger: 1
        channel_apd: 2
        timetagger_serial: '1924000QHS'
        timetagger_resolution: 'Standard'

    """
    _network = ConfigOption('network', missing='error')
    _address = ConfigOption('address', missing='error')
    _channel_trigger = ConfigOption('channel_trigger', missing='error')
    _channel_apd = ConfigOption('channel_apd', missing='error')
    _timetagger_serial = ConfigOption('timetagger_serial', 'Standard', missing='warn')
    _timetagger_resolution = ConfigOption('timetagger_resolution', 'Standard', missing='warn')


    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # self.TimeTagger = Pyro5.api.Proxy("PYRO:TimeTagger@localhost:23000")
        self._record_length = int(4000)
        if self._network:
            self.timetagger = TimeTagger.createTimeTaggerNetwork(address=self._address)
            self.timetagger.setTriggerLevel(2, 1)
        else:
            self.timetagger = TimeTagger.createTimeTagger(self._timetagger_serial)

    def on_deactivate(self):
        """ Initialisation performed during deactivation of the module.
        """
        try:
            if self.module_state() == 'locked':
                self.histogram.stop()
            self.histogram.clear()
            TimeTagger.freeTimeTagger(self.timetagger)
            del self.timetagger, self.histogram
        except AttributeError:
            TimeTagger.freeTimeTagger(self.timetagger)
            del self.timetagger


    def get_constraints(self):
        """ Retrieve the hardware constrains from the Fast counting device.

        @return dict: dict with keys being the constraint names as string and
                      items are the definition for the constaints.

         The keys of the returned dictionary are the str name for the constraints
        (which are set in this method).

                    NO OTHER KEYS SHOULD BE INVENTED!

        If you are not sure about the meaning, look in other hardware files tomy
        get an impression. If still additional constraints are needed, then they
        have to be added to all files containing this interface.

        The items of the keys are again dictionaries which have the generic
        dictionary form:
            {'min': <value>,
             'max': <value>,
             'step': <value>,
             'unit': '<value>'}

        Only the key 'hardware_binwidth_list' differs, since they
        contain the list of possible binwidths.

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
        constraints['hardware_binwidth_list'] = [1 / 1000e9, 5/1e12, 10/1e12, 20/1e12, 50/1e12, 81/1e12, 1/1e9, 5/1e9, 1/1e6, 1/1e3, 1]
        return constraints

    def configure(self, bin_width_s, record_length_s, number_of_gates=0):
        """ Configuration of the fast counter.

        @param float bin_width_s: Length of a single time bin in the time race histogram in seconds.
        @param float record_length_s: Total length of the timetrace/each single gate in seconds.
        @param int number_of_gates: optional, number of gates in the pulse sequence. Ignore for not gated counter.

        @return tuple(binwidth_s, record_length_s, number_of_gates):
                    binwidth_s: float the actual set binwidth in seconds
                    gate_length_s: the actual record length in seconds
                    number_of_gates: the number of gated, which are accepted, None if not-gated
        """
        self._bin_width = int(bin_width_s * 1e12)
        print(f'binwidth{bin_width_s} recordlength{record_length_s}')
        self._record_length = 1+int(np.ceil(record_length_s/bin_width_s))
        print(self._bin_width, self._record_length)
        self.configured = True
        self.statusvar = 1
        self._number_of_gates = number_of_gates

        self.histogram = TimeTagger.Histogram(self.timetagger, self._channel_apd, self._channel_trigger, self._bin_width, self._record_length)

        self.histogram.stop()
        return self._bin_width*1e-12, self._record_length * self._bin_width/1e12, number_of_gates

    def get_status(self):
        """
        Receives the current status of the Fast Counter and outputs it as return value.
        0 = unconfigured
        1 = idle
        2 = running
        3 = paused
        -1 = error state
        """
        return self.statusvar

    def start_measure(self):
        """ Start the fast counter. """
        self.module_state.lock()
        self.histogram.clear()
        self.histogram.start()
        self.statusvar = 2
        return 0

    def stop_measure(self):
        """ Stop the fast counter. """
        if self.module_state() == 'locked':
            self.histogram.stop()
            self.module_state.unlock()
        self.statusvar = 1
        return 0

    def pause_measure(self):
        """ Pauses the current measurement.

        Fast counter must be initially in the run state to make it pause.
        """
        if self.module_state() == 'locked':
            self.histogram.stop()
            self.statusvar = 3
        return 0

    def continue_measure(self):
        """ Continues the current measurement.

        If fast counter is in pause state, then fast counter will be continued.
        """
        if self.module_state() == 'locked':
            self.histogram.start()
            self.statusvar = 2
        return 0

    def is_gated(self):
        """ Check the gated counting possibility.

        Boolean return value indicates if the fast counter is a gated counter
        (TRUE) or not (FALSE).
        """
        return False

    def get_data_trace(self):
        """ Polls the current timetrace data from the fast counter.

        @return numpy.array: 2 dimensional array of dtype = int64. This counter☻
                             is gated the the return array has the following
                             shape:
                                returnarray[gate_index, timebin_index]

        The binning, specified by calling configure() in forehand, must be taken
        care of in this hardware class. A possible overflow of the histogram
        bins must be caught here and taken care of.
        """
        info_dict = {'elapsed_sweeps': None,
                     'elapsed_time': None}  # TODO : implement that according to hardware capabilities
        return np.array(self.histogram.getData(), dtype='int64'), info_dict

    def get_binwidth(self):
        """ Returns the width of a single timebin in the timetrace in seconds. """
        width_in_seconds = self._bin_width * 1e-12
        return width_in_seconds




