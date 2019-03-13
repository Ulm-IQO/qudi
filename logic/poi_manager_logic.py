# -*- coding: utf-8 -*-
"""
This module contains a POI Manager core class which gives capability to mark
points of interest, re-optimise their position, and keep track of sample drift
over time.

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

import math
import os
import numpy as np
import scipy.ndimage as ndimage
import scipy.ndimage.filters as filters
import time

from collections import OrderedDict
from core.module import Connector, StatusVar
from datetime import datetime
from logic.generic_logic import GenericLogic
from qtpy import QtCore
from core.util.mutex import Mutex


class RegionOfInterest:
    """
    Class containing the general information about a specific region of interest (ROI),
    e.g. the sample drift history and the corresponding confocal image.
    Each individual point of interest (POI) will be represented as a PointOfInterest instance.
    The origin af a new ROI is always defined as (0,0,0) initially.
    Sample shifts will cause this origin to move to a different coordinate.
    The anchors of each individual POI is given relative to the initial ROI origin (even if added later).
    """

    def __init__(self, name=None, creation_time=None, history=None, scan_image=None,
                 scan_image_extent=None, poi_list=None):
        # Remember the creation time for drift history timestamps
        self._creation_time = None
        # Keep track of the global position history relative to the initial position (sample drift).
        # Each item is a float[4] array containing (time_in_s, x, y, z)
        self._pos_history = None
        # Optional scan image associated with this ROI
        self._scan_image = None
        # Optional initial scan image extent.
        self._scan_image_extent = None
        # Save name of the ROI. Create a generic, unambiguous one as default.
        self._name = None
        # dictionary of POIs contained in this ROI with keys being the name
        self._pois = dict()

        self.creation_time = creation_time
        self.name = name
        self.pos_history = history
        self.set_scan_image(scan_image, scan_image_extent)
        if poi_list is not None:
            for poi in poi_list:
                self.add_poi(poi)
        return

    @property
    def name(self):
        return str(self._name)

    @name.setter
    def name(self, new_name):
        if isinstance(new_name, str) and new_name:
            self._name = new_name
        elif new_name is None or new_name == '':
            self._name = self._creation_time.strftime('roi_%Y%m%d_%H%M_%S_%f')
        else:
            raise TypeError('ROI name to set must be None or of type str.')
        return

    @property
    def pos_history(self):
        return np.array(self._pos_history, dtype=float)

    @pos_history.setter
    def pos_history(self, new_history):
        if new_history is None:
            new_history = [np.zeros(4, dtype=float)]
        self._pos_history = list(new_history)
        if len(self._pos_history) == 0:
            self._pos_history.append(np.zeros(4, dtype=float))
        return

    @property
    def creation_time(self):
        return self._creation_time

    @property
    def creation_time_as_str(self):
        return datetime.strftime(self._creation_time, '%Y-%m-%d %H:%M:%S.%f')

    @creation_time.setter
    def creation_time(self, new_time):
        if not new_time:
            new_time = datetime.now()
        elif isinstance(new_time, str):
            new_time = datetime.strptime(new_time, '%Y-%m-%d %H:%M:%S.%f')
        if isinstance(new_time, datetime):
            self._creation_time = new_time
        return

    @property
    def origin(self):
        return np.array(self._pos_history[-1][1:], dtype=float)

    @property
    def scan_image(self):
        return self._scan_image

    @property
    def scan_image_extent(self):
        x, y, z = self.origin
        x_extent = (self._scan_image_extent[0][0] + x, self._scan_image_extent[0][1] + x)
        y_extent = (self._scan_image_extent[1][0] + y, self._scan_image_extent[1][1] + y)
        return x_extent, y_extent

    @property
    def poi_names(self):
        return list(self._pois)

    @property
    def poi_positions(self):
        origin = self.origin
        return {name: poi.position + origin for name, poi in self._pois.items()}

    @property
    def poi_anchors(self):
        return {name: poi.position for name, poi in self._pois.items()}

    def get_poi_position(self, name):
        if not isinstance(name, str):
            raise TypeError('POI name must be of type str.')
        if name not in self._pois:
            raise KeyError('No POI with name "{0}" found in POI list.'.format(name))
        return self._pois[name].position + self.origin

    def get_poi_anchor(self, name):
        if not isinstance(name, str):
            raise TypeError('POI name must be of type str.')
        if name not in self._pois:
            raise KeyError('No POI with name "{0}" found in POI list.'.format(name))
        return self._pois[name].position

    def set_poi_position(self, name, new_pos):
        if name not in self._pois:
            raise KeyError('POI with name "{0}" not found in ROI "{1}".\n'
                           'Unable to change POI position.'.format(name, self.name))
        self._pois[name].position = np.array(new_pos, dtype=float) - self.origin
        return

    def set_poi_anchor(self, name, new_pos):
        if name not in self._pois:
            raise KeyError('POI with name "{0}" not found in ROI "{1}".\n'
                           'Unable to change POI position.'.format(name, self.name))
        self._pois[name].position = new_pos
        return

    def rename_poi(self, name, new_name=None):
        if new_name is not None and not isinstance(new_name, str):
            raise TypeError('POI name to set must be of type str or None.')
        if name not in self._pois:
            raise KeyError('Name "{0}" not found in POI list.'.format(name))
        self._pois[name].name = new_name
        self._pois[new_name] = self._pois.pop(name)
        return

    def add_poi(self, position, name=None):
        position = position - self.origin
        poi_inst = PointOfInterest(position=position, name=name)
        if poi_inst.name in self._pois:
            raise ValueError('POI with name "{0}" already present in ROI "{1}".\n'
                             'Could not add POI to ROI'.format(poi_inst.name, self.name))
        self._pois[poi_inst.name] = poi_inst
        return

    def delete_poi(self, name):
        if not isinstance(name, str):
            raise TypeError('POI name to delete must be of type str.')
        if name not in self._pois:
            raise KeyError('Name "{0}" not found in POI list.'.format(name))
        del self._pois[name]
        return

    def set_scan_image(self, image_arr, image_extent):
        """

        @param scalar[][] image_arr:
        @param float[2][2] image_extent:
        """
        if image_arr is None:
            self._scan_image = None
            self._scan_image_extent = None
        else:
            roi_x_pos, roi_y_pos, roi_z_pos = self.origin
            x_extent = (image_extent[0][0] - roi_x_pos, image_extent[0][1] - roi_x_pos)
            y_extent = (image_extent[1][0] - roi_y_pos, image_extent[1][1] - roi_y_pos)
            self._scan_image = np.array(image_arr)
            self._scan_image_extent = (x_extent, y_extent)
        return

    def add_history_entry(self, new_pos):
        """
        Add a new entry to the ROI position history and tag it with the current time.

        @param float[3] new_pos: Position coordinate (x,y,z) of the ROI
                                 (relative to initial position)
        """
        if len(new_pos) != 3:
            raise ValueError('ROI history position to set must be iterable of length 3 (X, Y, Z).')
        timedelta = datetime.now() - self.creation_time
        self._pos_history.append(np.array((timedelta.total_seconds(), *new_pos), dtype=float))
        return

    def delete_history_entry(self, history_index=-1):
        """
        Delete an entry in the ROI position history. Deletes the last position by default.

        @param int|slice history_index: List index of history entry to delete
        """
        try:
            del self._pos_history[history_index]
        except IndexError:
            pass
        if len(self._pos_history) == 0:
            self._pos_history.append(np.zeros(4, dtype=float))
        return

    def to_dict(self):
        return {'name': self.name,
                'creation_time': self.creation_time_as_str,
                'pos_history': self.pos_history,
                'scan_image': self.scan_image,
                'scan_image_extent': self.scan_image_extent,
                'pois': [poi.to_dict() for poi in self._pois.values()]}

    @classmethod
    def from_dict(cls, dict_repr):
        if not isinstance(dict_repr, dict):
            raise TypeError('Parameter to generate RegionOfInterest instance from must be of type '
                            'dict.')
        if 'pois' in dict_repr:
            poi_list = [PointOfInterest.from_dict(poi) for poi in dict_repr.get('pois')]
        else:
            poi_list = None

        roi = cls(name=dict_repr.get('name'),
                  creation_time=dict_repr.get('creation_time'),
                  history=dict_repr.get('pos_history'),
                  scan_image=dict_repr.get('scan_image'),
                  scan_image_extent=dict_repr.get('scan_image_extent'),
                  poi_list=poi_list)
        return roi


class PointOfInterest:
    """
    The actual individual poi is saved in this generic object.
    """

    def __init__(self, position, name=None):
        # Name of the POI
        self._name = ''
        # Relative POI position within the ROI (x,y,z)
        self._position = np.zeros(3)
        # Initialize properties
        self.position = position
        self.name = name

    @property
    def name(self):
        return str(self._name)

    @name.setter
    def name(self, new_name):
        if new_name is not None and not isinstance(new_name, str):
            raise TypeError('Name to set must be either None or of type str.')

        if not new_name:
            new_name = datetime.now().strftime('poi_%Y%m%d%H%M%S%f')
        self._name = new_name
        return

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, pos):
        if len(pos) != 3:
            raise ValueError('POI position to set must be iterable of length 3 (X, Y, Z).')
        self._position = np.array(pos, dtype=float)
        return

    def to_dict(self):
        return {'name': self.name, 'position': self.position}

    @classmethod
    def from_dict(cls, dict_repr):
        return cls(**dict_repr)


class PoiManagerLogic(GenericLogic):

    """
    This is the Logic class for mapping and tracking bright features in the confocal scan.
    """
    _modclass = 'poimanagerlogic'
    _modtype = 'logic'

    # declare connectors
    optimiserlogic = Connector(interface='OptimizerLogic')
    scannerlogic = Connector(interface='ConfocalLogic')
    savelogic = Connector(interface='SaveLogic')

    # status vars
    _roi = StatusVar(default=dict())  # Notice constructor and representer further below
    _refocus_period = StatusVar(default=120)
    _active_poi = StatusVar(default=None)
    _move_scanner_after_optimization = StatusVar(default=True)

    # Signals for connecting modules
    sigRefocusTimerUpdated = QtCore.Signal(bool, float, float)  # is_active, period, remaining_time
    sigPoisUpdated = QtCore.Signal(dict)
    sigPoiUpdated = QtCore.Signal(str, str, np.ndarray)  # old_name, new_name, current_position
    sigScanImageUpdated = QtCore.Signal(np.ndarray, tuple)  # x,y image and extent
    sigActivePoiUpdated = QtCore.Signal(str)
    sigRoiHistoryUpdated = QtCore.Signal(np.ndarray)
    sigRoiNameUpdated = QtCore.Signal(str)

    # Internal signals
    __sigStartPeriodicRefocus = QtCore.Signal()
    __sigStopPeriodicRefocus = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # timer for the periodic refocus
        self.__timer = None
        self._last_refocus = 0
        self._periodic_refocus_poi = None

        # threading
        self._threadlock = Mutex()
        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.__timer = QtCore.QTimer()
        self.__timer.setSingleShot(False)
        self._last_refocus = 0
        self._periodic_refocus_poi = None

        # Connect callback for a finished refocus
        self.optimiserlogic().sigRefocusFinished.connect(
            self._optimisation_callback, QtCore.Qt.QueuedConnection)
        # Connect internal start/stop signals to decouple QTimer from other threads
        self.__sigStartPeriodicRefocus.connect(
            self.start_periodic_refocus, QtCore.Qt.QueuedConnection)
        self.__sigStopPeriodicRefocus.connect(
            self.stop_periodic_refocus, QtCore.Qt.QueuedConnection)

        # Initialise the ROI scan image (xy confocal image) if not present
        if self._roi.scan_image is None:
            self.set_scan_image()
        self.sigPoisUpdated.emit(self.poi_positions)
        return

    def on_deactivate(self):
        # Stop active processes/loops
        self.stop_periodic_refocus()

        # Disconnect signals
        self.optimiserlogic().sigRefocusFinished.disconnect()
        self.__sigStartPeriodicRefocus.disconnect()
        self.__sigStopPeriodicRefocus.disconnect()
        return

    @property
    def active_poi(self):
        return self._active_poi

    @active_poi.setter
    def active_poi(self, name):
        self.set_active_poi(name)
        return

    @property
    def poi_names(self):
        return self._roi.poi_names

    @property
    def poi_positions(self):
        return self._roi.poi_positions

    @property
    def poi_anchors(self):
        return self._roi.poi_anchors

    @property
    def roi_name(self):
        return self._roi.name

    @roi_name.setter
    def roi_name(self, name):
        self.rename_roi(new_name=name)

    @property
    def roi_origin(self):
        return self._roi.origin

    @property
    def roi_creation_time(self):
        return self._roi.creation_time

    @property
    def roi_creation_time_as_str(self):
        return self._roi.creation_time_as_str

    @property
    def roi_pos_history(self):
        return self._roi.pos_history

    @property
    def roi_scan_image(self):
        return self._roi.scan_image

    @property
    def roi_scan_image_extent(self):
        return self._roi.scan_image_extent

    @property
    def refocus_period(self):
        return float(self._refocus_period)

    @refocus_period.setter
    def refocus_period(self, period):
        self.set_refocus_period(period)
        return

    @property
    def time_until_refocus(self):
        if not self.__timer.isActive():
            return -1
        return max(0., self._refocus_period - (time.time() - self._last_refocus))

    @property
    def scanner_position(self):
        return self.scannerlogic().get_position()[:3]

    @property
    def move_scanner_after_optimise(self):
        return bool(self._move_scanner_after_optimization)

    @move_scanner_after_optimise.setter
    def move_scanner_after_optimise(self, move):
        self.set_move_scanner_after_optimise(move)
        return

    @QtCore.Slot(int)
    @QtCore.Slot(bool)
    def set_move_scanner_after_optimise(self, move):
        with self._threadlock:
            self._move_scanner_after_optimization = bool(move)
        return

    @QtCore.Slot()
    def add_poi(self, name=None, position=None, emit_change=True):
        """
        Creates a new POI and adds it to the current ROI.
        POI can be optionally initialized with position and name.

        @param str name: Name for the POI (must be unique within ROI).
                         None (default) will create generic name.
        @param scalar[3] position: Iterable of length 3 representing the (x, y, z) position with
                                   respect to the ROI origin. None (default) causes the current
                                   scanner crosshair position to be used.
        @param bool emit_change: Flag indicating if the changed POI set should be signaled.
        """
        # Get current scanner position from scannerlogic if no position is provided.
        if position is None:
            position = self.scanner_position

        current_poi_set = set(self.poi_names)

        # Add POI to current ROI
        self._roi.add_poi(position=position, name=name)

        # Get newly added POI name from comparing POI names before and after addition of new POI
        poi_name = set(self.poi_names).difference(current_poi_set).pop()

        # Notify about a changed set of POIs if necessary
        if emit_change:
            self.sigPoiUpdated.emit('', poi_name, self.get_poi_position(poi_name))

        # Set newly created POI as active poi
        self.set_active_poi(poi_name)
        return

    @QtCore.Slot()
    def delete_poi(self, name=None):
        """
        Deletes the given poi from the ROI.

        @param str name: Name of the POI to delete. If None (default) delete active POI.
        @param bool emit_change: Flag indicating if the changed POI set should be signaled.
        """
        if name is None:
            if self.active_poi is None:
                self.log.error('No POI name to delete and no active POI set.')
                return
            else:
                name = self.active_poi

        self._roi.delete_poi(name)

        if self.active_poi == name:
            if len(self.poi_names) > 0:
                self.set_active_poi(self.poi_names[0])
            else:
                self.set_active_poi(None)

        # Notify about a changed set of POIs if necessary
        self.sigPoiUpdated.emit(name, '', np.zeros(3))
        return

    @QtCore.Slot(str)
    @QtCore.Slot(str, str)
    def rename_poi(self, new_name, name=None):
        """

        @param str name:
        @param str new_name:
        """
        if not isinstance(new_name, str) or not new_name:
            self.log.error('POI name to set must be str of length > 0.')
            return

        if name is None:
            if self.active_poi is None:
                self.log.error('Unable to rename POI. No POI name given and no active POI set.')
                return
            else:
                name = self.active_poi

        self._roi.rename_poi(name=name, new_name=new_name)

        self.sigPoiUpdated.emit(name, new_name, self.get_poi_position(new_name))

        if self.active_poi == name:
            self.set_active_poi(new_name)
        return

    @QtCore.Slot(str)
    def set_active_poi(self, name=None):
        """
        Set the name of the currently active POI
        @param name:
        """
        if not isinstance(name, str) and name is not None:
            self.log.error('POI name must be of type str or None.')
        elif name is None or name == '':
            self._active_poi = None
        elif name in self.poi_names:
            self._active_poi = name
        else:
            self.log.error('No POI with name "{0}" found in POI list.'.format(name))

        self.sigActivePoiUpdated.emit('' if self.active_poi is None else self.active_poi)
        self.update_poi_tag_in_savelogic()
        return

    def get_poi_position(self, name=None):
        """
        Returns the POI position of the specified POI or the active POI if none is given.

        @param str name: Name of the POI to return the position for.
                             If None (default) the active POI position is returned.
        @return float[3]: Coordinates of the desired POI (x,y,z)
        """
        if name is None:
            name = self.active_poi
        return self._roi.get_poi_position(name)

    def get_poi_anchor(self, name=None):
        """
        Returns the POI anchor position (excluding sample movement) of the specified POI or the
        active POI if none is given.

        @param str name: Name of the POI to return the position for.
                         If None (default) the active POI position is returned.
        @return float[3]: Coordinates of the desired POI anchor (x,y,z)
        """
        if name is None:
            name = self.active_poi
        return self._roi.get_poi_anchor(name)

    @QtCore.Slot()
    def move_roi_from_poi_position(self, name=None, position=None):
        if position is None:
            position = self.scanner_position

        if name is None:
            if self.active_poi is None:
                self.log.error('Unable to set POI position. '
                               'No POI name given and no active POI set.')
                return
            else:
                name = self.active_poi

        if len(position) != 3:
            self.log.error('POI position must be iterable of length 3.')
            return
        if not isinstance(name, str):
            self.log.error('POI name must be of type str.')

        shift = position - self.get_poi_position(name)
        self.add_roi_position(self.roi_origin + shift)
        return

    @QtCore.Slot()
    def set_poi_anchor_from_position(self, name=None, position=None):
        if position is None:
            position = self.scanner_position

        if name is None:
            if self.active_poi is None:
                self.log.error('Unable to set POI position. '
                               'No POI name given and no active POI set.')
                return
            else:
                name = self.active_poi

        if len(position) != 3:
            self.log.error('POI position must be iterable of length 3.')
            return
        if not isinstance(name, str):
            self.log.error('POI name must be of type str.')

        shift = position - self.get_poi_position(name)
        self._roi.set_poi_anchor(name, self.get_poi_anchor(name) + shift)
        self.sigPoiUpdated.emit(name, name, self.get_poi_position(name))
        return

    @QtCore.Slot(str)
    def rename_roi(self, new_name):
        if not isinstance(new_name, str) or new_name == '':
            self.log.error('ROI name to set must be str of length > 0.')
            return
        self._roi.name = new_name
        self.sigRoiNameUpdated.emit(self.roi_name)
        return

    @QtCore.Slot(np.ndarray)
    def add_roi_position(self, position):
        self._roi.add_history_entry(position)
        self.sigScanImageUpdated.emit(self.roi_scan_image, self.roi_scan_image_extent)
        self.sigPoisUpdated.emit(self.poi_positions)
        self.sigRoiHistoryUpdated.emit(self.roi_pos_history)
        return

    @QtCore.Slot()
    @QtCore.Slot(int)
    def delete_history_entry(self, history_index=-1):
        """
        Delete an entry in the ROI history. Deletes the last position by default.

        @param int|slice history_index: List index for history entry
        """
        self._roi.delete_history_entry(history_index)
        self.sigScanImageUpdated.emit(self.roi_scan_image, self.roi_scan_image_extent)
        self.sigPoisUpdated.emit(self.poi_positions)
        self.sigRoiHistoryUpdated.emit(self.roi_pos_history)
        return

    @QtCore.Slot()
    def go_to_poi(self, name=None):
        """
        Move crosshair to the given poi.

        @param str name: the name of the POI
        """
        if name is None:
            name = self.active_poi
        if not isinstance(name, str):
            self.log.error('POI name to move to must be of type str.')
            return
        self.move_scanner(self.get_poi_position(name))
        return

    def move_scanner(self, position):
        if len(position) != 3:
            self.log.error('Scanner position to set must be iterable of length 3.')
            return
        self.scannerlogic().set_position('poimanager', x=position[0], y=position[1], z=position[2])
        return

    @QtCore.Slot()
    def set_scan_image(self):
        """ Get the current xy scan data and set as scan_image of ROI. """
        self._roi.set_scan_image(
            self.scannerlogic().xy_image[:, :, 3],
            (tuple(self.scannerlogic().image_x_range), tuple(self.scannerlogic().image_y_range)))

        self.sigScanImageUpdated.emit(self.roi_scan_image, self.roi_scan_image_extent)
        return

    @QtCore.Slot()
    def reset_roi(self):
        self.stop_periodic_refocus()
        self._roi = RegionOfInterest()
        self.active_poi = None
        self.sigPoisUpdated.emit(self.poi_positions)
        self.set_scan_image()
        self.sigRoiHistoryUpdated.emit(self.roi_pos_history)
        return

    @QtCore.Slot(int)
    @QtCore.Slot(float)
    def set_refocus_period(self, period):
        """ Change the duration of the periodic optimise timer during active
        periodic refocusing.

        @param float period: The time between optimisation procedures.
        """
        if period < 0:
            self.log.error('Refocus period must be a value > 0. Unable to set period of "{0}".'
                           ''.format(period))
            return
        # Acquire thread lock in order to change the period during a running periodic refocus
        with self._threadlock:
            self._refocus_period = float(period)
            is_running = self.__timer.isActive()
            if is_running:
                self.sigRefocusTimerUpdated.emit(True, self.refocus_period, self.time_until_refocus)
            else:
                self.sigRefocusTimerUpdated.emit(False, self.refocus_period, self.refocus_period)
        return

    def start_periodic_refocus(self, name=None):
        """
        Starts periodic refocusing of the POI <name>.

        @param str name: The name of the POI to be refocused periodically.
        If None (default) perform periodic refocus on active POI.
        """
        if name is None:
            if self.active_poi is None:
                self.log.error('Unable to start periodic refocus. No POI name given and no active '
                               'POI set.')
                return
            else:
                name = self.active_poi
        if name not in self.poi_names:
            self.log.error('No POI with name "{0}" found in POI list.\n'
                           'Unable to start periodic refocus.')
            return

        with self._threadlock:
            if self.__timer.isActive():
                self.log.error('Periodic refocus already running. Unable to start a new one.')
                return
            self.module_state.lock()
            self._periodic_refocus_poi = name
            self.optimise_poi_position(name=name)
            self._last_refocus = time.time()
            self.__timer.timeout.connect(self._periodic_refocus_loop)
            self.__timer.start(500)

            self.sigRefocusTimerUpdated.emit(True, self.refocus_period, self.refocus_period)
        return

    def stop_periodic_refocus(self):
        """ Stops the periodic refocusing of the POI. """
        with self._threadlock:
            if self.__timer.isActive():
                self.__timer.stop()
                self.__timer.timeout.disconnect()
                self._periodic_refocus_poi = None
                self.module_state.unlock()
            self.sigRefocusTimerUpdated.emit(False, self.refocus_period, self.refocus_period)
        return

    @QtCore.Slot(bool)
    def toggle_periodic_refocus(self, switch_on):
        """

        @param switch_on:
        """
        if switch_on:
            self.__sigStartPeriodicRefocus.emit()
        else:
            self.__sigStopPeriodicRefocus.emit()
        return

    @QtCore.Slot()
    def _periodic_refocus_loop(self):
        """ This is the looped function that does the actual periodic refocus.

        If the time has run out, it refocuses the current poi.
        Otherwise it just updates the time that is left.
        """
        with self._threadlock:
            if self.__timer.isActive():
                remaining_time = self.time_until_refocus
                self.sigRefocusTimerUpdated.emit(True, self.refocus_period, remaining_time)
                if remaining_time <= 0 and self.optimiserlogic().module_state() == 'idle':
                    self.optimise_poi_position(self._periodic_refocus_poi)
                    self._last_refocus = time.time()
        return

    @QtCore.Slot()
    def optimise_poi_position(self, name=None, update_roi_position=True):
        """
        Triggers the optimisation procedure for the given poi using the optimiserlogic.
        The difference between old and new position can be used to update the ROI position.
        This function will return immediately. The function "_optimisation_callback" will handle
        the aftermath of the optimisation.

        @param str name: Name of the POI for which to optimise the position.
        @param bool update_roi_position: Flag indicating if the ROI should be shifted accordingly.
        """
        if name is None:
            if self.active_poi is None:
                self.log.error('Unable to optimize POI position. '
                               'No POI name given and not active POI set.')
                return
            else:
                name = self.active_poi

        if update_roi_position:
            tag = 'poimanagermoveroi_{0}'.format(name)
        else:
            tag = 'poimanager_{0}'.format(name)

        if self.optimiserlogic().module_state() == 'idle':
            self.optimiserlogic().start_refocus(initial_pos=self.get_poi_position(name),
                                                caller_tag=tag)
        else:
            self.log.warning('Unable to start POI refocus procedure. '
                             'OptimizerLogic module is still locked.')
        return

    def _optimisation_callback(self, caller_tag, optimal_pos):
        """
        Callback function for a finished position optimisation.
        If desired the relative shift of the optimised POI can be used to update the ROI position.
        The scanner is moved to the optimised POI if desired.

        @param caller_tag:
        @param optimal_pos:
        """
        # If the refocus was initiated by poimanager, update POI and ROI position
        if caller_tag.startswith('poimanager_') or caller_tag.startswith('poimanagermoveroi_'):
            shift_roi = caller_tag.startswith('poimanagermoveroi_')
            poi_name = caller_tag.split('_', 1)[1]
            if poi_name in self.poi_names:
                # We only need x, y, z
                optimal_pos = np.array(optimal_pos[:3], dtype=float)
                if shift_roi:
                    self.move_roi_from_poi_position(name=poi_name, position=optimal_pos)
                else:
                    self.set_poi_anchor_from_position(name=poi_name, position=optimal_pos)
                if self._move_scanner_after_optimization:
                    self.move_scanner(position=optimal_pos)
        return

    def update_poi_tag_in_savelogic(self):
        pass

    def save_roi(self):
        """
        Save all current absolute POI coordinates to a file.
        Save ROI history to a second file.
        Save ROI scan image (if present) to a third file (binary numpy .npy-format).
        """
        # File path and names
        filepath = self.savelogic().get_path_for_module(module_name='ROIs')
        pois_filename = '{0}_poi_list'.format(self.roi_name)
        roi_filename = '{0}_history'.format(self.roi_name)
        roi_image_filename = '{0}_scan_image'.format(self.roi_name)

        # Common timestamp for all files
        timestamp = datetime.now()

        # Metadata to save in both file headers
        parameters = OrderedDict()
        parameters['roi_name'] = self.roi_name
        parameters['roi_creation_time'] = self.roi_creation_time_as_str
        parameters['scan_image_extent'] = str(self.roi_scan_image_extent)

        ##################################
        # Save POI positions to first file
        ##################################
        data = OrderedDict()
        # Save POI names in the first column
        data['name'] = np.array(self.poi_names, dtype=str)
        # Save x,y,z coordinates in the following 3 columns
        data['X (m)'] = np.empty(len(self.poi_names), dtype=float)
        data['Y (m)'] = np.empty(len(self.poi_names), dtype=float)
        data['Z (m)'] = np.empty(len(self.poi_names), dtype=float)
        # coordinates = np.empty((len(self.poi_names), 3), dtype=float)
        for ii, name in enumerate(self.poi_names):
            data['X (m)'][ii], data['Y (m)'][ii], data['Z (m)'][ii] = self.get_poi_position(name)

        self.savelogic().save_data(data,
                                   filepath=filepath,
                                   parameters=parameters,
                                   filelabel=pois_filename,
                                   fmt=['%s', '%.6e', '%.6e', '%.6e'])

        ############################################
        # Save ROI history to second file if present
        ############################################
        if self.roi_pos_history:
            data = OrderedDict()
            history = np.array(self.roi_pos_history, dtype=float)
            # Save timestamps in the first column
            data['time (s)'] = history[:, 0]
            # Save x,y,z coordinates in the following 3 columns
            data['X (m)'] = history[:, 1]
            data['Y (m)'] = history[:, 2]
            data['Z (m)'] = history[:, 3]

            self.savelogic().save_data(data,
                                       filepath=filepath,
                                       parameters=parameters,
                                       filelabel=roi_filename,
                                       fmt=['%.15e', '%.6e', '%.6e', '%.6e'])

        #######################################################
        # Save ROI scan image to third file (binary) if present
        #######################################################
        if self.roi_scan_image is not None:
            np.save(os.path.join(filepath, roi_image_filename), self.roi_scan_image)
        return

    def load_roi(self, filename=None):
        print(filename)
        if filename is None:
            return

        with open(filename, 'r') as roifile:
            for line in roifile:
                if line[0] != '#' and line.split()[0] != 'NaN':
                    saved_poi_name = line.split()[0]
                    saved_poi_key = line.split()[1]
                    saved_poi_coords = [
                        float(line.split()[2]), float(line.split()[3]), float(line.split()[4])]

                    this_poi_key = self.add_poi(
                        position=saved_poi_coords,
                        key=saved_poi_key,
                        emit_change=False)
                    self.rename_poi(poikey=this_poi_key, name=saved_poi_name)

            # Now that all the POIs are created, emit the signal for other things (ie gui) to update
            self.signal_poi_updated.emit()
        return 0

    @_roi.constructor
    def dict_to_roi(self, roi_dict):
        return RegionOfInterest.from_dict(roi_dict)

    @_roi.representer
    def roi_to_dict(self, roi):
        return roi.to_dict()

    def triangulate(self, r, a1, b1, c1, a2, b2, c2):
        """ Reorients a coordinate r that is known relative to reference points a1, b1, c1 to
            produce a new vector rnew that has exactly the same relation to rotated/shifted/tilted
            reference positions a2, b2, c2.

            @param np.array r: position to be remapped.

            @param np.array a1: initial location of ref1.

            @param np.array a2: final location of ref1.

            @param np.array b1, b2, c1, c2: similar for ref2 and ref3
        """

        ab_old = b1 - a1
        ac_old = c1 - a1

        ab_new = b2 - a2
        ac_new = c2 - a2

        # Firstly, find the angle to rotate ab_old onto ab_new.  This rotation must be done in
        # the plane that contains these two vectors, which means rotating about an axis
        # perpendicular to both of them (the cross product).

        axis1 = np.cross(ab_old, ab_new)  # Only works if ab_old and ab_new are not parallel
        axis1length = np.sqrt((axis1 * axis1).sum())

        if axis1length == 0:
            ab_olddif = ab_old + np.array([100, 0, 0])
            axis1 = np.cross(ab_old, ab_olddif)

        # normalising the axis1 vector
        axis1 = axis1 / np.sqrt((axis1 * axis1).sum())

        # The dot product gives the angle between ab_old and ab_new
        dot = np.dot(ab_old, ab_new)
        x_modulus = np.sqrt((ab_old * ab_old).sum())
        y_modulus = np.sqrt((ab_new * ab_new).sum())

        # float errors can cause the division to be slightly above 1 for 90 degree rotations, which
        # will confuse arccos.
        cos_angle = min(dot / x_modulus / y_modulus, 1)

        angle1 = np.arccos(cos_angle)  # angle in radians

        # Construct a rotational matrix for axis1
        n1 = axis1[0]
        n2 = axis1[1]
        n3 = axis1[2]

        m1 = np.matrix(((((n1 * n1) * (1 - np.cos(angle1)) + np.cos(angle1)),
                         ((n1 * n2) * (1 - np.cos(angle1)) - n3 * np.sin(angle1)),
                         ((n1 * n3) * (1 - np.cos(angle1)) + n2 * np.sin(angle1))
                         ),
                        (((n2 * n1) * (1 - np.cos(angle1)) + n3 * np.sin(angle1)),
                         ((n2 * n2) * (1 - np.cos(angle1)) + np.cos(angle1)),
                         ((n2 * n3) * (1 - np.cos(angle1)) - n1 * np.sin(angle1))
                         ),
                        (((n3 * n1) * (1 - np.cos(angle1)) - n2 * np.sin(angle1)),
                         ((n3 * n2) * (1 - np.cos(angle1)) + n1 * np.sin(angle1)),
                         ((n3 * n3) * (1 - np.cos(angle1)) + np.cos(angle1))
                         )
                        )
                       )

        # Now that ab_old can be rotated to overlap with ab_new, we need to rotate in another
        # axis to fix "tilt".  By choosing ab_new as the rotation axis we ensure that the
        # ab vectors stay where they need to be.

        # ac_old_rot is the rotated ac_old (around axis1).  We need to find the angle to rotate
        # ac_old_rot around ab_new to get ac_new.
        ac_old_rot = np.array(np.dot(m1, ac_old))[0]

        axis2 = -ab_new  # TODO: check maths to find why this negative sign is necessary.  Empirically it is now working.
        axis2 = axis2 / np.sqrt((axis2 * axis2).sum())

        # To get the angle of rotation it is most convenient to work in the plane for which axis2 is the normal.
        # We must project vectors ac_old_rot and ac_new into this plane.
        a = ac_old_rot - np.dot(ac_old_rot, axis2) * axis2  # projection of ac_old_rot in the plane of rotation about axis2
        b = ac_new - np.dot(ac_new, axis2) * axis2  # projection of ac_new in the plane of rotation about axis2

        # The dot product gives the angle of rotation around axis2
        dot = np.dot(a, b)

        x_modulus = np.sqrt((a * a).sum())
        y_modulus = np.sqrt((b * b).sum())
        cos_angle = min(dot / x_modulus / y_modulus, 1)  # float errors can cause the division to be slightly above 1 for 90 degree rotations, which will confuse arccos.
        angle2 = np.arccos(cos_angle)  # angle in radians

        # Construct a rotation matrix around axis2
        n1 = axis2[0]
        n2 = axis2[1]
        n3 = axis2[2]

        m2 = np.matrix(((((n1 * n1) * (1 - np.cos(angle2)) + np.cos(angle2)),
                         ((n1 * n2) * (1 - np.cos(angle2)) - n3 * np.sin(angle2)),
                         ((n1 * n3) * (1 - np.cos(angle2)) + n2 * np.sin(angle2))
                         ),
                        (((n2 * n1) * (1 - np.cos(angle2)) + n3 * np.sin(angle2)),
                         ((n2 * n2) * (1 - np.cos(angle2)) + np.cos(angle2)),
                         ((n2 * n3) * (1 - np.cos(angle2)) - n1 * np.sin(angle2))
                         ),
                        (((n3 * n1) * (1 - np.cos(angle2)) - n2 * np.sin(angle2)),
                         ((n3 * n2) * (1 - np.cos(angle2)) + n1 * np.sin(angle2)),
                         ((n3 * n3) * (1 - np.cos(angle2)) + np.cos(angle2))
                         )
                        )
                       )

        # To find the new position of r, displace by (a2 - a1) and do the rotations
        a1r = r - a1

        rnew = a2 + np.array(np.dot(m2, np.array(np.dot(m1, a1r))[0]))[0]

        return rnew

    def reorient_roi(self, ref1_coords, ref2_coords, ref3_coords, ref1_newpos, ref2_newpos, ref3_newpos):
        """ Move and rotate the ROI to a new position specified by the newpos of 3 reference POIs from the saved ROI.

        @param ref1_coords: coordinates (from ROI save file) of reference 1.

        @param ref2_coords: similar, ref2.

        @param ref3_coords: similar, ref3.

        @param ref1_newpos: the new (current) position of POI reference 1.

        @param ref2_newpos: similar, ref2.

        @param ref3_newpos: similar, ref3.
        """

        for poikey in self.get_all_pois(abc_sort=True):
            if poikey is not 'sample' and poikey is not 'crosshair':
                thispoi = self.poi_list[poikey]

                old_coords = thispoi.get_coords_in_sample()

                new_coords = self.triangulate(old_coords, ref1_coords, ref2_coords, ref3_coords, ref1_newpos, ref2_newpos, ref3_newpos)

                self.move_coords(poikey=poikey, newpos=new_coords)

    def autofind_pois(self, neighborhood_size=1, min_threshold=10000, max_threshold=1e6):
        """Automatically search the xy scan image for POIs.

        @param neighborhood_size: size in microns.  Only the brightest POI per neighborhood will be found.

        @param min_threshold: POIs must have c/s above this threshold.

        @param max_threshold: POIs must have c/s below this threshold.
        """

        # Calculate the neighborhood size in pixels from the image range and resolution
        x_range_microns = np.max(self.roi_map_data[:, :, 0]) - np.min(self.roi_map_data[:, :, 0])
        y_range_microns = np.max(self.roi_map_data[:, :, 1]) - np.min(self.roi_map_data[:, :, 1])
        y_pixels = len(self.roi_map_data)
        x_pixels = len(self.roi_map_data[1, :])

        pixels_per_micron = np.max([x_pixels, y_pixels]) / np.max([x_range_microns, y_range_microns])
        # The neighborhood in pixels is nbhd_size * pixels_per_um, but it must be 1 or greater
        neighborhood_pix = int(np.max([math.ceil(pixels_per_micron * neighborhood_size), 1]))

        data = self.roi_map_data[:, :, 3]

        data_max = filters.maximum_filter(data, neighborhood_pix)
        maxima = (data == data_max)
        data_min = filters.minimum_filter(data, 3 * neighborhood_pix)
        diff = ((data_max - data_min) > min_threshold)
        maxima[diff is False] = 0

        labeled, num_objects = ndimage.label(maxima)
        xy = np.array(ndimage.center_of_mass(data, labeled, range(1, num_objects + 1)))

        for count, pix_pos in enumerate(xy):
            poi_pos = self.roi_map_data[pix_pos[0], pix_pos[1], :][0:3]
            this_poi_key = self.add_poi(position=poi_pos, emit_change=False)
            self.rename_poi(poikey=this_poi_key, name='spot' + str(count), emit_change=False)

        # Now that all the POIs are created, emit the signal for other things (ie gui) to update
        self.signal_poi_updated.emit()
