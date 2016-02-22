# -*- coding: utf-8 -*-

from core.base import Base
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from collections import OrderedDict
from interface.simple_data_interface import SimpleDataInterface
import numpy as np
import time

class SimpleDummy(Base, SimpleDataInterface):
    """
    """
    _modclass = 'simple'
    _modtype = 'hardware'

    # connectors
    _out = {'simple': 'Simple'}

    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, configuration=config, callbacks = c_dict)

    def activation(self, e):
        pass

    def deactivation(self, e):
        pass

    def getData(self):
        time.sleep(0.1)
        return [int(np.random.poisson(5)), int(np.random.poisson(6)), int(np.random.poisson(10))]

    def getChannels(self):
        time.sleep(0.1)
        return 3
