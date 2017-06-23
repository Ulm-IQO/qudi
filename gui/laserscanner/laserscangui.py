# -*- coding: utf-8 -*-

"""
This file contains a gui to see laser scanning data.

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
import pyqtgraph as pg
import pyqtgraph.exporters
import time

from core.module import Connector
from gui.guibase import GUIBase
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic


class LaserScanWindow(QtWidgets.QMainWindow):
    def __init__(self):
        """ Create the laser scanner window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_scanwindow.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class LaserScanningGui(GUIBase):
    _modclass = 'LaserScanningGUi'
    _modtype = 'gui'

    ## declare connectors
    laserscanninglogic1 = Connector(interface='LaserScanningLogic')
    savelogic = Connector(interface='SaveLogic')

    sigStartCounter = QtCore.Signal()
    sigStopCounter = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.debug('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key,config[key]))


    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """

        self._scanning_logic = self.get_connector('laserscanninglogic1')
        self._save_logic = self.get_connector('savelogic')

        # setting up the window
        self._mw = LaserScanWindow()

        ## giving the plots names allows us to link their axes together
        self._pw = self._mw.plotWidget # pg.PlotWidget(name='Counter1')
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
        self._mw.binSpinBox.setValue(self._scanning_logic.get_bins())
        self._mw.binSpinBox.editingFinished.connect(self.recalculate_histogram)

        self._mw.minDoubleSpinBox.setValue(self._scanning_logic.get_min_wavelength())
        self._mw.minDoubleSpinBox.editingFinished.connect(self.recalculate_histogram)

        self._mw.maxDoubleSpinBox.setValue(self._scanning_logic.get_max_wavelength())
        self._mw.maxDoubleSpinBox.editingFinished.connect(self.recalculate_histogram)

        self._mw.show()

        ## Create an empty plot curve to be filled later, set its pen
        self._curve1 = self._pw.plot()
        self._curve1.setPen({'color': '0F0', 'width': 2})

        self._curve2 = pg.PlotCurveItem()
        self._curve2.setPen({'color': 'F00', 'width': 1})
        self._right_axis.addItem(self._curve2)

        self._curve3 = pg.PlotCurveItem()
        self._curve3.setPen({'color': '00A', 'width': 0.2})
        self._top_axis.addItem(self._curve3)

        self._curve4 = pg.PlotCurveItem()
        self._curve4.setPen({'color': 'F0F', 'width': 1})
        self._pw.addItem(self._curve4)

        self._save_PNG = True

        # scatter plot for time series
        self._spw = self._mw.scatterPlotWidget
        self._spi = self._spw.plotItem
        self._spw.setLabel('bottom', 'Wavelength', units='nm')
        self._spw.setLabel('left', 'Time', units='s')
        self._scatterplot =  pg.ScatterPlotItem(size=10, pen=pg.mkPen(None), brush=pg.mkBrush(255, 255, 255, 20))
        self._spw.addItem(self._scatterplot)
        self._spw.setXLink(self._plot_item)
        self._scanning_logic.sig_new_data_point.connect(self.add_data_point)

        self._scanning_logic.sig_data_updated.connect(self.updateData)

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

    def updateData(self):
        """ The function that grabs the data and sends it to the plot.
        """
        self._mw.wavelengthLabel.setText('{0:,.6f} nm '.format(self._scanning_logic.current_wavelength))
        self._mw.autoMinLabel.setText('Minimum: {0:3.6f} (nm)   '.format(self._scanning_logic.intern_xmin))
        self._mw.autoMaxLabel.setText('Maximum: {0:3.6f} (nm)   '.format(self._scanning_logic.intern_xmax))

        x_axis = self._scanning_logic.histogram_axis
        x_axis_hz = 3.0e17 / (x_axis) - 6.0e17 / (self._scanning_logic.get_max_wavelength() + self._scanning_logic.get_min_wavelength())

        self._curve1.setData(y=self._scanning_logic.histogram, x=x_axis)
        self._curve2.setData(y=self._scanning_logic.sumhisto, x=x_axis)
        self._curve3.setData(y=self._scanning_logic.histogram, x=x_axis_hz)
        self._curve4.setData(y=self._scanning_logic.envelope_histogram, x=x_axis)

        if self._scanning_logic.getState() == 'running':
            self._mw.actionStop_resume_scan.setText('Stop')
            self._mw.actionStart_scan.setEnabled(False)
        else:
            self._mw.actionStop_resume_scan.setText('Resume')
            self._mw.actionStart_scan.setEnabled(True)

    def add_data_point(self, point):
        if len(point) >= 3 :
            spts = [{'pos': (point[0], point[1]), 'size': 5, 'brush':pg.intColor( point[2]/100, 255)}]
            self._scatterplot.addPoints(spts)
            #print(point)

    def stop_resume_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        if self._scanning_logic.getState() == 'running':
            self._mw.actionStop_resume_scan.setText('Resume')
            self._scanning_logic.stop_scanning()
            self._mw.actionStop_resume_scan.setEnabled(True)
            self._mw.binSpinBox.setEnabled(True)
        else:
            self._mw.actionStop_resume_scan.setText('Stop')
            self._scanning_logic.start_scanning(resume=True)
            self._mw.actionStart_scan.setEnabled(False)
            self._mw.binSpinBox.setEnabled(False)

    def start_clicked(self):
        """ Handling resume of the scanning without resetting the data.
        """
        if self._scanning_logic.getState() == 'idle':
            self._scatterplot.clear()
            self._scanning_logic.start_scanning()

            # Enable the stop button once a scan starts.
            self._mw.actionStop_resume_scan.setEnabled(True)
            self._mw.binSpinBox.setEnabled(False)
            self.recalculate_histogram()
        else:
            self.log.error('Cannot scan, since a scan is alredy running')

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
        """

        filepath = self._save_logic.get_path_for_module(module_name='LaserScanning')
        filename = os.path.join(filepath, time.strftime('%Y%m%d-%H%M-%S_laser_scan_thumbnail'))

        exporter = pg.exporters.SVGExporter(self._pw.plotItem)
        exporter.export(filename+'.svg')

        if self._save_PNG:
            exporter = pg.exporters.ImageExporter(self._pw.plotItem)
            exporter.export(filename+'.png')

        self._scanning_logic.save_data()

    def recalculate_histogram(self):
        self._scanning_logic.recalculate_histogram(
            bins = self._mw.binSpinBox.value(),
            xmin = self._mw.minDoubleSpinBox.value(),
            xmax = self._mw.maxDoubleSpinBox.value()
        )

    def set_auto_range(self):
        self._mw.minDoubleSpinBox.setValue(self._scanning_logic.intern_xmin)
        self._mw.maxDoubleSpinBox.setValue(self._scanning_logic.intern_xmax)
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

