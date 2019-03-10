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
import time

from core.module import Connector
from core.util.units import ScaledFloat
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from gui.colordefs import ColorScaleInferno
from gui.colordefs import QudiPalettePale as palette
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic

# Rather than import the ui*.py file here, the ui*.ui file itself is
# loaded by uic.loadUI in the QtGui classes below.


class PoiMark(pg.CircleROI):
    """
    Creates a circle as a marker.

    @param int[2] pos: (length-2 sequence) The position of the ROI’s origin.
    @param **args: All extra keyword arguments are passed to ROI()

    Have a look at:
    http://www.pyqtgraph.org/documentation/graphicsItems/roi.html
    """

    color = "F0F"
    selectcolor = "FFF"
    selected = False
    radius = 0.6e-6

    def __init__(self, pos, poi=None, click_action=None, viewwidget=None, **args):
        pg.CircleROI.__init__(
            self, pos, [2 * self.radius, 2 * self.radius], pen={'color': self.color, 'width': 2}, **args)

        self.poi = None
        self.viewwidget = None
        self.position = None
        self.label = None
        self.click_action = None

        if viewwidget is not None:
            self.viewwidget = viewwidget
        if poi is not None:
            self.poi = poi
        if pos is not None:
            self.position = pos  # This is the POI pos, so the centre of the marker circle.
        if click_action is not None:
            self.click_action = click_action
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.sigClicked.connect(self._activate_poi_from_marker)

    def add_to_viewwidget(self, viewwidget=None):
        if viewwidget is not None:
            self.viewwidget = viewwidget
        self.viewwidget.addItem(self)

        # Removing the handle from this CricleROI
        self.removeHandle(0)

        # create a new free handle for the name tag, positioned at "east" on the circle.
        self.my_handle = self.addRotateHandle([1, 0.5], [0.5, 0.5])
        self.sigRegionChangeFinished.connect(self._redraw_label)
        self.label = pg.TextItem(text=self.poi.get_name(),
                                 anchor=(0, 1),
                                 color=self.color)

        self.setAngle(30)
        self.setPos(self.position + self.get_marker_offset())
        # self.viewwidget.addItem(self.label)

    def _activate_poi_from_marker(self):
        self.click_action(self.poi.get_key())

    def _redraw_label(self):
        if self.label is not None:
            self.viewwidget.removeItem(self.label)

            cos_th = np.cos(self.angle() / 180. * np.pi)
            sin_th = np.sin(self.angle() / 180. * np.pi)

            text_pos = self.position\
                + [self.radius * cos_th, self.radius * sin_th]

            if cos_th > 0 and sin_th > 0:
                my_anchor = (0, 1)
            elif cos_th > 0 > sin_th:
                my_anchor = (0, 0)
            elif cos_th < 0 and sin_th < 0:
                my_anchor = (1, 0)
            else:
                my_anchor = (1, 1)

            # Updating the position of the circleROI origin in case it has been rotated.
            # It is important for finish=False so that this action does not call this
            # _redraw_label method recursively
            self.setPos(self.position + self.get_marker_offset(), finish=False)

            my_color = self.color
            if self.selected:
                my_color = self.selectcolor

            self.label = pg.TextItem(text=self.poi.get_name(),
                                     anchor=my_anchor,
                                     color=my_color
                                     )
            self.label.setPos(text_pos[0], text_pos[1])
            self.viewwidget.addItem(self.label)

    def get_marker_offset(self):

        # The origin of the circleROI is in the lower left corner, which is at -135 degrees
        # when the circleROI is in its initial unrotated state.
        origin_angle = self.angle() - 135

        # We wish to rotate the circleROI about its centre, and so from this angle
        # we calculate the necessary offset that will essentially rotate the circleROI origin
        # correspondingly.
        x_offset = np.sqrt(2.0) * self.radius * np.cos(origin_angle / 180. * np.pi)
        y_offset = np.sqrt(2.0) * self.radius * np.sin(origin_angle / 180. * np.pi)

        return [x_offset, y_offset]

    def delete_from_viewwidget(self, viewwidget=None):
        if viewwidget is not None:
            self.viewwidget = viewwidget
        self.viewwidget.removeItem(self.label)
        self.viewwidget.removeItem(self)

    def set_position(self, pos=None):
        if pos is not None:
            self.position = pos  # This is the POI pos, so the centre of the marker circle.

    def select(self):
        self.selected = True
        self.setPen({'color': self.selectcolor, 'width': 2})
        if self.label is not None:
            self._redraw_label()

    def deselect(self):
        self.selected = False
        self.setPen({'color': self.color, 'width': 2})
        if self.label is not None:
            self._redraw_label()


