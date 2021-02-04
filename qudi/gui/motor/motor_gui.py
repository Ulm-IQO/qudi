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
from qudi.core.connector import Connector
from qudi.core.util import units
from qudi.core.module import GuiBase
from PySide2 import QtCore, QtWidgets, QtGui
from qudi.core.util.paths import get_artwork_dir
from qudi.core.gui.uic import loadUi
from qudi.core.gui.colordefs import QudiPalettePale as palette


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


class MotorGui(GuiBase):
    """
    This is the GUI Class for Motor operations
    """

    # declare connectors
    _motor_logic = Connector(name='motor_logic', interface='MotorLogic')

    # sigUnitChanged = QtCore.Signal(bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_activate(self):
        self._mw = MotorMainWindow()
        self._mw.setDockNestingEnabled(True)
        self.constraints = self._motor_logic().constraints
        self._unit_mode = self.constraints['x']['unit']
        self._resolution = self.constraints['x']['resolution']
        if self._unit_mode == 'step':
            self._mw.radioButton_step.setChecked(True)
        else:
            self._mw.radioButton_um.setChecked(True)
        self._mw.motor_x_move_negative.clicked.connect(self.motor_x_move_negative)
        self._mw.motor_x_move_positive.clicked.connect(self.motor_x_move_positive)
        self._mw.motor_y_move_negative.clicked.connect(self.motor_y_move_negative)
        self._mw.motor_y_move_positive.clicked.connect(self.motor_y_move_positive)
        self._mw.abort.clicked.connect(self.abort)
        self._mw.radioButton_step.toggled.connect(self._unit_mode_clicked)
        self._mw.radioButton_um.toggled.connect(self._unit_mode_clicked)
        self._mw.lineEdit_speed_x.editingFinished.connect(self._change_speed_x)
        self._mw.lineEdit_speed_y.editingFinished.connect(self._change_speed_y)
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
        self._mw.motor_x_move_negative.clicked.disconnect()
        self._mw.motor_x_move_positive.clicked.disconnect()
        self._mw.motor_y_move_negative.clicked.disconnect()
        self._mw.motor_y_move_positive.clicked.disconnect()
        self._mw.abort.clicked.disconnect()
        self._mw.radioButton_step.toggled.disconnect()
        self._mw.radioButton_um.toggled.disconnect()
        self._mw.lineEdit_speed_x.editingFinished.disconnect()
        self._mw.lineEdit_speed_y.editingFinished.disconnect()
        self._mw.close()

    def _change_speed(self, param_dict):
        self._motor_logic().set_velocity(param_dict)

    def _change_speed_x(self):
        new_speed = int(self._mw.lineEdit_speed_x.text())
        vel_min = self.constraints['x']['vel_min'][0]
        vel_max = self.constraints['x']['vel_max'][0]
        if vel_min <= new_speed <= vel_max:
            self._change_speed({'x': new_speed})
        else:
            raise Exception('Speed does not match hardware constraints!')

    def _change_speed_y(self):
        new_speed = int(self._mw.lineEdit_speed_y.text())
        vel_min = self.constraints['y']['vel_min'][0]
        vel_max = self.constraints['y']['vel_max'][0]
        if vel_min <= new_speed <= vel_max:
            self._change_speed({'y': new_speed})
        else:
            raise Exception('Speed does not match hardware constraints!')

    def _unit_mode_clicked(self):
        if self._mw.radioButton_step.isChecked():
            if self._unit_mode == 'step':
                return
            else:
                self._unit_mode = 'step'
                # print(str(int(float(self._mw.lineEdit_x.text()) / self._resolution)))
                self._mw.lineEdit_x.setText(str(int(float(self._mw.lineEdit_x.text()) / self._resolution)))
                self._mw.lineEdit_y.setText(str(int(float(self._mw.lineEdit_y.text()) / self._resolution)))
        elif self._mw.radioButton_um.isChecked():
            if self._unit_mode == 'm':
                return
            else:
                self._unit_mode = 'm'
                self._mw.lineEdit_x.setText(str(float(self._mw.lineEdit_x.text()) * self._resolution))
                self._mw.lineEdit_y.setText(str(float(self._mw.lineEdit_y.text()) * self._resolution))

    def abort(self):
        self._motor_logic().abort()

    def move_relative(self, param_dict):
        self._motor_logic().move_rel(param_dict)

    def motor_x_move_negative(self):
        self.move_relative({'x': -float(self._mw.lineEdit_x.text()), 'unit': self._unit_mode})

    def motor_x_move_positive(self):
        self.move_relative({'x': float(self._mw.lineEdit_x.text()), 'unit': self._unit_mode})

    def motor_y_move_negative(self):
        self.move_relative({'y': -float(self._mw.lineEdit_y.text()), 'unit': self._unit_mode})

    def motor_y_move_positive(self):
        self.move_relative({'y': float(self._mw.lineEdit_y.text()), 'unit': self._unit_mode})
