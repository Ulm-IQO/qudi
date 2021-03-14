# -*- coding: utf-8 -*-
"""

"""

import os
import sys
from PySide2 import QtCore, QtGui, QtWidgets
from qudi.core.paths import get_artwork_dir


class ModuleConfigurationWidget(QtWidgets.QWidget):
    """
    """
    sigModuleConfigFinished = QtCore.Signal(str, dict, dict, dict)

    _add_icon_path = os.path.join(get_artwork_dir(), 'icons', 'oxygen', '64x64', 'add-icon.png')
    _remove_icon_path = os.path.join(os.path.dirname(_add_icon_path), 'remove-icon.png')

    def __init__(self, *args, available_modules=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.header_label = QtWidgets.QLabel()
        self.header_label.setAlignment(QtCore.Qt.AlignCenter)
        font = self.header_label.font()
        font.setPointSize(16)
        font.setBold(True)
        font2 = QtGui.QFont(font)
        font2.setPointSize(10)
        self.header_label.setFont(font)
        self.placeholder_label = QtWidgets.QLabel(
            'Please select a module to configure from the module tree.'
        )
        self.placeholder_label.setFont(font2)
        self.placeholder_label.setAlignment(QtCore.Qt.AlignCenter)
        self.placeholder_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                             QtWidgets.QSizePolicy.Expanding)
        self.footnote_label = QtWidgets.QLabel('* Mandatory Connector/ConfigOption')
        self.footnote_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.header_label)
        layout.addWidget(self.placeholder_label)
        layout.addWidget(self.splitter)
        layout.addWidget(self.footnote_label)
        layout.setStretch(1, 1)
        layout.setStretch(2, 1)
        self.setLayout(layout)

        # connector layout
        self.connector_layout = QtWidgets.QGridLayout()
        name_header = QtWidgets.QLabel('Connector')
        value_header = QtWidgets.QLabel('Connect To')
        name_header.setFont(font2)
        value_header.setFont(font2)
        hline = QtWidgets.QFrame()
        hline.setFrameShape(QtWidgets.QFrame.HLine)
        hline.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.add_connector_button = QtWidgets.QToolButton()
        self.add_connector_button.setIcon(QtGui.QIcon(self._add_icon_path))
        self.add_connector_button.clicked.connect(self.add_custom_connector)
        self.connector_layout.addWidget(name_header, 0, 1)
        self.connector_layout.addWidget(value_header, 0, 2)
        self.connector_layout.addWidget(hline, 1, 0, 1, 3)
        self.connector_layout.addWidget(self.add_connector_button, 2, 0)
        self.connector_layout.setColumnStretch(1, 1)
        self.connector_layout.setColumnStretch(2, 1)

        # options layout
        self.options_layout = QtWidgets.QGridLayout()
        name_header = QtWidgets.QLabel('Option')
        value_header = QtWidgets.QLabel('Value')
        name_header.setFont(font2)
        value_header.setFont(font2)
        hline = QtWidgets.QFrame()
        hline.setFrameShape(QtWidgets.QFrame.HLine)
        hline.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.add_option_button = QtWidgets.QToolButton()
        self.add_option_button.setIcon(QtGui.QIcon(self._add_icon_path))
        self.add_option_button.clicked.connect(self.add_custom_option)
        self.options_layout.addWidget(name_header, 0, 1)
        self.options_layout.addWidget(value_header, 0, 2)
        self.options_layout.addWidget(hline, 1, 0, 1, 3)
        self.options_layout.addWidget(self.add_option_button, 2, 0)
        self.options_layout.setColumnStretch(1, 1)
        self.options_layout.setColumnStretch(2, 1)

        # meta layout
        meta_layout = QtWidgets.QGridLayout()
        name_header = QtWidgets.QLabel('Module Meta')
        name_header.setFont(font2)
        self.allow_remote_checkbox = QtWidgets.QCheckBox()
        label = QtWidgets.QLabel('Allow Remote Access:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        hline = QtWidgets.QFrame()
        hline.setFrameShape(QtWidgets.QFrame.HLine)
        hline.setFrameShadow(QtWidgets.QFrame.Sunken)
        meta_layout.addWidget(name_header, 0, 0, 1, 2)
        meta_layout.addWidget(hline, 1, 0, 1, 2)
        meta_layout.addWidget(label, 2, 0)
        meta_layout.addWidget(self.allow_remote_checkbox, 2, 1)
        meta_layout.setColumnStretch(1, 1)

        # Stack layouts and add them to splitter
        left_layout = QtWidgets.QVBoxLayout()
        left_layout.addLayout(meta_layout)
        left_layout.addSpacing(2 * name_header.sizeHint().height())
        left_layout.addLayout(self.options_layout)
        left_layout.addStretch(1)
        left_widget = QtWidgets.QWidget()
        left_widget.setLayout(left_layout)
        left_widget.setMinimumWidth(200)
        left_scroll = QtWidgets.QScrollArea()
        left_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        left_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        left_scroll.setWidgetResizable(True)
        left_scroll.setWidget(left_widget)

        right_layout = QtWidgets.QVBoxLayout()
        right_layout.addLayout(self.connector_layout)
        right_layout.addStretch(1)
        right_widget = QtWidgets.QWidget()
        right_widget.setLayout(right_layout)
        right_widget.setMinimumWidth(200)
        right_scroll = QtWidgets.QScrollArea()
        right_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        right_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        right_scroll.setWidgetResizable(True)
        right_scroll.setWidget(right_widget)

        self.splitter.addWidget(left_scroll)
        self.splitter.addWidget(right_scroll)
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)

        # Containers to keep track of editor widgets
        self.opt_widgets = dict()
        self.conn_widgets = dict()
        self.custom_opt_widgets = list()
        self.custom_conn_widgets = list()
        self.currently_edited_module = None

        # Remember available modules
        self._available_modules = list() if available_modules is None else tuple(available_modules)

        # toggle closed editor
        self.splitter.setVisible(False)

    @property
    def not_connected_str(self):
        return 'Not Connected'

    @property
    def connections(self):
        # collect connections
        connections = {c: w.currentText() for c, (_, w) in self.conn_widgets.items() if
                       w.currentText() != self.not_connected_str}
        connections.update(
            {w[1].text().strip(): w[2].currentText() for w in self.custom_conn_widgets if
             w[2].currentText() != self.not_connected_str}
        )
        return connections

    @property
    def options(self):
        options = {
            opt: eval(w.text()) for opt, (_, w) in self.opt_widgets.items() if w.text().strip()
        }
        options.update(
            {w[1].text().strip(): eval(w[2].text()) for w in self.custom_opt_widgets if
             w[2].text().strip()}
        )
        return options

    @property
    def meta_options(self):
        return {'allow_remote': self.allow_remote_checkbox.isChecked()}

    @QtCore.Slot()
    def add_custom_connector(self, name='', target=None):
        # Create editor widgets for new connector
        name_editor = QtWidgets.QLineEdit(name)
        name_editor.setPlaceholderText('<Enter name for connector>')
        name_editor.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        target_editor = QtWidgets.QComboBox()
        target_editor.addItem(self.not_connected_str)
        target_editor.addItems(self._available_modules)
        if target in self._available_modules:
            target_editor.setCurrentText(target)
        remove_button = QtWidgets.QToolButton()
        remove_button.setIcon(QtGui.QIcon(self._remove_icon_path))
        remove_button.clicked.connect(lambda: self.remove_custom_connector(id(remove_button)))
        row = 2 + len(self.conn_widgets) + len(self.custom_conn_widgets)
        self.connector_layout.removeWidget(self.add_connector_button)
        self.connector_layout.addWidget(remove_button, row, 0)
        self.connector_layout.addWidget(name_editor, row, 1)
        self.connector_layout.addWidget(target_editor, row, 2)
        self.connector_layout.addWidget(self.add_connector_button, row+1, 0)
        self.custom_conn_widgets.append((remove_button, name_editor, target_editor))

    @QtCore.Slot()
    def remove_custom_connector(self, button_id=None):
        if not self.custom_conn_widgets:
            return

        if button_id is None:
            index = len(self.custom_conn_widgets) - 1
        else:
            current_ids = [id(button) for button, _, _ in self.custom_conn_widgets]
            try:
                index = current_ids.index(button_id)
            except ValueError:
                return

        # Remove all widgets from layout
        self.connector_layout.removeWidget(self.add_connector_button)
        for button, lineedit, combobox in reversed(self.custom_conn_widgets):
            self.connector_layout.removeWidget(button)
            self.connector_layout.removeWidget(lineedit)
            self.connector_layout.removeWidget(combobox)

        # Delete widgets for row to remove
        button, lineedit, combobox = self.custom_conn_widgets.pop(index)
        button.clicked.disconnect()
        button.setParent(None)
        lineedit.setParent(None)
        combobox.setParent(None)
        button.deleteLater()
        lineedit.deleteLater()
        combobox.deleteLater()

        # Add all remaining widgets to layout
        row_offset = 2 + len(self.conn_widgets)
        for row, (button, lineedit, combobox) in enumerate(self.custom_conn_widgets, row_offset):
            self.connector_layout.addWidget(button, row, 0)
            self.connector_layout.addWidget(lineedit, row, 1)
            self.connector_layout.addWidget(combobox, row, 2)
        self.connector_layout.addWidget(self.add_connector_button,
                                        row_offset + len(self.custom_conn_widgets),
                                        0)

    @QtCore.Slot()
    def add_custom_option(self, name='', value_str=''):
        # Create editor widgets for new config option
        name_editor = QtWidgets.QLineEdit(name)
        name_editor.setPlaceholderText('<Enter name for option>')
        name_editor.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        value_editor = QtWidgets.QLineEdit(value_str)
        remove_button = QtWidgets.QToolButton()
        remove_button.setIcon(QtGui.QIcon(self._remove_icon_path))
        remove_button.clicked.connect(lambda: self.remove_custom_option(id(remove_button)))
        row = 2 + len(self.opt_widgets) + len(self.custom_opt_widgets)
        self.options_layout.removeWidget(self.add_option_button)
        self.options_layout.addWidget(remove_button, row, 0)
        self.options_layout.addWidget(name_editor, row, 1)
        self.options_layout.addWidget(value_editor, row, 2)
        self.options_layout.addWidget(self.add_option_button, row + 1, 0)
        self.custom_opt_widgets.append((remove_button, name_editor, value_editor))

    @QtCore.Slot()
    def remove_custom_option(self, button_id=None):
        if not self.custom_opt_widgets:
            return

        if button_id is None:
            index = len(self.custom_opt_widgets) - 1
        else:
            current_ids = [id(button) for button, _, _ in self.custom_opt_widgets]
            try:
                index = current_ids.index(button_id)
            except ValueError:
                return

        # Remove all widgets from layout
        self.options_layout.removeWidget(self.add_connector_button)
        for button, name_edit, value_edit in reversed(self.custom_opt_widgets):
            self.options_layout.removeWidget(button)
            self.options_layout.removeWidget(name_edit)
            self.options_layout.removeWidget(value_edit)

        # Delete widgets for row to remove
        button, name_edit, value_edit = self.custom_opt_widgets.pop(index)
        button.clicked.disconnect()
        button.setParent(None)
        name_edit.setParent(None)
        value_edit.setParent(None)
        button.deleteLater()
        name_edit.deleteLater()
        value_edit.deleteLater()

        # Add all remaining widgets to layout
        row_offset = 2 + len(self.opt_widgets)
        for row, (button, name_edit, value_edit) in enumerate(self.custom_opt_widgets, row_offset):
            self.options_layout.addWidget(button, row, 0)
            self.options_layout.addWidget(name_edit, row, 1)
            self.options_layout.addWidget(value_edit, row, 2)
        self.options_layout.addWidget(self.add_option_button,
                                      row_offset + len(self.custom_opt_widgets),
                                      0)

    def set_available_modules(self, module_names):
        for combobox in self.conn_widgets.values():
            if combobox.currentText() not in self._available_modules:
                combobox.setCurrentIndex(0)
        self.close_module_editor()
        self._available_modules = list(module_names)

    def open_module_editor(self, name, config_dict=None, mandatory_conn_targets=None,
                           optional_conn_targets=None, mandatory_options=None,
                           optional_options=None):
        """
        """
        if name == self.currently_edited_module:
            return
        if config_dict is None:
            config_dict = dict()
        if mandatory_conn_targets is None:
            mandatory_conn_targets = dict()
        if optional_conn_targets is None:
            optional_conn_targets = dict()
        if mandatory_options is None:
            mandatory_options = tuple()
        if optional_options is None:
            optional_options = tuple()

        # Close previous editor session
        if self.currently_edited_module is not None:
            self.close_module_editor()

        # Update edited module name
        self.header_label.setText(f'Configuration for module "{name}"')
        self.currently_edited_module = name

        # Extract current config info
        connections = config_dict.get('connect', dict())
        allow_remote_access = config_dict.get('allow_remote', False)
        options = {key: value for key, value in config_dict.items() if
                   key not in ('connect', 'allow_remote', 'module.Class')}
        custom_connectors = [
            c for c in connections if c not in {*mandatory_conn_targets, *optional_conn_targets}
        ]
        custom_options = [
            opt for opt in options if opt not in {*mandatory_options, *optional_options}
        ]

        # Update module meta data editors
        self.allow_remote_checkbox.setChecked(allow_remote_access)

        # add all connectors
        self.connector_layout.removeWidget(self.add_connector_button)
        row = 2
        for conn, valid_targets in mandatory_conn_targets.items():
            label = QtWidgets.QLabel(f'* {conn}:')
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            combobox = QtWidgets.QComboBox()
            combobox.addItem(self.not_connected_str)
            combobox.addItems(valid_targets)
            target = connections.get(conn, self.not_connected_str)
            if target in valid_targets:
                combobox.setCurrentText(target)
            self.connector_layout.addWidget(label, row, 1)
            self.connector_layout.addWidget(combobox, row, 2)
            self.conn_widgets[conn] = (label, combobox)
            row += 1
        for conn, valid_targets in optional_conn_targets.items():
            label = QtWidgets.QLabel(f'{conn}:')
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            combobox = QtWidgets.QComboBox()
            combobox.addItem(self.not_connected_str)
            combobox.addItems(valid_targets)
            target = connections.get(conn, self.not_connected_str)
            if target in valid_targets:
                combobox.setCurrentText(target)
            self.connector_layout.addWidget(label, row, 1)
            self.connector_layout.addWidget(combobox, row, 2)
            self.conn_widgets[conn] = (label, combobox)
            row += 1
        self.connector_layout.addWidget(self.add_connector_button, row, 0)
        for conn in custom_connectors:
            self.add_custom_connector(conn, connections.get(conn, None))

        # add all options
        self.options_layout.removeWidget(self.add_option_button)
        row = 2
        for opt in mandatory_options:
            label = QtWidgets.QLabel(f'* {opt}:')
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            lineedit = QtWidgets.QLineEdit(repr(options.get(opt, None)))
            self.options_layout.addWidget(label, row, 1)
            self.options_layout.addWidget(lineedit, row, 2)
            self.opt_widgets[opt] = (label, lineedit)
            row += 1
        for opt in optional_options:
            label = QtWidgets.QLabel(f'{opt}:')
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            lineedit = QtWidgets.QLineEdit(repr(options.get(opt, None)))
            self.options_layout.addWidget(label, row, 1)
            self.options_layout.addWidget(lineedit, row, 2)
            self.opt_widgets[opt] = (label, lineedit)
            row += 1
        self.options_layout.addWidget(self.add_option_button, row, 0)
        for opt in custom_options:
            self.add_custom_option(opt, repr(options.get(opt, None)))

        # Show editor
        self.placeholder_label.setVisible(False)
        self.splitter.setVisible(True)

    def commit_module_config(self):
        if self.currently_edited_module is not None:
            self.sigModuleConfigFinished.emit(self.currently_edited_module,
                                              self.connections,
                                              self.options,
                                              self.meta_options)

    def close_module_editor(self):
        if self.currently_edited_module is not None:
            self.commit_module_config()
            self.placeholder_label.setVisible(True)
            self.splitter.setVisible(False)
            self._clear_editor_widgets()
            self.header_label.setText('')
            self.currently_edited_module = None

    def _clear_editor_widgets(self):
        # First remove "add custom ..." buttons
        self.connector_layout.removeWidget(self.add_connector_button)
        self.options_layout.removeWidget(self.add_option_button)

        # Remove custom connectors and options
        for button, name_edit, value_edit in reversed(self.custom_opt_widgets):
            self.options_layout.removeWidget(button)
            self.options_layout.removeWidget(name_edit)
            self.options_layout.removeWidget(value_edit)
            button.clicked.disconnect()
            button.setParent(None)
            name_edit.setParent(None)
            value_edit.setParent(None)
            button.deleteLater()
            name_edit.deleteLater()
            value_edit.deleteLater()
        self.custom_opt_widgets = list()
        for button, lineedit, combobox in reversed(self.custom_conn_widgets):
            self.connector_layout.removeWidget(button)
            self.connector_layout.removeWidget(lineedit)
            self.connector_layout.removeWidget(combobox)
            button.clicked.disconnect()
            button.setParent(None)
            lineedit.setParent(None)
            combobox.setParent(None)
            button.deleteLater()
            lineedit.deleteLater()
            combobox.deleteLater()
        self.custom_conn_widgets = list()

        # Remove "normal" connectors and options
        for label, lineedit in reversed(self.opt_widgets.values()):
            self.options_layout.removeWidget(label)
            self.options_layout.removeWidget(lineedit)
            label.setParent(None)
            lineedit.setParent(None)
            label.deleteLater()
            lineedit.deleteLater()
        self.opt_widgets = dict()
        for label, combobox in reversed(self.conn_widgets.values()):
            self.connector_layout.removeWidget(label)
            self.connector_layout.removeWidget(combobox)
            label.setParent(None)
            combobox.setParent(None)
            label.deleteLater()
            combobox.deleteLater()
        self.conn_widgets = dict()

        # Add "add custom ..." buttons again
        self.connector_layout.addWidget(self.add_connector_button, 2, 0)
        self.options_layout.addWidget(self.add_option_button, 2, 0)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    mw = ModuleConfigurationWidget()
    mw.resize(1600, 900)

    test_cfg = {'module.Class': 'test_gui.TestGUI',
                'allow_remote': True,
                'mandatory_option': [1, 2, 3, 'derp'],
                'optional_option': ' abcäöü "hallo"  ',
                'custom_option': None,
                'connect': {'mandatory_connector': 'my_cool_module_name1',
                            'optional_connector': 'my_cool_module_name2',
                            'custom_connector': 'my_cool_module_name3'}
                }
    mandatory_connectors = {'mandatory_connector': ('my_cool_module_name1', 'my_cool_module_name3')}
    optional_connectors = {'optional_connector': ('my_cool_module_name2', 'my_cool_module_name3')}
    mandatory_options = ('mandatory_option',)
    optional_options = ('optional_option',)
    available_modules = ('my_cool_module_name1',
                         'my_cool_module_name2',
                         'my_cool_module_name3',
                         'shameful_module')

    mw.set_available_modules(available_modules)
    mw.open_module_editor('my_test_module',
                          test_cfg,
                          mandatory_connectors,
                          optional_connectors,
                          mandatory_options,
                          optional_options)

    mw.show()
    sys.exit(app.exec_())
