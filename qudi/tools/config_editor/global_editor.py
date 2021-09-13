# -*- coding: utf-8 -*-
"""

"""

__all__ = ('GlobalConfigurationWidget',)

import os
from PySide2 import QtCore, QtGui, QtWidgets
from qudi.util.paths import get_artwork_dir


class GlobalConfigurationWidget(QtWidgets.QWidget):
    """
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create main layout
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

        # Create header
        header = QtWidgets.QLabel('Global Configuration')
        header.setAlignment(QtCore.Qt.AlignCenter)
        font = header.font()
        font.setBold(True)
        font.setPointSize(10)
        header.setFont(font)
        main_layout.addWidget(header)

        # Create module server groupbox
        server_groupbox = QtWidgets.QGroupBox('Module Server')
        layout = QtWidgets.QGridLayout()
        server_groupbox.setLayout(layout)
        label = QtWidgets.QLabel('Host address:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.host_lineedit = QtWidgets.QLineEdit('localhost')
        self.host_lineedit.setToolTip('The host address to share Qudi modules with remote machines')
        layout.addWidget(label, 0, 0)
        layout.addWidget(self.host_lineedit, 0, 1)
        label = QtWidgets.QLabel('Port:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.port_spinbox = QtWidgets.QSpinBox()
        self.port_spinbox.setToolTip('Port number for the remote module server')
        self.port_spinbox.setRange(0, 65535)
        self.port_spinbox.setValue(12345)
        layout.addWidget(label, 1, 0)
        layout.addWidget(self.port_spinbox, 1, 1)
        label = QtWidgets.QLabel('Certificate file:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.certfile_lineedit = QtWidgets.QLineEdit()
        self.certfile_lineedit.setPlaceholderText('No certificate')
        self.certfile_lineedit.setToolTip('Certificate file path for the remote module server')
        layout.addWidget(label, 2, 0)
        layout.addWidget(self.certfile_lineedit, 2, 1)
        label = QtWidgets.QLabel('Key file:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.keyfile_lineedit = QtWidgets.QLineEdit()
        self.keyfile_lineedit.setPlaceholderText('No key')
        self.keyfile_lineedit.setToolTip('Key file path for the remote module server')
        layout.addWidget(label, 3, 0)
        layout.addWidget(self.keyfile_lineedit, 3, 1)
        main_layout.addWidget(server_groupbox)

        # Create remaining editors in a grid
        layout = QtWidgets.QGridLayout()
        main_layout.addLayout(layout)

        # Create local module server port editor
        label = QtWidgets.QLabel('Local Module Server Port:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.local_port_spinbox = QtWidgets.QSpinBox()
        self.local_port_spinbox.setToolTip('Port number for the local module server')
        self.local_port_spinbox.setRange(0, 65535)
        self.local_port_spinbox.setValue(18861)
        layout.addWidget(label, 0, 0)
        layout.addWidget(self.local_port_spinbox, 0, 1)

        # Create flag editor to enforce remote calls by value
        label = QtWidgets.QLabel('Force remote calls by value:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.force_calls_by_value_checkbox = QtWidgets.QCheckBox()
        self.force_calls_by_value_checkbox.setToolTip(
            'Will force all arguments from remote calls to qudi API methods to pass by value '
            '(serialized -> sent to qudi -> de-serialized).'
        )
        self.force_calls_by_value_checkbox.setChecked(True)
        layout.addWidget(label, 1, 0)
        layout.addWidget(self.force_calls_by_value_checkbox, 1, 1)

        # Create startup modules editor
        label = QtWidgets.QLabel('Startup Modules:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.startup_lineedit = QtWidgets.QLineEdit()
        self.startup_lineedit.setPlaceholderText('No startup modules')
        self.startup_lineedit.setToolTip('Modules to be automatically activated on qudi startup.\n'
                                         'Separate multiple module names with commas.')
        layout.addWidget(label, 2, 0)
        layout.addWidget(self.startup_lineedit, 2, 1)

        # Create stylesheet file path editor
        label = QtWidgets.QLabel('Stylesheet:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.stylesheet_lineedit = QtWidgets.QLineEdit('qdark.qss')
        self.stylesheet_lineedit.setPlaceholderText('Platform dependent Qt default')
        self.stylesheet_lineedit.setToolTip(
            'Absolute file path for qudi QSS stylesheet to use. If just a file name is given '
            'without full path, the file must be located in the "<qudi>/artwork/styles/".'
        )
        layout.addWidget(label, 3, 0)
        layout.addWidget(self.stylesheet_lineedit, 3, 1)

        # Create path extensions editor
        label = QtWidgets.QLabel('Extension Paths:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.extensions_lineedit = QtWidgets.QLineEdit()
        self.extensions_lineedit.setPlaceholderText('No qudi extensions')
        self.extensions_lineedit.setToolTip('Extension module search paths for Qudi.\nSeparate '
                                            'multiple paths with commas.')
        layout.addWidget(label, 4, 0)
        layout.addWidget(self.extensions_lineedit, 4, 1)

        # Create default data path editor
        label = QtWidgets.QLabel('Data Directory:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.data_directory_lineedit = QtWidgets.QLineEdit()
        self.data_directory_lineedit.setPlaceholderText('Default "<UserHome>/qudi/Data/"')
        self.data_directory_lineedit.setToolTip('Default data directory for qudi modules to save '
                                                'measurement data into.')
        layout.addWidget(label, 5, 0)
        layout.addWidget(self.data_directory_lineedit, 5, 1)

        # Create flag editor to auomatically create a data sub-directory for each day
        label = QtWidgets.QLabel('Create daily data directories:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.daily_data_dirs_checkbox = QtWidgets.QCheckBox()
        self.daily_data_dirs_checkbox.setToolTip(
            'Whether to automatically create daily sub-directories in the data directory '
        )
        self.daily_data_dirs_checkbox.setChecked(True)
        layout.addWidget(label, 6, 0)
        layout.addWidget(self.daily_data_dirs_checkbox, 6, 1)

        # Create another layout to hold custom global config options
        self.custom_opt_layout = QtWidgets.QGridLayout()
        self.custom_opt_layout.setColumnStretch(2, 1)
        main_layout.addLayout(self.custom_opt_layout)

        # Add separator
        hline = QtWidgets.QFrame()
        hline.setFrameShape(QtWidgets.QFrame.HLine)
        hline.setFrameShadow(QtWidgets.QFrame.Sunken)
        main_layout.addWidget(hline)

        # Create new option editor button and name lineedit
        layout = QtWidgets.QHBoxLayout()
        main_layout.addLayout(layout)
        icon_path = os.path.join(get_artwork_dir(), 'icons', 'oxygen', '64x64', 'add-icon.png')
        self._remove_icon = QtGui.QIcon(os.path.join(os.path.dirname(icon_path), 'remove-icon.png'))
        self.add_option_button = QtWidgets.QToolButton()
        self.add_option_button.setIcon(QtGui.QIcon(icon_path))
        self.add_option_button.setToolTip('Add a custom option to the global config.')
        self.add_option_button.clicked.connect(self.add_custom_option)
        self.custom_opt_name_lineedit = QtWidgets.QLineEdit()
        self.custom_opt_name_lineedit.setPlaceholderText('Enter custom option name')
        layout.addWidget(self.add_option_button)
        layout.addWidget(self.custom_opt_name_lineedit)
        layout.setStretch(1, 1)

        main_layout.addStretch(1)

        # Keep track of custom options
        self.custom_opt_widgets = dict()

    def get_config_dict(self):
        # remote module server dict
        host = self.host_lineedit.text().strip()
        port = self.port_spinbox.value()
        certfile = self.certfile_lineedit.text().strip()
        keyfile = self.keyfile_lineedit.text().strip()
        remote_modules_server = {'address': host if host else None,
                                 'port': port,
                                 'certfile': certfile if certfile else None,
                                 'keyfile': keyfile if keyfile else None}
        namespace_server_port = self.local_port_spinbox.value()

        # Other options
        default_data_dir = self.data_directory_lineedit.text().strip()
        extensions = [path.strip() for path in self.extensions_lineedit.text().strip().split(',')]
        stylesheet = self.stylesheet_lineedit.text().strip()
        startup = [mod.strip() for mod in self.startup_lineedit.text().strip().split(',')]
        daily_data_dirs = self.daily_data_dirs_checkbox.isChecked()
        force_remote_calls_by_value = self.force_calls_by_value_checkbox.isChecked()

        # Create config dict
        cfg_dict = {'default_data_dir': default_data_dir if default_data_dir else None,
                    'daily_data_dirs': daily_data_dirs,
                    'extensions': extensions if extensions else None,
                    'stylesheet': stylesheet if stylesheet else None,
                    'remote_modules_server': remote_modules_server,
                    'namespace_server_port': namespace_server_port,
                    'force_remote_calls_by_value': force_remote_calls_by_value,
                    'startup': startup if startup else None}

        # Add custom config options
        if self.custom_opt_widgets:
            custom_options = {o: eval(e.text()) if e.text().strip() else None for o, e in
                              self.custom_opt_widgets.items()}
            cfg_dict.update(custom_options)
        return cfg_dict

    @QtCore.Slot(dict)
    def set_config(self, cfg_dict):
        # Create shallow copy of dict
        cfg_dict = cfg_dict.copy()
        default_data_dir = cfg_dict.pop('default_data_dir', None)
        daily_data_dirs = cfg_dict.pop('daily_data_dirs', True)
        extensions = cfg_dict.pop('extensions', None)
        stylesheet = cfg_dict.pop('stylesheet', None)
        startup = cfg_dict.pop('startup', None)
        remote_modules_server = cfg_dict.pop('remote_modules_server', dict())
        host = remote_modules_server.get('address', None)
        port = remote_modules_server.get('port', None)
        certfile = remote_modules_server.get('certfile', None)
        keyfile = remote_modules_server.get('keyfile', None)
        namespace_server_port = cfg_dict.pop('namespace_server_port', None)
        force_remote_calls_by_value = cfg_dict.pop('force_remote_calls_by_value', True)

        self.data_directory_lineedit.setText('' if default_data_dir is None else default_data_dir)
        self.stylesheet_lineedit.setText('' if stylesheet is None else stylesheet)
        self.extensions_lineedit.setText('' if extensions is None else ', '.join(extensions))
        self.startup_lineedit.setText('' if startup is None else ', '.join(startup))
        self.host_lineedit.setText('' if host is None else host)
        self.port_spinbox.setValue(0 if port is None else int(port))
        self.certfile_lineedit.setText('' if certfile is None else certfile)
        self.keyfile_lineedit.setText('' if keyfile is None else keyfile)
        self.local_port_spinbox.setValue(
            0 if namespace_server_port is None else int(namespace_server_port)
        )
        self.force_calls_by_value_checkbox.setChecked(force_remote_calls_by_value)
        self.daily_data_dirs_checkbox.setChecked(daily_data_dirs)

        # Handle custom options (all remaining items in cfg_dict)
        self._clear_custom_widgets()
        for name, value in cfg_dict.items():
            self.add_custom_option(name, repr(value))

    @QtCore.Slot()
    def add_custom_option(self, name=None, value_str=''):
        fixed_names = {'remote_modules_server', 'default_data_dir', 'extensions', 'stylesheet',
                       'startup'}
        name = name if isinstance(name, str) else self.custom_opt_name_lineedit.text().strip()
        self.custom_opt_name_lineedit.clear()
        # Create editor widget for new global config option if name is given
        if name and (name not in fixed_names) and (name not in self.custom_opt_widgets):
            label = QtWidgets.QLabel(f'{name}:')
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            value_editor = QtWidgets.QLineEdit(value_str)
            remove_button = QtWidgets.QToolButton()
            remove_button.setIcon(self._remove_icon)
            remove_button.clicked.connect(lambda: self.remove_custom_option(name))
            row = len(self.custom_opt_widgets)
            self.custom_opt_layout.addWidget(remove_button, row, 0)
            self.custom_opt_layout.addWidget(label, row, 1)
            self.custom_opt_layout.addWidget(value_editor, row, 2)
            self.custom_opt_widgets[name] = (remove_button, label, value_editor)

    @QtCore.Slot(str)
    def remove_custom_option(self, name):
        if name not in self.custom_opt_widgets:
            return

        # Remove all widgets from layout
        for button, label, value_edit in reversed(list(self.custom_opt_widgets.values())):
            self.custom_opt_layout.removeWidget(button)
            self.custom_opt_layout.removeWidget(label)
            self.custom_opt_layout.removeWidget(value_edit)

        # Delete widgets for row to remove
        button, label, value_edit = self.custom_opt_widgets.pop(name)
        button.clicked.disconnect()
        button.setParent(None)
        label.setParent(None)
        value_edit.setParent(None)
        button.deleteLater()
        label.deleteLater()
        value_edit.deleteLater()

        # Add all remaining widgets to layout
        for row, (button, name_edit, value_edit) in enumerate(self.custom_opt_widgets.values()):
            self.custom_opt_layout.addWidget(button, row, 0)
            self.custom_opt_layout.addWidget(name_edit, row, 1)
            self.custom_opt_layout.addWidget(value_edit, row, 2)

    def _clear_custom_widgets(self):
        # Remove all widgets from layout and delete widgets
        for button, label, value_edit in reversed(list(self.custom_opt_widgets.values())):
            self.custom_opt_layout.removeWidget(button)
            self.custom_opt_layout.removeWidget(label)
            self.custom_opt_layout.removeWidget(value_edit)
            button.clicked.disconnect()
            button.setParent(None)
            label.setParent(None)
            value_edit.setParent(None)
            button.deleteLater()
            label.deleteLater()
            value_edit.deleteLater()
        self.custom_opt_widgets = dict()
