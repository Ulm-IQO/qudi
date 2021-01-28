# -*- coding: utf-8 -*-

"""
ToDo: Document

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

import inspect
import lmfit
from PySide2 import QtCore
from qudi.core.util.mutex import Mutex
from qudi.core.util.units import create_formatted_output
from qudi.core import qudi_slot
from qudi.core import fit_models as __models


def __is_fit_model(cls):
    if inspect.isclass(cls) and issubclass(cls, __models.FitModelBase):
        return True
    return False


_fit_models = {name: cls for name, cls in inspect.getmembers(__models, __is_fit_model)}


class FitConfiguration:
    """
    """

    def __init__(self, name, model, estimator=None, parameters=None, parameter_units=None):
        assert isinstance(name, str), 'FitConfiguration name must be str type.'
        assert name, 'FitConfiguration name must be non-empty string.'
        assert model in _fit_models, f'Invalid fit model name encountered: "{model}".'

        self._access_lock = Mutex()
        self._name = name
        self._model = model
        self._estimator = None
        self._parameters = None
        self._parameters_units = None
        self.estimator = estimator
        self.parameters = parameters
        self.parameter_units = parameter_units

    @property
    def name(self):
        return self._name

    @property
    def model(self):
        return self._model

    @property
    def estimator(self):
        return self._estimator

    @estimator.setter
    def estimator(self, value):
        if value is not None:
            assert value in _fit_models[
                self._model].estimators, f'Invalid fit model estimator encountered: "{value}"'
        with self._access_lock:
            self._estimator = value

    @property
    def parameters(self):
        with self._access_lock:
            return self._parameters.copy() if self._parameters is not None else None

    @parameters.setter
    def parameters(self, value):
        if value is not None:
            model_params = _fit_models[self._model]().make_params()
            invalid = set(value).difference(model_params)
            assert not invalid, f'Invalid model parameters encountered: {invalid}'
            assert all(isinstance(p, lmfit.Parameter) for p in
                       value.values()), 'Fit parameters must be of type <lmfit.Parameter>.'
        with self._access_lock:
            self._parameters = value.copy() if value is not None else None

    @property
    def parameter_units(self):
        with self._access_lock:
            return self._parameter_units.copy() if self._parameter_units is not None else None

    @parameter_units.setter
    def parameter_units(self, value):
        if value is not None:
            model_params = _fit_models[self._model]().make_params()
            invalid = set(value).difference(model_params)
            assert not invalid, f'Invalid model parameters encountered: {invalid}'
            assert all(isinstance(u, str) for u in value.values()), \
                'Fit parameter units must be of str type.'
        with self._access_lock:
            self._parameters_units = value.copy() if value is not None else None

    def formatted_result(self, fit_result):
        assert self._model == fit_result.name.split('(', 1)[1].rsplit(')', 1)[0], \
            'lmfit.ModelResult does not match model of FitConfiguration'
        units = self.parameter_units
        if units is None:
            units = dict()
        parameters_to_format = dict()
        for name, param in fit_result.params.items():
            if not param.vary:
                continue
            parameters_to_format[name] = {'value': param.value,
                                          'error': param.stderr,
                                          'unit': units.get(name, '')}
        return create_formatted_output(parameters_to_format)


class FitContainer(QtCore.QObject):
    """
    """
    sigFitConfigurationsChanged = QtCore.Signal(dict)  # {config_name: fit_config}
    sigLastFitResultChanged = QtCore.Signal(object, object)  # (fit_config, lmfit.ModelResult)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._access_lock = Mutex()
        self._configured_fits = dict()
        self._last_fit_result = None
        self._last_fit_config = None

    @property
    def model_names(self):
        return tuple(_fit_models)

    @property
    def model_estimators(self):
        return {name: tuple(model.estimators) for name, model in _fit_models.items()}

    @property
    def model_default_parameters(self):
        return {name: model().make_params() for name, model in _fit_models.items()}

    @property
    def fit_configurations(self):
        with self._access_lock:
            return self._configured_fits.copy()

    @property
    def fit_configuration_names(self):
        with self._access_lock:
            return tuple(self._configured_fits)

    @property
    def last_fit(self):
        with self._access_lock:
            return self._last_fit_config_name, self._last_fit_result

    @qudi_slot(str, str)
    def add_fit_configuration(self, fit_name, model):
        with self._access_lock:
            assert fit_name not in self._configured_fits, \
                f'Fit configuration "{fit_name}" already present.'
            self._configured_fits[fit_name] = FitConfiguration(fit_name, model)
            self.sigFitConfigurationsChanged.emit(self.fit_configurations)

    @qudi_slot(str)
    def remove_fit_configuration(self, fit_name):
        with self._access_lock:
            removed = self._configured_fits.pop(fit_name, None)
            if removed is not None:
                self.sigFitConfigurationsChanged.emit(self.fit_configurations)

    def get_fit_configuration(self, fit_name):
        with self._access_lock:
            return self._configured_fits.get(fit_name, None)

    @qudi_slot(str, object, object)
    def fit_data(self, fit_config, x, data):
        with self._access_lock:
            config = self._configured_fits.get(fit_config, None)
            assert config is not None, f'No fit configuration found with name "{fit_config}".'
            model = _fit_models[config.model]
            estimator = config.estimator
            add_parameters = config.parameters
            if estimator is None:
                parameters = model.make_params()
            else:
                parameters = model.estimators[estimator](data, x)
            if add_parameters is not None:
                parameters.update(add_parameters)
            self._last_fit_result = model.fit(data, parameters, x=x)
            self._last_fit_config = config
            self.sigLastFitResultChanged.emit(self._last_fit_config, self._last_fit_result)
