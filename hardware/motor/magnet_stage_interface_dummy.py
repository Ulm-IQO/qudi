# -*- coding: utf-8 -*-

from core.base import Base
from hardware.magnet.magnet_stage_interface import MagnetStageInterface
from collections import OrderedDict

class MagnetStageDummy(Base,MagnetStageInterface):
    """This is the dummy class for the magent stage interface.
    """
    _modclass = 'MagnetStageInterface'
    _modtype = 'hardware'

    # connectors
    _out = {'magnet': 'MagnetStageInterface'}

   
    def __init__(self, manager, name, config, **kwargs):
        cb = {'onactivate': self.cativation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, cb)
        
        self.logMsg('The following configuration was found.', 
                    msgType='status')
                    
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')

#       TODO: here there should be checks if configuration is set and sensible
            
    def activation(self, e):
        x = 0.0
        y = 0.0
        z = 0.0
        phi = 0.0
        vel_x = 0.0
        vel_y = 0.0
        vel_z = 0.0
        vel_phi = 0.0
 
    def deactivation(self, e):
        pass

    def step_x(self, step = 0.0):
        """Moves stage in x-direction
        
        @param float step: amount of realtive movement
        
        @return int: error code (0:OK, -1:error)
        """
        self.x += step
        return 0
    
    def step_y(self, step = 0.0):
        """Moves stage in y-direction
        
        @param float step: amount of realtive movement
        
        @return int: error code (0:OK, -1:error)
        """
        self.y += step
        return 0
    
    def step_z(self, step = 0.0):
        """Moves stage in z-direction
        
        @param float step: amount of realtive movement
        
        @return int: error code (0:OK, -1:error)
        """
        self.z += step
        return 0
    
    def step_phi(self, step = 0.0):
        """Turns stage around angle phi
        
        @param float step: amount of realtive movement
        
        @return int: error code (0:OK, -1:error)
        """
        self.phi += step
        return 0         
    
    def abort(self):
        """Stops movement of the stage
        
        @return int: error code (0:OK, -1:error)
        """
        print('stage stopped')
        return 0 
        
    def get_pos(self):
        """Gets current position of the stage arms
        
        @return float x: current x stage position
        @return float y: current y stage position
        @return float z: current z stage position
        @return float phi: current phi stage position
        """
        return self.x, self.y, self.z, self.phi
     
    def get_status(self):
        """Get the status of the position
        
        @return int status: status of the stage      
        """
        return 0
    
    def move(self, x = 0.0, y = 0.0, z = 0.0, phi = 0.0):
        """Moves stage to absolute position
        
        @param float x: move to absolute position in x-direction
        @param float y: move to absolute position in y-direction
        @param float z: move to absolute position in z-direction
        @param float phi: move to absolute position in phi-direction
        
        @return int: error code (0:OK, -1:error)
        """
        self.x = x
        self.y = y
        self.z = z
        self.phi = phi
        return 0
        
    def calibrate_x(self):
        """Calibrates the x-direction of the stage. 
        For this it moves to the point zero in x.
        
        @return int: error code (0:OK, -1:error)
        """
        self.x = 0.0
        return 0
    
    def calibrate_y(self):
        """Calibrates the y-direction of the stage. 
        For this it moves to the point zero in y.
        
        @return int: error code (0:OK, -1:error)
        """
        self.y = 0.0
        return 0
    
    def calibrate_z(self):
        """Calibrates the z-direction of the stage. 
        For this it moves to the point zero in z.
        
        @return int: error code (0:OK, -1:error)
        """
        self.z = 0.0
        return 0
            
    def calibrate_phi(self):
        """Calibrates the phi-direction of the stage. 
        For this it turns to the point zero in phi.
        
        @return int: error code (0:OK, -1:error)
        """
        self.phi = 0.0
        return 0
    
    def get_velocity(self, dimension = 'x'):
        """ Gets the velocity of the given dimension
        
        @param str dimension: name of chosen dimension
        
        @return float velocity: velocity of chosen dimension
        """
        if dimension == 'x':
            vel = self.vel_x
        elif dimension == 'y':
            vel = self.vel_y
        elif dimension == 'z':
            vel = self.vel_z
        elif dimension == 'phi':
            vel = self.vel_phi
        return vel
        
    def set_velocity(self, dimension = 'x', vel = 0.0):
        """Write new value for velocity in chosen dimension
        
        @param str dimension: name of chosen dimension
        @param float vel: velocity for chosen dimension
        
        @return int: error code (0:OK, -1:error)
        """
        if dimension == 'x':
            self.vel_x = vel
        elif dimension == 'y':
            self.vel_y = vel
        elif dimension == 'z':
            self.vel_z = vel
        elif dimension == 'phi':
            self.vel_phi = vel
        return 0 

