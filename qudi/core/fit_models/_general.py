# -*- coding: utf-8 -*-

"""
This file contains base and meta class for data fit model classes for qudi based on the lmfit
package. Also contains an estimator decorator for fit models to name estimator methods.

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

from lmfit import Model


class estimator:
    def __init__(self, name):
        self.name = name

    def __call__(self, func):
        # ToDo: Sanity checking for appropriate estimator method. Keep in mind other decorators
        #  (i.e. staticmethod, classmethod etc.)
        #  Do not flag function if it is an invalid estimator.
        func.estimator_name = self.name
        return func


class FitModelMeta(type):
    def __init__(cls, name, bases, attrs):
        estimators = dict()
        for name, method in attrs.items():
            if hasattr(method, 'estimator_name'):
                estimators[method.estimator_name] = name

        @property
        def _estimators(self):
            names = estimators.copy()
            try:
                names.update(super(cls, self)._estimators)
            except AttributeError:
                pass
            return names

        cls._estimators = _estimators


class FitModelBase(Model, metaclass=FitModelMeta):
    """
    """

    def __init__(self, **kwargs):
        kwargs.pop('name', None)
        super().__init__(self._model_function, name=self.__class__.__name__, **kwargs)
        print(self.estimators)

    @property
    def estimators(self):
        return {name: getattr(self, attr) for name, attr in self._estimators.items()}
