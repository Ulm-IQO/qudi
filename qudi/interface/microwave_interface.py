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

from enum import Enum
from abc import abstractmethod
from qudi.core.module import InterfaceBase
from qudi.core.util.helpers import in_range


class TriggerEdge(Enum):
    """ On which electrical signal edge does a trigger occur? So edgy...!
    """
    INVALID = -1
    FALLING = 0
    RISING = 1


class MicrowaveMode(Enum):
    """ Operating modes for microwave generators.
    CW: continuous wave with fixed frequency
    LIST: ouptut list of arbitrary frequencies, each step triggered by electrical trigger input
    SWEEP: frequency sweep from f1 to f2, each step triggered by electrical trigger input
    """
    INVALID = -1
    CW = 0
    LIST = 1
    SWEEP = 2


class MicrowaveInterface(InterfaceBase):
    """This is the Interface class to define the controls for the simple microwave hardware.

    This interface is designed to interface microwave generator where the power and frequency of
    the produced microwave can be set.
    It can be operated in CW (continuous wave) or as a sweep system synchronised with a sampling
    device.
    """

    @property
    @abstractmethod
    def constraints(self):
        """ Return the device-specific parameter constraints.

        @return MicrowaveConstraints: Microwave constraints object
        """
        pass

    @property
    @abstractmethod
    def output_state(self):
        """ Returns the current state of the microwave output (mode and bool indicating activity).

        @return (MicrowaveMode, bool): Current output MicrowaveMode and active flag (Active: True)
        """
        pass

    @property
    @abstractmethod
    def trigger_parameters(self):
        """ Return current external trigger setup.

        @return (TriggerEdge, float): current trigger edge and estimated trigger frequency (in Hz)
        """
        pass

    @property
    @abstractmethod
    def cw_parameters(self):
        """ Return currently set frequency and power of CW mode.
        Raises exception if CW mode is not supported.

        @return (float, float): current frequency (in Hz) and power (in dBm) for CW mode
        """
        pass

    @property
    @abstractmethod
    def list_parameters(self):
        """ Return currently set frequency list and power of LIST mode.
        Raises exception if LIST mode is not supported.

        @return (float[], float): current frequency list (in Hz) and power (in dBm) for LIST mode
        """
        pass

    @property
    @abstractmethod
    def sweep_parameters(self):
        """ Return currently set start and stop frequency, number of frequencies and power of
        SWEEP mode.
        Raises exception if no SWEEP mode is supported.

        @return (float, float, int, float): sweep parameters (start, stop, points, power)
        """
        pass

    @abstractmethod
    def off(self):
        """ Switches off any microwave output regardless of current active. Does nothing if already
        inactive.

        Must return AFTER the device has actually stopped.
        """
        pass

    @abstractmethod
    def cw_on(self):
        """ Switches on cw microwave output.

        Must return AFTER the device is actually running.
        """
        pass

    @abstractmethod
    def set_cw(self, frequency=None, power=None):
        """ Sets frequency and/or power for CW mode

        @param float frequency: frequency to set in Hz
        @param float power: power to set in dBm
        """
        pass

    @abstractmethod
    def list_on(self):
        """ Switches on the list mode microwave output.

        Must return AFTER the device is actually running.
        """
        pass

    @abstractmethod
    def set_list(self, frequencies=None, power=None):
        """ Sets frequency list and/or power for LIST mode

        @param float[] frequencies: list of frequencies in Hz
        @param float power: power to set in dBm
        """
        pass

    @abstractmethod
    def reset_list(self):
        """ Reset list mode to start (first frequency step) """
        pass

    @abstractmethod
    def sweep_on(self):
        """ Switches on the sweep mode microwave output.

        Must return AFTER the device is actually running.
        """
        pass

    @abstractmethod
    def set_sweep(self, start=None, stop=None, points=None, power=None):
        """ Sets frequency start/stop/points and/or power for SWEEP mode

        @param float start: start frequency to set in Hz
        @param float stop: stop frequency to set in Hz
        @param int points: number of frequencies to set
        @param float power: power to set in dBm
        """
        pass

    @abstractmethod
    def reset_sweep(self):
        """ Reset sweep mode to start """
        pass

    @abstractmethod
    def set_trigger(self, edge=None, frequency=None):
        """
        Set the external trigger for this device with proper polarization and/or approx. frequency.

        @param TriggerEdge edge: Active trigger edge to listen to
        @param float frequency: estimated trigger frequency in Hz
        """
        pass

    def trigger(self):
        """ Trigger the next frequency in LIST or SWEEP mode programmatically """
        pass


