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
from qudi.core.datafitting import FitContainer
from qudi.core import qudi_slot
from qudi.core.util.paths import get_artwork_dir


class FitWidget(QtWidgets.QWidget):
    """
    """

    sigDoFit = QtCore.Signal(str)

    def __init__(self, *args, fit_container=None, **kwargs):
        super().__init__(*args, **kwargs)
        main_layout = QtWidgets.QGridLayout()
        self.setLayout(main_layout)

        self.selection_combobox = QtWidgets.QComboBox()
        self.fit_pushbutton = QtWidgets.QPushButton('Fit')
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
        assert isinstance(fit_container, FitContainer) or fit_container is None, \
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

    @qudi_slot(dict)
    def update_fit_configurations(self, fit_configs):
        old_text = self.selection_combobox.currentText()
        self.selection_combobox.clear()
        self.selection_combobox.addItems(tuple(fit_configs))
        if old_text in fit_configs:
            self.selection_combobox.setCurrentText(old_text)

    @qudi_slot(object, object)
    def update_fit_result(self, fit_config, fit_result):
        if self.selection_combobox.currentText() != fit_config.name:
            self.selection_combobox.setCurrentText(fit_config.name)
        self.result_label.setText(fit_config.formatted_result(fit_result))

    @qudi_slot()
    def _fit_clicked(self):
        config = self.selection_combobox.currentText()
        self.sigDoFit.emit(config)


class FitConfigurationWidget(QtWidgets.QWidget):
    """
    """

    def __init__(self, *args, fit_containers=None, **kwargs):
        super().__init__(*args, **kwargs)
        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        icon_dir = os.path.join(get_artwork_dir(), 'icons', 'oxygen', '64x64')

        # Create new fit config editor elements
        self.model_combobox = QtWidgets.QComboBox()
        self.model_combobox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
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
        self.config_listview = QtWidgets.QListView()
        self.config_listview.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        main_layout.addWidget(self.config_listview)
        main_layout.setStretch(1, 1)

        self.add_config_toolbutton.clicked.connect(self._add_config_clicked)

        self.__fit_container_refs = list()

    def link_fit_containers(self, fit_containers):
        assert all(isinstance(fc, FitContainer) for fc in fit_containers) or not fit_containers, \
            'Can only link qudi FitContainer instances.'
        old_containers = [fc_ref() for fc_ref in self.__fit_container_refs]
        old_containers = [fc for fc in old_containers if fc is not None]
        self.__fit_container_refs.clear()
        # disconnect old fit container if present
        # ToDo: update fit containers in config model
        for fc in old_containers:
            pass
        # link new fit container
        self.model_combobox.clear()
        if fit_containers:
            fc = fit_containers[0]
            self.model_combobox.addItems(fc.model_names)
            self.__fit_container_refs.extend(weakref.ref(fc) for fc in fit_containers)

    @qudi_slot()
    def _add_config_clicked(self):
        model = self.model_combobox.currentText()
        name = self.name_lineedit.text()
        if name and model:
            self.name_lineedit.clear()
            containers = [fc_ref() for fc_ref in self.__fit_container_refs]
            containers = [fc for fc in containers if fc is not None]
            for fc in containers:
                fc.add_fit_configuration(name, model)
