# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware file to control SMIQ microwave device.

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

Parts of this file were developed from a PI3diamond module which is
Copyright (C) 2009 Helmut Rathgen <helmut.rathgen@gmail.com>

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import visa
import numpy as np

from core.base import Base
from interface.microwave_interface import MicrowaveInterface
from interface.microwave_interface import MicrowaveLimits
from interface.microwave_interface import MicrowaveMode
from interface.microwave_interface import TriggerEdge


class MicrowaveSmiq(Base, MicrowaveInterface):
    """ This is the Interface class to define the controls for the simple
        microwave hardware.
    """

    _modclass = 'MicrowaveSmiq'
    _modtype = 'hardware'

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # checking for the right configuration
        config = self.getConfiguration()
        if 'gpib_address' in config.keys():
            self._gpib_address = config['gpib_address']
        else:
            self.log.error(
                'This is MWSMIQ: did not find >>gpib_address<< in '
                'configration.')

        if 'gpib_timeout' in config.keys():
            self._gpib_timeout = int(config['gpib_timeout'])*1000
        else:
            self._gpib_timeout = 10*1000
            self.log.error(
                'This is MWSMIQ: did not find >>gpib_timeout<< in '
                'configration. I will set it to 10 seconds.')

        # trying to load the visa connection to the module
        self.rm = visa.ResourceManager()
        try:
            self._gpib_connection = self.rm.open_resource(self._gpib_address,
                                                          timeout=self._gpib_timeout)
        except:
            self.log.error(
                'This is MWSMIQ: could not connect to the GPIB '
                'address >>{}<<.'.format(self._gpib_address))
            raise

        self.log.info('MWSMIQ initialised and connected to hardware.')
        self.model = self._gpib_connection.query('*IDN?').split(',')[1]

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """

        self._gpib_connection.close()
        self.rm.close()

    def get_limits(self):
        """ Create an object containing parameter limits for this microwave source.

            @return MicrowaveLimits: device-specific parameter limits
        """
        limits = MicrowaveLimits()
        limits.supported_modes = (MicrowaveMode.CW, MicrowaveMode.LIST, MicrowaveMode.SWEEP)

        limits.min_frequency = 300e3
        limits.max_frequency = 6.4e9

        limits.min_power = -144
        limits.max_power = 10

        limits.list_minstep = 0.1
        limits.list_maxstep = 6.4e9
        limits.list_maxentries = 4000

        limits.sweep_minstep = 0.1
        limits.sweep_maxstep = 6.4e9
        limits.sweep_maxentries = 10001

        if self.model == 'SMIQ02B':
            limits.max_frequency = 2.2e9
            limits.max_power = 13
        elif self.model == 'SMIQ03B':
            limits.max_frequency = 3.3e9
            limits.max_power = 13
        elif self.model == 'SMIQ03HD':
            limits.max_frequency = 3.3e9
            limits.max_power = 13
        elif self.model == 'SMIQ04B':
            limits.max_frequency = 4.4e9
        elif self.model == 'SMIQ06B':
            pass
        elif self.model == 'SMIQ06ATE':
            pass
        else:
            self.log.warning('Model string unknown, hardware limits may be wrong.')
        limits.list_maxstep = limits.max_frequency
        limits.sweep_maxstep = limits.max_frequency
        return limits

    def on(self):
        """ Switches on any preconfigured microwave output.

        @return int: error code (0:OK, -1:error)
        """

        self._gpib_connection.write(':OUTP ON')
        self._gpib_connection.write('*WAI')

        return 0

    def off(self):
        """ Switches off any microwave output.

        @return int: error code (0:OK, -1:error)
        """

        if self._gpib_connection.query(':FREQ:MODE?') != 'CW':
            self._gpib_connection.write(':FREQ:MODE CW')
        self._gpib_connection.write(':OUTP OFF')
        self._gpib_connection.write('*WAI')

        return 0

    def get_power(self):
        """ Gets the microwave output power.

        @return float: the power set at the device in dBm
        """
        return float(self._gpib_connection.query(':POW?'))

    def set_power(self, power=0.):
        """ Sets the microwave output power.

        @param float power: the power (in dBm) set for this device

        @return int: error code (0:OK, -1:error)
        """
        if power is not None:
            self._gpib_connection.write(':POW {0:f}'.format(power))
            return 0
        else:
            return -1

    def get_frequency(self):
        """ Gets the frequency of the microwave output.

        @return float: frequency (in Hz), which is currently set for this device
        """
        return float(self._gpib_connection.query(':FREQ?'))

    def set_frequency(self, freq=None):
        """ Sets the frequency of the microwave output.

        @param float freq: the frequency (in Hz) set for this device

        @return int: error code (0:OK, -1:error)
        """
        if freq is not None:
            self._gpib_connection.write(':FREQ {0:e}'.format(freq))
            return 0
        else:
            return -1

    def set_cw(self, freq=None, power=None, useinterleave=None):
        """ Sets the MW mode to cw and additionally frequency and power

        @param float freq: frequency to set in Hz
        @param float power: power to set in dBm
        @param bool useinterleave: If this mode exists you can choose it.

        @return int: error code (0:OK, -1:error)

        Interleave option is used for arbitrary waveform generator devices.
        """
        error = 0
        self._gpib_connection.write(':FREQ:MODE CW')

        if freq is not None:
            error = self.set_frequency(freq)
        else:
            return -1
        if power is not None:
            error = self.set_power(power)
        else:
            return -1
        return error

    def set_list(self, freq=None, power=None):
        """ Sets the MW mode to list mode

        @param list freq: list of frequencies in Hz
        @param float power: MW power of the frequency list in dBm

        @return int: error code (0:OK, -1:error)
        """
        error = 0
#        if self.set_cw(freq[0],power) != 0:
#            error = -1
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':LIST:DEL:ALL')
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(":LIST:SEL 'ODMR'")

        # put al frequencies into a string, first element is doubled
        # so there are n+1 list entries for scanning n frequencies
        # due to counter/trigger issues
        freqstring = ' {0:f},'.format(freq[0])
        for f in freq[:-1]:
            freqstring += ' {0:f},'.format(f)
        freqstring += ' {0:f}'.format(freq[-1])

        freqcommand = ':LIST:FREQ' + freqstring
        #print(freqcommand)
        self._gpib_connection.write(freqcommand)
        self._gpib_connection.write('*WAI')

        # there are n+1 list entries for scanning n frequencies
        # due to counter/trigger issues
        powcommand = ':LIST:POW {0}{1}'.format(power, (', ' + str(power)) * len(freq))
        #print(powcommand)
        self._gpib_connection.write(powcommand)

        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':LIST:MODE STEP')
        self._gpib_connection.write('*WAI')

        n = int(np.round(float(self._gpib_connection.query(':LIST:FREQ:POIN?'))))

        if n != len(freq) + 1:
            error = -1
        return error

    def reset_listpos(self):
        """ Reset of MW List Mode position to start from first given frequency

        @return int: error code (0:OK, -1:error)
        """
        self._gpib_connection.write(':ABOR:LIST')
        self._gpib_connection.write('*WAI')
        return 0

    def set_sweep(self, start, stop, step, power):
        """ Activate sweep mode on the microwave source

        @param start float: start frequency
        @param stop float: stop frequency
        @param step float: frequency step
        @param power float: output power
        @return int: number of frequency steps generated
        """
        self._gpib_connection.write(':SOUR:POW ' + str(power))
        self._gpib_connection.write('*WAI')

        self._gpib_connection.write(':SWE:MODE STEP')
        self._gpib_connection.write(':SOUR:FREQ:STAR ' + str(start-step))
        self._gpib_connection.write(':SOUR:FREQ:STOP ' + str(stop))
        self._gpib_connection.write(':SOUR:SWE:SPAC LIN')
        self._gpib_connection.write(':SOUR:SWE:STEP ' + str(step))
        self._gpib_connection.write(':TRIG1:SWE:SOUR EXT')
        self._gpib_connection.write(':TRIG1:SLOP POS')
        self._gpib_connection.write('*WAI')
        n = int(np.round(float(self._gpib_connection.query(':SWE:FREQ:POIN?'))))
        # print(n)
        # if n != len(self._mw_frequency_list):
        #     return -1
        return n - 1

    def reset_sweep(self):
        """ Reset of MW List Mode position to start from first given frequency

        @return int: error code (0:OK, -1:error)
        """
        self._gpib_connection.write(':ABOR:SWE')
        self._gpib_connection.write('*WAI')
        return 0

    def sweep_on(self):
        """ Switches on the list mode.

        @return int: error code (1: ready, 0:not ready, -1:error)
        """
        self._gpib_connection.write(':FREQ:MODE SWE')
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':OUTP ON')
        self._gpib_connection.write('*WAI')
        # If there are timeout  problems after this command, update the smiq
        # firmware to > 5.90 as there was a problem with excessive wait times
        # after issuing :LIST:LEARN over a GPIB connection in firmware 5.88
        return int(self._gpib_connection.query('*OPC?'))

    def list_on(self):
        """ Switches on the list mode.

        @return int: error code (1: ready, 0:not ready, -1:error)
        """
        self._gpib_connection.write(':OUTP ON')
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':LIST:LEARN')
        self._gpib_connection.write('*WAI')
        # If there are timeout  problems after this command, update the smiq
        # firmware to > 5.90 as there was a problem with excessive wait times
        # after issuing :LIST:LEARN over a GPIB connection in firmware 5.88
        self._gpib_connection.write(':FREQ:MODE LIST')
        self._gpib_connection.write('*WAI')
        return int(self._gpib_connection.query('*OPC?'))

    def set_ext_trigger(self, pol=TriggerEdge.RISING):
        """ Set the external trigger for this device with proper polarization.

        @param TriggerEdge pol: polarisation of the trigger (basically rising edge or
                        falling edge)

        @return int: error code (0:OK, -1:error)
        """
        if pol == TriggerEdge.RISING:
            edge = 'POS'
        elif pol == TriggerEdge.FALLING:
            edge = 'NEG'
        else:
            return -1
        try:
            self._gpib_connection.write(':TRIG1:LIST:SOUR EXT')
            self._gpib_connection.write(':TRIG1:SLOP {0}'.format(edge))
        except:
            return -1
        return 0

