# -*- coding: utf-8 -*-

"""
This file contains modified pyqtgraph Widgets/Items for Qudi to display scan images.

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
from pyqtgraph import PlotWidget, ImageItem, ViewBox, InfiniteLine, ROI

from .colorbar import ColorBarWidget, ColorBarMode
from ..colordefs import ColorScaleInferno

__all__ = ('ScanImageItem', 'Scan2DPlotWidget', 'Scan2DViewBox', 'Scan2DWidget')


class ScanImageItem(ImageItem):
    """ Extension of pg.ImageItem to display scanning microscopy images.

    Adds the signal sigMouseClicked to tap into mouse click events and receive the real world data
    coordinate of the click.
    Adds functionality to automatically calculate colorscale from configurable data percentile.
    """
    sigMouseClicked = QtCore.Signal(object, tuple)

    def __init__(self, *args, **kwargs):
        self._percentiles = None
        super().__init__(*args, **kwargs)
        # Change default color scale
        self.setLookupTable(ColorScaleInferno().lut)
        return

    @property
    def percentiles(self):
        return self._percentiles

    @percentiles.setter
    def percentiles(self, percentiles):
        if percentiles is None:
            self._percentiles = None
            return

        self._percentiles = (min(percentiles), max(percentiles))
        if self.image is not None:
            masked_image = np.ma.masked_invalid(self.image).compressed()
            if masked_image.size == 0:
                return
            min_value = np.percentile(masked_image, self._percentiles[0])
            max_value = np.percentile(masked_image, self._percentiles[1])
            self.setLevels((min_value, max_value))

    def set_image_extent(self, extent, adjust_for_px_size=True):
        """

        """
        if len(extent) != 2:
            raise TypeError('Image extent must be iterable of length 2.')
        if len(extent[0]) != 2 or len(extent[1]) != 2:
            raise TypeError('Image extent for each axis must be iterable of length 2.')

        if self.image is not None:
            x_min, x_max = min(extent[0]), max(extent[0])
            y_min, y_max = min(extent[1]), max(extent[1])
            if adjust_for_px_size:
                if self.image.shape[0] > 1 and self.image.shape[1] > 1:
                    half_px_x = (x_max - x_min) / (2 * (self.image.shape[0] - 1))
                    half_px_y = (y_max - y_min) / (2 * (self.image.shape[1] - 1))
                    x_min -= half_px_x
                    x_max += half_px_x
                    y_min -= half_px_y
                    y_max += half_px_y
            self.setRect(QtCore.QRectF(x_min, y_min, x_max - x_min, y_max - y_min))
        return

    def set_image(self, image=None, **kwargs):
        """
        pg.ImageItem method override to apply optional filter when setting image data.
        """
        if image is not None:
            masked_image = np.ma.masked_invalid(image).compressed()
            if masked_image.size < 1:
                image = None

        if image is None:
            self.clear()
            return

        if self._percentiles is not None:
            min_value = np.percentile(masked_image, self._percentiles[0])
            max_value = np.percentile(masked_image, self._percentiles[1])
            kwargs['levels'] = (min_value, max_value)
        self.setImage(image=image, **kwargs)
        return

    def mouseClickEvent(self, ev):
        if not ev.double():
            pos = self.getViewBox().mapSceneToView(ev.scenePos())
            self.sigMouseClicked.emit(ev.button(), (pos.x(), pos.y()))
        return super().mouseClickEvent(ev)


class Scan2DPlotWidget(PlotWidget):
    """
    Extend the PlotWidget Class with more functionality used for qudi scan images.
    Supported features:
     - draggable/static crosshair with optional range and size constraints.
     - zoom feature by rubberband selection
     - signalling for rubberband area selection

    This class depends on the Scan2DViewBox class defined further below.
    This class can be promoted in the Qt designer.
    """
    sigMouseAreaSelected = QtCore.Signal(tuple, tuple)  # mapped mouse rubberband selection (x, y)

    def __init__(self, *args, **kwargs):
        kwargs['viewBox'] = Scan2DViewBox()  # Use custom pg.ViewBox subclass
        super().__init__(*args, **kwargs)
        self.getViewBox().sigMouseAreaSelected.connect(self.__translate_selection_rect)
        self.crosshairs = list()

    @property
    def selection_enabled(self):
        return bool(self.getViewBox().rectangle_selection)

    @property
    def zoom_by_selection_enabled(self):
        return bool(self.getViewBox().zoom_by_selection)

    def toggle_selection(self, enable):
        """
        De-/Activate the rectangular rubber band selection tool.
        If active you can select a rectangular region within the ViewBox by dragging the mouse
        with the left button. Each selection rectangle in real-world data coordinates will be
        emitted by sigMouseAreaSelected.
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

    def add_crosshair(self, *args, **kwargs):
        """
        Add a crosshair to this Scan2DPlotWidget.
        You can pass all optional parameters you can pass to ScanCrosshair.__init__
        The stacking of crosshairs will be in order of insertion (last added crosshair is on top).
        Keep stacking in mind when you want to have a draggable crosshair.
        """
        # Create new ScanCrosshair instance and add to crosshairs list
        self.crosshairs.append(ScanCrosshair(self, *args, **kwargs))
        # Add crosshair to ViewBox
        self.show_crosshair(-1)
        return

    def remove_crosshair(self, index=-1):
        """
        Remove the crosshair at position <index> or the last one added (default) from this
        Scan2DPlotWidget.
        """
        crosshair = self.crosshairs.pop(index)
        # Remove crosshair from ViewBox
        crosshair.remove_from_view()
        crosshair.deleteLater()
        return

    def hide_crosshair(self, index=-1):
        self.crosshairs[index].remove_from_view()
        return

    def show_crosshair(self, index=-1):
        self.crosshairs[index].add_to_view()
        return

    def bring_crosshair_on_top(self, index):
        """

        @param index:
        """
        crosshair = self.crosshairs[index]
        crosshair.vline.setZValue(10)
        crosshair.hline.setZValue(10)
        crosshair.crosshair.setZValue(11)
        return

    @QtCore.Slot(QtCore.QRectF)
    def __translate_selection_rect(self, rect):
        tmp_x = (rect.left(), rect.right())
        tmp_y = (rect.top(), rect.bottom())
        x_limits = min(tmp_x), max(tmp_x)
        y_limits = min(tmp_y), max(tmp_y)
        self.sigMouseAreaSelected.emit(x_limits, y_limits)


