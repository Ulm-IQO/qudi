# -*- coding: utf-8 -*-

"""
This file contains the Qudi interfuse between ODMR Logic and MW/Slow Counter HW.

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

import numpy as np

from core.module import Connector
from logic.generic_logic import GenericLogic
from interface.odmr_counter_interface import ODMRCounterInterface
from interface.microwave_interface import MicrowaveInterface
from interface.microwave_interface import TriggerEdge

class ODMRCounterMicrowaveInterfuse(GenericLogic, ODMRCounterInterface,
                                    MicrowaveInterface):
    """
    Interfuse to enable a software trigger of the microwave source but still
    having a hardware timed counter.

    This interfuse connects the ODMR logic with a slowcounter and a microwave
    device.
    """

    _modclass = 'ODMRCounterMicrowaveInterfuse'
    _modtype = 'interfuse'

    slowcounter = Connector(interface='SlowCounterInterface')
    microwave = Connector(interface='MicrowaveInterface')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module."""
        self._mw_device = self.get_connector('microwave')
        self._sc_device = self.get_connector('slowcounter') # slow counter device
        pass

    def on_deactivate(self):
        pass

    ### ODMR counter interface commands

    def set_up_odmr_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of the
                                      clock
        @param str clock_channel: if defined, this is the physical channel of
                                  the clock

        @return int: error code (0:OK, -1:error)
        """
        return self._sc_device.set_up_clock(clock_frequency=clock_frequency,
                                                   clock_channel=clock_channel)


    def set_up_odmr(self, counter_channel=None, photon_source=None,
                    clock_channel=None, odmr_trigger_channel=None):
        """ Configures the actual counter with a given clock.

        @param str counter_channel: if defined, this is the physical channel of
                                    the counter
        @param str photon_source: if defined, this is the physical channel where
                                  the photons are to count from
        @param str clock_channel: if defined, this specifies the clock for the
                                  counter
        @param str odmr_trigger_channel: if defined, this specifies the trigger
                                         output for the microwave

        @return int: error code (0:OK, -1:error)
        """

        return self._sc_device.set_up_counter(counter_channels=counter_channel,
                                                sources=photon_source,
                                                clock_channel=clock_channel,
                                                counter_buffer=None)


    def set_odmr_length(self, length=100):
        """Set up the trigger sequence for the ODMR and the triggered microwave.

        @param int length: length of microwave sweep in pixel

        @return int: error code (0:OK, -1:error)
        """
        self._odmr_length = length
        return 0


    def count_odmr(self, length = 100):
        """ Sweeps the microwave and returns the counts on that sweep.

        @param int length: length of microwave sweep in pixel

        @return float[]: the photon counts per second
        """

        counts = np.zeros((len(self.get_odmr_channels()), length))
        # self.trigger()
        for i in range(length):
            self.trigger()
            counts[:, i] = self._sc_device.get_counter(samples=1)[0]
        self.trigger()
        return counts

    def close_odmr(self):
        """ Close the odmr and clean up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        return self._sc_device.close_counter()

    def close_odmr_clock(self):
        """ Close the odmr and clean up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        return self._sc_device.close_clock()

    def get_odmr_channels(self):
        """ Return a list of channel names.

        @return list(str): channels recorded during ODMR measurement
        """
        return self._sc_device.get_counter_channels()

    ### ----------- Microwave interface commands -----------

    def trigger(self):

        return self._mw_device.trigger()


    def off(self):
        """
        Switches off any microwave output.
        Must return AFTER the device is actually stopped.

        @return int: error code (0:OK, -1:error)
        """
        return self._mw_device.off()

    def get_status(self):
        """
        Gets the current status of the MW source, i.e. the mode (cw, list or sweep) and
        the output state (stopped, running)

        @return str, bool: mode ['cw', 'list', 'sweep'], is_running [True, False]
        """
        return self._mw_device.get_status()

    def get_power(self):
        """
        Gets the microwave output power for the currently active mode.

        @return float: the output power in dBm
        """
        return self._mw_device.get_power()

    def get_frequency(self):
        """
        Gets the frequency of the microwave output.
        Returns single float value if the device is in cw mode.
        Returns list like [start, stop, step] if the device is in sweep mode.
        Returns list of frequencies if the device is in list mode.

        @return [float, list]: frequency(s) currently set for this device in Hz
        """
        return self._mw_device.get_frequency()

    def cw_on(self):
        """
        Switches on cw microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        return self._mw_device.cw_on()

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
        return self._mw_device.set_cw(frequency=frequency, power=power)

    def list_on(self):
        """
        Switches on the list mode microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        return self._mw_device.list_on()

    def set_list(self, frequency=None, power=None):
        """
        Configures the device for list-mode and optionally sets frequencies and/or power

        @param list frequency: list of frequencies in Hz
        @param float power: MW power of the frequency list in dBm

        @return list, float, str: current frequencies in Hz, current power in dBm, current mode
        """
        return self._mw_device.set_list(frequency=frequency, power=power)

    def reset_listpos(self):
        """
        Reset of MW list mode position to start (first frequency step)

        @return int: error code (0:OK, -1:error)
        """
        return self._mw_device.reset_listpos()

    def sweep_on(self):
        """ Switches on the sweep mode.

        @return int: error code (0:OK, -1:error)
        """
        return self._mw_device.sweep_on()

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
        return self._mw_device.set_sweep(start=start, stop=stop, step=step,
                                         power=power)

    def reset_sweeppos(self):
        """
        Reset of MW sweep mode position to start (start frequency)

        @return int: error code (0:OK, -1:error)
        """
        return self._mw_device.reset_sweeppos()

    def set_ext_trigger(self, pol=TriggerEdge.RISING):
        """ Set the external trigger for this device with proper polarization.

        @param TriggerEdge pol: polarisation of the trigger (basically rising edge or falling edge)

        @return object: current trigger polarity [TriggerEdge.RISING, TriggerEdge.FALLING]
        """
        return self._mw_device.set_ext_trigger(pol=pol)

    def get_limits(self):
        """ Return the device-specific limits in a nested dictionary.

          @return MicrowaveLimits: Microwave limits object
        """
        return self._mw_device.get_limits()
