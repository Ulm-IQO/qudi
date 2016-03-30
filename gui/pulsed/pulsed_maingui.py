# -*- coding: utf-8 -*-

"""
This file contains the QuDi main GUI for pulsed measurements.

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

Copyright (C) 2015-2016 Alexander Stark alexander.stark@uni-ulm.de
"""

from PyQt4 import QtGui, QtCore, uic
import numpy as np
import os
from collections import OrderedDict
import pyqtgraph as pg
import pyqtgraph.exporters
import re
import inspect
import itertools
import datetime

from gui.guibase import GUIBase
from core.util.mutex import Mutex
from .qradiobutton_custom import CustomQRadioButton


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
#FIXME: Check whether as load_pulse_block_ensemble method is necessary.

# =============================================================================
#                       Define some delegate classes.
# =============================================================================
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

# ==============================================================================
#                Explanation of the usage of QTableWidget
# ==============================================================================

# In general a table consist out of an object for viewing the data and out of an
# object where the data are saved. For viewing the data, there is the general
# QWidgetView class and for holding/storing the data you have to define a model.
# The model ensures to hold your data in the proper data type and give the
# possibility to separate the data from the display.
# The QTableWidget class is a specialized class to handle user input into an
# table. In order to handle the data, it contains already a model (due to that
# you can e.g. easily add rows and columns and modify the content of each cell).
# Therefore the model of a QTableWidget is a privite attribute and cannot be
# changed externally. If you want to define a custom model for QTableWidget you
# have to start from a QTableView and construct you own data handling in the
# model.
# Since QTableWidget has all the (nice and) needed requirements for us, a
# custom definition of QTableView with a Model is not needed.


from .spinbox_delegate import SpinBoxDelegate
from .doublespinbox_delegate import DoubleSpinBoxDelegate
from .combobox_delegate import ComboBoxDelegate
from .checkbox_delegate import CheckBoxDelegate

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

