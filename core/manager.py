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
import weakref
import warnings
from functools import partial

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

logger = logging.getLogger(__name__)


class ManagedModulesSingleton(QtCore.QObject):
    """
    """
    __instance = None  # Only class instance created will be stored here as weakref

    _lock = RecursiveMutex()
    _manager = None
    _modules = dict()

    sigModuleStateChanged = QtCore.Signal(str, str, str)
    sigManagedModulesChanged = QtCore.Signal(dict)

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls.__instance is None or cls.__instance() is None:
                obj = super().__new__(cls, *args, **kwargs)
                cls._modules = dict()
                cls._manager = lambda: None
                cls.__instance = None
                return obj
            return cls.__instance()

    def __init__(self, *args, manager=None, **kwargs):
        with self._lock:
            if ManagedModulesSingleton.__instance is None:
                if not isinstance(manager, Manager):
                    raise Exception('First initialization of ManagedModulesSingleton requires the '
                                    'manager argument to be a Manager instance.')
                super().__init__(*args, **kwargs)
                ManagedModulesSingleton._manager = weakref.ref(
                    manager, partial(self._manager_ref_dead_callback))
                ManagedModulesSingleton.__instance = weakref.ref(self)

    def __del__(self):
        ManagedModulesSingleton.__instance = None
        ManagedModulesSingleton._manager = None

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
                    logger.error('No module with name "{0}" registered. Unable to remove module.'
                                 ''.format(module_name))
                return
            base = self._modules[module_name].module_base
            self._modules[module_name].deactivate()
            self._modules[module_name].sigStateChanged.disconnect(self.sigModuleStateChanged)
            del self._modules[module_name]
            self.refresh_module_links()
            if emit_change:
                self.sigManagedModulesChanged.emit(self.modules)

    def add_module(self, name, base, configuration, allow_overwrite=False, emit_change=True):
        with self._lock:
            if not isinstance(name, str) or not name:
                raise TypeError('module name must be non-empty str type')
            if base not in ('gui', 'logic', 'hardware'):
                logger.error('No valid module base "{0}". Unable to create qudi module "{1}".'
                             ''.format(base, name))
                return
            if allow_overwrite:
                self.remove_module(name, ignore_missing=True)
            elif name in self._modules:
                logger.error(
                    'Module with name "{0}" already registered. Unable to add module of same name.')
                return
            module = ManagedModule(name, base, configuration, self._manager)
            module.sigStateChanged.connect(self.sigModuleStateChanged)
            self._modules[name] = module
            self.refresh_module_links()
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
                logger.error('No module named "{0}" found in managed qudi modules. '
                             'Module activation aborted.'.format(module_name))
                return
            return self._modules[module_name].activate()

    def deactivate_module(self, module_name):
        with self._lock:
            if module_name not in self._modules:
                logger.error('No module named "{0}" found in managed qudi modules. '
                             'Module deactivation aborted.'.format(module_name))
                return
            return self._modules[module_name].deactivate()

    def reload_module(self, module_name):
        with self._lock:
            if module_name not in self._modules:
                logger.error('No module named "{0}" found in managed qudi modules. '
                             'Module reload aborted.'.format(module_name))
                return
            return self._modules[module_name].reload()

    def _module_ref_dead_callback(self, dead_ref, module_name):
        with self._lock:
            self.remove_module(module_name, ignore_missing=True)

    def _manager_ref_dead_callback(self, dead_ref):
        with self._lock:
            logger.error('Unexpected dead Manager weakref encountered in ManagedModulesSingleton.')
            self.clear()


