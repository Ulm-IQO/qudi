"""
This module controls AOM diffraction efficiency by voltage

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

import numpy as np
import time

from logic.generic_logic import GenericLogic
from core.connector import Connector
from core.statusvariable import StatusVar


class AomLogic(GenericLogic):
    """ This is the logic for controlling AOM diffraction efficiency via process_value_modifier and laserlogic

    The idea is to use an voltage output and a power-meter input to calibrate the power versus voltage curve.
    Another important task is to update the maximum power reachable via this method.
    """

    voltage_output = Connector(interface='ProcessControlInterface')
    power_input = Connector(interface='ProcessInterface')
    control_laser_interfuse = Connector(interface='ProcessControlModifier')
    savelogic = Connector(interface='SaveLogic')

    _time_before_start = StatusVar('time_before_start', 5)
    _resolution = StatusVar('resolution', 50)
    _delay_after_change = StatusVar('delay_after_change', 0.5)
    _delay_between_repetitions = StatusVar('delay_between_repetitions', .2)
    _repetitions = StatusVar('repetitions', 5)

    _abort_requested = None

    def on_activate(self):
        pass

    def on_deactivate(self):
        pass

# Protected functions

    def _get_power(self, repetitions=1):
        """ Helper method to read the power multiple times and return average """
        total_power = 0
        success = 0
        for i in range(repetitions):
            try:
                total_power += self.voltage_output().get_process_value()
                success += 1
            except:
                self.log.warning('Power-meter value unreadable')
            finally:
                time.sleep(self._delay_between_repetitions)
        if success == 0:
            raise ConnectionError('Could not read any value from power-meter')
        return total_power / success

    def _do_sweep(self):
        """ Method that launch a calibration sequence to measure power versus voltage """
        if self.module_state() != 'idle':
            self.log.error("Can not calibrate AOM. Logic module is not idle.")
        self.module_state.run()
        self._abort_requested = False
        time.sleep(self._time_before_start)
        voltages = np.linspace(0, self.voltage_output().get_control_limit()[1], self._resolution)
        powers_read = np.zeros(self._resolution)
        for i, voltage in enumerate(voltages):
            self.voltage_output().set_control_value(voltage)
            time.sleep(self._delay_after_change)
            powers_read[i] = self._get_power(self._repetitions)
            if self._abort_requested:
                self._abort_requested = False
                return None
        self.module_state.stop()
        return voltages, powers_read

# Accessible methods

    def calibrate(self):
        """ Method to call that full calibration procedure """
        result = self._do_sweep()
        if result is None: # is case of aborted sweep
            return
        voltages, powers_read = result
        power_max = powers_read.max()
        powers_normalized = powers_read / power_max

        i_max = np.argmax(powers_read)
        y = np.append(np.zeros(1), voltages[0:i_max + 1])
        x = np.append(np.zeros(1), powers_read[0:i_max + 1])

        self.control_laser_interfuse().update_calibration(np.array([x, y]).transpose())
        self.control_laser_interfuse().set_max_power(power_max)

    def calibrate_max(self):
        """ Method to calibrate only max power based on measured value """
        self.voltage_output().set_control_value(self.voltage_output().get_control_limit()[1])
        time.sleep(self._delay_after_change)
        power_max = self._get_power(self._repetitions)
        self.control_laser_interfuse().set_max_power(power_max)

    def calibrate_max_from_value(self, value):
        """ Method to calibrate maximum power based on a value passed as parameter """
        self.control_laser_interfuse().set_max_power(value)

    def abort(self):
        """ Method to abort the measurement sweep """
        if self.module_state() == 'running':
            self._abort_requested = True

# Attribute getters and setters

    @property
    def time_before_start(self):
        return self._time_before_start

    @time_before_start.setter
    def time_before_start(self, val):
        self._time_before_start = float(val)

    @property
    def resolution(self):
        return self._resolution

    @resolution.setter
    def resolution(self, val):
        self._resolution = int(val)

    @property
    def delay_after_change(self):
        return self._delay_after_change

    @delay_after_change.setter
    def delay_after_change(self, val):
        self._delay_after_change = float(val)

    @property
    def delay_between_repetitions(self):
        return self._delay_between_repetitions

    @delay_between_repetitions.setter
    def delay_between_repetitions(self, val):
        self._delay_between_repetitions = float(val)

    @property
    def repetitions(self):
        return self._repetitions

    @repetitions.setter
    def delay_between_repetitions(self, val):
        self._repetitions = int(val)
