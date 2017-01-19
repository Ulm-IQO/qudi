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
from qtpy import QtCore
from qtwidgets.scientific_spinbox import ScienDSpinBox

class DoubleSpinBoxDelegate(QtWidgets.QStyledItemDelegate):
    """ Make a QDoubleSpinBox delegate for the QTableWidget."""

    def __init__(self, parent, item_dict):
        """
        @param QWidget parent: the parent QWidget which hosts this child widget
        @param dict item_dict: dict with the following keys which give
                                informations about the current viewbox:
                                    'unit', 'init_val', 'min', 'max',
                                    'view_stepsize', 'dec', 'unit_prefix'

        """
        super().__init__(parent)
        self.item_dict = item_dict

        unit_prefix_dict = {'f':1e-15, 'p':1e-12, 'n': 1e-9, 'micro':1e-6,
                            'm':1e-3, '':1, 'k':1e3, 'M':1e6, 'G':1e9,
                            'T':1e12, 'P':1e15}

        # determine the value to normalized the constraints for that:
        self.norm_val = unit_prefix_dict[self.item_dict['unit_prefix']]

        # constant from Qt how to access the specific data type:
        self.model_data_access = QtCore.Qt.EditRole


    def get_unit_prefix(self):
        """ Return the unit prefix of that view element to determine the
            magnitude.
        @return str: unit prefic
        """
        return self.item_dict['unit_prefix']

    def get_initial_value(self):
        """ Tells you which object to insert in the model.setData function.

        @return list[2]: returns the two values, which corresponds to the last
                         two values you shoul insert in the setData function.
                         The first one is the first element of the passed item
                         list list_items and the second one is the Role.
            model.setData(index, editor.itemText(value), QtCore.Qt.DisplayRole)
        """
        return [self.item_dict['init_val'], self.model_data_access]

    def createEditor(self, parent, option, index):
        """ Create for the display and interaction with the user an editor.

        @param QtGui.QWidget parent: The parent object, here QTableWidget
        @param QtGui.QStyleOptionViewItemV4 option: This is a setting option
                                                    which you can use for style
                                                    configuration.
        @param QtCore.QModelIndex index: That index will be passed by the model
                                         object of the QTableWidget to the
                                         delegated object. This index contains
                                         information about the selected current
                                         cell.

        An editor can be in principle any QWidget, which you want to use to
        display the current (model-)data. Therefore the editor is like a
        container, which handles the passed entries from the user interface and
        should save the data to the model object of the QTableWidget. The
        setEditorData function reads data from the model.

        Do not save the created editor as a class variable! This consumes a lot
        of unneeded memory. It is way better to create an editor if it is
        needed. The inherent function closeEditor() of QStyledItemDelegate
        takes care of closing and destroying the editor for you, if it is not
        needed any longer.
        """
        editor = ScienDSpinBox(parent=parent)
        editor.setMinimum(self.item_dict['min']/self.norm_val)
        editor.setMaximum(self.item_dict['max']/self.norm_val)
        editor.setSingleStep(self.item_dict['view_stepsize']/self.norm_val)
        editor.setDecimals(self.item_dict['dec'])
        editor.installEventFilter(self)
        editor.setValue(self.item_dict['init_val']/self.norm_val)
        editor.setMaximumHeight(100)
        return editor

    def setEditorData(self, editor, index):
        pass

    def setModelData(self, spinBox_ref, model, index):
        pass

    def updateEditorGeometry(self, editor, option, index):
        pass

    def displayText(self, conv_object, qlocal):
        pass