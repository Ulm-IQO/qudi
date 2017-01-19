# -*- coding: utf-8 -*-

"""
This file contains a scientificspinbox delegate.

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

from qtpy import QtWidgets

class DoubleSpinBoxDelegate(QtWidgets.QStyledItemDelegate):
    """ Make a QDoubleSpinBox delegate for the QTableWidget."""

    def __init__(self, parent, item_dict):
        super().__init__(parent)
        pass


    def get_unit_prefix(self):
        pass

    def get_initial_value(self):
        pass

    def createEditor(self, parent, option, index):
        pass

    def setEditorData(self, editor, index):
        pass

    def setModelData(self, spinBox_ref, model, index):
        pass

    def updateEditorGeometry(self, editor, option, index):
        pass

    def displayText(self, conv_object, qlocal):
        pass