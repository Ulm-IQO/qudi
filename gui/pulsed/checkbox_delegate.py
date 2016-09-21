# -*- coding: utf-8 -*-

"""
This file contains a checkbox delegate.

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

class CheckBoxDelegate(QtWidgets.QStyledItemDelegate):
    """
    A delegate that places a fully functioning QCheckBox in every
    cell of the column to which it's applied
    """

    def __init__(self, parent, item_dict):
        """
        @param QWidget parent: the parent QWidget which hosts this child widget
        @param dict item_dict: A list with predefined properties for the used
                                editor. In this class the items must look like:
                                [default_val]
        """
        super().__init__(parent)
        self.item_dict = item_dict

        # constant from Qt how to access the specific data type:
        self.model_data_access = QtCore.Qt.CheckStateRole

    def get_initial_value(self):
        """ Tells you which object to insert in the model.setData function.

        @return list[2]: returns the two values, which corresponds to the last
                         two values you should insert in the setData function.
                         The first one is the first element of the passed item
                         list list_items and the second one is the Role.
            model.setData(index, value, QtCore.Qt.CheckStateRole)
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

        editor = QtWidgets.QCheckBox(parent)
        editor.setCheckState(self.item_dict['init_val'])
        editor.installEventFilter(self)
        return editor

    def setEditorData(self, editor, index):
        """ Set the display of the current value of the used editor.

        @param QCheckBox editor: QObject which was created in createEditor
                                 function, here a QCheckBox.
        @param QtCore.QModelIndex index: explained in createEditor function.

        This function converts the passed data to an value, which can be
        understood by the editor.
        """

        value = index.data(self.model_data_access)
        if value == 0:
            checkState = QtCore.Qt.Unchecked
        else:
            checkState = QtCore.Qt.Checked
        editor.setCheckState(checkState)


    def setModelData(self, editor, model, index):
        """ Save the data of the editor to the model of the QTableWidget.

        @param QCheckBox editor: QObject which was created in createEditor
                                 function, here a QCheckBox.
        @param QtCore.QAbstractTableModel model: That is the object which
                                                 contains the data of the
                                                 QTableWidget.
        @param QtCore.QModelIndex index: explained in createEditor function.
        Before the editor is destroyed the current selection should be saved
        in the model of the data. The setModelData() function reads the content
        of the editor, and writes it to the model. Furthermore here the
        postprocessing of the data can happen, where the data can be
        manipulated for the model.
        """

        value = editor.checkState()
        model.setData(index, value, self.model_data_access)

    def updateEditorGeometry(self, editor, option, index):
        """
        The updateEditorGeometry() function updates the editor widget's
        geometry using the information supplied in the style option. This is
        the minimum that the delegate must do in this case.
        """
        editor.setGeometry(option.rect)


