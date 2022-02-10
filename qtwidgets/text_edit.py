# -*- coding: utf-8 -*-
"""
This file contains a nicer TextEdit, from https://gist.github.com/hahastudio/4345418

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

from qtpy import QtCore
from qtpy import QtWidgets

class TextEdit(QtWidgets.QTextEdit):
    """
    A TextEdit editor that sends editingFinished events 
    when the text was changed and focus is lost.
    """

    valueChanged = QtCore.Signal()
    receivedFocus = QtCore.Signal()
    
    def __init__(self):
        super(TextEdit, self).__init__()
        self._changed = False
        self.setTabChangesFocus( True )
        self.textChanged.connect( self._handle_text_changed )

    def focusInEvent(self, event):
        super(TextEdit, self).focusInEvent( event )
        self.receivedFocus.emit()

    def focusOutEvent(self, event):
        if self._changed:
            self.valueChanged.emit()
        super(TextEdit, self).focusOutEvent( event )

    def _handle_text_changed(self):
        self._changed = True

    def setTextChanged(self, state=True):
        self._changed = state

    def setHtml(self, html):
        QtWidgets.QTextEdit.setHtml(self, html)
        self._changed = False
        
    def value(self):
        return self.toPlainText()
