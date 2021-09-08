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
"""

__all__ = ['csv_2_list', 'in_range', 'is_complex', 'is_complex_type', 'is_float', 'is_float_type',
           'is_integer', 'is_integer_type', 'is_number', 'is_number_type', 'is_string',
           'is_string_type', 'iter_modules_recursive', 'natural_sort', 'str_to_number']

import re
import os
import pkgutil
import numpy as np
from typing import Union, Optional, Iterable, List, Any, Type, Tuple, Callable

_RealNumber = Union[int, float]


def iter_modules_recursive(paths: Union[str, Iterable[str]],
                           prefix: Optional[str] = '') -> List[pkgutil.ModuleInfo]:
    """ Has the same signature as pkgutil.iter_modules() but extends the functionality by walking
    through the entire directory tree and concatenating the return values of pkgutil.iter_modules()
    for each directory.

    Additional modifications include:
    - Directories starting with "_" or "." are ignored (also including their sub-directories)
    - Python modules starting with a double-underscore ("__") are excluded in the result

    @param iterable paths: Iterable of root directories to start the search for modules
    @param str prefix: optional, prefix to prepend to all module names.
    """
    if isinstance(paths, str):
        paths = [paths]
    module_infos = list()
    for search_top in paths:
        for root, dirs, files in os.walk(search_top):
            rel_path = os.path.relpath(root, search_top)
            if rel_path and rel_path != '.' and rel_path[0] in '._':
                # Prevent os.walk to descent further down this tree branch
                dirs.clear()
                # Ignore this directory
                continue
            # Resolve current module prefix
            if not rel_path or rel_path == '.':
                curr_prefix = prefix
            else:
                curr_prefix = prefix + '.'.join(rel_path.split(os.sep)) + '.'
            # find modules and packages in current dir
            tmp = pkgutil.iter_modules([root], prefix=curr_prefix)
            module_infos.extend(
                [mod_inf for mod_inf in tmp if not mod_inf.name.rsplit('.', 1)[-1].startswith('__')]
            )
    return module_infos


def natural_sort(iterable: Iterable[Any]) -> List[Any]:
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


def is_number(test_value: Any) -> bool:
    """ Check whether passed value is a number """
    return is_integer(test_value) or is_float(test_value) or is_complex(test_value)


def is_number_type(test_obj: Type) -> bool:
    """ Check whether passed object is a number type """
    return is_integer_type(test_obj) or is_float_type(test_obj) or is_complex_type(test_obj)


def is_integer(test_value: Any) -> bool:
    """ Check all available integer representations """
    return isinstance(test_value, (int, np.integer))


def is_integer_type(test_obj: Type) -> bool:
    """ Check if passed object is an integer type """
    return issubclass(test_obj, (int, np.integer))


def is_float(test_value: Any) -> bool:
    """ Check all available float representations """
    return isinstance(test_value, (float, np.floating))


def is_float_type(test_obj: Type) -> bool:
    """ Check if passed object is a float type """
    return issubclass(test_obj, (float, np.floating))


def is_complex(test_value: Any) -> bool:
    """ Check all available complex representations """
    return isinstance(test_value, (complex, np.complexfloating))


def is_complex_type(test_obj: Type) -> bool:
    """ Check if passed object is a complex type """
    return issubclass(test_obj, (complex, np.complexfloating))


def is_string(test_value: Any) -> bool:
    """ Check all available string representations """
    return isinstance(test_value, (str, np.str_, np.string_))


def is_string_type(test_obj: Type) -> bool:
    """ Check if passed object is a string type """
    return issubclass(test_obj, (str, np.str_, np.string_))


def in_range(value: _RealNumber, lower_limit: _RealNumber,
             upper_limit: _RealNumber) -> Tuple[bool, _RealNumber]:
    """ Check if a value is in a given range an return closest possible value in range.
    Also check the range.
    Return value is clipped to range.
    """
    if upper_limit < lower_limit:
        lower_limit, upper_limit = upper_limit, lower_limit

    if value > upper_limit:
        return False, upper_limit
    if value < lower_limit:
        return False, lower_limit
    return True, value


def csv_2_list(csv_string: str, str_2_val: Optional[Callable[[str], Any]] = None) -> List[Any]:
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
        csv_list = [str_to_number(val_str) for val_str in csv_string.split(',')]
    else:
        csv_list = [str_2_val(val_str.strip()) for val_str in csv_string.split(',')]
    return csv_list


def str_to_number(str_value: str,
                  return_failed: Optional[bool] = False) -> Union[int, float, complex, str]:
    """ Parse a string into either int, float or complex (in that order) """
    try:
        return int(str_value)
    except ValueError:
        try:
            return float(str_value)
        except ValueError:
            try:
                return complex(str_value)
            except ValueError:
                if return_failed:
                    return str_value
                else:
                    raise ValueError(
                        f'Could not convert string to int, float or complex: \'{str_value}\''
                    )
