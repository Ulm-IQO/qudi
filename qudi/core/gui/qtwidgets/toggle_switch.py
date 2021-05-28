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

from PySide2 import QtWidgets, QtCore, QtGui


class ToggleSwitch(QtWidgets.QAbstractButton):
    """ A mobile/touch inspired toggle switch to switch between two states.
    """

    sigStateChanged = QtCore.Signal(str)

    def __init__(self, parent=None, state_names=None, thumb_track_ratio=1, scale_text=True,
                 display_text=True):
        super().__init__(parent=parent)
        self.setCheckable(True)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)

        # check state_names
        if state_names is None:
            self._state_names = None
        elif len(state_names) != 2 or not all(isinstance(n, str) and n != '' for n in state_names):
            raise ValueError(
                f'state_names must be None or sequence of exactly 2 non-empty strings. '
                f'Received: {state_names}'
            )
        else:
            self._state_names = tuple(state_names)
        # check thumb_track_ratio
        if thumb_track_ratio <= 0:
            raise ValueError(
                f'thumb_track_ratio must have a value > 0. Received: {thumb_track_ratio}'
            )
        self._thumb_track_ratio = thumb_track_ratio
        # check scale_text
        if not isinstance(scale_text, bool):
            raise ValueError(f'scale_text must be bool type. Received: {scale_text}')
        self._scale_text = scale_text
        # check display_text
        if not isinstance(display_text, bool):
            raise ValueError(f'display_text must be bool type. Received: {display_text}')
        self._display_text = display_text if self._state_names else False
        self.__display_text = self._display_text

        # Determine (minimal) size hint based on text to display
        self._default_text_size = None
        self._size_hint = None
        self._refresh_size_hint()

        # Calculate geometry for painting
        self._thumb_radius = 0
        self._track_radius = 0
        self._track_margin = 0
        self._thumb_origin = 0
        self._current_text_width = 0
        self._refresh_geometry()
        self._refresh_text_scale()

        # Determine appearance from current palette depending on thumb style
        palette = self.palette()
        if self._thumb_track_ratio > 1:
            self._track_colors = (palette.dark(), palette.highlight())
            self._thumb_colors = (palette.light(), palette.highlight())
            self._text_colors = (palette.text().color(), palette.highlightedText().color())
            self._track_opacity = 0.5
        else:
            self._track_colors = (palette.dark(), palette.highlight())
            self._thumb_colors = (palette.light(), palette.highlightedText())
            self._text_colors = (palette.text().color(), palette.highlightedText().color())
            self._track_opacity = 1

        # property value for current thumb position
        self._thumb_position = self._thumb_origin

        # Connect notifier signal
        self.clicked.connect(self._notify_state_change)

        # set up the animation
        self._slider_animation = QtCore.QPropertyAnimation(self, b'thumb_position', self)
        self._slider_animation.finished.connect(self._finish_animation)

    @QtCore.Slot()
    def _finish_animation(self):
        if self._thumb_position != self._thumb_end:
            self.setChecked(self.isChecked())

    def _refresh_size_hint(self):
        metrics = QtGui.QFontMetrics(self.font())
        if self._display_text:
            self._default_text_size = QtCore.QSize(
                max(metrics.horizontalAdvance(f' {text} ') for text in self._state_names),
                metrics.height()
            )
        else:
            self._default_text_size = QtCore.QSize(metrics.horizontalAdvance(' OFF '),
                                                   metrics.height())
        if self._thumb_track_ratio <= 1:
            height = self._default_text_size.height() * 1.5
        else:
            height = self._default_text_size.height() * 1.5 * self._thumb_track_ratio
        width = self._default_text_size.width() + 2 * height
        self._size_hint = QtCore.QSize(width, height)
        self.setMinimumSize(self._size_hint)

    def _refresh_text_scale(self):
        if not self._display_text:
            self._current_text_width = 0
            self.__display_text = False
            return

        if self._scale_text:
            # Determine current maximum height and width for text field
            max_height = int(round(1.5 * self._track_radius))
            if self._thumb_track_ratio > 1:
                max_width = int(round(self.width() - 4 * self._thumb_radius))
            else:
                max_width = int(round(self.width() - 4 * self._track_radius))
            # Return early if there is simply no space between thumb positions
            if max_width <= 0:
                self._current_text_width = 0
                self.__display_text = False
                return

            font = self.font()
            font.setPixelSize(max_height)
            metrics = QtGui.QFontMetrics(font)
            text_width = max(
                metrics.horizontalAdvance(f' {text} ') for text in self._state_names if text
            )
            if text_width > max_width:
                text_scale = max_width / text_width
                font.setPixelSize(max(1, int(round(max_height * text_scale))))
            super().setFont(font)

        metrics = QtGui.QFontMetrics(self.font())
        self._current_text_width = max(
            metrics.horizontalAdvance(f' {text} ') for text in self._state_names
        )
        self.__display_text = True

    def _refresh_geometry(self):
        # Calculate new size for track and thumb
        height = self.height()
        if self._thumb_track_ratio > 1:
            self._thumb_radius = height / 2
            self._track_radius = self._thumb_radius / self._thumb_track_ratio
        else:
            self._track_radius = height / 2
            self._thumb_radius = self._track_radius * self._thumb_track_ratio
        self._track_margin = max(0.0, self._thumb_radius - self._track_radius)
        self._thumb_origin = max(self._thumb_radius, self._track_radius)

    def setFont(self, new_font):
        super().setFont(new_font)
        self._refresh_size_hint()
        self._refresh_geometry()
        self._refresh_text_scale()
        self.update()

    @QtCore.Slot()
    def _notify_state_change(self):
        state = self.current_state
        self.sigStateChanged.emit(state if isinstance(state, str) else '')

    @property
    def current_state(self):
        is_checked = self.isChecked()
        return self._state_names[int(is_checked)] if self._state_names else is_checked

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

    @QtCore.Property(float)
    def thumb_position(self):
        return self._thumb_position

    @thumb_position.setter
    def thumb_position(self, value):
        self._thumb_position = value
        self.update()

    def sizeHint(self):
        return self._size_hint

    def minimumSizeHint(self):
        return self._size_hint

    def setChecked(self, checked):
        super().setChecked(checked)
        self._thumb_position = self._thumb_end

    def resizeEvent(self, event):
        self._refresh_geometry()
        self._refresh_text_scale()
        self.thumb_position = self._thumb_end
        event.accept()

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
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(track_brush)
        p.setOpacity(track_opacity)
        p.drawRoundedRect(self._track_margin,
                          max(0, self.height() / 2 - self._track_radius),
                          max(0, self.width() - 2 * self._track_margin),
                          2 * self._track_radius,
                          self._track_radius,
                          self._track_radius)

        # draw text if necessary
        if self.__display_text and self._current_text_width > 0:
            p.setPen(text_color)
            p.setOpacity(1.0)
            p.setFont(self.font())
            p.drawText(self._track_margin,
                       self.height() / 2 - self._track_radius,
                       self.width() - 2 * self._track_margin,
                       2 * self._track_radius,
                       QtCore.Qt.AlignCenter,
                       self.current_state)

        # draw thumb
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(thumb_brush)
        p.setOpacity(1.0)
        p.drawEllipse(self._thumb_position - self._thumb_radius,
                      int(round(self.height()/2 - self._thumb_radius)),
                      2 * self._thumb_radius,
                      2 * self._thumb_radius)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == QtCore.Qt.LeftButton:
            self._slider_animation.setDuration(200)
            self._slider_animation.setStartValue(self._thumb_position)
            self._slider_animation.setEndValue(self._thumb_end)
            self._slider_animation.start()

    def enterEvent(self, event):
        self.setCursor(QtCore.Qt.PointingHandCursor)
        super().enterEvent(event)
