# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware file to control Gigatronics Device.

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


class MicrowaveGigatronics(MicrowaveInterface):
    """ Hardware file for Gigatronics. Tested for the model 2400/2500.

    Example config for copy-paste:

    mw_source_gigatronics:
        module.Class: 'microwave.mw_source_gigatronics.MicrowaveGigatronics'
        visa_address: 'GPIB0::12::INSTR'
        comm_timeout: 10  # in seconds, optional
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

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # trying to load the visa connection to the module
        self._rm = visa.ResourceManager()
        self._device = self._rm.open_resource(self._visa_address,
                                              read_termination='\r\n',
                                              timeout=int(self._comm_timeout * 1000))

        # Reset device
        self._device.write('*RST')
        # FIXME: What does this mean. I'm keeping it for now...
        idn_list = list()
        while len(idn_list) < 3:
            idn_list = self._device.query('*IDN?').split(', ')
            time.sleep(0.1)
        self._model = idn_list[1]

        # Generate constraints
        if self.model.startswith('2508'):
            freq_limits = (100e3, 8e9)
        elif self.model.startswith('2520'):
            freq_limits = (100e3, 20e9)
        elif self.model.startswith('2526'):
            freq_limits = (100e3, 26.5e9)
        elif self.model.startswith('2540'):
            freq_limits = (100e3, 40e9)
        else:
            freq_limits = (100e3, 20e9)
            self.log.warning('Model string unknown, hardware limits may be wrong.')
        self._constraints = MicrowaveConstraints(
            power_limits=(-144, 10),
            frequency_limits=freq_limits,
            scan_size_limits=(2, 4000),
            sample_rate_limits=(0.1, 100),  # FIXME: Look up the proper specs for sample rate
            scan_modes=(SamplingOutputMode.JUMP_LIST,)
        )

        # Settings must be locally saved because the SCPI interface of that device is too bad to
        # query those values.
        self._scan_frequencies = None
        self._scan_power = self._constraints.min_power
        self._scan_sample_rate = self._constraints.max_sample_rate
        self._cw_power = self._constraints.min_power
        self._cw_frequency = 2870.0e6
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

            if not self._in_cw_mode():
                self._command_wait(':MODE CW')

            self._command_wait(f':FREQ {frequency:e}')
            self._command_wait(f':POW {power:f} DBM')
            self._cw_power = float(self._device.query(':POW?'))
            self._cw_frequency = float(self._device.query(':FREQ?'))

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
                self._device.write(':OUTP:STAT OFF')
                while int(float(self._device.query(':OUTP:STAT?'))) != 0:
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
                    'Unable to start CW microwave output. Microwave output is currently active.'
                )

            if not self._in_cw_mode():
                self._command_wait(':MODE CW')
                self._command_wait(f':FREQ {self._cw_frequency:e}')
                self._command_wait(f':POW {self._cw_power:f} DBM')

            self._device.write(':OUTP:STAT ON')
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

            if self._in_cw_mode():
                self._write_list()

            self._device.write(':OUTP:STAT ON')
            while int(float(self._device.query(':OUTP:STAT?'))) == 0:
                time.sleep(0.2)
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

            self._device.write(':MODE CW')
            self._device.write(':MODE LIST')
            # ToDo: Check if this actually works without restarting the output

    def _command_wait(self, command_str):
        """Writes the command in command_str via PyVisa and waits until the device has finished
        processing it.

        @param str command_str: The command to be written
        """
        self._device.write(command_str)
        self._device.write('*WAI')
        while int(float(self._device.query('*OPC?'))) != 1:
            time.sleep(0.2)

    def _in_cw_mode(self):
        return self._device.query(':MODE?').strip('\n').lower() == 'cw'

    def _write_list(self):
        if not self._in_cw_mode():
            self._command_wait(':MODE CW')

        self._command_wait(f':FREQ {self._scan_frequencies[0]:e}')
        self._command_wait(f':POW {self._scan_power:f} DBM')

        # self._device.write('*SRE 0')
        self._device.write(':LIST:SEQ:AUTO ON')

        freq_str = f'{self._scan_frequencies[0]:.1f},'
        freq_str += ','.join(f'{freq:.1f}' for freq in self._scan_frequencies)
        self._device.write(f'LIST:FREQ {freq_str}')

        pow_str = f'{self._scan_power:.3f}'
        pow_str = ','.join([pow_str] * (len(self._scan_frequencies) + 1))
        self._device.write(f'LIST:POW {pow_str}')

        self._device.write('LIST:DWEL 0.002000 S')
        self._device.write('LIST:RFOffTime 0.000000 MS')
        self._device.write('*OPC?')
        self._device.write('LIST:PREC 1')
        # wait for '1' from OPC
        self._device.read()
        self._device.write(':LIST:REP STEP')
        self._device.write(':TRIG:SOUR EXT')
        # self._device.write('*SRE 239')
        # self._device.write('*SRE 167')
