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

import inspect
import numpy as np
import os
import pyqtgraph as pg
import datetime

from core.module import Connector, StatusVar
from core.util import units
from gui.colordefs import QudiPalettePale as palette
from gui.colordefs import QudiPalette as palettedark
from gui.fitsettings import FitSettingsDialog
from gui.guibase import GUIBase
from qtpy import QtGui, QtCore, QtWidgets, uic
from qtwidgets.scientific_spinbox import ScienDSpinBox


# FIXME: Display the Pulse
# FIXME: save the length in sample points (bins)
# FIXME: adjust the length to the bins


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
    _second_plot_ComboBox_text = StatusVar('second_plot_ComboBox_text', 'None')
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
        self._pg = PulseGeneratorTab()
        self._pe = PulseExtractionTab()
        self._pm = PredefinedMethodsTab()
        self._sg = SequenceGeneratorTab()
        self._as = AnalysisSettingDialog()
        self._pm_cfg = PredefinedMethodsConfigDialog()

        self._mw.tabWidget.addTab(self._pa, 'Analysis')
        self._mw.tabWidget.addTab(self._pe, 'Pulse Extraction')
        self._mw.tabWidget.addTab(self._pg, 'Pulse Generator')
        self._mw.tabWidget.addTab(self._sg, 'Sequence Generator')
        self._mw.tabWidget.addTab(self._pm, 'Predefined Methods')

        self._setup_toolbar()

        self._connect_main_window_signals()
        self._connect_analysis_tab_signals()
        self._connect_extraction_tab_signals()
        self._connect_pulse_generator_tab_signals()
        self._connect_predefined_methods_tab_signals()
        self._connect_sequence_generator_tab_signals()
        self._connect_dialog_signals()
        self._connect_logic_signals()

        self._activate_main_window_ui()
        self._activate_analysis_ui()
        self._activate_extraction_ui()
        self._activate_pulse_generator_ui()
        self._activate_predefined_methods_ui()
        self._activate_sequence_generator_ui()
        self._activate_analysis_settings_ui()
        self._activate_predefined_methods_settings_ui()

        self.show()

        self._pa.ext_control_mw_freq_DoubleSpinBox.setMaximum(999999999999)

    def on_deactivate(self):
        """ Undo the Definition, configuration and initialisation of the pulsed
            measurement GUI.

        This deactivation disconnects all the graphic modules, which were
        connected in the initUI method.
        """

        self._mw.actionSave.triggered.disconnect()

        self._deactivate_analysis_settings_ui()
        self._deactivate_analysis_ui()

        self._deactivate_generator_settings_ui()
        self._deactivate_pulse_generator_ui()

        self._mw.close()
        return

    def show(self):
        """Make main window visible and put it above all other windows. """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()
        return

    def _setup_toolbar(self):
        # create all the needed control widgets on the fly
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
        return

    ###########################################################################
    #                          Signal (dis-)connections                       #
    ###########################################################################
    def _connect_main_window_signals(self):
        # Connect main window actions and toolbar
        self._mw.action_Settings_Block_Generation.triggered.connect(self.show_generator_settings)
        self._mw.action_Predefined_Methods_Config.triggered.connect(
            self.show_predefined_methods_config)
        self._mw.actionSave.triggered.connect(self.save_clicked)
        self._mw.pulser_on_off_PushButton.clicked.connect(self.pulser_on_off_clicked)
        self._mw.clear_device_PushButton.clicked.connect(self.clear_pulser_clicked)
        self._mw.action_run_stop.triggered.connect(self.measurement_run_stop_clicked)
        self._mw.action_continue_pause.triggered.connect(self.measurement_continue_pause_clicked)
        self._mw.action_pull_data.triggered.connect(self.pull_data_clicked)
        self._mw.action_save.triggered.connect(self.save_clicked)
        self._mw.action_Settings_Analysis.triggered.connect(self.show_analysis_settings)
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

        # Connect signals used in fit settings dialog
        self._fsd.sigFitsUpdated.connect(self._pa.fit_param_fit_func_ComboBox.setFitFunctions)
        return

    def _connect_pulse_generator_tab_signals(self):
        # Connect Block/Ensemble editor tab signals
        self._pg.gen_laserchannel_ComboBox.currentIndexChanged.connect(self.sampling_settings_changed, QtCore.Qt.QueuedConnection)
        self._pg.sample_ensemble_PushButton.clicked.connect(self.sample_ensemble_clicked)
        self._pg.samplo_ensemble_PushButton.clicked.connect(self.samplo_ensemble_clicked)

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
        self._pg.curr_block_load_PushButton.clicked.connect(self.editor_load_block_clicked)
        self._pg.curr_ensemble_generate_PushButton.clicked.connect(self.editor_generate_ensemble_clicked)
        self._pg.curr_ensemble_del_PushButton.clicked.connect(self.editor_delete_ensemble_clicked)
        self._pg.curr_ensemble_load_PushButton.clicked.connect(self.editor_load_ensemble_clicked)

        self._pg.load_ensemble_PushButton.clicked.connect(self.load_ensemble_clicked)

        self._pg.gen_use_interleave_CheckBox.stateChanged.connect()
        self._pg.gen_activation_config_ComboBox.currentIndexChanged.connect()
        self._pg.gen_sample_freq_DSpinBox.editingFinished.connect()
        return

    def _connect_sequence_generator_tab_signals(self):
        # Connect Sequence editor tab signals
        self._sg.sample_sequence_PushButton.clicked.connect(self.sample_sequence_clicked)
        self._sg.samplo_sequence_PushButton.clicked.connect(self.samplo_sequence_clicked)
        self._sg.sequence_add_last_PushButton.clicked.connect(self.sequence_add_last_clicked)
        self._sg.sequence_del_last_PushButton.clicked.connect(self.sequence_del_last_clicked)
        self._sg.sequence_add_sel_PushButton.clicked.connect(self.sequence_add_sel_clicked)
        self._sg.sequence_del_sel_PushButton.clicked.connect(self.sequence_del_sel_clicked)
        self._sg.sequence_clear_PushButton.clicked.connect(self.sequence_clear_clicked)
        self._sg.curr_sequence_generate_PushButton.clicked.connect(self.editor_generate_sequence_clicked)
        self._sg.curr_sequence_del_PushButton.clicked.connect(self.editor_delete_sequence_clicked)
        self._sg.curr_sequence_load_PushButton.clicked.connect(self.editor_load_sequence_clicked)

        self._sg.load_sequence_PushButton.clicked.connect(self.load_sequence_clicked)
        return

    def _connect_analysis_tab_signals(self):
        # Connect pulse analysis tab signals
        self._pa.fit_param_PushButton.clicked.connect(self.fit_clicked)
        self._pa.ext_control_use_mw_CheckBox.stateChanged.connect(self.ext_mw_params_changed)
        self._pa.ana_param_invoke_settings_CheckBox.stateChanged.connect(self.toggle_settings_editor)
        self._pa.ana_param_alternating_CheckBox.stateChanged.connect(self.measurement_sequence_settings_changed)
        self._pa.ana_param_ignore_first_CheckBox.stateChanged.connect(self.measurement_sequence_settings_changed)
        self._pa.ana_param_ignore_last_CheckBox.stateChanged.connect(self.measurement_sequence_settings_changed)
        self._pa.ana_param_errorbars_CheckBox.stateChanged.connect(self.toggle_error_bars)
        self._pa.gen_use_interleave_CheckBox.stateChanged.connect(self.pulse_generator_settings_changed)
        self._pa.ana_param_num_laser_pulse_SpinBox.editingFinished.connect(self.measurement_sequence_settings_changed)
        self._pa.ana_param_record_length_SpinBox.editingFinished.connect(self.fast_counter_settings_changed)
        self._pa.time_param_ana_periode_DoubleSpinBox.editingFinished.connect(self.measurement_timer_changed)
        self._pa.ext_control_mw_freq_DoubleSpinBox.editingFinished.connect(self.ext_mw_params_changed)
        self._pa.ext_control_mw_power_DoubleSpinBox.editingFinished.connect(self.ext_mw_params_changed)
        self._pa.ana_param_x_axis_start_ScienDSpinBox.editingFinished.connect(self.measurement_sequence_settings_changed)
        self._pa.ana_param_x_axis_inc_ScienDSpinBox.editingFinished.connect(self.measurement_sequence_settings_changed)
        self._pa.ana_param_fc_bins_ComboBox.currentIndexChanged.connect(self.fast_counter_settings_changed)
        self._pa.second_plot_ComboBox.currentIndexChanged.connect(self.change_second_plot)
        return

    def _connect_extraction_tab_signals(self):
        # Connect pulse extraction tab signals
        self._pe.extract_param_ana_window_start_DSpinBox.editingFinished.connect(self.analysis_settings_changed)
        self._pe.extract_param_ana_window_width_DSpinBox.editingFinished.connect(self.analysis_settings_changed)
        self._pe.extract_param_ref_window_start_DSpinBox.editingFinished.connect(self.analysis_settings_changed)
        self._pe.extract_param_ref_window_width_DSpinBox.editingFinished.connect(self.analysis_settings_changed)
        self._pe.extract_param_conv_std_dev_DSpinBox.editingFinished.connect(self.extraction_settings_changed)
        self._pe.extract_param_threshold_SpinBox.editingFinished.connect(self.extraction_settings_changed)
        self._pe.extract_param_min_laser_length_SpinBox.editingFinished.connect(self.extraction_settings_changed)
        self._pe.extract_param_tolerance_SpinBox.editingFinished.connect(self.extraction_settings_changed)
        self._pe.laserpulses_ComboBox.currentIndexChanged.connect(self.laser_to_show_changed)
        self._pe.extract_param_analysis_method_comboBox.currentIndexChanged.connect(self.analysis_settings_changed)
        self._pe.extract_param_extraction_method_comboBox.currentIndexChanged.connect(self.extraction_settings_changed)
        self._pe.laserpulses_display_raw_CheckBox.stateChanged.connect(self.laser_to_show_changed)
        self.sig_start_line.sigPositionChangeFinished.connect(self.analysis_settings_changed)
        self.sig_end_line.sigPositionChangeFinished.connect(self.analysis_settings_changed)
        self.ref_start_line.sigPositionChangeFinished.connect(self.analysis_settings_changed)
        self.ref_end_line.sigPositionChangeFinished.connect(self.analysis_settings_changed)
        self._pe.extract_param_conv_std_dev_slider.valueChanged.connect(self.extraction_settings_changed)
        return

    def _connect_logic_signals(self):
        # Connect update signals from pulsed_master_logic
        self.pulsedmasterlogic().sigEnsembleSaUpComplete.connect(self.sample_ensemble_finished)
        self.pulsedmasterlogic().sigSequenceSaUpComplete.connect(self.sample_sequence_finished)
        self.pulsedmasterlogic().sigSavedPulseBlocksUpdated.connect(self.update_block_dict)
        self.pulsedmasterlogic().sigSavedBlockEnsemblesUpdated.connect(self.update_ensemble_dict)
        self.pulsedmasterlogic().sigSavedSequencesUpdated.connect(self.update_sequence_dict)
        self.pulsedmasterlogic().sigGeneratorSettingsUpdated.connect(self.update_generator_settings)

        self.pulsedmasterlogic().sigCurrentPulseBlockUpdated.connect(self.load_block_in_editor)
        self.pulsedmasterlogic().sigCurrentBlockEnsembleUpdated.connect(self.load_ensemble_in_editor)
        self.pulsedmasterlogic().sigCurrentSequenceUpdated.connect(self.load_sequence_in_editor)

        self.pulsedmasterlogic().sigSignalDataUpdated.connect(self.signal_data_updated)
        self.pulsedmasterlogic().sigLaserDataUpdated.connect(self.laser_data_updated)
        self.pulsedmasterlogic().sigLaserToShowUpdated.connect(self.laser_to_show_updated)
        self.pulsedmasterlogic().sigElapsedTimeUpdated.connect(self.elapsed_time_updated)
        self.pulsedmasterlogic().sigFitUpdated.connect(self.fit_data_updated)
        self.pulsedmasterlogic().sigMeasurementStatusUpdated.connect(self.measurement_status_updated)
        self.pulsedmasterlogic().sigPulserRunningUpdated.connect(self.pulser_running_updated)
        self.pulsedmasterlogic().sigFastCounterSettingsUpdated.connect(self.fast_counter_settings_updated)
        self.pulsedmasterlogic().sigMeasurementSequenceSettingsUpdated.connect(self.measurement_sequence_settings_updated)
        self.pulsedmasterlogic().sigPulserSettingsUpdated.connect(self.pulse_generator_settings_updated)
        self.pulsedmasterlogic().sigUploadedAssetsUpdated.connect(self.update_uploaded_assets)
        self.pulsedmasterlogic().sigLoadedAssetUpdated.connect(self.update_loaded_asset)
        self.pulsedmasterlogic().sigExtMicrowaveSettingsUpdated.connect(self.microwave_settings_updated)
        self.pulsedmasterlogic().sigExtMicrowaveRunningUpdated.connect(self.microwave_running_updated)
        self.pulsedmasterlogic().sigTimerIntervalUpdated.connect(self.measurement_timer_updated)
        self.pulsedmasterlogic().sigAnalysisSettingsUpdated.connect(self.analysis_settings_updated)
        self.pulsedmasterlogic().sigAnalysisMethodsUpdated.connect(self.analysis_methods_updated)
        self.pulsedmasterlogic().sigExtractionSettingsUpdated.connect(self.extraction_settings_updated)
        self.pulsedmasterlogic().sigExtractionMethodsUpdated.connect(self.extraction_methods_updated)
        return

    def _disconnect_main_window_signals(self):
        # Connect main window actions and toolbar
        self._mw.action_Settings_Block_Generation.triggered.disconnect()
        self._mw.action_Predefined_Methods_Config.triggered.disconnect()
        self._mw.actionSave.triggered.disconnect()
        self._mw.pulser_on_off_PushButton.clicked.disconnect()
        self._mw.clear_device_PushButton.clicked.disconnect()
        self._mw.action_run_stop.triggered.disconnect()
        self._mw.action_continue_pause.triggered.disconnect()
        self._mw.action_pull_data.triggered.disconnect()
        self._mw.action_save.triggered.disconnect()
        self._mw.action_Settings_Analysis.triggered.disconnect()
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

        # Connect signals used in fit settings dialog
        self._fsd.sigFitsUpdated.disconnect()
        return

    def _disconnect_pulse_generator_tab_signals(self):
        # Connect Block/Ensemble editor tab signals
        self._pg.gen_laserchannel_ComboBox.currentIndexChanged.disconnect()
        self._pg.sample_ensemble_PushButton.clicked.disconnect()
        self._pg.samplo_ensemble_PushButton.clicked.disconnect()

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
        self._pg.curr_block_load_PushButton.clicked.disconnect()
        self._pg.curr_ensemble_generate_PushButton.clicked.disconnect()
        self._pg.curr_ensemble_del_PushButton.clicked.disconnect()
        self._pg.curr_ensemble_load_PushButton.clicked.disconnect()

        self._pg.load_ensemble_PushButton.clicked.disconnect()

        self._pg.gen_use_interleave_CheckBox.stateChanged.disconnect()
        self._pg.gen_activation_config_ComboBox.currentIndexChanged.disconnect()
        self._pg.gen_sample_freq_DSpinBox.editingFinished.disconnect()
        return

    def _disconnect_sequence_generator_tab_signals(self):
        # Connect Sequence editor tab signals
        self._sg.sample_sequence_PushButton.clicked.disconnect()
        self._sg.samplo_sequence_PushButton.clicked.disconnect()
        self._sg.sequence_add_last_PushButton.clicked.disconnect()
        self._sg.sequence_del_last_PushButton.clicked.disconnect()
        self._sg.sequence_add_sel_PushButton.clicked.disconnect()
        self._sg.sequence_del_sel_PushButton.clicked.disconnect()
        self._sg.sequence_clear_PushButton.clicked.disconnect()
        self._sg.curr_sequence_generate_PushButton.clicked.disconnect()
        self._sg.curr_sequence_del_PushButton.clicked.disconnect()
        self._sg.curr_sequence_load_PushButton.clicked.disconnect()

        self._sg.load_sequence_PushButton.clicked.disconnect()
        return

    def _disconnect_analysis_tab_signals(self):
        # Connect pulse analysis tab signals
        self._pa.fit_param_PushButton.clicked.disconnect()
        self._pa.ext_control_use_mw_CheckBox.stateChanged.disconnect()
        self._pa.ana_param_invoke_settings_CheckBox.stateChanged.disconnect()
        self._pa.ana_param_alternating_CheckBox.stateChanged.disconnect()
        self._pa.ana_param_ignore_first_CheckBox.stateChanged.disconnect()
        self._pa.ana_param_ignore_last_CheckBox.stateChanged.disconnect()
        self._pa.ana_param_errorbars_CheckBox.stateChanged.disconnect()
        self._pa.ana_param_num_laser_pulse_SpinBox.editingFinished.disconnect()
        self._pa.ana_param_record_length_SpinBox.editingFinished.disconnect()
        self._pa.time_param_ana_periode_DoubleSpinBox.editingFinished.disconnect()
        self._pa.ext_control_mw_freq_DoubleSpinBox.editingFinished.disconnect()
        self._pa.ext_control_mw_power_DoubleSpinBox.editingFinished.disconnect()
        self._pa.ana_param_x_axis_start_ScienDSpinBox.editingFinished.disconnect()
        self._pa.ana_param_x_axis_inc_ScienDSpinBox.editingFinished.disconnect()
        self._pa.ana_param_fc_bins_ComboBox.currentIndexChanged.disconnect()
        self._pa.second_plot_ComboBox.currentIndexChanged.disconnect()
        return

    def _disconnect_extraction_tab_signals(self):
        # Connect pulse extraction tab signals
        self._pe.extract_param_ana_window_start_DSpinBox.editingFinished.disconnect()
        self._pe.extract_param_ana_window_width_DSpinBox.editingFinished.disconnect()
        self._pe.extract_param_ref_window_start_DSpinBox.editingFinished.disconnect()
        self._pe.extract_param_ref_window_width_DSpinBox.editingFinished.disconnect()
        self._pe.extract_param_conv_std_dev_DSpinBox.editingFinished.disconnect()
        self._pe.extract_param_threshold_SpinBox.editingFinished.disconnect()
        self._pe.extract_param_min_laser_length_SpinBox.editingFinished.disconnect()
        self._pe.extract_param_tolerance_SpinBox.editingFinished.disconnect()
        self._pe.laserpulses_ComboBox.currentIndexChanged.disconnect()
        self._pe.extract_param_analysis_method_comboBox.currentIndexChanged.disconnect()
        self._pe.extract_param_extraction_method_comboBox.currentIndexChanged.disconnect()
        self._pe.laserpulses_display_raw_CheckBox.stateChanged.disconnect()
        self.sig_start_line.sigPositionChangeFinished.disconnect()
        self.sig_end_line.sigPositionChangeFinished.disconnect()
        self.ref_start_line.sigPositionChangeFinished.disconnect()
        self.ref_end_line.sigPositionChangeFinished.disconnect()
        self._pe.extract_param_conv_std_dev_slider.valueChanged.disconnect()
        return

    def _disconnect_logic_signals(self):
        # Connect update signals from pulsed_master_logic
        self.pulsedmasterlogic().sigEnsembleSaUpComplete.disconnect()
        self.pulsedmasterlogic().sigSequenceSaUpComplete.disconnect()
        self.pulsedmasterlogic().sigSavedPulseBlocksUpdated.disconnect()
        self.pulsedmasterlogic().sigSavedBlockEnsemblesUpdated.disconnect()
        self.pulsedmasterlogic().sigSavedSequencesUpdated.disconnect()
        self.pulsedmasterlogic().sigGeneratorSettingsUpdated.disconnect()

        self.pulsedmasterlogic().sigCurrentPulseBlockUpdated.disconnect()
        self.pulsedmasterlogic().sigCurrentBlockEnsembleUpdated.disconnect()
        self.pulsedmasterlogic().sigCurrentSequenceUpdated.disconnect()

        self.pulsedmasterlogic().sigSignalDataUpdated.disconnect()
        self.pulsedmasterlogic().sigLaserDataUpdated.disconnect()
        self.pulsedmasterlogic().sigLaserToShowUpdated.disconnect()
        self.pulsedmasterlogic().sigElapsedTimeUpdated.disconnect()
        self.pulsedmasterlogic().sigFitUpdated.disconnect()
        self.pulsedmasterlogic().sigMeasurementStatusUpdated.disconnect()
        self.pulsedmasterlogic().sigPulserRunningUpdated.disconnect()
        self.pulsedmasterlogic().sigFastCounterSettingsUpdated.disconnect()
        self.pulsedmasterlogic().sigMeasurementSequenceSettingsUpdated.disconnect()
        self.pulsedmasterlogic().sigPulserSettingsUpdated.disconnect()
        self.pulsedmasterlogic().sigUploadedAssetsUpdated.disconnect()
        self.pulsedmasterlogic().sigLoadedAssetUpdated.disconnect()
        self.pulsedmasterlogic().sigExtMicrowaveSettingsUpdated.disconnect()
        self.pulsedmasterlogic().sigExtMicrowaveRunningUpdated.disconnect()
        self.pulsedmasterlogic().sigTimerIntervalUpdated.disconnect()
        self.pulsedmasterlogic().sigAnalysisSettingsUpdated.disconnect()
        self.pulsedmasterlogic().sigAnalysisMethodsUpdated.disconnect()
        self.pulsedmasterlogic().sigExtractionSettingsUpdated.disconnect()
        self.pulsedmasterlogic().sigExtractionMethodsUpdated.disconnect()
        return

    ###########################################################################
    #                    Main window related methods                          #
    ###########################################################################
    def _activate_main_window_ui(self):
        pass

    def _deactivate_main_window_ui(self):
        pass

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
        self._sg.load_sequence_PushButton.setEnabled(True)
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
        controlled_val_unit = self._as.ana_param_x_axis_unit_LineEdit.text()
        save_second_plot = self._pa.second_plot_ComboBox.currentText() != 'None'

        self.pulsedmasterlogic().save_measurement_data(controlled_val_unit=controlled_val_unit,
                                                       tag=save_tag,
                                                       with_error=with_error,
                                                       save_alt_data=save_second_plot)
        self._mw.action_save.setEnabled(True)
        self._mw.actionSave.setEnabled(True)
        return

    @QtCore.Slot(float)
    @QtCore.Slot(int)
    def measurement_timer_changed(self, timer_interval):
        """ This method handles the analysis timing"""
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
        self._as.ana_param_x_axis_name_LineEdit.setText(self._ana_param_x_axis_name_text)
        self._as.ana_param_x_axis_unit_LineEdit.setText(self._ana_param_x_axis_unit_text)
        self._as.ana_param_y_axis_name_LineEdit.setText(self._ana_param_y_axis_name_text)
        self._as.ana_param_y_axis_unit_LineEdit.setText(self._ana_param_y_axis_unit_text)
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
        self._ana_param_x_axis_name_text = self._as.ana_param_x_axis_name_LineEdit.text()
        self._ana_param_x_axis_unit_text = self._as.ana_param_x_axis_unit_LineEdit.text()
        self._ana_param_y_axis_name_text = self._as.ana_param_y_axis_name_LineEdit.text()
        self._ana_param_y_axis_unit_text = self._as.ana_param_y_axis_unit_LineEdit.text()

        if self._pa.second_plot_ComboBox.currentText() == 'FFT':
            self._ana_param_second_plot_x_axis_name_text = self._as.ana_param_second_plot_x_axis_name_LineEdit.text()
            self._ana_param_second_plot_x_axis_unit_text = self._as.ana_param_second_plot_x_axis_unit_LineEdit.text()
            self._ana_param_second_plot_y_axis_name_text = self._as.ana_param_second_plot_y_axis_name_LineEdit.text()
            self._ana_param_second_plot_y_axis_unit_text = self._as.ana_param_second_plot_y_axis_unit_LineEdit.text()
        else:
            self._ana_param_second_plot_x_axis_name_text = self._ana_param_x_axis_name_text
            self._ana_param_second_plot_x_axis_unit_text = self._ana_param_x_axis_unit_text
            self._ana_param_second_plot_y_axis_name_text = self._ana_param_y_axis_name_text
            self._ana_param_second_plot_y_axis_unit_text = self._ana_param_y_axis_unit_text

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

        # FIXME: Not very elegant
        self.pulsedmasterlogic()._measurement_logic.fc.set_units(
            [self._ana_param_x_axis_unit_text, self._ana_param_y_axis_unit_text])
        return

    def keep_former_analysis_settings(self):
        """ Keep the old settings """
        self._as.ana_param_x_axis_name_LineEdit.setText(self._ana_param_x_axis_name_text)
        self._as.ana_param_x_axis_unit_LineEdit.setText(self._ana_param_x_axis_unit_text)
        self._as.ana_param_y_axis_name_LineEdit.setText(self._ana_param_y_axis_name_text)
        self._as.ana_param_y_axis_unit_LineEdit.setText(self._ana_param_y_axis_unit_text)
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
    #          Predefined methods settings dialog related methods             #
    ###########################################################################
    def _activate_predefined_methods_settings_ui(self):
        """ Initialize, connect and configure the pulse generator settings to be displayed in the
        editor.
        """
        # create all GUI elements and check all boxes listed in the methods to show
        for method_name in self.pulsedmasterlogic().generate_methods:
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
        # Set ranges for the global parameters and default values
        self._pm.pm_mw_amp_Widget.setRange(0, np.inf)
        self._pm.pm_mw_freq_Widget.setRange(0, np.inf)
        self._pm.pm_channel_amp_Widget.setRange(0, np.inf)
        self._pm.pm_delay_length_Widget.setRange(0, np.inf)
        self._pm.pm_wait_time_Widget.setRange(0, np.inf)
        self._pm.pm_laser_length_Widget.setRange(0, np.inf)
        self._pm.pm_rabi_period_Widget.setRange(0, np.inf)

        self._pm.pm_mw_amp_Widget.setValue('0.125')
        self._pm.pm_mw_freq_Widget.setValue('2.87e6')
        self._pm.pm_channel_amp_Widget.setValue(0)
        self._pm.pm_delay_length_Widget.setValue('500.0e-9')
        self._pm.pm_wait_time_Widget.setValue('1.5e-6')
        self._pm.pm_laser_length_Widget.setValue('3.0e-6')
        self._pm.pm_rabi_period_Widget.setValue('200.0e-9')

        # Contraint some widgets by hardware constraints
        self._pm_apply_hardware_constraints()

        # Dynamically create GUI elements for predefined methods
        self._create_predefined_methods()
        return

    def _deactivate_predefined_methods_ui(self):
        # TODO: Implement
        pass

    def _pm_apply_hardware_constraints(self):
        # TODO: Implement
        pass

    def _create_predefined_methods(self):
        """
        Initializes the GUI elements for the predefined methods
        """
        for method_name, method in self.pulsedmasterlogic().generate_methods.items():
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
            samplo_button.clicked.connect(self.samplo_predefined_clicked)
            gridLayout.addWidget(gen_button, 0, 0, 1, 1)
            gridLayout.addWidget(samplo_button, 1, 0, 1, 1)
            # inspect current method to extract the parameters
            inspected = inspect.signature(method)
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
                        input_obj = QtWidgets.QSpinBox(groupBox)
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

    ###########################################################################
    #                   Pulse Generator tab related methods                   #
    ###########################################################################
    def _activate_pulse_generator_ui(self):
        """ Initialize, connect and configure the 'Pulse Generator' Tab.
        """
        # Apply hardware constraints to input widgets
        self._pg_apply_hardware_constraints()

        # Fill initial values from logic into input widgets
        # TODO: implement
        # update pulse generator settings
        self.pulse_generator_settings_updated(self.pulsedmasterlogic().pulse_generator_settings)

        return

    def _deactivate_pulse_generator_ui(self):
        """ Disconnects the configuration for 'Pulse Generator Tab.
        """
        # TODO: implement
        pass

    def _pg_apply_hardware_constraints(self):
        """
        Retrieve the constraints from pulser hardware and apply these constraints to the pulse
        generator GUI elements.
        """
        # block signals
        self._pg.gen_activation_config_ComboBox.blockSignals(True)
        self._pg.gen_sample_freq_DSpinBox.blockSignals(True)
        # apply constraints
        pulser_constr = self.pulsedmasterlogic().pulse_generator_constraints
        self._pg.gen_activation_config_ComboBox.addItems(list(pulser_constr.activation_config))
        self._pg.gen_sample_freq_DSpinBox.setMinimum(pulser_constr.sample_rate.min)
        self._pg.gen_sample_freq_DSpinBox.setMaximum(pulser_constr.sample_rate.max)
        # unblock signals
        self._pg.gen_activation_config_ComboBox.blockSignals(False)
        self._pg.gen_sample_freq_DSpinBox.blockSignals(False)
        return

    def pulse_generator_settings_changed(self):
        """

        @return:
        """
        if self._mw.action_run_stop.isChecked():
            return
        # FIXME: Properly implement amplitude and interleave
        settings_dict = dict()
        settings_dict['sample_rate'] = self._pg.gen_sample_freq_DSpinBox.value()
        settings_dict['activation_config'] = self._pg.gen_activation_config_ComboBox.currentText()
        settings_dict['interleave'] = self._pg.gen_use_interleave_CheckBox.isChecked()
        self.pulsedmasterlogic().set_pulse_generator_settings(settings_dict)
        return

    def pulse_generator_settings_updated(self, settings_dict):
        """

        @param settings_dict
        @return:
        """
        # block signals
        self._pg.gen_sample_freq_DSpinBox.blockSignals(True)
        self._pg.gen_use_interleave_CheckBox.blockSignals(True)
        self._pg.gen_activation_config_ComboBox.blockSignals(True)
        self._pg.gen_activation_config_LineEdit.blockSignals(True)
        self._pa.pulser_activation_config_LineEdit.blockSignals(True)
        self._pg.gen_laserchannel_ComboBox.blockSignals(True)

        # Set widgets
        # FIXME: Properly implement amplitude and interleave
        if 'sample_rate' in settings_dict:
            self._pg.gen_sample_freq_DSpinBox.setValue(settings_dict['sample_rate'])
        if 'activation_config' in settings_dict:
            config_name = settings_dict['activation_config'][0]
            index = self._pg.gen_activation_config_ComboBox.findText(config_name)
            self._pg.gen_activation_config_ComboBox.setCurrentIndex(index)
            channel_str = str(list(settings_dict['activation_config'][1]).sorted())
            channel_str = channel_str.strip('[]').replace('\'', '').replace(',', ' |')
            self._pg.gen_activation_config_LineEdit.setText(channel_str)
            self._pa.pulser_activation_config_LineEdit.setText(channel_str)
            former_laser_channel = self._pg.gen_laserchannel_ComboBox.currentText()
            self._pg.gen_laserchannel_ComboBox.clear()
            self._pg.gen_laserchannel_ComboBox.addItems(
                list(settings_dict['activation_config'][1]).sorted())
            if former_laser_channel in settings_dict['activation_config'][1]:
                index = self._pg.gen_laserchannel_ComboBox.findText(former_laser_channel)
                self._pg.gen_laserchannel_ComboBox.setCurrentIndex(index)
        if 'interleave' in settings_dict:
            self._pg.gen_use_interleave_CheckBox.setChecked(settings_dict['interleave'])

        # unblock signals
        self._pg.gen_sample_freq_DSpinBox.blockSignals(False)
        self._pg.gen_use_interleave_CheckBox.blockSignals(False)
        self._pg.gen_activation_config_ComboBox.blockSignals(False)
        self._pg.gen_activation_config_LineEdit.blockSignals(False)
        self._pa.pulser_activation_config_LineEdit.blockSignals(False)
        self._pg.gen_laserchannel_ComboBox.blockSignals(False)
        return

    def sampling_settings_changed(self):
        """

        @return:
        """
        settings_dict = dict()
        settings_dict['laser_channel'] = self._pg.gen_laserchannel_ComboBox.currentText()

        self.pulsedmasterlogic().set_sampling_settings(settings_dict)
        return

    def sampling_settings_updated(self, settings_dict):
        """

        @param settings_dict:
        @return:
        """
        # block signals
        self._pg.gen_laserchannel_ComboBox.blockSignals(True)

        if 'laser_channel' in settings_dict:
            index = self._pg.gen_laserchannel_ComboBox.findText(settings_dict['laser_channel'])
            self._pg.gen_laserchannel_ComboBox.setCurrentIndex(index)

        # unblock signals
        self._pg.gen_laserchannel_ComboBox.blockSignals(False)
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
        return

    def editor_delete_ensemble_clicked(self):
        name = self._pg.saved_ensembles_ComboBox.currentText()
        self.pulsedmasterlogic().delete_block_ensemble(name)
        return

    def editor_load_ensemble_clicked(self):
        name = self._pg.saved_ensembles_ComboBox.currentText()
        ensemble = self.pulsedmasterlogic().saved_pulse_block_ensembles[name]
        self._pg.block_organizer.load_ensemble(ensemble)
        self._pg.curr_ensemble_name_LineEdit.setText(name)

        # FIXME: This is just a rough estimation of the waveform size in MB (only valid for AWG)
        # size_mb = (ensemble_params['sequence_length_bins'] * 5) / 1024**2
        self._pg.curr_ensemble_size_DSpinBox.setValue(0.0)
        if ensemble.measurement_information:
            self._pg.curr_ensemble_length_DSpinBox.setValue(
                ensemble.measurement_information['length_s'])
            self._pg.curr_ensemble_laserpulses_SpinBox.setValue(
                ensemble.measurement_information['number_of_lasers'])
        else:
            self._pg.curr_ensemble_length_DSpinBox.setValue(0.0)
            self._pg.curr_ensemble_laserpulses_SpinBox.setValue(0)

        if ensemble.sampling_information:
            self._pg.curr_ensemble_bins_SpinBox.setValue(
                ensemble.sampling_information['length_bins'])
        else:
            self._pg.curr_ensemble_bins_SpinBox.setValue(0)
        return

    def update_block_dict(self, block_dict):
        """

        @param block_dict:
        @return:
        """
        block_names = list(block_dict).sorted()
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
        self._pg.saved_blocks_ComboBox.blockSignals(False)
        return

    def update_ensemble_dict(self, ensemble_dict):
        """

        @param ensemble_dict:
        @return:
        """
        ensemble_names = list(ensemble_dict).sorted()
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
        # unblock signals
        self._pg.gen_ensemble_ComboBox.blockSignals(False)
        self._pg.saved_ensembles_ComboBox.blockSignals(False)
        return

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
        self._pg.sample_ensemble_PushButton.setEnabled(True)
        self._pg.samplo_ensemble_PushButton.setEnabled(True)
        return

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
            method_name = method_name[4:]
        elif method_name.startswith('samplo_'):
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

        self.pulsedmasterlogic().generate_predefined_sequence(method_name, param_dict)
        return

    @QtCore.Slot()
    def samplo_predefined_clicked(self):
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
        self._pg.sample_ensemble_PushButton.setEnabled(False)
        self._pg.samplo_ensemble_PushButton.setEnabled(False)
        self._pg.load_ensemble_PushButton.setEnabled(False)

        self.pulsedmasterlogic().sample_ensemble(asset_name, True)
        return

    def update_uploaded_assets(self, asset_names_list):
        """

        @param asset_names_list:
        @return:
        """
        pass

    ###########################################################################
    #                   Sequence Generator tab related methods                #
    ###########################################################################
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
        return

    def editor_delete_sequence_clicked(self):
        name = self._sg.saved_sequences_ComboBox.currentText()
        self.pulsedmasterlogic().delete_sequence(name)
        return

    def editor_load_sequence_clicked(self):
        name = self._sg.saved_sequences_ComboBox.currentText()
        sequence = self.pulsedmasterlogic().saved_pulse_sequences[name]
        self._pg.sequence_editor.load_sequence(sequence)
        self._pg.curr_sequence_name_LineEdit.setText(name)

        # FIXME: This is just a rough estimation of the sequence size in MB
        # size_mb = (sequence_params['sequence_length_bins'] * 5) / 1024 ** 2
        self._sg.curr_sequence_size_DSpinBox.setValue(0)
        if sequence.measurement_information:
            self._pg.curr_sequence_length_DSpinBox.setValue(sequence.measurement_information['length_s'])
            self._pg.curr_sequence_laserpulses_SpinBox.setValue(sequence.measurement_information['number_of_lasers'])
        else:
            self._pg.curr_sequence_length_DSpinBox.setValue(0.0)
            self._pg.curr_sequence_laserpulses_SpinBox.setValue(0)

        if sequence.sampling_information:
            self._pg.curr_sequence_bins_SpinBox.setValue(
                sequence.sampling_information['length_bins'])
        else:
            self._pg.curr_sequence_bins_SpinBox.setValue(0)
        return

    def update_sequence_dict(self, sequence_dict):
        """

        @param sequence_dict:
        @return:
        """
        sequence_names = list(sequence_dict).sorted()
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
        self._sg.sample_sequence_PushButton.setEnabled(True)
        self._sg.samplo_sequence_PushButton.setEnabled(True)
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

    ###########################################################################
    ###     Methods related to the Tab 'Analysis' in the Pulsed Window:     ###
    ###########################################################################
    def _activate_analysis_ui(self):
        """ Initialize, connect and configure the 'Analysis' Tab.
        """
        self._pa.ana_param_errorbars_CheckBox.setChecked(self._ana_param_errorbars)
        index = self._pa.second_plot_ComboBox.findText(self._second_plot_ComboBox_text)
        self._pa.second_plot_ComboBox.setCurrentIndex(index)
        self.pulsedmasterlogic()._measurement_logic.second_plot_type = self._second_plot_ComboBox_text

        self._pa.ana_param_invoke_settings_CheckBox.setChecked(
            self.pulsedmasterlogic().invoke_settings)

        # Fit settings dialog
        self._fsd = FitSettingsDialog(self.pulsedmasterlogic()._measurement_logic.fc)
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

        # apply hardware constraints
        self._analysis_apply_hardware_constraints()

        self.toggle_settings_editor()
        self.toggle_error_bars()
        self.change_second_plot()

        # initialize values
        self.pulsedmasterlogic().request_measurement_init_values()
        return

    def _deactivate_analysis_ui(self):
        """ Disconnects the configuration for 'Analysis' Tab.
        """
        self._ana_param_errorbars = self._pa.ana_param_errorbars_CheckBox.isChecked()
        self._second_plot_ComboBox_text = self._pa.second_plot_ComboBox.currentText()
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
            self._pa.ext_control_mw_freq_DoubleSpinBox.setEnabled(False)
            self._pa.ext_control_mw_power_DoubleSpinBox.setEnabled(False)
            self._pa.ana_param_x_axis_start_ScienDSpinBox.setEnabled(False)
            self._pa.ana_param_x_axis_inc_ScienDSpinBox.setEnabled(False)
            self._pa.ana_param_num_laser_pulse_SpinBox.setEnabled(False)
            self._pa.ana_param_record_length_SpinBox.setEnabled(False)
            self._pa.ext_control_use_mw_CheckBox.setEnabled(False)
            self._pa.ana_param_fc_bins_ComboBox.setEnabled(False)
            self._pa.ana_param_ignore_first_CheckBox.setEnabled(False)
            self._pa.ana_param_ignore_last_CheckBox.setEnabled(False)
            self._pa.ana_param_alternating_CheckBox.setEnabled(False)
            self._pa.ana_param_invoke_settings_CheckBox.setEnabled(False)
            self._pa.pulser_use_interleave_CheckBox.setEnabled(False)
            self._pg.load_ensemble_PushButton.setEnabled(False)
            self._pg.gen_sample_freq_DSpinBox.setEnabled(False)
            self._pg.gen_activation_config_ComboBox.setEnabled(False)
            self._sg.load_sequence_PushButton.setEnabled(False)
            self._mw.pulser_on_off_PushButton.setEnabled(False)
            self._mw.action_continue_pause.setEnabled(True)
            self._mw.action_pull_data.setEnabled(True)
            if not self._mw.action_run_stop.isChecked():
                self._mw.action_run_stop.toggle()
        else:
            self._pa.ext_control_use_mw_CheckBox.setEnabled(True)
            self._pa.ext_control_mw_freq_DoubleSpinBox.setEnabled(True)
            self._pa.ext_control_mw_power_DoubleSpinBox.setEnabled(True)
            self._pa.ana_param_fc_bins_ComboBox.setEnabled(True)
            self._pa.ana_param_ignore_first_CheckBox.setEnabled(True)
            self._pa.ana_param_ignore_last_CheckBox.setEnabled(True)
            self._pa.ana_param_alternating_CheckBox.setEnabled(True)
            self._pa.ana_param_invoke_settings_CheckBox.setEnabled(True)
            self._pa.pulser_use_interleave_CheckBox.setEnabled(True)
            self._pa.ana_param_x_axis_start_ScienDSpinBox.setEnabled(True)
            self._pa.ana_param_x_axis_inc_ScienDSpinBox.setEnabled(True)
            self._pa.ana_param_num_laser_pulse_SpinBox.setEnabled(True)
            self._pa.ana_param_record_length_SpinBox.setEnabled(True)
            self._pg.load_ensemble_PushButton.setEnabled(True)
            self._pg.gen_sample_freq_DSpinBox.setEnabled(True)
            self._pg.gen_activation_config_ComboBox.setEnabled(True)
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

    @QtCore.Slot()
    def measurement_data_updated(self):
        """

        @return:
        """
        signal_data = self.pulsedmasterlogic().signal_data
        signal_alt_data = self.pulsedmasterlogic().signal_alt_data
        measurement_error = self.pulsedmasterlogic().measurement_error

        # create ErrorBarItems
        tmp_array = signal_data[0, 1:] - signal_data[0, :-1]
        beamwidth = tmp_array.min() if tmp_array.min() > 0 else tmp_array.max()
        del tmp_array
        beamwidth /= 3
        self.signal_image_error_bars.setData(x=signal_data[0],
                                             y=signal_data[1],
                                             top=measurement_error[1],
                                             bottom=measurement_error[1],
                                             beam=beamwidth)
        if signal_data.shape[1] > 2 and measurement_error.shape[1] > 2:
            self.signal_image_error_bars2.setData(x=signal_data[0],
                                                  y=signal_data[2],
                                                  top=measurement_error[2],
                                                  bottom=measurement_error[2],
                                                  beam=beamwidth)

        # dealing with the actual signal plot
        self.signal_image.setData(x=signal_data[0], y=signal_data[1])
        if signal_data.shape[1] > 2:
            self.signal_image2.setData(x=signal_data[0], y=signal_data[2])

        # dealing with the secondary plot
        self.second_plot_image.setData(x=signal_alt_data[0], y=signal_alt_data[1])
        if signal_alt_data.shape[1] > 2:
            self.second_plot_image2.setData(x=signal_alt_data[0], y=signal_alt_data[2])

        # dealing with the error plot
        self.measuring_error_image.setData(x=measurement_error[0], y=measurement_error[1])
        if measurement_error.shape[1] > 2:
            self.measuring_error_image2.setData(x=measurement_error[0], y=measurement_error[2])

        # dealing with the laser plot
        self.update_laser_data()
        return

    @QtCore.Slot()
    def fit_clicked(self):
        """Fits the current data"""
        current_fit_method = self._pa.fit_param_fit_func_ComboBox.getCurrentFit()[0]
        self.pulsedmasterlogic().do_fit(current_fit_method)
        return

    @QtCore.Slot(str, np.ndarray, object)
    def fit_data_updated(self, fit_method, fit_data, result):
        """

        @param fit_method:
        @param fit_data:
        @param result:
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
                formatted_fitresult = units.create_formatted_output(result.result_str_dict)
            except:
                formatted_fitresult = 'This fit does not return formatted results'
        self._pa.fit_param_results_TextBrowser.setPlainText(formatted_fitresult)

        self.fit_image.setData(x=fit_data[0], y=fit_data[1])
        if fit_method == 'No Fit' and self.fit_image in self._pa.pulse_analysis_PlotWidget.items():
            self._pa.pulse_analysis_PlotWidget.removeItem(self.fit_image)
        elif fit_method != 'No Fit' and self.fit_image not in self._pa.pulse_analysis_PlotWidget.items():
            self._pa.pulse_analysis_PlotWidget.addItem(self.fit_image)
        if fit_method:
            self._pa.fit_param_fit_func_ComboBox.setCurrentFit(fit_method)
        # unblock signals
        self._pa.fit_param_fit_func_ComboBox.blockSignals(False)
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
        if 'frequency' in settings_dict:
            self._pa.ext_control_mw_freq_DoubleSpinBox.setValue(settings_dict['frequency'])
        if 'power' in settings_dict:
            self._pa.ext_control_mw_power_DoubleSpinBox.setValue(settings_dict['power'])

        # unblock signals
        self._pa.ext_control_mw_freq_DoubleSpinBox.blockSignals(False)
        self._pa.ext_control_mw_power_DoubleSpinBox.blockSignals(False)
        self._pa.ext_control_use_mw_CheckBox.blockSignals(False)
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
        settings_dict['record_length'] = self._pa.ana_param_record_length_SpinBox.value()
        settings_dict['bin_width'] = float(self._pa.ana_param_fc_bins_ComboBox.currentText())
        self.pulsedmasterlogic().set_fast_counter_settings(settings_dict)
        return

    @QtCore.Slot(dict)
    def fast_counter_settings_updated(self, settings_dict):
        """

        @param dict settings_dict:
        """
        # block signals
        self._pa.ana_param_record_length_SpinBox.blockSignals(True)
        self._pa.ana_param_fc_bins_ComboBox.blockSignals(True)
        # set widgets
        if 'record_length' in settings_dict:
            self._pa.ana_param_record_length_SpinBox.setValue(settings_dict['record_length'])
        if 'bin_width' in settings_dict:
            index = self._pa.ana_param_fc_bins_ComboBox.findText(str(settings_dict['bin_width']))
            self._pa.ana_param_fc_bins_ComboBox.setCurrentIndex(index)
        # unblock signals
        self._pa.ana_param_record_length_SpinBox.blockSignals(False)
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
        self._pe.laserpulses_ComboBox.blockSignals(True)

        # set widgets
        if 'number_of_lasers' in settings_dict:
            self._pa.ana_param_num_laser_pulse_SpinBox.setValue(settings_dict['number_of_lasers'])
            self._pe.laserpulses_ComboBox.clear()
            self._pe.laserpulses_ComboBox.addItem('sum')
            self._pe.laserpulses_ComboBox.addItems(
                [str(i) for i in range(1, settings_dict['number_of_lasers'] + 1)])
        if 'alternating' in settings_dict:
            self._pa.ana_param_alternating_CheckBox.setChecked(settings_dict['alternating'])
            if settings_dict['alternating']:
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
        if 'laser_ignore_list' in settings_dict:
            self._pa.ana_param_ignore_first_CheckBox.setChecked(
                0 in settings_dict['laser_ignore_list'])
            if -1 in settings_dict['laser_ignore_list'] or self._pa.ana_param_num_laser_pulse_SpinBox.value() - 1 in settings_dict['laser_ignore_list']:
                self._pa.ana_param_ignore_last_CheckBox.setChecked(True)
            else:
                self._pa.ana_param_ignore_last_CheckBox.setChecked(False)
        if 'controlled_variable' in settings_dict:
            self._pa.ana_param_x_axis_start_ScienDSpinBox.setValue(
                settings_dict['controlled_variable'][0])
            if len(settings_dict['controlled_variable']) > 1:
                self._pa.ana_param_x_axis_inc_ScienDSpinBox.setValue(
                    settings_dict['controlled_variable'][1] - settings_dict['controlled_variable'][
                        0])
            else:
                self._pa.ana_param_x_axis_inc_ScienDSpinBox.setValue(
                    settings_dict['controlled_variable'][0])
        if 'invoke_settings' in settings_dict:
            self.toggle_settings_editor(settings_dict['invoke_settings'])

        # unblock signals
        self._pa.ana_param_ignore_first_CheckBox.blockSignals(False)
        self._pa.ana_param_ignore_last_CheckBox.blockSignals(False)
        self._pa.ana_param_alternating_CheckBox.blockSignals(False)
        self._pa.ana_param_num_laser_pulse_SpinBox.blockSignals(False)
        self._pa.ana_param_x_axis_start_ScienDSpinBox.blockSignals(False)
        self._pa.ana_param_x_axis_inc_ScienDSpinBox.blockSignals(False)
        self._pe.laserpulses_ComboBox.blockSignals(False)
        return

    def toggle_settings_editor(self, hide_editor):
        """
        Shows or hides input widgets for measurement settings and fast counter settings
        """
        self._pa.ana_param_invoke_settings_CheckBox.blockSignals(True)
        self._pa.ana_param_invoke_settings_CheckBox.setChecked(hide_editor)
        self._pa.ana_param_invoke_settings_CheckBox.blockSignals(False)
        if hide_editor:
            self._pa.ana_param_x_axis_start_ScienDSpinBox.setEnabled(False)
            self._pa.ana_param_x_axis_inc_ScienDSpinBox.setEnabled(False)
            self._pa.ana_param_num_laser_pulse_SpinBox.setEnabled(False)
            self._pa.ana_param_record_length_SpinBox.setEnabled(False)
        else:
            self._pa.ana_param_x_axis_start_ScienDSpinBox.setEnabled(True)
            self._pa.ana_param_x_axis_inc_ScienDSpinBox.setEnabled(True)
            self._pa.ana_param_num_laser_pulse_SpinBox.setEnabled(True)
            self._pa.ana_param_record_length_SpinBox.setEnabled(True)
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
        is_alternating = self._pa.ana_param_alternating_CheckBox.isChecked()

        if second_plot == 'None':
            self._pa.second_plot_GroupBox.setVisible(False)
        else:
            self._pa.second_plot_GroupBox.setVisible(True)

        if second_plot == 'Delta' and not is_alternating:
            self.log.error('Delta can only be selected for the second plot if the sequence is '
                           'alternating. Setting it to None instead.')
            self._pa.second_plot_ComboBox.blockSignals(True)
            index = self._pa.second_plot_ComboBox.findText('None')
            self._pa.second_plot_ComboBox.setCurrentIndex(index)
            self._pa.second_plot_ComboBox.blockSignals(False)

        self.pulsedmasterlogic().set_alternative_data_type(second_plot)
        self._pa.second_plot_GroupBox.setTitle(second_plot)
        return

    def _activate_extraction_ui(self):
        # Configure the lasertrace plot display:
        self.sig_start_line = pg.InfiniteLine(pos=0,
                                              pen=QtGui.QPen(palette.c3, 5e-9),
                                              movable=True)
        # self.sig_start_line.setHoverPen(QtGui.QPen(palette.c3), width=10)
        self.sig_end_line = pg.InfiniteLine(pos=0,
                                            pen=QtGui.QPen(palette.c3, 5e-9),
                                            movable=True)
        # self.sig_end_line.setHoverPen(QtGui.QPen(palette.c3), width=10)
        self.ref_start_line = pg.InfiniteLine(pos=0,
                                              pen=QtGui.QPen(palettedark.c4, 5e-9),
                                              movable=True)
        # self.ref_start_line.setHoverPen(QtGui.QPen(palette.c4), width=10)
        self.ref_end_line = pg.InfiniteLine(pos=0,
                                            pen=QtGui.QPen(palettedark.c4, 5e-9),
                                            movable=True)
        # self.ref_end_line.setHoverPen(QtGui.QPen(palette.c4), width=10)
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

        self.lasertrace_image = pg.PlotDataItem(np.array(range(10)), np.zeros(10), pen=palette.c1)
        self._pe.laserpulses_PlotWidget.addItem(self.lasertrace_image)
        self._pe.laserpulses_PlotWidget.addItem(self.sig_start_line)
        self._pe.laserpulses_PlotWidget.addItem(self.sig_end_line)
        self._pe.laserpulses_PlotWidget.addItem(self.ref_start_line)
        self._pe.laserpulses_PlotWidget.addItem(self.ref_end_line)
        self._pe.laserpulses_PlotWidget.setLabel(axis='bottom', text='time', units='s')

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
        extraction_settings['threshold_tolerance'] = self._pe.extract_param_tolerance_SpinBox.value()
        extraction_settings['min_laser_length'] = self._pe.extract_param_min_laser_length_SpinBox.value()

        self.pulsedmasterlogic().extraction_settings_changed(extraction_settings)
        return

    def extraction_settings_updated(self, settings_dict):
        """

        @param dict settings_dict: dictionary with parameters to update
        @return:
        """

        if 'current_method' in settings_dict:
            self._pe.extract_param_extraction_method_comboBox.blockSignals(True)
            index = self._pe.extract_param_extraction_method_comboBox.findText(settings_dict['current_method'])
            self._pe.extract_param_extraction_method_comboBox.setCurrentIndex(index)
            self._pe.extract_param_extraction_method_comboBox.blockSignals(False)

        if 'conv_std_dev' in settings_dict:
            self._pe.extract_param_conv_std_dev_slider.blockSignals(True)
            self._pe.extract_param_conv_std_dev_DSpinBox.blockSignals(True)
            self._pe.extract_param_conv_std_dev_DSpinBox.setValue(settings_dict['conv_std_dev'])
            self._pe.extract_param_conv_std_dev_slider.setValue(settings_dict['conv_std_dev'])
            self._pe.extract_param_conv_std_dev_slider.blockSignals(False)
            self._pe.extract_param_conv_std_dev_DSpinBox.blockSignals(False)

        if 'count_threshold' in settings_dict:
            self._pe.extract_param_threshold_SpinBox.blockSignals(True)
            self._pe.extract_param_threshold_SpinBox.setValue(settings_dict['count_threshold'])
            self._pe.extract_param_threshold_SpinBox.blockSignals(False)

        if 'threshold_tolerance' in settings_dict:
            self._pe.extract_param_tolerance_SpinBox.blockSignals(True)
            self._pe.extract_param_tolerance_SpinBox.setValue(settings_dict['threshold_tolerance'])
            self._pe.extract_param_tolerance_SpinBox.blockSignals(False)

        if 'min_laser_length' in settings_dict:
            self._pe.extract_param_min_laser_length_SpinBox.blockSignals(True)
            self._pe.extract_param_min_laser_length_SpinBox.setValue(settings_dict['min_laser_length'])
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

        self.pulsedmasterlogic().analysis_settings_changed(analysis_settings)
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

    @QtCore.Slot()
    def update_laser_data(self):
        """

        @return:
        """
        laser_index = self._pe.laserpulses_ComboBox.currentIndex()
        show_raw = self._pe.laserpulses_display_raw_CheckBox.isChecked()
        is_gated = self.pulsedmasterlogic().raw_data.shape[1] > 2
        if show_raw:
            if is_gated:
                if laser_index == 0:
                    self.lasertrace_image.setData(x=self.pulsedmasterlogic().raw_data[0],
                                                  y=np.sum(self.pulsedmasterlogic().raw_data[1:],
                                                           0))
                else:
                    self.lasertrace_image.setData(x=self.pulsedmasterlogic().raw_data[0],
                                                  y=self.pulsedmasterlogic().raw_data[laser_index])
            else:
                self.lasertrace_image.setData(x=self.pulsedmasterlogic().raw_data[0],
                                              y=self.pulsedmasterlogic().raw_data[1])
        else:
            if laser_index == 0:
                self.lasertrace_image.setData(x=self.pulsedmasterlogic().laser_data[0],
                                              y=np.sum(self.pulsedmasterlogic().laser_data[1:], 0))
            else:
                self.lasertrace_image.setData(x=self.pulsedmasterlogic().laser_data[0],
                                              y=self.pulsedmasterlogic().laser_data[laser_index])
        return


