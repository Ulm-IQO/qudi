# -*- coding: utf-8 -*-
"""
This file contains a custom module widget for the Qudi manager GUI.

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
from qtpy import QtCore, QtGui, QtWidgets
from qudi.core.util.paths import get_main_dir
from qudi.core.util.mutex import Mutex


class ModuleFrameWidget(QtWidgets.QFrame):
    """
    Custom module QFrame widget for the Qudi manager GUI
    """
    sigActivateClicked = QtCore.Signal(str)
    sigDeactivateClicked = QtCore.Signal(str)
    sigReloadClicked = QtCore.Signal(str)
    sigCleanupClicked = QtCore.Signal(str)

    def __init__(self, *args, module_name=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Create QToolButtons
        self.cleanup_button = QtWidgets.QToolButton()
        self.cleanup_button.setObjectName('cleanupButton')
        self.deactivate_button = QtWidgets.QToolButton()
        self.deactivate_button.setObjectName('deactivateButton')
        self.reload_button = QtWidgets.QToolButton()
        self.reload_button.setObjectName('reloadButton')

        # Set icons for QToolButtons
        icon_path = os.path.join(get_main_dir(), 'core', 'artwork', 'icons', 'oxygen', '22x22')
        self.cleanup_button.setIcon(QtGui.QIcon(os.path.join(icon_path, 'edit-clear.png')))
        self.deactivate_button.setIcon(QtGui.QIcon(os.path.join(icon_path, 'edit-delete.png')))
        self.reload_button.setIcon(QtGui.QIcon(os.path.join(icon_path, 'view-refresh.png')))

        # Create activation pushbutton
        self.activate_button = QtWidgets.QPushButton('load/activate <module_name>')
        self.activate_button.setObjectName('loadButton')
        # self.activate_button.setCheckable(True)
        self.activate_button.setMinimumWidth(200)
        self.activate_button.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                           QtWidgets.QSizePolicy.Fixed)

        # Create status label
        self.status_label = QtWidgets.QLabel('Module status goes here...')
        self.status_label.setObjectName('statusLabel')

        # Set tooltips
        self.cleanup_button.setToolTip('Clean up module status file')
        self.deactivate_button.setToolTip('Deactivate module')
        self.reload_button.setToolTip('Reload module')
        self.activate_button.setToolTip('Load this module and all its dependencies')
        self.status_label.setToolTip('Displays module status information')

        # Combine all widgets in a layout and set as main layout
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.activate_button, 0, 0)
        layout.addWidget(self.reload_button, 0, 1)
        layout.addWidget(self.deactivate_button, 0, 2)
        layout.addWidget(self.cleanup_button, 0, 3)
        layout.addWidget(self.status_label, 1, 0, 1, 4)
        self.setLayout(layout)

        self._module_name = ''
        if module_name:
            self.set_module_name(module_name)

        self.activate_button.clicked.connect(self.activate_clicked)
        self.deactivate_button.clicked.connect(self.deactivate_clicked)
        self.reload_button.clicked.connect(self.reload_clicked)
        self.cleanup_button.clicked.connect(self.cleanup_clicked)
        return

    def set_module_name(self, name):
        if name:
            self.activate_button.setText('Load {0}'.format(name))
            self._module_name = name

    def set_module_state(self, state):
        if state == 'not loaded':
            self.activate_button.setText('Load {0}'.format(self._module_name))
            self.cleanup_button.setEnabled(True)
            self.deactivate_button.setEnabled(False)
            self.reload_button.setEnabled(False)
        elif state == 'deactivated':
            self.activate_button.setText('Activate {0}'.format(self._module_name))
            self.cleanup_button.setEnabled(True)
            self.deactivate_button.setEnabled(False)
            self.reload_button.setEnabled(False)
        else:
            self.activate_button.setText(self._module_name)
            self.cleanup_button.setEnabled(False)
            self.deactivate_button.setEnabled(True)
            self.reload_button.setEnabled(True)
        self.status_label.setText('Module is {0}'.format(state))
        return

    @QtCore.Slot()
    def activate_clicked(self):
        self.sigActivateClicked.emit(self._module_name)

    @QtCore.Slot()
    def deactivate_clicked(self):
        self.sigDeactivateClicked.emit(self._module_name)

    @QtCore.Slot()
    def cleanup_clicked(self):
        self.sigCleanupClicked.emit(self._module_name)

    @QtCore.Slot()
    def reload_clicked(self):
        self.sigReloadClicked.emit(self._module_name)


class ModuleListModel(QtCore.QAbstractListModel):
    """
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = Mutex()
        self._module_states = dict()
        self._module_names = list()

    def rowCount(self, parent):
        return len(self._module_names)

    def data(self, index, role):
        if not index.isValid():
            return
        row = index.row()
        if row >= len(self._module_names):
            return
        name = self._module_names[row]
        state = self._module_states[name]
        if role == QtCore.Qt.DisplayRole:
            return name, state

    def flags(self, index):
        return QtCore.Qt.ItemNeverHasChildren | QtCore.Qt.ItemIsEnabled# | QtCore.Qt.ItemIsEditable

    def append_module(self, name, state):
        with self._lock:
            if name in self._module_states:
                raise Exception(
                    'Module with name "{0}" already present in ModuleListModel.'.format(name))
            self.beginInsertRows(len(self._module_names))
            self._module_names.append(name)
            self._module_states[name] = state
            self.endInsertRows()

    def remove_module(self, name):
        with self._lock:
            if name not in self._module_states:
                return
            row = self._module_names.index(name)
            self.beginRemoveRows(row, row + 1)
            del self._module_names[row]
            del self._module_states[name]
            self.endRemoveRows()

    def reset_modules(self, state_dict):
        with self._lock:
            self.beginResetModel()
            self._module_states = state_dict.copy()
            self._module_names = list(state_dict)
            self.endResetModel()

    def change_module_state(self, name, state):
        with self._lock:
            if name not in self._module_states:
                raise Exception('Can not change module state in ModuleListModel. No module by the '
                                'name "{0}" found.'.format(name))
            self._module_states[name] = state
            row = self._module_names.index(name)
            self.dataChanged.emit(self.createIndex(row, 0),
                                  self.createIndex(row + 1, 0),
                                  (QtCore.Qt.DisplayRole,))


