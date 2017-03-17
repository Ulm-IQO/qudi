"""
This file contains the Qudi Interfuse between Confocal Logic and scanner Hardware as well as
Pulsed Measurements.

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

from logic.generic_logic import GenericLogic
from interface.confocal_scanner_interface import ConfocalScannerInterface
import copy
import numpy as np
import time


class ScannerMwsuperresInterfuse(GenericLogic, ConfocalScannerInterface):

    _modclass = 'ScannerMwsuperresInterfuse'
    _modtype = 'interfuse'

    _connectors = {'confocalscanner1': 'ConfocalScannerInterface',
                   'pulsedmeasurementlogic': 'PulsedMeasurementLogic',
                   'sequencegeneratorlogic': 'SequenceGeneratorLogic'}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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
        self._scanning_device = self.get_connector('confocalscanner1')
        self._pulsed_measurement = self.get_connector('pulsedmeasurementlogic')
        self._sequence_generator = self.get_connector('sequencegeneratorlogic')

        # For tilt correction
        self.tilt_variable_ax = 1
        self.tilt_variable_ay = 1
        self.tiltcorrection = False
        self.tilt_reference_x = 0
        self.tilt_reference_y = 0

        # For MW assisted superresolution scans
        self.superres_scanmode = True
        self.mw_frequencies = [2.77e9, 2.97e9]
        self.mw_amplitudes = [0.1, 0.1]
        self.pi_pulse_lengths = [100.0e-9, 100e-9]
        self.mw_channel = 'a_ch1'
        return

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
        return self._scanning_device.reset_hardware()

    def get_position_range(self):
        """ Returns the physical range of the scanner.

        @return float [4][2]: array of 4 ranges with an array containing lower
                              and upper limit
        """
        return self._scanning_device.get_position_range()

    def set_position_range(self, myrange=None):
        """ Sets the physical range of the scanner.

        @param float [4][2] myrange: array of 4 ranges with an array containing
                                     lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        if myrange is None:
            myrange = [[0, 1], [0, 1], [0, 1], [0, 1]]
        return self._scanning_device.set_position_range(myrange)

    def set_voltage_range(self, myrange=None):
        """ Sets the voltage range of the NI Card.

        @param float [2] myrange: array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        if myrange is None:
            myrange = [-10., 10.]
        return self._scanning_device.set_voltage_range(myrange)

    def get_scanner_axes(self):
        """ Pass through scanner axes """
        return self._scanning_device.get_scanner_axes()

    def get_scanner_count_channels(self):
        """ Pass through scanner counting channels """
        if self.superres_scanmode:
            count_channels = ['no_mw', 'mw_pi1', 'mw_pi2']
            # count_channels = ['superres']
        else:
            count_channels = self._scanning_device.get_scanner_count_channels()
        return count_channels

    def set_up_scanner_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of the
                                      clock
        @param str clock_channel: if defined, this is the physical channel of
                                  the clock

        @return int: error code (0:OK, -1:error)
        """
        return self._scanning_device.set_up_scanner_clock(clock_frequency, clock_channel)

    def set_up_scanner(self, counter_channel=None, photon_source=None, clock_channel=None,
                       scanner_ao_channels=None):
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
        # Set up pulse sequence
        if self.superres_scanmode:
            # generate pulse sequence
            self._sequence_generator.generate_superres_seq(name='Superres',
                                                           pi_length_1=self.pi_pulse_lengths[0],
                                                           pi_length_2=self.pi_pulse_lengths[1],
                                                           mw_freq_1=self.mw_frequencies[0],
                                                           mw_freq_2=self.mw_frequencies[1],
                                                           mw_amp_1=self.mw_amplitudes[0],
                                                           mw_amp_2=self.mw_amplitudes[1],
                                                           mw_channel=self.mw_channel)
            # Sample pulse sequence
            self._sequence_generator.sample_pulse_sequence('Superres')
            # Upload all waveforms and sequence files
            self._pulsed_measurement.upload_asset('Superres_dummy')
            self._pulsed_measurement.upload_asset('Superres_pi1')
            self._pulsed_measurement.upload_asset('Superres_pi2')
            self._pulsed_measurement.upload_asset('Superres')
            # Load sequence into channels
            self._pulsed_measurement.load_asset('Superres')

        return self._scanning_device.set_up_scanner(counter_channel, photon_source, clock_channel,
                                                    scanner_ao_channels)

    def scanner_set_position(self, x=None, y=None, z=None, a=None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).

        @param float x: postion in x-direction (volts)
        @param float y: postion in y-direction (volts)
        @param float z: postion in z-direction (volts)
        @param float a: postion in a-direction (volts)

        @return int: error code (0:OK, -1:error)
        """
        if self.tiltcorrection:
            z += self._calc_dz(x, y)
            z_min = self.get_position_range()[2][0]
            z_max = self.get_position_range()[2][1]
            if not(z_min <= z <= z_max):
                z = min(max(z, z_min), z_max)
                self.log.warning(
                    'The entered z position is out of scanner '
                    'range! z was set to min/max.')
            return self._scanning_device.scanner_set_position(x, y, z, a)
        else:
            return self._scanning_device.scanner_set_position(x, y, z, a)

    def get_scanner_position(self):
        """ Get the current position of the scanner hardware.

        @return float[]: current position in (x, y, z, a).
        """
        position = copy.copy(self._scanning_device.get_scanner_position())    # not tested atm
        if self.tiltcorrection:
            position[2] -= self._calc_dz(position[0], position[1])
            return position
        else:
            return position

    def set_up_line(self, length=100):
        """ Sets up the analoque output for scanning a line.

        @param int length: length of the line in pixel

        @return int: error code (0:OK, -1:error)
        """
        return self._scanning_device.set_up_line(length)

    # TODO: Magic needs to happen here
    def scan_line(self, line_path=None, pixel_clock=False):
        """ Scans a line and returns the counts on that line.

        @param float[][4] line_path: array of 4-part tuples defining the positions pixels
        @param bool pixel_clock: whether we need to output a pixel clock for this line

        @return float[]: the photon counts per second
        """
        if self.superres_scanmode:
            new_path = np.zeros([line_path.shape[0], line_path.shape[1]*3])
            new_path[:][0] = np.linspace(min(line_path[:][0]), max(line_path[:][0]),
                                         new_path.shape[1])
            new_path[:][1] = np.linspace(min(line_path[:][1]), max(line_path[:][1]),
                                         new_path.shape[1])
            new_path[:][2] = np.linspace(min(line_path[:][2]), max(line_path[:][2]),
                                         new_path.shape[1])
            line_path = new_path

        # apply tilt correction
        if self.tiltcorrection:
            line_path[:][2] += self._calc_dz(line_path[:][0], line_path[:][1])

        # apply superresolution mode
        if self.superres_scanmode:
            # Switch on pulse sequence
            self._pulsed_measurement.pulse_generator_on()
            time.sleep(0.1)
            # always sample 3 times the same position
            #line_path = np.repeat(line_path, 3, axis=1)
            tmp_return = self._scanning_device.scan_line(line_path, True)
            linescan_return = np.zeros([int(tmp_return.shape[0] / 3), 3])
            linescan_return[:, 0] = tmp_return[::3, 0]
            linescan_return[:, 1] = tmp_return[1::3, 0]
            linescan_return[:, 2] = tmp_return[2::3, 0]
            # Switch off pulse sequence (to reset the sequence)
            self._pulsed_measurement.pulse_generator_off()
            time.sleep(0.1)
        else:
            linescan_return = self._scanning_device.scan_line(line_path, pixel_clock)

        return linescan_return

    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        # Switch off pulse sequence
        self._pulsed_measurement.pulse_generator_off()
        return self._scanning_device.close_scanner()

    def close_scanner_clock(self, power=0):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        return self._scanning_device.close_scanner_clock()

    def _calc_dz(self, x, y):
        """Calculates the change in z for given tilt correction."""
        if not self.tiltcorrection:
            return 0.
        else:
            dz = -(
                (x - self.tilt_reference_x) * self.tilt_variable_ax
                + (y - self.tilt_reference_y) * self.tilt_variable_ay
            )
            return dz
