# -*- coding: utf-8 -*-

"""
This file contains a wrapper to display the SpinBox in scientific way

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

import pyqtgraph


class ScienDSpinBox(pyqtgraph.SpinBox):
    """ Wrapper Class from PyQtGraph to display a QDoubleSpinBox in Scientific way. """

    def __init__(self, *args, **kwargs):
        pyqtgraph.SpinBox.__init__(self, *args, int=False, suffix='s', siPrefix=True,  **kwargs)

class ScienSpinBox(pyqtgraph.SpinBox):
    """ Wrapper Class from PyQtGraph to display a QSpinBox in Scientific way. """

    def __init__(self, *args, **kwargs):
        pyqtgraph.SpinBox.__init__(self, *args, int=True, **kwargs)
