# -*- coding: utf-8 -*-

from core.util.customexceptions import InterfaceImplementationError


class MotorInterface():

    """ This is the Interface class to define the controls for the simple
        step motor device. The actual hardware implementation might have a
        different amount of axis. Implement each single axis as 'private'
        methods for the hardware class, which get called by the general method.
    """

    def move_rel(self,  axis=None, distance=None):
        """ Moves stage in given direction (relative movement)

        @param string axis: named axis of the motor hardware

        @param float distance: amount of relative movement in SI metric

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MagnetStageInterface>move_rel')
        return -1

    def move_abs(self, axis=None, position=None):
        """ Moves stage to absolute position (absolute movement)

        @param string axis: named axis of the motor hardware
        @param float position: move to absolute position in SI metric

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

    def get_pos(self, axis=None):
        """ Gets current position of the stage arms

        @param string axis: named axis of the motor hardware
        @return float: the position of motor
        """
        raise InterfaceImplementationError('MagnetStageInterface>get_pos')
        return -1

    def get_status(self):
        """ Get the status of the position

        @return int status: status of the stage
        """
        raise InterfaceImplementationError('MagnetStageInterface>get_status')
        return -1

    def calibrate(self, axis=None):
        """ Calibrates the stage.

        After calibration the stage moves to home position which will be the
        zero point for the passed axis.

        @param string axis: named axis of the motor hardware

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MagnetStageInterface>calibrate')
        return -1

    def get_velocity(self, axis=None):
        """ Gets the velocity of the given dimension

        @param string axis: named axis of the motor hardware

        @return float: the velocities in SI.
        """
        raise InterfaceImplementationError('MagnetStageInterface>get_velocity')
        return -1

    def set_velocity(self, axis=None, velocity=None):
        """ Write new value for velocity.

        @param string axis: named axis of the motor hardware
        @param float velocity: velocity, dimension in SI metric

        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MagnetStageInterface>set_velocity')
        return -1
