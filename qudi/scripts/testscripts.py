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

from PySide2 import QtCore
from qudi.core.scripting.moduletask import ModuleTask
from qudi.core.connector import Connector


class TestTask(ModuleTask):

    _derp = Connector(name='derp', interface='TemplateLogic')

    def _setup(self) -> None:
        i = 0
        for i in range(100000000):
            i += 1

    def _cleanup(self) -> None:
        i = 0
        for i in range(100000000):
            i += 1

    def _run(self, pos_arg='abc', kw_arg=42):
        i = 0
        for i in range(10000000):
            self._check_interrupt()
            i += 1
