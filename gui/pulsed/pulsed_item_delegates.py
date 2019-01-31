# -*- coding: utf-8 -*-

"""
This file contains item delegates for the pulse editor QTableView/model.

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

import numpy as np
from qtpy import QtCore, QtGui, QtWidgets
from gui.pulsed.pulsed_custom_widgets import MultipleCheckboxWidget, AnalogParametersWidget#, FlagChannelsWidget
from qtwidgets.scientific_spinbox import ScienDSpinBox


class CheckBoxItemDelegate(QtGui.QStyledItemDelegate):
    """
    """
    editingFinished = QtCore.Signal()

    def __init__(self, parent, data_access_role=QtCore.Qt.DisplayRole):
        """
        @param QWidget parent: the parent QWidget which hosts this child widget
        """
        super().__init__(parent)
        self._access_role = data_access_role
        return

    def createEditor(self, parent, option, index):
        """
        Create for the display and interaction with the user an editor.

        @param QtGui.QWidget parent: The parent object (probably QTableView)
        @param QtGui.QStyleOptionViewItemV4 option: This is a setting option which you can use for
                                                    style configuration.
        @param QtCore.QModelIndex index: That index will be passed by the model object of the
                                         QTableView to the delegated object. This index contains
                                         information about the selected current cell.

        An editor can be in principle any QWidget, which you want to use to display the current
        (model-)data. Therefore the editor is like a container, which handles the passed entries
        from the user interface and should save the data to the model object of the QTableWidget.
        The setEditorData function reads data from the model.

        Do not save the created editor as a class variable! This consumes a lot of unneeded memory.
        It is way better to create an editor if it is needed. The inherent function closeEditor()
        of QStyledItemDelegate takes care of closing and destroying the editor for you, if it is not
        needed any longer.
        """
        editor = QtWidgets.QCheckBox(parent=parent)
        editor.setGeometry(option.rect)
        editor.stateChanged.connect(self.commitAndCloseEditor)
        return editor

    def commitAndCloseEditor(self):
        editor = self.sender()
        self.commitData.emit(editor)
        # self.closeEditor.emit(editor)
        self.editingFinished.emit()
        return

    def sizeHint(self):
        return QtCore.QSize(15, 50)

    def setEditorData(self, editor, index):
        """
        Set the display of the current value of the used editor.

        @param ScienDSpinBox editor: QObject which was created in createEditor function,
                                     here a ScienDSpinBox.
        @param QtCore.QModelIndex index: explained in createEditor function.

        This function converts the passed data to an value, which can be
        understood by the editor.
        """
        data = index.data(self._access_role)
        if not isinstance(data, bool):
            return
        editor.blockSignals(True)
        editor.setChecked(data)
        editor.blockSignals(False)
        return

    def setModelData(self, editor, model, index):
        """
        Save the data of the editor to the model.

        @param ScienDSpinBox editor: QObject which was created in createEditor function,
                                                here a ScienDSpinBox.
        @param QtCore.QAbstractTableModel model: That is the object which contains the data model.
        @param QtCore.QModelIndex index: explained in createEditor function.

        Before the editor is destroyed the current selection should be saved in the underlying data
        model. The setModelData() function reads the content of the editor, and writes it to the
        model. Furthermore here the postprocessing of the data can happen, where the data can be
        manipulated for the model.
        """
        data = editor.isChecked()
        # write the data to the model:
        model.setData(index, data, self._access_role)
        return

    def paint(self, painter, option, index):
        painter.save()
        r = option.rect
        painter.translate(r.topLeft())
        widget = QtWidgets.QCheckBox()
        widget.setGeometry(r)
        widget.setChecked(index.data(self._access_role))
        widget.render(painter)
        painter.restore()


class SpinBoxItemDelegate(QtGui.QStyledItemDelegate):
    """
    """
    editingFinished = QtCore.Signal()

    def __init__(self, parent, item_dict=None, data_access_role=QtCore.Qt.DisplayRole):
        """
        @param QWidget parent: the parent QWidget which hosts this child widget
        @param dict item_dict:  dict with the following keys which give informations about the
                                current viewbox: 'unit', 'init_val', 'min', 'max', 'view_stepsize',
                                                 'dec', 'unit_prefix'
        """
        super().__init__(parent)
        if item_dict is None:
            item_dict = dict()
        self.item_dict = item_dict
        self._access_role = data_access_role
        return

    def createEditor(self, parent, option, index):
        """
        Create for the display and interaction with the user an editor.

        @param QtGui.QWidget parent: The parent object (probably QTableView)
        @param QtGui.QStyleOptionViewItemV4 option: This is a setting option which you can use for
                                                    style configuration.
        @param QtCore.QModelIndex index: That index will be passed by the model object of the
                                         QTableView to the delegated object. This index contains
                                         information about the selected current cell.

        An editor can be in principle any QWidget, which you want to use to display the current
        (model-)data. Therefore the editor is like a container, which handles the passed entries
        from the user interface and should save the data to the model object of the QTableWidget.
        The setEditorData function reads data from the model.

        Do not save the created editor as a class variable! This consumes a lot of unneeded memory.
        It is way better to create an editor if it is needed. The inherent function closeEditor()
        of QStyledItemDelegate takes care of closing and destroying the editor for you, if it is not
        needed any longer.
        """
        editor = QtGui.QSpinBox(parent=parent)
        if 'min' in self.item_dict:
            editor.setMinimum(self.item_dict['min'])
        if 'max' in self.item_dict:
            editor.setMaximum(self.item_dict['max'])
        if 'unit' in self.item_dict:
            editor.setSuffix(self.item_dict['unit'])
        editor.setGeometry(option.rect)
        editor.editingFinished.connect(self.commitAndCloseEditor)
        return editor

    def commitAndCloseEditor(self):
        editor = self.sender()
        self.commitData.emit(editor)
        # self.closeEditor.emit(editor)
        self.editingFinished.emit()
        return

    def sizeHint(self):
        return QtCore.QSize(90, 50)

    def setEditorData(self, editor, index):
        """
        Set the display of the current value of the used editor.

        @param ScienDSpinBox editor: QObject which was created in createEditor function,
                                     here a ScienDSpinBox.
        @param QtCore.QModelIndex index: explained in createEditor function.

        This function converts the passed data to an value, which can be
        understood by the editor.
        """
        data = index.data(self._access_role)
        if not isinstance(data, (np.integer, int)):
            data = self.item_dict['init_val']
        editor.blockSignals(True)
        editor.setValue(int(data))
        editor.blockSignals(False)
        return

    def setModelData(self, editor, model, index):
        """
        Save the data of the editor to the model.

        @param ScienDSpinBox editor: QObject which was created in createEditor function,
                                     here a ScienDSpinBox.
        @param QtCore.QAbstractTableModel model: That is the object which contains the data model.
        @param QtCore.QModelIndex index: explained in createEditor function.

        Before the editor is destroyed the current selection should be saved in the underlying data
        model. The setModelData() function reads the content of the editor, and writes it to the
        model. Furthermore here the postprocessing of the data can happen, where the data can be
        manipulated for the model.
        """
        data = editor.value()
        # write the data to the model:
        model.setData(index, data, self._access_role)
        return

    def paint(self, painter, option, index):
        painter.save()
        r = option.rect
        painter.translate(r.topLeft())
        widget = QtGui.QSpinBox()
        if 'min' in self.item_dict:
            widget.setMinimum(self.item_dict['min'])
        if 'max' in self.item_dict:
            widget.setMaximum(self.item_dict['max'])
        if 'unit' in self.item_dict:
            widget.setSuffix(self.item_dict['unit'])
        widget.setGeometry(r)
        widget.setValue(index.data(self._access_role))
        widget.render(painter)
        painter.restore()


class ScienDSpinBoxItemDelegate(QtGui.QStyledItemDelegate):
    """
    """
    editingFinished = QtCore.Signal()

    def __init__(self, parent, item_dict, data_access_role=QtCore.Qt.DisplayRole):
        """
        @param QWidget parent: the parent QWidget which hosts this child widget
        @param dict item_dict:  dict with the following keys which give informations about the
                                current viewbox: 'unit', 'init_val', 'min', 'max'
        """
        super().__init__(parent)
        self.item_dict = item_dict
        self._access_role = data_access_role
        # Note, the editor used in this delegate creates the unit prefix by
        # itself, therefore no handling for that is implemented.
        return

    def createEditor(self, parent, option, index):
        """
        Create for the display and interaction with the user an editor.

        @param QtGui.QWidget parent: The parent object (probably QTableView)
        @param QtGui.QStyleOptionViewItemV4 option: This is a setting option which you can use for
                                                    style configuration.
        @param QtCore.QModelIndex index: That index will be passed by the model object of the
                                         QTableView to the delegated object. This index contains
                                         information about the selected current cell.

        An editor can be in principle any QWidget, which you want to use to display the current
        (model-)data. Therefore the editor is like a container, which handles the passed entries
        from the user interface and should save the data to the model object of the QTableWidget.
        The setEditorData function reads data from the model.

        Do not save the created editor as a class variable! This consumes a lot of unneeded memory.
        It is way better to create an editor if it is needed. The inherent function closeEditor()
        of QStyledItemDelegate takes care of closing and destroying the editor for you, if it is not
        needed any longer.
        """
        editor = ScienDSpinBox(parent=parent)
        if 'min' in self.item_dict:
            editor.setMinimum(self.item_dict['min'])
        if 'max' in self.item_dict:
            editor.setMaximum(self.item_dict['max'])
        if 'dec' in self.item_dict:
            editor.setDecimals(self.item_dict['dec'])
        if 'unit' in self.item_dict:
            editor.setSuffix(self.item_dict['unit'])
        editor.setGeometry(option.rect)
        editor.editingFinished.connect(self.commitAndCloseEditor)
        return editor

    def commitAndCloseEditor(self):
        editor = self.sender()
        self.commitData.emit(editor)
        # self.closeEditor.emit(editor)
        self.editingFinished.emit()
        return

    def sizeHint(self):
        return QtCore.QSize(90, 50)

    def setEditorData(self, editor, index):
        """
        Set the display of the current value of the used editor.

        @param ScienDSpinBox editor: QObject which was created in createEditor function,
                                     here a ScienDSpinBox.
        @param QtCore.QModelIndex index: explained in createEditor function.

        This function converts the passed data to an value, which can be
        understood by the editor.
        """
        data = index.data(self._access_role)
        if not isinstance(data, float):
            data = self.item_dict['init_val']
        editor.blockSignals(True)
        editor.setValue(data)
        editor.blockSignals(False)
        return

    def setModelData(self, editor, model, index):
        """
        Save the data of the editor to the model.

        @param ScienDSpinBox editor: QObject which was created in createEditor function,
                                                here a ScienDSpinBox.
        @param QtCore.QAbstractTableModel model: That is the object which contains the data model.
        @param QtCore.QModelIndex index: explained in createEditor function.

        Before the editor is destroyed the current selection should be saved in the underlying data
        model. The setModelData() function reads the content of the editor, and writes it to the
        model. Furthermore here the postprocessing of the data can happen, where the data can be
        manipulated for the model.
        """
        data = editor.value()
        # write the data to the model:
        model.setData(index, data, self._access_role)
        return

    def paint(self, painter, option, index):
        painter.save()
        r = option.rect
        painter.translate(r.topLeft())
        widget = ScienDSpinBox()
        if 'dec' in self.item_dict:
            widget.setDecimals(self.item_dict['dec'])
        if 'unit' in self.item_dict:
            widget.setSuffix(self.item_dict['unit'])
        widget.setGeometry(r)
        widget.setValue(index.data(self._access_role))
        widget.render(painter)
        painter.restore()


class ComboBoxItemDelegate(QtGui.QStyledItemDelegate):
    """
    """
    editingFinished = QtCore.Signal()

    def __init__(self, parent, item_list, data_access_role=QtCore.Qt.DisplayRole,
                 size=QtCore.QSize(80, 50)):
        super().__init__(parent)
        self._item_list = item_list
        self._access_role = data_access_role
        self._size = size
        return

    def createEditor(self, parent, option, index):
        """
        Create for the display and interaction with the user an editor.

        @param QtGui.QWidget parent: The parent object (probably QTableView)
        @param QtGui.QStyleOptionViewItemV4 option: This is a setting option which you can use for
                                                    style configuration.
        @param QtCore.QModelIndex index: That index will be passed by the model object of the
                                         QTableView to the delegated object. This index contains
                                         information about the selected current cell.

        An editor can be in principle any QWidget, which you want to use to display the current
        (model-)data. Therefore the editor is also a container, which handles the passed entries
        from the user interface and should save the data in the model object of the QTableWidget.

        Do not save the created editor as a class variable! This consumes a lot of unneeded memory.
        It is way better to create an editor if it is needed. The inherent function closeEditor()
        of QStyledItemDelegate takes care of closing and destroying the editor for you, if it is not
        needed any longer.
        """
        widget = QtGui.QComboBox(parent)
        widget.addItems(self._item_list)
        widget.setGeometry(option.rect)
        widget.currentIndexChanged.connect(self.commitAndCloseEditor)
        return widget

    def commitAndCloseEditor(self):
        editor = self.sender()
        self.commitData.emit(editor)
        # self.closeEditor.emit(editor)
        self.editingFinished.emit()
        return

    def sizeHint(self):
        return self._size

    def setEditorData(self, editor, index):
        """
        Set the display of the current value of the used editor.

        @param QComboBox editor: QObject which was created in createEditor function,
                                 here a QCombobox.
        @param QtCore.QModelIndex index: explained in createEditor function.
        """
        data = index.data(self._access_role)
        combo_index = editor.findText(data)
        editor.blockSignals(True)
        editor.setCurrentIndex(combo_index)
        editor.blockSignals(False)
        return

    def setModelData(self, editor, model, index):
        """
        Save the data of the editor to the model.

        @param QComboBox editor: QObject which was created in createEditor function,
                                 here a QCombobox.
        @param QtCore.QAbstractTableModel model: That is the object which contains the data model.
        @param QtCore.QModelIndex index: explained in createEditor function.

        Before the editor is destroyed the current selection should be saved in the data model.
        The setModelData() function reads the content of the editor, and writes it to the model.
        Furthermore here the postprocessing of the data can happen, where the data can be
        manipulated for the model.
        """
        data = editor.currentText()
        model.setData(index, data, self._access_role)
        return

    def paint(self, painter, option, index):
        painter.save()
        r = option.rect
        painter.translate(r.topLeft())
        widget = QtGui.QComboBox()
        widget.addItem(index.data(self._access_role))
        widget.setGeometry(r)
        widget.render(painter)
        painter.restore()


class MultipleCheckboxItemDelegate(QtGui.QStyledItemDelegate):
    """
    """
    editingFinished = QtCore.Signal()

    def __init__(self, parent, label_list, data_access_role=QtCore.Qt.DisplayRole):

        super().__init__(parent)
        self._label_list = list() if label_list is None else list(label_list)
        self._access_role = data_access_role
        return

    def createEditor(self, parent, option, index):
        """
        Create for the display and interaction with the user an editor.

        @param QtGui.QWidget parent: The parent object, here QTableWidget
        @param QtGui.QStyleOptionViewItemV4 option: This is a setting option which you can use
                                                    for style configuration.
        @param QtCore.QModelIndex index: That index will be passed by the model object of the
                                         QTableWidget to the delegated object. This index contains
                                         information about the selected current cell.

        An editor can be in principle any QWidget, which you want to use to display the current
        (model-)data. Therefore the editor is also a container, which handles the passed entries
        from the user interface and should save the data in the model object of the QTableWidget.

        Do not save the created editor as a class variable! This consumes a lot of unneeded memory.
        It is way better to create an editor if it is needed. The inherent function closeEditor()
        of QStyledItemDelegate takes care of closing and destroying the editor for you, if it is not
        needed any longer.
        """
        editor = MultipleCheckboxWidget(parent, self._label_list)
        editor.setData(index.data(self._access_role))
        editor.stateChanged.connect(self.commitAndCloseEditor)
        return editor

    def commitAndCloseEditor(self):
        editor = self.sender()
        self.commitData.emit(editor)
        # self.closeEditor.emit(editor)
        self.editingFinished.emit()
        return

    def sizeHint(self):
        widget = MultipleCheckboxWidget(None, self._label_list)
        return widget.sizeHint()

    def setEditorData(self, editor, index):
        """
        Set the display of the current value of the used editor.

        @param MultipleCheckboxWidget editor: QObject which was created in createEditor function,
                                              here a MultipleCheckboxWidget.
        @param QtCore.QModelIndex index: explained in createEditor function.

        This function converts the passed data to an value, which can be understood by the editor.
        """
        data = index.data(self._access_role)
        editor.blockSignals(True)
        editor.setData(data)
        editor.blockSignals(False)
        return

    def setModelData(self, editor, model, index):
        """
        Save the data of the editor to the model.

        @param MultipleCheckboxWidget editor: QObject which was created in createEditor function,
                                              here a MultipleCheckboxWidget.
        @param QtCore.QAbstractTableModel model: That is the object which contains the data model.
        @param QtCore.QModelIndex index: explained in createEditor function.

        Before the editor is destroyed the current selection should be saved in the underlying data
        model. The setModelData() function reads the content of the editor, and writes it to the
        model. Furthermore here the postprocessing of the data can happen, where the data can be
        manipulated for the model.
        """
        data = editor.data()
        model.setData(index, data, self._access_role)
        return

    def paint(self, painter, option, index):
        painter.save()
        r = option.rect
        painter.translate(r.topLeft())
        widget = MultipleCheckboxWidget(None, self._label_list)
        widget.setData(index.data(self._access_role))
        widget.render(painter)
        painter.restore()


class AnalogParametersItemDelegate(QtGui.QStyledItemDelegate):
    """
    """
    editingFinished = QtCore.Signal()

    def __init__(self, parent, data_access_roles=None):
        super().__init__(parent)
        if data_access_roles is None:
            self._access_role = [QtCore.Qt.DisplayRole, QtCore.Qt.DisplayRole]
        else:
            self._access_role = data_access_roles

    def createEditor(self, parent, option, index):
        """
        Create for the display and interaction with the user an editor.

        @param QtGui.QWidget parent: The parent object, here QTableWidget
        @param QtGui.QStyleOptionViewItemV4 option: This is a setting option which you can use
                                                    for style configuration.
        @param QtCore.QModelIndex index: That index will be passed by the model object of the
                                         QTableWidget to the delegated object. This index contains
                                         information about the selected current cell.

        An editor can be in principle any QWidget, which you want to use to display the current
        (model-)data. Therefore the editor is also a container, which handles the passed entries
        from the user interface and should save the data in the model object of the QTableWidget.

        Do not save the created editor as a class variable! This consumes a lot of unneeded memory.
        It is way better to create an editor if it is needed. The inherent function closeEditor()
        of QStyledItemDelegate takes care of closing and destroying the editor for you, if it is not
        needed any longer.
        """
        parameters = index.data(self._access_role[0]).params
        editor = AnalogParametersWidget(parent, parameters)
        editor.setData(index.data(self._access_role[1]))
        editor.editingFinished.connect(self.commitAndCloseEditor)
        return editor

    def commitAndCloseEditor(self):
        editor = self.sender()
        self.commitData.emit(editor)
        # self.closeEditor.emit(editor)
        self.editingFinished.emit()
        return

    def sizeHint(self, option, index):
        parameters = index.data(self._access_role[0]).params
        widget = AnalogParametersWidget(None, parameters)
        return widget.sizeHint()

    def setEditorData(self, editor, index):
        """
        Set the display of the current value of the used editor.

        @param AnalogParametersWidget editor: QObject which was created in createEditor function,
                                              here a AnalogParametersWidget.
        @param QtCore.QModelIndex index: explained in createEditor function.

        This function converts the passed data to an value, which can be understood by the editor.
        """
        data = index.data(self._access_role[1])
        editor.blockSignals(True)
        editor.setData(data)
        editor.blockSignals(False)
        return

    def setModelData(self, editor, model, index):
        """
        Save the data of the editor to the model.

        @param AnalogParametersWidget editor: QObject which was created in createEditor function,
                                              here a AnalogParametersWidget.
        @param QtCore.QAbstractTableModel model: That is the object which contains the data model.
        @param QtCore.QModelIndex index: explained in createEditor function.

        Before the editor is destroyed the current selection should be saved in the underlying data
        model. The setModelData() function reads the content of the editor, and writes it to the
        model. Furthermore here the postprocessing of the data can happen, where the data can be
        manipulated for the model.
        """
        data = editor.data()
        model.setData(index, data, self._access_role[1])
        return

    def paint(self, painter, option, index):
        painter.save()
        r = option.rect
        painter.translate(r.topLeft())
        parameters = index.data(self._access_role[0]).params
        widget = AnalogParametersWidget(None, parameters)
        widget.setData(index.data(self._access_role[1]))
        widget.render(painter)
        painter.restore()
