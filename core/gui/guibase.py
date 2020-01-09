# -*- coding: utf-8 -*-

"""
This file contains the Qudi GUI module base class.

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

from qtpy.QtCore import QObject
from core.module import BaseMixin
import warnings


class GUIBaseMixin(BaseMixin):
    """This is the GUI base class. It provides functions that every GUI module should have.
    """
    def __init__(self, *args, **kwargs):
        BaseMixin.__init__(self, *args, **kwargs)

    def show(self):
        warnings.warn('Every GUI module needs to re-implement the show() function!')

    def save_window_pos(self, window):
        self._status_variables['__win_pos_x'] = window.pos().x()
        self._status_variables['__win_pos_y'] = window.pos().y()

    def restore_window_pos(self, window):
        if '__win_pos_x' in self._status_variables and '__win_pos_y' in self._status_variables:
            window.move(self._status_variables['__win_pos_x'],
                        self._status_variables['__win_pos_y'])


class GUIBase(QObject, GUIBaseMixin):
    def __init__(self, parent=None, **kwargs):
        QObject.__init__(self, parent)
        GUIBaseMixin.__init__(self, parent=parent, **kwargs)
