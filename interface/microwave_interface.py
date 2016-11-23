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

import abc
from core.util.interfaces import InterfaceMetaclass
from core.util.units import in_range
from enum import Enum

class TriggerEdge(Enum):
    """ On which electrical signal edge does a trigger occur?
      So edgy!
    """
    RISING = 0
    FALLING = 1
    NONE = 3
    UNKNOWN = 4

class MicrowaveMode(Enum):
    """ Modes for microwave generators:
        CW: continuous wave
        LIST: ouptut list of arbitrary frequencies, each step triggered by electrical input
        SWEEP: frequency sweep from f1 to f2, each step triggered by electrical input
        ASWEEP: frequency sweep from f1 to f2, triggered only on the start of the sweep
    """
    CW = 0
    LIST = 1
    SWEEP = 3
    ASWEEP = 4

class MicrowaveInterface(metaclass=InterfaceMetaclass):
    """This is the Interface class to define the controls for the simple
    microwave hardware.
    """

    _modclass = 'MicrowaveInterface'
    _modtype = 'interface'

    @abc.abstractmethod
    def on(self):
        """ Switches on any preconfigured microwave output.

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def off(self):
        """ Switches off any microwave output.

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def get_power(self):
        """ Gets the microwave output power.

        @return float: the power set at the device in dBm
        """
        pass

    @abc.abstractmethod
    def set_power(self, power=0.):
        """ Sets the microwave output power.

        @param float power: the power (in dBm) set for this device

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def get_frequency(self):
        """ Gets the frequency of the microwave output.

        @return float: frequency (in Hz), which is currently set for this device
        """
        pass

    @abc.abstractmethod
    def set_frequency(self, freq=0.):
        """ Sets the frequency of the microwave output.

        @param float freq: the frequency (in Hz) set for this device

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def set_cw(self, freq=None, power=None, useinterleave=None):
        """ Sets the MW mode to cw and additionally frequency and power

        @param float freq: frequency to set in Hz
        @param float power: power to set in dBm
        @param bool useinterleave: If this mode exists you can choose it.

        @return int: error code (0:OK, -1:error)

        Interleave option is used for arbitrary waveform generator devices.
        """
        pass

    @abc.abstractmethod
    def set_list(self, freq=None, power=None):
        """ Sets the MW mode to list mode

        @param list freq: list of frequencies in Hz
        @param float power: MW power of the frequency list in dBm

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def reset_listpos(self):
        """ Reset of MW List Mode position to start from first given frequency

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def list_on(self):
        """ Switches on the list mode.

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def sweep_on(self):
        """ Switches on the sweep mode.

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def set_sweep(self, start, stop, step, power):
        """ Sweep from frequency start to frequency sto pin steps of width stop with power.
        """
        pass

    @abc.abstractmethod
    def reset_sweep(self):
        """ Reset of MW sweep position to start

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def set_ext_trigger(self, pol=TriggerEdge.RISING):
        """ Set the external trigger for this device with proper polarization.

        @param TriggerEdge pol: polarisation of the trigger (basically rising edge or
                        falling edge)

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def get_limits(self):
        """ Return the device-specific limits in a nested dictionary.

          @return MicrowaveLimits: Microwave limits object
        """
        pass


class MicrowaveLimits:
    """ A container to hold all limits for microwave sources.
    """
    def __init__(self):
        """Create an instance containing all parameters with default values."""

        self.supported_modes = (
            MicrowaveMode.CW,
            MicrowaveMode.LIST,
            MicrowaveMode.SWEEP,
            MicrowaveMode.ASWEEP,
        )

        # frequency in Hz
        self.min_frequency = 1e6
        self.max_frequency = 1e9

        # power in dBm
        self.min_power = -10
        self.max_power = 0

        # list limits, frequencies in Hz, entries are single steps
        self.list_minstep = 1
        self.list_maxstep = 1e9
        self.list_maxentries = 1e3

        # sweep limits, frequencies in Hz, entries are single steps
        self.sweep_minstep = 1
        self.sweep_maxstep = 1e9
        self.sweep_maxentries = 1e3

        # analog sweep limits, slope in Hz/s
        self.sweep_minslope = 1
        self.sweep_maxslope = 1e9

    def frequency_in_range(self, frequency):
        return in_range(frequency, self.min_frequency, self.max_frequency)

    def power_in_range(self, power):
        return in_range(power, self.min_power, self.max_power)

    def list_step_in_range(self, step):
        return in_range(step, self.list_minstep, self.list_maxstep)

    def sweep_step_in_range(self, step):
        return in_range(step, self.sweep_minstep, self.sweep_maxstep)

    def slope_in_range(self, slope):
        return in_range(slope, self.sweep_minslope, self.sweep_maxslope)
