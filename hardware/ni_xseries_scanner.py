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

import re
import time
import ctypes
import numpy as np
from qtpy import QtCore

import nidaqmx as ni
from nidaqmx._lib import lib_importer  # Due to NIDAQmx C-API bug needed to bypass property getter
from nidaqmx.stream_readers import AnalogMultiChannelReader, CounterReader
from nidaqmx.stream_writers import AnalogMultiChannelWriter

from core.module import Base
from core.configoption import ConfigOption
from core.util.mutex import RecursiveMutex, Mutex


class NiXSeriesTaskManager:
    """

    """
    def __init__(self):
        self._devices = tuple(ni.system.System().devices.device_names)
        self._counters = dict()
        self._analog_in_terminals = dict()
        self._analog_out_terminals = dict()
        self._pfi_terminals = dict()
        for dev in self._devices:
            dev_handle = ni.system.Device(dev)
            # Extract counters
            ch_names = dev_handle.co_physical_chans.channel_names
            self._counters[dev] = tuple(ch.split('/')[-1] for ch in ch_names if 'ctr' in ch.lower())
            # Extract analog in terminals
            ch_names = dev_handle.ai_physical_chans.channel_names
            self._analog_in_terminals[dev] = tuple(ch.rsplit('/', 1)[-1] for ch in ch_names)
            # Extract analog out terminals
            ch_names = dev_handle.ao_physical_chans.channel_names
            self._analog_out_terminals[dev] = tuple(ch.rsplit('/', 1)[-1] for ch in ch_names)
            # Extract PFI terminals
            ch_names = dev_handle.terminals
            matches = tuple(re.search(r'PFI\d+\Z', ch, re.IGNORECASE) for ch in ch_names)
            self._pfi_terminals[dev] = tuple(match.group() for match in matches if match)

    @property
    def devices(self):
        return self._devices

    @property
    def analog_in_terminals(self):
        return self._analog_in_terminals.copy()

    @property
    def analog_out_terminals(self):
        return self._analog_out_terminals.copy()

    @property
    def pfi_terminals(self):
        return self._pfi_terminals.copy()

    def get_clock_task(self, name, frequency, cycles=-1, device=None, idle_high=False):
        """

        @param name:
        @param frequency:
        @param cycles:
        @param device:
        @param idle_high:
        @return:
        """
        if device is None:
            device = self._devices[0]
        elif device not in self._devices:
            return None
        cycles = -1 if cycles == 0 else int(cycles)
        idle_state = ni.constants.Level.HIGH if idle_high else ni.constants.Level.LOW
        # Try to find an available counter
        for ctr in self._counters[device]:
            # Check if task by that name already exists
            try:
                task = ni.Task(name)
            except ni.DaqError:
                return None

            # Try to configure the task
            try:
                task.co_channels.add_co_pulse_chan_freq('/{0}/{1}'.format(device, ctr),
                                                        freq=frequency,
                                                        idle_state=idle_state)
                if cycles < 0:
                    task.timing.cfg_implicit_timing(
                        sample_mode=ni.constants.AcquisitionType.CONTINUOUS)
                else:
                    task.timing.cfg_implicit_timing(
                        sample_mode=ni.constants.AcquisitionType.FINITE,
                        samps_per_chan=cycles)
            except ni.DaqError:
                return None

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
                continue
            return task
        return None

    def get_analog_in_task(self, name, channels, clk_terminal, clk_freq, samples=-1, device=None,
                           active_falling=True, min_val=-10.0, max_val=10.0, buffer_size=1048576):
        """

        :param name:
        :param channels:
        :param clk_terminal:
        :param clk_freq:
        :param samples:
        :param device:
        :param active_falling:
        :return:
        """
        if device is None:
            device = self._devices[0]
        elif device not in self._devices:
            return None, None
        samples = -1 if samples == 0 else int(samples)
        active_edge = ni.constants.Edge.FALLING if active_falling else ni.constants.Edge.RISING
        if min_val > max_val:
            min_val, max_val = max_val, min_val
        if any(ch not in self._analog_in_terminals[device] for ch in channels):
            return None, None
        ai_ch_str = ','.join(tuple('/{0}/{1}'.format(device, ch) for ch in channels))

        # Set up analog input task
        try:
            task = ni.Task(name)
        except ni.DaqError:
            return None, None

        try:
            task.ai_channels.add_ai_voltage_chan(ai_ch_str, min_val=min_val, max_val=max_val)
            if samples < 0:
                task.timing.cfg_samp_clk_timing(clk_freq,
                                                source=clk_terminal,
                                                active_edge=active_edge,
                                                sample_mode=ni.constants.AcquisitionType.CONTINUOUS,
                                                samps_per_chan=buffer_size)
            else:
                task.timing.cfg_samp_clk_timing(clk_freq,
                                                source=clk_terminal,
                                                active_edge=active_edge,
                                                sample_mode=ni.constants.AcquisitionType.FINITE,
                                                samps_per_chan=samples)
        except ni.DaqError:
            return None, None

        try:
            task.control(ni.constants.TaskMode.TASK_RESERVE)
        except ni.DaqError:
            try:
                task.close()
            except ni.DaqError:
                pass
            return None, None

        try:
            reader = AnalogMultiChannelReader(task.in_stream)
            reader.verify_array_shape = False
        except ni.DaqError:
            try:
                task.close()
            except ni.DaqError:
                pass
            return None, None
        return task, reader

    def get_analog_out_task(self, name, channels, clk_terminal, clk_freq, samples=-1, device=None,
                            active_falling=False, min_vals=None, max_vals=None, buffer_size=1048576):
        if device is None:
            device = self._devices[0]
        elif device not in self._devices:
            return None, None
        if any(ch not in self._analog_out_terminals[device] for ch in channels):
            return None, None
        if min_vals is None:
            min_vals = [-10.0] * len(channels)
        if max_vals is None:
            max_vals = [10.0] * len(channels)
        active_edge = ni.constants.Edge.FALLING if active_falling else ni.constants.Edge.RISING
        samples = -1 if samples == 0 else int(samples)

        # Set up analog output task
        try:
            task = ni.Task(name)
        except ni.DaqError:
            return None, None

        try:
            for ch_index, ch in enumerate(channels):
                ao_channel = '/{0}/{1}'.format(device, ch)
                task.ao_channels.add_ao_voltage_chan(ao_channel,
                                                     min_val=min_vals[ch_index],
                                                     max_val=max_vals[ch_index])
            if samples < 0:
                task.timing.cfg_samp_clk_timing(
                    clk_freq,
                    source=clk_terminal,
                    active_edge=active_edge,
                    sample_mode=ni.constants.AcquisitionType.CONTINUOUS,
                    samps_per_chan=buffer_size)
            else:
                task.timing.cfg_samp_clk_timing(
                    clk_freq,
                    source=clk_terminal,
                    active_edge=active_edge,
                    sample_mode=ni.constants.AcquisitionType.FINITE,
                    samps_per_chan=samples)
        except ni.DaqError:
            return None, None

        try:
            task.control(ni.constants.TaskMode.TASK_RESERVE)
        except ni.DaqError:
            try:
                task.close()
            except ni.DaqError:
                pass
            return None, None

        try:
            writer = AnalogMultiChannelWriter(task.out_stream)
        except ni.DaqError:
            try:
                task.close()
            except ni.DaqError:
                pass
            return None, None
        return task, writer

    def get_counting_task(self, name, channel, clk_terminal, clk_freq, samples=-1, device=None,
                           active_falling=False, min_val=0, max_val=100000000, buffer_size=1048576):
        if device is None:
            device = self._devices[0]
        elif device not in self._devices:
            return None, None
        if channel not in self._pfi_terminals[device]:
            return None, None
        active_edge = ni.constants.Edge.FALLING if active_falling else ni.constants.Edge.RISING
        samples = -1 if samples == 0 else int(samples)
        chnl_name = '/{0}/{1}'.format(device, channel)
        # Try to find available counter
        for ctr in self._counters[device]:
            ctr_name = '/{0}/{1}'.format(device, ctr)
            try:
                task = ni.Task(name)
            except ni.DaqError:
                try:
                    task.close()
                except:
                    pass
                return None, None

            try:
                task.ci_channels.add_ci_period_chan(ctr_name,
                                                    min_val=min_val,
                                                    max_val=max_val,
                                                    units=ni.constants.TimeUnits.TICKS,
                                                    edge=active_edge)
                # NOTE: The following two direct calls to C-function wrappers are a
                # workaround due to a bug in some NIDAQmx.lib property getters. If one of
                # these getters is called, it will mess up the task timing.
                # This behaviour has been confirmed using pure C code.
                # nidaqmx will call these getters and so the C function is called directly.
                try:
                    lib_importer.windll.DAQmxSetCIPeriodTerm(
                        task._handle,
                        ctypes.c_char_p(ctr_name.encode('ascii')),
                        ctypes.c_char_p(clk_terminal.encode('ascii')))
                    lib_importer.windll.DAQmxSetCICtrTimebaseSrc(
                        task._handle,
                        ctypes.c_char_p(ctr_name.encode('ascii')),
                        ctypes.c_char_p(chnl_name.encode('ascii')))
                except:
                    lib_importer.cdll.DAQmxSetCIPeriodTerm(
                        task._handle,
                        ctypes.c_char_p(ctr_name.encode('ascii')),
                        ctypes.c_char_p(clk_terminal.encode('ascii')))
                    lib_importer.cdll.DAQmxSetCICtrTimebaseSrc(
                        task._handle,
                        ctypes.c_char_p(ctr_name.encode('ascii')),
                        ctypes.c_char_p(chnl_name.encode('ascii')))

                if samples < 0:
                    task.timing.cfg_implicit_timing(
                        sample_mode=ni.constants.AcquisitionType.CONTINUOUS,
                        samps_per_chan=buffer_size)
                else:
                    task.timing.cfg_implicit_timing(
                        sample_mode=ni.constants.AcquisitionType.FINITE,
                        samps_per_chan=samples)
            except ni.DaqError:
                try:
                    task.close()
                except:
                    pass
                return None, None

            try:
                task.control(ni.constants.TaskMode.TASK_RESERVE)
            except ni.DaqError:
                try:
                    task.close()
                except ni.DaqError:
                    pass
                try:
                    del task
                except NameError:
                    pass

                if ctr == self._counters[device][-1]:
                    return None, None
                continue

            try:
                reader = CounterReader(task.in_stream)
                reader.verify_array_shape = False
            except ni.DaqError:
                try:
                    del reader
                except NameError:
                    pass
                try:
                    task.close()
                except ni.DaqError:
                    pass
                return None, None
            return task, reader
        return None, None

    @staticmethod
    def connect_terminals(source, destination):
        try:
            ni.system.system.System().connect_terms(source_terminal=source,
                                                    destination_terminal=destination)
        except ni.DaqError:
            return True
        return False

    @staticmethod
    def terminate_task(task):
        """

        @param ni.Task task:
        @return bool:
        """
        try:
            task.close()
        except ni.DaqError:
            return True
        return False


