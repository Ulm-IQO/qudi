# -*- coding: utf-8 -*-

"""
This file contains a gui for the laser controller logic.

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

from gui.guibase import GUIBase
from interface.simple_laser_interface import ControlMode, ShutterState, LaserState
from gui.colordefs import QudiPalettePale as palette
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic
import numpy as np
import pyqtgraph as pg
import os


class LaserWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_laser.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class LaserGUI(GUIBase):
    """ FIXME: Please document
    """
    _modclass = 'lasergui'
    _modtype = 'gui'

    ## declare connectors
    _in = {'laserlogic': 'LaserLogic'}

    sigLaser = QtCore.Signal(bool)
    sigShutter = QtCore.Signal(bool)
    sigPower = QtCore.Signal(float)
    sigCurrent = QtCore.Signal(float)
    sigCtrlMode = QtCore.Signal(ControlMode)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self, e=None):
        """ Definition and initialisation of the GUI plus staring the measurement.

        @param object e: Fysom.event object from Fysom class.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """
        self._laser_logic = self.get_in_connector('laserlogic')

        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = LaserWindow()

        # Setup dock widgets
        self._mw.setDockNestingEnabled(True)

        # set up plot
        pw = self._mw.graphicsView
        plot1 = pw.plotItem
        plot1.setLabel('left', 'Some Value', units='some unit', color='#00ff00')
        plot1.setLabel('bottom', 'Number of values', units='some unit')
        self.plots = {}
        colorlist = (palette.c1, palette.c2, palette.c3, palette.c4, palette.c5, palette.c6)
        i = 0
        for k in self._laser_logic.data:
            if k != 'time':
                self.plots[k] = plot1.plot()
                self.plots[k].setPen(colorlist[(2*i)%len(colorlist)])
                i += 1

        self.updateButtonsEnabled()

        self._mw.laserButton.clicked.connect(self.changeLaserState)
        self._mw.shutterButton.clicked.connect(self.changeShutterState)
        self.sigLaser.connect(self._laser_logic.set_laser_state)
        self.sigShutter.connect(self._laser_logic.set_shutter_state)
        self.sigCurrent.connect(self._laser_logic.set_current)
        self.sigPower.connect(self._laser_logic.set_power)
        self._mw.controlModeButtonGroup.buttonClicked.connect(self.changeControlMode)
        self.sliderProxy = pg.SignalProxy(self._mw.setValueVerticalSlider.valueChanged, 0.1, 5, self.updateFromSlider)
        self._mw.setValueDoubleSpinBox.editingFinished.connect(self.updateFromSpinBox)
        self._laser_logic.sigUpdate.connect(self.updateGui)

    def on_deactivate(self, e):
        """ Deactivate the module properly.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        self._mw.close()

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def changeLaserState(self, on):
        """ """
        self._mw.laserButton.setEnabled(False)
        self.sigLaser.emit(on)

    def changeShutterState(self, on):
        """ """
        self._mw.shutterButton.setEnabled(False)
        self.sigShutter.emit(on)

    @QtCore.Slot(int)
    def changeControlMode(self, buttonId):
        """ """
        cur = self._mw.currentRadioButton.isChecked() and self._mw.currentRadioButton.isEnabled()
        pwr = self._mw.powerRadioButton.isChecked() and self._mw.powerRadioButton.isEnabled()
        if pwr and not cur:
            lpr = self._laser_logic.laser_power_range
            self._mw.setValueDoubleSpinBox.setRange(lpr[0], lpr[1])
            self._mw.setValueDoubleSpinBox.setValue(self._laser_logic._laser.get_power_setpoint())
            self._mw.setValueVerticalSlider.setValue(
                self._laser_logic._laser.get_power_setpoint() / (lpr[1] - lpr[0]) * 100 - lpr[0])
            self.sigCtrlMode.emit(ControlMode.POWER)
        elif cur and not pwr:
            self._mw.setValueDoubleSpinBox.setRange(0, 100)
            self._mw.setValueDoubleSpinBox.setValue(self._laser_logic._laser.get_current_setpoint())
            self._mw.setValueVerticalSlider.setValue(self._laser_logic._laser.get_current_setpoint())
            self.sigCtrlMode.emit(ControlMode.CURRENT)
        else:
            self.log.error('Nope.')
        
    @QtCore.Slot()
    def updateButtonsEnabled(self):
        """ """
        self._mw.laserButton.setEnabled(self._laser_logic.laser_can_turn_on)
        if self._laser_logic.laser_state == LaserState.ON:
            self._mw.laserButton.setText('Laser: ON')
            self._mw.laserButton.setStyleSheet('')
        elif self._laser_logic.laser_state == LaserState.OFF:
            self._mw.laserButton.setText('Laser: OFF')
        else:
            self._mw.laserButton.setText('Laser: ?')

        self._mw.shutterButton.setEnabled(self._laser_logic.has_shutter)
        if self._laser_logic.laser_shutter == ShutterState.OPEN:
            self._mw.shutterButton.setText('Shutter: OPEN')
        elif self._laser_logic.laser_shutter == ShutterState.CLOSED:
            self._mw.shutterButton.setText('Shutter: CLOSED')
        elif self._laser_logic.laser_shutter == ShutterState.NOSHUTTER:
            self._mw.shutterButton.setText('No shutter.')
        else:
            self._mw.laserButton.setText('Shutter: ?')

        self._mw.currentRadioButton.setEnabled(self._laser_logic.laser_can_current)
        self._mw.powerRadioButton.setEnabled(self._laser_logic.laser_can_power)

    @QtCore.Slot()
    def updateGui(self):
        """ """
        self._mw.currentLabel.setText('{0:6.2f} %'.format(self._laser_logic.laser_current))
        self._mw.powerLabel.setText('{0:6.2f} W'.format(self._laser_logic.laser_power))
        self._mw.extraLabel.setText(self._laser_logic.laser_extra)
        self.updateButtonsEnabled()
        for k in self.plots:
            self.plots[k].setData(x=self._laser_logic.data['time'], y=self._laser_logic.data[k])

    @QtCore.Slot()
    def updateFromSpinBox(self):
        """ """
        self._mw.setValueVerticalSlider.setValue(self._mw.setValueDoubleSpinBox.value())
        cur = self._mw.currentRadioButton.isChecked() and self._mw.currentRadioButton.isEnabled()
        pwr = self._mw.powerRadioButton.isChecked() and  self._mw.powerRadioButton.isEnabled()
        if pwr and not cur:
            self.sigPower.emit(self._mw.setValueDoubleSpinBox.value())
        elif cur and not pwr:
            self.sigCurrent.emit(self._mw.setValueDoubleSpinBox.value())

    @QtCore.Slot()
    def updateFromSlider(self):
        """ """
        cur = self._mw.currentRadioButton.isChecked() and self._mw.currentRadioButton.isEnabled()
        pwr = self._mw.powerRadioButton.isChecked() and  self._mw.powerRadioButton.isEnabled()
        if pwr and not cur:
            lpr = self._laser_logic.laser_power_range
            self._mw.setValueDoubleSpinBox.setValue(
                lpr[0] + self._mw.setValueVerticalSlider.value() / 100 * (lpr[1] - lpr[0]))
            self.sigPower.emit(
                lpr[0] + self._mw.setValueVerticalSlider.value() / 100 * (lpr[1] - lpr[0]))
        elif cur and not pwr:
            self._mw.setValueDoubleSpinBox.setValue(self._mw.setValueVerticalSlider.value())
            self.sigCurrent.emit(self._mw.setValueDoubleSpinBox.value())

