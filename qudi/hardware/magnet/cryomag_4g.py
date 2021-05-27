# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware file to control Cryomagnetics 4G Magnet Power Supplies.

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
from qudi.core.configoption import ConfigOption
from qudi.interface.magnet_interface import MagnetInterface

class Cryomag4G(MagnetInterface):
    """
     Hardware class for Cryomagnetics 4G Magnet Power Supply.

    Example config for copy-paste:

    cryomag_4g:
        module.Class: 'magnet.cryomag_4g.Cryomag4G'
    """

    _visa_address = ConfigOption('visa_address', missing='error')
    _comm_timeout = ConfigOption('comm_timeout', default=10, missing='warn')
    _visa_baud_rate = ConfigOption('visa_baud_rate', default=None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._rm = None
        self._device = None
        self._model = ''
        self._constraints = None

    def on_activate(self):
        """Initialization of the Hardware during activation of the module"""
        self._rm = visa.ResourceManager()
        if self._visa_baud_rate is None:
            self._device = self._rm.open_resource(self._visa_address,
                                                  timeout=self._comm_timeout,
                                                  write_termination = '\n',
                                                  read_termination = '\n')
        else:
            self._device = self._rm.open_resource(self._visa_address,
                                                  timeout=self._comm_timeout,
                                                  baud_rate=self._visa_baud_rate,
                                                  write_termination = '\n',
                                                  read_termination = '\n')

        self._model = self._device.query('*IDN?').split(',')[1]
        # Reset device
        self.write('*CLS')
        self.write('*RST')


    def on_deactivate(self):
        """ Cleanup performed during deactivation of the module. """
        self._device.close()
        self._rm.close()
        self._device = None
        self._rm = None

    @property
    def constraints(self):
        """The magnet constraints object for this device.

               @return MagnetConstraints:
        """
        return self._constraints

    @abstractmethod
    def get_optional_setings(self):
        raise NotImplementedError

    @abstractmethod
    def set_optional_settings(self):
        raise NotImplementedError

    @abstractmethod
    def get_axis_value(self, axis):
        if self._model == 'APS100':
            mag_current = self.query('IMAG?').split(',')[0]
            return mag_current
        elif self._model == 'APS200':
            self.write('CHAN {0}'.format(axis))
            mag_current = self.query('IMAG?').split(',')[0]
            return mag_current

    @abstractmethod
    def set_axis_value(self):
        raise NotImplementedError

    @abstractmethod
    def calibrate(self):
        raise NotImplementedError

    @abstractmethod
    def abort(self):
        """ Stops movement or the actual current sweep """

        raise NotImplementedError

    @abstractmethod
    def get_status(self):
        raise NotImplementedError

######################### Hardware Intern Methods #############################

    def query(self, text):
        return self._device.query(text)

    def write(self, text):
        """ Writes the command in text via PyVisa and waits until the device has finished
        processing it.

        @param str text: The command to be written
        """
        self._device.write(text)
        self._device.write('*WAI')
        while int(float(self._device.query('*OPC?'))) != 1:
            time.sleep(0.2)