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


from gui.guibase import GUIBase
from gui.colordefs import QudiPalettePale as palette
from gui.colordefs import QudiPalette as palettedark
from core.util.mutex import Mutex
from core.util import units

from logic.pulse_objects import Pulse_Block_Element
from logic.pulse_objects import Pulse_Block
from logic.pulse_objects import Pulse_Block_Ensemble
from logic.pulse_objects import Pulse_Sequence

from .spinbox_delegate import SpinBoxDelegate
from .doublespinbox_delegate import DoubleSpinBoxDelegate
from .combobox_delegate import ComboBoxDelegate
from .checkbox_delegate import CheckBoxDelegate

#FIXME: Display the Pulse
#FIXME: save the length in sample points (bins)
#FIXME: adjust the length to the bins
#FIXME: Later that should be able to round up the values directly within


class PulsedMeasurementMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pulsed_noeditor.ui')

        # Load it
        super(PulsedMeasurementMainWindow, self).__init__()

        uic.loadUi(ui_file, self)
        self.show()

class BlockSettingDialog(QtWidgets.QDialog):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pulsed_main_gui_settings_block_gen.ui')

        # Load it
        super(BlockSettingDialog, self).__init__()

        uic.loadUi(ui_file, self)

class AnalysisSettingDialog(QtWidgets.QDialog):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui-pulsed-main-gui-settings-analysis.ui')

        # Load it
        super(AnalysisSettingDialog, self).__init__()

        uic.loadUi(ui_file, self)

