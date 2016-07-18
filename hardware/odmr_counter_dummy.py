# -*- coding: utf-8 -*-
"""
This file contains the QuDi Dummy file for ODMRCounter.

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

import numpy as np
import time

from core.base import Base
import core.logger as logger
from interface.odmr_counter_interface import ODMRCounterInterface

class ODMRCounterDummy(Base, ODMRCounterInterface):
    """This is the Dummy hardware class that simulates the controls for a simple ODMR.
    """
    _modclass = 'ODMRCounterDummy'
    _modtype = 'hardware'

    # connectors
    _in = {'fitlogic': 'FitLogic'}
    _out = {'odmrcounter': 'ODMRCounterInterface'}

    def __init__(self, manager, name, config, **kwargs):
        state_actions = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, state_actions, **kwargs)

        logger.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            logger.info('{}: {}'.format(key,config[key]))

        if 'clock_frequency' in config.keys():
            self._clock_frequency=config['clock_frequency']
        else:
            self._clock_frequency=100
            logger.warning('No clock_frequency configured taking 100 Hz '
                    'instead.')

        self._scanner_counter_daq_task = None
        self._odmr_length = None

    def activation(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """
        self._fit_logic = self.connector['in']['fitlogic']['object']

    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        logger.debug('ODMR counter is shutting down.')

    def set_up_odmr_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of the clock
        @param str clock_channel: if defined, this is the physical channel of the clock

        @return int: error code (0:OK, -1:error)
        """

        if clock_frequency != None:
            self._clock_frequency = float(clock_frequency)

        logger.warning('ODMRCounterDummy>set_up_odmr_clock')

        time.sleep(0.2)

        return 0


    def set_up_odmr(self, counter_channel=None, photon_source=None,
                    clock_channel=None, odmr_trigger_channel=None):
        """ Configures the actual counter with a given clock.

        @param str counter_channel: if defined, this is the physical channel of the counter
        @param str photon_source: if defined, this is the physical channel where the photons are to count from
        @param str clock_channel: if defined, this specifies the clock for the counter
        @param str odmr_trigger_channel: if defined, this specifies the trigger output for the microwave

        @return int: error code (0:OK, -1:error)
        """

        logger.warning('ODMRCounterDummy>set_up_odmr')

        if self.getState() == 'locked' or self._scanner_counter_daq_task != None:
            logger.error('Another odmr is already running, close this one '
                    'first.')
            return -1

        time.sleep(0.2)

        return 0

    def set_odmr_length(self, length=100):
        """ Sets up the trigger sequence for the ODMR and the triggered microwave.

        @param int length: length of microwave sweep in pixel

        @return int: error code (0:OK, -1:error)
        """


        self._odmr_length = length
#
#        logger.warning('ODMRCounterDummy>set_odmr_length')

        return 0

    def count_odmr(self, length=100):
        """ Sweeps the microwave and returns the counts on that sweep.

        @param int length: length of microwave sweep in pixel

        @return float[]: the photon counts per second
        """

        if self.getState() == 'locked':
            logger.error('A scan_line is already running, close this one '
                    'first.')
            return -1

        self.lock()


        self._odmr_length = length

        count_data = np.empty((self._odmr_length,), dtype=np.uint32)

        count_data = np.random.uniform(0, 5e4, length)

        lorentians,params = self._fit_logic.make_multiplelorentzian_model(no_of_lor=2)

        sigma = 3.

        params.add('lorentz0_amplitude', value=-30000.*np.pi*sigma)
        params.add('lorentz0_center', value=length/3)
        params.add('lorentz0_sigma', value=sigma)
        params.add('lorentz1_amplitude', value=-30000*np.pi*sigma)
        params.add('lorentz1_center', value=2*length/3)
        params.add('lorentz1_sigma', value=sigma)
        params.add('c', value=50000.)

        count_data += lorentians.eval(x=np.arange(1, length+1, 1), params=params)

        time.sleep(self._odmr_length*1./self._clock_frequency)

        self.unlock()

        return count_data


    def close_odmr(self):
        """ Closes the odmr and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """

        logger.warning('ODMRCounterDummy>close_odmr')

        self._scanner_counter_daq_task = None

        return 0

    def close_odmr_clock(self):
        """ Closes the odmr and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """

        logger.warning('ODMRCounterDummy>close_odmr_clock')

        return 0
