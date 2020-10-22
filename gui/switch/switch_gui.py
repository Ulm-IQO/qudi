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
from core.configoption import ConfigOption
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
        self.show()


class SwitchGui(GUIBase):
    """ A grephical interface to mofe switches by hand and change their calibration.
    """

    # declare connectors
    switchlogic = Connector(interface='SwitchLogic')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mw = SwitchMainWindow()
        self._widgets = dict()
        self._highlight_format = 'QRadioButton {color: green; font-weight: bold;}'
        self._lowlight_format = 'QRadioButton {color: red; font-weight: normal;}'

    def on_activate(self):
        """
        Create all UI objects and show the window.
        """
        self.restoreWindowPos(self._mw)
        self._populate_switches()
        self.show()

        self.switchlogic().sig_switch_updated.connect(self._switch_updated, QtCore.Qt.QueuedConnection)

    def on_deactivate(self):
        """
        Hide window empty the GUI and disconnect signals
        """
        self.switchlogic().sig_switch_updated.disconnect(self._switch_updated)

        self._depopulate_switches()

        self.saveWindowPos(self._mw)
        self._mw.close()

    def show(self):
        """
        Make sure that the window is visible and at the top.
        """
        self._mw.show()

    def _populate_switches(self):
        """
        Dynamically build the gui.
        By default check boxes are used, but by setting the ConfigOption radio_buttons=True
        #coloured radio buttons can be used.
        The latter is useful when working with laser protection goggles in the lab.
            @return: None
        """
        # For each switch that the logic has, add a widget to the GUI to show its state
        self._mw.switch_groupBox.setTitle(self.switchlogic().name)
        self._mw.switch_groupBox.setAlignment(QtCore.Qt.AlignLeft)
        self._mw.switch_groupBox.setFlat(False)
        vertical_layout = QtWidgets.QVBoxLayout(self._mw.switch_groupBox)
        self._widgets = dict()
        for switch in self.switchlogic().names_of_states:
            vertical_layout.addWidget(self._add_radio_widget(switch))

        self._mw.switch_groupBox.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                               QtWidgets.QSizePolicy.MinimumExpanding)
        self._mw.switch_groupBox.updateGeometry()
        self._switch_updated(self.switchlogic().states)

    def _add_radio_widget(self, switch):
        """
        Helper function to create a widget with radio buttons per switch.
            @param str switch: the index (in switchlogic) of the switch to be displayed
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

        names = self.switchlogic().names_of_states[switch]
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
        """
        Delete all the buttons from the group box and remove the layout.
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
        """
        Helper function that is connected to the GUI interaction.
        A GUI change is transmitted to the logic and the visual indicators are changed.
            @param int switch: switch index of the GUI element that was changed
            @param bool state: new state of the switch
            @return: None
        """
        if not is_set:
            return
        self.switchlogic().set_state(switch=switch, state=state)

    def _switch_updated(self, states):
        """
        Helper function that is connected to the signal coming from the switchlogic signaling a change in states.
            @param list(bool) states: a list of boolean values containing the states of the switches
            @return: None
        """
        for switch, state_tuple in states.items():
            for name, widget in self._widgets[switch].items():
                widget.blockSignals(True)
                widget.setChecked(name == state_tuple[1])
                widget.setStyleSheet(self._lowlight_format if name == state_tuple[1] else self._highlight_format)
                widget.blockSignals(False)
