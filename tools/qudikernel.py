# -*- coding: utf-8 -*-
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
        m = self.getModule('rkernel')
        self.kernelthread = m.startKernel(connfile)
        print('Kernel up!')

    def stopKernel(self):
        print('Shutting down: ', self.kernelthread)
        sys.stdout.flush()
        m = self.getModule('rkernel')
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
    
