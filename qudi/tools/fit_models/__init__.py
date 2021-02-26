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

from .sine import *
from .linear import *
from .gaussian import *
from .exp_decay import *
from .lorentzian import *
from ._general import FitModelBase
