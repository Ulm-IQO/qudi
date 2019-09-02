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
import ctypes
import nidaqmx as ni
from nidaqmx._lib import lib_importer
from nidaqmx.stream_readers import AnalogMultiChannelReader, CounterReader

from core.module import Base, ConfigOption
# from core.configoption import ConfigOption
from core.util.helpers import natural_sort
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
        device_name: 'Dev1'
        digital_sources:  # optional
            - 'PFI15'
        analog_sources:  # optional
            - 'ai1'
        # external_sample_clock_source: 'PFI0'  # optional
        # external_sample_clock_frequency: 1000  # optional
        adc_voltage_range: [-10, 10]  # optional
        max_channel_samples_buffer: 10000000  # optional
        read_write_timeout: 10  # optional

    """

    # config options
    _device_name = ConfigOption(name='device_name', default='Dev1', missing='warn')
    _digital_sources = ConfigOption(name='digital_sources', default=list(), missing='info')
    _analog_sources = ConfigOption(name='analog_sources', default=list(), missing='info')
    _external_sample_clock_source = ConfigOption(
        name='external_sample_clock_source', default=None, missing='nothing')
    _external_sample_clock_frequency = ConfigOption(
        name='external_sample_clock_frequency', default=None, missing='nothing')

    _adc_voltage_range = ConfigOption('adc_voltage_range', default=(-10, 10), missing='info')
    _max_channel_samples_buffer = ConfigOption(
        'max_channel_samples_buffer', default=25*1024**2, missing='info')
    _rw_timeout = ConfigOption('read_write_timeout', default=10, missing='nothing')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._device_handle = None
        self._di_task_handles = list()
        self._di_readers = list()
        self._ai_task_handle = None
        self._ai_reader = None
        self._clk_task_handle = None
        self.__current_clk_frequency = -1.0

        self._data_buffer = dict()
        self.__all_counters = tuple()

        self._constraints = None
        return

    def on_activate(self):
        """ Starts up the NI Card at activation.
        """
        # Check if device is connected and set device to use
        dev_names = ni.system.System().devices.device_names
        if self._device_name.lower() not in [dev.lower() for dev in dev_names]:
            raise Exception('Device name "{0}" not found in list of connected devices: {1}\n'
                            'Activation of NationalInstrumentsXSeriesCounter failed!'
                            ''.format(self._device_name, dev_names))
        for dev in dev_names:
            if dev.lower() == self._device_name.lower():
                self._device_name = dev
                break
        self._device_handle = ni.system.Device(self._device_name)

        # Check digital input terminals
        if self._digital_sources:
            term_names = [term.rsplit('/', 1)[-1] for term in self._device_handle.terminals if
                          'PFI' in term]
            new_source_names = [src.strip('/').split('/')[-1].upper() for src in
                                self._digital_sources]
            invalid_sources = set(new_source_names).difference(set(term_names))
            if invalid_sources:
                self.log.error(
                    'Invalid digital source terminals encountered. Following sources will '
                    'be ignored:\n  {0}\nValid digital input terminals are:\n  {1}'
                    ''.format(', '.join(natural_sort(invalid_sources)),
                              ', '.join(term_names)))
            self._digital_sources = natural_sort(set(new_source_names).difference(invalid_sources))

        # Check analog input channels
        if self._analog_sources:
            channel_names = [chnl.rsplit('/', 1)[-1] for chnl in
                             self._device_handle.ai_physical_chans.channel_names]
            new_source_names = [src.strip('/').split('/')[-1].lower() for src in
                                self._analog_sources]
            invalid_sources = set(new_source_names).difference(set(channel_names))
            if invalid_sources:
                self.log.error('Invalid analog source channels encountered. Following sources will '
                               'be ignored:\n  {0}\nValid analog input channels are:\n  {1}'
                               ''.format(', '.join(natural_sort(invalid_sources)),
                                         ', '.join(channel_names)))
            self._analog_sources = natural_sort(set(new_source_names).difference(invalid_sources))

        # Check if there are any valid input channels left
        if not self._analog_sources and not self._digital_sources:
            raise Exception('No valid analog or digital sources defined in config. '
                            'Activation of NationalInstrumentsXSeriesCounter failed!')

        # Create constraints
        self._constraints = SlowCounterConstraints()
        self._constraints.max_detectors = 4
        if self._analog_sources:
            self._constraints.min_count_frequency = self._device_handle.ai_min_rate
            self._constraints.max_count_frequency = self._device_handle.ai_max_multi_chan_rate
        else:
            # FIXME: What is the minimum frequency for the digital counter timebase?
            self._constraints.min_count_frequency = 0
            self._constraints.max_count_frequency = self._device_handle.ci_max_timebase
        self._constraints.counting_mode = [CountingMode.CONTINUOUS]

        # Check external sample clock source
        if self._external_sample_clock_source is not None:
            new_name = self._external_sample_clock_source.strip('/').lower()
            if 'dev' in new_name:
                new_name = new_name.split('/', 1)[-1]
            if new_name not in [src.split('/', 2)[-1].lower() for src in self._device_handle.terminals]:
                self.log.error('No valid source terminal found for external_sample_clock_source '
                               '"{0}". Falling back to internal sampling clock.'
                               ''.format(self._external_sample_clock_source))
                self._external_sample_clock_source = None
            else:
                self._external_sample_clock_source = new_name

        # Check external sample clock frequency
        if self._external_sample_clock_source is None:
            self._external_sample_clock_frequency = None
        elif self._external_sample_clock_frequency is None:
            self.log.error('External sample clock source supplied but no clock frequency. '
                           'Falling back to internal clock instead.')
            self._external_sample_clock_source = None
        elif not self._int_clk_frequency_valid(self._external_sample_clock_frequency):
            self.log.error('External sample clock frequency requested ({0:.3e}Hz) is out of bounds.'
                           ' Please choose a value between {1:.3e}Hz and {2:.3e}Hz.'
                           ' Value will be clipped to the closest boundary.'
                           ''.format(self._external_sample_clock_frequency,
                                     self._constraints.min_count_frequency,
                                     self._constraints.max_count_frequency))
            self._external_sample_clock_frequency = min(self._external_sample_clock_frequency,
                                                        self._constraints.max_count_frequency)
            self._external_sample_clock_frequency = max(self._external_sample_clock_frequency,
                                                        self._constraints.min_count_frequency)
        if self._external_sample_clock_frequency is not None:
            self.__current_clk_frequency = float(self._external_sample_clock_frequency)

        self.terminate_all_tasks()
        self._di_task_handles = list()
        self._di_readers = list()
        self._ai_task_handle = None
        self._ai_reader = None
        self._clk_task_handle = None

        # Check if all input channels fit in the device
        if self._constraints.max_detectors <= len(self._digital_sources):
            self.log.error('Too many digital channels specified. Maximum number of digital '
                           'channels is {0:d}.'.format(self._constraints.max_detectors - 1))
            return

        # Preallocate data buffer
        self._data_buffer = np.zeros((len(self._digital_sources) + len(self._analog_sources),
                                      self._max_channel_samples_buffer), dtype=np.float64)

        self.__all_counters = tuple(
            ctr.split('/')[-1] for ctr in self._device_handle.co_physical_chans.channel_names if
            'ctr' in ctr.lower())
        return

    def on_deactivate(self):
        """ Shut down the NI card.
        """
        self.terminate_all_tasks()
        return

    def get_constraints(self):
        """ Get hardware limits of NI device.

        @return SlowCounterConstraints: constraints class for slow counter

        FIXME: ask hardware for limits when module is loaded
        """
        return self._constraints

    def set_up_clock(self, clock_frequency, clock_channel=None, idle=False):
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
        # Ignore parameter for now
        if clock_channel:
            self.log.warning('Parameter "clock_channel" given to "set_up_clock" has been ignored.')

        # Return if sample clock is externally supplied
        if self._external_sample_clock_source is not None and self._external_sample_clock_frequency is not None:
            return 0

        if self._clk_task_handle is not None:
            self.log.error('Sample clock task is already running. Unable to set up a new clock '
                           'before you close the previous one.')
            return -1

        idle_level = ni.constants.Level.HIGH if idle else ni.constants.Level.LOW
        clock_frequency = float(clock_frequency)

        # create task for sample clock
        for src in self.__all_counters:
            # Check if task by that name already exists
            try:
                task = ni.Task('SampleClock')
            except ni.DaqError:
                self.log.exception('Could not create task with name "SampleClock".')
                return -1

            # Try to configure the task and reserve resources
            try:
                task.co_channels.add_co_pulse_chan_freq(
                    '/{0}/{1}'.format(self._device_name, src),
                    freq=clock_frequency,
                    idle_state=idle_level)
                task.timing.cfg_implicit_timing(
                    sample_mode=ni.constants.AcquisitionType.CONTINUOUS)
            except ni.DaqError:
                self.log.exception('Error while configuring sample clock task.')
                try:
                    del task
                except NameError:
                    pass
                return -1

            try:
                # reserve resources for the clock task
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

        try:
            task.start()
        except ni.DaqError:
            self.log.exception('Error while starting sample clock task.')
            try:
                task.stop()
            except ni.DaqError:
                pass
            try:
                task.close()
            except ni.DaqError:
                pass
            try:
                del task
            except NameError:
                pass
            self._clk_task_handle = None
            return -1

        self._clk_task_handle = task
        self.__current_clk_frequency = clock_frequency
        return 0

    def set_up_counter(self, sources=None, clock_channel=None, counter_buffer=None):
        """ Configures the actual counter with a given clock.

        @param list(str) sources: optional, physical channel where the photons
                                  are to count from
        @param str clock_channel: optional, specifies the clock channel for the
                                  counter
        @param int counter_buffer: optional, a buffer of specified integer
                                   length, where in each bin the count numbers
                                   are saved.

        @return int: error code (0:OK, -1:error)
        """
        if self._clk_task_handle is None and self._external_sample_clock_source is None:
            self.log.error(
                'No sample clock counter task has been generated and no external clock source '
                'specified. Maybe you did not call "set_up_clock" in advance. '
                '"set_up_counter" failed.')
            self.terminate_all_tasks()
            return -1

        if self._external_sample_clock_source:
            clock_channel = '/{0}/{1}'.format(self._device_name, self._external_sample_clock_source)
            sample_freq = float(self._external_sample_clock_frequency)
        else:
            clock_channel = '/{0}InternalOutput'.format(self._clk_task_handle.channel_names[0])
            sample_freq = float(self._clk_task_handle.co_channels.all.co_pulse_freq)

        analog_sources = natural_sort(self._analog_sources) if self._analog_sources else list()
        digital_sources = natural_sort(self._digital_sources) if self._digital_sources else list()

        buffer_samples = min(max(int(self._rw_timeout * sample_freq), 1000000),
                             self._max_channel_samples_buffer)

        # Set up digital counting tasks
        if digital_sources:
            if self._di_task_handles:
                self.log.error(
                    'Digital counting tasks have already been generated. "set_up_counter" failed.')
                self.terminate_all_tasks()
                return -1
            for i, chnl in enumerate(digital_sources):
                chnl_name = '/{0}/{1}'.format(self._device_name, chnl)
                for ctr in self.__all_counters:
                    try:
                        task = ni.Task('PeriodCounter_{0}'.format(ctr))
                    except ni.DaqError:
                        if ctr == self.__all_counters[-1]:
                            self.log.error('Could not find a free counter resource. '
                                           '"set_up_counter" failed.')
                            self.terminate_all_tasks()
                            return -1
                        else:
                            continue

                    try:
                        ctr_name = '/{0}/{1}'.format(self._device_name, ctr)
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
                            sample_mode=ni.constants.AcquisitionType.CONTINUOUS,
                            samps_per_chan=buffer_samples)
                    except ni.DaqError:
                        try:
                            del task
                        except NameError:
                            pass
                        self.terminate_all_tasks()
                        self.log.exception(
                            'Something went wrong while configuring digital counter task for '
                            'channel "{0}".'.format(chnl))
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
                            self.log.exception(
                                'Unable to reserve resources for digital counting task of channel '
                                '"{0}". "set_up_counter" failed!'.format(chnl))
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

        # Set up analog input task
        if analog_sources:
            if self._ai_task_handle is not None:
                self.log.error(
                    'Analog input task has already been generated. "set_up_counter" failed.')
                self.terminate_all_tasks()
                return -1

            try:
                ai_task = ni.Task('AnalogIn')
            except ni.DaqError:
                self.log.exception('Unable to create analog-in task.')
                self.terminate_all_tasks()
                return -1

            try:
                ai_task.ai_channels.add_ai_voltage_chan(
                    ','.join(
                        ['/{0}/{1}'.format(self._device_name, chnl) for chnl in analog_sources]),
                    max_val=max(self._adc_voltage_range),
                    min_val=min(self._adc_voltage_range))
                ai_task.timing.cfg_samp_clk_timing(
                    sample_freq,
                    source=clock_channel,
                    active_edge=ni.constants.Edge.FALLING,
                    sample_mode=ni.constants.AcquisitionType.CONTINUOUS,
                    samps_per_chan=buffer_samples)
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
                self.log.exception(
                    'Unable to reserve resources for analog-in task. "set_up_counter" failed!')
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

            try:
                self._ai_reader = AnalogMultiChannelReader(ai_task.in_stream)
                self._ai_reader.verify_array_shape = False
            except ni.DaqError:
                self.log.exception('Something went wrong while setting up the analog input reader.')
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

            self._ai_task_handle = ai_task

        if self._ai_task_handle is not None:
            try:
                self._ai_task_handle.start()
            except ni.DaqError:
                self.log.exception('Error while starting analog input task.')
                self.terminate_all_tasks()
                return -1

        try:
            for task in self._di_task_handles:
                task.start()
        except ni.DaqError:
            self.log.exception('Error while starting digital counter tasks.')
            self.terminate_all_tasks()
            return -1
        return 0

    def get_counter_channels(self):
        """ Returns the list of counter channel names.

        @return tuple(str): channel names

        Most methods calling this might just care about the number of channels, though.
        """
        return self._digital_sources + self._analog_sources

    def get_counter(self, samples=None):
        """ Returns the current counts per second of the counter.

        @param int samples: if defined, number of samples to read in one go.
                            How many samples are read per readout cycle. The
                            readout frequency was defined in the counter setup.
                            That sets also the length of the readout array.

        @return float [samples]: array with entries as photon counts per second
        """
        if not self._di_task_handles and self._ai_task_handle is None:
            self.log.error('No task running, call set_up_counter before reading it.')
            return np.full((len(self.get_counter_channels()), 1), -1, dtype=np.float64)

        if samples is None:
            if self._ai_task_handle is not None:
                samples = self._ai_task_handle.in_stream.total_samp_per_chan_acquired - self._ai_task_handle.in_stream.curr_read_pos
            else:
                samples = self._di_task_handles[0].in_stream.total_samp_per_chan_acquired - self._di_task_handles[0].in_stream.curr_read_pos
        else:
            samples = int(samples)

        if samples < 1:
            return np.full((len(self.get_counter_channels()), 1), -1, dtype=np.float64)
        if samples > self._data_buffer.shape[1]:
            self.log.warning('Number of samples to read exceeds data buffer size.')
            self._data_buffer = np.zeros((self._data_buffer.shape[0], samples), dtype=np.float64)

        try:
            # Read digital channels
            for i, reader in enumerate(self._di_readers):
                # read the counter value. This function is blocking.
                reader.read_many_sample_double(self._data_buffer[i, :samples],
                                               number_of_samples_per_channel=samples,
                                               timeout=self._rw_timeout)
            # Read analog channels
            if self._ai_reader is not None:
                self._ai_reader.read_many_sample(
                    self._data_buffer[len(self._di_readers):, :samples],
                    number_of_samples_per_channel=samples,
                    timeout=self._rw_timeout)
        except ni.DaqError:
            self.log.exception('Getting samples from counter failed.')
            return np.full((len(self.get_counter_channels()), 1), -1, dtype=np.float64)

        # FIXME: For now convert the digital count values to frequencies since the logic is dumb
        if self._di_readers:
            self._data_buffer[:, :samples] *= self.__current_clk_frequency
        return self._data_buffer[:, :samples]

    def close_counter(self, throw_errors=True):
        """ Closes the counter and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        err = 0

        self._di_readers = list()
        self._ai_reader = None

        for i in range(len(self._di_task_handles)):
            try:
                if not self._di_task_handles[i].is_task_done():
                    self._di_task_handles[i].stop()
                self._di_task_handles[i].close()
            except ni.DaqError:
                if throw_errors:
                    self.log.exception('Error while trying to terminate digital counter task.')
                err = -1
            finally:
                del self._di_task_handles[i]
        self._di_task_handles = list()

        if self._ai_task_handle is not None:
            try:
                if not self._ai_task_handle.is_task_done():
                    self._ai_task_handle.stop()
                self._ai_task_handle.close()
            except ni.DaqError:
                if throw_errors:
                    self.log.exception('Error while trying to terminate analog input task.')
                err = -1
        self._ai_task_handle = None
        return err

    def close_clock(self, throw_errors=True):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        if self._clk_task_handle is None:
            return 0

        try:
            if not self._clk_task_handle.is_task_done():
                self._clk_task_handle.stop()
            self._clk_task_handle.close()
        except ni.DaqError:
            if throw_errors:
                self.log.exception('Error while trying to terminate clock task.')
            return -1

        self._clk_task_handle = None
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
        self.close_counter(throw_errors=False)
        self.close_clock(throw_errors=False)
        return

    def _int_clk_frequency_valid(self, frequency):
        max_rate = self._constraints.max_count_frequency
        min_rate = self._constraints.min_count_frequency
        return min_rate <= frequency <= max_rate
