# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interface file to control microwave devices.

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

    def off(self):
        """ Switches off any microwave output.

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MicrowaveInterface>off')

    def get_power(self):
        """ Gets the microwave output power.

        @return float: the power set at the device in dBm
        """
        raise InterfaceImplementationError('MicrowaveInterface>get_power')

    def set_power(self, power=0.):
        """ Sets the microwave output power.

        @param float power: the power (in dBm) set for this device

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MicrowaveInterface>set_power')

    def get_frequency(self):
        """ Gets the frequency of the microwave output.

        @return float: frequency (in Hz), which is currently set for this device
        """
        raise InterfaceImplementationError('MicrowaveInterface>get_frequency')

    def set_frequency(self, freq=0.):
        """ Sets the frequency of the microwave output.

        @param float freq: the frequency (in Hz) set for this device

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MicrowaveInterface>set_frequency')

    def set_cw(self, freq=None, power=None, useinterleave=None):
        """ Sets the MW mode to cw and additionally frequency and power

        @param float freq: frequency to set in Hz
        @param float power: power to set in dBm
        @param bool useinterleave: If this mode exists you can choose it.

        @return int: error code (0:OK, -1:error)

        Interleave option is used for arbitrary waveform generator devices.
        """
        raise InterfaceImplementationError('MicrowaveInterface>set_cw')

    def set_list(self, freq=None, power=None):
        """ Sets the MW mode to list mode

        @param list freq: list of frequencies in Hz
        @param float power: MW power of the frequency list in dBm

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MicrowaveInterface>set_list')

    def reset_listpos(self):
        """ Reset of MW List Mode position to start from first given frequency

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MicrowaveInterface>reset_listpos')

    def list_on(self):
        """ Switches on the list mode.

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MicrowaveInterface>list_on')

    def sweep_on(self):
        """ Switches on the sweep mode.

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MicrowaveInterface>sweep_on')

    def set_sweep(self, start, stop, step, power):
        """ Sweep from frequency start to frequency sto pin steps of width stop with power.
        """
        raise InterfaceImplementationError('MicrowaveInterface>set_sweep')

    def reset_sweep(self):
        """ Reset of MW sweep position to start

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MicrowaveInterface>sweep_reset')

    def sweep_pos(self, frequency=None):
        """
        """
        raise InterfaceImplementationError('MicrowaveInterface>sweep_pos')

    def set_ex_trigger(self, source, pol):
        """ Set the external trigger for this device with proper polarization.

        @param str source: channel name, where external trigger is expected.
        @param str pol: polarisation of the trigger (basically rising edge or
                        falling edge)

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MicrowaveInterface>trigger')

    def set_modulation(self, flag=None):
        """
        """
        raise InterfaceImplementationError('MicrowaveInterface>set_modulation')

    def output(self):
        """
        """
        raise InterfaceImplementationError('MicrowaveInterface>output')

    def am(self, depth=None):
        """

        @return float:
        """
        raise InterfaceImplementationError('MicrowaveInterface>am')

    def get_limits(self):
        """ Return the device-specific limits in a nested dictionary.

          @return dict: limits dictionary

            The following structure is absolutely necessary:
            frequency:
                min:
                max:
            power:
                min:
                max:
            list:
                minstep:
                maxstep:
                maxentries:
            sweep:
                minstep:
                maxstep:
                maxentries:

           Frequency in Hz, power in dBm, minstep/maxstep in Hz.
        """
        raise InterfaceImplementationError('MicrowaveInterface>get_limits')

