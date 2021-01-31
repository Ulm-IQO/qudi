# -*- coding: utf-8 -*-

"""
ToDo: Document

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

import os
import weakref
from PySide2 import QtCore, QtWidgets, QtGui
from qudi.core.datafitting import FitContainer, FitConfigurationsModel, FitConfiguration
from qudi.core.util.paths import get_artwork_dir
from qudi.core.gui.qtwidgets.scientific_spinbox import ScienDSpinBox
from qudi.core import qudi_slot


class FitWidget(QtWidgets.QWidget):
    """
    """

    sigDoFit = QtCore.Signal(str)

    def __init__(self, *args, fit_container=None, **kwargs):
        super().__init__(*args, **kwargs)
        main_layout = QtWidgets.QGridLayout()
        self.setLayout(main_layout)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.selection_combobox = QtWidgets.QComboBox()
        self.selection_combobox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.fit_pushbutton = QtWidgets.QPushButton('Fit')
        self.fit_pushbutton.setMinimumWidth(3 * self.fit_pushbutton.sizeHint().width())
        self.result_label = QtWidgets.QLabel()
        self.result_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        main_layout.addWidget(self.fit_pushbutton, 0, 0)
        main_layout.addWidget(self.selection_combobox, 0, 1)
        main_layout.addWidget(self.result_label, 1, 0, 1, 2)
        main_layout.setColumnStretch(1, 1)

        self.fit_pushbutton.clicked.connect(self._fit_clicked)

        self.__fit_container_ref = lambda: None
        if fit_container is not None:
            self.link_fit_container(fit_container)

    def link_fit_container(self, fit_container):
        assert (fit_container is None) or isinstance(fit_container, FitContainer), \
            'Can only link qudi FitContainer instances.'
        old_container = self.__fit_container_ref()
        # disconnect old fit container if present
        if old_container is not None:
            old_container.sigFitConfigurationsChanged.disconnect(self.update_fit_configurations)
            old_container.sigLastFitResultChanged.disconnect(self.update_fit_result)
        # link new fit container
        self.result_label.clear()
        self.selection_combobox.clear()
        if fit_container is None:
            self.__fit_container_ref = lambda: None
        else:
            self.__fit_container_ref = weakref.ref(fit_container)
            self.selection_combobox.addItems(fit_container.fit_configuration_names)
            fit_container.sigFitConfigurationsChanged.connect(
                self.update_fit_configurations, QtCore.Qt.QueuedConnection
            )
            fit_container.sigLastFitResultChanged.connect(
                self.update_fit_result, QtCore.Qt.QueuedConnection
            )

    @qudi_slot(tuple)
    def update_fit_configurations(self, config_names):
        old_text = self.selection_combobox.currentText()
        self.selection_combobox.clear()
        self.selection_combobox.addItems(config_names)
        if old_text in config_names:
            self.selection_combobox.setCurrentText(old_text)

    @qudi_slot(str, object)
    def update_fit_result(self, fit_config, fit_result):
        if fit_config is not None:
            container = self.__fit_container_ref()
            if container is not None:
                if self.selection_combobox.currentText() != fit_config:
                    self.selection_combobox.setCurrentText(fit_config)
                self.result_label.setText(container.formatted_result(fit_result))

    @qudi_slot()
    def _fit_clicked(self):
        config = self.selection_combobox.currentText()
        self.sigDoFit.emit(config)


class FitConfigPanel(QtWidgets.QWidget):
    """
    """
    sigConfigurationRemovedClicked = QtCore.Signal(str)

    def __init__(self, *args, fit_config, **kwargs):
        assert isinstance(fit_config, FitConfiguration)
        super().__init__(*args, **kwargs)
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        groupbox = QtWidgets.QGroupBox(fit_config.name)
        font = groupbox.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 4)
        groupbox.setFont(font)
        layout.addWidget(groupbox)
        main_layout = QtWidgets.QVBoxLayout()
        groupbox.setLayout(main_layout)

        # add remove button
        icon_dir = os.path.join(get_artwork_dir(), 'icons', 'oxygen', '64x64')
        self._name = fit_config.name
        self.remove_config_toolbutton = QtWidgets.QToolButton()
        self.remove_config_toolbutton.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self.remove_config_toolbutton.setIcon(
            QtGui.QIcon(os.path.join(icon_dir, 'remove-icon.png'))
        )
        self.remove_config_toolbutton.clicked.connect(
            lambda: self.sigConfigurationRemovedClicked.emit(self._name)
        )

        # add estimator combobox
        self.estimator_selection_combobox = QtWidgets.QComboBox()
        self.estimator_selection_combobox.addItems(fit_config.available_estimators)
        self.estimator_selection_combobox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        label = QtWidgets.QLabel('Estimator:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        hlayout = QtWidgets.QHBoxLayout()
        main_layout.addLayout(hlayout)
        hlayout.addWidget(label)
        hlayout.addWidget(self.estimator_selection_combobox)
        hlayout.addStretch(1)
        hlayout.addWidget(self.remove_config_toolbutton)

        # add horizontal line
        hline = QtWidgets.QFrame()
        hline.setFrameShape(QtWidgets.QFrame.HLine)
        main_layout.addWidget(hline)

        # add parameters
        param_layout = QtWidgets.QGridLayout()
        main_layout.addLayout(param_layout)
        label = QtWidgets.QLabel('customize?')
        param_layout.addWidget(label, 0, 0)
        label = QtWidgets.QLabel('vary?')
        param_layout.addWidget(label, 0, 2)
        label = QtWidgets.QLabel('init:')
        param_layout.addWidget(label, 0, 3)
        label = QtWidgets.QLabel('min:')
        param_layout.addWidget(label, 0, 4)
        label = QtWidgets.QLabel('max:')
        param_layout.addWidget(label, 0, 5)
        # determine minimum width for SpinBoxes based on font metrics
        min_width = QtGui.QFontMetrics(label.font()).horizontalAdvance('999.999')
        self.parameters_widgets = dict()
        row = 1
        for param_name, param in fit_config.default_parameters.items():
            customize_checkbox = QtWidgets.QCheckBox()
            param_layout.addWidget(customize_checkbox, row, 0)
            label = QtWidgets.QLabel(param_name + ':')
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            param_layout.addWidget(label, row, 1)
            vary_checkbox = QtWidgets.QCheckBox()
            vary_checkbox.setChecked(param.vary)
            customize_checkbox.toggled.connect(vary_checkbox.setEnabled)
            param_layout.addWidget(vary_checkbox, row, 2)
            init_spinbox = ScienDSpinBox()
            init_spinbox.setMinimumWidth(min_width)
            init_spinbox.setRange(param.min, param.max)
            init_spinbox.setValue(param.value)
            customize_checkbox.toggled.connect(init_spinbox.setEnabled)
            param_layout.addWidget(init_spinbox, row, 3)
            min_spinbox = ScienDSpinBox()
            min_spinbox.setMinimumWidth(min_width)
            min_spinbox.setRange(param.min, param.max)
            min_spinbox.setValue(param.min)
            customize_checkbox.toggled.connect(min_spinbox.setEnabled)
            param_layout.addWidget(min_spinbox, row, 4)
            max_spinbox = ScienDSpinBox()
            max_spinbox.setMinimumWidth(min_width)
            max_spinbox.setRange(param.min, param.max)
            max_spinbox.setValue(param.max)
            customize_checkbox.toggled.connect(max_spinbox.setEnabled)
            param_layout.addWidget(max_spinbox, row, 5)
            self.parameters_widgets[param_name] = (
                customize_checkbox, vary_checkbox, init_spinbox, min_spinbox, max_spinbox
            )
            row += 1
        param_layout.setColumnStretch(3, 1)
        param_layout.setColumnStretch(4, 1)
        param_layout.setColumnStretch(5, 1)
        self.update_fit_config(fit_config)

    @property
    def estimator(self):
        return self.estimator_selection_combobox.currentText()

    @property
    def custom_parameters(self):
        parameters = dict()
        for param_name, widgets in self.parameters_widgets.items():
            if widgets[0].isChecked():
                parameters[param_name] = (widgets[1].isChecked(),
                                          widgets[2].value(),
                                          widgets[3].value(),
                                          widgets[4].value())
        return parameters

    def update_fit_config(self, config):
        self.blockSignals(True)
        self.estimator_selection_combobox.setCurrentText(config.estimator)
        custom_params = config.custom_parameters
        for param_name, widgets in self.parameters_widgets.items():
            customize = (custom_params is not None) and (param_name in custom_params)
            widgets[0].setChecked(customize)
            widgets[1].setEnabled(customize)
            widgets[2].setEnabled(customize)
            widgets[3].setEnabled(customize)
            widgets[4].setEnabled(customize)
            if customize:
                param = custom_params[param_name]
                widgets[1].setChecked(param.vary)
                widgets[2].setValue(param.value)
                widgets[3].setValue(param.min)
                widgets[4].setValue(param.max)
        self.blockSignals(False)


class FitConfigurationItemDelegate(QtWidgets.QStyledItemDelegate):
    """
    """

    def createEditor(self, parent, option, index):
        if index.isValid():
            print('createEditor:', index.row())
            editor = FitConfigPanel(parent=parent, fit_config=index.data(QtCore.Qt.DisplayRole))
            editor.setGeometry(option.rect)
            editor.sigConfigurationRemovedClicked.connect(self.parent().remove_config_clicked)
            return editor
        return None

    def setEditorData(self, editor, index):
        if index.isValid():
            editor.update_fit_config(index.data(QtCore.Qt.DisplayRole))

    def setModelData(self, editor, model, index):
        print('setModelData:', index.row())
        data = (editor.estimator, editor.custom_parameters)
        model.setData(index, data)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)
        return option.rect

    def sizeHint(self, option, index):
        size = FitConfigPanel(fit_config=index.data(QtCore.Qt.DisplayRole)).sizeHint()
        return size

    def paint(self, painter, option, index):
        painter.save()
        r = option.rect
        painter.translate(r.topLeft())
        widget = FitConfigPanel(fit_config=index.data(QtCore.Qt.DisplayRole))
        widget.setGeometry(r)
        widget.render(painter, QtCore.QPoint(0, 0), painter.viewport())
        painter.restore()

    def destroyEditor(self, editor, index):
        print('destroyEditor:', index.row())
        editor.sigConfigurationRemovedClicked.disconnect()
        self.setModelData(editor, index.model(), index)
        return super().destroyEditor(editor, index)


class FitConfigurationListView(QtWidgets.QListView):
    """
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setVerticalScrollMode(self.ScrollPerPixel)
        self.setMouseTracking(True)
        self.installEventFilter(self)
        config_item_delegate = FitConfigurationItemDelegate(parent=self)
        self.setItemDelegate(config_item_delegate)
        self.__previous_index = QtCore.QModelIndex()

    def mouseMoveEvent(self, event):
        curr_index = self.indexAt(event.pos())
        if curr_index != self.__previous_index:
            if self.__previous_index.isValid():
                self.closePersistentEditor(self.__previous_index)
            if curr_index.isValid():
                self.openPersistentEditor(curr_index)
            self.__previous_index = curr_index
        return super().mouseMoveEvent(event)

    def eventFilter(self, object, event):
        if event.type() == QtCore.QEvent.HoverLeave:
            if not self.geometry().contains(event.pos()):
                if self.__previous_index.isValid():
                    self.closePersistentEditor(self.__previous_index)
                self.__previous_index = QtCore.QModelIndex()
                return True
        return False

    def remove_config_clicked(self, config_name):
        if self.__previous_index.isValid():
            self.closePersistentEditor(self.__previous_index)
        self.__previous_index = QtCore.QModelIndex()
        self.model().remove_configuration(config_name)


