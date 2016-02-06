# -*- coding: utf-8 -*-

from core.util.customexceptions import InterfaceImplementationError

class MotorInterface():
    """ This is the Interface class to define the controls for the simple 
        step motor device. The actual hardware implementation might have a 
        different amount of axis. Implement each single axis as 'private'
        methods for the hardware class, which get called by the general method.
    """

    def move_rel(self,  x=None, y=None, z=None, phi=None):
        """ Moves stage in given direction (relative movement)
        
        @param float x: amount of relative movement in x direction in SI metric
        @param float y: amount of relative movement in y direction in SI metric
        @param float z: amount of relative movement in z direction in SI metric
        @param float phi: amount of relative movement in phi direction in SI metric
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MagnetStageInterface>move_rel')
        return -1

    def move_abs(self, x=None, y=None, z=None, phi=None):
        """ Moves stage to absolute position (absolute movement)
        
        @param float x: move to absolute position in x-direction in SI metric
        @param float y: move to absolute position in y-direction in SI metric
        @param float z: move to absolute position in z-direction in SI metric
        @param float phi: move to absolute position in phi-direction in SI metric

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MagnetStageInterface>move_abs')
        return -1

    def abort(self):
        """ Stops movement of the stage
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MagnetStageInterface>abort')
        return -1 
        
    def get_pos(self):
        """ Gets current position of the stage arms
        
        @return dict: a dictionary with four entries. Each value can be 
                      retrieved by the specific key.
        """
        raise InterfaceImplementationError('MagnetStageInterface>get_pos')        
        return {'x' : 0.0, 'y' : 0.0, 'z' : 0.0, 'phi' : 0.0}
        
    def get_status(self):
        """ Get the status of the position
        
        @return int status: status of the stage      
        """
        raise InterfaceImplementationError('MagnetStageInterface>get_status')
        return -1
          
    def calibrate(self, x=False, y=False, z=False, phi=False):
        """ Calibrates the stage. 

        After calibration the stage moves to home position which will be the 
        zero point for the passed axis.
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MagnetStageInterface>calibrate')
        return -1
            
    def get_velocity(self):
        """ Gets the velocity of the given dimension
        
        @return dict:  dictionary with keys denoting the velocities and the 
                       items representing their value. Always in SI.
        """
        raise InterfaceImplementationError('MagnetStageInterface>get_velocity')
        return {'x_vel' : 0.0, 'y_vel' : 0.0, 'z_vel' : 0.0, 'phi_vel' : 0.0}
        
    def set_velocity(self, x_vel=None, y_vel=None, z_vel=None, phi_vel=None): 
        """ Write new value for velocity.

        @param float x_vel: velocity for x direction, dimension in SI metric
        @param float y_vel: velocity for y direction, dimension in SI metric
        @param float z_vel: velocity for z direction, dimension in SI metric
        @param float phi_vel: velocity for phi direction, dimension in SI metric
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MagnetStageInterface>set_velocity')
        return -1        
