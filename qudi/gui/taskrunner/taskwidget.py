# -*- coding: utf-8 -*-
"""
This file contains a widget to control a ModuleTask and display its state.

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

__all__ = ['TaskWidget']

import os
from typing import Type, Optional, Dict, Tuple, Any, Iterable
from PySide2 import QtCore, QtWidgets, QtGui

from qudi.util.helpers import is_integer
from qudi.util.paths import get_artwork_dir
from qudi.util.parameters import ParameterWidgetMapper
from qudi.util.widgets.loading_indicator import CircleLoadingIndicator
from qudi.core.scripting.moduletask import ModuleTask


class TestToolButton(QtWidgets.QToolButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self.setIconSize(event.size())


class TaskWidget(QtWidgets.QWidget):
    """ QWidget to control a ModuleTask and display its state.
    """

    sigStartTask = QtCore.Signal(dict)  # parameters
    sigInterruptTask = QtCore.Signal()

    _ParamWidgetsIterable = Iterable[Tuple[QtWidgets.QLabel, QtWidgets.QWidget]]
    _ParamWidgetsDict = Dict[str, Tuple[QtWidgets.QLabel, QtWidgets.QWidget]]

    def __init__(self, *args, task_type: Type[ModuleTask], max_columns: Optional[int] = None,
                 max_rows: Optional[int] = None, **kwargs):
        super().__init__(*args, **kwargs)

        if max_rows is not None and max_columns is not None:
            raise ValueError('Can either set "max_columns" OR "max_rows" but not both.')
        if max_columns is not None and not is_integer(max_columns):
            raise ValueError('"max_columns" must be None or integer value')
        if max_rows is not None and not is_integer(max_rows):
            raise ValueError('"max_rows" must be None or integer value')

        if max_rows is None and max_columns is None:
            max_rows = 8
        elif max_rows is None:
            number_of_widgets = len(task_type.call_parameters())
            max_rows = number_of_widgets // max_columns + number_of_widgets % max_columns

        # Create control button and state label. Arrange them in a sub-layout and connect button.
        # Also add animated busy-indicator
        icon_dir = os.path.join(get_artwork_dir(), 'icons', 'oxygen', 'source_svg')
        self._play_icon = QtGui.QIcon(os.path.join(icon_dir, 'media-playback-start.svgz'))
        self._stop_icon = QtGui.QIcon(os.path.join(icon_dir, 'media-playback-stop.svgz'))
        self.state_label = QtWidgets.QLabel('stopped')
        self.state_label.setAlignment(QtCore.Qt.AlignCenter)
        font = self.state_label.font()
        font.setBold(True)
        self.state_label.setFont(font)
        control_width = self.state_label.sizeHint().width() * 2
        self.run_interrupt_button = QtWidgets.QToolButton()
        self.run_interrupt_button.setIcon(self._play_icon)
        self.run_interrupt_button.setToolButtonStyle(QtGui.Qt.ToolButtonIconOnly)
        self.run_interrupt_button.setFixedWidth(control_width)
        self.run_interrupt_button.setFixedHeight(control_width)
        self.run_interrupt_button.setIconSize(self.run_interrupt_button.size())

        self.running_indicator = CircleLoadingIndicator()
        self.running_indicator.setFixedWidth(control_width // 1.5)
        self.running_indicator.setFixedHeight(control_width // 1.5)
        tmp = self.running_indicator.sizePolicy()
        tmp.setRetainSizeWhenHidden(True)
        self.running_indicator.setSizePolicy(tmp)
        ctrl_layout = QtWidgets.QVBoxLayout()
        ctrl_layout.addStretch(1)
        ctrl_layout.addWidget(self.running_indicator, 0, QtCore.Qt.AlignCenter)
        ctrl_layout.addWidget(self.state_label)
        ctrl_layout.addWidget(self.run_interrupt_button, 0, QtCore.Qt.AlignCenter)
        self.running_indicator.hide()

        self.run_interrupt_button.clicked.connect(self._run_interrupt_clicked)

        # Create task parameter editors and put them in a sub-layout
        self.parameter_widgets = self.__create_parameter_editor_widgets(task_type)
        param_layout = self.__layout_parameter_widgets(self.parameter_widgets.values(), max_rows)

        # Add sub-layouts to main layout
        line = QtWidgets.QFrame()
        line.setFrameShape(line.VLine)
        main_layout = QtWidgets.QHBoxLayout()
        main_layout.addLayout(param_layout)
        main_layout.addWidget(line)
        main_layout.addLayout(ctrl_layout)
        self.setLayout(main_layout)

        # State flag to indicate current button functionality (start or interrupt)
        self._interrupt_enabled = False

    @staticmethod
    def __create_parameter_editor_widgets(task_type: Type[ModuleTask]) -> _ParamWidgetsDict:
        """ Helper function to create editor widgets and labels for each ModuleTask call parameter
        """
        task_parameters = task_type.call_parameters()
        param_widgets = dict()
        for param_name, param in task_parameters.items():
            editor = ParameterWidgetMapper.widget_for_parameter(param)
            if editor is None:
                editor = QtWidgets.QLabel('Unknown parameter type')
                editor.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
            else:
                editor = editor()
                # ToDo: Set default values here
            label = QtWidgets.QLabel(f'{param_name}:')
            label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
            param_widgets[param_name] = (label, editor)
        return param_widgets

    @staticmethod
    def __layout_parameter_widgets(param_widgets: _ParamWidgetsIterable,
                                   max_rows: int) -> QtWidgets.QGridLayout:
        """ Helper function to layout parameter widgets in a QGridLayout """
        row = 0
        column = 0
        layout = QtWidgets.QGridLayout()
        layout.setColumnStretch(1, 1)
        max_height = 0
        for label, editor in param_widgets:
            layout.addWidget(label, row, column)
            layout.addWidget(editor, row, column + 1)
            max_height = max(max_height, editor.sizeHint().height())
            if row + 1 >= max_rows:
                row = 0
                column += 2
                layout.setColumnStretch(column + 1, 1)
            else:
                row += 1
        for ii in range(row):
            layout.setRowMinimumHeight(ii, max_height)
        layout.setRowStretch(row, 1)
        return layout

    @QtCore.Slot()
    def _run_interrupt_clicked(self) -> None:
        """ Callback method for button clicks """
        if self._interrupt_enabled:
            self.sigInterruptTask.emit()
        else:
            self.run_interrupt_button.setEnabled(False)
            self.sigStartTask.emit(self.get_parameters())

    @QtCore.Slot()
    def task_started(self) -> None:
        self._interrupt_enabled = True
        self.run_interrupt_button.setIcon(self._stop_icon)
        self.run_interrupt_button.setEnabled(True)
        self.running_indicator.show()

    @QtCore.Slot(str)
    def task_state_changed(self, new_state: str) -> None:
        """ Callback method for ModuleTask state changes """
        self.state_label.setText(new_state)

    @QtCore.Slot(object, bool)
    def task_finished(self, result: Any, success: bool) -> None:
        """ Callback for task finished event """
        self._interrupt_enabled = False
        self.run_interrupt_button.setIcon(self._play_icon)
        self.run_interrupt_button.setEnabled(True)
        self.running_indicator.hide()
        self.set_task_result(result, success)

    @QtCore.Slot(object, bool)
    def set_task_result(self, result: Any, success: bool) -> None:
        """ Updates the task result display """
        print(result, success)

    def get_parameters(self) -> Dict[str, Any]:
        """ Reads parameters from parameter editors and returns them in a dict """
        parameters = dict()
        for param_name, (_, editor) in self.parameter_widgets.items():
            if isinstance(editor, QtWidgets.QLabel):
                continue
            try:
                parameters[param_name] = editor.value()
            except AttributeError:
                try:
                    parameters[param_name] = editor.isChecked()
                except AttributeError:
                    parameters[param_name] = editor.text()
        return parameters
