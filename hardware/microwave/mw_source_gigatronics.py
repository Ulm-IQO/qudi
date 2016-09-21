# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware file to control Gigatronics Device.

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
import time

from core.base import Base
from interface.microwave_interface import MicrowaveInterface


class MicrowaveGigatronics(Base, MicrowaveInterface):
    """ Hardware file for Gigatronics. """

    _modclass = 'MicrowaveInterface'
    _modtype = 'hardware'

    ## declare connectors
    _out = {'mwsourcegigatronics': 'MicrowaveInterface'}

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
            self.log.error('This is MWgigatronics: did not find '
                    '>>gpib_address<< in configration.')

        if 'gpib_timeout' in config.keys():
            self._gpib_timeout = int(config['gpib_timeout'])
        else:
            self._gpib_timeout = 10
            self.log.error('This is MWgigatronics: did not find '
                    '>>gpib_timeout<< in configration. I will set it to '
                    '10 seconds.')

        # trying to load the visa connection to the module
        visa.log_to_screen()
        self.rm = visa.ResourceManager()
        try:
            self._gpib_connection = self.rm.open_resource(
                self._gpib_address,
                read_termination='\r\n',
                timeout=self._gpib_timeout*1000,  # config is seconds, pyvisa is millisecondss
                )
        except:
            self.log.error('This is MWgigatronics: could not connect to the '
                    'GPIB address >>{}<<.'.format(self._gpib_address))
            raise
        self._gpib_connection.write('*RST')
        idnlist = []
        while len(idnlist) < 3:
            idnlist = self._gpib_connection.query('*IDN?').split(', ')
            print(idnlist)
            time.sleep(0.1)
        self.model = idnlist[1]
        self.log.info('MWgigatronics initialised and connected to hardware.')

    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        self._gpib_connection.close()
        self.rm.close()

    def get_limits(self):
        minpower = -144
        maxpower = 10
        minfreq = 100e3
        maxfreq = 20e9
        minliststep = 0.1
        maxliststep = 20e9
        listentries = 4000
        minsweepstep = 0.1
        maxsweepstep = 10e9
        sweepentries = 10e6
        if self.model.startswith('2508'):
            maxfreq = 8e9
        elif self.model.startswith('2520'):
            maxfreq = 20e9
        elif self.model.startswith('2526'):
            maxfreq = 26.5e9
        elif self.model.startswith('2540'):
            maxfreq = 40e9
        else:
            self.log.warn('Unknown Gigatronics moel, you are on your own!')

        limits = {
            'frequency': {
                'min': minfreq,
                'max': maxfreq
            },
            'power': {
                'min': minpower,
                'max': maxpower
            },
            'list': {
                'minstep': minliststep,
                'maxstep': maxliststep,
                'maxentries': listentries
            },
            'sweep': {
                'minstep': minsweepstep,
                'maxstep': maxsweepstep,
                'maxentries': sweepentries
            }
        }
        return limits

    def on(self):
        """ Switches on any preconfigured microwave output.

        @return int: error code (0:OK, -1:error)
        """
        self._gpib_connection.write(':OUTP ON')
        return 0


    def off(self):
        """ Switches off any microwave output.

        @return int: error code (0:OK, -1:error)
        """
        self._gpib_connection.write(':OUTP OFF')
        self._gpib_connection.write(':MODE CW')
        return 0


    def get_power(self):
        """ Gets the microwave output power.

        @return float: the power set at the device in dBm
        """
        return float(self._gpib_connection.ask(':POW?'))


    def set_power(self, power=None):
        """ Sets the microwave output power.

        @param float power: the power (in dBm) set for this device

        @return int: error code (0:OK, -1:error)
        """
        if power != None:
            self._gpib_connection.write(':POW {:f} DBM'.format(power))
            return 0
        else:
            return -1


    def get_frequency(self):
        """ Gets the frequency of the microwave output.

        @return float: frequency (in Hz), which is currently set for this device
        """

        return float(self._gpib_connection.ask(':FREQ?'))


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
        self._gpib_connection.write(':MODE CW')

        if freq != None:
            error = self.set_frequency(freq)
        else:
            return -1
        if power != None:
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

        if self.set_cw(freq[0], power) != 0:
            return -1
        try:
            self._gpib_connection.write('*SRE 0')
            self._gpib_connection.write(':LIST:SEQ:AUTO ON')
            freqstring = '{0:.1f},'.format(freq[0]) + ','.join(('{0:.1f}'.format(f) for f in freq))
            powstring = '{0:.3f},'.format(power) + ','.join(('{0:.3f}'.format(power) for f in freq))
            self._gpib_connection.write('LIST:FREQ {0:s}'.format(freqstring))
            self._gpib_connection.write('LIST:POW {0:s}'.format(powstring))
            self._gpib_connection.write('LIST:DWEL 0.002000 S')
            self._gpib_connection.write('LIST:RFOffTime 0.000000 MS')
            self._gpib_connection.write('*OPC?')
            self._gpib_connection.write('LIST:PREC 1')
            # wait for '1' from OPC
            self._gpib_connection.read()
            self._gpib_connection.write(':LIST:REP STEP')
            self._gpib_connection.write(':TRIG:SOUR EXT')
            self._gpib_connection.write('*SRE 239')
            self._gpib_connection.write('*SRE 167')

            nrpoints = int(np.round(float(self._gpib_connection.query(':LIST:FREQ:POIN?'))))
            if nrpoints != len(freq) + 1:
                self.log.error('List upload failed: expected {0} points, got {1}.'.format(len(freq) + 1, nrpoints))
                error = -1
        except visa.VisaIOError:
            self.log.error('List upload failed, I/O error.')
            error = -1
        return error

    def reset_listpos(self):#
        """ Reset of MW List Mode position to start from first given frequency

        @return int: error code (0:OK, -1:error)
        """
        self._gpib_connection.write(':MODE CW')
        self._gpib_connection.write(':MODE LIST')
        mode = self._gpib_connection.query(':MODE?')
        return 0 if 'LIST' in mode else -1

    def list_on(self):
        """ Switches on the list mode.

        @return int: error code (0:OK, -1:error)
        """
        #self._gpib_connection.write(':LIST:REP STEP')
        #self._gpib_connection.write(':TRIG:SOUR EXT')
        #self._gpib_connection.write(':LIST:SYNC 3')
        #self._gpib_connection.write(':LIST:SYNC:DEL 50')
        #self._gpib_connection.write(':MODE LIST')
        self._gpib_connection.write(':OUTP ON')

        return 0

    def set_ex_trigger(self, source, pol):
        """ Set the external trigger for this device with proper polarization.

        @param str source: channel name, where external trigger is expected.
        @param str pol: polarisation of the trigger (basically rising edge or
                        falling edge)

        @return int: error code (0:OK, -1:error)
        """
        return 0




