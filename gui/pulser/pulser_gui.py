#-*- coding: utf-8 -*-


"""
This file contains the Qudi gui file for loading pulse patterns.

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
import numpy as np
from tkinter import Tk
import tkinter.filedialog as fd
from functools import partial
import inspect

from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic

from core.connector import Connector
from gui.guibase import GUIBase



class PulserMainWindow(QtWidgets.QMainWindow):
    """
    Create the Main Window based on the *.ui file.
    
    """

    def __init__(self, **kwargs):
        # Get the path to the *.ui file.
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'load_pulses.ui')

        super().__init__(**kwargs)
        uic.loadUi(ui_file, self) # Loads the ui file.
        self.show() # Shows the GUI.



class PulserGUI(GUIBase):
    """GUI to talk to a pulsestreamer.
    
    Config example for copy paste:

    pulsergui:
        module.Class: 'pulser.pulser_gui.PulserGUI'
        connect:
            pulserlogic: 'pulserlogic'
    """
    
    #declare the connectors
    pulserlogic = Connector(interface='PulserLogic')

    # signals to logic
    sigPattern = QtCore.Signal(str,list)
    sigConst = QtCore.Signal(str)
    sigLow = QtCore.Signal(str)
    sigDelPattern = QtCore.Signal(str)
    sigStart = QtCore.Signal()
    sigStop = QtCore.Signal()



    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    

    def on_activate(self):

        self._pulserlogic = self.pulserlogic()
        # creates the window
        self._pw = PulserMainWindow()
    
        # connect signals internal
        # load pattern buttons
        self._pw.pushButton_path_d0.clicked.connect(partial(self.load_ch_clicked,'d0'))
        self._pw.pushButton_path_d1.clicked.connect(partial(self.load_ch_clicked,'d1'))
        self._pw.pushButton_path_d2.clicked.connect(partial(self.load_ch_clicked,'d2'))
        self._pw.pushButton_path_d3.clicked.connect(partial(self.load_ch_clicked,'d3'))
        self._pw.pushButton_path_d4.clicked.connect(partial(self.load_ch_clicked,'d4'))
        self._pw.pushButton_path_d5.clicked.connect(partial(self.load_ch_clicked,'d5'))
        self._pw.pushButton_path_d6.clicked.connect(partial(self.load_ch_clicked,'d6'))
        self._pw.pushButton_path_d7.clicked.connect(partial(self.load_ch_clicked,'d7'))
        # const buttons
        self._pw.pushButton_const_d0.clicked.connect(partial(self.const_clicked,'d0'))
        self._pw.pushButton_const_d1.clicked.connect(partial(self.const_clicked,'d1'))
        self._pw.pushButton_const_d2.clicked.connect(partial(self.const_clicked,'d2'))
        self._pw.pushButton_const_d3.clicked.connect(partial(self.const_clicked,'d3'))
        self._pw.pushButton_const_d4.clicked.connect(partial(self.const_clicked,'d4'))
        self._pw.pushButton_const_d5.clicked.connect(partial(self.const_clicked,'d5'))
        self._pw.pushButton_const_d6.clicked.connect(partial(self.const_clicked,'d6'))
        self._pw.pushButton_const_d7.clicked.connect(partial(self.const_clicked,'d7'))
        #low buttons
        self._pw.pushButton_low_d0.clicked.connect(partial(self.low_clicked,'d0'))
        self._pw.pushButton_low_d1.clicked.connect(partial(self.low_clicked,'d1'))
        self._pw.pushButton_low_d2.clicked.connect(partial(self.low_clicked,'d2'))
        self._pw.pushButton_low_d3.clicked.connect(partial(self.low_clicked,'d3'))
        self._pw.pushButton_low_d4.clicked.connect(partial(self.low_clicked,'d4'))
        self._pw.pushButton_low_d5.clicked.connect(partial(self.low_clicked,'d5'))
        self._pw.pushButton_low_d6.clicked.connect(partial(self.low_clicked,'d6'))
        self._pw.pushButton_low_d7.clicked.connect(partial(self.low_clicked,'d7'))
        # delete pattern buttons
        self._pw.pushButton_delete_d0.clicked.connect(partial(self.del_ch_clicked,'d0'))
        self._pw.pushButton_delete_d1.clicked.connect(partial(self.del_ch_clicked,'d1'))
        self._pw.pushButton_delete_d2.clicked.connect(partial(self.del_ch_clicked,'d2'))
        self._pw.pushButton_delete_d3.clicked.connect(partial(self.del_ch_clicked,'d3'))
        self._pw.pushButton_delete_d4.clicked.connect(partial(self.del_ch_clicked,'d4'))
        self._pw.pushButton_delete_d5.clicked.connect(partial(self.del_ch_clicked,'d5'))
        self._pw.pushButton_delete_d6.clicked.connect(partial(self.del_ch_clicked,'d6'))
        self._pw.pushButton_delete_d7.clicked.connect(partial(self.del_ch_clicked,'d7')) 
        # other buttons
        self._pw.pushButton_start.clicked.connect(self.start_clicked)
        self._pw.pushButton_stop.clicked.connect(self.stop_clicked)

        # connect signals to logic file
        self.sigPattern.connect(self._pulserlogic.store_pattern)
        self.sigConst.connect(self._pulserlogic.set_constant)
        self.sigLow.connect(self._pulserlogic.set_low)
        self.sigDelPattern.connect(self._pulserlogic.delete_pattern)
        self.sigStart.connect(self._pulserlogic.run_sequence)
        self.sigStop.connect(self._pulserlogic.stop_sequence)


    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._pw)
        self._pw.activateWindow()
        self._pw.raise_()
        return
    

    def on_deactivate(self):
        """
        Has no function as of yet.

        """
        pass


    def get_pattern_from_file(self,ch):
        """
        Gets the pattern for channel ch from a txt file.

        Pattern needs to be specified as column of integers (time in ns).
        Sign specifies hign (+) or low (-).
        Example for a pattern with 0.5s high, 0.5s low, 1s high, 2s low:
            0.5e9
            -0.5e9
            1e9
            -2e9

        @param ch: Specifies which output channel to use for the sequence.
            it needs to be one of the following d0, d1, ... , d7, a0, a1.

        @return pattern: patter for the pulse.

        @return fname: path to the file that got opened.

        """

        root = Tk()
        root.withdraw() # we don't want a full GUI, so keep the root window from appearing
        root.wm_attributes('-topmost', 1) # push to front
        fname = fd.askopenfilename() # show an "Open" dialog box and return the path to the selected file

        try:
            #times need to be specified in ns
            raw_pattern = np.loadtxt(fname, dtype=int)
            pattern = self.turn_into_pattern(raw_pattern)
        except:
            print('Specified file could not be found.\n')
            pattern = [(1,0)] #dummy pattern to get rid off error popup
            fname = 'none'
        
        return pattern , fname
        
    
    def turn_into_pattern(self,raw_pattern):
        """Takes a raw pattern and turns it into a form that the pulststteamer can read.
        
        @param raw_pattern: List of signed integers. +time specifies time for high, -time for low.

        @return pattern: list of tupels
        """
        pattern = []
        for el in raw_pattern:
            el = int(el)
            if el < 0:
                level = 0
            else:
                level = 1
            pattern.append((abs(el),level))
        
        return pattern


    def start_clicked(self):
        """Tells logic to start the sequence."""
        # get status of buttons and save into dict
        self.button_status_dict = self.get_status_of_QPushButtons()
        # deactivate all buttons
        names = self.get_names(ui=self._pw,type=QtWidgets.QPushButton)
        for name in names:
            eval('self._pw.' + name + '.setEnabled(False)')
        # activate stop button
        self._pw.pushButton_stop.setEnabled(True)
        # emit start signal to logic
        self.sigStart.emit()


    def stop_clicked(self):
        """Tells logic to start the sequence"""
        # reset status of buttons to before start was clicked
        for key in self.button_status_dict.keys():
            status = self.button_status_dict[key]
            eval('self._pw.' + key + '.setEnabled(' + str(status) + ')')
        # # deactivate stop button
        # self._pw.pushButton_stop.setEnabled(False)
        # # activate start button
        # self._pw.pushButton_start.setEnabled(True)
        # emit start signal to logic
        self.sigStop.emit()
    

    def load_ch_clicked(self,ch):
        """Gets pattern from file and sends it to logic.

        @param ch: Name of the chosen channel. Needs to be 'd0' ... 'd7', 'a0', 'a1'
        """
        # load the pattern from the file
        pattern , fname = self.get_pattern_from_file(ch)
        # display path to file
        eval('self._pw.label_path_' + ch + '.setText(fname)')
        self.deactivate_input_buttons(ch)
        # send pattern to logic
        self.sigPattern.emit(ch,pattern)
    

    def const_clicked(self,ch):
        """Tells the logic which channel needs a constant output.
        """        
        #display const
        eval('self._pw.label_path_' + ch + '.setText("HIGH")')
        self.deactivate_input_buttons(ch)
        # tell logic
        self.sigConst.emit(ch)


    def low_clicked(self,ch):
        """Tells the logic which channel needs a constant output.
        """
        #display const low
        eval('self._pw.label_path_' + ch + '.setText("LOW")')
        self.deactivate_input_buttons(ch)
        # tell logic
        self.sigLow.emit(ch)


    def del_ch_clicked(self,ch):
        """Deletes pattern for specified channel.

        @param ch: channel for which to delete the pattern.

        """
        # remove old path from display
        eval('self._pw.label_path_' + ch + '.setText("")')
        self.reactivate_input_buttons(ch)
        # send signal to logic
        self.sigDelPattern.emit(ch)


    def get_names(self, ui, type):
        """Returns the names of all objects of the type "pyte" from the object "ui".

        @param ui: object(?) that holds the to be named objects, e.g. self._pw

        @param type: type of the objects that should be listed, e.g. QtWidgets.QPushButton

        @return names: list with the names of the objects of type ype

        """

        members = inspect.getmembers(ui)
        names = []
        for name,obj in members:
            if isinstance(obj,type):
                names.append(name)
        return names
    
    
    def get_status_of_QPushButtons(self):
        """ Returns the status (enabled or not) of a QPushButtons.

        @return status_dict: dictionary with the name of the buttons as key and status (True, False) as entry.

        """
        ui = self._pw
        names = self.get_names(ui=ui,type=QtWidgets.QPushButton)
        status_dict = {}
        for name in names:
            
            status = eval('ui.%s.isEnabled()' % name)
            status_dict[name]=status
        return status_dict

    def deactivate_input_buttons(self, ch):
        # deactivate load pattern button
        eval('self._pw.pushButton_path_' + ch + '.setEnabled(False)')
        # deactivate constant output button
        eval('self._pw.pushButton_const_' + ch + '.setEnabled(False)')
        # deactivate low output button
        eval('self._pw.pushButton_const_' + ch + '.setEnabled(False)')
        # activate remove pattern button
        eval('self._pw.pushButton_delete_' + ch + '.setEnabled(True)')

    def reactivate_input_buttons(self, ch):
        # activate load pattern button
        eval('self._pw.pushButton_path_' + ch + '.setEnabled(True)')
        # activate constant output button
        eval('self._pw.pushButton_const_' + ch + '.setEnabled(True)')
        # activate low output button
        eval('self._pw.pushButton_const_' + ch + '.setEnabled(True)')
        # deactivate remove pattern button
        eval('self._pw.pushButton_delete_' + ch + '.setEnabled(False)')