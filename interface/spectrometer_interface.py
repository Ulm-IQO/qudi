# -*- coding: utf-8 -*-

from core.util.customexceptions import InterfaceImplementationError


class SpectrometerInterface():
    """This is the Interface class to define the controls for the simple
    optical spectrometer.
    """
    def recordSpectrum(self):
        raise InterfaceImplementationError

    def setExposure(self, exposureTime):
        raise InterfaceImplementationError

    def getExposure(self):
        raise InterfaceImplementationError