class ModuleListItemDelegate(QtWidgets.QStyledItemDelegate):
    """
    """
    sigActivateClicked = QtCore.Signal(str)
    sigDeactivateClicked = QtCore.Signal(str)
    sigReloadClicked = QtCore.Signal(str)
    sigCleanupClicked = QtCore.Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.render_widget = ModuleFrameWidget()
        self.__origin = QtCore.QPoint()

    def createEditor(self, parent, option, index):
        widget = ModuleFrameWidget(parent=parent)
        widget.sigActivateClicked.connect(self.sigActivateClicked)
        widget.sigDeactivateClicked.connect(self.sigDeactivateClicked)
        widget.sigReloadClicked.connect(self.sigReloadClicked)
        widget.sigCleanupClicked.connect(self.sigCleanupClicked)
        return widget

    def setEditorData(self, editor, index):
        data = index.data()
        if data:
            editor.set_module_name(data[0])
            editor.set_module_state(data[1])

    def setModelData(self, editor, model, index):
        pass

    def sizeHint(self, option=None, index=None):
        return self.render_widget.sizeHint()

    def paint(self, painter, option, index):
        """
        """
        name, state = index.data()
        self.render_widget.set_module_name(name)
        self.render_widget.set_module_state(state)
        self.render_widget.setGeometry(option.rect)
        painter.save()
        painter.translate(option.rect.topLeft())
        self.render_widget.render(painter, self.__origin)
        painter.restore()


class ModuleListView(QtWidgets.QListView):
    """
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)
        delegate = ModuleListItemDelegate()
        self.setItemDelegate(delegate)
        self.setMinimumWidth(delegate.sizeHint().width())
        self.setUniformItemSizes(True)
        self.setSpacing(1)
        self.previous_index = QtCore.QModelIndex()

    def mouseMoveEvent(self, event):
        index = self.indexAt(event.pos())
        if index != self.previous_index:
            if self.previous_index.isValid():
                self.closePersistentEditor(self.previous_index)
            if index.isValid():
                self.openPersistentEditor(index)
            self.previous_index = index

    def leaveEvent(self, event):
        if self.previous_index.isValid():
            self.closePersistentEditor(self.previous_index)
        self.previous_index = QtCore.QModelIndex()


class ModuleWidget(QtWidgets.QTabWidget):
    """
    """
    sigActivateModule = QtCore.Signal(str)
    sigDeactivateModule = QtCore.Signal(str)
    sigCleanupModule = QtCore.Signal(str)
    sigReloadModule = QtCore.Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.list_models = {'gui'     : ModuleListModel(),
                            'logic'   : ModuleListModel(),
                            'hardware': ModuleListModel()}
        self.list_views = {'gui'     : ModuleListView(),
                           'logic'   : ModuleListView(),
                           'hardware': ModuleListView()}
        self.addTab(self.list_views['gui'], 'GUI')
        self.addTab(self.list_views['logic'], 'Logic')
        self.addTab(self.list_views['hardware'], 'Hardware')
        for base, view in self.list_views.items():
            view.setModel(self.list_models[base])
            delegate = view.itemDelegate()
            delegate.sigActivateClicked.connect(self.sigActivateModule)
            delegate.sigDeactivateClicked.connect(self.sigDeactivateModule)
            delegate.sigReloadClicked.connect(self.sigReloadModule)
            delegate.sigCleanupClicked.connect(self.sigCleanupModule)

    @QtCore.Slot(dict)
    def update_modules(self, modules_dict):
        for base, model in self.list_models.items():
            model.reset_modules(
                {name: mod.state for name, mod in modules_dict.items() if mod.module_base == base})
        return

    @QtCore.Slot(str, str, str)
    def update_module_state(self, base, name, state):
        self.list_models[base].change_module_state(name, state)
