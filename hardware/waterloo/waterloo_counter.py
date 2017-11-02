# -*- coding: utf-8 -*-
"""
Created on Tue Oct 04 13:21:27 2016

@author: jk5430
@modified_by: ej15947
"""
from __future__ import division

import time
import socket
import json


class mysocket:
    '''
    demonstration class only
      - coded for clarity, not efficiency
    '''

    def __init__(self, sock=None, channels=[], biases=[], delay=[], coincidence=[], window=0, histogram_channels=[],
                 histogram_windows_ns=[]):
        self.need_setup = 1
        self.channels = channels
        self.biases = biases
        self.delay = delay
        self.coincidence = coincidence
        self.window = 0
        self.histogram_channels = histogram_channels
        self.histogram_windows_ns = histogram_windows_ns
        if sock is None:
            self.sock = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock

    def send_setup(self):
        '''
        Send JSON encoded settings to detector server
        '''
        print("------------------- sending setup ----------------------")
        #               print self.current_setup
        message = json.dumps(self.current_setup)
        self.send(message)
        print(message)
        print("--------------------------------------------------------")

    def connect(self, host, port):
        self.sock.connect((host, port))

    def send(self, msg):
        totalsent = 0
        while totalsent < len(msg):
            sent = self.sock.send(bytes(msg[totalsent:].encode("utf-8")))
            if sent == 0:
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent

    def recv(self, msglen):
        chunks = []
        bytes_recd = 0

        while bytes_recd < msglen:
            chunk = self.sock.recv(min(msglen - bytes_recd, 2048))
            #                       print ('\'' + chunk + '\'')
            if chunk == '':
                raise RuntimeError("socket connection broken")
            done = 0
            end = 0
            items_found = 0
            # Look for { ... } pairs, and consider them to be complete messages
            while not done:
                start = chunk.find('{'.encode("utf-8"), end);
                if (start >= 0):
                    end = chunk.find('}'.encode("utf-8"), start)
                    if (end >= 0):
                        json_str = chunk[start:end + 1]
                        json_data = json.loads(str(json_str, "utf-8"))
                        #                                               print (json_data)
                        if json_data["type"] == "setup":
                            self.handle_setup(json_data)
                        items_found += 1
                        chunks.append(json_data)
                    else:
                        done = 1
                else:
                    done = 1
            bytes_recd = bytes_recd + len(chunk)
        # print (items_found)
        return chunks

    def close(self):
        self.sock.close()

    def set_channels(self, channels, input_threshold_volts, delay_ns):
        active_channel_bits = sum(1 << (chan - 1) for (chan) in channels)

        #               active_channel_bits = 0xffff
        #               input_threshold_volts = -2.0

        self.current_setup["active_channels"] = active_channel_bits
        index = 0
        for chan in channels:
            self.current_setup["input_threshold_volts"][chan - 1] = input_threshold_volts[index]
            self.current_setup["channel_delay_ns"][chan - 1] = delay_ns[index]
            #                       self.current_setup["input_threshold_volts"][chan - 1] = input_threshold_volts[index]
            index += 1

    def add_coincidence(self, channels, coincidence_window_ns):
        co_channel_mask = sum(1 << (chan - 1) for (chan) in channels)
        self.current_setup["coincidence_channels"].append(co_channel_mask)
        self.current_setup["coincidence_windows_ns"].append(coincidence_window_ns)

    def add_histogram(self, histogram_channels, histogram_window_ns):
        co_histogram_mask = sum(1 << (chan - 1) for (chan) in histogram_channels)
        self.current_setup["histogram_channels"].append(co_histogram_mask)
        self.current_setup["histogram_windows_ns"].append(histogram_window_ns)

    ###### Here's where you set the number of channels, etc.
    def handle_setup(self, setup_object):
        self.current_setup = setup_object

        if (self.need_setup):
            self.current_setup["user_name"] = "Lawrence"
            self.current_setup["user_platform"] = "python3"
            #                       self.current_setup["poll_time"] = 1.0
            self.need_setup = 0

            # "I want data from channels 7, 15 and 16, with voltages -0.2 and delay 0ns"
            self.set_channels(self.channels, self.biases, self.delay)

            # "I want coincidences on channel 7 and 15, with 256 window"
            self.add_coincidence(self.coincidence, self.window)

            self.send_setup()

    def update_timing_window(self, integration_time):
        if self.need_setup:
            self.recv(1024)
        else:
            self.current_setup['poll_time'] = integration_time
            self.send_setup()

    # ===========================================================================
    # def process_singles(self, msgbytes, channel, signal_search=False):
    #       '''
    #       Depricated method use self.singles() instead
    #       '''
    #       data = self.recv(msgbytes)
    #       counts, time_diff, times = [], [], []
    #       for d in data:
    #               if d['type'] == 'counts':
    #                       if signal_search:
    #                               return d['counts'][channel-1]/d['span_time']
    #                       elif d['time'] not in times:
    #                               times.append(d['time'])
    #                               time_diff.append(d['span_time'])
    #                               counts.append(d['counts'][channel-1])
    #
    #       normalised_counts = []
    #       for c, t in zip(counts, time_diff):
    #               normalised_counts.append(float(c)/float(t))
    #
    #       if normalised_counts:
    #               counts_Hz = sum(normalised_counts)/len(normalised_counts)
    #               return counts_Hz
    #       else:
    #               return 0
    # ===========================================================================

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
        if isinstance(channels, (list, tuple)):
            num_channels = len(channels)
            singles = [0] * num_channels
        elif isinstance(channels, int):
            num_channels = 1
            singles = [0]
            channels = [channels]
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

                    # now loop through every channel and add the number of singles
                    for j in range(num_channels):
                        channel = channels[j] - 1
                        singles[j] += data[i]['counts'][channel]

                    # add to our total time integrated for
                    reltime += data[i]['span_time']

                    if (reltime >= inttime):
                        break

                        #               print ('singles:',singles, 'integration time:', reltime, 'counts/s',[single/reltime for single in singles])

        return [single / reltime for single in singles]

    def __del__(self):
        try:
            self.close()
        except:
            pass


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


