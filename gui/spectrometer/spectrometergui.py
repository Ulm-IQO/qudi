# -*- coding: utf-8 -*-
"""
This module contains a GUI for operating the spectrum logic module.

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

from gui.guibase import GUIBase
from gui.colordefs import QudiPalettePale as palette
import pyqtgraph as pg
from qtpy import QtWidgets
from qtpy import uic
import os


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
    _modclass = 'SpectrometerGui'
    _modtype = 'gui'

    # declare connectors
    _in = {'spectrumlogic1': 'SpectrumLogic'
           }

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))

    def on_activate(self, e=None):
        """ Definition and initialisation of the GUI.

        @param object e: Fysom.event object from Fysom class.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """

        self._spectrum_logic = self.connector['in']['spectrumlogic1']['object']

        # setting up the window
        self._mw = SpectrometerWindow()

        self._mw.stop_diff_spec_Action.setEnabled(False)
        self._mw.resume_diff_spec_Action.setEnabled(False)

        # giving the plots names allows us to link their axes together
        self._pw = self._mw.plotWidget  # pg.PlotWidget(name='Counter1')
        self._plot_item = self._pw.plotItem

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
        self._pw.setLabel('bottom', 'Wavelength', units='nm')
        self._pw.setLabel('top', 'Relative Frequency', units='Hz')

        self._mw.rec_single_spectrum_Action.triggered.connect(self.record_single_spectrum)
        self._mw.start_diff_spec_Action.triggered.connect(self.start_differential_measurement)
        self._mw.stop_diff_spec_Action.triggered.connect(self.stop_differential_measurement)
        self._mw.resume_diff_spec_Action.triggered.connect(self.resume_differential_measurement)

        self._mw.save_spectrum_Action.triggered.connect(self.save_spectrum_data)

        self._spectrum_logic.sig_specdata_updated.connect(self.updateData)

        self._mw.show()

        # Create an empty plot curve to be filled later, set its pen
        self._curve1 = self._pw.plot()
        self._curve1.setPen(palette.c2, width=2)

        self._save_PNG = True

    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        self._mw.close()

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def updateData(self):
        """ The function that grabs the data and sends it to the plot.
        """
        data = self._spectrum_logic.spectrum_data

        self._curve1.setData(x=data[0, :], y=data[1, :])

    def record_single_spectrum(self):
        """ Handling resume of the scanning without resetting the data.
        """
        self._spectrum_logic.get_single_spectrum()

        self.updateData()

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
