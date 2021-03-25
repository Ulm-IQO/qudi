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
from qudi.core.enums import TriggerEdge, SamplingOutputMode
from qudi.util.mutex import Mutex


class MicrowaveDummy(MicrowaveInterface):
    """A qudi dummy hardware module to emulate a microwave source.

    Example config for copy-paste:

    mw_source_dummy:
        module.Class: 'microwave.mw_source_dummy.MicrowaveDummy'
    """

    _SAMPLE_FREQUENCY = 50  # Frequency of scan output samples in Hz

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._thread_lock = Mutex()
        self._constraints = None

        self._cw_power = 0.0
        self._cw_frequency = 2.87e9
        self._scan_power = 0.0
        self._scan_frequencies = None
        self._scan_mode = SamplingOutputMode.JUMP_LIST
        self._trigger_edge = TriggerEdge.RISING
        self._is_scanning = False

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._constraints = MicrowaveConstraints(
            power_limits=(-60.0, 30),
            frequency_limits=(100e3, 20e9),
            scan_size_limits=(2, 1001),
            scan_modes=(SamplingOutputMode.JUMP_LIST, SamplingOutputMode.EQUIDISTANT_SWEEP)
        )

        self._cw_power = self._constraints.min_power + (
                    self._constraints.max_power - self._constraints.min_power) / 2
        self._cw_frequency = 2.87e9
        self._scan_power = self._cw_power
        self._scan_frequencies = None
        self._scan_mode = SamplingOutputMode.JUMP_LIST
        self._trigger_edge = TriggerEdge.RISING
        self._is_scanning = False

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
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
        """The CW microwave power in dBm.

        @return float: The currently set CW microwave power in dBm.
        """
        with self._thread_lock:
            return self._cw_power

    @cw_power.setter
    def cw_power(self, value):
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to set CW power. Microwave output is active.')
            is_in_range, new_val = self._constraints.power_in_range(value)
            if not is_in_range:
                self.log.warning(f'CW power to set out of bounds. Clipping value to {new_val} dBm')
            self.log.debug(f'Setting CW power to {new_val} dBm')
            self._cw_power = new_val

    @property
    def cw_frequency(self):
        """The CW microwave frequency in Hz.

        @return float: The currently set CW microwave frequency in Hz.
        """
        with self._thread_lock:
            return self._cw_frequency

    @cw_frequency.setter
    def cw_frequency(self, value):
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to set CW frequency. Microwave output is active.')
            is_in_range, new_val = self._constraints.frequency_in_range(value)
            if not is_in_range:
                self.log.warning(
                    f'CW frequency to set out of bounds. Clipping value to {new_val:.9e} Hz'
                )
            self.log.debug(f'Setting CW frequency to {new_val:.9e} Hz')
            self._cw_frequency = new_val

    @property
    def scan_power(self):
        """The microwave power in dBm used for scanning.

        @return float: The currently set scanning microwave power in dBm
        """
        with self._thread_lock:
            return self._scan_power

    @scan_power.setter
    def scan_power(self, value):
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to set scan power. Microwave output is active.')
            is_in_range, new_val = self._constraints.power_in_range(value)
            if not is_in_range:
                self.log.warning(
                    f'Scan power to set out of bounds. Clipping value to {new_val} dBm'
                )
            self.log.debug(f'Setting scan power to {new_val} dBm')
            self._scan_power = new_val

    @property
    def scan_frequencies(self):
        """The microwave frequencies used for scanning.

        In case of scan_mode == SamplingOutputMode.JUMP_LIST, this will be a 1D numpy array.
        In case of scan_mode == SamplingOutputMode.EQUIDISTANT_SWEEP, this will be a tuple
        containing 3 values (freq_begin, freq_end, number_of_samples).
        If no frequency scan has been specified, return None.

        @return float[]: The currently set scanning frequencies. None if not set.
        """
        with self._thread_lock:
            return self._scan_frequencies

    @scan_frequencies.setter
    def scan_frequencies(self, value):
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to set scan frequencies. Microwave output is active.')

            if self._scan_mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
                assert len(value) == 3, 'Setting scan_frequencies in "EQUIDISTANT_SWEEP" mode ' \
                                        'requires 3 values (start, stop, number_of_points)'
                points = int(value[2])
                assert self._constraints.scan_size_in_range(points)[0], \
                    f'Number of samples for frequency scan ({points}) is out of bounds for ' \
                    f'allowed scan size limits {self._constraints.scan_size_limits}'
                new_start = self._constraints.frequency_in_range(value[0])[1]
                new_stop = self._constraints.frequency_in_range(value[1])[1]
                if new_start != value[0] or new_stop != value[1]:
                    self.log.warning(f'Frequency scan start/stop is out of bounds. Clipping '
                                     f'frequencies to range {self._constraints.frequency_limits}')
                self._scan_frequencies = (new_start, new_stop, points)
            elif self._scan_mode == SamplingOutputMode.JUMP_LIST:
                points = len(value)
                min_freq = min(value)
                max_freq = max(value)
                assert self._constraints.scan_size_in_range(points)[0], \
                    f'Number of samples for frequency scan ({points}) is out of bounds for ' \
                    f'allowed scan size limits {self._constraints.scan_size_limits}'
                clipped_min = self._constraints.frequency_in_range(min_freq)[1]
                clipped_max = self._constraints.frequency_in_range(max_freq)[1]
                if clipped_min != min_freq or clipped_max != max_freq:
                    self.log.warning(f'Some frequency scan samples are out of bounds. Clipping '
                                     f'frequencies to range {self._constraints.frequency_limits}')
                self._scan_frequencies = np.clip(value,
                                                 *self._constraints.frequency_limits,
                                                 dtype=np.float64)
            else:
                self._scan_frequencies = None
                raise RuntimeError(f'Invalid scan mode encountered: "{self._scan_mode}"')
            self.log.debug(f'Setting scan_frequencies to: {self._scan_frequencies}')

    @property
    def scan_mode(self):
        """Scan mode Enum. Must implement setter as well.

        @return SamplingOutputMode: The currently set scan mode Enum
        """
        with self._thread_lock:
            return self._scan_mode

    @scan_mode.setter
    def scan_mode(self, value):
        assert self._constraints.mode_supported(value), f'Unsupported scan_mode to set: "{value}"'
        with self._thread_lock:
            if self._is_scanning:
                raise RuntimeError('Unable to set scan_mode. Frequency scanning in progress.')
            self.log.debug(f'Setting scan_mode to "{value.name}"')
            self._scan_mode = value

    @property
    def trigger_edge(self):
        """Input trigger polarity Enum for scanning. Must implement setter as well.

        @return TriggerEdge: The currently set active input trigger edge
        """
        with self._thread_lock:
            return self._trigger_edge

    @trigger_edge.setter
    def trigger_edge(self, value):
        assert isinstance(value, TriggerEdge), \
            'trigger_edge must be Enum type qudi.core.enums.TriggerEdge'
        with self._thread_lock:
            if self._is_scanning:
                raise RuntimeError('Unable to set trigger_edge. Frequency scanning in progress.')
            self.log.debug(f'Setting trigger_edge to "{value.name}"')
            self._trigger_edge = value

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

    def start_scan(self):
        """Switches on the microwave scanning.

        Must return AFTER the output is actually active (and can receive triggers for example).
        """
        with self._thread_lock:
            if self.module_state() == 'idle':
                self.log.debug(f'Starting frequency scan in "{self._scan_mode.name}" mode')
                time.sleep(1)
                self._is_scanning = True
                self.module_state.lock()
            elif not self._is_scanning:
                raise RuntimeError(
                    'Unable to start microwave frequency scan. CW microwave output is active.'
                )
            else:
                self.log.debug('Frequency scan already in progress')

    def reset_scan(self):
        """Reset currently running scan and return to start frequency.
        Does not need to stop and restart the microwave output if the device allows soft scan reset.
        """
        with self._thread_lock:
            if self._is_scanning:
                self.log.debug('Frequency scan soft reset')
                time.sleep(0.5)
