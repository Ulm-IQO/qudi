# -*- coding: utf-8 -*-

"""
This file contains the QuDi GUI module base class.

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

from PyQt4 import QtGui, QtCore, uic

import numpy as np
import os
from collections import OrderedDict
import pyqtgraph as pg
from gui.guibase import GUIBase
from core.util.mutex import Mutex

# Rather than import the ui*.py file here, the ui*.ui file itself is loaded by uic.loadUI in the QtGui classes below.

#FIXME: incoorporate the passed hardware constraints from the logic.
#FIXME: save the length in sample points (bins)
#FIXME: adjust the length to the bins
#FIXME: choose as default value the minimal sampling rate
#FIXME: insert warning text in choice of channels
#FIXME: pass the posibile channels over to laser channel select
#FIXME: count laser pulses
#FIXME: calculate total length of the sequence
#FIXME: insert checkbox (or something else) for removing the inital table
#FIXME: remove repeat and inc from the initial table
#FIXME: save the pattern of the table to a file. Think about possibilities to read in from file if number of channels is different. Therefore make also a load function.
#FIXME: give general access to specific element in the column and let it be changable by this function
#FIXME: return the whole table as a matrix
#FIXME: Make the minimum and the maximum values of the sampling frequency be dependent on the used hardware file.
#FIXME: make a generate button and insert a name for the pattern. The generate button will pass the values to the logic.
#FIXME: connect the current default value of length of the dspinbox with
#       the minimal sequence length and the sampling rate.
#FIXME: Later that should be able to round up the values directly within
#       the entering in the dspinbox for a consistent display of the
#       sequence length.

# =============================================================================
#                       Define some delegate classes.
# =============================================================================

# These delegate classes can modify the behaviour of a whole row or column of
# in a QTableWidget. When this starts to work properly, then the delegate
# classes will move to a separate file.
#
# A general idea, which functions are customizable for our purpose it is worth
# to read the documentation for the QItemDelegate Class:
# http://pyqt.sourceforge.net/Docs/PyQt4/qitemdelegate.html
#
# If you want to delegate a row or a column of a QTableWidget, then you have
# at least to declare the constructors and the modification function for the
# displayed data (which you see in the table) and the saved data (which is
# handeled by the model class of the table). That means your delegate should
# at least contain the functions:
#       - createEditor
#       - setEditor
#       - updateEditorGeometry
#       - setModelData
#
# I.e. when editing data in an item view, editors are created and displayed by
# a delegate.
#
# Use the QStyledItemDelegate class instead of QItemDelegate, since the first
# one provides extended possibilities of painting the windows and can be
# changed by Qt style sheets.
# Since the delegate is a subclass of QItemDelegate or QStyledItemDelegate, the
# data it retrieves from the model is displayed in a default style, and we do
# not need to provide a custom paintEvent().
# We use QStyledItemDelegate as our base class, so that we benefit from the
# default delegate implementation. We could also have used
# QAbstractItemDelegate, if we had wanted to start completely from scratch.
#
# Examples how to create e.g. of SpinBoxdelegate in native Qt:
# http://qt.developpez.com/doc/4.7/itemviews-spinboxdelegate/
# and a similar python implementation:
# https://github.com/PySide/Examples/blob/master/examples/itemviews/spinboxdelegate.py

class ComboBoxDelegate(QtGui.QStyledItemDelegate):

    def __init__(self, parent, get_func_config_list):
        # Use the constructor of the inherited class.
        QtGui.QStyledItemDelegate.__init__(self, parent)
        self.get_func_config_list = get_func_config_list[0]  # pass to the object a
                                                # reference to the calling
                                                # function, so that it can
                                                # check every time the value

        # constant from Qt how to access the specific data type:
        self.model_data_access = QtCore.Qt.DisplayRole


    def get_initial_value(self):
        """ Tells you which object to insert in the model.setData function.

        @return list[2]: returns the two values, which corresponds to the last
                         two values you should insert in the setData function.
                         The first one is the first element of the passed item
                         list items_list and the second one is the Role.
            model.setData(index, editor.itemText(value),QtCore.Qt.DisplayRole)
        """
        return [self.get_func_config_list()[0], self.model_data_access]

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
        editor.addItems(self.get_func_config_list())
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
        num = self.get_func_config_list().index(value)
        # num = self.items_list.index(value)
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

        editor.addItems(self.get_func_config_list())
        # editor.addItems(self.items_list)
        editor.setGeometry(option.rect)


class SpinBoxDelegate(QtGui.QStyledItemDelegate):
    """
    Create delegated Spinboxes.

    a well made qt help for spinboxes:
    http://doc.qt.io/qt-4.8/qt-itemviews-spinboxdelegate-example.html

    python help for spinboxes:
    http://stackoverflow.com/questions/28017395/how-to-use-delegate-to-control-qtableviews-rows-height
    """
    def __init__(self, parent, items_list):
        """
        @param QWidget parent: the parent QWidget which hosts this child widget
        @param list items_list: A list with predefined properties for the used
                                editor. In this class the items must look like:
                                [default_val, min_val, max_val]
        """
        QtGui.QStyledItemDelegate.__init__(self, parent)
        self.items_list = items_list

        # constant from Qt how to access the specific data type:
        self.model_data_access = QtCore.Qt.EditRole

    def get_initial_value(self):
        """ Tells you which object to insert in the model.setData function.

        @return list[2]: returns the two values, which corresponds to the last
                         two values you shoul insert in the setData function.
                         The first one is the first element of the passed item
                         list list_items and the second one is the Role.
            model.setData(index, editor.itemText(value),QtCore.Qt.DisplayRole)
        """
        return [self.items_list[0], self.model_data_access]

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
        editor.setMinimum(self.items_list[1])
        editor.setMaximum(self.items_list[2])
        editor.installEventFilter(self)
        editor.setValue(self.items_list[0])
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
            value = self.items_list[0]
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

class CheckBoxDelegate(QtGui.QStyledItemDelegate):
    """
    A delegate that places a fully functioning QCheckBox in every
    cell of the column to which it's applied
    """

    def __init__(self, parent, items_list):
        """
        @param QWidget parent: the parent QWidget which hosts this child widget
        @param list items_list: A list with predefined properties for the used
                                editor. In this class the items must look like:
                                [default_val]
        """
        QtGui.QStyledItemDelegate.__init__(self, parent)
        self.items_list = items_list

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
        return [self.items_list[0], self.model_data_access]

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

        editor = QtGui.QCheckBox(parent)
        editor.setCheckState(self.items_list[0])
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

class DoubleSpinBoxDelegate(QtGui.QStyledItemDelegate):
    """ Make a QDoubleSpinBox delegate for the QTableWidget."""

    def __init__(self, parent, items_list):
        """
        @param QWidget parent: the parent QWidget which hosts this child widget
        @param list items_list: ????????????? FIXME


        """
        QtGui.QStyledItemDelegate.__init__(self, parent)
        self.items_list = items_list[0]

        self.unit_list = {'p':1e-12, 'n':1e-9, 'micro':1e-6, 'm':1e-3, 'k':1e3, 'M':1e6, 'G':1e9, 'T':1e12}

        if 'disp_unit' in self.items_list.keys():
            self.norm = self.unit_list[self.items_list['disp_unit']]
        else:
            self.norm = 1.0

        # constant from Qt how to access the specific data type:
        self.model_data_access = QtCore.Qt.EditRole

    def get_initial_value(self):
        """ Tells you which object to insert in the model.setData function.

        @return list[2]: returns the two values, which corresponds to the last
                         two values you shoul insert in the setData function.
                         The first one is the first element of the passed item
                         list list_items and the second one is the Role.
            model.setData(index, editor.itemText(value), QtCore.Qt.DisplayRole)
        """
        return [self.items_list['init_val'], self.model_data_access]

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



        editor = QtGui.QDoubleSpinBox(parent)
        self.editor = editor
        editor.setMinimum(self.items_list['min'])
        editor.setMaximum(self.items_list['max'])
        editor.setSingleStep(self.items_list['view_stepsize']/self.norm)
        editor.setDecimals(self.items_list['dec'])
        editor.installEventFilter(self)
        editor.setValue(self.items_list['init_val'])
        return editor

    def setEditorData(self, editor, index):
        """ Set the display of the current value of the used editor.

        @param QDoubleSpinBox editor: QObject which was created in createEditor
                                      function, here a QDoubleSpinBox.
        @param QtCore.QModelIndex index: explained in createEditor function.

        This function converts the passed data to an value, which can be
        understood by the editor.
        """

        value = index.data(self.model_data_access)

        if not isinstance(value, float):
            value = self.items_list['init_val']
        editor.setValue(value)

    def setModelData(self, spinBox, model, index):
        """ Save the data of the editor to the model of the QTableWidget.

        @param QDoubleSpinBox editor: QObject which was created in createEditor
                                      function, here a QDoubleSpinBox.
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

        @param QDoubleSpinBox editor: QObject which was created in createEditor
                                      function, here a QDoubleSpinBox.
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

