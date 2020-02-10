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

Derived form ACQ4:
Copyright 2010  Luke Campagnola
Originally distributed under MIT/X11 license. See documentation/MITLicense.txt for more infomation.
"""

import logging
import os
import sys
import importlib
import copy
from weakref import WeakValueDictionary, ref

from qtpy import QtCore
from . import config

from .util.paths import get_main_dir
from .util.mutex import Mutex, RecursiveMutex   # provides access serialization between threads
from .logger import register_exception_handler
from .threadmanager import ThreadManager
# try to import RemoteObjectManager. Might fail if rpyc is not installed.
try:
    from .remote import RemoteObjectManager
except ImportError:
    RemoteObjectManager = None
from .module import Base
from .gui.popup_dialog import PopUpMessage

logger = logging.getLogger(__name__)


class ManagedModulesSingleton(QtCore.QObject):
    """
    """
    __instance = None
    _lock = RecursiveMutex()

    _manager = None
    _modules = dict()

    sigModuleStateChanged = QtCore.Signal(str, str, str)

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls.__instance is None:
                cls.__instance = super().__new__(cls, *args, **kwargs)
                cls._modules = dict()
                cls._manager = lambda: None
            return cls.__instance

    def __init__(self, *args, **kwargs):
        with self._lock:
            if self.__instance is None:
                super().__init__(*args, **kwargs)

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
                self.remove_module(module_name, ignore_missing=True)

    def get(self, *args):
        with self._lock:
            return self._modules.get(*args)

    def pop(self, *args):
        with self._lock:
            obj = self._modules.get(*args)
            self.remove_module(args[0], ignore_missing=True)
            return obj

    def update(self, *args, **kwargs):
        if len(args) > 1:
            raise TypeError('update expected at most 1 arguments, got {0:d}'.format(len(args)))
        with self._lock:
            if args:
                if isinstance(args[0], dict):
                    for module in args[0].values():
                        self.add_module(module, allow_overwrite=True)
                else:
                    for _, module in args[0]:
                        self.add_module(module, allow_overwrite=True)
            for module in kwargs.values():
                self.add_module(module, allow_overwrite=True)

    def remove_module(self, module_name, ignore_missing=False):
        with self._lock:
            if module_name not in self._modules:
                if not ignore_missing:
                    logger.error('No module with name "{0}" registered. Unable to remove module.'
                                 ''.format(module_name))
                return
            self._modules[module_name].deactivate()
            self._modules[module_name].sigStateChanged.disconnect(self.sigModuleStateChanged)
            del self._modules[module_name]
            self.link_module_dependencies()

    def add_module(self, module, allow_overwrite=False):
        with self._lock:
            if not isinstance(module, ManagedModule):
                raise TypeError('add_module expects a ManagedModule instance.')
            if allow_overwrite:
                self.remove_module(module.name, ignore_missing=True)
            elif module.name in self._modules:
                logger.error(
                    'Module with name "{0}" already registered. Unable to add module of same name.')
                return
            self._modules[module.name] = module
            self.link_module_dependencies()

    def link_module_dependencies(self):
        with self._lock:
            # ToDo: implement
            pass


class ManagedModule(QtCore.QObject):
    """ Object representing a qudi module (gui, logic or hardware) to be managed by the qudi Manager
     object. Contains status properties and handles initialization, state transitions and
     connection of the module.
    """
    # ToDO: Properly handle (i.e. test) optional connectors

    # ToDo: Handle remote connection/(de)activation
    sigStateChanged = QtCore.Signal(str, str, str)

    _manager = None
    _lock = RecursiveMutex()
    __managed_modules = WeakValueDictionary()

    def __init__(self, name, base, configuration):
        if not name or name in ManagedModule.__managed_modules:
            raise NameError('Module name must be a unique and non-empty string.')
        if base not in ('gui', 'logic', 'hardware'):
            raise NameError('Module base must be one of ("gui", "logic", "hardware").')
        if 'module.Class' not in configuration:
            raise KeyError('Mandatory config entry "module.Class" not found in config for module '
                           '"{0}".'.format(name))

        super().__init__()

        self._name = name  # Each qudi module needs a unique string identifier
        self._base = base  # Remember qudi module base
        self._instance = None  # Store the module instance later on
        self._reverse_dependencies = set()

        # Sort out configuration dict
        cfg = copy.deepcopy(configuration)
        # Extract module and class name
        self._module, self._class = cfg.pop('module.Class').rsplit('.', 1)
        # Remember connections by name
        self._connect_cfg = cfg.pop('connect', dict())
        # The rest are config options
        self._options = cfg
        # Store weak reference to new instance
        ManagedModule.__managed_modules[name] = self
        return

    def __call__(self):
        return self.instance

    @classmethod
    def set_manager(cls, manager):
        with cls._lock:
            if not isinstance(manager, Manager):
                raise TypeError('ManagedModule.set_manager is expecting a Manager object instance.')
            if cls._manager is not None and cls._manager() is not None:
                raise Exception('Can not set new manager reference in ManagedModule class. Old '
                                'manager reference is still valid (something is preventing it from '
                                'garbage collection).')
            cls._manager = ref(manager)

    @classmethod
    def build_reverse_dependencies(cls):
        with cls._lock:
            # This should ensure the weak references are not garbage collected during iteration
            module_list = [mod_ref() for mod_ref in cls.__managed_modules.itervaluerefs()]
            for module in module_list:
                if module is None:
                    continue
                mod_name = module.name
                reverse_deps = set()
                for inspect_module in module_list:
                    if (inspect_module is module) or (inspect_module is None):
                        continue
                    if mod_name in inspect_module.dependencies:
                        reverse_deps.add(inspect_module.name)
                module.reverse_dependencies = reverse_deps

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
        with ManagedModule._lock:
            return self._instance

    @property
    def status_file_path(self):
        with ManagedModule._lock:
            if self._instance is not None:
                return self._instance.module_status_file_path
            return None

    @property
    def is_loaded(self):
        with ManagedModule._lock:
            return self._instance is not None

    @property
    def is_active(self):
        with ManagedModule._lock:
            return self._instance is not None and self._instance.module_state() != 'deactivated'

    @property
    def is_busy(self):
        with ManagedModule._lock:
            return self.is_active and self._instance.module_state() != 'idle'

    @property
    def state(self):
        with ManagedModule._lock:
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
    def dependencies(self):
        return set(self._connect_cfg.values())

    @property
    def reverse_dependencies(self):
        with ManagedModule._lock:
            return self._reverse_dependencies.copy()

    @reverse_dependencies.setter
    def reverse_dependencies(self, dependency_set):
        with ManagedModule._lock:
            self._reverse_dependencies = set(dependency_set)

    @property
    def ranking_active_dependent_modules(self):
        with ManagedModule._lock:
            active_dependent_modules = set()
            for mod_name in self._reverse_dependencies:
                dep_module = ManagedModule.__managed_modules.get(mod_name, None)
                if dep_module is None:
                    continue
                if dep_module.is_active:
                    active_modules = dep_module.ranking_active_dependent_modules
                    if active_modules:
                        active_dependent_modules.update(active_modules)
                    else:
                        active_dependent_modules.add(mod_name)
            return active_dependent_modules

    def reload(self):
        with ManagedModule._lock:
            # Deactivate if active
            was_active = self.is_active
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
                    for mod_name in mod_to_activate:
                        module = ManagedModule.__managed_modules.get(mod_name, None)
                        if module is None:
                            continue
                        if not module.activate():
                            return False
                else:
                    if not self.activate():
                        return False
            return True

    def activate(self):
        print('starting to activate:', self._name)
        with ManagedModule._lock:
            if self.is_active:
                return True

            if not self.is_loaded:
                if not self._load():
                    return False

            # Recursive activation of dependencies. Map dependency modules to connector names.
            connect_dict = dict()
            for connector_name, mod_name in self._connect_cfg.items():
                dep_module = ManagedModule.__managed_modules.get(mod_name, None)
                if not dep_module.activate():
                    return False
                connect_dict[connector_name] = dep_module
            if not self._connect(connect_dict):
                return False

            # check if manager reference is set
            manager = None if self._manager is None else self._manager()
            if manager is None:
                logger.error('Unable to activate ManagedModule instances. Weak reference to Manager'
                             ' instance is not set or has been garbage collected.')
                return False

            print('activating:', self._name)
            try:
                if self._instance.is_module_threaded:
                    thread_name = 'mod-{0}-{1}'.format(self._base, self._name)
                    thread = manager.thread_manager.get_new_thread(thread_name)
                    self._instance.moveToThread(thread)
                    thread.start()
                    QtCore.QMetaObject.invokeMethod(self._instance.module_state,
                                                    'activate',
                                                    QtCore.Qt.BlockingQueuedConnection)
                    # Cleanup if activation was not successful
                    if not self.is_active:
                        QtCore.QMetaObject.invokeMethod(self._instance,
                                                        'move_to_manager_thread',
                                                        QtCore.Qt.BlockingQueuedConnection)
                        manager.thread_manager.quit_thread(thread_name)
                        manager.thread_manager.join_thread(thread_name)
                else:
                    self._instance.module_state.activate()
                QtCore.QCoreApplication.instance().processEvents()
                if not self.is_active:
                    return False
            except:
                logger.exception('Massive error during activation of module "{0}.{1}"'
                                 ''.format(self._base, self._name))
                return False
            self.sigStateChanged.emit(self._base, self._name, self.state)
            return True

    def deactivate(self):
        print('starting to deactivate:', self._name)
        with ManagedModule._lock:
            if not self.is_active:
                return True

            success = True  # error flag to return

            # Recursively deactivate dependent modules
            for mod_name in self._reverse_dependencies:
                dep_module = ManagedModule.__managed_modules.get(mod_name, None)
                if dep_module is None:
                    continue
                success = success and dep_module.deactivate()

            # check if manager reference is set
            manager = None if self._manager is None else self._manager()
            if manager is None:
                logger.error('Unable to properly deactivate ManagedModule instances. Weak reference'
                             ' to Manager instance is not set or has been garbage collected. Thread'
                             ' management can not take place.')
                success = False

            print('deactivating:', self._name)
            # Actual deactivation of this module
            try:
                if self._instance.is_module_threaded:
                    thread_name = self._instance.thread().objectName()
                    QtCore.QMetaObject.invokeMethod(self._instance.module_state,
                                                    'deactivate',
                                                    QtCore.Qt.BlockingQueuedConnection)
                    QtCore.QMetaObject.invokeMethod(self._instance,
                                                    'move_to_manager_thread',
                                                    QtCore.Qt.BlockingQueuedConnection)
                    if manager is not None:
                        manager.thread_manager.quit_thread(thread_name)
                        manager.thread_manager.join_thread(thread_name)
                else:
                    self._instance.module_state.deactivate()
                QtCore.QCoreApplication.instance().processEvents()
                success = success and not self.is_active
            except:
                logger.exception('Massive error during deactivation of module "{0}.{1}"'
                                 ''.format(self._base, self._name))
                success = False
            success = success and self._disconnect()
            self.sigStateChanged.emit(self._base, self._name, self.state)
            return success

    def remove(self):
        """Explicitly remove this ManagedModule instance from internal bookkeeping not relying on
        garbage collection.
        This process is irreversible and renders this instance non-functional.
        """
        with ManagedModule._lock:
            if self._name in ManagedModule.__managed_modules:
                del ManagedModule.__managed_modules[self._name]

    def _load(self, reload=False):
        """
        """
        with ManagedModule._lock:
            # Do nothing if already loaded and not reload
            if self.is_loaded and not reload:
                return True

            # check if manager reference is set
            manager = None if self._manager is None else self._manager()
            if manager is None:
                logger.error('Unable to load ManagedModule instances. Weak reference to Manager '
                             'instance is not set or has been garbage collected.')
                return False

            try:
                mod = importlib.import_module('{0}.{1}'.format(self._base, self._module))
                importlib.reload(mod)
            except ImportError:
                logger.exception(
                    'Error during import of module "{0}.{1}"'.format(self._base, self._module))
                return False
            try:
                mod_class = getattr(mod, self._class)
            except:
                logger.exception('Error getting module class "{0}" from module "{1}.{2}"'
                                 ''.format(self._class, self._base, self._module))
                return False
            if not issubclass(mod_class, Base):
                logger.error('Qudi module main class must be subclass of core.module.Base')
                return False
            try:
                self._instance = mod_class(manager=manager,
                                           name=self._name,
                                           config=self._options)
            except:
                logger.exception('Error during initialization of qudi module "{0}.{1}.{2}"'
                                 ''.format(self._class, self._base, self._module))
                self._instance = None
                return False
            return True

    def _connect(self, connect_dict):
        with ManagedModule._lock:
            # Sanity checking
            if not self.is_loaded:
                print('Connection failed. No module instance found.')
                return False
            module_connectors = self._instance._module_meta['connectors']
            mandatory_connector_names = set(
                conn.name for conn in module_connectors.values() if not conn.optional)
            if not mandatory_connector_names.issubset(connect_dict):
                logger.error('Connection of module "{0}.{1}" failed. Not all mandatory connectors '
                             'are specified in config.\nMandatory connectors are: {2}'
                             ''.format(self._base, self._name, mandatory_connector_names))
                return False

            # Iterate through module connectors and try to connect them
            try:
                for connector in module_connectors.values():
                    if connector.name not in connect_dict:
                        continue
                    connector.connect(connect_dict[connector.name].instance)
            except:
                logger.exception('Something went wrong while trying to connect module "{0}.{1}".'
                                 ''.format(self._base, self._name))
                return False
            return True

    def _disconnect(self):
        with ManagedModule._lock:
            try:
                for connector in self._instance._module_meta['connectors'].values():
                    connector.disconnect()
            except:
                logger.exception('Something went wrong while trying to disconnect module "{0}.{1}".'
                                 ''.format(self._base, self._name))
                return False
            return True


# class ManagedModule(QtCore.QObject):
#     """ Object representing a qudi module (gui, logic or hardware) to be managed by the qudi Manager
#      object. Contains status properties and handles initialization, state transitions and
#      connection of the module.
#     """
#     # ToDO: Each ManagedModule instance should hold references instead of names for each dependent
#     #  and required module. Take special care with gc and weakrefs to collect obsolete qudi module
#     #  class instances.
#
#     # ToDO: Properly handle (i.e. test) optional connectors
#
#     # ToDo: Handle remote connection/(de)activation
#     sigStateChanged = QtCore.Signal(str, str, str)
#
#     _manager = None
#     _lock = RecursiveMutex()
#     __managed_modules = WeakValueDictionary()
#
#     def __init__(self, name, base, configuration):
#         if not name or name in ManagedModule.__managed_modules:
#             raise NameError('Module name must be a unique and non-empty string.')
#         if base not in ('gui', 'logic', 'hardware'):
#             raise NameError('Module base must be one of ("gui", "logic", "hardware").')
#         if 'module.Class' not in configuration:
#             raise KeyError('Mandatory config entry "module.Class" not found in config for module '
#                            '"{0}".'.format(name))
#
#         super().__init__()
#
#         self._name = name  # Each qudi module needs a unique string identifier
#         self._base = base  # Remember qudi module base
#         self._instance = None  # Store the module instance later on
#         self._reverse_dependencies = set()
#
#         # Sort out configuration dict
#         cfg = copy.deepcopy(configuration)
#         # Extract module and class name
#         self._module, self._class = cfg.pop('module.Class').rsplit('.', 1)
#         # Remember connections by name
#         self._connect_cfg = cfg.pop('connect', dict())
#         # The rest are config options
#         self._options = cfg
#         # Store weak reference to new instance
#         ManagedModule.__managed_modules[name] = self
#         return
#
#     def __call__(self):
#         return self.instance
#
#     @classmethod
#     def set_manager(cls, manager):
#         with cls._lock:
#             if not isinstance(manager, Manager):
#                 raise TypeError('ManagedModule.set_manager is expecting a Manager object instance.')
#             if cls._manager is not None and cls._manager() is not None:
#                 raise Exception('Can not set new manager reference in ManagedModule class. Old '
#                                 'manager reference is still valid (something is preventing it from '
#                                 'garbage collection).')
#             cls._manager = ref(manager)
#
#     @classmethod
#     def build_reverse_dependencies(cls):
#         with cls._lock:
#             # This should ensure the weak references are not garbage collected during iteration
#             module_list = [mod_ref() for mod_ref in cls.__managed_modules.itervaluerefs()]
#             for module in module_list:
#                 if module is None:
#                     continue
#                 mod_name = module.name
#                 reverse_deps = set()
#                 for inspect_module in module_list:
#                     if (inspect_module is module) or (inspect_module is None):
#                         continue
#                     if mod_name in inspect_module.dependencies:
#                         reverse_deps.add(inspect_module.name)
#                 module.reverse_dependencies = reverse_deps
#
#     @property
#     def name(self):
#         return self._name
#
#     @property
#     def module_base(self):
#         return self._base
#
#     @property
#     def class_name(self):
#         return self._class
#
#     @property
#     def module_name(self):
#         return self._module
#
#     @property
#     def options(self):
#         return copy.deepcopy(self._options)
#
#     @property
#     def instance(self):
#         with ManagedModule._lock:
#             return self._instance
#
#     @property
#     def status_file_path(self):
#         with ManagedModule._lock:
#             if self._instance is not None:
#                 return self._instance.module_status_file_path
#             return None
#
#     @property
#     def is_loaded(self):
#         with ManagedModule._lock:
#             return self._instance is not None
#
#     @property
#     def is_active(self):
#         with ManagedModule._lock:
#             return self._instance is not None and self._instance.module_state() != 'deactivated'
#
#     @property
#     def is_busy(self):
#         with ManagedModule._lock:
#             return self.is_active and self._instance.module_state() != 'idle'
#
#     @property
#     def state(self):
#         with ManagedModule._lock:
#             if self._instance is None:
#                 return 'not loaded'
#             try:
#                 return self._instance.module_state()
#             except:
#                 return 'BROKEN'
#
#     @property
#     def connection_cfg(self):
#         return self._connect_cfg.copy()
#
#     @property
#     def dependencies(self):
#         return set(self._connect_cfg.values())
#
#     @property
#     def reverse_dependencies(self):
#         with ManagedModule._lock:
#             return self._reverse_dependencies.copy()
#
#     @reverse_dependencies.setter
#     def reverse_dependencies(self, dependency_set):
#         with ManagedModule._lock:
#             self._reverse_dependencies = set(dependency_set)
#
#     @property
#     def ranking_active_dependent_modules(self):
#         with ManagedModule._lock:
#             active_dependent_modules = set()
#             for mod_name in self._reverse_dependencies:
#                 dep_module = ManagedModule.__managed_modules.get(mod_name, None)
#                 if dep_module is None:
#                     continue
#                 if dep_module.is_active:
#                     active_modules = dep_module.ranking_active_dependent_modules
#                     if active_modules:
#                         active_dependent_modules.update(active_modules)
#                     else:
#                         active_dependent_modules.add(mod_name)
#             return active_dependent_modules
#
#     def reload(self):
#         with ManagedModule._lock:
#             # Deactivate if active
#             was_active = self.is_active
#             if was_active:
#                 mod_to_activate = self.ranking_active_dependent_modules
#                 if not self.deactivate():
#                     return False
#
#             # reload module
#             if not self._load(reload=True):
#                 return False
#
#             # re-activate all modules that have been active before
#             if was_active:
#                 if mod_to_activate:
#                     for mod_name in mod_to_activate:
#                         module = ManagedModule.__managed_modules.get(mod_name, None)
#                         if module is None:
#                             continue
#                         if not module.activate():
#                             return False
#                 else:
#                     if not self.activate():
#                         return False
#             return True
#
#     def activate(self):
#         print('starting to activate:', self._name)
#         with ManagedModule._lock:
#             if self.is_active:
#                 return True
#
#             if not self.is_loaded:
#                 if not self._load():
#                     return False
#
#             # Recursive activation of dependencies. Map dependency modules to connector names.
#             connect_dict = dict()
#             for connector_name, mod_name in self._connect_cfg.items():
#                 dep_module = ManagedModule.__managed_modules.get(mod_name, None)
#                 if not dep_module.activate():
#                     return False
#                 connect_dict[connector_name] = dep_module
#             if not self._connect(connect_dict):
#                 return False
#
#             # check if manager reference is set
#             manager = None if self._manager is None else self._manager()
#             if manager is None:
#                 logger.error('Unable to activate ManagedModule instances. Weak reference to Manager'
#                              ' instance is not set or has been garbage collected.')
#                 return False
#
#             print('activating:', self._name)
#             try:
#                 if self._instance.is_module_threaded:
#                     thread_name = 'mod-{0}-{1}'.format(self._base, self._name)
#                     thread = manager.thread_manager.get_new_thread(thread_name)
#                     self._instance.moveToThread(thread)
#                     thread.start()
#                     QtCore.QMetaObject.invokeMethod(self._instance.module_state,
#                                                     'activate',
#                                                     QtCore.Qt.BlockingQueuedConnection)
#                     # Cleanup if activation was not successful
#                     if not self.is_active:
#                         QtCore.QMetaObject.invokeMethod(self._instance,
#                                                         'move_to_manager_thread',
#                                                         QtCore.Qt.BlockingQueuedConnection)
#                         manager.thread_manager.quit_thread(thread_name)
#                         manager.thread_manager.join_thread(thread_name)
#                 else:
#                     self._instance.module_state.activate()
#                 QtCore.QCoreApplication.instance().processEvents()
#                 if not self.is_active:
#                     return False
#             except:
#                 logger.exception('Massive error during activation of module "{0}.{1}"'
#                                  ''.format(self._base, self._name))
#                 return False
#             self.__emit_state_change()
#             return True
#
#     def deactivate(self):
#         print('starting to deactivate:', self._name)
#         with ManagedModule._lock:
#             if not self.is_active:
#                 return True
#
#             success = True  # error flag to return
#
#             # Recursively deactivate dependent modules
#             for mod_name in self._reverse_dependencies:
#                 dep_module = ManagedModule.__managed_modules.get(mod_name, None)
#                 if dep_module is None:
#                     continue
#                 success = success and dep_module.deactivate()
#
#             # check if manager reference is set
#             manager = None if self._manager is None else self._manager()
#             if manager is None:
#                 logger.error('Unable to properly deactivate ManagedModule instances. Weak reference'
#                              ' to Manager instance is not set or has been garbage collected. Thread'
#                              ' management can not take place.')
#                 success = False
#
#             print('deactivating:', self._name)
#             # Actual deactivation of this module
#             try:
#                 if self._instance.is_module_threaded:
#                     thread_name = self._instance.thread().objectName()
#                     QtCore.QMetaObject.invokeMethod(self._instance.module_state,
#                                                     'deactivate',
#                                                     QtCore.Qt.BlockingQueuedConnection)
#                     QtCore.QMetaObject.invokeMethod(self._instance,
#                                                     'move_to_manager_thread',
#                                                     QtCore.Qt.BlockingQueuedConnection)
#                     if manager is not None:
#                         manager.thread_manager.quit_thread(thread_name)
#                         manager.thread_manager.join_thread(thread_name)
#                 else:
#                     self._instance.module_state.deactivate()
#                 QtCore.QCoreApplication.instance().processEvents()
#                 success = success and not self.is_active
#             except:
#                 logger.exception('Massive error during deactivation of module "{0}.{1}"'
#                                  ''.format(self._base, self._name))
#                 success = False
#             success = success and self._disconnect()
#             self.__emit_state_change()
#             return success
#
#     def remove(self):
#         """Explicitly remove this ManagedModule instance from internal bookkeeping not relying on
#         garbage collection.
#         This process is irreversible and renders this instance non-functional.
#         """
#         with ManagedModule._lock:
#             if self._name in ManagedModule.__managed_modules:
#                 del ManagedModule.__managed_modules[self._name]
#
#     def _load(self, reload=False):
#         """
#         """
#         with ManagedModule._lock:
#             # Do nothing if already loaded and not reload
#             if self.is_loaded and not reload:
#                 return True
#
#             # check if manager reference is set
#             manager = None if self._manager is None else self._manager()
#             if manager is None:
#                 logger.error('Unable to load ManagedModule instances. Weak reference to Manager '
#                              'instance is not set or has been garbage collected.')
#                 return False
#
#             try:
#                 mod = importlib.import_module('{0}.{1}'.format(self._base, self._module))
#                 importlib.reload(mod)
#             except ImportError:
#                 logger.exception(
#                     'Error during import of module "{0}.{1}"'.format(self._base, self._module))
#                 return False
#             try:
#                 mod_class = getattr(mod, self._class)
#             except:
#                 logger.exception('Error getting module class "{0}" from module "{1}.{2}"'
#                                  ''.format(self._class, self._base, self._module))
#                 return False
#             if not issubclass(mod_class, Base):
#                 logger.error('Qudi module main class must be subclass of core.module.Base')
#                 return False
#             try:
#                 self._instance = mod_class(manager=manager,
#                                            name=self._name,
#                                            config=self._options)
#             except:
#                 logger.exception('Error during initialization of qudi module "{0}.{1}.{2}"'
#                                  ''.format(self._class, self._base, self._module))
#                 self._instance = None
#                 return False
#             return True
#
#     def _connect(self, connect_dict):
#         with ManagedModule._lock:
#             # Sanity checking
#             if not self.is_loaded:
#                 print('Connection failed. No module instance found.')
#                 return False
#             module_connectors = self._instance._module_meta['connectors']
#             mandatory_connector_names = set(
#                 conn.name for conn in module_connectors.values() if not conn.optional)
#             if not mandatory_connector_names.issubset(connect_dict):
#                 logger.error('Connection of module "{0}.{1}" failed. Not all mandatory connectors '
#                              'are specified in config.\nMandatory connectors are: {2}'
#                              ''.format(self._base, self._name, mandatory_connector_names))
#                 return False
#
#             # Iterate through module connectors and try to connect them
#             try:
#                 for connector in module_connectors.values():
#                     if connector.name not in connect_dict:
#                         continue
#                     connector.connect(connect_dict[connector.name].instance)
#             except:
#                 logger.exception('Something went wrong while trying to connect module "{0}.{1}".'
#                                  ''.format(self._base, self._name))
#                 return False
#             return True
#
#     def _disconnect(self):
#         with ManagedModule._lock:
#             try:
#                 for connector in self._instance._module_meta['connectors'].values():
#                     connector.disconnect()
#             except:
#                 logger.exception('Something went wrong while trying to disconnect module "{0}.{1}".'
#                                  ''.format(self._base, self._name))
#                 return False
#             return True
#
#     def __emit_state_change(self):
#         self.sigStateChanged.emit(self._base, self._name, self.state)


