# -*- coding: utf-8 -*-

"""
This file contains the QuDi hardware module to use TimeTagger as a counter.

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

from TimeTagger import createTimeTagger, Counter
from core.base import Base
from interface.slow_counter_interface import SlowCounterInterface
import time


class TimeTaggerCounter(Base, SlowCounterInterface):

    """ Using the TimeTagger as a counter."""

    _modtype = 'TTCounter'
    _modclass = 'hardware'

    # connectors
    _out = {'ttcounter': 'SlowCounterInterface'
            }

    def __init__(self, manager, name, config, **kwargs):
        # declare actions for state transitions
        c_dict = {'onactivate': self.activation,
                  'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, c_dict)

    def activation(self, e=None):
        """ Starts up the NI Card at activation.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """

        self._tagger = createTimeTagger()

        self._count_frequency = 10  # Hz

        config = self.getConfiguration()

        if 'photon_source' in config.keys():
            self._photon_source = config['photon_source']
        else:
            self.log.error('No parameter "photon_source" configured.\n'
                    'Assign to that parameter an appropriated channel '
                    'from your NI Card!')

    def deactivation(self, e=None):
        """ Shut down the NI card.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        #self.reset_hardware()
        pass

    def set_up_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of
                                      the clock
        @param string clock_channel: if defined, this is the physical channel
                                     of the clock

        @return int: error code (0:OK, -1:error)
        """

        self._count_frequency = clock_frequency
        return 0

    def set_up_counter(self,
                       counter_channel=None,
                       photon_source=None,
                       counter_channel2=None,
                       photon_source2=None,
                       clock_channel=None,
                       counter_buffer=None):
        """ Configures the actual counter with a given clock.

        @param str counter_channel: optional, physical channel of the counter
        @param str photon_source: optional, physical channel where the photons
                                  are to count from
        @param str counter_channel2: optional, physical channel of the counter 2
        @param str photon_source2: optional, second physical channel where the
                                   photons are to count from
        @param str clock_channel: optional, specifies the clock channel for the
                                  counter
        @param int counter_buffer: optional, a buffer of specified integer
                                   length, where in each bin the count numbers
                                   are saved.

        @return int: error code (0:OK, -1:error)
        """

        self.counter = Counter(self._tagger, channels=[self._photon_source], binwidth=int((1/self._count_frequency)*1e12), n_values=1)
        self.log.info('set up counter with {0}'.format(self._count_frequency))
        return 0

    def get_counter(self, samples=None):
        """ Returns the current counts per second of the counter.

        @param int samples: if defined, number of samples to read in one go

        @return numpy.array(uint32): the photon counts per second
        """

        time.sleep(2/self._count_frequency)
        return self.counter.getData()

    def close_counter(self):
        """ Closes the counter and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """


        return 0

    def close_clock(self):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """


        return 0
