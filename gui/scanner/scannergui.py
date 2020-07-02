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

import numpy as np
import os
import pyqtgraph as pg
import time

from core.connector import Connector
from core.statusvariable import StatusVar
from core.configoption import ConfigOption
from qtwidgets.scan_plotwidget import ScanImageItem
from qtwidgets.scientific_spinbox import ScienDSpinBox
from qtwidgets.slider import DoubleSlider
from qtwidgets.colorbar import ColorBarWidget
from gui.guibase import GUIBase
from gui.colordefs import ColorScaleInferno
from gui.colordefs import QudiPalettePale as palette
from gui.fitsettings import FitParametersWidget
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy import uic


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


class Scan2dDockWidget(QtWidgets.QDockWidget):
    """ Create the 2D scan dockwidget based on the corresponding *.ui file.
    """

    def __init__(self, axes_names):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_2d_scan_widget.ui')

        ax1 = axes_names[0][0].upper() + axes_names[0][1:]
        ax2 = axes_names[1][0].upper() + axes_names[1][1:]
        dock_title = '{0}-{1} Scan'.format(ax1, ax2)

        super().__init__(dock_title)
        self.setObjectName('{0}_{1}_scan_dockWidget'.format(*axes_names))

        # Load UI file
        widget = QtWidgets.QWidget()
        uic.loadUi(ui_file, widget)
        widget.setObjectName('{0}_{1}_scan_widget'.format(*axes_names))

        self.channel_comboBox = widget.channel_comboBox
        self.channel_set = set()
        self.plot_widget = widget.image_scanPlotWidget
        self.colorbar = widget.colorbar_colorBarWidget
        self.image_item = ScanImageItem(image=np.zeros((2, 2)))
        self.plot_widget.addItem(self.image_item)
        self.colorbar.assign_image_item(self.image_item)
        self.colorbar.set_label(text='fluorescence', unit='c/s')
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


