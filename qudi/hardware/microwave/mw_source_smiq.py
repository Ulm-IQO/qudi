# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware file to control SMIQ microwave device.

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


class MicrowaveSmiq(MicrowaveInterface):
    """ This is the Interface class to define the controls for the simple
        microwave hardware.

    Example config for copy-paste:

    mw_source_smiq:
        module.Class: 'microwave.mw_source_smiq.MicrowaveSmiq'
        visa_address: 'GPIB0::28::INSTR'
        comm_timeout: 10  # in seconds
        visa_baud_rate: null  # optional
        frequency_min: null  # optional, in Hz
        frequency_max: null  # optional, in Hz
        power_min: null  # optional, in dBm
        power_max: null  # optional, in dBm
    """

    _visa_address = ConfigOption('visa_address', missing='error')
    _comm_timeout = ConfigOption('comm_timeout', default=10, missing='warn')
    _visa_baud_rate = ConfigOption('visa_baud_rate', default=None)
    _config_freq_min = ConfigOption('frequency_min', default=None)
    _config_freq_max = ConfigOption('frequency_max', default=None)
    _config_power_min = ConfigOption('power_min', default=None)
    _config_power_max = ConfigOption('power_max', default=None)

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
        self._scan_mode = None

    def on_activate(self):
        """ Initialisation performed during activation of the module. """
        # Connect to hardware
        self._rm = visa.ResourceManager()
        if self._visa_baud_rate is None:
            self._device = self._rm.open_resource(self._visa_address,
                                                  timeout=self._comm_timeout)
        else:
            self._device = self._rm.open_resource(self._visa_address,
                                                  timeout=self._comm_timeout,
                                                  baud_rate=self._visa_baud_rate)

        self._model = self._device.query('*IDN?').split(',')[1]
        # Reset device
        self._command_wait('*CLS')
        self._command_wait('*RST')

        # Generate constraints
        if self._model == 'SMIQ02B':
            freq_limits = (300e3, 2.2e9)
            power_limits = (-144, 13)
        elif self._model in ('SMIQ03B', 'SMIQ03HD'):
            freq_limits = (300e3, 3.3e9)
            power_limits = (-144, 13)
        elif self._model == 'SMIQ04B':
            freq_limits = (300e3, 4.4e9)
            power_limits = (-144, 10)
        elif self._model == 'SMIQ06B':
            freq_limits = (300e3, 6.4e9)
            power_limits = (-144, 16)
        elif self._model == 'SMIQ06ATE':
            freq_limits = (300e3, 6.4e9)
            power_limits = (-144, 10)
        else:
            freq_limits = (300e3, 6.4e9)
            power_limits = (-144, 10)
            self.log.warning('Model string unknown, hardware limits may be wrong.')
        # Apply configured soft-boundaries
        if self._config_power_min is not None:
            assert self._config_power_min < power_limits[1]
            power_limits = (max(power_limits[0], self._config_power_min), power_limits[1])
        if self._config_power_max is not None:
            assert self._config_power_max > power_limits[0]
            power_limits = (power_limits[0], min(power_limits[1], self._config_power_max))
        if self._config_freq_min is not None:
            assert self._config_freq_min < freq_limits[1]
            freq_limits = (max(freq_limits[0], self._config_freq_min), freq_limits[1])
        if self._config_freq_max is not None:
            assert self._config_freq_max > freq_limits[0]
            freq_limits = (freq_limits[0], min(freq_limits[1], self._config_freq_max))
        self._constraints = MicrowaveConstraints(
            power_limits=power_limits,
            frequency_limits=freq_limits,
            scan_size_limits=(2, 4000),
            scan_modes=(SamplingOutputMode.JUMP_LIST, SamplingOutputMode.EQUIDISTANT_SWEEP)
        )

        self._scan_frequencies = None
        self._scan_power = self._constraints.min_power
        self._cw_power = self._constraints.min_power
        self._cw_frequency = 2870.0e6
        self._scan_mode = SamplingOutputMode.JUMP_LIST

    def on_deactivate(self):
        """ Cleanup performed during deactivation of the module. """
        self._device.close()
        self._rm.close()

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

    @cw_power.setter
    def cw_power(self, value):
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to set cw_power. Microwave output is active.')
            assert self._constraints.power_in_range(value)[0], \
                f'cw_power to set ({value} dBm) out of bounds for allowed range ' \
                f'{self._constraints.power_limits}'

            if not self._in_cw_mode():
                self._command_wait(':FREQ:MODE CW')

            self._command_wait(f':FREQ {self._cw_frequency:f}')
            self._command_wait(f':POW {value:f}')

            self._cw_power = float(self._device.query(':POW?'))
            self._cw_frequency = float(self._device.query(':FREQ?'))

    @property
    def cw_frequency(self):
        """The CW microwave frequency in Hz. Must implement setter as well.

        @return float: The currently set CW microwave frequency in Hz.
        """
        with self._thread_lock:
            return self._cw_frequency

    @cw_frequency.setter
    def cw_frequency(self, value):
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to set cw_frequency. Microwave output is active.')
            assert self._constraints.frequency_in_range(value)[0], \
                f'cw_frequency to set ({value:.9e} Hz) out of bounds for allowed range ' \
                f'{self._constraints.frequency_limits}'

            if not self._in_cw_mode():
                self._command_wait(':FREQ:MODE CW')

            self._command_wait(f':FREQ {value:f}')
            self._command_wait(f':POW {self._cw_power:f}')

            self._cw_power = float(self._device.query(':POW?'))
            self._cw_frequency = float(self._device.query(':FREQ?'))

    @property
    def scan_power(self):
        """The microwave power in dBm used for scanning. Must implement setter as well.

        @return float: The currently set scanning microwave power in dBm
        """
        with self._thread_lock:
            return self._scan_power

    @scan_power.setter
    def scan_power(self, value):
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to set scan_power. Microwave output is active.')
            assert self._constraints.power_in_range(value)[0], \
                f'scan_power to set ({value} dBm) out of bounds for allowed range ' \
                f'{self._constraints.power_limits}'

            self._scan_power = value
            if self._scan_frequencies is not None:
                if self._scan_mode == SamplingOutputMode.JUMP_LIST:
                    self._write_list()
                elif self._scan_mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
                    self._write_sweep()

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

    @scan_frequencies.setter
    def scan_frequencies(self, value):
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to set scan_frequencies. Microwave output is active.')

            if self._scan_mode == SamplingOutputMode.JUMP_LIST:
                assert self._constraints.frequency_in_range(min(value))[0] and \
                       self._constraints.frequency_in_range(max(value))[0], \
                    f'scan_frequencies to set out of bounds for allowed range ' \
                    f'{self._constraints.frequency_limits}'
                assert self._constraints.scan_size_in_range(len(value))[0], \
                    f'Number of frequency steps to set ({len(value):d}) out of bounds for ' \
                    f'allowed range {self._constraints.scan_size_limits}'

                self._scan_frequencies = np.array(value, dtype=np.float64)
                self._write_list()
            elif self._scan_mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
                assert len(value) == 3, 'EQUIDISTANT_SWEEP scan mode requires a len 3 iterable ' \
                                        'of the form (start_freq, stop_freq, number_of_points)'
                in_range = self._constraints.frequency_in_range(value[0])[0] and \
                           self._constraints.frequency_in_range(value[1])[0]
                assert in_range, f'scan_frequencies to set are out of bounds for allowed ' \
                                 f'range {self._constraints.frequency_limits}'
                assert self._constraints.scan_size_in_range(value[2])[0], \
                    f'Number of frequency steps to set ({value[2]:d}) out of bounds for ' \
                    f'allowed range {self._constraints.scan_size_limits}'

                self._scan_frequencies = tuple(value)
                self._write_sweep()

    @property
    def scan_mode(self):
        """Scan mode Enum. Must implement setter as well.

        @return SamplingOutputMode: The currently set scan mode Enum
        """
        with self._thread_lock:
            return self._scan_mode

    @scan_mode.setter
    def scan_mode(self, value):
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to set scan_mode. Microwave output is active.')
            assert isinstance(value, SamplingOutputMode), \
                'scan_mode must be Enum type qudi.core.enums.SamplingOutputMode'
            assert self._constraints.mode_supported(value), \
                f'Unsupported scan_mode "{value}" encountered'

            self._scan_frequencies = None
            self._scan_mode = value

    @property
    def trigger_edge(self):
        """Input trigger polarity Enum for scanning. Must implement setter as well.

        @return TriggerEdge: The currently set active input trigger edge
        """
        with self._thread_lock:
            edge = self._device.query(':TRIG1:SLOP?')
            return TriggerEdge.FALLING if 'NEG' in edge else TriggerEdge.RISING

    @trigger_edge.setter
    def trigger_edge(self, value):
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to set trigger_edge. Microwave output is active.')
            assert isinstance(value, TriggerEdge), \
                'trigger_edge must be Enum type qudi.core.enums.TriggerEdge'

            edge = 'NEG' if value == TriggerEdge.FALLING else 'POS'
            self._command_wait(f':TRIG1:SLOP {edge}')

    def off(self):
        """Switches off any microwave output (both scan and CW).
        Must return AFTER the device has actually stopped.
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                list_mode = self._in_list_mode()
                if list_mode:
                    self._command_wait(':FREQ:MODE CW')

                self._device.write('OUTP:STAT OFF')
                self._device.write('*WAI')
                while int(float(self._device.query('OUTP:STAT?'))) != 0:
                    time.sleep(0.2)

                if list_mode:
                    self._command_wait(':LIST:LEARN')
                    self._command_wait(':FREQ:MODE LIST')
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
                    'Unable to start CW microwave output. Microwave output is currently active.'
                )

            if not self._in_cw_mode():
                self._command_wait(':FREQ:MODE CW')
                self._command_wait(f':FREQ {self._cw_frequency:f}')
                self._command_wait(f':POW {self._cw_power:f}')

            self._device.write(':OUTP:STAT ON')
            self._device.write('*WAI')
            while int(float(self._device.query(':OUTP:STAT?'))) == 0:
                time.sleep(0.2)
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

            if self._scan_mode == SamplingOutputMode.JUMP_LIST:
                if not self._in_list_mode():
                    self._write_list()

                # This needs to be done due to stupid design of the list mode (sweep is better)
                self._command_wait(':FREQ:MODE CW')
                self._command_wait(f':FREQ {self._constraints.max_frequency:f}')
                self._command_wait(f':POW {self._constraints.min_power:f}')
                self._device.write(':OUTP:STAT ON')
                self._device.write('*WAI')
                while int(float(self._device.query(':OUTP:STAT?'))) == 0:
                    time.sleep(0.2)

                self._command_wait(':LIST:LEARN')
                self._command_wait(':FREQ:MODE LIST')
                while int(float(self._device.query(':OUTP:STAT?'))) == 0:
                    time.sleep(0.2)
            elif self._scan_mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
                if not self._in_sweep_mode():
                    self._write_sweep()

                self._device.write(':OUTP:STAT ON')
                while int(float(self._device.query(':OUTP:STAT?'))) == 0:
                    time.sleep(0.2)
            else:
                raise RuntimeError(
                    f'Invalid scan mode encountered ({self._scan_mode}). Please set scan_mode '
                    f'property before configuring or starting a frequency scan.'
                )
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

            if self._scan_mode == SamplingOutputMode.JUMP_LIST:
                self._command_wait(':ABOR:LIST')
            elif self._scan_mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
                self._command_wait(':ABOR:SWE')

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
        return self._device.query(':FREQ:MODE?').strip('\n').lower() == 'list'

    def _in_sweep_mode(self):
        return self._device.query(':FREQ:MODE?').strip('\n').lower() == 'swe'

    def _in_cw_mode(self):
        return self._device.query(':FREQ:MODE?').strip('\n').lower() == 'cw'

    def _write_list(self):
        # Cant change list parameters if in list mode
        if not self._in_cw_mode():
            self._command_wait(':FREQ:MODE CW')

        self._device.write(":LIST:SEL 'QUDI'")
        self._device.write('*WAI')

        # Set list frequencies
        freq_str = f'{self._scan_frequencies[0]:f}, '
        freq_str += ', '.join(f'{freq:f}' for freq in self._scan_frequencies)
        self._device.write(f':LIST:FREQ {freq_str}')
        self._device.write('*WAI')
        self._device.write(':LIST:MODE STEP')
        self._device.write('*WAI')

        # Set list power
        self._device.write(f':LIST:POW {self._scan_power:f}')
        self._device.write('*WAI')

        self._command_wait(':TRIG1:LIST:SOUR EXT')

        # Apply settings in hardware
        self._command_wait(':LIST:LEARN')
        # If there are timeout problems after this command, update the smiq firmware to > 5.90
        # as there was a problem with excessive wait times after issuing :LIST:LEARN over a
        # GPIB connection in firmware 5.88
        self._command_wait(':FREQ:MODE LIST')

    def _write_sweep(self):
        if not self._in_sweep_mode():
            self._command_wait(':FREQ:MODE SWEEP')

        start, stop, points = self._scan_frequencies
        step = (stop - start) / (points - 1)

        self._device.write(':SWE:MODE STEP')
        self._device.write(':SWE:SPAC LIN')
        self._device.write('*WAI')
        self._device.write(f':FREQ:START {start - step:f}')
        self._device.write(f':FREQ:STOP {stop:f}')
        self._device.write(f':SWE:STEP:LIN {step:f}')
        self._device.write('*WAI')

        self._device.write(f':POW {self._scan_power:f}')
        self._device.write('*WAI')

        self._command_wait(':TRIG1:SWE:SOUR EXT')

    #########################################################################################

    # def get_power(self):
    #     """
    #     Gets the microwave output power.
    #
    #     @return float: the power set at the device in dBm
    #     """
    #     mode, dummy = self.get_status()
    #     if mode == 'list':
    #         return float(self._device.query(':LIST:POW?'))
    #     else:
    #         # This case works for cw AND sweep mode
    #         return float(self._device.query(':POW?'))

    # def get_frequency(self):
    #     """
    #     Gets the frequency of the microwave output.
    #     Returns single float value if the device is in cw mode.
    #     Returns list like [start, stop, step] if the device is in sweep mode.
    #     Returns list of frequencies if the device is in list mode.
    #
    #     @return [float, list]: frequency(s) currently set for this device in Hz
    #     """
    #     mode, is_running = self.get_status()
    #     if 'cw' in mode:
    #         return_val = float(self._device.query(':FREQ?'))
    #     elif 'sweep' in mode:
    #         start = float(self._device.query(':FREQ:STAR?'))
    #         stop = float(self._device.query(':FREQ:STOP?'))
    #         step = float(self._device.query(':SWE:STEP?'))
    #         return_val = [start+step, stop, step]
    #     elif 'list' in mode:
    #         # Exclude first frequency entry (duplicate due to trigger issues)
    #         frequency_str = self._device.query(':LIST:FREQ?').split(',', 1)[1]
    #         return_val = np.array([float(freq) for freq in frequency_str.split(',')])
    #     return return_val

