# -*- coding: utf-8 -*-
"""
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

Distributed under the MIT license, see documentation/MITLicense.md.
PyQtGraph - Scientific Graphics and GUI Library for Python
www.pyqtgraph.org
Copyright:
  2012  University of North Carolina at Chapel Hill
        Luke Campagnola    <luke.campagnola@gmail.com>
"""

import re
import logging
import numpy as np

# use setuptools parse_version if available and use distutils LooseVersion as
# fallback
try:
    from pkg_resources import parse_version
except ImportError:
    from distutils.version import LooseVersion as parse_version

has_pyqtgraph = False
try:
    import pyqtgraph
    has_pyqtgraph = True
except ImportError:
    pass

_logger = logging.getLogger(__name__)

__all__ = ('csv_2_list', 'has_pyqtgraph', 'in_range', 'is_complex', 'is_float', 'is_integer',
           'is_number', 'natural_sort')


def natural_sort(iterable):
    """
    Sort an iterable of str in an intuitive, natural way (human/natural sort).
    Use this to sort alphanumeric strings containing integers.

    @param str[] iterable: Iterable with str items to sort
    @return list: sorted list of strings
    """
    def conv(s):
        return int(s) if s.isdigit() else s
    try:
        return sorted(iterable, key=lambda key: [conv(i) for i in re.split(r'(\d+)', key)])
    except:
        return sorted(iterable)


def is_number(test_value):
    """ Check whether passed value is a number

    @return: bool, True if the passed value is a number, otherwise false.
    """
    return is_integer(test_value) or is_float(test_value) or is_complex(test_value)


def is_integer(test_value):
    """ Check all available integer representations.

    @return: bool, True if the passed value is a integer, otherwise false.
    """

    return type(test_value) in [np.int, np.int8, np.int16, np.int32, np.int64,
                                np.uint, np.uint8, np.uint16, np.uint32,
                                np.uint64]


def is_float(test_value):
    """ Check all available float representations.

    @return: bool, True if the passed value is a float, otherwise false.
    """
    return type(test_value) in [np.float, np.float16, np.float32, np.float64]


def is_complex(test_value):
    """ Check all available complex representations.

    @return: bool, True if the passed value is a complex value, otherwise false.
    """

    return np.iscomplexobj(test_value)


def in_range(value, lower_limit, upper_limit):
    """ Check if a value is in a given range an return closest possible value in range.
    Also check the range.

    @param value: value to be checked
    @param lower_limit: lowest allowed value
    @param upper_limit: highest allowed value
    @return (bool, type(value)): in_range indicator, value closest to value in range
    """
    if upper_limit < lower_limit:
        lower_limit, upper_limit = upper_limit, lower_limit

    if value > upper_limit:
        return False, upper_limit
    if value < lower_limit:
        return False, lower_limit
    return True, value


def csv_2_list(csv_string, str_2_val=None):
    """
    Parse a list literal (with or without square brackets) given as string containing
    comma-separated int or float values to a python list.
    (blanks before and after commas are handled)

    @param str csv_string: scalar number literals as strings separated by a single comma and any number
                       of blanks. (brackets are ignored)
                       Example: '[1e-6,2.5e6, 42]' or '1e-6, 2e-6,   42'
    @param function str_2_val: optional, function to use for casting substrings into single values.
    @return list: list of float values. If optional str_2_val is given, type is invoked by this
                  function.
    """
    if not isinstance(csv_string, str):
        raise TypeError('string_2_list accepts only str type input.')

    csv_string = csv_string.replace('[', '').replace(']', '')  # Remove square brackets
    csv_string = csv_string.replace('(', '').replace(')', '')  # Remove round brackets
    csv_string = csv_string.replace('{', '').replace('}', '')  # Remove curly brackets
    csv_string = csv_string.strip().strip(',')  # Remove trailing/leading blanks and commas

    # Cast each str value to float if no explicit cast function is given by parameter str_2_val.
    if str_2_val is None:
        csv_list = [float(val_str) for val_str in csv_string.split(',')]
    else:
        csv_list = [str_2_val(val_str.strip()) for val_str in csv_string.split(',')]
    return csv_list