class ManagedModule(QtCore.QObject):
    """ Object representing a qudi module (gui, logic or hardware) to be managed by the qudi Manager
     object. Contains status properties and handles initialization, state transitions and
     connection of the module.
    """
    # ToDo: Handle remote connection/(de)activation
    sigStateChanged = QtCore.Signal(str, str, str)

    _lock = RecursiveMutex()  # Single mutex shared across all ManagedModule instances

    def __init__(self, name, base, configuration, manager_ref):
        if not name or not isinstance(name, str):
            raise NameError('Module name must be a non-empty string.')
        if base not in ('gui', 'logic', 'hardware'):
            raise NameError('Module base must be one of ("gui", "logic", "hardware").')
        if 'module.Class' not in configuration:
            raise KeyError('Mandatory config entry "module.Class" not found in config for module '
                           '"{0}".'.format(name))
        if not isinstance(manager_ref, weakref.ref) or not isinstance(manager_ref(), Manager):
            raise TypeError(
                'manager_ref parameter is expected to be a weak reference to Manager instance.')

        super().__init__()

        self._manager = manager_ref
        self._name = name  # Each qudi module needs a unique string identifier
        self._base = base  # Remember qudi module base
        self._instance = None  # Store the module instance later on

        # Sort out configuration dict
        cfg = copy.deepcopy(configuration)
        # Extract module and class name
        self._module, self._class = cfg.pop('module.Class').rsplit('.', 1)
        # Remember connections by name
        self._connect_cfg = cfg.pop('connect', dict())
        # The rest are config options
        self._options = cfg

        self._required_modules = set()
        self._dependent_modules = set()
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
        with self._lock:
            if self._instance is not None:
                return self._instance.module_status_file_path
            return None

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
            self._required_modules.copy()

    @required_modules.setter
    def required_modules(self, module_iter):
        for module in module_iter:
            if not isinstance(module, weakref.ref):
                raise TypeError('items in required_modules must be weakref.ref instances.')
            if not isinstance(module(), ManagedModule):
                if module() is None:
                    logger.error('Dead weakref passed as required module to ManagedModule "{0}"'
                                 ''.format(self._name))
                    return
                raise TypeError('required_modules must be iterable of ManagedModule instances '
                                '(or weakref to same instances)')
        self._required_modules = set(module_iter)

    @property
    def dependent_modules(self):
        with self._lock:
            self._dependent_modules.copy()

    @dependent_modules.setter
    def dependent_modules(self, module_iter):
        dep_modules = set()
        for module in module_iter:
            if not isinstance(module, weakref.ref):
                raise TypeError('items in dependent_modules must be weakref.ref instances.')
            if not isinstance(module(), ManagedModule):
                if module() is None:
                    logger.error('Dead weakref passed as dependent module to ManagedModule "{0}"'
                                 ''.format(self._name))
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
                    logger.warning('Dead dependent module weakref encountered in ManagedModule '
                                   '"{0}".'.format(self._name))
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
        return 'mod-{0}-{1}'.format(self._base, self._name)

    def activate(self):
        print('starting to activate:', self._name)
        with self._lock:
            if self.is_active:
                if self._base == 'gui':
                    self._instance.show()
                return True

            if not self.is_loaded:
                if not self._load():
                    return False

            # Recursive activation of required modules
            for module_ref in self._required_modules:
                module = module_ref()
                if module is None:
                    logger.error('Dead required module weakref encountered in ManagedModule "{0}".'
                                 ''.format(self._name))
                    return False
                if not module.is_active:
                    if not module.activate():
                        return False

            # Establish module interconnections via Connector meta object in qudi module instance
            if not self._connect():
                return False

            # check if manager reference is set
            manager = self._get_manager()
            if manager is None:
                return False

            print('activating:', self._name)
            try:
                if self._instance.is_module_threaded:
                    thread_name = self.module_thread_name
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
        with self._lock:
            if not self.is_active:
                return True

            success = True  # error flag to return

            # Recursively deactivate dependent modules
            for module_ref in self._dependent_modules:
                module = module_ref()
                if module is None:
                    logger.error('Dead dependent module weakref encountered in ManagedModule "{0}".'
                                 ''.format(self._name))
                    return False
                if module.is_active:
                    success = success and module.deactivate()

            # check if manager reference is set
            manager = self._get_manager()
            if manager is None:
                success = False

            print('deactivating:', self._name)
            # Actual deactivation of this module
            try:
                if self._instance.is_module_threaded:
                    thread_name = self.module_thread_name
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

    def reload(self):
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

            manager = self._get_manager()
            if manager is None:
                return False

            # Try qudi module import
            try:
                mod = importlib.import_module('{0}.{1}'.format(self._base, self._module))
                importlib.reload(mod)
            except ImportError:
                logger.exception(
                    'Error during import of module "{0}.{1}"'.format(self._base, self._module))
                return False

            # Try getting qudi module class from imported module
            try:
                mod_class = getattr(mod, self._class)
            except:
                logger.exception('Error getting module class "{0}" from module "{1}.{2}"'
                                 ''.format(self._class, self._base, self._module))
                return False

            # Check if imported class is a valid qudi module class
            if not issubclass(mod_class, Base):
                logger.error('Qudi module main class must be subclass of core.module.Base')
                return False

            # Try to instantiate the imported qudi module class
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

    def _connect(self):
        with self._lock:
            # Check if module has already been loaded/instantiated
            if not self.is_loaded:
                logger.error('Connection failed. No module instance found or module "{0}.{1}".'
                             ''.format(self._base, self._name))
                return False

            # Get Connector meta objects for this module
            conn_objects = getattr(self._instance, '_module_meta', dict()).get('connectors', dict())
            conn_names = set(conn.name for conn in conn_objects.values())
            mandatory_conn = set(conn.name for conn in conn_objects.values() if not conn.optional)
            configured_conn = set(self._connect_cfg)
            if not configured_conn.issubset(conn_names):
                logger.error('Connection of module "{0}.{1}" failed. Encountered mismatch of '
                             'connectors in configuration {2} and module Connector meta objects '
                             '{3}.'.format(self._base, self._name, configured_conn, conn_names))
                return False
            if not mandatory_conn.issubset(configured_conn):
                logger.error('Connection of module "{0}.{1}" failed. Not all mandatory connectors '
                             'are specified in config.\nMandatory connectors are: {2}'
                             ''.format(self._base, self._name, mandatory_conn))
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
                logger.exception('Something went wrong while trying to connect module "{0}.{1}".'
                                 ''.format(self._base, self._name))
                return False
            return True

    def _disconnect(self):
        with self._lock:
            try:
                conn_obj = getattr(self._instance, '_module_meta', dict()).get('connectors', dict())
                for connector in conn_obj.values():
                    connector.disconnect()
            except:
                logger.exception('Something went wrong while trying to disconnect module "{0}.{1}".'
                                 ''.format(self._base, self._name))
                return False
            return True

    def _get_manager(self):
        # check if manager reference is set
        manager = self._manager()
        if manager is None:
            logger.error('Unable to activate/deactivate ManagedModule instance with name "{0}". '
                         'Weak reference to Manager instance is not set or has been garbage '
                         'collected.'.format(self._name))
        return manager


