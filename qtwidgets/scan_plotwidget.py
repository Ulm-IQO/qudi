# -*- coding: utf-8 -*-

"""
This file contains the modified PlotWidget for Qudi.

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

from pyqtgraph import PlotWidget, ImageItem, ViewBox
from qtpy import QtCore


class ScanImageItem(ImageItem):
    """

    """
    sigMouseClicked = QtCore.Signal(QtCore.Qt.MouseButton, QtCore.QPointF)

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
        kwargs['viewBox'] = ScanViewBox()
        super().__init__(*args, **kwargs)
        self.getViewBox().sigMouseAreaSelected.connect(self.sigMouseAreaSelected)

    def activate_selection(self, set_active):
        self.getViewBox().activate_selection(set_active)
        return

    def activate_zoom_by_selection(self, set_active):
        self.getViewBox().activate_zoom_by_selection(set_active)
        return


class ScanViewBox(ViewBox):
    """

    """

    sigMouseAreaSelected = QtCore.Signal(QtCore.QRectF)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.zoom_by_selection = False
        self.rectangle_selection = False
        return

    def activate_selection(self, set_active):
        self.rectangle_selection = bool(set_active)
        return

    def activate_zoom_by_selection(self, set_active):
        self.zoom_by_selection = bool(set_active)
        return

    def mouseDragEvent(self, ev, axis=None):
        """

        @param ev:
        @param axis:
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
                    if self.autoRangeEnabled():
                        self.disableAutoRange()
                    self.setRange(rect=rect, padding=0)
                self.sigMouseAreaSelected.emit(rect)
            return
        else:
            return super().mouseDragEvent(ev, axis)
