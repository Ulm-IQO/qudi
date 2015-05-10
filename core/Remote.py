# -*- coding: utf-8 -*-

from pyqtgraph.Qt import QtCore
import queue
import Pyro4
import socket


class RemoteObjectManager(QtCore.QObject):
    def __init__(self, threadManager, logger):
        super().__init__()
        self.hostname = socket.gethostname()
        self.nameserver = Pyro4.locateNS()
        self.tm = threadManager
        self.logger = logger
        self.logger.logMsg('Nameserver is: {0}'.format(self.nameserver._pyroUri), msgType='status')

    def refresNameserver(self):
        self.nameserver = Pyro4.locateNS()

    def createServer(self, name, obj):
        thread = self.tm.newThread('pyro-{0}'.format(name))
        server = PyroModuleServer(self.hostname, obj)
        server.moveToThread(thread)
        thread.started.connect(server.run)
        thread.start()
        self.nameserver.register('{0}-{1}'.format(self.hostname, name), server.uri)
        self.logger.logMsg('Module {0} registered as {1} and as {2}-{0} at nameserver {3}'.format(name, server.uri, self.hostname, self.nameserver._pyroUri), msgType='status')

    def getRemoteModule(self, name):
        uri = self.nameserver.lookup(name)
        return Pyro4.Proxy(uri)


class PyroModuleServer(QtCore.QObject):
    def __init__(self, host, module):
        super().__init__()
        Pyro4.config.COMMTIMEOUT = 0.5
        self.daemon = Pyro4.Daemon(host=host)
        self.uri = self.daemon.register(module)

    def run(self):
        self.daemon.requestLoop(loopCondition=self.checkEvents)

    
    def checkEvents(self):
        QtCore.QCoreApplication.processEvents()
        return QtCore.QThread.currentThread().isRunning()
