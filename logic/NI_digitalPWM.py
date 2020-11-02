import numpy as np
import time

from core.connector import Connector
from core.statusvariable import StatusVar
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore
import PyDAQmx as daq


class NIDigitalPWM(GenericLogic):
    """This logic module controls scans of DC voltage on the fourth analog
    output channel of the NI Card.  It collects countrate as a function of voltage.
    """
    dichannelprefix = StatusVar('dichannelprefix', '/Dev1/Port0')

    def __init__(self, **kwargs):
        """ Create VoltageScanningLogic object with connectors.

          @param dict kwargs: optional parameters
        """
        super().__init__(**kwargs)

        # locking for thread safety
        self.threadlock = Mutex()
        self.stopRequested = False
        self.width=1.5
        self.length=20
        self.rate=10000
        self.factor=self.rate/1000
        self.data = np.uint8(np.zeros(int(self.factor * self.length),))
        self.line=7
        self.datarenew = False
    def on_activate(self):
        self.holding = 0
        self.channelprefix = self.dichannelprefix + '/Line'
        """ Initialisation performed during activation of the module.
        """
        self.taskHandel = False

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """

    def set_rate(self,rate):
        self.rate= rate
        self.factor=self.rate / 1000

    def data_gen(self,width):
        self.width=width
        self.data = np.uint8(np.zeros(int(self.factor * self.length)))
        for i in range(0,int(self.width*self.factor)):
            self.data[i]=1
        self.datarenew= True

    def initialize(self,channel=7):
        self.line = self.channelprefix + str(channel)
        self.taskHandel = daq.TaskHandle()  # adding a block of digital output for AOM to repump
        daq.DAQmxCreateTask('', daq.byref(self.taskHandel))
        daq.DAQmxCreateDOChan(self.taskHandel, self.line, "",
                              daq.DAQmx_Val_ChanForAllLines)
        daq.DAQmxCfgSampClkTiming(self.taskHandel, " ", self.rate, daq.DAQmx_Val_Rising,
                                  daq.DAQmx_Val_ContSamps, int(self.length*self.factor))
        daq.DAQmxWriteDigitalLines(self.taskHandel, int(self.length*self.factor), 0, 10.0, daq.DAQmx_Val_GroupByChannel,
                                   self.data, None, None)

        return True

    def start(self):
        if self.datarenew==True:
            try:
                self.stop()
            except:
                self.log.info('datarenewstop')
                pass
        if self.taskHandel == False:
            self.initialize()
        daq.DAQmxStartTask(self.taskHandel)
        self.log.info('task started')
        self.datarenew = False
        return True

    def stop(self):

        daq.DAQmxStopTask(self.taskHandel)
        daq.DAQmxClearTask(self.taskHandel)
        self.taskHandel= False
        return True

