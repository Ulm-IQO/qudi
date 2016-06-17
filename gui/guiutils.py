# -*- coding: utf-8 -*-

"""
This file contains the QuDi GUI module utility classes.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2015 
    Florian S. Frank florian.frank@uni-ulm.de
    Alexander Stark alexander.stark@uni-ulm.de
    Lachlan J. Rogers lachlan.j.rogers@quantum.diamonds
"""

import pyqtgraph as pg
import numpy as np

class ColorBar(pg.GraphicsObject):
    """ Create a ColorBar according to a previously defined color map.

    @param object pyqtgraph.ColorMap cmap: a defined colormap
    @param float width: width of the colorbar in x direction, starting from
                        the origin.
    @param numpy.array ticks: optional, definition of the relative ticks marks
    """

    def __init__(self, cmap, width, cb_min, cb_max):

        pg.GraphicsObject.__init__(self)

        # handle the passed arguments:
        self.stops, self.colors = cmap.getStops('float')
        self.stops = (self.stops - self.stops.min())/self.stops.ptp()
        self.width = width

        # Constructs an empty picture which can be altered by QPainter
        # commands. The picture is a serialization of painter commands to an IO
        # device in a platform-independent format.
        self.pic = pg.QtGui.QPicture()

        self.refresh_colorbar(cb_min, cb_max)

    def refresh_colorbar(self, cb_min, cb_max, width = None, height = None, xMin = None, yMin = None):
        """ Refresh the appearance of the colorbar for a changed count range.

        @param float cb_min: The minimal count value should be passed here.
        @param float cb_max: The maximal count value should be passed here.
        @param float width: optional, with that you can change the width of the
                            colorbar in the display.
        """

        if width is None:
            width = self.width
        else:
            self.width = width

#       FIXME: Until now, if you want to refresh the colorbar, a new QPainter
#              object has been created, but I think that it is not necassary.
#              I have to figure out how to use the created object properly.
        p = pg.QtGui.QPainter(self.pic)
        p.drawRect(self.boundingRect())
        p.setPen(pg.mkPen('k'))
        grad = pg.QtGui.QLinearGradient(width/2.0, cb_min*1.0, width/2.0, cb_max*1.0)
        for stop, color in zip(self.stops, self.colors):
            grad.setColorAt(1.0 - stop, pg.QtGui.QColor(*[255*c for c in color]))
        p.setBrush(pg.QtGui.QBrush(grad))
        if xMin is None:
            p.drawRect(pg.QtCore.QRectF(0, cb_min, width, cb_max-cb_min))
        else:
            # If this picture whants to be set in a plot, which is going to be
            # saved:
            p.drawRect(pg.QtCore.QRectF(xMin, yMin, width, height))
        p.end()

        vb = self.getViewBox()
        # check whether a viewbox is already created for this object. If yes,
        # then it should be adjusted according to the full screen.
        if vb is not None:
            vb.updateAutoRange()
            vb.enableAutoRange()

    def paint(self, p, *args):
        """ Overwrite the paint method from GraphicsObject.

        @param object p: a pyqtgraph.QtGui.QPainter object, which is used to
                         set the color of the pen.

        Since this colorbar object is in the end a GraphicsObject, it will
        drop an implementation error, since you have to write your own paint
        function for the created GraphicsObject.
        """
        # paint colorbar
        p.drawPicture(0, 0, self.pic)

    def boundingRect(self):
        """ Overwrite the paint method from GraphicsObject.

        Get the position, width and hight of the displayed object.
        """
        return pg.QtCore.QRectF(self.pic.boundingRect())

