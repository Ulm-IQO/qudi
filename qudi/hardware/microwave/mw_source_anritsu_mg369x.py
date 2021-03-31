# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware file to control Anritsu 70GHz Device.

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
from qudi.core.enums import TriggerEdge, SamplingOutputMode


class MicrowaveAnritsuMG369x(MicrowaveInterface):
    """ Hardware control file for Anritsu 70GHz Devices.
        Tested for the model MG3696B.

    Example config for copy-paste:

    mw_source_anritsu:
        module.Class: 'microwave.mw_source_anritsu_mg369x.MicrowaveAnritsuMG369x'
        visa_address: 'GPIB0::12::INSTR'
        comm_timeout: 10  # in seconds

    """

    _visa_address = ConfigOption('visa_address', missing='error')
    _comm_timeout = ConfigOption('comm_timeout', default=10, missing='warn')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._thread_lock = Mutex()
        self._rm = None
        self._device = None
        self._model = ''
        self._constraints = None
        self._cw_power = -20
        self._cw_frequency = 2.0e9
        self._scan_power = -20
        self._scan_frequencies = None
        self._scan_sample_rate = 0.
        self._in_cw_mode = True

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # trying to load the visa connection to the module
        self._rm = visa.ResourceManager()
        self._device = self._rm.open_resource(self._visa_address,
                                              timeout=int(self._comm_timeout * 1000))
        # native command mode, some things are missing in SCPI mode
        self._device.write('SYST:LANG "NATIVE"')
        # query model ID
        self._model = self._device.query('*IDN?').split(',')[1]
        # Sets the RF output to 'off' at reset
        self._device.write('RO1')
        # Reset device
        self._device.write('RST')

        # Generate constraints
        if self._model == 'MG3696B':
            freq_limits = (10e6, 70e9)
            power_limits = (-20, 10)
        elif self._model == 'MG3691C':
            freq_limits = (10e6, 10e9)  # only with Option 4 or 5
            power_limits = (-120, 20)  # could be up to 26 dBm for Option 15
        else:
            freq_limits = (10e6, 70e9)
            power_limits = (-20, 10)
            self.log.warning('Model string unknown, hardware limits may be wrong.')
        self._constraints = MicrowaveConstraints(
            power_limits=power_limits,
            frequency_limits=freq_limits,
            scan_size_limits=(2, 1999),
            sample_rate_limits=(0.1, 100),  # FIXME: Look up the proper specs for sample rate
            scan_modes=(SamplingOutputMode.JUMP_LIST,)
        )

        # NOTE: Due to a crappy command set one can not query a lot of stuff.
        self._in_cw_mode = True
        self._scan_frequencies = None
        self._scan_power = self._constraints.min_power
        self._scan_sample_rate = self._constraints.max_sample_rate
        self._cw_frequency = 2.0e9
        self._cw_power = self._constraints.min_power

    def on_deactivate(self):
        """ Cleanup performed during deactivation of the module.
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
            return (self.module_state() != 'idle') and not self._in_cw_mode

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
            return self._cw_frequency

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
            return SamplingOutputMode.JUMP_LIST

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

            self._device.write('ACW')
            self._in_cw_mode = True
            self._device.write(f'F0 {frequency:f} HZ')
            self._device.write(f'L0 {power:f} DM')
            self._cw_power = float(self._device.query('OL0'))
            self._cw_frequency = 1e6 * float(self._device.query('OF0'))

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
            self._scan_frequencies = np.asarray(frequencies, dtype=np.float64)
            self._write_list()

    def off(self):
        """Switches off any microwave output (both scan and CW).
        Must return AFTER the device has actually stopped.
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                self._device.write('RF0')
                # FIXME: Due to a missing output state query command one can not WAIT until it has
                #  stopped
                time.sleep(1)
                self.module_state.unlock()

    def cw_on(self):
        """ Switches on cw microwave output.

        Must return AFTER the output is actually active.
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError(
                    'Unable to start CW microwave output. Microwave output is currently active.'
                )

            self._device.write('ACW')
            self._in_cw_mode = True
            self._device.write('RF1')
            # FIXME: Due to a missing output state query command one can not WAIT until it's running
            time.sleep(1)
            self.module_state.lock()

    def start_scan(self):
        """Switches on the microwave scanning.

        Must return AFTER the output is actually active (and can receive triggers for example).
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                if not self._in_cw_mode:
                    return
                raise RuntimeError('Unable to start frequency scan. CW microwave output is active.')
            assert self._scan_frequencies is not None, \
                'No scan_frequencies set. Unable to start scan.'

            # enter list mode
            self._device.write('LST')
            self._in_cw_mode = False
            # select list number 0
            self._device.write('ELN0')
            # select list index 0
            self._device.write('ELI0000')
            # Set list start index
            self._device.write('LIB0000')
            # Set list stop index
            self._device.write(f'LIE{len(self._scan_frequencies):04d}')
            # Set manual trigger mode
            self._device.write('MNT')
            # Learn list
            self._device.write('LEA')
            # activate output
            self._device.write('RF1')
            if self._model == 'MG3691C':
                time.sleep(10)  # for model MG3691C wait 10 seconds for the microwave to switch on
            else:
                time.sleep(2)
            self.module_state.lock()

    def reset_scan(self):
        """Reset currently running scan and return to start frequency.
        Does not need to stop and restart the microwave output if the device allows soft scan reset.
        """
        with self._thread_lock:
            if self.module_state() == 'idle':
                return
            if self._in_cw_mode:
                raise RuntimeError('Can not reset frequency scan. CW microwave output active.')

            self._device.write('ELI0000')

    def _write_list(self):
        self._device.write('LST')
        self._in_cw_mode = False
        self._device.write('ELN0')
        self._device.write('ELI0000')

        # FIXME: Do we need 2 times the first frequency?
        freq_str = f'{self._scan_frequencies[0]:f} HZ, '
        freq_str += ', '.join(f'{freq:f} HZ' for freq in self._scan_frequencies)
        self._device.write(f'LF {freq_str}')

        power_str = ', '.join([f'{self._scan_power:f} DM'] * (len(self._scan_frequencies) + 1))
        self._device.write(f'LP {power_str}')

        # Set list start index
        self._device.write('LIB0000')
        # Set list stop index
        self._device.write(f'LIE{len(self._scan_frequencies):04d}')
        # Set manual trigger mode
        self._device.write('MNT')
