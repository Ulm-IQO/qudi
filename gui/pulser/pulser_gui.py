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
    sigStart = QtCore.Signal()
    sigStop = QtCore.Signal()



    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def on_activate(self):

        self._pulserlogic = self.pulserlogic()
        #creates the window
        self._pw = PulserMainWindow()
    
        #connect signals internal
        self._pw.pushButton_path_d0.clicked.connect(partial(self.load_ch_clicked,'d0'))
        self._pw.pushButton_path_d1.clicked.connect(partial(self.load_ch_clicked,'d1'))
        self._pw.pushButton_path_d2.clicked.connect(partial(self.load_ch_clicked,'d2'))
        self._pw.pushButton_path_d3.clicked.connect(partial(self.load_ch_clicked,'d3'))
        self._pw.pushButton_path_d4.clicked.connect(partial(self.load_ch_clicked,'d4'))
        self._pw.pushButton_path_d5.clicked.connect(partial(self.load_ch_clicked,'d5'))
        self._pw.pushButton_path_d6.clicked.connect(partial(self.load_ch_clicked,'d6'))
        self._pw.pushButton_path_d7.clicked.connect(partial(self.load_ch_clicked,'d7'))
        self._pw.pushButton_start.clicked.connect(self.start_clicked)
        self._pw.pushButton_stop.clicked.connect(self.stop_clicked)

        #connect signals to logic file
        self.sigPattern.connect(self._pulserlogic.store_pattern)
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
        self.sigStart.emit()

    def stop_clicked(self):
        """Tells logic to start the sequence"""
        self.sigStop.emit()
    
    def load_ch_clicked(self,ch):
        """Gets pattern from file and sends it to logic.

        @param ch: Name of the chosen channel. Needs to be 'd0' ... 'd7', 'a0', 'a1'
        """
        # load the pattern from the file
        pattern , fname = self.get_pattern_from_file(ch)
        # display path to file
        eval('self._pw.label_path_' + ch + '.setText(fname)')
        # TODO: make label scrollable or resize it to fit content.
        # send pattern to logic
        self.sigPattern.emit(ch,pattern)
    