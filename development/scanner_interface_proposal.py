# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interfaces for scanning devices.

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

import abc
from core.util.interfaces import InterfaceMetaclass


class PositionerInterface(metaclass=InterfaceMetaclass):
    """
    Large parts were taken from the current motor_interface.py

    This is the Interface class to define the controls for a simple "move-from-A-to-B" positioner
    hardware (e.g. motorized stages, piezo scanners etc.). This device class is only capable to move
    from the current position to a certain point in a not strictly defined path.
    One does only define the target position and a moving velocity (units per second).
    """

    _modtype = 'PositionerInterface'
    _modclass = 'interface'

    @abc.abstractmethod
    def on_activate(self):
        pass

    @abc.abstractmethod
    def on_deactivate(self):
        pass

    @abc.abstractmethod
    def get_constraints(self):
        """
        Return a dictionary containing the constraints for each parameter that can be set in this
        hardware. See other hardware modules to get the idea.
        """
        pass

    @abc.abstractmethod
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
        pass

    @abc.abstractmethod
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
        pass

    @abc.abstractmethod
    def get_position(self, axes_list=None):
        """ Gets current position of the device

        @param list axes_list: optional, if a specific position of an axis is desired, then the
                               labels of the needed axis should be passed in the axes_list.
                               If nothing is passed, then from each axis the position is asked.

        @return dict: with keys being the axis labels and item the current position.
        """
        pass

    @abc.abstractmethod
    def get_target(self, axes_list=None):
        """ Gets current target position of the device

        @param list axes_list: optional, if a specific target position of an axis is desired, then
                               the labels of the needed axis should be passed in the axes_list.
                               If nothing is passed, then from each axis the target is asked.

        @return dict: with keys being the axis labels and item the current target position.
        """
        pass

    @abc.abstractmethod
    def get_status(self, axes_list=None):
        """ Get the status of the position

        @param list axes_list: optional, if a specific status of an axis is desired, then the
                               labels of the needed axis should be passed in the axes_list.
                               If nothing is passed, then from each axis the status is asked.

        @return dict: with the axis label as key and the status number as item.
        """
        pass

    @abc.abstractmethod
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
        pass

    @abc.abstractmethod
    def get_velocity(self, axes_list=None):
        """ Gets the current velocity for all connected axes.

        @param dict axes_list: optional, if a specific velocity of an axis is desired, then the
                               labels of the needed axis should be passed as the axes_list.
                               If nothing is passed, then from each axis the velocity is asked.

        @return dict : with the axis label as key and the velocity as item.
        """
        pass

    @abc.abstractmethod
    def set_velocity(self, velocity):
        """ Write new value for velocity.

        @param dict velocity:    dictionary, with keys being the axis label and items being the
                                velocity to set. Velocity is always measured in unit/s.

                                Usage:    {'axis_label': <the-velocity-value>}.
                                'axis_label' must correspond to a label given to one axis.

        @return dict: the actually set velocities
        """
        pass

    @abc.abstractmethod
    def abort(self):
        """ Stops movement of the positioner asap.

        @return int: error code (0:OK, -1:error)
        """
        pass
    
        
