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


class ModuleFrameWidget(QtWidgets.QFrame):
    """
    Custom module QFrame widget for the Qudi manager GUI
    """
    sigLoadClicked = QtCore.Signal(str)
    sigDeactivateClicked = QtCore.Signal(str)
    sigReloadClicked = QtCore.Signal(str)
    sigCleanupClicked = QtCore.Signal(str)

    def __init__(self, parent=None, module_name=None, **kwargs):
        super().__init__(parent, **kwargs)

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
        self.load_button = QtWidgets.QPushButton('load/activate <module_name>')
        self.load_button.setObjectName('loadButton')
        # self.load_button.setCheckable(True)
        self.load_button.setMinimumWidth(200)
        self.load_button.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                       QtWidgets.QSizePolicy.Fixed)

        # Create status label
        self.status_label = QtWidgets.QLabel('Module status goes here...')
        self.status_label.setObjectName('statusLabel')

        # Set tooltips
        self.cleanup_button.setToolTip('Clean up module status file')
        self.deactivate_button.setToolTip('Deactivate module')
        self.reload_button.setToolTip('Reload module')
        self.load_button.setToolTip('Load this module and all its dependencies')
        self.status_label.setToolTip('Displays module status information')

        # Combine all widgets in a layout and set as main layout
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.load_button, 0, 0)
        layout.addWidget(self.reload_button, 0, 1)
        layout.addWidget(self.deactivate_button, 0, 2)
        layout.addWidget(self.cleanup_button, 0, 3)
        layout.addWidget(self.status_label, 1, 0, 1, 4)
        self.setLayout(layout)

        self._module_name = ''
        if module_name:
            self.set_module_name(module_name)

        self.load_button.clicked.connect(self.load_clicked)
        self.reload_button.clicked.connect(self.reload_clicked)
        self.deactivate_button.clicked.connect(self.deactivate_clicked)
        self.cleanup_button.clicked.connect(self.cleanup_clicked)
        return

    def set_module_name(self, name):
        if name:
            self.load_button.setText('Load {0}'.format(name))
            self._module_name = name

    def set_module_state(self, state):
        if state == 'not loaded':
            self.load_button.setText('Load {0}'.format(self._module_name))
            self.cleanup_button.setEnabled(True)
            self.deactivate_button.setEnabled(False)
            self.reload_button.setEnabled(False)
        elif state == 'deactivated':
            self.load_button.setText('Activate {0}'.format(self._module_name))
            self.cleanup_button.setEnabled(True)
            self.deactivate_button.setEnabled(False)
            self.reload_button.setEnabled(False)
        else:
            self.load_button.setText(self._module_name)
            self.cleanup_button.setEnabled(False)
            self.deactivate_button.setEnabled(True)
            self.reload_button.setEnabled(True)
        self.status_label.setText('Module is {0}'.format(state))
        return

    @QtCore.Slot()
    def load_clicked(self):
        self.sigLoadClicked.emit(self._module_name)

    @QtCore.Slot()
    def deactivate_clicked(self):
        self.sigDeactivateClicked.emit(self._module_name)

    @QtCore.Slot()
    def cleanup_clicked(self):
        self.sigCleanupClicked.emit(self._module_name)

    @QtCore.Slot()
    def reload_clicked(self):
        self.sigReloadClicked.emit(self._module_name)


