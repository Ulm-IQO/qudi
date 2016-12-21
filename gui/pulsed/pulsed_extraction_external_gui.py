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

#from qtpy import QtGui
from pyqtgraph.Qt import QtGui
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
from qtwidgets.scientific_spinbox import ScienDSpinBox, ScienSpinBox
#from gui.pulsed.pulse_editor import PulseEditor
from core.util.mutex import Mutex
from core.util import units
from gui.pulsed.pulse_editors import BlockEditor, BlockOrganizer, SequenceEditor
from logic.sampling_functions import SamplingFunctions

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
    _in = {'pulsedextractionexternallogic1': 'PulsedExtractionExternalLogic'}

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))


    def on_activate(self, e=None):
        """ Definition and initialisation of the GUI.

        @param object e: Fysom.event object from Fysom class.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """
        #####################
        # Configuring the dock widgets
        # Use the inherited class 'PulsedExtractionExternalMainWindow' to create the GUI window
        self._mw = PulsedExtractionExternalMainWindow()

        self._epe_logic = self.get_in_connector('pulsedextractionexternallogic1')

        # Setup dock widgets
        self._mw.setDockNestingEnabled(True)

        # Plot labels:
        self._mw.raw_data_PlotWidget.setLabel('left', 'counts', units='a.u.')
        self._mw.raw_data_PlotWidget.setLabel('bottom', 'bins', units='')
        self._mw.extracted_laser_PlotWidget.setLabel('left', 'intensity', units='a.u.')
        self._mw.extracted_laser_PlotWidget.setLabel('bottom', 'bins', units='')
        self._mw.result_PlotWidget.setLabel('left', 'normalized intensity')
        self._mw.result_PlotWidget.setLabel('bottom', 'tau', units='ns')

        ########## connect the buttons to their respective function ###########

        self._mw.load_data_PushButton.clicked.connect(self.load_data_clicked)
        self._mw.analyze_PushButton.clicked.connect(self.analyze)
        self._mw.choose_laserpulse_ComboBox.currentIndexChanged.connect(self.plot_just_laser)



    def show(self):
        """Make window visible and put it above all other windows."""
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def on_deactivate(self, e):
        # FIXME: !
        """ Deactivate the module

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        self._mw.close()



    def load_data_clicked(self):
        filename = QtGui.QFileDialog.getOpenFileName(None,"Load File","","All Files (*)")
        self._mw.data_filename_LineEdit.setText(filename)
        len_header=self._mw.header_SpinBox.value()
        column=self._mw.column_SpinBox.value()-1
        filename=self._mw.data_filename_LineEdit.text()
        self.load_data(len_header,column,filename)
        return


    def load_data(self,len_header=100,column=10,filename=''):
        self.data = self._epe_logic.load_data(len_header,column,filename)
        self.plot_raw_data(self.data)        #
        return self.data




    def extract_laser_pulses(self):
        count_treshold=self._mw.treshold_SpinBox.value()
        min_len_laser=self._mw.min_laser_SpinBox.value()
        exception=self._mw.exception_SpinBox.value()
        ignore_first=False
        #FIXME: self.data
        self.laser_x,self.laser_y=self._epe_logic.extract_laser_pulses(count_treshold,min_len_laser,
                             exception,ignore_first)

        self._mw.number_pulses_lcdNumber.display(len(self.laser_x))
        self._mw.choose_laserpulse_ComboBox.clear()
        self._mw.choose_laserpulse_ComboBox.addItem('all')
        for laserindex in range(len(self.laser_y)):
            	self._mw.choose_laserpulse_ComboBox.addItem(str(laserindex+1))

        self.plot_just_laser()

        longest=self._epe_logic.find_longest_laser_pulse(self.laser_y)
        self._mw.length_pulse_lcdNumber.display(longest)
        sum_pulses = self._epe_logic.sum_pulses(self.laser_x,self.laser_y)
        self.plot_sum_pulses(sum_pulses)

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
        if index == 0:
            for nn in range(len(self.laser_x)):
                self._mw.extracted_laser_PlotWidget.addItem(pg.PlotDataItem(self.laser_x[nn][:],
                                                                    self.laser_y[nn][:]))
        else:
            self._mw.extracted_laser_PlotWidget.addItem(pg.PlotDataItem(self.laser_x[index-1][:],
                                                                    self.laser_y[index-1][:]))
        return

    def plot_sum_pulses(self,sum_pulses):
        x_values=np.linspace(1,len(sum_pulses),len(sum_pulses))
        self._mw.sum_laser_PlotWidget.clear()
        self._mw.sum_laser_PlotWidget.addItem(pg.PlotDataItem(x_values,sum_pulses))
        return


    def plot_result(self):

        self._mw.result_PlotWidget.clear()
        if self._mw.alternating_CheckBox.isChecked():
            if (len(self.signal))%2!=0:
                print('data is not even!!!')
            else:
                x_values=np.linspace(0,len(self.signal)/2-1,len(self.signal)/2)*self._mw.tau_increment_SpinBox.value()+self._mw.tau_start_SpinBox.value()
                self._mw.result_PlotWidget.addItem(pg.PlotDataItem(x_values, self.signal[0::2]))
                self._mw.result_PlotWidget.addItem(pg.PlotDataItem(x_values, self.signal[1::2],pen='r'))
        else:
            x_values=np.linspace(0,len(self.signal)-1,len(self.signal))*self._mw.tau_increment_SpinBox.value()+self._mw.tau_start_SpinBox.value()
            self._mw.result_PlotWidget.addItem(pg.PlotDataItem(x_values, self.signal))
            return



