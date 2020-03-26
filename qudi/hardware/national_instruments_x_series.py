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

from core.module import Base
from core.configoption import ConfigOption
from interface.slow_counter_interface import SlowCounterInterface
from interface.slow_counter_interface import SlowCounterConstraints
from interface.slow_counter_interface import CountingMode
from interface.odmr_counter_interface import ODMRCounterInterface
from interface.confocal_scanner_interface import ConfocalScannerInterface


class NationalInstrumentsXSeries(Base, SlowCounterInterface, ConfocalScannerInterface, ODMRCounterInterface):
    """ A National Instruments device that can count and control microvave generators.

    !!!!!! NI USB 63XX, NI PCIe 63XX and NI PXIe 63XX DEVICES ONLY !!!!!!

    See [National Instruments X Series Documentation](@ref nidaq-x-series) for details.

    stable: Kay Jahnke, Alexander Stark

    Example config for copy-paste:

    nicard_6343:
        module.Class: 'national_instruments_x_series.NationalInstrumentsXSeries'
        photon_sources:
            - '/Dev1/PFI8'
        #    - '/Dev1/PFI9'
        clock_channel: '/Dev1/Ctr0'
        default_clock_frequency: 100 # optional, in Hz
        counter_channels:
            - '/Dev1/Ctr1'
        counter_ai_channels:
            - '/Dev1/AI0'
        counter_voltage_range: [-10, 10]
        default_scanner_clock_frequency: 100 # optional, in Hz
        scanner_clock_channel: '/Dev1/Ctr2'
        pixel_clock_channel: '/Dev1/PFI6'
        scanner_ao_channels:
            - '/Dev1/AO0'
            - '/Dev1/AO1'
            - '/Dev1/AO2'
            - '/Dev1/AO3'
        scanner_ai_channels:
            - '/Dev1/AI1'
        scanner_counter_channels:
            - '/Dev1/Ctr3'
        scanner_voltage_ranges:
            - [-10, 10]
            - [-10, 10]
            - [-10, 10]
            - [-10, 10]
        scanner_position_ranges:
            - [0e-6, 200e-6]
            - [0e-6, 200e-6]
            - [-100e-6, 100e-6]
            - [-10, 10]

        odmr_trigger_channel: '/Dev1/PFI7'

        gate_in_channel: '/Dev1/PFI9'
        default_samples_number: 50
        max_counts: 3e7
        read_write_timeout: 10
        counting_edge_rising: True

    """

    # config options
    _photon_sources = ConfigOption('photon_sources', list(), missing='warn')

    # slow counter
    _clock_channel = ConfigOption('clock_channel', missing='error')
    _default_clock_frequency = ConfigOption('default_clock_frequency', 100, missing='info')
    _counter_channels = ConfigOption('counter_channels', missing='error')
    _counter_ai_channels = ConfigOption('counter_ai_channels', list(), missing='info')
    _counter_voltage_range = ConfigOption('counter_voltage_range', [-10, 10], missing='info')

    # confocal scanner
    _default_scanner_clock_frequency = ConfigOption('default_scanner_clock_frequency', 100, missing='info')
    _scanner_clock_channel = ConfigOption('scanner_clock_channel', missing='warn')
    _pixel_clock_channel = ConfigOption('pixel_clock_channel', None)
    _scanner_ao_channels = ConfigOption('scanner_ao_channels', missing='error')
    _scanner_ai_channels = ConfigOption('scanner_ai_channels', list(), missing='info')
    _scanner_counter_channels = ConfigOption('scanner_counter_channels', list(), missing='warn')
    _scanner_voltage_ranges = ConfigOption('scanner_voltage_ranges', missing='error')
    _scanner_position_ranges = ConfigOption('scanner_position_ranges', missing='error')

    # odmr
    _odmr_trigger_channel = ConfigOption('odmr_trigger_channel', missing='error')
    _odmr_trigger_line = ConfigOption('odmr_trigger_line', 'Dev1/port0/line0', missing='warn')
    _odmr_switch_line = ConfigOption('odmr_switch_line', 'Dev1/port0/line1', missing='warn')

    _gate_in_channel = ConfigOption('gate_in_channel', missing='error')
    # number of readout samples, mainly used for gated counter
    _default_samples_number = ConfigOption('default_samples_number', 50, missing='info')
    # used as a default for expected maximum counts
    _max_counts = ConfigOption('max_counts', default=3e7)
    # timeout for the Read or/and write process in s
    _RWTimeout = ConfigOption('read_write_timeout', default=10)
    _counting_edge_rising = ConfigOption('counting_edge_rising', default=True)

    def on_activate(self):
        """ Starts up the NI Card at activation.
        """
        # the tasks used on that hardware device:
        self._counter_daq_tasks = list()
        self._counter_analog_daq_task = None
        self._clock_daq_task = None
        self._scanner_clock_daq_task = None
        self._scanner_ao_task = None
        self._scanner_counter_daq_tasks = list()
        self._line_length = None
        self._odmr_length = None
        self._gated_counter_daq_task = None
        self._scanner_analog_daq_task = None
        self._odmr_pulser_daq_task = None
        self._oversampling = 0
        self._lock_in_active = False

        self._photon_sources = self._photon_sources if self._photon_sources is not None else list()
        self._scanner_counter_channels = self._scanner_counter_channels if self._scanner_counter_channels is not None else list()
        self._scanner_ai_channels = self._scanner_ai_channels if self._scanner_ai_channels is not None else list()

        # handle all the parameters given by the config
        self._current_position = np.zeros(len(self._scanner_ao_channels))

        if len(self._scanner_ao_channels) < len(self._scanner_voltage_ranges):
            self.log.error(
                'Specify at least as many scanner_voltage_ranges as scanner_ao_channels!')

        if len(self._scanner_ao_channels) < len(self._scanner_position_ranges):
            self.log.error(
                'Specify at least as many scanner_position_ranges as scanner_ao_channels!')

        if len(self._scanner_counter_channels) + len(self._scanner_ai_channels) < 1:
            self.log.error(
                'Specify at least one counter or analog input channel for the scanner!')

        # Analog output is always needed and it does not interfere with the
        # rest, so start it always and leave it running
        if self._start_analog_output() < 0:
            self.log.error('Failed to start analog output.')
            raise Exception('Failed to start NI Card module due to analog output failure.')

    def on_deactivate(self):
        """ Shut down the NI card.
        """
        self._stop_analog_output()
        # clear the task
        try:
            daq.DAQmxClearTask(self._scanner_ao_task)
            self._scanner_ao_task = None
        except:
            self.log.exception('Could not clear AO Out Task.')

        self.reset_hardware()

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

    def set_up_clock(self, clock_frequency=None, clock_channel=None, scanner=False, idle=False):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of
                                      the clock in Hz
        @param string clock_channel: if defined, this is the physical channel
                                     of the clock within the NI card.
        @param bool scanner: if set to True method will set up a clock function
                             for the scanner, otherwise a clock function for a
                             counter will be set.
        @param bool idle: set whether idle situation of the counter (where
                          counter is doing nothing) is defined as
                                True  = 'Voltage High/Rising Edge'
                                False = 'Voltage Low/Falling Edge'

        @return int: error code (0:OK, -1:error)
        """

        if not scanner and self._clock_daq_task is not None:
            self.log.error('Another counter clock is already running, close this one first.')
            return -1

        if scanner and self._scanner_clock_daq_task is not None:
            self.log.error('Another scanner clock is already running, close this one first.')
            return -1

        # Create handle for task, this task will generate pulse signal for
        # photon counting
        my_clock_daq_task = daq.TaskHandle()

        # assign the clock frequency, if given
        if clock_frequency is not None:
            if not scanner:
                self._clock_frequency = float(clock_frequency)
            else:
                self._scanner_clock_frequency = float(clock_frequency)
        else:
            if not scanner:
                self._clock_frequency = self._default_clock_frequency
            else:
                self._scanner_clock_frequency = self._default_scanner_clock_frequency

        # use the correct clock in this method
        if scanner:
            my_clock_frequency = self._scanner_clock_frequency * 2
        else:
            my_clock_frequency = self._clock_frequency * 2

        # assign the clock channel, if given
        if clock_channel is not None:
            if not scanner:
                self._clock_channel = clock_channel
            else:
                self._scanner_clock_channel = clock_channel

        # use the correct clock channel in this method
        if scanner:
            my_clock_channel = self._scanner_clock_channel
        else:
            my_clock_channel = self._clock_channel

        # check whether only one clock pair is available, since some NI cards
        # only one clock channel pair.
        if self._scanner_clock_channel == self._clock_channel:
            if not ((self._clock_daq_task is None) and (self._scanner_clock_daq_task is None)):
                self.log.error(
                    'Only one clock channel is available!\n'
                    'Another clock is already running, close this one first '
                    'in order to use it for your purpose!')
                return -1

        # Adjust the idle state if necessary
        my_idle = daq.DAQmx_Val_High if idle else daq.DAQmx_Val_Low
        try:
            # create task for clock
            task_name = 'ScannerClock' if scanner else 'CounterClock'
            daq.DAQmxCreateTask(task_name, daq.byref(my_clock_daq_task))

            # create a digital clock channel with specific clock frequency:
            daq.DAQmxCreateCOPulseChanFreq(
                # The task to which to add the channels
                my_clock_daq_task,
                # which channel is used?
                my_clock_channel,
                # Name to assign to task (NIDAQ uses by # default the physical channel name as
                # the virtual channel name. If name is specified, then you must use the name
                # when you refer to that channel in other NIDAQ functions)
                'Clock Producer',
                # units, Hertz in our case
                daq.DAQmx_Val_Hz,
                # idle state
                my_idle,
                # initial delay
                0,
                # pulse frequency, divide by 2 such that length of semi period = count_interval
                my_clock_frequency / 2,
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

            if scanner:
                self._scanner_clock_daq_task = my_clock_daq_task
            else:
                # actually start the preconfigured clock task
                daq.DAQmxStartTask(my_clock_daq_task)
                self._clock_daq_task = my_clock_daq_task
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

        my_counter_channels = counter_channels if counter_channels else self._counter_channels
        my_photon_sources = sources if sources else self._photon_sources
        my_clock_channel = clock_channel if clock_channel else self._clock_channel

        if len(my_photon_sources) < len(my_counter_channels):
            self.log.error('You have given {0} sources but {1} counting channels.'
                           'Please give an equal or greater number of sources.'
                           ''.format(len(my_photon_sources), len(my_counter_channels)))
            return -1

        try:
            for i, ch in enumerate(my_counter_channels):
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
                        my_clock_channel + 'InternalOutput')

                # Set a Counter Input Control Timebase Source.
                # Specify the terminal of the timebase which is used for the counter:
                # Define the source of ticks for the counter as self._photon_source for
                # the Scanner Task.
                daq.DAQmxSetCICtrTimebaseSrc(
                    # define to which task to connect this function
                    task,
                    # counter channel
                    ch,
                    # counter channel to output the counting results
                    my_photon_sources[i])

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
                        self._counter_voltage_range[0],
                        self._counter_voltage_range[1],
                        daq.DAQmx_Val_Volts,
                        ''
                    )
                    # Analog in channel timebase
                    daq.DAQmxCfgSampClkTiming(
                        atask,
                        my_clock_channel + 'InternalOutput',
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
        ch = self._counter_channels[:]
        ch.extend(self._counter_ai_channels)
        return ch

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

        if samples is None:
            samples = int(self._samples_number)
        else:
            samples = int(samples)
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

        real_data = np.empty((len(self._counter_channels), samples), dtype=np.uint32)

        # add up adjoint pixels to also get the counts from the low time of
        # the clock:
        real_data = count_data[:, ::2]
        real_data += count_data[:, 1::2]

        all_data = np.full((len(self.get_counter_channels()), samples), 222, dtype=np.float64)
        # normalize to counts per second for counter channels
        all_data[0:len(real_data)] = np.array(real_data * self._clock_frequency, np.float64)

        if len(self._counter_ai_channels) > 0:
            all_data[-len(self._counter_ai_channels):] = analog_data

        return all_data

    def close_counter(self, scanner=False):
        """ Closes the counter or scanner and cleans up afterwards.

        @param bool scanner: specifies if the counter- or scanner- function
                             will be excecuted to close the device.
                                True = scanner
                                False = counter

        @return int: error code (0:OK, -1:error)
        """
        error = 0
        if scanner:
            for i, task in enumerate(self._scanner_counter_daq_tasks):
                try:
                    # stop the counter task
                    daq.DAQmxStopTask(task)
                    # after stopping delete all the configuration of the counter
                    daq.DAQmxClearTask(task)
                except:
                    self.log.exception('Could not close scanner counter.')
                    error = -1
            self._scanner_counter_daq_tasks = []
        else:
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

            if len(self._counter_ai_channels) > 0:
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

    def close_clock(self, scanner=False):
        """ Closes the clock and cleans up afterwards.

        @param bool scanner: specifies if the counter- or scanner- function
                             should be used to close the device.
                                True = scanner
                                False = counter

        @return int: error code (0:OK, -1:error)
        """
        if scanner:
            my_task = self._scanner_clock_daq_task
        else:
            my_task = self._clock_daq_task
        try:
            # Stop the clock task:
            daq.DAQmxStopTask(my_task)

            # After stopping delete all the configuration of the clock:
            daq.DAQmxClearTask(my_task)

            # Set the task handle to None as a safety
            if scanner:
                self._scanner_clock_daq_task = None
            else:
                self._clock_daq_task = None
        except:
            self.log.exception('Could not close clock.')
            return -1
        return 0

    # ================ End SlowCounterInterface Commands =======================

    # ================ ConfocalScannerInterface Commands =======================
    def reset_hardware(self):
        """ Resets the NI hardware, so the connection is lost and other
            programs can access it.

        @return int: error code (0:OK, -1:error)
        """
        retval = 0
        chanlist = [
            self._odmr_trigger_channel,
            self._clock_channel,
            self._scanner_clock_channel,
            self._gate_in_channel
            ]
        chanlist.extend(self._scanner_ao_channels)
        chanlist.extend(self._photon_sources)
        chanlist.extend(self._counter_channels)
        chanlist.extend(self._scanner_counter_channels)

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

    def get_scanner_axes(self):
        """ Scanner axes depends on how many channels tha analog output task has.
        """
        if self._scanner_ao_task is None:
            self.log.error('Cannot get channel number, analog output task does not exist.')
            return []

        n_channels = daq.uInt32()
        daq.DAQmxGetTaskNumChans(self._scanner_ao_task, n_channels)
        possible_channels = ['x', 'y', 'z', 'a']

        return possible_channels[0:int(n_channels.value)]

    def get_scanner_count_channels(self):
        """ Return list of counter channels """
        ch = self._scanner_counter_channels[:]
        ch.extend(self._scanner_ai_channels)
        return ch

    def get_position_range(self):
        """ Returns the physical range of the scanner.

        @return float [4][2]: array of 4 ranges with an array containing lower
                              and upper limit. The unit of the scan range is
                              meters.
        """
        return self._scanner_position_ranges

    def set_position_range(self, myrange=None):
        """ Sets the physical range of the scanner.

        @param float [4][2] myrange: array of 4 ranges with an array containing
                                     lower and upper limit. The unit of the
                                     scan range is meters.

        @return int: error code (0:OK, -1:error)
        """
        if myrange is None:
            myrange = [[0, 1e-6], [0, 1e-6], [0, 1e-6], [0, 1e-6]]

        if not isinstance(myrange, (frozenset, list, set, tuple, np.ndarray, )):
            self.log.error('Given range is no array type.')
            return -1

        if len(myrange) != 4:
            self.log.error(
                'Given range should have dimension 4, but has {0:d} instead.'
                ''.format(len(myrange)))
            return -1

        for pos in myrange:
            if len(pos) != 2:
                self.log.error(
                    'Given range limit {1:d} should have dimension 2, but has {0:d} instead.'
                    ''.format(len(pos), pos))
                return -1
            if pos[0]>pos[1]:
                self.log.error(
                    'Given range limit {0:d} has the wrong order.'.format(pos))
                return -1

        self._scanner_position_ranges = myrange
        return 0

    def set_voltage_range(self, myrange=None):
        """ Sets the voltage range of the NI Card.

        @param float [n][2] myrange: array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        n_ch = len(self.get_scanner_axes())
        if myrange is None:
            myrange = [[-10., 10.], [-10., 10.], [-10., 10.], [-10., 10.]][0:n_ch]

        if not isinstance(myrange, (frozenset, list, set, tuple, np.ndarray)):
            self.log.error('Given range is no array type.')
            return -1

        if len(myrange) != n_ch:
            self.log.error(
                'Given range should have dimension 2, but has {0:d} instead.'
                ''.format(len(myrange)))
            return -1

        for r in myrange:
            if r[0] > r[1]:
                self.log.error('Given range limit {0:d} has the wrong order.'.format(r))
                return -1

        self._scanner_voltage_ranges = myrange
        return 0

    def _start_analog_output(self):
        """ Starts or restarts the analog output.

        @return int: error code (0:OK, -1:error)
        """
        try:
            # If an analog task is already running, kill that one first
            if self._scanner_ao_task is not None:
                # stop the analog output task
                daq.DAQmxStopTask(self._scanner_ao_task)

                # delete the configuration of the analog output
                daq.DAQmxClearTask(self._scanner_ao_task)

                # set the task handle to None as a safety
                self._scanner_ao_task = None

            # initialize ao channels / task for scanner, should always be active.
            # Define at first the type of the variable as a Task:
            self._scanner_ao_task = daq.TaskHandle()

            # create the actual analog output task on the hardware device. Via
            # byref you pass the pointer of the object to the TaskCreation function:
            daq.DAQmxCreateTask('ScannerAO', daq.byref(self._scanner_ao_task))
            for n, chan in enumerate(self._scanner_ao_channels):
                # Assign and configure the created task to an analog output voltage channel.
                daq.DAQmxCreateAOVoltageChan(
                    # The AO voltage operation function is assigned to this task.
                    self._scanner_ao_task,
                    # use (all) scanner ao_channels for the output
                    chan,
                    # assign a name for that channel
                    'Scanner AO Channel {0}'.format(n),
                    # minimum possible voltage
                    self._scanner_voltage_ranges[n][0],
                    # maximum possible voltage
                    self._scanner_voltage_ranges[n][1],
                    # units is Volt
                    daq.DAQmx_Val_Volts,
                    # empty for future use
                    '')
        except:
            self.log.exception('Error starting analog output task.')
            return -1
        return 0

    def _stop_analog_output(self):
        """ Stops the analog output.

        @return int: error code (0:OK, -1:error)
        """
        if self._scanner_ao_task is None:
            return -1
        retval = 0
        try:
            # stop the analog output task
            daq.DAQmxStopTask(self._scanner_ao_task)
        except:
            self.log.exception('Error stopping analog output.')
            retval = -1
        try:
            daq.DAQmxSetSampTimingType(self._scanner_ao_task, daq.DAQmx_Val_OnDemand)
        except:
            self.log.exception('Error changing analog output mode.')
            retval = -1
        return retval

    def set_up_scanner_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of
                                      the clock
        @param string clock_channel: if defined, this is the physical channel
                                     of the clock

        @return int: error code (0:OK, -1:error)
        """
        # The clock for the scanner is created on the same principle as it is
        # for the counter. Just to keep consistency, this function is a wrapper
        # around the set_up_clock.
        return self.set_up_clock(
            clock_frequency=clock_frequency,
            clock_channel=clock_channel,
            scanner=True)

    def set_up_scanner(self,
                       counter_channels=None,
                       sources=None,
                       clock_channel=None,
                       scanner_ao_channels=None):
        """ Configures the actual scanner with a given clock.

        The scanner works pretty much like the counter. Here you connect a
        created clock with a counting task. That can be seen as a gated
        counting, where the counts where sampled by the underlying clock.

        @param list(str) counter_channels: this is the physical channel of the counter
        @param list(str) sources:  this is the physical channel where the photons are to count from
        @param string clock_channel: optional, if defined, this specifies the clock for the counter
        @param list(str) scanner_ao_channels: optional, if defined, this specifies
                                           the analog output channels

        @return int: error code (0:OK, -1:error)
        """
        retval = 0
        if self._scanner_clock_daq_task is None and clock_channel is None:
            self.log.error('No clock running, call set_up_clock before starting the counter.')
            return -1

        my_counter_channels = counter_channels if counter_channels else self._scanner_counter_channels
        my_photon_sources = sources if sources else self._photon_sources
        self._my_scanner_clock_channel = clock_channel if clock_channel else self._scanner_clock_channel

        if scanner_ao_channels is not None:
            self._scanner_ao_channels = scanner_ao_channels
            retval = self._start_analog_output()

        if len(my_photon_sources) < len(my_counter_channels):
            self.log.error('You have given {0} sources but {1} counting channels.'
                           'Please give an equal or greater number of sources.'
                           ''.format(len(my_photon_sources), len(my_counter_channels)))
            return -1

        try:
            # Set the Sample Timing Type. Task timing to use a sampling clock:
            # specify how the Data of the selected task is collected, i.e. set it
            # now to be sampled on demand for the analog output, i.e. when
            # demanded by software.
            daq.DAQmxSetSampTimingType(self._scanner_ao_task, daq.DAQmx_Val_OnDemand)

            for i, ch in enumerate(my_counter_channels):
                # create handle for task, this task will do the photon counting for the
                # scanner.
                task = daq.TaskHandle()

                # actually create the scanner counting task
                daq.DAQmxCreateTask('ScannerCounter{0}'.format(i), daq.byref(task))

                # Create a Counter Input which samples with Semi Perides the Channel.
                # set up semi period width measurement in photon ticks, i.e. the width
                # of each pulse (high and low) generated by pulse_out_task is measured
                # in photon ticks.
                #   (this task creates a channel to measure the time between state
                #    transitions of a digital signal and adds the channel to the task
                #    you choose)
                daq.DAQmxCreateCISemiPeriodChan(
                    # The task to which to add the channels
                    task,
                    # use this counter channel
                    ch,
                    # name to assign to it
                    'Scanner Counter Channel {0}'.format(i),
                    # expected minimum value
                    0,
                    # Expected maximum count value
                    self._max_counts / self._scanner_clock_frequency,
                    # units of width measurement, here Timebase photon ticks
                    daq.DAQmx_Val_Ticks,
                    '')

                # Set the Counter Input to a Semi Period input Terminal.
                # Connect the pulses from the scanner clock to the scanner counter
                daq.DAQmxSetCISemiPeriodTerm(
                    # The task to which to add the counter channel.
                    task,
                    # use this counter channel
                    ch,
                    # assign a Terminal Name
                    self._my_scanner_clock_channel + 'InternalOutput')

                # Set a CounterInput Control Timebase Source.
                # Specify the terminal of the timebase which is used for the counter:
                # Define the source of ticks for the counter as self._photon_source for
                # the Scanner Task.
                daq.DAQmxSetCICtrTimebaseSrc(
                    # define to which task to# connect this function
                    task,
                    # counter channel to output the# counting results
                    ch,
                    # which channel to count
                    my_photon_sources[i])
                self._scanner_counter_daq_tasks.append(task)

            # Scanner analog input task
            if self._scanner_ai_channels:
                atask = daq.TaskHandle()

                daq.DAQmxCreateTask('ScanAnalogIn', daq.byref(atask))

                daq.DAQmxCreateAIVoltageChan(
                    atask,
                    ', '.join(self._scanner_ai_channels),
                    'Scan Analog In',
                    daq.DAQmx_Val_RSE,
                    self._counter_voltage_range[0],
                    self._counter_voltage_range[1],
                    daq.DAQmx_Val_Volts,
                    ''
                )
                self._scanner_analog_daq_task = atask
        except:
            self.log.exception('Error while setting up scanner.')
            retval = -1

        return retval

    def scanner_set_position(self, x=None, y=None, z=None, a=None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).

        #FIXME: No volts
        @param float x: postion in x-direction (volts)
        @param float y: postion in y-direction (volts)
        @param float z: postion in z-direction (volts)
        @param float a: postion in a-direction (volts)

        @return int: error code (0:OK, -1:error)
        """

        if self.module_state() == 'locked':
            self.log.error('Another scan_line is already running, close this one first.')
            return -1

        if x is not None:
            if not(self._scanner_position_ranges[0][0] <= x <= self._scanner_position_ranges[0][1]):
                self.log.error('You want to set x out of range: {0:f}.'.format(x))
                return -1
            self._current_position[0] = np.float(x)

        if y is not None:
            if not(self._scanner_position_ranges[1][0] <= y <= self._scanner_position_ranges[1][1]):
                self.log.error('You want to set y out of range: {0:f}.'.format(y))
                return -1
            self._current_position[1] = np.float(y)

        if z is not None:
            if not(self._scanner_position_ranges[2][0] <= z <= self._scanner_position_ranges[2][1]):
                self.log.error('You want to set z out of range: {0:f}.'.format(z))
                return -1
            self._current_position[2] = np.float(z)

        if a is not None:
            if not(self._scanner_position_ranges[3][0] <= a <= self._scanner_position_ranges[3][1]):
                self.log.error('You want to set a out of range: {0:f}.'.format(a))
                return -1
            self._current_position[3] = np.float(a)

        # the position has to be a vstack
        my_position = np.vstack(self._current_position)

        # then directly write the position to the hardware
        try:
            self._write_scanner_ao(
                voltages=self._scanner_position_to_volt(my_position),
                start=True)
        except:
            return -1
        return 0

    def _write_scanner_ao(self, voltages, length=1, start=False):
        """Writes a set of voltages to the analog outputs.

        @param float[][n] voltages: array of n-part tuples defining the voltage
                                    points
        @param int length: number of tuples to write
        @param bool start: write imediately (True)
                           or wait for start of task (False)

        n depends on how many channels are configured for analog output
        """
        # Number of samples which were actually written, will be stored here.
        # The error code of this variable can be asked with .value to check
        # whether all channels have been written successfully.
        self._AONwritten = daq.int32()
        # write the voltage instructions for the analog output to the hardware
        daq.DAQmxWriteAnalogF64(
            # write to this task
            self._scanner_ao_task,
            # length of the command (points)
            length,
            # start task immediately (True), or wait for software start (False)
            start,
            # maximal timeout in seconds for# the write process
            self._RWTimeout,
            # Specify how the samples are arranged: each pixel is grouped by channel number
            daq.DAQmx_Val_GroupByChannel,
            # the voltages to be written
            voltages,
            # The actual number of samples per channel successfully written to the buffer
            daq.byref(self._AONwritten),
            # Reserved for future use. Pass NULL(here None) to this parameter
            None)
        return self._AONwritten.value

    def _scanner_position_to_volt(self, positions=None):
        """ Converts a set of position pixels to acutal voltages.

        @param float[][n] positions: array of n-part tuples defining the pixels

        @return float[][n]: array of n-part tuples of corresponing voltages

        The positions is typically a matrix like
            [[x_values], [y_values], [z_values], [a_values]]
            but x, xy, xyz and xyza are allowed formats.
        """

        if not isinstance(positions, (frozenset, list, set, tuple, np.ndarray, )):
            self.log.error('Given position list is no array type.')
            return np.array([np.NaN])

        vlist = []
        for i, position in enumerate(positions):
            vlist.append(
                (self._scanner_voltage_ranges[i][1] - self._scanner_voltage_ranges[i][0])
                / (self._scanner_position_ranges[i][1] - self._scanner_position_ranges[i][0])
                * (position - self._scanner_position_ranges[i][0])
                + self._scanner_voltage_ranges[i][0]
            )
        volts = np.vstack(vlist)

        for i, v in enumerate(volts):
            if v.min() < self._scanner_voltage_ranges[i][0] or v.max() > self._scanner_voltage_ranges[i][1]:
                self.log.error(
                    'Voltages ({0}, {1}) exceed the limit, the positions have to '
                    'be adjusted to stay in the given range.'.format(v.min(), v.max()))
                return np.array([np.NaN])
        return volts

    def get_scanner_position(self):
        """ Get the current position of the scanner hardware.

        @return float[]: current position in (x, y, z, a).
        """
        return self._current_position.tolist()

    def _set_up_line(self, length=100):
        """ Sets up the analog output for scanning a line.

        Connect the timing of the Analog scanning task with the timing of the
        counting task.

        @param int length: length of the line in pixel

        @return int: error code (0:OK, -1:error)
        """
        if self._scanner_counter_channels and len(self._scanner_counter_daq_tasks) < 1:
            self.log.error('Configured counter is not running, cannot scan a line.')
            return np.array([[-1.]])

        if self._scanner_ai_channels and self._scanner_analog_daq_task is None:
            self.log.error('Configured analog input is not running, cannot scan a line.')
            return -1

        self._line_length = length

        try:
            # Just a formal check whether length is not a too huge number
            if length < np.inf:

                # Configure the Sample Clock Timing.
                # Set up the timing of the scanner counting while the voltages are
                # being scanned (i.e. that you go through each voltage, which
                # corresponds to a position. How fast the voltages are being
                # changed is combined with obtaining the counts per voltage peak).
                daq.DAQmxCfgSampClkTiming(
                    # add to this task
                    self._scanner_ao_task,
                    # use this channel as clock
                    self._my_scanner_clock_channel + 'InternalOutput',
                    # Maximum expected clock frequency
                    self._scanner_clock_frequency,
                    # Generate sample on falling edge
                    daq.DAQmx_Val_Rising,
                    # generate finite number of samples
                    daq.DAQmx_Val_FiniteSamps,
                    # number of samples to generate
                    self._line_length)

            # Configure Implicit Timing for the clock.
            # Set timing for scanner clock task to the number of pixel.
            daq.DAQmxCfgImplicitTiming(
                # define task
                self._scanner_clock_daq_task,
                # only a limited number of# counts
                daq.DAQmx_Val_FiniteSamps,
                # count twice for each voltage +1 for safety
                self._line_length + 1)

            for i, task in enumerate(self._scanner_counter_daq_tasks):
                # Configure Implicit Timing for the scanner counting task.
                # Set timing for scanner count task to the number of pixel.
                daq.DAQmxCfgImplicitTiming(
                    # define task
                    task,
                    # only a limited number of counts
                    daq.DAQmx_Val_FiniteSamps,
                    # count twice for each voltage +1 for safety
                    2 * self._line_length + 1)

                # Set the Read point Relative To an operation.
                # Specifies the point in the buffer at which to begin a read operation,
                # here we read samples from beginning of acquisition and do not overwrite
                daq.DAQmxSetReadRelativeTo(
                    # define to which task to connect this function
                    task,
                    # Start reading samples relative to the last sample returned
                    # by the previous read
                    daq.DAQmx_Val_CurrReadPos)

                # Set the Read Offset.
                # Specifies an offset in samples per channel at which to begin a read
                # operation. This offset is relative to the location you specify with
                # RelativeTo. Here we do not read the first sample.
                daq.DAQmxSetReadOffset(
                    # connect to this task
                    task,
                    # Offset after which to read
                    1)

                # Set Read OverWrite Mode.
                # Specifies whether to overwrite samples in the buffer that you have
                # not yet read. Unread data in buffer will be overwritten:
                daq.DAQmxSetReadOverWrite(
                    task,
                    daq.DAQmx_Val_DoNotOverwriteUnreadSamps)

            # Analog channels
            if self._scanner_ai_channels:
                # Analog in channel timebase
                daq.DAQmxCfgSampClkTiming(
                    self._scanner_analog_daq_task,
                    self._scanner_clock_channel + 'InternalOutput',
                    self._scanner_clock_frequency,
                    daq.DAQmx_Val_Rising,
                    daq.DAQmx_Val_ContSamps,
                    self._line_length + 1
                )
        except:
            self.log.exception('Error while setting up scanner to scan a line.')
            return -1
        return 0

    def scan_line(self, line_path=None, pixel_clock=False):
        """ Scans a line and return the counts on that line.

        @param float[c][m] line_path: array of c-tuples defining the voltage points
            (m = samples per line)
        @param bool pixel_clock: whether we need to output a pixel clock for this line

        @return float[m][n]: m (samples per line) n-channel photon counts per second

        The input array looks for a xy scan of 5x5 points at the position z=-2
        like the following:
            [ [1, 2, 3, 4, 5], [1, 1, 1, 1, 1], [-2, -2, -2, -2] ]
        n is the number of scanner axes, which can vary. Typical values are 2 for galvo scanners,
        3 for xyz scanners and 4 for xyz scanners with a special function on the a axis.
        """
        if self._scanner_counter_channels and len(self._scanner_counter_daq_tasks) < 1:
            self.log.error('Configured counter is not running, cannot scan a line.')
            return np.array([[-1.]])

        if self._scanner_ai_channels and self._scanner_analog_daq_task is None:
            self.log.error('Configured analog input is not running, cannot scan a line.')
            return -1

        if not isinstance(line_path, (frozenset, list, set, tuple, np.ndarray, ) ):
            self.log.error('Given line_path list is not array type.')
            return np.array([[-1.]])
        try:
            # set task timing to use a sampling clock:
            # specify how the Data of the selected task is collected, i.e. set it
            # now to be sampled by a hardware (clock) signal.
            daq.DAQmxSetSampTimingType(self._scanner_ao_task, daq.DAQmx_Val_SampClk)
            self._set_up_line(np.shape(line_path)[1])
            line_volts = self._scanner_position_to_volt(line_path)
            # write the positions to the analog output
            written_voltages = self._write_scanner_ao(
                voltages=line_volts,
                length=self._line_length,
                start=False)

            # start the timed analog output task
            daq.DAQmxStartTask(self._scanner_ao_task)

            for i, task in enumerate(self._scanner_counter_daq_tasks):
                daq.DAQmxStopTask(task)

            daq.DAQmxStopTask(self._scanner_clock_daq_task)

            if pixel_clock and self._pixel_clock_channel is not None:
                daq.DAQmxConnectTerms(
                    self._scanner_clock_channel + 'InternalOutput',
                    self._pixel_clock_channel,
                    daq.DAQmx_Val_DoNotInvertPolarity)

            # start the scanner counting task that acquires counts synchroneously
            for i, task in enumerate(self._scanner_counter_daq_tasks):
                daq.DAQmxStartTask(task)

            if self._scanner_ai_channels:
                daq.DAQmxStartTask(self._scanner_analog_daq_task)

            daq.DAQmxStartTask(self._scanner_clock_daq_task)

            for i, task in enumerate(self._scanner_counter_daq_tasks):
                # wait for the scanner counter to finish
                daq.DAQmxWaitUntilTaskDone(
                    # define task
                    task,
                    # Maximum timeout for the counter times the positions. Unit is seconds.
                    self._RWTimeout * 2 * self._line_length)

            # wait for the scanner clock to finish
            daq.DAQmxWaitUntilTaskDone(
                # define task
                self._scanner_clock_daq_task,
                # maximal timeout for the counter times the positions
                self._RWTimeout * 2 * self._line_length)

            # count data will be written here
            self._scan_data = np.empty(
                (len(self.get_scanner_count_channels()), 2 * self._line_length),
                dtype=np.uint32)

            # number of samples which were read will be stored here
            n_read_samples = daq.int32()
            for i, task in enumerate(self._scanner_counter_daq_tasks):
                # actually read the counted photons
                daq.DAQmxReadCounterU32(
                    # read from this task
                    task,
                    # read number of double the # number of samples
                    2 * self._line_length,
                    # maximal timeout for the read# process
                    self._RWTimeout,
                    # write into this array
                    self._scan_data[i],
                    # length of array to write into
                    2 * self._line_length,
                    # number of samples which were actually read
                    daq.byref(n_read_samples),
                    # Reserved for future use. Pass NULL(here None) to this parameter.
                    None)

                # stop the counter task
                daq.DAQmxStopTask(task)

            # Analog channels
            if self._scanner_ai_channels:
                self._analog_data = np.full(
                    (len(self._scanner_ai_channels), self._line_length + 1),
                    222,
                    dtype=np.float64)

                analog_read_samples = daq.int32()

                daq.DAQmxReadAnalogF64(
                    self._scanner_analog_daq_task,
                    self._line_length + 1,
                    self._RWTimeout,
                    daq.DAQmx_Val_GroupByChannel,
                    self._analog_data,
                    len(self._scanner_ai_channels) * (self._line_length + 1),
                    daq.byref(analog_read_samples),
                    None
                )

                daq.DAQmxStopTask(self._scanner_analog_daq_task)

            # stop the clock task
            daq.DAQmxStopTask(self._scanner_clock_daq_task)

            # stop the analog output task
            self._stop_analog_output()

            if pixel_clock and self._pixel_clock_channel is not None:
                daq.DAQmxDisconnectTerms(
                    self._scanner_clock_channel + 'InternalOutput',
                    self._pixel_clock_channel)

            # create a new array for the final data (this time of the length
            # number of samples):
            self._real_data = np.empty(
                (len(self._scanner_counter_channels), self._line_length),
                dtype=np.uint32)

            # add up adjoint pixels to also get the counts from the low time of
            # the clock:
            self._real_data = self._scan_data[:, ::2]
            self._real_data += self._scan_data[:, 1::2]

            all_data = np.full(
                (len(self.get_scanner_count_channels()), self._line_length), 2, dtype=np.float64)
            all_data[0:len(self._real_data)] = np.array(
                self._real_data * self._scanner_clock_frequency, np.float64)

            if self._scanner_ai_channels:
                all_data[len(self._scanner_counter_channels):] = self._analog_data[:, :-1]

            # update the scanner position instance variable
            self._current_position = np.array(line_path[:, -1])
        except:
            self.log.exception('Error while scanning line.')
            return np.array([[-1.]])
        # return values is a rate of counts/s
        return all_data.transpose()

    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        a = self._stop_analog_output()

        b = 0
        if self._scanner_ai_channels:
            try:
                # stop the counter task
                daq.DAQmxStopTask(self._scanner_analog_daq_task)
                # after stopping delete all the configuration of the counter
                daq.DAQmxClearTask(self._scanner_analog_daq_task)
                # set the task handle to None as a safety
                self._scanner_analog_daq_task = None
            except:
                self.log.exception('Could not close analog.')
                b = -1

        c = self.close_counter(scanner=True)
        return -1 if a < 0 or b < 0 or c < 0 else 0

    def close_scanner_clock(self):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        return self.close_clock(scanner=True)

    # ================ End ConfocalScannerInterface Commands ===================

    # ==================== ODMRCounterInterface Commands =======================
    def set_up_odmr_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of
                                      the clock
        @param string clock_channel: if defined, this is the physical channel
                                     of the clock

        @return int: error code (0:OK, -1:error)
        """

        return self.set_up_clock(
            clock_frequency=clock_frequency,
            clock_channel=clock_channel,
            scanner=True,
            idle=False)

    def set_up_odmr(self, counter_channel=None, photon_source=None,
                    clock_channel=None, odmr_trigger_channel=None):
        """ Configures the actual counter with a given clock.

        @param string counter_channel: if defined, this is the physical channel
                                       of the counter
        @param string photon_source: if defined, this is the physical channel
                                     where the photons are to count from
        @param string clock_channel: if defined, this specifies the clock for
                                     the counter
        @param string odmr_trigger_channel: if defined, this specifies the
                                            trigger output for the microwave

        @return int: error code (0:OK, -1:error)
        """
        if self._scanner_clock_daq_task is None and clock_channel is None:
            self.log.error('No clock running, call set_up_clock before starting the counter.')
            return -1
        if self._scanner_counter_daq_tasks:
            self.log.error('Another counter is already running, close this one first.')
            return -1
        if self._scanner_ai_channels and self._scanner_analog_daq_task is not None:
            self.log.error('Another analog is already running, close this one first.')
            return -1

        my_clock_channel = clock_channel if clock_channel else self._scanner_clock_channel

        if self._scanner_counter_channels and self._photon_sources:
            my_counter_channel = counter_channel if counter_channel else self._scanner_counter_channels[0]
            my_photon_source = photon_source if photon_source else self._photon_sources[0]

            # this task will count photons with binning defined by the clock_channel
            task = daq.TaskHandle()
            try:
                # create task for the counter
                daq.DAQmxCreateTask('ODMRCounter', daq.byref(task))

                # set up semi period width measurement in photon ticks, i.e. the width
                # of each pulse (high and low) generated by pulse_out_task is measured
                # in photon ticks.
                #   (this task creates a channel to measure the time between state
                #    transitions of a digital signal and adds the channel to the task
                #    you choose)
                daq.DAQmxCreateCISemiPeriodChan(
                    # define to which task to# connect this function
                    task,
                    # use this counter channel
                    my_counter_channel,
                    # name to assign to it
                    'ODMR Counter',
                    # Expected minimum count value
                    0,
                    # Expected maximum count value
                    self._max_counts / self._scanner_clock_frequency,
                    # units of width measurement, here photon ticks
                    daq.DAQmx_Val_Ticks,
                    '')

                # connect the pulses from the clock to the counter
                daq.DAQmxSetCISemiPeriodTerm(
                    task,
                    my_counter_channel,
                    my_clock_channel + 'InternalOutput')

                # define the source of ticks for the counter as self._photon_source
                daq.DAQmxSetCICtrTimebaseSrc(
                    task,
                    my_counter_channel,
                    my_photon_source)

                self._scanner_counter_daq_tasks.append(task)
            except:
                self.log.exception('Error while setting up the digital counter of ODMR scan.')
                return -1

        try:
            # Analog task
            if self._scanner_ai_channels:
                atask = daq.TaskHandle()
                daq.DAQmxCreateTask('ODMRAnalog', daq.byref(atask))

                daq.DAQmxCreateAIVoltageChan(
                    atask,
                    ', '.join(self._scanner_ai_channels),
                    'ODMR Analog',
                    daq.DAQmx_Val_RSE,
                    -10,
                    10,
                    daq.DAQmx_Val_Volts,
                    ''
                )
                self._scanner_analog_daq_task = atask

            # start and stop pulse task to correctly initiate idle state high voltage.
            daq.DAQmxStartTask(self._scanner_clock_daq_task)
            # otherwise, it will be low until task starts, and MW will receive wrong pulses.
            daq.DAQmxStopTask(self._scanner_clock_daq_task)

            if self.lock_in_active:
                ptask = daq.TaskHandle()
                daq.DAQmxCreateTask('ODMRPulser', daq.byref(ptask))
                daq.DAQmxCreateDOChan(
                    ptask,
                    '{0:s}, {1:s}'.format(self._odmr_trigger_line, self._odmr_switch_line),
                    "ODMRPulserChannel",
                    daq.DAQmx_Val_ChanForAllLines)

                self._odmr_pulser_daq_task = ptask

            # connect the clock to the trigger channel to give triggers for the
            # microwave
            daq.DAQmxConnectTerms(
                self._scanner_clock_channel + 'InternalOutput',
                self._odmr_trigger_channel,
                daq.DAQmx_Val_DoNotInvertPolarity)
        except:
            self.log.exception('Error while setting up ODMR scan.')
            return -1
        return 0

    def set_odmr_length(self, length=100):
        """ Sets up the trigger sequence for the ODMR and the triggered microwave.

        @param int length: length of microwave sweep in pixel

        @return int: error code (0:OK, -1:error)
        """
        if self._scanner_counter_channels and len(self._scanner_counter_daq_tasks) < 1:
            self.log.error('No counter is running, cannot do ODMR without one.')
            return -1

        if self._scanner_ai_channels and self._scanner_analog_daq_task is None:
            self.log.error('No analog task is running, cannot do ODMR without one.')
            return -1

        self._odmr_length = length
        try:
            # set timing for odmr clock task to the number of pixel.
            daq.DAQmxCfgImplicitTiming(
                # define task
                self._scanner_clock_daq_task,
                # only a limited number of counts
                daq.DAQmx_Val_FiniteSamps,
                # count twice for each voltage +1 for starting this task.
                # This first pulse will start the count task.
                self._odmr_length + 1)

            # Digital
            if self._scanner_counter_channels:
                # set timing for odmr count task to the number of pixel.
                daq.DAQmxCfgImplicitTiming(
                    # define task
                    self._scanner_counter_daq_tasks[0],
                    # only a limited number of counts
                    daq.DAQmx_Val_ContSamps,
                    # count twice for each voltage +1 for starting this task.
                    # This first pulse will start the count task.
                    2 * (self._odmr_length + 1))

                # read samples from beginning of acquisition, do not overwrite
                daq.DAQmxSetReadRelativeTo(
                    self._scanner_counter_daq_tasks[0],
                    daq.DAQmx_Val_CurrReadPos)

                # do not read first sample
                daq.DAQmxSetReadOffset(
                    self._scanner_counter_daq_tasks[0],
                    0)

                # unread data in buffer will be overwritten
                daq.DAQmxSetReadOverWrite(
                    self._scanner_counter_daq_tasks[0],
                    daq.DAQmx_Val_DoNotOverwriteUnreadSamps)

            # Analog
            if self._scanner_ai_channels:
                # Analog in channel timebase
                daq.DAQmxCfgSampClkTiming(
                    self._scanner_analog_daq_task,
                    self._scanner_clock_channel + 'InternalOutput',
                    self._scanner_clock_frequency,
                    daq.DAQmx_Val_Rising,
                    daq.DAQmx_Val_ContSamps,
                    self._odmr_length + 1
                )

            if self._odmr_pulser_daq_task:
                # pulser channel timebase
                daq.DAQmxCfgSampClkTiming(
                    self._odmr_pulser_daq_task,
                    self._scanner_clock_channel + 'InternalOutput',
                    self._scanner_clock_frequency,
                    daq.DAQmx_Val_Rising,
                    daq.DAQmx_Val_ContSamps,
                    self._odmr_length + 1
                )
        except:
            self.log.exception('Error while setting up ODMR counter.')
            return -1
        return 0

    @property
    def oversampling(self):
        return self._oversampling

    @oversampling.setter
    def oversampling(self, val):
        if not isinstance(val, (int, float)):
            self.log.error('oversampling has to be int of float.')
        else:
            self._oversampling = int(val)

    @property
    def lock_in_active(self):
        return self._lock_in_active

    @lock_in_active.setter
    def lock_in_active(self, val):
        if not isinstance(val, bool):
            self.log.error('lock_in_active has to be boolean.')
        else:
            self._lock_in_active = val
            if self._lock_in_active:
                self.log.warn('You just switched the ODMR counter to Lock-In-mode. \n'
                              'Please make sure you connected all triggers correctly:\n'
                              '  {0:s} is the microwave trigger channel\n'
                              '  {1:s} is the switching channel for the lock in\n'
                              ''.format(self._odmr_trigger_line, self._odmr_switch_line))

    def count_odmr(self, length=100):
        """ Sweeps the microwave and returns the counts on that sweep.

        @param int length: length of microwave sweep in pixel

        @return float[]: the photon counts per second
        """
        if len(self._scanner_counter_daq_tasks) < 1 and self._scanner_counter_channels:
            self.log.error(
                'No counter is running, cannot scan an ODMR line without one.')
            return True, np.array([-1.])

        if self._scanner_ai_channels and self._scanner_analog_daq_task is None:
            self.log.error('No analog task is running, cannot do ODMR without one.')
            return True, np.array([-1.])

        # check if length setup is correct, if not, adjust.
        if self._odmr_pulser_daq_task:
            odmr_length_to_set = length * self.oversampling * 2
        else:
            odmr_length_to_set = length

        if self.set_odmr_length(odmr_length_to_set) < 0:
            self.log.error('An error arose while setting the odmr lenth to {}.'.format(odmr_length_to_set))
            return True, np.array([-1.])

        try:
            # start the scanner counting task that acquires counts synchronously
            if self._scanner_counter_channels:
                daq.DAQmxStartTask(self._scanner_counter_daq_tasks[0])
            if self._scanner_ai_channels:
                daq.DAQmxStartTask(self._scanner_analog_daq_task)
        except:
            self.log.exception('Cannot start ODMR counter.')
            return True, np.array([-1.])

        if self._odmr_pulser_daq_task:
            try:

                # The pulse pattern is an alternating 0 and 1 on the switching channel (line0),
                # while the first half of the whole microwave pulse is 1 and the other half is 0.
                # This way the beginning of the microwave has a rising edge.
                pulse_pattern = np.zeros(self.oversampling * 2, dtype=np.uint32)
                pulse_pattern[:self.oversampling] += 1
                pulse_pattern[::2] += 2

                daq.DAQmxWriteDigitalU32(self._odmr_pulser_daq_task,
                                         len(pulse_pattern),
                                         0,
                                         self._RWTimeout * self._odmr_length,
                                         daq.DAQmx_Val_GroupByChannel,
                                         pulse_pattern,
                                         None,
                                         None)

                daq.DAQmxStartTask(self._odmr_pulser_daq_task)
            except:
                self.log.exception('Cannot start ODMR pulser.')
                return True, np.array([-1.])

        try:
            daq.DAQmxStartTask(self._scanner_clock_daq_task)

            # wait for the scanner clock to finish
            daq.DAQmxWaitUntilTaskDone(
                # define task
                self._scanner_clock_daq_task,
                # maximal timeout for the counter times the positions
                self._RWTimeout * 2 * self._odmr_length)

            # Digital
            if self._scanner_counter_channels:
                # count data will be written here
                odmr_data = np.full(
                    (2 * self._odmr_length + 1, ),
                    222,
                    dtype=np.uint32)

                #number of samples which were read will be stored here
                n_read_samples = daq.int32()

                # actually read the counted photons
                daq.DAQmxReadCounterU32(
                    # read from this task
                    self._scanner_counter_daq_tasks[0],
                    # Read number of double the# number of samples
                    2 * self._odmr_length + 1,
                    # Maximal timeout for the read # process
                    self._RWTimeout,
                    # write into this array
                    odmr_data,
                    # length of array to write into
                    2 * self._odmr_length + 1,
                    # number of samples which were actually read
                    daq.byref(n_read_samples),
                    # Reserved for future use. Pass NULL (here None) to this parameter.
                    None)

            # Analog
            if self._scanner_ai_channels:
                odmr_analog_data = np.full(
                    (len(self._scanner_ai_channels), self._odmr_length + 1),
                    222,
                    dtype=np.float64)

                analog_read_samples = daq.int32()

                daq.DAQmxReadAnalogF64(
                    self._scanner_analog_daq_task,
                    self._odmr_length + 1,
                    self._RWTimeout,
                    daq.DAQmx_Val_GroupByChannel,
                    odmr_analog_data,
                    len(self._scanner_ai_channels) * (self._odmr_length + 1),
                    daq.byref(analog_read_samples),
                    None
                )

            # stop the counter task
            daq.DAQmxStopTask(self._scanner_clock_daq_task)
            if self._scanner_counter_channels:
                daq.DAQmxStopTask(self._scanner_counter_daq_tasks[0])
            if self._scanner_ai_channels:
                daq.DAQmxStopTask(self._scanner_analog_daq_task)
            if self._odmr_pulser_daq_task:
                daq.DAQmxStopTask(self._odmr_pulser_daq_task)

            # prepare array to return data
            all_data = np.full((len(self.get_odmr_channels()), length),
                               222,
                               dtype=np.float64)
            start_index = 0
            if self._scanner_counter_channels:
                # create a new array for the final data (this time of the length
                # number of samples)
                real_data = np.zeros((self._odmr_length, ), dtype=np.uint32)

                # add upp adjoint pixels to also get the counts from the low time of
                # the clock:

                real_data += odmr_data[1:-1:2]
                real_data += odmr_data[:-1:2]

                if self._odmr_pulser_daq_task:
                    differential_data = np.zeros((self.oversampling * length, ), dtype=np.float64)

                    differential_data += real_data[1::2]
                    differential_data -= real_data[::2]
                    differential_data = np.divide(differential_data, real_data[::2],
                                                  np.zeros_like(differential_data),
                                                  where=real_data[::2] != 0)

                    all_data[0] = np.median(np.reshape(differential_data,
                                                       (-1, self.oversampling)),
                                            axis=1
                                            )
                else:
                    all_data[0] = np.array(real_data * self._scanner_clock_frequency, np.float64)
                start_index += 1

            if self._scanner_ai_channels:
                if self._odmr_pulser_daq_task:
                    for i, analog_data in enumerate(odmr_analog_data):
                        differential_data = np.zeros((self.oversampling * length, ), dtype=np.float64)

                        differential_data += analog_data[1:-1:2]
                        differential_data -= analog_data[:-1:2]
                        differential_data = np.divide(differential_data, analog_data[:-1:2],
                                                      np.zeros_like(differential_data),
                                                      where=analog_data[:-1:2] != 0)

                        all_data[i+start_index] = np.median(np.reshape(differential_data,
                                                                       (-1, self.oversampling)),
                                                            axis=1
                                                            )

                else:
                    all_data[start_index:] = odmr_analog_data[:, :-1]

            return False, all_data
        except:
            self.log.exception('Error while counting for ODMR.')
            return True, np.full((len(self.get_odmr_channels()), 1), [-1.])

    def close_odmr(self):
        """ Closes the odmr and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        retval = 0
        try:
            # disconnect the trigger channel
            daq.DAQmxDisconnectTerms(
                self._scanner_clock_channel + 'InternalOutput',
                self._odmr_trigger_channel)

        except:
            self.log.exception('Error while disconnecting ODMR clock channel.')
            retval = -1

        if self._scanner_ai_channels:
            try:
                # stop the counter task
                daq.DAQmxStopTask(self._scanner_analog_daq_task)
                # after stopping delete all the configuration of the counter
                daq.DAQmxClearTask(self._scanner_analog_daq_task)
                # set the task handle to None as a safety
                self._scanner_analog_daq_task = None
            except:
                self.log.exception('Could not close analog.')
                retval = -1

        if self._odmr_pulser_daq_task:
            try:
                # stop the pulser task
                daq.DAQmxStopTask(self._odmr_pulser_daq_task)
                # after stopping delete all the configuration of the pulser
                daq.DAQmxClearTask(self._odmr_pulser_daq_task)
                # set the task handle to None as a safety
                self._odmr_pulser_daq_task = None
            except:
                self.log.exception('Could not close pulser.')
                retval = -1

        retval = -1 if self.close_counter(scanner=True) < 0 or retval < 0 else 0
        return retval

    def get_odmr_channels(self):
        ch = list()
        if self._scanner_counter_channels:
            ch.append(self._scanner_counter_channels[0])
        ch.extend(self._scanner_ai_channels)
        return ch

    def close_odmr_clock(self):
        """ Closes the odmr and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        return self.close_clock(scanner=True)

    # ================== End ODMRCounterInterface Commands ====================

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
                self._counting_edge,
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
        if samples is None:
            samples = int(self._samples_number)
        else:
            samples = int(samples)

        if timeout is None:
            timeout = self._RWTimeout

        # Count data will be written here
        _gated_count_data = np.empty([2,samples], dtype=np.uint32)

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


    # ======================== Digital channel control ==========================

    def digital_channel_switch(self, channel_name, mode=True):
        """
        Switches on or off the voltage output (5V) of one of the digital channels, that
        can as an example be used to switch on or off the AOM driver or apply a single
        trigger for ODMR.
        @param str channel_name: Name of the channel which should be controlled
                                    for example ('/Dev1/PFI9')
        @param bool mode: specifies if the voltage output of the chosen channel should be turned on or off

        @return int: error code (0:OK, -1:error)
        """
        if channel_name is None:
            self.log.error('No channel for digital output specified')
            return -1
        else:

            self.digital_out_task = daq.TaskHandle()
            if mode:
                self.digital_data = daq.c_uint32(0xffffffff)
            else:
                self.digital_data = daq.c_uint32(0x0)
            self.digital_read = daq.c_int32()
            self.digital_samples_channel = daq.c_int32(1)
            daq.DAQmxCreateTask('DigitalOut', daq.byref(self.digital_out_task))
            daq.DAQmxCreateDOChan(self.digital_out_task, channel_name, "", daq.DAQmx_Val_ChanForAllLines)
            daq.DAQmxStartTask(self.digital_out_task)
            daq.DAQmxWriteDigitalU32(self.digital_out_task, self.digital_samples_channel, True,
                                        self._RWTimeout, daq.DAQmx_Val_GroupByChannel,
                                        np.array(self.digital_data), self.digital_read, None)

            daq.DAQmxStopTask(self.digital_out_task)
            daq.DAQmxClearTask(self.digital_out_task)
            return 0


