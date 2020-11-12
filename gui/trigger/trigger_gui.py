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


class TriggerMainWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self, **kwargs):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_trigger_gui.ui')

        # Load it
        super().__init__(**kwargs)
        uic.loadUi(ui_file, self)
        self.show()


class TriggerGui(GUIBase):
    """ A graphical interface to trigger a hardware by hand.
    """

    # declare connectors
    trigger_logic = Connector(interface='TriggerLogic')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mw = TriggerMainWindow()
        self._widgets = list()

    def on_activate(self):
        """ Create all UI objects and show the window.
        """
        self.restoreWindowPos(self._mw)
        self._populate_triggers()
        self.show()

    def on_deactivate(self):
        """ Hide window empty the GUI and disconnect signals
        """

        self._depopulate_triggers()

        self.saveWindowPos(self._mw)
        self._mw.close()

    def show(self):
        """ Make sure that the window is visible and at the top.
        """
        self._mw.show()

    def _populate_triggers(self):
        """ Dynamically build the gui.
        @return: None
        """
        # For each trigger the logic has, a button needs to be shown.
        self._mw.trigger_groupBox.setTitle('Triggers')
        self._mw.trigger_groupBox.setAlignment(QtCore.Qt.AlignLeft)
        self._mw.trigger_groupBox.setFlat(False)
        vertical_layout = QtWidgets.QVBoxLayout(self._mw.trigger_groupBox)
        self._widgets = list()
        for trigger in self.trigger_logic().names_of_triggers:
            widget = QtWidgets.QPushButton(trigger)
            widget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
            widget.setCheckable(True)
            widget.setChecked(False)
            widget.setFocusPolicy(QtCore.Qt.NoFocus)

            widget.clicked.connect(lambda button_state, trigger_origin=trigger:
                                   self._button_toggled(trigger_origin, button_state))

            self._widgets.append([trigger, widget])
            vertical_layout.addWidget(widget)

        self._mw.trigger_groupBox.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                QtWidgets.QSizePolicy.MinimumExpanding)
        self._mw.trigger_groupBox.updateGeometry()

    def _depopulate_triggers(self):
        """ Delete all the buttons from the group box and remove the layout.
        @return: None
        """
        for widgets in self._widgets:
            widgets[1].clicked.disconnect()
        self._widgets = list()

        vertical_layout = self._mw.trigger_groupBox.layout()
        if vertical_layout is not None:
            for i in reversed(range(vertical_layout.count())):
                vertical_layout.itemAt(i).widget().setParent(None)
            sip.delete(vertical_layout)

    def _button_toggled(self, trigger, is_set):
        """ Helper function that is connected to the GUI interaction.
        A GUI change is transmitted to the logic and the visual indicators are changed.
        @param str trigger: name of the trigger toggled
        @param bool is_set: indicator for the state of the button, ignored in this case
        @return: None
        """
        self.trigger_logic().trigger(trigger)
        for widget in self._widgets:
            if trigger == widget[0]:
                widget[1].setChecked(False)