class ScanImage:
    """

    """
    def __init__(self, extent, size, ax_names, ax_cfg, sample_frequency, count_channels=None, analog_channels=None):
        if any(len(var) != 2 for var in (extent, size, ax_names, ax_cfg)):
            raise ValueError('Parameters "extent", "size", "ax_names" and "ax_cfg" must be '
                             'iterables of length 2')

        self.lock = Mutex()
        self._axes_cfg = tuple(ax_cfg)
        self._axes_names = tuple(ax_names)
        self._extent = ((min(extent[0]), max(extent[0])), (min(extent[1]), max(extent[1])))
        self._size = (int(size[0]), int(size[1]))
        self._sample_frequency = float(sample_frequency)
        self._analog_channels = tuple(analog_channels) if analog_channels else tuple()
        self._count_channels = tuple(count_channels) if count_channels else tuple()
        self._channels = self._count_channels + self._analog_channels
        if len(self.channels) < 1:
            raise Exception('No digital or analog channels.')
        self._overscan = ax_cfg[0]['overscan']

        for axis, (min_val, max_val) in enumerate(self._extent):
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            min_limit, max_limit = self.axes_range_limits[axis]
            if min_val < min_limit or max_val > max_limit:
                raise ValueError('ScanImage extent for axis {0:d} is out of bounds for axis range '
                                 '[{1}, {2}]'.format(axis, min_limit, max_limit))

        if self._size[0] < 2 or self._size[1] < 2:
            raise ValueError('ScanImage size dimensions must be at least 2px')

        self.raw_count_data = None
        self.raw_analog_data = None
        self._voltage_path = None
        self.__initialize_data()
        self.__initialize_voltage_path()
        self.missing_samples = self.samples_per_channel

    def __initialize_data(self):
        """
        """
        # Calculate number of pixels in the image including backscan and overscan
        image_size = (2 * self._size[0] + 4 * self._overscan) * self._size[1]
        self.raw_count_data = np.zeros(len(self._count_channels) * image_size)
        self.raw_analog_data = np.zeros((len(self._analog_channels), image_size))

    def __initialize_voltage_path(self):
        """
        """
        # Convert fast axis into voltages
        min_ax, max_ax = self._extent[0]
        pos_low, pos_high = self.axes_range_limits[0]
        volt_low, volt_high = self._axes_cfg[0]['voltage_range']
        pos_span = pos_high - pos_low
        volt_span = volt_high - volt_low
        if self._overscan > 0:
            px_res = (max_ax - min_ax) / (self._size[0] - 1)
            min_ax -= self._overscan * px_res
            max_ax += self._overscan * px_res
        fast_axis = np.linspace(min_ax, max_ax, self._size[0] + 2 * self._overscan)
        fast_axis = volt_low + (((fast_axis - pos_low) / pos_span) * volt_span)
        np.clip(fast_axis, volt_low, volt_high, out=fast_axis)

        # Convert slow_axis into voltages
        min_ax, max_ax = self._extent[1]
        pos_low, pos_high = self.axes_range_limits[1]
        volt_low, volt_high = self._axes_cfg[1]['voltage_range']
        pos_span = pos_high - pos_low
        volt_span = volt_high - volt_low
        slow_axis = np.linspace(min_ax, max_ax, self._size[1])
        slow_axis = volt_low + (((slow_axis - pos_low) / pos_span) * volt_span)
        np.clip(slow_axis, volt_low, volt_high, out=slow_axis)

        fast = np.tile(np.concatenate((fast_axis, fast_axis[::-1])), slow_axis.size)
        slow = np.repeat(slow_axis, 2 * fast_axis.size)
        self._voltage_path = np.vstack((fast, slow))
        # repeat first voltage step due to sampling clock issues with NI card.
        self._voltage_path = np.concatenate((self._voltage_path, self._voltage_path[:, -1:]),
                                            axis=1)

    @property
    def axes_range_limits(self):
        return self._axes_cfg[0]['position_range'], self._axes_cfg[1]['position_range']

    @property
    def axes_voltage_limits(self):
        return self._axes_cfg[0]['voltage_range'], self._axes_cfg[1]['voltage_range']

    @property
    def overscan(self):
        return self._overscan

    @property
    def extent(self):
        return self._extent

    @property
    def size(self):
        return self._size

    @property
    def sample_frequency(self):
        return self._sample_frequency

    @property
    def analog_channels(self):
        return self._analog_channels

    @property
    def count_channels(self):
        return self._count_channels

    @property
    def channels(self):
        return self._count_channels + self._analog_channels

    @property
    def scan_image_dict(self):
        with self.lock:
            line_size = 4 * self._overscan + 2 * self._size[0]
            offset = 0
            end = self.samples_per_channel
            data_dict = dict()
            for ch in self._count_channels:
                full_scan = self.raw_count_data[offset:end].reshape(
                    (line_size, self._size[1]), order='F')
                data_dict[ch] = full_scan[self._overscan:self._overscan + self._size[0], :]
                offset = end
                end += self.samples_per_channel
            for ii, ch in enumerate(self._analog_channels):
                full_scan = self.raw_analog_data[ii, :].reshape(
                    (line_size, self._size[1]), order='F')
                data_dict[ch] = full_scan[self._overscan:self._overscan + self._size[0], :]
            return data_dict

    @property
    def backscan_image_dict(self):
        with self.lock:
            line_size = 4 * self._overscan + 2 * self._size[0]
            offset = 0
            end = self.samples_per_channel
            start = 3 * self._overscan + self._size[0]
            data_dict = dict()
            for ch in self._count_channels:
                full_scan = self.raw_count_data[offset:end].reshape(
                    (line_size, self._size[1]), order='F')
                data_dict[ch] = full_scan[start:start + self._size[0], :]
                offset = end
                end += self.samples_per_channel
            for ii, ch in enumerate(self._analog_channels):
                full_scan = self.raw_analog_data[ii, :].reshape(
                    (line_size, self._size[1]), order='F')
                data_dict[ch] = full_scan[start:start + self._size[0], :]
            return data_dict

    @property
    def fast_axis(self):
        return np.linspace(self._extent[0][0], self._extent[0][1], self._size[0])

    @property
    def slow_axis(self):
        return np.linspace(self._extent[1][0], self._extent[1][1], self._size[1])

    @property
    def voltage_path(self):
        return self._voltage_path

    @property
    def axes_names(self):
        return self._axes_names

    @property
    def is_done(self):
        with self.lock:
            return self.missing_samples == 0

    @property
    def fast_axis_scan_time(self):
        return (4 * self._overscan + 2 * self._size[0]) / self.sample_frequency

    @property
    def complete_scan_time(self):
        return self.fast_axis_scan_time * self._size[1]

    @property
    def samples_per_channel(self):
        return (4 * self._overscan + 2 * self._size[0]) * self._size[1]

    @property
    def samples_read(self):
        return self.samples_per_channel - self.missing_samples

    def reset(self):
        with self.lock:
            self.__initialize_data()
            self.missing_samples = self.samples_per_channel


