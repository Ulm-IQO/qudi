# -*- coding: utf-8 -*-

"""
This file contains the Qudi aom & psat gui.

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
from gui.colordefs import QudiPalettePale as palette
from gui.guibase import GUIBase
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic



class AomMainWindow(QtWidgets.QMainWindow):

    """ Create the Main Window based on the *.ui file. """

    def __init__(self, **kwargs):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_aom.ui')

        # Load it
        super().__init__(**kwargs)
        uic.loadUi(ui_file, self)
        self.show()


class AomGui(GUIBase):

    """ FIXME: Please document
    """
    _modclass = 'aomgui'
    _modtype = 'gui'

    # declare connectors
    aomlogic = Connector(interface='AomLogic')

    sigPsatFinished = QtCore.Signal()
    sigAomChange = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """

        self._aom_logic = self.get_connector('aomlogic')

        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = AomMainWindow()

        self.psat_image = pg.PlotDataItem(self._aom_logic.powers,
                                          self._aom_logic.psat_data,
                                          pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                                          symbol='o',
                                          symbolPen=palette.c1,
                                          symbolBrush=palette.c1,
                                          symbolSize=7)

        self.psat_fit_image = pg.PlotDataItem(self._aom_logic.psat_fit_x,
                                              self._aom_logic.psat_fit_y,
                                              pen=pg.mkPen(palette.c2))

        # Add the display item to the xy and xz ViewWidget, which was defined in the UI file.
        self._mw.psat_plot_PlotWidget.addItem(self.psat_image)
        self._mw.psat_plot_PlotWidget.addItem(self.psat_fit_image)
        self._mw.psat_plot_PlotWidget.setLabel(axis='left', text='Fluoresence', units='c/s')
        self._mw.psat_plot_PlotWidget.setLabel(axis='bottom', text='Power', units='W')
        self._mw.psat_plot_PlotWidget.showGrid(x=True, y=True, alpha=0.8)
        self._mw.setPower.setValue(self.get_power())
        self._mw.setPower.valueChanged.connect(self.set_power)
        self._mw.setPower.setMaximum(self._aom_logic.current_maximum_power()*1000)
        self._mw.set_to_psat.clicked.connect(self.set_power_to_psat)
        self._aom_logic.power_available.connect(self.update_power_available)

        #####################
        # Connecting user interactions
        self._mw.run_psat_Action.triggered.connect(self.run_psat_clicked)
        self._mw.save_psat_Action.triggered.connect(self.save_clicked)

        ##################
        # Handling signals from the logic
        self._aom_logic.psat_updated.connect(self.update_data)
        self._aom_logic.psat_fit_updated.connect(self.update_fit)
        self._aom_logic.aom_updated.connect(self.update_aom)

        return 0

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()
        return

    def on_deactivate(self):
        """ Deactivate the module
        """
        # disconnect signals
        self._mw.run_psat_Action.triggered.disconnect()
        self._mw.save_psat_Action.triggered.disconnect()
        self._aom_logic.psat_updated.disconnect()
        self._mw.close()
        return

    def update_aom(self):
        self._mw.setPower.blockSignals(True)
        self._mw.setPower.setValue(self.get_power())
        self._mw.setPower.blockSignals(False)

    def set_power_to_psat(self):
        self._aom_logic.set_power(self._aom_logic.fitted_Psat)

    def update_data(self):
        """ The function that grabs the data and sends it to the plot.
        """

        """ Refresh the plot widgets with new data. """
        # Update psat plot
        self.psat_image.setData(self._aom_logic.powers, self._aom_logic.psat_data)

        return 0

    def set_power(self,power):
        self._aom_logic.set_power(power/1000)

    def get_power(self):
        return self._aom_logic.get_power()*1000

    def update_fit(self):
        """ Refresh the plot widgets with new data. """
        if self._aom_logic.psat_fit_available():
            # Update psat plot
            self.psat_fit_image.setData(self._aom_logic.psat_fit_x, self._aom_logic.psat_fit_y)
            self._mw.Isat_display.setText("{:.2f}".format(self._aom_logic.fitted_Isat/1000))
            self._mw.Psat_display.setText("{:.2f}".format(self._aom_logic.fitted_Psat*1000))
            self._mw.bg_display.setText("{:.2f}".format(self._aom_logic.fitted_offset/1000))


    def run_psat_clicked(self):
        """ Handling the Start button
        """
        self.log.info("Running psat")
        self._aom_logic.run_psat()
        return self._aom_logic.module_state()

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
        """
        if self._aom_logic.psat_available():
            self._aom_logic.save_psat()
        return self._aom_logic.module_state()

    def update_max_power(self, count_length):
        """Function to ensure that the GUI displays the current value of the logic

        @param int count_length: adjusted count length in bins
        @return int count_length: see above
        """
        self._mw.setPower.blockSignals(True)
        self._mw.count_length_SpinBox.setValue(count_length)
        self._pw.setXRange(0, count_length / self._counting_logic.get_count_frequency())
        self._mw.count_length_SpinBox.blockSignals(False)
        return count_length

    def update_power_available(self, state):
        pass

    def update_saving_Action(self, start):
        pass