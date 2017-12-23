# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI module base class.

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
# Test gui (test)

from core.module import ConfigOption
from gui.guibase import GUIBase
from qtpy import QtWidgets


class TestGui(GUIBase):
    """A class to test gui module loading.

        This class does not implement a show() method to test the
        error thrown by GUIBase when this function is not implemented.
    """

    buttonText = ConfigOption('text', 'No Text configured')
    infoOption = ConfigOption('info', 'Info Option', missing='info')
    warningOption = ConfigOption('warning', 'Warning Option', missing='warn')
    errorOption = ConfigOption('error', missing='error')

    def __init__(self, config, **kwargs):
        """Create a TestWindow object.

          @param dict config: configuration dictionary
          @param dict kwargs: further optional arguments
        """
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """This creates all the necessary UI elements.
        """
        self._mw = QtWidgets.QMainWindow()
        self._mw.setGeometry(300,300,500,100)
        self._mw.setWindowTitle('TEST')
        self.cwdget = QtWidgets.QWidget()
        self.button = QtWidgets.QPushButton(self.buttonText)
        self.buttonerror = QtWidgets.QPushButton('Giff Error!')
        self.checkbutton = QtWidgets.QPushButton('Status Error')
        self.checkbutton.setCheckable(True)
        self.button.clicked.connect(self.handleButton)
        self.buttonerror.clicked.connect(self.handleButtonError)
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.button)
        self.layout.addWidget(self.buttonerror)
        self.layout.addWidget(self.checkbutton)
        self.cwdget.setLayout(self.layout)
        self._mw.setCentralWidget(self.cwdget)
        self._mw.show()

    def on_deactivate(self):
        """
        """
        pass

    def handleButton(self):
        """Change style of buttons.
        """
        self.button.setStyleSheet(
            'QPushButton {background-color:'
            ' #A3C1DA; color: red;}')

    def handleButtonError(self):
        """ Produce an exception for testing.
        """
        raise Exception('Сука Блять')

    def getState(self):
        if hasattr(self, 'checkbutton') and self.checkbutton.isChecked():
            raise Exception('Fail.')
        else:
            return super().module_state()
