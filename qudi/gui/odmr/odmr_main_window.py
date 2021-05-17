# -*- coding: utf-8 -*-
"""
This file contains the qudi main window for the Odmr GUI module.

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
import datetime
from PySide2 import QtCore, QtWidgets, QtGui

from qudi.core.gui.qtwidgets.scientific_spinbox import ScienDSpinBox
from qudi.core.paths import get_artwork_dir

from .odmr_plot_widget import OdmrPlotWidget

__all__ = ('OdmrMainWindow',)


class OdmrMainWindow(QtWidgets.QMainWindow):
    """ The main window for the ODMR measurement GUI
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle('qudi: ODMR')
        # Create central plot widgets
        self.setCentralWidget(OdmrPlotWidget())
        # Create status bar
        self.setStatusBar(OdmrStatusBar())

        # Create QActions
        icon_path = os.path.join(get_artwork_dir(), 'icons')

        icon = QtGui.QIcon(os.path.join(icon_path, 'qudiTheme', '22x22', 'start-counter.png'))
        icon.addFile(os.path.join(icon_path, 'qudiTheme', '22x22', 'stop-counter.png'),
                     state=QtGui.QIcon.On)
        self.action_toggle_measurement = QtWidgets.QAction('Toggle Measurement')
        self.action_toggle_measurement.setCheckable(True)
        self.action_toggle_measurement.setIcon(icon)
        self.action_toggle_measurement.setToolTip('Start/Stop ODMR scan measurement')

        icon = QtGui.QIcon(os.path.join(icon_path, 'qudiTheme', '22x22', 'restart-counter.png'))
        self.action_resume_measurement = QtWidgets.QAction('Resume Measurement')
        self.action_resume_measurement.setIcon(icon)
        self.action_resume_measurement.setToolTip('Resume ODMR scan measurement')

        icon = QtGui.QIcon(os.path.join(icon_path, 'oxygen', '22x22', 'document-save.png'))
        self.action_save_measurement = QtWidgets.QAction('Save Measurement')
        self.action_save_measurement.setIcon(icon)
        self.action_save_measurement.setToolTip(
            'Save ODMR scan measurement.\n'
            'Use text field in the toolbar to specify a nametag for the file.'
        )

        icon = QtGui.QIcon(os.path.join(icon_path, 'oxygen', '22x22', 'dialog-warning.png'))
        self.action_toggle_cw = QtWidgets.QAction('Toggle CW')
        self.action_toggle_cw.setCheckable(True)
        self.action_toggle_cw.setIcon(icon)
        self.action_toggle_cw.setToolTip('Toggle continuous microwave output.\n'
                                         'WARNING: Ensure RF network can handle CW power.')

        icon = QtGui.QIcon(os.path.join(icon_path, 'oxygen', '22x22', 'application-exit.png'))
        self.action_close = QtWidgets.QAction('Close')
        self.action_close.setIcon(icon)

        self.action_show_cw_controls = QtWidgets.QAction('Show CW Controls')
        self.action_show_cw_controls.setCheckable(True)
        self.action_show_cw_controls.setChecked(True)
        self.action_show_cw_controls.setToolTip('Show/Hide CW controls')

        self.action_restore_default_view = QtWidgets.QAction('Restore Default')

        icon = QtGui.QIcon(os.path.join(icon_path, 'oxygen', '22x22', 'configure.png'))
        self.action_show_odmr_settings = QtWidgets.QAction('ODMR Settings')
        self.action_show_odmr_settings.setToolTip(
            'Open a dialog to edit ODMR settings that are not very frequently used.'
        )
        self.action_show_odmr_settings.setIcon(icon)

        self.action_show_fit_configuration = QtWidgets.QAction('Fit Configuration')
        self.action_show_fit_configuration.setToolTip(
            'Open a dialog to edit data fitting configurations available to ODMR.'
        )
        self.action_show_fit_configuration.setIcon(icon)

        # Create QLineEdit for save tag
        self.save_nametag_lineedit = QtWidgets.QLineEdit()
        self.save_nametag_lineedit.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                                 QtWidgets.QSizePolicy.Fixed)
        self.save_nametag_lineedit.setMinimumWidth(
            QtGui.QFontMetrics(ScienDSpinBox().font()).width(75 * ' ')  # roughly 75 chars shown
        )
        self.save_nametag_lineedit.setToolTip('Enter a nametag to include in saved file name')

        # Create toolbar and add actions and QLineEdit
        toolbar = QtWidgets.QToolBar()
        toolbar.addAction(self.action_toggle_measurement)
        toolbar.addAction(self.action_resume_measurement)
        toolbar.addSeparator()
        toolbar.addAction(self.action_save_measurement)
        toolbar.addWidget(self.save_nametag_lineedit)
        toolbar.addSeparator()
        tool_button = QtWidgets.QToolButton()
        tool_button.setDefaultAction(self.action_toggle_cw)
        tool_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        toolbar.addWidget(tool_button)
        self.addToolBar(QtCore.Qt.TopToolBarArea, toolbar)

        # Create menu bar and add actions
        menu_bar = QtWidgets.QMenuBar()
        menu = menu_bar.addMenu('File')
        menu.addAction(self.action_save_measurement)
        menu.addSeparator()
        menu.addAction(self.action_close)
        menu = menu_bar.addMenu('View')
        menu.addAction(self.action_show_cw_controls)
        menu.addSeparator()
        menu.addAction(self.action_restore_default_view)
        menu = menu_bar.addMenu('Settings')
        menu.addAction(self.action_show_odmr_settings)
        menu.addAction(self.action_show_fit_configuration)
        self.setMenuBar(menu_bar)

        # Connect close actions
        self.action_close.triggered.connect(self.close)

    def set_elapsed(self, time=None, sweeps=None):
        status_bar = self.statusBar()
        if sweeps is not None:
            status_bar.elapsed_sweeps_spinbox.setValue(sweeps)
        if time is not None:
            if time >= 0:
                status_bar.elapsed_time_lineedit.setText(str(datetime.timedelta(seconds=round(time))))
            else:
                status_bar.elapsed_time_lineedit.setText('0:00:00')


