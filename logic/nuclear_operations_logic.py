# -*- coding: utf-8 -*-

"""
This file contains the QuDi Logic to control Nuclear Operations.

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


class NuclearOperationsLogic(GenericLogic):
    """ A higher order logic, which combines several lower class logic modules
        in order to perform measurements and manipulations of nuclear spins.

    DISCLAIMER:
    ===========

    This module has two major issues:
        - a lack of proper documentation of all the methods
        - usage of tasks is not implemented and therefore direct connection to
          all the modules is used (I tried to compress as good as possible all
          the part, where access to other modules occurs so that a later
          replacement would be easier and one does not have to search throughout
          the whole file.)

    The state of this module is considered to be UNSTABLE.

    I am currently working on that and will from time to time improve the status
    of this module. So if you want to use it, be aware that there might appear
    drastic changes.
    ---
    Alexander Stark

    """

    _modclass = 'NuclearOperationsLogic'
    _modtype = 'logic'

        ## declare connectors
    _in = {'sequencegenerationlogic': 'SequenceGenerationLogic',
           'traceanalysislogic': 'TraceAnalysisLogic',
           'odmrlogic': 'ODMRLogic',
           'savelogic': 'SaveLogic',
           'optimizerlogic': 'OptimizerLogic',
           'scannerlogic':'ScannerLogic'}
    _out = {'nuclearoperationlogic': 'NuclearOperationsLogic'}

    def __init__(self, manager, name, config, **kwargs):
        # declare actions for state transitions
        state_actions = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}
        GenericLogic.__init__(self, manager, name, config, state_actions,
                              **kwargs)

        self.logMsg('The following configuration was found.',
                    msgType='status')

        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]),
                        msgType='status')

    def activation(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """
        pass

    def deactivation(self, e):
        """ Deactivate the module properly.

        @param object e: Fysom.event object from Fysom class. A more detailed
                         explanation can be found in the method activation.
        """
        pass
