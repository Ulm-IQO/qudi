# -*- coding: utf-8 -*-
"""
ConfigOption object to be used in qudi modules. The value of each ConfigOption can
(if it has a default value) or must be specified by the user in the config file.
Usually these values should be constant for the duration of a qudi session.

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
from enum import Enum


class MissingOption(Enum):
    """ Representation for missing ConfigOption """
    error = -3
    warn = -2
    info = -1
    nothing = 0


class ConfigOption:
    """ This class represents a configuration entry in the config file that is loaded before
        module initalisation.
    """

    def __init__(self, name=None, default=None, *, var_name=None, missing='nothing',
                 constructor=None, checker=None, converter=None):
        """ Create a ConfigOption object.

            @param name: identifier of the option in the configuration file
            @param default: default value for the case that the option is not set
                in the config file
            @param var_name: name of the variable inside a running module. Only set this
                if you know what you are doing!
            @param missing: action to take when the option is not set. 'nothing' does nothing,
                'warn' logs a warning, 'error' logs an error and prevents the module from loading
            @param constructor: constructor function for complex config option behaviour
            @param checker: static function that checks if value is ok
            @param converter: static function that forces type interpretation
        """
        self.missing = MissingOption[missing]
        self.var_name = var_name
        if name is None:
            self.name = var_name
        else:
            self.name = name

        self.default = default
        self.constructor_function = constructor
        self.checker = checker
        self.converter = converter

    def copy(self, **kwargs):
        """ Create a new instance of ConfigOption with copied values and update

            @param kwargs: extra arguments or overrides for the constructor of this class
        """
        newargs = {'name': copy.copy(self.name), 'default': copy.copy(self.default),
                   'var_name': copy.copy(self.var_name), 'missing': copy.copy(self.missing.name),
                   'constructor': self.constructor_function, 'checker': self.checker, 'converter': self.converter}
        newargs.update(kwargs)
        return ConfigOption(**newargs)

    def check(self, value):
        """ If checker function set, check value. Else assume everything is ok.
        """
        if callable(self.checker):
            return self.checker(value)
        else:
            return True

    def convert(self, value):
        """ If converter function set, convert value. Needs to raise exception on error.

            @param value: value to convert (or not)

            @return: converted value (or passthrough)
        """
        if callable(self.converter):
            return self.converter(value)
        else:
            return value

    def constructor(self, func):
        """ This is the decorator for declaring a constructor function for this ConfigOption.

            @param func: constructor function for this ConfigOption
            @return: return the original function so this can be used as a decorator
        """
        if callable(func):
            self.constructor_function = func
        return func