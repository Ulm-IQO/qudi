# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware file to control the microwave dummy.

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

from qudi.interface.microwave_interface import MicrowaveInterface, MicrowaveConstraints
from qudi.core.enums import SamplingOutputMode
from qudi.util.mutex import Mutex


class MicrowaveDummy(MicrowaveInterface):
    """A qudi dummy hardware module to emulate a microwave source.

    Example config for copy-paste:

    mw_source_dummy:
        module.Class: 'microwave.mw_source_dummy.MicrowaveDummy'
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._thread_lock = Mutex()
        self._constraints = None

        self._cw_power = 0.
        self._cw_frequency = 2.87e9
        self._scan_power = 0.
        self._scan_frequencies = None
        self._scan_sample_rate = -1.
        self._scan_mode = SamplingOutputMode.JUMP_LIST
        self._is_scanning = False

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._constraints = MicrowaveConstraints(
            power_limits=(-60.0, 30),
            frequency_limits=(100e3, 20e9),
            scan_size_limits=(2, 1001),
            sample_rate_limits=(0.1, 200),
            scan_modes=(SamplingOutputMode.JUMP_LIST, SamplingOutputMode.EQUIDISTANT_SWEEP)
        )

        self._cw_power = self._constraints.min_power + (
                    self._constraints.max_power - self._constraints.min_power) / 2
        self._cw_frequency = 2.87e9
        self._scan_power = self._cw_power
        self._scan_frequencies = None
        self._scan_mode = SamplingOutputMode.JUMP_LIST
        self._scan_sample_rate = 100
        self._is_scanning = False

    def on_deactivate(self):
        """ Cleanup performed during deactivation of the module.
        """
        pass

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
        scan or CW.
        Should return False if module_state() is 'idle'.

        @return bool: Flag indicating if a scan is running (True) or not (False)
        """
        with self._thread_lock:
            return self._is_scanning

    @property
    def cw_power(self):
        """Read-only property returning the currently configured CW microwave power in dBm.

        @return float: The currently set CW microwave power in dBm.
        """
        with self._thread_lock:
            return self._cw_power

    @property
    def cw_frequency(self):
        """Read-only property returning the currently set CW microwave frequency in Hz.

        @return float: The currently set CW microwave frequency in Hz.
        """
        with self._thread_lock:
            return self._cw_frequency

    @property
    def scan_power(self):
        """Read-only property returning the currently configured microwave power in dBm used for
        scanning.

        @return float: The currently set scanning microwave power in dBm
        """
        with self._thread_lock:
            return self._scan_power

    @property
    def scan_frequencies(self):
        """Read-only property returning the currently configured microwave frequencies used for
        scanning.

        In case of self.scan_mode == SamplingOutputMode.JUMP_LIST, this will be a 1D numpy array.
        In case of self.scan_mode == SamplingOutputMode.EQUIDISTANT_SWEEP, this will be a tuple
        containing 3 values (freq_begin, freq_end, number_of_samples).
        If no frequency scan has been configured, return None.

        @return float[]: The currently set scanning frequencies. None if not set.
        """
        with self._thread_lock:
            return self._scan_frequencies

    @property
    def scan_mode(self):
        """Read-only property returning the currently configured scan mode Enum.

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

    def off(self):
        """Switches off any microwave output (both scan and CW).
        Must return AFTER the device has actually stopped.
        """
        with self._thread_lock:
            if self.module_state() == 'idle':
                self.log.debug('Microwave output was not active')
                return
            self.log.debug('Stopping microwave output')
            time.sleep(1)
            self._is_scanning = False
            self.module_state.unlock()

    def set_cw(self, frequency, power):
        """Configure the CW microwave output. Does not start physical signal output, see also
        "cw_on".

        @param float frequency: frequency to set in Hz
        @param float power: power to set in dBm
        """
        with self._thread_lock:
            # Check if CW parameters can be set.
            if self.module_state() != 'idle':
                raise RuntimeError(
                    'Unable to set CW power and frequency. Microwave output is active.'
                )
            assert self._constraints.power_in_range(power)[0], f'CW power to set out of bounds.'
            assert self._constraints.frequency_in_range(frequency)[0], \
                f'CW frequency to set out of bounds.'

            # Set power and frequency
            self.log.debug(f'Setting CW power to {power} dBm and frequency to {frequency:.9e} Hz')
            self._cw_power = power
            self._cw_frequency = frequency

    def cw_on(self):
        """ Switches on cw microwave output.

        Must return AFTER the output is actually active.
        """
        with self._thread_lock:
            if self.module_state() == 'idle':
                self.log.debug(f'Starting CW microwave output with {self._cw_frequency:.6e} Hz '
                               f'and {self._cw_power:.6f} dBm')
                time.sleep(1)
                self._is_scanning = False
                self.module_state.lock()
            elif self._is_scanning:
                raise RuntimeError(
                    'Unable to start microwave CW output. Frequency scanning in progress.'
                )
            else:
                self.log.debug('CW microwave output already running')

    def configure_scan(self, power, frequencies, mode, sample_rate):
        """
        """
        with self._thread_lock:
            # Sanity checking
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to configure scan. Microwave output is active.')
            # Check mode
            assert self._constraints.mode_supported(mode), f'Unsupported scan mode to set: "{mode}"'
            # Check sample rate
            assert self._constraints.sample_rate_in_range(sample_rate)[0], \
                f'Scan sample rate to set out of bounds.'
            # Check power
            assert self._constraints.power_in_range(power), f'Scan power to set out of bounds.'
            # Check frequencies
            if mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
                assert len(frequencies) == 3, \
                    'Setting scan frequencies in "EQUIDISTANT_SWEEP" mode requires 3 values ' \
                    '(start, stop, number_of_points)'
                frequencies = tuple(frequencies)
                samples = int(frequencies[2])
                min_freq, max_freq = frequencies[:2]
            elif mode == SamplingOutputMode.JUMP_LIST:
                frequencies = np.asarray(frequencies, dtype=np.float64)
                samples = len(frequencies)
                min_freq, max_freq = frequencies.min(), frequencies.max()
            else:
                raise RuntimeError(f'Unhandled scan mode encountered: "{mode}"')
            assert self._constraints.scan_size_in_range(samples)[0], \
                f'Number of samples for frequency scan ({samples}) is out of bounds for ' \
                f'allowed scan size limits {self._constraints.scan_size_limits}'
            assert self._constraints.frequency_in_range(min_freq)[0] and \
                   self._constraints.frequency_in_range(max_freq)[0], \
                f'Frequency samples to scan out of bounds.'

            # Actually change settings
            time.sleep(1)
            self._scan_power = power
            self._scan_frequencies = frequencies
            self._scan_mode = mode
            self._scan_sample_rate = sample_rate
            self.log.debug(
                f'Scan configured in mode "{mode.name}" with {sample_rate:.9e} Hz sample rate, '
                f'{power} dBm power and frequencies:\n{frequencies}.'
            )

    def start_scan(self):
        """Switches on the microwave scanning.

        Must return AFTER the output is actually active (and can receive triggers for example).
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError(
                    'Unable to start microwave frequency scan. Microwave output is active.'
                )
            self.module_state.lock()
            self._is_scanning = True
            time.sleep(1)
            self.log.debug(f'Starting frequency scan in "{self._scan_mode.name}" mode')

    def reset_scan(self):
        """Reset currently running scan and return to start frequency.
        Does not need to stop and restart the microwave output if the device allows soft scan reset.
        """
        with self._thread_lock:
            if self._is_scanning:
                self.log.debug('Frequency scan soft reset')
                time.sleep(0.5)
