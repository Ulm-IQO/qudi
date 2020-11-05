# -*- coding: utf-8 -*-

"""
This file contains modified pyqtgraph Widgets/Items for Qudi to display 1D scanning masurements.

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
from PySide2 import QtCore, QtWidgets
from pyqtgraph import PlotWidget, PlotDataItem, ViewBox, InfiniteLine, LinearRegionItem, mkPen

from .colorbar import ColorBarWidget, ColorBarMode
from ..colordefs import QudiPalette

__all__ = ('ScanPlotDataItem', 'Scan1DPlotWidget', 'Scan1DViewBox', 'Scan1DWidget')


class ScanPlotDataItem(PlotDataItem):
    """ Extension of pg.PlotDataItem to display 1D scanning measurement data.

    Adds the signal sigMouseClicked to tap into mouse click events and receive the real world data
    coordinate of the click.
    """
    sigMouseClicked = QtCore.Signal(object, float)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        return

    def mouseClickEvent(self, ev):
        if not ev.double():
            pos = self.getViewBox().mapSceneToView(ev.scenePos())
            print(pos)
            self.sigMouseClicked.emit(ev.button(), (pos.x(), pos.y()))
        return super().mouseClickEvent(ev)


class Scan1DPlotWidget(PlotWidget):
    """
    Extend the PlotWidget Class with more functionality used for qudi scan images.
    Supported features:
     - draggable/static vertical line (marker) with optional range constraints.
     - zoom feature by linear region selection
     - signalling for linear region selection

    This class depends on the Scan1DViewBox class defined further below.
    This class can be promoted in the Qt designer.
    """
    sigMouseAreaSelected = QtCore.Signal(float, float)  # mapped mouse 1D selection (x_start, x_end)

    def __init__(self, *args, **kwargs):
        kwargs['viewBox'] = Scan1DViewBox()  # Use custom pg.ViewBox subclass
        super().__init__(*args, **kwargs)
        self.getViewBox().sigMouseAreaSelected.connect(self.__translate_selection_range)
        self.markers = list()

    @property
    def selection_enabled(self):
        return bool(self.getViewBox().linear_selection)

    @property
    def zoom_by_selection_enabled(self):
        return bool(self.getViewBox().zoom_by_selection)

    def toggle_selection(self, enable):
        """
        De-/Activate the linear region selection tool.
        If active you can select a linear region within the ViewBox by dragging the mouse
        with the left button. Each selection in real-world data coordinates will be emitted by
        sigMouseAreaSelected.
        By using toggle_zoom_by_selection you can optionally de-/activate zooming in on the
        selection.

        @param bool enable: Toggle selection on (True) or off (False)
        """
        return self.getViewBox().toggle_selection(enable)

    def toggle_zoom_by_selection(self, enable):
        """
        De-/Activate automatic zooming into a selection.
        See also: toggle_selection

        @param bool enable: Toggle zoom upon selection on (True) or off (False)
        """
        return self.getViewBox().toggle_zoom_by_selection(enable)

    def add_marker(self, *args, **kwargs):
        """
        Add a vertical marker to this ScanPlotWidget.
        You can pass all optional parameters you can pass to ScanMarker.__init__
        The stacking of markers will be in order of insertion (last added marker is on top).
        Keep stacking in mind when you want to have a draggable marker.
        """
        # Create new ScanMarker instance and add to markers list
        self.markers.append(ScanMarker(self, *args, **kwargs))
        # Add marker to ViewBox
        self.show_marker(-1)
        return

    def remove_marker(self, index=-1):
        """
        Remove the marker at position <index> or the last one added (default) from this
        Scan1DPlotWidget.
        """
        marker = self.markers.pop(index)
        # Remove crosshair from ViewBox
        marker.remove_from_view()
        marker.deleteLater()
        return

    def hide_marker(self, index=-1):
        self.markers[index].remove_from_view()
        return

    def show_marker(self, index=-1):
        self.markers[index].add_to_view()
        return

    def bring_marker_on_top(self, index):
        """

        @param index:
        """
        self.markers[index].setZValue(11)
        return

    @QtCore.Slot(QtCore.QRectF)
    def __translate_selection_range(self, rect):
        tmp_x = (rect.left(), rect.right())
        tmp_y = (rect.top(), rect.bottom())
        x_limits = min(tmp_x), max(tmp_x)
        y_limits = min(tmp_y), max(tmp_y)
        self.sigMouseAreaSelected.emit(x_limits, y_limits)


class Scan1DViewBox(ViewBox):
    """
    Extension for pg.ViewBox to be used with ScanPlotWidget.

    Implements optional rectangular rubber band area selection and optional corresponding zooming.
    """

    sigMouseAreaSelected = QtCore.Signal(float, float)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.zoom_by_selection = False
        self.linear_selection = False
        self.linear_region = LinearRegionItem(orientation='horizontal', movable=False)
        return

    def toggle_selection(self, enable):
        """
        De-/Activate the linear selection tool.
        If active you can select a linear region within the ViewBox by dragging the mouse
        with the left button. Each selection range in real-world data coordinates will be
        emitted by sigMouseAreaSelected.
        By using toggle_zoom_by_selection you can optionally de-/activate zooming in on the
        selection.

        @param bool enable: Toggle selection on (True) or off (False)
        """
        self.linear_selection = bool(enable)
        return

    def toggle_zoom_by_selection(self, enable):
        """
        De-/Activate automatic zooming into a selection.
        See also: toggle_selection

        @param bool enable: Toggle zoom upon selection on (True) or off (False)
        """
        self.zoom_by_selection = bool(enable)
        return

    def mouseDragEvent(self, ev, axis=None):
        """
        Additional mouse drag event handling to implement linear selection and zooming.
        """
        if self.linear_selection and ev.button() == QtCore.Qt.LeftButton:
            self.linear_region.setRegion((ev.buttonDownPos().x(), ev.pos().x()))
            if ev.isStart():
                self.addItem(self.linear_region)
            elif ev.isFinish():
                start = self.mapToView(ev.buttonDownPos()).x()
                stop = self.mapToView(ev.pos()).x()
                self.removeItem(self.linear_region)
                if self.zoom_by_selection:
                    # AutoRange needs to be disabled by hand because of a pyqtgraph bug.
                    if self.autoRangeEnabled():
                        self.disableAutoRange()
                    self.setRange(xRange=(start, stop), padding=0)
                self.sigMouseAreaSelected.emit(start, stop)
            ev.accept()
            return
        else:
            return super().mouseDragEvent(ev, axis)


class ScanMarker(QtCore.QObject):
    """
    Represents a marker (vertical line) to be used in Scan1DPlotWidget.

    @param QPointF|float[2] position:
    @param QSizeF|float[2] size:
    @param float min_size_factor:
    @param float[2] allowed_range:
    @param bool movable:
    @param QPen pen:
    @param QPen hover_pen:
    """

    _default_pen = {'color': '#00ff00', 'width': 1}
    _default_hover_pen = {'color': '#ffff00', 'width': 1}

    sigPositionChanged = QtCore.Signal(float)
    sigPositionDragged = QtCore.Signal(float)
    sigDragStarted = QtCore.Signal()
    sigDragFinished = QtCore.Signal(float)

    def __init__(self, parent, position=None, allowed_range=None, movable=None, pen=None,
                 hover_pen=None):
        super().__init__(parent=parent)
        self._allowed_range = None
        self.__is_dragged = False
        self.vline = InfiniteLine(pos=0,
                                  angle=90,
                                  movable=False,
                                  pen=self._default_pen,
                                  hoverPen=self._default_hover_pen)

        if pen is not None:
            self.set_pen(pen)
        if hover_pen is not None:
            self.set_hover_pen(hover_pen)
        if position is not None:
            self.set_position(position)
        if allowed_range is not None:
            self.set_allowed_range(allowed_range)
        if movable is not None:
            self.set_movable(movable)

        self.vline.sigDragged.connect(self._update_pos)
        self.vline.sigPositionChangeFinished.connect(self._finish_drag)
        self.sigPositionDragged.connect(self.sigPositionChanged)

    @property
    def movable(self):
        return bool(self.vline.movable)

    @property
    def position(self):
        return self.vline.pos()[0]

    @property
    def allowed_range(self):
        if self._allowed_range is None:
            return None
        return tuple(self._allowed_range)

    def _update_pos(self, obj=None):
        """
        Called each time the position of the InfiniteLine has been changed by a user drag.
        """
        if not self.__is_dragged:
            self.__is_dragged = True
            self.sigDragStarted.emit()
        self.sigPositionDragged.emit(self.position)
        return

    def _finish_drag(self):
        if self.__is_dragged:
            self.__is_dragged = False
            self.sigDragFinished.emit(self.position)
        return

    def add_to_view(self):
        view = self.parent()
        if self.vline not in view.items():
            view.addItem(self.vline)

    def remove_from_view(self):
        view = self.parent()
        if self.vline in view.items():
            view.removeItem(self.vline)

    def set_movable(self, movable):
        """
        (Un-)Set the marker movable (draggable by mouse cursor).

        @param bool movable: Set the marker movable (True) or not (False)
        """
        self.vline.setMovable(movable)
        return

    def set_position(self, pos):
        """
        Set the marker to the given coordinate.

        @param float pos: x-position of the marker
        """
        self.vline.blockSignals(True)
        self.vline.setPos(pos)
        self.vline.blockSignals(False)
        self.sigPositionChanged.emit(self.position)
        return

    def set_allowed_range(self, new_range):
        """
        Sets a range boundary for the marker position.

        @param float[2] new_range: min-max range value tuple. If None set unlimited ranges.
        """
        if new_range is None:
            self.vline.setBounds((None, None))
        else:
            self.vline.setBounds(new_range)
        self._allowed_range = tuple(new_range)
        return

    def set_pen(self, pen):
        """
        Sets the pen to be used for drawing the marker line.
        Given parameter must be compatible with pyqtgraph.mkPen()

        @param pen: pyqtgraph compatible pen to use
        """
        self.vline.setPen(pen)
        return

    def set_hover_pen(self, pen):
        """
        Sets the pen to be used for drawing the marker line when the mouse cursor is hovering over
        them.
        Given parameter must be compatible with pyqtgraph.mkPen()

        @param pen: pyqtgraph compatible pen to use
        """
        self.vline.setHoverPen(pen)
        return


class Scan1DWidget(QtWidgets.QWidget):
    """
    Extend the PlotWidget Class with more functionality used for qudi scan images.
    Supported features:
     - draggable/static vertical line (marker) with optional range constraints.
     - zoom feature by linear region selection
     - signalling for linear region selection

    This class depends on the Scan1DViewBox class defined further below.
    This class can be promoted in the Qt designer.
    """
    sigScanToggled = QtCore.Signal(bool)

    # Wrapped attribute names from ScanPlotWidget and ScanPlotDataItem objects.
    # Adjust these sets if ScanPlotWidget or ScanPlotDataItem class changes.
    __plot_widget_wrapped = frozenset(
        {'selection_enabled', 'zoom_by_selection_enabled', 'toggle_selection',
         'toggle_zoom_by_selection', 'add_marker', 'remove_marker', 'hide_marker',
         'show_marker', 'bring_marker_on_top', 'markers', 'sigMouseAreaSelected',
         'autoRange'}
    )
    __plot_item_wrapped = frozenset({'sigMouseClicked'})

    def __init__(self, *args, channel_units, scan_icon=None, **kwargs):
        super().__init__(*args, **kwargs)

        self._channel_units = channel_units.copy()
        self._scan_data = dict()  # in case of multichannel data, save a reference here

        layout = QtWidgets.QGridLayout()
        layout.setColumnStretch(1, 1)
        self.setLayout(layout)

        self._toggle_scan_button = QtWidgets.QPushButton('Toggle Scan')
        self._toggle_scan_button.setCheckable(True)
        self._toggle_scan_button.setFocusPolicy(QtCore.Qt.FocusPolicy.TabFocus)
        if scan_icon is not None:
            self._toggle_scan_button.setIcon(scan_icon)
            # self._toggle_scan_button.setIconSize(QtCore.QSize(22, 22))
            # self._toggle_scan_button.setText('Scan')
        self._toggle_scan_button.setMinimumWidth(self._toggle_scan_button.sizeHint().width())
        layout.addWidget(self._toggle_scan_button, 0, 0)

        self._channel_selection_combobox = QtWidgets.QComboBox()
        self._channel_selection_combobox.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                                       QtWidgets.QSizePolicy.Preferred)
        self._channel_selection_combobox.addItems(tuple(channel_units))
        layout.addWidget(self._channel_selection_combobox, 0, 1)
        # Hide channel selection if only a single channel is given
        if len(channel_units) < 2:
            self._channel_selection_combobox.setVisible(False)

        self._plot_widget = Scan1DPlotWidget()
        self._plot_item = ScanPlotDataItem(pen=mkPen(QudiPalette.c1))
        self._plot_widget.addItem(self._plot_item)
        self._plot_widget.setMinimumWidth(100)
        self._plot_widget.setMinimumHeight(100)
        self._plot_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                        QtWidgets.QSizePolicy.Expanding)
        self._plot_widget.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        # self._plot_widget.setAspectLocked(lock=True, ratio=1.0)
        layout.addWidget(self._plot_widget, 1, 0, 1, 2)

        self._channel_selection_combobox.currentIndexChanged.connect(self.__channel_changed)
        self._toggle_scan_button.clicked[bool].connect(self.sigScanToggled)

        self.__channel_changed()

    def __getattr__(self, name):
        if name in self.__plot_widget_wrapped:
            return getattr(self._plot_widget, name)
        elif name in self.__plot_item_wrapped:
            return getattr(self._plot_item, name)
        raise AttributeError('No attribute "{0}" found in Scan1DWidget object.'.format(name))

    def set_data_channels(self, channel_units):
        if channel_units is None:
            self._channel_units = dict()
            self._channel_selection_combobox.setVisible(False)
            self._channel_selection_combobox.blockSignals(True)
            self._channel_selection_combobox.clear()
            self._channel_selection_combobox.setVisible(False)
            self._channel_selection_combobox.blockSignals(False)
            self._plot_item.clear()
            self._scan_data = dict()
            self.set_data_label('', '')
        elif isinstance(channel_units, dict) and len(channel_units) > 0:
            self._channel_units = channel_units.copy()
            old_channel = self._channel_selection_combobox.currentText()
            self._channel_selection_combobox.blockSignals(True)
            self._channel_selection_combobox.clear()
            self._channel_selection_combobox.addItems(tuple(self._channel_units))
            if old_channel in channel_units:
                self._channel_selection_combobox.setCurrentText(old_channel)
            else:
                self._channel_selection_combobox.setCurrentIndex(0)
            self._channel_selection_combobox.blockSignals(False)
            self._channel_selection_combobox.setVisible(len(channel_units) > 1)

            if old_channel not in channel_units:
                self.__channel_changed()
        else:
            raise ValueError('name_to_unit_map must be non-empty dict or None')
        return

    def set_scan_data(self, data, x=None):
        """

        """
        if data is None:
            self._plot_item.clear()
            self._scan_data = dict()
            return

        if isinstance(data, dict):
            self._scan_data = data.copy()
            channel = self._channel_selection_combobox.currentText()
            if channel not in self._scan_data:
                self._plot_item.clear()
                return
            scan = self._scan_data[channel]
        else:
            raise TypeError(
                'Scan data must be dict with keys as channel names and values as 1D numpy arrays'
            )

        # Set plot data
        self._plot_item.setData(x=self._plot_item.xData if x is None else x, y=scan)
        return

    def set_axis_label(self, label, unit=None):
        return self._plot_widget.setLabel('bottom', text=label, units=unit)

    def set_data_label(self, label, unit=None):
        return self._plot_widget.setLabel('left', text=label, units=unit)

    @QtCore.Slot(bool)
    def toggle_scan(self, enable):
        if enable != self._toggle_scan_button.isChecked():
            self._toggle_scan_button.setChecked(enable)

    @QtCore.Slot(bool)
    def toggle_enabled(self, enable):
        if enable != self._toggle_scan_button.isEnabled():
            self._toggle_scan_button.setEnabled(enable)

    @QtCore.Slot()
    def __channel_changed(self):
        channel = self._channel_selection_combobox.currentText()
        channel_unit = self._channel_units.get(channel, '')
        self.set_data_label(channel, unit=channel_unit)
        scan = self._scan_data.get(channel, None)
        if scan is None:
            self._plot_item.clear()
        else:
            self._plot_item.setData(x=self._plot_item.xData, y=scan)
        return
