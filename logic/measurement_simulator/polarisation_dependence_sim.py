# -*- coding: utf8 -*-
"""
This file contains a simulator for testing polarisation-dependence measurment tools

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

Copyright (C) 2016 Lachlan J. Rogers lachlan.rogers@uni-ulm.de
"""

from core.base import Base
from hardware.slow_counter_interface import SlowCounterInterface
from interface.motor_interface import MotorInterface
import time
import random
import numpy as np

class PolarizationDependenceSim(Base, SlowCounterInterface, MotorInterface):

    """ This class wraps the slow-counter dummy and adds polarisation angle dependence in order to simulate dipole polarisation measurements.  
    """

    _modclass = 'polarizationdepsim'
    _modtype = 'hardware'

    # Connectors
    _in = {'counter1': 'SlowCounterInterface'}

    _out = {'polarizationdependencesim': 'PolarizationDependenceSim'}

    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, configuration=config, callbacks = c_dict)
        
    def activation(self, e):
        """ Activation of the class
        """
        # name connected modules
        self._counter_hw = self.connector['in']['counter1']['object']

        # Required class variables to pretend to be the counter hardware
        self._photon_source2 = None

        # initialize class variables
        self.hwp_angle = 0

        self.dipole_angle = random.uniform(0,360)

        print('activated poldepsim')

    def deactivation(self,e):
        pass

    # Wrapping the slow counter methods
    def set_up_clock(self, clock_frequency = None, clock_channel = None):
        """ Direct pass-through to the counter hardware module
        """
        return self._counter_hw.set_up_clock(clock_frequency = clock_frequency, clock_channel = clock_channel)

    def set_up_counter(self,
                       counter_channel=None,
                       photon_source=None,
                       counter_channel2=None,
                       photon_source2=None,
                       clock_channel=None):
        """ Direct pass-through to the counter hardware module
        """
        return self._counter_hw.set_up_counter(counter_channel=counter_channel,
                                        photon_source=photon_source,
                                        counter_channel2=counter_channel2,
                                        photon_source2=photon_source2,
                                        clock_channel=clock_channel)

    def get_counter(self, samples=None):
        """ Direct pass-through to the counter hardware module
        """
        raw_count = self._counter_hw.get_counter(samples=samples)

        # modulate the counts with a polarisation dependence
        angle = np.radians(self.hwp_angle - self.dipole_angle)
        count = raw_count * np.sin(angle) * np.sin(angle)
        return count

    def close_counter(self):
        """ Direct pass-through to the counter hardware module
        """
        return self._counter_hw.close_counter()

    def close_clock(self, power=0):
        """ Direct pass-through to the counter hardware module
        """
        return self._counter_hw.close_clock(power=power)

    # Satisfy the motor interface

    def move_rel(self, axis=None, distance=None):
        """ Move the polarisation angle by relative degrees
        """
        if distance == None:
            #TODO warning
            pass
        self.hwp_angle += distance
        #TODO sleep
        return 0

    def move_abs(self, axis=None, position=None):
        """ Move the polarisation angle to absolute degrees
        """
        if position == None:
            #TODO warning
            pass
        self.hwp_angle = position
        #TODO sleep
        return 0

    def abort(self):
        return 0

    def get_pos(self, axis=None):
        return self.hwp_angle

    def get_status(self):
        return 0

    def calibrate(self, axis=None):
        self.hwp_angle = 0
        return 0

    def get_velocity(self, axis=None):
        # TODO set a sleep duration
        return 1

    def set_velocity(self, axis=None, velocity=None):
        # TODO set a sleep duration
        return 0