class NiXSeriesAnalogScanner(Base):
    """

    """
    _device_name = ConfigOption(name='device_name', missing='error')
    _axes_configuration = ConfigOption(name='axes_configuration', missing='error')
    _counter_channels = ConfigOption(name='counter_channels', default=dict(), missing='nothing')
    _analog_in_channels = ConfigOption(name='analog_in_channels', default=dict(), missing='nothing')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = RecursiveMutex()

        self._scan_image = None
        self._last_read_time = 0.0

        self._clock_task = None
        self._analog_out_task = None
        self._analog_writer = None
        self._analog_in_task = None
        self._analog_reader = None
        self._counter_tasks = list()
        self._counter_readers = list()

        self._task_manager = None

    def on_activate(self):
        self._last_read_time = 0.0
        self._task_manager = NiXSeriesTaskManager()

        self.terminate_image_scan()
        self._scan_image = None

        self.__check_axes_configuration()
        self.__check_data_input_channels()

    def on_deactivate(self):
        self.terminate_image_scan()
        self._sig_start_scan.disconnect()

    def terminate_image_scan(self):
        with self._lock:
            # Terminate clock task
            if self._clock_task is not None:
                self._task_manager.terminate_task(self._clock_task)
                self._clock_task = None
            # Terminate analog out task
            self._analog_writer = None
            if self._analog_out_task is not None:
                self._task_manager.terminate_task(self._analog_out_task)
                self._analog_out_task = None
            # Terminate analog in task
            self._analog_reader = None
            if self._analog_in_task is not None:
                self._task_manager.terminate_task(self._analog_in_task)
                self._analog_in_task = None
            # Terminate digital counting tasks
            self._counter_readers = list()
            for task in self._counter_tasks:
                self._task_manager.terminate_task(task)
            self._counter_tasks = list()
            # Unlock module if locked
            if self.module_state() == 'locked':
                self.module_state.unlock()

    def set_up_image_scan(self, size, extent, axes, sample_frequency):
        """

        @param size:
        @param extent:
        @param sample_frequency:
        @param axes:
        @return:
        """
        with self._lock:
            if self.module_state() != 'idle':
                self.log.error('Module is not idle. Unable to set up image scan.')
                return True

            new_scan_image = ScanImage(
                extent=extent,
                size=size,
                ax_names=axes,
                ax_cfg=(self._axes_configuration[axes[0]], self._axes_configuration[axes[1]]),
                sample_frequency=sample_frequency,
                analog_channels=tuple(self._analog_in_channels),
                count_channels=tuple(self._counter_channels))

            # Clean up any lingering tasks and other references
            self.terminate_image_scan()

            # Initialize scan parameters and data container
            self._scan_image = new_scan_image

            self._clock_task = self._task_manager.get_clock_task(
                name='ImgScanPxClk_{0:d}'.format(id(self)),
                frequency=self._scan_image.sample_frequency,
                cycles=self._scan_image.voltage_path.shape[1],
                device=self._device_name,
                idle_high=False)
            if self._clock_task is None:
                self.log.error('Failed to set up sample clock task.')
                self.terminate_image_scan()
                return True
            clock_channel = '/{0}InternalOutput'.format(self._clock_task.channel_names[0])

            ao_channels = (self._axes_configuration[axes[0]]['ao_channel'],
                           self._axes_configuration[axes[1]]['ao_channel'])
            self._analog_out_task, self._analog_writer = self._task_manager.get_analog_out_task(
                name='ImgScanAnalogOut_{0:d}'.format(id(self)),
                channels=ao_channels,
                clk_terminal=clock_channel,
                clk_freq=self._scan_image.sample_frequency,
                samples=self._scan_image.voltage_path.shape[1],
                device=self._device_name,
                active_falling=False,
                min_vals=None,
                max_vals=None,
                buffer_size=1048576)
            if self._analog_out_task is None or self._analog_writer is None:
                self.log.error('Failed to set up analog output task.')
                self.terminate_image_scan()
                return True
            self._analog_out_task.register_done_event(self.__scan_done_callback)

            if self._counter_channels:
                for ii, terminal in enumerate(self._counter_channels.values()):
                    task, reader = self._task_manager.get_counting_task(
                        name='ImgScanCtr{0:d}_{1:d}'.format(ii, id(self)),
                        channel=terminal,
                        clk_terminal=clock_channel,
                        clk_freq=self._scan_image.sample_frequency,
                        samples=self._scan_image.samples_per_channel,
                        device=self._device_name,
                        active_falling=False,
                        min_val=0,
                        max_val=100000000,
                        buffer_size=1048576)
                    if task is None or reader is None:
                        self.log.error('Failed to set up digital counting tasks.')
                        self.terminate_image_scan()
                        return
                    self._counter_tasks.append(task)
                    self._counter_readers.append(reader)

            if self._analog_in_channels:
                self._analog_in_task, self._analog_reader = self._task_manager.get_analog_in_task(
                    name='ImgScanAnalogIn_{0:d}'.format(id(self)),
                    channels=tuple(self._analog_in_channels.values()),
                    clk_terminal=clock_channel,
                    clk_freq=self._scan_image.sample_frequency,
                    samples=self._scan_image.samples_per_channel,
                    device=self._device_name,
                    active_falling=True,
                    min_val=-10.0,
                    max_val=10.0,
                    buffer_size=1048576)
                if self._analog_in_task is None or self._analog_reader is None:
                    self.log.error('Failed to set up analog input task.')
                    self.terminate_image_scan()
                    return True

            # FIXME: This is hardcoded
            self._task_manager.connect_terminals(source=clock_channel,
                                                 destination='/{0}/PFI7'.format(self._device_name))
            return False

    @QtCore.Slot()
    def start_image_scan(self):
        """

        @return bool: Error flag (True: error, False: OK)
        """
        with self._lock:
            if self.module_state() != 'idle':
                self.log.error('Module is not idle. Unable to start image scan.')
                return True
            if self._clock_task is None or self._analog_out_task is None:
                self.log.error('Unable to start image scan. Please call set_up_image_scan first.')
                return True

            self._scan_image.reset()

            try:
                for task in self._counter_tasks:
                    task.start()
                if self._analog_in_task is not None:
                    self._analog_in_task.start()
                self._analog_writer.write_many_sample(self._scan_image.voltage_path)
                self._analog_out_task.start()
                self._last_read_time = time.time()
                self._clock_task.start()
            except ni.DaqError:
                self.log.exception('Something went wrong while trying to start image scan tasks. '
                                   'Aborting image scan. Set up new image scan before trying to'
                                   ' call start_image_scan again.')
                self.terminate_image_scan()
                return True
            self.module_state.lock()
            return False

    def get_scan_data(self):
        with self._lock:
            if not self._scan_image.is_done:
                self._read_buffer_data()
            return self._scan_image.scan_image_dict

    def get_backscan_data(self):
        with self._lock:
            if not self._scan_image.is_done:
                self._read_buffer_data()
            return self._scan_image.backscan_image_dict

    @QtCore.Slot()
    def _read_buffer_data(self):
        with self._lock:
            if self.module_state() != 'locked' or self._scan_image.is_done:
                self.log.warning('Image scan is either stopped or already completed. '
                                 'Reading data from buffer skipped.')
                return
            curr_time = time.time()
            elapsed_time = curr_time - self._last_read_time
            self._last_read_time = curr_time
            samples_to_read = int(round(elapsed_time * self._scan_image.sample_frequency))
            samples_to_read = min(samples_to_read, self._scan_image.missing_samples)
            timeout = max(1.0, elapsed_time)
            with self._scan_image.lock:
                for ch, reader in enumerate(self._counter_readers):
                    offset = ch * self._scan_image.samples_per_channel + self._scan_image.samples_read
                    samples_read = reader.read_many_sample_double(
                        data=self._scan_image.raw_count_data[offset:],
                        number_of_samples_per_channel=samples_to_read,
                        timeout=timeout)
                    if samples_to_read != samples_read:
                        self.log.error('Samples read process failed for counting task.')
                        return

                if self._analog_reader is not None:
                    offset = self._scan_image.samples_read
                    buffer = np.zeros(
                        (self._scan_image.raw_analog_data.shape[0], samples_to_read))
                    samples_read = self._analog_reader.read_many_sample(
                        data=buffer,
                        number_of_samples_per_channel=samples_to_read,
                        timeout=timeout)
                    if samples_to_read != samples_read:
                        self.log.error('Samples read process failed for analog-in task.')
                        return
                    self._scan_image.raw_analog_data[:, offset:offset + samples_read] = buffer[:, :samples_read]

                self._scan_image.missing_samples -= samples_to_read
                print('READ_SAMPLES:', samples_to_read, self._scan_image.missing_samples)
                return

    def __check_axes_configuration(self):
        """
        """
        ao_channel_set = set()  # Remember which ao channels are already assigned an axis
        available_ao_channels = set(self._task_manager.analog_out_terminals[self._device_name])
        for axis, cfg in self._axes_configuration.items():
            if any(key not in cfg for key in ('voltage_range', 'ao_channel', 'position_range')):
                raise KeyError('Axis configuration must contain mandatory keywords "voltage_range",'
                               ' "ao_channel" and "position_range".')

            # ToDo: Check value ranges with device constraints here

            if any(len(cfg[key]) != 2 for key in ('voltage_range', 'position_range')):
                raise ValueError('Axis position and voltage range must be iterable of length 2.')

            ao_channel = self._extract_term(cfg['ao_channel'])
            for def_term in available_ao_channels:
                if re.match(ao_channel, def_term, re.IGNORECASE):
                    ao_channel = def_term
                    break
            if ao_channel in ao_channel_set:
                raise ValueError('Analog out channel "{0}" for axis "{1}" is already assigned to '
                                 'different axis.'.format(ao_channel, axis))
            ao_channel_set.add(ao_channel)
            if ao_channel not in available_ao_channels:
                raise NameError('Analog out channel "{0}" specified in config for axis "{1}" not '
                                'found in device channels.'.format(ao_channel, axis))
            cfg['ao_channel'] = ao_channel

            if 'overscan' in cfg:
                if not isinstance(cfg['overscan'], int) or cfg['overscan'] < 0:
                    raise ValueError('Overscan parameter must be integer value >= 0.')
            else:
                cfg['overscan'] = 0

            cfg['position_range'] = (min(cfg['position_range']), max(cfg['position_range']))
            cfg['voltage_range'] = (min(cfg['voltage_range']), max(cfg['voltage_range']))

    def __check_data_input_channels(self):
        """
        """
        # Check digital input channels
        if self._counter_channels:
            available_terminals = set(self._task_manager.pfi_terminals[self._device_name])
            for ch_name, terminal in self._counter_channels.copy().items():
                terminal = self._extract_term(terminal)
                for dev_term in available_terminals:
                    if re.match(terminal, dev_term, re.IGNORECASE):
                        self._counter_channels[ch_name] = dev_term
                        break
            configured_terminals = set(self._counter_channels.values())
            invalid_terminals = configured_terminals.difference(available_terminals)
            if invalid_terminals:
                self.log.error(
                    'Invalid digital source terminals encountered. Following sources will '
                    'be ignored:\n  {0}\nValid digital input terminals are:\n  {1}'
                    ''.format(invalid_terminals, available_terminals))
                for ch_name in tuple(self._counter_channels):
                    if self._counter_channels[ch_name] in invalid_terminals:
                        del self._counter_channels[ch_name]

        # Check analog input channels
        if self._analog_in_channels:
            available_terminals = set(self._task_manager.analog_in_terminals[self._device_name])
            for ch_name, terminal in self._analog_in_channels.copy().items():
                terminal = self._extract_term(terminal)
                for dev_term in available_terminals:
                    if re.match(terminal, dev_term, re.IGNORECASE):
                        self._analog_in_channels[ch_name] = dev_term
                        break
            configured_terminals = set(self._analog_in_channels.values())
            invalid_terminals = configured_terminals.difference(available_terminals)
            if invalid_terminals:
                self.log.error(
                    'Invalid analog source terminals encountered. Following sources will '
                    'be ignored:\n  {0}\nValid analog input terminals are:\n  {1}'
                    ''.format(invalid_terminals, available_terminals))
                for ch_name in tuple(self._analog_in_channels):
                    if self._analog_in_channels[ch_name] in invalid_terminals:
                        del self._analog_in_channels[ch_name]

        # Check if there are any valid input channels left
        if not self._analog_in_channels and not self._counter_channels:
            raise Exception('No valid analog or digital sources defined in config. Activation of '
                            'NiXSeriesAnalogScanner failed!')

        # Check if all input channels fit in the device
        if len(self._counter_channels) > 3:
            raise Exception(
                'Too many digital channels specified. Maximum number of digital channels is 3.')
        if len(self._analog_in_channels) > 16:
            raise Exception(
                'Too many analog channels specified. Maximum number of analog channels is 16.')

    def __scan_done_callback(self, *args, **kwargs):
        self._read_buffer_data()
        self.terminate_image_scan()
        return 0

    @staticmethod
    def _extract_term(term_str):
        """
        Helper function to extract the bare terminal name from a string and strip it of the device
        name and dashes.
        Will return the terminal name as it is.

        @param str term_str: The str to extract the terminal name from
        @return str: The terminal name
        """
        return term_str.strip('/').rsplit('/', 1)[-1]
