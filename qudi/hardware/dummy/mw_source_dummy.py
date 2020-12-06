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

import time
import numpy as np

from qudi.core.module import Base
from qudi.core.util.mutex import RecursiveMutex
from qudi.interface.microwave_interface import MicrowaveInterface, MicrowaveConstraints
from qudi.interface.microwave_interface import MicrowaveMode, TriggerEdge


class MicrowaveDummy(Base, MicrowaveInterface):
    """ A dummy class to emulate a microwave source.

    Example config for copy-paste:

    mw_source_dummy:
        module.Class: 'microwave.mw_source_dummy.MicrowaveDummy'

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._thread_lock = RecursiveMutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # CW parameters
        self._cw_power = -120.0
        self._cw_frequency = 2.87e9
        # LIST parameters
        self._list_power = 0.0
        self._list_frequencies = list()
        # SWEEP parameters
        self._sweep_power = 0.0
        self._sweep_start = 2.82e9
        self._sweep_stop = 2.92e9
        self._sweep_points = 101

        self._trigger_edge = TriggerEdge.RISING
        self._trigger_frequency = 100.0

        self._output_mode = MicrowaveMode.INVALID
        self._output_active = False

        self._constraints = MicrowaveConstraints(
            supported_modes={MicrowaveMode.CW, MicrowaveMode.LIST, MicrowaveMode.SWEEP},
            supported_trigger_edges={TriggerEdge.FALLING, TriggerEdge.RISING},
            trigger_rate_limits=(0.001, 1000),
            frequency_limits=(100e3, 20e9),
            power_limits=(-120, 30),
            list_points_limits=(2, 10001),
            list_step_limits=(0.001, 20e9),
            sweep_points_limits=(2, 10001),
            sweep_step_limits=(0.001, 20e9)
        )

    def on_deactivate(self):
        pass

    @property
    def constraints(self):
        """ Return the device-specific parameter constraints.

        @return MicrowaveConstraints: Microwave constraints object
        """
        return self._constraints

    @property
    def output_state(self):
        """ Returns the current state of the microwave output (mode and bool indicating activity).

        @return (MicrowaveMode, bool): Current output MicrowaveMode and active flag (Active: True)
        """
        return self._output_mode, self._output_active

    @property
    def trigger_parameters(self):
        """ Return current external trigger setup.

        @return (TriggerEdge, float): current trigger edge and estimated trigger frequency (in Hz)
        """
        return self._trigger_edge, self._trigger_frequency

    @property
    def cw_parameters(self):
        """ Return currently set frequency and power of CW mode.
        Raises exception if CW mode is not supported.

        @return (float, float): current frequency (in Hz) and power (in dBm) for CW mode
        """
        assert self._constraints.mode_supported(MicrowaveMode.CW)
        return self._cw_frequency, self._cw_power

    @property
    def list_parameters(self):
        """ Return currently set frequency list and power of LIST mode.
        Raises exception if LIST mode is not supported.

        @return (float[], float): current frequency list (in Hz) and power (in dBm) for LIST mode
        """
        assert self._constraints.mode_supported(MicrowaveMode.LIST)
        return self._list_frequencies, self._list_power

    @property
    def sweep_parameters(self):
        """ Return currently set start and stop frequency, number of frequencies and power of
        SWEEP mode.
        Raises exception if no SWEEP mode is supported.

        @return (float, float, int, float): sweep parameters (start, stop, points, power)
        """
        assert self._constraints.mode_supported(MicrowaveMode.SWEEP)
        return self._sweep_start, self._sweep_stop, self._sweep_points, self._sweep_power

    def off(self):
        """ Switches off any microwave output regardless of current active. Does not raise if
        already inactive.
        """
        with self._thread_lock:
            time.sleep(0.5)
            self._output_active = False
            self._output_mode = MicrowaveMode.INVALID
            if self.module_state() == 'locked':
                self.module_state.unlock()

    def cw_on(self):
        """ Switches on cw microwave output. """
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to turn CW microwave on. Output already active'
            self.module_state.lock()
            time.sleep(0.5)
            self._output_mode = MicrowaveMode.CW
            self._output_active = True

    def set_cw(self, frequency=None, power=None):
        """ Sets frequency and/or power for CW mode

        @param float frequency: frequency to set in Hz
        @param float power: power to set in dBm
        """
        with self._thread_lock:
            assert self._output_mode != MicrowaveMode.CW, \
                'Unable to change CW parameters while CW output is active'
            if frequency is not None:
                new_frequency = self._constraints.frequency_in_range(frequency)
                assert new_frequency == frequency, 'CW frequency to set out of bounds'
                self._cw_frequency = new_frequency
            if power is not None:
                new_power = self._constraints.power_in_range(power)
                assert new_power == power, 'CW power to set out of bounds'
                self._cw_power = new_power

    def list_on(self):
        """ Switches on the list mode microwave output. """
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to turn LIST microwave on. Output already active'
            self.module_state.lock()
            time.sleep(1)
            self._output_mode = MicrowaveMode.LIST
            self._output_active = True

    def set_list(self, frequencies=None, power=None):
        """ Sets frequency list and/or power for LIST mode

        @param float[] frequencies: list of frequencies in Hz
        @param float power: power to set in dBm
        """
        with self._thread_lock:
            assert self._output_mode != MicrowaveMode.LIST, \
                'Unable to change LIST parameters while LIST output is active'
            if frequencies is not None:
                points = len(frequencies)
                assert points == self._constraints.list_points_in_range(points), \
                    'Number of frequencies in LIST mode out of bounds.'
                steps = [abs(f - frequencies[ii]) for ii, f in enumerate(frequencies[1:])]
                assert all(s == self._constraints.list_step_in_range(s) for s in steps), \
                    'One or more frequency steps in LIST mode out of bounds'
                new_frequencies = [self._constraints.frequency_in_range(f) for f in frequencies]
                assert all(new_frequencies[ii] == f for ii, f in enumerate(frequencies)), \
                    'One or more LIST frequencies to set out of bounds'
                self._list_frequencies = new_frequencies
            if power is not None:
                new_power = self._constraints.power_in_range(power)
                assert new_power == power, 'LIST power to set out of bounds'
                self._list_power = new_power

    def reset_list(self):
        """ Reset list mode to start (first frequency step) """
        with self._thread_lock:
            assert self._output_mode == MicrowaveMode.LIST and self._output_active, \
                'Unable to reset frequency list. LIST mode output is not active.'

    def sweep_on(self):
        """ Switches on the sweep mode microwave output.

        Must return AFTER the device is actually running.
        """
        with self._thread_lock:
            assert self.module_state() == 'idle', \
                'Unable to turn SWEEP microwave on. Output already active'
            self.module_state.lock()
            time.sleep(1)
            self._output_mode = MicrowaveMode.SWEEP
            self._output_active = True

    def set_sweep(self, start=None, stop=None, points=None, power=None):
        """ Sets frequency start/stop/points and/or power for SWEEP mode

        @param float start: start frequency to set in Hz
        @param float stop: stop frequency to set in Hz
        @param int points: number of frequencies to set
        @param float power: power to set in dBm
        """
        with self._thread_lock:
            assert self._output_mode != MicrowaveMode.SWEEP, \
                'Unable to change SWEEP parameters while SWEEP output is active'
            if any(arg is not None for arg in (start, stop, points)):
                assert all(arg is not None for arg in (start, stop, points)), \
                    'must provide start, stop and points for sweep mode together.'
                new_start = self._constraints.frequency_in_range(start)
                new_stop = self._constraints.frequency_in_range(stop)
                new_points = self._constraints.sweep_points_in_range(points)
                assert start == new_start, 'SWEEP start frequency out of bounds'
                assert stop == new_stop, 'SWEEP stop frequency out of bounds'
                assert points == new_points, 'Number of SWEEP points out of bounds'
                step = abs(stop - start) / (points - 1)
                assert step == self._constraints.sweep_step_in_range(step), \
                    'SWEEP frequency step size out of bounds'
                self._sweep_start = new_start
                self._sweep_stop = new_stop
                self._sweep_points = new_points
            if power is not None:
                new_power = self._constraints.power_in_range(power)
                assert new_power == power, 'SWEEP power to set out of bounds'
                self._sweep_power = new_power

    def reset_sweep(self):
        """ Reset sweep mode to start """
        with self._thread_lock:
            assert self._output_mode == MicrowaveMode.SWEEP and self._output_active, \
                'Unable to reset frequency sweep. SWEEP mode output is not active.'

    def set_trigger(self, edge=None, frequency=None):
        """ Set the external trigger for this device with proper polarization and approx. frequency.

        @param TriggerEdge edge: Active trigger edge to listen to
        @param float frequency: estimated trigger frequency in Hz
        """
        with self._thread_lock:
            assert not self._output_active or self._output_mode == MicrowaveMode.CW, \
                'Unable to set trigger parameters while LIST or SWEEP mode is active.'
            if edge is not None:
                assert self._constraints.trigger_edge_supported(edge)
                self._trigger_edge = edge
            if frequency is not None:
                new_frequency = self._constraints.trigger_rate_in_range(frequency)
                assert new_frequency == frequency, 'Estimated trigger frequency out of bounds'
                self._trigger_frequency = new_frequency

    def trigger(self):
        """ Trigger the next frequency in LIST or SWEEP mode programmatically """
        time.sleep(1/self._trigger_frequency)
