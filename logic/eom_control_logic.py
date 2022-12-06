# -*- coding: utf-8 -*-
"""
This file contains the QuDi GUI module to operate a EOM regulation.
The aim of the program is to use the data of the pure laser signal from
the pulsed measurement to readjust the EOM via an analog output voltage
(compensation of the DC drift). To do this, the voltage at which
the entire laser signal (of the slow counter) is blocked must first
be found. Then the voltage is adjusted during the running pulse
sequence by the data of the pulsed measurement.


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

# ToDO deactivate schreiben
# ToDo Labor: testen ob record length richtig übertragen wird und ob speichern geht, und ob Pulser_on ein problem ist, wenn die messung bereits läuft


from qtpy import QtCore

import time
from datetime import timedelta
import numpy as np
import matplotlib.pyplot as plt
import math
import datetime
from scipy.stats import norm  # To fit gaussian average to data
from collections import OrderedDict
import threading
from random import *
from core.configoption import ConfigOption
from core.connector import Connector
from core.statusvariable import StatusVar
from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex
from scipy.optimize import curve_fit as cf


class EOMControlLogic(GenericLogic):
    '''
    This logic trys to lock the transmission of an electro-optical modulator by changing
    its bias voltage in order to switch a laser continously on/off.

    It is intended to first sweep the bias voltage from bias_voltage_min to bias_voltage_max
    in order to sample the whole transmission function for EOM parameters like Vpi and V0,
    i.e. the periodicity voltage and minimum voltage.

    For the control of the transmission, a process value, namely the contrast of on/off, is
    continously calculated by fetching data from the fastcounter as well as meta data about the
    pulse sequence from pulsed_measurement.

    The control value (bias_voltage) is then altered to maximize the process_value.

    eom_regulation_logic:
        module.Class: 'eom_control_logic.EOMControlLogic'
        bias_voltage_min: -5
        bias_voltage_step_min: 0.01
        bias_voltage_max: 5
        eom_pulse_channel: 'd_ch1'

        connect:
            fastcounter: 'fastcounter'
            pulsedmeasurementlogic: 'pulsedmeasurement'
            counterlogic: 'counter'
            analog_output: 'confocalogic'
            savelogic: 'save'
    '''

    _bias_voltage_min = ConfigOption('bias_voltage_min', missing='error')
    _bias_voltage_step_min = ConfigOption('bias_voltage_step_min', missing='error', default=0.01)
    _bias_voltage_max = ConfigOption('bias_voltage_max', missing='error')
    _eom_pulse_channel = ConfigOption('eom_pulse_channel', missing='error', default='d_ch1')

    fastcounter = Connector(interface='FastCounterInterface')
    pulsedmeasurementlogic = Connector(interface='PulsedMeasurementLogic')
    sequencegeneratorlogic = Connector(interface='SequenceGeneratorLogic')
    counterlogic = Connector(interface='CounterLogic')
    # analog_output = Connector(interface='AnalogueOutputInterface')
    analog_output = Connector(interface='ConfocalLogic')
    savelogic = Connector(interface='SaveLogic')

    sigDoNextControlLoop = QtCore.Signal()

    sigUpdateProcessValueTimeSeries = QtCore.Signal(list, list)
    sigUpdateControlValueTimeSeries = QtCore.Signal(list, list)
    sigUpdateControlValue = QtCore.Signal(float)
    sigUpdateLaserData = QtCore.Signal(np.ndarray, np.ndarray)
    sigUpdateControlParams = QtCore.Signal(str, str, str, str)
    sigUpdateVpi = QtCore.Signal(float, float)
    sigUpdateSweepPlot = QtCore.Signal(np.ndarray, np.ndarray, np.ndarray)

    sigChangeSweepState = QtCore.Signal()
    sigSweepStateChanged = QtCore.Signal(bool)

    sigStartControl = QtCore.Signal(int)
    sigPauseControl = QtCore.Signal(int)

    def __init__(self, config, **kwargs):

        super().__init__(config=config, **kwargs)

        self.control_timer = QtCore.QTimer()

        self.current_laser_hist = np.array([])
        self.previous_laser_hist = np.array([])

        self.start_state = 0
        self.pause_state = 0
        self.sweep_state = 0

        self.control_timedeltas = list()
        self.contrasts = list()
        self.bias_voltages = list()
        self.min_voltage = 0
        self.counter_data = list()

    def on_activate(self):
        self._fast_counter = self.fastcounter()
        self._pulsed_measurement_logic = self.pulsedmeasurementlogic()
        self._sequence_generation_logic = self.sequencegeneratorlogic()
        self._save_logic = self.savelogic()
        self._counter_logic = self.counterlogic()

        # self._analog_output.set_up_analogue_output(['cavity_scanner'])

        self.bias_voltage_step = self._bias_voltage_step_min

        self.extremum = 0
        self.sweep_voltage_start = 0
        self.sweep_voltage_stop = self._bias_voltage_max
        self.sweep_voltage_step = self._bias_voltage_step_min*10
        self.sweep_timestep = 50

        self._control_timestep_min = round(1000 * self._pulsed_measurement_logic.timer_interval)
        self._control_timestep = self._control_timestep_min
        self.num_points = 50
        self.resolution = 1
        self.num_diff_points = 6
        self.inverting_threshold = 5e-4

        self.sigDoNextControlLoop.connect(self.doControlLoop, QtCore.Qt.QueuedConnection)
        self.sigChangeSweepState.connect(self.changeSweepState, QtCore.Qt.QueuedConnection)

        self.sigStartControl.connect(self.startControlLoop, QtCore.Qt.QueuedConnection)
        self.sigPauseControl.connect(self.pauseControlLoop, QtCore.Qt.QueuedConnection)

        self.changeBiasVoltage(0)
        self._counter_logic.startCount()

    def on_deactivate(self):
        self.changeBiasVoltage(0)

        self._counter_logic.stopCount()
        # self._ put.close_analogue_output('cavity_scanner')

        self.start_state = 0
        self.pause_state = 0
        self.stopControlLoop()

        self.sweep_state = 0
        self.stopSweep()

    def startControlLoop(self, state):
        self.start_state = state
        if self.start_state > 0:
            self._pulsed_measurement_logic.pulse_generator_on()
            self._pulsed_measurement_logic.toggle_pulsed_measurement(True)
            self.initControlLoop()
        else:
            self._pulsed_measurement_logic.pulse_generator_off()
            self._pulsed_measurement_logic.toggle_pulsed_measurement(False)
            self.stopControlLoop()            

    def pauseControlLoop(self, state):
        self.pause_state = state
        if self.pause_state > 0:
            self._pulsed_measurement_logic.toggle_measurement_pause(True)
        else:
            self._pulsed_measurement_logic.toggle_measurement_pause(False)
            self.startControlLoop()

    def initControlLoop(self):
        self.start_time = time.time()

        self.control_timedeltas = [0]
        self.bias_voltages = [self.bias_voltages[-1]]
        self.contrasts = [1.]
        self.contrast_diffs = []

        self.current_laser_hist = np.array([])
        self.previous_laser_hist = np.array([])

        self.extractBinWidth()
        print("Start to control at V: ", self.bias_voltages[-1])
        QtCore.QTimer().singleShot(2*self.control_timestep, self.doControlLoop)

    def doControlLoop(self):
        """
        Continously fetch data from fast counter control histrogram.
        Subsequent binning of the histogram reduces the amount of data points and hence should increase processing speed.
        The binned histrogram is then used to calculate the contrast from the previous and current
        histogram and stored in the process_value list.
        The contrast is subsequently used to calculate a bias_voltage step which is applied
        to the EOM.
        Finally, process_value and control_value timeseries as well as laser pulses are
        updated in the gui.
        """

        if self.start_state and not self.pause_state:

            # Bin the fast counter control histogram in order to increase processing speed
            try:
                self.current_laser_hist = self.binnedHistogram(
                    data=self._fast_counter.get_control_data_hist()
                )
            except AttributeError:
                self.log.error("The fastcounter you provided does not support a control data histogram."
                               "Aborting control sequence.")
                return -1

            if not self.current_laser_hist.any():
                self.log.warning("Fastcounter recieved only zeros. Aborting control.")
                self.startControlLoop(False)
                return -1

            contrast = self.getContrast(self.previous_laser_hist, self.current_laser_hist)
            if contrast >= 0:
                self.contrasts.append(contrast)
                if len(self.contrasts) > 60:
                    self.contrasts.pop(0)
                self.previous_laser_hist = self.current_laser_hist
            else:
                self.log.error("Can not estimate laser contrast. Aborting control sequence.")
                self.startControlLoop(False)
                return -1

            bias_voltage = self.doStep()
            if bias_voltage <= self._bias_voltage_min or bias_voltage >= self._bias_voltage_max:
                self.log.warning("Reaching boundaries of EOM. Trying to relock")
                self.stopControlLoop()
                self.relock()
                return -1

            if self.changeBiasVoltage(bias_voltage) >= 0:
                self.control_timedeltas.append(timedelta(seconds=time.time() - self.start_time).seconds)
                if len(self.control_timedeltas) > 60:
                    self.control_timedeltas.pop(0)

                # Update plot of laser pulses, control (voltage @EOM) and process (contrast) data
                self.updatePlots()

                # Reiterate control loop
                QtCore.QTimer().singleShot(self.control_timestep, self.sigDoNextControlLoop.emit)
            else:
                self.log.error("Cannot write analog ouput. Aborting control sequence.")
                return -1

    def doStep(self):
        """
            Check if the average differences of (num_diff_points) contrast values is smaller
            than some (inverting_threshold) given threshold value.
            If this is true, change the voltage direction

            contrasts:          Current list of contrast values
            contrast_diffs      Current differences of contrast values

            :return
            bias_voltage:       Updated bias voltage after performing a control loop
        """
        if np.where(np.array(self.contrasts) > 0)[0].size > 1:

            self.contrast_diffs.append(self.contrasts[-1] - self.contrasts[-2])
            if len(self.contrast_diffs) > self.num_diff_points:
                if np.mean(np.array(self.contrast_diffs[-self.num_diff_points:])) < -self.inverting_threshold:
                    self.bias_voltage_step = -self.bias_voltage_step
                    self.bias_voltages[-1] += self.num_diff_points * self.bias_voltage_step
                    self.contrast_diffs = []

        return self.bias_voltages[-1] + self.bias_voltage_step

    def updatePlots(self):
        self.sigUpdateProcessValueTimeSeries.emit(
            self.control_timedeltas,
            self.contrasts
        )
        self.sigUpdateControlValueTimeSeries.emit(
            self.control_timedeltas,
            self.bias_voltages
        )
        self.sigUpdateLaserData.emit(
            self.binwidth * np.arange(0, len(self.current_laser_hist), 1),
            self.current_laser_hist
        )

    def stopControlLoop(self):
        self.start_state = 0
        self.pause_state = 0

    def relock(self):
        self.log.warning("Implement relock.")
        pass

    def changeBiasVoltage(self, bias_voltage):
        """
            Check if bias voltage is between boundaries given as config options.
            Then write the bias_voltage to the analog output and save it in the timeseries
            list as a controlvalue.

        :param bias_voltage: Bias voltage at EOM.
        :return:
        """
        if self._bias_voltage_min <= bias_voltage and bias_voltage <= self._bias_voltage_max:
            try:
                if not self.analog_output().set_position('Logic', z=bias_voltage*1e-6): #pretending to be in "um"
                    self.bias_voltages.append(bias_voltage)
                    if len(self.bias_voltages) > 60:
                        self.bias_voltages.pop(0)
                    self.sigUpdateControlValue.emit(bias_voltage)

                return 0

            except Exception as e:
                self.log.error(e)
                return -1
        else:
            self.log.warning(
                "Bias voltage {} limits of {},{} exceeded.".format(
                    bias_voltage, self._bias_voltage_min, self._bias_voltage_max)
            )
            return -1

    def extractBinWidth(self):
        pulse_widths = []
        self.asset = self._sequence_generation_logic.loaded_asset[0]
        if self.asset:
            ensemble = self._sequence_generation_logic.get_ensemble(self.asset)
            for block_name, num_iterations in ensemble.block_list:
                pulse_block = self._sequence_generation_logic.get_block(block_name)
                for element in pulse_block.get_dict_representation()['element_list']:
                    digital_channels = element['digital_high']
                    if digital_channels[self._eom_pulse_channel]:
                        pulse_widths.append(element['init_length_s'])

            self.binwidth = max(((min(pulse_widths) / self.num_points) // self._fast_counter.get_binwidth()) * self._fast_counter.get_binwidth(),
                                self._fast_counter.get_binwidth())
            self.sigUpdateControlParams.emit(self.asset, '', str(self.binwidth * 1e9), str(self._fast_counter.get_binwidth()*1e9))
        else:
            self.binwidth = 1e-9

    def gated_eom_pulses(self, data):
        self.gate_mask = np.zeros_like(data)
        self.tstart = 0
        if self.asset:
            ensemble = self._sequence_generation_logic.get_ensemble(self.asset)
            for block_name, num_iterations in ensemble.block_list:
                pulse_block = self._sequence_generation_logic.get_block(block_name)
                for element in pulse_block.get_dict_representation()['element_list']:
                    if not element['digital_high'][self._eom_pulse_channel]:
                        self.tstart += element['init_length_s']
                    else:
                        self.gate_mask[int(np.floor(self.tstart/self.binwidth)): int(np.ceil( (self.tstart + element['init_length_s'])/self.binwidth) )] = 1
            return data[self.gate_mask]
        else:
            self.log.warning("Cannot gate, since no pulse block ensemble can be found")

    def getContrast(self, previous_laser_hist, current_laser_hist):
        """
            The contrast is calculated by first taking the difference of two subsequent
            laser pulse sequences.

        :param previous_laser_hist:
        :param current_laser_hist:
        :return:
        """
        if not previous_laser_hist.any() or not current_laser_hist.any():
            contrast = 0
        else:
            laser_hist_diff = current_laser_hist - previous_laser_hist

            if laser_hist_diff.any():
                pulse_max = sorted(laser_hist_diff)[-2]

                laser_max_avg = np.mean(laser_hist_diff[np.argwhere(laser_hist_diff > pulse_max / 2).flatten()])
                laser_min_avg = np.mean(laser_hist_diff[np.argwhere(laser_hist_diff < pulse_max / 7).flatten()])

                contrast = 1 - (laser_min_avg / laser_max_avg)
            else:
                contrast = 0
        return contrast

    def binnedHistogram(self, data):
        resolution = int(max(self.binwidth // self._fast_counter.get_binwidth(), 1))
        ens_length, ens_bins, ens_lasers = self._sequence_generation_logic.get_ensemble_info(self.asset)
        data_trimmed = data[:int(np.ceil(ens_length / (self._fast_counter.get_binwidth() * len(data))) * len(data))]
        # data_gated = self.gated_eom_pulses(data_trimmed)

        binned_hist = np.zeros(len(data_trimmed) // resolution)
        for i in range(binned_hist.size):
            binned_hist[i] = np.sum(data_trimmed[i * resolution:(i + 1) * resolution])

        self.sigUpdateControlParams.emit(self.asset, str(binned_hist.size), str(self.binwidth*1e9), str(self._fast_counter.get_binwidth()*1e9))
        return binned_hist

    def changeSweepState(self):
        self.sweep_state = not self.sweep_state
        self.sigSweepStateChanged.emit(self.sweep_state)
        if self.sweep_state:
            self.startSweep()
        else:
            self.stopSweep()

    def startSweep(self):
        self.changeBiasVoltage(self.sweep_voltage_start)
        self.counter_data = []
        self.doSweepLoop()

    def doSweepLoop(self):
        if self.sweep_state and self.bias_voltages[-1] + self.sweep_voltage_step <= self.sweep_voltage_stop:
            if self.changeBiasVoltage(self.bias_voltages[-1] + self.sweep_voltage_step) < 0:
                self.changeSweepState()
                self.log.warning("Something went wront with changing the bias voltage. Aborting the sweep.")
            else:
               self.counter_data.append(self._counter_logic.countdata_smoothed.flatten()[-1])
               QtCore.QTimer().singleShot(self.sweep_timestep, self.doSweepLoop)
        else:
            try:
                V = np.linspace(self.sweep_voltage_start, self.sweep_voltage_stop, len(self.counter_data))
                popt, pcov = cf(Transmission, V, self.counter_data)
                Vpi, V0, T0, Tmin = popt
                Vpi, V0 = round(np.abs(Vpi), 2), round(V0, 2)
                V0 = min(V0%Vpi, V0%Vpi-Vpi)
                self.log.info(f"Vpi estimated {Vpi} with minimum voltage at {V0}")
                self.sigUpdateVpi.emit(Vpi, V0)
                self.sigUpdateSweepPlot.emit(V, np.array(self.counter_data), Transmission(V, *popt))
            except Exception:
                self.log.warning("Could not fit EOM transmission function. Try to increase sweep voltage limits.")
                V0 = 0
                Vpi = 1
            print(V0, Vpi)
            self.min_voltage = V0
            self.changeBiasVoltage(self.min_voltage)
            self.changeSweepState()

    def stopSweep(self):
        self.sweep_state = False

    def save_data(self, postfix='', save_figure=True):
        parameters = OrderedDict()
        parameters['Start counting time'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss',
                                                          time.localtime(self.start_time))
        parameters['Stop counting time'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss',
                                                         time.localtime(time.time()))

        parameters['Control Timestep (ms)'] = self.control_timestep
        parameters['Bias Voltage Step (mV)'] = self.bias_voltage_step
        parameters['Laser Pulses Bin Width (s)'] = self.binwidth
        parameters['Faser Counter Bin Width (s)'] = self._fast_counter.get_binwidth()
        parameters['Pulse Sequence Name'] = self.asset

        self._save_logic.save_data(
            {'Times (s)': self.binwidth*np.arange(0, len(self.current_laser_hist), 1), 'Clicks': self.current_laser_hist},
            filepath=self._save_logic.get_path_for_module('PulsedMeasurement'), parameters=parameters,
            filelabel='EOM Laser Pulses', plotfig=None, delimiter='\t')

    @property
    def control_timestep(self):
        return self._control_timestep

    @control_timestep.setter
    def control_timestep(self, val):
        if val < self._control_timestep_min:
            self.log.error(f'Increased control_timestep from {val} to the minimum of '
                           f'{self._pulsed_measurement_logic.timer_interval * 1000} given by pulsed measurement.')
            self._control_timestep = self._pulsed_measurement_logic.timer_interval * 1000
        else:
            self._control_timestep = val

def Transmission(V, Vpi, V0, T0, Tmin):
    return T0 * np.sin(np.pi*(V-V0)/Vpi)**2 + Tmin