# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI module for Motor control.

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
from qudi.core.util import units
from qudi.core.module import GuiBase
from .motor_main_window import MotorMainWindow


class MotorGui(GuiBase):
    """
    This is the GUI Class for Motor operations
    """

    # declare connectors
    _motor_logic = Connector(name='motor_logic', interface='MotorLogic')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_activate(self):
        self.motor_logic = self._motor_logic()
        self.constraints = self.motor_logic.constraints
        self._mw = MotorMainWindow()

    def on_deactivate(self):
        pass

