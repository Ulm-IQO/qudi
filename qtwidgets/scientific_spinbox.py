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

from qtpy import QtCore, QtGui, QtWidgets
import numpy as np
import re
from pyqtgraph import functions as fn
from decimal import Decimal as D  ## Use decimal to avoid accumulating floating-point errors
from decimal import getcontext, ROUND_FLOOR
import math

__all__ = ['ScienDSpinBox']


class FloatValidator(QtGui.QValidator):
    """
    This is a validator for float values represented as strings in scientific notation.
    (i.e. "1.35e-9", ".24E+8", "14e3" etc.)
    Also supports SI unit prefix like 'M', 'n' etc.
    """

    float_re = re.compile(r'((([+-]?\d+)\.?(\d*))?([eE][+-]?\d+)?\s?([YZEPTGMkmµunpfazy]?))')
    group_map = {'match': 0,
                 'mantissa': 1,
                 'integer': 2,
                 'fractional': 3,
                 'exponent': 4,
                 'si': 5
                 }

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

        groups = self.get_groups(string)
        if groups:
            if groups[self.group_map['match']] == string:
                return self.Acceptable, string, position

            if position > len(string):
                position = len(string)
            if string[position-1] in 'eE.-+':
                if string.count('.') > 1:
                    return self.Invalid, groups[self.group_map['match']], position
                return self.Intermediate, string, position

            return self.Invalid, groups[self.group_map['match']], position
        else:
            return self.Invalid, '', position

    def get_groups(self, string):
        match = self.float_re.search(string)
        if match:
            return match.groups()
        else:
            return False

    def fixup(self, text):
        match = self.float_re.search(text)
        if match:
            return match.groups()[0].strip()
        else:
            return ''


