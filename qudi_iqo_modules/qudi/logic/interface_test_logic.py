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
from qudi.core.module import LogicBase


class InterfaceTestLogic(LogicBase):

    _first_hardware = Connector(name='first_hardware', interface='FirstTestInterface')
    _second_hardware = Connector(name='second_hardware', interface='SecondTestInterface')

    def on_activate(self):
        self._first_hardware().herp()
        self._second_hardware().herp()
        print(self._first_hardware().x)
        print(self._second_hardware().y)

    def on_deactivate(self):
        pass
