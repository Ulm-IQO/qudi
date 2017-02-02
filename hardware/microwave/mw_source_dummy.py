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

from core.base import Base
from interface.microwave_interface import MicrowaveInterface
from interface.microwave_interface import MicrowaveLimits
from interface.microwave_interface import MicrowaveMode
from interface.microwave_interface import TriggerEdge


class MicrowaveDummy(Base, MicrowaveInterface):
    """This is the Interface class to define the controls for the simple
    microwave hardware.
    """
    _modclass = 'MicrowaveDummy'
    _modtype = 'mwsource'

    ## declare connectors
    _out = {'mwsourcedummy': 'MicrowaveInterface'}

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info("{0}: {1}".format(key,config[key]))

    def on_activate(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """
        self.mw_power = -120
        pass

    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
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

    def on(self):
        """ Switches on any preconfigured microwave output.

        @return int: error code (0:OK, -1:error)
        """
        self.log.info('MicrowaveDummy>on')
        return 0

    def off(self):
        """ Switches off any microwave output.

        @return int: error code (0:OK, -1:error)
        """
        self.log.info('MicrowaveDummy>off')
        return 0

    def get_power(self):
        """ Gets the microwave output power.

        @return float: the power set at the device in dBm
        """
        self.log.info('MicrowaveDummy>get_power')
        return self.mw_power

    def set_power(self, power=None):
        """ Sets the microwave output power.

        @param float power: the power (in dBm) set for this device

        @return int: error code (0:OK, -1:error)
        """
        self.mw_power = power
        self.log.info('MicrowaveDummy>set_power, power: {0:f}'.format(power))
        return 0

    def get_frequency(self):
        """ Gets the frequency of the microwave output.

        @return float: frequency (in Hz), which is currently set for this device
        """
        self.log.info('MicrowaveDummy>get_frequency')
        return random.uniform(0, 1e6)

    def set_frequency(self, freq=None):
        """ Sets the frequency of the microwave output.

        @param float freq: the frequency (in Hz) set for this device

        @return int: error code (0:OK, -1:error)
        """
        self.log.info('MicrowaveDummy>set_frequency, frequency: {0:f}'.format(freq))
        return 0

    def set_cw(self, freq=None, power=None, useinterleave=None):
        """ Sets the MW mode to cw and additionally frequency and power

        @param float freq: frequency to set in Hz
        @param float power: power to set in dBm
        @param bool useinterleave: If this mode exists you can choose it.

        @return int: error code (0:OK, -1:error)

        Interleave option is used for arbitrary waveform generator devices.
        """
        self.log.info(
            'MicrowaveDummy>set_cw, frequency: {0:f}, power {0:f}:'.format(freq, power))
        return 0

    def set_list(self, freq=None, power=None):
        """ Sets the MW mode to list mode

        @param list freq: list of frequencies in Hz
        @param float power: MW power of the frequency list in dBm

        @return int: error code (0:OK, -1:error)
        """

        self.log.info(
            'MicrowaveDummy>set_list,\nfrequency: {0}Hz\npower : {1}dBm'.format(freq, power))
        return 0

    def reset_listpos(self):
        """ Reset of MW List Mode position to start from first given frequency

        @return int: error code (0:OK, -1:error)
        """
        # self.log.warning('MicrowaveDummy>reset_listpos')
        return 0

    def list_on(self):
        """ Switches on the list mode.

        @return int: error code (0:OK, -1:error)
        """
        self.log.info('MicrowaveDummy>list_on')
        return 0

    def set_ext_trigger(self, pol=TriggerEdge.RISING):
        """ Set the external trigger for this device with proper polarization.

        @param TriggerEdge pol: polarisation of the trigger (basically rising edge or
                        falling edge)

        @return int: error code (0:OK, -1:error)
        """
        self.log.info('MicrowaveDummy>ext_trigger')
        return 0

    def sweep_on(self):
        """ Switches on the sweep mode.

        @return int: error code (0:OK, -1:error)
        """
        self.log.info('MicrowaveDummy>sweep_on')
        return 0

    def set_sweep(self, start, stop, step, power):
        """ Sweep from frequency start to frequency sto pin steps of width stop with power.
        """
        self.log.info(
            'MicrowaveDummy>set_sweep {0} {1} {2} {3}'.format(start, stop, step, power))
        return 0

    def reset_sweep(self):
        """ Reset of MW sweep position to start

        @return int: error code (0:OK, -1:error)
        """
        return 0
