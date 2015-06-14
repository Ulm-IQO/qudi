# -*- coding: utf-8 -*-

import visa
from core.Base import Base
from .LaserSwitchInterface import LaserSwitchInterface

class HBridge(Base, LaserSwitchInterface):
    """ Methods to control slow laser switching devices.
    """
    _modclass = 'laserswitchinterface'
    _modtype = 'hardware'

    def __init__(self, manager, name, config, **kwargs):
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, configuation=config, callbacks = c_dict)

        self.connector['out']['counter'] = OrderedDict()
        self.connector['out']['counter']['class'] = 'LaserSwitchInterface'

    def activation(self):
        config = self.getConfiguration()
        if not 'interface' in config:
            raise KeyError('{0} definitely needs an "interface" configuration value.'.format(self.__class__.__name__))
        self.inst = visa.SerialInstrument(
                config['interface'],
                baud_rate = 9600,
                term_chars='\r\n',
                timeout=10,
                send_end=True
        )

    def deactivation(self):
        self.inst.close()

    def getNumberOfSwitches(self):
        """ Gives the number of switches connected to this hardware.
        """
        return 4

    def getSwitchState(self, switchNumber):
        """
        """
        pos = self.inst.ask('STATUS')
        ret = list()
        for i in pos.split():
            ret.append(int(i))
        return ret[switchNumber]

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
        coilnr = int(switchNumber) + 1
        if int(coilnr) > 0 and int(coilnr) < 5:
            with self.lock:
                try:
                    answer = self.inst.ask('P{0}=1'.format(coilnr))
                    if answer != 'P{0}=1'.format(coilnr):
                        return False
                except:
                    return False
                return True
        else:
            self.logMsg('You are trying to use non-existing output no {0}'.format(coilnr), msgType='error')
    
    def switchOff(self, switchNumber):
        """
        """
        coilnr = int(switchNumber) + 1
        if int(coilnr) > 0 and int(coilnr) < 5:
            with self.lock:
                try:
                    answer = self.inst.ask('P{0}=0'.format(coilnr))
                    if answer != 'P{0}=0'.format(coilnr):
                        return False
                except:
                    return False
                return True
        else:
            self.logMsg('You are trying to use non-existing output no {0}'.format(coilnr), msgType='error')


    def _get_positions(self):
        
    # ========================================================================
    # Below here we have all functions that do something with the hardware and
    # do not do any setup or funny stuff.
    # They should all be decorated with @queued so they can only be called
    # inside the execution queue.
    # Do not call other queued functions here or the queue will lock up!!!!!
    # ========================================================================
    @queued
    def getPositions(self):

