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

__all__ = ['ComplexLineEdit', 'ComplexValidator', 'DictLineEdit', 'DictValidator',
           'LiteralLineEdit', 'LiteralValidator', 'SetLineEdit', 'SetValidator', 'TupleLineEdit',
           'TupleValidator']

from PySide2 import QtCore, QtGui, QtWidgets
from typing import Any, Optional, Mapping, MutableSequence, Sequence, Set, FrozenSet, Union, List
from typing import Tuple, Dict
from copy import deepcopy
from qudi.util.helpers import is_complex


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
        self.textChanged.connect(self._on_text_changed, QtCore.Qt.DirectConnection)
        self.setValue(value)

    def setValue(self, value: Any) -> None:
        """
        """
        text = '' if value is None else self.validator().text_from_value(value)
        if text != self._last_valid_text:
            self.setText(text)

    def value(self) -> Any:
        """
        """
        return self.validator().value_from_text(self._last_valid_text)

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        self._revert_text()
        return super().focusOutEvent(event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            self._revert_text()
        return super().keyPressEvent(event)

    def _revert_text(self) -> None:
        text = self.text()
        if self.validator().validate(text, len(text)) != QtGui.QValidator.Acceptable:
            self.setText(self._last_valid_text)

    @QtCore.Slot(str)
    def _on_text_changed(self, text: Optional[str] = None) -> None:
        validator = self.validator()
        text = validator.fixup(text)
        if text != self._last_valid_text:
            if validator.validate(text, len(text)) == QtGui.QValidator.Acceptable:
                self._last_valid_text = text
                self.valueChanged.emit(validator.value_from_text(text))


class ComplexLineEdit(LiteralLineEdit):
    """
    """

    valueChanged = QtCore.Signal(complex)

    def __init__(self, value: Optional[complex] = None, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(value=value, parent=parent, validator=ComplexValidator())


class ListLineEdit(LiteralLineEdit):
    """
    """

    valueChanged = QtCore.Signal(list)

    def __init__(self, value: Optional[MutableSequence] = None,
                 parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(value=value, parent=parent, validator=ListValidator())


class TupleLineEdit(LiteralLineEdit):
    """
    """

    valueChanged = QtCore.Signal(tuple)

    def __init__(self, value: Optional[Sequence] = None,
                 parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(value=value, parent=parent, validator=TupleValidator())


class SetLineEdit(LiteralLineEdit):
    """
    """

    valueChanged = QtCore.Signal(set)

    def __init__(self, value: Optional[Union[Set, FrozenSet]] = None,
                 parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(value=value, parent=parent, validator=SetValidator())


class DictLineEdit(LiteralLineEdit):
    """
    """

    valueChanged = QtCore.Signal(dict)

    def __init__(self, value: Optional[Mapping] = None, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(value=value, parent=parent, validator=DictValidator())
