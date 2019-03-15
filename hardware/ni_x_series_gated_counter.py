# -*- coding: utf-8 -*-

"""
This file contains the Qudi Hardware module NICard class.

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
import re

import PyDAQmx as daq

from core.module import Base, ConfigOption
from interface.slow_counter_interface import SlowCounterInterface
from interface.slow_counter_interface import SlowCounterConstraints
from interface.slow_counter_interface import CountingMode


class NationalInstrumentsXSeriesGatedCounter(Base, SlowCounterInterface):
    """ A National Instruments device that can count and control microvave generators.

    !!!!!! NI USB 63XX, NI PCIe 63XX and NI PXIe 63XX DEVICES ONLY !!!!!!

    See [National Instruments X Series Documentation](@ref nidaq-x-series) for details.

    Example config for copy-paste:

    nicard_6343:
        module.Class: 'ni_x_series_counter.NationalInstrumentsXSeriesGatedCounter'
        photon_sources: '/Dev1/PFI8'
        counter_channel: '/Dev1/Ctr1'
        gate_in_channel: '/Dev1/PFI7'

        default_samples_number: 50
        max_counts: 3e7
        read_write_timeout: 10
        counting_edge_rising: True

    """

    _modtype = 'NICard'
    _modclass = 'hardware'

    # config options
    _photon_source = ConfigOption('photon_sources', missing='error')

    _counter_channel = ConfigOption('counter_channels', missing='error')

    _gate_in_channel = ConfigOption('gate_in_channel', missing='error')
    # number of readout samples, mainly used for gated counter
    _default_samples_number = ConfigOption('default_samples_number', 50, missing='info')

    _max_counts = ConfigOption('max_counts', default=3e7)
    # timeout for the Read or/and write process in s
    _RWTimeout = ConfigOption('read_write_timeout', default=10)
    _counting_edge_rising = ConfigOption('counting_edge_rising', default=True)

    def on_activate(self):
        """ Starts up the NI Card at activation.
        """
        # the tasks used on that hardware device:
        self._gated_counter_daq_task = None

    def on_deactivate(self):
        """ Shut down the NI card.
        """
        self.close_counter()
        self.close_clock()

    def get_constraints(self):
        """ Get hardware limits of NI device.

        @return SlowCounterConstraints: constraints class for slow counter

        FIXME: ask hardware for limits when module is loaded
        """
        constraints = SlowCounterConstraints()
        constraints.max_detectors = 4
        constraints.min_count_frequency = 1e-3
        constraints.max_count_frequency = 10e9
        constraints.counting_mode = [CountingMode.FINITE_GATED]
        return constraints

    def set_up_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of the clock
        @param string clock_channel: if defined, this is the physical channel of the clock
        @return int: error code (0:OK, -1:error)
        """
        # ignore that command. For an gated counter (with external trigger
        # you do not need a clock signal).
        pass

    def set_up_counter(self,
                       counter_channels=None,
                       sources=None,
                       clock_channel=None,
                       counter_buffer=None):
        """ Configures the actual counter with a given clock.

        @param list(str) counter_channels: optional, physical channel of the counter
        @param list(str) sources: optional, physical channel where the photons
                                   photons are to count from
        @param str clock_channel: optional, specifies the clock channel for the
                                  counter
        @param int counter_buffer: optional, a buffer of specified integer
                                   length, where in each bin the count numbers
                                   are saved.

        @return int: error code (0:OK, -1:error)

        There need to be exactly the same number sof sources and counter channels and
        they need to be given in the same order.
        All counter channels share the same clock.
        """
        if self.set_up_gated_counter(buffer_length=counter_buffer) < 0:
            return -1
        return self.start_gated_counter()

    def get_counter(self, samples=None):
        """ Returns the current counts per second of the counter.

        @param int samples: if defined, number of samples to read in one go

        @return numpy.array((n, uint32)): the photon counts per second for n channels
        """
        return self.get_gated_counts(samples=samples)

    def get_counter_channels(self):
        """ Returns the list of counter channel names.

        @return list(str): channel names

        Most methods calling this might just care about the number of channels, though.
        """
        return set(self._counter_channel)

    def close_counter(self):
        """ Closes the counter and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        if self.stop_gated_counter() < 0:
            return -1
        return self.close_gated_counter()

    def close_clock(self):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        pass

    def get_status(self):
        """ Receives the current status of the Fast Counter and outputs it as
            return value.

        0 = unconfigured
        1 = idle
        2 = running
        3 = paused
        -1 = error state
        """
        if self._gated_counter_daq_task is None:
            return 0
        else:
            # return value represents a uint32 value, i.e.
            #   task_done = 0  => False, i.e. device is runnin
            #   task_done !=0  => True, i.e. device has stopped
            task_done = daq.bool32()

            ret_v = daq.DAQmxIsTaskDone(
                # task reference
                self._gated_counter_daq_task,
                # reference to bool value.
                daq.byref(task_done))

            if ret_v != 0:
                return ret_v

            if task_done.value() == 0:
                return 1
            else:
                return 2

    # ======================== Gated photon counting ==========================

    def set_up_gated_counter(self, buffer_length, read_available_samples=False):
        """ Initializes and starts task for external gated photon counting.

        @param int buffer_length: Defines how long the buffer to be filled with
                                  samples should be. If buffer is full, program
                                  crashes, so use upper bound. Some reference
                                  calculated with sample_rate (in Samples/second)
                                  divided by Buffer_size:
                                  sample_rate/Buffer_size =
                                      no rate     /  10kS,
                                      (0-100S/s)  /  10kS
                                      (101-10kS/s)/   1kS,
                                      (10k-1MS/s) / 100kS,
                                      (>1MS/s)    / 1Ms
        @param bool read_available_samples: if False, NiDaq waits for the
                                            sample you asked for to be in the
                                            buffer before, if True it returns
                                            what is in buffer until 'samples'
                                            is full
        """
        if self._gated_counter_daq_task is not None:
            self.log.error(
                'Another gated counter is already running, close this one first.')
            return -1

        try:
            # This task will count photons with binning defined by pulse task
            # Initialize a Task
            self._gated_counter_daq_task = daq.TaskHandle()
            daq.DAQmxCreateTask('GatedCounter', daq.byref(self._gated_counter_daq_task))

            # Set up pulse width measurement in photon ticks, i.e. the width of
            # each pulse generated by pulse_out_task is measured in photon ticks:
            daq.DAQmxCreateCIPulseWidthChan(
                # add to this task
                self._gated_counter_daq_task,
                # use this counter
                self._counter_channel,
                # name you assign to it
                'Gated Counting Task',
                # expected minimum value
                0,
                # expected maximum value
                self._max_counts,
                # units of width measurement,  here photon ticks.
                daq.DAQmx_Val_Ticks,
                # start pulse width measurement on rising edge
                self._counting_edge_rising,
                '')

            # Set the pulses to counter self._counter_channel
            daq.DAQmxSetCIPulseWidthTerm(
                self._gated_counter_daq_task,
                self._counter_channel,
                self._gate_in_channel)

            # Set the timebase for width measurement as self._photon_source, i.e.
            # define the source of ticks for the counter as self._photon_source.
            daq.DAQmxSetCICtrTimebaseSrc(
                self._gated_counter_daq_task,
                self._counter_channel,
                self._photon_source)

            # set timing to continuous
            daq.DAQmxCfgImplicitTiming(
                # define to which task to connect this function.
                self._gated_counter_daq_task,
                # Sample Mode: set the task to generate a continuous amount of running samples
                daq.DAQmx_Val_ContSamps,
                # buffer length which stores temporarily the number of generated samples
                buffer_length)

            # Read samples from beginning of acquisition, do not overwrite
            daq.DAQmxSetReadRelativeTo(self._gated_counter_daq_task, daq.DAQmx_Val_CurrReadPos)

            # If this is set to True, then the NiDaq will not wait for the sample
            # you asked for to be in the buffer before read out but immediately
            # hand back all samples until samples is reached.
            if read_available_samples:
                daq.DAQmxSetReadReadAllAvailSamp(self._gated_counter_daq_task, True)

            # Do not read first sample:
            daq.DAQmxSetReadOffset(self._gated_counter_daq_task, 0)

            # Unread data in buffer is not overwritten
            daq.DAQmxSetReadOverWrite(
                self._gated_counter_daq_task,
                daq.DAQmx_Val_DoNotOverwriteUnreadSamps)
        except:
            self.log.exception('Error while setting up gated counting.')
            return -1
        return 0

    def start_gated_counter(self):
        """Actually start the preconfigured counter task

        @return int: error code (0:OK, -1:error)
        """
        if self._gated_counter_daq_task is None:
            self.log.error(
                'Cannot start Gated Counter Task since it is notconfigured!\n'
                'Run the set_up_gated_counter routine.')
            return -1

        try:
            daq.DAQmxStartTask(self._gated_counter_daq_task)
        except:
            self.log.exception('Error while starting up gated counting.')
            return -1
        return 0

    def get_gated_counts(self, samples=None, timeout=None, read_available_samples=False):
        """ Returns latest count samples acquired by gated photon counting.

        @param int samples: if defined, number of samples to read in one go.
                            How many samples are read per readout cycle. The
                            readout frequency was defined in the counter setup.
                            That sets also the length of the readout array.
        @param int timeout: Maximal timeout for the read process. Since nidaq
                            waits for all samples to be acquired, make sure
                            this is long enough.
        @param bool read_available_samples : if False, NiDaq waits for the
                                             sample you asked for to be in the
                                             buffer before, True it returns
                                             what is in buffer until 'samples'
                                             is full.
        """

        samples = int(samples) if samples is not None else int(self._samples_number)

        if timeout is None:
            timeout = self._RWTimeout

        # Count data will be written here
        _gated_count_data = np.empty([2, samples], dtype=np.uint32)

        # Number of samples which were read will be stored here
        n_read_samples = daq.int32()

        if read_available_samples:
            # If the task acquires a finite number of samples
            # and you set this parameter to -1, the function
            # waits for the task to acquire all requested
            # samples, then reads those samples.
            num_samples = -1
        else:
            num_samples = int(samples)
        try:
            daq.DAQmxReadCounterU32(
                # read from this task
                self._gated_counter_daq_task,
                # read number samples
                num_samples,
                # maximal timeout for the read process
                timeout,
                _gated_count_data[0],
                # write into this array
                # length of array to write into
                samples,
                # number of samples which were actually read.
                daq.byref(n_read_samples),
                # Reserved for future use. Pass NULL (here None) to this parameter
                None)

            # Chops the array or read sample to the length that it exactly returns
            # acquired data and not more
            if read_available_samples:
                return _gated_count_data[0][:n_read_samples.value], n_read_samples.value
            else:
                return _gated_count_data
        except:
            self.log.exception('Error while reading gated count data.')
            return np.array([-1])

    def stop_gated_counter(self):
        """Actually start the preconfigured counter task

        @return int: error code (0:OK, -1:error)
        """
        if self._gated_counter_daq_task is None:
            self.log.error(
                'Cannot stop Gated Counter Task since it is not running!\n'
                'Start the Gated Counter Task before you can actually stop it!')
            return -1
        try:
            daq.DAQmxStopTask(self._gated_counter_daq_task)
        except:
            self.log.exception('Error while stopping gated counting.')
            return -1
        return 0

    def close_gated_counter(self):
        """ Clear tasks, so that counters are not in use any more.

        @return int: error code (0:OK, -1:error)
        """
        retval = 0
        try:
            # stop the task
            daq.DAQmxStopTask(self._gated_counter_daq_task)
        except:
            self.log.exception('Error while closing gated counter.')
            retval = -1
        try:
            # clear the task
            daq.DAQmxClearTask(self._gated_counter_daq_task)
            self._gated_counter_daq_task = None
        except:
            self.log.exception('Error while clearing gated counter.')
            retval = -1
        return retval

    def reset_hardware(self):
        """ Resets the NI hardware, so the connection is lost and other
            programs can access it.

        @return int: error code (0:OK, -1:error)
        """
        retval = 0
        chanlist = [self._counter_channel,
                    self._gate_in_channel]

        devicelist = []
        for channel in chanlist:
            if channel is None:
                continue
            match = re.match(
                '^/(?P<dev>[0-9A-Za-z\- ]+[0-9A-Za-z\-_ ]*)/(?P<chan>[0-9A-Za-z]+)',
                channel)
            if match:
                devicelist.append(match.group('dev'))
            else:
                self.log.error('Did not find device name in {0}.'.format(channel))
        for device in set(devicelist):
            self.log.info('Reset device {0}.'.format(device))
            try:
                daq.DAQmxResetDevice(device)
            except:
                self.log.exception('Could not reset NI device {0}'.format(device))
                retval = -1
        return retval