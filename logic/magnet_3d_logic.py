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
import time
import datetime

from qtpy import QtCore
from collections import OrderedDict
from core.connector import Connector
from core.pi3_utils import delay
from logic.generic_logic import GenericLogic


class MagnetLogic(GenericLogic):

    # declare connectors
    magnet_3d = Connector(interface='magnet_3d')
    timetagger = Connector(interface='TT')
    savelogic = Connector(interface='SaveLogic')
    optimizerlogic = Connector(interface='OptimizerLogic')
    confocallogic = Connector(interface='ConfocalLogic')


    # create signals internal
    sigScanNextLine = QtCore.Signal()
    sigInitNextPixel = QtCore.Signal()
    sigScanPixel = QtCore.Signal()
    # sigCheckRampDone = QtCore.Signal()
    sigCheckRamp = QtCore.Signal()
    sigRefocusAtZeroRampToZero = QtCore.Signal()
    sigRefocusAtZeroCheckRamp = QtCore.Signal()
    sigRefocusAtZeroRefocus = QtCore.Signal()

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
    sigScanFinished = QtCore.Signal()

    # create signals to optimizer logic
    sigStartOptimizer = QtCore.Signal(list, str)

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
        self.refocus_at_zero_field = False

        # other booleans
        self.refocusInitiatedByLogic = True

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
        self._savelogic = self.savelogic()

        # initialize other logic
        self._optimizerlogic = self.optimizerlogic()
        self._scanninglogic = self.confocallogic()

        #connect signals to hardware
        self.sigPause.connect(self._magnet_3d.pause_ramp)
        self.sigContinue.connect(self._magnet_3d.continue_ramp)
        self.sigRampZero.connect(self._magnet_3d.ramp_to_zero)
        
        # connect signals from hardware
        self._magnet_3d.sigRampFinished.connect(self._ramp_finished)

        # connect signals to optimizer logic
        self.sigStartOptimizer.connect(self._optimizerlogic.start_refocus)

        # connect signals from optimizerlogic
        self._optimizerlogic._sigFinishedAllOptimizationSteps.connect(self._refocus_at_zero_field_optimizer_done)

        #connect signals internally
        self.sigScanNextLine.connect(self._scan_line)
        self.sigInitNextPixel.connect(self._init_pixel)
        self.sigScanPixel.connect(self._scan_pixel)
        # self.sigCheckRampDone.connect(self._check_ramp_done)
        self.sigCheckRamp.connect(self._check_ramp)
        self.sigRefocusAtZeroRampToZero.connect(self._refocus_at_zero_field_ramp_to_zero)
        self.sigRefocusAtZeroCheckRamp.connect(self._refocus_at_zero_field_check_ramp)
        self.sigRefocusAtZeroRefocus.connect(self._refocus_at_zero_field_refocus)
        

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
        self.abort_scan = False
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
            self.ramp_to_zero()
            self.sigScanFinished.emit()
            return 0
        # else go to next line
        else:
            # set pixel counter to 0.
            self._pixel_counter = 0
            # scan first pixel in next line
            if self.refocus_at_zero_field:
                # signal to refocus at zero field
                self.sigRefocusAtZeroRampToZero.emit()
            else:
                # go straight to next pixel
                self.sigInitNextPixel.emit()
    
    
    def _refocus_at_zero_field_ramp_to_zero(self):
        # ramp B to zero
        self.ramp_to_zero()
        self.sigRefocusAtZeroCheckRamp.emit()


    def _refocus_at_zero_field_check_ramp(self):
        """Checks ramp status and acts accordingly.
        
        If ramp is still in progress: wait a bit and then check again (sends signal to itself).
        If ramp is done: sends Signal to start refocus and stops.
        """
        if self.abort_scan:
            return
        status = self._magnet_3d.get_ramping_state()
        if status == [2,2,2] or status == [8,8,8]:
            self.sigRefocusAtZeroRefocus.emit()
            return
        else:
            delay(1)
            self.sigRefocusAtZeroCheckRamp.emit()
            return 


    def _refocus_at_zero_field_refocus(self):
        # start refocus
        # set flag to know that magnetlogic initiated refocus
        self.refocusInitiatedByLogic = True
        crosshair_pos = self._scanninglogic.get_position()
        self.sigStartOptimizer.emit(crosshair_pos, 'magnetlogic')
        # once refocus is done, scanner logic will emit 
        # _sigFinishedAllOptimizationSteps


    def _refocus_at_zero_field_optimizer_done(self):
        # only act, if refocus was initiated by magnet logic.
        # Otherwise this will trigger also on manual refocus from confocal gui.
        if self.refocusInitiatedByLogic:
            self.refocusInitiatedByLogic = False
            self.sigInitNextPixel.emit()


    def _init_pixel(self):
        if self.abort_scan:
            self.scanning_finished = True
            print('stopping the scan')
            return
        # change B field
        B = self.B
        theta = self.thetas[self._line_counter]
        phi = self.phis[self._pixel_counter]
        self.ramp(target_field_polar=[B,theta,phi])
        
        self.sigCheckRamp.emit()
        return

    def _check_ramp(self):
        """Checks ramp status and acts accordingly.
        
        If ramp is still in progress: wait a bit and then check again (sends signal to itself).
        If ramp is done: sends Signal to start next pixel and stops.
        """
        if self.abort_scan:
            return
        status = self._magnet_3d.get_ramping_state()
        if status == [2,2,2]:
            # self.sigCheckRampDone.emit()
            self.sigScanPixel.emit()
            return
        else:
            delay(1)
            self.sigCheckRamp.emit()
            return

    # def _check_ramp(self):
    #     """Checks the ramping state of the magnet and sends signal if all are done.

    #     NOT USED ANYMORE

    #     Also stops the timer.
    #     """
    #     status = self._magnet_3d.get_ramping_state()
    #     if status == [2,2,2]:
    #         self.sigCheckRampDone.emit()
        
    
    # def _check_ramp_done(self):
    #     """Kills the timer and sends signal to scan next pixel.
        
    #     We need a second function that is not inside the event loop to kill the timer.
    #     """
    #     # I think this function serves only the purpose of emitting this signal. 
    #     # Can we move the contents to the function that calls it?
    #     self.sigScanPixel.emit()

    def _scan_pixel(self):
        """Gets countrate for current pixel.
        
        Countrate gets recorded in image matrix.
        """
        # ask TT for countrate
        ctr = self._timetagger.countrate()

        #get countrate every 0.1 s
        delay_time = 0.1
        n_points = round(self.int_time/delay_time)
        if np.isclose(n_points, 0.0):
            # avoid 0 for small integration times
            n_points = 1
        counts = 0
        for i in range(n_points):
            # last position gives sum of both APDs
            counts += ctr.getData()[-1]
            # with delay it is not working, we need to put sleep
            time.sleep(delay_time)
            # delay(delay_time)
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
            return
        # else, go to next pixel
        else:
            if self.refocus_at_zero_field:
                # ramp to zero, refocus and the scan pixel
                self.sigRefocusAtZeroRampToZero.emit()
            else:
                # scan pixel directly
                self.sigInitNextPixel.emit()
            return

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

    def _get_field_clicked(self):
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


    def save_2d_data(self, tag=None, timestamp=None):
        """Saves the data of the 2d magnet scan"""

        # create file and retun path to it
        filepath = self._savelogic.get_path_for_module(module_name='Magnet')

        if timestamp is None:
            timestamp = datetime.datetime.now()

        if tag is not None and len(tag) > 0:
            filelabel = tag + '_magnet_alignment_data'
        else:
            filelabel = 'magnet_alignment_data'

        # prepare the data in a dict or in an OrderedDict:
        matrix_data = OrderedDict()
        matrix_data['Alignment Matrix'] = self.thetaPhiImage

        parameters = OrderedDict()
        parameters['Time at Data save'] = timestamp
        parameters['absolute B field'] = self.B
        parameters['B field units'] = 'Tesla'
        parameters['refocus at zero field'] = self.refocus_at_zero_field
        parameters['theta_min (°)'] = self.theta_min
        parameters['theta_max (°)'] = self.theta_max
        parameters['n_theta'] = self.n_theta
        parameters['phi_min (°)'] = self.phi_min
        parameters['phi_max (°)'] = self.phi_max
        parameters['n_phi'] = self.n_phi
        parameters['thetas (°)'] = self.thetas
        parameters['phis (°)'] = self.phis


        self._savelogic.save_data(matrix_data, filepath=filepath, parameters=parameters,
                                   filelabel=filelabel, timestamp=timestamp)

        # not absolutely necessary, kill it if it breaks anything
        self.log.debug('Magnet 2D data saved to:\n{0}'.format(filepath))

       