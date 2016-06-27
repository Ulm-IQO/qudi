# -*- coding: utf-8 -*-

"""
This file contains the QuDi Interface file to control microwave devices.

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

from core.util.customexceptions import InterfaceImplementationError

class MicrowaveInterface():
    """This is the Interface class to define the controls for the simple
    microwave hardware.
    """

    _modclass = 'MicrowaveInterface'
    _modtype = 'interface'


    def on(self):
        """ Switches on any preconfigured microwave output.

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MicrowaveInterface>on')
        return -1

    def off(self):
        """ Switches off any microwave output.

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MicrowaveInterface>off')
        return -1

    def get_power(self):
        """ Gets the microwave output power.

        @return float: the power set at the device in dBm
        """
        raise InterfaceImplementationError('MicrowaveInterface>get_power')
        return 0.0

    def set_power(self, power=0.):
        """ Sets the microwave output power.

        @param float power: the power (in dBm) set for this device

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MicrowaveInterface>set_power')
        return -1

    def get_frequency(self):
        """ Gets the frequency of the microwave output.

        @return float: frequency (in Hz), which is currently set for this device
        """
        raise InterfaceImplementationError('MicrowaveInterface>get_frequency')
        return 0.0

    def set_frequency(self, freq=0.):
        """ Sets the frequency of the microwave output.

        @param float freq: the frequency (in Hz) set for this device

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MicrowaveInterface>set_frequency')
        return -1

    def set_cw(self, freq=None, power=None, useinterleave=None):
        """ Sets the MW mode to cw and additionally frequency and power

        @param float freq: frequency to set in Hz
        @param float power: power to set in dBm
        @param bool useinterleave: If this mode exists you can choose it.

        @return int: error code (0:OK, -1:error)

        Interleave option is used for arbitrary waveform generator devices.
        """
        raise InterfaceImplementationError('MicrowaveInterface>set_cw')
        return -1

    def set_list(self, freq=None, power=None):
        """ Sets the MW mode to list mode

        @param list freq: list of frequencies in Hz
        @param float power: MW power of the frequency list in dBm

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MicrowaveInterface>set_list')
        return -1

    def reset_listpos(self):
        """ Reset of MW List Mode position to start from first given frequency

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MicrowaveInterface>reset_listpos')
        return -1

    def list_on(self):
        """ Switches on the list mode.

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MicrowaveInterface>list_on')
        return -1

    def set_sweep(self, frequency_start=None, frequency_stop=None, frequency_delta=None):
        """
        """
        raise InterfaceImplementationError('MicrowaveInterface>set_sweep')
        return -1

    def sweep_pos(self, frequency=None):
        """
        """
        raise InterfaceImplementationError('MicrowaveInterface>sweep_pos')
        return -1

    def set_ex_trigger(self, source, pol):
        """ Set the external trigger for this device with proper polarization.

        @param str source: channel name, where external trigger is expected.
        @param str pol: polarisation of the trigger (basically rising edge or
                        falling edge)

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MicrowaveInterface>trigger')
        return -1

    def set_modulation(self, flag=None):
        """
        """
        raise InterfaceImplementationError('MicrowaveInterface>set_modulation')
        return -1

    def output(self):
        """
        """
        raise InterfaceImplementationError('MicrowaveInterface>output')
        return -1

    def am(self, depth=None):
        """

        @return float:
        """
        raise InterfaceImplementationError('MicrowaveInterface>am')
        return -1




