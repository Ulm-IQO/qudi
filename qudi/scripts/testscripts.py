# -*- coding: utf-8 -*-

"""
This file contains scripts for testing the qudi.core.scripting package.

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

from qudi.core.scripting.modulescript import ModuleScript
from qudi.core.connector import Connector


class TestScript(ModuleScript):

    def _run(self, pos_arg, kw_arg=42):
        print('TestScript executing:', pos_arg, kw_arg)
