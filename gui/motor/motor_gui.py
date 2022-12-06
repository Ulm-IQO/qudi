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
from qtpy import QtWidgets, QtCore
from qtpy.uic import loadUi
from core.statusvariable import StatusVar
from qtwidgets.scientific_spinbox import ScienSpinBox, ScienDSpinBox


class MotorMainWindow(QtWidgets.QMainWindow):
    """ The main window for the Motor GUI
        """

    sigPressKeyBoard = QtCore.Signal(QtCore.QEvent)
    sigReleaseKeyBoard = QtCore.Signal(QtCore.QEvent)

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

    def keyPressEvent(self, event):
        """Pass the keyboard press event from the main window further. """
        self.sigPressKeyBoard.emit(event)

    def keyReleaseEvent(self, event):
        """Pass the keyboard press event from the main window further. """
        self.sigReleaseKeyBoard.emit(event)

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
    _motor_logic = Connector(interface='MotorLogic')

    _xspeed = StatusVar(default=1e-5)
    _yspeed = StatusVar(default=1e-5)
    _step_x = StatusVar(default=1e-5)
    _step_y = StatusVar(default=1e-5)
    _step_z = StatusVar(default=1)

    _max_step_x = 800e-6
    _max_step_y = 800e-6
    _max_step_z = 1500

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mw = None

    def on_activate(self):

        self._mw = MotorMainWindow()
        self._mw.setDockNestingEnabled(True)

        self._mw.keyboard_checkbox.setChecked(False)
        # self._mw.sigPressKeyBoard.connect(self.keyPressEvent)
        self._mw.keyboard_checkbox.stateChanged.connect(self._toggle_keyboard_control)

        # self._resolution = self.constraints['x']['resolution']

        self._mw.motor_x_move_negative.clicked.connect(self.motor_x_move_negative)
        self._mw.motor_x_move_positive.clicked.connect(self.motor_x_move_positive)
        self._mw.motor_y_move_negative.clicked.connect(self.motor_y_move_negative)
        self._mw.motor_y_move_positive.clicked.connect(self.motor_y_move_positive)
        self._mw.motor_z_move_negative.clicked.connect(self.motor_z_move_negative)
        self._mw.motor_z_move_positive.clicked.connect(self.motor_z_move_positive)
        self._mw.abort.clicked.connect(self.abort)

        self._mw.radioButton_mode_step.setChecked(True)

        self._mode = 'step'

        self._mw.buttonGroup_mode.buttonClicked.connect(self._toggle_mode)

        self._mw.lineEdit_speed.setEnabled(False)

        # self._mw.radioButton_step.toggled.connect(self._unit_mode_clicked)
        # self._mw.radioButton_um.toggled.connect(self._unit_mode_clicked)
        # # self._mw.lineEdit_speed.editingFinished.connect(self._change_speed)
        # self._mw.radioButton_mode_step.toggled.connect(self._mode_clicked)
        # self._mw.radioButton_mode_jog.toggled.connect(self._mode_clicked)

        # if self._unit_mode == 'step':
        #     self._unit_mode = 'm'  # this is confusing but the uni_mode is changed in self._unit_mode_clicked
        #     self._mw.radioButton_step.setChecked(True)
        # else:
        #     self._unit_mode = 'step'
        #     self._mw.radioButton_um.setChecked(True)
        # self._mw.lineEdit_speed_x.setText(str(self._xspeed))
        # self._mw.lineEdit_speed_y.setText(str(self._yspeed))
        # self._motor_logic().set_velocity({'x': self._xspeed, 'y': self._yspeed})


        # self._mw.lineEdit_x.setText(str(self._step_x))
        # self._mw.lineEdit_y.setText(str(self._step_y))
        # self._mw.lineEdit_z.setText(str(self._step_z))
        #
        # self._mw.x_unit_label.setText(self._motor_logic().get_unit('x'))
        # self._mw.y_unit_label.setText(self._motor_logic().get_unit('y'))
        # self._mw.z_unit_label.setText(self._motor_logic().get_unit('z'))

        self._spinboxes = dict.fromkeys(('x', 'y', 'z'))

        for ax in self._spinboxes:
            axis_layout_name = '{0}_settings_horizontalLayout'.format(ax)
            ax_layout = getattr(self._mw, axis_layout_name)
            is_int_steps = self._motor_logic().is_ax_log_integer_steps(ax)
            self._spinboxes[ax] = ScienSpinBox() if is_int_steps else ScienDSpinBox()
            self._spinboxes[ax].setMinimum(0)
            self._spinboxes[ax].setMinimumSize(QtCore.QSize(120, 16777215))
            self._spinboxes[ax].assumed_unit_prefix = 'u' if not is_int_steps else None
            ax_layout.addWidget(self._spinboxes[ax])

            unit_label = QtWidgets.QLabel(self._motor_logic().get_unit(ax))
            unit_label.setMinimumSize(QtCore.QSize(26, 22))
            ax_layout.addWidget(unit_label)

        self._spinboxes['x'].setValue(self._step_x)
        self._spinboxes['y'].setValue(self._step_y)
        self._spinboxes['z'].setValue(self._step_z)

        self._spinboxes['x'].setMaximum(self._max_step_x*1.5)
        self._spinboxes['y'].setMaximum(self._max_step_y*1.5)
        self._spinboxes['z'].setMaximum(self._max_step_z*1.5)

        for ax, spinbox in self._spinboxes.items():
            spinbox.editingFinished.connect(self.__update_stat_var_callback(ax))

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
            self._disconnect_step_signals()
        elif self._mode == 'jog':
            self._disconnect_jog_signals()

        self._mw.abort.clicked.disconnect()
        self._mw.buttonGroup_mode.buttonClicked.disconnect()
        # self._mw.lineEdit_speed.editingFinished.disconnect()
        if self._mw.keyboard_checkbox.checkState == 2:
            self._mw.sigPressKeyBoard.disconnect()
            self._mw.sigReleaseKeyBoard.disconnect()
        self._mw.keyboard_checkbox.stateChanged.disconnect()
        self._mw.close()

        self._spinboxes['x'].editingFinished.disconnect()
        self._spinboxes['y'].editingFinished.disconnect()
        self._spinboxes['z'].editingFinished.disconnect()

    # def _change_speed(self, param_dict):
    #     self._motor_logic().set_velocity(param_dict)
    #
    # def _change_speed_x(self):
    #     new_speed = self._mw.lineEdit_speed.text().split(',')
    #     vel_min = self.constraints['x']['vel_min'][0]
    #     vel_max = self.constraints['x']['vel_max'][0]
    #     if vel_min <= new_speed <= vel_max:
    #         self._change_speed({'x': new_speed})
    #         self._xspeed = new_speed
    #     else:
    #         raise Exception('Speed does not match hardware constraints!')
    #
    # def _change_speed_y(self):
    #     new_speed = int(self._mw.lineEdit_speed_y.text())
    #     vel_min = self.constraints['y']['vel_min'][0]
    #     vel_max = self.constraints['y']['vel_max'][0]
    #     if vel_min <= new_speed <= vel_max:
    #         self._change_speed({'y': new_speed})
    #         self._yspeed = new_speed
    #     else:
    #         raise Exception('Speed does not match hardware constraints!')

    # TODO Status var _step_(xyz) should change value upon entering. Not upon press of a move button.
    def abort(self):
        self._motor_logic().abort()

    def move_relative(self, param_dict):
        self._motor_logic().move_rel(param_dict)

    def motor_x_move_negative(self):
        self._step_x = self._spinboxes['x'].value()
        self.move_relative({'x': -self._step_x})

    def motor_x_move_positive(self):
        self._step_x = self._spinboxes['x'].value()
        self.move_relative({'x': self._step_x})

    def motor_y_move_negative(self):
        self._step_y = self._spinboxes['y'].value()
        self.move_relative({'y': -self._step_y})

    def motor_y_move_positive(self):
        self._step_y = self._spinboxes['y'].value()
        self.move_relative({'y': self._step_y})

    def motor_z_move_negative(self):
        self._step_y = self._spinboxes['z'].value()
        self.move_relative({'z': -self._step_y})

    def motor_z_move_positive(self):
        self._step_y = self._spinboxes['z'].value()
        self.move_relative({'z': self._step_y})

    def motor_x_move_negative_jog(self):
        self.move_relative({'x': -self._max_step_x})

    def motor_x_move_positive_jog(self):
        self.move_relative({'x': self._max_step_x})

    def motor_y_move_negative_jog(self):
        self.move_relative({'y': -self._max_step_y})

    def motor_y_move_positive_jog(self):
        self.move_relative({'y': self._max_step_y})

    def motor_z_move_negative_jog(self):
        self.move_relative({'z': -self._max_step_z})

    def motor_z_move_positive_jog(self):
        self.move_relative({'z': self._max_step_z})

    @property
    def _button_mode(self):
        if self._mw.buttonGroup_mode.checkedId() == -2:
            return 'step'
        elif self._mw.buttonGroup_mode.checkedId() == -3:
            return 'jog'

    def _toggle_mode(self):
        if self._button_mode == 'step' and self._mode == 'jog':
            # print('Step mope')
            self._disconnect_jog_signals()
            self._connect_step_signals()
            self._mode = 'step'
            self._spinboxes['x'].setEnabled(True)
            self._spinboxes['z'].setEnabled(True)
            self._spinboxes['y'].setEnabled(True)
        elif self._button_mode == 'jog' and self._mode == 'step':
            # print('Jog mope')
            self._disconnect_step_signals()
            self._connect_jog_signals()
            self._mode = 'jog'
            self._spinboxes['x'].setEnabled(False)
            self._spinboxes['z'].setEnabled(False)
            self._spinboxes['y'].setEnabled(False)
        else:
            pass

    def _toggle_keyboard_control(self):
        if self._mw.keyboard_checkbox.checkState() == 2:
            self._mw.sigPressKeyBoard.connect(self.keyPressEvent)
            self._mw.sigReleaseKeyBoard.connect(self.keyReleaseEvent)
        else:
            self._mw.sigPressKeyBoard.disconnect()
            self._mw.sigReleaseKeyBoard.disconnect()

    def _disconnect_step_signals(self):
        self._mw.motor_x_move_negative.clicked.disconnect()
        self._mw.motor_x_move_positive.clicked.disconnect()
        self._mw.motor_y_move_negative.clicked.disconnect()
        self._mw.motor_y_move_positive.clicked.disconnect()
        self._mw.motor_z_move_negative.clicked.disconnect()
        self._mw.motor_z_move_positive.clicked.disconnect()

    def _connect_step_signals(self):
        self._mw.motor_x_move_negative.clicked.connect(self.motor_x_move_negative)
        self._mw.motor_x_move_positive.clicked.connect(self.motor_x_move_positive)
        self._mw.motor_y_move_negative.clicked.connect(self.motor_y_move_negative)
        self._mw.motor_y_move_positive.clicked.connect(self.motor_y_move_positive)
        self._mw.motor_z_move_negative.clicked.connect(self.motor_z_move_negative)
        self._mw.motor_z_move_positive.clicked.connect(self.motor_z_move_positive)

    def _disconnect_jog_signals(self):
        self._mw.motor_x_move_negative.pressed.disconnect()
        self._mw.motor_x_move_positive.pressed.disconnect()
        self._mw.motor_y_move_negative.pressed.disconnect()
        self._mw.motor_y_move_positive.pressed.disconnect()
        self._mw.motor_z_move_negative.pressed.disconnect()
        self._mw.motor_z_move_positive.pressed.disconnect()
        # and what when released
        self._mw.motor_x_move_negative.released.disconnect()
        self._mw.motor_x_move_positive.released.disconnect()
        self._mw.motor_y_move_negative.released.disconnect()
        self._mw.motor_y_move_positive.released.disconnect()
        self._mw.motor_z_move_negative.released.disconnect()
        self._mw.motor_z_move_positive.released.disconnect()

    def _connect_jog_signals(self):
        # define what happens when clicked
        self._mw.motor_x_move_negative.pressed.connect(self.motor_x_move_negative_jog)
        self._mw.motor_x_move_positive.pressed.connect(self.motor_x_move_positive_jog)
        self._mw.motor_y_move_negative.pressed.connect(self.motor_y_move_negative_jog)
        self._mw.motor_y_move_positive.pressed.connect(self.motor_y_move_positive_jog)
        self._mw.motor_z_move_negative.pressed.connect(self.motor_z_move_negative_jog)
        self._mw.motor_z_move_positive.pressed.connect(self.motor_z_move_positive_jog)
        # and what when released
        self._mw.motor_x_move_negative.released.connect(self.abort)
        self._mw.motor_x_move_positive.released.connect(self.abort)
        self._mw.motor_y_move_negative.released.connect(self.abort)
        self._mw.motor_y_move_positive.released.connect(self.abort)
        self._mw.motor_z_move_negative.released.connect(self.abort)
        self._mw.motor_z_move_positive.released.connect(self.abort)

    def keyPressEvent(self, event):
        """ Handles the passed keyboard events from the main window.

        @param object event: qtpy.QtCore.QEvent object.
        """

        modifiers = QtWidgets.QApplication.keyboardModifiers()

        if modifiers == QtCore.Qt.ControlModifier:
            if event.key() == QtCore.Qt.Key_Right and not event.isAutoRepeat():
                # print('x+')
                self.motor_x_move_positive_jog()
                event.accept()
            elif event.key() == QtCore.Qt.Key_Left and not event.isAutoRepeat():
                # print('x-')
                self.motor_x_move_negative_jog()
                event.accept()
            elif event.key() == QtCore.Qt.Key_Up and not event.isAutoRepeat():
                # print('y+')
                self.motor_y_move_positive_jog()
                event.accept()
            elif event.key() == QtCore.Qt.Key_Down and not event.isAutoRepeat():
                # print('y-')
                self.motor_y_move_negative_jog()
                event.accept()
            elif event.key() == QtCore.Qt.Key_PageUp and not event.isAutoRepeat():
                # print('z+')
                self.motor_z_move_positive_jog()
                event.accept()
            elif event.key() == QtCore.Qt.Key_PageDown and not event.isAutoRepeat():
                # print('z-')
                self.motor_z_move_negative_jog()
                event.accept()
            elif event.key() == QtCore.Qt.Key_X and not event.isAutoRepeat():
                print('x')
                if self._manager.tree['loaded']['logic']['optimizer']:
                    print('true')
                    self._manager.tree['loaded']['logic']['optimizer'].start_refocus()
            else:
                event.ignore()
                # print(event.key())
        elif modifiers == QtCore.Qt.ShiftModifier:
            if event.key() == QtCore.Qt.Key_Right and not event.isAutoRepeat():
                # print('Sx+')
                self.motor_x_move_positive()
                event.accept()
            elif event.key() == QtCore.Qt.Key_Left and not event.isAutoRepeat():
                # print('Sx-')
                self.motor_x_move_negative()
                event.accept()
            elif event.key() == QtCore.Qt.Key_Up and not event.isAutoRepeat():
                # print('Sy+')
                self.motor_y_move_positive()
                event.accept()
            elif event.key() == QtCore.Qt.Key_Down and not event.isAutoRepeat():
                # print('Sy-')
                self.motor_y_move_negative()
                event.accept()
            elif event.key() == QtCore.Qt.Key_PageUp and not event.isAutoRepeat():
                # print('Sz+')
                self.motor_z_move_positive()
                event.accept()
            elif event.key() == QtCore.Qt.Key_PageDown and not event.isAutoRepeat():
                # print('Sz-')
                self.motor_z_move_negative()
                event.accept()
            elif event.key() == QtCore.Qt.Key_Space and not event.isAutoRepeat():
                # print('Sx+ released')
                self.abort()
                event.accept()
            else:
                event.ignore()
        elif event.key() == QtCore.Qt.Key_Control or event.key() == QtCore.Qt.Key_Shift and not event.isAutoRepeat():
            # if control pressed, set focus on control label to not operate in a lineEdit
            # print('focs')
            self._mw.label_controlparam.setFocus()
            event.accept()
        else:
            # print('igno press')
            event.ignore()

    def keyReleaseEvent(self, event):
        """ Handles the passed keyboard events from the main window.

        @param object event: qtpy.QtCore.QEvent object.
        """

        modifiers = QtWidgets.QApplication.keyboardModifiers()

        if modifiers == QtCore.Qt.ControlModifier:
            if event.key() == QtCore.Qt.Key_Right and not event.isAutoRepeat():
                # print('x+ released')
                event.accept()
                self.abort()
                return
            elif event.key() == QtCore.Qt.Key_Left and not event.isAutoRepeat():
                # print('x- released')
                event.accept()
                self.abort()
                return
            elif event.key() == QtCore.Qt.Key_Up and not event.isAutoRepeat():
                # print('y+ released')
                event.accept()
                self.abort()
                return
            elif event.key() == QtCore.Qt.Key_Down and not event.isAutoRepeat():
                # print('y- released')
                event.accept()
                self.abort()
                return
            elif event.key() == QtCore.Qt.Key_PageUp and not event.isAutoRepeat():
                # print('z+ released')
                event.accept()
                self.abort()
            elif event.key() == QtCore.Qt.Key_PageDown and not event.isAutoRepeat():
                # print('z- released')
                event.accept()
                self.abort()
                return
            elif event.key() == QtCore.Qt.Key_Control and not event.isAutoRepeat():
                # print('Ctr realesed')
                event.accept()
                self.abort()
                return
        elif modifiers == QtCore.Qt.ShiftModifier:
            if event.key() == QtCore.Qt.Key_Space and not event.isAutoRepeat():
                # print('Sx+ released')
                event.accept()
                self.abort()
                return
            else:
                event.ignore()
        else:
            event.ignore()

    def __update_stat_var_callback(self, ax):
        def callback():
            if ax == 'x':
                self._step_x = self._spinboxes['x'].value()
            if ax == 'y':
                self._step_y = self._spinboxes['y'].value()
            if ax == 'z':
                self._step_z = self._spinboxes['z'].value()
        return callback
