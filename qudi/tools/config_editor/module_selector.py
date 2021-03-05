# -*- coding: utf-8 -*-
"""

"""

import os
from PySide2 import QtWidgets
from qudi.tools.config_editor.tree_widgets import AvailableModulesTreeWidget
from qudi.tools.config_editor.tree_widgets import SelectedModulesTreeWidget


class ModuleSelector(QtWidgets.QDialog):
    """
    """
    def __init__(self, *args, available_modules, selected_modules=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle('Qudi Config Editor: Module Selection')
        screen_size = QtWidgets.QApplication.instance().primaryScreen().availableSize()
        width = screen_size.width() // 2
        height = screen_size.height() // 2
        self.resize(width, height)

        # Create two slightly customized QTreeWidgets. One for all available modules and one for
        # the selected modules.
        self.available_treewidget = AvailableModulesTreeWidget(available_modules=available_modules)
        self.selected_treewidget = SelectedModulesTreeWidget(selected_modules=selected_modules)

        # Create left side of splitter widget
        left_widget = QtWidgets.QWidget()
        left_widget.setContentsMargins(0, 0, 0, 0)
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        label = QtWidgets.QLabel('Available Modules')
        font = label.font()
        font.setPointSize(14)
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label)
        layout.addWidget(self.available_treewidget)
        left_widget.setLayout(layout)
        # Create right side of splitter widget
        self.add_remote_button = QtWidgets.QPushButton('Add Remote Module')
        self.add_remote_button.clicked.connect(self.selected_treewidget.add_remote_module)
        right_widget = QtWidgets.QWidget()
        right_widget.setContentsMargins(0, 0, 0, 0)
        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        label = QtWidgets.QLabel('Selected Modules')
        font = label.font()
        font.setPointSize(14)
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label, 0, 0)
        layout.addWidget(self.add_remote_button, 0, 1)
        layout.addWidget(self.selected_treewidget, 1, 0, 1, 2)
        layout.setColumnStretch(0, 1)
        right_widget.setLayout(layout)
        # set splitter as main widget
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        # Create buttonbox for this dialog
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok)
        if self.selected_treewidget.has_invalid_module_names:
            self.button_box.button(self.button_box.Ok).setEnabled(False)
        self.button_box.accepted.connect(self.return_selected_modules)
        self.button_box.rejected.connect(self.return_empty)
        self.selected_treewidget.sigSetValidState.connect(
            self.button_box.button(self.button_box.Ok).setEnabled)

        # Add everything to the main layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(splitter)
        layout.addWidget(self.button_box)
        layout.setStretch(0, 1)
        self.setLayout(layout)
        self.selected_modules = dict()

    def return_selected_modules(self):
        if self.selected_treewidget.has_invalid_module_names:
            self.return_empty()
        else:
            self.selected_modules = self.selected_treewidget.get_selected_modules()
            self.accept()

    def return_empty(self):
        self.selected_modules = dict()
        self.reject()


if __name__ == '__main__':
    import sys
    sys.path.append(os.path.dirname(__file__))
    from config_editor import QudiEnvironment

    class MainWindow(QtWidgets.QMainWindow):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        def show(self):
            super().show()

            qudi_env = QudiEnvironment()
            mod_sel = ModuleSelector(parent=self,
                                     available_modules=tuple(qudi_env.module_finder.module_classes))
            print(mod_sel.exec_())
            print(mod_sel.selected_modules)


    app = QtWidgets.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec_())
