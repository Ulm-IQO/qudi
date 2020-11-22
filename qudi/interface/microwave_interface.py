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

from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass
from core.util.helpers import in_range
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
    """This is the Interface class to define the controls for the simple microwave hardware.

    This interface is designed to interface microwave generator where the power and frequency of the produced microwave
    can be set. Is can be operated in CW (continuous wave) or as a sweep system synchronised with a measured device.

    """

    @abstract_interface_method
    def off(self):
        """ Switches off any microwave output.

        @return int: error code (0:OK, -1:error)

        Must return AFTER the device is actually stopped.
        """
        pass

    @abstract_interface_method
    def get_status(self):
        """ Gets the current status of the MW source, i.e. the mode (cw, list or sweep) and
            the output state (stopped, running)

        @return str, bool: mode ['cw', 'list', 'sweep'], is_running [True, False]
        """
        pass

    @abstract_interface_method
    def get_power(self):
        """ Gets the microwave output power for the currently active mode.

        @return float: the output power in dBm
        """
        pass

    @abstract_interface_method
    def get_frequency(self):
        """ Gets the frequency of the microwave output.

        @return [float, list]: frequency(s) currently set for this device in Hz

        Returns single float value if the device is in cw mode.
        Returns list like [start, stop, step] if the device is in sweep mode.
        Returns list of frequencies if the device is in list mode.
        """
        pass

    @abstract_interface_method
    def cw_on(self):
        """ Switches on cw microwave output.

        @return int: error code (0:OK, -1:error)

        Must return AFTER the device is actually running.
        """
        pass

    @abstract_interface_method
    def set_cw(self, frequency=None, power=None):
        """ Configures the device for cw-mode and optionally sets frequency and/or power

        @param (float) frequency: frequency to set in Hz
        @param (float) power: power to set in dBm

        @return tuple(float, float, str): with the relation
            current frequency in Hz,
            current power in dBm,
            current mode
        """
        pass

    @abstract_interface_method
    def list_on(self):
        """  Switches on the list mode microwave output.

        @return int: error code (0:OK, -1:error)

        Must return AFTER the device is actually running.
        """
        pass

    @abstract_interface_method
    def set_list(self, frequency=None, power=None):
        """ Configures the device for list-mode and optionally sets frequencies and/or power

        @param (list(float)) frequency: list of frequencies in Hz
        @param (float) power: MW power of the frequency list in dBm

        @return tuple(list, float, str): current frequencies in Hz, current power in dBm, current mode
        """
        pass

    @abstract_interface_method
    def reset_listpos(self):
        """ Reset of MW list mode position to start (first frequency step)

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abstract_interface_method
    def sweep_on(self):
        """ Switches on the sweep mode.

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abstract_interface_method
    def set_sweep(self, start=None, stop=None, step=None, power=None):
        """  Configures the device for sweep-mode and optionally sets frequency start/stop/step and/or power

        @return float, float, float, float, str: current start frequency in Hz,
                                                 current stop frequency in Hz,
                                                 current frequency step in Hz,
                                                 current power in dBm,
                                                 current mode
        """
        pass

    @abstract_interface_method
    def reset_sweeppos(self):
        """ Reset of MW sweep mode position to start (start frequency)

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abstract_interface_method
    def set_ext_trigger(self, pol, timing):
        """ Set the external trigger for this device with proper polarization.

        @param TriggerEdge pol: polarisation of the trigger (basically rising edge or falling edge)
        @param timing: estimated time between triggers

        @return object, float: current trigger polarity [TriggerEdge.RISING, TriggerEdge.FALLING],
            trigger timing as queried from device
        """
        pass

    def trigger(self):
        """ Trigger the next element in the list or sweep mode programmatically.

        @return int: error code (0:OK, -1:error)

        Ensure that the Frequency was set AFTER the function returns, or give
        the function at least a save waiting time corresponding to the
        frequency switching speed.
        """
        pass

    @abstract_interface_method
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
