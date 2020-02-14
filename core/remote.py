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
from qtpy.QtCore import QObject
from urllib.parse import urlparse
import ssl
from .util.models import DictTableModel, ListTableModel
import rpyc
from rpyc.utils.server import ThreadedServer
from rpyc.utils.authenticators import SSLAuthenticator
from .manager import Manager

logger = logging.getLogger(__name__)
rpyc.core.protocol.DEFAULT_CONFIG['allow_pickle'] = True


class RemoteObjectManager(QObject):
    """ This shares modules with other computers and is responsible
        for obtaining modules shared by other computer.
    """
    def __init__(self, manager, **kwargs):
        """ Handle sharing and getting shared modules.
        """
        super().__init__(**kwargs)
        if not isinstance(manager, Manager):
            raise TypeError('manager argument must be Manager class instance.')
        self.__manager = manager
        self.remote_modules = ListTableModel()
        self.remote_modules.headers[0] = 'Remote Modules'
        self.shared_modules = DictTableModel()
        self.shared_modules.headers[0] = 'Shared Modules'
        self.server = None

    def make_remote_service(self):
        """ A function that returns a class containing a module list hat can be manipulated from
        the host.
        """
        class RemoteModuleService(rpyc.Service):
            """ An RPyC service that has a module list.
            """
            modules = self.shared_modules
            _manager = self.__manager

            @staticmethod
            def get_service_name():
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
                    logger.info('remotesearch: {0}'.format(name))
                    if name in self._manager.managed_modules:
                        module = self._manager.managed_modules[name]
                        if module.allow_remote_access:
                            self._manager.activate_module(name)
                            logger.info('remote load: {0}.{1}'.format(module.module_base, name))
                    if name in self.modules.storage:
                        return self.modules.storage[name]
                    else:
                        logger.error('Client requested a module that is not shared.')
                        return None
        return RemoteModuleService

    def create_server(self, hostname, port, certfile=None, keyfile=None):
        """ Start the rpyc modules server on a given port.

        @param str hostname:
        @param int port: port where the server should be running
        @param str certfile:
        @param str keyfile:
        """
        thread = self.__manager.thread_manager.get_new_thread('rpyc-server')
        if certfile is not None and keyfile is not None:
            self.server = RPyCServer(self.make_remote_service(),
                                     hostname,
                                     port,
                                     keyfile=keyfile,
                                     certfile=certfile)
        else:
            if hostname != 'localhost':
                logger.warning('Remote connection not secured! Use a certificate!')
            self.server = RPyCServer(self.make_remote_service(), hostname, port)
        self.server.moveToThread(thread)
        thread.started.connect(self.server.run)
        thread.start()
        logger.info('Started module server at {0} on port {1}'.format(hostname, port))

    def stop_server(self):
        """ Stop the remote module server.
        """
        if self.server is not None:
            self.server.close()

    def share_module(self, name, obj):
        """ Add a module to the list of modules that can be accessed remotely.

        @param str name: unique name that is used to access the module
        @param object obj: a reference to the module
        """
        if name in self.shared_modules.storage:
            logger.warning('Module "{0}" already shared.'.format(name))
        self.shared_modules.add(name, obj)
        logger.info('Shared module "{0}".'.format(name))

    def remove_shared_module(self, name):
        """ Remove a module from the shared module list.

        @param str name: unique name of the module that should not be accessible any more
        """
        if name not in self.shared_modules.storage:
            logger.error('Module "{0}" was not shared.'.format(name))
            return
        self.shared_modules.pop(name)

    def get_remote_module_from_url(self, url, certfile=None, keyfile=None):
        """ Get a remote module via its URL.

        @param str url: URL pointing to a module hosted b a remote server
        @param str certfile: filename of certificate or None if SSL is not used
        @param str keyfile: filename of key or None if SSL is not used

        @return object: remote module
        """
        # FIXME: This method gets mainly called by Manager but certfile and keyfile are not used.
        parsed = urlparse(url)
        name = parsed.path.replace('/', '')
        return self.get_remote_module(parsed.hostname, parsed.port, name)

    def get_remote_module(self, host, port, name, certfile=None, keyfile=None):
        """ Get a remote module via its host, port and name.

        @param str host: host that the remote module server is running on
        @param int port: port that the remote module server is listening on
        @param str name: unique name of the remote module
        @param str certfile: filename of certificate or None if SSL is not used
        @param str keyfile: filename of key or None if SSL is not used

        @return object: remote module
        """
        module = RemoteModule(host, port, name, certfile=certfile, keyfile=keyfile)
        self.remote_modules.append(module)
        return module.module


class RPyCServer(QObject):
    """ Contains a RPyC server that serves modules to remote computers. Runs in a QThread.
    """
    def __init__(self, service_class, host, port, certfile=None, keyfile=None):
        """
          @param class service_class: class that represents an RPyC service
          @param int port: port that hte RPyC server should listen on
        """
        super().__init__()
        self.service_class = service_class
        self.host = host
        self.port = port
        self.certfile = certfile
        self.keyfile = keyfile
        self.server = None

    def run(self):
        """ Start the RPyC server
        """
        if self.certfile is not None and self.keyfile is not None:
            authenticator = SSLAuthenticator(self.certfile, self.keyfile)
            self.server = ThreadedServer(
                self.serviceClass,
                hostname=self.host,
                port=self.port,
                protocol_config={'allow_all_attrs': True},
                authenticator=authenticator,
                cert_reqs=ssl.CERT_REQUIRED,
                ciphers='EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH',
                ssl_version=ssl.PROTOCOL_TLSv1_2)
        else:
            self.server = ThreadedServer(
                self.serviceClass,
                hostname=self.host,
                port=self.port,
                protocol_config={'allow_all_attrs': True})
        self.server.start()

    def close(self):
        if self.server is not None:
            self.server.close()


class RemoteModule:
    """ This class represents a module on a remote computer and holds a reference to it.
    """
    def __init__(self, host, port, name, certfile=None, keyfile=None):
        if certfile is not None and keyfile is not None:
            self.connection = rpyc.ssl_connect(host,
                                               port=port,
                                               config={'allow_all_attrs': True},
                                               certfile=certfile,
                                               keyfile=keyfile)
        else:
            self.connection = rpyc.connect(host, port, config={'allow_all_attrs': True})
        self.name = name

    @property
    def module(self):
        return self.connection.root.getModule(self.name)
