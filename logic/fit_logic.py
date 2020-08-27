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
import lmfit
from qtpy import QtCore
import numpy as np
import os
import sys
from collections import OrderedDict
from distutils.version import LooseVersion

from logic.generic_logic import GenericLogic
from core.util.modules import get_main_dir
from core.util.mutex import Mutex
from core.config import load, save
from core.configoption import ConfigOption


class FitLogic(GenericLogic):
    """
    Documentation to add a new fit model/estimator/function can be found in
    documentation/how_to_use_fitting.md or in the online documentation at
    http://qosvn.physik.uni-ulm.de/qudi-docs/fit_logic.html

    This is the fitting class where fit functions are defined and methods are
    implemented to process the data.

    For clarity reasons the fit function are imported from different files
    seperated by function type, e.g. gaussianlikemethods, sinemethods, generalmethods
    """

    # Optional additional paths to import from
    _additional_methods_import_path = ConfigOption(name='additional_fit_methods_path',
                                                   default=None,
                                                   missing='nothing')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # locking for thread safety
        self.lock = Mutex()

        filenames = []
        # for path in directories:
        path_list = [os.path.join(get_main_dir(), 'logic', 'fitmethods')]
        # adding additional path, to be defined in the config

        if self._additional_methods_import_path:
            if isinstance(self._additional_methods_import_path, str):
                self._additional_methods_import_path = [self._additional_methods_import_path]
                self.log.info('Adding fit methods path: {}'.format(self._additional_methods_import_path))

            if isinstance(self._additional_methods_import_path, (list, tuple, set)):
                self.log.info('Adding fit methods path list: {}'.format(self._additional_methods_import_path))
                for method_import_path in self._additional_methods_import_path:
                    if not os.path.exists(method_import_path):
                        self.log.error('Specified path "{0}" for import of additional fit methods '
                                       'does not exist.'.format(method_import_path))
                    else:
                        path_list.append(method_import_path)
            else:
                self.log.error('ConfigOption additional_predefined_methods_path needs to either be a string or '
                               'a list of strings.')

        for path in path_list:
            for f in os.listdir(path):
                if os.path.isfile(os.path.join(path, f)) and f.endswith('.py'):
                    filenames.append(f[:-3])
                    if path not in sys.path:
                        sys.path.append(path)

        # A dictionary containing all fit methods and their estimators.
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
            mod = importlib.import_module('{0}'.format(files))
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
            found_estimator = False
            for estimator_name in estimators_for_dict:
                estimator_method = 'estimate_' + estimator_name
                if fit_name == estimator_name:
                    self.fit_list[dimension][fit_name]['generic'] = getattr(self, estimator_method)
                    found_estimator = True
                elif estimator_name.startswith(fit_name + '_'):
                    custom_name = estimator_name.split('_', 1)[1]
                    self.fit_list[dimension][fit_name][custom_name] = getattr(self, estimator_method)
                    found_estimator = True
            if not found_estimator:
                self.log.error('No estimator method for fit "{0}" found in FitLogic.'
                               ''.format(fit_name))

        self.log.info('Methods were included to FitLogic, but only if naming is right: check the'
                      ' doxygen documentation if you added a new method and it does not show.')

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # FIXME: load all the fits here, otherwise reloading this module is really questionable
        fitversion = LooseVersion(lmfit.__version__)
        if fitversion < LooseVersion('0.9.2'):
            raise Exception('lmfit needs to be at least version 0.9.2!')

    def on_deactivate(self):
        """ """
        pass

    def validate_load_fits(self, fits):
        """ Take fit names and estimators from a dict and check if they are valid.
            @param fits dict: dictionary containing fit and estimator description

            @return dict: checked dictionary with references to fit, model and estimator

        The stored dictionary must have the following format.
        There can be a parameter settings string included at the deepest level.
        Example:
        '1d':
            'Two Lorentzian dips':
                'fit_function': 'doublelorentzoffset'
                'estimator': 'dip'

        The returned dictionary has the following format (example):
        '1d':
            'Two Lorentzian dips':
                'fit_name': 'doublelorentzoffset'
                'est_name': 'dip'
                'make_fit': function reference to fit function
                'make_model': function reference to model function
                'estimator': function reference to estimator function
                'parameters': lmfit.parameter.Parameters object
        """
        user_fits = OrderedDict()
        for dim, dfits in fits.items():
            if dim not in ('1d', '2d', '3d'):
                continue
            user_fits[dim] = OrderedDict()
            for name, fit in dfits.items():
                try:
                    fname = fit['fit_function']
                    new_fit = {'fit_name': fname, 'est_name': fit['estimator'],
                               'make_fit': self.fit_list[dim][fname]['make_fit'],
                               'make_model': self.fit_list[dim][fname]['make_model'],
                               'estimator': self.fit_list[dim][fname][fit['estimator']]}
                    try:
                        par = lmfit.parameter.Parameters()
                        par.loads(fit['parameters'])
                    except:
                        model, par = self.fit_list[dim][fname]['make_model']()
                    new_fit['parameters'] = par
                    user_fits[dim][name] = new_fit
                except KeyError:
                    self.log.exception('Failed to validate fit {0}'.format(name))
                    continue
        return user_fits

    def prepare_save_fits(self, fits):
        """ Convert fit dictionary into a storable form.
            @param fits dict: fit dictionary with function references and parameter objects

            @return dict: storable fits description dictionary

        For the format of this dictionary, ess validate_load_fits.
        """
        save_fits = OrderedDict()
        for dim, dfits in fits.items():
            if dim not in ('1d', '2d', '3d'):
                continue
            save_fits[dim] = OrderedDict()
            for name, fit in dfits.items():
                try:
                    new_fit = {'fit_function': fit['fit_name'], 'estimator': fit['est_name'],
                               'parameters': fit['parameters'].dumps()}
                    save_fits[dim][name] = new_fit
                except KeyError:
                    self.log.exception('Error while preparing fit {0} for saving.'.format(name))
                    continue
        return save_fits

    def load_fits(self, filename):
        """ Load collection of fits from YAML file.
            @param filename str: path of file containing fits in YAML format

            @return dict: validated fit dictionary with function references and parameter objects
        """
        if not filename:
            return {'1d': dict(), '2d': dict(), '3d': dict()}
        fits = load(filename)
        return self.validate_load_fits(fits)

    def save_fits(self, filename, fits):
        """ Save a collection of configured fits to YAML file.
            @param fits dict: dictionay with fits, function references and parameter objects

            @return dict: storable dictionary with fit description
        """
        stripped_fits = self.prepare_save_fits(fits)
        save(filename, stripped_fits)

    def make_fit_container(self, container_name, dimension):
        """ Creare a fit container object.
            @param container_name str: user-fiendly name for configurable fit
            @param dimension str: dimension of fit input data ('1d', '2d' od '3d')

            @return FitContainer: fit container object

        This is a convenience function so you do not have to mess with an extra import in modules
        using FitLogic.
        """
      
        return FitContainer(self, container_name, dimension)


