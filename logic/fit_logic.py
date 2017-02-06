# -*- coding: utf-8 -*-
"""
This file contains the Qudi FitLogic class, which provides all
fitting methods imported from the files in logic/fitmethods.

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

import importlib
from os import listdir
from os.path import isfile, join

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex


class FitLogic(GenericLogic):

    """
    UNSTABLE:Jochen Scheuer

    Documentation to add a new fit model/estimator/funciton can be found in
    documentation/how_to_use_fitting.md or in the online documentation at
    http://qosvn.physik.uni-ulm.de/qudi-docs/fit_logic.html

    This is the fitting class where fit functions are defined and methods are
    implemented to process the data.

    For clarity reasons the fit function are imported from different files
    seperated by function type, e.g. gaussianlikemethods, sinemethods, generalmethods
    """
    _modclass = 'fitlogic'
    _modtype = 'logic'
    # declare connectors
    _out = {'fitlogic': 'FitLogic'}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # locking for thread safety
        self.lock = Mutex()

        filenames = []
        # for path in directories:
        path = join(self.get_main_dir(), 'logic', 'fitmethods')
        for f in listdir(path):
            if isfile(join(path, f)):
                if f[-3:] == '.py':
                    filenames.append(f[:-3])

        # A dictionary contianing all fit methods and their estimators.
        self.fit_list = dict()
        self.fit_list['1d'] = dict()
        self.fit_list['2d'] = dict()
        self.fit_list['3d'] = dict()

        # Go through the fitmethods files and import all methods.
        for files in filenames:

            mod = importlib.import_module('logic.fitmethods.{0}'.format(files))

            for method in dir(mod):
                try:
                    if callable(getattr(mod, method)):
                        # import methods in Fitlogic
                        setattr(FitLogic, method, getattr(mod, method))
                        # add method to dictionary and define what
                        # estimators they have

                        fit_name = str(method).split('_')[1]
                        
                        if 'twoD' in fit_name:
                            dimension = '2d'
                        elif 'threeD' in fit_name:
                            dimension = '3d'
                        else:
                            dimension = '1d'

                        # check if it is a make_<fit name>_model method
                        if (str(method).startswith('make_') and str(method).endswith('_model')):

                            # Add fit_name entry to self.fit_list if it is not already there
                            if fit_name not in self.fit_list[dimension]:
                                self.fit_list[dimension][fit_name] = dict()
                                
                            # Give this fit_name its fit method in the sub-dictionary
                            self.fit_list[dimension][fit_name]['make_model'] = getattr(self, method)

                        # check if it is a make_<fit name>_fit method
                        if (str(method).startswith('make_') and str(method).endswith('_fit')):

                            # Add fit_name entry to self.fit_list if it is not already there
                            if fit_name not in self.fit_list[dimension]:
                                self.fit_list[dimension][fit_name] = dict()
                                
                            # Give this fit_name its fit method in the sub-dictionary
                            self.fit_list[dimension][fit_name]['make_fit'] = getattr(self, method)

                        # if there is an estimator add it to the dictionary
                        if 'estimate' in str(method):

                            
                            # Add fit_name entry to self.fit_list if it is not already there.
                            if fit_name not in self.fit_list[dimension]:
                                self.fit_list[dimension][fit_name] = dict()

                            # If this is a custom estimator
                            try:
                                estimator_name = str(method).split('_')[2]

                                # Give this fit_name another estimator in the sub-dictionary
                                self.fit_list[dimension][fit_name][estimator_name] = getattr(self, method)

                            # Otherwise this is a generic estimator for the fit_name
                            except:

                                self.fit_list[dimension][fit_name]['generic'] = method

                except:
                    self.log.error('It was not possible to import element {} '
                                   'into FitLogic.'.format(method)
                                   )
        self.log.warning('Methods were included to FitLogic, but only if '
                         'naming is right: check the doxygen documentation '
                         'if you added a new method and it does not show.'
                         )

    def on_activate(self, e):
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

    def on_deactivate(self, e):
        pass
