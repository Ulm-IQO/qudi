# -*- coding: utf-8 -*-
"""
This file contains the Qudi remotemodules object manager class.

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
from core.util.mutex import Mutex
from core.util.models import ListTableModel
from qtpy.QtCore import QObject
import rpyc
from rpyc.utils.authenticators import SSLAuthenticator
from weakref import WeakValueDictionary, WeakSet

logger = logging.getLogger(__name__)


class _RemoteModulesService(rpyc.Service):
    """ An RPyC service that has a module list.
    """
    ALIASES = ['RemoteModules', '_RemoteModules']
    shared_modules = WeakValueDictionary()
    _lock = Mutex()

    @classmethod
    def share_module(cls, module):
        with cls._lock:
            if module.name in cls.shared_modules:
                logger.debug(
                    'Module "{0}.{1}" already shared'.format(module.module_base, module.name))
                return
            cls.shared_modules[module.name] = module
            logger.debug('Started sharing module "{0}.{1}"'.format(module.module_base, module.name))

    @classmethod
    def remove_shared_module(cls, module):
        with cls._lock:
            name = module if isinstance(module, str) else module.name
            if name in cls.shared_modules:
                cls.shared_modules.pop(name, None)
                logger.debug('Stopped sharing module "{0}"'.format(name))

    def on_connect(self, conn):
        """ code that runs when a connection is created
        """
        logger.info('Client connected!')

    def on_disconnect(self, conn):
        """ code that runs when the connection has already closed
        """
        logger.info('Client disconnected!')

    def exposed_get_module_instance(self, name):
        """ Return reference to a module in the shared module list.

        @param str name: unique module name

        @return object: reference to the module
        """
        with self._lock:
            module = self.shared_modules.get(name, None)
            if module is None:
                logger.error('Client requested a module ("{0}") that is not shared.'.format(name))
                return None
            if not module.activate():
                logger.error('Unable to share requested module "{0}" with client. Module can not '
                             'be activated.'.format(name))
                return None
            return module.instance


class _RemoteServer(QObject):
    """ Contains a RPyC server that serves modules to remotemodules computers. Runs in a QThread.
    """
    def __init__(self, service_instance, config):
        """
        @param class service_instance: class instance that represents an RPyC service
        @param int port: port that hte RPyC server should listen on
        """
        super().__init__()
        self.service_instance = service_instance
        self.host = config.get('host')
        self.port = config.get('port')
        self.certfile = config.get('certfile', None)
        self.keyfile = config.get('keyfile', None)
        self.protocol_config = config.get('protocol_config', dict())
        self.ssl_version = config.get('ssl_version', None)
        self.cert_reqs = config.get('cert_reqs', None)
        self.ciphers = config.get('ciphers', None)
        self._server = None
        if self.certfile is None or self.keyfile is None:
            self.certfile = None
            self.keyfile = None

    @property
    def is_running(self):
        return self._server is not None

    def run(self):
        """ Start the RPyC server
        """
        if self._server is not None:
            logger.error(
                'Server is already running. Stop it first. Call to _RemoteServer.run ignored.')
            return

        if self.certfile is not None and self.keyfile is not None:
            authenticator = SSLAuthenticator(certfile=self.certfile,
                                             keyfile=self.keyfile,
                                             cert_reqs=self.cert_reqs,
                                             ssl_version=self.ssl_version,
                                             ciphers=self.ciphers)
        else:
            authenticator = None
        self._server = rpyc.ThreadedServer(self.service_instance,
                                           hostname=self.host,
                                           port=self.port,
                                           protocol_config=self.protocol_config,
                                           authenticator=authenticator)
        try:
            logger.info('Starting module server at "{0}" on port {1}'.format(self.host, self.port))
            self._server.start()
        except:
            logger.exception('Error during start of RemoteServer:')
            self._server = None
            return

    def stop(self):
        """ Stop the RPyC server
        """
        if self._server is not None:
            self._server.close()
            self._server = None
            logger.info('Stopped module server at "{0}" on port {1}'.format(self.host, self.port))


class SharedModulesModel(ListTableModel):
    """

    """
    __instances = WeakSet()
    __cls_lock = Mutex()

    def __init__(self):
        super().__init__(header='Shared Module')
        SharedModulesModel.__instances.add(self)

    @classmethod
    def add_shared_module(cls, module):
        with cls.__cls_lock:
            for instance in cls.__instances:
                if module.name not in instance:
                    instance.append(module.name)

    @classmethod
    def remove_shared_module(cls, module):
        with cls.__cls_lock:
            name = module if isinstance(module, str) else module.name
            for instance in cls.__instances:
                try:
                    instance.remove(name)
                except ValueError:
                    pass


def share_module(module):
    _RemoteModulesService.share_module(module)
    SharedModulesModel.add_shared_module(module)


def remove_shared_module(module):
    _RemoteModulesService.remove_shared_module(module)
    SharedModulesModel.remove_shared_module(module)
