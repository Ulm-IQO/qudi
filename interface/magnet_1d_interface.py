# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interface file to control 1d magnets.

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

from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass


class Magnet1DInterface(metaclass=InterfaceMetaclass):
    # This class needs to be imported in the hardware file and given to the class.
    @abstract_interface_method
    def ramp(self, field_target=None, current_target=None):
        pass

    @abstract_interface_method
    def get_field(self):
        pass

    @abstract_interface_method
    def ramp_to_zero(self):
        pass

    @abstract_interface_method
    def get_ramping_state(self):
        pass

    @abstract_interface_method
    def get_constraints(self):
        pass