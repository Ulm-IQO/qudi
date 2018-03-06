# -*- coding: utf-8 -*-

"""
This file contains the Qudi dummy module for the confocal scanner.

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
import time

from qtpy.QtCore import QTimer
from core.module import Base, Connector, ConfigOption
from development.scanner_interface_proposal import PositionerInterface, DataAcquisitionInterface, ScannerInterface
from enum import Enum
from functools import partial


class InternalState(Enum):
    free = 0
    idle = 1
    initialized = 2
    locked = 3


class ConfocalScannerDummy(Base, PositionerInterface, DataAcquisitionInterface, ScannerInterface):
    """ Dummy confocal scanner.
        Produces a picture with several gaussian spots.
    """
    _modclass = 'ConfocalScannerDummy'
    _modtype = 'hardware'

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # Internal parameters
        self._axes = dict()
        self._axes['axis_1'] = {'name': 'axis_x', 'unit': 'm', 'range_min': 0, 'range_max': 100e-6,
                                'status': InternalState.free, 'velocity': 0}
        self._axes['axis_2'] = {'name': 'axis_y', 'unit': 'm', 'range_min': 0, 'range_max': 100e-6,
                                'status': InternalState.free, 'velocity': 0}
        self._axes['axis_3'] = {'name': 'axis_z', 'unit': 'm', 'range_min': -50e-6, 'range_max': 50e-6,
                                'status': InternalState.free, 'velocity': 0}

        self._channels = dict()
        self._channels['channel_1'] = {'name': 'Analogue_IN', 'unit': 'V', 'range_min': 0, 'range_max': 10,
                                       'status': InternalState.free, 'sampling_rate': 100}

        self._current_position = dict()
        self._points = dict()
        self._num_points = 500

        self._continuous_acquisition = True
        self._common_timing = False
        self._data_generation_timer = dict()
        self._sampling_length = 100
        self._raw_data = list()

    def on_activate(self):

        self._points['amplitude'] = np.random.normal(4e5, 1e5, self._num_points)
        self._points['theta'] = np.ones(self._num_points) * 10.
        self._points['offset'] = np.zeros(self._num_points)

        for key in self._axes:
            self._points[key] = np.random.normal(self._axes[key]['range_min'],
                                                 self._axes[key]['range_max'],
                                                 self._num_points)
            self._points['sigma_{0:s}'.format(key)] = np.random.normal(0.7e-6, 0.1e-6, self._num_points)
            self._current_position[key] = 0

    def on_deactivate(self):
        pass

    def get_constraints(self):
        """
        Return a dictionary containing the constraints for each parameter that can be set in this
        hardware. See other hardware modules to get the idea.
        """
        return self._axes.update(self._channels)

    #
    #   PositionerInterface
    #

    def move_to(self, position, velocity=None):
        """
        Moves stage to absolute position (absolute movement)
        The velocity is optional since it can be globally set for this device.
        Exact path can vary depending on starting point and hardware used.

        @param dict position: dictionary, which passes the new positions for desired axes.
                              Usage: {'axis_label': <the-abs-pos-value>}.
                              'axis_label' must correspond to a label given to one of the axis.
        @param dict velocity: dictionary, which passes the new velocities for desired axes.
                              Usage: {'axis_label': <the-velocity-value>}.
                              'axis_label' must correspond to a label given to one of the axis.
                              Velocity is measured in unit/s.

        @return int: error code (0:OK, -1:error)
        """

        if isinstance(position, dict):
            for key in position:
                if key not in self._axes.keys():
                    self.log.error('The following axis could not been found: {0:s}'.format(key))
                elif not (self._axes[key]['range_min'] <= position[key] <= self._axes[key]['range_max']):
                    self.log.error('The position set does not confirm to axis constraints: {0:f} -> ({1:f},{2:f})'.
                                   format(position[key], self._axes[key]['range_min'], self._axes[key]['range_max'])
                                   )
                elif self._axes[key]['status'] not in (InternalState.free, InternalState.idle):
                    self.log.error('The following axis could not be changed, since it is in use: {0:s}'.format(key))
                else:
                    self._current_position[key] = position[key]
            return 0
        else:
            self.log.error('Position needs to be a dictionary.')
            return -1

    def move_relative(self, rel_position, velocity=None):
        """ Moves positioner in given direction (relative movement)

        @param dict rel_position: dictionary, which passes the axis as key and relative position as
                                  item.
                                  Usage: {'axis_label': <the-relative-pos-value>}.
                                  'axis_label' must correspond to a label given to one of the axis.
        @param dict velocity: dictionary, which passes the new velocities for desired axes.
                              Usage: {'axis_label': <the-velocity-value>}.
                              'axis_label' must correspond to a label given to one of the axis.
                              Velocity is measured in unit/s.

        A smart idea would be to ask the position after the movement.

        @return int: error code (0:OK, -1:error)
        """

        if isinstance(rel_position, dict):
            for key in rel_position:
                if key not in self._axes.keys():
                    self.log.error('The following axis could not been found: {0:s}'.format(key))
                elif not (self._axes[key]['range_min'] <= self._current_position[key] + rel_position[key]
                          <= self._axes[key]['range_max']):
                    self.log.error('The position set does not confirm to axis constraints: {0:f} -> ({1:f},{2:f})'.
                                   format(self._current_position[key] + rel_position[key],
                                          self._axes[key]['range_min'],
                                          self._axes[key]['range_max'])
                                   )
                elif self._axes[key]['status'] not in (InternalState.free, InternalState.idle):
                    self.log.error('The following axis could not be changed, since it is in use: {0:s}'.format(key))
                else:
                    self._current_position[key] += rel_position[key]
            return 0
        else:
            self.log.error('Position needs to be a dictionary.')
            return -1

    def get_position(self, axes_list=None):
        """ Gets current position of the device

        @param list axes_list: optional, if a specific position of an axis is desired, then the
                               labels of the needed axis should be passed in the axes_list.
                               If nothing is passed, then from each axis the position is asked.

        @return dict: with keys being the axis labels and item the current position.
        """
        return self._current_position

    def get_target(self, axes_list=None):
        """ Gets current target position of the device

        @param list axes_list: optional, if a specific target position of an axis is desired, then
                               the labels of the needed axis should be passed in the axes_list.
                               If nothing is passed, then from each axis the target is asked.

        @return dict: with keys being the axis labels and item the current target position.
        """
        return self._current_position

    def get_status(self, axes_list=None):
        """ Get the status of the position

        @param list axes_list: optional, if a specific status of an axis is desired, then the
                               labels of the needed axis should be passed in the axes_list.
                               If nothing is passed, then from each axis the status is asked.

        @return dict: with the axis label as key and the status number as item.
        """

        status = dict()

        if axes_list is not None:
            if isinstance(axes_list, list):
                for key in axes_list:
                    if key not in self._axes.keys():
                        self.log.error('The following axis could not been found: {0:s}'.format(key))
                    else:
                        status[key] = self._axes[key]['status']
                if len(status) > 0:
                    return status
            else:
                self.log.error('Parameter axes_list needs to be a list.')

        for key in self._axes:
            status[key] = self._axes[key]['status']
        return status

    def calibrate(self, axes_list=None):
        """ Calibrates the positioner.

        @param dict axes_list: param_list: optional, if a specific calibration of an axis is
                               desired, then the labels of the needed axis should be passed in the
                               axes_list. If nothing is passed, then all connected axis will be
                               calibrated.

        @return int: error code (0:OK, -1:error)

        After calibration the positioner moves to home position which will be the zero point for the
        passed axis. The calibration procedure will be different in general for each device.
        """
        self.log.warn('ConfocalScannerDummy has no calibration.')
        return 0

    def get_velocity(self, axes_list=None):
        """ Gets the current velocity for all connected axes.

        @param dict axes_list: optional, if a specific velocity of an axis is desired, then the
                               labels of the needed axis should be passed as the axes_list.
                               If nothing is passed, then from each axis the velocity is asked.

        @return dict : with the axis label as key and the velocity as item.
        """

        velocity = dict()

        if axes_list is not None:
            if isinstance(axes_list, list):
                for key in axes_list:
                    if key not in self._axes.keys():
                        self.log.error('The following axis could not been found: {0:s}'.format(key))
                    else:
                        velocity[key] = self._axes[key]['velocity']
                if len(velocity) > 0:
                    return velocity
            else:
                self.log.error('Parameter axes_list needs to be a list.')

        for key in self._axes:
            velocity[key] = self._axes[key]['velocity']
        return velocity

    def set_velocity(self, velocity):
        """ Write new value for velocity.

        @param dict velocity:    dictionary, with keys being the axis label and items being the
                                velocity to set. Velocity is always measured in unit/s.

                                Usage:    {'axis_label': <the-velocity-value>}.
                                'axis_label' must correspond to a label given to one axis.

        @return dict: the actually set velocities
        """

        if isinstance(velocity, dict):
            for key in velocity:
                if key not in self._axes.keys():
                    self.log.error('The following axis could not been found: {0:s}'.format(key))
                else:
                    self._axes[key]['velocity'] = velocity[key]
        else:
            self.log.error('Parameter velocity needs to be a dictionary.')

        current_velocity = dict()
        for key in self._axes:
            current_velocity[key] = self._axes[key]['velocity']
        return current_velocity

    def abort(self):
        """ Stops movement of the positioner asap.

        @return int: error code (0:OK, -1:error)
        """

        self.log.warn('ConfocalScannerDummy has no abort.')

    #
    #   DataAcquisitionInterface
    #

    def initialize(self, sampling_length=None, continuous=None, common_timing=None):
        """
        Set up timing and triggers
        """
        if sampling_length is not None:
            self._sampling_length = sampling_length
        if continuous is not None:
            self._continuous_acquisition = continuous
        if common_timing is not None:
            self._common_timing = common_timing
        for key in self._channels:
            if self._channels[key]['status'] is InternalState.locked:
                self.log.error('The following channel is locked '
                               'and can therefore not be initialized: {0:s}'.format(key))
            else:
                self._data_generation_timer[key] = QTimer()
                self._data_generation_timer[key].timeout.connect(partial(self._internal_generate_data, key))
                self._channels[key]['status'] = InternalState.initialized

    def set_sampling_rate(self, sampling_rate):
        """
        Set the sampling rate for one or multiple data acquisition channels.
        @param dict sampling_rate: dictionary, with keys being the channel label and items being the
                                   sampling rate to set. Sampling rate is always in samples/s.
                                   Usage: {'channel_label': <the-sampling-rate-value>}.
                                   'channel_label' must correspond to a label given to one channel.
        @return dict: the actually set sampling rates
        """
        if isinstance(sampling_rate, dict):
            if self._common_timing:
                self.log.debug('Common timing applies: setting sampling rate of ALL channels to {0:f}'.
                               format(sampling_rate[0]))
                for key in self._channels:
                    self._channels[key]['sampling_rate'] = sampling_rate[0]
            else:
                for key in sampling_rate:
                    if key not in self._channels.keys():
                        self.log.error('The following channel could not been found: {0:s}'.format(key))
                    elif self._channels[key] is InternalState.locked:
                        self.log.error('Cannot set sampling rate because the following channel is locked: {0:s}'.format(key))
                    else:
                        self._channels[key]['sampling_rate'] = sampling_rate[key]
        else:
            self.log.error('Parameter sampling_rate needs to be a dictionary.')

        internal_sampling_rate = dict()
        for key in self._channels:
            internal_sampling_rate[key] = self._channels[key]['sampling_rate']

        return internal_sampling_rate

    def get_sampling_rate(self, channel_list=None):
        """
        Gets the current sampling rate for all connected channels.
        @param dict channel_list: optional, if a specific sampling rate of a channel is desired,
                                  then the labels of the needed channels should be passed in the
                                  channel_list.
                                  If nothing is passed, then from each channel the sampling rate is
                                  returned.
        @return dict: with the channel label as key and the sampling rate as item.
        """
        internal_sampling_rate = dict()

        if channel_list is not None:
            if isinstance(channel_list, list):
                for key in channel_list:
                    if key not in self._channels.keys():
                        self.log.error('The following channel could not been found: {0:s}'.format(key))
                    else:
                        internal_sampling_rate[key] = self._channels[key]['sampling_rate']
                if len(internal_sampling_rate) > 0:
                    return internal_sampling_rate
            else:
                self.log.error('Parameter channel_list needs to be a list.')

        for key in self._channels:
            internal_sampling_rate[key] = self._channels[key]['sampling_rate']

        return internal_sampling_rate

    def start(self):
        """
        Start the data acquisition.
        If the data should be recorded immediately this will acquire the data asap.
        If the device is somehow synchronized with a trigger or such then this method will "arm"
        the data acquisition to listen to triggers etc.

        @return int: error code (0:OK, -1:error)
        """

        self._raw_data = dict()

        for key in self._channels:
            if self._channels[key] is not InternalState.initialized:
                self.log.error('Could not start the measurement, '
                               'because the following channels was not initialized: {0:s}'.format(key))
                return -1
            self._raw_data[key] = list()
            self._data_generation_timer[key].start(int(1000/self._channels[key]['sampling_rate']))

    def _internal_generate_data(self, channel_key=None):
        """
        This is an internal functions that generates the data for the DataAcquisitionInterface
        @return void: nothing
        """
        data_acquisition_done = False

        if channel_key is None:
            self.log.error('No channel given to acquire data to.')
            self.stop()
            return
        elif channel_key not in self._channels.keys():
            self.log.error('Cannot acquire data for the following channel because it does not exist: {0:s}'.
                           format(channel_key))
        else:
            self._raw_data[channel_key].append(np.random.uniform(self._channels[channel_key]['range_min'],
                                                                 self._channels[channel_key]['range_max'],
                                                                 1))
            if not self._continuous_acquisition and len(self._raw_data[channel_key]) > self._sampling_length:
                data_acquisition_done = True
        if data_acquisition_done:
            self.stop()

    def stop(self):
        """
        Stop the data acquisition early.
        The acquisition will stop automatically if all samples have been recorded but this method
        can stop the device manually.

        @return int: error code (0:OK, -1:error)
        """
        for key in self._channels:
            self._data_generation_timer[key].stop()
            self._channels[key]['status'] = InternalState.idle

    def get_data(self, sample_number=None):
        """
        Returns the last recorded data set
        @param dict/int sample_number: (optional) define how many samples should be acquired per channel.
                                   Option 1: Usage: {'channel_label': <number-of-samples-value>}.
                                        'channel_label' must correspond to a label given to one channel.
                                        This gives a different sample number to each channel.
                                        The function is blocking: it waits until the required sample number was acquired
                                   Option 2: Usage: int <number-of-samples-value-for-all-channels>
                                        This gives the same sample number to all channels.
                                        The function is blocking: it waits until the required sample number was acquired
                                   Option 3: If no sample_number is given, this function is non-blocking
                                        and returns however many samples were acquired.
        @return dict: With keys being the channel label and items being the data arrays
        """

        stop_triggered = False

        for key in self._channels:
            if self._channels[key]['status'] is not InternalState.locked:
                stop_triggered = True

        return_data = dict()
        return_length = dict()
        for key in self._channels:
            if stop_triggered or sample_number is None:
                return_length[key] = len(self._raw_data[key])
            else:
                if isinstance(sample_number, dict):
                    if key not in sample_number:
                        self.log.warn('No sample number found for the following channel: {0:s}'.format(key))
                        return_length[key] = len(self._raw_data[key])
                    else:
                        return_length[key] = int(sample_number[key])
                else:
                    return_length[key] = int(sample_number)

                # wait for the data to be available
                while ((len(self._raw_data[key]) < return_length[key])
                       and not stop_triggered):
                    time.sleep(1000 / self._channels[key]['sampling_rate'])

            return_data[key] = np.zeros(return_length[key])
            return_data[key] = self._raw_data[key][:return_length[key]]
            del self._raw_data[key][:return_length[key]]

        return return_data

    def set_data_channels(self, data_channels):
        """
        Set the active data channels to be used by the device.
        The channels provided in "data_channels" must be available (check hardware constraints).

        @param list data_channels: A list of channel labels to be active in the next acquisition

        @return list: Actually active data channels
        """

        for key in data_channels:
            if key not in self._channels.keys():
                self.log.error('The following channel could not been found: {0:s}'.format(key))

        for key in self._channels:
            if self._channels[key]['status'] is InternalState.locked and key not in data_channels:
                self.log.error('Cannot free the following channels, since it is locked: {0:s}'.format(key))
            elif key not in data_channels:
                self._channels[key]['status'] = InternalState.free
            elif self._channels[key]['status'] is InternalState.free:
                self._channels[key]['status'] = InternalState.idle

        internal_data_channels = list()
        for key in self._channels:
            if self._channels[key]['status'] is not InternalState.free:
                internal_data_channels.append(key)
        return internal_data_channels

    def get_data_channels(self):
        """
        Returns a list of active channel labels.

        @return list: Currently active data channels
        """
        data_channels = list()
        for key in self._channels:
            if self._channels[key]['status'] is not InternalState.free:
                data_channels.append(key)
        return data_channels
