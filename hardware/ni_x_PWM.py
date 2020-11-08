
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

import PyDAQmx as daq

from core.module import Base
from core.configoption import ConfigOption
from interface.ni_pwm_interface import NIPWMInterface
class NIXDiPWM(Base,NIPWMInterface):
    """ A simple hardware module to control one or multiple digital output channel of a nicard as triggers.
        Example config for copy - paste:
        NIXDiPWM:
        module.Class: 'ni_x_PWM.NIXDiPWM'
        trigger_output_channel:
            -'/Dev1/Port0/Line7'
        default_clock_frequency: 10000
        """
    _channel_list = ConfigOption('trigger_output_channel', list(), missing='warn')
    freq = ConfigOption('default_clock_frequency', 10000)
    v=0
    active_channel=-1
    line=[]
    data_array=[]
    value=0

    def on_activate(self):
        """ Activate module.
        """
        self.holding = 0
        self.taskHandel = False
        self._channel_list=self._channel_list
        self.active_channel=self.active_channel
        self.data_array=np.zeros(int(20*10**-3*self.freq))
    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        try:
            self.stop()
        except:
            pass

    def output(self,value=0,channel=-1,frequency=-1):
        if frequency ==-1:
            frequency = self.freq
        else:
            self.freq= frequency
        self.value=value
        if value<0 or value>1:
            self.log.exception('please input a value that is in [0,1]')
            return False
        else:
            PW=(1+value)*10**-3
            length=20*10**-3*frequency
            unit=1/frequency
            data=np.concatenate([(np.zeros(int(PW/unit))+1),np.zeros(int(length)-int(PW/unit))])
        if np.float16(value%(unit*10**3))!=0:
            self.log.warn('current frequency not high enough for given resolution, '
                          'current resolution: '+str(unit*10**3*90)+'degree.')
        digits=int(str(unit/10**5).split('e-')[1])-5
        pos_eff=round(int(value/(unit*10**3))*unit*10**3*90,digits)
        self.data_array=data
        self.active_channel=channel
        if channel==-1:
            self.line=self._channel_list
        elif type(channel)== list:
            for c in channel:
                if c not in self._channel_list:
                    self.log.exception('invalid channel name, please refer to channel_list')
                    return False
        else:
            self.log.exception('invalid channel value, channel can be a name list or -1')
            return False
        if self.taskHandel==False:
            self.taskHandel = daq.TaskHandle()  # adding a block of digital output for AOM to repump
        else:
            pass
        if self.holding == 1:
            daq.DAQmxStopTask(self.taskHandel)
            daq.DAQmxClearTask(self.taskHandel)
        else:
            pass
        daq.DAQmxCreateTask('testPWM', daq.byref(self.taskHandel))
        if type(self.line) == list:
            linelist=''
            for l in self.line:
                linelist+=l
                linelist+=','
        else:
            linelist=self.line
        daq.DAQmxCreateDOChan(self.taskHandel, linelist, "",
                              daq.DAQmx_Val_ChanForAllLines)
        daq.DAQmxCfgSampClkTiming(self.taskHandel, " ", frequency, daq.DAQmx_Val_Rising,
                                  daq.DAQmx_Val_ContSamps, int(length))
        daq.DAQmxWriteDigitalLines(self.taskHandel, int(length), 1, 10.0, daq.DAQmx_Val_GroupByChannel,
                                   np.uint8(data), None, None)

        self.holding=1
        self.log.info('holding')
        self.log.info('holding at position ' + str(pos_eff) + 'degree')
        return True

    def simple_0(self,channel=-1,freq=-1):

        self.output(0,channel, freq)

        return True

    def simple_45(self,channel=-1,freq=-1):

        self.output(0.5,channel, freq)

        return True

    def simple_90(self,channel=-1,freq=-1):

        self.output(1, channel, freq)

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
            return False
        return True

    def get_channel_list(self):
        return self._channel_list