class PulsedMeasurementMainWindow(QtGui.QMainWindow):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pulsed_maingui.ui')

        # Load it
        super(PulsedMeasurementMainWindow, self).__init__()

        uic.loadUi(ui_file, self)
        self.show()

class BlockSettingDialog(QtGui.QDialog):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pulsed_main_gui_settings_block_gen.ui')

        # Load it
        super(BlockSettingDialog, self).__init__()

        uic.loadUi(ui_file, self)

class PulsedMeasurementGui(GUIBase):
    """
    This is the GUI Class for pulsed measurements
    """
    _modclass = 'PulsedMeasurementGui'
    _modtype = 'gui'

    ## declare connectors
    _in = { 'pulseanalysislogic': 'PulseAnalysisLogic',
            'sequencegeneratorlogic': 'SequenceGeneratorLogic',
            'savelogic': 'SaveLogic',
            'pulsedmeasurementlogic': 'PulsedMeasurementLogic'
            }

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, c_dict)

        self.logMsg('The following configuration was found.',
                    msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')

        #locking for thread safety
        self.threadlock = Mutex()

    def activation(self, e=None):
        """ Initialize, connect and configure the pulsed measurement GUI.

        @param Fysom.event e: Event Object of Fysom

        Establish general connectivity and activate the different tabs of the
        GUI.
        """


        self._pulse_analysis_logic = self.connector['in']['pulseanalysislogic']['object']
        self._pulsed_measurement_logic = self.connector['in']['pulsedmeasurementlogic']['object']
        self._seq_gen_logic = self.connector['in']['sequencegeneratorlogic']['object']
        self._save_logic = self.connector['in']['savelogic']['object']


        self._mw = PulsedMeasurementMainWindow()

        self._activate_analysis_settings_ui(e)
        self._activate_analysis_ui(e)

        self._activate_pulse_generator_settings_ui(e)
        self._activate_pulse_generator_ui(e)

        self._activate_sequence_settings_ui(e)
        self._activate_sequence_generator_ui(e)

        self._activate_pulse_extraction_settings_ui(e)
        self._activate_pulse_extraction_ui(e)

        self.show()


    def deactivation(self, e):
        """ Undo the Definition, configuration and initialisation of the pulsed
            measurement GUI.

        @param Fysom.event e: Event Object of Fysom

        This deactivation disconnects all the graphic modules, which were
        connected in the initUI method.
        """


        self._deactivate_analysis_settings_ui(e)
        self._deactivate_analysis_ui(e)

        self._deactivate_pulse_generator_settings_ui(e)
        self._deactivate_pulse_generator_ui(e)

        self._deactivate_sequence_settings_ui(e)
        self._deactivate_sequence_generator_ui(e)

        self._deactivate_pulse_extraction_settings_ui(e)
        self._deactivate_pulse_extraction_ui(e)


        self._mw.close()

    def show(self):
        """Make main window visible and put it above all other windows. """
        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()




    ###########################################################################
    ###     Methods related to Settings for the 'Pulse Generator' Tab:      ###
    ###########################################################################


    def _activate_pulse_generator_settings_ui(self, e):
        """ Initialize, connect and configure the Settings for the
            'Pulse Generator' Tab.

        @param Fysom.event e: Event Object of Fysom
        """

        self._bs = BlockSettingDialog() # initialize the block settings
        self._bs.accepted.connect(self.update_block_settings)
        self._bs.rejected.connect(self.keep_former_block_settings)
        self._bs.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.update_block_settings)

        # Add in the settings menu within the groupbox widget all the available
        # math_functions, based on the list from the Logic. Right now, the GUI
        # objects are inserted the 'hard' way, like it is done in the
        # Qt-Designer.

        # FIXME: Make a nicer way of displaying the available functions, maybe
        #        with a Table!

        _encoding = QtGui.QApplication.UnicodeUTF8
        objectname = self._bs.objectName()
        for index, func_name in enumerate(self.get_func_config_list()):

            name_label = 'func_'+ str(index)
            setattr(self._bs, name_label, QtGui.QLabel(self._bs.groupBox))
            label = getattr(self._bs, name_label)
            label.setObjectName(name_label)
            self._bs.gridLayout_3.addWidget(label, index, 0, 1, 1)
            label.setText(QtGui.QApplication.translate(objectname, func_name, None, _encoding))

            name_checkbox = 'checkbox_'+ str(index)
            setattr(self._bs, name_checkbox, QtGui.QCheckBox(self._bs.groupBox))
            checkbox = getattr(self._bs, name_checkbox)
            checkbox.setObjectName(name_checkbox)
            self._bs.gridLayout_3.addWidget(checkbox, index, 1, 1, 1)
            checkbox.setText(QtGui.QApplication.translate(objectname, '', None, _encoding))

        # make the first 4 Functions as default.
        # FIXME: the default functions, must be passed as a config

        for index in range(4):
            name_checkbox = 'checkbox_'+ str(index)
            checkbox = getattr(self._bs, name_checkbox)
            checkbox.setCheckState(QtCore.Qt.Checked)

    def _deactivate_pulse_generator_settings_ui(self, e):
        """ Disconnects the configuration of the Settings for the
            'Pulse Generator' Tab.

        @param Fysom.event e: Event Object of Fysom
        """

        self._bs.accepted.disconnect()
        self._bs.rejected.disconnect()
        self._bs.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.disconnect()

        self._bs.close()

    def show_block_settings(self):
        """ Opens the block settings menue. """
        self._bs.exec_()

    def update_block_settings(self):
        """ Write new block settings from the gui to the file. """

        channel_config = self.get_hardware_constraints()['channel_config']

        ch_settings = (self._bs.analog_channels_SpinBox.value(), self._bs.digital_channels_SpinBox.value())

        if ch_settings in channel_config:
            self._set_channels(num_d_ch=ch_settings[1], num_a_ch=ch_settings[0])
        else:
            self.logMsg('Desired channel configuration (analog, digital) as '
                        '{0} not possible, since the hardware does not '
                        'support it!/n'
                        'Restore previous configuration.'.format(ch_settings),
                        msgType='warning')
            self.keep_former_block_settings()


    def keep_former_block_settings(self):
        """ Keep the old block settings and restores them in the gui. """

        self._bs.digital_channels_SpinBox.setValue(self._num_d_ch)
        self._bs.analog_channels_SpinBox.setValue(self._num_a_ch)

    def get_current_function_list(self):
        """ Retrieve the functions, which are chosen by the user.

        @return: list[] with strings of the used functions. Names are based on
                 the passed func_config dict from the logic.
        """

        current_functions = []

        for index in range(len(self.get_func_config_list())):
            name_checkbox = 'checkbox_'+ str(index)
            checkbox = getattr(self._bs, name_checkbox)
            if checkbox.isChecked():
                name_label = 'func_'+ str(index)
                func = getattr(self._bs, name_label)
                current_functions.append(func.text())

        return current_functions

    def set_channel_constraints(self):
        """ Set limitations for the choise of the channels based on the
            constraints received from the hardware. """

        channel_config = self.get_hardware_constraints()['channel_config']

        # at least one channel configuration must be known. Set this as initial
        # values for the constraints:
        a_ch_min = channel_config[0][0]
        a_ch_max = channel_config[0][0]
        d_ch_min = channel_config[0][1]
        d_ch_max = channel_config[0][1]


        for entry in (channel_config):
            if entry[0] < a_ch_min:
                a_ch_min = entry[0]
            if entry[0] > a_ch_max:
                a_ch_max = entry[0]
            if entry[1] < d_ch_min:
                d_ch_min = entry[1]
            if entry[1] > d_ch_max:
                d_ch_max = entry[1]

        self._bs.analog_channels_SpinBox.setRange(a_ch_min, a_ch_max)
        self._bs.digital_channels_SpinBox.setRange(d_ch_min, d_ch_max)



    ###########################################################################
    ###   Methods related to Tab 'Pulse Generator' in the Pulsed Window:    ###
    ###########################################################################

    def _activate_pulse_generator_ui(self, e):
        """ Initialize, connect and configure the 'Pulse Generator' Tab.

        @param Fysom.event e: Event Object of Fysom
        """
        # connect the signal for a change of the sample frequency
        self._mw.sample_freq_DSpinBox.editingFinished.connect(self.sample_frequency_changed)
        
        # connect the signals for the block editor:
        self._mw.block_add_last_PushButton.clicked.connect(self.block_editor_add_row_after_last)
        self._mw.block_del_last_PushButton.clicked.connect(self.block_editor_delete_row_last)
        self._mw.block_add_sel_PushButton.clicked.connect(self.block_editor_add_row_before_selected)
        self._mw.block_del_sel_PushButton.clicked.connect(self.block_editor_delete_row_selected)
        self._mw.block_clear_PushButton.clicked.connect(self.block_editor_clear_table)
        
        self._mw.curr_block_save_PushButton.clicked.connect(self.block_editor_save_clicked)
        self._mw.curr_block_del_PushButton.clicked.connect(self.block_editor_delete_clicked)

        # connect the signals for the block organizer:
        self._mw.organizer_add_last_PushButton.clicked.connect(self.block_organizer_add_row_after_last)
        self._mw.organizer_del_last_PushButton.clicked.connect(self.block_organizer_delete_row_last)
        self._mw.organizer_add_sel_PushButton.clicked.connect(self.block_organizer_add_row_before_selected)
        self._mw.organizer_del_sel_PushButton.clicked.connect(self.block_organizer_delete_row_selected)
        self._mw.organizer_clear_PushButton.clicked.connect(self.block_organizer_clear_table)

        # connect the signals for the "Upload on device" section
        self._mw.upload_on_ch1_PushButton.clicked.connect(self.upload_on_ch1_clicked)
        self._mw.upload_on_ch2_PushButton.clicked.connect(self.upload_on_ch2_clicked)

        # connect the menue to the actions:
        self._mw.action_Settings_Block_Generation.triggered.connect(self.show_block_settings)

        # emit a trigger event when for all mouse click and keyboard click events:
        self._mw.block_editor_TableWidget.setEditTriggers(QtGui.QAbstractItemView.AllEditTriggers)
        self._mw.block_organizer_TableWidget.setEditTriggers(QtGui.QAbstractItemView.AllEditTriggers)
        
        # connect update signals of the sequence_generator_logic
        self._seq_gen_logic.signal_block_list_updated.connect(self.update_block_list)
        self._seq_gen_logic.signal_ensemble_list_updated.connect(self.update_ensemble_list)
        self._seq_gen_logic.signal_sequence_list_updated.connect(self.update_sequence_list)
        
        #FIXME: Make the analog channel parameter chooseable in the settings.


        # the attributes are assigned to function an the desired argument one
        # wants to pass to these functions.
        self._param_a_ch = OrderedDict()
        self._param_a_ch['Function'] = self._get_settings_combobox()
        self._param_a_ch['Freq (GHz)'] = self._get_settings_dspinbox_freq()
        self._param_a_ch['Ampl. (V)'] = self._get_settings_dspinbox_amp()
        self._param_a_ch['Phase(°)'] = self._get_settings_dspinbox_phase()

        self._param_d_ch = OrderedDict()
        self._param_d_ch['CheckBox'] = self._get_settings_checkbox()

        self._param_block = OrderedDict()
        self._param_block['Length (ns)'] = self._get_settings_dspinbox_length()
        self._param_block['Inc. (ns)'] = self._get_settings_dspinbox_inc()
