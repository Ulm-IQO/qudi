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


from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic
import pyqtgraph as pg
import numpy as np
import os

from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from gui.colordefs import ColorScaleInferno
from gui.colordefs import QudiPalettePale as palette
from gui.fitsettings import FitSettingsDialog, FitSettingsComboBox
from core.util import units


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
    _connectors = {'odmrlogic1': 'ODMRLogic',
           'savelogic': 'SaveLogic'}

    sigStartODMRScan = QtCore.Signal()
    sigStopODMRScan = QtCore.Signal()
    sigContinueODMRScan = QtCore.Signal()
    sigClearPlots = QtCore.Signal()
    sigMWOn = QtCore.Signal()
    sigMWOff = QtCore.Signal()
    sigMWPowerChanged = QtCore.Signal(float)
    sigMWFreqChanged = QtCore.Signal(float)
    sigFitChanged = QtCore.Signal(str)
    sigDoFit = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))

    def on_activate(self):
        """ Definition, configuration and initialisation of the ODMR GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """

        self._odmr_logic = self.get_connector('odmrlogic1')
        self._save_logic = self.get_connector('savelogic')

        # Use the inherited class 'Ui_ODMRGuiUI' to create now the
        # GUI element:
        self._mw = ODMRMainWindow()
        self._sd = ODMRSettingDialog()

        # Create a QSettings object for the mainwindow and store the actual GUI layout
        self.mwsettings = QtCore.QSettings("QUDI", "ODMR")
        self.mwsettings.setValue("geometry", self._mw.saveGeometry())
        self.mwsettings.setValue("windowState", self._mw.saveState())

        # Adjust range of scientific spinboxes above what is possible in Qt Designer
        self._mw.frequency_DoubleSpinBox.setMaximum(self._odmr_logic.limits.max_frequency)
        self._mw.frequency_DoubleSpinBox.setMinimum(self._odmr_logic.limits.min_frequency)
        self._mw.start_freq_DoubleSpinBox.setMaximum(self._odmr_logic.limits.max_frequency)
        self._mw.start_freq_DoubleSpinBox.setMinimum(self._odmr_logic.limits.min_frequency)
        self._mw.step_freq_DoubleSpinBox.setMaximum(100e9)
        self._mw.stop_freq_DoubleSpinBox.setMaximum(self._odmr_logic.limits.max_frequency)
        self._mw.stop_freq_DoubleSpinBox.setMinimum(self._odmr_logic.limits.min_frequency)
        self._mw.power_DoubleSpinBox.setMaximum(self._odmr_logic.limits.max_power)
        self._mw.power_DoubleSpinBox.setMinimum(self._odmr_logic.limits.min_power)

        # connect the parameter update events:
        self._odmr_logic.sigParameterChanged.connect(self.update_parameter)

        # Add save file tag input box
        self._mw.save_tag_LineEdit = QtWidgets.QLineEdit(self._mw)
        self._mw.save_tag_LineEdit.setMaximumWidth(200)
        self._mw.save_tag_LineEdit.setToolTip(
            'Enter a nametag which will be\nadded to the filename.')
        self._mw.save_ToolBar.addWidget(self._mw.save_tag_LineEdit)

        # add a clear button to clear the ODMR plots:
        self._mw.clear_odmr_PushButton = QtWidgets.QPushButton(self._mw)
        self._mw.clear_odmr_PushButton.setText('Clear ODMR')
        self._mw.clear_odmr_PushButton.setToolTip(
            'Clear the plots of the\ncurrent ODMR measurements.')
        self._mw.clear_odmr_PushButton.setEnabled(False)
        self._mw.save_ToolBar.addWidget(self._mw.clear_odmr_PushButton)
        self.sigClearPlots.connect(self._odmr_logic.clear_odmr_plots)

        # Get the image from the logic
        self.odmr_matrix_image = pg.ImageItem(self._odmr_logic.ODMR_plot_xy.transpose())
        self.odmr_matrix_image.setRect(
            QtCore.QRectF(
                self._odmr_logic.mw_start,
                0,
                self._odmr_logic.mw_stop - self._odmr_logic.mw_start,
                self._odmr_logic.number_of_lines
            ))

        self.odmr_image = pg.PlotDataItem(
            self._odmr_logic.ODMR_plot_x,
            self._odmr_logic.ODMR_plot_y,
            pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
            symbol='o',
            symbolPen=palette.c1,
            symbolBrush=palette.c1,
            symbolSize=7
        )

        self.odmr_fit_image = pg.PlotDataItem(
            self._odmr_logic.ODMR_fit_x,
            self._odmr_logic.ODMR_fit_y,
            pen=pg.mkPen(palette.c2)
        )

        # Add the display item to the xy and xz VieWidget, which was defined in
        # the UI file.
        self._mw.odmr_PlotWidget.addItem(self.odmr_image)
        self._mw.odmr_PlotWidget.setLabel(axis='left', text='Counts',
                                          units='Counts/s')
        self._mw.odmr_PlotWidget.setLabel(axis='bottom', text='Frequency',
                                          units='Hz')

        self._mw.odmr_matrix_PlotWidget.addItem(self.odmr_matrix_image)
        self._mw.odmr_matrix_PlotWidget.setLabel(axis='left',
                                                 text='Matrix Lines',
                                                 units='#')
        self._mw.odmr_matrix_PlotWidget.setLabel(axis='bottom', text='Frequency',
                                                 units='Hz')

        self._mw.odmr_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        # Get the colorscales at set LUT
        my_colors = ColorScaleInferno()
        self.odmr_matrix_image.setLookupTable(my_colors.lut)

        # Configuration of the microwave mode comboWidget
        self._mw.mode_ComboBox.addItem('Off')
        self._mw.mode_ComboBox.addItem('CW')

        ########################################################################
        #                  Configuration of the Colorbar                       #
        ########################################################################

        self.odmr_cb = ColorBar(my_colors.cmap_normed, 100, 0, 100000)

        # adding colorbar to ViewWidget
        self._mw.odmr_cb_PlotWidget.addItem(self.odmr_cb)
        self._mw.odmr_cb_PlotWidget.hideAxis('bottom')
        self._mw.odmr_cb_PlotWidget.hideAxis('left')
        self._mw.odmr_cb_PlotWidget.setLabel('right', 'Fluorescence', units='counts/s')

        # Connect the buttons and inputs for the odmr colorbar
        self._mw.odmr_cb_manual_RadioButton.clicked.connect(self.refresh_matrix)
        self._mw.odmr_cb_centiles_RadioButton.clicked.connect(self.refresh_matrix)

        ########################################################################
        #          Configuration of the various display Widgets                #
        ########################################################################

        # Take the default values from logic:
        self._mw.frequency_DoubleSpinBox.setValue(self._odmr_logic.mw_frequency)
        self._mw.start_freq_DoubleSpinBox.setValue(self._odmr_logic.mw_start)

        self._mw.step_freq_DoubleSpinBox.setValue(self._odmr_logic.mw_step)
        self._mw.step_freq_DoubleSpinBox.setOpts(minStep=1.0)  # set the minimal step to 1Hz.

        self._mw.stop_freq_DoubleSpinBox.setValue(self._odmr_logic.mw_stop)

        self._mw.power_DoubleSpinBox.setValue(self._odmr_logic.mw_power)
        self._mw.power_DoubleSpinBox.setOpts(minStep=0.1)

        self._mw.runtime_DoubleSpinBox.setValue(self._odmr_logic.run_time)
        self._mw.elapsed_time_DisplayWidget.display(int(self._odmr_logic.elapsed_time))

        self._sd.matrix_lines_SpinBox.setValue(self._odmr_logic.number_of_lines)
        self._sd.clock_frequency_DoubleSpinBox.setValue(self._odmr_logic._clock_frequency)

        # fit settings
        self._fsd = FitSettingsDialog(self._odmr_logic.fc)
        self._fsd.sigFitsUpdated.connect(self._mw.fit_methods_ComboBox.setFitFunctions)
        self._fsd.applySettings()

        self._mw.action_FitSettings.triggered.connect(self._fsd.show)
        self.sigDoFit.connect(self._odmr_logic.do_fit)
        self.sigFitChanged.connect(self._odmr_logic.fc.set_current_fit)
        self._odmr_logic.sigOdmrFitUpdated.connect(self.update_fit_display)

        # Update the inputed/displayed numbers if return key is hit:

        # If the attribute setKeyboardTracking is set in a SpinBox or
        # DoubleSpinBox the valueChanged method will actually hold on the signal
        #  until the return key is pressed which is pretty useful ;)

        # self._mw.frequency_DoubleSpinBox.setKeyboardTracking(False)

        # Update the inputed/displayed numbers if the cursor has left the field:

        self._mw.frequency_DoubleSpinBox.editingFinished.connect(self.change_frequency)
        self._mw.start_freq_DoubleSpinBox.editingFinished.connect(self.change_start_freq)
        self._mw.step_freq_DoubleSpinBox.editingFinished.connect(self.change_step_freq)
        self._mw.stop_freq_DoubleSpinBox.editingFinished.connect(self.change_stop_freq)
        self._mw.power_DoubleSpinBox.editingFinished.connect(self.change_power)
        self._mw.runtime_DoubleSpinBox.editingFinished.connect(self.change_runtime)

        self._mw.odmr_cb_max_DoubleSpinBox.valueChanged.connect(self.refresh_matrix)
        self._mw.odmr_cb_min_DoubleSpinBox.valueChanged.connect(self.refresh_matrix)
        self._mw.odmr_cb_high_percentile_DoubleSpinBox.valueChanged.connect(self.refresh_matrix)
        self._mw.odmr_cb_low_percentile_DoubleSpinBox.valueChanged.connect(self.refresh_matrix)

        ########################################################################
        #                       Connect signals                                #
        ########################################################################

        # Connect the RadioButtons and connect to the events if they are clicked:
        self._mw.action_run_stop.triggered.connect(self.run_stop)
        self._mw.action_resume_odmr.triggered.connect(self.resume_odmr)
        self._mw.action_Save.triggered.connect(self.save_data)
        self._mw.action_RestoreDefault.triggered.connect(self.restore_defaultview)
        self.sigStartODMRScan.connect(self._odmr_logic.start_odmr_scan)
        self.sigStopODMRScan.connect(self._odmr_logic.stop_odmr_scan)
        self.sigContinueODMRScan.connect(self._odmr_logic.continue_odmr_scan)

        self.sigMWOn.connect(self._odmr_logic.MW_on)
        self.sigMWOff.connect(self._odmr_logic.MW_off)
        self.sigMWFreqChanged.connect(self._odmr_logic.set_frequency)
        self.sigMWPowerChanged.connect(self._odmr_logic.set_power)

        # react on an axis change in the logic by adapting the display:
        self._odmr_logic.sigODMRMatrixAxesChanged.connect(self.update_matrix_axes)

        # connect the clear button:
        self._mw.clear_odmr_PushButton.clicked.connect(self.clear_odmr_plots_clicked)

        self._odmr_logic.sigOdmrPlotUpdated.connect(self.refresh_plot)
        self._odmr_logic.sigOdmrMatrixUpdated.connect(self.refresh_matrix)
        self._odmr_logic.sigOdmrElapsedTimeChanged.connect(self.refresh_elapsedtime)
        # connect settings signals
        self._mw.action_Settings.triggered.connect(self.menu_settings)
        self._sd.accepted.connect(self.update_settings)
        self._sd.rejected.connect(self.reject_settings)
        self._sd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.update_settings)
        self.reject_settings()
        # Connect stop odmr
        self._odmr_logic.sigOdmrStarted.connect(self.odmr_started)
        self._odmr_logic.sigOdmrStopped.connect(self.odmr_stopped)
        # Combo Widget
        self._mw.mode_ComboBox.activated[str].connect(self.mw_stop)
        # Push Buttons
        self._mw.do_fit_PushButton.clicked.connect(self.do_fit)

        # let the gui react on the signals from the GUI
        self._odmr_logic.sigMicrowaveCWModeChanged.connect(self.update_cw_display)
        self._odmr_logic.sigMicrowaveListModeChanged.connect(self.update_run_stop_display)

        # Show the Main ODMR GUI:
        self._mw.show()

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        self._mw.close()
        return 0

    def show(self):
        """Make window visible and put it above all other windows. """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def run_stop(self, is_checked):
        """ Manages what happens if odmr scan is started/stopped. """
        if is_checked:
            # change the axes appearance according to input values:
            self.sigStopODMRScan.emit()
            self.sigStartODMRScan.emit()
            self._mw.action_run_stop.setEnabled(False)
            self._mw.action_resume_odmr.setEnabled(False)
            self._mw.odmr_PlotWidget.removeItem(self.odmr_fit_image)

            # during scan, enable the clear plot possibility.
            self._mw.clear_odmr_PushButton.setEnabled(True)
        else:
            self.sigStopODMRScan.emit()
            self._mw.action_run_stop.setEnabled(False)
            self._mw.action_resume_odmr.setEnabled(False)
            # Disable the clear functionality since that is not needed if no
            # scan is running:
            self._mw.clear_odmr_PushButton.setEnabled(False)

    def update_cw_display(self, cw_on):
        """ Update the display for the cw state of the microwave.

        @param bool cw_on: for True the mw on display will be shown, otherwise
                           mw off will be displayed.
        """
        if cw_on:
            # # prevent any triggering, which results from changing the state of
            # # the combobox:
            # self._mw.mode_ComboBox.blockSignals(True)
            text = 'CW'
        else:
            text = 'Off'

        index = self._mw.mode_ComboBox.findText(text, QtCore.Qt.MatchFixedString)
        if index >= 0:
            self._mw.mode_ComboBox.setCurrentIndex(index)
        else:
            self.log.warning('No proper state to display was found in the combobox!')

    def update_run_stop_display(self, run_odmr):
        """ Update the display for the odmr measurement.

        @param bool run_odmr: True indicates that the measurement is running and
                              False that it is stopped.
        """
        if run_odmr:
            self._mw.action_resume_odmr.setEnabled(False)
            self._mw.clear_odmr_PushButton.setEnabled(True)
        else:
            self._mw.action_resume_odmr.setEnabled(True)
            self._mw.clear_odmr_PushButton.setEnabled(False)

    def resume_odmr(self, is_checked):
        if is_checked:
            self.sigStopODMRScan.emit()
            self.sigContinueODMRScan.emit()
            self._mw.action_run_stop.setChecked(True)
            self._mw.action_run_stop.setEnabled(False)
            self._mw.action_resume_odmr.setEnabled(False)

            # during scan, enable the clear plot possibility.
            self._mw.clear_odmr_PushButton.setEnabled(True)
        else:
            self.sigStopODMRScan.emit()
            self._mw.action_run_stop.setChecked(False)
            self._mw.action_run_stop.setEnabled(True)
            self._mw.action_resume_odmr.setEnabled(True)
            # Disable the clear functionality since that is not needed if no scan is running:
            self._mw.clear_odmr_PushButton.setEnabled(False)

    def odmr_started(self):
        """ Switch the run/stop button to stop after receiving an odmsStarted
                    signal """
        if not self._mw.action_run_stop.isChecked():
            self._mw.action_run_stop.blockSignals(True)
            self._mw.action_run_stop.setChecked(True)
            self._mw.action_run_stop.blockSignals(False)
        self._mw.action_run_stop.setEnabled(True)

        if not self._mw.action_resume_odmr.isChecked():
            self._mw.action_resume_odmr.blockSignals(True)
            self._mw.action_resume_odmr.setChecked(True)
            self._mw.action_resume_odmr.blockSignals(False)
        self._mw.action_resume_odmr.setEnabled(False)

    def odmr_stopped(self):
        """ Switch the run/stop button to stop after receiving an odmr_stoped
            signal """
        self._mw.action_run_stop.setChecked(False)
        self._mw.action_resume_odmr.setChecked(False)
        self._mw.action_run_stop.setEnabled(True)
        self._mw.action_resume_odmr.setEnabled(True)

    def clear_odmr_plots_clicked(self):
        """ Clear the ODMR plots. """
        self.sigClearPlots.emit()

    def menu_settings(self):
        """ Open the settings menu """
        self._sd.exec_()

    def refresh_plot(self):
        """ Refresh the xy-plot image """
        self.odmr_image.setData(
            self._odmr_logic.ODMR_plot_x,
            self._odmr_logic.ODMR_plot_y)

    def refresh_matrix(self):
        """ Refresh the xy-matrix image """
        odmr_image_data = self._odmr_logic.ODMR_plot_xy.transpose()

        cb_range = self.get_matrix_cb_range()

        # Now update image with new color scale, and update colorbar
        self.odmr_matrix_image.setImage(image=odmr_image_data,
                                        levels=(cb_range[0], cb_range[1])
                                        )
        self.refresh_odmr_colorbar()

    def update_matrix_axes(self):
        """ Adjust the x and y axes in the image according to the input. """

        self.odmr_matrix_image.setRect(
            QtCore.QRectF(
                self._odmr_logic.mw_start,
                0,
                self._odmr_logic.mw_stop - self._odmr_logic.mw_start,
                self._odmr_logic.number_of_lines
            ))

    def refresh_odmr_colorbar(self):
        """ Update the colorbar to a new scaling.

        Calls the refresh method from colorbar.
        """
        cb_range = self.get_matrix_cb_range()
        self.odmr_cb.refresh_colorbar(cb_range[0], cb_range[1])

        self._mw.odmr_cb_PlotWidget.update()  # TODO: Is this necessary?  It is not in refresh_xy_colorbar in confocal gui

    def get_matrix_cb_range(self):
        """ Determines the cb_min and cb_max values for the matrix plot
        """
        matrix_image = self.odmr_matrix_image.image

        # If "Manual" is checked or the image is empty (all zeros), then take manual cb range.
        if self._mw.odmr_cb_manual_RadioButton.isChecked() or np.max(matrix_image) == 0.0:
            cb_min = self._mw.odmr_cb_min_DoubleSpinBox.value()
            cb_max = self._mw.odmr_cb_max_DoubleSpinBox.value()

        # Otherwise, calculate cb range from percentiles.
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

    def refresh_elapsedtime(self):
        """ Show current elapsed measurement time """
        self._mw.elapsed_time_DisplayWidget.display(int(self._odmr_logic.elapsed_time))

    def update_settings(self):
        """ Write the new settings from the gui to the file. """
        self._odmr_logic.number_of_lines = self._sd.matrix_lines_SpinBox.value()
        self._odmr_logic.set_clock_frequency(self._sd.clock_frequency_DoubleSpinBox.value())
        self._odmr_logic.saveRawData = self._sd.save_raw_data_CheckBox.isChecked()

    def reject_settings(self):
        """ Keep the old settings and restores the old settings in the gui. """
        self._sd.matrix_lines_SpinBox.setValue(self._odmr_logic.number_of_lines)
        self._sd.clock_frequency_DoubleSpinBox.setValue(self._odmr_logic._clock_frequency)
        self._sd.save_raw_data_CheckBox.setChecked(self._odmr_logic.saveRawData)

    def do_fit(self):
        self.sigFitChanged.emit(self._mw.fit_methods_ComboBox.getCurrentFit()[0])
        self.sigDoFit.emit()

    def update_fit_display(self):
        """ Do the configured fit and show it in the sum plot """
        fit_name = self._odmr_logic.fc.current_fit
        fit_result = self._odmr_logic.fc.current_fit_result
        fit_param = self._odmr_logic.fc.current_fit_param

        if fit_result is not None:
            # display results as formatted text
            self._mw.odmr_fit_results_DisplayWidget.clear()
            try:
                formated_results = units.create_formatted_output(fit_result.result_str_dict)
            except:
                formated_results = 'this fit does not return formatted results'
            self._mw.odmr_fit_results_DisplayWidget.setPlainText(formated_results)

        if fit_name is not None:
            self._mw.fit_methods_ComboBox.setCurrentFit(fit_name)

        # check which Fit method is used and remove or add again the
        # odmr_fit_image, check also whether a odmr_fit_image already exists.
        if fit_name != 'No Fit':
            self.odmr_fit_image.setData(
                x=self._odmr_logic.ODMR_fit_x,
                y=self._odmr_logic.ODMR_fit_y)
            if self.odmr_fit_image not in self._mw.odmr_PlotWidget.listDataItems():
                self._mw.odmr_PlotWidget.addItem(self.odmr_fit_image)
        else:
            if self.odmr_fit_image in self._mw.odmr_PlotWidget.listDataItems():
                self._mw.odmr_PlotWidget.removeItem(self.odmr_fit_image)

        self._mw.odmr_PlotWidget.getViewBox().updateAutoRange()

    def update_parameter(self, param_dict=None):
        """ Update the parameter display in the GUI.

        @param param_dict:
        @return:

        Any change event from the logic should call this update function.
        The update will block the GUI signals from emiting a change back to the
        logic.
        """

        if param_dict is None:
            return

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

    def mw_stop(self, txt):
        """ Stop frequency sweep and change to CW of off"""
        if txt == 'Off':
            self.sigMWOff.emit()
        if txt == 'CW':
            self.change_frequency()
            self.change_power()
            self.sigMWOn.emit()

    ############################################################################
    #                           Change Methods                                 #
    ############################################################################

    def change_frequency(self):
        """ Change CW frequency of microwave source """
        frequency = self._mw.frequency_DoubleSpinBox.value()
        self.sigMWFreqChanged.emit(frequency)

    def change_start_freq(self):
        """ Change start frequency of frequency sweep """
        self._odmr_logic.mw_start = self._mw.start_freq_DoubleSpinBox.value()

    def change_step_freq(self):
        """ Change step size in which frequency is changed """
        self._odmr_logic.mw_step = self._mw.step_freq_DoubleSpinBox.value()

    def change_stop_freq(self):
        """ Change end of frequency sweep """
        self._odmr_logic.mw_stop = self._mw.stop_freq_DoubleSpinBox.value()

    def change_power(self):
        """ Change microwave power """
        power = self._mw.power_DoubleSpinBox.value()
        self.sigMWPowerChanged.emit(power)

    def change_runtime(self):
        """ Change time after which microwave sweep is stopped """
        self._odmr_logic.run_time = self._mw.runtime_DoubleSpinBox.value()

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

        self._odmr_logic.save_ODMR_Data(filetag, colorscale_range=cb_range, percentile_range=pcile_range)

    def restore_defaultview(self):
        self._mw.restoreGeometry(self.mwsettings.value("geometry", ""))
        self._mw.restoreState(self.mwsettings.value("windowState", ""))
