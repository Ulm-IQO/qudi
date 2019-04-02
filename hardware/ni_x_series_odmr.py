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
from interface.slow_counter_interface import SlowCounterConstraints
from interface.slow_counter_interface import CountingMode
from interface.odmr_counter_interface import ODMRCounterInterface


class NationalInstrumentsXSeriesODMR(Base, ODMRCounterInterface):
    """ A National Instruments device that can count and control microvave generators.

    !!!!!! NI USB 63XX, NI PCIe 63XX and NI PXIe 63XX DEVICES ONLY !!!!!!

    See [National Instruments X Series Documentation](@ref nidaq-x-series) for details.

    stable: Kay Jahnke, Alexander Stark

    Example config for copy-paste:

    nicard_6343:
        module.Class: 'ni_x_series_odmr.NationalInstrumentsXSeriesODMR'
        photon_sources:
            - '/Dev1/PFI8'
        #    - '/Dev1/PFI9'
        default_odmr_clock_frequency: 100 # optional, in Hz
        odmr_clock_channel: '/Dev1/Ctr2'
        odmr_ai_channels:
            - '/Dev1/AI1'
        odmr_counter_channels:
            - '/Dev1/Ctr3'

        odmr_trigger_channel: '/Dev1/PFI7'

        max_counts: 3e7
        read_write_timeout: 10
        counting_edge_rising: True

    """

    _modtype = 'NICard'
    _modclass = 'hardware'

    # config options
    _photon_sources = ConfigOption('photon_sources', missing='error')

    # odmr
    _default_odmr_clock_frequency = ConfigOption('default_odmr_clock_frequency', 100, missing='info')
    _odmr_clock_channel = ConfigOption('odmr_clock_channel', missing='warn')
    _odmr_ai_channels = ConfigOption('odmr_ai_channels', [], missing='info')
    _odmr_counter_channels = ConfigOption('odmr_counter_channels', [], missing='warn')

    _odmr_trigger_channel = ConfigOption('odmr_trigger_channel', missing='error')
    _odmr_trigger_line = ConfigOption('odmr_trigger_line', 'Dev1/port0/line0', missing='warn')
    _odmr_switch_line = ConfigOption('odmr_switch_line', 'Dev1/port0/line1', missing='warn')

    # used as a default for expected maximum counts
    _max_counts = ConfigOption('max_counts', default=3e7)
    # timeout for the Read or/and write process in s
    _RWTimeout = ConfigOption('read_write_timeout', default=10)
    _counting_edge_rising = ConfigOption('counting_edge_rising', default=True)

    def on_activate(self):
        """ Starts up the NI Card at activation.
        """
        # the tasks used on that hardware device:
        self._odmr_clock_daq_task = None
        self._odmr_counter_daq_tasks = []
        self._odmr_length = None
        self._odmr_analog_daq_task = None
        self._odmr_pulser_daq_task = None
        self._oversampling = 0
        self._lock_in_active = False
        self._ai_voltage_range = [0, 0]

        if len(self._odmr_counter_channels) + len(self._odmr_ai_channels) < 1:
            self.log.error(
                'Specify at least one counter or analog input channel for the odmr!')

    def on_deactivate(self):
        """ Shut down the NI card.
        """
        self.close_odmr_clock()
        self.close_odmr()

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

    def reset_hardware(self):
        """ Resets the NI hardware, so the connection is lost and other
            programs can access it.

        @return int: error code (0:OK, -1:error)
        """
        retval = 0
        chanlist = [
            self._odmr_trigger_channel,
            self._odmr_clock_channel
            ]
        chanlist.extend(self._photon_sources)
        chanlist.extend(self._odmr_counter_channels)

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

    def set_up_odmr_clock(self, clock_frequency=None, clock_channel=None, idle=False):
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

        if self._odmr_clock_daq_task is not None:
            self.log.error('Another odmr clock is already running, close this one first.')
            return -1

        # Create handle for task, this task will generate pulse signal for
        # photon counting
        my_clock_daq_task = daq.TaskHandle()

        self._odmr_clock_frequency = float(clock_frequency) if clock_frequency is not None else self._default_odmr_clock_frequency

        # assign the clock channel, if given
        if clock_channel is not None:
            self._odmr_clock_channel = clock_channel

        # check whether only one clock pair is available, since some NI cards
        # only one clock channel pair.
        if self._odmr_clock_daq_task is not None:
            self.log.error(
                'Only one clock channel is available!\n'
                'Another clock is already running, close this one first '
                'in order to use it for your purpose!')
            return -1

        # Adjust the idle state if necessary
        my_idle = daq.DAQmx_Val_High if idle else daq.DAQmx_Val_Low
        try:
            # create task for clock
            task_name = 'ODMRClock'
            daq.DAQmxCreateTask(task_name, daq.byref(my_clock_daq_task))

            # create a digital clock channel with specific clock frequency:
            daq.DAQmxCreateCOPulseChanFreq(
                # The task to which to add the channels
                my_clock_daq_task,
                # which channel is used?
                self._odmr_clock_channel,
                # Name to assign to task (NIDAQ uses by # default the physical channel name as
                # the virtual channel name. If name is specified, then you must use the name
                # when you refer to that channel in other NIDAQ functions)
                'ODMR Clock Producer',
                # units, Hertz in our case
                daq.DAQmx_Val_Hz,
                # idle state
                my_idle,
                # initial delay
                0,
                # pulse frequency
                self._odmr_clock_frequency,
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

            self._odmr_clock_daq_task = my_clock_daq_task
        except:
            self.log.exception('Error while setting up clock.')
            return -1
        return 0

    def close_odmr_clock(self, power=0):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        try:
            # Stop the clock task:
            daq.DAQmxStopTask(self._odmr_clock_daq_task)

            # After stopping delete all the configuration of the clock:
            daq.DAQmxClearTask(self._odmr_clock_daq_task)

            # Set the task handle to None as a safety
            self._odmr_clock_daq_task = None
        except:
            self.log.exception('Could not close clock.')
            return -1
        return 0

    # ==================== ODMRCounterInterface Commands =======================

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
        if self._odmr_clock_daq_task is None and clock_channel is None:
            self.log.error('No clock running, call set_up_clock before starting the counter.')
            return -1
        if len(self._odmr_counter_daq_tasks) > 0:
            self.log.error('Another counter is already running, close this one first.')
            return -1
        if len(self._odmr_ai_channels) > 0 and self._odmr_analog_daq_task is not None:
            self.log.error('Another analog is already running, close this one first.')
            return -1

        clock_channel = clock_channel if clock_channel is not None else self._odmr_clock_channel
        counter_channel = counter_channel if counter_channel is not None else self._odmr_counter_channels[0]
        photon_source = photon_source if photon_source is not None else self._photon_sources[0]
        odmr_trigger_channel = odmr_trigger_channel if odmr_trigger_channel is not None else self._odmr_trigger_channel

        # this task will count photons with binning defined by the clock_channel
        task = daq.TaskHandle()
        if len(self._odmr_ai_channels) > 0:
            atask = daq.TaskHandle()
        try:
            # create task for the counter
            daq.DAQmxCreateTask('ODMRCounter', daq.byref(task))
            if len(self._odmr_ai_channels) > 0:
                daq.DAQmxCreateTask('ODMRAnalog', daq.byref(atask))

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
                counter_channel,
                # name to assign to it
                'ODMR Counter',
                # Expected minimum count value
                0,
                # Expected maximum count value
                self._max_counts / self._odmr_clock_frequency,
                # units of width measurement, here photon ticks
                daq.DAQmx_Val_Ticks,
                '')

            # Analog task
            if len(self._odmr_ai_channels) > 0:
                daq.DAQmxCreateAIVoltageChan(
                    atask,
                    ', '.join(self._odmr_ai_channels),
                    'ODMR Analog',
                    daq.DAQmx_Val_RSE,
                    self._ai_voltage_range[0],
                    self._ai_voltage_range[1],
                    daq.DAQmx_Val_Volts,
                    ''
                )

            # connect the pulses from the clock to the counter
            daq.DAQmxSetCISemiPeriodTerm(
                task,
                counter_channel,
                clock_channel + 'InternalOutput')

            # define the source of ticks for the counter as self._photon_source
            daq.DAQmxSetCICtrTimebaseSrc(
                task,
                counter_channel,
                photon_source)

            # start and stop pulse task to correctly initiate idle state high voltage.
            daq.DAQmxStartTask(self._odmr_clock_daq_task)
            # otherwise, it will be low until task starts, and MW will receive wrong pulses.
            daq.DAQmxStopTask(self._odmr_clock_daq_task)

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
                self._odmr_clock_channel + 'InternalOutput',
                odmr_trigger_channel,
                daq.DAQmx_Val_DoNotInvertPolarity)
            self._odmr_counter_daq_tasks.append(task)
            if len(self._odmr_ai_channels) > 0:
                self._odmr_analog_daq_task = atask
        except:
            self.log.exception('Error while setting up ODMR scan.')
            return -1
        return 0

    def set_odmr_length(self, length=100):
        """ Sets up the trigger sequence for the ODMR and the triggered microwave.

        @param int length: length of microwave sweep in pixel

        @return int: error code (0:OK, -1:error)
        """
        if len(self._odmr_counter_channels) > 0 and len(self._odmr_counter_daq_tasks) < 1:
            self.log.error('No counter is running, cannot do ODMR without one.')
            return -1

        if len(self._odmr_ai_channels) > 0 and self._odmr_analog_daq_task is None:
            self.log.error('No analog task is running, cannot do ODMR without one.')
            return -1

        self._odmr_length = length
        try:
            # set timing for odmr clock task to the number of pixel.
            daq.DAQmxCfgImplicitTiming(
                # define task
                self._odmr_clock_daq_task,
                # only a limited number of counts
                daq.DAQmx_Val_FiniteSamps,
                # count twice for each voltage +1 for starting this task.
                # This first pulse will start the count task.
                self._odmr_length + 1)

            # set timing for odmr count task to the number of pixel.
            daq.DAQmxCfgImplicitTiming(
                # define task
                self._odmr_counter_daq_tasks[0],
                # only a limited number of counts
                daq.DAQmx_Val_ContSamps,
                # count twice for each voltage +1 for starting this task.
                # This first pulse will start the count task.
                2 * (self._odmr_length + 1))

            # read samples from beginning of acquisition, do not overwrite
            daq.DAQmxSetReadRelativeTo(
                self._odmr_counter_daq_tasks[0],
                daq.DAQmx_Val_CurrReadPos)

            # do not read first sample
            daq.DAQmxSetReadOffset(
                self._odmr_counter_daq_tasks[0],
                0)

            # unread data in buffer will be overwritten
            daq.DAQmxSetReadOverWrite(
                self._odmr_counter_daq_tasks[0],
                daq.DAQmx_Val_DoNotOverwriteUnreadSamps)

            # Analog
            if len(self._odmr_ai_channels) > 0:
                # Analog in channel timebase
                daq.DAQmxCfgSampClkTiming(
                    self._odmr_analog_daq_task,
                    self._odmr_clock_channel + 'InternalOutput',
                    self._odmr_clock_frequency,
                    daq.DAQmx_Val_Rising,
                    daq.DAQmx_Val_ContSamps,
                    self._odmr_length + 1
                )

            if self._odmr_pulser_daq_task:
                # pulser channel timebase
                daq.DAQmxCfgSampClkTiming(
                    self._odmr_pulser_daq_task,
                    self._odmr_clock_channel + 'InternalOutput',
                    self._odmr_clock_frequency,
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
        if len(self._odmr_counter_daq_tasks) < 1:
            self.log.error(
                'No counter is running, cannot scan an ODMR line without one.')
            return True, np.array([-1.])

        if len(self._odmr_ai_channels) > 0 and self._odmr_analog_daq_task is None:
            self.log.error('No analog task is running, cannot do ODMR without one.')
            return True, np.array([-1.])

        odmr_length_to_set = length * self.oversampling * 2 if self._odmr_pulser_daq_task else length

        if self.set_odmr_length(odmr_length_to_set) < 0:
            self.log.error('An error arose while setting the odmr lenth to {}.'.format(odmr_length_to_set))
            return True, np.array([-1.])

        try:
            # start the odmr counting task that acquires counts synchronously
            daq.DAQmxStartTask(self._odmr_counter_daq_tasks[0])
            if len(self._odmr_ai_channels) > 0:
                daq.DAQmxStartTask(self._odmr_analog_daq_task)
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
            daq.DAQmxStartTask(self._odmr_clock_daq_task)

            # wait for the odmr clock to finish
            daq.DAQmxWaitUntilTaskDone(
                # define task
                self._odmr_clock_daq_task,
                # maximal timeout for the counter times the positions
                self._RWTimeout * 2 * self._odmr_length)

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
                self._odmr_counter_daq_tasks[0],
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
            if len(self._odmr_ai_channels) > 0:
                odmr_analog_data = np.full(
                    (len(self._odmr_ai_channels), self._odmr_length + 1),
                    222,
                    dtype=np.float64)

                analog_read_samples = daq.int32()

                daq.DAQmxReadAnalogF64(
                    self._odmr_analog_daq_task,
                    self._odmr_length + 1,
                    self._RWTimeout,
                    daq.DAQmx_Val_GroupByChannel,
                    odmr_analog_data,
                    len(self._odmr_ai_channels) * (self._odmr_length + 1),
                    daq.byref(analog_read_samples),
                    None
                )

            # stop the counter task
            daq.DAQmxStopTask(self._odmr_clock_daq_task)
            daq.DAQmxStopTask(self._odmr_counter_daq_tasks[0])
            if len(self._odmr_ai_channels) > 0:
                daq.DAQmxStopTask(self._odmr_analog_daq_task)
            if self._odmr_pulser_daq_task:
                daq.DAQmxStopTask(self._odmr_pulser_daq_task)

            # prepare array to return data
            all_data = np.full((len(self.get_odmr_channels()), length),
                               222,
                               dtype=np.float64)

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

                if len(self._odmr_ai_channels) > 0:
                    for i, analog_data in enumerate(odmr_analog_data):
                        differential_data = np.zeros((self.oversampling * length, ), dtype=np.float64)

                        differential_data += analog_data[1:-1:2]
                        differential_data -= analog_data[:-1:2]
                        differential_data = np.divide(differential_data, analog_data[:-1:2],
                                                      np.zeros_like(differential_data),
                                                      where=analog_data[:-1:2] != 0)

                        all_data[i+1] = np.median(np.reshape(differential_data,
                                                             (-1, self.oversampling)),
                                                  axis=1
                                                  )

            else:
                all_data[0] = np.array(real_data * self._odmr_clock_frequency, np.float64)
                if len(self._odmr_ai_channels) > 0:
                    all_data[1:] = odmr_analog_data[:, :-1]

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
                self._odmr_clock_channel + 'InternalOutput',
                self._odmr_trigger_channel)

        except:
            self.log.exception('Error while disconnecting ODMR clock channel.')
            retval = -1

        for i, task in enumerate(self._odmr_counter_daq_tasks):
            try:
                # stop the counter task
                daq.DAQmxStopTask(task)
                # after stopping delete all the configuration of the counter
                daq.DAQmxClearTask(task)
                # set the task handle to None as a safety
            except:
                self.log.exception('Could not close counter.')
                retval = -1
        self._odmr_counter_daq_tasks = []

        if len(self._odmr_ai_channels) > 0:
            try:
                # stop the counter task
                daq.DAQmxStopTask(self._odmr_analog_daq_task)
                # after stopping delete all the configuration of the counter
                daq.DAQmxClearTask(self._odmr_analog_daq_task)
                # set the task handle to None as a safety
                self._odmr_analog_daq_task = None
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

        return retval

    def get_odmr_channels(self):
        ch = [self._odmr_counter_channels[0]]
        ch.extend(self._odmr_ai_channels)
        return ch

    @property
    def ai_voltage_range(self):
        return self._ai_voltage_range

    @ai_voltage_range.setter
    def ai_voltage_range(self, val):
        if not isinstance(val, list):
            self.log.error('ai_voltage_range has to be list.')
        else:
            self._ai_voltage_range = val.copy()
