# -*- coding: utf-8 -*-

"""
This module provides QWidget subclasses to enter different literals (complex, dict, list, tuple,
set).

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

__all__ = ['ComplexLineEdit', 'ComplexValidator', 'DictLineEdit', 'DictValidator', 'ListLineEdit',
           'ListValidator', 'LiteralLineEdit', 'LiteralValidator', 'SetLineEdit', 'SetValidator',
           'TupleLineEdit', 'TupleValidator']

from PySide2 import QtCore, QtGui, QtWidgets
from typing import Any, Optional, Mapping, MutableSequence, Sequence, Set, FrozenSet, Union, List
from typing import Tuple, Dict


class LiteralValidator(QtGui.QValidator):
    """
    """
    def __init__(self, parent: Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)

    def validate(self, text: str, position: int) -> QtGui.QValidator.State:
        """
        """
        try:
            self.value_from_text(text)
            return self.Acceptable
        except:
            return self.Intermediate

    def fixup(self, text: str) -> str:
        return text

    def value_from_text(self, text: str) -> Any:
        return eval(text)

    def text_from_value(self, value: Any) -> str:
        return repr(value)


class ComplexValidator(QtGui.QValidator):
    """
    """
    def __init__(self, parent: Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)

    def validate(self, text: str, position: int) -> QtGui.QValidator.State:
        """
        """
        try:
            self.value_from_text(text)
            return self.Acceptable
        except ValueError:
            return self.Intermediate

    def fixup(self, text: str) -> str:
        return text

    def value_from_text(self, text: str) -> complex:
        return complex(text)

    def text_from_value(self, value: complex) -> str:
        if value is None:
            value = complex()
        return repr(complex(value))


class ListValidator(QtGui.QValidator):
    """
    """
    def __init__(self, parent: Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)

    def validate(self, text: str, position: int) -> QtGui.QValidator.State:
        """
        """
        try:
            self.value_from_text(text)
            return self.Acceptable
        except:
            return self.Intermediate

    def fixup(self, text: str) -> str:
        return text

    def value_from_text(self, text: str) -> List[Any]:
        tmp = eval(text)
        if isinstance(tmp, (list, tuple)):
            return list(tmp)
        raise ValueError

    def text_from_value(self, value: MutableSequence[Any]) -> str:
        if value is None:
            value = list()
        return repr(list(value))


class TupleValidator(QtGui.QValidator):
    """
    """
    def __init__(self, parent: Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)

    def validate(self, text: str, position: int) -> QtGui.QValidator.State:
        """
        """
        try:
            self.value_from_text(text)
            return self.Acceptable
        except:
            return self.Intermediate

    def fixup(self, text: str) -> str:
        return text

    def value_from_text(self, text: str) -> Tuple[Any, ...]:
        tmp = eval(text)
        if isinstance(tmp, tuple):
            return tmp
        raise ValueError

    def text_from_value(self, value: Sequence[Any]) -> str:
        if value is None:
            value = tuple()
        return repr(tuple(value))


class SetValidator(QtGui.QValidator):
    """
    """
    def __init__(self, parent: Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)

    def validate(self, text: str, position: int) -> QtGui.QValidator.State:
        """
        """
        try:
            self.value_from_text(text)
            return self.Acceptable
        except:
            return self.Intermediate

    def fixup(self, text: str) -> str:
        return text

    def value_from_text(self, text: str) -> Set[Any]:
        tmp = eval(text)
        if isinstance(tmp, (tuple, set, frozenset)):
            return set(tmp)
        raise ValueError

    def text_from_value(self, value: Union[Set[Any], FrozenSet[Any]]) -> str:
        if value is None:
            value = set()
        return repr(set(value))


class DictValidator(QtGui.QValidator):
    """
    """
    def __init__(self, parent: Optional[QtCore.QObject] = None):
        super().__init__(parent=parent)

    def validate(self, text: str, position: int) -> QtGui.QValidator.State:
        """
        """
        try:
            self.value_from_text(text)
            return self.Acceptable
        except:
            return self.Intermediate

    def fixup(self, text: str) -> str:
        return text

    def value_from_text(self, text: str) -> Dict[Any, Any]:
        tmp = eval(text)
        if isinstance(tmp, dict):
            return tmp
        elif isinstance(tmp, tuple):
            return dict(tmp)
        raise ValueError

    def text_from_value(self, value: Mapping[Any, Any]) -> str:
        if value is None:
            value = dict()
        return repr(dict(value))


class LiteralLineEdit(QtWidgets.QLineEdit):
    """
    """

    valueChanged = QtCore.Signal(object)

    def __init__(self, value: Optional[Any] = None, parent: Optional[QtWidgets.QWidget] = None,
                 validator: Optional[QtGui.QValidator] = None):
        super().__init__(parent=parent)
        if validator is None:
            validator = LiteralValidator()
        self._last_valid_text = ''
        self.setValidator(validator)
        self.setValue(value)

    def setValue(self, value: Any) -> None:
        """
        """
        validator = self.validator()
        text = validator.fixup(validator.text_from_value(value))
        if self._new_text_valid(text):
            self.setText(text)
            self._last_valid_text = text
            self.valueChanged.emit(self.value())
        elif text != self._last_valid_text:
            raise ValueError

    def value(self) -> Any:
        """
        """
        return self.validator().value_from_text(self._last_valid_text)

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        self._revert_text()
        return super().focusOutEvent(event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        check_text = True
        if event.key() in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            self._revert_text()
            check_text = False
        ret_val = super().keyPressEvent(event)
        if check_text:
            text = self.text()
            if self._new_text_valid(text):
                self._last_valid_text = text
                self.valueChanged.emit(self.value())
        return ret_val

    def _revert_text(self) -> None:
        text = self.text()
        if self.validator().validate(text, len(text)) != QtGui.QValidator.Acceptable:
            self.setText(self._last_valid_text)

    def _new_text_valid(self, text: str) -> bool:
        """ Helper method to check if the given text is suitable to replace the current text as
        valid value.
        """
        if text != self._last_valid_text:
            validator = self.validator()
            return validator.validate(text, len(text)) == QtGui.QValidator.Acceptable
        return False


class ComplexLineEdit(LiteralLineEdit):
    """
    """

    valueChanged = QtCore.Signal(complex)

    def __init__(self, value: Optional[complex] = None, parent: Optional[QtWidgets.QWidget] = None):
        if value is None:
            value = complex()
        super().__init__(value=value, parent=parent, validator=ComplexValidator())


class ListLineEdit(LiteralLineEdit):
    """
    """

    valueChanged = QtCore.Signal(list)

    def __init__(self, value: Optional[MutableSequence] = None,
                 parent: Optional[QtWidgets.QWidget] = None):
        if value is None:
            value = list()
        super().__init__(value=value, parent=parent, validator=ListValidator())


class TupleLineEdit(LiteralLineEdit):
    """
    """

    valueChanged = QtCore.Signal(tuple)

    def __init__(self, value: Optional[Sequence] = None,
                 parent: Optional[QtWidgets.QWidget] = None):
        if value is None:
            value = tuple()
        super().__init__(value=value, parent=parent, validator=TupleValidator())


class SetLineEdit(LiteralLineEdit):
    """
    """

    valueChanged = QtCore.Signal(set)

    def __init__(self, value: Optional[Union[Set, FrozenSet]] = None,
                 parent: Optional[QtWidgets.QWidget] = None):
        if value is None:
            value = set()
        super().__init__(value=value, parent=parent, validator=SetValidator())


class DictLineEdit(LiteralLineEdit):
    """
    """

    valueChanged = QtCore.Signal(dict)

    def __init__(self, value: Optional[Mapping] = None, parent: Optional[QtWidgets.QWidget] = None):
        if value is None:
            value = dict()
        super().__init__(value=value, parent=parent, validator=DictValidator())
