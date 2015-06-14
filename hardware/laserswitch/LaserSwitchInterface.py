# -*- coding: utf-8 -*-

from core.util.CustomExceptions import InterfaceImplementationError

class LaserSwitchInterface():
    """ Methods to control slow laser switching devices.
    """

    def getNumberOfSwitches(self):
        """
        """
        raise InterfaceImplementationError('LaserSwitchInterface: getNumberOfSwitches')
        return -1

    def getSwitchState(self, switchNumber):
        """
        """
        raise InterfaceImplementationError('LaserSwitchInterface: getNumberOfSwitches')
        return -1

    def getCalibration(self, switchNumber, state):
        """
        """
        raise InterfaceImplementationError('LaserSwitchInterface: getNumberOfSwitches')
        return -1

    def setCalibration(self, switchNumber, state, value):
        """
        """
        raise InterfaceImplementationError('LaserSwitchInterface: getNumberOfSwitches')
        return -1

    def switchOn(self):
        """
        """
        raise InterfaceImplementationError('LaserSwitchInterface: getNumberOfSwitches')
        return -1
    
    def switchOff(self):
        """
        """
        raise InterfaceImplementationError('LaserSwitchInterface: getNumberOfSwitches')
        return -1

