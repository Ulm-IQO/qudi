# -*- coding: utf-8 -*-

from pyqtgraph.Qt import QtCore
import queue
import Pyro4
import socket


class RemoteObjectManager(QtCore.QObject):
    def __init__(self, threadManager):
        super().__init__()
        self.hostname = socket.gethostname()
        self.nameserver = Pyro4.locateNS()
        self.tm = threadManager

    def refresNameserver(self):
        self.nameserver = Pyro4.locateNS()

    def createServer(self, name, obj):
        thread = self.tm.newThread('pyro-{0}'.format(name))
        server = PyroModuleServer(obj)
        server.moveToThread(thread)
        thread.started.connect(server.run)
        thread.start()
        self.nameserver.register('{0}-{1}'.format(self.hostname, name), server.uri)
        


class PyroModuleServer(QtCore.QObject):
    def __init__(self, module):
        super().__init__()
        Pyro4.config.COMMTIMEOUT = 0.5
        self.daemon = Pyro4.Daemon()
        self.uri = self.daemon.register(module)

    def run(self):
        self.daemon.requestLoop(loopCondition=self.checkEvents)

    
    def checkEvents(self):
        QtCore.QCoreApplication.processEvents()
        return QtCore.QThread.currentThread().isRunning()
