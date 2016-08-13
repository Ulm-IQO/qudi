# -*- coding: utf-8 -*-
"""
This file contains the QuDi Manager class.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

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
import gc
import glob
import re
import time
import atexit
import weakref
import importlib
import threading
import socket

from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.reload as reload
from . import config

from .util import ptime
from .util.mutex import Mutex   # Mutex provides access serialization between threads
from collections import OrderedDict
import pyqtgraph as pg
from .logger import register_exception_handler
from .threadmanager import ThreadManager
from .remote import RemoteObjectManager
from .base import Base

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
    sigShowManager = QtCore.Signal()

    def __init__(self, args, **kwargs):
        """Constructor for QuDi main management class

          @param args: argparse command line arguments
        """
        # used for keeping some basic methods thread-safe
        self.lock = Mutex(recursive=True)
        self.tree = OrderedDict()
        self.tree['config'] = OrderedDict()
        self.tree['start'] = OrderedDict()
        self.tree['defined'] = OrderedDict()
        self.tree['loaded'] = OrderedDict()

        self.tree['defined']['hardware'] = OrderedDict()
        self.tree['loaded']['hardware'] = OrderedDict()

        self.tree['start']['gui'] = OrderedDict()
        self.tree['defined']['gui'] = OrderedDict()
        self.tree['loaded']['gui'] = OrderedDict()

        self.tree['start']['logic'] = OrderedDict()
        self.tree['defined']['logic'] = OrderedDict()
        self.tree['loaded']['logic'] = OrderedDict()

        self.tree['global'] = OrderedDict()
        self.tree['global']['startup'] = list()

        self.hasGui = not args.no_gui
        self.currentDir = None
        self.baseDir = None
        self.alreadyQuit = False
        self.remoteServer = True

        try:
            # Initialize parent class QObject
            super().__init__(**kwargs)

            # Register exception handler
            register_exception_handler(self)

            # Thread management
            self.tm = ThreadManager()
            logger.debug('Main thread is {0}'.format(threading.get_ident()))

            # Task runner
            self.tr = None

            # Gui setup if we have gui
            if self.hasGui:
                import core.gui
                self.gui = core.gui.Gui()
                self.gui.makePyQtGraphQApplication()
                self.gui.setTheme()
                self.gui.setAppIcon()

            # Read in configuration file
            if args.config == '':
                config_file = self._getConfigFile()
            else:
                config_file = args.config
            self.configDir = os.path.dirname(config_file)
            self.readConfig(config_file)

            # Create remote module server
            try:
                if 'serverport' in self.tree['global']:
                    remotePort = self.tree['global']['serverport']
                    logger.info('Remote port is configured to {0}'.format(
                        remotePort))
                else:
                    remotePort = 12345
                    logger.info('Remote port is the standard {0}'.format(
                        remotePort))
                serveraddress = 'localhost'
                if 'serveraddress' in self.tree['global']:
                    serveraddress = self.tree['global']['serveraddress']
                else:
                    # bind to all available interfaces
                    serveraddress = ''
                if 'certfile' in self.tree['global']:
                    certfile = self.tree['global']['certfile']
                else:
                    certfile = None
                if 'keyfile' in self.tree['global']:
                    keyfile = self.tree['global']['keyfile']
                else:
                    keyfile = None
                self.rm = RemoteObjectManager(
                    self,
                    serveraddress,
                    remotePort,
                    certfile=certfile,
                    keyfile=keyfile)
                self.rm.createServer()
            except:
                self.remoteServer = False
                logger.exception('Remote server could not be started.')

            logger.info('QuDi started.')

            # Load startup things from config here
            if 'startup' in self.tree['global']:
                # walk throug the list of loadable modules to be loaded on startup and load them if appropriate
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
                    and len(self.tree['loaded']['gui']) == 0 ):
                logger.critical('No modules loaded during startup.')

    def getMainDir(self):
        """Returns the absolut path to the directory of the main software.

             @return string: path to the main tree of the software

        """
        return os.path.abspath( os.path.join( os.path.dirname(__file__), ".." ) )

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


    def readConfig(self, configFile):
        """Read configuration file and sort entries into categories.

          @param string configFile: path to configuration file
        """
        print("============= Starting Manager configuration from {0} =================".format(configFile) )
        logger.info("Starting Manager configuration from {0}".format(
            configFile))
        cfg = config.load(configFile)
        # Read modules, devices, and stylesheet out of config
        self.configure(cfg)

        self.configFile = configFile
        print("\n============= Manager configuration complete =================\n")
        logger.info('Manager configuration complete.')

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
                if key == 'hardware':
                    for m in cfg['hardware']:
                        if 'module.Class' in cfg['hardware'][m]:
                            self.tree['defined']['hardware'][m] = cfg['hardware'][m]
                        else:
                            logger.warning('    --> Ignoring device {0} -- '
                                    'no module specified'.format(m))

                # logic
                elif key == 'logic':
                    for m in cfg['logic']:
                        if 'module.Class' in cfg['logic'][m]:
                            self.tree['defined']['logic'][m] = cfg['logic'][m]
                        else:
                            logger.warning('    --> Ignoring logic {0} -- '
                                    'no module specified'.format(m))

                # GUI
                elif key == 'gui' and self.hasGui:
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
                elif key == 'global':
                    for m in cfg['global']:
                        if m == 'startup':
                            self.tree['global']['startup'] = cfg['global']['startup']
                        elif m == 'useOpenGL' and self.hasGui:
                            # use accelerated drawing
                            pg.setConfigOption('useOpenGL', cfg['global']['useOpenGl'])
                            self.tree['global']['useOpenGL'] = cfg['global']['useOpenGL']

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
                                    'Stylesheet not found at {0}'.format(
                                        stylesheetpath))
                                continue
                            stylesheetfile = open(stylesheetpath)
                            stylesheet = stylesheetfile.read()
                            stylesheetfile.close()
                            self.gui.setStyleSheet(stylesheet)
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
                        raise Exception('Config file {0} not found.'.format(fileName) )

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

    def saveConfig(self, filename):
        """Save configuration to a file.

          @param str filename: path where the config flie should be saved
        """
        saveconfig = OrderedDict()
        saveconfig.update(self.tree['defined'])
        saveconfig['global'] = self.tree['global']

        self.writeConfigFile(saveconfig, filename)
        logger.info('Saved configuration to {0}'.format(filename))

    def loadConfig(self, filename, restart=False):
        """ Load configuration from file.

          @param str filename: path of file to be loaded
        """
        maindir = self.getMainDir()
        configdir = os.path.join(maindir, 'config')
        loadFile = os.path.join(configdir, 'load.cfg')
        if filename.startswith(configdir):
            filename = re.sub('^'+re.escape('/'), '', re.sub('^'+re.escape(configdir), '', filename))
        loadData = {'configfile': filename}
        config.save(loadFile, loadData)
        logger.info('Set loaded configuration to {0}'.format(filename))
        if restart:
            logger.info('Restarting QuDi after configuration reload.')
            self.restart()

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
        """Load a python module that is a loadable QuDi module.

          @param string baseName: the module base package (hardware, logic, or gui)
          @param string module: the python module name inside the base package

          @return object: the loaded python module
        """

        logger.info('Loading module ".{0}.{1}"'.format(baseName, module))
        if baseName not in ['hardware', 'logic', 'gui']:
            raise Exception('You are trying to cheat the '
                            'system with some category {0}'.format(baseName) )

        # load the python module
        mod = importlib.__import__('{0}.{1}'.format(baseName, module), fromlist=['*'])
        # print('refcnt:', sys.getrefcount(mod))
        return mod

    def configureModule(self, moduleObject, baseName, className, instanceName,
                        configuration = {} ):
        """Instantiate an object from the class that makes up a QuDi module
           from a loaded python module object.

          @param object moduleObject: loaded python module
          @param string baseName: module base package (hardware, logic or gui)
          @param string className: name of the class we want an object from
                                 (same as module name usually)
          @param string instanceName: unique name thet the QuDi module instance
                                 was given in the configuration
          @param dict configuration: configuration options for the QuDi module

          @return object: QuDi module instance (object of the class derived
                          from Base)

          This method will add the resulting QuDi module instance to internal
          bookkeeping.
        """
        logger.info('Configuring {0} as {1}'.format(
            className, instanceName))
        with self.lock:
            if baseName in ['hardware', 'logic', 'gui']:
                if instanceName in self.tree['loaded'][baseName]:
                    raise Exception('{0} already exists with '
                                    'name {1}'.format(baseName, instanceName))
            else:
                raise Exception('You are trying to cheat the system with some '
                                'category {0}'.format(baseName) )

        if configuration is None:
            configuration = {}

        # get class from module by name
        print( moduleObject, className)
        modclass = getattr(moduleObject, className)

        #FIXME: Check if the class we just obtained has the right inheritance
        if not issubclass(modclass, Base):
            raise Exception('Bad inheritance, for instance %s from %s.%s.' % (instanceName, baseName, className))

        # Create object from class
        instance = modclass(manager=self, name=instanceName,
                config=configuration)

        with self.lock:
            if baseName in ['hardware', 'logic', 'gui']:
                self.tree['loaded'][baseName][instanceName] = instance
            else:
                raise Exception('We checked this already, there is no way that '
                                'we should get base class {0} here'.format(baseName))

        self.sigModulesChanged.emit()
        return instance

    def connectModule(self, base, mkey):
        """ Connects the given module in mkey to main object with the help of base.

          @param string base: module base package (hardware, logic or gui)
          @param string mkey: module which you want to connect

          @return int: 0 on success, -1 on failure
        """
        thismodule = self.tree['defined'][base][mkey]
        if mkey not in self.tree['loaded'][base]:
            logger.error('Loading of {0} module {1} as {2} was not '
                    'successful, not connecting it.'.format(
                        base, thismodule['module.Class'], mkey))
            return -1
        if 'connect' not in thismodule:
            return 0
        if 'in' not in  self.tree['loaded'][base][mkey].connector:
            logger.error('{0} module {1} loaded as {2} is supposed to '
                'get connected but it does not declare any IN '
                'connectors.'.format(base, thismodule['module.Class'], mkey))
            return -1
        if 'module.Class' not in thismodule:
            logger.error('{0} module {1} ({2}) connection configuration '
                'is broken: no module defined.'.format(
                    base, mkey, thismodule['module.Class']))
            return -1
        if not isinstance(thismodule['connect'], OrderedDict):
            logger.error('{0} module {1} ({2}) connection configuration '
                'is broken: connect is not a dictionary.'
                ''.format(base, mkey, thismodule['module.Class']))
            return -1

        connections = thismodule['connect']
        for c in connections:
            connectorIn = self.tree['loaded'][base][mkey].connector['in']
            if c not in connectorIn:
                logger.error('IN connector {0} of {1} module {2} loaded '
                    'as {3} is supposed to get connected but is not declared '
                    'in the module.'.format(
                        c, base, thismodule['module.Class'], mkey))
                continue
            if not isinstance(connectorIn[c], OrderedDict):
                logger.error('IN connector is no dictionary.')
                continue
            if 'class' not in connectorIn[c]:
                logger.error('No class key in connection declaration.')
                continue
            if not isinstance(connectorIn[c]['class'], str):
                logger.error('Value for class key is not a string.')
                continue
            if 'object' not in connectorIn[c]:
                logger.error('No object key in connection declaration.')
                continue
            if connectorIn[c]['object'] is not None:
                logger.warning('IN connector {0} of {1} module {2}'
                    ' loaded as {3} is already connected.'
                    ''.format(c, base, thismodule['module.Class'], mkey))
                continue
            if not isinstance(connections[c], str):
                logger.error('{0} module {1} ({2}) connection configuration '
                        'is broken, value for key {3} is not a string.'
                        ''.format(base, mkey, thismodule['module.Class'], c))
                continue
            if '.' not in connections[c]:
                logger.error('{0} module {1} ({2}) connection configuration '
                        'is broken, value {3} for key {4} does not contain '
                        'a dot.'.format(base, mkey,
                            thismodule['module.Class'], connections[c], c))
                continue
            destmod = connections[c].split('.')[0]
            destcon = connections[c].split('.')[1]
            destbase = ''
            if destmod in self.tree['loaded']['hardware'] and destmod in self.tree['loaded']['logic']:
                logger.error('Unique name {0} is in both hardware and logic '
                        'module list. Connection is not well defined, cannot '
                        'connect {1} ({2}) to  it.'.format(
                            destmod, mkey, thismodule['module.Class']))
                continue

            # Connect to hardware module
            elif destmod in self.tree['loaded']['hardware']:
                destbase = 'hardware'
            elif destmod in self.tree['loaded']['logic']:
                destbase = 'logic'
            else:
                logger.error('Unique name {0} is neither in hardware or '
                        'logic module list. Cannot connect {1} ({2}) to it.'
                        ''.format(connections[c], mkey,
                            thismodule['module.Class']))
                continue

            if 'out' not in self.tree['loaded'][destbase][destmod].connector:
                logger.error('Module {0} loaded as {1} is supposed to '
                        'get connected to module loaded as {2} that does not '
                        'declare any OUT connectors.'.format(
                            thismodule['module.Class'], mkey, destmod))
                continue
            outputs = self.tree['loaded'][destbase][destmod].connector['out']
            if destcon not in outputs:
                logger.error('OUT connector {} not declared in module {}.{} '
                        'but connected to IN connector {} of module {}.'
                        ''.format(destcon, destbase, destmod, c,
                            thismodule['module.Class']))
                continue
            if not isinstance(outputs[destcon], OrderedDict):
                logger.error('OUT connector not a dictionary.')
                continue
            if 'class' not in outputs[destcon]:
                logger.error('No class key in OUT connector dictionary.')
                continue
            if not isinstance(outputs[destcon]['class'], str):
                logger.error('Class value not a string.')
                continue
#            if not issubclass(self.tree['loaded'][destbase][destmod].__class__, outputs[destcon]['class']):
#                logger.error('not the correct class for declared interface.')
#                return

            # Finally set the connection object
            logger.info('Connecting {0} module {1}.IN.{2} to {3} {4}.{5}'
                ''.format(base, mkey, c, destbase, destmod, destcon))
            connectorIn[c]['object'] = self.tree['loaded'][destbase][destmod]

        # check that all IN connectors are connected
        for c,v in self.tree['loaded'][base][mkey].connector['in'].items():
            if v['object'] is None:
                logger.error('IN connector {} of module {}.{} is empty, '
                        'connection not complete.'.format(c, base, mkey))
                return -1
        return 0

    def loadConfigureModule(self, base, key):
        """Loads the configuration Module in key with the help of base class.

          @param string base: module base package (hardware, logic or gui)
          @param string key: module which is going to be loaded

          @return int: 0 on success, -1 on fatal error, 1 on error
        """
        if 'module.Class' in self.tree['defined'][base][key]:
            if 'remote' in self.tree['defined'][base][key]:
                if not self.remoteServer:
                    logger.error('Remote functionality not working, check '
                            'your log.')
                    return -1
                if not isinstance(self.tree['defined'][base][key]['remote'], str):
                    logger.error('Remote URI of {0} module {1} not a string.'
                            ''.format(base, key))
                    return -1
                try:
                    instance = self.rm.getRemoteModuleUrl(self.tree['defined'][base][key]['remote'])
                    logger.info('Remote module {0} loaded as .{1}.{2}.'.format(
                        self.tree['defined'][base][key]['remote'], base, key))
                    with self.lock:
                        if base in ['hardware', 'logic', 'gui']:
                            self.tree['loaded'][base][key] = instance
                            self.sigModulesChanged.emit()
                        else:
                            raise Exception('You are trying to cheat the system with some category {0}'.format(base))
                except:
                    logger.exception('Error while loading {0} module: '
                            '{1}'.format(base, key))
                    return -1
            else:
                try:
                    # class_name is the last part of the config entry
                    class_name = re.split('\.', self.tree['defined'][base][key]['module.Class'])[-1]
                    # module_name is the whole line without this last part (and with the trailing dot removed also)
                    module_name = re.sub('.'+class_name+'$', '', self.tree['defined'][base][key]['module.Class'])

                    modObj = self.importModule(base, module_name)
                    self.configureModule(modObj, base, class_name, key, self.tree['defined'][base][key])
                    if 'remoteaccess' in self.tree['defined'][base][key] and self.tree['defined'][base][key]['remoteaccess']:
                        if not self.remoteServer:
                            logger.error('Remote module sharing does not work '
                                    'as server startup failed earlier, check '
                                    'your log.')
                            return 1
                        self.rm.shareModule(key, self.tree['loaded'][base][key])
                except:
                    logger.exception('Error while loading {0} module:'
                        ' {1}'.format(base, key))
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
        if 'remote' in self.tree['defined'][base][key]:
            if not self.remoteServer:
                logger.error('Remote functionality not working, check your '
                        'log.')
                return -1
            if not isinstance(self.tree['defined'][base][key]['remote'], str):
                logger.error('Remote URI of {0} module {1} not a string.'
                        ''.format(base, key))
                return -1
            try:
                instance = self.rm.getRemoteModuleUrl(self.tree['defined'][base][key]['remote'])
                logger.info('Remote module {0} loaded as .{1}.{2}.'
                    ''.format(self.tree['defined'][base][key]['remote'],
                        base, key))
                with self.lock:
                    if base in ['hardware', 'logic', 'gui']:
                        self.tree['loaded'][base][key] = instance
                        self.sigModulesChanged.emit()
                    else:
                        raise Exception(
                            'You are trying to cheat the system with some category {0}'.format(base))
            except:
                logger.exception('Error while loading {0} module: '
                        '{1}'.format(base, key))
        elif (key in self.tree['loaded'][base]
                and 'module.Class' in self.tree['defined'][base][key]):
            try:
                # state machine: deactivate
                if self.isModuleActive(base, key):
                    self.deactivateModule(base, key)
            except:
                logger.exception('Error while deactivating {0} module: '
                        '{1}'.format(base, key))
                return -1
            try:
                with self.lock:
                    self.tree['loaded'][base].pop(key, None)
                # reload config part associated with module
                self.reloadConfigPart(base, key)
                # class_name is the last part of the config entry
                class_name = re.split('\.', self.tree['defined'][base][key]['module.Class'])[-1]
                # module_name is the whole line without this last part (and with the trailing dot removed also)
                module_name = re.sub('.'+class_name+'$', '', self.tree['defined'][base][key]['module.Class'])

                modObj = self.importModule(base, module_name)
                # des Pudels Kern
                importlib.reload(modObj)
                self.configureModule(modObj, base, class_name, key, self.tree['defined'][base][key])
            except:
                logger.exception('Error while reloading {0} module: '
                        '{1}'.format(base, key))
                return -1
        else:
            logger.error('Module not loaded or not loadable (missing module '
                     'declaration in configuration): {0}.{1}'.format(base, key))
        return 0

    def isModuleActive(self, base, key):
        """Returns whether a given module is active.

          @param string base: module base package (hardware, logic or gui)
          @param string key: module which is going to be activated.
        """
        if base not in self.tree['loaded']:
            logger.error('Unknown module base "{0}"'.format(base))
            return False
        if key not in self.tree['loaded'][base]:
            logger.error('{0} module {1} not loaded.'.format(base, key))
            return False
        return self.tree['loaded'][base][key].getState() in ('idle',
                'running')

    @QtCore.pyqtSlot(str, str)
    def activateModule(self, base, key):
        """Activate the module given in key with the help of base class.

          @param string base: module base package (hardware, logic or gui)
          @param string key: module which is going to be activated.

        """
        if base not in self.tree['loaded']:
            logger.error('Unknown module base "{0}"'.format(base))
            return
        if key not in self.tree['loaded'][base]:
            logger.error('{0} module {1} not loaded.'.format(base, key))
            return
        if self.tree['loaded'][base][key].getState() != 'deactivated' and (
                ( base in self.tree['defined']
                    and key in self.tree['defined'][base]
                    and 'remote' in self.tree['defined'][base][key]
                    and self.remoteServer)
                or (base in self.tree['start']
                    and  key in self.tree['start'][base])) :
            return
        if self.tree['loaded'][base][key].getState() != 'deactivated':
            logger.error('{0} module {1} not deactivated'.format(
                base, key))
            return
        ## start main loop for qt objects
        if base == 'logic':
            modthread = self.tm.newThread('mod-' + base + '-' + key)
            self.tree['loaded'][base][key].moveToThread(modthread)
            modthread.start()
        try:
            self.tree['loaded'][base][key].setStatusVariables(
                    self.loadStatusVariables(base, key))
            self.tree['loaded'][base][key].activate()
        except:
            logger.exception(
                    '{0} module {1}: error during activation:'.format(
                        base, key))
        QtCore.QCoreApplication.instance().processEvents()

    @QtCore.pyqtSlot(str, str)
    def deactivateModule(self, base, key):
        """Activated the module given in key with the help of base class.

          @param string base: module base package (hardware, logic or gui)
          @param string key: module which is going to be activated.

        """
        logger.info('Deactivating {0}.{1}'.format(base, key))
        if base not in self.tree['loaded']:
            logger.error('Unknown module base "{0}"'.format(base))
            return
        if key not in self.tree['loaded'][base]:
            logger.error('{0} module {1} not loaded.'.format(base, key))
            return
        if not self.tree['loaded'][base][key].getState() in ('idle',
                'running'):
            logger.error('{0} module {1} not active (idle or running).'
                    ''.format(base, key))
            return
        try:
            self.tree['loaded'][base][key].deactivate()
            if base == 'logic':
                self.tm.quitThread('mod-' + base + '-' + key)
                self.tm.joinThread('mod-' + base + '-' + key)
            self.saveStatusVariables(base, key,
                    self.tree['loaded'][base][key].getStatusVariables())
        except:
            logger.exception(
                    '{0} module {1}: error during deactivation:'.format(
                        base, key))
        QtCore.QCoreApplication.instance().processEvents()

    def getSimpleModuleDependencies(self, base, key):
        """ Based on object id, find which connections to replace.

          @param str base: Module category
          @param str key: Unique configured module name for module where
                          we want the dependencies

          @return dict: module dependencies in the right format for the
                        Manager.toposort function
        """
        deplist = list()
        if base not in self.tree['loaded']:
            logger.error('Unknown base in module {0}.{1}'.format(base, key))
            return None
        if key not in self.tree['loaded'][base]:
            logger.error('{0} module {1} not loaded.'.format(
                base, key))
            return None
        for mbase in self.tree['loaded']:
            for mkey in self.tree['loaded'][mbase]:
                target = self.tree['loaded'][mbase][mkey]
                if not hasattr(target, 'connector'):
                    logger.error('No connector in module .{0}.{1}!'.format(
                        mbase, mkey))
                    continue
                for conn in target.connector['in']:
                    if not 'object' in target.connector['in'][conn]:
                        logger.error('Malformed connector {2} in module '
                                '.{0}.{1}!'.format(mbase, mkey, conn))
                        continue
                    if target.connector['in'][conn]['object'] is self.tree[
                            'loaded'][base][key]:
                        deplist.append( (mbase, mkey) )
        return {key: deplist}


    def getRecursiveModuleDependencies(self, base, key):
        """ Based on input connector declarations, determine in which other modules are needed for a specific module to run.

          @param str base: Module category
          @param str key: Unique configured module name for module where we want the dependencies

          @return dict: module dependencies in the right format for the Manager.toposort function
        """
        deps = dict()
        if base not in self.tree['defined']:
            logger.error('{0} module {1}: no such base'.format(base, key))
            return None
        if key not in self.tree['defined'][base]:
            logger.error('{0} module {1}: no such module defined'.format(
                base, key))
            return None
        if 'connect' not in self.tree['defined'][base][key]:
            return dict()
        if not isinstance(self.tree['defined'][base][key]['connect'], OrderedDict):
            logger.error('{0} module {1}: connect is not a dictionary'.format(
                base, key))
            return None
        connections = self.tree['defined'][base][key]['connect']
        deplist = set()
        for c in connections:
            if not isinstance(connections[c], str):
                logger.error('Value for class key is not a string.')
                return None
            if not '.' in connections[c]:
                logger.error('{}.{}: connection {}: {} has wrong format'
                        'for connection target'.format(
                            base, key, c, connections[c]))
                return None
            destmod = connections[c].split('.')[0]
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

    @QtCore.pyqtSlot(str, str)
    def startModule(self, base, key):
        """ Figure out the module dependencies in terms of connections, load and activate module.

          @param str base: Module category
          @param str key: Unique module name

          @return int: 0 on success, -1 on error

            If the module is already loaded, just activate it.
            If the module is an active GUI module, show its window.
        """
        deps = self.getRecursiveModuleDependencies(base, key)
        sorteddeps = Manager.toposort(deps)
        if len(sorteddeps) == 0:
            sorteddeps.append(key)

        for mkey in sorteddeps:
            for mbase in ['hardware', 'logic', 'gui']:
                if mkey in self.tree['defined'][mbase] and not mkey in self.tree['loaded'][mbase]:
                    success = self.loadConfigureModule(mbase, mkey)
                    if success < 0:
                        logger.warning('Stopping module loading after loading '
                                'failure.')
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
                    if self.tree['loaded'][mbase][mkey].getState() == 'deactivated':
                        self.activateModule(mbase, mkey)
                    elif self.tree['loaded'][mbase][mkey].getState() != 'deactivated' and mbase == 'gui':
                        self.tree['loaded'][mbase][mkey].show()
        return 0

    @QtCore.pyqtSlot(str, str)
    def stopModule(self, base, key):
        """ Figure out the module dependencies in terms of connections and deactivate module.

          @param str base: Module category
          @param str key: Unique module name

        """
        deps = self.getRecursiveModuleDependencies(base, key)
        sorteddeps = Manager.toposort(deps)
        if len(sorteddeps) == 0:
            sorteddeps.append(key)

        for mkey in reversed(sorteddeps):
            for mbase in ['hardware', 'logic', 'gui']:
                if mkey in self.tree['defined'][mbase] and mkey in self.tree['loaded'][mbase]:
                    if self.tree['loaded'][mbase][mkey].getState() in ('idle', 'running'):
                        logger.info('Deactivating module {0}.{1}'.format(
                            mbase, mkey))
                        self.deactivateModule(mbase, mkey)

    @QtCore.pyqtSlot(str, str)
    def restartModuleSimple(self, base, key):
        """Deactivate, reloade, activate module.
          @param str base: Module category
          @param str key: Unique module name

          @return int: 0 on success, -1 on error

            Deactivates and activates all modules that depend on it in order to ensure correct connections.
        """
        deps = self.getSimpleModuleDependencies(base, key)
        if deps is None:
            return
        # Remove references
        for depmod in deps[key]:
            destbase, destmod = depmod
            for c in self.tree['loaded'][destbase][destmod].connector['in']:
                if self.tree['loaded'][destbase][destmod].connector[
                        'in'][c]['object'] is self.tree['loaded'][base][key]:
                    if self.isModuleActive(destbase, destmod):
                        self.deactivateModule(destbase, destmod)
                    self.tree['loaded'][destbase][destmod].connector[
                            'in'][c]['object'] = None

        # reload and reconnect
        success = self.reloadConfigureModule(base, key)
        if success < 0:
            logger.warning('Stopping module {0}.{1} loading after loading '
                    'failure.'.format(base, key))
            return -1
        success = self.connectModule(base, key)
        if success < 0:
            logger.warning('Stopping module {0}.{1} loading after '
                    'connection failure.'.format(base, key))
            return -1
        self.activateModule(base, key)

        for depmod in deps[key]:
            destbase, destmod = depmod
            self.connectModule(destbase, destmod)
            self.activateModule(destbase, destmod)
        return 0

    @QtCore.pyqtSlot(str, str)
    def restartModuleRecursive(self, base, key):
        """ Figure out the module dependencies in terms of connections, reload and activate module.

          @param str base: Module category
          @param str key: Unique configured module name

        """
        deps = self.getSimpleModuleDependencies(base, key)
        sorteddeps = Manager.toposort(deps)

        for mkey in sorteddeps:
            for mbase in ['gui', 'logic', 'hardware']:
                # load if the config changed
                if mkey in self.tree['defined'][mbase] and not mkey in self.tree['loaded'][mbase]:
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
                        self.activateModule(mbase, mkey)
                # reload if already there
                elif mkey in self.tree['loaded'][mbase]:
                    success = self.reloadConfigureModule(mbase, mkey)
                    if success < 0:
                        logger.warning('Stopping loading module {0}.{1} after '
                                'loading error'.format(mbase, mkey))
                        return -1
                    success = self.connectModule(mbase, mkey)
                    if success < 0:
                        logger.warning('Stopping loading module {0}.{1} after '
                                'connection error'.format(mbase, mkey))
                        return -1
                    if mkey in self.tree['loaded'][mbase]:
                        self.activateModule(mbase, mkey)

    def startAllConfiguredModules(self):
        """Connect all QuDi modules from the currently laoded configuration and
            activate them.
        """
        #FIXME: actually load all the modules in the correct order and connect
        # the interfaces
        for base in ['hardware', 'logic', 'gui']:
            for key in self.tree['defined'][base]:
                self.startModule(base, key)

        logger.info('Activation finished.')

    def getStatusDir(self):
        """ Get the directory where the app state is saved, create it if necessary.

          @return str: path of application status directory
        """
        appStatusDir = os.path.join(self.configDir, 'app_status')
        if not os.path.isdir(appStatusDir):
            os.makedirs(appStatusDir)
        return appStatusDir

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
                        'status-{0}_{1}_{2}.cfg'.format(classname, base,
                            module))
                config.save(filename, variables)
            except:
                print(variables)
                logger.exception('Failed to save status variables of module '
                        '{0}.{1}:\n'
                        '{2}'.format(base, module, repr(variables)))

    def loadStatusVariables(self, base, module):
        """ If a status variable file exists for a module, load it into a dictionary.

          @param str base: the module category
          @param str module: the unique mduel name

          @return dict: dictionary of satus variable names and values
        """
        try:
            statusdir = self.getStatusDir()
            classname = self.tree['loaded'][base][module].__class__.__name__
            filename = os.path.join(statusdir, 'status-{0}_{1}_{2}.cfg'.format(classname, base, module))
            if os.path.isfile(filename):
                variables = config.load(filename)
            else:
                variables = OrderedDict()
        except:
            logger.exception('Failed to load status variables.')
            variables = OrderedDict()
        return variables

    def removeStatusFile(self, base, module):
        try:
            statusdir = self.getStatusDir()
            classname = self.tree['defined'][base][module]['module.Class'].split('.')[-1]
            filename = os.path.join(statusdir, 'status-{0}_{1}_{2}.cfg'.format(classname, base, module))
            if os.path.isfile(filename):
                os.remove(filename)
        except:
            logger.exception('Failed to remove module status file.')

    def quit(self):
        """Nicely request that all modules shut down."""
        for mbase in ['gui', 'logic', 'hardware']:
            for module in self.tree['loaded'][mbase]:
                self.stopModule(mbase, module)
                QtCore.QCoreApplication.processEvents()
        self.sigManagerQuit.emit(self, False)

    def restart(self):
        """Nicely request that all modules shut down for application restart."""
        for mbase in ['hardware', 'logic', 'gui']:
            for module in self.tree['loaded'][mbase]:
                if self.isModuleActive(mbase, module):
                    self.deactivateModule(mbase, module)
                QtCore.QCoreApplication.processEvents()
        self.sigManagerQuit.emit(self, True)

    # Staticmethods are used to group functions which have some logical
    # connection with a class but they They behave like plain functions except
    # that you can call them from an instance or the class. Methods covered
    # with static decorators are an organization/stylistic feature in python.
    @staticmethod
    def toposort(deps, cost=None):
        """Topological sort. Arguments are:

          @param dict deps: Dictionary describing dependencies where a:[b,c]
                            means "a depends on b and c"
          @param dict cost: Optional dictionary of per-node cost values. This
                            will be used to sort independent graph branches by
                            total cost.

        Examples::

            # Sort the following graph:
            #
            #   B ──┬─────> C <── D
            #       │       │
            #   E <─┴─> A <─┘
            #
            deps = {'a': ['b', 'c'], 'c': ['b', 'd'], 'e': ['b']}
            toposort(deps)
            => ['b', 'e', 'd', 'c', 'a']

            # This example is underspecified; there are several orders that
            # correctly satisfy the graph. However, we may use the 'cost'
            # argument to impose more constraints on the sort order.

            # Let each node have the following cost:
            cost = {'a': 0, 'b': 0, 'c': 1, 'e': 1, 'd': 3}

            # Then the total cost of following any node is its own cost plus
            # the cost of all nodes that follow it:
            #   A = cost[a]
            #   B = cost[b] + cost[c] + cost[e] + cost[a]
            #   C = cost[c] + cost[a]
            #   D = cost[d] + cost[c] + cost[a]
            #   E = cost[e]
            # If we sort independent branches such that the highest cost comes
            # first, the output is:
            toposort(deps, cost=cost)
            => ['d', 'b', 'c', 'e', 'a']
        """
        # copy deps and make sure all nodes have a key in deps
        deps0 = deps
        deps = {}
        for k,v in list(deps0.items()):
            deps[k] = v[:]
            for k2 in v:
                if k2 not in deps:
                    deps[k2] = []

        # Compute total branch cost for each node
        key = None
        if cost is not None:
            order = Manager.toposort(deps)
            allDeps = {n: set(n) for n in order}
            for n in order[::-1]:
                for n2 in deps.get(n, []):
                    allDeps[n2] |= allDeps.get(n, set())

            totalCost = {n: sum([cost.get(x, 0) for x in allDeps[n]]) for n in allDeps}
            key = lambda x: totalCost.get(x, 0)

        # compute weighted order
        order = []
        while len(deps) > 0:
            # find all nodes with no remaining dependencies
            ready = [k for k in deps if len(deps[k]) == 0]

            # If no nodes are ready, then there must be a cycle in the graph
            if len(ready) == 0:
                print(deps, deps0)
                raise Exception('Cannot resolve requested device configure/start order.')

            # sort by branch cost
            if key is not None:
                ready.sort(key=key, reverse=True)

            # add the highest-cost node to the order, then remove it from the
            # entire set of dependencies
            order.append(ready[0])
            del deps[ready[0]]
            for v in list(deps.values()):
                try:
                    v.remove(ready[0])
                except ValueError:
                    pass

        return order

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
                logger.error('You tried to remove the task runner but none '
                        'was registered.')
            else:
                logger.warning('Replacing task runner.')

