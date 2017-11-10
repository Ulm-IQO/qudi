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

import logging
import math
import numpy as np
import re
import scipy.ndimage as ndimage
import scipy.ndimage.filters as filters
import time

from collections import OrderedDict
from core.module import Connector
from core.util.mutex import Mutex
from datetime import datetime
from logic.generic_logic import GenericLogic
from qtpy import QtCore


class PoI:

    """
    The actual individual poi is saved in this generic object.

    """

    def __init__(self, pos=None, name=None, key=None):
        # Logging
        self.log = logging.getLogger(__name__)

        # The POI has fixed coordinates relative to the sample, enabling a map to be saved.
        self._coords_in_sample = []

        # The POI is at a scanner position, which may vary with time (drift).  This time
        # trace records every time+position when the POI position was explicitly known.
        self._position_time_trace = []

        # To avoid duplication while algorithmically setting POIs, we need the key string to
        # go to sub-second. This requires the datetime module.
        self._creation_time = datetime.now()

        if key is None:
            self._key = self._creation_time.strftime('poi_%Y%m%d_%H%M_%S_%f')
        else:
            self._key = key

        if pos is not None:
            if len(pos) != 3:
                self.log.error('Given position does not contain 3 '
                               'dimensions.'
                               )
            # Store the time in the history log as seconds since 1970,
            # rather than as a datetime object.
            creation_time_sec = (self._creation_time - datetime.utcfromtimestamp(0)).total_seconds()
            self._position_time_trace.append(
                np.array([creation_time_sec, pos[0], pos[1], pos[2]]))
        if name is None:
            self._name = self._creation_time.strftime('poi_%H%M%S')
        else:
            self._name = name

    def set_coords_in_sample(self, coords=None):
        '''Defines the position of the poi relative to the sample,
        allowing a sample map to be constructed.  Once set, these
        "coordinates in sample" will not be altered unless the user wants to
        manually redefine this POI (for example, they put the POI in
        the wrong place).
        '''

        if coords is not None:  # FIXME: Futurewarning fired here.
            if len(coords) != 3:
                self.log.error('Given position does not contain 3 '
                               'dimensions.'
                               )
            self._coords_in_sample = [coords[0], coords[1], coords[2]]

    def add_position_to_history(self, position=None):
        """ Adds an explicitly known position+time to the history of the POI.

        @param float[3] position: position coordinates of the poi

        @return int: error code (0:OK, -1:error)
        """
        if position is None:
            position = []
        if isinstance(position, (np.ndarray,)) and not position.size == 3:
            return -1
        elif isinstance(position, (list, tuple)) and not len(position) == 3:
            return -1
        else:
            self._position_time_trace.append(
                np.array([time.time(), position[0], position[1], position[2]]))

    def get_coords_in_sample(self):
        """ Returns the coordinates of the POI relative to the sample.

        @return float[3]: the POI coordinates.
        """

        return self._coords_in_sample

    def set_name(self, name=None):
        """ Sets the name of the poi.

        @param string name: name to be set.

        @return int: error code (0:OK, -1:error)
        """
        if self._name is 'crosshair' or self._name is 'sample':
            #            self.log.error('You can not change the name of the crosshair.')
            return -1
        if name is not None:
            self._name = name
            return 0
        if len(self._position_time_trace) > 0:
            self._name = time.strftime('Point_%Y%m%d_%M%S%', self._creation_time)
            return -1
        else:
            self._name = time.strftime('Point_%Y%m%d_%M%S%')
            return -1

    def get_name(self):
        """ Returns the name of the poi.

        @return string: name
        """
        return self._name

    def get_key(self):
        """ Returns the dictionary key of the poi.

        @return string: key
        """
        return self._key

    def get_position_history(self):  # TODO: instead of "trace": drift_log, history,
        """ Returns the whole position history as array.

        @return float[][4]: the whole position history
        """

        return np.array(self._position_time_trace)

    def delete_last_position(self, empty_array_completely=False):
        """ Delete the last position in the history.
        @param bool empty_array_completely: If _position_time_trace can be deleted completely
                                            this variable is set to True if not the last value
                                            will not be deleted

        @return float[4]: the position just deleted.
        """
        # do not delete initial position
        if len(self._position_time_trace) > 1:
            return self._position_time_trace.pop()
        elif empty_array_completely:
            return self._position_time_trace.pop()
        else:
            self.log.error('Position was not deleted, initial point of history reached.')
            return [-1., -1., -1., -1.]


