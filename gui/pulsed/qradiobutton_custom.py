# -*- coding: utf-8 -*-

"""
This file contains the a wrapper around QRadioButton, to customize it.

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

Copyright (C) 2016 Alexander Stark alexander.stark@uni-ulm.de
"""

from PyQt4 import QtGui
from PyQt4 import QtCore


class CustomQRadioButton(QtGui.QRadioButton):
    """ Class which customize QRadioButton behaviour.

    The following customization have been applied:
        - Make the QRadioButton readonly, i.e. catch all the Signals and pass
          them or not, depending on the chosen state of the Widget.
    """

    def __init__(self, *args):
        # just pass all stuff to superclass, will fail if passing **kwargs
        super(CustomQRadioButton, self).__init__(*args)
        self._readOnly = False

    def isReadOnly(self):
        """ Check the current state of the Radiobox. """
        return self._readOnly

    def mousePressEvent(self, event):
        """ Handle what happens on press event of the mouse.

        @param event: QEvent of a Mouse Release action
        """
        if self.isReadOnly():
            event.accept()
        else:
            super(CustomQRadioButton, self).mousePressEvent(event)

    # Comment out this method, since it is called, if QToolTip is going to be
    # displayed. You would not see any QTooltip if you catch that signal.
    # def mouseMoveEvent( self, event ):
    #     if ( self.isReadOnly() ):
    #         event.accept()
    #     else:
    #         super(CustomQRadioButton, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """ Handle what happens on release of the mouse.

        @param event: QEvent of a Mouse Release action
        """
        if self.isReadOnly() :
            event.accept()
        else:
            super(CustomQRadioButton, self).mouseReleaseEvent(event)

    # Handle event in which the widget has focus and the spacebar is pressed.
    def keyPressEvent(self, event):
        if self.isReadOnly():
            event.accept()
        else:
            super(CustomQRadioButton, self).keyPressEvent(event)

    @QtCore.pyqtSlot(bool)
    def setReadOnly(self, state):
        """ Set the Readonly state.

        @param bool state: True or False, for having a readonly QRadioButton.
        """
        self._readOnly = state
    readOnly = QtCore.pyqtProperty(bool, isReadOnly, setReadOnly)
