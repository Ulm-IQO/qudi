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

#ToDO deactivate schreiben
#ToDo Labor: testen ob record length richtig übertragen wird und ob speichern geht, und ob Pulser_on ein problem ist, wenn die messung bereits läuft


from qtpy import QtCore

import time
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



class EOMRegulationLogic(GenericLogic):  # Todo connect to generic logic
    """
    This is the Logic class for software driven driven EOM regulation.
    """
    _modclass = 'EOMRegulationLogic'
    _modtype = 'logic'

    pulsedmeasurementlogic = Connector(interface='PulsedMeasurementLogic')
    pulsedmeasurementlogic2 = Connector(interface='PulsedMeasurementLogic')

    counterlogic = Connector(interface='CounterLogic')
    confocallogic = Connector(interface='ConfocalLogic')


    #declare connectors, Qt.Signal
    sigChangeAnalogOutputVoltage = QtCore.Signal(float)
    sigVoltageUpdate = QtCore.Signal(float)
    sigRegulationPlotUpdated = QtCore.Signal(np.ndarray, np.ndarray)
    sigMinimumRepeat = QtCore.Signal()
    sigRegulationRepeat = QtCore.Signal()
    sigChangeButton = QtCore.Signal(str)
    sigsuppressionUpdate = QtCore.Signal(float)

    # config opts
    _voltage_min = ConfigOption('voltage_min', missing='error')
    _voltage_max = ConfigOption('voltage_max', missing='error')
    _fc_binwidth = ConfigOption('fc_binwidth', missing='error')

    def __init__(self, config, **kwargs):

        super().__init__(config=config, **kwargs)

        self._start_voltage = 0
        self._start_voltage = 0
        self._rough_voltage_step = 0.05
        self._fine_voltage_step = 0.01
        self._fine_step_counts = 500
        self._actual_voltage = 0
        self._regulation_voltage_step = 0.01
        self._regulation_interval = 5
        self._record_length = 3e-6
        self._neglect_0 = True
        self.stopRequested_regulation = True
        self.stopRequested_minimum = True
        self.count_alt = self._fine_step_counts + 1


    def on_activate(self):

        # connectors
        self.sigMinimumRepeat.connect(self.find_minimum_loop, QtCore.Qt.QueuedConnection)
        self.sigRegulationRepeat.connect(self.regulation_loop, QtCore.Qt.QueuedConnection)
        self.sigChangeAnalogOutputVoltage.connect(self.change_analogue_output_voltage, QtCore.Qt.QueuedConnection)
        self.pulsedmeasurementlogic().sigMeasurementStatusUpdated.connect(self.change_pulsedmeasurement_status)
        self.pulsedmeasurementlogic2().sigMeasurementStatusUpdated.connect(self.change_pulsedmeasurement2_status)



    def on_deactivate(self):
        self.stopRequested_regulation = True
        self.stopRequested_minimum = True
        self.change_analogue_output_voltage(0)
        self.sigMinimumRepeat.disconnect()
        self.sigRegulationRepeat.disconnect()
        pass

