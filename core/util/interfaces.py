# -*- coding: utf-8 -*-
"""
Metaclass for interfaces.

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
top-level directory of this distribution and at
<https://github.com/Ulm-IQO/qudi/>
"""


import abc
from qtpy.QtCore import QObject
from core.module import ModuleMeta

QObjectMeta = type(QObject)

class InterfaceMetaclass(ModuleMeta, abc.ABCMeta):
    """
    Metaclass for interfaces.
    """
    pass


class TaskMetaclass(QObjectMeta, abc.ABCMeta):
    """
    Metaclass for interfaces.
    """
    pass


class ScalarConstraint:
    """
    Constraint definition for a scalar variable hardware parameter.
    """
    def __init__(self, min=0.0, max=0.0, step=0.0, default=0.0, unit=''):
        # allowed minimum value for parameter
        self.min = min
        # allowed maximum value for parameter
        self.max = max
        # allowed step size for parameter value changes (for spinboxes etc.)
        self.step = step
        # the default value for the parameter
        self.default = default
        # the unit of the parameter value(optional)
        self.unit = unit
        return
