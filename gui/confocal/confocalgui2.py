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

from core.module import Connector, ConfigOption, StatusVar
from qtwidgets.scan_plotwidget import ScanImageItem
from qtwidgets.scientific_spinbox import ScienDSpinBox
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

    sigKeyboardPressed = QtCore.Signal(QtCore.QEvent)

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_confocalgui2.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        return

    def keyPressEvent(self, event):
        """Pass the keyboard press event from the main window further. """
        self.sigKeyboardPressed.emit(event)
        super().keyPressEvent(event)
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

        self.plot_widget = widget.image_scanPlotWidget
        self.colorbar = widget.colorbar_colorBarWidget
        self.image_item = ScanImageItem(image=np.zeros((2, 2)), axisOrder='row-major')
        self.plot_widget.addItem(self.image_item)
        self.colorbar.assign_image_item(self.image_item)

        self.setWidget(widget)
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
        self.image_item = ScanImageItem(image=np.zeros((2, 2)), axisOrder='row-major')
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


class TiltCorrectionDockWidget(QtWidgets.QDockWidget):
    """ Create the tilt correction dockwidget based on the corresponding *.ui file.
    """
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_tilt_correction_widget.ui')

        super().__init__('Tilt Correction')
        self.setObjectName('tilt_correction_dockWidget')

        # Load UI file
        widget = QtWidgets.QWidget()
        uic.loadUi(ui_file, widget)
        widget.setObjectName('tilt_correction_widget')

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


