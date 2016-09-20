# -*- coding: utf-8 -*-

from qtpy import QtGui
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic
import numpy as np
import os
from collections import OrderedDict
import pyqtgraph as pg
import re
import inspect
import datetime

from logic.pulse_objects import Pulse_Block_Element
from logic.pulse_objects import Pulse_Block
from logic.pulse_objects import Pulse_Block_Ensemble
from logic.pulse_objects import Pulse_Sequence

from .spinbox_delegate import SpinBoxDelegate
from .doublespinbox_delegate import DoubleSpinBoxDelegate
from .combobox_delegate import ComboBoxDelegate
from .checkbox_delegate import CheckBoxDelegate

from core.util.mutex import Mutex
from core.util import units

class PulseEditorWidget(QtWidgets.QWidget):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pulse_editor.ui')
        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)


class BlockSettingsDialog(QtWidgets.QDialog):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pulsed_main_gui_settings_block_gen.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)


class PredefinedMethodsDialog(QtWidgets.QDialog):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_predefined_methods.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)


class PredefinedMethodsConfigDialog(QtWidgets.QDialog):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui-predefined_methods_config.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)


class PulseEditor:
    def __init__(self, sequence_gen_logic, pulse_meas_logic):
        self._pe = PulseEditorWidget()
        self._pulsed_meas_logic = pulse_meas_logic
        self._seq_gen_logic = sequence_gen_logic
        self._activate_pulse_generator_settings_ui()
        self._activate_pulse_generator_ui()

    def _activate_pulse_generator_settings_ui(self):
        """ Initialize, connect and configure the Settings for the
            'Pulse Generator' Tab.
        """

        self._bs = BlockSettingsDialog() # initialize the block settings
        self._bs.accepted.connect(self.apply_block_settings)
        self._bs.rejected.connect(self.keep_former_block_settings)
        self._bs.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.apply_block_settings)

        #self._bs.use_interleave_CheckBox.setChecked(self._pulsed_meas_logic.get_interleave())
        self._bs.use_interleave_CheckBox.stateChanged.connect(self._interleave_changed)

        # create the Predefined methods Dialog
        self._pm = PredefinedMethodsDialog()
        self._predefined_methods_list = []  # here are all the names saved of
                                            # the created predefined methods.

        # create a config for the predefined methods:
        self._pm_cfg = PredefinedMethodsConfigDialog()

        # Add in the settings menu within the groupbox widget all the available
        # math_functions, based on the list from the Logic. Right now, the GUI
        # objects are inserted the 'hard' way, like it is done in the
        # Qt-Designer.

        # FIXME: Make a nicer way of displaying the available functions, maybe
        #        with a Table!

        _encoding = QtWidgets.QApplication.UnicodeUTF8
        objectname = self._bs.objectName()
        for index, func_name in enumerate(self.get_func_config_list()):

            name_label = 'func_'+ str(index)
            setattr(self._bs, name_label, QtWidgets.QLabel(self._bs.groupBox))
            label = getattr(self._bs, name_label)
            label.setObjectName(name_label)
            self._bs.gridLayout_3.addWidget(label, index, 0, 1, 1)
            label.setText(QtWidgets.QApplication.translate(objectname, func_name, None, _encoding))

            name_checkbox = 'checkbox_'+ str(index)
            setattr(self._bs, name_checkbox, QtWidgets.QCheckBox(self._bs.groupBox))
            checkbox = getattr(self._bs, name_checkbox)
            checkbox.setObjectName(name_checkbox)
            self._bs.gridLayout_3.addWidget(checkbox, index, 1, 1, 1)
            checkbox.setText(QtWidgets.QApplication.translate(objectname, '', None, _encoding))

        # make the first 4 Functions as default.
        # FIXME: the default functions, must be passed as a config

        for index in range(4):
            name_checkbox = 'checkbox_'+ str(index)
            checkbox = getattr(self._bs, name_checkbox)
            checkbox.setCheckState(QtCore.Qt.Checked)

    def _deactivate_pulse_generator_settings_ui(self):
        """ Disconnects the configuration of the Settings for the
            'Pulse Generator' Tab.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        self._bs.accepted.disconnect()
        self._bs.rejected.disconnect()
        self._bs.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.disconnect()
        self._bs.close()

    def _interleave_changed(self, state):
        """ React on a Interleave state change.

        @param int state: 0 for False and 1 or 2 for True.
        """
        self._seq_gen_logic.set_interleave(bool(state))

    def show_block_settings(self):
        """ Opens the block settings menue. """
        self._bs.exec_()

    def show_predefined_methods(self):
        """ Opens the predefined methods Window."""
        self._pm.show()
        self._pm.raise_()

    def show_predefined_methods_config(self):
        """ Opens the Window for the config of predefined methods."""
        self._pm_cfg.show()
        self._pm_cfg.raise_()

    def keep_former_predefined_methods(self):

        for method_name in self._predefined_methods_list:
            groupbox = self._get_ref_groupbox_predefined_methods(method_name)
            checkbox = self._get_ref_checkbox_predefined_methods_config(method_name)

            checkbox.setChecked(groupbox.isVisible())

    def update_predefined_methods(self):

        for method_name in self._predefined_methods_list:
            groupbox = self._get_ref_groupbox_predefined_methods(method_name)
            checkbox = self._get_ref_checkbox_predefined_methods_config(method_name)

            groupbox.setVisible(checkbox.isChecked())


    def apply_block_settings(self):
        """ Write new block settings from the gui to the file. """
        if self._bs.use_saupload_CheckBox.isChecked():
            self._set_visibility_saupload_button_pulse_gen(state=True)
        else:
            self._set_visibility_saupload_button_pulse_gen(state=False)


    def keep_former_block_settings(self):
        """ Keep the old block settings and restores them in the gui. """
        pass

    def get_current_function_list(self):
        """ Retrieve the functions, which are chosen by the user.

        @return: list[] with strings of the used functions. Names are based on
                 the passed func_config dict from the logic. Depending on the
                 settings, a current function list is generated.
        """
        current_functions = []

        for index, func_name in enumerate(self.get_func_config_list()):
            name_checkbox = 'checkbox_'+ str(index)
            checkbox = getattr(self._bs, name_checkbox)
            if checkbox.isChecked():
                name_label = 'func_'+ str(index)
                func = getattr(self._bs, name_label)
                current_functions.append(func.text())

        return current_functions

    def _activate_pulse_generator_ui(self):
        """ Initialize, connect and configure the 'Pulse Generator' Tab.
        """
        # connect the signal for a change of the generator parameters
        self._pe.gen_sample_freq_DSpinBox.editingFinished.connect(
            self.generator_sample_rate_changed)
        self._pe.gen_laserchannel_ComboBox.currentIndexChanged.connect(
            self.generator_laser_channel_changed)
        self._pe.gen_activation_config_ComboBox.currentIndexChanged.connect(
            self.generator_activation_config_changed)

        # connect signal for file upload and loading of pulser device
        #self.sigSampleEnsemble.connect(self._seq_gen_logic.sample_pulse_block_ensemble)
        #self.sigUploadToDevice.connect(self._pulsed_meas_logic.upload_asset)
        #self.sigLoadToChannel.connect(self._pulsed_meas_logic.load_asset)

        # set them to maximum or minimum
        self._pe.curr_block_bins_SpinBox.setMaximum(2**31 -1)
        self._pe.curr_block_laserpulses_SpinBox.setMaximum(2**31 -1)
        self._pe.curr_ensemble_bins_SpinBox.setMaximum(2**31 -1)
        self._pe.curr_ensemble_length_DSpinBox.setMaximum(np.inf)

        # connect the signals for the block editor:
        self._pe.block_add_last_PushButton.clicked.connect(self.block_editor_add_row_after_last)
        self._pe.block_del_last_PushButton.clicked.connect(self.block_editor_delete_row_last)
        self._pe.block_add_sel_PushButton.clicked.connect(self.block_editor_add_row_before_selected)
        self._pe.block_del_sel_PushButton.clicked.connect(self.block_editor_delete_row_selected)
        self._pe.block_clear_PushButton.clicked.connect(self.block_editor_clear_table)

        self._pe.curr_block_load_PushButton.clicked.connect(self.load_pulse_block_clicked)
        self._pe.curr_block_del_PushButton.clicked.connect(self.delete_pulse_block_clicked)

        # connect the signals for the block organizer:
        self._pe.organizer_add_last_PushButton.clicked.connect(self.block_organizer_add_row_after_last)
        self._pe.organizer_del_last_PushButton.clicked.connect(self.block_organizer_delete_row_last)
        self._pe.organizer_add_sel_PushButton.clicked.connect(self.block_organizer_add_row_before_selected)
        self._pe.organizer_del_sel_PushButton.clicked.connect(self.block_organizer_delete_row_selected)
        self._pe.organizer_clear_PushButton.clicked.connect(self.block_organizer_clear_table)

        self._pe.curr_ensemble_load_PushButton.clicked.connect(self.load_pulse_block_ensemble_clicked)
        self._pe.curr_ensemble_del_PushButton.clicked.connect(self.delete_pulse_block_ensemble_clicked)

        # connect the signals for the "Upload on device" section
        #self._pe.sample_ensemble_PushButton.clicked.connect(self.sample_ensemble_clicked)
        #self._pe.upload_to_device_PushButton.clicked.connect(self.upload_to_device_clicked)
        #self._pe.load_channel_PushButton.clicked.connect(self.load_into_channel_clicked)

        # connect the menue to the actions:
        #self._pe.action_Settings_Block_Generation.triggered.connect(self.show_block_settings)
        #self._pe.actionOpen_Predefined_Methods.triggered.connect(self.show_predefined_methods)
        #self._pe.actionConfigure_Predefined_Methods.triggered.connect(self.show_predefined_methods_config)

        # emit a trigger event when for all mouse click and keyboard click events:
        self._pe.block_editor_TableWidget.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)
        self._pe.block_organizer_TableWidget.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)
        # self._pe.seq_editor_TableWidget.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)

        # connect update signals of the sequence_generator_logic
        #self._seq_gen_logic.signal_block_list_updated.connect(self.update_block_list)
        #self._seq_gen_logic.signal_ensemble_list_updated.connect(self.update_ensemble_list)
        #self._seq_gen_logic.sigSampleEnsembleComplete.connect(self.sample_ensemble_finished)

        # connect update signals of the pulsed_measurement_logic
        #self._pulsed_meas_logic.sigUploadAssetComplete.connect(self.upload_to_device_finished)
        #self._pulsed_meas_logic.sigLoadAssetComplete.connect(self.load_into_channel_finished)

        # Definition of this parameter. See fore more explanation in file
        # sampling_functions.py
        length_def = {'unit': 's', 'init_val': 0.0, 'min': 0.0, 'max': np.inf,
                      'view_stepsize': 1e-9, 'dec': 8, 'unit_prefix': 'n', 'type': float}
        rep_def = {'unit': '#', 'init_val': 0, 'min': 0, 'max': (2 ** 31 - 1),
                   'view_stepsize': 1, 'dec': 0, 'unit_prefix': '', 'type': int}
        bool_def = {'unit': 'bool', 'init_val': 0, 'min': 0, 'max': 1,
                    'view_stepsize': 1, 'dec': 0, 'unit_prefix': '', 'type': bool}
        # make a parameter constraint dict for the additional parameters of the
        # Pulse_Block_Ensemble objects:
        self._add_pbe_param = OrderedDict()
        self._add_pbe_param['length'] = length_def
        self._add_pbe_param['increment'] = length_def
        self._add_pbe_param['use as tick?'] = bool_def
        # make a parameter constraint dict for the additional parameters of the
        # Pulse_Block objects:
        self._add_pb_param = OrderedDict()
        self._add_pb_param['repetition'] = rep_def

        # create all the needed control widgets on the fly and connect their
        # actions to each other:

        self.keep_former_block_settings()

        self._set_block_editor_columns()
        self._set_organizer_columns()

        # connect all the needed signal to methods:
        self._pe.curr_block_generate_PushButton.clicked.connect(self.generate_pulse_block_clicked)
        self._pe.curr_ensemble_generate_PushButton.clicked.connect(self.generate_pulse_block_ensemble_clicked)
        self._pe.block_editor_TableWidget.itemChanged.connect(self._update_current_pulse_block)

        self._pe.block_organizer_TableWidget.itemChanged.connect(self._update_current_pulse_block_ensemble)

        # the loaded asset will be updated in the GUI:
        #self._pulsed_meas_logic.sigLoadedAssetUpdated.connect(self.update_loaded_asset)

        # connect the actions of the Config for Predefined methods:
        self._pm_cfg.accepted.connect(self.update_predefined_methods)
        self._pm_cfg.rejected.connect(self.keep_former_predefined_methods)
        self._pm_cfg.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.update_predefined_methods)

        # set the chosen predefined method to be visible:
        for predefined_method in self._predefined_methods_list:
            if predefined_method in self._statusVariables:
                checkbox = self._get_ref_checkbox_predefined_methods_config(predefined_method)
                checkbox.setChecked(self._statusVariables[predefined_method])

        self.update_predefined_methods()

        # Apply hardware constraints to input widgets
        self._gen_apply_hardware_constraints()

        # Fill initial values from logic into input widgets
        self._init_generator_values()

        # Modified by me
        # self._pe.init_block_TableWidget.viewport().setAttribute(QtCore.Qt.WA_Hover)
        # self._pe.repeat_block_TableWidget.viewport().setAttribute(QtCore.Qt.WA_Hover)

    def _deactivate_pulse_generator_ui(self):
        """ Disconnects the configuration for 'Pulse Generator Tab.
        """
        #FIXME: implement a proper deactivation for that.
        self._pm.close()
        self._pm_cfg.close()

        # save which predefined method should be visible:
        for predefined_method in self._predefined_methods_list:
            checkbox = self._get_ref_checkbox_predefined_methods_config(predefined_method)
            self._statusVariables[predefined_method] = checkbox.isChecked()

    def _gen_apply_hardware_constraints(self):
        """
        Retrieve the constraints from pulser hardware and apply these constraints to the pulse
        generator GUI elements.
        """
        pulser_constr = self._pulsed_meas_logic.get_pulser_constraints()
        sample_min = pulser_constr['sample_rate']['min'] / 1e6
        sample_max = pulser_constr['sample_rate']['max'] / 1e6
        sample_step = pulser_constr['sample_rate']['step'] / 1e6

        self._pe.gen_sample_freq_DSpinBox.setMinimum(sample_min)
        self._pe.gen_sample_freq_DSpinBox.setMaximum(sample_max)
        self._pe.gen_sample_freq_DSpinBox.setSingleStep(sample_step)
        self._pe.gen_sample_freq_DSpinBox.setDecimals( (np.log10(sample_step)* -1) )

        # configure the sequence generator logic to use the hardware compatible file formats
        self._seq_gen_logic.waveform_format = pulser_constr['waveform_format']
        self._seq_gen_logic.sequence_format = pulser_constr['sequence_format']

    def _init_generator_values(self):
        """
        This method will retrieve the initial values from the sequence_generator_logic and
        initializes all input GUI elements with these values.
        """
        # get init values from logic
        sample_rate = self._seq_gen_logic.sample_rate
        laser_channel = self._seq_gen_logic.laser_channel
        activation_config = self._seq_gen_logic.activation_config
        # get hardware constraints
        avail_activation_configs = self._pulsed_meas_logic.get_pulser_constraints()['activation_config']
        # init GUI elements
        # set sample rate
        self._pe.gen_sample_freq_DSpinBox.setValue(sample_rate/1e6)
        self.generator_sample_rate_changed()
        # set activation_config. This will also update the laser channel and number of channels
        # from the logic.
        self._pe.gen_activation_config_ComboBox.blockSignals(True)
        self._pe.gen_activation_config_ComboBox.clear()
        self._pe.gen_activation_config_ComboBox.addItems(list(avail_activation_configs))
        found_config = False
        for config in avail_activation_configs:
            if avail_activation_configs[config] == activation_config:
                index = self._pe.gen_activation_config_ComboBox.findText(config)
                self._pe.gen_activation_config_ComboBox.setCurrentIndex(index)
                found_config = True
                break
        if not found_config:
            self._pe.gen_activation_config_ComboBox.setCurrentIndex(0)
        self._pe.gen_activation_config_ComboBox.blockSignals(False)
        self.generator_activation_config_changed()

    def get_func_config_list(self):
        """ Retrieve the possible math functions as a list of strings.

        @return: list[] with string entries as function names.
        """
        return list(self._seq_gen_logic.func_config)

    def get_current_pulse_block_list(self):
        """ Retrieve the available Pulse_Block objects from the logic.

        @return: list[] with strings descriping the available Pulse_Block
                        objects.
        """
        return self._seq_gen_logic.saved_pulse_blocks

    def get_current_ensemble_list(self):
        """ Retrieve the available Pulse_Block_Ensemble objects from the logic.

        @return: list[] with strings descriping the available Pulse_Block_Ensemble objects.
        """
        return self._seq_gen_logic.saved_pulse_block_ensembles

    def generator_sample_rate_changed(self):
        """
        Is called whenever the sample rate for the sequence generation has changed in the GUI
        """
        self._pe.gen_sample_freq_DSpinBox.blockSignals(True)
        sample_rate = self._pe.gen_sample_freq_DSpinBox.value()*1e6
        actual_sample_rate = self._seq_gen_logic.set_sample_rate(sample_rate)
        self._pe.gen_sample_freq_DSpinBox.setValue(actual_sample_rate/1e6)
        self._pe.gen_sample_freq_DSpinBox.blockSignals(False)
        self._update_current_pulse_block()
        self._update_current_pulse_block_ensemble()
        # self._update_current_pulse_sequence()

    def generator_laser_channel_changed(self):
        """
        Is called whenever the laser channel for the sequence generation has changed in the GUI
        """
        self._pe.gen_laserchannel_ComboBox.blockSignals(True)
        laser_channel = self._pe.gen_laserchannel_ComboBox.currentText()
        actual_laser_channel = self._seq_gen_logic.set_laser_channel(laser_channel)
        index = self._pe.gen_laserchannel_ComboBox.findText(actual_laser_channel)
        self._pe.gen_laserchannel_ComboBox.setCurrentIndex(index)
        self._pe.gen_laserchannel_ComboBox.blockSignals(False)
        self._update_current_pulse_block()
        self._update_current_pulse_block_ensemble()

    def generator_activation_config_changed(self):
        """
        Is called whenever the channel config for the sequence generation has changed in the GUI
        """
        self._pe.block_editor_TableWidget.blockSignals(True)
        # retreive GUI inputs
        new_config_name = self._pe.gen_activation_config_ComboBox.currentText()
        new_channel_config = self._pulsed_meas_logic.get_pulser_constraints()['activation_config'][new_config_name]
        # set chosen config in sequence generator logic
        self._seq_gen_logic.set_activation_config(new_channel_config)
        # set display new config alongside with number of channels
        display_str = ''
        for chnl in new_channel_config:
            display_str += chnl + ' | '
        display_str = display_str[:-3]
        self._pe.gen_activation_config_LineEdit.setText(display_str)
        self._pe.gen_analog_channels_SpinBox.setValue(self._seq_gen_logic.analog_channels)
        self._pe.gen_digital_channels_SpinBox.setValue(self._seq_gen_logic.digital_channels)
        # and update the laser channel combobx
        self._pe.gen_laserchannel_ComboBox.blockSignals(True)
        self._pe.gen_laserchannel_ComboBox.clear()
        self._pe.gen_laserchannel_ComboBox.addItems(new_channel_config)
        # set the laser channel in the ComboBox
        laser_channel = self._seq_gen_logic.laser_channel
        index = self._pe.gen_laserchannel_ComboBox.findText(laser_channel)
        self._pe.gen_laserchannel_ComboBox.setCurrentIndex(index)
        self._pe.gen_laserchannel_ComboBox.blockSignals(False)

        # reshape block editor table
        self._set_block_editor_columns()

        self._pe.block_editor_TableWidget.blockSignals(False)

        self._update_current_pulse_block()
        self._update_current_pulse_block_ensemble()

    def generate_pulse_block_object(self, pb_name, block_matrix):
        """ Generates from an given table block_matrix a block_object.

        @param pb_name: string, Name of the created Pulse_Block Object
        @param block_matrix: structured np.array, matrix, in which the
                             construction plan for Pulse_Block_Element objects
                             are displayed as rows.

        Three internal dict where used, to get all the needed information about
        how parameters, functions are defined (_add_pbe_param,func_config and
        _unit_prefix).
        The dict cfg_param_pbe (configuration parameter declaration dict for
        Pulse_Block_Element) stores how the objects are appearing in the GUI.
        This dict enables the proper access to the desired element in the GUI.
        """

        # list of all the pulse block element objects
        pbe_obj_list = [None] * len(block_matrix)

        # seperate digital and analogue channels
        activation_config = self._seq_gen_logic.activation_config
        analog_chnl_names = [chnl for chnl in activation_config if 'a_ch' in chnl]
        digital_chnl_names = [chnl for chnl in activation_config if 'd_ch' in chnl]

        for row_index, row in enumerate(block_matrix):
            # check how length is displayed and convert it to bins:
            length_time = row[self._cfg_param_pbe['length']]
            init_length_bins = int(np.round(length_time * self._seq_gen_logic.sample_rate))

            # check how increment is displayed and convert it to bins:
            increment_time = row[self._cfg_param_pbe['increment']]
            increment_bins = int(np.round(increment_time * self._seq_gen_logic.sample_rate))

            # get the dict with all possible functions and their parameters:
            func_dict = self._seq_gen_logic.func_config

            # get the proper pulse_functions and its parameters:
            pulse_function = [None] * self._seq_gen_logic.analog_channels
            parameter_list = [None] * self._seq_gen_logic.analog_channels
            for num in range(self._seq_gen_logic.analog_channels):
                # get the number of the analogue channel according to the channel activation_config
                a_chnl_number = analog_chnl_names[num].split('ch')[-1]
                pulse_function[num] = row[self._cfg_param_pbe['function_' + a_chnl_number]].decode(
                    'UTF-8')

                # search for this function in the dictionary and get all the
                # parameter with their names in list:
                param_dict = func_dict[pulse_function[num]]
                parameters = {}
                for entry in list(param_dict):
                    # Obtain how the value is displayed in the table:
                    param_value = row[self._cfg_param_pbe[entry + '_' + a_chnl_number]]
                    parameters[entry] = param_value
                parameter_list[num] = parameters

            digital_high = [None] * self._seq_gen_logic.digital_channels
            for num in range(self._seq_gen_logic.digital_channels):
                # get the number of the digital channel according to the channel activation_config
                d_chnl_number = digital_chnl_names[num].split('ch')[-1]
                digital_high[num] = bool(row[self._cfg_param_pbe['digital_' + d_chnl_number]])

            use_as_tick = bool(row[self._cfg_param_pbe['use']])

            # create here actually the object with all the obtained information:
            pbe_obj_list[row_index] = Pulse_Block_Element(init_length_bins=init_length_bins,
                                                          increment_bins=increment_bins,
                                                          pulse_function=pulse_function,
                                                          digital_high=digital_high,
                                                          parameters=parameter_list,
                                                          use_as_tick=use_as_tick)

        pb_obj = Pulse_Block(pb_name, pbe_obj_list)
        # save block
        self._seq_gen_logic.save_block(pb_name, pb_obj)


    def generate_pulse_block_ensemble_object(self, ensemble_name, ensemble_matrix, rotating_frame=True):
        """
        Generates from an given table ensemble_matrix a ensemble object.

        @param str ensemble_name: Name of the created Pulse_Block_Ensemble object
        @param np.array ensemble_matrix: structured 2D np.array, matrix, in which the construction
                                         plan for Pulse_Block objects are displayed as rows.
        @param str laser_channel: the channel controlling the laser
        @param bool rotating_frame: optional, whether the phase preservation is mentained
                                    throughout the sequence.

        The dict cfg_param_pb (configuration parameter declaration dict for Pulse_Block) stores how
        the objects are related to each other in a sequencial way. That relationship is used in the
        GUI, where the parameters appear in columns.
        This dict enables the proper access to the desired element in the GUI.
        """

        # list of all the pulse block element objects
        pb_obj_list = [None] * len(ensemble_matrix)

        for row_index, row in enumerate(ensemble_matrix):
            pulse_block_name = row[self._cfg_param_pb['pulse_block']].decode('UTF-8')
            pulse_block_reps = row[self._cfg_param_pb['repetition']]
            # Fetch previously saved block object
            block = self._seq_gen_logic.get_pulse_block(pulse_block_name)
            # Append block object along with repetitions to the block list
            pb_obj_list[row_index] = (block, pulse_block_reps)

        # Create the Pulse_Block_Ensemble object
        pulse_block_ensemble = Pulse_Block_Ensemble(name=ensemble_name, block_list=pb_obj_list,
                                                    activation_config=self._seq_gen_logic.activation_config,
                                                    sample_rate=self._seq_gen_logic.sample_rate,
                                                    laser_channel=self._seq_gen_logic.laser_channel,
                                                    rotating_frame=rotating_frame)
        # save ensemble
        self._seq_gen_logic.save_ensemble(ensemble_name, pulse_block_ensemble)


    # -------------------------------------------------------------------------
    #           Methods for the Pulse Block Editor
    # -------------------------------------------------------------------------

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
        tab = self._pe.block_editor_TableWidget
        # Get from the corresponding delegate the data access model
        access = tab.itemDelegateForColumn(column).model_data_access
        data = tab.model().index(row, column).data(access)
        # check whether the value has to be normalized to SI values.
        if hasattr(tab.itemDelegateForColumn(column),'get_unit_prefix'):
            unit_prefix = tab.itemDelegateForColumn(column).get_unit_prefix()
            # access the method defined in base for unit prefix:
            return data * units.get_unit_prefix_dict()[unit_prefix]
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
        tab = self._pe.block_editor_TableWidget
        model = tab.model()
        access = tab.itemDelegateForColumn(column).model_data_access
        data = tab.model().index(row, column).data(access)

        if type(data) == type(value):
            # check whether the SI value has to be adjusted according to the
            # desired unit prefix of the current viewbox:
            if hasattr(tab.itemDelegateForColumn(column),'get_unit_prefix'):
                unit_prefix = tab.itemDelegateForColumn(column).get_unit_prefix()
                # access the method defined in base for unit prefix:
                value = value / units.get_unit_prefix_dict()[unit_prefix]
            model.setData(model.index(row,column), value, access)
        else:
            self.log.warning('The cell ({0},{1}) in block table could not be '
                        'assigned with the value="{2}", since the type "{3}" '
                        'of the cell from the delegated type differs from '
                        '"{4}" of the value!\nPrevious value will be '
                        'kept.'.format(row, column, value, type(data),
                                       type(value)))


    def _update_current_pulse_block(self):
        """ Update the current Pulse Block Info in the display. """
        length = 0.0 # in ns
        bin_length = 0
        col_ind = self._cfg_param_pbe['length']

        laser_channel = self._seq_gen_logic.laser_channel
        num_laser_ch = 0

        # Simple search routine:
        if 'a' in laser_channel:
            # extract with regular expression module the number from the
            # string:
            num = re.findall('\d+', laser_channel)
            laser_column = self._cfg_param_pbe['function_'+str(num[0])]
        elif 'd' in laser_channel:
            num = re.findall('\d+', laser_channel)
            laser_column = self._cfg_param_pbe['digital_'+str(num[0])]
        else:
            return

        # This bool is to prevent two consecutive laser on states to be counted as two laser pulses.
        laser_on = False
        # Iterate over the editor rows
        for row_ind in range(self._pe.block_editor_TableWidget.rowCount()):
            curr_length = self.get_element_in_block_table(row_ind, col_ind)
            curr_bin_length = int(np.round(curr_length*(self._seq_gen_logic.sample_rate)))
            length += curr_length
            bin_length += curr_bin_length

            laser_val =self.get_element_in_block_table(row_ind, laser_column)
            if laser_val in ('DC', 2):
                if not laser_on:
                    num_laser_ch += 1
                    laser_on = True
            else:
                laser_on = False

        #FIXME: The display unit will be later on set in the settings, so that
        #       one can choose which units are suiting the best. For now on it
        #       will be fixed to microns.

        self._pe.curr_block_length_DSpinBox.setValue(length*1e6) # in microns
        self._pe.curr_block_bins_SpinBox.setValue(bin_length)
        self._pe.curr_block_laserpulses_SpinBox.setValue(num_laser_ch)

    def get_pulse_block_table(self):
        """ Convert block table data to numpy array.

        @return: np.array[rows][columns] which has a structure, i.e. strings
                 integer and float values are represented by this array.
                 The structure was taken according to the init table itself.
        """

        tab = self._pe.block_editor_TableWidget

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
                self.log.error('Type definition not found in the block table.'
                            '\nType is neither a string, integer or float. '
                            'Include that type in the get_pulse_block_table '
                            'method!')

        # remove the last two elements since these are a comma and a space:
        structure = structure[:-2]
        table = np.zeros(tab.rowCount(), dtype=structure)

        # fill the table:
        for column in range(tab.columnCount()):
            for row in range(tab.rowCount()):
                table[row][column] = self.get_element_in_block_table(row, column)

        return table

    def load_pulse_block_clicked(self, block_name=None):
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
            current_block_name = self._pe.saved_blocks_ComboBox.currentText()

        block = self._seq_gen_logic.get_pulse_block(current_block_name, set_as_current_block=True)

        # of no object was found then block has reference to None
        if block is None:
            return -1

        # get the number of currently set analogue and digital channels from the logic.
        num_analog_chnl = self._seq_gen_logic.analog_channels
        num_digital_chnl = self._seq_gen_logic.digital_channels
        # get currently active activation_config and all possible configs.
        activation_config = self._pulsed_meas_logic.get_pulser_constraints()['activation_config']
        current_config = self._seq_gen_logic.activation_config

        # check if the currently set activation_config has the same number of channels as
        # the block object to be loaded. If this is not the case, change the config
        # to something suitable and inform the user.
        if num_analog_chnl != block.analog_channels or num_digital_chnl != block.digital_channels:
            # find the first valid activation config
            config_to_set = None
            for config in activation_config:
                num_analog = len([chnl for chnl in activation_config[config] if 'a_ch' in chnl])
                num_digital = len([chnl for chnl in activation_config[config] if 'd_ch' in chnl])
                if num_analog == block.analog_channels and num_digital == block.digital_channels:
                    config_to_set = config
                    break
            if config_to_set is None:
                self.log.error('Mismatch in number of channels between block '
                        'to load and chosen activation_config. Need {0} '
                        'digital and {1} analogue channels. Could not find a '
                        'matching activation_config.'.format(
                            block.digital_channels, block.analog_channels))
                return -1
            # find index of the config inside the ComboBox
            index_to_set = self._pe.gen_activation_config_ComboBox.findText(config_to_set)
            self._pe.gen_activation_config_ComboBox.setCurrentIndex(index_to_set)
            self.log.error('Mismatch in number of channels between block to '
                    'load and chosen activation_config. Need {0} digital '
                    'and {1} analogue channels. The following '
                    'activation_config was chosen: "{2}"'.format(
                        block.digital_channels,
                        block.analog_channels,
                        config_to_set))

            # get currently active activation_config.
            current_config = activation_config[config_to_set]

        # seperate active analog and digital channels in lists
        active_analog = [chnl for chnl in current_config if 'a_ch' in chnl]
        active_digital = [chnl for chnl in current_config if 'd_ch' in chnl]

        self.block_editor_clear_table()  # clear table
        rows = len(block.element_list)  # get amout of rows needed for display

        # configuration dict from the logic:
        block_config_dict = self._cfg_param_pbe

        self.block_editor_add_row_after_last(rows - 1)  # since one is already present

        for row_index, elem in enumerate(block.element_list):

            # set at first all digital channels:
            for digital_ch in range(elem.digital_channels):
                column = block_config_dict['digital_' + active_digital[digital_ch].split('ch')[-1]]
                value = elem.digital_high[digital_ch]
                if value:
                    value = 2
                else:
                    value = 0
                self.set_element_in_block_table(row_index, column, value)

            # now set all parameters for the analog channels:
            for analog_ch in range(elem.analog_channels):
                # the function text:
                column = block_config_dict['function_' + active_analog[analog_ch].split('ch')[-1]]
                func_text = elem.pulse_function[analog_ch]
                self.set_element_in_block_table(row_index, column, func_text)

                # then the parameter dictionary:
                parameter_dict = elem.parameters[analog_ch]
                for parameter in parameter_dict:
                    column = block_config_dict[parameter + '_' + active_analog[analog_ch].split('ch')[-1]]
                    value = np.float(parameter_dict[parameter])
                    self.set_element_in_block_table(row_index, column, value)

            # FIXME: that is not really general, since the name 'use_as_tick' is
            #       directly taken. That must be more general! Right now it is
            #       hard to make it in a general way.

            # now set use as tick parameter:
            column = block_config_dict['use']
            value = elem.use_as_tick
            # the ckeckbox has a special input value, it is 0, 1 or 2. (tri-state)
            if value:
                value = 2
            else:
                value = 0
            self.set_element_in_block_table(row_index, column, value)

            # and set the init_length_bins:
            column = block_config_dict['length']
            value = elem.init_length_bins / (self._seq_gen_logic.sample_rate)
            # the setter method will handle the proper unit for that value!
            # Just make sure to pass to the function the value in SI units!
            self.set_element_in_block_table(row_index, column, value)

            # and set the increment parameter
            column = block_config_dict['increment']
            value = elem.increment_bins / (self._seq_gen_logic.sample_rate)
            # the setter method will handle the proper unit for that value!
            # Just make sure to pass to the function the value in SI units!
            self.set_element_in_block_table(row_index, column, value)

        self._pe.curr_block_name_LineEdit.setText(current_block_name)


    def delete_pulse_block_clicked(self):
        """
        Actions to perform when the delete button in the block editor is clicked
        """
        name = self._pe.saved_blocks_ComboBox.currentText()
        self._seq_gen_logic.delete_block(name)

        # update at first the comboboxes within the organizer table and block
        # all the signals which might cause an error, because during the update
        # there is access on the table and that happens row by row, i.e. not all
        # cells are updated if the first signal is emited and there might be
        # some cells which are basically empty, which would cause an error in
        # the display of the current ensemble configuration.
        self._pe.block_organizer_TableWidget.blockSignals(True)
        self.update_block_organizer_list()
        self._pe.block_organizer_TableWidget.blockSignals(False)
        # after everything is fine, perform the update:
        self._update_current_pulse_block_ensemble()
        return

    def generate_pulse_block_clicked(self):
        """ Generate a Pulse_Block object."""
        objectname = self._pe.curr_block_name_LineEdit.text()
        if objectname == '':
            self.log.warning('No Name for Pulse_Block specified. Generation '
                        'aborted!')
            return
        self.generate_pulse_block_object(objectname, self.get_pulse_block_table())

        # update at first the comboboxes within the organizer table and block
        # all the signals which might cause an error, because during the update
        # there is access on the table and that happens row by row, i.e. not all
        # cells are updated if the first signal is emited and there might be
        # some cells which are basically empty, which would cause an error in
        # the display of the current ensemble configuration.
        self._pe.block_organizer_TableWidget.blockSignals(True)
        self.update_block_organizer_list()
        self._pe.block_organizer_TableWidget.blockSignals(False)
        # after everything is fine, perform the update:
        self._update_current_pulse_block_ensemble()

    def _determine_needed_parameters(self):
        """ Determine the maximal number of needed parameters for desired functions.

        @return ('<biggest_func_name>, number_of_parameters)
        """

        # FIXME: Reimplement this function such that it will return the
        #       parameters of all needed functions and not take only the
        #       parameters of the biggest function. Then the return should be
        #       not the biggest function, but a set of all the needed
        #       parameters which is obtained from get_func_config()!


        curr_func_list = self.get_current_function_list()
        complete_func_config = self._seq_gen_logic.func_config

        num_max_param = 0
        biggest_func = ''

        for func in curr_func_list:
            if num_max_param < len(complete_func_config[func]):
                num_max_param = len(complete_func_config[func])
                biggest_func = func

        return (num_max_param, biggest_func)

    def _set_block_editor_columns(self):
        """ General function which creates the needed columns in Pulse Block
            Editor according to the currently set channel activation_config.

        Retreives the curently set activation_config from the sequence generator logic.
        Every time this function is executed all the table entries are erased
        and created again to prevent wrong delegation.
        """

        # get the currently chosen activation_config
        # config_name = self._seq_gen_logic.current_activation_config_name
        channel_active_config = self._seq_gen_logic.activation_config

        self._pe.block_editor_TableWidget.blockSignals(True)

        # Determine the function with the most parameters. Use also that
        # function as a construction plan to create all the needed columns for
        # the parameters.
        (num_max_param, biggest_func) = self._determine_needed_parameters()

        # Erase the delegate from the column, pass a None reference:
        for column in range(self._pe.block_editor_TableWidget.columnCount()):
            self._pe.block_editor_TableWidget.setItemDelegateForColumn(column, None)

        # clear the number of columns:
        self._pe.block_editor_TableWidget.setColumnCount(0)

        # total number of analog and digital channels:
        num_of_columns = 0
        for channel in channel_active_config:
            if 'd_ch' in channel:
                num_of_columns += 1
            elif 'a_ch' in channel:
                num_of_columns += num_max_param + 1

        self._pe.block_editor_TableWidget.setColumnCount(num_of_columns)

        column_count = 0
        for channel in channel_active_config:
            if 'a_ch' in channel:
                self._pe.block_editor_TableWidget.setHorizontalHeaderItem(column_count,
                    QtWidgets.QTableWidgetItem())
                self._pe.block_editor_TableWidget.horizontalHeaderItem(column_count).setText(
                    'ACh{0}\nfunction'.format(channel.split('ch')[-1]))
                self._pe.block_editor_TableWidget.setColumnWidth(column_count, 70)

                item_dict = {}
                item_dict['get_list_method'] = self.get_current_function_list

                delegate = ComboBoxDelegate(self._pe.block_editor_TableWidget, item_dict)
                self._pe.block_editor_TableWidget.setItemDelegateForColumn(column_count, delegate)

                column_count += 1

                # fill here all parameter columns for the current analogue channel
                for parameter in self._seq_gen_logic.func_config[biggest_func]:
                    # initial block:

                    item_dict = self._seq_gen_logic.func_config[biggest_func][parameter]

                    unit_text = item_dict['unit_prefix'] + item_dict['unit']

                    self._pe.block_editor_TableWidget.setHorizontalHeaderItem(
                        column_count, QtWidgets.QTableWidgetItem())
                    self._pe.block_editor_TableWidget.horizontalHeaderItem(column_count).setText(
                        'ACh{0}\n{1} ({2})'.format(channel.split('ch')[-1], parameter,
                                                     unit_text))
                    self._pe.block_editor_TableWidget.setColumnWidth(column_count, 100)

                    # add the new properties to the whole column through delegate:

                    # extract the classname from the _param_a_ch list to be able to deligate:
                    delegate = DoubleSpinBoxDelegate(self._pe.block_editor_TableWidget, item_dict)
                    self._pe.block_editor_TableWidget.setItemDelegateForColumn(column_count,
                        delegate)
                    column_count += 1

            elif 'd_ch' in channel:
                self._pe.block_editor_TableWidget.setHorizontalHeaderItem(column_count,
                    QtWidgets.QTableWidgetItem())
                self._pe.block_editor_TableWidget.horizontalHeaderItem(column_count).setText(
                    'DCh{0}'.format(channel.split('ch')[-1]))
                self._pe.block_editor_TableWidget.setColumnWidth(column_count, 40)

                # itemlist for checkbox
                item_dict = {}
                item_dict['init_val'] = QtCore.Qt.Unchecked
                checkDelegate = CheckBoxDelegate(self._pe.block_editor_TableWidget, item_dict)
                self._pe.block_editor_TableWidget.setItemDelegateForColumn(column_count, checkDelegate)

                column_count += 1

        # Insert the additional parameters given in the add_pbe_param dictionary (length etc.)
        for column, parameter in enumerate(self._add_pbe_param):
            # add the new properties to the whole column through delegate:
            item_dict = self._add_pbe_param[parameter]

            if 'unit_prefix' in item_dict.keys():
                unit_text = item_dict['unit_prefix'] + item_dict['unit']
            else:
                unit_text = item_dict['unit']

            self._pe.block_editor_TableWidget.insertColumn(num_of_columns + column)
            self._pe.block_editor_TableWidget.setHorizontalHeaderItem(num_of_columns + column,
                                                                      QtWidgets.QTableWidgetItem())
            self._pe.block_editor_TableWidget.horizontalHeaderItem(
                num_of_columns + column).setText('{0} ({1})'.format(parameter, unit_text))
            self._pe.block_editor_TableWidget.setColumnWidth(num_of_columns + column, 90)

            # Use only DoubleSpinBox as delegate:
            if item_dict['unit'] == 'bool':
                delegate = CheckBoxDelegate(self._pe.block_editor_TableWidget, item_dict)
            else:
                delegate = DoubleSpinBoxDelegate(self._pe.block_editor_TableWidget, item_dict)
            self._pe.block_editor_TableWidget.setItemDelegateForColumn(num_of_columns + column,
                                                                       delegate)

            # initialize the whole row with default values:
            for row_num in range(self._pe.block_editor_TableWidget.rowCount()):
                # get the model, here are the data stored:
                model = self._pe.block_editor_TableWidget.model()
                # get the corresponding index of the current element:
                index = model.index(row_num, num_of_columns + column)
                # get the initial values of the delegate class which was
                # uses for this column:
                ini_values = delegate.get_initial_value()
                # set initial values:
                model.setData(index, ini_values[0], ini_values[1])

        self.initialize_cells_block_editor(0, self._pe.block_editor_TableWidget.rowCount())

        self.set_cfg_param_pbe()
        self._pe.block_editor_TableWidget.blockSignals(False)
        self._update_current_pulse_block()

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
            stop_row = start_row + 1

        if start_col is None:
            start_col = 0

        if stop_col is None:
            stop_col = self._pe.block_editor_TableWidget.columnCount()

        for col_num in range(start_col, stop_col):

            for row_num in range(start_row, stop_row):
                # get the model, here are the data stored:
                model = self._pe.block_editor_TableWidget.model()
                # get the corresponding index of the current element:
                index = model.index(row_num, col_num)
                # get the initial values of the delegate class which was
                # uses for this column:
                ini_values = self._pe.block_editor_TableWidget.itemDelegateForColumn(
                    col_num).get_initial_value()
                # set initial values:
                model.setData(index, ini_values[0], ini_values[1])

    # -------------------------------------------------------------------------
    #           Methods for the Pulse Block Organizer
    # -------------------------------------------------------------------------

    def update_block_organizer_list(self):
        """ If a Pulse_Block object has been deleted, update the list in
            organizer.
        """

        column = 0
        for row in range(self._pe.block_organizer_TableWidget.rowCount()):
            data = self.get_element_in_organizer_table(row, column)
            if data not in self._seq_gen_logic.saved_pulse_blocks:
                self.initialize_cells_block_organizer(start_row=row, stop_row=row+1,
                                                      start_col=column,stop_col=column+1)

    def _update_current_pulse_block_ensemble(self):
        length_mu = 0.0  # in microseconds
        length_bin = 0
        num_laser_pulses = 0
        filesize_bytes = 0
        pulse_block_col = self._cfg_param_pb['pulse_block']

        reps_col = self._cfg_param_pb['repetition']

        if len(self._seq_gen_logic.saved_pulse_blocks) > 0:
            for row_ind in range(self._pe.block_organizer_TableWidget.rowCount()):
                pulse_block_name = self.get_element_in_organizer_table(row_ind, pulse_block_col)

                block_obj = self._seq_gen_logic.get_pulse_block(pulse_block_name)

                reps = self.get_element_in_organizer_table(row_ind, reps_col)

                # Calculate the length via the gaussian summation formula:
                length_bin = int(length_bin + block_obj.init_length_bins * (reps + 1) +
                             ((reps + 1) * ((reps + 1) + 1) / 2) * block_obj.increment_bins)

                # Calculate the number of laser pulses
                num_laser_pulses_block = 0
                if self._seq_gen_logic.laser_channel is None:
                    num_laser_pulses_block = 0
                elif 'd_ch' in self._seq_gen_logic.laser_channel:
                    # determine the laser channel index for the corresponding channel
                    digital_chnl_list = [chnl for chnl in self._seq_gen_logic.activation_config if
                                         'd_ch' in chnl]
                    laser_index = digital_chnl_list.index(self._seq_gen_logic.laser_channel)
                    # Iterate through the elements and count laser on state changes
                    # (no double counting)
                    laser_on = False
                    for elem in block_obj.element_list:
                        if laser_index >= len(elem.digital_high):
                            break
                        if elem.digital_high[laser_index] and not laser_on:
                            num_laser_pulses_block += 1
                            laser_on = True
                        elif not elem.digital_high[laser_index]:
                            laser_on = False
                elif 'a_ch' in self._seq_gen_logic.laser_channel:
                    # determine the laser channel index for the corresponding channel
                    analog_chnl_list = [chnl for chnl in self._seq_gen_logic.activation_config if
                                        'a_ch' in chnl]
                    laser_index = analog_chnl_list.index(self._seq_gen_logic.laser_channel)
                    # Iterate through the elements and count laser on state changes
                    # (no double counting)
                    laser_on = False
                    for elem in block_obj.element_list:
                        if laser_index >= len(elem.pulse_function):
                            break
                        if elem.pulse_function[laser_index] == 'DC' and not laser_on:
                            num_laser_pulses_block += 1
                            laser_on = True
                        elif elem.pulse_function[laser_index] != 'DC':
                            laser_on = False
                num_laser_pulses += num_laser_pulses_block*(reps+1)


            length_mu = (length_bin / self._seq_gen_logic.sample_rate) * 1e6  # in microns

        # get file format to determine the file size in bytes.
        # This is just an estimate since it does not include file headers etc..
        # FIXME: This is just a crude first try to implement this. Improvement required.
        file_format = self._pulsed_meas_logic.get_pulser_constraints()['waveform_format']
        if file_format == 'wfm':
            num_ana_chnl = self._seq_gen_logic.analog_channels
            filesize_bytes = num_ana_chnl * 5 * length_bin
        elif file_format == 'wfmx':
            chnl_config = self._seq_gen_logic.activation_config
            analogue_chnl_num = [int(chnl.split('ch')[1]) for chnl in chnl_config if 'a_ch' in chnl]
            digital_chnl_num= [int(chnl.split('ch')[1]) for chnl in chnl_config if 'd_ch' in chnl]
            for ana_chnl in analogue_chnl_num:
                if (ana_chnl*2-1) in digital_chnl_num or (ana_chnl*2) in digital_chnl_num:
                    filesize_bytes += 5 * length_bin
                else:
                    filesize_bytes += 4 * length_bin
        elif file_format == 'fpga':
            filesize_bytes = length_bin
        else:
            filesize_bytes = 0

        self._pe.curr_ensemble_size_DSpinBox.setValue(filesize_bytes/(1024**2))
        self._pe.curr_ensemble_length_DSpinBox.setValue(length_mu)
        self._pe.curr_ensemble_bins_SpinBox.setValue(length_bin)
        self._pe.curr_ensemble_laserpulses_SpinBox.setValue(num_laser_pulses)


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

        tab = self._pe.block_organizer_TableWidget

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

        tab = self._pe.block_organizer_TableWidget
        model = tab.model()
        access = tab.itemDelegateForColumn(column).model_data_access
        data = tab.model().index(row, column).data(access)

        if type(data) == type(value):
            model.setData(model.index(row,column), value, access)
        else:
            self.log.warning('The cell ({0},{1}) in block organizer table '
                    'could not be assigned with the value="{2}", since the '
                    'type "{3}" of the cell from the delegated type differs '
                    'from "{4}" of the value!\nPrevious value will be '
                    'kept.'.format(row, column, value, type(data),
                        type(value)))

    def get_organizer_table(self):
        """ Convert organizer table data to numpy array.

        @return: np.array[rows][columns] which has a structure, i.e. strings
                 integer and float values are represented by this array.
                 The structure was taken according to the init table itself.
        """

        tab = self._pe.block_organizer_TableWidget

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
                self.log.error('Type definition not found in the organizer '
                        'table.'
                        '\nType is neither a string, integer or float. '
                        'Include that type in the get_organizer_table '
                        'method!')

        # remove the last two elements since these are a comma and a space:
        structure = structure[:-2]
        table = np.zeros(tab.rowCount(), dtype=structure)

        # fill the table:
        for column in range(tab.columnCount()):
            for row in range(tab.rowCount()):
                table[row][column] = self.get_element_in_organizer_table(row, column)

        return table

    def block_editor_add_row_before_selected(self, insert_rows=1):
        """ Add row before selected element. """

        self._pe.block_editor_TableWidget.blockSignals(True)

        selected_row = self._pe.block_editor_TableWidget.currentRow()

        # the signal passes a boolean value, which overwrites the insert_rows
        # parameter. Check that here and use the actual default value:
        if type(insert_rows) is bool:
            insert_rows = 1

        for rows in range(insert_rows):
            self._pe.block_editor_TableWidget.insertRow(selected_row)
        self.initialize_cells_block_editor(start_row=selected_row,
                                           stop_row=selected_row + insert_rows)

        self._pe.block_editor_TableWidget.blockSignals(False)

    def block_editor_add_row_after_last(self, insert_rows=1):
        """ Add row after last row in the block editor. """

        self._pe.block_editor_TableWidget.blockSignals(True)

        # the signal passes a boolean value, which overwrites the insert_rows
        # parameter. Check that here and use the actual default value:
        if type(insert_rows) is bool:
            insert_rows = 1

        number_of_rows = self._pe.block_editor_TableWidget.rowCount()

        self._pe.block_editor_TableWidget.setRowCount(
            number_of_rows + insert_rows)
        self.initialize_cells_block_editor(start_row=number_of_rows,
                                           stop_row=number_of_rows + insert_rows)

        self._pe.block_editor_TableWidget.blockSignals(False)

    def block_editor_delete_row_selected(self):
        """ Delete row of selected element. """

        # get the row number of the selected item(s). That will return the
        # lowest selected row
        row_to_remove = self._pe.block_editor_TableWidget.currentRow()
        self._pe.block_editor_TableWidget.removeRow(row_to_remove)

    def block_editor_delete_row_last(self):
        """ Delete the last row in the block editor. """

        number_of_rows = self._pe.block_editor_TableWidget.rowCount()
        # remember, the row index is started to count from 0 and not from 1,
        # therefore one has to reduce the value by 1:
        self._pe.block_editor_TableWidget.removeRow(number_of_rows - 1)

    def block_editor_clear_table(self):
        """ Delete all rows in the block editor table. """

        self._pe.block_editor_TableWidget.blockSignals(True)

        self._pe.block_editor_TableWidget.setRowCount(1)
        self._pe.block_editor_TableWidget.clearContents()

        self.initialize_cells_block_editor(start_row=0)
        self._pe.block_editor_TableWidget.blockSignals(False)

    def load_pulse_block_ensemble_clicked(self, ensemble_name=None):
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
            current_ensemble_name = self._pe.saved_ensembles_ComboBox.currentText()

        # get the ensemble object and set as current ensemble
        ensemble = self._seq_gen_logic.get_pulse_block_ensemble(current_ensemble_name,
                                                    set_as_current_ensemble=True)

        # Check whether an ensemble is found, otherwise there will be None:
        if ensemble is None:
            return

        # set the activation_config to the one defined in the loaded ensemble
        avail_configs = self._pulsed_meas_logic.get_pulser_constraints()['activation_config']
        current_activation_config = self._seq_gen_logic.activation_config
        activation_config_to_set = ensemble.activation_config
        config_name_to_set = None
        if current_activation_config != activation_config_to_set:
            for config in avail_configs:
                if activation_config_to_set == avail_configs[config]:
                    config_name_to_set = config
                    break
            if config_name_to_set is not None:
                index = self._pe.gen_activation_config_ComboBox.findText(config_name_to_set)
                self._pe.gen_activation_config_ComboBox.setCurrentIndex(index)
            self.log.info('Current generator channel activation config '
                    'did not match the activation config of the '
                    'Pulse_Block_Ensemble to load. Changed config to "{0}".'
                    ''.format(config_name_to_set))

        # set the sample rate to the one defined in the loaded ensemble
        current_sample_rate = self._seq_gen_logic.sample_rate
        sample_rate_to_set = ensemble.sample_rate
        if current_sample_rate != sample_rate_to_set:
            self._pe.gen_sample_freq_DSpinBox.setValue(sample_rate_to_set/1e6)
            self.generator_sample_rate_changed()
            self.log.info('Current generator sample rate did not match the '
                    'sample rate of the Pulse_Block_Ensemble to load. '
                    'Changed the sample rate to {0}Hz.'
                    ''.format(sample_rate_to_set))

        # set the laser channel to the one defined in the loaded ensemble
        current_laser_channel = self._seq_gen_logic.laser_channel
        laser_channel_to_set = ensemble.laser_channel
        if current_laser_channel != laser_channel_to_set and laser_channel_to_set is not None:
            index = self._pe.gen_laserchannel_ComboBox.findText(laser_channel_to_set)
            self._pe.gen_laserchannel_ComboBox.setCurrentIndex(index)
            self.log.info('Current generator laser channel did not match the '
                    'laser channel of the Pulse_Block_Ensemble to load. '
                    'Changed the laser channel to "{0}".'
                    ''.format(laser_channel_to_set))

        self.block_organizer_clear_table()  # clear the block organizer table
        rows = len(ensemble.block_list)  # get amout of rows needed for display

        # add as many rows as there are blocks in the ensemble
        # minus 1 because a single row is already present after clear
        self.block_organizer_add_row_after_last(rows - 1)

        # This dictionary has the information which column number describes
        # which object, it is a configuration dict between GUI and logic
        organizer_config_dict = self._cfg_param_pb

        # run through all blocks in the block_elements block_list to fill in the
        # row informations
        for row_index, (pulse_block, repetitions) in enumerate(ensemble.block_list):
            column = organizer_config_dict['pulse_block']
            self.set_element_in_organizer_table(row_index, column, pulse_block.name)

            column = organizer_config_dict['repetition']
            self.set_element_in_organizer_table(row_index, column, int(repetitions))

        # set the ensemble name LineEdit to the current ensemble
        self._pe.curr_ensemble_name_LineEdit.setText(current_ensemble_name)




    def block_organizer_add_row_before_selected(self,insert_rows=1):
        """ Add row before selected element. """
        self._pe.block_organizer_TableWidget.blockSignals(True)
        selected_row = self._pe.block_organizer_TableWidget.currentRow()

        # the signal passes a boolean value, which overwrites the insert_rows
        # parameter. Check that here and use the actual default value:
        if type(insert_rows) is bool:
            insert_rows = 1

        for rows in range(insert_rows):
            self._pe.block_organizer_TableWidget.insertRow(selected_row)

        self.initialize_cells_block_organizer(start_row=selected_row)
        self._pe.block_organizer_TableWidget.blockSignals(False)
        self._update_current_pulse_block_ensemble()


    def block_organizer_add_row_after_last(self, insert_rows=1):
        """ Add row after last row in the block editor. """
        self._pe.block_organizer_TableWidget.blockSignals(True)

        # the signal of a QPushButton passes an optional boolean value to this
        # method, which overwrites the insert_rows parameter. Check that here
        # and use the actual default value:
        if type(insert_rows) is bool:
            insert_rows = 1

        number_of_rows = self._pe.block_organizer_TableWidget.rowCount()
        self._pe.block_organizer_TableWidget.setRowCount(number_of_rows+insert_rows)

        self.initialize_cells_block_organizer(start_row=number_of_rows,
                                              stop_row=number_of_rows + insert_rows)

        self._pe.block_organizer_TableWidget.blockSignals(False)
        self._update_current_pulse_block_ensemble()

    def block_organizer_delete_row_selected(self):
        """ Delete row of selected element. """

        # get the row number of the selected item(s). That will return the
        # lowest selected row
        row_to_remove = self._pe.block_organizer_TableWidget.currentRow()
        self._pe.block_organizer_TableWidget.removeRow(row_to_remove)
        self._update_current_pulse_block_ensemble()

    def block_organizer_delete_row_last(self):
        """ Delete the last row in the block editor. """

        number_of_rows = self._pe.block_organizer_TableWidget.rowCount()
        # remember, the row index is started to count from 0 and not from 1,
        # therefore one has to reduce the value by 1:
        self._pe.block_organizer_TableWidget.removeRow(number_of_rows-1)
        self._update_current_pulse_block_ensemble()

    def block_organizer_clear_table(self):
        """ Delete all rows in the block editor table. """


        self._pe.block_organizer_TableWidget.blockSignals(True)
        self._pe.block_organizer_TableWidget.setRowCount(1)
        self._pe.block_organizer_TableWidget.clearContents()
        self.initialize_cells_block_organizer(start_row=0)
        self._pe.block_organizer_TableWidget.blockSignals(False)
        self._update_current_pulse_block_ensemble()

    def delete_pulse_block_ensemble_clicked(self):
        """
        Actions to perform when the delete button in the block organizer is clicked
        """
        name = self._pe.saved_ensembles_ComboBox.currentText()
        self._seq_gen_logic.delete_ensemble(name)
        self.update_ensemble_list()
        return


    def generate_pulse_block_ensemble_clicked(self):
        """ Generate a Pulse_Block_ensemble object."""

        objectname = self._pe.curr_ensemble_name_LineEdit.text()
        if objectname == '':
            self.log.warning('No Name for Pulse_Block_Ensemble specified. '
                        'Generation aborted!')
            return
        rotating_frame =  self._pe.curr_ensemble_rot_frame_CheckBox.isChecked()
        self.generate_pulse_block_ensemble_object(objectname, self.get_organizer_table(),
                                                  rotating_frame)

    def set_cfg_param_pbe(self):
        """ Set the parameter configuration of the Pulse_Block_Elements
        according to the current table configuration and updates the dict in
        the logic.
        """

        cfg_param_pbe = OrderedDict()
        for column in range(self._pe.block_editor_TableWidget.columnCount()):
            text = self._pe.block_editor_TableWidget.horizontalHeaderItem(column).text()
            split_text = text.split()
            if 'DCh' in split_text[0]:
                cfg_param_pbe['digital_' + split_text[0][3]] = column
            elif 'ACh' in split_text[0]:
                cfg_param_pbe[split_text[1] + '_' + split_text[0][3]] = column
            else:
                cfg_param_pbe[split_text[0]] = column

        self._cfg_param_pbe = cfg_param_pbe

    def set_cfg_param_pb(self):
        """ Set the parameter configuration of the Pulse_Block according to the
        current table configuration and updates the dict in the logic.
        """

        cfg_param_pb = OrderedDict()

        for column in range(self._pe.block_organizer_TableWidget.columnCount()):
            text = self._pe.block_organizer_TableWidget.horizontalHeaderItem(column).text()
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

    def _set_organizer_columns(self):

        # Erase the delegate from the column, i.e. pass a None reference:
        for column in range(self._pe.block_organizer_TableWidget.columnCount()):
            self._pe.block_organizer_TableWidget.setItemDelegateForColumn(column, None)

        # clear the number of columns:
        self._pe.block_organizer_TableWidget.setColumnCount(0)

        # total number columns in block organizer:
        num_column = 1
        self._pe.block_organizer_TableWidget.setColumnCount(num_column)

        column = 0
        self._pe.block_organizer_TableWidget.setHorizontalHeaderItem(column, QtWidgets.QTableWidgetItem())
        self._pe.block_organizer_TableWidget.horizontalHeaderItem(column).setText('Pulse Block')
        self._pe.block_organizer_TableWidget.setColumnWidth(column, 100)

        item_dict = {}
        item_dict['get_list_method'] = self.get_current_pulse_block_list

        comboDelegate = ComboBoxDelegate(self._pe.block_organizer_TableWidget, item_dict)
        self._pe.block_organizer_TableWidget.setItemDelegateForColumn(column, comboDelegate)

        column = 1
        insert_at_col_pos = column
        for column, parameter in enumerate(self._add_pb_param):

            # add the new properties to the whole column through delegate:
            item_dict = self._add_pb_param[parameter]

            unit_text = item_dict['unit_prefix'] + item_dict['unit']

            self._pe.block_organizer_TableWidget.insertColumn(insert_at_col_pos+column)
            self._pe.block_organizer_TableWidget.setHorizontalHeaderItem(insert_at_col_pos+column, QtWidgets.QTableWidgetItem())
            self._pe.block_organizer_TableWidget.horizontalHeaderItem(insert_at_col_pos+column).setText('{0} ({1})'.format(parameter,unit_text))
            self._pe.block_organizer_TableWidget.setColumnWidth(insert_at_col_pos+column, 80)

            # Use only DoubleSpinBox  as delegate:
            if item_dict['unit'] == 'bool':
                delegate = CheckBoxDelegate(self._pe.block_organizer_TableWidget, item_dict)
            elif parameter == 'repetition':
                delegate = SpinBoxDelegate(self._pe.block_organizer_TableWidget, item_dict)
            else:
                delegate = DoubleSpinBoxDelegate(self._pe.block_organizer_TableWidget, item_dict)
            self._pe.block_organizer_TableWidget.setItemDelegateForColumn(insert_at_col_pos+column, delegate)

            column += 1

        self.initialize_cells_block_organizer(start_row=0,
                                              stop_row=self._pe.block_organizer_TableWidget.rowCount())

        self.set_cfg_param_pb()
        self._update_current_pulse_block_ensemble()


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
            stop_col = self._pe.block_organizer_TableWidget.columnCount()

        for col_num in range(start_col, stop_col):

            for row_num in range(start_row,stop_row):
                # get the model, here are the data stored:
                model = self._pe.block_organizer_TableWidget.model()
                # get the corresponding index of the current element:
                index = model.index(row_num, col_num)
                # get the initial values of the delegate class which was
                # uses for this column:
                ini_values = self._pe.block_organizer_TableWidget.itemDelegateForColumn(col_num).get_initial_value()
                # set initial values:
                model.setData(index, ini_values[0], ini_values[1])

    def _add_config_for_predefined_methods(self, parent, name):
        """ Create the Config Elements for altering the Predefined Methods
            display.
        """
        # one has to know that all the checkbox control elements are attached
        # to the widget verticalLayout, accessible via self._pm_cfg.verticalLayout

        checkbox = self._create_QCheckBox(parent, default_val=True)

        checkbox.setText(name)
        setattr(self._pm_cfg, name +'_CheckBox', checkbox)
        self._pm_cfg.verticalLayout.addWidget(checkbox)

    def _get_ref_checkbox_predefined_methods_config(self, name):
        """ Retrieve the reference to the CheckBox with the name of the predefined method

        @param str name: the name of the predefined method

        @return QtGui.QCheckBox: reference to the CheckBox widget.
        """

        return getattr(self._pm_cfg, name+'_CheckBox')

    def _create_control_for_predefined_methods(self):
        """ Create the Control Elements in the Predefined Windows, depending
            on the methods of the logic.

        The following procedure was chosen:
            1. At first the method is inspected and all the parameters are
              investigated. Depending on the type of the default value of the
              keyword, a ControlBox (CheckBox, DoubleSpinBox, ...) is created.laserchannel_ComboBox
                _<method_name>_generate()
                which are connected to the generate button and passes all the
                parameters to the method in the logic.
            3. An additional method is created as
                _<method_name>_generate_upload()
                which generates and uploads the current values to the device.
        """
        method_list = self._seq_gen_logic.predefined_method_list

        for method in method_list:
            inspected = inspect.signature(method)


            gridLayout = QtWidgets.QGridLayout()
            groupBox = QtWidgets.QGroupBox(self._pm)

            obj_list = []

            # go through the parameter list and check the type of the default
            # parameter
            for index, param_name in enumerate(inspected.parameters):

                label_obj = self._create_QLabel(groupBox, param_name)

                default_value = inspected.parameters[param_name].default

                if default_value is inspect._empty:
                    self.log.error('The method "{0}" in the logic has an '
                                'argument "{1}" without a default value!\n'
                                'Assign a default value to that, otherwise a '
                                'type estimation is not possible!\n'
                                'Creation of the viewbox '
                                'aborted.'.format(method.__name__, param_name))
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
                    self.log.error('The method "{0}" in the logic has an '
                            'argument "{1}" with is not of the valid types'
                            'str, float int or bool!\n'
                            'Choose one of those default values! Creation '
                            'of the viewbox aborted.'.format(
                                method.__name__, param_name))

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

            horizontalLayout = QtWidgets.QHBoxLayout(groupBox)

            horizontalLayout.addLayout(gridLayout)

            groupBox.setTitle(method.__name__.replace('_',' '))

            # attach the GroupBox widget to the predefined methods widget.
            setattr(self._pm, method.__name__+'_GroupBox', groupBox)

            # Since a Scroll Widget is used, you need you pass the
            # scrollAreaWidgetContents as the parent widget.
            self._add_config_for_predefined_methods(self._pm_cfg.scrollAreaWidgetContents, method.__name__)

            # add the name of the predefined method to a local list to keep
            # track of the method:
            self._predefined_methods_list.append(method.__name__)

            self._pm.verticalLayout.addWidget(groupBox)

    def _get_ref_groupbox_predefined_methods(self, name):
        """ Retrieve the reference to the GroupBox with the name of the predefined method

        @param str name: the name of the predefined method

        @return QtGui.QGroupBox: reference to the groupbox widget containing all
                                 elements for the predefined methods.
        """

        return getattr(self._pm, name+'_GroupBox')


    def _create_QLabel(self, parent, label_name):
        """ Helper method for _create_control_for_predefined_methods.

        @param parent: The parent QWidget, which should own that object
        @param str label_name: the display name for the QLabel Widget.

        @return QtGui.QLabel: a predefined label for the GUI.
        """

        label = QtWidgets.QLabel(parent)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(label.sizePolicy().hasHeightForWidth())
        label.setSizePolicy(sizePolicy)
        label.setText(label_name)
        return label

    def _create_QDoubleSpinBox(self, parent, default_val=0.0):
        """ Helper method for _create_control_for_predefined_methods.

        @param parent: The parent QWidget, which should own that object
        @param float default_val: a default value for the QDoubleSpinBox.

        @return QtGui.QDoubleSpinBox: a predefined QDoubleSpinBox for the GUI.
        """

        doublespinbox = QtWidgets.QDoubleSpinBox(parent)
        doublespinbox.setMaximum(np.inf)
        doublespinbox.setMinimum(-np.inf)

        # set a size for vertivcal an horizontal dimensions
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(doublespinbox.sizePolicy().hasHeightForWidth())

        doublespinbox.setMinimumSize(QtCore.QSize(80, 0))
        doublespinbox.setValue(default_val)
        return doublespinbox

    def _create_QSpinBox(self, parent, default_val=0):
        """ Helper method for _create_control_for_predefined_methods.

        @param parent: The parent QWidget, which should own that object
        @param int default_val: a default value for the QSpinBox.

        @return QtGui.QSpinBox: a predefined QSpinBox for the GUI.
        """

        spinBox = QtWidgets.QSpinBox(parent)
        spinBox.setMaximum(2**31 -1)
        spinBox.setMinimum(-2**31 +1)
        spinBox.setValue(default_val)
        return spinBox

    def _create_QCheckBox(self, parent, default_val=False):
        """ Helper method for _create_control_for_predefined_methods.

        @param parent: The parent QWidget, which should own that object
        @param bool default_val: a default value for the QCheckBox.

        @return QtGui.QCheckBox: a predefined QCheckBox for the GUI.
        """

        checkBox = QtWidgets.QCheckBox(parent)
        checkBox.setChecked(default_val)
        return checkBox

    def _create_QLineEdit(self, parent, default_val=''):
        """ Helper method for _create_control_for_predefined_methods.

        @param parent: The parent QWidget, which should own that object
        @param str default_val: a default value for the QLineEdit.

        @return QtGui.QLineEdit: a predefined QLineEdit for the GUI.
        """

        lineedit = QtWidgets.QLineEdit(parent)
        lineedit.setText(default_val)

        # set a size for vertivcal an horizontal dimensions
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(lineedit.sizePolicy().hasHeightForWidth())

        lineedit.setMinimumSize(QtCore.QSize(80, 0))

        lineedit.setSizePolicy(sizePolicy)
        return lineedit

    def _create_QPushButton(self, parent, text='Generate'):
        """ Helper method for _create_control_for_predefined_methods.

        @param parent: The parent QWidget, which should own that object
        @param str text: a display text for the QPushButton.

        @return QtGui.QPushButton: a predefined QPushButton for the GUI.
        """

        pushbutton = QtWidgets.QPushButton(parent)
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
            for index, obj in enumerate(object_list):
                if hasattr(obj,'isChecked'):
                    parameters[index] = obj.isChecked()
                elif hasattr(obj,'value'):
                    parameters[index] = obj.value()
                elif hasattr(obj,'text'):

                    parameters[index] = obj.text()
                    ensemble_name = obj.text()
                else:
                    self.log.error('Not possible to get the value from the '
                            'viewbox, since it does not have one of the'
                            'possible access methods!')

            # the * operator unpacks the list
            ref_logic_gen(*parameters)
            return ensemble_name

        # assign now a new name to that function, this name will be used to
        # bound the function as attribute to the main object.
        func_dummy_name.__name__ = func_name
        return func_dummy_name





