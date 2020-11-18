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

from core.connector import Connector
from gui.guibase import GUIBase
from qtpy import QtWidgets, QtCore, QtGui
from .switch_state_widgets import SwitchRadioButtonWidget


class SwitchMainWindow(QtWidgets.QMainWindow):
    """ Main Window for the SwitchGui module """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Create main layout within group box as central widget
        layout = QtWidgets.QGridLayout()
        layout.setColumnStretch(1, 1)
        self.group_box = QtWidgets.QGroupBox('Name of Switch Hardware')
        self.group_box.setAlignment(QtCore.Qt.AlignLeft)
        self.group_box.setLayout(layout)
        self.setCentralWidget(self.group_box)
        self.setWindowTitle('qudi: Switches')

        # Create QActions and menu bar
        self.action_periodic_state_check = QtWidgets.QAction('Periodic State Checking')
        self.action_periodic_state_check.setCheckable(True)
        self.action_close = QtWidgets.QAction('Close Window')
        self.action_close.setCheckable(False)
        self.action_close.setIcon(QtGui.QIcon('artwork/icons/oxygen/22x22/application-exit.png'))
        self.addAction(self.action_periodic_state_check)
        self.addAction(self.action_close)
        menu_bar = QtWidgets.QMenuBar()
        menu = menu_bar.addMenu('Menu')
        menu.addAction(self.action_periodic_state_check)
        menu.addSeparator()
        menu.addAction(self.action_close)
        self.setMenuBar(menu_bar)

        # close window upon triggering close action
        self.action_close.triggered.connect(self.close)
        return


class SwitchGui(GUIBase):
    """ A graphical interface to switch a hardware by hand.
    """

    # declare connectors
    switchlogic = Connector(interface='SwitchLogic')

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

        self._populate_switches()

        self.sigSwitchChanged.connect(self.switchlogic().set_state, QtCore.Qt.QueuedConnection)
        self._mw.action_periodic_state_check.toggled.connect(
            self.switchlogic().toggle_watchdog, QtCore.Qt.QueuedConnection
        )
        self.switchlogic().sigWatchdogToggled.connect(
            self._watchdog_updated, QtCore.Qt.QueuedConnection
        )
        self.switchlogic().sigSwitchesChanged.connect(
            self._switches_updated, QtCore.Qt.QueuedConnection
        )

        self._watchdog_updated(self.switchlogic().watchdog_active)
        self._switches_updated(self.switchlogic().states)
        self._mw.setFixedSize(self._mw.sizeHint())
        self.show()

    def on_deactivate(self):
        """ Hide window empty the GUI and disconnect signals
        """
        self.switchlogic().sigSwitchesChanged.disconnect(self._switches_updated)
        self.switchlogic().sigWatchdogToggled.disconnect(self._watchdog_updated)
        self._mw.action_periodic_state_check.toggled.disconnect()
        self.sigSwitchChanged.disconnect()

        self._depopulate_switches()

        self.saveWindowPos(self._mw)
        self._mw.close()

    def show(self):
        """ Make sure that the window is visible and at the top.
        """
        self._mw.show()

    def _populate_switches(self):
        """ Dynamically build the gui
        """
        # For each switch that the logic has, add a widget to the GUI to show its state
        self._mw.group_box.setTitle(self.switchlogic().device_name)
        layout = self._mw.group_box.layout()
        self._widgets = dict()
        for ii, (switch, states) in enumerate(self.switchlogic().available_states.items()):
            self._widgets[switch] = (
                self._get_switch_label(switch),
                SwitchRadioButtonWidget(switch_name=switch, switch_states=states)
            )
            layout.addWidget(self._widgets[switch][0], ii, 0)
            layout.addWidget(self._widgets[switch][1], ii, 1)
            self._widgets[switch][1].sigStateChanged.connect(self.__get_state_update_func(switch))

    @staticmethod
    def _get_switch_label(switch):
        """ Helper function to create a QLabel for a single switch.

        @param str switch: The name of the switch to create the label for
        @return QWidget: QLabel with switch name
        """
        label = QtWidgets.QLabel(f'{switch}:')
        font = QtGui.QFont()
        font.setBold(True)
        label.setFont(font)
        # label.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
        #                     QtWidgets.QSizePolicy.MinimumExpanding)
        label.setMinimumWidth(label.sizeHint().width())
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        return label

    def _depopulate_switches(self):
        """ Delete all the buttons from the group box and remove the layout.
        @return: None
        """
        layout = self._mw.group_box.layout()
        for switch in reversed(self._widgets):
            label, widget = self._widgets[switch]
            widget.sigStateChanged.disconnect()
            layout.removeWidget(label)
            layout.removeWidget(widget)
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

    def __get_state_update_func(self, switch):
        def update_func(state):
            self.sigSwitchChanged.emit(switch, state)
        return update_func
