# -*- coding: utf-8 -*-

"""
Interface file to control processes in PID control.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from core.util.customexceptions import InterfaceImplementationError


class ProcessControlInterface():
    """ A very simple interface to control a single value.
        Used for PID control.
    """

    _modtype = 'ProcessControlInterface'
    _modclass = 'interface'

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

