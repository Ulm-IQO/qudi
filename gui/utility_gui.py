# -*- coding: utf-8 -*-
"""
This file contains the qudi switch GUI module.

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

from enum import IntEnum

import numpy as np

from core.connector import Connector
from core.statusvariable import StatusVar
from gui.guibase import GUIBase
from qtpy import QtWidgets, QtCore, QtGui
from core.configoption import ConfigOption
from qtwidgets.scientific_spinbox import ScienDSpinBox, ScienSpinBox
from .switch.switch_state_widgets import SwitchRadioButtonWidget, ToggleSwitchWidget

from gui.colordefs import QudiPalettePale as palette
from .switch.switch_gui import SwitchGui as SwitchGui


class SwitchStyle(IntEnum):
    TOGGLE_SWITCH = 0
    RADIO_BUTTON = 1


class StateColorScheme(IntEnum):
    DEFAULT = 0
    HIGHLIGHT = 1


class SwitchMainWindow(QtWidgets.QMainWindow):
    """ Main Window for the SwitchGui module """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('qudi: <INSERT HARDWARE NAME>')
        # Create main layout and central widget
        self.main_layout = QtWidgets.QGridLayout()
        self.main_layout.setColumnStretch(1, 1)
        self.main_layout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.main_layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        widget = QtWidgets.QWidget()
        widget.setLayout(self.main_layout)
        #widget.setFixedSize(1, 1)
        self._dockwidget = QtWidgets.QDockWidget()
        self._dockwidget.setWidget(widget)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self._dockwidget)

        self.pid_layout = QtWidgets.QGridLayout()
        # self.main_layout.setColumnStretch(1, 1)
        # self.main_layout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        # self.main_layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self._pid_dockwidget = QtWidgets.QDockWidget()
        self.pid_widget = QtWidgets.QWidget()
        self.pid_widget.setLayout(self.pid_layout)
        # self.widget.setFixedSize(1, 1)
        self._pid_dockwidget.setWidget(self.pid_widget)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self._pid_dockwidget)

        self.powermeter_layout = QtWidgets.QGridLayout()
        # self.main_layout.setColumnStretch(1, 1)
        # self.main_layout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        # self.main_layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self._powermeter_dockwidget = QtWidgets.QDockWidget()
        self.powermeter_widget = QtWidgets.QWidget()
        self.powermeter_widget.setLayout(self.powermeter_layout)
        # self.widget.setFixedSize(1, 1)
        self._powermeter_dockwidget.setWidget(self.powermeter_widget)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._powermeter_dockwidget)

        # Create QActions and menu bar
        menu_bar = QtWidgets.QMenuBar()
        self.setMenuBar(menu_bar)

        menu = menu_bar.addMenu('Menu')
        self.action_close = QtWidgets.QAction('Close Window')
        self.action_close.setCheckable(False)
        self.action_close.setIcon(QtGui.QIcon('artwork/icons/oxygen/22x22/application-exit.png'))
        self.addAction(self.action_close)
        menu.addAction(self.action_close)

        menu = menu_bar.addMenu('View')
        self.action_periodic_state_check = QtWidgets.QAction('Periodic State Checking')
        self.action_periodic_state_check.setCheckable(True)
        menu.addAction(self.action_periodic_state_check)
        separator = menu.addSeparator()
        separator.setText('Switch Appearance')
        self.switch_view_actions = [QtWidgets.QAction('use toggle switches'),
                                    QtWidgets.QAction('use radio buttons')]
        self.switch_view_action_group = QtWidgets.QActionGroup(self)
        for action in self.switch_view_actions:
            action.setCheckable(True)
            self.switch_view_action_group.addAction(action)
            menu.addAction(action)
        self.action_view_highlight_state = QtWidgets.QAction('highlight state labels')
        self.action_view_highlight_state.setCheckable(True)
        menu.addAction(self.action_view_highlight_state)
        self.action_view_alt_toggle_style = QtWidgets.QAction('alternative toggle switch')
        self.action_view_alt_toggle_style.setCheckable(True)
        menu.addAction(self.action_view_alt_toggle_style)

        # close window upon triggering close action
        self.action_close.triggered.connect(self.close)
        return




class UtilityGui(GUIBase):
    """ A graphical interface to switch a hardware by hand.
    """
    # declare connectors
    switchlogic = Connector(interface='SwitchLogic')
    pidlogic = Connector(interface='PIDLogic', optional=True)


    # declare status variables
    _switch_style = StatusVar(name='switch_style',
                              default=SwitchStyle.TOGGLE_SWITCH,
                              representer=lambda _, x: int(x),
                              constructor=lambda _, x: SwitchStyle(x))
    _state_colorscheme = StatusVar(name='state_colorscheme',
                                   default=StateColorScheme.DEFAULT,
                                   representer=lambda _, x: int(x),
                                   constructor=lambda _, x: StateColorScheme(x))
    _alt_toggle_switch_style = StatusVar(name='alt_toggle_switch_style', default=False)

    # declare signals
    sigSwitchChanged = QtCore.Signal(str, str)

    limit = ConfigOption(name='limit', default=4000, missing='nothing')
    sigStart = QtCore.Signal()
    sigStop = QtCore.Signal()


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mw = None
        self._widgets = dict()


    def on_activate(self):
        """ Create all UI objects and show the window.
        """
        self._mw = SwitchMainWindow()
        self.on_activate_switch()
        self.on_activate_pid()
        self.on_activate_powermeter()
        self.restoreWindowPos(self._mw)
        self._mw.setWindowTitle('qudi Utility')
        self.show()

    def on_activate_pid(self):
        self.history = np.empty([1, 100])
        self.history[:] = np.NaN

        self._pid_logic = self.pidlogic()

        self._mw.setDockNestingEnabled(True)

        self.state_switch_widget = ToggleSwitchWidget(switch_states=['manual', 'PID'], thumb_track_ratio=0.9)
        self.loop_state_switch_widget = ToggleSwitchWidget(switch_states=['logging disabled', 'logging enabled'], thumb_track_ratio=0.9)
        self._mw.pid_layout.addWidget(self.state_switch_widget, 0, 0, 1, 2)
        self._mw.pid_layout.addWidget(self.loop_state_switch_widget, 0, 2, 1, 2)

        self.setpointDoubleSpinBox = ScienSpinBox()
        self.manualDoubleSpinBox = ScienSpinBox()
        self._mw.pid_layout.addWidget(QtWidgets.QLabel("Setpoint"), 1, 0)
        self._mw.pid_layout.addWidget(QtWidgets.QLabel("Manual Values"), 1, 2)
        self._mw.pid_layout.addWidget(self.setpointDoubleSpinBox, 1, 1)
        self._mw.pid_layout.addWidget(self.manualDoubleSpinBox, 1, 3)

        self._mw.pid_layout.addWidget(QtWidgets.QLabel("Controll Value"), 2, 0)
        self._mw.pid_layout.addWidget(QtWidgets.QLabel("Setpoint"), 2, 1)
        self._mw.pid_layout.addWidget(QtWidgets.QLabel("Process Value"), 2, 2)
        self._mw.pid_layout.addWidget(QtWidgets.QLabel("Mean | Deviation"), 2, 3)

        self._mw.control_value_Label = QtWidgets.QLabel()
        self._mw.setpoint_Label = QtWidgets.QLabel()
        self._mw.process_value_Label = QtWidgets.QLabel()
        self._mw.deviation_value_Label = QtWidgets.QLabel()

        font = QtGui.QFont()
        font.setBold(True)
        font.setPointSize(16)
        # font.setPixelSize(int(round(0.75 * QtWidgets.QLineEdit().sizeHint().height())))
        self._mw.control_value_Label.setFont(font)
        self._mw.setpoint_Label.setFont(font)
        self._mw.process_value_Label.setFont(font)
        self._mw.deviation_value_Label.setFont(font)

        self._mw.pid_layout.addWidget(self._mw.control_value_Label, 3, 0, 1, 1)
        self._mw.pid_layout.addWidget(self._mw.setpoint_Label, 3, 1, 1, 1)
        self._mw.pid_layout.addWidget(self._mw.process_value_Label, 3, 2, 1, 1)
        self._mw.pid_layout.addWidget(self._mw.deviation_value_Label, 3, 3, 1, 1)
        # Update Values from logic

        self.setpointDoubleSpinBox.setValue(self._pid_logic.get_setpoint())
        self.manualDoubleSpinBox.setValue(self._pid_logic.get_manual_value())

        if self._pid_logic._controller.get_enabled():
            self.state_switch_widget.set_state('PID')
        else:
            self.state_switch_widget.set_state('manual')

        if self._pid_logic.get_enabled():
            self.loop_state_switch_widget.set_state('logging enabled')
        else:
            self.loop_state_switch_widget.set_state('logging disabled')

        self.setpointDoubleSpinBox.valueChanged.connect(self.setpointChanged)
        self.manualDoubleSpinBox.valueChanged.connect(self.manualValueChanged)


        self.state_switch_widget.sigStateChanged.connect(self.pidEnabledChanged)
        self.loop_state_switch_widget.sigStateChanged.connect(self.loopEnabledChanged)
        self.sigStart.connect(self._pid_logic.startLoop)
        self.sigStop.connect(self._pid_logic.stopLoop)

        self._pid_logic.sigUpdateDisplay.connect(self.updateData)

    def on_activate_switch(self):

        try:
            self._mw.switch_view_actions[self._switch_style].setChecked(True)
        except IndexError:
            self._mw.switch_view_actions[0].setChecked(True)
            self._switch_style = SwitchStyle(0)
        self._mw.action_view_highlight_state.setChecked(
            self._state_colorscheme == StateColorScheme.HIGHLIGHT
        )
        self._mw.action_view_alt_toggle_style.setChecked(self._alt_toggle_switch_style)

        self._populate_switches()

        self.sigSwitchChanged.connect(self.switchlogic().set_state, QtCore.Qt.QueuedConnection)
        self._mw.action_periodic_state_check.toggled.connect(
            self.switchlogic().toggle_watchdog, QtCore.Qt.QueuedConnection
        )
        self._mw.switch_view_action_group.triggered.connect(self._update_switch_appearance)
        self._mw.action_view_highlight_state.triggered.connect(self._update_state_colorscheme)
        self._mw.action_view_alt_toggle_style.triggered.connect(self._update_toggle_switch_style)
        self.switchlogic().sigWatchdogToggled.connect(
            self._watchdog_updated, QtCore.Qt.QueuedConnection
        )
        self.switchlogic().sigSwitchesChanged.connect(
            self._switches_updated, QtCore.Qt.QueuedConnection
        )

        self._watchdog_updated(self.switchlogic().watchdog_active)
        self._switches_updated(self.switchlogic().states)
        self._update_state_colorscheme()


    def on_activate_powermeter(self):
        self.wavelength_switch_widget = ToggleSwitchWidget(switch_states=['532', '737'], thumb_track_ratio=0.9)
        self._mw.powermeter_layout.addWidget(self.wavelength_switch_widget, 0, 1, 1, 1)
        self._mw.powermeter_layout.addWidget(QtWidgets.QLabel("Wavelenght"), 0, 0)
        self._mw.powermeter_layout.addWidget(QtWidgets.QLabel("Power"), 1, 0)

        font = QtGui.QFont()
        font.setBold(True)
        font.setPointSize(18)

        self._mw.power_value_Label = QtWidgets.QLabel()

        self._mw.power_value_Label.setFont(font)
        self._mw.powermeter_layout.addWidget(self._mw.power_value_Label, 2, 0, 1, 2)

        self._mw.power_value_Label.setText("250 µW")




    def on_deactivate(self):
        """ Hide window empty the GUI and disconnect signals
        """
        self.on_deactivate_switch()
        self.on_deactivate_pid()
        self.on_deactivate_powermeter()
        self._mw.close()

    def on_deactivate_switch(self):
        self.switchlogic().sigSwitchesChanged.disconnect(self._switches_updated)
        self.switchlogic().sigWatchdogToggled.disconnect(self._watchdog_updated)
        self._mw.action_view_highlight_state.triggered.disconnect()
        self._mw.action_view_alt_toggle_style.triggered.disconnect()
        self._mw.switch_view_action_group.triggered.disconnect()
        self._mw.action_periodic_state_check.toggled.disconnect()
        self.sigSwitchChanged.disconnect()

        self.saveWindowPos(self._mw)
        self._delete_switches()

    def on_deactivate_pid(self):
        self.sigStart.disconnect()
        self.sigStop.disconnect()
        self._pid_logic.sigUpdateDisplay.disconnect(self.updateData)
        self.setpointDoubleSpinBox.valueChanged.disconnect(self.setpointChanged)
        self.manualDoubleSpinBox.valueChanged.disconnect(self.manualValueChanged)
        self.state_switch_widget.sigStateChanged.disconnect(self.pidEnabledChanged)
        self.loop_state_switch_widget.sigStateChanged.disconnect(self.loopEnabledChanged)

    def on_deactivate_powermeter(self):
        pass

    def show(self):
        """ Make sure that the window is visible and at the top.
        """
        self._mw.show()

    def _populate_switches(self):
        """ Dynamically build the gui
        """
        self._widgets = dict()
        for ii, (switch, states) in enumerate(self.switchlogic().available_states.items()):
            label = self._get_switch_label(switch)
            if len(states) > 2 or self._switch_style == SwitchStyle.RADIO_BUTTON:
                switch_widget = SwitchRadioButtonWidget(switch_states=states)
                self._widgets[switch] = (label, switch_widget)
                self._mw.main_layout.addWidget(self._widgets[switch][0], ii, 0)
                self._mw.main_layout.addWidget(self._widgets[switch][1], ii, 1)
                switch_widget.sigStateChanged.connect(self.__get_state_update_func(switch))
            elif self._switch_style == SwitchStyle.TOGGLE_SWITCH:
                if self._alt_toggle_switch_style:
                    switch_widget = ToggleSwitchWidget(switch_states=states, thumb_track_ratio=1.35)
                else:
                    switch_widget = ToggleSwitchWidget(switch_states=states, thumb_track_ratio=0.9)
                self._widgets[switch] = (label, switch_widget)
                switch_widget.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                                            QtWidgets.QSizePolicy.Fixed)
                self._mw.main_layout.addWidget(self._widgets[switch][0], ii, 0)
                self._mw.main_layout.addWidget(switch_widget, ii, 1)
                switch_widget.sigStateChanged.connect(self.__get_state_update_func(switch))

    @staticmethod
    def _get_switch_label(switch):
        """ Helper function to create a QLabel for a single switch.

        @param str switch: The name of the switch to create the label for
        @return QWidget: QLabel with switch name
        """
        label = QtWidgets.QLabel(f'{switch}:')
        font = QtGui.QFont()
        font.setBold(True)
        font.setPointSize(11)
        # font.setPixelSize(int(round(0.75 * QtWidgets.QLineEdit().sizeHint().height())))
        label.setFont(font)
        # label.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
        #                     QtWidgets.QSizePolicy.MinimumExpanding)
        label.setMinimumWidth(label.sizeHint().width())
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        return label

    def _delete_switches(self):
        """ Delete all the buttons from the main layout. """
        for switch in reversed(tuple(self._widgets)):
            label, widget = self._widgets[switch]
            widget.sigStateChanged.disconnect()
            self._mw.main_layout.removeWidget(label)
            self._mw.main_layout.removeWidget(widget)
            label.setParent(None)
            widget.setParent(None)
            del self._widgets[switch]
            label.deleteLater()
            widget.deleteLater()

    @QtCore.Slot(dict)
    def _switches_updated(self, states):
        """ Helper function to update the GUI on a change of the states in the logic.
        This function is connected to the signal coming from the switchlogic signaling a change in states.
        @param dict states: The state dict of the form {"switch": "state"}
        @return: None
        """
        for switch, state in states.items():
            self._widgets[switch][1].set_state(state)

    @QtCore.Slot(bool)
    def _watchdog_updated(self, enabled):
        """ Update the menu action accordingly if the watchdog has been (de-)activated.

        @param bool enabled: Watchdog active (True) or inactive (False)
        """
        if enabled != self._mw.action_periodic_state_check.isChecked():
            self._mw.action_periodic_state_check.blockSignals(True)
            self._mw.action_periodic_state_check.setChecked(enabled)
            self._mw.action_periodic_state_check.blockSignals(False)

    def _update_switch_appearance(self, action):
        index = self._mw.switch_view_actions.index(action)
        if index != self._switch_style:
            self._switch_style = SwitchStyle(index)
            self._delete_switches()
            self._populate_switches()
            self._switches_updated(self.switchlogic().states)
            self._update_state_colorscheme()
            self._mw.show()

    def _update_state_colorscheme(self):
        self._state_colorscheme = StateColorScheme(self._mw.action_view_highlight_state.isChecked())
        if self._state_colorscheme is StateColorScheme.HIGHLIGHT:
            checked_color = self._mw.palette().highlight().color()
            unchecked_color = None
        else:
            checked_color = None
            unchecked_color = None
        for widget in self._widgets.values():
            widget[1].set_state_colors(unchecked_color, checked_color)
            widget[1].update()

    @QtCore.Slot(bool)
    def _update_toggle_switch_style(self, checked):
        if self._alt_toggle_switch_style != checked:
            self._alt_toggle_switch_style = checked
            if self._switch_style == SwitchStyle.TOGGLE_SWITCH:
                self._mw.close()
                self._delete_switches()
                self._mw.centralWidget().setFixedSize(1, 1)
                self._populate_switches()
                self._switches_updated(self.switchlogic().states)
                self._update_state_colorscheme()
                self._mw.show()

    def __get_state_update_func(self, switch):
        def update_func(state):
            self.sigSwitchChanged.emit(switch, state)
        return update_func



    def setpointChanged(self):
        self._pid_logic.set_setpoint(self.setpointDoubleSpinBox.value())
        self.history[:] = np.NaN

    def manualValueChanged(self):
        self._pid_logic.set_manual_value(self.manualDoubleSpinBox.value())

    def pidEnabledChanged(self):
        if self.state_switch_widget.switch_state == 'PID':
            self._pid_logic._controller.set_enabled(True)
            self.history[:] = np.NaN
        else:
            self._pid_logic._controller.set_enabled(False)
            self.history[:] = np.NaN


    def loopEnabledChanged(self):
        if self.loop_state_switch_widget.switch_state == 'logging enabled':
            self.sigStart.emit()
            self.history[:] = np.NaN
        else:
            self.sigStop.emit()
            self.history[:] = np.NaN

    def updateData(self):
        if self._pid_logic.get_enabled():
            self._mw.process_value_Label.setText(
                '<font color={0}>{1:,.3f}</font>'.format(
                palette.c1.name(),
                self._pid_logic.history[0, -1]))
            self._mw.control_value_Label.setText(
                '<font color={0}>{1:,.3f}</font>'.format(
                palette.c3.name(),
                self._pid_logic.history[1, -1]))
            self._mw.setpoint_Label.setText(
                '<font color={0}>{1:,.3f}</font>'.format(
                palette.c2.name(),
                self._pid_logic.history[2, -1]))

            self.history = np.roll(self.history, -1, axis=1)
            self.history[0, -1] = self._pid_logic.history[0, -1]

            self._mw.deviation_value_Label.setText(
                '<font color={0}>{1:,.3f}+-{2:,.3f}</font>'.format(
                palette.c2.name(),
                np.nanmean(self.history-self._pid_logic.history[2, -1]),
                    np.nanstd(self.history-self._pid_logic.history[2, -1])))

            if self._pid_logic.history[1, -1]>self.limit:
                self._mw._pid_dockwidget.setStyleSheet('background-color: #903535;')

            else:
                self._mw._pid_dockwidget.setStyleSheet('background-color: #353535;')
