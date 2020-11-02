# -*- coding: utf-8 -*-
"""
This file contains a Qudi logic module for controlling scans of the
fourth analog output channel.  It was originally written for
scanning laser frequency, but it can be used to control any parameter
in the experiment that is voltage controlled.  The hardware
range is typically -10 to +10 V.

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


import numpy as np
import time

from core.connector import Connector
from core.statusvariable import StatusVar
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore
import PyDAQmx as daq


class NIDigitalTriger(GenericLogic):

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

    def on_activate(self):
        self.holding=0
        self.channelprefix=self.dichannelprefix + '/Line'
        """ Initialisation performed during activation of the module.
        """
        self.taskHandel=False

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """

    def output(self,value=1,channel=5,duration=-1,hold='True'):
        if value!=0 and value!=1:
            self.log.exception('output value can only be 0 or 1')
        if duration!=-1 and hold=='True':
            self.log.exception('please specify intention: hold or with finite duration?')
            return False
        if hold == 'False' and duration == -1:
            self.log.exception('please specify duration length in s')
            return False
        self.line=self.channelprefix+str(channel)
        if self.taskHandel==False:
            self.taskHandel = daq.TaskHandle()  # adding a block of digital output for AOM to repump
        else:
            pass
        if self.holding == 1:
            daq.DAQmxStopTask(self.taskHandel)
            daq.DAQmxClearTask(self.taskHandel)
        else:
            pass
        daq.DAQmxCreateTask('testDO', daq.byref(self.taskHandel))
        daq.DAQmxCreateDOChan(self.taskHandel, self.line, "",
                              daq.DAQmx_Val_ChanForAllLines)
        daq.DAQmxWriteDigitalLines(self.taskHandel, 1, 1, 10.0, daq.DAQmx_Val_GroupByChannel,
                                   np.array([value], dtype=np.uint8), None, None)

        if hold == 'True':
            self.holding=1
            self.log.info('holding')
        else:
            self.holding=0
            self.log.info('di output on: '+ self.line + ' duration: '+ str(duration)+'s')
            time.sleep(duration)
            daq.DAQmxWriteDigitalLines(self.taskHandel, 1, 1, 10.0, daq.DAQmx_Val_GroupByChannel,
                                   np.array([value], dtype=np.uint8), None, None)
            daq.DAQmxStopTask(self.taskHandel)
            daq.DAQmxClearTask(self.taskHandel)
        return True

    def simple_on(self,channel=5):

        self.output(1,channel, -1, 'True')

        return True

    def simple_off(self,channel=5):

        self.output(0,channel, -1, 'True')

        return True

    def simple_flip(self):

        self.simple_on()
        self.simple_off()

        return True

    def stop(self):
        try:
            daq.DAQmxStopTask(self.taskHandel)
            daq.DAQmxClearTask(self.taskHandel)
            self.holding=0
            self.log.info('full stop')
            self.taskHandel=False
        except:
            self.log.exception('cannot stop, maybe never started?')
        return True

