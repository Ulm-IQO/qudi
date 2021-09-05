# -*- coding: utf-8 -*-
"""
This file contains utility methods for GUI widgets.

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

__all__ = []

import inspect
from PySide2 import QtWidgets
from typing import Callable, List, Type, Any, Set, FrozenSet, Iterable, Mapping, _SpecialForm
from typing import get_args, get_origin

from qudi.util.helpers import is_complex, is_float, is_integer, is_string, is_number_type
from qudi.util.helpers import is_complex_type, is_float_type, is_integer_type, is_string_type
from qudi.core.gui.qtwidgets.scientific_spinbox import ScienSpinBox, ScienDSpinBox


class ParameterWidgetMapper:

    @staticmethod
    def widget_from_default_value(value: Any) -> Type[QtWidgets.QWidget]:
        if is_integer(value):
            return ScienSpinBox
        if is_float(value):
            return ScienDSpinBox
        return QtWidgets.QLineEdit

    @classmethod
    def widget_from_annotation(cls, annotation: Any) -> Type[QtWidgets.QWidget]:
        normalized_types = cls._annotation_to_builtin(annotation)
        if not isinstance(normalized_types, tuple):
            normalized_types = (normalized_types,)
        widgets = list()
        for tmp in normalized_types:
            if isinstance(tmp, tuple):

        if is_integer(value):
            return ScienSpinBox
        if is_float(value):
            return ScienDSpinBox
        return QtWidgets.QLineEdit

    @staticmethod
    def _normalize_type(typ):
        if is_string_type(typ):
            return str
        elif is_integer_type(typ):
            return int
        elif is_float_type(typ):
            return float
        elif is_complex_type(typ):
            return complex
        elif issubclass(typ, (Set, FrozenSet)):
            return set
        elif issubclass(typ, Mapping):
            return dict
        elif issubclass(typ, Iterable):
            return list
        return None

    @classmethod
    def _annotation_to_builtin(cls, ann_type):
        """
        """
        if inspect.isclass(ann_type):
            return cls._normalize_type(ann_type)
        else:
            origin = get_origin(ann_type)
            args = get_args(ann_type)
            if origin is None:
                return None
            elif isinstance(origin, _SpecialForm):
                if len(args) > 1:
                    return tuple(cls._annotation_to_builtin(a) for a in args)
                elif len(args) == 1:
                    return cls._annotation_to_builtin(args[0])
            elif issubclass(origin, Mapping):
                return dict, tuple(cls._annotation_to_builtin(a) for a in args)
            elif issubclass(origin, (Set, FrozenSet)):
                return set, cls._annotation_to_builtin(args[0])
            elif issubclass(origin, Iterable):
                if len(args) > 1:
                    return tuple, (cls._annotation_to_builtin(a) for a in args)
                else:
                    return list, cls._annotation_to_builtin(args[0])
        return None


def callable_parameters_widget_types(func: Callable) -> List[Type[QtWidgets.QWidget]]:
    """
    """
    sig = inspect.signature(func)


def callable_parameter_widget_type(param: inspect.Parameter) -> Type[QtWidgets.QWidget]:
    """
    """
    # Try to deduce missing type annotation from default parameter type
    if param.annotation is inspect.Parameter.empty:
        default = param.default
        if is_integer(default):
            return ScienSpinBox
        if is_float(default):
            return ScienDSpinBox
        return QtWidgets.QLineEdit
    else:
        param_type = param.annotation
        if param.default is inspect.Parameter.empty:
            # No type annotation and no default parameter
            return

