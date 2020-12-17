# -*- coding: utf-8 -*-

"""
This file contains custom QWidgets to show (animated) loading indicators.

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

from qtpy import QtWidgets, QtCore, QtGui


class CircleLoadingIndicator(QtWidgets.QWidget):
    """ Simple circular loading indicator.
    You can customize cycle period, indicator arc length and width.
    Animation will automatically start (stop) upon showing (hiding) the widget.
    The widget can be arbitrarily resized but the actual indicator will always maintain 1:1 aspect
    ratio and will be centered.
    The color of the indicator is chosen to be the current palette highlight color.

    Indicator length must be specified as integer value in 1/16th of a degree.
    Indicator width ratio can be any value 0 < x <= 0.5
    """

    def __init__(self, *args, cycle_time=1.2, indicator_length=960, indicator_width_ratio=0.2,
                 **kwargs):
        """
        @param float cycle_time: The animation time in seconds for a full cycle
        @param int indicator_length: Length of the indicator arc in 1/16th of a degree
        @param float indicator_width_ratio: Ratio of the indicator arc width WRT widget size
        """
        assert cycle_time > 0, 'cycle_time must be larger than 0'
        assert 0 < indicator_length < 5760, 'indicator_length must be >0 and <5760'
        assert 0 < indicator_width_ratio <= 0.5, 'indicator_width_ratio must be >0 and <=0.5'
        super().__init__(*args, **kwargs)
        self.setMinimumSize(6, 6)
        self.setMouseTracking(False)
        self.setFocusPolicy(QtCore.Qt.NoFocus)

        # Fixed init parameters
        self._indicator_length = indicator_length
        self._cycle_time_ms = int(round(1000 * cycle_time))
        self._indicator_width_ratio = indicator_width_ratio

        # property value (angle in 1/16th of a degree) for current indicator position.
        # 0 means 3 o'clock.
        self._indicator_position = 0

        # misc parameters
        self.__animation = None
        self.__pen = QtGui.QPen(self.palette().highlight().color())
        self.__pen.setCapStyle(QtCore.Qt.RoundCap)
        self.__draw_rect = None
        self.__update_draw_size()
        self.__size_hint = None
        self.__update_size_hint()

    @QtCore.Property(int)
    def indicator_position(self):
        return self._indicator_position

    @indicator_position.setter
    def indicator_position(self, value):
        self._indicator_position = value
        self.update()

    def sizeHint(self):
        return self.__size_hint

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.__update_draw_size()
        self.__update_size_hint()

    def paintEvent(self, event):
        # Set up painter
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setBrush(QtCore.Qt.NoBrush)
        self.__pen.setColor(self.palette().highlight().color())  # in case the palette has changed
        p.setPen(self.__pen)

        # draw indicator
        p.drawArc(self.__draw_rect, self._indicator_position, self._indicator_length)

    def showEvent(self, ev):
        super().showEvent(ev)
        if self.__animation is None:
            self.__animation = QtCore.QPropertyAnimation(self, b'indicator_position', self)
            self.__animation.setDuration(self._cycle_time_ms)
            self.__animation.setStartValue(0)
            self.__animation.setEndValue(-5760)
            self.__animation.setLoopCount(-1)
            self.__animation.start()

    def hideEvent(self, ev):
        if self.__animation is not None:
            self.__animation.stop()
            self.__animation = None
        super().hideEvent(ev)

    def __update_draw_size(self):
        width = self.width()
        height = self.height()
        if height > width:
            x_offset = 0
            y_offset = (height - width) // 2
            base_size = width
        else:
            x_offset = (width - height) // 2
            y_offset = 0
            base_size = height
        line_width = max(1, int(round(base_size * self._indicator_width_ratio)))
        margin = max(1, line_width // 2)
        size = base_size - 2 * margin
        self.__draw_rect = QtCore.QRect(x_offset + margin, y_offset + margin, size, size)
        self.__pen.setWidth(line_width)

    def __update_size_hint(self):
        self.__size_hint = QtCore.QSize(min(self.width(), self.height()),
                                        min(self.width(), self.height()))