class CustomViewBox(pg.ViewBox):

    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        self.setMouseMode(self.RectMode)

    # reimplement right-click to zoom out
    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton:
            # self.autoRange()
            self.setXRange(0, 5)
            self.setYRange(0, 10)

    def mouseDragEvent(self, ev, axis=0):
        if (ev.button() == QtCore.Qt.LeftButton) and (ev.modifiers() & QtCore.Qt.ControlModifier):
            pg.ViewBox.mouseDragEvent(self, ev, axis)
        else:
            ev.ignore()


class PoiManagerMainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_poimangui.ui')

        # Load it
        super(PoiManagerMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()


class ReorientRoiDialog(QtWidgets.QDialog):

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_reorient_roi_dialog.ui')

        # Load it
        super(ReorientRoiDialog, self).__init__()
        uic.loadUi(ui_file, self)


class PoiManagerGui(GUIBase):

    """ This is the GUI Class for PoiManager """

    _modclass = 'PoiManagerGui'
    _modtype = 'gui'

    # declare connectors
    poimanagerlogic = Connector(interface='PoiManagerLogic')
    scannerlogic = Connector(interface='ConfocalLogic')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """
        Initializes the overall GUI, and establishes the connectors.

        This method executes the init methods for each of the GUIs.
        """
        # Initializing the GUIs
        self.initMainUI()
        # self.initReorientRoiDialogUI()

        # There could be POIs created in the logic already, so update lists and map
        # self.populate_poi_list()
        # self._redraw_sample_shift()
        # self._redraw_poi_markers()

    def on_deactivate(self):
        """
        De-initialisation performed during deactivation of the module.
        """
        self._mw.close()

    def initMainUI(self):
        """ Definition, configuration and initialisation of the POI Manager GUI.
        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """
        self._mw = PoiManagerMainWindow()

        # Configuring the dock widgets
        # All our gui elements are dockable, and so there should be no "central" widget.
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)

        # Setting up display of ROI map xy image
        self.roi_image = pg.ImageItem(image=np.zeros([2,2]), axisOrder='row-major')
        # Get the colorscales and set LUT
        my_colors = ColorScaleInferno()
        self.roi_image.setLookupTable(my_colors.lut)
        # Add color bar:
        self.roi_cb = ColorBar(my_colors.cmap_normed, 100, 0, 100000)
        self._mw.roi_cb_ViewWidget.addItem(self.roi_cb)
        self._mw.roi_cb_ViewWidget.hideAxis('bottom')
        self._mw.roi_cb_ViewWidget.setLabel('left', 'Fluorescence', units='c/s')
        self._mw.roi_cb_ViewWidget.setMouseEnabled(x=False, y=False)
        # Add the display item to the roi map ViewWidget defined in the UI file
        self._mw.roi_map_ViewWidget.addItem(self.roi_image)
        self._mw.roi_map_ViewWidget.setLabel('bottom', 'X position', units='m')
        self._mw.roi_map_ViewWidget.setLabel('left', 'Y position', units='m')
        # Set to fixed 1.0 aspect ratio, since the metaphor is a "map" of the sample
        self._mw.roi_map_ViewWidget.setAspectLocked(lock=True, ratio=1.0)
        # Get scan image from logic and update initialize plot
        if self.poimanagerlogic().roi_scan_image is None:
            self.poimanagerlogic().update_scan_image()
        self._update_scan_image()

        # Setting up display of sample shift plot
        self.x_shift_plot = pg.PlotDataItem(
            [0],
            [0],
            pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
            symbol='o',
            symbolPen=palette.c1,
            symbolBrush=palette.c1,
            symbolSize=5,
            name='x'
            )
        self.y_shift_plot = pg.PlotDataItem(
            [0],
            [0],
            pen=pg.mkPen(palette.c2, style=QtCore.Qt.DotLine),
            symbol='s',
            symbolPen=palette.c2,
            symbolBrush=palette.c2,
            symbolSize=5,
            name='y'
            )
        self.z_shift_plot = pg.PlotDataItem(
            [0],
            [0],
            pen=pg.mkPen(palette.c3, style=QtCore.Qt.DotLine),
            symbol='t',
            symbolPen=palette.c3,
            symbolBrush=palette.c3,
            symbolSize=5,
            name='z'
            )

        self._mw.sample_shift_ViewWidget.addLegend()

        # Add the plot to the ViewWidget defined in the UI file
        self._mw.sample_shift_ViewWidget.addItem(self.x_shift_plot)
        self._mw.sample_shift_ViewWidget.addItem(self.y_shift_plot)
        self._mw.sample_shift_ViewWidget.addItem(self.z_shift_plot)

        # Label axes
        self._mw.sample_shift_ViewWidget.setLabel('bottom', 'Time', units='s')
        self._mw.sample_shift_ViewWidget.setLabel('left', 'Sample shift', units='m')

        # Connect signals

        # Distance Measurement:
        # Introducing a SignalProxy will limit the rate of signals that get fired.
        # Otherwise we will run into a heap of unhandled function calls.
        proxy = pg.SignalProxy(
            self.roi_image.scene().sigMouseMoved,
            rateLimit=60,
            slot=self.mouseMoved)
        # Connecting a Mouse Signal to trace to mouse movement function.
        self.roi_image.scene().sigMouseMoved.connect(self.mouseMoved)

        # Toolbar actions
        self._mw.new_roi_Action.triggered.connect(self.make_new_roi)
        self._mw.save_roi_Action.triggered.connect(self.save_roi)
        self._mw.load_roi_Action.triggered.connect(self.load_roi)
        self._mw.reorient_roi_Action.triggered.connect(self.open_reorient_roi_dialog)
        self._mw.autofind_pois_Action.triggered.connect(self.autofind_pois)
        self._mw.optimize_roi_Action.triggered.connect(self.optimize_roi)

        self._mw.new_poi_Action.triggered.connect(
            self.poimanagerlogic().add_poi, QtCore.Qt.QueuedConnection)
        self._mw.goto_poi_Action.triggered.connect(
            self.poimanagerlogic().go_to_poi, QtCore.Qt.QueuedConnection)
        self._mw.refind_poi_Action.triggered.connect(self.update_poi_pos)
        self._mw.track_poi_Action.triggered.connect(self.toggle_tracking)

        # Interface controls
        self._mw.get_confocal_image_PushButton.clicked.connect(
            self.poimanagerlogic().update_scan_image, QtCore.Qt.QueuedConnection)
        self._mw.set_poi_PushButton.clicked.connect(
            self.poimanagerlogic().add_poi, QtCore.Qt.QueuedConnection)
        self._mw.delete_last_pos_Button.clicked.connect(
            self.poimanagerlogic().delete_history_entry, QtCore.Qt.QueuedConnection)
        self._mw.manual_update_poi_PushButton.clicked.connect(
            self.poimanagerlogic().set_poi_position, QtCore.Qt.QueuedConnection)
        self._mw.move_poi_PushButton.clicked.connect(self.move_poi)
        self._mw.poi_name_LineEdit.editingFinished.connect(self.change_poi_name)
        self._mw.roi_name_LineEdit.editingFinished.connect(self.set_roi_name)
        self._mw.delete_poi_PushButton.clicked.connect(
            self.poimanagerlogic().delete_poi, QtCore.Qt.QueuedConnection)
        self._mw.active_poi_ComboBox.currentTextChanged.connect(
            self.poimanagerlogic().set_active_poi, QtCore.Qt.QueuedConnection)

        # Connect the buttons and inputs for the colorbar
        self._mw.roi_cb_centiles_RadioButton.toggled.connect(self._update_scan_image)
        self._mw.roi_cb_manual_RadioButton.toggled.connect(self._update_scan_image)
        self._mw.roi_cb_min_SpinBox.valueChanged.connect(self.shortcut_to_roi_cb_manual)
        self._mw.roi_cb_max_SpinBox.valueChanged.connect(self.shortcut_to_roi_cb_manual)
        self._mw.roi_cb_low_percentile_DoubleSpinBox.valueChanged.connect(self.shortcut_to_roi_cb_centiles)
        self._mw.roi_cb_high_percentile_DoubleSpinBox.valueChanged.connect(self.shortcut_to_roi_cb_centiles)

        self._mw.display_shift_vs_duration_RadioButton.toggled.connect(self._redraw_sample_shift)
        self._mw.display_shift_vs_clocktime_RadioButton.toggled.connect(self._redraw_sample_shift)

        self._markers = dict()

        # Signal at end of refocus
        self.poimanagerlogic().sigRefocusTimerUpdated.connect(
            self._update_refocus_timer, QtCore.Qt.QueuedConnection)
        self.poimanagerlogic().sigPoisUpdated.connect(
            self._update_pois, QtCore.Qt.QueuedConnection)
        self.poimanagerlogic().sigScanImageUpdated.connect(
            self._update_scan_image, QtCore.Qt.QueuedConnection)
        self.poimanagerlogic().sigActivePoiUpdated.connect(
            self._update_active_poi, QtCore.Qt.QueuedConnection)

        # Connect track period after setting the GUI value from the logic
        self._mw.track_period_SpinBox.setValue(self.poimanagerlogic().refocus_period)
        self._mw.time_till_next_update_ProgressBar.setMaximum(self.poimanagerlogic().refocus_period)
        self._mw.time_till_next_update_ProgressBar.setValue(self.poimanagerlogic().refocus_period)


        # Redraw the sample_shift axes if the range changes
        self._mw.sample_shift_ViewWidget.plotItem.sigRangeChanged.connect(self._redraw_sample_shift)

        self._mw.show()

    def initReorientRoiDialogUI(self):
        """ Definition, configuration and initialization fo the Reorient ROI Dialog GUI.

        This init connects all the graphic modules which were created in the
        *.ui file and configures event handling.
        """

        # Create the Reorient ROI Dialog window
        self._rrd = ReorientRoiDialog()

        # Connect the QDialog buttons to methods in the GUI
        self._rrd.accepted.connect(self.do_roi_reorientation)
        self._rrd.rejected.connect(self.reset_reorientation_dialog)

        # Connect the at_crosshair buttons
        self._rrd.ref_a_at_crosshair_PushButton.clicked.connect(self.ref_a_at_crosshair)
        self._rrd.ref_b_at_crosshair_PushButton.clicked.connect(self.ref_b_at_crosshair)
        self._rrd.ref_c_at_crosshair_PushButton.clicked.connect(self.ref_c_at_crosshair)

        # Connect input value changes to update the sanity-check values
        self._rrd.ref_a_poi_ComboBox.activated.connect(self.reorientation_sanity_check)
        self._rrd.ref_b_poi_ComboBox.activated.connect(self.reorientation_sanity_check)
        self._rrd.ref_c_poi_ComboBox.activated.connect(self.reorientation_sanity_check)
        self._rrd.ref_a_x_pos_DoubleSpinBox.valueChanged.connect(self.reorientation_sanity_check)
        self._rrd.ref_a_y_pos_DoubleSpinBox.valueChanged.connect(self.reorientation_sanity_check)
        self._rrd.ref_a_z_pos_DoubleSpinBox.valueChanged.connect(self.reorientation_sanity_check)
        self._rrd.ref_b_x_pos_DoubleSpinBox.valueChanged.connect(self.reorientation_sanity_check)
        self._rrd.ref_b_y_pos_DoubleSpinBox.valueChanged.connect(self.reorientation_sanity_check)
        self._rrd.ref_b_z_pos_DoubleSpinBox.valueChanged.connect(self.reorientation_sanity_check)
        self._rrd.ref_c_x_pos_DoubleSpinBox.valueChanged.connect(self.reorientation_sanity_check)
        self._rrd.ref_c_y_pos_DoubleSpinBox.valueChanged.connect(self.reorientation_sanity_check)
        self._rrd.ref_c_z_pos_DoubleSpinBox.valueChanged.connect(self.reorientation_sanity_check)

    def mouseMoved(self, event):
        """ Handles any mouse movements inside the image.

        @param event:   Event that signals the new mouse movement.
                        This should be of type QPointF.

        Gets the mouse position, converts it to a position scaled to the image axis
        and than calculates and updated the position to the current POI.
        """

        # converts the absolute mouse position to a position relative to the axis
        mouse_point = self._mw.roi_map_ViewWidget.getPlotItem().getViewBox().mapSceneToView(
            event.toPoint())

        # only calculate distance, if a POI is selected
        if self.poimanagerlogic().active_poi is not None:
            cur_poi_pos = self.poimanagerlogic().get_poi_position(
                poikey=self.poimanagerlogic().active_poi.get_key())
            dx = ScaledFloat(mouse_point.x() - cur_poi_pos[0])
            dy = ScaledFloat(mouse_point.y() - cur_poi_pos[1])
            d_total = ScaledFloat(np.sqrt(
                    (mouse_point.x() - cur_poi_pos[0])**2
                    + (mouse_point.y() - cur_poi_pos[1])**2))

            self._mw.poi_distance_label.setText(
                '{0:.2r}m ({1:.2r}m, {2:.2r}m)'.format(d_total, dx, dy))

    def show(self):
        """Make main window visible and put it above all other windows. """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    @QtCore.Slot()
    def _update_scan_image(self, scan_image=None, image_extent=None):
        if scan_image is None:
            scan_image = self.poimanagerlogic().roi_scan_image
        if image_extent is None:
            image_extent = self.poimanagerlogic().roi_scan_image_extent
        (x_min, x_max), (y_min, y_max) = image_extent
        self.roi_image.getViewBox().enableAutoRange()
        self.roi_image.setRect(QtCore.QRectF(x_min, y_min, x_max - x_min, y_max - y_min))
        cb_range = self.get_cb_range(image=scan_image)
        self.roi_image.setImage(image=scan_image, levels=cb_range)
        self._mw.roi_map_ViewWidget.update()
        self.roi_cb.refresh_colorbar(*cb_range)
        self._mw.roi_cb_ViewWidget.update()
        return

    def shortcut_to_roi_cb_manual(self):
        if not self._mw.roi_cb_manual_RadioButton.isChecked():
            self._mw.roi_cb_manual_RadioButton.toggle()
        else:
            self._update_scan_image()

    def shortcut_to_roi_cb_centiles(self):
        if not self._mw.roi_cb_centiles_RadioButton.isChecked():
            self._mw.roi_cb_centiles_RadioButton.toggle()
        else:
            self._update_scan_image()

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

    def _remove_poi_marker(self, name):
        """ Remove the POI marker for a POI that was deleted. """
        if name in self._markers:
            self._markers[name].delete_from_viewwidget()
            del self._markers[name]
        return

    def move_poi(self):
        """Manually move a POI to a new location in the sample map, but WITHOUT changing the sample position.  This moves a POI relative to all the others.
        """
        self.poimanagerlogic().set_poi_position(shift_roi=False)
        return

    def toggle_tracking(self, state):
        if state:
            self.poimanagerlogic().start_periodic_refocus()
        else:
            self.poimanagerlogic().stop_periodic_refocus()
        return

    def _update_refocus_timer(self, is_active, period, time_until_refocus):
        self._mw.track_poi_Action.blockSignals(True)
        self._mw.track_period_SpinBox.blockSignals(True)
        self._mw.time_till_next_update_ProgressBar.blockSignals(True)

        if is_active:
            self._mw.track_poi_Action.setChecked(True)
        else:
            self._mw.track_poi_Action.setChecked(False)
        self._mw.track_period_SpinBox.setValue(period)
        self._mw.time_till_next_update_ProgressBar.setMaximum(period)
        self._mw.time_till_next_update_ProgressBar.setValue(time_until_refocus)

        self._mw.time_till_next_update_ProgressBar.blockSignals(False)
        self._mw.track_period_SpinBox.blockSignals(False)
        self._mw.track_poi_Action.blockSignals(False)
        return

    def _update_pois(self, poi_dict):
        """ Populate the dropdown box for selecting a poi. """
        self._mw.active_poi_ComboBox.blockSignals(True)
        self._mw.offset_anchor_ComboBox.blockSignals(True)

        self._mw.active_poi_ComboBox.clear()
        self._mw.offset_anchor_ComboBox.clear()
        # self._rrd.ref_a_poi_ComboBox.clear()
        # self._rrd.ref_b_poi_ComboBox.clear()
        # self._rrd.ref_c_poi_ComboBox.clear()

        poi_names = sorted(poi_dict)
        self._mw.active_poi_ComboBox.addItems(poi_names)
        self._mw.offset_anchor_ComboBox.addItems(poi_names)

        for name, position in poi_dict.items():
            pass

        # If there is no active POI, set the combobox to nothing (-1)
        if self.poimanagerlogic().active_poi is None:
            self._mw.active_poi_ComboBox.setCurrentIndex(-1)
        else:
            index = self._mw.active_poi_ComboBox.findText(self.poimanagerlogic().active_poi)
            self._mw.active_poi_ComboBox.setCurrentIndex(index)

        self._mw.offset_anchor_ComboBox.blockSignals(False)
        self._mw.active_poi_ComboBox.blockSignals(False)
        return

    def _update_active_poi(self, name):
        self._mw.active_poi_ComboBox.blockSignals(True)
        index = self._mw.active_poi_ComboBox.findText(name) if name else -1
        self._mw.active_poi_ComboBox.setCurrentIndex(index)
        self._mw.active_poi_ComboBox.blockSignals(True)

    def set_roi_name(self, name):
        """ Set the name of the current ROI."""
        self.poimanagerlogic().roi_name = name

    def change_poi_name(self):
        """ Change the name of a poi."""

        new_name = self._mw.poi_name_LineEdit.text()
        if self._mw.active_poi_ComboBox.text() == new_name or not new_name:
            return

        self.poimanagerlogic().rename_poi(new_name=new_name)

        # After POI name is changed, empty name field
        self._mw.poi_name_LineEdit.blockSignals(True)
        self._mw.poi_name_LineEdit.setText('')
        self._mw.poi_name_LineEdit.blockSignals(False)
        return

    def select_poi_from_marker(self, poikey=None):
        """ Process the selection of a POI from click on POImark."""

        # Keep track of selected POI
        self.poimanagerlogic().set_active_poi(poikey)

