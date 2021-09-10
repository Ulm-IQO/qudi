# -*- coding: utf-8 -*-
"""
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

__all__ = ['ParameterEditor', 'ParameterEditorDialog']

import inspect
from typing import Any, Optional, Dict, Mapping, Callable
from PySide2 import QtCore, QtWidgets

from qudi.util.parameters import ParameterWidgetMapper


class ParameterEditor(QtWidgets.QWidget):
    """ Dynamically created editor widget for callable parameters.
    For best results use default values and simple type annotations in the callable to create the
    editor for.
    """
    INVALID = object()

    def __init__(self, *args, func: Callable, values: Optional[Mapping[str, Any]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        if values is None:
            values = dict()
        self.parameter_editors = dict()
        layout = QtWidgets.QGridLayout()
        parameters = inspect.signature(func).parameters
        for row, (name, param) in enumerate(parameters.items()):
            label = QtWidgets.QLabel(f'{name}:')
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            editor = ParameterWidgetMapper.widget_for_parameter(param)
            if editor is None:
                editor = QtWidgets.QLabel('Unknown argument type!')
                editor.setAlignment(QtCore.Qt.AlignCenter)
            else:
                editor = editor()
                # Attempt to set default value
                if not ((param.default is inspect.Parameter.empty) and (name not in values)):
                    try:
                        init_value = values[name]
                    except KeyError:
                        init_value = param.default

                    try:
                        editor.setValue(init_value)
                    except AttributeError:
                        try:
                            editor.setChecked(init_value)
                        except AttributeError:
                            try:
                                editor.setText(init_value)
                            except AttributeError:
                                pass

            layout.addWidget(label, row, 0)
            layout.addWidget(editor, row, 1)
            self.parameter_editors[name] = editor
        self.setLayout(layout)

    def get_parameter_values(self) -> Dict[str, Any]:
        """ Returns the current parameter values entered into the editor """
        values = dict()
        for name, editor in self.parameter_editors.items():
            if isinstance(editor, QtWidgets.QLabel):
                values[name] = self.INVALID
            else:
                try:
                    values[name] = editor.value()
                except AttributeError:
                    try:
                        values[name] = editor.isChecked()
                    except AttributeError:
                        try:
                            values[name] = editor.text()
                        except AttributeError:
                            pass
        return values


class ParameterEditorDialog(QtWidgets.QDialog):
    """ QDialog containing a ParameterEditor widget and OK, Cancel and Apply buttons.
    Is non-modal by default but can be configured like any other QDialog.
    """
    def __init__(self, *args, func: Callable, values: Optional[Mapping[str, Any]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.setModal(False)
        self.parameter_editor = ParameterEditor(func=func, values=values)
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidget(self.parameter_editor)
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok |
            QtWidgets.QDialogButtonBox.Cancel |
            QtWidgets.QDialogButtonBox.Apply,
            orientation=QtCore.Qt.Horizontal
        )
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.scroll_area)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        # Connect signals
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.accept)
        self.button_box.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(self.reject)
