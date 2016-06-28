# -*- coding: utf-8 -*-
"""
Interface for a spectrometer.

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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

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
