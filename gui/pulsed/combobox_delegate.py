# -*- coding: utf-8 -*-

"""
This file contains a combo box delegate.

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


class ComboBoxDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, parent, item_dict):
        # Use the constructor of the inherited class.
        super().__init__(parent)
        # QtGui.QStyledItemDelegate.__init__(self, parent)
        self.item_dict = item_dict  # pass to the object a
                                                # reference to the calling
                                                # function, so that it can
                                                # check every time the value

        self.get_list = self.item_dict['get_list_method']

        # constant from Qt how to access the specific data type:
        self.model_data_access = QtCore.Qt.DisplayRole


    def get_initial_value(self):
        """ Tells you which object to insert in the model.setData function.

        @return list[2]: returns the two values, which corresponds to the last
                         two values you should insert in the setData function.
                         The first one is the first element of the passed item
                         list item_dict and the second one is the Role.
            model.setData(index, editor.itemText(value),QtCore.Qt.DisplayRole)
        """

        if len(self.get_list()) == 0:
            ini_val = ''
        else:
            ini_val = self.get_list()[0]

        return [ini_val, self.model_data_access]

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
        display the current (model-)data. Therefore the editor is also a
        container, which handles the passed entries from the user interface and
        should save the data in the model object of the QTableWidget.

        Do not save the created editor as a class variable! This consumes a lot
        of unneeded memory. It is way better to create an editor if it is
        needed. The inherent function closeEditor() of QStyledItemDelegate
        takes care of closing and destroying the editor for you, if it is not
        needed any longer.
        """
        editor = QtWidgets.QComboBox(parent)    # Editor is Combobox
        editor.addItems(self.get_list())
        editor.setCurrentIndex(0)
        editor.installEventFilter(self)
        return editor

    def setEditorData(self, editor, index):
        """ Set the display of the current value of the used editor.

        @param QComboBox editor: QObject which was created in createEditor
                                 function, here a QCombobox.
        @param QtCore.QModelIndex index: explained in createEditor function.
        """

        # just for safety, block any signal which might change the values of
        # the editor during the access.
        value = index.data(self.model_data_access)
        if value == '':
            num = 0
        else:
            num = self.get_list().index(value)
        # num = self.item_dict.index(value)
        editor.setCurrentIndex(num)

    def setModelData(self, editor, model, index):
        """ Save the data of the editor to the model of the QTableWidget.

        @param QComboBox editor: QObject which was created in createEditor
                                 function, here a QCombobox.
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
        value = editor.currentIndex()   # take current value and save to model
        model.setData(index, editor.itemText(value), self.model_data_access)

    def updateEditorGeometry(self, editor, option, index):
        """ State how the editor should behave if it is opened.

        @param QComboBox editor: QObject which was created in createEditor
                                 function, here a QCombobox.
        @param QtGui.QStyleOptionViewItemV4 option: This is a setting option
                                                    which you can use for style
                                                    configuration.
        @param QtCore.QModelIndex index: explained in createEditor function.

        Here you can basically change the appearance of you displayed editor.
        """

        # Every time the editor is displayed the current list should be renewed.
        # This is introduced for experimenting with a passed data set. It is
        # not clear whether this will be useful or not. That will be found out.
        editor.clear()

        editor.addItems(self.get_list())
        # editor.addItems(self.item_dict)
        editor.setGeometry(option.rect)