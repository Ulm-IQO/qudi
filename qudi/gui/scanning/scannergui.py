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
from PySide2 import QtCore, QtGui, QtWidgets

import qudi.core.gui.uic as uic
from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.core.configoption import ConfigOption
from qudi.interface.scanning_probe_interface import ScanData
from qudi.core.module import GuiBase

from .axes_control_dockwidget import AxesControlDockWidget
from .optimizer_setting_dialog import OptimizerSettingDialog
from .scan_settings_dialog import ScannerSettingDialog
from .scan_dockwidget import Scan2DDockWidget, Scan1DDockWidget
from .optimizer_dockwidget import OptimizerDockWidget


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
    _window_state = StatusVar(name='window_state', default=None)
    _window_geometry = StatusVar(name='window_geometry', default=None)

    # signals
    sigScannerTargetChanged = QtCore.Signal(dict, object)
    sigScanSettingsChanged = QtCore.Signal(dict)
    sigToggleScan = QtCore.Signal(bool, tuple, object)
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

        # misc
        self._optimizer_id = 0
        return

    def on_activate(self):
        """ Initializes all needed UI files and establishes the connectors.

        This method executes the all the inits for the differnt GUIs and passes
        the event argument from fysom to the methods.
        """
        self._optimizer_id = self._optimize_logic().module_uuid

        self.scan_2d_dockwidgets = dict()
        self.scan_1d_dockwidgets = dict()

        # Initialize main window
        self._mw = ConfocalMainWindow()
        self._mw.setDockNestingEnabled(True)

        # Initialize fixed dockwidgets
        self._init_static_dockwidgets()

        # Initialize dialog windows
        self._init_optimizer_settings()
        self._init_scanner_settings()

        # Automatically generate scanning widgets for desired scans
        scans = list()
        axes = tuple(self._scanning_logic().scanner_axes)
        for i, first_ax in enumerate(axes, 1):
            if not scans:
                scans.append((first_ax,))
            for second_ax in axes[i:]:
                scans.append((first_ax, second_ax))
        for scan in scans:
            self._add_scan_dockwidget(scan)

        # Initialize widget data
        self.scanner_settings_updated()
        self.scanner_target_updated()
        self.scan_state_updated(self._scanning_logic().module_state() != 'idle')

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
            self._scanning_logic().set_target_position, QtCore.Qt.QueuedConnection
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

        self._scanning_logic().sigScannerTargetChanged.connect(
            self.scanner_target_updated, QtCore.Qt.QueuedConnection
        )
        self._scanning_logic().sigScanSettingsChanged.connect(
            self.scanner_settings_updated, QtCore.Qt.QueuedConnection
        )
        self._scanning_logic().sigScanStateChanged.connect(
            self.scan_state_updated, QtCore.Qt.QueuedConnection
        )
        self._data_logic().sigHistoryScanDataRestored.connect(
            self._update_scan_data, QtCore.Qt.QueuedConnection
        )
        self._optimize_logic().sigOptimizeStateChanged.connect(
            self.optimize_state_updated, QtCore.Qt.QueuedConnection
        )

        # Initialize dockwidgets to default view
        self.restore_default_view()
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
        self._scanning_logic().sigScannerTargetChanged.disconnect(self.scanner_target_updated)
        self._scanning_logic().sigScanSettingsChanged.disconnect(self.scanner_settings_updated)
        self._scanning_logic().sigScanStateChanged.disconnect(self.scan_state_updated)
        self._optimize_logic().sigOptimizeStepComplete.disconnect(self.optimization_step_updated)
        self._optimize_logic().sigOptimizeStateChanged.disconnect(self.optimize_state_updated)
        self._data_logic().sigHistoryScanDataRestored.disconnect(self._update_scan_data)

        for scan in tuple(self.scan_1d_dockwidgets):
            self._remove_scan_dockwidget(scan)
        for scan in tuple(self.scan_2d_dockwidgets):
            self._remove_scan_dockwidget(scan)
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
        self._osd = OptimizerSettingDialog(tuple(self._scanning_logic().scanner_axes.values()),
                                           tuple(self._scanning_logic().scanner_channels.values()))

        # Connect MainWindow actions
        self._mw.action_optimizer_settings.triggered.connect(lambda x: self._osd.exec_())

        # Connect the action of the settings window with the code:
        self._osd.accepted.connect(self.change_optimizer_settings)
        self._osd.rejected.connect(self.update_optimizer_settings)
        self._osd.button_box.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(
            self.change_optimizer_settings)
        return

    def _init_scanner_settings(self):
        """
        """
        # Create the Settings dialog
        self._ssd = ScannerSettingDialog(tuple(self._scanning_logic().scanner_axes.values()))

        # Connect MainWindow actions
        self._mw.action_scanner_settings.triggered.connect(lambda x: self._ssd.exec_())

        # Connect the action of the settings dialog with the GUI module:
        self._ssd.accepted.connect(self.change_scanner_settings)
        self._ssd.rejected.connect(self.restore_scanner_settings)
        self._ssd.button_box.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(
            self.change_scanner_settings
        )

    def _init_static_dockwidgets(self):
        self.scanner_control_dockwidget = AxesControlDockWidget(
            tuple(self._scanning_logic().scanner_axes.values())
        )
        if self._default_position_unit_prefix is not None:
            self.scanner_control_dockwidget.set_assumed_unit_prefix(
                self._default_position_unit_prefix
            )
        self.scanner_control_dockwidget.setAllowedAreas(QtCore.Qt.BottomDockWidgetArea)
        self._mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.scanner_control_dockwidget)
        self.scanner_control_dockwidget.visibilityChanged.connect(
            self._mw.action_view_scanner_control.setChecked)
        self._mw.action_view_scanner_control.triggered[bool].connect(
            self.scanner_control_dockwidget.setVisible)
        self.scanner_control_dockwidget.sigResolutionChanged.connect(
            lambda ax, res: self.sigScanSettingsChanged.emit({'resolution': {ax: res}})
        )
        self.scanner_control_dockwidget.sigRangeChanged.connect(
            lambda ax, ranges: self.sigScanSettingsChanged.emit({'range': {ax: ranges}})
        )
        self.scanner_control_dockwidget.sigTargetChanged.connect(
            lambda ax, pos: self.sigScannerTargetChanged.emit({ax: pos}, self.module_uuid)
        )
        # ToDo: Implement a way to avoid too fast position update from slider movement.
        #  Currently the scanner target position is only updated upon slider release.
        # self.scanner_control_dockwidget.sigSliderMoved.connect()

        self.optimizer_dockwidget = OptimizerDockWidget()
        self.optimizer_dockwidget.setAllowedAreas(QtCore.Qt.TopDockWidgetArea)
        self._mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.optimizer_dockwidget)
        self.optimizer_dockwidget.visibilityChanged.connect(
            self._mw.action_view_optimizer.setChecked)
        self._mw.action_view_optimizer.triggered[bool].connect(
            self.optimizer_dockwidget.setVisible)

        self._mw.util_toolBar.visibilityChanged.connect(
            self._mw.action_view_toolbar.setChecked)
        self._mw.action_view_toolbar.triggered[bool].connect(self._mw.util_toolBar.setVisible)

    @QtCore.Slot()
    def restore_default_view(self):
        """ Restore the arrangement of DockWidgets to default """
        self._mw.setDockNestingEnabled(True)

        # Remove all dockwidgets from main window layout
        self._mw.removeDockWidget(self.optimizer_dockwidget)
        self._mw.removeDockWidget(self.scanner_control_dockwidget)
        for dockwidget in self.scan_2d_dockwidgets.values():
            self._mw.removeDockWidget(dockwidget)
        for dockwidget in self.scan_1d_dockwidgets.values():
            self._mw.removeDockWidget(dockwidget)

        # Return toolbar to default position
        self._mw.util_toolBar.show()
        self._mw.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, self._mw.util_toolBar)

        # Add axes control dock widget to layout
        self.scanner_control_dockwidget.setFloating(False)
        self.scanner_control_dockwidget.show()
        self._mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.scanner_control_dockwidget)
        # Add dynamically created dock widgets to layout
        dockwidgets_2d = tuple(self.scan_2d_dockwidgets.values())
        dockwidgets_1d = tuple(self.scan_1d_dockwidgets.values())
        multiple_2d_scans = len(dockwidgets_2d) > 1
        multiple_1d_scans = len(dockwidgets_1d) > 1
        has_1d_scans = bool(dockwidgets_1d)
        has_2d_scans = bool(dockwidgets_2d)
        if has_2d_scans:
            for i, dockwidget in enumerate(dockwidgets_2d):
                dockwidget.show()
                self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, dockwidget)
                dockwidget.setFloating(False)
        if has_1d_scans:
            for i, dockwidget in enumerate(dockwidgets_1d):
                dockwidget.show()
                self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, dockwidget)
                dockwidget.setFloating(False)
        # Add optimizer dock widget to layout
        self.optimizer_dockwidget.show()
        self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.optimizer_dockwidget)
        self.optimizer_dockwidget.setFloating(False)

        # tabify dockwidgets if needed
        if multiple_2d_scans:
            if has_1d_scans:
                for ii, dockwidget in enumerate(dockwidgets_2d[1:]):
                    self._mw.tabifyDockWidget(dockwidgets_2d[ii], dockwidget)
                dockwidgets_2d[0].raise_()
            else:
                for ii, dockwidget in enumerate(dockwidgets_2d[2:]):
                    if ii == 0:
                        self._mw.tabifyDockWidget(dockwidgets_2d[ii], dockwidget)
                    else:
                        self._mw.tabifyDockWidget(dockwidgets_2d[ii+1], dockwidget)
                dockwidgets_2d[0].raise_()
        if multiple_1d_scans:
            for ii, dockwidget in enumerate(dockwidgets_1d[1:]):
                self._mw.tabifyDockWidget(dockwidgets_1d[ii], dockwidget)
            dockwidgets_1d[0].raise_()

        # split scan dock widget with optimizer dock widget if needed. Resize all groups.
        if has_1d_scans and has_2d_scans:
            self._mw.splitDockWidget(dockwidgets_1d[0],
                                     self.optimizer_dockwidget,
                                     QtCore.Qt.Vertical)
            self._mw.resizeDocks((dockwidgets_1d[0], self.optimizer_dockwidget),
                                 (3, 2),
                                 QtCore.Qt.Vertical)
            self._mw.resizeDocks((dockwidgets_2d[0], dockwidgets_1d[0]),
                                 (1, 1),
                                 QtCore.Qt.Horizontal)
        elif multiple_2d_scans:
            self._mw.splitDockWidget(dockwidgets_2d[1],
                                     self.optimizer_dockwidget,
                                     QtCore.Qt.Vertical)
            self._mw.resizeDocks((dockwidgets_2d[1], self.optimizer_dockwidget),
                                 (3, 2),
                                 QtCore.Qt.Vertical)
            self._mw.resizeDocks((dockwidgets_2d[0], dockwidgets_2d[1]),
                                 (1, 1),
                                 QtCore.Qt.Horizontal)
        elif has_1d_scans:
            self._mw.resizeDocks((dockwidgets_1d[0], self.optimizer_dockwidget),
                                 (1, 1),
                                 QtCore.Qt.Horizontal)
        elif has_2d_scans:
            self._mw.resizeDocks((dockwidgets_2d[0], self.optimizer_dockwidget),
                                 (1, 1),
                                 QtCore.Qt.Horizontal)
        return

    def _remove_scan_dockwidget(self, axes):
        if axes in tuple(self.scan_1d_dockwidgets):
            self._mw.removeDockWidget(self.scan_1d_dockwidgets[axes])
            self.scan_1d_dockwidgets[axes].sigPositionDragged.disconnect()
            self.scan_1d_dockwidgets[axes].sigScanToggled.disconnect()
            self.scan_1d_dockwidgets[axes].sigMouseAreaSelected.disconnect()
            self.scan_1d_dockwidgets[axes].deleteLater()
            del self.scan_1d_dockwidgets[axes]
        elif axes in tuple(self.scan_2d_dockwidgets):
            self._mw.removeDockWidget(self.scan_2d_dockwidgets[axes])
            self.scan_2d_dockwidgets[axes].sigPositionDragged.disconnect()
            self.scan_2d_dockwidgets[axes].sigScanToggled.disconnect()
            self.scan_2d_dockwidgets[axes].sigMouseAreaSelected.disconnect()
            self.scan_2d_dockwidgets[axes].deleteLater()
            del self.scan_2d_dockwidgets[axes]
        return

    def _add_scan_dockwidget(self, axes):
        axes_constr = self._scanning_logic().scanner_axes
        channel_constr = self._scanning_logic().scanner_channels
        optimizer_range = self._optimize_logic().scan_range
        axes = tuple(axes)
        if len(axes) == 1:
            if axes in self.scan_1d_dockwidgets:
                self.log.error('Unable to add scanning widget for axes {0}. Widget for this scan '
                               'already created. Remove old widget first.'.format(axes))
                return
            dockwidget = Scan1DDockWidget(scan_axis=axes_constr[axes[0]],
                                          channels=tuple(channel_constr.values()))
            dockwidget.setAllowedAreas(QtCore.Qt.TopDockWidgetArea)
            self.scan_1d_dockwidgets[axes] = dockwidget
            self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, dockwidget)

            dockwidget.sigPositionDragged.connect(self.__get_marker_update_func(axes))
            dockwidget.sigScanToggled.connect(self.__get_toggle_scan_func(axes))
            dockwidget.sigMouseAreaSelected.connect(self.__get_range_from_selection_func(axes))
        else:
            if axes in self.scan_2d_dockwidgets:
                self.log.error('Unable to add scanning widget for axes {0}. Widget for this scan '
                               'already created. Remove old widget first.'.format(axes))
                return
            dockwidget = Scan2DDockWidget(scan_axes=(axes_constr[axes[0]], axes_constr[axes[1]]),
                                          channels=tuple(channel_constr.values()))
            dockwidget.setAllowedAreas(QtCore.Qt.TopDockWidgetArea)
            dockwidget.crosshair.set_size(tuple(optimizer_range[ax] for ax in axes))
            self.scan_2d_dockwidgets[axes] = dockwidget
            self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, dockwidget)

            dockwidget.sigPositionDragged.connect(self.__get_crosshair_update_func(axes))
            dockwidget.sigScanToggled.connect(self.__get_toggle_scan_func(axes))
            dockwidget.sigMouseAreaSelected.connect(self.__get_range_from_selection_func(axes))
        return

    @QtCore.Slot(bool)
    def toggle_cursor_zoom(self, enable):
        if self._mw.action_utility_zoom.isChecked() != enable:
            self._mw.action_utility_zoom.blockSignals(True)
            self._mw.action_utility_zoom.setChecked(enable)
            self._mw.action_utility_zoom.blockSignals(False)

        for dockwidget in self.scan_2d_dockwidgets.values():
            dockwidget.toggle_selection(enable)
        for dockwidget in self.scan_1d_dockwidgets.values():
            dockwidget.toggle_selection(enable)
        return

    @QtCore.Slot()
    def change_scanner_settings(self):
        """ ToDo: Document
        """
        # ToDo: Implement backwards scanning functionality
        forward_freq = {ax: freq[0] for ax, freq in self._ssd.settings_widget.frequency.items()}
        self.sigScanSettingsChanged.emit({'frequency': forward_freq})

    @QtCore.Slot()
    def restore_scanner_settings(self):
        """ ToDo: Document
        """
        self.scanner_settings_updated({'frequency': self._scanning_logic().scan_frequency})

    @QtCore.Slot()
    @QtCore.Slot(dict)
    def scanner_settings_updated(self, settings=None):
        """
        Update scanner settings from logic and set widgets accordingly.

        @param dict settings: Settings dict containing the scanner settings to update.
                              If None (default) read the scanner setting from logic and update.
        """
        if not isinstance(settings, dict):
            settings = self._scanning_logic().scan_settings

        # ToDo: Handle all remaining settings
        # ToDo: Implement backwards scanning functionality

        if 'resolution' in settings:
            self.scanner_control_dockwidget.set_resolution(settings['resolution'])
        if 'range' in settings:
            self.scanner_control_dockwidget.set_range(settings['range'])
        if 'frequency' in settings:
            old_freq = self._ssd.settings_widget.frequency
            new_freq = {
                ax: (forward, old_freq[ax][1]) for ax, forward in settings['frequency'].items()
            }
            self._ssd.settings_widget.set_frequency(new_freq)
        return

    def set_scanner_target_position(self, target_pos):
        """

        @param dict target_pos:
        """
        self.sigScannerTargetChanged.emit(target_pos, self.module_uuid)

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
        if caller_id is self.module_uuid:
            return

        if not isinstance(pos_dict, dict):
            pos_dict = self._scanning_logic().scanner_target

        self._update_scan_crosshairs(pos_dict)
        self.scanner_control_dockwidget.set_target(pos_dict)
        return

    @QtCore.Slot(bool, object, object)
    def scan_state_updated(self, is_running, scan_data=None, caller_id=None):
        scan_axes = scan_data.scan_axes if scan_data is not None else None
        self._toggle_enable_scan_buttons(not is_running, exclude_scan=scan_axes)
        self._toggle_enable_actions(not is_running)
        self._toggle_enable_scan_crosshairs(not is_running)
        if scan_data is not None:
            if caller_id is self._optimizer_id:
                channel = self._osd.settings['data_channel']
                if scan_data.scan_dimension == 2:
                    x_ax, y_ax = scan_data.scan_axes
                    self.optimizer_dockwidget.set_image(image=scan_data.data[channel],
                                                        extent=scan_data.scan_range)
                    self.optimizer_dockwidget.set_image_label(axis='bottom',
                                                              text=x_ax,
                                                              units=scan_data.axes_units[x_ax])
                    self.optimizer_dockwidget.set_image_label(axis='left',
                                                              text=y_ax,
                                                              units=scan_data.axes_units[y_ax])
                elif scan_data.scan_dimension == 1:
                    x_ax = scan_data.scan_axes[0]
                    self.optimizer_dockwidget.set_plot_data(
                        x=np.linspace(*scan_data.scan_range[0], scan_data.scan_resolution[0]),
                        y=scan_data.data[channel]
                    )
                    self.optimizer_dockwidget.set_plot_label(axis='bottom',
                                                             text=x_ax,
                                                             units=scan_data.axes_units[x_ax])
                    self.optimizer_dockwidget.set_plot_label(axis='left',
                                                             text=channel,
                                                             units=scan_data.channel_units[channel])
            else:
                if scan_data.scan_dimension == 2:
                    dockwidget = self.scan_2d_dockwidgets.get(scan_axes, None)
                else:
                    dockwidget = self.scan_1d_dockwidgets.get(scan_axes, None)
                if dockwidget is not None:
                    dockwidget.toggle_scan(is_running)
                    self._update_scan_data(scan_data)
        return

    @QtCore.Slot(bool, dict, object)
    def optimize_state_updated(self, is_running, optimal_position=None, fit_data=None):
        self._toggle_enable_scan_buttons(not is_running)
        self._toggle_enable_actions(not is_running,
                                    exclude_action=self._mw.action_optimize_position)
        self._toggle_enable_scan_crosshairs(not is_running)
        self._mw.action_optimize_position.setChecked(is_running)
        # Update optimal position crosshair and marker
        if isinstance(optimal_position, dict):
            if len(optimal_position) == 2:
                self.optimizer_dockwidget.set_2d_position(tuple(optimal_position.values()))
            elif len(optimal_position) == 1:
                self.optimizer_dockwidget.set_1d_position(next(iter(optimal_position.values())))
        if fit_data is not None:
            if fit_data.ndim == 1:
                self.optimizer_dockwidget.set_fit_data(y=fit_data)
        return

    @QtCore.Slot(bool)
    def toggle_optimize(self, enabled):
        """
        """
        self._toggle_enable_actions(not enabled, exclude_action=self._mw.action_optimize_position)
        self._toggle_enable_scan_buttons(not enabled)
        self._toggle_enable_scan_crosshairs(not enabled)
        self.sigToggleOptimize.emit(enabled)

    def _update_scan_crosshairs(self, pos_dict, exclude_scan=None):
        """
        """
        for scan_axes, dockwidget in self.scan_2d_dockwidgets.items():
            if exclude_scan == scan_axes or not any(ax in pos_dict for ax in scan_axes):
                continue
            old_x, old_y = dockwidget.crosshair.position
            new_pos = (pos_dict.get(scan_axes[0], old_x), pos_dict.get(scan_axes[1], old_y))
            dockwidget.crosshair.set_position(new_pos)
        for scan_axes, dockwidget in self.scan_1d_dockwidgets.items():
            if exclude_scan == scan_axes or not any(ax in pos_dict for ax in scan_axes):
                continue
            new_pos = pos_dict.get(scan_axes[0], dockwidget.marker.position)
            dockwidget.marker.set_position(new_pos)

    def _update_scan_data(self, scan_data):
        """
        @param ScanData scan_data:
        """
        axes = scan_data.scan_axes
        data = scan_data.data
        extent = scan_data.scan_range
        if scan_data.scan_dimension == 2:
            dockwidget = self.scan_2d_dockwidgets.get(axes, None)
            if dockwidget is None:
                self.log.error('No 2D scan dockwidget found for scan axes {0}'.format(axes))
                return
            dockwidget.set_scan_data(data)
            if data is not None:
                dockwidget.set_image_extent(extent)
            dockwidget.scan_widget.autoRange()
        else:
            dockwidget = self.scan_1d_dockwidgets.get(axes, None)
            if dockwidget is None:
                self.log.error('No 1D scan dockwidget found for scan axes {0}'.format(axes))
                return
            dockwidget.set_scan_data(data, x=np.linspace(*extent[0], scan_data.scan_resolution[0]))
        return

    def _toggle_enable_scan_crosshairs(self, enable):
        for dockwidget in self.scan_2d_dockwidgets.values():
            dockwidget.toggle_crosshair(enable)
        for axes, dockwidget in self.scan_1d_dockwidgets.items():
            dockwidget.toggle_marker(enable)

    def _toggle_enable_scan_buttons(self, enable, exclude_scan=None):
        for axes, dockwidget in self.scan_2d_dockwidgets.items():
            if exclude_scan == axes:
                continue
            dockwidget.toggle_enabled(enable)
        for axes, dockwidget in self.scan_1d_dockwidgets.items():
            if exclude_scan == axes:
                continue
            dockwidget.toggle_enabled(enable)

    def _toggle_enable_actions(self, enable, exclude_action=None):
        if exclude_action is not self._mw.action_utility_zoom:
            self._mw.action_utility_zoom.setEnabled(enable)
        if exclude_action is not self._mw.action_utility_full_range:
            self._mw.action_utility_full_range.setEnabled(enable)
        if exclude_action is not self._mw.action_history_back:
            self._mw.action_history_back.setEnabled(enable)
        if exclude_action is not self._mw.action_history_forward:
            self._mw.action_history_forward.setEnabled(enable)
        if exclude_action is not self._mw.action_optimize_position:
            self._mw.action_optimize_position.setEnabled(enable)

    def __get_crosshair_update_func(self, axes):
        def update_func(x, y):
            pos_dict = {axes[0]: x, axes[1]: y}
            self._update_scan_crosshairs(pos_dict, exclude_scan=axes)
            # self.scanner_control_dockwidget.widget().set_target(pos_dict)
            self.set_scanner_target_position(pos_dict)
        return update_func

    def __get_marker_update_func(self, axes):
        def update_func(pos):
            pos_dict = {axes[0]: pos}
            self._update_scan_crosshairs(pos_dict, exclude_scan=axes)
            # self.scanner_control_dockwidget.widget().set_target(pos_dict)
            self.set_scanner_target_position(pos_dict)
        return update_func

    def __get_toggle_scan_func(self, axes):
        def toggle_func(enabled):
            self._toggle_enable_scan_buttons(not enabled, exclude_scan=axes)
            self._toggle_enable_actions(not enabled)
            self._toggle_enable_scan_crosshairs(not enabled)
            self.sigToggleScan.emit(enabled, axes, self.module_uuid)
        return toggle_func

    def __get_range_from_selection_func(self, axes):
        if len(axes) == 2:
            def set_range_func(x_range, y_range):
                x_min, x_max = min(x_range), max(x_range)
                y_min, y_max = min(y_range), max(y_range)
                self.sigScanSettingsChanged.emit(
                    {'range': {axes[0]: (x_min, x_max), axes[1]: (y_min, y_max)}}
                )
                self._mw.action_utility_zoom.setChecked(False)
        else:
            def set_range_func(start, stop):
                extent = (stop, start) if start > stop else (start, stop)
                self.sigScanSettingsChanged.emit({'range': {axes[0]: extent}})
                self._mw.action_utility_zoom.setChecked(False)
        return set_range_func

    @QtCore.Slot()
    def change_optimizer_settings(self):
        # FIXME: sequence needs to be properly implemented
        self.sigOptimizerSettingsChanged.emit(self._osd.settings)
        return

    @QtCore.Slot()
    @QtCore.Slot(dict)
    def update_optimizer_settings(self, settings=None):
        if not isinstance(settings, dict):
            settings = self._optimize_logic().optimize_settings

        # Update optimizer settings QDialog
        self._osd.change_settings(settings)

        # FIXME: sequence needs to be properly implemented
        # Adjust optimizer scan axis labels
        if 'scan_sequence' in settings:
            axes_constr = self._scanning_logic().scanner_axes
            for seq_step in settings['scan_sequence']:
                if len(seq_step) == 1:
                    axis = seq_step[0]
                    self.optimizer_dockwidget.set_plot_label(axis='bottom',
                                                             text=axis,
                                                             units=axes_constr[axis].unit)
                    self.optimizer_dockwidget.set_plot_data()
                    self.optimizer_dockwidget.set_fit_data()
                elif len(seq_step) == 2:
                    x_axis, y_axis = seq_step
                    self.optimizer_dockwidget.set_image_label(axis='bottom',
                                                              text=x_axis,
                                                              units=axes_constr[x_axis].unit)
                    self.optimizer_dockwidget.set_image_label(axis='left',
                                                              text=y_axis,
                                                              units=axes_constr[y_axis].unit)
                    self.optimizer_dockwidget.set_image(None, extent=((-0.5, 0.5), (-0.5, 0.5)))

        # Adjust 1D plot y-axis label
        if 'data_channel' in settings:
            channel_constr = self._scanning_logic().scanner_channels
            channel = settings['data_channel']
            self.optimizer_dockwidget.set_plot_label(axis='left',
                                                     text=channel,
                                                     units=channel_constr[channel].unit)

        # Adjust crosshair size according to optimizer range
        if 'scan_range' in settings:
            for scan_axes, dockwidget in self.scan_2d_dockwidgets.items():
                if any(ax in settings['scan_range'] for ax in scan_axes):
                    crosshair = dockwidget.scan_widget.crosshairs[0]
                    x_size = settings['scan_range'].get(scan_axes[0], crosshair.size[0])
                    y_size = settings['scan_range'].get(scan_axes[1], crosshair.size[1])
                    crosshair.set_size((x_size, y_size))
        return
