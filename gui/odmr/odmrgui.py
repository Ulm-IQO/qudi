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

from core.module import Connector
from core.util import units
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from gui.colordefs import ColorScaleInferno
from gui.colordefs import QudiPalettePale as palette
from gui.fitsettings import FitSettingsDialog, FitSettingsComboBox
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic


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

    _modclass = 'ODMRGui'
    _modtype = 'gui'

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
    sigMwSweepParamsChanged = QtCore.Signal(float, float, float, float)
    sigClockFreqChanged = QtCore.Signal(float)
    sigFitChanged = QtCore.Signal(str)
    sigNumberOfLinesChanged = QtCore.Signal(int)
    sigRuntimeChanged = QtCore.Signal(float)
    sigDoFit = QtCore.Signal(str)
    sigSaveMeasurement = QtCore.Signal(str, list, list)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition, configuration and initialisation of the ODMR GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """

        self._odmr_logic = self.get_connector('odmrlogic1')

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
        self._mw.start_freq_DoubleSpinBox.setMaximum(constraints.max_frequency)
        self._mw.start_freq_DoubleSpinBox.setMinimum(constraints.min_frequency)
        self._mw.step_freq_DoubleSpinBox.setMaximum(100e9)
        self._mw.step_freq_DoubleSpinBox.setOpts(minStep=1.0)  # set the minimal step to 1Hz
        self._mw.stop_freq_DoubleSpinBox.setMaximum(constraints.max_frequency)
        self._mw.stop_freq_DoubleSpinBox.setMinimum(constraints.min_frequency)
        self._mw.cw_power_DoubleSpinBox.setMaximum(constraints.max_power)
        self._mw.cw_power_DoubleSpinBox.setMinimum(constraints.min_power)
        self._mw.cw_power_DoubleSpinBox.setOpts(minStep=0.1)
        self._mw.sweep_power_DoubleSpinBox.setMaximum(constraints.max_power)
        self._mw.sweep_power_DoubleSpinBox.setMinimum(constraints.min_power)
        self._mw.sweep_power_DoubleSpinBox.setOpts(minStep=0.1)

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

        # Get the image from the logic
        self.odmr_matrix_image = pg.ImageItem(self._odmr_logic.odmr_plot_xy, axisOrder='row-major')
        self.odmr_matrix_image.setRect(QtCore.QRectF(
                self._odmr_logic.mw_start,
                0,
                self._odmr_logic.mw_stop - self._odmr_logic.mw_start,
                self._odmr_logic.number_of_lines
            ))

        self.odmr_image = pg.PlotDataItem(self._odmr_logic.odmr_plot_x,
                                          self._odmr_logic.odmr_plot_y,
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
        self._mw.start_freq_DoubleSpinBox.setValue(self._odmr_logic.mw_start)
        self._mw.stop_freq_DoubleSpinBox.setValue(self._odmr_logic.mw_stop)
        self._mw.step_freq_DoubleSpinBox.setValue(self._odmr_logic.mw_step)
        self._mw.cw_power_DoubleSpinBox.setValue(self._odmr_logic.cw_mw_power)
        self._mw.sweep_power_DoubleSpinBox.setValue(self._odmr_logic.sweep_mw_power)

        self._mw.runtime_DoubleSpinBox.setValue(self._odmr_logic.run_time)
        self._mw.elapsed_time_DisplayWidget.display(int(np.rint(self._odmr_logic.elapsed_time)))
        self._mw.elapsed_sweeps_DisplayWidget.display(self._odmr_logic.elapsed_sweeps)

        self._sd.matrix_lines_SpinBox.setValue(self._odmr_logic.number_of_lines)
        self._sd.clock_frequency_DoubleSpinBox.setValue(self._odmr_logic.clock_frequency)

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
        self._mw.start_freq_DoubleSpinBox.editingFinished.connect(self.change_sweep_params)
        self._mw.step_freq_DoubleSpinBox.editingFinished.connect(self.change_sweep_params)
        self._mw.stop_freq_DoubleSpinBox.editingFinished.connect(self.change_sweep_params)
        self._mw.sweep_power_DoubleSpinBox.editingFinished.connect(self.change_sweep_params)
        self._mw.cw_power_DoubleSpinBox.editingFinished.connect(self.change_cw_params)
        self._mw.runtime_DoubleSpinBox.editingFinished.connect(self.change_runtime)
        self._mw.odmr_cb_max_DoubleSpinBox.valueChanged.connect(self.colorscale_changed)
        self._mw.odmr_cb_min_DoubleSpinBox.valueChanged.connect(self.colorscale_changed)
        self._mw.odmr_cb_high_percentile_DoubleSpinBox.valueChanged.connect(self.colorscale_changed)
        self._mw.odmr_cb_low_percentile_DoubleSpinBox.valueChanged.connect(self.colorscale_changed)
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
        self.sigSaveMeasurement.connect(self._odmr_logic.save_odmr_data, QtCore.Qt.QueuedConnection)

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
        self.sigSaveMeasurement.disconnect()
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
        self._mw.start_freq_DoubleSpinBox.editingFinished.disconnect()
        self._mw.step_freq_DoubleSpinBox.editingFinished.disconnect()
        self._mw.stop_freq_DoubleSpinBox.editingFinished.disconnect()
        self._mw.cw_power_DoubleSpinBox.editingFinished.disconnect()
        self._mw.sweep_power_DoubleSpinBox.editingFinished.disconnect()
        self._mw.runtime_DoubleSpinBox.editingFinished.disconnect()
        self._mw.odmr_cb_max_DoubleSpinBox.valueChanged.disconnect()
        self._mw.odmr_cb_min_DoubleSpinBox.valueChanged.disconnect()
        self._mw.odmr_cb_high_percentile_DoubleSpinBox.valueChanged.disconnect()
        self._mw.odmr_cb_low_percentile_DoubleSpinBox.valueChanged.disconnect()
        self._fsd.sigFitsUpdated.disconnect()
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
            self._mw.start_freq_DoubleSpinBox.setEnabled(False)
            self._mw.step_freq_DoubleSpinBox.setEnabled(False)
            self._mw.stop_freq_DoubleSpinBox.setEnabled(False)
            self._mw.runtime_DoubleSpinBox.setEnabled(False)
            self._sd.clock_frequency_DoubleSpinBox.setEnabled(False)
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
            self._mw.start_freq_DoubleSpinBox.setEnabled(False)
            self._mw.step_freq_DoubleSpinBox.setEnabled(False)
            self._mw.stop_freq_DoubleSpinBox.setEnabled(False)
            self._mw.runtime_DoubleSpinBox.setEnabled(False)
            self._sd.clock_frequency_DoubleSpinBox.setEnabled(False)
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
                self._mw.start_freq_DoubleSpinBox.setEnabled(False)
                self._mw.step_freq_DoubleSpinBox.setEnabled(False)
                self._mw.stop_freq_DoubleSpinBox.setEnabled(False)
                self._mw.sweep_power_DoubleSpinBox.setEnabled(False)
                self._mw.runtime_DoubleSpinBox.setEnabled(False)
                self._sd.clock_frequency_DoubleSpinBox.setEnabled(False)
                self._mw.action_run_stop.setChecked(True)
                self._mw.action_resume_odmr.setChecked(True)
                self._mw.action_toggle_cw.setChecked(False)
            else:
                self._mw.clear_odmr_PushButton.setEnabled(False)
                self._mw.action_run_stop.setEnabled(False)
                self._mw.action_toggle_cw.setEnabled(True)
                self._mw.start_freq_DoubleSpinBox.setEnabled(True)
                self._mw.step_freq_DoubleSpinBox.setEnabled(True)
                self._mw.stop_freq_DoubleSpinBox.setEnabled(True)
                self._mw.sweep_power_DoubleSpinBox.setEnabled(True)
                self._mw.runtime_DoubleSpinBox.setEnabled(True)
                self._sd.clock_frequency_DoubleSpinBox.setEnabled(True)
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
            self._mw.start_freq_DoubleSpinBox.setEnabled(True)
            self._mw.step_freq_DoubleSpinBox.setEnabled(True)
            self._mw.stop_freq_DoubleSpinBox.setEnabled(True)
            self._mw.runtime_DoubleSpinBox.setEnabled(True)
            self._sd.clock_frequency_DoubleSpinBox.setEnabled(True)
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
        self.odmr_image.setData(odmr_data_x, odmr_data_y)
        # Update raw data matrix plot
        cb_range = self.get_matrix_cb_range()
        self.update_colorbar(cb_range)
        self.odmr_matrix_image.setRect(
            QtCore.QRectF(
                odmr_data_x[0],
                0,
                np.abs(odmr_data_x[-1] - odmr_data_x[0]),
                odmr_matrix.shape[0])
            )
        self.odmr_matrix_image.setImage(
            image=odmr_matrix,
            axisOrder='row-major',
            levels=(cb_range[0], cb_range[1]))

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
        if self._mw.odmr_cb_manual_RadioButton.isChecked() or np.max(matrix_image) < 0.1:
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
        self.sigClockFreqChanged.emit(clock_frequency)
        self.sigNumberOfLinesChanged.emit(number_of_lines)
        return

    def reject_settings(self):
        """ Keep the old settings and restores the old settings in the gui. """
        self._sd.matrix_lines_SpinBox.setValue(self._odmr_logic.number_of_lines)
        self._sd.clock_frequency_DoubleSpinBox.setValue(self._odmr_logic.clock_frequency)
        return

    def do_fit(self):
        fit_function  = self._mw.fit_methods_ComboBox.getCurrentFit()[0]
        self.sigDoFit.emit(fit_function)
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

    def update_parameter(self, param_dict):
        """ Update the parameter display in the GUI.

        @param param_dict:
        @return:

        Any change event from the logic should call this update function.
        The update will block the GUI signals from emitting a change back to the
        logic.
        """
        param = param_dict.get('mw_power')
        if param is not None:
            self._mw.power_DoubleSpinBox.blockSignals(True)
            self._mw.power_DoubleSpinBox.setValue(param)
            self._mw.power_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('mw_frequency')
        if param is not None:
            self._mw.frequency_DoubleSpinBox.blockSignals(True)
            self._mw.frequency_DoubleSpinBox.setValue(param)
            self._mw.frequency_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('mw_start')
        if param is not None:
            self._mw.start_freq_DoubleSpinBox.blockSignals(True)
            self._mw.start_freq_DoubleSpinBox.setValue(param)
            self._mw.start_freq_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('mw_step')
        if param is not None:
            self._mw.step_freq_DoubleSpinBox.blockSignals(True)
            self._mw.step_freq_DoubleSpinBox.setValue(param)
            self._mw.step_freq_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('mw_stop')
        if param is not None:
            self._mw.stop_freq_DoubleSpinBox.blockSignals(True)
            self._mw.stop_freq_DoubleSpinBox.setValue(param)
            self._mw.stop_freq_DoubleSpinBox.blockSignals(False)

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
        start = self._mw.start_freq_DoubleSpinBox.value()
        stop = self._mw.stop_freq_DoubleSpinBox.value()
        step = self._mw.step_freq_DoubleSpinBox.value()
        power = self._mw.sweep_power_DoubleSpinBox.value()
        self.sigMwSweepParamsChanged.emit(start, stop, step, power)
        return

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
