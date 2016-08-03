# -*- coding: utf-8 -*-

"""
This file contains the QuDi hardware file to control Anritsu 70GHz Device.

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

Parts of this file were developed from a PI3diamond module which is
Copyright (C) 2009 Helmut Rathgen <helmut.rathgen@gmail.com>

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import visa

from core.base import Base
from interface.microwave_interface import MicrowaveInterface


class MicrowaveAnritsu70GHz(Base, MicrowaveInterface):
    """ This is the Interface class to define the controls for the simple
        microwave hardware.
    """
    _modclass = 'MicrowaveAanritsu70GHz'
    _modtype = 'hardware'

    ## declare connectors
    _out = {'mwsourceanritsu': 'MicrowaveInterface'}

    def on_activate(self,e=None):
        # checking for the right configuration
        config = self.getConfiguration()
        if 'gpib_address' in config.keys():
            self._gpib_address = config['gpib_address']
        else:
            self.log.error('This is MWanritsu70GHz: did not find '
                    '>>gpib_address<<  in configration.')

        if 'gpib_timeout' in config.keys():
            self._gpib_timeout = int(config['gpib_timeout'])
        else:
            self._gpib_timeout = 10
            self.log.warning('This is MWanritsu70GHz: did not find '
                    '>>gpib_timeout<< in configration. I will set it to '
                    '10 seconds.')

        # trying to load the visa connection to the module
        self.rm = visa.ResourceManager()
        try:
            self._gpib_connection = self.rm.open_resource(
                self._gpib_address,
                timeout=self._gpib_timeout*1000)
        except:
            log.error('This is MWanritsu70GHz: could not connect to the GPIB '
                      'address >>{}<<.'.format(self._gpib_address))
            raise
        # native command mode, some things are missing in SCPI mode
        self._gpib_connection.write('SYST:LANG \"NATIVE\"')
        self.model = self._gpib_connection.query('*IDN?').split(',')[1]
        self.log.info('Anritsu {} initialised and connected to hardware.'
                ''.format(self.model))

    def on_deactivate(self,e=None):
        self._gpib_connection.close()
        self.rm.close()

    def get_limits(self):
        """ Right now, this is for Anritsu MG3696B only."""
        limits = {
            'frequency': {
                'min': 10*10e6,
                'max': 70*10e9
                },
            'power': {
                'min': -20,
                'max': 10
                },
            'list': {
                'minstep': 0.001,
                'maxstep': 70*10e9,
                'maxentries': 2000
                },
            'sweep': {
                'minstep': 0.001,
                'maxstep': 70*10e9,
                'maxentries': 10000
                }
            }
        return limits

    def on(self):
        """ Switches on any preconfigured microwave output.

        @return int: error code (0:OK, -1:error)
        """
        print("on")
        self._gpib_connection.write('RF1')

        return 0

    def off(self):
        """ Switches off any microwave output.

        @return int: error code (0:OK, -1:error)
        """
        print("off")
        self._gpib_connection.write('RF0')

        return 0

    def get_power(self):
        """ Gets the microwave output power.

        @return float: the power set at the device in dBm
        """
        return float(self._gpib_connection.ask('OL0'))

    def set_power(self, power=None):
        """ Sets the microwave output power.

        @param float power: the power (in dBm) set for this device

        @return int: error code (0:OK, -1:error)
        """
        if power is not None:
            self._gpib_connection.write('L0 {:f} DM'.format(power))
            return 0
        else:
            return -1

    def get_frequency(self):
        """ Gets the frequency of the microwave output.

        @return float: frequency (in Hz), which is currently set for this device
        """
        return float(self._gpib_connection.ask('OF0'))

    def set_frequency(self, freq=None):
        """ Sets the frequency of the microwave output.

        @param float freq: the frequency (in Hz) set for this device

        @return int: error code (0:OK, -1:error)
        """
        if freq is not None:
            self._gpib_connection.write('F0 {:f} HZ'.format(freq))
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
        print("set cw")
        if freq != None:
            error = self.set_frequency(freq)
        else:
            return -1

        if power != None:
            error = self.set_power(power)
        else:
            return -1
        self._gpib_connection.write('ACW')
        return error

    def set_list(self, freq=None, power=None):
        """ Sets the MW mode to list mode

        @param list freq: list of frequencies in Hz
        @param float power: MW power of the frequency list in dBm

        @return int: error code (0:OK, -1:error)
        """
        error = 0

        if self.set_cw(freq[0], power) != 0:
            error = -1

        flist = '{:f} HZ, '.format(freq[0])
        plist = '{:f} DM, '.format(power)

        for f in freq[:-1]:
            flist += '{:f} HZ, '.format(f)
            plist += '{:f} DM, '.format(power)

        flist += '{:f} HZ'.format(freq[-1])
        plist += '{:f} DM'.format(power)
        stop = len(freq)

        self._gpib_connection.write(
            'ELN0 ELI0000 '
            'LF ' + flist
            + ' LP ' + plist
            + 'LIB0000 LIE{:04d}'.format(stop))
        return error

    def reset_listpos(self):
        """ Reset of MW List Mode position to start from first given frequency

        @return int: error code (0:OK, -1:error)
        """
        self._gpib_connection.write('ELI0000')
        return 0

    def list_on(self):
        """ Switches on the list mode.

        @return int: error code (0:OK, -1:error)
        """
        self._gpib_connection.write('LST LEA RF1')
        return 0

    def set_ex_trigger(self, source, pol):
        """ Set the external trigger for this device with proper polarization.

        @param str source: channel name, where external trigger is expected.
        @param str pol: polarisation of the trigger (basically rising edge or
                        falling edge)

        @return int: error code (0:OK, -1:error)
        """
        print("trigger")
        self._gpib_connection.write('MNT')
        return 0

    def set_sweep(self, start, stop, step, power):
        """

        @param start:
        @param stop:
        @param step:
        @param power:
        @return:
        """
        print("sweep on")
        self.set_power(power)
        self._gpib_connection.write('F1 {} Hz, SYZ {} Hz, F2 {} Hz, SF1'.format(start - step, step, stop))
        nrsteps = int(self._gpib_connection.query('OSS'))
        print('steps', nrsteps)
        return nrsteps - 1

    def reset_sweep(self):
        """ Reset of MW List Mode position to start from first given frequency

        @return int: error code (0:OK, -1:error)
        """
        print("reset sweep")
        self._gpib_connection.write('RSS')
        return 0

    def sweep_on(self):
        """ Switches on the list mode.

        @return int: error code (1: ready, 0:not ready, -1:error)
        """
        print("sweep on")
        self._gpib_connection.write('SSP RF1')
        return 0
