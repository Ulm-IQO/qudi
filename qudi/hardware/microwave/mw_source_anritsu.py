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
from qudi.core.enums import TriggerEdge, SamplingOutputMode


class MicrowaveAnritsu(MicrowaveInterface):
    """ Hardware control file for Anritsu Devices.

    Tested for the model MG37022A with Option 4.

    Example config for copy-paste:

    mw_source_anritsu:
        module.Class: 'microwave.mw_source_anritsu.MicrowaveAnritsu'
        gpib_address: 'GPIB0::12::INSTR'
        gpib_timeout: 10 # in seconds
    """

    _visa_address = ConfigOption('visa_address', missing='error')
    _comm_timeout = ConfigOption('comm_timeout', 10, missing='warn')

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
            scan_modes=(SamplingOutputMode.JUMP_LIST, SamplingOutputMode.EQUIDISTANT_SWEEP)
        )

        self._cw_power = float(self._gpib_connection.query(':POW?'))
        self._scan_power = self._cw_power
        self._scan_frequencies = None
        self._scan_mode = SamplingOutputMode.JUMP_LIST

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
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
            mode = self._device.query(':FREQ:MODE?').strip('\n').upper()
            return (self.module_state() != 'idle') and mode != 'CW'

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

            if self._device.query(':FREQ:MODE?').strip('\n').upper() != 'CW':
                self._command_wait(':FREQ:MODE CW')
            self._command_wait(f':POW {value:f}')
            self._cw_power = float(self._device.query(':POW?'))

    @property
    def cw_frequency(self):
        """The CW microwave frequency in Hz. Must implement setter as well.

        @return float: The currently set CW microwave frequency in Hz.
        """
        with self._thread_lock:
            return float(self._device.query(':FREQ?'))

    @cw_frequency.setter
    def cw_frequency(self, value):
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to set cw_frequency. Microwave output is active.')
            assert self._constraints.frequency_in_range(value)[0], \
                f'cw_frequency to set ({value:.9e} Hz) out of bounds for allowed range ' \
                f'{self._constraints.frequency_limits}'

            if self._device.query(':FREQ:MODE?').strip('\n').upper() != 'CW':
                self._command_wait(':FREQ:MODE CW')
            self._command_wait(f':FREQ {value:f}')

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

            if self._scan_mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
                if self._device.query(':FREQ:MODE?').strip('\n').upper() != 'SWE':
                    self._command_wait(':FREQ:MODE SWEEP')

                self._device.write(':SWE:GEN STEP')
                self._device.write('*WAI')
                self._command_wait(f':POW {value:f}')
                self._command_wait(':TRIG:SOUR EXT')
                self._scan_power = float(self._device.query(':POW?'))

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

            if self._scan_mode == SamplingOutputMode.EQUIDISTANT_SWEEP:
                assert len(value) == 3, 'EQUIDISTANT_SWEEP scan mode requires a len 3 iterable ' \
                                        'of the form (start_freq, stop_freq, number_of_points)'
                assert self._constraints.frequency_in_range(value[0])[0] and \
                       self._constraints.frequency_in_range(value[1])[0], \
                    f'scan_frequencies to set out of bounds for allowed range ' \
                    f'{self._constraints.frequency_limits}'
                assert self._constraints.scan_size_in_range(value[2])[0], \
                    f'Number of frequency steps to set ({value[2]:d}) out of bounds for ' \
                    f'allowed range {self._constraints.scan_size_limits}'

                freq_step = (value[1] - value[0]) / (value[2] - 1)

                self._scan_frequencies = None

                if self._device.query(':FREQ:MODE?').strip('\n').upper() != 'SWE':
                    self._command_wait(':FREQ:MODE SWEEP')
                self._device.write(':SWE:GEN STEP')
                self._device.write('*WAI')
                self._device.write(f':FREQ:START {value[0] - freq_step:f}')
                self._device.write(f':FREQ:STOP {value[1]:f}')
                self._device.write(f':SWE:FREQ:STEP {freq_step:f}')
                self._device.write('*WAI')
                self._command_wait(f':POW {self._scan_power:f}')
                self._command_wait(':TRIG:SOUR EXT')

                self._scan_frequencies = tuple(value)
            elif self._scan_mode == SamplingOutputMode.JUMP_LIST:
                assert self._constraints.frequency_in_range(min(value))[0] and \
                       self._constraints.frequency_in_range(max(value))[0], \
                    f'scan_frequencies to set out of bounds for allowed range ' \
                    f'{self._constraints.frequency_limits}'
                assert self._constraints.scan_size_in_range(len(value))[0], \
                    f'Number of frequency steps to set ({len(value):d}) out of bounds for ' \
                    f'allowed range {self._constraints.scan_size_limits}'

                self._scan_frequencies = None

                if self._device.query(':FREQ:MODE?').strip('\n').upper() != 'LIST':
                    self._command_wait(':FREQ:MODE LIST')
                self._device.write(':LIST:TYPE FREQ')
                self._device.write(':LIST:IND 0')
                freq_str = ', '.join(f'{freq:f}' for freq in value)
                self._device.write(f':LIST:FREQ {freq_str}')
                self._device.write(':LIST:STAR 0')
                self._device.write(f':LIST:STOP {len(value) - 1:d}')
                self._device.write(':LIST:MODE MAN')
                self._device.write('*WAI')
                self._command_wait(':LIST:IND 0')
                self._command_wait(f':POW {self._scan_power:f}')
                self._command_wait(':TRIG:SOUR EXT')

                self._scan_frequencies = np.array(value, dtype=np.float64)
            else:
                raise RuntimeError(
                    f'Invalid scan mode encountered ({self._scan_mode}). Please set scan_mode '
                    f'property before configuring or starting a frequency scan.'
                )

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
            self._scan_mode = value
            self._scan_frequencies = None

    @property
    def trigger_edge(self):
        """Input trigger polarity Enum for scanning. Must implement setter as well.

        @return TriggerEdge: The currently set active input trigger edge
        """
        with self._thread_lock:
            edge = self._device.query(':TRIG:SEQ3:SLOPE?')
            return TriggerEdge.FALLING if 'NEG' in edge else TriggerEdge.RISING

    @trigger_edge.setter
    def trigger_edge(self, value):
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to set trigger_edge. Microwave output is active.')
            assert isinstance(value, TriggerEdge), \
                'trigger_edge must be Enum type qudi.core.enums.TriggerEdge'
            assert value == TriggerEdge.RISING or value == TriggerEdge.FALLING, \
                'Trigger edge must be FALLING or RISING'

            edge = 'POS' if value == TriggerEdge.RISING else 'NEG'
            self._command_wait(f':TRIG:SEQ3:SLOP {edge}')

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

