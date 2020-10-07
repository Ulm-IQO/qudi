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

Derived form ACQ4:
Copyright 2010  Luke Campagnola
Originally distributed under MIT/X11 license. See documentation/MITLicense.txt for more infomation.
"""

import traceback
from datetime import datetime
from collections import deque
from qudi.core.util.mutex import RecursiveMutex
from PySide2 import QtWidgets, QtCore


class ErrorDialog(QtWidgets.QDialog):
    """This class provides a popup window for notification with the option to
      show the next error popup in the queue and to show the log window where
      you can see the traceback for an exception.
    """

    def __init__(self, parent=None):
        """ Create an ErrorDialog object

        @param object log_window: reference to log_window object that this popup belongs to
        """
        super().__init__(parent)

        self._thread_lock = RecursiveMutex()
        self._error_queue = deque()  # queued individual error messages to display

        # Set up dialog window
        self.setWindowTitle('Qudi Error')
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowStaysOnTopHint)
        screen_size = QtWidgets.QApplication.instance().primaryScreen().availableSize()
        screen_width = screen_size.width()
        screen_height = screen_size.height()
        self.setGeometry((screen_width * 3) // 8,
                         (screen_height * 3) // 8,
                         screen_width // 4,
                         screen_height // 4)
        self.setMinimumSize(screen_width // 6, screen_height // 8)

        # Set up message label widget
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.msg_label = QtWidgets.QLabel()
        self.msg_label.setWordWrap(True)
        self.msg_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                     QtWidgets.QSizePolicy.Expanding)
        scroll_area.setWidget(self.msg_label)

        # Set up disable checkbox
        self.disable_checkbox = QtWidgets.QCheckBox('Disable error message popups')

        # Set up buttons and group them in a layout
        self.dismiss_button = QtWidgets.QPushButton('Dismiss')
        self.next_button = QtWidgets.QPushButton('Show next error')
        self.log_button = QtWidgets.QPushButton('Show log...')
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.dismiss_button)
        btn_layout.addWidget(self.next_button)
        btn_layout.addWidget(self.log_button)
        # btn_layout.addStretch()
        # self.next_button.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
        #                                QtWidgets.QSizePolicy.Fixed)

        # Set up dialog main layout and add all widgets to it
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(3, 3, 3, 3)
        main_layout.addWidget(scroll_area)
        main_layout.addWidget(self.disable_checkbox)
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

        # Connect button click signals to slots
        self.dismiss_button.clicked.connect(self.accept)
        self.next_button.clicked.connect(self.show_next_error)
        self.log_button.clicked.connect(self.log_clicked)

    @QtCore.Slot(object)
    def new_error(self, data):
        """ Show a new error log entry.

        @param logging.LogRecord data: log record as returned from logging module
        """
        with self._thread_lock:
            self._error_queue.append(data)
            self._update_next_button()
            if not self.isVisible():
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
                    message += '\n{0}'.format(traceback.format_exception(*err.exc_info)[-1][:-1])
                    tb = '\n'.join(traceback.format_exception(*err.exc_info)[:-1])
                    if tb:
                        message += '\n{0}'.format(tb)

                self.msg_label.setText(
                    'Error in {0} ({1}):\n\n{2}'.format(err.name, time_str, message)
                )
                if self.enabled:
                    self.show()
                    # self.raise_()
                    self.activateWindow()

    # def show(self, entry):
    #     """ Show a log entry in a popup window.
    #
    #     @param dict entry: log entry in dictionary form
    #     """
    #     # Return early if disabled
    #     if self.disabled:
    #         return
    #
    #     # extract list of exceptions
    #     exceptions = list()
    #     key = 'exception'
    #     exc = entry
    #     while key in exc:
    #         exc = exc[key]
    #         if exc is None:
    #             break
    #         # ignore this error if it was generated on the command line.
    #         tb = exc.get('traceback', ['', ''])
    #         if len(tb) > 1 and 'File "<stdin>"' in tb[1]:
    #             return
    #
    #         if exc is None:
    #             break
    #         key = 'oldExc'
    #         if exc['message'] == 'None':
    #             continue
    #         elif exc['message'].startswith('HelpfulException'):
    #             # FIXME: Should be possible to remove this case (not used in qudi)
    #             msg = exc['message'].lstrip('HelpfulException: ')
    #             exceptions.append('<b>{0}</b>'.format(self.clean_text(msg)))
    #         else:
    #             exceptions.append(self.clean_text(exc['message']))
    #
    #     msg = '<b>{0}</b><br>'.format(entry['message']) + '<br>'.join(exceptions)
    #
    #     if self.isVisible():
    #         self.messages.append(msg)
    #         self._update_next_button()
    #     else:
    #         w = QtWidgets.QApplication.activeWindow()
    #         self.msg_label.setText(msg)
    #         self.open()
    #         self._update_next_button()
    #         if w is not None:
    #             cp = w.geometry().center()
    #             self.setGeometry(cp.x() - self.width() // 2,
    #                              cp.y() - self.height() // 2,
    #                              self.width(),
    #                              self.height())
    #     self.raise_()
    #     self.activateWindow()

    @property
    def enabled(self):
        """ Property holding the enabled flag for this error message popup

        @return bool: Flag indicating enabled (True) or disabled (False) error message popups
        """
        return not self.disable_checkbox.isChecked()

    @QtCore.Slot(bool)
    def set_enabled(self, enable):
        self.disable_checkbox.setChecked(not bool(enable))

    # @staticmethod
    # def clean_text(text):
    #     """ Return a string with some special characters escaped for HTML.
    #
    #     @param str text: string to sanitize
    #     @return str: string with special characters replaced by HTML escape sequences
    #     """
    #     text = text.replace('&', '&amp;')
    #     text = text.replace('>', '&gt;')
    #     text = text.replace('<', '&lt;')
    #     return text.replace('\n', '<br/>\n')

    def closeEvent(self, ev):
        """ Specify close event action. Extends the parent class closeEvent handler to delete all
        pending messages.

        @param QEvent ev: event from event handler
        """
        self._error_queue.clear()
        return super().closeEvent(ev)

    @QtCore.Slot()
    def log_clicked(self):
        """ Marks messages as accepted and shows log window.
        """
        self.accept()
        self.parent().show()

    def _update_next_button(self):
        msg_number = len(self._error_queue) - 1
        self.next_button.setText('Show next error ({0:d} more)'.format(msg_number))
        self.next_button.setEnabled(msg_number > 0)
        return
