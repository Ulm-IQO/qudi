# -*- coding: utf-8 -*-

from core.Base import Base
from .LaserSwitchInterface import LaserSwitchInterface

class LaserSwitchInterface(Base, LaserSwitchInterface):
    """ Methods to control slow laser switching devices.
    """
    _modclass = 'laserswitchinterface'
    _modtype = 'hardware'

    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, configuation=config, callbacks = c_dict)

        self.connector['out']['counter'] = OrderedDict()
        self.connector['out']['counter']['class'] = 'LaserSwitchInterface'

        self.switchState = [False, False, False]
        self.switchCalibration = dict()
        self.switchCalibration['On'] = [0.9, 0.8, 0.88]
        self.switchCalibration['Off'] = [0.15, 0.3, 0.2]

    def activation(self):
        pass

    def deactivation(self):
        pass

    def getNumberOfSwitches(self):
        """ Gives the number of switches connected to this hardware.
        """
        return len(switchState)

    def getSwitchState(self, switchNumber):
        """
        """
        return self.switchState[switchNumber]

    def getCalibration(self, switchNumber, state):
        """
        """
        bstate = state == 'On'
        return self.switchCalibration[bstate][switchNumber]

    def setCalibration(self, switchNumber, state, value):
        """
        """
        bstate = state == 'On'
        self.switchCalibration[bstate][switchNumber] = value

    def switchOn(self, switchNumber):
        """
        """
        self.switchState[switchNumber] = True
        return self.switchState[switchNumber]
    
    def switchOff(self, switchNumber):
        """
        """
        self.switchState[switchNumber] = False
        return self.switchState[switchNumber]

