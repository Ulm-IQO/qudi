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

Copyright (C) 2015 Florian S. Frank florian.frank@uni-ulm.de
"""


from pyqtgraph.Qt import QtCore, QtGui, uic
import pyqtgraph as pg
import pyqtgraph.exporters
import numpy as np
import time
import os

from gui.guibase import GUIBase
from gui.guiutils import ColorScale, ColorBar


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
        super().__init__(manager,
                         name,
                         config,
                         c_dict)

        self.logMsg('The following configuration was found.', msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')

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


        # Get the image from the logic
        self.odmr_matrix_image = pg.ImageItem(self._odmr_logic.ODMR_plot_xy.transpose())
        self.odmr_matrix_image.setRect(QtCore.QRectF(self._odmr_logic.MW_start,0,self._odmr_logic.MW_stop-self._odmr_logic.MW_start,self._odmr_logic.NumberofLines))
        self.odmr_image = pg.PlotDataItem(self._odmr_logic.ODMR_plot_x,self._odmr_logic.ODMR_plot_y)
        self.odmr_fit_image = pg.PlotDataItem(self._odmr_logic.ODMR_fit_x,self._odmr_logic.ODMR_fit_y,
                                                    pen=QtGui.QPen(QtGui.QColor(255,255,255,255)))

        # Add the display item to the xy and xz VieWidget, which was defined in
        # the UI file.
        self._mw.odmr_PlotWidget.addItem(self.odmr_image)
        self._mw.odmr_PlotWidget.addItem(self.odmr_fit_image)
        self._mw.odmr_matrix_PlotWidget.addItem(self.odmr_matrix_image)
        self._mw.odmr_PlotWidget.showGrid(x=True, y=True, alpha=0.8)



        # Get the colorscales at set LUT
        my_colors = ColorScale()

        self.odmr_matrix_image.setLookupTable(my_colors.lut)

        # Set the state button as ready button as default setting.
        # self._mw.idle_StateWidget.click()

        # Configuration of the comboWidget
        self._mw.mode_ComboBox.addItem('Off')
        self._mw.mode_ComboBox.addItem('CW')

        self._mw.fit_methods_ComboBox.addItem('No Fit')
        self._mw.fit_methods_ComboBox.addItem('Lorentzian')
        self._mw.fit_methods_ComboBox.addItem('Double Lorentzian')
        self._mw.fit_methods_ComboBox.addItem('Double Lorentzian with fixed splitting')
        self._mw.fit_methods_ComboBox.addItem('N14')
        self._mw.fit_methods_ComboBox.addItem('N15')


        ########################################################################
        ##                 Configuration of the Colorbar                      ##
        ########################################################################

        self.odmr_cb = ColorBar(my_colors.cmap_normed, 100, 0, 100000)

        #adding colorbar to ViewWidget
        self._mw.odmr_cb_PlotWidget.addItem(self.odmr_cb)
        self._mw.odmr_cb_PlotWidget.hideAxis('bottom')
        self._mw.odmr_cb_PlotWidget.hideAxis('left')
        self._mw.odmr_cb_PlotWidget.setLabel('right', 'Fluorescence', units='c/s')

        # Connect the buttons and inputs for the odmr colorbar
        self._mw.odmr_cb_manual_RadioButton.clicked.connect(self.refresh_matrix)
        self._mw.odmr_cb_centiles_RadioButton.clicked.connect(self.refresh_matrix)


        ########################################################################
        ##          Configuration of the various display Widgets              ##
        ########################################################################

        # Take the default values from logic:
        self._mw.frequency_DoubleSpinBox.setValue(self._odmr_logic.MW_frequency)
        self._mw.start_freq_DoubleSpinBox.setValue(self._odmr_logic.MW_start)
        self._mw.step_freq_DoubleSpinBox.setValue(self._odmr_logic.MW_step)
        self._mw.stop_freq_DoubleSpinBox.setValue(self._odmr_logic.MW_stop)
        self._mw.power_DoubleSpinBox.setValue(self._odmr_logic.MW_power)
        self._mw.runtime_DoubleSpinBox.setValue(self._odmr_logic.RunTime)
        self._mw.elapsed_time_DisplayWidget.display(int(self._odmr_logic.ElapsedTime))
        self._sd.matrix_lines_SpinBox.setValue(self._odmr_logic.NumberofLines)
        self._sd.clock_frequency_DoubleSpinBox.setValue(self._odmr_logic._clock_frequency)

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

        #

        self._mw.odmr_cb_max_SpinBox.valueChanged.connect(self.refresh_matrix)
        self._mw.odmr_cb_min_SpinBox.valueChanged.connect(self.refresh_matrix)
        self._mw.odmr_cb_high_centile_SpinBox.valueChanged.connect(self.refresh_matrix)
        self._mw.odmr_cb_low_centile_SpinBox.valueChanged.connect(self.refresh_matrix)

        ########################################################################
        ##                       Connect signals                              ##
        ########################################################################

        # Connect the RadioButtons and connect to the events if they are clicked:
        # self._mw.idle_StateWidget.toggled.connect(self.idle_clicked)
        # self._mw.run_StateWidget.toggled.connect(self.run_clicked)
        self._mw.action_run_stop.toggled.connect(self.run_stop)
        self._mw.action_Save.triggered.connect(self.save_plots_and_data)

        self._odmr_logic.signal_ODMR_plot_updated.connect(self.refresh_plot)
        self._odmr_logic.signal_ODMR_matrix_updated.connect(self.refresh_matrix)
        self._odmr_logic.signal_ODMR_elapsedtime_changed.connect(self.refresh_elapsedtime)
        # connect settings signals
        self._mw.action_Settings.triggered.connect(self.menue_settings)
        self._sd.accepted.connect(self.update_settings)
        self._sd.rejected.connect(self.reject_settings)
        self._sd.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.update_settings)
        self.reject_settings()
        # Connect stop odmr
        # self._odmr_logic.signal_ODMR_finished.connect(self._mw.idle_StateWidget.click)
        self._odmr_logic.signal_ODMR_finished.connect(self.odmr_stopped)
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

#     def idle_clicked(self):
#         """ Stopp the scan if the state has switched to idle. """
#         self._odmr_logic.stop_ODMR_scan()
#         self._sd.matrix_lines_SpinBox.setReadOnly(False)
# #        self._odmr_logic.kill_ODMR()
#
#
#     def run_clicked(self, enabled):
#         """ Manages what happens if odmr scan is started.
#
#         @param bool enabled: start scan if that is possible
#         """
#
#         #Firstly stop any scan that might be in progress
#         self._odmr_logic.stop_ODMR_scan()
# #        self._odmr_logic.kill_ODMR()
#         #Then if enabled. start a new odmr scan.
#         if enabled:
#             self._odmr_logic.start_ODMR_scan()
#             self._sd.matrix_lines_SpinBox.setReadOnly(True)

    def run_stop(self, is_checked):
        """ Manages what happens if odmr scan is started/stopped """
        if is_checked:
            self._odmr_logic.stop_ODMR_scan()
            self._odmr_logic.start_ODMR_scan()
            self._mw.odmr_PlotWidget.removeItem(self.odmr_fit_image)
            self._sd.matrix_lines_SpinBox.setReadOnly(True)
        else:
            self._odmr_logic.stop_ODMR_scan()
            self._sd.matrix_lines_SpinBox.setReadOnly(False)

    def odmr_stopped(self):
        """ Switch the run/stop button to stop after receiving an odmr_stoped
            signal """
        self._mw.action_run_stop.setChecked(False)

    def menue_settings(self):
        """ Open the settings menue """
        self._sd.exec_()

    def refresh_plot(self):
        """ Refresh the xy-plot image """
        self.odmr_image.setData(self._odmr_logic.ODMR_plot_x,
                                self._odmr_logic.ODMR_plot_y)

        if not self._mw.fit_methods_ComboBox.currentText() == 'No Fit':
            self.odmr_fit_image.setData(self._odmr_logic.ODMR_fit_x,
                                        self._odmr_logic.ODMR_fit_y,
                                        pen=QtGui.QPen(QtGui.QColor(255,0,255,255)))
        else:
            if self.odmr_fit_image in self._mw.odmr_PlotWidget.listDataItems():
                self._mw.odmr_PlotWidget.removeItem(self.odmr_fit_image)

    def refresh_matrix(self):
        """ Refresh the xy-matrix image """