class FitConfigurationWidget(QtWidgets.QWidget):
    """
    """
    _sigAddNewConfig = QtCore.Signal(str, str)  # name, model

    def __init__(self, *args, fit_config_model, **kwargs):
        assert isinstance(fit_config_model, FitConfigurationsModel)
        super().__init__(*args, **kwargs)
        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)
        main_layout.setContentsMargins(0, 0, 0, 0)

        icon_dir = os.path.join(get_artwork_dir(), 'icons', 'oxygen', '64x64')

        # Create new fit config editor elements
        self.model_combobox = QtWidgets.QComboBox()
        self.model_combobox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.model_combobox.addItems(fit_config_model.model_names)
        self.name_lineedit = QtWidgets.QLineEdit()
        self.add_config_toolbutton = QtWidgets.QToolButton()
        self.add_config_toolbutton.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self.add_config_toolbutton.setIcon(QtGui.QIcon(os.path.join(icon_dir, 'add-icon.png')))
        hlayout = QtWidgets.QHBoxLayout()
        hlayout.addWidget(self.model_combobox)
        hlayout.addWidget(self.name_lineedit)
        hlayout.addWidget(self.add_config_toolbutton)
        hlayout.setContentsMargins(0, 0, 0, 0)
        # hlayout.setStretch(0, 1)
        hlayout.setStretch(1, 1)
        main_layout.addLayout(hlayout)

        # Create fit config editor list view
        self.config_listview = FitConfigurationListView()
        self.config_listview.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self.config_listview.setModel(fit_config_model)
        main_layout.addWidget(self.config_listview)
        main_layout.setStretch(1, 1)

        self.add_config_toolbutton.clicked.connect(self._add_config_clicked)
        self._sigAddNewConfig.connect(
            fit_config_model.add_configuration, QtCore.Qt.QueuedConnection
        )

    @qudi_slot()
    def _add_config_clicked(self):
        model = self.model_combobox.currentText()
        name = self.name_lineedit.text()
        if name and model:
            self.name_lineedit.clear()
            self._sigAddNewConfig.emit(name, model)
