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
                                       'status': InternalState.free}

        self._current_position = dict()
        self._points = dict()
        self._num_points = 500

        self._acquisition_frequency = 1000
        self._sampling_length = 100
        self._continuous_acquisition = True
        self._data_generation_timer = QTimer()
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

        self._data_generation_timer.timeout.connect(self._internal_generate_data)

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

    def initialize(self, acquisition_frequency=None, sampling_length=None, continuous=None):
        """
        Set up timing and triggers
        """
        if acquisition_frequency is not None:
            self._acquisition_frequency = acquisition_frequency
        if sampling_length is not None:
            self._sampling_length = sampling_length
        if continuous is not None:
            self._continuous_acquisition = continuous
        for key in self._channels:
            if self._channels[key]['status'] is InternalState.locked:
                self.log.error('The following channel is locked '
                               'and can therefore not be initialized: {0:s}'.format(key))
            else:
                self._channels[key]['status'] = InternalState.initialized

    def set_sampling_rate(self, sampling_rate):
        """
        Set the sampling rate for one or multiple data acquisition channels.

        @param float sampling_rate: The sampling rate defines the acquisition frequency of the hardware module.
                                    Sampling rate is always in samples/s.

        @return float: the actually set sampling rate
        """

        for key in self._channels:
            if self._channels[key] is InternalState.locked:
                self.log.error('Cannot set sampling rate because the following channel is locked: {0:s}'.format(key))

        self._acquisition_frequency = sampling_rate
        return self._acquisition_frequency

    def get_sampling_rate(self):
        """
        Gets the current sampling rate for the acquisition frequency of the hardware module.


        @return float: the sampling rate.
        """
        return self._acquisition_frequency

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
            self._raw_data[key] = list()
            if self._channels[key] is not InternalState.initialized:
                self.log.error('Could not start the measurement, '
                               'because the following channels was not initialized: {0:s}'.format(key))

        self._data_generation_timer.start(int(1000/self._acquisition_frequency))

    def _internal_generate_data(self):
        """
        This is an internal functions that generates the data for the DataAcquisitionInterface
        @return void: nothing
        """
        data_acquisition_done = False

        for key in self._channels:
            self._raw_data[key].append(np.random.uniform(self._channels[key]['range_min'],
                                                         self._channels[key]['range_max'],
                                                         1))
            if not self._continuous_acquisition and len(self._raw_data[key]) > self._sampling_length:
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
        self._data_generation_timer.stop()
        for key in self._channels:
            self._channels[key]['status'] = InternalState.idle

    def get_data(self):
        """
        Returns the last recorded data set

        @return dict: With keys being the channel label and items being the data arrays
        """

        stop_triggered = False
        data_length = len(self._raw_data[0])

        while ((data_length < self._sampling_length)
                and not stop_triggered):
            for key in self._channels:
                if self._channels[key]['status'] is not InternalState.locked:
                    stop_triggered = True
            time.sleep((1000/self._acquisition_frequency) * (self._sampling_length - data_length) / 2)
            data_length = len(self._raw_data[0])

        data_length = len(self._raw_data[0])
        return_data = dict()
        for key in self._channels:
            return_data[key] = np.zeros(self._sampling_length)
            return_data[key][:min(data_length,
                                  self._sampling_length)] = self._raw_data[key][:min(data_length,
                                                                                     self._sampling_length)]
            del self._raw_data[key][:min(data_length, self._sampling_length)]

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
