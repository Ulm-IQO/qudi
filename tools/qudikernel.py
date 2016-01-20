# -*- coding: utf-8 -*-
import rpyc
import time
import sys

class QuDi(object):

    def __init__(self):
        self.host = 'localhost'
        self.port = 12345
        self.conn_config = {'allow_all_attrs': True}

    def connect(self, **kwargs):
        self.connection = rpyc.connect(self.host, self.port, config=self.conn_config)

    def getModule(self, name):
        return self.connection.root.getModule(name)

    def startKernel(self, connfile):
        m = self.getModule('rkernel')
        m.startKernel(connfile)

if __name__ == '__main__':
    q = QuDi()
    q.connect()
    q.startKernel(sys.argv[1])
    
    while True:
        time.sleep(1)
