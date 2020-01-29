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
import time
import logging
logger = logging.getLogger(__name__)

import os
import sys
import re
import importlib

from qtpy import QtCore
from . import config

from .util import get_main_dir
from .util.mutex import Mutex   # Mutex provides access serialization between threads
from .util.modules import toposort, is_base
from collections import OrderedDict
from .logger import register_exception_handler
from .threadmanager import ThreadManager
# try to import RemoteObjectManager. Might fail if rpyc is not installed.
try:
    from .remote import RemoteObjectManager
except ImportError:
    RemoteObjectManager = None
from .module import Base
from .connector import Connector
from .gui.popup_dialog import PopUpMessage


class Manager(QtCore.QObject):
    """The Manager object is responsible for:
      - Loading/configuring device modules and storing their handles
      - Providing unified timestamps
      - Making sure all devices/modules are properly shut down
        at the end of the program

      @signal sigConfigChanged: the configuration has changed, please reread your configuration
      @signal sigModulesChanged: the available modules have changed
      @signal sigModuleHasQuit: the module whose name is passed is now deactivated
      @signal sigAbortAll: abort all running things as quicly as possible
      @signal sigManagerQuit: the manager is quitting
      @signal sigManagerShow: show whatever part of the GUI is important
      """

    # Prepare Signal declarations for Qt: Allows Python to interface with Qt
    # signal and slot delivery mechanisms.
    sigConfigChanged = QtCore.Signal()
    sigModulesChanged = QtCore.Signal()
    sigModuleHasQuit = QtCore.Signal(object)
    sigLogDirChanged = QtCore.Signal(object)
    sigAbortAll = QtCore.Signal()
    sigManagerQuit = QtCore.Signal(object, bool)
    sigShutdownAcknowledge = QtCore.Signal(bool, bool)
    sigShowManager = QtCore.Signal()

    def __init__(self, args, **kwargs):
        """
        Constructor for Qudi main management class

        @param args: argparse command line arguments
        """
        # used for keeping some basic methods thread-safe
        self.lock = Mutex(recursive=True)
        self.tree = OrderedDict()
        self.tree['config'] = OrderedDict()
        self.tree['defined'] = OrderedDict()
        self.tree['loaded'] = OrderedDict()

        self.tree['defined']['hardware'] = OrderedDict()
        self.tree['loaded']['hardware'] = OrderedDict()

        self.tree['defined']['gui'] = OrderedDict()
        self.tree['loaded']['gui'] = OrderedDict()

        self.tree['defined']['logic'] = OrderedDict()
        self.tree['loaded']['logic'] = OrderedDict()

        self.tree['global'] = OrderedDict()
        self.tree['global']['startup'] = list()

        self.has_gui = not args.no_gui
        self.remote_server = False

        try:
            # Initialize parent class QObject
            super().__init__()

            # Register exception handler
            register_exception_handler(self)

            # Thread management
            self.thread_manager = ThreadManager()
            logger.debug('Main thread is {0}'.format(QtCore.QThread.currentThread()))

            # Task runner
            self.task_runner = None

            # Gui setup if we have gui
            if self.has_gui:
                import core.gui.gui
                self.gui = core.gui.gui.Gui(artwork_dir=os.path.join(get_main_dir(), 'artwork'))
                self.gui.system_tray_icon.quitAction.triggered.connect(self.quit)
                self.gui.system_tray_icon.managerAction.triggered.connect(self.sigShowManager)
                self.gui.set_theme('qudiTheme')

            # Read in configuration file
            self.config_file = args.config if args.config else self.find_default_config_file()
            # self.config_dir = os.path.dirname(config_file)
            print('============= Starting Manager configuration from {0} ================='
                  ''.format(self.config_file))
            logger.info("Starting Manager configuration from {0}".format(self.config_file))
            cfg = self.read_config_file(self.config_file, missing_ok=False)
            self.configure(cfg)
            print("\n============= Manager configuration complete =================\n")
            logger.info('Manager configuration complete.')

            # check first if remote support is enabled and if so create RemoteObjectManager
            if RemoteObjectManager is None:
                logger.error('Remote modules disabled. Rpyc not installed.')
                self.remote_manager = None
            else:
                self.remote_manager = RemoteObjectManager(self)
                # Create remote module server if specified in config file
                if 'module_server' in self.tree['global']:
                    if not isinstance(self.tree['global']['module_server'], dict):
                        logger.error('"module_server" entry in "global" section of configuration'
                                     ' file is not a dictionary.')
                    else:
                        # new style
                        try:
                            server_address = self.tree['global']['module_server'].get('address',
                                                                                      'localhost')
                            server_port = self.tree['global']['module_server'].get('port', 12345)
                            certfile = self.tree['global']['module_server'].get('certfile', None)
                            keyfile = self.tree['global']['module_server'].get('keyfile', None)
                            self.remote_manager.createServer(server_address,
                                                             server_port,
                                                             certfile,
                                                             keyfile)
                            # successfully started remote server
                            logger.info(
                                'Started server rpyc://{0}:{1}'.format(server_address, server_port))
                            self.remote_server = True
                        except:
                            logger.exception('Rpyc server could not be started.')

            logger.info('qudi started.')

            # Load startup things from config here
            if 'startup' in self.tree['global']:
                # walk throug the list of loadable modules to be loaded on
                # startup and load them if appropriate
                for key in self.tree['global']['startup']:
                    if key in self.tree['defined']['hardware']:
                        self.start_module('hardware', key)
                        self.sigModulesChanged.emit()
                    elif key in self.tree['defined']['logic']:
                        self.start_module('logic', key)
                        self.sigModulesChanged.emit()
                    elif self.has_gui and key in self.tree['defined']['gui']:
                        self.start_module('gui', key)
                        self.sigModulesChanged.emit()
                    else:
                        logger.error('Loading startup module {} failed, not '
                                     'defined anywhere.'.format(key))
        except:
            logger.exception('Error while configuring Manager:')
        finally:
            if (len(self.tree['loaded']['logic']) == 0
                    and len(self.tree['loaded']['gui']) == 0):
                logger.critical('No modules loaded during startup.')

    @property
    def default_config_dir(self):
        return os.path.join(get_main_dir(), 'config')

    @property
    def config_dir(self):
        return os.path.dirname(self.config_file)

    def find_default_config_file(self):
        """
        Search all the default locations to find a suitable configuration file.

        @return str: path to configuration file
        """
        # we first look for config/load.cfg which can point to another config file using the
        # "configfile" key
        load_config_file = os.path.join(self.default_config_dir, 'load.cfg')
        if os.path.isfile(load_config_file):
            logger.info('load.cfg config file found at {0}'.format(load_config_file))
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

    @QtCore.Slot(dict)
    def configure(self, cfg):
        """
        Sort modules from configuration into categories

        @param dict cfg: dictionary from configuration file

        There are the main categories hardware, logic, gui, startup and global.
        Startup modules can be logic or gui and are loaded directly on 'startup'. 'global' contains
        settings for the whole application. hardware, logic and gui contain configuration of and
        for loadable modules.
        """
        for key in cfg:
            try:
                # hardware
                if key == 'hardware' and cfg['hardware'] is not None:
                    for m in cfg['hardware']:
                        if 'module.Class' in cfg['hardware'][m]:
                            self.tree['defined']['hardware'][m] = cfg['hardware'][m]
                        else:
                            logger.warning(
                                '    --> Ignoring device {0} -- no module specified'.format(m))

                # logic
                elif key == 'logic' and cfg['logic'] is not None:
                    for m in cfg['logic']:
                        if 'module.Class' in cfg['logic'][m]:
                            self.tree['defined']['logic'][m] = cfg['logic'][m]
                        else:
                            logger.warning(
                                '    --> Ignoring logic {0} -- no module specified'.format(m))

                # GUI
                elif key == 'gui' and cfg['gui'] is not None and self.has_gui:
                    for m in cfg['gui']:
                        if 'module.Class' in cfg['gui'][m]:
                            self.tree['defined']['gui'][m] = cfg['gui'][m]
                        else:
                            logger.warning(
                                '    --> Ignoring GUI {0} -- no module specified'.format(m))

                # Load on startup
                elif key == 'startup':
                    logger.warning(
                        'Old style startup loading not supported. Please update your config file.')

                # global config
                elif key == 'global' and cfg['global'] is not None:
                    for m in cfg['global']:
                        if m == 'extensions':
                            # deal with str, list and unknown types
                            if isinstance(cfg['global'][m], str):
                                dirnames = [cfg['global'][m]]
                            elif isinstance(cfg['global'][m], list):
                                dirnames = cfg['global'][m]
                            else:
                                logger.warning('Global "path" configuration is neither str nor '
                                               'list. Ignoring.')
                                continue
                            # add specified directories
                            for ii, dir_name in enumerate(dirnames):
                                path = ''
                                # absolute or relative path? Existing?
                                if os.path.isabs(dir_name) and os.path.isdir(dir_name):
                                    path = dir_name
                                else:
                                    # relative path?
                                    path = os.path.abspath(
                                        '{0}/{1}'.format(self.config_dir, dir_name))
                                    if not os.path.isdir(path):
                                        path = ''
                                if path == '':
                                    logger.warning('Error while adding qudi extension: Directory '
                                                   '\'{0}\' does not exist.'.format(dir_name))
                                    continue
                                # check for __init__.py files within extension and issue warning
                                # if existing
                                for paths, dirs, files in os.walk(path):
                                    if '__init__.py' in files:
                                        logger.warning('Warning: Extension {0} contains '
                                                       '__init__.py. Expect unexpected behaviour. '
                                                       'Hope you know what you are doing.'
                                                       ''.format(path))
                                        break
                                # add directory to search path
                                logger.debug('Adding extension path: {0}'.format(path))
                                sys.path.insert(1+ii, path)
                        elif m == 'startup':
                            self.tree['global']['startup'] = cfg['global']['startup']
                        elif m == 'stylesheet' and self.has_gui:
                            self.tree['global']['stylesheet'] = cfg['global']['stylesheet']
                            stylesheetpath = os.path.join(get_main_dir(),
                                                          'artwork',
                                                          'styles',
                                                          'application',
                                                          cfg['global']['stylesheet'])
                            if not os.path.isfile(stylesheetpath):
                                logger.warning('Stylesheet not found at {0}'.format(stylesheetpath))
                                continue
                            self.gui.set_style_sheet(stylesheetpath)
                        else:
                            self.tree['global'][m] = cfg['global'][m]

                # Copy in any other configurations.
                # dicts are extended, all others are overwritten.
                else:
                    if isinstance(cfg[key], dict):
                        if key not in self.tree['config']:
                            self.tree['config'][key] = dict()
                        for key2 in cfg[key]:
                            self.tree['config'][key][key2] = cfg[key][key2]
                    else:
                        self.tree['config'][key] = cfg[key]
            except:
                logger.exception('Error in configuration:')
        self.sigConfigChanged.emit()

    def read_config_file(self, file_path, missing_ok=True):
        """
        Actually check if the configuration file exists and read it

        @param str file_path: path to configuration file
        @param bool missing_ok: suppress exception if file does not exist

        @return dict: configuration from file
        """
        with self.lock:
            if not os.path.isfile(file_path):
                file_path = os.path.join(self.config_dir, file_path)
            return config.load(file_path, ignore_missing=missing_ok)

    @QtCore.Slot(dict, str)
    def write_config_file(self, data, file_path):
        """
        Write a file into the currently used config directory.

        @param dict data: dictionary to write into file
        @param str file_path: path for filr to be written
        """
        with self.lock:
            file_path = os.path.join(self.config_dir, file_path)
            file_dir = os.path.dirname(file_path)
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)
            config.save(file_path, data)

    @QtCore.Slot(str)
    def save_config_to_file(self, file_path):
        """
        Save current configuration to a file.

        @param str file_path: path where the config file should be saved
        """
        config_tree = OrderedDict()
        config_tree.update(self.tree['defined'])
        config_tree['global'] = self.tree['global']

        self.write_config_file(config_tree, file_path)
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

    @QtCore.Slot(str, str)
    def reload_config_part(self, base, mod):
        """Reread the configuration file and update the internal configuration of module

        @params str modname: name of module where config file should be reloaded.
        """
        config_path = self.find_default_config_file()
        cfg = self.read_config_file(config_path)
        try:
            if cfg[base][mod]['module.Class'] == self.tree['defined'][base][mod]['module.Class']:
                self.tree['defined'][base][mod] = cfg[base][mod]
        except KeyError:
            pass

    ##################
    # Module loading #
    ##################
    def import_qudi_module(self, base, module):
        """
        Load a python module that is a loadable qudi module.

        @param str base: the module base package (hardware, logic, or gui)
        @param str module: the python module name inside the base package

        @return object: the loaded python module
        """

        logger.info('Loading module ".{0}.{1}"'.format(base, module))
        if not is_base(base):
            raise Exception(
                'You are trying to cheat the system with some module category "{0}"'.format(base))

        # load the python module
        mod = importlib.__import__('{0}.{1}'.format(base, module), fromlist=['*'])
        return mod

    def configure_qudi_module(self, module, base, class_name, instance_name, configuration=None):
        """
        Instantiate an object from the class that makes up a qudi module from a loaded python
        module object.
        This method will also add the resulting qudi module instance to internal bookkeeping.

        @param object module: loaded python module
        @param str base: module base package (hardware, logic or gui)
        @param str class_name: class name we want an object from (same as module name usually)
        @param str instance_name: unique name the qudi module instance was given in the config
        @param dict configuration: configuration options for the qudi module

        @return object: qudi module instance (child object derived from module Base class)
        """
        if configuration is None:
            configuration = dict()

        # Sanity checking
        logger.info('Configuring {0} as {1}'.format(class_name, instance_name))
        with self.lock:
            if is_base(base):
                if self.is_module_loaded(base, instance_name):
                    raise Exception('{0} already exists with name {1}'.format(base, instance_name))
            else:
                raise Exception('You are trying to cheat the system with some module category '
                                '"{0}"'.format(base))

        # get class from module by name
        modclass = getattr(module, class_name)

        # Check if the class we just obtained has the right inheritance
        if not issubclass(modclass, Base):
            raise Exception('Bad inheritance for instance {0!s} from {1!s}.{2!s}.'
                            ''.format(instance_name, base, class_name))

        # Create instance from class
        instance = modclass(manager=self, name=instance_name, config=configuration)

        with self.lock:
            self.tree['loaded'][base][instance_name] = instance

        self.sigModulesChanged.emit()
        return instance

    def connect_qudi_module(self, base, instance_name):
        """
        Connects the given module instance by name instance_name to main object with the help of
        base.

        @param str base: module base package (hardware, logic or gui)
        @param str instance_name: module instance name (as defined in config) you want to connect

        @return int: 0 on success, -1 on failure
        """
        # Check if module is defined and loaded
        thismodule = self.tree['defined'][base][instance_name]
        if not self.is_module_loaded(base, instance_name):
            logger.error('Loading of {0} module {1} as {2} was not successful, not connecting it.'
                         ''.format(base, thismodule['module.Class'], instance_name))
            return -1

        # Check if connections need to be established. Return early if not
        loaded_module = self.tree['loaded'][base][instance_name]
        if 'connect' not in thismodule:
            return 0

        # Sanity checking for broken configuration
        if not isinstance(loaded_module.connectors, dict):
            logger.error('Connectors attribute of module {0}.{1} is not a dictionary.'
                         ''.format(base, instance_name))
            return -1
        if 'module.Class' not in thismodule:
            logger.error('Connection configuration of module {0}.{1} is broken: no module defined.'
                         ''.format(base, instance_name))
            return -1
        if not isinstance(thismodule['connect'], dict):
            logger.error('Connection configuration of module {0}.{1} is broken: connect is not a '
                         'dictionary.'.format(base, instance_name))
            return -1

        # lets go through all connections provided in configuration
        connections = thismodule['connect']
        for c in connections:
            connectors = loaded_module.connectors
            if c not in connectors:
                logger.error('Connector {0}.{1}.{2} is supposed to get connected but is not '
                             'declared in the module class.'.format(c, base, instance_name))
                continue
            if not isinstance(connectors[c], Connector):
                logger.error('{0}.{1}.{2}: Connector is no Connector object instance.'
                             ''.format(c, base, instance_name))
                continue
            if not isinstance(connections[c], str):
                logger.error('Connector configuration {0}.{1}.{2} is broken since it is not a str.'
                             ''.format(base, instance_name, c))
                continue

            destmod = connections[c]
            # check if module exists at all
            if not any(destmod in self.tree['loaded'][b] for b in ('gui', 'logic', 'hardware')):
                logger.error('Cannot connect {0}.{1}.{2} to module {3}. Module does not exist.'
                             ''.format(base, instance_name, c, destmod))
                continue
            # check that module exists only once
            if not ((destmod in self.tree['loaded']['gui']) ^
                    (destmod in self.tree['loaded']['hardware']) ^
                    (destmod in self.tree['loaded']['logic'])):
                logger.error('Cannot connect {0}.{1}.{2} to module {3}. Module exists more than '
                             'once.'.format(base, instance_name, c, destmod))
                continue

            # find category of module that should be connected to
            if destmod in self.tree['loaded']['gui']:
                destbase = 'gui'
            elif destmod in self.tree['loaded']['hardware']:
                destbase = 'hardware'
            elif destmod in self.tree['loaded']['logic']:
                destbase = 'logic'

            # Finally set the connection object
            logger.info('Connecting {0}.{1}.{2} to {3}.{4}'
                        ''.format(base, instance_name, c, destbase, destmod))
            if isinstance(connectors[c], Connector):
                connectors[c].connect(self.tree['loaded'][destbase][destmod])
            else:
                logger.error(
                    'Connector {0} has wrong type even though we checked before.'.format(c))
                continue

        # check that all connectors are connected
        for c, v in self.tree['loaded'][base][instance_name].connectors.items():
            if isinstance(v, Connector) and not v.is_connected and not v.optional:
                logger.error('Connector {0} of module {1}.{2} is not connected. Connection not '
                             'complete.'.format(c, base, instance_name))
                return -1
        return 0

    def load_and_configure_qudi_module(self, base, instance_name):
        """
        Loads the configuration module in instance_name with the help of base class.

        @param str base: module base package (hardware, logic or gui)
        @param str instance_name: module instance name (as defined in config) you want to load

        @return int: 0 on success, -1 on fatal error, 1 on error
        """
        defined_module = self.tree['defined'][base][instance_name]
        if 'module.Class' in defined_module:
            if 'remote' in defined_module:
                if self.remote_manager is None:
                    logger.error('Remote module functionality disabled. Rpyc not installed.')
                    return -1
                if not isinstance(defined_module['remote'], str):
                    logger.error('Remote URL of {0} module {1} not a string.'
                                 ''.format(base, instance_name))
                    return -1
                try:
                    certfile = defined_module.get('certfile', None)
                    keyfile = defined_module.get('keyfile', None)
                    instance = self.remote_manager.getRemoteModuleUrl(defined_module['remote'],
                                                                      certfile=certfile,
                                                                      keyfile=keyfile)
                    logger.info('Remote module {0} loaded as {1}.{2}.'
                                ''.format(defined_module['remote'], base, instance_name))
                    with self.lock:
                        if is_base(base):
                            self.tree['loaded'][base][instance_name] = instance
                            self.sigModulesChanged.emit()
                        else:
                            raise Exception('You are trying to cheat the system with some category '
                                            '{0}'.format(base))
                except:
                    logger.exception('Error while loading {0} module: {1}'
                                     ''.format(base, instance_name))
                    return -1
            else:
                try:
                    # class_name is the last part of the config entry
                    class_name = re.split('\.', defined_module['module.Class'])[-1]
                    # module_name is the whole line without this last part (and with trailing dot
                    # removed)
                    module_name = re.sub('.' + class_name + '$',
                                         '',
                                         defined_module['module.Class'])

                    mod_obj = self.import_qudi_module(base, module_name)

                    # Ensure that the namespace of a module is reloaded before instantiation.
                    # That will not harm anything. Even if the import is successful an error might
                    # occur during instantiation. E.g. in an abc metaclass, methods might be
                    # missing in a derived interface file. Reloading the namespace will prevent the
                    # need to restart qudi, if a module instantiation was not successful upon load.
                    importlib.reload(mod_obj)

                    self.configure_qudi_module(mod_obj,
                                               base,
                                               class_name,
                                               instance_name,
                                               defined_module)

                    if 'remoteaccess' in defined_module and defined_module['remoteaccess']:
                        if self.remote_manager is None:
                            logger.error(
                                'Remote module sharing functionality disabled. Rpyc not installed.')
                            return 1
                        if not self.remote_server:
                            logger.error('Remote module sharing does not work as no server '
                                         'configured or server startup failed earlier. Check your '
                                         'configuration and log.')
                            return 1
                        self.remote_manager.shareModule(instance_name,
                                                        self.tree['loaded'][base][instance_name])
                except:
                    logger.exception(
                        'Error while loading {0} module: {1}'.format(base, instance_name))
                    return -1
        else:
            logger.error(
                'Missing module declaration in configuration: {0}.{1}'.format(base, instance_name))
            return -1
        return 0

    def reload_and_configure_qudi_module(self, base, instance_name):
        """
        Reloads the configuration module in instance_name with the help of base class.

        @param str base: module base package (hardware, logic or gui)
        @param str instance_name: module instance name (as defined in config) you want to reload

        @return int: 0 on success, -1 on failure
        """
        defined_module = self.tree['defined'][base][instance_name]
        if 'remote' in defined_module:
            if self.remote_manager is None:
                logger.error('Remote functionality not working, check your log.')
                return -1
            if not isinstance(defined_module['remote'], str):
                logger.error(
                    'Remote URL of {0} module {1} not a string.'.format(base, instance_name))
                return -1
            try:
                instance = self.remote_manager.getRemoteModuleUrl(defined_module['remote'])
                logger.info('Remote module {0} loaded as .{1}.{2}.'
                            ''.format(defined_module['remote'], base, instance_name))
                with self.lock:
                    if is_base(base):
                        self.tree['loaded'][base][instance_name] = instance
                        self.sigModulesChanged.emit()
                    else:
                        raise Exception('You are trying to cheat the system with some module '
                                        'category "{0}"'.format(base))
            except:
                logger.exception('Error while loading {0} module: {1}'.format(base, instance_name))
                return -1
        elif instance_name in self.tree['loaded'][base] and 'module.Class' in defined_module:
            try:
                # state machine: deactivate
                if self.is_module_active(base, instance_name):
                    self.deactivate_module(base, instance_name)
            except:
                logger.exception(
                    'Error while deactivating {0} module: {1}'.format(base, instance_name))
                return -1
            try:
                with self.lock:
                    self.tree['loaded'][base].pop(instance_name, None)
                # reload config part associated with module
                self.reloadConfigPart(base, instance_name)
                # class_name is the last part of the config entry
                class_name = re.split('\.', defined_module['module.Class'])[-1]
                # module_name is the whole line without this last part (and with trailing dot
                # removed)
                module_name = re.sub('.' + class_name + '$',
                                     '',
                                     defined_module['module.Class'])

                mod_obj = self.import_qudi_module(base, module_name)
                # des Pudels Kern
                importlib.reload(mod_obj)
                self.configure_qudi_module(mod_obj, base, class_name, instance_name, defined_module)
            except:
                logger.exception(
                    'Error while reloading {0} module: {1}'.format(base, instance_name))
                return -1
        else:
            logger.error('Module not loaded or not loadable (missing module declaration in '
                         'configuration): {0}.{1}'.format(base, instance_name))
        return 0

    def is_module_defined(self, base, name):
        """
        Check if module is present in module definition.

        @param str base: module base package (hardware, logic or gui)
        @param str name: unique module name to check

        @return bool: module is present in definition
        """
        return (is_base(base)
                and base in self.tree['defined']
                and name in self.tree['defined'][base])

    def is_module_loaded(self, base, name):
        """
        Check if module was loaded.

        @param str base: module base package (hardware, logic or gui)
        @param str name: unique module name to check

        @return bool: module is loaded
        """
        return is_base(base) and base in self.tree['loaded'] and name in self.tree['loaded'][base]

    def is_module_active(self, base, name):
        """
        Returns whether a given module is active.

        @param str base: module base package (hardware, logic or gui)
        @param str name: unique module name to check

        @return bool: module is active flag
        """
        if not self.is_module_loaded(base, name):
            return False
        return self.tree['loaded'][base][name].module_state() != 'deactivated'

    def find_module_base(self, name):
        """
        Find base (hardware, logic or gui) for a given module name.

        @param str name: unique module name

        @return str: base name (hardware, logic or gui)
        """
        for base in ('hardware', 'logic', 'gui'):
            if name in self.tree['defined'][base]:
                return base
        raise KeyError(name)

    @QtCore.Slot(str, str)
    def activate_module(self, base, name):
        """
        Activate the module given in name with the help of base class.

        @param str base: module base package (hardware, logic or gui)
        @param str name: module which is going to be activated.
        """
        if not self.is_module_loaded(base, name):
            logger.error('{0} module {1} not loaded.'.format(base, name))
            return
        module = self.tree['loaded'][base][name]
        if module.module_state() != 'deactivated':
            if self.is_module_defined(base, name) and 'remote' in self.tree['defined'][base][name]:
                logger.debug('No need to activate remote module {0}.{1}.'.format(base, name))
            else:
                logger.error('{0} module {1} not deactivated'.format(base, name))
            return
        try:
            module.status_variables = self.load_module_status_variables(base, name)
            # start main loop for qt objects
            if module.is_module_threaded:
                thread_name = 'mod-{0}-{1}'.format(base, name)
                thread = self.thread_manager.get_new_thread(thread_name)
                module.moveToThread(thread)
                thread.start()
                QtCore.QMetaObject.invokeMethod(module.module_state,
                                                'activate',
                                                QtCore.Qt.BlockingQueuedConnection)
                # Cleanup if activation was not successful
                if not module.module_state() != 'deactivated':
                    QtCore.QMetaObject.invokeMethod(module,
                                                    'move_to_manager_thread',
                                                    QtCore.Qt.BlockingQueuedConnection)
                    self.thread_manager.quit_thread(thread_name)
                    self.thread_manager.join_thread(thread_name)
            else:
                module.module_state.activate()  # runs on_activate in main thread
            logger.debug('Activation success: {}'.format(module.module_state() != 'deactivated'))
        except:
            logger.exception('{0} module {1}: error during activation:'.format(base, name))
        QtCore.QCoreApplication.instance().processEvents()

    @QtCore.Slot(str, str)
    def deactivate_module(self, base, name):
        """
        Activated the module given in name with the help of base class.

        @param str base: module base package (hardware, logic or gui)
        @param str name: module which is going to be activated.
        """
        logger.info('Deactivating {0}.{1}'.format(base, name))
        if not self.is_module_loaded(base, name):
            logger.error('{0} module {1} not loaded.'.format(base, name))
            return
        module = self.tree['loaded'][base][name]
        try:
            if not self.is_module_active(base, name):
                logger.error('{0} module {1} is not activated.'.format(base, name))
                return
        except:
            logger.exception('Error while getting status of {0}. Removing reference without '
                             'deactivation.'.format(name))
            with self.lock:
                self.tree['loaded'][base].pop(name)
            return
        try:
            if module.is_module_threaded:
                thread_name = module.thread().objectName()
                QtCore.QMetaObject.invokeMethod(module.module_state,
                                                'deactivate',
                                                QtCore.Qt.BlockingQueuedConnection)
                QtCore.QMetaObject.invokeMethod(module,
                                                'move_to_manager_thread',
                                                QtCore.Qt.BlockingQueuedConnection)

                self.thread_manager.quit_thread(thread_name)
                self.thread_manager.join_thread(thread_name)
            else:
                module.module_state.deactivate()  # runs on_deactivate in main thread

            self.save_module_status_variables(base, name, module.status_variables)
            logger.debug('Deactivation success: {}'.format(module.module_state() == 'deactivated'))
        except:
            logger.exception('{0} module {1}: error during deactivation:'.format(base, name))
        QtCore.QCoreApplication.instance().processEvents()

    @QtCore.Slot(str, str)
    def get_reverse_recursive_module_dependencies(self, base, module_name, deps=None):
        """
        Based on input connector declarations, determine which other modules need to be removed
        when stopping.

        @param str base: module base package (hardware, logic or gui)
        @param str module_name: unique configured module name to get the dependencies for

        @return dict: module dependencies in the right format for the toposort function
        """
        if deps is None:
            deps = dict()
        if not self.is_module_defined(base, module_name):
            logger.error('{0} module {1}: no such module defined'.format(base, module_name))
            return None

        deplist = set()
        for base_name, base_tree in self.tree['defined'].items():
            for mod_name, mod in base_tree.items():
                if 'connect' not in mod:
                    continue
                connections = mod['connect']
                if not isinstance(connections, dict):
                    logger.error(
                        '{0} module {1}: connect is not a dictionary'.format(base_name, mod_name))
                    continue
                for conn_name, connection in connections.items():
                    conn = connection
                    if '.' in connection:
                        conn = connection.split('.')[0]
                        logger.warning(
                            '{0}.{1}: connection {2}: {3} has legacy format for connection target'
                            ''.format(base_name, mod_name, conn_name, connection))
                    if conn == module_name:
                        deplist.add(mod_name)
        if len(deplist) > 0:
            deps.update({module_name: list(deplist)})

        for name in deplist:
            if name not in deps:
                subdeps = self.get_reverse_recursive_module_dependencies(
                    self.find_module_base(name), name, deps)
                if subdeps is not None:
                    deps.update(subdeps)
        return deps

    @QtCore.Slot(str, str)
    def get_recursive_module_dependencies(self, base, module_name):
        """
        Based on input connector declarations, determine which other modules are needed for a
        specific module to run.

        @param str base: module base package (hardware, logic or gui)
        @param str module_name: unique configured module name to get the dependencies for

        @return dict: module dependencies in the right format for the toposort function
        """
        deps = dict()
        if not self.is_module_defined(base, module_name):
            logger.error('{0} module {1}: no such module defined'.format(base, module_name))
            return None
        defined_module = self.tree['defined'][base][module_name]
        if 'connect' not in defined_module:
            return dict()
        if not isinstance(defined_module['connect'], dict):
            logger.error('{0} module {1}: connect is not a dictionary'.format(base, module_name))
            return None
        connections = defined_module['connect']
        deplist = set()
        for c in connections:
            if not isinstance(connections[c], str):
                logger.error('Value for class key is not a string.')
                return None
            if '.' in connections[c]:
                logger.warning('{0}.{1}: connection {2}: {3} has legacy format for connection '
                               'target'.format(base, module_name, c, connections[c]))
                destmod = connections[c].split('.')[0]
            else:
                destmod = connections[c]

            if all(destmod in self.tree['defined'][b] for b in ('hardware', 'logic')):
                logger.error('Unique name {0} is in both hardware and logic module list. '
                             'Connection is not well defined.'.format(destmod))
                return None
            elif destmod in self.tree['defined']['hardware']:
                destbase = 'hardware'
            elif destmod in self.tree['defined']['logic']:
                destbase = 'logic'
            else:
                logger.error('Unique name {0} is neither in hardware or logic module list. Cannot '
                             'connect {1} to it.'.format(connections[c], module_name))
                return None
            deplist.add(destmod)
            subdeps = self.get_recursive_module_dependencies(destbase, destmod)
            if subdeps is not None:
                deps.update(subdeps)
            else:
                return None
        if len(deplist) > 0:
            deps.update({module_name: list(deplist)})
        return deps

    def get_all_recursive_module_dependencies(self, all_mods):
        """
        Build a dependency tree for defined or loaded modules.

        @param dict all_mods: dictionary containing module bases (self.tree['loaded'] equivalent)

        @return dict: module dependencies in the right format for the toposort function
        """
        deps = dict()
        for mod_base, base_dict in all_mods.items():
            for module in base_dict:
                deps.update(self.get_recursive_module_dependencies(mod_base, module))
        return deps

    @QtCore.Slot(str, str)
    def start_module(self, base, name):
        """
        Figure out the module dependencies in terms of connections, load and activate module.
        If the module is already loaded, just activate it.
        If the module is an active GUI module, show its window.

        @param str base: module base package (hardware, logic or gui)
        @param str name: Unique module name as defined in config

        @return int: 0 on success, -1 on error
        """
        dependencies = self.get_recursive_module_dependencies(base, name)
        sorted_dependencies = toposort(dependencies)
        if len(sorted_dependencies) == 0:
            sorted_dependencies.append(name)

        for mod_key in sorted_dependencies:
            for mod_base in ('hardware', 'logic', 'gui'):
                # Do nothing if module is not defined in config (should not happen)
                if self.is_module_defined(mod_base, mod_key):
                    # If module is already loaded, activate it if needed and show GUI if possible
                    if self.is_module_loaded(mod_base, mod_key):
                        if self.tree['loaded'][mod_base][mod_key].module_state() == 'deactivated':
                            self.activate_module(mod_base, mod_key)
                        elif mod_base == 'gui':
                            self.tree['loaded'][mod_base][mod_key].show()
                    # If module is not loaded yet, load, configure and activate module
                    else:
                        success = self.load_and_configure_qudi_module(mod_base, mod_key)
                        if success < 0:
                            logger.warning('Stopping module loading after loading failure.')
                            return -1
                        elif success > 0:
                            logger.warning('Nonfatal loading error, going on.')
                        success = self.connect_qudi_module(mod_base, mod_key)
                        if success < 0:
                            logger.warning('Stopping loading module {0}.{1} after connection '
                                           'failure.'.format(mod_base, mod_key))
                            return -1
                        if self.is_module_loaded(mod_base, mod_key):
                            self.activate_module(mod_base, mod_key)
        return 0

    @QtCore.Slot(str, str)
    def stop_module(self, base, name):
        """
        Figure out the module dependencies in terms of connections and deactivate module.

        @param str base: module base package (hardware, logic or gui)
        @param str name: Unique module name as defined in config
        """
        dependencies = self.get_recursive_module_dependencies(base, name)
        sorted_dependencies = toposort(dependencies)
        if len(sorted_dependencies) == 0:
            sorted_dependencies.append(name)

        for mod_key in reversed(sorted_dependencies):
            for mod_base in ('hardware', 'logic', 'gui'):
                if self.is_module_loaded(mod_base, mod_key):
                    try:
                        deact = self.tree['loaded'][mod_base][mod_key].module_state.can(
                            'deactivate')
                    except:
                        deact = True
                    if deact:
                        logger.info('Deactivating module {0}.{1}'.format(mod_base, mod_key))
                        self.deactivate_module(mod_base, mod_key)

    @QtCore.Slot(str, str)
    def restart_module_recursive(self, base, name):
        """
        Figure out the module dependencies in terms of connections and reload and activate modules.

        @param str base: module base package (hardware, logic or gui)
        @param str name: Unique module name as defined in config
        """
        unload_dependencies = self.get_reverse_recursive_module_dependencies(base, name)
        sorted_unload_dependencies = toposort(unload_dependencies)
        unloaded_mods = list()
        if len(sorted_unload_dependencies) == 0:
            sorted_unload_dependencies.append(name)

        for mod_key in sorted_unload_dependencies:
            mod_base = self.find_module_base(mod_key)
            if self.is_module_loaded(mod_base, mod_key):
                success = self.reload_and_configure_qudi_module(mod_base, mod_key)
                if success < 0:
                    logger.warning('Stopping loading module {0}.{1} after loading error'
                                   ''.format(mod_base, mod_key))
                    return -1
                unloaded_mods.append(mod_key)

        for mod_key in reversed(unloaded_mods):
            mod_base = self.find_module_base(mod_key)
            if self.is_module_defined(mod_base, mod_key):
                if self.is_module_loaded(mod_base, mod_key):
                    success = self.connect_qudi_module(mod_base, mod_key)
                    if success < 0:
                        logger.warning('Stopping loading module {0}.{1} after connection error'
                                       ''.format(mod_base, mod_key))
                        return -1
                    self.activate_module(mod_base, mod_key)
                else:
                    success = self.load_and_configure_qudi_module(mod_base, mod_key)
                    if success < 0:
                        logger.warning('Stopping loading module {0}.{1} after loading error.'
                                       ''.format(mod_base, mod_key))
                        return -1
                    success = self.connect_qudi_module(mod_base, mod_key)
                    if success < 0:
                        logger.warning('Stopping loading module {0}.{1} after connection error'
                                       ''.format(mod_base, mod_key))
                        return -1
        return 0

    @QtCore.Slot()
    def start_all_modules(self):
        """
        Load, configure and connect all qudi modules from the currently loaded configuration and
        activate them.
        """
        dependencies = self.get_all_recursive_module_dependencies(self.tree['defined'])
        sorted_dependencies = toposort(dependencies)

        for module in sorted_dependencies:
            base = self.find_module_base(module)
            if self.start_module(base, module) < 0:
                break
        logger.info('Start all modules finished.')

    def get_status_dir(self):
        """
        Get the directory where the app state is saved, create it if necessary.

        @return str: path of application status directory
        """
        status_dir = os.path.join(self.config_dir, 'app_status')
        if not os.path.isdir(status_dir):
            os.makedirs(status_dir)
        return status_dir

    @QtCore.Slot(str, str, dict)
    def save_module_status_variables(self, base, module, variables):
        """
        If a module has status variables, save them to a file in the application status directory.

        @param str base: the module category
        @param str module: the unique module name
        @param dict variables: a dictionary of status variable names and values
        """
        if len(variables) > 0:
            try:
                status_dir = self.get_status_dir()
                class_name = self.tree['loaded'][base][module].__class__.__name__
                filename = os.path.join(status_dir,
                                        'status-{0}_{1}_{2}.cfg'.format(class_name, base, module))
                config.save(filename, variables)
            except:
                logger.exception('Failed to save status variables of module {0}.{1}:\n{2}'
                                 ''.format(base, module, repr(variables)))

    def load_module_status_variables(self, base, module):
        """
        If a status variable file exists for a module, load it into a dictionary.

        @param str base: the module category
        @param str module: the unique module name

        @return dict: dictionary of status variable names and values
        """
        variables = OrderedDict()
        try:
            status_dir = self.get_status_dir()
            class_name = self.tree['loaded'][base][module].__class__.__name__
            filename = os.path.join(status_dir,
                                    'status-{0}_{1}_{2}.cfg'.format(class_name, base, module))
            if os.path.isfile(filename):
                variables = config.load(filename)
        except:
            logger.exception('Failed to load status variables.')
        return variables

    @QtCore.Slot(str, str)
    def remove_module_status_file(self, base, module):
        """
        Removes (if present) the stored status variable file for given module with base.

        @param str base: the module base category ('gui', 'logic' or 'hardware')
        @param str module: the unique module name as specified in config
        """
        try:
            status_dir = self.get_status_dir()
            class_name = self.tree['defined'][base][module]['module.Class'].split('.')[-1]
            filename = os.path.join(status_dir,
                                    'status-{0}_{1}_{2}.cfg'.format(class_name, base, module))
            if os.path.isfile(filename):
                os.remove(filename)
        except:
            logger.exception('Failed to remove module status file.')

    @QtCore.Slot()
    def quit(self):
        """ Nicely request that all modules shut down. """
        locked_modules = False
        broken_modules = False
        for base, mods in self.tree['loaded'].items():
            for name, module in mods.items():
                try:
                    if module.module_state() == 'locked':
                        locked_modules = True
                except:
                    broken_modules = True
                if broken_modules and locked_modules:
                    break
        if locked_modules:
            if self.has_gui:
                self.sigShutdownAcknowledge.emit(locked_modules, broken_modules)
            else:
                # FIXME: console prompt here
                self.force_quit()
        else:
            self.force_quit()

    @QtCore.Slot()
    def force_quit(self):
        """ Stop all modules, no questions asked. """
        dependencies = self.get_all_recursive_module_dependencies(self.tree['loaded'])
        sorted_dependencies = toposort(dependencies)
        for modules in self.tree['loaded'].values():
            for module_name in modules.keys():
                if module_name not in sorted_dependencies:
                    sorted_dependencies.append(module_name)

        logger.debug('Deactivating {}'.format(sorted_dependencies))

        for module in reversed(sorted_dependencies):
            base = self.find_module_base(module)
            try:
                can_deactivate = self.tree['loaded'][base][module].can('deactivate')
            except:
                can_deactivate = True
            if can_deactivate:
                logger.info('Deactivating module {0}.{1}'.format(base, module))
                self.deactivate_module(base, module)
            QtCore.QCoreApplication.processEvents()
        self.sigManagerQuit.emit(self, False)

    @QtCore.Slot()
    def restart(self):
        """ Nicely request that all modules shut down for application restart. """
        for base, base_tree in self.tree['loaded'].items():
            for module_name in base_tree:
                try:
                    if self.is_module_active(base, module_name):
                        self.deactivate_module(base, module_name)
                except:
                    logger.exception(
                        'Module {0} failed to stop, continuing anyway.'.format(module_name))
                QtCore.QCoreApplication.processEvents()
        self.sigManagerQuit.emit(self, True)

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
        if not self.has_gui:
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
        if not self.has_gui or not self.gui.system_tray_icon.supportsMessages():
            logger.warning('{0}:\n{1}'.format(title, message))
            return
        if self.thread() is not QtCore.QThread.currentThread():
            logger.error('Pop-up notifications can only be invoked from GUI/main thread or via '
                         'queued connection.')
            return
        self.gui.system_tray_notification_bubble(title, message, time=time, icon=icon)
        return