class Manager(QtCore.QObject):
    """The Manager object is responsible for:
      - Loading/configuring device modules and storing their handles
      - Providing unified timestamps
      - Making sure all devices/modules are properly shut down at the end of the program

    @signal sigConfigChanged: the configuration has changed, please reread your configuration
    @signal sigManagedModulesChanged: the available modules have changed
    @signal (str, str, str) sigModuleStateChanged: the module state has changed (base, name, state)
    @signal sigManagerQuit: the manager is quitting
    @signal sigShowManager: show whatever part of the GUI is important
    """

    # Signal declarations for Qt
    sigConfigChanged = QtCore.Signal(dict)
    sigManagedModulesChanged = QtCore.Signal(dict)
    sigModuleStateChanged = QtCore.Signal(str, str, str)
    sigManagerQuit = QtCore.Signal(bool)
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
        # Singleton container for all qudi modules
        self.managed_modules = ManagedModulesSingleton(manager=self)
        self.managed_modules.sigModuleStateChanged.connect(self.sigModuleStateChanged)
        self.managed_modules.sigManagedModulesChanged.connect(self.sigManagedModulesChanged)

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
            self.__load_and_process_config()
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
                self.activate_module(module_name)

        # Gui setup if we have gui
        if self._has_gui:
            if self._stylesheet:
                style_path = os.path.join(get_main_dir(),
                                          'artwork',
                                          'styles',
                                          'application',
                                          self._stylesheet)
                if not os.path.isfile(style_path):
                    logger.warning('Stylesheet not found at "{0}"'.format(style_path))
                    self._stylesheet = None
                    style_path = None
            else:
                style_path = None

            try:
                from .gui.gui import Gui
                self.gui = Gui(artwork_dir=os.path.join(get_main_dir(), 'artwork'),
                               stylesheet_path=style_path)
                self.gui.system_tray_icon.quitAction.triggered.connect(self.quit)
                self.gui.system_tray_icon.managerAction.triggered.connect(self.sigShowManager)
                self.gui.set_theme('qudiTheme')
            except:
                logger.error('Error during GUI setup.')
                raise

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
            for mod_name, module in self.managed_modules.items():
                mod_dict = dict()
                mod_dict['module.Class'] = '{0}.{1}'.format(module.module_name, module.class_name)
                mod_dict.update(module.options)
                mod_dict['connect'] = module.connection_cfg
                config_tree[module.module_base][mod_name] = mod_dict
            return config_tree

    @property
    def configured_modules(self):
        return self.managed_modules.module_names

    @property
    def activated_modules(self):
        return tuple(name for name, mod in self.managed_modules.items() if mod.is_active)

    @property
    def deactivated_modules(self):
        return tuple(name for name, mod in self.managed_modules.items() if
                     mod.is_loaded and not mod.is_active)

    @property
    def module_states(self):
        return {name: mod.state for name, mod in self.managed_modules.items()}

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
        print('============= Starting Manager configuration from {0} ============='
              ''.format(self.config_file_path))
        logger.info('Starting Manager configuration from {0}'.format(self.config_file_path))

        # Clean up previous config settings
        for ext_path in self._extension_paths:
            if ext_path in sys.path:
                sys.path.remove(ext_path)
        self.managed_modules.clear()

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
            modules_dict = cfg.pop(base, None)
            if not modules_dict:
                continue
            # Create ManagedModule instance by adding each module to ManagedModulesSingleton
            for module_name, module_cfg in modules_dict.items():
                try:
                    self.managed_modules.add_module(name=module_name,
                                                    base=base,
                                                    configuration=module_cfg)
                except:
                    self.managed_modules.remove_module(module_name, ignore_missing=True)
                    logger.exception('Unable to create ManagedModule instance for module '
                                     '"{0}.{1}"'.format(base, module_name))

        # Check if there is still a part of the config unprocessed
        if cfg:
            logger.warning('Unknown config file sections encountered.\nAllowed sections are: '
                           '{0}\nThe following part will be ignored:\n{1}'
                           ''.format(('global', 'gui', 'logic', 'hardware'), cfg))
        print("\n============= Manager configuration complete =================\n")
        logger.info('Manager configuration complete.')
        self.sigConfigChanged.emit(self.config_dict)

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
                logger.error('Module "{0}" not declared in config file. Unable to reload module '
                             'config.'.format(module_name))
                return

            # remember if module was active
            was_active = self.is_module_active(module_name)
            # Deactivate and remove module from managed modules
            self.managed_modules.remove_module(module_name)
            # Add module again to managed modules with new config
            self.managed_modules.add_module(name=module_name, base=base, configuration=module_cfg)
            # Re-activate module if it was active before
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
            logger.warning('No module by the name "{0}" configured. Unable to poll activation '
                           'status.'.format(module_name))
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
        logger.info('Activating qudi module "{0}"'.format(module_name))
        if not self.managed_modules.activate_module(module_name):
            logger.error('Unable to activate qudi module "{0}"'.format(module_name))
            return False
        logger.debug('Activation success of qudi module "{0}"'.format(module_name))
        return True

    @QtCore.Slot(str)
    def deactivate_module(self, module_name):
        """Deactivate the module given in module_name. Does nothing if already deactivated.

        @param str module_name: module which is going to be activated.
        """
        logger.info('Deactivating qudi module "{0}"'.format(module_name))
        if not self.managed_modules.deactivate_module(module_name):
            logger.error('Unable to deactivate qudi module "{0}"'.format(module_name))
            return False
        logger.debug('Deactivation success of qudi module "{0}"'.format(module_name))
        return True

    @QtCore.Slot(str)
    def restart_module(self, module_name):
        """Restart qudi module

        @param str module_name: Unique module name as defined in config
        """
        logger.info('Restarting/reloading qudi module "{0}"'.format(module_name))
        if not self.managed_modules.reload_module(module_name):
            logger.error('Unable to restart/reload qudi module "{0}"'.format(module_name))
        else:
            logger.debug('Restart/reload success of qudi module "{0}"'.format(module_name))

    @QtCore.Slot()
    def start_all_modules(self):
        """Configure, connect and activate all qudi modules from the currently loaded configuration.
        """
        logger.info('Starting all qudi modules...')
        for module_name in self.managed_modules.module_names:
            if not self.managed_modules.activate_module(module_name):
                logger.warning(
                    'Activating module "{0}" failed while loading all modules.'.format(module_name))
        logger.info('Start all qudi modules finished.')

    @QtCore.Slot()
    def stop_all_modules(self):
        """Deactivate all qudi modules from the currently loaded configuration.
        """
        logger.info('Stopping all qudi modules...')
        for module_name in self.managed_modules.module_names:
            if not self.managed_modules.deactivate_module(module_name):
                logger.warning('Deactivating module "{0}" failed while loading all modules.'
                               ''.format(module_name))
        logger.info('Stopping all qudi modules finished.')

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
        for module in self.managed_modules.values():
            if module.is_busy:
                locked_modules = True
            elif module.state == 'BROKEN':
                broken_modules = True
            if broken_modules and locked_modules:
                break

        if self._has_gui:
            if self.gui.prompt_shutdown(locked_modules):
                self.force_quit()
        else:
            # FIXME: console prompt here
            self.force_quit()

    @QtCore.Slot()
    def force_quit(self):
        """ Stop all modules, no questions asked. """
        self.stop_all_modules()
        if self.remote_manager is not None:
            self.remote_manager.stopServer()
        self.managed_modules.clear()
        self.sigManagerQuit.emit(False)

    @QtCore.Slot()
    def restart(self):
        """ Nicely request that all modules shut down for application restart. """
        self.stop_all_modules()
        if self.remote_manager is not None:
            self.remote_manager.stopServer()
        self.managed_modules.clear()
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
        else:
            self.gui.pop_up_message(title, message)
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
        if self._has_gui:
            self.gui.balloon_message(title, message, time, icon)
        else:
            logger.warning('{0}:\n{1}'.format(title, message))
        return