#        self._param_block['Repeat?'] = self._get_settings_checkbox()
#        self._param_block['Use as tau?'] = self._get_settings_checkbox()

        # a dictionary containing the names and indices of the GUI block
        # generator table. Should be set and updated by the GUI:

        #self._seq_gen_logic.table_config


        self.insert_parameters(0)
        channel_config = self.get_hardware_constraints()['channel_config'][-1]
        self._set_channels(num_d_ch=channel_config[1], num_a_ch=channel_config[0])

        self.keep_former_block_settings()
        # A dictionary containing the mathematical function names to choose
        # from in the block editor with corresponding lists of needed
        # parameters like phase, frequency etc. This should be provided by the
        #  "math logic".

        # initialize the lists of available blocks, ensembles and sequences
        self.update_block_list()
        self.update_ensemble_list()
        self.update_sequence_list()


        # =====================================================================
        #              Explanation of the usage of QTableWidget
        # =====================================================================

        # In general a table consist out of an object for viewing the data and
        # and out of an object where the data are saved. For viewing the data,
        # there is the general QWidgetView class and for holding/storing the
        # data you have to define a model. The model ensures to hold your data
        # in the proper data type and give the possibility to separate the data
        # from the display.
        # The QTableWidget class is a specialized class to handle user input
        # into an table. In order to handle the data, it contains already a
        # model (due to that you can e.g. easily add rows and columns and
        # modify the content of each cell). Therefore the model of a
        # QTableWidget is a privite attribute and cannot be changed externally.
        # If you want to define a custom model for QTableWidget you have to
        # start from a QTableView and construct you own data handling in the
        # model.
        # Since QTableWidget has all the (nice and) needed requirements for us,
        # a custom definition of QTableView with a Model is not needed.


        # Modified by me
        # self._mw.init_block_TableWidget.viewport().setAttribute(QtCore.Qt.WA_Hover)
        # self._mw.repeat_block_TableWidget.viewport().setAttribute(QtCore.Qt.WA_Hover)

    def _deactivate_pulse_generator_ui(self, e):
        """ Disconnects the configuration for 'Pulse Generator Tab.

        @param Fysom.event e: Event Object of Fysom
        """
        #FIXME: implement a proper deactivation for that.
        pass

    def get_func_config(self):
        """ Retrieve the function configuration from the Logic.

        @return: dict with keys denoting the function name as a string and the
                 value of each key is again a dict, which contains as key the
                 parameter name as a string and for that string key how often
                 the parameter is used.
        """
        return self._seq_gen_logic.get_func_config()

    def get_func_config_list(self):
        """ Retrieve the possible math functions as a list of strings.

        @return: list[] with string entries as function names.
        """
        return list(self._seq_gen_logic.get_func_config())
        
    def sample_frequency_changed(self):
        """
        This method is called when the user enters a new sample frequency in the SpinBox
        """
        freq = 1e6*self._mw.sample_freq_DSpinBox.value()
        self._seq_gen_logic.set_sampling_freq(freq)
        return
        
    def upload_on_ch1_clicked(self):
        """
        This method is called when the user clicks on "Upload on Ch1"
        """
        # Get the ensemble name to be uploaded from the ComboBox
        ensemble_name = self._mw.upload_ensemble_ComboBox.currentText()
        # Sample and upload the ensemble via logic module
        self._seq_gen_logic.download_ensemble(ensemble_name)
        # Load the ensemble/waveform into channel 1 (or multiple channels if specified in the ensemble)
        self._seq_gen_logic.load_asset(ensemble_name, 1)
        return
        
    def upload_on_ch2_clicked(self):
        """
        This method is called when the user clicks on "Upload on Ch2"
        """
        # Get the ensemble name to be uploaded from the ComboBox
        ensemble_name = self._mw.upload_ensemble_ComboBox.currentText()
        # Sample and upload the ensemble via logic module
        self._seq_gen_logic.download_ensemble(ensemble_name)
        # Load the ensemble/waveform into channel 1 (or multiple channels if specified in the ensemble)
        self._seq_gen_logic.load_asset(ensemble_name, 2)
        return
    
    def update_block_list(self):
        """
        This method is called upon signal_block_list_updated emit of the sequence_generator_logic.
        Updates all ComboBoxes showing generated blocks.
        """
        # updated list of all generated blocks
        new_list = self._seq_gen_logic.saved_blocks
        # update saved_blocks_ComboBox items
        self._mw.saved_blocks_ComboBox.clear()
        self._mw.saved_blocks_ComboBox.addItems(new_list)
        return
    
    def update_ensemble_list(self):
        """
        This method is called upon signal_ensemble_list_updated emit of the sequence_generator_logic.
        Updates all ComboBoxes showing generated block_ensembles.
        """
        # updated list of all generated ensembles
        new_list = self._seq_gen_logic.saved_ensembles
        # update upload_ensemble_ComboBox items
        self._mw.upload_ensemble_ComboBox.clear()
        self._mw.upload_ensemble_ComboBox.addItems(new_list)
        # update saved_ensembles_ComboBox items
        self._mw.saved_ensembles_ComboBox.clear()
        self._mw.saved_ensembles_ComboBox.addItems(new_list)
        return
        
    def update_sequence_list(self):
        """
        This method is called upon signal_sequence_list_updated emit of the sequence_generator_logic.
        Updates all ComboBoxes showing generated sequences.
        """
        # updated list of all generated sequences
        new_list = self._seq_gen_logic.saved_sequences
        return
        
    # -------------------------------------------------------------------------
    #           Methods for the Pulse Block Editor
    # -------------------------------------------------------------------------

    def _get_settings_combobox(self):
        """ Get the custom setting for a general ComboBox object.

        @return list[N]: A list with pulse functions.

        This return object must coincide with the according delegate class.
        """
        return [ComboBoxDelegate, self.get_current_function_list]
        # return [ComboBoxDelegate,'Idle','Sin','Cos','DC','Sin-Gauss']

    def _get_settings_checkbox(self):
        """ Get the custom setting for a general CheckBox object.

        @return list[1]: A list with
                        [class, default_val]

        This return object must coincide with the according delegate class.
        """
        return [CheckBoxDelegate,QtCore.Qt.Unchecked]

    def _get_settings_spinbox(self):
        """ Get the custom setting for a general SpinBox object.

        @return list[3]: A list with
                        [default_val, min_val, max_val]

        This return object must coincide with the according delegate class.
        """
        return [2,0,1000000]

    def _get_settings_dspinbox_phase(self):
        """ Get the custom setting for a general phase DoubleSpinBox object.

        @return list[5]: A list with
                        [class, default_val, min_val, max_val, step_size, digits]

        This return object must coincide with the according delegate class.
        """
        return [DoubleSpinBoxDelegate, 0.0, -1000000.0, 1000000.0, 0.1, 5]

    def _get_settings_dspinbox_freq(self):
        """ Get the custom setting for a general frequency DoubleSpinBox object.

        @return list[5]: A list with
                        [class, default_val, min_val, max_val, step_size, digits]

        This return object must coincide with the according delegate class.
        """
        return [DoubleSpinBoxDelegate, 2.8, 0.0, 1000000.0, 0.01, 5]

    def _get_settings_dspinbox_amp(self):
        """ Get the custom setting for a general amplitude DoubleSpinBox object.

        @return list[5]: A list with
                        [class, default_val, min_val, max_val, step_size, digits]

        This return object must coincide with the according delegate class.
        """
        return [DoubleSpinBoxDelegate, 1.0, 0.0, 2.0, 0.01, 5]

    def _get_settings_dspinbox_length(self):
        """ Get the custom setting for a general length DoubleSpinBox object.

        @return list[5]: A list with
                        [class, default_val, min_val, max_val, step_size, digits]

        This return object must coincide with the according delegate class.
        """
        return [DoubleSpinBoxDelegate, {'unit': 'V', 'init_val': 0.0, 'min': 0.0, 'max': 100000.0,
                    'view_stepsize': 0.001, 'dec': 3}]


    def _get_settings_dspinbox_inc(self):
        """ Get the custom setting for a general increment DoubleSpinBox object.

        @return list[5]: A list with
                        [class, default_val, min_val, max_val, step_size, digits]

        This return object must coincide with the according delegate class.
        """
        return [DoubleSpinBoxDelegate, {'unit': 'V', 'init_val': 0.0, 'min': 0.0, 'max': 100000.0,
                    'view_stepsize': 0.001, 'dec': 3}]



    def _get_itemlist_combobox(self):
        """ Pass needed itemlist to specific delegate class ComboBoxDelegate.

        @return: list with the entries:
                 [initial value, reference to ask the available function list]

        This is a special functions, which passes the needed itemlist for the
        specific delegate class, here for ComboBoxDelegate. That information is
        necessary to construct properly the ViewWidget.
        """

        return [self.get_current_function_list()[0],
                self.get_current_function_list]


    def _get_itemlist_spinbox(self):
        """ Pass needed itemlist to specific delegate class SpinBoxDelegate.

        @return: list with the entries:
                 [initial value, min_value, max_value,
                  desired stepsize in ViewWidget, displayed decimals (int),
                  reference to ask current sample rate]

        This is a special function, which passes the needed itemlist for the
        specific delegate class, here for SpinBoxDelegate. That information is
        necessary to construct properly the ViewWidget.
        """
        pass

    def _get_itemlist_dspinbox(self):
        """ Pass needed itemlist to specific delegate class DoubleSpinBoxDelegate.

        @return: list with the entries:
                 [initial value, min_value, max_value,
                  desired stepsize in ViewWidget]

        This is a special function, which passes the needed itemlist for the
        specific delegate class, here for DoubleSpinBoxDelegate. That
        information is necessary to construct properly the ViewWidget.
        """
        pass

    def _get_itemlist_checkbox(self):
        """ Pass needed itemlist to specific delegate class CheckBoxDelegate.

        @return: list: with the entries:
                 [initial value]

        This is a special function, which passes the needed itemlist for the
        specific delegate class, here for CheckBoxDelegate. That information is
        necessary to construct properly the ViewWidget.
        """

        pass


    def get_current_channels(self):
        """ Get current number of analog and digial channels chosen by user.

        @return: tuple(2), with (number_a_ch, number_d_ch).

        The configuration will be one of those, received from the logic from
        the method get_hardware_constraints.
        """
        return (self._num_a_ch, self._num_d_ch)


    def get_hardware_constraints(self):
        """ Request the constrains from the logic, which are coming from the
            hardware.

        @return: dict where the keys in it are predefined in the interface.
        """
        return self._seq_gen_logic.get_hardware_constraints()


    def get_param_config(self):
        """ Retrieve the parameter configuration from Logic.

        @return: dict with the configurations for the additional parameters.
        """
        return self._seq_gen_logic.get_param_config()


    def get_element_in_block_table(self, row, column):
        """ Simplified wrapper function to get the data from a specific cell
            in the init table.

        @param int column: column index
        @param int row: row index
        @return: the value of the corresponding cell, which can be a string, a
                 float or an integer. Remember that the checkbox state
                 unchecked corresponds to 0 and check to 2. That is Qt
                 convention.

        Note that the order of the arguments in this function (first row index
        and then column index) was taken from the Qt convention.
        """

        tab = self._mw.block_editor_TableWidget

        # Get from the corresponding delegate the data access model
        access = tab.itemDelegateForColumn(column).model_data_access
        data = tab.model().index(row, column).data(access)
        return data

    def get_block_table(self):
        """ Convert initial table data to numpy array.

        @return: np.array[rows][columns] which has a structure, i.e. strings
                 integer and float values are represented by this array.
                 The structure was taken according to the init table itself.
        """

        tab = self._mw.block_editor_TableWidget

        # create a structure for the output numpy array:
        structure = ''
        for column in range(tab.columnCount()):
            elem = self.get_element_in_block_table(0,column)
            if type(elem) is str:
                structure = structure + '|S20, '
            elif type(elem) is int:
                structure = structure + '|i4, '
            elif type(elem) is float:
                structure = structure + '|f4, '
            else:
                self.logMsg('Type definition not found in the table. Include '
                            'that type!', msgType='error')

        # remove the last two elements since these are a comma and a space:
        structure = structure[:-2]
        table = np.zeros(tab.rowCount(), dtype=structure)

        # fill the table:
        for column in range(tab.columnCount()):
            for row in range(tab.rowCount()):
                # self.logMsg(, msgType='status')
                table[row][column] = self.get_element_in_block_table(row, column)

        return table


    #FIXME: Possibility to insert many rows at once

    def block_editor_add_row_before_selected(self):
        """ Add row before selected element. """

        selected_row = self._mw.block_editor_TableWidget.currentRow()

        self._mw.block_editor_TableWidget.insertRow(selected_row)
        self.initialize_row_init_block(selected_row)


    def block_editor_add_row_after_last(self):
        """ Add row after last row in the block editor. """

        number_of_rows = self._mw.block_editor_TableWidget.rowCount()
        self._mw.block_editor_TableWidget.setRowCount(number_of_rows+1)
        self.initialize_row_init_block(number_of_rows)

    def block_editor_delete_row_selected(self):
        """ Delete row of selected element. """

        # get the row number of the selected item(s). That will return the
        # lowest selected row
        row_to_remove = self._mw.block_editor_TableWidget.currentRow()
        self._mw.block_editor_TableWidget.removeRow(row_to_remove)

    def block_editor_delete_row_last(self):
        """ Delete the last row in the block editor. """

        number_of_rows = self._mw.block_editor_TableWidget.rowCount()
        # remember, the row index is started to count from 0 and not from 1,
        # therefore one has to reduce the value by 1:
        self._mw.block_editor_TableWidget.removeRow(number_of_rows-1)

    def block_editor_clear_table(self):
        """ Delete all rows in the block editor table. """

        self._mw.block_editor_TableWidget.setRowCount(1)
        self._mw.block_editor_TableWidget.clearContents()
        self.initialize_row_init_block(0)
        
    def block_editor_save_clicked(self):
        """
        Actions to perform when the save button in the block editor is clicked
        """
        name = self._mw.curr_block_name_LineEdit.text()
        table_struct = self.get_block_table()
        self._seq_gen_logic.generate_block(name, table_struct)
        return
        
    def block_editor_delete_clicked(self):
        """
        Actions to perform when the delete button in the block editor is clicked
        """
        name = self._mw.saved_blocks_ComboBox.currentText()
        self._seq_gen_logic.delete_block(name)
        return

    # -------------------------------------------------------------------------
    #           Methods for the Pulse Block Organizer
    # -------------------------------------------------------------------------


    def block_organizer_add_row_before_selected(self):
        """ Add row before selected element. """

        selected_row = self._mw.block_organizer_TableWidget.currentRow()

        self._mw.block_organizer_TableWidget.insertRow(selected_row)
        self.initialize_row_init_block(selected_row)


    def block_organizer_add_row_after_last(self):
        """ Add row after last row in the block editor. """

        number_of_rows = self._mw.block_organizer_TableWidget.rowCount()
        self._mw.block_organizer_TableWidget.setRowCount(number_of_rows+1)
        self.initialize_row_init_block(number_of_rows)

    def block_organizer_delete_row_selected(self):
        """ Delete row of selected element. """

        # get the row number of the selected item(s). That will return the
        # lowest selected row
        row_to_remove = self._mw.block_organizer_TableWidget.currentRow()
        self._mw.block_organizer_TableWidget.removeRow(row_to_remove)

    def block_organizer_delete_row_last(self):
        """ Delete the last row in the block editor. """

        number_of_rows = self._mw.block_organizer_TableWidget.rowCount()
        # remember, the row index is started to count from 0 and not from 1,
        # therefore one has to reduce the value by 1:
        self._mw.block_organizer_TableWidget.removeRow(number_of_rows-1)

    def block_organizer_clear_table(self):
        """ Delete all rows in the block editor table. """

        self._mw.block_organizer_TableWidget.setRowCount(1)
        self._mw.block_organizer_TableWidget.clearContents()
        self.initialize_row_init_block(0)
        
    def block_organizer_delete_clicked(self):
        """
        Actions to perform when the delete button in the block organizer is clicked
        """
        name = self._mw.saved_ensembles_ComboBox.currentText()
        self._seq_gen_logic.delete_ensemble(name)
        return


    def insert_parameters(self, column):

        # insert parameter:
        insert_at_col_pos = column
        for column, parameter in enumerate(self.get_param_config()):

            # add the new properties to the whole column through delegate:
            items_list = self.get_param_config()[parameter]

            if 'disp_unit' in items_list.keys():
                unit_text = items_list['disp_unit'] + items_list['unit']
            else:
                unit_text = items_list['unit']

            self._mw.block_editor_TableWidget.insertColumn(insert_at_col_pos+column)
            self._mw.block_editor_TableWidget.setHorizontalHeaderItem(insert_at_col_pos+column, QtGui.QTableWidgetItem())
            self._mw.block_editor_TableWidget.horizontalHeaderItem(insert_at_col_pos+column).setText('{0} ({1})'.format(parameter,unit_text))
            self._mw.block_editor_TableWidget.setColumnWidth(insert_at_col_pos+column, 80)

            # extract the classname from the _param_block list to be able to deligate:
            delegate = DoubleSpinBoxDelegate(self._mw.block_editor_TableWidget, [items_list])
            self._mw.block_editor_TableWidget.setItemDelegateForColumn(insert_at_col_pos+column, delegate)

            # initialize the whole row with default values:
            for row_num in range(self._mw.block_editor_TableWidget.rowCount()):
                # get the model, here are the data stored:
                model = self._mw.block_editor_TableWidget.model()
                # get the corresponding index of the current element:
                index = model.index(row_num, insert_at_col_pos+column)
                # get the initial values of the delegate class which was
                # uses for this column:
                ini_values = delegate.get_initial_value()
                # set initial values:
                model.setData(index, ini_values[0], ini_values[1])



            # add the new properties to the whole column through delegate:
            items_list = self.get_param_config()[parameter]

            if 'disp_unit' in items_list.keys():
                unit_text = items_list['disp_unit'] + items_list['unit']
            else:
                unit_text = items_list['unit']

            self._mw.block_organizer_TableWidget.insertColumn(insert_at_col_pos+column)
            self._mw.block_organizer_TableWidget.setHorizontalHeaderItem(insert_at_col_pos+column, QtGui.QTableWidgetItem())
            self._mw.block_organizer_TableWidget.horizontalHeaderItem(insert_at_col_pos+column).setText('{0} ({1})'.format(parameter,unit_text))
            self._mw.block_organizer_TableWidget.setColumnWidth(insert_at_col_pos+column, 80)

            # extract the classname from the _param_block list to be able to deligate:
            delegate = DoubleSpinBoxDelegate(self._mw.block_organizer_TableWidget, [items_list])
            self._mw.block_organizer_TableWidget.setItemDelegateForColumn(insert_at_col_pos+column, delegate)

            # initialize the whole row with default values:
            for row_num in range(self._mw.block_organizer_TableWidget.rowCount()):
                # get the model, here are the data stored:
                model = self._mw.block_organizer_TableWidget.model()
                # get the corresponding index of the current element:
                index = model.index(row_num, insert_at_col_pos+column)
                # get the initial values of the delegate class which was
                # uses for this column:
                ini_values = delegate.get_initial_value()
                # set initial values:
                model.setData(index, ini_values[0], ini_values[1])

    def count_digital_channels(self):
        """ Get the number of currently displayed digital channels.

        @return int: number of digital channels

        The number of digital channal are counted and return and additionally
        the internal counter variable _num_d_ch is updated. The counting
        procedure is based on the block_editor_TableWidget since it is assumed
        that all operation on the block_editor_TableWidget is also applied on
        block_organizer_TableWidget.
        """
        count_dch = 0
        for column in range(self._mw.block_editor_TableWidget.columnCount()):
            if 'DCh' in self._mw.block_editor_TableWidget.horizontalHeaderItem(column).text():
                count_dch = count_dch + 1

        self._num_d_ch = count_dch
        return count_dch

    def set_d_ch(self, num_d_ch):
        """

        @param num_d_ch: number of digital channels.
        """
        self._set_channels(num_d_ch=num_d_ch)

    def set_a_ch(self, num_a_ch):
        """

        @param num_a_ch: number of analog channels.
        @return:
        """
        self._set_channels(num_a_ch=num_a_ch)


    def _determine_needed_parameters(self):
        """ Determine the maximal number of needed parameters for desired functions.

        @return ('<biggest_func_name>, number_of_parameters)
        """

        #FIXME: Reimplement this function such that it will return the
        #       parameters of all needed functions and not take only the
        #       parameters of the biggest function. Then the return should be
        #       not the biggest function, but a set of all the needed
        #       parameters which is obtained from get_func_config()!


        curr_func_list = self.get_current_function_list()
        complete_func_config = self.get_func_config()

        num_max_param = 0
        biggest_func = ''

        for func in curr_func_list:
            if num_max_param < len(complete_func_config[func]):
                num_max_param = len(complete_func_config[func])
                biggest_func = func

        return (num_max_param, biggest_func)

    def update_current_table_config(self):
        """ Updates the current table configuration in the logic.

        @return list with column configuration

        """
        table_config = {}
        for column in range(self._mw.block_editor_TableWidget.columnCount()):
            text = self._mw.block_editor_TableWidget.horizontalHeaderItem(column).text()
            split_text = text.split()
            if 'DCh' in split_text[0]:
                table_config['digital_' + split_text[0][3]] = column
            elif 'ACh' in split_text[0]:
                table_config[split_text[1] + '_' + split_text[0][3]] = column
            else:
                table_config[split_text[0]] = column
        self._seq_gen_logic.table_config = table_config
        return


    def _set_channels(self, num_d_ch=None, num_a_ch=None):
        """ General function which creates the needed columns.

        @param num_d_ch:
        @param num_a_ch:

        If no argument is passed, the table is simply renewed.
        """

        if num_d_ch is None:
            num_d_ch = self._num_d_ch

        if num_a_ch is None:
            num_a_ch = self._num_a_ch

        (num_max_param, biggest_func) = self._determine_needed_parameters()

        # Erase the delegate from the column:
        for column in range(self._mw.block_editor_TableWidget.columnCount()):
            self._mw.block_editor_TableWidget.setItemDelegateForColumn(column,None)
            self._mw.block_organizer_TableWidget.setItemDelegateForColumn(column,None)

        # clear the number of columns:
        self._mw.block_editor_TableWidget.setColumnCount(0)
        self._mw.block_organizer_TableWidget.setColumnCount(0)

