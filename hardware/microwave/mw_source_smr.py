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
import time

from core.base import Base
from interface.microwave_interface import MicrowaveInterface
from interface.microwave_interface import MicrowaveLimits
from interface.microwave_interface import MicrowaveMode
from interface.microwave_interface import TriggerEdge


class MicrowaveSMR(Base, MicrowaveInterface):
    """ The hardware control for the device Rohde and Schwarz of type SMR.
    The command structure has been tested for type SMR20.
    Not tested on the device types SMR27, SMR30, SMR40
    For additional information concerning the commands to communicate via the
    GPIB connection through visa, please have a look at:
    http://cdn.rohde-schwarz.com/pws/dl_downloads/dl_common_library/dl_manuals/gb_1/s/smr_1/smr_20-40.pdf
    """

    _modclass = 'MicrowaveSMR20'
    _modtype = 'hardware'

    def on_activate(self):
        """ Initialisation performed during activation of the module. """


        self._LIST_DWELL = 10e-3    # Dwell time for list mode to set how long
                                    # the device should stay at one list entry.
                                    # here dwell time can be between 1ms and 1s
        self._SWEEP_DWELL = 10e-3   # Dwell time for sweep mode to set how long
                                    # the device should stay at one list entry.
                                    # here dwell time can be between 10ms and 5s

        # checking for the right configuration
        config = self.getConfiguration()

        if 'gpib_address' in config.keys():
            self._gpib_address = config['gpib_address']
        else:
            self.log.error('MicrowaveSMR20: did not find parameter '
                        '>>gpib_address<< in configuration.')

        if 'gpib_timeout' in config.keys():
            self._gpib_timeout = int(config['gpib_timeout'])*1000
        else:
            self._gpib_timeout = 10*1000
            self.log.error('MicrowaveSMR20: did not find >>gpib_timeout<< in '
                           'configration. It will be set to {0} '
                           'seconds.'.format(self._gpib_timeout))

        # trying to load the visa connection to the module
        self.rm = visa.ResourceManager()
        try:
            # such a stupid stuff, the timeout is specified here in ms not in
            # seconds any more, take that into account.
            self._gpib_connection = self.rm.open_resource(self._gpib_address,
                                                          timeout=self._gpib_timeout*1000)

            self._gpib_connection.write_termination = "\r\n"
            self._gpib_connection.read_termination = None

            self.log.info('MicrowaveSMR20: initialised and connected to '
                        'hardware.')
        except:
             self.log.error('MicrowaveSMR20: could not connect to the GPIB '
                         'address >>{0}<<.'.format(self._gpib_address))

        self._gpib_connection.write('*WAI')
        self._FREQ_MAX = float(self._ask('FREQuency? MAX'))
        self._FREQ_MIN = float(self._ask('FREQuency? MIN'))
        self._POWER_MAX = float(self._ask('POWER? MAX'))
        self._POWER_MIN = float(self._ask('POWER? MIN'))

        # although it is the step mode, this number should be the same for the
        # list mode:
        self._LIST_FREQ_STEP_MIN = float(self._ask(':SOURce:FREQuency:STEP? MIN'))
        self._LIST_FREQ_STEP_MAX = float(self._ask(':SOURce:FREQuency:STEP? MAX'))

        self._SWEEP_FREQ_STEP_MIN = float(self._ask(':SOURce:SWEep:FREQuency:STEP? MIN'))
        self._SWEEP_FREQ_STEP_MAX = float(self._ask(':SOURce:SWEep:FREQuency:STEP? MAX'))

        # the return will be a list telling how many are free and occupied, i.e.
        # [free, occupied] and the sum of that is the total list entries.
        max_list_entries = self._ask('SOUR:LIST:FREE?')
        self._MAX_LIST_ENTRIES = sum([int(entry) for entry in max_list_entries.strip().split(',')])
        # FIXME: Not quite sure about this:
        self._MAX_SWEEP_ENTRIES = 10001

        # extract the options from the device:
        message = self._ask('*OPT?').strip().split(',')
        self.OPTIONS = [entry for entry in message if entry != '0']

        message = self._ask('*IDN?').strip().split(',')
        self._BRAND = message[0]
        self._MODEL = message[1]
        self._SERIALNUMBER = message[2]
        self._FIRMWARE_VERSION = message[3]

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """

        self.off()  # turn the device off in case it is running
        self._gpib_connection.close()   # close the gpib connection
        self.rm.close()                 # close the resource manager

    def get_limits(self):
        """ Retrieve the limits of the device.
        @return: object MicrowaveLimits: Serves as a container for the limits
                                         of the microwave device.
        """
        limits = MicrowaveLimits()
        limits.supported_modes = (MicrowaveMode.CW, MicrowaveMode.LIST,
                                  MicrowaveMode.SWEEP)

        limits.min_frequency = self._FREQ_MIN
        limits.max_frequency = self._FREQ_MAX
        limits.min_power = self._POWER_MIN
        limits.max_power = self._POWER_MAX

        limits.list_minstep = self._LIST_FREQ_STEP_MIN
        limits.list_maxstep = self._LIST_FREQ_STEP_MAX
        limits.list_maxentries = self._MAX_LIST_ENTRIES

        limits.sweep_minstep = self._SWEEP_FREQ_STEP_MIN
        limits.sweep_maxstep = self._SWEEP_FREQ_STEP_MAX
        limits.sweep_maxentries = self._MAX_SWEEP_ENTRIES
        return limits

    def off(self):
        """ Switches off any microwave output.
        Must return AFTER the device is actually stopped.
        @return int: error code (0:OK, -1:error)
        """
        mode, is_running = self.get_status()
        if not is_running:
            return 0

        if mode == 'list':
            self._write(':FREQ:MODE CW')

        self._write(':OUTP OFF')

        # check whether
        while int(float(self._gpib_connection.query('OUTP:STAT?'))) != 0:
            time.sleep(0.2)

        if mode == 'list':
            self._command_wait(':LIST:LEARN')
            self._command_wait(':FREQ:MODE LIST')
        return 0


    def get_status(self):
        """ Get the current status of the MW source, i.e. the mode
        (cw, list or sweep) and the output state (stopped, running).
        @return str, bool: mode ['cw', 'list', 'sweep'], is_running [True, False]
        """
        is_running = bool(int(self._ask('OUTP:STAT?')))
        mode = self._ask(':FREQ:MODE?').strip().lower()

        # The modes 'fix' and 'cw' are treated the same in the SMR device,
        # therefore, 'fix' is converted to 'cw':
        if mode == 'fix':
            mode = 'cw'

        # rename the mode according to the interface
        if mode == 'swe':
            mode = 'sweep'

        return mode, is_running



    def get_power(self):
        """ Gets the microwave output power.
        @return float: the power set at the device in dBm
        """

        mode, dummy = self.get_status()
        if mode == 'list':
            return float(self._ask(':LIST:POW?'))
        else:
            # This case works for cw AND sweep mode
            return float(self._ask(':POW?'))

    def _set_power(self, power):
        """ Sets the microwave output power.
        @param float power: the power (in dBm) set for this device
        @return float: actual power set (in dBm)
        """

        # every time a single power is set, the CW mode is activated!
        self._gpib_connection.write(':FREQ:MODE CW')
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':POW {0:f};'.format(power))
        actual_power = self.get_power()
        return actual_power


    def get_frequency(self):
        """  Gets the frequency of the microwave output.
        @return float|list: frequency(s) currently set for this device in Hz
        Returns single float value if the device is in cw mode.
        Returns list like [start, stop, step] if the device is in sweep mode.
        Returns list of frequencies if the device is in list mode.
        """

        mode, is_running = self.get_status()

        if 'cw' in mode:
            return_val = float(self._ask(':FREQ?'))
        elif 'sweep' in mode:
            start = float(self._ask(':FREQ:STAR?'))
            stop = float(self._ask(':FREQ:STOP?'))
            step = float(self._ask(':SWE:STEP?'))
            return_val = [start+step, stop, step]
        elif 'list' in mode:
            # Exclude first frequency entry, since that is a duplicate due to
            # trigger issues if triggered from external sources, like NI card.
            freq_list = self._ask(':LIST:FREQ?').strip().split(',')
            if len(freq_list) > 1:
                freq_list.pop()
            return_val = np.array([float(freq) for freq in freq_list])
        else:
            self.log.error('Mode Unknown! Cannot determine Frequency!')
        return return_val

    def set_frequency(self, freq):
        """ Sets the frequency of the microwave output.
        @param float freq: the frequency (in Hz) set for this device
        @return int: error code (0:OK, -1:error)
        """

        # every time a single frequency is set, the CW mode is activated!
        self._gpib_connection.write(':FREQ:MODE CW')
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

        if self.set_cw(freq[0], power) != 0:
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
        # that and the instrument displays an error, when this parameter is not
        # set in the list mode (even it should be set by default):
        self._gpib_connection.write(':SOUR:LIST:DWEL')
        self._gpib_connection.write('*WAI')

        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':TRIG1:LIST:SOUR EXT')
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':TRIG1:SLOP NEG')


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

        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':OUTP:AMOD FIX')


        self._gpib_connection.write('*WAI')
        self.reset_listpos()

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
        # self._gpib_connection.write(':LIST:LEAR')

        self._gpib_connection.write(':FREQ:MODE LIST')
        self._gpib_connection.write('*WAI')
        self._gpib_connection.write(':ABOR:LIST')
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

    def _ask(self, question):
        return self._gpib_connection.query(question)

    def _write(self, command, wait=True):
        statuscode = self._gpib_connection.write(command)
        if wait:
            self._gpib_connection.write('*WAI')
return statuscode