#        # Set the selected POI in the combobox
#        self._mw.active_poi_ComboBox.setCurrentIndex(self._mw.active_poi_ComboBox.findData(poikey))
#        self._redraw_poi_markers()

    def update_poi_pos(self):
        if self.poimanagerlogic().active_poi is None:
            self.log.warning("No POI selected.")
        else:
            if self._mw.refind_method_ComboBox.currentText() == 'position optimisation':
                self.poimanagerlogic().optimise_poi(poikey=self.poimanagerlogic().active_poi.get_key())

            elif self._mw.refind_method_ComboBox.currentText() == 'offset anchor':
                anchor_key = self._mw.offset_anchor_ComboBox.itemData(
                    self._mw.offset_anchor_ComboBox.currentIndex())
                self.poimanagerlogic().optimise_poi(poikey=self.poimanagerlogic().active_poi.get_key(),
                                                     anchorkey=anchor_key)

    def toggle_follow(self):
        if self._mw.goto_poi_after_update_checkBox.isChecked():
            self.poimanagerlogic().go_to_crosshair_after_refocus = False
        else:
            self.poimanagerlogic().go_to_crosshair_after_refocus = True

    def _update_timer(self):
        self._mw.time_till_next_update_ProgressBar.setValue(self.poimanagerlogic().time_left)

    def set_track_period(self):
        """ Change the progress bar and update the timer duration."""

        new_track_period = self._mw.track_period_SpinBox.value()
        self.poimanagerlogic().set_periodic_optimize_duration(duration=new_track_period)

    def _track_period_changed(self):
        """ Reflect the changed track period in the GUI elements.
        """
        new_track_period = self.poimanagerlogic().timer_duration
        # Set the new maximum for the progress bar
        self._mw.time_till_next_update_ProgressBar.setMaximum(new_track_period)

        # If the tracker is not active, then set the value of the progress bar to the
        # new maximum
        if not self._mw.track_poi_Action.isChecked():
            self._mw.time_till_next_update_ProgressBar.setValue(new_track_period)

    def _redraw_clocktime_ticks(self):
        """If duration is displayed, reset ticks to default.
        Otherwise, create and update custom date/time ticks to the new axis range.
        """
        myAxisItem = self._mw.sample_shift_ViewWidget.plotItem.axes['bottom']['item']

        # if duration display, reset to default ticks
        if self._mw.display_shift_vs_duration_RadioButton.isChecked():
            myAxisItem.setTicks(None)

        # otherwise, convert tick strings to clock format
        else:

            # determine size of the sample shift bottom axis item in pixels
            bounds = myAxisItem.mapRectFromParent(myAxisItem.geometry())
            span = (bounds.topLeft(), bounds.topRight())
            lengthInPixels = (span[1] - span[0]).manhattanLength()

            if lengthInPixels == 0:
                return -1
            if myAxisItem.range[0] < 0:
                return -1

            default_ticks = myAxisItem.tickValues(
                myAxisItem.range[0], myAxisItem.range[1], lengthInPixels)

            newticks = []
            for i, tick_level in enumerate(default_ticks):
                newticks_this_level = []
                ticks = tick_level[1]
                for ii, tick in enumerate(ticks):
                    # For major ticks, include date
                    if i == 0:
                        string = time.strftime("%H:%M (%d.%m.)", time.localtime(tick * 3600))
                        # (the axis is plotted in hours to get naturally better placed ticks.)

                    # for middle and minor ticks, just display clock time
                    else:
                        string = time.strftime("%H:%M", time.localtime(tick * 3600))

                    newticks_this_level.append((tick, string))
                newticks.append(newticks_this_level)

            myAxisItem.setTicks(newticks)
            return 0

    def _redraw_sample_shift(self):

        # Get trace data and calculate shifts in x,y,z
        poi_trace = self.poimanagerlogic().poi_list['sample'].get_position_history()

        # If duration display is checked, subtract initial time and convert to
        # mins or hours as appropriate
        if self._mw.display_shift_vs_duration_RadioButton.isChecked():
            time_shift_data = (poi_trace[:, 0] - poi_trace[0, 0])

            if np.max(time_shift_data) < 300:
                self._mw.sample_shift_ViewWidget.setLabel('bottom', 'Time elapsed', units='s')
            elif np.max(time_shift_data) < 7200:
                time_shift_data = time_shift_data / 60.0
                self._mw.sample_shift_ViewWidget.setLabel('bottom', 'Time elapsed', units='min')
            else:
                time_shift_data = time_shift_data / 3600.0
                self._mw.sample_shift_ViewWidget.setLabel('bottom', 'Time elapsed', units='hr')

        # Otherwise, take the actual time but divide by 3600 so that tickmarks
        # automatically fall on whole hours
        else:
            time_shift_data = poi_trace[:, 0] / 3600.0
            self._mw.sample_shift_ViewWidget.setLabel('bottom', 'Time', units='')

        # Subtract initial position to get shifts
        x_shift_data = (poi_trace[:, 1] - poi_trace[0, 1])
        y_shift_data = (poi_trace[:, 2] - poi_trace[0, 2])
        z_shift_data = (poi_trace[:, 3] - poi_trace[0, 3])

        # Plot data
        self.x_shift_plot.setData(time_shift_data, x_shift_data)
        self.y_shift_plot.setData(time_shift_data, y_shift_data)
        self.z_shift_plot.setData(time_shift_data, z_shift_data)

        self._redraw_clocktime_ticks()

    def _redraw_poi_markers(self):

        self.log.debug('starting redraw_poi_markers {0}'.format(time.time()))

        for key in self.poimanagerlogic().get_all_pois():
            if key is not 'crosshair' and key is not 'sample':
                position = self.poimanagerlogic().get_poi_position(poikey=key)
                position = position[:2]

                if key in self._markers.keys():
                    self._markers[key].set_position(position)
                    self._markers[key].deselect()
                else:
                    # Create Region of Interest as marker:
                    marker = PoiMark(
                        position,
                        poi=self.poimanagerlogic().poi_list[key],
                        click_action=self.select_poi_from_marker,
                        movable=False,
                        scaleSnap=False,
                        snapSize=1.0e-6)

                    # Add to the Map Widget
                    marker.add_to_viewwidget(self._mw.roi_map_ViewWidget)
                    self._markers[key] = marker

        if self.poimanagerlogic().active_poi is not None:
            active_poi_key = self.poimanagerlogic().active_poi.get_key()

            self._markers[active_poi_key].select()
            cur_poi_pos = self.poimanagerlogic().get_poi_position(poikey=active_poi_key)
            self._mw.poi_coords_label.setText(
                '({0:.2r}m, {1:.2r}m, {2:.2r}m)'.format(
                    ScaledFloat(cur_poi_pos[0]),
                    ScaledFloat(cur_poi_pos[1]),
                    ScaledFloat(cur_poi_pos[2])
                    )
                )
        self.log.debug('finished redraw at {0}'.format(time.time()))

    def make_new_roi(self):
        """ Start new ROI by removing all POIs and resetting the sample history."""

        for key in self.poimanagerlogic().get_all_pois():
            if key is not 'crosshair' and key is not 'sample':
                self._markers[key].delete_from_viewwidget()

        del self._markers
        self._markers = dict()

        self.poimanagerlogic().reset_roi()

        self.populate_poi_list()

    def save_roi(self):
        """ Save ROI to file."""

        self.poimanagerlogic().save_poi_map_as_roi()

    def load_roi(self):
        """ Load a saved ROI from file."""

        this_file = QtWidgets.QFileDialog.getOpenFileName(
            self._mw,
            str("Open ROI"),
            None,
            str("Data files (*.dat)"))[0]

        self.poimanagerlogic().load_roi_from_file(filename=this_file)

        self.populate_poi_list()

    def open_reorient_roi_dialog(self):
        """ Open the dialog for reorienting the ROI. """
        self._rrd.show()

    def ref_a_at_crosshair(self):
        """ Set the newpos for ref A from the current crosshair position. """
        # TODO: get the range for these spinboxes from the hardware scanner range!
        self._rrd.ref_a_x_pos_DoubleSpinBox.setValue(self.scannerlogic().get_position()[0])
        self._rrd.ref_a_y_pos_DoubleSpinBox.setValue(self.scannerlogic().get_position()[1])
        self._rrd.ref_a_z_pos_DoubleSpinBox.setValue(self.scannerlogic().get_position()[2])

    def ref_b_at_crosshair(self):
        """ Set the newpos for ref B from the current crosshair position. """
        self._rrd.ref_b_x_pos_DoubleSpinBox.setValue(self.scannerlogic().get_position()[0])
        self._rrd.ref_b_y_pos_DoubleSpinBox.setValue(self.scannerlogic().get_position()[1])
        self._rrd.ref_b_z_pos_DoubleSpinBox.setValue(self.scannerlogic().get_position()[2])

    def ref_c_at_crosshair(self):
        """ Set the newpos for ref C from the current crosshair position. """
        self._rrd.ref_c_x_pos_DoubleSpinBox.setValue(self.scannerlogic().get_position()[0])
        self._rrd.ref_c_y_pos_DoubleSpinBox.setValue(self.scannerlogic().get_position()[1])
        self._rrd.ref_c_z_pos_DoubleSpinBox.setValue(self.scannerlogic().get_position()[2])

    def do_roi_reorientation(self):
        """Pass the old and new positions of refs A, B, C to PoiManager Logic to reorient every POI in the ROI.
        """

        ref_a_coords, ref_b_coords, ref_c_coords, ref_a_newpos, ref_b_newpos, ref_c_newpos = self._read_reorient_roi_dialog_values()

        self.poimanagerlogic().reorient_roi(ref_a_coords, ref_b_coords, ref_c_coords, ref_a_newpos, ref_b_newpos, ref_c_newpos)

        # Clear the values in the Reorient Roi Dialog in case it is needed again
        self.reset_reorientation_dialog()

    def _read_reorient_roi_dialog_values(self):
        """ This reads the values from reorient ROI Dialog, and returns them. """

        # Get POI keys for the chosen ref points
        ref_a_key = self._rrd.ref_a_poi_ComboBox.itemData(self._rrd.ref_a_poi_ComboBox.currentIndex())
        ref_b_key = self._rrd.ref_b_poi_ComboBox.itemData(self._rrd.ref_b_poi_ComboBox.currentIndex())
        ref_c_key = self._rrd.ref_c_poi_ComboBox.itemData(self._rrd.ref_c_poi_ComboBox.currentIndex())

        # Get the old coords for these refs
        ref_a_coords = np.array(self.poimanagerlogic().poi_list[ref_a_key].get_coords_in_sample())
        ref_b_coords = np.array(self.poimanagerlogic().poi_list[ref_b_key].get_coords_in_sample())
        ref_c_coords = np.array(self.poimanagerlogic().poi_list[ref_c_key].get_coords_in_sample())

        ref_a_newpos = np.array([self._rrd.ref_a_x_pos_DoubleSpinBox.value(),
                                 self._rrd.ref_a_y_pos_DoubleSpinBox.value(),
                                 self._rrd.ref_a_z_pos_DoubleSpinBox.value()])
        ref_b_newpos = np.array([self._rrd.ref_b_x_pos_DoubleSpinBox.value(),
                                 self._rrd.ref_b_y_pos_DoubleSpinBox.value(),
                                 self._rrd.ref_b_z_pos_DoubleSpinBox.value()])
        ref_c_newpos = np.array([self._rrd.ref_c_x_pos_DoubleSpinBox.value(),
                                 self._rrd.ref_c_y_pos_DoubleSpinBox.value(),
                                 self._rrd.ref_c_z_pos_DoubleSpinBox.value()])

        return ref_a_coords, ref_b_coords, ref_c_coords, ref_a_newpos*1e-6, ref_b_newpos*1e-6, ref_c_newpos*1e-6

    def reset_reorientation_dialog(self):
        """ Reset all the values in the reorient roi dialog. """

        self._rrd.ref_a_x_pos_DoubleSpinBox.setValue(0)
        self._rrd.ref_a_y_pos_DoubleSpinBox.setValue(0)
        self._rrd.ref_a_z_pos_DoubleSpinBox.setValue(0)

        self._rrd.ref_b_x_pos_DoubleSpinBox.setValue(0)
        self._rrd.ref_b_y_pos_DoubleSpinBox.setValue(0)
        self._rrd.ref_b_z_pos_DoubleSpinBox.setValue(0)

        self._rrd.ref_c_x_pos_DoubleSpinBox.setValue(0)
        self._rrd.ref_c_y_pos_DoubleSpinBox.setValue(0)
        self._rrd.ref_c_z_pos_DoubleSpinBox.setValue(0)

    def reorientation_sanity_check(self):
        """ Calculate the difference in length between edges of old triangle defined by refs A, B, C and the new triangle.
        """

        # Get set of positions from GUI
        ref_a_coords, ref_b_coords, ref_c_coords, ref_a_newpos, ref_b_newpos, ref_c_newpos = self._read_reorient_roi_dialog_values()

        # Calculate the difference in side lengths AB, BC, CA between the old triangle and the new triangle
        delta_ab = np.linalg.norm(ref_b_coords - ref_a_coords) - np.linalg.norm(ref_b_newpos - ref_a_newpos)
        delta_bc = np.linalg.norm(ref_c_coords - ref_b_coords) - np.linalg.norm(ref_c_newpos - ref_b_newpos)
        delta_ca = np.linalg.norm(ref_a_coords - ref_c_coords) - np.linalg.norm(ref_a_newpos - ref_c_newpos)

        # Write to the GUI
        self._rrd.length_difference_ab_Label.setText(str(delta_ab))
        self._rrd.length_difference_bc_Label.setText(str(delta_bc))
        self._rrd.length_difference_ca_Label.setText(str(delta_ca))

    def autofind_pois(self):
        """Run the autofind_pois procedure in the POI Manager Logic to get all the POIs in the current ROI image."""
        #Fixme: Add here the appropriate functionality

        self.log.error("Has to be implemented properly. Feel free to do it.")

        # # Get the thresholds from the user-chosen color bar range
        # cb_min, cb_max = self.get_cb_range()
        #
        # this_min_threshold = cb_min + 0.3 * (cb_max - cb_min)
        # this_max_threshold = cb_max
        #
        # self.poimanagerlogic().autofind_pois(neighborhood_size=1, min_threshold=this_min_threshold, max_threshold=this_max_threshold)

    def optimize_roi(self):
        """Run the autofind_pois procedure in the POI Manager Logic to get all the POIs in the current ROI image."""
        #Fixme: Add here the appropriate functionality
        self.log.error("Not implemented yet. Feel free to help!")