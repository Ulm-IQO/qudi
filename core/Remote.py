# -*- coding: utf-8 -*-
"""
This file contains the QuDi remote object manager class.

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

Copyright (C) 2015 Jan M. Binder jan.binder@uni-ulm.de
"""


from pyqtgraph.Qt import QtCore
import rpyc
from rpyc.utils.server import ThreadedServer
import socket
from urllib.parse import urlparse


class RemoteObjectManager(QtCore.QObject):
    """ This shares modules with other computers and is resonsible
        for obtaining modules shared by other computer.
    """
    def __init__(self, threadManager, logger):
        """ Handle sharing and getting shared modules.
        """
        super().__init__()
        self.hostname = socket.gethostname()
        self.tm = threadManager
        self.logger = logger
        #self.logger.logMsg('Nameserver is: {0}'.format(self.nameserver._pyroUri), msgType='status')
        self.remoteModules = list()
        self.sharedModules = dict()

    def makeRemoteService(self):
        """ A function that returns a class containing a module list hat can be manipulated from the host.
        """
        class RemoteModuleService(rpyc.Service):
            modules = self.sharedModules
            def on_connect(self):
                # code that runs when a connection is created
                # (to init the serivce, if needed)
                print('Client connected!')

            def on_disconnect(self):
                # code that runs when the connection has already closed
                # (to finalize the service, if needed)
                print('Client disconnected!')

            def exposed_getModule(self, name):
                if name in self.modules:
                    return self.modules[name]
                else:
                    return None

        return RemoteModuleService

    def refresNameserver(self):
        #self.nameserver = Pyro4.locateNS()
        pass

    def createServer(self, port):
        thread = self.tm.newThread('rpyc-server')
        self.server = RPyCServer(self.makeRemoteService(), port)
        self.server.moveToThread(thread)
        thread.started.connect(self.server.run)
        thread.start()
        #self.nameserver.register('{0}-{1}'.format(self.hostname, name), server.uri)
        self.logger.logMsg('Started module server at {0} on port {1}'.format(self.hostname, port), msgType='status')

    def stopServer(self):
        if hasattr(self, 'server'):
            self.server.close()

    def shareModule(self, name, obj):
        if name in self.sharedModules:
            self.logger.logMsg('Module {0} already shared.'.format(name), msgType='warning')
        self.sharedModules[name] = obj
        self.logger.logMsg('Shared module {0}.'.format(name), msgType='status')

    def unshareModule(self, name):
        if name in self.sharedModules:
            self.logger.logMsg('Module {0} was not shared.'.format(name), msgType='error')
        self.sharedModules.popKey(name, None)

    def getRemoteModuleUrl(self, url):
        parsed = urlparse(url)
        name = parsed.path.replace('/', '')
        return self.getRemoteModule(parsed.hostname, parsed.port, name)

    def getRemoteModule(self, host, port, name):
        module = RemoteModule(host, port, name)
        self.remoteModules.append(module)
        return module.module


class RPyCServer(QtCore.QObject):
    def __init__(self, serviceClass, port):
        super().__init__()
        self.serviceClass = serviceClass
        self.port = port

    def run(self):
        self.server = ThreadedServer(self.serviceClass, port = self.port, protocol_config = {'allow_all_attrs': True })
        self.server.start()

class RemoteModule: 
    def __init__(self, host, port, name):
        self.connection = rpyc.connect(host, port, config={'allow_all_attrs': True})
        self.module = self.connection.root.getModule(name)
        self.name = name
