# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware file to control Anritsu 70GHz Device.

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
import time

from core.module import Base, ConfigOption
from interface.microwave_interface import MicrowaveInterface
from interface.microwave_interface import MicrowaveLimits
from interface.microwave_interface import MicrowaveMode
from interface.microwave_interface import TriggerEdge


class MicrowaveAnritsu70GHz(Base, MicrowaveInterface):
    """ This is the Interface class to define the controls for the simple
        microwave hardware.
    """
    _modclass = 'MicrowaveAanritsu70GHz'
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
                timeout=self._gpib_timeout*1000)
        except:
            self.log.error('Could not connect to the GPIB address >>{}<<.'
                           ''.format(self._gpib_address))
            raise
        # native command mode, some things are missing in SCPI mode
        self._gpib_connection.write('SYST:LANG \"NATIVE\"')
        # query model ID
        self.model = self._gpib_connection.query('*IDN?').split(',')[1]
        # Sets the RF output to 'off' at reset
        self._gpib_connection.write('RO1')
        # Reset device
        self._gpib_connection.write('RST')
        self.log.info('Anritsu {} initialised and connected to hardware.'.format(self.model))

        # FIXME: Due to a crappy command set one can not query a lot of stuff.
        self._is_running = False
        self._current_mode = 'cw'
        self._freq_list = list()
        self._list_power = -20
        self._cw_freq = 2.0e9
        self._cw_power = -20
        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._gpib_connection.close()
        self.rm.close()

    def get_limits(self):
        """ Right now, this is for Anritsu MG3696B only."""
        limits = MicrowaveLimits()
        limits.supported_modes = (MicrowaveMode.CW, MicrowaveMode.LIST)

        limits.min_frequency = 10e6
        limits.max_frequency = 70e9

        limits.min_power = -20
        limits.max_power = 10

        limits.list_minstep = 0.001
        limits.list_maxstep = 70e9
        limits.list_maxentries = 1999

        limits.sweep_minstep = 0.001
        limits.sweep_maxstep = 70e9
        limits.sweep_maxentries = 10001
        return limits

    def off(self):
        """ 
        Switches off any microwave output.
        Must return AFTER the device is actually stopped.

        @return int: error code (0:OK, -1:error)
        """
        self._gpib_connection.write('RF0')
        self._is_running = False
        # FIXME: Due to a missing output state query command one can not WAIT until it has stopped
        return 0

    def get_status(self):
        """ 
        Gets the current status of the MW source, i.e. the mode (cw, list or sweep) and 
        the output state (stopped, running)

        @return str, bool: mode ['cw', 'list', 'sweep'], is_running [True, False] 
        """
        return self._current_mode, self._is_running

    def get_power(self):
        """ 
        Gets the microwave output power for the currently active mode.

        @return float: the output power in dBm
        """
        mode, dummy = self.get_status()
        if mode == 'cw':
            power = float(self._gpib_connection.query('OL0'))
        else:
            power = self._list_power
        return power

    def get_frequency(self):
        """ 
        Gets the frequency of the microwave output.
        Returns single float value if the device is in cw mode. 
        Returns list like [start, stop, step] if the device is in sweep mode.
        Returns list of frequencies if the device is in list mode.

        @return [float, list]: frequency(s) currently set for this device in Hz
        """
        mode, dummy = self.get_status()
        if mode == 'cw':
            freq = 1e6 * float(self._gpib_connection.query('OF0'))
        else:
            freq = self._freq_list
        return freq

    def cw_on(self):
        """ 
        Switches on cw microwave output. 
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        mode, is_running = self.get_status()

        if mode != 'cw':
            self.set_cw()
        elif is_running:
            return 0

        self._gpib_connection.write('RF1')
        self._is_running = True
        # FIXME: Due to a missing output state query command one can not WAIT until it's running
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

        if frequency is None:
            self._gpib_connection.write('F0 {0:f} HZ'.format(self._cw_freq))
        else:
            self._gpib_connection.write('F0 {0:f} HZ'.format(frequency))
            self._cw_freq = frequency

        if power is None:
            self._gpib_connection.write('L0 {0:f} DM'.format(self._cw_power))
        else:
            self._gpib_connection.write('L0 {0:f} DM'.format(power))
            self._cw_power = power

        self._gpib_connection.write('ACW')
        self._current_mode = 'cw'

        mode, dummy = self.get_status()
        actual_frequency = self.get_frequency()
        actual_power = self.get_power()
        return actual_frequency, actual_power, mode

    def list_on(self):
        """
        Switches on the list mode microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        mode, is_running = self.get_status()
        if is_running:
            if mode != 'list':
                self.off()
            else:
                return 0

        # enter list mode
        self._gpib_connection.write('LST')
        # select list number 0
        self._gpib_connection.write('ELN0')
        # select list index 0
        self._gpib_connection.write('ELI0000')
        self._current_mode = 'list'
        # Set list start index
        self._gpib_connection.write('LIB0000')
        # Set list stop index
        self._gpib_connection.write('LIE{0:04d}'.format(len(self._freq_list)))
        # Set manual trigger mode
        self._gpib_connection.write('MNT')
        # Learn list
        self._gpib_connection.write('LEA')
        # activate output
        self._gpib_connection.write('RF1')
        self._is_running = True
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
        if mode != 'list':
            self._gpib_connection.write('LST')
            self._gpib_connection.write('ELN0')
            self._gpib_connection.write('ELI0000')
            self._current_mode = 'list'

        # if self.set_cw(freq[0], power) != 0:
        #     error = -1

        if frequency is not None:
            flist = '{0:f} HZ'.format(frequency[0])
            for f in frequency:
                flist += ', {0:f} HZ'.format(f)
            self._gpib_connection.write('LF ' + flist)
            self._freq_list = frequency

        if power is not None:
            plist = '{0:f} DM'.format(power)
            for f in self._freq_list:
                plist += ', {0:f} DM'.format(power)
            self._gpib_connection.write('LP ' + plist)
            self._list_power = power

        # Set list start index
        self._gpib_connection.write('LIB0000')
        # Set list stop index
        self._gpib_connection.write('LIE{0:04d}'.format(len(self._freq_list)))
        # Set manual trigger mode
        self._gpib_connection.write('MNT')

        mode, dummy = self.get_status()
        return self.get_frequency(), self.get_power(), mode

    def reset_listpos(self):
        """ 
        Reset of MW list mode position to start (first frequency step)

        @return int: error code (0:OK, -1:error)
        """
        self._gpib_connection.write('ELI0000')
        return 0

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
        return -1.0, -1.0, -1.0, -1.0, self._current_mode

    def reset_sweeppos(self):
        """ 
        Reset of MW sweep mode position to start (start frequency)

        @return int: error code (0:OK, -1:error)
        """
        return -1

    def set_ext_trigger(self, pol=TriggerEdge.RISING):
        """ Set the external trigger for this device with proper polarization.

        @param TriggerEdge pol: polarisation of the trigger (basically rising edge or falling edge)

        @return object: current trigger polarity [TriggerEdge.RISING, TriggerEdge.FALLING]
        """
        return TriggerEdge.RISING

    # FIXME: All of the below code is not tested and was not working even before the overhaul.
    # def sweep_on(self):
    #     """ Switches on the sweep mode.
    #
    #     @return int: error code (0:OK, -1:error)
    #     """
    #     mode, is_running = self.get_status()
    #
    #     if is_running:
    #         if mode != 'sweep':
    #             self.off()
    #         else:
    #             return 0
    #
    #     self._gpib_connection.write('SSP')
    #     self._current_mode = 'sweep'
    #     self._gpib_connection.write('RF1')
    #     self._is_running = True
    #     return 0
    #
    # def set_sweep(self, start=None, stop=None, step=None, power=None):
    #     """
    #     Configures the device for sweep-mode and optionally sets frequency start/stop/step
    #     and/or power
    #
    #     @return float, float, float, float, str: current start frequency in Hz,
    #                                              current stop frequency in Hz,
    #                                              current frequency step in Hz,
    #                                              current power in dBm,
    #                                              current mode
    #     """
    #     mode, is_running = self.get_status()
    #
    #     if is_running:
    #         self.off()
    #     if mode != 'sweep':
    #         self._gpib_connection.write('SSP')
    #         self._current_mode = 'sweep'
    #
    #     if (start is not None) and (stop is not None) and (step is not None):
    #         self._gpib_connection.write('F1 {0:f} Hz'.format(start - step))
    #         self._gpib_connection.write('SYZ {0:f} Hz'.format(step))
    #         self._gpib_connection.write('F2 {0:f} Hz'.format(stop))
    #
    #     if power is not None:
    #         self._gpib_connection.write('L1 {0:f} DM'.format(power))
    #         self._gpib_connection.write('L2 {0:f} DM'.format(power))
    #
    #     self._gpib_connection.write('SF1')
    #     nrsteps = int(self._gpib_connection.query('OSS'))
    #     return nrsteps
    #
    # def reset_sweeppos(self):
    #     """
    #     Reset of MW sweep mode position to start (start frequency)
    #
    #     @return int: error code (0:OK, -1:error)
    #     """
    #     self._gpib_connection.write('RSS')
    #     return 0
