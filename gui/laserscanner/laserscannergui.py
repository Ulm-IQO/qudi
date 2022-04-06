# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI module to operate the voltage (laser) scanner.

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
import time
from collections import OrderedDict
from core.connector import Connector
from gui.colordefs import ColorScaleInferno
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy import uic


class VoltScanMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_laserscannergui.ui')

        # Load it
        super(VoltScanMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()


class VoltScanGui(GUIBase):
    """

    """
    
    # declare connectors
    voltagescannerlogic1 = Connector(interface='LaserScannerLogic')
    savelogic = Connector(interface='SaveLogic')

    sigStartScan = QtCore.Signal()
    sigResumeScan = QtCore.Signal()
    sigStopScan = QtCore.Signal()
    sigChangeVoltage = QtCore.Signal(float)
    sigChangeRange = QtCore.Signal(list)
    sigChangeResolution = QtCore.Signal(float)
    sigChangeSpeed = QtCore.Signal(float)
    sigChangeLines = QtCore.Signal(int)
    sigSaveMeasurement = QtCore.Signal(str, list, list)

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        self._mw.close()
        return 0

    def on_activate(self):
        """ 

        """
        self._voltscan_logic = self.voltagescannerlogic1()
        self._savelogic = self.savelogic()

        # Use the inherited class 'Ui_VoltagescannerGuiUI' to create now the
        # GUI element:
        self._mw = VoltScanMainWindow()

        # Add save file tag input box
        self._mw.save_tag_LineEdit = QtWidgets.QLineEdit(self._mw)
        self._mw.save_tag_LineEdit.setMaximumWidth(500)
        self._mw.save_tag_LineEdit.setMinimumWidth(200)
        self._mw.save_tag_LineEdit.setToolTip('Enter a nametag which will be\n'
                                              'added to the filename.')
        self._mw.toolBar.addWidget(self._mw.save_tag_LineEdit)

        # Get the image from the logic
        self.scan_matrix_image = pg.ImageItem(
            self._voltscan_logic.scan_matrix_new,
            axisOrder='row-major')

        self.scan_matrix_image.setRect(
            QtCore.QRectF(
                self._voltscan_logic.scan_range[0],
                0,
                self._voltscan_logic.scan_range[1] - self._voltscan_logic.scan_range[0],
                self._voltscan_logic.number_of_repeats)
        )

        self.scan_matrix_image2 = pg.ImageItem(
            self._voltscan_logic.scan_matrix2,
            axisOrder='row-major')

        self.scan_matrix_image2.setRect(
            QtCore.QRectF(
                self._voltscan_logic.scan_range[0],
                0,
                self._voltscan_logic.scan_range[1] - self._voltscan_logic.scan_range[0],
                self._voltscan_logic.number_of_repeats)
        )

        self.scan_image = pg.PlotDataItem()
        #self.scan_image2 = pg.PlotDataItem(self._voltscan_logic.plot_x, self._voltscan_logic.plot_y)
        #self.scan_image = pg.PlotDataItem(
        #    self._voltscan_logic.raw_matrix_voltage[self._voltscan_logic._scan_counter_down+self._voltscan_logic._scan_counter_up],
        #    self._voltscan_logic.raw_matrix_counts[self._voltscan_logic._scan_counter_up+self._voltscan_logic._scan_counter_down])

        self.scan_image2 = pg.PlotDataItem()
        #    self._voltscan_logic.raw_matrix_voltage[self._voltscan_logic._scan_counter_down+self._voltscan_logic._scan_counter_up],
        #    self._voltscan_logic.raw_matrix_counts[self._voltscan_logic._scan_counter_down+self._voltscan_logic._scan_counter_up])

        self.scan_fit_image = pg.PlotDataItem(
            self._voltscan_logic.fit_x,
            self._voltscan_logic.fit_y,
            pen=pg.mkPen('r', width=5))
            #pen=QtGui.QPen(QtGui.QColor(0, 255, 255, 255)))
        self.scan_fit_image2 = pg.PlotDataItem(
            self._voltscan_logic.fit_x2,
            self._voltscan_logic.fit_y2,
            pen=pg.mkPen('r', width=5))
        # pen=QtGui.QPen(QtGui.QColor(0, 255, 255, 255)))

        # Add the display item to the xy and xz VieWidget, which was defined in
        # the UI file.
        self._mw.voltscan_ViewWidget.addItem(self.scan_image)
        self._mw.voltscan_ViewWidget.addItem(self.scan_fit_image)
        self._mw.voltscan_ViewWidget.showGrid(x=True, y=True, alpha=0.8)
        self._mw.voltscan_ViewWidget.setLabel('bottom','Voltage',units='V')
        self._mw.voltscan_ViewWidget.setLabel('left','Fluorescence',units='counts/s')

        self._mw.voltscan_matrix_ViewWidget.addItem(self.scan_matrix_image)
        self._mw.voltscan_matrix_ViewWidget.setLabel('bottom','Voltage',units='V')
        self._mw.voltscan_matrix_ViewWidget.setLabel('left', 'Scan Lines')


        self._mw.voltscan2_ViewWidget.addItem(self.scan_image2)
        self._mw.voltscan2_ViewWidget.addItem(self.scan_fit_image2)
        self._mw.voltscan2_ViewWidget.showGrid(x=True, y=True, alpha=0.8)
        self._mw.voltscan2_ViewWidget.setLabel('bottom','Voltage',units='V')
        self._mw.voltscan2_ViewWidget.setLabel('left','Fluorescence',units='counts/s')

        self._mw.voltscan_matrix2_ViewWidget.addItem(self.scan_matrix_image2)
        self._mw.voltscan_matrix2_ViewWidget.setLabel('bottom', 'Voltage', units='V')
        self._mw.voltscan_matrix2_ViewWidget.setLabel('left', 'Scan Lines')


        # Get the colorscales at set LUT
        my_colors = ColorScaleInferno()

        self.scan_matrix_image.setLookupTable(my_colors.lut)
        self.scan_matrix_image2.setLookupTable(my_colors.lut)

        # Configuration of the Colorbar
        self.scan_cb = ColorBar(my_colors.cmap_normed, 100, 0, 100000)

        #adding colorbar to ViewWidget
        self._mw.voltscan_cb_ViewWidget.addItem(self.scan_cb)
        self._mw.voltscan_cb_ViewWidget.hideAxis('bottom')
        self._mw.voltscan_cb_ViewWidget.hideAxis('left')
        self._mw.voltscan_cb_ViewWidget.setLabel('right', 'Fluorescence', units='c/s')

        # Connect the buttons and inputs for colorbar
        self._mw.voltscan_cb_manual_RadioButton.clicked.connect(self.refresh_matrix)
        self._mw.voltscan_cb_centiles_RadioButton.clicked.connect(self.refresh_matrix)

        # set constrains
        self._mw.startDoubleSpinBox.setMaximum(self._voltscan_logic.a_range[1])
        self._mw.stopDoubleSpinBox.setMaximum(self._voltscan_logic.a_range[1])
        self._mw.startDoubleSpinBox.setMinimum(self._voltscan_logic.a_range[0])
        self._mw.stopDoubleSpinBox.setMinimum(self._voltscan_logic.a_range[0])
        self._mw.speedDoubleSpinBox.setMaximum(self._voltscan_logic._speed_limit)
        # set initial values
        self._mw.startDoubleSpinBox.setValue(self._voltscan_logic.scan_range[0])

        self._mw.speedDoubleSpinBox.setValue(self._voltscan_logic._scan_speed)
        self._mw.stopDoubleSpinBox.setValue(self._voltscan_logic.scan_range[1])
        self._mw.constDoubleSpinBox.setValue(self._voltscan_logic._static_v)
        self._mw.resolutionSpinBox.setValue(self._voltscan_logic.resolution)
        self._mw.linesSpinBox.setValue(self._voltscan_logic.number_of_repeats)

        # Update the inputed/displayed numbers if the cursor has left the field:
        self._mw.startDoubleSpinBox.editingFinished.connect(self.update_scan_range)
        self._mw.speedDoubleSpinBox.editingFinished.connect(self.update_scan_speed)
        self._mw.stopDoubleSpinBox.editingFinished.connect(self.update_scan_range)
        self._mw.resolutionSpinBox.editingFinished.connect(self.update_resolution)
        self._mw.linesSpinBox.editingFinished.connect(self.change_lines)
        self._mw.constDoubleSpinBox.editingFinished.connect(self.change_voltage)

        #
        self._mw.voltscan_cb_max_InputWidget.valueChanged.connect(self.refresh_matrix)
        self._mw.voltscan_cb_min_InputWidget.valueChanged.connect(self.refresh_matrix)
        self._mw.voltscan_cb_high_centile_InputWidget.valueChanged.connect(self.refresh_matrix)
        self._mw.voltscan_cb_low_centile_InputWidget.valueChanged.connect(self.refresh_matrix)

        # Connect signals
        self._voltscan_logic.sigUpdatePlots.connect(self.refresh_matrix)
        self._voltscan_logic.sigUpdatePlots.connect(self.refresh_plot)
        self._voltscan_logic.sigUpdatePlots.connect(self.refresh_lines)
        self._voltscan_logic.sigScanFinished.connect(self.scan_stopped)
        self._voltscan_logic.sigScanStarted.connect(self.scan_started)
        self._voltscan_logic.sigScanResumed.connect(self.scan_resumed)
        self._voltscan_logic.sigSpeedChanged.connect(self.update_inputs)
        self._voltscan_logic.sigResolutionChanged.connect(self.update_inputs)
        self._voltscan_logic.sigScanRangeChanged.connect(self.update_inputs)
        self._voltscan_logic.sigSpeedLimitChanged.connect(self.update_inputs)



        self.sigStartScan.connect(self._voltscan_logic.start_scanning)
        self.sigResumeScan.connect(self._voltscan_logic.resume_scanning)
        self.sigStopScan.connect(self._voltscan_logic.stop_scanning)
        self.sigChangeVoltage.connect(self._voltscan_logic.set_voltage)
        self.sigChangeRange.connect(self._voltscan_logic.set_scan_range)
        self.sigChangeSpeed.connect(self._voltscan_logic.set_scan_speed)
        self.sigChangeLines.connect(self._voltscan_logic.set_scan_lines)
        self.sigChangeResolution.connect(self._voltscan_logic.set_resolution)
        self.sigSaveMeasurement.connect(self._voltscan_logic.save_data)

        self._mw.action_run_stop.triggered.connect(self.run_stop)
        self._mw.action_Save.triggered.connect(self.save_data)
        self._mw.show()

    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def run_stop(self, is_checked):
        """ Manages what happens if scan is started/stopped """
        self._mw.action_run_stop.setEnabled(False)
        if is_checked:
            self.sigStartScan.emit()
            #self._mw.voltscan_ViewWidget.removeItem(self.scan_fit_image)
            #self._mw.voltscan2_ViewWidget.removeItem(self.scan_fit_image)
        else:
            self.sigStopScan.emit()

    def resume(self):
        """ Manages what happens if scan is started/stopped """
        #self._mw.action_run_stop.setEnabled(False)
        if self._mw.action_run_stop.isChecked():
            pass
            # self._mw.voltscan_ViewWidget.removeItem(self.scan_fit_image)
            # self._mw.voltscan2_ViewWidget.removeItem(self.scan_fit_image)
        else:
            self.sigResumeScan.emit()

    def scan_started(self):
        self._mw.action_run_stop.setEnabled(True)
        self._mw.action_run_stop.setChecked(True)


    def scan_resumed(self):
        self._mw.action_run_stop.setEnabled(True)
        self._mw.action_run_stop.setChecked(True)

    def scan_stopped(self):
        self._mw.action_run_stop.setEnabled(True)
        self._mw.action_run_stop.setChecked(False)
        self.refresh_plot()
        self.refresh_matrix()
        self.refresh_lines()

    def update_scan_range(self):
        if self._mw.action_run_stop.isChecked() == False:
            self.sigChangeRange.emit([self._mw.startDoubleSpinBox.value(),self._mw.stopDoubleSpinBox.value()])
        else:
            self._mw.action_run_stop.trigger()
            duration = abs(
                self._voltscan_logic.scan_range[0] - self._voltscan_logic.scan_range[1]) / self._voltscan_logic._scan_speed
            time.sleep(duration)
            self.sigChangeRange.emit([self._mw.startDoubleSpinBox.value(),self._mw.stopDoubleSpinBox.value()])

            self.resume()

    def update_scan_speed(self):
        if self._mw.action_run_stop.isChecked() == False:
            self.sigChangeSpeed.emit(self._mw.speedDoubleSpinBox.value())
        else:
            self._mw.action_run_stop.trigger()
            #self.scan_stopped()
            duration = abs(
                self._voltscan_logic.scan_range[0] - self._voltscan_logic.scan_range[
                    1]) / self._voltscan_logic._scan_speed
            time.sleep(duration)
            self.sigChangeSpeed.emit(self._mw.speedDoubleSpinBox.value())
            #self._voltscan_logic.resume_scanning()
            self.resume()

    def update_resolution(self):
        if self._mw.action_run_stop.isChecked() == False:
            self.sigChangeResolution.emit(self._mw.resolutionSpinBox.value())
        else:
            self._mw.action_run_stop.trigger()
            # self.scan_stopped()
            duration = abs(
                self._voltscan_logic.scan_range[0] - self._voltscan_logic.scan_range[
                    1]) / self._voltscan_logic._scan_speed
            time.sleep(duration)
            self.sigChangeResolution.emit(self._mw.resolutionSpinBox.value())
            self.resume()

    def refresh_plot(self):
        """ Refresh the xy-plot image """
        #self.scan_image.setData(self._voltscan_logic.plot_x, self._voltscan_logic.scan_matrix[self._voltscan_logic._scan_counter_up-1])
        self.scan_image.setData(
            np.concatenate(np.array(self._voltscan_logic.raw_matrix_voltage)[self._voltscan_logic._upwards_index_list]),
            np.concatenate(np.array(self._voltscan_logic.raw_matrix_counts)[self._voltscan_logic._upwards_index_list]))
        self.scan_fit_image.setData(self._voltscan_logic.fit_x, self._voltscan_logic.fit_y)
        #enableAutoRange(axis='y')
        #self.scan_fit_image.setRange(xRange=[min(self._voltscan_logic.fit_x),max(self._voltscan_logic.fit_x)])
        self.scan_fit_image2.setData(self._voltscan_logic.fit_x2, self._voltscan_logic.fit_y2)
        if len(self._voltscan_logic._downwards_index_list)>0:
            self.scan_image2.setData(
                np.concatenate(np.array(self._voltscan_logic.raw_matrix_voltage)[self._voltscan_logic._downwards_index_list]),
                np.concatenate(np.array(self._voltscan_logic.raw_matrix_counts)[self._voltscan_logic._downwards_index_list]))
        else:
            pass
        #self.scan_image2.setData(self._voltscan_logic.plot_x, self._voltscan_logic.scan_matrix2[self._voltscan_logic._scan_counter_up-1])

    def update_inputs(self):

        self._mw.startDoubleSpinBox.setValue(self._voltscan_logic.scan_range[0])
        self._mw.speedDoubleSpinBox.setValue(self._voltscan_logic._scan_speed)
        self._mw.speedDoubleSpinBox.setMaximum(self._voltscan_logic._speed_limit)
        self._mw.stopDoubleSpinBox.setValue(self._voltscan_logic.scan_range[1])
        self._mw.constDoubleSpinBox.setValue(self._voltscan_logic._static_v)
        self._mw.resolutionSpinBox.setValue(self._voltscan_logic.resolution)
        self._mw.linesSpinBox.setValue(self._voltscan_logic.number_of_repeats)

    def refresh_matrix(self):
        """ Refresh the xy-matrix image """
        scan_image_data = self._voltscan_logic.scan_matrix_new
        scan_image_data2 = self._voltscan_logic.scan_matrix2
        self.scan_matrix_image.setImage(scan_image_data, axisOrder='row-major')
        self.scan_matrix_image.setRect(
            QtCore.QRectF(
                self._voltscan_logic.a_range[0],
                0,
                self._voltscan_logic.a_range[1]-
                self._voltscan_logic.a_range[0],
                self._voltscan_logic.number_of_repeats)
            )
        self.scan_matrix_image2.setImage(scan_image_data2, axisOrder='row-major')
        self.scan_matrix_image2.setRect(
            QtCore.QRectF(
                self._voltscan_logic.a_range[0],
                0,
                self._voltscan_logic.a_range[1] - self._voltscan_logic.a_range[0],
                self._voltscan_logic.number_of_repeats)
        )
        self.refresh_scan_colorbar()



        # If "Centiles" is checked, adjust colour scaling automatically to centiles.
        # Otherwise, take user-defined values.
        if self._mw.voltscan_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.voltscan_cb_low_centile_InputWidget.value()
            high_centile = self._mw.voltscan_cb_high_centile_InputWidget.value()

            cb_min = np.percentile(scan_image_data, low_centile)
            cb_max = np.percentile(scan_image_data, high_centile)
        else:
            cb_min = self._mw.voltscan_cb_min_InputWidget.value()
            cb_max = self._mw.voltscan_cb_max_InputWidget.value()

        # Now update image with new color scale, and update colorbar
        self.scan_matrix_image.setImage(
            image=scan_image_data,
            levels=(cb_min, cb_max),
            axisOrder='row-major')

        scan_image_data2 = self._voltscan_logic.scan_matrix2
        # Now update image with new color scale, and update colorbar
        self.scan_matrix_image2.setImage(
            image=scan_image_data2,
            levels=(cb_min, cb_max),
            axisOrder='row-major')

        self.refresh_scan_colorbar()

    def refresh_scan_colorbar(self):
        """ Update the colorbar to a new scaling."""

        # If "Centiles" is checked, adjust colour scaling automatically to centiles.
        # Otherwise, take user-defined values.
        if self._mw.voltscan_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.voltscan_cb_low_centile_InputWidget.value()
            high_centile = self._mw.voltscan_cb_high_centile_InputWidget.value()

            cb_min = np.percentile(self.scan_matrix_image.image, low_centile)
            cb_max = np.percentile(self.scan_matrix_image.image, high_centile)
        else:
            cb_min = self._mw.voltscan_cb_min_InputWidget.value()
            cb_max = self._mw.voltscan_cb_max_InputWidget.value()

        self.scan_cb.refresh_colorbar(cb_min, cb_max)
        self._mw.voltscan_cb_ViewWidget.update()

    def refresh_lines(self):
        self._mw.elapsed_lines_DisplayWidget.display(self._voltscan_logic._scan_counter_up)

    def change_voltage(self):
        self.scan_stopped()
        self.sigChangeVoltage.emit(self._mw.constDoubleSpinBox.value())
        #self.scan_resumed()
    def change_start_volt(self):
        self.scan_stopped()
        if self._mw.startDoubleSpinBox.value()<self._mw.stopDoubleSpinBox.value():
            self.sigChangeRange.emit([
                self._mw.startDoubleSpinBox.value(),
                self._mw.stopDoubleSpinBox.value()
            ])
        else:
            self._mw.startDoubleSpinBox.setValue(self._voltscan_logic.scan_range[0])
            self.log.warn('start_value must be smaller than stop_value')
        #self.scan_resumed()


    def change_speed(self):
        self.scan_stopped()
        self.sigChangeSpeed.emit(self._mw.speedDoubleSpinBox.value())
        #self.scan_resumed()
    def change_stop_volt(self):
        self.scan_stopped()
        if self._mw.startDoubleSpinBox.value() < self._mw.stopDoubleSpinBox.value():
            self.sigChangeRange.emit([
                self._mw.startDoubleSpinBox.value(),
                self._mw.stopDoubleSpinBox.value()
            ])
        else:
            self._mw.stopDoubleSpinBox.setValue(self._voltscan_logic.scan_range[1])
            self.log.warn('start_value must be smaller than stop_value')
        #self.scan_resumed()
    def change_lines(self):

        self.sigChangeLines.emit(self._mw.linesSpinBox.value())

    def change_resolution(self):
        self.scan_stopped()
        self.sigChangeResolution.emit(self._mw.resolutionSpinBox.value())
        #self.scan_resumed()
    def get_matrix_cb_range(self):
        """
        Determines the cb_min and cb_max values for the matrix plot
        """
        matrix_image = self.scan_matrix_image.image

        # If "Manual" is checked or the image is empty (all zeros), then take manual cb range.
        # Otherwise, calculate cb range from percentiles.
        if self._mw.voltscan_cb_manual_RadioButton.isChecked() or np.max(matrix_image) < 0.1:
            cb_min = self._mw.voltscan_cb_min_InputWidget.value()
            cb_max = self._mw.voltscan_cb_max_InputWidget.value()
        else:
            # Exclude any zeros (which are typically due to unfinished scan)
            matrix_image_nonzero = matrix_image[np.nonzero(matrix_image)]

            # Read centile range
            low_centile = self._mw.voltscan_cb_low_centile_InputWidget.value()
            high_centile = self._mw.voltscan_cb_high_centile_InputWidget.value()

            cb_min = np.percentile(matrix_image_nonzero, low_centile)
            cb_max = np.percentile(matrix_image_nonzero, high_centile)

        cb_range = [cb_min, cb_max]
        return cb_range

    def save_data(self):
        """ Save the sum plot, the scan marix plot and the scan data """
        filetag = self._mw.save_tag_LineEdit.text()
        cb_range = self.get_matrix_cb_range()

        # Percentile range is None, unless the percentile scaling is selected in GUI.
        pcile_range = None
        if self._mw.voltscan_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.voltscan_cb_low_centile_InputWidget.value()
            high_centile = self._mw.voltscan_cb_high_centile_InputWidget.value()
            pcile_range = [low_centile, high_centile]

        self.sigSaveMeasurement.emit(filetag, cb_range, pcile_range)
