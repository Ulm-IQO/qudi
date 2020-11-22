# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware file to control Anritsu Microwave Device.

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
import numpy as np

from core.module import Base
from core.configoption import ConfigOption
from interface.microwave_interface import MicrowaveInterface
from interface.microwave_interface import MicrowaveLimits
from interface.microwave_interface import MicrowaveMode
from interface.microwave_interface import TriggerEdge


class MicrowaveAnritsu(Base, MicrowaveInterface):
    """ Hardware control file for Anritsu Devices.

    Tested for the model MG3691C with OPTION 2.
    cw and list modes are tested.
    Important: Trigger for frequency sweep is totally independent with most trigger syntax.
            In addition, it has to be Aux I/O pin connection.

    Example config for copy-paste:

    mw_source_anritsu_mg3691c:
        module.Class: 'microwave.mw_source_anritsu_mg3691.MicrowaveAnritsu'
        gpib_address: 'GPIB0::12::INSTR'
        gpib_timeout: 10 # in seconds

    """

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
            self._gpib_connection = self.rm.open_resource(
                self._gpib_address,
                timeout=self._gpib_timeout*1000)
        except:
            self.log.error('This is MWanritsu: could not connect to the GPIB '
                        'address >>{}<<.'.format(self._gpib_address))
            raise
        self._gpib_connection.write('SYST:LANG "SCPI"')
        self.model = self._gpib_connection.query('*IDN?').split(',')[1]
        self.log.info('MicrowaveAnritsu initialised and connected to '
                'hardware.')

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._gpib_connection.close()
        self.rm.close()

    def _command_wait(self, command_str):
        """
        Writes the command in command_str via GPIB and waits until the device has finished
        processing it.

        @param command_str: The command to be written
        """
        self._gpib_connection.write(command_str+'*WAI')
        return

    def get_limits(self):
        """ Right now, this is for Anritsu MG3691C with Option 2 only."""
        limits = MicrowaveLimits()
        limits.supported_modes = (MicrowaveMode.CW, MicrowaveMode.LIST)

        limits.min_frequency = 10e6
        limits.max_frequency = 20e9

        limits.min_power = -130
        limits.max_power = 30

        limits.list_minstep = 0.001
        limits.list_maxstep = 10e9
        limits.list_maxentries = 10001

        limits.sweep_minstep = 0.001
        limits.sweep_maxstep = 10e9
        limits.sweep_maxentries = 10001
        if self.model == 'MG3961C':
            limits.max_frequency = 10e9
            limits.min_frequency = 10e6
            limits.min_power = -130
            limits.max_power = 30
        return limits

    def off(self):
        """
        Switches off any microwave output.
        Must return AFTER the device is actually stopped.

        @return int: error code (0:OK, -1:error)
        """
        self._gpib_connection.write('OUTP:STAT OFF')
        while int(self._gpib_connection.query('OUTP:STAT?').strip('\r\n')) != 0:
            time.sleep(0.2)
        return 0

    def get_status(self):
        """
        Gets the current status of the MW source, i.e. the mode (cw, list or sweep) and
        the output state (stopped, running)

        @return str, bool: mode ['cw', 'list', 'sweep'], is_running [True, False]
        """
        is_running = bool(int(self._gpib_connection.query('OUTP:STAT?').strip('\r\n')))
        mode = self._gpib_connection.query(':FREQ:MODE?').strip('\r\n')
        if mode == 'CW':
            mode = 'cw'
        if 'SWE' in mode:
            mode = 'sweep'
        if 'LIST' in mode:
            mode = 'list'
        return mode, is_running

    def get_power(self):
        """
        Gets the microwave output power.

        @return float: the power set at the device in dBm
        """
        if self.get_status()[0] == 'cw':
            power = float(self._gpib_connection.query(':POW?').strip('\r\n'))
        if self.get_status()[0] == 'list':
            self._command_wait(':LIST:IND 0')
            power = self._gpib_connection.query(':LIST:POW?').strip('\r\n')
        if self.get_status()[0] == 'sweep':
            power = self._gpib_connection.query(':POW?').strip('\r\n')
        return power

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
            return_val = float(self._gpib_connection.query(':FREQ?').strip('\r\n'))
        elif 'sweep' in mode:
            start = float(self._gpib_connection.query(':FREQ:STAR?').strip('\r\n'))
            stop = float(self._gpib_connection.query(':FREQ:STOP?').strip('\r\n'))
            step = float(self._gpib_connection.query(':SWE:FREQ:STEP?').strip('\r\n'))
            return_val = [start, stop, step]
        elif 'list' in mode:
            stop_index = int(self._gpib_connection.query(':LIST:STOP?').strip('\r\n'))
            self._gpib_connection.write(':LIST:IND {0}'.format(stop_index))
            stop = float(self._gpib_connection.query(':LIST:FREQ?').strip('\r\n'))
            self._gpib_connection.write(':LIST:IND 0')
            start = float(self._gpib_connection.query(':LIST:FREQ?').strip('\r\n'))
            step = (stop - start) / stop_index
            return_val = np.arange(start, stop+step, step)
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
            self._command_wait(':FREQ:MODE CW')

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
        @param bool useinterleave: If this mode exists you can choose it.

        @return float, float, str: current frequency in Hz, current power in dBm, current mode

        Interleave option is used for arbitrary waveform generator devices.
        """
        mode, is_running = self.get_status()
        if is_running:
            self.off()

        if mode != 'cw':
            self._command_wait(':FREQ:MODE CW')

        if frequency is not None:
            self._command_wait(':FREQ {0:f}'.format(frequency))

        if power is not None:
            self._command_wait(':POW {0:.2f}'.format(power))

        mode, dummy = self.get_status()
        actual_freq = self.get_frequency()
        actual_power = self.get_power()
        return actual_freq, actual_power, mode

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
            self._command_wait(':FREQ:MODE LIST')

        self._gpib_connection.write(':LIST:MODE MNT')

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

        if mode != 'list':
            self._command_wait(':FREQ:MODE LIST')
        self._command_wait(':LIST:IND 0')

        if frequency is not None:
            s = ' {0:f},'.format(frequency[0])
            for f in frequency[:-1]:
                s += ' {0:f},'.format(f)
            s += ' {0:f}'.format(frequency[-1])
            self._command_wait(':LIST:FREQ' + s)
            self._command_wait(':LIST:STAR 0')
            self._command_wait(':LIST:STOP {0}'.format(len(frequency)-1))
        self._gpib_connection.write(':LIST:MODE MAN')

        if power is not None:
            self._command_wait(':LIST:IND 0')
            self._command_wait(':LIST:POW {0}'.format((len(frequency)-1)*(str(power)+', ')+str(power)))

        self._command_wait(':LIST:IND 0')

        actual_power = self.get_power()
        actual_freq = self.get_frequency()
        mode, dummy = self.get_status()
        return actual_freq, actual_power, mode

    def reset_listpos(self):
        """
        Reset of MW list mode position to start (first frequency step)

        @return int: error code (0:OK, -1:error)
        """
        self._command_wait(':LIST:IND 0')
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
        actual_power = self.get_power()
        mode, dummy = self.get_status()
        return -1, -1, -1, actual_power, mode

    def reset_sweeppos(self):
        """
        Reset of MW sweep mode position to start (start frequency)

        @return int: error code (0:OK, -1:error)
        """

        return -1

    def set_ext_trigger(self, pol, timing):
        """ Set the external trigger for this device with proper polarization.

        @param TriggerEdge pol: polarisation of the trigger (basically rising edge or falling edge)
        @param float timing: estimated time between triggers

        @return object, float: current trigger polarity [TriggerEdge.RISING, TriggerEdge.FALLING],
            trigger timing
        """
        if pol == TriggerEdge.RISING:
            edge = 'POS'
        elif pol == TriggerEdge.FALLING:
            edge = 'NEG'
        else:
            self.log.warning('No valid trigger polarity passed to microwave hardware module.')
            edge = None

        if edge is not None:
            self._command_wait(':TRIG:SEQ3:SLOP {0}'.format(edge))

        polarity = self._gpib_connection.query(':TRIG:SEQ3:SLOP?').strip('\r\n')
        if polarity == 'NEG':
            return TriggerEdge.FALLING, timing
        else:
            return TriggerEdge.RISING, timing

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

