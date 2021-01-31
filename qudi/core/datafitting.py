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
from PySide2 import QtCore, QtWidgets
from qudi.core.util.mutex import Mutex
from qudi.core.util.units import create_formatted_output
from qudi.core import qudi_slot
from qudi.core import fit_models as __models


def __is_fit_model(cls):
    if inspect.isclass(cls) and issubclass(cls, __models.FitModelBase):
        return True
    return False


_fit_models = {name: cls for name, cls in inspect.getmembers(__models, __is_fit_model)}


class FitConfiguration(QtCore.QObject):
    """
    """
    sigConfigurationChanged = QtCore.Signal(object)

    def __init__(self, name, model, estimator=None, parameters=None, parameter_units=None, **kargs):
        assert isinstance(name, str), 'FitConfiguration name must be str type.'
        assert name, 'FitConfiguration name must be non-empty string.'
        assert model in _fit_models, f'Invalid fit model name encountered: "{model}".'
        super().__init__(**kargs)

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
            self.sigConfigurationChanged.emit(self)

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
            self.sigConfigurationChanged.emit(self)

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
            self.sigConfigurationChanged.emit(self)

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


class FitConfigurationsModel(QtCore.QAbstractListModel):
    """
    """
    sigFitConfigurationsChanged = QtCore.Signal(tuple)

    def __init__(self, *args, configurations=None, **kwargs):
        assert all(isinstance(c, FitConfiguration) for c in configurations) or (
                    configurations is None)
        super().__init__(*args, **kwargs)
        self._fit_configurations = list() if configurations is None else list(configurations)
        for config in self._fit_configurations:
            config.sigConfigurationChanged.connect(
                self._configuration_data_changed, QtCore.Qt.QueuedConnection
            )

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
    def configuration_names(self):
        return tuple(fc.name for fc in self._fit_configurations)

    @property
    def configurations(self):
        return self._fit_configurations.copy()

    @qudi_slot(str, str)
    def add_configuration(self, name, model):
        assert name not in self.configuration_names, f'Fit config "{name}" already defined.'
        config = FitConfiguration(name, model, parent=self)
        new_row = len(self._fit_configurations)
        self.beginInsertRows(self.createIndex(new_row, 0), new_row, new_row)
        self._fit_configurations.append(config)
        config.sigConfigurationChanged.connect(
            self._configuration_data_changed, QtCore.Qt.QueuedConnection
        )
        self.endInsertRows()
        self.sigFitConfigurationsChanged.emit(self.configuration_names)

    @qudi_slot(str)
    def remove_configuration(self, name):
        try:
            row_index = self.configuration_names.index(name)
        except ValueError:
            return
        self.beginRemoveRows(self.createIndex(row_index, 0), row_index, row_index)
        config = self._fit_configurations.pop(row_index)
        config.sigConfigurationChanged.disconnect()
        config.setParent(None)
        self.endRemoveRows()
        self.sigFitConfigurationsChanged.emit(self.configuration_names)

    def get_configuration_by_name(self, name):
        try:
            row_index = self.configuration_names.index(name)
        except ValueError:
            raise ValueError(f'No fit configuration found with name "{name}".')
        return self._fit_configurations[row_index]

    def flags(self, index):
        if index.isValid():
            return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._fit_configurations)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            if (orientation == QtCore.Qt.Horizontal) and (section == 0):
                return 'Fit Configurations'
            elif orientation == QtCore.Qt.Vertical:
                try:
                    return self.configuration_names[section]
                except IndexError:
                    pass
        return None

    def data(self, index=QtCore.QModelIndex(), role=QtCore.Qt.DisplayRole):
        if (role == QtCore.Qt.DisplayRole) and (index.isValid()):
            row = index.row()
            # ToDo: Return the entire object to an item delegate instead of the name
            return self._fit_configurations[row].name
        return None

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        return False

    @qudi_slot(object)
    def _configuration_data_changed(self, config):
        try:
            row = self._fit_configurations.index(config)
        except ValueError:
            return
        self.dataChanged.emit(self.createIndex(row, 0), self.createIndex(row, 0))


class FitContainer(QtCore.QObject):
    """
    """
    sigFitConfigurationsChanged = QtCore.Signal(tuple)  # config_names
    sigLastFitResultChanged = QtCore.Signal(object, object)  # (fit_config, lmfit.ModelResult)

    def __init__(self, *args, config_model, **kwargs):
        assert isinstance(config_model, FitConfigurationsModel)
        super().__init__(*args, **kwargs)
        self._access_lock = Mutex()
        self._configuration_model = config_model
        self._last_fit_result = None
        self._last_fit_config = None

        self._configuration_model.sigFitConfigurationsChanged.connect(
            self.sigFitConfigurationsChanged
        )

    @property
    def fit_configurations(self):
        return self._configuration_model.configurations

    @property
    def fit_configuration_names(self):
        return self._configuration_model.configuration_names

    @property
    def last_fit(self):
        with self._access_lock:
            return self._last_fit_config, self._last_fit_result

    @qudi_slot(str, object, object)
    def fit_data(self, fit_config, x, data):
        with self._access_lock:
            config = self._configuration_model.get_configuration_by_name(fit_config)
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
