# -*- coding: utf-8 -*-
"""
IPython notebook kernel executable file for QuDi.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2016 Jan M. Binder jan.binder@uni-ulm.de
"""

import os
import sys
import rpyc
import time
import signal
import atexit

from parentpoller import ParentPollerUnix, ParentPollerWindows

class QuDi(object):

    def __init__(self):
        self.host = 'localhost'
        self.port = 12345
        self.conn_config = {'allow_all_attrs': True}
        self.parent_handle = int(os.environ.get('JPY_PARENT_PID') or 0)
        self.interrupt = int(os.environ.get('JPY_INTERRUPT_EVENT') or 0)
        self.kernelthread = None

    def connect(self, **kwargs):
        self.connection = rpyc.connect(self.host, self.port, config=self.conn_config)

    def getModule(self, name):
        return self.connection.root.getModule(name)

    def startKernel(self, connfile):
        m = self.getModule('kernellogic')
        self.kernelthread = m.startKernel(connfile)
        print('Kernel up!')

    def stopKernel(self):
        print('Shutting down: ', self.kernelthread)
        sys.stdout.flush()
        m = self.getModule('kernellogic')
        if self.kernelthread is not None:
            m.stopKernel(self.kernelthread)
            print('Down!')
            sys.stdout.flush()

    def initSignal(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    def initPoller(self):
        if sys.platform == 'win32':
            if self.interrupt or self.parent_handle:
                self.poller = ParentPollerWindows(self.interrupt, self.parent_handle)
        elif self.parent_handle:
            self.poller = ParentPollerUnix()


if __name__ == '__main__':
    q = QuDi()
    q.initSignal()
    q.initPoller()
    q.connect()
    q.startKernel(sys.argv[1])
    atexit.register(q.stopKernel)
    print('Sleeping.')
    q.poller.run()
    print('Quitting.')
    sys.stdout.flush()
    #q.stopKernel()
    #q.connection.close()
    
