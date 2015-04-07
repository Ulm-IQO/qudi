# Manager gui (test)

from core.Base import Base
from pyqtgraph.Qt import QtCore, QtGui


class ManagerGui(Base):
    def __init__(self, manager, name, config, **kwargs):
        self._mw = QtGui.QMainWindow()
        Base.__init__(self, manager, name, configuration=config)
        self.initUI()

    def initUI(self):
        self._mw.setGeometry(300,300,300,300)
        self._mw.setWindowTitle('TEST')
        self._mw.show()
