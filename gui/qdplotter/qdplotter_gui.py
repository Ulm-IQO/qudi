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

Completely reworked by Kay Jahnke, May 2020
"""

import os
import numpy as np
from itertools import cycle
from qtpy import QtWidgets
from qtpy import QtCore
from qtpy import uic

from core.connector import Connector
from core.statusvariable import StatusVar
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


class PlotDockWidget(QtWidgets.QDockWidget):
    """ Create a DockWidget for plots including fits based on the *.ui file. """
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_plot_widget.ui')
        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)


class ParameterDockWidget(QtWidgets.QDockWidget):
    """ Create a DockWidget for parameters based on the *.ui file. """
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_parameter_widget.ui')
        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)


class QDPlotterGui(GUIBase):
    """ GUI  for displaying up to 3 custom plots.
    The plots are held in tabified DockWidgets and can either be manipulated in the logic
    or by corresponding parameter DockWidgets."""

    # declare connectors
    qdplot_logic = Connector(interface='QDPlotLogic')

    widget_alignment = StatusVar(name='widget_alignment', default='tabbed')

    sigStartCounter = QtCore.Signal()
    sigStopCounter = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._plot_logic = None
        self._mw = None
        self._fsd = None

        self._plot1 = None
        self._plot2 = None
        self._plot3 = None
        self._plots = list()
        self._parameter1 = None
        self._parameter2 = None
        self._parameter3 = None
        self._parameters = list()

        self._pen_colors = [cycle(['b', 'y', 'm', 'g']), cycle(['b', 'y', 'm', 'g']), cycle(['b', 'y', 'm', 'g'])]
        self._plot_curves = [list()] * 3
        self._fit_curves = [list()] * 3

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """

        self._plot_logic = self.qdplot_logic()

        # Use the inherited class 'QDPlotMainWindow' to create the GUI window
        self._mw = QDPlotMainWindow()

        # Fit settings dialogs
        self._fsd = FitSettingsDialog(self._plot_logic.fit_container)
        self._fsd.applySettings()
        self._mw.fit_settings_Action.triggered.connect(self._fsd.show)

        # Connect the default view action
        self._mw.restore_tabbed_view_Action.triggered.connect(self.restore_tabbed_view)
        self._mw.restore_side_by_side_view_Action.triggered.connect(self.restore_side_by_side_view)
        self._mw.restore_arc_view_Action.triggered.connect(self.restore_arc_view)

        # Add the actual plots as DockWidgets to the main window
        self.initialize_plot1()
        self.initialize_plot2()
        self.initialize_plot3()

        self._plots = [self._plot1, self._plot2, self._plot3]
        self._parameters = [self._parameter1, self._parameter2, self._parameter3]

        self.restore_tabbed_view(alignment=self.widget_alignment)
        self.update_data()
        self.update_plot()

        # connect the the logic
        self._plot_logic.sigPlotDataUpdated.connect(self.update_data)
        self._plot_logic.sigPlotParamsUpdated.connect(self.update_plot)
        self._plot_logic.sigFitUpdated.connect(self.fit_updated)

    def show(self):
        """ Make window visible and put it above all other windows. """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def on_deactivate(self):
        """ Deactivate the module """

        # disconnect fit
        self._fsd.sigFitsUpdated.disconnect()
        self._mw.fit_settings_Action.triggered.disconnect(self._fsd.show)

        self._mw.restore_tabbed_view_Action.triggered.disconnect(self.restore_tabbed_view)
        self._mw.restore_side_by_side_view_Action.triggered.disconnect(self.restore_side_by_side_view)
        self._mw.restore_arc_view_Action.triggered.disconnect(self.restore_arc_view)

        # disconnect logic
        self._plot_logic.sigPlotDataUpdated.disconnect(self.update_data)
        self._plot_logic.sigPlotParamsUpdated.disconnect(self.update_plot)
        self._plot_logic.sigFitUpdated.disconnect(self.fit_updated)

        # disconnect GUI elements
        self.disconnect_plot1()
        self.disconnect_plot2()
        self.disconnect_plot3()

        self._mw.close()

    def initialize_plot1(self):
        """ Initialize the first plot and parameter DockWidget. Connect signals the GUI. """

        self._plot1 = PlotDockWidget()
        self._parameter1 = ParameterDockWidget()

        # correct names for the widgets
        self._plot1.setWindowTitle('Plot 1')
        self._parameter1.setWindowTitle('Parameter Plot 1')

        # connect the fits to the plot
        self._plot1.fit_comboBox.setFitFunctions(self._fsd.currentFits)
        self._fsd.sigFitsUpdated.connect(self._plot1.fit_comboBox.setFitFunctions)
        self._plot1.fit_pushButton.clicked.connect(self.fit_1_clicked)
        self._plot1.show_fit_checkBox.setChecked(False)

        # Connecting user interactions
        self._parameter1.x_lower_limit_DoubleSpinBox.valueChanged.connect(self.parameter_1_x_limits_changed)
        self._parameter1.x_upper_limit_DoubleSpinBox.valueChanged.connect(self.parameter_1_x_limits_changed)
        self._parameter1.y_lower_limit_DoubleSpinBox.valueChanged.connect(self.parameter_1_y_limits_changed)
        self._parameter1.y_upper_limit_DoubleSpinBox.valueChanged.connect(self.parameter_1_y_limits_changed)

        self._parameter1.x_label_lineEdit.editingFinished.connect(self.parameter_1_x_label_changed)
        self._parameter1.x_unit_lineEdit.editingFinished.connect(self.parameter_1_x_label_changed)
        self._parameter1.y_label_lineEdit.editingFinished.connect(self.parameter_1_y_label_changed)
        self._parameter1.y_unit_lineEdit.editingFinished.connect(self.parameter_1_y_label_changed)

        self._parameter1.x_auto_PushButton.clicked.connect(self.parameter_1_x_auto_clicked)
        self._parameter1.y_auto_PushButton.clicked.connect(self.parameter_1_y_auto_clicked)
        self._plot1.save_pushButton.clicked.connect(self.plot_1_save_clicked)

    def disconnect_plot1(self):
        """ Disconnect signals the GUI. """

        self._plot1.fit_pushButton.clicked.disconnect()

        self._parameter1.x_lower_limit_DoubleSpinBox.valueChanged.disconnect()
        self._parameter1.x_upper_limit_DoubleSpinBox.valueChanged.disconnect()
        self._parameter1.y_lower_limit_DoubleSpinBox.valueChanged.disconnect()
        self._parameter1.y_upper_limit_DoubleSpinBox.valueChanged.disconnect()

        self._parameter1.x_label_lineEdit.editingFinished.disconnect()
        self._parameter1.x_unit_lineEdit.editingFinished.disconnect()
        self._parameter1.y_label_lineEdit.editingFinished.disconnect()
        self._parameter1.y_unit_lineEdit.editingFinished.disconnect()

        self._parameter1.x_auto_PushButton.clicked.disconnect()
        self._parameter1.y_auto_PushButton.clicked.disconnect()
        self._plot1.save_pushButton.clicked.disconnect()

    def initialize_plot2(self):
        """ Initialize the second plot and parameter DockWidget. Connect signals the GUI. """

        self._plot2 = PlotDockWidget()
        self._parameter2 = ParameterDockWidget()

        # correct names for the widgets
        self._plot2.setWindowTitle('Plot 2')
        self._parameter2.setWindowTitle('Parameter Plot 2')

        # connect the fits to the plot
        self._plot2.fit_comboBox.setFitFunctions(self._fsd.currentFits)
        self._fsd.sigFitsUpdated.connect(self._plot2.fit_comboBox.setFitFunctions)
        self._plot2.fit_pushButton.clicked.connect(self.fit_2_clicked)
        self._plot2.show_fit_checkBox.setChecked(False)

        # Connecting user interactions
        self._parameter2.x_lower_limit_DoubleSpinBox.valueChanged.connect(self.parameter_2_x_limits_changed)
        self._parameter2.x_upper_limit_DoubleSpinBox.valueChanged.connect(self.parameter_2_x_limits_changed)
        self._parameter2.y_lower_limit_DoubleSpinBox.valueChanged.connect(self.parameter_2_y_limits_changed)
        self._parameter2.y_upper_limit_DoubleSpinBox.valueChanged.connect(self.parameter_2_y_limits_changed)

        self._parameter2.x_label_lineEdit.editingFinished.connect(self.parameter_2_x_label_changed)
        self._parameter2.x_unit_lineEdit.editingFinished.connect(self.parameter_2_x_label_changed)
        self._parameter2.y_label_lineEdit.editingFinished.connect(self.parameter_2_y_label_changed)
        self._parameter2.y_unit_lineEdit.editingFinished.connect(self.parameter_2_y_label_changed)

        self._parameter2.x_auto_PushButton.clicked.connect(self.parameter_2_x_auto_clicked)
        self._parameter2.y_auto_PushButton.clicked.connect(self.parameter_2_y_auto_clicked)
        self._plot2.save_pushButton.clicked.connect(self.plot_2_save_clicked)

    def disconnect_plot2(self):
        """ Disconnect signals the GUI. """
        
        self._plot2.fit_pushButton.clicked.disconnect()

        # Connecting user interactions
        self._parameter2.x_lower_limit_DoubleSpinBox.valueChanged.disconnect()
        self._parameter2.x_upper_limit_DoubleSpinBox.valueChanged.disconnect()
        self._parameter2.y_lower_limit_DoubleSpinBox.valueChanged.disconnect()
        self._parameter2.y_upper_limit_DoubleSpinBox.valueChanged.disconnect()

        self._parameter2.x_label_lineEdit.editingFinished.disconnect()
        self._parameter2.x_unit_lineEdit.editingFinished.disconnect()
        self._parameter2.y_label_lineEdit.editingFinished.disconnect()
        self._parameter2.y_unit_lineEdit.editingFinished.disconnect()

        self._parameter2.x_auto_PushButton.clicked.disconnect()
        self._parameter2.y_auto_PushButton.clicked.disconnect()
        self._plot2.save_pushButton.clicked.disconnect()

    def initialize_plot3(self):
        """ Initialize the third plot and parameter DockWidget. Connect signals the GUI. """

        self._plot3 = PlotDockWidget()
        self._parameter3 = ParameterDockWidget()

        # correct names for the widgets
        self._plot3.setWindowTitle('Plot 3')
        self._parameter3.setWindowTitle('Parameter Plot 3')

        # connect the fits to the plot
        self._plot3.fit_comboBox.setFitFunctions(self._fsd.currentFits)
        self._fsd.sigFitsUpdated.connect(self._plot3.fit_comboBox.setFitFunctions)
        self._plot3.fit_pushButton.clicked.connect(self.fit_3_clicked)
        self._plot3.show_fit_checkBox.setChecked(False)

        # Connecting user interactions
        self._parameter3.x_lower_limit_DoubleSpinBox.valueChanged.connect(self.parameter_3_x_limits_changed)
        self._parameter3.x_upper_limit_DoubleSpinBox.valueChanged.connect(self.parameter_3_x_limits_changed)
        self._parameter3.y_lower_limit_DoubleSpinBox.valueChanged.connect(self.parameter_3_y_limits_changed)
        self._parameter3.y_upper_limit_DoubleSpinBox.valueChanged.connect(self.parameter_3_y_limits_changed)

        self._parameter3.x_label_lineEdit.editingFinished.connect(self.parameter_3_x_label_changed)
        self._parameter3.x_unit_lineEdit.editingFinished.connect(self.parameter_3_x_label_changed)
        self._parameter3.y_label_lineEdit.editingFinished.connect(self.parameter_3_y_label_changed)
        self._parameter3.y_unit_lineEdit.editingFinished.connect(self.parameter_3_y_label_changed)

        self._parameter3.x_auto_PushButton.clicked.connect(self.parameter_3_x_auto_clicked)
        self._parameter3.y_auto_PushButton.clicked.connect(self.parameter_3_y_auto_clicked)
        self._plot3.save_pushButton.clicked.connect(self.plot_3_save_clicked)

    def disconnect_plot3(self):
        """ Disconnect signals the GUI. """

        self._plot3.fit_pushButton.clicked.disconnect()
        
        self._parameter3.x_lower_limit_DoubleSpinBox.valueChanged.disconnect()
        self._parameter3.x_upper_limit_DoubleSpinBox.valueChanged.disconnect()
        self._parameter3.y_lower_limit_DoubleSpinBox.valueChanged.disconnect()
        self._parameter3.y_upper_limit_DoubleSpinBox.valueChanged.disconnect()

        self._parameter3.x_label_lineEdit.editingFinished.disconnect()
        self._parameter3.x_unit_lineEdit.editingFinished.disconnect()
        self._parameter3.y_label_lineEdit.editingFinished.disconnect()
        self._parameter3.y_unit_lineEdit.editingFinished.disconnect()

        self._parameter3.x_auto_PushButton.clicked.disconnect()
        self._parameter3.y_auto_PushButton.clicked.disconnect()
        self._plot3.save_pushButton.clicked.disconnect()

    def restore_side_by_side_view(self):
        """ Restore the arrangement of DockWidgets to the default """
        self.restore_tabbed_view(alignment='side_by_side')

    def restore_arc_view(self):
        """ Restore the arrangement of DockWidgets to the default """
        self.restore_tabbed_view(alignment='arc')

    def restore_tabbed_view(self, alignment='tabbed'):
        """ Restore the arrangement of DockWidgets to the default """

        self.widget_alignment = alignment
        self._mw.setTabPosition(QtCore.Qt.TopDockWidgetArea, 0)  # North: 0, South: 1, West: 2, East: 3
        self._mw.setDockNestingEnabled(True)

        # Arrange docks widgets
        if alignment == 'tabbed':
            self._mw.centralwidget.setVisible(False)
            self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, self._plot1)
            self._mw.tabifyDockWidget(self._plot1, self._plot2)
            self._mw.tabifyDockWidget(self._plot1, self._plot3)
        elif alignment == 'arc':
            self._mw.centralwidget.setVisible(True)
            self._mw.centralwidget.setFixedWidth(0)
            self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, self._plot1)
            self._mw.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self._plot2)
            self._mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._plot3)
        elif alignment == 'side_by_side':
            self._mw.centralwidget.setVisible(False)
            self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, self._plot1)
            self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, self._plot2)
            self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, self._plot3)

        self._mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self._parameter1)
        self._mw.tabifyDockWidget(self._parameter1, self._parameter2)
        self._mw.tabifyDockWidget(self._parameter1, self._parameter3)

        for plot in self._plots:
            # Show any hidden dock widgets
            plot.setVisible(True)
            # re-dock any floating dock widgets
            plot.setFloating(False)

        for parameter in self._parameters:
            # Show any hidden dock widgets
            parameter.setVisible(True)
            # re-dock any floating dock widgets
            parameter.setFloating(False)
            parameter.setFixedHeight(110)

    def update_data(self):
        """ Function creates empty plots, grabs the data and sends it to them. """

        for plot_index, plot in enumerate(self._plots):

            if self._plot_logic.clear_old_data(plot_index=plot_index):
                plot.plot_PlotWidget.clear()

            self._plot_curves[plot_index] = []
            self._fit_curves[plot_index] = []

            for line in range(len(self._plot_logic.get_x_data(plot_index=plot_index))):
                pen_color = next(self._pen_colors[plot_index])
                self._plot_curves[plot_index].append(plot.plot_PlotWidget.plot(pen=pen_color,
                                                                               symbol='d',
                                                                               symbolSize=6,
                                                                               symbolBrush=pen_color))
                self._plot_curves[plot_index][line].setData(x=self._plot_logic.get_x_data(plot_index=plot_index)[line],
                                                            y=self._plot_logic.get_y_data(plot_index=plot_index)[line])
                self._fit_curves[plot_index].append(plot.plot_PlotWidget.plot())
                self._fit_curves[plot_index][line].setPen('r')

    def update_plot(self):
        """ Function updated limits, labels and units in the plot and parameter widgets. """

        for plot_index, plot in enumerate(self._plots):
            plot.plot_PlotWidget.setXRange(self._plot_logic.get_x_limits(plot_index)[0],
                                           self._plot_logic.get_x_limits(plot_index)[1])
            plot.plot_PlotWidget.setYRange(self._plot_logic.get_y_limits(plot_index)[0],
                                           self._plot_logic.get_y_limits(plot_index)[1])
            plot.plot_PlotWidget.setLabel('bottom', self._plot_logic.get_x_label(plot_index),
                                          units=self._plot_logic.get_x_unit(plot_index))
            plot.plot_PlotWidget.setLabel('left', self._plot_logic.get_y_label(plot_index),
                                          units=self._plot_logic.get_y_unit(plot_index))

        # Update display in gui if plot params are changed by script access to logic
        for plot_index, parameter in enumerate(self._parameters):
            parameter.x_lower_limit_DoubleSpinBox.blockSignals(True)
            parameter.x_upper_limit_DoubleSpinBox.blockSignals(True)
            parameter.y_lower_limit_DoubleSpinBox.blockSignals(True)
            parameter.y_upper_limit_DoubleSpinBox.blockSignals(True)
            parameter.x_label_lineEdit.blockSignals(True)
            parameter.x_unit_lineEdit.blockSignals(True)
            parameter.y_label_lineEdit.blockSignals(True)
            parameter.y_unit_lineEdit.blockSignals(True)

            parameter.x_lower_limit_DoubleSpinBox.setValue(self._plot_logic.get_x_limits(plot_index)[0])
            parameter.x_upper_limit_DoubleSpinBox.setValue(self._plot_logic.get_x_limits(plot_index)[1])
            parameter.y_lower_limit_DoubleSpinBox.setValue(self._plot_logic.get_y_limits(plot_index)[0])
            parameter.y_upper_limit_DoubleSpinBox.setValue(self._plot_logic.get_y_limits(plot_index)[1])

            parameter.x_label_lineEdit.setText(self._plot_logic.get_x_label(plot_index))
            parameter.x_unit_lineEdit.setText(self._plot_logic.get_x_unit(plot_index))
            parameter.y_label_lineEdit.setText(self._plot_logic.get_y_label(plot_index))
            parameter.y_unit_lineEdit.setText(self._plot_logic.get_y_unit(plot_index))

            parameter.x_lower_limit_DoubleSpinBox.blockSignals(False)
            parameter.x_upper_limit_DoubleSpinBox.blockSignals(False)
            parameter.y_lower_limit_DoubleSpinBox.blockSignals(False)
            parameter.y_upper_limit_DoubleSpinBox.blockSignals(False)
            parameter.x_label_lineEdit.blockSignals(False)
            parameter.x_unit_lineEdit.blockSignals(False)
            parameter.y_label_lineEdit.blockSignals(False)
            parameter.y_unit_lineEdit.blockSignals(False)

    def plot_1_save_clicked(self):
        """ Handling the save button to save the data into a file. """
        self._plot_logic.save_data(plot_index=0)

    def plot_2_save_clicked(self):
        """ Handling the save button to save the data into a file. """
        self._plot_logic.save_data(plot_index=1)

    def plot_3_save_clicked(self):
        """ Handling the save button to save the data into a file. """
        self._plot_logic.save_data(plot_index=2)

    def parameter_1_x_limits_changed(self):
        """ Handling the change of the parameter_1_x_limits. """
        self._plot_logic.set_x_limits(limits=[self._parameter1.x_lower_limit_DoubleSpinBox.value(),
                                              self._parameter1.x_upper_limit_DoubleSpinBox.value()],
                                      plot_index=0)

    def parameter_1_y_limits_changed(self):
        """ Handling the change of the parameter_1_y_limits. """
        self._plot_logic.set_y_limits(limits=[self._parameter1.y_lower_limit_DoubleSpinBox.value(),
                                              self._parameter1.y_upper_limit_DoubleSpinBox.value()],
                                      plot_index=0)

    def parameter_1_x_auto_clicked(self):
        """ Set the parameter_1_x_limits to the min/max of the data values """
        self._plot_logic.set_x_limits(plot_index=0)

    def parameter_1_y_auto_clicked(self):
        """ Set the parameter_1_y_limits to the min/max of the data values """
        self._plot_logic.set_y_limits(plot_index=0)

    def parameter_1_x_label_changed(self):
        """ Set the x-label and the uni of plot 1 """
        unit = self._parameter1.x_unit_lineEdit.text()
        self._plot_logic.set_x_label(value=self._parameter1.x_label_lineEdit.text(), plot_index=0)
        self._plot_logic.set_x_unit(value=unit, plot_index=0)

    def parameter_1_y_label_changed(self):
        """ Set the y-label and the uni of plot 1 """
        unit = self._parameter1.y_unit_lineEdit.text()
        self._plot_logic.set_y_label(value=self._parameter1.y_label_lineEdit.text(), plot_index=0)
        self._plot_logic.set_y_unit(value=unit, plot_index=0)

    def parameter_2_x_limits_changed(self):
        """ Handling the change of the parameter_2_x_limits. """
        self._plot_logic.set_x_limits(limits=[self._parameter2.x_lower_limit_DoubleSpinBox.value(),
                                              self._parameter2.x_upper_limit_DoubleSpinBox.value()],
                                      plot_index=1)

    def parameter_2_y_limits_changed(self):
        """ Handling the change of the parameter_2_y_limits. """
        self._plot_logic.set_y_limits(limits=[self._parameter2.y_lower_limit_DoubleSpinBox.value(),
                                              self._parameter2.y_upper_limit_DoubleSpinBox.value()],
                                      plot_index=1)

    def parameter_2_x_auto_clicked(self):
        """ Set the parameter_1_x_limits to the min/max of the data values """
        self._plot_logic.set_x_limits(plot_index=1)

    def parameter_2_y_auto_clicked(self):
        """ Set the parameter_1_y_limits to the min/max of the data values """
        self._plot_logic.set_y_limits(plot_index=1)

    def parameter_2_x_label_changed(self):
        """ Set the x-label and the uni of plot 2 """
        unit = self._parameter2.x_unit_lineEdit.text()
        self._plot_logic.set_x_label(value=self._parameter2.x_label_lineEdit.text(), plot_index=1)
        self._plot_logic.set_x_unit(value=unit, plot_index=1)

    def parameter_2_y_label_changed(self):
        """ Set the y-label and the uni of plot 2 """
        unit = self._parameter2.y_unit_lineEdit.text()
        self._plot_logic.set_y_label(value=self._parameter2.y_label_lineEdit.text(), plot_index=1)
        self._plot_logic.set_y_unit(value=unit, plot_index=1)

    def parameter_3_x_limits_changed(self):
        """ Handling the change of the parameter_3_x_limits. """
        self._plot_logic.set_x_limits(limits=[self._parameter3.x_lower_limit_DoubleSpinBox.value(),
                                              self._parameter3.x_upper_limit_DoubleSpinBox.value()],
                                      plot_index=2)

    def parameter_3_y_limits_changed(self):
        """ Handling the change of the parameter_3_y_limits. """
        self._plot_logic.set_y_limits(limits=[self._parameter3.y_lower_limit_DoubleSpinBox.value(),
                                              self._parameter3.y_upper_limit_DoubleSpinBox.value()],
                                      plot_index=2)

    def parameter_3_x_auto_clicked(self):
        """ Set the parameter_3_x_limits to the min/max of the data values """
        self._plot_logic.set_x_limits(plot_index=2)

    def parameter_3_y_auto_clicked(self):
        """ Set the parameter_1_y_limits to the min/max of the data values """
        self._plot_logic.set_y_limits(plot_index=2)

    def parameter_3_x_label_changed(self):
        """ Set the x-label and the uni of plot 3 """
        unit = self._parameter3.x_unit_lineEdit.text()
        self._plot_logic.set_x_label(value=self._parameter3.x_label_lineEdit.text(), plot_index=2)
        self._plot_logic.set_x_unit(value=unit, plot_index=2)

    def parameter_3_y_label_changed(self):
        """ Set the y-label and the uni of plot 3 """
        unit = self._parameter3.y_unit_lineEdit.text()
        self._plot_logic.set_y_label(value=self._parameter3.y_label_lineEdit.text(), plot_index=2)
        self._plot_logic.set_y_unit(value=unit, plot_index=2)

    def fit_1_clicked(self):
        self.fit_clicked(plot_index=0)

    def fit_2_clicked(self):
        self.fit_clicked(plot_index=1)

    def fit_3_clicked(self):
        self.fit_clicked(plot_index=2)

    def fit_clicked(self, plot_index=0):
        """ Triggers the fit to be done. Attention, this runs in the GUI thread. """
        current_fit_method = self._plots[plot_index].fit_comboBox.getCurrentFit()[0]
        self._plot_logic.do_fit(fit_method=current_fit_method, plot_index=plot_index)

    @QtCore.Slot(int, np.ndarray, str, str)
    def fit_updated(self, plot_index, fit_data, formatted_fitresult, fit_method):
        """ Function that handles the fit results received from the logic via a signal.

        @param int plot_index: index of the plot the fit was performed for in the range for 0 to 2
        @param 3-dimensional np.ndarray fit_data: the fit data in a 2-d array for each data set
        @param str formatted_fitresult: string containing the parameters already formatted
        @param str fit_method: the fit_method used
        """
        self._plots[plot_index].fit_comboBox.blockSignals(True)

        self._plots[plot_index].show_fit_checkBox.setChecked(True)
        self._plots[plot_index].fit_textBrowser.clear()
        self._plots[plot_index].fit_textBrowser.setPlainText(formatted_fitresult)

        if fit_method:
            self._plots[plot_index].fit_comboBox.setCurrentFit(fit_method)

        for index, curve in enumerate(self._fit_curves[plot_index]):
            curve.setData(x=fit_data[index][0], y=fit_data[index][1])

            if fit_method == 'No Fit' and curve in self._plots[plot_index].plot_PlotWidget.items():
                self._plots[plot_index].plot_PlotWidget.removeItem(curve)
            elif fit_method != 'No Fit' and curve not in self._plots[plot_index].plot_PlotWidget.items():
                self._plots[plot_index].plot_PlotWidget.addItem(curve)

        self._plots[plot_index].fit_comboBox.blockSignals(False)
