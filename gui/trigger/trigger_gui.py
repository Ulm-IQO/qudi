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
from qtpy import QtWidgets, QtCore, QtGui


class TriggerMainWindow(QtWidgets.QMainWindow):
    """ Main Window for the TriggerGui module """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('qudi: Trigger GUI')
        # Create main layout and central widget
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
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

        # close window upon triggering close action
        self.action_close.triggered.connect(self.close)
        return


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

        self._delete_triggers()

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
        self._widgets = list()
        for trigger in self.trigger_logic().names_of_triggers:
            widget = QtWidgets.QPushButton(trigger)
            widget.setMinimumWidth(100)
            widget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
            widget.setCheckable(True)
            widget.setChecked(False)
            widget.setFocusPolicy(QtCore.Qt.NoFocus)

            widget.clicked.connect(lambda button_state, trigger_origin=trigger:
                                   self._button_toggled(trigger_origin, button_state))

            self._widgets.append([trigger, widget])

            self._mw.main_layout.addWidget(widget)

    def _delete_triggers(self):
        """ Delete all the buttons from the group box and remove the layout.
        @return: None
        """

        for index in reversed(range(len(self._widgets))):
            trigger, widget = self._widgets[index]
            widget.clicked.disconnect()
            self._mw.main_layout.removeWidget(widget)
            widget.setParent(None)
            del self._widgets[index]
            widget.deleteLater()

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
