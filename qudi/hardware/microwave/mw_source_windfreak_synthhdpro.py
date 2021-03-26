# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware module for the Windfreak SynthHDPro microwave source.

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


class MicrowaveSynthHDPro(MicrowaveInterface):
    """ Hardware class to controls a SynthHD Pro.

    Example config for copy-paste:

    mw_source_synthhd:
        module.Class: 'microwave.mw_source_windfreak_synthhdpro.MicrowaveSynthHDPro'
        serial_port: 'COM3'
        comm_timeout: 10  # in seconds
        output_channel: 0  # either 0 or 1
    """

    _serial_port = ConfigOption('serial_port', missing='error')
    _comm_timeout = ConfigOption('comm_timeout', default=10, missing='warn')
    _output_channel = ConfigOption('output_channel', 0, missing='info')

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
        """ Initialisation performed during activation of the module.
        """
        # trying to load the visa connection to the module
        self._rm = visa.ResourceManager()
        self._device = self._rm.open_resource(self._serial_port,
                                              baud_rate=9600,
                                              read_termination='\n',
                                              write_termination='\n',
                                              timeout=int(self._comm_timeout * 1000))
        self._model = self._device.query('+')
        for channel in (0, 1):
            ch = self._device.query(f'C{channel:d}C?')
            self.log.debug(f'Ch{ch} Off: {self._off()}')

        ch = self._device.query('C{0:d}C?'.format(self._output_channel))
        self.log.debug(f'Selected channel is Ch{ch}')

        # Generate constraints
        self._constraints = MicrowaveConstraints(
            power_limits=(-60, 20),
            frequency_limits=(53e6, 14e9),
            scan_size_limits=(2, 100),
            scan_modes=(SamplingOutputMode.EQUIDISTANT_SWEEP,)
        )

        self._scan_power = -20
        self._scan_frequencies = None
        self._in_cw_mode = True

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.off()
        self._device.close()
        self._rm.close()
        self._rm = None
        self._device = None

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
            return float(self._device.query('W?'))

    @cw_power.setter
    def cw_power(self, value):
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to set cw_power. Microwave output is active.')
            assert self._constraints.power_in_range(value)[0], \
                f'cw_power to set ({value} dBm) out of bounds for allowed range ' \
                f'{self._constraints.power_limits}'

            self._device.write('X0')
            self._device.write('c1')
            # trigger mode: software
            self._device.write('w0')

            self._device.write(f'W{value:2.3f}')
            self._device.write(f'[{value:2.3f}')
            self._device.write(f']{value:2.3f}')

    @property
    def cw_frequency(self):
        """The CW microwave frequency in Hz. Must implement setter as well.

        @return float: The currently set CW microwave frequency in Hz.
        """
        with self._thread_lock:
            return float(self._device.query('f?')) * 1e6

    @cw_frequency.setter
    def cw_frequency(self, value):
        with self._thread_lock:
            if self.module_state() != 'idle':
                raise RuntimeError('Unable to set cw_frequency. Microwave output is active.')
            assert self._constraints.frequency_in_range(value)[0], \
                f'cw_frequency to set ({value:.9e} Hz) out of bounds for allowed range ' \
                f'{self._constraints.frequency_limits}'

            self._device.write('X0')
            self._device.write('c1')
            # trigger mode: software
            self._device.write('w0')

            # sweep frequency and steps
            self._device.write(f'f{value / 1e6:5.7f}')
            self._device.write(f'l{value / 1e6:5.7f}')
            self._device.write(f'u{value / 1e6:5.7f}')

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
            assert self._constraints.frequency_in_range(min(value))[0] and \
                   self._constraints.frequency_in_range(max(value))[0], \
                f'scan_frequencies to set out of bounds for allowed range ' \
                f'{self._constraints.frequency_limits}'
            assert self._constraints.scan_size_in_range(len(value))[0], \
                f'Number of frequency steps to set ({len(value):d}) out of bounds for ' \
                f'allowed range {self._constraints.scan_size_limits}'

            self._scan_frequencies = np.array(value, dtype=np.float64)
            self._write_sweep()

    @property
    def scan_mode(self):
        """Scan mode Enum. Must implement setter as well.

        @return SamplingOutputMode: The currently set scan mode Enum
        """
        with self._thread_lock:
            return SamplingOutputMode.EQUIDISTANT_SWEEP

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
        return TriggerEdge.RISING

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
                # disable sweep mode
                self._device.write('g0')
                # set trigger source to software
                self._device.write('w0')
                # turn off everything for the current channel
                self.log.debug(f'Off: {self._off()}')
                self.module_state.unlock()

    def cw_on(self):
        """ Switches on cw microwave output.

        Must return AFTER the output is actually active.
        """
        with self._thread_lock:
            if self.module_state() != 'idle':
                if self._in_cw_mode:
                    return
                raise RuntimeError(
                    'Unable to start CW microwave output. Microwave output is currently active.'
                )

            self._in_cw_mode = True
            self.log.debug(f'On: {self._on()}')
            # enable sweep mode and set to start frequency
            self._device.write('g1')
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
            self._on()
            # enable sweep mode and set to start frequency
            self._device.write('g1')
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

            # enable sweep mode and set to start frequency
            self._device.write('g1')

    def _write_sweep(self):
        start, stop, points = self._scan_frequencies
        step = (stop - start) / (points - 1)

        # sweep mode: linear sweep, non-continuous
        self._device.write('X0')
        self._device.write('c0')

        # trigger mode: single step
        self._device.write('w2')

        # sweep direction
        if stop >= start:
            self._device.write('^1')
        else:
            self._device.write('^0')

        # sweep lower and upper frequency and steps
        self._device.write(f'l{start / 1e6:5.7f}')
        self._device.write(f'u{stop / 1e6:5.7f}')
        self._device.write(f's{step / 1e6:5.7f}')

        # set power
        self._device.write(f'W{self._scan_power:2.3f}')
        # set sweep lower end power
        self._device.write(f'[{self._scan_power:2.3f}')
        # set sweep upper end power
        self._device.write(f']{self._scan_power:2.3f}')

    def _off(self):
        """ Turn the current channel off.

        @return tuple: see _stat()
        """
        self._device.write('E0r0h0')
        return self._stat()

    def _on(self):
        """ Turn on the current channel.

        @return tuple(bool): see _stat()
        """
        self._device.write('E1r1h1')
        return self._stat()

    def _stat(self):
        """ Return status of PLL, power amplifier and output power muting for current channel.

        @return tuple(bool): PLL on, power amplifier on, output power muting on
        """
        # PLL status
        E = int(self._device.query('E?'))
        # power amplifier status
        r = int(self._device.query('r?'))
        # hig/low power selector
        h = int(self._device.query('h?'))
        return E, r, h

    def _is_running(self):
        status = self._stat()
        return (status[0] == 1) and (status[1] == 1) and (status[2] == 1)

##########################################################

    # def set_ext_trigger(self, pol, dwelltime):
    #     """ Set the external trigger for this device with proper polarization.
    #
    #     @param TriggerEdge pol: polarisation of the trigger (basically rising edge or falling edge)
    #     @param dwelltime: minimum dwell time
    #
    #     @return object: current trigger polarity [TriggerEdge.RISING, TriggerEdge.FALLING]
    #     """
    #     self.log.debug('Trigger at {} dwell for {}'.format(pol, dwelltime))
    #     self._device.write('t{0:f}'.format(1000 * 0.75 * dwelltime))
    #     newtime = float(self._device.query('t?')) / 1000
    #     return TriggerEdge.RISING, newtime
