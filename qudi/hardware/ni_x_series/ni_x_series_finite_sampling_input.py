# -*- coding: utf-8 -*-

"""
This file contains the qudi hardware module to use a National Instruments X-series card as mixed
signal input data streamer.

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

import ctypes
import time
import numpy as np
import nidaqmx as ni
from nidaqmx._lib import lib_importer  # Due to NIDAQmx C-API bug needed to bypass property getter
from nidaqmx.stream_readers import AnalogMultiChannelReader, CounterReader

from qudi.util.mutex import RecursiveMutex
from qudi.core.configoption import ConfigOption
from qudi.util.helpers import natural_sort
from qudi.interface.finite_sampling_input_interface import FiniteSamplingInputInterface, FiniteSamplingInputConstraints


class NIXSeriesFiniteSamplingInput(FiniteSamplingInputInterface):
    """
    A National Instruments device that can detect and count digital pulses and measure analog
    voltages as data stream.

    !!!!!! NI USB 63XX, NI PCIe 63XX and NI PXIe 63XX DEVICES ONLY !!!!!!

    See [National Instruments X Series Documentation](@ref nidaq-x-series) for details.

    Example config for copy-paste:

    ni_finite_sampling_input:
        module.Class: 'ni_x_series_finite_sampling_input.NIXSeriesFiniteSamplingInput'
        device_name: 'Dev1'
        digital_channel_units:  # optional
            'PFI15': 'c/s'
        analog_channel_units:  # optional
            'ai0': 'V'
            'ai1': 'V'
        # external_sample_clock_source: 'PFI0'  # optional
        # external_sample_clock_frequency: 1000  # optional
        adc_voltage_range: [-10, 10]  # optional
        max_channel_samples_buffer: 10000000  # optional
        read_write_timeout: 10  # optional
        sample_clock_output: '/Dev1/PFI20'  # optional

    """

    # config options
    _device_name = ConfigOption(name='device_name', default='Dev1', missing='warn')
    _digital_channel_units = ConfigOption(name='digital_channel_units', default=dict(), missing='info')
    _analog_channel_units = ConfigOption(name='analog_channel_units', default=dict(), missing='info')
    _external_sample_clock_source = ConfigOption(
        name='external_sample_clock_source', default=None, missing='nothing')
    _external_sample_clock_frequency = ConfigOption(
        name='external_sample_clock_frequency', default=None, missing='nothing')

    _physical_sample_clock_output = ConfigOption(name='sample_clock_output', default=None)

    _adc_voltage_range = ConfigOption('adc_voltage_range', default=(-10, 10), missing='info')
    _max_channel_samples_buffer = ConfigOption(
        'max_channel_samples_buffer', default=25e6, missing='info')

    # TODO: check limits
    _sample_rate_limits = ConfigOption(name='sample_rate_limits', default=(1, 1e6))
    _frame_size_limits = ConfigOption(name='frame_size_limits', default=(1, 1e9))

    _rw_timeout = ConfigOption('read_write_timeout', default=10, missing='nothing')

    # Hardcoded data type
    __data_type = np.float64

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # NIDAQmx device handle
        self._device_handle = None
        # Task handles for NIDAQmx tasks
        self._di_task_handles = list()
        self._ai_task_handle = None
        self._clk_task_handle = None
        # nidaqmx stream reader instances to help with data acquisition
        self._di_readers = list()
        self._ai_reader = None

        # List of all available counters and terminals for this device
        self.__all_counters = tuple()
        self.__all_digital_terminals = tuple()
        self.__all_analog_terminals = tuple()

        # currently active channels
        self.__active_channels = dict(di_channels=frozenset(), ai_channels=frozenset())

        self._thread_lock = RecursiveMutex()
        self._sample_rate = -1
        self._frame_size = -1
        self._constraints = None

    def on_activate(self):
        """
        Starts up the NI-card and performs sanity checks.
        """
        self._digital_channel_units = {self._extract_terminal(key): value
                                       for key, value in self._digital_channel_units.items()}
        self._analog_channel_units = {self._extract_terminal(key): value
                                      for key, value in self._analog_channel_units.items()}

        # Check if device is connected and set device to use
        dev_names = ni.system.System().devices.device_names
        if self._device_name.lower() not in set(dev.lower() for dev in dev_names):
            raise ValueError(
                f'Device name "{self._device_name}" not found in list of connected devices: '
                f'{dev_names}\nActivation of NIXSeriesInStreamer failed!'
            )
        for dev in dev_names:
            if dev.lower() == self._device_name.lower():
                self._device_name = dev
                break
        self._device_handle = ni.system.Device(self._device_name)

        self.__all_counters = tuple(
            ctr.split('/')[-1] for ctr in self._device_handle.co_physical_chans.channel_names if
            'ctr' in ctr.lower())
        self.__all_digital_terminals = tuple(
            term.rsplit('/', 1)[-1].lower() for term in self._device_handle.terminals if 'PFI' in term)
        self.__all_analog_terminals = tuple(
            term.rsplit('/', 1)[-1].lower() for term in self._device_handle.ai_physical_chans.channel_names)

        # Check digital input terminals
        digital_sources = set(src for src in self._digital_channel_units)
        if digital_sources:
            source_set = set(self._extract_terminal(src) for src in digital_sources)
            invalid_sources = source_set.difference(set(self.__all_digital_terminals))
            if invalid_sources:
                self.log.error(
                    'Invalid digital source terminals encountered. Following sources will '
                    'be ignored:\n  {0}\nValid digital input terminals are:\n  {1}'
                    ''.format(', '.join(natural_sort(invalid_sources)),
                              ', '.join(self.__all_digital_terminals)))
            digital_sources = set(natural_sort(source_set.difference(invalid_sources)))

        # Check analog input channels
        analog_sources = set(src for src in self._analog_channel_units)
        if analog_sources:
            source_set = set(self._extract_terminal(src) for src in analog_sources)
            invalid_sources = source_set.difference(set(self.__all_analog_terminals))
            if invalid_sources:
                self.log.error('Invalid analog source channels encountered. Following sources will '
                               'be ignored:\n  {0}\nValid analog input channels are:\n  {1}'
                               ''.format(', '.join(natural_sort(invalid_sources)),
                                         ', '.join(self.__all_analog_terminals)))
            analog_sources = set(natural_sort(source_set.difference(invalid_sources)))

        # Check if all input channels fit in the device
        if len(digital_sources) > 3:
            raise ValueError(
                'Too many digital channels specified. Maximum number of digital channels is 3.'
            )
        if len(analog_sources) > 16:
            raise ValueError(
                'Too many analog channels specified. Maximum number of analog channels is 16.'
            )

        # Check if there are any valid input channels left
        if not analog_sources and not digital_sources:
            raise ValueError(
                'No valid analog or digital sources defined in config. Activation of '
                'NIXSeriesInStreamer failed!'
            )

        # Check Physical clock output if specified
        if self._physical_sample_clock_output is not None:
            self._physical_sample_clock_output = self._extract_terminal(self._physical_sample_clock_output)
            assert self._physical_sample_clock_output in self.__all_digital_terminals, \
                f'Physical sample clock terminal specified in config is invalid'

        # Create constraints object and perform sanity/type checking
        self._channel_units = self._digital_channel_units.copy()
        self._channel_units.update(self._analog_channel_units)
        self._constraints = FiniteSamplingInputConstraints(
            channel_units=self._channel_units,
            frame_size_limits=self._frame_size_limits,
            sample_rate_limits=self._sample_rate_limits
        )
        # Make sure the ConfigOptions have correct values and types
        # (ensured by FiniteSamplingInputConstraints)
        self._sample_rate_limits = self._constraints.sample_rate_limits
        self._frame_size_limits = self._constraints.frame_size_limits
        self._channel_units = self._constraints.channel_units

        # initialize default settings
        self._sample_rate = self._constraints.max_sample_rate
        self._frame_size = 0

        self.set_active_channels(digital_sources.union(analog_sources))

    def on_deactivate(self):
        """ Shut down the NI card.
        """
        self.terminate_all_tasks()
        return

    @property
    def constraints(self):
        return self._constraints

    @property
    def active_channels(self):
        return self.__active_channels['di_channels'].union(self.__active_channels['ai_channels'])

    @property
    def sample_rate(self):
        """
        The currently set sample rate

        @return float: current sample rate in Hz
        """
        return self._sample_rate

    @property
    def frame_size(self):
        return self._frame_size

    @property
    def samples_in_buffer(self):
        """ Currently available samples per channel being held in the input buffer.
        This is the current minimum number of samples to be read with "get_buffered_samples()"
        without blocking.

        @return int: Number of unread samples per channel
        """
        with self._thread_lock:
            if self.module_state() == 'locked':
                if self._ai_task_handle is None:
                    return self._di_task_handles[0].in_stream.avail_samp_per_chan
                else:
                    return self._ai_task_handle.in_stream.avail_samp_per_chan
            return 0

    def set_sample_rate(self, rate):
        sample_rate = float(rate)
        assert self._constraints.sample_rate_in_range(sample_rate)[0], \
            f'Sample rate "{sample_rate}Hz" to set is out of ' \
            f'bounds {self._constraints.sample_rate_limits}'
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to set sample rate. Data acquisition in progress.'
            self._sample_rate = sample_rate
        return

    def set_active_channels(self, channels):
        """ Will set the currently active channels. All other channels will be deactivated.

        @param iterable(str) channels: Iterable of channel names to set active.
        """
        assert hasattr(channels, '__iter__') and not isinstance(channels, str), \
            f'Given input channels {channels} are not iterable'

        assert self.module_state() != 'locked', \
            'Unable to change active channels while finite sampling is running. New settings ignored.'

        channels = tuple(self._extract_terminal(channel) for channel in channels)

        assert set(channels).issubset(set(self._constraints.channel_names)), \
            f'Trying to set invalid input channels "' \
            f'{set(channels).difference(set(self._constraints.channel_names))}" not defined in config.'

        di_channels, ai_channels = self._extract_ai_di_from_input_channels(channels)

        with self._thread_lock:
            self.__active_channels['di_channels'], self.__active_channels['ai_channels'] \
                = frozenset(di_channels), frozenset(ai_channels)

    def set_frame_size(self, size):
        """ Will set the number of samples per channel to acquire within one frame.

        @param int size: The sample rate to set
        """
        samples = int(round(size))
        assert self._constraints.frame_size_in_range(samples)[0], \
            f'frame size "{samples}" to set is out of bounds {self._constraints.frame_size_limits}'
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to set frame size. Data acquisition in progress.'
            self._frame_size = samples

    def start_buffered_acquisition(self):
        """ Will start the acquisition of a data frame in a non-blocking way.
        Must return immediately and not wait for the data acquisition to finish.

        Must raise exception if data acquisition can not be started.
        """
        assert self.module_state() == 'idle', \
            'Unable to start data acquisition. Data acquisition already in progress.'
        self.module_state.lock()

        # set up tasks
        if self._init_sample_clock() < 0:
            self.terminate_all_tasks()
            self.module_state.unlock()
            raise NiInitError('Sample clock initialization failed; all tasks terminated')
        if self._init_digital_tasks() < 0:
            self.terminate_all_tasks()
            self.module_state.unlock()
            raise NiInitError('Counter task initialization failed; all tasks terminated')
        if self._init_analog_task() < 0:
            self.terminate_all_tasks()
            self.module_state.unlock()
            raise NiInitError('Analog in task initialization failed; all tasks terminated')

        # start tasks
        if len(self._di_task_handles) > 0:
            try:
                for task in self._di_task_handles:
                    task.start()
            except ni.DaqError:
                self.terminate_all_tasks()
                self.module_state.unlock()
                raise

        if self._ai_task_handle is not None:
            try:
                self._ai_task_handle.start()
            except ni.DaqError:
                self.terminate_all_tasks()
                self.module_state.unlock()
                raise

        try:
            self._clk_task_handle.start()
        except ni.DaqError:
            self.terminate_all_tasks()
            self.module_state.unlock()
            raise

    def stop_buffered_acquisition(self):
        """ Will abort the currently running data frame acquisition.
        Will return AFTER the data acquisition has been terminated without waiting for all samples
        to be acquired (if possible).

        Must NOT raise exceptions if no data acquisition is running.
        """
        if self.module_state() == 'locked':
            self.terminate_all_tasks()
            self.module_state.unlock()

    def get_buffered_samples(self, number_of_samples=None):
        """ Returns a chunk of the current data frame for all active channels read from the frame
        buffer.
        If parameter <number_of_samples> is omitted, this method will return the currently
        available samples within the frame buffer (i.e. the value of property <samples_in_buffer>).
        If <number_of_samples> is exceeding the currently available samples in the frame buffer,
        this method will block until the requested number of samples is available.
        If the explicitly requested number of samples is exceeding the number of samples pending
        for acquisition in the rest of this frame, raise an exception.

        Samples that have been already returned from an earlier call to this method are not
        available anymore and can be considered discarded by the hardware. So this method is
        effectively decreasing the value of property <samples_in_buffer> (until new samples have
        been read).

        If the data acquisition has been stopped before the frame has been acquired completely,
        this method must still return all available samples already read into buffer.

        @param int number_of_samples: optional, the number of samples to read from buffer

        @return dict: Sample arrays (values) for each active channel (keys)
        """
        data = dict()
        if self.module_state() == 'idle' and self.samples_in_buffer < 1:
            self.log.error('Unable to read data. Device is not running and no data in buffer.')
            return data

        number_of_samples = self.samples_in_buffer if number_of_samples is None else number_of_samples

        if number_of_samples > self._frame_size:
            raise ValueError(
                f'Number of requested samples ({number_of_samples}) exceeds number of samples '
                f'pending for acquisition ({self._frame_size}).'
            )

        if number_of_samples is not None and self.module_state() == 'locked':
            request_time = time.time()
            while number_of_samples > self.samples_in_buffer:  # TODO: Check whether this works with a real HW
                # TODO could one use the ni timeout of the reader class here?
                if time.time() - request_time < 1.1 * self._frame_size / self._sample_rate:  # TODO Is this timeout ok?
                    time.sleep(0.05)
                else:
                    self.terminate_all_tasks()
                    self.module_state.unlock()
                    raise TimeoutError(f'Acquiring {number_of_samples} samples took longer than the whole frame.')
        try:
            #TODO: What if counter stops while waiting for samples?

            # Read digital channels
            for i, reader in enumerate(self._di_readers):
                data_buffer = np.zeros(number_of_samples)
                # read the counter value. This function is blocking.
                read_samples = reader.read_many_sample_double(
                    data_buffer,
                    number_of_samples_per_channel=number_of_samples,
                    timeout=self._rw_timeout)
                if read_samples != number_of_samples:
                    return data
                data[reader._task.name.split('_')[-1]] = data_buffer
            # Read analog channels
            if self._ai_reader is not None:
                data_buffer = np.zeros(number_of_samples)
                read_samples = self._ai_reader.read_many_sample(
                    data_buffer,
                    number_of_samples_per_channel=number_of_samples,
                    timeout=self._rw_timeout)
                if read_samples != number_of_samples:
                    return data
                data[self._ai_reader._task.channel_names[0]] = data_buffer
        except ni.DaqError:
            self.log.exception('Getting samples from streamer failed.')
            return data
        return data

    def acquire_frame(self, frame_size=None):
        """ Acquire a single data frame for all active channels.
        This method call is blocking until the entire data frame has been acquired.

        If an explicit frame_size is given as parameter, it will not overwrite the property
        <frame_size> but just be valid for this single frame.

        See <start_buffered_acquisition>, <stop_buffered_acquisition> and <get_buffered_samples>
        for more details.

        @param int frame_size: optional, the number of samples to acquire in this frame

        @return dict: Sample arrays (values) for each active channel (keys)
        """
        with self._thread_lock:
            if frame_size is None:
                buffered_frame_size = None
            else:
                buffered_frame_size = self._frame_size
                self.set_frame_size(frame_size)

            self.start_buffered_acquisition()
            data = self.get_buffered_samples(self._frame_size)
            self.stop_buffered_acquisition()

            if buffered_frame_size is not None:
                self._frame_size = buffered_frame_size
            return data


    # =============================================================================================
    def _init_sample_clock(self):
        """
        If no external clock is given, configures a counter to provide the sample clock for all
        channels.

        @return int: error code (0: OK, -1: Error)
        """
        if self._clk_task_handle is not None:
            self.log.error('Sample clock task is already running. Unable to set up a new clock '
                           'before you close the previous one.')
            return -1

        # Try to find an available counter
        for src in self.__all_counters:
            # Check if task by that name already exists
            task_name = 'SampleClock_{0:d}'.format(id(self))
            try:
                task = ni.Task(task_name)
            except ni.DaqError:
                self.log.exception('Could not create task with name "{0}".'.format(task_name))
                return -1

            # Try to configure the task
            try:
                task.co_channels.add_co_pulse_chan_freq(
                    '/{0}/{1}'.format(self._device_name, src),
                    freq=self._sample_rate,
                    idle_state=ni.constants.Level.LOW)
                task.timing.cfg_implicit_timing(
                    sample_mode=ni.constants.AcquisitionType.FINITE,
                    samps_per_chan=self._frame_size + 1)
            except ni.DaqError:
                self.log.exception('Error while configuring sample clock task.')
                try:
                    del task
                except NameError:
                    pass
                return -1

            # Try to reserve resources for the task
            try:
                task.control(ni.constants.TaskMode.TASK_RESERVE)
            except ni.DaqError:
                # Try to clean up task handle
                try:
                    task.close()
                except ni.DaqError:
                    pass
                try:
                    del task
                except NameError:
                    pass

                # Return if no counter could be reserved
                if src == self.__all_counters[-1]:
                    self.log.exception('Error while setting up clock. Probably because no free '
                                       'counter resource could be reserved.')
                    return -1
                continue
            break

        self._clk_task_handle = task

        if self._physical_sample_clock_output is not None:
            clock_channel = '/{0}InternalOutput'.format(self._clk_task_handle.channel_names[0])
            ni.system.System().connect_terms(source_terminal=clock_channel,
                                             destination_terminal='/{0}/{1}'.format(
                                                 self._device_name, self._physical_sample_clock_output))
        return 0

    def _init_digital_tasks(self):
        """
        Set up tasks for digital event counting.

        @return int: error code (0:OK, -1:error)
        """
        digital_channels = self.__active_channels['di_channels']
        if not digital_channels:
            return 0
        if self._di_task_handles:
            self.log.error('Digital counting tasks have already been generated. '
                           'Setting up counter tasks has failed.')
            self.terminate_all_tasks()
            return -1

        if self._clk_task_handle is None and self._external_sample_clock_source is None:
            self.log.error(
                'No sample clock task has been generated and no external clock source specified. '
                'Unable to create digital counting tasks.')
            self.terminate_all_tasks()
            return -1

        clock_channel = '/{0}InternalOutput'.format(self._clk_task_handle.channel_names[0])
        # sample_freq = float(self._clk_task_handle.co_channels.all.co_pulse_freq)

        # Set up digital counting tasks
        for i, chnl in enumerate(digital_channels):
            chnl_name = '/{0}/{1}'.format(self._device_name, chnl)
            task_name = 'PeriodCounter_{0}'.format(chnl)
            # Try to find available counter
            for ctr in self.__all_counters:
                ctr_name = '/{0}/{1}'.format(self._device_name, ctr)
                try:
                    task = ni.Task(task_name)
                except ni.DaqError:
                    self.log.error('Could not create task with name "{0}"'.format(task_name))
                    self.terminate_all_tasks()
                    return -1

                try:
                    task.ci_channels.add_ci_period_chan(
                        ctr_name,
                        min_val=0,
                        max_val=100000000,
                        units=ni.constants.TimeUnits.TICKS,
                        edge=ni.constants.Edge.RISING)
                    # NOTE: The following two direct calls to C-function wrappers are a
                    # workaround due to a bug in some NIDAQmx.lib property getters. If one of
                    # these getters is called, it will mess up the task timing.
                    # This behaviour has been confirmed using pure C code.
                    # nidaqmx will call these getters and so the C function is called directly.
                    try:
                        lib_importer.windll.DAQmxSetCIPeriodTerm(
                            task._handle,
                            ctypes.c_char_p(ctr_name.encode('ascii')),
                            ctypes.c_char_p(clock_channel.encode('ascii')))
                        lib_importer.windll.DAQmxSetCICtrTimebaseSrc(
                            task._handle,
                            ctypes.c_char_p(ctr_name.encode('ascii')),
                            ctypes.c_char_p(chnl_name.encode('ascii')))
                    except:
                        lib_importer.cdll.DAQmxSetCIPeriodTerm(
                            task._handle,
                            ctypes.c_char_p(ctr_name.encode('ascii')),
                            ctypes.c_char_p(clock_channel.encode('ascii')))
                        lib_importer.cdll.DAQmxSetCICtrTimebaseSrc(
                            task._handle,
                            ctypes.c_char_p(ctr_name.encode('ascii')),
                            ctypes.c_char_p(chnl_name.encode('ascii')))

                    task.timing.cfg_implicit_timing(
                        sample_mode=ni.constants.AcquisitionType.FINITE,
                        samps_per_chan=self._frame_size)
                except ni.DaqError:
                    try:
                        task.close()
                        del task
                    except NameError:
                        pass
                    self.terminate_all_tasks()
                    self.log.exception('Something went wrong while configuring digital counter '
                                       'task for channel "{0}".'.format(chnl))
                    return -1

                try:
                    task.control(ni.constants.TaskMode.TASK_RESERVE)
                except ni.DaqError:
                    try:
                        task.close()
                    except ni.DaqError:
                        self.log.exception('Unable to close task.')
                    try:
                        del task
                    except NameError:
                        self.log.exception('Some weird namespace voodoo happened here...')

                    if ctr == self.__all_counters[-1]:
                        self.log.exception('Unable to reserve resources for digital counting task '
                                           'of channel "{0}". No available counter found!'
                                           ''.format(chnl))
                        self.terminate_all_tasks()
                        return -1
                    continue

                try:
                    self._di_readers.append(CounterReader(task.in_stream))
                    self._di_readers[-1].verify_array_shape = False
                except ni.DaqError:
                    self.log.exception(
                        'Something went wrong while setting up the digital counter reader for '
                        'channel "{0}".'.format(chnl))
                    self.terminate_all_tasks()
                    try:
                        task.close()
                    except ni.DaqError:
                        self.log.exception('Unable to close task.')
                    try:
                        del task
                    except NameError:
                        self.log.exception('Some weird namespace voodoo happened here...')
                    return -1

                self._di_task_handles.append(task)
                break
        return 0

    def _init_analog_task(self):
        """
        Set up task for analog voltage measurement.

        @return int: error code (0:OK, -1:error)
        """
        analog_channels = self.__active_channels['ai_channels']
        if not analog_channels:
            return 0
        if self._ai_task_handle:
            self.log.error(
                'Analog input task has already been generated. Unable to set up analog in task.')
            self.terminate_all_tasks()
            return -1
        if self._clk_task_handle is None and self._external_sample_clock_source is None:
            self.log.error(
                'No sample clock task has been generated and no external clock source specified. '
                'Unable to create analog voltage measurement tasks.')
            self.terminate_all_tasks()
            return -1

        clock_channel = '/{0}InternalOutput'.format(self._clk_task_handle.channel_names[0])
        sample_freq = float(self._clk_task_handle.co_channels.all.co_pulse_freq)

        # Set up analog input task
        task_name = 'AnalogIn_{0:d}'.format(id(self))
        try:
            ai_task = ni.Task(task_name)
        except ni.DaqError:
            self.log.exception('Unable to create analog-in task with name "{0}".'.format(task_name))
            self.terminate_all_tasks()
            return -1

        try:
            ai_ch_str = ','.join(['/{0}/{1}'.format(self._device_name, c) for c in analog_channels])
            ai_task.ai_channels.add_ai_voltage_chan(ai_ch_str,
                                                    max_val=max(self._adc_voltage_range),
                                                    min_val=min(self._adc_voltage_range))
            ai_task.timing.cfg_samp_clk_timing(sample_freq,
                                               source=clock_channel,
                                               active_edge=ni.constants.Edge.RISING,
                                               sample_mode=ni.constants.AcquisitionType.FINITE,
                                               samps_per_chan=self._frame_size)
        except ni.DaqError:
            self.log.exception(
                'Something went wrong while configuring the analog-in task.')
            try:
                del ai_task
            except NameError:
                pass
            self.terminate_all_tasks()
            return -1

        try:
            ai_task.control(ni.constants.TaskMode.TASK_RESERVE)
        except ni.DaqError:
            try:
                ai_task.close()
            except ni.DaqError:
                self.log.exception('Unable to close task.')
            try:
                del ai_task
            except NameError:
                self.log.exception('Some weird namespace voodoo happened here...')

            self.log.exception('Unable to reserve resources for analog-in task.')
            self.terminate_all_tasks()
            return -1

        try:
            self._ai_reader = AnalogMultiChannelReader(ai_task.in_stream)
            self._ai_reader.verify_array_shape = False
        except ni.DaqError:
            try:
                ai_task.close()
            except ni.DaqError:
                self.log.exception('Unable to close task.')
            try:
                del ai_task
            except NameError:
                self.log.exception('Some weird namespace voodoo happened here...')
            self.log.exception('Something went wrong while setting up the analog input reader.')
            self.terminate_all_tasks()
            return -1

        self._ai_task_handle = ai_task
        return 0

    def reset_hardware(self):
        """
        Resets the NI hardware, so the connection is lost and other programs can access it.
        @return int: error code (0:OK, -1:error)
        """
        try:
            self._device_handle.reset_device()
            self.log.info('Reset device {0}.'.format(self._device_name))
        except ni.DaqError:
            self.log.exception('Could not reset NI device {0}'.format(self._device_name))
            return -1
        return 0

    def terminate_all_tasks(self):
        err = 0

        self._di_readers = list()
        self._ai_reader = None

        while len(self._di_task_handles) > 0:
            try:
                if not self._di_task_handles[-1].is_task_done():
                    self._di_task_handles[-1].stop()
                self._di_task_handles[-1].close()
            except ni.DaqError:
                self.log.exception('Error while trying to terminate digital counter task.')
                err = -1
            finally:
                del self._di_task_handles[-1]
        self._di_task_handles = list()

        if self._ai_task_handle is not None:
            try:
                if not self._ai_task_handle.is_task_done():
                    self._ai_task_handle.stop()
                self._ai_task_handle.close()
            except ni.DaqError:
                self.log.exception('Error while trying to terminate analog input task.')
                err = -1
        self._ai_task_handle = None

        if self._clk_task_handle is not None:
            try:
                if not self._clk_task_handle.is_task_done():
                    self._clk_task_handle.stop()
                self._clk_task_handle.close()
            except ni.DaqError:
                self.log.exception('Error while trying to terminate clock task.')
                err = -1
        self._clk_task_handle = None
        return err


    @staticmethod
    def _extract_terminal(term_str):
        """
        Helper function to extract the bare terminal name from a string and strip it of the device
        name and dashes.
        Will return the terminal name in lower case.

        @param str term_str: The str to extract the terminal name from
        @return str: The terminal name in lower case
        """
        term = term_str.strip('/').lower()
        if 'dev' in term:
            term = term.split('/', 1)[-1]
        return term

    def _extract_ai_di_from_input_channels(self, input_channels):
        """
        Takes an iterable and returns the split up ai and di channels
        @return tuple(di_channels), tuple(ai_channels))
        """
        input_channels = tuple(self._extract_terminal(src) for src in input_channels)

        di_channels = tuple(channel for channel in input_channels if 'pfi' in channel)
        ai_channels = tuple(channel for channel in input_channels if 'ai' in channel)

        assert (di_channels or ai_channels), f'No channels could be extracted from {*input_channels,}'

        return tuple(di_channels), tuple(ai_channels)


class NiInitError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
