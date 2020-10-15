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
from qtpy import QtWidgets, QtGui, QtCore
from qtpy import uic


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
        self._widgets = list()
        self._highlight_format = 'QRadioButton {color: green; font-weight: bold;}'
        self._lowlight_format = 'QRadioButton {color: red; font-weight: normal;}'

    def on_activate(self):
        """Create all UI objects and show the window.
        """
        self.restoreWindowPos(self._mw)
        self._populate_switches()

        self.show()

        self.switchlogic().sig_switch_updated.connect(self._switch_updated, QtCore.Qt.QueuedConnection)

    def on_deactivate(self):
        """ Hide window and stop ipython console.
        """
        self.switchlogic().sig_switch_updated.disconnect(self._switch_updated)

        for hw_index, switch_widgets in enumerate(self._widgets):
            for sw_index, widgets in enumerate(switch_widgets):
                widgets['on_button'].disconnect()

        self.saveWindowPos(self._mw)
        self._mw.close()

    def show(self):
        """Make sure that the window is visible and at the top.
        """
        self._mw.show()

    def _populate_switches(self):
        # For each switch that the logic has, add a widget to the GUI to show its state
        for hardware_index, switch in enumerate(self.switchlogic().names_of_hardware):
            frame = QtWidgets.QGroupBox(switch, self._mw.scroll_area)
            frame.setAlignment(QtCore.Qt.AlignLeft)
            frame.setFlat(False)
            vertical_layout = QtWidgets.QVBoxLayout(frame)
            self._widgets.append(list())
            for switch_index, _ in enumerate(self.switchlogic().names_of_states[hardware_index]):
                vertical_layout.addWidget(self._add_radio_widget(hardware_index, switch_index))

            frame.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
            self._mw.scroll_area_widget.layout().addWidget(frame)
        self._switch_updated(self.switchlogic().states)

    def _add_radio_widget(self, hardware_index, switch_index):
        button_group = QtWidgets.QButtonGroup()
        names = self.switchlogic().names_of_states[hardware_index][switch_index]

        on_button = QtWidgets.QRadioButton(names[0])
        on_button.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        off_button = QtWidgets.QRadioButton(names[1])
        off_button.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        button_group.addButton(on_button)
        button_group.addButton(off_button)
        self._widgets[hardware_index].append({'on_button': on_button, 'off_button': off_button})

        on_button.toggled.connect(lambda button_state, hw_origin=hardware_index, switch_origin=switch_index:
                                  self._radio_button_toggled(hw_origin, switch_origin, button_state))

        label = QtWidgets.QLabel(str(self.switchlogic().names_of_switches[hardware_index][switch_index]) + ':')
        label.setFixedWidth(100)

        radio_layout = QtWidgets.QHBoxLayout()
        radio_layout.addWidget(label)
        radio_layout.addWidget(off_button)
        radio_layout.addWidget(on_button)

        widget = QtWidgets.QWidget()
        widget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        widget.setLayout(radio_layout)

        return widget

    def _radio_button_toggled(self, hardware_index, switch_index, state):
        self.switchlogic().set_state(hardware_index, switch_index, state)
        self._widgets[hardware_index][switch_index]['on_button'].setStyleSheet(
            self._lowlight_format if state else self._highlight_format)
        self._widgets[hardware_index][switch_index]['off_button'].setStyleSheet(
            self._lowlight_format if not state else self._highlight_format)

    def _switch_updated(self, states):
        for hw_index, switch_number in enumerate(self.switchlogic().number_of_switches):
            for sw_index in range(switch_number):
                button = 'on_button' if states[hw_index][sw_index] else 'off_button'
                self._widgets[hw_index][sw_index][button].blockSignals(True)
                self._widgets[hw_index][sw_index][button].setChecked(True)
                self._widgets[hw_index][sw_index][button].blockSignals(False)

                self._widgets[hw_index][sw_index]['on_button'].setStyleSheet(
                    self._lowlight_format if states[hw_index][sw_index] else self._highlight_format)
                self._widgets[hw_index][sw_index]['off_button'].setStyleSheet(
                    self._lowlight_format if not states[hw_index][sw_index] else self._highlight_format)