############################## find minimum #############################

    def stop_find_minimum(self):
        """ Stop Find minimum
             """
        self.stopRequested_minimum = True

    def initialise_find_minimum(self):
        """Starts Find minimum
        """

        if self.stopRequested_minimum:
            self.log.manager.disable = 31  # IGNORES WARNINGS, INFO and DEBUG
            self.counterlogic().startCount()
            self.pulsedmeasurementlogic().stop_pulsed_measurement()
            self.pulsedmeasurementlogic().pulse_generator_off()
            self.log.manager.disable = 0  # DOES NOT IGNORES WARNINGS, INFO and DEBUG ANYMORE

            self.sigChangeButton.emit('md')
            self.stopRequested_minimum = False
            self._actual_voltage = self._start_voltage
            self.count_alt = self._fine_step_counts + 1
            QtCore.QTimer().singleShot(500, self.sigMinimumRepeat.emit)
        else:
            self.log.warning("Find Minimum already running, call ignored")



    def find_minimum_loop(self):
        """ This method gets the count data from the counterlogic.

        It runs repeatedly in the logic module event loop by being connected
        to sigMinimumRepeat and emitting sigMinimumRepeat through a queued connection.
        """
        #stops loop
        if self.stopRequested_minimum:
            self.sigChangeButton.emit('me')
        # calls loop function again
        else:
            self.find_minimum_function()
            QtCore.QTimer().singleShot(250, self.sigMinimumRepeat.emit)


    def find_minimum_function(self):
        """ This function is called during the find_minimum_loop and determines the voltages, where the eom blocks.
            First the function increases the voltage until the count rate is smaller than the parameter
            self._fine_step_counts (in the beginning, the count rate will increase till it reaches the first maximum)
            When this parameter count rate is reached, the voltage increase stops as soon as the countrate increases
            again.
             """

        if self.count_alt < self._fine_step_counts:

            count_neu = np.mean(np.concatenate(self.counterlogic().countdata)[-5:-1])
            if count_neu > self.count_alt:
                self._actual_voltage = self._actual_voltage - self._regulation_voltage_step
                self.change_analogue_output_voltage(self._actual_voltage)
                self.stopRequested_minimum = True
            else:
                self.count_alt = count_neu;
                self._actual_voltage = self._actual_voltage + self._fine_voltage_step
                self.change_analogue_output_voltage(self._actual_voltage)

        else:
            self.count_alt =  np.mean(np.concatenate(self.counterlogic().countdata)[-5:-1])
            if self.count_alt < self._fine_step_counts:
                self._actual_voltage = self._actual_voltage + self._fine_voltage_step
                self.change_analogue_output_voltage(self._actual_voltage)
            else:
                self._actual_voltage = self._actual_voltage + self._rough_voltage_step
                self.change_analogue_output_voltage(self._actual_voltage)

