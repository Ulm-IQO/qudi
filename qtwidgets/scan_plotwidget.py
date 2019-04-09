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

from pyqtgraph import PlotWidget, ImageItem, ViewBox, InfiniteLine, ROI
from qtpy import QtCore
from core.util.filters import scan_blink_correction

__all__ = ['ScanImageItem', 'ScanPlotWidget', 'ScanViewBox']


class ScanImageItem(ImageItem):
    """
    Extension of pg.ImageItem to display scanning microscopy images.
    Adds the signal sigMouseClicked to tap into mouse click events and receive the real world data
    coordinate of the click.
    Adds blink correction functionality capable of filtering out single pixel wide artifacts along
    a single image dimension.
    """
    sigMouseClicked = QtCore.Signal(QtCore.Qt.MouseButton, QtCore.QPointF)
    sigCrosshairPosChanged = QtCore.Signal(QtCore.QPointF)
    sigCrosshairDraggedPosChanged = QtCore.Signal(QtCore.QPointF)

    def __init__(self, *args, **kwargs):
        self.use_blink_correction = False
        self.blink_correction_axis = 0
        self.orig_image = None
        super().__init__(*args, **kwargs)

        self.crosshair = ROI((0, 0), (0, 0), pen={'color': '#00ff00', 'width': 1})
        self.hline = InfiniteLine(pos=0,
                                  angle=0,
                                  movable=True,
                                  pen={'color': '#00ff00', 'width': 1},
                                  hoverPen={'color': '#ffff00', 'width': 1})
        self.vline = InfiniteLine(pos=0,
                                  angle=90,
                                  movable=True,
                                  pen={'color': '#00ff00', 'width': 1},
                                  hoverPen={'color': '#ffff00', 'width': 1})
        self.vline.sigDragged.connect(self._update_pos_from_line)
        self.hline.sigDragged.connect(self._update_pos_from_line)
        self.crosshair.sigRegionChanged.connect(self._update_pos_from_roi)
        self.sigCrosshairDraggedPosChanged.connect(self.sigCrosshairPosChanged)
        return

    @property
    def crosshair_movable(self):
        return bool(self.crosshair.translatable)

    @crosshair_movable.setter
    def crosshair_movable(self, movable):
        self.crosshair.translatable = bool(movable)
        return

    @property
    def crosshair_position(self):
        pos = self.vline.pos()
        pos[1] = self.hline.pos()[1]
        return tuple(pos)

    @property
    def crosshair_size(self):
        return tuple(self.crosshair.size())

    def _update_pos_from_line(self, obj):
        if obj not in (self.hline, self.vline):
            return
        pos = self.vline.pos()
        pos[1] = self.hline.pos()[1]
        size = self.crosshair_size
        self.crosshair.blockSignals(True)
        self.crosshair.setPos((pos[0] - size[0] / 2, pos[1] - size[1] / 2))
        self.crosshair.blockSignals(False)
        self.sigCrosshairDraggedPosChanged.emit(QtCore.QPointF(pos[0], pos[1]))
        return

    def _update_pos_from_roi(self, obj):
        if obj is not self.crosshair:
            return
        pos = self.crosshair.pos()
        size = self.crosshair.size()
        pos[0] += size[0] / 2
        pos[1] += size[1] / 2
        self.vline.setPos(pos[0])
        self.hline.setPos(pos[1])
        self.sigCrosshairDraggedPosChanged.emit(QtCore.QPointF(pos[0], pos[1]))
        return

    def toggle_crosshair(self, enable, movable=True):
        """

        @param bool enable:
        @param bool movable:
        """
        if not isinstance(enable, bool):
            raise TypeError('Positional argument "enable" must be bool type.')
        if not isinstance(movable, bool):
            raise TypeError('Optional argument "movable" must be bool type.')

        self.crosshair.translatable = movable
        self.vline.setMovable(movable)
        self.hline.setMovable(movable)

        vw = self.getViewWidget()
        vw_items = vw.items()
        if enable:
            if self.vline not in vw_items:
                vw.addItem(self.vline)
            if self.hline not in vw_items:
                vw.addItem(self.hline)
            if self.crosshair not in vw_items:
                vw.addItem(self.crosshair)
        else:
            if self.vline in vw_items:
                vw.removeItem(self.vline)
            if self.hline in vw_items:
                vw.removeItem(self.hline)
            if self.crosshair in vw_items:
                vw.removeItem(self.crosshair)
        return

    def set_crosshair_pos(self, pos):
        try:
            pos = (pos[0], pos[1])
        except TypeError:
            pos = (pos.x(), pos.y())
        size = self.crosshair.size()
        self.crosshair.blockSignals(True)
        self.vline.blockSignals(True)
        self.hline.blockSignals(True)
        self.crosshair.setPos(pos[0] - size[0] / 2, pos[1] - size[1] / 2)
        self.vline.setPos(pos[0])
        self.hline.setPos(pos[1])
        self.crosshair.blockSignals(False)
        self.vline.blockSignals(False)
        self.hline.blockSignals(False)
        self.sigCrosshairPosChanged.emit(QtCore.QPointF(*pos))
        return

    def set_crosshair_size(self, size):
        try:
            size = (size[0], size[1])
        except TypeError:
            size = (size.width(), size.height())
        pos = self.vline.pos()
        pos[1] = self.hline.pos()[1] - size[1] / 2
        pos[0] -= size[0] / 2
        self.crosshair.blockSignals(True)
        self.crosshair.setSize(size)
        self.crosshair.setPos(pos)
        self.crosshair.blockSignals(False)
        return

    def set_crosshair_pen(self, pen):
        self.crosshair.setPen(pen)
        self.vline.setPen(pen)
        self.hline.setPen(pen)
        return

    def set_image_extent(self, extent):
        if len(extent) != 2:
            raise TypeError('Image extent must be iterable of length 2.')
        if len(extent[0]) != 2 or len(extent[1]) != 2:
            raise TypeError('Image extent for each axis must be iterable of length 2.')
        x_min, x_max = sorted(extent[0])
        y_min, y_max = sorted(extent[1])
        self.setRect(QtCore.QRectF(x_min, y_min, x_max - x_min, y_max - y_min))
        return

    def activate_blink_correction(self, set_active, axis=0):
        """
        De-/Activates the blink correction filter.
        Can filter out single pixel wide artifacts along a single image dimension.

        @param bool set_active: activate (True) or deactivate (False) the filter
        @param int axis: Array dimension to apply the filter on (0 or 1)
        """
        set_active = bool(set_active)
        axis = int(axis)
        if self.use_blink_correction != set_active:
            self.blink_correction_axis = axis
            self.use_blink_correction = set_active
            if set_active:
                self.setImage(self.image, autoLevels=False)
            else:
                self.setImage(self.orig_image, autoLevels=False)
        elif axis != self.blink_correction_axis:
            self.blink_correction_axis = axis
            if self.use_blink_correction:
                self.setImage(self.orig_image, autoLevels=False)
        return

    def setImage(self, image=None, autoLevels=None, **kwargs):
        """
        pg.ImageItem method override to apply optional filter when setting image data.
        """
        if self.use_blink_correction:
            self.orig_image = image
            image = scan_blink_correction(image=image, axis=self.blink_correction_axis)
        return super().setImage(image=image, autoLevels=autoLevels, **kwargs)

    def mouseClickEvent(self, ev):
        if not ev.double():
            pos = self.getViewBox().mapSceneToView(ev.scenePos())
            self.sigMouseClicked.emit(ev.button(), pos)
        return super().mouseClickEvent(ev)


class ScanPlotWidget(PlotWidget):
    """
    Extend the PlotWidget Class with more functionality used for qudi scan images.

    This class can be promoted in the Qt designer. Here you can predefine or
    redefined all methods and class variables, which should be used in the
    Qt Designer before it will be loaded into the created ui file.
    """
    sigMouseAreaSelected = QtCore.Signal(QtCore.QRectF)  # mapped rectangle mouse cursor selection

    def __init__(self, *args, **kwargs):
        kwargs['viewBox'] = ScanViewBox()  # Use custom pg.ViewBox subclass
        super().__init__(*args, **kwargs)
        self.getViewBox().sigMouseAreaSelected.connect(self.sigMouseAreaSelected)

    def toggle_selection(self, enable):
        """
        De-/Activate the rectangular rubber band selection tool.
        If active you can select a rectangular region within the ViewBox by dragging the mouse
        with the left button. Each selection rectangle in real-world data coordinates will be
        emitted by sigMouseAreaSelected.
        By using activate_zoom_by_selection you can optionally de-/activate zooming in on the
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


class ScanViewBox(ViewBox):
    """
    Extension for pg.ViewBox to be used with ScanPlotWidget.

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
        By using activate_zoom_by_selection you can optionally de-/activate zooming in on the
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
