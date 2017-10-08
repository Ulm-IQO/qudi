# -*- coding: utf-8 -*-

"""
This file contains the Qudi Hardware module for Rohde and Schwary SMR.

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

from core.module import Base, ConfigOption
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

    _modclass = 'MicrowaveSMR'
    _modtype = 'hardware'

    _gpib_address = ConfigOption('gpib_address', missing='error')
    _gpib_timeout = ConfigOption('gpib_timeout', 10, missing='warn')

    # Indicate how fast frequencies within a list or sweep mode can be changed:
    _FREQ_SWITCH_SPEED = 0.01  # Frequency switching speed in s (acc. to specs)

    def on_activate(self):
        """ Initialisation performed during activation of the module. """


        self._LIST_DWELL = 10e-3    # Dwell time for list mode to set how long
                                    # the device should stay at one list entry.
                                    # here dwell time can be between 1ms and 1s
        self._SWEEP_DWELL = 10e-3   # Dwell time for sweep mode to set how long
                                    # the device should stay at one list entry.
                                    # here dwell time can be between 10ms and 5s

        # trying to load the visa connection to the module
        self.rm = visa.ResourceManager()
        try:
            # such a stupid stuff, the timeout is specified here in ms not in
            # seconds any more, take that into account.
            self._gpib_connection = self.rm.open_resource(
                                        self._gpib_address,
                                        timeout=self._gpib_timeout*1000)

            self._gpib_connection.write_termination = "\r\n"
            self._gpib_connection.read_termination = None

            self.log.info('MicrowaveSMR: initialised and connected to '
                          'hardware.')
        except:
             self.log.error('MicrowaveSMR: could not connect to the GPIB '
                            'address "{0}".'.format(self._gpib_address))

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
        self._OPTIONS = [entry for entry in message if entry != '0']

        # get the info from the device:
        message = self._ask('*IDN?').strip().split(',')
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

        # self.off()  # turn the device off in case it is running
        # self._gpib_connection.close()   # close the gpib connection
        # self.rm.close()                 # close the resource manager
        return

    def get_limits(self):
        """ Retrieve the limits of the device.

        @return: object MicrowaveLimits: Serves as a container for the limits
                                         of the microwave device.
        """
        limits = MicrowaveLimits()
        limits.supported_modes = (MicrowaveMode.CW, MicrowaveMode.LIST)
        # the sweep mode seems not to work properly, comment it out:
                                  #MicrowaveMode.SWEEP)

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

        self._write(':OUTP OFF')

        if mode == 'list':
            self._write(':FREQ:MODE CW')

        # check whether
        while int(float(self._ask('OUTP:STAT?').strip())) != 0:
            time.sleep(0.2)

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

        if 'list' in mode:
            pow_list = self._ask(':LIST:POW?').strip().split(',')

            # THIS AMBIGUITY IN THE RETURN VALUE TYPE IS NOT GOOD AT ALL!!!
            #FIXME: Correct that as soon as possible in the interface!!!
            return np.array([float(pow) for pow in pow_list])

        else:
            return float(self._ask(':POW?'))

    def get_frequency(self):
        """  Gets the frequency of the microwave output.

        @return float|list: frequency(s) currently set for this device in Hz

        Returns single float value if the device is in cw mode.
        Returns list like [start, stop, step] if the device is in sweep mode.
        Returns list of frequencies if the device is in list mode.
        """

        # THIS AMBIGUITY IN THE RETURN VALUE TYPE IS NOT GOOD AT ALL!!!
        # FIXME: Correct that as soon as possible in the interface!!!

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

    def cw_on(self):
        """ Switches on cw microwave output.

        @return int: error code (0:OK, -1:error)

        Must return AFTER the device is actually running.
        """
        current_mode, is_running = self.get_status()
        if is_running:
            if current_mode == 'cw':
                return 0
            else:
                self.off()

        if current_mode != 'cw':
            self._write(':FREQ:MODE CW')

        self._write(':OUTP:STAT ON')
        self._write('*WAI')
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

        @return tuple(float, float, str): with the relation
            current frequency in Hz,
            current power in dBm,
            current mode
        """
        mode, is_running = self.get_status()
        if is_running:
            self.off()

        # Activate CW mode
        if mode != 'cw':
            self._write(':FREQ:MODE CW')

        # Set CW frequency
        if frequency is not None:
            self._write(':FREQ {0:f}'.format(frequency))

        # Set CW power
        if power is not None:
            self._write(':POW {0:f}'.format(power))

        # Return actually set values
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

        current_mode, is_running = self.get_status()
        if is_running:
            if current_mode == 'list':
                return 0
            else:
                self.off()

        self._write(':LIST:LEARN')
        self._write(':FREQ:MODE LIST')

        self._write(':OUTP:STAT ON')
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

        @return tuple(list, float, str):
            current frequencies in Hz,
            current power in dBm,
            current mode
        """

        mode, is_running = self.get_status()
        if is_running:
            self.off()

        # Bug in the micro controller of SMR20:
        # check the amount of entries, since the timeout is not working properly
        # and the SMR20 overwrites for too big entries the device-internal
        # memory such that the current firmware becomes corrupt. That is an
        # extreme annoying bug. Therefore catch too long lists.

        if len(frequency) > self._MAX_LIST_ENTRIES:
            self.log.error('The frequency list exceeds the hardware limitation '
                           'of {0} list entries. Aborting creation of a list '
                           'due to potential overwrite of the firmware on the '
                           'device.'.format(self._MAX_LIST_ENTRIES))

        else:

            self._write(':SOUR:LIST:MODE STEP')

            # It seems that we have to set a DWEL for the device, but it is not so
            # clear why it is necessary. At least there was a hint in the manual for
            # that and the instrument displays an error, when this parameter is not
            # set in the list mode (even it should be set by default):
            self._write(':SOUR:LIST:DWEL {0}'.format(self._LIST_DWELL))

            self._write(':TRIG1:LIST:SOUR EXT')
            self._write(':TRIG1:SLOP NEG')

            # delete all list entries and create/select a new list
            self._write(':SOUR:LIST:DEL:ALL')
            self._write(':SOUR:LIST:SEL "LIST1"')

            FreqString = ''
            PowerString = ''

            for f in frequency[:-1]:
                FreqString += ' {0:f}Hz,'.format(f)
                PowerString +=' {0:f}dBm,'.format(power)
            FreqString += ' {0:f}Hz'.format(frequency[-1])
            PowerString +=' {0:f}dBm'.format(power)

            self._write(':SOUR:LIST:FREQ' + FreqString)
            self._write(':SOUR:LIST:POW' + PowerString)
            self._write(':OUTP:AMOD FIX')

            # Apply settings in hardware
            self._write(':LIST:LEARN')
            # If there are timeout problems after this command, update the smiq
            # firmware to > 5.90 as there was a problem with excessive wait
            # times after issuing :LIST:LEARN over a GPIB connection in
            # firmware 5.88.
            self._write(':FREQ:MODE LIST')

            N = int(np.round(float(self._ask(':SOUR:LIST:FREQ:POIN?'))))

            if N != len(frequency):
                self.log.error('The input Frequency list does not corresponds '
                               'to the generated List from the SMR20.')

        actual_freq = self.get_frequency()
        actual_power_list = self.get_power() # in list mode we get a power list!
        # THIS AMBIGUITY IN THE RETURN VALUE TYPE IS NOT GOOD AT ALL!!!
        # FIXME: Ahh this is so shitty with the return value!!!
        actual_power = actual_power_list[0]
        mode, dummy = self.get_status()
        return actual_freq, actual_power, mode

    def reset_listpos(self):
        """ Reset of MW List Mode position to start from first given frequency

        @return int: error code (0:OK, -1:error)
        """

        self._gpib_connection.write(':ABOR:LIST')

        return 0

    def sweep_on(self):
        """ Switches on the sweep mode.

        @return int: error code (0:OK, -1:error)
        """
        mode, is_running = self.get_status()
        if is_running:
            if mode == 'sweep':
                return 0
            else:
                self.off()

        if mode != 'sweep':
            self._write('SOUR:FREQ:MODE SWE')

        self._write(':OUTP:STAT ON')
        dummy, is_running = self.get_status()
        while not is_running:
            time.sleep(0.2)
            dummy, is_running = self.get_status()
        return 0

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
        mode, is_running = self.get_status()

        if is_running:
            self.off()

        if mode != 'sweep':
            self._write('SOUR:FREQ:MODE SWE')

        self._write(':SOUR:SWE:FREQ:SPAC LIN')
        self._write(':SOUR:SWE:FREQ:STEP {0}'.format())

        if (start is not None) and (stop is not None) and (step is not None):
            self._write(':FREQ:START {0}'.format(start - step))
            self._write(':FREQ:STOP {0}'.format(stop))
            self._write(':SWE:FREQ:STEP {0}'.format(step))

        if power is not None:
            self._write(':POW {0:f}'.format(power))

        self._write(':TRIG:SOUR EXT')

        actual_power = self.get_power()
        freq_list = self.get_frequency()
        mode, dummy = self.get_status()
        return freq_list[0], freq_list[1], freq_list[2], actual_power, mode

    def reset_sweeppos(self):
        """
        Reset of MW sweep mode position to start (start frequency)

        @return int: error code (0:OK, -1:error)
        """
        self._command_wait(':ABORT')
        return 0

    def set_ext_trigger(self, pol=TriggerEdge.RISING):
        """ Set the external trigger for this device with proper polarization.

        @param TriggerEdge pol: polarisation of the trigger (basically rising edge or falling edge)

        @return object: current trigger polarity [TriggerEdge.RISING, TriggerEdge.FALLING]
        """
        if pol == TriggerEdge.RISING:
            edge = 'POS'
        elif pol == TriggerEdge.FALLING:
            edge = 'NEG'
        else:
            self.log.warning('No valid trigger polarity passed to microwave hardware module.')
            edge = None

        self._write(':TRIG1:LIST:SOUR EXT')
        self._write(':TRIG1:SLOP NEG')

        if edge is not None:
            self._write(':TRIG1:SLOP {0}'.format(edge))

        polarity = self._ask(':TRIG1:SLOP?')
        if 'NEG' in polarity:
            return TriggerEdge.FALLING
        else:
            return TriggerEdge.RISING

    # ================== Non interface commands: ==================

    def _set_power(self, power):
        """ Sets the microwave output power.

        @param float power: the power (in dBm) set for this device

        @return float: actual power set (in dBm)
        """

        # every time a single power is set, the CW mode is activated!
        self._write(':FREQ:MODE CW')
        self._write('*WAI')
        self._write(':POW {0:f};'.format(power))
        actual_power = self.get_power()
        return actual_power

    def _set_frequency(self, freq):
        """ Sets the frequency of the microwave output.

        @param float freq: the frequency (in Hz) set for this device

        @return int: error code (0:OK, -1:error)
        """

        # every time a single frequency is set, the CW mode is activated!
        self._write(':FREQ:MODE CW')
        self._write('*WAI')
        self._write(':FREQ {0:e}'.format(freq))
        # {:e} means a representation in float with exponential style
        return 0

    def turn_AM_on(self, depth):
        """ Turn on the Amplitude Modulation mode.

        @param float depth: modulation depth in percent (from 0 to 100%).

        @return int: error code (0:OK, -1:error)

        Set the Amplitude modulation based on an external DC signal source and
        switch on the device after configuration.
        """

        self._write('AM:SOUR EXT')
        self._write('AM:EXT:COUP DC')
        self._write('AM {0:f}'.format(float(depth)))
        self._write('AM:STAT ON')

        return 0

    def turn_AM_off(self):
        """ Turn off the Amlitude Modulation Mode.

        @return int: error code (0:OK, -1:error)
        """

        self._write(':AM:STAT OFF')

        return 0

    def trigger(self):
        """ Trigger the next element in the list or sweep mode programmatically.

        @return int: error code (0:OK, -1:error)

        Ensure that the Frequency was set AFTER the function returns, or give
        the function at least a save waiting time.
        """

        self._gpib_connection.write('*TRG')
        time.sleep(self._FREQ_SWITCH_SPEED)  # that is the switching speed
        return 0

    def reset_device(self):
        """ Resets the device and sets the default values."""
        self._write(':SYSTem:PRESet')
        self._write('*RST')
        self._write(':OUTP OFF')

        return 0

    def _ask(self, question):
        """ Ask wrapper.

        @param str question: a question to the device

        @return: the received answer
        """
        return self._gpib_connection.query(question)

    def _write(self, command, wait=True):
        """ Write wrapper.

        @param str command: a command to the device
        @param bool wait: optional, is the wait statement should be skipped.

        @return: str: the statuscode of the write command.
        """
        statuscode = self._gpib_connection.write(command)
        if wait:
            self._gpib_connection.write('*WAI')
        return statuscode