class ModuleScrollWidget(QtWidgets.QScrollArea):
    """

    """
    sigActivateModule = QtCore.Signal(str)
    sigDeactivateModule = QtCore.Signal(str)
    sigCleanupModule = QtCore.Signal(str)
    sigReloadModule = QtCore.Signal(str)

    def __init__(self, parent=None, module_names=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.setLayout(QtWidgets.QVBoxLayout())

        self._frames = dict()
        if module_names:
            self.create_module_frames(module_names)
        return

    def __contains__(self, item):
        return self._frames.__contains__(item)

    def __len__(self):
        return self._frames.__len__()

    def clear(self):
        # Remove old connections and module frame widgets
        for frame in self._frames.values():
            frame.sigLoadClicked.disconnect()
            frame.sigReloadClicked.disconnect()
            frame.sigDeactivateClicked.disconnect()
            frame.sigCleanupClicked.disconnect()
            frame.setParent(None)
        self._frames = dict()

    @property
    def module_names(self):
        return tuple(self._frames)

    @property
    def module_frames(self):
        return self._frames.copy()

    @QtCore.Slot(dict)
    def create_module_frames(self, modules):
        # Create new frame widgets and connect them
        frames = dict()
        for name, mod in modules.items():
            if name in frames:
                raise NameError('Module with name "{0}" occurs twice in module list.')
            frames[name] = ModuleFrameWidget(parent=self, module_name=name)
            frames[name].sigLoadClicked.connect(self.sigActivateModule)
            frames[name].sigReloadClicked.connect(self.sigReloadModule)
            frames[name].sigDeactivateClicked.connect(self.sigDeactivateModule)
            frames[name].sigCleanupClicked.connect(self.sigCleanupModule)
            frames[name].set_module_state(mod.state)

        # delete old frame widgets and disconnect them
        self.clear()

        self.setLayout(QtWidgets.QVBoxLayout())
        self._frames = frames
        for frame in frames.values():
            self.layout().addWidget(frame)
        return

    @QtCore.Slot(dict)
    def set_module_states(self, module_states):
        for mod_name, frame in self._frames.items():
            state = module_states.get(mod_name, 'BROKEN')
            frame.set_module_state(state)
        return

    @QtCore.Slot(str, str)
    def set_module_state(self, name, state):
        if name in self._frames:
            self._frames[name].set_module_state(state)


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
        self.module_scroll_widgets = {'gui': ModuleScrollWidget(),
                                      'logic': ModuleScrollWidget(),
                                      'hardware': ModuleScrollWidget()}
        self.addTab(self.module_scroll_widgets['gui'], 'GUI')
        self.addTab(self.module_scroll_widgets['logic'], 'Logic')
        self.addTab(self.module_scroll_widgets['hardware'], 'Hardware')
        self.module_scroll_widgets['gui'].sigActivateModule.connect(self.sigActivateModule)
        self.module_scroll_widgets['logic'].sigActivateModule.connect(self.sigActivateModule)
        self.module_scroll_widgets['hardware'].sigActivateModule.connect(self.sigActivateModule)
        self.module_scroll_widgets['gui'].sigDeactivateModule.connect(self.sigDeactivateModule)
        self.module_scroll_widgets['logic'].sigDeactivateModule.connect(self.sigDeactivateModule)
        self.module_scroll_widgets['hardware'].sigDeactivateModule.connect(self.sigDeactivateModule)
        self.module_scroll_widgets['gui'].sigCleanupModule.connect(self.sigCleanupModule)
        self.module_scroll_widgets['logic'].sigCleanupModule.connect(self.sigCleanupModule)
        self.module_scroll_widgets['hardware'].sigCleanupModule.connect(self.sigCleanupModule)
        self.module_scroll_widgets['gui'].sigReloadModule.connect(self.sigReloadModule)
        self.module_scroll_widgets['logic'].sigReloadModule.connect(self.sigReloadModule)
        self.module_scroll_widgets['hardware'].sigReloadModule.connect(self.sigReloadModule)

    @QtCore.Slot(dict)
    def update_modules(self, modules_dict):
        self.module_scroll_widgets['gui'].create_module_frames(
            {name: mod for name, mod in modules_dict.items() if mod.module_base == 'gui'})
        self.module_scroll_widgets['logic'].create_module_frames(
            {name: mod for name, mod in modules_dict.items() if mod.module_base == 'logic'})
        self.module_scroll_widgets['hardware'].create_module_frames(
            {name: mod for name, mod in modules_dict.items() if mod.module_base == 'hardware'})
        return

    @QtCore.Slot(str, str, str)
    def update_module_state(self, base, name, state):
        self.module_scroll_widgets[base].set_module_state(name, state)
