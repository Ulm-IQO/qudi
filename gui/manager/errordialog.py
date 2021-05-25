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
import re


class ErrorDialog(QtWidgets.QDialog):
    """This class provides a popup window for notification with the option to
      show the next error popup in the queue and to show the log window where
      you can see the traceback for an exception.
    """

    def __init__(self, logWindow):
        """ Create an ErrorDialog object

          @param object logWindow: reference to LogWindow object that this
                                   popup belongs to
        """
        super().__init__()
        self.logWindow = logWindow
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        # self.setWindowModality(QtCore.Qt.NonModal)
        self.setWindowTitle('Qudi Error')
        wid = QtWidgets.QDesktopWidget()
        screenWidth = wid.screen(wid.primaryScreen()).width()
        screenHeight = wid.screen(wid.primaryScreen()).height()
        self.setGeometry((screenWidth - 500) / 2,
                         (screenHeight - 100) / 2, 500, 100)
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(3, 3, 3, 3)
        self.setLayout(self.layout)
        self.messages = []

        self.msgLabel = QtWidgets.QLabel()
        # self.msgLabel.setWordWrap(False)
        # self.msgLabel.setMaximumWidth(800)
        self.msgLabel.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        # self.msgLabel.setFrameStyle(QtGui.QFrame.Box)
        # self.msgLabel.setStyleSheet('QLabel { font-weight: bold }')
        self.layout.addWidget(self.msgLabel)
        self.msgLabel.setMaximumWidth(800)
        self.msgLabel.setMinimumWidth(500)
        self.msgLabel.setWordWrap(True)
        self.layout.addStretch()
        self.disableCheck = QtWidgets.QCheckBox(
            'Disable error message popups')
        self.layout.addWidget(self.disableCheck)

        self.btnLayout = QtWidgets.QHBoxLayout()
        self.btnLayout.addStretch()
        self.okBtn = QtWidgets.QPushButton('OK')
        self.btnLayout.addWidget(self.okBtn)
        self.nextBtn = QtWidgets.QPushButton('Show next error')
        self.btnLayout.addWidget(self.nextBtn)
        self.nextBtn.hide()
        self.logBtn = QtWidgets.QPushButton('Show Log...')
        self.btnLayout.addWidget(self.logBtn)
        self.btnLayoutWidget = QtWidgets.QWidget()
        self.layout.addWidget(self.btnLayoutWidget)
        self.btnLayoutWidget.setLayout(self.btnLayout)
        self.btnLayout.addStretch()

        self.okBtn.clicked.connect(self.okClicked)
        self.nextBtn.clicked.connect(self.nextMessage)
        self.logBtn.clicked.connect(self.logClicked)

    def show(self, entry):
        """ Show a log entry in a popup window.

          @param dict entry: log entry in dictionary form

        """
        # rules are:
        # - Try to show friendly error messages
        # - If there are any helpfulExceptions, ONLY show those
        # otherwise, show everything
        self.lastEntry = entry

        # extract list of exceptions
        exceptions = []
        # helpful = []
        key = 'exception'
        exc = entry
        while key in exc:
            exc = exc[key]
            if exc is None:
                break
            # ignore this error if it was generated on the command line.
            tb = exc.get('traceback', ['', ''])
            if len(tb) > 1 and 'File "<stdin>"' in tb[1]:
                return False

            if exc is None:
                break
            key = 'oldExc'
            if exc['message'].startswith('HelpfulException'):
                exceptions.append(
                    '<b>' + self.cleanText(re.sub(r'^HelpfulException: ', '',
                                                  exc['message'])) + '</b>')
            elif exc['message'] == 'None':
                continue
            else:
                exceptions.append(self.cleanText(exc['message']))

        msg = '<b>' + entry['message'] + '</b><br>' + '<br>'.join(exceptions)

        if self.disableCheck.isChecked():
            return False
        if self.isVisible():
            self.messages.append(msg)
            self.nextBtn.show()
            self.nextBtn.setEnabled(True)
            self.nextBtn.setText('Show next error ({0:d} more)'.format(
                len(self.messages)))
        else:
            w = QtWidgets.QApplication.activeWindow()
            self.nextBtn.hide()
            self.msgLabel.setText(msg)
            self.open()
            if w is not None:
                cp = w.geometry().center()
                self.setGeometry(cp.x() - self.width() / 2., cp.y() -
                                 self.height() / 2., self.width(),
                                 self.height())
        # self.activateWindow()
        self.raise_()

    @staticmethod
    def cleanText(text):
        """ Return a string with some special characters escaped for HTML.

          @param str text: string to sanitize

          @return str: string with spechial characters replaced by HTML
                       escape sequences

          FIXME: there is probably a pre-defined function for this, use it!
        """
        text = re.sub(r'&', '&amp;', text)
        text = re.sub(r'>', '&gt;', text)
        text = re.sub(r'<', '&lt;', text)
        text = re.sub(r'\n', '<br/>\n', text)
        return text

    def closeEvent(self, ev):
        """ Specify close event action.
          @param QEvent ev: event from event handler

          Extends the parent class closeEvent hndling function to delete
          pending messages.
        """
        QtWidgets.QDialog.closeEvent(self, ev)
        self.messages = []

    def okClicked(self):
        """ Marks message as acceped and closes popup.
        """
        self.accept()
        self.messages = []

    def logClicked(self):
        """ Marks message as accepted and shows log window.
        """
        self.accept()
        self.logWindow.show()
        self.messages = []

    def nextMessage(self):
        """ Shows the next error message popup.
        """
        self.msgLabel.setText(self.messages.pop(0))
        self.nextBtn.setText('Show next error ({0:d} more)'.format(len(self.messages)))
        if len(self.messages) == 0:
            self.nextBtn.setEnabled(False)

    def disable(self, disable):
        """ Disables popups.

          @param bool disable: disable popups if true, enables if false
        """
        self.disableCheck.setChecked(disable)
