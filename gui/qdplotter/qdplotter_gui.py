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
from core.util.helpers import natural_sort
from core.util import units
from gui.fitsettings import FitSettingsDialog
from qtwidgets.scientific_spinbox import ScienDSpinBox, ScienSpinBox


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
        self._fsd = None

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
        # Setting default parameters
        self._mw.domain_min_DoubleSpinBox.setValue(self._plot_logic.get_domain()[0])
        self._mw.domain_max_DoubleSpinBox.setValue(self._plot_logic.get_domain()[1])
        self._mw.range_min_DoubleSpinBox.setValue(self._plot_logic.get_range()[0])
        self._mw.range_max_DoubleSpinBox.setValue(self._plot_logic.get_range()[1])

        self._mw.horizontal_label_lineEdit.setText(self._plot_logic.h_label)
        self._mw.horizontal_units_lineEdit.setText(self._plot_logic.h_units)
        self._mw.vertical_label_lineEdit.setText(self._plot_logic.v_label)
        self._mw.vertical_units_lineEdit.setText(self._plot_logic.v_units)

        #####################
        # Connecting user interactions
        self._mw.domain_min_DoubleSpinBox.valueChanged.connect(self.domain_min_changed)
        self._mw.domain_max_DoubleSpinBox.valueChanged.connect(self.domain_max_changed)
        self._mw.range_min_DoubleSpinBox.valueChanged.connect(self.range_min_changed)
        self._mw.range_max_DoubleSpinBox.valueChanged.connect(self.range_max_changed)

        self._mw.horizontal_label_lineEdit.editingFinished.connect(self.h_label_changed)
        self._mw.horizontal_units_lineEdit.editingFinished.connect(self.h_label_changed)
        self._mw.vertical_label_lineEdit.editingFinished.connect(self.v_label_changed)
        self._mw.vertical_units_lineEdit.editingFinished.connect(self.v_label_changed)

        self._mw.fit_domain_to_data_PushButton.clicked.connect(self.fit_domain_to_data)
        self._mw.fit_range_to_data_PushButton.clicked.connect(self.fit_range_to_data)

        # Connect the default view action
        self._mw.restore_default_view_Action.triggered.connect(self.restore_default_view)
        self._mw.save_Action.triggered.connect(self.save_clicked)

        #####################
        self._plot_logic.sigPlotDataUpdated.connect(self.update_data)
        self._plot_logic.sigPlotParamsUpdated.connect(self.update_plot)

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

        if self._plot_logic.clear_old_data:
            self._mw.plot_1_PlotWidget.clear()

        self.curves = []
        pen_colors = cycle(['b', 'y', 'm', 'g'])
        for ii in range(len(self._plot_logic.indep_vals)):
            self.curves.append(self._mw.plot_1_PlotWidget.plot())
            self.curves[ii].setPen(next(pen_colors))
            self.curves[ii].setData(y=self._plot_logic.depen_vals[ii], x=self._plot_logic.indep_vals[ii])

    def update_plot(self):
        self._mw.plot_1_PlotWidget.setXRange(self._plot_logic.plot_domain[0], self._plot_logic.plot_domain[1])
        self._mw.plot_1_PlotWidget.setYRange(self._plot_logic.plot_range[0], self._plot_logic.plot_range[1])
        self._mw.plot_1_PlotWidget.setLabel('bottom', self._plot_logic.h_label, units=self._plot_logic.h_units)
        self._mw.plot_1_PlotWidget.setLabel('left', self._plot_logic.v_label, units=self._plot_logic.v_units)

        # Update display in gui if plot params are changed by script access to logic
        self._mw.domain_min_DoubleSpinBox.setValue(self._plot_logic.get_domain()[0])
        self._mw.domain_max_DoubleSpinBox.setValue(self._plot_logic.get_domain()[1])
        self._mw.range_min_DoubleSpinBox.setValue(self._plot_logic.get_range()[0])
        self._mw.range_max_DoubleSpinBox.setValue(self._plot_logic.get_range()[1])

        self._mw.horizontal_label_lineEdit.setText(self._plot_logic.h_label)
        self._mw.horizontal_units_lineEdit.setText(self._plot_logic.h_units)
        self._mw.vertical_label_lineEdit.setText(self._plot_logic.v_label)
        self._mw.vertical_units_lineEdit.setText(self._plot_logic.v_units)

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
        """
        self._plot_logic.save_data()

    def domain_min_changed(self):
        """ Handling the change of the domain minimum.
        """
        self._plot_logic.set_domain([self._mw.domain_min_DoubleSpinBox.value(),
                                     self._plot_logic.get_domain()[1]
                                     ]
                                    )

    def domain_max_changed(self):
        """ Handling the change of the domain minimum.
        """
        self._plot_logic.set_domain([self._plot_logic.get_domain()[0],
                                     self._mw.domain_max_DoubleSpinBox.value()
                                     ]
                                    )

    def range_min_changed(self):
        """ Handling the change of range.
        """
        self._plot_logic.set_range([self._mw.range_min_DoubleSpinBox.value(),
                                    self._plot_logic.get_range()[1]
                                    ]
                                   )

    def range_max_changed(self):
        """ Handling the change of range.
        """
        self._plot_logic.set_range([self._plot_logic.get_range()[0],
                                    self._mw.range_max_DoubleSpinBox.value()
                                    ]
                                   )

    def fit_domain_to_data(self):
        """Set the domain to the min/max of the data values"""
        self._plot_logic.set_domain()

    def fit_range_to_data(self):
        """Set the range to the min/max of the data values"""
        self._plot_logic.set_range()

    def h_label_changed(self):
        self._plot_logic.set_hlabel(self._mw.horizontal_label_lineEdit.text(),
                                    self._mw.horizontal_units_lineEdit.text()
                                    )

    def v_label_changed(self):
        self._plot_logic.set_vlabel(self._mw.vertical_label_lineEdit.text(),
                                    self._mw.vertical_units_lineEdit.text()
                                    )

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
