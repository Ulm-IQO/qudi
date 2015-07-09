# -*- coding: utf-8 -*-
# unstable: Christoph Müller

from logic.generic_logic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from collections import OrderedDict
import numpy as np
import time

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
    signal_change_position = QtCore.Signal()
    sigImageXYInitialized = QtCore.Signal()
    sigImageDepthInitialized = QtCore.Signal()

    # counter for scan_image
    _scan_counter = 0

    def __init__(self, manager, name, config, **kwargs):
        # declare actions for state transitions
        state_actions = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)

        self.logMsg('The following configuration was found.',
                    msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), msgType='status')

        #default values for clock frequency and slowness
        #slowness: steps during retrace line
        self._clock_frequency = 1000.
        self.return_slowness = 50

        self._zscan = False
        
        self._depth_line_pos = 0
        
        self._xy_line_pos = 0

        #locking for thread safety
        self.threadlock = Mutex()

        self.stopRequested = False

        self.yz_instead_of_xz_scan = False
        
        self.permanent_scan = False


    def activation(self, e):
        """ Initialisation performed during activation of the module.

        @param e: error code
        """
        self._scanning_device = self.connector['in']['confocalscanner1']['object']
#        print("Scanning device is", self._scanning_device)

        self._save_logic = self.connector['in']['savelogic']['object']

        # Reads in the maximal scanning range. The unit of that scan range is
        # micrometer!
        self.x_range = self._scanning_device.get_position_range()[0]
        self.y_range = self._scanning_device.get_position_range()[1]
        self.z_range = self._scanning_device.get_position_range()[2]

        # Sets the current position to the center of the maximal scanning range
        self._current_x = (self.x_range[0] + self.x_range[1]) / 2.
        self._current_y = (self.y_range[0] + self.y_range[1]) / 2.
        self._current_z = (self.z_range[0] + self.z_range[1]) / 2.
        self._current_a = 0.0

        # Sets the size of the image to the maximal scanning range
        self.image_x_range = self.x_range
        self.image_y_range = self.y_range
        self.image_z_range = self.z_range

        # Default values for the resolution of the scan
        self.xy_resolution = 100
        self.z_resolution = 50

        # Initialization of internal counter for scanning
        self._scan_counter=0

        #tilt correction stuff:
        self.TiltCorrection = False
        self._tiltreference_x = 0.5*(self.x_range[0] + self.x_range[1])
        self._tiltreference_y = 0.5*(self.y_range[0] + self.y_range[1])
        self._tilt_variable_ax = 0.
        self._tilt_variable_ay = 0.

        # Sets connections between signals and functions
        self.signal_scan_lines_next.connect(self._scan_line, QtCore.Qt.QueuedConnection)
        self.signal_change_position.connect(self._change_position, QtCore.Qt.QueuedConnection)
        self.signal_start_scanning.connect(self.start_scanner, QtCore.Qt.QueuedConnection)
        self.signal_continue_scanning.connect(self.continue_scanner, QtCore.Qt.QueuedConnection)

        self.initialize_image()
        self._zscan = True
        self.initialize_image()
        self._zscan = False


    def deactivation(self, e):
        """ Reverse steps of activation

        @param e: error code

        @return int: error code (0:OK, -1:error)
        """
        self._scanning_device.reset_hardware()
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
        pass
#        self.start_scanner()
#        self.set_position(x = 1., y = 2., z = 3., a = 4.)
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

        #TODO: this is dirty, but it works for now
