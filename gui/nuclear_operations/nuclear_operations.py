# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI module for nuclear operations control.

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

import os
import datetime
import pyqtgraph as pg
import pyqtgraph.exporters
from qtpy import QtGui, QtWidgets, QtCore, uic

from gui.guibase import GUIBase


class NuclearOperationsMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_nuclear_operations_gui.ui')

        # Load it
        super(NuclearOperationsMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

class NuclearOperationsGui(GUIBase):
    """ This is the main GUI Class for Nuclear Operations. """

    _modclass = 'NuclearOperationsGui'
    _modtype = 'gui'

    # declare connectors
    _in = {'nuclearoperationslogic': 'NuclearOperationsLogic',
           'savelogic': 'SaveLogic'}

    def __init__(self, manager, name, config, **kwargs):
        # declare actions for state transitions
        c_dict = {'onactivate': self.initUI, 'ondeactivate':self.deactivation}
        super().__init__(manager,
                         name,
                         config,
                         c_dict)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key,config[key]))

    def initUI(self, e=None):
        """ Definition, configuration and initialisation of the ODMR GUI.

        @param object e: Fysom.event object from Fysom class.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """

        self._no_logic = self.get_in_connector('nuclearoperationslogic')
        self._save_logic = self.get_in_connector('savelogic')

        # Create the MainWindow to display the GUI
        self._mw = NuclearOperationsMainWindow()

        # Add save file tag input box
        self._mw.save_tag_LineEdit = QtWidgets.QLineEdit(self._mw)
        self._mw.save_tag_LineEdit.setMaximumWidth(200)
        self._mw.save_tag_LineEdit.setToolTip('Enter a nametag which will be\n'
                                              'added to the filename.')
        self._mw.save_ToolBar.addWidget(self._mw.save_tag_LineEdit)


        # Set the values from the logic to the GUI:

        # Set the pulser parameter:
        self._mw.electron_rabi_periode_DSpinBox.setValue(self._no_logic.electron_rabi_periode*1e9)
        self._mw.pulser_mw_freq_DSpinBox.setValue(self._no_logic.pulser_mw_freq/1e6)
        self._mw.pulser_mw_amp_DSpinBox.setValue(self._no_logic.pulser_mw_amp)
        self._mw.pulser_mw_ch_SpinBox.setValue(self._no_logic.pulser_mw_ch)
        self._mw.nuclear_rabi_period0_DSpinBox.setValue(self._no_logic.nuclear_rabi_period0*1e6)
        self._mw.pulser_rf_freq0_DSpinBox.setValue(self._no_logic.pulser_rf_freq0/1e6)
        self._mw.pulser_rf_amp0_DSpinBox.setValue(self._no_logic.pulser_rf_amp0)
        self._mw.nuclear_rabi_period1_DSpinBox.setValue(self._no_logic.nuclear_rabi_period1*1e6)
        self._mw.pulser_rf_freq1_DSpinBox.setValue(self._no_logic.pulser_rf_freq1/1e6)
        self._mw.pulser_rf_amp1_DSpinBox.setValue(self._no_logic.pulser_rf_amp1)
        self._mw.pulser_rf_ch_SpinBox.setValue(self._no_logic.pulser_rf_ch)
        self._mw.pulser_laser_length_DSpinBox.setValue(self._no_logic.pulser_laser_length*1e9)
        self._mw.pulser_laser_amp_DSpinBox.setValue(self._no_logic.pulser_laser_amp)
        self._mw.pulser_laser_ch_SpinBox.setValue(self._no_logic.pulser_laser_ch)
        self._mw.num_singleshot_readout_SpinBox.setValue(self._no_logic.num_singleshot_readout)
        self._mw.pulser_idle_time_DSpinBox.setValue(self._no_logic.pulser_idle_time*1e9)
        self._mw.pulser_detect_ch_SpinBox.setValue(self._no_logic.pulser_detect_ch)


        # set the measurement parameter:
        self._mw.current_meas_asset_name_ComboBox.clear()
        self._mw.current_meas_asset_name_ComboBox.addItems(self._no_logic.get_meas_type_list())
        if self._no_logic.current_meas_asset_name != '':
            index = self._mw.current_meas_asset_name_ComboBox.findText(self._no_logic.current_meas_asset_name, QtCore.Qt.MatchFixedString)
            if index >= 0:
                self._mw.current_meas_asset_name_ComboBox.setCurrentIndex(index)

        if self._no_logic.current_meas_asset_name == 'Nuclear_Frequency_Scan':
            self._mw.x_axis_start_DSpinBox.setValue(self._no_logic.x_axis_start/1e6)
            self._mw.x_axis_step_DSpinBox.setValue(self._no_logic.x_axis_step/1e6)
        elif self._no_logic.current_meas_asset_name in ['Nuclear_Rabi','QSD_-_Artificial_Drive', 'QSD_-_SWAP_FID','QSD_-_Entanglement_FID']:
            self._mw.x_axis_start_DSpinBox.setValue(self._no_logic.x_axis_start*1e6)
            self._mw.x_axis_step_DSpinBox.setValue(self._no_logic.x_axis_step*1e6)

        self._mw.x_axis_num_points_SpinBox.setValue(self._no_logic.x_axis_num_points)

        self._mw.num_of_meas_runs_SpinBox.setValue(self._no_logic.num_of_meas_runs)

        # set the optimize parameters:
        self._mw.optimize_period_odmr_SpinBox.setValue(self._no_logic.optimize_period_odmr)
        self._mw.optimize_period_confocal_SpinBox.setValue(self._no_logic.optimize_period_confocal)
        self._mw.odmr_meas_freq0_DSpinBox.setValue(self._no_logic.odmr_meas_freq0/1e6)
        self._mw.odmr_meas_freq1_DSpinBox.setValue(self._no_logic.odmr_meas_freq1/1e6)
        self._mw.odmr_meas_freq2_DSpinBox.setValue(self._no_logic.odmr_meas_freq2/1e6)
        self._mw.odmr_meas_runtime_DSpinBox.setValue(self._no_logic.odmr_meas_runtime)
        self._mw.odmr_meas_freq_range_DSpinBox.setValue(self._no_logic.odmr_meas_freq_range/1e6)
        self._mw.odmr_meas_step_DSpinBox.setValue(self._no_logic.odmr_meas_step/1e6)
        self._mw.odmr_meas_power_DSpinBox.setValue(self._no_logic.odmr_meas_power)

        # set the mw parameters for measurement
        self._mw.mw_cw_freq_DSpinBox.setValue(self._no_logic.mw_cw_freq/1e6)
        self._mw.mw_cw_power_DSpinBox.setValue(self._no_logic.mw_cw_power)
        self._mw.mw_on_odmr_peak_ComboBox.clear()
        # convert on the fly the integer entries to str entries:
        self._mw.mw_on_odmr_peak_ComboBox.addItems([str(elem) for elem in self._no_logic.get_available_odmr_peaks()])

        # set gated counter parameters:
        self._mw.gc_number_of_samples_SpinBox.setValue(self._no_logic.gc_number_of_samples)
        self._mw.gc_samples_per_readout_SpinBox.setValue(self._no_logic.gc_samples_per_readout)


        # Create the graphic display for the measurement:
        self.nuclear_ops_graph = pg.PlotDataItem(self._no_logic.x_axis_list,
                                                 self._no_logic.y_axis_list,
                                                 pen=QtGui.QPen(QtGui.QColor(212, 85, 0, 255)))

        self._mw.nulcear_ops_GraphicsView.addItem(self.nuclear_ops_graph)

        # Set the proper initial display:
        self.current_meas_asset_name_changed()

        # Connect the signals:
        self._mw.current_meas_asset_name_ComboBox.currentIndexChanged.connect(self.current_meas_asset_name_changed)

        # adapt the unit according to the

        # Connect the start and stop signals:
        self._mw.action_run_stop.toggled.connect(self.start_stop_measurement)
        self._mw.action_continue.toggled.connect(self.continue_stop_measurement)
        self._mw.action_save.triggered.connect(self.save_measurement)
        self._no_logic.sigMeasurementStopped.connect(self._update_display_meas_stopped)

        # Connect graphic update:
        self._no_logic.sigCurrMeasPointUpdated.connect(self.update_meas_graph)
        self._no_logic.sigCurrMeasPointUpdated.connect(self.update_meas_parameter)

    def deactivation(self, e):
        """ Reverse steps of activation

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.

        @return int: error code (0:OK, -1:error)
        """
        self._mw.close()

    def show(self):
        """Make window visible and put it above all other windows. """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def start_stop_measurement(self, is_checked):
        """ Manages what happens if nuclear operations are started/stopped.

        @param bool ischecked: If true measurement is started, if false
                               measurement stops.
        """

        if is_checked:

            # change the axes appearance according to input values:
            self._no_logic.stop_nuclear_meas()

            self.update_all_logic_parameter()
            self._no_logic.start_nuclear_meas()
            self._mw.action_continue.setEnabled(False)
        else:
            self._no_logic.stop_nuclear_meas()
            self._mw.action_continue.setEnabled(True)

    def continue_stop_measurement(self, is_checked):
        """ Manages what happens if nuclear operations are continued/stopped.

        @param bool ischecked: If true measurement is continued, if false
                               measurement stops.
        """

        if is_checked:
            # self._no_logic.stop_nuclear_meas()
            self._no_logic.start_nuclear_meas(continue_meas=True)
            self._mw.action_run_stop.setEnabled(False)

        else:
            self._no_logic.stop_nuclear_meas()
            self._mw.action_run_stop.setEnabled(True)

    def _update_display_meas_stopped(self):
        """ Update all the displays of the current measurement state and set
            them to stop. """

        self.start_stop_measurement(is_checked=False)
        self.continue_stop_measurement(is_checked=False)

    def current_meas_asset_name_changed(self):
        """ Adapt the input widget to the current measurement sequence. """

        name = self._mw.current_meas_asset_name_ComboBox.currentText()

        if name == 'Nuclear_Rabi':
            self._mw.nuclear_rabi_period0_DSpinBox.setVisible(False)
            self._mw.nuclear_rabi_period0_Label.setVisible(False)
            self._mw.nuclear_rabi_period1_DSpinBox.setVisible(False)
            self._mw.nuclear_rabi_period1_Label.setVisible(False)
            self._mw.pulser_rf_freq1_DSpinBox.setVisible(False)
            self._mw.pulser_rf_freq1_Label.setVisible(False)
            self._mw.pulser_rf_amp1_DSpinBox.setVisible(False)
            self._mw.pulser_rf_amp1_Label.setVisible(False)

            self._mw.pulser_rf_freq0_DSpinBox.setVisible(True)
            self._mw.pulser_rf_freq0_Label.setVisible(True)

            self._mw.nulcear_ops_GraphicsView.setLabel(axis='bottom',
                                                       text='RF pulse length',
                                                       units='s')
            self._mw.nulcear_ops_GraphicsView.setLabel(axis='left',
                                                       text='Flip probability')

            self._mw.x_axis_start_Label.setText('x start (u\u00B5s)')
            self._mw.x_axis_step_Label.setText('x step (u\u00B5s)')

            self._mw.current_meas_point_Label.setText('Curr meas point (u\u00B5s)')


        elif name == 'Nuclear_Frequency_Scan':
            self._mw.pulser_rf_freq0_DSpinBox.setVisible(False)
            self._mw.pulser_rf_freq0_Label.setVisible(False)
            self._mw.nuclear_rabi_period1_DSpinBox.setVisible(False)
            self._mw.nuclear_rabi_period1_Label.setVisible(False)
            self._mw.pulser_rf_freq1_DSpinBox.setVisible(False)
            self._mw.pulser_rf_freq1_Label.setVisible(False)
            self._mw.pulser_rf_amp1_DSpinBox.setVisible(False)
            self._mw.pulser_rf_amp1_Label.setVisible(False)

            self._mw.nuclear_rabi_period0_DSpinBox.setVisible(True)
            self._mw.nuclear_rabi_period0_Label.setVisible(True)

            self._mw.nulcear_ops_GraphicsView.setLabel(axis='bottom',
                                                       text='RF pulse Frequency',
                                                       units='Hz')
            self._mw.nulcear_ops_GraphicsView.setLabel(axis='left',
                                                       text='Flip probability')

            self._mw.x_axis_start_Label.setText('x start (MHz)')
            self._mw.x_axis_step_Label.setText('x step (MHz)')

            self._mw.current_meas_point_Label.setText('Curr meas point (MHz)')

        elif name in ['QSD_-_Artificial_Drive', 'QSD_-_SWAP_FID','QSD_-_Entanglement_FID']:

            self._mw.nuclear_rabi_period0_DSpinBox.setVisible(True)
            self._mw.nuclear_rabi_period0_Label.setVisible(True)
            self._mw.nuclear_rabi_period1_DSpinBox.setVisible(True)
            self._mw.nuclear_rabi_period1_Label.setVisible(True)
            self._mw.pulser_rf_freq1_DSpinBox.setVisible(True)
            self._mw.pulser_rf_freq1_Label.setVisible(True)
            self._mw.pulser_rf_amp1_DSpinBox.setVisible(True)
            self._mw.pulser_rf_amp1_Label.setVisible(True)
            self._mw.pulser_rf_freq0_DSpinBox.setVisible(True)
            self._mw.pulser_rf_freq0_Label.setVisible(True)


            self._mw.nulcear_ops_GraphicsView.setLabel(axis='bottom',
                                                       text='Pulse length',
                                                       units='s')
            self._mw.nulcear_ops_GraphicsView.setLabel(axis='left',
                                                       text='Flip probability')

            self._mw.x_axis_start_Label.setText('x start (\u00B5s)')
            self._mw.x_axis_step_Label.setText('x step (\u00B5s)')

            self._mw.current_meas_point_Label.setText('Curr meas point (u\u00B5s)')


    def update_all_logic_parameter(self):
        """ If the measurement is started, update all parameters in the logic.
        """

        # pulser parameter:
        self._no_logic.electron_rabi_periode = self._mw.electron_rabi_periode_DSpinBox.value()/1e9
        self._no_logic.pulser_mw_freq = self._mw.pulser_mw_freq_DSpinBox.value()*1e6
        self._no_logic.pulser_mw_amp = self._mw.pulser_mw_amp_DSpinBox.value()
        self._no_logic.pulser_mw_ch = self._mw.pulser_mw_ch_SpinBox.value()
        self._no_logic.nuclear_rabi_period0 = self._mw.nuclear_rabi_period0_DSpinBox.value()/1e6
        self._no_logic.pulser_rf_freq0 = self._mw.pulser_rf_freq0_DSpinBox.value()*1e6
        self._no_logic.pulser_rf_amp0 = self._mw.pulser_rf_amp0_DSpinBox.value()
        self._no_logic.nuclear_rabi_period1 = self._mw.nuclear_rabi_period1_DSpinBox.value()/1e6
        self._no_logic.pulser_rf_freq1 = self._mw.pulser_rf_freq1_DSpinBox.value()*1e6
        self._no_logic.pulser_rf_amp1 = self._mw.pulser_rf_amp1_DSpinBox.value()
        self._no_logic.pulser_rf_ch = self._mw.pulser_rf_ch_SpinBox.value()
        self._no_logic.pulser_laser_length = self._mw.pulser_laser_length_DSpinBox.value()/1e9
        self._no_logic.pulser_laser_amp = self._mw.pulser_laser_amp_DSpinBox.value()
        self._no_logic.pulser_laser_ch = self._mw.pulser_laser_ch_SpinBox.value()
        self._no_logic.num_singleshot_readout = self._mw.num_singleshot_readout_SpinBox.value()
        self._no_logic.pulser_idle_time = self._mw.pulser_idle_time_DSpinBox.value()/1e9
        self._no_logic.pulser_detect_ch = self._mw.pulser_detect_ch_SpinBox.value()

        # measurement parameter
        curr_meas_name = self._mw.current_meas_asset_name_ComboBox.currentText()
        self._no_logic.current_meas_asset_name = curr_meas_name

        if curr_meas_name in ['Nuclear_Rabi','QSD_-_Artificial_Drive', 'QSD_-_SWAP_FID','QSD_-_Entanglement_FID']:
            self._no_logic.x_axis_start = self._mw.x_axis_start_DSpinBox.value()/1e6
            self._no_logic.x_axis_step = self._mw.x_axis_step_DSpinBox.value()/1e6
        elif curr_meas_name in ['Nuclear_Frequency_Scan']:
            self._no_logic.x_axis_start = self._mw.x_axis_start_DSpinBox.value()*1e6
            self._no_logic.x_axis_step = self._mw.x_axis_step_DSpinBox.value()*1e6
        else:
            self.log.error('This measurement does not have any units associated to it!')

        self._no_logic.x_axis_num_points = self._mw.x_axis_num_points_SpinBox.value()
        self._no_logic.num_of_meas_runs = self._mw.num_of_meas_runs_SpinBox.value()

        # Optimization measurements:
        self._no_logic.optimize_period_odmr = self._mw.optimize_period_odmr_SpinBox.value()
        self._no_logic.optimize_period_confocal = self._mw.optimize_period_confocal_SpinBox.value()

        # Optimization parameters:
        self._no_logic.odmr_meas_freq0 = self._mw.odmr_meas_freq0_DSpinBox.value()*1e6
        self._no_logic.odmr_meas_freq1 = self._mw.odmr_meas_freq1_DSpinBox.value()*1e6
        self._no_logic.odmr_meas_freq2 = self._mw.odmr_meas_freq2_DSpinBox.value()*1e6
        self._no_logic.odmr_meas_runtime = self._mw.odmr_meas_runtime_DSpinBox.value()
        self._no_logic.odmr_meas_freq_range = self._mw.odmr_meas_freq_range_DSpinBox.value()*1e6
        self._no_logic.odmr_meas_step = self._mw.odmr_meas_step_DSpinBox.value()*1e6
        self._no_logic.odmr_meas_power = self._mw.odmr_meas_power_DSpinBox.value()

        # mw parameters for measurement
        self._no_logic.mw_cw_freq = self._mw.mw_cw_freq_DSpinBox.value()*1e6
        self._no_logic.mw_cw_power = self._mw.mw_cw_power_DSpinBox.value()
        self._no_logic.mw_on_odmr_peak = int(self._mw.mw_on_odmr_peak_ComboBox.currentText())

        # gated counter
        self._no_logic.gc_number_of_samples = self._mw.gc_number_of_samples_SpinBox.value()
        self._no_logic.gc_samples_per_readout = self._mw.gc_samples_per_readout_SpinBox.value()


    def save_measurement(self):
        """ Save the current measurement.

        @return:
        """
        timestamp = datetime.datetime.now()
        filetag = self._mw.save_tag_LineEdit.text()
        filepath = self._save_logic.get_path_for_module(module_name='NuclearOperations')

        if len(filetag) > 0:
            filename = os.path.join(filepath, '{0}_{1}_NuclearOps'.format(timestamp.strftime('%Y%m%d-%H%M-%S'), filetag))
        else:
            filename = os.path.join(filepath, '{0}_NuclearOps'.format(timestamp.strftime('%Y%m%d-%H%M-%S'),))

        exporter_graph = pg.exporters.SVGExporter(self._mw.nulcear_ops_GraphicsView.plotItem.scene())

        #exporter_graph = pg.exporters.ImageExporter(self._mw.odmr_PlotWidget.plotItem)
        exporter_graph.export(filename + '.svg')

        # self._save_logic.
        self._no_logic.save_nuclear_operation_measurement(name_tag=filetag, timestamp=timestamp)

    def update_meas_graph(self):
        """ Retrieve from the logic the current x and y values and display them
            in the graph.
        """

        self.nuclear_ops_graph.setData(self._no_logic.x_axis_list, self._no_logic.y_axis_list)

    def update_meas_parameter(self):
        """ Update the display parameter close to the graph. """

        self._mw.current_meas_index_SpinBox.setValue(self._no_logic.current_meas_index)
        self._mw.elapsed_time_DSpinBox.setValue(self._no_logic.elapsed_time)
        self._mw.num_of_current_meas_runs_SpinBox.setValue(self._no_logic.num_of_current_meas_runs)

        measurement_name = self._no_logic.current_meas_asset_name
        if measurement_name in ['Nuclear_Rabi','QSD_-_Artificial_Drive', 'QSD_-_SWAP_FID','QSD_-_Entanglement_FID']:
            self._mw.current_meas_point_DSpinBox.setValue(self._no_logic.current_meas_point*1e6)
        elif measurement_name == 'Nuclear_Frequency_Scan':
            self._mw.current_meas_point_DSpinBox.setValue(self._no_logic.current_meas_point/1e6)
        else:
            pass
