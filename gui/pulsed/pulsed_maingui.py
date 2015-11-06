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




# =============================================================================
#                       Define some delegate classes.
# =============================================================================

# These delegate classes can modify the behaviour of a whole row or column of
# in a QTableWidget. When this starts to work properly, then the delegate
# classes will mose to a separate file.
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
# We use QStyledItemDelegate as our base class so that we benefit from the
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
        self.items_list = items_list    # save the passed values to a list,
                                        #  which will be displayed and from
                                        # which you can choose.

    def get_initial_value(self):
        """ Tells you which object to insert in the model.setData function.

        @return list[2]: returns the two values, which corresponds to the last
                         two values you should insert in the setData function.
                         The first one is the first element of the passed item
                         list items_list and the second one is the Role.
            model.setData(index, editor.itemText(value),QtCore.Qt.DisplayRole)
        """
        return [self.items_list[0], QtCore.Qt.DisplayRole]

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
        editor.addItems(self.items_list)
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
        value = index.data(QtCore.Qt.DisplayRole)
        num = self.items_list.index(value)
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
        model.setData(index, editor.itemText(value), QtCore.Qt.DisplayRole)

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
        editor.addItems(self.items_list)
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

    def get_initial_value(self):
        """ Tells you which object to insert in the model.setData function.

        @return list[2]: returns the two values, which corresponds to the last
                         two values you shoul insert in the setData function.
                         The first one is the first element of the passed item
                         list list_items and the second one is the Role.
            model.setData(index, editor.itemText(value),QtCore.Qt.DisplayRole)
        """
        return [self.items_list[0], QtCore.Qt.DisplayRole]

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

        value = index.data(QtCore.Qt.EditRole)

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
        model.setData(index, value, QtCore.Qt.EditRole)

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

    def get_initial_value(self):
        """ Tells you which object to insert in the model.setData function.

        @return list[2]: returns the two values, which corresponds to the last
                         two values you shoul insert in the setData function.
                         The first one is the first element of the passed item
                         list list_items and the second one is the Role.
            model.setData(index, value, QtCore.Qt.CheckStateRole)
        """
        return [self.items_list[0], QtCore.Qt.CheckStateRole]

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

        value = index.data(QtCore.Qt.CheckStateRole)
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
        model.setData(index, value, QtCore.Qt.CheckStateRole)

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
        @param list items_list: A list with predefined properties for the used
                                editor. In this class the items must look like:
                                [default_val, min_val, max_val,step_size]
        """
        QtGui.QStyledItemDelegate.__init__(self, parent)
        self.items_list = items_list

    def get_initial_value(self):
        """ Tells you which object to insert in the model.setData function.

        @return list[2]: returns the two values, which corresponds to the last
                         two values you shoul insert in the setData function.
                         The first one is the first element of the passed item
                         list list_items and the second one is the Role.
            model.setData(index, editor.itemText(value), QtCore.Qt.DisplayRole)
        """
        return [self.items_list[0], QtCore.Qt.DisplayRole]

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
        editor.setMinimum(self.items_list[1])
        editor.setMaximum(self.items_list[2])
        editor.setSingleStep(self.items_list[3])
        editor.setDecimals(self.items_list[4])
        editor.installEventFilter(self)
        editor.setValue(self.items_list[0])
        return editor

    def setEditorData(self, editor, index):
        """ Set the display of the current value of the used editor.

        @param QDoubleSpinBox editor: QObject which was created in createEditor
                                      function, here a QDoubleSpinBox.
        @param QtCore.QModelIndex index: explained in createEditor function.

        This function converts the passed data to an value, which can be
        understood by the editor.
        """

        value = index.data(QtCore.Qt.EditRole)

        if not isinstance(value, float):
            value = self.items_list[0]
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
        model.setData(index, value, QtCore.Qt.EditRole)

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
        """ Definition, configuration and initialisation of the pulsed measurement GUI.

          @param class e: event class from Fysom

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """


        self._pulse_analysis_logic = self.connector['in']['pulseanalysislogic']['object']
        self._pulsed_measurement_logic = self.connector['in']['pulsedmeasurementlogic']['object']
        self._sequence_generator_logic = self.connector['in']['sequencegeneratorlogic']['object']
        self._save_logic = self.connector['in']['savelogic']['object']

        self._activted_main_ui(e)
        self._activated_block_settings_ui(e)

        self.count_analog_channels()
        self.count_digital_channels()
        
        # plotwidgets of analysis tab
        
        # Get the image from the logic
        # pulsed measurement tab
#        self.signal_image = pg.PlotDataItem(self._pulsed_measurement_logic.signal_plot_x, self._pulsed_measurement_logic.signal_plot_y)
#        self.lasertrace_image = pg.PlotDataItem(self._pulsed_measurement_logic.laser_plot_x, self._pulsed_measurement_logic.laser_plot_y)
#        self.sig_start_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(QtGui.QColor(255,0,0,255)))
#        self.sig_end_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(QtGui.QColor(255,0,0,255)))
#        self.ref_start_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(QtGui.QColor(0,255,0,255)))
#        self.ref_end_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(QtGui.QColor(0,255,0,255)))        
#
#        # Add the display item to the xy VieWidget, which was defined in
#        # the UI file.
#        self._mw.signal_plot_ViewWidget.addItem(self.signal_image)
#        self._mw.lasertrace_plot_ViewWidget.addItem(self.lasertrace_image)
#        self._mw.lasertrace_plot_ViewWidget.addItem(self.sig_start_line)
#        self._mw.lasertrace_plot_ViewWidget.addItem(self.sig_end_line)
#        self._mw.lasertrace_plot_ViewWidget.addItem(self.ref_start_line)
#        self._mw.lasertrace_plot_ViewWidget.addItem(self.ref_end_line)
#        self._mw.signal_plot_ViewWidget.showGrid(x=True, y=True, alpha=0.8)


        # Set the state button as ready button as default setting.
        self._mw.idle_radioButton.click()

        # Configuration of the comboWidget
#        self._mw.binning_comboBox.addItem(str(self._pulsed_measurement_logic.fast_counter_status['binwidth_ns']))
#        self._mw.binning_comboBox.addItem(str(self._pulsed_measurement_logic.fast_counter_status['binwidth_ns']*2.))
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
        
        #######################################################################
        ##                      Connect signals                              ##
        #######################################################################

        # Connect the RadioButtons and connect to the events if they are clicked:
        # pulsed measurement tab
        self._mw.idle_radioButton.toggled.connect(self.idle_clicked)
        self._mw.run_radioButton.toggled.connect(self.run_clicked)
        
        self._mw.pull_data_pushButton.clicked.connect(self.pull_data_clicked)
        self._mw.pull_data_pushButton.setEnabled(False)

#        self._pulsed_measurement_logic.signal_laser_plot_updated.connect(self.refresh_lasertrace_plot)
#        self._pulsed_measurement_logic.signal_signal_plot_updated.connect(self.refresh_signal_plot)
#        self._pulsed_measurement_logic.signal_time_updated.connect(self.refresh_elapsed_time)
        # sequence generator tab

        
        # Connect InputWidgets to events
        # pulsed measurement tab
#        self._mw.numlaser_InputWidget.editingFinished.connect(self.seq_parameters_changed)
#        self._mw.lasertoshow_spinBox.valueChanged.connect(self.seq_parameters_changed)
#        self._mw.taustart_InputWidget.editingFinished.connect(self.seq_parameters_changed)
#        self._mw.tauincrement_InputWidget.editingFinished.connect(self.seq_parameters_changed)
#        self._mw.signal_start_InputWidget.editingFinished.connect(self.analysis_parameters_changed)
#        self._mw.signal_length_InputWidget.editingFinished.connect(self.analysis_parameters_changed)
#        self._mw.reference_start_InputWidget.editingFinished.connect(self.analysis_parameters_changed)
#        self._mw.reference_length_InputWidget.editingFinished.connect(self.analysis_parameters_changed)
#        self._mw.analysis_period_InputWidget.editingFinished.connect(self.analysis_parameters_changed)
        # sequence generator tab
#        self._mw.pg_timebase_InputWidget.editingFinished.connect(self.check_input_with_samplerate)
#        self._mw.rabi_mwfreq_InputWidget.editingFinished.connect(self.check_input_with_samplerate)
#        self._mw.rabi_mwpower_InputWidget.editingFinished.connect(self.check_input_with_samplerate)
#        self._mw.rabi_waittime_InputWidget.editingFinished.connect(self.check_input_with_samplerate)
#        self._mw.rabi_lasertime_InputWidget.editingFinished.connect(self.check_input_with_samplerate)
#        self._mw.rabi_taustart_InputWidget.editingFinished.connect(self.check_input_with_samplerate)
#        self._mw.rabi_tauend_InputWidget.editingFinished.connect(self.check_input_with_samplerate)
#        self._mw.rabi_tauincrement_InputWidget.editingFinished.connect(self.check_input_with_samplerate)
        
#        self.seq_parameters_changed()
#        self.analysis_parameters_changed()
#        
#        self._mw.actionSave_Data.triggered.connect(self.save_clicked)
        
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
        self._param_block['Repeat?'] = self._get_settings_checkbox()
        self._param_block['Use as tau?'] = self._get_settings_checkbox()


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

        # emit a trigger event when for all mouse click and keyboard click events:
        self._mw.init_block_TableWidget.setEditTriggers(QtGui.QAbstractItemView.AllEditTriggers)
        self._mw.repeat_block_TableWidget.setEditTriggers(QtGui.QAbstractItemView.AllEditTriggers)

        self.insert_parameters(column=0)

        self.keep_former_block_settings()

        # Modified by me
        self._mw.init_block_TableWidget.viewport().setAttribute(QtCore.Qt.WA_Hover)
        self._mw.repeat_block_TableWidget.viewport().setAttribute(QtCore.Qt.WA_Hover)

    def _get_settings_combobox(self):
        """ Get the custom setting for a general ComboBox object.

        @return list[N]: A list with pulse functions.

        This return object must coincide with the according delegate class.
        """
        return [ComboBoxDelegate,'Idle','Sin','Cos','DC','Sin-Gauss']

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
        return [DoubleSpinBoxDelegate, 0.0, -1000000, 1000000, 0.1, 5]

    def _get_settings_dspinbox_freq(self):
        """ Get the custom setting for a general frequency DoubleSpinBox object.

        @return list[5]: A list with
                        [class, default_val, min_val, max_val, step_size, digits]

        This return object must coincide with the according delegate class.
        """
        return [DoubleSpinBoxDelegate, 2.8, 0, 1000000, 0.01, 5]

    def _get_settings_dspinbox_amp(self):
        """ Get the custom setting for a general amplitude DoubleSpinBox object.

        @return list[5]: A list with
                        [class, default_val, min_val, max_val, step_size, digits]

        This return object must coincide with the according delegate class.
        """
        return [DoubleSpinBoxDelegate, 1, 0, 2, 0.01, 5]


    #FIXME: connect the current default value of length of the dspinbox with
    #       the minimal sequence length and the sampling rate.
    #FIXME: Later that should be able to round up the values directly within
    #       the entering in the dspinbox for a consistent display of the
    #       sequence length.
    def _get_settings_dspinbox_length(self):
        """ Get the custom setting for a general length DoubleSpinBox object.

        @return list[5]: A list with
                        [class, default_val, min_val, max_val, step_size, digits]

        This return object must coincide with the according delegate class.
        """
        return [DoubleSpinBoxDelegate, 10, 0, 100000000, 0.01, 5]

    def _get_settings_dspinbox_inc(self):
        """ Get the custom setting for a general increment DoubleSpinBox object.

        @return list[5]: A list with
                        [class, default_val, min_val, max_val, step_size, digits]

        This return object must coincide with the according delegate class.
        """
        return [DoubleSpinBoxDelegate, 0, 0, 2, 0.01, 5]



    def get_data_init(self, row, column):
        """ Simplified wrapper function to get the data from the init table """
        tab =self._mw.init_block_TableWidget
        data = tab.model().data(tab.model().index(row, column))
        return data



    def deactivation(self, e):
        """ Undo the Definition, configuration and initialisation of the pulsed measurement GUI.

          @param class e: event class from Fysom

        This deactivation disconnects all the graphic modules, which were
        connected in the initUI method.
        """
        self.idle_clicked()
        # disconnect signals
        self._mw.idle_radioButton.toggled.disconnect()
        self._mw.run_radioButton.toggled.disconnect()
        #self._pulsed_measurement_logic.signal_laser_plot_updated.disconnect()
        #self._pulsed_measurement_logic.signal_signal_plot_updated.disconnect()
        #self._mw.numlaser_InputWidget.editingFinished.disconnect()
        #self._mw.lasertoshow_spinBox.valueChanged.disconnect()
        self._deactivat_main_ui(e)
        self._deactivate_block_ui(e)


    def _activted_main_ui(self, e):
        """ Initialize, connect and configure the main UI. """

        self._mw = PulsedMeasurementMainWindow()

        self._mw.add_init_row_selected_PushButton.clicked.connect(self.add_init_row_before_selected)
        self._mw.del_init_row_selected_PushButton.clicked.connect(self.del_init_row_selected)
        self._mw.add_init_row_last_PushButton.clicked.connect(self.add_init_row_after_last)
        self._mw.del_init_row_last_PushButton.clicked.connect(self.del_init_row_last)
        self._mw.clear_init_table_PushButton.clicked.connect(self.clear_init_table)


        self._mw.add_repeat_row_selected_PushButton.clicked.connect(self.add_repeat_row_before_selected)
        self._mw.del_repeat_row_selected_PushButton.clicked.connect(self.del_repeat_row_selected)
        self._mw.add_repeat_row_last_PushButton.clicked.connect(self.add_repeat_row_after_last)
        self._mw.del_repeat_row_last_PushButton.clicked.connect(self.del_repeat_row_last)
        self._mw.clear_repeat_table_PushButton.clicked.connect(self.clear_repeat_table)

        # connect the menue to the actions:
        self._mw.action_Settings_Block_Generation.triggered.connect(self.show_block_settings)
        self.show()


    def _deactivat_main_ui(self, e):
        """ Disconnects the main ui and deactivates the window. """

        self._mw.add_init_row_selected_PushButton.clicked.disconnect()
        self._mw.del_init_row_selected_PushButton.clicked.disconnect()
        self._mw.add_init_row_last_PushButton.clicked.disconnect()
        self._mw.del_init_row_last_PushButton.clicked.disconnect()
        self._mw.clear_init_table_PushButton.clicked.disconnect()

        self._mw.add_repeat_row_selected_PushButton.clicked.disconnect()
        self._mw.del_repeat_row_selected_PushButton.clicked.disconnect()
        self._mw.add_repeat_row_last_PushButton.clicked.disconnect()
        self._mw.del_repeat_row_last_PushButton.clicked.disconnect()
        self._mw.clear_repeat_table_PushButton.clicked.disconnect()

        self._mw.close()

    def _activated_block_settings_ui(self, e):
        """ Initialize, connect and configure the block settings UI. """

        self._bs = BlockSettingDialog() # initialize the block settings
        self._bs.accepted.connect(self.update_block_settings)
        self._bs.rejected.connect(self.keep_former_block_settings)
        self._bs.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.update_block_settings)

    def _deactivate_block_ui(self, e):
        """ Deactivate the Block settings """
        self._bs.accepted.disconnect()
        self._bs.rejected.disconnect()
        self._bs.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.disconnect()

        self._bs.close()

    def show(self):
        """Make main window visible and put it above all other windows. """
        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def show_block_settings(self):
        """ Opens the block settings menue. """
        self._bs.exec_()

    def update_block_settings(self):
        """ Write new block settings from the gui to the file. """
        self._set_channels(num_d_ch=self._bs.digital_channels_SpinBox.value(), num_a_ch=self._bs.analog_channels_SpinBox.value())
        # self._use_digital_ch(self._bs.digital_channels_SpinBox.value())
        # self._use_analog_channel(self._bs.analog_channels_SpinBox.value())

    def keep_former_block_settings(self):
        """ Keep the old block settings and restores them in the gui. """

        self._bs.digital_channels_SpinBox.setValue(self._num_d_ch)
        self._bs.analog_channels_SpinBox.setValue(self._num_a_ch)






    def add_init_row_before_selected(self):
        """
        """
        selected_row = self._mw.init_block_TableWidget.currentRow()

        self._mw.init_block_TableWidget.insertRow(selected_row)



    def add_n_rows(self, row_pos, ):
        pass



    def add_init_row_after_last(self):
        """

        """
        pass


    def del_init_row_selected(self):
        """
        """
        # get the row number of the selected item(s). That will return the
        # lowest selected row
        row_to_remove = self._mw.init_block_TableWidget.currentRow()
        self._mw.init_block_TableWidget.removeRow(row_to_remove)
        #self.update_sequence_parameters()
        pass

    def del_init_row_last(self):
        """
        """
        number_of_rows = self._mw.init_block_TableWidget.rowCount()
        # remember, the row index is started to count from 0 and not from 1,
        # therefore one has to reduce the value by 1:
        self._mw.init_block_TableWidget.removeRow(number_of_rows-1)
        #self.update_sequence_parameters()
        pass

    def clear_init_table(self):
        """
        """

        self._mw.init_block_TableWidget.setRowCount(1)
        self._mw.init_block_TableWidget.clearContents()



    def add_repeat_row_after_last(self):
        """
        """
        pass

    def add_repeat_row_before_selected(self):
        """
        """

        pass


    def del_repeat_row_selected(self):
        """
        """

        row_to_remove = self._mw.repeat_block_TableWidget.currentRow()
        self._mw.repeat_block_TableWidget.removeRow(row_to_remove)
        #self.update_sequence_parameters()
        pass

    def del_repeat_row_last(self):
        """
        """
        number_of_rows = self._mw.repeat_block_TableWidget.rowCount()
        # remember, the row index is started to count from 0 and not from 1,
        # therefore one has to reduce the value by 1:
        self._mw.repeat_block_TableWidget.removeRow(number_of_rows-1)
        #self.update_sequence_parameters()
        pass

    def clear_repeat_table(self):
        """
        """

        self._mw.repeat_block_TableWidget.setRowCount(1)
        self._mw.repeat_block_TableWidget.clearContents()


    def insert_parameters(self, column):

        # insert parameter:
        insert_at_col_pos = column
        for column, parameter in enumerate(self._param_block):

            self._mw.init_block_TableWidget.insertColumn(insert_at_col_pos+column)
            self._mw.init_block_TableWidget.setHorizontalHeaderItem(insert_at_col_pos+column, QtGui.QTableWidgetItem())
            self._mw.init_block_TableWidget.horizontalHeaderItem(insert_at_col_pos+column).setText('{0}'.format(parameter))
            self._mw.init_block_TableWidget.setColumnWidth(insert_at_col_pos+column, 70)

            # add the new properties to the whole column through delegate:
            items_list = self._param_block[parameter][1:]

            # extract the classname from the _param_block list to be able to deligate:
            delegate = eval(self._param_block[parameter][0].__name__)(self._mw.init_block_TableWidget, items_list)
            self._mw.init_block_TableWidget.setItemDelegateForColumn(insert_at_col_pos+column, delegate)

            # initialize the whole row with default values:
            for row_num in range(self._mw.init_block_TableWidget.rowCount()):
                # get the model, here are the data stored:
                model = self._mw.init_block_TableWidget.model()
                # get the corresponding index of the current element:
                index = model.index(row_num, insert_at_col_pos+column)
                # get the initial values of the delegate class which was
                # uses for this column:
                ini_values = delegate.get_initial_value()
                # set initial values:
                model.setData(index, ini_values[0], ini_values[1])

            self._mw.repeat_block_TableWidget.insertColumn(insert_at_col_pos+column)
            self._mw.repeat_block_TableWidget.setHorizontalHeaderItem(insert_at_col_pos+column, QtGui.QTableWidgetItem())
            self._mw.repeat_block_TableWidget.horizontalHeaderItem(insert_at_col_pos+column).setText('{0}'.format(parameter))
            self._mw.repeat_block_TableWidget.setColumnWidth(insert_at_col_pos+column, 70)

            # add the new properties to the whole column through delegate:
            items_list = self._param_block[parameter][1:]

            # extract the classname from the _param_block list to be able to deligate:
            delegate = eval(self._param_block[parameter][0].__name__)(self._mw.repeat_block_TableWidget, items_list)
            self._mw.repeat_block_TableWidget.setItemDelegateForColumn(insert_at_col_pos+column, delegate)

            # initialize the whole row with default values:
            for row_num in range(self._mw.repeat_block_TableWidget.rowCount()):
                # get the model, here are the data stored:
                model = self._mw.repeat_block_TableWidget.model()
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
        procedure is based on the init_block_TableWidget since it is assumed
        that all operation on the init_block_TableWidget is also applied on
        repeat_block_TableWidget.
        """
        count_dch = 0
        for column in range(self._mw.init_block_TableWidget.columnCount()):
            if 'DCh' in self._mw.init_block_TableWidget.horizontalHeaderItem(column).text():
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

        for column in range(self._mw.init_block_TableWidget.columnCount()):
            self._mw.init_block_TableWidget.setItemDelegateForColumn(column,None)
            self._mw.repeat_block_TableWidget.setItemDelegateForColumn(column,None)

        self._mw.init_block_TableWidget.setColumnCount(0)
        self._mw.repeat_block_TableWidget.setColumnCount(0)

        num_a_d_ch =  num_a_ch*len(self._param_a_ch) + num_d_ch*len(self._param_d_ch)
        # num_ch = num_a_d_ch + len(self._param_block)
        #
        #
        self._mw.init_block_TableWidget.setColumnCount(num_a_d_ch)
        self._mw.repeat_block_TableWidget.setColumnCount(num_a_d_ch)

        # if num_a_ch == 0:
        #     for column in range(num_d_ch):
        #         self._mw.init_block_TableWidget.insertColumn

        num_a_to_create = num_a_ch
        num_d_to_create = num_d_ch

        a_created = False
        d_created = False

        column = 0
        while (column < num_a_d_ch):

            if num_a_to_create == 0 or a_created:

                self._mw.init_block_TableWidget.setHorizontalHeaderItem(column, QtGui.QTableWidgetItem())
                self._mw.init_block_TableWidget.horizontalHeaderItem(column).setText('DCh{:d}'.format(num_d_ch-num_d_to_create))
                self._mw.init_block_TableWidget.setColumnWidth(column, 40)

                items_list = self._param_d_ch['CheckBox'][1:]
                checkDelegate = CheckBoxDelegate(self._mw.init_block_TableWidget, items_list)
                self._mw.init_block_TableWidget.setItemDelegateForColumn(column, checkDelegate)

                self._mw.repeat_block_TableWidget.setHorizontalHeaderItem(column, QtGui.QTableWidgetItem())
                self._mw.repeat_block_TableWidget.horizontalHeaderItem(column).setText('DCh{:d}'.format(num_d_ch-num_d_to_create) )
                self._mw.repeat_block_TableWidget.setColumnWidth(column, 40)

                items_list = self._param_d_ch['CheckBox'][1:]
                checkDelegate = CheckBoxDelegate(self._mw.repeat_block_TableWidget, items_list)
                self._mw.repeat_block_TableWidget.setItemDelegateForColumn(column, checkDelegate)

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
                for param_pos, parameter in enumerate(self._param_a_ch):

                    # initial block:
                    self._mw.init_block_TableWidget.setHorizontalHeaderItem(column+param_pos, QtGui.QTableWidgetItem())
                    self._mw.init_block_TableWidget.horizontalHeaderItem(column+param_pos).setText('ACh{:d}\n'.format(num_a_ch-num_a_to_create) + parameter)
                    self._mw.init_block_TableWidget.setColumnWidth(column+param_pos, 70)

                    # add the new properties to the whole column through delegate:
                    items_list = self._param_a_ch[parameter][1:]

                    # extract the classname from the _param_a_ch list to be able to deligate:
                    delegate = eval(self._param_a_ch[parameter][0].__name__)(self._mw.init_block_TableWidget, items_list)
                    self._mw.init_block_TableWidget.setItemDelegateForColumn(column+param_pos, delegate)

                    # repeated block:
                    self._mw.repeat_block_TableWidget.setHorizontalHeaderItem(column+param_pos, QtGui.QTableWidgetItem())
                    self._mw.repeat_block_TableWidget.horizontalHeaderItem(column+param_pos).setText('ACh{:d}\n'.format(num_a_ch-num_a_to_create) + parameter)
                    self._mw.repeat_block_TableWidget.setColumnWidth(column+param_pos, 70)

                    # add the new properties to the whole column through delegate:
                    items_list = self._param_a_ch[parameter][1:]

                    # extract the classname from the _param_a_ch list to be able to deligate:
                    delegate = eval(self._param_a_ch[parameter][0].__name__)(self._mw.repeat_block_TableWidget, items_list)
                    self._mw.repeat_block_TableWidget.setItemDelegateForColumn(column+param_pos, delegate)

                column = column + len(self._param_a_ch)
                num_a_to_create = num_a_to_create - 1



        self._num_a_ch = num_a_ch
        self._num_d_ch = num_d_ch
        self.insert_parameters(num_a_d_ch)

        self.initialize_row_init_block(0,self._mw.init_block_TableWidget.rowCount())
        self.initialize_row_repeat_block(0,self._mw.repeat_block_TableWidget.rowCount())

    def initialize_row_init_block(self, start_row, stop_row=None):

        if stop_row is None:
            stop_row = start_row +1

        for col_num in range(self._mw.init_block_TableWidget.columnCount()):

            for row_num in range(start_row,stop_row):
                # get the model, here are the data stored:
                model = self._mw.init_block_TableWidget.model()
                # get the corresponding index of the current element:
                index = model.index(row_num, col_num)
                # get the initial values of the delegate class which was
                # uses for this column:
                ini_values = self._mw.init_block_TableWidget.itemDelegateForColumn(col_num).get_initial_value()
                # set initial values:
                model.setData(index, ini_values[0], ini_values[1])


    def initialize_row_repeat_block(self, start_row, stop_row=None):

        if stop_row is None:
            stop_row = start_row +1

        for col_num in range(self._mw.repeat_block_TableWidget.columnCount()):

            for row_num in range(start_row,stop_row):
                # get the model, here are the data stored:
                model = self._mw.repeat_block_TableWidget.model()
                # get the corresponding index of the current element:
                index = model.index(row_num, col_num)
                # get the initial values of the delegate class which was
                # uses for this column:
                ini_values = self._mw.repeat_block_TableWidget.itemDelegateForColumn(col_num).get_initial_value()
                # set initial values:
                model.setData(index, ini_values[0], ini_values[1])


    def count_analog_channels(self):
        """ Get the number of currently displayed analog channels.

        @return int: number of analog channels

        The number of analog channal are counted and return and additionally
        the internal counter variable _num_a_ch is updated. The counting
        procedure is based on the init_block_TableWidget since it is assumed
        that all operation on the init_block_TableWidget is also applied on
        repeat_block_TableWidget.
        """

        count_a_ch = 0
        # there must be definitly less analog channels then available columns
        # in the table, therefore the number of columns can be used as the
        # upper border.
        for poss_a_ch in range(self._mw.init_block_TableWidget.columnCount()):
            for column in range(self._mw.init_block_TableWidget.columnCount()):
                if ('ACh'+str(poss_a_ch)) in self._mw.init_block_TableWidget.horizontalHeaderItem(column).text():
                    # analog channel found, break the inner loop to
                    count_a_ch = count_a_ch + 1
                    break

        self._num_a_ch = count_a_ch
        return self._num_a_ch

    def idle_clicked(self):
        """ Stopp the scan if the state has switched to idle. """
        self._pulsed_measurement_logic.stop_pulsed_measurement()
        self._mw.frequency_InputWidget.setEnabled(True)
        self._mw.power_InputWidget.setEnabled(True)
        self._mw.binning_comboBox.setEnabled(True)
        self._mw.pull_data_pushButton.setEnabled(False)


    def run_clicked(self, enabled):
        """ Manages what happens if odmr scan is started.

        @param bool enabled: start scan if that is possible
        """

        #Firstly stop any scan that might be in progress
        self._pulse_analysis_logic.stop_pulsed_measurement()
        #Then if enabled. start a new scan.
        if enabled:
            self._mw.frequency_InputWidget.setEnabled(False)
            self._mw.power_InputWidget.setEnabled(False)
            self._mw.binning_comboBox.setEnabled(False)
            self._mw.pull_data_pushButton.setEnabled(True)
            self._pulsed_measurement_logic.start_pulsed_measurement()

    def pull_data_clicked(self):
        self._pulsed_measurement_logic.manually_pull_data()



    def refresh_lasertrace_plot(self):
        ''' This method refreshes the xy-plot image
        '''
        self.lasertrace_image.setData(self._pulse_analysis_logic.laser_plot_x, self._pulse_analysis_logic.laser_plot_y)

    def refresh_signal_plot(self):
        ''' This method refreshes the xy-matrix image
        '''
        self.signal_image.setData(self._pulse_analysis_logic.signal_plot_x, self._pulse_analysis_logic.signal_plot_y)
        
