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
import inspect
from os import listdir
from os.path import isfile, join
from collections import OrderedDict

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
        self.fit_list = OrderedDict()
        self.fit_list['1d'] = OrderedDict()
        self.fit_list['2d'] = OrderedDict()
        self.fit_list['3d'] = OrderedDict()

        # Go through the fitmethods files and import all methods.
        # Also determine which methods need to be added to the fit_list dictionary
        estimators_for_dict = list()
        models_for_dict = list()
        fits_for_dict = list()

        for files in filenames:

            mod = importlib.import_module('logic.fitmethods.{0}'.format(files))

            for method in dir(mod):
                ref = getattr(mod, method)
                if callable(ref) and (inspect.ismethod(ref) or inspect.isfunction(ref)):
                    method_str = str(method)
                    try:
                        # import methods in Fitlogic
                        setattr(FitLogic, method, ref)
                        # append method to a list of methods to include in the fit_list dictionary
                        if method_str.startswith('make_') and method_str.endswith('_fit'):
                            fits_for_dict.append(method_str.split('_', 1)[1].rsplit('_', 1)[0])
                        elif method_str.startswith('make_') and method_str.endswith('_model'):
                            models_for_dict.append(method_str.split('_', 1)[1].rsplit('_', 1)[0])
                        elif method_str.startswith('estimate_'):
                            estimators_for_dict.append(method_str.split('_', 1)[1])
                    except:
                        self.log.error('Method "{0}" could not be imported to FitLogic.'
                                       ''.format(str(method)))

        fits_for_dict.sort()
        models_for_dict.sort()
        estimators_for_dict.sort()
        # Now attach the fit, model and estimator methods to the proper dictionary fields
        for fit_name in fits_for_dict:
            fit_method = 'make_' + fit_name + '_fit'
            model_method = 'make_' + fit_name + '_model'

            # Determine fit dimension
            if 'twoD' in fit_name:
                dimension = '2d'
            elif 'threeD' in fit_name:
                dimension = '3d'
            else:
                dimension = '1d'

            # Attach make_*_fit method to fit_list
            if fit_name not in self.fit_list[dimension]:
                self.fit_list[dimension][fit_name] = OrderedDict()
            self.fit_list[dimension][fit_name]['make_fit'] = getattr(self, fit_method)

            # Attach make_*_model method to fit_list
            if fit_name in models_for_dict:
                self.fit_list[dimension][fit_name]['make_model'] = getattr(self, model_method)
            else:
                self.log.error('No make_*_model method for fit "{0}" found in FitLogic.'
                               ''.format(fit_name))

            # Attach all estimate_* methods to corresponding fit method in fit_list
            found_generic_estimator = False
            for estimator_name in estimators_for_dict:
                estimator_method = 'estimate_' + estimator_name
                if fit_name == estimator_name:
                    self.fit_list[dimension][fit_name]['generic'] = getattr(self, estimator_method)
                    found_generic_estimator = True
                elif estimator_name.startswith(fit_name + '_'):
                    custom_name = estimator_name.split('_', 1)[1]
                    self.fit_list[dimension][fit_name][custom_name] = getattr(self, estimator_method)
            if not found_generic_estimator:
                self.log.error('No generic estimator method for fit "{0}" found in FitLogic.'
                               ''.format(fit_name))

        self.log.info('Methods were included to FitLogic, but only if naming is right: check the'
                         ' doxygen documentation if you added a new method and it does not show.')

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
