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
from decimal import getcontext

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
        'u': '1e-6',
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
        self.__value = D(0.0)
        self.__minimum = -np.inf
        self.__maximum = np.inf
        self.__decimals = 3
        self.__prefix = ''
        self.__suffix = ''
        self.__singleStep = D('1.0')
        self.__minimalStep = D('0.0')
        self.validator = FloatValidator()
        self.dynamic_stepping = True
        self.dynamic_precision = True
        self.editingFinished.connect(self.editingFinishedEvent)
        self.lineEdit().textEdited.connect(self.test)

    def test(self, text):
        print('That was AWESOME!')
        text = self.cleanText()
        value = self.valueFromText(text)
        value, in_range = self.check_range(value)
        if self.__value != value:
            self.__value = value
            self.valueChanged.emit(self.value())
        #     new_text = self.textFromValue()
        # self.setValue(value)
        # value, in_range = self.check_range(value)
        # if self.__value != value:
        #     self.__value = value
        #     self.valueChanged.emit(self.value())
        #     string
        #
        # text = self.__prefix + string + self.__suffix

    def value(self):
        return float(self.__value)

    def setValue(self, value):
        value = D(value)
        value, in_range = self.check_range(value)

        if self.__value != value:
            self.__value = value
            self.update_display()
            self.valueChanged.emit(self.value())

    def check_range(self, value):
        if value < self.__minimum:
            value = self.__minimum
            in_range = False
        elif value > self.__maximum:
            value = self.__maximum
            in_range = False
        else:
            in_range = True
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

    def setDecimals(self, decimals):
        self.__decimals = int(decimals)
        # Increase precision of decimal calculation if number of decimals exceed current settings
        if self.__decimals >= getcontext().prec - 1:
            getcontext().prec = self.__decimals + 2
        elif self.__decimals < 28 < getcontext().prec:
            getcontext().prec = 28  # The default precision

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

    def setSingleStep(self, step):
        self.__singleStep = D(step)

    def minimalStep(self):
        return float(self.__minimalStep)

    def setMinimalStep(self, step):
        self.__minimalStep = D(step)

    def cleanText(self):
        text = self.text().strip()
        if self.__prefix and text.startswith(self.__prefix):
            text = text[len(self.__prefix):]
        if self.__suffix and text.endswith(self.__suffix):
            text = text[:-len(self.__suffix)]
        return text.strip()

    def update_display(self):
        """

        @return:
        """
        text = self.textFromValue(self.value())
        text = self.__prefix + text + self.__suffix
        self.lineEdit().setText(text)

    def keyPressEvent(self, event):
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

        print('VALIDATION BABY!!! {0}'.format(text))
        state, string, position = self.validator.validate(text, position)

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
        print('FIXUP CALLED!!!')
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
            si_scale_str = self.unit_prefix_dict[si_prefix]
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

        @param value: float, the numeric value to be formatted into a string
        @return: str, the formatted string representing the input value
        """
        print(float(value))

        scale_factor, si_prefix = si_scale(value)
        scaled_val = value * scale_factor
        print(float(scaled_val))
        string = ('{0:.' + str(self.__decimals) + 'f}').format(float(scaled_val))
        string += ' ' + si_prefix
        return string

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
        if self.dynamic_stepping:
            text = self.text()
            groups = self.validator.float_re.search(text).groups()
            integer_str = groups[self.validator.group_map['integer']]
            fractional_str = groups[self.validator.group_map['fractional']]
            si_prefix = groups[self.validator.group_map['si']]

            if not integer_str:
                integer_str = '0'
            if not fractional_str:
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
        else:
            text = self.text()
            value = self.value()
            new_value = value + steps * self.singleStep()
            self.setValue(new_value)
            while text == self.text():
                self.precision += 1
                self.setValue(value)
                text = self.text()
                self.setValue(new_value)
                # raise UserWarning('The set step size is much smaller than the displayed magnitude.')
        return

    def editingFinishedEvent(self):
        print('YEAP')
        self.update_display()

    def si_scale(x):
        """
        Return the recommended scale factor and SI prefix string for x.

        Example::

            siScale(0.0001)   # returns (1e6, 'μ')
            # This indicates that the number 0.0001 is best represented as 0.0001 * 1e6 = 100 μUnits
        """
        try:
            if isinstance(x, decimal.Decimal):
                if x.is_infinite() or x.is_nan():
                    return 1, ''
            else:
                if np.isnan(x) or np.isinf(x):
                    return 1, ''
        except:
            print(x, type(x))
            raise

        exponent = int(math.log10(abs(x)) // 3)

        if exponent == 0:
            prefix = ''
        elif exponent > 8 or exponent < -8:
            prefix = 'e{0:d}'.format(exponent)
        else:
            prefix = 'yzafpnµm kMGTPEZY'[8 + exponent]

        if isinstance(x, decimal.Decimal):
            scale_factor = decimal.Decimal('0.001') ** exponent
        else:
            scale_factor = 0.001 ** exponent

        return scale_factor, prefix


    # def setSingleStep(self, val, dynamic_stepping=True):
    #     """
    #     Pass call to this method to parent implementation.
    #     Additionally set flag indicating if the dynamic stepping should be used (default) or not.
    #     The specified step size will only be used if the dynamic_stepping is set to False.
    #
    #     @param val: float|str, the absolute step size for a single step.
    #                        Unused if dynamic_stepping=True.
    #     @param dynamic_stepping: bool, Flag indicating if the absolute step size should be used.
    #     """
    #     super().setSingleStep(val)
    #     self.dynamic_stepping = dynamic_stepping
    #     return
    #
    # def setDecimals(self, digits, dynamic_precision=True):
    #     """
    #     Overwrite the parent implementation in order to always have max digits available.
    #     Set the number of fractional digits to display though.
    #
    #     @param digits: int, number of fractional digits to show.
    #     @param dynamic_precision: Flag to set if dynamic precision should be enabled
    #     """
    #     super().setDecimals(1000)
    #     self.precision = digits
    #     self.dynamic_precision = dynamic_precision
    #     return
