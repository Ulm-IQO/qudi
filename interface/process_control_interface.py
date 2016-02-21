# -*- coding: utf-8 -*-

from core.util.customexceptions import InterfaceImplementationError

class ProcessControlInterface():
    """ A very simple interface to control a single value.
        Used for PID control.
    """
    def setControlValue(self, value):
        """ Set the value of the controlled process variable """
        raise InterfaceImplementationError('ProcessInterface->setControlValue')
        return -1

    def getControlValue(self):
        """ Get the value of the controlled process variable """
        raise InterfaceImplementationError('ProcessInterface->setControlValue')
        return -1

    def getControlUnit(self):
        """ Return the unit that the value is set in as a tuple of ('abreviation', 'full unit name') """
        raise InterfaceImplementationError('ProcessControlInterface->getControlUnit')
        return -1

    def getControlLimits(self):
        """ Return limits within which the controlled value can be set as a tuple of (low limit, high limit)
        """
        raise InterfaceImplementationError('ProcessControlInterface->getControlLimits')
        return -1

