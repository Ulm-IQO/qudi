# -*- coding: utf-8 -*-

"""
This file contains the Qudi Logic module base class.

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

from qtpy import QtCore
import numpy as np

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex
from core.connector import Connector
from core.statusvariable import StatusVar
from scipy.constants import physical_constants


class NVCalculatorLogic(GenericLogic):
    """This is the Logic class for Calculator."""
    _modclass = 'calculatorlogic'
    _modtype = 'logic'

    # declare connectors
    odmr = Connector(interface='ODMRLogic', optional=True)
    pulsed = Connector(interface='PulsedMeasurementLogic', optional=True)

    data_source = 0  # choose the data and fitting source, either from cw-odmr, or pulsedmeasurement 0: "no data_source", 1: "CW_ODMR", 2: "pulsed"
    zero_field_D = StatusVar('ZFS', 2870e6)
    diamond_strain = StatusVar('strain', 0)
    freq1 = StatusVar('freq1', 2800e6)
    freq2 = StatusVar('freq2', 2900e6)
    lac = StatusVar('level_anti_crossing', default=False)
    manual_nmr = StatusVar('manual_NMR', default=False)

    auto_field = 0.0
    manual_field = 0.0

    # Update signals, e.g. for GUI module
    sigFieldaCalUpdated = QtCore.Signal(str, str)
    sigFieldmCalUpdated = QtCore.Signal(str, str)
    sigFieldParamsUpdated = QtCore.Signal(dict)
    sigDataSourceUpdated = QtCore.Signal(int)
    sigManualFieldUpdated = QtCore.Signal(float)
    sigNMRUpdated = QtCore.Signal(list, list)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.threadlock = Mutex()

    def on_activate(self):
        # Get connectors
        self.set_data_source(self.data_source)
        return

    def on_deactivate(self):
        """ """
        pass

    def set_data_source(self, data_source):
        self.data_source = data_source
        if data_source == 0:
            self.sigDataSourceUpdated.emit(0)
        elif data_source == 1:
            self.fit = self.odmr()
            self.sigDataSourceUpdated.emit(1)
        elif data_source == 2:
            self.fit = self.pulsed()
            self.sigDataSourceUpdated.emit(2)
        return

    def set_field_params(self, zfs, e, lac):
        self.zero_field_D = zfs
        self.diamond_strain = e
        self.lac = lac
        param_dict = {'ZFS': self.zero_field_D, 'strain': self.diamond_strain, 'level_anti_crossing': self.lac}
        self.sigFieldParamsUpdated.emit(param_dict)
        return self.zero_field_D, self.diamond_strain, self.lac

    def set_manual_dip_values(self, freq1, freq2):
        self.freq1 = freq1
        self.freq2 = freq2
        param_dict = {'freq1': self.freq1, 'freq2': self.freq2}
        self.sigFieldParamsUpdated.emit(param_dict)
        return self.freq1, self.freq2

    def set_manual_field(self, field):
        self.manual_field = field
        self.sigManualFieldUpdated.emit(field)
        return self.manual_field

    def cal_alignment(self, freq1, freq2):  # from Balasubramanian2008 paper
        '''calculates the alignment theta and the magn. field out of the two
        transition frequencies freq1 and freq2

        Attention: If the field is higher than 1000 Gauss the -1 transition frequency
        has to be inserted as a negative value'''
        D_zerofield = self.zero_field_D / 1e6
        zeroField_E = self.diamond_strain / 1e6

        if self.lac:
            freq1 = -freq1  # In case of level anti-crossing, freq1 transforms to be negative value

        delta = ((7 * D_zerofield ** 3 + 2 * (freq1 + freq2) * (
                2 * (freq1 ** 2 + freq2 ** 2) - 5 * freq1 * freq2 - 9 * zeroField_E ** 2) -
                  3 * D_zerofield * (freq1 ** 2 + freq2 ** 2 - freq1 * freq2 + 9 * zeroField_E ** 2)) /
                 (9 * (freq1 ** 2 + freq2 ** 2 - freq1 * freq2 - D_zerofield ** 2 - 3 * zeroField_E ** 2)))
        angle_factor = delta / D_zerofield - 1e-9
        field_factor = (freq1 ** 2 + freq2 ** 2 - freq1 * freq2 - D_zerofield ** 2) / 3 - zeroField_E ** 2
        if -1 < angle_factor < 1:
            angle = np.arccos(angle_factor) / 2 / (np.pi) * 180
        else:
            angle = np.nan
            self.log.error("Angle calculation failed, probably because of incorrect input ODMR frequencies or "
                           "incorrect zero-field splitting, or strain value has to be considered!")
        if field_factor >= 0:
            beta = np.sqrt(field_factor)
            b_field = beta / physical_constants['Bohr magneton in Hz/T'][0] / \
                      (-1 * physical_constants['electron g factor'][0]) * 1e10
        else:
            b_field = np.nan
            self.log.error("Field calculation failed, probably because of incorrect input ODMR frequencies or "
                           "incorrect zero-field splitting, or strain value has to be considered!")
        return b_field, angle  # in Gauss and degrees

    def manual_dips(self):
        b_field, angle = self.cal_alignment(self.freq1 / 1e6, self.freq2 / 1e6)
        self.sigFieldmCalUpdated.emit('%.3f' % b_field, '%.3f' % angle)
        self.auto_field = b_field
        return

    def auto_dips(self):
        if self.data_source == 0:
            self.log.error("You have not select data source. Select a data source, or try manual Freqs.")
            return
        try:
            if 'g0_center' in self.fit.fc.current_fit_param:
                freq1 = self.fit.fc.current_fit_param['g0_center'].value / 1e6
                freq2 = self.fit.fc.current_fit_param['g1_center'].value / 1e6
            else:
                freq1 = self.fit.fc.current_fit_param['l0_center'].value / 1e6
                freq2 = self.fit.fc.current_fit_param['l1_center'].value / 1e6
            b_field, angle = self.cal_alignment(freq1, freq2)
            self.sigFieldaCalUpdated.emit('%.3f' % b_field, '%.3f' % angle)
            self.auto_field = b_field
        except:
            self.log.error("The NV calculator seems unable to get ODMR dips!"
                           " Only double dip Lorentzian or double dip Gaussian fitting can be recognized by the "
                           "program. Please inspect your fitting method.")

        return

    def set_m_f(self):
        self.manual_nmr = False
        return

    def set_m_t(self):
        self.manual_nmr = True
        self.auto_field = int(self.auto_field)
        return

    def calculate_nmr(self):
        """
        NMR frequency in Hz, XY8 in s
        """
        if self.manual_nmr:
            field = self.manual_field
        else:
            field = self.auto_field

        h1_freq = 42.58 * field * 1e2
        c13_freq = 10.705 * field * 1e2
        n14_freq = 3.077 * field * 1e2
        n15_freq = -4.316 * field * 1e2

        freqs = [h1_freq, c13_freq, n14_freq, n15_freq]

        h1_xy8 = 1 / 2 / h1_freq
        c13_xy8 = 1 / 2 / c13_freq
        n14_xy8 = 1 / 2 / n14_freq
        n15_xy8 = 0.5 / n15_freq

        xy8 = [h1_xy8, c13_xy8, n14_xy8, n15_xy8]
        self.sigNMRUpdated.emit(freqs, xy8)
        return freqs, xy8

    def single_freq(self, freq):
        if self.lac:
            b_field = np.abs(freq / 1e6 + self.zero_field_D / 1e6) / 2.8
        else:
            b_field = np.abs(freq / 1e6 - self.zero_field_D / 1e6) / 2.8
        return b_field
