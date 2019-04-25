# -*- coding: utf-8 -*-
"""
Interfuse to do confocal scans with any stage that satisfies the 
qudi motor interface, and with APD counts at the counter logic.
This limited by timing latency of the USB connection.

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

import time
import numpy as np

from core.module import Base, Connector, ConfigOption
from interface.confocal_scanner_interface import ConfocalScannerInterface


class ScannerMotorInterfuse(Base, ConfocalScannerInterface):

    """Interfuse to combine a motor stage with the slow counter for simple confocal scanning.
    
    This allows confocal scanning to be simply performed with
    general hardware, but has slow speed because it needs to "think" per pixel
    rather than per scanline. This interfuse appears as a Confocal Scanner
    that can be connected to Confocal Logic.

    unstable: Lachlan J. Rogers; diamond2nv@GitHub

    Example test config for actual hardware:

    #(logic:)

    counter:
        module.Class: 'counter_logic.CounterLogic'
        connect:
            counter1: 'mydummycounter'
            savelogic: 'save'

    piezo_scanner_interfuse:
        module.Class: 'interfuse.confocal_scanner_motor_interfuse.ScannerMotorInterfuse'
        connect:
            counterlogic: 'counter'
            stage1: 'piezo_stage_nanos' #TODO: This need actual hardware.

    scanner:
        module.Class: 'confocal_logic.ConfocalLogic'
        connect:
            confocalscanner1: 'piezo_scanner_interfuse'
            savelogic: 'save'

    """
    _modclass = 'confocalscannerinterface'
    _modtype = 'hardware'

    # connectors
    counterlogic = Connector(interface='CounterLogic')
    stage1 = Connector(interface='MotorInterface')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # Internal parameters
        self._line_length = None

        self._num_points = 500

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        self._counter_logic = self.get_connector('counterlogic')
        self._stage_hw = self.get_connector('stage1')

        self._position_range = self.get_position_range()
        self._current_position = [0., 0., 0.]

        # The number of counter logic bins to include in count data for a scan pixel
        self._dwell_cnt_bins = 1

        # The dwell time (seconds) to wait before sampling counter logic counts for the scan pixel
        self._dwell_delay = 0.02

    def on_deactivate(self):
        self.reset_hardware()

    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs can access it.

        @return int: error code (0:OK, -1:error)
        """
        self._scanner_hw.abort()
        self.log.warning('TODO: reset Stage.')
        return 0

    def get_position_range(self):
        """ Returns the physical range of the scanner.
        This is a direct pass-through to the scanner HW.

        @return float [4][2]: array of 4 ranges with an array containing lower and upper limit
        """
        hw_constraints = self._stage_hw.get_constraints()

        pos_range = np.zeros((4, 2))

        if 'x' in hw_constraints.keys():
            pos_range[0] = self._constraints_to_range(hw_constraints, 'x')
        if 'y' in hw_constraints.keys():
            pos_range[1] = self._constraints_to_range(hw_constraints, 'y')
        if 'z' in hw_constraints.keys():
            pos_range[2] = self._constraints_to_range(hw_constraints, 'z')
        
        return pos_range

    def set_position_range(self, myrange=None):
        """ Sets the physical range of the scanner.
        This is a direct pass-through to the scanner HW

        @param float [4][2] myrange: array of 4 ranges with an array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        # TODO
        self.log.warning('Cannot set position range yet - fix TODO')

        return 0

    def set_voltage_range(self, myrange=None):
        """ Sets the voltage range of the NI Card.
        This is a direct pass-through to the scanner HW

        @param float [2] myrange: array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        # TODO
        self.log.warning('Voltage range is not sensible for PiezoStagePI. Fix TODO')

        return 0

    def get_scanner_count_channels(self):
        """ Returns the list of channels that are recorded while scanning an image.

        @return list(str): channel names

        Most methods calling this might just care about the number of channels.
        """
        #TODO: get_scanner_count_channels
        return ['APD1']

    def set_up_scanner_clock(self, clock_frequency = None, clock_channel = None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.
        This is a direct pass-through to the scanner HW

        @param float clock_frequency: if defined, this sets the frequency of the clock
        @param string clock_channel: if defined, this is the physical channel of the clock

        @return int: error code (0:OK, -1:error)
        """

        #return self._scanner_hw.set_up_scanner_clock(clock_frequency=clock_frequency, clock_channel=clock_channel)
        return 0

    def set_up_scanner(self, counter_channel = None, photon_source = None, clock_channel = None, scanner_ao_channels = None):
        """ Configures the actual scanner with a given clock.

        TODO this is not technically required, because the spectrometer scanner does not need clock synchronisation.

        @param string counter_channel: if defined, this is the physical channel of the counter
        @param string photon_source: if defined, this is the physical channel where the photons are to count from
        @param string clock_channel: if defined, this specifies the clock for the counter
        @param string scanner_ao_channels: if defined, this specifies the analoque output channels

        @return int: error code (0:OK, -1:error)
        """
        return 0

    def get_scanner_axes(self):
        """ Pass through scanner axes. """
        return ['x', 'y', 'z', 'a']

    def scanner_set_position(self, x = None, y = None, z = None, a = None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).
        This is a direct pass-through to the scanner HW

        @param float x: postion in x-direction (volts)
        @param float y: postion in y-direction (volts)
        @param float z: postion in z-direction (volts)
        @param float a: postion in a-direction (volts)

        @return int: error code (0:OK, -1:error)
        """

        move_dict = {}
        move_dict['x'] = x
        move_dict['y'] = y
        move_dict['z'] = z
        try:
            self._stage_hw.move_abs(move_dict)
            return 0
        except:
            self.log.error("Can't set stage position. Check device connection!")
            return -1

    def get_scanner_position(self):
        """ Get the current position of the scanner hardware.

        @return float[]: current position in (x, y, z, a).
        """
        prange = self.get_position_range()
        position = [0., 0., 0.]
        for i in range(3):
            position[i] = prange[i].mean()
            
        try:
            pos_dict = self._stage_hw.get_pos()

            position = [pos_dict['x'], pos_dict['y'], pos_dict['z'], 0]

        except:
            self.log.error("Can't get stage position. Check device connection!")

        return position
    
    def on_target(self):
        """ Stage will move all axes to targets 
        and waits until the motion has finished.
        Maybe useful in scan line began.

        @return int: error code (0:OK, -1:error)
        """
        result = self._stage_hw.on_target()

        return result

    def set_up_line(self, length=100):
        """ Set the line length
        Nothing else to do here, because the line will be scanned using multiple scanner_set_position calls.

        @param int length: length of the line in pixel

        @return int: error code (0:OK, -1:error)
        """
        self._line_length = length
        return 0

    def scan_line(self, line_path=None, pixel_clock=False):
        """ Scans a line and returns the counts on that line.

        @param float[][4] line_path: array of 4-part tuples defining the voltage points
        TODO: This SHOULD NOT be voltage - it should be position in metres or unit-sensitive distance.

        @param bool pixel_clock: whether we need to output a pixel clock for this line

        @return float[]: the photon counts per second
        """

        #if self.getState() == 'locked':
        #    self.log.error('A scan_line is already running, close this one first.')
        #    return -1
        #
        #self.lock()

        if not isinstance(line_path, (frozenset, list, set, tuple, np.ndarray, )):
            self.log.error('The given line to scan is not the right format or array type.')
            return np.array([-1.])

        self.set_up_line(np.shape(line_path)[1])

        count_data = np.zeros(self._line_length)
        # TODO: is it necessary for line_length to be a class variable?

        for i in range(self._line_length):
            coords = line_path[:, i]
            self.scanner_set_position(x=coords[0], y=coords[1], z=coords[2], a=coords[3])

            if i is 0:
                self.on_target()
                #waits until the motion has finished
                #time.sleep(self._dwell_delay)
            else:
                time.sleep(self._dwell_delay)
                # dwell to accumulate count data

                #self.on_target()
                #waits until the motion has finished,slow for pixel

            # record count data
            # TODO: how to ensure count begin after stage on target, 
            # and count for as same time as every pixel ? 
            this_count_data = self._counter_logic.countdata[0, -self._dwell_cnt_bins:]
            count_data[i] = np.mean(this_count_data)

        return np.array([count_data]).T

    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        try:
            self._scanner_hw.abort()
        except:
            self.log.error("Can't close scanner. Check device connection!")
            return -1

        return 0

    def close_scanner_clock(self):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        #self._scanner_hw.close_scanner_clock()
        return 0

    def set_dwell_count_bins(self, num_of_bins):
        """ Sets the number of bins to be considered from counter logic when providing the count data
        at a pixel.

        @param int num_of_bins: How many count bins of data from the counter logic will be used to
                                provide the count data at a pixel in the scan.
        @return:
        """

        self._dwell_cnt_bins = num_of_bins

    def set_dwell_delay(self, delay):
        """ Sets the dwell time. This is the waiting time before querying the counter logic
        This gives time for the count readings to accumulate before we ask for them to find the
        count value at a given "pixel".

        It is probably most sensible to set this as a multiple of  1/count_freq so that it corresponds
        to an integer number of count bins.

        @param float delay: delay time in seconds
        """
        self._dwell_delay = delay

    def get_dwell_count_bins(self):
        """

        @return int: number of count bins from counter logic that are considered for a pixel in the scan.
        """
        return self._dwell_cnt_bins

    def get_dwell_delay(self):
        """

        @return float: dwell delay time while waiting for count data to accumulate
        """
        return self._dwell_delay

    def _constraints_to_range(self, hw_constraints, axis):
        """ Turn constraints dict from hardware into the  position range
        required for the scanner interface.

        @param dict hw_constraints: dictionary from hardware file.

        @param string axis: axis name, should be 'x', 'y', or 'z'.

        @return list range: [pos_min, pos_max]
        """

        if axis not in ['x', 'y', 'z']:
            # TODO: give error
            return [0, 0]

        if 'pos_min' in hw_constraints[axis].keys():
            pos_min = hw_constraints[axis]['pos_min']
        else:
            # TODO: give error
            return [0, 0]
        
        if 'pos_max' in hw_constraints[axis].keys():
            pos_max = hw_constraints[axis]['pos_max']
        else:
            # TODO: give error
            return [0, 0]

        return [pos_min, pos_max]
