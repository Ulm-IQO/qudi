# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware file to control SRS SG devices.

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


class MicrowaveSRSSG(MicrowaveInterface):
    """ Hardware control class to controls SRS SG390 devices.

    Example config for copy-paste:

    mw_source_srssg:
        module.Class: 'microwave.mw_source_srssg.MicrowaveSRSSG'
        visa_address: 'GPIB0::12::INSTR'
        comm_timeout: 10

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
        self._scan_power = -20
        self._scan_frequencies = None
        self._in_cw_mode = True

    def on_activate(self):
        """ Initialisation performed during activation of the module. """
        # trying to load the visa connection to the module
        self._rm = visa.ResourceManager()
        self._device = self._rm.open_resource(self._visa_address,
                                              timeout=int(self._comm_timeout * 1000))

        # Reset device
        self._device.write('*RST')
        self._device.write('ENBR 0')  # turn off Type N output
        self._device.write('ENBL 0')  # turn off BNC output

        self._model = self._device.query('*IDN?').strip().split(',')[1]

        # Generate constraints
        # SRS has two output connectors. The specifications are used for the Type N output.
        if self._model == 'SG392':
            freq_limits = (1e6, 2.025e9)
        elif self._model == 'SG394':
            freq_limits = (1e6, 4.050e9)
        elif self._model == 'SG396':
            freq_limits = (1e6, 6.075e9)
        else:
            freq_limits = (1e6, 6.075e9)
            self.log.error(f'Model brand "{self._model}" unknown, hardware limits may be wrong!')
        self._constraints = MicrowaveConstraints(
            power_limits=(-110, 16.5),
            frequency_limits=freq_limits,
            scan_size_limits=(2, 2000),
            scan_modes=(SamplingOutputMode.JUMP_LIST,)
        )

        self._scan_frequencies = None
        self._scan_power = self._constraints.min_power
        self._in_cw_mode = True

    def on_deactivate(self):
        """ Cleanup performed during deactivation of the module."""
        self.off()
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
            return float(self._device.query('AMPR?'))

    @cw_power.setter
    def cw_power(self, value):
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to set cw_power. Microwave output is active.')
            assert self._constraints.power_in_range(value)[0], \
                f'cw_power to set ({value} dBm) out of bounds for allowed range ' \
                f'{self._constraints.power_limits}'

            # disable modulation:
            self._device.write('MODL 0')
            # and the subtype (analog,)
            self._device.write('STYP 0')
            self._device.write(f'AMPR {value:f}')

    @property
    def cw_frequency(self):
        """The CW microwave frequency in Hz. Must implement setter as well.

        @return float: The currently set CW microwave frequency in Hz.
        """
        with self._thread_lock:
            return float(self._device.query('FREQ?'))

    @cw_frequency.setter
    def cw_frequency(self, value):
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to set cw_frequency. Microwave output is active.')
            assert self._constraints.frequency_in_range(value)[0], \
                f'cw_frequency to set ({value:.9e} Hz) out of bounds for allowed range ' \
                f'{self._constraints.frequency_limits}'

            # disable modulation:
            self._device.write('MODL 0')
            # and the subtype (analog,)
            self._device.write('STYP 0')
            self._device.write(f'FREQ {value:e}')

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
                self._write_list()

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
            assert self._constraints.frequency_in_range(min(value))[0] and \
                   self._constraints.frequency_in_range(max(value))[0], \
                f'scan_frequencies to set out of bounds for allowed range ' \
                f'{self._constraints.frequency_limits}'
            assert self._constraints.scan_size_in_range(len(value))[0], \
                f'Number of frequency steps to set ({len(value):d}) out of bounds for ' \
                f'allowed range {self._constraints.scan_size_limits}'

            self._scan_frequencies = np.array(value, dtype=np.float64)
            self._write_list()

    @property
    def scan_mode(self):
        """Scan mode Enum. Must implement setter as well.

        @return SamplingOutputMode: The currently set scan mode Enum
        """
        with self._thread_lock:
            return SamplingOutputMode.JUMP_LIST

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

    @property
    def trigger_edge(self):
        """Input trigger polarity Enum for scanning. Must implement setter as well.

        @return TriggerEdge: The currently set active input trigger edge
        """
        return TriggerEdge.NONE

    @trigger_edge.setter
    def trigger_edge(self, value):
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to set trigger_edge. Microwave output is active.')
            assert isinstance(value, TriggerEdge), \
                'trigger_edge must be Enum type qudi.core.enums.TriggerEdge'

            self.log.warning('No external trigger channel can be set in this hardware. '
                             'Method will be skipped.')

    def off(self):
        """Switches off any microwave output (both scan and CW).
        Must return AFTER the device has actually stopped.
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                self._device.write('ENBR 0')
                while self._output_active():
                    time.sleep(0.1)
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

            self._in_cw_mode = True
            self._rf_on()
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

            self._in_cw_mode = False
            self._rf_on()
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

            self._device.write('LSTR')

    def _command_wait(self, command_str):
        """ Writes the command in command_str via PyVisa and waits until the device has finished
        processing it.

        @param str command_str: The command to be written
        """
        self._device.write(command_str)
        self._device.write('*WAI')
        while int(float(self._device.query('*OPC?'))) != 1:
            time.sleep(0.2)

    def _write_list(self):
        # delete a previously created list:
        self._device.write('LSTD')

        # ask for a new list
        self._device.query(f'LSTC? {len(self._scan_frequencies):d}')

        for ii, freq in enumerate(self._scan_frequencies):
            self._device.write(
                f'LSTP {ii:d},{freq:e},N,N,N,{self._scan_power:f},N,N,N,N,N,N,N,N,N,N'
            )
        # the commands contains 15 entries, which are related to the
        # following commands (in brackets the explanation), if parameter is
        # specified as 'N', then it will be left unchanged.
        #
        #   '1,2,3,4,5,6,7,8,9,10,11,12,13,14,15'
        #
        #   Position explanation:
        #
        #   1 = FREQ (frequency in exponential representation: e.g. 1.45e9)
        #   2 = PHAS (phase in degree as float, e.g.45.0 )
        #   3 = AMPL (Amplitude of LF in dBm as float, BNC output, e.g. -45.0)
        #   4 = OFSL (Offset of LF in Volt as float, BNC output, e.g. 0.02)
        #   5 = AMPR (Amplitude of RF in dBm as float, Type N output, e.g. -45.0)
        #   6 = DISP (set the Front panel display type as integer)
        #           0: Modulation Type
        #           1: Modulation Function
        #           2: Frequency
        #           3: Phase
        #           4: Modulation Rate or Period
        #           5: Modulation Deviation or Duty Cycle
        #           6: RF Type N Amplitude
        #           7: BNC Amplitude
        #           10: BNC Offset
        #           13: I Offset
        #           14: Q Offset
        #   7 = Enable/Disable modulation by an integer number, with the
        #       following bit meaning:
        #           Bit 0: MODL (Enable modulation)
        #           Bit 1: ENBL (Disable LF, BNC output)
        #           Bit 2: ENBR (Disable RF, Type N output)
        #           Bit 3:  -   (Disable Clock output)
        #           Bit 4:  -   (Disable HF, RF doubler output)
        #   8 = TYPE (Modulation type, integer number with the meaning)
        #           0: AM/ASK   (amplitude modulation)
        #           1: FM/FSK   (frequency modulation)
        #           2: ΦM/PSK   (phase modulation)
        #           3: Sweep
        #           4: Pulse
        #           5: Blank
        #           7: QAM (quadrature amplitude modulation)
        #           8: CPM (continuous phase modulation)
        #           9: VSB (vestigial/single sideband modulation)
        #   9 = Modulation function, integer number. Note that not all
        #       values are valid in all modulation modes. In brackets
        #       behind the possible modulation functions are denoted with
        #       the meaning: MFNC = AM/FM/ΦM,  SFNC = Sweep,
        #                    PFNC = Pulse/Blank, QFNC = IQ
        #           0: Sine                 MFNC, SFNC,       QFNC
        #           1: Ramp                 MFNC, SFNC,       QFNC
        #           2: Triangle             MFNC, SFNC,       QFNC
        #           3: Square               MFNC,       PFNC, QFNC
        #           4: Phase noise          MFNC,       PFNC, QFNC
        #           5: External             MFNC, SFNC, PFNC, QFNC
        #           6: Sine/Cosine                            QFNC
        #           7: Cosine/Sine                            QFNC
        #           8: IQ Noise                               QFNC
        #           9: PRBS symbols                           QFNC
        #           10: Pattern (16 bits)                     QFNC
        #           11: User waveform       MFNC, SFNC, PFNC, QFNC
        #  10 = RATE/SRAT/(PPER, RPER)
        #       Modulation rate in frequency as float, e.g. 20.4 (for 20.4kHz)
        #       with the meaning
        #  11 = (ADEP, ANDP)/(FDEV, FNDV)/(PDEV, PNDV)/SDEV/PWID
        #       Modulation deviation in percent as float (e.g. 90.0 for 90%
        #       modulation depth)
        #  12 = Amplitude of clock output
        #  13 = Offset of clock output
        #  14 = Amplitude of HF (RF doubler output)
        #  15 = Offset of rear DC
        # enable the created list:
        self._device.write('LSTE 1')

    def _rf_on(self):
        """ Switches on any preconfigured microwave output.
        """
        self._device.write('ENBR 1')
        while not self._output_active():
            time.sleep(0.1)

    def _output_active(self):
        return bool(int(self._ask('ENBR?').strip()))

    ########################################################################################
    ########################################################################################
    ########################################################################################
    ########################################################################################
    ########################################################################################
    ########################################################################################
    ########################################################################################

    # def sweep_on(self):
    #     """ Switches on the sweep mode.
    #
    #     @return int: error code (0:OK, -1:error)
    #     """
    #     self._internal_mode = 'sweep'
    #     self.log.error('This was never tested!')
    #     return self.on()
    #
    # def set_sweep(self, start, stop, step, power):
    #     """ Sweep from frequency start to frequency sto pin steps of width stop with power.
    #     """
    #     # set the type
    #     self._device.write('MODL 3')
    #     # and the subtype
    #     self._device.write('STYP 0')
    #
    #     sweep_length = stop - start
    #     index = 0
    #
    #     time_per_freq =  2e-3 # in Hz, 2ms per point assumed for the beginning
    #     # time it takes for a whole sweep, which is the rate of the sweep,
    #     # i.e. rate = 1/ time_for_freq_range
    #     rate = (sweep_length/step) * time_per_freq
    #     mod_type = 5 # blank
    #     mod_func = 3 # blank
    #     self._device.write('LSTP {0:d},{1:e},N,N,N,{2:f},N,N,{3},{4},{5:e},{6:e},N,N,N,N'.format(index, start, power, mod_type, mod_func, rate, sweep_length))
    #     self._internal_mode = 'sweep'
    #
    #     self.log.error('This was never tested!')
    #
    #     return start, stop, step, power, self._internal_mode
    #
    # def reset_sweeppos(self):
    #     """ Reset of MW sweep position to start
    #
    #     @return int: error code (0:OK, -1:error)
    #     """
    #     self._internal_mode = 'sweep'
    #     self.log.error('This was never tested!')
    #     return self.reset_listpos()