class Scan2DViewBox(ViewBox):
    """
    Extension for pg.ViewBox to be used with Scan2DPlotWidget.

    Implements optional rectangular rubber band area selection and optional corresponding zooming.
    """

    sigMouseAreaSelected = QtCore.Signal(QtCore.QRectF)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.zoom_by_selection = False
        self.rectangle_selection = False
        return

    def toggle_selection(self, enable):
        """
        De-/Activate the rectangular rubber band selection tool.
        If active you can select a rectangular region within the ViewBox by dragging the mouse
        with the left button. Each selection rectangle in real-world data coordinates will be
        emitted by sigMouseAreaSelected.
        By using toggle_zoom_by_selection you can optionally de-/activate zooming in on the
        selection.

        @param bool enable: Toggle selection on (True) or off (False)
        """
        self.rectangle_selection = bool(enable)
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
        Additional mouse drag event handling to implement rubber band selection and zooming.
        """
        if self.rectangle_selection and ev.button() == QtCore.Qt.LeftButton:
            ev.accept()
            self.updateScaleBox(ev.buttonDownPos(), ev.pos())
            if ev.isFinish():
                self.rbScaleBox.hide()
                start = self.mapToView(ev.buttonDownPos())
                stop = self.mapToView(ev.pos())
                rect = QtCore.QRectF(start, stop)
                if self.zoom_by_selection:
                    # AutoRange needs to be disabled by hand because of a pyqtgraph bug.
                    if self.autoRangeEnabled():
                        self.disableAutoRange()
                    self.setRange(rect=rect, padding=0)
                self.sigMouseAreaSelected.emit(rect)
            return
        else:
            return super().mouseDragEvent(ev, axis)


class ScanCrosshair(QtCore.QObject):
    """
    Represents a crosshair (two perpendicular infinite lines and optionally a rectangle around the
    intersection) to be used in Scan2DPlotWidget.

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

    sigPositionChanged = QtCore.Signal(float, float)
    sigPositionDragged = QtCore.Signal(float, float)
    sigDragStarted = QtCore.Signal()
    sigDragFinished = QtCore.Signal(float, float)

    def __init__(self, parent, position=None, size=None, min_size_factor=None, allowed_range=None,
                 movable=None, pen=None, hover_pen=None):
        super().__init__(parent=parent)
        self._min_size_factor = 0.02
        self._size = (0, 0)
        self._allowed_range = None
        self.__is_dragged = False

        self.crosshair = ROI((0, 0),
                             (0, 0),
                             pen=self._default_pen if pen is None else pen)
        self.hline = InfiniteLine(pos=0,
                                  angle=0,
                                  movable=False,
                                  pen=self._default_pen,
                                  hoverPen=self._default_hover_pen)
        self.vline = InfiniteLine(pos=0,
                                  angle=90,
                                  movable=False,
                                  pen=self._default_pen,
                                  hoverPen=self._default_hover_pen)

        self.parent().sigRangeChanged.connect(self._constraint_size)
        self.vline.sigDragged.connect(self._update_pos_from_line)
        self.vline.sigPositionChangeFinished.connect(self._finish_drag)
        self.hline.sigDragged.connect(self._update_pos_from_line)
        self.hline.sigPositionChangeFinished.connect(self._finish_drag)
        self.crosshair.sigRegionChanged.connect(self._update_pos_from_roi)
        self.crosshair.sigRegionChangeFinished.connect(self._finish_drag)
        self.sigPositionDragged.connect(self.sigPositionChanged)

        if pen is not None:
            self.set_pen(pen)
        if hover_pen is not None:
            self.set_hover_pen(hover_pen)
        if min_size_factor is not None:
            self.set_min_size_factor(min_size_factor)
        if allowed_range is not None:
            self.set_allowed_range(allowed_range)
        if size is not None:
            self.set_size(size)
        if position is not None:
            self.set_position(position)
        if movable is not None:
            self.set_movable(movable)

    @property
    def movable(self):
        return bool(self.crosshair.translatable)

    @property
    def position(self):
        return self.vline.pos()[0], self.hline.pos()[1]

    @property
    def size(self):
        return tuple(self._size)

    @property
    def min_size_factor(self):
        return float(self._min_size_factor)

    @property
    def allowed_range(self):
        if self._allowed_range is None:
            return None
        return tuple(self._allowed_range)

    def _update_pos_from_line(self, obj=None):
        """
        Called each time the position of the InfiniteLines has been changed by a user drag.
        Causes the crosshair rectangle to follow the lines.
        """
        x = self.vline.pos()[0]
        y = self.hline.pos()[1]
        size = self.crosshair.size()
        if not self.__is_dragged:
            self.__is_dragged = True
            self.sigDragStarted.emit()
        self.crosshair.blockSignals(True)
        self.crosshair.setPos((x - size[0] / 2, y - size[1] / 2))
        self.crosshair.blockSignals(False)
        self.sigPositionDragged.emit(x, y)
        return

    def _update_pos_from_roi(self, obj=None):
        """
        Called each time the position of the rectangular ROI has been changed by a user drag.
        Causes the InfiniteLines to follow the ROI.
        """
        pos = self.crosshair.pos()
        size = self.crosshair.size()
        x = pos[0] + size[0] / 2
        y = pos[1] + size[1] / 2
        if not self.__is_dragged:
            self.__is_dragged = True
            self.sigDragStarted.emit()
        self.vline.setPos(x)
        self.hline.setPos(y)
        self.sigPositionDragged.emit(x, y)
        return

    def _finish_drag(self):
        if self.__is_dragged:
            self.__is_dragged = False
            self.sigDragFinished.emit(*self.position)
        return

    def _constraint_size(self):
        if self._min_size_factor == 0:
            return
        if self._size[0] == 0 or self._size[1] == 0:
            return
        corr_size = self._get_corrected_size(self._size)
        if corr_size != tuple(self.crosshair.size()):
            self.set_size(corr_size, set_as_default=False)
        return

    def _get_corrected_size(self, size):
        try:
            size = tuple(size)
        except TypeError:
            size = (size.width(), size.height())

        min_size = min(size)
        if min_size > 0:
            vb_size = self.parent().viewRect()
            print(vb_size)
            min_vb_size = min(abs(vb_size.width()), abs(vb_size.height()))
            min_vb_size *= self._min_size_factor

            if min_size < min_vb_size:
                scale_factor = min_vb_size / min_size
                size = (size[0] * scale_factor, size[1] * scale_factor)
        return size

    def add_to_view(self):
        view = self.parent()
        if self.vline not in view.items():
            view.addItem(self.vline)
            view.addItem(self.hline)
            view.addItem(self.crosshair)

    def remove_from_view(self):
        view = self.parent()
        if self.vline in view.items():
            view.removeItem(self.vline)
            view.removeItem(self.hline)
            view.removeItem(self.crosshair)

    def set_movable(self, movable):
        """
        (Un-)Set the crosshair movable (draggable by mouse cursor).

        @param bool movable: Set the crosshair movable (True) or not (False)
        """
        self.crosshair.translatable = bool(movable)
        self.vline.setMovable(movable)
        self.hline.setMovable(movable)
        return

    def set_position(self, pos):
        """
        Set the crosshair center to the given coordinates.

        @param QPointF|float[2] pos: (x,y) position of the crosshair
        """
        try:
            pos = tuple(pos)
        except TypeError:
            pos = (pos.x(), pos.y())
        size = self.crosshair.size()

        self.crosshair.blockSignals(True)
        self.vline.blockSignals(True)
        self.hline.blockSignals(True)
        self.crosshair.setPos(pos[0] - size[0] / 2, y=pos[1] - size[1] / 2)
        self.vline.setPos(pos[0])
        self.hline.setPos(pos[1])
        self.crosshair.blockSignals(False)
        self.vline.blockSignals(False)
        self.hline.blockSignals(False)
        self.sigPositionChanged.emit(*pos)
        return

    def set_size(self, size, set_as_default=True):
        """
        Set the (optionally default) size of the crosshair rectangle (x, y) and update the display.

        @param QSize|float[2] size: the (x,y) size of the crosshair rectangle
        @param bool set_as_default: Set default crosshair size and enforce minimal size (True).
                                    Enforce displayed crosshair size while keeping default size
                                    untouched (False).
        """
        try:
            size = tuple(size)
        except TypeError:
            size = (size.width(), size.height())

        if set_as_default:
            if size[0] <= 0 and size[1] <= 0:
                self._size = (0, 0)
            else:
                self._size = size
                # Check if actually displayed size needs to be adjusted due to minimal size
                size = self._get_corrected_size(size)

        pos = self.vline.pos()
        pos[1] = self.hline.pos()[1] - size[1] / 2
        pos[0] -= size[0] / 2

        if self._allowed_range:
            crange = self._allowed_range
            self.crosshair.maxBounds = QtCore.QRectF(crange[0][0] - size[0] / 2,
                                                     crange[1][0] - size[1] / 2,
                                                     crange[0][1] - crange[0][0] + size[0],
                                                     crange[1][1] - crange[1][0] + size[1])
        self.crosshair.blockSignals(True)
        self.crosshair.setSize(size)
        self.crosshair.setPos(pos)
        self.crosshair.blockSignals(False)
        return

    def set_min_size_factor(self, factor):
        """
        Sets the minimum crosshair size factor. This will determine the minimum size of the
        smallest edge of the crosshair center rectangle.
        This minimum size is calculated by taking the smallest visible axis of the ViewBox and
        multiplying it with the scale factor set by this method.
        The crosshair rectangle will be then scaled accordingly if the set crosshair size is
        smaller than this minimal size.

        @param float factor: The scale factor to set. If <= 0 no minimal crosshair size enforced.
        """
        if factor <= 0:
            self._min_size_factor = 0
        elif factor <= 1:
            self._min_size_factor = float(factor)
        else:
            raise ValueError('Crosshair min size factor must be a value <= 1.')
        return

    def set_allowed_range(self, new_range):
        """
        Sets a range boundary for the crosshair position.

        @param float[2][2] new_range: two min-max range value tuples (for x and y axis).
                                      If None set unlimited ranges.
        """
        if new_range is None:
            self.vline.setBounds([None, None])
            self.hline.setBounds([None, None])
            self.crosshair.maxBounds = None
        else:
            self.vline.setBounds(new_range[0])
            self.hline.setBounds(new_range[1])
            size = self.crosshair.size()
            pos = self.position
            self.crosshair.maxBounds = QtCore.QRectF(new_range[0][0] - size[0] / 2,
                                                     new_range[1][0] - size[1] / 2,
                                                     new_range[0][1] - new_range[0][0] + size[0],
                                                     new_range[1][1] - new_range[1][0] + size[1])
            self.crosshair.setPos(pos[0] - size[0] / 2, pos[1] - size[1] / 2)
        self._allowed_range = new_range
        return

    def set_pen(self, pen):
        """
        Sets the pen to be used for drawing the crosshair lines.
        Given parameter must be compatible with pyqtgraph.mkPen()

        @param pen: pyqtgraph compatible pen to use
        """
        self.crosshair.setPen(pen)
        self.vline.setPen(pen)
        self.hline.setPen(pen)
        return

    def set_hover_pen(self, pen):
        """
        Sets the pen to be used for drawing the crosshair lines when the mouse cursor is hovering
        over them.
        Given parameter must be compatible with pyqtgraph.mkPen()

        @param pen: pyqtgraph compatible pen to use
        """
        # self.crosshair.setPen(pen)
        self.vline.setHoverPen(pen)
        self.hline.setHoverPen(pen)
        return


