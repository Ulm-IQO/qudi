# -*- coding: utf-8 -*-

from core.util.customexceptions import InterfaceImplementationError

class SimpleDataInterface():

    def getData(self):
        """ Return a measured value """
        raise InterfaceImplementationError('SimpleDatsInterface->getData')
        return -1

    def getChannels(self):
        """ Return number of channels for value """
        raise InterfaceImplementationError('SimpleDatsInterface->getChannels')
        return -1
