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

#import pyqtgraph
from tools.pyqtgraphmod.SpinBox import SpinBox


class ScienDSpinBox(SpinBox):
    """ Wrapper Class from PyQtGraph to display a QDoubleSpinBox in Scientific 
        way. 

    This class can be directly used in Qt Designer by promoting the 
    QDoubleSpinBox to ScienDSpinBox. State the path to this file (in python 
    style, i.e. dots are separating the directories) as the header file and use
    the name of the present class.
    """

    def __init__(self, *args, **kwargs):
        SpinBox.__init__(
                self,
                *args,
                int=False,
                #suffix='s',
                siPrefix=True,
                dec=True,
                step=0.1,
                minStep=0.0001,
                bounds=(0.0, 99.99),    # set the bounds to be convenient to the default values of the Qt Designer.
                **kwargs
        )

class ScienSpinBox(SpinBox):
    """ Wrapper Class from PyQtGraph to display a QSpinBox in Scientific way. 
    
    This class can be directly used in Qt Designer by promoting the 
    QSpinBox to ScienSpinBox. State the path to this file (in python style, 
    i.e. dots are separating the directories) as the header file and use the 
    name of the present class.
    """

    def __init__(self, *args, **kwargs):
        SpinBox.__init__(self,
                         *args,
                         int=True,
                         bounds=(0, 99), # set the bounds to be convenient to the default values of the Qt Designer.
                         **kwargs)
