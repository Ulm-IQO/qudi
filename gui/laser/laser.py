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

import numpy as np
import os
import pyqtgraph as pg
import time

from core.module import Connector
from gui.colordefs import QudiPalettePale as palette
from gui.guibase import GUIBase
from interface.simple_laser_interface import ControlMode, ShutterState, LaserState
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic


class TimeAxisItem(pg.AxisItem):
    """ pyqtgraph AxisItem that shows a HH:MM:SS timestamp on ticks.
        X-Axis must be formatted as (floating point) Unix time.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enableAutoSIPrefix(False)

    def tickStrings(self, values, scale, spacing):
        """ Hours:Minutes:Seconds string from float unix timestamp. """
        return [time.strftime("%H:%M:%S", time.localtime(value)) for value in values]


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
    laserlogic = Connector(interface='LaserLogic')

    sigLaser = QtCore.Signal(bool)
    sigShutter = QtCore.Signal(bool)
    sigPower = QtCore.Signal(float)
    sigCurrent = QtCore.Signal(float)
    sigCtrlMode = QtCore.Signal(ControlMode)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition and initialisation of the GUI plus staring the measurement.
        """
        self._laser_logic = self.get_connector('laserlogic')

        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = LaserWindow()

        # Setup dock widgets
        self._mw.setDockNestingEnabled(True)
        self._mw.actionReset_View.triggered.connect(self.restoreDefaultView)

        # set up plot
        self._mw.plotWidget = pg.PlotWidget(
            axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self._mw.pwContainer.layout().addWidget(self._mw.plotWidget)

        plot1 = self._mw.plotWidget.getPlotItem()
        plot1.setLabel('left', 'power', units='W', color=palette.c1.name())
        plot1.setLabel('bottom', 'Time', units=None)
        plot1.setLabel('right', 'Temperature', units='°C', color=palette.c3.name())

        plot2 = pg.ViewBox()
        plot1.scene().addItem(plot2)
        plot1.getAxis('right').linkToView(plot2)
        plot2.setXLink(plot1)

        self.curves = {}
        colorlist = (palette.c2, palette.c3, palette.c4, palette.c5, palette.c6)
        i = 0
        for name in self._laser_logic.data:
            if name != 'time':
                curve = pg.PlotDataItem()
                if name == 'power':
                    curve.setPen(palette.c1)
                    plot1.addItem(curve)
                else:
                    curve.setPen(colorlist[(2*i) % len(colorlist)])
                    plot2.addItem(curve)
                self.curves[name] = curve
                i += 1

        self.plot1 = plot1
        self.plot2 = plot2
        self.updateViews()
        self.plot1.vb.sigResized.connect(self.updateViews)

        self.updateButtonsEnabled()
        self._mw.laserButton.clicked.connect(self.changeLaserState)
        self._mw.shutterButton.clicked.connect(self.changeShutterState)
        self.sigLaser.connect(self._laser_logic.set_laser_state)
        self.sigShutter.connect(self._laser_logic.set_shutter_state)
        self.sigCurrent.connect(self._laser_logic.set_current)
        self.sigPower.connect(self._laser_logic.set_power)
        self.sigCtrlMode.connect(self._laser_logic.set_control_mode)
        self._mw.controlModeButtonGroup.buttonClicked.connect(self.changeControlMode)
        self.sliderProxy = pg.SignalProxy(self._mw.setValueVerticalSlider.valueChanged, 0.1, 5, self.updateFromSlider)
        self._mw.setValueDoubleSpinBox.editingFinished.connect(self.updateFromSpinBox)
        self._laser_logic.sigUpdate.connect(self.updateGui)

    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        self._mw.close()

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def restoreDefaultView(self):
        """ Restore the arrangement of DockWidgets to the default
        """
        # Show any hidden dock widgets
        self._mw.adjustDockWidget.show()
        self._mw.plotDockWidget.show()

        # re-dock any floating dock widgets
        self._mw.adjustDockWidget.setFloating(False)
        self._mw.plotDockWidget.setFloating(False)

        # Arrange docks widgets
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.adjustDockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(2), self._mw.plotDockWidget)

    @QtCore.Slot()
    def updateViews(self):
        """ Keep plot views for left and right axis identical when resizing the plot widget. """
        # view has resized; update auxiliary views to match
        self.plot2.setGeometry(self.plot1.vb.sceneBoundingRect())

        # need to re-update linked axes since this was called incorrectly while views had different
        # shapes. (probably this should be handled in ViewBox.resizeEvent)
        self.plot2.linkedViewChanged(self.plot1.vb, self.plot2.XAxis)

    @QtCore.Slot(bool)
    def changeLaserState(self, on):
        """ Disable laser power button and give logic signal.
            Logic reaction to that signal will enable the button again.
        """
        self._mw.laserButton.setEnabled(False)
        self.sigLaser.emit(on)

    @QtCore.Slot(bool)
    def changeShutterState(self, on):
        """ Disable laser shutter button and give logic signal.
            Logic reaction to that signal will enable the button again.
        """
        self._mw.shutterButton.setEnabled(False)
        self.sigShutter.emit(on)

    @QtCore.Slot(QtWidgets.QAbstractButton)
    def changeControlMode(self, buttonId):
        """ Process signal from laser control mode radio button group. """
        cur = self._mw.currentRadioButton.isChecked() and self._mw.currentRadioButton.isEnabled()
        pwr = self._mw.powerRadioButton.isChecked() and self._mw.powerRadioButton.isEnabled()
        if pwr and not cur:
            lpr = self._laser_logic.laser_power_range
            self._mw.setValueDoubleSpinBox.setRange(lpr[0], lpr[1])
            self._mw.setValueDoubleSpinBox.setValue(self._laser_logic.laser_power_setpoint)
            self._mw.setValueDoubleSpinBox.setSuffix('W')
            self._mw.setValueVerticalSlider.setValue(
                self._laser_logic.laser_power_setpoint / (lpr[1] - lpr[0]) * 100 - lpr[0])
            self.sigCtrlMode.emit(ControlMode.POWER)
        elif cur and not pwr:
            lcr = self._laser_logic.laser_current_range
            self._mw.setValueDoubleSpinBox.setRange(lcr[0], lcr[1])
            self._mw.setValueDoubleSpinBox.setValue(self._laser_logic.laser_current_setpoint)
            self._mw.setValueDoubleSpinBox.setSuffix('%')
            self._mw.setValueVerticalSlider.setValue(
                self._laser_logic.laser_current_setpoint / (lcr[1] - lcr[0]) * 100 - lcr[0])
            self.sigCtrlMode.emit(ControlMode.CURRENT)
        else:
            self.log.error('How did you mess up the radio button group?')

    @QtCore.Slot()
    def updateButtonsEnabled(self):
        """ Logic told us to update our button states, so set the buttons accordingly. """
        self._mw.laserButton.setEnabled(self._laser_logic.laser_can_turn_on)
        if self._laser_logic.laser_state == LaserState.ON:
            self._mw.laserButton.setText('Laser: ON')
            self._mw.laserButton.setChecked(True)
            self._mw.laserButton.setStyleSheet('')
        elif self._laser_logic.laser_state == LaserState.OFF:
            self._mw.laserButton.setText('Laser: OFF')
            self._mw.laserButton.setChecked(False)
        elif self._laser_logic.laser_state == LaserState.LOCKED:
            self._mw.laserButton.setText('INTERLOCK')
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
        """ Update labels, the plot and button states with new data. """
        self._mw.currentLabel.setText(
            '{0:6.3f} {1}'.format(
                self._laser_logic.laser_current,
                self._laser_logic.laser_current_unit))
        self._mw.powerLabel.setText('{0:6.3f} W'.format(self._laser_logic.laser_power))
        self._mw.extraLabel.setText(self._laser_logic.laser_extra)
        self.updateButtonsEnabled()
        for name, curve in self.curves.items():
            curve.setData(x=self._laser_logic.data['time'], y=self._laser_logic.data[name])

    @QtCore.Slot()
    def updateFromSpinBox(self):
        """ The user has changed the spinbox, update all other values from that. """
        self._mw.setValueVerticalSlider.setValue(self._mw.setValueDoubleSpinBox.value())
        cur = self._mw.currentRadioButton.isChecked() and self._mw.currentRadioButton.isEnabled()
        pwr = self._mw.powerRadioButton.isChecked() and  self._mw.powerRadioButton.isEnabled()
        if pwr and not cur:
            self.sigPower.emit(self._mw.setValueDoubleSpinBox.value())
        elif cur and not pwr:
            self.sigCurrent.emit(self._mw.setValueDoubleSpinBox.value())

    @QtCore.Slot()
    def updateFromSlider(self):
        """ The user has changed the slider, update all other values from that. """
        cur = self._mw.currentRadioButton.isChecked() and self._mw.currentRadioButton.isEnabled()
        pwr = self._mw.powerRadioButton.isChecked() and self._mw.powerRadioButton.isEnabled()
        if pwr and not cur:
            lpr = self._laser_logic.laser_power_range
            self._mw.setValueDoubleSpinBox.setValue(
                lpr[0] + self._mw.setValueVerticalSlider.value() / 100 * (lpr[1] - lpr[0]))
            self.sigPower.emit(
                lpr[0] + self._mw.setValueVerticalSlider.value() / 100 * (lpr[1] - lpr[0]))
        elif cur and not pwr:
            self._mw.setValueDoubleSpinBox.setValue(self._mw.setValueVerticalSlider.value())
            self.sigCurrent.emit(self._mw.setValueDoubleSpinBox.value())

