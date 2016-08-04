# -*- coding: utf-8 -*-
"""
This file contains the QuDi GUI module base class.

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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""
# Test gui (test)

from gui.guibase import GUIBase
from pyqtgraph.Qt import QtCore, QtGui

class TestGui(GUIBase):
    """A class to test gui module loading.

        This class does not implement a show() method to test the
        error thrown by GUIBase when this function is not implemented.
    """
    def __init__(self, config, **kwargs):
        """Create a TestWindow object.

          @param dict config: configuration dictionary
          @param dict kwargs: further optional arguments
        """
        super().__init__(config=config, **kwargs)

        # get text from config
        self.buttonText = 'No Text configured'
        if 'text' in config:
            self.buttonText = config['text']

    def on_activate(self, e=None):
        """This creates all the necessary UI elements.
          @param object e: Fysom state change
        """
        self._mw = QtGui.QMainWindow()
        self._mw.setGeometry(300,300,500,100)
        self._mw.setWindowTitle('TEST')
        self.cwdget = QtGui.QWidget()
        self.button = QtGui.QPushButton(self.buttonText)
        self.buttonerror = QtGui.QPushButton('Giff Error!')
        self.button.clicked.connect(self.handleButton)
        self.buttonerror.clicked.connect(self.handleButtonError)
        self.layout = QtGui.QVBoxLayout()
        self.layout.addWidget(self.button)
        self.layout.addWidget(self.buttonerror)
        self.cwdget.setLayout(self.layout)
        self._mw.setCentralWidget(self.cwdget)
        self._mw.show()

    def on_deactivate(self, e):
        """
          @param object e: Fysom state change
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
