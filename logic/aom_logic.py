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
import matplotlib.pyplot as plt
import time
from collections import OrderedDict
from qtpy import QtCore

from logic.generic_logic import GenericLogic
from core.connector import Connector
from core.statusvariable import StatusVar


class AomLogic(GenericLogic):
    """ This is the logic for controlling AOM diffraction efficiency via process_value_modifier and laserlogic

    The idea is to use an voltage output and a power-meter input to calibrate the power versus voltage curve.
    Another important task is to update the maximum power reachable via this method.

    Example configuration :

    aomlogic:
        module.Class: 'aom_logic.AomLogic'
        connect:
            voltage_output: 'processdummy'
            power_input: 'processdummy'
            control_laser_interfuse: 'control_laser_interfuse'
            output_modifier: 'power_to_volt_modifier'
            laser: 'laserlogic'
            savelogic: 'savelogic'
    """

    voltage_output = Connector(interface='ProcessControlInterface')
    output_modifier = Connector(interface='ProcessControlModifier')
    power_input = Connector(interface='ProcessInterface')
    control_laser_interfuse = Connector(interface='Interfuse')
    laser = Connector(interface='LaserLogic')
    savelogic = Connector(interface='SaveLogic')

    _time_before_start = StatusVar('time_before_start', 5)
    _resolution = StatusVar('resolution', 50)
    _delay_after_change = StatusVar('delay_after_change', 0.5)
    _delay_between_repetitions = StatusVar('delay_between_repetitions', .2)
    _repetitions = StatusVar('repetitions', 5)

    _voltages = StatusVar('voltages', [0])
    _powers = StatusVar('power', [0])

    _abort_requested = None

    sigNewDataPoint = QtCore.Signal()
    sigNewMaxPower = QtCore.Signal()
    sigStarted = QtCore.Signal()
    sigFinished = QtCore.Signal()
    sigParameterChanged = QtCore.Signal()

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
                total_power += self.power_input().get_process_value()
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
        self.sigStarted.emit()
        self._abort_requested = False
        self._voltages = []
        voltages = np.linspace(0, self.voltage_output().get_control_limit()[1], self._resolution)
        self._powers = []
        self.sigNewDataPoint.emit()
        time.sleep(self._time_before_start)
        for voltage in voltages:
            self.voltage_output().set_control_value(voltage)
            time.sleep(self._delay_after_change)
            self._voltages.append(voltage)
            self._powers.append(self._get_power(self._repetitions))
            self.sigNewDataPoint.emit()
            if self._abort_requested:
                break
        self.module_state.stop()
        self.sigFinished.emit()
        if self._abort_requested:
            self._abort_requested = False
            return
        else:
            return np.array(self._voltages), np.array(self._powers)

# Accessible methods

    def calibrate(self):
        """ Method to call that full calibration procedure """
        result = self._do_sweep()
        if result is None:  # in case of aborted sweep
            return
        voltages, powers = result
        power_max = powers.max()
        powers_normalized = powers / power_max

        i_max = np.argmax(powers)
        y = np.append(np.zeros(1), voltages[0:i_max + 1])
        x = np.append(np.zeros(1), powers_normalized[0:i_max + 1])

        self.output_modifier().update_calibration(np.array([x, y]).transpose())
        self.calibrate_max_from_value(power_max)

    def calibrate_max(self):
        """ Method to calibrate only max power based on measured value """
        self.voltage_output().set_control_value(self.voltage_output().get_control_limit()[1])
        time.sleep(self._delay_after_change)
        power_max = self._get_power(self._repetitions)
        self.calibrate_max_from_value(power_max)

    def calibrate_max_from_value(self, value):
        """ Method to calibrate maximum power based on a value passed as parameter """
        self.control_laser_interfuse().set_max_power(value)
        self.laser().update_laser_power_range()
        self.sigNewMaxPower.emit()

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
        if float(val) != self._time_before_start:
            self.sigParameterChanged.emit()
        self._time_before_start = float(val)

    @property
    def resolution(self):
        return self._resolution

    @resolution.setter
    def resolution(self, val):
        if int(val) != self._resolution:
            self.sigParameterChanged.emit()
        self._resolution = int(val)

    @property
    def delay_after_change(self):
        return self._delay_after_change

    @delay_after_change.setter
    def delay_after_change(self, val):
        if float(val) != self._delay_after_change:
            self.sigParameterChanged.emit()
        self._delay_after_change = float(val)

    @property
    def delay_between_repetitions(self):
        return self._delay_between_repetitions

    @delay_between_repetitions.setter
    def delay_between_repetitions(self, val):
        if float(val) != self._delay_between_repetitions:
            self.sigParameterChanged.emit()
        self._delay_between_repetitions = float(val)

    @property
    def repetitions(self):
        return self._repetitions

    @repetitions.setter
    def repetitions(self, val):
        if int(val) != self._repetitions:
            self.sigParameterChanged.emit()
        self._repetitions = int(val)

    @property
    def power_max(self):
        """ Method used by GUI to get current maximum power known to laser interfuse """
        return self.control_laser_interfuse().get_power_range()[1]

    @property
    def voltages(self):
        return self._voltages

    @property
    def powers(self):
        return self._powers

# save functions

    def draw_figure(self):
        """ Method to draw the curves with matplotlib """
        fig, ax = plt.subplots()
        ax.set_xlabel("Voltage (V)", fontsize=15)
        ax.set_ylabel("Power (W)", fontsize=15)
        ax.tick_params(axis='both', which='major', labelsize=15)
        ax.plot(self.voltages, self.powers, marker='.')
        return fig, ax

    def save(self, save_figure=True):
        """ Method to save the measured data for posterity """
        filepath = self.savelogic().get_path_for_module(module_name='aom_logic')
        data = OrderedDict()
        data['Voltage (V)'] = np.array(self.voltages)
        data['powers'] = np.array(self._powers)
        parameters = OrderedDict()
        parameters['time_before_start'] = self.time_before_start
        parameters['resolution'] = self.resolution
        parameters['delay_after_change'] = self.delay_after_change
        parameters['delay_between_repetitions'] = self.delay_between_repetitions
        parameters['repetitions'] = self.repetitions
        fig, ax = self.draw_figure()

        self.savelogic().save_data(data, filepath=filepath, parameters=parameters, plotfig=fig, delimiter='\t')
        self.log.info('AOM data saved')
