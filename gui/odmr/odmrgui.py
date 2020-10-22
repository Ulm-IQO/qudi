# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI module for ODMR control.

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

import numpy as np
import os
import pyqtgraph as pg

from core.connector import Connector
from core.util import units
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from gui.colordefs import ColorScaleInferno
from gui.colordefs import QudiPalettePale as palette
from gui.fitsettings import FitSettingsDialog, FitSettingsComboBox
from qtpy import QtCore
from qtpy import QtCore, QtWidgets, uic
from qtwidgets.scientific_spinbox import ScienDSpinBox
from qtpy import uic
from functools import partial


class ODMRMainWindow(QtWidgets.QMainWindow):
    """ The main window for the ODMR measurement GUI.
    """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_odmrgui.ui')

        # Load it
        super(ODMRMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()


class ODMRSettingDialog(QtWidgets.QDialog):
    """ The settings dialog for ODMR measurements.
    """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_odmr_settings.ui')

        # Load it
        super(ODMRSettingDialog, self).__init__()
        uic.loadUi(ui_file, self)


class ODMRGui(GUIBase):
    """
    This is the GUI Class for ODMR measurements
    """

    # declare connectors
    odmrlogic1 = Connector(interface='ODMRLogic')
    savelogic = Connector(interface='SaveLogic')

    sigStartOdmrScan = QtCore.Signal()
    sigStopOdmrScan = QtCore.Signal()
    sigContinueOdmrScan = QtCore.Signal()
    sigClearData = QtCore.Signal()
    sigCwMwOn = QtCore.Signal()
    sigMwOff = QtCore.Signal()
    sigMwPowerChanged = QtCore.Signal(float)
    sigMwCwParamsChanged = QtCore.Signal(float, float)
    sigMwSweepParamsChanged = QtCore.Signal(list, list, list, float)
    sigClockFreqChanged = QtCore.Signal(float)
    sigOversamplingChanged = QtCore.Signal(int)
    sigLockInChanged = QtCore.Signal(bool)
    sigFitChanged = QtCore.Signal(str)
    sigNumberOfLinesChanged = QtCore.Signal(int)
    sigRuntimeChanged = QtCore.Signal(float)
    sigDoFit = QtCore.Signal(str, object, object, int, int)
    sigSaveMeasurement = QtCore.Signal(str, list, list)
    sigAverageLinesChanged = QtCore.Signal(int)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition, configuration and initialisation of the ODMR GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """

        self._odmr_logic = self.odmrlogic1()

        # Use the inherited class 'Ui_ODMRGuiUI' to create now the GUI element:
        self._mw = ODMRMainWindow()
        self._sd = ODMRSettingDialog()

        # Create a QSettings object for the mainwindow and store the actual GUI layout
        self.mwsettings = QtCore.QSettings("QUDI", "ODMR")
        self.mwsettings.setValue("geometry", self._mw.saveGeometry())
        self.mwsettings.setValue("windowState", self._mw.saveState())

        # Get hardware constraints to set limits for input widgets
        constraints = self._odmr_logic.get_hw_constraints()

        # Adjust range of scientific spinboxes above what is possible in Qt Designer
        self._mw.cw_frequency_DoubleSpinBox.setMaximum(constraints.max_frequency)
        self._mw.cw_frequency_DoubleSpinBox.setMinimum(constraints.min_frequency)
        self._mw.cw_power_DoubleSpinBox.setMaximum(constraints.max_power)
        self._mw.cw_power_DoubleSpinBox.setMinimum(constraints.min_power)
        self._mw.sweep_power_DoubleSpinBox.setMaximum(constraints.max_power)
        self._mw.sweep_power_DoubleSpinBox.setMinimum(constraints.min_power)

        # Add grid layout for ranges
        groupBox = QtWidgets.QGroupBox(self._mw.dockWidgetContents_3)
        groupBox.setAlignment(QtCore.Qt.AlignLeft)
        groupBox.setTitle('Scanning Ranges')
        gridLayout = QtWidgets.QGridLayout(groupBox)
        for row in range(self._odmr_logic.ranges):
            # start
            start_label = QtWidgets.QLabel(groupBox)
            start_label.setText('Start:')
            setattr(self._mw.odmr_control_DockWidget, 'start_label_{}'.format(row), start_label)
            start_freq_DoubleSpinBox = ScienDSpinBox(groupBox)
            start_freq_DoubleSpinBox.setSuffix('Hz')
            start_freq_DoubleSpinBox.setMaximum(constraints.max_frequency)
            start_freq_DoubleSpinBox.setMinimum(constraints.min_frequency)
            start_freq_DoubleSpinBox.setMinimumSize(QtCore.QSize(80, 0))
            start_freq_DoubleSpinBox.setValue(self._odmr_logic.mw_starts[row])
            start_freq_DoubleSpinBox.setMinimumWidth(75)
            start_freq_DoubleSpinBox.setMaximumWidth(100)
            setattr(self._mw.odmr_control_DockWidget, 'start_freq_DoubleSpinBox_{}'.format(row),
                    start_freq_DoubleSpinBox)
            gridLayout.addWidget(start_label, row, 1, 1, 1)
            gridLayout.addWidget(start_freq_DoubleSpinBox, row, 2, 1, 1)
            start_freq_DoubleSpinBox.editingFinished.connect(self.change_sweep_params)
            # step
            step_label = QtWidgets.QLabel(groupBox)
            step_label.setText('Step:')
            setattr(self._mw.odmr_control_DockWidget, 'step_label_{}'.format(row), step_label)
            step_freq_DoubleSpinBox = ScienDSpinBox(groupBox)
            step_freq_DoubleSpinBox.setSuffix('Hz')
            step_freq_DoubleSpinBox.setMaximum(100e9)
            step_freq_DoubleSpinBox.setMinimumSize(QtCore.QSize(80, 0))
            step_freq_DoubleSpinBox.setValue(self._odmr_logic.mw_steps[row])
            step_freq_DoubleSpinBox.setMinimumWidth(75)
            step_freq_DoubleSpinBox.setMaximumWidth(100)
            step_freq_DoubleSpinBox.editingFinished.connect(self.change_sweep_params)
            setattr(self._mw.odmr_control_DockWidget, 'step_freq_DoubleSpinBox_{}'.format(row),
                    step_freq_DoubleSpinBox)
            gridLayout.addWidget(step_label, row, 3, 1, 1)
            gridLayout.addWidget(step_freq_DoubleSpinBox, row, 4, 1, 1)

            # stop
            stop_label = QtWidgets.QLabel(groupBox)
            stop_label.setText('Stop:')
            setattr(self._mw.odmr_control_DockWidget, 'stop_label_{}'.format(row), stop_label)
            stop_freq_DoubleSpinBox = ScienDSpinBox(groupBox)
            stop_freq_DoubleSpinBox.setSuffix('Hz')
            stop_freq_DoubleSpinBox.setMaximum(constraints.max_frequency)
            stop_freq_DoubleSpinBox.setMinimum(constraints.min_frequency)
            stop_freq_DoubleSpinBox.setMinimumSize(QtCore.QSize(80, 0))
            stop_freq_DoubleSpinBox.setValue(self._odmr_logic.mw_stops[row])
            stop_freq_DoubleSpinBox.setMinimumWidth(75)
            stop_freq_DoubleSpinBox.setMaximumWidth(100)
            stop_freq_DoubleSpinBox.editingFinished.connect(self.change_sweep_params)
            setattr(self._mw.odmr_control_DockWidget, 'stop_freq_DoubleSpinBox_{}'.format(row),
                    stop_freq_DoubleSpinBox)
            gridLayout.addWidget(stop_label, row, 5, 1, 1)
            gridLayout.addWidget(stop_freq_DoubleSpinBox, row, 6, 1, 1)

            # on the first row add buttons to add and remove measurement ranges
            if row == 0:
                # # stop
                # stop_label = QtWidgets.QLabel(groupBox)
                # stop_label.setText('Stop:')
                # setattr(self._mw.odmr_control_DockWidget, 'stop_label_{}'.format(row), stop_label)
                # stop_freq_DoubleSpinBox = ScienDSpinBox(groupBox)
                # stop_freq_DoubleSpinBox.setMaximum(constraints.max_frequency)
                # stop_freq_DoubleSpinBox.setMinimum(constraints.min_frequency)
                # stop_freq_DoubleSpinBox.setMinimumSize(QtCore.QSize(80, 0))
                # stop_freq_DoubleSpinBox.setValue(self._odmr_logic.mw_stops[row])
                # stop_freq_DoubleSpinBox.setMinimumWidth(75)
                # stop_freq_DoubleSpinBox.setMaximumWidth(100)
                # setattr(self._mw.odmr_control_DockWidget, 'stop_freq_DoubleSpinBox_{}'.format(row),
                #         stop_freq_DoubleSpinBox)
                # add range
                add_range_button = QtWidgets.QPushButton(groupBox)
                add_range_button.setText('Add Range')
                add_range_button.setMinimumWidth(75)
                add_range_button.setMaximumWidth(100)
                if self._odmr_logic.mw_scanmode.name == 'SWEEP':
                    add_range_button.setDisabled(True)
                add_range_button.clicked.connect(self.add_ranges_gui_elements_clicked)
                gridLayout.addWidget(add_range_button, row, 7, 1, 1)
                setattr(self._mw.odmr_control_DockWidget, 'add_range_button',
                        add_range_button)

                remove_range_button = QtWidgets.QPushButton(groupBox)
                remove_range_button.setText('Remove Range')
                remove_range_button.setMinimumWidth(75)
                remove_range_button.setMaximumWidth(100)
                remove_range_button.clicked.connect(self.remove_ranges_gui_elements_clicked)
                gridLayout.addWidget(remove_range_button, row, 8, 1, 1)
                setattr(self._mw.odmr_control_DockWidget, 'remove_range_button',
                        remove_range_button)

                matrix_range_label = QtWidgets.QLabel(groupBox)
                matrix_range_label.setText('Matrix Range:')
                matrix_range_label.setMinimumWidth(75)
                matrix_range_label.setMaximumWidth(100)
                gridLayout.addWidget(matrix_range_label, row + 1, 7, 1, 1)

                matrix_range_SpinBox = QtWidgets.QSpinBox(groupBox)
                matrix_range_SpinBox.setValue(0)
                matrix_range_SpinBox.setMinimumWidth(75)
                matrix_range_SpinBox.setMaximumWidth(100)
                matrix_range_SpinBox.setMaximum(self._odmr_logic.ranges - 1)
                gridLayout.addWidget(matrix_range_SpinBox, row + 1, 8, 1, 1)
                setattr(self._mw.odmr_control_DockWidget, 'matrix_range_SpinBox',
                        matrix_range_SpinBox)

        self._mw.fit_range_SpinBox.setMaximum(self._odmr_logic.ranges - 1)
        setattr(self._mw.odmr_control_DockWidget, 'ranges_groupBox', groupBox)
        self._mw.dockWidgetContents_3_grid_layout = self._mw.dockWidgetContents_3.layout()
        self._mw.fit_range_SpinBox.valueChanged.connect(self.change_fit_range)
        # (QWidget * widget, int row, int column, Qt::Alignment alignment = Qt::Alignment())

        self._mw.dockWidgetContents_3_grid_layout.addWidget(groupBox, 7, 1, 1, 5)

        # Add save file tag input box
        self._mw.save_tag_LineEdit = QtWidgets.QLineEdit(self._mw)
        self._mw.save_tag_LineEdit.setMaximumWidth(500)
        self._mw.save_tag_LineEdit.setMinimumWidth(200)
        self._mw.save_tag_LineEdit.setToolTip('Enter a nametag which will be\n'
                                              'added to the filename.')
        self._mw.save_ToolBar.addWidget(self._mw.save_tag_LineEdit)

        # add a clear button to clear the ODMR plots:
        self._mw.clear_odmr_PushButton = QtWidgets.QPushButton(self._mw)
        self._mw.clear_odmr_PushButton.setText('Clear ODMR')
        self._mw.clear_odmr_PushButton.setToolTip('Clear the data of the\n'
                                                  'current ODMR measurements.')
        self._mw.clear_odmr_PushButton.setEnabled(False)
        self._mw.toolBar.addWidget(self._mw.clear_odmr_PushButton)

        # Set up and connect channel combobox
        self.display_channel = 0
        odmr_channels = self._odmr_logic.get_odmr_channels()
        for n, ch in enumerate(odmr_channels):
            self._mw.odmr_channel_ComboBox.addItem(str(ch), n)

        self._mw.odmr_channel_ComboBox.activated.connect(self.update_channel)

        # Get the image from the logic
        self.odmr_matrix_image = pg.ImageItem(
            self._odmr_logic.odmr_plot_xy[:, self.display_channel],
            axisOrder='row-major')
        self.odmr_matrix_image.setRect(QtCore.QRectF(
            self._odmr_logic.mw_starts[0],
            0,
            self._odmr_logic.mw_stops[0] - self._odmr_logic.mw_starts[0],
            self._odmr_logic.number_of_lines
        ))

        self.odmr_image = pg.PlotDataItem(self._odmr_logic.odmr_plot_x,
                                          self._odmr_logic.odmr_plot_y[self.display_channel],
                                          pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                                          symbol='o',
                                          symbolPen=palette.c1,
                                          symbolBrush=palette.c1,
                                          symbolSize=7)

        self.odmr_fit_image = pg.PlotDataItem(self._odmr_logic.odmr_fit_x,
                                              self._odmr_logic.odmr_fit_y,
                                              pen=pg.mkPen(palette.c2))

        # Add the display item to the xy and xz ViewWidget, which was defined in the UI file.
        self._mw.odmr_PlotWidget.addItem(self.odmr_image)
        self._mw.odmr_PlotWidget.setLabel(axis='left', text='Counts', units='Counts/s')
        self._mw.odmr_PlotWidget.setLabel(axis='bottom', text='Frequency', units='Hz')
        self._mw.odmr_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        self._mw.odmr_matrix_PlotWidget.addItem(self.odmr_matrix_image)
        self._mw.odmr_matrix_PlotWidget.setLabel(axis='left', text='Matrix Lines', units='#')
        self._mw.odmr_matrix_PlotWidget.setLabel(axis='bottom', text='Frequency', units='Hz')

        # Get the colorscales at set LUT
        my_colors = ColorScaleInferno()
        self.odmr_matrix_image.setLookupTable(my_colors.lut)

        ########################################################################
        #                  Configuration of the Colorbar                       #
        ########################################################################
        self.odmr_cb = ColorBar(my_colors.cmap_normed, 100, 0, 100000)

        # adding colorbar to ViewWidget
        self._mw.odmr_cb_PlotWidget.addItem(self.odmr_cb)
        self._mw.odmr_cb_PlotWidget.hideAxis('bottom')
        self._mw.odmr_cb_PlotWidget.hideAxis('left')
        self._mw.odmr_cb_PlotWidget.setLabel('right', 'Fluorescence', units='counts/s')

        ########################################################################
        #          Configuration of the various display Widgets                #
        ########################################################################
        # Take the default values from logic:
        self._mw.cw_frequency_DoubleSpinBox.setValue(self._odmr_logic.cw_mw_frequency)
        self._mw.cw_power_DoubleSpinBox.setValue(self._odmr_logic.cw_mw_power)
        self._mw.sweep_power_DoubleSpinBox.setValue(self._odmr_logic.sweep_mw_power)

        self._mw.runtime_DoubleSpinBox.setValue(self._odmr_logic.run_time)
        self._mw.elapsed_time_DisplayWidget.display(int(np.rint(self._odmr_logic.elapsed_time)))
        self._mw.elapsed_sweeps_DisplayWidget.display(self._odmr_logic.elapsed_sweeps)
        self._mw.average_level_SpinBox.setValue(self._odmr_logic.lines_to_average)

        self._sd.matrix_lines_SpinBox.setValue(self._odmr_logic.number_of_lines)
        self._sd.clock_frequency_DoubleSpinBox.setValue(self._odmr_logic.clock_frequency)
        self._sd.oversampling_SpinBox.setValue(self._odmr_logic.oversampling)
        self._sd.lock_in_CheckBox.setChecked(self._odmr_logic.lock_in)

        # fit settings
        self._fsd = FitSettingsDialog(self._odmr_logic.fc)
        self._fsd.sigFitsUpdated.connect(self._mw.fit_methods_ComboBox.setFitFunctions)
        self._fsd.applySettings()
        self._mw.action_FitSettings.triggered.connect(self._fsd.show)

        ########################################################################
        #                       Connect signals                                #
        ########################################################################
        # Internal user input changed signals
        self._mw.cw_frequency_DoubleSpinBox.editingFinished.connect(self.change_cw_params)

        self._mw.sweep_power_DoubleSpinBox.editingFinished.connect(self.change_sweep_params)
        self._mw.cw_power_DoubleSpinBox.editingFinished.connect(self.change_cw_params)
        self._mw.runtime_DoubleSpinBox.editingFinished.connect(self.change_runtime)
        self._mw.odmr_cb_max_DoubleSpinBox.valueChanged.connect(self.colorscale_changed)
        self._mw.odmr_cb_min_DoubleSpinBox.valueChanged.connect(self.colorscale_changed)
        self._mw.odmr_cb_high_percentile_DoubleSpinBox.valueChanged.connect(self.colorscale_changed)
        self._mw.odmr_cb_low_percentile_DoubleSpinBox.valueChanged.connect(self.colorscale_changed)
        self._mw.average_level_SpinBox.valueChanged.connect(self.average_level_changed)
        # Internal trigger signals
        self._mw.odmr_cb_manual_RadioButton.clicked.connect(self.colorscale_changed)
        self._mw.odmr_cb_centiles_RadioButton.clicked.connect(self.colorscale_changed)
        self._mw.clear_odmr_PushButton.clicked.connect(self.clear_odmr_data)
        self._mw.action_run_stop.triggered.connect(self.run_stop_odmr)
        self._mw.action_resume_odmr.triggered.connect(self.resume_odmr)
        self._mw.action_toggle_cw.triggered.connect(self.toggle_cw_mode)
        self._mw.action_Save.triggered.connect(self.save_data)
        self._mw.action_RestoreDefault.triggered.connect(self.restore_defaultview)
        self._mw.do_fit_PushButton.clicked.connect(self.do_fit)
        self._mw.fit_range_SpinBox.editingFinished.connect(self.update_fit_range)
        self._mw.odmr_control_DockWidget.matrix_range_SpinBox.editingFinished.connect(self.update_matrix_range)

        # Control/values-changed signals to logic
        self.sigCwMwOn.connect(self._odmr_logic.mw_cw_on, QtCore.Qt.QueuedConnection)
        self.sigMwOff.connect(self._odmr_logic.mw_off, QtCore.Qt.QueuedConnection)
        self.sigClearData.connect(self._odmr_logic.clear_odmr_data, QtCore.Qt.QueuedConnection)
        self.sigStartOdmrScan.connect(self._odmr_logic.start_odmr_scan, QtCore.Qt.QueuedConnection)
        self.sigStopOdmrScan.connect(self._odmr_logic.stop_odmr_scan, QtCore.Qt.QueuedConnection)
        self.sigContinueOdmrScan.connect(self._odmr_logic.continue_odmr_scan,
                                         QtCore.Qt.QueuedConnection)
        self.sigDoFit.connect(self._odmr_logic.do_fit, QtCore.Qt.QueuedConnection)
        self.sigMwCwParamsChanged.connect(self._odmr_logic.set_cw_parameters,
                                          QtCore.Qt.QueuedConnection)
        self.sigMwSweepParamsChanged.connect(self._odmr_logic.set_sweep_parameters,
                                             QtCore.Qt.QueuedConnection)
        self.sigRuntimeChanged.connect(self._odmr_logic.set_runtime, QtCore.Qt.QueuedConnection)
        self.sigNumberOfLinesChanged.connect(self._odmr_logic.set_matrix_line_number,
                                             QtCore.Qt.QueuedConnection)
        self.sigClockFreqChanged.connect(self._odmr_logic.set_clock_frequency,
                                         QtCore.Qt.QueuedConnection)
        self.sigOversamplingChanged.connect(self._odmr_logic.set_oversampling, QtCore.Qt.QueuedConnection)
        self.sigLockInChanged.connect(self._odmr_logic.set_lock_in, QtCore.Qt.QueuedConnection)
        self.sigSaveMeasurement.connect(self._odmr_logic.save_odmr_data, QtCore.Qt.QueuedConnection)
        self.sigAverageLinesChanged.connect(self._odmr_logic.set_average_length,
                                            QtCore.Qt.QueuedConnection)

        # Update signals coming from logic:
        self._odmr_logic.sigParameterUpdated.connect(self.update_parameter,
                                                     QtCore.Qt.QueuedConnection)
        self._odmr_logic.sigOutputStateUpdated.connect(self.update_status,
                                                       QtCore.Qt.QueuedConnection)
        self._odmr_logic.sigOdmrPlotsUpdated.connect(self.update_plots, QtCore.Qt.QueuedConnection)
        self._odmr_logic.sigOdmrFitUpdated.connect(self.update_fit, QtCore.Qt.QueuedConnection)
        self._odmr_logic.sigOdmrElapsedTimeUpdated.connect(self.update_elapsedtime,
                                                           QtCore.Qt.QueuedConnection)

        # connect settings signals
        self._mw.action_Settings.triggered.connect(self._menu_settings)
        self._sd.accepted.connect(self.update_settings)
        self._sd.rejected.connect(self.reject_settings)
        self._sd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(
            self.update_settings)
        self.reject_settings()

        # Show the Main ODMR GUI:
        self.show()

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        # Disconnect signals
        self._sd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.disconnect()
        self._sd.accepted.disconnect()
        self._sd.rejected.disconnect()
        self._mw.action_Settings.triggered.disconnect()
        self._odmr_logic.sigParameterUpdated.disconnect()
        self._odmr_logic.sigOutputStateUpdated.disconnect()
        self._odmr_logic.sigOdmrPlotsUpdated.disconnect()
        self._odmr_logic.sigOdmrFitUpdated.disconnect()
        self._odmr_logic.sigOdmrElapsedTimeUpdated.disconnect()
        self.sigCwMwOn.disconnect()
        self.sigMwOff.disconnect()
        self.sigClearData.disconnect()
        self.sigStartOdmrScan.disconnect()
        self.sigStopOdmrScan.disconnect()
        self.sigContinueOdmrScan.disconnect()
        self.sigDoFit.disconnect()
        self.sigMwCwParamsChanged.disconnect()
        self.sigMwSweepParamsChanged.disconnect()
        self.sigRuntimeChanged.disconnect()
        self.sigNumberOfLinesChanged.disconnect()
        self.sigClockFreqChanged.disconnect()
        self.sigOversamplingChanged.disconnect()
        self.sigLockInChanged.disconnect()
        self.sigSaveMeasurement.disconnect()
        self.sigAverageLinesChanged.disconnect()
        self._mw.odmr_cb_manual_RadioButton.clicked.disconnect()
        self._mw.odmr_cb_centiles_RadioButton.clicked.disconnect()
        self._mw.clear_odmr_PushButton.clicked.disconnect()
        self._mw.action_run_stop.triggered.disconnect()
        self._mw.action_resume_odmr.triggered.disconnect()
        self._mw.action_Save.triggered.disconnect()
        self._mw.action_toggle_cw.triggered.disconnect()
        self._mw.action_RestoreDefault.triggered.disconnect()
        self._mw.do_fit_PushButton.clicked.disconnect()
        self._mw.cw_frequency_DoubleSpinBox.editingFinished.disconnect()
        dspinbox_dict = self.get_all_dspinboxes_from_groupbox()
        for identifier_name in dspinbox_dict:
            dspinbox_type_list = dspinbox_dict[identifier_name]
            [dspinbox_type.editingFinished.disconnect() for dspinbox_type in dspinbox_type_list]

        self._mw.cw_power_DoubleSpinBox.editingFinished.disconnect()
        self._mw.sweep_power_DoubleSpinBox.editingFinished.disconnect()
        self._mw.runtime_DoubleSpinBox.editingFinished.disconnect()
        self._mw.odmr_cb_max_DoubleSpinBox.valueChanged.disconnect()
        self._mw.odmr_cb_min_DoubleSpinBox.valueChanged.disconnect()
        self._mw.odmr_cb_high_percentile_DoubleSpinBox.valueChanged.disconnect()
        self._mw.odmr_cb_low_percentile_DoubleSpinBox.valueChanged.disconnect()
        self._mw.average_level_SpinBox.valueChanged.disconnect()
        self._fsd.sigFitsUpdated.disconnect()
        self._mw.fit_range_SpinBox.editingFinished.disconnect()
        self._mw.action_FitSettings.triggered.disconnect()
        self._mw.close()
        return 0

    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def _menu_settings(self):
        """ Open the settings menu """
        self._sd.exec_()

    def add_ranges_gui_elements_clicked(self):
        """
        When button >>add range<< is pushed add some buttons to the gui and connect accordingly to the
        logic.
        :return:
        """
        # make sure the logic keeps track
        groupBox = self._mw.odmr_control_DockWidget.ranges_groupBox
        gridLayout = groupBox.layout()
        constraints = self._odmr_logic.get_hw_constraints()

        insertion_row = self._odmr_logic.ranges
        # start
        start_label = QtWidgets.QLabel(groupBox)
        start_label.setText('Start:')
        setattr(self._mw.odmr_control_DockWidget, 'start_label_{}'.format(insertion_row), start_label)
        start_freq_DoubleSpinBox = ScienDSpinBox(groupBox)
        start_freq_DoubleSpinBox.setSuffix('Hz')
        start_freq_DoubleSpinBox.setMaximum(constraints.max_frequency)
        start_freq_DoubleSpinBox.setMinimum(constraints.min_frequency)
        start_freq_DoubleSpinBox.setMinimumSize(QtCore.QSize(80, 0))
        start_freq_DoubleSpinBox.setValue(self._odmr_logic.mw_starts[0])
        start_freq_DoubleSpinBox.setMinimumWidth(75)
        start_freq_DoubleSpinBox.setMaximumWidth(100)
        start_freq_DoubleSpinBox.editingFinished.connect(self.change_sweep_params)
        setattr(self._mw.odmr_control_DockWidget, 'start_freq_DoubleSpinBox_{}'.format(insertion_row),
                start_freq_DoubleSpinBox)
        gridLayout.addWidget(start_label, insertion_row, 1, 1, 1)
        gridLayout.addWidget(start_freq_DoubleSpinBox, insertion_row, 2, 1, 1)

        # step
        step_label = QtWidgets.QLabel(groupBox)
        step_label.setText('Step:')
        setattr(self._mw.odmr_control_DockWidget, 'step_label_{}'.format(insertion_row), step_label)
        step_freq_DoubleSpinBox = ScienDSpinBox(groupBox)
        step_freq_DoubleSpinBox.setSuffix('Hz')
        step_freq_DoubleSpinBox.setMaximum(100e9)
        step_freq_DoubleSpinBox.setMinimumSize(QtCore.QSize(80, 0))
        step_freq_DoubleSpinBox.setValue(self._odmr_logic.mw_steps[0])
        step_freq_DoubleSpinBox.setMinimumWidth(75)
        step_freq_DoubleSpinBox.setMaximumWidth(100)
        step_freq_DoubleSpinBox.editingFinished.connect(self.change_sweep_params)
        setattr(self._mw.odmr_control_DockWidget, 'step_freq_DoubleSpinBox_{}'.format(insertion_row),
                step_freq_DoubleSpinBox)
        gridLayout.addWidget(step_label, insertion_row, 3, 1, 1)
        gridLayout.addWidget(step_freq_DoubleSpinBox, insertion_row, 4, 1, 1)

        # stop
        stop_label = QtWidgets.QLabel(groupBox)
        stop_label.setText('Stop:')
        setattr(self._mw.odmr_control_DockWidget, 'stop_label_{}'.format(insertion_row), stop_label)
        stop_freq_DoubleSpinBox = ScienDSpinBox(groupBox)
        stop_freq_DoubleSpinBox.setSuffix('Hz')
        stop_freq_DoubleSpinBox.setMaximum(constraints.max_frequency)
        stop_freq_DoubleSpinBox.setMinimum(constraints.min_frequency)
        stop_freq_DoubleSpinBox.setMinimumSize(QtCore.QSize(80, 0))
        stop_freq_DoubleSpinBox.setValue(self._odmr_logic.mw_stops[0])
        stop_freq_DoubleSpinBox.setMinimumWidth(75)
        stop_freq_DoubleSpinBox.setMaximumWidth(100)
        stop_freq_DoubleSpinBox.editingFinished.connect(self.change_sweep_params)
        setattr(self._mw.odmr_control_DockWidget, 'stop_freq_DoubleSpinBox_{}'.format(insertion_row),
                stop_freq_DoubleSpinBox)

        gridLayout.addWidget(stop_label, insertion_row, 5, 1, 1)
        gridLayout.addWidget(stop_freq_DoubleSpinBox, insertion_row, 6, 1, 1)

        starts = self.get_frequencies_from_spinboxes('start')
        stops = self.get_frequencies_from_spinboxes('stop')
        steps = self.get_frequencies_from_spinboxes('step')
        power = self._mw.sweep_power_DoubleSpinBox.value()

        self.sigMwSweepParamsChanged.emit(starts, stops, steps, power)
        self._mw.fit_range_SpinBox.setMaximum(self._odmr_logic.ranges)
        self._mw.odmr_control_DockWidget.matrix_range_SpinBox.setMaximum(self._odmr_logic.ranges)
        self._odmr_logic.ranges += 1

        # remove stuff that remained from the old range that might have been in place there
        key = 'channel: {0}, range: {1}'.format(self.display_channel, self._odmr_logic.ranges - 1)
        if key in self._odmr_logic.fits_performed:
            self._odmr_logic.fits_performed.pop(key)
        return

    def remove_ranges_gui_elements_clicked(self):
        if self._odmr_logic.ranges == 1:
            return

        remove_row = self._odmr_logic.ranges - 1

        groupBox = self._mw.odmr_control_DockWidget.ranges_groupBox
        gridLayout = groupBox.layout()

        object_dict = self.get_objects_from_groupbox_row(remove_row)

        for object_name in object_dict:
            if 'DoubleSpinBox' in object_name:
                object_dict[object_name].editingFinished.disconnect()
            object_dict[object_name].hide()
            gridLayout.removeWidget(object_dict[object_name])
            del self._mw.odmr_control_DockWidget.__dict__[object_name]

        starts = self.get_frequencies_from_spinboxes('start')
        stops = self.get_frequencies_from_spinboxes('stop')
        steps = self.get_frequencies_from_spinboxes('step')
        power = self._mw.sweep_power_DoubleSpinBox.value()
        self.sigMwSweepParamsChanged.emit(starts, stops, steps, power)

        # in case the removed range is the one selected for fitting right now adjust the value
        self._odmr_logic.ranges -= 1
        max_val = self._odmr_logic.ranges - 1
        self._mw.fit_range_SpinBox.setMaximum(max_val)
        if self._odmr_logic.range_to_fit > max_val:
            self._odmr_logic.range_to_fit = max_val

        self._mw.fit_range_SpinBox.setMaximum(max_val)
        
        self._mw.odmr_control_DockWidget.matrix_range_SpinBox.setMaximum(max_val)
        if self._mw.odmr_control_DockWidget.matrix_range_SpinBox.value() > max_val:
            self._mw.odmr_control_DockWidget.matrix_range_SpinBox.setValue(max_val)

        return

    def get_objects_from_groupbox_row(self, row):
        # get elements from the row
        # first strings

        start_label_str = 'start_label_{}'.format(row)
        step_label_str = 'step_label_{}'.format(row)
        stop_label_str = 'stop_label_{}'.format(row)

        # get widgets
        start_freq_DoubleSpinBox_str = 'start_freq_DoubleSpinBox_{}'.format(row)
        step_freq_DoubleSpinBox_str = 'step_freq_DoubleSpinBox_{}'.format(row)
        stop_freq_DoubleSpinBox_str = 'stop_freq_DoubleSpinBox_{}'.format(row)

        # now get the objects
        start_label = getattr(self._mw.odmr_control_DockWidget, start_label_str)
        step_label = getattr(self._mw.odmr_control_DockWidget, step_label_str)
        stop_label = getattr(self._mw.odmr_control_DockWidget, stop_label_str)

        start_freq_DoubleSpinBox = getattr(self._mw.odmr_control_DockWidget, start_freq_DoubleSpinBox_str)
        step_freq_DoubleSpinBox = getattr(self._mw.odmr_control_DockWidget, step_freq_DoubleSpinBox_str)
        stop_freq_DoubleSpinBox = getattr(self._mw.odmr_control_DockWidget, stop_freq_DoubleSpinBox_str)

        return_dict = {start_label_str: start_label, step_label_str: step_label,
                       stop_label_str: stop_label,
                       start_freq_DoubleSpinBox_str: start_freq_DoubleSpinBox,
                       step_freq_DoubleSpinBox_str: step_freq_DoubleSpinBox,
                       stop_freq_DoubleSpinBox_str: stop_freq_DoubleSpinBox
                       }

        return return_dict

    def get_freq_dspinboxes_from_groubpox(self, identifier):
        dspinboxes = []
        for name in self._mw.odmr_control_DockWidget.__dict__:
            box_name = identifier + '_freq_DoubleSpinBox'
            if box_name in name:
                freq_DoubleSpinBox = getattr(self._mw.odmr_control_DockWidget, name)
                dspinboxes.append(freq_DoubleSpinBox)

        return dspinboxes

    def get_all_dspinboxes_from_groupbox(self):
        identifiers = ['start', 'step', 'stop']

        all_spinboxes = {}
        for identifier in identifiers:
            all_spinboxes[identifier] = self.get_freq_dspinboxes_from_groubpox(identifier)

        return all_spinboxes

    def get_frequencies_from_spinboxes(self, identifier):
        dspinboxes = self.get_freq_dspinboxes_from_groubpox(identifier)
        freqs = [dspinbox.value() for dspinbox in dspinboxes]
        return freqs

    def run_stop_odmr(self, is_checked):
        """ Manages what happens if odmr scan is started/stopped. """
        if is_checked:
            # change the axes appearance according to input values:
            self._mw.action_run_stop.setEnabled(False)
            self._mw.action_resume_odmr.setEnabled(False)
            self._mw.action_toggle_cw.setEnabled(False)
            self._mw.odmr_PlotWidget.removeItem(self.odmr_fit_image)
            self._mw.cw_power_DoubleSpinBox.setEnabled(False)
            self._mw.sweep_power_DoubleSpinBox.setEnabled(False)
            self._mw.cw_frequency_DoubleSpinBox.setEnabled(False)
            dspinbox_dict = self.get_all_dspinboxes_from_groupbox()
            for identifier_name in dspinbox_dict:
                dspinbox_type_list = dspinbox_dict[identifier_name]
                [dspinbox_type.setEnabled(False) for dspinbox_type in dspinbox_type_list]
            self._mw.odmr_control_DockWidget.add_range_button.setEnabled(False)
            self._mw.odmr_control_DockWidget.remove_range_button.setEnabled(False)
            self._mw.runtime_DoubleSpinBox.setEnabled(False)
            self._sd.clock_frequency_DoubleSpinBox.setEnabled(False)
            self._sd.oversampling_SpinBox.setEnabled(False)
            self._sd.lock_in_CheckBox.setEnabled(False)
            self.sigStartOdmrScan.emit()
        else:
            self._mw.action_run_stop.setEnabled(False)
            self._mw.action_resume_odmr.setEnabled(False)
            self._mw.action_toggle_cw.setEnabled(False)
            self.sigStopOdmrScan.emit()
        return

    def resume_odmr(self, is_checked):
        if is_checked:
            self._mw.action_run_stop.setEnabled(False)
            self._mw.action_resume_odmr.setEnabled(False)
            self._mw.action_toggle_cw.setEnabled(False)
            self._mw.cw_power_DoubleSpinBox.setEnabled(False)
            self._mw.sweep_power_DoubleSpinBox.setEnabled(False)
            self._mw.cw_frequency_DoubleSpinBox.setEnabled(False)
            dspinbox_dict = self.get_all_dspinboxes_from_groupbox()
            for identifier_name in dspinbox_dict:
                dspinbox_type_list = dspinbox_dict[identifier_name]
                [dspinbox_type.setEnabled(False) for dspinbox_type in dspinbox_type_list]
            self._mw.odmr_control_DockWidget.add_range_button.setEnabled(False)
            self._mw.odmr_control_DockWidget.remove_range_button.setEnabled(False)
            self._mw.runtime_DoubleSpinBox.setEnabled(False)
            self._sd.clock_frequency_DoubleSpinBox.setEnabled(False)
            self._sd.oversampling_SpinBox.setEnabled(False)
            self._sd.lock_in_CheckBox.setEnabled(False)
            self.sigContinueOdmrScan.emit()
        else:
            self._mw.action_run_stop.setEnabled(False)
            self._mw.action_resume_odmr.setEnabled(False)
            self._mw.action_toggle_cw.setEnabled(False)
            self.sigStopOdmrScan.emit()
        return

    def toggle_cw_mode(self, is_checked):
        """ Starts or stops CW microwave output if no measurement is running. """
        if is_checked:
            self._mw.action_run_stop.setEnabled(False)
            self._mw.action_resume_odmr.setEnabled(False)
            self._mw.action_toggle_cw.setEnabled(False)
            self._mw.cw_power_DoubleSpinBox.setEnabled(False)
            self._mw.cw_frequency_DoubleSpinBox.setEnabled(False)
            self.sigCwMwOn.emit()
        else:
            self._mw.action_toggle_cw.setEnabled(False)
            self.sigMwOff.emit()
        return

    def update_status(self, mw_mode, is_running):
        """
        Update the display for a change in the microwave status (mode and output).

        @param str mw_mode: is the microwave output active?
        @param bool is_running: is the microwave output active?
        """
        # Block signals from firing
        self._mw.action_run_stop.blockSignals(True)
        self._mw.action_resume_odmr.blockSignals(True)
        self._mw.action_toggle_cw.blockSignals(True)

        # Update measurement status (activate/deactivate widgets/actions)
        if is_running:
            self._mw.action_resume_odmr.setEnabled(False)
            self._mw.cw_power_DoubleSpinBox.setEnabled(False)
            self._mw.cw_frequency_DoubleSpinBox.setEnabled(False)
            if mw_mode != 'cw':
                self._mw.clear_odmr_PushButton.setEnabled(True)
                self._mw.action_run_stop.setEnabled(True)
                self._mw.action_toggle_cw.setEnabled(False)
                dspinbox_dict = self.get_all_dspinboxes_from_groupbox()
                for identifier_name in dspinbox_dict:
                    dspinbox_type_list = dspinbox_dict[identifier_name]
                    [dspinbox_type.setEnabled(False) for dspinbox_type in dspinbox_type_list]
                self._mw.odmr_control_DockWidget.add_range_button.setEnabled(False)
                self._mw.odmr_control_DockWidget.remove_range_button.setEnabled(False)
                self._mw.sweep_power_DoubleSpinBox.setEnabled(False)
                self._mw.runtime_DoubleSpinBox.setEnabled(False)
                self._sd.clock_frequency_DoubleSpinBox.setEnabled(False)
                self._sd.oversampling_SpinBox.setEnabled(False)
                self._sd.lock_in_CheckBox.setEnabled(False)
                self._mw.action_run_stop.setChecked(True)
                self._mw.action_resume_odmr.setChecked(True)
                self._mw.action_toggle_cw.setChecked(False)
            else:
                self._mw.clear_odmr_PushButton.setEnabled(False)
                self._mw.action_run_stop.setEnabled(False)
                self._mw.action_toggle_cw.setEnabled(True)
                dspinbox_dict = self.get_all_dspinboxes_from_groupbox()
                for identifier_name in dspinbox_dict:
                    dspinbox_type_list = dspinbox_dict[identifier_name]
                    [dspinbox_type.setEnabled(True) for dspinbox_type in dspinbox_type_list]
                self._mw.odmr_control_DockWidget.add_range_button.setEnabled(True)
                self._mw.odmr_control_DockWidget.remove_range_button.setEnabled(True)
                self._mw.sweep_power_DoubleSpinBox.setEnabled(True)
                self._mw.runtime_DoubleSpinBox.setEnabled(True)
                self._sd.clock_frequency_DoubleSpinBox.setEnabled(True)
                self._sd.oversampling_SpinBox.setEnabled(True)
                self._sd.lock_in_CheckBox.setEnabled(True)
                self._mw.action_run_stop.setChecked(False)
                self._mw.action_resume_odmr.setChecked(False)
                self._mw.action_toggle_cw.setChecked(True)
        else:
            self._mw.action_resume_odmr.setEnabled(True)
            self._mw.cw_power_DoubleSpinBox.setEnabled(True)
            self._mw.sweep_power_DoubleSpinBox.setEnabled(True)
            self._mw.cw_frequency_DoubleSpinBox.setEnabled(True)
            self._mw.clear_odmr_PushButton.setEnabled(False)
            self._mw.action_run_stop.setEnabled(True)
            self._mw.action_toggle_cw.setEnabled(True)
            dspinbox_dict = self.get_all_dspinboxes_from_groupbox()
            for identifier_name in dspinbox_dict:
                dspinbox_type_list = dspinbox_dict[identifier_name]
                [dspinbox_type.setEnabled(True) for dspinbox_type in dspinbox_type_list]
            if self._odmr_logic.mw_scanmode.name == 'SWEEP':
                self._mw.odmr_control_DockWidget.add_range_button.setDisabled(True)
            elif self._odmr_logic.mw_scanmode.name == 'LIST':
                self._mw.odmr_control_DockWidget.add_range_button.setEnabled(True)
            self._mw.odmr_control_DockWidget.remove_range_button.setEnabled(True)
            self._mw.runtime_DoubleSpinBox.setEnabled(True)
            self._sd.clock_frequency_DoubleSpinBox.setEnabled(True)
            self._sd.oversampling_SpinBox.setEnabled(True)
            self._sd.lock_in_CheckBox.setEnabled(True)
            self._mw.action_run_stop.setChecked(False)
            self._mw.action_resume_odmr.setChecked(False)
            self._mw.action_toggle_cw.setChecked(False)

        # Unblock signal firing
        self._mw.action_run_stop.blockSignals(False)
        self._mw.action_resume_odmr.blockSignals(False)
        self._mw.action_toggle_cw.blockSignals(False)
        return

    def clear_odmr_data(self):
        """ Clear the ODMR data. """
        self.sigClearData.emit()
        return

    def update_plots(self, odmr_data_x, odmr_data_y, odmr_matrix):
        """ Refresh the plot widgets with new data. """
        # Update mean signal plot
        self.odmr_image.setData(odmr_data_x, odmr_data_y[self.display_channel])
        # Update raw data matrix plot
        cb_range = self.get_matrix_cb_range()
        self.update_colorbar(cb_range)
        matrix_range = self._mw.odmr_control_DockWidget.matrix_range_SpinBox.value()
        start = self._odmr_logic.mw_starts[matrix_range]
        step = self._odmr_logic.mw_steps[matrix_range]
        stop = self._odmr_logic.mw_stops[matrix_range]
        selected_odmr_data_x = np.arange(start, stop, step)

        self.odmr_matrix_image.setRect(
            QtCore.QRectF(
                selected_odmr_data_x[0],
                0,
                np.abs(selected_odmr_data_x[-1] - selected_odmr_data_x[0]),
                odmr_matrix.shape[0])
        )

        odmr_matrix_range = self._odmr_logic.select_odmr_matrix_data(odmr_matrix, self.display_channel, matrix_range)
        self.odmr_matrix_image.setImage(
            image=odmr_matrix_range,
            axisOrder='row-major',
            levels=(cb_range[0], cb_range[1]))

    def update_channel(self, index):
        self.display_channel = int(
            self._mw.odmr_channel_ComboBox.itemData(index, QtCore.Qt.UserRole))
        self.update_plots(
            self._odmr_logic.odmr_plot_x,
            self._odmr_logic.odmr_plot_y,
            self._odmr_logic.odmr_plot_xy)

    def average_level_changed(self):
        """
        Sends to lines to average to the logic
        """
        self.sigAverageLinesChanged.emit(self._mw.average_level_SpinBox.value())
        return

    def colorscale_changed(self):
        """
        Updates the range of the displayed colorscale in both the colorbar and the matrix plot.
        """
        cb_range = self.get_matrix_cb_range()
        self.update_colorbar(cb_range)
        matrix_image = self.odmr_matrix_image.image
        self.odmr_matrix_image.setImage(image=matrix_image, levels=(cb_range[0], cb_range[1]))
        return

    def update_colorbar(self, cb_range):
        """
        Update the colorbar to a new range.

        @param list cb_range: List or tuple containing the min and max values for the cb range
        """
        self.odmr_cb.refresh_colorbar(cb_range[0], cb_range[1])
        return

    def get_matrix_cb_range(self):
        """
        Determines the cb_min and cb_max values for the matrix plot
        """
        matrix_image = self.odmr_matrix_image.image

        # If "Manual" is checked or the image is empty (all zeros), then take manual cb range.
        # Otherwise, calculate cb range from percentiles.
        if self._mw.odmr_cb_manual_RadioButton.isChecked() or np.count_nonzero(matrix_image) < 1:
            cb_min = self._mw.odmr_cb_min_DoubleSpinBox.value()
            cb_max = self._mw.odmr_cb_max_DoubleSpinBox.value()
        else:
            # Exclude any zeros (which are typically due to unfinished scan)
            matrix_image_nonzero = matrix_image[np.nonzero(matrix_image)]

            # Read centile range
            low_centile = self._mw.odmr_cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.odmr_cb_high_percentile_DoubleSpinBox.value()

            cb_min = np.percentile(matrix_image_nonzero, low_centile)
            cb_max = np.percentile(matrix_image_nonzero, high_centile)

        cb_range = [cb_min, cb_max]
        return cb_range

    def restore_defaultview(self):
        self._mw.restoreGeometry(self.mwsettings.value("geometry", ""))
        self._mw.restoreState(self.mwsettings.value("windowState", ""))

    def update_elapsedtime(self, elapsed_time, scanned_lines):
        """ Updates current elapsed measurement time and completed frequency sweeps """
        self._mw.elapsed_time_DisplayWidget.display(int(np.rint(elapsed_time)))
        self._mw.elapsed_sweeps_DisplayWidget.display(scanned_lines)
        return

    def update_settings(self):
        """ Write the new settings from the gui to the file. """
        number_of_lines = self._sd.matrix_lines_SpinBox.value()
        clock_frequency = self._sd.clock_frequency_DoubleSpinBox.value()
        oversampling = self._sd.oversampling_SpinBox.value()
        lock_in = self._sd.lock_in_CheckBox.isChecked()
        self.sigOversamplingChanged.emit(oversampling)
        self.sigLockInChanged.emit(lock_in)
        self.sigClockFreqChanged.emit(clock_frequency)
        self.sigNumberOfLinesChanged.emit(number_of_lines)
        return

    def reject_settings(self):
        """ Keep the old settings and restores the old settings in the gui. """
        self._sd.matrix_lines_SpinBox.setValue(self._odmr_logic.number_of_lines)
        self._sd.clock_frequency_DoubleSpinBox.setValue(self._odmr_logic.clock_frequency)
        self._sd.oversampling_SpinBox.setValue(self._odmr_logic.oversampling)
        self._sd.lock_in_CheckBox.setChecked(self._odmr_logic.lock_in)
        return

    def do_fit(self):
        fit_function = self._mw.fit_methods_ComboBox.getCurrentFit()[0]
        self.sigDoFit.emit(fit_function, None, None, self._mw.odmr_channel_ComboBox.currentIndex(),
                           self._mw.fit_range_SpinBox.value())
        return

    def update_fit(self, x_data, y_data, result_str_dict, current_fit):
        """ Update the shown fit. """
        if current_fit != 'No Fit':
            # display results as formatted text
            self._mw.odmr_fit_results_DisplayWidget.clear()
            try:
                formated_results = units.create_formatted_output(result_str_dict)
            except:
                formated_results = 'this fit does not return formatted results'
            self._mw.odmr_fit_results_DisplayWidget.setPlainText(formated_results)

        self._mw.fit_methods_ComboBox.blockSignals(True)
        self._mw.fit_methods_ComboBox.setCurrentFit(current_fit)
        self._mw.fit_methods_ComboBox.blockSignals(False)

        # check which Fit method is used and remove or add again the
        # odmr_fit_image, check also whether a odmr_fit_image already exists.
        if current_fit != 'No Fit':
            self.odmr_fit_image.setData(x=x_data, y=y_data)
            if self.odmr_fit_image not in self._mw.odmr_PlotWidget.listDataItems():
                self._mw.odmr_PlotWidget.addItem(self.odmr_fit_image)
        else:
            if self.odmr_fit_image in self._mw.odmr_PlotWidget.listDataItems():
                self._mw.odmr_PlotWidget.removeItem(self.odmr_fit_image)

        self._mw.odmr_PlotWidget.getViewBox().updateAutoRange()
        return

    def update_fit_range(self):
        self._odmr_logic.range_to_fit = self._mw.fit_range_SpinBox.value()
        return

    def update_matrix_range(self):
        self._odmr_logic.matrix_range = self._mw.odmr_control_DockWidget.matrix_range_SpinBox.value()
        # need to update the plot that is showed
        key = 'Matrix range: {}'.format(self._odmr_logic.matrix_range)
        self.odmr_matrix_image.setImage(self._odmr_logic.select_odmr_matrix_data(self._odmr_logic.odmr_plot_xy,
                                                                                 self.display_channel,
                                                                                 self._odmr_logic.matrix_range))
        return

    def update_parameter(self, param_dict):
        """ Update the parameter display in the GUI.

        @param param_dict:
        @return:

        Any change event from the logic should call this update function.
        The update will block the GUI signals from emitting a change back to the
        logic.
        """
        param = param_dict.get('sweep_mw_power')
        if param is not None:
            self._mw.sweep_power_DoubleSpinBox.blockSignals(True)
            self._mw.sweep_power_DoubleSpinBox.setValue(param)
            self._mw.sweep_power_DoubleSpinBox.blockSignals(False)

        mw_starts = param_dict.get('mw_starts')
        mw_steps = param_dict.get('mw_steps')
        mw_stops = param_dict.get('mw_stops')

        if mw_starts is not None:
            start_frequency_boxes = self.get_freq_dspinboxes_from_groubpox('start')
            for mw_start, start_frequency_box in zip(mw_starts, start_frequency_boxes):
                start_frequency_box.blockSignals(True)
                start_frequency_box.setValue(mw_start)
                start_frequency_box.blockSignals(False)

        if mw_steps is not None:
            step_frequency_boxes = self.get_freq_dspinboxes_from_groubpox('step')
            for mw_step, step_frequency_box in zip(mw_steps, step_frequency_boxes):
                step_frequency_box.blockSignals(True)
                step_frequency_box.setValue(mw_step)
                step_frequency_box.blockSignals(False)

        if mw_stops is not None:
            stop_frequency_boxes = self.get_freq_dspinboxes_from_groubpox('stop')
            for mw_stop, stop_frequency_box in zip(mw_stops, stop_frequency_boxes):
                stop_frequency_box.blockSignals(True)
                stop_frequency_box.setValue(mw_stop)
                stop_frequency_box.blockSignals(False)

        param = param_dict.get('run_time')
        if param is not None:
            self._mw.runtime_DoubleSpinBox.blockSignals(True)
            self._mw.runtime_DoubleSpinBox.setValue(param)
            self._mw.runtime_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('number_of_lines')
        if param is not None:
            self._sd.matrix_lines_SpinBox.blockSignals(True)
            self._sd.matrix_lines_SpinBox.setValue(param)
            self._sd.matrix_lines_SpinBox.blockSignals(False)

        param = param_dict.get('clock_frequency')
        if param is not None:
            self._sd.clock_frequency_DoubleSpinBox.blockSignals(True)
            self._sd.clock_frequency_DoubleSpinBox.setValue(param)
            self._sd.clock_frequency_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('oversampling')
        if param is not None:
            self._sd.oversampling_SpinBox.blockSignals(True)
            self._sd.oversampling_SpinBox.setValue(param)
            self._sd.oversampling_SpinBox.blockSignals(False)

        param = param_dict.get('lock_in')
        if param is not None:
            self._sd.lock_in_CheckBox.blockSignals(True)
            self._sd.lock_in_CheckBox.setChecked(param)
            self._sd.lock_in_CheckBox.blockSignals(False)

        param = param_dict.get('cw_mw_frequency')
        if param is not None:
            self._mw.cw_frequency_DoubleSpinBox.blockSignals(True)
            self._mw.cw_frequency_DoubleSpinBox.setValue(param)
            self._mw.cw_frequency_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('cw_mw_power')
        if param is not None:
            self._mw.cw_power_DoubleSpinBox.blockSignals(True)
            self._mw.cw_power_DoubleSpinBox.setValue(param)
            self._mw.cw_power_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('average_length')
        if param is not None:
            self._mw.average_level_SpinBox.blockSignals(True)
            self._mw.average_level_SpinBox.setValue(param)
            self._mw.average_level_SpinBox.blockSignals(False)
        return

    ############################################################################
    #                           Change Methods                                 #
    ############################################################################

    def change_cw_params(self):
        """ Change CW frequency and power of microwave source """
        frequency = self._mw.cw_frequency_DoubleSpinBox.value()
        power = self._mw.cw_power_DoubleSpinBox.value()
        self.sigMwCwParamsChanged.emit(frequency, power)
        return

    def change_sweep_params(self):
        """ Change start, stop and step frequency of frequency sweep """
        starts = []
        steps = []
        stops = []

        num = self._odmr_logic.ranges

        for counter in range(num):
            # construct strings
            start, stop, step = self.get_frequencies_from_row(counter)

            starts.append(start)
            steps.append(step)
            stops.append(stop)

        power = self._mw.sweep_power_DoubleSpinBox.value()
        self.sigMwSweepParamsChanged.emit(starts, stops, steps, power)
        return

    def change_fit_range(self):
        self._odmr_logic.fit_range = self._mw.fit_range_SpinBox.value()
        return

    def get_frequencies_from_row(self, row):
        object_dict = self.get_objects_from_groupbox_row(row)
        for object_name in object_dict:
            if "DoubleSpinBox" in object_name:
                if "start" in object_name:
                    start = object_dict[object_name].value()
                elif "step" in object_name:
                    step = object_dict[object_name].value()
                elif "stop" in object_name:
                    stop = object_dict[object_name].value()

        return start, stop, step

    def change_runtime(self):
        """ Change time after which microwave sweep is stopped """
        runtime = self._mw.runtime_DoubleSpinBox.value()
        self.sigRuntimeChanged.emit(runtime)
        return

    def save_data(self):
        """ Save the sum plot, the scan marix plot and the scan data """
        filetag = self._mw.save_tag_LineEdit.text()
        cb_range = self.get_matrix_cb_range()

        # Percentile range is None, unless the percentile scaling is selected in GUI.
        pcile_range = None
        if self._mw.odmr_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.odmr_cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.odmr_cb_high_percentile_DoubleSpinBox.value()
            pcile_range = [low_centile, high_centile]

        self.sigSaveMeasurement.emit(filetag, cb_range, pcile_range)
        return
