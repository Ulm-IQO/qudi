# -*- coding: utf-8 -*-
"""
This file contains a qudi GUI module template

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

from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.core.configoption import ConfigOption
from PySide2 import QtCore, QtWidgets, QtGui
from .testgui import TemplateGui


class MyMainWindow(QtWidgets.QMainWindow):
    """Create a Qt main window.
    Can either be customized entirely here or loaded from a .ui file.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.button_up = QtWidgets.QPushButton('count up')
        self.button_down = QtWidgets.QPushButton('count down')
        self.spinbox = QtWidgets.QSpinBox()
        self.spinbox.setRange(-2**31, 2**31-1)
        self.spinbox.setValue(0)
        self.spinbox.setReadOnly(True)
        self.label = QtWidgets.QLabel()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.button_up)
        layout.addWidget(self.spinbox)
        layout.addWidget(self.button_down)
        layout.addWidget(self.label)
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)


class TestGui2(TemplateGui):
    """Description of this qudi module goes here.
    """

    my_first_logic_connector = Connector(interface='TemplateLogic')
    my_third_logic_connector = Connector(interface='TestLogic2')

    _cfg_option = ConfigOption(name='cfg_option', default='derpherp', missing='warn')

    sigStuffDone2 = QtCore.Signal()

    _my_variable = StatusVar(name='my_variable', default=111111111111111)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mw = None
