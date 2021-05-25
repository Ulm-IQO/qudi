# -*- coding: utf-8 -*-
"""
This file contains the Qudi remote object manager class.

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


import logging
logger = logging.getLogger(__name__)

from qtpy.QtCore import QObject
from urllib.parse import urlparse
import ssl
from .util.models import DictTableModel, ListTableModel
import rpyc
from rpyc.utils.server import ThreadedServer
rpyc.core.protocol.DEFAULT_CONFIG['allow_pickle'] = True
import os
import sys


class SSLAuthenticator:
    """
    An SSL authenticator using an SSLContext as preferred since python 3.4
    """
    def __init__(self, server_key_file, server_cert_file, ca_certs=None):
        self.server_key_file = str(server_key_file)
        self.server_cert_file = str(server_cert_file)
        self.ca_certs = str(ca_certs) if ca_certs else None

    def __call__(self, sock):
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_cert_chain(certfile=self.server_cert_file, keyfile=self.server_key_file)
        if self.ca_certs is not None:
            context.load_verify_locations(cafile=self.ca_certs)

        try:
            conn = context.wrap_socket(sock, server_side=True)
        except ssl.SSLError:
            ex = sys.exc_info()[1]
            raise Exception(str(ex))
        return conn, conn.getpeercert()


class RemoteObjectManager(QObject):
    """ This shares modules with other computers and is responsible
        for obtaining modules shared by other computer.
    """
    def __init__(self, manager, **kwargs):
        """ Handle sharing and getting shared modules.
        """
        super().__init__(**kwargs)
        self.tm = manager.tm
        self.manager = manager
        self.server = None
        self.remoteModules = ListTableModel()
        self.remoteModules.headers[0] = 'Remote Modules'
        self.sharedModules = DictTableModel()
        self.sharedModules.headers[0] = 'Shared Modules'

    def makeRemoteService(self):
        """ A function that returns a class containing a module list hat can be manipulated from the host.
        """
        class RemoteModuleService(rpyc.Service):
            """ An RPyC service that has a module list.
            """
            modules = self.sharedModules
            _manager = self.manager

            @classmethod
            def get_service_name(cls):
                return 'RemoteModule'

            def on_connect(self, conn):
                """ code that runs when a connection is created
                    (to init the service, if needed)
                """
                logger.info('Client connected!')

            def on_disconnect(self, conn):
                """ code that runs when the connection has already closed
                    (to finalize the service, if needed)
                """
                logger.info('Client disconnected!')

            def exposed_getModule(self, name):
                """ Return reference to a module in the shared module list.

                  @param str name: unique module name

                  @return object: reference to the module
                """
                name = str(name)
                if name in self.modules.storage:
                    return self.modules.storage[name]
                else:
                    for base in ['hardware', 'logic', 'gui']:
                        logger.info('remotesearch: {0}'.format(name))
                        if name in self._manager.tree['defined'][base] and \
                                'remoteaccess' in self._manager.tree['defined'][base][name]:
                            self._manager.startModule(base, name)
                            logger.info('remoteload: {0}{1}'.format(base, name))
                    if name in self.modules.storage:
                        return self.modules.storage[name]
                    else:
                        logger.error('Client requested a module that is not shared.')
                        return None
        return RemoteModuleService

    def createServer(self, hostname, port, certfile=None, keyfile=None, cacertfile=None):
        """ Start the rpyc modules server on a given port.

          @param int port: port where the server should be running
        """
        thread = self.tm.newThread('rpyc-server')
        if certfile is not None and keyfile is not None:
            self.server = RPyCServer(
                self.makeRemoteService(),
                hostname,
                port,
                keyfile=keyfile,
                certfile=certfile,
                cacertsfile=cacertfile)
        else:
            if hostname != 'localhost':
                logger.warning('Remote connection not secured! Use a certificate!')
            self.server = RPyCServer(self.makeRemoteService(), hostname, port)
        self.server.moveToThread(thread)
        thread.started.connect(self.server.run)
        thread.start()
        logger.info('Started module server at {0} on port {1}'
                    ''.format(hostname, port))

    def stopServer(self):
        """ Stop the remote module server.
        """
        if self.server is not None:
            self.server.close()
            self.server = None

    def shareModule(self, name, obj):
        """ Add a module to the list of modules that can be accessed remotely.

          @param str name: unique name that is used to access the module
          @param object obj: a reference to the module
        """
        if name in self.sharedModules.storage:
            logger.warning('Module {0} already shared.'.format(name))
        self.sharedModules.add(name, obj)
        logger.info('Shared module {0}.'.format(name))

    def unshareModule(self, name):
        """ Remove a module from the shared module list.

          @param str name: unique name of the module that should not be accessible any more
        """
        if name in self.sharedModules.storage:
            logger.error('Module {0} was not shared.'.format(name))
        self.sharedModules.pop(name)

    def getRemoteModuleUrl(self, url, certfile=None, keyfile=None, cacertsfile=None):
        """ Get a remote module via its URL.

          @param str url: URL pointing to a module hosted b a remote server
          @param str certfile: filename of certificate or None if SSL is not used
          @param str keyfile: filename of key or None if SSL is not used
          @param str cacertsfile: filename of cacerts of None if SSL is not used

          @return object: remote module
        """
        parsed = urlparse(url)
        name = parsed.path.replace('/', '')
        return self.getRemoteModule(parsed.hostname, parsed.port, name, certfile, keyfile,
                                    cacertsfile)

    def getRemoteModule(self, host, port, name, certfile=None, keyfile=None, cacertsfile=None):
        """ Get a remote module via its host, port and name.

          @param str host: host that the remote module server is running on
          @param int port: port that the remote module server is listening on
          @param str name: unique name of the remote module
          @param str certfile: filename of certificate or None if SSL is not used
          @param str keyfile: filename of key or None if SSL is not used
          @param str cacertsfile: filename of cacerts of None if SSL is not used

          @return object: remote module
        """
        module = RemoteModule(host, port, name, certfile=certfile, keyfile=keyfile,
                              cacertsfile=cacertsfile)
        self.remoteModules.append(module)
        return module.module


class RPyCServer(QObject):
    """ Contains a RPyC server that serves modules to remote computers. Runs in a QThread.
    """
    def __init__(self, serviceClass, host, port, certfile=None, keyfile=None, cacertsfile=None):
        """
          @param class serviceClass: class that represents an RPyC service
          @param int port: port that hte RPyC server should listen on
        """
        super().__init__()
        self.serviceClass = serviceClass
        self.host = host
        self.port = port
        self.certfile = certfile
        self.keyfile = keyfile
        self.cacertsfile = cacertsfile

    def run(self):
        """ Start the RPyC server
        """
        if self.certfile is not None and self.keyfile is not None:
            if not os.path.exists(self.certfile):
                raise Exception('SSL certificate {0} does not exist.'.format(self.certfile))
            if not os.path.exists(self.keyfile):
                raise Exception('SSL private key file {0} does not exist.'.format(self.keyfile))
            if (self.cacertsfile is not None) and (not os.path.exists(self.cacertsfile)):
                logger.warning('SSL CA certificates file {0} does not exist.'.format(
                    self.cacertsfile))
            authenticator = SSLAuthenticator(server_key_file=self.keyfile,
                                             server_cert_file=self.certfile,
                                             ca_certs=self.cacertsfile)
            self.server = ThreadedServer(
                self.serviceClass,
                hostname=self.host,
                port=self.port,
                protocol_config={'allow_all_attrs': True},
                authenticator=authenticator)
        else:
            self.server = ThreadedServer(
                self.serviceClass,
                hostname=self.host,
                port=self.port,
                protocol_config={'allow_all_attrs': True})
        self.server.start()


class RemoteModule:
    """ This class represents a module on a remote computer and holds a reference to it.
    """
    def __init__(self, host, port, name, certfile=None, keyfile=None, cacertsfile=None):
        if certfile is not None and keyfile is not None:
            if not os.path.exists(certfile):
                raise Exception('SSL certificate {0} does not exist.'.format(certfile))
            if not os.path.exists(keyfile):
                raise Exception('SSL private key file {0} does not exist.'.format(keyfile))
            if (cacertsfile is not None) and (not os.path.exists(cacertsfile)):
                logger.warning('SSL CA certificates file {0} does not exist.'.format(cacertsfile))
            self.connection = rpyc.ssl_connect(
                host,
                port=port,
                config={'allow_all_attrs': True},
                certfile=certfile,
                keyfile=keyfile,
                ca_certs=cacertsfile,
                cert_reqs=ssl.CERT_REQUIRED)
        else:
            self.connection = rpyc.connect(host, port, config={'allow_all_attrs': True})
        self.module = self.connection.root.getModule(name)
        self.name = name
