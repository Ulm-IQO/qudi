# -*- coding: utf-8 -*-
"""
Different Qt widgets for pop-up dialogues.

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
top-level directory of this distribution and at
<https://github.com/Ulm-IQO/qudi/>
"""

from qtpy import QtWidgets, QtCore


class PopUpMessage(QtWidgets.QDialog):
    """
    Simple notification dialog box. Will display a text message in a window 1/4 the size of the
    primary display available space. Has an OK button to dismiss.
    """
    def __init__(self, title=None, message=None, min_size=None):
        """

        @param str title: optional, the dialog window title
        @param str message: optional, the message to be shown inside the dialog
        @param QSize min_size: optional, the (minimal) size of the dialog window
        """
        super().__init__()

        self.text = QtWidgets.QLabel()
        self.text.setWordWrap(True)
        font = self.text.font()
        font.setBold(True)
        self.text.setFont(font)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        buttons.setCenterButtons(True)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.text)
        layout.addWidget(buttons)
        self.setLayout(layout)
        buttons.accepted.connect(self.accept)

        if min_size is None:
            screen_size = QtWidgets.QApplication.instance().primaryScreen().availableSize()
            min_size = QtCore.QSize(screen_size.width() // 4,  screen_size.height() // 4)
        self.setMinimumSize(min_size)
        if title is not None:
            self.set_title(title)
        if message is not None:
            self.set_message(message)
        return

    def set_message(self, message):
        """
        Set dialog text message to show.

        @param str message: The message to show in the dialog
        """
        self.text.setText(message)

    def set_title(self, title):
        """
        Set dialog window title.

        @param str title: The window title of the dialog
        """
        self.setWindowTitle(title)