class OdmrStatusBar(QtWidgets.QStatusBar):
    """
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        min_widget_width = QtGui.QFontMetrics(ScienDSpinBox().font()).width(' 00:00:00 ')

        self.setStyleSheet('QStatusBar::item { border: 0px}')
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        layout.addStretch(1)
        label = QtWidgets.QLabel('Elapsed Sweeps:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label)
        self.elapsed_sweeps_spinbox = QtWidgets.QSpinBox()
        self.elapsed_sweeps_spinbox.setMinimumWidth(min_widget_width)
        self.elapsed_sweeps_spinbox.setMinimum(-1)
        self.elapsed_sweeps_spinbox.setSpecialValueText('NaN')
        self.elapsed_sweeps_spinbox.setValue(-1)
        self.elapsed_sweeps_spinbox.setReadOnly(True)
        self.elapsed_sweeps_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.elapsed_sweeps_spinbox.setFocusPolicy(QtCore.Qt.NoFocus)
        layout.addWidget(self.elapsed_sweeps_spinbox)
        label = QtWidgets.QLabel('Elapsed Time:')
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        layout.addWidget(label)
        self.elapsed_time_lineedit = QtWidgets.QLineEdit('0:00:00')
        self.elapsed_time_lineedit.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.elapsed_time_lineedit.setReadOnly(True)
        self.elapsed_time_lineedit.setMinimumWidth(min_widget_width)
        self.elapsed_time_lineedit.setFocusPolicy(QtCore.Qt.NoFocus)
        layout.addWidget(self.elapsed_time_lineedit)
        self.addPermanentWidget(widget, 1)
