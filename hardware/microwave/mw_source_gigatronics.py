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

from core.module import Base, ConfigOption
from interface.microwave_interface import MicrowaveInterface
from interface.microwave_interface import MicrowaveLimits
from interface.microwave_interface import MicrowaveMode
from interface.microwave_interface import TriggerEdge


class MicrowaveGigatronics(Base, MicrowaveInterface):
    """ Hardware file for Gigatronics. Tested for the model 2400/2500. """

    _modclass = 'MicrowaveInterface'
    _modtype = 'hardware'

    _gpib_address = ConfigOption('gpib_address', missing='error')
    _gpib_timeout = ConfigOption('gpib_timeout', 10, missing='warn')

    # Indicate how fast frequencies within a list or sweep mode can be changed:
    _FREQ_SWITCH_SPEED = 0.009  # Frequency switching speed in s (acc. to specs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # trying to load the visa connection to the module
        self.rm = visa.ResourceManager()
        try:
            self._gpib_connection = self.rm.open_resource(self._gpib_address,
                                                          read_termination='\r\n',
                                                          timeout=self._gpib_timeout*1000)
        except:
            self.log.error('This is MWgigatronics: could not connect to the GPIB address >>{}<<.'
                           ''.format(self._gpib_address))
            raise
        self._gpib_connection.write('*RST')
        idnlist = []
        while len(idnlist) < 3:
            idnlist = self._gpib_connection.query('*IDN?').split(', ')
            time.sleep(0.1)
        self.model = idnlist[1]
        self.log.info('MWgigatronics initialised and connected to hardware.')

        # Settings must be locally saved because the SCPI interface of that device is too bad to
        # query those values.
        self._freq_list = list()
        self._list_power = -144
        self._cw_power = -144
        self._cw_frequency = 2870.0e6

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._gpib_connection.close()
        self.rm.close()

    def get_limits(self):
        """Limits of Gigatronics 2400/2500 microwave source series.

          return MicrowaveLimits: limits of the particular Gigatronics MW source model
        """
        limits = MicrowaveLimits()
        limits.supported_modes = (MicrowaveMode.CW, MicrowaveMode.LIST)

        limits.min_frequency = 100e3
        limits.max_frequency = 20e9

        limits.min_power = -144
        limits.max_power = 10

        limits.list_minstep = 0.1
        limits.list_maxstep = 20e9
        limits.list_maxentries = 4000

        limits.sweep_minstep = 0.1
        limits.sweep_maxstep = 20e9
        limits.sweep_maxentries = 10001

        if self.model.startswith('2508'):
            limits.max_frequency = 8e9
        elif self.model.startswith('2520'):
            limits.max_frequency = 20e9
        elif self.model.startswith('2526'):
            limits.max_frequency = 26.5e9
        elif self.model.startswith('2540'):
            limits.max_frequency = 40e9
        else:
            self.log.warn('Unknown Gigatronics model, you are on your own!')

        return limits

    def _command_wait(self, command_str):
        """
        Writes the command in command_str via GPIB and waits until the device has finished
        processing it.

        @param command_str: The command to be written
        """
        self._gpib_connection.write(command_str)
        self._gpib_connection.write('*WAI')
        while int(float(self._gpib_connection.query('*OPC?'))) != 1:
            time.sleep(0.2)
        return

    def off(self):
        """
        Switches off any microwave output.
        Must return AFTER the device is actually stopped.

        @return int: error code (0:OK, -1:error)
        """
        self._gpib_connection.write(':OUTP:STAT OFF')
        while int(float(self._gpib_connection.query(':OUTP:STAT?'))) != 0:
            time.sleep(0.2)
        return 0

    def get_status(self):
        """
        Gets the current status of the MW source, i.e. the mode (cw, list or sweep) and
        the output state (stopped, running)

        @return str, bool: mode ['cw', 'list', 'sweep'], is_running [True, False]
        """
        is_running = bool(int(float(self._gpib_connection.query(':OUTP:STAT?'))))
        mode = self._gpib_connection.query(':MODE?').strip('\n').lower()
        return mode, is_running

    def get_power(self):
        """
        Gets the microwave output power.

        @return float: the power set at the device in dBm
        """
        mode, dummy = self.get_status()
        if mode == 'list':
            return self._list_power
        else:
            return float(self._gpib_connection.query(':POW?'))

    def get_frequency(self):
        """
        Gets the frequency of the microwave output.
        Returns single float value if the device is in cw mode.
        Returns list like [start, stop, step] if the device is in sweep mode.
        Returns list of frequencies if the device is in list mode.

        @return [float, list]: frequency(s) currently set for this device in Hz
        """
        mode, is_running = self.get_status()
        if 'cw' in mode:
            return_val = float(self._gpib_connection.query(':FREQ?'))
        elif 'list' in mode:
            return_val = self._freq_list
        else:
            return_val = -1
        return return_val

    def cw_on(self):
        """ Switches on any preconfigured microwave output.

        @return int: error code (0:OK, -1:error)
        """
        mode, is_running = self.get_status()
        if is_running:
            if mode == 'cw':
                return 0
            else:
                self.off()

        if mode != 'cw':
            self.set_cw()

        self._gpib_connection.write(':OUTP:STAT ON')
        dummy, is_running = self.get_status()
        while not is_running:
            time.sleep(0.2)
            dummy, is_running = self.get_status()
        return 0

    def set_cw(self, frequency=None, power=None):
        """
        Configures the device for cw-mode and optionally sets frequency and/or power

        @param float frequency: frequency to set in Hz
        @param float power: power to set in dBm

        @return float, float, str: current frequency in Hz, current power in dBm, current mode
        """
        mode, is_running = self.get_status()
        if is_running:
            self.off()

        if mode != 'cw':
            self._command_wait(':MODE CW')

        if frequency is not None:
            self._command_wait(':FREQ {0:e}'.format(frequency))
        else:
            self._command_wait(':FREQ {0:e}'.format(self._cw_frequency))

        if power is not None:
            self._command_wait(':POW {0:f} DBM'.format(power))
        else:
            self._command_wait(':POW {0:f} DBM'.format(self._cw_power))

        mode, dummy = self.get_status()
        self._cw_frequency = self.get_frequency()
        self._cw_power = self.get_power()
        return self._cw_frequency, self._cw_power, mode

    def list_on(self):
        """
        Switches on the list mode microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        mode, is_running = self.get_status()
        if is_running:
            if mode == 'list':
                return 0
            else:
                self.off()

        if mode != 'list':
            self.set_list()

        self._gpib_connection.write(':OUTP:STAT ON')
        dummy, is_running = self.get_status()
        while not is_running:
            time.sleep(0.2)
            dummy, is_running = self.get_status()
        return 0

    def set_list(self, frequency=None, power=None):
        """
        Configures the device for list-mode and optionally sets frequencies and/or power

        @param list frequency: list of frequencies in Hz
        @param float power: MW power of the frequency list in dBm

        @return list, float, str: current frequencies in Hz, current power in dBm, current mode
        """
        mode, is_running = self.get_status()

        if is_running:
            self.off()

        old_cw_power = self._cw_power
        old_cw_frequency = self._cw_frequency
        if frequency is not None:
            self.set_cw(frequency=frequency[0])
        else:
            self.set_cw(frequency=self._freq_list[0])
        if power is not None:
            self.set_cw(power=power)
        else:
            self.set_cw(power=self._list_power)
        self._cw_power = old_cw_power
        self._cw_frequency = old_cw_frequency

        #self._gpib_connection.write('*SRE 0')
        self._gpib_connection.write(':LIST:SEQ:AUTO ON')

        if frequency is not None:
            freqstring = '{0:.1f},'.format(frequency[0]) + ','.join(('{0:.1f}'.format(f) for f in frequency))
            self._freq_list = frequency
        else:
            freqstring = '{0:.1f},'.format(self._freq_list[0]) + ','.join(('{0:.1f}'.format(f) for f in self._freq_list))
        self._gpib_connection.write('LIST:FREQ {0:s}'.format(freqstring))

        if power is not None:
            powstring = '{0:.3f},'.format(power) + ','.join(('{0:.3f}'.format(power) for f in frequency))
            self._list_power = power
        else:
            powstring = '{0:.3f}'.format(self._list_power)
            powstring = powstring + len(self._freq_list) * ',{0:.3f}'.format(self._list_power)
        self._gpib_connection.write('LIST:POW {0:s}'.format(powstring))

        self._gpib_connection.write('LIST:DWEL 0.002000 S')
        self._gpib_connection.write('LIST:RFOffTime 0.000000 MS')
        self._gpib_connection.write('*OPC?')
        self._gpib_connection.write('LIST:PREC 1')
        # wait for '1' from OPC
        self._gpib_connection.read()
        self._gpib_connection.write(':LIST:REP STEP')
        self._gpib_connection.write(':TRIG:SOUR EXT')
        #self._gpib_connection.write('*SRE 239')
        #self._gpib_connection.write('*SRE 167')
        mode, dummy = self.get_status()
        return self._freq_list, self._list_power, mode

    def reset_listpos(self):#
        """ Reset of MW List Mode position to start from first given frequency

        @return int: error code (0:OK, -1:error)
        """
        self._gpib_connection.write(':MODE CW')
        self._gpib_connection.write(':MODE LIST')
        mode, is_running = self.get_status()
        return 0 if ('list' in mode) and is_running else -1

    def set_ext_trigger(self, pol=TriggerEdge.RISING):
        """ Set the external trigger for this device with proper polarization.

        @param TriggerEdge pol: polarisation of the trigger (basically rising edge or
                        falling edge)

        @return int: error code (0:OK, -1:error)
        """
        return TriggerEdge.RISING

    def sweep_on(self):
        """ Switches on the sweep mode.

        @return int: error code (0:OK, -1:error)
        """
        return -1

    def set_sweep(self, start=None, stop=None, step=None, power=None):
        """
        Configures the device for sweep-mode and optionally sets frequency start/stop/step
        and/or power

        @return float, float, float, float, str: current start frequency in Hz,
                                                 current stop frequency in Hz,
                                                 current frequency step in Hz,
                                                 current power in dBm,
                                                 current mode
        """
        return -1, -1, -1, -1, ''

    def reset_sweeppos(self):
        """
        Reset of MW sweep mode position to start (start frequency)

        @return int: error code (0:OK, -1:error)
        """
        return -1

    def trigger(self):
        """ Trigger the next element in the list or sweep mode programmatically.

        @return int: error code (0:OK, -1:error)

        Ensure that the Frequency was set AFTER the function returns, or give
        the function at least a save waiting time.
        """

        # WARNING:
        # The manual trigger functionality was not tested for this device!
        # Might not work well! Please check that!

        self._gpib_connection.write('*TRG')
        time.sleep(self._FREQ_SWITCH_SPEED)  # that is the switching speed
        return 0

