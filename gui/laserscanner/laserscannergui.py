# -*- coding: utf-8 -*-
"""
This file contains the QuDi GUI module to operate the voltage (laser) scanner.

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

#from PyQt4 import QtCore, QtGui
from pyqtgraph.Qt import QtCore, QtGui, uic
import pyqtgraph as pg
import numpy as np
import os

from collections import OrderedDict
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from gui.colordefs import ColorScaleInferno


class VoltScanMainWindow(QtGui.QMainWindow):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_odmrgui.ui')

        # Load it
        super(ODMRMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()


class VoltScanGui(GUIBase):
    """
    This is the GUI Class for ODMR
    """
    _modclass = 'VoltScanGui'
    _modtype = 'gui'
    ## declare connectors
    _in = {'voltagescannerlogic1': 'VoltageScannerLogic',
          }

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{}: {}'.format(key,config[key]))

    def on_deactivate(self, e):
        """ Reverse steps of activation

        @param e: error code

        @return int: error code (0:OK, -1:error)
        """
        self._mw.close()
        return 0

    def on_activate(self, e=None):
        """ Definition, configuration and initialisation of the ODMR GUI.

          @param class e: event class from Fysom


        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.

        """

        self._voltscan_logic = self.connector['in']['odmrlogic1']['object']
        print("ODMR logic is", self._odmr_logic)

        # Use the inherited class 'Ui_VoltagescannerGuiUI' to create now the
        # GUI element:
        self._mw = VoltScanMainWindow()

        # Get the image from the logic
        self.odmr_matrix_image = pg.ImageItem(self._odmr_logic.ODMR_plot_xy.transpose())
        self.odmr_matrix_image.setRect(QtCore.QRectF(self._odmr_logic.mw_start,0,self._odmr_logic.mw_stop-self._odmr_logic.mw_start,self._odmr_logic.number_of_lines))
        self.odmr_image = pg.PlotDataItem(self._odmr_logic.ODMR_plot_x,self._odmr_logic.ODMR_plot_y)
        self.odmr_fit_image = pg.PlotDataItem(self._odmr_logic.ODMR_fit_x,self._odmr_logic.ODMR_fit_y,
                                                    pen=QtGui.QPen(QtGui.QColor(255,255,255,255)))


        # Add the display item to the xy and xz VieWidget, which was defined in
        # the UI file.
        self._mw.voltscan_ViewWidget.addItem(self.odmr_image)
        self._mw.voltscan_ViewWidget.addItem(self.odmr_fit_image)
        self._mw.voltscan_matrix_ViewWidget.addItem(self.odmr_matrix_image)
        self._mw.vonsoltscan_ViewWidget.showGrid(x=True, y=True, alpha=0.8)



        # Get the colorscales at set LUT
        my_colors = ColorScaleInferno()

        self.odmr_matrix_image.setLookupTable(my_colors.lut)

        # Set the state button as ready button as default setting.
        # self._mw.idle_StateWidget.click()

        # Configuration of the comboWidget
        self._mw.mode_ComboWidget.addItem('Off')
        self._mw.mode_ComboWidget.addItem('CW')

        self._mw.fit_methods_ComboWidget.addItem('No Fit')
        self._mw.fit_methods_ComboWidget.addItem('Lorentzian')
        self._mw.fit_methods_ComboWidget.addItem('Double Lorentzian')
        self._mw.fit_methods_ComboWidget.addItem('Double Lorentzian with fixed splitting')
        self._mw.fit_methods_ComboWidget.addItem('N14')
        self._mw.fit_methods_ComboWidget.addItem('N15')


        #######################################################################
        ##                Configuration of the Colorbar                      ##
        #######################################################################

        self.odmr_cb = ColorBar(my_colors.cmap_normed, 100, 0, 100000)

        #adding colorbar to ViewWidget
        self._mw.odmr_cb_ViewWidget.addItem(self.odmr_cb)
        self._mw.odmr_cb_ViewWidget.hideAxis('bottom')
        self._mw.odmr_cb_ViewWidget.hideAxis('left')
        self._mw.odmr_cb_ViewWidget.setLabel('right', 'Fluorescence', units='c/s')

        # Connect the buttons and inputs for the odmr colorbar
        self._mw.odmr_cb_manual_RadioButton.clicked.connect(self.refresh_matrix)
        self._mw.odmr_cb_centiles_RadioButton.clicked.connect(self.refresh_matrix)


        #######################################################################
        ##                Configuration of the InputWidgets                  ##
        #######################################################################

        # Add Validators to InputWidgets
        validator = QtGui.QDoubleValidator()
        validator2 = QtGui.QIntValidator()

        self._mw.frequency_InputWidget.setValidator(validator)
        self._mw.start_freq_InputWidget.setValidator(validator)
        self._mw.step_freq_InputWidget.setValidator(validator)
        self._mw.stop_freq_InputWidget.setValidator(validator)
        self._mw.power_InputWidget.setValidator(validator)
        self._mw.runtime_InputWidget.setValidator(validator2)
        self._sd.matrix_lines_InputWidget.setValidator(validator)
        self._sd.clock_frequency_InputWidget.setValidator(validator2)

        # Take the default values from logic:
        self._mw.frequency_InputWidget.setText(str(self._odmr_logic.mw_frequency))
        self._mw.start_freq_InputWidget.setText(str(self._odmr_logic.mw_start))
        self._mw.step_freq_InputWidget.setText(str(self._odmr_logic.mw_step))
        self._mw.stop_freq_InputWidget.setText(str(self._odmr_logic.mw_stop))
        self._mw.power_InputWidget.setText(str(self._odmr_logic.mw_power))
        self._mw.runtime_InputWidget.setText(str(self._odmr_logic.run_time))
        self._mw.elapsed_time_DisplayWidget.display(int(self._odmr_logic.ElapsedTime))
        self._sd.matrix_lines_InputWidget.setText(str(self._odmr_logic.number_of_lines))
        self._sd.clock_frequency_InputWidget.setText(str(self._odmr_logic._clock_frequency))

        # Update the inputed/displayed numbers if return key is hit:

        self._mw.frequency_InputWidget.returnPressed.connect(self.change_frequency)
        self._mw.start_freq_InputWidget.returnPressed.connect(self.change_start_freq)
        self._mw.step_freq_InputWidget.returnPressed.connect(self.change_step_freq)
        self._mw.stop_freq_InputWidget.returnPressed.connect(self.change_stop_freq)
        self._mw.power_InputWidget.returnPressed.connect(self.change_power)
        self._mw.runtime_InputWidget.returnPressed.connect(self.change_runtime)

        # Update the inputed/displayed numbers if the cursor has left the field:

        self._mw.frequency_InputWidget.editingFinished.connect(self.change_frequency)
        self._mw.start_freq_InputWidget.editingFinished.connect(self.change_start_freq)
        self._mw.step_freq_InputWidget.editingFinished.connect(self.change_step_freq)
        self._mw.stop_freq_InputWidget.editingFinished.connect(self.change_stop_freq)
        self._mw.power_InputWidget.editingFinished.connect(self.change_power)
        self._mw.runtime_InputWidget.editingFinished.connect(self.change_runtime)

        #

        self._mw.odmr_cb_max_InputWidget.valueChanged.connect(self.refresh_matrix)
        self._mw.odmr_cb_min_InputWidget.valueChanged.connect(self.refresh_matrix)
        self._mw.odmr_cb_high_centile_InputWidget.valueChanged.connect(self.refresh_matrix)
        self._mw.odmr_cb_low_centile_InputWidget.valueChanged.connect(self.refresh_matrix)

        #######################################################################
        ##                      Connect signals                              ##
        #######################################################################

        # Connect the RadioButtons and connect to the events if they are clicked:
        # self._mw.idle_StateWidget.toggled.connect(self.idle_clicked)
        # self._mw.run_StateWidget.toggled.connect(self.run_clicked)
        self._mw.action_run_stop.toggled.connect(self.run_stop)
        self._mw.action_Save.triggered.connect(self._odmr_logic.save_ODMR_Data)

        self._odmr_logic.sigOdmrPlotUpdated.connect(self.refresh_plot)
        self._odmr_logic.sigOdmrPlotUpdated.connect(self.refresh_matrix)
        self._odmr_logic.sigOdmrElapsedTimeChanged.connect(self.refresh_elapsedtime)
        # connect settings signals
        self._mw.action_Settings.triggered.connect(self.menue_settings)
        self._sd.accepted.connect(self.update_settings)
        self._sd.rejected.connect(self.reject_settings)
        self._sd.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.update_settings)
        self.reject_settings()
        # Connect stop odmr
        # self._odmr_logic.sigOdmrFinished.connect(self._mw.idle_StateWidget.click)
        self._odmr_logic.sigOdmrFinished.connect(self.odmr_stopped)
        # Combo Widget
        self._mw.mode_ComboWidget.activated[str].connect(self.mw_stop)
        self._mw.fit_methods_ComboWidget.activated[str].connect(self.update_fit_variable)
        # Push Buttons
        self._mw.do_fit_PushButton.clicked.connect(self.update_fit)

        # Show the Main ODMR GUI:
        self._mw.show()




    def show(self):
        """Make window visible and put it above all other windows. """
        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

#     def idle_clicked(self):
#         """ Stopp the scan if the state has switched to idle. """
#         self._odmr_logic.stop_odmr_scan()
#         self._sd.matrix_lines_InputWidget.setReadOnly(False)
# #        self._odmr_logic.kill_odmr()
#
#
#     def run_clicked(self, enabled):
#         """ Manages what happens if odmr scan is started.
#
#         @param bool enabled: start scan if that is possible
#         """
#
#         #Firstly stop any scan that might be in progress
#         self._odmr_logic.stop_odmr_scan()
# #        self._odmr_logic.kill_odmr()
#         #Then if enabled. start a new odmr scan.
#         if enabled:
#             self._odmr_logic.start_odmr_scan()
#             self._sd.matrix_lines_InputWidget.setReadOnly(True)

    def run_stop(self, is_checked):
        """ Manages what happens if odmr scan is started/stopped """
        if is_checked:
            self._odmr_logic.stop_odmr_scan()
            self._odmr_logic.start_odmr_scan()
            self._mw.odmr_ViewWidget.removeItem(self.odmr_fit_image)
            self._sd.matrix_lines_InputWidget.setReadOnly(True)
        else:
            self._odmr_logic.stop_odmr_scan()
            self._sd.matrix_lines_InputWidget.setReadOnly(False)

    def odmr_stopped(self):
        """ Switch the run/stop button to stop after receiving an odmr_stoped signal """
        self._mw.action_run_stop.setChecked(False)

    def menue_settings(self):
        """ Open the settings menue """
        self._sd.exec_()

    def refresh_plot(self):
        """ Refresh the xy-plot image """
        self.odmr_image.setData(self._odmr_logic.ODMR_plot_x,self._odmr_logic.ODMR_plot_y)
        if not self._mw.fit_methods_ComboWidget.currentText() == 'No Fit':
            self.odmr_fit_image.setData(self._odmr_logic.ODMR_fit_x,self._odmr_logic.ODMR_fit_y,pen=QtGui.QPen(QtGui.QColor(255,0,255,255)))
        else:
            if self.odmr_fit_image in self._mw.odmr_ViewWidget.listDataItems():
                self._mw.odmr_ViewWidget.removeItem(self.odmr_fit_image)

    def refresh_matrix(self):
        """ Refresh the xy-matrix image """
