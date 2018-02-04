# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware module to use TimeTagger as a counter.

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

import visa
import logging
from core.module import Base
from interface.slow_counter_interface import SlowCounterInterface
from interface.slow_counter_interface import SlowCounterConstraints
from interface.slow_counter_interface import CountingMode
import socket
import json
import time
import numpy as np
import math


class Keithley(Base, SlowCounterInterface):

    """ Using the TimeTagger as a counter."""

    _modclass = 'Keithley'
    _modtype = 'hardware'

    _out = {'counter1': 'SlowCounterInterface'}


    def on_activate(self):
        """ Start up TimeTagger interface
            This is where the channels and coincidences are decided
        """



        config = self.getConfiguration()

        if 'timetagger_channel_apd_0' in config.keys():
            self._channel_apd_0 = config['timetagger_channel_apd_0']
            self._chan_list = [config['timetagger_channel_apd_0']]
        else:
            self.log.error('No parameter "timetagger_channel_apd_0" configured.\n')


        if 'averager' in config.keys():
            self._chan_list.append(2)
            self._chan_list.append(3)
            self._chan_list.append(4)
            #self._chan_list.append(2)

        if 'timetagger_channel_apd_1' in config.keys():
            self._channel_apd_1 = config['timetagger_channel_apd_1']
            self._chan_list.append(config['timetagger_channel_apd_1'])
        else:
            self._channel_apd_1 = None

        if 'coincidence' in config.keys():
            self._coincidence = config['coincidence']
        else:
            self._coincidence = []

        try:
            self.rm = visa.ResourceManager()
            self.srs = self.rm.open_resource('GPIB1::18::INSTR')
            idn = self.srs.write('*IDN?')
            idn = self.srs.read()
            self.log.info(' Connected {0}'.format(idn))
        except visa.VisaIOError:
            self.log.error('GPIB device not found')
            return False

        self._count_frequency = 100  # Hz


        if 'timetagger_sum_channels' in config.keys():
            self._sum_channels = config['timetagger_sum_channels']
        else:
            #self.log.warning('No indication whether or not to sum apd channels for timetagger. Assuming false.')
            self._sum_channels = False
            self._channel_apd = 0

        if self._sum_channels and ('timetagger_channel_apd_1' in config.keys()):
            self.log.error('Cannot sum channels when only one apd channel given')

        if 'coincidence_window' in config.keys():
            self._coin_window = config[ 'coincidence_window']
        else:
            self._coin_window = 400e-9
            #self.log.info('No coincidence window set. Choosing 400 ns')

        ## self._mode can take 3 values:
        # 0: single channel, no summing
        # 1: single channel, summed over apd_0 and apd_1
        # 2: dual channel for apd_0 and apd_1
        if self._sum_channels:
            self._mode = 1
        elif self._channel_apd_1 is None:
            self._mode = 0
        else:
            self._mode = 2


    def on_deactivate(self):
        """ Shut down the TimeTagger.
        """
        #self.reset_hardware()
        #message = 'disconnect'
        #self.ms.send(message)
        #print('deactivate')
        #self.ms.close()
        self.srs.clear()
        self.srs.close()
        self.rm.close()

    def set_up_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the TimeTagger for timing

        @param float clock_frequency: if defined, this sets the frequency of
                                      the clock
        @param string clock_channel: if defined, this is the physical channel
                                     of the clock

        @return int: error code (0:OK, -1:error)
        """


        #self._count_frequency = clock_frequency

        #self.ms.send('setup')
        #self.ms.update_timing_window(1/self._count_frequency)

        return 0


    def set_up_counter(self,
                       counter_channels=None,
                       sources=None,
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

        self.srs.write('*LANG TSP')
        self.srs.write('reset()')
        self.srs.write('display.changescreen(display.SCREEN_USER_SWIPE)')
        self.srs.write('display.settext(display.TEXT1, "QUDI CONTROL")')
        self.srs.write('smu.measure.func =smu.FUNC_DC_CURRENT')
        self.srs.write('smu.measure.autorange = smu.ON')
        self.srs.write('smu.source.ilimit.level = 50E-6')
        self.srs.write('smu.source.func = smu.FUNC_DC_VOLTAGE')
        self.srs.write('smu.source.level = -6') #-8.69
        self.srs.write('smu.source.output = smu.ON')

        return 0

    def get_counter_channels(self):

        '''
        Return list of counter channels. Useful to work out if coincidences in use

        '''

        channels = ['APD 0']
        if self._channel_apd_1 is not None:
            channels.append('APD 1')
        if self._coincidence:
            channels.append('Coincidence/ APD 0')

        return channels


    def get_constraints(self):
        """ Get hardware limits the device

        @return SlowCounterConstraints: constraints class for slow counter

        FIXME: ask hardware for limits when module is loaded
        """
        constraints = SlowCounterConstraints()
        constraints.max_detectors = 2
        constraints.min_count_frequency = 1e-3
        constraints.max_count_frequency = 10e9
        constraints.counting_mode = [CountingMode.CONTINUOUS]
        return constraints

    def get_counter(self, samples=None):
        """ Returns the current counts per second of the counter.

        @param int samples: if defined, number of samples to read in one go

        @return numpy.array(uint32): the photon counts per second
        """

        if samples is None:
            samples = 1

        found = 0
        counts_out = []


        while found < 1:

            counts_out_col = []


            counts0 = abs(float(self.srs.query('print(smu.measure.read())'))*1e12)

            counts_out_col.append(counts0)
            if self._channel_apd_1 is not None:
                counts_out_col.append(0)
                counts_out_col.append(0)

            #print(counts0)
            counts_out.append(counts_out_col)
            #print(counts_out)
            found = found + 1



        # for x in range(0, len(data)):
        #
        #     counts_out_col = []
        #     try:
        #         deltatime = data[x]['delta_time']
        #
        #         counts = np.array(data[x]['counts'])
        #         #print(counts)
        #         counts0 = np.median(counts[0:3])
        #
        #         if counts0 is None or counts0 is 0:
        #             counts0 = 1
        #
        #         counts_out_col.append(round(counts0/deltatime))
        #
        #         if self._channel_apd_1 is not None:
        #             counts_out_col.append(0)
        #             counts_out_col.append(0)
        #
        #         counts_out.append(counts_out_col)
        #     except KeyError:
        #         pass

        if counts_out:
            counts_out = np.transpose(np.array(counts_out, dtype=np.uint32))
        else:
            counts_out = np.ones((len(self.get_counter_channels()), samples), dtype=np.uint32)*0

        return counts_out



    def close_counter(self, scanner=False):
        """ Closes the counter and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        #message = 'disconnect'
        #self.ms.send(message)
        #self.ms.sock.close()


        #self.ms.send('disconnect')

        self.srs.write('smu.source.output = smu.OFF')
        #time.sleep(0.2)
        return 0

    def close_clock(self, scanner=False):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """

        #message = 'setup'
        #self.ms.send('disconnect')

        # Try to make the server not hang by sending the setup
        #message = 'setup'
        #self.ms.send(message)
        #self.ms.recv(1)

        return 0

