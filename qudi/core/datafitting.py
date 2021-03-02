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
import numpy as np
from PySide2 import QtCore
from qudi.util.mutex import Mutex
from qudi.util.units import create_formatted_output
from qudi.tools import fit_models as __models
try:
    from tools import fit_models as __ext_models
    if __ext_models == __models:
        __ext_models = None
except ImportError:
    __ext_models = None


def __is_fit_model(cls):
    return inspect.isclass(cls) and issubclass(cls, __models.FitModelBase) and (
                cls is not __models.FitModelBase)


_fit_models = {name: cls for name, cls in inspect.getmembers(__models, __is_fit_model)}
# Import fit models from extension modules
if __ext_models is not None:
    _fit_models.update(
        {name: cls for name, cls in inspect.getmembers(__ext_models, __is_fit_model)}
    )


class FitConfiguration:
    """
    """

    def __init__(self, name, model, estimator=None, custom_parameters=None):
        assert isinstance(name, str), 'FitConfiguration name must be str type.'
        assert name, 'FitConfiguration name must be non-empty string.'
        assert model in _fit_models, f'Invalid fit model name encountered: "{model}".'
        assert name != 'No Fit', '"No Fit" is a reserved name for fit configs. Choose another.'

        self._name = name
        self._model = model
        self._estimator = None
        self._custom_parameters = None
        self.estimator = estimator
        self.custom_parameters = custom_parameters

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
            assert value in self.available_estimators, \
                f'Invalid fit model estimator encountered: "{value}"'
        self._estimator = value

    @property
    def available_estimators(self):
        return tuple(_fit_models[self._model]().estimators)

    @property
    def default_parameters(self):
        params = _fit_models[self._model]().make_params()
        return lmfit.Parameters() if params is None else params

    @property
    def custom_parameters(self):
        return self._custom_parameters.copy() if self._custom_parameters is not None else None

    @custom_parameters.setter
    def custom_parameters(self, value):
        if value is not None:
            default_params = self.default_parameters
            invalid = set(value).difference(default_params)
            assert not invalid, f'Invalid model parameters encountered: {invalid}'
            assert isinstance(value, lmfit.Parameters), \
                'Property custom_parameters must be of type <lmfit.Parameters>.'
        self._custom_parameters = value.copy() if value is not None else None

    def to_dict(self):
        return {
            'name': self._name,
            'model': self._model,
            'estimator': self._estimator,
            'custom_parameters': None if self._custom_parameters is None else self._custom_parameters.dumps()
        }

    @classmethod
    def from_dict(cls, dict_repr):
        assert set(dict_repr) == {'name', 'model', 'estimator', 'custom_parameters'}
        if isinstance(dict_repr['custom_parameters'], str):
            dict_repr['custom_parameters'] = lmfit.Parameters().loads(
                dict_repr['custom_parameters']
            )
        return cls(**dict_repr)


