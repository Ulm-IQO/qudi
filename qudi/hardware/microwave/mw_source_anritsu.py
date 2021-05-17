# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware file to control Anritsu Microwave Device.

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

from qudi.util.mutex import Mutex
from qudi.core.configoption import ConfigOption
from qudi.interface.microwave_interface import MicrowaveInterface, MicrowaveConstraints
from qudi.util.enums import SamplingOutputMode


class MicrowaveAnritsu(MicrowaveInterface):
    """ Hardware control file for Anritsu Devices.

    Tested for the model MG37022A with Option 4.

    Example config for copy-paste:

    mw_source_anritsu:
        module.Class: 'microwave.mw_source_anritsu.MicrowaveAnritsu'
        gpib_address: 'GPIB0::12::INSTR'
        gpib_timeout: 10  # in seconds, optional
        rising_edge_trigger: True  # optional
    """

    _visa_address = ConfigOption('visa_address', missing='error')
    _comm_timeout = ConfigOption('comm_timeout', default=10, missing='warn')
    _rising_edge_trigger = ConfigOption('rising_edge_trigger', default=True, missing='info')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._thread_lock = Mutex()
        self._rm = None
        self._device = None
        self._model = ''
        self._constraints = None
        self._cw_power = -105
        self._scan_power = -105
        self._scan_frequencies = None
        self._scan_mode = None
        self._scan_sample_rate = 0.

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # connect via PyVisa
        self._rm = visa.ResourceManager()
        self._device = self._rm.open_resource(self._visa_address,
                                              timeout=int(self._comm_timeout * 1000))
        self._model = self._device.query('*IDN?').split(',')[1]

        # Generate constraints
        self._constraints = MicrowaveConstraints(
            power_limits=(-105, 30),
            frequency_limits=(10e6, 20e9),
            scan_size_limits=(2, 10001),
            sample_rate_limits=(0.1, 100),  # FIXME: Look up the proper specs for sample rate
            scan_modes=(SamplingOutputMode.JUMP_LIST, SamplingOutputMode.EQUIDISTANT_SWEEP)
        )

        self._cw_power = float(self._gpib_connection.query(':POW?'))
        self._scan_power = self._cw_power
        self._scan_frequencies = None
        self._scan_mode = SamplingOutputMode.JUMP_LIST
        self._scan_sample_rate = self._constraints.max_sample_rate

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._device.close()
        self._rm.close()
        self._device = None
        self._rm = None

    @property
    def constraints(self):
        return self._constraints

    @property
    def is_scanning(self):
        """Read-Only boolean flag indicating if a scan is running at the moment. Can be used together with
        module_state() to determine if the currently running microwave output is a scan or CW.
        Should return False if module_state() is 'idle'.

        @return bool: Flag indicating if a scan is running (True) or not (False)
        """
        with self._thread_lock:
            return (self.module_state() != 'idle') and not self._in_cw_mode()

    @property
    def cw_power(self):
        """The CW microwave power in dBm. Must implement setter as well.

        @return float: The currently set CW microwave power in dBm.
        """
        with self._thread_lock:
            return self._cw_power

    @property
    def cw_frequency(self):
        """The CW microwave frequency in Hz. Must implement setter as well.

        @return float: The currently set CW microwave frequency in Hz.
        """
        with self._thread_lock:
            return float(self._device.query(':FREQ?'))

    @property
    def scan_power(self):
        """The microwave power in dBm used for scanning. Must implement setter as well.

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

            if not self._in_cw_mode():
                self._command_wait(':FREQ:MODE CW')
            self._command_wait(f':POW {power:f}')
            self._command_wait(f':FREQ {frequency:f}')
            self._cw_power = float(self._device.query(':POW?'))

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
            if mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
                self._scan_frequencies = tuple(frequencies)
                freq_step = (frequencies[1] - frequencies[0]) / (frequencies[2] - 1)

                if not self._in_sweep_mode():
                    self._command_wait(':FREQ:MODE SWEEP')

                self._device.write(':SWE:GEN STEP')
                self._device.write('*WAI')
                self._device.write(f':FREQ:START {frequencies[0] - freq_step:f}')
                self._device.write(f':FREQ:STOP {frequencies[1]:f}')
                self._device.write(f':SWE:FREQ:STEP {freq_step:f}')
                self._device.write('*WAI')
                self._command_wait(f':POW {power:f}')
                self._command_wait(':TRIG:SOUR EXT')
            else:
                self._scan_frequencies = np.asarray(frequencies, dtype=np.float64)

                if not self._in_list_mode():
                    self._command_wait(':FREQ:MODE LIST')

                self._device.write(':LIST:TYPE FREQ')
                self._device.write(':LIST:IND 0')
                freq_str = ', '.join(f'{freq:f}' for freq in frequencies)
                self._device.write(f':LIST:FREQ {freq_str}')
                self._device.write(':LIST:STAR 0')
                self._device.write(f':LIST:STOP {len(frequencies) - 1:d}')
                self._device.write(':LIST:MODE MAN')
                self._device.write('*WAI')
                self._command_wait(':LIST:IND 0')
                self._command_wait(f':POW {power:f}')
                self._command_wait(':TRIG:SOUR EXT')

            self._set_trigger_edge()

    def off(self):
        """Switches off any microwave output (both scan and CW).
        Must return AFTER the device has actually stopped.
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                self._device.write('OUTP:STAT OFF')
                while int(float(self._device.query('OUTP:STAT?'))) != 0:
                    time.sleep(0.2)
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

            if self._device.query(':FREQ:MODE?').strip('\n').upper() != 'CW':
                self._command_wait(':FREQ:MODE CW')
            self._device.write(':OUTP:STAT ON')
            while int(float(self._device.query('OUTP:STAT?'))) == 0:
                time.sleep(0.2)
            self.module_state.lock()

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

            if self._scan_mode == SamplingOutputMode.JUMP_LIST:
                if self._device.query(':FREQ:MODE?').strip('\n').upper() != 'LIST':
                    self._command_wait(':FREQ:MODE LIST')
            else:
                if self._device.query(':FREQ:MODE?').strip('\n').upper() != 'SWE':
                    self._command_wait(':FREQ:MODE SWEEP')
            self._device.write(':OUTP:STAT ON')
            while int(float(self._device.query('OUTP:STAT?'))) == 0:
                time.sleep(0.2)
            self.module_state.lock()

    def reset_scan(self):
        """Reset currently running scan and return to start frequency.
        Does not need to stop and restart the microwave output if the device allows soft scan reset.
        """
        with self._thread_lock:
            if self.module_state() == 'idle':
                return
            if self._device.query(':FREQ:MODE?').strip('\n').upper() == 'CW':
                raise RuntimeError('Can not reset frequency scan. CW microwave output active.')

            if self._scan_mode == SamplingOutputMode.JUMP_LIST:
                self._command_wait(':LIST:IND 0')
            else:
                self._command_wait(':ABORT')

    def _command_wait(self, command_str):
        """ Writes the command in command_str via PyVisa and waits until the device has finished
        processing it.

        @param command_str: The command to be written
        """
        self._device.write(command_str)
        self._device.write('*WAI')
        while int(float(self._device.query('*OPC?'))) != 1:
            time.sleep(0.2)

    def _in_cw_mode(self):
        return self._device.query(':FREQ:MODE?').strip('\n').upper() == 'CW'

    def _in_sweep_mode(self):
        return self._device.query(':FREQ:MODE?').strip('\n').upper() == 'SWE'

    def _in_list_mode(self):
        return self._device.query(':FREQ:MODE?').strip('\n').upper() == 'LIST'

    def _set_trigger_edge(self):
        edge = 'POS' if self._rising_edge_trigger else 'NEG'
        self._command_wait(f':TRIG:SEQ3:SLOP {edge}')

    # def trigger(self):
    #     """ Trigger the next element in the list or sweep mode programmatically.
    #
    #     @return int: error code (0:OK, -1:error)
    #
    #     Ensure that the Frequency was set AFTER the function returns, or give
    #     the function at least a save waiting time.
    #     """
    #
    #     # WARNING:
    #     # The manual trigger functionality was not tested for this device!
    #     # Might not work well! Please check that!
    #
    #     self._gpib_connection.write('*TRG')
    #     time.sleep(self._FREQ_SWITCH_SPEED)  # that is the switching speed
    #     return 0

