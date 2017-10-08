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

import logging
from core.module import Base
from interface.slow_counter_interface import SlowCounterInterface
from interface.slow_counter_interface import SlowCounterConstraints
from interface.slow_counter_interface import CountingMode

import socket
import json


class mysocket:
    '''demonstration class only
      - coded for clarity, not efficiency
    '''

    def __init__(self, sock=None, channels=[], biases=[], delays=[], coincidences=[], window=0, histogram_channels=[],
                 histogram_windows_ns=[]):
        if sock is None:
            self.sock = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock
        self.need_setup = 1
        self.channels = channels
        self.biases = biases
        self.delays = delays
        self.coincidences = coincidences
        self.window = 0
        self.histogram_channels = histogram_channels
        self.histogram_windows_ns = histogram_windows_ns

    def send_setup(self):
        #logging.info("------------------- sending setup ----------------------")
        #        print self.current_setup
        message = json.dumps(self.current_setup)
        self.send(message)
        #logging.info(message)
        #logging.info("--------------------------------------------------------")

    def connect(self, host, port):
        self.sock.connect((host, port))

    def send(self, msg):
        #msg should be bytes
        totalsent = 0
        while totalsent < len(msg):
            #logging.info(type(msg))
            #logging.info(msg.type)
            #logging.info(msg[totalsent:])

            sent = self.sock.send(bytes(msg[totalsent:].encode("utf-8")))
            if sent == 0:
                logging.error("Socket connection to Waterloo broken")
            totalsent = totalsent + sent

    def recv(self, msglen):
        chunks = []
        bytes_recd = 0

        while bytes_recd < msglen:
            chunk = self.sock.recv(min(msglen - bytes_recd, 2048))
            #            print '\'' + chunk + '\''
            if chunk == '':
                logging.error("socket connection broken")
            done = 0
            end = 0
            items_found = 0
            # Look for { ... } pairs, and consider them to be complete messages
            while not done:
                start = bytes(chunk).find(bytes('{'.encode('utf8')), end);
                if (start >= 0):
                    end = bytes(chunk).find(bytes('}'.encode('utf8')), start)
                    if (end >= 0):
                        json_str = chunk[start:end + 1]
                        json_data = json.loads(json_str)
                        #print(json_data)
                        if json_data["type"] == "setup":
                            self.handle_setup(json_data)
                        items_found += 1
                        chunks.append(json_data)
                    else:
                        done = 1
                else:
                    done = 1
            bytes_recd = bytes_recd + len(chunk)
        # print items_found
        return chunks

    def close(self):
        self.sock.close()

    def set_channels(self, channels, input_threshold_volts, delay_ns):
        active_channel_bits = sum(1 << (chan - 1) for (chan) in channels)

        #        active_channel_bits = 0xffff
        #        input_threshold_volts = -2.0

        self.current_setup["active_channels"] = active_channel_bits
        index = 0
        for chan in channels:
            self.current_setup["input_threshold_volts"][chan - 1] = input_threshold_volts[index]
            self.current_setup["channel_delay_ns"][chan - 1] = delay_ns[index]
            #            self.current_setup["input_threshold_volts"][chan - 1] = input_threshold_volts[index]
            index += 1

    def add_coincidence(self, channels, coincidence_window_ns):
        co_channel_mask = sum(1 << (chan - 1) for (chan) in channels)
        self.current_setup["coincidence_channels"].append(co_channel_mask)
        self.current_setup["coincidence_windows_ns"].append(coincidence_window_ns)

    def update_timing_window(self, integration_time):
        if self.need_setup:
            self.recv(1024)
        else:
            self.current_setup['poll_time'] = integration_time
            self.send_setup()

    ###### Here's where you se the number of channels, etc.
    def handle_setup(self, setup_object):
        self.current_setup = setup_object

        if (self.need_setup):
            self.current_setup["user_name"] = "trapping_pc"
            self.current_setup["user_platform"] = "python"
            self.need_setup = 0

            # "I want data from channels 7, 15 and 16, with voltages -0.1 and delay 0ns"
            self.set_channels(self.channels, self.biases, self.delays)

            # "I want coincidences on channel 7 and 15, with 4000ns window"
            # self.add_coincidence([7, 15], 4000)

            # "I ALSO want coincidences on channel 7 and 15, with 4000ns window"
            # self.add_coincidence([15, 16], 4000)
            self.send_setup()

    def singles(self, channels, inttime=1.0, msgbytes=2048):
        '''
        Integrate the singles counts per second for an arbitrary number of
        channels
        --------
        :channels:
                list or tuple of ints, or an int specifying the channel(s) to
                integrate singles for
        :inttime:
                positive float - total time to integrate for
        :msgbytes:
                positive int - size of message in bytes to recieve from websocket
        '''
        # Check for correct datatypes
        #logging.info(channels)
        if isinstance(channels, (list, tuple)):
            num_channels = len(channels)
            singles = [0] * num_channels
        elif isinstance(channels, int):
            num_channels = 1
            singles = [0]
            channels = channels
        else:
            raise TypeError('channels arg must be a list, tuple or int')

        if not isinstance(msgbytes, int):
            try:
                msgbytes = int(msgbytes)
            except:
                raise TypeError('msgbytes arg must be an int')

        reltime = 0.
        attempts = 0
        MAX_ATTEMPTS = 10

        while (reltime < inttime):

            # Attempt to handle errors from the socket not responding
            try:
                # get our data from the socket
                data = self.recv(msgbytes)
                #logging.info(data)
                if not data:
                    continue
                attempts = 0
            except:
                attempts += 1
                if attempts < MAX_ATTEMPTS:
                    print('An error occurred... trying again (attempt {}/{})'.format(attempts, MAX_ATTEMPTS))
                else:
                    print('Maximum number of tries reached... quitting')
                    self.__del__()
                    raise
                continue

            # loop through the data acquired
            for i in range(1, len(data) - 1):

                # check the datatype
                if data[i]['type'] == 'counts':
                    #logging.info(data[i]['counts'])
                    # now loop through every channel and add the number of singles
                    for j in range(num_channels):
                        channel = 0 #TODO : fix
                        singles[j] += data[i]['counts'][channel]
                        #logging.info(singles[j])
                        #logging.info(channel)

                    # add to our total time integrated for
                    reltime += data[i]['span_time']
                    #logging.info(reltime)
                    #logging.info(inttime)
                    if (reltime >= inttime):
                        break

                        #               print ('singles:',singles, 'integration time:', reltime, 'counts/s',[single/reltime for single in singles])
        #logging.info(singles)
        return [single / reltime for single in singles]

    def integrate(ms, msgbytes, channels, inttime):
        singles = [0, 0]
        coincidence = 0.
        reltime = 0.00000001

        #       message = 'setup'
        #       ms.send(message)

        # print('Recieving data')
        # data = ms.recv(int(msgbytes/4))
        # print (len(data))
        #       print('reltime\t\tsingles[0]\tsingles[1]\tcoincidence')

        while (reltime < inttime):
            data = ms.recv(msgbytes)
            datlen = len(data)
            #               print (len(data))
            # while len(data) < 8: #ensure that we actually got something
            # print('Recieving data')
            # data = ms.recv(msgbytes)
            # print (len(data))

            for i in range(1, datlen - 1):
                if data[i]['type'] == 'counts':
                    if len(data[i]['coincidence']) == 1:
                        singles[0] += data[i]['counts'][channels[0] - 1]
                        singles[1] += data[i]['counts'][channels[1] - 1]
                        coincidence += data[i]['coincidence'][0]
                        reltime += data[i]['span_time']

                        #               print('{0: 6.2f}\t\t{1: 6.0f}\t\t{2: 6.0f}\t\t{3: 6.2f}' .format(reltime, singles[0]/reltime,  singles[1]/reltime,  coincidence/reltime))

        return [reltime, singles[0] / reltime, singles[1] / reltime, coincidence / reltime]

    def __del__(self):
        try:
            self.close()
        except:
            pass


