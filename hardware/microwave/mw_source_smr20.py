# -*- coding: utf-8 -*-

"""
This file contains the QuDi Hardware module for Rohde and Schwary SMR20.

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

import visa
import numpy as np

from core.base import Base
from interface.microwave_interface import MicrowaveInterface


class MicrowaveSMR20(Base, MicrowaveInterface):
    """ The hardware control for the device Rohde and Schwarz SMR 20.

    For additional information concerning the commands to communicate via the
    GPIB connection through visa, please have a look at:

    http://cdn.rohde-schwarz.com/pws/dl_downloads/dl_common_library/dl_manuals/gb_1/s/smr_1/smr_20-40.pdf
    """

    _modclass = 'MicrowaveSMR20'
    _modtype = 'hardware'

    ## declare connectors
    _out = {'MWSourceSMR20': 'MicrowaveInterface'}

    def __init__(self, manager, name, config = {}, **kwargs):
        cb = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, cb)

    def activation(self, e):
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
            self.logMsg('MicrowaveSMR20: did not find parameter '
                        '>>gpib_address<< in configuration.', msgType='error')

        if 'gpib_timeout' in config.keys():
            self._gpib_timeout = int(config['gpib_timeout'])
        else:
            self._gpib_timeout = 10
            self.logMsg('MicrowaveSMR20: did not find >>gpib_timeout<< in '
                        'configration. It will be set to {0} '
                        'seconds.'.format(self._gpib_timeout),
                        msgType='error')

        # trying to load the visa connection to the module
        self.rm = visa.ResourceManager()
        try:
            self._gpib_connection = self.rm.open_resource(self._gpib_address,
                                                          timeout=self._gpib_timeout)
            #self._gpib_connection.term_chars = "\r\n"

            self.logMsg('MicrowaveSMR20: initialised and connected to '
                        'hardware.', msgType='status')
        except:
             self.logMsg('MicrowaveSMR20: could not connect to the GPIB '
                         'address >>{0}<<.'.format(self._gpib_address),
                         msgType='error')

        # set manually the number of entries in a list, the explanation for that
        # procedure is in the function self.set_list.
        self._num_list_entries = 4000

    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """

        self.off()  # turn the device off in case it is running
        self._gpib_connection.close()
        self.rm.close()

    def on(self):
        """ Switches on any preconfigured microwave output.

        @return int: error code (0:OK, -1:error)
        """
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':OUTP ON')


        return 0

    def off(self):
        """ Switches off any microwave output.

        @return int: error code (0:OK, -1:error)
        """

        self._gpib_connection.write('*WAI')
        if self._gpib_connection.ask(':FREQ:MODE?') == 'LIST':
            self._gpib_connection.write(':FREQ:MODE CW')
        self._gpib_connection.write(':OUTP OFF')


        return 0

    def get_power(self):
        """ Gets the microwave output power.

        @return float: the power set at the device in dBm
        """
        self._gpib_connection.write('*WAI')
        return float(self._gpib_connection.ask(':POW?'))

    def set_power(self, power):
        """ Sets the microwave output power.

        @param float power: the power (in dBm) set for this device

        @return int: error code (0:OK, -1:error)
        """

        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':POW {:f};'.format(power))
        return 0

    def get_frequency(self):
        """ Gets the frequency of the microwave output.

        @return float: frequency (in Hz), which is currently set for this device
        """

        self._gpib_connection.write('*WAI')
        return float(self._gpib_connection.ask(':FREQ?'))

    def set_frequency(self, freq):
        """ Sets the frequency of the microwave output.

        @param float freq: the frequency (in Hz) set for this device

        @return int: error code (0:OK, -1:error)
        """

        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':FREQ {:e}'.format(freq))
        # {:e} meens a representation in float with exponential style
        return 0

    def set_cw(self, freq=None, power=None, useinterleave=None):
        """ Sets the MW mode to cw and additionally frequency and power

        @param float freq: frequency to set in Hz
        @param float power: power to set in dBm
        @param bool useinterleave: If this mode exists you can choose it.

        @return int: error code (0:OK, -1:error)

        Interleave option is used for arbitrary waveform generator devices.
        """

        self._gpib_connection.write(':FREQ:MODE CW')

        if freq != None:
            self.set_frequency(freq)

        if power != None:
            self.set_power(power)

        self.on()

        return 0

    def set_list(self, freq=None, power=None):
        """ Sets the MW mode to list mode

        @param list freq: list of frequencies in Hz
        @param float power: MW power of the frequency list in dBm

        @return int: error code (0:OK, -1:error)
        """

        error = 0

        if self.set_cw(freq[0],power) != 0:
            self.logMsg('The frequency list has an invalide first frequency '
                        'and power, which cannot be set.', msgType='error')
            error = -1

        # Bug in the micro controller of SMR20:
        # check the amount of entries, since the timeout is not working properly
        # and the SMR20 overwrites for too big entries the device-internal
        # memory such that the current firmware becomes corrupt. That is an
        # extreme annoying bug. Therefore catch too long lists.

        if len(freq)> self._num_list_entries:
            self.logMsg('The frequency list exceeds the hardware limitation of '
                        '{0} list entries. Aborting creation of a list due to '
                        'potential overwrite of the firmware on the '
                        'device.'.format(self._num_list_entries),
                        msgType='error')
            return -1

        self._gpib_connection.write(':SOUR:LIST:MODE STEP')
        self._gpib_connection.write('*WAI')


        # It seems that we have to set a DWEL for the device, but it is not so
        # clear why it is necessary. At least there was a hint in the manual for
        # that:
        self._gpib_connection.write(':SOUR:LIST:DWEL')
        self._gpib_connection.write('*WAI')


        self._gpib_connection.write(':SOUR:LIST:DEL:ALL')
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(":SOUR:LIST:SEL 'ODMR'")
        FreqString = ''
        PowerString = ''

        for f in freq[:-1]:
            FreqString += ' {:f}Hz,'.format(f)
            PowerString +=' {:f}dBm,'.format(power)
        FreqString += ' {:f}Hz'.format(freq[-1])
        PowerString +=' {:f}dBm'.format(power)

        self._gpib_connection.write(':SOUR:LIST:FREQ' + FreqString)
        self._gpib_connection.write('*WAI')

        self._gpib_connection.write(':SOUR:LIST:POW' + PowerString)

        # It seems that we have to set a DWEL for the device, but it is not so
        # clear why it is necessary. At least the instrument displays an error,
        # when this parameter is not set in the list mode (even it should be
        # set by default):
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':OUTP:AMOD FIX')

        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':TRIG1:LIST:SOUR EXT')
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':TRIG1:SLOP NEG')
        self._gpib_connection.write('*WAI')

        N = int(np.round(float(self._gpib_connection.ask(':SOUR:LIST:FREQ:POIN?'))))

        if N != len(freq):
            error = -1
            self.logMsg('The input Frequency list does not corresponds to the '
                        'generated List from the SMR20.', msgType='error')

        return error

    def reset_listpos(self):
        """ Reset of MW List Mode position to start from first given frequency

        @return int: error code (0:OK, -1:error)
        """
        # self._gpib_connection.write('*WAI')
        # self._gpib_connection.write(':FREQ:MODE CW')
        # self._gpib_connection.write('*WAI')
        # self._gpib_connection.write(':FREQ:MODE LIST')

        self._gpib_connection.write(':ABOR:LIST')

        return 0

    def list_on(self):
        """ Switches on the list mode.

        @return int: error code (0:OK, -1:error)
        """
        self._gpib_connection.write(':LIST:LEAR')
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':FREQ:MODE LIST')
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':OUTP ON')

        return 0

    def turn_AM_on(self, depth):
        """ Turn on the Amplitude Modulation mode.

        @param float depth: modulation depth in percent (from 0 to 100%).

        @return int: error code (0:OK, -1:error)

        Set the Amplitude modulation based on an external DC signal source and
        switch on the device after configuration.
        """
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write('AM:SOUR EXT')
        self._gpib_connection.write('AM:EXT:COUP DC')
        self._gpib_connection.write('AM {:f}'.format(float(depth)))
        self._gpib_connection.write('AM:STAT ON')

        return 0

    def turn_AM_off(self):
        """ Turn off the Amlitude Modulation Mode.

        @return int: error code (0:OK, -1:error)
        """

        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':AM:STAT OFF')

        return 0

    def set_ex_trigger(self, source, pol):
        """ Set the external trigger for this device with proper polarization.

        @param str source: channel name, where external trigger is expected.
        @param str pol: polarisation of the trigger (basically rising edge or
                        falling edge)

        @return int: error code (0:OK, -1:error)
        """
        #FIXME: make here the external trigger settings!
        return 0

    def reset_device(self):
        """ Resets the device and sets the default values."""
        self._gpib_connection.write(':SYSTem:PRESet')
        self._gpib_connection.write('*RST')
        self._gpib_connection.write(':OUTP OFF')

        return 0