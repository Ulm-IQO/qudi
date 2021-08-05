# -*- coding: utf-8 -*-

"""
This file contains the GUI for the vector magnet.

Qudi is free software: you can redistribute it and/or modify
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


import os
from qtpy import uic

from core.connector import Connector
from gui.colordefs import ColorScaleViridis
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from qtpy import QtCore
from qtpy import QtWidgets
from qtwidgets.scientific_spinbox import ScienDSpinBox
from qtwidgets.scan_plotwidget import ScanImageItem



class MagnetMainWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_magnet_3d_gui.ui')

        # Load it
        super(MagnetMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()


class MagnetGui(GUIBase):
    """ Main GUI for the magnet. """

    # declare connectors
    magnetlogic = Connector(interface='MagnetLogic')

    # create signals
    sigPhiMin = QtCore.Signal(float)
    sigPhiMax = QtCore.Signal(float)
    sigNPhi = QtCore.Signal(int)
    sigPhi = QtCore.Signal(float)
    sigThetaMin = QtCore.Signal(float)
    sigThetaMax = QtCore.Signal(float)
    sigNTheta = QtCore.Signal(int)
    sigTheta = QtCore.Signal(float)
    sigB = QtCore.Signal(float)
    sigIntTime = QtCore.Signal(float)
    sigReps = QtCore.Signal(float)
    
    sigStart = QtCore.Signal()
    sigStop = QtCore.Signal()
    sigSet = QtCore.Signal()
    


    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)



    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """
        
        self._magnetlogic = self.magnetlogic()
        self._mw = MagnetMainWindow()

        # connect signals to logic
        self.sigPhiMin.connect(self._magnetlogic.set_phi_min)
        self.sigPhiMax.connect(self._magnetlogic.set_phi_max)
        self.sigNPhi.connect(self._magnetlogic.set_n_phi)
        self.sigPhi.connect(self._magnetlogic.set_phi)
        self.sigThetaMin.connect(self._magnetlogic.set_theta_min)
        self.sigThetaMax.connect(self._magnetlogic.set_theta_max)
        self.sigNTheta.connect(self._magnetlogic.set_n_theta)
        self.sigTheta.connect(self._magnetlogic.set_theta)
        self.sigB.connect(self._magnetlogic.set_B)
        self.sigIntTime.connect(self._magnetlogic.set_int_time)
        self.sigReps.connect(self._magnetlogic.set_reps)
        
        self.sigStart.connect(self._magnetlogic.start_scan)
        #self.sigStop.connect()
        #self.sigSet.connect()



        # connect signal internal
        self._mw.doubleSpinBox_set_B.editingFinished.connect(self.changed_B2)
        self._mw.doubleSpinBox_scan_B.editingFinished.connect(self.changed_B1)
        self._mw.doubleSpinBox_scan_phi_min.editingFinished.connect(self.changed_phi_min)
        self._mw.doubleSpinBox_scan_phi_max.editingFinished.connect(self.changed_phi_max)
        self._mw.doubleSpinBox_scan_n_phi.editingFinished.connect(self.changed_n_phi)
        self._mw.doubleSpinBox_scan_theta_min.editingFinished.connect(self.changed_theta_min)
        self._mw.doubleSpinBox_scan_theta_max.editingFinished.connect(self.changed_theta_max)
        self._mw.doubleSpinBox_scan_n_theta.editingFinished.connect(self.changed_n_theta)
        self._mw.doubleSpinBox_scan_int_time.editingFinished.connect(self.changed_int_time)
        self._mw.doubleSpinBox_scan_reps.editingFinished.connect(self.changed_reps)
        self._mw.doubleSpinBox_set_phi.editingFinished.connect(self.changed_phi)
        self._mw.doubleSpinBox_set_theta.editingFinished.connect(self.changed_theta)

        self._mw.pushButton_start.clicked.connect(self.start_pressed)
        self._mw.pushButton_stop.clicked.connect(self.stop_pressed)
        self._mw.pushButton_set.clicked.connect(self.set_pressed)

        # set initial values from logic
        self.phi_min = self._magnetlogic.phi_min
        self.phi_max = self._magnetlogic.phi_max
        self.n_phi = self._magnetlogic.n_phi
        self.phi = self._magnetlogic.phi
        self.theta_min = self._magnetlogic.theta_min
        self.theta_max = self._magnetlogic.theta_max
        self.n_theta = self._magnetlogic.n_theta
        self.theta = self._magnetlogic.theta
        self.B =  self._magnetlogic.B
        self.int_time =  self._magnetlogic.int_time
        self.reps =  self._magnetlogic.reps

        #and also display the initial values in the gui
        self._mw.doubleSpinBox_set_B.setValue(self.B)
        self._mw.doubleSpinBox_scan_B.setValue(self.B)
        self._mw.doubleSpinBox_scan_phi_min.setValue(self.phi_min)
        self._mw.doubleSpinBox_scan_phi_max.setValue(self.phi_max)
        self._mw.doubleSpinBox_scan_n_phi.setValue(self.n_phi)
        self._mw.doubleSpinBox_scan_theta_min.setValue(self.theta_min)
        self._mw.doubleSpinBox_scan_theta_max.setValue(self.theta_max)
        self._mw.doubleSpinBox_scan_n_theta.setValue(self.n_theta)
        self._mw.doubleSpinBox_scan_int_time.setValue(self.int_time)
        self._mw.doubleSpinBox_scan_reps.setValue(self.reps)
        self._mw.doubleSpinBox_set_phi.setValue(self.phi)
        self._mw.doubleSpinBox_set_theta.setValue(self.theta)


    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        self._magnetlogic.on_deactivate()
        self._mw.close()

    def show(self):
        """Make window visible and put it above all other windows. """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()

    def changed_phi_min(self):
        self.phi_min = self._mw.doubleSpinBox_scan_phi_min.value()
        self.sigPhiMin.emit(self.phi_min)

    def changed_phi_max(self):
        self.phi_max = self._mw.doubleSpinBox_scan_phi_max.value()
        self.sigPhiMax.emit(self.phi_max)

    def changed_n_phi(self):
        self.n_phi = self._mw.doubleSpinBox_scan_n_phi.value()
        self.sigNPhi.emit(self.n_phi)

    def changed_theta_min(self):
        self.theta_min = self._mw.doubleSpinBox_scan_theta_min.value()
        self.sigThetaMin.emit(self.theta_min)

    def changed_theta_max(self):
        self.theta_max = self._mw.doubleSpinBox_scan_theta_max.value()
        self.sigThetaMax.emit(self.theta_max)

    def changed_n_theta(self):
        self.n_theta = self._mw.doubleSpinBox_scan_n_theta.value()
        self.sigNTheta.emit(self.n_theta)

    def changed_B1(self):
        """B field got changed in spinBox from the scan"""
        self.B = self._mw.doubleSpinBox_scan_B.value()
        self._mw.doubleSpinBox_set_B.setValue(self.B)
        self.sigB.emit(self.B)

    def changed_B2(self):
        """B field got changed in the spin box for setting the B field"""
        self.B = self._mw.doubleSpinBox_set_B.value()
        self._mw.doubleSpinBox_scan_B.setValue(self.B)
        self.sigB.emit(self.B)

    def changed_int_time(self):
        self.int_time = self._mw.doubleSpinBox_scan_int_time.vale()
        self.sigIntTime.emit(self.int_time)

    def changed_reps(self):
        self.reps = self._mw.doubleSpinBox_scan_reps.value()
        self.sigReps.emit(self.reps)

    def changed_phi(self):
        self.phi = self._mw.doubleSpinBox_set_phi.value()
        self.sigPhi.emit(self.phi)

    def changed_theta(self):
        self.theta = self._mw.doubleSpinBox_set_theta.value()
        self.sigTheta.emit(self.theta)

    def start_pressed(self):
        self._mw.pushButton_start.setEnabled(False)
        self._mw.pushButton_stop.setEnabled(True)
        self._mw.pushButton_set.setEnabled(False)
        self._mw.sigStart.emit()

    def stop_pressed(self):
        #TODO: dis-/enable buttons once scan has finished
        self._mw.pushButton_start.setEnabled(True)
        self._mw.pushButton_stop.setEnabled(False)
        self._mw.pushButton_set.setEnabled(True)
        self._mw.sigStop.emit()

    def set_pressed(self):
        self._mw.sigSet.emit()

