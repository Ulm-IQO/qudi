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

import numpy as np
from lmfit import Model, CompositeModel


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

    @property
    def estimators(self):
        return {name: getattr(self, attr) for name, attr in self._estimators.items()}


# class FitCompositeModelBase(CompositeModel, FitModelBase):
#     """
#     """
#
#     def __init__(self, **kwargs):
#         kwargs.pop('name', None)
#         super().__init__(self._model_function, name=self.__class__.__name__, **kwargs)
#
#     @property
#     def estimators(self):
#         return {name: getattr(self, attr) for name, attr in self._estimators.items()}


def search_single_peak(data, peak_type=None):
    """ ToDo: Document
    Assuming equally spaced data points. Data must be smoothed and offset corrected beforehand.
    """
    amplitude = max(data)
    position = np.argmax(data)
    if peak_type == 'gauss':
        approx_width = abs(np.trapz(data) / (np.sqrt(2*np.pi) * amplitude))
    else:
        approx_width = abs(np.trapz(data) / (np.pi * amplitude))

    # Find threshold that approximately corresponds to the peak width estimated.
    # Search in steps of 10% multiples of amplitude.
    start_index, stop_index = 0, len(data) - 1
    width_diff = np.inf
    for threshold in [ii * amplitude/10 for ii in reversed(range(1, 11))]:
        args = np.argwhere(data >= threshold)[:, 0]
        # Stop here if no arguments are found
        if len(args) == 0:
            continue
        consecutive_args = np.split(args, np.where(np.ediff1d(args) != 1)[0]+1)
        max_streak_length = max(len(arr) for arr in consecutive_args if position in arr)
        for args in consecutive_args:
            if len(args) == max_streak_length:
                break
        diff = abs(approx_width - args.size)
        if diff < width_diff:
            width_diff = diff
            start_index, stop_index = args[0], args[-1]

    # Take middle of determined range as peak position index
    position = (stop_index - start_index) // 2 + start_index
    return position, (start_index, stop_index)


def search_double_peak(data):
    pass
