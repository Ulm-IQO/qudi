# -*- coding: utf-8 -*-
"""
This module operates a confocal microsope.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""


from logic.generic_logic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from core.util.numpyhelpers import numpy_to_b, numpy_from_b
from collections import OrderedDict
from copy import copy
from datetime import datetime
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt


class ConfocalHistoryEntry(QtCore.QObject):
    """ This class contains all relevant parameters of a Confocal scan.
        It provides methods to extract, restore and serialize this data.
    """

    def __init__(self, confocal):
        """ Make a confocal data setting with default values. """
        super().__init__()

        self.xy_line_pos = 0
        self.depth_line_pos = 0

        # Reads in the maximal scanning range. The unit of that scan range is micrometer!
        self.x_range = confocal._scanning_device.get_position_range()[0]
        self.y_range = confocal._scanning_device.get_position_range()[1]
        self.z_range = confocal._scanning_device.get_position_range()[2]

        # Sets the current position to the center of the maximal scanning range
        self.current_x = (self.x_range[0] + self.x_range[1]) / 2
        self.current_y = (self.y_range[0] + self.y_range[1]) / 2
        self.current_z = (self.z_range[0] + self.z_range[1]) / 2
        self.current_a = 0.0

        # Sets the size of the image to the maximal scanning range
        self.image_x_range = self.x_range
        self.image_y_range = self.y_range
        self.image_z_range = self.z_range

        # Default values for the resolution of the scan
        self.xy_resolution = 100
        self.z_resolution = 50

        # Initialization of internal counter for scanning
        self.xy_line_position = 0
        self.depth_line_position = 0

        # Variable to check if a scan is continuable
        self.xy_scan_continuable = False
        self.depth_scan_continuable = False

        # tilt correction stuff:
        self.tilt_correction = False

        self.tilt_reference_x = 0.5 * (self.x_range[0] + self.x_range[1])
        self.tilt_reference_y = 0.5 * (self.y_range[0] + self.y_range[1])

        self.tilt_slope_x = 0
        self.tilt_slope_y = 0

        self.point1 = np.array((0, 0, 0))
        self.point2 = np.array((0, 0, 0))
        self.point3 = np.array((0, 0, 0))


    def restore(self, confocal):
        """ Write data back into confocal logic and pull all the necessary strings """
        confocal._current_x = self.current_x
        confocal._current_y = self.current_y
        confocal._current_z = self.current_z
        confocal._current_a = self.current_a
        confocal.image_x_range = np.copy(self.image_x_range)
        confocal.image_y_range = np.copy(self.image_y_range)
        confocal.image_z_range = np.copy(self.image_z_range)
        confocal.xy_resolution = self.xy_resolution
        confocal.z_resolution = self.z_resolution
        confocal._xy_line_pos = self.xy_line_position
        confocal._depth_line_pos = self.depth_line_position
        confocal._xyscan_continuable = self.xy_scan_continuable
        confocal._zscan_continuable = self.depth_scan_continuable
        confocal.TiltCorrection = self.tilt_correction
        confocal.point1 = np.copy(self.point1)
        confocal.point2 = np.copy(self.point2)
        confocal.point3 = np.copy(self.point3)
        confocal._tiltreference_x = self.tilt_reference_x
        confocal._tiltreference_y = self.tilt_reference_y
        confocal._tilt_variable_ax = self.tilt_slope_x
        confocal._tilt_variable_ay = self.tilt_slope_y

        confocal.initialize_image()
        try:
            if confocal.xy_image.shape == self.xy_image.shape:
                confocal.xy_image = np.copy(self.xy_image)
        except AttributeError:
            self.xy_image = np.copy(confocal.xy_image)

        confocal._zscan = True
        confocal.initialize_image()
        try:
            if confocal.depth_image.shape == self.depth_image.shape:
                confocal.depth_image = np.copy(self.depth_image)
        except AttributeError:
            self.depth_image = np.copy(confocal.depth_image)
        confocal._zscan = False

    def snapshot(self, confocal):
        """ Extract all necessary data from a confocal logic and keep it for later use """
        self.current_x = confocal._current_x
        self.current_y = confocal._current_y
        self.current_z = confocal._current_z
        self.current_a = confocal._current_a
        self.image_x_range = np.copy(confocal.image_x_range)
        self.image_y_range = np.copy(confocal.image_y_range)
        self.image_z_range = np.copy(confocal.image_z_range)
        self.xy_resolution = confocal.xy_resolution
        self.z_resolution = confocal.z_resolution
        self.xy_line_position = confocal._xy_line_pos
        self.depth_line_position = confocal._depth_line_pos
        self.xy_scan_continuable = confocal._xyscan_continuable
        self.depth_scan_continuable = confocal._zscan_continuable
        self.tilt_correction = confocal.TiltCorrection
        self.point1 = np.copy(confocal.point1)
        self.point2 = np.copy(confocal.point2)
        self.point3 = np.copy(confocal.point3)
        self.tilt_reference_x = confocal._tiltreference_x
        self.tilt_reference_y = confocal._tiltreference_y
        self.tilt_slope_x = confocal._tilt_variable_ax
        self.tile_slope_y = confocal._tilt_variable_ay
        self.xy_image = np.copy(confocal.xy_image)
        self.depth_image = np.copy(confocal.depth_image)


    def serialize(self):
        """ Give out a dictionary that can be saved via the usual means """
        serialized = dict()
        serialized['focus_position'] = [self.current_x, self.current_y, self.current_z, self.current_a]
        serialized['x_range'] = self.image_x_range
        serialized['y_range'] = self.image_y_range
        serialized['z_range'] = self.image_z_range
        serialized['xy_resolution'] = self.xy_resolution
        serialized['z_resolution'] = self.z_resolution
        serialized['xy_line_position'] = self.xy_line_position
        serialized['depth_linne_position'] = self.depth_line_position
        serialized['xy_scan_cont'] = self.xy_scan_continuable
        serialized['depth_scan_cont'] = self.depth_scan_continuable
        serialized['tilt_correction'] = self.tilt_correction
        serialized['tilt_point1'] = self.point1
        serialized['tilt_point2'] = self.point2
        serialized['tilt_point3'] = self.point3
        serialized['tilt_reference'] = [self.tilt_reference_x, self.tilt_reference_y]
        serialized['tilt_slope'] = [self.tilt_slope_x, self.tilt_slope_y]
        serialized['xy_image'] = numpy_to_b(image=self.xy_image)
        serialized['depth_image'] = numpy_to_b(image=self.depth_image)
        return serialized


    def deserialize(self, serialized):
        """ Restore Confocal history object from a dict """
        if 'focus_position' in serialized and len(serialized['focus_position']) == 4:
            self.current_x = serialized['focus_position'][0]
            self.current_y = serialized['focus_position'][1]
            self.current_z = serialized['focus_position'][2]
            self.current_a = serialized['focus_position'][3]
        if 'x_range' in serialized and len(serialized['x_range']) == 2:
            self.image_x_range = serialized['x_range']
        if 'y_range' in serialized and len(serialized['y_range']) == 2:
            self.image_y_range = serialized['y_range']
        if 'z_range' in serialized and len(serialized['z_range']) == 2:
            self.image_z_range = serialized['z_range']
        if 'xy_resolution' in serialized:
            self.xy_resolution = serialized['xy_resolution']
        if 'z_resolution' in serialized:
            self.z_resolution = serialized['z_resolution']
        if 'tilt_correction' in serialized:
            self.tilt_correction = serialized['tilt_correction']
        if 'tilt_reference' in serialized and len(serialized['tilt_reference']) == 2:
            self.tilt_reference_x = serialized['tilt_reference'][0]
            self.tilt_reference_y = serialized['tilt_reference'][1]
        if 'tilt_slope' in serialized and len(serialized['tilt_slope']) == 2:
            self.tilt_slope_x = serialized['tilt_slope'][0]
            self.tilt_slope_y = serialized['tilt_slope'][1]
        if 'tilt_point1' in serialized and len(serialized['tilt_point1'] ) == 3:
            self.point1 = np.array(serialized['tilt_point1'])
        if 'tilt_point2' in serialized and len(serialized['tilt_point2'] ) == 3:
            self.point2 = np.array(serialized['tilt_point2'])
        if 'tilt_point3' in serialized and len(serialized['tilt_point3'] ) == 3:
            self.point3 = np.array(serialized['tilt_point3'])
        if 'xy_image' in serialized:
            self.xy_image = numpy_from_b(serialized['xy_image'])['image']
        if 'depth_image' in serialized:
            self.depth_image = numpy_from_b(serialized['depth_image'])['image']


class ConfocalLogic(GenericLogic):
    """unstable: Christoph Müller
    This is the Logic class for confocal scanning.
    """
    _modclass = 'confocallogic'
    _modtype = 'logic'

    # declare connectors
    _in = { 'confocalscanner1': 'ConfocalScannerInterface',
            'savelogic': 'SaveLogic'
            }
    _out = {'scannerlogic': 'ConfocalLogic'}

    # signals
    signal_start_scanning = QtCore.Signal()
    signal_continue_scanning = QtCore.Signal()
    signal_scan_lines_next = QtCore.Signal()
    signal_xy_image_updated = QtCore.Signal()
    signal_depth_image_updated = QtCore.Signal()
    signal_change_position = QtCore.Signal(str)

    sigImageXYInitialized = QtCore.Signal()
    sigImageDepthInitialized = QtCore.Signal()

    signal_history_event = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        # declare actions for state transitions
        state_actions = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        super().__init__(manager=manager, name=name, config=config,
                callbacks=state_actions, **kwargs)

        self.logMsg('The following configuration was found.', msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key, config[key]), msgType='status')


        #locking for thread safety
        self.threadlock = Mutex()

        # counter for scan_image
        self._scan_counter = 0
        self._zscan = False
        self.stopRequested = False
        self.depth_scan_dir_is_xz = True
        self.permanent_scan = False


    def activation(self, e):
        """ Initialisation performed during activation of the module.

        @param e: error code
        """
        self._scanning_device = self.connector['in']['confocalscanner1']['object']
#        print("Scanning device is", self._scanning_device)

        self._save_logic = self.connector['in']['savelogic']['object']

        #default values for clock frequency and slowness
        #slowness: steps during retrace line
        if 'clock_frequency' in self._statusVariables:
            self._clock_frequency = self._statusVariables['clock_frequency']
        else:
            self._clock_frequency = 1000.
        if 'return_slowness' in self._statusVariables:
            self.return_slowness = self._statusVariables['return_slowness']
        else:
            self.return_slowness = 50

        # Reads in the maximal scanning range. The unit of that scan range is micrometer!
        self.x_range = self._scanning_device.get_position_range()[0]
        self.y_range = self._scanning_device.get_position_range()[1]
        self.z_range = self._scanning_device.get_position_range()[2]

        # restore here ...
        self.history = []
        if 'max_history_length' in self._statusVariables:
                self.max_history_length = self._statusVariables ['max_history_length']
                for i in reversed(range(1, self.max_history_length)):
                    try:
                        new_history_item = ConfocalHistoryEntry(self)
                        new_history_item.deserialize(self._statusVariables['history_{}'.format(i)])
                        self.history.append(new_history_item)
                    except:
                        pass
        else:
            self.max_history_length = 10
        try:
            new_state = ConfocalHistoryEntry(self)
            new_state.deserialize(self._statusVariables['history_0'])
            new_state.restore(self)
        except:
            new_state = ConfocalHistoryEntry(self)
            new_state.restore(self)
        finally:
            self.history.append(new_state)

        self.history_index = len(self.history) - 1

        # Sets connections between signals and functions
        self.signal_scan_lines_next.connect(self._scan_line, QtCore.Qt.QueuedConnection)
        self.signal_start_scanning.connect(self.start_scanner, QtCore.Qt.QueuedConnection)
        self.signal_continue_scanning.connect(self.continue_scanner, QtCore.Qt.QueuedConnection)

        self._change_position('activation')


    def deactivation(self, e):
        """ Reverse steps of activation

        @param e: error code

        @return int: error code (0:OK, -1:error)
        """
        self._statusVariables['clock_frequency'] = self._clock_frequency
        self._statusVariables['return_slowness'] = self.return_slowness
        self._statusVariables['max_history_length'] = self.max_history_length
        closing_state = ConfocalHistoryEntry(self)
        closing_state.snapshot(self)
        self.history.append(closing_state)
        histindex = 0
        for state in reversed(self.history):
            self._statusVariables['history_{}'.format(histindex)] = state.serialize()
            histindex += 1
        return 0


    def switch_hardware(self, to_on=False):
        """ Switches the Hardware off or on.

        @param to_on: True switches on, False switched off

        @return int: error code (0:OK, -1:error)
        """

        if to_on:
            return self._scanning_device.activation()
        else:
            return self._scanning_device.reset_hardware()


    def testing(self):
        """ Debug method. """
        print ('testing')
#        self.start_scanner()
#        self.set_position('testing', x = 1., y = 2., z = 3., a = 4.)
#        self.start_scanning()
#        self.kill_scanner()


    def set_clock_frequency(self, clock_frequency):
        """Sets the frequency of the clock

        @param int clock_frequency: desired frequency of the clock

        @return int: error code (0:OK, -1:error)
        """
        self._clock_frequency = int(clock_frequency)
        #checks if scanner is still running
        if self.getState() == 'locked':
            return -1
        else:
            return 0


    def start_scanning(self, zscan = False):
        """Starts scanning

        @param bool zscan: zscan if true, xyscan if false

        @return int: error code (0:OK, -1:error)
        """
        # TODO: this is dirty, but it works for now
#        while self.getState() == 'locked':
#            time.sleep(0.01)
        self._scan_counter = 0
        self._zscan=zscan
        if self._zscan:
            self._zscan_continuable=True
        else:
            self._xyscan_continuable=True

        self.signal_start_scanning.emit()
        return 0


    def continue_scanning(self,zscan):
        """Continue scanning

        @return int: error code (0:OK, -1:error)
        """
        self._zscan = zscan
        if zscan:
            self._scan_counter = self._depth_line_pos
        else:
            self._scan_counter = self._xy_line_pos
        self.signal_continue_scanning.emit()
        return 0


    def stop_scanning(self):
        """Stops the scan

        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.getState() == 'locked':
                self.stopRequested = True
        return 0


    def initialize_image(self):
        """Initalization of the image.

        @return int: error code (0:OK, -1:error)
        """

        # x1: x-start-value, x2: x-end-value
        x1, x2 = self.image_x_range[0], self.image_x_range[1]
        # y1: x-start-value, y2: x-end-value
        y1, y2 = self.image_y_range[0], self.image_y_range[1]
        # z1: x-start-value, z2: x-end-value
        z1, z2 = self.image_z_range[0], self.image_z_range[1]

        # Checks if the x-start and x-end value are ok
        if x2 < x1:
            self.logMsg('x1 must be smaller than x2, but they are ({0:.3f},{1:.3f}).'.format(x1, x2), msgType='error')
            return -1

        if self._zscan:
            # creates an array of evenly spaced numbers over the interval
            # x1, x2 and the spacing is equal to xy_resolution
            self._X = np.linspace(x1, x2, self.xy_resolution)
            # Checks if the z-start and z-end value are ok
            if z2 < z1:
                self.logMsg('z1 must be smaller than z2, but they are ({0:.3f},{1:.3f}).'.format(z1, z2), msgType='error')
                return -1
            # creates an array of evenly spaced numbers over the interval
            # z1, z2 and the spacing is equal to z_resolution
            self._Z = np.linspace(z1, z2, self.z_resolution)
        else:
            # Checks if the y-start and y-end value are ok
            if y2 < y1:
                self.logMsg('y1 must be smaller than y2, but they are ({0:.3f},{1:.3f}).'.format(y1, y2), msgType='error')
                return -1

            # prevents distorion of the image
            if (x2-x1) >= (y2-y1):
                self._X = np.linspace(x1, x2, self.xy_resolution)
                self._Y = np.linspace(y1, y2, int(self.xy_resolution*(y2-y1)/(x2-x1)))
            else:
                self._Y = np.linspace(y1, y2, self.xy_resolution)
                self._X = np.linspace(x1, x2, int(self.xy_resolution*(x2-x1)/(y2-y1)))

        self._XL = self._X
        self._YL = self._Y
        self._AL = np.zeros(self._XL.shape)

        # Arrays for retrace line
        self._return_XL = np.linspace(self._XL[-1], self._XL[0], self.return_slowness)
        self._return_AL = np.zeros(self._return_XL.shape)

        if self._zscan:
            if self.depth_scan_dir_is_xz:
                self._image_vert_axis = self._Z
                # creates an image where each pixel will be [x,y,z,counts]
                self.depth_image = np.zeros((len(self._image_vert_axis), len(self._X), 4))
                self.depth_image[:,:,0] = np.full((len(self._image_vert_axis), len(self._X)), self._XL)
                self.depth_image[:,:,1] = self._current_y * np.ones((len(self._image_vert_axis), len(self._X)))
                z_value_matrix = np.full((len(self._X), len(self._image_vert_axis)), self._Z)
                self.depth_image[:,:,2] = z_value_matrix.transpose()
            else: # depth scan is yz instead of xz
                self._image_vert_axis = self._Z
                # creats an image where each pixel will be [x,y,z,counts]
                self.depth_image = np.zeros((len(self._image_vert_axis), len(self._Y), 4))
                self.depth_image[:,:,0] = self._current_x * np.ones((len(self._image_vert_axis), len(self._Y)))
                self.depth_image[:,:,1] = np.full((len(self._image_vert_axis), len(self._Y)), self._YL)
                z_value_matrix = np.full((len(self._Y), len(self._image_vert_axis)), self._Z)
                self.depth_image[:,:,2] = z_value_matrix.transpose()
                # now we are scanning along the y-axis, so we need a new return line along Y:
                self._return_YL = np.linspace(self._YL[-1], self._YL[0], self.return_slowness)
                self._return_AL = np.zeros(self._return_YL.shape)
            self.sigImageDepthInitialized.emit()
        else:
            self._image_vert_axis = self._Y
            # creats an image where each pixel will be [x,y,z,counts]
            self.xy_image = np.zeros((len(self._image_vert_axis), len(self._X), 4))
            self.xy_image[:,:,0] = np.full((len(self._image_vert_axis), len(self._X)), self._XL)
            y_value_matrix = np.full((len(self._X), len(self._image_vert_axis)), self._Y)
            self.xy_image[:,:,1] = y_value_matrix.transpose()
            self.xy_image[:,:,2] = self._current_z * np.ones((len(self._image_vert_axis), len(self._X)))
            self.sigImageXYInitialized.emit()
        return 0


    def start_scanner(self):
        """Setting up the scanner device and starts the scanning procedure

        @return int: error code (0:OK, -1:error)
        """

        self.lock()
        self._scanning_device.lock()
        if self.initialize_image() < 0:
            self._scanning_device.unlock()
            self.unlock()
            return -1

        returnvalue = self._scanning_device.set_up_scanner_clock(clock_frequency=self._clock_frequency)
        if returnvalue < 0:
            self._scanning_device.unlock()
            self.unlock()
            self.set_position('scanner')
            return

        returnvalue = self._scanning_device.set_up_scanner()
        if returnvalue < 0:
            self._scanning_device.unlock()
            self.unlock()
            self.set_position('scanner')
            return

        self.signal_scan_lines_next.emit()
        return 0


    def continue_scanner(self):
        """Continue the scanning procedure

        @return int: error code (0:OK, -1:error)
        """

        self.lock()
        self._scanning_device.lock()
        self._scanning_device.set_up_scanner_clock(clock_frequency=self._clock_frequency)
        self._scanning_device.set_up_scanner()
        self.signal_scan_lines_next.emit()

        return 0


    def kill_scanner(self):
        """Closing the scanner device.

        @return int: error code (0:OK, -1:error)
        """
        try:
            self._scanning_device.close_scanner()
            self._scanning_device.close_scanner_clock()
        except Exception as e:
            self.logExc('Could not even close the scanner, giving up.', msgType='error')
            raise e
        try:
            self._scanning_device.unlock()
        except Exception as e:
            self.logExc('Could not unlock scanning device.', msgType='error')

        return 0


    def set_position(self, tag, x=None, y=None, z=None, a=None):
        """Forwarding the desired new position from the GUI to the scanning device.

        @param string tag: TODO

        @param float x: if defined, changes to postion in x-direction (microns)
        @param float y: if defined, changes to postion in y-direction (microns)
        @param float z: if defined, changes to postion in z-direction (microns)
        @param float a: if defined, changes to postion in a-direction (microns)

        @return int: error code (0:OK, -1:error)
        """
        # print(tag, x, y, z)
        # Changes the respective value
        if x != None:
            self._current_x = x
        if y != None:
            self._current_y = y
        if z != None:
            self._current_z = z

        #Checks if the scanner is still running
        if self.getState() == 'locked' or self._scanning_device.getState() == 'locked':
            return -1
        else:
            self._change_position(tag)
            self.signal_change_position.emit(tag)
            return 0


    def _change_position(self, tag):
        """ Threaded method to change the hardware position.

        @return int: error code (0:OK, -1:error)
        """
        if tag == 'optimizer' or tag == 'scanner' or tag == 'activation':
            self._scanning_device.scanner_set_position(
            x = self._current_x,
            y = self._current_y,
            z = self._current_z,
            a = self._current_a
            )
        else:
            self._scanning_device.scanner_set_position(
                x = self._current_x,
                y = self._current_y,
                z = self._current_z + self._calc_dz(x=self._current_x, y=self._current_y),
                a = self._current_a
                )
        return 0


    def get_position(self):
        """Forwarding the desired new position from the GUI to the scanning device.

        @return list: with three entries x, y and z denoting the current
                      position in microns
        """
        #FIXME: change that to SI units!
        # return [
        #     self._current_x,
        #     self._current_y,
        #     self._current_z + self._calc_dz(x=self._current_x, y=self._current_y)
        #     ]
        return self._scanning_device.get_scanner_position()[:3]


    def _scan_line(self):
        """scanning an image in either depth or xy

        """
        # TODO: change z_values, if z is changed during scan!
        # stops scanning
        if self.stopRequested:
            with self.threadlock:
                self.kill_scanner()
                self.stopRequested = False
                self.unlock()
                self.signal_xy_image_updated.emit()
                self.signal_depth_image_updated.emit()
                self.set_position('scanner')
                if self._zscan :
                    self._depth_line_pos = self._scan_counter
                else:
                    self._xy_line_pos = self._scan_counter
                # add new history entry
                new_history = ConfocalHistoryEntry(self)
                new_history.snapshot(self)
                self.history.append(new_history)
                if len(self.history) > self.max_history_length:
                    self.history.pop(0)
                self.history_index = len(self.history) - 1
                return

        if self._zscan:
            if self.TiltCorrection:
                image = copy(self.depth_image)
                image[:,:,2] += self._calc_dz(x = image[:,:,0], y = image[:,:,1])
            else:
                image = self.depth_image
        else:
            if self.TiltCorrection:
                image = copy(self.xy_image)
                image[:,:,2] += self._calc_dz(x = image[:,:,0], y = image[:,:,1])
            else:
                image = self.xy_image

        try:
            if self._scan_counter == 0:
                # defines trace of positions for single line scan
                start_line = np.vstack((
                    np.linspace(self._current_x, image[self._scan_counter, 0, 0], self.return_slowness),
                    np.linspace(self._current_y, image[self._scan_counter, 0, 1], self.return_slowness),
                    np.linspace(self._current_z, image[self._scan_counter, 0, 2], self.return_slowness),
                    np.linspace(self._current_a, 0, self.return_slowness)
                    ))
                # scan of a single line
                start_line_counts = self._scanning_device.scan_line(start_line)
            # defines trace of positions for a single line scan
            line = np.vstack( (image[self._scan_counter, :, 0],
                               image[self._scan_counter, :, 1],
                               image[self._scan_counter, :, 2],
                               image[self._scan_counter, :, 3]) )
            # scan of a single line
            line_counts = self._scanning_device.scan_line(line)
            # defines trace of positions for a single return line scan
            if self.depth_scan_dir_is_xz:
                return_line = np.vstack((
                    self._return_XL,
                    image[self._scan_counter,0,1] * np.ones(self._return_XL.shape),
                    image[self._scan_counter,0,2] * np.ones(self._return_XL.shape),
                    self._return_AL
                    ))
            else:
                return_line = np.vstack((
                    image[self._scan_counter,0,1] * np.ones(self._return_YL.shape),
                    self._return_YL,
                    image[self._scan_counter,0,2] * np.ones(self._return_YL.shape),
                    self._return_AL
                    ))

            # scan of a single return-line
            # This is just needed in order to return the scanner to the start of next line
            return_line_counts = self._scanning_device.scan_line(return_line)
            # updating images
            if self._zscan:
                if self.depth_scan_dir_is_xz:
                    self.depth_image[self._scan_counter,:,3] = line_counts
                else:
                    self.depth_image[self._scan_counter,:,3] = line_counts
                self.signal_depth_image_updated.emit()
            else:
                self.xy_image[self._scan_counter,:,3] = line_counts
                self.signal_xy_image_updated.emit()
