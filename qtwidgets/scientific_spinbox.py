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
"""

from qtpy import QtCore, QtGui, QtWidgets
import numpy as np
import re
from decimal import Decimal as D  # Use decimal to avoid accumulating floating-point errors
from decimal import ROUND_FLOOR
import math

__all__ = ['ScienDSpinBox', 'ScienSpinBox']


class FloatValidator(QtGui.QValidator):
    """
    This is a validator for float values represented as strings in scientific notation.
    (i.e. "1.35e-9", ".24E+8", "14e3" etc.)
    Also supports SI unit prefix like 'M', 'n' etc.
    """

    float_re = re.compile(r'(\s*([+-]?)(\d+\.\d+|\.\d+|\d+\.?)([eE][+-]?\d+)?\s?([YZEPTGMkmµunpfazy]?)\s*)')
    group_map = {'match': 0,
                 'sign': 1,
                 'mantissa': 2,
                 'exponent': 3,
                 'si': 4}

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
        # Return intermediate status when empty string is passed or when incomplete "[+-]inf"
        if string.strip() in '+.-.' or string.strip() in list('YZEPTGMkmµunpfazy') or re.match(
                r'[+-]?(in$|i$)', string, re.IGNORECASE):
            return self.Intermediate, string, position

        # Accept input of [+-]inf. Not case sensitive.
        if re.match(r'[+-]?\binf$', string, re.IGNORECASE):
            return self.Acceptable, string.lower(), position

        group_dict = self.get_group_dict(string)
        if group_dict:
            if group_dict['match'] == string:
                return self.Acceptable, string, position
            if string.count('.') > 1:
                return self.Invalid, group_dict['match'], position
            if position > len(string):
                position = len(string)
            if string[position-1] in 'eE-+' and 'i' not in string.lower():
                return self.Intermediate, string, position
            return self.Invalid, group_dict['match'], position
        else:
            if string[position-1] in 'eE-+.' and 'i' not in string.lower():
                return self.Intermediate, string, position
            return self.Invalid, '', position

    def get_group_dict(self, string):
        """
        This method will match the input string with the regular expression of this validator.
        The match groups will be put into a dictionary with string descriptors as keys describing
        the role of the specific group (i.e. mantissa, exponent, si-prefix etc.)

        @param string: str, input string to be matched
        @return: dictionary containing groups as items and descriptors as keys (see: self.group_map)
        """
        match = self.float_re.search(string)
        if not match:
            return False
        groups = match.groups()
        group_dict = dict()
        for group_key in self.group_map:
            group_dict[group_key] = groups[self.group_map[group_key]]
        return group_dict

    def fixup(self, text):
        match = self.float_re.search(text)
        if match:
            return match.groups()[0].strip()
        else:
            return ''


class IntegerValidator(QtGui.QValidator):
    """
    This is a validator for int values represented as strings in scientific notation.
    Using engeneering notation only positive exponents are allowed
    (i.e. "1e9", "2E+8", "14e+3" etc.)
    Also supports non-fractional SI unit prefix like 'M', 'k' etc.
    """

    int_re = re.compile(r'(([+-]?\d+)([eE]\+?\d+)?\s?([YZEPTGMk])?\s*)')
    group_map = {'match': 0,
                 'mantissa': 1,
                 'exponent': 2,
                 'si': 3
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
        if not string.strip() or string.strip() in list('YZEPTGMk'):
            return self.Intermediate, string, position

        group_dict = self.get_group_dict(string)
        if group_dict:
            if group_dict['match'] == string:
                return self.Acceptable, string, position

            if position > len(string):
                position = len(string)
            if string[position-1] in 'eE-+':
                return self.Intermediate, string, position

            return self.Invalid, group_dict['match'], position
        else:
            return self.Invalid, '', position

    def get_group_dict(self, string):
        """
        This method will match the input string with the regular expression of this validator.
        The match groups will be put into a dictionary with string descriptors as keys describing
        the role of the specific group (i.e. mantissa, exponent, si-prefix etc.)

        @param string: str, input string to be matched
        @return: dictionary containing groups as items and descriptors as keys (see: self.group_map)
        """
        match = self.int_re.search(string)
        if not match:
            return False
        groups = match.groups()
        group_dict = dict()
        for group_key in self.group_map:
            group_dict[group_key] = groups[self.group_map[group_key]]
        return group_dict

    def fixup(self, text):
        match = self.int_re.search(text)
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

    # The maximum number of decimals to allow. Be careful when changing this number since
    # the decimal package has by default a limited accuracy.
    __max_decimals = 20
    # Dictionary mapping the si-prefix to a scaling factor as decimal.Decimal (exact value)
    _unit_prefix_dict = {
        'y': D('1e-24'),
        'z': D('1e-21'),
        'a': D('1e-18'),
        'f': D('1e-15'),
        'p': D('1e-12'),
        'n': D('1e-9'),
        'µ': D('1e-6'),
        'm': D('1e-3'),
        '': D('1'),
        'k': D('1e3'),
        'M': D('1e6'),
        'G': D('1e9'),
        'T': D('1e12'),
        'P': D('1e15'),
        'E': D('1e18'),
        'Z': D('1e21'),
        'Y': D('1e24')
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__value = D(0)
        self.__minimum = -np.inf
        self.__maximum = np.inf
        self.__decimals = 2  # default in QtDesigner
        self.__prefix = ''
        self.__suffix = ''
        self.__singleStep = D('0.1')  # must be precise Decimal always, no conversion from float
        self.__minimalStep = D(0)  # must be precise Decimal always, no conversion from float
        self.__cached_value = None  # a temporary variable for restore functionality
        self._dynamic_stepping = True
        self._dynamic_precision = True
        self._assumed_unit_prefix = None  # To assume one prefix. This is only used if no prefix would be out of range
        self._is_valid = True  # A flag property to check if the current value is valid.
        self.validator = FloatValidator()
        self.lineEdit().textEdited.connect(self.update_value)
        self.update_display()

    @property
    def dynamic_stepping(self):
        """
        This property is a flag indicating if the dynamic (logarithmic) stepping should be used or
        not (fixed steps).

        @return: bool, use dynamic stepping (True) or constant steps (False)
        """
        return bool(self._dynamic_stepping)

    @dynamic_stepping.setter
    def dynamic_stepping(self, use_dynamic_stepping):
        """
        This property is a flag indicating if the dynamic (logarithmic) stepping should be used or
        not (fixed steps).

        @param use_dynamic_stepping: bool, use dynamic stepping (True) or constant steps (False)
        """
        use_dynamic_stepping = bool(use_dynamic_stepping)
        self._dynamic_stepping = use_dynamic_stepping

    @property
    def dynamic_precision(self):
        """
        This property is a flag indicating if the dynamic (invoked from user input) decimal
        precision should be used or not (fixed number of digits).

        @return: bool, use dynamic precision (True) or fixed precision (False)
        """
        return bool(self._dynamic_precision)

    @dynamic_precision.setter
    def dynamic_precision(self, use_dynamic_precision):
        """
        This property is a flag indicating if the dynamic (invoked from user input) decimal
        precision should be used or not (fixed number of digits).

        @param use_dynamic_precision: bool, use dynamic precision (True) or fixed precision (False)
        """
        use_dynamic_precision = bool(use_dynamic_precision)
        self._dynamic_precision = use_dynamic_precision

    @property
    def assumed_unit_prefix(self):
        """
        This property can fix a default unit prefix that is used for text input.

        @return: None or prefix string
        """
        return self._assumed_unit_prefix

    @assumed_unit_prefix.setter
    def assumed_unit_prefix(self, unit_prefix):
        """
        This property can fix a default unit prefix that is used for text input.

        @param unit_prefix: None or unit prefix in the dictionary
        """
        if unit_prefix is None or unit_prefix in self._unit_prefix_dict:
            self._assumed_unit_prefix = unit_prefix
        if unit_prefix == 'u':  # in case of encoding problems
            self._assumed_unit_prefix = 'µ'

    @property
    def is_valid(self):
        """
        This property is a flag indicating if the currently available value is valid.
        It will return False if there has been an attempt to set NaN as current value.
        Will return True after a valid value has been set.

        @return: bool, current value invalid (False) or current value valid (True)
        """
        return bool(self._is_valid)

    def update_value(self):
        """
        This method will grab the currently shown text from the QLineEdit and interpret it.
        Range checking is performed on the value afterwards.
        If a valid value can be derived, it will set this value as the current value
        (if it has changed) and emit the valueChanged signal.
        Note that the comparison between old and new value is done by comparing the float
        representations of both values and not by comparing them as Decimals.
        The valueChanged signal will only emit if the actual float representation has changed since
        Decimals are only internally used and the rest of the program won't notice a slight change
        in the Decimal that can't be resolved in a float.
        In addition it will cache the old value provided the cache is empty to be able to restore
        it later on.
        """
        text = self.cleanText()
        value = self.valueFromText(text)
        if value is False:
            return
        value, in_range = self.check_range(value)
        # if the value is out of range, then only use assumed unit prefix
        if not in_range and self._assumed_unit_prefix is not None:
            value = self.valueFromText(text, use_assumed_unit_prefix=True)
            value, in_range = self.check_range(value)
        # save old value to be able to restore it later on
        if self.__cached_value is None:
            self.__cached_value = self.__value

        if float(value) != self.value():
            self.__value = value
            self.valueChanged.emit(self.value())
        else:
            self.__value = value
        self._is_valid = True

    def value(self):
        """
        Getter method to obtain the current value as float.

        @return: float, the current value of the SpinBox
        """
        return float(self.__value)

    def setValue(self, value):
        """
        Setter method to programmatically set the current value. For best robustness pass the value
        as string or Decimal in order to be lossless cast into Decimal.
        Will perform range checking and ignore NaN values.
        Will emit valueChanged if the new value is different from the old one.
        When using dynamic decimals precision, this method will also try to invoke the optimal
        display precision by checking for a change in the displayed text.
        """
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

        # catch NaN values and set the "is_valid" flag to False until a valid value is set again.
        if value.is_nan():
            self._is_valid = False
            return

        value, in_range = self.check_range(value)

        if self.__value != value or not self.is_valid:
            # Try to increase decimals when the value has changed but no change in display detected.
            # This will only be executed when the dynamic precision flag is set
            if self.value() != float(value) and self.dynamic_precision and not value.is_infinite():
                old_text = self.cleanText()
                new_text = self.textFromValue(value).strip()
                current_dec = self.decimals()
                while old_text == new_text:
                    if self.__decimals > self.__max_decimals:
                        self.__decimals = current_dec
                        break
                    self.__decimals += 1
                    new_text = self.textFromValue(value).strip()
            self.__value = value
            self._is_valid = True
            self.update_display()
            self.valueChanged.emit(self.value())

    def setProperty(self, prop, val):
        """
        For compatibility with QtDesigner. Somehow the value gets initialized through this method.
        @param prop:
        @param val:
        """
        if prop == 'value':
            self.setValue(val)
        else:
            raise UserWarning('setProperty in scientific spinboxes only works for "value".')

    def check_range(self, value):
        """
        Helper method to check if the passed value is within the set minimum and maximum value
        bounds.
        If outside of bounds the returned value will be clipped to the nearest boundary.

        @param value: float|Decimal, number to be checked
        @return: (Decimal, bool), the corrected value and a flag indicating if the value has been
                                  changed (False) or not (True)
        """

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
        """
        Setter method to set the minimum value allowed in the SpinBox.
        Input will be converted to float before being stored.

        @param minimum: float, the minimum value to be set
        """
        # Ignore NaN values
        if self._check_nan(float(minimum)):
            return

        self.__minimum = float(minimum)
        if self.__minimum > self.value():
            self.setValue(self.__minimum)

    def maximum(self):
        return float(self.__maximum)

    def setMaximum(self, maximum):
        """
        Setter method to set the maximum value allowed in the SpinBox.
        Input will be converted to float before being stored.

        @param maximum: float, the maximum value to be set
        """
        # Ignore NaN values
        if self._check_nan(float(maximum)):
            return

        self.__maximum = float(maximum)
        if self.__maximum < self.value():
            self.setValue(self.__maximum)

    def setRange(self, minimum, maximum):
        """
        Convenience method for compliance with Qt SpinBoxes.
        Essentially a wrapper to call both self.setMinimum and self.setMaximum.

        @param minimum: float, the minimum value to be set
        @param maximum: float, the maximum value to be set
        """
        self.setMinimum(minimum)
        self.setMaximum(maximum)

    def decimals(self):
        return self.__decimals

    def setDecimals(self, decimals, dynamic_precision=True):
        """
        Method to set the number of displayed digits after the decimal point.
        Also specifies if the dynamic precision functionality should be used or not.
        If dynamic_precision=True the number of decimals will be invoked from the number of
        decimals entered by the user in the QLineEdit of this spinbox. The set decimal value will
        only be used before the first explicit user text input or call to self.setValue.
        If dynamic_precision=False the specified number of decimals will be fixed and will not be
        changed except by calling this method.

        @param decimals: int, the number of decimals to be displayed
        @param dynamic_precision: bool, flag indicating the use of dynamic_precision
        """
        decimals = int(decimals)
        # Restrict the number of fractional digits to a maximum of self.__max_decimals = 20.
        # Beyond that the number is not very meaningful anyways due to machine precision.
        if decimals < 0:
            decimals = 0
        elif decimals > self.__max_decimals:
            decimals = self.__max_decimals
        self.__decimals = decimals
        # Set the flag for using dynamic precision (decimals invoked from user input)
        self.dynamic_precision = dynamic_precision

    def prefix(self):
        return self.__prefix

    def setPrefix(self, prefix):
        """
        Set a string to be shown as non-editable prefix in the spinbox.

        @param prefix: str, the prefix string to be set
        """
        self.__prefix = str(prefix)
        self.update_display()

    def suffix(self):
        return self.__suffix

    def setSuffix(self, suffix):
        """
        Set a string to be shown as non-editable suffix in the spinbox.
        This suffix will come right after the si-prefix.

        @param suffix: str, the suffix string to be set
        """
        self.__suffix = str(suffix)
        self.update_display()

    def singleStep(self):
        return float(self.__singleStep)

    def setSingleStep(self, step, dynamic_stepping=True):
        """
        Method to set the stepping behaviour of the spinbox (e.g. when moving the mouse wheel).

        When dynamic_stepping=True the spinbox will perform logarithmic steps according to the
        values' current order of magnitude. The step parameter is then referring to the step size
        relative to the values order of magnitude. Meaning step=0.1 would step increment the second
        most significant digit by one etc.

        When dynamic_stepping=False the step parameter specifies an absolute step size. Meaning each
        time a step is performed this value is added/substracted from the current value.

        For maximum roboustness and consistency it is strongly recommended to pass step as Decimal
        or string in order to be converted lossless to Decimal.

        @param step: Decimal|str, the (relative) step size to set
        @param dynamic_stepping: bool, flag indicating the use of dynamic stepping (True) or
                                       constant stepping (False)
        """
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

        # ignore NaN and infinity values
        if not step.is_nan() and not step.is_infinite():
            self.__singleStep = step

        self.dynamic_stepping = dynamic_stepping

    def minimalStep(self):
        return float(self.__minimalStep)

    def setMinimalStep(self, step):
        """
        Method used to set a minimal step size.
        When the absolute step size has been calculated in either dynamic or constant step mode
        this value is checked against the minimal step size. If it is smaller then the minimal step
        size is chosen over the calculated step size. This ensures that no step taken can be
        smaller than minimalStep.
        Set this value to 0 for no minimal step size.

        For maximum roboustness and consistency it is strongly recommended to pass step as Decimal
        or string in order to be converted lossless to Decimal.

        @param step: Decimal|str, the minimal step size to be set
        """
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

        # ignore NaN and infinity values
        if not step.is_nan() and not step.is_infinite():
            self.__minimalStep = step

    def cleanText(self):
        """
        Compliance method from Qt SpinBoxes.
        Returns the currently shown text from the QLineEdit without prefix and suffix and stripped
        from leading or trailing whitespaces.

        @return: str, currently shown text stripped from suffix and prefix
        """
        text = self.text().strip()
        if self.__prefix and text.startswith(self.__prefix):
            text = text[len(self.__prefix):]
        if self.__suffix and text.endswith(self.__suffix):
            text = text[:-len(self.__suffix)]
        return text.strip()

    def update_display(self):
        """
        This helper method updates the shown text based on the current value.
        Because this method is only called upon finishing an editing procedure, the eventually
        cached value gets deleted.
        """
        text = self.textFromValue(self.value())
        text = self.__prefix + text + self.__suffix
        self.lineEdit().setText(text)
        self.__cached_value = None  # clear cached value
        self.lineEdit().setCursorPosition(0)  # Display the most significant part of the number

    def keyPressEvent(self, event):
        """
        This method catches all keyboard press events triggered by the user. Can be used to alter
        the behaviour of certain key events from the default implementation of QAbstractSpinBox.

        @param event: QKeyEvent, a Qt QKeyEvent instance holding the event information
        """
        # Restore cached value upon pressing escape and lose focus.
        if event.key() == QtCore.Qt.Key_Escape:
            if self.__cached_value is not None:
                self.__value = self.__cached_value
                self.valueChanged.emit(self.value())
            self.clearFocus()  # This will also trigger editingFinished
            return

        # Update display upon pressing enter/return before processing the event in the default way.
        if event.key() == QtCore.Qt.Key_Enter or event.key() == QtCore.Qt.Key_Return:
            self.update_display()

        if (QtCore.Qt.ControlModifier | QtCore.Qt.MetaModifier) & event.modifiers():
            super().keyPressEvent(event)
            return

        # The rest is to avoid editing suffix and prefix
        if len(event.text()) > 0:
            # Allow editing of the number or SI-prefix even if part of the prefix/suffix is selected.
            if self.lineEdit().selectedText():
                sel_start = self.lineEdit().selectionStart()
                sel_end = sel_start + len(self.lineEdit().selectedText())
                min_start = len(self.__prefix)
                max_end = len(self.__prefix) + len(self.cleanText())
                if sel_start < min_start:
                    sel_start = min_start
                if sel_end > max_end:
                    sel_end = max_end
                self.lineEdit().setSelection(sel_start, sel_end - sel_start)
            else:
                cursor_pos = self.lineEdit().cursorPosition()
                begin = len(self.__prefix)
                end = len(self.text()) - len(self.__suffix)
                if cursor_pos < begin:
                    self.lineEdit().setCursorPosition(begin)
                elif cursor_pos > end:
                    self.lineEdit().setCursorPosition(end)

        if event.key() == QtCore.Qt.Key_Left:
            if self.lineEdit().cursorPosition() == len(self.__prefix):
                return
        if event.key() == QtCore.Qt.Key_Right:
            if self.lineEdit().cursorPosition() == len(self.text()) - len(self.__suffix):
                return
        if event.key() == QtCore.Qt.Key_Home:
            self.lineEdit().setCursorPosition(len(self.__prefix))
            return
        if event.key() == QtCore.Qt.Key_End:
            self.lineEdit().setCursorPosition(len(self.text()) - len(self.__suffix))
            return

        super().keyPressEvent(event)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.selectAll()
        return

    def focusOutEvent(self, event):
        self.update_display()
        super().focusOutEvent(event)
        return

    def paintEvent(self, ev):
        """
        Add drawing of a red frame around the spinbox if the is_valid flag is False
        """
        super().paintEvent(ev)

        # draw red frame if is_valid = False
        if not self.is_valid:
            pen = QtGui.QPen()
            pen.setColor(QtGui.QColor(200, 50, 50))
            pen.setWidth(2)

            p = QtGui.QPainter(self)
            p.setRenderHint(p.Antialiasing)
            p.setPen(pen)
            p.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 4, 4)
            p.end()

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
        return self.validator.fixup(text)

    def valueFromText(self, text, use_assumed_unit_prefix=False):
        """
        This method is responsible for converting a string displayed in the SpinBox into a Decimal.

        The input string is already stripped of prefix and suffix.
        Just the si-prefix may be present.

        @param text: str, the display string to be converted into a numeric value.
                          This string must be conform with the validator.
        @return: Decimal, the numeric value converted from the input string.
        """
        # Check for infinite value
        if 'inf' in text.lower():
            if text.startswith('-'):
                return D('-inf')
            else:
                return D('inf')

        # Handle "normal" (non-infinite) input
        group_dict = self.validator.get_group_dict(text)
        if not group_dict:
            return False

        if not group_dict['mantissa']:
            return False

        si_prefix = group_dict['si']
        if si_prefix is None:
            si_prefix = ''
        if si_prefix == '' and use_assumed_unit_prefix and self._assumed_unit_prefix is not None:
            si_prefix = self._assumed_unit_prefix
        si_scale = self._unit_prefix_dict[si_prefix.replace('u', 'µ')]

        if group_dict['sign'] is not None:
            unscaled_value_str = group_dict['sign'] + group_dict['mantissa']
        else:
            unscaled_value_str = group_dict['mantissa']
        if group_dict['exponent'] is not None:
            unscaled_value_str += group_dict['exponent']

        value = D(unscaled_value_str) * si_scale

        # Try to extract the precision the user intends to use
        if self.dynamic_precision:
            split_mantissa = group_dict['mantissa'].split('.')
            if len(split_mantissa) == 2:
                self.setDecimals(max(len(split_mantissa[1]), 1))
            else:
                self.setDecimals(1)  # Minimum number of digits is 1

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
        # Catch infinity value
        if np.isinf(float(value)):
            if value < 0:
                return '-inf '
            else:
                return 'inf '

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
                    if not fractional_str:
                        fractional_str = '1'
                    else:
                        fractional_str = str(int(fractional_str) + 1)
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
                    if fractional_str:
                        fractional_str = str(int(fractional_str) + 1) + '0' * digits_to_add
                    else:
                        fractional_str = '1' + '0' * digits_to_add
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
        """
        Enables stepping (mouse wheel, arrow up/down, clicking, PgUp/Down) by default.
        """
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
        # Ignore stepping for infinity values
        if self.__value.is_infinite():
            return

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
            value = value + max(self.__minimalStep * n, self.__singleStep * n)
        self.setValue(value)
        return

    def selectAll(self):
        begin = len(self.__prefix)
        text = self.cleanText()
        if text.endswith(' '):
            selection_length = len(text) + 1
        elif len(text) > 0 and text[-1] in self._unit_prefix_dict:
            selection_length = len(text) - 1
        else:
            selection_length = len(text)
        self.lineEdit().setSelection(begin, selection_length)

    @staticmethod
    def _check_nan(value):
        """
        Helper method to check if the passed float value is NaN.
        Makes use of the fact that NaN values will always compare to false, even with itself.

        @param value: Decimal|float, value to be checked for NaN
        @return: (bool) is NaN (True), is no NaN (False)
        """
        return not value == value

    # Property added as a temporary fix so that Qudi mapper works with this Class.
    # When moving to PySide2, it won't be necessary any longer
    value_float = QtCore.Property(float, fget=value, fset=setValue, notify=valueChanged)


class ScienSpinBox(QtWidgets.QAbstractSpinBox):
    """
    Wrapper Class from PyQt5 (or QtPy) to display a QSpinBox in Scientific way.
    Fully supports prefix and suffix functionality of the QSpinBox.

    This class can be directly used in Qt Designer by promoting the QSpinBox to ScienSpinBox.
    State the path to this file (in python style, i.e. dots are separating the directories) as the
    header file and use the name of the present class.
    """

    valueChanged = QtCore.Signal(object)
    # Dictionary mapping the si-prefix to a scaling factor as integer (exact value)
    _unit_prefix_dict = {
        '': 1,
        'k': 10 ** 3,
        'M': 10 ** 6,
        'G': 10 ** 9,
        'T': 10 ** 12,
        'P': 10 ** 15,
        'E': 10 ** 18,
        'Z': 10 ** 21,
        'Y': 10 ** 24
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__value = 0
        self.__minimum = -2 ** 63  # Use a 64bit integer size by default.
        self.__maximum = 2 ** 63 - 1  # Use a 64bit integer size by default.
        self.__prefix = ''
        self.__suffix = ''
        self.__singleStep = 1
        self.__minimalStep = 1
        self.__cached_value = None  # a temporary variable for restore functionality
        self._dynamic_stepping = True
        self.validator = IntegerValidator()
        self.lineEdit().textEdited.connect(self.update_value)
        self.update_display()

    @property
    def dynamic_stepping(self):
        """
        This property is a flag indicating if the dynamic (logarithmic) stepping should be used or
        not (fixed steps).

        @return: bool, use dynamic stepping (True) or constant steps (False)
        """
        return bool(self._dynamic_stepping)

    @dynamic_stepping.setter
    def dynamic_stepping(self, use_dynamic_stepping):
        """
        This property is a flag indicating if the dynamic (logarithmic) stepping should be used or
        not (fixed steps).

        @param use_dynamic_stepping: bool, use dynamic stepping (True) or constant steps (False)
        """
        use_dynamic_stepping = bool(use_dynamic_stepping)
        self._dynamic_stepping = use_dynamic_stepping

    def update_value(self):
        """
        This method will grab the currently shown text from the QLineEdit and interpret it.
        Range checking is performed on the value afterwards.
        If a valid value can be derived, it will set this value as the current value
        (if it has changed) and emit the valueChanged signal.
        In addition it will cache the old value provided the cache is empty to be able to restore
        it later on.
        """
        text = self.cleanText()
        value = self.valueFromText(text)
        if value is False:
            return
        value, in_range = self.check_range(value)

        # save old value to be able to restore it later on
        if self.__cached_value is None:
            self.__cached_value = self.__value

        if value != self.value():
            self.__value = value
            self.valueChanged.emit(self.value())

    def value(self):
        """
        Getter method to obtain the current value as int.

        @return: int, the current value of the SpinBox
        """
        return int(self.__value)

    def setValue(self, value):
        """
        Setter method to programmatically set the current value.
        Will perform range checking and ignore NaN values.
        Will emit valueChanged if the new value is different from the old one.
        """
        if value is np.nan:
            return

        value = int(value)

        value, in_range = self.check_range(value)

        if self.__value != value:
            self.__value = value
            self.update_display()
            self.valueChanged.emit(self.value())

    def setProperty(self, prop, val):
        """
        For compatibility with QtDesigner. Somehow the value gets initialized through this method.
        @param prop:
        @param val:
        """
        if prop == 'value':
            self.setValue(val)
        else:
            raise UserWarning('setProperty in scientific spinboxes only works for "value".')

    def check_range(self, value):
        """
        Helper method to check if the passed value is within the set minimum and maximum value
        bounds.
        If outside of bounds the returned value will be clipped to the nearest boundary.

        @param value: int, number to be checked
        @return: (int, bool), the corrected value and a flag indicating if the value has been
                              changed (False) or not (True)
        """
        if value < self.__minimum:
            new_value = self.__minimum
            in_range = False
        elif value > self.__maximum:
            new_value = self.__maximum
            in_range = False
        else:
            in_range = True
        if not in_range:
            value = int(new_value)
        return value, in_range

    def minimum(self):
        return int(self.__minimum)

    def setMinimum(self, minimum):
        """
        Setter method to set the minimum value allowed in the SpinBox.
        Input will be converted to int before being stored.

        @param minimum: int, the minimum value to be set
        """
        self.__minimum = int(minimum)
        if self.__minimum > self.value():
            self.setValue(self.__minimum)

    def maximum(self):
        return int(self.__maximum)

    def setMaximum(self, maximum):
        """
        Setter method to set the maximum value allowed in the SpinBox.
        Input will be converted to int before being stored.

        @param maximum: int, the maximum value to be set
        """
        self.__maximum = int(maximum)
        if self.__maximum < self.value():
            self.setValue(self.__maximum)

    def setRange(self, minimum, maximum):
        """
        Convenience method for compliance with Qt SpinBoxes.
        Essentially a wrapper to call both self.setMinimum and self.setMaximum.

        @param minimum: int, the minimum value to be set
        @param maximum: int, the maximum value to be set
        """
        self.setMinimum(minimum)
        self.setMaximum(maximum)

    def prefix(self):
        return self.__prefix

    def setPrefix(self, prefix):
        """
        Set a string to be shown as non-editable prefix in the spinbox.

        @param prefix: str, the prefix string to be set
        """
        self.__prefix = str(prefix)
        self.update_display()

    def suffix(self):
        return self.__suffix

    def setSuffix(self, suffix):
        """
        Set a string to be shown as non-editable suffix in the spinbox.
        This suffix will come right after the si-prefix.

        @param suffix: str, the suffix string to be set
        """
        self.__suffix = str(suffix)
        self.update_display()

    def singleStep(self):
        return int(self.__singleStep)

    def setSingleStep(self, step, dynamic_stepping=True):
        """
        Method to set the stepping behaviour of the spinbox (e.g. when moving the mouse wheel).

        When dynamic_stepping=True the spinbox will perform logarithmic steps according to the
        values' current order of magnitude. The step parameter is then ignored.
        Will always increment the second most significant digit by one.

        When dynamic_stepping=False the step parameter specifies an absolute step size. Meaning each
        time a step is performed this value is added/substracted from the current value.

        @param step: int, the absolute step size to set
        @param dynamic_stepping: bool, flag indicating the use of dynamic stepping (True) or
                                       constant stepping (False)
        """
        if step < 1:
            step = 1
        self.__singleStep = int(step)
        self.dynamic_stepping = dynamic_stepping

    def minimalStep(self):
        return int(self.__minimalStep)

    def setMinimalStep(self, step):
        """
        Method used to set a minimal step size.
        When the absolute step size has been calculated in either dynamic or constant step mode
        this value is checked against the minimal step size. If it is smaller then the minimal step
        size is chosen over the calculated step size. This ensures that no step taken can be
        smaller than minimalStep.
        Minimal step size can't be smaller than 1 for integer.

        @param step: int, the minimal step size to be set
        """
        if step < 1:
            step = 1
        self.__minimalStep = int(step)

    def cleanText(self):
        """
        Compliance method from Qt SpinBoxes.
        Returns the currently shown text from the QLineEdit without prefix and suffix and stripped
        from leading or trailing whitespaces.

        @return: str, currently shown text stripped from suffix and prefix
        """
        text = self.text().strip()
        if self.__prefix and text.startswith(self.__prefix):
            text = text[len(self.__prefix):]
        if self.__suffix and text.endswith(self.__suffix):
            text = text[:-len(self.__suffix)]
        return text.strip()

    def update_display(self):
        """
        This helper method updates the shown text based on the current value.
        Because this method is only called upon finishing an editing procedure, the eventually
        cached value gets deleted.
        """
        text = self.textFromValue(self.value())
        text = self.__prefix + text + self.__suffix
        self.lineEdit().setText(text)
        self.__cached_value = None  # clear cached value
        self.lineEdit().setCursorPosition(0)  # Display the most significant part of the number

    def keyPressEvent(self, event):
        """
        This method catches all keyboard press events triggered by the user. Can be used to alter
        the behaviour of certain key events from the default implementation of QAbstractSpinBox.

        @param event: QKeyEvent, a Qt QKeyEvent instance holding the event information
        """
        # Restore cached value upon pressing escape and lose focus.
        if event.key() == QtCore.Qt.Key_Escape:
            if self.__cached_value is not None:
                self.__value = self.__cached_value
                self.valueChanged.emit(self.value())
            self.clearFocus()  # This will also trigger editingFinished

        # Update display upon pressing enter/return before processing the event in the default way.
        if event.key() == QtCore.Qt.Key_Enter or event.key() == QtCore.Qt.Key_Return:
            self.update_display()

        if (QtCore.Qt.ControlModifier | QtCore.Qt.MetaModifier) & event.modifiers():
            super().keyPressEvent(event)
            return

        # The rest is to avoid editing suffix and prefix
        if len(event.text()) > 0:
            # Allow editing of the number or SI-prefix even if part of the prefix/suffix is selected.
            if self.lineEdit().selectedText():
                sel_start = self.lineEdit().selectionStart()
                sel_end = sel_start + len(self.lineEdit().selectedText())
                min_start = len(self.__prefix)
                max_end = len(self.__prefix) + len(self.cleanText())
                if sel_start < min_start:
                    sel_start = min_start
                if sel_end > max_end:
                    sel_end = max_end
                self.lineEdit().setSelection(sel_start, sel_end - sel_start)
            else:
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
                return
        if event.key() == QtCore.Qt.Key_Right:
            if self.lineEdit().cursorPosition() == len(self.text()) - len(self.__suffix):
                return
        if event.key() == QtCore.Qt.Key_Home:
            self.lineEdit().setCursorPosition(len(self.__prefix))
            return
        if event.key() == QtCore.Qt.Key_End:
            self.lineEdit().setCursorPosition(len(self.text()) - len(self.__suffix))
            return

        super().keyPressEvent(event)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.selectAll()
        return

    def focusOutEvent(self, event):
        self.update_display()
        super().focusOutEvent(event)
        return

    def validate(self, text, position):
        """
        Access method to the validator. See IntegerValidator class for more information.

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
        return self.validator.fixup(text)

    def valueFromText(self, text):
        """
        This method is responsible for converting a string displayed in the SpinBox into an int
        value.
        The input string is already stripped of prefix and suffix.
        Just the si-prefix may be present.

        @param text: str, the display string to be converted into a numeric value.
                          This string must be conform with the validator.
        @return: int, the numeric value converted from the input string.
        """
        group_dict = self.validator.get_group_dict(text)
        if not group_dict:
            return False

        if not group_dict['mantissa']:
            return False

        si_prefix = group_dict['si']
        if si_prefix is None:
            si_prefix = ''
        si_scale = self._unit_prefix_dict[si_prefix.replace('u', 'µ')]

        unscaled_value = int(group_dict['mantissa'])
        if group_dict['exponent'] is not None:
            scale_factor = 10 ** int(group_dict['exponent'].replace('e', '').replace('E', ''))
            unscaled_value = unscaled_value * scale_factor

        value = unscaled_value * si_scale
        return value

    def textFromValue(self, value):
        """
        This method is responsible for the mapping of the underlying value to a string to display
        in the SpinBox.
        Suffix and Prefix must not be handled here, just the si-Prefix.

        @param value: int, the numeric value to be formatted into a string
        @return: str, the formatted string representing the input value
        """
        # Convert the integer value to a string
        sign = '-' if value < 0 else ''
        value_str = str(abs(value))

        # find out the index of the least significant non-zero digit
        for digit_index in range(len(value_str)):
            if value_str[digit_index:].count('0') == len(value_str) - digit_index:
                break

        # get the engineering notation exponent (multiple of 3)
        missing_zeros = (len(value_str) - digit_index) % 3
        exponent = len(value_str) - digit_index - missing_zeros

        # the scaled integer string that is still missing the order of magnitude (si-prefix or e)
        integer_str = value_str[:digit_index + missing_zeros]

        space = ' ' if self.__suffix else ''
        # Add si-prefix or, if the exponent is too big, add e-notation
        if 2 < exponent <= 24:
            si_prefix = ' ' + 'kMGTPEZY'[exponent // 3 - 1]
        elif exponent > 24:
            si_prefix = 'e{0:d}'.format(exponent) + space
        else:
            si_prefix = space

        # Assemble the string and return it
        return sign + integer_str + si_prefix

    def stepEnabled(self):
        """
        Enables stepping (mouse wheel, arrow up/down, clicking, PgUp/Down) by default.
        """
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
        steps = int(steps)
        value = self.__value  # working copy of current value
        sign = -1 if steps < 0 else 1  # determine sign of step
        if self.dynamic_stepping:
            for i in range(abs(steps)):
                if value == 0:
                    step = max(1, self.__minimalStep)
                else:
                    integer_str = str(abs(value))
                    if len(integer_str) > 1:
                        step = 10 ** (len(integer_str) - 2)
                        # Handle the transition to lower order of magnitude
                        if integer_str.startswith('10') and (sign * value) < 0:
                            step = step // 10
                    else:
                        step = 1

                    step = max(step, self.__minimalStep)

                value += sign * step
        else:
            value = value + max(self.__minimalStep * steps, self.__singleStep * steps)

        self.setValue(value)
        return

    def selectAll(self):
        begin = len(self.__prefix)
        text = self.cleanText()
        if text.endswith(' '):
            selection_length = len(text) + 1
        elif len(text) > 0 and text[-1] in self._unit_prefix_dict:
            selection_length = len(text) - 1
        else:
            selection_length = len(text)
        self.lineEdit().setSelection(begin, selection_length)

    # Property added as a temporary fix so that Qudi mapper works with this Class.
    # When moving to PySide2, it won't be necessary any longer
    value_int = QtCore.Property(float, fget=value, fset=setValue, notify=valueChanged)
