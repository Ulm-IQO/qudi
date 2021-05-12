# -*- coding: utf-8 -*-
"""

"""

__all__ = ('ModuleSelector',)

from PySide2 import QtWidgets, QtCore
from qudi.tools.config_editor.tree_widgets import AvailableModulesTreeWidget, SelectedModulesTreeWidget


class ModuleSelector(QtWidgets.QDialog):
    """
    """

    def __init__(self, *args, available_modules, selected_modules=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle('Qudi Config Editor: Module Selection')
        screen_size = QtWidgets.QApplication.instance().primaryScreen().availableSize()
        self.resize(screen_size.width() // 2, screen_size.height() // 2)

        # Create two customized QTreeWidgets. One for all available modules to select from and one
        # for the selected modules.
        self.available_treewidget = AvailableModulesTreeWidget(modules=available_modules)
        self.selected_treewidget = SelectedModulesTreeWidget(modules=selected_modules)

        # Create left side of splitter widget
        left_widget = QtWidgets.QWidget()
        left_widget.setContentsMargins(0, 0, 0, 0)
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        label = QtWidgets.QLabel('Available Modules')
        font = label.font()
        font.setPointSize(16)
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label)
        layout.addWidget(self.available_treewidget)
        left_widget.setLayout(layout)

        # Create right side of splitter widget
        right_widget = QtWidgets.QWidget()
        right_widget.setContentsMargins(0, 0, 0, 0)
        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        right_widget.setLayout(layout)
        label = QtWidgets.QLabel('Selected Modules')
        label.setFont(font)
        self.add_remote_button = QtWidgets.QPushButton('Add Remote Module')
        self.add_custom_button = QtWidgets.QPushButton('Add Custom Module')
        self.custom_module_lineedit = QtWidgets.QLineEdit()
        self.custom_module_lineedit.setPlaceholderText('Custom module name (module.Class)')
        self.base_selection_combobox = QtWidgets.QComboBox()
        self.base_selection_combobox.addItems(('GUI', 'Logic', 'Hardware'))
        self.add_remote_button.clicked.connect(self.add_remote_module)
        self.add_custom_button.clicked.connect(self.add_custom_module)
        layout.addWidget(label, 0, 0, 1, 3)
        layout.addWidget(self.selected_treewidget, 1, 0, 1, 3)
        label = QtWidgets.QLabel('Module Base:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label, 2, 0)
        layout.addWidget(self.base_selection_combobox, 2, 1)
        layout.addWidget(self.add_remote_button, 2, 2)
        layout.addWidget(self.custom_module_lineedit, 3, 0, 1, 2)
        layout.addWidget(self.add_custom_button, 3, 2)
        layout.setColumnStretch(0, 1)
        layout.setRowStretch(1, 1)

        # set splitter as main widget
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        # Create buttonbox for this dialog
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # Add everything to the main layout
        hline = QtWidgets.QFrame()
        hline.setFrameShape(QtWidgets.QFrame.HLine)
        hline.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(splitter)
        layout.addWidget(hline)
        layout.addWidget(self.button_box)
        layout.setStretch(0, 1)
        self.setLayout(layout)

    @QtCore.Slot()
    def add_remote_module(self):
        base = self.base_selection_combobox.currentText().lower()
        if base == 'gui':
            raise ValueError('Unable to add remote module.\nGUI modules can not be remote modules.')
        self.selected_treewidget.add_module(f'{base}.<REMOTE MODULE>')

    @QtCore.Slot()
    def add_custom_module(self):
        base = self.base_selection_combobox.currentText().lower()
        module = self.custom_module_lineedit.text().strip()
        if module:
            self.selected_treewidget.add_module(f'{base}.{module}')

    def get_selected_modules(self):
        return self.selected_treewidget.get_modules()
