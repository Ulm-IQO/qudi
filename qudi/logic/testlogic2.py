# -*- coding: utf-8 -*-
"""
This file contains a qudi logic module template

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

from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.core.configoption import ConfigOption
from qudi.core.module import LogicBase
from qtpy import QtCore


class TestLogic2(LogicBase):
    """Description of this qudi module goes here.
    """

    # my_logic_connector = Connector(interface='LogicClassName')
    my_hardware_connector = Connector(interface='TestHardware2')

    _my_config_var = ConfigOption(name='my_config_var', default=None, missing='warn')

    sigStuffDone = QtCore.Signal()

    _my_status_variable = StatusVar(name='my_status_variable', default=42)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_activate(self):
        """Everything that should be done when activating the module must go in here.
        """
        # Establish Qt signal-slot connections if needed. Also connect to logic/hardware signals
        # and slots, preferably through QtCore.Qt.QueuedConnection
        self.sigStuffDone.connect(self.my_slot_for_stuff)
        return

    def on_deactivate(self):
        """Undo everything that has been done in on_activate. In other words clean up after
        yourself and ensure there are no lingering connections, references to outside objects, open
        file handles etc. etc.
        """
        # disconnect all signals connected in on_activate
        self.sigStuffDone.disconnect(self.my_slot_for_stuff)
        return

    def set_status_var(self, new_var):
        """Example method that changes the StatusVar >>_my_status_variable<<
        """
        self._my_status_variable = new_var
        print('StatusVar set to:', self._my_status_variable)
        return

    def print_stuff(self):
        """Example function to print out ConfigOption and StatusVar.
        """
        print('StatusVar is: {0}\nConfigOption is: {1}'.format(
            self._my_status_variable, self._my_config_var))
        return

    @QtCore.Slot()
    def my_slot_for_stuff(self):
        """Dummy slot that gets called every time sigStuffDone is emitted and connected.
        """
        print('my_slot_for_stuff has been called!')
        return
