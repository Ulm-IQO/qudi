# -*- coding: utf-8 -*-

"""
This file contains the general logic for magnet control.

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


import numpy as np
from qtpy import QtCore

from core.connector import Connector
from logic.generic_logic import GenericLogic


class MagnetLogic(GenericLogic):

    # declare connectors
    magnet_3d = Connector(interface='magnet_3d')

    # create signals
    sigScanNextLine = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)


    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """

        #initialize hardware
        self._magnet_3d = self.magnet_3d()

        #connect signals to hardware

        #connect signals internally
        self.sigScanNextLine.connect(self._scan_line)

        # initialize variables with standard values
        # the GUI takes these as initial values as well
        self.phi_min = 0
        self.phi_max = 360
        self.n_phi = 20
        self.phi = 0
        self.theta_min = 0
        self.theta_max = 180
        self.n_theta = 20
        self.theta = 0
        self.B = 0.01
        self.int_time = 1
        self.reps = 1

    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        self._magnet_3d.on_deactivate()
        print('deactivating magnet')

    #--------------------------------------------
    #functions to store values as class objects
    def set_phi_min(self,phi_min):
        self.phi_min = phi_min

    def set_phi_max(self,phi_max):
        self.phi_max = phi_max
    
    def set_n_phi(self,n_phi):
        self.n_phi = n_phi

    def set_phi(self,phi):
        self.phi = phi

    def set_theta_min(self,theta_min):
        self.theta_min = theta_min

    def set_theta_max(self,theta_max):
        self.theta_max = theta_max
    
    def set_n_theta(self,n_theta):
        self.n_theta = n_theta

    def set_theta(self,theta):
        self.theta = theta

    def set_B(self,B):
        self.B = B

    def set_int_time(self,int_time):
        self.int_time = int_time

    def set_reps(self,reps):
        self.reps = reps
    #--------------------------------------------

    def calc_xyz_from_angle(self,B,theta,phi):
        """ Calculates x,y,z from spherical coordinates.

        Returns list with values.
        """
        x = B * np.sin(2*np.pi/360*theta) * np.cos(2*np.pi/360*phi)
        y = B * np.sin(2*np.pi/360*theta) * np.sin(2*np.pi/360*phi)
        z = B * np.cos(2*np.pi/360*theta)
        return [x,y,z]
    

    def ramp(self,target_field_polar=[0,0,0]):
        """Tells the magnet to ramp the B-field to the specified value.
        
        @param target_field_polar: iterable with the spherical parameters [B,theta,phi].
        """
        B = target_field_polar[0]
        theta = target_field_polar[1]
        phi = target_field_polar[2]
        target_field_cartesian = self.calc_xyz_from_angle(B,theta,phi)
        self._magnet_3d.ramp(target_field_cartesian)

        return 0

    def start_scan(self):
        """"""
        #set up the array for the angles
        self.thetas = np.linspace(self.theta_min, self.theta_max, self.n_theta)
        self.phis = np.linspace(self.phi_min, self.phi_max, self.n_phi)
        self._scan_counter = 0

        #set up the array for the plot
        self.thetaPhiImage = np.zeros(len(self.thetas),len(self.phis))

        #start scan of first line
        self.sigScanLine.emit()

        return 0
    
    def _scan_line(self):
        """Scans one line along phi for fixed theta."""
        #SCAN THE LINE
        #RETURN THE COUNTS FOR THE LINES
        #WRITE THE COUNTS IN THE IMAGE MATRIX
        self._scan_counter += 1
        self.sigScanNextLine.emit()
    
    