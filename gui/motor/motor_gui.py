# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI module for Motor control.

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
from core.connector import Connector
from gui.guibase import GUIBase
from qtpy import QtWidgets
from qtpy.uic import loadUi
from core.statusvariable import StatusVar


class MotorMainWindow(QtWidgets.QMainWindow):
    """ The main window for the Motor GUI
        """

    def __init__(self, **kwargs):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'motor.ui')

        # Load it
        super().__init__(**kwargs)
        loadUi(ui_file, self)

        # self.setTabPosition(QtCore.Qt.TopDockWidgetArea, QtWidgets.QTabWidget.North)
        # self.setTabPosition(QtCore.Qt.BottomDockWidgetArea, QtWidgets.QTabWidget.North)
        # self.setTabPosition(QtCore.Qt.LeftDockWidgetArea, QtWidgets.QTabWidget.North)
        # self.setTabPosition(QtCore.Qt.RightDockWidgetArea, QtWidgets.QTabWidget.North)
        self.setWindowTitle('qudi: Motor')

        # # Create QActions
        # icon_path = os.path.join(get_artwork_dir(), 'icons')
        #
        # icon = QtGui.QIcon(os.path.join(icon_path, 'qudiTheme', '22x22', 'start-counter.png'))
        # icon.addFile(os.path.join(icon_path, 'qudiTheme', '22x22', 'stop-counter.png'),
        #              state=QtGui.QIcon.On)


