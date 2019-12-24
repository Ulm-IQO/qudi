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

from collections import OrderedDict
import numpy as np
from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex
from core.module import Connector, ConfigOption, StatusVar
from qtpy import QtCore

class AomLogic(GenericLogic):
    """
    This is the logic for controlling AOM diffraction efficiency
    for power control and Psat
    """
    _modclass = 'aomlogic'
    _modtype = 'logic'

    # declare connectors
    voltagescanner = Connector(interface='VoltageScannerInterface')
    laser = Connector(interface='SimpleLaserInterface')
    savelogic = Connector(interface='SaveLogic')
    fitlogic = Connector(interface='FitLogic')

    psat_updated = QtCore.Signal()
    psat_fit_updated = QtCore.Signal()
    psat_saved = QtCore.Signal()
    aom_updated = QtCore.Signal()
    power_available = QtCore.Signal(bool)
    max_power_update = QtCore.Signal()

    # status vars
    _clock_frequency = StatusVar('clock_frequency', 30)
    #_calibration_voltage = ConfigOption('voltage', missing='error')
    #_calibration_efficiency = ConfigOption('efficiency', missing='error')

    # temporary to avoid restarting qudi
    _calibration_voltage = [0.6, 0.65, .7, .75, .8, .85, .9, .95, 1.0, 1.05, 1.10, 1.15, 1.2, 1.3, 1.4]
    _calibration_efficiency = [.00141, .00554, .01342, .02467, .03881, .05515, .07320, 0.09160, .11123, .12956,
                               .14604, .16094, .17408, .19377, .20777]

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.powers = []
        self.psat_data = []
        self.psat_fit_x = []
        self.psat_fit_y = []
        self.fitted_Isat = 0.0
        self.fitted_Psat = 0.0
        self.fitted_offset = 0.0
        self.psat_fitted = False
        self.psat_collected = False

        #locking for thread safety
        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._voltagescanner = self.get_connector('voltagescanner')
        self._laser = self.get_connector('laser')
        self._save_logic = self.get_connector('savelogic')
        self._fitlogic = self.get_connector('fitlogic')
        config = self.getConfiguration()

        # configure calibration
        self._cal_voltage = config['voltage']
        self._cal_efficiency = config['efficiency']
        self.maximum_efficiency = max(self._cal_efficiency)

        self.set_psat_points()
        self.clear()

        self.psat_updated.connect(self.fit_data)
        # self.laser.sigPower.connect(self.update_aom)


    def on_deactivate(self):
        self.psat_updated.disconnect(self.fit_data)

    def clear(self):
        self.set_psat_points()
        self.psat_data = np.zeros_like(self.powers)
        self.psat_fit_x = np.linspace(0, max(self.powers), 60)
        self.psat_fit_y = np.zeros_like(self.psat_fit_x)
        self.fitted_Isat = 0.0
        self.fitted_Psat = 0.0
        self.fitted_offset = 0.0
        self.psat_fitted = False
        self.psat_colllected = False
        self.psat_updated.emit()
        self.psat_fit_updated.emit()

    def psat_available(self):
        return self.psat_available

    def psat_fit_available(self):
        return self.psat_fit_available

    def efficiency_for_voltage(self, v):
        return np.interp(v, self._cal_voltage, self._cal_efficiency)

    def voltage_for_efficiency(self, e):
        return np.interp(e, self._cal_efficiency, self._cal_voltage, 0.0, np.inf)

    def voltages_for_powers(self, powers):
        laser_power = self._get_laser_power()
        e = [p / laser_power for p in powers]
        return np.interp(e, self._cal_efficiency, self._cal_voltage, 0.0, np.inf)

    def set_power(self, p):
        laser_power = self._get_laser_power()
        efficiency = p/laser_power
        if efficiency > self.maximum_efficiency:
            self.log.warning("Too much power requested, turn the laser up!")
        else:
            self.power = p
            self.update_aom()

    def source_changed(self):
        self.max_power_updated.emit()
        self.update_aom()

    def update_aom(self):
        if self.power > self.current_maximum_power():
            self.power_unavailable.emit()
        else:
            laser_power = self._get_laser_power()
            efficiency = self.power/laser_power
            v = self.voltage_for_efficiency(efficiency)
            self.log.info("Setting AOM voltage {}V efficiency {}".format(v, efficiency))
            self._voltagescanner.set_voltage(v)
            self.aom_updated.emit()

    def _get_laser_power(self):
        return self._laser.laser_power_setpoint

    def get_power(self):
        laser_power = self._get_laser_power()
        v = self._voltagescanner.get_voltage()
        efficiency = self.efficiency_for_voltage(v)
        return laser_power * efficiency

    def current_maximum_power(self):
        laser_power = self._get_laser_power()
        return laser_power * self.maximum_efficiency

    def set_psat_points(self, minimum=0.0, maximum=None, points=100):
        if maximum is None:
            maximum = self.current_maximum_power()*.95
        if maximum > self.current_maximum_power():
            self.log.warn("Maximum power is not available without more laser power")

        self.powers = np.linspace(minimum, maximum, points)

    def run_psat(self):
        if max(self.powers) > self.current_maximum_power():
            self.log.warn("Full range not available for current laser power")
        v = self.voltages_for_powers(self.powers)
        self.log.info("Scanning AOM efficiency with voltages {}".format(v))
        self._voltagescanner.set_up_scanner_clock(clock_frequency=self._clock_frequency)
        self._voltagescanner.set_up_scanner()
        o = self._voltagescanner.scan_voltage(v)
        self._voltagescanner.close_scanner()
        self._voltagescanner.close_scanner_clock()
        d = np.append(o, [])
        self.clear()

        self.psat_data = d
        self.psat_voltages = v

        self.psat_collected = True

        self.psat_updated.emit()

        return self.powers, v, self.psat_data

    def fit_data(self):
        model, param = self._fitlogic.make_hyperbolicsaturation_model()
        param['I_sat'].min = 0
        param['I_sat'].max = 1e7
        param['I_sat'].value = max(self.psat_data) * .7
        param['P_sat'].max = 10.0
        param['P_sat'].min = 0.0
        param['P_sat'].value = 0.0001
        param['slope'].min = 0.0
        param['slope'].value = 1e3
        param['offset'].min = 0.0
        fit = self._fitlogic.make_hyperbolicsaturation_fit(x_axis=self.powers, data=self.psat_data,
                                                           estimator=self._fitlogic.estimate_hyperbolicsaturation,
                                                           add_params=param)
        self.fit = fit
        self.fitted_Psat = fit.best_values['P_sat']
        self.fitted_Isat = fit.best_values['I_sat']
        self.fitted_offset = fit.best_values['offset']
        self.psat_fitted = True
        self.psat_fit_y = model.eval(x=self.psat_fit_x, params=fit.params)

        self.psat_fit_updated.emit()

    def set_to_psat(self):
        if self.fitted_Psat:
            self.set_power(self.fitted_Psat)

    def save_psat(self):
        # File path and name
        filepath = self._save_logic.get_path_for_module(module_name='Psat')

        # We will fill the data OrderedDict to send to savelogic
        data = OrderedDict()

        # Lists for each column of the output file
        power = self.powers
        voltage = self.psat_voltages
        counts = self.psat_data

        data['Power (mW)'] = np.array(power)
        data['Voltage (V)'] = np.array(voltage)
        data['Count rate (/s)'] = np.array(counts)

        self._save_logic.save_data(data, filepath=filepath, filelabel='Psat', fmt=['%.6e', '%.6e', '%.6e'])
        self.log.debug('Psat saved to:\n{0}'.format(filepath))

        self.psat_saved.emit()

        return 0


    def set_clock_frequency(self, clock_frequency):
        """Sets the frequency of the clock

        @param int clock_frequency: desired frequency of the clock

        @return int: error code (0:OK, -1:error)
        """
        self._clock_frequency = int(clock_frequency)
        #checks if scanner is still running
        if self.module_state() == 'locked':
            return -1
        else:
            return 0
