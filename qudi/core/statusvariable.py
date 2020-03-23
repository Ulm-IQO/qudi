# -*- coding: utf-8 -*-
"""
StatusVar object for qudi modules to allow storing of application status variables on disk.
These variables get stored during deactivation of qudi modules and loaded back in during activation.

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
top-level directory of this distribution and at
<https://github.com/Ulm-IQO/qudi/>
"""

import copy


class StatusVar:
    """ This class defines a status variable that is loaded before activation and saved after
    deactivation.
    """

    def __init__(self, name=None, default=None, *, constructor=None, representer=None):
        """
        @param name: identifier of the status variable when stored
        @param default: default value for the status variable when a saved version is not present
        @param constructor: constructor function for variable; use for type checks or conversion
        @param representer: representer function for status variable; use for saving conversion
        """
        self.name = name

        self.constructor_function = constructor
        self.representer_function = representer
        self.default = default

    def copy(self, **kwargs):
        """ Create a new instance of StatusVar with copied and updated values.

        @param kwargs: Additional or overridden parameters for the constructor of this class
        """
        newargs = {'name': copy.copy(self.name),
                   'default': copy.copy(self.default),
                   'constructor': self.constructor_function,
                   'representer': self.representer_function}
        newargs.update(kwargs)
        return StatusVar(**newargs)

    def constructor(self, func):
        """ This is the decorator for declaring constructor function for this StatusVar.

        @param func: constructor function for this StatusVar
        @return: return the original function so this can be used as a decorator
        """
        if callable(func):
            self.constructor_function = func
        return func

    def representer(self, func):
        """ This is the decorator for declaring a representer function for this StatusVar.

        @param func: representer function for this StatusVar
        @return: return the original function so this can be used as a decorator
        """
        if callable(func):
            self.representer_function = func
        return func
