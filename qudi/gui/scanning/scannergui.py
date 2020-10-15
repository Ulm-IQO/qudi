# -*- coding: utf-8 -*-

"""
This file contains the Qudi GUI for general Confocal control.

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
import pyqtgraph as pg
from PySide2 import QtCore, QtGui, QtWidgets

import qudi.core.gui.uic as uic
from qudi.core import qudi_slot
from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.core.configoption import ConfigOption
from qudi.interface.scanning_probe_interface import ScanData
from qudi.core.gui.qtwidgets.scan_widget import ScanImageItem, ScanWidget
from qudi.core.gui.qtwidgets.scientific_spinbox import ScienDSpinBox
from qudi.core.gui.qtwidgets.slider import DoubleSlider
from qudi.core.module import GuiBase
from qudi.core.gui.colordefs import QudiPalettePale as palette


class ConfocalMainWindow(QtWidgets.QMainWindow):
    """ Create the Mainwindow based on the corresponding *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_scannergui.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        return

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.action_utility_zoom.setChecked(not self.action_utility_zoom.isChecked())
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)
        return


class ScannerControlDockWidget(QtWidgets.QDockWidget):
    """ Create the scanner control dockwidget based on the corresponding *.ui file.
    """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_scanner_control_widget.ui')

        super().__init__('Scanner Control')
        self.setObjectName('scanner_control_dockWidget')

        # Load UI file
        widget = QtWidgets.QWidget()
        uic.loadUi(ui_file, widget)
        widget.setObjectName('scanner_control_widget')

        self.setWidget(widget)
        return


class Scan2dDockWidget(QtWidgets.QDockWidget):
    """ Create the 2D scan dockwidget based on the corresponding *.ui file.
    """

    def __init__(self, axes, channel_units):
        # Get the path to the *.ui file
        dock_title = '{0}-{1} Scan'.format(axes[0].name.title(), axes[1].name.title())
        super().__init__(dock_title)
        self.setObjectName('{0}_{1}_scan_dockWidget'.format(axes[0].name, axes[1].name))

        self.scan_widget = ScanWidget()
        self.toggle_scan_button = self.scan_widget.toggle_scan_button
        self.channel_combobox = self.scan_widget.channel_selection_combobox
        self.scan_widget.set_axis_label('bottom', label=axes[0].name.title(), unit=axes[0].unit)
        self.scan_widget.set_axis_label('left', label=axes[1].name.title(), unit=axes[1].unit)
        self.scan_widget.set_data_channels(channel_units)

        self.setWidget(self.scan_widget)
        return


class Scan1dDockWidget(QtWidgets.QDockWidget):
    """ Create the 1D scan dockwidget based on the corresponding *.ui file.
    """

    def __init__(self, axis_name):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_1d_scan_widget.ui')

        dock_title = '{0} Scan'.format(axis_name)

        super().__init__(dock_title)
        self.setObjectName('{0}_scan_dockWidget'.format(axis_name))

        # Load UI file
        widget = QtWidgets.QWidget()
        uic.loadUi(ui_file, widget)
        widget.setObjectName('{0}_scan_widget'.format(axis_name))

        self.toggle_scan_button = widget.toggle_scan_pushButton
        self.channel_combobox = widget.channel_comboBox
        self.channel_set = set()
        self.plot_widget = widget.scan_plotWidget
        self.plot_item = pg.PlotDataItem(x=np.arange(2), y=np.zeros(2), pen=pg.mkPen(palette.c1))
        self.plot_widget.addItem(self.plot_item)

        self.setWidget(widget)
        return


class OptimizerDockWidget(QtWidgets.QDockWidget):
    """ Create the optimizer dockwidget based on the corresponding *.ui file.
    """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_optimizer_widget.ui')

        super().__init__('Optimizer')
        self.setObjectName('optimizer_dockWidget')

        # Load UI file
        widget = QtWidgets.QWidget()
        uic.loadUi(ui_file, widget)
        widget.setObjectName('optimizer_widget')

        self.plot_widget = widget.optimizer_1d_plotWidget
        self.scan_widget = widget.optimizer_2d_scanPlotWidget
        self.axes_label = widget.optimizer_axes_label
        self.position_label = widget.optimizer_position_label
        self.image_item = ScanImageItem(image=np.zeros((2, 2)))
        self.plot_item = pg.PlotDataItem(x=np.arange(10),
                                         y=np.zeros(10),
                                         pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                                         symbol='o',
                                         symbolPen=palette.c1,
                                         symbolBrush=palette.c1,
                                         symbolSize=7)
        self.fit_plot_item = pg.PlotDataItem(x=np.arange(10),
                                             y=np.zeros(10),
                                             pen=pg.mkPen(palette.c2))
        self.plot_widget.addItem(self.plot_item)
        self.plot_widget.addItem(self.fit_plot_item)
        self.scan_widget.addItem(self.image_item)

        self.setWidget(widget)
        self.plot_widget.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.scan_widget.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.position_label.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        return


class ScannerSettingDialog(QtWidgets.QDialog):
    """ Create the ScannerSettingsDialog window, based on the corresponding *.ui file."""

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_scanner_settings.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        return


class OptimizerSettingDialog(QtWidgets.QDialog):
    """ User configurable settings for the optimizer embedded in cofocal gui"""

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_optimizer_settings.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        return