#        num_a_d_ch =  num_a_ch*len(self._param_a_ch) + num_d_ch*len(self._param_d_ch)
        # +1 for the displayed function
        num_a_d_ch =  num_a_ch*(num_max_param +1) + num_d_ch


        self._mw.block_editor_TableWidget.setColumnCount(num_a_d_ch)
        self._mw.block_organizer_TableWidget.setColumnCount(num_a_d_ch)

        num_a_to_create = num_a_ch
        num_d_to_create = num_d_ch

        a_created = False
        d_created = False

        column = 0
        while (column < num_a_d_ch):

            if num_a_to_create == 0 or a_created:

                self._mw.block_editor_TableWidget.setHorizontalHeaderItem(column, QtGui.QTableWidgetItem())
                self._mw.block_editor_TableWidget.horizontalHeaderItem(column).setText('DCh{:d}'.format(num_d_ch-num_d_to_create))
                self._mw.block_editor_TableWidget.setColumnWidth(column, 40)

                items_list = self._param_d_ch['CheckBox'][1:]
                checkDelegate = CheckBoxDelegate(self._mw.block_editor_TableWidget, items_list)
                self._mw.block_editor_TableWidget.setItemDelegateForColumn(column, checkDelegate)



                self._mw.block_organizer_TableWidget.setHorizontalHeaderItem(column, QtGui.QTableWidgetItem())
                self._mw.block_organizer_TableWidget.horizontalHeaderItem(column).setText('DCh{:d}'.format(num_d_ch-num_d_to_create) )
                self._mw.block_organizer_TableWidget.setColumnWidth(column, 40)

                items_list = self._param_d_ch['CheckBox'][1:]
                checkDelegate = CheckBoxDelegate(self._mw.block_organizer_TableWidget, items_list)
                self._mw.block_organizer_TableWidget.setItemDelegateForColumn(column, checkDelegate)


                if not d_created and num_d_to_create != 1:
                    d_created = True
                else:
                    a_created = False
                    d_created = False

                num_d_to_create = num_d_to_create - 1
                column = column + 1

            else:
                if num_d_to_create>0:
                    a_created = True

                param_pos = 0
                self._mw.block_editor_TableWidget.setHorizontalHeaderItem(column+param_pos, QtGui.QTableWidgetItem())
                self._mw.block_editor_TableWidget.horizontalHeaderItem(column+param_pos).setText('ACh{0:d}\nfunction'.format(num_a_ch-num_a_to_create))
                self._mw.block_editor_TableWidget.setColumnWidth(column+param_pos, 70)

                items_list = [self.get_current_function_list]

                delegate = ComboBoxDelegate(self._mw.block_editor_TableWidget, items_list)
                self._mw.block_editor_TableWidget.setItemDelegateForColumn(column+param_pos, delegate)




                self._mw.block_organizer_TableWidget.setHorizontalHeaderItem(column+param_pos, QtGui.QTableWidgetItem())
                self._mw.block_organizer_TableWidget.horizontalHeaderItem(column+param_pos).setText('ACh{0:d}\nfunction'.format(num_a_ch-num_a_to_create))
                self._mw.block_organizer_TableWidget.setColumnWidth(column+param_pos, 70)

                items_list = [self.get_current_function_list]

                delegate = ComboBoxDelegate(self._mw.block_organizer_TableWidget, items_list)
                self._mw.block_organizer_TableWidget.setItemDelegateForColumn(column+param_pos, delegate)


                for param_pos, parameter in enumerate(self.get_func_config()[biggest_func]):

                    # initial block:

                    items_list = self.get_func_config()[biggest_func][parameter]

                    if 'disp_unit' in items_list.keys():
                        unit_text = items_list['disp_unit'] + items_list['unit']
                    else:
                        unit_text = items_list['unit']

                    self._mw.block_editor_TableWidget.setHorizontalHeaderItem(column+param_pos+1, QtGui.QTableWidgetItem())
                    self._mw.block_editor_TableWidget.horizontalHeaderItem(column+param_pos+1).setText('ACh{0:d}\n{1} ({2})'.format(num_a_ch-num_a_to_create, parameter, unit_text))
                    self._mw.block_editor_TableWidget.setColumnWidth(column+param_pos+1, 100)

                    # add the new properties to the whole column through delegate:


                    # extract the classname from the _param_a_ch list to be able to deligate:
                    delegate = DoubleSpinBoxDelegate(self._mw.block_editor_TableWidget, [items_list])
                    self._mw.block_editor_TableWidget.setItemDelegateForColumn(column+param_pos+1, delegate)




                    self._mw.block_organizer_TableWidget.setHorizontalHeaderItem(column+param_pos+1, QtGui.QTableWidgetItem())
                    self._mw.block_organizer_TableWidget.horizontalHeaderItem(column+param_pos+1).setText('ACh{0:d}\n{1} ({2})'.format(num_a_ch-num_a_to_create, parameter, unit_text))
                    self._mw.block_organizer_TableWidget.setColumnWidth(column+param_pos+1, 100)

                    # add the new properties to the whole column through delegate:


                    # extract the classname from the _param_a_ch list to be able to deligate:
                    delegate = DoubleSpinBoxDelegate(self._mw.block_organizer_TableWidget, [items_list])
                    self._mw.block_organizer_TableWidget.setItemDelegateForColumn(column+param_pos+1, delegate)

                column = column + (num_max_param +1)
                num_a_to_create = num_a_to_create - 1

        self._num_a_ch = num_a_ch
        self._num_d_ch = num_d_ch


        self.insert_parameters(num_a_d_ch)

        self.initialize_row_init_block(0,self._mw.block_editor_TableWidget.rowCount())
        self.initialize_row_repeat_block(0,self._mw.block_organizer_TableWidget.rowCount())
        self.update_current_table_config()

    def initialize_row_init_block(self, start_row, stop_row=None):
        """

        @param start_row:
        @param stop_row:

        """
        if stop_row is None:
            stop_row = start_row +1

        for col_num in range(self._mw.block_editor_TableWidget.columnCount()):

            for row_num in range(start_row,stop_row):
                # get the model, here are the data stored:
                model = self._mw.block_editor_TableWidget.model()
                # get the corresponding index of the current element:
                index = model.index(row_num, col_num)
                # get the initial values of the delegate class which was
                # uses for this column:
                ini_values = self._mw.block_editor_TableWidget.itemDelegateForColumn(col_num).get_initial_value()
                # set initial values:
                model.setData(index, ini_values[0], ini_values[1])

    def initialize_row_repeat_block(self, start_row, stop_row=None):
        """
        @param start_row:
        @param stop_row:

        """
        if stop_row is None:
            stop_row = start_row +1

        for col_num in range(self._mw.block_organizer_TableWidget.columnCount()):

            for row_num in range(start_row,stop_row):
                # get the model, here are the data stored:
                model = self._mw.block_organizer_TableWidget.model()
                # get the corresponding index of the current element:
                index = model.index(row_num, col_num)
                # get the initial values of the delegate class which was
                # uses for this column:
                ini_values = self._mw.block_organizer_TableWidget.itemDelegateForColumn(col_num).get_initial_value()
                # set initial values:
                model.setData(index, ini_values[0], ini_values[1])

    def count_analog_channels(self):
        """ Get the number of currently displayed analog channels.

        @return int: number of analog channels

        The number of analog channal are counted and return and additionally
        the internal counter variable _num_a_ch is updated. The counting
        procedure is based on the block_editor_TableWidget since it is assumed
        that all operation on the block_editor_TableWidget is also applied on
        block_organizer_TableWidget.
        """

        count_a_ch = 0
        # there must be definitly less analog channels then available columns
        # in the table, therefore the number of columns can be used as the
        # upper border.
        for poss_a_ch in range(self._mw.block_editor_TableWidget.columnCount()):
            for column in range(self._mw.block_editor_TableWidget.columnCount()):
                if ('ACh'+str(poss_a_ch)) in self._mw.block_editor_TableWidget.horizontalHeaderItem(column).text():
                    # analog channel found, break the inner loop to
                    count_a_ch = count_a_ch + 1
                    break

        self._num_a_ch = count_a_ch
        return self._num_a_ch
        

    ###########################################################################
    ###        Methods related to Settings for the 'Analysis' Tab:          ###
    ###########################################################################

    #FIXME: Implement the setting for 'Analysis' tab.

    def _activate_analysis_settings_ui(self, e):
        """ Initialize, connect and configure the Settings of 'Analysis' Tab.

        @param Fysom.event e: Event Object of Fysom
        """

        pass

    def _deactivate_analysis_settings_ui(self, e):
        """ Disconnects the configuration of the Settings for 'Analysis' Tab.

        @param Fysom.event e: Event Object of Fysom
        """

        pass


    ###########################################################################
    ###     Methods related to the Tab 'Analysis' in the Pulsed Window:     ###
    ###########################################################################

    def _activate_analysis_ui(self, e):
        """ Initialize, connect and configure the 'Analysis' Tab.

        @param Fysom.event e: Event Object of Fysom
        """
        # Get the image from the logic
        # pulsed measurement tab
        self.signal_image = pg.PlotDataItem(self._pulsed_measurement_logic.signal_plot_x, self._pulsed_measurement_logic.signal_plot_y)
        self.lasertrace_image = pg.PlotDataItem(self._pulsed_measurement_logic.laser_plot_x, self._pulsed_measurement_logic.laser_plot_y)
        self.sig_start_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(QtGui.QColor(255,0,0,255)))
        self.sig_end_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(QtGui.QColor(255,0,0,255)))
        self.ref_start_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(QtGui.QColor(0,255,0,255)))
        self.ref_end_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(QtGui.QColor(0,255,0,255)))
