# -*- coding: utf-8 -*-

"""
This file contains a wrapper to display the SpinBox in scientific way

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

Copyright (C) 2016 Alexander Stark alexander.stark@uni-ulm.de
"""

from qtpy import QtGui, QtWidgets
import numpy as np
import re
from pyqtgraph import functions as fn
__all__=['ScienDSpinBox']

class FloatValidator(QtGui.QValidator):
    """
    This is a validator for float values represented as strings in scientific notation.
    (i.e. "1.35e-9", ".24E+8", "14e3" etc.)
    Also supports SI unit prefix like 'M', 'n' etc.
    """
    def __init__(self):
        self.float_re = None
        self.group_map = dict()  # mapping of the regex groups
        self.set_prefix_suffix()  # Set regular expression
        return

    def validate(self, string, position):

        match = self.float_re.search(string)

        if match:
            if match.groups()[self.group_map['match']] != string:
                return self.Invalid, string, position

            if position > len(string):
                position = len(string)
            elif position < 1:
                position = 1
            if match.groups()[self.group_map['mantissa']] is None or string[position-1] in 'eE.-+ ':
                return self.Intermediate, string, position

            return self.Acceptable, string, position
        else:
            return self.Invalid, string, position

    def fixup(self, text):
        match = self.float_re.search(text)
        if match:
            return match.groups()[0].lstrip().rstrip()
        else:
            return ''

    def set_prefix_suffix(self, prefix=None, suffix=None):
        self.group_map = dict()
        self.group_map['match'] = 0
        if suffix is None and prefix is not None:
            self.float_re = re.compile(
                r'(({0})\s?([+-]?(\d+)\.?(\d*))?([eE][+-]?\d+)?\s?([YZEPTGMkmµunpfazy]?))'
                r''.format(prefix))
            self.group_map['prefix'] = 1
            self.group_map['mantissa'] = 2
            self.group_map['integer'] = 3
            self.group_map['fractional'] = 4
            self.group_map['exponent'] = 5
            self.group_map['si'] = 6
        elif suffix is not None and prefix is None:
            self.float_re = re.compile(
                r'(([+-]?(\d+)\.?(\d*))?([eE][+-]?\d+)?\s?([YZEPTGMkmµunpfazy]?)\s?({0}))'
                r''.format(suffix))
            self.group_map['mantissa'] = 1
            self.group_map['integer'] = 2
            self.group_map['fractional'] = 3
            self.group_map['exponent'] = 4
            self.group_map['si'] = 5
            self.group_map['suffix'] = 6
        elif suffix is not None and prefix is not None:
            self.float_re = re.compile(
                r'(({0})\s?([+-]?(\d+)\.?(\d*))?([eE][+-]?\d+)?\s?([YZEPTGMkmµunpfazy]?)\s?({1}))'
                r''.format(prefix, suffix))
            self.group_map['prefix'] = 1
            self.group_map['mantissa'] = 2
            self.group_map['integer'] = 3
            self.group_map['fractional'] = 4
            self.group_map['exponent'] = 5
            self.group_map['si'] = 6
            self.group_map['suffix'] = 7
        else:
            self.float_re = re.compile(
                r'(([+-]?(\d+)\.?(\d*))?([eE][+-]?\d+)?\s?([YZEPTGMkmµunpfazy]?))')
            self.group_map['mantissa'] = 1
            self.group_map['integer'] = 2
            self.group_map['fractional'] = 3
            self.group_map['exponent'] = 4
            self.group_map['si'] = 5
        return


class ScienDSpinBox(QtWidgets.QDoubleSpinBox):
    """
    Wrapper Class from PyQt5 (or QtPy) to display a QDoubleSpinBox in Scientific way.

    This class can be directly used in Qt Designer by promoting the QDoubleSpinBox to ScienDSpinBox.
    State the path to this file (in python style, i.e. dots are separating the directories) as the
    header file and use the name of the present class.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMinimum(-np.inf)
        self.setMaximum(np.inf)
        self.validator = FloatValidator()
        self.setDecimals(1000)

    def validate(self, text, position):
        state, string, position = self.validator.validate(text, position)
        return state, string, position

    def fixup(self, text):
        return self.validator.fixup(text)

    def setPrefix(self, prefix=None):
        if not prefix:
            prefix = None

        if self.suffix():
            suffix = self.suffix()
        else:
            suffix = None

        self.validator.set_prefix_suffix(prefix, suffix)
        super().setPrefix(prefix)
        return

    def setSuffix(self, suffix=None):
        if not suffix:
            suffix = None

        if self.prefix():
            prefix = self.prefix()
        else:
            prefix = None

        self.validator.set_prefix_suffix(prefix, suffix)
        super().setSuffix(suffix)
        return

    def valueFromText(self, text):
        text = text.lstrip().rstrip()  # get rid of leading and trailing whitespaces
        text = text.replace(self.suffix(), '').replace(self.prefix(), '') # get rid of prefix/suffix
        return fn.siEval(text)

    def textFromValue(self, value):
        (scale_factor, suffix) = fn.siScale(value)
        scaled_val = value * scale_factor
        if abs(scaled_val) < 10:
            string = fn.siFormat(value, precision=4)
        elif abs(scaled_val) < 100:
            string = fn.siFormat(value, precision=5)
        elif abs(scaled_val) < 1000:
            string = fn.siFormat(value, precision=6)
        return string

    def stepBy(self, steps):
        text = self.text()
        groups = self.validator.float_re.search(text).groups()
        decimal_num = float(groups[self.validator.group_map['mantissa']])
        si_prefix = groups[self.validator.group_map['si']]
        decimal_num += steps
        new_string = '{0:g}'.format(decimal_num) + ((' ' + si_prefix) if si_prefix else '')
        new_value = fn.siEval(new_string)
        if new_value < self.minimum():
            new_value = self.minimum()
        if new_value > self.maximum():
            new_value = self.maximum()
        new_string = self.textFromValue(new_value)
        if self.prefix():
            new_string = self.prefix() + new_string
        if self.suffix():
            new_string += self.suffix()
        self.lineEdit().setText(new_string)
        return


# class ScienDSpinBox(SpinBox):
#     """ Wrapper Class from PyQtGraph to display a QDoubleSpinBox in Scientific
#         way.
#
#     This class can be directly used in Qt Designer by promoting the
#     QDoubleSpinBox to ScienDSpinBox. State the path to this file (in python
#     style, i.e. dots are separating the directories) as the header file and use
#     the name of the present class.
#     """
#
#     def __init__(self, *args, **kwargs):
#         SpinBox.__init__(
#                 self,
#                 *args,
#                 int=False,
#                 #suffix='s',
#                 siPrefix=True,
#                 dec=True,
#                 step=0.1,
#                 minStep=0.0001,
#                 bounds=(0.0, 99.99),    # set the bounds to be convenient to the default values of the Qt Designer.
#                 **kwargs
#         )
#
# class ScienSpinBox(SpinBox):
#     """ Wrapper Class from PyQtGraph to display a QSpinBox in Scientific way.
#
#     This class can be directly used in Qt Designer by promoting the
#     QSpinBox to ScienSpinBox. State the path to this file (in python style,
#     i.e. dots are separating the directories) as the header file and use the
#     name of the present class.
#     """
#
#     def __init__(self, *args, **kwargs):
#         SpinBox.__init__(self,
#                          *args,
#                          int=True,
#                          bounds=(0, 99), # set the bounds to be convenient to the default values of the Qt Designer.
#                          **kwargs)
