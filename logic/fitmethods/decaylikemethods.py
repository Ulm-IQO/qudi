# -*- coding: utf-8 -*-

"""
This file contains the QuDi fitting logic functions needed for gaussian-like-methods.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2016 Jochen Scheuer jochen.scheuer@uni-ulm.de
"""

import numpy as np
from lmfit.models import Model
from lmfit import Parameters
