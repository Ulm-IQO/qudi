# -*- coding: utf-8 -*-
"""
This file contains the Qudi console GUI module.

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
from qtpy import uic
import sip


class SwitchMainWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self, **kwargs):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_switch_gui.ui')

        # Load it
        super().__init__(**kwargs)
        uic.loadUi(ui_file, self)


class SwitchGui(GUIBase):
    """ A graphical interface to switch a hardware by hand.
    """

    # declare connectors
    switchlogic = Connector(interface='SwitchLogic')

    # declare signals
    sigSwitchChanged = QtCore.Signal(str, str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mw = SwitchMainWindow()
        self._widgets = dict()
        self._highlight_format = 'QRadioButton {color: green; font-weight: bold;}'
        self._lowlight_format = 'QRadioButton {color: red; font-weight: normal;}'

    def on_activate(self):
        """ Create all UI objects and show the window.
        """
        self.restoreWindowPos(self._mw)
        self._populate_switches()

        self.sigSwitchChanged.connect(self.switchlogic().set_state, QtCore.Qt.QueuedConnection)
        self.switchlogic().sigSwitchesChanged.connect(
            self._switches_updated, QtCore.Qt.QueuedConnection
        )

        self.show()

    def on_deactivate(self):
        """ Hide window empty the GUI and disconnect signals
        """
        self.switchlogic().sigSwitchesChanged.disconnect(self._switches_updated)
        self.sigSwitchChanged.disconnect()

        self._depopulate_switches()

        self.saveWindowPos(self._mw)
        self._mw.close()

    def show(self):
        """ Make sure that the window is visible and at the top.
        """
        self._mw.show()

    def _populate_switches(self):
        """ Dynamically build the gui.
        @return: None
        """
        # For each switch that the logic has, add a widget to the GUI to show its state
        self._mw.switch_groupBox.setTitle(self.switchlogic().device_name)
        self._mw.switch_groupBox.setAlignment(QtCore.Qt.AlignLeft)
        self._mw.switch_groupBox.setFlat(False)
        vertical_layout = QtWidgets.QVBoxLayout(self._mw.switch_groupBox)
        self._widgets = dict()
        for switch in self.switchlogic().available_states:
            vertical_layout.addWidget(self._add_radio_widget(switch))

        self._mw.switch_groupBox.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                               QtWidgets.QSizePolicy.MinimumExpanding)
        self._mw.switch_groupBox.updateGeometry()
        self._switches_updated(self.switchlogic().states)

    def _add_radio_widget(self, switch):
        """ Helper function to create a widget with radio buttons per switch.
        @param str switch: the switch name (in switchlogic) of the switch to be displayed
        @return QWidget: widget containing the radio buttons and the label
        """
        button_group = QtWidgets.QButtonGroup()

        label = QtWidgets.QLabel(switch + ':')
        label.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        label.setMinimumWidth(100)

        widget = QtWidgets.QWidget()
        widget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(label)

        names = self.switchlogic().available_states[switch]
        self._widgets[switch] = dict()
        for state in names:
            button = QtWidgets.QRadioButton(state)
            button.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

            button_group.addButton(button)
            self._widgets[switch][state] = button

            button.toggled.connect(lambda button_state, switch_origin=switch, state_origin=state:
                                   self._button_toggled(switch_origin, state_origin, button_state))
            layout.addWidget(button)

        layout.setAlignment(QtCore.Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        widget.setLayout(layout)

        return widget

    def _depopulate_switches(self):
        """ Delete all the buttons from the group box and remove the layout.
        @return: None
        """
        for widgets in self._widgets.values():
            for widget in widgets.values():
                widget.disconnect()
        self._widgets = dict()

        vertical_layout = self._mw.switch_groupBox.layout()
        if vertical_layout is not None:
            for i in reversed(range(vertical_layout.count())):
                vertical_layout.itemAt(i).widget().setParent(None)
            sip.delete(vertical_layout)

    def _button_toggled(self, switch, state, is_set):
        """ Helper function that is connected to the GUI interaction.
        A GUI change is transmitted to the logic and the visual indicators are changed.
        @param str switch: switch name of the GUI element that was changed
        @param str state: new state name of the switch
        @param bool is_set: indicator if this particular state was switched to True
        @return: None
        """
        if not is_set:
            return
        self.sigSwitchChanged.emit(switch, state)

    def _switches_updated(self, states):
        """ Helper function to update the GUI on a change of the states in the logic.
        This function is connected to the signal coming from the switchlogic signaling a change in states.
        @param dict states: The state dict of the form {"switch": "state"}
        @return: None
        """
        for switch, state in states.items():
            for name, widget in self._widgets[switch].items():
                widget.blockSignals(True)
                widget.setChecked(name == state)
                widget.setStyleSheet(self._lowlight_format if name == state else self._highlight_format)
                widget.blockSignals(False)
