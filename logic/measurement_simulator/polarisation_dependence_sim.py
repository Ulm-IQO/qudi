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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from core.base import Base
from interface.slow_counter_interface import SlowCounterInterface
from interface.motor_interface import MotorInterface
from pyqtgraph.Qt import QtCore
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

    _move_signal = QtCore.Signal()

    def on_activate(self, e):
        """ Activation of the class
        """
        # name connected modules
        self._counter_hw = self.connector['in']['counter1']['object']

        # Required class variables to pretend to be the counter hardware
        self._photon_source2 = None

        # initialize class variables
        self.hwp_angle = 0

        self.dipole_angle = random.uniform(0,360)

        self.velocity = 10
        self.clock_frequency = 50
        self.forwards_motion = True
        self.moving = False

        # Signals
        self._move_signal.connect(self._move_step, QtCore.Qt.QueuedConnection)

    def on_deactivate(self,e):
        self._counter_hw.close_counter()
        self._counter_hw.close_clock()

    # Wrapping the slow counter methods
    def set_up_clock(self, clock_frequency = None, clock_channel = None):
        """ Direct pass-through to the counter hardware module
        """
        self.clock_frequency = clock_frequency
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
        count = raw_count * np.sin(angle) * np.sin(angle) + random.uniform(-0.1, 0.1)
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

        self.destination = self.hwp_angle + distance

        # Keep track of the motion direction so we will know when we are past the destination
        if distance > 0:
            self.forwards_motion = True
        else:
            self.forwards_motion = False

        self.moving = True
        self._move_signal.emit()
        return 0

    def move_abs(self, axis=None, position=None):
        """ Move the polarisation angle to absolute degrees
        """
        if position == None:
            #TODO warning
            pass
        self.destination = position

        # Keep track of the motion direction so we will know when we are past the destination
        if position > self.hwp_angle:
            self.forwards_motion = True
        else:
            self.forwards_motion = False

        self.moving = True
        self._move_signal.emit()
        return 0

    def _move_step(self):
        """Make movement steps in a threaded loop
        """

        # if abort is requested, then stop moving
        if not self.moving:
            return

        # If we have reached the destination then stop the movement
        if self.forwards_motion:
            if self.hwp_angle > self.destination:
                return
        else:
            if self.hwp_angle < self.destination:
                return

        # Otherwise make a movement step

        step_size = self.velocity / self.clock_frequency

        if self.forwards_motion:
            self.hwp_angle += step_size
        else:
            self.hwp_angle -= step_size

        time.sleep(1./self.clock_frequency)
        self._move_signal.emit()

    def abort(self):
        self.moving = False
        return 0

    def get_pos(self, axis=None):
        return self.hwp_angle

    def get_status(self):
        return 0

    def calibrate(self, axis=None):
        self.hwp_angle = 0
        return 0

    def get_velocity(self, axis=None):
        return self.velocity

    def set_velocity(self, axis=None, velocity=None):
        self.velocity = velocity
        return 0
