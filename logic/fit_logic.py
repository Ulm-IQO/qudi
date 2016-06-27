# -*- coding: utf-8 -*-
"""
This file contains the QuDi FitLogic class, which provides all
fitting methods imported from the files in logic/fitmethods.

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

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex

import importlib

from os import listdir
from os.path import isfile, join

class FitLogic(GenericLogic):
    """
    UNSTABLE:Jochen Scheuer

    Documentation to add a new fit model/estimator/funciton can be found in
    documentation/how_to_use_fitting.md or in the online documentation

    This is the fitting class where fit functions are defined and methods are
    implemented to process the data.

    For clarity reasons the fit function are imported from different files
    seperated by function type, e.g. gaussianlikemethods, sinemethods, generalmethods
    """
    _modclass = 'fitlogic'
    _modtype = 'logic'
    # declare connectors
    _out = {'fitlogic': 'FitLogic'}

    def __init__(self, manager, name, config, **kwargs):
        # declare actions for state transitions
        state_actions = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}
        GenericLogic.__init__(self, manager, name, config, state_actions,
                              **kwargs)
        # locking for thread safety
        self.lock = Mutex()

        filenames = []
        # for path in directories:
        path = join(self.get_main_dir(), 'logic', 'fitmethods')
        for f in listdir(path):
            if isfile(join(path, f)):
                if f[-3:] == '.py':
                    filenames.append(f[:-3])

        self.oneD_fit_methods = dict()
        self.twoD_fit_methods = dict()

        for files in filenames:

            mod = importlib.import_module('logic.fitmethods.{}'.format(files))
            for method in dir(mod):
                try:
                    if callable(getattr(mod, method)):
                        # import methods in Fitlogic
                        setattr(FitLogic, method, getattr(mod, method))
                        # add method to dictionary and define what
                        # estimators they have

                        # check if it is a make_<own fuction>_fit method
                        if (str(method).startswith('make_') and
                                str(method).endswith('_fit')):
                            # only add to dictionary if it is not already there
                            if 'twoD' in str(method) and str(method).split('_')[1] not in self.twoD_fit_methods:
                                self.twoD_fit_methods[str(method).split('_')[1]] = []
                            elif str(method).split('_')[1] not in self.oneD_fit_methods:
                                self.oneD_fit_methods[str(method)[5:-4]] = []
                        # if there is an estimator add it to the dictionary
                        if 'estimate' in str(method):
                            if 'twoD' in str(method):
                                try:  # if there is a given estimator it will be set or added
                                    if str(method).split('_')[1] in self.twoD_fit_methods:
                                        self.twoD_fit_methods[str(method).split('_')[1]] = self.twoD_fit_methods[
                                            str(method).split('_')[1]].append(str(method).split('_')[2])
                                    else:
                                        self.twoD_fit_methods[str(method).split('_')[1]] = [str(method).split('_')[2]]
                                except:  # if there is no estimator but only a standard one the estimator is empty
                                    if not str(method).split('_')[1] in self.twoD_fit_methods:
                                        self.twoD_fit_methods[str(method).split('_')[1]] = []
                            else:  # this is oneD case
                                try:  # if there is a given estimator it will be set or added
                                    if (str(method).split('_')[1] in self.oneD_fit_methods and str(method).split('_')[
                                        2] is not None):
                                        self.oneD_fit_methods[str(method).split('_')[1]].append(
                                            str(method).split('_')[2])
                                    elif str(method).split('_')[2] is not None:
                                        self.oneD_fit_methods[str(method).split('_')[1]] = [str(method).split('_')[2]]
                                except:  # if there is no estimator but only a standard one the estimator is empty
                                    if not str(method).split('_')[1] in self.oneD_fit_methods:
                                        self.oneD_fit_methods[str(method).split('_')[1]] = []
                except:
                    self.logMsg('It was not possible to import element {} into FitLogic.'.format(method),
                                msgType='error')
        self.logMsg('Methods were included to FitLogic, but only if naming is right: check the doxygen documentation' +
                    'if you added a new method and it does not show',
                    msgType='warning')

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
        pass