#    def seq_parameters_changed(self):
#        laser_num = int(self._mw.numlaser_InputWidget.text())
#        tau_start = int(self._mw.taustart_InputWidget.text())
#        tau_incr = int(self._mw.tauincrement_InputWidget.text())
#        mw_frequency = float(self._mw.frequency_InputWidget.text())
#        mw_power = float(self._mw.power_InputWidget.text())
#        self._mw.lasertoshow_spinBox.setRange(0, laser_num)
#        laser_show = self._mw.lasertoshow_spinBox.value()
#        if (laser_show > laser_num):
#            self._mw.lasertoshow_spinBox.setValue(0)
#            laser_show = self._mw.lasertoshow_spinBox.value()
#        tau_vector = np.array(range(tau_start, tau_start + tau_incr*laser_num, tau_incr))
#        self._pulsed_measurement_logic.running_sequence_parameters['tau_vector'] = tau_vector
#        self._pulsed_measurement_logic.running_sequence_parameters['number_of_lasers'] = laser_num
#        self._pulsed_measurement_logic.display_pulse_no = laser_show
#        self._pulsed_measurement_logic.mykrowave_freq = mw_frequency
#        self._pulsed_measurement_logic.mykrowave_power = mw_power
#        return
#     
#     
#    def analysis_parameters_changed(self):
#        sig_start = int(self._mw.signal_start_InputWidget.text())
#        sig_length = int(self._mw.signal_length_InputWidget.text())
#        ref_start = int(self._mw.reference_start_InputWidget.text())
#        ref_length = int(self._mw.reference_length_InputWidget.text())
#        timer_interval = float(self._mw.analysis_period_InputWidget.text())
#        self.signal_start_bin = sig_start
#        self.signal_width_bins = sig_length
#        self.norm_start_bin = ref_start
#        self.norm_width_bins = ref_length
#        self.sig_start_line.setValue(sig_start)
#        self.sig_end_line.setValue(sig_start+sig_length)
#        self.ref_start_line.setValue(ref_start)
#        self.ref_end_line.setValue(ref_start+ref_length)
#        self._pulsed_measurement_logic.signal_start_bin = sig_start
#        self._pulsed_measurement_logic.signal_width_bin = sig_length
#        self._pulsed_measurement_logic.norm_start_bin = ref_start
#        self._pulsed_measurement_logic.norm_width_bin = ref_length
#        self._pulsed_measurement_logic.change_timer_interval(timer_interval)
#        return


    def create_row(self):
        ''' This method creates a new row in the TableWidget at the current cursor position.
        '''
        # block all signals from the TableWidget
        self._mw.sequence_tableWidget.blockSignals(True)
        # insert empty row after current cursor position
        current_row = self._mw.sequence_tableWidget.currentRow()+1
        if current_row == 0:
            current_row = self._mw.sequence_tableWidget.rowCount()

        self._mw.sequence_tableWidget.insertRow(current_row)

        # create the checkbox item to fill the channel rows and the "use as tau" row with
        chkBoxItem  = QtGui.QTableWidgetItem()
        chkBoxItem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        chkBoxItem.setCheckState(QtCore.Qt.Unchecked)

        # fill channel rows with the checkbox item
        for i in range(8):
            self._mw.sequence_tableWidget.setItem(current_row, i, chkBoxItem.clone())

        # create text field item and put it in the "length" and "increment" column
        textItem = QtGui.QTableWidgetItem('0')
        textItem.setFlags(QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled)
        self._mw.sequence_tableWidget.setItem(current_row, 8, textItem)
        self._mw.sequence_tableWidget.setItem(current_row, 9, textItem.clone())

        # put checkbox items into "repeat?" and "use as tau?" column
        self._mw.sequence_tableWidget.setItem(current_row, 10, chkBoxItem.clone())
        self._mw.sequence_tableWidget.setItem(current_row, 11, chkBoxItem.clone())

        # increment current row
        self._mw.sequence_tableWidget.setCurrentCell(current_row, 0)
        # unblock all signals from the TableWidget
        self._mw.sequence_tableWidget.blockSignals(False)
        return


    def delete_row(self):
        ''' This method deletes a row in the TableWidget at the current cursor position.
        '''
        # block all signals from the TableWidget
        self._mw.sequence_tableWidget.blockSignals(True)

        # check if a current row is selected. Select last row if not.
        current_row = self._mw.sequence_tableWidget.currentRow()
        if current_row == -1:
            current_row = self._mw.sequence_tableWidget.rowCount()

        # delete current row and all its items
        self._mw.sequence_tableWidget.removeRow(current_row)

        # decrement current row
        self._mw.sequence_tableWidget.setCurrentCell(current_row-1, 8)

        # unblock all signals from the TableWidget
        self._mw.sequence_tableWidget.blockSignals(False)
        return


    def clear_list(self):
        ''' This method deletes all rows in the TableWidget.
        '''
        # block all signals from the TableWidget
        self._mw.sequence_tableWidget.blockSignals(True)

        # clear the TableWidget
        number_of_rows = self._mw.sequence_tableWidget.rowCount()

        while number_of_rows >= 0:
            self._mw.sequence_tableWidget.removeRow(number_of_rows)
            number_of_rows -= 1

        # unblock all signals from the TableWidget
        self._mw.sequence_tableWidget.blockSignals(False)
        return


    def sequence_parameters_changed(self, item):
        ''' This method calculates and updates all parameters (size, length etc.) upon a change of a sequence entry.

        @param QTableWidgetItem item: Table item that has been changed
        '''
        # Check if the changed item is of importance for the parameters
        if (item.column() in [0,8,9,10]):
            # calculate the current sequence parameters
            self.update_sequence_parameters()
        return


    def update_sequence_parameters(self):
        """ Initialize the matrix creation and update the logic. """
        # calculate the current sequence parameters
        repetitions = int(self._mw.repetitions_lineEdit.text())
        matrix = self.get_matrix()
        self._sequence_generator_logic.update_sequence_parameters(matrix, repetitions)

        # get updated values from SequenceGeneratorLogic
        length_bins = self._sequence_generator_logic._current_sequence_parameters['length_bins']
        length_ms = self._sequence_generator_logic._current_sequence_parameters['length_ms']
        number_of_lasers = self._sequence_generator_logic._current_sequence_parameters['number_of_lasers']

        # update the DisplayWidgets
        self._mw.length_bins_lcdNumber.display(length_bins)
        self._mw.length_s_lcdNumber.display(length_ms)
        self._mw.laser_number_lcdNumber.display(number_of_lasers)
        return


