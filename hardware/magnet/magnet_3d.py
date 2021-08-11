# -*- coding: utf-8 -*-

"""
This module controls a 3D magnet.

The 3D magnet consists of three 1D magnets, to which it needs to be connected to.

Config for copy paste:
    magnet_3d:
        module.Class: 'magnet.3dmagnet.magnet_3d'
        connect:
            magnet_x: 'magnet_x'
            magnet_y: 'magnet_y'
            magnet_z: 'magnet_z'


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
from qtpy import QtCore

from core.module import Base
from core.connector import Connector


class magnet_3d(Base):

    # declare connector
    # Note: you must create the interface file and give it to the class in the hardware file.
    magnet_x = Connector(interface='Magnet1DInterface')
    magnet_y = Connector(interface='Magnet1DInterface')
    magnet_z = Connector(interface='Magnet1DInterface')

    # create signal to logic
    sigRampFinished = QtCore.Signal()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    def on_activate(self):
        self._magnet_x = self.magnet_x()
        self._magnet_y = self.magnet_y()
        self._magnet_z = self.magnet_z()


    def on_deactivate(self):
        # Deactivate the individual 1D magnets.
        # This is important because this ramps the field to zero.
        self._magnet_x.on_deactivate()
        self._magnet_y.on_deactivate()
        self._magnet_z.on_deactivate()


    def get_field(self):
        """Returns field in x,y,z direction."""
        #TODO: get value from hardware
        field_x = self._magnet_x.get_field()
        field_y = self._magnet_y.get_field()
        field_z = self._magnet_z.get_field()
        return[field_x,field_y,field_z]

    def ramp(self, target_field=[0,0,0]):
        """Ramps to the desired field in cartesian coordinates.

        If there is no danger of exceeding the max vectorial field, fast ramp is used. Otherwise safe ramp.

        Calculations are done in T.
        """

        #check if field exceeds specs
        self.check_field(target_field)

        # check for danger of exceeding max vectorial field 
        worst_case_field = [0,0,0]
        current_field = self.get_field()
        for i in range(len(target_field)):
            t = target_field[i]
            c = current_field[i]
            w =  max(abs(t),abs(c))
            worst_case_field[i] = w
        worst_case_amplitude = np.linalg.norm(worst_case_field)

        # ramp fast or slow
        if worst_case_amplitude < 1:
            self.fast_ramp(target_field)
        else:
            self.safe_ramp(target_field)

        #start timer
        self.ramping_state_timer = QtCore.QTimer()
        self.ramping_state_timer.timeout.connect(self._ramp_loop)
        self.ramping_state_timer.setInterval(1000)
        self.ramping_state_timer.start()

        return 0

    def _ramp_loop(self):
        """Periodically checks the ramping state, emits a signal once all three axes are finished.
        """
        state = self.get_ramping_state()
        if state == [2,2,2]:
            self.ramping_state_timer.stop()
            del self.ramping_state_timer
            self.sigRampFinished.emit()


    def pause_ramp(self):
        """Pauses the ramping process."""
        self._magnet_x.pause_ramp()
        self._magnet_y.pause_ramp()
        self._magnet_z.pause_ramp()
        return 0
    
    def continue_ramp(self):
        """Continues the ramping process."""
        self._magnet_x.continue_ramp()
        self._magnet_y.continue_ramp()
        self._magnet_z.continue_ramp()

    def ramp_to_zero(self):
        """Ramps all three 1D magnets to zero."""
        self._magnet_x.ramp_to_zero()
        self._magnet_y.ramp_to_zero()
        self._magnet_z.ramp_to_zero()
        

    def fast_ramp(self, target_field=[0,0,0]):
        """Ramps all three axes at once."""

        #check if field exceeds specs
        self.check_field(target_field)

        #ramp
        self._magnet_x.ramp(field_target=target_field[0])
        self._magnet_y.ramp(field_target=target_field[1])
        self._magnet_z.ramp(field_target=target_field[2])

    def safe_ramp(self, target_field=[0,0,0]):
        """Ramps to the target field in a safe way.
        
        Calculations are done for field units in Tesla. 
        If you want to use kG, change factor.
        """

        #check if field exceeds specs
        self.check_field(target_field)

        self.target_field = target_field
        
        # define the order of the axes for the magnetic field
        indices = np.argsort(self.target_field)
        self.order_axes = []
        for i in indices:
            if i == 0:
                self.order_axes.append('x')
            elif i == 1:
                self.order_axes.append('y')
            elif i == 2:
                self.order_axes.append('z')
        
        #specify with which axis to start
        self.current_axis_index = 0
        #start ramping on this axis
        axis = self.order_axes[self.current_axis_index]
        target = str(self.target_field[self.current_axis_index])
        eval('self._magnet_' + axis + '.ramp(field_target=' + target + ')')

        #start timer
        self.ramping_timer = QtCore.QTimer()
        self.ramping_timer.timeout.connect(self._safe_ramp_loop)
        self.ramping_timer.setInterval(1000)
        self.ramping_timer.start()


    def check_field(self,target_field):
        """Checks if the given field exceeds the constraints.
        
        Returns 0 if everything is okay.
        """

        target_amplitude = np.linalg.norm(target_field)
        if target_amplitude > 1 and target_field[0] !=0 and target_field[1] != 0:
            raise RuntimeError('Max vector field 1T exceeded')
        elif abs(target_field[2]) > 6:
            raise RuntimeError('Max z-field 6T exceeded')
        else:
            return 0


    def get_ramping_state(self):
        """Returns the ramping state of all three 1D magnets.
        
        For meaning of values refer to doc of get_ramping_state on 1D magnet.

        @return: list of ints with ramping status [status_x,status_y,status_z].
        """
        status_x = self._magnet_x.get_ramping_state()
        status_y = self._magnet_y.get_ramping_state()
        status_z = self._magnet_z.get_ramping_state()
        status = [status_x[0],status_y[0],status_z[0]]
        return status


    def _safe_ramp_loop(self):
        """ Internal function to ramp in a save way
        """
        axis = self.order_axes[self.current_axis_index]
        status = eval('self._magnet_' + axis + '.get_ramping_state()')
        if status == 2: #HOLDING at the target field/current
            #go to next axis
            self.current_axis_index += 1
            # end timer if all axes are finished
            if self.current_axis_index == 3:
                self.ramping_timer.stop()
                del self.ramping_timer
                del self.target_field
                return 0
            #update parameters
            axis = self.order_axes[self.current_axis_index]
            target = str(self.target_field[self.current_axis_index])
            #start ramping there
            eval('self._magnet_' + axis + '.ramp(field_target=' + target + ')')
        else:
            print(status)
            