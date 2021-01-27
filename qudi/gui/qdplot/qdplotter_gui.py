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
import functools
import numpy as np
from itertools import cycle
from qtpy import QtWidgets
from qtpy import QtCore
from qtpy import uic
from pyqtgraph import SignalProxy, mkColor

from core.connector import Connector
from core.configoption import ConfigOption
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
        self.setTabPosition(QtCore.Qt.TopDockWidgetArea, QtWidgets.QTabWidget.North)
        self.setTabPosition(QtCore.Qt.BottomDockWidgetArea, QtWidgets.QTabWidget.North)
        self.setTabPosition(QtCore.Qt.LeftDockWidgetArea, QtWidgets.QTabWidget.North)
        self.setTabPosition(QtCore.Qt.RightDockWidgetArea, QtWidgets.QTabWidget.North)


class PlotDockWidget(QtWidgets.QDockWidget):
    """ Create a DockWidget for plots including fits based on the *.ui file. """
    def __init__(self, title=None, parent=None):
        if isinstance(title, str):
            super().__init__(title, parent)
        else:
            super().__init__(parent)

        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_plot_widget.ui')
        # Load it
        widget = QtWidgets.QWidget()
        uic.loadUi(ui_file, widget)
        widget.setObjectName('plot_widget')
        widget.fit_groupBox.setVisible(False)
        widget.controls_groupBox.setVisible(False)

        # widget.plot_PlotWidget.setMouseEnabled(x=False, y=False)  # forbid mouse panning/zooming
        # widget.plot_PlotWidget.disableAutoRange()  # disable any axis scale changes by pyqtgraph
        # widget.plot_PlotWidget.hideButtons()  # do not show the "A" autoscale button of pyqtgraph
        # widget.plot_PlotWidget.setMenuEnabled(False)  # Disable pyqtgraph right click context menu

        self.setWidget(widget)
        self.setFeatures(self.DockWidgetFloatable | self.DockWidgetMovable)


