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

import numpy as np
from qtpy import QtCore

from core.connector import Connector
from core.pi3_utils import delay
from logic.generic_logic import GenericLogic


class MagnetLogic(GenericLogic):

    # declare connectors
    magnet_3d = Connector(interface='magnet_3d')
    timetagger = Connector(interface='TT')


    # create signals internal
    sigScanNextLine = QtCore.Signal()
    sigInitNextPixel = QtCore.Signal()
    sigScanPixel = QtCore.Signal()

    # create signals to hardware
    sigPause = QtCore.Signal()
    sigContinue = QtCore.Signal()
    sigRampZero = QtCore.Signal()
    sigGetPos = QtCore.Signal()

    # create signals to gui
    sigAngleChanged = QtCore.Signal()
    sigGotPos = QtCore.Signal(list,list)
    sigRampFinished = QtCore.Signal()
    sigPixelFinished = QtCore.Signal()

    def __init__(self, config, **kwargs):

        # initialize variables with standard values
        # the GUI takes these as initial values as well
        self.phi_min = 0
        self.phi_max = 360
        self.n_phi = 10
        self.phis = np.linspace(self.phi_min, self.phi_max, self.n_phi)
        self.phi = 0
        self.theta_min = 0
        self.theta_max = 180
        self.n_theta = 10
        self.thetas = np.linspace(self.theta_min, self.theta_max, self.n_theta)
        self.theta = 0
        self.B = 0.01
        self.int_time = 1
        self.reps = 1

        # booleans for the scan
        self.abort_scan = False
        self.scanning_finished = False

        # set up the image array for the plot
        self.thetaPhiImage = np.zeros((self.n_theta,self.n_phi))
        # matrix for testing
        self.thetaPhiImage = np.random.rand(self.n_theta,self.n_phi)
        for i in range(self.n_theta):
            for j in range(self.n_phi):
                self.thetaPhiImage[i,j] = 10*i+j

        super().__init__(config=config, **kwargs)


    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """

        #initialize hardware
        self._magnet_3d = self.magnet_3d()
        self._timetagger = self.timetagger()

        #connect signals to hardware
        self.sigPause.connect(self._magnet_3d.pause_ramp)
        self.sigContinue.connect(self._magnet_3d.continue_ramp)
        self.sigRampZero.connect(self._magnet_3d.ramp_to_zero)
        
        # connect signals from hardware
        self._magnet_3d.sigRampFinished.connect(self._ramp_finished)

        #connect signals internally
        self.sigScanNextLine.connect(self._scan_line)
        self.sigInitNextPixel.connect(self._init_pixel)
        self.sigScanPixel.connect(self._scan_pixel)

        

    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        # deactivates 3d magnet, rmaps it back to zero
        self._magnet_3d.on_deactivate()

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

    def pause_ramp(self):
        """Pauses the ramp."""
        self.sigPause.emit()

    def continue_ramp(self):
        """Continues the ramp."""
        self.sigContinue.emit()

    def ramp_to_zero(self):
        """Tells the hardware to ramp the B field to zero."""
        self.sigRampZero.emit()

    def _ramp_finished(self):
        """Takes the signal from hardware and passes it on to the gui."""
        self.sigRampFinished.emit()

    def start_scan(self):
        """"""
        #set up the array for the angles
        self.thetas = np.linspace(self.theta_min, self.theta_max, self.n_theta)
        self.phis = np.linspace(self.phi_min, self.phi_max, self.n_phi)
        #calculate dimension of the image
        self.n_lines = self.n_theta
        self.n_pixels = self.n_phi
        # set index of the scan line to 0, goes to n_lines
        self._line_counter = 0
        # index of the pixel in the current line. It goes up to n_pixels.
        self._pixel_counter = 0

        # set up the array for the plot
        self.thetaPhiImage = np.zeros((self.n_lines,self.n_pixels))

        #start scan of first line
        self.sigScanNextLine.emit()

        return 0
    
    def _scan_line(self):
        """Scans one line along phi for fixed theta."""
        print('Scanning line %i'%self._line_counter)

        # stop if last line is done
        if self._line_counter == self.n_lines:
            print('Scan done')
            self.scanning_finished = True
            return 0
        # else go to next line
        else:
            # set pixel counter to 0.
            self._pixel_counter = 0
            # scan first pixel in next line
            self.sigInitNextPixel.emit()

    def _init_pixel(self):
        if self.abort_scan:
            self.scanning_finished = True
            return
        # change B field
        B = self.B
        theta = self.thetas[self._line_counter]
        phi = self.phis[self._pixel_counter]
        self.ramp(target_field_polar=[B,theta,phi])
        
        #start timer
        self._pixel_timer = QtCore.QTimer()
        self._pixel_timer.timeout.connect(self._check_ramp)
        self._pixel_timer.setInterval(1000)
        self._pixel_timer.start()


    def _check_ramp(self):
        """Checks the ramping state of the magnet and sends signal if all are done.
        
        Also stops the timer.
        """
        status = self._magnet_3d.get_ramping_state()
        if status == [2,2,2]:
            self._pixel_timer.stop()
            del self._pixel_timer
            self.sigScanPixel.emit()


    def _scan_pixel(self):
        """Gets countrate for current pixel.
        
        Countrate gets recorded in image matrix.
        """
        # ask TT for countrate
        ctr = self._timetagger.countrate()
        if self.int_time == 0:
            # take only one measurement
            # position 2 gives sum of both APDs
            counts = ctr.getData()[2]
        else:
            #get countrate every 0.1 s
            delay_time = 0.1
            n_points = round(self.int_time/delay_time)
            counts = 0
            for i in range(n_points):
                # position 2 gives sum of both APDs
                counts += ctr.getData()[2]
                delay(delay_time)
            counts = counts/n_points

        # write counts to pixel in image matrix
        self.thetaPhiImage[self._pixel_counter, self._line_counter] = counts

        # hopefully this does not break anything
        self.sigPixelFinished.emit()

        # increase pixel counter
        self._pixel_counter += 1
        #go to next line if line is finished
        if self._pixel_counter == self.n_pixels:
            self._line_counter += 1
            self.sigScanNextLine.emit()
        # else, go to next pixel
        else:
            self.sigInitNextPixel.emit()

    def _set_B_field(self):
        """Calls ramp with class values."""
        B = self.B
        phi = self.phi
        theta = self.theta
        target_field_polar = [B,theta,phi]
        self.ramp(target_field_polar)

    def get_field_cartesian(self):
        """Returns list with field in x,y,z direction."""
        field_xyz = self._magnet_3d.get_field()
        return field_xyz

    def get_field_spherical(self):
        """Returns list with spherical field parameters [B,theta,phi]."""
        [x,y,z] = self._magnet_3d.get_field()

        B = (x**2 + y**2 + z**2)**0.5

        if np.isclose(z, 0.0):
            theta = 90
        else:
            theta = 180/np.pi*np.arctan((x**2 + y**2)**0.5/z)

        if np.isclose(x, 0.0):
            if y >= 0:
                phi = 90
            else:
                phi = 270
        else:
            phi = 180/np.pi*np.arctan(y/x)

        return [B,theta,phi]

    def _get_field_spherical_clicked(self):
        field_spherical = self.get_field_spherical()
        field_cartesian = self.get_field_cartesian()
        self.sigGotPos.emit(field_spherical, field_cartesian)
    
    def _decrease_B(self,step):
        field_spherical = self.get_field_spherical()
        field_spherical[0] = field_spherical[0] - step
        self.ramp(target_field_polar=field_spherical)

    def _increase_B(self,step):
        field_spherical = self.get_field_spherical()
        field_spherical[0] = field_spherical[0] + step
        self.ramp(target_field_polar=field_spherical)

    def _decrease_theta(self,step):
        field_spherical = self.get_field_spherical()
        field_spherical[1] = field_spherical[1] - step
        self.ramp(target_field_polar=field_spherical)

    def _increase_theta(self,step):
        field_spherical = self.get_field_spherical()
        field_spherical[1] = field_spherical[1] + step
        self.ramp(target_field_polar=field_spherical)

    def _decrease_phi(self,step):
        field_spherical = self.get_field_spherical()
        field_spherical[2] = field_spherical[2] - step
        self.ramp(target_field_polar=field_spherical)

    def _increase_phi(self,step):
        field_spherical = self.get_field_spherical()
        field_spherical[2] = field_spherical[2] + step
        self.ramp(target_field_polar=field_spherical)