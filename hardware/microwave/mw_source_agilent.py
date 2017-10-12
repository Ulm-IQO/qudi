# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware file to control Agilent microwave device.
The hardware file was tested using the model N9310A.

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


class MicrowaveAgilent(Base, MicrowaveInterface):
    """ This is the Interface class to define the controls for the simple
        microwave hardware.
        The hardware file was tested using the model N9310A.
    """

    _modclass = 'MicrowaveAgilent'
    _modtype = 'hardware'

    _usb_address = ConfigOption('usb_address', missing='error')
    _usb_timeout = ConfigOption('usb_timeout', 100, missing='warn')


    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        try:
            self._usb_timeout = self._usb_timeout
            # trying to load the visa connection to the module
            self.rm = visa.ResourceManager()
            self._usb_connection = self.rm.open_resource(
                resource_name=self._usb_address,
                timeout=self._usb_timeout)

            self.log.info('MWAGILENT initialised and connected to hardware.')
            self.model = self._usb_connection.query('*IDN?').split(',')[1]
            self._FREQ_SWITCH_SPEED = 0.09  # Frequency switching speed in s (acc. to specs)
            #set trigger of Sweep and Point to be FALLING
            self.set_ext_trigger()
        except:
            self.log.error('This is MWagilent: could not connect to the GPIB '
                           'address >>{}<<.'.format(self._usb_address))

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """

        self._usb_connection.close()
        self.rm.close()
        return


    def off(self):
        """ Switches off any microwave output.

        @return int: error code (0:OK, -1:error)
        """
        # turn of sweeping (both "list" or ”sweep“）
        self._usb_connection.write(':SWEep:RF:STATe OFF')
        while int(float(self._usb_connection.query(':SWEep:RF:STATe?'))) != 0:
            time.sleep(0.2)
        # check if running
        mode, is_running = self.get_status()
        if not is_running:
            return 0
        self._usb_connection.write(':RFO:STAT OFF')
        while int(float(self._usb_connection.query(':RFO:STAT?'))) != 0:
            time.sleep(0.2)
        #self._mode ="cw"
        return 0

    def get_status(self):
        """
        Gets the current status of the MW source, i.e. the mode (cw, list or sweep) and
        the output state (stopped, running)

        @return str, bool: mode ['cw', 'list', 'sweep'], is_running [True, False]
        """

        is_running = bool(int(float(self._usb_connection.ask(":RFOutput:STATe?"))))

        if bool(int(float(self._usb_connection.ask(":SWEep:RF:STATe?")))):
            if self._usb_connection.ask(":SWEep:TYPE?") == "STEP":
                mode = "sweep"
            else:
                mode="list"
        else:
            mode="cw"
        return mode, is_running


    def get_power(self):
        """ Gets the microwave output power.

        @return float: the power set at the device in dBm
        """
        mode, is_running = self.get_status()
        if mode == 'list':
            #add the moment all powers in the list file should be the same
            self._usb_connection.write(':LIST:ROW:GOTO {0:e}'.format(1))
            return float(self._usb_connection.ask(':LIST:Amplitude?'))
        else:
            return float(self._usb_connection.query(':AMPL:CW?'))

    def get_frequency(self):
        """ Gets the frequency of the microwave output.

        @return float: frequency (in Hz), which is currently set for this device
        """
        mode, is_running = self.get_status()
        if 'cw' in mode:
            return_val = float(self._usb_connection.query(':FREQ:CW?'))
        elif 'sweep' in mode:
            start = float(self._usb_connection.ask(':SWE:RF:STAR?'))
            stop = float(self._usb_connection.ask(':SWE:RF:STOP?'))
            num_of_points = int(self._usb_connection.ask(':SWE:STEP:POIN?'))
            freq_range = stop - start
            step = freq_range / (num_of_points - 1)
            return_val = [start, stop, step]
        elif 'list' in mode:
            # get the number of rows and initalize output arraz
            current_rows = int(self._usb_connection.ask(':LIST:RF:POINts?'))
            return_val = np.zeros((current_rows,1))
            for ii in range(current_rows):
                # go to respective row
                self._usb_connection.write(':LIST:ROW:GOTO {0:e}'.format(ii + 1))
                return_val[ii] = float(self._command_wait(':LIST:RF?'))
        return return_val


    def cw_on(self):
        """ Switches on any preconfigured microwave output.

        @return int: error code (0:OK, -1:error)
        """
        current_mode, is_running = self.get_status()
        if is_running:
            if current_mode == 'cw':
                return 0
            else:
                self.off()

        self._usb_connection.write(':RFO:STAT ON')
        while not is_running:
            time.sleep(0.2)
            dummy, is_running = self.get_status()

        return 0

    def set_cw(self, freq=None, power=None, useinterleave=None):
        """ Sets the MW mode to cw and additionally frequency and power
        #For agilent device there is no CW mode, so just do nothing

        @param float freq: frequency to set in Hz
        @param float power: power to set in dBm
        @param bool useinterleave: If this mode exists you can choose it.

        @return int: error code (0:OK, -1:error)

        Interleave option is used for arbitrary waveform generator devices.
        """
        mode, is_running = self.get_status()
        if is_running:
            self.off()

        if freq is not None:
            self.set_frequency(freq)
        if power is not None:
            self.set_power(power)
        if useinterleave is not None:
            self.log.warning("No interleave available at the moment!")

        mode, is_running = self.get_status()
        actual_freq = self.get_frequency()
        actual_power = self.get_power()
        return actual_freq, actual_power, mode

    def list_on(self):
        """ Switches on the list mode.

        @return int: error code (1: ready, 0:not ready, -1:error)
        """
        current_mode, is_running = self.get_status()
        if is_running:
            if current_mode == 'list':
                return 0
            else:
                self.off()
        try:
            self._usb_connection.write(":SWEep:TYPE LIST")
            self._usb_connection.write(':SWE:RF:STAT ON')
            while int(float(self._usb_connection.query(':SWEep:RF:STATe?'))) != 1:
                time.sleep(0.2)
            self._usb_connection.write(':RFO:STAT ON')
            dummy, is_running = self.get_status()
            while not is_running:
                time.sleep(0.2)
                dummy, is_running = self.get_status()
            return 0
        except:
            self.log.warning("Turning on of List mode does not work")
            return -1


    def set_list(self, freq=None, power=None):
        """ There is no list mode for agilent
        # Also the list is created by giving 'start_freq, step, stop_freq'

        @param list freq: list of frequencies in Hz
        @param float power: MW power of the frequency list in dBm

        """
        mode, is_running = self.get_status()
        if is_running:
            self.off()

        if freq is not None:
            num_of_freq = len(freq)
            current_rows = int(self._usb_connection.ask(':LIST:RF:POINts?'))
            # adapt the length of the list
            while current_rows != num_of_freq:
                if current_rows > num_of_freq:
                    for kk in range(int(current_rows-num_of_freq)):
                        #always delete the second row (first might not work)
                        self._usb_connection.write(':LIST:ROW:DELete {0:e}'.format(2))
                        time.sleep(0.05)
                elif current_rows < num_of_freq:
                    for kk in range(int(num_of_freq-current_rows)):
                        self._usb_connection.write(':LIST:ROW:INsert {0:e}'.format(2))
                        time.sleep(0.05)
                current_rows = int(self._usb_connection.ask(':LIST:RF:POINts?'))
                self.log.info("adjusting list length again")

            for ii in range(current_rows):
                self._usb_connection.write(':LIST:ROW:GOTO {0:e}'.format(ii+1))
                time.sleep(0.1)
                self._usb_connection.write(':LIST:RF {0:e} Hz'.format(freq[ii]))
                time.sleep(0.25)
                if power is not None:
                    self._usb_connection.write(':LIST:Amplitude {0:e} dBm'.format(power))
                # seems to need some time
                time.sleep(0.25)

        else:
            if power is not None:
                current_rows = int(self._usb_connection.ask(':LIST:RF:POINts?'))
                for ii in range(current_rows):
                    self._usb_connection.write(':LIST:ROW:GOTO {0:e}'.format(ii + 1))
                    self._usb_connection.write(':LIST:Amplitude {0:e} dBm'.format(power))
                    # seems to need some time
                    time.sleep(0.5)
            else:
                self.log.warning("Not changing freq or power!")

        self._usb_connection.write(':SWE:REP CONT')
        self._usb_connection.write(':SWE:STRG EXT')
        #self._usb_connection.write(':SWE:STRG:SLOP EXTP')
        self._usb_connection.write(':SWE:PTRG EXT')
        self._usb_connection.write(':SWE:PTRG:SLOP EXTP')
        self._usb_connection.write(':SWE:DIR:UP')
        self.set_ext_trigger()

    #        self._usb_connection.write(':RFO:STAT ON')
    #        self._usb_connection.write(':SWE:RF:STAT ON')
        actual_power = self.get_power()
        # dont take actual frequencz arraz at the moment since this is far too slow
        #actual_freq = self.get_frequency()
        actual_freq = freq
        mode, dummy = self.get_status()
        return actual_freq, actual_power, mode



    def reset_listpos(self):
        """ Reset of MW List Mode position to start from first given frequency

        @return int: error code (0:OK, -1:error)
        """
        try:
            self._usb_connection.write(':RFO:STAT OFF')
            self._usb_connection.write(':SWEep:RF:STATe OFF')
            self._usb_connection.write(':LIST:ROW:GOTO 1')
            self._usb_connection.write(':SWEep:RF:STATe ON')
            self._usb_connection.write(':RFO:STAT ON')
            return 0
        except:
            self.log.error("Reset of list position did not work")
            return -1


    def sweep_on(self):
        """ Switches on the list mode.

        @return int: error code (0:OK, -1:error)
        """
        mode, is_running = self.get_status()
        if is_running:
            if mode == 'sweep':
                return 0
            else:
                self.off()
        try:
            self._usb_connection.write(":SWEep:TYPE STEP")
            self._usb_connection.write(':SWE:RF:STAT ON')
            while int(float(self._usb_connection.query(':SWEep:RF:STATe?'))) != 1:
                time.sleep(0.5)
            self._usb_connection.write(':RFO:STAT ON')
            dummy, is_running = self.get_status()
            while not is_running:
                time.sleep(0.5)
                dummy, is_running = self.get_status()
            #self._usb_connection.write('*WAI')
            return 0
        except:
            self.log.error("Turning on of sweep mode did not work!")
            return -1



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

        mode, is_running = self.get_status()

        if is_running:
            self.off()

        n = int(stop-start)/step + 1

        self._usb_connection.write(':SWE:RF:STAR {0:e} Hz'.format(start))
        self._usb_connection.write(':SWE:RF:STOP {0:e} Hz'.format(stop))
        self._usb_connection.write(':SWE:STEP:POIN {0}'.format(n))
        #self._usb_connection.write(':SWE:STEP:DWEL 10 ms')

        self.set_power(power)
        self._usb_connection.write(':SWE:REP CONT')
        self._usb_connection.write(':SWE:STRG EXT')
        #        self._usb_connection.write(':SWE:STRG:SLOP EXTP')
        self._usb_connection.write(':SWE:PTRG  EXT')
        #        self._usb_connection.write(':SWE:PTRG:SLOP EXTP')
        #self._usb_connection.write(':SWE:DIR:UP')
        #self._usb_connection.write('*WAI')
        self.set_ext_trigger()

        # short waiting time to prevent crashes
        time.sleep(0.2)

        freq_start = float(self._usb_connection.ask(':SWE:RF:STAR?'))
        freq_stop = float(self._usb_connection.ask(':SWE:RF:STOP?'))
        num_of_points = int(self._usb_connection.ask(':SWE:STEP:POIN?'))
        freq_range = freq_stop - freq_start
        freq_step = freq_range / (num_of_points -1)
        freq_power = self.get_power()
        mode = 'sweep'
        return freq_start, freq_stop, freq_step, freq_power, mode

    def _turn_off_output(self,repetitions=10):
        self._usb_connection.write(':RFO:STAT OFF')
        dummy, is_running = self.get_status()
        index = 0
        while is_running and index < repetitions:
            time.sleep(0.5)
            dummy, is_running = self.get_status()
            index =+ 1

        index = 0
        self._usb_connection.write(':SWE:RF:STAT OFF')
        while int(float(self._usb_connection.query(':SWEep:RF:STATe?'))) != 0  and index < repetitions:
            time.sleep(0.5)
            index =+ 1


    def _turn_on_output(self,repetitions=10):
        self._usb_connection.write(':SWE:RF:STAT ON')
        index = 0
        while int(float(self._usb_connection.query(':SWEep:RF:STATe?'))) != 1 and index < repetitions:
            time.sleep(0.5)
            index =+ 1
        self._usb_connection.write(':RFO:STAT ON')
        dummy, is_running = self.get_status()
        index = 0
        while not is_running and index < repetitions:
            time.sleep(0.5)
            dummy, is_running = self.get_status()
            index =+ 1

    def reset_sweeppos(self):
        """ Reset of MW List Mode position to start from first given frequency

        @return int: error code (0:OK, -1:error)
        """
        # turn off the sweepmode and the rf output and turn it on again
        # unfortunately sleep times seem to be neccessary
        time.sleep(0.5)
        self._turn_off_output()
        time.sleep(0.2)
        self._turn_on_output()

        return 0



    def set_ext_trigger(self, pol=TriggerEdge.FALLING):
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
            self._usb_connection.write(':SWE:PTRG:SLOP {0}'.format(edge))
            time.sleep(0.5)
            self._usb_connection.write(':SWE:STRG:SLOP {0}'.format(edge))
        except:
            self.log.error("Setting of trigger did not work!")
            return -1
        return 0


    def trigger(self):
        """ Trigger the next element in the list or sweep mode programmatically.

        @return int: error code (0:OK, -1:error)
        """

        start_freq = self.get_frequency()
        self._usb_connection.write(':TRIGger:IMMediate')
        time.sleep(self._FREQ_SWITCH_SPEED)
        curr_freq = self.get_frequency()
        if start_freq == curr_freq:
            self.log.error('Internal trigger for Agilent MW source did not work!')
            return -1

        return 0

    def get_limits(self):
        limits = MicrowaveLimits()
        limits.supported_modes = (MicrowaveMode.CW, MicrowaveMode.LIST, MicrowaveMode.SWEEP)

        limits.min_frequency = 9.0e3
        limits.max_frequency = 3.0e9

        limits.min_power = -144
        limits.max_power = 10

        limits.list_minstep = 0.1
        limits.list_maxstep = 3.0e9
        limits.list_maxentries = 4000

        limits.sweep_minstep = 0.1
        limits.sweep_maxstep = 3.0e9
        limits.sweep_maxentries = 10001

        if self.model == 'N9310A':
            limits.min_frequency = 9e3
            limits.max_frequency = 3.0e9
            limits.min_power = -127
            limits.max_power = 20
        else:
            self.log.warning('Model string unknown, hardware limits may be wrong.')
        #limits.list_maxstep = limits.max_frequency
        #limits.sweep_maxstep = limits.max_frequency
        return limits


    def set_power(self, power=0.):
        """ Sets the microwave output power.

        @param float power: the power (in dBm) set for this device

        @return int: error code (0:OK, -1:error)
        """
        if power is not None:
            self._command_wait(':AMPL:CW {0:f}'.format(power))
            return 0
        else:
            return -1


    def set_frequency(self, freq=None):
        """ Sets the frequency of the microwave output.

        @param float freq: the frequency (in Hz) set for this device

        @return int: error code (0:OK, -1:error)
        """
        if freq is not None:
            self._command_wait(':FREQ:CW {0:e} Hz'.format(freq))
            return 0
        else:
            return -1

    def _command_wait(self, command_str):
        """
        Writes the command in command_str via USB and waits until the device has finished
        processing it.

        @param command_str: The command to be written
        """
        self._usb_connection.write(command_str)
        self._usb_connection.write('*WAI')
        while int(float(self._usb_connection.query('*OPC?'))) != 1:
            time.sleep(0.2)

        return



