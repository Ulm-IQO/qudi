# -*- coding: utf-8 -*-
"""
This file contains the QuDi GUI module for ODMR control.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""


from pyqtgraph.Qt import QtCore, QtGui, uic
import pyqtgraph as pg
import pyqtgraph.exporters
import numpy as np
import datetime
import os
from collections import OrderedDict
import copy

from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from gui.colordefs import ColorScaleInferno
from gui.colordefs import QudiPalettePale as palette
from gui.fitsettings import FitSettingsWidget
from core.util import units

class ODMRMainWindow(QtGui.QMainWindow):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_odmrgui.ui')

        # Load it
        super(ODMRMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

class ODMRSettingDialog(QtGui.QDialog):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_odmr_settings.ui')

        # Load it
        super(ODMRSettingDialog, self).__init__()
        uic.loadUi(ui_file, self)

class ODMRGui(GUIBase):
    """
    This is the GUI Class for ODMR
    """

    _modclass = 'ODMRGui'
    _modtype = 'gui'

    # declare connectors
    _in = {'odmrlogic1': 'ODMRLogic',
           'savelogic': 'SaveLogic'}

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.initUI, 'ondeactivate':self.deactivation}
        super().__init__(manager, name, config, c_dict)

        self.logMsg('The following configuration was found.', msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), msgType='status')

    def initUI(self, e=None):
        """ Definition, configuration and initialisation of the ODMR GUI.

        @param object e: Fysom.event object from Fysom class.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """

        self._odmr_logic = self.connector['in']['odmrlogic1']['object']
        self._save_logic = self.connector['in']['savelogic']['object']

        # Use the inherited class 'Ui_ODMRGuiUI' to create now the
        # GUI element:
        self._mw = ODMRMainWindow()
        self._sd = ODMRSettingDialog()

        # Add save file tag input box
        self._mw.save_tag_LineEdit = QtGui.QLineEdit(self._mw)
        self._mw.save_tag_LineEdit.setMaximumWidth(200)
        self._mw.save_tag_LineEdit.setToolTip('Enter a nametag which will be\n'
                                              'added to the filename.')
        self._mw.save_ToolBar.addWidget(self._mw.save_tag_LineEdit)

        # add a clear button to clear the ODMR plots:
        self._mw.clear_odmr_PushButton = QtGui.QPushButton(self._mw)

        self._mw.clear_odmr_PushButton.setText('Clear ODMR')
        self._mw.clear_odmr_PushButton.setToolTip('Clear the plots of the\n'
                                                    'current ODMR measurements.')
        self._mw.clear_odmr_PushButton.setEnabled(False)
        self._mw.save_ToolBar.addWidget(self._mw.clear_odmr_PushButton)

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

        # set the prefix, which determines the representation in the viewboxes
        # for the frequencies,  one can choose from the dict obtainable from
        # units.get_unit_prefix_dict():
        self._freq_prefix = 'M'

        # Add the display item to the xy and xz VieWidget, which was defined in
        # the UI file.
        self._mw.odmr_PlotWidget.addItem(self.odmr_image)
        self._mw.odmr_PlotWidget.setLabel(axis='left', text='Counts',
                                          units='Counts/s')
        self._mw.odmr_PlotWidget.setLabel(axis='bottom', text='Frequency',
                                          units='Hz')

        #self._mw.odmr_PlotWidget.addItem(self.odmr_fit_image)
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

        # Set the state button as ready button as default setting.
        # self._mw.idle_StateWidget.click()

        # Configuration of the comboWidget
        self._mw.mode_ComboBox.addItem('Off')
        self._mw.mode_ComboBox.addItem('CW')

        fit_functions = self._odmr_logic.get_fit_functions()
        self._mw.fit_methods_ComboBox.clear()
        self._mw.fit_methods_ComboBox.addItems(fit_functions)

        ########################################################################
        ##                 Configuration of the Colorbar                      ##
        ########################################################################

        self.odmr_cb = ColorBar(my_colors.cmap_normed, 100, 0, 100000)

        #adding colorbar to ViewWidget
        self._mw.odmr_cb_PlotWidget.addItem(self.odmr_cb)
        self._mw.odmr_cb_PlotWidget.hideAxis('bottom')
        self._mw.odmr_cb_PlotWidget.hideAxis('left')
        self._mw.odmr_cb_PlotWidget.setLabel('right', 'Fluorescence', units='counts/s')

        # Connect the buttons and inputs for the odmr colorbar
        self._mw.odmr_cb_manual_RadioButton.clicked.connect(self.refresh_matrix)
        self._mw.odmr_cb_centiles_RadioButton.clicked.connect(self.refresh_matrix)


        ########################################################################
        ##          Configuration of the various display Widgets              ##
        ########################################################################

        # Take the default values from logic:
        freq_norm = units.get_unit_prefix_dict()[self._freq_prefix]

        self._mw.frequency_DoubleSpinBox.setValue(self._odmr_logic.mw_frequency/freq_norm)
        self._mw.start_freq_DoubleSpinBox.setValue(self._odmr_logic.mw_start/freq_norm)
        self._mw.step_freq_DoubleSpinBox.setValue(self._odmr_logic.mw_step/freq_norm)
        self._mw.stop_freq_DoubleSpinBox.setValue(self._odmr_logic.mw_stop/freq_norm)
        self._mw.power_DoubleSpinBox.setValue(self._odmr_logic.mw_power)
        self._mw.runtime_DoubleSpinBox.setValue(self._odmr_logic.run_time)
        self._mw.elapsed_time_DisplayWidget.display(int(self._odmr_logic.elapsed_time))

        self._sd.matrix_lines_SpinBox.setValue(self._odmr_logic.number_of_lines)
        self._sd.clock_frequency_DoubleSpinBox.setValue(self._odmr_logic._clock_frequency)
        self._sd.fit_tabs = {}
        for name, model in self._odmr_logic.fit_models.items():
            try:
                self._sd.fit_tabs[name] = FitSettingsWidget(model[1])
            except:
                self.logExc('Could not load fitmodel {}'.format(name), msgType='warning')
            else:
                self._sd.tabWidget.addTab(self._sd.fit_tabs[name], name)

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

        self._mw.odmr_cb_max_SpinBox.valueChanged.connect(self.refresh_matrix)
        self._mw.odmr_cb_min_SpinBox.valueChanged.connect(self.refresh_matrix)
        self._mw.odmr_cb_high_centile_SpinBox.valueChanged.connect(self.refresh_matrix)
        self._mw.odmr_cb_low_centile_SpinBox.valueChanged.connect(self.refresh_matrix)

        ########################################################################
        ##                       Connect signals                              ##
        ########################################################################

        # Connect the RadioButtons and connect to the events if they are clicked:
        self._mw.action_run_stop.toggled.connect(self.run_stop)
        self._mw.action_resume_odmr.toggled.connect(self.resume_odmr)
        self._mw.action_Save.triggered.connect(self.save_data)

        # react on an axis change in the logic by adapting the display:
        self._odmr_logic.sigODMRMatrixAxesChanged.connect(self.update_matrix_axes)

        # connect the clear button:
        self._mw.clear_odmr_PushButton.clicked.connect(self.clear_odmr_plots_clicked)

        self._odmr_logic.sigOdmrPlotUpdated.connect(self.refresh_plot)
        self._odmr_logic.sigOdmrFitUpdated.connect(self.refresh_plot_fit)
        self._odmr_logic.sigOdmrMatrixUpdated.connect(self.refresh_matrix)
        self._odmr_logic.sigOdmrElapsedTimeChanged.connect(self.refresh_elapsedtime)
        # connect settings signals
        self._mw.action_Settings.triggered.connect(self.menue_settings)
        self._sd.accepted.connect(self.update_settings)
        self._sd.rejected.connect(self.reject_settings)
        self._sd.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.update_settings)
        self.reject_settings()
        # Connect stop odmr
        self._odmr_logic.sigOdmrFinished.connect(self.odmr_stopped)
        # Combo Widget
        self._mw.mode_ComboBox.activated[str].connect(self.mw_stop)
        self._mw.fit_methods_ComboBox.activated[str].connect(self.update_fit_variable)
        # Push Buttons
        self._mw.do_fit_PushButton.clicked.connect(self.update_fit)

        # Show the Main ODMR GUI:
        self._mw.show()

    def deactivation(self, e):
        """ Reverse steps of activation

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.

        @return int: error code (0:OK, -1:error)
        """
        self._mw.close()
        return 0

    def show(self):
        """Make window visible and put it above all other windows. """
        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def run_stop(self, is_checked):
        """ Manages what happens if odmr scan is started/stopped. """

        if is_checked:

            # change the axes appearance according to input values:
            self._odmr_logic.stop_odmr_scan()
            self._odmr_logic.start_odmr_scan()
            self._mw.action_resume_odmr.setEnabled(False)
            self._mw.odmr_PlotWidget.removeItem(self.odmr_fit_image)

            # during scan, enable the clear plot possibility.
            self._mw.clear_odmr_PushButton.setEnabled(True)
        else:
            self._odmr_logic.stop_odmr_scan()
            self._mw.action_resume_odmr.setEnabled(True)
            # Disable the clear functionality since that is not needed if no
            # scan is running:
            self._mw.clear_odmr_PushButton.setEnabled(False)

    def resume_odmr(self, is_checked):
        if is_checked:
            self._odmr_logic.stop_odmr_scan()
            self._odmr_logic.continue_odmr_scan()
            self._mw.action_run_stop.setEnabled(False)

            # during scan, enable the clear plot possibility.
            self._mw.clear_odmr_PushButton.setEnabled(True)
        else:
            self._odmr_logic.stop_odmr_scan()
            self._mw.action_run_stop.setEnabled(True)
            # Disable the clear functionality since that is not needed if no
            # scan is running:
            self._mw.clear_odmr_PushButton.setEnabled(False)

    def odmr_stopped(self):
        """ Switch the run/stop button to stop after receiving an odmr_stoped
            signal """
        self._mw.action_run_stop.setChecked(False)
        self._mw.action_resume_odmr.setChecked(False)

    def clear_odmr_plots_clicked(self):
        """ Clear the ODMR plots. """
        self._odmr_logic.clear_odmr_plots()

    def menue_settings(self):
        """ Open the settings menue """
        self._sd.exec_()

    def refresh_plot(self):
        """ Refresh the xy-plot image """
        self.odmr_image.setData(self._odmr_logic.ODMR_plot_x,
                                self._odmr_logic.ODMR_plot_y)

    def refresh_plot_fit(self):
        """ Refresh the xy fit plot image. """

        if not self._mw.fit_methods_ComboBox.currentText() == 'No Fit':
            self.odmr_fit_image.setData(x=self._odmr_logic.ODMR_fit_x,
                                        y=self._odmr_logic.ODMR_fit_y)
        else:
            if self.odmr_fit_image in self._mw.odmr_PlotWidget.listDataItems():
                self._mw.odmr_PlotWidget.removeItem(self.odmr_fit_image)

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
            cb_min = self._mw.odmr_cb_min_SpinBox.value()
            cb_max = self._mw.odmr_cb_max_SpinBox.value()

        # Otherwise, calculate cb range from percentiles.
        else:
            # Exclude any zeros (which are typically due to unfinished scan)
            matrix_image_nonzero = matrix_image[np.nonzero(matrix_image)]

            # Read centile range
            low_centile = self._mw.odmr_cb_low_centile_SpinBox.value()
            high_centile = self._mw.odmr_cb_high_centile_SpinBox.value()

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
        self._odmr_logic.safeRawData = self._sd.save_raw_data_CheckBox.isChecked()
        for name, tab in self._sd.fit_tabs.items():
            self._odmr_logic.use_custom_params[name] = tab.updateFitSettings(
                self._odmr_logic.fit_models[name][1])

    def reject_settings(self):
        """ Keep the old settings and restores the old settings in the gui. """
        self._sd.matrix_lines_SpinBox.setValue(self._odmr_logic.number_of_lines)
        self._sd.clock_frequency_DoubleSpinBox.setValue(self._odmr_logic._clock_frequency)
        self._sd.save_raw_data_CheckBox.setChecked(self._odmr_logic.safeRawData)
        for name, tab in self._sd.fit_tabs.items():
            tab.keepFitSettings(
                self._odmr_logic.fit_models[name][1],
                self._odmr_logic.use_custom_params[name])

    def update_fit_variable(self, txt):
        """ Set current fit function """
        self._odmr_logic.current_fit_function = txt

    def update_fit(self):
        """ Do the configured fit and show it in the sum plot """
        x_data_fit, y_data_fit, fit_param, fit_result = self._odmr_logic.do_fit(fit_function=self._odmr_logic.current_fit_function)
        # The fit signal was already emitted in the logic, so there is no need
        # to set the fit data

        # One need to copy the whole fit param dict, otherwise it will be
        # altered and changed.
        fit_param = copy.deepcopy(fit_param)

        # check which Fit method is used and remove or add again the
        # odmr_fit_image, check also whether a odmr_fit_image already exists.
        if self._mw.fit_methods_ComboBox.currentText() == 'No Fit':
            if self.odmr_fit_image in self._mw.odmr_PlotWidget.listDataItems():
                self._mw.odmr_PlotWidget.removeItem(self.odmr_fit_image)
        else:
            if self.odmr_fit_image not in self._mw.odmr_PlotWidget.listDataItems():
                self._mw.odmr_PlotWidget.addItem(self.odmr_fit_image)

        self._mw.odmr_PlotWidget.getViewBox().updateAutoRange()
        self._mw.odmr_fit_results_DisplayWidget.clear()

        # Since the display of the fit parameters is desired e.g. in MHz, adapt
        # the passed parameter dict for further custom display.
        for param in fit_param:

            unit = fit_param[param]['unit']
            norm = 1.0

            # Insert here all custom display of the parameters:
            if fit_param[param]['unit'] == 'Hz':

                freq_prefix = self._freq_prefix
                # safety check, if the prefix is really in the unit_prefix_dict
                if self._freq_prefix not in units.get_unit_prefix_dict():
                    freq_prefix = ''

                norm = units.get_unit_prefix_dict()[freq_prefix]
                unit = '{0}{1}'.format(freq_prefix, fit_param[param]['unit'])

            fit_param[param]['unit'] = unit
            fit_param[param]['value'] = fit_param[param]['value']/norm

            if 'error' in fit_param[param]:
                fit_param[param]['error'] = fit_param[param]['error']/norm

        formated_results = units.create_formatted_output(fit_param)

        self._mw.odmr_fit_results_DisplayWidget.setPlainText(formated_results)

    def _format_param_dict(self, param_dict):
        """ Create from the passed param_dict a proper display of the parameters.

        @param dict param_dict: the dictionary with keys being the names of the
                                parameter and items being values/parameters.

        @return:
        """
        pass

    def mw_stop(self, txt):
        """ Stop frequency sweep and change to CW of off"""
        if txt == 'Off':
            self._odmr_logic.MW_off()
        if txt == 'CW':
            self.change_frequency()
            self.change_power()
            self._odmr_logic.MW_on()


    ############################################################################
    ##                          Change Methods                                ##
    ############################################################################

    def change_frequency(self):
        """ Change CW frequency of microwave source """
        freq_norm = units.get_unit_prefix_dict()[self._freq_prefix]
        self._odmr_logic.set_frequency(frequency=self._mw.frequency_DoubleSpinBox.value()*freq_norm)

    def change_start_freq(self):
        """ Change start frequency of frequency sweep """
        freq_norm = units.get_unit_prefix_dict()[self._freq_prefix]
        self._odmr_logic.mw_start = self._mw.start_freq_DoubleSpinBox.value()*freq_norm

    def change_step_freq(self):
        """ Change step size in which frequency is changed """
        freq_norm = units.get_unit_prefix_dict()[self._freq_prefix]
        self._odmr_logic.mw_step = self._mw.step_freq_DoubleSpinBox.value()*freq_norm

    def change_stop_freq(self):
        """ Change end of frequency sweep """
        freq_norm = units.get_unit_prefix_dict()[self._freq_prefix]
        self._odmr_logic.mw_stop = self._mw.stop_freq_DoubleSpinBox.value()*freq_norm

    def change_power(self):
        """ Change microwave power """
        self._odmr_logic.mw_power = self._mw.power_DoubleSpinBox.value()
        self._odmr_logic.set_power(power=self._odmr_logic.mw_power)

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
            low_centile = self._mw.odmr_cb_low_centile_SpinBox.value()
            high_centile = self._mw.odmr_cb_high_centile_SpinBox.value()
            pcile_range = [low_centile, high_centile]

        self._odmr_logic.save_ODMR_Data(filetag, colorscale_range=cb_range, percentile_range=pcile_range)