class MotorGui(GUIBase):
    """
    This is the GUI Class for Motor operations
    """

    # declare connectors
    _motor_logic = Connector(name='_motor_logic', interface='MotorLogic')

    _xspeed = StatusVar(default=250)
    _yspeed = StatusVar(default=250)
    _step_x = StatusVar(default=100)
    _step_y = StatusVar(default=100)
    _unit_mode = StatusVar(default='step')

    # sigUnitChanged = QtCore.Signal(bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_activate(self):
        self._mw = MotorMainWindow()
        self._mw.setDockNestingEnabled(True)
        self.constraints = self._motor_logic().constraints
        self._mode = 'step'
        self._resolution = self.constraints['x']['resolution']

        self._mw.motor_x_move_negative.clicked.connect(self.motor_x_move_negative)
        self._mw.motor_x_move_positive.clicked.connect(self.motor_x_move_positive)
        self._mw.motor_y_move_negative.clicked.connect(self.motor_y_move_negative)
        self._mw.motor_y_move_positive.clicked.connect(self.motor_y_move_positive)
        self._mw.abort.clicked.connect(self.abort)
        self._mw.radioButton_step.toggled.connect(self._unit_mode_clicked)
        self._mw.radioButton_um.toggled.connect(self._unit_mode_clicked)
        self._mw.lineEdit_speed_x.editingFinished.connect(self._change_speed_x)
        self._mw.lineEdit_speed_y.editingFinished.connect(self._change_speed_y)
        self._mw.radioButton_mode_step.toggled.connect(self._mode_clicked)
        self._mw.radioButton_mode_jog.toggled.connect(self._mode_clicked)

        if self._unit_mode == 'step':
            self._unit_mode = 'm'  # this is confusing but the uni_mode is changed in self._unit_mode_clicked
            self._mw.radioButton_step.setChecked(True)
        else:
            self._unit_mode = 'step'
            self._mw.radioButton_um.setChecked(True)
        self._mw.lineEdit_speed_x.setText(str(self._xspeed))
        self._mw.lineEdit_speed_y.setText(str(self._yspeed))
        self._motor_logic().set_velocity({'x': self._xspeed, 'y': self._yspeed})
        self._mw.lineEdit_x.setText(str(self._step_x))
        self._mw.lineEdit_y.setText(str(self._step_y))
        # self.sigUnitChanged.connect(self._unit_mode_clicked)
        self.show()
        return

    def show(self):
        """
        Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()
        return

    def on_deactivate(self):
        if self._mode == 'step':
            self._mw.motor_x_move_negative.clicked.disconnect()
            self._mw.motor_x_move_positive.clicked.disconnect()
            self._mw.motor_y_move_negative.clicked.disconnect()
            self._mw.motor_y_move_positive.clicked.disconnect()
        elif self._mode == 'jog':
            self._mw.motor_x_move_negative.pressed.disconnect()
            self._mw.motor_x_move_positive.pressed.disconnect()
            self._mw.motor_y_move_negative.pressed.disconnect()
            self._mw.motor_y_move_positive.pressed.disconnect()
            # and what when released
            self._mw.motor_x_move_negative.released.disconnect()
            self._mw.motor_x_move_positive.released.disconnect()
            self._mw.motor_y_move_negative.released.disconnect()
            self._mw.motor_y_move_positive.released.disconnect()
        self._mw.abort.clicked.disconnect()
        self._mw.radioButton_step.toggled.disconnect()
        self._mw.radioButton_um.toggled.disconnect()
        self._mw.lineEdit_speed_x.editingFinished.disconnect()
        self._mw.lineEdit_speed_y.editingFinished.disconnect()
        self._mw.radioButton_mode_step.toggled.disconnect()
        self._mw.radioButton_mode_jog.toggled.disconnect()
        self._mw.close()

    def _change_speed(self, param_dict):
        self._motor_logic().set_velocity(param_dict)

    def _change_speed_x(self):
        new_speed = int(self._mw.lineEdit_speed_x.text())
        vel_min = self.constraints['x']['vel_min'][0]
        vel_max = self.constraints['x']['vel_max'][0]
        if vel_min <= new_speed <= vel_max:
            self._change_speed({'x': new_speed})
            self._xspeed = new_speed
        else:
            raise Exception('Speed does not match hardware constraints!')

    def _change_speed_y(self):
        new_speed = int(self._mw.lineEdit_speed_y.text())
        vel_min = self.constraints['y']['vel_min'][0]
        vel_max = self.constraints['y']['vel_max'][0]
        if vel_min <= new_speed <= vel_max:
            self._change_speed({'y': new_speed})
            self._yspeed = new_speed
        else:
            raise Exception('Speed does not match hardware constraints!')

    def _mode_clicked(self):
        if self._mw.radioButton_mode_step.isChecked():
            if self._mode == 'step':
                return
            else:
                self._mode = 'step'
                self._mw.motor_x_move_negative.pressed.disconnect()
                self._mw.motor_x_move_positive.pressed.disconnect()
                self._mw.motor_y_move_negative.pressed.disconnect()
                self._mw.motor_y_move_positive.pressed.disconnect()
                # and what when released
                self._mw.motor_x_move_negative.released.disconnect()
                self._mw.motor_x_move_positive.released.disconnect()
                self._mw.motor_y_move_negative.released.disconnect()
                self._mw.motor_y_move_positive.released.disconnect()
                self._mw.motor_x_move_negative.clicked.connect(self.motor_x_move_negative)
                self._mw.motor_x_move_positive.clicked.connect(self.motor_x_move_positive)
                self._mw.motor_y_move_negative.clicked.connect(self.motor_y_move_negative)
                self._mw.motor_y_move_positive.clicked.connect(self.motor_y_move_positive)
        elif self._mw.radioButton_mode_jog.isChecked():
            if self._mode == 'jog':
                return
            else:
                self._mode = 'jog'
                # disconnect step mode
                self._mw.motor_x_move_negative.clicked.disconnect()
                self._mw.motor_x_move_positive.clicked.disconnect()
                self._mw.motor_y_move_negative.clicked.disconnect()
                self._mw.motor_y_move_positive.clicked.disconnect()
                # define what happens when clicked
                self._mw.motor_x_move_negative.pressed.connect(self.motor_x_move_negative_jog)
                self._mw.motor_x_move_positive.pressed.connect(self.motor_x_move_positive_jog)
                self._mw.motor_y_move_negative.pressed.connect(self.motor_y_move_negative_jog)
                self._mw.motor_y_move_positive.pressed.connect(self.motor_y_move_positive_jog)
                # and what when released
                self._mw.motor_x_move_negative.released.connect(self.abort)
                self._mw.motor_x_move_positive.released.connect(self.abort)
                self._mw.motor_y_move_negative.released.connect(self.abort)
                self._mw.motor_y_move_positive.released.connect(self.abort)

    def _unit_mode_clicked(self):
        if self._mw.radioButton_step.isChecked():
            if self._unit_mode == 'step':
                return
            else:
                self._unit_mode = 'step'
                self._step_x = str(int(float(self._mw.lineEdit_x.text()) / self._resolution))
                self._step_y = str(int(float(self._mw.lineEdit_y.text()) / self._resolution))
                self._mw.lineEdit_x.setText(self._step_x)
                self._mw.lineEdit_y.setText(self._step_y)
        elif self._mw.radioButton_um.isChecked():
            if self._unit_mode == 'm':
                return
            else:
                self._unit_mode = 'm'
                self._step_x = str(float(self._mw.lineEdit_x.text()) * self._resolution)
                self._step_y = str(float(self._mw.lineEdit_y.text()) * self._resolution)
                self._mw.lineEdit_x.setText(self._step_x)
                self._mw.lineEdit_y.setText(self._step_y)

    def abort(self):
        self._motor_logic().abort()

    def move_relative(self, param_dict):
        self._motor_logic().move_rel(param_dict)

    def motor_x_move_negative(self):
        self._step_x = self._mw.lineEdit_x.text()
        self.move_relative({'x': -float(self._step_x), 'unit': self._unit_mode})

    def motor_x_move_positive(self):
        self._step_x = self._mw.lineEdit_x.text()
        self.move_relative({'x': float(self._step_x), 'unit': self._unit_mode})

    def motor_y_move_negative(self):
        self._step_y = self._mw.lineEdit_y.text()
        self.move_relative({'y': -float(self._step_y), 'unit': self._unit_mode})

    def motor_y_move_positive(self):
        self._step_y = self._mw.lineEdit_y.text()
        self.move_relative({'y': float(self._step_y), 'unit': self._unit_mode})

    def motor_x_move_negative_jog(self):
        self.move_relative({'x': -40000, 'unit': 'step'})

    def motor_x_move_positive_jog(self):
        self.move_relative({'x': 40000, 'unit': 'step'})

    def motor_y_move_negative_jog(self):
        self.move_relative({'y': -40000, 'unit': 'step'})

    def motor_y_move_positive_jog(self):
        self.move_relative({'y': 40000, 'unit': 'step'})
