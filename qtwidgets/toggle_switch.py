# -*- coding: utf-8 -*-
"""
This file contains a touch-like toggle switch.

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


class ToggleSwitch(QtWidgets.QAbstractButton):
    """ A mobile/touch inspired toggle switch to switch between two states.
    Using default settings, this switch will resize horizontally. If you want a fixed size switch,
    please set the horizontal size policy to Fixed.

    """

    def __init__(self, parent=None, off_state=None, on_state=None, thumb_track_ratio=1):
        assert off_state is None or isinstance(off_state, str), 'off_state must be str or None'
        assert on_state is None or isinstance(on_state, str), 'on_state must be str or None'
        super().__init__(parent=parent)

        # remember state names
        if off_state is None and on_state is None:
            self._state_names = None
        else:
            self._state_names = (off_state, on_state)

        # Get default track height from QLineEdit sizeHint if thumb_track_ratio <= 1
        # If thumb_track_ratio > 1 the QLineEdit height will serve as thumb diameter
        if thumb_track_ratio > 1:
            self._thumb_radius = int(round(QtWidgets.QLineEdit().sizeHint().height() / 2))
            self._track_radius = max(1, int(round(self._thumb_radius / thumb_track_ratio)))
            self._text_font = QtWidgets.QLabel().font()
        else:
            self._track_radius = int(round(QtWidgets.QLineEdit().sizeHint().height() / 2))
            self._thumb_radius = max(1, int(round(self._track_radius * thumb_track_ratio)))
        self._track_margin = max(0, self._thumb_radius - self._track_radius)
        self._thumb_origin = max(self._thumb_radius, self._track_radius)

        # Determine appearance from current palette depending on thumb style
        palette = self.palette()
        if thumb_track_ratio > 1:
            self._track_colors = (palette.dark(), palette.highlight())
            self._thumb_colors = (palette.light(), palette.highlight())
            self._text_colors = (palette.text().color(), palette.highlightedText().color())
            self._track_opacity = 0.5
        else:
            self._track_colors = (palette.dark(), palette.highlight())
            self._thumb_colors = (palette.light(), palette.highlightedText())
            self._text_colors = (palette.text().color(), palette.highlightedText().color())
            self._track_opacity = 1
        self._text_font = QtGui.QFont()
        # self._text_font.setBold(True)
        self._text_font.setPixelSize(1.5 * self._track_radius)

        # property value for current thumb position
        self._thumb_position = self._thumb_origin

        self.setCheckable(True)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        if self._state_names is None or thumb_track_ratio > 1:
            self._text_width = 0
        else:
            metrics = QtGui.QFontMetrics(self._text_font)
            self._text_width = max(metrics.width(f' {text} ') for text in self._state_names if text)
        self._size_hint = QtCore.QSize(
            4 * self._track_radius + 2 * self._track_margin + self._text_width,
            2 * self._track_radius + 2 * self._track_margin
        )
        self.setMinimumSize(self._size_hint)

    @property
    def current_state(self):
        return self._state_names[int(self.isChecked())] if self._state_names else None

    @property
    def _thumb_end(self):
        return self.width() - self._thumb_origin if self.isChecked() else self._thumb_origin

    @property
    def _track_color(self):
        return self._track_colors[int(self.isChecked())]

    @property
    def _thumb_color(self):
        return self._thumb_colors[int(self.isChecked())]

    @property
    def _text_color(self):
        return self._text_colors[int(self.isChecked())]

    @QtCore.Property(int)
    def thumb_position(self):
        return self._thumb_position

    @thumb_position.setter
    def thumb_position(self, value):
        self._thumb_position = value
        self.update()

    def sizeHint(self):
        return self._size_hint

    def setChecked(self, checked):
        super().setChecked(checked)
        self._thumb_position = self._thumb_end

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.thumb_position = self._thumb_end

    def paintEvent(self, event):
        # Set up painter
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setPen(QtCore.Qt.NoPen)
        track_opacity = self._track_opacity
        if self.isEnabled():
            track_brush = self._track_color
            thumb_brush = self._thumb_color
            text_color = self._text_color
        else:
            palette = self.palette()
            track_opacity *= 0.8
            track_brush = palette.shadow()
            thumb_brush = palette.mid()
            text_color = palette.shadow().color()

        # draw track
        p.setBrush(track_brush)
        p.setOpacity(track_opacity)
        p.drawRoundedRect(self._track_margin,
                          self.height()/2 - self._track_radius,
                          self.width() - 2 * self._track_margin,
                          2 * self._track_radius,
                          self._track_radius,
                          self._track_radius)
        # draw text if necessary
        state_str = self.current_state
        if state_str is not None and self._track_margin == 0:
            p.setPen(text_color)
            p.setOpacity(1.0)
            p.setFont(self._text_font)
            p.drawText(self._track_margin,
                       self.height() / 2 - self._track_radius,
                       self.width() - 2 * self._track_margin,
                       2 * self._track_radius,
                       QtCore.Qt.AlignCenter,
                       state_str)
        # draw thumb
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(thumb_brush)
        p.setOpacity(1.0)
        p.drawEllipse(self._thumb_position - self._thumb_radius,
                      self.height()/2 - self._thumb_radius,
                      2 * self._thumb_radius,
                      2 * self._thumb_radius)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            anim = QtCore.QPropertyAnimation(self, b'thumb_position', self)
            anim.setDuration(200)
            anim.setStartValue(self._thumb_position)
            anim.setEndValue(self._thumb_end)
            anim.start()

    def enterEvent(self, event):
        self.setCursor(QtCore.Qt.PointingHandCursor)
        super().enterEvent(event)
