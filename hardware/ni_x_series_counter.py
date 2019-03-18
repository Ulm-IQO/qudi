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


class NationalInstrumentsXSeriesCounter(Base, SlowCounterInterface):
    """ A National Instruments device that can count and control microvave generators.

    !!!!!! NI USB 63XX, NI PCIe 63XX and NI PXIe 63XX DEVICES ONLY !!!!!!

    See [National Instruments X Series Documentation](@ref nidaq-x-series) for details.

    Example config for copy-paste:

    nicard_6343:
        module.Class: 'ni_x_series_counter.NationalInstrumentsXSeriesCounter'
        photon_sources:
            - '/Dev1/PFI8'
        #    - '/Dev1/PFI9'
        clock_channel: '/Dev1/Ctr0'
        default_clock_frequency: 100 # optional, in Hz
        counter_channels:
            - '/Dev1/Ctr1'
        counter_ai_channels:
            - '/Dev1/AI0'
        max_counts: 3e7
        read_write_timeout: 10

    """

    _modtype = 'NICard'
    _modclass = 'hardware'

    # config options
    _photon_sources = ConfigOption('photon_sources', missing='error')

    # slow counter
    _clock_channel = ConfigOption('clock_channel', missing='error')
    _default_clock_frequency = ConfigOption('default_clock_frequency', 100, missing='info')
    _counter_channels = ConfigOption('counter_channels', missing='error')
    _counter_ai_channels = ConfigOption('counter_ai_channels', [], missing='info')

    _max_counts = ConfigOption('max_counts', default=3e7)
    # timeout for the Read or/and write process in s
    _RWTimeout = ConfigOption('read_write_timeout', default=10)

    def on_activate(self):
        """ Starts up the NI Card at activation.
        """
        # the tasks used on that hardware device:
        self._counter_daq_tasks = []
        self._counter_analog_daq_task = None
        self._clock_daq_task = None

    def on_deactivate(self):
        """ Shut down the NI card.
        """
        self.close_counter()
        self.close_clock()

    # =================== SlowCounterInterface Commands ========================

    def get_constraints(self):
        """ Get hardware limits of NI device.

        @return SlowCounterConstraints: constraints class for slow counter

        FIXME: ask hardware for limits when module is loaded
        """
        constraints = SlowCounterConstraints()
        constraints.max_detectors = 4
        constraints.min_count_frequency = 1e-3
        constraints.max_count_frequency = 10e9
        constraints.counting_mode = [CountingMode.CONTINUOUS]
        return constraints

    def set_up_clock(self, clock_frequency=None, clock_channel=None, idle=False):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of
                                      the clock in Hz
        @param string clock_channel: if defined, this is the physical channel
                                     of the clock within the NI card.
        @param bool idle: set whether idle situation of the counter (where
                          counter is doing nothing) is defined as
                                True  = 'Voltage High/Rising Edge'
                                False = 'Voltage Low/Falling Edge'

        @return int: error code (0:OK, -1:error)
        """

        if self._clock_daq_task is not None:
            self.log.error('Another counter clock is already running, close this one first.')
            return -1

        # Create handle for task, this task will generate pulse signal for
        # photon counting
        my_clock_daq_task = daq.TaskHandle()

        # assign the clock frequency, if given
        self._clock_frequency = float(clock_frequency) if clock_frequency is not None else self._default_clock_frequency

        # assign the clock channel, if given
        if clock_channel is not None:
            self._clock_channel = clock_channel

        # Adjust the idle state if necessary
        my_idle = daq.DAQmx_Val_High if idle else daq.DAQmx_Val_Low

        try:
            # create task for clock
            task_name = 'CounterClock'
            daq.DAQmxCreateTask(task_name, daq.byref(my_clock_daq_task))

            # create a digital clock channel with specific clock frequency:
            daq.DAQmxCreateCOPulseChanFreq(
                # The task to which to add the channels
                my_clock_daq_task,
                # which channel is used?
                self._clock_channel,
                # Name to assign to task (NIDAQ uses by default the physical channel name as
                # the virtual channel name. If name is specified, then you must use the name
                # when you refer to that channel in other NIDAQ functions)
                'Clock Producer',
                # units, Hertz in our case
                daq.DAQmx_Val_Hz,
                # idle state
                my_idle,
                # initial delay
                0,
                # pulse frequency
                self._clock_frequency,
                # duty cycle of pulses, 0.5 such that high and low duration are both
                # equal to count_interval
                0.5)

            # Configure Implicit Timing.
            # Set timing to continuous, i.e. set only the number of samples to
            # acquire or generate without specifying timing:
            daq.DAQmxCfgImplicitTiming(
                # Define task
                my_clock_daq_task,
                # Sample Mode: set the task to generate a continuous amount of running samples
                daq.DAQmx_Val_ContSamps,
                # buffer length which stores temporarily the number of generated samples
                1000)

            # actually start the preconfigured clock task
            self._clock_daq_task = my_clock_daq_task
            daq.DAQmxStartTask(self._clock_daq_task)
        except:
            self.log.exception('Error while setting up clock.')
            return -1
        return 0

    def set_up_counter(self,
                       counter_channels=None,
                       sources=None,
                       clock_channel=None,
                       counter_buffer=None):
        """ Configures the actual counter with a given clock.

        @param list(str) counter_channels: optional, physical channel of the counter
        @param list(str) sources: optional, physical channel where the photons
                                  are to count from
        @param str clock_channel: optional, specifies the clock channel for the
                                  counter
        @param int counter_buffer: optional, a buffer of specified integer
                                   length, where in each bin the count numbers
                                   are saved.

        @return int: error code (0:OK, -1:error)
        """

        if self._clock_daq_task is None and clock_channel is None:
            self.log.error('No clock running, call set_up_clock before starting the counter.')
            return -1

        if len(self._counter_daq_tasks) > 0:
            self.log.error('Another counter is already running, close this one first.')
            return -1

        counter_channels = counter_channels if counter_channels is not None else self._counter_channels
        sources = sources if sources is not None else self._photon_sources
        clock_channel = clock_channel if clock_channel is not None else self._clock_channel

        if len(sources) < len(counter_channels):
            self.log.error('You have given {0} sources but {1} counting channels.'
                           'Please give an equal or greater number of sources.'
                           ''.format(len(sources), len(counter_channels)))
            return -1

        try:
            for i, ch in enumerate(counter_channels):
                # This task will count photons with binning defined by the clock_channel
                task = daq.TaskHandle()  # Initialize a Task
                # Create task for the counter
                daq.DAQmxCreateTask('Counter{0}'.format(i), daq.byref(task))
                # Create a Counter Input which samples with Semi-Periodes the Channel.
                # set up semi period width measurement in photon ticks, i.e. the width
                # of each pulse (high and low) generated by pulse_out_task is measured
                # in photon ticks.
                #   (this task creates a channel to measure the time between state
                #    transitions of a digital signal and adds the channel to the task
                #    you choose)
                daq.DAQmxCreateCISemiPeriodChan(
                    # define to which task to connect this function
                    task,
                    # use this counter channel
                    ch,
                    # name to assign to it
                    'Counter Channel {0}'.format(i),
                    # expected minimum count value
                    0,
                    # Expected maximum count value
                    self._max_counts / 2 / self._clock_frequency,
                    # units of width measurement, here photon ticks
                    daq.DAQmx_Val_Ticks,
                    # empty extra argument
                    '')

                # Set the Counter Input to a Semi Period input Terminal.
                # Connect the pulses from the counter clock to the counter channel
                daq.DAQmxSetCISemiPeriodTerm(
                        # The task to which to add the counter channel.
                        task,
                        # use this counter channel
                        ch,
                        # assign a named Terminal
                        clock_channel + 'InternalOutput')

                # Set a Counter Input Control Timebase Source.
                # Specify the terminal of the timebase which is used for the counter:
                # Define the source of ticks for the counter as self._photon_source for
                # the Counter Task.
                daq.DAQmxSetCICtrTimebaseSrc(
                    # define to which task to connect this function
                    task,
                    # counter channel
                    ch,
                    # counter channel to output the counting results
                    sources[i])

                # Configure Implicit Timing.
                # Set timing to continuous, i.e. set only the number of samples to
                # acquire or generate without specifying timing:
                daq.DAQmxCfgImplicitTiming(
                    # define to which task to connect this function
                    task,
                    # Sample Mode: Acquire or generate samples until you stop the task.
                    daq.DAQmx_Val_ContSamps,
                    # buffer length which stores  temporarily the number of generated samples
                    1000)

                # Set the Read point Relative To an operation.
                # Specifies the point in the buffer at which to begin a read operation.
                # Here we read most recent recorded samples:
                daq.DAQmxSetReadRelativeTo(
                    # define to which task to connect this function
                    task,
                    # Start reading samples relative to the last sample returned by the previously.
                    daq.DAQmx_Val_CurrReadPos)

                # Set the Read Offset.
                # Specifies an offset in samples per channel at which to begin a read
                # operation. This offset is relative to the location you specify with
                # RelativeTo. Here we set the Offset to 0 for multiple samples:
                daq.DAQmxSetReadOffset(task, 0)

                # Set Read OverWrite Mode.
                # Specifies whether to overwrite samples in the buffer that you have
                # not yet read. Unread data in buffer will be overwritten:
                daq.DAQmxSetReadOverWrite(
                    task,
                    daq.DAQmx_Val_DoNotOverwriteUnreadSamps)
                # add task to counter task list
                self._counter_daq_tasks.append(task)

                # Counter analog input task
                if len(self._counter_ai_channels) > 0:
                    atask = daq.TaskHandle()

                    daq.DAQmxCreateTask('CounterAnalogIn', daq.byref(atask))

                    daq.DAQmxCreateAIVoltageChan(
                        atask,
                        ', '.join(self._counter_ai_channels),
                        'Counter Analog In',
                        daq.DAQmx_Val_RSE,
                        -10,
                        10,
                        daq.DAQmx_Val_Volts,
                        ''
                    )
                    # Analog in channel timebase
                    daq.DAQmxCfgSampClkTiming(
                        atask,
                        clock_channel + 'InternalOutput',
                        self._clock_frequency,
                        daq.DAQmx_Val_Rising,
                        daq.DAQmx_Val_ContSamps,
                        int(self._clock_frequency * 5)
                    )
                    self._counter_analog_daq_task = atask
        except:
            self.log.exception('Error while setting up counting task.')
            return -1

        try:
            for i, task in enumerate(self._counter_daq_tasks):
                # Actually start the preconfigured counter task
                daq.DAQmxStartTask(task)
            if len(self._counter_ai_channels) > 0:
                daq.DAQmxStartTask(self._counter_analog_daq_task)
        except:
            self.log.exception('Error while starting Counter')
            try:
                self.close_counter()
            except:
                self.log.exception('Could not close counter after error')
            return -1
        return 0

    def get_counter_channels(self):
        """ Returns the list of counter channel names.

        @return tuple(str): channel names

        Most methods calling this might just care about the number of channels, though.
        """
        return set(self._counter_channels).union(set(self._counter_ai_channels))

    def get_counter(self, samples=None):
        """ Returns the current counts per second of the counter.

        @param int samples: if defined, number of samples to read in one go.
                            How many samples are read per readout cycle. The
                            readout frequency was defined in the counter setup.
                            That sets also the length of the readout array.

        @return float [samples]: array with entries as photon counts per second
        """
        if len(self._counter_daq_tasks) < 1:
            self.log.error(
                'No counter running, call set_up_counter before reading it.')
            # in case of error return a lot of -1
            return np.ones((len(self.get_counter_channels()), samples), dtype=np.uint32) * -1

        if len(self._counter_ai_channels) > 0 and self._counter_analog_daq_task is None:
            self.log.error(
                'No counter analog input task running, call set_up_counter before reading it.')
            # in case of error return a lot of -1
            return np.ones((len(self.get_counter_channels()), samples), dtype=np.uint32) * -1

        samples = int(samples) if samples is not None else int(self._samples_number)
        try:
            # count data will be written here in the NumPy array of length samples
            count_data = np.empty((len(self._counter_daq_tasks), 2 * samples), dtype=np.uint32)

            # number of samples which were actually read, will be stored here
            n_read_samples = daq.int32()
            for i, task in enumerate(self._counter_daq_tasks):
                # read the counter value: This function is blocking and waits for the
                # counts to be all filled:
                daq.DAQmxReadCounterU32(
                    # read from this task
                    task,
                    # number of samples to read
                    2 * samples,
                    # maximal timeout for the read process
                    self._RWTimeout,
                    # write the readout into this array
                    count_data[i],
                    # length of array to write into
                    2 * samples,
                    # number of samples which were read
                    daq.byref(n_read_samples),
                    # Reserved for future use. Pass NULL (here None) to this parameter
                    None)

            # Analog channels
            if len(self._counter_ai_channels) > 0:
                analog_data = np.full(
                    (len(self._counter_ai_channels), samples), 111, dtype=np.float64)

                analog_read_samples = daq.int32()

                daq.DAQmxReadAnalogF64(
                    self._counter_analog_daq_task,
                    samples,
                    self._RWTimeout,
                    daq.DAQmx_Val_GroupByChannel,
                    analog_data,
                    len(self._counter_ai_channels) * samples,
                    daq.byref(analog_read_samples),
                    None
                )
        except:
            self.log.exception(
                'Getting samples from counter failed.')
            # in case of error return a lot of -1
            return np.ones((len(self.get_counter_channels()), samples), dtype=np.uint32) * -1

        # add up adjoined pixels to also get the counts from the low time of
        # the clock:
        real_data = count_data[:, ::2]
        real_data += count_data[:, 1::2]

        all_data = np.full((len(self.get_counter_channels()), samples), 222, dtype=np.float64)
        # normalize to counts per second for counter channels
        all_data[0:len(real_data)] = np.array(real_data * self._clock_frequency, np.float64)

        if len(self._counter_ai_channels) > 0:
            all_data[-len(self._counter_ai_channels):] = analog_data

        return all_data

    def close_counter(self):
        """ Closes the counter and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        error = 0
        for i, task in enumerate(self._counter_daq_tasks):
            try:
                # stop the counter task
                daq.DAQmxStopTask(task)
                # after stopping delete all the configuration of the counter
                daq.DAQmxClearTask(task)
                # set the task handle to None as a safety
            except:
                self.log.exception('Could not close counter.')
                error = -1
        self._counter_daq_tasks = []

        if len(self._counter_ai_channels) > 0 and self._counter_analog_daq_task is not None:
            try:
                # stop the counter task
                daq.DAQmxStopTask(self._counter_analog_daq_task)
                # after stopping delete all the configuration of the counter
                daq.DAQmxClearTask(self._counter_analog_daq_task)
                # set the task handle to None as a safety
            except:
                self.log.exception('Could not close counter analog channels.')
                error = -1
            self._counter_analog_daq_task = None
        return error

    def close_clock(self):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        if self._clock_daq_task is not None:
            try:
                # Stop the clock task:
                daq.DAQmxStopTask(self._clock_daq_task)

                # After stopping delete all the configuration of the clock:
                daq.DAQmxClearTask(self._clock_daq_task)

                # Set the task handle to None as a safety
                self._clock_daq_task = None
            except:
                self.log.exception('Could not close clock.')
                return -1
        return 0

    # ================ End SlowCounterInterface Commands =======================

    def reset_hardware(self):
        """ Resets the NI hardware, so the connection is lost and other
            programs can access it.

        @return int: error code (0:OK, -1:error)
        """
        retval = 0
        chanlist = [self._clock_channel]
        chanlist.extend(self._counter_channels)
        chanlist.extend(self._counter_ai_channels)

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
