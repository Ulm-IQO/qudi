# -*- coding: utf-8 -*-

"""
This file contains a more advanced QDockWidget subclass.

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
"""

__all__ = ['AdvancedDockWidget']

from PySide2 import QtCore, QtWidgets


class AdvancedDockWidget(QtWidgets.QDockWidget):
    """ QDockWidget that emits a sigClosed signal when handling a closeEvent
    """

    sigClosed = QtCore.Signal()

    def closeEvent(self, event):
        self.sigClosed.emit()
        return super().closeEvent(event)
