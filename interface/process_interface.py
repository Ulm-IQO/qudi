# -*- coding: utf-8 -*-

from core.util.customexceptions import InterfaceImplementationError

class ProcessInterface():
    """ A very simple interface to measure a single value.
        Used for PID controll.
    """
    def getProcessValue(self):
        """ Return a measured value """
        raise InterfaceImplementationError('ProcessInterface->getProcessValue')
        return -1

    def getProcessUnit(self):
        """ Return the unit that hte value is measured in as a tuple of ('abreviation', 'full unit name') """
        raise InterfaceImplementationError('ProcessInterface->getProcessUnit')
        return -1