#            self.return_image[i,:] = return_line_counts
            #self.sigImageNext.emit()
        # call this again from event loop
            self._scan_counter += 1
            # stop scanning when last line scan was performed and makes scan not continuable

            if self._scan_counter >= np.size(self._image_vert_axis):
                if not self.permanent_scan:
                    self.stop_scanning()
                    if self._zscan:
                        self._zscan_continuable=False
                    else:
                        self._xyscan_continuable=False
                else:
                    self._scan_counter = 0

            self.signal_scan_lines_next.emit()

        except Exception as e:
            self.logMsg('The scan went wrong, killing the scanner.', msgType='error')
            self.stop_scanning()
            self.signal_scan_lines_next.emit()
            raise e


    def save_xy_data(self, colorscale_range=None, percentile_range=None):
        """ Save the current confocal xy data to file.

        Two files are created.  The first is the imagedata, which has a text-matrix of count values
        corresponding to the pixel matrix of the image.  Only count-values are saved here.

        The second file saves the full raw data with x, y, z, and counts at every pixel.

        A figure is also saved.

        @param: list colorscale_range (optional) The range [min, max] of the display colour scale (for the figure)

        @param: list percentile_range (optional) The percentile range [min, max] of the color scale
        """
        save_time = datetime.now()

        filepath = self._save_logic.get_path_for_module(module_name='Confocal')

        # Prepare the metadata parameters (common to both saved files):
        parameters = OrderedDict()

        parameters['X image min (micrometer)'] = self.image_x_range[0]
        parameters['X image max (micrometer)'] = self.image_x_range[1]
        parameters['X image range (micrometer)'] = self.image_x_range[1] - self.image_x_range[0]

        parameters['Y image min'] = self.image_y_range[0]
        parameters['Y image max'] = self.image_y_range[1]
        parameters['Y image range'] = self.image_y_range[1] - self.image_y_range[0]

        parameters['XY resolution (samples per range)'] = self.xy_resolution
        parameters['XY Image at z position (micrometer)'] = self._current_z

        parameters['Clock frequency of scanner (Hz)'] = self._clock_frequency
        parameters['Return Slowness (Steps during retrace line)'] = self.return_slowness

        # data for the text-array "image":
        image_data = OrderedDict()
        image_data['Confocal pure XY scan image data without axis.\n'
                   '# The upper left entry represents the signal at the upper '
                   'left pixel position.\n'
                   '# A pixel-line in the image corresponds to a row '
                   'of entries where the Signal is in counts/s:'] = self.xy_image[:,:,3]

        # Prepare a figure to be saved
        figure_data = self.xy_image[:,:,3]
        image_extent = [self.image_x_range[0],
                        self.image_x_range[1],
                        self.image_y_range[0],
                        self.image_y_range[1]
                        ]
        axes = ['X', 'Y']
        crosshair_pos = [self.get_position()[0], self.get_position()[1]]

        fig = self.draw_figure(data=figure_data,
                               image_extent=image_extent,
                               scan_axis=axes,
                               cbar_range=colorscale_range,
                               percentile_range=percentile_range,
                               crosshair_pos=crosshair_pos
                               )

        # Save the image data and figure
        filelabel = 'confocal_xy_image'
        self._save_logic.save_data(image_data,
                                   filepath,
                                   parameters=parameters,
                                   filelabel=filelabel,
                                   as_text=True,
                                   timestamp=save_time,
                                   plotfig=fig
                                   )
        #, as_xml=False, precision=None, delimiter=None)

        # prepare the full raw data in an OrderedDict:
        data = OrderedDict()
        x_data = []
        y_data = []
        z_data = []
        counts_data = []

        for row in self.xy_image:
            for entry in row:
                x_data.append(entry[0])
                y_data.append(entry[1])
                z_data.append(entry[2])
                counts_data.append(entry[3])

        data['x values (micron)'] = x_data
        data['y values (micron)'] = y_data
        data['z values (micron)'] = z_data
        data['count values (c/s)'] = counts_data

        # Save the raw data to file
        filelabel = 'confocal_xy_data'
        self._save_logic.save_data(data,
                                   filepath,
                                   parameters=parameters,
                                   filelabel=filelabel,
                                   as_text=True,
                                   timestamp=save_time
                                   )
        #, as_xml=False, precision=None, delimiter=None)

        self.logMsg('Confocal Image saved to:\n{0}'.format(filepath), msgType='status', importance=3)

    def save_depth_data(self, colorscale_range=None, percentile_range=None):
        """ Save the current confocal depth data to file.

        Two files are created.  The first is the imagedata, which has a text-matrix of count values
        corresponding to the pixel matrix of the image.  Only count-values are saved here.

        The second file saves the full raw data with x, y, z, and counts at every pixel.
        """
        save_time = datetime.now()

        filepath = self._save_logic.get_path_for_module(module_name='Confocal')

        # Prepare the metadata parameters (common to both saved files):
        parameters = OrderedDict()

        # TODO: This needs to check whether the scan was XZ or YZ direction
        parameters['X image min (micrometer)'] = self.image_x_range[0]
        parameters['X image max (micrometer)'] = self.image_x_range[1]
        parameters['X image range (micrometer)'] = self.image_x_range[1] - self.image_x_range[0]

        parameters['Z image min'] = self.image_z_range[0]
        parameters['Z image max'] = self.image_z_range[1]
        parameters['Z image range'] = self.image_z_range[1] - self.image_z_range[0]

        parameters['XY resolution (samples per range)'] = self.xy_resolution
        parameters['Z resolution (samples per range)'] = self.z_resolution
        parameters['Depth Image at y position (micrometer)'] = self._current_y

        parameters['Clock frequency of scanner (Hz)'] = self._clock_frequency
        parameters['Return Slowness (Steps during retrace line)'] = self.return_slowness

        # data for the text-array "image":
        image_data = OrderedDict()
        image_data['Confocal pure depth scan image data without axis.\n'
                   '# The upper left entry represents the signal at the upper '
                   'left pixel position.\n'
                   '# A pixel-line in the image corresponds to a row in '
                   'of entries where the Signal is in counts/s:'] = self.depth_image[:,:,3]

        # Prepare a figure to be saved
        figure_data = self.depth_image[:,:,3]

        if self.depth_scan_dir_is_xz:
            horizontal_range = [self.image_x_range[0], self.image_x_range[1]]
            axes = ['X', 'Z']
            crosshair_pos = [self.get_position()[0], self.get_position()[2]]
        else:
            horizontal_range = [self.image_y_range[0], self.image_y_range[1]]
            axes = ['Y', 'Z']
            crosshair_pos = [self.get_position()[1], self.get_position()[2]]

        image_extent = [horizontal_range[0],
                        horizontal_range[1],
                        self.image_z_range[0],
                        self.image_z_range[1]
                        ]

        fig = self.draw_figure(data=figure_data,
                               image_extent=image_extent,
                               scan_axis=axes,
                               cbar_range=colorscale_range,
                               percentile_range=percentile_range,
                               crosshair_pos=crosshair_pos
                               )

        # Save the image data and figure
        filelabel = 'confocal_xy_image'
        self._save_logic.save_data(image_data,
                                   filepath,
                                   parameters=parameters,
                                   filelabel=filelabel,
                                   as_text=True,
                                   timestamp=save_time,
                                   plotfig=fig
                                   )
        #, as_xml=False, precision=None, delimiter=None)

        # prepare the full raw data in an OrderedDict:
        data = OrderedDict()
        x_data = []
        y_data = []
        z_data = []
        counts_data = []

        for row in self.depth_image:
            for entry in row:
                x_data.append(entry[0])
                y_data.append(entry[1])
                z_data.append(entry[2])
                counts_data.append(entry[3])

        data['x values (micros)'] = x_data
        data['y values (micros)'] = y_data
        data['z values (micros)'] = z_data
        data['count values (micros)'] = counts_data

        # Save the raw data to file
        filelabel = 'confocal_depth_data'
        self._save_logic.save_data(data,
                                   filepath,
                                   parameters=parameters,
                                   filelabel=filelabel,
                                   as_text=True,
                                   timestamp=save_time
                                   )
        #, as_xml=False, precision=None, delimiter=None)

        self.logMsg('Confocal Image saved to:\n{0}'.format(filepath), msgType='status', importance=3)

    def draw_figure(self, data, image_extent, scan_axis=['X', 'Y'], cbar_range=None, percentile_range=None,  crosshair_pos=None):
        """ Create a 2-D color map figure of the scan image.

        @param: array data: The NxM array of count values from a scan with NxM pixels.

        @param: list image_extent: The scan range in the form [hor_min, hor_max, ver_min, ver_max]

        @param: list axes: Names of the horizontal and vertical axes in the image

        @param: list cbar_range: (optional) [color_scale_min, color_scale_max].  If not supplied then a default of
                                 data_min to data_max will be used.

        @param: list percentile_range: (optional) Percentile range of the chosen cbar_range.

        @param: list crosshair_pos: (optional) crosshair position as [hor, vert] in the chosen image axes.

        @return: fig fig: a matplotlib figure object to be saved to file.
        """

        # If no colorbar range was given, take full range of data
        if cbar_range is None:
            cbar_range = [np.min(data), np.max(data)]

        # Scale color values using SI prefix
        prefix = ['', 'k', 'M', 'G']
        prefix_count = 0
        image_data = data
        draw_cb_range = np.array(cbar_range)

        while draw_cb_range[1] > 1000:
            image_data = image_data/1000
            draw_cb_range = draw_cb_range/1000
            prefix_count = prefix_count + 1

        c_prefix = prefix[prefix_count]

        # Use qudi style
        plt.style.use(self._save_logic.mpl_qd_style)

        # Create figure
        fig, ax = plt.subplots()

        # Create image plot
        cfimage = ax.imshow(image_data,
                            cmap=plt.get_cmap('inferno'), # reference the right place in qd
                            origin="lower",
                            vmin=draw_cb_range[0],
                            vmax=draw_cb_range[1],
                            interpolation='none',
                            extent=image_extent
                            )

        ax.set_aspect(1)
        ax.set_xlabel(scan_axis[0] + ' position (um)')
        ax.set_ylabel(scan_axis[1] + ' position (um)')
        ax.spines['bottom'].set_position(('outward', 10))
        ax.spines['left'].set_position(('outward', 10))
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.get_xaxis().tick_bottom()
        ax.get_yaxis().tick_left()

        # draw the crosshair position if defined
        if crosshair_pos is not None:
            trans_xmark = mpl.transforms.blended_transform_factory(
                ax.transData,
                ax.transAxes)

            trans_ymark = mpl.transforms.blended_transform_factory(
                ax.transAxes,
                ax.transData)

            ax.annotate('', xy=(crosshair_pos[0], 0), xytext=(crosshair_pos[0], -0.01), xycoords=trans_xmark,
                        arrowprops=dict(facecolor='#17becf', shrink=0.05),
                        )

            ax.annotate('', xy=(0, crosshair_pos[1]), xytext=(-0.01, crosshair_pos[1]), xycoords=trans_ymark,
                        arrowprops=dict(facecolor='#17becf', shrink=0.05),
                        )

        # Draw the colorbar
        cbar = plt.colorbar(cfimage, shrink=0.8)#, fraction=0.046, pad=0.08, shrink=0.75)
        cbar.set_label('Fluorescence (' + c_prefix + 'c/s)')

        # remove ticks from colorbar for cleaner image
        cbar.ax.tick_params(which=u'both', length=0)

        # If we have percentile information, draw that to the figure
        if percentile_range is not None:
            cbar.ax.annotate(str(percentile_range[0]),
                             xy=(-0.3, 0.0),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )
            cbar.ax.annotate(str(percentile_range[1]),
                             xy=(-0.3, 1.0),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )
            cbar.ax.annotate('(percentile)',
                             xy=(-0.3, 0.5),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )

        return fig

    def set_tilt_point1(self):
        """ Gets the first reference point for tilt correction."""
        self.point1 = np.array((self._current_x, self._current_y, self._current_z))

    def set_tilt_point2(self):
        """ Gets the second reference point for tilt correction."""

        self.point2 = np.array((self._current_x, self._current_y, self._current_z))

    def set_tilt_point3(self):
        """Gets the third reference point for tilt correction."""

        self.point3 = np.array((self._current_x, self._current_y, self._current_z))


    def calc_tilt_correction(self):
        """Calculates the values for the tilt correction."""

        # I took this from the old code, maybe we should double-check the formulas, but so far it worked...
        a = self.point2 - self.point1
        b = self.point3 - self.point1
        # guys is there really no cross product?????
        n = np.array((
            a[1]*b[2] - a[2]*b[1],
            a[2]*b[0] - a[0]*b[2],
            a[0]*b[1] - a[1]*b[0]
             ))
        self._tilt_variable_ax = n[0] / n[2]
        self._tilt_variable_ay = n[1] / n[2]


    def _calc_dz(self, x, y):
        """Calculates the change in z for given tilt correction."""

        # I took this from the old code, maybe we should double-check the formulas, but so far it worked...
        if not self.TiltCorrection:
            return 0.
        else:
            dz = -( (x - self._tiltreference_x)*self._tilt_variable_ax + (y - self._tiltreference_y)*self._tilt_variable_ay )
            return dz

    def history_forward(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.history[self.history_index].restore(self)
            self.signal_xy_image_updated.emit()
            self.signal_depth_image_updated.emit()
            self._change_position('history')
            self.signal_change_position.emit('history')
            self.signal_history_event.emit()

    def history_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.history[self.history_index].restore(self)
            self.signal_xy_image_updated.emit()
            self.signal_depth_image_updated.emit()
            self._change_position('history')
            self.signal_change_position.emit('history')
            self.signal_history_event.emit()
