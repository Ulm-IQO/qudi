# -*- coding: utf-8 -*-
"""
This file contains the Qudi error dialog class.

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

import traceback
from datetime import datetime
from collections import deque
from qudi.util.mutex import RecursiveMutex
from PySide2 import QtWidgets, QtCore


class ErrorDialog(QtWidgets.QDialog):
    """This class provides a popup window for notification with the option to
      show the next error popup in the queue and to show the log window where
      you can see the traceback for an exception.
    """

    _stylesheet_map = {'error'   : 'font-weight: bold; color: #F11000;',
                       'critical': 'font-weight: bold; color: #FF00FF;'}

    def __init__(self, *args, **kwargs):
        """ Create an ErrorDialog object
        """
        super().__init__(*args, **kwargs)

        self._thread_lock = RecursiveMutex()
        self._error_queue = deque()  # queued individual error messages to display

        # Set up dialog window
        self.setWindowTitle('Qudi Error')
        self.setWindowFlags((QtCore.Qt.Dialog |
                             QtCore.Qt.CustomizeWindowHint |
                             QtCore.Qt.WindowSystemMenuHint |
                             QtCore.Qt.WindowTitleHint) & (~QtCore.Qt.WindowCloseButtonHint))
        self.setModal(True)
        screen_size = QtWidgets.QApplication.instance().primaryScreen().availableSize()
        screen_width = screen_size.width()
        screen_height = screen_size.height()
        self._default_size = ((screen_width * 3) // 8,
                              (screen_height * 3) // 8,
                              screen_width // 4,
                              screen_height // 4)
        self.setGeometry(*self._default_size)
        self.setMinimumSize(screen_width // 6, screen_height // 8)

        # Set up header label widget
        self.header_label = QtWidgets.QLabel()
        self.header_label.setFocusPolicy(QtCore.Qt.NoFocus)
        self.header_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse | QtCore.Qt.LinksAccessibleByMouse
        )
        self.header_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                     QtWidgets.QSizePolicy.Preferred)

        # Set up scrollable message label widget
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFocusPolicy(QtCore.Qt.NoFocus)
        self.msg_label = QtWidgets.QLabel()
        self.msg_label.setFocusPolicy(QtCore.Qt.NoFocus)
        self.msg_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse | QtCore.Qt.LinksAccessibleByMouse
        )
        self.msg_label.setWordWrap(True)
        self.msg_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.msg_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                     QtWidgets.QSizePolicy.Expanding)
        scroll_area.setWidget(self.msg_label)

        # Set up disable checkbox
        self.disable_checkbox = QtWidgets.QCheckBox('Disable error message popups')

        # Set up buttons and group them in a layout
        self.dismiss_button = QtWidgets.QPushButton('Dismiss')
        self.next_button = QtWidgets.QPushButton('Show next error')
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.next_button)
        btn_layout.addWidget(self.dismiss_button)

        # Set up dialog main layout and add all widgets to it
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(3, 3, 3, 3)
        main_layout.addWidget(self.header_label)
        main_layout.addWidget(scroll_area)
        main_layout.addWidget(self.disable_checkbox)
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

        # Connect button click signals to slots
        self.dismiss_button.clicked.connect(self.accept)
        self.next_button.clicked.connect(self.show_next_error)
        self.accepted.connect(self._accepted_callback)

    @QtCore.Slot(object)
    def new_error(self, data):
        """ Show a new error log entry.

        @param logging.LogRecord data: log record as returned from logging module
        """
        with self._thread_lock:
            self._error_queue.append(data)
            if self.isVisible():
                self._update_next_button()
            else:
                self.setGeometry(*self._default_size)
                self.show_next_error()

    @QtCore.Slot()
    def show_next_error(self):
        with self._thread_lock:
            if len(self._error_queue) > 0:
                err = self._error_queue.popleft()
                self._update_next_button()
                time_str = datetime.fromtimestamp(err.created).strftime('%Y-%m-%d %H:%M:%S')
                message = err.message if hasattr(err, 'message') else err.msg
                if err.exc_info is not None:
                    message += '\n\n{0}'.format(traceback.format_exception(*err.exc_info)[-1][:-1])
                    tb = '\n'.join(traceback.format_exception(*err.exc_info)[:-1])
                    if tb:
                        message += '\n{0}'.format(tb)

                self.header_label.setStyleSheet(self._stylesheet_map[err.levelname])
                self.header_label.setText('Error in {0} ({1}):'.format(err.name, time_str))
                self.msg_label.setText(message)
                if self.enabled:
                    self.show()
                    self.activateWindow()

    @property
    def enabled(self):
        """ Property holding the enabled flag for this error message popup

        @return bool: Flag indicating enabled (True) or disabled (False) error message popups
        """
        with self._thread_lock:
            return not self.disable_checkbox.isChecked()

    @QtCore.Slot(bool)
    def set_enabled(self, enable):
        with self._thread_lock:
            self.disable_checkbox.setChecked(not bool(enable))

    @QtCore.Slot()
    def _accepted_callback(self):
        with self._thread_lock:
            self._error_queue.clear()

    def _update_next_button(self):
        with self._thread_lock:
            msg_number = len(self._error_queue)
            btn_enabled = self.next_button.isEnabled()
            self.next_button.setText('Show next error ({0:d} more)'.format(msg_number))
            if msg_number == 0 and btn_enabled:
                self.next_button.setEnabled(False)
                self.dismiss_button.setFocus()
            elif msg_number > 0 and not btn_enabled:
                self.next_button.setEnabled(True)
                self.next_button.setFocus()

    @QtCore.Slot()
    def reject(self):
        """ Override reject slot in order to prevent rejection of this QDialog.
        """
        if not self.dismiss_button.hasFocus():
            self.dismiss_button.setFocus()

