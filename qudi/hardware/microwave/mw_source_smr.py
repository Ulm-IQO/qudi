# -*- coding: utf-8 -*-

"""
This file contains the Qudi Hardware module for Rohde and Schwary SMR.

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

import visa
import time
import numpy as np

from qudi.util.mutex import Mutex
from qudi.core.configoption import ConfigOption
from qudi.interface.microwave_interface import MicrowaveInterface, MicrowaveConstraints
from qudi.core.enums import TriggerEdge, SamplingOutputMode


class MicrowaveSMR(MicrowaveInterface):
    """ The hardware control for the device Rohde and Schwarz of type SMR.

    The command structure has been tested for type SMR20.
    Not tested on the device types SMR27, SMR30, SMR40

    For additional information concerning the commands to communicate via the
    GPIB connection through visa, please have a look at:

    http://cdn.rohde-schwarz.com/pws/dl_downloads/dl_common_library/dl_manuals/gb_1/s/smr_1/smr_20-40.pdf

    Example config for copy-paste:

    mw_source_smr:
        module.Class: 'microwave.mw_source_smr.MicrowaveSMR'
        visa_address: 'GPIB0::28::INSTR'
        comm_timeout: 10  # in seconds
        rising_edge_trigger: True  # optional
    """

    _visa_address = ConfigOption('visa_address', missing='error')
    _comm_timeout = ConfigOption('comm_timeout', default=10, missing='warn')
    _rising_edge_trigger = ConfigOption('rising_edge_trigger', default=True, missing='info')

    # Dwell time for list mode to set how long the device should stay at one list entry.
    # Here dwell time can be between 1ms and 1s
    _LIST_DWELL = 10e-3
    # Dwell time for sweep mode to set how long the device should stay at one list entry.
    # Here dwell time can be between 10ms and 5s
    _SWEEP_DWELL = 10e-3

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
        """ Initialisation performed during activation of the module. """

        # trying to load the visa connection to the module
        self._rm = visa.ResourceManager()
        self._device = self._rm.open_resource(self._visa_address,
                                              write_termination='\r\n',
                                              read_termination=None,
                                              timeout=int(self._comm_timeout * 1000))

        # get the info from the device:
        self._model = self._device.query('*IDN?').strip().split(',')[1]
        # Reset device
        self._device.write(':SYSTem:PRESet')
        self._device.write('*RST')
        self._device.write(':OUTP OFF')

        # Generate constraints
        # Read parameter boundaries from device
        freq_max = float(self._device.query('FREQuency? MAX'))
        freq_min = float(self._device.query('FREQuency? MIN'))
        power_max = float(self._device.query('POWER? MAX'))
        power_min = float(self._device.query('POWER? MIN'))
        # although it is the step mode, this number should be the same for the list mode:
        # LIST_FREQ_STEP_MIN = float(self._ask(':SOURce:FREQuency:STEP? MIN'))
        # LIST_FREQ_STEP_MAX = float(self._ask(':SOURce:FREQuency:STEP? MAX'))
        # SWEEP_FREQ_STEP_MIN = float(self._ask(':SOURce:SWEep:FREQuency:STEP? MIN'))
        # SWEEP_FREQ_STEP_MAX = float(self._ask(':SOURce:SWEep:FREQuency:STEP? MAX'))
        # the return will be a list telling how many are free and occupied, i.e. [free, occupied]
        # and the sum of that is the total list entries.
        max_list_entries = sum(
            [int(s) for s in self._device.query('SOUR:LIST:FREE?').strip().split(',')]
        )
        # extract the options from the device:
        # options = [s for s in self._device.query('*OPT?').strip().split(',') if s != '0']
        self._constraints = MicrowaveConstraints(
            power_limits=(power_min, power_max),
            frequency_limits=(freq_min, freq_max),
            scan_size_limits=(2, max_list_entries),
            sample_rate_limits=(1, 100),
            scan_modes=(SamplingOutputMode.JUMP_LIST,)
        )

        self._scan_frequencies = None
        self._scan_power = power_min
        self._scan_sample_rate = self._constraints.max_sample_rate
        self._cw_power = power_min
        self._cw_frequency = 2870.0e6

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
                self._command_wait(':FREQ:MODE CW')
            self._command_wait(f':FREQ {frequency:e}')
            self._command_wait(f':POW {power:f}')
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

            self._set_trigger_edge()

    def off(self):
        """Switches off any microwave output (both scan and CW).
        Must return AFTER the device has actually stopped.
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                self._device.write(':OUTP OFF')
                self._device.write(':FREQ:MODE CW')
                while int(float(self._ask('OUTP:STAT?').strip())) != 0:
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
                self._command_wait(':FREQ:MODE CW')
                self._command_wait(f':FREQ {self._cw_frequency:e}')
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

            if not self._in_list_mode():
                self._write_list()

            self._device.write(':LIST:LEARN')
            self._device.write(':FREQ:MODE LIST')
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

            self._device.write(':ABOR:LIST')

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
        return self._device.query(':FREQ:MODE?').strip().lower() == 'list'

    def _in_cw_mode(self):
        return self._device.query(':FREQ:MODE?').strip().lower() in ('cw', 'fix')

    def _write_list(self):
        self._device.write(':SOUR:LIST:MODE STEP')
        # It seems that we have to set a DWEL for the device, but it is not so
        # clear why it is necessary. At least there was a hint in the manual for
        # that and the instrument displays an error, when this parameter is not
        # set in the list mode (even it should be set by default):
        self._device.write(f':SOUR:LIST:DWEL {self._LIST_DWELL}')

        # FIXME: Is this needed?
        self._device.write(':TRIG1:LIST:SOUR EXT')
        # self._device.write(':TRIG1:SLOP NEG')

        # delete all list entries and create/select a new list
        self._device.write(':SOUR:LIST:DEL:ALL')
        self._device.write(':SOUR:LIST:SEL "LIST1"')

        freq_str = ', '.join(f'{freq:f}Hz' for freq in self._scan_frequencies)
        power_str = ', '.join([f'{self._scan_power:f}dBm'] * len(self._scan_frequencies))

        self._device.write(f':SOUR:LIST:FREQ {freq_str}')
        self._device.write(f':SOUR:LIST:POW {power_str}')
        self._device.write(':OUTP:AMOD FIX')

        # Apply settings in hardware
        self._device.write(':LIST:LEARN')
        # If there are timeout problems after this command, update the smiq firmware to > 5.90 as
        # there was a problem with excessive wait times after issuing :LIST:LEARN over a GPIB
        # connection in firmware 5.88.
        self._device.write(':FREQ:MODE LIST')

        list_len = int(round(float(self._device.query(':SOUR:LIST:FREQ:POIN?'))))

        if list_len != len(self._scan_frequencies):
            self.log.error('The input frequency list does not correspond to the generated list '
                           'inside the SMR20.')

    def _set_trigger_edge(self):
        edge = 'POS' if self._rising_edge_trigger else 'NEG'
        self._device.write(':TRIG1:LIST:SOUR EXT')
        self._device.write(f':TRIG1:SLOP {edge}')

    # ================== Non interface commands: ==================

    def turn_AM_on(self, depth):
        """ Turn on the Amplitude Modulation mode.

        @param float depth: modulation depth in percent (from 0 to 100%).

        @return int: error code (0:OK, -1:error)

        Set the Amplitude modulation based on an external DC signal source and
        switch on the device after configuration.
        """
        self._device.write('AM:SOUR EXT')
        self._device.write('AM:EXT:COUP DC')
        self._device.write('AM {0:f}'.format(float(depth)))
        self._device.write('AM:STAT ON')

    def turn_AM_off(self):
        """ Turn off the Amlitude Modulation Mode.

        @return int: error code (0:OK, -1:error)
        """
        self._device.write(':AM:STAT OFF')