#
#        # Add the display item to the xy VieWidget, which was defined in
#        # the UI file.
        self._mw.signal_plot_ViewWidget.addItem(self.signal_image)
        self._mw.lasertrace_plot_ViewWidget.addItem(self.lasertrace_image)
        self._mw.lasertrace_plot_ViewWidget.addItem(self.sig_start_line)
        self._mw.lasertrace_plot_ViewWidget.addItem(self.sig_end_line)
        self._mw.lasertrace_plot_ViewWidget.addItem(self.ref_start_line)
        self._mw.lasertrace_plot_ViewWidget.addItem(self.ref_end_line)
        self._mw.signal_plot_ViewWidget.showGrid(x=True, y=True, alpha=0.8)


        # Set the state button as ready button as default setting.
        self._mw.idle_radioButton.click()

        # Configuration of the comboWidget
        self._mw.binning_comboBox.addItem(str(self._pulsed_measurement_logic.fast_counter_status['binwidth_ns']))
        self._mw.binning_comboBox.addItem(str(self._pulsed_measurement_logic.fast_counter_status['binwidth_ns']*2.))
        # set up the types of the columns and create a pattern based on
        # the desired settings:

#        # Add Validators to InputWidgets
        validator = QtGui.QDoubleValidator()
        validator2 = QtGui.QIntValidator()

        # pulsed measurement tab
        self._mw.frequency_InputWidget.setValidator(validator)
        self._mw.power_InputWidget.setValidator(validator)
        self._mw.analysis_period_InputWidget.setValidator(validator)
        self._mw.numlaser_InputWidget.setValidator(validator2)
        self._mw.taustart_InputWidget.setValidator(validator)
        self._mw.tauincrement_InputWidget.setValidator(validator)
        self._mw.signal_start_InputWidget.setValidator(validator2)
        self._mw.signal_length_InputWidget.setValidator(validator2)
        self._mw.reference_start_InputWidget.setValidator(validator2)
        self._mw.reference_length_InputWidget.setValidator(validator2)

        # Fill in default values:

        # pulsed measurement tab
        self._mw.frequency_InputWidget.setText(str(2870.))
        self._mw.power_InputWidget.setText(str(-30.))
        self._mw.numlaser_InputWidget.setText(str(50))
        self._mw.taustart_InputWidget.setText(str(1))
        self._mw.tauincrement_InputWidget.setText(str(1))
        self._mw.lasertoshow_spinBox.setRange(0, 50)
        self._mw.lasertoshow_spinBox.setPrefix("#")
        self._mw.lasertoshow_spinBox.setSpecialValueText("sum")
        self._mw.lasertoshow_spinBox.setValue(0)
        self._mw.signal_start_InputWidget.setText(str(5))
        self._mw.signal_length_InputWidget.setText(str(200))
        self._mw.reference_start_InputWidget.setText(str(500))
        self._mw.reference_length_InputWidget.setText(str(200))
        self._mw.expected_duration_TimeLabel.setText('00:00:00:00')
        self._mw.elapsed_time_label.setText('00:00:00:00')
        self._mw.elapsed_sweeps_LCDNumber.setDigitCount(0)
        self._mw.analysis_period_InputWidget.setText(str(5))
        self._mw.laser_channel_LineEdit.setText(str(1))
        self._mw.refocus_interval_LineEdit.setText(str(5))
        self._mw.odmr_refocus_interval_LineEdit.setText(str(5))
        self._mw.counter_safety_LineEdit.setText(str(0))

        self._mw.show_fft_plot_CheckBox.setChecked(False)
        self._mw.ignore_first_laser_CheckBox.setChecked(False)
        self._mw.ignore_last_laser_CheckBox.setChecked(True)
        self._mw.alternating_sequence_CheckBox.setChecked(False)
        self._mw.tau_defined_in_sequence_CheckBox.setChecked(False)

        # ---------------------------------------------------------------------
        #                         Connect signals
        # ---------------------------------------------------------------------

        # Connect the RadioButtons and connect to the events if they are clicked:
        # pulsed measurement tab
        self._mw.idle_radioButton.toggled.connect(self.idle_clicked)
        self._mw.run_radioButton.toggled.connect(self.run_clicked)

        self._mw.pull_data_pushButton.clicked.connect(self.pull_data_clicked)
        self._mw.pull_data_pushButton.setEnabled(False)

        self._pulsed_measurement_logic.signal_laser_plot_updated.connect(self.refresh_lasertrace_plot)
        self._pulsed_measurement_logic.signal_signal_plot_updated.connect(self.refresh_signal_plot)
        self._pulsed_measurement_logic.signal_time_updated.connect(self.refresh_elapsed_time)
        # sequence generator tab


        # Connect InputWidgets to events
        # pulsed measurement tab
        self._mw.numlaser_InputWidget.editingFinished.connect(self.seq_parameters_changed)
        self._mw.lasertoshow_spinBox.valueChanged.connect(self.seq_parameters_changed)
        self._mw.taustart_InputWidget.editingFinished.connect(self.seq_parameters_changed)
        self._mw.tauincrement_InputWidget.editingFinished.connect(self.seq_parameters_changed)
        self._mw.signal_start_InputWidget.editingFinished.connect(self.analysis_parameters_changed)
        self._mw.signal_length_InputWidget.editingFinished.connect(self.analysis_parameters_changed)
        self._mw.reference_start_InputWidget.editingFinished.connect(self.analysis_parameters_changed)
        self._mw.reference_length_InputWidget.editingFinished.connect(self.analysis_parameters_changed)
        self._mw.analysis_period_InputWidget.editingFinished.connect(self.analysis_parameters_changed)

        self.seq_parameters_changed()
        self.analysis_parameters_changed()
