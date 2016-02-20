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
import re
import inspect

from gui.guibase import GUIBase
from core.util.mutex import Mutex

# Rather than import the ui*.py file here, the ui*.ui file itself is loaded by uic.loadUI in the QtGui classes below.

#FIXME: Display the Pulse
#FIXME: save the length in sample points (bins)
#FIXME: adjust the length to the bins
#FIXME: insert warning text in choice of channels
#FIXME: save the pattern of the table to a file. Think about possibilities to read in from file if number of channels is different. Therefore make also a load function.
#FIXME: connect the current default value of length of the dspinbox with
#       the minimal sequence length and the sampling rate.
#FIXME: Later that should be able to round up the values directly within
#       the entering in the dspinbox for a consistent display of the
#       sequence length.
#FIXME: Use the desired unit representation to display the value from the logic


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

    def __init__(self, parent, items_list):
        # Use the constructor of the inherited class.
        QtGui.QStyledItemDelegate.__init__(self, parent)
        self.items_list = items_list  # pass to the object a
                                                # reference to the calling
                                                # function, so that it can
                                                # check every time the value

        self.get_list = self.items_list['get_list_method']

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

        editor.addItems(self.get_list())
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
        editor = QtGui.QSpinBox(parent)
        self.editor = editor
        editor.setMinimum(self.items_list['min'])
        editor.setMaximum(self.items_list['max'])
        editor.setSingleStep(self.items_list['view_stepsize'])
        editor.installEventFilter(self)
        editor.setValue(self.items_list['init_val'])
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
            value = self.items_list['init_val']
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

        editor = QtGui.QCheckBox(parent)
        editor.setCheckState(self.items_list['init_val'])
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
        self.items_list = items_list

        self.unit_list = {'p':1e-12, 'n':1e-9, 'micro':1e-6, 'm':1e-3, 'k':1e3, 'M':1e6, 'G':1e9, 'T':1e12}

        if 'unit_prefix' in self.items_list.keys():
            self.norm = self.unit_list[self.items_list['unit_prefix']]
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