class QDPlotterGui(GUIBase):
    """ GUI  for displaying up to 3 custom plots.
    The plots are held in tabified DockWidgets and can either be manipulated in the logic
    or by corresponding parameter DockWidgets.

    Example config for copy-paste:

    qdplotter:
        module.Class: 'qdplotter.qdplotter_gui.QDPlotterGui'
        pen_color_list: [[100, 100, 100], 'c', 'm', 'g']
        connect:
            qdplot_logic: 'qdplotlogic'
    """

    sigPlotParametersChanged = QtCore.Signal(int, dict)
    sigAutoRangeClicked = QtCore.Signal(int, bool, bool)
    sigDoFit = QtCore.Signal(str, int)
    sigRemovePlotClicked = QtCore.Signal(int)

    # declare connectors
    qdplot_logic = Connector(interface='QDPlotLogic')
    # declare config options
    _pen_color_list = ConfigOption(name='pen_color_list', default=['b', 'y', 'm', 'g'])
    # declare status variables
    widget_alignment = StatusVar(name='widget_alignment', default='tabbed')

    _allowed_colors = {'b', 'g', 'r', 'c', 'm', 'y', 'k', 'w'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._plot_logic = None
        self._mw = None
        self._fsd = None

        self._plot_dockwidgets = list()
        self._pen_colors = list()
        self._plot_curves = list()
        self._fit_curves = list()
        self._pg_signal_proxys = list()

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """
        self._plot_logic = self.qdplot_logic()

        if not isinstance(self._pen_color_list, (list, tuple)) or len(self._pen_color_list) < 1:
            self.log.warning(
                'The ConfigOption pen_color_list needs to be a list of strings but was "{0}".'
                ' Will use the following pen colors as default: {1}.'
                ''.format(self._pen_color_list, ['b', 'y', 'm', 'g']))
            self._pen_color_list = ['b', 'y', 'm', 'g']
        else:
            self._pen_color_list = list(self._pen_color_list)

        for index, color in enumerate(self._pen_color_list):
            if (isinstance(color, (list, tuple)) and len(color) == 3) or \
                    (isinstance(color, str) and color in self._allowed_colors):
                pass
            else:
                self.log.warning('The color was "{0}" but needs to be from this list: {1} '
                                 'or a 3 element tuple with values from 0 to 255 for RGB.'
                                 ' Setting color to "b".'.format(color, self._allowed_colors))
                self._pen_color_list[index] = 'b'

        # Use the inherited class 'QDPlotMainWindow' to create the GUI window
        self._mw = QDPlotMainWindow()

        # Fit settings dialogs
        self._fsd = FitSettingsDialog(self._plot_logic.fit_container)
        self._fsd.applySettings()
        self._mw.fit_settings_Action.triggered.connect(self._fsd.show)

        # Connect the main window restore view actions
        self._mw.restore_tabbed_view_Action.triggered.connect(self.restore_tabbed_view)
        self._mw.restore_side_by_side_view_Action.triggered.connect(self.restore_side_by_side_view)
        self._mw.restore_arc_view_Action.triggered.connect(self.restore_arc_view)
        self._mw.save_all_Action.triggered.connect(self.save_all_clicked)

        # Initialize dock widgets
        self._plot_dockwidgets = list()
        self._pen_colors = list()
        self._plot_curves = list()
        self._fit_curves = list()
        self._pg_signal_proxys = list()
        self.update_number_of_plots(self._plot_logic.number_of_plots)
        # Update all plot parameters and data from logic
        for index, _ in enumerate(self._plot_dockwidgets):
            self.update_data(index)
            self.update_fit_data(index)
            self.update_plot_parameters(index)
        self.restore_view()

        # Connect signal to logic
        self.sigPlotParametersChanged.connect(
            self._plot_logic.update_plot_parameters, QtCore.Qt.QueuedConnection)
        self.sigAutoRangeClicked.connect(
            self._plot_logic.update_auto_range, QtCore.Qt.QueuedConnection)
        self.sigDoFit.connect(self._plot_logic.do_fit, QtCore.Qt.QueuedConnection)
        self.sigRemovePlotClicked.connect(self._plot_logic.remove_plot, QtCore.Qt.QueuedConnection)
        self._mw.new_plot_Action.triggered.connect(
            self._plot_logic.add_plot, QtCore.Qt.QueuedConnection)
        # Connect signals from logic
        self._plot_logic.sigPlotDataUpdated.connect(self.update_data, QtCore.Qt.QueuedConnection)
        self._plot_logic.sigPlotParamsUpdated.connect(
            self.update_plot_parameters, QtCore.Qt.QueuedConnection)
        self._plot_logic.sigPlotNumberChanged.connect(
            self.update_number_of_plots, QtCore.Qt.QueuedConnection)
        self._plot_logic.sigFitUpdated.connect(self.update_fit_data, QtCore.Qt.QueuedConnection)

        self.show()

    def show(self):
        """ Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def on_deactivate(self):
        """ Deactivate the module """
        # disconnect fit
        self._mw.fit_settings_Action.triggered.disconnect()

        self._mw.restore_tabbed_view_Action.triggered.disconnect()
        self._mw.restore_side_by_side_view_Action.triggered.disconnect()
        self._mw.restore_arc_view_Action.triggered.disconnect()
        self._mw.save_all_Action.triggered.disconnect()

        # Disconnect signal to logic
        self.sigPlotParametersChanged.disconnect()
        self.sigAutoRangeClicked.disconnect()
        self.sigDoFit.disconnect()
        self.sigRemovePlotClicked.disconnect()
        self._mw.new_plot_Action.triggered.disconnect()
        # Disconnect signals from logic
        self._plot_logic.sigPlotDataUpdated.disconnect(self.update_data)
        self._plot_logic.sigPlotParamsUpdated.disconnect(self.update_plot_parameters)
        self._plot_logic.sigPlotNumberChanged.disconnect(self.update_number_of_plots)
        self._plot_logic.sigFitUpdated.disconnect(self.update_fit_data)

        # disconnect GUI elements
        self.update_number_of_plots(0)

        self._fsd.sigFitsUpdated.disconnect()
        self._mw.close()

    @QtCore.Slot(int)
    def update_number_of_plots(self, count):
        """ Adjust number of QDockWidgets to current number of plots. Does NO initialization of the
        contents.

        @param int count: Number of plots to display.
        """
        # Remove dock widgets if plot count decreased
        while count < len(self._plot_dockwidgets):
            index = len(self._plot_dockwidgets) - 1
            self._disconnect_plot_signals(index)
            self._plot_dockwidgets[-1].setParent(None)
            del self._plot_curves[-1]
            del self._fit_curves[-1]
            del self._pen_colors[-1]
            del self._plot_dockwidgets[-1]
            del self._pg_signal_proxys[-1]
        # Add dock widgets if plot count increased
        while count > len(self._plot_dockwidgets):
            index = len(self._plot_dockwidgets)
            dockwidget = PlotDockWidget('Plot {0:d}'.format(index + 1), self._mw)
            dockwidget.widget().fit_comboBox.setFitFunctions(self._fsd.currentFits)
            dockwidget.widget().show_fit_checkBox.setChecked(False)
            dockwidget.widget().show_controls_checkBox.setChecked(False)
            dockwidget.widget().fit_groupBox.setVisible(False)
            dockwidget.widget().controls_groupBox.setVisible(False)
            self._plot_dockwidgets.append(dockwidget)
            self._pen_colors.append(cycle(self._pen_color_list))
            self._plot_curves.append(list())
            self._fit_curves.append(list())
            self._pg_signal_proxys.append([None, None])
            self._connect_plot_signals(index)
            self.restore_view()

    def _connect_plot_signals(self, index):
        dockwidget = self._plot_dockwidgets[index].widget()
        self._fsd.sigFitsUpdated.connect(dockwidget.fit_comboBox.setFitFunctions)
        dockwidget.fit_pushButton.clicked.connect(functools.partial(self.fit_clicked, index))

        x_lim_callback = functools.partial(self.x_limits_changed, index)
        dockwidget.x_lower_limit_DoubleSpinBox.valueChanged.connect(x_lim_callback)
        dockwidget.x_upper_limit_DoubleSpinBox.valueChanged.connect(x_lim_callback)
        y_lim_callback = functools.partial(self.y_limits_changed, index)
        dockwidget.y_lower_limit_DoubleSpinBox.valueChanged.connect(y_lim_callback)
        dockwidget.y_upper_limit_DoubleSpinBox.valueChanged.connect(y_lim_callback)

        dockwidget.x_label_lineEdit.editingFinished.connect(
            functools.partial(self.x_label_changed, index))
        dockwidget.x_unit_lineEdit.editingFinished.connect(
            functools.partial(self.x_unit_changed, index))
        dockwidget.y_label_lineEdit.editingFinished.connect(
            functools.partial(self.y_label_changed, index))
        dockwidget.y_unit_lineEdit.editingFinished.connect(
            functools.partial(self.y_unit_changed, index))

        dockwidget.x_auto_PushButton.clicked.connect(
            functools.partial(self.x_auto_range_clicked, index))
        dockwidget.y_auto_PushButton.clicked.connect(
            functools.partial(self.y_auto_range_clicked, index))
        dockwidget.save_pushButton.clicked.connect(functools.partial(self.save_clicked, index))
        dockwidget.remove_pushButton.clicked.connect(functools.partial(self.remove_clicked, index))
        self._pg_signal_proxys[index][0] = SignalProxy(
            dockwidget.plot_PlotWidget.sigXRangeChanged,
            delay=0.2,
            slot=lambda args: self._pyqtgraph_x_limits_changed(index, args[1]))
        self._pg_signal_proxys[index][1] = SignalProxy(
            dockwidget.plot_PlotWidget.sigYRangeChanged,
            delay=0.2,
            slot=lambda args: self._pyqtgraph_y_limits_changed(index, args[1]))

    def _disconnect_plot_signals(self, index):
        dockwidget = self._plot_dockwidgets[index].widget()
        self._fsd.sigFitsUpdated.disconnect(dockwidget.fit_comboBox.setFitFunctions)
        dockwidget.fit_pushButton.clicked.disconnect()

        dockwidget.x_lower_limit_DoubleSpinBox.valueChanged.disconnect()
        dockwidget.x_upper_limit_DoubleSpinBox.valueChanged.disconnect()
        dockwidget.y_lower_limit_DoubleSpinBox.valueChanged.disconnect()
        dockwidget.y_upper_limit_DoubleSpinBox.valueChanged.disconnect()

        dockwidget.x_label_lineEdit.editingFinished.disconnect()
        dockwidget.x_unit_lineEdit.editingFinished.disconnect()
        dockwidget.y_label_lineEdit.editingFinished.disconnect()
        dockwidget.y_unit_lineEdit.editingFinished.disconnect()

        dockwidget.x_auto_PushButton.clicked.disconnect()
        dockwidget.y_auto_PushButton.clicked.disconnect()
        dockwidget.save_pushButton.clicked.disconnect()
        dockwidget.remove_pushButton.clicked.disconnect()
        for sig_proxy in self._pg_signal_proxys[index]:
            sig_proxy.sigDelayed.disconnect()
            sig_proxy.disconnect()

    @property
    def pen_color_list(self):
        return self._pen_color_list.copy()

    @pen_color_list.setter
    def pen_color_list(self, value):
        if not isinstance(value, (list, tuple)) or len(value) < 1:
            self.log.warning(
                'The parameter pen_color_list needs to be a list of strings but was "{0}".'
                ' Will use the following old pen colors: {1}.'
                ''.format(value, self._pen_color_list))
            return
        for index, color in enumerate(self._pen_color_list):
            if (isinstance(color, (list, tuple)) and len(color) == 3) or \
                    (isinstance(color, str) and color in self._allowed_colors):
                pass
            else:
                self.log.warning('The color was "{0}" but needs to be from this list: {1} '
                                 'or a 3 element tuple with values from 0 to 255 for RGB.'
                                 ''.format(color, self._allowed_colors))
                return
        else:
            self._pen_color_list = list(value)

    def restore_side_by_side_view(self):
        """ Restore the arrangement of DockWidgets to the default """
        self.restore_view(alignment='side_by_side')

    def restore_arc_view(self):
        """ Restore the arrangement of DockWidgets to the default """
        self.restore_view(alignment='arc')

    def restore_tabbed_view(self):
        """ Restore the arrangement of DockWidgets to the default """
        self.restore_view(alignment='tabbed')

    @QtCore.Slot()
    def restore_view(self, alignment=None):
        """ Restore the arrangement of DockWidgets to the default """

        if alignment is None:
            alignment = self.widget_alignment
        if alignment not in ('side_by_side', 'arc', 'tabbed'):
            alignment = 'tabbed'
        self.widget_alignment = alignment

        self._mw.setDockNestingEnabled(True)
        self._mw.centralwidget.setVisible(False)

        for i, dockwidget in enumerate(self._plot_dockwidgets):
            dockwidget.show()
            dockwidget.setFloating(False)
            dockwidget.widget().show_fit_checkBox.setChecked(False)
            dockwidget.widget().show_controls_checkBox.setChecked(False)
            if alignment == 'tabbed':
                self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, dockwidget)
                if i > 0:
                    self._mw.tabifyDockWidget(self._plot_dockwidgets[0], dockwidget)
            elif alignment == 'arc':
                mod = i % 3
                if mod == 0:
                    self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, dockwidget)
                    if i > 2:
                        self._mw.tabifyDockWidget(self._plot_dockwidgets[0], dockwidget)
                elif mod == 1:
                    self._mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dockwidget)
                    if i > 2:
                        self._mw.tabifyDockWidget(self._plot_dockwidgets[1], dockwidget)
                elif mod == 2:
                    self._mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dockwidget)
                    if i > 2:
                        self._mw.tabifyDockWidget(self._plot_dockwidgets[2], dockwidget)
            elif alignment == 'side_by_side':
                self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, dockwidget)
        if alignment == 'arc':
            if len(self._plot_dockwidgets) > 2:
                self._mw.resizeDocks([self._plot_dockwidgets[1], self._plot_dockwidgets[2]],
                                     [1, 1],
                                     QtCore.Qt.Horizontal)
        elif alignment == 'side_by_side':
            self._mw.resizeDocks(
                self._plot_dockwidgets, [1]*len(self._plot_dockwidgets), QtCore.Qt.Horizontal)

    @QtCore.Slot(int, list, list, bool)
    def update_data(self, plot_index, x_data=None, y_data=None, clear_old=None):
        """ Function creates empty plots, grabs the data and sends it to them. """
        if not (0 <= plot_index < len(self._plot_dockwidgets)):
            self.log.warning('Tried to update plot with invalid index {0:d}'.format(plot_index))
            return

        if x_data is None:
            x_data = self._plot_logic.get_x_data(plot_index)
        if y_data is None:
            y_data = self._plot_logic.get_y_data(plot_index)
        if clear_old is None:
            clear_old = self._plot_logic.clear_old_data(plot_index)

        dockwidget = self._plot_dockwidgets[plot_index].widget()
        if clear_old:
            dockwidget.plot_PlotWidget.clear()
            self._pen_colors[plot_index] = cycle(self._pen_color_list)

        self._plot_curves[plot_index] = list()
        self._fit_curves[plot_index] = list()

        for line, xd in enumerate(x_data):
            yd = y_data[line]
            pen_color = next(self._pen_colors[plot_index])
            self._plot_curves[plot_index].append(dockwidget.plot_PlotWidget.plot(
                pen=mkColor(pen_color),
                symbol='d',
                symbolSize=6,
                symbolBrush=mkColor(pen_color)))
            self._plot_curves[plot_index][-1].setData(x=xd, y=yd)
            self._fit_curves[plot_index].append(dockwidget.plot_PlotWidget.plot())
            self._fit_curves[plot_index][-1].setPen('r')

    @QtCore.Slot(int)
    @QtCore.Slot(int, dict)
    def update_plot_parameters(self, plot_index, params=None):
        """ Function updated limits, labels and units in the plot and parameter widgets. """
        if not (0 <= plot_index < len(self._plot_dockwidgets)):
            self.log.warning('Tried to update plot with invalid index {0:d}'.format(plot_index))
            return

        dockwidget = self._plot_dockwidgets[plot_index].widget()
        if params is None:
            params = dict()
            params['x_label'] = self._plot_logic.get_x_label(plot_index)
            params['y_label'] = self._plot_logic.get_y_label(plot_index)
            params['x_unit'] = self._plot_logic.get_x_unit(plot_index)
            params['y_unit'] = self._plot_logic.get_y_unit(plot_index)
            params['x_limits'] = self._plot_logic.get_x_limits(plot_index)
            params['y_limits'] = self._plot_logic.get_y_limits(plot_index)

        if 'x_label' in params or 'x_unit' in params:
            label = params.get('x_label', None)
            unit = params.get('x_unit', None)
            if label is None:
                label = self._plot_logic.get_x_label(plot_index)
            if unit is None:
                unit = self._plot_logic.get_x_unit(plot_index)
            dockwidget.plot_PlotWidget.setLabel('bottom', label, units=unit)
            dockwidget.x_label_lineEdit.blockSignals(True)
            dockwidget.x_unit_lineEdit.blockSignals(True)
            dockwidget.x_label_lineEdit.setText(label)
            dockwidget.x_unit_lineEdit.setText(unit)
            dockwidget.x_label_lineEdit.blockSignals(False)
            dockwidget.x_unit_lineEdit.blockSignals(False)
        if 'y_label' in params or 'y_unit' in params:
            label = params.get('y_label', None)
            unit = params.get('y_unit', None)
            if label is None:
                label = self._plot_logic.get_y_label(plot_index)
            if unit is None:
                unit = self._plot_logic.get_y_unit(plot_index)
            dockwidget.plot_PlotWidget.setLabel('left', label, units=unit)
            dockwidget.y_label_lineEdit.blockSignals(True)
            dockwidget.y_unit_lineEdit.blockSignals(True)
            dockwidget.y_label_lineEdit.setText(label)
            dockwidget.y_unit_lineEdit.setText(unit)
            dockwidget.y_label_lineEdit.blockSignals(False)
            dockwidget.y_unit_lineEdit.blockSignals(False)
        if 'x_limits' in params:
            limits = params['x_limits']
            self._pg_signal_proxys[plot_index][0].block = True
            dockwidget.plot_PlotWidget.setXRange(*limits, padding=0)
            self._pg_signal_proxys[plot_index][0].block = False
            dockwidget.x_lower_limit_DoubleSpinBox.blockSignals(True)
            dockwidget.x_upper_limit_DoubleSpinBox.blockSignals(True)
            dockwidget.x_lower_limit_DoubleSpinBox.setValue(limits[0])
            dockwidget.x_upper_limit_DoubleSpinBox.setValue(limits[1])
            dockwidget.x_lower_limit_DoubleSpinBox.blockSignals(False)
            dockwidget.x_upper_limit_DoubleSpinBox.blockSignals(False)
        if 'y_limits' in params:
            limits = params['y_limits']
            self._pg_signal_proxys[plot_index][1].block = True
            dockwidget.plot_PlotWidget.setYRange(*limits, padding=0)
            self._pg_signal_proxys[plot_index][1].block = False
            dockwidget.y_lower_limit_DoubleSpinBox.blockSignals(True)
            dockwidget.y_upper_limit_DoubleSpinBox.blockSignals(True)
            dockwidget.y_lower_limit_DoubleSpinBox.setValue(limits[0])
            dockwidget.y_upper_limit_DoubleSpinBox.setValue(limits[1])
            dockwidget.y_lower_limit_DoubleSpinBox.blockSignals(False)
            dockwidget.y_upper_limit_DoubleSpinBox.blockSignals(False)

    def save_clicked(self, plot_index):
        """ Handling the save button to save the data into a file. """
        self._flush_pg_proxy(plot_index)
        self._plot_logic.save_data(plot_index=plot_index)

    def save_all_clicked(self):
        """ Handling the save button to save the data into a file. """
        for plot_index, _ in enumerate(self._plot_dockwidgets):
            self.save_clicked(plot_index)

    def remove_clicked(self, plot_index):
        self._flush_pg_proxy(plot_index)
        self.sigRemovePlotClicked.emit(plot_index)

    def x_auto_range_clicked(self, plot_index):
        """ Set the parameter_1_x_limits to the min/max of the data values """
        self.sigAutoRangeClicked.emit(plot_index, True, False)

    def y_auto_range_clicked(self, plot_index):
        """ Set the parameter_1_y_limits to the min/max of the data values """
        self.sigAutoRangeClicked.emit(plot_index, False, True)

    def x_limits_changed(self, plot_index):
        """ Handling the change of the parameter_1_x_limits. """
        dockwidget = self._plot_dockwidgets[plot_index].widget()
        self.sigPlotParametersChanged.emit(
            plot_index,
            {'x_limits': [dockwidget.x_lower_limit_DoubleSpinBox.value(),
                          dockwidget.x_upper_limit_DoubleSpinBox.value()]})

    def y_limits_changed(self, plot_index):
        """ Handling the change of the parameter_1_y_limits. """
        dockwidget = self._plot_dockwidgets[plot_index].widget()
        self.sigPlotParametersChanged.emit(
            plot_index,
            {'y_limits': [dockwidget.y_lower_limit_DoubleSpinBox.value(),
                          dockwidget.y_upper_limit_DoubleSpinBox.value()]})

    def x_label_changed(self, plot_index):
        """ Set the x-label """
        dockwidget = self._plot_dockwidgets[plot_index].widget()
        self.sigPlotParametersChanged.emit(plot_index,
                                           {'x_label': dockwidget.x_label_lineEdit.text()})

    def y_label_changed(self, plot_index):
        """ Set the y-label and the uni of plot 1 """
        dockwidget = self._plot_dockwidgets[plot_index].widget()
        self.sigPlotParametersChanged.emit(plot_index,
                                           {'y_label': dockwidget.y_label_lineEdit.text()})

    def x_unit_changed(self, plot_index):
        """ Set the x-label """
        dockwidget = self._plot_dockwidgets[plot_index].widget()
        self.sigPlotParametersChanged.emit(plot_index,
                                           {'x_unit': dockwidget.x_unit_lineEdit.text()})

    def y_unit_changed(self, plot_index):
        """ Set the y-label and the uni of plot 1 """
        dockwidget = self._plot_dockwidgets[plot_index].widget()
        self.sigPlotParametersChanged.emit(plot_index,
                                           {'y_unit': dockwidget.y_unit_lineEdit.text()})

    def fit_clicked(self, plot_index=0):
        """ Triggers the fit to be done. Attention, this runs in the GUI thread. """
        current_fit_method = self._plot_dockwidgets[plot_index].widget().fit_comboBox.getCurrentFit()[0]
        self.sigDoFit.emit(current_fit_method, plot_index)

    @QtCore.Slot(int, np.ndarray, str, str)
    def update_fit_data(self, plot_index, fit_data=None, formatted_fitresult=None, fit_method=None):
        """ Function that handles the fit results received from the logic via a signal.

        @param int plot_index: index of the plot the fit was performed for in the range for 0 to 2
        @param 3-dimensional np.ndarray fit_data: the fit data in a 2-d array for each data set
        @param str formatted_fitresult: string containing the parameters already formatted
        @param str fit_method: the fit_method used
        """
        dockwidget = self._plot_dockwidgets[plot_index].widget()

        if fit_data is None or formatted_fitresult is None or fit_method is None:
            fit_data, formatted_fitresult, fit_method = self._plot_logic.get_fit_data(plot_index)

        if not fit_method:
            fit_method = 'No Fit'

        dockwidget.fit_comboBox.blockSignals(True)

        dockwidget.show_fit_checkBox.setChecked(True)
        dockwidget.fit_textBrowser.clear()
        dockwidget.fit_comboBox.setCurrentFit(fit_method)
        if fit_method == 'No Fit':
            for index, curve in enumerate(self._fit_curves[plot_index]):
                if curve in dockwidget.plot_PlotWidget.items():
                    dockwidget.plot_PlotWidget.removeItem(curve)
        else:
            dockwidget.fit_textBrowser.setPlainText(formatted_fitresult)
            for index, curve in enumerate(self._fit_curves[plot_index]):
                if curve not in dockwidget.plot_PlotWidget.items():
                    dockwidget.plot_PlotWidget.addItem(curve)
                curve.setData(x=fit_data[index][0], y=fit_data[index][1])

        dockwidget.fit_comboBox.blockSignals(False)

    def _pyqtgraph_x_limits_changed(self, plot_index, limits):
        plot_item = self._plot_dockwidgets[plot_index].widget().plot_PlotWidget.getPlotItem()
        if plot_item.ctrl.logXCheck.isChecked() or plot_item.ctrl.fftCheck.isChecked():
            return
        self.sigPlotParametersChanged.emit(plot_index, {'x_limits': limits})

    def _pyqtgraph_y_limits_changed(self, plot_index, limits):
        plot_item = self._plot_dockwidgets[plot_index].widget().plot_PlotWidget.getPlotItem()
        if plot_item.ctrl.logYCheck.isChecked() or plot_item.ctrl.fftCheck.isChecked():
            return
        self.sigPlotParametersChanged.emit(plot_index, {'y_limits': limits})

    def _flush_pg_proxy(self, plot_index):
        x_proxy, y_proxy = self._pg_signal_proxys[plot_index]
        x_proxy.flush()
        y_proxy.flush()
