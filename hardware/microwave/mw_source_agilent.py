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

from core.module import Base, ConfigOption
from interface.microwave_interface import MicrowaveInterface
from interface.microwave_interface import MicrowaveLimits
from interface.microwave_interface import MicrowaveMode
from interface.microwave_interface import TriggerEdge


class MicrowaveAgilent(Base, MicrowaveInterface):
    """ This is the Interface class to define the controls for the simple
        microwave hardware.
    """

    _modclass = 'MicrowaveAgilent'
    _modtype = 'hardware'

    _usb_address = ConfigOption('usb_address', missing='error')
    _usb_timeout = ConfigOption('usb_timeout', 10, missing='warn')

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._usb_timeout = self._usb_timeout * 1000
        # trying to load the visa connection to the module
        self.rm = visa.ResourceManager()
        self._usb_connection = self.rm.open_resource(
            resource_name=self._usb_address,
            timeout=self._usb_timeout)

        self.log.info('MWAGILENT initialised and connected to hardware.')
        self.model = self._usb_connection.query('*IDN?').split(',')[1]

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """

        self._usb_connection.close()
        self.rm.close()

    def get_limits(self):
        limits = MicrowaveLimits()
        limits.supported_modes = ('CW', 'LIST', 'SWEEP')

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

        if self.model == 'N9310A':
            limits.min_frequency = 9e3
            limits.max_frequency = 3.0e9
            limits.min_power = -127
            limits.max_power = 20
        else:
            self.log.warning('Model string unknown, hardware limits may be wrong.')
        limits.list_maxstep = limits.max_frequency
        limits.sweep_maxstep = limits.max_frequency
        return limits

    def on(self):
        """ Switches on any preconfigured microwave output.

        @return int: error code (0:OK, -1:error)
        """

        self._usb_connection.write(':RFO:STAT ON')
        self._usb_connection.write('*WAI')

        return 0

    def off(self):
        """ Switches off any microwave output.

        @return int: error code (0:OK, -1:error)
        """

        self._usb_connection.write(':RFO:STAT OFF')
        self._usb_connection.write('*WAI')

        return 0

    def get_power(self):
        """ Gets the microwave output power.

        @return float: the power set at the device in dBm
        """
        return float(self._usb_connection.query(':AMPL:CW?'))

    def set_power(self, power=0.):
        """ Sets the microwave output power.

        @param float power: the power (in dBm) set for this device

        @return int: error code (0:OK, -1:error)
        """
        if power is not None:
            self._usb_connection.write(':AMPL:CW {0:f}'.format(power))
            return 0
        else:
            return -1

    def get_frequency(self):
        """ Gets the frequency of the microwave output.

        @return float: frequency (in Hz), which is currently set for this device
        """
        return float(self._usb_connection.query(':FREQ:CW?'))

    def set_frequency(self, freq=None):
        """ Sets the frequency of the microwave output.

        @param float freq: the frequency (in Hz) set for this device

        @return int: error code (0:OK, -1:error)
        """
        if freq is not None:
            self._usb_connection.write(':FREQ:CW {0:e} Hz'.format(freq))
            return 0
        else:
            return -1

    def set_cw(self, freq=None, power=None, useinterleave=None):
        """ Sets the MW mode to cw and additionally frequency and power
        #For agilent device there is no CW mode, so just do nothing

        @param float freq: frequency to set in Hz
        @param float power: power to set in dBm
        @param bool useinterleave: If this mode exists you can choose it.

        @return int: error code (0:OK, -1:error)

        Interleave option is used for arbitrary waveform generator devices.
        """
        error = 0

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
        """ There is no list mode for agilent
        # Also the list is created by giving 'start_freq, step, stop_freq'

        @param list freq: list of frequencies in Hz
        @param float power: MW power of the frequency list in dBm

        """
#        if self.set_cw(freq[0],power) != 0:
#            error = -1

        #self._usb_connection.write(':SWE:RF:STAT ON')

        # put all frequencies into a string, first element is doubled
        # so there are n+1 list entries for scanning n frequencies
        # due to counter/trigger issues
        #freqstring = ' {0:f},'.format(freq[0])
        #for f in freq[:-1]:
        #    freqstring += ' {0:f},'.format(f)
        #freqstring += ' {0:f}'.format(freq[-1])

        #freqcommand = ':LIST:FREQ' + freqstring

        n = len(freq)

        self._usb_connection.write(':SWE:RF:STAR {0:e} Hz'.format(freq[0]))
        self._usb_connection.write(':SWE:RF:STOP {0:e} Hz'.format(freq[-1]))
        self._usb_connection.write(':SWE:STEP:POIN {0}'.format(n))
        self._usb_connection.write(':SWE:STEP:DWEL 10 ms')
        self._usb_connection.write('*WAI')

        self._usb_connection.write(':SWE:AMPL:STAR {0:f}'.format(power))
        self._usb_connection.write(':SWE:AMPL:STOP {0:f}'.format(power))
        self._usb_connection.write(':SWE:REP CONT')
        self._usb_connection.write(':SWE:STRG IMM')
#        self._usb_connection.write(':SWE:STRG:SLOP EXTP')
        self._usb_connection.write(':SWE:PTRG IMM')
#        self._usb_connection.write(':SWE:PTRG:SLOP EXTP')
        self._usb_connection.write(':SWE:DIR:UP')
        self._usb_connection.write('*WAI')

        self._usb_connection.write(':RFO:STAT ON')
        self._usb_connection.write(':SWE:RF:STAT ON')

        return 0

    def reset_listpos(self):
        """ Reset of MW List Mode position to start from first given frequency

        @return int: error code (0:OK, -1:error)
        """
        self._usb_connection.write(':SWE:RF:STAT OFF')
        self._usb_connection.write('*WAI')
        return 0

    def set_sweep(self, start, stop, step, power):
        """

        @param start:
        @param stop:
        @param step:
        @param power:
        @return:
        """
        #self._usb_connection.write(':SOUR:POW ' + str(power))
        #self._usb_connection.write('*WAI')

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
        self._usb_connection.write(':RFO:STAT OFF')
        self._usb_connection.write(':SWE:RF:STAT OFF')
        self._usb_connection.write('*WAI')
        return 0

    def sweep_on(self):
        """ Switches on the list mode.

        @return int: error code (1: ready, 0:not ready, -1:error)
        """
        self._usb_connection.write(':RFO:STAT ON')
        self._usb_connection.write(':SWE:RF:STAT ON')
        self._usb_connection.write('*WAI')
        # If there are timeout  problems after this command, update the smiq
        # firmware to > 5.90 as there was a problem with excessive wait times
        # after issuing :LIST:LEARN over a GPIB connection in firmware 5.88
        return 0

    def list_on(self):
        """ Switches on the list mode.

        @return int: error code (1: ready, 0:not ready, -1:error)
        """
        self._usb_connection.write(':RFO:STAT ON')
        self._usb_connection.write('*WAI')
        # If there are timeout  problems after this command, update the smiq
        # firmware to > 5.90 as there was a problem with excessive wait times
        # after issuing :LIST:LEARN over a GPIB connection in firmware 5.88
        self._usb_connection.write(':SWE:RF:STAT ON')
        self._usb_connection.write('*WAI')


        return 0

    def set_ext_trigger(self, pol=TriggerEdge.RISING):
        """ Set the external trigger for this device with proper polarization.

        @param str source: channel name, where external trigger is expected.
        @param str pol: polarisation of the trigger (basically rising edge or
                        falling edge)

        @return int: error code (0:OK, -1:error)
        """
        if pol == TriggerEdge.RISING:
            edge = 'EXTP'
        elif pol == TriggerEdge.FALLING:
            edge = 'EXTN'
        else:
            return -1
        try:
            self._usb_connection.write(':SWE:STRG:SLOP {0}'.format(edge))
        except:
            return -1
        return 0