class ScannerGui(GUIBase):
    """ Main Confocal Class for xy and depth scans.
    """
    _modclass = 'ScannerGui'
    _modtype = 'gui'

    # declare connectors
    scanninglogic = Connector(interface='ScanningLogic')

    # config options for gui
    image_axes_padding = ConfigOption(name='image_axes_padding', default=0.02)
    default_position_unit_prefix = ConfigOption(name='default_position_unit_prefix', default=None)

    # status vars
    slider_small_step = StatusVar(name='slider_small_step', default=10e-9)
    slider_big_step = StatusVar(name='slider_big_step', default=100e-9)
    _window_state = StatusVar(name='window_state', default=None)
    _window_geometry = StatusVar(name='window_geometry', default=None)

    # signals
    sigMoveScannerPosition = QtCore.Signal(dict, object)
    sigScannerSettingsChanged = QtCore.Signal(dict)
    sigOptimizerSettingsChanged = QtCore.Signal(dict)
    sigToggleScan = QtCore.Signal(bool, str)
    sigToggleOptimize = QtCore.Signal(bool)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # QMainWindow and QDialog child instances
        self._mw = ConfocalMainWindow()
        self._ssd = ScannerSettingDialog()
        self._osd = OptimizerSettingDialog()

        # References to dockwidgets
        self.xy_scan = Scan2dDockWidget(('x', 'y'))
        self.xz_scan = Scan2dDockWidget(('x', 'z'))
        self.optimizer_dockwidget = OptimizerDockWidget()

        self.xy_scan.plot_widget.setLabel('bottom', 'X', units='m')
        self.xy_scan.plot_widget.setLabel('left', 'Y', units='m')
        self.xy_scan.plot_widget.add_crosshair(movable=True, min_size_factor=0.02)
        self.xy_scan.plot_widget.setAspectLocked(lock=True, ratio=1.0)
        self.xy_scan.plot_widget.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        # self.xy_scan.plot_widget.toggle_zoom_by_selection(True)

        self.xz_scan.plot_widget.setLabel('bottom', 'X', units='m')
        self.xz_scan.plot_widget.setLabel('left', 'Z', units='m')
        self.xz_scan.plot_widget.add_crosshair(movable=True, min_size_factor=0.02)
        self.xz_scan.plot_widget.setAspectLocked(lock=True, ratio=1.0)
        # self.xz_scan.plot_widget.toggle_zoom_by_selection(True)

        # Customize
        self.optimizer_dockwidget.setAllowedAreas(QtCore.Qt.TopDockWidgetArea)
        self.optimizer_dockwidget.scan_widget.add_crosshair(movable=False,
                                                            pen={'color': '#00ff00', 'width': 2})
        self.optimizer_dockwidget.scan_widget.setAspectLocked(lock=True, ratio=1.0)
        return

    def on_activate(self):
        """ Initializes all needed UI files and establishes the connectors.

        This method executes the all the inits for the different GUIs and passes
        the event argument from fysom to the methods.
        """
        # connect view/visibility signals
        self.optimizer_dockwidget.visibilityChanged.connect(
            self._mw.action_view_optimizer.setChecked)
        self._mw.action_view_optimizer.triggered[bool].connect(
            self.optimizer_dockwidget.setVisible)
        self._mw.action_restore_default_view.triggered.connect(self.restore_default_view)
        self._mw.action_optimizer_settings.triggered.connect(lambda x: self._osd.exec_())
        self._mw.action_scanner_settings.triggered.connect(lambda x: self._ssd.exec_())

        # Connect the action of the optimizer settings window with the code:
        self._osd.accepted.connect(self.change_optimizer_settings)
        self._osd.rejected.connect(self.update_optimizer_settings)
        self._osd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(
            self.change_optimizer_settings)
        # Connect the action of the scanner settings window with the code:
        self._ssd.accepted.connect(self.change_scanner_settings)
        self._ssd.rejected.connect(self.update_scanner_settings)
        self._ssd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(
            self.change_scanner_settings)

        # Set input widget value ranges and units according to scanner constraints
        self.apply_scanner_constraints()

        # Connect axis control signals
        self._mw.x_min_range_doubleSpinBox.valueChanged.connect(self.change_x_scan_range)
        self._mw.x_max_range_doubleSpinBox.valueChanged.connect(self.change_x_scan_range)
        self._mw.y_min_range_doubleSpinBox.valueChanged.connect(self.change_y_scan_range)
        self._mw.y_max_range_doubleSpinBox.valueChanged.connect(self.change_y_scan_range)
        self._mw.z_min_range_doubleSpinBox.valueChanged.connect(self.change_z_scan_range)
        self._mw.z_max_range_doubleSpinBox.valueChanged.connect(self.change_z_scan_range)
        self._mw.x_resolution_spinBox.valueChanged.connect(self.change_scan_resolution)
        # self._mw.y_resolution_spinBox.valueChanged.connect(self.change_scan_resolution)
        # self._mw.z_resolution_spinBox.valueChanged.connect(self.change_scan_resolution)
        self._mw.x_slider.sliderMoved.connect(self._x_slider_moved)
        self._mw.y_slider.sliderMoved.connect(self._y_slider_moved)
        self._mw.z_slider.sliderMoved.connect(self._z_slider_moved)
        self._mw.x_slider.sliderReleased.connect(self._x_slider_released)
        self._mw.y_slider.sliderReleased.connect(self._y_slider_released)
        self._mw.z_slider.sliderReleased.connect(self._z_slider_released)
        self._mw.x_position_doubleSpinBox.editingFinished.connect(self._x_position_changed)
        self._mw.y_position_doubleSpinBox.editingFinished.connect(self._y_position_changed)
        self._mw.z_position_doubleSpinBox.editingFinished.connect(self._z_position_changed)

        # Initialize widget data
        self.update_optimizer_settings()
        self.update_scanner_settings()
        self.scanner_target_updated()
        self.scan_data_updated('xy', self.scanninglogic().xy_scan_data)
        self.scan_data_updated('xz', self.scanninglogic().xz_scan_data)

        # Initialize dockwidgets to default view
        self.restore_default_view()
        # Try to restore window state and geometry
        # if self._window_geometry is not None:
        #     if not self._mw.restoreGeometry(bytearray.fromhex(self._window_geometry)):
        #         self._window_geometry = None
        #         self.log.debug(
        #             'Unable to restore previous window geometry. Falling back to default.')
        # if self._window_state is not None:
        #     if not self._mw.restoreState(bytearray.fromhex(self._window_state)):
        #         self._window_state = None
        #         self.log.debug(
        #             'Unable to restore previous window state. Falling back to default.')

        # Connect signals to logic
        self.sigMoveScannerPosition.connect(
            self.scanninglogic().set_scanner_target_position, QtCore.Qt.QueuedConnection)
        self.sigScannerSettingsChanged.connect(
            self.scanninglogic().set_scanner_settings, QtCore.Qt.QueuedConnection)
        self.sigOptimizerSettingsChanged.connect(
            self.scanninglogic().set_optimizer_settings, QtCore.Qt.QueuedConnection)
        self.sigToggleScan.connect(self.scanninglogic().toggle_scan, QtCore.Qt.QueuedConnection)
        # self.sigToggleOptimize.connect(self.scanninglogic().toggle_scan, QtCore.Qt.QueuedConnection)
        # self._mw.action_history_forward.triggered.connect(
        #     self.scanninglogic().history_forward, QtCore.Qt.QueuedConnection)
        # self._mw.action_history_back.triggered.connect(
        #     self.scanninglogic().history_backward, QtCore.Qt.QueuedConnection)
        # self._mw.action_utility_full_range.triggered.connect(
        #     self.scanninglogic().set_full_scan_ranges, QtCore.Qt.QueuedConnection)

        # Connect signals from logic
        self.scanninglogic().sigScannerTargetChanged.connect(
            self.scanner_target_updated, QtCore.Qt.QueuedConnection)
        self.scanninglogic().sigScannerSettingsChanged.connect(
            self.update_scanner_settings, QtCore.Qt.QueuedConnection)
        self.scanninglogic().sigOptimizerSettingsChanged.connect(
            self.update_optimizer_settings, QtCore.Qt.QueuedConnection)
        self.scanninglogic().sigScanDataChanged.connect(
            self.scan_data_updated, QtCore.Qt.QueuedConnection)
        self.scanninglogic().sigScanStateChanged.connect(
            self.scan_state_updated, QtCore.Qt.QueuedConnection)

        # self._mw.action_utility_zoom.toggled.connect(self.toggle_cursor_zoom)
        # connect plot signals
        self.xy_scan.plot_widget.crosshairs[0].sigDraggedPosChanged.connect(
            self._xy_crosshair_dragged)
        self.xy_scan.plot_widget.crosshairs[0].sigDragStopped.connect(
            self._xy_crosshair_released)
        # self.xy_scan.plot_widget.sigMouseAreaSelected.connect(self._xy_area_selected)
        # self.xy_scan.channel_comboBox.currentIndexChanged.connect(self._xy_channel_changed)
        self.xz_scan.plot_widget.crosshairs[0].sigDraggedPosChanged.connect(
            self._xz_crosshair_dragged)
        self.xz_scan.plot_widget.crosshairs[0].sigDragStopped.connect(
            self._xz_crosshair_released)
        # self.xz_scan.plot_widget.sigMouseAreaSelected.connect(self._xz_area_selected)
        # self.xz_scan.channel_comboBox.currentIndexChanged.connect(self._xz_channel_changed)

        self._mw.action_xy_scan.triggered.connect(self._xy_scan_triggered)
        self._mw.action_xz_scan.triggered.connect(self._xz_scan_triggered)

        self.show()
        return

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        self._mw.action_restore_default_view.triggered.disconnect()

        self.sigMoveScannerPosition.disconnect()
        self.sigScannerSettingsChanged.disconnect()
        self.sigOptimizerSettingsChanged.disconnect()
        self.sigToggleScan.disconnect()
        self._mw.action_history_forward.triggered.disconnect()
        self._mw.action_history_back.triggered.disconnect()
        self._mw.action_utility_full_range.triggered.disconnect()
        self._mw.action_utility_zoom.toggled.disconnect()
        self.scanninglogic().sigScannerPositionChanged.disconnect()
        self.scanninglogic().sigScannerTargetChanged.disconnect()
        self.scanninglogic().sigScannerSettingsChanged.disconnect()
        self.scanninglogic().sigOptimizerSettingsChanged.disconnect()
        self.scanninglogic().sigScanDataChanged.disconnect()
        self.scanninglogic().sigScanStateChanged.disconnect()

        self._window_geometry = bytearray(self._mw.saveGeometry()).hex()
        self._window_state = bytearray(self._mw.saveState()).hex()
        self._mw.close()
        return 0

    def show(self):
        """Make main window visible and put it above all other windows. """
        # Show the Main Confocal GUI:
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    @QtCore.Slot()
    def restore_default_view(self):
        """ Restore the arrangement of DockWidgets to default """
        self._mw.setDockNestingEnabled(False)

        # Handle scan dock widgets
        self.xy_scan.show()
        self.xy_scan.setFloating(False)
        self.xz_scan.show()
        self.xz_scan.setFloating(False)
        self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.xy_scan)
        self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.xz_scan)

        # Handle optimizer dock widget
        self.optimizer_dockwidget.setFloating(False)
        self.optimizer_dockwidget.show()
        self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.optimizer_dockwidget)
        self._mw.splitDockWidget(self.xz_scan, self.optimizer_dockwidget, QtCore.Qt.Vertical)
        self._mw.resizeDocks([self.xz_scan, self.optimizer_dockwidget],
                             [1, 1],
                             QtCore.Qt.Vertical)
        self._mw.resizeDocks([self.xy_scan, self.xz_scan],
                             [1, 1],
                             QtCore.Qt.Horizontal)
        return

    def apply_scanner_constraints(self):
        """ Set limits on input widgets according to scanner hardware constraints. """
        constraints = self.scanninglogic().scanner_constraints

        min_res = max(min(constraints['axes_resolution_ranges']['x']),
                      min(constraints['axes_resolution_ranges']['y']),
                      min(constraints['axes_resolution_ranges']['z']))
        max_res = min(max(constraints['axes_resolution_ranges']['x']),
                      max(constraints['axes_resolution_ranges']['y']),
                      max(constraints['axes_resolution_ranges']['z']))
        self._mw.x_resolution_spinBox.setRange(min_res, max_res)
        self._mw.y_resolution_spinBox.setRange(min_res, max_res)
        self._mw.z_resolution_spinBox.setRange(min_res, max_res)
        self._mw.x_min_range_doubleSpinBox.setRange(min(constraints['axes_position_ranges']['x']),
                                                    max(constraints['axes_position_ranges']['x']))
        self._mw.y_min_range_doubleSpinBox.setRange(min(constraints['axes_position_ranges']['y']),
                                                    max(constraints['axes_position_ranges']['y']))
        self._mw.z_min_range_doubleSpinBox.setRange(min(constraints['axes_position_ranges']['z']),
                                                    max(constraints['axes_position_ranges']['z']))
        self._mw.x_slider.setRange(min(constraints['axes_position_ranges']['x']),
                                   max(constraints['axes_position_ranges']['x']))
        self._mw.y_slider.setRange(min(constraints['axes_position_ranges']['y']),
                                   max(constraints['axes_position_ranges']['y']))
        self._mw.z_slider.setRange(min(constraints['axes_position_ranges']['z']),
                                   max(constraints['axes_position_ranges']['z']))
        self._mw.x_position_doubleSpinBox.setRange(min(constraints['axes_position_ranges']['x']),
                                                   max(constraints['axes_position_ranges']['x']))
        self._mw.y_position_doubleSpinBox.setRange(min(constraints['axes_position_ranges']['y']),
                                                   max(constraints['axes_position_ranges']['y']))
        self._mw.z_position_doubleSpinBox.setRange(min(constraints['axes_position_ranges']['z']),
                                                   max(constraints['axes_position_ranges']['z']))

        optimizer_settings = self.scanninglogic().optimizer_settings
        self.xy_scan.plot_widget.crosshairs[0].set_allowed_range(
            ((min(constraints['axes_position_ranges']['x']),
              max(constraints['axes_position_ranges']['x'])),
             (min(constraints['axes_position_ranges']['y']),
              max(constraints['axes_position_ranges']['y'])))
        )
        self.xy_scan.plot_widget.crosshairs[0].set_size((optimizer_settings['x_range'],
                                                         optimizer_settings['y_range']))
        self.xz_scan.plot_widget.crosshairs[0].set_allowed_range(
            ((min(constraints['axes_position_ranges']['x']),
              max(constraints['axes_position_ranges']['x'])),
             (min(constraints['axes_position_ranges']['z']),
              max(constraints['axes_position_ranges']['z'])))
        )
        self.xz_scan.plot_widget.crosshairs[0].set_size((optimizer_settings['x_range'],
                                                         optimizer_settings['z_range']))
        return

    @QtCore.Slot()
    @QtCore.Slot(dict)
    def update_scanner_settings(self, settings=None):
        """
        Update scanner settings from logic and set widgets accordingly.

        @param dict settings: Settings dict containing the scanner settings to update.
                              If None (default) read the scanner setting from logic and update.
        """
        if not isinstance(settings, dict):
            settings = self.scanninglogic().scanner_settings

        if 'pixel_clock_frequency' in settings:
            self._ssd.pixel_clock_frequency_scienSpinBox.setValue(settings['pixel_clock_frequency'])
        if 'scan_resolution' in settings:
            self._mw.x_resolution_spinBox.blockSignals(True)
            self._mw.y_resolution_spinBox.blockSignals(True)
            self._mw.z_resolution_spinBox.blockSignals(True)
            self._mw.x_resolution_spinBox.setValue(settings['scan_resolution'])
            self._mw.y_resolution_spinBox.setValue(settings['scan_resolution'])
            self._mw.z_resolution_spinBox.setValue(settings['scan_resolution'])
            self._mw.x_resolution_spinBox.blockSignals(False)
            self._mw.y_resolution_spinBox.blockSignals(False)
            self._mw.z_resolution_spinBox.blockSignals(False)
        if 'x_scan_range' in settings:
            self._mw.x_min_range_doubleSpinBox.blockSignals(True)
            self._mw.x_max_range_doubleSpinBox.blockSignals(True)
            self._mw.x_min_range_doubleSpinBox.setValue(min(settings['x_scan_range']))
            self._mw.x_max_range_doubleSpinBox.setValue(max(settings['x_scan_range']))
            self._mw.x_min_range_doubleSpinBox.blockSignals(False)
            self._mw.x_max_range_doubleSpinBox.blockSignals(False)
        if 'y_scan_range' in settings:
            self._mw.y_min_range_doubleSpinBox.blockSignals(True)
            self._mw.y_max_range_doubleSpinBox.blockSignals(True)
            self._mw.y_min_range_doubleSpinBox.setValue(min(settings['y_scan_range']))
            self._mw.y_max_range_doubleSpinBox.setValue(max(settings['y_scan_range']))
            self._mw.y_min_range_doubleSpinBox.blockSignals(False)
            self._mw.y_max_range_doubleSpinBox.blockSignals(False)
        if 'z_scan_range' in settings:
            self._mw.z_min_range_doubleSpinBox.blockSignals(True)
            self._mw.z_max_range_doubleSpinBox.blockSignals(True)
            self._mw.z_min_range_doubleSpinBox.setValue(min(settings['z_scan_range']))
            self._mw.z_max_range_doubleSpinBox.setValue(max(settings['z_scan_range']))
            self._mw.z_min_range_doubleSpinBox.blockSignals(False)
            self._mw.z_max_range_doubleSpinBox.blockSignals(False)
        return

    def move_scanner_position(self, target_pos):
        """

        @param dict target_pos:
        """
        if self.scanninglogic().module_state() == 'idle':
            self.sigMoveScannerPosition.emit(target_pos, id(self))

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
        # This has already been done.
        if caller_id == id(self):
            return

        if not isinstance(pos_dict, dict):
            pos_dict = self.scanninglogic().scanner_target

        self._update_target_display(pos_dict)
        return

    @QtCore.Slot(str, np.ndarray)
    def scan_data_updated(self, axes, scan_data):
        """

        @param dict scan_data:
        """
        resolution = self._mw.x_resolution_spinBox.value()
        if axes.lower() == 'xy':
            self.xy_scan.image_item.setImage(image=scan_data)
            px_size_x = abs(
                self._mw.x_max_range_doubleSpinBox.value() - self._mw.x_min_range_doubleSpinBox.value()) / (
                                    resolution - 1)
            px_size_y = abs(
                self._mw.y_max_range_doubleSpinBox.value() - self._mw.y_min_range_doubleSpinBox.value()) / (
                                    resolution - 1)
            x_min = self._mw.x_min_range_doubleSpinBox.value() - px_size_x / 2
            x_max = self._mw.x_max_range_doubleSpinBox.value() + px_size_x / 2
            y_min = self._mw.y_min_range_doubleSpinBox.value() - px_size_y / 2
            y_max = self._mw.y_max_range_doubleSpinBox.value() + px_size_y / 2
            self.xy_scan.image_item.set_image_extent(((x_min, x_max), (y_min, y_max)))
        elif axes.lower() == 'xz':
            self.xz_scan.image_item.setImage(image=scan_data)
            px_size_x = abs(
                self._mw.x_max_range_doubleSpinBox.value() - self._mw.x_min_range_doubleSpinBox.value()) / (
                                resolution - 1)
            px_size_z = abs(
                self._mw.z_max_range_doubleSpinBox.value() - self._mw.z_min_range_doubleSpinBox.value()) / (
                                resolution - 1)
            x_min = self._mw.x_min_range_doubleSpinBox.value() - px_size_x / 2
            x_max = self._mw.x_max_range_doubleSpinBox.value() + px_size_x / 2
            z_min = self._mw.z_min_range_doubleSpinBox.value() - px_size_z / 2
            z_max = self._mw.z_max_range_doubleSpinBox.value() + px_size_z / 2
            self.xz_scan.image_item.set_image_extent(((x_min, x_max), (z_min, z_max)))
        return

    @QtCore.Slot(bool, str)
    def scan_state_updated(self, is_running, scan_axes):
        if is_running:
            self._mw.x_position_doubleSpinBox.setEnabled(False)
            self._mw.y_position_doubleSpinBox.setEnabled(False)
            self._mw.z_position_doubleSpinBox.setEnabled(False)
            self._mw.x_slider.setEnabled(False)
            self._mw.y_slider.setEnabled(False)
            self._mw.z_slider.setEnabled(False)
            self._mw.x_resolution_spinBox.setEnabled(False)
            self._mw.x_min_range_doubleSpinBox.setEnabled(False)
            self._mw.y_min_range_doubleSpinBox.setEnabled(False)
            self._mw.z_min_range_doubleSpinBox.setEnabled(False)
            self._mw.x_max_range_doubleSpinBox.setEnabled(False)
            self._mw.y_max_range_doubleSpinBox.setEnabled(False)
            self._mw.z_max_range_doubleSpinBox.setEnabled(False)
            self.xy_scan.plot_widget.crosshairs[0].set_movable(False)
            self.xz_scan.plot_widget.crosshairs[0].set_movable(False)

            if scan_axes == 'xy':
                self._mw.action_xy_scan.setChecked(True)
                self._mw.action_xz_scan.setEnabled(False)
            elif scan_axes == 'xz':
                self._mw.action_xz_scan.setChecked(True)
                self._mw.action_xy_scan.setEnabled(False)
            self._mw.action_optimize_position.setEnabled(False)
        else:
            self._mw.x_position_doubleSpinBox.setEnabled(True)
            self._mw.y_position_doubleSpinBox.setEnabled(True)
            self._mw.z_position_doubleSpinBox.setEnabled(True)
            self._mw.x_slider.setEnabled(True)
            self._mw.y_slider.setEnabled(True)
            self._mw.z_slider.setEnabled(True)
            self._mw.x_resolution_spinBox.setEnabled(True)
            self._mw.x_min_range_doubleSpinBox.setEnabled(True)
            self._mw.y_min_range_doubleSpinBox.setEnabled(True)
            self._mw.z_min_range_doubleSpinBox.setEnabled(True)
            self._mw.x_max_range_doubleSpinBox.setEnabled(True)
            self._mw.y_max_range_doubleSpinBox.setEnabled(True)
            self._mw.z_max_range_doubleSpinBox.setEnabled(True)
            self.xy_scan.plot_widget.crosshairs[0].set_movable(True)
            self.xz_scan.plot_widget.crosshairs[0].set_movable(True)

            self._mw.action_xy_scan.setEnabled(True)
            self._mw.action_xz_scan.setEnabled(True)
            self._mw.action_optimize_position.setEnabled(True)
            self._mw.action_xy_scan.setChecked(False)
            self._mw.action_xz_scan.setChecked(False)
        return

    def _update_target_display(self, pos_dict, exclude_widget=None):
        """

        @param dict pos_dict:
        """
        if ('x' in pos_dict or 'y' in pos_dict) and exclude_widget is not self.xy_scan:
            crosshair_pos = self.xy_scan.plot_widget.crosshairs[0].position
            new_pos = (pos_dict.get('x', crosshair_pos[0]), pos_dict.get('y', crosshair_pos[1]))
            self.xy_scan.plot_widget.crosshairs[0].set_position(new_pos)
        if ('x' in pos_dict or 'z' in pos_dict) and exclude_widget is not self.xz_scan:
            crosshair_pos = self.xz_scan.plot_widget.crosshairs[0].position
            new_pos = (pos_dict.get('x', crosshair_pos[0]), pos_dict.get('z', crosshair_pos[1]))
            self.xz_scan.plot_widget.crosshairs[0].set_position(new_pos)

        if 'x' in pos_dict:
            if exclude_widget is not self._mw.x_position_doubleSpinBox:
                self._mw.x_position_doubleSpinBox.blockSignals(True)
                self._mw.x_position_doubleSpinBox.setValue(pos_dict['x'])
                self._mw.x_position_doubleSpinBox.blockSignals(False)
            if exclude_widget is not self._mw.x_slider:
                self._mw.x_slider.blockSignals(True)
                self._mw.x_slider.setValue(pos_dict['x'])
                self._mw.x_slider.blockSignals(False)
        if 'y' in pos_dict:
            if exclude_widget is not self._mw.y_position_doubleSpinBox:
                self._mw.y_position_doubleSpinBox.blockSignals(True)
                self._mw.y_position_doubleSpinBox.setValue(pos_dict['y'])
                self._mw.y_position_doubleSpinBox.blockSignals(False)
            if exclude_widget is not self._mw.y_slider:
                self._mw.y_slider.blockSignals(True)
                self._mw.y_slider.setValue(pos_dict['y'])
                self._mw.y_slider.blockSignals(False)
        if 'z' in pos_dict:
            if exclude_widget is not self._mw.z_position_doubleSpinBox:
                self._mw.z_position_doubleSpinBox.blockSignals(True)
                self._mw.z_position_doubleSpinBox.setValue(pos_dict['z'])
                self._mw.z_position_doubleSpinBox.blockSignals(False)
            if exclude_widget is not self._mw.x_slider:
                self._mw.z_slider.blockSignals(True)
                self._mw.z_slider.setValue(pos_dict['z'])
                self._mw.z_slider.blockSignals(False)
        return

    @QtCore.Slot(float)
    def _x_slider_moved(self, value):
        pos_dict = {'x': value}
        self._update_target_display(pos_dict, exclude_widget=self._mw.x_slider)
        return

    @QtCore.Slot(float)
    def _y_slider_moved(self, value):
        pos_dict = {'y': value}
        self._update_target_display(pos_dict, exclude_widget=self._mw.y_slider)
        return

    @QtCore.Slot(float)
    def _z_slider_moved(self, value):
        pos_dict = {'z': value}
        self._update_target_display(pos_dict, exclude_widget=self._mw.z_slider)
        return

    @QtCore.Slot()
    def _x_slider_released(self):
        pos_dict = {'x': self._mw.x_slider.value()}
        self._update_target_display(pos_dict, exclude_widget=self._mw.x_slider)
        self.move_scanner_position(pos_dict)
        return

    @QtCore.Slot()
    def _y_slider_released(self):
        pos_dict = {'y': self._mw.y_slider.value()}
        self._update_target_display(pos_dict, exclude_widget=self._mw.y_slider)
        self.move_scanner_position(pos_dict)
        return

    @QtCore.Slot()
    def _z_slider_released(self):
        pos_dict = {'z': self._mw.z_slider.value()}
        self._update_target_display(pos_dict, exclude_widget=self._mw.z_slider)
        self.move_scanner_position(pos_dict)
        return

    @QtCore.Slot()
    def _x_position_changed(self):
        pos_dict = {'x': self._mw.x_position_doubleSpinBox.value()}
        self._update_target_display(pos_dict, exclude_widget=self._mw.x_position_doubleSpinBox)
        self.move_scanner_position(pos_dict)
        return

    @QtCore.Slot()
    def _y_position_changed(self):
        pos_dict = {'y': self._mw.y_position_doubleSpinBox.value()}
        self._update_target_display(pos_dict, exclude_widget=self._mw.y_position_doubleSpinBox)
        self.move_scanner_position(pos_dict)
        return

    @QtCore.Slot()
    def _z_position_changed(self):
        pos_dict = {'z': self._mw.z_position_doubleSpinBox.value()}
        self._update_target_display(pos_dict, exclude_widget=self._mw.z_position_doubleSpinBox)
        self.move_scanner_position(pos_dict)
        return

    @QtCore.Slot(float, float)
    def _xy_crosshair_dragged(self, x_pos, y_pos):
        pos_dict = {'x': x_pos, 'y': y_pos}
        self._update_target_display(pos_dict, exclude_widget=self.xy_scan)
        return

    @QtCore.Slot(float, float)
    def _xz_crosshair_dragged(self, x_pos, z_pos):
        pos_dict = {'x': x_pos, 'z': z_pos}
        self._update_target_display(pos_dict, exclude_widget=self.xz_scan)
        return

    @QtCore.Slot()
    def _xy_crosshair_released(self):
        position = self.xy_scan.plot_widget.crosshairs[0].position
        pos_dict = {'x': position[0], 'y': position[1]}
        self._update_target_display(pos_dict, exclude_widget=self.xy_scan)
        self.move_scanner_position(pos_dict)
        return

    @QtCore.Slot()
    def _xz_crosshair_released(self):
        position = self.xz_scan.plot_widget.crosshairs[0].position
        pos_dict = {'x': position[0], 'z': position[1]}
        self._update_target_display(pos_dict, exclude_widget=self.xz_scan)
        self.move_scanner_position(pos_dict)
        return

    # def __get_range_from_selection_func(self, ax):
    #     def set_range_func(qrect):
    #         x_min, x_max = min(qrect.left(), qrect.right()), max(qrect.left(), qrect.right())
    #         y_min, y_max = min(qrect.top(), qrect.bottom()), max(qrect.top(), qrect.bottom())
    #         self.sigScannerSettingsChanged.emit({'scan_range': {ax[0]: (x_min, x_max),
    #                                                             ax[1]: (y_min, y_max)}})
    #         self._mw.action_utility_zoom.setChecked(False)
    #     return set_range_func

    # def __get_data_channel_changed_func(self, ax):
    #     def set_data_channel():
    #         self.scan_data_updated({ax: self.scanninglogic().scan_data[ax]})
    #     return set_data_channel

    @QtCore.Slot()
    def change_x_scan_range(self):
        scan_range = (self._mw.x_min_range_doubleSpinBox.value(),
                      self._mw.x_max_range_doubleSpinBox.value())
        self.sigScannerSettingsChanged.emit({'x_scan_range': scan_range})
        return

    @QtCore.Slot()
    def change_y_scan_range(self):
        scan_range = (self._mw.y_min_range_doubleSpinBox.value(),
                      self._mw.y_max_range_doubleSpinBox.value())
        self.sigScannerSettingsChanged.emit({'y_scan_range': scan_range})
        return

    @QtCore.Slot()
    def change_z_scan_range(self):
        scan_range = (self._mw.z_min_range_doubleSpinBox.value(),
                      self._mw.z_max_range_doubleSpinBox.value())
        self.sigScannerSettingsChanged.emit({'z_scan_range': scan_range})
        return

    @QtCore.Slot()
    def change_scan_resolution(self):
        scan_res = self._mw.x_resolution_spinBox.value()
        self.sigScannerSettingsChanged.emit({'scan_resolution': scan_res})
        return

    # @QtCore.Slot(bool)
    # def toggle_cursor_zoom(self, enable):
    #     if self._mw.action_utility_zoom.isChecked() != enable:
    #         self._mw.action_utility_zoom.blockSignals(True)
    #         self._mw.action_utility_zoom.setChecked(enable)
    #         self._mw.action_utility_zoom.blockSignals(False)
    #
    #     for dockwidget in self.scan_2d_dockwidgets.values():
    #         dockwidget.plot_widget.toggle_selection(enable)
    #     return

    @QtCore.Slot()
    def change_scanner_settings(self):
        self.sigScannerSettingsChanged.emit(
            {'pixel_clock_frequency': self._ssd.pixel_clock_frequency_scienSpinBox.value()})

    @QtCore.Slot()
    def change_optimizer_settings(self):
        settings = dict()
        settings['pixel_clock'] = self._osd.pixel_clock_frequency_scienSpinBox.value()
        settings['sequence'] = [s.strip().lower() for s in
                                self._osd.optimization_sequence_lineEdit.text().split(',')]
        settings['x_range'] = self._osd.x_optimizer_range_doubleSpinBox.value()
        settings['y_range'] = self._osd.y_optimizer_range_doubleSpinBox.value()
        settings['z_range'] = self._osd.z_optimizer_range_doubleSpinBox.value()
        settings['x_resolution'] = self._osd.x_optimizer_resolution_spinBox.value()
        settings['y_resolution'] = self._osd.y_optimizer_resolution_spinBox.value()
        settings['z_resolution'] = self._osd.z_optimizer_resolution_spinBox.value()
        self.sigOptimizerSettingsChanged.emit(settings)
        return

    @QtCore.Slot()
    @QtCore.Slot(dict)
    def update_optimizer_settings(self, settings=None):
        if not isinstance(settings, dict):
            settings = self.scanninglogic().optimizer_settings

        if 'pixel_clock' in settings:
            self._osd.pixel_clock_frequency_scienSpinBox.blockSignals(True)
            self._osd.pixel_clock_frequency_scienSpinBox.setValue(settings['pixel_clock'])
            self._osd.pixel_clock_frequency_scienSpinBox.blockSignals(False)
        if 'x_range' in settings:
            self._osd.x_optimizer_range_doubleSpinBox.blockSignals(True)
            self._osd.x_optimizer_range_doubleSpinBox.setValue(settings['x_range'])
            self._osd.x_optimizer_range_doubleSpinBox.blockSignals(False)
            crosshair = self.xy_scan.plot_widget.crosshairs[0]
            crosshair_size = (settings['x_range'], crosshair.size[1])
            crosshair.set_size(crosshair_size)
            crosshair = self.xz_scan.plot_widget.crosshairs[0]
            crosshair_size = (settings['x_range'], crosshair.size[1])
            crosshair.set_size(crosshair_size)
        if 'y_range' in settings:
            self._osd.y_optimizer_range_doubleSpinBox.blockSignals(True)
            self._osd.y_optimizer_range_doubleSpinBox.setValue(settings['y_range'])
            self._osd.y_optimizer_range_doubleSpinBox.blockSignals(False)
            crosshair = self.xy_scan.plot_widget.crosshairs[0]
            crosshair_size = (crosshair.size[0], settings['y_range'])
            crosshair.set_size(crosshair_size)
        if 'z_range' in settings:
            self._osd.z_optimizer_range_doubleSpinBox.blockSignals(True)
            self._osd.z_optimizer_range_doubleSpinBox.setValue(settings['z_range'])
            self._osd.z_optimizer_range_doubleSpinBox.blockSignals(False)
            crosshair = self.xz_scan.plot_widget.crosshairs[0]
            crosshair_size = (crosshair.size[0], settings['z_range'])
            crosshair.set_size(crosshair_size)
        if 'x_resolution' in settings:
            self._osd.x_optimizer_resolution_spinBox.blockSignals(True)
            self._osd.x_optimizer_resolution_spinBox.setValue(settings['x_resolution'])
            self._osd.x_optimizer_resolution_spinBox.blockSignals(False)
        if 'y_resolution' in settings:
            self._osd.y_optimizer_resolution_spinBox.blockSignals(True)
            self._osd.y_optimizer_resolution_spinBox.setValue(settings['y_resolution'])
            self._osd.y_optimizer_resolution_spinBox.blockSignals(False)
        if 'z_resolution' in settings:
            self._osd.z_optimizer_resolution_spinBox.blockSignals(True)
            self._osd.z_optimizer_resolution_spinBox.setValue(settings['z_resolution'])
            self._osd.z_optimizer_resolution_spinBox.blockSignals(False)
        if 'sequence' in settings:
            self._osd.optimization_sequence_lineEdit.blockSignals(True)
            self._osd.optimization_sequence_lineEdit.setText(','.join(settings['sequence']))
            self._osd.optimization_sequence_lineEdit.blockSignals(False)
        return

    @QtCore.Slot()
    def _xy_scan_triggered(self):
        start = self._mw.action_xy_scan.isEnabled()
        self.sigToggleScan.emit(start, 'xy')

    @QtCore.Slot()
    def _xz_scan_triggered(self):
        start = self._mw.action_xz_scan.isEnabled()
        self.sigToggleScan.emit(start, 'xz')
