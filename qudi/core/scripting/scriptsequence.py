# -*- coding: utf-8 -*-

"""
ToDo: Document

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
from collections.abc import Sequence

from qudi.core.scripting.modulescript import ModuleScript


class ModuleScriptSequence(QtCore.QObject):
    """
    """
    def __int__(self, *args, script_sequence: Sequence[ModuleScript] = None, **kwargs):
        super().__init__(*args, **kwargs)
        if script_sequence is not None:
            assert all(isinstance(scr, ModuleScript) for scr in script_sequence), \
                'script_sequence must be sequence of ModuleScript instances'
        self._script_sequence = list()

    def