class WaterlooCounter2(Base, SlowCounterInterface):

    """ Using the TimeTagger as a counter."""

    _modclass = 'WaterlooCounter2'
    _modtype = 'hardware'

    _out = {'counter1': 'SlowCounterInterface'}


    def on_activate(self):
        """ Start up TimeTagger interface
        """

        TCP_IP = 'localhost'
        TCP_PORT = 5001
        window = 256

        self.ms = mysocket(sock=None, channels=[1], biases=[1.1], delays=[0], coincidences=[0], window=window,
                  histogram_channels=[1], histogram_windows_ns=50)
        self.ms.connect(TCP_IP, TCP_PORT)
        self.ms.update_timing_window(window)
        self._channel_apd = 1
        message = 'setup'
        self.ms.send(message)

        self._count_frequency = 100  # Hz

        config = self.getConfiguration()

        if 'timetagger_channel_apd_0' in config.keys():
            self._channel_apd_0 = config['timetagger_channel_apd_0']
        else:
            self.log.error('No parameter "timetagger_channel_apd_0" configured.\n')

        if 'timetagger_channel_apd_1' in config.keys():
            self._channel_apd_1 = config['timetagger_channel_apd_1']
        else:
            self._channel_apd_1 = None

        if 'timetagger_sum_channels' in config.keys():
            self._sum_channels = config['timetagger_sum_channels']
        else:
            #self.log.warning('No indication whether or not to sum apd channels for timetagger. Assuming false.')
            self._sum_channels = False
            self._channel_apd = 0

        if self._sum_channels and ('timetagger_channel_apd_1' in config.keys()):
            self.log.error('Cannot sum channels when only one apd channel given')

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
        self.ms.close()

    def set_up_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the TimeTagger for timing

        @param float clock_frequency: if defined, this sets the frequency of
                                      the clock
        @param string clock_channel: if defined, this is the physical channel
                                     of the clock

        @return int: error code (0:OK, -1:error)
        """

        self._count_frequency = clock_frequency
        self.ms.update_timing_window(1/self._count_frequency)
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

        self.ms.channels = counter_channels


        return 0

    def get_counter_channels(self):
            return [self._channel_apd]


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
        #self._tagger.start()
        #n = 2/self._count_frequency
        #n =self._count_frequency
        #time.sleep(2/n)
        # singles for the last 1/ n seconds of data
        # to convert to counts per second

        #self.log.info(data)
        singles = self.ms.singles(self.get_counter_channels(), inttime=1/self._count_frequency)

        return singles
        #data = data[0]
        #self.log.info(data)


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

