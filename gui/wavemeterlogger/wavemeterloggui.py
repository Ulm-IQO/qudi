# -*- coding: utf-8 -*-

"""
This file contains a gui to see wavemeter data during laser scanning.

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

import datetime
import numpy as np
import os
import pyqtgraph as pg
import pyqtgraph.exporters

from core.connector import Connector
from core.util import units
from gui.guibase import GUIBase
from gui.colordefs import QudiPalettePale as palette
from gui.fitsettings import FitSettingsDialog, FitSettingsComboBox
from qtpy import QtWidgets
from qtpy import QtCore
from qtpy import uic


class WavemeterLogWindow(QtWidgets.QMainWindow):
    def __init__(self):
        """ Create the laser scanner window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_scanwindow.ui')

        # Load it
        super(WavemeterLogWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()


class WavemeterLogGui(GUIBase):
    """
    This GUI is for PLE measurements, reading out a wavemeter
    """
    # declare connectors
    wavemeterloggerlogic = Connector(interface='WavemeterLoggerLogic')
    savelogic = Connector(interface='SaveLogic')

    sigStartCounter = QtCore.Signal()
    sigStopCounter = QtCore.Signal()
    sigFitChanged = QtCore.Signal(str)
    sigDoFit = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.debug('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """
        self._save_logic = self.savelogic()

        # setting up the window
        self._mw = WavemeterLogWindow()

        ## giving the plots names allows us to link their axes together
        self._pw = self._mw.plotWidget  # pg.PlotWidget(name='Counter1')
        self._plot_item = self._pw.plotItem

        ## create a new ViewBox, link the right axis to its coordinate system
        self._right_axis = pg.ViewBox()
        self._plot_item.showAxis('right')
        self._plot_item.scene().addItem(self._right_axis)
        self._plot_item.getAxis('right').linkToView(self._right_axis)
        self._right_axis.setXLink(self._plot_item)

        ## create a new ViewBox, link the right axis to its coordinate system
        self._top_axis = pg.ViewBox()
        self._plot_item.showAxis('top')
        self._plot_item.scene().addItem(self._top_axis)
        self._plot_item.getAxis('top').linkToView(self._top_axis)
        self._top_axis.setYLink(self._plot_item)
        self._top_axis.invertX(b=True)

        # handle resizing of any of the elements
        self._update_plot_views()
        self._plot_item.vb.sigResized.connect(self._update_plot_views)

        self._pw.setLabel('left', 'Fluorescence', units='counts/s')
        self._pw.setLabel('right', 'Number of Points', units='#')
        self._pw.setLabel('bottom', 'Wavelength', units='nm')
        self._pw.setLabel('top', 'Relative Frequency', units='Hz')

        self._mw.actionStop_resume_scan.triggered.connect(self.stop_resume_clicked)
        self._mw.actionSave_histogram.triggered.connect(self.save_clicked)
        self._mw.actionStart_scan.triggered.connect(self.start_clicked)
        self._mw.actionAuto_range.triggered.connect(self.set_auto_range)

        # defining the parameters to edit
        self._mw.binSpinBox.setValue(self.wavemeterloggerlogic().get_bins())
        self._mw.binSpinBox.editingFinished.connect(self.recalculate_histogram)

        self._mw.minDoubleSpinBox.setValue(self.wavemeterloggerlogic().get_min_wavelength())
        self._mw.minDoubleSpinBox.editingFinished.connect(self.recalculate_histogram)

        self._mw.maxDoubleSpinBox.setValue(self.wavemeterloggerlogic().get_max_wavelength())
        self._mw.maxDoubleSpinBox.editingFinished.connect(self.recalculate_histogram)

        self._mw.show()

        ## Create an empty plot curve to be filled later, set its pen
        self.curve_data_points = pg.PlotDataItem(
            pen=pg.mkPen(palette.c1),
            symbol=None
        )

        self.curve_nm_counts = pg.PlotDataItem(
            pen=pg.mkPen(palette.c2, style=QtCore.Qt.DotLine),
            symbol=None
        )

        self.curve_hz_counts = pg.PlotDataItem(
            pen=pg.mkPen(palette.c6, style=QtCore.Qt.DotLine),
            symbol=None
        )

        self.curve_envelope = pg.PlotDataItem(
            pen=pg.mkPen(palette.c3, style=QtCore.Qt.DotLine),
            symbol=None
        )

        self.curve_fit = pg.PlotDataItem(
            pen=pg.mkPen(palette.c2, width=3),
            symbol=None
        )

        self._pw.addItem(self.curve_data_points)
        self._pw.addItem(self.curve_envelope)
        self._right_axis.addItem(self.curve_nm_counts)
        self._top_axis.addItem(self.curve_hz_counts)

        # scatter plot for time series
        self._spw = self._mw.scatterPlotWidget
        self._spi = self._spw.plotItem
        self._spw.setLabel('bottom', 'Wavelength', units='nm')
        self._spw.setLabel('left', 'Time', units='s')
        self._scatterplot = pg.ScatterPlotItem(size=10, pen=pg.mkPen(None),
                                               brush=pg.mkBrush(255, 255, 255, 20))
        self._spw.addItem(self._scatterplot)
        self._spw.setXLink(self._plot_item)
        self.wavemeterloggerlogic().sig_new_data_point.connect(self.add_data_point)

        self.wavemeterloggerlogic().sig_data_updated.connect(self.updateData)
        self.wavemeterloggerlogic().sig_new_wavelength.connect(self._update_live_wavelength)

        # fit settings
        self._fsd = FitSettingsDialog(self.wavemeterloggerlogic().fc)
        self._fsd.sigFitsUpdated.connect(self._mw.fit_methods_ComboBox.setFitFunctions)
        self._fsd.applySettings()

        # Add save file tag input box
        self._mw.save_tag_LineEdit = QtWidgets.QLineEdit(self._mw)
        self._mw.save_tag_LineEdit.setMaximumWidth(500)
        self._mw.save_tag_LineEdit.setMinimumWidth(200)
        self._mw.save_tag_LineEdit.setToolTip('Enter a nametag which will be\n'
                                              'added to the filename.')
        self._mw.scanToolBar.addWidget(self._mw.save_tag_LineEdit)

        # Connect signals
        self._mw.actionFit_settings.triggered.connect(self._fsd.show)
        self._mw.do_fit_PushButton.clicked.connect(self.doFit)
        self.sigDoFit.connect(self.wavemeterloggerlogic().do_fit)
        self.sigFitChanged.connect(self.wavemeterloggerlogic().fc.set_current_fit)
        self.wavemeterloggerlogic().sig_fit_updated.connect(self.updateFit)

    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        self._mw.close()

    def show(self):
        """ Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def _update_live_wavelength(self, wavelength, intern_xmin, intern_xmax):
        self._mw.wavelengthLabel.setText('{0:,.6f} nm '.format(wavelength))
        self._mw.autoMinLabel.setText('Minimum: {0:3.6f} (nm)   '.format(intern_xmin))
        self._mw.autoMaxLabel.setText('Maximum: {0:3.6f} (nm)   '.format(intern_xmax))

    def updateData(self):
        """ The function that grabs the data and sends it to the plot.
        """

        x_axis = self.wavemeterloggerlogic().histogram_axis
        x_axis_hz = (
                3.0e17 / x_axis
                - 6.0e17 / (
                            self.wavemeterloggerlogic().get_max_wavelength() + self.wavemeterloggerlogic().get_min_wavelength())
        )

        plotdata = np.array(self.wavemeterloggerlogic().counts_with_wavelength)
        if len(plotdata.shape) > 1 and plotdata.shape[1] >= 3:
            self.curve_data_points.setData(plotdata[:, 2:0:-1])

        self.curve_nm_counts.setData(x=x_axis, y=self.wavemeterloggerlogic().histogram)
        self.curve_hz_counts.setData(x=x_axis_hz, y=self.wavemeterloggerlogic().histogram)
        self.curve_envelope.setData(x=x_axis, y=self.wavemeterloggerlogic().envelope_histogram)

    @QtCore.Slot()
    def doFit(self):
        self.sigFitChanged.emit(self._mw.fit_methods_ComboBox.getCurrentFit()[0])
        self.sigDoFit.emit()

    @QtCore.Slot()
    def updateFit(self):
        """ Do the configured fit and show it in the plot """
        fit_name = self.wavemeterloggerlogic().fc.current_fit
        fit_result = self.wavemeterloggerlogic().fc.current_fit_result
        fit_param = self.wavemeterloggerlogic().fc.current_fit_param

        if fit_result is not None:
            # display results as formatted text
            self._mw.fit_results_DisplayWidget.clear()
            try:
                formated_results = units.create_formatted_output(fit_result.result_str_dict)
            except:
                formated_results = 'this fit does not return formatted results'
            self._mw.fit_results_DisplayWidget.setPlainText(formated_results)

        if fit_name is not None:
            self._mw.fit_methods_ComboBox.setCurrentFit(fit_name)

        # check which fit method is used and show the curve in the plot accordingly
        if fit_name != 'No Fit':
            self.curve_fit.setData(
                x=self.wavemeterloggerlogic().wlog_fit_x,
                y=self.wavemeterloggerlogic().wlog_fit_y)

            if self.curve_fit not in self._mw.plotWidget.listDataItems():
                self._mw.plotWidget.addItem(self.curve_fit)
        else:
            if self.curve_fit in self._mw.plotWidget.listDataItems():
                self._mw.plotWidget.removeItem(self.curve_fit)

    def add_data_point(self, point):
        if len(point) >= 3:
            spts = [
                {'pos': (point[0], point[1]), 'size': 5, 'brush': pg.intColor(point[2] / 100, 255)}]
            self._scatterplot.addPoints(spts)

    def stop_resume_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        # If running, then we stop the measurement and enable inputs again
        if self.wavemeterloggerlogic().module_state() == 'running':
            self._mw.actionStop_resume_scan.setText('Resume')
            self.wavemeterloggerlogic().stop_scanning()
            self._mw.actionStop_resume_scan.setEnabled(True)
            self._mw.actionStart_scan.setEnabled(True)
            self._mw.binSpinBox.setEnabled(True)
        # Otherwise, we start a measurement and disable some inputs.
        else:
            self._mw.actionStop_resume_scan.setText('Stop')
            self.wavemeterloggerlogic().start_scanning(resume=True)
            self._mw.actionStart_scan.setEnabled(False)
            self._mw.binSpinBox.setEnabled(False)

    def start_clicked(self):
        """ Handling resume of the scanning without resetting the data.
        """
        if self.wavemeterloggerlogic().module_state() == 'idle':
            self._scatterplot.clear()
            self.wavemeterloggerlogic().start_scanning()

            # Enable the stop button once a scan starts.
            self._mw.actionStop_resume_scan.setText('Stop')
            self._mw.actionStop_resume_scan.setEnabled(True)
            self._mw.actionStart_scan.setEnabled(False)
            self._mw.binSpinBox.setEnabled(False)
            self.recalculate_histogram()
        else:
            self.log.error('Cannot scan, since a scan is already running.')

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
        """
        filetag = self._mw.save_tag_LineEdit.text()
        self.wavemeterloggerlogic().save_data(filetag)

    def recalculate_histogram(self):
        self.wavemeterloggerlogic().recalculate_histogram(
            bins=self._mw.binSpinBox.value(),
            xmin=self._mw.minDoubleSpinBox.value(),
            xmax=self._mw.maxDoubleSpinBox.value()
        )

    def set_auto_range(self):
        self._mw.minDoubleSpinBox.setValue(self.wavemeterloggerlogic().intern_xmin)
        self._mw.maxDoubleSpinBox.setValue(self.wavemeterloggerlogic().intern_xmax)
        self.recalculate_histogram()

    ## Handle view resizing
    def _update_plot_views(self):
        ## view has resized; update auxiliary views to match
        self._right_axis.setGeometry(self._plot_item.vb.sceneBoundingRect())
        self._top_axis.setGeometry(self._plot_item.vb.sceneBoundingRect())

        ## need to re-update linked axes since this was called
        ## incorrectly while views had different shapes.
        ## (probably this should be handled in ViewBox.resizeEvent)
        self._right_axis.linkedViewChanged(self._plot_item.vb, self._right_axis.XAxis)
        self._top_axis.linkedViewChanged(self._plot_item.vb, self._top_axis.YAxis)
