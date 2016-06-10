# -*- coding: utf-8 -*-

"""
This file contains a combo box delegate.

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

Copyright (C) 2015 Alexander Stark alexander.stark@uni-ulm.de
"""

from PyQt4 import QtGui, QtCore

class ComboBoxDelegate(QtGui.QStyledItemDelegate):

    def __init__(self, parent, item_dict):
        # Use the constructor of the inherited class.
        QtGui.QStyledItemDelegate.__init__(self, parent)
        self.item_dict = item_dict  # pass to the object a
                                                # reference to the calling
                                                # function, so that it can
                                                # check every time the value

        self.get_list = self.item_dict['get_list_method']
        print(self.item_dict)

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
        editor = QtGui.QComboBox(parent)    # Editor is Combobox
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


class SpinBoxDelegate(QtGui.QStyledItemDelegate):
    """
    Create delegated Spinboxes.

    a well made qt help for spinboxes:
    http://doc.qt.io/qt-4.8/qt-itemviews-spinboxdelegate-example.html

    python help for spinboxes:
    http://stackoverflow.com/questions/28017395/how-to-use-delegate-to-control-qtableviews-rows-height
    """
    def __init__(self, parent, item_dict):
        """
        @param QWidget parent: the parent QWidget which hosts this child widget
        @param dict item_dict: A list with predefined properties for the used
                                editor. In this class the items must look like:
                                [default_val, min_val, max_val]
        """
        QtGui.QStyledItemDelegate.__init__(self, parent)
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
            model.setData(index, editor.itemText(value),QtCore.Qt.DisplayRole)
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
        editor = QtGui.QSpinBox(parent)
        self.editor = editor

        editor.setMinimum(self.item_dict['min']/self.norm_val)
        editor.setMaximum(self.item_dict['max']/self.norm_val)
        editor.setSingleStep(self.item_dict['view_stepsize']/self.norm_val)
        editor.installEventFilter(self)
        editor.setValue(self.item_dict['init_val']/self.norm_val)
        return editor

    def setEditorData(self, editor, index):
        """ Set the display of the current value of the used editor.

        @param QSpinBox editor: QObject which was created in createEditor
                                function, here a QSpinBox.
        @param QtCore.QModelIndex index: explained in createEditor function.

        This function converts the passed data to an value, which can be
        understood by the editor.
        """

        value = index.data(self.model_data_access)

        if not isinstance(value, int):
            value = self.item_dict['init_val']/self.norm_val
        editor.setValue(value)

    def setModelData(self, spinBox, model, index):
        """ Save the data of the editor to the model of the QTableWidget.

        @param QSpinBox editor: QObject which was created in createEditor
                                function, here a QSpinBox.
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

        spinBox.interpretText()
        value = spinBox.value()
        self.value = value
        # set the data to the table model:
        model.setData(index, value, self.model_data_access)

    def updateEditorGeometry(self, editor, option, index):
        """ State how the editor should behave if it is opened.

        @param QSpinBox editor: QObject which was created in createEditor
                                function, here a QSpinBox.
        @param QtGui.QStyleOptionViewItemV4 option: This is a setting option
                                                    which you can use for style
                                                    configuration.
        @param QtCore.QModelIndex index: explained in createEditor function.

        This function updates the editor widget's geometry using the
        information supplied in the style option. This is the minimum that the
        delegate must do in this case.
        Here you can basically change the appearance of you displayed editor.
        """
        editor.setGeometry(option.rect)

    def sizeHint(self, option, index):
        """ Give the drawing function the proper dimensions of the size."""
        return QtCore.QSize(64,64)

