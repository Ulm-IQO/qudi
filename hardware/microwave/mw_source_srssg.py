# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware file to control SRS SG devices.

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
import time

from core.module import Base, ConfigOption
from interface.microwave_interface import MicrowaveInterface
from interface.microwave_interface import MicrowaveLimits
from interface.microwave_interface import MicrowaveMode
from interface.microwave_interface import TriggerEdge

class MicrowaveSRSSG(Base, MicrowaveInterface):
    """ Hardware control class to controls SRS SG390 devices.  """

    _modclass = 'MicrowaveSRSSG'
    _modtype = 'hardware'

    _gpib_address = ConfigOption('gpib_address', missing='error')
    _gpib_timeout = ConfigOption('gpib_timeout', 10, missing='warn')

    _internal_mode = 'cw' # list and sweep might also be possible, but start
                          # always with that

    def on_activate(self):
        """ Initialisation performed during activation of the module. """

        # checking for the right configuration
        config = self.getConfiguration()
        if 'gpib_address' in config.keys():
            self._gpib_address = config['gpib_address']
        else:
            self.log.error('No configuration value set for "gpib_address"! '
                           'Enter a valid GPIB address.')

        if 'gpib_timeout' in config.keys():
            self._gpib_timeout = int(config['gpib_timeout'])*1000
        else:
            self._gpib_timeout = 10*1000
            self.log.error('No "gpib_timeout" was set in the configration. '
                           'Timeout will be set to 10 seconds.')

        # trying to load the visa connection to the module
        self.rm = visa.ResourceManager()
        try:
            self._gpib_connection = self.rm.open_resource(
                self._gpib_address,
                timeout=self._gpib_timeout)
        except:
            self.log.error('Could not connect to the GPIB address "{}". Check '
                           'whether address exists and reload '
                           'module!'.format(self._gpib_address))
            raise

        message = self._gpib_connection.query('*IDN?').strip().split(',')
        self._BRAND = message[0]
        self._MODEL = message[1]
        self._SERIALNUMBER = message[2]
        self._FIRMWARE_VERSION = message[3]

        self.log.info('Load the device model "{0}" from "{1}" with the serial'
                      'number "{2}" and the firmware version "{3}" '
                      'successfully.'.format(self._MODEL, self._BRAND,
                                             self._SERIALNUMBER,
                                             self._FIRMWARE_VERSION))

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """

        # self.off()
        # self._gpib_connection.close()
        # self.rm.close()
        return

    def cw_on(self):
        self._internal_mode = 'cw'
        self.on()
        return 0

    def get_status(self):
        is_running = bool(int(self._gpib_connection.ask('ENBR?').strip()))
        return self._internal_mode, is_running

    def get_limits(self):
        limits = MicrowaveLimits()
        limits.supported_modes = (MicrowaveMode.CW, MicrowaveMode.LIST, MicrowaveMode.SWEEP)

        # SRS has two output connectors. The specifications
        # are used for the Type N output.
        limits.min_frequency = 950e3
        limits.max_frequency = 6.4e9

        limits.min_power = -110
        limits.max_power = 16.5

        # FIXME: Not quite sure about this:
        limits.list_minstep = 1e-6
        limits.list_maxstep = 2.025e9
        limits.list_maxentries = 4000

        # FIXME: Not quite sure about this:
        limits.sweep_minstep = 0.1
        limits.sweep_maxstep = 6.4e9
        limits.sweep_maxentries = 10001

        if self._MODEL == 'SG392':
            limits.max_frequency = 2.025e9
        elif self._MODEL == 'SG394':
            limits.max_frequency = 4.050e9
        elif self._MODEL == 'SG396':
            limits.max_frequency = 6.075e9
        else:
            self.log.warning('Model string unknown, hardware limits may be wrong.')

        limits.list_maxstep = limits.max_frequency
        limits.sweep_maxstep = limits.max_frequency
        return limits

    def on(self):
        """ Switches on any preconfigured microwave output.

        @return int: error code (0:OK, -1:error)
        """
        self._gpib_connection.write('ENBR 1')
        self._gpib_connection.write('*WAI')

        return 0

    def off(self):
        """ Switches off any microwave output.

        @return int: error code (0:OK, -1:error)
        """

        self._gpib_connection.write('ENBR 0')
        self._gpib_connection.write('*WAI')

        return 0

    def get_power(self):
        """ Gets the microwave output power.

        @return float: the power set at the device in dBm
        """
        return float(self._gpib_connection.query('AMPR?'))

    def set_power(self, power=0.):
        """ Sets the microwave output power.

        @param float power: the power (in dBm) set for this device

        @return int: error code (0:OK, -1:error)
        """
        self._gpib_connection.write('AMPR {0:f}'.format(power))

        return 0

    def get_frequency(self):
        """ Gets the frequency of the microwave output.

        @return float: frequency (in Hz), which is currently set for this device
        """
        return float(self._gpib_connection.query('FREQ ?'))

    def set_frequency(self, freq=0.):
        """ Sets the frequency of the microwave output.

        @param float freq: the frequency (in Hz) set for this device

        @return int: error code (0:OK, -1:error)
        """

        self._gpib_connection.write('FREQ {0:e}'.format(freq))

        return 0

    def set_cw(self, frequency=None, power=None, useinterleave=None):
        """
        Configures the device for cw-mode and optionally sets frequency and/or power

        @param float frequency: frequency to set in Hz
        @param float power: power to set in dBm

        @return tuple(float, float, str): with the relation
            current frequency in Hz,
            current power in dBm,
            current mode
        """
        error = 0

        # disable modulation:
        self._gpib_connection.write('MODL 0')
        # and the subtype (analog,)
        self._gpib_connection.write('STYP 0')

        if frequency is not None:
            error = self.set_frequency(frequency)

        set_freq = self.get_frequency()

        if power is not None:
            error = self.set_power(power) | error

        set_power = self.get_power()

        self._internal_mode = 'cw'

        return set_freq, set_power, self._internal_mode

    def set_list(self, frequency=None, power=None):
        """ Sets the MW mode to list mode

        @param list freq: list of frequencies in Hz
        @param float power: MW power of the frequency list in dBm

        @return int: error code (0:OK, -1:error)
        """

        # delete a previously created list:
        self._gpib_connection.write('LSTD')

        #FIXME: catch the list number better:
        num_freq = len(frequency)

        self._gpib_connection.ask('LSTC? {0:d}'.format(num_freq))


        for index, entry in enumerate(frequency):
            self._gpib_connection.write('LSTP {0:d},{1:e},N,N,N,{2:f},N,N,N,N,N,N,N,N,N,N'.format(index, entry, power))

        # the commands contains 15 entries, which are related to the following
        # commands (in brackets the explanation):
        #
        #   '1,2,3,4,5,6,7,8,9,10,11,12,13,14,15'
        #
        #   1=FREQ (frequency)
        #   2=PHAS (phase)
        #   3=AMPL (Amplitude of LF (BNC output))
        #   4=OFSL (Offset of LF (BNC output))
        #   5=AMPR
        #   6=DISP
        #   7=MODL/ENBL/ENBR
        #   8=TYPE
        #   9=MFNC ()
        #     SFNC ()
        # ...

        # for entry in freq:
        #     self._gpib_connection.write('{0:e},N,N,N,{1:f},N,N,N,N,N,N,N,N,N,N'.format(entry, power))

        # enable the created list:
        self._gpib_connection.write('LSTE 1')
        self._internal_mode = 'list'    # since if now the device is switched on
                                        # the list will be used.

        curr_freq = self.get_frequency()
        curr_power = self.get_power()

        return curr_freq, curr_power, self._internal_mode

    def reset_listpos(self):
        """ Reset of MW List Mode position to start from first given frequency

        @return int: error code (0:OK, -1:error)
        """

        self._gpib_connection.write('LSTR')
        return 0

    def list_on(self):
        """ Switches on the list mode.

        @return int: error code (0:OK, -1:error)
        """
        self._internal_mode = 'list'
        return self.on()

    def sweep_on(self):
        """ Switches on the sweep mode.

        @return int: error code (0:OK, -1:error)
        """
        self._internal_mode = 'sweep'
        return self.on()

    def set_sweep(self, start, stop, step, power):
        """ Sweep from frequency start to frequency sto pin steps of width stop with power.
        """
        # set the type
        self._gpib_connection.write('MODL 3')
        # and the subtype
        self._gpib_connection.write('STYP 0')

        sweep_length = stop-start
        index = 0

        time_per_freq =  2e-3 # in Hz, 2ms per point assumed for the beginning
        # time it takes for a whole sweep, which is the rate of the sweep,
        # i.e. rate = 1/ time_for_freq_range
        rate = (sweep_length/step) * time_per_freq
        mod_type = 5 # blank
        mod_func = 3 # blank
        self._gpib_connection.write('LSTP {0:d},{1:e},N,N,N,{2:f},N,N,{3},{4},{5:e},{6:e},N,N,N,N'.format(index, start, power, mod_type, mod_func, rate, sweep_length))
        self._internal_mode = 'sweep'

        self.log.error('This was never tested!')

        return start, stop, step, power, self._internal_mode

    def reset_sweeppos(self):
        """ Reset of MW sweep position to start

        @return int: error code (0:OK, -1:error)
        """
        self._internal_mode = 'sweep'
        return self.reset_listpos()


    def set_ext_trigger(self, pol=TriggerEdge.RISING):
        """ Set the external trigger for this device with proper polarization.

        @param TriggerEdge pol: polarisation of the trigger (basically rising edge or
                        falling edge)

        @return int: error code (0:OK, -1:error)
        """

        #FIXME: that method is not used propertly. For now this
        self.log.warning('No external trigger channel can be set in this '
                         'hardware. Method will be skipped.')
        return 0

    def trigger(self):
        """ Trigger the next element in the list or sweep mode programmatically.

        Ensure that the Frequency was set when the function returns.
        """
        # serves as a software trigger
        self._gpib_connection.write('*TRG')
        # Check whether all pending operation are successful and finished:
        self._gpib_connection.ask('*OPC?')
        self._gpib_connection.ask('*OPC?')
        # while not bool(int(self._gpib_connection.ask('*OPC?').strip())):
        #     pass
        time.sleep(0.008)

