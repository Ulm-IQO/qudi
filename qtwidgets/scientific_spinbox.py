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

__all__ = ['ScienDSpinBox']


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
        """
        This is the actual validator. It checks whether the current user input is a valid string
        every time the user types a character. There are 3 states that are possible.
        1) Invalid: The current input string is invalid. The user input will not accept the last
                    typed character.
        2) Acceptable: The user input in conform with the regular expression and will be accepted.
        3) Intermediate: The user input is not a valid string yet but on the right track. Use this
                         return value to allow the user to type fill-characters needed in order to
                         complete an expression (i.e. the decimal point of a float value).
        @param string: The current input string (from a QLineEdit for example)
        @param position: The current position of the text cursor
        @return: enum QValidator::State: the returned validator state,
                 str: the input string, int: the cursor position
        """
        # Return intermediate status when empty string is passed or cursor is at index 0
        if not string.strip() or position < 1:
            return self.Intermediate, string, position

        match = self.float_re.search(string)
        if match:
            if match.groups()[self.group_map['match']] != string:
                return self.Invalid, string, position

            if position > len(string):
                position = len(string)
            if match.groups()[self.group_map['mantissa']] is None or string[position-1] in 'eE.-+ ':
                return self.Intermediate, string, position

            return self.Acceptable, string, position
        else:
            return self.Invalid, string, position

    def fixup(self, text):
        match = self.float_re.search(text)
        if match:
            return match.groups()[0].strip()
        else:
            return ''

    def set_prefix_suffix(self, prefix=None, suffix=None):
        self.group_map = dict()
        self.group_map['match'] = 0
        if suffix is None and prefix is not None:
            self.float_re = re.compile(
                r'(({0})\s?(([+-]?\d+)\.?(\d*))?([eE][+-]?\d+)?\s?([YZEPTGMkmµunpfazy]?))'
                r''.format(prefix))
            self.group_map['prefix'] = 1
            self.group_map['mantissa'] = 2
            self.group_map['integer'] = 3
            self.group_map['fractional'] = 4
            self.group_map['exponent'] = 5
            self.group_map['si'] = 6
        elif suffix is not None and prefix is None:
            self.float_re = re.compile(
                r'((([+-]?\d+)\.?(\d*))?([eE][+-]?\d+)?\s?([YZEPTGMkmµunpfazy]?)\s?({0}))'
                r''.format(suffix))
            self.group_map['mantissa'] = 1
            self.group_map['integer'] = 2
            self.group_map['fractional'] = 3
            self.group_map['exponent'] = 4
            self.group_map['si'] = 5
            self.group_map['suffix'] = 6
        elif suffix is not None and prefix is not None:
            self.float_re = re.compile(
                r'(({0})\s?(([+-]?\d+)\.?(\d*))?([eE][+-]?\d+)?\s?([YZEPTGMkmµunpfazy]?)\s?({1}))'
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
                r'((([+-]?\d+)\.?(\d*))?([eE][+-]?\d+)?\s?([YZEPTGMkmµunpfazy]?))')
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
        self.precision = 6
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
        text = text.strip()  # get rid of leading and trailing whitespaces
        text = text.replace(self.suffix(), '')  # get rid of suffix
        text = text.replace(self.prefix(), '')  # get rid of prefix

        # Try to extract the precision the user intends to use
        split_text = text.split()
        if 0 < len(split_text) < 3:
            float_str = split_text[0]
            if len(float_str.split('.')) == 2:
                integer, fractional = float_str.split('.')
                self.precision = len(fractional)
                print(self.precision)
        return fn.siEval(text)

    def textFromValue(self, value):
        scale_factor, prefix = fn.siScale(value)
        scaled_val = value * scale_factor
        if scaled_val < 10:
            string = fn.siFormat(value, precision=self.precision + 1)
        elif scaled_val < 100:
            string = fn.siFormat(value, precision=self.precision + 2)
        else:
            string = fn.siFormat(value, precision=self.precision + 3)
        return string

    def stepBy(self, steps):
        text = self.text()
        groups = self.validator.float_re.search(text).groups()
        integer_str = groups[self.validator.group_map['integer']]
        fractional_str = groups[self.validator.group_map['fractional']]
        si_prefix = groups[self.validator.group_map['si']]

        if not integer_str:
            integer_str = '0'
        elif not fractional_str:
            fractional_str = '0'

        integer_value = int(integer_str)
        integer_str = integer_str.strip('+-')  # remove plus/minus sign
        if len(integer_str) < 3:
            integer_value += steps
        else:
            integer_value += steps * 10**(len(integer_str) - 2)

        float_str = '{0:d}.{1}'.format(integer_value, fractional_str)
        if si_prefix:
            float_str += ' {0}'.format(si_prefix)

        # constraint new value to allowed min/max range
        if fn.siEval(float_str) > self.maximum():
            float_str = self.textFromValue(self.maximum())
        elif fn.siEval(float_str) < self.minimum():
            float_str = self.textFromValue(self.minimum())

        if self.prefix():
            float_str = self.prefix() + float_str
        if self.suffix():
            float_str += self.suffix()

        self.lineEdit().setText(float_str)
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
