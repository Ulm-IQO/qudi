# -*- coding: utf-8 -*-
"""
This file contains the Qudi log window class.

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

from qtpy import QtWidgets, QtCore


class ErrorDialog(QtWidgets.QDialog):
    """This class provides a popup window for notification with the option to
      show the next error popup in the queue and to show the log window where
      you can see the traceback for an exception.
    """

    def __init__(self, log_window):
        """ Create an ErrorDialog object

        @param object log_window: reference to log_window object that this popup belongs to
        """
        super().__init__()

        self._log_window = log_window  # Save a reference to the log window
        self.messages = list()  # List of queued individual error messages to display

        # Set up dialog window
        self.setWindowTitle('Qudi Error')
        screen_size = QtWidgets.QApplication.instance().primaryScreen().availableSize()
        screen_width = screen_size.width()
        screen_height = screen_size.height()
        self.setGeometry((screen_width * 3) // 8,
                         (screen_height * 3) // 8,
                         screen_width // 4,
                         screen_height // 4)
        self.setMinimumSize(screen_width // 6, screen_height // 8)

        # Set up message label widget
        self.msg_label = QtWidgets.QLabel()
        self.msg_label.setWordWrap(True)
        self.msg_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                     QtWidgets.QSizePolicy.Expanding)

        # Set up disable checkbox
        self.disable_checkbox = QtWidgets.QCheckBox('Disable error message popups')

        # Set up buttons and group them in a layout
        self.ok_button = QtWidgets.QPushButton('OK')
        self.next_button = QtWidgets.QPushButton('Show next error')
        self.log_button = QtWidgets.QPushButton('Show log...')
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_button)
        btn_layout.addWidget(self.next_button)
        btn_layout.addWidget(self.log_button)
        btn_layout.addStretch()
        self.next_button.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                       QtWidgets.QSizePolicy.Fixed)

        # Set up dialog main layout and add all widgets to it
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(3, 3, 3, 3)
        main_layout.addWidget(self.msg_label)
        main_layout.addWidget(self.disable_checkbox)
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

        # Connect button click signals to slots
        self.ok_button.clicked.connect(self.ok_clicked)
        self.next_button.clicked.connect(self.next_message)
        self.log_button.clicked.connect(self.log_clicked)

    def show(self, entry):
        """ Show a log entry in a popup window.

        @param dict entry: log entry in dictionary form
        """
        # Return early if disabled
        if self.disabled:
            return

        # extract list of exceptions
        exceptions = list()
        key = 'exception'
        exc = entry
        while key in exc:
            exc = exc[key]
            if exc is None:
                break
            # ignore this error if it was generated on the command line.
            tb = exc.get('traceback', ['', ''])
            if len(tb) > 1 and 'File "<stdin>"' in tb[1]:
                return

            if exc is None:
                break
            key = 'oldExc'
            if exc['message'] == 'None':
                continue
            elif exc['message'].startswith('HelpfulException'):
                # FIXME: Should be possible to remove this case (not used in qudi)
                msg = exc['message'].lstrip('HelpfulException: ')
                exceptions.append('<b>{0}</b>'.format(self.clean_text(msg)))
            else:
                exceptions.append(self.clean_text(exc['message']))

        msg = '<b>{0}</b><br>'.format(entry['message']) + '<br>'.join(exceptions)

        if self.isVisible():
            self.messages.append(msg)
            self._update_next_button()
        else:
            w = QtWidgets.QApplication.activeWindow()
            self.msg_label.setText(msg)
            self.open()
            self._update_next_button()
            if w is not None:
                cp = w.geometry().center()
                self.setGeometry(cp.x() - self.width() // 2,
                                 cp.y() - self.height() // 2,
                                 self.width(),
                                 self.height())
        self.raise_()
        self.activateWindow()

    @property
    def disabled(self):
        """ Property holding the disabled flag for this error message popup

        @return bool: Flag indicating disabled (True) or enabled (False) error message popups
        """
        return self.disable_checkbox.isChecked()

    @disabled.setter
    def disabled(self, disable):
        self.disable_checkbox.setChecked(bool(disable))

    @QtCore.Slot()
    def disable(self):
        """ Convenience method to disable this error message popup.
        """
        self.disabled = True

    @QtCore.Slot()
    def enable(self):
        """ Convenience method to enable this error message popup.
        """
        self.disabled = False

    @staticmethod
    def clean_text(text):
        """ Return a string with some special characters escaped for HTML.

        @param str text: string to sanitize
        @return str: string with special characters replaced by HTML escape sequences
        """
        text = text.replace('&', '&amp;')
        text = text.replace('>', '&gt;')
        text = text.replace('<', '&lt;')
        return text.replace('\n', '<br/>\n')

    def closeEvent(self, ev):
        """ Specify close event action.
          @param QEvent ev: event from event handler

          Extends the parent class closeEvent hndling function to delete
          pending messages.
        """
        super().closeEvent(ev)
        self.messages = list()

    @QtCore.Slot()
    def ok_clicked(self):
        """ Marks messages as accepted and closes dialog.
        """
        self.accept()
        self.messages = list()

    @QtCore.Slot()
    def log_clicked(self):
        """ Marks messages as accepted and shows log window.
        """
        self.accept()
        self._log_window.show()
        self.messages = list()

    @QtCore.Slot()
    def next_message(self):
        """ Shows the next error message popup.
        """
        if self.messages:
            self.msg_label.setText(self.messages.pop(0))
        self._update_next_button()

    def _update_next_button(self):
        msg_number = len(self.messages)
        self.next_button.setText('Show next error ({0:d} more)'.format(msg_number))
        if msg_number > 0 and not self.next_button.isVisible():
            self.next_button.show()
        elif msg_number == 0 and self.next_button.isVisible():
            self.next_button.hide()
        return
