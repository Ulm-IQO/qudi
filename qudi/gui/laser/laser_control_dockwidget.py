# -*- coding: utf-8 -*-

"""
This file contains a QDockWidget subclass for the laser control elements of the laser GUI.

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

__all__ = ('LaserControlDockWidget',)

from PySide2 import QtCore, QtWidgets

from qudi.core.gui.qtwidgets.scientific_spinbox import ScienDSpinBox
from qudi.core.gui.qtwidgets.slider import DoubleSlider
from qudi.core.gui.qtwidgets.advanced_dockwidget import AdvancedDockWidget
from qudi.interface.simple_laser_interface import ControlMode


class LaserControlDockWidget(AdvancedDockWidget):
    """
    """
    sigControlModeChanged = QtCore.Signal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # generate main widget and layout
        main_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QGridLayout()
        main_layout.setContentsMargins(1, 1, 1, 1)
        main_widget.setLayout(main_layout)
        self.setWidget(main_widget)

        # generate child widgets
        # ToDo: Use toggle switches
        self.laser_button = QtWidgets.QPushButton('Laser')
        self.laser_button.setCheckable(True)
        main_layout.addWidget(self.laser_button, 0, 0)
        self.shutter_button = QtWidgets.QPushButton('Shutter')
        self.shutter_button.setCheckable(True)
        main_layout.addWidget(self.shutter_button, 0, 1)

        group_box = QtWidgets.QGroupBox('Control Mode')
        layout = QtWidgets.QHBoxLayout()
        group_box.setLayout(layout)
        button_group = QtWidgets.QButtonGroup(self)
        self.control_power_radio_button = QtWidgets.QRadioButton('Power')
        self.control_current_radio_button = QtWidgets.QRadioButton('Current')
        button_group.addButton(self.control_power_radio_button)
        button_group.addButton(self.control_current_radio_button)
        layout.addWidget(self.control_power_radio_button)
        layout.addWidget(self.control_current_radio_button)
        self.control_power_radio_button.clicked.connect(
            lambda: self.sigControlModeChanged.emit(ControlMode.POWER)
        )
        self.control_current_radio_button.clicked.connect(
            lambda: self.sigControlModeChanged.emit(ControlMode.CURRENT)
        )
        main_layout.addWidget(group_box, 1, 0, 1, 2)

        group_box = QtWidgets.QGroupBox('Power')
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignCenter)
        group_box.setLayout(layout)
        self.power_spinbox = ScienDSpinBox()
        self.power_spinbox.setDecimals(2)
        self.power_spinbox.setMinimum(-1)
        self.power_spinbox.setSuffix('W')
        self.power_spinbox.setMinimumWidth(75)
        self.power_spinbox.setReadOnly(True)
        self.power_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.power_spinbox.setFocusPolicy(QtCore.Qt.NoFocus)
        self.power_spinbox.setMouseTracking(False)
        self.power_spinbox.setKeyboardTracking(False)
        layout.addWidget(self.power_spinbox)
        self.power_setpoint_spinbox = ScienDSpinBox()
        self.power_setpoint_spinbox.setDecimals(2)
        self.power_setpoint_spinbox.setMinimum(0)
        self.power_setpoint_spinbox.setSuffix('W')
        self.power_setpoint_spinbox.setMinimumWidth(75)
        layout.addWidget(self.power_setpoint_spinbox)
        self.power_slider = DoubleSlider(QtCore.Qt.Vertical)
        self.power_slider.set_granularity(10000)  # 0.01% precision
        self.power_slider.setMinimumHeight(200)
        self.power_slider.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                        QtWidgets.QSizePolicy.Expanding)
        layout.addWidget(self.power_slider)
        main_layout.addWidget(group_box, 2, 0)

        group_box = QtWidgets.QGroupBox('Current')
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignCenter)
        group_box.setLayout(layout)
        self.current_spinbox = ScienDSpinBox()
        self.current_spinbox.setDecimals(2)
        self.current_spinbox.setMinimum(-1)
        self.current_spinbox.setMinimumWidth(75)
        self.current_spinbox.setReadOnly(True)
        self.current_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.current_spinbox.setFocusPolicy(QtCore.Qt.NoFocus)
        self.current_spinbox.setMouseTracking(False)
        self.current_spinbox.setKeyboardTracking(False)
        layout.addWidget(self.current_spinbox)
        self.current_setpoint_spinbox = ScienDSpinBox()
        self.current_setpoint_spinbox.setDecimals(2)
        self.current_setpoint_spinbox.setMinimum(0)
        self.current_setpoint_spinbox.setMinimumWidth(75)
        layout.addWidget(self.current_setpoint_spinbox)
        self.current_slider = DoubleSlider(QtCore.Qt.Vertical)
        self.current_slider.set_granularity(10000)  # 0.01% precision
        self.current_slider.setRange(0, 100)
        self.current_slider.setMinimumHeight(200)
        self.current_slider.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                          QtWidgets.QSizePolicy.Expanding)
        layout.addWidget(self.current_slider)
        main_layout.addWidget(group_box, 2, 1)
        main_widget.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)