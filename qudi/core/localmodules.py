# -*- coding: utf-8 -*-
"""
This file contains the Qudi tools to provide an RPyC Server exposing qudi modules locally.
This is used for example by the qudi ipython kernel to interface with a running qudi instance.

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

__all__ = ('LocalModuleServer',)

import rpyc
from PySide2 import QtCore

from qudi.util.mutex import Mutex
from qudi.core.logger import get_logger
from qudi.core.modulemanager import ModuleManager

logger = get_logger(__name__)


class LocalModuleServer(QtCore.QObject):
    """ Contains a RPyC server that serves all qudi modules locally without encryption.
    You can specify the port but the host will always be "localhost"/127.0.0.1
    See qudi.core.remotemodules.RemoteModuleServer if you want to expose qudi modules to non-local
    clients.
    Runs in a QThread.
    """

    def __init__(self, *args, port=None, **kwargs):
        """
        @param int port: port the RPyC server should listen to
        """
        super().__init__(*args, **kwargs)
        self.service_instance = _LocalModulesService()
        self.port = int(port)
        self.server = None

    @property
    def is_running(self):
        return self.server is not None

    @QtCore.Slot()
    def run(self):
        """ Start the RPyC server
        """
        if self.is_running:
            logger.error(
                'Server is already running. Stop it first. Call to LocalModuleServer.run ignored.'
            )
            return
        try:
            self.server = rpyc.ThreadedServer(self.service_instance,
                                               hostname='127.0.0.1',
                                               port=self.port,
                                               protocol_config={'allow_all_attrs': True},
                                               authenticator=None)
            logger.info(f'Starting local module server on [127.0.0.1]:{self.port:d}')
            self.server.start()
        except:
            logger.exception('Error during start of LocalModuleServer:')
            self.server = None

    @QtCore.Slot()
    def stop(self):
        """ Stop the RPyC server
        """
        if self.is_running:
            self.server.close()
            self.server = None
            logger.info(f'Stopped local module server on [127.0.0.1]:{self.port:d}')


class _LocalModulesService(rpyc.Service):
    """ An RPyC service that has a module list.
    """
    ALIASES = ['LocalModules', '_LocalModules']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._thread_lock = Mutex()

    def on_connect(self, conn):
        """ code that runs when a connection is created
        """
        host, port = conn._config['endpoints'][1]
        logger.info(f'Client connected to local module service from [{host}]:{port:d}')

    def on_disconnect(self, conn):
        """ code that runs when the connection is closing
        """
        host, port = conn._config['endpoints'][1]
        logger.info(f'Client [{host}]:{port:d} disconnected from local module service')

    def _get_module_manager(self):
        mod_manager = ModuleManager.instance()
        if mod_manager is None:
            raise RuntimeError(
                'ModuleManager instance is not available. Qudi is probably not running.'
            )
        return mod_manager

    def exposed_get_module_instance(self, name):
        """ Return reference to a qudi module.

        @param str name: unique module name
        @return object: reference to the module instance. None if module has not been loaded yet.
        """
        with self._thread_lock:
            mod_manager = self._get_module_manager()
            module = mod_manager.get(name, None)
            return module.instance if module is not None else None

    def exposed_get_module_names(self):
        """ Returns the available module names.

        @return tuple: Names of the available modules
        """
        with self._thread_lock:
            mod_manager = self._get_module_manager()
            return mod_manager.module_names

    def exposed_get_loaded_module_names(self):
        """ Returns the currently shared module names for all modules that have been loaded
        (instantiated).

        @return tuple: Names of the currently shared loaded modules
        """
        with self._thread_lock:
            return tuple(self._get_module_manager().module_instances)

    def exposed_get_loaded_module_instances(self):
        """ Returns the currently loaded module instances.

        @return dict: Names (keys) and instances (values) of the currently loaded modules
        """
        with self._thread_lock:
            return self._get_module_manager().module_instances

    def exposed_get_active_module_names(self):
        """ Returns the names of the currently active modules.

        @return tuple: Names of the currently active modules
        """
        with self._thread_lock:
            mod_manager = self._get_module_manager()
            return tuple(name for name, mod in mod_manager.items() if mod.is_active)

    def exposed_get_active_module_instances(self):
        """ Returns the instances of the currently active modules.

        @return dict: Names (keys) and instances (values) of the currently active modules
        """
        with self._thread_lock:
            mod_manager = self._get_module_manager()
            return {name: mod.instance for name, mod in mod_manager.items() if mod.is_active}