if __name__ == '__main__':
    msgbytes = int(4096)
    channels = [5, 6]
    coincs = [5, 6]
    inttime = 5
    histogram_windows_ns = 50

    TCP_IP = 'det.phy.bris.ac.uk'
    TCP_PORT = 8080
    biases = [-0.10, -0.10]
    delay = [0, 0]
    window = 256

    ms = mysocket(sock=None, channels=channels, biases=biases, delay=delay, coincidence=channels, window=window,
                  histogram_channels=channels, histogram_windows_ns=histogram_windows_ns)
    ms.connect(TCP_IP, TCP_PORT)
    ms.update_timing_window(window)

    for _ in range(100):
        singles = ms.singles([5, 6], inttime=5.0)
        print(singles)

    # from time import time
    # #
    #       t = time()
    #       print ('singles 1s poll:', ms.process_singles(msgbytes=2048, channel=6))
    #       print ('time for cps',time() - t,'s')
    #
    #       window = 5.0
    #       for _ in range(10):
    #               t = time()
    #               print ('singles {}s poll: {:.1f}'.format(window, ms.process_singles(msgbytes=1300, channel=6)))
    #               print ('time for cps {:.4f} s'.format(time() - t))


    #       _, channel1, channel2, _ = integrate(ms, msgbytes, channels,  inttime)
    ms.close()

    #       print("channel 1: ", channel1)
    #       print("channel 2: ", channel2)

    # TCP_IP = 'det.phy.bris.ac.uk'
    # TCP_PORT = 8080

    # ms = mysocket()

    # ms.connect(TCP_IP, TCP_PORT)

    # message = 'setup'
    # ms.send(message)

    # data = ms.recv(8192)
    # ms.close()

    # print(data[5]['coincidence'][0])

    # print ("received data:", data)