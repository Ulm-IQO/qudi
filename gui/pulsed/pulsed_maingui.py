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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import datetime
import inspect
import numpy as np
import os
import pyqtgraph as pg
import re


from collections import OrderedDict
from core.module import Connector, StatusVar
from core.util import units
from core.util.mutex import Mutex
from gui.colordefs import QudiPalettePale as palette
from gui.colordefs import QudiPalette as palettedark
from gui.fitsettings import FitSettingsDialog, FitSettingsComboBox
from gui.guibase import GUIBase
from gui.pulsed.pulse_editors import BlockEditor, BlockOrganizer, SequenceEditor
#from gui.pulsed.pulse_editor import PulseEditor
from logic.sampling_functions import SamplingFunctions
from qtpy import QtGui
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic
from qtwidgets.scientific_spinbox import ScienDSpinBox, ScienSpinBox


#FIXME: Display the Pulse
#FIXME: save the length in sample points (bins)
#FIXME: adjust the length to the bins


class PulsedMeasurementMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pulsed_maingui.ui')

        # Load it
        super(PulsedMeasurementMainWindow, self).__init__()

        uic.loadUi(ui_file, self)
        self.show()


class PulseAnalysisTab(QtWidgets.QWidget):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pulse_analysis.ui')
        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)


class PulseGeneratorTab(QtWidgets.QWidget):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pulse_editor.ui')
        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)


class SequenceGeneratorTab(QtWidgets.QWidget):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_sequence_editor.ui')
        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)


class PulseExtractionTab(QtWidgets.QWidget):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pulse_extraction.ui')
        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)


class AnalysisSettingDialog(QtWidgets.QDialog):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pulsed_main_gui_settings_analysis.ui')

        # Load it
        super().__init__()

        uic.loadUi(ui_file, self)


class GeneratorSettingsDialog(QtWidgets.QDialog):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pulsed_main_gui_settings_block_gen.ui')

        # Load it
        super().__init__()

        uic.loadUi(ui_file, self)


class PredefinedMethodsTab(QtWidgets.QWidget):
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
        ui_file = os.path.join(this_dir, 'ui_predefined_methods_config.ui')

        # Load it
        super().__init__()

        uic.loadUi(ui_file, self)