class AnalysisSettingDialog(QtGui.QDialog):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui-pulsed-main-gui-settings-analysis.ui')

        # Load it
        super(AnalysisSettingDialog, self).__init__()

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
    """ This is the main GUI Class for pulsed measurements. """

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
        c_dict = {'onactivate': self.initUI, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, c_dict)

        self.logMsg('The following configuration was found.',
                    msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')

        #locking for thread safety
        self.threadlock = Mutex()

    def initUI(self, e=None):
        """ Initialize, connect and configure the pulsed measurement GUI.

        @param object e: Fysom.event object from Fysom class.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.

        Establish general connectivity and activate the different tabs of the
        GUI.
        """

        self._pulsed_ana_logic = self.connector['in']['pulseanalysislogic']['object']
        self._pulsed_meas_logic  = self.connector['in']['pulsedmeasurementlogic']['object']
        self._seq_gen_logic = self.connector['in']['sequencegeneratorlogic']['object']
        self._save_logic = self.connector['in']['savelogic']['object']

        self._mw = PulsedMeasurementMainWindow()


        # each tab/section has its own activation methods:
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

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.

        This deactivation disconnects all the graphic modules, which were
        connected in the initUI method.
        """

        # each tab/section has its own deactivation methods:
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

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """

        self._bs = BlockSettingDialog() # initialize the block settings
        self._bs.accepted.connect(self.update_block_settings)
        self._bs.rejected.connect(self.keep_former_block_settings)
        self._bs.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.update_block_settings)

        # load in the possible channel configurations into the config
        pulser_constr = self.get_hardware_constraints()
        channel_config = list(pulser_constr['channel_config'])
        self._bs.channel_config_ComboBox.clear()
        self._bs.channel_config_ComboBox.addItems(channel_config)

        self._bs.channel_config_ComboBox.currentIndexChanged.connect(self._update_channel_display)

        activation_map = list(pulser_constr['activation_map'])
        self._bs.ch_activation_pattern_ComboBox.clear()
        self._bs.ch_activation_pattern_ComboBox.addItems(activation_map)

        self._bs.ch_activation_pattern_ComboBox.currentIndexChanged.connect(self._update_activation_map)
        self._bs.use_interleave_CheckBox.stateChanged.connect(self._interleave_changed)

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

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """

        self._bs.accepted.disconnect()
        self._bs.rejected.disconnect()
        self._bs.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.disconnect()

        self._bs.close()

    def _interleave_changed(self, state):
        """ React on a Interleave state change.

        @param int state: 0 for False and 1 or 2 for True.
        """
        self._seq_gen_logic.set_interleave(bool(state))
        # Check also whether the sample rate has been changed:
        self._set_sample_rate_constraints()

    def _update_channel_display(self, index=None):
        """ Updates the channel display of the currently chosen configuration in
            the settings for Block Generator.

        @param int index: optional, update the display boxes with the
                          configuration corresponding to the passed index in the
                          Combobox. Otherwise the active index will be asked
                          from the Combobox.
        """
        if index is None:
            config = self._bs.channel_config_ComboBox.currentText()
        else:
            config = self._bs.channel_config_ComboBox.itemText(index)

        channel_config = self.get_hardware_constraints()['channel_config'][config]

        # Here just the number of analog or digital channels is needed:
        self._bs.digital_channels_SpinBox.setValue(channel_config.count('d_ch'))
        self._bs.analog_channels_SpinBox.setValue(channel_config.count('a_ch'))


    def _update_activation_map(self, index=None):
        """ Switches the dedicated Radiobuttons for the channels on or off.
        Also activates the chosen channels in the hardware.

        @param int index: optional, update the display boxes with the
                          configuration corresponding to the passed index in the
                          Combobox. Otherwise the active index will be asked
                          from the Combobox.

        The Radiobuttons are used to show the channel activity. Moreover, if
        pulser is switched on, it will tell which channels are switched on.
        """

        pulser_const = self.get_hardware_constraints()

        available_ch =  list(pulser_const['available_ch'])

        if index is None:
            map = self._bs.ch_activation_pattern_ComboBox.currentText()
        else:
            map = self._bs.ch_activation_pattern_ComboBox.itemText(index)

        activation_map = pulser_const['activation_map'][map]
        self._bs.ch_activation_pattern_LineEdit.setText(str(activation_map))
        # at first disable all the channels:

        for channelname in available_ch:
            radiobutton_obj = self.get_radiobutton_obj(channelname)
            radiobutton_obj.setEnabled(False)

        for channelname in activation_map:
            radiobutton_obj = self.get_radiobutton_obj(channelname)
            radiobutton_obj.setEnabled(True)

        # activate channels in hardware
        a_ch = {}   # create something like  a_ch = {1:True, 2:True} to switch
        d_ch = {}   # the various channel separetely on.
        # reset all channels to False
        for ch_name in pulser_const['available_ch'].keys():
            if 'ACH' in ch_name:
                a_ch[int(ch_name[-1])] = False
            if 'DCH' in ch_name:
                d_ch[int(ch_name[-1])] = False
        # Set desired channels to True
        for ch_name in activation_map:
            ch_type = list(pulser_const['available_ch'][ch_name])[0]
            if 'a_ch' == ch_type:
                a_ch[pulser_const['available_ch'][ch_name][ch_type]] = True
            if 'd_ch' == ch_type:
                d_ch[pulser_const['available_ch'][ch_name][ch_type]] = True




    def show_block_settings(self):
        """ Opens the block settings menue. """
        self._bs.exec_()


    def show_prepared_methods(self):
        """ Opens the prepared methods Window."""
        self._pm.show()
        self._pm.raise_()

    def update_block_settings(self):
        """ Write new block settings from the gui to the file. """

        self._mw.block_editor_TableWidget.blockSignals(True)

        ch_settings = (self._bs.analog_channels_SpinBox.value(),
                       self._bs.digital_channels_SpinBox.value())

        self._set_block_editor_columns(num_a_ch=ch_settings[0],
                                       num_d_ch=ch_settings[1])

        self._mw.block_editor_TableWidget.blockSignals(False)

        #FIXME: Think about whether this method should not make an instant
        #       action if an activation map is chosen, but rather be executed on
        #       on pressing the apply and cancel button:
        self._update_activation_map()


    def keep_former_block_settings(self):
        """ Keep the old block settings and restores them in the gui. """

        self._bs.digital_channels_SpinBox.setValue(self._num_d_ch)
        self._bs.analog_channels_SpinBox.setValue(self._num_a_ch)

        #FIXME: Think about whether this method should not make an instant
        #       action if an activation map is chosen, but rather be executed on
        #       on pressing the apply and cancel button:
        self._update_activation_map()


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

    ###########################################################################
    ###   Methods related to Tab 'Pulse Generator' in the Pulsed Window:    ###
    ###########################################################################

    def _activate_pulse_generator_ui(self, e):
        """ Initialize, connect and configure the 'Pulse Generator' Tab.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        # connect the signal for a change of the sample frequency
        self._mw.sample_freq_DSpinBox.editingFinished.connect(self.update_sample_rate)
        self._set_sample_rate_constraints()

        # set them to maximum or minimum
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
        self._mw.curr_block_del_PushButton.clicked.connect(self.block_editor_delete_clicked)

        # connect the signals for the block organizer:
        self._mw.organizer_add_last_PushButton.clicked.connect(self.block_organizer_add_row_after_last)
        self._mw.organizer_del_last_PushButton.clicked.connect(self.block_organizer_delete_row_last)
        self._mw.organizer_add_sel_PushButton.clicked.connect(self.block_organizer_add_row_before_selected)
        self._mw.organizer_del_sel_PushButton.clicked.connect(self.block_organizer_delete_row_selected)
        self._mw.organizer_clear_PushButton.clicked.connect(self.block_organizer_clear_table)

        self._mw.curr_ensemble_load_PushButton.clicked.connect(self.load_pulse_block_ensemble)
        self._mw.curr_ensemble_del_PushButton.clicked.connect(self.block_organizer_delete_clicked)

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

        pulser_constr = self.get_hardware_constraints()
        # Here just the number of analog or digital channels is needed:
        channel_config = pulser_constr['channel_config']['conf1']
        self._set_block_editor_columns(num_a_ch=channel_config.count('a_ch'),
                                       num_d_ch=channel_config.count('d_ch'))

        # create all the needed control widgets on the fly and connect their a
        # actions to each other:
        self._create_control_for_prepared_methods()
        self._create_pulser_on_off_buttons()
        self._create_radiobuttons_for_channels()
        self._create_pushbutton_clear_device()

        # filename tag input widget
        self._create_save_tag_input()

        self.keep_former_block_settings()

        # create a list with all possible combinations of independant channels,
        # so that one can choose, which scenerio to take and to which channel
        # to upload which created file:
        maximum_ch_variation = range(1,pulser_constr['independent_ch']+1)
        channels_combi = []
        for entry in range(0, len(maximum_ch_variation)+1):
            for subset in itertools.combinations(maximum_ch_variation, entry):
                if subset != ():
                    channels_combi.append(str(list(subset)))

        # A dictionary containing the mathematical function names to choose
        # from in the block editor with corresponding lists of needed
        # parameters like phase, frequency etc. This should be provided by the
        #  "math logic".

        self.set_cfg_param_pbe()
        self._set_organizer_columns()

        # connect all the needed signal to methods:
        self._mw.curr_block_generate_PushButton.clicked.connect(self.generate_pulse_block)
        self._mw.curr_ensemble_generate_PushButton.clicked.connect(self.generate_pulse_block_ensemble)
        self._mw.block_editor_TableWidget.itemChanged.connect(self._update_current_pulse_block)
        self._mw.laserchannel_ComboBox.currentIndexChanged.connect(self._update_current_pulse_block)
        self._mw.block_organizer_TableWidget.itemChanged.connect(self._update_current_pulse_block_ensemble)
        self._mw.pulser_on_PushButton.clicked.connect(self.pulser_on_clicked)
        self._mw.pulser_off_PushButton.clicked.connect(self.pulser_off_clicked)
        self._mw.clear_device_PushButton.clicked.connect(self.clear_device_clicked)

        # initialize the lists of available blocks, ensembles and sequences
        self.update_block_list()
        self.update_ensemble_list()
        self.update_sequence_list()

        # Modified by me
        # self._mw.init_block_TableWidget.viewport().setAttribute(QtCore.Qt.WA_Hover)
        # self._mw.repeat_block_TableWidget.viewport().setAttribute(QtCore.Qt.WA_Hover)

    def _deactivate_pulse_generator_ui(self, e):
        """ Disconnects the configuration for 'Pulse Generator Tab.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        #FIXME: implement a proper deactivation for that.
        self._pm.close()

    def _create_save_tag_input(self):
        """ Add save file tag input box. """
        self._mw.save_tag_LineEdit = QtGui.QLineEdit()
        self._mw.save_tag_LineEdit.setMaximumWidth(200)
        self._mw.save_ToolBar.addWidget(self._mw.save_tag_LineEdit)

    def _create_pulser_on_off_buttons(self):
        """ Create Buttons for Pulser on and Pulser Off and add to toolbar. """

        self._mw.pulser_on_PushButton =  QtGui.QPushButton(self._mw)
        self._mw.pulser_on_PushButton.setText('Pulser On')
        self._mw.pulser_on_PushButton.setToolTip('Switch on the device.\n'
                                                 'The channels, which will be activated\n'
                                                 'are displayed on the right.')
        self._mw.control_ToolBar.addWidget(self._mw.pulser_on_PushButton)


        self._mw.pulser_off_PushButton = QtGui.QPushButton(self._mw)
        self._mw.pulser_off_PushButton.setText('Pulser Off')
        self._mw.pulser_off_PushButton.setToolTip('Switch off the device.\n'
                                                  'The channels, which will be deactivated\n'
                                                  'are displayed on the right.')
        self._mw.control_ToolBar.addWidget(self._mw.pulser_off_PushButton)

    def _create_radiobuttons_for_channels(self):
        """ To display, which channels are on and active, create a row of
            Radiobuttons in a dedicated region in the gui.

        Procedure of construction:
            Create a raw QWidget and use this as a container for RadioButtons
            Widgets. Add the RadioButtonWidgets to the Layout of the raw
            QWidget.
            Moreover, attach them to the main window object to be able to ask
            their status if needed.
            Equip additionaly each radiobutton with a Tooltip as the channel
            name, chosen in the pulser constraints.
        """

        # Create container with layout
        self._mw.radiobutton_container =  QtGui.QWidget(self._mw.control_ToolBar)
        self._mw.radiobutton_container_layout = QtGui.QHBoxLayout()
        self._mw.radiobutton_container.setLayout(self._mw.radiobutton_container_layout)

        pulser_const = self.get_hardware_constraints()

        # delete in the cleanest way at first all Widgets which are within the
        # RadioButtons_HorizontalLayout by dereferencing them:
        # for i in reversed(range(self._mw.RadioButtons_HorizontalLayout.count())):
        #     self._mw.RadioButtons_HorizontalLayout.itemAt(i).widget().setParent(None)

        for channel in pulser_const['available_ch']:

            radiobutton_obj_name = str(channel) + '_RadioButton'

            # Use a customized version of radiobuttons:
            radiobutton = CustomQRadioButton(self._mw.control_ToolBar)
            radiobutton.setEnabled(False)
            radiobutton.setText('')
            radiobutton.setAutoExclusive(False)
            radiobutton.setObjectName(radiobutton_obj_name)
            radiobutton.setToolTip(str(channel))
            radiobutton.setReadOnly(True)
            self._mw.radiobutton_container_layout.addWidget(radiobutton)
            # attach to the main object the radiobutton:
            setattr(self._mw, radiobutton_obj_name, radiobutton)

        # add finally the container to the ToolBar:
        self._mw.control_ToolBar.addWidget(self._mw.radiobutton_container)

    def _create_pushbutton_clear_device(self):
        """ Create the  Clear Button to clear the device. """

        self._mw.clear_device_PushButton = QtGui.QPushButton(self._mw)
        self._mw.clear_device_PushButton.setText('Clear Pulser')
        self._mw.clear_device_PushButton.setToolTip('Clear the Pulser Device Memory\n'
                                                    'from all loaded files.')
        self._mw.control_ToolBar.addWidget(self._mw.clear_device_PushButton)


    def get_radiobutton_obj(self, channelname):
        """ Retrieve the reference to the Radiobutton with the passed name.

        @param str channelname: A name which must be present in the hardware
                                constraints under the category 'available_ch'.

        @return: object: Reference to a QtGui.QRadioButton object
        """
        radiobutton_obj_name =  str(channelname) + '_RadioButton'
        radiobutton = getattr(self._mw, radiobutton_obj_name)
        return radiobutton

    def _set_sample_rate_constraints(self):
        """ Retrieve from the Hardware again the constraints dict and set again
            the sample rate constraits.
        """

        pulser_constr = self.get_hardware_constraints()
        sample_min = pulser_constr['sample_rate']['min']
        sample_max = pulser_constr['sample_rate']['max']
        sample_step = pulser_constr['sample_rate']['step']

        #FIXME: that should be in SI units! ...that will be changed soon
        self._mw.sample_freq_DSpinBox.setMinimum(sample_min/1e6)
        self._mw.sample_freq_DSpinBox.setMaximum(sample_max/1e6)
        self._mw.sample_freq_DSpinBox.setSingleStep(sample_step/1e6)
        self._mw.sample_freq_DSpinBox.setDecimals( (np.log10(sample_step/1e6)* -1) )
        self.set_sample_rate(sample_max)

    def pulser_on_clicked(self):
        """ Switch on the pulser output. """

        # provide the logic, which buttons to switch on:
        pulser_const = self.get_hardware_constraints()
        curr_map = self._bs.ch_activation_pattern_ComboBox.currentText()

        a_ch = {}   # create something like  a_ch = {1:True, 2:True} to switch
        d_ch = {}   # the various channel separetely on.
        for ch_name in pulser_const['activation_map'][curr_map]:
            ch_type = list(pulser_const['available_ch'][ch_name])[0]
            if 'a_ch' == ch_type:
                a_ch[pulser_const['available_ch'][ch_name][ch_type]] = True
            if 'd_ch' == ch_type:
                d_ch[pulser_const['available_ch'][ch_name][ch_type]] = True
            radiobutton = self.get_radiobutton_obj(ch_name)
            radiobutton.setChecked(True)

        self._seq_gen_logic.pulser_on(a_ch, d_ch)

    def pulser_off_clicked(self):
        """ Switch off the pulser output. """

        pulser_const = self.get_hardware_constraints()
        curr_map = self._bs.ch_activation_pattern_ComboBox.currentText()

        a_ch = {}   # create something like  a_ch = {1:True, 2:True} to switch
        d_ch = {}   # the various channel separetely on.
        for ch_name in pulser_const['activation_map'][curr_map]:
            ch_type = list(pulser_const['available_ch'][ch_name])[0]
            if 'a_ch' == ch_type:
                a_ch[pulser_const['available_ch'][ch_name][ch_type]] = False
            if 'd_ch' == ch_type:
                d_ch[pulser_const['available_ch'][ch_name][ch_type]] = False
            radiobutton = self.get_radiobutton_obj(ch_name)
            radiobutton.setChecked(False)

        self._seq_gen_logic.pulser_off(a_ch, d_ch)

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
        """Updates the current sample rate in the logic """
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

        # FIXME: Implement a proper choosing of the channels to upload to.
        # Right now the channels are invoked from the asset filenames

        self._seq_gen_logic.sample_ensemble(ensemble_name, True, False)
        return

    def upload_to_device_clicked(self):
        """
        This method is called when the user clicks on "upload to device"
        """

        # Get the asset name to be uploaded from the ComboBox
        asset_name = self._mw.upload_ensemble_ComboBox.currentText()

        # Upload the asset via logic module
        self._seq_gen_logic.upload_asset(asset_name)
        return

    def load_into_channel_clicked(self):
        """
        This method is called when the user clicks on "load to channel"
        """
        # Get the asset name to be uploaded from the ComboBox
        asset_name = self._mw.upload_ensemble_ComboBox.currentText()

        # Check out on which channel it should be uploaded:
        # FIXME: Implement a proper GUI element (upload center) to manually assign assets to channels
        # Right now the default is chosen to invoke channel assignment from the Ensemble/Sequence object
        load_dict = {}

        channels = self._mw.upload_independ_ch_combi_ComboBox.currentText()
        # evaluate to have a proper list:
        channels = eval(channels)
        for entry in channels:
            load_dict[entry] = asset_name

        # Load asset into channles via logic module
        self._seq_gen_logic.load_asset(asset_name, load_dict)
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
        # Set active index of the ComboBoxes to the currently shown/last created ensemble
        if self._seq_gen_logic.current_ensemble is not None:
            # get last generated and currently shown ensemble name from logic
            current_ensemble_name = self._seq_gen_logic.current_ensemble.name
            # identify the corresponding index within the ComboBox
            index_to_set = self._mw.upload_ensemble_ComboBox.findText(current_ensemble_name)
            # Set index inside the ComboBox
            self._mw.upload_ensemble_ComboBox.setCurrentIndex(index_to_set)
            self._mw.saved_ensembles_ComboBox.setCurrentIndex(index_to_set)
        else:
            # set the current ensemble in the logic and all ComboBoxes to the currently
            # shown ensemble in the upload_ensemble_ComboBox.
            current_ensemble_name = self._mw.upload_ensemble_ComboBox.currentText()
            index_to_set = self._mw.saved_ensembles_ComboBox.findText(current_ensemble_name)
            self._mw.saved_ensembles_ComboBox.setCurrentIndex(index_to_set)
            self.load_pulse_block_ensemble()
        return

    def update_sequence_list(self):
        """
        This method is called upon signal_sequence_list_updated emit of the sequence_generator_logic.
        Updates all ComboBoxes showing generated sequences.
        """
        # updated list of all generated sequences
        new_list = self._seq_gen_logic.saved_sequences
        return


    def clear_device_clicked(self):
        """ Delete all loaded files in the device's current memory. """
        self._seq_gen_logic.clear_pulser()

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

        # check whether the value has to be normalized to SI values.
        if hasattr(tab.itemDelegateForColumn(column),'get_unit_prefix'):
            unit_prefix = tab.itemDelegateForColumn(column).get_unit_prefix()
            # access the method defined in base for unit prefix:
            return data*self.get_unit_prefix_dict()[unit_prefix]

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

        tab = self._mw.block_editor_TableWidget
        model = tab.model()
        access = tab.itemDelegateForColumn(column).model_data_access
        data = tab.model().index(row, column).data(access)

        if type(data) == type(value):

            # check whether the SI value has to be adjusted according to the
            # desired unit prefix of the current viewbox:
            if hasattr(tab.itemDelegateForColumn(column),'get_unit_prefix'):
                unit_prefix = tab.itemDelegateForColumn(column).get_unit_prefix()

                # access the method defined in base for unit prefix:
                value = value/self.get_unit_prefix_dict()[unit_prefix]
            model.setData(model.index(row,column), value, access)
        else:
            self.logMsg('The cell ({0},{1}) in block table could not be '
                        'assigned with the value="{2}", since the type "{3}" '
                        'of the cell from the delegated type differs from '
                        '"{4}" of the value!\nPrevious value will be '
                        'kept.'.format(row, column, value, type(data),
                                       type(value) ) , msgType='warning')


    def _update_current_pulse_block(self):
        """ Update the current Pulse Block Info in the display. """

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
            curr_bin_length = int(np.round(curr_length*(self.get_sample_rate())))
            length = length + curr_length
            bin_length = bin_length + curr_bin_length

            laser_val =self.get_element_in_block_table(row_ind, laser_column)
            if (laser_val=='DC') or (laser_val==2):
                num_laser_ch = num_laser_ch +1

        #FIXME: The display unit will be later on set in the settings, so that
        #       one can choose which units are suiting the best. For now on it
        #       will be fixed to microns.

        self._mw.curr_block_length_DSpinBox.setValue(length*1e6) # in microns
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

                num_laser_pulses = num_laser_pulses + block_obj.number_of_lasers * (reps+1)


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

    def load_pulse_block(self, block_name=None):
        """ Loads the current selected Pulse_Block object from the logic into
            the editor or a specified Pulse_Block with name block_name.

        @param str block_name: optional, name of the Pulse_Block object, which
                               should be loaded in the GUI Block Organizer. If
                               no name passed, the current Pulse_Block from the
                               Logic is taken to be loaded.

        Unfortuanetly this method needs to know how Pulse_Block objects are
        looking like and cannot be that general.
        """

        # NOTE: This method will be connected to the CLICK event of a
        #       QPushButton, which passes as an optional argument a a bool value
        #       depending on the checked state of the QPushButton. Therefore
        #       the passed boolean value has to be handled in addition!

        if (block_name is not None) and (type(block_name) is not bool):
            current_block_name = block_name
        else:
            current_block_name = self._mw.saved_blocks_ComboBox.currentText()

        block = self._seq_gen_logic.get_block(current_block_name,
                                              set_as_current_block=True)

        # of no object was found then block has reference to None
        if block is None:
            return

        self.block_editor_clear_table() # clear table
        rows = len(block.element_list)  # get amout of rows needed for display

        # configuration dict from the logic:
        block_config_dict = self.get_cfg_param_pbe()

        self.block_editor_add_row_after_last(rows-1) # since one is already present

        for row_index, pulse_block_element in enumerate(block.element_list):

            # set at first all digital channels:
            for digital_ch in range(pulse_block_element.digital_channels):
                column = block_config_dict['digital_'+str(digital_ch)]
                value = pulse_block_element.marker_active[digital_ch]
                if value:
                    value=2
                else:
                    value=0
                self.set_element_in_block_table(row_index,column, value)

            # now set all parameters for the analog channels:
            for analog_ch in range(pulse_block_element.analog_channels):

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
            value = pulse_block_element.use_as_tau
            # the ckeckbox has a special input value, it is 0, 1 or 2. (tri-state)
            if value:
                value=2
            else:
                value=0
            self.set_element_in_block_table(row_index, column, value)

            # and set the init_length_bins:
            column = block_config_dict['length']
            value = pulse_block_element.init_length_bins / (self.get_sample_rate() )
            # the setter method will handle the proper unit for that value!
            # Just make sure to pass to the function the value in SI units!
            self.set_element_in_block_table(row_index, column, value)

            # and set the increment parameter
            column = block_config_dict['increment']
            value = pulse_block_element.increment_bins / (self.get_sample_rate() )
            # the setter method will handle the proper unit for that value!
            # Just make sure to pass to the function the value in SI units!
            self.set_element_in_block_table(row_index, column, value)

        self._mw.curr_block_name_LineEdit.setText(current_block_name)


    def load_pulse_block_ensemble(self, ensemble_name=None):
        """ Loads the current selected Pulse_Block_Ensemble object from the
            logic into the editor or a specified object with name ensemble_name.

        @param str ensemble_name: optional, name of the Pulse_Block_Element
                                  object, which should be loaded in the GUI
                                  Block Organizer. If no name passed, the
                                  current Pulse_Block_Ensemble from the Logic is
                                  taken to be loaded.

        Unfortuanetly this method needs to know how Pulse_Block_Ensemble objects
        are looking like and cannot be that general.
        """

        # NOTE: This method will be connected to the CLICK event of a
        #       QPushButton, which passes as an optional argument as a bool
        #       value depending on the checked state of the QPushButton. The
        #       passed boolean value has to be handled in addition!

        if (ensemble_name is not None) and (type(ensemble_name) is not bool):
            current_ensemble_name = ensemble_name
        else:
            current_ensemble_name = self._mw.saved_ensembles_ComboBox.currentText()

        # get the ensemble object and set as current ensemble
        ensemble = self._seq_gen_logic.get_ensemble(current_ensemble_name,
                                                    set_as_current_ensemble=True)

        # Check whether an ensemble is found, otherwise there will be None:
        if ensemble is None:
            return

        self.block_organizer_clear_table() # clear the block organizer table
        rows = len(ensemble.block_list) # get amout of rows needed for display

        # add as many rows as there are blocks in the ensemble
        # minus 1 because a single row is already present after clear
        self.block_organizer_add_row_after_last(rows-1)

        # This dictionary has the information which column number describes
        # which object, it is a configuration dict between GUI and logic
        organizer_config_dict = self.get_cfg_param_pb()

        # run through all blocks in the block_elements block_list to fill in the
        # row informations
        for row_index, (pulse_block, repetitions) in enumerate(ensemble.block_list):

            column = organizer_config_dict['pulse_block']
            self.set_element_in_organizer_table(row_index, column, pulse_block.name)

            column = organizer_config_dict['repetition']
            self.set_element_in_organizer_table(row_index, column, int(repetitions))

        # set the ensemble name LineEdit to the current ensemble
        self._mw.curr_ensemble_name_LineEdit.setText(current_ensemble_name)


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
        self.initialize_cells_block_editor(start_row=selected_row,
                                           stop_row=selected_row+insert_rows)

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
        self.initialize_cells_block_editor(start_row=number_of_rows,
                                           stop_row=number_of_rows+insert_rows)

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

    def set_element_in_organizer_table(self, row, column, value):
        """ Simplified wrapper function to set the data to a specific cell
            in the block organizer table.

        @param int row: row index
        @param int column: column index

        Note that the order of the arguments in this function (first row index
        and then column index) was taken from the Qt convention.
        A type check will be performed for the passed value argument. If the
        type does not correspond to the delegate, then the value will not be
        changed. You have to ensure that
        """

        tab = self._mw.block_organizer_TableWidget
        model = tab.model()
        access = tab.itemDelegateForColumn(column).model_data_access
        data = tab.model().index(row, column).data(access)

        if type(data) == type(value):
            model.setData(model.index(row,column), value, access)
        else:
            self.logMsg('The cell ({0},{1}) in block organizer table could not be '
                        'assigned with the value="{2}", since the type "{3}" '
                        'of the cell from the delegated type differs from '
                        '"{4}" of the value!\nPrevious value will be '
                        'kept.'.format(row, column, value, type(data),
                                       type(value) ) , msgType='warning')

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
                                                    self._mw.laserchannel_ComboBox.currentText(),
                                                    rotating_frame)


    def insert_parameters(self, column):

        # insert parameter:
        insert_at_col_pos = column
        for column, parameter in enumerate(self.get_add_pbe_param()):

            # add the new properties to the whole column through delegate:
            item_dict = self.get_add_pbe_param()[parameter]

            if 'unit_prefix' in item_dict.keys():
                unit_text = item_dict['unit_prefix'] + item_dict['unit']
            else:
                unit_text = item_dict['unit']

            self._mw.block_editor_TableWidget.insertColumn(insert_at_col_pos+column)
            self._mw.block_editor_TableWidget.setHorizontalHeaderItem(insert_at_col_pos+column, QtGui.QTableWidgetItem())
            self._mw.block_editor_TableWidget.horizontalHeaderItem(insert_at_col_pos+column).setText('{0} ({1})'.format(parameter,unit_text))
            self._mw.block_editor_TableWidget.setColumnWidth(insert_at_col_pos+column, 90)

            # Use only DoubleSpinBox  as delegate:
            if item_dict['unit'] == 'bool':
                delegate = CheckBoxDelegate(self._mw.block_editor_TableWidget, item_dict)
            else:
                delegate = DoubleSpinBoxDelegate(self._mw.block_editor_TableWidget, item_dict)
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

    def set_a_d_ch(self, num_a_ch=None, num_d_ch=None):
        """ Set amount of analog or/and digital channels.

        @param num_a_ch: int, optional, number of analog channels.
        @param num_d_ch: int, optional, number of digital channels.

        This function wraps basically around the function
        _set_block_editor_columns. It is more intuitive to set the number of
        channels then the number of columns.
        If no arguments are passed, the table is simple reinitialized to
        default values.
        """
        self._set_block_editor_columns(num_a_ch=num_a_ch, num_d_ch=num_d_ch,)

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



    def _set_block_editor_columns(self, num_a_ch=None, num_d_ch=None,):
        """ General function which creates the needed columns in Pulse Block
            Editor.

        @param num_a_ch: int, desired numbe of analog channels
        @param num_d_ch: int, desired number of digital channels

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

        self._pulsed_meas_logic.analog = num_a_ch
        self._pulsed_meas_logic.digital = num_d_ch
        self._seq_gen_logic.analog_channels = num_a_ch
        self._seq_gen_logic.digital_channels = num_d_ch

        # Determine the function with the most parameters. Use also that
        # function as a construction plan to create all the needed columns for
        # the parameters.
        (num_max_param, biggest_func) = self._determine_needed_parameters()

        # Erase the delegate from the column, pass a None reference:
        for column in range(self._mw.block_editor_TableWidget.columnCount()):
            self._mw.block_editor_TableWidget.setItemDelegateForColumn(column, None)

        # clear the number of columns:
        self._mw.block_editor_TableWidget.setColumnCount(0)

        # total number of analog and digital channels:
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
                item_dict = {}
                item_dict['init_val'] = QtCore.Qt.Unchecked
                checkDelegate = CheckBoxDelegate(self._mw.block_editor_TableWidget, item_dict)
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

                item_dict = {}
                item_dict['get_list_method'] = self.get_current_function_list

                delegate = ComboBoxDelegate(self._mw.block_editor_TableWidget, item_dict)
                self._mw.block_editor_TableWidget.setItemDelegateForColumn(column+param_pos, delegate)

                # create here all
                for param_pos, parameter in enumerate(self.get_func_config()[biggest_func]):

                    # initial block:

                    item_dict = self.get_func_config()[biggest_func][parameter]


                    unit_text = item_dict['unit_prefix'] + item_dict['unit']


                    self._mw.block_editor_TableWidget.setHorizontalHeaderItem(column+param_pos+1, QtGui.QTableWidgetItem())
                    self._mw.block_editor_TableWidget.horizontalHeaderItem(column+param_pos+1).setText('ACh{0:d}\n{1} ({2})'.format(num_a_ch-num_a_to_create, parameter, unit_text))
                    self._mw.block_editor_TableWidget.setColumnWidth(column+param_pos+1, 100)

                    # add the new properties to the whole column through delegate:

                    # extract the classname from the _param_a_ch list to be able to deligate:
                    delegate = DoubleSpinBoxDelegate(self._mw.block_editor_TableWidget, item_dict)
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
        # set laserchannel_ComboBox to first digital channel as default
        for index, channel in enumerate(channel_map):
            if 'D' in channel:
                self._mw.laserchannel_ComboBox.setCurrentIndex(index)
                break
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
        return self._cfg_param_pb


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

        item_dict = {}
        item_dict['get_list_method'] = self.get_current_pb_list

        comboDelegate = ComboBoxDelegate(self._mw.block_organizer_TableWidget, item_dict)
        self._mw.block_organizer_TableWidget.setItemDelegateForColumn(column, comboDelegate)

        column = 1
        insert_at_col_pos = column
        for column, parameter in enumerate(self.get_add_pb_param()):

            # add the new properties to the whole column through delegate:
            item_dict = self.get_add_pb_param()[parameter]

            unit_text = item_dict['unit_prefix'] + item_dict['unit']

            print('insert_at_col_pos',insert_at_col_pos)
            print('column',column)
            self._mw.block_organizer_TableWidget.insertColumn(insert_at_col_pos+column)
            self._mw.block_organizer_TableWidget.setHorizontalHeaderItem(insert_at_col_pos+column, QtGui.QTableWidgetItem())
            self._mw.block_organizer_TableWidget.horizontalHeaderItem(insert_at_col_pos+column).setText('{0} ({1})'.format(parameter,unit_text))
            self._mw.block_organizer_TableWidget.setColumnWidth(insert_at_col_pos+column, 80)

            # Use only DoubleSpinBox  as delegate:
            if item_dict['unit'] == 'bool':
                delegate = CheckBoxDelegate(self._mw.block_organizer_TableWidget, item_dict)
            elif parameter == 'repetition':
                delegate = SpinBoxDelegate(self._mw.block_organizer_TableWidget, item_dict)
            else:
                delegate = DoubleSpinBoxDelegate(self._mw.block_organizer_TableWidget, item_dict)
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
            2. Then callable methods are created in the GUI like
                _<method_name>_generate()
                which are connected to the generate button and passes all the
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

            # position the buttons in the groupbox:
            pos = len(inspected.parameters)
            gridLayout.addWidget(gen_button, 0, pos, 1, 1)
            gridLayout.addWidget(gen_upload_button, 1, pos, 1, 1)

            horizontalLayout = QtGui.QHBoxLayout(groupBox)

            horizontalLayout.addLayout(gridLayout)

            groupBox.setTitle(method.__name__.replace('_',' '))

            self._pm.verticalLayout.addWidget(groupBox)

    def _create_QLabel(self, parent, label_name):
        """ Helper method for _create_control_for_prepared_methods.

        @param parent: The parent QWidget, which should own that object
        @param str label_name: the display name for the QLabel Widget.

        @return QtGui.QLabel: a predefined label for the GUI.
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
        """ Helper method for _create_control_for_prepared_methods.

        @param parent: The parent QWidget, which should own that object
        @param float default_val: a default value for the QDoubleSpinBox.

        @return QtGui.QDoubleSpinBox: a predefined QDoubleSpinBox for the GUI.
        """

        doublespinBox = QtGui.QDoubleSpinBox(parent)
        doublespinBox.setMaximum(np.inf)
        doublespinBox.setMinimum(-np.inf)

        # set a size for vertivcal an horizontal dimensions
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(doublespinBox.sizePolicy().hasHeightForWidth())

        doublespinBox.setMinimumSize(QtCore.QSize(80, 0))

        return doublespinBox

    def _create_QSpinBox(self, parent, default_val=0):
        """ Helper method for _create_control_for_prepared_methods.

        @param parent: The parent QWidget, which should own that object
        @param int default_val: a default value for the QSpinBox.

        @return QtGui.QSpinBox: a predefined QSpinBox for the GUI.
        """

        spinBox = QtGui.QSpinBox(parent)
        spinBox.setMaximum(2**31 -1)
        spinBox.setMinimum(-2**31 -1)
        return spinBox

    def _create_QCheckBox(self, parent, default_val=False):
        """ Helper method for _create_control_for_prepared_methods.

        @param parent: The parent QWidget, which should own that object
        @param bool default_val: a default value for the QCheckBox.

        @return QtGui.QCheckBox: a predefined QCheckBox for the GUI.
        """

        checkBox = QtGui.QCheckBox(parent)
        checkBox.setChecked(default_val)
        return checkBox

    def _create_QLineEdit(self, parent, default_val=''):
        """ Helper method for _create_control_for_prepared_methods.

        @param parent: The parent QWidget, which should own that object
        @param str default_val: a default value for the QLineEdit.

        @return QtGui.QLineEdit: a predefined QLineEdit for the GUI.
        """

        lineedit = QtGui.QLineEdit(parent)
        lineedit.setText(default_val)

        # set a size for vertivcal an horizontal dimensions
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(lineedit.sizePolicy().hasHeightForWidth())

        lineedit.setMinimumSize(QtCore.QSize(80, 0))

        lineedit.setSizePolicy(sizePolicy)
        return lineedit

    def _create_QPushButton(self, parent, text='Generate'):
        """ Helper method for _create_control_for_prepared_methods.

        @param parent: The parent QWidget, which should own that object
        @param str text: a display text for the QPushButton.

        @return QtGui.QPushButton: a predefined QPushButton for the GUI.
        """

        pushbutton = QtGui.QPushButton(parent)
        pushbutton.setText(text)
        return pushbutton

    def _function_builder_generate(self, func_name, obj_list, ref_logic_gen ):
        """ Create a function/method which is called by the generate button.

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

        # assign now a new name to that function, this name will be used to
        # bound the function as attribute to the main object.
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
            self.sample_ensemble_clicked()
            self.upload_to_device_clicked()

        # assign now a new name to that function, this name will be used to
        # bound the function as attribute to the main object.
        func_dummy_name.__name__ = func_name
        return func_dummy_name



    ###########################################################################
    ###        Methods related to Settings for the 'Analysis' Tab:          ###
    ###########################################################################

    #FIXME: Implement the setting for 'Analysis' tab.

    def _activate_analysis_settings_ui(self, e):
        """ Initialize, connect and configure the Settings of 'Analysis' Tab.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        self._as = AnalysisSettingDialog()
        self._as.accepted.connect(self.update_analysis_settings)
        self._as.rejected.connect(self.keep_former_analysis_settings)
        self._as.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.update_analysis_settings)
        self._as.ana_param_x_axis_name_LineEdit.setText('tau(ns)')
        self._as.ana_param_x_axis_name_LineEdit.editingFinished.connect(self.name_x_axis_changed)
        self._as.ana_param_y_axis_name_LineEdit.setText('Counts')
        self._as.ana_param_y_axis_name_LineEdit.editingFinished.connect(self.name_y_axis_changed)
        pass

    def _deactivate_analysis_settings_ui(self, e):
        """ Disconnects the configuration of the Settings for 'Analysis' Tab.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """

        pass

    def update_analysis_settings(self):
        """ Apply the new settings """
        #FIXME: Implement the behaviour
        pass

    def keep_former_analysis_settings(self):
        """ Keep the old settings """
        #FIXME: Implement the behaviour
        pass

    def show_analysis_settings(self):
        """ Open the Analysis Settings Window. """
        self._as.exec_()

    def name_x_axis_changed(self):
        name=self._as.ana_param_x_axis_name_LineEdit.text()
        self._mw.pulse_analysis_PlotWidget.setLabel('bottom', name)
        #self._mw.pulse_analysis_second_PlotWidget.setLabel('bottom', name)
        return

    def name_y_axis_changed(self):
        name=self._as.ana_param_y_axis_name_LineEdit.text()
        self._mw.pulse_analysis_PlotWidget.setLabel('left', name)
        #self._mw.pulse_analysis_second_PlotWidget.setLabel('bottom', name)
        return

    ###########################################################################
    ###     Methods related to the Tab 'Analysis' in the Pulsed Window:     ###
    ###########################################################################

    def _activate_analysis_ui(self, e):
        """ Initialize, connect and configure the 'Analysis' Tab.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """


        # Configure the main pulse analysis display:
        self.signal_image = pg.PlotDataItem(self._pulsed_meas_logic.signal_plot_x, self._pulsed_meas_logic.signal_plot_y)
        self._mw.pulse_analysis_PlotWidget.addItem(self.signal_image)
        self._mw.pulse_analysis_PlotWidget.setLabel('left', 'Counts')
        self._mw.pulse_analysis_PlotWidget.setLabel('bottom', self._as.ana_param_x_axis_name_LineEdit.text())

        # Configure the fit of the data in the main pulse analysis display:
        self.fit_image = pg.PlotDataItem()
        self._mw.pulse_analysis_PlotWidget.addItem(self.fit_image, pen='r')
        self._mw.pulse_analysis_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        # Configure the errorbars of the data in the main pulse analysis display:
        self.signal_image_error_bars=pg.ErrorBarItem(x=self._pulsed_meas_logic.signal_plot_x,
                                                     y=self._pulsed_meas_logic.signal_plot_y,
                                                     top=self._pulsed_meas_logic.measuring_error_plot_y,
                                                     bottom=self._pulsed_meas_logic.measuring_error_plot_y,pen='b')

        # Configure the fourier transform of the main pulse analysis display:
        self.fft_image = pg.PlotDataItem(self._pulsed_meas_logic.signal_plot_x, self._pulsed_meas_logic.signal_plot_y)
        self._mw.pulse_analysis_second_PlotWidget.addItem(self.fft_image)
        self._mw.pulse_analysis_second_PlotWidget.showGrid(x=True, y=True, alpha=0.8)



        #FIXME: Is currently needed for the errorbars, but there has to be a better solution
        self.errorbars_present=False

        #FIXME: THE DEFAULT VALUES DO NOT NEED TO BE DEFINED HERE!!!
        # Initialize  what is visible and what not
        self._mw.ext_control_mw_freq_Label.setVisible(False)
        self._mw.ext_control_mw_freq_DoubleSpinBox.setVisible(False)
        self._mw.ext_control_mw_power_Label.setVisible(False)
        self._mw.ext_control_mw_power_DoubleSpinBox.setVisible(False)

        self._mw.ana_param_x_axis_start_Label.setVisible(False)
        self._mw.ana_param_x_axis_start_DoubleSpinBox.setVisible(False)
        self._mw.ana_param_x_axis_inc_Label.setVisible(False)
        self._mw.ana_param_x_axis_inc_DoubleSpinBox.setVisible(False)

        # Set the state button as ready button as default setting.

        self._mw.action_continue_pause.setEnabled(False)
        self._mw.action_pull_data.setEnabled(False)

        # pulsed measurement tab
        self._mw.ext_control_mw_freq_DoubleSpinBox.setValue(2870e6)
        self._mw.ext_control_mw_power_DoubleSpinBox.setValue(-30.)
        self._mw.ana_param_fc_num_laser_pulse_SpinBox.setValue(self._pulsed_meas_logic.get_num_of_lasers())
        self._mw.ana_param_x_axis_start_DoubleSpinBox.setValue(1)
        self._mw.ana_param_x_axis_inc_DoubleSpinBox.setValue(1)

        self._mw.time_param_expected_dur_DoubleSpinBox.setValue(0)
        self._mw.time_param_elapsed_time_LineEdit.setText('00:00:00:00')

        self._mw.time_param_elapsed_sweep_SpinBox.setValue(0)
        self._mw.time_param_ana_periode_DoubleSpinBox.setValue(2)
        self._mw.ext_control_optimize_interval_DoubleSpinBox.setValue(500)
        self._mw.ext_control_redo_odmr_DoubleSpinBox.setValue(500)

        # Configuration of the second plot ComboBox

        #FIXME: This should be given by the fast counter
        self._mw.ana_param_fc_bins_ComboBox.addItem('1.0')
        self._mw.ana_param_fc_bins_ComboBox.addItem('2.0')
        self._mw.ana_param_fc_bins_ComboBox.addItem('3.0')
        self._mw.ana_param_fc_bins_ComboBox.addItem('4.0')
        self._mw.ana_param_fc_bins_ComboBox.addItem('5.0')
        self._mw.ana_param_fc_bins_ComboBox.addItem('10.0')

        self._mw.second_plot_ComboBox.addItem('None')
        self._mw.second_plot_ComboBox.addItem('unchanged data')
        self._mw.second_plot_ComboBox.addItem('FFT')
        self._mw.second_plot_ComboBox.addItem('Log(x)')
        self._mw.second_plot_ComboBox.addItem('Log(y)')
        self._mw.second_plot_ComboBox.addItem('Log(x)&Log(y)')

        # Configuration of the fit ComboBox
        self._mw.fit_param_fit_func_ComboBox.addItem('No Fit')
        self._mw.fit_param_fit_func_ComboBox.addItem('Rabi Decay')
        self._mw.fit_param_fit_func_ComboBox.addItem('Lorentian (neg)')
        self._mw.fit_param_fit_func_ComboBox.addItem('Lorentian (pos)')
        self._mw.fit_param_fit_func_ComboBox.addItem('N14')
        self._mw.fit_param_fit_func_ComboBox.addItem('N15')
        self._mw.fit_param_fit_func_ComboBox.addItem('Stretched Exponential')
        self._mw.fit_param_fit_func_ComboBox.addItem('Exponential')
        self._mw.fit_param_fit_func_ComboBox.addItem('XY8')


        # ---------------------------------------------------------------------
        #                         Connect signals
        # ---------------------------------------------------------------------


        self._mw.action_run_stop.triggered.connect(self.run_stop_clicked)
        self._mw.action_continue_pause.triggered.connect(self.continue_pause_clicked)
        self._mw.action_pull_data.triggered.connect(self.pull_data_clicked)
        self._mw.action_save.triggered.connect(self.save_clicked)


        self._pulsed_meas_logic.signal_time_updated.connect(self.refresh_elapsed_time)
        self._pulsed_meas_logic.sigPulseAnalysisUpdated.connect(self.refresh_signal_plot)
        self._pulsed_meas_logic.sigMeasuringErrorUpdated.connect(self.refresh_measuring_error_plot)

        self._mw.action_Settings_Analysis.triggered.connect(self.show_analysis_settings)


        # Connect the CheckBoxes
        # anaylsis tab

        self._mw.ext_control_use_mw_CheckBox.stateChanged.connect(self.show_external_mw_source_checked)
        self._mw.ana_param_x_axis_defined_CheckBox.stateChanged.connect(self.show_tau_editor)


        # Connect InputWidgets to events
        self._mw.ana_param_fc_num_laser_pulse_SpinBox.editingFinished.connect(self.num_of_lasers_changed)
        self._mw.ana_param_x_axis_start_DoubleSpinBox.editingFinished.connect(self.seq_parameters_changed)
        self._mw.ana_param_x_axis_inc_DoubleSpinBox.editingFinished.connect(self.seq_parameters_changed)

        self._mw.time_param_ana_periode_DoubleSpinBox.editingFinished.connect(self.analysis_timing_changed)
        self.analysis_timing_changed()
        self._mw.ana_param_fc_bins_ComboBox.currentIndexChanged.connect(self.analysis_fc_binning_changed)
        self.analysis_fc_binning_changed()
        self._mw.fit_param_PushButton.clicked.connect(self.fit_clicked)
        self._mw.second_plot_ComboBox.currentIndexChanged.connect(self.change_second_plot)
        self.change_second_plot()

    def _deactivate_analysis_ui(self, e):
        """ Disconnects the configuration for 'Analysis' Tab.

       @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """

        self.run_stop_clicked(False)

        # disconnect signals
        # self._pulsed_meas_logic.sigPulseAnalysisUpdated.disconnect()
        # self._mw.ana_param_fc_num_laser_pulse_SpinBox.editingFinished.disconnect()

    def run_stop_clicked(self, isChecked):
        """ Manages what happens if pulsed measurement is started or stopped.

        @param bool enabled: start scan if that is possible
        """

        #Firstly stop any scan that might be in progress
        self._pulsed_meas_logic.stop_pulsed_measurement()

        #Then if enabled. start a new scan.

        # provide the logic, which buttons to switch on:
        pulser_const = self.get_hardware_constraints()
        curr_map = self._bs.ch_activation_pattern_ComboBox.currentText()

        a_ch = {}   # create something like  a_ch = {1:True, 2:True} to switch
        d_ch = {}   # the various channel separetely on.
        for ch_name in pulser_const['activation_map'][curr_map]:
            ch_type = list(pulser_const['available_ch'][ch_name])[0]
            if 'a_ch' == ch_type:
                a_ch[pulser_const['available_ch'][ch_name][ch_type]] = isChecked
            if 'd_ch' == ch_type:
                d_ch[pulser_const['available_ch'][ch_name][ch_type]] = isChecked
            radiobutton = self.get_radiobutton_obj(ch_name)
            radiobutton.setChecked(isChecked)

        self._pulsed_meas_logic.active_analog = a_ch
        self._pulsed_meas_logic.active_digital= d_ch

        if isChecked:
            self._mw.ext_control_mw_freq_DoubleSpinBox.setEnabled(False)
            self._mw.ext_control_mw_power_DoubleSpinBox.setEnabled(False)
            self._mw.ana_param_fc_bins_ComboBox.setEnabled(False)
            self._mw.action_pull_data.setEnabled(True)

            # set number of laser pulses:
            self._pulsed_meas_logic.set_num_of_lasers(self._mw.ana_param_fc_num_laser_pulse_SpinBox.value())

            self._pulsed_meas_logic.aom_delay_s = 0.5e-6
            self._pulsed_meas_logic.laser_length_s = 3e-6

            self._pulsed_meas_logic.configure_fast_counter()
            # FIXME: Not sure if that belongs to here...
            #self._mw.time_param_expected_dur_DoubleSpinBox.setValue(5765.0)
            'FIXME: Not really sure if for two multiplication it is convenient to have an extra function in ulsed_measurment_logic'
            #self.__pulsed_meas_logic.compute_expected_duration(self._seq_gen_logic.current_ensemble.length_bins,self.ana_param_fc_bins_ComboBox.value())
            self._mw.time_param_expected_dur_DoubleSpinBox.setValue(self._seq_gen_logic.current_ensemble.length_bins/self._seq_gen_logic.sample_rate*1e3) #computed expected duration in ms

            self._pulsed_meas_logic.start_pulsed_measurement()
            self._mw.action_continue_pause.setEnabled(True)


            if not self._mw.action_continue_pause.isChecked():
                self._mw.action_continue_pause.toggle()

        else:
            self._pulsed_meas_logic.stop_pulsed_measurement()
            self._mw.ext_control_mw_freq_DoubleSpinBox.setEnabled(True)
            self._mw.ext_control_mw_power_DoubleSpinBox.setEnabled(True)
            self._mw.ana_param_fc_bins_ComboBox.setEnabled(True)
            self._mw.action_pull_data.setEnabled(False)
            self._mw.action_continue_pause.setEnabled(False)


    #ToDo: I think that is not really working yet
    def continue_pause_clicked(self,isChecked):
        """ Continues and pauses the measurement. """

        if isChecked:
            #self._mw.action_continue_pause.toggle()

            self._mw.action_run_stop.setChecked(True)
        else:
            #self._mw.action_continue_pause.toggle

            self._mw.action_run_stop.setChecked(False)



    def pull_data_clicked(self):
        self._pulsed_meas_logic.manually_pull_data()
        return

    def save_clicked(self):
        self.save_plots()


    def fit_clicked(self):
        self._mw.fit_param_results_TextBrowser.clear()

        current_fit_function = self._mw.fit_param_fit_func_ComboBox.currentText()

        fit_x, fit_y, fit_result = self._pulsed_meas_logic.do_fit(current_fit_function)
        self.fit_image.setData(x=fit_x, y=fit_y, pen='r')

        self._mw.fit_param_results_TextBrowser.setPlainText(fit_result)

        return



    def refresh_signal_plot(self):
        ''' This method refreshes the xy-matrix image
        '''
        #### dealing with the error bars
        #FIXME: Does that belong into the logic?
        if self._mw.ana_param_errorbars_CheckBox.isChecked():
            # calculate optimal beam width for the error bars
            beamwidth = 1e99
            for i in range(len(self._pulsed_meas_logic.tau_array)-1):
                width = self._pulsed_meas_logic.tau_array[i+1] - self._pulsed_meas_logic.tau_array[i]
                width = width/3
                if width <= beamwidth:
                    beamwidth = width
            # create ErrorBarItem
            self.signal_image_error_bars.setData(x=self._pulsed_meas_logic.signal_plot_x, y=self._pulsed_meas_logic.signal_plot_y, top=self._pulsed_meas_logic.measuring_error,bottom=self._pulsed_meas_logic.measuring_error,beam=beamwidth)
            if not self.errorbars_present:
                self._mw.pulse_analysis_PlotWidget.addItem(self.signal_image_error_bars)
                self.errorbars_present = True

        else:
            if self.errorbars_present:
                self._mw.pulse_analysis_PlotWidget.removeItem(self.signal_image_error_bars)
                self.errorbars_present = False

            else:
                pass

        # dealing with the actual signal
        self.signal_image.setData(self._pulsed_meas_logic.signal_plot_x, self._pulsed_meas_logic.signal_plot_y)
        self.change_second_plot()



    def refresh_measuring_error_plot(self):

        #print(self._pulsed_meas_logic.measuring_error)

        self.measuring_error_image.setData(self._pulsed_meas_logic.signal_plot_x, self._pulsed_meas_logic.measuring_error*1000)

    def refresh_elapsed_time(self):
        ''' This method refreshes the elapsed time and sweeps of the measurement
        '''
        self._mw.time_param_elapsed_time_LineEdit.setText(self._pulsed_meas_logic.elapsed_time_str)


        #FIXME: That is not a clean way! What if there is no waveform defined,
        #       so that expected duration is actually zero??!! Handle that for
        #       now in checking the parameter for zero, and if so, then using
        #       just 1.0 instead.
        if np.isclose(self._mw.time_param_expected_dur_DoubleSpinBox.value()/1e3,0):
            expected_time = 1.0
        else:
            expected_time = self._mw.time_param_expected_dur_DoubleSpinBox.value()
        self._mw.time_param_elapsed_sweep_SpinBox.setValue(self._pulsed_meas_logic.elapsed_time/(expected_time/1e3))




    def show_external_mw_source_checked(self):
        if not self._mw.ext_control_use_mw_CheckBox.isChecked():

            self._mw.ext_control_mw_freq_Label.setVisible(False)
            self._mw.ext_control_mw_freq_DoubleSpinBox.setVisible(False)
            self._mw.ext_control_mw_power_Label.setVisible(False)
            self._mw.ext_control_mw_power_DoubleSpinBox.setVisible(False)
        else:
            self._mw.ext_control_mw_freq_Label.setVisible(True)
            self._mw.ext_control_mw_freq_DoubleSpinBox.setVisible(True)
            self._mw.ext_control_mw_power_Label.setVisible(True)
            self._mw.ext_control_mw_power_DoubleSpinBox.setVisible(True)


    def show_tau_editor(self):
        if self._mw.ana_param_x_axis_defined_CheckBox.isChecked():
            self._mw.ana_param_x_axis_start_Label.setVisible(True)
            self._mw.ana_param_x_axis_start_DoubleSpinBox.setVisible(True)
            self._mw.ana_param_x_axis_inc_Label.setVisible(True)
            self._mw.ana_param_x_axis_inc_DoubleSpinBox.setVisible(True)
        else:
            self._mw.ana_param_x_axis_start_Label.setVisible(False)
            self._mw.ana_param_x_axis_start_DoubleSpinBox.setVisible(False)
            self._mw.ana_param_x_axis_inc_Label.setVisible(False)
            self._mw.ana_param_x_axis_inc_DoubleSpinBox.setVisible(False)


    def change_second_plot(self):
        if self._mw.second_plot_ComboBox.currentText()=='None':
            self._mw.fourier_transform_GroupBox.setVisible(False)
        else:
            self._mw.fourier_transform_GroupBox.setVisible(True)

            #Here FFT is seperated from the other option. The reason for that is preventing of code doubling
            if self._mw.second_plot_ComboBox.currentText()=='FFT':
                fft_x,fft_y=self._pulsed_meas_logic.compute_fft()
                self.fft_image.setData(fft_x, fft_y)
                self._mw.pulse_analysis_second_PlotWidget.setLogMode(x=False,y=False)
                if self._as.ana_param_second_plot_x_axis_name_LineEdit.text()=='':
                    self._mw.pulse_analysis_second_PlotWidget.setLabel('left', 'FT-Amplitude')
                    self._mw.pulse_analysis_second_PlotWidget.setLabel('bottom', 'frequency [GHz]')
                else:
                    self._mw.pulse_analysis_second_PlotWidget.setLabel('bottom', self._as.ana_param_second_plot_x_axis_name_LineEdit.text())
                    self._mw.pulse_analysis_second_PlotWidget.setLabel('left', self._as.ana_param_second_plot_y_axis_name_LineEdit.text())


            else:
                #FIXME: Is not working when there is a 0 in the values, therefore ignoring the first measurment point
                self.fft_image.setData(self._pulsed_meas_logic.signal_plot_x[1:], self._pulsed_meas_logic.signal_plot_y[1:])

                if self._as.ana_param_second_plot_x_axis_name_LineEdit.text()=='':
                    self._mw.pulse_analysis_second_PlotWidget.setLabel('left', self._as.ana_param_y_axis_name_LineEdit.text())
                    self._mw.pulse_analysis_second_PlotWidget.setLabel('bottom', self._as.ana_param_x_axis_name_LineEdit.text())

                else:
                    self._mw.pulse_analysis_second_PlotWidget.setLabel('bottom', self._as.ana_param_second_plot_x_axis_name_LineEdit.text())
                    self._mw.pulse_analysis_second_PlotWidget.setLabel('left', self._as.ana_param_second_plot_y_axis_name_LineEdit.text())

                if self._mw.second_plot_ComboBox.currentText()=='unchanged data':
                    self._mw.pulse_analysis_second_PlotWidget.setLogMode(x=False,y=False)

                elif self._mw.second_plot_ComboBox.currentText()=='Log(x)':
                    self._mw.pulse_analysis_second_PlotWidget.setLogMode(x=True,y=False)

                elif self._mw.second_plot_ComboBox.currentText()=='Log(y)':
                    self._mw.pulse_analysis_second_PlotWidget.setLogMode(x=False,y=True)

                elif self._mw.second_plot_ComboBox.currentText()=='Log(x)&Log(y)':
                    self._mw.pulse_analysis_second_PlotWidget.setLogMode(x=True,y=True)




    def seq_parameters_changed(self):

        laser_num = self._mw.ana_param_fc_num_laser_pulse_SpinBox.value()
        tau_start = self._mw.ana_param_x_axis_start_DoubleSpinBox.value()
        tau_incr = self._mw.ana_param_x_axis_inc_DoubleSpinBox.value()
        mw_frequency = self._mw.ext_control_mw_freq_DoubleSpinBox.value()
        mw_power = self._mw.ext_control_mw_power_DoubleSpinBox.value()
        #self._mw.lasertoshow_spinBox.setRange(0, laser_num)




        tau_vector = np.arange(tau_start, tau_start + tau_incr*laser_num, tau_incr)
        # self._pulsed_meas_logic.running_sequence_parameters['tau_vector'] = tau_vector

        self._pulsed_meas_logic.microwave_freq = mw_frequency
        self._pulsed_meas_logic.microwave_power = mw_power
        return

    def analysis_timing_changed(self):

        timer_interval = self._mw.time_param_ana_periode_DoubleSpinBox.value()
        self._pulsed_meas_logic.change_timer_interval(timer_interval)


    def analysis_fc_binning_changed(self):

        fc_binning=float(self._mw.ana_param_fc_bins_ComboBox.currentText())
        self._pulsed_meas_logic.change_fc_binning_for_pulsed_analysis(fc_binning)
        return

    #FIXME:
    def check_input_with_samplerate(self):
        pass


    ###########################################################################
    ###   Methods related to Settings for the 'Sequence Generator' Tab:     ###
    ###########################################################################

    #FIXME: Implement the setting for 'Sequence Generator' tab.

    def _activate_sequence_settings_ui(self, e):
        """ Initialize, connect and configure the Settings of the
        'Sequence Generator' Tab.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """

        pass

    def _deactivate_sequence_settings_ui(self, e):
        """ Disconnects the configuration of the Settings for the
        'Sequence Generator' Tab.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """

        pass


    ###########################################################################
    ###         Methods related to the Tab 'Sequence Generator':            ###
    ###########################################################################

    #FIXME: Implement the 'Sequence Generator' tab.

    def _activate_sequence_generator_ui(self, e):
        """ Initialize, connect and configure the 'Sequence Generator' Tab.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        pass

    def _deactivate_sequence_generator_ui(self, e):
        """ Disconnects the configuration for 'Sequence Generator' Tab.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        pass

    ###########################################################################
    ###    Methods related to Settings for the 'Pulse Extraction' Tab:      ###
    ###########################################################################

    #FIXME: Implement the setting for 'Pulse Extraction' tab.

    def _activate_pulse_extraction_settings_ui(self, e):
        """ Initialize, connect and configure the Settings of the
        'Sequence Generator' Tab.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        pass

    def _deactivate_pulse_extraction_settings_ui(self, e):
        """ Disconnects the configuration of the Settings for the
        'Sequence Generator' Tab.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """

        pass


    ###########################################################################
    ###          Methods related to the Tab 'Pulse Extraction':             ###
    ###########################################################################

    #FIXME: Implement the 'Pulse Extraction' tab.

    def _activate_pulse_extraction_ui(self, e):
        """ Initialize, connect and configure the 'Pulse Extraction' Tab.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """

        # Configure all objects for laserpulses_PlotWidget and also itself:

        # The infinite lines:
        self.sig_start_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(QtGui.QColor(255,0,0,255)), movable=True)
        self.sig_start_line.setHoverPen(QtGui.QPen(QtGui.QColor(255,0,255,255)))
        self.sig_end_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(QtGui.QColor(255,0,0,255)), movable=True)
        self.sig_end_line.setHoverPen(QtGui.QPen(QtGui.QColor(255,0,255,255)))
        self.ref_start_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(QtGui.QColor(0,255,0,255)), movable=True)
        self.ref_start_line.setHoverPen(QtGui.QPen(QtGui.QColor(255,0,255,255)))
        self.ref_end_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(QtGui.QColor(0,255,0,255)), movable=True)
        self.ref_end_line.setHoverPen(QtGui.QPen(QtGui.QColor(255,0,255,255)))

        # the actual data:
        self.lasertrace_image = pg.PlotDataItem(self._pulsed_meas_logic.laser_plot_x, self._pulsed_meas_logic.laser_plot_y)

        self._mw.laserpulses_PlotWidget.addItem(self.lasertrace_image)
        self._mw.laserpulses_PlotWidget.addItem(self.sig_start_line)
        self._mw.laserpulses_PlotWidget.addItem(self.sig_end_line)
        self._mw.laserpulses_PlotWidget.addItem(self.ref_start_line)
        self._mw.laserpulses_PlotWidget.addItem(self.ref_end_line)

        self._mw.laserpulses_PlotWidget.setLabel('bottom', 'tau', units='s')
        self._mw.laserpulses_PlotWidget.setLabel('bottom', 'bins')

        # Configure all objects for measuring_error_PlotWidget and also itself:

        self.measuring_error_image = pg.PlotDataItem(self._pulsed_meas_logic.measuring_error_plot_x, self._pulsed_meas_logic.measuring_error_plot_y*1000)
        self._mw.measuring_error_PlotWidget.addItem(self.measuring_error_image)
        self._mw.measuring_error_PlotWidget.setLabel('left', 'measuring error', units='a.u.')
        self._mw.measuring_error_PlotWidget.setLabel('bottom', 'tau', units='ns')


        # prepare the combobox:
        self.num_of_lasers_changed()

        self._mw.extract_param_ana_window_start_SpinBox.setValue(5)
        self._mw.extract_param_ana_window_width_SpinBox.setValue(200)
        self._mw.extract_param_ref_window_start_SpinBox.setValue(500)
        self._mw.extract_param_ref_window_width_SpinBox.setValue(200)

        # Display laser pulses, connect change of viewboxes and change of lines:
        self._mw.extract_param_ana_window_start_SpinBox.valueChanged.connect(self.analysis_window_values_changed)
        self._mw.extract_param_ana_window_width_SpinBox.valueChanged.connect(self.analysis_window_values_changed)
        self._mw.extract_param_ref_window_start_SpinBox.valueChanged.connect(self.analysis_window_values_changed)
        self._mw.extract_param_ref_window_width_SpinBox.valueChanged.connect(self.analysis_window_values_changed)
        self.analysis_window_values_changed()   # run it to apply changes.

        self.sig_start_line.sigPositionChanged.connect(self.analysis_window_sig_line_start_changed)
        self.sig_end_line.sigPositionChanged.connect(self.analysis_window_sig_line_stop_changed)
        self.ref_start_line.sigPositionChanged.connect(self.analysis_window_ref_line_start_changed)
        self.ref_end_line.sigPositionChanged.connect(self.analysis_window_ref_line_stop_changed)

        self._mw.laserpulses_ComboBox.currentIndexChanged.connect(self.refresh_laser_pulses_display)
        self._mw.laserpulses_display_raw_CheckBox.stateChanged.connect(self.refresh_laser_pulses_display)

        self._pulsed_meas_logic.sigSinglePulsesUpdated.connect(self.refresh_laser_pulses_display)
        self._pulsed_meas_logic.sigPulseAnalysisUpdated.connect(self.refresh_laser_pulses_display)


        #FIXME: remove the dependency on the seq parameter changed for this
        #       section!
        self.seq_parameters_changed()


        #self._mw.measuring_error_PlotWidget.showGrid(x=True, y=True, alpha=0.8)


    def _deactivate_pulse_extraction_ui(self, e):
        """ Disconnects the configuration for 'Pulse Extraction' Tab.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        pass

    def num_of_lasers_changed(self):
        """ Handle what happens if number of laser pulses changes. """

        self._mw.laserpulses_ComboBox.blockSignals(True)

        self._mw.laserpulses_ComboBox.clear()
        self._mw.laserpulses_ComboBox.addItem('sum')
        for ii in range(self._mw.ana_param_fc_num_laser_pulse_SpinBox.value()):
            self._mw.laserpulses_ComboBox.addItem(str(1+ii))

        self._mw.laserpulses_ComboBox.blockSignals(True)

    def analysis_window_values_changed(self):
        """ If the boarders or the lines are changed update the other parameters
        """

        sig_start = self._mw.extract_param_ana_window_start_SpinBox.value()
        sig_length = self._mw.extract_param_ana_window_width_SpinBox.value()
        ref_start = self._mw.extract_param_ref_window_start_SpinBox.value()
        ref_length = self._mw.extract_param_ref_window_width_SpinBox.value()

        self.sig_start_line.setValue(sig_start)
        self.sig_end_line.setValue(sig_start+sig_length)

        self.ref_start_line.setValue(ref_start)
        self.ref_end_line.setValue(ref_start+ref_length)

        self._pulsed_meas_logic.signal_start_bin = sig_start
        self._pulsed_meas_logic.signal_width_bin = sig_length
        self._pulsed_meas_logic.norm_start_bin = ref_start
        self._pulsed_meas_logic.norm_width_bin = ref_length

    def analysis_window_sig_line_start_changed(self):
        """ React when the start signal line get moved by the user. """
        sig_start = self.sig_start_line.value()
        self._mw.extract_param_ana_window_start_SpinBox.setValue(sig_start)
        self._pulsed_meas_logic.signal_start_bin = sig_start

    def analysis_window_sig_line_stop_changed(self):
        """ React when the stop signal line get moved by the user. """
        sig_start = self.sig_start_line.value()
        sig_length = self.sig_end_line.value() - sig_start
        self._mw.extract_param_ana_window_width_SpinBox.setValue(sig_length)
        self._pulsed_meas_logic.signal_width_bin = sig_length

    def analysis_window_ref_line_start_changed(self):
        """ React when the reference start line get moved by the user. """
        ref_start = self.ref_start_line.value()
        self._mw.extract_param_ref_window_start_SpinBox.setValue(ref_start)
        self._pulsed_meas_logic.norm_start_bin = ref_start

    def analysis_window_ref_line_stop_changed(self):
        """ React when the reference stop line get moved by the user. """
        ref_start = self.ref_start_line.value()
        ref_length = self.ref_end_line.value()-ref_start
        self._mw.extract_param_ref_window_width_SpinBox.setValue(ref_length)
        self._pulsed_meas_logic.norm_width_bin = ref_length

    def refresh_laser_pulses_display(self):
        """ Refresh the extracted laser pulse display. """


        current_laser = self._mw.laserpulses_ComboBox.currentText()

        if current_laser == 'sum':
            show_laser_num = 0
        else:
            show_laser_num = int(current_laser)

        if self._mw.laserpulses_display_raw_CheckBox.isChecked():
            self._pulsed_meas_logic.raw_laser_pulse = True
        else:
            self._pulsed_meas_logic.raw_laser_pulse = False

        x_data, y_data = self._pulsed_meas_logic.get_laserpulse(show_laser_num)

        self.lasertrace_image.setData(x=x_data, y=y_data)

    def save_plots(self):
        """ Save plot from analysis graph as a picture. """
        timestamp = datetime.datetime.now()
        filetag = self._mw.save_tag_LineEdit.text()
        filepath = self._save_logic.get_path_for_module(module_name='PulsedMeasurement')
        if len(filetag) > 0:
            filename = os.path.join(filepath, '{}_{}_pulsed'.format(timestamp.strftime('%Y%m%d-%H%M-%S'), filetag))
        else:
            filename = os.path.join(filepath, '{}_pulsed'.format(timestamp.strftime('%Y%m%d-%H%M-%S')))

        # print(type(self._mw.second_plot_ComboBox.currentText()), self._mw.second_plot_ComboBox.currentText())
        # pulse plot
        exporter = pg.exporters.SVGExporter(self._mw.pulse_analysis_PlotWidget.plotItem.scene())
        exporter.export(filename+'.svg')

        # auxiliary plot
        if 'None' not in self._mw.second_plot_ComboBox.currentText():
            exporter_aux = pg.exporters.SVGExporter(self._mw.pulse_analysis_second_PlotWidget.plotItem.scene())
            exporter_aux.export(filename + '_aux' + '.svg')

        self._pulsed_meas_logic._save_data(filetag, timestamp)


