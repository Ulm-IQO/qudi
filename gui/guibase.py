# -*- coding: utf-8 -*-

"""
This file contains the QuDi GUI module base class.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from core.base import Base
import warnings

class GUIBase(Base):
    """This is the GUI base class. It provides functions that every GUI module should have.
    """
    _modclass = 'GUIBase'
    _modtype = 'Gui'

    def show(self):
        warnings.warn('Every GUI module needs to reimplement the show() '
                'function!')

    def saveWindowPos(self, window):
        self._statusVariables['pos_x'] = window.pos().x()
        self._statusVariables['pos_y'] = window.pos().y()

    def restoreWindowPos(self, window):
        if 'pos_x' in self._statusVariables and 'pos_y' in self._statusVariables:
            window.move(self._statusVariables['pos_x'],  self._statusVariables['pos_y'])