class ConfocalGui(GUIBase):
    """ Main Confocal Class for xy and depth scans.
    """
    _modclass = 'ConfocalGui'
    _modtype = 'gui'

    # declare connectors
    scannerlogic = Connector(interface='ConfocalLogic')

    # config options for gui
    image_axes_padding = ConfigOption(name='image_axes_padding', default=0.02)
    default_position_unit_prefix = ConfigOption(name='default_position_unit_prefix', default=None)

    # status vars
    slider_small_step = StatusVar(name='slider_small_step', default=10e-9)
    slider_big_step = StatusVar(name='slider_big_step', default=100e-9)
    _window_state = StatusVar(name='window_state', default=None)
    _window_geometry = StatusVar(name='window_geometry', default=None)

    # signals
    sigStartOptimizer = QtCore.Signal(list, str)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # QMainWindow and QDialog child instances
        self._mw = None
        self._ssd = None
        self._osd = None

        # Plot items
        self.optimizer_2d_image = None
        self.optimizer_1d_plot = None
        self.optimizer_1d_fit_plot = None

        # References to automatically generated GUI elements
        self.axes_control_widgets = None
        self.optimizer_settings_axes_widgets = None
        self.scan_2d_dockwidgets = None
        self.scan_1d_dockwidgets = None
        self.optimizer_dockwidget = None
        self.tilt_correction_dockwidget = None
        return

    def on_activate(self):
        """ Initializes all needed UI files and establishes the connectors.

        This method executes the all the inits for the differnt GUIs and passes
        the event argument from fysom to the methods.
        """
        self.scan_2d_dockwidgets = dict()
        self.scan_1d_dockwidgets = dict()

        # Initialize main window and dialogues
        self._ssd = ScannerSettingDialog()
        self._osd = OptimizerSettingDialog()
        self._mw = ConfocalMainWindow()

        # Configure widgets according to available scan axes
        self._generate_axes_control_widgets()
        self._generate_optimizer_axes_widgets()

        # Set input widget value ranges and units according to scanner constraints
        self.apply_scanner_constraints()

        # Initialize widget data
        self.scanner_settings_updated()
        self.scanner_position_updated()
        self.scan_data_updated()

        # Initialize fixed dockwidgets
        self.optimizer_dockwidget = OptimizerDockWidget()
        self.optimizer_dockwidget.setAllowedAreas(QtCore.Qt.TopDockWidgetArea)
        self.optimizer_dockwidget.scan_widget.toggle_crosshair(True, movable=False)
        self.optimizer_dockwidget.scan_widget.setAspectLocked(lock=True, ratio=1.0)
        self.tilt_correction_dockwidget = TiltCorrectionDockWidget()
        self.tilt_correction_dockwidget.setAllowedAreas(QtCore.Qt.RightDockWidgetArea)

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

        self.show()
        return

    def init_main(self):
        """
        Definition, configuration and initialisation of the confocal GUI.

        This init connects all the graphic modules, which were created in the *.ui file and
        configures the event handling between the modules. Moreover it sets default values and
        constraints.
        """
        ###################################################################
        #               Icons for the scan actions                        #
        ###################################################################

        self._scan_xy_single_icon = QtGui.QIcon()
        self._scan_xy_single_icon.addPixmap(
            QtGui.QPixmap("artwork/icons/qudiTheme/22x22/scan-xy-start.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off)

        self._scan_depth_single_icon = QtGui.QIcon()
        self._scan_depth_single_icon.addPixmap(
            QtGui.QPixmap("artwork/icons/qudiTheme/22x22/scan-depth-start.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off)

        self._scan_xy_loop_icon = QtGui.QIcon()
        self._scan_xy_loop_icon.addPixmap(
            QtGui.QPixmap("artwork/icons/qudiTheme/22x22/scan-xy-loop.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off)

        self._scan_depth_loop_icon = QtGui.QIcon()
        self._scan_depth_loop_icon.addPixmap(
            QtGui.QPixmap("artwork/icons/qudiTheme/22x22/scan-depth-loop.png"),
            QtGui.QIcon.Normal,
            QtGui.QIcon.Off)

        self._mw.sigKeyboardPressed.connect(self.keyPressEvent)
        self.show()

    def initOptimizerSettingsUI(self):
        """ Definition, configuration and initialisation of the optimizer settings GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        Moreover it sets default values if not existed in the logic modules.
        """
        # Create the Settings window
        self._osd = OptimizerSettingDialog()
        # Connect the action of the settings window with the code:
        self._osd.accepted.connect(self.update_optimizer_settings)
        self._osd.rejected.connect(self.keep_former_optimizer_settings)
        self._osd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.update_optimizer_settings)

        # Set up and connect xy channel combobox
        scan_channels = self._optimizer_logic.get_scanner_count_channels()
        for n, ch in enumerate(scan_channels):
            self._osd.opt_channel_ComboBox.addItem(str(ch), n)

        # Generation of the fit params tab ##################
        self._osd.fit_tab = FitParametersWidget(self._optimizer_logic.z_params)
        self._osd.settings_tabWidget.addTab(self._osd.fit_tab, "Fit Params")

        # write the configuration to the settings window of the GUI.
        self.keep_former_optimizer_settings()

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
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

    def _generate_axes_control_widgets(self):
        font = QtGui.QFont()
        font.setBold(True)
        layout = self._mw.centralwidget.layout()

        self.axes_control_widgets = dict()
        for index, axis_name in enumerate(self.scannerlogic().scanner_axes_names, 1):
            if index == 1:
                label = self._mw.axis_0_label
                label.setFont(font)
                label.setText('{0}-Axis:'.format(axis_name))
                res_spinbox = self._mw.axis_0_resolution_spinBox
                min_spinbox = self._mw.axis_0_min_range_scienDSpinBox
                max_spinbox = self._mw.axis_0_max_range_scienDSpinBox
                slider = self._mw.axis_0_slider
                pos_spinbox = self._mw.axis_0_position_scienDSpinBox
            else:
                label = QtWidgets.QLabel('{0}-Axis:'.format(axis_name))
                label.setFont(font)
                label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

                res_spinbox = QtWidgets.QSpinBox()
                res_spinbox.setRange(2, 2 ** 31 - 1)
                res_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
                res_spinbox.setMinimumSize(50, 0)
                res_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                          QtWidgets.QSizePolicy.Preferred)

                min_spinbox = ScienDSpinBox()
                min_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
                min_spinbox.setMinimumSize(75, 0)
                min_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                          QtWidgets.QSizePolicy.Preferred)

                max_spinbox = ScienDSpinBox()
                max_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
                max_spinbox.setMinimumSize(75, 0)
                max_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                          QtWidgets.QSizePolicy.Preferred)

                slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
                slider.setMinimumSize(150, 0)
                slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

                pos_spinbox = ScienDSpinBox()
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

            # Remember widgets references for later access
            self.axes_control_widgets[axis_name] = dict()
            self.axes_control_widgets[axis_name]['label'] = label
            self.axes_control_widgets[axis_name]['res_spinbox'] = res_spinbox
            self.axes_control_widgets[axis_name]['min_spinbox'] = min_spinbox
            self.axes_control_widgets[axis_name]['max_spinbox'] = max_spinbox
            self.axes_control_widgets[axis_name]['slider'] = slider
            self.axes_control_widgets[axis_name]['pos_spinbox'] = pos_spinbox

        # layout.removeWidget(line)
        layout.addWidget(self._mw.line, 0, 2, -1, 1)
        layout.addWidget(self._mw.line_2, 0, 5, -1, 1)
        layout.setColumnStretch(5, 1)
        return

    def _generate_optimizer_axes_widgets(self):
        font = QtGui.QFont()
        font.setBold(True)
        layout = self._osd.scan_ranges_gridLayout

        self.optimizer_settings_axes_widgets = dict()
        for index, axis_name in enumerate(self.scannerlogic().scanner_axes_names, 1):
            label_text = '{0}-Axis:'.format(axis_name)
            if index == 1:
                label = self._osd.axis_0_label
                label.setFont(font)
                label.setText(label_text)
                res_spinbox = self._osd.axis_0_optimizer_resolution_spinBox
                range_spinbox = self._osd.axis_0_optimizer_range_scienDSpinBox
            else:
                label = QtWidgets.QLabel(label_text)
                label.setFont(font)
                label.setAlignment(QtCore.Qt.AlignRight)

                range_spinbox = ScienDSpinBox()
                range_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
                range_spinbox.setMinimumSize(70, 0)
                range_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                            QtWidgets.QSizePolicy.Preferred)

                res_spinbox = QtWidgets.QSpinBox()
                res_spinbox.setRange(2, 2 ** 31 - 1)
                res_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
                res_spinbox.setMinimumSize(70, 0)
                res_spinbox.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                          QtWidgets.QSizePolicy.Preferred)

                # Add to layout
                layout.addWidget(label, index, 0)
                layout.addWidget(range_spinbox, index, 1)
                layout.addWidget(res_spinbox, index, 2)

            # Remember widgets references for later access
            self.optimizer_settings_axes_widgets[axis_name] = dict()
            self.optimizer_settings_axes_widgets[axis_name]['label'] = label
            self.optimizer_settings_axes_widgets[axis_name]['range_spinbox'] = range_spinbox
            self.optimizer_settings_axes_widgets[axis_name]['res_spinbox'] = res_spinbox
        return

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
        for i, dockwidget in enumerate(self.scan_1d_dockwidgets.values()):
            dockwidget.show()
            dockwidget.setFloating(False)
            self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, dockwidget)
            if i > 0:
                first_dockwidget = self.scan_1d_dockwidgets[list(self.scan_1d_dockwidgets)[0]]
                self._mw.tabifyDockWidget(first_dockwidget, dockwidget)

        # Handle static dock widgets
        self.optimizer_dockwidget.setFloating(False)
        self.tilt_correction_dockwidget.setFloating(False)
        self.tilt_correction_dockwidget.hide()
        self._mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.tilt_correction_dockwidget)
        self.optimizer_dockwidget.show()
        self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.optimizer_dockwidget)
        if self.scan_1d_dockwidgets:
            dockwidget = self.scan_1d_dockwidgets[list(self.scan_1d_dockwidgets)[0]]
            self._mw.splitDockWidget(dockwidget, self.optimizer_dockwidget, QtCore.Qt.Vertical)
        elif len(self.scan_2d_dockwidgets) > 1:
            dockwidget = self.scan_2d_dockwidgets[list(self.scan_2d_dockwidgets)[1]]
            self._mw.splitDockWidget(dockwidget, self.optimizer_dockwidget, QtCore.Qt.Vertical)
        return

    def apply_scanner_constraints(self):
        """ Set limits on input widgets according to scanner hardware constraints. """
        constraints = self.scannerlogic().scanner_constraints

        # Apply constraints for every scannner axis
        for index, (axis, axis_dict) in enumerate(constraints.items()):
            # Set value ranges
            res_range = (max(2, axis_dict['min_resolution']),
                         min(2**31-1, axis_dict['max_resolution']))
            self.axes_control_widgets[axis]['res_spinbox'].setRange(*res_range)
            self.axes_control_widgets[axis]['min_spinbox'].setRange(axis_dict['min_value'],
                                                                    axis_dict['max_value'])
            self.axes_control_widgets[axis]['max_spinbox'].setRange(axis_dict['min_value'],
                                                                    axis_dict['max_value'])
            self.axes_control_widgets[axis]['pos_spinbox'].setRange(axis_dict['min_value'],
                                                                    axis_dict['max_value'])
            self.axes_control_widgets[axis]['slider'].setRange(axis_dict['min_value'],
                                                               axis_dict['max_value'])
            self.optimizer_settings_axes_widgets[axis]['range_spinbox'].setRange(
                0, axis_dict['max_value'] - axis_dict['min_value'])
            self.optimizer_settings_axes_widgets[axis]['res_spinbox'].setRange(*res_range)
            # Set units as SpinBox suffix
            self.axes_control_widgets[axis]['min_spinbox'].setSuffix(axis_dict['unit'])
            self.axes_control_widgets[axis]['max_spinbox'].setSuffix(axis_dict['unit'])
            self.axes_control_widgets[axis]['pos_spinbox'].setSuffix(axis_dict['unit'])
            self.optimizer_settings_axes_widgets[axis]['range_spinbox'].setSuffix(axis_dict['unit'])

        # FIXME: Apply general scanner constraints
        return

    def _remove_scan_dockwidget(self, key):
        if key in self.scan_1d_dockwidgets:
            self._mw.removeDockWidget(self.scan_1d_dockwidgets[key])
            del self.scan_1d_dockwidgets[key]
        elif key in self.scan_2d_dockwidgets:
            self._mw.removeDockWidget(self.scan_2d_dockwidgets[key])
            del self.scan_2d_dockwidgets[key]
        return

    def _add_scan_dockwidget(self, key):
        scanner_constraints = self.scannerlogic().scanner_constraints
        axes = key.split(',')
        if len(axes) == 1:
            dockwidget = Scan1dDockWidget(key)
            dockwidget.setAllowedAreas(QtCore.Qt.TopDockWidgetArea)
            self.scan_1d_dockwidgets[key] = dockwidget
            self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, dockwidget)
            # Set axis labels
            dockwidget.plot_widget.setLabel('bottom', key, units=scanner_constraints[key]['unit'])
            dockwidget.plot_widget.setLabel('left', 'scan data', units='arb.u.')
        else:
            dockwidget = Scan2dDockWidget(axes)
            dockwidget.setAllowedAreas(QtCore.Qt.TopDockWidgetArea)
            self.scan_2d_dockwidgets[key] = dockwidget
            self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, dockwidget)
            # Set axis labels
            dockwidget.plot_widget.setLabel(
                'bottom', axes[0], units=scanner_constraints[axes[0]]['unit'])
            dockwidget.plot_widget.setLabel(
                'left', axes[1], units=scanner_constraints[axes[1]]['unit'])
            dockwidget.plot_widget.toggle_crosshair(True, movable=True)
            dockwidget.plot_widget.set_crosshair_min_size_factor(0.02)
            dockwidget.plot_widget.setAspectLocked(lock=True, ratio=1.0)
            dockwidget.plot_widget.toggle_zoom_by_selection(True)
        return

    @QtCore.Slot()
    @QtCore.Slot(dict)
    def scanner_settings_updated(self, settings=None):
        """
        Update scanner settings from logic and set widgets accordingly.

        @param dict settings: Settings dict containing the scanner settings to update.
                              If None (default) read the scanner setting from logic and update.
        """
        if not isinstance(settings, dict):
            settings = self.scannerlogic().scanner_settings

        if 'pixel_clock_frequency' in settings:
            self._ssd.pixel_clock_frequency_scienSpinBox.setValue(settings['pixel_clock_frequency'])
        if 'backscan_speed' in settings:
            self._ssd.backscan_speed_scienSpinBox.setValue(settings['backscan_speed'])
        if 'scan_resolution' in settings:
            for axis, resolution in settings['scan_resolution'].items():
                res_spinbox = self.axes_control_widgets[axis]['res_spinbox']
                res_spinbox.blockSignals(True)
                res_spinbox.setValue(resolution)
                res_spinbox.blockSignals(False)
        if 'scan_range' in settings:
            for axis, axis_range in settings['scan_range'].items():
                min_spinbox = self.axes_control_widgets[axis]['min_spinbox']
                max_spinbox = self.axes_control_widgets[axis]['max_spinbox']
                min_spinbox.blockSignals(True)
                max_spinbox.blockSignals(True)
                min_spinbox.setValue(axis_range[0])
                max_spinbox.setValue(axis_range[1])
                min_spinbox.blockSignals(False)
                max_spinbox.blockSignals(False)
        if 'scan_axes' in settings:
            present_keys = set(self.scan_1d_dockwidgets)
            present_keys.update(set(self.scan_2d_dockwidgets))
            new_keys = [','.join(axes) for axes in settings['scan_axes']]

            # Remove obsolete scan dockwidgets and images items
            keys_to_delete = present_keys.difference(new_keys)
            for key in keys_to_delete:
                self._remove_scan_dockwidget(key)

            # Add new dockwidgets and image items, do not use set to keep ordering
            keys_to_add = [key for key in new_keys if key not in present_keys]
            for key in keys_to_add:
                self._add_scan_dockwidget(key)
        return

    @QtCore.Slot()
    @QtCore.Slot(dict)
    def scanner_position_updated(self, position=None):
        """
        Updates the scanner position and set widgets accordingly.

        @param dict position: The scanner position dict to update each axis position.
                              If None (default) read the scanner position from logic and update.
        """
        if not isinstance(position, dict):
            position = self.scannerlogic().scanner_position

        for axis, pos in position.items():
            slider = self.axes_control_widgets[axis]['slider']
            spinbox = self.axes_control_widgets[axis]['pos_spinbox']
            slider.blockSignals(True)
            spinbox.blockSignals(True)
            slider.setValue(pos)
            spinbox.setValue(pos)
            slider.blockSignals(False)
            spinbox.blockSignals(False)
        return

    @QtCore.Slot()
    @QtCore.Slot(list)
    @QtCore.Slot(tuple)
    def scan_data_updated(self, scan_data=None):
        """

        @param dict scan_data:
        """
        if not isinstance(scan_data, (list, tuple)):
            scan_data = self.scannerlogic().scan_data
        else:
            scan_data = list(scan_data)

        for data in scan_data:
            axes = data['axes']['names']
            if len(axes) == 2:
                if 'scan' in data:
                    key = '{0},{1}'.format(*axes)
                    self.scan_2d_dockwidgets[key].image_item.setImage(image=data['scan'])
                self.scan_2d_dockwidgets[key].image_item.set_image_extent(data['axes']['extent'])
                self.scan_2d_dockwidgets[key].colorbar.set_label(text='scan data',
                                                                 unit=data['unit'])
            elif len(axes) == 1:
                if 'scan' in data:
                    self.scan_1d_dockwidgets[axes[0]].plot_item.setData(data['scan'])
                self.scan_1d_dockwidgets[axes[0]].plot_widget.setLabel(
                    'left', 'scan data', units=data['unit'])
        return

    def move_scanner_by_keyboard_event(self, event):
        """
        Handles the passed keyboard events from the main window.

        @param object event: qtpy.QtCore.QEvent object.
        """
        pass
        # modifiers = QtWidgets.QApplication.keyboardModifiers()
        # key = event.key()
        #
        # position = self._scanning_logic.get_position()   # in meters
        # x_pos = position[0]
        # y_pos = position[1]
        # z_pos = position[2]
        #
        # if modifiers == QtCore.Qt.ControlModifier:
        #     if key == QtCore.Qt.Key_Right:
        #         self.update_from_key(x=float(round(x_pos + self.slider_big_step, 10)))
        #     elif key == QtCore.Qt.Key_Left:
        #         self.update_from_key(x=float(round(x_pos - self.slider_big_step, 10)))
        #     elif key == QtCore.Qt.Key_Up:
        #         self.update_from_key(y=float(round(y_pos + self.slider_big_step, 10)))
        #     elif key == QtCore.Qt.Key_Down:
        #         self.update_from_key(y=float(round(y_pos - self.slider_big_step, 10)))
        #     elif key == QtCore.Qt.Key_PageUp:
        #         self.update_from_key(z=float(round(z_pos + self.slider_big_step, 10)))
        #     elif key == QtCore.Qt.Key_PageDown:
        #         self.update_from_key(z=float(round(z_pos - self.slider_big_step, 10)))
        #     else:
        #         event.ignore()
        # else:
        #     if key == QtCore.Qt.Key_Right:
        #         self.update_from_key(x=float(round(x_pos + self.slider_small_step, 10)))
        #     elif key == QtCore.Qt.Key_Left:
        #         self.update_from_key(x=float(round(x_pos - self.slider_small_step, 10)))
        #     elif key == QtCore.Qt.Key_Up:
        #         self.update_from_key(y=float(round(y_pos + self.slider_small_step, 10)))
        #     elif key == QtCore.Qt.Key_Down:
        #         self.update_from_key(y=float(round(y_pos - self.slider_small_step, 10)))
        #     elif key == QtCore.Qt.Key_PageUp:
        #         self.update_from_key(z=float(round(z_pos + self.slider_small_step, 10)))
        #     elif key == QtCore.Qt.Key_PageDown:
        #         self.update_from_key(z=float(round(z_pos - self.slider_small_step, 10)))
        #     else:
        #         event.ignore()