#
#        self._mw.actionSave_Data.triggered.connect(self.save_clicked)


    def _deactivate_analysis_ui(self, e):
        """ Disconnects the configuration for 'Analysis' Tab.

        @param Fysom.event e: Event Object of Fysom
        """

        self.idle_clicked()

        # disconnect signals
        self._mw.idle_radioButton.toggled.disconnect()
        self._mw.run_radioButton.toggled.disconnect()
        self._pulsed_measurement_logic.signal_laser_plot_updated.disconnect()
        self._pulsed_measurement_logic.signal_signal_plot_updated.disconnect()
        self._mw.numlaser_InputWidget.editingFinished.disconnect()
        self._mw.lasertoshow_spinBox.valueChanged.disconnect()

    def idle_clicked(self):
        """ Stopp the scan if the state has switched to idle. """
        self._pulsed_measurement_logic.stop_pulsed_measurement()
        self._mw.frequency_InputWidget.setEnabled(True)
        self._mw.power_InputWidget.setEnabled(True)
        self._mw.binning_comboBox.setEnabled(True)
        self._mw.pull_data_pushButton.setEnabled(False)

    def run_clicked(self, enabled):
        """ Manages what happens if pulsed measurement is started.

        @param bool enabled: start scan if that is possible
        """

        #Firstly stop any scan that might be in progress
        self._pulsed_measurement_logic.stop_pulsed_measurement()
        #Then if enabled. start a new scan.
        if enabled:
            self._mw.frequency_InputWidget.setEnabled(False)
            self._mw.power_InputWidget.setEnabled(False)
            self._mw.binning_comboBox.setEnabled(False)
            self._mw.pull_data_pushButton.setEnabled(True)
            self._pulsed_measurement_logic.start_pulsed_measurement()

    def pull_data_clicked(self):
        self._pulsed_measurement_logic.manually_pull_data()

    def generate_rabi_clicked(self):
        # calculate parameters in terms of timebins/samples
        samplerate = float(self._mw.pg_timebase_InputWidget.text())
        mw_freq = np.round(float(self._mw.rabi_mwfreq_InputWidget.text()) * 10e9 * samplerate)
        mw_power = np.round(float(self._mw.rabi_mwpower_InputWidget.text()) * 10e9 * samplerate)
        waittime = np.round(float(self._mw.rabi_waittime_InputWidget.text()) * 10e9 * samplerate)
        lasertime = np.round(float(self._mw.rabi_waittime_InputWidget.text()) * 10e9 * samplerate)
        tau_start = np.round(float(self._mw.rabi_taustart_InputWidget.text()) * 10e9 * samplerate)
        tau_end = np.round(float(self._mw.rabi_tauend_InputWidget.text()) * 10e9 * samplerate)
        tau_incr = np.round(float(self._mw.rabi_tauincrement_InputWidget.text()) * 10e9 * samplerate)
        # generate sequence
        self._sequence_generator_logic.generate_rabi(mw_freq, mw_power, waittime, lasertime, tau_start, tau_end, tau_incr)


    def refresh_lasertrace_plot(self):
        ''' This method refreshes the xy-plot image
        '''
        self.lasertrace_image.setData(self._pulsed_measurement_logic.laser_plot_x, self._pulsed_measurement_logic.laser_plot_y)

    def refresh_signal_plot(self):
        ''' This method refreshes the xy-matrix image
        '''
        self.signal_image.setData(self._pulsed_measurement_logic.signal_plot_x, self._pulsed_measurement_logic.signal_plot_y)

    def refresh_elapsed_time(self):
        ''' This method refreshes the elapsed time of the measurement
        '''
        self._mw.elapsed_time_label.setText(self._pulsed_measurement_logic.elapsed_time_str)

    def seq_parameters_changed(self):
        laser_num = int(self._mw.numlaser_InputWidget.text())
        tau_start = int(self._mw.taustart_InputWidget.text())
        tau_incr = int(self._mw.tauincrement_InputWidget.text())
        mw_frequency = float(self._mw.frequency_InputWidget.text())
        mw_power = float(self._mw.power_InputWidget.text())
        self._mw.lasertoshow_spinBox.setRange(0, laser_num)
        laser_show = self._mw.lasertoshow_spinBox.value()
        if (laser_show > laser_num):
            self._mw.lasertoshow_spinBox.setValue(0)
            laser_show = self._mw.lasertoshow_spinBox.value()
        tau_vector = np.array(range(tau_start, tau_start + tau_incr*laser_num, tau_incr))
        self._pulsed_measurement_logic.running_sequence_parameters['tau_vector'] = tau_vector
        self._pulsed_measurement_logic.running_sequence_parameters['number_of_lasers'] = laser_num
        self._pulsed_measurement_logic.display_pulse_no = laser_show
        self._pulsed_measurement_logic.mykrowave_freq = mw_frequency
        self._pulsed_measurement_logic.mykrowave_power = mw_power
        return


    def analysis_parameters_changed(self):
        sig_start = int(self._mw.signal_start_InputWidget.text())
        sig_length = int(self._mw.signal_length_InputWidget.text())
        ref_start = int(self._mw.reference_start_InputWidget.text())
        ref_length = int(self._mw.reference_length_InputWidget.text())
        timer_interval = float(self._mw.analysis_period_InputWidget.text())
        self.signal_start_bin = sig_start
        self.signal_width_bins = sig_length
        self.norm_start_bin = ref_start
        self.norm_width_bins = ref_length
        self.sig_start_line.setValue(sig_start)
        self.sig_end_line.setValue(sig_start+sig_length)
        self.ref_start_line.setValue(ref_start)
        self.ref_end_line.setValue(ref_start+ref_length)
        self._pulsed_measurement_logic.signal_start_bin = sig_start
        self._pulsed_measurement_logic.signal_width_bin = sig_length
        self._pulsed_measurement_logic.norm_start_bin = ref_start
        self._pulsed_measurement_logic.norm_width_bin = ref_length
        self._pulsed_measurement_logic.change_timer_interval(timer_interval)
        return

    def check_input_with_samplerate(self):
        pass


    def save_clicked(self):
        self._pulsed_measurement_logic._save_data()
        return


    def current_sequence_changed(self):
        ''' This method updates the current sequence variables in the sequence generator logic.
        '''
        name = self._mw.sequence_list_comboBox.currentText()
        self._sequence_generator_logic.set_current_sequence(name)
        self.create_table()
        repetitions = self._sequence_generator_logic._current_sequence_parameters['repetitions']
        self._mw.repetitions_lineEdit.setText(str(repetitions))
        return


    def sequence_to_run_changed(self):
        ''' This method updates the parameter set of the sequence to run in the PulseAnalysisLogic.
        '''
        name = self._mw.sequence_name_comboBox.currentText()
        self._pulse_analysis_logic.update_sequence_parameters(name)
        return


    ###########################################################################
    ###   Methods related to Settings for the 'Sequence Generator' Tab:     ###
    ###########################################################################

    #FIXME: Implement the setting for 'Sequence Generator' tab.

    def _activate_sequence_settings_ui(self, e):
        """ Initialize, connect and configure the Settings of the
        'Sequence Generator' Tab.

        @param Fysom.event e: Event Object of Fysom
        """

        pass

    def _deactivate_sequence_settings_ui(self, e):
        """ Disconnects the configuration of the Settings for the
        'Sequence Generator' Tab.

        @param Fysom.event e: Event Object of Fysom
        """

        pass


    ###########################################################################
    ###         Methods related to the Tab 'Sequence Generator':            ###
    ###########################################################################

    #FIXME: Implement the 'Sequence Generator' tab.

    def _activate_sequence_generator_ui(self, e):
        """ Initialize, connect and configure the 'Sequence Generator' Tab.

        @param Fysom.event e: Event Object of Fysom
        """
        pass

    def _deactivate_sequence_generator_ui(self, e):
        """ Disconnects the configuration for 'Sequence Generator' Tab.

        @param Fysom.event e: Event Object of Fysom
        """
        pass

    ###########################################################################
    ###    Methods related to Settings for the 'Pulse Extraction' Tab:      ###
    ###########################################################################

    #FIXME: Implement the setting for 'Pulse Extraction' tab.

    def _activate_pulse_extraction_settings_ui(self, e):
        """ Initialize, connect and configure the Settings of the
        'Sequence Generator' Tab.

        @param Fysom.event e: Event Object of Fysom
        """

        pass

    def _deactivate_pulse_extraction_settings_ui(self, e):
        """ Disconnects the configuration of the Settings for the
        'Sequence Generator' Tab.

        @param Fysom.event e: Event Object of Fysom
        """

        pass


    ###########################################################################
    ###          Methods related to the Tab 'Pulse Extraction':             ###
    ###########################################################################

    #FIXME: Implement the 'Pulse Extraction' tab.

    def _activate_pulse_extraction_ui(self, e):
        """ Initialize, connect and configure the 'Pulse Extraction' Tab.

        @param Fysom.event e: Event Object of Fysom
        """
        pass

    def _deactivate_pulse_extraction_ui(self, e):
        """ Disconnects the configuration for 'Pulse Extraction' Tab.

        @param Fysom.event e: Event Object of Fysom
        """
        pass