class PulsedMeasurementGui(GUIBase):
    """ This is the main GUI Class for pulsed measurements. """

    _modclass = 'PulsedMeasurementGui'
    _modtype = 'gui'

    ## declare connectors
    pulsedmasterlogic = Connector(interface='PulsedMasterLogic')
    savelogic = Connector(interface='SaveLogic')

    # status var
    _ana_param_x_axis_name_text = StatusVar('ana_param_x_axis_name_LineEdit', 'Tau')
    _ana_param_x_axis_unit_text = StatusVar('ana_param_x_axis_unit_LineEdit', 's')
    _ana_param_y_axis_name_text = StatusVar('ana_param_y_axis_name_LineEdit', 'Normalized Signal')
    _ana_param_y_axis_unit_text = StatusVar('ana_param_y_axis_unit_LineEdit', '')
    _ana_param_second_plot_x_axis_name_text = StatusVar('ana_param_second_plot_x_axis_name_LineEdit', 'Frequency')
    _ana_param_second_plot_x_axis_unit_text = StatusVar('ana_param_second_plot_x_axis_unit_LineEdit', 'Hz')
    _ana_param_second_plot_y_axis_name_text = StatusVar('ana_param_second_plot_y_axis_name_LineEdit', 'Ft Signal')
    _ana_param_second_plot_y_axis_unit_text = StatusVar('ana_param_second_plot_y_axis_unit_LineEdit', '')

    _ana_param_errorbars = StatusVar('ana_param_errorbars_CheckBox', False)
    _second_plot_ComboBox_text = StatusVar('second_plot_ComboBox_text', '')

    _predefined_methods_to_show = StatusVar('predefined_methods_to_show', [])
    _functions_to_show = StatusVar('functions_to_show', [])

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialize, connect and configure the pulsed measurement GUI.

        Establish general connectivity and activate the different tabs of the
        GUI.
        """
        self._pulsed_master_logic = self.get_connector('pulsedmasterlogic')
        self._save_logic = self.get_connector('savelogic')

        self._mw = PulsedMeasurementMainWindow()
        self._pa = PulseAnalysisTab()
        self._pg = PulseGeneratorTab()
        self._pe = PulseExtractionTab()
        self._pm = PredefinedMethodsTab()
        self._sg = SequenceGeneratorTab()

        self._mw.tabWidget.addTab(self._pa, 'Analysis')
        self._mw.tabWidget.addTab(self._pe, 'Pulse Extraction')
        self._mw.tabWidget.addTab(self._pg, 'Pulse Generator')
        self._mw.tabWidget.addTab(self._sg, 'Sequence Generator')
        self._mw.tabWidget.addTab(self._pm, 'Predefined Methods')

        self.setup_toolbar()
        self._activate_analysis_settings_ui()
        self._activate_analysis_ui()
        self.setup_extraction_ui()

        self._activate_generator_settings_ui()
        self._activate_pulse_generator_ui()

        self.show()

        self._pa.ext_control_mw_freq_DoubleSpinBox.setMaximum(999999999999)

    def on_deactivate(self):
        """ Undo the Definition, configuration and initialisation of the pulsed
            measurement GUI.

        This deactivation disconnects all the graphic modules, which were
        connected in the initUI method.
        """
        self._deactivate_analysis_settings_ui()
        self._deactivate_analysis_ui()

        self._deactivate_generator_settings_ui()
        self._deactivate_pulse_generator_ui()

        self._mw.close()

    def show(self):
        """Make main window visible and put it above all other windows. """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    ###########################################################################
    ###   Methods related to Settings for the 'Pulse Generator' tab:        ###
    ###########################################################################
    def _activate_generator_settings_ui(self):
        """ Initialize, connect and configure the pulse generator settings to be displayed in the
        editor.
        """
        self._gs = GeneratorSettingsDialog()
        self._gs.accepted.connect(self.apply_generator_settings)
        self._gs.rejected.connect(self.keep_former_generator_settings)
        self._gs.sampled_file_format_comboBox.currentIndexChanged.connect(
            self.generator_settings_changed, QtCore.Qt.QueuedConnection)
        self._gs.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(
            self.apply_generator_settings)

        # here are all the names of the predefined methods are saved.
        self._predefined_methods_list = []
        # create a config for the predefined methods:
        self._pm_cfg = PredefinedMethodsConfigDialog()
        self._pm_cfg.accepted.connect(self.apply_predefined_methods_config)
        self._pm_cfg.rejected.connect(self.keep_former_predefined_methods_config)
        self._pm_cfg.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(
            self.apply_predefined_methods_config)
        # Set ranges for the global parameters and default values
        self._pm.pm_mw_amp_Widget.setRange(0.0, np.inf)
        self._pm.pm_mw_freq_Widget.setRange(0.0, np.inf)
        self._pm.pm_channel_amp_Widget.setRange(0.0, np.inf)
        self._pm.pm_delay_length_Widget.setRange(0.0, np.inf)
        self._pm.pm_wait_time_Widget.setRange(0.0, np.inf)
        self._pm.pm_laser_length_Widget.setRange(0.0, np.inf)
        self._pm.pm_rabi_period_Widget.setRange(0.0, np.inf)
        self._pm.pm_mw_amp_Widget.setValue(0.125)
        self._pm.pm_mw_freq_Widget.setValue(2.87e6)
        self._pm.pm_channel_amp_Widget.setValue(0.0)
        self._pm.pm_delay_length_Widget.setValue(500.0e-9)
        self._pm.pm_wait_time_Widget.setValue(1.5e-6)
        self._pm.pm_laser_length_Widget.setValue(3.0e-6)
        self._pm.pm_rabi_period_Widget.setValue(200.0e-9)

        # connect the menu to the actions:
        self._mw.action_Settings_Block_Generation.triggered.connect(self.show_generator_settings)
        self._mw.action_Predefined_Methods_Config.triggered.connect(self.show_predefined_methods_config)

        self._pulsed_master_logic.sigPredefinedSequencesUpdated.connect(self.predefined_methods_changed)

        # Create function config dialog
        self._create_function_config()
        return

    def _deactivate_generator_settings_ui(self):
        """ Disconnects the configuration of the Settings for the 'Pulse Generator' Tab.
        """
        self._gs.accepted.disconnect()
        self._gs.rejected.disconnect()
        self._gs.sampled_file_format_comboBox.currentIndexChanged.disconnect()
        self._gs.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.disconnect()
        self._gs.close()

        self._pm_cfg.accepted.disconnect()
        self._pm_cfg.rejected.disconnect()
        self._pm_cfg.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.disconnect()
        self._pm_cfg.close()


        self._pulsed_master_logic.sigPredefinedSequencesUpdated.disconnect()
        self._mw.action_Settings_Block_Generation.triggered.disconnect()
        self._mw.action_Predefined_Methods_Config.triggered.disconnect()
        return

    def show_generator_settings(self):
        """
        Opens the generator settings menu.
        """
        self._gs.exec_()
        return

    def _create_function_config(self):
        # Add in the settings menu within the groupbox widget all the available math_functions,
        # based on the list from the Logic. Right now, the GUI objects are inserted the 'hard' way,
        # like it is done in the Qt-Designer.
        # FIXME: Make a nicer way of displaying the available functions, maybe with a Table!
        objectname = self._gs.objectName()
        for index, func_name in enumerate(list(SamplingFunctions().func_config)):
            name_label = 'func_' + str(index)
            setattr(self._gs, name_label, QtWidgets.QLabel(self._gs.groupBox))
            label = getattr(self._gs, name_label)
            label.setObjectName(name_label)
            self._gs.gridLayout_3.addWidget(label, index, 0, 1, 1)
            label.setText(QtWidgets.QApplication.translate(objectname, func_name, None))

            name_checkbox = 'checkbox_' + str(index)
            setattr(self._gs, name_checkbox, QtWidgets.QCheckBox(self._gs.groupBox))
            checkbox = getattr(self._gs, name_checkbox)
            checkbox.setObjectName(name_checkbox)
            self._gs.gridLayout_3.addWidget(checkbox, index, 1, 1, 1)
            checkbox.setText(QtWidgets.QApplication.translate(objectname, '', None))
        # Check all functions that are in the _functions_to_show list.
        # If no such list is present take the first 3 functions as default
        if len(self._functions_to_show) > 0:
            for func in self._functions_to_show:
                index = list(SamplingFunctions().func_config).index(func)
                name_checkbox = 'checkbox_' + str(index)
                checkbox = getattr(self._gs, name_checkbox)
                checkbox.setCheckState(QtCore.Qt.Checked)
        else:
            for index in range(3):
                name_checkbox = 'checkbox_' + str(index)
                checkbox = getattr(self._gs, name_checkbox)
                checkbox.setCheckState(QtCore.Qt.Checked)
        return

    def apply_generator_settings(self):
        """
        Write new generator settings from the gui to the file.
        """
        new_config = SamplingFunctions().func_config
        for index, func_name in enumerate(list(SamplingFunctions().func_config)):
            name_checkbox = 'checkbox_' + str(index)
            checkbox = getattr(self._gs, name_checkbox)
            if not checkbox.isChecked():
                name_label = 'func_' + str(index)
                func = getattr(self._gs, name_label)
                del new_config[func.text()]
        self._functions_to_show = list(new_config)
        if self.block_editor.function_config != new_config:
            self.block_editor.set_function_config(new_config)
        return

    def keep_former_generator_settings(self):
        """
        Keep the old generator settings and restores them in the gui.
        """
        old_config = self.block_editor.function_config
        for index, func_name in enumerate(list(SamplingFunctions().func_config)):
            name_checkbox = 'checkbox_' + str(index)
            checkbox = getattr(self._gs, name_checkbox)
            if func_name in old_config:
                checkbox.setChecked(True)
            else:
                checkbox.setChecked(False)
        return

    def show_predefined_methods_config(self):
        """ Opens the Window for the config of predefined methods."""
        self._pm_cfg.show()
        self._pm_cfg.raise_()

    def predefined_methods_changed(self, methods_dict):
        """

        @param methods_dict:
        @return:
        """
        self._predefined_methods_list = list(methods_dict)
        # create all GUI elements
        self._create_predefined_methods(methods_dict)
        # check all checkboxes that correspond to the methods to show in the config dialogue
        for method_name in self._predefined_methods_to_show:
            if method_name in self._predefined_methods_list:
                index = self._predefined_methods_list.index(method_name)
                checkbox = getattr(self._pm_cfg, 'checkbox_' + str(index))
                checkbox.setChecked(True)
            else:
                del_index = self._predefined_methods_to_show.index(method_name)
                del self._predefined_methods_to_show[del_index]
        # apply the chosen methods to the methods dialogue
        self.apply_predefined_methods_config()
        return

    def _create_predefined_methods(self, methods_dict):
        """
        Initializes the GUI elements for the predefined methods and the corresponding config

        @param methods_dict:
        @return:
        """
        for index, method_name in enumerate(list(methods_dict)):
            # create checkboxes for the config dialogue
            name_checkbox = 'checkbox_' + str(index)
            setattr(self._pm_cfg, name_checkbox, QtWidgets.QCheckBox(self._pm_cfg.scrollArea))
            checkbox = getattr(self._pm_cfg, name_checkbox)
            checkbox.setObjectName(name_checkbox)
            checkbox.setText(method_name)
            checkbox.setChecked(False)
            self._pm_cfg.verticalLayout.addWidget(checkbox)

            # Create the widgets for the predefined methods dialogue
            # Create GroupBox for the method to reside in
            groupBox = QtWidgets.QGroupBox(self._pm)
            groupBox.setAlignment(QtCore.Qt.AlignLeft)
            groupBox.setTitle(method_name)
            # Create layout within the GroupBox
            gridLayout = QtWidgets.QGridLayout(groupBox)
            # Create generate buttons
            gen_button = QtWidgets.QPushButton(groupBox)
            gen_button.setText('Generate')
            gen_button.setObjectName('gen_' + method_name)
            gen_button.clicked.connect(self.generate_predefined_clicked)
            sauplo_button = QtWidgets.QPushButton(groupBox)
            sauplo_button.setText('GenSaUpLo')
            sauplo_button.setObjectName('sauplo_' + method_name)
            sauplo_button.clicked.connect(self.generate_sauplo_predefined_clicked)
            gridLayout.addWidget(gen_button, 0, 0, 1, 1)
            gridLayout.addWidget(sauplo_button, 1, 0, 1, 1)
            # inspect current method to extract the parameters
            inspected = inspect.signature(methods_dict[method_name])
            # run through all parameters of the current method and create the widgets
            for param_index, param_name in enumerate(inspected.parameters):
                if param_name not in ['mw_channel', 'gate_count_channel', 'sync_trig_channel',
                                      'mw_amp', 'mw_freq', 'channel_amp', 'delay_length',
                                      'wait_time', 'laser_length', 'rabi_period']:
                    # get default value of the parameter
                    default_val = inspected.parameters[param_name].default
                    if default_val is inspect._empty:
                        self.log.error('The method "{0}" in the logic has an argument "{1}" without'
                                       ' a default value!\nAssign a default value to that, '
                                       'otherwise a type estimation is not possible!\n'
                                       'Creation of the viewbox aborted.'
                                       ''.format('generate_' + method_name, param_name))
                        return
                    # create a label for the parameter
                    param_label = QtWidgets.QLabel(groupBox)
                    param_label.setText(param_name)
                    # create proper input widget for the parameter depending on the type of default_val
                    if type(default_val) is bool:
                        input_obj = QtWidgets.QCheckBox(groupBox)
                        input_obj.setChecked(default_val)
                    elif type(default_val) is float:
                        input_obj = ScienDSpinBox(groupBox)
                        input_obj.setMaximum(np.inf)
                        input_obj.setMinimum(-np.inf)
                        if 'amp' in param_name:
                            input_obj.setSuffix('V')
                        elif 'freq' in param_name:
                            input_obj.setSuffix('Hz')
                        elif 'length' in param_name or 'time' in param_name or 'period' in param_name or 'tau' in param_name:
                            input_obj.setSuffix('s')
                        input_obj.setMinimumSize(QtCore.QSize(80, 0))
                        input_obj.setValue(default_val)
                    elif type(default_val) is int:
                        input_obj = ScienSpinBox(groupBox)
                        input_obj.setMaximum(2**31 - 1)
                        input_obj.setMinimum(-2**31 + 1)
                        input_obj.setValue(default_val)
                    elif type(default_val) is str:
                        input_obj = QtWidgets.QLineEdit(groupBox)
                        input_obj.setMinimumSize(QtCore.QSize(80, 0))
                        input_obj.setText(default_val)
                    else:
                        self.log.error('The method "{0}" in the logic has an argument "{1}" with is not'
                                       ' of the valid types str, float, int or bool!\nChoose one of '
                                       'those default values! Creation of the viewbox aborted.'
                                       ''.format('generate_' + method_name, param_name))
                    # Adjust size policy
                    input_obj.setMinimumWidth(75)
                    input_obj.setMaximumWidth(100)
                    gridLayout.addWidget(param_label, 0, param_index+1, 1, 1)
                    gridLayout.addWidget(input_obj, 1, param_index+1, 1, 1)
                    setattr(self._pm, method_name + '_param_' + param_name + '_Widget', input_obj)
            h_spacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Expanding,
                                             QtWidgets.QSizePolicy.Minimum)
            gridLayout.addItem(h_spacer, 1, param_index+2, 1, 1)

            # attach the GroupBox widget to the predefined methods widget.
            setattr(self._pm, method_name + '_GroupBox', groupBox)
            self._pm.verticalLayout.addWidget(groupBox)
        self._pm.verticalLayout.addStretch()
        return

    def keep_former_predefined_methods_config(self):
        for index, name in enumerate(self._predefined_methods_list):
            groupbox = getattr(self._pm, name + '_GroupBox')
            checkbox = getattr(self._pm_cfg, 'checkbox_' + str(index))
            checkbox.setChecked(groupbox.isVisible())
        return

    def apply_predefined_methods_config(self):
        self._predefined_methods_to_show = []
        for index, name in enumerate(self._predefined_methods_list):
            groupbox = getattr(self._pm, name + '_GroupBox')
            checkbox = getattr(self._pm_cfg, 'checkbox_' + str(index))
            is_checked = checkbox.isChecked()
            groupbox.setVisible(is_checked)
            if is_checked:
                self._predefined_methods_to_show.append(name)

        self._pm.hintLabel.setVisible(len(self._predefined_methods_to_show) == 0)
        return


    ###########################################################################
    ###   Methods related to Tab 'Pulse Generator' in the Pulsed Window:    ###
    ###########################################################################
    def _activate_pulse_generator_ui(self):
        """ Initialize, connect and configure the 'Pulse Generator' Tab.
        """
        # connect signals of input widgets
        self._pg.gen_sample_freq_DSpinBox.editingFinished.connect(self.generator_settings_changed, QtCore.Qt.QueuedConnection)
        self._pg.gen_laserchannel_ComboBox.currentIndexChanged.connect(self.generator_settings_changed, QtCore.Qt.QueuedConnection)
        self._pg.gen_activation_config_ComboBox.currentIndexChanged.connect(self.generator_settings_changed, QtCore.Qt.QueuedConnection)
        # connect signals of buttons
        self._pg.saup_ensemble_PushButton.clicked.connect(self.saup_ensemble_clicked)
        self._sg.saup_sequence_PushButton.clicked.connect(self.saup_sequence_clicked)
        self._pg.sauplo_ensemble_PushButton.clicked.connect(self.sauplo_ensemble_clicked)
        self._sg.sauplo_sequence_PushButton.clicked.connect(self.sauplo_sequence_clicked)

        self._pg.block_add_last_PushButton.clicked.connect(self.block_add_last_clicked)
        self._pg.block_del_last_PushButton.clicked.connect(self.block_del_last_clicked)
        self._pg.block_add_sel_PushButton.clicked.connect(self.block_add_sel_clicked)
        self._pg.block_del_sel_PushButton.clicked.connect(self.block_del_sel_clicked)
        self._pg.block_clear_PushButton.clicked.connect(self.block_clear_clicked)
        self._pg.organizer_add_last_PushButton.clicked.connect(self.organizer_add_last_clicked)
        self._pg.organizer_del_last_PushButton.clicked.connect(self.organizer_del_last_clicked)
        self._pg.organizer_add_sel_PushButton.clicked.connect(self.organizer_add_sel_clicked)
        self._pg.organizer_del_sel_PushButton.clicked.connect(self.organizer_del_sel_clicked)
        self._pg.organizer_clear_PushButton.clicked.connect(self.organizer_clear_clicked)
        self._sg.sequence_add_last_PushButton.clicked.connect(self.sequence_add_last_clicked)
        self._sg.sequence_del_last_PushButton.clicked.connect(self.sequence_del_last_clicked)
        self._sg.sequence_add_sel_PushButton.clicked.connect(self.sequence_add_sel_clicked)
        self._sg.sequence_del_sel_PushButton.clicked.connect(self.sequence_del_sel_clicked)
        self._sg.sequence_clear_PushButton.clicked.connect(self.sequence_clear_clicked)

        self._pg.curr_block_generate_PushButton.clicked.connect(self.editor_generate_block_clicked)
        self._pg.curr_block_del_PushButton.clicked.connect(self.editor_delete_block_clicked)
        self._pg.curr_block_load_PushButton.clicked.connect(self.editor_load_block_clicked)
        self._pg.curr_ensemble_generate_PushButton.clicked.connect(self.editor_generate_ensemble_clicked)
        self._pg.curr_ensemble_del_PushButton.clicked.connect(self.editor_delete_ensemble_clicked)
        self._pg.curr_ensemble_load_PushButton.clicked.connect(self.editor_load_ensemble_clicked)
        self._sg.curr_sequence_generate_PushButton.clicked.connect(self.editor_generate_sequence_clicked)
        self._sg.curr_sequence_del_PushButton.clicked.connect(self.editor_delete_sequence_clicked)
        self._sg.curr_sequence_load_PushButton.clicked.connect(self.editor_load_sequence_clicked)

        # connect update signals from pulsed_master_logic
        self._pulsed_master_logic.sigEnsembleSaUpComplete.connect(self.saup_ensemble_finished)
        self._pulsed_master_logic.sigSequenceSaUpComplete.connect(self.saup_sequence_finished)
        self._pulsed_master_logic.sigSavedPulseBlocksUpdated.connect(self.update_block_dict)
        self._pulsed_master_logic.sigSavedBlockEnsemblesUpdated.connect(self.update_ensemble_dict)
        self._pulsed_master_logic.sigSavedSequencesUpdated.connect(self.update_sequence_dict)
        self._pulsed_master_logic.sigGeneratorSettingsUpdated.connect(self.update_generator_settings)

        self._pulsed_master_logic.sigCurrentPulseBlockUpdated.connect(self.load_block_in_editor)
        self._pulsed_master_logic.sigCurrentBlockEnsembleUpdated.connect(self.load_ensemble_in_editor)
        self._pulsed_master_logic.sigCurrentSequenceUpdated.connect(self.load_sequence_in_editor)

        self.block_organizer = BlockOrganizer(self._pg.block_organizer_TableWidget)
        self.block_editor = BlockEditor(self._pg.block_editor_TableWidget)
        self.sequence_editor = SequenceEditor(self._sg.sequence_editor_TableWidget)

        # Apply hardware constraints to input widgets
        self._gen_apply_hardware_constraints()

        # Fill initial values from logic into input widgets
        self._pulsed_master_logic.request_generator_init_values()
        return

    def _deactivate_pulse_generator_ui(self):
        """ Disconnects the configuration for 'Pulse Generator Tab.
        """
        # disconnect signals of input widgets
        self._pg.gen_sample_freq_DSpinBox.editingFinished.disconnect()
        self._pg.gen_laserchannel_ComboBox.currentIndexChanged.disconnect()
        self._pg.gen_activation_config_ComboBox.currentIndexChanged.disconnect()
        # disconnect signals of buttons
        self._pg.saup_ensemble_PushButton.clicked.disconnect()
        self._sg.saup_sequence_PushButton.clicked.disconnect()
        self._pg.sauplo_ensemble_PushButton.clicked.disconnect()
        self._sg.sauplo_sequence_PushButton.clicked.disconnect()
        self._pg.block_add_last_PushButton.clicked.disconnect()
        self._pg.block_del_last_PushButton.clicked.disconnect()
        self._pg.block_add_sel_PushButton.clicked.disconnect()
        self._pg.block_del_sel_PushButton.clicked.disconnect()
        self._pg.block_clear_PushButton.clicked.disconnect()
        self._pg.organizer_add_last_PushButton.clicked.disconnect()
        self._pg.organizer_del_last_PushButton.clicked.disconnect()
        self._pg.organizer_add_sel_PushButton.clicked.disconnect()
        self._pg.organizer_del_sel_PushButton.clicked.disconnect()
        self._pg.organizer_clear_PushButton.clicked.disconnect()
        self._sg.sequence_add_last_PushButton.clicked.disconnect()
        self._sg.sequence_del_last_PushButton.clicked.disconnect()
        self._sg.sequence_add_sel_PushButton.clicked.disconnect()
        self._sg.sequence_del_sel_PushButton.clicked.disconnect()
        self._sg.sequence_clear_PushButton.clicked.disconnect()
        self._pg.curr_block_generate_PushButton.clicked.disconnect()
        self._pg.curr_block_del_PushButton.clicked.disconnect()
        self._pg.curr_block_load_PushButton.clicked.disconnect()
        self._pg.curr_ensemble_generate_PushButton.clicked.disconnect()
        self._pg.curr_ensemble_del_PushButton.clicked.disconnect()
        self._pg.curr_ensemble_load_PushButton.clicked.disconnect()
        self._sg.curr_sequence_generate_PushButton.clicked.disconnect()
        self._sg.curr_sequence_del_PushButton.clicked.disconnect()
        self._sg.curr_sequence_load_PushButton.clicked.disconnect()
        # disconnect update signals from pulsed_master_logic
        self._pulsed_master_logic.sigEnsembleSaUpComplete.disconnect()
        self._pulsed_master_logic.sigSequenceSaUpComplete.disconnect()
        self._pulsed_master_logic.sigSavedPulseBlocksUpdated.disconnect()
        self._pulsed_master_logic.sigSavedBlockEnsemblesUpdated.disconnect()
        self._pulsed_master_logic.sigSavedSequencesUpdated.disconnect()
        self._pulsed_master_logic.sigGeneratorSettingsUpdated.disconnect()
        self._pulsed_master_logic.sigCurrentPulseBlockUpdated.disconnect()
        self._pulsed_master_logic.sigCurrentBlockEnsembleUpdated.disconnect()
        self._pulsed_master_logic.sigCurrentSequenceUpdated.disconnect()
        return

    def _gen_apply_hardware_constraints(self):
        """
        Retrieve the constraints from pulser hardware and apply these constraints to the pulse
        generator GUI elements.
        """
        # block signals
        self._pg.gen_activation_config_ComboBox.blockSignals(True)
        self._pg.gen_sample_freq_DSpinBox.blockSignals(True)
        # apply constraints
        pulser_constr, dummy = self._pulsed_master_logic.get_hardware_constraints()
        self._pg.gen_activation_config_ComboBox.addItems(list(pulser_constr.activation_config))
        self._pg.gen_sample_freq_DSpinBox.setMinimum(pulser_constr.sample_rate.min)
        self._pg.gen_sample_freq_DSpinBox.setMaximum(pulser_constr.sample_rate.max)
        self._pg.gen_sample_freq_DSpinBox.setSingleStep(pulser_constr.sample_rate.step)
        # unblock signals
        self._pg.gen_activation_config_ComboBox.blockSignals(False)
        self._pg.gen_sample_freq_DSpinBox.blockSignals(False)
        return

    def generator_settings_changed(self):
        """

        @return:
        """
        sample_rate = self._pg.gen_sample_freq_DSpinBox.value()
        laser_channel = self._pg.gen_laserchannel_ComboBox.currentText()
        activation_config_name = self._pg.gen_activation_config_ComboBox.currentText()
        amplitude_dict = self._pulsed_master_logic._generator_logic.amplitude_dict
        waveform_format = self._gs.sampled_file_format_comboBox.currentText()

        self._pulsed_master_logic.generator_settings_changed(activation_config_name, laser_channel,
                                                             sample_rate, amplitude_dict,
                                                             waveform_format)
        return

    def update_generator_settings(self, activation_config_name, activation_config, sample_rate,
                                   amplitude_dict, laser_channel, waveform_format):
        """

        @param activation_config_name:
        @param activation_config:
        @param sample_rate:
        @param amplitude_dict:
        @param laser_channel:
        @param waveform_format:
        @return:
        """
        # block signals
        self._pg.gen_sample_freq_DSpinBox.blockSignals(True)
        self._pg.gen_laserchannel_ComboBox.blockSignals(True)
        self._pg.gen_activation_config_ComboBox.blockSignals(True)
        self._gs.sampled_file_format_comboBox.blockSignals(True)
        # sampling format
        index = self._gs.sampled_file_format_comboBox.findText(waveform_format)
        self._gs.sampled_file_format_comboBox.setCurrentIndex(index)
        # activation config
        index = self._pg.gen_activation_config_ComboBox.findText(activation_config_name)
        self._pg.gen_activation_config_ComboBox.setCurrentIndex(index)
        display_str = ''
        for chnl in activation_config:
            display_str += chnl + ' | '
        display_str = display_str[:-3]
        self._pg.gen_activation_config_LineEdit.setText(display_str)
        self._pg.gen_analog_channels_SpinBox.setValue(
            len([chnl for chnl in activation_config if 'a_ch' in chnl]))
        self._pg.gen_digital_channels_SpinBox.setValue(
            len([chnl for chnl in activation_config if 'd_ch' in chnl]))
        # laser channel
        self._pg.gen_laserchannel_ComboBox.clear()
        self._pg.gen_laserchannel_ComboBox.addItems(activation_config)
        index = self._pg.gen_laserchannel_ComboBox.findText(laser_channel)
        self._pg.gen_laserchannel_ComboBox.setCurrentIndex(index)
        # sample rate
        self._pg.gen_sample_freq_DSpinBox.setValue(sample_rate)
        # set activation config in block editor
        if self.block_editor.activation_config != activation_config:
            if self.block_editor.activation_config is None:
                self.block_editor.set_activation_config(activation_config)
                self.apply_generator_settings()
            else:
                self.block_editor.set_activation_config(activation_config)
        # unblock signals
        self._gs.sampled_file_format_comboBox.blockSignals(False)
        self._pg.gen_sample_freq_DSpinBox.blockSignals(False)
        self._pg.gen_laserchannel_ComboBox.blockSignals(False)
        self._pg.gen_activation_config_ComboBox.blockSignals(False)
        return

    def block_add_last_clicked(self):
        """

        @return:
        """
        self.block_editor.insert_rows(self._pg.block_editor_TableWidget.rowCount(), 1)
        return

    def block_del_last_clicked(self):
        """

        @return:
        """
        self.block_editor.delete_row(self._pg.block_editor_TableWidget.rowCount() - 1)
        return

    def block_add_sel_clicked(self):
        """

        @return:
        """
        index = self._pg.block_editor_TableWidget.currentRow()
        self.block_editor.insert_rows(index + 1, 1)
        return

    def block_del_sel_clicked(self):
        """

        @return:
        """
        index = self._pg.block_editor_TableWidget.currentRow()
        self.block_editor.delete_row(index)
        return

    def block_clear_clicked(self):
        """

        @return:
        """
        self.block_editor.clear_table()
        return

    def organizer_add_last_clicked(self):
        """

        @return:
        """
        self.block_organizer.insert_rows(self._pg.block_organizer_TableWidget.rowCount(), 1)
        return

    def organizer_del_last_clicked(self):
        """

        @return:
        """
        self.block_organizer.delete_row(self._pg.block_organizer_TableWidget.rowCount() - 1)
        return

    def organizer_add_sel_clicked(self):
        """

        @return:
        """
        index = self._pg.block_organizer_TableWidget.currentRow()
        self.block_organizer.insert_rows(index + 1, 1)
        return

    def organizer_del_sel_clicked(self):
        """

        @return:
        """
        index = self._pg.block_organizer_TableWidget.currentRow()
        self.block_organizer.delete_row(index)
        return

    def organizer_clear_clicked(self):
        """

        @return:
        """
        self.block_organizer.clear_table()
        return

    def sequence_add_last_clicked(self):
        """

        @return:
        """
        self.sequence_editor.insert_rows(self._sg.sequence_editor_TableWidget.rowCount(), 1)
        return

    def sequence_del_last_clicked(self):
        """

        @return:
        """
        self.sequence_editor.delete_row(self._sg.sequence_editor_TableWidget.rowCount() - 1)
        return

    def sequence_add_sel_clicked(self):
        """

        @return:
        """
        index = self._sg.sequence_editor_TableWidget.currentRow()
        self.sequence_editor.insert_rows(index + 1, 1)
        return

    def sequence_del_sel_clicked(self):
        """

        @return:
        """
        index = self._sg.sequence_editor_TableWidget.currentRow()
        self.sequence_editor.delete_row(index)
        return

    def sequence_clear_clicked(self):
        """

        @return:
        """
        self.sequence_editor.clear_table()
        return

    def editor_generate_block_clicked(self):
        name = self._pg.curr_block_name_LineEdit.text()
        if name == '':
            self.log.error('No name has been entered for the PulseBlock to be generated.')
            return
        block_object = self.block_editor.generate_block_object(name)
        self._pulsed_master_logic.save_pulse_block(name, block_object)
        return

    def editor_delete_block_clicked(self):
        name = self._pg.saved_blocks_ComboBox.currentText()
        self._pulsed_master_logic.delete_pulse_block(name)
        return

    def editor_load_block_clicked(self):
        name = self._pg.saved_blocks_ComboBox.currentText()
        self._pulsed_master_logic.load_pulse_block(name)
        return

    def editor_generate_ensemble_clicked(self):
        name = self._pg.curr_ensemble_name_LineEdit.text()
        if name == '':
            self.log.error('No name has been entered for the PulseBlockEnsemble to be generated.')
            return
        rotating_frame = self._pg.curr_ensemble_rot_frame_CheckBox.isChecked()
        ensemble_object = self.block_organizer.generate_ensemble_object(name, rotating_frame)
        self._pulsed_master_logic.save_block_ensemble(name, ensemble_object)
        return

    def editor_delete_ensemble_clicked(self):
        name = self._pg.saved_ensembles_ComboBox.currentText()
        self._pulsed_master_logic.delete_block_ensemble(name)
        return

    def editor_load_ensemble_clicked(self):
        name = self._pg.saved_ensembles_ComboBox.currentText()
        self._pulsed_master_logic.load_block_ensemble(name)
        return

    def editor_generate_sequence_clicked(self):
        name = self._sg.curr_sequence_name_LineEdit.text()
        if name == '':
            self.log.error('No name has been entered for the PulseSequence to be generated.')
            return
        rotating_frame = self._sg.curr_sequence_rot_frame_CheckBox.isChecked()
        sequence_object = self.sequence_editor.generate_sequence_object(name, rotating_frame)
        self._pulsed_master_logic.save_sequence(name, sequence_object)
        return

    def editor_delete_sequence_clicked(self):
        name = self._sg.saved_sequences_ComboBox.currentText()
        self._pulsed_master_logic.delete_sequence(name)
        return

    def editor_load_sequence_clicked(self):
        name = self._sg.saved_sequences_ComboBox.currentText()
        self._pulsed_master_logic.load_sequence(name)
        return

    def load_block_in_editor(self, block_obj):
        self.block_editor.load_pulse_block(block_obj)
        if block_obj is not None:
            self._pg.curr_block_name_LineEdit.setText(block_obj.name)
        return

    def load_ensemble_in_editor(self, ensemble_obj, ensemble_params):
        self.block_organizer.load_pulse_block_ensemble(ensemble_obj)
        if ensemble_params != {}:
            self._pg.curr_ensemble_length_DSpinBox.setValue(ensemble_params['sequence_length'])
            self._pg.curr_ensemble_bins_SpinBox.setValue(ensemble_params['sequence_length_bins'])
            # FIXME: This is just a rough estimation of the waveform size in MB (only valid for AWG)
            size_mb = (ensemble_params['sequence_length_bins'] * 5) / 1024**2
            self._pg.curr_ensemble_size_DSpinBox.setValue(size_mb)
            self._pg.curr_ensemble_laserpulses_SpinBox.setValue(ensemble_params['num_of_lasers'])
        else:
            self._pg.curr_ensemble_length_DSpinBox.setValue(0.0)
            self._pg.curr_ensemble_bins_SpinBox.setValue(0)
            self._pg.curr_ensemble_size_DSpinBox.setValue(0.0)
            self._pg.curr_ensemble_laserpulses_SpinBox.setValue(0)
        if ensemble_obj is not None:
            self._pg.curr_ensemble_name_LineEdit.setText(ensemble_obj.name)
        return

    def load_sequence_in_editor(self, sequence_obj, sequence_params):
        self.sequence_editor.load_pulse_sequence(sequence_obj)
        if sequence_params != {}:
            self._sg.curr_sequence_length_DSpinBox.setValue(sequence_params['sequence_length'])
            self._sg.curr_sequence_bins_SpinBox.setValue(sequence_params['sequence_length_bins'])
            # FIXME: This is just a rough estimation of the sequence size in MB
            size_mb = (sequence_params['sequence_length_bins'] * 5) / 1024**2
            self._sg.curr_sequence_size_DSpinBox.setValue(size_mb)
        else:
            self._sg.curr_sequence_length_DSpinBox.setValue(0.0)
            self._sg.curr_sequence_bins_SpinBox.setValue(0)
            self._sg.curr_sequence_size_DSpinBox.setValue(0.0)
        if sequence_obj is not None:
            self._sg.curr_sequence_name_LineEdit.setText(sequence_obj.name)
        return

    def update_block_dict(self, block_dict):
        """

        @param block_dict:
        @return:
        """
        self.block_organizer.set_block_dict(block_dict)
        self._pg.saved_blocks_ComboBox.blockSignals(True)
        self._pg.saved_blocks_ComboBox.clear()
        self._pg.saved_blocks_ComboBox.addItems(list(block_dict))
        self._pg.saved_blocks_ComboBox.blockSignals(False)
        return

    def update_ensemble_dict(self, ensemble_dict):
        """

        @param ensemble_dict:
        @return:
        """
        # Check if an ensemble has been added. In that case set the current index to the new one.
        # In all other cases try to maintain the current item and if it was removed, set the first.
        text_to_set = None
        if len(ensemble_dict) == self._pg.gen_ensemble_ComboBox.count() + 1:
            for key in ensemble_dict:
                if self._pg.gen_ensemble_ComboBox.findText(key) == -1:
                    text_to_set = key
        else:
            text_to_set = self._pg.gen_ensemble_ComboBox.currentText()

        self.sequence_editor.set_ensemble_dict(ensemble_dict)
        # block signals
        self._pg.gen_ensemble_ComboBox.blockSignals(True)
        self._pg.saved_ensembles_ComboBox.blockSignals(True)
        # update gen_sequence_ComboBox items
        self._pg.gen_ensemble_ComboBox.clear()
        self._pg.gen_ensemble_ComboBox.addItems(list(ensemble_dict))
        self._pg.saved_ensembles_ComboBox.clear()
        self._pg.saved_ensembles_ComboBox.addItems(list(ensemble_dict))
        if text_to_set is not None:
            index = self._pg.gen_ensemble_ComboBox.findText(text_to_set)
            if index != -1:
                self._pg.gen_ensemble_ComboBox.setCurrentIndex(index)
        # unblock signals
        self._pg.gen_ensemble_ComboBox.blockSignals(False)
        self._pg.saved_ensembles_ComboBox.blockSignals(False)
        return

    def update_sequence_dict(self, sequence_dict):
        """

        @param sequence_dict:
        @return:
        """
        # Check if a sequence has been added. In that case set the current index to the new one.
        # In all other cases try to maintain the current item and if it was removed, set the first.
        text_to_set = None
        if len(sequence_dict) == self._sg.gen_sequence_ComboBox.count() + 1:
            for key in sequence_dict:
                if self._sg.gen_sequence_ComboBox.findText(key) == -1:
                    text_to_set = key
        else:
            text_to_set = self._sg.gen_sequence_ComboBox.currentText()

        # block signals
        self._sg.gen_sequence_ComboBox.blockSignals(True)
        self._sg.saved_sequences_ComboBox.blockSignals(True)
        # update gen_sequence_ComboBox items
        self._sg.gen_sequence_ComboBox.clear()
        self._sg.gen_sequence_ComboBox.addItems(list(sequence_dict))
        self._sg.saved_sequences_ComboBox.clear()
        self._sg.saved_sequences_ComboBox.addItems(list(sequence_dict))
        if text_to_set is not None:
            index = self._sg.gen_sequence_ComboBox.findText(text_to_set)
            if index != -1:
                self._sg.gen_sequence_ComboBox.setCurrentIndex(index)
        # unblock signals
        self._sg.gen_sequence_ComboBox.blockSignals(False)
        self._sg.saved_sequences_ComboBox.blockSignals(False)
        return

    def saup_ensemble_clicked(self):
        """
        This method is called when the user clicks on "Sample + Upload Ensemble"
        """
        # Get the ensemble name from the ComboBox
        ensemble_name = self._pg.gen_ensemble_ComboBox.currentText()
        # disable buttons
        self._pg.saup_ensemble_PushButton.setEnabled(False)
        self._pg.sauplo_ensemble_PushButton.setEnabled(False)
        # Sample and upload the ensemble via logic module
        self._pulsed_master_logic.sample_block_ensemble(ensemble_name, False)
        return

    def saup_ensemble_finished(self, ensemble_name):
        """
        This method
        """
        # enable buttons
        self._pg.saup_ensemble_PushButton.setEnabled(True)
        self._pg.sauplo_ensemble_PushButton.setEnabled(True)
        return

    def sauplo_ensemble_clicked(self):
        """
        This method is called when the user clicks on "Sample + Upload + Load Ensemble"
        """
        # Get the ensemble name from the ComboBox
        ensemble_name = self._pg.gen_ensemble_ComboBox.currentText()
        # disable buttons
        self._pg.saup_ensemble_PushButton.setEnabled(False)
        self._pg.sauplo_ensemble_PushButton.setEnabled(False)
        self._pg.load_ensemble_PushButton.setEnabled(False)
        # Sample, upload and load the ensemble via logic module
        self._pulsed_master_logic.sample_block_ensemble(ensemble_name, True)
        return

    def saup_sequence_clicked(self):
        """
        This method is called when the user clicks on "Sample + Upload Sequence"
        """
        # Get the sequence name from the ComboBox
        sequence_name = self._sg.gen_sequence_ComboBox.currentText()
        # disable buttons
        self._sg.saup_sequence_PushButton.setEnabled(False)
        self._sg.sauplo_sequence_PushButton.setEnabled(False)
        # Sample the sequence via logic module
        self._pulsed_master_logic.sample_sequence(sequence_name, False)
        return

    def saup_sequence_finished(self, sequence_name):
        """
        This method
        """
        # enable buttons
        self._sg.saup_sequence_PushButton.setEnabled(True)
        self._sg.sauplo_sequence_PushButton.setEnabled(True)
        return

    def sauplo_sequence_clicked(self):
        """
        This method is called when the user clicks on "Sample + Upload + Load Sequence"
        """
        # Get the sequence name from the ComboBox
        sequence_name = self._sg.gen_sequence_ComboBox.currentText()
        # disable buttons
        self._sg.saup_sequence_PushButton.setEnabled(False)
        self._sg.sauplo_sequence_PushButton.setEnabled(False)
        self._sg.load_sequence_PushButton.setEnabled(False)
        # Sample the sequence via logic module
        self._pulsed_master_logic.sample_sequence(sequence_name, True)
        return

    def generate_predefined_clicked(self, button_obj=None):
        """

        @param button_obj:
        @return:
        """
        if type(button_obj) is bool:
            button_obj = self.sender()
        method_name = button_obj.objectName()
        if method_name.startswith('gen_'):
            method_name = method_name[4:]
        elif method_name.startswith('sauplo_'):
            method_name = method_name[7:]
        else:
            self.log.error('Strange naming of generate buttons in predefined methods occured.')
            return

        # get parameters from input widgets
        param_searchstr = method_name + '_param_'
        param_widgets = [widget for widget in dir(self._pm) if widget.startswith(param_searchstr)]
        # Store parameters together with the parameter names in a dictionary
        param_dict = dict()
        for widget_name in param_widgets:
            input_obj = getattr(self._pm, widget_name)
            param_name = widget_name.replace(param_searchstr, '').replace('_Widget', '')

            if hasattr(input_obj, 'isChecked'):
                param_dict[param_name] = input_obj.isChecked()
            elif hasattr(input_obj, 'value'):
                param_dict[param_name] = input_obj.value()
            elif hasattr(input_obj, 'text'):
                param_dict[param_name] = input_obj.text()
            else:
                self.log.error('Not possible to get the value from the widgets, since it does not '
                               'have one of the possible access methods!')
                return

        # get global parameters and add them to the dictionary
        for param_name in ['mw_channel', 'gate_count_channel', 'sync_trig_channel', 'mw_amp',
                           'mw_freq', 'channel_amp', 'delay_length', 'wait_time', 'laser_length',
                           'rabi_period']:
            input_obj = getattr(self._pm, 'pm_' + param_name + '_Widget')

            if hasattr(input_obj, 'isChecked'):
                param_dict[param_name] = input_obj.isChecked()
            elif hasattr(input_obj, 'value'):
                param_dict[param_name] = input_obj.value()
            elif hasattr(input_obj, 'text'):
                param_dict[param_name] = input_obj.text()
            else:
                self.log.error('Not possible to get the value from the widgets, since it does not '
                               'have one of the possible access methods!')
                return

        self._pulsed_master_logic.generate_predefined_sequence(method_name, param_dict)
        return

    def generate_sauplo_predefined_clicked(self):
        button_obj = self.sender()
        method_name = button_obj.objectName()[7:]
        self.generate_predefined_clicked(button_obj)
        # get name of the generated ensemble
        if not hasattr(self._pm, method_name + '_param_name_Widget'):
            self.log.error('Predefined sequence methods must have an argument called "name" in '
                           'order to use the sample/upload/load functionality. It must be the '
                           'naming of the generated asset.\n"{0}" has probably been generated '
                           'but not sampled/uploaded/loaded'.format(method_name))
            return
        input_obj = getattr(self._pm, method_name + '_param_name_Widget')
        if not hasattr(input_obj, 'text'):
            self.log.error('Predefined sequence methods must have as first argument the name of '
                           'the asset to be generated.')
            return
        asset_name = input_obj.text()

        # disable buttons
        self._pg.saup_ensemble_PushButton.setEnabled(False)
        self._pg.sauplo_ensemble_PushButton.setEnabled(False)
        self._pg.load_ensemble_PushButton.setEnabled(False)

        self._pulsed_master_logic.sample_block_ensemble(asset_name, True)
        return

    ###########################################################################
    ###        Methods related to Settings for the 'Analysis' Tab:          ###
    ###########################################################################
    #FIXME: Implement the setting for 'Analysis' tab.
    def _activate_analysis_settings_ui(self):
        """ Initialize, connect and configure the Settings of 'Analysis' Tab.
        """
        self._as = AnalysisSettingDialog()
        self._as.accepted.connect(self.update_analysis_settings)
        self._as.rejected.connect(self.keep_former_analysis_settings)
        self._as.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.update_analysis_settings)

        self._as.ana_param_x_axis_name_LineEdit.setText(self._ana_param_x_axis_name_text)
        self._as.ana_param_x_axis_unit_LineEdit.setText(self._ana_param_x_axis_unit_text)
        self._as.ana_param_y_axis_name_LineEdit.setText(self._ana_param_y_axis_name_text)
        self._as.ana_param_y_axis_unit_LineEdit.setText(self._ana_param_y_axis_unit_text)
        self._as.ana_param_second_plot_x_axis_name_LineEdit.setText(self._ana_param_second_plot_x_axis_name_text)
        self._as.ana_param_second_plot_x_axis_unit_LineEdit.setText(self._ana_param_second_plot_x_axis_unit_text)
        self._as.ana_param_second_plot_y_axis_name_LineEdit.setText(self._ana_param_second_plot_y_axis_name_text)
        self._as.ana_param_second_plot_y_axis_unit_LineEdit.setText(self._ana_param_second_plot_y_axis_unit_text)
        self._as.ana_param_couple_settings_checkBox.setChecked(self._pulsed_master_logic.couple_generator_hw)
        self.update_analysis_settings()
        return

    def _deactivate_analysis_settings_ui(self):
        """ Disconnects the configuration of the Settings for 'Analysis' Tab.
        """
        # FIXME: disconnect something
        return

    def update_analysis_settings(self):
        """ Apply the new settings """
        self._ana_param_x_axis_name_text = self._as.ana_param_x_axis_name_LineEdit.text()
        self._ana_param_x_axis_unit_text = self._as.ana_param_x_axis_unit_LineEdit.text()
        self._ana_param_y_axis_name_text = self._as.ana_param_y_axis_name_LineEdit.text()
        self._ana_param_y_axis_unit_text = self._as.ana_param_y_axis_unit_LineEdit.text()
        self._ana_param_second_plot_x_axis_name_text = self._as.ana_param_second_plot_x_axis_name_LineEdit.text()
        self._ana_param_second_plot_x_axis_unit_text = self._as.ana_param_second_plot_x_axis_unit_LineEdit.text()
        self._ana_param_second_plot_y_axis_name_text = self._as.ana_param_second_plot_y_axis_name_LineEdit.text()
        self._ana_param_second_plot_y_axis_unit_text = self._as.ana_param_second_plot_y_axis_unit_LineEdit.text()

        self._pa.pulse_analysis_PlotWidget.setLabel(
            axis='bottom',
            text=self._ana_param_x_axis_name_text,
            units=self._ana_param_x_axis_unit_text)
        self._pa.pulse_analysis_PlotWidget.setLabel(
            axis='left',
            text=self._ana_param_y_axis_name_text,
            units=self._ana_param_y_axis_unit_text)
        self._pa.pulse_analysis_second_PlotWidget.setLabel(
            axis='bottom',
            text=self._ana_param_second_plot_x_axis_name_text,
            units=self._ana_param_second_plot_x_axis_unit_text)
        self._pa.pulse_analysis_second_PlotWidget.setLabel(
            axis='left',
            text=self._ana_param_second_plot_y_axis_name_text,
            units=self._ana_param_second_plot_y_axis_unit_text)
        self._pe.measuring_error_PlotWidget.setLabel(
            axis='bottom',
            text=self._ana_param_x_axis_name_text,
            units=self._ana_param_x_axis_unit_text)

        couple_settings = self._as.ana_param_couple_settings_checkBox.isChecked()
        self._pulsed_master_logic.couple_generator_hw = couple_settings
        if couple_settings:
            self._pg.gen_sample_freq_DSpinBox.blockSignals(True)
            self._pg.gen_activation_config_ComboBox.blockSignals(True)
            self._pg.gen_sample_freq_DSpinBox.setEnabled(False)
            self._pg.gen_activation_config_ComboBox.setEnabled(False)
        else:
            self._pg.gen_sample_freq_DSpinBox.blockSignals(False)
            self._pg.gen_activation_config_ComboBox.blockSignals(False)
            self._pg.gen_sample_freq_DSpinBox.setEnabled(True)
            self._pg.gen_activation_config_ComboBox.setEnabled(True)
        # FIXME: Not very elegant
        self._pulsed_master_logic._measurement_logic.fc.set_units(
            [self._ana_param_x_axis_unit_text, self._ana_param_y_axis_unit_text])
        return

    def keep_former_analysis_settings(self):
        """ Keep the old settings """
        #FIXME: Implement the behaviour
        pass

    def show_analysis_settings(self):
        """ Open the Analysis Settings Window. """
        self._as.exec_()
        return

    ###########################################################################
    ###     Methods related to the Tab 'Analysis' in the Pulsed Window:     ###
    ###########################################################################
    def setup_toolbar(self):
        # create all the needed control widgets on the fly and connect their
        # actions to each other:
        self._mw.pulser_on_off_PushButton = QtWidgets.QPushButton()
        self._mw.pulser_on_off_PushButton.setText('Pulser ON')
        self._mw.pulser_on_off_PushButton.setToolTip('Switch the device on and off.')
        self._mw.pulser_on_off_PushButton.setCheckable(True)
        self._mw.control_ToolBar.addWidget(self._mw.pulser_on_off_PushButton)

        self._mw.clear_device_PushButton = QtWidgets.QPushButton(self._mw)
        self._mw.clear_device_PushButton.setText('Clear Pulser')
        self._mw.clear_device_PushButton.setToolTip(
            'Clear the Pulser Device Memory\nfrom all loaded files.')
        self._mw.control_ToolBar.addWidget(self._mw.clear_device_PushButton)

        self._mw.current_loaded_asset_Label = QtWidgets.QLabel(self._mw)
        sizepolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                           QtWidgets.QSizePolicy.Fixed)
        sizepolicy.setHorizontalStretch(0)
        sizepolicy.setVerticalStretch(0)
        sizepolicy.setHeightForWidth(
            self._mw.current_loaded_asset_Label.sizePolicy().hasHeightForWidth())
        self._mw.current_loaded_asset_Label.setSizePolicy(sizepolicy)
        self._mw.current_loaded_asset_Label.setText('  No Asset Loaded')
        self._mw.current_loaded_asset_Label.setToolTip('Display the currently loaded asset.')
        self._mw.control_ToolBar.addWidget(self._mw.current_loaded_asset_Label)

        self._mw.save_tag_LineEdit = QtWidgets.QLineEdit()
        self._mw.save_tag_LineEdit.setMaximumWidth(200)
        self._mw.save_ToolBar.addWidget(self._mw.save_tag_LineEdit)

    def setup_extraction_ui(self):
        self.lasertrace_image = pg.PlotDataItem(np.array(range(10)), np.zeros(10), pen=palette.c1)
        self._pe.laserpulses_PlotWidget.addItem(self.lasertrace_image)
        self._pe.laserpulses_PlotWidget.addItem(self.sig_start_line)
        self._pe.laserpulses_PlotWidget.addItem(self.sig_end_line)
        self._pe.laserpulses_PlotWidget.addItem(self.ref_start_line)
        self._pe.laserpulses_PlotWidget.addItem(self.ref_end_line)
        self._pe.laserpulses_PlotWidget.setLabel(axis='bottom', text='time', units='s')

    def _activate_analysis_ui(self):
        """ Initialize, connect and configure the 'Analysis' Tab.
        """
        self._pa.ana_param_errorbars_CheckBox.setChecked(self._ana_param_errorbars)
        index = self._pa.second_plot_ComboBox.findText(self._second_plot_ComboBox_text)
        self._pa.second_plot_ComboBox.setCurrentIndex(index)

        self._pa.ana_param_invoke_settings_CheckBox.setChecked(
            self._pulsed_master_logic.invoke_settings)

        # Fit settings dialog
        self._fsd = FitSettingsDialog(self._pulsed_master_logic._measurement_logic.fc)
        self._fsd.sigFitsUpdated.connect(self._pa.fit_param_fit_func_ComboBox.setFitFunctions)
        self._fsd.applySettings()

        # Configure the main pulse analysis display:
        self.signal_image = pg.PlotDataItem(np.array(range(10)),
                                            np.zeros(10),
                                            pen=pg.mkPen(palette.c1,
                                                         style=QtCore.Qt.DotLine),
                                            style=QtCore.Qt.DotLine,
                                            symbol='o',
                                            symbolPen=palette.c1,
                                            symbolBrush=palette.c1,
                                            symbolSize=7)

        self._pa.pulse_analysis_PlotWidget.addItem(self.signal_image)
        self.signal_image2 = pg.PlotDataItem(pen=pg.mkPen(palette.c4,
                                                          style=QtCore.Qt.DotLine),
                                             style=QtCore.Qt.DotLine,
                                             symbol='o',
                                             symbolPen=palette.c4,
                                             symbolBrush=palette.c4,
                                             symbolSize=7)
        self._pa.pulse_analysis_PlotWidget.addItem(self.signal_image2)
        self._pa.pulse_analysis_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        # Configure the fit of the data in the main pulse analysis display:
        self.fit_image = pg.PlotDataItem(pen=palette.c3)
        self._pa.pulse_analysis_PlotWidget.addItem(self.fit_image)

        # Configure the errorbars of the data in the main pulse analysis display:
        self.signal_image_error_bars = pg.ErrorBarItem(x=np.array(range(10)),
                                                       y=np.zeros(10),
                                                       top=0., bottom=0.,
                                                       pen=palette.c2)
        self.signal_image_error_bars2 = pg.ErrorBarItem(x=np.array(range(10)),
                                                        y=np.zeros(10),
                                                        top=0., bottom=0.,
                                                        pen=palette.c5)

        # Configure the second pulse analysis display:
        self.second_plot_image = pg.PlotDataItem(np.array(range(10)),
                                                 np.zeros(10), pen=palette.c1)
        self._pa.pulse_analysis_second_PlotWidget.addItem(self.second_plot_image)
        self.second_plot_image2 = pg.PlotDataItem(pen=palette.c4)
        self._pa.pulse_analysis_second_PlotWidget.addItem(self.second_plot_image2)
        self._pa.pulse_analysis_second_PlotWidget.showGrid(x=True, y=True,
                                                           alpha=0.8)

        # Configure the lasertrace plot display:
        self.sig_start_line = pg.InfiniteLine(pos=0,
                                              pen=QtGui.QPen(palette.c3, 5e-9),
                                              movable=True)
        #self.sig_start_line.setHoverPen(QtGui.QPen(palette.c3), width=10)
        self.sig_end_line = pg.InfiniteLine(pos=0,
                                            pen=QtGui.QPen(palette.c3, 5e-9),
                                            movable=True)
        #self.sig_end_line.setHoverPen(QtGui.QPen(palette.c3), width=10)
        self.ref_start_line = pg.InfiniteLine(pos=0,
                                              pen=QtGui.QPen(palettedark.c4, 5e-9),
                                              movable=True)
        #self.ref_start_line.setHoverPen(QtGui.QPen(palette.c4), width=10)
        self.ref_end_line = pg.InfiniteLine(pos=0,
                                            pen=QtGui.QPen(palettedark.c4, 5e-9),
                                            movable=True)
        #self.ref_end_line.setHoverPen(QtGui.QPen(palette.c4), width=10)
        # Configure the measuring error display:
        self.measuring_error_image = pg.PlotDataItem(np.array(range(10)),
                                                     np.zeros(10),
                                                     pen=palette.c1)
        self.measuring_error_image2 = pg.PlotDataItem(np.array(range(10)),
                                                      np.zeros(10),
                                                      pen=palette.c3)
        self._pe.measuring_error_PlotWidget.addItem(self.measuring_error_image)
        self._pe.measuring_error_PlotWidget.addItem(self.measuring_error_image2)
        self._pe.measuring_error_PlotWidget.setLabel('left', 'measuring error',
                                                     units='a.u.')
        #self._pe.measuring_error_PlotWidget.setLabel('bottom', 'tau', units='s')


        # set boundaries
        self._pe.extract_param_conv_std_dev_slider.setRange(1, 200)
        self._pe.extract_param_conv_std_dev_DSpinBox.setRange(1, 200)
        self._pa.ana_param_x_axis_start_ScienDSpinBox.setRange(0, 1.0e99)
        self._pa.ana_param_x_axis_inc_ScienDSpinBox.setRange(0, 1.0e99)
        self._pa.ana_param_num_laser_pulse_SpinBox.setRange(1, 1e6)
        self._pa.ana_param_record_length_SpinBox.setRange(0, 1.0e99)
        self._pa.time_param_ana_periode_DoubleSpinBox.setRange(0, 1.0e99)
        self._pa.ext_control_mw_freq_DoubleSpinBox.setRange(0, 1.0e99)
        self._pa.ext_control_mw_power_DoubleSpinBox.setRange(-200, 1.0e99)
        self._pe.extract_param_threshold_SpinBox.setRange(1, 2**31-1)

        # ---------------------------------------------------------------------
        #                         Connect signals
        # ---------------------------------------------------------------------
        # connect update signals from logic
        self._pulsed_master_logic.sigSignalDataUpdated.connect(self.signal_data_updated)
        self._pulsed_master_logic.sigLaserDataUpdated.connect(self.laser_data_updated)
        self._pulsed_master_logic.sigLaserToShowUpdated.connect(self.laser_to_show_updated)
        self._pulsed_master_logic.sigElapsedTimeUpdated.connect(self.elapsed_time_updated)
        self._pulsed_master_logic.sigFitUpdated.connect(self.fit_data_updated)
        self._pulsed_master_logic.sigMeasurementStatusUpdated.connect(self.measurement_status_updated)
        self._pulsed_master_logic.sigPulserRunningUpdated.connect(self.pulser_running_updated)
        self._pulsed_master_logic.sigFastCounterSettingsUpdated.connect(self.fast_counter_settings_updated)
        self._pulsed_master_logic.sigMeasurementSequenceSettingsUpdated.connect(self.measurement_sequence_settings_updated)
        self._pulsed_master_logic.sigPulserSettingsUpdated.connect(self.pulse_generator_settings_updated)
        self._pulsed_master_logic.sigUploadedAssetsUpdated.connect(self.update_uploaded_assets)
        self._pulsed_master_logic.sigLoadedAssetUpdated.connect(self.update_loaded_asset)
        self._pulsed_master_logic.sigExtMicrowaveSettingsUpdated.connect(self.microwave_settings_updated)
        self._pulsed_master_logic.sigExtMicrowaveRunningUpdated.connect(self.microwave_running_updated)
        self._pulsed_master_logic.sigTimerIntervalUpdated.connect(self.measurement_timer_updated)
        self._pulsed_master_logic.sigAnalysisSettingsUpdated.connect(self.analysis_settings_updated)
        self._pulsed_master_logic.sigAnalysisMethodsUpdated.connect(self.analysis_methods_updated)
        self._pulsed_master_logic.sigExtractionSettingsUpdated.connect(self.extraction_settings_updated)
        self._pulsed_master_logic.sigExtractionMethodsUpdated.connect(self.extraction_methods_updated)

        # connect button click signals
        self._pg.load_ensemble_PushButton.clicked.connect(self.load_ensemble_clicked)
        self._sg.load_sequence_PushButton.clicked.connect(self.load_sequence_clicked)
        self._mw.pulser_on_off_PushButton.clicked.connect(self.pulser_on_off_clicked)
        self._mw.clear_device_PushButton.clicked.connect(self.clear_pulser_clicked)
        self._pa.fit_param_PushButton.clicked.connect(self.fit_clicked)

        # connect action trigger signals
        self._mw.action_run_stop.triggered.connect(self.measurement_run_stop_clicked)
        self._mw.action_continue_pause.triggered.connect(self.measurement_continue_pause_clicked)
        self._mw.action_pull_data.triggered.connect(self.pull_data_clicked)
        self._mw.action_save.triggered.connect(self.save_clicked)
        self._mw.action_Settings_Analysis.triggered.connect(self.show_analysis_settings)
        self._mw.action_FitSettings.triggered.connect(self._fsd.show)

        # connect checkbox click signals
        self._pa.ext_control_use_mw_CheckBox.stateChanged.connect(self.ext_mw_params_changed)
        self._pa.ana_param_invoke_settings_CheckBox.stateChanged.connect(self.toggle_settings_editor)
        self._pa.ana_param_alternating_CheckBox.stateChanged.connect(self.measurement_sequence_settings_changed)
        self._pa.ana_param_ignore_first_CheckBox.stateChanged.connect(self.measurement_sequence_settings_changed)
        self._pa.ana_param_ignore_last_CheckBox.stateChanged.connect(self.measurement_sequence_settings_changed)
        self._pe.laserpulses_display_raw_CheckBox.stateChanged.connect(self.laser_to_show_changed)
        self._pa.ana_param_errorbars_CheckBox.stateChanged.connect(self.toggle_error_bars)
        self._pa.pulser_use_interleave_CheckBox.stateChanged.connect(self.pulse_generator_settings_changed)

        # connect spinbox changed signals
        self._pa.ana_param_num_laser_pulse_SpinBox.editingFinished.connect(self.measurement_sequence_settings_changed)
        self._pa.ana_param_record_length_SpinBox.editingFinished.connect(self.fast_counter_settings_changed)
        self._pa.time_param_ana_periode_DoubleSpinBox.editingFinished.connect(self.measurement_timer_changed)
        self._pa.ext_control_mw_freq_DoubleSpinBox.editingFinished.connect(self.ext_mw_params_changed)
        self._pa.ext_control_mw_power_DoubleSpinBox.editingFinished.connect(self.ext_mw_params_changed)
        self._pa.pulser_sample_freq_DSpinBox.editingFinished.connect(self.pulse_generator_settings_changed)
        self._pa.ana_param_x_axis_start_ScienDSpinBox.editingFinished.connect(self.measurement_sequence_settings_changed)
        self._pa.ana_param_x_axis_inc_ScienDSpinBox.editingFinished.connect(self.measurement_sequence_settings_changed)
        self._pe.extract_param_ana_window_start_DSpinBox.editingFinished.connect(self.analysis_settings_changed)
        self._pe.extract_param_ana_window_width_DSpinBox.editingFinished.connect(self.analysis_settings_changed)
        self._pe.extract_param_ref_window_start_DSpinBox.editingFinished.connect(self.analysis_settings_changed)
        self._pe.extract_param_ref_window_width_DSpinBox.editingFinished.connect(self.analysis_settings_changed)
        self._pe.extract_param_conv_std_dev_DSpinBox.editingFinished.connect(self.extraction_settings_changed)
        self._pe.extract_param_threshold_SpinBox.editingFinished.connect(self.extraction_settings_changed)
        self._pe.extract_param_min_laser_length_SpinBox.editingFinished.connect(self.extraction_settings_changed)
        self._pe.extract_param_tolerance_SpinBox.editingFinished.connect(self.extraction_settings_changed)

        # connect combobox changed signals
        self._pa.ana_param_fc_bins_ComboBox.currentIndexChanged.connect(self.fast_counter_settings_changed)
        self._pa.second_plot_ComboBox.currentIndexChanged.connect(self.change_second_plot)
        self._pa.pulser_activation_config_ComboBox.currentIndexChanged.connect(self.pulse_generator_settings_changed)
        self._pe.laserpulses_ComboBox.currentIndexChanged.connect(self.laser_to_show_changed)
        self._pe.extract_param_analysis_method_comboBox.currentIndexChanged.connect(self.analysis_settings_changed)
        self._pe.extract_param_extraction_method_comboBox.currentIndexChanged.connect(self.extraction_settings_changed)

        # connect other widgets changed signals
        self.sig_start_line.sigPositionChangeFinished.connect(self.analysis_settings_changed)
        self.sig_end_line.sigPositionChangeFinished.connect(self.analysis_settings_changed)
        self.ref_start_line.sigPositionChangeFinished.connect(self.analysis_settings_changed)
        self.ref_end_line.sigPositionChangeFinished.connect(self.analysis_settings_changed)
        self._pe.extract_param_conv_std_dev_slider.valueChanged.connect(self.extraction_settings_changed)


        # apply hardware constraints
        self._analysis_apply_hardware_constraints()

        self.toggle_settings_editor()
        self.toggle_error_bars()
        self.change_second_plot()

        # initialize values
        self._pulsed_master_logic.request_measurement_init_values()
        return

    def _deactivate_analysis_ui(self):
        """ Disconnects the configuration for 'Analysis' Tab.
        """
        self.measurement_run_stop_clicked(False)

        self._ana_param_errorbars = self._pa.ana_param_errorbars_CheckBox.isChecked()
        self._second_plot_ComboBox_text = self._pa.second_plot_ComboBox.currentText()

        # disconnect signals
        self._pulsed_master_logic.sigSignalDataUpdated.disconnect()
        self._pulsed_master_logic.sigLaserDataUpdated.disconnect()
        self._pulsed_master_logic.sigLaserToShowUpdated.disconnect()
        self._pulsed_master_logic.sigElapsedTimeUpdated.disconnect()
        self._pulsed_master_logic.sigFitUpdated.disconnect()
        self._pulsed_master_logic.sigMeasurementStatusUpdated.disconnect()
        self._pulsed_master_logic.sigPulserRunningUpdated.disconnect()
        self._pulsed_master_logic.sigFastCounterSettingsUpdated.disconnect()
        self._pulsed_master_logic.sigMeasurementSequenceSettingsUpdated.disconnect()
        self._pulsed_master_logic.sigPulserSettingsUpdated.disconnect()
        self._pulsed_master_logic.sigUploadedAssetsUpdated.disconnect()
        self._pulsed_master_logic.sigLoadedAssetUpdated.disconnect()
        self._pulsed_master_logic.sigExtMicrowaveSettingsUpdated.disconnect()
        self._pulsed_master_logic.sigExtMicrowaveRunningUpdated.disconnect()
        self._pulsed_master_logic.sigTimerIntervalUpdated.disconnect()
        self._pulsed_master_logic.sigAnalysisSettingsUpdated.disconnect()
        self._pulsed_master_logic.sigAnalysisMethodsUpdated.disconnect()
        self._pulsed_master_logic.sigExtractionSettingsUpdated.disconnect()
        self._pulsed_master_logic.sigExtractionMethodsUpdated.disconnect()
        self._pg.load_ensemble_PushButton.clicked.disconnect()
        self._sg.load_sequence_PushButton.clicked.disconnect()
        self._mw.pulser_on_off_PushButton.clicked.disconnect()
        self._mw.clear_device_PushButton.clicked.disconnect()
        self._pa.fit_param_PushButton.clicked.disconnect()
        self._mw.action_run_stop.triggered.disconnect()
        self._mw.action_continue_pause.triggered.disconnect()
        self._mw.action_pull_data.triggered.disconnect()
        self._mw.action_save.triggered.disconnect()
        self._mw.action_Settings_Analysis.triggered.disconnect()
        self._pa.ext_control_use_mw_CheckBox.stateChanged.disconnect()
        self._pa.ana_param_invoke_settings_CheckBox.stateChanged.disconnect()
        self._pa.ana_param_alternating_CheckBox.stateChanged.disconnect()
        self._pa.ana_param_ignore_first_CheckBox.stateChanged.disconnect()
        self._pa.ana_param_ignore_last_CheckBox.stateChanged.disconnect()
        self._pe.laserpulses_display_raw_CheckBox.stateChanged.disconnect()
        self._pa.ana_param_errorbars_CheckBox.stateChanged.disconnect()
        self._pa.pulser_use_interleave_CheckBox.stateChanged.disconnect()
        self._pa.ana_param_num_laser_pulse_SpinBox.editingFinished.disconnect()
        self._pa.ana_param_record_length_SpinBox.editingFinished.disconnect()
        self._pa.time_param_ana_periode_DoubleSpinBox.editingFinished.disconnect()
        self._pa.ext_control_mw_freq_DoubleSpinBox.editingFinished.disconnect()
        self._pa.ext_control_mw_power_DoubleSpinBox.editingFinished.disconnect()
        self._pa.pulser_sample_freq_DSpinBox.editingFinished.disconnect()
        self._pa.ana_param_x_axis_start_ScienDSpinBox.editingFinished.disconnect()
        self._pa.ana_param_x_axis_inc_ScienDSpinBox.editingFinished.disconnect()
        self._pe.extract_param_ana_window_start_DSpinBox.editingFinished.disconnect()
        self._pe.extract_param_ana_window_width_DSpinBox.editingFinished.disconnect()
        self._pe.extract_param_ref_window_start_DSpinBox.editingFinished.disconnect()
        self._pe.extract_param_ref_window_width_DSpinBox.editingFinished.disconnect()
        self._pe.extract_param_conv_std_dev_DSpinBox.editingFinished.disconnect()
        self._pe.extract_param_threshold_SpinBox.editingFinished.disconnect()
        self._pe.extract_param_min_laser_length_SpinBox.editingFinished.disconnect()
        self._pe.extract_param_tolerance_SpinBox.editingFinished.disconnect()
        self._pa.ana_param_fc_bins_ComboBox.currentIndexChanged.disconnect()
        self._pa.second_plot_ComboBox.currentIndexChanged.disconnect()
        self._pa.pulser_activation_config_ComboBox.currentIndexChanged.disconnect()
        self._pe.laserpulses_ComboBox.currentIndexChanged.disconnect()
        self._pe.extract_param_analysis_method_comboBox.currentIndexChanged.disconnect()
        self._pe.extract_param_extraction_method_comboBox.currentIndexChanged.disconnect()
        self.sig_start_line.sigPositionChangeFinished.disconnect()
        self.sig_end_line.sigPositionChangeFinished.disconnect()
        self.ref_start_line.sigPositionChangeFinished.disconnect()
        self.ref_end_line.sigPositionChangeFinished.disconnect()
        self._pe.extract_param_conv_std_dev_slider.valueChanged.disconnect()
        self._fsd.sigFitsUpdated.disconnect()
        return

    def _analysis_apply_hardware_constraints(self):
        """
        Retrieve the constraints from pulser and fast counter hardware and apply these constraints
        to the analysis tab GUI elements.
        """
        # block signals
        self._pa.pulser_activation_config_ComboBox.blockSignals(True)
        self._pa.ana_param_fc_bins_ComboBox.blockSignals(True)
        # apply constraints
        pulser_constr, fastcounter_constr = self._pulsed_master_logic.get_hardware_constraints()
        self._pa.pulser_sample_freq_DSpinBox.setMinimum(pulser_constr.sample_rate.min)
        self._pa.pulser_sample_freq_DSpinBox.setMaximum(pulser_constr.sample_rate.max)
        self._pa.pulser_sample_freq_DSpinBox.setSingleStep(pulser_constr.sample_rate.step)
        self._pa.pulser_activation_config_ComboBox.clear()
        self._pa.pulser_activation_config_ComboBox.addItems(list(pulser_constr.activation_config))
        self._pa.ana_param_fc_bins_ComboBox.clear()
        for binwidth in fastcounter_constr['hardware_binwidth_list']:
            self._pa.ana_param_fc_bins_ComboBox.addItem(str(binwidth))
        # unblock signals
        self._pa.pulser_activation_config_ComboBox.blockSignals(False)
        self._pa.ana_param_fc_bins_ComboBox.blockSignals(False)
        return

    def measurement_run_stop_clicked(self, isChecked):
        """ Manages what happens if pulsed measurement is started or stopped.

        @param bool isChecked: start scan if that is possible
        """
        if isChecked:
            self._pulsed_master_logic.start_measurement()
        else:
            self._pulsed_master_logic.stop_measurement()
        return

    def measurement_continue_pause_clicked(self, isChecked):
        """ Continues and pauses the measurement. """
        if isChecked:
            self._pulsed_master_logic.pause_measurement()
        else:
            self._pulsed_master_logic.continue_measurement()
        return

    def measurement_status_updated(self, is_running, is_paused):
        """

        @param is_running:
        @param is_paused:
        @return:
        """
        # block signals
        self._mw.action_run_stop.blockSignals(True)
        self._mw.action_continue_pause.blockSignals(True)

        # Enable/Disable widgets
        if is_running:
            if self._pa.ext_control_use_mw_CheckBox.isChecked():
                self._pa.ext_control_mw_freq_DoubleSpinBox.setEnabled(False)
                self._pa.ext_control_mw_power_DoubleSpinBox.setEnabled(False)
            if not self._pa.ana_param_invoke_settings_CheckBox.isChecked():
                self._pa.ana_param_x_axis_start_ScienDSpinBox.setEnabled(False)
                self._pa.ana_param_x_axis_inc_ScienDSpinBox.setEnabled(False)
                self._pa.ana_param_num_laser_pulse_SpinBox.setEnabled(False)
                self._pa.ana_param_record_length_SpinBox.setEnabled(False)
            self._pa.ext_control_use_mw_CheckBox.setEnabled(False)
            self._pa.pulser_sample_freq_DSpinBox.setEnabled(False)
            self._pa.pulser_activation_config_ComboBox.setEnabled(False)
            self._pa.ana_param_fc_bins_ComboBox.setEnabled(False)
            self._pa.ana_param_ignore_first_CheckBox.setEnabled(False)
            self._pa.ana_param_ignore_last_CheckBox.setEnabled(False)
            self._pa.ana_param_alternating_CheckBox.setEnabled(False)
            self._pa.ana_param_invoke_settings_CheckBox.setEnabled(False)
            self._pa.pulser_use_interleave_CheckBox.setEnabled(False)
            self._pg.load_ensemble_PushButton.setEnabled(False)
            self._sg.load_sequence_PushButton.setEnabled(False)
            self._mw.pulser_on_off_PushButton.setEnabled(False)
            self._mw.action_continue_pause.setEnabled(True)
            self._mw.action_pull_data.setEnabled(True)
            if not self._mw.action_run_stop.isChecked():
                self._mw.action_run_stop.toggle()
        else:
            self._pa.ext_control_use_mw_CheckBox.setEnabled(True)
            if self._pa.ext_control_use_mw_CheckBox.isChecked():
                self._pa.ext_control_mw_freq_DoubleSpinBox.setEnabled(True)
                self._pa.ext_control_mw_power_DoubleSpinBox.setEnabled(True)
            self._pa.pulser_sample_freq_DSpinBox.setEnabled(True)
            self._pa.pulser_activation_config_ComboBox.setEnabled(True)
            self._pa.ana_param_fc_bins_ComboBox.setEnabled(True)
            self._pa.ana_param_ignore_first_CheckBox.setEnabled(True)
            self._pa.ana_param_ignore_last_CheckBox.setEnabled(True)
            self._pa.ana_param_alternating_CheckBox.setEnabled(True)
            self._pa.ana_param_invoke_settings_CheckBox.setEnabled(True)
            self._pa.pulser_use_interleave_CheckBox.setEnabled(True)
            if not self._pa.ana_param_invoke_settings_CheckBox.isChecked():
                self._pa.ana_param_x_axis_start_ScienDSpinBox.setEnabled(True)
                self._pa.ana_param_x_axis_inc_ScienDSpinBox.setEnabled(True)
                self._pa.ana_param_num_laser_pulse_SpinBox.setEnabled(True)
                self._pa.ana_param_record_length_SpinBox.setEnabled(True)
            self._pg.load_ensemble_PushButton.setEnabled(True)
            self._sg.load_sequence_PushButton.setEnabled(True)
            self._mw.pulser_on_off_PushButton.setEnabled(True)
            self._mw.action_continue_pause.setEnabled(False)
            self._mw.action_pull_data.setEnabled(False)
            if self._mw.action_run_stop.isChecked():
                self._mw.action_run_stop.toggle()
        if is_paused:
            if not self._mw.action_continue_pause.isChecked():
                self._mw.action_continue_pause.toggle()
        else:
            if self._mw.action_continue_pause.isChecked():
                self._mw.action_continue_pause.toggle()
        # unblock signals
        self._mw.action_run_stop.blockSignals(False)
        self._mw.action_continue_pause.blockSignals(False)
        return

    def pull_data_clicked(self):
        """ Pulls and analysis the data when the 'action_pull_data'-button is clicked. """
        self._pulsed_master_logic.manually_pull_data()
        return

    def signal_data_updated(self, x_data, y_signal_data, y2_signal_data, y_error_data,
                            y2_error_data, fft_x_data, fft_y_data, fft_y2_data):
        """

        @param x_data:
        @param y_signal_data:
        @param y2_signal_data:
        @param y_error_data:
        @param y2_error_data:
        @return:
        """
        is_alternating = self._pa.ana_param_alternating_CheckBox.isChecked()
        if self._pa.second_plot_ComboBox.currentText() == 'FFT':
            is_fft = True
        else:
            is_fft = False

        # create ErrorBarItems
        beamwidth = np.inf
        for i in range(len(x_data) - 1):
            width = x_data[i + 1] - x_data[i]
            width = width / 3
            if width <= beamwidth:
                beamwidth = width
        self.signal_image_error_bars.setData(x=x_data, y=y_signal_data, top=y_error_data,
                                             bottom=y_error_data, beam=beamwidth)
        if is_alternating:
            self.signal_image_error_bars2.setData(x=x_data, y=y2_signal_data, top=y2_error_data,
                                                  bottom=y2_error_data, beam=beamwidth)
        # dealing with the actual signal plot
        self.signal_image.setData(x=x_data, y=y_signal_data)
        if is_alternating:
            self.signal_image2.setData(x=x_data, y=y2_signal_data)

        # dealing with the secondary plot
        if is_fft:
            self.second_plot_image.setData(x=fft_x_data, y=fft_y_data)
        else:
            self.second_plot_image.setData(x=x_data, y=y_signal_data)
        if is_alternating:
            if is_fft:
                self.second_plot_image2.setData(x=fft_x_data, y=fft_y2_data)
            else:
                self.second_plot_image2.setData(x=x_data, y=y2_signal_data)

        # dealing with the error plot
        self.measuring_error_image.setData(x=x_data, y=y_error_data)
        if is_alternating:
            self.measuring_error_image2.setData(x=x_data, y=y2_error_data)
        return

    def save_clicked(self):
        """Saves the current data"""
        self._mw.action_save.setEnabled(False)
        save_tag = self._mw.save_tag_LineEdit.text()
        with_error = self._pa.ana_param_errorbars_CheckBox.isChecked()
        controlled_val_unit = self._as.ana_param_x_axis_unit_LineEdit.text()
        if self._pa.second_plot_ComboBox.currentText() == 'None':
            save_ft = True
        else:
            save_ft = False
        self._pulsed_master_logic.save_measurement_data(controlled_val_unit=controlled_val_unit,
                                                        tag=save_tag,
                                                        with_error=with_error,
                                                        save_ft=save_ft)
        self._mw.action_save.setEnabled(True)
        return

    def fit_clicked(self):
        """Fits the current data"""
        current_fit_method = self._pa.fit_param_fit_func_ComboBox.getCurrentFit()[0]
        self._pulsed_master_logic.do_fit(current_fit_method)
        return

    def fit_data_updated(self, fit_method, fit_data_x, fit_data_y, result_dict):
        """

        @param fit_method:
        @param fit_data_x:
        @param fit_data_y:
        @param result_dict:
        @return:
        """
        # block signals
        self._pa.fit_param_fit_func_ComboBox.blockSignals(True)
        # set widgets
        self._pa.fit_param_results_TextBrowser.clear()
        if fit_method == 'No Fit':
            formatted_fitresult = 'No Fit'
        else:
            try:
                formatted_fitresult = units.create_formatted_output(result_dict.result_str_dict)
            except:
                formatted_fitresult = 'This fit does not return formatted results'
        self._pa.fit_param_results_TextBrowser.setPlainText(formatted_fitresult)

        self.fit_image.setData(x=fit_data_x, y=fit_data_y)
        if fit_method == 'No Fit' and self.fit_image in self._pa.pulse_analysis_PlotWidget.items():
            self._pa.pulse_analysis_PlotWidget.removeItem(self.fit_image)
        elif fit_method != 'No Fit' and self.fit_image not in self._pa.pulse_analysis_PlotWidget.items():
            self._pa.pulse_analysis_PlotWidget.addItem(self.fit_image)
        if fit_method is not None:
            self._pa.fit_param_fit_func_ComboBox.setCurrentFit(fit_method)
        # unblock signals
        self._pa.fit_param_fit_func_ComboBox.blockSignals(False)
        return

    def elapsed_time_updated(self, elapsed_time, elapsed_time_str):
        """
        Refreshes the elapsed time and sweeps of the measurement.

        @param elapsed_time:
        @param elapsed_time_str:
        @return:
        """
        # block signals
        self._pa.time_param_elapsed_time_LineEdit.blockSignals(True)
        # Set widgets
        self._pa.time_param_elapsed_time_LineEdit.setText(elapsed_time_str)
        # unblock signals
        self._pa.time_param_elapsed_time_LineEdit.blockSignals(True)
        return

    def ext_mw_params_changed(self):
        """ Shows or hides input widgets which are necessary if an external mw is turned on"""
        if self._mw.action_run_stop.isChecked():
            return
        use_ext_microwave = self._pa.ext_control_use_mw_CheckBox.isChecked()
        microwave_freq = self._pa.ext_control_mw_freq_DoubleSpinBox.value()
        microwave_power = self._pa.ext_control_mw_power_DoubleSpinBox.value()
        if use_ext_microwave and not self._pa.ext_control_mw_freq_DoubleSpinBox.isVisible():
            self._pa.ext_control_mw_freq_Label.setVisible(True)
            self._pa.ext_control_mw_freq_DoubleSpinBox.setVisible(True)
            self._pa.ext_control_mw_power_Label.setVisible(True)
            self._pa.ext_control_mw_power_DoubleSpinBox.setVisible(True)
            self._pa.ext_control_mw_freq_DoubleSpinBox.setEnabled(True)
            self._pa.ext_control_mw_power_DoubleSpinBox.setEnabled(True)
        elif not use_ext_microwave and self._pa.ext_control_mw_freq_DoubleSpinBox.isVisible():
            self._pa.ext_control_mw_freq_DoubleSpinBox.setEnabled(False)
            self._pa.ext_control_mw_power_DoubleSpinBox.setEnabled(False)
            self._pa.ext_control_mw_freq_Label.setVisible(False)
            self._pa.ext_control_mw_freq_DoubleSpinBox.setVisible(False)
            self._pa.ext_control_mw_power_Label.setVisible(False)
            self._pa.ext_control_mw_power_DoubleSpinBox.setVisible(False)

        self._pulsed_master_logic.ext_microwave_settings_changed(microwave_freq, microwave_power,
                                                                 use_ext_microwave)
        return

    def microwave_settings_updated(self, frequency, power, use_ext_microwave):
        """

        @param frequency:
        @param power:
        @param use_ext_microwave:
        @return:
        """
        # set visibility
        if use_ext_microwave and not self._pa.ext_control_mw_freq_DoubleSpinBox.isVisible():
            self._pa.ext_control_mw_freq_Label.setVisible(True)
            self._pa.ext_control_mw_freq_DoubleSpinBox.setVisible(True)
            self._pa.ext_control_mw_power_Label.setVisible(True)
            self._pa.ext_control_mw_power_DoubleSpinBox.setVisible(True)
            self._pa.ext_control_mw_freq_DoubleSpinBox.setEnabled(True)
            self._pa.ext_control_mw_power_DoubleSpinBox.setEnabled(True)
        elif not use_ext_microwave and self._pa.ext_control_mw_freq_DoubleSpinBox.isVisible():
            self._pa.ext_control_mw_freq_DoubleSpinBox.setEnabled(False)
            self._pa.ext_control_mw_power_DoubleSpinBox.setEnabled(False)
            self._pa.ext_control_mw_freq_Label.setVisible(False)
            self._pa.ext_control_mw_freq_DoubleSpinBox.setVisible(False)
            self._pa.ext_control_mw_power_Label.setVisible(False)
            self._pa.ext_control_mw_power_DoubleSpinBox.setVisible(False)
        # block signals
        self._pa.ext_control_mw_freq_DoubleSpinBox.blockSignals(True)
        self._pa.ext_control_mw_power_DoubleSpinBox.blockSignals(True)
        self._pa.ext_control_use_mw_CheckBox.blockSignals(True)
        # set widgets
        self._pa.ext_control_mw_freq_DoubleSpinBox.setValue(frequency)
        self._pa.ext_control_mw_power_DoubleSpinBox.setValue(power)
        self._pa.ext_control_use_mw_CheckBox.setChecked(use_ext_microwave)
        # unblock signals
        self._pa.ext_control_mw_freq_DoubleSpinBox.blockSignals(False)
        self._pa.ext_control_mw_power_DoubleSpinBox.blockSignals(False)
        self._pa.ext_control_use_mw_CheckBox.blockSignals(False)
        return

    def microwave_running_updated(self, is_running):
        """

        @return:
        """
        pass

    def pulse_generator_settings_changed(self):
        """

        @return:
        """
        if self._mw.action_run_stop.isChecked():
            return
        # FIXME: Properly implement amplitude and interleave
        sample_rate_hz = self._pa.pulser_sample_freq_DSpinBox.value()
        activation_config_name = self._pa.pulser_activation_config_ComboBox.currentText()
        analogue_amplitude, dummy = self._pulsed_master_logic._measurement_logic._pulse_generator_device.get_analog_level()
        interleave_on = self._pa.pulser_use_interleave_CheckBox.isChecked()
        self._pulsed_master_logic.pulse_generator_settings_changed(sample_rate_hz,
                                                                   activation_config_name,
                                                                   analogue_amplitude,
                                                                   interleave_on)
        return

    def pulse_generator_settings_updated(self, sample_rate_hz, activation_config_name,
                                         activation_config, analogue_amplitude, interleave_on):
        """

        @param sample_rate_hz:
        @param activation_config_name:
        @param analogue_amplitude:
        @param interleave_on:
        @return:
        """
        # block signals
        self._pa.pulser_sample_freq_DSpinBox.blockSignals(True)
        self._pa.pulser_activation_config_ComboBox.blockSignals(True)
        self._pa.pulser_activation_config_LineEdit.blockSignals(True)
        self._pa.pulser_use_interleave_CheckBox.blockSignals(True)
        # Set widgets
        # FIXME: Properly implement amplitude and interleave
        self._pa.pulser_sample_freq_DSpinBox.setValue(sample_rate_hz)
        index = self._pa.pulser_activation_config_ComboBox.findText(activation_config_name)
        self._pa.pulser_activation_config_ComboBox.setCurrentIndex(index)
        config_display_str = ''
        for channel in activation_config:
            config_display_str += channel + ' | '
        config_display_str = config_display_str[:-3]
        self._pa.pulser_activation_config_LineEdit.setText(config_display_str)
        self._pa.pulser_use_interleave_CheckBox.setChecked(interleave_on)
        # unblock signals
        self._pa.pulser_sample_freq_DSpinBox.blockSignals(False)
        self._pa.pulser_activation_config_ComboBox.blockSignals(False)
        self._pa.pulser_activation_config_LineEdit.blockSignals(False)
        self._pa.pulser_use_interleave_CheckBox.blockSignals(False)
        return

    def fast_counter_settings_changed(self):
        """

        @return:
        """
        if self._mw.action_run_stop.isChecked():
            return
        record_length_s = self._pa.ana_param_record_length_SpinBox.value()
        bin_width_s = float(self._pa.ana_param_fc_bins_ComboBox.currentText())
        self._pulsed_master_logic.fast_counter_settings_changed(bin_width_s, record_length_s)
        return

    def fast_counter_settings_updated(self, bin_width_s, record_length_s):
        """

        @param bin_width_s:
        @param record_length_s:
        @return:
        """
        # block signals
        self._pa.ana_param_record_length_SpinBox.blockSignals(True)
        self._pa.ana_param_fc_bins_ComboBox.blockSignals(True)
        # set widgets
        self._pa.ana_param_record_length_SpinBox.setValue(record_length_s)
        index = self._pa.ana_param_fc_bins_ComboBox.findText(str(bin_width_s))
        self._pa.ana_param_fc_bins_ComboBox.setCurrentIndex(index)
        # unblock signals
        self._pa.ana_param_record_length_SpinBox.blockSignals(False)
        self._pa.ana_param_fc_bins_ComboBox.blockSignals(False)
        return

    def measurement_sequence_settings_changed(self):
        """

        @return:
        """

        if self._mw.action_run_stop.isChecked():
            return
        laser_ignore_list = []
        if self._pa.ana_param_ignore_first_CheckBox.isChecked():
            laser_ignore_list.append(0)
        if self._pa.ana_param_ignore_last_CheckBox.isChecked():
            laser_ignore_list.append(-1)
        alternating = self._pa.ana_param_alternating_CheckBox.isChecked()
        num_of_lasers = self._pa.ana_param_num_laser_pulse_SpinBox.value()
        controlled_vals_start = self._pa.ana_param_x_axis_start_ScienDSpinBox.value()
        controlled_vals_incr = self._pa.ana_param_x_axis_inc_ScienDSpinBox.value()
        # FIXME: properly implement sequence_length_s
        sequence_length_s = self._pulsed_master_logic._measurement_logic.sequence_length_s
        num_of_ticks = num_of_lasers - len(laser_ignore_list)
        if alternating:
            num_of_ticks //= 2
        controlled_vals = np.arange(controlled_vals_start,
                                    controlled_vals_start + (controlled_vals_incr * num_of_ticks) - (controlled_vals_incr / 2),
                                    controlled_vals_incr)

        self._pulsed_master_logic.measurement_sequence_settings_changed(controlled_vals,
                                                                        num_of_lasers,
                                                                        sequence_length_s,
                                                                        laser_ignore_list,
                                                                        alternating)
        return

    def measurement_sequence_settings_updated(self, controlled_vals, number_of_lasers,
                                              sequence_length_s, laser_ignore_list, alternating):
        """

        @param controlled_vals:
        @param number_of_lasers:
        @param sequence_length_s:
        @param laser_ignore_list:
        @param alternating:
        @return:
        """
        # block signals
        self._pa.ana_param_ignore_first_CheckBox.blockSignals(True)
        self._pa.ana_param_ignore_last_CheckBox.blockSignals(True)
        self._pa.ana_param_alternating_CheckBox.blockSignals(True)
        self._pa.ana_param_num_laser_pulse_SpinBox.blockSignals(True)
        self._pa.ana_param_x_axis_start_ScienDSpinBox.blockSignals(True)
        self._pa.ana_param_x_axis_inc_ScienDSpinBox.blockSignals(True)
        self._pe.laserpulses_ComboBox.blockSignals(True)
        # set widgets
        self._pa.ana_param_ignore_first_CheckBox.setChecked(0 in laser_ignore_list)
        self._pa.ana_param_ignore_last_CheckBox.setChecked(-1 in laser_ignore_list)
        self._pa.ana_param_alternating_CheckBox.setChecked(alternating)
        self._pa.ana_param_num_laser_pulse_SpinBox.setValue(number_of_lasers)
        self._pa.ana_param_x_axis_start_ScienDSpinBox.setValue(controlled_vals[0])
        if len(controlled_vals) > 1:
            self._pa.ana_param_x_axis_inc_ScienDSpinBox.setValue(
                (controlled_vals[-1] - controlled_vals[0]) / (len(controlled_vals)-1))
        elif controlled_vals[0] > 0.0:
            self._pa.ana_param_x_axis_inc_ScienDSpinBox.setValue(controlled_vals[0])
        else:
            self._pa.ana_param_x_axis_inc_ScienDSpinBox.setValue(1.0)
        self._pe.laserpulses_ComboBox.clear()
        self._pe.laserpulses_ComboBox.addItem('sum')
        self._pe.laserpulses_ComboBox.addItems([str(i) for i in range(1, number_of_lasers+1)])
        # change plots accordingly
        if alternating:
            if self.signal_image2 not in self._pa.pulse_analysis_PlotWidget.items():
                self._pa.pulse_analysis_PlotWidget.addItem(self.signal_image2)
            if self.signal_image_error_bars in self._pa.pulse_analysis_PlotWidget.items() and self.signal_image_error_bars2 not in self._pa.pulse_analysis_PlotWidget.items():
                self._pa.pulse_analysis_PlotWidget.addItem(self.signal_image_error_bars2)
            if self.measuring_error_image2 not in self._pe.measuring_error_PlotWidget.items():
                self._pe.measuring_error_PlotWidget.addItem(self.measuring_error_image2)
            if self.second_plot_image2 not in self._pa.pulse_analysis_second_PlotWidget.items():
                self._pa.pulse_analysis_second_PlotWidget.addItem(self.second_plot_image2)
        else:
            if self.signal_image2 in self._pa.pulse_analysis_PlotWidget.items():
                self._pa.pulse_analysis_PlotWidget.removeItem(self.signal_image2)
            if self.signal_image_error_bars2 in self._pa.pulse_analysis_PlotWidget.items():
                self._pa.pulse_analysis_PlotWidget.removeItem(self.signal_image_error_bars2)
            if self.measuring_error_image2 in self._pe.measuring_error_PlotWidget.items():
                self._pe.measuring_error_PlotWidget.removeItem(self.measuring_error_image2)
            if self.second_plot_image2 in self._pa.pulse_analysis_second_PlotWidget.items():
                self._pa.pulse_analysis_second_PlotWidget.removeItem(self.second_plot_image2)
        # unblock signals
        self._pa.ana_param_ignore_first_CheckBox.blockSignals(False)
        self._pa.ana_param_ignore_last_CheckBox.blockSignals(False)
        self._pa.ana_param_alternating_CheckBox.blockSignals(False)
        self._pa.ana_param_num_laser_pulse_SpinBox.blockSignals(False)
        self._pa.ana_param_x_axis_start_ScienDSpinBox.blockSignals(False)
        self._pa.ana_param_x_axis_inc_ScienDSpinBox.blockSignals(False)
        self._pe.laserpulses_ComboBox.blockSignals(False)
        return

    def toggle_settings_editor(self):
        """
        Shows or hides input widgets which are necessary if the x axis id defined or not.
        """
        invoke_checked = self._pa.ana_param_invoke_settings_CheckBox.isChecked()
        if not invoke_checked:
            self._pa.ana_param_x_axis_start_ScienDSpinBox.setEnabled(True)
            self._pa.ana_param_x_axis_inc_ScienDSpinBox.setEnabled(True)
            self._pa.ana_param_num_laser_pulse_SpinBox.setEnabled(True)
            self._pa.ana_param_record_length_SpinBox.setEnabled(True)
        else:
            self._pa.ana_param_x_axis_start_ScienDSpinBox.setEnabled(False)
            self._pa.ana_param_x_axis_inc_ScienDSpinBox.setEnabled(False)
            self._pa.ana_param_num_laser_pulse_SpinBox.setEnabled(False)
            self._pa.ana_param_record_length_SpinBox.setEnabled(False)
        self._pulsed_master_logic.invoke_settings = invoke_checked
        return

    def toggle_error_bars(self):
        """

        @return:
        """
        show_bars = self._pa.ana_param_errorbars_CheckBox.isChecked()
        is_alternating = self.signal_image2 in self._pa.pulse_analysis_PlotWidget.items()
        if show_bars:
            if self.signal_image_error_bars not in self._pa.pulse_analysis_PlotWidget.items():
                self._pa.pulse_analysis_PlotWidget.addItem(self.signal_image_error_bars)
            if is_alternating and self.signal_image_error_bars2 not in self._pa.pulse_analysis_PlotWidget.items():
                self._pa.pulse_analysis_PlotWidget.addItem(self.signal_image_error_bars2)
        else:
            if self.signal_image_error_bars in self._pa.pulse_analysis_PlotWidget.items():
                self._pa.pulse_analysis_PlotWidget.removeItem(self.signal_image_error_bars)
            if is_alternating and self.signal_image_error_bars2 in self._pa.pulse_analysis_PlotWidget.items():
                self._pa.pulse_analysis_PlotWidget.removeItem(self.signal_image_error_bars2)
        return

    def change_second_plot(self):
        """ This method handles the second plot"""
        if self._pa.second_plot_ComboBox.currentText() == 'None':
            self._pa.second_plot_GroupBox.setVisible(False)
        else:
            self._pa.second_plot_GroupBox.setVisible(True)

            if self._pa.second_plot_ComboBox.currentText() == 'FFT':
                self._pa.pulse_analysis_second_PlotWidget.setLogMode(x=False, y=False)
            elif self._pa.second_plot_ComboBox.currentText() == 'Log(x)':
                self._pa.pulse_analysis_second_PlotWidget.setLogMode(x=True, y=False)
            elif self._pa.second_plot_ComboBox.currentText() == 'Log(y)':
                self._pa.pulse_analysis_second_PlotWidget.setLogMode(x=False, y=True)
            elif self._pa.second_plot_ComboBox.currentText() == 'Log(x)Log(y)':
                self._pa.pulse_analysis_second_PlotWidget.setLogMode(x=True, y=True)
        return

    def measurement_timer_changed(self):
        """ This method handles the analysis timing"""
        timer_interval = self._pa.time_param_ana_periode_DoubleSpinBox.value()
        self._pulsed_master_logic.analysis_interval_changed(timer_interval)
        return

    def measurement_timer_updated(self, timer_interval_s):
        """

        @param timer_interval_s:
        @return:
        """
        # block signals
        self._pa.time_param_ana_periode_DoubleSpinBox.blockSignals(True)
        # set widget
        self._pa.time_param_ana_periode_DoubleSpinBox.setValue(timer_interval_s)
        # unblock signals
        self._pa.time_param_ana_periode_DoubleSpinBox.blockSignals(False)
        return

    def extraction_settings_changed(self):
        """
        Uodate new value of standard deviation of gaussian filter
        """
        extraction_settings = dict()
        # determine if one of the conv_std_dev widgets (SpinBox or slider) has emitted the signal
        if self.sender().objectName() == 'extract_param_conv_std_dev_slider':
            extraction_settings['conv_std_dev'] = self._pe.extract_param_conv_std_dev_slider.value()
        else:
            extraction_settings['conv_std_dev'] = self._pe.extract_param_conv_std_dev_DSpinBox.value()

        extraction_settings['current_method'] = self._pe.extract_param_extraction_method_comboBox.currentText()
        extraction_settings['count_threshold'] = self._pe.extract_param_threshold_SpinBox.value()
        extraction_settings['threshold_tolerance_bins'] = self._pe.extract_param_tolerance_SpinBox.value()
        extraction_settings['min_laser_length'] = self._pe.extract_param_min_laser_length_SpinBox.value()

        self._pulsed_master_logic.extraction_settings_changed(extraction_settings)
        return

    def extraction_settings_updated(self, extraction_settings):
        """

        @param dict extraction_settings: dictionary with parameters to update
        @return:
        """

        if 'current_method' in extraction_settings:
            self._pe.extract_param_extraction_method_comboBox.blockSignals(True)
            index = self._pe.extract_param_extraction_method_comboBox.findText(extraction_settings['current_method'])
            self._pe.extract_param_extraction_method_comboBox.setCurrentIndex(index)
            self._pe.extract_param_extraction_method_comboBox.blockSignals(False)

        if 'conv_std_dev' in extraction_settings:
            self._pe.extract_param_conv_std_dev_slider.blockSignals(True)
            self._pe.extract_param_conv_std_dev_DSpinBox.blockSignals(True)
            self._pe.extract_param_conv_std_dev_DSpinBox.setValue(extraction_settings['conv_std_dev'])
            self._pe.extract_param_conv_std_dev_slider.setValue(extraction_settings['conv_std_dev'])
            self._pe.extract_param_conv_std_dev_slider.blockSignals(False)
            self._pe.extract_param_conv_std_dev_DSpinBox.blockSignals(False)

        if 'count_threshold' in extraction_settings:
            self._pe.extract_param_threshold_SpinBox.blockSignals(True)
            self._pe.extract_param_threshold_SpinBox.setValue(extraction_settings['count_threshold'])
            self._pe.extract_param_threshold_SpinBox.blockSignals(False)

        if 'threshold_tolerance_bins' in extraction_settings:
            self._pe.extract_param_tolerance_SpinBox.blockSignals(True)
            self._pe.extract_param_tolerance_SpinBox.setValue(extraction_settings['threshold_tolerance_bins'])
            self._pe.extract_param_tolerance_SpinBox.blockSignals(False)

        if 'min_laser_length' in extraction_settings:
            self._pe.extract_param_min_laser_length_SpinBox.blockSignals(True)
            self._pe.extract_param_min_laser_length_SpinBox.setValue(extraction_settings['min_laser_length'])
            self._pe.extract_param_min_laser_length_SpinBox.blockSignals(False)

        return


    def extraction_methods_updated(self, methods_dict):
        """

        @param methods_dict:
        @return:
        """
        method_names = list(methods_dict)
        # block signals
        self._pe.extract_param_extraction_method_comboBox.blockSignals(True)
        # set items
        self._pe.extract_param_extraction_method_comboBox.clear()
        self._pe.extract_param_extraction_method_comboBox.addItems(method_names)
        # unblock signals
        self._pe.extract_param_extraction_method_comboBox.blockSignals(False)
        return

    def analysis_settings_changed(self):
        """

        @return:
        """
        analysis_settings = dict()
        # Check if the signal has been emitted by a dragged line in the laser plot
        if self.sender().__class__.__name__ == 'InfiniteLine':
            analysis_settings['signal_start_s'] = self.sig_start_line.value()
            analysis_settings['signal_end_s'] = self.sig_end_line.value()
            analysis_settings['norm_start_s'] = self.ref_start_line.value()
            analysis_settings['norm_end_s'] = self.ref_end_line.value()
        else:
            signal_width = self._pe.extract_param_ana_window_width_DSpinBox.value()
            analysis_settings['signal_start_s'] = self._pe.extract_param_ana_window_start_DSpinBox.value()
            analysis_settings['signal_end_s'] = analysis_settings['signal_start_s'] + signal_width
            norm_width = self._pe.extract_param_ref_window_width_DSpinBox.value()
            analysis_settings['norm_start_s'] = self._pe.extract_param_ref_window_start_DSpinBox.value()
            analysis_settings['norm_end_s'] = analysis_settings['norm_start_s'] + norm_width

        analysis_settings['current_method'] = self._pe.extract_param_analysis_method_comboBox.currentText()

        self._pulsed_master_logic.analysis_settings_changed(analysis_settings)
        return

    def analysis_settings_updated(self, analysis_settings):
        """

        @param dict analysis_settings: dictionary with parameters to update
        @return:
        """

        # block signals
        self._pe.extract_param_analysis_method_comboBox.blockSignals(True)
        self._pe.extract_param_ana_window_start_DSpinBox.blockSignals(True)
        self._pe.extract_param_ana_window_width_DSpinBox.blockSignals(True)
        self._pe.extract_param_ref_window_start_DSpinBox.blockSignals(True)
        self._pe.extract_param_ref_window_width_DSpinBox.blockSignals(True)
        self.sig_start_line.blockSignals(True)
        self.sig_end_line.blockSignals(True)
        self.ref_start_line.blockSignals(True)
        self.ref_end_line.blockSignals(True)

        if 'signal_start_s' in analysis_settings:
            signal_start_s = analysis_settings['signal_start_s']
        else:
            signal_start_s = self._pe.extract_param_ana_window_start_DSpinBox.value()

        if 'signal_end_s' in analysis_settings:
            signal_end_s = analysis_settings['signal_end_s']
        else:
            signal_end_s = signal_start_s + self._pe.extract_param_ana_window_width_DSpinBox.value()

        if 'norm_start_s' in analysis_settings:
            norm_start_s = analysis_settings['norm_start_s']
        else:
            norm_start_s =  self._pe.extract_param_ref_window_start_DSpinBox.value()

        if 'norm_end_s' in analysis_settings:
            norm_end_s = analysis_settings['norm_end_s']
        else:
            norm_end_s = norm_start_s + self._pe.extract_param_ref_window_width_DSpinBox.value()

        if 'current_method' in analysis_settings:
            index = self._pe.extract_param_analysis_method_comboBox.findText(analysis_settings['current_method'])
            self._pe.extract_param_analysis_method_comboBox.setCurrentIndex(index)
        self._pe.extract_param_ana_window_start_DSpinBox.setValue(signal_start_s)
        self._pe.extract_param_ana_window_width_DSpinBox.setValue(signal_end_s - signal_start_s)
        self._pe.extract_param_ref_window_start_DSpinBox.setValue(norm_start_s)
        self._pe.extract_param_ref_window_width_DSpinBox.setValue(norm_end_s - norm_start_s)
        # update plots
        self.sig_start_line.setValue(signal_start_s)
        self.sig_end_line.setValue(signal_end_s)
        self.ref_start_line.setValue(norm_start_s)
        self.ref_end_line.setValue(norm_end_s)
        # unblock signals
        self._pe.extract_param_analysis_method_comboBox.blockSignals(False)
        self._pe.extract_param_ana_window_start_DSpinBox.blockSignals(False)
        self._pe.extract_param_ana_window_width_DSpinBox.blockSignals(False)
        self._pe.extract_param_ref_window_start_DSpinBox.blockSignals(False)
        self._pe.extract_param_ref_window_width_DSpinBox.blockSignals(False)
        self.sig_start_line.blockSignals(False)
        self.sig_end_line.blockSignals(False)
        self.ref_start_line.blockSignals(False)
        self.ref_end_line.blockSignals(False)
        return

    def analysis_methods_updated(self, methods_dict):
        """

        @param methods_dict:
        @return:
        """
        method_names = list(methods_dict)
        # block signals
        self._pe.extract_param_analysis_method_comboBox.blockSignals(True)
        # set items
        self._pe.extract_param_analysis_method_comboBox.clear()
        self._pe.extract_param_analysis_method_comboBox.addItems(method_names)
        # unblock signals
        self._pe.extract_param_analysis_method_comboBox.blockSignals(False)
        return

    def laser_to_show_changed(self):
        """

        @return:
        """
        current_laser = self._pe.laserpulses_ComboBox.currentText()
        show_raw_data = self._pe.laserpulses_display_raw_CheckBox.isChecked()
        if current_laser == 'sum':
            show_laser_index = 0
        else:
            show_laser_index = int(current_laser)

        self._pulsed_master_logic.laser_to_show_changed(show_laser_index, show_raw_data)
        return

    def laser_to_show_updated(self, laser_index, show_raw_data):
        """

        @param laser_index:
        @param show_raw_data:
        @return:
        """
        # block signals
        self._pe.laserpulses_ComboBox.blockSignals(True)
        self._pe.laserpulses_display_raw_CheckBox.blockSignals(True)
        # set widgets
        self._pe.laserpulses_ComboBox.setCurrentIndex(laser_index)
        self._pe.laserpulses_display_raw_CheckBox.setChecked(show_raw_data)
        # unblock signals
        self._pe.laserpulses_ComboBox.blockSignals(False)
        self._pe.laserpulses_display_raw_CheckBox.blockSignals(False)
        return

    def laser_data_updated(self, x_data, y_data):
        """

        @param x_data:
        @param y_data:
        @return:
        """
        self.lasertrace_image.setData(x=x_data, y=y_data)
        return



    ###########################################################################
    ###         Methods related to the Tab 'Sequence Generator':            ###
    ###########################################################################
    def pulser_on_off_clicked(self, checked):
        """ Manually switch the pulser output on/off. """
        checked = self._mw.pulser_on_off_PushButton.isChecked()
        if checked:
            self._mw.pulser_on_off_PushButton.setText('Pulser OFF')
            self._pulsed_master_logic.toggle_pulse_generator(True)
        else:
            self._mw.pulser_on_off_PushButton.setText('Pulser ON')
            self._pulsed_master_logic.toggle_pulse_generator(False)
        return

    def pulser_running_updated(self, is_running):
        """

        @param is_running:
        @return:
        """
        # block signals
        self._mw.pulser_on_off_PushButton.blockSignals(True)
        # set widgets
        if is_running:
            self._mw.pulser_on_off_PushButton.setText('Pulser OFF')
            if not self._mw.pulser_on_off_PushButton.isChecked():
                self._mw.pulser_on_off_PushButton.toggle()
        else:
            self._mw.pulser_on_off_PushButton.setText('Pulser ON')
            if self._mw.pulser_on_off_PushButton.isChecked():
                self._mw.pulser_on_off_PushButton.toggle()
        # unblock signals
        self._mw.pulser_on_off_PushButton.blockSignals(False)
        return

    def clear_pulser_clicked(self):
        """ Delete all loaded files in the device's current memory. """
        self._pulsed_master_logic.clear_pulse_generator()
        return

    def update_uploaded_assets(self, asset_names_list):
        """

        @param asset_names_list:
        @return:
        """
        pass

    def load_ensemble_clicked(self):
        """
        This method
        """
        # disable button
        self._pg.load_ensemble_PushButton.setEnabled(False)
        # Get the asset name to be uploaded from the ComboBox
        asset_name = self._pg.gen_ensemble_ComboBox.currentText()
        # Load asset into channles via logic module
        self._pulsed_master_logic.load_asset_into_channels(asset_name, {})
        return

    def load_sequence_clicked(self):
        """
        This method
        """
        # disable button
        self._sg.load_sequence_PushButton.setEnabled(False)
        # Get the asset name to be uploaded from the ComboBox
        asset_name = self._sg.gen_sequence_ComboBox.currentText()
        # Load asset into channles via logic module
        self._pulsed_master_logic.load_asset_into_channels(asset_name, {})
        return

    def update_loaded_asset(self, asset_name, asset_type):
        """ Check the current loaded asset from the logic and update the display. """
        label = self._mw.current_loaded_asset_Label
        if asset_name is None or asset_name == '':
            label.setText('  No asset loaded')
        elif asset_type == 'PulseBlockEnsemble' or asset_type == 'PulseSequence':
            label.setText('  {0} ({1})'.format(asset_name, asset_type))
        else:
            label.setText('  Unknown asset type')
        # enable buttons
        if asset_type == 'PulseBlockEnsemble':
            self._pg.load_ensemble_PushButton.setEnabled(True)
            self._pg.sauplo_ensemble_PushButton.setEnabled(True)
            self._pg.saup_ensemble_PushButton.setEnabled(True)
        elif asset_type == 'PulseSequence':
            self._sg.load_sequence_PushButton.setEnabled(True)
            self._sg.sauplo_sequence_PushButton.setEnabled(True)
            self._sg.saup_sequence_PushButton.setEnabled(True)
        return
