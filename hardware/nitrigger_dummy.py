"""
This file contains the Qudi Hardware module NIXdiTrigger class.

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
import re

#import PyDAQmx as daq

from core.module import Base
from core.configoption import ConfigOption
from interface.trigger_interface import TriggerInterface
class NIXDiTriggerDummy(Base,TriggerInterface):
    """ A simple hardware module to control one or multiple digital output channel of a nicard as triggers.
        Example config for copy - paste:
        NIXDiTrigger:
        module.Class: 'ni_x_di_trigger.NIXDiTrigger'
        trigger_output_channel:
            -'/Dev1/Port0/Line5'
            -'/Dev1/Port0/Line6'
        default_clock_frequency: 100
        """
    _channel_list = ConfigOption('trigger_output_channel', list(), missing='warn')
    freq = ConfigOption('default_clock_frequency', 100)
    v=0
    active_channel=-1
    line=[]

    def on_activate(self):
        """ Activate module.
        """
        self.holding = 0
        self.DOtaskHandel = False
        self._channel_list=self._channel_list
        self.active_channel=self.active_channel
    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.holding = 0
        try:
            self.stop()
        except:
            pass

    def output(self,value=[1.0],channel=-1,duration=-1,hold='True'):
        self.active_channel=channel
        self.v=v=np.array([value])
        if len(np.where(v!=0)[0]) + len(np.where(v!=1)[0]) > len(v):
            self.log.exception('output value can only be 0 or 1')
        if duration!=-1 and hold=='True':
            self.log.exception('please specify intention: hold or with finite duration?')
            return False
        if hold == 'False' and duration == -1:
            self.log.exception('please specify duration length in s')
            return False
        if channel==-1:
            self.line=self._channel_list
        else:
            if type(channel)== list:
                for c in channel:
                    if c not in self._channel_list:
                        self.log.exception('invalid channel name, please refer to channel_list')
                        return False
            else:
                if type(channel)== str:
                    if channel not in self._channel_list:
                        self.log.exception('invalid channel name, please refer to channel_list')
                    else:
                        self.line=channel
                else:
                    self.log.exception('invalid channel value, channel can be a name list or -1')
                    return False
        if len(v)==1 and len(self.line)>1:
            v=np.zeros(len(self.line))+v
        if len(v)>1 and type(self.line)== list and len(v)!=len(self.line):
            self.log.exception('input value array size does not match output channel number, please double check.')
            return False
        if len(v)==1 and type(self.line)==str:
            pass
        if self.DOtaskHandel==False:
            self.DOtaskHandel == True
            #pass #self.DOtaskHandel = daq.TaskHandle()
        else:
            pass
        if self.holding == 1:
            pass
            #daq.DAQmxStopTask(self.DOtaskHandel)
            #daq.DAQmxClearTask(self.DOtaskHandel)
        else:
            pass
        #daq.DAQmxCreateTask('testDO', daq.byref(self.DOtaskHandel))
        if type(self.line) == list:
            linelist=''
            for l in self.line:
                linelist+=l
                linelist+=','
        else:
            linelist=self.line
        #daq.DAQmxCreateDOChan(self.DOtaskHandel, linelist, "",
        #                      daq.DAQmx_Val_ChanForAllLines)
        #daq.DAQmxWriteDigitalLines(self.DOtaskHandel, 1, 1, 10.0, daq.DAQmx_Val_GroupByChannel,
        #                           np.array(v, dtype=np.uint8), None, None)

        if hold == 'True':
            self.holding=1
            self.log.info('holding')
        else:
            self.holding=0
            self.log.info('di output on: '+ self.line + ' duration: '+ str(duration)+'s')
            time.sleep(duration)
        #    daq.DAQmxWriteDigitalLines(self.DOtaskHandel, 1, 1, 10.0, daq.DAQmx_Val_GroupByChannel,
        #                           np.array(0, dtype=np.uint8), None, None)
        #    daq.DAQmxStopTask(self.DOtaskHandel)
        #    daq.DAQmxClearTask(self.DOtaskHandel)
            self.DOtaskHandel=False
        return True

    def simple_on(self,channel=-1):

        self.output(1,channel, -1, 'True')

        return True

    def simple_off(self,channel=-1):

        self.output(0,channel, -1, 'True')

        return True

    def simple_flip(self,channel=-1):

        self.simple_on(channel)
        self.simple_off(channel)

        return True

    def stop(self):
        try:
            #daq.DAQmxStopTask(self.DOtaskHandel)
            #daq.DAQmxClearTask(self.DOtaskHandel)
            #self.DOtaskHandel=False
            self.holding=0
            self.log.info('full stop')
            self.DOtaskHandel=False
        except:
            #daq.DAQmxClearTask(self.DOtaskHandel)
            self.log.exception('cannot stop, maybe never started?')
        return True

    def get_channel_list(self):
        return self._channel_list