# -*- coding: utf-8 -*-
"""
This file contains the Qudi tools for remote module sharing via rpyc server.

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

__all__ = ('get_remote_module_instance', 'get_remote_modules_model', 'start_sharing_module',
           'stop_sharing_module', 'RemoteModuleServer')

import ssl
import rpyc
import weakref
from rpyc.utils.authenticators import SSLAuthenticator
from urllib.parse import urlparse
from PySide2 import QtCore

from qudi.util.mutex import Mutex
from qudi.util.models import DictTableModel
from qudi.core.logger import get_logger

logger = get_logger(__name__)


def start_sharing_module(module):
    """ Helper method to start sharing modules

    @param ManagedModule module: The ManagedModule instance to share
    """
    _RemoteModulesService.share_module(module)


def stop_sharing_module(module):
    """ Helper method to stop sharing modules

    @param ManagedModule module: The ManagedModule instance or module name to stop sharing
    """
    _RemoteModulesService.remove_shared_module(module)


def get_remote_module_instance(remote_url, certfile=None, keyfile=None, protocol_config=None):
    """ Helper method to retrieve a remote module instance via rpyc from a Qudi RemoteModuleServer.

    @param str remote_url: The URL of the remote qudi module
    @param str certfile: Certificate file path for the request
    @param str keyfile: Key file path for the request
    @param dict protocol_config: optional, configuration options for rpyc.ssl_connect

    @return object: The requested qudi module instance (None if request failed)
    """
    parsed = urlparse(remote_url)
    if protocol_config is None:
        protocol_config = {'allow_all_attrs': True}
    connection = rpyc.ssl_connect(host=parsed.hostname,
                                  port=parsed.port,
                                  config=protocol_config,
                                  certfile=certfile,
                                  keyfile=keyfile)
    return connection.root.get_module_instance(parsed.path.replace('/', ''))


def get_remote_modules_model():
    return _RemoteModulesService.shared_modules


class _SharedModulesModel(DictTableModel):
    """ Derived dict model for GUI display elements
    """
    def __init__(self):
        super().__init__(headers='Shared Module')

    def data(self, index, role):
        """ Get data from model for a given cell. Data can have a role that affects display.

        @param QModelIndex index: cell for which data is requested
        @param ItemDataRole role: role for which data is requested

        @return QVariant: data for given cell and role
        """
        data = super().data(index, role)
        if data is None:
            return None
        # second column returns weakref.ref object
        if index.column() == 1:
            data = data()
        return data


class RemoteModuleServer(QtCore.QObject):
    """ Contains a RPyC server that serves modules to remotemodules computers. Runs in a QThread.
    """
    # Default configuration
    _protocol_config = {'allow_all_attrs': True}
    _ssl_version = ssl.PROTOCOL_TLSv1_2
    _cert_reqs = ssl.CERT_REQUIRED
    _ciphers = 'EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH'
    _port = 12345
    _host = 'localhost'
    _certfile = None
    _keyfile = None

    def __init__(self, host=None, port=None, certfile=None, keyfile=None, protocol_config=None,
                 ssl_version=None, cert_reqs=None, ciphers=None):
        """
        @param object service_instance: class instance that represents an RPyC service
        @param dict config: port that hte RPyC server should listen on
        """
        super().__init__()
        self.service_instance = _RemoteModulesService()
        self.host = self._host if host is None else str(host)
        self.port = self._port if port is None else int(port)
        self.certfile = self._certfile if certfile is None else certfile
        self.keyfile = self._keyfile if keyfile is None else keyfile
        self.protocol_config = self._protocol_config if protocol_config is None else protocol_config
        self.ssl_version = self._ssl_version if ssl_version is None else ssl_version
        self.cert_reqs = self._cert_reqs if cert_reqs is None else cert_reqs
        self.ciphers = self._ciphers if ciphers is None else ciphers
        if self.certfile is None or self.keyfile is None:
            self.certfile = None
            self.keyfile = None
        self._server = None

    @property
    def is_running(self):
        return self._server is not None

    @QtCore.Slot()
    def run(self):
        """ Start the RPyC server
        """
        if self.is_running:
            logger.error('Server is already running. Stop it first. Call to '
                         'RemoteModuleServer.run ignored.')
            return

        if self.certfile is not None and self.keyfile is not None:
            authenticator = SSLAuthenticator(certfile=self.certfile,
                                             keyfile=self.keyfile,
                                             cert_reqs=self.cert_reqs,
                                             ssl_version=self.ssl_version,
                                             ciphers=self.ciphers)
        else:
            authenticator = None

        try:
            self._server = rpyc.ThreadedServer(self.service_instance,
                                               hostname=self.host,
                                               port=self.port,
                                               protocol_config=self.protocol_config,
                                               authenticator=authenticator)
            logger.info(f'Starting remote module server on [{self.host}]:{self.port:d}')
            self._server.start()
        except:
            logger.exception('Error during start of RemoteServer:')
            self._server = None

    @QtCore.Slot()
    def stop(self):
        """ Stop the RPyC server
        """
        if self.is_running:
            self._server.close()
            self._server = None
            logger.info(f'Stopped remote module server on [{self.host}]:{self.port:d}')


class _RemoteModulesService(rpyc.Service):
    """ An RPyC service that has a module list.
    """
    ALIASES = ['RemoteModules', '_RemoteModules']

    shared_modules = _SharedModulesModel()
    _lock = Mutex()

    @classmethod
    def share_module(cls, module):
        with cls._lock:
            if module.name in cls.shared_modules:
                logger.debug(
                    'Module "{0}.{1}" already shared'.format(module.module_base, module.name))
                return
            cls.shared_modules[module.name] = weakref.ref(module)
            weakref.finalize(module, cls.remove_shared_module, module.name)
            logger.debug('Started sharing module "{0}.{1}"'.format(module.module_base, module.name))

    @classmethod
    def remove_shared_module(cls, module):
        with cls._lock:
            name = module if isinstance(module, str) else module.name
            if cls.shared_modules.pop(name, None) is not None:
                logger.debug('Stopped sharing module "{0}"'.format(name))

    def on_connect(self, conn):
        """ code that runs when a connection is created
        """
        host, port = conn._config['endpoints'][1]
        logger.info(f'Client connected to remote module service from [{host}]:{port:d}')

    def on_disconnect(self, conn):
        """ code that runs when the connection is closing
        """
        host, port = conn._config['endpoints'][1]
        logger.info(f'Client [{host}]:{port:d} disconnected from remote module service')

    def exposed_get_module_instance(self, name, activate=False):
        """ Return reference to a module in the shared module list.

        @param str name: unique module name

        @return object: reference to the module
        """
        with self._lock:
            try:
                module = self.shared_modules.get(name, None)()
            except TypeError:
                logger.error('Client requested a module ("{0}") that is not shared.'.format(name))
                return None
            if activate:
                if not module.activate():
                    logger.error('Unable to share requested module "{0}" with client. Module can not '
                                 'be activated.'.format(name))
                    return None
            return module.instance

    def exposed_get_available_module_names(self):
        """ Returns the currently shared module names.

        @return tuple: Names of the currently shared modules
        """
        with self._lock:
            return tuple(name for name, ref in self.shared_modules.items() if ref() is not None)

    def exposed_get_loaded_module_names(self):
        """ Returns the currently shared module names for all modules that have been loaded
        (instantiated).

        @return tuple: Names of the currently shared loaded modules
        """
        with self._lock:
            return tuple(name for name, ref in self.shared_modules.items() if
                         ref() is not None and ref().instance is not None)

    def exposed_get_active_module_names(self):
        """ Returns the currently shared module names for all modules that are active.

        @return tuple: Names of the currently shared active modules
        """
        with self._lock:
            return tuple(name for name, ref in self.shared_modules.items() if
                         ref() is not None and ref().is_active)