class PredefinedMethodsDialog(QtGui.QDialog):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_predefined_methods.ui')

        # Load it
        super(PredefinedMethodsDialog, self).__init__()

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

        # create the Predefined methods Dialog
        self._pm = PredefinedMethodsDialog()


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


    def show_prepared_methods(self):
        """ Opens the prepared methods Window."""
        self._pm.show()

    def update_block_settings(self):
        """ Write new block settings from the gui to the file. """

        self._mw.block_editor_TableWidget.blockSignals(True)

        channel_config = self.get_hardware_constraints()['channel_config']

        ch_settings = (self._bs.analog_channels_SpinBox.value(), self._bs.digital_channels_SpinBox.value())

        if ch_settings in channel_config:

            self._set_block_editor_columns(num_d_ch=ch_settings[1], num_a_ch=ch_settings[0])

            self._seq_gen_logic.set_active_channels(digital=ch_settings[1],
                                                analogue=ch_settings[0])
        else:
            self.logMsg('Desired channel configuration (analog, digital) as '
                        '{0} not possible, since the hardware does not '
                        'support it!/n'
                        'Restore previous configuration.'.format(ch_settings),
                        msgType='warning')
            self.keep_former_block_settings()

        self._mw.block_editor_TableWidget.blockSignals(False)


    def keep_former_block_settings(self):
        """ Keep the old block settings and restores them in the gui. """

        self._bs.digital_channels_SpinBox.setValue(self._num_d_ch)
        self._bs.analog_channels_SpinBox.setValue(self._num_a_ch)
        self._seq_gen_logic.set_active_channels(digital=self._num_d_ch,
                                                analogue=self._num_a_ch)

    def get_current_function_list(self):
        """ Retrieve the functions, which are chosen by the user.

        @return: list[] with strings of the used functions. Names are based on
                 the passed func_config dict from the logic. Depending on the
                 settings, a current function list is generated.
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
        self._mw.sample_freq_DSpinBox.editingFinished.connect(self.update_sample_rate)

        sample_min, sample_max, sample_step = self.get_hardware_constraints()['sample_rate']
        self._mw.sample_freq_DSpinBox.setMinimum(sample_min/1e6)
        self._mw.sample_freq_DSpinBox.setMaximum(sample_max/1e6)
        self._mw.sample_freq_DSpinBox.setSingleStep(sample_step/1e6)
        self._mw.sample_freq_DSpinBox.setDecimals( (np.log10(sample_step/1e6)* -1) )
        self.set_sample_rate(sample_max)


        self._mw.curr_block_bins_SpinBox.setMaximum(2**31 -1)
        self._mw.curr_block_laserpulses_SpinBox.setMaximum(2**31 -1)
        self._mw.curr_ensemble_bins_SpinBox.setMaximum(2**31 -1)
        self._mw.curr_ensemble_length_DSpinBox.setMaximum(np.inf)

        # connect the signals for the block editor:
        self._mw.block_add_last_PushButton.clicked.connect(self.block_editor_add_row_after_last)
        self._mw.block_del_last_PushButton.clicked.connect(self.block_editor_delete_row_last)
        self._mw.block_add_sel_PushButton.clicked.connect(self.block_editor_add_row_before_selected)
        self._mw.block_del_sel_PushButton.clicked.connect(self.block_editor_delete_row_selected)
        self._mw.block_clear_PushButton.clicked.connect(self.block_editor_clear_table)

        self._mw.curr_block_load_PushButton.clicked.connect(self.load_pulse_block)
        self._mw.curr_block_save_PushButton.clicked.connect(self.block_editor_save_clicked)
        self._mw.curr_block_del_PushButton.clicked.connect(self.block_editor_delete_clicked)

        # connect the signals for the block organizer:
        self._mw.organizer_add_last_PushButton.clicked.connect(self.block_organizer_add_row_after_last)
        self._mw.organizer_del_last_PushButton.clicked.connect(self.block_organizer_delete_row_last)
        self._mw.organizer_add_sel_PushButton.clicked.connect(self.block_organizer_add_row_before_selected)
        self._mw.organizer_del_sel_PushButton.clicked.connect(self.block_organizer_delete_row_selected)
        self._mw.organizer_clear_PushButton.clicked.connect(self.block_organizer_clear_table)

        # connect the signals for the "Upload on device" section
        self._mw.upload_sample_ensemble_PushButton.clicked.connect(self.sample_ensemble_clicked)
        self._mw.upload_to_device_PushButton.clicked.connect(self.upload_to_device_clicked)
        self._mw.upload_load_channel_PushButton.clicked.connect(self.load_into_channel_clicked)

        # connect the menue to the actions:
        self._mw.action_Settings_Block_Generation.triggered.connect(self.show_block_settings)
        self._mw.actionOpen_Prepared_Methods.triggered.connect(self.show_prepared_methods)

        # emit a trigger event when for all mouse click and keyboard click events:
        self._mw.block_editor_TableWidget.setEditTriggers(QtGui.QAbstractItemView.AllEditTriggers)
        self._mw.block_organizer_TableWidget.setEditTriggers(QtGui.QAbstractItemView.AllEditTriggers)

        # connect update signals of the sequence_generator_logic
        self._seq_gen_logic.signal_block_list_updated.connect(self.update_block_list)
        self._seq_gen_logic.signal_ensemble_list_updated.connect(self.update_ensemble_list)
        self._seq_gen_logic.signal_sequence_list_updated.connect(self.update_sequence_list)

        channel_config = self.get_hardware_constraints()['channel_config'][-1]
        self._set_block_editor_columns(num_d_ch=channel_config[1], num_a_ch=channel_config[0])

        self.keep_former_block_settings()
        # A dictionary containing the mathematical function names to choose
        # from in the block editor with corresponding lists of needed
        # parameters like phase, frequency etc. This should be provided by the
        #  "math logic".

        # initialize the lists of available blocks, ensembles and sequences
        self.update_block_list()
        self.update_ensemble_list()
        self.update_sequence_list()

        self._mw.curr_block_generate_PushButton.clicked.connect(self.generate_pulse_block)

        self._mw.curr_ensemble_generate_PushButton.clicked.connect(self.generate_pulse_block_ensemble)

        self.set_cfg_param_pbe()
        self._mw.block_editor_TableWidget.itemChanged.connect(self._update_current_pulse_block)
        self._mw.laserchannel_ComboBox.currentIndexChanged.connect(self._update_current_pulse_block)

        self._seq_gen_logic.signal_ensemble_list_updated.connect(self.update_pulse_block_ensemble_list)

        self._set_organizer_columns()

        self._mw.block_organizer_TableWidget.itemChanged.connect(self._update_current_pulse_block_ensemble)

        self._mw.curr_ensemble_del_PushButton.clicked.connect(self.block_organizer_delete_clicked)


        self._create_control_for_prepared_methods()

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
        self._pm.close()

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


    def get_current_pb_list(self):
        """ Retrieve the available Pulse_Block objects from the logic.

        @return: list[] with strings descriping the available Pulse_Block
                        objects.
        """

        return self._seq_gen_logic.saved_pulse_blocks


    def update_sample_rate(self):
        """Updates the current sample rate in the logic"""
        sample_rate = self._mw.sample_freq_DSpinBox.value()
        self._seq_gen_logic.set_sample_rate(sample_rate*1e6)
        self._update_current_pulse_block()
        self._update_current_pulse_block_ensemble()

    def set_sample_rate(self, sample_rate):
        """ Set the current sample rate in the spin_box and in the logic.

        @param float sample_rate: sample rate in Hz
        """

        self._mw.sample_freq_DSpinBox.setValue(sample_rate/1e6)
        self._seq_gen_logic.set_sample_rate(sample_rate)


    def get_sample_rate(self):
        """ Retrieve the current sample rate

        @return: float, sample_rate in Hz
        """
        return self._mw.sample_freq_DSpinBox.value()*1e6

    def sample_ensemble_clicked(self):
        """
        This method is called when the user clicks on "sample"
        """
        # Get the ensemble name to be uploaded from the ComboBox
        ensemble_name = self._mw.upload_ensemble_ComboBox.currentText()
        # Sample the ensemble via logic module
        self._seq_gen_logic.sample_ensemble(ensemble_name, True, True)
        return

    def upload_to_device_clicked(self):
        """
        This method is called when the user clicks on "load to channel"
        """
        # Get the ensemble name to be uploaded from the ComboBox
        ensemble_name = self._mw.upload_ensemble_ComboBox.currentText()
        # Upload the ensemble via logic module
        self._seq_gen_logic.upload_file(ensemble_name)
        return

    def load_into_channel_clicked(self):
        """
        This method is called when the user clicks on "load to channel"
        """
        # Get the ensemble name to be uploaded from the ComboBox
        ensemble_name = self._mw.upload_ensemble_ComboBox.currentText()
        # Sample and upload the ensemble via logic module
        self._seq_gen_logic.load_asset(ensemble_name)
        return

    def update_block_list(self):
        """
        This method is called upon signal_block_list_updated emit of the sequence_generator_logic.
        Updates all ComboBoxes showing generated blocks.
        """
        # updated list of all generated blocks
        new_list = self._seq_gen_logic.saved_pulse_blocks
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
        new_list = self._seq_gen_logic.saved_pulse_block_ensembles
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


    def get_add_pbe_param(self):
        """ Retrieve the additional parameter configuration for the
        Pulse_Block_Element objects from the logic.

        @return: dict with the configurations for the additional parameters.
        """
        return self._seq_gen_logic.get_add_pbe_param()

    def get_add_pb_param(self):
        """ Retrieve the additional parameter configuration for the
        Pulse_Block objects from the logic.

        @return: dict with the configurations for the additional parameters.
        """
        return self._seq_gen_logic.get_add_pb_param()


    def get_element_in_block_table(self, row, column):
        """ Simplified wrapper function to get the data from a specific cell
            in the block table.

        @param int row: row index
        @param int column: column index
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

    def set_element_in_block_table(self, row, column, value):
        """ Simplified wrapper function to set the data to a specific cell
            in the block table.

        @param int row: row index
        @param int column: column index

        Note that the order of the arguments in this function (first row index
        and then column index) was taken from the Qt convention.
        A type check will be performed for the passed value argument. If the
        type does not correspond to the delegate, then the value will not be
        changed. You have to ensure that
        """

        #FIXME: that method should get the values in SI metric and convert them
        #        to the desired display.

        tab = self._mw.block_editor_TableWidget
        model = tab.model()
        access = tab.itemDelegateForColumn(column).model_data_access
        data = tab.model().index(row, column).data(access)
        if type(data) == type(value):
            model.setData(model.index(row,column), value, access)
        else:
            self.logMsg('The cell ({0},{1}) in block table could not be '
                        'assigned with the value="{2}", since the type "{3}" '
                        'of the cell from the delegated type differs from '
                        '"{4}" of the value!\nPrevious value will be '
                        'kept.'.format(row, column, value, type(data),
                                       type(value) ) , msgType='warning')



    def test_func(self, arg=None):


        self.logMsg('Item changed. {0}'.format(arg), msgType='warning')


    def _update_current_pulse_block(self):

        length = 0.0 # in ns
        bin_length = 0
        col_ind = self._cfg_param_pbe['length']

        laser_channel = self._mw.laserchannel_ComboBox.currentText()
        num_laser_ch = 0

        # Simple search routine:
        if 'A' in laser_channel:
            # extract with regular expression module the number from the
            # string:
            num = re.findall('\d+', laser_channel)
            laser_column = self._cfg_param_pbe['function_'+str(num[0])]
        elif 'D' in laser_channel:
            num = re.findall('\d+', laser_channel)
            laser_column = self._cfg_param_pbe['digital_'+str(num[0])]
        else:
            return

        for row_ind in range(self._mw.block_editor_TableWidget.rowCount()):
            curr_length = self.get_element_in_block_table(row_ind, col_ind)
            curr_bin_length = int(np.round(curr_length*(self.get_sample_rate()/1e9)))
            length = length + curr_length
            bin_length = bin_length + curr_bin_length

            laser_val =self.get_element_in_block_table(row_ind, laser_column)
            if (laser_val=='DC') or (laser_val==2):
                num_laser_ch = num_laser_ch +1


        self._mw.curr_block_length_DSpinBox.setValue(length/1000.0) # in microns
        self._mw.curr_block_bins_SpinBox.setValue(bin_length)
        self._mw.curr_block_laserpulses_SpinBox.setValue(num_laser_ch)


    def _update_current_pulse_block_ensemble(self):

        length_mu = 0.0 # in microseconds
        length_bin = 0
        num_laser_pulses = 0
        pulse_block_col = self._cfg_param_pb['pulse_block']

        reps_col = self._cfg_param_pb['repetition']

        if len(self._seq_gen_logic.saved_pulse_blocks) > 0:
            for row_ind in range(self._mw.block_organizer_TableWidget.rowCount()):
                pulse_block_name = self.get_element_in_organizer_table(row_ind, pulse_block_col)

                block_obj = self._seq_gen_logic.get_block(pulse_block_name)



                reps = self.get_element_in_organizer_table(row_ind, reps_col)

                # Calculate the length via the gaussian summation formula:
                length_bin = int(length_bin + block_obj.init_length_bins*(reps+1) + ((reps+1)*((reps+1)+1)/2)*block_obj.increment_bins)

                num_laser_pulses = num_laser_pulses + block_obj.num_laser_pulses * (reps+1)


            length_mu = (length_bin/self.get_sample_rate())*1e6 # in microns

        self._mw.curr_ensemble_length_DSpinBox.setValue(length_mu)

        self._mw.curr_ensemble_bins_SpinBox.setValue(length_bin)

        self._mw.curr_ensemble_laserpulses_SpinBox.setValue(num_laser_pulses)

    def get_block_table(self):
        """ Convert block table data to numpy array.

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
                self.logMsg('Type definition not found in the block table.'
                            '\nType is neither a string, integer or float. '
                            'Include that type in the get_block_table method!',
                            msgType='error')

        # remove the last two elements since these are a comma and a space:
        structure = structure[:-2]
        table = np.zeros(tab.rowCount(), dtype=structure)

        # fill the table:
        for column in range(tab.columnCount()):
            for row in range(tab.rowCount()):
                # self.logMsg(, msgType='status')
                table[row][column] = self.get_element_in_block_table(row, column)

        return table

    def load_pulse_block(self):
        """ Loads the current selected Pulse_Block object from the logic into
            the editor.

            Unfortuanetly this method needs to know how Pulse_Block objects
            are looking like and cannot be that general.
        """

        current_block_name = self._mw.saved_blocks_ComboBox.currentText()
        block = self._seq_gen_logic.get_block(current_block_name, set_as_current_block=True)
        self.block_editor_clear_table()

        rows = len(block.element_list)

        block_config_dict = self.get_cfg_param_pbe()

        self.block_editor_add_row_after_last(rows-1) # since one is already present

        for row_index, pulse_block_element in enumerate(block.element_list):

            # set at first all digital channels:
            for digital_ch in range(pulse_block_element.digital_channels):
                column = block_config_dict['digital_'+str(digital_ch)]
                value = pulse_block_element.markers_on[digital_ch]
                if value:
                    value=0
                else:
                    value=2
                self.set_element_in_block_table(row_index,column, value)

            # now set all parameters for the analog channels:
            for analog_ch in range(pulse_block_element.analogue_channels):

                # the function text:
                column = block_config_dict['function_'+str(analog_ch)]
                func_text = pulse_block_element.pulse_function[analog_ch]
                self.set_element_in_block_table(row_index, column, func_text)

                # then the parameter dictionary:
                parameter_dict = pulse_block_element.parameters[analog_ch]
                for parameter in parameter_dict:
                    column = block_config_dict[parameter + '_' +str(analog_ch)]
                    value = np.float(parameter_dict[parameter])
                    self.set_element_in_block_table(row_index, column, value)


            #FIXME: that is not really general, since the name 'use_as_tau' is
            #       directly taken. That must be more general! Right now it is
            #       hard to make it in a general way.

            # now set use as tau parameter:
            column = block_config_dict['use']
            value = pulse_block_element.use_as_tau / (self.get_sample_rate() /1e9 )
            # the ckeckbox has a special input value, it is 0, 1 or 2. (tri-state)
            if value:
                value=0
            else:
                value=2
            self.set_element_in_block_table(row_index, column, value)

            # and set the init_length_bins:
            column = block_config_dict['length']
            value = pulse_block_element.init_length_bins / (self.get_sample_rate() /1e9 )
            self.set_element_in_block_table(row_index, column, value)

            # and set the increment parameter
            column = block_config_dict['increment']
            value = pulse_block_element.increment_bins / (self.get_sample_rate() /1e9 )
            self.set_element_in_block_table(row_index, column, value)

        self._mw.curr_block_name_LineEdit.setText(current_block_name)



    def block_editor_add_row_before_selected(self, insert_rows=1):
        """ Add row before selected element. """

        self._mw.block_editor_TableWidget.blockSignals(True)

        selected_row = self._mw.block_editor_TableWidget.currentRow()

        # the signal passes a boolean value, which overwrites the insert_rows
        # parameter. Check that here and use the actual default value:
        if type(insert_rows) is bool:
            insert_rows = 1

        for rows in range(insert_rows):
            self._mw.block_editor_TableWidget.insertRow(selected_row)
        self.initialize_cells_block_editor(start_row=selected_row,stop_row=selected_row+insert_rows)

        self._mw.block_editor_TableWidget.blockSignals(False)


    def block_editor_add_row_after_last(self, insert_rows=1):
        """ Add row after last row in the block editor. """

        self._mw.block_editor_TableWidget.blockSignals(True)

        # the signal passes a boolean value, which overwrites the insert_rows
        # parameter. Check that here and use the actual default value:
        if type(insert_rows) is bool:
            insert_rows = 1

        number_of_rows = self._mw.block_editor_TableWidget.rowCount()

        self._mw.block_editor_TableWidget.setRowCount(number_of_rows+insert_rows)
        self.initialize_cells_block_editor(start_row=number_of_rows,stop_row=number_of_rows+insert_rows)

        self._mw.block_editor_TableWidget.blockSignals(False)

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

        self._mw.block_editor_TableWidget.blockSignals(True)

        self._mw.block_editor_TableWidget.setRowCount(1)
        self._mw.block_editor_TableWidget.clearContents()

        self.initialize_cells_block_editor(start_row=0)
        self._mw.block_editor_TableWidget.blockSignals(False)

    def block_editor_save_clicked(self):
        """
        Actions to perform when the save button in the block editor is clicked
        """
        objectname = self._mw.curr_block_name_LineEdit.text()
        table_struct = self.get_block_table()
        num_laser_pulses = self._mw.curr_block_laserpulses_SpinBox.value()
        self._seq_gen_logic.generate_pulse_block_object(objectname,
                                                        table_struct,
                                                        num_laser_pulses)
        return

    def block_editor_delete_clicked(self):
        """
        Actions to perform when the delete button in the block editor is clicked
        """
        name = self._mw.saved_blocks_ComboBox.currentText()
        self._seq_gen_logic.delete_block(name)
        self.update_block_organizer_list()
        return

    def generate_pulse_block(self):
        """ Generate a Pulse_Block object."""

        objectname = self._mw.curr_block_name_LineEdit.text()
        if objectname == '':
            self.logMsg('No Name for Pulse_Block specified. Generation '
                        'aborted!', importance=7, msgType='warning')
            return
        num_laser_pulses = self._mw.curr_block_laserpulses_SpinBox.value()
        self._seq_gen_logic.generate_pulse_block_object(objectname,
                                                  self.get_block_table(),
                                                  num_laser_pulses)

        self.update_block_organizer_list()



    # -------------------------------------------------------------------------
    #           Methods for the Pulse Block Organizer
    # -------------------------------------------------------------------------

    def update_block_organizer_list(self):
        """ If a Pulse_Block object has been deleted, update the list in
            organizer.
        """

        column = 0
        for row in range(self._mw.block_organizer_TableWidget.rowCount()):
            data = self.get_element_in_organizer_table(row, column)
            if data not in self._seq_gen_logic.saved_pulse_blocks:
                self.initialize_cells_block_organizer(start_row=row, stop_row=row+1,
                                                      start_col=column,stop_col=column+1)


    def get_element_in_organizer_table(self, row, column):
        """ Simplified wrapper function to get the data from a specific cell
            in the organizer table.

        @param int row: row index
        @param int column: column index
        @return: the value of the corresponding cell, which can be a string, a
                 float or an integer. Remember that the checkbox state
                 unchecked corresponds to 0 and check to 2. That is Qt
                 convention.

        Note that the order of the arguments in this function (first row index
        and then column index) was taken from the Qt convention.
        """

        tab = self._mw.block_organizer_TableWidget

        # Get from the corresponding delegate the data access model
        access = tab.itemDelegateForColumn(column).model_data_access
        data = tab.model().index(row, column).data(access)
        return data

    def get_organizer_table(self):
        """ Convert organizer table data to numpy array.

        @return: np.array[rows][columns] which has a structure, i.e. strings
                 integer and float values are represented by this array.
                 The structure was taken according to the init table itself.
        """

        tab = self._mw.block_organizer_TableWidget

        # create a structure for the output numpy array:
        structure = ''
        for column in range(tab.columnCount()):
            elem = self.get_element_in_organizer_table(0,column)
            if type(elem) is str:
                structure = structure + '|S20, '
            elif type(elem) is int:
                structure = structure + '|i4, '
            elif type(elem) is float:
                structure = structure + '|f4, '
            else:
                self.logMsg('Type definition not found in the organizer table.'
                            '\nType is neither a string, integer or float. '
                            'Include that type in the get_block_table method!',
                            msgType='error')

        # remove the last two elements since these are a comma and a space:
        structure = structure[:-2]
        table = np.zeros(tab.rowCount(), dtype=structure)

        # fill the table:
        for column in range(tab.columnCount()):
            for row in range(tab.rowCount()):
                # self.logMsg(, msgType='status')
                table[row][column] = self.get_element_in_organizer_table(row, column)

        return table




    def block_organizer_add_row_before_selected(self,insert_rows=1):
        """ Add row before selected element. """
        self._mw.block_organizer_TableWidget.blockSignals(True)
        selected_row = self._mw.block_organizer_TableWidget.currentRow()

        # the signal passes a boolean value, which overwrites the insert_rows
        # parameter. Check that here and use the actual default value:
        if type(insert_rows) is bool:
            insert_rows = 1

        for rows in range(insert_rows):
            self._mw.block_organizer_TableWidget.insertRow(selected_row)

        self.initialize_cells_block_organizer(start_row=selected_row)
        self._mw.block_organizer_TableWidget.blockSignals(False)
        self._update_current_pulse_block_ensemble()


    def block_organizer_add_row_after_last(self,insert_rows=1):
        """ Add row after last row in the block editor. """
        self._mw.block_organizer_TableWidget.blockSignals(True)

        # the signal passes a boolean value, which overwrites the insert_rows
        # parameter. Check that here and use the actual default value:
        if type(insert_rows) is bool:
            insert_rows = 1

        number_of_rows = self._mw.block_organizer_TableWidget.rowCount()
        self._mw.block_organizer_TableWidget.setRowCount(number_of_rows+insert_rows)

        self.initialize_cells_block_organizer(start_row=number_of_rows)
        self._mw.block_organizer_TableWidget.blockSignals(False)
        self._update_current_pulse_block_ensemble()

    def block_organizer_delete_row_selected(self):
        """ Delete row of selected element. """

        # get the row number of the selected item(s). That will return the
        # lowest selected row
        row_to_remove = self._mw.block_organizer_TableWidget.currentRow()
        self._mw.block_organizer_TableWidget.removeRow(row_to_remove)
        self._update_current_pulse_block_ensemble()

    def block_organizer_delete_row_last(self):
        """ Delete the last row in the block editor. """

        number_of_rows = self._mw.block_organizer_TableWidget.rowCount()
        # remember, the row index is started to count from 0 and not from 1,
        # therefore one has to reduce the value by 1:
        self._mw.block_organizer_TableWidget.removeRow(number_of_rows-1)
        self._update_current_pulse_block_ensemble()

    def block_organizer_clear_table(self):
        """ Delete all rows in the block editor table. """


        self._mw.block_organizer_TableWidget.blockSignals(True)
        self._mw.block_organizer_TableWidget.setRowCount(1)
        self._mw.block_organizer_TableWidget.clearContents()

        self.initialize_cells_block_organizer(start_row=0)
        self._mw.block_organizer_TableWidget.blockSignals(False)
        self._update_current_pulse_block_ensemble()

    def block_organizer_delete_clicked(self):
        """
        Actions to perform when the delete button in the block organizer is clicked
        """
        name = self._mw.saved_ensembles_ComboBox.currentText()
        self._seq_gen_logic.delete_ensemble(name)
        return

    def generate_pulse_block_ensemble(self):
        """ Generate a Pulse_Block_ensemble object."""

        objectname = self._mw.curr_ensemble_name_LineEdit.text()
        if objectname == '':
            self.logMsg('No Name for Pulse_Block_Ensemble specified. '
                        'Generation aborted!', importance=7, msgType='warning')
            return
        rotating_frame =  self._mw.curr_ensemble_rot_frame_CheckBox.isChecked()
        self._seq_gen_logic.generate_pulse_block_ensemble(objectname,
                                                    self.get_organizer_table(),
                                                    rotating_frame)


    def update_pulse_block_ensemble_list(self):
        """ Update the Pulse Block Ensemble list.  """
        self._mw.upload_ensemble_ComboBox.clear()
        self._mw.upload_ensemble_ComboBox.addItems(self._seq_gen_logic.saved_pulse_block_ensembles)


    def insert_parameters(self, column):

        # insert parameter:
        insert_at_col_pos = column
        for column, parameter in enumerate(self.get_add_pbe_param()):

            # add the new properties to the whole column through delegate:
            items_list = self.get_add_pbe_param()[parameter]

            if 'unit_prefix' in items_list.keys():
                unit_text = items_list['unit_prefix'] + items_list['unit']
            else:
                unit_text = items_list['unit']

            self._mw.block_editor_TableWidget.insertColumn(insert_at_col_pos+column)
            self._mw.block_editor_TableWidget.setHorizontalHeaderItem(insert_at_col_pos+column, QtGui.QTableWidgetItem())
            self._mw.block_editor_TableWidget.horizontalHeaderItem(insert_at_col_pos+column).setText('{0} ({1})'.format(parameter,unit_text))
            self._mw.block_editor_TableWidget.setColumnWidth(insert_at_col_pos+column, 80)

            # Use only DoubleSpinBox  as delegate:
            if items_list['unit'] == 'bool':
                delegate = CheckBoxDelegate(self._mw.block_editor_TableWidget, items_list)
            else:
                delegate = DoubleSpinBoxDelegate(self._mw.block_editor_TableWidget, items_list)
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


    def count_digital_channels(self):
        """ Get the number of currently displayed digital channels.

        @return int: number of digital channels

        The number of digital channal are counted and return and additionally
        the internal counter variable _num_d_ch is updated. The counting
        procedure is based on the block_editor_TableWidget.
        """
        count_dch = 0
        for column in range(self._mw.block_editor_TableWidget.columnCount()):
            if 'DCh' in self._mw.block_editor_TableWidget.horizontalHeaderItem(column).text():
                count_dch = count_dch + 1

        self._num_d_ch = count_dch
        return count_dch

    def set_a_d_ch(self, num_d_ch=None, num_a_ch=None):
        """ Set amount of analog or/and digital channels.

        @param num_d_ch: int, optional, number of digital channels.
        @param num_a_ch: int, optional, number of analog channels.

        This function wraps basically around the function
        _set_block_editor_columns. It is more intuitive to set the number of
        channels then the number of columns.
        If no arguments are passed, the table is simple reinitialized to
        default values.
        """
        self._set_block_editor_columns(num_d_ch=num_d_ch, num_a_ch=num_a_ch)

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



    def _set_block_editor_columns(self, num_d_ch=None, num_a_ch=None):
        """ General function which creates the needed columns in Pulse Block
            Editor.

        @param num_d_ch: int, desired number of digital channels
        @param num_a_ch: int, desired numbe of analogue channels

        If no argument is passed, the table is simply renewed. Otherwise the
        desired number of channels are created.
        Every time this function is executed all the table entries are erased
        and created again to prevent wrong delegation.
        """

        self._mw.block_editor_TableWidget.blockSignals(True)

        if num_d_ch is None:
            num_d_ch = self._num_d_ch

        if num_a_ch is None:
            num_a_ch = self._num_a_ch

        # Determine the function with the most parameters. Use also that
        # function as a construction plan to create all the needed columns for
        # the parameters.
        (num_max_param, biggest_func) = self._determine_needed_parameters()

        # Erase the delegate from the column, pass a None reference:
        for column in range(self._mw.block_editor_TableWidget.columnCount()):
            self._mw.block_editor_TableWidget.setItemDelegateForColumn(column,None)

        # clear the number of columns:
        self._mw.block_editor_TableWidget.setColumnCount(0)

        # total number of analogue and digital channels:
        num_a_d_ch =  num_a_ch*(num_max_param +1) + num_d_ch


        self._mw.block_editor_TableWidget.setColumnCount(num_a_d_ch)

        num_a_to_create = num_a_ch
        num_d_to_create = num_d_ch

        channel_map = []

        a_created = False
        d_created = False

        column = 0
        while (column < num_a_d_ch):

            if num_a_to_create == 0 or a_created:

                self._mw.block_editor_TableWidget.setHorizontalHeaderItem(column, QtGui.QTableWidgetItem())
                self._mw.block_editor_TableWidget.horizontalHeaderItem(column).setText('DCh{:d}'.format(num_d_ch-num_d_to_create))
                self._mw.block_editor_TableWidget.setColumnWidth(column, 40)

                channel_map.append('DCh{:d}'.format(num_d_ch-num_d_to_create))

                # itemlist for checkbox
                items_list = {}
                items_list['init_val'] = QtCore.Qt.Unchecked
                checkDelegate = CheckBoxDelegate(self._mw.block_editor_TableWidget, items_list)
                self._mw.block_editor_TableWidget.setItemDelegateForColumn(column, checkDelegate)


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

                channel_map.append('ACh{0:d}'.format(num_a_ch-num_a_to_create))

                items_list = {}
                items_list['get_list_method'] = self.get_current_function_list

                delegate = ComboBoxDelegate(self._mw.block_editor_TableWidget, items_list)
                self._mw.block_editor_TableWidget.setItemDelegateForColumn(column+param_pos, delegate)

                # create here all
                for param_pos, parameter in enumerate(self.get_func_config()[biggest_func]):

                    # initial block:

                    items_list = self.get_func_config()[biggest_func][parameter]

                    if 'unit_prefix' in items_list.keys():
                        unit_text = items_list['unit_prefix'] + items_list['unit']
                    else:
                        unit_text = items_list['unit']

                    self._mw.block_editor_TableWidget.setHorizontalHeaderItem(column+param_pos+1, QtGui.QTableWidgetItem())
                    self._mw.block_editor_TableWidget.horizontalHeaderItem(column+param_pos+1).setText('ACh{0:d}\n{1} ({2})'.format(num_a_ch-num_a_to_create, parameter, unit_text))
                    self._mw.block_editor_TableWidget.setColumnWidth(column+param_pos+1, 100)

                    # add the new properties to the whole column through delegate:

                    # extract the classname from the _param_a_ch list to be able to deligate:
                    delegate = DoubleSpinBoxDelegate(self._mw.block_editor_TableWidget, items_list)
                    self._mw.block_editor_TableWidget.setItemDelegateForColumn(column+param_pos+1, delegate)

                column = column + (num_max_param +1)
                num_a_to_create = num_a_to_create - 1

        self._num_a_ch = num_a_ch
        self._num_d_ch = num_d_ch


        self.insert_parameters(num_a_d_ch)


        self.initialize_cells_block_editor(0,self._mw.block_editor_TableWidget.rowCount())

        self.set_cfg_param_pbe()
        self._mw.block_editor_TableWidget.blockSignals(False)
        self.set_channel_map(channel_map)
        self._update_current_pulse_block()


    def set_channel_map(self, channel_map):
        """ Set the possible channels

        @param channel_map:
        """
        self._mw.laserchannel_ComboBox.clear()
        self._mw.laserchannel_ComboBox.addItems(channel_map)
        self._channel_map = channel_map



    def get_channel_map(self):
        """

        @return: list, with string entries denoting the current channel config.
        """
        self._channel_map

    def get_cfg_param_pbe(self):
        """ Get the current parameter configuration of Pulse Block Element.

        @return dict: An abstract dictionary, which tells the logic the
                      configuration of a Pulse_Block_Element, i.e. how many
                      parameters are used for a Pulse_Block_Element (pbe)
                      object. Keys describing the names of the column (as
                      string) and the items denoting the column number (int).
        """
        return self._cfg_param_pbe


    def set_cfg_param_pbe(self):
        """ Set the parameter configuration of the Pulse_Block_Elements
        according to the current table configuration and updates the dict in
        the logic.
        """

        cfg_param_pbe = OrderedDict()
        for column in range(self._mw.block_editor_TableWidget.columnCount()):
            text = self._mw.block_editor_TableWidget.horizontalHeaderItem(column).text()
            split_text = text.split()
            if 'DCh' in split_text[0]:
                cfg_param_pbe['digital_' + split_text[0][3]] = column
            elif 'ACh' in split_text[0]:
                cfg_param_pbe[split_text[1] + '_' + split_text[0][3]] = column
            else:
                cfg_param_pbe[split_text[0]] = column

        self._cfg_param_pbe = cfg_param_pbe
        self._seq_gen_logic.cfg_param_pbe = cfg_param_pbe

    def get_cfg_param_pb(self):
        """ Ask for the current configuration of the

        @return dict: An abstract dictionary, which tells the logic the
                      configuration of a Pulse_Block, i.e. how many parameters
                      are used for a Pulse_Block (pb) object. Keys describing
                      the names of the column (as string) and the items
                      denoting the column number (int).
        """
        return self._org_table_config


    def set_cfg_param_pb(self):
        """ Set the parameter configuration of the Pulse_Block according to the
        current table configuration and updates the dict in the logic.
        """

        cfg_param_pb = OrderedDict()

        for column in range(self._mw.block_organizer_TableWidget.columnCount()):
            text = self._mw.block_organizer_TableWidget.horizontalHeaderItem(column).text()
            # split_text = text.split()
            if 'Pulse Block' in text:
                cfg_param_pb['pulse_block'] = column
            elif 'length' in text:
                cfg_param_pb['length'] = column
            elif 'repetition' in text:
                cfg_param_pb['repetition'] = column
            else:
                print('text:',text)
                raise NotImplementedError
        self._cfg_param_pb = cfg_param_pb
        self._seq_gen_logic.cfg_param_pb = cfg_param_pb

    def _set_organizer_columns(self):

        # Erase the delegate from the column, pass a None reference:
        for column in range(self._mw.block_organizer_TableWidget.columnCount()):
            self._mw.block_organizer_TableWidget.setItemDelegateForColumn(column, None)

        # clear the number of columns:
        self._mw.block_organizer_TableWidget.setColumnCount(0)

        # total number columns in block organizer:
        num_column = 1
        self._mw.block_organizer_TableWidget.setColumnCount(num_column)

        column = 0
        self._mw.block_organizer_TableWidget.setHorizontalHeaderItem(column, QtGui.QTableWidgetItem())
        self._mw.block_organizer_TableWidget.horizontalHeaderItem(column).setText('Pulse Block')
        self._mw.block_organizer_TableWidget.setColumnWidth(column, 100)

        items_list = {}
        items_list['get_list_method'] = self.get_current_pb_list

        comboDelegate = ComboBoxDelegate(self._mw.block_organizer_TableWidget, items_list)
        self._mw.block_organizer_TableWidget.setItemDelegateForColumn(column, comboDelegate)

        column = 1
        insert_at_col_pos = column
        for column, parameter in enumerate(self.get_add_pb_param()):

            # add the new properties to the whole column through delegate:
            items_list = self.get_add_pb_param()[parameter]

            if 'unit_prefix' in items_list.keys():
                unit_text = items_list['unit_prefix'] + items_list['unit']
            else:
                unit_text = items_list['unit']

            print('insert_at_col_pos',insert_at_col_pos)
            print('column',column)
            self._mw.block_organizer_TableWidget.insertColumn(insert_at_col_pos+column)
            self._mw.block_organizer_TableWidget.setHorizontalHeaderItem(insert_at_col_pos+column, QtGui.QTableWidgetItem())
            self._mw.block_organizer_TableWidget.horizontalHeaderItem(insert_at_col_pos+column).setText('{0} ({1})'.format(parameter,unit_text))
            self._mw.block_organizer_TableWidget.setColumnWidth(insert_at_col_pos+column, 80)

            # Use only DoubleSpinBox  as delegate:
            if items_list['unit'] == 'bool':
                delegate = CheckBoxDelegate(self._mw.block_organizer_TableWidget, items_list)
            elif parameter == 'repetition':
                delegate = SpinBoxDelegate(self._mw.block_organizer_TableWidget, items_list)
            else:
                delegate = DoubleSpinBoxDelegate(self._mw.block_organizer_TableWidget, items_list)
            self._mw.block_organizer_TableWidget.setItemDelegateForColumn(insert_at_col_pos+column, delegate)

        self.initialize_cells_block_organizer(0, self._mw.block_organizer_TableWidget.rowCount())

        self.set_cfg_param_pb()
        self._update_current_pulse_block_ensemble()


    def initialize_cells_block_editor(self, start_row, stop_row=None,
                                    start_col=None, stop_col=None):
        """ Initialize the desired cells in the block editor table.

        @param start_row: int, index of the row, where the initialization
                          should start
        @param stop_row: int, optional, index of the row, where the
                         initalization should end.
        @param start_col: int, optional, index of the column where the
                          initialization should start
        @param stop_col: int, optional, index of the column, where the
                         initalization should end.

        With this function it is possible to reinitialize specific elements or
        part of a row or even the whole row. If start_row is set to 0 the whole
        row is going to be initialzed to the default value.
        """

        if stop_row is None:
            stop_row = start_row +1

        if start_col is None:
            start_col = 0

        if stop_col is None:
            stop_col= self._mw.block_editor_TableWidget.columnCount()

        for col_num in range(start_col, stop_col):

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


    def initialize_cells_block_organizer(self, start_row, stop_row=None,
                                    start_col=None, stop_col=None):
        """ Initialize the desired cells in the block organizer table.

        @param start_row: int, index of the row, where the initialization
                          should start
        @param stop_row: int, optional, index of the row, where the
                         initalization should end.
        @param start_col: int, optional, index of the column where the
                          initialization should start
        @param stop_col: int, optional, index of the column, where the
                         initalization should end.

        With this function it is possible to reinitialize specific elements or
        part of a row or even the whole row. If start_row is set to 0 the whole
        row is going to be initialzed to the default value.
        """

        if stop_row is None:
            stop_row = start_row +1

        if start_col is None:
            start_col = 0

        if stop_col is None:
            stop_col = self._mw.block_organizer_TableWidget.columnCount()

        for col_num in range(start_col, stop_col):

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


    def _create_control_for_prepared_methods(self):
        """ Create the Control Elements in the Predefined Windows, depending
            on the methods of the logic.

        The following procedure was chosen:
            1. At first the method is inspected and all the parameters are
              investigated. Depending on the type of the default value of the
              keyword, a ControlBox (CheckBox, DoubleSpinBox, ...) is created.
            2. Then a in the GUI is created like
                _<method_name>_generate()
                which is connected to the generate button and passes all the
                parameters to the method in the logic.
            3. An additional method is created as
                _<method_name>_generate_upload()
                which generates and uploads the current values to the device.
        """
        method_list = self._seq_gen_logic.prepared_method_list

        for method in method_list:
            inspected = inspect.signature(method)


            gridLayout = QtGui.QGridLayout()
            groupBox = QtGui.QGroupBox(self._pm)

            obj_list = []

            # go through the parameter list and check the type of the default
            # parameter
            for index, param_name in enumerate(inspected.parameters):

                label_obj = self._create_QLabel(groupBox, param_name)

                default_value = inspected.parameters[param_name].default

                if default_value is inspect._empty:
                    self.logMsg('The method "{0}" in the logic has an '
                                'argument "{1}" without a default value!\n'
                                'Assign a default value to that, otherwise a '
                                'type estimation is not possible!\n'
                                'Creation of the viewbox '
                                'aborted.'.format(method.__name__, param_name),
                                msgType='error')
                    return

                if type(default_value) is bool:
                    view_obj = self._create_QCheckBox(groupBox, default_value)
                elif type(default_value) is float:
                    view_obj = self._create_QDoubleSpinBox(groupBox, default_value)
                elif type(default_value) is int:
                    view_obj = self._create_QSpinBox(groupBox, default_value)
                elif type(default_value) is str:
                    view_obj = self._create_QLineEdit(groupBox, default_value)
                else:
                    self.logMsg('The method "{0}" in the logic has an '
                                'argument "{1}" with is not of the valid types'
                                'str, float int or bool!\n'
                                'Choose one of those default values! Creation '
                                'of the viewbox '
                                'aborted.'.format(method.__name__, param_name)
                                , msgType='error')

                obj_list.append(view_obj)
                gridLayout.addWidget(label_obj, 0, index, 1, 1)
                gridLayout.addWidget(view_obj, 1, index, 1, 1)

            gen_button = self._create_QPushButton(groupBox, 'Generate')
            # Create with the function builder a method, which will be
            # connected to the click event of the pushbutton generate:
            func_name = '_'+ method.__name__ + '_generate'
            setattr(self, func_name, self._function_builder_generate(func_name, obj_list, method) )
            gen_func = getattr(self, func_name)
            gen_button.clicked.connect(gen_func)


            gen_upload_button = self._create_QPushButton(groupBox, 'Gen. & Upload')
            # Create with the function builder a method, which will be
            # connected to the click event of the pushbutton generate & upload:
            func_name = '_'+ method.__name__ + '_generate_upload'
            setattr(self, func_name, self._function_builder_generate_upload(func_name, gen_func) )
            gen_upload_func = getattr(self, func_name)
            gen_upload_button.clicked.connect(gen_upload_func)

            pos = len(inspected.parameters)
            gridLayout.addWidget(gen_button, 0, pos, 1, 1)
            gridLayout.addWidget(gen_upload_button, 1, pos, 1, 1)

            horizontalLayout = QtGui.QHBoxLayout(groupBox)

            horizontalLayout.addLayout(gridLayout)

            groupBox.setTitle(method.__name__.replace('_',' '))

            self._pm.verticalLayout.addWidget(groupBox)

    def _create_QLabel(self, parent, label_name):
        """ Helper method for _create_control_for_prepared_methods.

        Generate a predefined label.
        """
        label = QtGui.QLabel(parent)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(label.sizePolicy().hasHeightForWidth())
        label.setSizePolicy(sizePolicy)
        label.setText(label_name)
        return label

    def _create_QDoubleSpinBox(self, parent, default_val=0.0):

        doublespinBox = QtGui.QDoubleSpinBox(parent)
        doublespinBox.setMaximum(np.inf)
        doublespinBox.setMinimum(-np.inf)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(doublespinBox.sizePolicy().hasHeightForWidth())

        doublespinBox.setMinimumSize(QtCore.QSize(80, 0))

        return doublespinBox

    def _create_QSpinBox(self, parent, default_val=0):

        spinBox = QtGui.QSpinBox(parent)
        spinBox.setMaximum(2**31 -1)
        spinBox.setMinimum(-2**31 -1)
        return spinBox

    def _create_QCheckBox(self, parent, default_val=False):
        checkBox = QtGui.QCheckBox(parent)
        checkBox.setChecked(default_val)
        return checkBox

    def _create_QLineEdit(self, parent, default_val=''):
        lineedit = QtGui.QLineEdit(parent)
        lineedit.setText(default_val)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(lineedit.sizePolicy().hasHeightForWidth())

        lineedit.setMinimumSize(QtCore.QSize(80, 0))

        lineedit.setSizePolicy(sizePolicy)
        return lineedit

    def _create_QPushButton(self, parent, text='Generate'):
        pushbutton = QtGui.QPushButton(parent)
        pushbutton.setText(text)
        return pushbutton

    def _function_builder_generate(self, func_name, obj_list, ref_logic_gen ):
        """ Create a function/method which is called by the generate button
        @param str func_name: name of the function, which will be append to self
        @param list obj_list: list of objects, which where the value will be
                              retrieved
        @param method ref_logic_gen: reference to method in logic
        @return: a function, which can be called with func_name
        """

        def func_dummy_name():
            object_list = obj_list

            ensemble_name = ''
            parameters = [None]*len(object_list)
            for index, object in enumerate(object_list):
                if hasattr(object,'isChecked'):
                    parameters[index] = object.isChecked()
                elif hasattr(object,'value'):
                    parameters[index] = object.value()
                elif hasattr(object,'text'):

                    parameters[index] = object.text()
                    ensemble_name = object.text()
                else:
                    self.logMsg('Not possible to get the value from the '
                                'viewbox, since it does not have one of the'
                                'possible access methods!', msgType='error')

            # the * operator unpacks the list
            ref_logic_gen(*parameters)
            return ensemble_name

        func_dummy_name.__name__ = func_name
        return func_dummy_name

    def _function_builder_generate_upload(self, func_name, ref_gen_func):
        """ Create a function/method which is called by the generate and upload button

        @param str func_name: name of the function, which will be append to self
        @param str ensemble_name: name of the pulse_block_ensemble which will
                                  be uploaded.
        @param ref_gen_func: reference to the generate function, which calls
                             the logic method
        @return: a function, which can be called with func_name
        """

        def func_dummy_name():
            ensemble_name = ref_gen_func()

            index = self._mw.upload_ensemble_ComboBox.findText(ensemble_name, QtCore.Qt.MatchFixedString)
            self._mw.upload_ensemble_ComboBox.setCurrentIndex(index)
            self.upload_to_device_clicked()

        func_dummy_name.__name__ = func_name
        return func_dummy_name



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
        self.fft_image = pg.PlotDataItem(self._pulsed_measurement_logic.signal_plot_x, self._pulsed_measurement_logic.signal_plot_y)
        self.lasertrace_image = pg.PlotDataItem(self._pulsed_measurement_logic.laser_plot_x, self._pulsed_measurement_logic.laser_plot_y)
        self.measuring_error_image = pg.PlotDataItem(self._pulsed_measurement_logic.measuring_error_plot_x, self._pulsed_measurement_logic.measuring_error_plot_y*1000)

        self.fit_image = pg.PlotDataItem(self._pulsed_measurement_logic.signal_plot_x, self._pulsed_measurement_logic.signal_plot_y)

        self.sig_start_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(QtGui.QColor(255,0,0,255)))
        self.sig_end_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(QtGui.QColor(255,0,0,255)))
        self.ref_start_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(QtGui.QColor(0,255,0,255)))
        self.ref_end_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(QtGui.QColor(0,255,0,255)))
#
#        # Add the display item to the xy VieWidget, which was defined in
#        # the UI file.
        self._mw.signal_plot_ViewWidget.addItem(self.signal_image)
        self._mw.signal_plot_ViewWidget.addItem(self.fit_image)
        self._mw.fft_PlotWidget.addItem(self.fft_image)
        self._mw.lasertrace_plot_ViewWidget.addItem(self.lasertrace_image)

        self._mw.lasertrace_plot_ViewWidget.addItem(self.sig_start_line)
        self._mw.lasertrace_plot_ViewWidget.addItem(self.sig_end_line)
        self._mw.lasertrace_plot_ViewWidget.addItem(self.ref_start_line)
        self._mw.lasertrace_plot_ViewWidget.addItem(self.ref_end_line)
        self._mw.measuring_error_PlotWidget.addItem(self.measuring_error_image)
        self._mw.signal_plot_ViewWidget.showGrid(x=True, y=True, alpha=0.8)
        self._mw.fft_PlotWidget.showGrid(x=True, y=True, alpha=0.8)
        self._mw.signal_plot_ViewWidget.setLabel('left', 'Intensity', units='a.u.')
        self._mw.signal_plot_ViewWidget.setLabel('left', 'Counts')
        self._mw.lasertrace_plot_ViewWidget.setLabel('bottom', 'tau', units='ns')
        self._mw.lasertrace_plot_ViewWidget.setLabel('bottom', 'bins')
        self._mw.measuring_error_PlotWidget.setLabel('left', 'measuring error', units='a.u.')
        self._mw.measuring_error_PlotWidget.setLabel('bottom', 'tan', units='ns')
        #self._mw.measuring_error_PlotWidget.showGrid(x=True, y=True, alpha=0.8)



        # Initialize  what is visible and what not
        self._mw.mw_frequency_Label.setVisible(False)
        self._mw.mw_frequency_InputWidget.setVisible(False)
        self._mw.mw_power_Label.setVisible(False)
        self._mw.mw_power_InputWidget.setVisible(False)

        self._mw.tau_start_Label.setVisible(False)
        self._mw.tau_start_InputWidget.setVisible(False)
        self._mw.tau_increment_Label.setVisible(False)
        self._mw.tau_increment_InputWidget.setVisible(False)

        self._mw.fft_PlotWidget.setVisible(False)


        # Set the state button as ready button as default setting.

        self._mw.action_continue_pause.setEnabled(False)

        self._mw.action_pull_data.setEnabled(False)

        # Configuration of the comboWidget
        # self._mw.binning_comboBox.addItem(str(self._pulsed_measurement_logic.fast_counter_status['binwidth_ns']))
        # self._mw.binning_comboBox.addItem(str(self._pulsed_measurement_logic.fast_counter_status['binwidth_ns']*2.))
        # set up the types of the columns and create a pattern based on
        # the desired settings:

#        # Add Validators to InputWidgets
        validator = QtGui.QDoubleValidator()
        validator2 = QtGui.QIntValidator()

        # pulsed measurement tab
        self._mw.mw_frequency_InputWidget.setValidator(validator)
        self._mw.mw_power_InputWidget.setValidator(validator)
        self._mw.analysis_period_InputWidget.setValidator(validator)
        self._mw.numlaser_InputWidget.setValidator(validator2)
        self._mw.tau_start_InputWidget.setValidator(validator)
        self._mw.tau_increment_InputWidget.setValidator(validator)
        self._mw.signal_start_InputWidget.setValidator(validator2)
        self._mw.signal_length_InputWidget.setValidator(validator2)
        self._mw.reference_start_InputWidget.setValidator(validator2)
        self._mw.reference_length_InputWidget.setValidator(validator2)

        # Fill in default values:

        # pulsed measurement tab
        self._mw.mw_frequency_InputWidget.setText(str(2870.))
        self._mw.mw_power_InputWidget.setText(str(-30.))
        self._mw.numlaser_InputWidget.setText(str(50))
        self._mw.tau_start_InputWidget.setText(str(1))
        self._mw.tau_increment_InputWidget.setText(str(1))
#        self._mw.lasertoshow_spinBox.setRange(0, 50)
#        self._mw.lasertoshow_spinBox.setPrefix("#")
#        self._mw.lasertoshow_spinBox.setSpecialValueText("sum")
#        self._mw.lasertoshow_spinBox.setValue(0)

        self._mw.laser_to_show_ComboBox.clear()
        self._mw.laser_to_show_ComboBox.addItem('sum')
        for ii in range(50):
            self._mw.laser_to_show_ComboBox.addItem(str(1+ii))

        self._mw.signal_start_InputWidget.setText(str(5))
        self._mw.signal_length_InputWidget.setText(str(200))
        self._mw.reference_start_InputWidget.setText(str(500))
        self._mw.reference_length_InputWidget.setText(str(200))
        self._mw.expected_duration_TimeLabel.setText('00:00:00:03')
        self._mw.elapsed_time_label.setText('00:00:00:00')
        self._mw.elapsed_sweeps_LCDNumber.display(0)
        self._mw.analysis_period_InputWidget.setText(str(2))
        self._mw.refocus_interval_LineEdit.setText(str(500))
        self._mw.odmr_refocus_interval_LineEdit.setText(str(500))


        # Configuration of the fit ComboBox

        self._mw.fit_function_ComboBox.addItem('No Fit')
        self._mw.fit_function_ComboBox.addItem('Rabi Decay')
        self._mw.fit_function_ComboBox.addItem('Lorentian (neg)')
        self._mw.fit_function_ComboBox.addItem('Lorentian (pos)')
        self._mw.fit_function_ComboBox.addItem('N14')
        self._mw.fit_function_ComboBox.addItem('N15')
        self._mw.fit_function_ComboBox.addItem('Stretched Exponential')
        self._mw.fit_function_ComboBox.addItem('Exponential')
        self._mw.fit_function_ComboBox.addItem('XY8')


        # ---------------------------------------------------------------------
        #                         Connect signals
        # ---------------------------------------------------------------------

        # Connect the RadioButtons and connect to the events if they are clicked:
        # pulsed measurement tab
        #self._mw.idle_RadioButton.toggled.connect(self.idle_clicked)
        #self._mw.run_RadioButton.toggled.connect(self.run_clicked)
#        self._mw.pause_RadioButton.toggled.connect(self.pause_clicked)
#        self._mw.continue_RadioButton.toggled.connect(self.continue_clicked)

        self._mw.action_run_stop.triggered.connect(self.run_stop_clicked)

        self._mw.action_continue_pause.triggered.connect(self.continue_pause_clicked)

        self._mw.action_save.toggled.connect(self.save_clicked)

#        self._mw.pull_data_pushButton.clicked.connect(self.pull_data_clicked)
        self._mw.action_pull_data.toggled.connect(self.pull_data_clicked)


        self._pulsed_measurement_logic.signal_laser_plot_updated.connect(self.refresh_lasertrace_plot)
        self._pulsed_measurement_logic.signal_signal_plot_updated.connect(self.refresh_signal_plot)
        self._pulsed_measurement_logic.measuring_error_plot_updated.connect(self.refresh_measuring_error_plot)
        self._pulsed_measurement_logic.signal_time_updated.connect(self.refresh_elapsed_time)

        # sequence generator tab

        # Connect the CheckBoxes
        # anaylsis tab

        self._mw.turn_off_external_mw_source_CheckBox.stateChanged.connect(self.show_external_mw_source_checked)
        self._mw.tau_defined_in_sequence_CheckBox.stateChanged.connect(self.show_tau_editor)
        self._mw.show_fft_plot_CheckBox.stateChanged.connect(self.show_fft_plot)

        # Connect InputWidgets to events
        # pulsed measurement tab
        self._mw.numlaser_InputWidget.editingFinished.connect(self.lasernum_changed)
        #self._mw.lasertoshow_spinBox.valueChanged.connect(self.seq_parameters_changed)
        self._mw.laser_to_show_ComboBox.activated.connect(self.seq_parameters_changed)
        self._mw.tau_start_InputWidget.editingFinished.connect(self.seq_parameters_changed)
        self._mw.tau_increment_InputWidget.editingFinished.connect(self.seq_parameters_changed)
        self._mw.signal_start_InputWidget.editingFinished.connect(self.analysis_parameters_changed)
        self._mw.signal_length_InputWidget.editingFinished.connect(self.analysis_parameters_changed)
        self._mw.reference_start_InputWidget.editingFinished.connect(self.analysis_parameters_changed)
        self._mw.reference_length_InputWidget.editingFinished.connect(self.analysis_parameters_changed)
        self._mw.analysis_period_InputWidget.editingFinished.connect(self.analysis_parameters_changed)

        self.seq_parameters_changed()
        self.analysis_parameters_changed()
#
#        self._mw.actionSave_Data.triggered.connect(self.save_clicked)

        self._mw.fit_PushButton.clicked.connect(self.fit_clicked)


    def _deactivate_analysis_ui(self, e):
        """ Disconnects the configuration for 'Analysis' Tab.

        @param Fysom.event e: Event Object of Fysom
        """

        self.run_stop_clicked(False)

        # disconnect signals
#        self._mw.idle_RadioButton.toggled.disconnect()
#        self._mw.run_RadioButton.toggled.disconnect()
        self._pulsed_measurement_logic.signal_laser_plot_updated.disconnect()
        self._pulsed_measurement_logic.signal_signal_plot_updated.disconnect()
        self._pulsed_measurement_logic.measuring_error_plot_updated.disconnect()
        self._mw.numlaser_InputWidget.editingFinished.disconnect()
        #self._mw.lasertoshow_spinBox.valueChanged.disconnect()
        self._mw.laser_to_show_ComboBox.activated.disconnect()

#    def idle_clicked(self):
#        """ Stopp the scan if the state has switched to idle. """
#        self._pulsed_measurement_logic.stop_pulsed_measurement()
#        self._mw.mw_frequency_InputWidget.setEnabled(True)
#        self._mw.mw_power_InputWidget.setEnabled(True)
#        self._mw.binning_comboBox.setEnabled(True)
#        self._mw.pull_data_pushButton.setEnabled(False)

    def run_stop_clicked(self, isChecked):
        """ Manages what happens if pulsed measurement is started or stopped.

        @param bool enabled: start scan if that is possible
        """

        #Firstly stop any scan that might be in progress
        self._pulsed_measurement_logic.stop_pulsed_measurement()
        #Then if enabled. start a new scan.

        if isChecked:
            #self._mw.signal_plot_ViewWidget.clear()
            self._mw.mw_frequency_InputWidget.setEnabled(False)
            self._mw.mw_power_InputWidget.setEnabled(False)
            self._mw.binning_comboBox.setEnabled(False)
            self._mw.action_pull_data.setEnabled(True)
            self._pulsed_measurement_logic.start_pulsed_measurement()
            self._mw.action_continue_pause.setEnabled(True)
            if not self._mw.action_continue_pause.isChecked():
                self._mw.action_continue_pause.toggle()

        else:
            self._pulsed_measurement_logic.stop_pulsed_measurement()
            self._mw.mw_frequency_InputWidget.setEnabled(True)
            self._mw.mw_power_InputWidget.setEnabled(True)
            self._mw.binning_comboBox.setEnabled(True)
            self._mw.action_pull_data.setEnabled(False)
            self._mw.action_continue_pause.setEnabled(False)



    def continue_pause_clicked(self,isChecked):
        """ Continues and pauses the measurement. """

        if isChecked:
            #self._mw.action_continue_pause.toggle()

            self._mw.action_run_stop.setChecked(True)


        else:
            #self._mw.action_continue_pause.toggle

            self._mw.action_run_stop.setChecked(False)



    def pull_data_clicked(self):
        self._pulsed_measurement_logic.manually_pull_data()
        return

    def save_clicked(self):
        self._pulsed_measurement_logic._save_data()
        return

    def fit_clicked(self):
        self._mw.fit_result_TextBrowser.clear()

        current_fit_function = self._mw.fit_function_ComboBox.currentText()



        fit_x, fit_y, fit_result = self._pulsed_measurement_logic.do_fit(current_fit_function)

        self.fit_image = pg.PlotDataItem(fit_x, fit_y,pen='r')

        self._mw.signal_plot_ViewWidget.addItem(self.fit_image,pen='r')

        self._mw.fit_result_TextBrowser.setPlainText(fit_result)

        return




    def refresh_lasertrace_plot(self):
        ''' This method refreshes the xy-plot image
        '''
        self.lasertrace_image.setData(self._pulsed_measurement_logic.laser_plot_x, self._pulsed_measurement_logic.laser_plot_y)

    def refresh_signal_plot(self):
        ''' This method refreshes the xy-matrix image
        '''
        self.signal_image.setData(self._pulsed_measurement_logic.signal_plot_x, self._pulsed_measurement_logic.signal_plot_y)
        self.fft_image.setData(self._pulsed_measurement_logic.signal_plot_x, self._pulsed_measurement_logic.signal_plot_y)




    def refresh_measuring_error_plot(self):

        #print(self._pulsed_measurement_logic.measuring_error)

        self.measuring_error_image.setData(self._pulsed_measurement_logic.signal_plot_x,self._pulsed_measurement_logic.measuring_error*1000)

    def refresh_elapsed_time(self):
        ''' This method refreshes the elapsed time and sweeps of the measurement
        '''
        self._mw.elapsed_time_label.setText(self._pulsed_measurement_logic.elapsed_time_str)
        self._mw.elapsed_sweeps_LCDNumber.display(self._pulsed_measurement_logic.elapsed_sweeps)




    def show_external_mw_source_checked(self):
        if self._mw.turn_off_external_mw_source_CheckBox.isChecked():

            self._mw.mw_frequency_Label.setVisible(False)
            self._mw.mw_frequency_InputWidget.setVisible(False)
            self._mw.mw_power_Label.setVisible(False)
            self._mw.mw_power_InputWidget.setVisible(False)
        else:
            self._mw.mw_frequency_Label.setVisible(True)
            self._mw.mw_frequency_InputWidget.setVisible(True)
            self._mw.mw_power_Label.setVisible(True)
            self._mw.mw_power_InputWidget.setVisible(True)


    def show_tau_editor(self):
        if self._mw.tau_defined_in_sequence_CheckBox.isChecked():
            self._mw.tau_start_Label.setVisible(True)
            self._mw.tau_start_InputWidget.setVisible(True)
            self._mw.tau_increment_Label.setVisible(True)
            self._mw.tau_increment_InputWidget.setVisible(True)
        else:
            self._mw.tau_start_Label.setVisible(False)
            self._mw.tau_start_InputWidget.setVisible(False)
            self._mw.tau_increment_Label.setVisible(False)
            self._mw.tau_increment_InputWidget.setVisible(False)

    def show_fft_plot(self):
        if self._mw.show_fft_plot_CheckBox.isChecked():
            self._mw.fft_PlotWidget.setVisible(True)
        else:
            self._mw.fft_PlotWidget.setVisible(False)

    def lasernum_changed(self):
        self._mw.laser_to_show_ComboBox.clear()
        self._mw.laser_to_show_ComboBox.addItem('sum')
        for ii in range(int(self._mw.numlaser_InputWidget.text())):
            self._mw.laser_to_show_ComboBox.addItem(str(1+ii))
        # print (self._mw.laser_to_show_ComboBox.currentText())
        #self.seq_parameters_changed()

    def seq_parameters_changed(self):
        laser_num = int(self._mw.numlaser_InputWidget.text())
        tau_start = int(self._mw.tau_start_InputWidget.text())
        tau_incr = int(self._mw.tau_increment_InputWidget.text())
        mw_frequency = float(self._mw.mw_frequency_InputWidget.text())
        mw_power = float(self._mw.mw_power_InputWidget.text())
        #self._mw.lasertoshow_spinBox.setRange(0, laser_num)

        current_laser = self._mw.laser_to_show_ComboBox.currentText()


        # print (current_laser)

        if current_laser == 'sum':

            laser_show = 0


        else:
            # print (self._mw.laser_to_show_ComboBox.currentText())
            laser_show = int(current_laser)
            #laser_show=5


        if (laser_show > laser_num):
            print ('warning. Number too high')
            self._mw.laser_to_show_ComboBox.setEditText('sum')
            laser_show = 0



        tau_vector = np.array(range(tau_start, tau_start + tau_incr*laser_num, tau_incr))
        # self._pulsed_measurement_logic.running_sequence_parameters['tau_vector'] = tau_vector
        # self._pulsed_measurement_logic.running_sequence_parameters['number_of_lasers'] = laser_num
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