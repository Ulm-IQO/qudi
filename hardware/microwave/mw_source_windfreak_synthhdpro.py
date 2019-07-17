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
from core.module import Base
from core.configoption import ConfigOption
from interface.microwave_interface import MicrowaveInterface
from interface.microwave_interface import MicrowaveLimits
from interface.microwave_interface import MicrowaveMode
from interface.microwave_interface import TriggerEdge
import time


class MicrowaveSynthHDPro(Base, MicrowaveInterface):
    """ Hardware class to controls a SynthHD Pro.

    Example config for copy-paste:

    mw_source_synthhd:
        module.Class: 'microwave.mw_source_windfreak_synthhdpro.MicrowaveSynthHDPro'
        serial_port: 'COM3'
        serial_timeout: 10 # in seconds
        output_channel: 0 # either 0 or 1

    """

    _serial_port = ConfigOption('serial_port', missing='error')
    _serial_timeout = ConfigOption('serial_timeout', 10, missing='warn')
    _channel = ConfigOption('output_channel', 0, missing='info')

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # trying to load the visa connection to the module
        self.rm = visa.ResourceManager()
        self._conn = self.rm.open_resource(
            self._serial_port,
            baud_rate=9600,
            read_termination='\n',
            write_termination='\n',
            timeout=self._serial_timeout*1000
        )
        self.model = self._conn.query('+')
        self.sernr = self._conn.query('-')
        self.mod_hw = self._conn.query('v1')
        self.mod_fw = self._conn.query('v0')

        self.log.info('Found {0} Ser No: {1} {2} {3}'.format(
            self.model, self.sernr, self.mod_hw, self.mod_fw)
        )

        # query temperature sensor
        tmp = self._conn.query('z')
        self.log.info('MW synth temperature: {0}°C'.format(tmp))

        for channel in (0, 1):
            ch = self._conn.query('C{0:d}C?'.format(channel))
            self.log.debug('Ch{} Off: {}'.format(ch, self._off()))

        ch = self._conn.query('C{0:d}C?'.format(self._channel))
        self.log.debug('Selected channel ic Ch{}'.format(ch))

        self.current_output_mode = MicrowaveMode.CW

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._conn.close()
        self.rm.close()

    def get_limits(self):
        """SynthHD Pro limits"""
        limits = MicrowaveLimits()
        limits.supported_modes = (MicrowaveMode.CW, MicrowaveMode.SWEEP)  # MicrowaveMode.LIST)

        limits.min_frequency = 53e6
        limits.max_frequency = 14e9

        limits.min_power = -60
        limits.max_power = 20

        limits.list_minstep = 0.01
        limits.list_maxstep = 14e9
        limits.list_maxentries = 100

        limits.sweep_minstep = 0.01
        limits.sweep_maxstep = 14e9
        limits.sweep_maxentries = 100
        return limits

    def get_status(self):
        """
        Gets the current status of the MW source, i.e. the mode (cw, list or sweep) and
        the output state (stopped, running)

        @return str, bool: mode ['cw', 'list', 'sweep'], is_running [True, False]
        """
        mode = ''

        status = self._stat()
        active = status[0] == 1 and status[1] == 1 and status[2] == 1

        if self.current_output_mode == MicrowaveMode.CW:
            mode = 'cw'
        elif self.current_output_mode == MicrowaveMode.LIST:
            mode = 'list'
        elif self.current_output_mode == MicrowaveMode.SWEEP:
            mode = 'sweep'
        return mode, active

    def off(self):
        """ Switches off any microwave output.

        @return int: error code (0:OK, -1:error)
        """
        # disable sweep mode
        self._conn.write('g0')
        # set trigger source to software
        self._conn.write('w0')
        # turn off everything for the current channel
        self.log.debug('Off: {}'.format(self._off()))
        return 0

    def get_power(self):
        """ Gets the microwave output power.

        @return float: the power set at the device in dBm
        """
        if self.current_output_mode == MicrowaveMode.CW:
            # query mw power
            mw_cw_power = float(self._conn.query('W?'))
            return mw_cw_power
        else:
            return self.mw_sweep_power

    def get_frequency(self):
        """
        Gets the frequency of the microwave output.
        Returns single float value if the device is in cw mode.
        Returns list if the device is in either list or sweep mode.

        @return [float, list]: frequency(s) currently set for this device in Hz
        """
        if self.current_output_mode == MicrowaveMode.CW:
            # query frequency
            mw_cw_frequency = float(self._conn.query('f?')) * 1e6
            return mw_cw_frequency
        elif self.current_output_mode == MicrowaveMode.LIST:
            return self.mw_frequency_list
        elif self.current_output_mode == MicrowaveMode.SWEEP:
            mw_start_freq = float(self._conn.query('l?')) * 1e6
            mw_stop_freq = float(self._conn.query('u?')) * 1e6
            mw_step_freq = float(self._conn.query('s?')) * 1e6
            return mw_start_freq, mw_stop_freq, mw_step_freq

    def cw_on(self):
        """
        Switches on cw microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        self.current_output_mode = MicrowaveMode.CW
        self.log.debug('On: {}'.format(self._on()))
        # enable sweep mode and set to start frequency
        self._conn.write('g1')
        return 0

    def set_cw(self, frequency=None, power=None):
        """
        Configures the device for cw-mode and optionally sets frequency and/or power

        @param float frequency: frequency to set in Hz
        @param float power: power to set in dBm
        @return float, float, str: current frequency in Hz, current power in dBm, current mode
        """
        self.current_output_mode = MicrowaveMode.CW

        self._conn.write('X0')
        self._conn.write('c1')

        # trigger mode: software
        self._conn.write('w0')

        # sweep frequency and steps

        if frequency is not None:
            self._conn.write('f{0:5.7f}'.format(frequency / 1e6))
            self._conn.write('l{0:5.7f}'.format(frequency / 1e6))
            self._conn.write('u{0:5.7f}'.format(frequency / 1e6))
        if power is not None:
            self._conn.write('W{0:2.3f}'.format(power))
            self._conn.write('[{0:2.3f}'.format(power))
            self._conn.write(']{0:2.3f}'.format(power))

        mw_cw_freq = float(self._conn.query('f?')) * 1e6
        mw_cw_power = float(self._conn.query('W?'))
        self.log.debug('CW f: {0} {2} P: {1} {3}'.format(frequency, power, mw_cw_freq, mw_cw_power))
        return mw_cw_freq, mw_cw_power, 'cw'

    def list_on(self):
        """
        Switches on the list mode microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        self.current_output_mode = MicrowaveMode.LIST
        time.sleep(1)
        self.output_active = True
        self.log.warn('MicrowaveDummy>List mode output on')
        return 0

    def set_list(self, frequency=None, power=None):
        """
        Configures the device for list-mode and optionally sets frequencies and/or power

        @param list frequency: list of frequencies in Hz
        @param float power: MW power of the frequency list in dBm

        @return list, float, str: current frequencies in Hz, current power in dBm, current mode
        """
        self.log.debug('MicrowaveDummy>set_list, frequency_list: {0}, power: {1:f}'
                       ''.format(frequency, power))
        self.output_active = False
        self.current_output_mode = MicrowaveMode.LIST
        if frequency is not None:
            self.mw_frequency_list = frequency
        if power is not None:
            # set power
            self._conn.write('W{0:2.3f}'.format(power))
        return self.mw_frequency_list, self.mw_cw_power, 'list'

    def reset_listpos(self):
        """
        Reset of MW list mode position to start (first frequency step)

        @return int: error code (0:OK, -1:error)
        """
        self._conn.write('g1')  # enable sweep mode and set to start frequency
        return 0

    def sweep_on(self):
        """ Switches on the sweep mode.

        @return int: error code (0:OK, -1:error)
        """
        self.current_output_mode = MicrowaveMode.SWEEP
        self._on()
        # enable sweep mode and set to start frequency
        self._conn.write('g1')
        # query sweep mode
        mode = int(self._conn.query('g?'))
        return 0

    def set_sweep(self, start=None, stop=None, step=None, power=None):
        """
        Configures the device for sweep-mode and optionally sets frequency start/stop/step
        and/or power

        @return float, float, float, float, str: current start frequency in Hz,
                                                 current stop frequency in Hz,
                                                 current frequency step in Hz,
                                                 current power in dBm,
                                                 current mode
        """
        self.current_output_mode = MicrowaveMode.SWEEP
        if (start is not None) and (stop is not None) and (step is not None):
            # sweep mode: linear sweep, non-continuous
            self._conn.write('X0')
            self._conn.write('c0')

            # trigger mode: single step
            self._conn.write('w2')

            # sweep direction
            if stop >= start:
                self._conn.write('^1')
            else:
                self._conn.write('^0')

            # sweep lower and upper frequency and steps
            self._conn.write('l{0:5.7f}'.format(start / 1e6))
            self._conn.write('u{0:5.7f}'.format(stop / 1e6))
            self._conn.write('s{0:5.7f}'.format(step / 1e6))

        # sweep power
        if power is not None:
            # set power
            self._conn.write('W{0:2.3f}'.format(power))
            # set sweep lower end power
            self._conn.write('[{0:2.3f}'.format(power))
            # set sweep upper end power
            self._conn.write(']{0:2.3f}'.format(power))

        # query lower frequency
        mw_start_freq = float(self._conn.query('l?')) * 1e6
        # query upper frequency
        mw_stop_freq = float(self._conn.query('u?')) * 1e6
        # query sweep step size
        mw_step_freq = float(self._conn.query('s?')) * 1e6
        # query power
        mw_power = float(self._conn.query('W?'))
        # query sweep lower end power
        mw_sweep_power_start = float(self._conn.query('[?'))
        # query sweep upper end power
        mw_sweep_power_stop = float(self._conn.query(']?'))
        self.log.debug('SWEEP: {} -> {} {}, {} -> {} {}, {} -> {}'.format(
            start, stop, step, mw_start_freq, mw_stop_freq, mw_step_freq, mw_power,
            mw_sweep_power_start, mw_sweep_power_stop))
        return (
            mw_start_freq,
            mw_stop_freq,
            mw_step_freq,
            mw_sweep_power_start,
            'sweep'
        )

    def reset_sweeppos(self):
        """
        Reset of MW sweep mode position to start (start frequency)

        @return int: error code (0:OK, -1:error)
        """
        # enable sweep mode and set to start frequency
        self._conn.write('g1')
        return 0

    def set_ext_trigger(self, pol, dwelltime):
        """ Set the external trigger for this device with proper polarization.

        @param TriggerEdge pol: polarisation of the trigger (basically rising edge or falling edge)
        @param dwelltime: minimum dwell time

        @return object: current trigger polarity [TriggerEdge.RISING, TriggerEdge.FALLING]
        """
        self.log.debug('Trigger at {} dwell for {}'.format(pol, dwelltime))
        self._conn.write('t{0:f}'.format(1000 * 0.75 * dwelltime))
        newtime = float(self._conn.query('t?')) / 1000
        return TriggerEdge.RISING, newtime

    def trigger(self):
        """ Trigger the next element in the list or sweep mode programmatically.

        @return int: error code (0:OK, -1:error)

        Ensure that the Frequency was set AFTER the function returns, or give
        the function at least a save waiting time.
        """
        return

    def _off(self):
        """ Turn the current channel off.

        @return tuple: see _stat()
        """
        self._conn.write('E0r0h0')
        return self._stat()

    def _on(self):
        """ Turn on the current channel.

        @return tuple(bool): see _stat()
        """
        self._conn.write('E1r1h1')
        return self._stat()

    def _stat(self):
        """ Return status of PLL, power amplifier and output power muting for current channel.

        @return tuple(bool): PLL on, power amplifier on, output power muting on
        """
        # PLL status
        E = int(self._conn.query('E?'))
        # power amplifier status
        r = int(self._conn.query('r?'))
        # hig/low power selector
        h = int(self._conn.query('h?'))
        return E, r, h
