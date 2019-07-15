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
    _modclass = 'MicrowaveDummy'
    _modtype = 'mwsource'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._output_active = False

        self._current_output_mode = None
        self._current_trig_pol = None
        self._timing = 1e-3
        
        self._mw_cw_power = -120.0
        self._mw_cw_frequency = 2.87e9

        self._mw_frequency_list = list()
        self._mw_power_list = list()

        self._mw_sweep_power = 0.0
        self._mw_start_freq = 2.5e9
        self._mw_stop_freq = 3.1e9
        self._mw_step_freq = 2.0e6

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        # frequency switching speed by a program in a list mode:
        self._FREQ_SWITCH_SPEED = 0.008  # Frequency switching speed in s

        self._current_output_mode = MicrowaveMode.CW     # Can be MicrowaveMode.CW, MicrowaveMode.LIST or
                                                        # MicrowaveMode.SWEEP
        self._current_trig_pol = TriggerEdge.RISING      # Can be TriggerEdge.RISING or
                                                        # TriggerEdge.FALLING
        self._output_active = False
        return

    def on_deactivate(self):
        """ De-initialisation performed during deactivation of the module.
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

        @return dict: A dict containing the mode and output state but also information about the class
        """
        statusdict = {
            'mode': str(self._current_output_mode),
            'output_active': self._output_active,
            'module_state': self.module_state(),
        }
        return statusdict

    def off(self):
        """ Switches off any microwave output.

        @return int: error code (0:OK, -1:error)
        """
        self._output_active = False
        self.log.info('MicrowaveDummy>off')
        return 0

    def cw_on(self):
        """
        Switches on cw microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        self._current_output_mode = MicrowaveMode.CW
        time.sleep(0.5)
        self._output_active = True
        self.log.info('MicrowaveDummy>CW output on')
        return 0
    
    def get_parameters_cw(self):
        """
        Gets the current parameters of the cw mode: microwave output power and frequency as single values.

        @return tuple(float, float, str): frequency in Hz, the output power in dBm, current mode
        """
        return self._mw_cw_frequency, self._mw_cw_power

    def set_parameters_cw(self, frequency=None, power=None):
        """
        Configures the device for cw-mode and optionally sets frequency and/or power

        @param float frequency: frequency to set in Hz
        @param float power: power to set in dBm

        @return int: error code (0:OK, -1:error)
        """
        self.log.debug('MicrowaveDummy>set_cw, frequency: {0:f}, power {0:f}:'.format(frequency,
                                                                                      power))
        self.off()
        self._current_output_mode = MicrowaveMode.CW
        if frequency is not None:
            self._mw_cw_frequency = frequency
        if power is not None:
            self._mw_cw_power = power
        return 0

    def list_on(self):
        """
        Switches on the list mode microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        self._current_output_mode = MicrowaveMode.LIST
        time.sleep(1)
        self._output_active = True
        self.log.info('MicrowaveDummy>List mode output on')
        return 0

    def get_parameters_list(self):
        """
        Gets the current parameters of the list mode: microwave output power and frequency as lists.

        @return tuple(list, list, str): list of frequency in Hz, list of output powers in dBm, current mode
        """
        return self._mw_frequency_list, self._mw_power_list, str(self._current_output_mode)

    def set_parameters_list(self, frequency=None, power=None):
        """
        Configures the device for list-mode and optionally sets frequencies and/or power

        @param list frequency: list of frequencies in Hz
        @param list power: MW power of the frequency list in dBm

        @return int: error code (0:OK, -1:error)
        """
        self.log.debug('MicrowaveDummy>set_list, frequency_list: {0}, power: {1}'
                       ''.format(frequency, power))
        self.off()
        self._current_output_mode = MicrowaveMode.LIST
        if frequency is not None:
            self._mw_frequency_list = frequency
        if power is not None:
            self._mw_power_list = power
        return 0

    def reset_list_pos(self):
        """
        Reset of MW list mode position to start (first frequency step)

        @return int: error code (0:OK, -1:error)
        """
        return 0

    def sweep_on(self):
        """ Switches on the sweep mode.

        @return int: error code (0:OK, -1:error)
        """
        self._current_output_mode = MicrowaveMode.SWEEP
        time.sleep(1)
        self._output_active = True
        self.log.info('MicrowaveDummy>Sweep mode output on')
        return 0
    
    def get_parameters_sweep(self):
        """
        Gets the current parameters of the sweep mode: parameters of the sweep and a single power.

        @return float, float, float, float, str: current start frequency in Hz,
                                                 current stop frequency in Hz,
                                                 current frequency step in Hz,
                                                 current power in dBm,
                                                 current mode
        """
        return self._mw_start_freq, self._mw_stop_freq, self._mw_step_freq, self._mw_sweep_power, \
               str(self._current_output_mode)

    def set_parameters_sweep(self, start=None, stop=None, step=None, power=None):
        """
        Configures the device for sweep-mode and optionally sets frequency start/stop/step
        and/or power

        @return int: error code (0:OK, -1:error)
        """
        self.log.debug('MicrowaveDummy>set_sweep, start: {0:f}, stop: {1:f}, step: {2:f}, '
                       'power: {3:f}'.format(start, stop, step, power))
        self.off()
        self._current_output_mode = MicrowaveMode.SWEEP
        if (start is not None) and (stop is not None) and (step is not None):
            self._mw_start_freq = start
            self._mw_stop_freq = stop
            self._mw_step_freq = step
        if power is not None:
            self._mw_sweep_power = power
        return 0

    def reset_sweep_pos(self):
        """
        Reset of MW sweep mode position to start (start frequency)

        @return int: error code (0:OK, -1:error)
        """
        return 0

    def get_ext_trigger(self):
        """ Get the external trigger for this device with proper polarization.

        @return object, float: current trigger polarity [TriggerEdge.RISING, TriggerEdge.FALLING],
            trigger timing as queried from device
        """
        return self._current_trig_pol, self._timing

    def set_ext_trigger(self, pol, timing):
        """ Set the external trigger for this device with proper polarization.

        @param TriggerEdge pol: polarisation of the trigger (basically rising edge or falling edge)
        @param timing: estimated time between triggers

        @return int: error code (0:OK, -1:error)
        """
        self.log.info('MicrowaveDummy>ext_trigger set')
        self._current_trig_pol = pol
        self._timing = timing
        return 0

    def trigger(self):
        """ Trigger the next element in the list or sweep mode programmatically.

        @return int: error code (0:OK, -1:error)

        Ensure that the Frequency was set AFTER the function returns, or give
        the function at least a save waiting time.
        """

        time.sleep(self._FREQ_SWITCH_SPEED)  # that is the switching speed
        return 0
