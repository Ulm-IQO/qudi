# -*- coding: utf-8 -*-

"""
Interface file for simple data acquisition.

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

Copyright (C) 2015 Jan M. Binder jan.binder@uni-ulm.de
"""

from core.util.customexceptions import InterfaceImplementationError


class SimpleDataInterface():

    _modtype = 'SimpleDataInterface'
    _modclass = 'interface'

    def getData(self):
        """ Return a measured value """
        raise InterfaceImplementationError('SimpleDatsInterface->getData')
        return -1

    def getChannels(self):
        """ Return number of channels for value """
        raise InterfaceImplementationError('SimpleDatsInterface->getChannels')
        return -1