#        self.odmr_matrix_image.setImage(self._odmr_logic.ODMR_plot_xy.transpose())
#        self.odmr_matrix_image.setRect(QtCore.QRectF(self._odmr_logic.MW_start,
#                                                     0,
#                                                     self._odmr_logic.MW_stop-self._odmr_logic.MW_start,self._odmr_logic.NumberofLines))
#        self.refresh_odmr_colorbar()

        odmr_image_data = self._odmr_logic.ODMR_plot_xy.transpose()

        # If "Centiles" is checked, adjust colour scaling automatically to
        # centiles. Otherwise, take user-defined values:
        if self._mw.odmr_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.odmr_cb_low_centile_SpinBox.value()
            high_centile = self._mw.odmr_cb_high_centile_SpinBox.value()

            cb_min = np.percentile(odmr_image_data, low_centile)
            cb_max = np.percentile(odmr_image_data, high_centile)

        else:
            cb_min = self._mw.odmr_cb_min_SpinBox.value()
            cb_max = self._mw.odmr_cb_max_SpinBox.value()

        # Now update image with new color scale, and update colorbar
        self.odmr_matrix_image.setImage(image=odmr_image_data,
                                        levels=(cb_min, cb_max))
        self.odmr_matrix_image.setRect(QtCore.QRectF(self._odmr_logic.MW_start,
                                                     0,
                                                     self._odmr_logic.MW_stop-self._odmr_logic.MW_start,self._odmr_logic.NumberofLines))
        self.refresh_odmr_colorbar()


    def refresh_odmr_colorbar(self):
        """ Update the colorbar to a new scaling."""

        # If "Centiles" is checked, adjust colour scaling automatically to
        # centiles. Otherwise, take user-defined values.

        if self._mw.odmr_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.odmr_cb_low_centile_SpinBox.value()
            high_centile = self._mw.odmr_cb_high_centile_SpinBox.value()

            cb_min = np.percentile(self.odmr_matrix_image.image, low_centile)
            cb_max = np.percentile(self.odmr_matrix_image.image, high_centile)

        else:
            cb_min = self._mw.odmr_cb_min_SpinBox.value()
            cb_max = self._mw.odmr_cb_max_SpinBox.value()

        self.odmr_cb.refresh_colorbar(cb_min, cb_max)
        self._mw.odmr_cb_PlotWidget.update()

    def refresh_elapsedtime(self):
        """ Show current elapsed measurement time """
        self._mw.elapsed_time_DisplayWidget.display(int(self._odmr_logic.ElapsedTime))

    def update_settings(self):
        """ Write the new settings from the gui to the file. """
        self._odmr_logic.NumberofLines = self._sd.matrix_lines_SpinBox.value()
        self._odmr_logic.set_clock_frequency(self._sd.clock_frequency_DoubleSpinBox.value())
        self._odmr_logic.safeRawData = self._sd.save_raw_data_CheckBox.isChecked()

    def update_fit_variable(self, txt):
        """ Set current fit function """
        self._odmr_logic.current_fit_function = txt

    def update_fit(self):
        """ Do the configured fit and show it in the sum plot """
        self._odmr_logic.do_fit(fit_function=self._odmr_logic.current_fit_function)
        self.refresh_plot()

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
        self._mw.odmr_fit_results_DisplayWidget.setPlainText(str(self._odmr_logic.fit_result))

    def reject_settings(self):
        """ Keep the old settings and restores the old settings in the gui. """
        self._sd.matrix_lines_SpinBox.setValue(self._odmr_logic.NumberofLines)
        self._sd.clock_frequency_DoubleSpinBox.setValue(self._odmr_logic._clock_frequency)
        self._sd.save_raw_data_CheckBox.setChecked(self._odmr_logic.safeRawData)

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
        self._odmr_logic.set_frequency(frequency=self._mw.frequency_DoubleSpinBox.value())

    def change_start_freq(self):
        """ Change start frequency of frequency sweep """
        self._odmr_logic.MW_start = self._mw.start_freq_DoubleSpinBox.value()

    def change_step_freq(self):
        """ Change step size in which frequency is changed """
        self._odmr_logic.MW_step = self._mw.step_freq_DoubleSpinBox.value()

    def change_stop_freq(self):
        """ Change end of frequency sweep """
        self._odmr_logic.MW_stop = self._mw.stop_freq_DoubleSpinBox.value()

    def change_power(self):
        """ Change microwave power """
        self._odmr_logic.MW_power = self._mw.power_DoubleSpinBox.value()
        self._odmr_logic.set_power(power=self._odmr_logic.MW_power)

    def change_runtime(self):
        """ Change time after which microwave sweep is stopped """
        self._odmr_logic.RunTime = self._mw.runtime_DoubleSpinBox.value()

    def save_plots_and_data(self):
        """ Save the sum plot, the scan marix plot and the scan data """
        filepath = self._save_logic.get_path_for_module(module_name='ODMR')
        filename = os.path.join(filepath, time.strftime('%Y%m%d-%H%M-%S_odmr'))

        exporter_graph = pg.exporters.SVGExporter(self._mw.odmr_PlotWidget.plotItem.scene())
        #exporter_graph = pg.exporters.ImageExporter(self._mw.odmr_PlotWidget.plotItem)
        exporter_graph.export(filename+'.svg')

        exporter_matrix = pg.exporters.SVGExporter(self._mw.odmr_matrix_PlotWidget.plotItem.scene())
        #exporter_matrix = pg.exporters.ImageExporter(self._mw.odmr_matrix_PlotWidget.plotItem)
        exporter_matrix.export(filename + '_matrix' + '.svg')

        # self._save_logic.
        self._odmr_logic.save_ODMR_Data()