class Manager(QtCore.QObject):
    """The Manager object is responsible for:
      - Loading/configuring device modules and storing their handles
      - Providing unified timestamps
      - Making sure all devices/modules are properly shut down at the end of the program

    @signal sigConfigChanged: the configuration has changed, please reread your configuration
    @signal sigModulesChanged: the available modules have changed
    @signal (str, str, str) sigModuleStateChanged: the module state has changed (base, name, state)
    @signal sigManagerQuit: the manager is quitting
    @signal sigShowManager: show whatever part of the GUI is important
    """

    # Signal declarations for Qt
    sigConfigChanged = QtCore.Signal(dict)
    sigModulesChanged = QtCore.Signal(dict)
    sigModuleStateChanged = QtCore.Signal(str, str, str)
    sigManagerQuit = QtCore.Signal(bool)
    sigShutdownAcknowledge = QtCore.Signal(bool, bool)
    sigShowManager = QtCore.Signal()

    def __init__(self, args, **kwargs):
        """
        Constructor for Qudi main management class

        @param args: argparse command line arguments
        """
        # Initialize parent class QObject
        super().__init__()

        self.lock = Mutex(recursive=True)  # used for keeping some basic methods thread-safe
        self._has_gui = not args.no_gui  # flag indicating GUI or command line mode

        self.remote_manager = None  # Reference to RemoteObjectManager instance if possible
        self.task_runner = None  # Task runner reference

        self.managed_modules = dict()  # container for all qudi modules (as defined by config)

        # Known global config parameters
        self._startup_modules = list()
        self._module_server = None
        self._stylesheet = None
        self._extension_paths = list()
        self._globals = dict()

        # Register exception handler
        register_exception_handler(self)

        # Thread management
        try:
            self.thread_manager = ThreadManager()
            logger.debug('Main thread is {0}'.format(QtCore.QThread.currentThread()))
        except:
            logger.error('Error while instantiating thread manager.')
            raise

        # Find config file path
        self.config_file_path = args.config if os.path.isfile(
            args.config) else self.find_default_config_file()
        # Process configuration file
        try:
            print('============= Starting Manager configuration from {0} ============='
                  ''.format(self.config_file_path))
            logger.info('Starting Manager configuration from {0}'.format(self.config_file_path))

            self.__load_and_process_config()

            print("\n============= Manager configuration complete =================\n")
            logger.info('Manager configuration complete.')
        except:
            logger.error('Error encountered while processing config file.')
            raise

        # check first if remote support is enabled and if so create RemoteObjectManager
        if RemoteObjectManager is None:
            logger.warning('Remote modules disabled. Rpyc not installed.')
        else:
            self.remote_manager = RemoteObjectManager(self)
            # Create remote module server if specified in config file
            if self._module_server:
                # new style
                try:
                    server_address = self._module_server.get('address', 'localhost')
                    server_port = self._module_server.get('port', 12345)
                    certfile = self._module_server.get('certfile', None)
                    keyfile = self._module_server.get('keyfile', None)
                    self.remote_manager.createServer(server_address, server_port, certfile, keyfile)
                    # successfully started remote server
                    logger.info('Started server rpyc://{0}:{1}'.format(server_address, server_port))
                except:
                    logger.exception('Rpyc server could not be started.')

        # walk through the list of modules to be loaded on startup and load them if appropriate
        for module_name in self._startup_modules:
            if module_name not in self.managed_modules:
                logger.error('Startup module "{0}" not found in configuration'.format(module_name))
            else:
                self.start_module(module_name)

        # Gui setup if we have gui
        if self._has_gui:
            try:
                from .gui.gui import Gui
                self.gui = Gui(artwork_dir=os.path.join(get_main_dir(), 'artwork'))
                self.gui.system_tray_icon.quitAction.triggered.connect(self.quit)
                self.gui.system_tray_icon.managerAction.triggered.connect(
                    self.sigShowManager)
                self.gui.set_theme('qudiTheme')
            except:
                logger.error('Error during GUI setup.')
                raise
            if self._stylesheet:
                style_path = os.path.join(get_main_dir(),
                                          'artwork',
                                          'styles',
                                          'application',
                                          self._stylesheet)
                if os.path.isfile(style_path):
                    self.gui.set_style_sheet(style_path)
                else:
                    logger.warning('Stylesheet not found at "{0}"'.format(style_path))
                    self._stylesheet = None

        logger.info('qudi started.')
        return

    @property
    def default_config_dir(self):
        return os.path.join(get_main_dir(), 'config')

    @property
    def config_dir(self):
        return os.path.dirname(self.config_file_path)

    @property
    def has_gui(self):
        return self._has_gui

    @property
    def has_remote_server(self):
        return self.remote_manager is not None

    @property
    def startup_modules(self):
        return self._startup_modules.copy()

    @property
    def global_config(self):
        return copy.deepcopy(self._globals)

    @property
    def config_dict(self):
        with self.lock:
            config_tree = {'global': dict(), 'hardware': dict(), 'logic': dict(), 'gui': dict()}

            # Add global variables
            config_tree['global'].update(self.global_config)
            if self._startup_modules:
                config_tree['global']['startup'] = self.startup_modules
            if self._module_server:
                config_tree['global']['module_server'] = self._module_server.copy()
            if self._stylesheet:
                config_tree['global']['stylesheet'] = self._stylesheet
            if self._extension_paths:
                config_tree['global']['extensions'] = self._extension_paths.copy()

            # Add module declarations
            for module_name, module in self.managed_modules.items():
                mod_dict = dict()
                mod_dict['module.Class'] = '{0}.{1}'.format(module.module_name, module.class_name)
                mod_dict.update(module.options)
                mod_dict['connect'] = module.connection_cfg
                config_tree[module.module_base][module_name] = mod_dict
            return config_tree

    @property
    def configured_modules(self):
        return self.managed_modules.copy()

    @property
    def active_modules(self):
        return tuple(mod_name for mod_name, mod in self.managed_modules.items() if mod.is_active)

    @property
    def hardware_module_states(self):
        return {name: m.state for name, m in self.managed_modules.items() if
                m.module_base == 'hardware'}

    @property
    def logic_module_states(self):
        return {name: m.state for name, m in self.managed_modules.items() if
                m.module_base == 'logic'}

    @property
    def gui_module_states(self):
        return {name: m.state for name, m in self.managed_modules.items() if m.module_base == 'gui'}

    def get_module_instance(self, module_name):
        """Returns the qudi module class instance associated with module_name.

        @param module_name: The module name to get the class instance for
        @return: Qudi module class instance
        """
        if not self.is_module_configured(module_name):
            logger.error('No module by the name "{0}" configured. Unable to return module instance.'
                         ''.format(module_name))
            return None
        return self.managed_modules[module_name].instance

    def find_default_config_file(self):
        """
        Search all the default locations to find a suitable configuration file.

        @return str: path to configuration file
        """
        # we first look for config/load.cfg which can point to another config file using the
        # "configfile" key
        load_config_file = os.path.join(self.default_config_dir, 'load.cfg')
        if os.path.isfile(load_config_file):
            logger.info('load.cfg file found at {0}'.format(load_config_file))
            try:
                config_dict = config.load(load_config_file)
                if 'configfile' in config_dict and isinstance(config_dict['configfile'], str):
                    # check if this config file is existing and also try relative filenames
                    config_file = os.path.join(self.default_config_dir, config_dict['configfile'])
                    if os.path.isfile(config_file):
                        return config_file
                    # try absolute filename or relative to pwd
                    if os.path.isfile(config_dict['configfile']):
                        return config_dict['configfile']
                    else:
                        logger.critical('Couldn\'t find config file specified in load.cfg: {0}'
                                        ''.format(config_dict['configfile']))
            except:
                logger.exception('Error while handling load.cfg.')
        # try config/example/custom.cfg if no file has been found so far
        cf = os.path.join(self.default_config_dir, 'example', 'custom.cfg')
        if os.path.isfile(cf):
            return cf
        # try config/example/default.cfg if no file has been found so far
        cf = os.path.join(self.default_config_dir, 'example', 'default.cfg')
        if os.path.isfile(cf):
            return cf
        raise Exception('Could not find any config file.')

    def __load_and_process_config(self):
        # Clean up previous config settings
        for ext_path in self._extension_paths:
            if ext_path in sys.path:
                sys.path.remove(ext_path)
        for module_name, module in self.managed_modules.items():
            module.deactivate()
            module.sigStateChanged.disconnect()
        self.managed_modules = dict()

        # Read config file
        cfg = config.load(self.config_file_path)

        # Extract global/static parameters from config
        if 'global' in cfg:
            self._startup_modules = cfg['global'].pop('startup', list())
            self._module_server = cfg['global'].pop('module_server', None)
            self._stylesheet = cfg['global'].pop('stylesheet', None)
            self._extension_paths = cfg['global'].pop('extensions', list())
            if isinstance(self._extension_paths, str):
                self._extension_paths = [self._extension_paths]
            elif not isinstance(self._extension_paths, list):
                self._extension_paths = list()
                logger.warning(
                    'Global "extensions" configuration is neither str nor list. Ignoring.')
            self._globals = cfg.pop('global', dict())  # The rest

        # Add qudi extension paths to sys.path
        full_path_ext = list()
        for ii, ext_path in enumerate(self._extension_paths):
            # absolute or relative path? Existing?
            if not (os.path.isabs(ext_path) and os.path.isdir(ext_path)):
                # relative path? Try relative to config file dir and relative to main dir
                path = os.path.abspath(os.path.join(self.config_dir, ext_path))
                if not os.path.isdir(path):
                    path = os.path.abspath(os.path.join(get_main_dir(), ext_path))
                    if not os.path.isdir(path):
                        logger.warning('Error while adding qudi extension: Directory "{0}" does'
                                       ' not exist.'.format(ext_path))
                        continue
                ext_path = path
            # check for __init__.py files within extension and issue warning if existing
            for paths, dirs, files in os.walk(ext_path):
                if '__init__.py' in files:
                    logger.warning('Warning: Extension "{0}" contains __init__.py. Expect '
                                   'unexpected behaviour. Hope you know what you are doing.'
                                   ''.format(ext_path))
                    break
            # add directory to sys.path
            logger.info('Adding extension path: {0}'.format(ext_path))
            full_path_ext.append(ext_path)
            sys.path.insert(1 + ii, ext_path)
        self._extension_paths = full_path_ext

        # Extract module declarations from config
        for base in ('gui', 'logic', 'hardware'):
            # Skip module base category if not present in config or empty
            if not cfg.get(base, None):
                continue
            # Create ManagedModule instance for each defined module
            modules_dict = cfg.pop(base)
            for module_name, module_cfg in modules_dict.items():
                try:
                    self.managed_modules[module_name] = ManagedModule(name=module_name,
                                                                      base=base,
                                                                      configuration=module_cfg)
                    self.managed_modules[module_name].sigStateChanged.connect(
                        self.sigModuleStateChanged)
                except:
                    self.managed_modules.pop(module_name, None)
                    logger.exception('Unable to create ManagedModule instance for module '
                                     '"{0}.{1}"'.format(base, module_name))

        # Configure ManagedModule class and build reverse dependencies
        ManagedModule.set_manager(self)
        ManagedModule.build_reverse_dependencies()

        # Check if there is still a part of the config unprocessed
        if cfg:
            logger.warning('Unknown config file sections encountered.\nAllowed sections are: '
                           '{0}\nThe following part will be ignored:\n{1}'
                           ''.format(('global', 'gui', 'logic', 'hardware'), cfg))
        self.sigConfigChanged.emit(self.config_dict)
        self.sigModulesChanged.emit({'gui': self.gui_module_states,
                                     'logic': self.logic_module_states,
                                     'hardware': self.hardware_module_states})

    @QtCore.Slot(str)
    def save_config_to_file(self, file_path):
        """
        Save current configuration to a file.

        @param str file_path: path where the config file should be saved
        """
        file_path = os.path.join(self.config_dir, file_path)
        file_dir = os.path.dirname(file_path)
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        config.save(file_path, self.config_dict)
        logger.info('Saved configuration to {0}'.format(file_path))

    @QtCore.Slot(str, bool)
    def set_load_config(self, file_path, restart=False):
        """
        Set a new config file path and save it to /config/load.cfg.
        Optionally trigger a restart of qudi.

        @param str file_path: path of file to be loaded
        @param bool restart: Flag indicating if a restart of qudi should be triggered after loading
        """
        load_config_path = os.path.join(self.default_config_dir, 'load.cfg')
        if file_path.startswith(self.default_config_dir):
            file_path = os.path.relpath(file_path, self.default_config_dir)
        config.save(load_config_path, {'configfile': file_path})
        logger.info('Set loaded configuration to {0}'.format(file_path))
        if restart:
            logger.info('Restarting qudi after configuration reload.')
            self.restart()

    @QtCore.Slot(str)
    def reload_module_config(self, module_name):
        """Reread the configuration file and re-initialize a specific module

        @param str module_name: name of module the config should be reloaded for
        """
        with self.lock:
            if module_name not in self.managed_modules:
                logger.error('No module configured with name "{0}"'.format(module_name))
                return

            # Load config file and extract module config of interest
            cfg = config.load(self.config_file_path, ignore_missing=True)
            for base in ('hardware', 'logic', 'gui'):
                module_cfg = cfg.get(base, dict()).get(module_name, None)
                if module_cfg is not None:
                    break
            if module_cfg is None:
                logger.error('Module "{0}" not declared in config file. Unable to reload module config.'
                             ''.format(module_name))
                return

            # deactivate module first if needed
            was_active = self.is_module_active(module_name)
            if was_active:
                self.deactivate_module(module_name)

            self.managed_modules[module_name].sigStateChanged.disconnect()
            self.managed_modules[module_name].remove()
            del self.managed_modules[module_name]

            self.managed_modules[module_name] = ManagedModule(name=module_name,
                                                              base=base,
                                                              configuration=module_cfg)
            ManagedModule.build_reverse_dependencies()
            self.managed_modules[module_name].sigStateChanged.connect(self.sigModuleStateChanged)
            if was_active:
                self.activate_module(module_name)
            self.sigConfigChanged.emit(self.config_dict)
            return

    ##################
    # Module loading #
    ##################
    def is_module_configured(self, module_name):
        """Check if module is defined in config and being managed.

        @param str module_name: unique module name to check

        @return bool: module is configured (True) or not (False)
        """
        return module_name in self.managed_modules

    def is_module_active(self, module_name):
        """Returns whether a given module is active.

        @param str module_name: unique module name to check

        @return bool: module is active flag
        """
        if not self.is_module_configured(module_name):
            logger.error('No module by the name "{0}" configured. Unable to poll activation status.'
                         ''.format(module_name))
            return False
        return self.managed_modules[module_name].is_active

    def find_module_base(self, module_name):
        """Find base (hardware, logic or gui) for a given module name.

        @param str module_name: unique module name

        @return str: base name (hardware, logic or gui)
        """
        if self.is_module_configured(module_name):
            return self.managed_modules[module_name].module_base
        raise KeyError(module_name)

    @QtCore.Slot(str)
    def activate_module(self, module_name):
        """Activate the module given in module_name. Does nothing if already active.
        If the module class has not been instantiated so far, do that as well.

        @param str module_name: module which is going to be activated.
        """
        if not self.is_module_configured(module_name):
            logger.error('No module by the name "{0}" configured. Unable to activate module.'
                         ''.format(module_name))
            return

        if self.is_module_active(module_name):
            if self.find_module_base(module_name) == 'gui':
                self.managed_modules[module_name].instance.show()
            return

        logger.info('Activating qudi module "{0}"'.format(module_name))
        if not self.managed_modules[module_name].activate():
            logger.error('Unable to activate qudi module "{0}"'.format(module_name))
        else:
            logger.debug('Activation success of qudi module "{0}"'.format(module_name))

    @QtCore.Slot(str)
    def deactivate_module(self, module_name):
        """Deactivate the module given in module_name. Does nothing if already deactivated.

        @param str module_name: module which is going to be activated.
        """
        if not self.is_module_configured(module_name):
            logger.error('No module by the name "{0}" configured. Unable to deactivate module.'
                         ''.format(module_name))
            return

        if not self.is_module_active(module_name):
            return

        logger.info('Deactivating qudi module "{0}"'.format(module_name))
        if not self.managed_modules[module_name].deactivate():
            logger.error('Unable to deactivate qudi module "{0}"'.format(module_name))
        else:
            logger.debug('Deactivation success of qudi module "{0}"'.format(module_name))

    @QtCore.Slot(str)
    def start_module(self, module_name):
        """Redirects to Manager.activate_module for backwards compatibility.

        @param str module_name: Unique module name as defined in config
        """
        return self.activate_module(module_name)

    @QtCore.Slot(str)
    def stop_module(self, module_name):
        """Redirects to Manager.deactivate_module for backwards compatibility.

        @param str module_name: Unique module name as defined in config
        """
        return self.deactivate_module(module_name)

    @QtCore.Slot(str)
    def restart_module(self, module_name):
        """Restart qudi module

        @param str module_name: Unique module name as defined in config
        """
        if not self.is_module_configured(module_name):
            logger.error('No module by the name "{0}" configured. Unable to restart module.'
                         ''.format(module_name))
            return

        logger.info('Restarting/reloading qudi module "{0}"'.format(module_name))
        if not self.managed_modules[module_name].reload():
            logger.error('Unable to restart/reload qudi module "{0}"'.format(module_name))
        else:
            logger.debug('Restart/reload success of qudi module "{0}"'.format(module_name))

    @QtCore.Slot()
    def start_all_modules(self):
        """Configure, connect and activate all qudi modules from the currently loaded configuration.
        """
        logger.info('Starting all qudi modules...')
        for module_name, module in self.managed_modules.items():
            if not module.activate():
                logger.warning(
                    'Activating module "{0}" failed while loading all modules.'.format(module_name))
        logger.info('Start all qudi modules finished.')
        QtCore.QCoreApplication.processEvents()

    @QtCore.Slot()
    def stop_all_modules(self):
        """Deactivate all qudi modules from the currently loaded configuration.
        """
        logger.info('Stopping all qudi modules...')
        for module_name, module in self.managed_modules.items():
            if not module.deactivate():
                logger.warning('Deactivating module "{0}" failed while loading all modules.'
                               ''.format(module_name))
        logger.info('Stopping all qudi modules finished.')
        QtCore.QCoreApplication.processEvents()

    def get_status_dir(self):
        """Get the directory where the app state is saved, create it if necessary.

        @return str: path of application status directory
        """
        status_dir = os.path.join(self.config_dir, 'app_status')
        if not os.path.isdir(status_dir):
            os.makedirs(status_dir)
        return status_dir

    @QtCore.Slot(str)
    def remove_module_status_file(self, module_name):
        """Removes (if present) the stored status variable file for given module.

        @param str module_name: the unique module name as specified in config
        """
        if not self.is_module_configured(module_name):
            logger.error('No module by the name "{0}" configured. Unable to remove module status '
                         'file.'.format(module_name))
            return

        file_path = self.managed_modules[module_name].status_file_path
        if os.path.isfile(file_path):
            os.remove(file_path)
        return

    @QtCore.Slot()
    def quit(self):
        """ Nicely request that all modules shut down. """
        locked_modules = False
        broken_modules = False
        for module_name, module in self.managed_modules.items():
            try:
                if module.is_busy:
                    locked_modules = True
            except:
                broken_modules = True
            if broken_modules and locked_modules:
                break

        if locked_modules:
            if self._has_gui:
                self.sigShutdownAcknowledge.emit(locked_modules, broken_modules)
            else:
                # FIXME: console prompt here
                self.force_quit()
        else:
            self.force_quit()

    @QtCore.Slot()
    def force_quit(self):
        """ Stop all modules, no questions asked. """
        self.stop_all_modules()
        if self.remote_manager is not None:
            self.remote_manager.stopServer()
        self.sigManagerQuit.emit(False)

    @QtCore.Slot()
    def restart(self):
        """ Nicely request that all modules shut down for application restart. """
        self.stop_all_modules()
        if self.remote_manager is not None:
            self.remote_manager.stopServer()
        self.sigManagerQuit.emit(True)

    @QtCore.Slot(object)
    def register_task_runner(self, reference):
        """
        Register/unregister/replace a task runner object.
        If a reference is passed that is not None, it is kept and passed out as the task runner
        instance.
        If None is passed, the reference is discarded.
        If another reference is passed, the current one is replaced.

        @param object reference: reference to a task runner or None
        """
        with self.lock:
            if self.task_runner is None and reference is not None:
                logger.info('Task runner registered.')
            elif self.task_runner is not None and reference is None:
                logger.info('Task runner removed.')
            elif self.task_runner is None and reference is None:
                logger.warning('You tried to remove the task runner but none was registered.')
            else:
                logger.warning('Replacing task runner.')
            self.task_runner = reference

    @QtCore.Slot(str, str)
    def pop_up_message(self, title, message):
        """
        Slot prompting a dialog window with a message and an OK button to dismiss it.

        @param str title: The window title of the dialog
        @param str message: The message to be shown in the dialog window
        """
        if not self._has_gui:
            logger.warning('{0}:\n{1}'.format(title, message))
            return

        if self.thread() is not QtCore.QThread.currentThread():
            logger.error('Pop-up notifications can only be invoked from GUI/main thread or via '
                         'queued connection.')
            return
        dialog = PopUpMessage(title=title, message=message)
        dialog.exec_()
        return

    @QtCore.Slot(str, str)
    @QtCore.Slot(str, str, object)
    @QtCore.Slot(str, str, object, object)
    def balloon_message(self, title, message, time=None, icon=None):
        """
        Slot prompting a balloon notification from the system tray icon.

        @param str title: The notification title of the balloon
        @param str message: The message to be shown in the balloon
        @param float time: optional, The lingering time of the balloon in seconds
        @param QIcon icon: optional, an icon to be used in the balloon. "None" will use OS default.
        """
        if not self._has_gui or not self.gui.system_tray_icon.supportsMessages():
            logger.warning('{0}:\n{1}'.format(title, message))
            return
        if self.thread() is not QtCore.QThread.currentThread():
            logger.error('Pop-up notifications can only be invoked from GUI/main thread or via '
                         'queued connection.')
            return
        self.gui.system_tray_notification_bubble(title, message, time=time, icon=icon)
        return