class Scan2DWidget(QtWidgets.QWidget):
    """
    Extend the PlotWidget Class with more functionality used for qudi scan images.
    Supported features:
     - draggable/static crosshair with optional range and size constraints.
     - zoom feature by rubberband selection
     - signalling for rubberband area selection

    This class depends on the Scan2DViewBox class defined further below.
    This class can be promoted in the Qt designer.
    """
    sigScanToggled = QtCore.Signal(bool)

    # Wrapped attribute names from Scan2DPlotWidget and ScanImageItem objects.
    # Adjust these sets if Scan2DPlotWidget or ScanImageItem class changes.
    __plot_widget_wrapped = frozenset(
        {'selection_enabled', 'zoom_by_selection_enabled', 'toggle_selection',
         'toggle_zoom_by_selection', 'add_crosshair', 'remove_crosshair', 'hide_crosshair',
         'show_crosshair', 'bring_crosshair_on_top', 'crosshairs', 'sigMouseAreaSelected',
         'autoRange'}
    )
    __image_item_wrapped = frozenset({'set_image_extent', 'sigMouseClicked'})

    def __init__(self, *args, channel_units, scan_icon=None, **kwargs):
        super().__init__(*args, **kwargs)

        self._channel_units = channel_units.copy()
        self._image_data = dict()  # in case of multichannel data, save a reference here

        layout = QtWidgets.QGridLayout()
        layout.setColumnStretch(1, 2)
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

        self._plot_widget = Scan2DPlotWidget()
        self._image_item = ScanImageItem()
        self._plot_widget.addItem(self._image_item)
        self._plot_widget.setMinimumWidth(100)
        self._plot_widget.setMinimumHeight(100)
        self._plot_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                        QtWidgets.QSizePolicy.Expanding)
        self._plot_widget.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self._plot_widget.setAspectLocked(lock=True, ratio=1.0)
        layout.addWidget(self._plot_widget, 1, 0, 1, 2)

        self._colorbar_widget = ColorBarWidget()
        layout.addWidget(self._colorbar_widget, 1, 2)

        if self._colorbar_widget.mode is ColorBarMode.PERCENTILE:
            self._image_item.percentiles = self._colorbar_widget.percentiles
        else:
            self._image_item.percentiles = None

        self._colorbar_widget.sigModeChanged.connect(self.__colorbar_mode_changed)
        self._colorbar_widget.sigLimitsChanged.connect(self.__colorbar_limits_changed)
        self._colorbar_widget.sigPercentilesChanged.connect(self.__colorbar_percentiles_changed)
        self._channel_selection_combobox.currentIndexChanged.connect(self.__channel_changed)
        self._toggle_scan_button.clicked[bool].connect(self.sigScanToggled)

    def __getattr__(self, name):
        if name in self.__plot_widget_wrapped:
            return getattr(self._plot_widget, name)
        elif name in self.__image_item_wrapped:
            return getattr(self._image_item, name)
        raise AttributeError('No attribute "{0}" found in Scan2DWidget object.'.format(name))

    def set_data_channels(self, channel_units):
        if channel_units is None:
            self._channel_units = dict()
            self._channel_selection_combobox.setVisible(False)
            self._channel_selection_combobox.blockSignals(True)
            self._channel_selection_combobox.clear()
            self._channel_selection_combobox.setVisible(False)
            self._channel_selection_combobox.blockSignals(False)
            self._image_item.set_image(image=None, autoLevels=False)
            self._image_data = dict()
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
                channel = self._channel_selection_combobox.currentText()
                self.set_data_label(channel, unit=self._channel_units[channel])
                self._image_item.set_image(image=None, autoLevels=False)
                self._image_data = dict()
        else:
            raise ValueError('name_to_unit_map must be non-empty dict or None')
        return

    def set_scan_data(self, data):
        """

        """
        if data is None:
            self._image_item.set_image(image=None, autoLevels=False)
            self._image_data = dict()
            return

        if isinstance(data, dict):
            self._image_data = data.copy()
            channel = self._channel_selection_combobox.currentText()
            if channel not in self._image_data:
                self._image_item.set_image(image=None, autoLevels=False)
                return
            image = self._image_data[channel]
        else:
            raise TypeError(
                'Scan data must be dict with keys as channel names and values as 2D numpy arrays'
            )

        # Set image with proper colorbar limits
        if self._colorbar_widget.mode is ColorBarMode.PERCENTILE:
            self._image_item.set_image(image=image, autoLevels=False)
            levels = self._image_item.levels
            if levels is not None:
                self._colorbar_widget.set_limits(*levels)
        else:
            self._image_item.set_image(image=image,
                                      autoLevels=False,
                                      levels=self._colorbar_widget.limits)
        return

    def set_axis_label(self, axis, label=None, unit=None):
        return self._plot_widget.setLabel(axis, text=label, units=unit)

    def set_data_label(self, label, unit=None):
        return self._colorbar_widget.set_label(label, unit)

    @QtCore.Slot(bool)
    def toggle_scan(self, enable):
        if enable != self._toggle_scan_button.isChecked():
            self._toggle_scan_button.setChecked(enable)

    @QtCore.Slot(bool)
    def toggle_enabled(self, enable):
        if enable != self._toggle_scan_button.isEnabled():
            self._toggle_scan_button.setEnabled(enable)

    @QtCore.Slot(object)
    def __colorbar_mode_changed(self, mode):
        if mode is ColorBarMode.PERCENTILE:
            self.__colorbar_percentiles_changed(self._colorbar_widget.percentiles)
        else:
            self.__colorbar_limits_changed(self._colorbar_widget.limits)

    @QtCore.Slot(tuple)
    def __colorbar_limits_changed(self, limits):
        self._image_item.percentiles = None
        self._image_item.setLevels(limits)

    @QtCore.Slot(tuple)
    def __colorbar_percentiles_changed(self, percentiles):
        self._image_item.percentiles = percentiles
        levels = self._image_item.levels
        if levels is not None:
            self._colorbar_widget.set_limits(*levels)

    @QtCore.Slot()
    def __channel_changed(self):
        channel = self._channel_selection_combobox.currentText()
        channel_unit = self._channel_units.get(channel, '')
        self.set_data_label(channel, unit=channel_unit)
        image = self._image_data.get(channel, None)
        if image is not None:
            if self._colorbar_widget.mode is ColorBarMode.PERCENTILE:
                self._image_item.set_image(image=image, autoLevels=False)
                levels = self._image_item.levels
                if levels is not None:
                    self._colorbar_widget.set_limits(*levels)
            else:
                self._image_item.set_image(image=image,
                                          autoLevels=False,
                                          levels=self._colorbar_widget.limits)
        return
