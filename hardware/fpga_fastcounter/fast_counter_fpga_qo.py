# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware module for the FPGA based fast counter.

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
import struct
import os
import time

from interface.fast_counter_interface import FastCounterInterface
from core.module import Base, ConfigOption
from core.util.modules import get_main_dir
import okfrontpanel as ok
from core.util.mutex import Mutex


class FastCounterFPGAQO(Base, FastCounterInterface):
    """ unstable: Nikolas Tomek
        This is the hardware class for the Spartan-6 (Opal Kelly XEM6310) FPGA
        based fast counter.
        The command reference for the communicating via the OpalKelly Frontend
        can be looked up here:

            https://library.opalkelly.com/library/FrontPanelAPI/index.html

        The Frontpanel is basically a C++ interface, where a wrapper was used
        (SWIG) to access the dll library. Be aware that the wrapper is specified
        for a specific version of python (here python 3.4), and it is not
        guaranteed to be working with other versions.

    Example config for copy-paste:

    fpga_qo:
        module.Class: 'fpga_fastcounter.fast_counter_fpga_qo.FastCounterFPGAQO'
        fpgacounter_serial: '143400058N'
        fpga_type: 'XEM6310_LX150'
        #threshV_ch1: 0.5   # optional, threshold voltage for detection
        #threshV_ch2: 0.5   # optional, threshold voltage for detection
        #threshV_ch3: 0.5   # optional, threshold voltage for detection
        #threshV_ch4: 0.5   # optional, threshold voltage for detection
        #threshV_ch5: 0.5   # optional, threshold voltage for detection
        #threshV_ch6: 0.5   # optional, threshold voltage for detection
        #threshV_ch7: 0.5   # optional, threshold voltage for detection
        #threshV_ch8: 0.5   # optional, threshold voltage for detection

    """

    _modclass = 'FastCounterFPGAQO'
    _modtype = 'hardware'

    _serial = ConfigOption('fpgacounter_serial', missing='error')
    # 'No parameter "fpgacounter_serial" specified in the config! Set the '
    # 'serial number for the currently used fpga counter!\n'
    # 'Open the Opal Kelly Frontpanel to obtain the serial number of the '
    # 'connected FPGA.\nDo not forget to close the Frontpanel before starting '
    # 'the Qudi program.')

    _fpga_type = ConfigOption('fpga_type', 'XEM6310_LX150', missing='warn')
    # 'No parameter "fpga_type" specified in the config!\n'
    # 'Possible types are "XEM6310_LX150" or "XEM6310_LX45".\n'
    # 'Taking the type "{0}" as default.'.format(self._fpga_type))


    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.threadlock = Mutex()

        self.log.debug('The following configuration was found.')
        for key in config.keys():
            self.log.debug('{0}: {1}'.format(key, config[key]))

        self._internal_clock_hz = 950e6     # that is a fixed number, 950MHz
        self.statusvar = -1                 # fast counter state
        # The following is the encoding (status flags and errors) of the FPGA status register
        self._status_encoding = {0x00000001: 'initialization',
                                 0x00000002: 'pulling_data',
                                 0x00000004: 'idle_ready',
                                 0x00000008: 'running',
                                 0x80000000: 'TDC_in_reset'}
        self._error_encoding = {0x00000020: 'Init/output FSM in FPGA hardware encountered an error.'
                                            ' Please reset the device to recover from this state.',
                                0x00000040: 'Histogram FSM in FPGA hardware encountered an error. '
                                            'Please reset the device to recover from this state.',
                                0x00000080: 'One or more histogram bins have overflown (32 bit '
                                            'unsigned integer). Time tagger will not continue to '
                                            'accumulate more events. Please save current data and '
                                            'start a new measurement.',
                                0x00000200: 'Output buffer FIFO for pipe transfer via USB has '
                                            'overflown. This should not happen under any '
                                            'circumstance. Please contact hardware manufacturer.',
                                0x00000400: 'Output buffer FIFO for pipe transfer via USB has '
                                            'underrun. This should not happen under any '
                                            'circumstance. Please contact hardware manufacturer.',
                                0x00000800: 'Power-On self calibration of DDR2 interface not '
                                            'successful. Please contact hardware manufacturer.',
                                0x00001000: 'Read buffer of init/output memory interface port has '
                                            'overflown. This should not happen under any '
                                            'circumstance. Please contact hardware manufacturer.',
                                0x00002000: 'Write buffer of init/output memory interface port has '
                                            'underrun. This should not happen under any '
                                            'circumstance. Please contact hardware manufacturer.',
                                0x00004000: 'Init/output memory interface read port has encountered'
                                            ' a fatal error. Please contact hardware manufacturer.',
                                0x00008000: 'Init/output memory interface write port has '
                                            'encountered a fatal error. Please contact hardware '
                                            'manufacturer.',
                                0x00010000: 'Read buffer of histogram memory interface port has '
                                            'overflown. This should not happen under any '
                                            'circumstance. Please contact hardware manufacturer.',
                                0x00020000: 'Write buffer of histogram memory interface port has '
                                            'underrun. This should not happen under any '
                                            'circumstance. Please contact hardware manufacturer.',
                                0x00040000: 'Histogram memory interface read port has encountered a'
                                            ' fatal error. Please contact hardware manufacturer.',
                                0x00080000: 'Histogram memory interface write port has encountered '
                                            'a fatal error. Please contact hardware manufacturer.',
                                0x00100000: 'Idle memory interface port encountered an error. '
                                            'This should not happen under any circumstance. '
                                            'Please contact hardware manufacturer.',
                                0x00200000: 'Idle memory interface port encountered an error. '
                                            'This should not happen under any circumstance. '
                                            'Please contact hardware manufacturer.',
                                0x00400000: 'Idle memory interface port encountered an error. '
                                            'This should not happen under any circumstance. '
                                            'Please contact hardware manufacturer.',
                                0x00800000: 'Idle memory interface port encountered an error. '
                                            'This should not happen under any circumstance. '
                                            'Please contact hardware manufacturer.',
                                0x01000000: 'Bandwidth of Timetagger buffer memory exceeded. This '
                                            'can happen if the rate of detector events is too high '
                                            'and/or the data requests are too frequent. Timetrace '
                                            'is not reliable.',
                                0x10000000: 'Timetagger event buffer has encountered an overflow. '
                                            'This should not happen under any circumstance. '
                                            'Please contact hardware manufacturer.',
                                0x20000000: 'Timetagger event buffer has encountered an underrun. '
                                            'This should not happen under any circumstance. '
                                            'Please contact hardware manufacturer.',
                                0x40000000: 'Power-On self calibration of TDC not successful. '
                                            'Please contact hardware manufacturer.'}

    def on_activate(self):
        """ Connect and configure the access to the FPGA.
        """
        config = self.getConfiguration()

        self._switching_voltage = {1: 0.5, 2: 0.5, 3: 0.5, 4: 0.5, 5: 0.5, 6: 0.5, 7: 0.5, 8: 0.5}
        for key in config.keys():
            if 'threshV_ch' in key:
                self._switching_voltage[int(key[-1])] = config[key]

        # fast counter state
        self.statusvar = -1
        # fast counter parameters to be configured. Default values.
        self._binwidth = 1              # number of elementary bins to be combined into a single bin
        self._gate_length_bins = 8192   # number of bins in one gate (max 65536)
        self._number_of_gates = 1       # number of gates in the pulse sequence (max 512)

        self._old_data = None           # histogram to be added to the current data after
                                        # continuing a measurement
        self.count_data = None
        self.saved_count_data = None    # Count data stored to continue measurement

        # Create an instance of the Opal Kelly FrontPanel. The Frontpanel is a C dll which was
        # wrapped for use with python.
        self._fpga = ok.FrontPanel()
        # connect to the FPGA module
        self._connect()
        # configure DAC for threshold voltages
        self._reset_dac()
        self._activate_dac_ref()
        self._set_dac_voltages()
        return

    def on_deactivate(self):
        """ Deactivate the FPGA.
        """
        self.stop_measure()
        self.statusvar = -1
        del self._fpga
        return

    def _connect(self):
        """
        Connect host PC to FPGA module with the specified serial number.
        """
        # check if a FPGA is connected to this host PC. That method is used to determine also how
        # many devices are available.
        if not self._fpga.GetDeviceCount():
            self.log.error('No FPGA connected to host PC or FrontPanel.exe is running.')
            return -1

        # open a connection to the FPGA with the specified serial number
        self._fpga.OpenBySerial(self._serial)

        # upload the proper fast counter configuration bitfile to the FPGA
        bitfile_name = 'fastcounter_' + self._fpga_type + '.bit'
        # Load on the FPGA a configuration file (bit file).
        self._fpga.ConfigureFPGA(os.path.join(get_main_dir(), 'thirdparty', 'qo_fpga',
                                              bitfile_name))

        # Check if the upload was successful and the Opal Kelly FrontPanel is
        # enabled on the FPGA
        if not self._fpga.IsFrontPanelEnabled():
            self.log.error('Opal Kelly FrontPanel is not enabled in FPGA.\n'
                           'Upload of bitfile failed.')
            self.statusvar = -1
            return -1

        # Wait until all power-up initialization processes on the FPGA have finished
        timeout = 5
        start_time = time.time()
        while True:
            if time.time()-start_time >= timeout:
                self.log.error('Power-on initialization of FPGA-timetagger timed out. '
                               'Device non-functional.')
                self.statusvar = -1
                break
            status_messages = self._get_status_messages()
            if len(status_messages) == 2 and ('idle_ready' in status_messages) and (
                'TDC_in_reset' in status_messages):
                self.log.info('Power-on initialization of FPGA-timetagger complete.')
                self.statusvar = 0
                break
            time.sleep(0.2)
        return self.statusvar

    def _read_status_register(self):
        """
        Reads the 32bit status register from the FPGA Timetagger via USB.

        @return: 32bit status register
        """
        self._fpga.UpdateWireOuts()
        status_register = self._fpga.GetWireOutValue(0x20)
        return status_register

    def _get_status_messages(self):
        """

        @return:
        """
        status_register = self._read_status_register()
        status_messages = []
        for bitmask in self._status_encoding:
            if (bitmask & status_register) != 0:
                status_messages.append(self._status_encoding[bitmask])
        return status_messages

    def _get_error_messages(self):
        """

        @return:
        """
        status_register = self._read_status_register()
        error_messages = []
        for bitmask in self._error_encoding:
            if (bitmask & status_register) != 0:
                error_messages.append(self._error_encoding[bitmask])
        return error_messages

    def _set_dac_voltages(self):
        """
        """
        with self.threadlock:
            dac_sma_mapping = {1: 1, 2: 5, 3: 2, 4: 6, 5: 3, 6: 7, 7: 4, 8: 8}
            set_voltage_cmd = 0x03000000
            for dac_chnl in range(8):
                sma_chnl = dac_sma_mapping[dac_chnl+1]
                dac_value = int(np.rint(4096*self._switching_voltage[sma_chnl]/(2.5*2)))
                if dac_value > 4095:
                    dac_value = 4095
                elif dac_value < 0:
                    dac_value = 0
                tmp_cmd = set_voltage_cmd + (dac_chnl << 20) + (dac_value << 8)
                self._fpga.SetWireInValue(0x01, tmp_cmd)
                self._fpga.UpdateWireIns()
                self._fpga.ActivateTriggerIn(0x41, 0)
        return

    def _activate_dac_ref(self):
        """
        """
        with self.threadlock:
            self._fpga.SetWireInValue(0x01, 0x08000001)
            self._fpga.UpdateWireIns()
            self._fpga.ActivateTriggerIn(0x41, 0)
        return

    def _reset_dac(self):
        """
        """
        with self.threadlock:
            self._fpga.ActivateTriggerIn(0x41, 31)
        return

    def get_constraints(self):
        """ Retrieve the hardware constrains from the Fast counting device.


        @return dict: dict with keys being the constraint names as string and
                      items are the definition for the constaints.

         The keys of the returned dictionary are the str name for the constraints
        (which are set in this method).

                    NO OTHER KEYS SHOULD BE INVENTED!

        If you are not sure about the meaning, look in other hardware files to
        get an impression. If still additional constraints are needed, then they
        have to be added to all files containing this interface.

        The items of the keys are again dictionaries which have the generic
        dictionary form:
            {'min': <value>,
             'max': <value>,
             'step': <value>,
             'unit': '<value>'}

        Only the key 'hardware_binwidth_list' differs, since they
        contain the list of possible binwidths.

        If the constraints cannot be set in the fast counting hardware then
        write just zero to each key of the generic dicts.
        Note that there is a difference between float input (0.0) and
        integer input (0), because some logic modules might rely on that
        distinction.

        ALL THE PRESENT KEYS OF THE CONSTRAINTS DICT MUST BE ASSIGNED!
        """
        constraints = dict()
        # the unit of those entries are seconds per bin. In order to get the
        # current binwidth in seonds use the get_binwidth method.
        constraints['hardware_binwidth_list'] = [1/950e6]

        #TODO:  think maybe about a software_binwidth_list, which will postprocess the obtained
        #       counts. These bins must be integer multiples of the current hardware_binwidth
        return constraints

    def configure(self, bin_width_s, record_length_s, number_of_gates=0):
        """ Configuration of the fast counter.

        @param float bin_width_s: Length of a single time bin in the time trace
                                  histogram in seconds.
        @param float record_length_s: Total length of the timetrace/each single
                                      gate in seconds.
        @param int number_of_gates: optional, number of gates in the pulse
                                    sequence. Ignore for not gated counter.

        @return tuple(binwidth_s, gate_length_s, number_of_gates):
                    binwidth_s: float the actual set binwidth in seconds
                    gate_length_s: the actual set gate length in seconds
                    number_of_gates: the number of gated, which are accepted
        """
        # Do nothing if fast counter is running
        if self.statusvar >= 2:
            binwidth_s = self._binwidth / self._internal_clock_hz
            gate_length_s = self._gate_length_bins * binwidth_s
            return binwidth_s, gate_length_s, self._number_of_gates

        # set class variables
        self._binwidth = int(np.rint(bin_width_s * self._internal_clock_hz))

        # calculate the actual binwidth depending on the internal clock:
        binwidth_s = self._binwidth / self._internal_clock_hz

        self._gate_length_bins = int(np.rint(record_length_s / bin_width_s))
        gate_length_s = self._gate_length_bins * binwidth_s

        self._number_of_gates = number_of_gates

        self.statusvar = 1
        return binwidth_s, gate_length_s, number_of_gates

    def start_measure(self):
        """ Start the fast counter. """
        self.saved_count_data = None
        # initialize the data array
        self.count_data = np.zeros([self._number_of_gates, self._gate_length_bins], dtype='int64')
        # Start the counter.
        self._fpga.ActivateTriggerIn(0x40, 0)
        timeout = 5
        start_time = time.time()
        while True:
            status_messages = self._get_status_messages()
            if len(status_messages) <= 2 and ('running' in status_messages):
                self.log.info('FPGA-timetagger measurement started.')
                self.statusvar = 2
                break
            if time.time() - start_time >= timeout:
                self.log.error('Starting of FPGA-timetagger timed out.')
                break
            time.sleep(0.1)
        return self.statusvar

    def get_data_trace(self):
        """ Polls the current timetrace data from the fast counter.

        @return numpy.array: 2 dimensional numpy ndarray. This counter is gated.
                             The return array has the following shape:
                             returnarray[gate_index, timebin_index]

        The binning, specified by calling configure() in forehand, must be taken
        care of in this hardware class. A possible overflow of the histogram
        bins must be caught here and taken care of.
        """
        with self.threadlock:
            # check for error status in FPGA timetagger
            error_messages = self._get_error_messages()
            if len(error_messages) != 0:
                for err_message in error_messages:
                    self.log.error(err_message)
                self.stop_measure()
                return self.count_data

            # check for running status
            status_messages = self._get_status_messages()
            if len(status_messages) != 1 or ('running' not in status_messages):
                self.log.error('The FPGA is currently not running! Start the FPGA to get the data '
                               'trace of the device. An empty numpy array[{0},{1}] filled with '
                               'zeros will be returned.'.format(self._number_of_gates,
                                                                self._gate_length_bins))
                return self.count_data

            # initialize the read buffer for the USB transfer.
            # one timebin of the data to read is 32 bit wide and the data is transferred in bytes.
            buffersize = 128 * 1024 * 1024  # 128 MB
            data_buffer = bytearray(buffersize)

            # trigger the data read in the FPGA
            self._fpga.ActivateTriggerIn(0x40, 2)
            # Read data from FPGA
            read_err_code = self._fpga.ReadFromBlockPipeOut(0xA0, 1024, data_buffer)
            if read_err_code != buffersize:
                self.log.error('Data transfer from FPGA via USB failed with error code {0}. '
                               'Returning old count data.'.format(read_err_code))
                return self.count_data

            # Encode bytes into 32bit unsigned integers
            buffer_encode = np.frombuffer(data_buffer, dtype='uint32')

            # Extract only the requested number of gates and gate length
            buffer_encode = buffer_encode.reshape(512, 65536)[0:self._number_of_gates,
                                                              0:self._gate_length_bins]

            # convert into int64 values
            self.count_data = buffer_encode.astype('int64', casting='safe')

            # Add saved count data (in case of continued measurement)
            if self.saved_count_data is not None:
                if self.saved_count_data.shape == self.count_data.shape:
                    self.count_data = self.count_data + self.saved_count_data
                else:
                    self.log.error('Count data before pausing measurement had different shape than '
                                   'after measurement. Can not properly continue measurement.')

            # bin the data according to the specified bin width
            #if self._binwidth != 1:
            #    buffer_encode = buffer_encode[:(buffer_encode.size // self._binwidth) * self._binwidth].reshape(-1, self._binwidth).sum(axis=1)
            return self.count_data

    def stop_measure(self):
        """ Stop the fast counter. """
        self.saved_count_data = None
        # stop FPGA timetagger
        self._fpga.ActivateTriggerIn(0x40, 1)
        # Check status and wait until stopped
        timeout = 5
        start_time = time.time()
        while True:
            status_messages = self._get_status_messages()
            if len(status_messages) == 2 and ('idle_ready' in status_messages) and (
                        'TDC_in_reset' in status_messages):
                self.log.info('FPGA-timetagger measurement stopped.')
                self.statusvar = 1
                break
            if time.time() - start_time >= timeout:
                self.log.error('Stopping of FPGA-timetagger timed out.')
                break
            time.sleep(0.1)
        return self.statusvar

    def pause_measure(self):
        """ Pauses the current measurement.

        Fast counter must be initially in the run state to make it pause.
        """
        # stop FPGA timetagger
        self.saved_count_data = self.get_data_trace()
        self._fpga.ActivateTriggerIn(0x40, 1)
        # Check status and wait until stopped
        timeout = 5
        start_time = time.time()
        while True:
            status_messages = self._get_status_messages()
            if len(status_messages) == 2 and ('idle_ready' in status_messages) and (
                        'TDC_in_reset' in status_messages):
                self.log.info('FPGA-timetagger measurement paused.')
                self.statusvar = 3
                break
            if time.time() - start_time >= timeout:
                self.log.error('Pausing of FPGA-timetagger timed out.')
                break
            time.sleep(0.1)
        return self.statusvar

    def continue_measure(self):
        """ Continues the current measurement.

        If fast counter is in pause state, then fast counter will be continued.
        """
        self.count_data = np.zeros([self._number_of_gates, self._gate_length_bins], dtype='int64')
        # Check if fastcounter was in pause state
        if self.statusvar != 3:
            self.log.error('Can not continue fast counter since it was not in a paused state.')
            return self.statusvar

        # Start the counter.
        self._fpga.ActivateTriggerIn(0x40, 0)
        timeout = 5
        start_time = time.time()
        while True:
            status_messages = self._get_status_messages()
            if len(status_messages) == 1 and ('running' in status_messages):
                self.log.info('FPGA-timetagger measurement started.')
                self.statusvar = 2
                break
            if time.time() - start_time >= timeout:
                self.log.error('Starting of FPGA-timetagger timed out.')
                break
            time.sleep(0.1)
        return self.statusvar

    def is_gated(self):
        """ Check the gated counting possibility.

        @return bool: Boolean value indicates if the fast counter is a gated
                      counter (TRUE) or not (FALSE).
        """
        return True

    def get_binwidth(self):
        """ Returns the width of a single timebin in the timetrace in seconds.

        @return float: current length of a single bin in seconds (seconds/bin)
        """
        width_in_seconds = self._binwidth / self._internal_clock_hz
        return width_in_seconds

    def get_status(self):
        """ Receives the current status of the Fast Counter and outputs it as
            return value.

        0 = unconfigured
        1 = idle
        2 = running
        3 = paused
        -1 = error state
        """
        return self.statusvar

    def get_current_sweeps(self):
        """ Get the current number of sweeps

        @return int: current number of sweeps

        Let's not return 0 because some logic might be dividing by this """
        return 1