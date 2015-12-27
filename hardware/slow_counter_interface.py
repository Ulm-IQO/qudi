# -*- coding: utf-8 -*-

from core.util.customexceptions import InterfaceImplementationError

class SlowCounterInterface():
    """This is the Interface class to define the controls for the simple
    microwave hardware.
    """

    def set_up_clock(self, clock_frequency = None, clock_channel = None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of
                                      the clock
        @param string clock_channel: if defined, this is the physical channel
                                     of the clock

        @return int: error code (0:OK, -1:error)
        """

        raise InterfaceImplementationError('SlowCounterInterface>set_up_clock')
        return -1

    def set_up_counter(self,
                       counter_channel=None,
                       photon_source=None,
                       counter_channel2=None,
                       photon_source2=None,
                       clock_channel = None):
        """ Configures the actual counter with a given clock.

        @param string counter_channel: optional, this is the physical channel
                                       of the counter
        @param string photon_source: optional, this is the physical channel
                                     where the photons are to count from
        @param string clock_channel: optional, this specifies the clock for the
                                     counter

        @return int: error code (0:OK, -1:error)
        """

        raise InterfaceImplementationError('SlowCounterInterface>set_up_counter')
        return -1

    def get_counter(self, samples=None):
        """ Returns the current counts per second of the counter.

        @param int samples: if defined, number of samples to read in one go

        @return array(uint32): the photon counts per second
        """

        raise InterfaceImplementationError('SlowCounterInterface>get_counter')
        return 0.0

    def close_counter(self):
        """ Closes the counter and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """

        raise InterfaceImplementationError('SlowCounterInterface>close_counter')
        return -1

    def close_clock(self):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """

        raise InterfaceImplementationError('SlowCounterInterface>close_clock')
        return -1