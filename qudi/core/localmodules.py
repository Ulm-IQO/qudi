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
import weakref
from PySide2 import QtCore

from qudi.core.logger import get_logger

logger = get_logger(__name__)


class LocalModuleServer(QtCore.QObject):
    """ Contains a RPyC server that serves all qudi modules locally without encryption.
    You can specify the port but the host will always be "localhost"/127.0.0.1
    See qudi.core.remotemodules.RemoteModuleServer if you want to expose qudi modules to non-local
    clients.
    Actual rpyc server runs in a QThread.
    """

    def __init__(self, *args, module_manager, thread_manager, port, **kwargs):
        """
        @param int port: port the RPyC server should listen to
        """
        super().__init__(*args, **kwargs)
        self.port = int(port)
        self.server = None
        self.service_instance = _LocalModulesService(module_manager=module_manager)
        self._module_manager_ref = weakref.ref(module_manager)
        self._thread_manager_ref = weakref.ref(thread_manager)

    @property
    def _thread_manager(self):
        thread_manager = self._thread_manager_ref()
        if thread_manager is None:
            raise RuntimeError('Dead qudi ThreadManager reference encountered.')
        return thread_manager

    @property
    def _module_manager(self):
        module_manager = self._module_manager_ref()
        if module_manager is None:
            raise RuntimeError('Dead qudi ModuleManager reference encountered.')
        return module_manager

    @QtCore.Slot()
    def start(self):
        """ Start the RPyC server
        """
        if self.server is None:
            self.server = _LocalModuleServerRunnable(service=self.service_instance, port=self.port)
            thread = self._thread_manager.get_new_thread('local-module-server')
            self.server.moveToThread(thread)
            thread.started.connect(self.server.run)
            self._module_manager.sigModuleStateChanged.connect(
                self.service_instance.notify_module_change
            )
            thread.start()
        else:
            logger.warning('LocalModuleServer is already running.')

    @QtCore.Slot()
    def stop(self):
        """ Stop the RPyC server
        """
        if self.server is not None:
            try:
                self._module_manager.sigModuleStateChanged.disconnect(
                    self.service_instance.notify_module_change
                )
            except AttributeError:
                pass
            try:
                self.server.stop()
                self._thread_manager.quit_thread('local-module-server')
                self._thread_manager.join_thread('local-module-server', time=5)
            finally:
                self.server = None


class _LocalModuleServerRunnable(QtCore.QObject):
    """ QObject containing the actual long-running code to execute in a separate thread for the
    rpyc module server.
    """
    def __init__(self, *args, service, port, **kwargs):
        super().__init__(*args, **kwargs)
        self.server = None
        self.port = port
        self._service = service

    @QtCore.Slot()
    def run(self):
        """ Start the RPyC server
        """
        try:
            self.server = rpyc.ThreadedServer(self._service,
                                              hostname='localhost',
                                              port=self.port,
                                              protocol_config={'allow_all_attrs': True})
            logger.info(f'Starting local module server on [localhost]:{self.port:d}')
            self.server.start()
        except:
            logger.exception('Error during start of LocalModuleServer:')
            self.server = None

    @QtCore.Slot()
    def stop(self):
        """ Stop the RPyC server
        """
        if self.server is not None:
            try:
                self.server.close()
                logger.info(f'Stopped local module server on [localhost]:{self.port:d}')
            except:
                logger.exception(f'Exception while trying to stop local module server on '
                                 f'[localhost]:{self.port:d}')
            finally:
                self.server = None


class _LocalModulesService(rpyc.Service):
    """ An RPyC service that has a module list.
    """
    ALIASES = ['LocalModules', '_LocalModules']

    def __init__(self, *args, module_manager, **kwargs):
        super().__init__(*args, **kwargs)
        self.__module_manager_ref = weakref.ref(module_manager)
        self._notifier_callbacks = dict()

    def on_connect(self, conn):
        """ code that runs when a connection is created
        """
        try:
            self._notifier_callbacks[conn] = rpyc.async_(conn.root.modules_changed)
        except AttributeError:
            pass
        host, port = conn._config['endpoints'][1]
        logger.info(f'Client connected to local module service from [{host}]:{port:d}')

    def on_disconnect(self, conn):
        """ code that runs when the connection is closing
        """
        self._notifier_callbacks.pop(conn, None)
        host, port = conn._config['endpoints'][1]
        logger.info(f'Client [{host}]:{port:d} disconnected from local module service')

    @property
    def _module_manager(self):
        mod_manager = self.__module_manager_ref()
        if mod_manager is None:
            raise RuntimeError(
                'ModuleManager instance is not available. Qudi is probably not running.'
            )
        return mod_manager

    def notify_module_change(self):
        logger.debug('Local module server has detected a module state change and sends async '
                     'notifier signals to all clients')
        for callback in self._notifier_callbacks.values():
            callback()

    def exposed_get_module_instance(self, name):
        """ Return reference to a qudi module.

        @param str name: unique module name
        @return object: reference to the module instance. None if module has not been loaded yet.
        """
        module = self._module_manager.get(name, None)
        return module.instance if module is not None else None

    def exposed_get_module_names(self):
        """ Returns the available module names.

        @return tuple: Names of the available modules
        """
        return self._module_manager.module_names

    def exposed_get_loaded_module_instances(self):
        """ Returns the currently loaded module instances.

        @return dict: Names (keys) and instances (values) of the currently loaded modules
        """
        return self._module_manager.module_instances

    def exposed_get_active_module_instances(self):
        """ Returns the instances of the currently active modules.

        @return dict: Names (keys) and instances (values) of the currently active modules
        """
        return {name: mod.instance for name, mod in self._module_manager.items() if mod.is_active}
