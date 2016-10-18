#!/usr/bin/env python3
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

from pyqtgraph import PlotWidget
from qtpy import QtCore
from qtpy import QtWidgets


class PlotWidgetModified(PlotWidget):
    """ Extend the PlotWidget Class with more adjustment possibilities.

    This class can be promoted in the Qt designer. Here you can predefine or
    redefined all methods and class variables, which should be used in the
    Qt Designer before it will be loaded into the created ui file.

    This class behaves like the normal PlotWidget class but extends its
    functionality with modified mouse events.
    """

    sigMouseClick = QtCore.Signal(object)
    sigMouseReleased = QtCore.Signal(object)

    def __init__(self, *args, **kargs):
        PlotWidget.__init__(self,**kargs)

    def mousePressEvent(self, ev):
        """ Override the Qt method, which handels mouse press events.

        @param QEvent ev: Event object which contains all the information at
                          the time the event was emitted.

        That is basically a reimplementation of the mouseReleaseEvent function
        of the PlotWidget.
        """

        # Extend the received event ev with all the properties of a Qt mouse
        # press event.
        QtWidgets.QGraphicsView.mousePressEvent(self, ev)

        # this signal will be catched by other methods if the mouse was clicked
        # inside the PlotWidget.
        self.sigMouseClick.emit(ev)

        if not self.mouseEnabled:
            return
        self.mousePressPos = ev.pos()
        self.clickAccepted = ev.isAccepted()

        if not self.clickAccepted:
            self.scene().clearSelection()
        return   ## Everything below disabled for now.


    def mouseReleaseEvent(self, ev):
        """ Override the Qt method, which handels mouse release events.

        @param QEvent ev: Event object which contains all the information at
                          the time the event was emitted.

        That is basically a reimplementation of the mouseReleaseEvent function
        of the PlotWidget.
        """
        # Extend the received event ev with all the properties of a Qt mouse
        # press event.
        QtWidgets.QGraphicsView.mouseReleaseEvent(self, ev)

        # this signal will be catched by other methods if the mouse was clicked
        # and afterwards release inside the PlotWidget.
        self.sigMouseReleased.emit(ev)
        if not self.mouseEnabled:
            return

        self.lastButtonReleased = ev.button()
        return   ## Everything below disabled for now.

