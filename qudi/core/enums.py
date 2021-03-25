# -*- coding: utf-8 -*-

"""
This module contains qudi general-purpose Enum types.

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

from enum import Enum


class TriggerEdge(Enum):
    """ Active trigger edge for a digital trigger signal? So edgy!
    """
    RISING = 0
    FALLING = 1
    BOTH = 2
    NONE = 3
    INVALID = 4


class SamplingOutputMode(Enum):
    """ Modes for finite output sampling.

    JUMP_LIST: Free arbitrary sampling defined by a list of values. Values do not need to be
               equidistant or monotonous.
    EQUIDISTANT_SWEEP: Sampling defined by a range of values (begin, end) and a number of samples.
                       Sampling values will be equidistant between begin and end value.
    CONSTANT: Sampling defined by a finite number of constant value samples.
    """
    JUMP_LIST = 0
    EQUIDISTANT_SWEEP = 1
    CONSTANT = 2
    INVALID = 3