#        self.odmr_matrix_image.setImage(self._odmr_logic.ODMR_plot_xy.transpose())
#        self.odmr_matrix_image.setRect(QtCore.QRectF(self._odmr_logic.mw_start,0,self._odmr_logic.mw_stop-self._odmr_logic.mw_start,self._odmr_logic.number_of_lines))
#        self.refresh_odmr_colorbar()


        odmr_image_data = self._odmr_logic.ODMR_plot_xy.transpose()

        # If "Centiles" is checked, adjust colour scaling automatically to centiles.
        # Otherwise, take user-defined values.
        if self._mw.odmr_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.odmr_cb_low_centile_InputWidget.value()
            high_centile = self._mw.odmr_cb_high_centile_InputWidget.value()

            cb_min = np.percentile( odmr_image_data, low_centile )
            cb_max = np.percentile( odmr_image_data, high_centile )

        else:
            cb_min = self._mw.odmr_cb_min_InputWidget.value()
            cb_max = self._mw.odmr_cb_max_InputWidget.value()

        # Now update image with new color scale, and update colorbar
        self.odmr_matrix_image.setImage(image=odmr_image_data, levels=(cb_min, cb_max) )
        self.odmr_matrix_image.setRect(QtCore.QRectF(self._odmr_logic.mw_start,0,self._odmr_logic.mw_stop-self._odmr_logic.mw_start,self._odmr_logic.number_of_lines))
        self.refresh_odmr_colorbar()


    def refresh_odmr_colorbar(self):
        """ Update the colorbar to a new scaling."""

        # If "Centiles" is checked, adjust colour scaling automatically to centiles.
        # Otherwise, take user-defined values.
        if self._mw.odmr_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.odmr_cb_low_centile_InputWidget.value()
            high_centile = self._mw.odmr_cb_high_centile_InputWidget.value()

            cb_min = np.percentile( self.odmr_matrix_image.image, low_centile )
            cb_max = np.percentile( self.odmr_matrix_image.image, high_centile )

        else:
            cb_min = self._mw.odmr_cb_min_InputWidget.value()
            cb_max = self._mw.odmr_cb_max_InputWidget.value()

        self.odmr_cb.refresh_colorbar(cb_min,cb_max)
        self._mw.odmr_cb_ViewWidget.update()

    def refresh_elapsedtime(self):
        self._mw.elapsed_time_DisplayWidget.display(int(self._odmr_logic.ElapsedTime))

    def update_settings(self):
        """ Write the new settings from the gui to the file. """
        self._odmr_logic.number_of_lines = int(self._sd.matrix_lines_InputWidget.text())
        self._odmr_logic.set_clock_frequency(int(self._sd.clock_frequency_InputWidget.text()))
        self._odmr_logic.safeRawData = self._sd.save_raw_data_box.isChecked()

    def update_fit_variable(self, txt):
        self._odmr_logic.current_fit_function = txt

    def update_fit(self):
        self._odmr_logic.do_fit(fit_function = self._odmr_logic.current_fit_function)
        self.refresh_plot()

        # check which Fit method is used and remove or add again the
        # odmr_fit_image, check also whether a odmr_fit_image already exists.
        if self._mw.fit_methods_ComboWidget.currentText() == 'No Fit':
            if self.odmr_fit_image in self._mw.odmr_ViewWidget.listDataItems():
                self._mw.odmr_ViewWidget.removeItem(self.odmr_fit_image)
        else:
            if self.odmr_fit_image not in self._mw.odmr_ViewWidget.listDataItems():
                self._mw.odmr_ViewWidget.addItem(self.odmr_fit_image)

        self._mw.odmr_ViewWidget.getViewBox().updateAutoRange()
        self._mw.odmr_fit_results_DisplayWidget.clear()
        self._mw.odmr_fit_results_DisplayWidget.setPlainText(str(self._odmr_logic.fit_result))

    def reject_settings(self):
        """ Keep the old settings and restores the old settings in the gui. """
        self._sd.matrix_lines_InputWidget.setText(str(self._odmr_logic.number_of_lines))
        self._sd.clock_frequency_InputWidget.setText(str(self._odmr_logic._clock_frequency))
        self._sd.save_raw_data_box.setChecked(self._odmr_logic.safeRawData)

    def mw_stop(self, txt):
        if txt == 'Off':
            self._odmr_logic.MW_off()
        if txt == 'CW':
            self.change_frequency()
            self.change_power()
            self._odmr_logic.MW_on()



    ###########################################################################
    ##                         Change Methods                                ##
    ###########################################################################

    def change_frequency(self):
        self._odmr_logic.set_frequency(frequency = float(self._mw.frequency_InputWidget.text()))

    def change_start_freq(self):
        self._odmr_logic.mw_start = float(self._mw.start_freq_InputWidget.text())

    def change_step_freq(self):
        self._odmr_logic.mw_step = float(self._mw.step_freq_InputWidget.text())

    def change_stop_freq(self):
        self._odmr_logic.mw_stop = float(self._mw.stop_freq_InputWidget.text())

    def change_power(self):
        self._odmr_logic.mw_power = float(self._mw.power_InputWidget.text())
        self._odmr_logic.set_power(power = self._odmr_logic.mw_power)

    def change_runtime(self):
        self._odmr_logic.run_time = float(self._mw.runtime_InputWidget.text())