class FitConfigurationsModel(QtCore.QAbstractListModel):
    """
    """

    sigFitConfigurationsChanged = QtCore.Signal(tuple)

    def __init__(self, *args, configurations=None, **kwargs):
        assert (configurations is None) or all(isinstance(c, FitConfiguration) for c in configurations)
        super().__init__(*args, **kwargs)
        self._fit_configurations = list() if configurations is None else list(configurations)

    @property
    def model_names(self):
        return tuple(_fit_models)

    @property
    def model_estimators(self):
        return {name: tuple(model().estimators) for name, model in _fit_models.items()}

    @property
    def model_default_parameters(self):
        return {name: model().make_params() for name, model in _fit_models.items()}

    @property
    def configuration_names(self):
        return tuple(fc.name for fc in self._fit_configurations)

    @property
    def configurations(self):
        return self._fit_configurations.copy()

    @QtCore.Slot(str, str)
    def add_configuration(self, name, model):
        assert name not in self.configuration_names, f'Fit config "{name}" already defined.'
        assert name != 'No Fit', '"No Fit" is a reserved name for fit configs. Choose another.'
        config = FitConfiguration(name, model)
        new_row = len(self._fit_configurations)
        self.beginInsertRows(self.createIndex(new_row, 0), new_row, new_row)
        self._fit_configurations.append(config)
        self.endInsertRows()
        self.sigFitConfigurationsChanged.emit(self.configuration_names)

    @QtCore.Slot(str)
    def remove_configuration(self, name):
        try:
            row_index = self.configuration_names.index(name)
        except ValueError:
            return
        self.beginRemoveRows(self.createIndex(row_index, 0), row_index, row_index)
        self._fit_configurations.pop(row_index)
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
            try:
                return self._fit_configurations[index.row()]
            except IndexError:
                pass
        return None

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if index.isValid():
            config = index.data(QtCore.Qt.DisplayRole)
            if config is None:
                return False
            new_params = value[1]
            params = config.default_parameters
            for name in [p for p in params if p not in new_params]:
                del params[name]
            for name, p in params.items():
                value_tuple = new_params[name]
                p.set(vary=value_tuple[0],
                      value=value_tuple[1],
                      min=value_tuple[2],
                      max=value_tuple[3])
            print('setData:', params)
            config.estimator = None if not value[0] else value[0]
            config.custom_parameters = None if not params else params
            self.dataChanged.emit(self.createIndex(index.row(), 0),
                                  self.createIndex(index.row(), 0))
            return True
        return False

    def dump_configs(self):
        """ Returns all currently held fit configurations as dicts representations containing only
        data types that can be dumped as YAML in qudi app status.

        @return list: List of fit config dict representations.
        """
        return [cfg.to_dict() for cfg in self._fit_configurations]

    def load_configs(self, configs):
        """ Initializes/overwrites all currently held fit configurations by a given iterable of dict
        representations (see also: FitConfigurationsModel.dump_configs).

        Calling this method will reset the list model.

        @param iterable configs: Iterable of FitConfiguration dict representations
        """
        config_objects = [FitConfiguration.from_dict(cfg) for cfg in configs]
        self.beginResetModel()
        self._fit_configurations = config_objects
        self.endResetModel()
        self.sigFitConfigurationsChanged.emit(self.configuration_names)


class FitContainer(QtCore.QObject):
    """
    """
    sigFitConfigurationsChanged = QtCore.Signal(tuple)  # config_names
    sigLastFitResultChanged = QtCore.Signal(str, object)  # (fit_config name, lmfit.ModelResult)

    def __init__(self, *args, config_model, **kwargs):
        assert isinstance(config_model, FitConfigurationsModel)
        super().__init__(*args, **kwargs)
        self._access_lock = Mutex()
        self._configuration_model = config_model
        self._last_fit_result = None
        self._last_fit_config = 'No Fit'

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

    @QtCore.Slot(str, object, object)
    def fit_data(self, fit_config, x, data):
        with self._access_lock:
            if fit_config:
                # Handle "No Fit" case
                if fit_config == 'No Fit':
                    self._last_fit_result = None
                    self._last_fit_config = 'No Fit'
                else:
                    config = self._configuration_model.get_configuration_by_name(fit_config)
                    model = _fit_models[config.model]()
                    estimator = config.estimator
                    add_parameters = config.custom_parameters
                    if estimator is None:
                        parameters = model.make_params()
                    else:
                        parameters = model.estimators[estimator](data, x)
                    if add_parameters is not None:
                        for name, param in add_parameters.items():
                            parameters[name] = param
                    result = model.fit(data, parameters, x=x)
                    # Mutate lmfit.ModelResult object to include high-resolution result curve
                    high_res_x = np.linspace(x[0], x[-1], len(x) * 10)
                    result.high_res_best_fit = (high_res_x,
                                                model.eval(**result.best_values, x=high_res_x))
                    self._last_fit_result = result
                    self._last_fit_config = fit_config
                self.sigLastFitResultChanged.emit(self._last_fit_config, self._last_fit_result)
                return self._last_fit_config, self._last_fit_result
            return '', None

    @staticmethod
    def formatted_result(fit_result, parameters_units=None):
        if fit_result is None:
            return ''
        if parameters_units is None:
            parameters_units = dict()
        parameters_to_format = dict()
        for name, param in fit_result.params.items():
            if not param.vary:
                continue
            parameters_to_format[name] = {'value': param.value,
                                          'error': param.stderr,
                                          'unit': parameters_units.get(name, '')}
        return create_formatted_output(parameters_to_format)
