# -*- coding: utf-8 -*-

"""
This module controls a 3D magnet.

The 3D magnet consists of three 1D magnets, to which it needs to be connected to.

Config for copy paste:


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

from core.module import Base

class magnet_3d(Base):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    def on_activate(self):
        pass


    def on_deactivate(self):
        pass


    def get_field_amplitude(self):
        pass
