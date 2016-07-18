# -*- coding: utf-8 -*-

"""
This file contains the QuDi hardware file to control the microwave dummy.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import random

from core.base import Base
import core.logger as logger
from interface.microwave_interface import MicrowaveInterface


class MicrowaveDummy(Base, MicrowaveInterface):
    """This is the Interface class to define the controls for the simple
    microwave hardware.
    """
    _modclass = 'MicrowaveDummy'
    _modtype = 'mwsource'

    ## declare connectors
    _out = {'mwsourcedummy': 'MicrowaveInterface'}

    def __init__(self, manager, name, config, **kwargs):
        # declare actions for state transitions
        state_actions = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, state_actions, **kwargs)

        logger.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            logger.info("{}: {}".format(key,config[key]))

        # trying to load the visa connection
        try:
            import visa
        except:
            logger.error('No visa connection installed. Please install '
                    'pyvisa.')

    def activation(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """
        pass

    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        pass

    def get_limits(self):
        """Dummy limits"""
        limits = {
            'frequency': {
                'min': 100 * 10e3,
                'max': 50 * 10e9
                },
            'power': {
                'min': -120,
                'max': 30
                },
            'list': {
                'minstep': 1,
                'maxstep': 10 * 10e9,
                'maxentries': 5000
                },
            'sweep': {
                'minstep': 0.1,
                'maxstep': 10 * 10e9,
                'maxentries': 10 * 10e9
                }
            }
        return limits

    def on(self):
        """ Switches on any preconfigured microwave output.

        @return int: error code (0:OK, -1:error)
        """
        logger.warning('MicrowaveDummy>on')
        return 0

    def off(self):
        """ Switches off any microwave output.

        @return int: error code (0:OK, -1:error)
        """
        logger.warning('MicrowaveDummy>off')
        return 0

    def get_power(self):
        """ Gets the microwave output power.

        @return float: the power set at the device in dBm
        """
        logger.warning('MicrowaveDummy>get_power')
        return random.uniform(-10, 10)

    def set_power(self,power=None):
        """ Sets the microwave output power.

        @param float power: the power (in dBm) set for this device

        @return int: error code (0:OK, -1:error)
        """
        logger.warning('MicrowaveDummy>set_power, power: {0:f}'.format(power))
        return 0


    def get_frequency(self):
        """ Gets the frequency of the microwave output.

        @return float: frequency (in Hz), which is currently set for this device
        """
        logger.warning('MicrowaveDummy>get_frequency')
        return random.uniform(0, 1e6)

    def set_frequency(self, freq=None):
        """ Sets the frequency of the microwave output.

        @param float freq: the frequency (in Hz) set for this device

        @return int: error code (0:OK, -1:error)
        """
        logger.warning('MicrowaveDummy>set_frequency, frequency: '
                    '{0:f}'.format(freq))
        return 0

    def set_cw(self, freq=None, power=None, useinterleave=None):
        """ Sets the MW mode to cw and additionally frequency and power

        @param float freq: frequency to set in Hz
        @param float power: power to set in dBm
        @param bool useinterleave: If this mode exists you can choose it.

        @return int: error code (0:OK, -1:error)

        Interleave option is used for arbitrary waveform generator devices.
        """
        logger.warning('MicrowaveDummy>set_cw, frequency: {0:f}, power '
                    '{0:f}:'.format(freq, power))
        return 0

    def set_list(self, freq=None, power=None):
        """ Sets the MW mode to list mode

        @param list freq: list of frequencies in Hz
        @param float power: MW power of the frequency list in dBm

        @return int: error code (0:OK, -1:error)
        """

        logger.warning('MicrowaveDummy>set_list,\nfrequency (Hz): {0}\n'
                    'power (dBm): {1}'.format(freq, power))
        return 0

    def reset_listpos(self):
        """ Reset of MW List Mode position to start from first given frequency

        @return int: error code (0:OK, -1:error)
        """
        # logger.warning('MicrowaveDummy>reset_listpos')
        return 0

    def list_on(self):
        """ Switches on the list mode.

        @return int: error code (0:OK, -1:error)
        """
        logger.warning('MicrowaveDummy>list_on')
        return 0

    def set_ex_trigger(self, source, pol):
        """ Set the external trigger for this device with proper polarization.

        @param str source: channel name, where external trigger is expected.
        @param str pol: polarisation of the trigger (basically rising edge or
                        falling edge)

        @return int: error code (0:OK, -1:error)
        """
        pass


