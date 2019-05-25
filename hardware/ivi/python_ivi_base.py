# -*- coding: utf-8 -*-
"""
This file contains the base class for all pythonIVI library interfaces.

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

from core.module import Base, ConfigOption
import importlib


class PythonIviBase(Base):
    """
    Base class for connecting to hardware via PythonIVI library.

    Config options:
    - driver : str module.class name of driver within the python IVI library
                   e.g. 'ivi.tektronix.tektronixAWG5000.tektronixAWG5002c'
    - uri : str unique remote identifier used to connect to instrument.
                e.g. 'TCPIP::192.168.1.1::INSTR'
    """

    driver_config = ConfigOption('driver', missing='error')
    uri = ConfigOption('uri', missing='error')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._driver_module = None
        self._driver_class = None
        self.driver = None

    def on_activate(self):
        """
        Event handler called when module is activated.

        Opens connection to instrument.
        """

        # load driver package
        module_name, class_name = self.driver_config.rsplit('.', 1)
        self._driver_module = importlib.import_module(module_name)

        # instantiate class and connect to scope
        self._driver_class = getattr(self._driver_module, class_name)
        self.driver = self._driver_class(self.uri)

    def on_deactivate(self):
        """
        Event handler called when module is deactivated.

        Closes connection to instrument.
        """
        if self.driver is not None:
            self.driver.close()
            self.driver = None
        self._driver_class = None
        self._driver_module = None