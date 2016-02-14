# -*- coding: utf-8 -*-

"""
This file contains the QuDi Logic module base class.

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

Copyright (C) 2016 Alexander Stark alexander.stark@uni-ulm.de
"""


"""
An interfuse file is indented to fuse/combine a logic with a hardware, which
was not indented to be used with the logic. The interfuse file extend the
ability of a hardware file by converting the logic calls (from a different
interface) to the interface commands, which suits the hardware.
"""

from logic.generic_logic import GenericLogic
from interface.magnet_interface import MagnetInterface
from interface.motor_interface import MotorInterface

class MagnetMotorInterfuse(GenericLogic, MagnetInterface, MotorInterface):

    _modclass = 'magnetmotorinterfuse'
    _modtype = 'interfuse'
    ## declare connectors
    _in = {'odmrcounter': 'ODMRCounterInterface',
           'fitlogic': 'FitLogic',
           'microwave1': 'mwsourceinterface',
           'savelogic': 'SaveLogic'
            }
    _out = {'odmrlogic': 'ODMRLogic'}



    