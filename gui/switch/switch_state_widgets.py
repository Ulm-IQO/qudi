# -*- coding: utf-8 -*-
"""
This file contains the qudi switch state QWidgets for the GUI module SwitchGui.

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

from qtpy import QtWidgets, QtCore


class SwitchRadioButtonWidget(QtWidgets.QWidget):
    """
    """

    sigStateChanged = QtCore.Signal(str)

    _highlight_style = 'QRadioButton {color: green; font-weight: bold;}'
    _lowlight_style = 'QRadioButton {color: red; font-weight: normal;}'

    def __init__(self, *args, switch_name, switch_states, **kwargs):
        super().__init__(*args, **kwargs)
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)

        self.switch_name = switch_name
        self.switch_states = tuple(switch_states)
        self.radio_buttons = {state: QtWidgets.QRadioButton(state) for state in switch_states}
        button_group = QtWidgets.QButtonGroup(self)
        for ii, button in enumerate(self.radio_buttons.values()):
            layout.addWidget(button)
            button_group.addButton(button, ii)
        # self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
        #                      QtWidgets.QSizePolicy.MinimumExpanding)
        # self.setMinimumWidth(self.sizeHint().width())
        button_group.buttonToggled.connect(self.__button_toggled_cb)

    def __button_toggled_cb(self, button, checked):
        """

        @param button:
        @param checked:
        """
        if checked:
            self.sigStateChanged.emit(button.text())
            self._update_stylesheet()

    def set_state(self, state):
        assert state in self.switch_states, f'Invalid switch state: "{state}"'
        button = self.radio_buttons[state]
        if not button.isChecked():
            button.blockSignals(True)
            button.setChecked(True)
            button.blockSignals(False)
            self._update_stylesheet()

    def _update_stylesheet(self):
        for button in self.radio_buttons.values():
            if button.isChecked():
                button.setStyleSheet(self._lowlight_style)
            else:
                button.setStyleSheet(self._highlight_style)
