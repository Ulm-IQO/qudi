# -*- coding: utf-8 -*-
"""
This file contains the Qudi Dummy file for ODMRCounter.

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

import numpy as np
import time

from core.module import Base, Connector, ConfigOption
from interface.odmr_counter_interface import ODMRCounterInterface

class ODMRCounterDummy(Base, ODMRCounterInterface):
    """This is the Dummy hardware class that simulates the controls for a simple ODMR.
    """
    _modclass = 'ODMRCounterDummy'
    _modtype = 'hardware'

    # connectors
    fitlogic = Connector(interface='FitLogic')

    # config options
    _clock_frequency = ConfigOption('clock_frequency', 100, missing='warn')
    _number_of_channels = ConfigOption('number_of_channels', 2, missing='warn')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self._scanner_counter_daq_task = None
        self._odmr_length = None

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._fit_logic = self.get_connector('fitlogic')

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.log.debug('ODMR counter is shutting down.')

    def set_up_odmr_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of the clock
        @param str clock_channel: if defined, this is the physical channel of the clock

        @return int: error code (0:OK, -1:error)
        """

        if clock_frequency is not None:
            self._clock_frequency = float(clock_frequency)

        self.log.info('ODMRCounterDummy>set_up_odmr_clock')

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

        self.log.info('ODMRCounterDummy>set_up_odmr')

        if self.module_state() == 'locked' or self._scanner_counter_daq_task is not None:
            self.log.error('Another odmr is already running, close this one '
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
        return 0

    def count_odmr(self, length=100):
        """ Sweeps the microwave and returns the counts on that sweep.

        @param int length: length of microwave sweep in pixel

        @return float[]: the photon counts per second
        """

        if self.module_state() == 'locked':
            self.log.error('A scan_line is already running, close this one '
                           'first.')
            return -1

        self.module_state.lock()

        self._odmr_length = length

        lorentians, params = self._fit_logic.make_lorentziandouble_model()

        sigma = 3.

        params.add('l0_amplitude', value=-30000)
        params.add('l0_center', value=length/3)
        params.add('l0_sigma', value=sigma)
        params.add('l1_amplitude', value=-30000)
        params.add('l1_center', value=2*length/3)
        params.add('l1_sigma', value=sigma)
        params.add('offset', value=50000.)

        ret = np.empty((self._number_of_channels, length))

        for chnl_index in range(self._number_of_channels):
            count_data = np.random.uniform(0, 5e4, length)
            count_data += (chnl_index + 1) * lorentians.eval(x=np.arange(1, length + 1, 1),
                                                             params=params)
            ret[chnl_index] = count_data

        time.sleep(self._odmr_length*1./self._clock_frequency)

        self.module_state.unlock()
        return ret


    def close_odmr(self):
        """ Closes the odmr and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """

        self.log.info('ODMRCounterDummy>close_odmr')

        self._scanner_counter_daq_task = None

        return 0

    def close_odmr_clock(self):
        """ Closes the odmr and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """

        self.log.info('ODMRCounterDummy>close_odmr_clock')

        return 0

    def get_odmr_channels(self):
        """ Return a list of channel names.

        @return list(str): channels recorded during ODMR measurement
        """
        return ['ch{0:d}'.format(i) for i in range(1, self._number_of_channels + 1)]
