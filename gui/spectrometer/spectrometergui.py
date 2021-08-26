# -*- coding: utf-8 -*-
"""
This module contains a GUI for operating the spectrum logic module.

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
import numpy as np

from core.connector import Connector
from core.util import units
from gui.colordefs import QudiPalettePale as palette
from gui.guibase import GUIBase
from gui.fitsettings import FitSettingsDialog, FitSettingsComboBox
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic


class SpectrometerWindow(QtWidgets.QMainWindow):

    def __init__(self):
        """ Create the laser scanner window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_spectrometer.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class SpectrometerGui(GUIBase):
    """
    """

    # declare connectors
    spectrumlogic = Connector(interface='SpectrumLogic')
    sigRecordSpectrum = QtCore.Signal(bool)
    
    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """

        self._spectrum_logic = self.spectrumlogic()

        # setting up the window
        self._mw = SpectrometerWindow()

        #Vlad updates
        self.sigRecordSpectrum.connect(self._spectrum_logic.get_single_spectrum)
        self._mw.integration_time_doubleSpinBox.editingFinished.connect(self.update_integration_time)
        self.update_integration_time()

        # ... 
        self._mw.stop_diff_spec_Action.setEnabled(False)
        self._mw.resume_diff_spec_Action.setEnabled(False)
        self._mw.correct_background_Action.setChecked(self._spectrum_logic.background_correction)

        # giving the plots names allows us to link their axes together
        self._pw = self._mw.plotWidget  # pg.PlotWidget(name='Counter1')
        
        self._plot_item = self._pw.plotItem
        self._plot_item.scene().sigMouseClicked.connect(self.onClick)
        self.vb = self._plot_item.vb
        # create a new ViewBox, link the right axis to its coordinate system
        self._right_axis = pg.ViewBox()
        self._plot_item.showAxis('right')
        self._plot_item.scene().addItem(self._right_axis)
        self._plot_item.getAxis('right').linkToView(self._right_axis)
        self._right_axis.setXLink(self._plot_item)

        # create a new ViewBox, link the right axis to its coordinate system
        self._top_axis = pg.ViewBox()
        self._plot_item.showAxis('top')
        self._plot_item.scene().addItem(self._top_axis)
        self._plot_item.getAxis('top').linkToView(self._top_axis)
        self._top_axis.setYLink(self._plot_item)
        self._top_axis.invertX(b=True)

        # handle resizing of any of the elements

        self._pw.setLabel('left', 'Fluorescence', units='counts/s')
        self._pw.setLabel('right', 'Number of Points', units='#')
        self._pw.setLabel('bottom', 'Wavelength', units='m')
        self._pw.setLabel('top', 'Relative Frequency', units='Hz')

        # Create an empty plot curve to be filled later, set its pen
        self._curve1 = self._pw.plot()
        self._curve1.setPen(palette.c1, width=2)

        self._curve2 = self._pw.plot()
        self._curve2.setPen(palette.c2, width=2)
        self.set_plot_domain()
        self.update_data()

        # Connect singals
        self._mw.rec_single_spectrum_Action.triggered.connect(self.record_single_spectrum)
        self._mw.start_diff_spec_Action.triggered.connect(self.start_differential_measurement)
        self._mw.stop_diff_spec_Action.triggered.connect(self.stop_differential_measurement)
        self._mw.resume_diff_spec_Action.triggered.connect(self.resume_differential_measurement)

        self._mw.save_spectrum_Action.triggered.connect(self.save_spectrum_data)
        self._mw.correct_background_Action.triggered.connect(self.correct_background)
        self._mw.acquire_background_Action.triggered.connect(self.acquire_background)
        self._mw.save_background_Action.triggered.connect(self.save_background_data)

        self._mw.restore_default_view_Action.triggered.connect(self.restore_default_view)

        self._spectrum_logic.sig_specdata_updated.connect(self.update_data)
        self._spectrum_logic.spectrum_fit_updated_Signal.connect(self.update_fit)
        self._spectrum_logic.fit_domain_updated_Signal.connect(self.update_fit_domain)
        
        
 
        self._mw.show()

        self._save_PNG = True

        # Internal user input changed signals
        self._mw.fit_domain_min_doubleSpinBox.valueChanged.connect(self.set_fit_domain)
        self._mw.fit_domain_max_doubleSpinBox.valueChanged.connect(self.set_fit_domain)

        self._mw.spec_range_left_doubleSpinBox.valueChanged.connect(self.set_plot_domain)
        self._mw.spec_range_right_doubleSpinBox.valueChanged.connect(self.set_plot_domain)

        # Internal trigger signals
        self._mw.do_fit_PushButton.clicked.connect(self.do_fit)
        self._mw.fit_domain_all_data_pushButton.clicked.connect(self.reset_fit_domain_all_data)

        # fit settings
        self._fsd = FitSettingsDialog(self._spectrum_logic.fc)
        self._fsd.sigFitsUpdated.connect(self._mw.fit_methods_ComboBox.setFitFunctions)
        self._fsd.applySettings()
        self._mw.action_FitSettings.triggered.connect(self._fsd.show)

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        # disconnect signals
        self._fsd.sigFitsUpdated.disconnect()

        self._mw.close()

    def onClick(self, event):
        items = self._plot_item.scene().items(event.scenePos())
        mousePoint = self.vb.mapSceneToView(event._scenePos)
        print(mousePoint.x(), mousePoint.y())
        # if self._plot_item.sceneBoundingRect().contains(event._scenePos):
        #     mousePoint = self.vb.mapSceneToView(event._scenePos)
        #     index = int(mousePoint.x())
        #     print(index, mousePoint.x(), mousePoint.y())
        #     data = self._spectrum_logic.spectrum_data
        #     lam, spec = data[0, :], data[1, :]
        #     if index > 0 and index < len(self._spectrum_logic.spectrum_data):
        #         self.label.setText(
        #             "<span style='font-size: 12pt'>x=%0.1f,   <span style='color: red'>y1=%0.1f</span>,   <span style='color: green'>y2=%0.1f</span>" % (
        #             mousePoint.x(), lam[index], spec[index]))

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def update_data(self):
        """ The function that grabs the data and sends it to the plot.
        """
        data = self._spectrum_logic.spectrum_data

        # erase previous fit line
        self._curve2.setData(x=[], y=[])
        
        # draw new data
        lam, spec = data[0, :], data[1, :]
        plot_range = (lam > self.plot_domain[0]) * (lam < self.plot_domain[1])
        self._curve1.setData(x=lam[plot_range], y=spec[plot_range])

    def update_fit(self, fit_data, result_str_dict, current_fit):
        """ Update the drawn fit curve and displayed fit results.
        """
        if current_fit != 'No Fit':
            # display results as formatted text
            self._mw.spectrum_fit_results_DisplayWidget.clear()
            try:
                formated_results = units.create_formatted_output(result_str_dict)
            except:
                formated_results = 'this fit does not return formatted results'
            self._mw.spectrum_fit_results_DisplayWidget.setPlainText(formated_results)

            # redraw the fit curve in the GUI plot.
            self._curve2.setData(x=fit_data[0, :], y=fit_data[1, :])

    def record_single_spectrum(self, background=False):
        """ Handle resume of the scanning without resetting the data.
        """
        int_time = self._mw.integration_time_doubleSpinBox.value()
        self.time_passed = 0
        self._mw.progressBar.setMaximum(int_time)
        self.sigRecordSpectrum.emit(background)
        self._mw.rec_single_spectrum_Action.setEnabled(False)
        self._mw.acquire_background_Action.setEnabled(False)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updateProgress)
        self.update_time = 500
        self.timer.start(self.update_time)
    
    def updateProgress(self):
        int_time = self._mw.integration_time_doubleSpinBox.value()
        self.time_passed += self.update_time/1000
        if self.time_passed > int_time:
            self.timer.stop()
            self._mw.progressBar.setValue(int_time)
            self._mw.rec_single_spectrum_Action.setEnabled(True)
            self._mw.acquire_background_Action.setEnabled(True)
            self.update_data()
            return
        self._mw.progressBar.setValue(self.time_passed)


    def update_integration_time(self):
        int_time = self._mw.integration_time_doubleSpinBox.value()
        self._spectrum_logic.update_integration_time(int_time)

    def start_differential_measurement(self):

        # Change enabling of GUI actions
        self._mw.stop_diff_spec_Action.setEnabled(True)
        self._mw.start_diff_spec_Action.setEnabled(False)
        self._mw.rec_single_spectrum_Action.setEnabled(False)
        self._mw.resume_diff_spec_Action.setEnabled(False)

        self._spectrum_logic.start_differential_spectrum()

    def stop_differential_measurement(self):
        self._spectrum_logic.stop_differential_spectrum()

        # Change enabling of GUI actions
        self._mw.stop_diff_spec_Action.setEnabled(False)
        self._mw.start_diff_spec_Action.setEnabled(True)
        self._mw.rec_single_spectrum_Action.setEnabled(True)
        self._mw.resume_diff_spec_Action.setEnabled(True)

    def resume_differential_measurement(self):
        self._spectrum_logic.resume_differential_spectrum()

        # Change enabling of GUI actions
        self._mw.stop_diff_spec_Action.setEnabled(True)
        self._mw.start_diff_spec_Action.setEnabled(False)
        self._mw.rec_single_spectrum_Action.setEnabled(False)
        self._mw.resume_diff_spec_Action.setEnabled(False)

    def save_spectrum_data(self):
        self._spectrum_logic.save_spectrum_data()

    def correct_background(self):
        self._spectrum_logic.background_correction = self._mw.correct_background_Action.isChecked()

    def acquire_background(self):
        self.record_single_spectrum(background=True)
        # self._spectrum_logic.get_single_spectrum(background=True)

    def save_background_data(self):
        self._spectrum_logic.save_spectrum_data(background=True)

    def set_plot_domain(self):
       lambda_min = self._mw.spec_range_left_doubleSpinBox.value()  #nm
       lambda_max = self._mw.spec_range_right_doubleSpinBox.value()  #nm

       self.plot_domain = np.array([lambda_min, lambda_max])


    def do_fit(self):
        """ Command spectrum logic to do the fit with the chosen fit function.
        """
        fit_function = self._mw.fit_methods_ComboBox.getCurrentFit()[0]
        self._spectrum_logic.do_fit(fit_function)

    def set_fit_domain(self):
        """ Set the fit domain in the spectrum logic to values given by the GUI spinboxes.
        """
        lambda_min = self._mw.fit_domain_min_doubleSpinBox.value()
        lambda_max = self._mw.fit_domain_max_doubleSpinBox.value()

        new_fit_domain = np.array([lambda_min, lambda_max])

        self._spectrum_logic.set_fit_domain(new_fit_domain)

    def reset_fit_domain_all_data(self):
        """ Reset the fit domain to match the full data set.
        """
        self._spectrum_logic.set_fit_domain()

    def update_fit_domain(self, domain):
        """ Update the displayed fit domain to new values (set elsewhere).
        """
        self._mw.fit_domain_min_doubleSpinBox.setValue(domain[0])
        self._mw.fit_domain_max_doubleSpinBox.setValue(domain[1])

    def restore_default_view(self):
        """ Restore the arrangement of DockWidgets to the default
        """
        # Show any hidden dock widgets
        self._mw.spectrum_fit_dockWidget.show()

        # re-dock any floating dock widgets
        self._mw.spectrum_fit_dockWidget.setFloating(False)

        # Arrange docks widgets
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(QtCore.Qt.TopDockWidgetArea),
                               self._mw.spectrum_fit_dockWidget
                               )

        # Set the toolbar to its initial top area
        self._mw.addToolBar(QtCore.Qt.TopToolBarArea,
                            self._mw.measure_ToolBar)
        self._mw.addToolBar(QtCore.Qt.TopToolBarArea,
                            self._mw.background_ToolBar)
        self._mw.addToolBar(QtCore.Qt.TopToolBarArea,
                            self._mw.differential_ToolBar)
        return 0