class FitContainer(QtCore.QObject):
    """ A class for managing a single flexible fit setting in a logic module.
    """
    sigFitUpdated = QtCore.Signal()
    sigCurrentFit = QtCore.Signal(str)
    sigNewFitResult = QtCore.Signal(str, lmfit.model.ModelResult)
    sigNewFitParameters = QtCore.Signal(str, lmfit.parameter.Parameters)

    def __init__(self, fit_logic, name, dimension):
        """ Create a fit container.

            @param fit_logic FitLogic: reference to a FitLogic instance
            @param name str: user-friendly name for this container
            @param dimension str: dimension for fit input in this container, '1d', '2d' or '3d'
        """
        super().__init__()

        self.fit_logic = fit_logic
        self.name = name
        if dimension == '1d':
            self.dim = 1
        elif dimension == '2d':
            self.dim = 2
        elif dimension == '3d':
            self.dim = 3
        else:
            raise Exception('Invalid dimension {0}'.format(dimension))
        self.dimension = dimension
        self.fit_list = OrderedDict()
        # variables for fitting
        self.fit_granularity_fact = 10
        self.current_fit = 'No Fit'
        self.current_fit_param = lmfit.parameter.Parameters()
        self.current_fit_result = None
        self.use_settings = None
        self.units = ['independent variable {0}'.format(i+1) for i in range(self.dim)]
        self.units.append('dependent variable')

    def set_units(self, units):
        """ Set units for this fit.
            @param units list(str): list of units (for x axes and y axis)

            Number of units must be = dimensions + 1
        """
        if len(units) == self.dim + 1:
            self.units = units

    def load_from_dict(self, fit_dict):
        """ Take a list of fits from a storable dictionary, load to self.fit_list and check.
            @param fit_dict dict: fit dictionary with function references etc

        """
        try:
            self.fit_list = self.fit_logic.validate_load_fits(fit_dict)[self.dimension]
        except KeyError:
            self.fit_list = OrderedDict()

    def save_to_dict(self):
        """ Convert self.fit_list to a storable dictionary.

            @return dict: storable configured fits dictionary
        """
        prep = self.fit_logic.prepare_save_fits({self.dimension: self.fit_list})
        return prep

    def clear_result(self):
        """ Reset fit result and fit parameters from result for this container.
        """
        self.current_fit_param = lmfit.parameter.Parameters()
        self.current_fit_result = None

    @QtCore.Slot(dict)
    def set_fit_functions(self, fit_functions):
        """ Set the configured fit functions for this container.
            @param fit_functions dict: configured fit functions dictionary
        """
        self.fit_list = fit_functions
        self.set_current_fit(self.current_fit)

    @QtCore.Slot(str)
    def set_current_fit(self, current_fit):
        """ Check and set the current fit for this container by name.
            @param current_fit str: name of configured fit to be used as current fit

        If the name given is not in the list of fits, the current fit will be 'No Fit'.
        This is a reserved name that will do nothing and should not display a fit line if set.
        """
        if current_fit not in self.fit_list and current_fit != 'No Fit':
            self.fit_logic.log.warning('{0} not in {1} fit list!'.format(current_fit, self.name))
            self.current_fit = 'No Fit'
        else:
            self.current_fit = current_fit
            if current_fit != 'No Fit':
                use_settings = self.fit_list[self.current_fit]['use_settings']
                self.use_settings = lmfit.parameter.Parameters()
                # Update the use parameter dictionary
                for para in use_settings:
                    if use_settings[para]:
                        self.use_settings[para]=self.fit_list[self.current_fit]['parameters'][para]
            else:
                self.use_settings=None
        self.clear_result()
        self.sigCurrentFit.emit(self.current_fit)
        return self.current_fit, self.use_settings

    def do_fit(self, x_data, y_data):
        """Performs the chosen fit on the measured data.
        @param array x_data: optional, 1D np.array or 1D list with the x values.
                             If None is passed then the module x values are
                             taken.
        @param array y_data: optional, 1D np.array or 1D list with the y values.
                             If None is passed then the module y values are
                             taken. If passed, then it should have the same size
                             as x_data.

        @return: tuple (fit_x, fit_y, str_dict, fit_result)
            np.array fit_x: 1D array containing the x values of the fit
            np.array fit_y: 1D array containing the y values of the fit
            OrderedDict str_dict: a dictionary with the relevant fit
                                    parameters, i.e. the result of the fit. Each
                                    entry is again a dict with three entries,
                                        {'value': ... , 'error': ...., 'unit': '...'}
                                    The values and the errors are always saved
                                    in SI units!

            lmfit.model.ModelResult fit_result:
                            the result object of lmfit. If additional
                            information is needed from the fit, then they can be
                            obtained from this object. If no fit is performed
                            then result is set to None.
        """
        self.clear_result()

        fit_x = np.linspace(
            start=x_data[0],
            stop=x_data[-1],
            num=int(len(x_data) * self.fit_granularity_fact))

        # set the keyword arguments, which will be passed to the fit.
        kwargs = {
            'x_axis': x_data,
            'data': y_data,
            'units': self.units,
            'add_params': self.use_settings}

        result = None

        if self.current_fit in self.fit_list:
            result = self.fit_list[self.current_fit]['make_fit'](
                estimator=self.fit_list[self.current_fit]['estimator'],
                **kwargs)

        elif self.current_fit == 'No Fit':
            fit_y = np.zeros(fit_x.shape)

        else:
            self.fit_logic.log.warning(
                'The Fit Function "{0}" is not implemented to be used in the ODMR Logic. '
                'Correct that! Fit Call will be skipped and Fit Function will be set to '
                '"No Fit".'.format(self.current_fit))

            self.current_fit = 'No Fit'

        if self.current_fit != 'No Fit':
            # after the fit was performed, retrieve the fitting function and
            # evaluate the fitted parameters according to the function:
            model, params = self.fit_list[self.current_fit]['make_model']()
            fit_y = model.eval(x=fit_x, params=result.params)

        if result is not None:
            self.current_fit_param = result.params
            self.current_fit_result = result
            self.sigNewFitParameters.emit(self.current_fit, result.params)
            self.sigNewFitResult.emit(self.current_fit, result)

        self.sigFitUpdated.emit()

        return fit_x, fit_y, result