class PulsedMeasurementGui(GUIBase):
    """ This is the main GUI Class for pulsed measurements. """

    _modclass = 'PulsedMeasurementGui'
    _modtype = 'gui'

    ## declare connectors
    _in = {'pulsedmasterlogic': 'PulsedMasterLogic',
           'savelogic': 'SaveLogic'}

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{}: {}'.format(key,config[key]))

        # that variable is for testing issues and can be deleted if not needed:
        self._write_chunkwise = False

    def on_activate(self, e=None):
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
        self._pulsed_master_logic = self.connector['in']['pulsedmasterlogic']['object']
        self._save_logic = self.connector['in']['savelogic']['object']

        self._mw = PulsedMeasurementMainWindow()

        self._activate_analysis_settings_ui(e)
        self._activate_analysis_ui(e)

        self._activate_pulse_generator_ui(e)

        self.show()

    def on_deactivate(self, e):
        """ Undo the Definition, configuration and initialisation of the pulsed
            measurement GUI.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.

        This deactivation disconnects all the graphic modules, which were
        connected in the initUI method.
        """
        self._deactivate_analysis_settings_ui(e)
        self._deactivate_analysis_ui(e)

        self._deactivate_pulse_generator_ui(e)

        self._mw.close()

    def show(self):
        """Make main window visible and put it above all other windows. """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def get_current_function_list(self):
        """ Retrieve the functions, which are chosen by the user.

        @return: list[] with strings of the used functions. Names are based on
                 the passed func_config dict from the logic. Depending on the
                 settings, a current function list is generated.
        """
        current_functions = []

        for index in range(len(list(self._pulsed_master_logic._generator_logic.func_config))):
            name_checkbox = 'checkbox_' + str(index)
            checkbox = getattr(self._bs, name_checkbox)
            if checkbox.isChecked():
                name_label = 'func_' + str(index)
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
        # connect signals of input widgets
        self._mw.gen_sample_freq_DSpinBox.editingFinished.connect(self.generator_settings_changed, QtCore.Qt.QueuedConnection)
        self._mw.gen_laserchannel_ComboBox.currentIndexChanged.connect(self.generator_settings_changed, QtCore.Qt.QueuedConnection)
        self._mw.gen_activation_config_ComboBox.currentIndexChanged.connect(self.generator_settings_changed, QtCore.Qt.QueuedConnection)
        # connect signals of buttons
        self._mw.sample_ensemble_PushButton.clicked.connect(self.sample_ensemble_clicked)
        self._mw.sample_sequence_PushButton.clicked.connect(self.sample_sequence_clicked)

        # connect update signals from pulsed_master_logic
        self._pulsed_master_logic.sigBlockEnsembleSampled.connect(self.sample_ensemble_finished)
        self._pulsed_master_logic.sigSequenceSampled.connect(self.sample_sequence_finished)
        self._pulsed_master_logic.sigSavedPulseBlocksUpdated.connect(self.update_block_list)
        self._pulsed_master_logic.sigSavedBlockEnsemblesUpdated.connect(self.update_ensemble_list)
        self._pulsed_master_logic.sigSavedSequencesUpdated.connect(self.update_sequence_list)
        self._pulsed_master_logic.sigGeneratorSettingsUpdated.connect(self.update_generator_settings)

        # self._pulsed_master_logic.sigCurrentPulseBlockUpdated.connect(self.)
        # self._pulsed_master_logic.sigCurrentBlockEnsembleUpdated.connect(self.)
        # self._pulsed_master_logic.sigCurrentSequenceUpdated.connect(self.)

        # Apply hardware constraints to input widgets
        self._gen_apply_hardware_constraints()

        # Fill initial values from logic into input widgets
        self._pulsed_master_logic.request_generator_init_values()
        return


    def _deactivate_pulse_generator_ui(self, e):
        """ Disconnects the configuration for 'Pulse Generator Tab.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        # disconnect signals of input widgets
        self._mw.gen_sample_freq_DSpinBox.editingFinished.disconnect()
        self._mw.gen_laserchannel_ComboBox.currentIndexChanged.disconnect()
        self._mw.gen_activation_config_ComboBox.currentIndexChanged.disconnect()
        # disconnect signals of buttons
        self._mw.sample_ensemble_PushButton.clicked.disconnect()
        self._mw.sample_sequence_PushButton.clicked.disconnect()
        # disconnect update signals from pulsed_master_logic
        self._pulsed_master_logic.sigBlockEnsembleSampled.disconnect()
        self._pulsed_master_logic.sigSequenceSampled.disconnect()
        self._pulsed_master_logic.sigSavedPulseBlocksUpdated.disconnect()
        self._pulsed_master_logic.sigSavedBlockEnsemblesUpdated.disconnect()
        self._pulsed_master_logic.sigSavedSequencesUpdated.disconnect()
        self._pulsed_master_logic.sigGeneratorSettingsUpdated.disconnect()
        # self._pulsed_master_logic.sigCurrentPulseBlockUpdated.disconnect()
        # self._pulsed_master_logic.sigCurrentBlockEnsembleUpdated.disconnect()
        # self._pulsed_master_logic.sigCurrentSequenceUpdated.disconnect()
        return

    def _gen_apply_hardware_constraints(self):
        """
        Retrieve the constraints from pulser hardware and apply these constraints to the pulse
        generator GUI elements.
        """
        # block signals
        self._mw.gen_activation_config_ComboBox.blockSignals(True)
        self._mw.gen_sample_freq_DSpinBox.blockSignals(True)
        # apply constraints
        pulser_constr, dummy = self._pulsed_master_logic.get_hardware_constraints()
        self._mw.gen_activation_config_ComboBox.addItems(list(pulser_constr['activation_config']))
        self._mw.gen_sample_freq_DSpinBox.setMinimum(pulser_constr['sample_rate']['min'])
        self._mw.gen_sample_freq_DSpinBox.setMaximum(pulser_constr['sample_rate']['max'])
        # unblock signals
        self._mw.gen_activation_config_ComboBox.blockSignals(False)
        self._mw.gen_sample_freq_DSpinBox.blockSignals(False)
        return

    def generator_settings_changed(self):
        """

        @return:
        """
        sample_rate = self._mw.gen_sample_freq_DSpinBox.value()
        laser_channel = self._mw.gen_laserchannel_ComboBox.currentText()
        activation_config_name = self._mw.gen_activation_config_ComboBox.currentText()
        amplitude_dict = self._pulsed_master_logic._generator_logic.amplitude_list

        self._pulsed_master_logic.generator_settings_changed(activation_config_name, laser_channel,
                                                             sample_rate, amplitude_dict)
        return

    def update_generator_settings(self, activation_config_name, activation_config, sample_rate,
                                   amplitude_dict, laser_channel):
        """

        @param activation_config_name:
        @param activation_config:
        @param sample_rate:
        @param amplitude_dict:
        @param laser_channel:
        @return:
        """
        # block signals
        self._mw.gen_sample_freq_DSpinBox.blockSignals(True)
        self._mw.gen_laserchannel_ComboBox.blockSignals(True)
        self._mw.gen_activation_config_ComboBox.blockSignals(True)
        # activation config
        index = self._mw.gen_activation_config_ComboBox.findText(activation_config_name)
        self._mw.gen_activation_config_ComboBox.setCurrentIndex(index)
        display_str = ''
        for chnl in activation_config:
            display_str += chnl + ' | '
        display_str = display_str[:-3]
        self._mw.gen_activation_config_LineEdit.setText(display_str)
        self._mw.gen_analog_channels_SpinBox.setValue(
            len([chnl for chnl in activation_config if 'a_ch' in chnl]))
        self._mw.gen_digital_channels_SpinBox.setValue(
            len([chnl for chnl in activation_config if 'd_ch' in chnl]))
        # laser channel
        self._mw.gen_laserchannel_ComboBox.clear()
        self._mw.gen_laserchannel_ComboBox.addItems(activation_config)
        index = self._mw.gen_laserchannel_ComboBox.findText(laser_channel)
        self._mw.gen_laserchannel_ComboBox.setCurrentIndex(index)
        #sample rate
        self._mw.gen_sample_freq_DSpinBox.setValue(sample_rate)
        # unblock signals
        self._mw.gen_sample_freq_DSpinBox.blockSignals(False)
        self._mw.gen_laserchannel_ComboBox.blockSignals(False)
        self._mw.gen_activation_config_ComboBox.blockSignals(False)
        return

    def update_block_list(self, block_list):
        """

        @param block_list:
        @return:
        """
        pass

    def update_ensemble_list(self, ensemble_list):
        """

        @param ensemble_list:
        @return:
        """
        # block signals
        self._mw.gen_ensemble_ComboBox.blockSignals(True)
        # update gen_sequence_ComboBox items
        self._mw.gen_ensemble_ComboBox.clear()
        self._mw.gen_ensemble_ComboBox.addItems(ensemble_list)
        # unblock signals
        self._mw.gen_ensemble_ComboBox.blockSignals(False)
        return

    def update_sequence_list(self, sequence_list):
        """

        @param sequence_list:
        @return:
        """
        # block signals
        self._mw.gen_sequence_ComboBox.blockSignals(True)
        # update gen_sequence_ComboBox items
        self._mw.gen_sequence_ComboBox.clear()
        self._mw.gen_sequence_ComboBox.addItems(sequence_list)
        # unblock signals
        self._mw.gen_sequence_ComboBox.blockSignals(False)
        return

    def sample_ensemble_clicked(self):
        """
        This method is called when the user clicks on "sample"
        """
        # Get the ensemble name from the ComboBox
        ensemble_name = self._mw.gen_ensemble_ComboBox.currentText()
        # Sample the ensemble via logic module
        self._pulsed_master_logic.sample_block_ensemble(ensemble_name, True, self._write_chunkwise)
        # disable button
        self._mw.sample_ensemble_PushButton.setEnabled(False)
        return

    def sample_ensemble_finished(self):
        """

        @return:
        """
        # enable button
        self._mw.sample_ensemble_PushButton.setEnabled(True)
        return

    def sample_sequence_clicked(self):
        """
        This method is called when the user clicks on "sample"
        """
        # Get the sequence name from the ComboBox
        sequence_name = self._mw.gen_sequence_ComboBox.currentText()
        # Sample the sequence via logic module
        self._pulsed_master_logic.sample_sequence(sequence_name, True, self._write_chunkwise)
        # disable button
        self._mw.sample_sequence_PushButton.setEnabled(False)
        return

    def sample_sequence_finished(self):
        """

        @return:
        """
        # enable button
        self._mw.sample_sequence_PushButton.setEnabled(True)
        return

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
        self._as.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.update_analysis_settings)

        if 'ana_param_x_axis_name_LineEdit' in self._statusVariables:
            self._as.ana_param_x_axis_name_LineEdit.setText(self._statusVariables['ana_param_x_axis_name_LineEdit'])
        if 'ana_param_x_axis_unit_LineEdit' in self._statusVariables:
            self._as.ana_param_x_axis_unit_LineEdit.setText(self._statusVariables['ana_param_x_axis_unit_LineEdit'])
        if 'ana_param_y_axis_name_LineEdit' in self._statusVariables:
            self._as.ana_param_y_axis_name_LineEdit.setText(self._statusVariables['ana_param_y_axis_name_LineEdit'])
        if 'ana_param_y_axis_unit_LineEdit' in self._statusVariables:
            self._as.ana_param_y_axis_unit_LineEdit.setText(self._statusVariables['ana_param_y_axis_unit_LineEdit'])
        if 'ana_param_second_plot_x_axis_name_LineEdit' in self._statusVariables:
            self._as.ana_param_second_plot_x_axis_name_LineEdit.setText(self._statusVariables['ana_param_second_plot_x_axis_name_LineEdit'])
        if 'ana_param_second_plot_x_axis_unit_LineEdit' in self._statusVariables:
            self._as.ana_param_second_plot_x_axis_unit_LineEdit.setText(self._statusVariables['ana_param_second_plot_x_axis_unit_LineEdit'])
        if 'ana_param_second_plot_y_axis_name_LineEdit' in self._statusVariables:
            self._as.ana_param_second_plot_y_axis_name_LineEdit.setText(self._statusVariables['ana_param_second_plot_y_axis_name_LineEdit'])
        if 'ana_param_second_plot_y_axis_unit_LineEdit' in self._statusVariables:
            self._as.ana_param_second_plot_y_axis_unit_LineEdit.setText(self._statusVariables['ana_param_second_plot_y_axis_unit_LineEdit'])
        self.update_analysis_settings()
        return


    def _deactivate_analysis_settings_ui(self, e):
        """ Disconnects the configuration of the Settings for 'Analysis' Tab.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        self._statusVariables['ana_param_x_axis_name_LineEdit'] = self._as.ana_param_x_axis_name_LineEdit.text()
        self._statusVariables['ana_param_x_axis_unit_LineEdit'] = self._as.ana_param_x_axis_unit_LineEdit.text()
        self._statusVariables['ana_param_y_axis_name_LineEdit'] = self._as.ana_param_y_axis_name_LineEdit.text()
        self._statusVariables['ana_param_y_axis_unit_LineEdit'] = self._as.ana_param_y_axis_unit_LineEdit.text()
        self._statusVariables['ana_param_second_plot_x_axis_name_LineEdit'] = self._as.ana_param_second_plot_x_axis_name_LineEdit.text()
        self._statusVariables['ana_param_second_plot_x_axis_unit_LineEdit'] = self._as.ana_param_second_plot_x_axis_unit_LineEdit.text()
        self._statusVariables['ana_param_second_plot_y_axis_name_LineEdit'] = self._as.ana_param_second_plot_y_axis_name_LineEdit.text()
        self._statusVariables['ana_param_second_plot_y_axis_unit_LineEdit'] = self._as.ana_param_second_plot_y_axis_unit_LineEdit.text()
        return


    def update_analysis_settings(self):
        """ Apply the new settings """
        self._mw.pulse_analysis_PlotWidget.setLabel(axis='bottom',
            text=self._as.ana_param_x_axis_name_LineEdit.text(),
            units=self._as.ana_param_x_axis_unit_LineEdit.text())
        self._mw.pulse_analysis_PlotWidget.setLabel(axis='left',
            text=self._as.ana_param_y_axis_name_LineEdit.text(),
            units=self._as.ana_param_y_axis_unit_LineEdit.text())
        self._mw.pulse_analysis_second_PlotWidget.setLabel(axis='bottom',
            text=self._as.ana_param_second_plot_x_axis_name_LineEdit.text(),
            units=self._as.ana_param_second_plot_x_axis_unit_LineEdit.text())
        self._mw.pulse_analysis_second_PlotWidget.setLabel(axis='left',
            text=self._as.ana_param_second_plot_y_axis_name_LineEdit.text(),
            units=self._as.ana_param_second_plot_y_axis_unit_LineEdit.text())
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
    def _activate_analysis_ui(self, e):
        """ Initialize, connect and configure the 'Analysis' Tab.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        self._mw.second_plot_GroupBox.setVisible(False)
        # Configure the main pulse analysis display:
        self.signal_image = pg.PlotDataItem(np.array(range(10)), np.zeros(10), pen=palette.c1)
        self._mw.pulse_analysis_PlotWidget.addItem(self.signal_image)
        self.signal_image2 = pg.PlotDataItem(pen=palette.c3)
        self._mw.pulse_analysis_PlotWidget.addItem(self.signal_image2)
        self._mw.pulse_analysis_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        # Configure the fit of the data in the main pulse analysis display:
        self.fit_image = pg.PlotDataItem(pen=palette.c2)
        self._mw.pulse_analysis_PlotWidget.addItem(self.fit_image)
        self._mw.fit_param_fit_func_ComboBox.clear()
        self._mw.fit_param_fit_func_ComboBox.addItems(self._pulsed_master_logic.get_fit_functions())

        # Configure the errorbars of the data in the main pulse analysis display:
        self.signal_image_error_bars = pg.ErrorBarItem(x=np.array(range(10)), y=np.zeros(10),
                                                       top=0., bottom=0., pen=palette.c1)
        self.signal_image_error_bars2 = pg.ErrorBarItem(x=np.array(range(10)), y=np.zeros(10),
                                                        top=0., bottom=0., pen=palette.c3)

        # Configure the second pulse analysis display:
        self.second_plot_image = pg.PlotDataItem(np.array(range(10)), np.zeros(10), pen=palette.c1)
        self._mw.pulse_analysis_second_PlotWidget.addItem(self.second_plot_image)
        self._mw.pulse_analysis_second_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        # Configure the lasertrace plot display:
        self.sig_start_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(palette.c3), movable=True)
        self.sig_start_line.setHoverPen(QtGui.QPen(palette.c2))
        self.sig_end_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(palette.c3), movable=True)
        self.sig_end_line.setHoverPen(QtGui.QPen(palette.c2))
        self.ref_start_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(palettedark.c4), movable=True)
        self.ref_start_line.setHoverPen(QtGui.QPen(palette.c4))
        self.ref_end_line = pg.InfiniteLine(pos=0, pen=QtGui.QPen(palettedark.c4), movable=True)
        self.ref_end_line.setHoverPen(QtGui.QPen(palette.c4))
        self.lasertrace_image = pg.PlotDataItem(np.array(range(10)), np.zeros(10), pen=palette.c1)
        self._mw.laserpulses_PlotWidget.addItem(self.lasertrace_image)
        self._mw.laserpulses_PlotWidget.addItem(self.sig_start_line)
        self._mw.laserpulses_PlotWidget.addItem(self.sig_end_line)
        self._mw.laserpulses_PlotWidget.addItem(self.ref_start_line)
        self._mw.laserpulses_PlotWidget.addItem(self.ref_end_line)
        self._mw.laserpulses_PlotWidget.setLabel('bottom', 'bins')

        # Configure the measuring error display:
        self.measuring_error_image = pg.PlotDataItem(np.array(range(10)), np.zeros(10),
                                                     pen=palette.c1)
        self.measuring_error_image2 = pg.PlotDataItem(np.array(range(10)), np.zeros(10),
                                                     pen=palette.c3)
        self._mw.measuring_error_PlotWidget.addItem(self.measuring_error_image)
        self._mw.measuring_error_PlotWidget.addItem(self.measuring_error_image2)
        self._mw.measuring_error_PlotWidget.setLabel('left', 'measuring error', units='a.u.')
        self._mw.measuring_error_PlotWidget.setLabel('bottom', 'tau', units='ns')

        # create all the needed control widgets on the fly and connect their
        # actions to each other:
        self._mw.pulser_on_off_PushButton = QtWidgets.QPushButton(self._mw)
        self._mw.pulser_on_off_PushButton.setText('Pulser ON')
        self._mw.pulser_on_off_PushButton.setToolTip('Switch the device on and off.\n')
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

        # set boundaries
        self._mw.slider_conv_std_dev.setRange(1, 200)
        self._mw.conv_std_dev.setRange(1, 200)

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
        self._pulsed_master_logic.sigAnalysisWindowsUpdated.connect(self.analysis_windows_updated)
        self._pulsed_master_logic.sigAnalysisMethodUpdated.connect(self.analysis_method_updated)

        # connect button click signals
        self._mw.upload_ensemble_PushButton.clicked.connect(self.upload_ensemble_clicked)
        self._mw.load_ensemble_PushButton.clicked.connect(self.load_ensemble_clicked)
        self._mw.upload_sequence_PushButton.clicked.connect(self.upload_sequence_clicked)
        self._mw.load_sequence_PushButton.clicked.connect(self.load_sequence_clicked)
        self._mw.pulser_on_off_PushButton.clicked.connect(self.pulser_on_off_clicked)
        self._mw.clear_device_PushButton.clicked.connect(self.clear_pulser_clicked)
        self._mw.fit_param_PushButton.clicked.connect(self.fit_clicked)

        # connect action trigger signals
        self._mw.action_run_stop.triggered.connect(self.measurement_run_stop_clicked)
        self._mw.action_continue_pause.triggered.connect(self.measurement_continue_pause_clicked)
        self._mw.action_pull_data.triggered.connect(self.pull_data_clicked)
        self._mw.action_save.triggered.connect(self.save_clicked)
        self._mw.action_Settings_Analysis.triggered.connect(self.show_analysis_settings)

        # connect checkbox click signals
        self._mw.ext_control_use_mw_CheckBox.stateChanged.connect(self.ext_mw_params_changed)
        self._mw.ana_param_x_axis_defined_CheckBox.stateChanged.connect(self.toggle_laser_xaxis_editor)
        self._mw.ana_param_laserpulse_defined_CheckBox.stateChanged.connect(self.toggle_laser_xaxis_editor)
        self._mw.ana_param_alternating_CheckBox.stateChanged.connect(self.measurement_sequence_settings_changed)
        self._mw.ana_param_ignore_first_CheckBox.stateChanged.connect(self.measurement_sequence_settings_changed)
        self._mw.ana_param_ignore_last_CheckBox.stateChanged.connect(self.measurement_sequence_settings_changed)
        self._mw.laserpulses_display_raw_CheckBox.stateChanged.connect(self.laser_to_show_changed)
        self._mw.ana_param_errorbars_CheckBox.stateChanged.connect(self.toggle_error_bars)
        self._mw.pulser_use_interleave_CheckBox.stateChanged.connect(self.pulse_generator_settings_changed)

        # connect spinbox changed signals
        self._mw.ana_param_num_laser_pulse_SpinBox.editingFinished.connect(self.measurement_sequence_settings_changed)
        self._mw.ana_param_record_length_SpinBox.editingFinished.connect(self.fast_counter_settings_changed)
        self._mw.time_param_ana_periode_DoubleSpinBox.editingFinished.connect(self.measurement_timer_changed)
        self._mw.ext_control_mw_freq_DoubleSpinBox.editingFinished.connect(self.ext_mw_params_changed)
        self._mw.ext_control_mw_power_DoubleSpinBox.editingFinished.connect(self.ext_mw_params_changed)
        self._mw.pulser_sample_freq_DSpinBox.editingFinished.connect(self.pulse_generator_settings_changed)
        self._mw.ana_param_x_axis_start_ScienDSpinBox.editingFinished.connect(self.measurement_sequence_settings_changed)
        self._mw.ana_param_x_axis_inc_ScienDSpinBox.editingFinished.connect(self.measurement_sequence_settings_changed)
        self._mw.extract_param_ana_window_start_SpinBox.editingFinished.connect(self.analysis_windows_changed)
        self._mw.extract_param_ana_window_width_SpinBox.editingFinished.connect(self.analysis_windows_changed)
        self._mw.extract_param_ref_window_start_SpinBox.editingFinished.connect(self.analysis_windows_changed)
        self._mw.extract_param_ref_window_width_SpinBox.editingFinished.connect(self.analysis_windows_changed)
        self._mw.conv_std_dev.valueChanged.connect(self.conv_std_dev_changed)

        # connect combobox changed signals
        self._mw.ana_param_fc_bins_ComboBox.currentIndexChanged.connect(self.fast_counter_settings_changed)
        #self._mw.second_plot_ComboBox.currentIndexChanged.connect(self.change_second_plot)
        self._mw.pulser_activation_config_ComboBox.currentIndexChanged.connect(self.pulse_generator_settings_changed)
        self._mw.laserpulses_ComboBox.currentIndexChanged.connect(self.laser_to_show_changed)

        # connect other widgets changed signals
        self.sig_start_line.sigPositionChanged.connect(self.analysis_windows_line_changed)
        self.sig_end_line.sigPositionChanged.connect(self.analysis_windows_line_changed)
        self.ref_start_line.sigPositionChanged.connect(self.analysis_windows_line_changed)
        self.ref_end_line.sigPositionChanged.connect(self.analysis_windows_line_changed)
        self._mw.slider_conv_std_dev.sliderMoved.connect(self.slider_conv_std_dev_changed)

        # apply hardware constraints
        self._analysis_apply_hardware_constraints()

        # initialize values
        self._pulsed_master_logic.request_measurement_init_values()
        return

    def _deactivate_analysis_ui(self, e):
        """ Disconnects the configuration for 'Analysis' Tab.

       @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        self.measurement_run_stop_clicked(False)

        self._statusVariables['ana_param_x_axis_defined_CheckBox'] = self._mw.ana_param_x_axis_defined_CheckBox.isChecked()
        self._statusVariables['ana_param_laserpulse_defined_CheckBox'] = self._mw.ana_param_laserpulse_defined_CheckBox.isChecked()
        self._statusVariables['ana_param_ignore_first_CheckBox'] = self._mw.ana_param_ignore_first_CheckBox.isChecked()
        self._statusVariables['ana_param_ignore_last_CheckBox'] = self._mw.ana_param_ignore_last_CheckBox.isChecked()
        self._statusVariables['ana_param_errorbars_CheckBox'] = self._mw.ana_param_errorbars_CheckBox.isChecked()
        self._statusVariables['second_plot_ComboBox_text'] = self._mw.second_plot_ComboBox.currentText()

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
        self._pulsed_master_logic.sigAnalysisWindowsUpdated.disconnect()
        self._pulsed_master_logic.sigAnalysisMethodUpdated.disconnect()
        self._mw.upload_ensemble_PushButton.clicked.disconnect()
        self._mw.load_ensemble_PushButton.clicked.disconnect()
        self._mw.upload_sequence_PushButton.clicked.disconnect()
        self._mw.load_sequence_PushButton.clicked.disconnect()
        self._mw.pulser_on_off_PushButton.clicked.disconnect()
        self._mw.clear_device_PushButton.clicked.disconnect()
        self._mw.fit_param_PushButton.clicked.disconnect()
        self._mw.action_run_stop.triggered.disconnect()
        self._mw.action_continue_pause.triggered.disconnect()
        self._mw.action_pull_data.triggered.disconnect()
        self._mw.action_save.triggered.disconnect()
        self._mw.action_Settings_Analysis.triggered.disconnect()
        self._mw.ext_control_use_mw_CheckBox.stateChanged.disconnect()
        self._mw.ana_param_x_axis_defined_CheckBox.stateChanged.disconnect()
        self._mw.ana_param_laserpulse_defined_CheckBox.stateChanged.disconnect()
        self._mw.ana_param_alternating_CheckBox.stateChanged.disconnect()
        self._mw.ana_param_ignore_first_CheckBox.stateChanged.disconnect()
        self._mw.ana_param_ignore_last_CheckBox.stateChanged.disconnect()
        self._mw.laserpulses_display_raw_CheckBox.stateChanged.disconnect()
        self._mw.ana_param_errorbars_CheckBox.stateChanged.disconnect()
        self._mw.pulser_use_interleave_CheckBox.stateChanged.disconnect()
        self._mw.ana_param_num_laser_pulse_SpinBox.editingFinished.disconnect()
        self._mw.ana_param_record_length_SpinBox.editingFinished.disconnect()
        self._mw.time_param_ana_periode_DoubleSpinBox.editingFinished.disconnect()
        self._mw.ext_control_mw_freq_DoubleSpinBox.editingFinished.disconnect()
        self._mw.ext_control_mw_power_DoubleSpinBox.editingFinished.disconnect()
        self._mw.pulser_sample_freq_DSpinBox.editingFinished.disconnect()
        self._mw.ana_param_x_axis_start_ScienDSpinBox.editingFinished.disconnect()
        self._mw.ana_param_x_axis_inc_ScienDSpinBox.editingFinished.disconnect()
        self._mw.extract_param_ana_window_start_SpinBox.editingFinished.disconnect()
        self._mw.extract_param_ana_window_width_SpinBox.editingFinished.disconnect()
        self._mw.extract_param_ref_window_start_SpinBox.editingFinished.disconnect()
        self._mw.extract_param_ref_window_width_SpinBox.editingFinished.disconnect()
        self._mw.conv_std_dev.valueChanged.disconnect()
        self._mw.ana_param_fc_bins_ComboBox.currentIndexChanged.disconnect()
        # self._mw.second_plot_ComboBox.currentIndexChanged.disconnect()
        self._mw.pulser_activation_config_ComboBox.currentIndexChanged.disconnect()
        self._mw.laserpulses_ComboBox.currentIndexChanged.disconnect()
        self.sig_start_line.sigPositionChanged.disconnect()
        self.sig_end_line.sigPositionChanged.disconnect()
        self.ref_start_line.sigPositionChanged.disconnect()
        self.ref_end_line.sigPositionChanged.disconnect()
        self._mw.slider_conv_std_dev.sliderMoved.disconnect()
        return

    def _analysis_apply_hardware_constraints(self):
        """
        Retrieve the constraints from pulser and fast counter hardware and apply these constraints
        to the analysis tab GUI elements.
        """
        # block signals
        self._mw.pulser_activation_config_ComboBox.blockSignals(True)
        self._mw.ana_param_fc_bins_ComboBox.blockSignals(True)
        # apply constraints
        pulser_constr, fastcounter_constr = self._pulsed_master_logic.get_hardware_constraints()
        sample_min = pulser_constr['sample_rate']['min']
        sample_max = pulser_constr['sample_rate']['max']
        sample_step = pulser_constr['sample_rate']['step']
        self._mw.pulser_sample_freq_DSpinBox.setMinimum(sample_min)
        self._mw.pulser_sample_freq_DSpinBox.setMaximum(sample_max)
        self._mw.pulser_sample_freq_DSpinBox.setSingleStep(sample_step)
        self._mw.pulser_activation_config_ComboBox.clear()
        self._mw.pulser_activation_config_ComboBox.addItems(list(pulser_constr['activation_config']))
        self._mw.ana_param_fc_bins_ComboBox.clear()
        for binwidth in fastcounter_constr['hardware_binwidth_list']:
            self._mw.ana_param_fc_bins_ComboBox.addItem(str(binwidth))
        # unblock signals
        self._mw.pulser_activation_config_ComboBox.blockSignals(False)
        self._mw.ana_param_fc_bins_ComboBox.blockSignals(False)
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

    #ToDo: I think that is not really working yet. Yeap, true....
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
        self._mw.pulser_on_off_PushButton.blockSignals(True)

        # Enable/Disable widgets
        if is_running:
            self._mw.ext_control_use_mw_CheckBox.setEnabled(False)
            self._mw.ext_control_mw_freq_DoubleSpinBox.setEnabled(False)
            self._mw.ext_control_mw_power_DoubleSpinBox.setEnabled(False)
            self._mw.pulser_sample_freq_DSpinBox.setEnabled(False)
            self._mw.pulser_activation_config_ComboBox.setEnabled(False)
            self._mw.ana_param_fc_bins_ComboBox.setEnabled(False)
            self._mw.ana_param_laserpulse_defined_CheckBox.setEnabled(False)
            self._mw.ana_param_num_laser_pulse_SpinBox.setEnabled(False)
            self._mw.ana_param_record_length_SpinBox.setEnabled(False)
            self._mw.ana_param_ignore_first_CheckBox.setEnabled(False)
            self._mw.ana_param_ignore_last_CheckBox.setEnabled(False)
            self._mw.ana_param_alternating_CheckBox.setEnabled(False)
            self._mw.ana_param_x_axis_defined_CheckBox.setEnabled(False)
            self._mw.ana_param_x_axis_start_ScienDSpinBox.setEnabled(False)
            self._mw.ana_param_x_axis_inc_ScienDSpinBox.setEnabled(False)
            self._mw.load_ensemble_PushButton.setEnabled(False)
            self._mw.load_sequence_PushButton.setEnabled(False)
            self._mw.pulser_on_off_PushButton.setEnabled(False)
            self._mw.action_continue_pause.setEnabled(True)
            self._mw.action_pull_data.setEnabled(True)
            if not self._mw.action_run_stop.isChecked():
                self._mw.action_run_stop.toggle()
            if not self._mw.pulser_on_off_PushButton.isChecked():
                self._mw.pulser_on_off_PushButton.setText('Pulser OFF')
                self._mw.pulser_on_off_PushButton.toggle()
        else:
            self._mw.ext_control_use_mw_CheckBox.setEnabled(True)
            self._mw.ext_control_mw_freq_DoubleSpinBox.setEnabled(True)
            self._mw.ext_control_mw_power_DoubleSpinBox.setEnabled(True)
            self._mw.pulser_sample_freq_DSpinBox.setEnabled(True)
            self._mw.pulser_activation_config_ComboBox.setEnabled(True)
            self._mw.ana_param_fc_bins_ComboBox.setEnabled(True)
            self._mw.ana_param_laserpulse_defined_CheckBox.setEnabled(True)
            self._mw.ana_param_num_laser_pulse_SpinBox.setEnabled(True)
            self._mw.ana_param_record_length_SpinBox.setEnabled(True)
            self._mw.ana_param_ignore_first_CheckBox.setEnabled(True)
            self._mw.ana_param_ignore_last_CheckBox.setEnabled(True)
            self._mw.ana_param_alternating_CheckBox.setEnabled(True)
            self._mw.ana_param_x_axis_defined_CheckBox.setEnabled(True)
            self._mw.ana_param_x_axis_start_ScienDSpinBox.setEnabled(True)
            self._mw.ana_param_x_axis_inc_ScienDSpinBox.setEnabled(True)
            self._mw.load_ensemble_PushButton.setEnabled(True)
            self._mw.load_sequence_PushButton.setEnabled(True)
            self._mw.pulser_on_off_PushButton.setEnabled(True)
            self._mw.action_continue_pause.setEnabled(False)
            self._mw.action_pull_data.setEnabled(False)
            if self._mw.action_run_stop.isChecked():
                self._mw.action_run_stop.toggle()
            if self._mw.pulser_on_off_PushButton.isChecked():
                self._mw.pulser_on_off_PushButton.setText('Pulser ON')
                self._mw.pulser_on_off_PushButton.toggle()

        if is_paused:
            if not self._mw.action_continue_pause.isChecked():
                self._mw.action_continue_pause.toggle()
            if self._mw.pulser_on_off_PushButton.isChecked():
                self._mw.pulser_on_off_PushButton.setText('Pulser ON')
                self._mw.pulser_on_off_PushButton.toggle()
        else:
            if self._mw.action_continue_pause.isChecked():
                self._mw.action_continue_pause.toggle()
            if not self._mw.pulser_on_off_PushButton.isChecked():
                self._mw.pulser_on_off_PushButton.setText('Pulser OFF')
                self._mw.pulser_on_off_PushButton.toggle()

        # unblock signals
        self._mw.action_run_stop.blockSignals(False)
        self._mw.action_continue_pause.blockSignals(False)
        self._mw.pulser_on_off_PushButton.blockSignals(False)
        return

    def pull_data_clicked(self):
        """ Pulls and analysis the data when the 'action_pull_data'-button is clicked. """
        self._pulsed_master_logic.manually_pull_data()
        return

    def signal_data_updated(self, x_data, y_signal_data, y2_signal_data, y_error_data, y2_error_data):
        """

        @param x_data:
        @param y_signal_data:
        @param y2_signal_data:
        @param y_error_data:
        @param y2_error_data:
        @return:
        """
        show_error_bars = self._mw.ana_param_errorbars_CheckBox.isChecked()
        is_alternating = self._mw.ana_param_alternating_CheckBox.isChecked()
        if show_error_bars:
            beamwidth = np.inf
            for i in range(len(x_data) - 1):
                width = x_data[i + 1] - x_data[i]
                width = width / 3
                if width <= beamwidth:
                    beamwidth = width
            # create ErrorBarItems
            self.signal_image_error_bars.setData(x=x_data, y=y_signal_data, top=y_error_data,
                                                 bottom=y_error_data, beam=beamwidth)
            if is_alternating:
                self.signal_image_error_bars2.setData(x=x_data, y=y2_signal_data, top=y2_error_data,
                                                      bottom=y2_error_data, beam=beamwidth)
            if not self.signal_image_error_bars in self._mw.pulse_analysis_PlotWidget.items():
                self._mw.pulse_analysis_PlotWidget.addItem(self.signal_image_error_bars)
                if is_alternating:
                    self._mw.pulse_analysis_PlotWidget.addItem(self.signal_image_error_bars2)
        else:
            if self.signal_image_error_bars in self._mw.pulse_analysis_PlotWidget.items():
                self._mw.pulse_analysis_PlotWidget.removeItem(self.signal_image_error_bars)
                if is_alternating:
                    self._mw.pulse_analysis_PlotWidget.addItem(self.signal_image_error_bars2)

        # dealing with the actual signal
        self.signal_image.setData(x=x_data, y=y_signal_data)
        if is_alternating:
            self.signal_image2.setData(x=x_data, y=y2_signal_data)

        # dealing with the error plot
        self.measuring_error_image.setData(x=x_data, y=y_error_data)
        if is_alternating:
            self.measuring_error_image2.setData(x=x_data, y=y2_error_data)
        return

    # FIXME: Implement that
    def save_clicked(self):
        """Saves the current data"""
        pass

    def fit_clicked(self):
        """Fits the current data"""
        current_fit_function = self._mw.fit_param_fit_func_ComboBox.currentText()
        self._pulsed_master_logic.do_fit(current_fit_function)
        return

    def fit_data_updated(self, fit_function, fit_data_x, fit_data_y, param_dict, result_dict):
        """

        @param fit_function:
        @param fit_data_x:
        @param fit_data_y:
        @param param_dict:
        @param result_dict:
        @return:
        """
        # block signals
        self._mw.fit_param_fit_func_ComboBox.blockSignals(True)
        # set widgets
        self._mw.fit_param_results_TextBrowser.clear()
        fit_text = units.create_formatted_output(param_dict)
        self._mw.fit_param_results_TextBrowser.setPlainText(fit_text)
        self.fit_image.setData(x=fit_data_x, y=fit_data_y)
        if fit_function == 'No Fit' and self.fit_image in self._mw.pulse_analysis_PlotWidget.items():
            self._mw.pulse_analysis_PlotWidget.removeItem(self.fit_image)
        elif fit_function != 'No Fit' and self.fit_image not in self._mw.pulse_analysis_PlotWidget.items():
            self._mw.pulse_analysis_PlotWidget.addItem(self.fit_image)
        if self._mw.fit_param_fit_func_ComboBox.currentText() != fit_function:
            index = self._mw.fit_param_fit_func_ComboBox.findText(fit_function)
            if index >= 0:
                self._mw.fit_param_fit_func_ComboBox.setCurrentIndex(index)
        # unblock signals
        self._mw.fit_param_fit_func_ComboBox.blockSignals(False)
        return

    def elapsed_time_updated(self, elapsed_time, elapsed_time_str):
        """
        Refreshes the elapsed time and sweeps of the measurement.

        @param elapsed_time:
        @param elapsed_time_str:
        @return:
        """
        # block signals
        self._mw.time_param_elapsed_time_LineEdit.blockSignals(True)
        # Set widgets
        self._mw.time_param_elapsed_time_LineEdit.setText(elapsed_time_str)
        # unblock signals
        self._mw.time_param_elapsed_time_LineEdit.blockSignals(True)
        return

    def ext_mw_params_changed(self):
        """ Shows or hides input widgets which are necessary if an external mw is turned on"""
        use_ext_microwave = self._mw.ext_control_use_mw_CheckBox.isChecked()
        microwave_freq = self._mw.ext_control_mw_freq_DoubleSpinBox.value()
        microwave_power = self._mw.ext_control_mw_power_DoubleSpinBox.value()
        if use_ext_microwave:
            self._mw.ext_control_mw_freq_Label.setEnabled(True)
            self._mw.ext_control_mw_freq_DoubleSpinBox.setEnabled(True)
            self._mw.ext_control_mw_power_Label.setEnabled(True)
            self._mw.ext_control_mw_power_DoubleSpinBox.setEnabled(True)

            self._mw.ext_control_mw_freq_Label.setVisible(True)
            self._mw.ext_control_mw_freq_DoubleSpinBox.setVisible(True)
            self._mw.ext_control_mw_power_Label.setVisible(True)
            self._mw.ext_control_mw_power_DoubleSpinBox.setVisible(True)
        else:
            self._mw.ext_control_mw_freq_Label.setEnabled(False)
            self._mw.ext_control_mw_freq_DoubleSpinBox.setEnabled(False)
            self._mw.ext_control_mw_power_Label.setEnabled(False)
            self._mw.ext_control_mw_power_DoubleSpinBox.setEnabled(False)

            self._mw.ext_control_mw_freq_Label.setVisible(False)
            self._mw.ext_control_mw_freq_DoubleSpinBox.setVisible(False)
            self._mw.ext_control_mw_power_Label.setVisible(False)
            self._mw.ext_control_mw_power_DoubleSpinBox.setVisible(False)

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
        # block signals
        self._mw.ext_control_mw_freq_DoubleSpinBox.blockSignals(True)
        self._mw.ext_control_mw_power_DoubleSpinBox.blockSignals(True)
        self._mw.ext_control_use_mw_CheckBox.blockSignals(True)
        # set widgets
        self._mw.ext_control_mw_freq_DoubleSpinBox.setValue(frequency)
        self._mw.ext_control_mw_power_DoubleSpinBox.setValue(power)
        self._mw.ext_control_use_mw_CheckBox.setChecked(use_ext_microwave)
        # set visibility
        if use_ext_microwave:
            self._mw.ext_control_mw_freq_Label.setEnabled(True)
            self._mw.ext_control_mw_freq_DoubleSpinBox.setEnabled(True)
            self._mw.ext_control_mw_power_Label.setEnabled(True)
            self._mw.ext_control_mw_power_DoubleSpinBox.setEnabled(True)

            self._mw.ext_control_mw_freq_Label.setVisible(True)
            self._mw.ext_control_mw_freq_DoubleSpinBox.setVisible(True)
            self._mw.ext_control_mw_power_Label.setVisible(True)
            self._mw.ext_control_mw_power_DoubleSpinBox.setVisible(True)
        else:
            self._mw.ext_control_mw_freq_Label.setEnabled(False)
            self._mw.ext_control_mw_freq_DoubleSpinBox.setEnabled(False)
            self._mw.ext_control_mw_power_Label.setEnabled(False)
            self._mw.ext_control_mw_power_DoubleSpinBox.setEnabled(False)

            self._mw.ext_control_mw_freq_Label.setVisible(False)
            self._mw.ext_control_mw_freq_DoubleSpinBox.setVisible(False)
            self._mw.ext_control_mw_power_Label.setVisible(False)
            self._mw.ext_control_mw_power_DoubleSpinBox.setVisible(False)
        # unblock signals
        self._mw.ext_control_mw_freq_DoubleSpinBox.blockSignals(False)
        self._mw.ext_control_mw_power_DoubleSpinBox.blockSignals(False)
        self._mw.ext_control_use_mw_CheckBox.blockSignals(False)
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
        # FIXME: Properly implement amplitude and interleave
        sample_rate_hz = self._mw.pulser_sample_freq_DSpinBox.value()
        activation_config_name = self._mw.pulser_activation_config_ComboBox.currentText()
        analogue_amplitude, dummy = self._pulsed_master_logic._measurement_logic._pulse_generator_device.get_analog_level()
        interleave_on = self._mw.pulser_use_interleave_CheckBox.isChecked()
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
        self._mw.pulser_sample_freq_DSpinBox.blockSignals(True)
        self._mw.pulser_activation_config_ComboBox.blockSignals(True)
        self._mw.pulser_activation_config_LineEdit.blockSignals(True)
        self._mw.pulser_use_interleave_CheckBox.blockSignals(True)
        # Set widgets
        # FIXME: Properly implement amplitude and interleave
        self._mw.pulser_sample_freq_DSpinBox.setValue(sample_rate_hz)
        index = self._mw.pulser_activation_config_ComboBox.findText(activation_config_name)
        self._mw.pulser_activation_config_ComboBox.setCurrentIndex(index)
        config_display_str = ''
        for channel in activation_config:
            config_display_str += channel + ' | '
        config_display_str = config_display_str[:-3]
        self._mw.pulser_activation_config_LineEdit.setText(config_display_str)
        self._mw.pulser_use_interleave_CheckBox.setChecked(interleave_on)
        # unblock signals
        self._mw.pulser_sample_freq_DSpinBox.blockSignals(False)
        self._mw.pulser_activation_config_ComboBox.blockSignals(False)
        self._mw.pulser_activation_config_LineEdit.blockSignals(False)
        self._mw.pulser_use_interleave_CheckBox.blockSignals(False)
        return

    def fast_counter_settings_changed(self):
        """

        @return:
        """
        record_length_s = self._mw.ana_param_record_length_SpinBox.value()
        bin_width_s = float(self._mw.ana_param_fc_bins_ComboBox.currentText())
        print('fc binwidth is: {0}'.format(bin_width_s))
        self._pulsed_master_logic.fast_counter_settings_changed(bin_width_s, record_length_s)
        return

    def fast_counter_settings_updated(self, bin_width_s, record_length_s):
        """

        @param bin_width_s:
        @param record_length_s:
        @return:
        """
        # block signals
        self._mw.ana_param_record_length_SpinBox.blockSignals(True)
        self._mw.ana_param_fc_bins_ComboBox.blockSignals(True)
        # set widgets
        self._mw.ana_param_record_length_SpinBox.setValue(record_length_s)
        index = self._mw.ana_param_fc_bins_ComboBox.findText(str(bin_width_s))
        self._mw.ana_param_fc_bins_ComboBox.setCurrentIndex(index)
        # unblock signals
        self._mw.ana_param_record_length_SpinBox.blockSignals(False)
        self._mw.ana_param_fc_bins_ComboBox.blockSignals(False)
        return

    def measurement_sequence_settings_changed(self):
        """

        @return:
        """
        laser_ignore_list = []
        if self._mw.ana_param_ignore_first_CheckBox.isChecked():
            laser_ignore_list.append(0)
        if self._mw.ana_param_ignore_last_CheckBox.isChecked():
            laser_ignore_list.append(-1)
        alternating = self._mw.ana_param_alternating_CheckBox.isChecked()
        num_of_lasers = self._mw.ana_param_num_laser_pulse_SpinBox.value()
        xaxis_start = self._mw.ana_param_x_axis_start_ScienDSpinBox.value()
        print('GUI measurement settings changed: ', xaxis_start)
        xaxis_incr = self._mw.ana_param_x_axis_inc_ScienDSpinBox.value()
        laser_trigger_delay = self._as.ana_param_lasertrigger_delay_ScienDSpinBox.value()
        # FIXME: properly implement sequence_length_s
        sequence_length_s = self._pulsed_master_logic._measurement_logic.sequence_length_s
        num_of_ticks = num_of_lasers - len(laser_ignore_list)
        if alternating:
            num_of_ticks //= 2
        measurement_ticks = np.arange(xaxis_start,
                                      xaxis_start + (xaxis_incr * num_of_ticks) - (xaxis_incr / 2),
                                      xaxis_incr)

        self._pulsed_master_logic.measurement_sequence_settings_changed(measurement_ticks,
                                                                        num_of_lasers,
                                                                        sequence_length_s,
                                                                        laser_ignore_list,
                                                                        alternating,
                                                                        laser_trigger_delay)
        return

    def measurement_sequence_settings_updated(self, measurement_ticks, number_of_lasers,
                                              sequence_length_s, laser_ignore_list, alternating,
                                              laser_trigger_delay):
        """

        @param measurement_ticks:
        @param number_of_lasers:
        @param sequence_length_s:
        @param laser_ignore_list:
        @param alternating:
        @param laser_trigger_delay:
        @return:
        """
        print('GUI measurement settings updated: ', measurement_ticks[0])

        # block signals
        self._mw.ana_param_ignore_first_CheckBox.blockSignals(True)
        self._mw.ana_param_ignore_last_CheckBox.blockSignals(True)
        self._mw.ana_param_alternating_CheckBox.blockSignals(True)
        self._mw.ana_param_num_laser_pulse_SpinBox.blockSignals(True)
        self._mw.ana_param_x_axis_start_ScienDSpinBox.blockSignals(True)
        self._mw.ana_param_x_axis_inc_ScienDSpinBox.blockSignals(True)
        self._as.ana_param_lasertrigger_delay_ScienDSpinBox.blockSignals(True)
        self._mw.laserpulses_ComboBox.blockSignals(True)
        # set widgets
        self._mw.ana_param_ignore_first_CheckBox.setChecked(0 in laser_ignore_list)
        self._mw.ana_param_ignore_last_CheckBox.setChecked(-1 in laser_ignore_list)
        self._mw.ana_param_alternating_CheckBox.setChecked(alternating)
        self._mw.ana_param_num_laser_pulse_SpinBox.setValue(number_of_lasers)
        self._as.ana_param_lasertrigger_delay_ScienDSpinBox.setValue(laser_trigger_delay)
        self._mw.ana_param_x_axis_start_ScienDSpinBox.setValue(measurement_ticks[0])
        self._mw.ana_param_x_axis_inc_ScienDSpinBox.setValue(
            (measurement_ticks[-1] - measurement_ticks[0]) / (len(measurement_ticks)-1))
        self._mw.laserpulses_ComboBox.addItems([str(i) for i in range(number_of_lasers+1)])
        # change plots accordingly
        if alternating:
            if self.signal_image2 not in self._mw.pulse_analysis_PlotWidget.items():
                self._mw.pulse_analysis_PlotWidget.addItem(self.signal_image2)
            if self.signal_image_error_bars in self._mw.pulse_analysis_PlotWidget.items() and self.signal_image_error_bars2 not in self._mw.pulse_analysis_PlotWidget.items():
                self._mw.pulse_analysis_PlotWidget.addItem(self.signal_image_error_bars2)
            if self.measuring_error_image2 not in self._mw.measuring_error_PlotWidget.items():
                self._mw.measuring_error_PlotWidget.addItem(self.measuring_error_image2)
        else:
            if self.signal_image2 in self._mw.pulse_analysis_PlotWidget.items():
                self._mw.pulse_analysis_PlotWidget.removeItem(self.signal_image2)
            if self.signal_image_error_bars2 in self._mw.pulse_analysis_PlotWidget.items():
                self._mw.pulse_analysis_PlotWidget.removeItem(self.signal_image_error_bars2)
            if self.measuring_error_image2 in self._mw.measuring_error_PlotWidget.items():
                self._mw.measuring_error_PlotWidget.removeItem(self.measuring_error_image2)
        # unblock signals
        self._mw.ana_param_ignore_first_CheckBox.blockSignals(False)
        self._mw.ana_param_ignore_last_CheckBox.blockSignals(False)
        self._mw.ana_param_alternating_CheckBox.blockSignals(False)
        self._mw.ana_param_num_laser_pulse_SpinBox.blockSignals(False)
        self._mw.ana_param_x_axis_start_ScienDSpinBox.blockSignals(False)
        self._mw.ana_param_x_axis_inc_ScienDSpinBox.blockSignals(False)
        self._as.ana_param_lasertrigger_delay_ScienDSpinBox.blockSignals(False)
        self._mw.laserpulses_ComboBox.blockSignals(False)
        return

    def toggle_laser_xaxis_editor(self):
        """ Shows or hides input widgets which are necessary if the x axis id defined or not."""
        if self._mw.ana_param_x_axis_defined_CheckBox.isChecked():
            self._mw.ana_param_x_axis_start_Label.setVisible(True)
            self._mw.ana_param_x_axis_start_ScienDSpinBox.setVisible(True)
            self._mw.ana_param_x_axis_inc_Label.setVisible(True)
            self._mw.ana_param_x_axis_inc_ScienDSpinBox.setVisible(True)
            self._mw.ana_param_x_axis_start_ScienDSpinBox.setEnabled(True)
            self._mw.ana_param_x_axis_inc_ScienDSpinBox.setEnabled(True)
        else:
            self._mw.ana_param_x_axis_start_Label.setVisible(False)
            self._mw.ana_param_x_axis_start_ScienDSpinBox.setVisible(False)
            self._mw.ana_param_x_axis_inc_Label.setVisible(False)
            self._mw.ana_param_x_axis_inc_ScienDSpinBox.setVisible(False)
            self._mw.ana_param_x_axis_start_ScienDSpinBox.setEnabled(False)
            self._mw.ana_param_x_axis_inc_ScienDSpinBox.setEnabled(False)

        if self._mw.ana_param_laserpulse_defined_CheckBox.isChecked():
            self._mw.ana_param_num_laserpulses_Label.setVisible(True)
            self._mw.ana_param_num_laser_pulse_SpinBox.setVisible(True)
            self._mw.ana_param_record_length_Label.setVisible(True)
            self._mw.ana_param_record_length_SpinBox.setVisible(True)
            self._mw.ana_param_num_laser_pulse_SpinBox.setEnabled(True)
            self._mw.ana_param_record_length_SpinBox.setEnabled(True)
        else:
            self._mw.ana_param_num_laserpulses_Label.setVisible(False)
            self._mw.ana_param_num_laser_pulse_SpinBox.setVisible(False)
            self._mw.ana_param_record_length_Label.setVisible(False)
            self._mw.ana_param_record_length_SpinBox.setVisible(False)
            self._mw.ana_param_num_laser_pulse_SpinBox.setEnabled(False)
            self._mw.ana_param_record_length_SpinBox.setEnabled(False)
        return

    def toggle_error_bars(self):
        """

        @return:
        """
        show_bars = self._mw.ana_param_errorbars_CheckBox.isChecked()
        is_alternating = self.signal_image2 in self._mw.pulse_analysis_PlotWidget.items()
        if show_bars:
            if self.signal_image_error_bars not in self._mw.pulse_analysis_PlotWidget.items():
                self._mw.pulse_analysis_PlotWidget.addItem(self.signal_image_error_bars)
            if is_alternating and self.signal_image_error_bars2 not in self._mw.pulse_analysis_PlotWidget.items():
                self._mw.pulse_analysis_PlotWidget.addItem(self.signal_image_error_bars2)
        else:
            if self.signal_image_error_bars in self._mw.pulse_analysis_PlotWidget.items():
                self._mw.pulse_analysis_PlotWidget.removeItem(self.signal_image_error_bars)
            if is_alternating and self.signal_image_error_bars2 in self._mw.pulse_analysis_PlotWidget.items():
                self._mw.pulse_analysis_PlotWidget.removeItem(self.signal_image_error_bars2)
        return

    # def change_second_plot(self):
    #     """ This method handles the second plot"""
    #     if self._mw.second_plot_ComboBox.currentText()=='None':
    #         self._mw.second_plot_GroupBox.setVisible(False)
    #     else:
    #         self._mw.second_plot_GroupBox.setVisible(True)
    #
    #         # Here FFT is seperated from the other option. The reason for that
    #         # is preventing of code doubling
    #         if self._mw.second_plot_ComboBox.currentText() == 'FFT':
    #             fft_x, fft_y = self._pulsed_meas_logic.compute_fft()
    #             self.second_plot_image.setData(fft_x, fft_y)
    #             self._mw.pulse_analysis_second_PlotWidget.setLogMode(x=False, y=False)
    #
    #             self._mw.pulse_analysis_second_PlotWidget.setLabel(axis='bottom',
    #                                                                text=self._as.ana_param_second_plot_x_axis_name_LineEdit.text(),
    #                                                                units=self._as.ana_param_second_plot_x_axis_unit_LineEdit.text())
    #             self._mw.pulse_analysis_second_PlotWidget.setLabel(axis='left',
    #                                                                text=self._as.ana_param_second_plot_y_axis_name_LineEdit.text(),
    #                                                                units=self._as.ana_param_second_plot_y_axis_unit_LineEdit.text())
    #
    #         else:
    #             #FIXME: Is not working when there is a 0 in the values, therefore ignoring the first measurment point
    #             self.second_plot_image.setData(self._pulsed_meas_logic.signal_plot_x[1:], self._pulsed_meas_logic.signal_plot_y[1:])
    #
    #             if self._as.ana_param_second_plot_x_axis_name_LineEdit.text()== '':
    #                 self._mw.pulse_analysis_second_PlotWidget.setLabel(axis='left',
    #                                                                    text=self._as.ana_param_y_axis_name_LineEdit.text(),
    #                                                                    units=self._as.ana_param_y_axis_unit_LineEdit.text())
    #                 self._mw.pulse_analysis_second_PlotWidget.setLabel(axis='bottom',
    #                                                                    text=self._as.ana_param_x_axis_name_LineEdit.text(),
    #                                                                    units=self._as.ana_param_x_axis_unit_LineEdit.text())
    #
    #             else:
    #                 self._mw.pulse_analysis_second_PlotWidget.setLabel(axis='bottom',
    #                                                                    text=self._as.ana_param_second_plot_x_axis_name_LineEdit.text(),
    #                                                                    units=self._as.ana_param_second_plot_x_axis_unit_LineEdit.text())
    #                 self._mw.pulse_analysis_second_PlotWidget.setLabel(axis='left',
    #                                                                    text=self._as.ana_param_second_plot_y_axis_name_LineEdit.text(),
    #                                                                    units=self._as.ana_param_second_plot_y_axis_unit_LineEdit.text())
    #
    #             if self._mw.second_plot_ComboBox.currentText() == 'unchanged data':
    #                 self._mw.pulse_analysis_second_PlotWidget.setLogMode(x=False, y=False)
    #
    #             elif self._mw.second_plot_ComboBox.currentText() == 'Log(x)':
    #                 self._mw.pulse_analysis_second_PlotWidget.setLogMode(x=True, y=False)
    #
    #             elif self._mw.second_plot_ComboBox.currentText() == 'Log(y)':
    #                 self._mw.pulse_analysis_second_PlotWidget.setLogMode(x=False,y=True)
    #
    #             elif self._mw.second_plot_ComboBox.currentText() == 'Log(x)&Log(y)':
    #                 self._mw.pulse_analysis_second_PlotWidget.setLogMode(x=True, y=True)

    def measurement_timer_changed(self):
        """ This method handles the analysis timing"""
        timer_interval = self._mw.time_param_ana_periode_DoubleSpinBox.value()
        self._pulsed_master_logic.analysis_interval_changed(timer_interval)
        return

    def measurement_timer_updated(self, timer_interval_s):
        """

        @param timer_interval_s:
        @return:
        """
        # block signals
        self._mw.time_param_ana_periode_DoubleSpinBox.blockSignals(True)
        # set widget
        self._mw.time_param_ana_periode_DoubleSpinBox.setValue(timer_interval_s)
        # unblock signals
        self._mw.time_param_ana_periode_DoubleSpinBox.blockSignals(False)
        return

    def conv_std_dev_changed(self):
        """
        Uodate new value of standard deviation of gaussian filter
        """
        # block signals
        self._mw.slider_conv_std_dev.blockSignals(True)
        # set widgets
        std_dev = self._mw.conv_std_dev.value()
        self._mw.slider_conv_std_dev.setValue(std_dev)
        # unblock signals
        self._mw.slider_conv_std_dev.blockSignals(False)

        self._pulsed_master_logic.analysis_method_changed(std_dev)
        return

    def slider_conv_std_dev_changed(self):
        """
        Uodate new value of standard deviation of gaussian filter
        from slider
        """
        # block signals
        self._mw.conv_std_dev.blockSignals(True)
        # set widgets
        std_dev = self._mw.slider_conv_std_dev.value()
        self._mw.conv_std_dev.setValue(std_dev)
        # unblock signals
        self._mw.conv_std_dev.blockSignals(False)

        self._pulsed_master_logic.analysis_method_changed(std_dev)
        return

    def analysis_method_updated(self, gaussfilt_std_dev):
        """

        @param gaussfilt_std_dev:
        @return:
        """
        # block signals
        self._mw.slider_conv_std_dev.blockSignals(True)
        self._mw.conv_std_dev.blockSignals(True)
        # set widgets
        self._mw.slider_conv_std_dev.setValue(gaussfilt_std_dev)
        self._mw.conv_std_dev.setValue(gaussfilt_std_dev)
        # unblock signals
        self._mw.slider_conv_std_dev.blockSignals(False)
        self._mw.conv_std_dev.blockSignals(False)
        return

    def analysis_windows_changed(self):
        """

        @return:
        """
        # block signals
        self.sig_start_line.blockSignals(True)
        self.sig_end_line.blockSignals(True)
        self.ref_start_line.blockSignals(True)
        self.ref_end_line.blockSignals(True)
        # get data
        sig_start = self._mw.extract_param_ana_window_start_SpinBox.value()
        sig_length = self._mw.extract_param_ana_window_width_SpinBox.value()
        ref_start = self._mw.extract_param_ref_window_start_SpinBox.value()
        ref_length = self._mw.extract_param_ref_window_width_SpinBox.value()
        # update plots
        self.sig_start_line.setValue(sig_start)
        self.sig_end_line.setValue(sig_start + sig_length)
        self.ref_start_line.setValue(ref_start)
        self.ref_end_line.setValue(ref_start + ref_length)
        # unblock signals
        self.sig_start_line.blockSignals(False)
        self.sig_end_line.blockSignals(False)
        self.ref_start_line.blockSignals(False)
        self.ref_end_line.blockSignals(False)

        self._pulsed_master_logic.analysis_windows_changed(sig_start, sig_length, ref_start,
                                                           ref_length)
        return

    def analysis_windows_line_changed(self):
        """

        @return:
        """
        # block signals
        self._mw.extract_param_ana_window_start_SpinBox.blockSignals(True)
        self._mw.extract_param_ana_window_width_SpinBox.blockSignals(True)
        self._mw.extract_param_ref_window_start_SpinBox.blockSignals(True)
        self._mw.extract_param_ref_window_width_SpinBox.blockSignals(True)
        # get data
        sig_start = self.sig_start_line.value()
        sig_length = self.sig_end_line.value() - sig_start
        ref_start = self.ref_start_line.value()
        ref_length = self.ref_end_line.value() - ref_start
        # set widgets
        self._mw.extract_param_ana_window_start_SpinBox.setValue(sig_start)
        self._mw.extract_param_ana_window_width_SpinBox.setValue(sig_length)
        self._mw.extract_param_ref_window_start_SpinBox.setValue(ref_start)
        self._mw.extract_param_ref_window_width_SpinBox.setValue(ref_length)
        # unblock signals
        self._mw.extract_param_ana_window_start_SpinBox.blockSignals(False)
        self._mw.extract_param_ana_window_width_SpinBox.blockSignals(False)
        self._mw.extract_param_ref_window_start_SpinBox.blockSignals(False)
        self._mw.extract_param_ref_window_width_SpinBox.blockSignals(False)
        return

    def analysis_windows_updated(self, sig_start, sig_length, ref_start, ref_length):
        """

        @param sig_start:
        @param sig_length:
        @param ref_start:
        @param ref_length:
        @return:
        """
        # block signals
        self._mw.extract_param_ana_window_start_SpinBox.blockSignals(True)
        self._mw.extract_param_ana_window_width_SpinBox.blockSignals(True)
        self._mw.extract_param_ref_window_start_SpinBox.blockSignals(True)
        self._mw.extract_param_ref_window_width_SpinBox.blockSignals(True)
        # set widgets
        self._mw.extract_param_ana_window_start_SpinBox.setValue(sig_start)
        self._mw.extract_param_ana_window_width_SpinBox.setValue(sig_length)
        self._mw.extract_param_ref_window_start_SpinBox.setValue(ref_start)
        self._mw.extract_param_ref_window_width_SpinBox.setValue(ref_length)
        # update plots
        self.sig_start_line.setValue(sig_start)
        self.sig_end_line.setValue(sig_start + sig_length)
        self.ref_start_line.setValue(ref_start)
        self.ref_end_line.setValue(ref_start + ref_length)
        # unblock signals
        self._mw.extract_param_ana_window_start_SpinBox.blockSignals(False)
        self._mw.extract_param_ana_window_width_SpinBox.blockSignals(False)
        self._mw.extract_param_ref_window_start_SpinBox.blockSignals(False)
        self._mw.extract_param_ref_window_width_SpinBox.blockSignals(False)
        return

    def laser_to_show_changed(self):
        """

        @return:
        """
        current_laser = self._mw.laserpulses_ComboBox.currentText()
        show_raw_data = self._mw.laserpulses_display_raw_CheckBox.isChecked()
        print(current_laser)
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
        self._mw.laserpulses_ComboBox.blockSignals(True)
        self._mw.laserpulses_display_raw_CheckBox.blockSignals(True)
        # set widgets
        self._mw.laserpulses_ComboBox.setCurrentIndex(laser_index)
        self._mw.laserpulses_display_raw_CheckBox.setChecked(show_raw_data)
        # unblock signals
        self._mw.laserpulses_ComboBox.blockSignals(False)
        self._mw.laserpulses_display_raw_CheckBox.blockSignals(False)
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

    def upload_ensemble_clicked(self):
        """

        @return:
        """
        # Get the ensemble name from the ComboBox
        ensemble_name = self._mw.gen_ensemble_ComboBox.currentText()
        # Upload the ensemble via logic module
        self._pulsed_master_logic.upload_asset(ensemble_name)
        # disable button
        self._mw.upload_ensemble_PushButton.setEnabled(False)
        self._mw.load_ensemble_PushButton.setEnabled(False)
        return

    def upload_sequence_clicked(self):
        """

        @return:
        """
        # Get the sequence name from the ComboBox
        seq_name = self._mw.gen_sequence_ComboBox.currentText()
        # Upload the asset via logic module
        self._pulsed_master_logic.upload_asset(seq_name)
        # disable button
        self._mw.upload_sequence_PushButton.setEnabled(False)
        self._mw.load_sequence_PushButton.setEnabled(False)
        return

    def update_uploaded_assets(self, asset_names_list):
        """

        @param asset_names_list:
        @return:
        """
        # enable buttons
        self._mw.upload_sequence_PushButton.setEnabled(True)
        self._mw.upload_ensemble_PushButton.setEnabled(True)
        self._mw.load_ensemble_PushButton.setEnabled(True)
        self._mw.load_sequence_PushButton.setEnabled(True)
        return

    def load_ensemble_clicked(self):
        """

        @return:
        """
        # Get the asset name to be uploaded from the ComboBox
        asset_name = self._mw.gen_ensemble_ComboBox.currentText()
        # Load asset into channles via logic module
        self._pulsed_master_logic.load_asset_into_channels(asset_name, {}, False)
        # disable button
        self._mw.load_ensemble_PushButton.setEnabled(False)
        return

    def load_sequence_clicked(self):
        """

        @return:
        """
        # Get the asset name to be uploaded from the ComboBox
        asset_name = self._mw.gen_sequence_ComboBox.currentText()
        # Load asset into channles via logic module
        self._pulsed_master_logic.load_asset_into_channels(asset_name, {}, False)
        # disable button
        self._mw.load_sequence_PushButton.setEnabled(False)
        return

    def update_loaded_asset(self, asset_name, asset_type):
        """ Check the current loaded asset from the logic and update the display. """
        label = self._mw.current_loaded_asset_Label
        if asset_name is None:
            label.setText(asset_type)
        elif asset_type == 'Pulse_Block_Ensemble' or asset_type == 'Pulse_Sequence':
            label.setText('  {0} ({1})'.format(asset_name, asset_type))
        else:
            label.setText('  Unknown asset type')
        # enable buttons
        if asset_type == 'Pulse_Block_Ensemble':
            self._mw.load_ensemble_PushButton.setEnabled(True)
        elif asset_type == 'Pulse_Sequence':
            self._mw.load_sequence_PushButton.setEnabled(True)
        return


    # def save_plots(self):
    #     """ Save plot from analysis graph as a picture. """
    #     timestamp = datetime.datetime.now()
    #     filetag = self._mw.save_tag_LineEdit.text()
    #     filepath = self._save_logic.get_path_for_module(module_name='PulsedMeasurement')
    #     if len(filetag) > 0:
    #         filename = os.path.join(filepath, '{}_{}_pulsed'.format(timestamp.strftime('%Y%m%d-%H%M-%S'), filetag))
    #     else:
    #         filename = os.path.join(filepath, '{}_pulsed'.format(timestamp.strftime('%Y%m%d-%H%M-%S')))
    #
    #     # print(type(self._mw.second_plot_ComboBox.currentText()), self._mw.second_plot_ComboBox.currentText())
    #     # pulse plot
    #     # exporter = pg.exporters.SVGExporter(self._mw.pulse_analysis_PlotWidget.plotItem.scene())
    #     # exporter.export(filename+'.svg')
    #     #
    #     # # auxiliary plot
    #     # if 'None' not in self._mw.second_plot_ComboBox.currentText():
    #     #     exporter_aux = pg.exporters.SVGExporter(self._mw.pulse_analysis_second_PlotWidget.plotItem.scene())
    #     #     exporter_aux.export(filename + '_aux' + '.svg')
    #
    #     self._pulsed_meas_logic._save_data(filetag, timestamp)



