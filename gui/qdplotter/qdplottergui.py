# -*- coding: utf-8 -*-

"""
This file contains a Qudi gui module for quick plotting.

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

import os
from qtpy import QtWidgets
from qtpy import QtCore
from qtpy import uic

from gui.guibase import GUIBase


class QdplotMainWindow(QtWidgets.QMainWindow):

    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_qdplotter.ui')

        # Load it
        super(QdplotMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()


class QdplotterGui(GUIBase):

    """ FIXME: Please document
    """
    _modclass = 'qdplotgui'
    _modtype = 'gui'

    # declare connectors
    _in = {'qdplotlogic1': 'QdplotLogic'}

    sigStartCounter = QtCore.Signal()
    sigStopCounter = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{}: {}'.format(key, config[key]))


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

        self._qdplot_logic = self.connector['in']['qdplotlogic1']['object']

        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = QdplotMainWindow()

        # Setup dock widgets
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)

        # Plot labels.
        self._pw = self._mw.qdplot_PlotWidget

        self._pw.setLabel('left', 'Dependent variable', units='?')
        self._pw.setLabel('bottom', 'Independent variable', units='?')

        ## Create an empty plot curve to be filled later, set its pen
        self._curve1 = self._pw.plot()
        self._curve1.setPen('g')

        #####################
        # Setting default parameters
        self._mw.domain_min_DoubleSpinBox.setValue(self._qdplot_logic.get_domain()[0])
        self._mw.domain_max_DoubleSpinBox.setValue(self._qdplot_logic.get_domain()[1])
        self._mw.range_min_DoubleSpinBox.setValue(self._qdplot_logic.get_range()[0])
        self._mw.range_max_DoubleSpinBox.setValue(self._qdplot_logic.get_range()[1])

        self._mw.horizontal_label_lineEdit.setText(self._qdplot_logic.h_label)
        self._mw.horizontal_units_lineEdit.setText(self._qdplot_logic.h_units)
        self._mw.vertical_label_lineEdit.setText(self._qdplot_logic.v_label)
        self._mw.vertical_units_lineEdit.setText(self._qdplot_logic.v_units)

        #####################
        # Connecting user interactions
        self._mw.domain_min_DoubleSpinBox.valueChanged.connect(self.domain_changed)
        self._mw.domain_max_DoubleSpinBox.valueChanged.connect(self.domain_changed)
        self._mw.range_min_DoubleSpinBox.valueChanged.connect(self.range_changed)
        self._mw.range_max_DoubleSpinBox.valueChanged.connect(self.range_changed)

        self._mw.horizontal_label_lineEdit.editingFinished.connect(self.h_label_changed)
        self._mw.horizontal_units_lineEdit.editingFinished.connect(self.h_label_changed)
        self._mw.vertical_label_lineEdit.editingFinished.connect(self.v_label_changed)
        self._mw.vertical_units_lineEdit.editingFinished.connect(self.v_label_changed)

        # Connect the default view action
        self._mw.restore_default_view_Action.triggered.connect(self.restore_default_view)
        self._mw.save_Action.triggered.connect(self.save_clicked)

        #####################
        self._qdplot_logic.sigPlotDataUpdated.connect(self.updateData)
        self._qdplot_logic.sigPlotParamsUpdated.connect(self.updatePlot)

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def on_deactivate(self, e):
        # FIXME: !
        """ Deactivate the module

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        self._mw.close()

    def updateData(self):
        """ The function that grabs the data and sends it to the plot.
        """

        self._curve1.setData(y=self._qdplot_logic.depen_vals, x=self._qdplot_logic.indep_vals)

    def updatePlot(self):
        self._pw.setXRange(self._qdplot_logic.plot_domain[0], self._qdplot_logic.plot_domain[1])
        self._pw.setYRange(self._qdplot_logic.plot_range[0], self._qdplot_logic.plot_range[1])
        self._pw.setLabel('bottom', self._qdplot_logic.h_label, units=self._qdplot_logic.h_units)
        self._pw.setLabel('left', self._qdplot_logic.v_label, units=self._qdplot_logic.v_units)

        # Update display in gui if plot params are changed by script access to logic
        self._mw.domain_min_DoubleSpinBox.setValue(self._qdplot_logic.get_domain()[0])
        self._mw.domain_max_DoubleSpinBox.setValue(self._qdplot_logic.get_domain()[1])
        self._mw.range_min_DoubleSpinBox.setValue(self._qdplot_logic.get_range()[0])
        self._mw.range_max_DoubleSpinBox.setValue(self._qdplot_logic.get_range()[1])

        print('v_label in logic when updatePLot',self._qdplot_logic.v_label)

        self._mw.horizontal_label_lineEdit.setText(self._qdplot_logic.h_label)
        self._mw.horizontal_units_lineEdit.setText(self._qdplot_logic.h_units)
        self._mw.vertical_label_lineEdit.setText(self._qdplot_logic.v_label)
        self._mw.vertical_units_lineEdit.setText(self._qdplot_logic.v_units)

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
        """
        self._qdplot_logic.save_data()

    def domain_changed(self):
        """ Handling the change of the domain.
        """
        self._qdplot_logic.set_domain([self._mw.domain_min_DoubleSpinBox.value(),
                                       self._mw.domain_max_DoubleSpinBox.value()
                                       ]
                                      )


    def range_changed(self):
        """ Handling the change of range.
        """
        self._qdplot_logic.set_range([self._mw.range_min_DoubleSpinBox.value(),
                                      self._mw.range_max_DoubleSpinBox.value()
                                      ]
                                     )

        return

    def h_label_changed(self):
        self._qdplot_logic.set_hlabel(self._mw.horizontal_label_lineEdit.text(),
                                      self._mw.horizontal_units_lineEdit.text()
                                      )

    def v_label_changed(self):
        self._qdplot_logic.set_vlabel(self._mw.vertical_label_lineEdit.text(),
                                      self._mw.vertical_units_lineEdit.text()
                                      )

    def restore_default_view(self):
        """ Restore the arrangement of DockWidgets to the default
        """
        # Show any hidden dock widgets
        self._mw.qdplot_DockWidget.show()
        self._mw.plot_parameters_DockWidget.show()

        # re-dock any floating dock widgets
        self._mw.qdplot_DockWidget.setFloating(False)
        self._mw.plot_parameters_DockWidget.setFloating(False)

        # Arrange docks widgets
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1), self._mw.qdplot_DockWidget)
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8), self._mw.plot_parameters_DockWidget)

        # Set the toolbar to its initial top area
        self._mw.addToolBar(QtCore.Qt.TopToolBarArea,
                            self._mw.counting_control_ToolBar)
