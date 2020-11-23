# -*- coding: utf-8 -*-

"""
This file contains a custom QDockWidget subclass to be used in the ODMR GUI module.

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

from PySide2 import QtCore, QtWidgets, QtGui

from qudi.core.gui.qtwidgets.advanced_dockwidget import AdvancedDockWidget

__all__ = ('OdmrFitDockWidget',)


class OdmrFitDockWidget(AdvancedDockWidget):
    """
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('ODMR Fit')

        label = QtWidgets.QLabel('This is a placeholder for future fit controls')
        label.setMinimumSize(300, 300)
        label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setWidget(label)