class PoiManagerLogic(GenericLogic):

    """
    This is the Logic class for mapping and tracking bright features in the confocal scan.
    """
    _modclass = 'poimanagerlogic'
    _modtype = 'logic'

    # declare connectors
    optimizer1 = Connector(interface='OptimizerLogic')
    scannerlogic = Connector(interface='ConfocalLogic')
    savelogic = Connector(interface='SaveLogic')

    signal_timer_updated = QtCore.Signal()
    signal_poi_updated = QtCore.Signal()
    signal_poi_deleted = QtCore.Signal(str)
    signal_confocal_image_updated = QtCore.Signal()
    signal_periodic_opt_started = QtCore.Signal()
    signal_periodic_opt_duration_changed = QtCore.Signal()
    signal_periodic_opt_stopped = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.roi_name = ''
        self.poi_list = dict()
        self._current_poi_key = None
        self.go_to_crosshair_after_refocus = False  # default value

        # timer and its handling for the periodic refocus
        self.timer = None
        self.time_left = 0
        self.timer_step = 0
        self.timer_duration = 300

        # locking for thread safety
        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        self._optimizer_logic = self.get_connector('optimizer1')
        self._confocal_logic = self.get_connector('scannerlogic')
        self._save_logic = self.get_connector('savelogic')

        # initally add crosshair to the pois
        crosshair = PoI(pos=[0, 0, 0], name='crosshair')
        crosshair._key = 'crosshair'
        self.poi_list[crosshair._key] = crosshair

        # initally add sample to the pois
        sample = PoI(pos=[0, 0, 0], name='sample')
        sample._key = 'sample'
        self.poi_list[sample._key] = sample

        # listen for the refocus to finish
        self._optimizer_logic.sigRefocusFinished.connect(self._refocus_done)

        # listen for the deactivation of a POI caused by moving to a different position
        self._confocal_logic.signal_change_position.connect(self.user_move_deactivates_poi)

        self.testing()

        # Initialise the roi_map_data (xy confocal image)
        self.roi_map_data = self._confocal_logic.xy_image

        # A POI is active if the scanner is at that POI
        self.active_poi = None

    def on_deactivate(self):
        return

    def user_move_deactivates_poi(self, tag):
        """ Deactivate the active POI if the confocal microscope scanner position is
        moved by anything other than the optimizer
        """
        if tag != 'optimizer':
            self._deactivate_poi()

    def testing(self):
        """ Debug function for testing. """
        pass

    def add_poi(self, position=None, key=None, emit_change=True):
        """ Creates a new poi and adds it to the list.

        @return int: key of this new poi

        A position can be provided (such as during re-loading a saved ROI).
        If no position is provided, then the current crosshair position is used.
        """
        # If there are only 2 POIs (sample and crosshair) then the newly added POI needs to start the sample drift logging.
        if len(self.poi_list) == 2:
            self.poi_list['sample']._creation_time = time.time()
            # When the poimanager is activated the 'sample' poi is created because it is needed
            # from the beginning for various functionalities. If the tracking of the sample is started it has
            # to be reset such that this first point is deleted here
            # Probably this can be solved a lot nicer.
            self.poi_list['sample'].delete_last_position(empty_array_completely=True)
            self.poi_list['sample'].add_position_to_history(position=[0, 0, 0])
            self.poi_list['sample'].set_coords_in_sample(coords=[0, 0, 0])

        if position is None:
            position = self._confocal_logic.get_position()[:3]
        if len(position) != 3:
            self.log.error('Given position is not 3-dimensional.'
                           'Please pass POIManager a 3-dimensional position to set a POI.')
            return

        new_poi = PoI(pos=position, key=key)
        self.poi_list[new_poi.get_key()] = new_poi

        # The POI coordinates are set relative to the last known sample position
        most_recent_sample_pos = self.poi_list['sample'].get_position_history()[-1, :][1:4]
        this_poi_coords = position - most_recent_sample_pos
        new_poi.set_coords_in_sample(coords=this_poi_coords)

        # Since POI was created at current scanner position, it automatically
        # becomes the active POI.
        self.set_active_poi(poikey=new_poi.get_key())

        if emit_change:
            self.signal_poi_updated.emit()

        return new_poi.get_key()

    def get_confocal_image_data(self):
        """ Get the current confocal xy scan data to hold as image of ROI"""

        # get the roi_map_data (xy confocal image)
        self.roi_map_data = self._confocal_logic.xy_image

        self.signal_confocal_image_updated.emit()

    def get_all_pois(self, abc_sort=False):
        """ Returns a list of the names of all existing POIs.

        @return string[]: List of names of the POIs

        Also crosshair and sample are included.
        """
        if abc_sort is False:
            return sorted(self.poi_list.keys())

        elif abc_sort is True:
            # First create a dictionary with poikeys indexed against names
            poinames = [''] * len(self.poi_list.keys())
            for i, poikey in enumerate(self.poi_list.keys()):
                poiname = self.poi_list[poikey].get_name()
                poinames[i] = [poiname, poikey]

            # Sort names in the way that humans expect (site1, site2, site11, etc)

            # Regular expressions to make sorting key
            convert = lambda text: int(text) if text.isdigit() else text
            alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key[0])]
            # Now we can sort poinames by name and return keys in that order
            return [key for [name, key] in sorted(poinames, key=alphanum_key)]

        else:
            # TODO: produce sensible error about unknown value of abc_sort.
            self.log.debug('fix TODO!')

        # TODO: Find a way to return a list of POI keys sorted in order of the POI names.

    def delete_last_position(self, poikey=None):
        """ Delete the last position in the history.

        @param string poikey: the key of the poi

        @return int: error code (0:OK, -1:error)
        """
        if poikey is not None and poikey in self.poi_list.keys():
            self.poi_list[poikey].delete_last_position()
            self.poi_list['sample'].delete_last_position()
            self.signal_poi_updated.emit()
            return 0
        else:
            self.log.error('The last position of given POI ({0}) could not be deleted.'.format(
                poikey))
            return -1

    def delete_poi(self, poikey=None):
        """ Completely deletes the whole given poi.

        @param string poikey: the key of the poi

        @return int: error code (0:OK, -1:error)

        Does not delete the crosshair and sample.
        """

        if poikey is not None and poikey in self.poi_list.keys():
            if poikey is 'crosshair' or poikey is 'sample':
                self.log.warning('You cannot delete the crosshair or sample.')
                return -1
            del self.poi_list[poikey]

            # If the active poi was deleted, there is no way to automatically choose
            # another active POI, so we deactivate POI
            if self.active_poi is not None and poikey == self.active_poi.get_key():
                self._deactivate_poi()

            self.signal_poi_updated.emit()
            self.signal_poi_deleted.emit(poikey)
            return 0
        elif poikey is None:
            self.log.warning('No POI for deletion specified.')
        else:
            self.log.error('X. The given POI ({0}) does not exist.'.format(
                poikey))
            return -1

    def optimise_poi(self, poikey=None):
        """ Starts the optimisation procedure for the given poi.

        @param string poikey: the key of the poi

        @return int: error code (0:OK, -1:error)

        This is threaded, so it returns directly.
        The function _refocus_done handles the data when the optimisation returns.
        """

        if poikey is not None and poikey in self.poi_list.keys():
            self.poi_list['crosshair'].add_position_to_history(position=self._confocal_logic.get_position()[:3])
            self._current_poi_key = poikey
            self._optimizer_logic.start_refocus(
                initial_pos=self.get_poi_position(poikey=poikey),
                caller_tag='poimanager')
            return 0
        else:
            self.log.error(
                'Z. The given POI ({0}) does not exist.'.format(poikey))
            return -1

    def go_to_poi(self, poikey=None):
        """ Goes to the given poi and saves it as the current one.

        @param string poikey: the key of the poi

        @return int: error code (0:OK, -1:error)
        """
        if poikey is not None and poikey in self.poi_list.keys():
            self._current_poi_key = poikey
            x, y, z = self.get_poi_position(poikey=poikey)
            self._confocal_logic.set_position('poimanager', x=x, y=y, z=z)
        else:
            self.log.error('The given POI ({0}) does not exist.'.format(
                poikey))
            return -1
        # This is now the active POI to send to save logic for naming in any saved filenames.
        self.set_active_poi(poikey)

        #Fixme: After pressing the Go to Poi button the active poi is empty and the following lines do fix this
        # The time.sleep is somehow needed if not active_poi can not be set
        time.sleep(0.001)
        self.active_poi = self.poi_list[poikey]
        self.signal_poi_updated.emit()


    def get_poi_position(self, poikey=None):
        """ Returns the current position of the given poi, calculated from the
        POI coords in sample and the current sample position.

        @param string poikey: the key of the poi

        @return
        """

        if poikey is not None and poikey in self.poi_list.keys():

            poi_coords = self.poi_list[poikey].get_coords_in_sample()
            sample_pos = self.poi_list['sample'].get_position_history()[-1, :][1:4]

            return sample_pos + poi_coords

        else:
            self.log.error('G. The given POI ({0}) does not exist.'.format(
                poikey))
            return [-1., -1., -1.]

    def set_new_position(self, poikey=None, newpos=None):
        """
        Moves the given POI to a new position, and uses this information to update
        the sample position.

        @param string poikey: the key of the poi
        @param float[3] newpos: coordinates of the new position

        @return int: error code (0:OK, -1:error)
        """

        # If no new position is given, take the current confocal crosshair position
        if newpos is None:
            newpos = self._confocal_logic.get_position()[:3]

        if poikey is not None and poikey in self.poi_list.keys():
            if len(newpos) != 3:
                self.log.error('Length of set poi is not 3.')
                return -1
            # Add new position to trace of POI
            self.poi_list[poikey].add_position_to_history(position=newpos)

            # Calculate sample shift and add it to the trace of 'sample' POI
            sample_shift = newpos - self.get_poi_position(poikey=poikey)
            sample_shift += self.poi_list['sample'].get_position_history()[-1, :][1:4]
            self.poi_list['sample'].add_position_to_history(position=sample_shift)

            # signal POI has been updated (this will cause GUI to redraw)
            if (poikey is not 'crosshair') and (poikey is not 'sample'):
                self.signal_poi_updated.emit()

            return 0

        self.log.error('J. The given POI ({0}) does not exist.'.format(poikey))
        return -1

    def move_coords(self, poikey=None, newpos=None):
        """Updates the coords of a given POI, and adds a position to the POI history,
        but DOES NOT update the sample position.
        """
        if newpos is None:
            newpos = self._confocal_logic.get_position()[:3]

        if poikey is not None and poikey in self.poi_list.keys():
            if len(newpos) != 3:
                self.log.error('Length of set poi is not 3.')
                return -1
            this_poi = self.poi_list[poikey]
            return_val = this_poi.add_position_to_history(position=newpos)

            sample_pos = self.poi_list['sample'].get_position_history()[-1, :][1:4]

            new_coords = newpos - sample_pos

            this_poi.set_coords_in_sample(new_coords)

            self.signal_poi_updated.emit()

            return return_val

        self.log.error('JJ. The given POI ({0}) does not exist.'.format(poikey))
        return -1

    def rename_poi(self, poikey=None, name=None, emit_change=True):
        """ Sets the name of the given poi.

        @param string poikey: the key of the poi
        @param string name: name of the poi to be set

        @return int: error code (0:OK, -1:error)
        """

        if poikey is not None and name is not None and poikey in self.poi_list.keys():

            success = self.poi_list[poikey].set_name(name=name)

            # if this is the active POI then we need to update poi tag in savelogic
            if self.poi_list[poikey] == self.active_poi:
                self.update_poi_tag_in_savelogic()

            if emit_change:
                self.signal_poi_updated.emit()

            return success

        else:
            self.log.error('AAAThe given POI ({0}) does not exist.'.format(
                poikey))
            return -1

    def start_periodic_refocus(self, poikey=None):
        """ Starts the perodic refocussing of the poi.

        @param float duration: (optional) the time between periodic optimization
        @param string poikey: (optional) the key of the poi to be set and refocussed on.

        @return int: error code (0:OK, -1:error)
        """

        if poikey is not None and poikey in self.poi_list.keys():
            self._current_poi_key = poikey
        else:
            # Todo: warning message that active POI used by default
            self._current_poi_key = self.active_poi.get_key()

        self.log.info('Periodic refocus on {0}.'.format(self._current_poi_key))

        self.timer_step = 0
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self._periodic_refocus_loop)
        self.timer.start(300)

        self.signal_periodic_opt_started.emit()
        return 0

    def set_periodic_optimize_duration(self, duration=None):
        """ Change the duration of the periodic optimize timer during active
        periodic refocussing.

        @param float duration: (optional) the time between periodic optimization.
        """
        if duration is not None:
            self.timer_duration = duration
        else:
            self.log.warning('No timer duration given, using {0} s.'.format(
                self.timer_duration))

        self.signal_periodic_opt_duration_changed.emit()

    def _periodic_refocus_loop(self):
        """ This is the looped function that does the actual periodic refocus.

        If the time has run out, it refocussed the current poi.
        Otherwise it just updates the time that is left.
        """
        self.time_left = self.timer_step - time.time() + self.timer_duration
        self.signal_timer_updated.emit()
        if self.time_left <= 0:
            self.timer_step = time.time()
            self.optimise_poi(poikey=self._current_poi_key)

    def stop_periodic_refocus(self):
        """ Stops the perodic refocussing of the poi.

        @return int: error code (0:OK, -1:error)
        """
        if self.timer is None:
            self.log.warning('No timer to stop.')
            return -1
        self.timer.stop()
        self.timer = None

        self.signal_periodic_opt_stopped.emit()
        return 0

    def _refocus_done(self, caller_tag, optimal_pos):
        """ Gets called automatically after the refocus is done and saves the new position
        to the poi history.

        Also it tracks the sample and may go back to the crosshair.

        @return int: error code (0:OK, -1:error)
        """
        # We only need x, y, z
        optimized_position = optimal_pos[0:3]

        # If the refocus was on the crosshair, then only update crosshair POI and don't
        # do anything with sample position.
        caller_tags = ['confocalgui', 'magnet_logic', 'singleshot_logic']
        if caller_tag in caller_tags:
            self.poi_list['crosshair'].add_position_to_history(position=optimized_position)

        # If the refocus was initiated here by poimanager, then update POI and sample
        elif caller_tag == 'poimanager':

            if self._current_poi_key is not None and self._current_poi_key in self.poi_list.keys():

                self.set_new_position(poikey=self._current_poi_key, newpos=optimized_position)

                if self.go_to_crosshair_after_refocus:
                    temp_key = self._current_poi_key
                    self.go_to_poi(poikey='crosshair')
                    self._current_poi_key = temp_key
                else:
                    self.go_to_poi(poikey=self._current_poi_key)
                return 0
            else:
                self.log.error('The given POI ({0}) does not exist.'.format(
                    self._current_poi_key))
                return -1

        else:
            self.log.warning("Unknown caller_tag for the optimizer. POI "
                             "Manager does not know what to do with optimized "
                             "position, and has done nothing.")

    def reset_roi(self):

        del self.poi_list
        self.poi_list = dict()

        self.active_poi = None

        self.roi_name = ''

        # initally add crosshair to the pois
        crosshair = PoI(pos=[0, 0, 0], name='crosshair')
        crosshair._key = 'crosshair'
        self.poi_list[crosshair._key] = crosshair

        # Re-initialise sample in the poi list
        sample = PoI(pos=[0, 0, 0], name='sample')
        sample._key = 'sample'
        self.poi_list[sample._key] = sample

        self.signal_poi_updated.emit()

    def set_active_poi(self, poikey=None):
        """
        Set the active POI object.
        """

        if poikey is None:
            # If poikey is none and no active poi is set, then do nothing
            if self.active_poi is None:
                return
            else:
                self.active_poi = None

        elif poikey in self.get_all_pois():
            # If poikey is the current active POI then do nothing
            if self.poi_list[poikey] == self.active_poi:
                return

            else:
                self.active_poi = self.poi_list[poikey]

        else:
            # todo: error poikey unknown
            return -1

        self.update_poi_tag_in_savelogic()
        self.signal_poi_updated.emit()  # todo: this breaks the emit_change = false case

    def _deactivate_poi(self):
        self.set_active_poi(poikey=None)

    def update_poi_tag_in_savelogic(self):

        if self.active_poi is not None:
            self._save_logic.active_poi_name = self.active_poi.get_name()
        else:
            self._save_logic.active_poi_name = ''

    def save_poi_map_as_roi(self):
        '''Save a list of POIs with their coordinates to a file.
        '''
        # File path and name
        filepath = self._save_logic.get_path_for_module(module_name='ROIs')

        # We will fill the data OderedDict to send to savelogic
        data = OrderedDict()

        # Lists for each column of the output file
        poinames = []
        poikeys = []
        x_coords = []
        y_coords = []
        z_coords = []

        for poikey in self.get_all_pois(abc_sort=True):
            if poikey is not 'sample' and poikey is not 'crosshair':
                thispoi = self.poi_list[poikey]

                poinames.append(thispoi.get_name())
                poikeys.append(poikey)
                x_coords.append(thispoi.get_coords_in_sample()[0])
                y_coords.append(thispoi.get_coords_in_sample()[1])
                z_coords.append(thispoi.get_coords_in_sample()[2])

        data['POI Name'] = np.array(poinames)
        data['POI Key'] = np.array(poikeys)
        data['X'] = np.array(x_coords)
        data['Y'] = np.array(y_coords)
        data['Z'] = np.array(z_coords)

        self._save_logic.save_data(data, filepath=filepath, filelabel=self.roi_name,
                                   fmt=['%s', '%s', '%.6e', '%.6e', '%.6e'])

        self.log.debug('ROI saved to:\n{0}'.format(filepath))

        return 0

    def load_roi_from_file(self, filename=None):

        if filename is None:
            return -1

        roifile = open(filename, 'r')

        for line in roifile:
            if line[0] != '#' and line.split()[0] != 'NaN':
                saved_poi_name = line.split()[0]
                saved_poi_key = line.split()[1]
                saved_poi_coords = [
                    float(line.split()[2]), float(line.split()[3]), float(line.split()[4])]

                this_poi_key = self.add_poi(position=saved_poi_coords, key=saved_poi_key, emit_change=False)
                self.rename_poi(poikey=this_poi_key, name=saved_poi_name, emit_change=False)

        roifile.close()
        # Now that all the POIs are created, emit the signal for other things (ie gui) to update
        self.signal_poi_updated.emit()

        return 0

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