class ScannerGui(GuiBase):
    """ Main Confocal Class for xy and depth scans.
    """

    # declare connectors
    _scanning_logic = Connector(name='scanning_logic', interface='ScanningProbeLogic')
    _data_logic = Connector(name='data_logic', interface='ScanningDataLogic')
    _optimize_logic = Connector(name='optimize_logic', interface='ScanningOptimizeLogic')

    # config options for gui
    _default_position_unit_prefix = ConfigOption(name='default_position_unit_prefix', default=None)

    # status vars
    _show_true_scanner_position = StatusVar(name='show_true_scanner_position', default=True)
    _window_state = StatusVar(name='window_state', default=None)
    _window_geometry = StatusVar(name='window_geometry', default=None)

    # signals
    sigScannerTargetChanged = QtCore.Signal(dict, object)
    sigScanSettingsChanged = QtCore.Signal(dict)
    sigToggleScan = QtCore.Signal(bool, tuple)
    sigOptimizerSettingsChanged = QtCore.Signal(dict)
    sigToggleOptimize = QtCore.Signal(bool)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # QMainWindow and QDialog child instances
        self._mw = None
        self._ssd = None
        self._osd = None

        # References to automatically generated GUI elements
        self.axes_control_widgets = None
        self.optimizer_settings_axes_widgets = None
        self.scanner_settings_axes_widgets = None
        self.scan_2d_dockwidgets = None
        self.scan_1d_dockwidgets = None

        # References to static dockwidgets
        self.optimizer_dockwidget = None
        self.scanner_control_dockwidget = None
        return

    def on_activate(self):
        """ Initializes all needed UI files and establishes the connectors.

        This method executes the all the inits for the differnt GUIs and passes
        the event argument from fysom to the methods.
        """
        self.scan_2d_dockwidgets = dict()
        self.scan_1d_dockwidgets = dict()

        # Initialize main window
        self._mw = ConfocalMainWindow()

        # Initialize fixed dockwidgets
        self._init_static_dockwidgets()

        # Initialize dialog windows
        self._init_optimizer_settings()
        self._init_scanner_settings()

        # Configure widgets according to available scan axes and apply scanner constraints
        self._generate_axes_control_widgets()

        # Automatically generate scanning widgets for desired scans
        scans = list()
        axes = tuple(self._scanning_logic().scanner_axes)
        for i, first_ax in enumerate(axes, 1):
            for second_ax in axes[i:]:
                scans.append((first_ax, second_ax))
        for scan in scans:
            self._add_scan_dockwidget(scan)

        # Initialize widget data
        self.update_scanner_settings()
        self.scanner_target_updated()
        self.scanner_position_updated()
        self.scan_data_updated()

        # Initialize dockwidgets to default view
        self.restore_default_view()
        # Try to restore window state and geometry
        if self._window_geometry is not None:
            if not self._mw.restoreGeometry(bytearray.fromhex(self._window_geometry)):
                self._window_geometry = None
                self.log.debug(
                    'Unable to restore previous window geometry. Falling back to default.')
        if self._window_state is not None:
            if not self._mw.restoreState(bytearray.fromhex(self._window_state)):
                self._window_state = None
                self.log.debug(
                    'Unable to restore previous window state. Falling back to default.')

        # Connect signals
        self.sigScannerTargetChanged.connect(
            self._scanning_logic().set_scanner_target_position, QtCore.Qt.QueuedConnection
        )
        self.sigScanSettingsChanged.connect(
            self._scanning_logic().set_scan_settings, QtCore.Qt.QueuedConnection
        )
        self.sigToggleScan.connect(self._scanning_logic().toggle_scan, QtCore.Qt.QueuedConnection)
        self.sigToggleOptimize.connect(
            self._optimize_logic().toggle_optimize, QtCore.Qt.QueuedConnection
        )

        self._mw.action_optimize_position.triggered[bool].connect(self.toggle_optimize)
        self._mw.action_restore_default_view.triggered.connect(self.restore_default_view)
        self._mw.action_utility_zoom.toggled.connect(self.toggle_cursor_zoom)
        self._mw.action_utility_full_range.triggered.connect(
            self._scanning_logic().set_full_scan_ranges, QtCore.Qt.QueuedConnection
        )
        self._mw.action_history_forward.triggered.connect(
            self._data_logic().history_next, QtCore.Qt.QueuedConnection
        )
        self._mw.action_history_back.triggered.connect(
            self._data_logic().history_previous, QtCore.Qt.QueuedConnection
        )

        self._scanning_logic().sigScannerPositionChanged.connect(
            self.scanner_position_updated, QtCore.Qt.QueuedConnection
        )
        self._scanning_logic().sigScannerTargetChanged.connect(
            self.scanner_target_updated, QtCore.Qt.QueuedConnection
        )
        self._scanning_logic().sigScanSettingsChanged.connect(
            self.update_scanner_settings, QtCore.Qt.QueuedConnection
        )
        self._scanning_logic().sigScanDataChanged.connect(
            self.scan_data_updated, QtCore.Qt.QueuedConnection
        )
        self._scanning_logic().sigScanStateChanged.connect(
            self.scan_state_updated, QtCore.Qt.QueuedConnection
        )
        self._data_logic().sigScanDataChanged.connect(
            self.scan_data_updated, QtCore.Qt.QueuedConnection
        )
        self._optimize_logic().sigOptimizeStateChanged.connect(
            self.optimize_state_updated, QtCore.Qt.QueuedConnection
        )
        self._optimize_logic().sigOptimizeScanDataChanged.connect(
            self.optimize_data_updated, QtCore.Qt.QueuedConnection
        )

        # FIXME: Dirty workaround for strange pyqtgraph autoscale behaviour
        for dockwidget in self.scan_2d_dockwidgets.values():
            dockwidget.scan_widget.autoRange()
            dockwidget.scan_widget.autoRange()

        self.show()
        return

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        # Remember window position and geometry and close window
        self._window_geometry = str(self._mw.saveGeometry().toHex(), encoding='utf-8')
        self._window_state = str(self._mw.saveState().toHex(), encoding='utf-8')
        self._mw.close()

        # Disconnect signals
        self.sigScannerTargetChanged.disconnect()
        self.sigScanSettingsChanged.disconnect()
        self.sigToggleScan.disconnect()
        self.sigToggleOptimize.disconnect()
        self._mw.action_optimize_position.triggered[bool].disconnect()
        self._mw.action_restore_default_view.triggered.disconnect()
        self._mw.action_history_forward.triggered.disconnect()
        self._mw.action_history_back.triggered.disconnect()
        self._mw.action_utility_full_range.triggered.disconnect()
        self._mw.action_utility_zoom.toggled.disconnect()
        self._scanning_logic().sigScannerPositionChanged.disconnect(self.scanner_position_updated)
        self._scanning_logic().sigScannerTargetChanged.disconnect(self.scanner_target_updated)
        self._scanning_logic().sigScanSettingsChanged.disconnect(self.update_scanner_settings)
        self._scanning_logic().sigScanDataChanged.disconnect(self.scan_data_updated)
        self._scanning_logic().sigScanStateChanged.disconnect(self.scan_state_updated)
        self._optimize_logic().sigOptimizeScanDataChanged.disconnect(self.optimize_data_updated)
        self._optimize_logic().sigOptimizeStateChanged.disconnect(self.optimize_state_updated)
        self._data_logic().sigScanDataChanged.disconnect(self.scan_data_updated)

        for scan in tuple(self.scan_1d_dockwidgets):
            self._remove_scan_dockwidget(scan)
        for scan in tuple(self.scan_2d_dockwidgets):
            self._remove_scan_dockwidget(scan)
        self._clear_axes_control_widgets()
        self._clear_optimizer_axes_widgets()
        return

    def show(self):
        """Make main window visible and put it above all other windows. """
        # Show the Main Confocal GUI:
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def _init_optimizer_settings(self):
        """ Configuration and initialisation of the optimizer settings dialog.
        """
        # Create the Settings window
        self._osd = OptimizerSettingDialog()

        # Connect MainWindow actions
        self._mw.action_optimizer_settings.triggered.connect(lambda x: self._osd.exec_())

        # Create dynamically created widgets
        self._generate_optimizer_axes_widgets()

        # Constraint dialog size
        self._osd.layout().setSizeConstraint(QtWidgets.QLayout.SetFixedSize)

        # Connect the action of the settings window with the code:
        self._osd.accepted.connect(self.change_optimizer_settings)
        self._osd.rejected.connect(self.update_optimizer_settings)
        self._osd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(
            self.change_optimizer_settings)
        return

    def _init_scanner_settings(self):
        """
        """
        # Create the Settings dialog
        self._ssd = ScannerSettingDialog()

        # Connect MainWindow actions
        self._mw.action_scanner_settings.triggered.connect(lambda x: self._ssd.exec_())

        # Create dynamically created widgets
        self._generate_settings_axes_widgets()

        # Constraint dialog size
        self._ssd.layout().setSizeConstraint(QtWidgets.QLayout.SetFixedSize)

        # Connect the action of the settings dialog with the GUI module:
        self._ssd.accepted.connect(self.change_scanner_settings)
        self._ssd.rejected.connect(self.restore_scanner_settings)
        self._ssd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(
            self.change_scanner_settings
        )

    def _init_static_dockwidgets(self):
        self.optimizer_dockwidget = OptimizerDockWidget()
        self.optimizer_dockwidget.setAllowedAreas(QtCore.Qt.TopDockWidgetArea)
        self.optimizer_dockwidget.scan_widget.add_crosshair(movable=False,
                                                            pen={'color': '#00ff00', 'width': 2})
        self.optimizer_dockwidget.scan_widget.setAspectLocked(lock=True, ratio=1.0)
        self.optimizer_dockwidget.visibilityChanged.connect(
            self._mw.action_view_optimizer.setChecked)
        self._mw.action_view_optimizer.triggered[bool].connect(
            self.optimizer_dockwidget.setVisible)

        self.scanner_control_dockwidget = ScannerControlDockWidget()
        self.scanner_control_dockwidget.setAllowedAreas(QtCore.Qt.BottomDockWidgetArea)
        self.scanner_control_dockwidget.visibilityChanged.connect(
            self._mw.action_view_scanner_control.setChecked)
        self._mw.action_view_scanner_control.triggered[bool].connect(
            self.scanner_control_dockwidget.setVisible)

        self._mw.util_toolBar.visibilityChanged.connect(
            self._mw.action_view_toolbar.setChecked)
        self._mw.action_view_toolbar.triggered[bool].connect(self._mw.util_toolBar.setVisible)

    def _generate_axes_control_widgets(self):
        font = QtGui.QFont()
        font.setBold(True)
        layout = self.scanner_control_dockwidget.widget().layout()
        self.axes_control_widgets = dict()
        for index, (ax_name, axis) in enumerate(self._scanning_logic().scanner_axes.items(), 1):
            label = QtWidgets.QLabel('{0}-Axis:'.format(ax_name.title()))
            label.setObjectName('{0}_axis_label'.format(ax_name))
            label.setFont(font)
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

            res_spinbox = QtWidgets.QSpinBox()
            res_spinbox.setObjectName('{0}_resolution_spinBox'.format(ax_name))
            res_spinbox.setRange(axis.min_resolution, min(2 ** 31 - 1, axis.max_resolution))
            res_spinbox.setSuffix('px')
            res_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            res_spinbox.setMinimumSize(50, 0)
            res_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                      QtWidgets.QSizePolicy.Preferred)

            min_spinbox = ScienDSpinBox()
            if self._default_position_unit_prefix is not None:
                min_spinbox.assumed_unit_prefix = self._default_position_unit_prefix
            min_spinbox.setObjectName('{0}_min_range_scienDSpinBox'.format(ax_name))
            min_spinbox.setRange(*axis.value_range)
            min_spinbox.setSuffix(axis.unit)
            min_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            min_spinbox.setMinimumSize(75, 0)
            min_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                      QtWidgets.QSizePolicy.Preferred)

            max_spinbox = ScienDSpinBox()
            if self._default_position_unit_prefix is not None:
                max_spinbox.assumed_unit_prefix = self._default_position_unit_prefix
            max_spinbox.setObjectName('{0}_max_range_scienDSpinBox'.format(ax_name))
            max_spinbox.setRange(*axis.value_range)
            max_spinbox.setSuffix(axis.unit)
            max_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            max_spinbox.setMinimumSize(75, 0)
            max_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                      QtWidgets.QSizePolicy.Preferred)

            slider = DoubleSlider(QtCore.Qt.Horizontal)
            slider.setObjectName('{0}_position_doubleSlider'.format(ax_name))
            slider.setRange(*axis.value_range)
            if axis.min_step > 0:
                slider.set_granularity(round((axis.max_value - axis.min_value) / axis.min_step) + 1)
            else:
                slider.set_granularity(2**16-1)
            slider.setMinimumSize(150, 0)
            slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

            pos_spinbox = ScienDSpinBox()
            if self._default_position_unit_prefix is not None:
                pos_spinbox.assumed_unit_prefix = self._default_position_unit_prefix
            pos_spinbox.setObjectName('{0}_position_scienDSpinBox'.format(ax_name))
            pos_spinbox.setRange(*axis.value_range)
            pos_spinbox.setSuffix(axis.unit)
            pos_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            pos_spinbox.setMinimumSize(75, 0)
            pos_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                      QtWidgets.QSizePolicy.Preferred)

            # Add to layout
            layout.addWidget(label, index, 0)
            layout.addWidget(res_spinbox, index, 1)
            layout.addWidget(min_spinbox, index, 3)
            layout.addWidget(max_spinbox, index, 4)
            layout.addWidget(slider, index, 6)
            layout.addWidget(pos_spinbox, index, 7)

            # Connect signals
            min_spinbox.editingFinished.connect(self.__get_axis_scan_range_update_func(ax_name))
            max_spinbox.editingFinished.connect(self.__get_axis_scan_range_update_func(ax_name))
            res_spinbox.editingFinished.connect(self.__get_axis_scan_res_update_func(ax_name))
            slider.doubleSliderMoved.connect(self.__get_slider_update_func(ax_name, slider))
            pos_spinbox.editingFinished.connect(
                self.__get_target_spinbox_update_func(ax_name, pos_spinbox)
            )

            # Remember widgets references for later access
            self.axes_control_widgets[ax_name] = dict()
            self.axes_control_widgets[ax_name]['label'] = label
            self.axes_control_widgets[ax_name]['res_spinbox'] = res_spinbox
            self.axes_control_widgets[ax_name]['min_spinbox'] = min_spinbox
            self.axes_control_widgets[ax_name]['max_spinbox'] = max_spinbox
            self.axes_control_widgets[ax_name]['slider'] = slider
            self.axes_control_widgets[ax_name]['pos_spinbox'] = pos_spinbox

        layout.addWidget(self.scanner_control_dockwidget.widget().line, 0, 2, -1, 1)
        layout.addWidget(self.scanner_control_dockwidget.widget().line_2, 0, 5, -1, 1)
        layout.setColumnStretch(5, 1)
        self.scanner_control_dockwidget.widget().setMaximumHeight(
            self.scanner_control_dockwidget.widget().sizeHint().height())
        return

    def _clear_axes_control_widgets(self):
        layout = self.scanner_control_dockwidget.widget().layout()
        for axis in tuple(self.axes_control_widgets):
            # Disconnect signals
            self.axes_control_widgets[axis]['min_spinbox'].editingFinished.disconnect()
            self.axes_control_widgets[axis]['max_spinbox'].editingFinished.disconnect()
            self.axes_control_widgets[axis]['res_spinbox'].editingFinished.disconnect()
            self.axes_control_widgets[axis]['slider'].valueChanged.disconnect()
            self.axes_control_widgets[axis]['pos_spinbox'].editingFinished.disconnect()

            # Remove from layout
            layout.removeWidget(self.axes_control_widgets[axis]['label'])
            layout.removeWidget(self.axes_control_widgets[axis]['min_spinbox'])
            layout.removeWidget(self.axes_control_widgets[axis]['max_spinbox'])
            layout.removeWidget(self.axes_control_widgets[axis]['res_spinbox'])
            layout.removeWidget(self.axes_control_widgets[axis]['slider'])
            layout.removeWidget(self.axes_control_widgets[axis]['pos_spinbox'])

            # Mark widgets for deletion in Qt framework
            self.axes_control_widgets[axis]['label'].deleteLater()
            self.axes_control_widgets[axis]['min_spinbox'].deleteLater()
            self.axes_control_widgets[axis]['max_spinbox'].deleteLater()
            self.axes_control_widgets[axis]['res_spinbox'].deleteLater()
            self.axes_control_widgets[axis]['slider'].deleteLater()
            self.axes_control_widgets[axis]['pos_spinbox'].deleteLater()

        self.axes_control_widgets = dict()
        return

    def _generate_optimizer_axes_widgets(self):
        layout = self._osd.scan_ranges_gridLayout
        self.optimizer_settings_axes_widgets = dict()
        for index, (ax_name, axis) in enumerate(self._scanning_logic().scanner_axes.items(), 1):
            label = QtWidgets.QLabel('{0}-Axis:'.format(ax_name))
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

            range_spinbox = ScienDSpinBox()
            if self._default_position_unit_prefix is not None:
                range_spinbox.assumed_unit_prefix = self._default_position_unit_prefix
            range_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            range_spinbox.setRange(0, axis.max_value - axis.min_value)
            range_spinbox.setSuffix(axis.unit)
            range_spinbox.setMinimumSize(70, 0)
            range_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                        QtWidgets.QSizePolicy.Preferred)

            res_spinbox = QtWidgets.QSpinBox()
            res_spinbox.setRange(axis.min_resolution, min(2 ** 31 - 1, axis.max_resolution))
            res_spinbox.setSuffix('px')
            res_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            res_spinbox.setMinimumSize(70, 0)
            res_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                      QtWidgets.QSizePolicy.Preferred)

            freq_spinbox = ScienDSpinBox()
            freq_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            freq_spinbox.setRange(*axis.frequency_range)
            freq_spinbox.setSuffix('Hz')
            freq_spinbox.setMinimumSize(70, 0)
            freq_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                       QtWidgets.QSizePolicy.Preferred)

            # Add to layout
            layout.addWidget(label, index, 0)
            layout.addWidget(range_spinbox, index, 1)
            layout.addWidget(res_spinbox, index, 2)
            layout.addWidget(freq_spinbox, index, 3)

            # Remember widgets references for later access
            self.optimizer_settings_axes_widgets[ax_name] = dict()
            self.optimizer_settings_axes_widgets[ax_name]['label'] = label
            self.optimizer_settings_axes_widgets[ax_name]['range_spinbox'] = range_spinbox
            self.optimizer_settings_axes_widgets[ax_name]['res_spinbox'] = res_spinbox
            self.optimizer_settings_axes_widgets[ax_name]['freq_spinbox'] = res_spinbox
        return

    def _clear_optimizer_axes_widgets(self):
        layout = self._osd.scan_ranges_gridLayout
        for axis in tuple(self.optimizer_settings_axes_widgets):
            # Remove from layout
            layout.removeWidget(self.optimizer_settings_axes_widgets[axis]['label'])
            layout.removeWidget(self.optimizer_settings_axes_widgets[axis]['range_spinbox'])
            layout.removeWidget(self.optimizer_settings_axes_widgets[axis]['res_spinbox'])
            layout.removeWidget(self.optimizer_settings_axes_widgets[axis]['freq_spinbox'])

            # Mark widgets for deletion in Qt framework
            self.optimizer_settings_axes_widgets[axis]['label'].deleteLater()
            self.optimizer_settings_axes_widgets[axis]['range_spinbox'].deleteLater()
            self.optimizer_settings_axes_widgets[axis]['res_spinbox'].deleteLater()
            self.optimizer_settings_axes_widgets[axis]['freq_spinbox'].deleteLater()

        self.optimizer_settings_axes_widgets = dict()
        return

    def _generate_settings_axes_widgets(self):
        layout = self._ssd.axes_settings_gridLayout
        self.scanner_settings_axes_widgets = dict()
        for index, (ax_name, axis) in enumerate(self._scanning_logic().scanner_axes.items(), 2):
            label = QtWidgets.QLabel('{0}-Axis:'.format(ax_name))
            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

            forward_spinbox = ScienDSpinBox()
            forward_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            forward_spinbox.setRange(*axis.frequency_range)
            forward_spinbox.setSuffix('Hz')
            forward_spinbox.setMinimumSize(70, 0)
            forward_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                          QtWidgets.QSizePolicy.Preferred)

            backward_spinbox = ScienDSpinBox()
            backward_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            backward_spinbox.setRange(*axis.frequency_range)
            backward_spinbox.setSuffix('Hz')
            backward_spinbox.setMinimumSize(70, 0)
            backward_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                           QtWidgets.QSizePolicy.Preferred)

            # Add to layout
            layout.addWidget(label, index, 0)
            layout.addWidget(forward_spinbox, index, 1)
            layout.addWidget(backward_spinbox, index, 2)

            # Remember widgets references for later access
            self.scanner_settings_axes_widgets[ax_name] = {'label'           : label,
                                                           'forward_spinbox' : forward_spinbox,
                                                           'backward_spinbox': backward_spinbox}
        return

    def _clear_settings_axes_widgets(self):
        layout = self._ssd.axes_settings_gridLayout
        for axis in tuple(self.scanner_settings_axes_widgets):
            # Remove from layout
            layout.removeWidget(self.scanner_settings_axes_widgets[axis]['label'])
            layout.removeWidget(self.scanner_settings_axes_widgets[axis]['forward_spinbox'])
            layout.removeWidget(self.scanner_settings_axes_widgets[axis]['backward_spinbox'])

            # Mark widgets for deletion in Qt framework
            self.scanner_settings_axes_widgets[axis]['label'].deleteLater()
            self.scanner_settings_axes_widgets[axis]['forward_spinbox'].deleteLater()
            self.scanner_settings_axes_widgets[axis]['backward_spinbox'].deleteLater()

        self.scanner_settings_axes_widgets = dict()
        return

    @QtCore.Slot()
    def restore_default_view(self):
        """ Restore the arrangement of DockWidgets to default """
        self._mw.setDockNestingEnabled(True)

        # Handle dynamically created dock widgets
        for i, dockwidget in enumerate(self.scan_2d_dockwidgets.values()):
            dockwidget.show()
            dockwidget.setFloating(False)
            self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, dockwidget)
            if i > 1:
                first_dockwidget = self.scan_2d_dockwidgets[list(self.scan_2d_dockwidgets)[0]]
                self._mw.tabifyDockWidget(first_dockwidget, dockwidget)
                if i >= len(self.scan_2d_dockwidgets) - 1:
                    first_dockwidget.raise_()
        for i, dockwidget in enumerate(self.scan_1d_dockwidgets.values()):
            dockwidget.show()
            dockwidget.setFloating(False)
            self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, dockwidget)
            if i > 0:
                first_dockwidget = self.scan_1d_dockwidgets[list(self.scan_1d_dockwidgets)[0]]
                self._mw.tabifyDockWidget(first_dockwidget, dockwidget)
                if i >= len(self.scan_1d_dockwidgets) - 1:
                    first_dockwidget.raise_()

        # Handle static dock widgets
        self.optimizer_dockwidget.setFloating(False)
        self.optimizer_dockwidget.show()
        self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.optimizer_dockwidget)
        if self.scan_1d_dockwidgets:
            dockwidget = self.scan_1d_dockwidgets[list(self.scan_1d_dockwidgets)[0]]
            if self.scan_2d_dockwidgets:
                self._mw.splitDockWidget(dockwidget, self.optimizer_dockwidget, QtCore.Qt.Vertical)
            if len(self.scan_2d_dockwidgets) > 1:
                dock_list = [self.scan_2d_dockwidgets[list(self.scan_2d_dockwidgets)[0]],
                             self.scan_2d_dockwidgets[list(self.scan_2d_dockwidgets)[1]],
                             dockwidget]
                self._mw.resizeDocks(dock_list, [1, 1, 1], QtCore.Qt.Horizontal)
            elif self.scan_2d_dockwidgets:
                dock_list = [self.scan_2d_dockwidgets[list(self.scan_2d_dockwidgets)[0]],
                             dockwidget]
                self._mw.resizeDocks(dock_list, [1, 1], QtCore.Qt.Horizontal)
            else:
                dock_list = [dockwidget, self.optimizer_dockwidget]
                self._mw.resizeDocks(dock_list, [1, 1], QtCore.Qt.Horizontal)
        elif len(self.scan_2d_dockwidgets) > 1:
            dockwidget = self.scan_2d_dockwidgets[list(self.scan_2d_dockwidgets)[1]]
            self._mw.splitDockWidget(dockwidget, self.optimizer_dockwidget, QtCore.Qt.Vertical)
            dock_list = [self.scan_2d_dockwidgets[list(self.scan_2d_dockwidgets)[0]],
                         dockwidget]
            self._mw.resizeDocks(dock_list, [1, 1], QtCore.Qt.Horizontal)
        else:
            dock_list = [self.scan_2d_dockwidgets[list(self.scan_2d_dockwidgets)[0]],
                         self.optimizer_dockwidget]
            self._mw.resizeDocks(dock_list, [1, 1], QtCore.Qt.Horizontal)

        self.scanner_control_dockwidget.setFloating(False)
        self.scanner_control_dockwidget.show()
        self._mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.scanner_control_dockwidget)

        # Return toolbar to default position
        self._mw.util_toolBar.show()
        self._mw.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, self._mw.util_toolBar)
        return

    def _remove_scan_dockwidget(self, axes):
        if axes in self.scan_1d_dockwidgets:
            self._mw.removeDockWidget(self.scan_1d_dockwidgets[axes])
            self.scan_1d_dockwidgets[axes].toggle_scan_button.clicked.disconnect()
            self.scan_1d_dockwidgets[axes].deleteLater()
            del self.scan_1d_dockwidgets[axes]
        elif axes in self.scan_2d_dockwidgets:
            self._mw.removeDockWidget(self.scan_2d_dockwidgets[axes])
            self.scan_2d_dockwidgets[axes].toggle_scan_button.clicked.disconnect()
            self.scan_2d_dockwidgets[axes].scan_widget.crosshairs[
                0].sigDraggedPosChanged.disconnect()
            self.scan_2d_dockwidgets[axes].scan_widget.sigMouseAreaSelected.disconnect()
            self.scan_2d_dockwidgets[axes].channel_combobox.currentIndexChanged.disconnect()
            self.scan_2d_dockwidgets[axes].deleteLater()
            del self.scan_2d_dockwidgets[axes]
        return

    def _add_scan_dockwidget(self, axes):
        constraints = self._scanning_logic().scanner_constraints
        axes_constr = constraints.axes
        optimizer_settings = self._optimize_logic().optimize_settings
        axes = tuple(axes)
        if len(axes) == 1:
            if axes in self.scan_1d_dockwidgets:
                self.log.error('Unable to add scanning widget for axes {0}. Widget for this scan '
                               'already created. Remove old widget first.'.format(axes))
                return
            dockwidget = Scan1dDockWidget(axes[0])
            dockwidget.setAllowedAreas(QtCore.Qt.TopDockWidgetArea)
            self.scan_1d_dockwidgets[axes] = dockwidget
            self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, dockwidget)
            # Set axis labels and initial data
            dockwidget.plot_widget.setLabel('bottom', axes[0], units=axes_constr[axes[0]].unit)
            dockwidget.plot_widget.setLabel('left', 'scan data', units='arb.u.')
            this_constr = axes_constr[axes[0]]
            x_data = np.linspace(this_constr.min_value,
                                 this_constr.min_value,
                                 max(2, this_constr.min_resolution))
            dockwidget.plot_item.setData(x_data, np.full(x_data.size, this_constr.min_value))
            dockwidget.toggle_scan_button.clicked.connect(self.__get_toggle_scan_func(axes))
        else:
            if axes in self.scan_2d_dockwidgets:
                self.log.error('Unable to add scanning widget for axes {0}. Widget for this scan '
                               'already created. Remove old widget first.'.format(axes))
                return
            dockwidget = Scan2dDockWidget(
                (axes_constr[axes[0]], axes_constr[axes[1]]),
                {name: ch.unit for name, ch in constraints.channels.items()}
            )
            dockwidget.setAllowedAreas(QtCore.Qt.TopDockWidgetArea)
            self.scan_2d_dockwidgets[axes] = dockwidget
            self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, dockwidget)
            dockwidget.scan_widget.add_crosshair(movable=True, min_size_factor=0.02)
            dockwidget.scan_widget.add_crosshair(movable=False,
                                                 pen={'color': '#00ffff', 'width': 1})
            dockwidget.scan_widget.bring_crosshair_on_top(0)
            dockwidget.scan_widget.crosshairs[0].set_allowed_range(
                (axes_constr[axes[0]].value_range, axes_constr[axes[1]].value_range)
            )
            dockwidget.scan_widget.crosshairs[0].set_size(
                (optimizer_settings['scan_range'][axes[0]],
                 optimizer_settings['scan_range'][axes[1]])
            )
            if not self.show_true_scanner_position:
                dockwidget.scan_widget.hide_crosshair(1)
            dockwidget.scan_widget.toggle_zoom_by_selection(True)
            dockwidget.scan_widget.crosshairs[0].sigDraggedPosChanged.connect(
                self.__get_crosshair_update_func(axes, dockwidget.scan_widget.crosshairs[0])
            )
            dockwidget.toggle_scan_button.clicked.connect(self.__get_toggle_scan_func(axes))
            dockwidget.scan_widget.sigMouseAreaSelected.connect(
                self.__get_range_from_selection_func(axes)
            )
            # Set initial scan image
            x_constr, y_constr = axes_constr[axes[0]], axes_constr[axes[1]]
            dockwidget.scan_widget.set_image(
                np.zeros((x_constr.min_resolution, y_constr.min_resolution))
            )
            dockwidget.scan_widget.set_image_extent((x_constr.value_range, y_constr.value_range))
        return

    @property
    def show_true_scanner_position(self):
        return self._show_true_scanner_position

    @show_true_scanner_position.setter
    def show_true_scanner_position(self, show):
        self.toggle_true_scanner_position_display(show)

    @QtCore.Slot(bool)
    def toggle_cursor_zoom(self, enable):
        if self._mw.action_utility_zoom.isChecked() != enable:
            self._mw.action_utility_zoom.blockSignals(True)
            self._mw.action_utility_zoom.setChecked(enable)
            self._mw.action_utility_zoom.blockSignals(False)

        for dockwidget in self.scan_2d_dockwidgets.values():
            dockwidget.scan_widget.toggle_selection(enable)
        return

    @QtCore.Slot(bool)
    def toggle_true_scanner_position_display(self, show):
        show = bool(show)
        if show == self._show_true_scanner_position:
            return
        self._show_true_scanner_position = show
        if self._show_true_scanner_position:
            for dockwidget in self.scan_2d_dockwidgets.values():
                dockwidget.scan_widget.show_crosshair(1)
        else:
            for dockwidget in self.scan_2d_dockwidgets.values():
                dockwidget.scan_widget.hide_crosshair(1)
        return

    @QtCore.Slot()
    def change_scanner_settings(self):
        """ ToDo: Document
        """
        forward_freq = {ax: w_dict['forward_spinbox'].value() for ax, w_dict in
                        self.scanner_settings_axes_widgets.items()}
        self.sigScanSettingsChanged.emit({'frequency': forward_freq})

    @QtCore.Slot()
    def restore_scanner_settings(self):
        """ ToDo: Document
        """
        self.update_scanner_settings({'frequency': self._scanning_logic().scan_frequency})

    @QtCore.Slot()
    @QtCore.Slot(dict)
    def update_scanner_settings(self, settings=None):
        """
        Update scanner settings from logic and set widgets accordingly.

        @param dict settings: Settings dict containing the scanner settings to update.
                              If None (default) read the scanner setting from logic and update.
        """
        if not isinstance(settings, dict):
            settings = self._scanning_logic().scan_settings

        # ToDo: Handle all remaining settings

        if 'resolution' in settings:
            for axis, resolution in settings['resolution'].items():
                res_spinbox = self.axes_control_widgets[axis]['res_spinbox']
                res_spinbox.blockSignals(True)
                res_spinbox.setValue(resolution)
                res_spinbox.blockSignals(False)
        if 'range' in settings:
            for axis, axis_range in settings['range'].items():
                min_spinbox = self.axes_control_widgets[axis]['min_spinbox']
                max_spinbox = self.axes_control_widgets[axis]['max_spinbox']
                min_spinbox.blockSignals(True)
                max_spinbox.blockSignals(True)
                min_spinbox.setValue(axis_range[0])
                max_spinbox.setValue(axis_range[1])
                min_spinbox.blockSignals(False)
                max_spinbox.blockSignals(False)
        if 'frequency' in settings:
            for axis, frequency in settings['frequency'].items():
                self.scanner_settings_axes_widgets[axis]['forward_spinbox'].setValue(frequency)
        return

    def set_scanner_target_position(self, target_pos):
        """

        @param dict target_pos:
        """
        self.sigScannerTargetChanged.emit(target_pos, id(self))

    @QtCore.Slot(dict)
    @QtCore.Slot(dict, object)
    def scanner_position_updated(self, pos_dict=None, caller_id=None):
        """
        Updates the scanner position and set widgets accordingly.

        @param dict pos_dict: The scanner position dict to update each axis position.
                              If None (default) read the scanner position from logic and update.
        @param int caller_id: The qudi module object id responsible for triggering this update
        """
        # If this update has been issued by this module, do not update display.
        # This has already been done before notifying the logic.
        # Also ignore this call if the real momentary scanner position should not be shown
        if caller_id == id(self) or not self._show_true_scanner_position:
            return

        if not isinstance(pos_dict, dict):
            pos_dict = self._scanning_logic().scanner_position

        self._update_position_display(pos_dict)
        return

    @QtCore.Slot(dict)
    @QtCore.Slot(dict, object)
    def scanner_target_updated(self, pos_dict=None, caller_id=None):
        """
        Updates the scanner target and set widgets accordingly.

        @param dict pos_dict: The scanner position dict to update each axis position.
                              If None (default) read the scanner position from logic and update.
        @param int caller_id: The qudi module object id responsible for triggering this update
        """
        # If this update has been issued by this module, do not update display.
        # This has already been done before notifying the logic.
        if caller_id == id(self):
            return

        if not isinstance(pos_dict, dict):
            pos_dict = self._scanning_logic().scanner_target

        self._update_target_display(pos_dict)
        return

    @QtCore.Slot()
    @QtCore.Slot(object)
    def scan_data_updated(self, scan_data=None):
        """
        @param dict scan_data:
        """
        if not isinstance(scan_data, ScanData):
            scan_data = self._scanning_logic().scan_data
        if scan_data is None:
            return

        if scan_data.scan_dimension == 2:
            dockwidget = self.scan_2d_dockwidgets[scan_data.scan_axes]
            data = scan_data.data
            dockwidget.scan_widget.set_image(data)
            if data is not None:
                dockwidget.scan_widget.set_image_extent(scan_data.scan_range)
            dockwidget.scan_widget.autoRange()
        elif scan_data.scan_dimension == 1:
            dockwidget = self.scan_1d_dockwidgets[scan_data.scan_axes]
            if set(scan_data.channel_names) != dockwidget.channel_set:
                old_channel = dockwidget.channel_combobox.currentText()
                dockwidget.channel_combobox.blockSignals(True)
                dockwidget.channel_combobox.clear()
                dockwidget.channel_combobox.addItems(scan_data.channel_names)
                dockwidget.channel_set = set(scan_data.channel_names)
                if old_channel in dockwidget.channel_set:
                    dockwidget.channel_combobox.setCurrentText(old_channel)
                else:
                    dockwidget.channel_combobox.setCurrentIndex(0)
                dockwidget.channel_combobox.blockSignals(False)
            channel = dockwidget.channel_combobox.currentText()
            if scan_data.data is None:
                dockwidget.plot_item.setData(np.zeros(1), np.zeros(1))
            else:
                dockwidget.plot_item.setData(
                    np.linspace(*(scan_data.scan_range[0]), scan_data.scan_resolution[0]),
                    scan_data.data[channel]
                )
            dockwidget.plot_widget.setLabel(
                'left', channel, units=scan_data.channel_units[channel])
        return

    @QtCore.Slot(bool, tuple)
    def scan_state_updated(self, is_running, scan_axes):
        self._toggle_enable_scan_actions_buttons(not is_running)
        if self._optimize_logic().module_state() == 'idle':
            dockwidget = self.scan_2d_dockwidgets.get(scan_axes, None)
            if dockwidget is not None:
                dockwidget.toggle_scan_button.setChecked(is_running)
                dockwidget.toggle_scan_button.setEnabled(True)
        else:
            self._mw.action_optimize_position.setEnabled(True)
        return

    @QtCore.Slot(bool)
    def optimize_state_updated(self, is_running):
        self._mw.action_optimize_position.setChecked(is_running)
        if is_running:
            try:
                self._scanning_logic().sigScanDataChanged.disconnect(self.scan_data_updated)
            except RuntimeError:
                pass
            curr_pos = self._scanning_logic().scanner_target
            axes_constr = self._scanning_logic().scanner_axes
            channel_constr = self._scanning_logic().scanner_channels
            optim_settings = self._optimize_logic().optimize_settings
            for seq_step in self._optimize_logic().scan_sequence:
                if len(seq_step) == 1:
                    axis = seq_step[0]
                    channel = optim_settings['data_channel']
                    self.optimizer_dockwidget.plot_widget.setLabel(
                        'bottom', axis, units=axes_constr[axis].unit
                    )
                    self.optimizer_dockwidget.plot_widget.setLabel(
                        'left', channel, units=channel_constr[channel].unit
                    )
                    self.optimizer_dockwidget.plot_widget.removeItem(
                        self.optimizer_dockwidget.fit_plot_item
                    )
                    self.optimizer_dockwidget.plot_item.setData(
                        np.zeros(optim_settings['scan_resolution'][axis])
                    )
                elif len(seq_step) == 2:
                    x_axis, y_axis = seq_step
                    x_extent = optim_settings['scan_range'][x_axis] / 2
                    y_extent = optim_settings['scan_range'][y_axis] / 2
                    self.optimizer_dockwidget.scan_widget.setLabel(
                        'bottom', x_axis, units=axes_constr[x_axis].unit
                    )
                    self.optimizer_dockwidget.scan_widget.setLabel(
                        'left', y_axis, units=axes_constr[y_axis].unit
                    )
                    self.optimizer_dockwidget.scan_widget.crosshairs[0].set_position(
                        (curr_pos[x_axis], curr_pos[y_axis])
                    )
                    self.optimizer_dockwidget.image_item.setImage(
                        np.zeros((optim_settings['scan_resolution'][x_axis],
                                  optim_settings['scan_resolution'][y_axis]))
                    )
                    self.optimizer_dockwidget.image_item.set_image_extent(
                        ((-x_extent, x_extent), (-y_extent, y_extent))
                    )
        else:
            self._scanning_logic().sigScanDataChanged.connect(
                self.scan_data_updated, QtCore.Qt.QueuedConnection
            )
        return

    @QtCore.Slot(object)
    def optimize_data_updated(self, scan_data=None):
        """
        @param dict scan_data:
        """
        print('OPTIMIZE DATA UPDATE')
        if scan_data is None:
            return
        if not isinstance(scan_data, ScanData):
            self.log.error('Parameter "scan_data" must be ScanData instance. '
                           'Unable to display optimizer scan data.')

        if scan_data.scan_dimension == 2:
            self.optimizer_dockwidget.image_item.setImage(
                scan_data.data[self._optimize_logic().data_channel]
            )
            if scan_data.data is not None:
                self.optimizer_dockwidget.image_item.set_image_extent(scan_data.scan_range)
            self.optimizer_dockwidget.scan_widget.autoRange()
        elif scan_data.scan_dimension == 1:
            x_data = np.linspace(*scan_data.scan_range[0], scan_data.scan_resolution[0])
            y_data = scan_data.data[self._optimize_logic().data_channel]
            self.optimizer_dockwidget.plot_item.setData(x_data, y_data)
        return

    @QtCore.Slot(bool)
    def toggle_optimize(self, enabled):
        """
        """
        self._toggle_enable_scan_actions_buttons(not enabled)
        self.sigToggleOptimize.emit(enabled)

    def _update_position_display(self, pos_dict):
        """

        @param dict pos_dict:
        """
        for axis, pos in pos_dict.items():
            for axes, dockwidget in self.scan_2d_dockwidgets.items():
                crosshair = dockwidget.scan_widget.crosshairs[1]
                ax1, ax2 = axes
                if ax1 == axis:
                    crosshair_pos = (pos, crosshair.position[1])
                    crosshair.set_position(crosshair_pos)
                elif ax2 == axis:
                    crosshair_pos = (crosshair.position[0], pos)
                    crosshair.set_position(crosshair_pos)
        return

    def _update_target_display(self, pos_dict, exclude_widget=None):
        """

        @param dict pos_dict:
        @param object exclude_widget:
        """
        for axis, pos in pos_dict.items():
            spinbox = self.axes_control_widgets[axis]['pos_spinbox']
            if exclude_widget is not spinbox:
                spinbox.blockSignals(True)
                spinbox.setValue(pos)
                spinbox.blockSignals(False)
            slider = self.axes_control_widgets[axis]['slider']
            if exclude_widget is not slider:
                slider.blockSignals(True)
                slider.setValue(pos)
                slider.blockSignals(False)
            for axes, dockwidget in self.scan_2d_dockwidgets.items():
                crosshair = dockwidget.scan_widget.crosshairs[0]
                if crosshair is exclude_widget:
                    continue
                ax1, ax2 = axes
                if ax1 == axis:
                    crosshair_pos = (pos, crosshair.position[1])
                    crosshair.set_position(crosshair_pos)
                elif ax2 == axis:
                    crosshair_pos = (crosshair.position[0], pos)
                    crosshair.set_position(crosshair_pos)
        return

    def _toggle_enable_scan_actions_buttons(self, enable):
        self._mw.action_utility_zoom.setEnabled(enable)
        self._mw.action_utility_full_range.setEnabled(enable)
        self._mw.action_history_back.setEnabled(enable)
        self._mw.action_history_forward.setEnabled(enable)
        self._mw.action_optimize_position.setEnabled(enable)
        for axes, dockwidget in self.scan_2d_dockwidgets.items():
            dockwidget.toggle_scan_button.setEnabled(enable)
        for axes, dockwidget in self.scan_1d_dockwidgets.items():
            dockwidget.toggle_scan_button.setEnabled(enable)

    def __get_slider_update_func(self, ax, slider):
        def update_func(x):
            pos_dict = {ax: x}
            self._update_target_display(pos_dict, exclude_widget=slider)
            self.set_scanner_target_position(pos_dict)
        return update_func

    def __get_target_spinbox_update_func(self, ax, spinbox):
        def update_func():
            pos_dict = {ax: spinbox.value()}
            self._update_target_display(pos_dict, exclude_widget=spinbox)
            self.set_scanner_target_position(pos_dict)
        return update_func

    def __get_crosshair_update_func(self, ax, crosshair):
        def update_func(x, y):
            pos_dict = {ax[0]: x, ax[1]: y}
            self._update_target_display(pos_dict, exclude_widget=crosshair)
            self.set_scanner_target_position(pos_dict)
        return update_func

    def __get_toggle_scan_func(self, ax):
        def toggle_func(enabled):
            self._toggle_enable_scan_actions_buttons(not enabled)
            self.sigToggleScan.emit(enabled, ax)
        return toggle_func

    def __get_range_from_selection_func(self, ax):
        def set_range_func(x_range, y_range):
            x_min, x_max = min(x_range), max(x_range)
            y_min, y_max = min(y_range), max(y_range)
            self.sigScanSettingsChanged.emit(
                {'range': {ax[0]: (x_min, x_max), ax[1]: (y_min, y_max)}}
            )
            self._mw.action_utility_zoom.setChecked(False)
        return set_range_func

    def __get_axis_scan_range_update_func(self, ax):
        def update_func():
            range_dict = {ax: (self.axes_control_widgets[ax]['min_spinbox'].value(),
                               self.axes_control_widgets[ax]['max_spinbox'].value())}
            self.sigScanSettingsChanged.emit({'range': range_dict})
        return update_func

    def __get_axis_scan_res_update_func(self, ax):
        def update_func():
            res_dict = {ax: self.axes_control_widgets[ax]['res_spinbox'].value()}
            self.sigScanSettingsChanged.emit({'resolution': res_dict})
        return update_func

    @QtCore.Slot()
    def change_optimizer_settings(self):
        # FIXME: sequence needs to be properly implemented
        widgets = self.optimizer_settings_axes_widgets
        settings = {
            'data_channel': self._osd.opt_channel_ComboBox.text(),
            'scan_sequence': (('x', 'y'), ('z',)),
            'scan_resolution': {ax: w_dict['res_spinbox'] for ax, w_dict in widgets.items()},
            'scan_range': {ax: w_dict['range_spinbox'] for ax, w_dict in widgets.items()},
            'scan_frequency': {ax: w_dict['freq_spinbox'] for ax, w_dict in widgets.items()},
        }
        self.sigOptimizerSettingsChanged.emit(settings)
        return

    @QtCore.Slot()
    @QtCore.Slot(dict)
    def update_optimizer_settings(self, settings=None):
        if not isinstance(settings, dict):
            settings = self._optimize_logic().optimize_settings

        if 'data_channel' in settings:
            self._osd.opt_channel_ComboBox.blockSignals(True)
            self._osd.opt_channel_ComboBox.setCurrentText(settings['data_channel'])
            self._osd.opt_channel_ComboBox.blockSignals(False)
        # FIXME: sequence needs to be properly implemented
        if 'scan_sequence' in settings:
            self._osd.optimization_sequence_lineEdit.blockSignals(True)
            self._osd.optimization_sequence_lineEdit.setText(str(settings['scan_sequence']))
            self._osd.optimization_sequence_lineEdit.blockSignals(False)

            axes_constr = self._scanning_logic().scanner_axes
            for seq_step in settings['scan_sequence']:
                if len(seq_step) == 1:
                    axis = seq_step[0]
                    self.optimizer_dockwidget.plot_widget.setLabel('bottom',
                                                                   axis,
                                                                   units=axes_constr[axis].unit)
                    self.optimizer_dockwidget.plot_item.setData(np.zeros(10))
                elif len(seq_step) == 2:
                    x_axis, y_axis = seq_step
                    self.optimizer_dockwidget.scan_widget.setLabel('bottom',
                                                                   x_axis,
                                                                   units=axes_constr[x_axis].unit)
                    self.optimizer_dockwidget.scan_widget.setLabel('left',
                                                                   y_axis,
                                                                   units=axes_constr[y_axis].unit)
                    self.optimizer_dockwidget.image_item.setImage(np.zeros((2, 2)))
                    self.optimizer_dockwidget.image_item.set_image_extent(
                        ((-0.5, 0.5), (-0.5, 0.5))
                    )
        if 'scan_range' in settings:
            for axis, ax_range in settings['scan_range'].items():
                spinbox = self.optimizer_settings_axes_widgets[axis]['range_spinbox']
                spinbox.blockSignals(True)
                spinbox.setValue(ax_range)
                spinbox.blockSignals(False)

            # Adjust crosshair size according to optimizer range
            for scan_axes, dockwidget in self.scan_2d_dockwidgets.items():
                if any(ax in settings['scan_range'] for ax in scan_axes):
                    crosshair = dockwidget.scan_widget.crosshairs[0]
                    x_size = settings['scan_range'].get(scan_axes[0], crosshair.size[0])
                    y_size = settings['scan_range'].get(scan_axes[1], crosshair.size[1])
                    crosshair.set_size((x_size, y_size))
        if 'scan_resolution' in settings:
            for axis, ax_res in settings['scan_resolution'].items():
                spinbox = self.optimizer_settings_axes_widgets[axis]['res_spinbox']
                spinbox.blockSignals(True)
                spinbox.setValue(ax_res)
                spinbox.blockSignals(False)
        if 'scan_frequency' in settings:
            for axis, ax_freq in settings['scan_frequency'].items():
                spinbox = self.optimizer_settings_axes_widgets[axis]['freq_spinbox']
                spinbox.blockSignals(True)
                spinbox.setValue(ax_freq)
                spinbox.blockSignals(False)
        return
