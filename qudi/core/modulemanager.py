# -*- coding: utf-8 -*-
"""
This file contains the Qudi Manager class.

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

import os
import importlib
import copy
import weakref

from functools import partial
from PySide2 import QtCore

from qudi.util.mutex import RecursiveMutex   # provides access serialization between threads
from qudi.core.logger import get_logger
from qudi.core.threadmanager import ThreadManager
from qudi.core.servers import get_remote_module_instance
from qudi.core.module import Base, get_module_app_data_path

logger = get_logger(__name__)


class ModuleManager(QtCore.QObject):
    """
    """
    _instance = None  # Only class instance created will be stored here as weakref
    _lock = RecursiveMutex()

    sigModuleStateChanged = QtCore.Signal(str, str, str)
    sigModuleAppDataChanged = QtCore.Signal(str, str, bool)
    sigManagedModulesChanged = QtCore.Signal(dict)

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None or cls._instance() is None:
                obj = super().__new__(cls, *args, **kwargs)
                cls._instance = weakref.ref(obj)
                return obj
            raise RuntimeError(
                'ModuleManager is a singleton. An instance has already been created in this '
                'process. Please use ModuleManager.instance() instead.'
            )

    def __init__(self, *args, qudi_main, **kwargs):
        super().__init__(*args, **kwargs)
        self._qudi_main_ref = weakref.ref(qudi_main, self._qudi_main_ref_dead_callback)
        self._modules = dict()

    @classmethod
    def instance(cls):
        with cls._lock:
            if cls._instance is None:
                return None
            return cls._instance()

    def __len__(self):
        with self._lock:
            return len(self._modules)

    def __getitem__(self, key):
        with self._lock:
            return self._modules.__getitem__(key)

    def __setitem__(self, key, value):
        with self._lock:
            if value.name != key:
                raise NameError('ManagedModule.name attribute does not match key')
            self.add_module(value, allow_overwrite=True)

    def __delitem__(self, key):
        self.remove_module(key)

    def __contains__(self, item):
        with self._lock:
            return self._modules.__contains__(item)

    def clear(self):
        with self._lock:
            for module_name in tuple(self._modules):
                self.remove_module(module_name, ignore_missing=True, emit_change=False)
            self.sigManagedModulesChanged.emit(self.modules)

    def get(self, *args):
        with self._lock:
            return self._modules.get(*args)

    def items(self):
        return self._modules.copy().items()

    def values(self):
        return self._modules.copy().values()

    def keys(self):
        return self._modules.copy().keys()

    @property
    def module_names(self):
        with self._lock:
            return tuple(self._modules)

    @property
    def module_states(self):
        with self._lock:
            return {name: mod.state for name, mod in self._modules.items()}

    @property
    def module_instances(self):
        with self._lock:
            return {name: mod.instance for name, mod in self._modules.items() if
                    mod.instance is not None}

    @property
    def modules(self):
        return self._modules.copy()

    def remove_module(self, module_name, ignore_missing=False, emit_change=True):
        with self._lock:
            if module_name not in self._modules:
                if not ignore_missing:
                    logger.error(
                        f'No module with name "{module_name}" registered. Unable to remove module.'
                    )
                return
            self._modules[module_name].deactivate()
            self._modules[module_name].sigStateChanged.disconnect(self.sigModuleStateChanged)
            self._modules[module_name].sigAppDataChanged.disconnect(self.sigModuleAppDataChanged)
            self.refresh_module_links()
            if self._modules[module_name].allow_remote_access:
                remote_modules_server = self._qudi_main_ref().remote_modules_server
                if remote_modules_server is not None:
                    remote_modules_server.remove_shared_module(module_name)
            del self._modules[module_name]
            if emit_change:
                self.sigManagedModulesChanged.emit(self.modules)

    def add_module(self, name, base, configuration, allow_overwrite=False, emit_change=True):
        with self._lock:
            if not isinstance(name, str) or not name:
                raise TypeError('module name must be non-empty str type')
            if base not in ('gui', 'logic', 'hardware'):
                logger.error(
                    f'No valid module base "{base}". Unable to create qudi module "{name}".'
                )
                return
            if allow_overwrite:
                self.remove_module(name, ignore_missing=True)
            elif name in self._modules:
                logger.error(
                    'Module with name "{0}" already registered. Unable to add module of same name.')
                return
            module = ManagedModule(self._qudi_main_ref, name, base, configuration)
            module.sigStateChanged.connect(self.sigModuleStateChanged)
            module.sigAppDataChanged.connect(self.sigModuleAppDataChanged)
            self._modules[name] = module
            self.refresh_module_links()
            # Register module in remote module service if module should be shared
            if module.allow_remote_access:
                remote_modules_server = self._qudi_main_ref().remote_modules_server
                if remote_modules_server is None:
                    logger.error(f'Unable to share qudi module "{module.name}" as remote module. '
                                 f'No remote module server running in this qudi process.')
                else:
                    logger.info(
                        f'Start sharing qudi module "{module.name}" via remote module server.'
                    )
                    remote_modules_server.share_module(module)
            if emit_change:
                self.sigManagedModulesChanged.emit(self.modules)

    def refresh_module_links(self):
        with self._lock:
            weak_refs = {
                name: weakref.ref(mod, partial(self._module_ref_dead_callback, module_name=name))
                for name, mod in self._modules.items()}
            for module_name, module in self._modules.items():
                # Add required module references
                required = set(module.connection_cfg.values())
                module.required_modules = set(
                    mod_ref for name, mod_ref in weak_refs.items() if name in required)
                # Add dependent module references
                module.dependent_modules = set(mod_ref for mod_ref in weak_refs.values() if
                                               module_name in mod_ref().connection_cfg.values())
            return

    def activate_module(self, module_name):
        with self._lock:
            if module_name not in self._modules:
                logger.error(f'No module named "{module_name}" found in managed qudi modules. '
                             f'Module activation aborted.')
                return False
            return self._modules[module_name].activate()

    def deactivate_module(self, module_name):
        with self._lock:
            if module_name not in self._modules:
                logger.error(f'No module named "{module_name}" found in managed qudi modules. '
                             f'Module deactivation aborted.')
                return False
            return self._modules[module_name].deactivate()

    def reload_module(self, module_name):
        with self._lock:
            if module_name not in self._modules:
                logger.error(f'No module named "{module_name}" found in managed qudi modules. '
                             f'Module reload aborted.')
                return False
            return self._modules[module_name].reload()

    def clear_module_app_data(self, module_name):
        with self._lock:
            if module_name not in self._modules:
                logger.error(f'No module named "{module_name}" found in managed qudi modules. '
                             f'Can not clear module app status.')
                return False
            return self._modules[module_name].clear_module_app_data()

    def has_app_data(self, module_name):
        with self._lock:
            if module_name not in self._modules:
                logger.error(f'No module named "{module_name}" found in managed qudi modules. '
                             f'Can not check for app status file.')
                return False
            return self._modules[module_name].has_app_data()

    def start_all_modules(self):
        with self._lock:
            for module in self._modules.values():
                module.activate()

    def stop_all_modules(self):
        with self._lock:
            for module in self._modules.values():
                module.deactivate()

    def _module_ref_dead_callback(self, dead_ref, module_name):
        with self._lock:
            self.remove_module(module_name, ignore_missing=True)

    def _qudi_main_ref_dead_callback(self):
        logger.error('Qudi main reference no longer valid. This should never happen. Tearing down '
                     'ModuleManager.')
        self.clear()


class ManagedModule(QtCore.QObject):
    """ Object representing a qudi module (gui, logic or hardware) to be managed by the qudi Manager
     object. Contains status properties and handles initialization, state transitions and
     connection of the module.
    """
    sigStateChanged = QtCore.Signal(str, str, str)
    sigAppDataChanged = QtCore.Signal(str, str, bool)

    _lock = RecursiveMutex()  # Single mutex shared across all ManagedModule instances

    __state_poll_interval = 1  # Max interval in seconds to poll module_state of remote modules

    def __init__(self, qudi_main_ref, name, base, configuration):
        if not isinstance(qudi_main_ref, weakref.ref):
            raise TypeError('qudi_main_ref must be weakref to qudi main instance.')
        if not name or not isinstance(name, str):
            raise ValueError('Module name must be a non-empty string.')
        if base not in ('gui', 'logic', 'hardware'):
            raise ValueError('Module base must be one of ("gui", "logic", "hardware").')
        if 'module.Class' not in configuration and 'remote_url' not in configuration:
            raise ValueError(f'Module config entry must contain either "module.Class" or '
                             f'"remote_url". None of them was found in config for module "{name}".')
        if not isinstance(configuration.get('module.Class', ''), str):
            raise TypeError(f'module.Class config entry of module "{name}" must be str type.')
        if not isinstance(configuration.get('remote_url', ''), str):
            raise TypeError(f'remote URL of module "{name}" must be of str type.')
        if not isinstance(configuration.get('certfile', ''), str):
            raise TypeError(
                f'certfile config option of remotemodules module "{name}" must be of str type.'
            )
        if not isinstance(configuration.get('keyfile', ''), str):
            raise TypeError(
                f'keyfile config option of remotemodules module "{name}" must be of str type.'
            )
        if not isinstance(configuration.get('remoteaccess', False), bool):
            raise TypeError(f'remoteaccess config option of remotemodules module "{name}" must be '
                            f'of bool type.')

        super().__init__()
        if self.thread() is not QtCore.QCoreApplication.instance().thread():
            raise RuntimeError('ManagedModules can only be owned by the application main thread.')

        self._qudi_main_ref = qudi_main_ref  # Weak reference to qudi main instance
        self._name = name  # Each qudi module needs a unique string identifier
        self._base = base  # Remember qudi module base
        self._instance = None  # Store the module instance later on

        # Sort out configuration dict
        cfg = copy.deepcopy(configuration)
        # Extract module and class name
        self._module, self._class = cfg.pop('module.Class', 'REMOTE.REMOTE').rsplit('.', 1)
        # Remember connections by name
        self._connect_cfg = cfg.pop('connect', dict())
        # See if remotemodules access to this module is allowed (allowed by default)
        self._allow_remote_access = cfg.pop('allow_remote', False)
        # Extract remote modules URL and certificate if this module is run on a remote machine
        self._remote_url = cfg.pop('remote_url', None)
        self._remote_certfile = cfg.pop('certfile', None)
        self._remote_keyfile = cfg.pop('keyfile', None)
        # Do not propagate remotemodules access
        if self._remote_url:
            self._allow_remote_access = False
        # The rest are config options
        self._options = cfg

        self._required_modules = set()
        self._dependent_modules = set()

        self.__poll_timer = None
        self.__last_state = None
        return

    def __call__(self):
        return self.instance

    @property
    def name(self):
        return self._name

    @property
    def module_base(self):
        return self._base

    @property
    def class_name(self):
        return self._class

    @property
    def module_name(self):
        return self._module

    @property
    def options(self):
        return copy.deepcopy(self._options)

    @property
    def instance(self):
        with self._lock:
            return self._instance

    @property
    def status_file_path(self):
        return get_module_app_data_path(self.class_name, self.module_base, self.name)

    @property
    def is_loaded(self):
        with self._lock:
            return self._instance is not None

    @property
    def is_active(self):
        with self._lock:
            return self._instance is not None and self._instance.module_state() != 'deactivated'

    @property
    def is_busy(self):
        with self._lock:
            return self.is_active and self._instance.module_state() != 'idle'

    @property
    def is_remote(self):
        return bool(self._remote_url)

    @property
    def allow_remote_access(self):
        return self._allow_remote_access

    @property
    def remote_url(self):
        return self._remote_url

    @property
    def remote_key_path(self):
        return self._remote_keyfile

    @property
    def remote_cert_path(self):
        return self._remote_certfile

    @property
    def state(self):
        with self._lock:
            if self._instance is None:
                return 'not loaded'
            try:
                return self._instance.module_state()
            except:
                return 'BROKEN'

    @property
    def connection_cfg(self):
        return self._connect_cfg.copy()

    @property
    def required_modules(self):
        with self._lock:
            return self._required_modules.copy()

    @required_modules.setter
    def required_modules(self, module_iter):
        for module in module_iter:
            if not isinstance(module, weakref.ref):
                raise TypeError('items in required_modules must be weakref.ref instances.')
            if not isinstance(module(), ManagedModule):
                if module() is None:
                    logger.error(
                        f'Dead weakref passed as required module to ManagedModule "{self._name}"'
                    )
                    return
                raise TypeError('required_modules must be iterable of ManagedModule instances '
                                '(or weakref to same instances)')
        self._required_modules = set(module_iter)

    @property
    def dependent_modules(self):
        with self._lock:
            return self._dependent_modules.copy()

    @dependent_modules.setter
    def dependent_modules(self, module_iter):
        dep_modules = set()
        for module in module_iter:
            if not isinstance(module, weakref.ref):
                raise TypeError('items in dependent_modules must be weakref.ref instances.')
            if not isinstance(module(), ManagedModule):
                if module() is None:
                    logger.error(
                        f'Dead weakref passed as dependent module to ManagedModule "{self._name}"'
                    )
                    return
                raise TypeError('dependent_modules must be iterable of ManagedModule instances '
                                '(or weakref to same instances)')
            dep_modules.add(module)
        self._dependent_modules = dep_modules

    @property
    def ranking_active_dependent_modules(self):
        with self._lock:
            active_dependent_modules = set()
            for module_ref in self._dependent_modules:
                module = module_ref()
                if module is None:
                    logger.warning(f'Dead dependent module weakref encountered in ManagedModule '
                                   f'"{self._name}".')
                    continue
                if module.is_active:
                    active_modules = module.ranking_active_dependent_modules
                    if active_modules:
                        active_dependent_modules.update(active_modules)
                    else:
                        active_dependent_modules.add(module_ref)
            return active_dependent_modules

    @property
    def module_thread_name(self):
        return f'mod-{self._base}-{self._name}'

    @property
    def has_app_data(self):
        with self._lock:
            return os.path.exists(self.status_file_path)

    @QtCore.Slot()
    def clear_module_app_data(self):
        with self._lock:
            try:
                os.remove(self.status_file_path)
            except OSError:
                return False
            self.sigAppDataChanged.emit(self._base, self._name, self.has_app_data)
            return True

    @QtCore.Slot()
    def activate(self):
        if QtCore.QThread.currentThread() is not self.thread():
            QtCore.QMetaObject.invokeMethod(self, 'activate', QtCore.Qt.BlockingQueuedConnection)
            return self.is_active
        with self._lock:
            if not self.is_loaded:
                if not self._load():
                    return False

            if self.is_active:
                if self._base == 'gui':
                    self._instance.show()
                return True

            if self.is_remote:
                logger.info(f'Activating remote {self._base} module "{self._remote_url}"')
            else:
                logger.info(f'Activating {self._base} module "{self._module}.{self._class}"')

            # Recursive activation of required modules
            for module_ref in self._required_modules:
                module = module_ref()
                if module is None:
                    logger.error(f'Dead required module weakref encountered in ManagedModule '
                                 f'"{self._name}".')
                    return False
                if not module.is_active:
                    if not module.activate():
                        return False

            # Establish module interconnections via Connector meta object in qudi module instance
            if not self._connect():
                return False

            try:
                if self._instance.is_module_threaded:
                    thread_name = self.module_thread_name
                    thread_manager = ThreadManager.instance()
                    if thread_manager is None:
                        return False
                    thread = thread_manager.get_new_thread(thread_name)
                    self._instance.moveToThread(thread)
                    thread.start()
                    QtCore.QMetaObject.invokeMethod(self._instance.module_state,
                                                    'activate',
                                                    QtCore.Qt.BlockingQueuedConnection)
                    # Cleanup if activation was not successful
                    if not self.is_active:
                        QtCore.QMetaObject.invokeMethod(self._instance,
                                                        'move_to_main_thread',
                                                        QtCore.Qt.BlockingQueuedConnection)
                        thread_manager.quit_thread(thread_name)
                        thread_manager.join_thread(thread_name)
                else:
                    self._instance.module_state.activate()
                if not self.is_active:
                    return False
            except:
                logger.exception(
                    f'Massive error during activation of module "{self._base}.{self._name}"'
                )
                return False
            self.__last_state = self.state
            self.sigStateChanged.emit(self._base, self._name, self.__last_state)
            self.sigAppDataChanged.emit(self._base, self._name, self.has_app_data)
            if self.is_remote:
                self.__poll_timer = QtCore.QTimer(self)
                self.__poll_timer.setInterval(int(round(self.__state_poll_interval * 1000)))
                self.__poll_timer.setSingleShot(True)
                self.__poll_timer.timeout.connect(self._poll_module_state)
                self.__poll_timer.start()
            else:
                self._instance.module_state.sigStateChanged.connect(self._state_change_callback)

            if self.is_active:
                if self._base == 'gui':
                    self._qudi_main_ref().gui.add_to_system_tray(self._name, self._instance.show)
            return True

    @QtCore.Slot()
    def _poll_module_state(self):
        with self._lock:
            state = self.state
            if state != self.__last_state:
                self.__last_state = state
                self.sigStateChanged.emit(self._base, self._name, state)
            if self.__poll_timer is not None:
                self.__poll_timer.start()

    @QtCore.Slot()
    @QtCore.Slot(object)
    def _state_change_callback(self, event=None):
        self.sigStateChanged.emit(self._base, self._name, self.state)

    @QtCore.Slot()
    def deactivate(self):
        if QtCore.QThread.currentThread() is not self.thread():
            QtCore.QMetaObject.invokeMethod(self, 'deactivate', QtCore.Qt.BlockingQueuedConnection)
            return not self.is_active
        with self._lock:
            if not self.is_active:
                return True

            if self.is_remote:
                logger.info(f'Deactivating remote {self._base} module "{self._remote_url}"')
            else:
                logger.info(f'Deactivating {self._base} module "{self._module}.{self._class}"')

            success = True  # error flag to return

            # Recursively deactivate dependent modules
            for module_ref in self._dependent_modules:
                module = module_ref()
                if module is None:
                    logger.error(f'Dead dependent module weakref encountered in ManagedModule '
                                 f'"{self._name}".')
                    return False
                if module.is_active:
                    success = success and module.deactivate()

            # Disable state updated
            if self.__poll_timer is not None:
                self.__poll_timer.stop()
                self.__poll_timer.timeout.disconnect()
                self.__poll_timer = None
            else:
                self._instance.module_state.sigStateChanged.disconnect(self._state_change_callback)

            # Actual deactivation of this module
            try:
                if self._instance.is_module_threaded:
                    thread_name = self.module_thread_name
                    thread_manager = ThreadManager.instance()
                    if thread_manager is None:
                        return False
                    QtCore.QMetaObject.invokeMethod(self._instance.module_state,
                                                    'deactivate',
                                                    QtCore.Qt.BlockingQueuedConnection)
                    QtCore.QMetaObject.invokeMethod(self._instance,
                                                    'move_to_main_thread',
                                                    QtCore.Qt.BlockingQueuedConnection)
                    thread_manager.quit_thread(thread_name)
                    thread_manager.join_thread(thread_name)
                else:
                    self._instance.module_state.deactivate()
                QtCore.QCoreApplication.instance().processEvents()
                success = success and not self.is_active
            except:
                logger.exception(
                    f'Massive error during deactivation of module "{self._base}.{self._name}"'
                )
                success = False
            success = success and self._disconnect()
            self.__last_state = self.state
            self.sigStateChanged.emit(self._base, self._name, self.__last_state)
            self.sigAppDataChanged.emit(self._base, self._name, self.has_app_data)

            if self._base == 'gui':
                self._qudi_main_ref().gui.remove_from_system_tray(self._name)

            return success

    @QtCore.Slot()
    def reload(self):
        if QtCore.QThread.currentThread() is not self.thread():
            QtCore.QMetaObject.invokeMethod(self, 'reload', QtCore.Qt.BlockingQueuedConnection)
        with self._lock:
            # Deactivate if active
            was_active = self.is_active
            mod_to_activate = None
            if was_active:
                mod_to_activate = self.ranking_active_dependent_modules
                if not self.deactivate():
                    return False

            # reload module
            if not self._load(reload=True):
                return False

            # re-activate all modules that have been active before
            if was_active:
                if mod_to_activate:
                    for module_ref in mod_to_activate:
                        module = module_ref()
                        if module is None:
                            continue
                        if not module.activate():
                            return False
                else:
                    if not self.activate():
                        return False
            return True

    def _load(self, reload=False):
        """
        """
        with self._lock:
            # Do nothing if already loaded and not reload
            if self.is_loaded and not reload:
                return True

            if self.is_remote:
                try:
                    self._instance = get_remote_module_instance(self._remote_url,
                                                                certfile=self._remote_certfile,
                                                                keyfile=self._remote_keyfile)
                except:
                    logger.exception(
                        f'Error during initialization of remote {self._base} module '
                        f'{self._remote_url}'
                    )
                    self._instance = None
                    return False
            else:
                # Try qudi module import
                try:
                    mod = importlib.import_module(f'{self._base}.{self._module}')
                    importlib.reload(mod)
                except ImportError:
                    logger.exception(f'Error during import of module "{self._base}.{self._module}"')
                    return False

                # Try getting qudi module class from imported module
                try:
                    mod_class = getattr(mod, self._class)
                except:
                    logger.exception(f'Error getting module class "{self._class}" from module '
                                     f'"{self._base}.{self._module}"')
                    return False

                # Check if imported class is a valid qudi module class
                if not issubclass(mod_class, Base):
                    logger.error(f'Qudi module main class "{mod_class}" must be subclass of '
                                 f'core.module.Base')
                    return False

                # Try to instantiate the imported qudi module class
                try:
                    self._instance = mod_class(qudi_main_weakref=self._qudi_main_ref,
                                               name=self._name,
                                               config=self._options)
                except:
                    logger.exception(f'Error during initialization of qudi module '
                                     f'"{self._class}.{self._base}.{self._module}"')
                    self._instance = None
                    return False
            self.__last_state = self.state
            self.sigStateChanged.emit(self._base, self._name, self.__last_state)
            return True

    def _connect(self):
        with self._lock:
            # Check if module has already been loaded/instantiated
            if not self.is_loaded:
                logger.error(f'Connection failed. No module instance found or module '
                             f'"{self._base}.{self._name}".')
                return False

            # Get Connector meta objects for this module
            conn_objects = getattr(self._instance, '_module_meta', dict()).get('connectors', dict())
            conn_names = set(conn.name for conn in conn_objects.values())
            mandatory_conn = set(conn.name for conn in conn_objects.values() if not conn.optional)
            configured_conn = set(self._connect_cfg)
            if not configured_conn.issubset(conn_names):
                logger.error(
                    f'Connection of module "{self._base}.{self._name}" failed. Encountered '
                    f'mismatch of connectors in configuration {configured_conn} and module '
                    f'Connector meta objects {conn_names}.'
                )
                return False
            if not mandatory_conn.issubset(configured_conn):
                logger.error(
                    f'Connection of module "{self._base}.{self._name}" failed. Not all mandatory '
                    f'connectors are specified in config.\n'
                    f'Mandatory connectors are: {mandatory_conn}'
                )
                return False

            # Iterate through module connectors and try to connect them
            try:
                for connector in conn_objects.values():
                    if connector.name not in configured_conn:
                        continue
                    for module_ref in self._required_modules:
                        if module_ref().name == self._connect_cfg[connector.name]:
                            break
                    connector.connect(module_ref().instance)
            except:
                logger.exception(f'Something went wrong while trying to connect module '
                                 f'"{self._base}.{self._name}".')
                return False
            return True

    def _disconnect(self):
        with self._lock:
            try:
                conn_obj = getattr(self._instance, '_module_meta', dict()).get('connectors', dict())
                for connector in conn_obj.values():
                    connector.disconnect()
            except:
                logger.exception(f'Something went wrong while trying to disconnect module '
                                 f'"{self._base}.{self._name}".')
                return False
            return True
