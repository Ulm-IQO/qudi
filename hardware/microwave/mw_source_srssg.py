# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware file to control SRS SG390 devices.

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


import visa

from core.base import Base
from interface.microwave_interface import MicrowaveInterface
from interface.microwave_interface import MicrowaveLimits
from interface.microwave_interface import MicrowaveMode
from interface.microwave_interface import TriggerEdge

class MicrowaveSRSSG(Base, MicrowaveInterface):
    """ Hardware control class to controls SRS SG390 devices.  """

    _modclass = 'MicrowaveSRSSG'
    _modtype = 'interface'

    _out = {'mwsourcesrssg': 'MicrowaveInterface'}

    def on_activate(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """

        # checking for the right configuration
        config = self.getConfiguration()
        if 'gpib_address' in config.keys():
            self._gpib_address = config['gpib_address']
        else:
            self.log.error(
                'This is MW SRS SG: did not find >>gpib_address<< in '
                'configration.')

        if 'gpib_timeout' in config.keys():
            self._gpib_timeout = int(config['gpib_timeout'])*1000
        else:
            self._gpib_timeout = 10*1000
            self.log.error(
                'This is MW SRS SG: did not find >>gpib_timeout<< in '
                'configration. I will set it to 10 seconds.')

        # trying to load the visa connection to the module
        self.rm = visa.ResourceManager()
        try:
            self._gpib_connection = self.rm.open_resource(self._gpib_address,
                                                          timeout=self._gpib_timeout)
        except:
            self.log.error(
                'This is MW SRS SG: could not connect to the GPIB '
                'address >>{}<<.'.format(self._gpib_address))
            raise

        self.log.info('MW SRS SG initialised and connected to hardware.')
        self.model = self._gpib_connection.query('*IDN?').split(',')[1]

    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """

        self._gpib_connection.close()
        self.rm.close()