class ScienDSpinBox(QtWidgets.QAbstractSpinBox):
    """
    Wrapper Class from PyQt5 (or QtPy) to display a QDoubleSpinBox in Scientific way.
    Fully supports prefix and suffix functionality of the QDoubleSpinBox.
    Has built-in functionality to invoke the displayed number precision from the user input.

    This class can be directly used in Qt Designer by promoting the QDoubleSpinBox to ScienDSpinBox.
    State the path to this file (in python style, i.e. dots are separating the directories) as the
    header file and use the name of the present class.
    """

    valueChanged = QtCore.Signal(object)

    unit_prefix_dict = {
        'y': '1e-24',
        'z': '1e-21',
        'a': '1e-18',
        'f': '1e-15',
        'p': '1e-12',
        'n': '1e-9',
        'µ': '1e-6',
        'm': '1e-3',
        '': '1',
        'k': '1e3',
        'M': '1e6',
        'G': '1e9',
        'T': '1e12',
        'P': '1e15',
        'E': '1e18',
        'Z': '1e21',
        'Y': '1e24'
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__value = D(0)
        self.__minimum = -np.inf
        self.__maximum = np.inf
        self.__decimals = 2  # default in QtDesigner
        self.__prefix = ''
        self.__suffix = ''
        self.__singleStep = D('0.1')
        self.__minimalStep = D(0)
        self.__cached_value = None  # a temporary variable for restore functionality
        self._dynamic_stepping = True
        self._dynamic_precision = True
        self.validator = FloatValidator()
        self.editingFinished.connect(self.editingFinishedEvent)
        self.lineEdit().textEdited.connect(self.update_value)
        self.update_display()

    @property
    def dynamic_stepping(self):
        return bool(self._dynamic_stepping)

    @dynamic_stepping.setter
    def dynamic_stepping(self, use_dynamic_stepping):
        use_dynamic_stepping = bool(use_dynamic_stepping)
        self._dynamic_stepping = use_dynamic_stepping

    @property
    def dynamic_precision(self):
        return bool(self._dynamic_precision)

    @dynamic_precision.setter
    def dynamic_precision(self, use_dynamic_precision):
        use_dynamic_precision = bool(use_dynamic_precision)
        self._dynamic_precision = use_dynamic_precision

    def update_value(self):
        text = self.cleanText()
        value = self.valueFromText(text)
        if not value:
            return
        value, in_range = self.check_range(value)

        # save old value to be able to restore it later on
        if self.__cached_value is None:
            self.__cached_value = self.__value

        if float(value) != self.value():
            self.__value = value
            self.valueChanged.emit(self.value())
        else:
            self.__value = value

    def value(self):
        return float(self.__value)

    def setValue(self, value):
        try:
            value = D(value)
        except TypeError:
            if 'int' in type(value).__name__:
                value = int(value)
            elif 'float' in type(value).__name__:
                value = float(value)
            else:
                raise
            value = D(value)

        if value.is_nan():
            return

        value, in_range = self.check_range(value)

        if self.__value != value:
            # Try to increase decimals when the value has changed but no change in display detected.
            # This will only be executed when the dynamic precision flag is set
            if self.value() != float(value) and self.dynamic_precision and not value.is_infinite():
                old_text = self.cleanText()
                new_text = self.textFromValue(value).strip()
                current_dec = self.decimals()
                while old_text == new_text:
                    if self.__decimals > 20:
                        self.__decimals = current_dec
                        break
                    self.__decimals += 1
                    new_text = self.textFromValue(value).strip()
            self.__value = value
            self.update_display()
            self.valueChanged.emit(self.value())

    def check_range(self, value):
        if value < self.__minimum:
            new_value = self.__minimum
            in_range = False
        elif value > self.__maximum:
            new_value = self.__maximum
            in_range = False
        else:
            in_range = True
        if not in_range:
            value = D(new_value)
        return value, in_range

    def minimum(self):
        return float(self.__minimum)

    def setMinimum(self, minimum):
        self.__minimum = float(minimum)
        if self.__minimum > self.value():
            self.setValue(self.__minimum)

    def maximum(self):
        return float(self.__maximum)

    def setMaximum(self, maximum):
        self.__maximum = float(maximum)
        if self.__maximum < self.value():
            self.setValue(self.__maximum)

    def setRange(self, minimum, maximum):
        self.setMinimum(minimum)
        self.setMaximum(maximum)

    def decimals(self):
        return self.__decimals

    def setDecimals(self, decimals, dynamic_precision=True):
        decimals = int(decimals)
        # Restrict the number of fractional digits to a maximum of 20. Beyond that the number
        # is not very meaningful anyways due to machine precision. (even before that)
        if decimals < 0:
            decimals = 0
        elif decimals > 20:
            decimals = 20
        self.__decimals = decimals
        # Set the flag for using dynamic precision (decimals invoked from user input)
        self.dynamic_precision = dynamic_precision
        # Increase precision of decimal calculation if number of decimals exceed current settings
        # if self.__decimals >= getcontext().prec - 1:
        #     getcontext().prec = self.__decimals + 2
        # elif self.__decimals < 28 < getcontext().prec:
        #     getcontext().prec = 28  # The default precision

    def prefix(self):
        return self.__prefix

    def setPrefix(self, prefix):
        self.__prefix = str(prefix)
        self.update_display()

    def suffix(self):
        return self.__suffix

    def setSuffix(self, suffix):
        self.__suffix = str(suffix)
        self.update_display()

    def singleStep(self):
        return float(self.__singleStep)

    def setSingleStep(self, step, dynamic_stepping=True):
        try:
            step = D(step)
        except TypeError:
            if 'int' in type(step).__name__:
                step = int(step)
            elif 'float' in type(step).__name__:
                step = float(step)
            else:
                raise
            step = D(step)
        self.__singleStep = step
        self.dynamic_stepping = dynamic_stepping

    def minimalStep(self):
        return float(self.__minimalStep)

    def setMinimalStep(self, step):
        try:
            step = D(step)
        except TypeError:
            if 'int' in type(step).__name__:
                step = int(step)
            elif 'float' in type(step).__name__:
                step = float(step)
            else:
                raise
            step = D(step)
        self.__minimalStep = step

    def cleanText(self):
        text = self.text().strip()
        if self.__prefix and text.startswith(self.__prefix):
            text = text[len(self.__prefix):]
        if self.__suffix and text.endswith(self.__suffix):
            text = text[:-len(self.__suffix)]
        return text.strip()

    def update_display(self):
        """
        """
        text = self.textFromValue(self.value())
        text = self.__prefix + text + self.__suffix
        self.lineEdit().setText(text)
        self.__cached_value = None  # clear cached value
        self.clearFocus()

    def keyPressEvent(self, event):
        # Restore cached value upon pressing escape and lose focus.
        if event.key() == QtCore.Qt.Key_Escape:
            if self.__cached_value is not None:
                self.__value = self.__cached_value
                self.valueChanged.emit(self.value())
            self.clearFocus()  # This will also trigger editingFinished

        # The rest is to avoid editing suffix and prefix
        if (QtCore.Qt.ControlModifier | QtCore.Qt.MetaModifier) & event.modifiers():
            super().keyPressEvent(event)
            return

        if len(event.text()) > 0:
            cursor_pos = self.lineEdit().cursorPosition()
            begin = len(self.__prefix)
            end = len(self.text()) - len(self.__suffix)
            if cursor_pos < begin:
                self.lineEdit().setCursorPosition(begin)
                return
            elif cursor_pos > end:
                self.lineEdit().setCursorPosition(end)
                return

        if event.key() == QtCore.Qt.Key_Left:
            if self.lineEdit().cursorPosition() == len(self.__prefix):
                event.ignore()
                return
        if event.key() == QtCore.Qt.Key_Right:
            if self.lineEdit().cursorPosition() == len(self.text()) - len(self.__suffix):
                event.ignore()
                return
        if event.key() == QtCore.Qt.Key_Home:
            self.lineEdit().setCursorPosition(len(self.__prefix))
            return
        if event.key() == QtCore.Qt.Key_End:
            self.lineEdit().setCursorPosition(len(self.text()) - len(self.__suffix))
            return

        super().keyPressEvent(event)

    def validate(self, text, position):
        """
        Access method to the validator. See FloatValidator class for more information.

        @param text: str, string to be validated.
        @param position: int, current text cursor position
        @return: (enum QValidator::State) the returned validator state,
                 (str) the input string, (int) the cursor position
        """
        begin = len(self.__prefix)
        end = len(text) - len(self.__suffix)
        if position < begin:
            position = begin
        elif position > end:
            position = end

        if self.__prefix and text.startswith(self.__prefix):
            text = text[len(self.__prefix):]
        if self.__suffix and text.endswith(self.__suffix):
            text = text[:-len(self.__suffix)]

        state, string, position = self.validator.validate(text, position)

        text = self.__prefix + string + self.__suffix

        end = len(text) - len(self.__suffix)
        if position > end:
            position = end

        return state, text, position

    def fixup(self, text):
        """
        Takes an invalid string and tries to fix it in order to pass validation.
        The returned string is not guaranteed to pass validation.

        @param text: str, a string that has not passed validation in need to be fixed.
        @return: str, the resulting string from the fix attempt
        """
        print('fixup called on: "{0}"'.format(text))
        return self.validator.fixup(text)

    def valueFromText(self, text):
        """
        This method is responsible for converting a string displayed in the SpinBox into a float
        value.
        The input string is already stripped of prefix and suffix.
        Just the si-prefix may be present.

        @param text: str, the display string to be converted into a numeric value.
                          This string must be conform with the validator.
        @return: Decimal, the numeric value converted from the input string.
        """
        groups = self.validator.get_groups(text)
        group_map = self.validator.group_map
        if not groups:
            return False

        if not groups[group_map['mantissa']]:
            return False

        si_prefix = groups[group_map['si']]
        if si_prefix is not None:
            si_scale_str = self.unit_prefix_dict[si_prefix.replace('u', 'µ')]
        else:
            si_scale_str = '1'

        unscaled_value_str = groups[group_map['mantissa']]
        if groups[group_map['exponent']] is not None:
            unscaled_value_str += groups[group_map['exponent']]

        value = D(unscaled_value_str) * D(si_scale_str)

        # Try to extract the precision the user intends to use
        if self.dynamic_precision:
            if groups[group_map['fractional']] is not None:
                self.setDecimals(len(groups[group_map['fractional']]))

        return value

    def textFromValue(self, value):
        """
        This method is responsible for the mapping of the underlying value to a string to display
        in the SpinBox.
        Suffix and Prefix must not be handled here, just the si-Prefix.

        The main problem here is, that a scaled float with a suffix is represented by a different
        machine precision than the total value.
        This method is so complicated because it represents the actual precision of the value as
        float and not the precision of the scaled si float.
        '{:.20f}'.format(value) shows different digits than
        '{:.20f} {}'.format(scaled_value, si_prefix)

        @param value: float|decimal.Decimal, the numeric value to be formatted into a string
        @return: str, the formatted string representing the input value
        """
        # Catch infinity and NaN values
        if abs(value) == np.inf or abs(value) == np.nan:
            return ' '

        sign = '-' if value < 0 else ''
        fractional, integer = math.modf(abs(value))
        integer = int(integer)
        si_prefix = ''
        prefix_index = 0
        if integer != 0:
            integer_str = str(integer)
            fractional_str = ''
            while len(integer_str) > 3:
                fractional_str = integer_str[-3:] + fractional_str
                integer_str = integer_str[:-3]
                if prefix_index < 8:
                    si_prefix = 'kMGTPEZY'[prefix_index]
                else:
                    si_prefix = 'e{0:d}'.format(3 * (prefix_index + 1))
                prefix_index += 1
            # Truncate and round to set number of decimals
            # Add digits from fractional if it's not already enough for set self.__decimals
            if self.__decimals < len(fractional_str):
                round_indicator = int(fractional_str[self.__decimals])
                fractional_str = fractional_str[:self.__decimals]
                if round_indicator >= 5:
                    fractional_int = int(fractional_str) + 1
                    fractional_str = str(fractional_int)
            elif self.__decimals == len(fractional_str):
                if fractional >= 0.5:
                    if fractional_str:
                        fractional_int = int(fractional_str) + 1
                        fractional_str = str(fractional_int)
                    else:
                        fractional_str = '1'
            elif self.__decimals > len(fractional_str):
                digits_to_add = self.__decimals - len(fractional_str) # number of digits to add
                fractional_tmp_str = ('{0:.' + str(digits_to_add) + 'f}').format(fractional)
                if fractional_tmp_str.startswith('1'):
                    fractional_str = str(int(fractional_str) + 1) + '0' * digits_to_add
                else:
                    fractional_str += fractional_tmp_str.split('.')[1]
            # Check if the rounding has overflown the fractional part into the integer part
            if len(fractional_str) > self.__decimals:
                integer_str = str(int(integer_str) + 1)
                fractional_str = '0' * self.__decimals
        elif fractional == 0.0:
            fractional_str = '0' * self.__decimals
            integer_str = '0'
        else:
            # determine the order of magnitude by comparing the fractional to unit values
            prefix_index = 1
            magnitude = 1e-3
            si_prefix = 'm'
            while magnitude > fractional:
                prefix_index += 1
                magnitude = magnitude ** prefix_index
                if prefix_index <= 8:
                    si_prefix = 'mµnpfazy'[prefix_index - 1]  # use si-prefix if possible
                else:
                    si_prefix = 'e-{0:d}'.format(3 * prefix_index)  # use engineering notation
            # Get the string representation of all needed digits from the fractional part of value.
            digits_needed = 3 * prefix_index + self.__decimals
            helper_str = ('{0:.' + str(digits_needed) + 'f}').format(fractional)
            overflow = bool(int(helper_str.split('.')[0]))
            helper_str = helper_str.split('.')[1]
            if overflow:
                integer_str = '1000'
                fractional_str = '0' * self.__decimals
            elif (prefix_index - 1) > 0 and helper_str[3 * (prefix_index - 1) - 1] != '0':
                integer_str = '1000'
                fractional_str = '0' * self.__decimals
            else:
                integer_str = str(int(helper_str[:3 * prefix_index]))
                fractional_str = helper_str[3 * prefix_index:3 * prefix_index + self.__decimals]

        # Create the actual string representation of value scaled in a scientific way
        space = '' if si_prefix.startswith('e') else ' '
        if self.__decimals > 0:
            string = '{0}{1}.{2}{3}{4}'.format(sign, integer_str, fractional_str, space, si_prefix)
        else:
            string = '{0}{1}{2}{3}'.format(sign, integer_str, space, si_prefix)
        return string

    def stepEnabled(self):
        return self.StepUpEnabled | self.StepDownEnabled

    def stepBy(self, steps):
        """
        This method is incrementing the value of the SpinBox when the user triggers a step
        (by pressing PgUp/PgDown/Up/Down, MouseWheel movement or clicking on the arrows).
        It should handle the case when the new to-set value is out of bounds.
        Also the absolute value of a single step increment should be handled here.
        It is absolutely necessary to avoid accumulating rounding errors and/or discrepancy between
        self.value and the displayed text.

        @param steps: int, Number of steps to increment (NOT the absolute step size)
        """
        n = D(int(steps))  # n must be integral number of steps.
        s = [D(-1), D(1)][n >= 0]  # determine sign of step
        value = self.__value  # working copy of current value
        if self.dynamic_stepping:
            for i in range(int(abs(n))):
                if value == 0:
                    step = self.__minimalStep
                else:
                    vs = [D(-1), D(1)][value >= 0]
                    fudge = D('1.01') ** (s * vs)  # fudge factor. At some places, the step size
                                                   # depends on the step sign.
                    exp = abs(value * fudge).log10().quantize(1, rounding=ROUND_FLOOR)
                    step = self.__singleStep * D(10) ** exp
                    if self.__minimalStep > 0:
                        step = max(step, self.__minimalStep)
                value += s * step
        else:
            value = value + self.__singleStep * n
        self.setValue(value)
        return

    def editingFinishedEvent(self):
        self.update_display()