#    def reset_parameters(self):
#        ''' This method resets all GUI parameters to the default state.
#        '''
#        # update the DisplayWidgets
#        self._mw.length_bins_lcdNumber.display(0)
#        self._mw.length_s_lcdNumber.display(0)
#        self._mw.laser_number_lcdNumber.display(0)


    def save_sequence(self):
        ''' This method encodes the currently edited sequence into a matrix for passing it to the logic module.
            There the sequence will be created and saved.
        '''
        # Create matrix to pass the data to the logic module where it will be saved
        name = str(self._mw.sequence_name_lineEdit.text())
        # update current sequence parameters in the logic
        self.update_sequence_parameters()
        # save current sequence under name "name"
        self._sequence_generator_logic.save_sequence(name)
        # update sequence combo boxes
        self.sequence_list_changed()
        return


    def get_matrix(self):
        """ Create a Matrix from the GUI's TableWidget.

        This method creates a matrix out of the current TableWidget to be
        further processed by the logic module.
        """
        # get the number of rows and columns
        num_of_rows = self._mw.sequence_tableWidget.rowCount()
        num_of_columns = self._mw.sequence_tableWidget.columnCount()

        #FIXME: the matrix should not be in the future not an integer type
        #       since the length of a pulse can and have sometimes to be an
        #       float value.

        # Initialize a matrix of proper size and integer data type
        matrix = np.empty([num_of_rows, num_of_columns], dtype=int)
        # Loop through all matrix entries and fill them with the data of the TableWidgetItems
        for row in range(num_of_rows):
            for column in range(num_of_columns):
                # Get the item of the current row and column
                item = self._mw.sequence_tableWidget.item(row, column)
                # check if the current column is a checkbox or a textfield
                if (int(item.flags()) & 16):
                    matrix[row, column] = int(bool(item.checkState()))
                else:
                    matrix[row, column] = int(item.data(0))
        return matrix


    def create_table(self):
        ''' This method creates a TableWidget out of the current matrix passed from the logic module.
        '''
        # get matrix from the sequence generator logic
        matrix = self._sequence_generator_logic._current_matrix
        # clear current table widget
        self.clear_list()
        # create as many rows in the table widget as the matrix has and fill them with entries
        for row_number, row in enumerate(matrix):
            # create the row
            self.create_row()
            # block all signals from the TableWidget
            self._mw.sequence_tableWidget.blockSignals(True)
            # edit all items in the row
            for column_number in range(matrix.shape[1]):
                item = self._mw.sequence_tableWidget.item(row_number, column_number)
                # is the current item a checkbox or a number?
                if (int(item.flags()) & 16):
                    # check ckeckbox if the corresponding matrix entry is "1"
                    if matrix[row_number, column_number] == 1:
                        item.setCheckState(QtCore.Qt.Checked)
                else:
                    item.setText(str(matrix[row_number, column_number]))
        # unblock all signals from the TableWidget
        self._mw.sequence_tableWidget.blockSignals(False)
        return


    def delete_sequence(self):
        ''' This method completely removes the currently selected sequence.
        '''
        # call the delete method in the sequence generator logic
        name = self._mw.sequence_list_comboBox.currentText()
        self._sequence_generator_logic.delete_sequence(name)
        # update the combo boxes
        self.sequence_list_changed()
        self.clear_list()
        return


    def sequence_list_changed(self):
        ''' This method updates the Seqeuence combo boxes upon the adding or removal of a sequence
        '''
        # get the names of all saved sequences from the sequence generator logic
        names = self._sequence_generator_logic.get_sequence_names()
        # clear combo boxes
        self._mw.sequence_name_comboBox.clear()
        self._mw.sequence_list_comboBox.clear()
        # fill combo boxes with current names
        self._mw.sequence_name_comboBox.addItems(names)
        self._mw.sequence_list_comboBox.addItems(names)
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


    def clear_list_clicked(self):
        ''' This method clears the current tableWidget, inserts a single empty row and updates the sequence parameters in the GUI and SequenceGeneratorLogic
        '''
        self.clear_list()
        self.create_row()
        self.update_sequence_parameters()
        return





    def test(self):
        print('called test function!')
        print(str(self._mw.sequence_list_comboBox.currentText()))
        return
#
#
#
#    ###########################################################################
#    ##                         Change Methods                                ##
#    ###########################################################################
#
#    def change_frequency(self):
#        self._pulse_analysis_logic.MW_frequency = float(self._mw.frequency_InputWidget.text())
#
#    def change_power(self):
#        self._pulse_analysis_logic.MW_power = float(self._mw.power_InputWidget.text())
#
#    def change_pg_frequency(self):
#        self._pulse_analysis_logic.pulse_generator_frequency = float(self._mw.pg_frequency_lineEdit.text())
#
#    def change_runtime(self):
#        pass
