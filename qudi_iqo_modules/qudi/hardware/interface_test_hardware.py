# -*- coding: utf-8 -*-

"""
This file contains a qudi hardware module template

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

from qudi.util.overload import OverloadedAttribute
from qudi.interface.test_interface import FirstTestInterface, SecondTestInterface


class TestHardware(FirstTestInterface, SecondTestInterface):

    def on_activate(self):
        pass

    def on_deactivate(self):
        pass

    @property
    def x(self):
        print('TestHardware.x called')

    herp = OverloadedAttribute()

    @herp.overload('FirstTestInterface')
    def herp(self):
        print('herp1 called')

    @herp.overload('SecondTestInterface')
    def herp(self):
        print('herp2 called')
