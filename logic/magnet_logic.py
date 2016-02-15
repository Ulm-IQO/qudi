# -*- coding: utf-8 -*-

"""
This file contains the dummy for a motorized stage interface.

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

Copyright (C) 2016 Alexander Stark alexander.stark@uni-ulm.de
"""

from logic.generic_logic import GenericLogic

class MagnetLogic(GenericLogic):
    """This is the Interface class to define the controls for the simple
    magnet hardware.
    """
    _modclass = 'magnetlogic'
    _modtype = 'logic'
    ## declare connectors
    _in = {'magnetstage': 'MagnetInterface'}


    _out = {'magnetlogic': 'MagnetLogic'}

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}
        GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)

        self.logMsg('The following configuration was found.',
                    msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')





    def activation(self, e):
        """ Initialisation performed during activation of the module.
        """

        self._magnet_device = self.connector['in']['magnetstage']['object']


#        self.testing()

    def deactivation(self, e):
        pass


    def get_hardware_constraints(self):
        return self._magnet_device.get_constraints()