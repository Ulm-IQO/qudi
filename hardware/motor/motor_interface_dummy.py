# -*- coding: utf-8 -*-

"""
This file contains the QuDi hardware interface for fast counting devices.

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

Copyright (C) 2015 Christoph Mueller christoph-1.mueller@uni-ulm.de
Copyright (C) 2015 Jochen Scheuer jochen.scheuer@uni-ulm.de
Copyright (C) 2016 Alexander Stark alexander.stark@uni-ulm.de
"""

from core.base import Base
from interface.motor_interface import MotorInterface
from collections import OrderedDict

class MotorInterfaceDummy(Base, MotorInterface):
    """ This is the dummy class to simulate a motorized stage. """

    _modclass = 'MotorInterfaceDummy'
    _modtype = 'hardware'

    # connectors
    _out = {'magnet': 'MotorInterface'}

   
    def __init__(self, manager, name, config, **kwargs):
        cb = {'onactivate': self.cativation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, cb)
        
        self.logMsg('The following configuration was found.', 
                    msgType='status')
                    
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')

    #TODO: Checks if configuration is set and is reasonable
            
    def activation(self, e):

        # PLEASE REMEMBER: DO NOT CALL THE POSITION SIMPLY self.x SINCE IT IS
        # EXTREMLY DIFFICULT TO SEARCH FOR x GLOBALLY IN A FILE!
        # Same applies to all other axis. I.e. choose more descriptive names. 

        self.x_pos = 0.0
        self.y_pos = 0.0
        self.z_pos = 0.0
        self.phi_pos = 0.0
        self.x_vel = 0.0
        self.y_vel = 0.0
        self.z_vel = 0.0
        self.phi_vel = 0.0
 
    def deactivation(self, e):
        pass

    def move_rel(self,  x=None, y=None, z=None, phi=None):
        """ Moves stage in given direction (relative movement)
        
        @param float x: amount of relative movement in x direction in SI metric
        @param float y: amount of relative movement in y direction in SI metric
        @param float z: amount of relative movement in z direction in SI metric
        @param float phi: amount of relative movement in phi direction in SI metric
        
        @return int: error code (0:OK, -1:error)
        """
        if x is not None:
            self.x_pos += x
        if y is not None:
            self.y_pos += y
        if z is not None:
            self.z_pos += z
        if phi is not None:
            self.phi_pos += phi
        return 0     
    
    def abort(self):
        """Stops movement of the stage
        
        @return int: error code (0:OK, -1:error)
        """
        self.logMsg('MotorInterfaceDummy: Movement stopped!', msgType='status')
        return 0 
        
    def get_pos(self):
        """Gets current position of the stage arms
        
        @return float x: current x stage position
        @return float y: current y stage position
        @return float z: current z stage position
        @return float phi: current phi stage position
        """
        return {'x' : self.x_pos, 'y' : self.y_pos, 
                'z' : self.z_pos, 'phi' : self.phi_pos}
     
    def get_status(self):
        """Get the status of the position
        
        @return int status: status of the stage      
        """
        return 0
    
    def move_abs(self, x=None, y=None, z=None, phi=None):
        """Moves stage to absolute position
        
        @param float x: move to absolute position in x-direction in SI metric
        @param float y: move to absolute position in y-direction in SI metric
        @param float z: move to absolute position in z-direction in SI metric
        @param float phi: move to absolute position in phi-direction in SI metric
        
        @return int: error code (0:OK, -1:error)
        """

        if x is not None:
            self.x_pos = x
        if y is not None:
            self.y_pos = y
        if z is not None:
            self.z_pos = z
        if phi is not None:
            self.phi_pos = phi
        return 0 
        
    def calibrate(self, x=False, y=False, z=False, phi=False):
        """ Calibrates the stage. 

        After calibration the stage moves to home position which will be the 
        zero point for the passed axis.
        
        @return int: error code (0:OK, -1:error)
        """
        if x:
            self.x_pos = 0.0
        if y:
            self.y_pos = 0.0
        if z:
            self.z_pos = 0.0
        if phi:
            self.phi_pos = 0.0
        return 0
    
    def get_velocity(self):
        """ Gets the velocity of the given dimension
        
        @return dict:  dictionary with keys denoting the velocities and the 
                       items representing their value. Always in SI.
        """

        return {'x_vel' : self.x_vel, 'y_vel' : self.y_vel,
                'z_vel' : self.z_vel, 'phi_vel' : self.phi_vel}
        
    def set_velocity(self, x_vel=None, y_vel=None, z_vel=None, phi_vel=None): 
        """Write new value for velocity.

        @param float x_vel: velocity for x direction, dimension in SI metric
        
        @return int: error code (0:OK, -1:error)
        """
        if x_vel is not None:
            self.x_vel = x_vel
        if y_vel is not None:
            self.y_vel = y_vel
        if z_vel is not None:
            self.z_vel = z_vel
        if phi_vel is not None:
            self.phi_vel = phi_vel
        return 0 

