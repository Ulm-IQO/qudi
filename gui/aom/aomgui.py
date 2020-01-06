# -*- coding: utf-8 -*-

"""
This file contains the Qudi aom & psat gui.

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
import os
import pyqtgraph as pg

from core.module import Connector
from gui.colordefs import QudiPalettePale as palette
from gui.guibase import GUIBase
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic


class AomMainWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self, **kwargs):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_aom.ui')

        # Load it
        super().__init__(**kwargs)
        uic.loadUi(ui_file, self)
        self.show()


class AomGui(GUIBase):
    """ GUI for aom logic. Module used for controlling AOM diffraction efficiency via process_value_modifier

        Example config :
        aom_gui:
            module.Class: 'aom.aomgui.AomGui'
            connect:
                logic: 'aomlogic'

    """

    logic = Connector(interface='AomLogic')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """
        self._mw = AomMainWindow()
        self._curve = pg.PlotDataItem(self.logic().voltages,
                                          self.logic().powers,
                                          pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                                          symbol='o',
                                          symbolPen=palette.c1,
                                          symbolBrush=palette.c1,
                                          symbolSize=7)

        self._mw.plotWidget.addItem(self._curve)
        self._mw.plotWidget.setLabel(axis='left', text='Power', units='W')
        self._mw.plotWidget.setLabel(axis='bottom', text='Voltage', units='V')
        self._mw.plotWidget.showGrid(x=True, y=True, alpha=0.8)

        self.update_max_power_from_logic()
        self.update_parameters_from_logic()

        # Handling signals from the logic
        self.logic().sigNewDataPoint.connect(self.update_data)
        self.logic().sigNewMaxPower.connect(self.update_max_power_from_logic)
        self.logic().sigStarted.connect(self.started)
        self.logic().sigFinished.connect(self.finished)
        self.logic().sigParameterChanged.connect(self.update_parameters_from_logic)

        # Sending signals to the logic
        self._mw.runAction.triggered.connect(self.logic().calibrate)
        self._mw.saveAction.triggered.connect(self.logic().save)
        self._mw.abortAction.triggered.connect(self.logic().abort,  QtCore.Qt.DirectConnection)

        self._mw.timeBeforeStartDoubleSpinBox.editingFinished.connect(self.parameters_changed)
        self._mw.resolutionSpinBox.editingFinished.connect(self.parameters_changed)
        self._mw.delayAfterChangeDoubleSpinBox.editingFinished.connect(self.parameters_changed)
        self._mw.delayBetweenRepetitions.editingFinished.connect(self.parameters_changed)
        self._mw.repetitionsSpinBox.editingFinished.connect(self.parameters_changed)

        self._mw.maxPower.editingFinished.connect(self.max_power_changed)
        self._mw.setFromMeasurement.clicked.connect(self.logic().calibrate_max)

        self._mw.abortAction.setEnabled(False)

    def show(self):
        """ Make window visible and put it above all other windows. """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def on_deactivate(self):
        """ Deactivate the module """
        self.logic().sigNewDataPoint.disconnect()
        self.logic().sigNewMaxPower.disconnect()
        self.logic().sigStarted.disconnect()
        self.logic().sigFinished.disconnect()

        self._mw.runAction.triggered.disconnect()
        self._mw.saveAction.triggered.disconnect()
        self._mw.abortAction.triggered.disconnect()

        self._mw.timeBeforeStartDoubleSpinBox.editingFinished.disconnect()
        self._mw.resolutionSpinBox.editingFinished.disconnect()
        self._mw.delayAfterChangeDoubleSpinBox.editingFinished.disconnect()
        self._mw.delayBetweenRepetitions.editingFinished.disconnect()
        self._mw.repetitionsSpinBox.editingFinished.disconnect()

        self._mw.maxPower.editingFinished.disconnect()
        self._mw.setFromMeasurement.clicked.disconnect()

        self._mw.close()

    def update_max_power_from_logic(self):
        self._mw.maxPower.blockSignals(True)
        self._mw.maxPower.setValue(self.logic().power_max)
        self._mw.maxPower.blockSignals(False)

    def update_parameters_from_logic(self):
        self._mw.timeBeforeStartDoubleSpinBox.blockSignals(True)
        self._mw.resolutionSpinBox.blockSignals(True)
        self._mw.delayAfterChangeDoubleSpinBox.blockSignals(True)
        self._mw.delayBetweenRepetitions.blockSignals(True)
        self._mw.repetitionsSpinBox.blockSignals(True)

        self._mw.timeBeforeStartDoubleSpinBox.setValue(self.logic().time_before_start*1)
        self._mw.resolutionSpinBox.setValue(self.logic().resolution*1)
        self._mw.delayAfterChangeDoubleSpinBox.setValue(self.logic().delay_after_change*1)
        self._mw.delayBetweenRepetitions.setValue(self.logic().delay_between_repetitions*1)
        self._mw.repetitionsSpinBox.setValue(self.logic().repetitions*1)

        self._mw.timeBeforeStartDoubleSpinBox.blockSignals(False)
        self._mw.resolutionSpinBox.blockSignals(False)
        self._mw.delayAfterChangeDoubleSpinBox.blockSignals(False)
        self._mw.delayBetweenRepetitions.blockSignals(False)
        self._mw.repetitionsSpinBox.blockSignals(False)

    def parameters_changed(self):
        self.logic().time_before_start = self._mw.timeBeforeStartDoubleSpinBox.value()
        self.logic().resolution = self._mw.resolutionSpinBox.value()
        self.logic().delay_after_change = self._mw.delayAfterChangeDoubleSpinBox.value()
        self.logic().delay_between_repetitions = self._mw.delayBetweenRepetitions.value()
        self.logic().repetitions = self._mw.repetitionsSpinBox.value()

        self.update_parameters_from_logic()  # needed otherwise weird alternating value effect (gui/logic)
        return

    def max_power_changed(self):
        self.logic().calibrate_max_from_value(self._mw.maxPower.value())
        self.update_max_power_from_logic() # same thing

    def update_data(self):
        """ Refresh the plot widgets with new data. """
        self._curve.setData(self.logic().voltages, self.logic().powers)

    def started(self):
        """ Update GUI when logic runs """
        self._mw.abortAction.setEnabled(True)
        self._mw.runAction.setEnabled(False)
        self._mw.saveAction.setEnabled(False)

    def finished(self):
        """ Update GUI when logic stops """
        self._mw.abortAction.setEnabled(False)
        self._mw.runAction.setEnabled(True)
        self._mw.saveAction.setEnabled(True)

