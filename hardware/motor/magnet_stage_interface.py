# -*- coding: utf-8 -*-

from core.util.customexceptions import InterfaceImplementationError

class MagnetStageInterface():
    """This is the Interface class to define the controls for the simple 
    magnetstage hardware.
    """
    
    
    def step(self, x = None, y = None, z = None, phi = None):
        """Moves stage in given direction (relative movement)
        
        @param float x: amount of realtive movement in x direction
        @param float y: amount of realtive movement in y direction
        @param float z: amount of realtive movement in z direction
        @param float phi: amount of realtive movement in phi direction
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MagnetStageInterface>step_x')
        return -1
        
    
    def move(self, x = None, y = None, z = None, phi = None):
        """Moves stage to absolute position (absolute movement)
        
        @param float x: move to absolute position in x-direction
        @param float y: move to absolute position in y-direction
        @param float z: move to absolute position in z-direction
        @param float phi: move to absolute position in phi-direction
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MagnetStageInterface>move')
        return -1
    

    def abort(self):
        """Stops movement of the stage
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MagnetStageInterface>abort')
        return -1 
        
    
    def get_pos(self):
        """Gets current position of the stage arms
        
        @return float x: current x stage position
        @return float y: current y stage position
        @return float z: current z stage position
        @return float phi: current phi stage position
        """
        raise InterfaceImplementationError('MWInterface>get_pos')        
        return 0.0, 0.0, 0.0, 0.0
        
     
    def get_status(self):
        """Get the status of the position
        
        @return int status: status of the stage      
        """
        raise InterfaceImplementationError('MWInterface>get_status')
        return -1
        
    #Why not calibrate all together using None    
    def calibrate_x(self):
        """Calibrates the x-direction of the stage. 
        For this it moves to the point zero in x.
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MagnetStageInterface>calibrate_x')
        return -1
            
    
    def calibrate_y(self):
        """Calibrates the y-direction of the stage. 
        For this it moves to the point zero in y.
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MagnetStageInterface>calibrate_y')
        return -1
            
    
    def calibrate_z(self):
        """Calibrates the z-direction of the stage. 
        For this it moves to the point zero in z.
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MagnetStageInterface>calibrate_z')
        return -1
    
            
    def calibrate_phi(self):
        """Calibrates the phi-direction of the stage. 
        For this it turns to the point zero in phi.
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MagnetStageInterface>calibrate_phi')
        return -1
    
    #FIXME: x as default value. See set_velocity below.
    #FIXME: Does returning an array with all velocities simplify this?
    def get_velocity(self, dimension = ''):
        """ Gets the velocity of the given dimension
        
        @param str dimension: name of chosen dimension (x, y, z or phi)
        
        @return float velocity: velocity of chosen dimension
        """
        raise InterfaceImplementationError('MagnetStageInterface>get_velocity')
        return 0.0
        
        #FIXME: vllt hier auch vel_x, vel_y, vel_z, vel_phi ?
        #FIXME: Does NONE make sense here?
    def set_velocity(self, dimension = 'x', vel = None): 
        """Write new value for velocity in chosen dimension
        
        @param str dimension: name of chosen dimension
        @param float vel: velocity for chosen dimension
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MagnetStageInterface>calibrate_z')
        return -1        