#        while self.getState() == 'locked':
#            time.sleep(0.01)

        self._scan_counter = 0
        self._zscan=zscan
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
        """Stop the scan

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

        #x1: x-start-value, x2: x-end-value
        x1, x2 = self.image_x_range[0], self.image_x_range[1]
        #y1: x-start-value, y2: x-end-value
        y1, y2 = self.image_y_range[0], self.image_y_range[1]
        #z1: x-start-value, z2: x-end-value
        z1, z2 = self.image_z_range[0], self.image_z_range[1]

        #Checks if the x-start and x-end value are ok
        if x2 < x1:
            self.logMsg('x1 must be smaller than x2, but they are ({0:.3f},{1:.3f}).'.format(x1, x2),
                    msgType='error')
            return -1

        if self._zscan:
            #creates an array of evenly spaced numbers over the interval
            #x1, x2 and the spacing is equal to xy_resolution
            self._X = np.linspace(x1, x2, self.xy_resolution)
            #Checks if the z-start and z-end value are ok
            if z2 < z1:
                self.logMsg('z1 must be smaller than z2, but they are ({0:.3f},{1:.3f}).'.format(z1, z2),
                    msgType='error')
                return -1
            #creates an array of evenly spaced numbers over the interval
            #z1, z2 and the spacing is equal to z_resolution
            self._Z = np.linspace(z1, z2, self.z_resolution)
        else:
            #Checks if the y-start and y-end value are ok
            if y2 < y1:
                self.logMsg('y1 must be smaller than y2, but they are ({0:.3f},{1:.3f}).'.format(y1, y2),
                    msgType='error')
                return -1

            #prevents distorion of the image
            if (x2-x1) >= (y2-y1):
                self._X = np.linspace(x1, x2, self.xy_resolution)
                self._Y = np.linspace(y1, y2, int(self.xy_resolution*(y2-y1)/(x2-x1)))
            else:
                self._Y = np.linspace(y1, y2, self.xy_resolution)
                self._X = np.linspace(x1, x2, int(self.xy_resolution*(x2-x1)/(y2-y1)))

        self._XL = self._X
        self._YL = self._Y
        self._AL = np.zeros(self._XL.shape)

        #Arrays for retrace line
        self._return_XL = np.linspace(self._XL[-1], self._XL[0], self.return_slowness)
        self._return_AL = np.zeros(self._return_XL.shape)

        if self._zscan:
            if not self.yz_instead_of_xz_scan:
                self._image_vert_axis = self._Z
                #creats an image where each pixel will be [x,y,z,counts]
                self.depth_image = np.zeros((len(self._image_vert_axis), len(self._X), 4))
                self.depth_image[:,:,0] = np.full((len(self._image_vert_axis), len(self._X)), self._XL)
                self.depth_image[:,:,1] = self._current_y * np.ones((len(self._image_vert_axis), len(self._X)))
                z_value_matrix = np.full((len(self._X), len(self._image_vert_axis)), self._Z)
                self.depth_image[:,:,2] = z_value_matrix.transpose()
            else: # if self.xy_instead_of_xz == True
                self._image_vert_axis = self._Z
                #creats an image where each pixel will be [x,y,z,counts]
                self.depth_image = np.zeros((len(self._image_vert_axis), len(self._Y), 4))
                self.depth_image[:,:,0] = self._current_x * np.ones((len(self._image_vert_axis), len(self._Y)))
                self.depth_image[:,:,1] = np.full((len(self._image_vert_axis), len(self._Y)), self._YL)
                z_value_matrix = np.full((len(self._Y), len(self._image_vert_axis)), self._Z)
                self.depth_image[:,:,2] = z_value_matrix.transpose()
                # now we are scanning along the y-axis, so we need a new return line along Y:
                self._return_YL = np.linspace(self._YL[-1], self._YL[0], self.return_slowness)
                self._return_AL = np.zeros(self._return_YL.shape)
            # this should do the whole tilt correction for scanning
            if self.TiltCorrection:
                self.xy_image[:,:,2] += self._calc_dz(x = self.xy_image[:,:,0], y = self.xy_image[:,:,1])
            self.sigImageDepthInitialized.emit()
        else:
            self._image_vert_axis = self._Y
            #creats an image where each pixel will be [x,y,z,counts]
            self.xy_image = np.zeros((len(self._image_vert_axis), len(self._X), 4))
            self.xy_image[:,:,0] = np.full((len(self._image_vert_axis), len(self._X)), self._XL)
            y_value_matrix = np.full((len(self._X), len(self._image_vert_axis)), self._Y)
            self.xy_image[:,:,1] = y_value_matrix.transpose()
            self.xy_image[:,:,2] = self._current_z * np.ones((len(self._image_vert_axis), len(self._X)))
            # this should do the whole tilt correction for scanning
            if self.TiltCorrection:
                self.xy_image[:,:,2] += self._calc_dz(x = self.xy_image[:,:,0], y = self.xy_image[:,:,1])
            self.sigImageXYInitialized.emit()


        return 0


    def start_scanner(self):
        """Setting up the scanner device and starts the scanning procedure

        @return int: error code (0:OK, -1:error)
        """

        self.lock()
        if self.initialize_image() < 0:
            self.unlock()
            return -1

        returnvalue = self._scanning_device.set_up_scanner_clock(clock_frequency = self._clock_frequency)
        if returnvalue < 0:
            self.unlock()
            self.set_position()
            return

        returnvalue = self._scanning_device.set_up_scanner()
        if returnvalue < 0:
            self.unlock()
            self.set_position()
            return

        self.signal_scan_lines_next.emit()
        return 0


    def continue_scanner(self):
        """Continue the scanning procedure

        @return int: error code (0:OK, -1:error)
        """

        self.lock()
        self._scanning_device.set_up_scanner_clock(clock_frequency = self._clock_frequency)
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
            self.logMsg('Could not even close the scanner, giving up.', msgType='error')
            raise e

        return 0


    def set_position(self, x = None, y = None, z = None, a = None):
        """Forwarding the desired new position from the GUI to the scanning device.

        @param float x: if defined, changes to postion in x-direction (microns)
        @param float y: if defined, changes to postion in y-direction (microns)
        @param float z: if defined, changes to postion in z-direction (microns)
        @param float a: if defined, changes to postion in a-direction (microns)

        @return int: error code (0:OK, -1:error)
        """
        #Changes the respective value
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
            self.signal_change_position.emit()
            return 0


    def _change_position(self):
        """ Threaded method to change the hardware position.

        @return int: error code (0:OK, -1:error)
        """
        self._scanning_device.scanner_set_position(x = self._current_x,
                                                   y = self._current_y,
                                                   z = self._current_z + self._calc_dz(x=self._current_x, y=self._current_y),
                                                   a = self._current_a)

        return 0


    def get_position(self):
        """Forwarding the desired new position from the GUI to the scanning device.

        @return int[]: Current position
        """
        return [self._current_x, self._current_y, self._current_z]


    def _scan_line(self):
        """scanning an image in either depth or xy

        """
        #TODO: change z_values, if z is changed during scan!
        #stops scanning
        if self.stopRequested:
            with self.threadlock:
                self.kill_scanner()
                self.stopRequested = False
                self.unlock()
                self.signal_xy_image_updated.emit()
                self.signal_depth_image_updated.emit()
                self.set_position()
                if self._zscan :
                    self._depth_line_pos = self._scan_counter
                else:
                    self._xy_line_pos = self._scan_counter
                return

        if self._zscan:
            image = self.depth_image
        else:
            image = self.xy_image

        try:
            if self._scan_counter == 0:
                # defines trace of positions for single line scan
                start_line = np.vstack( (np.linspace(self._current_x, \
                                                     image[self._scan_counter,0,0], \
                                                     self.return_slowness), \
                                         np.linspace(self._current_y, \
                                                     image[self._scan_counter,0,1], \
                                                     self.return_slowness), \
                                         np.linspace(self._current_z, \
                                                     image[self._scan_counter,0,2], \
                                                     self.return_slowness), \
                                         np.linspace(self._current_a, \
                                                     0, \
                                                     self.return_slowness) ))
                # scan of a single line
                start_line_counts = self._scanning_device.scan_line(start_line)
            # defines trace of positions for a single line scan
            line = np.vstack( (image[self._scan_counter,:,0],
                               image[self._scan_counter,:,1],
                               image[self._scan_counter,:,2],
                               self._AL) )
            # scan of a single line
            line_counts = self._scanning_device.scan_line(line)
            # defines trace of positions for a single return line scan
            if not self.yz_instead_of_xz_scan:
                return_line = np.vstack( (self._return_XL,
                                      image[self._scan_counter,0,1] * np.ones(self._return_XL.shape),
                                      image[self._scan_counter,0,2] * np.ones(self._return_XL.shape),
                                      self._return_AL) )
            else:
                return_line = np.vstack( (image[self._scan_counter,0,1] * np.ones(self._return_YL.shape),
                                      self._return_YL,
                                      image[self._scan_counter,0,2] * np.ones(self._return_YL.shape),
                                      self._return_AL) )

            # scan of a single return-line
            return_line_counts = self._scanning_device.scan_line(return_line)
            # updating images
            if self._zscan:
                if not self.yz_instead_of_xz_scan:
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
            # stop scanning when last line scan was performed
            if self._scan_counter >= np.size(self._image_vert_axis):
                if not self.permanent_scan:
                    self.stop_scanning()
                else:
                    self._scan_counter = 0                    
            self.signal_scan_lines_next.emit()

        except Exception as e:
            self.logMsg('The scan went wrong, killing the scanner.', msgType='error')
            self.stop_scanning()
            self.signal_scan_lines_next.emit()
            raise e


    def save_xy_data(self):
        """ Save the current confocal xy data to a file.

        The save method saves the data in """

        filepath = self._save_logic.get_path_for_module(module_name='Confocal')

        # data for the pure image:
        image_data = OrderedDict()
        image_data['Confocal pure XY scan image data without axis.\n'
                   '# The upper left entry represents the signal at the upper '
                   'left pixel position.\n'
                   '# A pixel-line in the image corresponds to a row in '
                   'of entries where the Signal is in counts/s:'] = self.xy_image[:,:,3]

        # write the parameters:
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

        filelabel = 'confocal_xy_imagedata'
        self._save_logic.save_data(image_data, filepath, parameters=parameters,
                                   filelabel=filelabel, as_text=True)#, as_xml=False, precision=None, delimiter=None)

        # prepare the data in a dict or in an OrderedDict:
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

        data['x values (micros)'] = x_data
        data['y values (micros)'] = y_data
        data['z values (micros)'] = z_data
        data['count values (micros)'] = counts_data

        filelabel = 'confocal_xy_data'
        self._save_logic.save_data(data, filepath, parameters=parameters,
                                   filelabel=filelabel, as_text=True)#, as_xml=False, precision=None, delimiter=None)

        self.logMsg('Confocal Image saved to:\n{0}'.format(filepath),
                    msgType='status', importance=3)


    def save_depth_data(self):
        """ Save the current confocal depth data to a file. """

        filepath = self._save_logic.get_path_for_module(module_name='Confocal')

        # data for the pure image:
        image_data = OrderedDict()
        image_data['Confocal pure depth scan image data without axis.\n'
                   '# The upper left entry represents the signal at the upper '
                   'left pixel position.\n'
                   '# A pixel-line in the image corresponds to a row in '
                   'of entries where the Signal is in counts/s:'] = self.depth_image[:,:,3]

        # write the parameters:
        parameters = OrderedDict()

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

        filelabel = 'confocal_depth_imagedata'
        self._save_logic.save_data(image_data, filepath, parameters=parameters,
                                   filelabel=filelabel, as_text=True)#, as_xml=False, precision=None, delimiter=None)

        # prepare the data in a dict or in an OrderedDict:
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

        filelabel = 'confocal_depth_data'
        self._save_logic.save_data(data, filepath, parameters=parameters,
                                   filelabel=filelabel, as_text=True)#, as_xml=False, precision=None, delimiter=None)

        self.logMsg('Confocal Image saved to:\n{0}'.format(filepath),
                    msgType='status', importance=3)


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
        n = np.array( ( a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0] ) )
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
