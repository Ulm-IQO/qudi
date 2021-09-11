# -*- coding: utf-8 -*-
"""

"""

__all__ = ('ModuleConfigurationWidget',)

import os
from PySide2 import QtCore, QtGui, QtWidgets
from qudi.util.paths import get_artwork_dir


class ModuleConfigurationWidget(QtWidgets.QWidget):
    """
    """
    sigModuleConfigFinished = QtCore.Signal(str, dict, dict, dict)

    _add_icon_path = os.path.join(get_artwork_dir(), 'icons', 'oxygen', '64x64', 'add-icon.png')
    _remove_icon_path = os.path.join(os.path.dirname(_add_icon_path), 'remove-icon.png')

    _non_config_options = frozenset(
        {'connect', 'allow_remote', 'module.Class', 'remote_url', 'certfile', 'keyfile'}
    )

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
        self.specify_name_label = QtWidgets.QLabel(
            'Please enter a unique module name before editing module config.'
        )
        self.specify_name_label.setFont(font2)
        self.specify_name_label.setAlignment(QtCore.Qt.AlignCenter)
        self.specify_name_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                              QtWidgets.QSizePolicy.Expanding)
        self.footnote_label = QtWidgets.QLabel('* Mandatory Connector/ConfigOption')
        self.footnote_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.header_label)
        layout.addWidget(self.placeholder_label)
        layout.addWidget(self.specify_name_label)
        layout.addWidget(self.splitter)
        layout.addWidget(self.footnote_label)
        layout.setStretch(1, 1)
        layout.setStretch(2, 1)
        layout.setStretch(3, 1)
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
        self.connector_layout.addWidget(name_header, 0, 1)
        self.connector_layout.addWidget(value_header, 0, 2)
        self.connector_layout.addWidget(hline, 1, 0, 1, 3)
        self.connector_layout.setColumnStretch(2, 1)
        add_connector_layout = QtWidgets.QHBoxLayout()
        add_connector_layout.setStretch(1, 1)
        self.add_connector_button = QtWidgets.QToolButton()
        self.add_connector_button.setIcon(QtGui.QIcon(self._add_icon_path))
        self.add_connector_button.clicked.connect(self.add_custom_connector)
        self.add_connector_lineedit = QtWidgets.QLineEdit()
        self.add_connector_lineedit.setPlaceholderText('Enter custom connector name')
        add_connector_layout.addWidget(self.add_connector_button)
        add_connector_layout.addWidget(self.add_connector_lineedit)

        # options layout
        self.options_layout = QtWidgets.QGridLayout()
        name_header = QtWidgets.QLabel('Option')
        value_header = QtWidgets.QLabel('Value')
        name_header.setFont(font2)
        value_header.setFont(font2)
        hline = QtWidgets.QFrame()
        hline.setFrameShape(QtWidgets.QFrame.HLine)
        hline.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.options_layout.addWidget(name_header, 0, 1)
        self.options_layout.addWidget(value_header, 0, 2)
        self.options_layout.addWidget(hline, 1, 0, 1, 3)
        self.options_layout.setColumnStretch(2, 1)
        add_option_layout = QtWidgets.QHBoxLayout()
        add_option_layout.setStretch(1, 1)
        self.add_option_button = QtWidgets.QToolButton()
        self.add_option_button.setIcon(QtGui.QIcon(self._add_icon_path))
        self.add_option_button.clicked.connect(self.add_custom_option)
        self.add_option_lineedit = QtWidgets.QLineEdit()
        self.add_option_lineedit.setPlaceholderText('Enter custom option name')
        add_option_layout.addWidget(self.add_option_button)
        add_option_layout.addWidget(self.add_option_lineedit)

        # meta layout
        meta_layout = QtWidgets.QVBoxLayout()
        name_header = QtWidgets.QLabel('Module Meta')
        name_header.setFont(font2)
        hline = QtWidgets.QFrame()
        hline.setFrameShape(QtWidgets.QFrame.HLine)
        hline.setFrameShadow(QtWidgets.QFrame.Sunken)
        meta_layout.addWidget(name_header)
        meta_layout.addWidget(hline)

        self.module_meta_widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        layout.setStretch(1, 1)
        layout.setContentsMargins(0, 0, 0, 0)
        self.module_meta_widget.setLayout(layout)
        self.allow_remote_checkbox = QtWidgets.QCheckBox()
        self.allow_remote_checkbox.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                                 QtWidgets.QSizePolicy.Preferred)
        label = QtWidgets.QLabel('Allow Remote Access:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label)
        layout.addWidget(self.allow_remote_checkbox)
        meta_layout.addWidget(self.module_meta_widget)

        self.remote_meta_widget = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.remote_meta_widget.setLayout(layout)
        self.remote_url_lineedit = QtWidgets.QLineEdit()
        label = QtWidgets.QLabel('* Remote URL:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label, 0, 0)
        layout.addWidget(self.remote_url_lineedit, 0, 1)
        self.remote_certfile_lineedit = QtWidgets.QLineEdit()
        label = QtWidgets.QLabel('Remote certfile:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label, 1, 0)
        layout.addWidget(self.remote_certfile_lineedit, 1, 1)
        self.remote_keyfile_lineedit = QtWidgets.QLineEdit()
        label = QtWidgets.QLabel('Remote keyfile:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label, 2, 0)
        layout.addWidget(self.remote_keyfile_lineedit, 2, 1)
        meta_layout.addWidget(self.remote_meta_widget)

        # Stack layouts and add them to splitter
        left_layout = QtWidgets.QVBoxLayout()
        left_layout.addLayout(meta_layout)
        left_layout.addSpacing(2 * name_header.sizeHint().height())
        left_layout.addLayout(self.options_layout)
        hline = QtWidgets.QFrame()
        hline.setFrameShape(QtWidgets.QFrame.HLine)
        hline.setFrameShadow(QtWidgets.QFrame.Sunken)
        left_layout.addWidget(hline)
        left_layout.addLayout(add_option_layout)
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
        hline = QtWidgets.QFrame()
        hline.setFrameShape(QtWidgets.QFrame.HLine)
        hline.setFrameShadow(QtWidgets.QFrame.Sunken)
        right_layout.addWidget(hline)
        right_layout.addLayout(add_connector_layout)
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
        self.custom_opt_widgets = dict()
        self.custom_conn_widgets = dict()
        self.currently_edited_module = None

        # Remember available modules
        self._available_modules = list() if available_modules is None else tuple(available_modules)

        # toggle closed editor
        self.splitter.setVisible(False)
        self.specify_name_label.setVisible(False)

    @property
    def not_connected_str(self):
        return 'Not Connected'

    @property
    def connections(self):
        # collect connections
        connections = {c: w.currentText() for c, (_, w) in self.conn_widgets.items() if
                       w.currentText() != self.not_connected_str}
        connections.update(
            {c: w.currentText() for c, (_, _, w) in self.custom_conn_widgets.items() if
             w.currentText() != self.not_connected_str}
        )
        return connections

    @property
    def options(self):
        options = {
            opt: eval(w.text()) for opt, (_, w) in self.opt_widgets.items() if w.text().strip()
        }
        options.update(
            {opt: eval(w.text()) for opt, (_, _, w) in self.custom_opt_widgets.items() if
             w.text().strip()}
        )
        return options

    @property
    def meta_options(self):
        return {'allow_remote': self.allow_remote_checkbox.isChecked()}

    @QtCore.Slot()
    def add_custom_connector(self, target=None):
        name = self.add_connector_lineedit.text().strip()
        if name and (name not in self.conn_widgets) and (name not in self.custom_conn_widgets):
            self.add_connector_lineedit.clear()
            # Create editor widgets for new connector
            label = QtWidgets.QLabel(f'{name}:')
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            editor = QtWidgets.QComboBox()
            editor.addItem(self.not_connected_str)
            editor.addItems(self._available_modules)
            if target in self._available_modules:
                editor.setCurrentText(target)
            remove_button = QtWidgets.QToolButton()
            remove_button.setIcon(QtGui.QIcon(self._remove_icon_path))
            remove_button.clicked.connect(lambda: self.remove_custom_connector(name))
            row = 2 + len(self.conn_widgets) + len(self.custom_conn_widgets)
            self.connector_layout.addWidget(remove_button, row, 0)
            self.connector_layout.addWidget(label, row, 1)
            self.connector_layout.addWidget(editor, row, 2)
            self.custom_conn_widgets[name] = (remove_button, label, editor)

    @QtCore.Slot()
    def remove_custom_connector(self, name):
        if name not in self.custom_conn_widgets:
            return

        # Remove all widgets from layout
        for button, label, editor in reversed(list(self.custom_conn_widgets.values())):
            self.connector_layout.removeWidget(button)
            self.connector_layout.removeWidget(label)
            self.connector_layout.removeWidget(editor)

        # Delete widgets for row to remove
        button, label, editor = self.custom_conn_widgets.pop(name)
        button.clicked.disconnect()
        button.setParent(None)
        label.setParent(None)
        editor.setParent(None)
        button.deleteLater()
        label.deleteLater()
        editor.deleteLater()

        # Add all remaining widgets to layout
        row_offset = 2 + len(self.conn_widgets)
        for row, (button, label, editor) in enumerate(self.custom_conn_widgets.values(), row_offset):
            self.connector_layout.addWidget(button, row, 0)
            self.connector_layout.addWidget(label, row, 1)
            self.connector_layout.addWidget(editor, row, 2)

    @QtCore.Slot()
    def add_custom_option(self, value_str=''):
        # Create editor widgets for new config option
        name = self.add_option_lineedit.text().strip()
        if name and (name not in self.opt_widgets) and (name not in self.custom_opt_widgets):
            self.add_option_lineedit.clear()
            label = QtWidgets.QLabel(f'{name}:')
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            value_editor = QtWidgets.QLineEdit(value_str if isinstance(value_str, str) else '')
            remove_button = QtWidgets.QToolButton()
            remove_button.setIcon(QtGui.QIcon(self._remove_icon_path))
            remove_button.clicked.connect(lambda: self.remove_custom_option(name))
            row = 2 + len(self.opt_widgets) + len(self.custom_opt_widgets)
            self.options_layout.addWidget(remove_button, row, 0)
            self.options_layout.addWidget(label, row, 1)
            self.options_layout.addWidget(value_editor, row, 2)
            self.custom_opt_widgets[name] = (remove_button, label, value_editor)

    @QtCore.Slot(str)
    def remove_custom_option(self, name):
        if name not in self.custom_opt_widgets:
            return

        # Remove all widgets from layout
        for button, label, editor in reversed(list(self.custom_opt_widgets.values())):
            self.options_layout.removeWidget(button)
            self.options_layout.removeWidget(label)
            self.options_layout.removeWidget(editor)

        # Delete widgets for row to remove
        button, label, editor = self.custom_opt_widgets.pop(name)
        button.clicked.disconnect()
        button.setParent(None)
        label.setParent(None)
        editor.setParent(None)
        button.deleteLater()
        label.deleteLater()
        editor.deleteLater()

        # Add all remaining widgets to layout
        row_offset = 2 + len(self.opt_widgets)
        for row, (button, label, editor) in enumerate(self.custom_opt_widgets.values(), row_offset):
            self.options_layout.addWidget(button, row, 0)
            self.options_layout.addWidget(label, row, 1)
            self.options_layout.addWidget(editor, row, 2)

    def set_available_modules(self, module_names):
        for combobox in self.conn_widgets.values():
            if combobox.currentText() not in self._available_modules:
                combobox.setCurrentIndex(0)
        self.close_module_editor()
        self._available_modules = list(module_names)

    def open_module_editor(self, name, config_dict=None, mandatory_conn_targets=None,
                           optional_conn_targets=None, mandatory_options=None,
                           optional_options=None, is_remote_module=False):
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
        remote_url = config_dict.get('remote_url', '')
        remote_certfile = config_dict.get('certfile', '')
        remote_keyfile = config_dict.get('keyfile', '')

        options = {
            key: value for key, value in config_dict.items() if key not in self._non_config_options
        }
        custom_connectors = [
            c for c in connections if c not in {*mandatory_conn_targets, *optional_conn_targets}
        ]
        custom_options = [
            opt for opt in options if opt not in {*mandatory_options, *optional_options}
        ]

        # Update module meta data editors
        self.allow_remote_checkbox.setChecked(allow_remote_access)
        self.remote_url_lineedit.setText(remote_url)
        self.remote_certfile_lineedit.setText(remote_certfile)
        self.remote_keyfile_lineedit.setText(remote_keyfile)

        # add all connectors
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
        for conn in custom_connectors:
            self.add_custom_connector(conn, connections.get(conn, None))

        # add all options
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
        for opt in custom_options:
            self.add_custom_option(opt, repr(options.get(opt, None)))

        # Show different meta option editors for remote modules
        self.module_meta_widget.setVisible(not is_remote_module)
        self.remote_meta_widget.setVisible(is_remote_module)

        # Show editor
        self.placeholder_label.setVisible(False)
        self.specify_name_label.setVisible(False)
        self.splitter.setVisible(True)

    def commit_module_config(self):
        if self.currently_edited_module is not None:
            self.sigModuleConfigFinished.emit(self.currently_edited_module,
                                              self.connections,
                                              self.options,
                                              self.meta_options)

    def close_module_editor(self):
        self.placeholder_label.setVisible(True)
        self.specify_name_label.setVisible(False)
        self.splitter.setVisible(False)
        if self.currently_edited_module is not None:
            self.commit_module_config()
            self._clear_editor_widgets()
            self.header_label.setText('')
            self.currently_edited_module = None

    def show_invalid_module_label(self):
        self.close_module_editor()
        self.specify_name_label.setVisible(True)
        self.placeholder_label.setVisible(False)
        self.splitter.setVisible(False)

    def hide_invalid_module_label(self):
        if self.currently_edited_module is None:
            self.placeholder_label.setVisible(True)
            self.specify_name_label.setVisible(False)
            self.splitter.setVisible(False)

    def _clear_editor_widgets(self):
        # Remove custom connectors and options
        for button, label, editor in reversed(list(self.custom_opt_widgets.values())):
            self.options_layout.removeWidget(button)
            self.options_layout.removeWidget(label)
            self.options_layout.removeWidget(editor)
            button.clicked.disconnect()
            button.setParent(None)
            label.setParent(None)
            editor.setParent(None)
            button.deleteLater()
            label.deleteLater()
            editor.deleteLater()
        self.custom_opt_widgets = dict()
        for button, label, editor in reversed(list(self.custom_conn_widgets.values())):
            self.connector_layout.removeWidget(button)
            self.connector_layout.removeWidget(label)
            self.connector_layout.removeWidget(editor)
            button.clicked.disconnect()
            button.setParent(None)
            label.setParent(None)
            editor.setParent(None)
            button.deleteLater()
            label.deleteLater()
            editor.deleteLater()
        self.custom_conn_widgets = dict()

        # Remove "normal" connectors and options
        for label, lineedit in reversed(list(self.opt_widgets.values())):
            self.options_layout.removeWidget(label)
            self.options_layout.removeWidget(lineedit)
            label.setParent(None)
            lineedit.setParent(None)
            label.deleteLater()
            lineedit.deleteLater()
        self.opt_widgets = dict()
        for label, combobox in reversed(list(self.conn_widgets.values())):
            self.connector_layout.removeWidget(label)
            self.connector_layout.removeWidget(combobox)
            label.setParent(None)
            combobox.setParent(None)
            label.deleteLater()
            combobox.deleteLater()
        self.conn_widgets = dict()
