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

import numpy as np
import os
import pyqtgraph as pg
import datetime

from core.connector import Connector
from core.statusvariable import StatusVar
from core.util import units
from core.util.helpers import natural_sort
from gui.colordefs import QudiPalettePale as palette
from gui.fitsettings import FitSettingsDialog
from gui.guibase import GUIBase
from qtpy import QtCore, QtWidgets, uic
from qtwidgets.scientific_spinbox import ScienDSpinBox, ScienSpinBox
from enum import Enum


# TODO: Display the Pulse graphically (similar to AWG application)


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

class TimetraceAnalysisTab(QtWidgets.QWidget):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_timetrace_analysis.ui')
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


class GeneratorSettingDialog(QtWidgets.QDialog):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pulsed_main_gui_settings_generator.ui')

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
    ## declare connectors
    pulsedmasterlogic = Connector(interface='PulsedMasterLogic')

    # status var
    _ana_param_x_axis_name_text = StatusVar('ana_param_x_axis_name_LineEdit', 'Tau')
    _ana_param_x_axis_unit_text = StatusVar('ana_param_x_axis_unit_LineEdit', 's')
    _ana_param_y_axis_name_text = StatusVar('ana_param_y_axis_name_LineEdit', 'Normalized Signal')
    _ana_param_y_axis_unit_text = StatusVar('ana_param_y_axis_unit_LineEdit', '')
    _ana_param_second_plot_x_axis_name_text = StatusVar('ana_param_second_plot_x_axis_name_LineEdit', 'Frequency')
    _ana_param_second_plot_x_axis_unit_text = StatusVar('ana_param_second_plot_x_axis_unit_LineEdit', 'Hz')
    _ana_param_second_plot_y_axis_name_text = StatusVar('ana_param_second_plot_y_axis_name_LineEdit', 'Ft Signal')
    _ana_param_second_plot_y_axis_unit_text = StatusVar('ana_param_second_plot_y_axis_unit_LineEdit', '')

    _show_raw_data = StatusVar(default=False)
    _show_laser_index = StatusVar(default=0)
    _ana_param_errorbars = StatusVar('ana_param_errorbars_CheckBox', False)
    _predefined_methods_to_show = StatusVar('predefined_methods_to_show', [])

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialize, connect and configure the pulsed measurement GUI.

        Establish general connectivity and activate the different tabs of the
        GUI.
        """
        self._mw = PulsedMeasurementMainWindow()
        self._pa = PulseAnalysisTab()
        self._ta = TimetraceAnalysisTab()
        self._pg = PulseGeneratorTab()
        self._pe = PulseExtractionTab()
        self._pm = PredefinedMethodsTab()
        self._sg = SequenceGeneratorTab()
        self._as = AnalysisSettingDialog()
        self._pgs = GeneratorSettingDialog()
        self._pm_cfg = PredefinedMethodsConfigDialog()

        self._mw.tabWidget.addTab(self._pa, 'Analysis')
        self._mw.tabWidget.addTab(self._pe, 'Pulse Extraction')
        self._mw.tabWidget.addTab(self._ta, 'Timetrace  Analysis')
        self._mw.tabWidget.addTab(self._pg, 'Pulse Generator')
        self._mw.tabWidget.addTab(self._sg, 'Sequence Generator')
        self._mw.tabWidget.addTab(self._pm, 'Predefined Methods')

        self._activate_main_window_ui()
        self._activate_extraction_ui()
        self._activate_analysis_ui()
        self._activate_timetrace_analysis_ui()
        self._activate_generator_settings_ui()
        self._activate_pulse_generator_ui()
        self._activate_predefined_methods_ui()
        self._activate_sequence_generator_ui()
        self._activate_analysis_settings_ui()
        self._activate_predefined_methods_settings_ui()

        self.measurement_data_updated()

        self._connect_main_window_signals()
        self._connect_analysis_tab_signals()
        self._connect_extraction_tab_signals()
        self._connect_timetrace_analysis_tab_signals()
        self._connect_pulse_generator_tab_signals()
        self._connect_predefined_methods_tab_signals()
        self._connect_sequence_generator_tab_signals()
        self._connect_dialog_signals()
        self._connect_logic_signals()

        self.show()
        return

    def on_deactivate(self):
        """ Undo the Definition, configuration and initialisation of the pulsed
            measurement GUI.

        This deactivation disconnects all the graphic modules, which were
        connected in the initUI method.
        """
        self._deactivate_predefined_methods_settings_ui()
        self._deactivate_analysis_settings_ui()
        self._deactivate_timetrace_analysis_ui()
        self._deactivate_generator_settings_ui()
        self._deactivate_sequence_generator_ui()
        self._deactivate_predefined_methods_ui()
        self._deactivate_pulse_generator_ui()
        self._deactivate_analysis_ui()
        self._deactivate_extraction_ui()
        self._deactivate_main_window_ui()

        self._disconnect_main_window_signals()
        self._disconnect_analysis_tab_signals()
        self._disconnect_extraction_tab_signals()
        self._disconnect_pulse_generator_tab_signals()
        self._disconnect_predefined_methods_tab_signals()
        self._disconnect_sequence_generator_tab_signals()
        self._disconnect_dialog_signals()
        self._disconnect_logic_signals()

        self._mw.close()
        return

    def show(self):
        """Make main window visible and put it above all other windows. """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()
        return

    ###########################################################################
    #                          Signal (dis-)connections                       #
    ###########################################################################
    def _connect_main_window_signals(self):
        # Connect main window actions and toolbar
        self._mw.action_Predefined_Methods_Config.triggered.connect(
            self.show_predefined_methods_config)
        self._mw.pulser_on_off_PushButton.clicked.connect(self.pulser_on_off_clicked)
        self._mw.clear_device_PushButton.clicked.connect(self.clear_pulser_clicked)
        self._mw.action_run_stop.triggered.connect(self.measurement_run_stop_clicked)
        self._mw.action_continue_pause.triggered.connect(self.measurement_continue_pause_clicked)
        self._mw.action_pull_data.triggered.connect(self.pull_data_clicked)
        self._mw.action_save.triggered.connect(self.save_clicked)
        self._mw.actionSave.triggered.connect(self.save_clicked)
        self._mw.action_Settings_Analysis.triggered.connect(self.show_analysis_settings)
        self._mw.action_Settings_Generator.triggered.connect(self.show_generator_settings)
        self._mw.action_FitSettings.triggered.connect(self._fsd.show)
        return

    def _connect_dialog_signals(self):
        # Connect signals used in predefined methods config dialog
        self._pm_cfg.accepted.connect(self.apply_predefined_methods_config)
        self._pm_cfg.rejected.connect(self.keep_former_predefined_methods_config)
        self._pm_cfg.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.apply_predefined_methods_config)

        # Connect signals used in analysis settings dialog
        self._as.accepted.connect(self.update_analysis_settings)
        self._as.rejected.connect(self.keep_former_analysis_settings)
        self._as.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.update_analysis_settings)

        # Connect signals used in pulse generator settings dialog
        self._pgs.accepted.connect(self.apply_generator_settings)
        self._pgs.rejected.connect(self.keep_former_generator_settings)
        self._pgs.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.apply_generator_settings)

        # Connect signals used in fit settings dialog
        self._fsd.sigFitsUpdated.connect(self._pa.fit_param_fit_func_ComboBox.setFitFunctions)
        self._fsd.sigFitsUpdated.connect(self._pa.fit_param_alt_fit_func_ComboBox.setFitFunctions)
        self._fsd.sigFitsUpdated.connect(self._ta.fit_method_comboBox.setFitFunctions)
        return

    def _connect_pulse_generator_tab_signals(self):
        # Connect Block/Ensemble editor tab signals
        self._pg.gen_laserchannel_ComboBox.currentIndexChanged.connect(self.generation_parameters_changed)
        self._pg.gen_syncchannel_ComboBox.currentIndexChanged.connect(self.generation_parameters_changed)
        self._pg.gen_gatechannel_ComboBox.currentIndexChanged.connect(self.generation_parameters_changed)

        self._pg.sample_ensemble_PushButton.clicked.connect(self.sample_ensemble_clicked)
        self._pg.samplo_ensemble_PushButton.clicked.connect(self.samplo_ensemble_clicked)
        self._pg.load_ensemble_PushButton.clicked.connect(self.load_ensemble_clicked)

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
        self._pg.curr_block_generate_PushButton.clicked.connect(self.editor_generate_block_clicked)
        self._pg.curr_block_del_PushButton.clicked.connect(self.editor_delete_block_clicked)
        self._pg.curr_block_del_all_PushButton.clicked.connect(self.editor_delete_all_blocks_clicked)
        self._pg.curr_block_load_PushButton.clicked.connect(self.editor_load_block_clicked)
        self._pg.curr_ensemble_generate_PushButton.clicked.connect(self.editor_generate_ensemble_clicked)
        self._pg.curr_ensemble_del_PushButton.clicked.connect(self.editor_delete_ensemble_clicked)
        self._pg.curr_ensemble_del_all_PushButton.clicked.connect(self.editor_delete_all_ensembles_clicked)
        self._pg.curr_ensemble_load_PushButton.clicked.connect(self.editor_load_ensemble_clicked)
        return

    def _connect_sequence_generator_tab_signals(self):
        # Connect Sequence editor tab signals
        self._sg.sample_sequence_PushButton.clicked.connect(self.sample_sequence_clicked)
        self._sg.samplo_sequence_PushButton.clicked.connect(self.samplo_sequence_clicked)
        self._sg.load_sequence_PushButton.clicked.connect(self.load_sequence_clicked)

        self._sg.sequence_add_last_PushButton.clicked.connect(self.sequence_add_last_clicked)
        self._sg.sequence_del_last_PushButton.clicked.connect(self.sequence_del_last_clicked)
        self._sg.sequence_add_sel_PushButton.clicked.connect(self.sequence_add_sel_clicked)
        self._sg.sequence_del_sel_PushButton.clicked.connect(self.sequence_del_sel_clicked)
        self._sg.sequence_clear_PushButton.clicked.connect(self.sequence_clear_clicked)
        self._sg.curr_sequence_generate_PushButton.clicked.connect(self.editor_generate_sequence_clicked)
        self._sg.curr_sequence_del_PushButton.clicked.connect(self.editor_delete_sequence_clicked)
        self._sg.curr_sequence_del_all_PushButton.clicked.connect(self.editor_delete_all_sequences_clicked)
        self._sg.curr_sequence_load_PushButton.clicked.connect(self.editor_load_sequence_clicked)
        return

    def _connect_analysis_tab_signals(self):
        # Connect pulse analysis tab signals
        self._pa.fit_param_PushButton.clicked.connect(self.fit_clicked)
        self._pa.alt_fit_param_PushButton.clicked.connect(self.fit_clicked)

        self._pa.ext_control_use_mw_CheckBox.stateChanged.connect(self.microwave_settings_changed)
        self._pa.ext_control_mw_freq_DoubleSpinBox.editingFinished.connect(self.microwave_settings_changed)
        self._pa.ext_control_mw_power_DoubleSpinBox.editingFinished.connect(self.microwave_settings_changed)

        self._pa.ana_param_invoke_settings_CheckBox.stateChanged.connect(self.measurement_settings_changed)
        self._pa.ana_param_alternating_CheckBox.stateChanged.connect(self.measurement_settings_changed)
        self._pa.ana_param_ignore_first_CheckBox.stateChanged.connect(self.measurement_settings_changed)
        self._pa.ana_param_ignore_last_CheckBox.stateChanged.connect(self.measurement_settings_changed)
        self._pa.ana_param_x_axis_start_ScienDSpinBox.editingFinished.connect(self.measurement_settings_changed)
        self._pa.ana_param_x_axis_inc_ScienDSpinBox.editingFinished.connect(self.measurement_settings_changed)
        self._pa.ana_param_num_laser_pulse_SpinBox.editingFinished.connect(self.measurement_settings_changed)

        self._pa.ana_param_record_length_DoubleSpinBox.editingFinished.connect(self.fast_counter_settings_changed)
        self._pa.ana_param_fc_bins_ComboBox.currentIndexChanged.connect(self.fast_counter_settings_changed)

        self._pa.time_param_ana_periode_DoubleSpinBox.editingFinished.connect(self.measurement_timer_changed)
        self._pa.ana_param_errorbars_CheckBox.toggled.connect(self.toggle_error_bars)
        self._pa.second_plot_ComboBox.currentIndexChanged[str].connect(self.second_plot_changed)
        return

    def _connect_extraction_tab_signals(self):
        # Connect pulse extraction tab signals
        self._pe.extract_param_ana_window_start_DSpinBox.editingFinished.connect(self.analysis_settings_changed)
        self._pe.extract_param_ana_window_width_DSpinBox.editingFinished.connect(self.analysis_settings_changed)
        self._pe.extract_param_ref_window_start_DSpinBox.editingFinished.connect(self.analysis_settings_changed)
        self._pe.extract_param_ref_window_width_DSpinBox.editingFinished.connect(self.analysis_settings_changed)
        self.sig_start_line.sigPositionChangeFinished.connect(self.analysis_settings_changed)
        self.sig_end_line.sigPositionChangeFinished.connect(self.analysis_settings_changed)
        self.ref_start_line.sigPositionChangeFinished.connect(self.analysis_settings_changed)
        self.ref_end_line.sigPositionChangeFinished.connect(self.analysis_settings_changed)
        self._pe.extract_param_analysis_method_comboBox.currentIndexChanged.connect(self.analysis_settings_changed)
        self._pe.extract_param_method_comboBox.currentIndexChanged.connect(self.extraction_settings_changed)

        self._pe.laserpulses_ComboBox.currentIndexChanged.connect(self.update_laser_data)
        self._pe.laserpulses_display_raw_CheckBox.stateChanged.connect(self.update_laser_data)
        return

    def _connect_timetrace_analysis_tab_signals(self):
        # Connect timetrace analysis tab signals
        self._ta.param_1_rebinnig_spinBox.editingFinished.connect(self.timetrace_analysis_settings_changed)
        self._ta.param_2_start_DSpinBox.editingFinished.connect(self.timetrace_analysis_settings_changed)
        self._ta.param_3_width_DSpinBox.editingFinished.connect(self.timetrace_analysis_settings_changed)
        self._ta.param_4_origin_DSpinBox.editingFinished.connect(self.timetrace_analysis_settings_changed)
        self.ta_start_line.sigPositionChangeFinished.connect(self.timetrace_analysis_settings_changed)
        self.ta_end_line.sigPositionChangeFinished.connect(self.timetrace_analysis_settings_changed)
        self.ta_origin_line.sigPositionChangeFinished.connect(self.timetrace_analysis_settings_changed)

        self._ta.timetrace_fit_pushButton.clicked.connect(self.fit_clicked)

    def _connect_predefined_methods_tab_signals(self):
        pass

    def _connect_logic_signals(self):
        # Connect update signals from pulsed_master_logic
        self.pulsedmasterlogic().sigMeasurementDataUpdated.connect(self.measurement_data_updated)
        self.pulsedmasterlogic().sigTimerUpdated.connect(self.measurement_timer_updated)
        self.pulsedmasterlogic().sigFitUpdated.connect(self.fit_data_updated)
        self.pulsedmasterlogic().sigMeasurementStatusUpdated.connect(self.measurement_status_updated)
        self.pulsedmasterlogic().sigPulserRunningUpdated.connect(self.pulser_running_updated)
        self.pulsedmasterlogic().sigExtMicrowaveRunningUpdated.connect(self.microwave_running_updated)
        self.pulsedmasterlogic().sigExtMicrowaveSettingsUpdated.connect(self.microwave_settings_updated)
        self.pulsedmasterlogic().sigFastCounterSettingsUpdated.connect(self.fast_counter_settings_updated)
        self.pulsedmasterlogic().sigMeasurementSettingsUpdated.connect(self.measurement_settings_updated)
        self.pulsedmasterlogic().sigAnalysisSettingsUpdated.connect(self.analysis_settings_updated)
        self.pulsedmasterlogic().sigTimetraceAnalysisSettingsUpdated.connect(self.timetrace_analysis_settings_updated)
        self.pulsedmasterlogic().sigExtractionSettingsUpdated.connect(self.extraction_settings_updated)

        self.pulsedmasterlogic().sigBlockDictUpdated.connect(self.update_block_dict)
        self.pulsedmasterlogic().sigEnsembleDictUpdated.connect(self.update_ensemble_dict)
        self.pulsedmasterlogic().sigSequenceDictUpdated.connect(self.update_sequence_dict)
        self.pulsedmasterlogic().sigAvailableWaveformsUpdated.connect(self.waveform_list_updated)
        self.pulsedmasterlogic().sigAvailableSequencesUpdated.connect(self.sequence_list_updated)
        self.pulsedmasterlogic().sigSampleEnsembleComplete.connect(self.sample_ensemble_finished)
        self.pulsedmasterlogic().sigSampleSequenceComplete.connect(self.sample_sequence_finished)
        self.pulsedmasterlogic().sigLoadedAssetUpdated.connect(self.loaded_asset_updated)
        self.pulsedmasterlogic().sigGeneratorSettingsUpdated.connect(self.pulse_generator_settings_updated)
        self.pulsedmasterlogic().sigSamplingSettingsUpdated.connect(self.generation_parameters_updated)
        self.pulsedmasterlogic().sigPredefinedSequenceGenerated.connect(self.predefined_generated)
        return

    def _disconnect_main_window_signals(self):
        # Connect main window actions and toolbar
        self._mw.action_Predefined_Methods_Config.triggered.disconnect()
        self._mw.pulser_on_off_PushButton.clicked.disconnect()
        self._mw.clear_device_PushButton.clicked.disconnect()
        self._mw.action_run_stop.triggered.disconnect()
        self._mw.action_continue_pause.triggered.disconnect()
        self._mw.action_pull_data.triggered.disconnect()
        self._mw.action_save.triggered.disconnect()
        self._mw.actionSave.triggered.disconnect()
        self._mw.action_Settings_Analysis.triggered.disconnect()
        self._mw.action_Settings_Generator.triggered.disconnect()
        self._mw.action_FitSettings.triggered.disconnect()
        return

    def _disconnect_dialog_signals(self):
        # Connect signals used in predefined methods config dialog
        self._pm_cfg.accepted.disconnect()
        self._pm_cfg.rejected.disconnect()
        self._pm_cfg.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.disconnect()

        # Connect signals used in analysis settings dialog
        self._as.accepted.disconnect()
        self._as.rejected.disconnect()
        self._as.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.disconnect()

        # Connect signals used in pulse generator settings dialog
        self._pgs.accepted.disconnect()
        self._pgs.rejected.disconnect()
        self._pgs.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.disconnect()

        # Connect signals used in fit settings dialog
        self._fsd.sigFitsUpdated.disconnect()
        return

    def _disconnect_pulse_generator_tab_signals(self):
        # Connect Block/Ensemble editor tab signals
        self._pg.gen_laserchannel_ComboBox.currentIndexChanged.disconnect()
        self._pg.gen_syncchannel_ComboBox.currentIndexChanged.disconnect()
        self._pg.gen_gatechannel_ComboBox.currentIndexChanged.disconnect()

        self._pg.sample_ensemble_PushButton.clicked.disconnect()
        self._pg.samplo_ensemble_PushButton.clicked.disconnect()
        self._pg.load_ensemble_PushButton.clicked.disconnect()

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
        self._pg.curr_block_generate_PushButton.clicked.disconnect()
        self._pg.curr_block_del_PushButton.clicked.disconnect()
        self._pg.curr_block_del_all_PushButton.clicked.disconnect()
        self._pg.curr_block_load_PushButton.clicked.disconnect()
        self._pg.curr_ensemble_generate_PushButton.clicked.disconnect()
        self._pg.curr_ensemble_del_PushButton.clicked.disconnect()
        self._pg.curr_ensemble_del_all_PushButton.clicked.disconnect()
        self._pg.curr_ensemble_load_PushButton.clicked.disconnect()
        return

    def _disconnect_sequence_generator_tab_signals(self):
        # Connect Sequence editor tab signals
        self._sg.sample_sequence_PushButton.clicked.disconnect()
        self._sg.samplo_sequence_PushButton.clicked.disconnect()
        self._sg.load_sequence_PushButton.clicked.disconnect()

        self._sg.sequence_add_last_PushButton.clicked.disconnect()
        self._sg.sequence_del_last_PushButton.clicked.disconnect()
        self._sg.sequence_add_sel_PushButton.clicked.disconnect()
        self._sg.sequence_del_sel_PushButton.clicked.disconnect()
        self._sg.sequence_clear_PushButton.clicked.disconnect()
        self._sg.curr_sequence_generate_PushButton.clicked.disconnect()
        self._sg.curr_sequence_del_PushButton.clicked.disconnect()
        self._sg.curr_sequence_del_all_PushButton.clicked.disconnect()
        self._sg.curr_sequence_load_PushButton.clicked.disconnect()
        return

    def _disconnect_analysis_tab_signals(self):
        # Connect pulse analysis tab signals
        self._pa.fit_param_PushButton.clicked.disconnect()
        self._pa.alt_fit_param_PushButton.clicked.disconnect()
        self._pa.ext_control_use_mw_CheckBox.stateChanged.disconnect()
        self._pa.ext_control_mw_freq_DoubleSpinBox.editingFinished.disconnect()
        self._pa.ext_control_mw_power_DoubleSpinBox.editingFinished.disconnect()

        self._pa.ana_param_invoke_settings_CheckBox.stateChanged.disconnect()
        self._pa.ana_param_alternating_CheckBox.stateChanged.disconnect()
        self._pa.ana_param_ignore_first_CheckBox.stateChanged.disconnect()
        self._pa.ana_param_ignore_last_CheckBox.stateChanged.disconnect()
        self._pa.ana_param_x_axis_start_ScienDSpinBox.editingFinished.disconnect()
        self._pa.ana_param_x_axis_inc_ScienDSpinBox.editingFinished.disconnect()
        self._pa.ana_param_num_laser_pulse_SpinBox.editingFinished.disconnect()

        self._pa.ana_param_record_length_DoubleSpinBox.editingFinished.disconnect()
        self._pa.ana_param_fc_bins_ComboBox.currentIndexChanged.disconnect()

        self._pa.time_param_ana_periode_DoubleSpinBox.editingFinished.disconnect()
        self._pa.ana_param_errorbars_CheckBox.toggled.disconnect()
        self._pa.second_plot_ComboBox.currentIndexChanged[str].disconnect()
        return

    def _disconnect_extraction_tab_signals(self):
        # Connect pulse extraction tab signals
        self._pe.extract_param_ana_window_start_DSpinBox.editingFinished.disconnect()
        self._pe.extract_param_ana_window_width_DSpinBox.editingFinished.disconnect()
        self._pe.extract_param_ref_window_start_DSpinBox.editingFinished.disconnect()
        self._pe.extract_param_ref_window_width_DSpinBox.editingFinished.disconnect()
        self.sig_start_line.sigPositionChangeFinished.disconnect()
        self.sig_end_line.sigPositionChangeFinished.disconnect()
        self.ref_start_line.sigPositionChangeFinished.disconnect()
        self.ref_end_line.sigPositionChangeFinished.disconnect()
        self._pe.extract_param_analysis_method_comboBox.currentIndexChanged.disconnect()
        self._pe.extract_param_method_comboBox.currentIndexChanged.disconnect()

        self._pe.laserpulses_ComboBox.currentIndexChanged.disconnect()
        self._pe.laserpulses_display_raw_CheckBox.stateChanged.disconnect()
        return

    def _disconnect_timetrace_analysis_tab_signals(self):
        # Connect timetrace analysis tab signals
        self._ta.param_1_rebinnig_spinBox.editingFinished.disconnect()
        self._ta.param_2_start_DSpinBox.editingFinished.disconnect()
        self._ta.param_3_width_DSpinBox.editingFinished.disconnect()
        self._ta.param_4_origin_DSpinBox.editingFinished.disconnect()
        self.ta_start_line.sigPositionChangeFinished.disconnect()
        self.ta_end_line.sigPositionChangeFinished.disconnect()
        self.ta_origin_line.sigPositionChangeFinished.disconnect()

        self._pa.timetrace_fit_pushButton.clicked.disconnect()

    def _disconnect_predefined_methods_tab_signals(self):
        for combobox in self._channel_selection_comboboxes:
            combobox.currentIndexChanged.disconnect()
        for widget in self._global_param_widgets:
            if hasattr(widget, 'isChecked'):
                widget.stateChanged.disconnect()
            else:
                widget.editingFinished.disconnect()
        return

    def _disconnect_logic_signals(self):
        # Disconnect update signals from pulsed_master_logic
        self.pulsedmasterlogic().sigMeasurementDataUpdated.disconnect()
        self.pulsedmasterlogic().sigTimerUpdated.disconnect()
        self.pulsedmasterlogic().sigFitUpdated.disconnect()
        self.pulsedmasterlogic().sigMeasurementStatusUpdated.disconnect()
        self.pulsedmasterlogic().sigPulserRunningUpdated.disconnect()
        self.pulsedmasterlogic().sigExtMicrowaveRunningUpdated.disconnect()
        self.pulsedmasterlogic().sigExtMicrowaveSettingsUpdated.disconnect()
        self.pulsedmasterlogic().sigFastCounterSettingsUpdated.disconnect()
        self.pulsedmasterlogic().sigMeasurementSettingsUpdated.disconnect()
        self.pulsedmasterlogic().sigAnalysisSettingsUpdated.disconnect()
        self.pulsedmasterlogic().sigExtractionSettingsUpdated.disconnect()

        self.pulsedmasterlogic().sigBlockDictUpdated.disconnect()
        self.pulsedmasterlogic().sigEnsembleDictUpdated.disconnect()
        self.pulsedmasterlogic().sigSequenceDictUpdated.disconnect()
        self.pulsedmasterlogic().sigAvailableWaveformsUpdated.disconnect()
        self.pulsedmasterlogic().sigAvailableSequencesUpdated.disconnect()
        self.pulsedmasterlogic().sigSampleEnsembleComplete.disconnect()
        self.pulsedmasterlogic().sigSampleSequenceComplete.disconnect()
        self.pulsedmasterlogic().sigLoadedAssetUpdated.disconnect()
        self.pulsedmasterlogic().sigGeneratorSettingsUpdated.disconnect()
        self.pulsedmasterlogic().sigSamplingSettingsUpdated.disconnect()
        self.pulsedmasterlogic().sigPredefinedSequenceGenerated.disconnect()
        return

    ###########################################################################
    #                    Main window related methods                          #
    ###########################################################################
    def _activate_main_window_ui(self):
        self._setup_toolbar()
        self.loaded_asset_updated(*self.pulsedmasterlogic().loaded_asset)
        return

    def _deactivate_main_window_ui(self):
        pass

    def _setup_toolbar(self):
        # create all the needed control widgets on the fly - Qt Creator does not like non button objects in toolbars
        self._mw.pulser_on_off_PushButton = QtWidgets.QPushButton()
        self._mw.pulser_on_off_PushButton.setText('Pulser ON')
        self._mw.pulser_on_off_PushButton.setToolTip('Switch the device on and off.')
        self._mw.pulser_on_off_PushButton.setCheckable(True)
        self._mw.control_ToolBar.addWidget(self._mw.pulser_on_off_PushButton)

        self._mw.clear_device_PushButton = QtWidgets.QPushButton(self._mw)
        self._mw.clear_device_PushButton.setText('Clear Pulser')
        self._mw.clear_device_PushButton.setToolTip('Clear the Pulser Device Memory\n'
                                                    'from all loaded files.')
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


        self._mw.save_label_pulses =  QtWidgets.QLabel('Save pulses :')
        self._mw.save_label_pulses.setContentsMargins(5, 0, 0, 0)
        self._mw.save_checkbox_pulses = QtWidgets.QCheckBox()
        self._mw.save_checkbox_pulses.setChecked(True)
        self._mw.save_label_timetrace = QtWidgets.QLabel('Save timetrace :')
        self._mw.save_label_timetrace.setContentsMargins(5, 0, 0, 0)
        self._mw.save_checkbox_timetrace = QtWidgets.QCheckBox()

        self._mw.save_ToolBar.addWidget(self._mw.save_label_pulses)
        self._mw.save_ToolBar.addWidget(self._mw.save_checkbox_pulses)
        self._mw.save_ToolBar.addWidget(self._mw.save_label_timetrace)
        self._mw.save_ToolBar.addWidget(self._mw.save_checkbox_timetrace)
        return

    @QtCore.Slot(bool)
    def pulser_on_off_clicked(self, checked):
        """ Manually switch the pulser output on/off. """
        if checked:
            self._mw.pulser_on_off_PushButton.setText('Pulser OFF')
        else:
            self._mw.pulser_on_off_PushButton.setText('Pulser ON')
        self.pulsedmasterlogic().toggle_pulse_generator(checked)
        return

    @QtCore.Slot(bool)
    def pulser_running_updated(self, is_running):
        """

        @param is_running:
        @return:
        """
        # block signals
        self._mw.pulser_on_off_PushButton.blockSignals(True)
        # set widgets
        if is_running:
            self._pg.curr_ensemble_del_all_PushButton.setEnabled(False)
            self._sg.curr_sequence_del_all_PushButton.setEnabled(False)
            self._mw.clear_device_PushButton.setEnabled(False)
            self._mw.pulser_on_off_PushButton.setText('Pulser OFF')
            if not self._mw.pulser_on_off_PushButton.isChecked():
                self._mw.pulser_on_off_PushButton.toggle()
        else:
            self._pg.curr_ensemble_del_all_PushButton.setEnabled(True)
            self._sg.curr_sequence_del_all_PushButton.setEnabled(True)
            self._mw.clear_device_PushButton.setEnabled(True)
            self._mw.pulser_on_off_PushButton.setText('Pulser ON')
            if self._mw.pulser_on_off_PushButton.isChecked():
                self._mw.pulser_on_off_PushButton.toggle()
        # unblock signals
        self._mw.pulser_on_off_PushButton.blockSignals(False)
        return

    @QtCore.Slot()
    def clear_pulser_clicked(self):
        """ Delete all loaded files in the device's current memory. """
        self.pulsedmasterlogic().clear_pulse_generator()
        return

    @QtCore.Slot(str, str)
    def loaded_asset_updated(self, asset_name, asset_type):
        """ Check the current loaded asset from the logic and update the display. """
        label = self._mw.current_loaded_asset_Label
        if not asset_name:
            label.setText('  No asset loaded')
        elif asset_type in ('PulseBlockEnsemble', 'PulseSequence'):
            label.setText('  {0} ({1})'.format(asset_name, asset_type))
        else:
            label.setText('  Unknown asset type')
        # enable buttons
        self._pg.load_ensemble_PushButton.setEnabled(True)
        self._pg.samplo_ensemble_PushButton.setEnabled(True)
        self._pg.sample_ensemble_PushButton.setEnabled(True)
        self._sg.load_sequence_PushButton.setEnabled(True)
        self._sg.samplo_sequence_PushButton.setEnabled(True)
        self._sg.sample_sequence_PushButton.setEnabled(True)
        # Reactivate predefined method buttons
        if hasattr(self._pm, 'samplo_buttons'):
            for button in self._pm.samplo_buttons.values():
                button.setEnabled(True)
        return

    @QtCore.Slot(bool)
    def measurement_run_stop_clicked(self, isChecked):
        """ Manages what happens if pulsed measurement is started or stopped.

        @param bool isChecked: start scan if that is possible
        """
        self.pulsedmasterlogic().toggle_pulsed_measurement(isChecked)
        return

    @QtCore.Slot(bool)
    def measurement_continue_pause_clicked(self, isChecked):
        """ Continues and pauses the measurement. """
        self.pulsedmasterlogic().toggle_pulsed_measurement_pause(isChecked)
        return

    @QtCore.Slot(bool, bool)
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
            self._pgs.gen_use_interleave_CheckBox.setEnabled(False)
            self._pgs.gen_sample_freq_DSpinBox.setEnabled(False)
            self._pgs.gen_activation_config_ComboBox.setEnabled(False)
            for label, widget1, widget2 in self._analog_chnl_setting_widgets.values():
                widget1.setEnabled(False)
                widget2.setEnabled(False)
            for label, widget1, widget2 in self._digital_chnl_setting_widgets.values():
                widget1.setEnabled(False)
                widget2.setEnabled(False)
            self._pa.ext_control_mw_freq_DoubleSpinBox.setEnabled(False)
            self._pa.ext_control_mw_power_DoubleSpinBox.setEnabled(False)
            self._pa.ana_param_x_axis_start_ScienDSpinBox.setEnabled(False)
            self._pa.ana_param_x_axis_inc_ScienDSpinBox.setEnabled(False)
            self._pa.ana_param_num_laser_pulse_SpinBox.setEnabled(False)
            self._pa.ana_param_record_length_DoubleSpinBox.setEnabled(False)
            self._pa.ext_control_use_mw_CheckBox.setEnabled(False)
            self._pa.ana_param_fc_bins_ComboBox.setEnabled(False)
            self._pa.ana_param_ignore_first_CheckBox.setEnabled(False)
            self._pa.ana_param_ignore_last_CheckBox.setEnabled(False)
            self._pa.ana_param_alternating_CheckBox.setEnabled(False)
            self._pa.ana_param_invoke_settings_CheckBox.setEnabled(False)
            self._pg.load_ensemble_PushButton.setEnabled(False)
            self._pg.curr_ensemble_del_all_PushButton.setEnabled(False)
            self._sg.curr_sequence_del_all_PushButton.setEnabled(False)
            self._sg.load_sequence_PushButton.setEnabled(False)
            self._mw.pulser_on_off_PushButton.setEnabled(False)
            self._mw.action_continue_pause.setEnabled(True)
            self._mw.action_pull_data.setEnabled(True)
            self._mw.clear_device_PushButton.setEnabled(False)
            if not self._mw.action_run_stop.isChecked():
                self._mw.action_run_stop.toggle()
        else:
            self._pgs.gen_use_interleave_CheckBox.setEnabled(True)
            self._pgs.gen_sample_freq_DSpinBox.setEnabled(True)
            self._pgs.gen_activation_config_ComboBox.setEnabled(True)
            for label, widget1, widget2 in self._analog_chnl_setting_widgets.values():
                widget1.setEnabled(True)
                widget2.setEnabled(True)
            for label, widget1, widget2 in self._digital_chnl_setting_widgets.values():
                widget1.setEnabled(True)
                widget2.setEnabled(True)
            self._pa.ext_control_use_mw_CheckBox.setEnabled(True)
            self._pa.ext_control_mw_freq_DoubleSpinBox.setEnabled(True)
            self._pa.ext_control_mw_power_DoubleSpinBox.setEnabled(True)
            self._pa.ana_param_fc_bins_ComboBox.setEnabled(True)
            self._pg.load_ensemble_PushButton.setEnabled(True)
            self._pg.curr_ensemble_del_all_PushButton.setEnabled(True)
            self._sg.curr_sequence_del_all_PushButton.setEnabled(True)
            self._sg.load_sequence_PushButton.setEnabled(True)
            self._mw.pulser_on_off_PushButton.setEnabled(True)
            self._mw.action_continue_pause.setEnabled(False)
            self._mw.action_pull_data.setEnabled(False)
            self._mw.clear_device_PushButton.setEnabled(True)
            self._pa.ana_param_invoke_settings_CheckBox.setEnabled(True)
            if not self._pa.ana_param_invoke_settings_CheckBox.isChecked():
                self._pa.ana_param_ignore_first_CheckBox.setEnabled(True)
                self._pa.ana_param_ignore_last_CheckBox.setEnabled(True)
                self._pa.ana_param_alternating_CheckBox.setEnabled(True)
                self._pa.ana_param_x_axis_start_ScienDSpinBox.setEnabled(True)
                self._pa.ana_param_x_axis_inc_ScienDSpinBox.setEnabled(True)
                self._pa.ana_param_num_laser_pulse_SpinBox.setEnabled(True)
                self._pa.ana_param_record_length_DoubleSpinBox.setEnabled(True)
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

    @QtCore.Slot()
    def pull_data_clicked(self):
        """ Pulls and analysis the data when the 'action_pull_data'-button is clicked. """
        self.pulsedmasterlogic().manually_pull_data()
        return

    def save_clicked(self):
        """Saves the current data"""
        self._mw.action_save.setEnabled(False)
        self._mw.actionSave.setEnabled(False)
        save_tag = self._mw.save_tag_LineEdit.text()
        with_error = self._pa.ana_param_errorbars_CheckBox.isChecked()
        save_pulses = self._mw.save_checkbox_pulses.isChecked()
        save_timetrace = self._mw.save_checkbox_timetrace.isChecked()

        self.pulsedmasterlogic().save_measurement_data(tag=save_tag, with_error=with_error,
                                                       save_laser_pulses=save_pulses,
                                                       save_pulsed_measurement=save_pulses,
                                                       save_timetrace=save_timetrace)
        self._mw.action_save.setEnabled(True)
        self._mw.actionSave.setEnabled(True)
        return

    @QtCore.Slot()
    def measurement_timer_changed(self):
        """ This method handles the analysis timing"""
        timer_interval = self._pa.time_param_ana_periode_DoubleSpinBox.value()
        self.pulsedmasterlogic().set_timer_interval(timer_interval)
        return

    @QtCore.Slot(float, int, float)
    def measurement_timer_updated(self, elapsed_time, elapsed_sweeps, timer_interval):
        """
        Refreshes the elapsed time and sweeps of the measurement.

        @param float elapsed_time:
        @param int elapsed_sweeps:
        @param float timer_interval:
        @return:
        """
        time_str = str(datetime.timedelta(seconds=elapsed_time)).rsplit('.', 1)[0]
        # block signals
        self._pa.time_param_elapsed_time_LineEdit.blockSignals(True)
        self._pa.time_param_ana_periode_DoubleSpinBox.blockSignals(True)
        self._pa.time_param_elapsed_sweep_SpinBox.blockSignals(True)
        # Set widgets
        self._pa.time_param_elapsed_time_LineEdit.setText(time_str)
        self._pa.time_param_ana_periode_DoubleSpinBox.setValue(timer_interval)
        self._pa.time_param_elapsed_sweep_SpinBox.setValue(elapsed_sweeps)
        # unblock signals
        self._pa.time_param_elapsed_time_LineEdit.blockSignals(False)
        self._pa.time_param_ana_periode_DoubleSpinBox.blockSignals(False)
        self._pa.time_param_elapsed_sweep_SpinBox.blockSignals(False)
        return

    ###########################################################################
    #                 Analysis settings dialog related methods                #
    ###########################################################################
    def _activate_analysis_settings_ui(self):
        """
        Initialize the settings dialog for 'Analysis' Tab.
        """
        self._as.ana_param_x_axis_name_LineEdit.setText(
            self.pulsedmasterlogic().measurement_settings['labels'][0])
        self._as.ana_param_x_axis_unit_LineEdit.setText(
            self.pulsedmasterlogic().measurement_settings['units'][0])
        self._as.ana_param_y_axis_name_LineEdit.setText(
            self.pulsedmasterlogic().measurement_settings['labels'][1])
        self._as.ana_param_y_axis_unit_LineEdit.setText(
            self.pulsedmasterlogic().measurement_settings['units'][1])

        self._as.ana_param_second_plot_x_axis_name_LineEdit.setText(self._ana_param_second_plot_x_axis_name_text)
        self._as.ana_param_second_plot_x_axis_unit_LineEdit.setText(self._ana_param_second_plot_x_axis_unit_text)
        self._as.ana_param_second_plot_y_axis_name_LineEdit.setText(self._ana_param_second_plot_y_axis_name_text)
        self._as.ana_param_second_plot_y_axis_unit_LineEdit.setText(self._ana_param_second_plot_y_axis_unit_text)

        self.update_analysis_settings()
        return

    def _deactivate_analysis_settings_ui(self):
        """
        De-initialize the settings dialog for 'Analysis' Tab.
        """
        self._as.close()
        return

    def update_analysis_settings(self):
        """ Apply the new settings """
        axis_labels = (self._as.ana_param_x_axis_name_LineEdit.text(),
                       self._as.ana_param_y_axis_name_LineEdit.text())
        axis_units = (self._as.ana_param_x_axis_unit_LineEdit.text(),
                      self._as.ana_param_y_axis_unit_LineEdit.text())

        self._ana_param_second_plot_x_axis_name_text = self._as.ana_param_second_plot_x_axis_name_LineEdit.text()
        self._ana_param_second_plot_x_axis_unit_text = self._as.ana_param_second_plot_x_axis_unit_LineEdit.text()
        self._ana_param_second_plot_y_axis_name_text = self._as.ana_param_second_plot_y_axis_name_LineEdit.text()
        self._ana_param_second_plot_y_axis_unit_text = self._as.ana_param_second_plot_y_axis_unit_LineEdit.text()

        self.pulsedmasterlogic().set_measurement_settings(units=axis_units, labels=axis_labels)
        return

    def keep_former_analysis_settings(self):
        """ Keep the old settings """
        self._as.ana_param_x_axis_name_LineEdit.setText(
            self.pulsedmasterlogic().measurement_settings['labels'][0])
        self._as.ana_param_x_axis_unit_LineEdit.setText(
            self.pulsedmasterlogic().measurement_settings['units'][0])
        self._as.ana_param_y_axis_name_LineEdit.setText(
            self.pulsedmasterlogic().measurement_settings['labels'][1])
        self._as.ana_param_y_axis_unit_LineEdit.setText(
            self.pulsedmasterlogic().measurement_settings['units'][1])
        self._as.ana_param_second_plot_x_axis_name_LineEdit.setText(
            self._ana_param_second_plot_x_axis_name_text)
        self._as.ana_param_second_plot_x_axis_unit_LineEdit.setText(
            self._ana_param_second_plot_x_axis_unit_text)
        self._as.ana_param_second_plot_y_axis_name_LineEdit.setText(
            self._ana_param_second_plot_y_axis_name_text)
        self._as.ana_param_second_plot_y_axis_unit_LineEdit.setText(
            self._ana_param_second_plot_y_axis_unit_text)
        return

    def show_analysis_settings(self):
        """ Open the Analysis Settings Window. """
        self._as.exec_()
        return

    ###########################################################################
    #             Pulse generator settings dialog related methods             #
    ###########################################################################
    def _activate_generator_settings_ui(self):
        """
        Initialize the dialog for the pulse generator settings.
        """
        # Dynamically create channel related widgets and keep them in dictionaries
        self._analog_chnl_setting_widgets = dict()
        self._digital_chnl_setting_widgets = dict()
        self.__create_analog_channel_setting_widgets()
        self.__create_digital_channel_setting_widgets()

        # Apply hardware constraints to widgets
        pg_constr = self.pulsedmasterlogic().pulse_generator_constraints
        self._pgs.gen_sample_freq_DSpinBox.setMinimum(pg_constr.sample_rate.min)
        self._pgs.gen_sample_freq_DSpinBox.setMaximum(pg_constr.sample_rate.max)
        self._pgs.gen_activation_config_ComboBox.clear()
        self._pgs.gen_activation_config_ComboBox.addItems(list(pg_constr.activation_config.keys()))
        for label, widget1, widget2 in self._analog_chnl_setting_widgets.values():
            widget1.setRange(pg_constr.a_ch_amplitude.min, pg_constr.a_ch_amplitude.max)
            widget2.setRange(pg_constr.a_ch_offset.min, pg_constr.a_ch_offset.max)
        for label, widget1, widget2 in self._digital_chnl_setting_widgets.values():
            widget1.setRange(pg_constr.d_ch_low.min, pg_constr.d_ch_low.max)
            widget2.setRange(pg_constr.d_ch_high.min, pg_constr.d_ch_high.max)

        # Set widget values/content
        self.pulse_generator_settings_updated(self.pulsedmasterlogic().pulse_generator_settings)
        return

    def _deactivate_generator_settings_ui(self):
        """
        De-initialize the dialog for the pulse generator settings.
        """
        self._pgs.close()
        return

    def __create_analog_channel_setting_widgets(self):
        """
        Dynamically creates analog channel setting input widgets (like analog offset and pp-voltage)
        from the currently set activation config.
        """
        if self._analog_chnl_setting_widgets:
            self.log.debug('Unable to create analog channel settings. Widgets already exist.')
            return

        analog_channels = set()
        for cfg in self.pulsedmasterlogic().pulse_generator_constraints.activation_config.values():
            for ach in (chnl for chnl in cfg if chnl.startswith('a')):
                analog_channels.add(ach)
        analog_channels = natural_sort(analog_channels)

        for i, chnl in enumerate(analog_channels, 1):
            self._analog_chnl_setting_widgets[chnl] = (
                QtWidgets.QLabel(text=chnl + ':'), ScienDSpinBox(), ScienDSpinBox())
            self._analog_chnl_setting_widgets[chnl][0].setAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self._analog_chnl_setting_widgets[chnl][1].setAlignment(
                QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            self._analog_chnl_setting_widgets[chnl][1].setSizePolicy(
                QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            self._analog_chnl_setting_widgets[chnl][1].setDecimals(6)
            self._analog_chnl_setting_widgets[chnl][1].setSuffix('V')
            self._analog_chnl_setting_widgets[chnl][2].setAlignment(
                QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            self._analog_chnl_setting_widgets[chnl][2].setSizePolicy(
                QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            self._analog_chnl_setting_widgets[chnl][2].setDecimals(6)
            self._analog_chnl_setting_widgets[chnl][2].setSuffix('V')
            self._pgs.ach_groupBox.layout().addWidget(
                self._analog_chnl_setting_widgets[chnl][0], i, 0)
            self._pgs.ach_groupBox.layout().addWidget(
                self._analog_chnl_setting_widgets[chnl][1], i, 1)
            self._pgs.ach_groupBox.layout().addWidget(
                self._analog_chnl_setting_widgets[chnl][2], i, 2)
        return

    def __create_digital_channel_setting_widgets(self):
        """
        Dynamically creates digital channel setting input widgets (like analog offset and pp-voltage)
        from the currently set activation config.
        """
        if self._digital_chnl_setting_widgets:
            self.log.debug('Unable to create digital channel settings. Widgets already exist.')
            return

        digital_channels = set()
        for cfg in self.pulsedmasterlogic().pulse_generator_constraints.activation_config.values():
            for dch in (chnl for chnl in cfg if chnl.startswith('d')):
                digital_channels.add(dch)
        digital_channels = natural_sort(digital_channels)

        for i, chnl in enumerate(digital_channels, 1):
            self._digital_chnl_setting_widgets[chnl] = (
                QtWidgets.QLabel(text=chnl + ':'), ScienDSpinBox(), ScienDSpinBox())
            self._digital_chnl_setting_widgets[chnl][0].setAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self._digital_chnl_setting_widgets[chnl][1].setAlignment(
                QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            self._digital_chnl_setting_widgets[chnl][1].setSizePolicy(
                QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            self._digital_chnl_setting_widgets[chnl][1].setDecimals(6)
            self._digital_chnl_setting_widgets[chnl][1].setSuffix('V')
            self._digital_chnl_setting_widgets[chnl][2].setAlignment(
                QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            self._digital_chnl_setting_widgets[chnl][2].setSizePolicy(
                QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            self._digital_chnl_setting_widgets[chnl][2].setDecimals(6)
            self._digital_chnl_setting_widgets[chnl][2].setSuffix('V')
            self._pgs.dch_groupBox.layout().addWidget(
                self._digital_chnl_setting_widgets[chnl][0], i, 0)
            self._pgs.dch_groupBox.layout().addWidget(
                self._digital_chnl_setting_widgets[chnl][1], i, 1)
            self._pgs.dch_groupBox.layout().addWidget(
                self._digital_chnl_setting_widgets[chnl][2], i, 2)
        return

    def apply_generator_settings(self):
        """ Apply the new settings """
        if self._mw.action_run_stop.isChecked():
            self.keep_former_generator_settings()
            return
        settings_dict = dict()
        settings_dict['sample_rate'] = self._pgs.gen_sample_freq_DSpinBox.value()
        settings_dict['activation_config'] = self._pgs.gen_activation_config_ComboBox.currentText()
        settings_dict['interleave'] = self._pgs.gen_use_interleave_CheckBox.isChecked()

        analog_ppamp = dict()
        analog_offset = dict()
        for chnl, (label, widget1, widget2) in self._analog_chnl_setting_widgets.items():
            analog_ppamp[chnl] = widget1.value()
            analog_offset[chnl] = widget2.value()
        settings_dict['analog_levels'] = (analog_ppamp, analog_offset)

        digital_low = dict()
        digital_high = dict()
        for chnl, (label, widget1, widget2) in self._digital_chnl_setting_widgets.items():
            digital_low[chnl] = widget1.value()
            digital_high[chnl] = widget2.value()
        settings_dict['digital_levels'] = (digital_low, digital_high)

        self.pulsedmasterlogic().set_pulse_generator_settings(settings_dict)
        return

    def keep_former_generator_settings(self):
        """ Keep the old settings """
        self.pulse_generator_settings_updated(self.pulsedmasterlogic().pulse_generator_settings)
        return

    def show_generator_settings(self):
        """ Open the Pulse generator settings window. """
        self._pgs.exec_()
        return

    ###########################################################################
    #          Predefined methods settings dialog related methods             #
    ###########################################################################
    def _activate_predefined_methods_settings_ui(self):
        """ Initialize, connect and configure the pulse generator settings to be displayed in the
        editor.
        """
        # create all GUI elements and check all boxes listed in the methods to show
        for method_name in natural_sort(self.pulsedmasterlogic().generate_methods):
            # create checkboxes for the config dialogue
            name_checkbox = 'checkbox_' + method_name
            setattr(self._pm_cfg, name_checkbox, QtWidgets.QCheckBox(self._pm_cfg.scrollArea))
            checkbox = getattr(self._pm_cfg, name_checkbox)
            checkbox.setObjectName(name_checkbox)
            checkbox.setText(method_name)
            checkbox.setChecked(method_name in self._predefined_methods_to_show)
            self._pm_cfg.verticalLayout.addWidget(checkbox)

        # apply the chosen methods to the methods dialogue
        self.apply_predefined_methods_config()
        return

    def _deactivate_predefined_methods_settings_ui(self):
        self._pm_cfg.close()
        return

    def show_predefined_methods_config(self):
        """ Opens the Window for the config of predefined methods."""
        self._pm_cfg.show()
        self._pm_cfg.raise_()
        return

    def keep_former_predefined_methods_config(self):
        for method_name in self.pulsedmasterlogic().generate_methods:
            groupbox = getattr(self._pm, method_name + '_GroupBox')
            checkbox = getattr(self._pm_cfg, 'checkbox_' + method_name)
            checkbox.setChecked(groupbox.isVisible())
        return

    def apply_predefined_methods_config(self):
        self._predefined_methods_to_show = list()
        for method_name in self.pulsedmasterlogic().generate_methods:
            groupbox = getattr(self._pm, method_name + '_GroupBox')
            checkbox = getattr(self._pm_cfg, 'checkbox_' + method_name)
            groupbox.setVisible(checkbox.isChecked())
            if checkbox.isChecked():
                self._predefined_methods_to_show.append(method_name)

        self._pm.hintLabel.setVisible(len(self._predefined_methods_to_show) == 0)
        return

    ###########################################################################
    #                Predefined Methods tab related methods                   #
    ###########################################################################
    def _activate_predefined_methods_ui(self):
        # Contraint some widgets by hardware constraints
        self._pm_apply_hardware_constraints()

        # Dynamically create GUI elements for global parameters
        self._channel_selection_comboboxes = list()  # List of created channel selection ComboBoxes
        self._global_param_widgets = list()  # List of all other created global parameter widgets
        self._create_pm_global_params()
        self.generation_parameters_updated(self.pulsedmasterlogic().generation_parameters)

        # Dynamically create GUI elements for predefined methods
        self._pm.gen_buttons = dict()
        self._pm.samplo_buttons = dict()
        self._pm.method_param_widgets = dict()
        self._create_predefined_methods()
        return

    def _deactivate_predefined_methods_ui(self):
        # TODO: Implement
        pass

    def _pm_apply_hardware_constraints(self):
        # TODO: Implement
        pass

    def _create_pm_global_params(self):
        """
        Create GUI elements for global parameters of sequence generation
        """
        col_count = 0
        row_count = 1
        combo_count = 0
        for param, value in self.pulsedmasterlogic().generation_parameters.items():
            # Do not create widget for laser_channel since this widget is already part of the pulse
            # editor tab.
            if param in ('laser_channel', 'sync_channel', 'gate_channel'):
                continue

            # Create ComboBoxes for parameters ending on '_channel' to only be able to select
            # active channels. Also save references to those widgets in a list for easy access in
            # case of a change of channel activation config.
            if param.endswith('_channel') and (value is None or type(value) is str):
                widget = QtWidgets.QComboBox()
                widget.setObjectName('global_param_' + param)
                widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
                widget.addItem('')
                widget.addItems(natural_sort(self.pulsedmasterlogic().digital_channels))
                widget.addItems(natural_sort(self.pulsedmasterlogic().analog_channels))
                index = widget.findText(value)
                if index >= 0:
                    widget.setCurrentIndex(index)
                label = QtWidgets.QLabel(param + ':')
                label.setAlignment(QtCore.Qt.AlignRight)
                self._pm.global_param_gridLayout.addWidget(label, 0, combo_count, QtCore.Qt.AlignVCenter)
                self._pm.global_param_gridLayout.addWidget(widget, 0, combo_count + 1)
                combo_count += 2
                self._channel_selection_comboboxes.append(widget)
                widget.currentIndexChanged.connect(self.generation_parameters_changed)
                continue

            # Create all other widgets for int, float, bool and str and save them in a list for
            # later access. Also connect edited signals.
            if isinstance(value, str) or value is None:
                if value is None:
                    value = ''
                widget = QtWidgets.QLineEdit()
                widget.setText(value)
                widget.editingFinished.connect(self.generation_parameters_changed)
            elif type(value) is int:
                widget = ScienSpinBox()
                widget.setValue(value)
                widget.editingFinished.connect(self.generation_parameters_changed)
            elif type(value) is float:
                widget = ScienDSpinBox()
                widget.setValue(value)
                if 'amp' in param or 'volt' in param:
                    widget.setSuffix('V')
                elif 'freq' in param:
                    widget.setSuffix('Hz')
                elif any(x in param for x in ('tau', 'period', 'time', 'delay', 'laser_length')):
                    widget.setSuffix('s')
                widget.editingFinished.connect(self.generation_parameters_changed)
            elif type(value) is bool:
                widget = QtWidgets.QCheckBox()
                widget.setChecked(value)
                widget.stateChanged.connect(self.generation_parameters_changed)

            widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)

            # Create label
            label = QtWidgets.QLabel(param + ':')
            label.setAlignment(QtCore.Qt.AlignRight)

            # Rename widget to a naming convention
            widget.setObjectName('global_param_' + param)

            # Save widget in list
            self._global_param_widgets.append(widget)

            # Add widget to GUI layout
            if col_count > 4:
                col_count = 0
                row_count += 1
            self._pm.global_param_gridLayout.addWidget(label, row_count, col_count, QtCore.Qt.AlignVCenter)
            self._pm.global_param_gridLayout.addWidget(widget, row_count, col_count + 1)
            col_count += 2
        spacer = QtWidgets.QSpacerItem(20, 0,
                                       QtWidgets.QSizePolicy.Expanding,
                                       QtWidgets.QSizePolicy.Minimum)
        if row_count > 1:
            self._pm.global_param_gridLayout.addItem(spacer, 1, 6)
        else:
            self._pm.global_param_gridLayout.addItem(spacer, 0, max(col_count, combo_count))
        return

    def _create_predefined_methods(self):
        """
        Initializes the GUI elements for the predefined methods
        """
        # Empty reference containers
        self._pm.gen_buttons = dict()
        self._pm.samplo_buttons = dict()
        self._pm.method_param_widgets = dict()

        method_params = self.pulsedmasterlogic().generate_method_params
        for method_name in natural_sort(self.pulsedmasterlogic().generate_methods):
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
            samplo_button = QtWidgets.QPushButton(groupBox)
            samplo_button.setText('GenSampLo')
            samplo_button.setObjectName('samplo_' + method_name)
            samplo_button.clicked.connect(self.generate_predefined_clicked)
            gridLayout.addWidget(gen_button, 0, 0, 1, 1)
            gridLayout.addWidget(samplo_button, 1, 0, 1, 1)
            self._pm.gen_buttons[method_name] = gen_button
            self._pm.samplo_buttons[method_name] = samplo_button

            # run through all parameters of the current method and create the widgets
            self._pm.method_param_widgets[method_name] = dict()
            for param_index, (param_name, param) in enumerate(method_params[method_name].items()):
                    # create a label for the parameter
                    param_label = QtWidgets.QLabel(groupBox)
                    param_label.setText(param_name)
                    # create proper input widget for the parameter depending on default value type
                    if type(param) is bool:
                        input_obj = QtWidgets.QCheckBox(groupBox)
                        input_obj.setChecked(param)
                    elif type(param) is float:
                        input_obj = ScienDSpinBox(groupBox)
                        if 'amp' in param_name or 'volt' in param_name:
                            input_obj.setSuffix('V')
                        elif 'freq' in param_name:
                            input_obj.setSuffix('Hz')
                        elif 'time' in param_name or 'period' in param_name or 'tau' in param_name:
                            input_obj.setSuffix('s')
                        input_obj.setMinimumSize(QtCore.QSize(80, 0))
                        input_obj.setValue(param)
                    elif type(param) is int:
                        input_obj = ScienSpinBox(groupBox)
                        input_obj.setValue(param)
                    elif type(param) is str:
                        input_obj = QtWidgets.QLineEdit(groupBox)
                        input_obj.setMinimumSize(QtCore.QSize(80, 0))
                        input_obj.setText(param)
                    elif issubclass(type(param), Enum):
                        input_obj = QtWidgets.QComboBox(groupBox)
                        for option in type(param):
                            input_obj.addItem(option.name, option)
                        input_obj.setCurrentText(param.name)
                        # Set size constraints
                        input_obj.setMinimumSize(QtCore.QSize(80, 0))
                    else:
                        self.log.error('The predefined method "{0}" has an argument "{1}" which '
                                       'has no default argument or an invalid type (str, float, '
                                       'int, bool or Enum allowed)!\nCreation of the viewbox aborted.'
                                       ''.format('generate_' + method_name, param_name))
                        continue
                    # Adjust size policy
                    input_obj.setMinimumWidth(75)
                    input_obj.setMaximumWidth(100)
                    gridLayout.addWidget(param_label, 0, param_index + 1, 1, 1)
                    gridLayout.addWidget(input_obj, 1, param_index + 1, 1, 1)
                    self._pm.method_param_widgets[method_name][param_name] = input_obj
            h_spacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Expanding,
                                             QtWidgets.QSizePolicy.Minimum)
            gridLayout.addItem(h_spacer, 1, param_index + 2, 1, 1)

            # attach the GroupBox widget to the predefined methods widget.
            setattr(self._pm, method_name + '_GroupBox', groupBox)
            self._pm.verticalLayout.addWidget(groupBox)
        self._pm.verticalLayout.addStretch()
        return

    ###########################################################################
    #                   Pulse Generator tab related methods                   #
    ###########################################################################
    def _activate_pulse_generator_ui(self):
        """ Initialize, connect and configure the 'Pulse Generator' Tab.
        """
        # Configure widgets
        self._pg.curr_ensemble_length_DSpinBox.setRange(0, np.inf)
        self._pg.curr_ensemble_length_DSpinBox.setDecimals(6, dynamic_precision=False)
        self._pg.curr_ensemble_bins_SpinBox.setRange(0, 2**63-1)
        self._pg.curr_ensemble_laserpulses_SpinBox.setRange(0, 2**31-1)

        # initialize widgets
        self.generation_parameters_updated(self.pulsedmasterlogic().generation_parameters)
        self.fast_counter_settings_updated(self.pulsedmasterlogic().fast_counter_settings)
        self.update_block_dict(self.pulsedmasterlogic().saved_pulse_blocks)
        self.update_ensemble_dict(self.pulsedmasterlogic().saved_pulse_block_ensembles)
        return

    def _deactivate_pulse_generator_ui(self):
        """ Disconnects the configuration for 'Pulse Generator Tab.
        """
        # TODO: implement
        pass

    @QtCore.Slot(dict)
    def pulse_generator_settings_updated(self, settings_dict):
        """

        @param settings_dict
        @return:
        """
        # block signals
        self._pgs.gen_sample_freq_DSpinBox.blockSignals(True)
        self._pgs.gen_use_interleave_CheckBox.blockSignals(True)
        self._pgs.gen_activation_config_ComboBox.blockSignals(True)
        self._pgs.gen_analog_channels_lineEdit.blockSignals(True)
        self._pgs.gen_digital_channels_lineEdit.blockSignals(True)
        if hasattr(self, '_analog_chnl_setting_widgets'):
            for label, widget1, widget2 in self._analog_chnl_setting_widgets.values():
                widget1.blockSignals(True)
                widget2.blockSignals(True)
            for label, widget1, widget2 in self._digital_chnl_setting_widgets.values():
                widget1.blockSignals(True)
                widget2.blockSignals(True)
        self._pg.gen_laserchannel_ComboBox.blockSignals(True)
        self._pg.gen_syncchannel_ComboBox.blockSignals(True)
        self._pg.gen_gatechannel_ComboBox.blockSignals(True)
        if hasattr(self, '_channel_selection_comboboxes'):
            for widget in self._channel_selection_comboboxes:
                widget.blockSignals(True)

        # Set widgets
        if 'sample_rate' in settings_dict:
            self._pgs.gen_sample_freq_DSpinBox.setValue(settings_dict['sample_rate'])
        if 'activation_config' in settings_dict:
            config_name = settings_dict['activation_config'][0]
            digital_channels = natural_sort(
                (ch for ch in settings_dict['activation_config'][1] if ch.startswith('d')))
            analog_channels = natural_sort(
                (ch for ch in settings_dict['activation_config'][1] if ch.startswith('a')))
            index = self._pgs.gen_activation_config_ComboBox.findText(config_name)
            self._pgs.gen_activation_config_ComboBox.setCurrentIndex(index)
            digital_str = str(digital_channels).strip('[]').replace('\'', '').replace(',', ' |')
            analog_str = str(analog_channels).strip('[]').replace('\'', '').replace(',', ' |')
            self._pgs.gen_digital_channels_lineEdit.setText(digital_str)
            self._pgs.gen_analog_channels_lineEdit.setText(analog_str)

            # Update channel ComboBoxes
            former_laser_channel = self._pg.gen_laserchannel_ComboBox.currentText()
            self._pg.gen_laserchannel_ComboBox.clear()
            self._pg.gen_laserchannel_ComboBox.addItem('')
            self._pg.gen_laserchannel_ComboBox.addItems(digital_channels)
            self._pg.gen_laserchannel_ComboBox.addItems(analog_channels)
            if former_laser_channel in settings_dict['activation_config'][1]:
                index = self._pg.gen_laserchannel_ComboBox.findText(former_laser_channel)
                self._pg.gen_laserchannel_ComboBox.setCurrentIndex(index)
                self._pg.block_editor.set_laser_channel_is_digital(former_laser_channel.startswith('d'))

            former_sync_channel = self._pg.gen_syncchannel_ComboBox.currentText()
            self._pg.gen_syncchannel_ComboBox.clear()
            self._pg.gen_syncchannel_ComboBox.addItem('')
            self._pg.gen_syncchannel_ComboBox.addItems(digital_channels)
            self._pg.gen_syncchannel_ComboBox.addItems(analog_channels)
            if former_sync_channel in settings_dict['activation_config'][1]:
                index = self._pg.gen_syncchannel_ComboBox.findText(former_sync_channel)
                self._pg.gen_syncchannel_ComboBox.setCurrentIndex(index)

            former_gate_channel = self._pg.gen_gatechannel_ComboBox.currentText()
            self._pg.gen_gatechannel_ComboBox.clear()
            self._pg.gen_gatechannel_ComboBox.addItem('')
            self._pg.gen_gatechannel_ComboBox.addItems(digital_channels)
            self._pg.gen_gatechannel_ComboBox.addItems(analog_channels)
            if former_gate_channel in settings_dict['activation_config'][1]:
                index = self._pg.gen_gatechannel_ComboBox.findText(former_gate_channel)
                self._pg.gen_gatechannel_ComboBox.setCurrentIndex(index)

            if hasattr(self, '_channel_selection_comboboxes'):
                for widget in self._channel_selection_comboboxes:
                    former_channel = widget.currentText()
                    widget.clear()
                    widget.addItem('')
                    widget.addItems(analog_channels)
                    widget.addItems(digital_channels)
                    if former_channel in settings_dict['activation_config'][1]:
                        index = widget.findText(former_channel)
                        widget.setCurrentIndex(index)

            # Hide/Show analog and digital channel setting groupBoxes if no respective channel is
            # active.
            if len(analog_channels) == 0:
                self._pgs.ach_groupBox.hide()
            else:
                self._pgs.ach_groupBox.show()
            if len(digital_channels) == 0:
                self._pgs.dch_groupBox.hide()
            else:
                self._pgs.dch_groupBox.show()

            # Hide/Show channel settings for inactive/active channels
            for chnl, (label, widget1, widget2) in self._analog_chnl_setting_widgets.items():
                if chnl in analog_channels:
                    label.show()
                    widget1.show()
                    widget2.show()
                else:
                    label.hide()
                    widget1.hide()
                    widget2.hide()
            for chnl, (label, widget1, widget2) in self._digital_chnl_setting_widgets.items():
                if chnl in digital_channels:
                    label.show()
                    widget1.show()
                    widget2.show()
                else:
                    label.hide()
                    widget1.hide()
                    widget2.hide()

            # Set activation config in block editor
            self._pg.block_editor.set_activation_config(settings_dict['activation_config'][1])
        if 'analog_levels' in settings_dict:
            for chnl, pp_amp in settings_dict['analog_levels'][0].items():
                self._analog_chnl_setting_widgets[chnl][1].setValue(pp_amp)
            for chnl, offset in settings_dict['analog_levels'][1].items():
                self._analog_chnl_setting_widgets[chnl][2].setValue(offset)
        if 'digital_levels' in settings_dict:
            for chnl, low_voltage in settings_dict['digital_levels'][0].items():
                self._digital_chnl_setting_widgets[chnl][1].setValue(low_voltage)
            for chnl, high_voltage in settings_dict['digital_levels'][1].items():
                self._digital_chnl_setting_widgets[chnl][2].setValue(high_voltage)
        if 'interleave' in settings_dict:
            self._pgs.gen_use_interleave_CheckBox.setChecked(settings_dict['interleave'])
        if 'flags' in settings_dict:
            self._sg.sequence_editor.set_available_flags(settings_dict['flags'])

        # unblock signals
        self._pgs.gen_sample_freq_DSpinBox.blockSignals(False)
        self._pgs.gen_use_interleave_CheckBox.blockSignals(False)
        self._pgs.gen_activation_config_ComboBox.blockSignals(False)
        self._pgs.gen_analog_channels_lineEdit.blockSignals(False)
        self._pgs.gen_digital_channels_lineEdit.blockSignals(False)
        if hasattr(self, '_analog_chnl_setting_widgets'):
            for label, widget1, widget2 in self._analog_chnl_setting_widgets.values():
                widget1.blockSignals(False)
                widget2.blockSignals(False)
            for label, widget1, widget2 in self._digital_chnl_setting_widgets.values():
                widget1.blockSignals(False)
                widget2.blockSignals(False)
        self._pg.gen_laserchannel_ComboBox.blockSignals(False)
        self._pg.gen_syncchannel_ComboBox.blockSignals(False)
        self._pg.gen_gatechannel_ComboBox.blockSignals(False)
        if hasattr(self, '_channel_selection_comboboxes'):
            for widget in self._channel_selection_comboboxes:
                widget.blockSignals(False)
        return

    @QtCore.Slot()
    def generation_parameters_changed(self):
        """

        @return:
        """
        settings_dict = dict()
        settings_dict['laser_channel'] = self._pg.gen_laserchannel_ComboBox.currentText()
        settings_dict['sync_channel'] = self._pg.gen_syncchannel_ComboBox.currentText()
        settings_dict['gate_channel'] = self._pg.gen_gatechannel_ComboBox.currentText()
        # Add channel specifiers from predefined methods tab
        if hasattr(self, '_channel_selection_comboboxes'):
            for combobox in self._channel_selection_comboboxes:
                # cut away 'global_param_' from beginning of the objectName
                param_name = combobox.objectName()[13:]
                settings_dict[param_name] = combobox.currentText()
        # Add remaining global parameter widgets
        if hasattr(self, '_global_param_widgets'):
            for widget in self._global_param_widgets:
                # cut away 'global_param_' from beginning of the objectName
                param_name = widget.objectName()[13:]
                if hasattr(widget, 'isChecked'):
                    settings_dict[param_name] = widget.isChecked()
                elif hasattr(widget, 'value'):
                    settings_dict[param_name] = widget.value()
                elif hasattr(widget, 'text'):
                    settings_dict[param_name] = widget.text()

        self.pulsedmasterlogic().set_generation_parameters(settings_dict)

        self._pg.block_editor.set_laser_channel_is_digital(settings_dict['laser_channel'].startswith('d'))
        return

    @QtCore.Slot(dict)
    def generation_parameters_updated(self, settings_dict):
        """

        @param settings_dict:
        @return:
        """
        # block signals
        self._pg.gen_laserchannel_ComboBox.blockSignals(True)
        self._pg.gen_syncchannel_ComboBox.blockSignals(True)
        self._pg.gen_gatechannel_ComboBox.blockSignals(True)

        if 'laser_channel' in settings_dict:
            index = self._pg.gen_laserchannel_ComboBox.findText(settings_dict['laser_channel'])
            self._pg.gen_laserchannel_ComboBox.setCurrentIndex(index)
            self._pg.block_editor.set_laser_channel_is_digital(settings_dict['laser_channel'].startswith('d'))
        if 'sync_channel' in settings_dict:
            index = self._pg.gen_syncchannel_ComboBox.findText(settings_dict['sync_channel'])
            self._pg.gen_syncchannel_ComboBox.setCurrentIndex(index)
        if 'gate_channel' in settings_dict:
            index = self._pg.gen_gatechannel_ComboBox.findText(settings_dict['gate_channel'])
            self._pg.gen_gatechannel_ComboBox.setCurrentIndex(index)
        if hasattr(self, '_channel_selection_comboboxes'):
            for combobox in self._channel_selection_comboboxes:
                param_name = combobox.objectName()[13:]
                if param_name in settings_dict:
                    combobox.blockSignals(True)
                    index = combobox.findText(settings_dict[param_name])
                    combobox.setCurrentIndex(index)
                    combobox.blockSignals(False)
        if hasattr(self, '_global_param_widgets'):
            for widget in self._global_param_widgets:
                param_name = widget.objectName()[13:]
                if param_name in settings_dict:
                    widget.blockSignals(True)
                    if hasattr(widget, 'setChecked'):
                        widget.setChecked(settings_dict[param_name])
                    elif hasattr(widget, 'setValue'):
                        widget.setValue(settings_dict[param_name])
                    elif hasattr(widget, 'setText'):
                        widget.setText(settings_dict[param_name])
                    widget.blockSignals(False)

        # unblock signals
        self._pg.gen_laserchannel_ComboBox.blockSignals(False)
        self._pg.gen_syncchannel_ComboBox.blockSignals(False)
        self._pg.gen_gatechannel_ComboBox.blockSignals(False)
        return

    @QtCore.Slot()
    def block_add_last_clicked(self):
        """

        @return:
        """
        self._pg.block_editor.add_elements(1, self._pg.block_editor.rowCount())
        return

    @QtCore.Slot()
    def block_del_last_clicked(self):
        """

        @return:
        """
        self._pg.block_editor.remove_elements(1, self._pg.block_editor.rowCount() - 1)
        return

    @QtCore.Slot()
    def block_add_sel_clicked(self):
        """

        @return:
        """
        index = self._pg.block_editor.currentRow()
        self._pg.block_editor.add_elements(1, index + 1)
        return

    @QtCore.Slot()
    def block_del_sel_clicked(self):
        """

        @return:
        """
        index = self._pg.block_editor.currentRow()
        self._pg.block_editor.remove_elements(1, index)
        return

    @QtCore.Slot()
    def block_clear_clicked(self):
        """

        @return:
        """
        self._pg.block_editor.clear()
        return

    @QtCore.Slot()
    def organizer_add_last_clicked(self):
        """

        @return:
        """
        self._pg.block_organizer.add_blocks(1, self._pg.block_organizer.rowCount())
        return

    @QtCore.Slot()
    def organizer_del_last_clicked(self):
        """

        @return:
        """
        self._pg.block_organizer.remove_blocks(1, self._pg.block_organizer.rowCount() - 1)
        return

    @QtCore.Slot()
    def organizer_add_sel_clicked(self):
        """

        @return:
        """
        index = self._pg.block_organizer.currentRow()
        self._pg.block_organizer.add_blocks(1, index + 1)
        return

    @QtCore.Slot()
    def organizer_del_sel_clicked(self):
        """

        @return:
        """
        index = self._pg.block_organizer.currentRow()
        self._pg.block_organizer.remove_blocks(1, index)
        return

    @QtCore.Slot()
    def organizer_clear_clicked(self):
        """

        @return:
        """
        self._pg.block_organizer.clear()
        return

    @QtCore.Slot()
    def editor_generate_block_clicked(self):
        name = self._pg.curr_block_name_LineEdit.text()
        if not name:
            self.log.error('No name has been entered for the PulseBlock to be generated.')
            return
        block_object = self._pg.block_editor.get_block()
        block_object.name = name
        self.pulsedmasterlogic().save_pulse_block(block_object)
        return

    @QtCore.Slot()
    def editor_delete_block_clicked(self):
        name = self._pg.saved_blocks_ComboBox.currentText()
        self.pulsedmasterlogic().delete_pulse_block(name)
        return

    @QtCore.Slot()
    def editor_delete_all_blocks_clicked(self):
        # Prompt user and ask for confirmation
        result = QtWidgets.QMessageBox.question(
            self._mw,
            'Qudi: Delete all PulseBlocks?',
            'Do you really want to delete all saved PulseBlocks?',
            QtWidgets.QMessageBox.Yes,
            QtWidgets.QMessageBox.No)
        if result == QtWidgets.QMessageBox.Yes:
            self.pulsedmasterlogic().delete_all_pulse_blocks()
        return

    @QtCore.Slot()
    def editor_load_block_clicked(self):
        name = self._pg.saved_blocks_ComboBox.currentText()
        block = self.pulsedmasterlogic().saved_pulse_blocks[name]

        # Do not load PulseBlock into editor if channel activations do not match
        current_channels = self.pulsedmasterlogic().pulse_generator_settings['activation_config'][1]
        if block.channel_set != current_channels:
            self.log.error('Can not load PulseBlock "{0}" into editor.\nCurrent channel activation '
                           '"{1}" does not match channel activation "{2}" used during generation '
                           'of PulseBlock to load.'
                           ''.format(name, current_channels, block.channel_set))
            return

        self._pg.block_editor.load_block(block)
        self._pg.curr_block_name_LineEdit.setText(name)
        return

    @QtCore.Slot()
    def editor_generate_ensemble_clicked(self):
        name = self._pg.curr_ensemble_name_LineEdit.text()
        if not name:
            self.log.error('No name has been entered for the PulseBlockEnsemble to be generated.')
            return
        rotating_frame = self._pg.curr_ensemble_rot_frame_CheckBox.isChecked()
        self._pg.block_organizer.set_rotating_frame(rotating_frame)
        ensemble_object = self._pg.block_organizer.get_ensemble()
        ensemble_object.name = name
        self.pulsedmasterlogic().save_block_ensemble(ensemble_object)
        length_s, length_bins, lasers = self.pulsedmasterlogic().get_ensemble_info(ensemble_object)
        self._pg.curr_ensemble_length_DSpinBox.setValue(length_s)
        self._pg.curr_ensemble_bins_SpinBox.setValue(length_bins)
        self._pg.curr_ensemble_laserpulses_SpinBox.setValue(lasers)
        return

    @QtCore.Slot()
    def editor_delete_ensemble_clicked(self):
        name = self._pg.saved_ensembles_ComboBox.currentText()
        self.pulsedmasterlogic().delete_block_ensemble(name)
        return

    @QtCore.Slot()
    def editor_delete_all_ensembles_clicked(self):
        # Prompt user and ask for confirmation
        result = QtWidgets.QMessageBox.question(
            self._mw,
            'Qudi: Delete all PulseBlockEnsembles?',
            'Do you really want to delete all saved PulseBlockEnsembles?\n'
            'This will also delete all waveforms within the pulse generator memory.',
            QtWidgets.QMessageBox.Yes,
            QtWidgets.QMessageBox.No)
        if result == QtWidgets.QMessageBox.Yes:
            self.pulsedmasterlogic().delete_all_block_ensembles()
        return

    @QtCore.Slot()
    def editor_load_ensemble_clicked(self):
        name = self._pg.saved_ensembles_ComboBox.currentText()
        ensemble = self.pulsedmasterlogic().saved_pulse_block_ensembles[name]
        self._pg.block_organizer.load_ensemble(ensemble)
        self._pg.curr_ensemble_name_LineEdit.setText(name)
        self._pg.curr_ensemble_rot_frame_CheckBox.setChecked(ensemble.rotating_frame)

        length_s, length_bins, lasers = self.pulsedmasterlogic().get_ensemble_info(ensemble)
        self._pg.curr_ensemble_length_DSpinBox.setValue(length_s)
        self._pg.curr_ensemble_bins_SpinBox.setValue(length_bins)
        self._pg.curr_ensemble_laserpulses_SpinBox.setValue(lasers)
        return

    @QtCore.Slot(dict)
    def update_block_dict(self, block_dict):
        """

        @param block_dict:
        @return:
        """
        block_names = natural_sort(block_dict)
        # Check if a block has been added. In that case set the current index to the new one.
        # In all other cases try to maintain the current item and if it was removed, set the first.
        text_to_set = None
        if len(block_names) == self._pg.saved_blocks_ComboBox.count() + 1:
            for name in block_names:
                if self._pg.saved_blocks_ComboBox.findText(name) < 0:
                    text_to_set = name
        if text_to_set is None:
            text_to_set = self._pg.saved_blocks_ComboBox.currentText()

        self._pg.block_organizer.set_available_pulse_blocks(block_names)
        self._pg.saved_blocks_ComboBox.blockSignals(True)
        self._pg.saved_blocks_ComboBox.clear()
        self._pg.saved_blocks_ComboBox.addItems(block_names)
        index = self._pg.saved_blocks_ComboBox.findText(text_to_set)
        if index >= 0:
            self._pg.saved_blocks_ComboBox.setCurrentIndex(index)
        self._pg.block_organizer.set_available_pulse_blocks(block_names)
        self._pg.saved_blocks_ComboBox.blockSignals(False)
        return

    @QtCore.Slot(dict)
    def update_ensemble_dict(self, ensemble_dict):
        """

        @param ensemble_dict:
        @return:
        """
        ensemble_names = natural_sort(ensemble_dict)
        # Check if an ensemble has been added. In that case set the current index to the new one.
        # In all other cases try to maintain the current item and if it was removed, set the first.
        text_to_set = None
        if len(ensemble_names) == self._pg.gen_ensemble_ComboBox.count() + 1:
            for name in ensemble_names:
                if self._pg.gen_ensemble_ComboBox.findText(name) < 0:
                    text_to_set = name
        if text_to_set is None:
            text_to_set = self._pg.gen_ensemble_ComboBox.currentText()

        self._sg.sequence_editor.set_available_block_ensembles(ensemble_names)
        # block signals
        self._pg.gen_ensemble_ComboBox.blockSignals(True)
        self._pg.saved_ensembles_ComboBox.blockSignals(True)
        # update gen_sequence_ComboBox items
        self._pg.gen_ensemble_ComboBox.clear()
        self._pg.gen_ensemble_ComboBox.addItems(ensemble_names)
        self._pg.saved_ensembles_ComboBox.clear()
        self._pg.saved_ensembles_ComboBox.addItems(ensemble_names)
        index = self._pg.gen_ensemble_ComboBox.findText(text_to_set)
        if index >= 0:
            self._pg.gen_ensemble_ComboBox.setCurrentIndex(index)
            self._pg.saved_ensembles_ComboBox.setCurrentIndex(index)
        self._sg.sequence_editor.set_available_block_ensembles(ensemble_names)
        # unblock signals
        self._pg.gen_ensemble_ComboBox.blockSignals(False)
        self._pg.saved_ensembles_ComboBox.blockSignals(False)
        return

    @QtCore.Slot()
    def sample_ensemble_clicked(self):
        """
        This method is called when the user clicks on "Sample Ensemble"
        """
        # disable buttons
        self._pg.sample_ensemble_PushButton.setEnabled(False)
        self._pg.samplo_ensemble_PushButton.setEnabled(False)
        # Get the ensemble name from the ComboBox
        ensemble_name = self._pg.gen_ensemble_ComboBox.currentText()
        # Sample and upload the ensemble via logic module
        self.pulsedmasterlogic().sample_ensemble(ensemble_name, False)
        return

    @QtCore.Slot(object)
    def sample_ensemble_finished(self, ensemble):
        """
        This method
        """
        # enable buttons
        if not self.pulsedmasterlogic().status_dict['sampload_busy']:
            self._pg.sample_ensemble_PushButton.setEnabled(True)
            self._pg.samplo_ensemble_PushButton.setEnabled(True)
            # Reactivate predefined method buttons
            for button in self._pm.samplo_buttons.values():
                button.setEnabled(True)
        return

    @QtCore.Slot()
    def samplo_ensemble_clicked(self):
        """
        This method is called when the user clicks on "Sample + Load Ensemble"
        """
        # disable buttons
        self._pg.sample_ensemble_PushButton.setEnabled(False)
        self._pg.samplo_ensemble_PushButton.setEnabled(False)
        self._pg.load_ensemble_PushButton.setEnabled(False)
        # Get the ensemble name from the ComboBox
        ensemble_name = self._pg.gen_ensemble_ComboBox.currentText()
        # Sample, upload and load the ensemble via logic module
        self.pulsedmasterlogic().sample_ensemble(ensemble_name, True)
        return

    @QtCore.Slot()
    def load_ensemble_clicked(self):
        """
        This method
        """
        # disable button
        self._pg.load_ensemble_PushButton.setEnabled(False)
        # Get the ensemble name to be loaded from the ComboBox
        ensemble_name = self._pg.gen_ensemble_ComboBox.currentText()
        # Load ensemble into channles via logic module
        self.pulsedmasterlogic().load_ensemble(ensemble_name)
        return

    @QtCore.Slot(bool)
    def generate_predefined_clicked(self, button_obj=None):
        """

        @param button_obj:
        @return:
        """
        if isinstance(button_obj, bool):
            button_obj = self.sender()
        method_name = button_obj.objectName()
        if method_name.startswith('gen_'):
            sample_and_load = False
            method_name = method_name[4:]
        elif method_name.startswith('samplo_'):
            sample_and_load = True
            method_name = method_name[7:]
        else:
            self.log.error('Strange naming of generate buttons in predefined methods occured.')
            return

        # get parameters from input widgets
        # Store parameters together with the parameter names in a dictionary
        param_dict = dict()
        for param_name, widget in self._pm.method_param_widgets[method_name].items():
            if hasattr(widget, 'isChecked'):
                param_dict[param_name] = widget.isChecked()
            elif hasattr(widget, 'value'):
                param_dict[param_name] = widget.value()
            elif hasattr(widget, 'text'):
                param_dict[param_name] = widget.text()
            elif hasattr(widget, 'currentIndex') and hasattr(widget, 'itemData'):
                param_dict[param_name] = widget.itemData(widget.currentIndex())
            else:
                self.log.error('Not possible to get the value from the widgets, since it does not '
                               'have one of the possible access methods!')
                return

        if sample_and_load:
            # disable buttons
            for button in self._pm.gen_buttons.values():
                button.setEnabled(False)
            for button in self._pm.samplo_buttons.values():
                button.setEnabled(False)

        self.pulsedmasterlogic().generate_predefined_sequence(
            method_name, param_dict, sample_and_load)
        return

    @QtCore.Slot(object, bool)
    def predefined_generated(self, asset_name, is_sequence):
        # Enable all "Generate" buttons in predefined methods tab
        for button in self._pm.gen_buttons.values():
            button.setEnabled(True)

        # Enable all "GenSampLo" buttons in predefined methods tab if generation failed or
        # "sampload_busy" flag in PulsedMasterLogic status_dict is False.
        # If generation was successful and "sampload_busy" flag is True, disable respective buttons
        # in "Pulse Generator" and "Sequence Generator" tab
        if asset_name is None or not self.pulsedmasterlogic().status_dict['sampload_busy']:
            for button in self._pm.samplo_buttons.values():
                button.setEnabled(True)
        else:
            self._pg.sample_ensemble_PushButton.setEnabled(False)
            self._pg.samplo_ensemble_PushButton.setEnabled(False)
            self._pg.load_ensemble_PushButton.setEnabled(False)
            if is_sequence:
                self._sg.load_sequence_PushButton.setEnabled(False)
                self._sg.samplo_sequence_PushButton.setEnabled(False)
                self._sg.sample_sequence_PushButton.setEnabled(False)
        return

    @QtCore.Slot(list)
    def waveform_list_updated(self, waveform_list):
        """

        @param list waveform_list:
        """
        # TODO: This method will be needed later on to implement an upload center
        pass

    ###########################################################################
    #                   Sequence Generator tab related methods                #
    ###########################################################################
    def _activate_sequence_generator_ui(self):
        self.update_sequence_dict(self.pulsedmasterlogic().saved_pulse_sequences)
        self._sg.curr_sequence_length_DSpinBox.setRange(0, np.inf)
        pulser_constr = self.pulsedmasterlogic().pulse_generator_constraints
        self._sg.sequence_editor.set_available_triggers(pulser_constr.event_triggers)
        self._sg.sequence_editor.set_available_flags(set(pulser_constr.flags))
        return

    def _deactivate_sequence_generator_ui(self):
        pass

    @QtCore.Slot()
    def sequence_add_last_clicked(self):
        """

        @return:
        """
        self._sg.sequence_editor.add_steps(1, self._sg.sequence_editor.rowCount())
        return

    @QtCore.Slot()
    def sequence_del_last_clicked(self):
        """

        @return:
        """
        self._sg.sequence_editor.remove_steps(1, self._sg.sequence_editor.rowCount() - 1)
        return

    @QtCore.Slot()
    def sequence_add_sel_clicked(self):
        """

        @return:
        """
        index = self._sg.sequence_editor.currentRow()
        self._sg.sequence_editor.add_steps(1, index + 1)
        return

    @QtCore.Slot()
    def sequence_del_sel_clicked(self):
        """

        @return:
        """
        index = self._sg.sequence_editor.currentRow()
        self._sg.sequence_editor.remove_steps(1, index)
        return

    @QtCore.Slot()
    def sequence_clear_clicked(self):
        """

        @return:
        """
        self._sg.sequence_editor.clear()
        return

    @QtCore.Slot()
    def editor_generate_sequence_clicked(self):
        name = self._sg.curr_sequence_name_LineEdit.text()
        if not name:
            self.log.error('No name has been entered for the PulseSequence to be generated.')
            return
        rotating_frame = self._sg.curr_sequence_rot_frame_CheckBox.isChecked()
        self._sg.sequence_editor.set_rotating_frame(rotating_frame)
        sequence_object = self._sg.sequence_editor.get_sequence()
        sequence_object.name = name
        self.pulsedmasterlogic().save_sequence(sequence_object)
        length_s, length_bins, lasers = self.pulsedmasterlogic().get_sequence_info(sequence_object)
        self._sg.curr_sequence_length_DSpinBox.setValue(length_s)
        self._sg.curr_sequence_bins_SpinBox.setValue(length_bins)
        self._sg.curr_sequence_laserpulses_SpinBox.setValue(lasers)
        return

    @QtCore.Slot()
    def editor_delete_sequence_clicked(self):
        name = self._sg.saved_sequences_ComboBox.currentText()
        self.pulsedmasterlogic().delete_sequence(name)
        return

    @QtCore.Slot()
    def editor_delete_all_sequences_clicked(self):
        # Prompt user and ask for confirmation
        result = QtWidgets.QMessageBox.question(
            self._mw,
            'Qudi: Delete all PulseSequences?',
            'Do you really want to delete all saved PulseSequences?\n'
            'This will also delete all sequences within the pulse generator memory.',
            QtWidgets.QMessageBox.Yes,
            QtWidgets.QMessageBox.No)
        if result == QtWidgets.QMessageBox.Yes:
            self.pulsedmasterlogic().delete_all_pulse_sequences()
        return

    @QtCore.Slot()
    def editor_load_sequence_clicked(self):
        name = self._sg.saved_sequences_ComboBox.currentText()
        sequence = self.pulsedmasterlogic().saved_pulse_sequences[name]
        self._sg.sequence_editor.load_sequence(sequence)
        self._sg.curr_sequence_name_LineEdit.setText(name)
        self._sg.curr_sequence_rot_frame_CheckBox.setChecked(sequence.rotating_frame)

        length_s, length_bins, lasers = self.pulsedmasterlogic().get_sequence_info(sequence)
        self._sg.curr_sequence_length_DSpinBox.setValue(length_s)
        self._sg.curr_sequence_bins_SpinBox.setValue(length_bins)
        self._sg.curr_sequence_laserpulses_SpinBox.setValue(lasers)
        return

    @QtCore.Slot(dict)
    def update_sequence_dict(self, sequence_dict):
        """

        @param sequence_dict:
        @return:
        """
        sequence_names = natural_sort(sequence_dict)
        # Check if a sequence has been added. In that case set the current index to the new one.
        # In all other cases try to maintain the current item and if it was removed, set the first.
        text_to_set = None
        if len(sequence_names) == self._sg.gen_sequence_ComboBox.count() + 1:
            for name in sequence_names:
                if self._sg.gen_sequence_ComboBox.findText(name) == -1:
                    text_to_set = name
        if text_to_set is None:
            text_to_set = self._sg.gen_sequence_ComboBox.currentText()

        # block signals
        self._sg.gen_sequence_ComboBox.blockSignals(True)
        self._sg.saved_sequences_ComboBox.blockSignals(True)
        # update gen_sequence_ComboBox items
        self._sg.gen_sequence_ComboBox.clear()
        self._sg.gen_sequence_ComboBox.addItems(sequence_names)
        self._sg.saved_sequences_ComboBox.clear()
        self._sg.saved_sequences_ComboBox.addItems(sequence_names)
        index = self._sg.gen_sequence_ComboBox.findText(text_to_set)
        if index >= 0:
            self._sg.gen_sequence_ComboBox.setCurrentIndex(index)
            self._sg.saved_sequences_ComboBox.setCurrentIndex(index)
        # unblock signals
        self._sg.gen_sequence_ComboBox.blockSignals(False)
        self._sg.saved_sequences_ComboBox.blockSignals(False)
        return

    @QtCore.Slot()
    def sample_sequence_clicked(self):
        """
        This method is called when the user clicks on "Sample + Upload Sequence"
        """
        # disable buttons
        self._sg.sample_sequence_PushButton.setEnabled(False)
        self._sg.samplo_sequence_PushButton.setEnabled(False)
        # Get the sequence name from the ComboBox
        sequence_name = self._sg.gen_sequence_ComboBox.currentText()
        # Sample the sequence via logic module
        self.pulsedmasterlogic().sample_sequence(sequence_name, False)
        return

    @QtCore.Slot(object)
    def sample_sequence_finished(self, sequence):
        """
        This method
        """
        # enable buttons
        if not self.pulsedmasterlogic().status_dict['sampload_busy']:
            self._sg.sample_sequence_PushButton.setEnabled(True)
            self._sg.samplo_sequence_PushButton.setEnabled(True)
            # Reactivate predefined method buttons
            for button in self._pm.samplo_buttons.values():
                button.setEnabled(True)
        return

    @QtCore.Slot()
    def samplo_sequence_clicked(self):
        """
        This method is called when the user clicks on "Sample + Load Sequence"
        """
        # disable buttons
        self._sg.sample_sequence_PushButton.setEnabled(False)
        self._sg.samplo_sequence_PushButton.setEnabled(False)
        self._sg.load_sequence_PushButton.setEnabled(False)
        # Get the sequence name from the ComboBox
        sequence_name = self._sg.gen_sequence_ComboBox.currentText()
        # Sample the sequence via logic module
        self.pulsedmasterlogic().sample_sequence(sequence_name, True)
        return

    @QtCore.Slot()
    def load_sequence_clicked(self):
        """
        This method
        """
        # disable button
        self._sg.load_sequence_PushButton.setEnabled(False)
        # Get the sequence name to be loaded from the ComboBox
        sequence_name = self._sg.gen_sequence_ComboBox.currentText()
        # Load sequence into channles via logic module
        self.pulsedmasterlogic().load_sequence(sequence_name)
        return

    @QtCore.Slot(list)
    def sequence_list_updated(self, sequence_list):
        """

        @param list sequence_list:
        """
        # TODO: This method will be needed later on to implement an upload center
        pass

    ###########################################################################
    #                      Analysis tab related methods                       #
    ###########################################################################
    def _activate_analysis_ui(self):
        """ Initialize, connect and configure the 'Analysis' Tab.
        """
        # Configure the main pulse analysis display:
        self.signal_image = pg.PlotDataItem(pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                                            style=QtCore.Qt.DotLine,
                                            symbol='o',
                                            symbolPen=palette.c1,
                                            symbolBrush=palette.c1,
                                            symbolSize=7)
        self.signal_image2 = pg.PlotDataItem(pen=pg.mkPen(palette.c4, style=QtCore.Qt.DotLine),
                                             style=QtCore.Qt.DotLine,
                                             symbol='o',
                                             symbolPen=palette.c4,
                                             symbolBrush=palette.c4,
                                             symbolSize=7)
        self._pa.pulse_analysis_PlotWidget.addItem(self.signal_image)
        self._pa.pulse_analysis_PlotWidget.addItem(self.signal_image2)
        self._pa.pulse_analysis_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        # Configure the fit of the data in the main pulse analysis display:
        self.fit_image = pg.PlotDataItem(pen=palette.c3)
        self._pa.pulse_analysis_PlotWidget.addItem(self.fit_image)

        # Configure the errorbars of the data in the main pulse analysis display:
        self.signal_image_error_bars = pg.ErrorBarItem(x=np.arange(10),
                                                       y=np.zeros(10),
                                                       top=0.,
                                                       bottom=0.,
                                                       pen=palette.c2)
        self.signal_image_error_bars2 = pg.ErrorBarItem(x=np.arange(10),
                                                        y=np.zeros(10),
                                                        top=0.,
                                                        bottom=0.,
                                                        pen=palette.c5)

        # Configure the second pulse analysis plot display:
        self.second_plot_image = pg.PlotDataItem(pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                                            style=QtCore.Qt.DotLine,
                                            symbol='o',
                                            symbolPen=palette.c1,
                                            symbolBrush=palette.c1,
                                            symbolSize=7)
        self.second_plot_image2 = pg.PlotDataItem(pen=pg.mkPen(palette.c4, style=QtCore.Qt.DotLine),
                                             style=QtCore.Qt.DotLine,
                                             symbol='o',
                                             symbolPen=palette.c4,
                                             symbolBrush=palette.c4,
                                             symbolSize=7)
        self._pa.pulse_analysis_second_PlotWidget.addItem(self.second_plot_image)
        self._pa.pulse_analysis_second_PlotWidget.addItem(self.second_plot_image2)
        self._pa.pulse_analysis_second_PlotWidget.showGrid(x=True, y=True, alpha=0.8)
        # Configure the fit of the data in the secondary pulse analysis display:
        self.second_fit_image = pg.PlotDataItem(pen=palette.c3)
        self._pa.pulse_analysis_second_PlotWidget.addItem(self.second_fit_image)

        # Fit settings dialog
        self._fsd = FitSettingsDialog(self.pulsedmasterlogic().fit_container)
        self._fsd.applySettings()
        self._pa.fit_param_fit_func_ComboBox.setFitFunctions(self._fsd.currentFits)
        self._pa.fit_param_alt_fit_func_ComboBox.setFitFunctions(self._fsd.currentFits)

        # set boundaries
        self._pa.ana_param_num_laser_pulse_SpinBox.setMinimum(1)
        self._pa.ana_param_record_length_DoubleSpinBox.setMinimum(0)
        self._pa.ana_param_record_length_DoubleSpinBox.setMaximum(np.inf)
        self._pa.time_param_ana_periode_DoubleSpinBox.setMinimum(0)
        self._pa.time_param_ana_periode_DoubleSpinBox.setMinimalStep(1)
        self._pa.ext_control_mw_freq_DoubleSpinBox.setMinimum(0)
        self._pa.ana_param_x_axis_start_ScienDSpinBox.setMaximum(np.inf)
        self._pa.ana_param_x_axis_start_ScienDSpinBox.setMinimum(-np.inf)
        self._pa.ana_param_x_axis_inc_ScienDSpinBox.setMaximum(np.inf)
        self._pa.ana_param_x_axis_inc_ScienDSpinBox.setMinimum(-np.inf)

        # apply hardware constraints
        self._pa_apply_hardware_constraints()

        # Recall StatusVars into widgets
        self._pa.ana_param_errorbars_CheckBox.blockSignals(True)
        self._pa.ana_param_errorbars_CheckBox.setChecked(self._ana_param_errorbars)
        self._pa.ana_param_errorbars_CheckBox.blockSignals(False)
        self.second_plot_changed(self.pulsedmasterlogic().alternative_data_type)

        # Update measurement, microwave and fast counter settings from logic
        self.measurement_settings_updated(self.pulsedmasterlogic().measurement_settings)
        self.fast_counter_settings_updated(self.pulsedmasterlogic().fast_counter_settings)
        self.microwave_settings_updated(self.pulsedmasterlogic().ext_microwave_settings)
        # Update analysis interval from logic
        self._pa.time_param_ana_periode_DoubleSpinBox.setValue(
            self.pulsedmasterlogic().timer_interval)

        self.toggle_error_bars(self._ana_param_errorbars)
        self.second_plot_changed(self.pulsedmasterlogic().alternative_data_type)
        return

    def _deactivate_analysis_ui(self):
        """ Disconnects the configuration for 'Analysis' Tab.
        """
        self._ana_param_errorbars = self._pa.ana_param_errorbars_CheckBox.isChecked()
        return

    def _pa_apply_hardware_constraints(self):
        """
        Retrieve the constraints from pulser and fast counter hardware and apply these constraints
        to the analysis tab GUI elements.
        """
        mw_constraints = self.pulsedmasterlogic().ext_microwave_constraints
        fc_constraints = self.pulsedmasterlogic().fast_counter_constraints
        # block signals
        self._pa.ext_control_mw_freq_DoubleSpinBox.blockSignals(True)
        self._pa.ext_control_mw_power_DoubleSpinBox.blockSignals(True)
        self._pa.ana_param_fc_bins_ComboBox.blockSignals(True)
        # apply constraints
        self._pa.ext_control_mw_freq_DoubleSpinBox.setRange(mw_constraints.min_frequency,
                                                            mw_constraints.max_frequency)
        self._pa.ext_control_mw_power_DoubleSpinBox.setRange(mw_constraints.min_power,
                                                             mw_constraints.max_power)
        self._pa.ana_param_fc_bins_ComboBox.clear()
        for binwidth in fc_constraints['hardware_binwidth_list']:
            self._pa.ana_param_fc_bins_ComboBox.addItem(str(binwidth))
        # unblock signals
        self._pa.ext_control_mw_freq_DoubleSpinBox.blockSignals(False)
        self._pa.ext_control_mw_power_DoubleSpinBox.blockSignals(False)
        self._pa.ana_param_fc_bins_ComboBox.blockSignals(False)
        return

    @QtCore.Slot()
    def measurement_data_updated(self):
        """

        @return:
        """
        signal_data = self.pulsedmasterlogic().signal_data
        signal_alt_data = self.pulsedmasterlogic().signal_alt_data
        measurement_error = self.pulsedmasterlogic().measurement_error

        # Adjust number of data sets to plot
        self.set_plot_dimensions()

        # Change second plot combobox if it has been changed in the logic
        self.second_plot_changed(self.pulsedmasterlogic().alternative_data_type)

        # create ErrorBarItems
        tmp_array = signal_data[0, 1:] - signal_data[0, :-1]
        if len(tmp_array) > 0:
            beamwidth = tmp_array.min() if tmp_array.min() > 0 else tmp_array.max()
        else:
            beamwidth = 0
        del tmp_array
        beamwidth /= 3
        self.signal_image_error_bars.setData(x=signal_data[0],
                                             y=signal_data[1],
                                             top=measurement_error[1],
                                             bottom=measurement_error[1],
                                             beam=beamwidth)
        if signal_data.shape[0] > 2 and measurement_error.shape[0] > 2:
            self.signal_image_error_bars2.setData(x=signal_data[0],
                                                  y=signal_data[2],
                                                  top=measurement_error[2],
                                                  bottom=measurement_error[2],
                                                  beam=beamwidth)

        # dealing with the actual signal plot
        self.signal_image.setData(x=signal_data[0], y=signal_data[1])
        if signal_data.shape[0] > 2:
            self.signal_image2.setData(x=signal_data[0], y=signal_data[2])

        # dealing with the secondary plot
        self.second_plot_image.setData(x=signal_alt_data[0], y=signal_alt_data[1])
        if signal_alt_data.shape[0] > 2:
            self.second_plot_image2.setData(x=signal_alt_data[0], y=signal_alt_data[2])

        # dealing with the error plot
        self.measuring_error_image.setData(x=measurement_error[0], y=measurement_error[1])
        if measurement_error.shape[0] > 2:
            self.measuring_error_image2.setData(x=measurement_error[0], y=measurement_error[2])

        # dealing with the laser plot
        self.update_laser_data()
        # dealing with the window plot
        self.update_timetrace_window()
        return

    @QtCore.Slot()
    def fit_clicked(self):
        """Fits the current data"""
        if self.sender().objectName().startswith('alt_fit_param'):
            current_fit_method = self._pa.fit_param_alt_fit_func_ComboBox.getCurrentFit()[0]
            fit_type = 'pulses_alt'
        elif self.sender().objectName().startswith('timetrace'):
            current_fit_method = self._ta.fit_method_comboBox.getCurrentFit()[0]
            fit_type = 'timetrace'
        else:
            current_fit_method = self._pa.fit_param_fit_func_ComboBox.getCurrentFit()[0]
            fit_type = 'pulses'
        self.pulsedmasterlogic().do_fit(current_fit_method, fit_type)
        return

    @QtCore.Slot(str, np.ndarray, object, str)
    def fit_data_updated(self, fit_method, fit_data, result, fit_type):
        """

        @param str fit_method:
        @param numpy.ndarray fit_data:
        @param object result:
        @param str fit_type: 'pulses' 'pulses_alt' or 'timetrace'
        @return:
        """
        # Get formatted result string
        if fit_method == 'No Fit':
            formatted_fitresult = 'No Fit'
        else:
            try:
                formatted_fitresult = units.create_formatted_output(result.result_str_dict)
            except:
                formatted_fitresult = 'This fit does not return formatted results'

        # block signals.
        # Clear text widget and show formatted result string.
        # Update plot and fit function selection ComboBox.
        # Unblock signals.
        if fit_type == 'pulses_alt':
            self._pa.fit_param_alt_fit_func_ComboBox.blockSignals(True)
            self._pa.alt_fit_param_results_TextBrowser.clear()
            self._pa.alt_fit_param_results_TextBrowser.setPlainText(formatted_fitresult)
            if fit_method:
                self._pa.fit_param_alt_fit_func_ComboBox.setCurrentFit(fit_method)
            self.second_fit_image.setData(x=fit_data[0], y=fit_data[1])
            if fit_method == 'No Fit' and self.second_fit_image in self._pa.pulse_analysis_second_PlotWidget.items():
                self._pa.pulse_analysis_second_PlotWidget.removeItem(self.second_fit_image)
            elif fit_method != 'No Fit' and self.second_fit_image not in self._pa.pulse_analysis_second_PlotWidget.items():
                self._pa.pulse_analysis_second_PlotWidget.addItem(self.second_fit_image)
            self._pa.fit_param_alt_fit_func_ComboBox.blockSignals(False)
        elif fit_type == 'pulses':
            self._pa.fit_param_fit_func_ComboBox.blockSignals(True)
            self._pa.fit_param_results_TextBrowser.clear()
            self._pa.fit_param_results_TextBrowser.setPlainText(formatted_fitresult)
            if fit_method:
                self._pa.fit_param_fit_func_ComboBox.setCurrentFit(fit_method)
            self.fit_image.setData(x=fit_data[0], y=fit_data[1])
            if fit_method == 'No Fit' and self.fit_image in self._pa.pulse_analysis_PlotWidget.items():
                self._pa.pulse_analysis_PlotWidget.removeItem(self.fit_image)
            elif fit_method != 'No Fit' and self.fit_image not in self._pa.pulse_analysis_PlotWidget.items():
                self._pa.pulse_analysis_PlotWidget.addItem(self.fit_image)
            self._pa.fit_param_fit_func_ComboBox.blockSignals(False)
        elif fit_type == 'timetrace':
            self._ta.fit_method_comboBox.blockSignals(True)
            self._ta.fit_result_textBrowser.clear()
            self._ta.fit_result_textBrowser.setPlainText(formatted_fitresult)
            if fit_method:
                self._ta.fit_method_comboBox.setCurrentFit(fit_method)
            self.ta_window_image_fit.setData(x=fit_data[0], y=fit_data[1])
            if fit_method == 'No Fit' and self.ta_window_image_fit in self._ta.window_PlotWidget.items():
                self._ta.window_PlotWidget.removeItem(self.ta_window_image_fit)
            elif fit_method != 'No Fit' and self.ta_window_image_fit not in self._ta.window_PlotWidget.items():
                self._ta.window_PlotWidget.addItem(self.ta_window_image_fit)
            self._ta.fit_method_comboBox.blockSignals(False)

        return

    @QtCore.Slot()
    def microwave_settings_changed(self):
        """ Shows or hides input widgets which are necessary if an external mw is turned on"""
        if self._mw.action_run_stop.isChecked():
            return

        use_ext_microwave = self._pa.ext_control_use_mw_CheckBox.isChecked()

        settings_dict = dict()
        settings_dict['use_ext_microwave'] = use_ext_microwave
        settings_dict['frequency'] = self._pa.ext_control_mw_freq_DoubleSpinBox.value()
        settings_dict['power'] = self._pa.ext_control_mw_power_DoubleSpinBox.value()

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

        self.pulsedmasterlogic().set_ext_microwave_settings(settings_dict)
        return

    @QtCore.Slot(dict)
    def microwave_settings_updated(self, settings_dict):
        """

        @param dict settings_dict:
        """
        # block signals
        self._pa.ext_control_mw_freq_DoubleSpinBox.blockSignals(True)
        self._pa.ext_control_mw_power_DoubleSpinBox.blockSignals(True)
        self._pa.ext_control_use_mw_CheckBox.blockSignals(True)

        if 'use_ext_microwave' in settings_dict:
            use_ext_microwave = settings_dict['use_ext_microwave']
            self._pa.ext_control_use_mw_CheckBox.setChecked(use_ext_microwave)
            # Set visibility
            self.toggle_microwave_settings_editor(settings_dict['use_ext_microwave'])
        if 'frequency' in settings_dict:
            self._pa.ext_control_mw_freq_DoubleSpinBox.setValue(settings_dict['frequency'])
        if 'power' in settings_dict:
            self._pa.ext_control_mw_power_DoubleSpinBox.setValue(settings_dict['power'])

        # unblock signals
        self._pa.ext_control_mw_freq_DoubleSpinBox.blockSignals(False)
        self._pa.ext_control_mw_power_DoubleSpinBox.blockSignals(False)
        self._pa.ext_control_use_mw_CheckBox.blockSignals(False)
        return

    def toggle_microwave_settings_editor(self, show_editor):
        """

        @param show_editor:
        @return:
        """
        if show_editor:
            self._pa.ext_control_mw_freq_Label.setVisible(True)
            self._pa.ext_control_mw_freq_DoubleSpinBox.setVisible(True)
            self._pa.ext_control_mw_power_Label.setVisible(True)
            self._pa.ext_control_mw_power_DoubleSpinBox.setVisible(True)
            self._pa.ext_control_mw_freq_DoubleSpinBox.setEnabled(True)
            self._pa.ext_control_mw_power_DoubleSpinBox.setEnabled(True)
        else:
            self._pa.ext_control_mw_freq_DoubleSpinBox.setEnabled(False)
            self._pa.ext_control_mw_power_DoubleSpinBox.setEnabled(False)
            self._pa.ext_control_mw_freq_Label.setVisible(False)
            self._pa.ext_control_mw_freq_DoubleSpinBox.setVisible(False)
            self._pa.ext_control_mw_power_Label.setVisible(False)
            self._pa.ext_control_mw_power_DoubleSpinBox.setVisible(False)
        return

    @QtCore.Slot(bool)
    def microwave_running_updated(self, is_running):
        """

        @return:
        """
        pass

    @QtCore.Slot()
    def fast_counter_settings_changed(self):
        """

        @return:
        """
        if self._mw.action_run_stop.isChecked():
            return
        settings_dict = dict()
        settings_dict['record_length'] = self._pa.ana_param_record_length_DoubleSpinBox.value()
        settings_dict['bin_width'] = float(self._pa.ana_param_fc_bins_ComboBox.currentText())
        self.pulsedmasterlogic().set_fast_counter_settings(settings_dict)
        return

    @QtCore.Slot(dict)
    def fast_counter_settings_updated(self, settings_dict):
        """

        @param dict settings_dict:
        """
        # block signals
        self._pa.ana_param_record_length_DoubleSpinBox.blockSignals(True)
        self._pa.ana_param_fc_bins_ComboBox.blockSignals(True)
        # set widgets
        if 'record_length' in settings_dict:
            self._pa.ana_param_record_length_DoubleSpinBox.setValue(settings_dict['record_length'])
        if 'bin_width' in settings_dict:
            index = self._pa.ana_param_fc_bins_ComboBox.findText(str(settings_dict['bin_width']))
            self._pa.ana_param_fc_bins_ComboBox.setCurrentIndex(index)
        if 'is_gated' in settings_dict:
            if settings_dict.get('is_gated'):
                self._pg.gen_gatechannel_ComboBox.setEnabled(True)
            else:
                self._pg.gen_gatechannel_ComboBox.setEnabled(False)
                self.pulsedmasterlogic().set_generation_parameters(gate_channel='')

        # unblock signals
        self._pa.ana_param_record_length_DoubleSpinBox.blockSignals(False)
        self._pa.ana_param_fc_bins_ComboBox.blockSignals(False)
        return

    @QtCore.Slot()
    def measurement_settings_changed(self):
        """

        @return:
        """
        # Do nothing if measurement is already running
        if self._mw.action_run_stop.isChecked():
            return

        settings_dict = dict()
        settings_dict['invoke_settings'] = self._pa.ana_param_invoke_settings_CheckBox.isChecked()
        settings_dict['laser_ignore_list'] = list()
        if self._pa.ana_param_ignore_first_CheckBox.isChecked():
            settings_dict['laser_ignore_list'].append(0)
        if self._pa.ana_param_ignore_last_CheckBox.isChecked():
            settings_dict['laser_ignore_list'].append(-1)
        settings_dict['alternating'] = self._pa.ana_param_alternating_CheckBox.isChecked()
        settings_dict['number_of_lasers'] = self._pa.ana_param_num_laser_pulse_SpinBox.value()
        vals_start = self._pa.ana_param_x_axis_start_ScienDSpinBox.value()
        vals_incr = self._pa.ana_param_x_axis_inc_ScienDSpinBox.value()
        num_of_ticks = max(1, settings_dict['number_of_lasers'] - len(
            settings_dict['laser_ignore_list']))
        if settings_dict['alternating'] and num_of_ticks > 1:
            num_of_ticks //= 2
        controlled_variable = np.arange(num_of_ticks, dtype=float)
        settings_dict['controlled_variable'] = controlled_variable * vals_incr + vals_start

        self.pulsedmasterlogic().set_measurement_settings(settings_dict)
        return

    @QtCore.Slot(dict)
    def measurement_settings_updated(self, settings_dict):
        """

        @param dict settings_dict:
        """
        # block signals
        self._pa.ana_param_ignore_first_CheckBox.blockSignals(True)
        self._pa.ana_param_ignore_last_CheckBox.blockSignals(True)
        self._pa.ana_param_alternating_CheckBox.blockSignals(True)
        self._pa.ana_param_num_laser_pulse_SpinBox.blockSignals(True)
        self._pa.ana_param_x_axis_start_ScienDSpinBox.blockSignals(True)
        self._pa.ana_param_x_axis_inc_ScienDSpinBox.blockSignals(True)
        self._pa.ana_param_invoke_settings_CheckBox.blockSignals(True)
        self._pe.laserpulses_ComboBox.blockSignals(True)
        self._as.ana_param_x_axis_name_LineEdit.blockSignals(True)
        self._as.ana_param_x_axis_unit_LineEdit.blockSignals(True)
        self._as.ana_param_y_axis_name_LineEdit.blockSignals(True)
        self._as.ana_param_y_axis_unit_LineEdit.blockSignals(True)

        # set widgets
        if 'number_of_lasers' in settings_dict:
            self._pa.ana_param_num_laser_pulse_SpinBox.setValue(settings_dict['number_of_lasers'])
            self._pe.laserpulses_ComboBox.clear()
            self._pe.laserpulses_ComboBox.addItem('sum')
            self._pe.laserpulses_ComboBox.addItems(
                [str(i) for i in range(1, settings_dict['number_of_lasers'] + 1)])
        if 'alternating' in settings_dict:
            self._pa.ana_param_alternating_CheckBox.setChecked(settings_dict['alternating'])
            # self.toggle_alternating_plots(settings_dict['alternating'])
        if 'laser_ignore_list' in settings_dict:
            self._pa.ana_param_ignore_first_CheckBox.setChecked(
                0 in settings_dict['laser_ignore_list'])
            if -1 in settings_dict['laser_ignore_list'] or self._pa.ana_param_num_laser_pulse_SpinBox.value() - 1 in settings_dict['laser_ignore_list']:
                self._pa.ana_param_ignore_last_CheckBox.setChecked(True)
            else:
                self._pa.ana_param_ignore_last_CheckBox.setChecked(False)
        if 'controlled_variable' in settings_dict:
            if len(settings_dict['controlled_variable']) < 1:
                self._pa.ana_param_x_axis_start_ScienDSpinBox.setValue(0)
                self._pa.ana_param_x_axis_inc_ScienDSpinBox.setValue(0)
            elif len(settings_dict['controlled_variable']) == 1:
                self._pa.ana_param_x_axis_start_ScienDSpinBox.setValue(
                    settings_dict['controlled_variable'][0])
                self._pa.ana_param_x_axis_inc_ScienDSpinBox.setValue(
                    settings_dict['controlled_variable'][0])
            else:
                self._pa.ana_param_x_axis_start_ScienDSpinBox.setValue(
                    settings_dict['controlled_variable'][0])
                self._pa.ana_param_x_axis_inc_ScienDSpinBox.setValue(
                    settings_dict['controlled_variable'][1] - settings_dict['controlled_variable'][
                        0])
        if 'invoke_settings' in settings_dict:
            self._pa.ana_param_invoke_settings_CheckBox.setChecked(settings_dict['invoke_settings'])
            self.toggle_measurement_settings_editor(settings_dict['invoke_settings'])
        if 'units' in settings_dict and 'labels' in settings_dict:
            self._as.ana_param_x_axis_name_LineEdit.setText(settings_dict['labels'][0])
            self._as.ana_param_x_axis_unit_LineEdit.setText(settings_dict['units'][0])
            self._as.ana_param_y_axis_name_LineEdit.setText(settings_dict['labels'][1])
            self._as.ana_param_y_axis_unit_LineEdit.setText(settings_dict['units'][1])
            self._pa.pulse_analysis_PlotWidget.setLabel(
                axis='bottom',
                text=settings_dict['labels'][0],
                units=settings_dict['units'][0])
            self._pa.pulse_analysis_PlotWidget.setLabel(
                axis='left',
                text=settings_dict['labels'][1],
                units=settings_dict['units'][1])
            self._pe.measuring_error_PlotWidget.setLabel(
                axis='bottom',
                text=settings_dict['labels'][0],
                units=settings_dict['units'][0])

        # unblock signals
        self._as.ana_param_x_axis_name_LineEdit.blockSignals(False)
        self._as.ana_param_x_axis_unit_LineEdit.blockSignals(False)
        self._as.ana_param_y_axis_name_LineEdit.blockSignals(False)
        self._as.ana_param_y_axis_unit_LineEdit.blockSignals(False)
        self._pa.ana_param_ignore_first_CheckBox.blockSignals(False)
        self._pa.ana_param_ignore_last_CheckBox.blockSignals(False)
        self._pa.ana_param_alternating_CheckBox.blockSignals(False)
        self._pa.ana_param_num_laser_pulse_SpinBox.blockSignals(False)
        self._pa.ana_param_x_axis_start_ScienDSpinBox.blockSignals(False)
        self._pa.ana_param_x_axis_inc_ScienDSpinBox.blockSignals(False)
        self._pa.ana_param_invoke_settings_CheckBox.blockSignals(False)
        self._pe.laserpulses_ComboBox.blockSignals(False)

        self.second_plot_changed(self.pulsedmasterlogic().alternative_data_type)
        return

    def set_plot_dimensions(self):
        """

        @param alternating:
        @return:
        """
        number_of_signals = self.pulsedmasterlogic().signal_data.shape[0] - 1
        number_of_alt_signals = self.pulsedmasterlogic().signal_alt_data.shape[0] - 1

        if number_of_signals == 1:
            if self.signal_image2 in self._pa.pulse_analysis_PlotWidget.items():
                self._pa.pulse_analysis_PlotWidget.removeItem(self.signal_image2)
            if self.signal_image_error_bars2 in self._pa.pulse_analysis_PlotWidget.items():
                self._pa.pulse_analysis_PlotWidget.removeItem(self.signal_image_error_bars2)
            if self.measuring_error_image2 in self._pe.measuring_error_PlotWidget.items():
                self._pe.measuring_error_PlotWidget.removeItem(self.measuring_error_image2)
        else:
            if self.signal_image2 not in self._pa.pulse_analysis_PlotWidget.items():
                self._pa.pulse_analysis_PlotWidget.addItem(self.signal_image2)
            if self.signal_image_error_bars in self._pa.pulse_analysis_PlotWidget.items() and self.signal_image_error_bars2 not in self._pa.pulse_analysis_PlotWidget.items():
                self._pa.pulse_analysis_PlotWidget.addItem(self.signal_image_error_bars2)
            if self.measuring_error_image2 not in self._pe.measuring_error_PlotWidget.items():
                self._pe.measuring_error_PlotWidget.addItem(self.measuring_error_image2)

        if number_of_alt_signals == 1:
            if self.second_plot_image2 in self._pa.pulse_analysis_second_PlotWidget.items():
                self._pa.pulse_analysis_second_PlotWidget.removeItem(self.second_plot_image2)
        else:
            if self.second_plot_image2 not in self._pa.pulse_analysis_second_PlotWidget.items():
                self._pa.pulse_analysis_second_PlotWidget.addItem(self.second_plot_image2)
        return

    def toggle_measurement_settings_editor(self, hide_editor):
        """
        Shows or hides input widgets for measurement settings and fast counter settings
        """
        if hide_editor:
            self._pa.ana_param_x_axis_start_ScienDSpinBox.setEnabled(False)
            self._pa.ana_param_x_axis_inc_ScienDSpinBox.setEnabled(False)
            self._pa.ana_param_num_laser_pulse_SpinBox.setEnabled(False)
            self._pa.ana_param_record_length_DoubleSpinBox.setEnabled(False)
            self._pa.ana_param_ignore_first_CheckBox.setEnabled(False)
            self._pa.ana_param_ignore_last_CheckBox.setEnabled(False)
            self._pa.ana_param_alternating_CheckBox.setEnabled(False)
        else:
            self._pa.ana_param_x_axis_start_ScienDSpinBox.setEnabled(True)
            self._pa.ana_param_x_axis_inc_ScienDSpinBox.setEnabled(True)
            self._pa.ana_param_num_laser_pulse_SpinBox.setEnabled(True)
            self._pa.ana_param_record_length_DoubleSpinBox.setEnabled(True)
            self._pa.ana_param_ignore_first_CheckBox.setEnabled(True)
            self._pa.ana_param_ignore_last_CheckBox.setEnabled(True)
            self._pa.ana_param_alternating_CheckBox.setEnabled(True)
        return

    @QtCore.Slot(bool)
    def toggle_error_bars(self, show_bars):
        """

        @return:
        """
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

    @QtCore.Slot(str)
    def second_plot_changed(self, second_plot):
        """ This method handles the second plot"""
        self._pa.second_plot_GroupBox.setVisible(second_plot != 'None')
        self._pa.second_plot_GroupBox.setTitle(second_plot)

        if second_plot != self._pa.second_plot_ComboBox.currentText():
            self._pa.second_plot_ComboBox.blockSignals(True)
            index = self._pa.second_plot_ComboBox.findText(second_plot)
            self._pa.second_plot_ComboBox.setCurrentIndex(index)
            self._pa.second_plot_ComboBox.blockSignals(False)

        if second_plot != self.pulsedmasterlogic().alternative_data_type:
            self.pulsedmasterlogic().set_alternative_data_type(second_plot)

        if self.pulsedmasterlogic().alternative_data_type == 'Delta':
            self._ana_param_second_plot_x_axis_name_text = self._as.ana_param_x_axis_name_LineEdit.text()
            self._ana_param_second_plot_x_axis_unit_text = self._as.ana_param_x_axis_unit_LineEdit.text()
            self._ana_param_second_plot_y_axis_name_text = self._as.ana_param_y_axis_name_LineEdit.text()
            self._ana_param_second_plot_y_axis_unit_text = self._as.ana_param_y_axis_unit_LineEdit.text()
        else:
            self._ana_param_second_plot_x_axis_name_text = self._as.ana_param_second_plot_x_axis_name_LineEdit.text()
            self._ana_param_second_plot_x_axis_unit_text = self._as.ana_param_second_plot_x_axis_unit_LineEdit.text()
            self._ana_param_second_plot_y_axis_name_text = self._as.ana_param_second_plot_y_axis_name_LineEdit.text()
            self._ana_param_second_plot_y_axis_unit_text = self._as.ana_param_second_plot_y_axis_unit_LineEdit.text()

        self._pa.pulse_analysis_second_PlotWidget.setLabel(
            axis='bottom',
            text=self._ana_param_second_plot_x_axis_name_text,
            units=self._ana_param_second_plot_x_axis_unit_text)
        self._pa.pulse_analysis_second_PlotWidget.setLabel(
            axis='left',
            text=self._ana_param_second_plot_y_axis_name_text,
            units=self._ana_param_second_plot_y_axis_unit_text)

        return

    ###########################################################################
    #                      Extraction tab related methods                     #
    ###########################################################################
    def _activate_extraction_ui(self):
        # Configure the lasertrace plot display:
        self.sig_start_line = pg.InfiniteLine(pos=0,
                                              pen={'color': palette.c3, 'width': 1},
                                              movable=True)
        self.sig_end_line = pg.InfiniteLine(pos=0,
                                            pen={'color': palette.c3, 'width': 1},
                                            movable=True)
        self.ref_start_line = pg.InfiniteLine(pos=0,
                                              pen={'color': palette.c4, 'width': 1},
                                              movable=True)
        self.ref_end_line = pg.InfiniteLine(pos=0,
                                            pen={'color': palette.c4, 'width': 1},
                                            movable=True)
        self.lasertrace_image = pg.PlotDataItem(np.arange(10), np.zeros(10), pen=palette.c1)
        self._pe.laserpulses_PlotWidget.addItem(self.lasertrace_image)
        self._pe.laserpulses_PlotWidget.addItem(self.sig_start_line)
        self._pe.laserpulses_PlotWidget.addItem(self.sig_end_line)
        self._pe.laserpulses_PlotWidget.addItem(self.ref_start_line)
        self._pe.laserpulses_PlotWidget.addItem(self.ref_end_line)
        self._pe.laserpulses_PlotWidget.setLabel(axis='bottom', text='time', units='s')
        self._pe.laserpulses_PlotWidget.setLabel(axis='left', text='events', units='#')

        # Configure the measuring error plot display:
        self.measuring_error_image = pg.PlotDataItem(np.arange(10), np.zeros(10), pen=palette.c1)
        self.measuring_error_image2 = pg.PlotDataItem(np.arange(10), np.zeros(10), pen=palette.c3)
        self._pe.measuring_error_PlotWidget.addItem(self.measuring_error_image)
        self._pe.measuring_error_PlotWidget.addItem(self.measuring_error_image2)
        self._pe.measuring_error_PlotWidget.setLabel('left', 'measuring error',  units='arb.u.')

        # Initialize widgets
        number_of_lasers = self.pulsedmasterlogic().measurement_settings['number_of_lasers']
        self._pe.laserpulses_display_raw_CheckBox.blockSignals(True)
        self._pe.laserpulses_ComboBox.blockSignals(True)
        self._pe.extract_param_analysis_method_comboBox.blockSignals(True)
        self._pe.extract_param_method_comboBox.blockSignals(True)

        self._pe.laserpulses_display_raw_CheckBox.setChecked(self._show_raw_data)

        self._pe.laserpulses_ComboBox.clear()
        self._pe.laserpulses_ComboBox.addItem('sum')
        for ii in range(1, number_of_lasers + 1):
            self._pe.laserpulses_ComboBox.addItem(str(ii))
        self._pe.laserpulses_ComboBox.setCurrentIndex(self._show_laser_index)

        self._pe.extract_param_analysis_method_comboBox.clear()
        self._pe.extract_param_analysis_method_comboBox.addItems(
            list(self.pulsedmasterlogic().analysis_methods))
        self._pe.extract_param_method_comboBox.clear()
        self._pe.extract_param_method_comboBox.addItems(
            list(self.pulsedmasterlogic().extraction_methods))

        self._pe.laserpulses_display_raw_CheckBox.blockSignals(False)
        self._pe.laserpulses_ComboBox.blockSignals(False)
        self._pe.extract_param_analysis_method_comboBox.blockSignals(False)
        self._pe.extract_param_method_comboBox.blockSignals(False)

        # variable holding all dynamically generated widgets for the selected extraction method
        self._extraction_param_widgets = None

        # Initialize from logic values
        self.analysis_settings_updated(self.pulsedmasterlogic().analysis_settings)
        self.extraction_settings_updated(self.pulsedmasterlogic().extraction_settings)
        self.update_laser_data()
        return

    def _deactivate_extraction_ui(self):
        self._show_laser_index = self._pe.laserpulses_ComboBox.currentIndex()
        self._show_raw_data = self._pe.laserpulses_display_raw_CheckBox.isChecked()
        return

    @QtCore.Slot()
    def extraction_settings_changed(self):
        """
        Uodate new value of standard deviation of gaussian filter
        """
        settings_dict = dict()
        settings_dict['method'] = self._pe.extract_param_method_comboBox.currentText()
        # Check if the method has been changed
        if settings_dict['method'] == self.pulsedmasterlogic().extraction_settings['method']:
            for label, widget in self._extraction_param_widgets:
                param_name = widget.objectName()[14:]
                if hasattr(widget, 'isChecked'):
                    settings_dict[param_name] = widget.isChecked()
                elif hasattr(widget, 'value'):
                    settings_dict[param_name] = widget.value()
                elif hasattr(widget, 'text'):
                    settings_dict[param_name] = widget.text()
        else:
            self._delete_extraction_param_widgets()

        self.pulsedmasterlogic().set_extraction_settings(settings_dict)
        return

    @QtCore.Slot(dict)
    def extraction_settings_updated(self, settings_dict):
        """

        @param dict settings_dict: dictionary with parameters to update
        @return:
        """
        # If no widgets have been generated yet, generate them now.
        if self._extraction_param_widgets is None:
            self._create_extraction_param_widgets(extraction_settings=settings_dict)

        # If the method is unchanged, just update the widget values.
        # Otherwise delete all widgets and create new ones for the changed method.
        if settings_dict.get('method') == self._pe.extract_param_method_comboBox.currentText():
            for label, widget in self._extraction_param_widgets:
                param_name = widget.objectName()[14:]
                widget.blockSignals(True)
                if hasattr(widget, 'setValue'):
                    widget.setValue(settings_dict.get(param_name))
                elif hasattr(widget, 'setChecked'):
                    widget.setChecked(settings_dict.get(param_name))
                elif hasattr(widget, 'setText'):
                    widget.setText(settings_dict.get(param_name))
                else:
                    self.log.error('Unable to update widget value for parameter "{0}".\n'
                                   'Widget is of unknown type.'.format(param_name))
                widget.blockSignals(False)
        else:
            self._delete_extraction_param_widgets()
            self._create_extraction_param_widgets(extraction_settings=settings_dict)

        # Update the method combobox
        self._pe.extract_param_method_comboBox.blockSignals(True)
        index = self._pe.extract_param_method_comboBox.findText(settings_dict.get('method'))
        self._pe.extract_param_method_comboBox.setCurrentIndex(index)
        self._pe.extract_param_method_comboBox.blockSignals(False)
        return

    def _delete_extraction_param_widgets(self):
        """

        @return:
        """
        for index in reversed(range(len(self._extraction_param_widgets))):
            label = self._extraction_param_widgets[index][0]
            widget = self._extraction_param_widgets[index][1]
            # Disconnect signals
            if hasattr(widget, 'setChecked'):
                widget.stateChanged.disconnect()
            else:
                widget.editingFinished.disconnect()
            # Remove label and widget from layout
            self._pe.extraction_param_gridLayout.removeWidget(label)
            self._pe.extraction_param_gridLayout.removeWidget(widget)
            # Stage label and widget for deletion
            label.deleteLater()
            widget.deleteLater()
            del self._extraction_param_widgets[index]
        self._extraction_param_widgets = None
        return

    def _create_extraction_param_widgets(self, extraction_settings):
        """

        @param extraction_settings:
        @return:
        """
        self._extraction_param_widgets = list()
        layout_row = 1
        for param_name, value in extraction_settings.items():
            if param_name == 'method':
                continue

            # Create label for the parameter
            label = QtWidgets.QLabel(param_name + ':')
            label.setObjectName('extract_param_label_' + param_name)

            # Create widget for parameter and connect update signal
            if isinstance(value, float):
                widget = ScienDSpinBox()
                widget.setValue(value)
                widget.editingFinished.connect(self.extraction_settings_changed)
            elif isinstance(value, int):
                widget = ScienSpinBox()
                widget.setValue(value)
                widget.editingFinished.connect(self.extraction_settings_changed)
            elif isinstance(value, str):
                widget = QtWidgets.QLineEdit()
                widget.setText(value)
                widget.editingFinished.connect(self.extraction_settings_changed)
            elif isinstance(value, bool):
                widget = QtWidgets.QCheckBox()
                widget.setChecked(value)
                widget.stateChanged.connect(self.extraction_settings_changed)
            else:
                self.log.error('Could not create widget for extraction parameter "{0}".\n'
                               'Default parameter value is of invalid type.'.format(param_name))
                continue
            widget.setObjectName('extract_param_' + param_name)
            widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

            # Add label and widget to the main grid layout
            self._pe.extraction_param_gridLayout.addWidget(label, layout_row, 0)
            self._pe.extraction_param_gridLayout.addWidget(widget, layout_row, 1)

            # Add label and widget to the list
            self._extraction_param_widgets.append((label, widget))
            layout_row += 1

    @QtCore.Slot()
    def analysis_settings_changed(self):
        """

        @return:
        """
        settings_dict = dict()

        # Check if the signal has been emitted by a dragged line in the laser plot
        if self.sender().__class__.__name__ == 'InfiniteLine':
            sig_start = self.sig_start_line.value()
            sig_end = self.sig_end_line.value()
            ref_start = self.ref_start_line.value()
            ref_end = self.ref_end_line.value()
            settings_dict['signal_start'] = sig_start if sig_start <= sig_end else sig_end
            settings_dict['signal_end'] = sig_end if sig_end >= sig_start else sig_start
            settings_dict['norm_start'] = ref_start if ref_start <= ref_end else ref_end
            settings_dict['norm_end'] = ref_end if ref_end >= ref_start else ref_start
        else:
            signal_width = self._pe.extract_param_ana_window_width_DSpinBox.value()
            settings_dict['signal_start'] = self._pe.extract_param_ana_window_start_DSpinBox.value()
            settings_dict['signal_end'] = settings_dict['signal_start'] + signal_width
            norm_width = self._pe.extract_param_ref_window_width_DSpinBox.value()
            settings_dict['norm_start'] = self._pe.extract_param_ref_window_start_DSpinBox.value()
            settings_dict['norm_end'] = settings_dict['norm_start'] + norm_width

        settings_dict['method'] = self._pe.extract_param_analysis_method_comboBox.currentText()

        self.pulsedmasterlogic().set_analysis_settings(settings_dict)
        return

    @QtCore.Slot(dict)
    def analysis_settings_updated(self, settings_dict):
        """

        @param dict settings_dict: dictionary with parameters to update
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

        if 'signal_start' in settings_dict:
            self._pe.extract_param_ana_window_start_DSpinBox.setValue(
                settings_dict['signal_start'])
            self.sig_start_line.setValue(settings_dict['signal_start'])
        if 'norm_start' in settings_dict:
            self._pe.extract_param_ref_window_start_DSpinBox.setValue(settings_dict['norm_start'])
            self.ref_start_line.setValue(settings_dict['norm_start'])
        if 'signal_end' in settings_dict:
            signal_start = self._pe.extract_param_ana_window_start_DSpinBox.value()
            self._pe.extract_param_ana_window_width_DSpinBox.setValue(
                settings_dict['signal_end'] - signal_start)
            self.sig_end_line.setValue(settings_dict['signal_end'])
        if 'norm_end' in settings_dict:
            norm_start = self._pe.extract_param_ref_window_start_DSpinBox.value()
            self._pe.extract_param_ref_window_width_DSpinBox.setValue(
                settings_dict['norm_end'] - norm_start)
            self.ref_end_line.setValue(settings_dict['norm_end'])
        if 'method' in settings_dict:
            index = self._pe.extract_param_analysis_method_comboBox.findText(settings_dict['method'])
            self._pe.extract_param_analysis_method_comboBox.setCurrentIndex(index)

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

    @QtCore.Slot()
    def update_laser_data(self):
        """

        @return:
        """
        laser_index = self._pe.laserpulses_ComboBox.currentIndex()
        show_raw = self._pe.laserpulses_display_raw_CheckBox.isChecked()
        is_gated = len(self.pulsedmasterlogic().raw_data.shape) > 1

        # Determine the right array to plot as y-data
        if show_raw:
            if is_gated:
                if laser_index == 0:
                    y_data = np.sum(self.pulsedmasterlogic().raw_data, axis=0)
                else:
                    y_data = self.pulsedmasterlogic().raw_data[laser_index - 1]
            else:
                y_data = self.pulsedmasterlogic().raw_data
        else:
            if laser_index == 0:
                y_data = np.sum(self.pulsedmasterlogic().laser_data, axis=0)
            else:
                y_data = self.pulsedmasterlogic().laser_data[laser_index - 1]

        # Calculate the x-axis of the laser plot here
        bin_width = self.pulsedmasterlogic().fast_counter_settings['bin_width']
        x_data = np.arange(y_data.size, dtype=float) * bin_width

        # Plot data
        self.lasertrace_image.setData(x=x_data, y=y_data)
        return

    ###########################################################################
    #                      Timetrace analysis tab related methods             #
    ###########################################################################
    def _activate_timetrace_analysis_ui(self):
        # Configure the full timetrace plot display:
        self.ta_start_line = pg.InfiniteLine(pos=0,
                                              pen={'color': palette.c3, 'width': 1},
                                              movable=True)
        self.ta_end_line = pg.InfiniteLine(pos=0,
                                            pen={'color': palette.c3, 'width': 1},
                                            movable=True)
        self.ta_origin_line = pg.InfiniteLine(pos=0,
                                              pen={'color': palette.c4, 'width': 1},
                                              movable=True)
        self.ta_full_image = pg.PlotDataItem(np.arange(10), np.zeros(10), pen=palette.c1)
        self._ta.full_timetrace_PlotWidget.addItem(self.ta_full_image)
        self._ta.full_timetrace_PlotWidget.addItem(self.ta_start_line)
        self._ta.full_timetrace_PlotWidget.addItem(self.ta_end_line)
        self._ta.full_timetrace_PlotWidget.addItem(self.ta_origin_line)
        self._ta.full_timetrace_PlotWidget.setLabel(axis='bottom', text='time', units='s')
        self._ta.full_timetrace_PlotWidget.setLabel(axis='left', text='events', units='#')

        # Configure the window plot display:
        self.ta_window_image = pg.PlotDataItem(np.arange(10), np.zeros(10), pen=palette.c1)
        self._ta.window_PlotWidget.addItem(self.ta_window_image)
        self._ta.window_PlotWidget.setLabel(axis='bottom', text='time', units='s')
        self._ta.window_PlotWidget.setLabel(axis='left', text='Photoluminescence', units='c/s')

        self._ta.window_PlotWidget.showAxis('right')
        self._ta.window_PlotWidget.getAxis('right').setLabel('events', units='#', color=palette.c1.name())

        self._ta.window_PlotWidget_ViewBox = pg.ViewBox()
        self._ta.window_PlotWidget.scene().addItem(self._ta.window_PlotWidget_ViewBox)
        self._ta.window_PlotWidget.getAxis('right').linkToView(self._ta.window_PlotWidget_ViewBox)
        self._ta.window_PlotWidget_ViewBox.setXLink(self._ta.window_PlotWidget)

        def updateSecondAxis():
            sweeps = self.pulsedmasterlogic().elapsed_sweeps
            bin_width = self.pulsedmasterlogic().fast_counter_settings['bin_width']
            rebinning = self.pulsedmasterlogic().timetrace_analysis_settings['rebinning']
            factor = (sweeps * (bin_width * rebinning))
            if sweeps == 0:
                return
            view_rect = self._ta.window_PlotWidget.viewRect()
            y_range = np.array([view_rect.bottom(), view_rect.top()]) * factor
            self._ta.window_PlotWidget_ViewBox.setRange(yRange=y_range, padding=0)

        updateSecondAxis()
        self._ta.window_PlotWidget_ViewBox.sigRangeChanged.connect(updateSecondAxis)


        self.ta_window_image_fit = pg.PlotDataItem(pen=palette.c3)

        self._ta.fit_method_comboBox.setFitFunctions(self._fsd.currentFits)

        # Initialize from logic values
        self.timetrace_analysis_settings_updated(self.pulsedmasterlogic().timetrace_analysis_settings)
        self.update_timetrace_window()

    def _deactivate_timetrace_analysis_ui(self):
        pass

    @QtCore.Slot()
    def timetrace_analysis_settings_changed(self):
        """

        @return:
        """
        settings_dict = dict()
        settings_dict['rebinning'] = self._ta.param_1_rebinnig_spinBox.value()
        # Check if the signal has been emitted by a dragged line in the laser plot
        if self.sender().__class__.__name__ == 'InfiniteLine':
            start = self.ta_start_line.value()
            end = self.ta_end_line.value()
            settings_dict['start'] = start if start <= end else end
            settings_dict['end'] = end if end >= start else start
            settings_dict['origin'] = self.ta_origin_line.value()
        else:
            settings_dict['start'] = self._ta.param_2_start_DSpinBox.value()
            settings_dict['end'] = settings_dict['start'] + self._ta.param_3_width_DSpinBox.value()
            settings_dict['origin'] = self._ta.param_4_origin_DSpinBox.value()

        self.pulsedmasterlogic().set_timetrace_analysis_settings(settings_dict)
        return

    @QtCore.Slot(dict)
    def timetrace_analysis_settings_updated(self, settings_dict):
        """

        @param dict settings_dict: dictionary with parameters to update
        @return:
        """
        # block signals
        self._ta.param_1_rebinnig_spinBox.blockSignals(True)
        self._ta.param_2_start_DSpinBox.blockSignals(True)
        self._ta.param_3_width_DSpinBox.blockSignals(True)
        self._ta.param_4_origin_DSpinBox.blockSignals(True)
        self.ta_start_line.blockSignals(True)
        self.ta_end_line.blockSignals(True)
        self.ta_origin_line.blockSignals(True)

        if 'start' in settings_dict:
            self._ta.param_2_start_DSpinBox.setValue(settings_dict['start'])
            self.ta_start_line.setValue(settings_dict['start'])
        if 'end' in settings_dict and 'start' in settings_dict:
            self._ta.param_3_width_DSpinBox.setValue(settings_dict['end']-settings_dict['start'])
            self.ta_end_line.setValue(settings_dict['end'])
        if 'origin' in settings_dict:
            self._ta.param_4_origin_DSpinBox.setValue(settings_dict['origin'])
            self.ta_origin_line.setValue(settings_dict['origin'])
        if 'rebinning' in settings_dict:
            index = self._ta.param_1_rebinnig_spinBox.setValue(settings_dict['rebinning'])

        # unblock signals
        self._ta.param_1_rebinnig_spinBox.blockSignals(False)
        self._ta.param_2_start_DSpinBox.blockSignals(False)
        self._ta.param_3_width_DSpinBox.blockSignals(False)
        self._ta.param_4_origin_DSpinBox.blockSignals(False)
        self.ta_start_line.blockSignals(False)
        self.ta_end_line.blockSignals(False)
        self.ta_origin_line.blockSignals(False)

        self.update_timetrace_window()

    @QtCore.Slot()
    def update_timetrace_window(self):
        """

        @return:
        """
        # Determine the right array to plot as y-data
        bin_width = self.pulsedmasterlogic().fast_counter_settings['bin_width']
        y_data = self.pulsedmasterlogic().raw_data
        x_data = np.arange(y_data.size, dtype=float) * bin_width

        self.ta_full_image.setData(x=x_data, y=y_data)

        x_data, y_data = self.pulsedmasterlogic().timetrace_data
        if len(y_data) > 1:
            self.ta_window_image.setData(x=x_data, y=y_data)
        return
