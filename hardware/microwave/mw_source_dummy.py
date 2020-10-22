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

import random

from core.module import Base
from interface.microwave_interface import MicrowaveInterface
from interface.microwave_interface import MicrowaveLimits
from interface.microwave_interface import MicrowaveMode
from interface.microwave_interface import TriggerEdge
import time


class MicrowaveDummy(Base, MicrowaveInterface):
    """ A dummy class to emulate a microwave source.

    Example config for copy-paste:

    mw_source_dummy:
        module.Class: 'microwave.mw_source_dummy.MicrowaveDummy'

    """

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.mw_cw_power = -120.0
        self.mw_sweep_power = 0.0
        self.mw_cw_frequency = 2.87e9
        self.mw_frequency_list = list()
        self.mw_start_freq = 2.5e9
        self.mw_stop_freq = 3.1e9
        self.mw_step_freq = 2.0e6

        # frequency switching speed by a program in a list mode:
        self._FREQ_SWITCH_SPEED = 0.008  # Frequency switching speed in s

        self.current_output_mode = MicrowaveMode.CW     # Can be MicrowaveMode.CW, MicrowaveMode.LIST or
                                                        # MicrowaveMode.SWEEP
        self.current_trig_pol = TriggerEdge.RISING      # Can be TriggerEdge.RISING or
                                                        # TriggerEdge.FALLING
        self.output_active = False
        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        pass

    def get_limits(self):
        """Dummy limits"""
        limits = MicrowaveLimits()
        limits.supported_modes = (MicrowaveMode.CW, MicrowaveMode.LIST, MicrowaveMode.SWEEP)

        limits.min_frequency = 100e3
        limits.max_frequency = 20e9

        limits.min_power = -120
        limits.max_power = 30

        limits.list_minstep = 0.001
        limits.list_maxstep = 20e9
        limits.list_maxentries = 10001

        limits.sweep_minstep = 0.001
        limits.sweep_maxstep = 20e9
        limits.sweep_maxentries = 10001
        return limits

    def get_status(self):
        """
        Gets the current status of the MW source, i.e. the mode (cw, list or sweep) and
        the output state (stopped, running)

        @return str, bool: mode ['cw', 'list', 'sweep'], is_running [True, False]
        """
        if self.current_output_mode == MicrowaveMode.CW:
            mode = 'cw'
        elif self.current_output_mode == MicrowaveMode.LIST:
            mode = 'list'
        elif self.current_output_mode == MicrowaveMode.SWEEP:
            mode = 'sweep'
        return mode, self.output_active

    def off(self):
        """ Switches off any microwave output.

        @return int: error code (0:OK, -1:error)
        """
        self.output_active = False
        self.log.info('MicrowaveDummy>off')
        return 0

    def get_power(self):
        """ Gets the microwave output power.

        @return float: the power set at the device in dBm
        """
        self.log.debug('MicrowaveDummy>get_power')
        if self.current_output_mode == MicrowaveMode.CW:
            return self.mw_cw_power
        else:
            return self.mw_sweep_power

    def get_frequency(self):
        """
        Gets the frequency of the microwave output.
        Returns single float value if the device is in cw mode.
        Returns list if the device is in either list or sweep mode.

        @return [float, list]: frequency(s) currently set for this device in Hz
        """
        self.log.debug('MicrowaveDummy>get_frequency')
        if self.current_output_mode == MicrowaveMode.CW:
            return self.mw_cw_frequency
        elif self.current_output_mode == MicrowaveMode.LIST:
            return self.mw_frequency_list
        elif self.current_output_mode == MicrowaveMode.SWEEP:
            return self.mw_start_freq, self.mw_stop_freq, self.mw_step_freq

    def cw_on(self):
        """
        Switches on cw microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        self.current_output_mode = MicrowaveMode.CW
        time.sleep(0.5)
        self.output_active = True
        self.log.info('MicrowaveDummy>CW output on')
        return 0

    def set_cw(self, frequency=None, power=None):
        """
        Configures the device for cw-mode and optionally sets frequency and/or power

        @param float frequency: frequency to set in Hz
        @param float power: power to set in dBm
        @param bool useinterleave: If this mode exists you can choose it.

        @return float, float, str: current frequency in Hz, current power in dBm, current mode

        Interleave option is used for arbitrary waveform generator devices.
        """
        self.log.debug('MicrowaveDummy>set_cw, frequency: {0:f}, power {1:f}:'.format(frequency,
                                                                                      power))
        self.output_active = False
        self.current_output_mode = MicrowaveMode.CW
        if frequency is not None:
            self.mw_cw_frequency = frequency
        if power is not None:
            self.mw_cw_power = power
        return self.mw_cw_frequency, self.mw_cw_power, 'cw'

    def list_on(self):
        """
        Switches on the list mode microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        self.current_output_mode = MicrowaveMode.LIST
        time.sleep(1)
        self.output_active = True
        self.log.info('MicrowaveDummy>List mode output on')
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
            self.mw_cw_power = power
        return self.mw_frequency_list, self.mw_cw_power, 'list'

    def reset_listpos(self):
        """
        Reset of MW list mode position to start (first frequency step)

        @return int: error code (0:OK, -1:error)
        """
        return 0

    def sweep_on(self):
        """ Switches on the sweep mode.

        @return int: error code (0:OK, -1:error)
        """
        self.current_output_mode = MicrowaveMode.SWEEP
        time.sleep(1)
        self.output_active = True
        self.log.info('MicrowaveDummy>Sweep mode output on')
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
        self.log.debug('MicrowaveDummy>set_sweep, start: {0:f}, stop: {1:f}, step: {2:f}, '
                       'power: {3:f}'.format(start, stop, step, power))
        self.output_active = False
        self.current_output_mode = MicrowaveMode.SWEEP
        if (start is not None) and (stop is not None) and (step is not None):
            self.mw_start_freq = start
            self.mw_stop_freq = stop
            self.mw_step_freq = step
        if power is not None:
            self.mw_sweep_power = power
        return self.mw_start_freq, self.mw_stop_freq, self.mw_step_freq, self.mw_sweep_power, \
               'sweep'

    def reset_sweeppos(self):
        """
        Reset of MW sweep mode position to start (start frequency)

        @return int: error code (0:OK, -1:error)
        """
        return 0

    def set_ext_trigger(self, pol, timing):
        """ Set the external trigger for this device with proper polarization.

        @param TriggerEdge pol: polarisation of the trigger (basically rising edge or falling edge)
        @param float timing: estimated time between triggers

        @return object: current trigger polarity [TriggerEdge.RISING, TriggerEdge.FALLING]
        """
        self.log.info('MicrowaveDummy>ext_trigger set')
        self.current_trig_pol = pol
        return self.current_trig_pol, timing

    def trigger(self):
        """ Trigger the next element in the list or sweep mode programmatically.

        @return int: error code (0:OK, -1:error)

        Ensure that the Frequency was set AFTER the function returns, or give
        the function at least a save waiting time.
        """

        time.sleep(self._FREQ_SWITCH_SPEED)  # that is the switching speed
        return