class MicrowaveConstraints:
    """ A container to hold all limits for microwave sources.
    """
    def __init__(self, supported_modes, supported_trigger_edges, trigger_rate_limits,
                 frequency_limits, power_limits,
                 list_points_limits, list_step_limits,
                 sweep_points_limits, sweep_step_limits):
        assert len(frequency_limits) == 2
        assert len(power_limits) == 2
        assert len(list_points_limits) == 2
        assert len(list_step_limits) == 2
        assert len(sweep_points_limits) == 2
        assert len(sweep_step_limits) == 2
        assert len(trigger_rate_limits) == 2
        assert all(isinstance(mode, MicrowaveMode) for mode in supported_modes)
        assert all(isinstance(edge, TriggerEdge) for edge in supported_trigger_edges)

        self._supported_modes = frozenset(supported_modes)
        self._supported_trigger_edges = frozenset(supported_trigger_edges)
        self._trigger_rate_limits = (
            float(min(trigger_rate_limits)), float(max(trigger_rate_limits))
        )
        self._frequency_limits = (float(min(frequency_limits)), float(max(frequency_limits)))
        self._power_limits = (float(min(power_limits)), float(max(power_limits)))
        self._list_points_limits = (int(min(list_points_limits)), int(max(list_points_limits)))
        self._list_step_limits = (float(min(list_step_limits)), float(max(list_step_limits)))
        self._sweep_points_limits = (int(min(sweep_points_limits)), int(max(sweep_points_limits)))
        self._sweep_step_limits = (float(min(sweep_step_limits)), float(max(sweep_step_limits)))

    @property
    def supported_modes(self):
        return self._supported_modes

    @property
    def supported_trigger_edges(self):
        return self._supported_trigger_edges

    @property
    def trigger_rate_limits(self):
        return self._trigger_rate_limits

    @property
    def min_trigger_rate(self):
        return self._trigger_rate_limits[0]

    @property
    def max_trigger_rate(self):
        return self._trigger_rate_limits[1]

    @property
    def frequency_limits(self):
        return self._frequency_limits

    @property
    def min_frequency(self):
        return self._frequency_limits[0]

    @property
    def max_frequency(self):
        return self._frequency_limits[1]

    @property
    def power_limits(self):
        return self._power_limits

    @property
    def min_power(self):
        return self._power_limits[0]

    @property
    def max_power(self):
        return self._power_limits[1]

    @property
    def list_points_limits(self):
        return self._list_points_limits

    @property
    def min_list_points(self):
        return self._list_points_limits[0]

    @property
    def max_list_points(self):
        return self._list_points_limits[1]

    @property
    def list_step_limits(self):
        return self._list_step_limits

    @property
    def min_list_step(self):
        return self._list_step_limits[0]

    @property
    def max_list_step(self):
        return self._list_step_limits[1]

    @property
    def sweep_points_limits(self):
        return self._sweep_points_limits

    @property
    def min_sweep_points(self):
        return self._sweep_points_limits[0]

    @property
    def max_sweep_points(self):
        return self._sweep_points_limits[1]

    @property
    def sweep_step_limits(self):
        return self._sweep_step_limits

    @property
    def min_sweep_step(self):
        return self._sweep_step_limits[0]

    @property
    def max_sweep_step(self):
        return self._sweep_step_limits[1]

    def mode_supported(self, mode):
        return mode in self._supported_modes

    def trigger_edge_supported(self, edge):
        return edge in self._supported_trigger_edges

    def trigger_rate_in_range(self, rate):
        return in_range(rate, *self._trigger_rate_limits)

    def frequency_in_range(self, frequency):
        return in_range(frequency, *self._frequency_limits)

    def power_in_range(self, power):
        return in_range(power, *self._power_limits)

    def list_step_in_range(self, step):
        return in_range(step, *self._list_step_limits)

    def list_points_in_range(self, points):
        return in_range(points, *self._list_points_limits)

    def sweep_step_in_range(self, step):
        return in_range(step, *self._sweep_step_limits)

    def sweep_points_in_range(self, points):
        return in_range(points, *self._sweep_points_limits)
