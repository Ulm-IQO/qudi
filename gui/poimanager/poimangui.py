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

    """ Creates a circle as a marker.

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
                                 color= self.color
                                 )

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
            elif cos_th > 0 and sin_th < 0:
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
    poimanagerlogic1 = Connector(interface='PoiManagerLogic')
    confocallogic1 = Connector(interface='ConfocalLogic')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initializes the overall GUI, and establishes the connectors.

        This method executes the init methods for each of the GUIs.
        """

        # Connectors
        self._poi_manager_logic = self.get_connector('poimanagerlogic1')
        self._confocal_logic = self.get_connector('confocallogic1')
        self.log.debug("POI Manager logic is {0}".format(self._poi_manager_logic))
        self.log.debug("Confocal logic is {0}".format(self._confocal_logic))

        # Initializing the GUIs
        self.initMainUI()
        self.initReorientRoiDialogUI()

        # There could be POIs created in the logic already, so update lists and map
        self.populate_poi_list()
        self._redraw_sample_shift()
        self._redraw_poi_markers()

    def mouseMoved(self, event):
        """ Handles any mouse movements inside the image.

        @param event:   Event that signals the new mouse movement.
                        This should be of type QPointF.

        Gets the mouse position, converts it to a position scaled to the image axis
        and than calculates and updated the position to the current POI.
        """

        # converts the absolute mouse position to a position relative to the axis
        mouse_point=self.roi_map_image.mapFromScene(event.toPoint())
        #self.log.debug("Mouse at x = {0:0.2e}, y = {1:0.2e}".format(mouse_point.x(), mouse_point.y()))

        # only calculate distance, if a POI is selected
        if self._poi_manager_logic.active_poi is not None:
            cur_poi_pos = self._poi_manager_logic.get_poi_position(poikey=self._poi_manager_logic.active_poi.get_key())
            self._mw.poi_distance_label.setText('{0:.2e} ({1:.2e}, {2:.2e})'.format(
                np.sqrt((mouse_point.x() - cur_poi_pos[0])**2+(mouse_point.y() - cur_poi_pos[1])**2),
                mouse_point.x() - cur_poi_pos[0],
                mouse_point.y() - cur_poi_pos[1]))

    def initMainUI(self):
        """ Definition, configuration and initialisation of the POI Manager GUI.
        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """

        # Use the inherited class 'Ui_PoiManagerGuiTemplate' to create now the
        # GUI element:
        self._mw = PoiManagerMainWindow()

        #####################
        # Configuring the dock widgets
        #####################

        # All our gui elements are dockable, and so there should be no "central" widget.
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)
        #####################
        # Setting up display of ROI map xy image
        #####################

        # Get the image for the display from the logic:
        self.roi_xy_image_data = self._poi_manager_logic.roi_map_data[:, :, 3]

        # Load the image in the display:
        self.roi_map_image = pg.ImageItem(image=self.roi_xy_image_data, axisOrder='row-major')
        self.roi_map_image.setRect(
            QtCore.QRectF(
                self._confocal_logic.image_x_range[0],
                self._confocal_logic.image_y_range[0],
                self._confocal_logic.image_x_range[1] - self._confocal_logic.image_x_range[0],
                self._confocal_logic.image_y_range[1] - self._confocal_logic.image_y_range[0]))

        # Add the display item to the roi map ViewWidget defined in the UI file
        self._mw.roi_map_ViewWidget.addItem(self.roi_map_image)
        self._mw.roi_map_ViewWidget.setLabel('bottom', 'X position', units='m')
        self._mw.roi_map_ViewWidget.setLabel('left', 'Y position', units='m')

        # Set to fixed 1.0 aspect ratio, since the metaphor is a "map" of the sample
        self._mw.roi_map_ViewWidget.setAspectLocked(lock=True, ratio=1.0)

        # Get the colorscales and set LUT
        my_colors = ColorScaleInferno()

        self.roi_map_image.setLookupTable(my_colors.lut)

        # Add color bar:
        self.roi_cb = ColorBar(my_colors.cmap_normed, 100, 0, 100000)

        self._mw.roi_cb_ViewWidget.addItem(self.roi_cb)
        self._mw.roi_cb_ViewWidget.hideAxis('bottom')
        self._mw.roi_cb_ViewWidget.setLabel('left', 'Fluorescence', units='c/s')
        self._mw.roi_cb_ViewWidget.setMouseEnabled(x=False, y=False)

        #####################
        # Setting up display of sample shift plot
        #####################

        # Load image in the display
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

        #####################
        # Connect signals
        #####################

        # Distance Measurement:
        # Introducing a SignalProxy will limit the rate of signals that get fired.
        # Otherwise we will run into a heap of unhandled function calls.
        proxy = pg.SignalProxy(self.roi_map_image.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        # Connecting a Mouse Signal to trace to mouse movement function.
        self.roi_map_image.scene().sigMouseMoved.connect(self.mouseMoved)

        # Toolbar actions
        self._mw.new_roi_Action.triggered.connect(self.make_new_roi)
        self._mw.save_roi_Action.triggered.connect(self.save_roi)
        self._mw.load_roi_Action.triggered.connect(self.load_roi)
        self._mw.reorient_roi_Action.triggered.connect(self.open_reorient_roi_dialog)
        self._mw.autofind_pois_Action.triggered.connect(self.do_autofind_poi_procedure)
        self._mw.optimize_roi_Action.triggered.connect(self.optimize_roi)


        self._mw.new_poi_Action.triggered.connect(self.set_new_poi)
        self._mw.goto_poi_Action.triggered.connect(self.goto_poi)
        self._mw.refind_poi_Action.triggered.connect(self.update_poi_pos)
        self._mw.track_poi_Action.triggered.connect(self.toggle_tracking)

        # Interface controls
        self._mw.get_confocal_image_PushButton.clicked.connect(self.get_confocal_image)
        self._mw.set_poi_PushButton.clicked.connect(self.set_new_poi)
        self._mw.delete_last_pos_Button.clicked.connect(self.delete_last_point)
        self._mw.manual_update_poi_PushButton.clicked.connect(self.manual_update_poi)
        self._mw.move_poi_PushButton.clicked.connect(self.move_poi)
        self._mw.poi_name_LineEdit.returnPressed.connect(self.change_poi_name)
        self._mw.roi_name_LineEdit.editingFinished.connect(self.set_roi_name)
        self._mw.delete_poi_PushButton.clicked.connect(self.delete_poi)

        self._mw.goto_poi_after_update_checkBox.toggled.connect(self.toggle_follow)


        # This needs to be activated so that it only listens to user input, and ignores
        # algorithmic index changes
        self._mw.active_poi_ComboBox.activated.connect(self.handle_active_poi_ComboBox_index_change)
        self._mw.refind_method_ComboBox.currentIndexChanged.connect(self.change_refind_method)

        # Connect the buttons and inputs for the colorbar
        self._mw.roi_cb_centiles_RadioButton.toggled.connect(self.refresh_roi_colorscale)
        self._mw.roi_cb_manual_RadioButton.toggled.connect(self.refresh_roi_colorscale)
        self._mw.roi_cb_min_SpinBox.valueChanged.connect(self.shortcut_to_roi_cb_manual)
        self._mw.roi_cb_max_SpinBox.valueChanged.connect(self.shortcut_to_roi_cb_manual)
        self._mw.roi_cb_low_percentile_DoubleSpinBox.valueChanged.connect(self.shortcut_to_roi_cb_centiles)
        self._mw.roi_cb_high_percentile_DoubleSpinBox.valueChanged.connect(self.shortcut_to_roi_cb_centiles)

        self._mw.display_shift_vs_duration_RadioButton.toggled.connect(self._redraw_sample_shift)
        self._mw.display_shift_vs_clocktime_RadioButton.toggled.connect(self._redraw_sample_shift)

        self._markers = dict()

        # Signal at end of refocus
        self._poi_manager_logic.signal_timer_updated.connect(
            self._update_timer,
            QtCore.Qt.QueuedConnection
        )
        self._poi_manager_logic.signal_poi_updated.connect(
            self._redraw_sample_shift,
            QtCore.Qt.QueuedConnection
        )
        self._poi_manager_logic.signal_poi_updated.connect(
            self.populate_poi_list,
            QtCore.Qt.QueuedConnection
        )
        self._poi_manager_logic.signal_poi_updated.connect(
            self._redraw_poi_markers,
            QtCore.Qt.QueuedConnection
        )
        self._poi_manager_logic.signal_poi_deleted.connect(
            self._remove_poi_marker
        )
        self._poi_manager_logic.signal_confocal_image_updated.connect(
            self._redraw_roi_image
        )

        self._poi_manager_logic.signal_periodic_opt_duration_changed.connect(
            self._track_period_changed
        )
        self._poi_manager_logic.signal_periodic_opt_started.connect(
            self._tracking_started
        )
        self._poi_manager_logic.signal_periodic_opt_stopped.connect(
            self._tracking_stopped
        )

        # Connect track period after setting the GUI value from the logic
        initial_period = self._poi_manager_logic.timer_duration
        self._mw.track_period_SpinBox.setValue(initial_period)
        self._mw.time_till_next_update_ProgressBar.setMaximum(initial_period)
        self._mw.time_till_next_update_ProgressBar.setValue(initial_period)
        self._mw.track_period_SpinBox.valueChanged.connect(self.set_track_period)

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

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._mw.close()

    def show(self):
        """Make main window visible and put it above all other windows. """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def get_confocal_image(self):
        """ Update the roi_map_data in poi manager logic, and use this updated
            data to redraw an image of the ROI.
        """

        # Make poi manager logic get the confocal data
        self._poi_manager_logic.get_confocal_image_data()

    def _redraw_roi_image(self):

        # the image data is the fluorescence part
        self.roi_xy_image_data = self._poi_manager_logic.roi_map_data[:, :, 3]

        # Also get the x and y range limits and hold them locally
        self.roi_map_xmin = np.min(self._poi_manager_logic.roi_map_data[:, :, 0])
        self.roi_map_xmax = np.max(self._poi_manager_logic.roi_map_data[:, :, 0])
        self.roi_map_ymin = np.min(self._poi_manager_logic.roi_map_data[:, :, 1])
        self.roi_map_ymax = np.max(self._poi_manager_logic.roi_map_data[:, :, 1])

        self.roi_map_image.getViewBox().enableAutoRange()
        self.roi_map_image.setRect(
            QtCore.QRectF(
                self.roi_map_xmin,
                self.roi_map_ymin,
                self.roi_map_xmax - self.roi_map_xmin,
                self.roi_map_ymax - self.roi_map_ymin))
        self.roi_map_image.setImage(image=self.roi_xy_image_data, autoLevels=True)

    def shortcut_to_roi_cb_manual(self):
        self._mw.roi_cb_manual_RadioButton.setChecked(True)
        self.refresh_roi_colorscale()

    def shortcut_to_roi_cb_centiles(self):
        self._mw.roi_cb_centiles_RadioButton.setChecked(True)
        self.refresh_roi_colorscale()

    def refresh_roi_colorscale(self):
        """ Adjust the colorbar in the ROI xy image, and update the image with the
        new color scale.

        Calls the refresh method from colorbar, which takes either the lowest
        and higherst value in the image or predefined ranges. Note that you can
        invert the colorbar if the lower border is bigger then the higher one.
        """

        cb_min, cb_max = self.determine_cb_range()

        self.roi_map_image.setImage(image=self.roi_xy_image_data, levels=(cb_min, cb_max))

        self.roi_cb.refresh_colorbar(cb_min, cb_max)
        self._mw.roi_cb_ViewWidget.update()

    def determine_cb_range(self):
        """ Process UI input to determine color bar range"""

        # If "Centiles" is checked, adjust colour scaling automatically to centiles.
        # Otherwise, take user-defined values.
        if self._mw.roi_cb_centiles_RadioButton.isChecked():
            low_centile = self._mw.roi_cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.roi_cb_high_percentile_DoubleSpinBox.value()

            cb_min = np.percentile(self.roi_xy_image_data, low_centile)
            cb_max = np.percentile(self.roi_xy_image_data, high_centile)

        else:
            cb_min = self._mw.roi_cb_min_SpinBox.value()
            cb_max = self._mw.roi_cb_max_SpinBox.value()

        return cb_min, cb_max

    def set_new_poi(self):
        """ This method sets a new poi from the current crosshair position."""
        key = self._poi_manager_logic.add_poi()

    def delete_last_point(self):
        """ Delete the last track position of a chosen poi. """
        if self._poi_manager_logic.active_poi is None:
            self.log.warning("No POI selected. No datapoint can be deleted")
        else:
            self._poi_manager_logic.delete_last_position(poikey=self._poi_manager_logic.active_poi.get_key())

    def delete_poi(self):
        """ Delete the active poi from the list of managed points. """
        if self._poi_manager_logic.active_poi is None:
            self.log.warning("No POI selected.")
        else:
            key = self._poi_manager_logic.active_poi.get_key()

            # todo: this needs to handle the case where the logic deletes a POI.

            self._poi_manager_logic.delete_poi(poikey=key)

    def _remove_poi_marker(self, poikey):
        """ Remove the POI marker for a POI that was deleted.
        """
        self._markers[poikey].delete_from_viewwidget()
        del self._markers[poikey]

    def manual_update_poi(self):
        """ Manually adds a point to the trace of a given poi without refocussing, and uses that information to update sample position.
        """
        if self._poi_manager_logic.active_poi is None:
            self.log.warning("No POI selected.")
        else:
            self._poi_manager_logic.set_new_position(poikey=self._poi_manager_logic.active_poi.get_key())

    def move_poi(self):
        """Manually move a POI to a new location in the sample map, but WITHOUT changing the sample position.  This moves a POI relative to all the others.
        """
        if self._poi_manager_logic.active_poi is None:
            self.log.warning("No POI selected.")
        else:
            self._poi_manager_logic.move_coords(poikey=self._poi_manager_logic.active_poi.get_key())

    def toggle_tracking(self):
        if self._poi_manager_logic.active_poi is None:
            self.log.warning("No POI selected.")
        else:
            if self._poi_manager_logic.timer is None:
                self._poi_manager_logic.start_periodic_refocus(poikey=self._poi_manager_logic.active_poi.get_key())

            else:
                self._poi_manager_logic.stop_periodic_refocus()

    def _tracking_started(self):
        self._mw.track_poi_Action.setChecked(True)

    def _tracking_stopped(self):
        self._mw.track_poi_Action.setChecked(False)

    def goto_poi(self, key):
        """ Go to the last known position of poi <key>."""
        if self._poi_manager_logic.active_poi is None:
            self.log.warning("No POI selected.")
        else:
            self._poi_manager_logic.go_to_poi(poikey=self._poi_manager_logic.active_poi.get_key())

    def populate_poi_list(self):
        """ Populate the dropdown box for selecting a poi. """
        self.log.debug('started populate_poi_list at {0}'.format(time.time()))
        self._mw.active_poi_ComboBox.clear()
        self._mw.offset_anchor_ComboBox.clear()
        self._rrd.ref_a_poi_ComboBox.clear()
        self._rrd.ref_b_poi_ComboBox.clear()
        self._rrd.ref_c_poi_ComboBox.clear()

        for key in self._poi_manager_logic.get_all_pois(abc_sort=True):
            if key is not 'crosshair' and key is not 'sample':
                poi_list_empty = False
                self._mw.active_poi_ComboBox.addItem(
                    self._poi_manager_logic.poi_list[key].get_name(), key)
                self._mw.offset_anchor_ComboBox.addItem(
                    self._poi_manager_logic.poi_list[key].get_name(), key)
                self._rrd.ref_a_poi_ComboBox.addItem(
                    self._poi_manager_logic.poi_list[key].get_name(), key)
                self._rrd.ref_b_poi_ComboBox.addItem(
                    self._poi_manager_logic.poi_list[key].get_name(), key)
                self._rrd.ref_c_poi_ComboBox.addItem(
                    self._poi_manager_logic.poi_list[key].get_name(), key)

        # If there is no active POI, set the combobox to nothing (-1)
        if self._poi_manager_logic.active_poi is None:
            self._mw.active_poi_ComboBox.setCurrentIndex(-1)

        # Otherwise, set it to the active POI
        else:
            self._mw.active_poi_ComboBox.setCurrentIndex(
                self._mw.active_poi_ComboBox.findData(
                    self._poi_manager_logic.active_poi.get_key()
                )
            )

        self.log.debug('finished populating at '.format(time.time()))

    def change_refind_method(self):
        """ Make appropriate changes in the GUI to reflect the newly chosen refind method."""

        if self._mw.refind_method_ComboBox.currentText() == 'position optimisation':
            self._mw.offset_anchor_ComboBox.setEnabled(False)
        elif self._mw.refind_method_ComboBox.currentText() == 'offset anchor':
            self.log.error("Anchor method not fully implemented yet. "
                           "Feel free to fix this method. Using position optimisation instead.")
            self._mw.offset_anchor_ComboBox.setEnabled(True)
        else:
            # TODO: throw an error
            self.log.debug('error 123')

    def set_roi_name(self):
        """ Set the name of a ROI (useful when saving)."""

        self._poi_manager_logic.roi_name = self._mw.roi_name_LineEdit.text().replace(" ", "_")

    def change_poi_name(self):
        """ Change the name of a poi."""

        newname = self._mw.poi_name_LineEdit.text()

        self._poi_manager_logic.rename_poi(poikey=self._poi_manager_logic.active_poi.get_key(), name=newname)

        # After POI name is changed, empty name field
        self._mw.poi_name_LineEdit.setText('')

    def handle_active_poi_ComboBox_index_change(self):
        """ Handle the change of index in the active POI combobox."""

        key = self._mw.active_poi_ComboBox.itemData(self._mw.active_poi_ComboBox.currentIndex())

        self._poi_manager_logic.set_active_poi(poikey = key)

        self._redraw_poi_markers() # todo when line 660 signal in logic is done, this is not necessary

    def select_poi_from_marker(self, poikey=None):
        """ Process the selection of a POI from click on POImark."""

        # Keep track of selected POI
        self._poi_manager_logic.set_active_poi(poikey=poikey)

#        # Set the selected POI in the combobox
#        self._mw.active_poi_ComboBox.setCurrentIndex(self._mw.active_poi_ComboBox.findData(poikey))
#        self._redraw_poi_markers()

    def update_poi_pos(self):
        if self._poi_manager_logic.active_poi is None:
            self.log.warning("No POI selected.")
        else:
            if self._mw.refind_method_ComboBox.currentText() == 'position optimisation':
                self._poi_manager_logic.optimise_poi(poikey=self._poi_manager_logic.active_poi.get_key())

            elif self._mw.refind_method_ComboBox.currentText() == 'offset anchor':
                anchor_key = self._mw.offset_anchor_ComboBox.itemData(
                    self._mw.offset_anchor_ComboBox.currentIndex())
                self._poi_manager_logic.optimise_poi(poikey=self._poi_manager_logic.active_poi.get_key(),
                                                     anchorkey=anchor_key)

    def toggle_follow(self):
        if self._mw.goto_poi_after_update_checkBox.isChecked():
            self._poi_manager_logic.go_to_crosshair_after_refocus = False
        else:
            self._poi_manager_logic.go_to_crosshair_after_refocus = True

    def _update_timer(self):
        self._mw.time_till_next_update_ProgressBar.setValue(self._poi_manager_logic.time_left)

    def set_track_period(self):
        """ Change the progress bar and update the timer duration."""

        new_track_period = self._mw.track_period_SpinBox.value()
        self._poi_manager_logic.set_periodic_optimize_duration(duration=new_track_period)

    def _track_period_changed(self):
        """ Reflect the changed track period in the GUI elements.
        """
        new_track_period = self._poi_manager_logic.timer_duration
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
        poi_trace = self._poi_manager_logic.poi_list['sample'].get_position_history()

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

        for key in self._poi_manager_logic.get_all_pois():
            if key is not 'crosshair' and key is not 'sample':
                position = self._poi_manager_logic.get_poi_position(poikey=key)
                position = position[:2]

                if key in self._markers.keys():
                    self._markers[key].set_position(position)
                    self._markers[key].deselect()
                else:
                    # Create Region of Interest as marker:
                    marker = PoiMark(
                        position,
                        poi=self._poi_manager_logic.poi_list[key],
                        click_action=self.select_poi_from_marker,
                        movable=False,
                        scaleSnap=False,
                        snapSize=1.0e-6)

                    # Add to the Map Widget
                    marker.add_to_viewwidget(self._mw.roi_map_ViewWidget)
                    self._markers[key] = marker

        if self._poi_manager_logic.active_poi is not None:
            active_poi_key = self._poi_manager_logic.active_poi.get_key()

            self._markers[active_poi_key].select()
            cur_poi_pos = self._poi_manager_logic.get_poi_position(poikey=key)
            self._mw.poi_coords_label.setText(
                '({0:.2e}, {1:.2e}, {2:.2e})'.format(cur_poi_pos[0],
                                                     cur_poi_pos[1],
                                                     cur_poi_pos[2]
                                                     )
                )
        self.log.debug('finished redraw at {0}'.format(time.time()))

    def make_new_roi(self):
        """ Start new ROI by removing all POIs and resetting the sample history."""

        for key in self._poi_manager_logic.get_all_pois():
            if key is not 'crosshair' and key is not 'sample':
                self._markers[key].delete_from_viewwidget()

        del self._markers
        self._markers = dict()

        self._poi_manager_logic.reset_roi()

        self.populate_poi_list()

    def save_roi(self):
        """ Save ROI to file."""

        self._poi_manager_logic.save_poi_map_as_roi()

    def load_roi(self):
        """ Load a saved ROI from file."""

        this_file = QtWidgets.QFileDialog.getOpenFileName(
            self._mw,
            str("Open ROI"),
            None,
            str("Data files (*.dat)"))[0]

        self._poi_manager_logic.load_roi_from_file(filename=this_file)

        self.populate_poi_list()

    def open_reorient_roi_dialog(self):
        """ Open the dialog for reorienting the ROI. """
        self._rrd.show()

    def ref_a_at_crosshair(self):
        """ Set the newpos for ref A from the current crosshair position. """
        # TODO: get the range for these spinboxes from the hardware scanner range!
        self._rrd.ref_a_x_pos_DoubleSpinBox.setValue(self._confocal_logic.get_position()[0])
        self._rrd.ref_a_y_pos_DoubleSpinBox.setValue(self._confocal_logic.get_position()[1])
        self._rrd.ref_a_z_pos_DoubleSpinBox.setValue(self._confocal_logic.get_position()[2])

    def ref_b_at_crosshair(self):
        """ Set the newpos for ref B from the current crosshair position. """
        self._rrd.ref_b_x_pos_DoubleSpinBox.setValue(self._confocal_logic.get_position()[0])
        self._rrd.ref_b_y_pos_DoubleSpinBox.setValue(self._confocal_logic.get_position()[1])
        self._rrd.ref_b_z_pos_DoubleSpinBox.setValue(self._confocal_logic.get_position()[2])

    def ref_c_at_crosshair(self):
        """ Set the newpos for ref C from the current crosshair position. """
        self._rrd.ref_c_x_pos_DoubleSpinBox.setValue(self._confocal_logic.get_position()[0])
        self._rrd.ref_c_y_pos_DoubleSpinBox.setValue(self._confocal_logic.get_position()[1])
        self._rrd.ref_c_z_pos_DoubleSpinBox.setValue(self._confocal_logic.get_position()[2])

    def do_roi_reorientation(self):
        """Pass the old and new positions of refs A, B, C to PoiManager Logic to reorient every POI in the ROI.
        """

        ref_a_coords, ref_b_coords, ref_c_coords, ref_a_newpos, ref_b_newpos, ref_c_newpos = self._read_reorient_roi_dialog_values()

        self._poi_manager_logic.reorient_roi(ref_a_coords, ref_b_coords, ref_c_coords, ref_a_newpos, ref_b_newpos, ref_c_newpos)

        # Clear the values in the Reorient Roi Dialog in case it is needed again
        self.reset_reorientation_dialog()

    def _read_reorient_roi_dialog_values(self):
        """ This reads the values from reorient ROI Dialog, and returns them. """

        # Get POI keys for the chosen ref points
        ref_a_key = self._rrd.ref_a_poi_ComboBox.itemData(self._rrd.ref_a_poi_ComboBox.currentIndex())
        ref_b_key = self._rrd.ref_b_poi_ComboBox.itemData(self._rrd.ref_b_poi_ComboBox.currentIndex())
        ref_c_key = self._rrd.ref_c_poi_ComboBox.itemData(self._rrd.ref_c_poi_ComboBox.currentIndex())

        # Get the old coords for these refs
        ref_a_coords = np.array(self._poi_manager_logic.poi_list[ref_a_key].get_coords_in_sample())
        ref_b_coords = np.array(self._poi_manager_logic.poi_list[ref_b_key].get_coords_in_sample())
        ref_c_coords = np.array(self._poi_manager_logic.poi_list[ref_c_key].get_coords_in_sample())

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

    def do_autofind_poi_procedure(self):
        """Run the autofind_pois procedure in the POI Manager Logic to get all the POIs in the current ROI image."""
        #Fixme: Add here the appropriate functionality

        self.log.error("Has to be implemented properly. Feel free to do it.")

        # # Get the thresholds from the user-chosen color bar range
        # cb_min, cb_max = self.determine_cb_range()
        #
        # this_min_threshold = cb_min + 0.3 * (cb_max - cb_min)
        # this_max_threshold = cb_max
        #
        # self._poi_manager_logic.autofind_pois(neighborhood_size=1, min_threshold=this_min_threshold, max_threshold=this_max_threshold)

    def optimize_roi(self):
        """Run the autofind_pois procedure in the POI Manager Logic to get all the POIs in the current ROI image."""
        #Fixme: Add here the appropriate functionality
        self.log.error("Not implemented yet. Feel free to help!")