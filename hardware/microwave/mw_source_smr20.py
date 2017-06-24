# -*- coding: utf-8 -*-

"""
This file contains the Qudi Hardware module for Rohde and Schwary SMR20.

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
import numpy as np

from core.module import Base, ConfigOption
from interface.microwave_interface import MicrowaveInterface
from interface.microwave_interface import MicrowaveLimits
from interface.microwave_interface import MicrowaveMode
from interface.microwave_interface import TriggerEdge


class MicrowaveSMR20(Base, MicrowaveInterface):
    """ The hardware control for the device Rohde and Schwarz SMR 20.

    For additional information concerning the commands to communicate via the
    GPIB connection through visa, please have a look at:

    http://cdn.rohde-schwarz.com/pws/dl_downloads/dl_common_library/dl_manuals/gb_1/s/smr_1/smr_20-40.pdf
    """

    _modclass = 'MicrowaveSMR20'
    _modtype = 'hardware'

    _gpib_address = ConfigOption('gpib_address', missing='error')
    _gpib_timeout = ConfigOption('gpib_timeout', 10, missing='warn')

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # trying to load the visa connection to the module
        self.rm = visa.ResourceManager()
        try:
            self._gpib_connection = self.rm.open_resource(
                self._gpib_address,
                timeout=self._gpib_timeout)
            #self._gpib_connection.term_chars = "\r\n"

            self.log.info('MicrowaveSMR20: initialised and connected to '
                        'hardware.')
        except:
             self.log.error('MicrowaveSMR20: could not connect to the GPIB '
                         'address >>{0}<<.'.format(self._gpib_address))

        # set manually the number of entries in a list, the explanation for that
        # procedure is in the function self.set_list.
        self._MAX_LIST_ENTRIES = 4000

        self._gpib_connection.write('*WAI')
        self._FREQ_MAX = float(self._gpib_connection.ask('FREQuency? MAX'))
        self._FREQ_MIN = float(self._gpib_connection.ask('FREQuency? MIN'))
        self._POWER_MAX = float(self._gpib_connection.ask('POWER? MAX'))
        self._POWER_MIN = float(self._gpib_connection.ask('POWER? MIN'))

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """

        self.off()  # turn the device off in case it is running
        self._gpib_connection.close()
        self.rm.close()


    def get_limits(self):
        """ Retrieve the limits of the device.

        @return: object MicrowaveLimits: Serves as a container for the limits
                                         of the microwave device.
        """

        limits = MicrowaveLimits()

        identify = self._gpib_connection.query('*IDN?')
        # split the comma separted options and out the entries in an array:
        identify = identify.strip().split(',')

        opts = self._gpib_connection.query('*OPT?')

        # split the comma separted options and out the entries in an array:
        opts = opts.strip().split(',')

        limits.supported_modes = (MicrowaveMode.CW, MicrowaveMode.LIST,
                                  MicrowaveMode.SWEEP)

        # the extended frequency option
        if 'B11' in opts:
            limits.min_frequency = 10e6
        else:
            limits.min_frequency = 1e9

        if 'SMR20' in identify:
            limits.max_frequency = 20e9
        elif 'SMR27' in identify:
            limits.max_frequency = 27e9
        elif 'SMR30' in identify:
            limits.max_frequency = 30e9
        elif 'SMR40' in identify:
            limits.max_frequency = 40e9
        else:
            self.error('The SMR device is not of the types '
                       '"R&S SMR20 or SMR27 or SMR30 or SMR40"! Could not '
                       'determine the maximal frequency limit. Set it just to '
                       '10GHz as default. Please check the device type and the '
                       'maximal frequency for your device!')


        limits.min_power = -130
        limits.max_power = 13

        # FIXME: Not quite sure about this:
        limits.list_minstep = limits.min_frequency
        limits.list_maxstep = limits.max_frequency
        limits.list_maxentries = 2003

        # FIXME: Not quite sure about this:
        limits.sweep_minstep = limits.min_frequency
        limits.sweep_maxstep = limits.max_frequency
        limits.sweep_maxentries = 10001
        return limits

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
        self._gpib_connection.write(':POW {0:f};'.format(power))
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
        self._gpib_connection.write(':FREQ {0:e}'.format(freq))
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

        if freq is not None:
            self.set_frequency(freq)

        if power is not None:
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
            self.log.error('The frequency list has an invalide first '
                    'frequency and power, which cannot be set.')
            error = -1

        # Bug in the micro controller of SMR20:
        # check the amount of entries, since the timeout is not working properly
        # and the SMR20 overwrites for too big entries the device-internal
        # memory such that the current firmware becomes corrupt. That is an
        # extreme annoying bug. Therefore catch too long lists.

        if len(freq)> self._MAX_LIST_ENTRIES:
            self.log.error('The frequency list exceeds the hardware '
                    'limitation of {0} list entries. Aborting creation of a '
                    'list due to potential overwrite of the firmware on the '
                    'device.'.format(self._MAX_LIST_ENTRIES))
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
            FreqString += ' {0:f}Hz,'.format(f)
            PowerString +=' {0:f}dBm,'.format(power)
        FreqString += ' {0:f}Hz'.format(freq[-1])
        PowerString +=' {0:f}dBm'.format(power)

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
            self.log.error('The input Frequency list does not corresponds to '
                    'the generated List from the SMR20.')

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
        self._gpib_connection.write('AM {0:f}'.format(float(depth)))
        self._gpib_connection.write('AM:STAT ON')

        return 0

    def turn_AM_off(self):
        """ Turn off the Amlitude Modulation Mode.

        @return int: error code (0:OK, -1:error)
        """

        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':AM:STAT OFF')

        return 0

    def set_ext_trigger(self, pol=TriggerEdge.RISING):
        """ Set the external trigger for this device with proper polarization.

        @param TriggerEdge pol: polarisation of the trigger (basically rising edge or
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

    def get_limits(self):
        """ Return the device-specific limits in a nested dictionary.

          @return MicrowaveLimits: limits object
        """
        limits = MicrowaveLimits()
        limits.supported_modes = (MicrowaveMode.CW, MicrowaveMode.LIST)

        limits.min_frequency = self._FREQ_MIN
        limits.max_frequency = self._FREQ_MAX

        limits.min_power = self._POWER_MIN
        limits.max_power = self._POWER_MAX

        limits.list_minstep = 0.1
        limits.list_maxstep = 6.4e9
        limits.list_maxentries = self._MAX_LIST_ENTRIES

        limits.sweep_minstep = 0.1
        limits.sweep_maxstep = 10e9
        limits.sweep_maxentries = 10e6

        return limits

    def sweep_on(self):
        """ Switches on the sweep mode.

        @return int: error code (0:OK, -1:error)
        """
        return -1

    def set_sweep(self, start, stop, step, power):
        """ Sweep from frequency start to frequency sto pin steps of width stop with power.
        """
        return -1

    def reset_sweep(self):
        """ Reset of MW sweep position to start

        @return int: error code (0:OK, -1:error)
        """
        return -1
