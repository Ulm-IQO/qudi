"""
This file contains the QuDi Interfuse between Magnet Logic and Motor Hardware.

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
Copyright (C) 2016 Florian Frank alexander.stark@uni-ulm.de
"""

from logic.generic_logic import GenericLogic
from interface.confocal_scanner_interface import ConfocalScannerInterface
import numpy as np

class ScannerIntefuse(GenericLogic, ConfocalScannerInterface):

    _modclass = 'ScannerInterfuse'
    _modtype = 'interfuse'

    _in = {'confocalscanner1': 'ConfocalScannerInterface'}
    _out = {'confocalscanner1': 'ConfocalScannerInterface'}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._tiltcorrection = False
        self._tilt_reference_x = 0
        self._tilt_reference_y = 0

    def on_activate(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """
        self._scanning_device = self.connector['in']['confocalscanner1']['object']

    def on_deactivate(self,e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        pass

    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs
            can access it.

        @return int: error code (0:OK, -1:error)
        """

        self._scanning_device.reset_hardware()

    def get_position_range(self):
        """ Returns the physical range of the scanner.

        @return float [4][2]: array of 4 ranges with an array containing lower
                              and upper limit
        """

        return self._scanning_device.get_position_range()

    def set_position_range(self, myrange=[[0, 1], [0, 1], [0, 1], [0, 1]]):
        """ Sets the physical range of the scanner.

        @param float [4][2] myrange: array of 4 ranges with an array containing
                                     lower and upper limit

        @return int: error code (0:OK, -1:error)
        """

        self._scanning_device.set_position_range(myrange)

    def set_voltage_range(self, myrange=[-10., 10.]):
        """ Sets the voltage range of the NI Card.

        @param float [2] myrange: array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """

        self._scanning_device.set_voltage_range(myrange)

    def set_up_scanner_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of the
                                      clock
        @param str clock_channel: if defined, this is the physical channel of
                                  the clock

        @return int: error code (0:OK, -1:error)
        """

        self._scanning_device.set_up_scanner_clock(clock_frequency,clock_channel)

    def set_up_scanner(self, counter_channel=None, photon_source=None,
                       clock_channel=None, scanner_ao_channels=None):
        """ Configures the actual scanner with a given clock.

        @param str counter_channel: if defined, this is the physical channel
                                    of the counter
        @param str photon_source: if defined, this is the physical channel where
                                  the photons are to count from
        @param str clock_channel: if defined, this specifies the clock for the
                                  counter
        @param str scanner_ao_channels: if defined, this specifies the analoque
                                        output channels

        @return int: error code (0:OK, -1:error)
        """

        self._scanning_device.set_up_scanner(counter_channel,photon_source,clock_channel,
                                             scanner_ao_channels)

    def scanner_set_position(self, x=None, y=None, z=None, a=None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).

        @param float x: postion in x-direction (volts)
        @param float y: postion in y-direction (volts)
        @param float z: postion in z-direction (volts)
        @param float a: postion in a-direction (volts)

        @return int: error code (0:OK, -1:error)
        """

        if self._tiltcorrection:
            z = z+self._calc_dz(x,y)
            z_min = self.get_position_range()[2][0]
            z_max = self.get_position_range()[2][1]
            if z<z_min or z>z_max:
                z = min(max(z,z_min),z_max)
                self.logMsg('The entered z position is out of scanner range! z was set to min/max.'
                            ,msgType='warning')
            self._scanning_device.set_position(x,y,z,a)
        else:
            self._scanning_device.set_position(x,y,z,a)

    def get_scanner_position(self):
        """ Get the current position of the scanner hardware.

        @return float[]: current position in (x, y, z, a).
        """
        position = self._scanning_device.get_position()         # not tested atm
        if self._tiltcorrection:
            position[2] = position[2]-self._calc_dz(position[0],position[1])
            return position
        else:
            return position


    def set_up_line(self, length=100):
        """ Sets up the analoque output for scanning a line.

        @param int length: length of the line in pixel

        @return int: error code (0:OK, -1:error)
        """

        self._scanning_device.set_up_line(length)

    def scan_line(self, line_path=None):
        """ Scans a line and returns the counts on that line.

        @param float[][4] line_path: array of 4-part tuples defining the
                                     positions pixels

        @return float[]: the photon counts per second
        """

        if self._tiltcorrection:
            line_path[:][2] = line_path[:][2] + self._calc_dz(line_path[:][0],line_path[:][1])
        self._scanning_device.scan_line(line_path)

    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """

        self._scanning_device.close_scanner()

    def close_scanner_clock(self, power=0):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """

        self._scanning_device.close_scanner_clock()

    ###############################################################################################
    ################################### Tiltcorrection Stuff ######################################
    ###############################################################################################

    def set_tilt_point1(self):
        """ Gets the first reference point for tilt correction."""
        self.point1 = self.get_scanner_position()[:3]

    def set_tilt_point2(self):
        """ Gets the second reference point for tilt correction."""
        self.point2 = self.get_scanner_position()[:3]

    def set_tilt_point3(self):
        """Gets the third reference point for tilt correction."""
        self.point3 = self.get_scanner_position()[:3]

    def calc_tilt_correction(self):
        """Calculates the values for the tilt correction."""
        a = self.point2 - self.point1
        b = self.point3 - self.point1
        n = np.cross(a,b)
        self._tilt_variable_ax = n[0] / n[2]
        self._tilt_variable_ay = n[1] / n[2]

    def _calc_dz(self, x, y):
        """Calculates the change in z for given tilt correction."""
        if not self._tiltcorrection:
            return 0.
        else:
            dz = -((x - self._tilt_reference_x)*self._tilt_variable_ax+(y - self._tilt_reference_y)
                    *self._tilt_variable_ay )
            return dz

    def activate_tiltcorrection(self):
        self._tiltcorrection = True
        self._tilt_reference_x = self.get_scanner_position()[0]
        self._tilt_reference_y = self.get_scanner_position()[1]

    def deactivate_tiltcorrection(self):
        self._tiltcorrection = False
        self._tilt_reference_x = self.get_scanner_position()[0]
        self._tilt_reference_y = self.get_scanner_position()[1]
