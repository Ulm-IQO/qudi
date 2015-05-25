# -*- coding: utf-8 -*-
# Test gui (test)

from gui.GUIBase import GUIBase
from pyqtgraph.Qt import QtCore, QtGui


class TestGui(GUIBase):
    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.initUI}
        super().__init__(
                    manager,
                    name,
                    config,
                    c_dict)
        
        # get text from config
        self.buttonText = 'No Text configured'
        if 'text' in config:
            self.buttonText = config['text']

    def initUI(self, e=None):
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

    def handleButton(self):
        self.button.setStyleSheet('QPushButton {background-color:'
                                ' #A3C1DA; color: red;}')

    def handleButtonError(self):
        raise Exception('Сука Блять')
