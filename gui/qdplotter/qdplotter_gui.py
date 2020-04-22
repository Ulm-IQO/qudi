# -*- coding: utf-8 -*-

"""
This file contains a Qudi gui module for quick plotting.

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
import numpy as np
from itertools import cycle
from qtpy import QtWidgets
from qtpy import QtCore
from qtpy import uic

from core.connector import Connector
from gui.guibase import GUIBase
from gui.fitsettings import FitSettingsDialog


class QDPlotMainWindow(QtWidgets.QMainWindow):

    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_qdplotter.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class QDPlotterGui(GUIBase):
    """ FIXME: Please document
    """
    # declare connectors
    qdplotlogic = Connector(interface='QDPlotLogic')

    sigStartCounter = QtCore.Signal()
    sigStopCounter = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._plot_logic = None
        self._mw = None
        self._fsd_1 = None
        self._pen_colors = cycle(['b', 'y', 'm', 'g'])
        self._plot_1_curves = []
        self._fit_1_curves = []

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """

        self._plot_logic = self.qdplotlogic()

        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = QDPlotMainWindow()

        # Setup dock widgets
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)

        #####################
        # Connecting user interactions
        self._mw.parameter_1_x_lower_limit_DoubleSpinBox.valueChanged.connect(self.parameter_1_x_limits_changed)
        self._mw.parameter_1_x_upper_limit_DoubleSpinBox.valueChanged.connect(self.parameter_1_x_limits_changed)
        self._mw.parameter_1_y_lower_limit_DoubleSpinBox.valueChanged.connect(self.parameter_1_y_limits_changed)
        self._mw.parameter_1_y_upper_limit_DoubleSpinBox.valueChanged.connect(self.parameter_1_y_limits_changed)

        self._mw.parameter_1_x_label_lineEdit.editingFinished.connect(self.parameter_1_x_label_changed)
        self._mw.parameter_1_x_unit_lineEdit.editingFinished.connect(self.parameter_1_x_label_changed)
        self._mw.parameter_1_y_label_lineEdit.editingFinished.connect(self.parameter_1_y_label_changed)
        self._mw.parameter_1_y_unit_lineEdit.editingFinished.connect(self.parameter_1_y_label_changed)

        self._mw.parameter_1_x_auto_PushButton.clicked.connect(self.parameter_1_x_auto_clicked)
        self._mw.parameter_1_y_auto_PushButton.clicked.connect(self.parameter_1_y_auto_clicked)
        self._mw.plot_1_save_pushButton.clicked.connect(self.save_clicked)

        # Fit settings dialogs
        self._fsd_1 = FitSettingsDialog(self._plot_logic.plot_1_fit_container)
        self._fsd_1.applySettings()
        self._mw.fit_1_comboBox.setFitFunctions(self._fsd_1.currentFits)
        self._mw.fit_settings_Action.triggered.connect(self._fsd_1.show)
        self._fsd_1.sigFitsUpdated.connect(self._mw.fit_1_comboBox.setFitFunctions)
        self._mw.fit_1_pushButton.clicked.connect(self.fit_1_clicked)

        # Connect the default view action
        self._mw.restore_default_view_Action.triggered.connect(self.restore_default_view)

        #####################
        self._plot_logic.sigPlotDataUpdated.connect(self.update_data)
        self._plot_logic.sigPlotParamsUpdated.connect(self.update_plot)
        self._plot_logic.sigFit1Updated.connect(self.fit_1_updated)

        self.update_data()
        self.update_plot()

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def on_deactivate(self):
        # FIXME: !
        """ Deactivate the module
        """
        self._mw.close()

    def update_data(self):
        """ Function creates empty plots, grabs the data and sends it to them.
        """

        if self._plot_logic.plot_1_clear_old_data:
            self._mw.plot_1_PlotWidget.clear()

        self._plot_1_curves = []
        self._fit_1_curves = []
        for line in range(len(self._plot_logic.plot_1_y_data)):
            self._plot_1_curves.append(self._mw.plot_1_PlotWidget.plot())
            self._plot_1_curves[line].setPen(next(self._pen_colors))
            self._plot_1_curves[line].setData(x=self._plot_logic.plot_1_x_data[line],
                                              y=self._plot_logic.plot_1_y_data[line])
            self._fit_1_curves.append(self._mw.plot_1_PlotWidget.plot())
            self._fit_1_curves[line].setPen('r')
            self._fit_1_curves[line].setData(y=[0, 1],
                                             x=[0, 1])

    def update_plot(self):
        self._mw.plot_1_PlotWidget.setXRange(self._plot_logic.plot_1_x_limits[0], self._plot_logic.plot_1_x_limits[1])
        self._mw.plot_1_PlotWidget.setYRange(self._plot_logic.plot_1_y_limits[0], self._plot_logic.plot_1_y_limits[1])
        self._mw.plot_1_PlotWidget.setLabel('bottom', self._plot_logic.plot_1_x_label,
                                            units=self._plot_logic.plot_1_x_unit)
        self._mw.plot_1_PlotWidget.setLabel('left', self._plot_logic.plot_1_y_label,
                                            units=self._plot_logic.plot_1_y_unit)

        # Update display in gui if plot params are changed by script access to logic
        self._mw.parameter_1_x_lower_limit_DoubleSpinBox.blockSignals(True)
        self._mw.parameter_1_x_upper_limit_DoubleSpinBox.blockSignals(True)
        self._mw.parameter_1_y_lower_limit_DoubleSpinBox.blockSignals(True)
        self._mw.parameter_1_y_upper_limit_DoubleSpinBox.blockSignals(True)
        self._mw.parameter_1_x_label_lineEdit.blockSignals(True)
        self._mw.parameter_1_x_unit_lineEdit.blockSignals(True)
        self._mw.parameter_1_y_label_lineEdit.blockSignals(True)
        self._mw.parameter_1_y_unit_lineEdit.blockSignals(True)

        self._mw.parameter_1_x_lower_limit_DoubleSpinBox.setValue(self._plot_logic.plot_1_x_limits[0])
        self._mw.parameter_1_x_upper_limit_DoubleSpinBox.setValue(self._plot_logic.plot_1_x_limits[1])
        self._mw.parameter_1_y_lower_limit_DoubleSpinBox.setValue(self._plot_logic.plot_1_y_limits[0])
        self._mw.parameter_1_y_upper_limit_DoubleSpinBox.setValue(self._plot_logic.plot_1_y_limits[1])

        self._mw.parameter_1_x_label_lineEdit.setText(self._plot_logic.plot_1_x_label)
        self._mw.parameter_1_x_unit_lineEdit.setText(self._plot_logic.plot_1_x_unit)
        self._mw.parameter_1_y_label_lineEdit.setText(self._plot_logic.plot_1_y_label)
        self._mw.parameter_1_y_unit_lineEdit.setText(self._plot_logic.plot_1_y_unit)

        self._mw.parameter_1_x_lower_limit_DoubleSpinBox.blockSignals(False)
        self._mw.parameter_1_x_upper_limit_DoubleSpinBox.blockSignals(False)
        self._mw.parameter_1_y_lower_limit_DoubleSpinBox.blockSignals(False)
        self._mw.parameter_1_y_upper_limit_DoubleSpinBox.blockSignals(False)
        self._mw.parameter_1_x_label_lineEdit.blockSignals(False)
        self._mw.parameter_1_x_unit_lineEdit.blockSignals(False)
        self._mw.parameter_1_y_label_lineEdit.blockSignals(False)
        self._mw.parameter_1_y_unit_lineEdit.blockSignals(False)

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
        """
        self._plot_logic.save_data()

    def parameter_1_x_limits_changed(self):
        """ Handling the change of the parameter_1_x_limits.
        """
        self._plot_logic.plot_1_x_limits = [self._mw.parameter_1_x_lower_limit_DoubleSpinBox.value(),
                                            self._mw.parameter_1_x_upper_limit_DoubleSpinBox.value()]

    def parameter_1_y_limits_changed(self):
        """ Handling the change of the parameter_1_y_limits.
        """
        self._plot_logic.plot_1_y_limits = [self._mw.parameter_1_y_lower_limit_DoubleSpinBox.value(),
                                            self._mw.parameter_1_y_upper_limit_DoubleSpinBox.value()]

    def parameter_1_x_auto_clicked(self):
        """Set the parameter_1_x_limits to the min/max of the data values"""
        self._plot_logic.plot_1_x_limits = None

    def parameter_1_y_auto_clicked(self):
        """Set the parameter_1_y_limits to the min/max of the data values"""
        self._plot_logic.plot_1_y_limits = None

    def parameter_1_x_label_changed(self):
        unit = self._mw.parameter_1_x_unit_lineEdit.text()
        self._plot_logic.plot_1_x_label = self._mw.parameter_1_x_label_lineEdit.text()
        self._plot_logic.plot_1_x_unit = unit

    def parameter_1_y_label_changed(self):
        unit = self._mw.parameter_1_y_unit_lineEdit.text()
        self._plot_logic.plot_1_y_label = self._mw.parameter_1_y_label_lineEdit.text()
        self._plot_logic.plot_1_y_unit = unit

    def restore_default_view(self):
        """ Restore the arrangement of DockWidgets to the default
        """
        # Show any hidden dock widgets
        self._mw.plot_1_DockWidget.show()
        self._mw.plot_1_parameter_DockWidget.show()

        # re-dock any floating dock widgets
        self._mw.plot_1_DockWidget.setFloating(False)
        self._mw.plot_1_parameter_DockWidget.setFloating(False)

        # Arrange docks widgets
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.plot_1_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8), self._mw.plot_1_parameter_DockWidget)

        # Set the toolbar to its initial top area
        self._mw.addToolBar(QtCore.Qt.TopToolBarArea,
                            self._mw.control_ToolBar)

    def fit_1_clicked(self):

        print('fit')
        current_fit_method = self._mw.fit_1_comboBox.getCurrentFit()[0]
        self._plot_logic.do_fit_1(current_fit_method)

    @QtCore.Slot(np.ndarray, str, str)
    def fit_1_updated(self, fit_data, formatted_fitresult, fit_method):
        print('fit returned', fit_data)
        self._mw.fit_1_comboBox.blockSignals(True)
        self._mw.fit_1_textBrowser.clear()
        self._mw.fit_1_textBrowser.setPlainText(formatted_fitresult)
        if fit_method:
            self._mw.fit_1_comboBox.setCurrentFit(fit_method)
        for index, curve in enumerate(self._fit_1_curves):
            curve.setData(x=fit_data[index][0], y=fit_data[index][1])
            if fit_method == 'No Fit' and curve in self._mw.plot_1_PlotWidget.items():
                self._mw.plot_1_PlotWidget.removeItem(curve)
            elif fit_method != 'No Fit' and curve not in self._mw.plot_1_PlotWidget.items():
                self._mw.plot_1_PlotWidget.addItem(curve)
        self._mw.fit_1_comboBox.blockSignals(False)
