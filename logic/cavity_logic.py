"""
This module operates a cavity using analogue voltages

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
from qtpy import QtCore
from collections import OrderedDict
import numpy as np
import time
import matplotlib.pyplot as plt

from core.module import Connector, StatusVar
from logic.generic_logic import GenericLogic
from interface.slow_counter_interface import CountingMode
from core.util.mutex import Mutex


class CavityLogic(GenericLogic):  # Todo connect to generic logic
    """
    This is the Logic class for cavity operation.
    """
    _modclass = 'CavityLogic'
    _modtype = 'logic'

    savelogic = Connector(interface='SaveLogic')
    analoguereader = Connector(interface='AnalogReaderInterface')

    _count_length = StatusVar('count_length', 300)
    _smooth_window_length = StatusVar('smooth_window_length', 10)
    _counting_samples = StatusVar('counting_samples', 1)
    _measurement_frequency = StatusVar('measurement_frequency', 50)
    _saving = StatusVar('saving', False)

    # Signals
    sigReaderUpdated = QtCore.Signal()

    sigMeasurementDataNext = QtCore.Signal()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        # Todo: Add initialisation from _statusVariable

        # Connectors
        self._voltage_reader_device = self.get_connector('analoguereader')
        self._save_logic = self.get_connector('savelogic')

        # Variables
        self._transmission_voltage_channel = "APD"
        self._movement_voltage_channel = "Scanner"
        self._movement_input = True
        if self._movement_input:
            self.channels = [self._transmission_voltage_channel, self._movement_voltage_channel]
        else:
            self.channels = [self._transmission_voltage_channel]

        # initialize data arrays
        self.countdata = np.zeros([len(self.channels), self._count_length])
        self.countdata_smoothed = np.zeros([len(self.channels), self._count_length])
        self.rawdata = np.zeros([len(self.channels), self._counting_samples])
        self._data_to_save = []

        self.sigMeasurementDataNext.connect(self.measure_loop_body, QtCore.Qt.QueuedConnection)

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        pass

    def save_data(self):
        """ Save the current confocal xy data to file.

                Two files are created.  The first is the imagedata, which has a text-matrix of count values
                corresponding to the pixel matrix of the image.  Only count-values are saved here.

                The second file saves the full raw data with x, y, z, and counts at every pixel.

                A figure is also saved.

                @param: list colorscale_range (optional) The range [min, max] of the display colour scale
                            (for the figure)

                @param: list percentile_range (optional) The percentile range [min, max] of the color scale
                """
        filepath = self._save_logic.get_path_for_module('Cavity')
        timestamp = datetime.datetime.now()
        # Prepare the meta data parameters (common to both saved files):
        parameters = OrderedDict()

        # parameters['']


        # Save the image data and figure
        figs = {ch: self.draw_figure(data=self.stepping_raw_data_back)
                for n, ch in enumerate(self.get_counter_count_channels())}

        # Save the image data and figure
        for n, ch in enumerate(self.get_counter_count_channels()):
            # data for the text-array "image":
            image_data = OrderedDict()
            image_data['Confocal pure {}{} scan image data without axis.\n'
                       'The upper left entry represents the signal at the upper left pixel '
                       'position.\nA pixel-line in the image corresponds to a row '
                       'of entries where the Signal is in counts/s:'.format(
                self._first_scan_axis, self._second_scan_axis)] = self.stepping_raw_data_back

            filelabel = 'cavity_data{0}'.format(ch.replace('/', ''))
            self._save_logic.save_data(image_data,
                                       filepath=filepath,
                                       timestamp=timestamp,
                                       parameters=parameters,
                                       filelabel=filelabel,
                                       fmt='%.6e',
                                       delimiter='\t',
                                       plotfig=figs[ch])

        self.log.debug('Cavity Scan Data saved.')
        self.signal_data_saved.emit()
        # Todo Ask if it is possible to write only one save with options for which lines were scanned
        return

    def start_measurement(self):
        """ This is called externally, and is basically a wrapper that
            redirects to the chosen counting mode start function.

            @return error: 0 is OK, -1 is error
        """

        # Todo: Make lock or something similar

        # Set up clock
        clock_status = self._voltage_reader_device.set_up_analogue_voltage_reader_clock(
            clock_frequency=self._measurment_frequency, set_up=True)
        if clock_status < 0:
            self.unlock()
            return -1

        measurement_status = self._voltage_reader_device.set_up_continuous_analog_reader(self.channels[0])
        if measurement_status < 0:
            return -1
        if self._movement_input:
            measurement_status = self._voltage_reader_device.add_analogue_reader_channel_to_measurement(
                self.channels[0], [self.channels[1]])
            if measurement_status < 0:
                return -1

        # initialising the data arrays
        self.rawdata = np.zeros([len(self.get_channels()), self._counting_samples])
        self.countdata = np.zeros([len(self.get_channels()), self._count_length])
        self.countdata_smoothed = np.zeros([len(self.get_channels()), self._count_length])
        self._sampling_data = np.empty([len(self.get_channels()), self._counting_samples])

        # the sample index for gated counting
        self._already_counted_samples = 0

        # Start data reader loop
        self.sigMeasurementDataNext.emit()
        return

    def stop_measurement(self):
        pass

    def initialise_measurement(self):
        pass

    def measure_loop_body(self):
        """ This method gets the count data from the hardware for the continuous counting mode (default).

        It runs repeatedly in the logic module event loop by being connected
        to sigCountContinuousNext and emitting sigCountContinuousNext through a queued connection.
        """
        if self.getState() == 'locked':
            with self.threadlock:
                # check for aborts of the thread in break if necessary
                if self.stopRequested:
                    # close off the actual counter
                    cnt_err = self._voltage_reader_device.stop_analogue_voltage_reader(
                        self._transmission_voltage_channel)
                    if cnt_err < 0:
                        self.log.warning("Closing cavity measurement failed")
                    cnt_err = self._voltage_reader_device.close_analogue_voltage_reader_clock()
                    clk_err = self._voltage_reader_device.close_analogue_voltage_reader(
                        self._transmission_voltage_channel)
                    if cnt_err < 0 or clk_err < 0:
                        self.log.error('Could not even close the voltage hardware, giving up.')
                    # switch the state variable off again
                    self.stopRequested = False
                    return

                # read the current counter value
                self.rawdata = self._voltage_reader_device.get_analogue_voltage_reader(self.channels,
                                                                                       self._measurement_samples)
                if self.rawdata[0, 0] < 0:
                    self.log.error('The counting went wrong, killing the counter.')
                    self.stopRequested = True

            # call this again from event loop
            self.sigMeasurementDataNext.emit()
        return
