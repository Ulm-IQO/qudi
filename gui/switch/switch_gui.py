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

    _radio_buttons = ConfigOption(name='radio_buttons', default=False, missing='nothing')

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
        self._mw.action_show_radio_buttons.setChecked(self._radio_buttons)
        self.show()

        self.switchlogic().sig_switch_updated.connect(self._switch_updated, QtCore.Qt.QueuedConnection)
        self._mw.action_show_radio_buttons.toggled.connect(self._show_radio_buttons_changed, QtCore.Qt.QueuedConnection)

    def on_deactivate(self):
        """ Hide window and stop ipython console.
        """
        self.switchlogic().sig_switch_updated.disconnect(self._switch_updated)
        self._mw.action_show_radio_buttons.toggled.disconnect(self._show_radio_buttons_changed)

        self._depopulate_switches()

        self.saveWindowPos(self._mw)
        self._mw.close()

    def show(self):
        """Make sure that the window is visible and at the top.
        """
        self._mw.show()

    def _populate_switches(self):
        # For each switch that the logic has, add a widget to the GUI to show its state
        self._mw.switch_groupBox.setTitle(self.switchlogic().name_of_hardware)
        self._mw.switch_groupBox.setAlignment(QtCore.Qt.AlignLeft)
        self._mw.switch_groupBox.setFlat(False)
        vertical_layout = QtWidgets.QVBoxLayout(self._mw.switch_groupBox)
        self._widgets = list()
        for switch_index in range(self.switchlogic().number_of_switches):
            if self._radio_buttons:
                vertical_layout.addWidget(self._add_radio_widget(switch_index))
            else:
                vertical_layout.addWidget(self._add_check_widget(switch_index))

        self._mw.switch_groupBox.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                               QtWidgets.QSizePolicy.MinimumExpanding)
        self._mw.switch_groupBox.updateGeometry()
        self._switch_updated(self.switchlogic().states)

    def _add_radio_widget(self, switch_index):
        button_group = QtWidgets.QButtonGroup()

        on_button = QtWidgets.QRadioButton(self.switchlogic().names_of_states[int(switch_index)][1])
        on_button.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        off_button = QtWidgets.QRadioButton(self.switchlogic().names_of_states[int(switch_index)][0])
        off_button.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        button_group.addButton(on_button)
        button_group.addButton(off_button)
        self._widgets.append({'on_button': on_button, 'off_button': off_button})

        on_button.toggled.connect(lambda button_state, switch_origin=switch_index:
                                  self._button_toggled(switch_origin, button_state))

        label = QtWidgets.QLabel(str(self.switchlogic().names_of_switches[switch_index]) + ':')
        label.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        label.setMinimumWidth(100)

        widget = QtWidgets.QWidget()
        widget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(label)
        layout.addWidget(off_button)
        layout.addWidget(on_button)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        widget.setLayout(layout)

        return widget

    def _add_check_widget(self, switch_index):
        button = QtWidgets.QCheckBox()
        button.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        button.setMinimumWidth(100)
        button.toggled.connect(lambda button_state, switch_origin=switch_index:
                               self._button_toggled(switch_origin, button_state))

        label = QtWidgets.QLabel(str(self.switchlogic().names_of_switches[switch_index]) + ':')
        label.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        label.setMinimumWidth(100)
        self._widgets.append({'on_button': button})

        widget = QtWidgets.QWidget()
        widget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        layout = QtWidgets.QHBoxLayout(widget)
        layout.addWidget(label)
        layout.addWidget(button)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        widget.setLayout(layout)
        return widget

    def _depopulate_switches(self):
        for sw_index, widgets in enumerate(self._widgets):
            widgets['on_button'].disconnect()
        self._widgets = list()

        vertical_layout = self._mw.switch_groupBox.layout()
        if vertical_layout is not None:
            for i in reversed(range(vertical_layout.count())):
                vertical_layout.itemAt(i).widget().setParent(None)
            sip.delete(vertical_layout)

    def _show_radio_buttons_changed(self, state):
        self._depopulate_switches()
        self._radio_buttons = bool(state)
        self._populate_switches()

    def _button_toggled(self, switch_index, state):
        self.switchlogic().set_state(switch_index, state)
        if self._radio_buttons:
            self._widgets[switch_index]['on_button'].setStyleSheet(
                self._lowlight_format if state else self._highlight_format)
            self._widgets[switch_index]['off_button'].setStyleSheet(
                self._lowlight_format if not state else self._highlight_format)
        else:
            self._widgets[switch_index]['on_button'].setChecked(state)
            label = self.switchlogic().names_of_states[switch_index][int(state)]
            self._widgets[switch_index]['on_button'].setText(label)

    def _switch_updated(self, states):
        for sw_index in range(self.switchlogic().number_of_switches):
            if self._radio_buttons:
                button = 'on_button' if states[sw_index] else 'off_button'
                self._widgets[sw_index][button].blockSignals(True)
                self._widgets[sw_index][button].setChecked(True)
                self._widgets[sw_index][button].blockSignals(False)

                self._widgets[sw_index]['on_button'].setStyleSheet(
                    self._lowlight_format if states[sw_index] else self._highlight_format)
                self._widgets[sw_index]['off_button'].setStyleSheet(
                    self._lowlight_format if not states[sw_index] else self._highlight_format)
            else:
                self._widgets[sw_index]['on_button'].blockSignals(True)
                self._widgets[sw_index]['on_button'].setChecked(states[sw_index])
                label = self.switchlogic().names_of_states[sw_index][int(states[sw_index])]
                self._widgets[sw_index]['on_button'].setText(label)
                self._widgets[sw_index]['on_button'].blockSignals(False)