class DataAcquisitionInterface(metaclass=InterfaceMetaclass):
    """
    This is the Interface class to define the controls for a data acquisition device (e.g. A/D converter).
    This device class should be capable to record a data array from certain input channels given
    the sample rate and a synchronization/timing configuration (i.e. external trigger,
    immediate record, etc.).
    """

    _modtype = 'DataAcquisitionInterface'
    _modclass = 'interface'

    @abc.abstractmethod
    def on_activate(self):
        pass

    @abc.abstractmethod
    def on_deactivate(self):
        pass

    @abc.abstractmethod
    def get_constraints(self):
        """
        Return a dictionary containing the constraints for each parameter that can be set in this
        hardware. See other hardware modules to get the idea.
        """
        pass

    @abc.abstractmethod
    def initialize(self, stuff):
        """
        Set up timing and triggers
        """
        pass

    @abc.abstractmethod
    def set_sampling_rate(self, sampling_rate):
        """
        Set the sampling rate for one or multiple data acquisition channels.

        @param dict sampling_rate: dictionary, with keys being the channel label and items being the
                                   sampling rate to set. Sampling rate is always in samples/s.

                                   Usage: {'channel_label': <the-sampling-rate-value>}.
                                   'channel_label' must correspond to a label given to one channel.

        @return dict: the actually set sampling rates
        """

    @abc.abstractmethod
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
        pass

    @abc.abstractmethod
    def start(self):
        """
        Start the data acquisition.
        If the data should be recorded immediately this will acquire the data asap.
        If the device is somehow synchronized with a trigger or such then this method will "arm"
        the data acquisition to listen to triggers etc.

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def stop(self):
        """
        Stop the data acquisition early.
        The acquisition will stop automatically if all samples have been recorded but this method
        can stop the device manually.

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def get_data(self):
        """
        Returns the last recorded data set

        @return dict: With keys being the channel label and items being the data arrays
        """
        pass

    @abc.abstractmethod
    def set_data_channels(self, data_channels):
        """
        Set the active data channels to be used by the device.
        The channels provided in "data_channels" must be available (check hardware constraints).

        @param list data_channels: A list of channel labels to be active in the next acquisition

        @return list: Actually active data channels
        """
        pass

    @abc.abstractmethod
    def get_data_channels(self):
        """
        Returns a list of active channel labels.

        @return list: Currently active data channels
        """
        pass


class ScannerInterface(metaclass=InterfaceMetaclass):
    """
    This is the Interface class to define the controls for a scanning device.
    This device class should be capable to move along a defined sequence of positions (path) an
    record data at each position.
    """

    _modtype = 'ScannerInterface'
    _modclass = 'interface'

    @abc.abstractmethod
    def on_activate(self):
        pass

    @abc.abstractmethod
    def on_deactivate(self):
        pass

    @abc.abstractmethod
    def get_constraints(self):
        """
        Return a dictionary containing the constraints for each parameter that can be set in this
        hardware. See other hardware modules to get the idea.
        """
        pass

    @abc.abstractmethod
    def set_path(self, path):
        """
        Sets a path the scanner should move along in the scan.
        Move from point to point with the set clock frequency.

        @param dict path: dictionary with keys being the axis label and items being the position
                          array.

        @return dict: The actually set path
        """
        pass

    @abc.abstractmethod
    def get_path(self, axes_list=None):
        """
        Returns the currently set scanning path.
        If no axes_list is given, this method will return the path for all axes.

        @param list axes_list: optional, list containing the axis labels to ask for.

        @return dict: dictionary with keys being the axis label and items being the position array.
        """
        pass

    @abc.abstractmethod
    def set_up_synchronization(self, *args, **kwargs):
        """
        Much Voodoo going on here.
        This method should in principle handle setting up the synchronization between movement
        device and the data acquisition device.
        One must mainly answer the question about who is the timing master and set this up.
        """
        pass

    @abc.abstractmethod
    def set_data_channels(self, data_channels):
        """
        Set the active data channels to be used by the device.
        The channels provided in "data_channels" must be available (check hardware constraints).

        @param list data_channels: A list of channel labels to be active in the next acquisition

        @return list: Actually active data channels
        """
        pass

    @abc.abstractmethod
    def get_data_channels(self):
        """
        Returns a list of active channel labels.

        @return list: Currently active data channels
        """
        pass

    @abc.abstractmethod
    def start_scan(self, path=None, data_channels=None):
        """
        Starts a scan along the given "path" and collect data at each position from each of the
        "data_channels" provided.
        If no path/data_channels is given, the previously set path/data_channels will be used.

        @param dict path: See "ScannerInterface.set_path"
        @param list data_channels: See "ScannerInterface.set_data_channels"

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def get_data(self):
        """
        Will return a set of real positions with corresponding data points
        (as many as data channels used).
        If the device has no position feedback, this will return the target path data.

        @return tuple: the real path data array, dictionary containing the channel data arrays
        """
        pass

    @abc.abstractmethod
    def start_move(self, path=None):
        """
        Starts a movement without collecting data along the given "path".
        Basicaly the same as start_scan but without data acquisition.
        If no path is given, the previously set path will be used.

        @param dict path: See "ScannerInterface.set_path"

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def stop(self):
        """
        Stops a scan/movement early.
        Scans/Movements will otherwise stop automatically when they complete their path.

        @return int: error code (0: OK, -1: error)
        """
        pass
