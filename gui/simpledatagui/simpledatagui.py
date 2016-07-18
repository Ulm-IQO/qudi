# -*- coding: utf-8 -*-

"""
This file contains a gui to show data from a simple data source.

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

import core.logger as logger
from gui.guibase import GUIBase
from pyqtgraph.Qt import QtCore, QtGui, uic
from collections import OrderedDict
import numpy as np
import pyqtgraph as pg
import os


class SimpleMainWindow(QtGui.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_simpledata_gui.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class SimpleDataGui(GUIBase):
    """ FIXME: Please document
    """
    _modclass = 'simplegui'
    _modtype = 'gui'

    ## declare connectors
    _in = {'simplelogic': 'SimpleDataLogic'}

    sigStart = QtCore.Signal()
    sigStop = QtCore.Signal()

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        c_dict = {'onactivate': self.initUI, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, c_dict)
        logger.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            logger.info('{}: {}'.format(key,config[key]))

    def initUI(self, e=None):
        """ Definition and initialisation of the GUI.

        @param object e: Fysom.event object from Fysom class.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """
        self._simple_logic = self.connector['in']['simplelogic']['object']

        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = SimpleMainWindow()

        # Setup dock widgets
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)

        # Plot labels.
        self._pw = self._mw.trace_PlotWidget

        self.plot1 = self._pw.plotItem
        self.plot1.setLabel('left', 'Some Value', units='some unit', color='#00ff00')
        self.plot1.setLabel('bottom', 'Number of values', units='some unit')
        self.plot2 = self._pw.plotItem
        self.plot2.setLabel('right', 'Smooth Value', units='some unit', color='#ff0000')

        self.curvearr = []
        self.smootharr = []
        ## Create an empty plot curve to be filled later, set its pen
        for i in range(self._simple_logic._data_logic.getChannels()):
            self.curvearr.append(self.plot1.plot())
            self.curvearr[-1].setPen('g')
            self.smootharr.append(self.plot2.plot())
            self.smootharr[-1].setPen('r', width=2)

        # make correct button state
        self._mw.startAction.setChecked(False)

        #####################
        # Connecting user interactions
        self._mw.startAction.triggered.connect(self.start_clicked)
        self._mw.recordAction.triggered.connect(self.save_clicked)

        #####################
        # starting the physical measurement
        self.sigStart.connect(self._simple_logic.startMeasure)
        self.sigStop.connect(self._simple_logic.stopMeasure)

        self._simple_logic.sigRepeat.connect(self.updateData)

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtGui.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def deactivation(self, e):
        """ Deactivate the module properly.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method initUI.
        """
        # FIXME: !
        self._mw.close()

    def updateData(self):
        """ The function that grabs the data and sends it to the plot.
        """
        for i in range(self._simple_logic._data_logic.getChannels()):
            self.curvearr[i].setData(
                y=self._simple_logic.buf[0:-11, i],
                x=np.arange(0, len(self._simple_logic.buf[0:-11]))
                )
            self.smootharr[i].setData(
                y=self._simple_logic.smooth[24:-25-10, i],
                x=np.arange(0, len(self._simple_logic.smooth[24:-25-10]))
                )

        if self._simple_logic.getState() == 'locked':
            self._mw.startAction.setText('Stop')
        else:
            self._mw.startAction.setText('Start')

    def start_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        if self._simple_logic.getState() == 'locked':
            self._mw.startAction.setText('Start')
            self.sigStop.emit()
        else:
            self._mw.startAction.setText('Stop')
            self.sigStart.emit()

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
        """
        return