#################################### regulation ############################################

    def stop_regulation(self):
        """ Stops Regulation
             """
        self.stopRequested_regulation = True

    def initialise_regulation(self):
        """ Starts regulation
        """

        if self.stopRequested_regulation:
            self.sigChangeButton.emit('rd')

            #self.log.manager.disable = 31  # IGNORES WARNINGS, INFO and DEBUG
            self.pulsedmeasurementlogic().pulse_generator_on()
            self.pulsedmeasurementlogic2().toggle_pulsed_measurement('True')
            self.pulsedmeasurementlogic2().set_fast_counter_settings(dict(record_length=self._record_length,
                                                                          bin_width=self._fc_binwidth))
            #self.log.manager.disable = 0  # DOES NOT IGNORES WARNINGS, INFO and DEBUG ANYMORE
            self.suppression_old = 0
            self.regulation_direction = "up"
            self.stopRequested_regulation = False
            try:
                QtCore.QTimer().singleShot(1000, self.start_regulation_loop())
            except:
                pass
        else:
            self.log.warning("Regulation already running, call ignored")

    def start_regulation_loop(self):
        self.pulse_old = self.pulsedmeasurementlogic2().fastcounter().get_data_trace()[0]
        QtCore.QTimer().singleShot(5000, self.sigRegulationRepeat.emit)


    def regulation_loop(self):
        """ This method gets the pulsed data from the pulsedmeasurementlogic2 and increases the pulse suppression.
            It runs repeatedly in the logic module event loop by being connected
                to sigRegulationRepeat and emitting sigRegulationRepeat through a queued connection.
                """
        #stops the loop
        if self.stopRequested_regulation:
            self.pulsedmeasurementlogic2().stop_pulsed_measurement()
            QtCore.QTimer().singleShot(self._regulation_interval * 1000, self.sigChangeButton.emit('re'))
        # calls loop function again
        else:
            pulse_new = self.pulsedmeasurementlogic2().fastcounter().get_data_trace()[0]
            #pulse_new = self.fastcounter().get_data_trace()[0][0]
            suppression_new = self.suppression(pulse_new - self.pulse_old)
            if suppression_new > self.suppression_old:
                self.change_voltage_in_direction()
            else:
                print(self.regulation_direction)
                self.change_voltage_direction()
                self.change_voltage_in_direction()

            self.pulse_old = pulse_new
            self.sigsuppressionUpdate.emit(suppression_new)
            print(suppression_new)
            self.suppression_old = suppression_new
            # calls loop function again
            QtCore.QTimer().singleShot(self._regulation_interval*1000, self.sigRegulationRepeat.emit)

    def change_voltage_direction(self):
        """ switches self.regulation_direction between "up" and "down"
                        """
        if self.regulation_direction == "up":
            self.regulation_direction = "down"
        else:
            self.regulation_direction = "up"


    def change_voltage_in_direction(self):
        """ self.regulation_direction = "up" increases voltage; "down" decreases voltage; updates voltage in Gui
                        """
        if self.regulation_direction == "up":
            self._actual_voltage = self._actual_voltage + self._regulation_voltage_step
        if self.regulation_direction  == "down":
            self._actual_voltage = self._actual_voltage - self._regulation_voltage_step
        self.change_analogue_output_voltage(self._actual_voltage)


    def suppression(self, pulse_data_diff):
        """ calculates the suppression of a laser signal and updates the plot
                              """
        #deletes 0 at the end of the sequence resulting from too long recording times
        if self._neglect_0 :
            pulse_data_diff = np.trim_zeros(pulse_data_diff, 'b')

        self.sigRegulationPlotUpdated.emit(np.linspace(0, self._record_length, len(pulse_data_diff)), pulse_data_diff)
        pulse_max = sorted(pulse_data_diff)[-2]
        pulse_min = sorted(pulse_data_diff)[5]
        pulse_max_data = [k for k, l in enumerate(pulse_data_diff) if l > (pulse_max / 2)]
        pulse_max_average = np.mean(pulse_data_diff[pulse_max_data])
        pulse_min_data = [u for u, v in enumerate(pulse_data_diff) if v < (pulse_max / 7)]
        pulse_min_average = np.mean(pulse_data_diff[pulse_min_data])
        pulse_suppression = 1 - (pulse_min_average / pulse_max_average)
        return pulse_suppression


    def save_data(self):
        """ Saves the laser signal data
                                     """
        self.pulsedmeasurementlogic2().save_measurement_data()

    def change_analogue_output_voltage(self, output_value):
        """ Changes the output voltage that regulates the eom
                                     """
        if self._voltage_min <= output_value <= self._voltage_max:
            self.sigVoltageUpdate.emit(output_value)
            self.confocallogic().set_position('Logic', a=output_value)
        else:
            self.stopRequested_minimum = True
            self.stopRequested_regulation = True
            self.log.error(f"Voltage exceeds the limit from the config file: {self._voltage_min} - {self._voltage_max} V")

    def change_pulsedmeasurement_status(self,is_running, is_paused):
        """ Stops the operation, when pulsedmeasurement was started or stopped externally
                             """

        if self.stopRequested_regulation and self.stopRequested_minimum:
            pass
        elif is_running:
            pass
        elif not is_running:
            self.pulsedmeasurementlogic().pulse_generator_on()
        else:
            self.stop_find_minimum()
            self.stop_regulation()
            self.log.warning("Pulsed Measurement was stopped or started during regulation. Regulation stopped")

    def change_pulsedmeasurement2_status(self,is_running, is_paused):
        """ Stops the operation, when pulsedmeasurement was started or stopped externally
                             """
        if self.stopRequested_regulation and self.stopRequested_minimum:
            pass
        else:
            self.stop_find_minimum()
            self.stop_regulation()
            self.log.warning("Pulsed Measurement 2 was stopped during regulation. Regulation stopped")
