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

logger = logging.getLogger(__name__)

import os
import sys
import re
import time
import importlib

from qtpy import QtCore
from . import config

from .util.mutex import Mutex  # Mutex provides access serialization between threads
from .util.modules import toposort, is_base
from collections import OrderedDict
from .logger import register_exception_handler
from .threadmanager import ThreadManager

# try to import RemoteObjectManager. Might fail if rpyc is not installed.
try:
    from .remote import RemoteObjectManager
except ImportError:
    RemoteObjectManager = None
from .module import BaseMixin
from .connector import Connector


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
        """Constructor for Qudi main management class

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

        self.hasGui = not args.no_gui
        self.currentDir = None
        self.baseDir = None
        self.alreadyQuit = False
        self.remote_server = False

        try:
            # Initialize parent class QObject
            super().__init__(**kwargs)

            # Register exception handler
            register_exception_handler(self)

            # Thread management
            self.tm = ThreadManager()
            logger.debug('Main thread is {0}'.format(QtCore.QThread.currentThreadId()))

            # Task runner
            self.tr = None

            # Gui setup if we have gui
            if self.hasGui:
                import core.gui
                self.gui = core.gui.Gui()
                self.gui.setTheme('qudiTheme', os.path.join(self.getMainDir(), 'artwork', 'icons'))
                self.gui.setAppIcon()

            # Read in configuration file
            if args.config == '':
                config_file = self._getConfigFile()
            else:
                config_file = args.config
            self.configDir = os.path.dirname(config_file)
            self.readConfig(config_file)

            # check first if remote support is enabled and if so create RemoteObjectManager
            if RemoteObjectManager is None:
                logger.error('Remote modules disabled. Rpyc not installed.')
                self.rm = None
            else:
                self.rm = RemoteObjectManager(self)
                # Create remote module server if specified in config file
                if 'module_server' in self.tree['global']:
                    if not isinstance(self.tree['global']['module_server'], dict):
                        logger.error('"module_server" entry in "global" section of configuration'
                                     ' file is not a dictionary.')
                    else:
                        # new style
                        try:
                            server_address = self.tree['global']['module_server'].get(
                                'address',
                                'localhost')
                            server_port = self.tree['global']['module_server'].get(
                                'port', 12345)
                            certfile = self.tree['global']['module_server'].get(
                                'certfile', None)
                            if (certfile is not None) and not os.path.isabs(certfile):
                                certfile = os.path.abspath(os.path.join(self.configDir, certfile))
                            keyfile = self.tree['global']['module_server'].get('keyfile', None)
                            if (keyfile is not None) and not os.path.isabs(keyfile):
                                keyfile = os.path.abspath(os.path.join(self.configDir, keyfile))
                            cacertfile = self.tree['global']['module_server'].get('cacertfile',
                                                                                  None)
                            if (cacertfile is not None) and not os.path.isabs(cacertfile):
                                cacertfile = os.path.abspath(os.path.join(self.configDir,
                                                                          cacertfile))
                            self.rm.createServer(server_address, server_port, certfile, keyfile,
                                                 cacertfile)
                            # successfully started remote server
                            logger.info('Started server rpyc://{0}:{1}'.format(server_address,
                                                                               server_port))
                            self.remote_server = True
                        except:
                            logger.exception('Rpyc server could not be started.')
                elif 'serveraddress' in self.tree['global']:
                    logger.warning('Deprecated remote server settings. Please update to new '
                                   'style. See documentation.')

            logger.info('Qudi started.')

            # Load startup things from config here
            if 'startup' in self.tree['global']:
                # walk throug the list of loadable modules to be loaded on
                # startup and load them if appropriate
                for key in self.tree['global']['startup']:
                    if key in self.tree['defined']['hardware']:
                        self.startModule('hardware', key)
                        self.sigModulesChanged.emit()
                    elif key in self.tree['defined']['logic']:
                        self.startModule('logic', key)
                        self.sigModulesChanged.emit()
                    elif self.hasGui and key in self.tree['defined']['gui']:
                        self.startModule('gui', key)
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

    def getMainDir(self):
        """Returns the absolut path to the directory of the main software.

             @return string: path to the main tree of the software

        """
        return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def _getConfigFile(self):
        """ Search all the default locations to find a configuration file.

          @return sting: path to configuration file
        """
        path = self.getMainDir()
        # we first look for config/load.cfg which can point to another
        # config file using the "configfile" key
        loadConfigFile = os.path.join(path, 'config', 'load.cfg')
        if os.path.isfile(loadConfigFile):
            logger.info('load.cfg config file found at {0}'.format(
                loadConfigFile))
            try:
                confDict = config.load(loadConfigFile)
                if ('configfile' in confDict
                        and isinstance(confDict['configfile'], str)):
                    # check if this config file is existing
                    # try relative filenames
                    configFile = os.path.join(path, 'config',
                                              confDict['configfile'])
                    if os.path.isfile(configFile):
                        return configFile
                    # try absolute filename or relative to pwd
                    if os.path.isfile(confDict['configfile']):
                        return confDict['configfile']
                    else:
                        logger.critical('Couldn\'t find config file '
                                        'specified in load.cfg: {0}'.format(
                            confDict['configfile']))
            except Exception:
                logger.exception('Error while handling load.cfg.')
        # try config/example/custom.cfg next
        cf = os.path.join(path, 'config', 'example', 'custom.cfg')
        if os.path.isfile(cf):
            return cf
        # try config/example/default.cfg
        cf = os.path.join(path, 'config', 'example', 'default.cfg')
        if os.path.isfile(cf):
            return cf
        raise Exception('Could not find any config file.')

    def _appDataDir(self):
        """Get the system specific application data directory.

          @return string: path to application directory
        """
        # return the user application data directory
        if sys.platform == 'win32':
            # resolves to "C:/Documents and Settings/User/Application Data/"
            # on XP and "C:\User\Username\AppData\Roaming" on win7
            return os.path.join(os.environ['APPDATA'], 'qudi')
        elif sys.platform == 'darwin':
            return os.path.expanduser('~/Library/Preferences/qudi')
        else:
            return os.path.expanduser('~/.local/qudi')

    @QtCore.Slot(str)
    def readConfig(self, configFile):
        """Read configuration file and sort entries into categories.

          @param string configFile: path to configuration file
        """
        print("============= Starting Manager configuration from {0} =================".format(
            configFile))
        logger.info("Starting Manager configuration from {0}".format(
            configFile))
        cfg = config.load(configFile)
        self.configFile = configFile
        # Read modules, devices, and stylesheet out of config
        self.configure(cfg)

        print("\n============= Manager configuration complete =================\n")
        logger.info('Manager configuration complete.')

    @QtCore.Slot(dict)
    def configure(self, cfg):
        """Sort modules from configuration into categories

          @param dict cfg: dictionary from configuration file

          There are the main categories hardware, logic, gui, startup
          and global.
          Startup modules can be logic or gui and are loaded
          directly on 'startup'.
          'global' contains settings for the whole application.
          hardware, logic and gui contain configuration of and
          for loadable modules.
        """

        for key in cfg:
            try:
                # hardware
                if key == 'hardware' and cfg['hardware'] is not None:
                    for m in cfg['hardware']:
                        if 'module.Class' in cfg['hardware'][m]:
                            self.tree['defined']['hardware'][
                                m] = cfg['hardware'][m]
                        else:
                            logger.warning('    --> Ignoring device {0} -- '
                                           'no module specified'.format(m))

                # logic
                elif key == 'logic' and cfg['logic'] is not None:
                    for m in cfg['logic']:
                        if 'module.Class' in cfg['logic'][m]:
                            self.tree['defined']['logic'][m] = cfg['logic'][m]
                        else:
                            logger.warning('    --> Ignoring logic {0} -- '
                                           'no module specified'.format(m))

                # GUI
                elif key == 'gui' and cfg['gui'] is not None and self.hasGui:
                    for m in cfg['gui']:
                        if 'module.Class' in cfg['gui'][m]:
                            self.tree['defined']['gui'][m] = cfg['gui'][m]
                        else:
                            logger.warning('    --> Ignoring GUI {0} -- no '
                                           'module specified'.format(m))

                # Load on startup
                elif key == 'startup':
                    logger.warning('Old style startup loading not supported. '
                                   'Please update your config file.')

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
                                logger.warning('Global ''path'' '
                                               'configuration is neither str '
                                               ' nor list. Ignoring.')
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
                                        '{0}/{1}'.format(
                                            os.path.dirname(self.configFile),
                                            dir_name))
                                    if not os.path.isdir(path):
                                        path = ''
                                if path == '':
                                    logger.warning(
                                        'Error while adding qudi '
                                        'extension: Directory \'{0}\' '
                                        'does not exist.'
                                        ''.format(dir_name))
                                    continue
                                # check for __init__.py files within extension
                                # and issue warning if existing
                                for paths, dirs, files in os.walk(path):
                                    if '__init__.py' in files:
                                        logger.warning(
                                            'Warning: Extension {0} contains '
                                            '__init__.py. Expect unexpected '
                                            'behaviour. Hope you know what '
                                            'you are doing.'.format(path))
                                        break
                                # add directory to search path
                                logger.debug('Adding extension path: {0}'
                                             ''.format(path))
                                sys.path.insert(1 + ii, path)
                        elif m == 'startup':
                            self.tree['global']['startup'] = cfg[
                                'global']['startup']
                        elif m == 'stylesheet' and self.hasGui:
                            self.tree['global']['stylesheet'] = cfg['global']['stylesheet']
                            stylesheetpath = os.path.join(
                                self.getMainDir(),
                                'artwork',
                                'styles',
                                'application',
                                cfg['global']['stylesheet'])
                            if not os.path.isfile(stylesheetpath):
                                logger.warning(
                                    'Stylesheet not found at {0}'.format(stylesheetpath))
                                continue
                            self.gui.setStyleSheet(stylesheetpath)
                        else:
                            self.tree['global'][m] = cfg['global'][m]

                # Copy in any other configurations.
                # dicts are extended, all others are overwritten.
                else:
                    if isinstance(cfg[key], dict):
                        if key not in self.tree['config']:
                            self.tree['config'][key] = {}
                        for key2 in cfg[key]:
                            self.tree['config'][key][key2] = cfg[key][key2]
                    else:
                        self.tree['config'][key] = cfg[key]
            except:
                logger.exception('Error in configuration:')
        # print self.tree['config']
        self.sigConfigChanged.emit()

    def readConfigFile(self, fileName, missingOk=True):
        """Actually check if the configuration file exists and read it

          @param string fileName: path to configuration file
          @param bool missingOk: suppress exception if file does not exist

          @return dict: configuration from file
        """
        with self.lock:
            if os.path.isfile(fileName):
                return config.load(fileName)
            else:
                fileName = self.configFileName(fileName)
                if os.path.isfile(fileName):
                    return config.load(fileName)
                else:
                    if missingOk:
                        return {}
                    else:
                        raise Exception(
                            'Config file {0} not found.'.format(fileName))

    @QtCore.Slot(dict, str)
    def writeConfigFile(self, data, fileName):
        """Write a file into the currently used config directory.

          @param dict data: dictionary to write into file
          @param string fileName: path for filr to be written
        """
        with self.lock:
            fileName = self.configFileName(fileName)
            dirName = os.path.dirname(fileName)
            if not os.path.exists(dirName):
                os.makedirs(dirName)
            config.save(fileName, data)

    def configFileName(self, name):
        """Get the full path of a configuration file from its filename.

          @param string name: filename of file in configuration directory

          @return string: full path to file
        """
        with self.lock:
            return os.path.join(self.configDir, name)

    @QtCore.Slot(str)
    def saveConfig(self, filename):
        """Save configuration to a file.

          @param str filename: path where the config flie should be saved
        """
        saveconfig = OrderedDict()
        saveconfig.update(self.tree['defined'])
        saveconfig['global'] = self.tree['global']

        self.writeConfigFile(saveconfig, filename)
        logger.info('Saved configuration to {0}'.format(filename))

    @QtCore.Slot(str, bool)
    def loadConfig(self, filename, restart=False):
        """ Load configuration from file.

          @param str filename: path of file to be loaded
          @param bool restart: should qudi be restarted after the reload of the config
        """
        maindir = self.getMainDir()
        configdir = os.path.join(maindir, 'config')
        loadFile = os.path.join(configdir, 'load.cfg')
        if filename.startswith(configdir):
            filename = re.sub(
                '^' + re.escape('/'),
                '',
                re.sub(
                    '^' + re.escape(configdir),
                    '',
                    filename)
            )
        loadData = {'configfile': filename}
        config.save(loadFile, loadData)
        logger.info('Set loaded configuration to {0}'.format(filename))
        if restart:
            logger.info('Restarting Qudi after configuration reload.')
            self.realQuit(restart=True)

    @QtCore.Slot(str, str)
    def reloadConfigPart(self, base, mod):
        """Reread the configuration file and update the internal configuration of module

        @params str modname: name of module where config file should be reloaded.
        """
        configFile = self._getConfigFile()
        cfg = self.readConfigFile(configFile)
        try:
            if cfg[base][mod]['module.Class'] == self.tree['defined'][base][mod]['module.Class']:
                self.tree['defined'][base][mod] = cfg[base][mod]
        except KeyError:
            pass

    ##################
    # Module loading #
    ##################

    def importModule(self, baseName, module):
        """Load a python module that is a loadable Qudi module.

          @param string baseName: the module base package (hardware, logic, or gui)
          @param string module: the python module name inside the base package

          @return object: the loaded python module
        """

        logger.info('Loading module ".{0}.{1}"'.format(baseName, module))
        if not is_base(baseName):
            raise Exception('You are trying to cheat the '
                            'system with some category {0}'.format(baseName))

        # load the python module
        mod = importlib.__import__('{0}.{1}'.format(
            baseName, module), fromlist=['*'])
        # print('refcnt:', sys.getrefcount(mod))
        return mod

    def configureModule(self, moduleObject, baseName, className, instanceName,
                        configuration=None):
        """Instantiate an object from the class that makes up a Qudi module
           from a loaded python module object.

          @param object moduleObject: loaded python module
          @param string baseName: module base package (hardware, logic or gui)
          @param string className: name of the class we want an object from
                                 (same as module name usually)
          @param string instanceName: unique name thet the Qudi module instance
                                 was given in the configuration
          @param dict configuration: configuration options for the Qudi module

          @return object: Qudi module instance (object of the class derived
                          from Base)

          This method will add the resulting Qudi module instance to internal
          bookkeeping.
        """
        if configuration is None:
            configuration = {}
        logger.info('Configuring {0} as {1}'.format(
            className, instanceName))
        with self.lock:
            if is_base(baseName):
                if self.isModuleLoaded(baseName, instanceName):
                    raise Exception(
                        '{0} already exists with name {1}'.format(baseName, instanceName))
            else:
                raise Exception('You are trying to cheat the system with some '
                                'category {0}'.format(baseName))

        if configuration is None:
            configuration = {}

        # get class from module by name
        # print(moduleObject, className)
        modclass = getattr(moduleObject, className)

        # FIXME: Check if the class we just obtained has the right inheritance
        if not issubclass(modclass, BaseMixin):
            raise Exception('Bad inheritance, for instance {0!s} from {1!s}.{2!s}.'.format(
                instanceName, baseName, className))

        # Create object from class
        instance = modclass(manager=self, name=instanceName, config=configuration)

        with self.lock:
            self.tree['loaded'][baseName][instanceName] = instance

        self.sigModulesChanged.emit()
        return instance

    def connectModule(self, base, mkey):
        """ Connects the given module in mkey to main object with the help
            of base.

          @param string base: module base package (hardware, logic or gui)
          @param string mkey: module which you want to connect

          @return int: 0 on success, -1 on failure
        """
        thismodule = self.tree['defined'][base][mkey]
        if not self.isModuleLoaded(base, mkey):
            logger.error('Loading of {0} module {1} as {2} was not '
                         'successful, not connecting it.'.format(
                base, thismodule['module.Class'], mkey))
            return -1
        loaded_module = self.tree['loaded'][base][mkey]
        if 'connect' not in thismodule:
            return 0
        if not isinstance(loaded_module.connectors, OrderedDict):
            logger.error('Connectors attribute of module {0}.{1} is not a '
                         'dictionary.'.format(base, mkey))
            return -1
        if 'module.Class' not in thismodule:
            logger.error('Connection configuration of module {0}.{1} '
                         'is broken: no module defined.'.format(
                base, mkey))
            return -1
        if not isinstance(thismodule['connect'], OrderedDict):
            logger.error('Connection configuration of module {0}.{1} '
                         'is broken: connect is not a dictionary.'
                         ''.format(base, mkey))
            return -1

        # lets go through all connections provided in configuration
        connections = thismodule['connect']
        for c in connections:
            connectors = loaded_module.connectors
            if c not in connectors:
                logger.error('Connector {0}.{1}.{2} is supposed to get '
                             'connected but is not declared in the module '
                             'class.'.format(c, base, mkey))
                continue
            # new-style connector
            if isinstance(connectors[c], Connector):
                pass
            # legacy connector
            elif isinstance(connectors[c], OrderedDict):
                if 'class' not in connectors[c]:
                    logger.error('{0}.{1}.{2}: No class key in connection declaration.'
                                 ''.format(c, base, mkey))
                    continue
                if not isinstance(connectors[c]['class'], str):
                    logger.error('{0}.{1}.{2}: Value {3} for class key is not a string.'
                                 ''.format(c, base, mkey, connectors[c]['class']))
                    continue
                if 'object' not in connectors[c]:
                    logger.error('{0}.{1}.{2}: No object key in connection declaration.'
                                 ''.format(c, base, mkey))
                    continue
                if connectors[c]['object'] is not None:
                    logger.warning('Connector {0}.{1}.{2} is already connected.'
                                   ''.format(c, base, mkey))
                    continue
                logger.warning('Connector {0} in {1}.{2} is a legacy connector.\n'
                               'Use core.module.Connector to declare connectors.'
                               ''.format(c, base, mkey))
            else:
                logger.error('{0}.{1}.{2}: Connector is no dictionary or Connector.'
                             ''.format(c, base, mkey))
                continue
            if not isinstance(connections[c], str):
                logger.error('Connector configuration {0}.{1}.{2} '
                             'is broken since it is not a string.'
                             ''.format(base, mkey, c))
                continue
            if '.' in connections[c]:
                logger.warning('Connector configuration {0}.{1}.{2} has '
                               'legacy format since it contains a dot.'
                               ''.format(base, mkey, c))
                logger.error('{0}.{1}.{2}: Connector is no dictionary.'
                             ''.format(c, base, mkey))
                continue
                destmod = connections[c].split('.')[0]
            else:
                destmod = connections[c]
            destbase = ''
            # check if module exists at all
            if (destmod not in self.tree['loaded']['gui'] and
                    destmod not in self.tree['loaded']['hardware'] and
                    destmod not in self.tree['loaded']['logic']):
                logger.error('Cannot connect {0}.{1}.{2} to module {3}. '
                             'Module does not exist.'.format(
                    base, mkey, c, destmod))
                continue
            # check that module exists only once
            if not ((destmod in self.tree['loaded']['gui']) ^
                    (destmod in self.tree['loaded']['hardware']) ^
                    (destmod in self.tree['loaded']['logic'])):
                logger.error('Cannot connect {0}.{1}.{2} to module {3}. '
                             'Module exists more than once.'.format(
                    base, mkey, c, destmod))
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
                        ''.format(base, mkey, c, destbase, destmod))
            # new-style connector
            if isinstance(connectors[c], Connector):
                connectors[c].connect(self.tree['loaded'][destbase][destmod])
            # legacy connector
            elif isinstance(connectors[c], dict):
                connectors[c]['object'] = self.tree['loaded'][destbase][destmod]
            else:
                logger.error(
                    'Connector {0} has wrong type even though we checked before.'
                    ''.format(c))

        # check that all connectors are connected
        for c, v in self.tree['loaded'][base][mkey].connectors.items():
            # new-style connector
            if isinstance(v, Connector) and not v.is_connected and not v.optional:
                logger.error('Connector {0} of module {1}.{2} is not '
                             'connected. Connection not complete.'.format(
                    c, base, mkey))
                return -1
            # legacy connector
            elif isinstance(v, dict) and v['object'] is None:
                logger.error('Connector {0} of module {1}.{2} is not '
                             'connected. Connection not complete.'.format(
                    c, base, mkey))
                return -1
        return 0

    def loadConfigureModule(self, base, key):
        """Loads the configuration Module in key with the help of base class.

          @param string base: module base package (hardware, logic or gui)
          @param string key: module which is going to be loaded

          @return int: 0 on success, -1 on fatal error, 1 on error
        """
        defined_module = self.tree['defined'][base][key]
        if 'module.Class' in defined_module:
            if 'remote' in defined_module:
                if self.rm is None:
                    logger.error('Remote module functionality disabled. Rpyc not installed.')
                    return -1
                if not isinstance(defined_module['remote'], str):
                    logger.error('Remote URI of {0} module {1} not a string.'.format(base, key))
                    return -1
                try:
                    certfile = defined_module.get('certfile', None)
                    keyfile = defined_module.get('keyfile', None)
                    cacertsfile = defined_module.get('cacerts', None)
                    instance = self.rm.getRemoteModuleUrl(
                        defined_module['remote'],
                        certfile=certfile,
                        keyfile=keyfile,
                        cacertsfile=cacertsfile)
                    logger.info('Remote module {0} loaded as {1}.{2}.'
                                ''.format(defined_module['remote'], base, key))
                    with self.lock:
                        if is_base(base):
                            self.tree['loaded'][base][key] = instance
                            self.sigModulesChanged.emit()
                        else:
                            raise Exception(
                                'You are trying to cheat the system with some category {0}'
                                ''.format(base))
                except:
                    logger.exception('Error while loading {0} module: {1}'.format(base, key))
                    return -1
            else:
                try:
                    # class_name is the last part of the config entry
                    class_name = re.split('\.', defined_module['module.Class'])[-1]
                    # module_name is the whole line without this last part (and
                    # with the trailing dot removed also)
                    module_name = re.sub(
                        '.' + class_name + '$',
                        '',
                        defined_module['module.Class'])

                    modObj = self.importModule(base, module_name)

                    # Ensure that the namespace of a module is reloaded before 
                    # instantiation. That will not harm anything.
                    # Even if the import is successful an error might occur 
                    # during instantiation. E.g. in an abc metaclass, 
                    # methods might be missing in a derived interface file.
                    # Reloading the namespace will prevent the need to restart 
                    # Qudi, if a module instantiation was not successful upon 
                    # load.
                    importlib.reload(modObj)  # keep the namespace of module up to date

                    self.configureModule(modObj, base, class_name, key, defined_module)
                    if 'remoteaccess' in defined_module and defined_module['remoteaccess']:
                        if self.rm is None:
                            logger.error('Remote module sharing functionality disabled. Rpyc not'
                                         ' installed.')
                            return 1
                        if not self.remote_server:
                            logger.error('Remote module sharing does not work '
                                         'as no server configured or server startup failed earlier.'
                                         ' Check your configuration and log.')
                            return 1
                        self.rm.shareModule(key, self.tree['loaded'][base][key])
                except:
                    logger.exception(
                        'Error while loading {0} module: {1}'.format(base, key))
                    return -1
        else:
            logger.error('Missing module declaration in configuration: '
                         '{0}.{1}'.format(base, key))
            return -1
        return 0

    def reloadConfigureModule(self, base, key):
        """Reloads the configuration module in key with the help of base class.

          @param string base: module base package (hardware, logic or gui)
          @param string key: module which is going to be loaded

          @return int: 0 on success, -1 on failure
        """
        defined_module = self.tree['defined'][base][key]
        if 'remote' in defined_module:
            if self.rm is None:
                logger.error('Remote functionality not working, check your log.')
                return -1
            if not isinstance(defined_module['remote'], str):
                logger.error('Remote URI of {0} module {1} not a string.'.format(base, key))
                return -1
            try:
                instance = self.rm.getRemoteModuleUrl(defined_module['remote'])
                logger.info('Remote module {0} loaded as .{1}.{2}.'
                            ''.format(defined_module['remote'], base, key))
                with self.lock:
                    if is_base(base):
                        self.tree['loaded'][base][key] = instance
                        self.sigModulesChanged.emit()
                    else:
                        raise Exception(
                            'You are trying to cheat the system with some category {0}'
                            ''.format(base))
            except:
                logger.exception('Error while loading {0} module: {1}'.format(base, key))
        elif (key in self.tree['loaded'][base]
              and 'module.Class' in defined_module):
            try:
                # state machine: deactivate
                if self.isModuleActive(base, key):
                    self.deactivateModule(base, key)
            except:
                logger.exception('Error while deactivating {0} module: {1}'.format(base, key))
                return -1
            try:
                with self.lock:
                    self.tree['loaded'][base].pop(key, None)
                # reload config part associated with module
                self.reloadConfigPart(base, key)
                # class_name is the last part of the config entry
                class_name = re.split('\.', defined_module['module.Class'])[-1]
                # module_name is the whole line without this last part (and
                # with the trailing dot removed also)
                module_name = re.sub(
                    '.' + class_name + '$',
                    '',
                    defined_module['module.Class'])

                modObj = self.importModule(base, module_name)
                # des Pudels Kern
                importlib.reload(modObj)
                self.configureModule(modObj, base, class_name, key, defined_module)
            except:
                logger.exception('Error while reloading {0} module: {1}'.format(base, key))
                return -1
        else:
            logger.error('Module not loaded or not loadable (missing module '
                         'declaration in configuration): {0}.{1}'.format(base, key))
        return 0

    def isModuleDefined(self, base, name):
        """Check if module is present in module definition.
          @param str base: module base package
          @param str name: unique module name
          @return bool: module is present in definition
        """
        return (
                is_base(base)
                and base in self.tree['defined']
                and name in self.tree['defined'][base]
        )

    def isModuleLoaded(self, base, name):
        """Check if module was loaded.
          @param str base: module base package
          @param str name: unique module name
          @return bool: module is loaded
        """
        return (
                is_base(base)
                and base in self.tree['loaded']
                and name in self.tree['loaded'][base]
        )

    def isModuleActive(self, base, name):
        """Returns whether a given module is active.

          @param string base: module base package (hardware, logic or gui)
          @param string key: module which is going to be activated.
        """
        if not self.isModuleLoaded(base, name):
            logger.error('{0} module {1} not loaded.'.format(base, name))
            return False
        return self.tree['loaded'][base][name].module_state() in ('idle', 'running', 'locked')

    def findBase(self, name):
        """ Find base for a given module name.
          @param str name: module name

          @return str: base name
        """
        for base in ('hardware', 'logic', 'gui'):
            if name in self.tree['defined'][base]:
                return base
        raise KeyError(name)

    @QtCore.Slot(str, str)
    def activateModule(self, base, name):
        """Activate the module given in key with the help of base class.

          @param string base: module base package (hardware, logic or gui)
          @param string name: module which is going to be activated.

        """
        if not self.isModuleLoaded(base, name):
            logger.error('{0} module {1} not loaded.'.format(base, name))
            return
        module = self.tree['loaded'][base][name]
        if module.module_state() != 'deactivated' and (
                self.isModuleDefined(base, name)
                and 'remote' in self.tree['defined'][base][name]):
            logger.debug('No need to activate remote module {0}.{1}.'.format(base, name))
            return
        if module.module_state() != 'deactivated':
            logger.error('{0} module {1} not deactivated'.format(base, name))
            return
        try:
            module.setStatusVariables(self.loadStatusVariables(base, name))
            # start main loop for qt objects
            if module.is_module_threaded:
                modthread = self.tm.newThread('mod-{0}-{1}'.format(base, name))
                module.moveToThread(modthread)
                modthread.start()
                success = QtCore.QMetaObject.invokeMethod(
                    module.module_state,
                    'trigger',
                    QtCore.Qt.BlockingQueuedConnection,
                    QtCore.Q_RETURN_ARG(bool),
                    QtCore.Q_ARG(str, 'activate'))
            else:
                success = module.module_state.activate()  # runs on_activate in main thread
            logger.debug('Activation success: {}'.format(success))
        except:
            logger.exception(
                '{0} module {1}: error during activation:'.format(base, name))
        QtCore.QCoreApplication.instance().processEvents()

    @QtCore.Slot(str, str)
    def deactivateModule(self, base, name):
        """Activated the module given in key with the help of base class.

          @param string base: module base package (hardware, logic or gui)
          @param string name: module which is going to be activated.

        """
        logger.info('Deactivating {0}.{1}'.format(base, name))
        if not self.isModuleLoaded(base, name):
            logger.error('{0} module {1} not loaded.'.format(base, name))
            return
        module = self.tree['loaded'][base][name]
        try:
            if not self.isModuleActive(base, name):
                logger.error('{0} module {1} is not activated.'.format(base, name))
                return
        except:
            logger.exception(
                'Error while getting status of {0}, removing reference without deactivation.'
                ''.format(name))
            with self.lock:
                self.tree['loaded'][base].pop(name)
            return
        try:
            if module.is_module_threaded:
                success = QtCore.QMetaObject.invokeMethod(
                    module.module_state,
                    'trigger',
                    QtCore.Qt.BlockingQueuedConnection,
                    QtCore.Q_RETURN_ARG(bool),
                    QtCore.Q_ARG(str, 'deactivate'))

                QtCore.QMetaObject.invokeMethod(
                    module,
                    'moveToThread',
                    QtCore.Qt.BlockingQueuedConnection,
                    QtCore.Q_ARG(QtCore.QThread, self.tm.thread))
                self.tm.quitThread('mod-{0}-{1}'.format(base, name))
                self.tm.joinThread('mod-{0}-{1}'.format(base, name))
            else:
                success = module.module_state.deactivate()  # runs on_deactivate in main thread

            self.saveStatusVariables(base, name, module.getStatusVariables())
            logger.debug('Deactivation success: {}'.format(success))
        except:
            logger.exception('{0} module {1}: error during deactivation:'.format(base, name))
        QtCore.QCoreApplication.instance().processEvents()

    @QtCore.Slot(str, str)
    def getReverseRecursiveModuleDependencies(self, base, module, deps=None):
        """ Based on input connector declarations, determine in which other modules need to be removed when stopping.

          @param str base: Module category
          @param str key: Unique configured module name for module where we want the dependencies

          @return dict: module dependencies in the right format for the toposort function
        """
        if deps is None:
            deps = dict()
        if not self.isModuleDefined(base, module):
            logger.error('{0} module {1}: no such module defined'.format(base, module))
            return None

        deplist = set()
        for bname, base in self.tree['defined'].items():
            for mname, mod in base.items():
                if 'connect' not in mod:
                    continue
                connections = mod['connect']
                if not isinstance(connections, OrderedDict):
                    logger.error('{0} module {1}: connect is not a dictionary'.format(bname, mname))
                    continue
                for cname, connection in connections.items():
                    conn = connection
                    if '.' in connection:
                        conn = connection.split('.')[0]
                        logger.warning(
                            '{0}.{1}: connection {2}: {3} has legacy '
                            ' format for connection target'
                            ''.format(bname, mname, cname, connection))
                    if conn == module:
                        deplist.add(mname)
        if len(deplist) > 0:
            deps.update({module: list(deplist)})

        for name in deplist:
            if name not in deps:
                subdeps = self.getReverseRecursiveModuleDependencies(self.findBase(name), name, deps)
                if subdeps is not None:
                    deps.update(subdeps)

        return deps

    @QtCore.Slot(str, str)
    def getRecursiveModuleDependencies(self, base, key):
        """ Based on input connector declarations, determine in which other modules are needed for a specific module to run.

          @param str base: Module category
          @param str key: Unique configured module name for module where we want the dependencies

          @return dict: module dependencies in the right format for the toposort function
        """
        deps = dict()
        if not self.isModuleDefined(base, key):
            logger.error('{0} module {1}: no such module defined'.format(base, key))
            return None
        defined_module = self.tree['defined'][base][key]
        if 'connect' not in defined_module:
            return dict()
        if not isinstance(defined_module['connect'], OrderedDict):
            logger.error('{0} module {1}: connect is not a dictionary'.format(base, key))
            return None
        connections = defined_module['connect']
        deplist = set()
        for c in connections:
            if not isinstance(connections[c], str):
                logger.error('Value for class key is not a string.')
                return None
            if '.' in connections[c]:
                logger.warning('{0}.{1}: connection {2}: {3} has legacy '
                               ' format for connection target'.format(
                    base, key, c, connections[c]))
                destmod = connections[c].split('.')[0]
            else:
                destmod = connections[c]
            destbase = ''
            if destmod in self.tree['defined']['hardware'] and destmod in self.tree['defined']['logic']:
                logger.error('Unique name {0} is in both hardware and '
                             'logic module list. Connection is not well defined.'
                             ''.format(destmod))
                return None
            elif destmod in self.tree['defined']['hardware']:
                destbase = 'hardware'
            elif destmod in self.tree['defined']['logic']:
                destbase = 'logic'
            else:
                logger.error('Unique name {0} is neither in hardware or '
                             'logic module list. Cannot connect {1} '
                             'to it.'.format(connections[c], key))
                return None
            deplist.add(destmod)
            subdeps = self.getRecursiveModuleDependencies(destbase, destmod)
            if subdeps is not None:
                deps.update(subdeps)
            else:
                return None
        if len(deplist) > 0:
            deps.update({key: list(deplist)})
        return deps

    def getAllRecursiveModuleDependencies(self, allmods):
        """ Build a dependency tre for defined or loaded modules.
          @param dict allmods: dictionary containing module bases (self.tree['loaded'] equivalent)

          @return dict:  module dependencies in the right format for the toposort function
        """
        deps = {}
        for mbase, bdict in allmods.items():
            for module in bdict:
                deps.update(self.getRecursiveModuleDependencies(mbase, module))
        return deps

    @QtCore.Slot(str, str)
    def startModule(self, base, key):
        """ Figure out the module dependencies in terms of connections, load and activate module.

          @param str base: Module category
          @param str key: Unique module name

          @return int: 0 on success, -1 on error

            If the module is already loaded, just activate it.
            If the module is an active GUI module, show its window.
        """

        deps = self.getRecursiveModuleDependencies(base, key)
        sorteddeps = toposort(deps)
        if len(sorteddeps) == 0:
            sorteddeps.append(key)

        for mkey in sorteddeps:
            for mbase in ('hardware', 'logic', 'gui'):
                if mkey in self.tree['defined'][mbase] and mkey not in self.tree['loaded'][mbase]:
                    success = self.loadConfigureModule(mbase, mkey)
                    if success < 0:
                        logger.warning('Stopping module loading after loading failure.')
                        return -1
                    elif success > 0:
                        logger.warning('Nonfatal loading error, going on.')
                    success = self.connectModule(mbase, mkey)
                    if success < 0:
                        logger.warning('Stopping loading module {0}.{1} after '
                                       'connection failure.'.format(mbase, mkey))
                        return -1
                    if mkey in self.tree['loaded'][mbase]:
                        self.activateModule(mbase, mkey)
                elif mkey in self.tree['defined'][mbase] and mkey in self.tree['loaded'][mbase]:
                    if self.tree['loaded'][mbase][mkey].module_state() == 'deactivated':
                        self.activateModule(mbase, mkey)
                    elif (self.tree['loaded'][mbase][mkey].module_state() != 'deactivated' and
                          mbase == 'gui'):
                        self.tree['loaded'][mbase][mkey].show()
        return 0

    @QtCore.Slot(str, str)
    def stopModule(self, base, key):
        """ Figure out the module dependencies in terms of connections and deactivate module.

          @param str base: Module category
          @param str key: Unique module name

        """
        deps = self.getRecursiveModuleDependencies(base, key)
        sorteddeps = toposort(deps)
        if len(sorteddeps) == 0:
            sorteddeps.append(key)

        for mkey in reversed(sorteddeps):
            for mbase in ('hardware', 'logic', 'gui'):
                if mkey in self.tree['defined'][mbase] and mkey in self.tree['loaded'][mbase]:
                    try:
                        deact = self.tree['loaded'][mbase][mkey].module_state.can('deactivate')
                    except:
                        deact = True
                    if deact:
                        logger.info('Deactivating module {0}.{1}'.format(mbase, mkey))
                        self.deactivateModule(mbase, mkey)

    @QtCore.Slot(str, str)
    def restartModuleRecursive(self, base, key):
        """ Figure out the module dependencies in terms of connections, reload and activate module.

          @param str base: Module category
          @param str key: Unique configured module name

        """
        unload_deps = self.getReverseRecursiveModuleDependencies(base, key)
        sorted_u_deps = toposort(unload_deps)
        unloaded_mods = []
        if len(sorted_u_deps) == 0:
            sorted_u_deps.append(key)

        for mkey in sorted_u_deps:
            mbase = self.findBase(mkey)
            if mkey in self.tree['loaded'][mbase]:
                success = self.reloadConfigureModule(mbase, mkey)
                if success < 0:
                    logger.warning('Stopping loading module {0}.{1} after '
                                   'loading error'.format(mbase, mkey))
                    return -1
                unloaded_mods.append(mkey)

        for mkey in reversed(unloaded_mods):
            mbase = self.findBase(mkey)
            if mkey in self.tree['defined'][mbase] and mkey not in self.tree['loaded'][mbase]:
                success = self.loadConfigureModule(mbase, mkey)
                if success < 0:
                    logger.warning('Stopping loading module {0}.{1} after '
                                   'loading error.'.format(mbase, mkey))
                    return -1
                success = self.connectModule(mbase, mkey)
                if success < 0:
                    logger.warning('Stopping loading module {0}.{1} after '
                                   'connection error'.format(mbase, mkey))
                    return -1

            if mkey in self.tree['loaded'][mbase]:
                if mkey in self.tree['loaded'][mbase]:
                    success = self.connectModule(mbase, mkey)
                    if success < 0:
                        logger.warning('Stopping loading module {0}.{1} after '
                                       'connection error'.format(mbase, mkey))
                        return -1
                    self.activateModule(mbase, mkey)
        return 0

    @QtCore.Slot()
    def startAllConfiguredModules(self):
        """Connect all Qudi modules from the currently loaded configuration and
            activate them.
        """
        deps = self.getAllRecursiveModuleDependencies(self.tree['defined'])
        sorteddeps = toposort(deps)

        for module in sorteddeps:
            base = self.findBase(module)
            if self.startModule(base, module) < 0:
                break

        logger.info('Start all modules finished.')

    def getStatusDir(self):
        """ Get the directory where the app state is saved, create it if necessary.

          @return str: path of application status directory
        """
        appStatusDir = os.path.join(self.configDir, 'app_status')
        if not os.path.isdir(appStatusDir):
            os.makedirs(appStatusDir)
        return appStatusDir

    @QtCore.Slot(str, str, dict)
    def saveStatusVariables(self, base, module, variables):
        """ If a module has status variables, save them to a file in the application status directory.

          @param str base: the module category
          @param str module: the unique module name
          @param dict variables: a dictionary of status variable names and values
        """
        if len(variables) > 0:
            try:
                statusdir = self.getStatusDir()
                classname = self.tree['loaded'][base][module].__class__.__name__
                filename = os.path.join(statusdir,
                                        'status-{0}_{1}_{2}.cfg'.format(classname, base, module))
                config.save(filename, variables)
            except:
                print(variables)
                logger.exception('Failed to save status variables of module '
                                 '{0}.{1}:\n{2}'.format(base, module, repr(variables)))

    def loadStatusVariables(self, base, module):
        """ If a status variable file exists for a module, load it into a dictionary.

          @param str base: the module category
          @param str module: the unique mduel name

          @return dict: dictionary of satus variable names and values
        """
        try:
            statusdir = self.getStatusDir()
            classname = self.tree['loaded'][base][module].__class__.__name__
            filename = os.path.join(
                statusdir, 'status-{0}_{1}_{2}.cfg'.format(classname, base, module))
            if os.path.isfile(filename):
                variables = config.load(filename)
            else:
                variables = OrderedDict()
        except:
            logger.exception('Failed to load status variables.')
            variables = OrderedDict()
        return variables

    @QtCore.Slot(str, str)
    def removeStatusFile(self, base, module):
        try:
            statusdir = self.getStatusDir()
            classname = self.tree['defined'][base][
                module]['module.Class'].split('.')[-1]
            filename = os.path.join(
                statusdir, 'status-{0}_{1}_{2}.cfg'.format(classname, base, module))
            if os.path.isfile(filename):
                os.remove(filename)
        except:
            logger.exception('Failed to remove module status file.')

    @QtCore.Slot()
    def quit(self):
        """Nicely request that all modules shut down."""
        lockedmodules = False
        brokenmodules = False
        for base, mods in self.tree['loaded'].items():
            for name, module in mods.items():
                try:
                    state = module.module_state()
                    if state == 'locked':
                        lockedmodules = True
                except:
                    brokenmodules = True
        if lockedmodules:
            if self.hasGui:
                self.sigShutdownAcknowledge.emit(lockedmodules, brokenmodules)
            else:
                # FIXME: console prompt here
                self.realQuit()
        else:
            self.realQuit()

    @QtCore.Slot()
    @QtCore.Slot(bool)
    def realQuit(self, restart=False):
        """ Stop all modules, no questions asked. """
        deps = self.getAllRecursiveModuleDependencies(self.tree['loaded'])
        sorteddeps = toposort(deps)
        for b, mods in self.tree['loaded'].items():
            for m in mods.keys():
                if m not in sorteddeps:
                    sorteddeps.append(m)

        logger.debug('Deactivating {}'.format(sorteddeps))

        for module in reversed(sorteddeps):
            base = self.findBase(module)
            try:
                deact = self.tree['loaded'][base][module].can('deactivate')
            except:
                deact = True
            if deact:
                logger.info('Deactivating module {0}.{1}'.format(base, module))
                self.deactivateModule(base, module)
            QtCore.QCoreApplication.processEvents()
        self.sigManagerQuit.emit(self, bool(restart))

    @QtCore.Slot(object)
    def registerTaskRunner(self, reference):
        """ Register/deregister/replace a task runner object.

        @param object reference: reference to a task runner or null class

        If a reference is passed that is not None, it is kept and passed out as the task runner instance.
        If a None is passed, the reference is discarded.
        Id another reference is passed, the current one is replaced.

        """
        with self.lock:
            if self.tr is None and reference is not None:
                self.tr = reference
                logger.info('Task runner registered.')
            elif self.tr is not None and reference is None:
                logger.info('Task runner removed.')
            elif self.tr is None and reference is None:
                logger.error('You tried to remove the task runner but none was registered.')
            else:
                logger.warning('Replacing task runner.')
