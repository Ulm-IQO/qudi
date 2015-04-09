# -*- coding: utf-8 -*-
# Test gui (test)

from core.Base import Base
from pyqtgraph.Qt import QtCore, QtGui


class CounterGui(Base):
    def __init__(self, manager, name, config, **kwargs):
        self._mw = QtGui.QMainWindow()
        Base.__init__(self, manager, name, configuration=config)
        
        self.initUI()

    def initUI(self):
        self._mw.setGeometry(300,300,500,100)
        self._mw.setWindowTitle('Slow Photon counter')
        self.cwdget = QtGui.QWidget()
        self.button = QtGui.QPushButton('Click it!')
        self.button.clicked.connect(self.handleButton)
        self.layout = QtGui.QVBoxLayout()
        self.layout.addWidget(self.button)
        self.cwdget.setLayout(self.layout)
        self._mw.setCentralWidget(self.cwdget)
        self._mw.show()

    def handleButton(self):
        self.button.setStyleSheet('QPushButton {background-color:'
                                ' #A3C1DA; color: red;}')
