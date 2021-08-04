# -*- coding: utf-8 -*-

"""
This module controls a 3D magnet.

The 3D magnet consists of three 1D magnets, to which it needs to be connected to.

Config for copy paste:


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
    #Note: you must create the interface file and give it to the class in the hardware file.
    magnet_x = Connector(interface='Magnet1DInterface')
    magnet_y = Connector(interface='Magnet1DInterface')
    magnet_z = Connector(interface='Magnet1DInterface')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    def on_activate(self):
        self._magnet_x = self.magnet_x()
        self._magnet_y = self.magnet_y()
        self._magnet_z = self.magnet_z()

    def on_deactivate(self):
        pass


    def get_field(self):
        """Returns field in x,y,z direction."""
        #TODO: get value from hardware
        field_x = self._magnet_x.get_field()
        field_y = self._magnet_y.get_field()
        field_z = self._magnet_z.get_field()
        return[field_x,field_y,field_z]

    def fast_ramp(sef):
        pass

    def safe_ramp(self, target_field=[0,0,0]):
        """Ramps to the target in a safe way.
        
        Calculations are done for field units in Tesla. 
        If you want to use kG, change factor.
        """

        self.target_field = target_field

        #check if field exceeds specs
        target_amplitude = np.linalg.norm(self.target_field)
        if target_amplitude > 1 and self.target_field[0] !=0 and self.target_field[1] != 0:
            raise RuntimeError('Max vector field 1T exceeded')
        elif self.target_field[2] > 6:
            raise RuntimeError('Max z-field 6T exceeded')
        
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


    def _safe_ramp_loop(self):
        """ Internal function to ramp in a save way
        """
        axis = self.order_axes[self.current_axis_index]
        status = eval('self._magnet_' + axis + '.get_ramping_state()')
        if status == ['2']: #HOLDING at the target field/current
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

        
        
            