# -*- coding: utf-8 -*-
"""
This module contains a GUI through which the POI Manager class can be controlled.

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
import re

from core.connector import Connector
from core.util.units import ScaledFloat
from core.util.helpers import natural_sort
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from gui.colordefs import ColorScaleInferno
from gui.colordefs import QudiPalettePale as palette
from qtpy import QtCore, QtGui
from qtpy import QtWidgets
from qtpy import uic
from qtwidgets.scan_plotwidget import ScanImageItem


class PoiMarker(pg.EllipseROI):
    """
    Creates a circle as a marker.

    @param float[2] pos: The (x, y) position of the POI.
    @param **args: All extra keyword arguments are passed to ROI()

    Have a look at:
    http://www.pyqtgraph.org/documentation/graphicsItems/roi.html
    """
    default_pen = {'color': 'F0F', 'width': 2}
    select_pen = {'color': 'FFF', 'width': 2}

    sigPoiSelected = QtCore.Signal(str)

    def __init__(self, position, radius, poi_name=None, view_widget=None, **kwargs):
        """

        @param position:
        @param radius:
        @param poi_name:
        @param view_widget:
        @param kwargs:
        """
        self._poi_name = '' if poi_name is None else poi_name
        self._view_widget = view_widget
        self._selected = False
        self._position = np.array(position, dtype=float)

        size = (2 * radius, 2 * radius)
        super().__init__(pos=self._position, size=size, pen=self.default_pen, **kwargs)
        # self.aspectLocked = True
        self.label = pg.TextItem(text=self._poi_name,
                                 anchor=(0, 1),
                                 color=self.default_pen['color'])
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.sigClicked.connect(self._notify_clicked_poi_name)
        self.set_position(self._position)
        return

    def _addHandles(self):
        pass

    @property
    def radius(self):
        return self.size()[0] / 2

    @property
    def selected(self):
        return bool(self._selected)

    @property
    def poi_name(self):
        return str(self._poi_name)

    @property
    def position(self):
        return self._position

    @QtCore.Slot()
    def _notify_clicked_poi_name(self):
        self.sigPoiSelected.emit(self._poi_name)

    def add_to_view_widget(self, view_widget=None):
        if view_widget is not None:
            self._view_widget = view_widget
        self._view_widget.addItem(self)
        self._view_widget.addItem(self.label)
        return

    def delete_from_view_widget(self, view_widget=None):
        if view_widget is not None:
            self._view_widget = view_widget
        self._view_widget.removeItem(self.label)
        self._view_widget.removeItem(self)
        return

    def set_position(self, position):
        """
        Sets the POI position and center the marker circle on that position.
        Also position the label accordingly.

        @param float[2] position: The (x,y) center position of the POI marker
        """
        self._position = np.array(position, dtype=float)
        radius = self.radius
        label_offset = radius / np.sqrt(2)
        self.setPos(self._position[0] - radius, self._position[1] - radius)
        self.label.setPos(self._position[0] + label_offset, self._position[1] + label_offset)
        return

    def set_name(self, name):
        """
        Set the poi_name of the marker and update tha label accordingly.

        @param str name:
        """
        self._poi_name = name
        self.label.setText(self._poi_name)
        return

    def set_radius(self, radius):
        """
        Set the size of the marker and reposition itself and the label to center it again.

        @param float radius: The radius of the circle
        """
        label_offset = radius / np.sqrt(2)
        self.setSize((2 * radius, 2 * radius))
        self.setPos(self.position[0] - radius, self.position[1] - radius)
        self.label.setPos(self.position[0] + label_offset, self.position[1] + label_offset)
        return

    def select(self):
        """
        Set the markers _selected flag to True and change the marker appearance according to
        PoiMarker.select_pen.
        """
        self._selected = True
        self.setPen(self.select_pen)
        self.label.setColor(self.select_pen['color'])
        return

    def deselect(self):
        """
        Set the markers _selected flag to False and change the marker appearance according to
        PoiMarker.default_pen.
        """
        self._selected = False
        self.setPen(self.default_pen)
        self.label.setColor(self.default_pen['color'])
        return


class NameValidator(QtGui.QValidator):
    """
    This is a validator for strings that should be compatible with filenames and likes.
    So no special characters (except '_') and blanks are allowed.
    """

    name_re = re.compile(r'([\w]+)')

    def __init__(self, *args, empty_allowed=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._empty_allowed = bool(empty_allowed)

    def validate(self, string, position):
        """
        This is the actual validator. It checks whether the current user input is a valid string
        every time the user types a character. There are 3 states that are possible.
        1) Invalid: The current input string is invalid. The user input will not accept the last
                    typed character.
        2) Acceptable: The user input in conform with the regular expression and will be accepted.
        3) Intermediate: The user input is not a valid string yet but on the right track. Use this
                         return value to allow the user to type fill-characters needed in order to
                         complete an expression.
        @param string: The current input string (from a QLineEdit for example)
        @param position: The current position of the text cursor
        @return: enum QValidator::State: the returned validator state,
                 str: the input string, int: the cursor position
        """
        # Return intermediate status when empty string is passed
        if not string:
            if self._empty_allowed:
                return self.Acceptable, '', position
            else:
                return self.Intermediate, string, position

        match = self.name_re.match(string)
        if not match:
            return self.Invalid, '', position

        matched = match.group()
        if matched == string:
            return self.Acceptable, string, position

        return self.Invalid, matched, position

    def fixup(self, text):
        match = self.name_re.search(text)
        if match:
            return match.group()
        return ''


class PoiManagerMainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_poimangui.ui')

        # Load it
        super(PoiManagerMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()


class PoiManagerGui(GUIBase):
    """ This is the GUI Class for PoiManager """

    # declare connectors
    poimanagerlogic = Connector(interface='PoiManagerLogic')
    scannerlogic = Connector(interface='ConfocalLogic')

    # declare signals
    sigTrackPeriodChanged = QtCore.Signal(float)
    sigPoiThresholdChanged = QtCore.Signal(float)
    sigPoiDiameterChanged = QtCore.Signal(float)
    sigPoiNameChanged = QtCore.Signal(str)
    sigPoiNameTagChanged = QtCore.Signal(str)
    sigRoiNameChanged = QtCore.Signal(str)
    sigAddPoiByClick = QtCore.Signal(np.ndarray)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self._mw = None             # QMainWindow handle
        self.roi_image = None       # pyqtgraph PlotImage for ROI scan image
        self.roi_cb = None          # The qudi colorbar to use with roi_image
        self.x_shift_plot = None    # pyqtgraph PlotDataItem for ROI history plot
        self.y_shift_plot = None    # pyqtgraph PlotDataItem for ROI history plot
        self.z_shift_plot = None    # pyqtgraph PlotDataItem for ROI history plot

        self._markers = dict()      # dict to hold handles for the POI markers

        self._mouse_moved_proxy = None  # Signal proxy to limit mousMoved event rate

        self.__poi_selector_active = False  # Flag indicating if the poi selector is active
        return

    def on_activate(self):
        """
        Initializes the overall GUI, and establishes the connectors.

        This method executes the init methods for each of the GUIs.
        """
        self._markers = dict()

        self._mw = PoiManagerMainWindow()
        # Configuring the dock widgets.
        self.restore_dockwidgets_default()

        # Add validator to LineEdits
        self._mw.roi_name_LineEdit.setValidator(NameValidator())
        self._mw.poi_name_LineEdit.setValidator(NameValidator())
        self._mw.poi_nametag_LineEdit.setValidator(NameValidator(empty_allowed=True))

        # Initialize plots
        self.__init_roi_scan_image()
        self.__init_roi_history_plot()

        # Initialize refocus timer
        self.update_refocus_timer(self.poimanagerlogic().module_state() == 'locked',
                                  self.poimanagerlogic().refocus_period,
                                  self.poimanagerlogic().refocus_period)
        # Initialize POIs
        self._update_pois(self.poimanagerlogic().poi_positions)
        # Initialize ROI name
        self._update_roi_name(self.poimanagerlogic().roi_name)
        # Initialize POI nametag
        self._update_poi_nametag(self.poimanagerlogic().poi_nametag)
        # Initialize Auto POI threshold
        self._update_poi_threshold(self.poimanagerlogic().poi_threshold)
        # Initialize Auto POI diameter
        self._update_poi_diameter(self.poimanagerlogic().poi_diameter)
        # Distance Measurement:
        # Introducing a SignalProxy will limit the rate of signals that get fired.
        self._mouse_moved_proxy = pg.SignalProxy(signal=self.roi_image.scene().sigMouseMoved,
                                                 rateLimit=30,
                                                 slot=self.mouse_moved_callback)

        # Connect signals
        self.__connect_internal_signals()
        self.__connect_update_signals_from_logic()
        self.__connect_control_signals_to_logic()

        self._mw.show()
        return

    def on_deactivate(self):
        """
        De-initialisation performed during deactivation of the module.
        """
        self.toggle_poi_selector(False)
        self.__disconnect_control_signals_to_logic()
        self.__disconnect_update_signals_from_logic()
        self.__disconnect_internal_signals()
        self._mw.close()

    @QtCore.Slot()
    def restore_dockwidgets_default(self):
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)

        self._mw.roi_map_dockWidget.setFloating(False)
        self._mw.auto_pois_dockWidget.setFloating(False)
        self._mw.poi_editor_dockWidget.setFloating(False)
        self._mw.poi_tracker_dockWidget.setFloating(False)
        self._mw.sample_shift_dockWidget.setFloating(False)

        self._mw.roi_map_dockWidget.show()
        self._mw.auto_pois_dockWidget.show()
        self._mw.poi_editor_dockWidget.show()
        self._mw.poi_tracker_dockWidget.show()
        self._mw.sample_shift_dockWidget.show()

        self._mw.addDockWidget(QtCore.Qt.TopDockWidgetArea, self._mw.roi_map_dockWidget)
        self._mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self._mw.poi_editor_dockWidget)
        self._mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self._mw.poi_tracker_dockWidget)
        self._mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self._mw.auto_pois_dockWidget)
        self._mw.splitDockWidget(
            self._mw.poi_tracker_dockWidget, self._mw.auto_pois_dockWidget, QtCore.Qt.Vertical)
        self._mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self._mw.sample_shift_dockWidget)

        if not self._mw.roi_map_view_Action.isChecked():
            self._mw.roi_map_view_Action.trigger()
        if not self._mw.poi_editor_view_Action.isChecked():
            self._mw.poi_editor_view_Action.trigger()
        if not self._mw.poi_tracker_view_Action.isChecked():
            self._mw.poi_tracker_view_Action.trigger()
        if not self._mw.auto_pois_view_Action.isChecked():
            self._mw.auto_pois_view_Action.trigger()
        if not self._mw.sample_shift_view_Action.isChecked():
            self._mw.sample_shift_view_Action.trigger()
        return

    def __init_roi_scan_image(self):
        # Get the color scheme
        my_colors = ColorScaleInferno()
        # Setting up display of ROI xy scan image
        self.roi_image = ScanImageItem(axisOrder='row-major', lut=my_colors.lut)
        self._mw.roi_map_ViewWidget.addItem(self.roi_image)
        self._mw.roi_map_ViewWidget.setLabel('bottom', 'X position', units='m')
        self._mw.roi_map_ViewWidget.setLabel('left', 'Y position', units='m')
        self._mw.roi_map_ViewWidget.setAspectLocked(lock=True, ratio=1.0)
        # Set up color bar
        self.roi_cb = ColorBar(my_colors.cmap_normed, 100, 0, 100000)
        self._mw.roi_cb_ViewWidget.addItem(self.roi_cb)
        self._mw.roi_cb_ViewWidget.hideAxis('bottom')
        self._mw.roi_cb_ViewWidget.setLabel('left', 'Fluorescence', units='c/s')
        self._mw.roi_cb_ViewWidget.setMouseEnabled(x=False, y=False)

        # Get scan image from logic and update initialize plot
        self._update_scan_image(self.poimanagerlogic().roi_scan_image,
                                self.poimanagerlogic().roi_scan_image_extent)
        return

    def __init_roi_history_plot(self):
        # Setting up display of sample shift plot
        self.x_shift_plot = pg.PlotDataItem(x=[0],
                                            y=[0],
                                            pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                                            symbol='o',
                                            symbolPen=palette.c1,
                                            symbolBrush=palette.c1,
                                            symbolSize=5,
                                            name='x')
        self.y_shift_plot = pg.PlotDataItem(x=[0],
                                            y=[0],
                                            pen=pg.mkPen(palette.c2, style=QtCore.Qt.DotLine),
                                            symbol='s',
                                            symbolPen=palette.c2,
                                            symbolBrush=palette.c2,
                                            symbolSize=5,
                                            name='y')
        self.z_shift_plot = pg.PlotDataItem(x=[0],
                                            y=[0],
                                            pen=pg.mkPen(palette.c3, style=QtCore.Qt.DotLine),
                                            symbol='t',
                                            symbolPen=palette.c3,
                                            symbolBrush=palette.c3,
                                            symbolSize=5,
                                            name='z')

        self._mw.sample_shift_ViewWidget.addLegend()

        # Add the plot to the ViewWidget defined in the UI file
        self._mw.sample_shift_ViewWidget.addItem(self.x_shift_plot)
        self._mw.sample_shift_ViewWidget.addItem(self.y_shift_plot)
        self._mw.sample_shift_ViewWidget.addItem(self.z_shift_plot)

        # Label axes
        self._mw.sample_shift_ViewWidget.setLabel('bottom', 'Time', units='s')
        self._mw.sample_shift_ViewWidget.setLabel('left', 'Sample shift', units='m')

        self._update_roi_history(self.poimanagerlogic().roi_pos_history)
        return

    def __connect_update_signals_from_logic(self):
        self.poimanagerlogic().sigRefocusTimerUpdated.connect(
            self.update_refocus_timer, QtCore.Qt.QueuedConnection)
        self.poimanagerlogic().sigPoiUpdated.connect(
            self.update_poi, QtCore.Qt.QueuedConnection)
        self.poimanagerlogic().sigActivePoiUpdated.connect(
            self.update_active_poi, QtCore.Qt.QueuedConnection)
        self.poimanagerlogic().sigRoiUpdated.connect(self.update_roi, QtCore.Qt.QueuedConnection)
        self.poimanagerlogic().sigRefocusStateUpdated.connect(
            self.update_refocus_state, QtCore.Qt.QueuedConnection)
        self.poimanagerlogic().sigThresholdUpdated.connect(
            self._update_poi_threshold, QtCore.Qt.QueuedConnection)
        self.poimanagerlogic().sigDiameterUpdated.connect(
            self._update_poi_diameter, QtCore.Qt.QueuedConnection)
        return

    def __disconnect_update_signals_from_logic(self):
        self.poimanagerlogic().sigRefocusTimerUpdated.disconnect()
        self.poimanagerlogic().sigPoiUpdated.disconnect()
        self.poimanagerlogic().sigActivePoiUpdated.disconnect()
        self.poimanagerlogic().sigRoiUpdated.disconnect()
        self.poimanagerlogic().sigRefocusStateUpdated.disconnect()
        return

    def __connect_control_signals_to_logic(self):
        self._mw.new_poi_Action.triggered.connect(
            self.poimanagerlogic().add_poi, QtCore.Qt.QueuedConnection)
        self._mw.auto_pois_PushButton.clicked.connect(
            self.poimanagerlogic().auto_catch_poi, QtCore.Qt.QueuedConnection)
        self._mw.del_all_pois_PushButton.clicked.connect(
            self.delete_all_pois_clicked, QtCore.Qt.QueuedConnection)
        self._mw.goto_poi_Action.triggered.connect(
            self.poimanagerlogic().go_to_poi, QtCore.Qt.QueuedConnection)
        self._mw.new_roi_Action.triggered.connect(
            self.poimanagerlogic().reset_roi, QtCore.Qt.QueuedConnection)
        self._mw.refind_poi_Action.triggered.connect(
            self.poimanagerlogic().optimise_poi_position, QtCore.Qt.QueuedConnection)
        self._mw.get_confocal_image_PushButton.clicked.connect(
            self.poimanagerlogic().set_scan_image, QtCore.Qt.QueuedConnection)
        self._mw.set_poi_PushButton.clicked.connect(
            self.poimanagerlogic().add_poi, QtCore.Qt.QueuedConnection)
        self._mw.delete_last_pos_Button.clicked.connect(
            self.poimanagerlogic().delete_history_entry, QtCore.Qt.QueuedConnection)
        self._mw.manual_update_poi_PushButton.clicked.connect(
            self.poimanagerlogic().move_roi_from_poi_position, QtCore.Qt.QueuedConnection)
        self._mw.move_poi_PushButton.clicked.connect(
            self.poimanagerlogic().set_poi_anchor_from_position, QtCore.Qt.QueuedConnection)
        self._mw.delete_poi_PushButton.clicked.connect(
            self.poimanagerlogic().delete_poi, QtCore.Qt.QueuedConnection)
        self._mw.active_poi_ComboBox.activated[str].connect(
            self.poimanagerlogic().set_active_poi, QtCore.Qt.QueuedConnection)
        self._mw.goto_poi_after_update_checkBox.stateChanged.connect(
            self.poimanagerlogic().set_move_scanner_after_optimise, QtCore.Qt.QueuedConnection)
        self._mw.track_poi_Action.triggered.connect(
            self.poimanagerlogic().toggle_periodic_refocus, QtCore.Qt.QueuedConnection)
        self.sigTrackPeriodChanged.connect(
            self.poimanagerlogic().set_refocus_period, QtCore.Qt.QueuedConnection)
        self.sigPoiThresholdChanged.connect(
            self.poimanagerlogic().set_poi_threshold)
        self.sigPoiDiameterChanged.connect(
            self.poimanagerlogic().set_poi_diameter)
        self.sigRoiNameChanged.connect(
            self.poimanagerlogic().rename_roi, QtCore.Qt.QueuedConnection)
        self.sigPoiNameChanged.connect(
            self.poimanagerlogic().rename_poi, QtCore.Qt.QueuedConnection)
        self.sigPoiNameTagChanged.connect(
            self.poimanagerlogic().set_poi_nametag, QtCore.Qt.QueuedConnection)
        self.sigAddPoiByClick.connect(self.poimanagerlogic().add_poi, QtCore.Qt.QueuedConnection)
        return

    def __disconnect_control_signals_to_logic(self):
        self._mw.new_poi_Action.triggered.disconnect()
        self._mw.goto_poi_Action.triggered.disconnect()
        self._mw.new_roi_Action.triggered.disconnect()
        self._mw.refind_poi_Action.triggered.disconnect()
        self._mw.get_confocal_image_PushButton.clicked.disconnect()
        self._mw.set_poi_PushButton.clicked.disconnect()
        self._mw.delete_last_pos_Button.clicked.disconnect()
        self._mw.manual_update_poi_PushButton.clicked.disconnect()
        self._mw.move_poi_PushButton.clicked.disconnect()
        self._mw.delete_poi_PushButton.clicked.disconnect()
        self._mw.active_poi_ComboBox.activated[str].disconnect()
        self._mw.goto_poi_after_update_checkBox.stateChanged.disconnect()
        self._mw.track_poi_Action.triggered.disconnect()
        self.sigTrackPeriodChanged.disconnect()
        self.sigPoiThresholdChanged.disconnect()
        self.sigPoiDiameterChanged.disconnect()
        self.sigRoiNameChanged.disconnect()
        self.sigPoiNameChanged.disconnect()
        self.sigPoiNameTagChanged.disconnect()
        self.sigAddPoiByClick.disconnect()
        for marker in self._markers.values():
            marker.sigPoiSelected.disconnect()
        return

    def __connect_internal_signals(self):
        self._mw.track_period_SpinBox.editingFinished.connect(self.track_period_changed)
        self._mw.poi_threshold_doubleSpinBox.editingFinished.connect(self.poi_threshold_changed)
        self._mw.poi_diameter_doubleSpinBox.editingFinished.connect(self.poi_diameter_changed)
        self._mw.roi_name_LineEdit.editingFinished.connect(self.roi_name_changed)
        self._mw.poi_name_LineEdit.returnPressed.connect(self.poi_name_changed)
        self._mw.poi_nametag_LineEdit.editingFinished.connect(self.poi_nametag_changed)
        self._mw.save_roi_Action.triggered.connect(self.save_roi)
        self._mw.load_roi_Action.triggered.connect(self.load_roi)
        self._mw.blink_correction_view_Action.triggered.connect(self.toggle_blink_correction)
        self._mw.poi_selector_Action.toggled.connect(self.toggle_poi_selector)
        self._mw.roi_cb_centiles_RadioButton.toggled.connect(self.update_cb)
        self._mw.roi_cb_manual_RadioButton.toggled.connect(self.update_cb)
        self._mw.roi_cb_min_SpinBox.valueChanged.connect(self.update_cb_absolute)
        self._mw.roi_cb_max_SpinBox.valueChanged.connect(self.update_cb_absolute)
        self._mw.roi_cb_low_percentile_DoubleSpinBox.valueChanged.connect(self.update_cb_centiles)
        self._mw.roi_cb_high_percentile_DoubleSpinBox.valueChanged.connect(self.update_cb_centiles)
        self._mw.restore_default_view_Action.triggered.connect(self.restore_dockwidgets_default)
        return

    def __disconnect_internal_signals(self):
        self._mw.track_period_SpinBox.editingFinished.disconnect()
        self._mw.roi_name_LineEdit.editingFinished.disconnect()
        self._mw.poi_name_LineEdit.returnPressed.disconnect()
        self._mw.poi_nametag_LineEdit.editingFinished.disconnect()
        self._mw.save_roi_Action.triggered.disconnect()
        self._mw.load_roi_Action.triggered.disconnect()
        self._mw.blink_correction_view_Action.triggered.disconnect()
        self._mw.poi_selector_Action.toggled.disconnect()
        self._mw.roi_cb_centiles_RadioButton.toggled.disconnect()
        self._mw.roi_cb_manual_RadioButton.toggled.disconnect()
        self._mw.roi_cb_min_SpinBox.valueChanged.disconnect()
        self._mw.roi_cb_max_SpinBox.valueChanged.disconnect()
        self._mw.roi_cb_low_percentile_DoubleSpinBox.valueChanged.disconnect()
        self._mw.roi_cb_high_percentile_DoubleSpinBox.valueChanged.disconnect()
        self._mw.restore_default_view_Action.triggered.disconnect()
        return

    def show(self):
        """Make main window visible and put it above all other windows. """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    @QtCore.Slot(bool)
    def toggle_blink_correction(self, is_active):
        self.roi_image.activate_blink_correction(is_active)
        return

    @QtCore.Slot(object)
    def mouse_moved_callback(self, event):
        """ Handles any mouse movements inside the image.

        @param event:   Event that signals the new mouse movement.
                        This should be of type QPointF.

        Gets the mouse position, converts it to a position scaled to the image axis
        and than calculates and updated the position to the current POI.
        """

        # converts the absolute mouse position to a position relative to the axis
        mouse_pos = self.roi_image.getViewBox().mapSceneToView(event[0])

        # only calculate distance, if a POI is selected
        active_poi = self.poimanagerlogic().active_poi
        if active_poi:
            poi_pos = self.poimanagerlogic().get_poi_position(active_poi)
            dx = ScaledFloat(mouse_pos.x() - poi_pos[0])
            dy = ScaledFloat(mouse_pos.y() - poi_pos[1])
            d_total = ScaledFloat(
                np.sqrt((mouse_pos.x() - poi_pos[0])**2 + (mouse_pos.y() - poi_pos[1])**2))

            self._mw.poi_distance_label.setText(
                '{0:.2r}m ({1:.2r}m, {2:.2r}m)'.format(d_total, dx, dy))
        else:
            self._mw.poi_distance_label.setText('? (?, ?)')
        pass

    @QtCore.Slot(bool)
    def toggle_poi_selector(self, is_active):
        if is_active != self._mw.poi_selector_Action.isChecked():
            self._mw.poi_selector_Action.blockSignals(True)
            self._mw.poi_selector_Action.setChecked(is_active)
            self._mw.poi_selector_Action.blockSignals(False)
        if is_active != self.__poi_selector_active:
            if is_active:
                self.roi_image.sigMouseClicked.connect(self.create_poi_from_click)
                self.roi_image.setCursor(QtCore.Qt.CrossCursor)
            else:
                self.roi_image.sigMouseClicked.disconnect()
                self.roi_image.setCursor(QtCore.Qt.ArrowCursor)
        self.__poi_selector_active = is_active
        return

    @QtCore.Slot(object, QtCore.QPointF)
    def create_poi_from_click(self, button, pos):
        # Only create new POI if the mouse click event has not been accepted by some other means
        # In our case this is most likely the POI marker to select the active POI from.
        if button != QtCore.Qt.LeftButton:
            return
        # Z position from ROI origin, X and Y positions from click event
        new_pos = self.poimanagerlogic().roi_origin
        new_pos[0] = pos.x()
        new_pos[1] = pos.y()
        self.sigAddPoiByClick.emit(new_pos)
        return

    @QtCore.Slot(dict)
    def update_roi(self, roi_dict):
        if not isinstance(roi_dict, dict):
            self.log.error('ROI parameters to update must be given in a single dictionary.')
            return

        if 'name' in roi_dict:
            self._update_roi_name(name=roi_dict['name'])
        if 'poi_nametag' in roi_dict:
            self._update_poi_nametag(tag=roi_dict['poi_nametag'])
        if 'history' in roi_dict:
            self._update_roi_history(history=roi_dict['history'])
        if 'scan_image' in roi_dict and 'scan_image_extent' in roi_dict:
            self._update_scan_image(scan_image=roi_dict['scan_image'],
                                    image_extent=roi_dict['scan_image_extent'])
        if 'pois' in roi_dict:
            self._update_pois(poi_dict=roi_dict['pois'])
        return

    @QtCore.Slot(bool, float, float)
    def update_refocus_timer(self, is_active, period, time_until_refocus):
        if not self._mw.track_period_SpinBox.hasFocus():
            self._mw.track_period_SpinBox.blockSignals(True)
            self._mw.track_period_SpinBox.setValue(period)
            self._mw.track_period_SpinBox.blockSignals(False)

        self._mw.track_poi_Action.blockSignals(True)
        self._mw.time_till_next_update_ProgressBar.blockSignals(True)

        self._mw.track_poi_Action.setChecked(is_active)
        self._mw.time_till_next_update_ProgressBar.setMaximum(period)
        self._mw.time_till_next_update_ProgressBar.setValue(time_until_refocus)

        self._mw.time_till_next_update_ProgressBar.blockSignals(False)
        self._mw.track_poi_Action.blockSignals(False)
        return

    @QtCore.Slot(bool)
    def update_refocus_state(self, is_active):
        self._mw.refind_poi_Action.setEnabled(not is_active)
        return

    @QtCore.Slot(str, str, np.ndarray)
    def update_poi(self, old_name, new_name, position):
        # Handle changed names and deleted/added POIs
        if old_name != new_name:
            self._mw.active_poi_ComboBox.blockSignals(True)
            # Remember current text
            text_active_poi = self._mw.active_poi_ComboBox.currentText()
            # sort POI names and repopulate ComboBoxes
            self._mw.active_poi_ComboBox.clear()
            poi_names = natural_sort(self.poimanagerlogic().poi_names)
            self._mw.active_poi_ComboBox.addItems(poi_names)
            if text_active_poi == old_name:
                self._mw.active_poi_ComboBox.setCurrentText(new_name)
            else:
                self._mw.active_poi_ComboBox.setCurrentText(text_active_poi)
            self._mw.active_poi_ComboBox.blockSignals(False)

        # Delete/add/update POI marker to image
        if not old_name:
            # POI has been added
            self._add_poi_marker(name=new_name, position=position)
        elif not new_name:
            # POI has been deleted
            self._remove_poi_marker(name=old_name)
        else:
            # POI has been renamed and/or changed position
            size = self.poimanagerlogic().optimise_xy_size * np.sqrt(2)
            self._markers[old_name].set_name(new_name)
            self._markers[new_name] = self._markers.pop(old_name)
            self._markers[new_name].setSize((size, size))
            self._markers[new_name].set_position(position[:2])

        active_poi = self._mw.active_poi_ComboBox.currentText()
        if active_poi:
            self._markers[active_poi].select()
        return

    @QtCore.Slot(str)
    def update_active_poi(self, name):

        # Deselect current marker
        for marker in self._markers.values():
            if marker.selected:
                marker.deselect()
                break

        # Unselect POI if name is None or empty str
        self._mw.active_poi_ComboBox.blockSignals(True)
        if not name:
            self._mw.active_poi_ComboBox.setCurrentIndex(-1)
        else:
            self._mw.active_poi_ComboBox.setCurrentText(name)
        self._mw.active_poi_ComboBox.blockSignals(False)

        if name:
            active_poi_pos = self.poimanagerlogic().get_poi_position(name)
        else:
            active_poi_pos = np.zeros(3)
        self._mw.poi_coords_label.setText(
            '({0:.2r}m, {1:.2r}m, {2:.2r}m)'.format(ScaledFloat(active_poi_pos[0]),
                                                    ScaledFloat(active_poi_pos[1]),
                                                    ScaledFloat(active_poi_pos[2])))

        if name in self._markers:
            self._markers[name].set_radius(self.poimanagerlogic().optimise_xy_size / np.sqrt(2))
            self._markers[name].select()
        return

    @QtCore.Slot()
    def track_period_changed(self):
        self.sigTrackPeriodChanged.emit(self._mw.track_period_SpinBox.value())
        return

    @QtCore.Slot()
    def poi_threshold_changed(self):
        self.sigPoiThresholdChanged.emit(self._mw.poi_threshold_doubleSpinBox.value())
        return

    @QtCore.Slot()
    def poi_diameter_changed(self):
        self.sigPoiDiameterChanged.emit(self._mw.poi_diameter_doubleSpinBox.value())
        return

    @QtCore.Slot()
    def roi_name_changed(self):
        """ Set the name of the current ROI."""
        self.sigRoiNameChanged.emit(self._mw.roi_name_LineEdit.text())
        return

    @QtCore.Slot()
    def poi_name_changed(self):
        """ Change the name of the active poi."""
        new_name = self._mw.poi_name_LineEdit.text()
        if self._mw.active_poi_ComboBox.currentText() == new_name or not new_name:
            return

        self.sigPoiNameChanged.emit(new_name)

        # After POI name is changed, empty name field
        self._mw.poi_name_LineEdit.blockSignals(True)
        self._mw.poi_name_LineEdit.setText('')
        self._mw.poi_name_LineEdit.blockSignals(False)
        return

    @QtCore.Slot()
    def poi_nametag_changed(self):
        self.sigPoiNameTagChanged.emit(self._mw.poi_nametag_LineEdit.text())
        return

    @QtCore.Slot()
    def save_roi(self):
        """ Save ROI to file."""
        roi_name = self._mw.roi_name_LineEdit.text()
        self.poimanagerlogic().rename_roi(roi_name)
        self.poimanagerlogic().save_roi()
        return

    @QtCore.Slot()
    def load_roi(self):
        """ Load a saved ROI from file."""
        this_file = QtWidgets.QFileDialog.getOpenFileName(self._mw,
                                                          'Open ROI',
                                                          self.poimanagerlogic().data_directory,
                                                          'Data files (*.dat)')[0]
        if this_file:
            self.poimanagerlogic().load_roi(complete_path=this_file)
        return

    @QtCore.Slot()
    def update_cb_centiles(self):
        if not self._mw.roi_cb_centiles_RadioButton.isChecked():
            self._mw.roi_cb_centiles_RadioButton.toggle()
        else:
            self.update_cb()
        return

    @QtCore.Slot()
    def update_cb_absolute(self):
        if not self._mw.roi_cb_manual_RadioButton.isChecked():
            self._mw.roi_cb_manual_RadioButton.toggle()
        else:
            self.update_cb()
        return

    @QtCore.Slot()
    def update_cb(self):
        image = self.poimanagerlogic().roi_scan_image
        if image is None:
            return
        cb_range = self.get_cb_range(image)
        self.roi_image.setLevels(cb_range)
        self.roi_cb.refresh_colorbar(*cb_range)
        return

    @QtCore.Slot()
    def delete_all_pois_clicked(self):
        result = QtWidgets.QMessageBox.question(self._mw, 'Qudi: Delete all POIs?',
                                                'Are you sure to delete all POIs?',
                                                QtWidgets.QMessageBox.Yes,
                                                QtWidgets.QMessageBox.No)
        if result == QtWidgets.QMessageBox.Yes:
            self.poimanagerlogic().delete_all_pois()
        return

    def _update_scan_image(self, scan_image, image_extent):
        """

        @param scan_image:
        @param image_extent:
        """
        if scan_image is None or image_extent is None:
            self._mw.roi_map_ViewWidget.removeItem(self.roi_image)
            return
        elif self.roi_image not in self._mw.roi_map_ViewWidget.items():
            self._mw.roi_map_ViewWidget.addItem(self.roi_image)
        self.roi_image.setImage(image=scan_image)
        (x_min, x_max), (y_min, y_max) = image_extent
        self.roi_image.getViewBox().enableAutoRange()
        self.roi_image.setRect(QtCore.QRectF(x_min, y_min, x_max - x_min, y_max - y_min))

        self.update_cb()
        return

    def _update_roi_name(self, name):
        self._mw.roi_name_LineEdit.blockSignals(True)
        self._mw.roi_name_LineEdit.setText(name)
        self._mw.roi_name_LineEdit.blockSignals(False)
        return

    def _update_poi_nametag(self, tag):
        if tag is None:
            tag = ''
        self._mw.poi_nametag_LineEdit.blockSignals(True)
        self._mw.poi_nametag_LineEdit.setText(tag)
        self._mw.poi_nametag_LineEdit.blockSignals(False)
        return

    def _update_poi_threshold(self, threshold):
        self._mw.poi_threshold_doubleSpinBox.setValue(threshold)
        return

    def _update_poi_diameter(self, diameter):
        self._mw.poi_diameter_doubleSpinBox.setValue(diameter)
        return

    def _update_roi_history(self, history=None):
        if history is None:
            history = self.poimanagerlogic().roi_pos_history

        if history.shape[1] != 4:
            self.log.error('ROI history must be an array of type float[][4].')
            return

        max_time = np.max(history[:, 0])
        if max_time < 300:
            self._mw.sample_shift_ViewWidget.setLabel('bottom', 'Time', units='s')
            time_arr = history[:, 0]
        elif max_time < 7200:
            self._mw.sample_shift_ViewWidget.setLabel('bottom', 'Time', units='min')
            time_arr = history[:, 0] / 60
        elif max_time < 172800:
            self._mw.sample_shift_ViewWidget.setLabel('bottom', 'Time', units='h')
            time_arr = history[:, 0] / 3600
        else:
            self._mw.sample_shift_ViewWidget.setLabel('bottom', 'Time', units='d')
            time_arr = history[:, 0] / 86400

        self.x_shift_plot.setData(time_arr, history[:, 1])
        self.y_shift_plot.setData(time_arr, history[:, 2])
        self.z_shift_plot.setData(time_arr, history[:, 3])
        return

    def _update_pois(self, poi_dict):
        """ Populate the dropdown box for selecting a poi. """
        self._mw.active_poi_ComboBox.blockSignals(True)

        self._mw.active_poi_ComboBox.clear()

        poi_names = natural_sort(poi_dict)
        self._mw.active_poi_ComboBox.addItems(poi_names)

        # Get two list of POI names. One of those to delete and one of those to add
        old_poi_names = set(self._markers)
        new_poi_names = set(poi_names)
        names_to_delete = list(old_poi_names.difference(new_poi_names))
        names_to_add = list(new_poi_names.difference(old_poi_names))

        # Delete markers accordingly
        for name in names_to_delete:
            self._remove_poi_marker(name)
        # Update positions of all remaining markers
        size = self.poimanagerlogic().optimise_xy_size * np.sqrt(2)
        for name, marker in self._markers.items():
            marker.setSize((size, size))
            marker.set_position(poi_dict[name])
        # Add new markers
        for name in names_to_add:
            self._add_poi_marker(name=name, position=poi_dict[name])

        # If there is no active POI, set the combobox to nothing (-1)
        active_poi = self.poimanagerlogic().active_poi
        if active_poi in poi_names:
            self._mw.active_poi_ComboBox.setCurrentText(active_poi)
            self._markers[active_poi].select()
            active_poi_pos = poi_dict[active_poi]
            self._mw.poi_coords_label.setText(
                '({0:.2r}m, {1:.2r}m, {2:.2r}m)'.format(ScaledFloat(active_poi_pos[0]),
                                                        ScaledFloat(active_poi_pos[1]),
                                                        ScaledFloat(active_poi_pos[2])))
        else:
            self._mw.active_poi_ComboBox.setCurrentIndex(-1)

        self._mw.active_poi_ComboBox.blockSignals(False)
        return

    def get_cb_range(self, image):
        """ Process UI input to determine color bar range"""
        # If "Centiles" is checked, adjust colour scaling automatically to centiles.
        # Otherwise, take user-defined values.
        if self._mw.roi_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.roi_cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.roi_cb_high_percentile_DoubleSpinBox.value()

            cb_min = np.percentile(image, low_centile)
            cb_max = np.percentile(image, high_centile)
        else:
            cb_min = self._mw.roi_cb_min_SpinBox.value()
            cb_max = self._mw.roi_cb_max_SpinBox.value()
        return cb_min, cb_max

    def _add_poi_marker(self, name, position):
        """ Add a circular POI marker to the ROI scan image. """
        if name:
            if name in self._markers:
                self.log.error('Unable to add POI marker to ROI image. POI marker already present.')
                return
            marker = PoiMarker(position=position[:2],
                               view_widget=self._mw.roi_map_ViewWidget,
                               poi_name=name,
                               radius=self.poimanagerlogic().optimise_xy_size / np.sqrt(2),
                               movable=False)
            # Add to the scan image widget
            marker.add_to_view_widget()
            marker.sigPoiSelected.connect(
                self.poimanagerlogic().set_active_poi, QtCore.Qt.QueuedConnection)
            self._markers[name] = marker
        return

    def _remove_poi_marker(self, name):
        """ Remove the POI marker for a POI that was deleted. """
        if name in self._markers:
            self._markers[name].delete_from_view_widget()
            self._markers[name].sigPoiSelected.disconnect()
            del self._markers[name]
        return
