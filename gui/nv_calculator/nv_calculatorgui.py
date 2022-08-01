# -*- coding: utf-8 -*-
"""
This file contains the Qudi console GUI module.

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

import os

from core.module import Connector
from gui.guibase import GUIBase
from qtpy import QtWidgets
from qtpy import QtCore
from qtpy import uic


class NVCalculatorGui(GUIBase):
    _modclass = 'NVCalculatorGui'
    _modtype = 'gui'
    ## declare connectors
    nv_calculatorlogic = Connector(interface='NVCalculatorLogic')

    sigCalParamsChanged = QtCore.Signal(float, float, bool)
    sigManualDipsChanged = QtCore.Signal(float, float)
    sigMaualFieldChanged = QtCore.Signal(float)
    sigManualNMRChanged = QtCore.Signal(bool)

    def on_activate(self):
        """Create all UI objects and show the window.
        """
        self._mw = NVCalculatorMainWindow()
        self.calculator = self.nv_calculatorlogic()

        ########################################################################
        #              Configuration of the display Widgets                    #
        ########################################################################
        self._mw.zfs_DoubleSpinBox.setValue(self.calculator.zero_field_D)
        self._mw.e_DoubleSpinBox.setValue(self.calculator.diamond_strain)
        self._mw.freq1_DoubleSpinBox.setValue(self.calculator.freq1)
        self._mw.freq2_DoubleSpinBox.setValue(self.calculator.freq2)
        self._mw.lac_CheckBox.setChecked(self.calculator.lac)
        # fit source setting
        self._mw.fit_source_comboBox.addItem('no source')
        self._mw.fit_source_comboBox.addItem('CW_ODMR')
        self._mw.fit_source_comboBox.addItem('pulsed')
        self._mw.fit_source_comboBox.activated.connect(self.update_source)
        ########################################################################
        #                       Connect signals                                #
        ########################################################################
        # Internal user input changed signals
        self._mw.zfs_DoubleSpinBox.editingFinished.connect(self.change_field_param)
        self._mw.e_DoubleSpinBox.editingFinished.connect(self.change_field_param)
        self._mw.lac_CheckBox.stateChanged.connect(self.change_field_param)
        self._mw.freq1_DoubleSpinBox.editingFinished.connect(self.change_dip_values)
        self._mw.freq2_DoubleSpinBox.editingFinished.connect(self.change_dip_values)
        self._mw.manual_field_DoubleSpinBox.editingFinished.connect(self.change_manual_field)

        # Internal trigger signals
        self._mw.a_field_PushButton.clicked.connect(self.calculator.auto_dips, QtCore.Qt.QueuedConnection)
        self._mw.m_field_PushButton.clicked.connect(self.calculator.manual_dips, QtCore.Qt.QueuedConnection)

        self._mw.nmr_auto_PushButton.clicked.connect(self.auto_calculate_nmr, QtCore.Qt.QueuedConnection)
        self._mw.nmr_manual_PushButton.clicked.connect(self.manual_calculate_nmr, QtCore.Qt.QueuedConnection)
        self._mw.odmr1nmr_manual_PushButton.clicked.connect(self.use_single_freq, QtCore.Qt.QueuedConnection)

        # send signals to logic
        self.sigCalParamsChanged.connect(self.calculator.set_field_params, QtCore.Qt.QueuedConnection)
        self.sigManualDipsChanged.connect(self.calculator.set_manual_dip_values, QtCore.Qt.QueuedConnection)
        self.sigMaualFieldChanged.connect(self.calculator.set_manual_field, QtCore.Qt.QueuedConnection)

        # Update signals coming from logic
        self.calculator.sigFieldaCalUpdated.connect(self.a_update_field, QtCore.Qt.QueuedConnection)
        self.calculator.sigFieldmCalUpdated.connect(self.m_update_field, QtCore.Qt.QueuedConnection)
        self.calculator.sigFieldParamsUpdated.connect(self.update_field_params, QtCore.Qt.QueuedConnection)
        self.calculator.sigDataSourceUpdated.connect(self.update_source, QtCore.Qt.QueuedConnection)
        self.calculator.sigManualFieldUpdated.connect(self.update_manual_field, QtCore.Qt.QueuedConnection)
        self.calculator.sigNMRUpdated.connect(self.update_nmr, QtCore.Qt.QueuedConnection)

        self.restoreWindowPos(self._mw)
        self.show()

    def show(self):
        """Make sure that the window is visible and at the top.
        """
        self._mw.show()

    def on_deactivate(self):
        """ Hide window and stop ipython console.
        """
        self.saveWindowPos(self._mw)
        self.sigCalParamsChanged.disconnect()
        self.sigManualDipsChanged.disconnect()
        self._mw.a_field_PushButton.clicked.disconnect()
        self._mw.m_field_PushButton.clicked.disconnect()
        self._mw.zfs_DoubleSpinBox.editingFinished.disconnect()
        self._mw.e_DoubleSpinBox.editingFinished.disconnect()
        self._mw.freq1_DoubleSpinBox.editingFinished.disconnect()
        self._mw.freq2_DoubleSpinBox.editingFinished.disconnect()
        self._mw.close()

    def a_update_field(self, b_field, angle):
        """Update calculated magnetic field and the NV-B angle, from a 2-dip fitting"""
        self._mw.a_field_alignment_DisplayWidget.setPlainText(
            'Magnetic field: {0} Gauss\nNV-B angle: {1} degree'.format(b_field, angle))
        return

    def m_update_field(self, b_field, angle):
        """Update calculated magnetic field and the NV-B angle, from user input values"""
        self._mw.m_field_alignment_DisplayWidget.setPlainText(
            'Magnetic field: {0} Gauss\nNV-B angle: {1} degree'.format(b_field, angle))
        return

    def update_source(self, index):
        self._mw.fit_source_comboBox.itemData(index, QtCore.Qt.UserRole)
        self.calculator.set_data_source(index)
        return

    def update_field_params(self, param_dict):
        param = param_dict.get('ZFS')
        if param is not None:
            self._mw.zfs_DoubleSpinBox.blockSignals(True)
            self._mw.zfs_DoubleSpinBox.setValue(param)
            self._mw.zfs_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('strain')
        if param is not None:
            self._mw.e_DoubleSpinBox.blockSignals(True)
            self._mw.e_DoubleSpinBox.setValue(param)
            self._mw.e_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('freq1')
        if param is not None:
            self._mw.freq1_DoubleSpinBox.blockSignals(True)
            self._mw.freq1_DoubleSpinBox.setValue(param)
            self._mw.freq1_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('freq2')
        if param is not None:
            self._mw.freq2_DoubleSpinBox.blockSignals(True)
            self._mw.freq2_DoubleSpinBox.setValue(param)
            self._mw.freq2_DoubleSpinBox.blockSignals(False)
        return

    def update_manual_field(self, field):
        self._mw.manual_field_DoubleSpinBox.setValue(field)
        return

    def update_nmr(self, freqs, xy8):
        self._mw.nmrh_DoubleSpinBox.setValue(freqs[0])
        self._mw.nmrc13_DoubleSpinBox.setValue(freqs[1])
        self._mw.nmrn14_DoubleSpinBox.setValue(freqs[2])
        self._mw.nmrn15_DoubleSpinBox.setValue(freqs[3])

        self._mw.xy8h_DoubleSpinBox.setValue(xy8[0])
        self._mw.xy8c13_DoubleSpinBox.setValue(xy8[1])
        self._mw.xy8n14_DoubleSpinBox.setValue(xy8[2])
        self._mw.xy8n15_DoubleSpinBox.setValue(xy8[3])
        return

    def change_field_param(self):
        """ Change the zero-field-splitting value of NV center, for the calculation of field"""
        zfs = self._mw.zfs_DoubleSpinBox.value()
        e = self._mw.e_DoubleSpinBox.value()
        lac = self._mw.lac_CheckBox.isChecked()
        self.sigCalParamsChanged.emit(zfs, e, lac)
        return

    def change_dip_values(self):
        """ Change the dip values manuly for field calculation"""
        freq1 = self._mw.freq1_DoubleSpinBox.value()
        freq2 = self._mw.freq2_DoubleSpinBox.value()
        self.sigManualDipsChanged.emit(freq1, freq2)
        return

    def change_manual_field(self):
        """ Change the field values manualy for NMR calculation"""
        manual_field = self._mw.manual_field_DoubleSpinBox.value()
        self.sigMaualFieldChanged.emit(manual_field)
        return

    def use_single_freq(self):
        single_freq = self._mw.odmr1_DoubleSpinBox.value()
        b_field = self.calculator.single_freq(single_freq)
        self._mw.manual_field_DoubleSpinBox.setValue(b_field)
        self.change_manual_field()
        return

    def auto_calculate_nmr(self):
        self.calculator.set_m_f()
        self.calculator.calculate_nmr()
        return

    def manual_calculate_nmr(self):
        self.calculator.set_m_t()
        self.calculator.calculate_nmr()
        return


class NVCalculatorMainWindow(QtWidgets.QMainWindow):
    """ Create the Calculator GUI window.
    """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_nv_calculator.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()
