# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware file to control Agilent microwave device.
The hardware file was tested using the model N9310A.

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

Parts of this file were developed from a PI3diamond module which is
Copyright (C) 2009 Helmut Rathgen <helmut.rathgen@gmail.com>

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import visa
import time
import numpy as np

from qudi.core.configoption import ConfigOption
from qudi.interface.microwave_interface import MicrowaveInterface, MicrowaveConstraints
from qudi.core.enums import SamplingOutputMode, TriggerEdge
from qudi.util.mutex import Mutex


class MicrowaveAgilent(MicrowaveInterface):
    """ Hardware control file for Agilent Devices.

    The hardware file was tested using the model N9310A.

    ToDo: Check if all these extremely long wait times are actually needed.

    Example config for copy-paste:

    mw_source_agilent:
        module.Class: 'microwave.mw_source_agilent.MicrowaveAgilent'
        visa_address: USB0::10::INSTR  # PyVisa compatible resource name
        comm_timeout: 5  # in seconds, optional
        rising_edge_trigger: True  # optional
    """

    _visa_address = ConfigOption('visa_address', missing='error')
    _comm_timeout = ConfigOption('comm_timeout', default=5, missing='warn')
    _rising_edge_trigger = ConfigOption('rising_edge_trigger', default=True, missing='info')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._thread_lock = Mutex()
        self._rm = None
        self._device = None
        self._model = ''
        self._constraints = None
        self._is_scanning = False
        self._scan_power = 0.
        self._scan_mode = None
        self._scan_frequencies = None
        self._scan_sample_rate = 0.

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # trying to open a communication channel to the device using PyVisa
        self._rm = visa.ResourceManager()
        self._device = self._rm.open_resource(resource_name=self._visa_address,
                                              timeout=int(self._comm_timeout * 1000))
        self._model = self._device.query('*IDN?').split(',')[1]

        # Generate constraints
        if self._model == 'N9310A':
            freq_limits = (9e3, 3e9)
            power_limits = (-127, 20)
        else:
            freq_limits = (9e3, 3e9)
            power_limits = (-144, 10)
            self.log.warning('Model string unknown, hardware constraints might be wrong.')
        self._constraints = MicrowaveConstraints(
            power_limits=power_limits,
            frequency_limits=freq_limits,
            scan_size_limits=(2, 4000),
            sample_rate_limits=(0.1, 100),  # FIXME: Look up the proper specs for sample rate
            scan_modes=(SamplingOutputMode.JUMP_LIST, SamplingOutputMode.EQUIDISTANT_SWEEP)
        )

        self._is_scanning = False
        self._scan_power = float(self._device.query(':AMPL:CW?'))
        self._scan_frequencies = None
        self._scan_mode = SamplingOutputMode.JUMP_LIST
        self._scan_sample_rate = self._constraints.max_sample_rate

    def on_deactivate(self):
        """ Cleanup performed during deactivation of the module.
        """
        self._device.close()
        self._rm.close()
        self._device = None
        self._rm = None

    @property
    def constraints(self):
        """The microwave constraints object for this device.

        @return MicrowaveConstraints:
        """
        return self._constraints

    @property
    def is_scanning(self):
        """Read-Only boolean flag indicating if a scan is running at the moment. Can be used
        together with module_state() to determine if the currently running microwave output is a
        scan or CW. Should return False if module_state() is 'idle'.

        @return bool: Flag indicating if a scan is running (True) or not (False)
        """
        with self._thread_lock:
            return self._is_scanning()

    @property
    def cw_power(self):
        """The CW microwave power in dBm.

        @return float: The currently set CW microwave power in dBm.
        """
        with self._thread_lock:
            return float(self._device.query(':AMPL:CW?'))

    @property
    def cw_frequency(self):
        """The CW microwave frequency in Hz. Must implement setter as well.

        @return float: The currently set CW microwave frequency in Hz.
        """
        with self._thread_lock:
            return float(self._device.query(':FREQ:CW?'))

    @property
    def scan_power(self):
        """The microwave power in dBm used for scanning.

        @return float: The currently set scanning microwave power in dBm
        """
        with self._thread_lock:
            return self._scan_power

    @property
    def scan_frequencies(self):
        """The microwave frequencies used for scanning. Must implement setter as well.

        In case of scan_mode == SamplingOutputMode.JUMP_LIST, this will be a 1D numpy array.
        In case of scan_mode == SamplingOutputMode.EQUIDISTANT_SWEEP, this will be a tuple
        containing 3 values (freq_begin, freq_end, number_of_samples).
        If no frequency scan has been specified, return None.

        @return float[]: The currently set scanning frequencies. None if not set.
        """
        with self._thread_lock:
            return self._scan_frequencies

    @property
    def scan_mode(self):
        """Scan mode Enum. Must implement setter as well.

        @return SamplingOutputMode: The currently set scan mode Enum
        """
        with self._thread_lock:
            return self._scan_mode

    @property
    def scan_sample_rate(self):
        """Read-only property returning the currently configured scan sample rate in Hz.

        @return float: The currently set scan sample rate in Hz
        """
        with self._thread_lock:
            return self._scan_sample_rate

    def set_cw(self, frequency, power):
        """Configure the CW microwave output. Does not start physical signal output, see also
        "cw_on".

        @param float frequency: frequency to set in Hz
        @param float power: power to set in dBm
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to set CW parameters. Microwave output active.')
            self._assert_cw_parameters_args(frequency, power)
            self._command_wait(f':FREQ:CW {frequency:e} Hz')
            self._command_wait(f':AMPL:CW {power:f}')

    def configure_scan(self, power, frequencies, mode, sample_rate):
        """
        """
        with self._thread_lock:
            # Sanity checks
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to configure frequency scan. Microwave output active.')
            self._assert_scan_configuration_args(power, frequencies, mode, sample_rate)

            # configure scan according to scan mode
            self._scan_sample_rate = sample_rate
            self._scan_power = power
            self._scan_mode = mode
            if mode == SamplingOutputMode.JUMP_LIST:
                # Adjust number of scan list entries
                num_of_freq = len(frequencies)
                current_rows = int(self._device.query(':LIST:RF:POINts?'))
                while current_rows != num_of_freq:
                    if current_rows > num_of_freq:
                        for ii in range(current_rows - num_of_freq):
                            # always delete the second row (first might not work)
                            self._device.write(f':LIST:ROW:DELete 2')
                            time.sleep(0.05)
                    else:
                        for ii in range(num_of_freq - current_rows):
                            self._device.write(':LIST:ROW:INsert 2')
                            time.sleep(0.05)
                    current_rows = int(self._device.query(':LIST:RF:POINts?'))
                # Set list values
                for ii, freq in enumerate(frequencies, 1):
                    self._device.write(f':LIST:ROW:GOTO {ii:d}')
                    time.sleep(0.1)
                    self._device.write(f':LIST:RF {freq:e} Hz')
                    time.sleep(0.25)
                    self._device.write(f':LIST:Amplitude {power:e} dBm')
                    time.sleep(0.25)

                self._scan_frequencies = np.asarray(frequencies, dtype=np.float64)

            elif mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
                self._device.write(f':SWE:RF:STAR {frequencies[0]:e} Hz')
                self._device.write(f':SWE:RF:STOP {frequencies[1]:e} Hz')
                self._device.write(f':SWE:STEP:POIN {frequencies[2]:d}')
                # self._device.write(':SWE:STEP:DWEL 10 ms')
                self._command_wait(f':AMPL:CW {power:f}')

                self._scan_frequencies = tuple(frequencies)

            self._device.write(':SWE:REP CONT')
            self._device.write(':SWE:STRG EXT')
            self._device.write(':SWE:PTRG EXT')
            trig_slope = 'EXTP' if self._rising_edge_trigger else 'EXTN'
            self._device.write(f':SWE:PTRG:SLOP {trig_slope}')
            self._device.write(':SWE:DIR:UP')
            # short waiting time to prevent crashes
            time.sleep(0.2)

    def off(self):
        """Switches off any microwave output (both scan and CW).
        Must return AFTER the device has actually stopped.
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                # turn of scanning (both "list" and "sweep"）
                self._device.write(':SWEep:RF:STATe OFF')
                while int(float(self._device.query(':SWEep:RF:STATe?'))) != 0:
                    time.sleep(0.2)
                # check if running
                if not self._is_running():
                    return
                self._device.write(':RFO:STAT OFF')
                while int(float(self._device.query(':RFO:STAT?'))) != 0:
                    time.sleep(0.2)
                self._is_scanning = False
                self.module_state.unlock()

    def cw_on(self):
        """ Switches on cw microwave output.

        Must return AFTER the output is actually active.
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                if self._in_cw_mode():
                    return
                raise RuntimeError(
                    'Unable to start CW microwave output. Frequency scanning in progress.'
                )

            self._is_scanning = False
            self._device.write(':RFO:STAT ON')
            while not self._is_running():
                time.sleep(0.2)

    def start_scan(self):
        """Switches on the microwave scanning.

        Must return AFTER the output is actually active (and can receive triggers for example).
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                if self._is_scanning:
                    return
                raise RuntimeError('Unable to start frequency scan. CW microwave output is active.')
            assert self._scan_frequencies is not None, \
                'No scan_frequencies set. Unable to start scan.'

            sweep_type = 'LIST' if self._scan_mode == SamplingOutputMode.JUMP_LIST else 'STEP'
            self._device.write(f':SWEep:TYPE {sweep_type}')
            self._device.write(':SWE:RF:STAT ON')
            while self._in_cw_mode():
                time.sleep(0.2)
            self._device.write(':RFO:STAT ON')
            while not self._is_running():
                time.sleep(0.2)
            self._is_scanning = True

    def reset_scan(self):
        """Reset currently running scan and return to start frequency.
        Does not need to stop and restart the microwave output if the device allows soft scan reset.
        """
        with self._thread_lock:
            if not self._is_scanning:
                return
            if self._scan_mode == SamplingOutputMode.JUMP_LIST:
                self._usb_connection.write(':RFO:STAT OFF')
                self._usb_connection.write(':SWEep:RF:STATe OFF')
                self._usb_connection.write(':LIST:ROW:GOTO 1')
                self._usb_connection.write(':SWEep:RF:STATe ON')
                self._usb_connection.write(':RFO:STAT ON')
            else:
                # No soft reset for sweep
                # Turn off
                self._device.write(':SWEep:RF:STATe OFF')
                while int(float(self._device.query(':SWEep:RF:STATe?'))) != 0:
                    time.sleep(0.2)
                # check if running
                if not self._is_running():
                    return
                self._device.write(':RFO:STAT OFF')
                while int(float(self._device.query(':RFO:STAT?'))) != 0:
                    time.sleep(0.2)
                # Turn on
                self._device.write(f':SWEep:TYPE STEP')
                self._device.write(':SWE:RF:STAT ON')
                while self._in_cw_mode():
                    time.sleep(0.2)
                self._device.write(':RFO:STAT ON')
                while not self._is_running():
                    time.sleep(0.2)

    def _command_wait(self, command_str):
        """ Writes the command in command_str via PyVisa and waits until the device has finished
        processing it.

        @param str command_str: The command to be written
        """
        self._device.write(command_str)
        self._device.write('*WAI')
        while int(float(self._device.query('*OPC?'))) != 1:
            time.sleep(0.2)

    def _in_list_mode(self):
        if self._in_cw_mode:
            return False
        return self._device.ask(':SWEep:TYPE?') != 'STEP'

    def _in_cw_mode(self):
        return not bool(int(float(self._device.ask(':SWEep:RF:STATe?'))))

    def _is_running(self):
        return bool(int(float(self._device.ask(":RFOutput:STATe?"))))

    # def trigger(self):
    #     """ Trigger the next element in the list or sweep mode programmatically.
    #
    #     @return int: error code (0:OK, -1:error)
    #     """
    #     start_freq = self.get_frequency()
    #     self._device.write(':TRIGger:IMMediate')
    #     time.sleep(self._FREQ_SWITCH_SPEED)
    #     curr_freq = self.get_frequency()
    #     if start_freq == curr_freq:
    #         self.log.error('Internal trigger for Agilent MW source did not work!')
