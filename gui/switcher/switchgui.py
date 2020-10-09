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

from core.connector import Connector
from gui.guibase import GUIBase
from qtpy import QtWidgets, QtGui, QtCore


class SwitchMainWindow(QtWidgets.QMainWindow):
    """ Helper class for window loaded from UI file.
    """

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.setWindowTitle('qudi: Switch GUI')
        self.resize(300, 400)

        self.scroll_area = QtWidgets.QScrollArea()
        # Add layout that we want to fill
        self.layout = QtWidgets.QVBoxLayout(self.scroll_area)

        self.setCentralWidget(self.scroll_area)

        # quit action
        self.action_quit = QtWidgets.QAction()
        self.action_quit.setIcon(QtGui.QIcon('application-exit.png'))
        self.action_quit.setText('&Close')
        self.action_quit.setToolTip('Close')
        self.action_quit.setShortcut(QtGui.QKeySequence('C'))
        self.action_quit.triggered.connect(self.close)

        # Create menu bar
        menu = self.menuBar().addMenu('&File')
        menu.addAction(self.action_quit)

        self.show()


class ColouredRadioButton(QtWidgets.QRadioButton):

    def setChecked(self, value):
        super().setChecked(value)
        if value:
            self.setStyleSheet('QRadioButton {color: ' + 'red;}' if value else 'green;}')


class SwitchGui(GUIBase):
    """ A grephical interface to mofe switches by hand and change their calibration.
    """

    # declare connectors
    switchlogic = Connector(interface='SwitchLogic')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mw = SwitchMainWindow()

        self._widgets = list()

    def on_activate(self):
        """Create all UI objects and show the window.
        """
        # For each switch that the logic has, add a widget to the GUI to show its state
        for hardware_index, switch in enumerate(self.switchlogic().names_of_switches):
            frame = QtWidgets.QGroupBox(switch, self._mw.scroll_area)
            frame.setAlignment(QtCore.Qt.AlignLeft)
            frame.setFlat(False)
            vertical_layout = QtWidgets.QVBoxLayout(frame)
            self._widgets.append(list())
            for switch_index, names in enumerate(self.switchlogic().names_of_states[hardware_index]):
                vertical_layout.addWidget(self._add_radio_widget(hardware_index, switch_index, names))

            frame.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
            self._mw.layout.addWidget(frame)
        self.restoreWindowPos(self._mw)
        self.show()

    def _add_radio_widget(self, hardware_index, switch_index, names):
        radio_layout = QtWidgets.QHBoxLayout()
        button_group = QtWidgets.QButtonGroup()
        state = self.switchlogic().states[hardware_index][switch_index]

        on_button = QtWidgets.QRadioButton(names[0])
        on_button.setStyleSheet('QRadioButton {color: red;}' if state else 'QRadioButton {color: green;}')
        on_button.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        off_button = QtWidgets.QRadioButton(names[1])
        off_button.setStyleSheet('QRadioButton {color: red;}' if not state else 'QRadioButton {color: green;}')
        off_button.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        button_group.addButton(on_button)
        button_group.addButton(off_button)
        self._widgets[hardware_index].append({'on_button': on_button, 'off_button': off_button})

        if state:
            on_button.setChecked(True)
        else:
            off_button.setChecked(True)

        on_button.toggled.connect(lambda button_state, hw_origin=hardware_index, switch_origin=switch_index:
                                  self._radio_button_toggled(hw_origin, switch_origin, button_state))

        radio_layout.addWidget(on_button)
        radio_layout.addWidget(off_button)

        widget = QtWidgets.QWidget()
        widget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        widget.setLayout(radio_layout)

        return widget

    def _radio_button_toggled(self, hardware_index, switch_index, state):
        self.switchlogic().set_state(hardware_index, switch_index, state)
        self._widgets[hardware_index][switch_index]['on_button'].setStyleSheet(
            'QRadioButton {color: red;}' if state else 'QRadioButton {color: green;}')
        self._widgets[hardware_index][switch_index]['off_button'].setStyleSheet(
            'QRadioButton {color: red;}' if not state else 'QRadioButton {color: green;}')

    def show(self):
        """Make sure that the window is visible and at the top.
        """
        self._mw.show()

    def on_deactivate(self):
        """ Hide window and stop ipython console.
        """
        self.saveWindowPos(self._mw)
        self._mw.close()
