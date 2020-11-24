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
from core.connector import Connector
from core.statusvariable import StatusVar
from gui.guibase import GUIBase
from qtpy import QtWidgets, QtCore, QtGui
from .switch_state_widgets import SwitchRadioButtonWidget, ToggleSwitchWidget


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
        widget.setFixedSize(1, 1)
        self.setCentralWidget(widget)

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


class SwitchGui(GUIBase):
    """ A graphical interface to switch a hardware by hand.
    """

    # declare connectors
    switchlogic = Connector(interface='SwitchLogic')

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mw = None
        self._widgets = dict()

    def on_activate(self):
        """ Create all UI objects and show the window.
        """
        self._mw = SwitchMainWindow()
        self.restoreWindowPos(self._mw)
        try:
            self._mw.switch_view_actions[self._switch_style].setChecked(True)
        except IndexError:
            self._mw.switch_view_actions[0].setChecked(True)
            self._switch_style = SwitchStyle(0)
        self._mw.action_view_highlight_state.setChecked(
            self._state_colorscheme == StateColorScheme.HIGHLIGHT
        )
        self._mw.action_view_alt_toggle_style.setChecked(self._alt_toggle_switch_style)
        self._mw.setWindowTitle(f'qudi: {self.switchlogic().device_name.title()}')

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
        self.show()

    def on_deactivate(self):
        """ Hide window empty the GUI and disconnect signals
        """
        self.switchlogic().sigSwitchesChanged.disconnect(self._switches_updated)
        self.switchlogic().sigWatchdogToggled.disconnect(self._watchdog_updated)
        self._mw.action_view_highlight_state.triggered.disconnect()
        self._mw.action_view_alt_toggle_style.triggered.disconnect()
        self._mw.switch_view_action_group.triggered.disconnect()
        self._mw.action_periodic_state_check.toggled.disconnect()
        self.sigSwitchChanged.disconnect()

        self.saveWindowPos(self._mw)
        self._delete_switches()
        self._mw.close()

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
            self._mw.close()
            self._delete_switches()
            self._mw.centralWidget().setFixedSize(1, 1)
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
