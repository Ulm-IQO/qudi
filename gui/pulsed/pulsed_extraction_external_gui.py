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
from core.module import Connector
from core.util import units
from core.util.mutex import Mutex
from gui.colordefs import QudiPalettePale as palette
from gui.colordefs import QudiPalette as palettedark
from gui.guibase import GUIBase
from gui.pulsed.pulse_editors import BlockEditor, BlockOrganizer, SequenceEditor
#from gui.pulsed.pulse_editor import PulseEditor
from logic.sampling_functions import SamplingFunctions
#from qtpy import QtGui
from pyqtgraph.Qt import QtGui
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic
from qtwidgets.scientific_spinbox import ScienDSpinBox, ScienSpinBox



class PulsedExtractionExternalMainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pulsed_extraction_external_gui.ui')

        # Load it
        super(PulsedExtractionExternalMainWindow, self).__init__()

        uic.loadUi(ui_file, self)
        self.show()


class PulsedExtractionExternalGui(GUIBase):


    _modclass = 'ExternalPulseExtractionGui'
    _modtype = 'gui'

    # declare connectors
    pulsedextractionexternallogic1 = Connector(interface_name='PulsedExtractionExternalLogic')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """
        #####################
        # Configuring the dock widgets
        # Use the inherited class 'PulsedExtractionExternalMainWindow' to create the GUI window
        self._mw = PulsedExtractionExternalMainWindow()

        self._epe_logic = self.get_connector('pulsedextractionexternallogic1')

        # Setup dock widgets
        self._mw.setDockNestingEnabled(True)

        # Plot labels:
        self._mw.raw_data_PlotWidget.setLabel('left', 'counts', units='a.u.')
        self._mw.raw_data_PlotWidget.setLabel('bottom', 'bins', units='')
        self._mw.extracted_laser_PlotWidget.setLabel('left', 'intensity', units='a.u.')
        self._mw.extracted_laser_PlotWidget.setLabel('bottom', 'bins', units='')
        self._mw.result_PlotWidget.setLabel('left', 'normalized intensity')
        self._mw.result_PlotWidget.setLabel('bottom', 'tau')

        ########## connect the buttons to their respective function ###########

        self._mw.data_filename_LineEdit.editingFinished.connect(self.load_data)
        self._mw.analysis_method_ComboBox.currentIndexChanged.connect(self.change_parameters)
        self._mw.load_data_PushButton.clicked.connect(self.load_data_clicked)
        self._mw.analyze_PushButton.clicked.connect(self.analyze)
        self._mw.choose_laserpulse_ComboBox.currentIndexChanged.connect(self.plot_just_laser)

        self._mw.save_result_PushButton.clicked.connect(self.save_result)
        self._mw.start_SpinBox.editingFinished.connect(self.plot_result)
        self._mw.increment_SpinBox.editingFinished.connect(self.plot_result)
        self._mw.xlabel_LineEdit.editingFinished.connect(self.plot_result)
        self._mw.ylabel_LineEdit.editingFinished.connect(self.plot_result)
        self._mw.errorbars_CheckBox.toggled.connect(self.plot_result)


        ########## Analysis method combobox setup ##########

        methods=self._epe_logic.get_analysis_methods()
        for method in methods:
            self._mw.analysis_method_ComboBox.addItem(method)




    def show(self):
        """Make window visible and put it above all other windows."""
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def on_deactivate(self):
        # FIXME: !
        """ Deactivate the module
        """
        self._mw.close()



    def load_data_clicked(self):
        filename = QtGui.QFileDialog.getOpenFileName(None,"Load File","","All Files (*)")[0]
        self._mw.data_filename_LineEdit.setText(filename)
        self.load_data()
        return


    def load_data(self):
        len_header=self._mw.header_SpinBox.value()
        column=self._mw.column_SpinBox.value()-1
        filename=self._mw.data_filename_LineEdit.text()
        self.data = self._epe_logic.load_data(len_header,column,filename)
        self.plot_raw_data(self.data)        #
        return self.data




    def extract_laser_pulses(self):
        ignore_first=self._mw.ignore_first_CheckBox.checkState()
        method=self._mw.analysis_method_ComboBox.currentText()
        param_dict={}
        if method == 'treshold':
            param_dict['count_treshold']=self._mw.treshold_SpinBox.value()
            param_dict['min_len_laser']=self._mw.min_laser_SpinBox.value()
            param_dict['exception']=self._mw.exception_SpinBox.value()
            self.log.warning(param_dict)
            #FIXME: self.data

        if method == 'Niko':
            param_dict['number_laser'] = self._mw.number_pulses_SpinBox.value()
            param_dict['conv'] = self._mw.filter_SpinBox.value()
            self.log.warning(param_dict)

        if method == 'old':
            param_dict['number_laser'] = self._mw.number_pulses_SpinBox.value()
            param_dict['laser_length'] = self._mw.pulse_length_SpinBox.value()
            param_dict['initial_offset'] = self._mw.initial_offset_SpinBox.value()
            param_dict['initial_length'] = self._mw.initial_length_SpinBox.value()
            param_dict['increment_length'] = self._mw.increment_length_SpinBox.value()


        self.laser_y=self._epe_logic.extract_laser_pulses(method,ignore_first,param_dict)
        self._mw.number_pulses_lcdNumber.display(len(self.laser_y))
        self._mw.choose_laserpulse_ComboBox.clear()
        self._mw.choose_laserpulse_ComboBox.addItem('sum')
        for index, laser in enumerate(self.laser_y):
            self._mw.choose_laserpulse_ComboBox.addItem(str(index+1))
        self.plot_just_laser()
        longest=self._epe_logic.length_laser_pulses(self.laser_y)
        self._mw.length_pulse_lcdNumber.display(longest)

        return self.laser_x,self.laser_y

    def analyze_data(self):

        signal_start_bin=self._mw.signal_begin_SpinBox.value()
        signal_end_bin=self._mw.signal_end_SpinBox.value()
        norm_start_bin=self._mw.norm_begin_SpinBox.value()
        norm_end_bin=self._mw.norm_end_SpinBox.value()

        laser=np.asarray(self.laser_y)
        self.signal,self.measuring_error=self._epe_logic.analyze_data(laser,norm_start_bin,norm_end_bin,
                                     signal_start_bin,signal_end_bin)
        self.plot_result()
        return self.signal,self.measuring_error


    def analyze(self):
        self.extract_laser_pulses()
        self.analyze_data()
        return



########## Plot functions ##########

    def plot_raw_data(self,data):
        bins=np.linspace(1,len(data),len(data))
        self._mw.raw_data_PlotWidget.clear()
        self._mw.raw_data_PlotWidget.addItem(pg.PlotDataItem(bins,data))
        return


    def plot_just_laser(self):
        index = self._mw.choose_laserpulse_ComboBox.currentIndex()
        self._mw.extracted_laser_PlotWidget.clear()
        #prepare x_axis_
        self.laser_x=np.linspace(1,len(self.laser_y[1]),len(self.laser_y[1]))
        if index == 0:
            sum=self._epe_logic.sum_pulses(self.laser_y)
            self._mw.extracted_laser_PlotWidget.addItem(pg.PlotDataItem(self.laser_x,sum))
        else:
            self._mw.extracted_laser_PlotWidget.addItem(pg.PlotDataItem(self.laser_x,
                                                                    self.laser_y[index-1][:]))
        return



    def plot_result(self):

        self._mw.result_PlotWidget.clear()
        start=self._mw.start_SpinBox.value()
        increment=self._mw.increment_SpinBox.value()
        xlabel=self._mw.xlabel_LineEdit.text()
        ylabel=self._mw.ylabel_LineEdit.text()

        if self._mw.alternating_CheckBox.isChecked():
            if (len(self.signal))%2!=0:
                print('data is not even!!!')
            else:
                x_values = self._epe_logic.compute_x_values(start,increment,True)
                self._mw.result_PlotWidget.addItem(pg.PlotDataItem(x_values, self.signal[0::2]))
                self._mw.result_PlotWidget.addItem(pg.PlotDataItem(x_values, self.signal[1::2],pen='r'))
        else:
            x_values = self._epe_logic.compute_x_values(start,increment,False)
            self._mw.result_PlotWidget.addItem(pg.PlotDataItem(x_values, self.signal))
            if self._mw.errorbars_CheckBox.isChecked():
                beamwidth=self.compute_errorbar_beamwidth(x_values)
                self._mw.result_PlotWidget.addItem(pg.ErrorBarItem(x=x_values, y=self.signal,
                                                               top=self.measuring_error,
                                                               bottom=self.measuring_error,
                                                                   beam=beamwidth))

        self._mw.result_PlotWidget.setLabel('left',ylabel)
        self._mw.result_PlotWidget.setLabel('bottom',xlabel)

        return

    def change_parameters(self):
        method = self._mw.analysis_method_ComboBox.currentText()
        self._mw.number_pulses_Label.setVisible(False)
        self._mw.number_pulses_SpinBox.setVisible(False)
        self._mw.filter_Label.setVisible(False)
        self._mw.filter_SpinBox.setVisible(False)
        self._mw.treshold_Label.setVisible(False)
        self._mw.treshold_SpinBox.setVisible(False)
        self._mw.min_laser_Label.setVisible(False)
        self._mw.min_laser_SpinBox.setVisible(False)
        self._mw.exception_Label.setVisible(False)
        self._mw.exception_SpinBox.setVisible(False)
        self._mw.pulse_length_Label.setVisible(False)
        self._mw.pulse_length_SpinBox.setVisible(False)
        self._mw.initial_offset_Label.setVisible(False)
        self._mw.initial_offset_SpinBox.setVisible(False)
        self._mw.initial_length_Label.setVisible(False)
        self._mw.initial_length_SpinBox.setVisible(False)
        self._mw.increment_length_Label.setVisible(False)
        self._mw.increment_length_SpinBox.setVisible(False)
        if method == 'Niko':
            self._mw.number_pulses_Label.setVisible(True)
            self._mw.number_pulses_SpinBox.setVisible(True)
            self._mw.filter_Label.setVisible(True)
            self._mw.filter_SpinBox.setVisible(True)
        elif method == 'treshold':
            self._mw.treshold_Label.setVisible(True)
            self._mw.treshold_SpinBox.setVisible(True)
            self._mw.min_laser_Label.setVisible(True)
            self._mw.min_laser_SpinBox.setVisible(True)
            self._mw.exception_Label.setVisible(True)
            self._mw.exception_SpinBox.setVisible(True)
        elif method == 'old':
            self._mw.number_pulses_Label.setVisible(True)
            self._mw.number_pulses_SpinBox.setVisible(True)
            self._mw.pulse_length_Label.setVisible(True)
            self._mw.pulse_length_SpinBox.setVisible(True)
            self._mw.initial_offset_Label.setVisible(True)
            self._mw.initial_offset_SpinBox.setVisible(True)
            self._mw.initial_length_Label.setVisible(True)
            self._mw.initial_length_SpinBox.setVisible(True)
            self._mw.increment_length_Label.setVisible(True)
            self._mw.increment_length_SpinBox.setVisible(True)

        else:
            self.log.warning('Not yet implemented')
        return method

    def compute_errorbar_beamwidth(self,x_data):
        beamwidth = np.inf
        for i in range(len(x_data) - 1):
            width = x_data[i + 1] - x_data[i]
            width = width / 3
            if width <= beamwidth:
                beamwidth = width
        return beamwidth


    ########## Save data ##########

    def save_result(self):
        self._epe_logic.save_file()
        self._epe_logic.save_figure()
        return





