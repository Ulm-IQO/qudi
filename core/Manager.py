# -*- coding: utf-8 -*-
"""
Manager.py -  Defines main Manager class for ACQ4
Copyright 2010  Luke Campagnola
Distributed under MIT/X11 license. See license.txt for more infomation.

This class must be invoked once to initialize the ACQ4 core system.
The class is responsible for:
    - Configuring devices
    - Invoking/managing modules
    - Creating and executing acquisition tasks. 
"""
import os
import sys
import gc
import getopt
import glob

import time
import atexit
import weakref
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.reload as reload
import pyqtgraph.configfile as configfile

from .util import ptime
from .util.Mutex import Mutex
from collections import OrderedDict
import pyqtgraph as pg
from .Logger import Logger, LOG, printExc

class Manager(QtCore.QObject):
    """Manager class is responsible for:
      - Loading/configuring device modules and storing their handles
      - Providing unified timestamps
      - Making sure all devices/modules are properly shut down
        at the end of the program

      @signal sigConfigChanged
      @signal sigModulesChanged
      @signal sigModuleHasQuit
      @signal sigBaseDirChanged
      @signal sigAbortAll
      """
      
    sigConfigChanged = QtCore.Signal()
    sigModulesChanged = QtCore.Signal() 
    sigModuleHasQuit = QtCore.Signal(object) ## (module name)
    sigBaseDirChanged = QtCore.Signal()
    sigLogDirChanged = QtCore.Signal(object) #dir
    sigAbortAll = QtCore.Signal()  # User requested abort all tasks via ESC key
    
    def __init__(self, configFile=None, argv=None):
        """Constructor for QuDi main management class

          @param string configFile: path to configuration file
          @param list argv: command line arguments
        """
        ## used for keeping some basic methods thread-safe
        self.lock = Mutex(recursive=True)
        self.config = OrderedDict()
        
        self.hardware = OrderedDict()
        self.definedHardware = OrderedDict()
        
        self.gui = OrderedDict()
        self.startupGui = OrderedDict()
        self.definedGui = OrderedDict()
        
        self.logic = OrderedDict()
        self.startupLogic = OrderedDict()
        self.definedLogic = OrderedDict()

        self.currentDir = None
        self.baseDir = None
        self.disableDevs = []
        self.disableAllDevs = False
        self.alreadyQuit = False
        self.taskLock = Mutex(QtCore.QMutex.Recursive)
        
        try:
            global LOG
            LOG = Logger(self)
            #print(LOG)
            self.logger = LOG
            
            if argv is not None:
                try:
                    opts, args = getopt.getopt(argv, 'c:a:m:b:s:d:nD',
                    ['config=',
                    'config-name=',
                    'module=',
                    'base-dir=',
                    'storage-dir=',
                    'disable=',
                    'no-manager',
                    'disable-all'])
                except getopt.GetoptError as err:
                    print(str(err))
                    print("""
    Valid options are:
        -c --config=       Configuration file to load
        -a --config-name=  Named configuration to load
        -m --module=       Module name to load
        -b --base-dir=     Base directory to use
        -s --storage-dir=  Storage directory to use
        -n --no-manager    Do not load manager module
        -d --disable=      Disable the device specified
        -D --disable-all   Disable all devices
    """)
                    raise
            else:
                opts = []
            
            QtCore.QObject.__init__(self)
            atexit.register(self.quit)
    
            
            ## Handle command line options
            loadModules = []
            setBaseDir = None
            setStorageDir = None
            loadManager = True
            loadConfigs = []
            for o, a in opts:
                if o in ['-c', '--config']:
                    configFile = a
                elif o in ['-a', '--config-name']:
                    loadConfigs.append(a)
                elif o in ['-m', '--module']:
                    loadModules.append(a)
                elif o in ['-b', '--baseDir']:
                    setBaseDir = a
                elif o in ['-s', '--storageDir']:
                    setStorageDir = a
                elif o in ['-n', '--noManager']:
                    loadManager = False
                elif o in ['-d', '--disable']:
                    self.disableDevs.append(a)
                elif o in ['-D', '--disable-all']:
                    self.disableAllDevs = True
                else:
                    print("Unhandled option", o, a)
            
            ## Read in configuration file
            if configFile is None:
                configFile = self._getConfigFile()
            
            self.configDir = os.path.dirname(configFile)
            self.readConfig(configFile)
            
            self.logger.logMsg('QuDi started.', importance=9)
            
            ## Act on options if they were specified..
            try:
                for name in loadConfigs:
                    self.loadDefinedConfig(name)
                for m in loadModules:
                    try:
                        self.loadDefinedModule(m)
                    except:
                        raise
            except:
                printExc("\nError while acting on command line options: "
                "(but continuing on anyway..)")
            ## load startup things from config here
            for key in self.startupGui:
                try:
                    # self.loadModule( baseclass, module, instanceName, config=None)
                    modObj = self.loadModule('gui',
                                            self.startupGui[key]['module'])
                    modName = modObj.__name__.replace(modObj.__package__, '').replace('.', '')
                    self.configureModule(modObj,
                                        'gui',
                                        modName,
                                        key,
                                        self.startupGui[key])
                    self.gui[key].activate()
                except:
                    raise
        except:
            printExc("Error while configuring Manager:")
        finally:
            if len(self.logic) == 0 and len(self.gui) == 0 :
                self.logger.logMsg('No modules loaded during startup. ' 
                                    'Not much is happening.',
                                    importance=9)
            
    def _getConfigFile(self):
        ## search all the default locations to find a configuration file.
        from . import CONFIGPATH
        for path in CONFIGPATH:
            cf = os.path.join(path, 'default.cfg')
            if os.path.isfile(cf):
                return cf
        raise Exception("Could not find config file in: %s" % CONFIGPATH)
    
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
        print("============= Starting Manager configuration from %s =================" % configFile)
        self.logger.logMsg("Starting Manager configuration from %s" % configFile)
        cfg = configfile.readConfigFile(configFile)
            
        ## read modules, devices, and stylesheet out of config
        self.configure(cfg)

        self.configFile = configFile
        print("\n============= Manager configuration complete =================\n")
        self.logger.logMsg('Manager configuration complete.')
        
    def configure(self, cfg):
        """Sort modules from configuration into categories

          @param dict cfg: dictionary from configuration file

          There are the main categories hardware, logic, gui, startup
          and global.
          startup modules can be logic or gui and are loaded
          directly on startup.
          global contains settings for the whole application.
          hardware, logic and gui contain configuration of and
          for loadable modules.
        """
        
        for key in cfg:
            try:
                ## hardware
                if key == 'hardware':
                    for m in cfg['hardware']:
                        if self.disableAllDevs or m in self.disableDevs:
                            self.logger.print_logMsg("    --> Ignoring device '%s' -- disabled by request" % m)
                            continue
                        if 'module' in cfg['hardware'][m]:
                            self.definedHardware[m] = cfg['hardware'][m]
                        else: 
                            self.logger.print_logMsg("    --> Ignoring device '%s' -- no module specified" % m)

                ## logic
                elif key == 'logic':
                    for m in cfg['logic']:
                        if 'module' in cfg['logic'][m]:
                            self.definedLogic[m] = cfg['logic'][m]
                        else:
                            self.logger.print_logMsg("    --> Ignoring logic '%s' -- no module specified" % m)
                        
                ## GUI
                elif key == 'gui':
                    for m in cfg['gui']:
                        if 'module' in cfg['gui'][m]:
                            self.definedGui[m] = cfg['gui'][m]
                        else:
                            self.logger.print_logMsg("    --> Ignoring GUI '%s' -- no module specified" % m)

                ## load on startup
                elif key == 'startup':
                    for skey in cfg['startup']:
                        if skey == 'gui':
                            for m in cfg['startup']['gui']:
                                if 'module' in cfg['startup']['gui'][m]:
                                    self.startupGui[m] = cfg['startup']['gui'][m]
                                else:
                                    self.logger.print_logMsg("    --> Ignoring startup logic '%s' -- no module specified" % m)
                        elif skey == 'logic':
                            for m in cfg['startup']['logic']:
                                if 'module' in cfg['startup']['logic'][m]:
                                    self.startupLogic[m] = cfg['startup']['logic'][m]
                                else:
                                    self.logger.print_logMsg("    --> Ignoring startup GUI '%s' -- no module specified" % m)

                ## global config
                elif key == 'global':
                    for m in cfg['global']:
                        if m == 'storageDir':
                            self.logger.print_logMsg("=== Setting base directory: %s ===" % cfg['global']['storageDir'])
                            self.setBaseDir(cfg['global']['storageDir'])
                
                        elif m == 'useOpenGL':
                            pg.setConfigOption('useOpenGL', cfg['global']['useOpenGl'])
                
                ## Copy in any other configurations.
                ## dicts are extended, all others are overwritten.
                else:
                    if isinstance(cfg[key], dict):
                        if key not in self.config:
                            self.config[key] = {}
                        for key2 in cfg[key]:
                            self.config[key][key2] = cfg[key][key2]
                    else:
                        self.config[key] = cfg[key]
            except:
                printExc("Error in configuration:")
        #print self.config
        self.sigConfigChanged.emit()

    def listConfigurations(self):
        """Return a list of the named configurations available

          @return list: user configurations
        """
        with self.lock:
            if 'configurations' in self.config:
                return list(self.config['configurations'].keys())
            else:
                return []

    def loadDefinedConfig(self, name):
        with self.lock:
            if name not in self.config['configurations']:
                raise Exception("Could not find configuration named '%s'" % name)
            cfg = self.config['configurations'].get(name, )
        self.configure(cfg)

    def readConfigFile(self, fileName, missingOk=True):
        """Actually check if the configuration file exists and read it

          @param string fileName: path to configuration file
          @param bool missingOk: suppress exception if file does not exist

          @return dict: configuration from file
        """
        with self.lock:
            fileName = self.configFileName(fileName)
            if os.path.isfile(fileName):
                return configfile.readConfigFile(fileName)
            else:
                if missingOk: 
                    return {}
                else:
                    raise Exception('Config file "%s" not found.' % fileName)
            
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
            configfile.writeConfigFile(data, fileName)
    
    def appendConfigFile(self, data, fileName):
        """Append configuration to a file in the currently used config directory.

          @param dict data: dictionary to write into file
          @param string fileName: path for filr to be written
        """
        with self.lock:
            fileName = self.configFileName(fileName)
            if os.path.exists(fileName):
                configfile.appendConfigFile(data, fileName)
            else:
                raise Exception("Could not find file %s" % fileName)
        
        
    def configFileName(self, name):
        """Get the full path of a configuration file from its filename.

          @param string name: filename of file in configuration directory
          @return string: full path to file
        """
        with self.lock:
            return os.path.join(self.configDir, name)

    def setBaseDir(self, path):
        """Set base directory for data

          @param string path: base directory path
        """
        oldBaseDir = self.baseDir
        dirName = os.path.dirName(path)
        if not os.path.exists(dirName):
            os.makedirs(dirName)
        self.baseDir = dirName
        if(oldBaseDir != dirName):
            self.sigBaseDirChanged.emit()


## Module loading

    def loadModule(self, baseName, module):
        """Load a python module that is a loadable QuDi module.

          @param string baseName: the module base package (hardware, logic, or gui)
          @param string module: the python module name inside the base package

          @return object: the loaded python module
        """
        
        self.logger.print_logMsg('Loading module ".%s.%s"' % (baseName, module))
        if baseName not in ['hardware', 'logic', 'gui']:
            raise Exception('You are trying to cheat the system with some category "%s"' % baseName)
        
        ## load the python module
        mod = __import__('%s.%s' % (baseName, module), fromlist=['*'])
        return mod

    def configureModule(self, moduleObject, baseName, className, instanceName, configuration = {} ):
        """Instantiate an object from the class that makes up a QuDi module from a loaded python module object.

          @param object moduleObject: loaded python module
          @param string baseName: module base package (hardware, logic or gui)
          @param string className: name of the class we want an object from (same as module name usually)
          @param string instanceName: unique name thet the QuDi module instance was given in the configuration
          @param dict configuration: configuration options for the QuDi module

          @return object: QuDi module instance (object of class derived from Base)

          This method will add the resulting QuDi module instance to internal bookkeeping.
        """
        self.logger.print_logMsg('Configuring "%s" as "%s"' % (className, instanceName) )
        with self.lock:
            if baseName == 'hardware':
                if instanceName in self.hardware:
                    raise Exception('Hadware already exists with name "%s"' % instanceName)
            elif baseName == 'logic':
                if instanceName in self.logic:
                    raise Exception('Logic already exists with name "%s"' % instanceName)
            elif baseName == 'gui':
                if instanceName in self.gui:
                    raise Exception('GUI already exists with name "%s"' % instanceName)
            else:
                raise Exception('You are trying to cheat the system with some category "%s"' % baseName)
        
        if configuration is None:
            configuration = {}

        modclass = getattr(moduleObject, className)
        
        #FIXME: Check if the class we just obtained has the right inheritance

        # Create object from class (Manager, Name, config)
        instance = modclass(self, instanceName, configuration)

        with self.lock:
            if baseName == 'hardware':
                self.hardware[instanceName] = instance
            elif baseName == 'logic':
                self.logic[instanceName] = instance
            elif baseName == 'gui':
                self.gui[instanceName] = instance
            else:
                raise Exception('We checked this already, there is no way that '
                                'we should get base class "%s" here'
                                % baseclass)
        
        self.sigModulesChanged.emit()
        return instance

    def startAllConfiguredModules(self):
        """Connect all QuDi modules from the currently laoded configuration and
            activate them.
        """
        ##FIXME: actually load all the modules in the correct order 
        ## and connect the interfaces
        #print("HW:", self.definedHardware)
        #print("LG:", self.definedLogic)
        #print("GU:", self.definedGui)
        ## Hardware
        for key in self.definedHardware:
            if 'module' in self.definedHardware[key]:
                try:
                    modObj = self.loadModule(
                                        'hardware',
                                        self.definedHardware[key]['module'])
                    modName = modObj.__name__.replace(modObj.__package__, '').replace('.', '')
                    self.configureModule(modObj,
                                        'hardware',
                                        modName,
                                        key,
                                        self.definedHardware[key])
                except:
                    self.logger.logExc(
                            'Error while loading hardware module: %s' % key,
                             msgType='error')
                    continue
            else:
                self.logger.logMsg('Not a loadable hardware module: %s' % key,
                                    msgType='error')
        ## Logic
        for key in self.definedLogic:
            if 'module' in self.definedLogic[key]:
                try:
                    modObj = self.loadModule(
                                        'logic',
                                        self.definedLogic[key]['module'])
                    modName = modObj.__name__.replace(modObj.__package__, '').replace('.', '')
                    self.configureModule(modObj,
                                        'logic',
                                        modName,
                                        key,
                                        self.definedLogic[key])
                except:
                    self.logger.logExc(
                                'Error while loading logic module: %s' % key,
                                msgType='error')
                    continue
            else:
                self.logger.logMsg('Not a loadable logic module: %s' % key,
                                    msgType='error')
        ## GUI
        for key in self.definedGui:
            if 'module' in self.definedGui[key]:
                try:
                    modObj = self.loadModule(
                                        'gui',
                                         self.definedGui[key]['module'])
                    modName = modObj.__name__.replace(modObj.__package__, '').replace('.', '')
                    self.configureModule(modObj,
                                        'gui',
                                        modName,
                                        key,
                                        self.definedGui[key])
                except:
                    self.logger.logExc(
                            'Error while loading GUI module: %s' % key,
                             msgType='error')
                    continue
            else:
                self.logger.logMsg('Not a loadable gui module: %s' % key,
                                    msgType='error')
        ## Connect ALL the things!
        print('Connecting ALL the things!!')
        for logicmodule in self.definedLogic:
            thismodule = self.definedLogic[logicmodule]
            if logicmodule not in self.logic:
                self.logger.logMsg(
                    'Loading of logic module %s as %s was not successful, not connecting it.' % (thismodule['module'], logicmodule),
                    msgType='error')
                continue
            if 'connect' in thismodule:
                if 'in' not in  self.logic[logicmodule].connector:
                    self.logger.logMsg(
                        'Module %s loaded as %s is supposed to get connected but it does not declare any IN connectors.' % (thismodule['module'], logicmodule),
                        msgType='error')
                    continue
                if 'module' not in thismodule:
                    self.logger.logMsg(
                        'Logic module %s (%s) connection configuration is broken: no module defined.' % (logicmodule, thismodule['module'] ),
                        msgType='error')
                    continue
#                if thismodule['connect'] is not dict:
#                    self.logger.logMsg(
#                        'Logic module %s (%s) connection configuration is broken: connect is not a dict.' % (logicmodule, thismodule['module'] ),
#                        msgType='error')
#                    continue

                connections = thismodule['connect']
                for c in connections:
                    if c not in self.logic[logicmodule].connector['in']:
                        self.logger.logMsg(
                            'IN connector %s of module %s loaded as %s is supposed to get connected but is not declared in the module.' % (c, thismodule['module'], logicmodule),
                            msgType='error')
                        continue
#                    if self.logic[logicmodule].connector['in'][c] is not OrderedDict:
#                        self.logger.logMsg(
#                            'No dict.',
#                            msgType='error')
#                        continue
                    if 'class' not in self.logic[logicmodule].connector['in'][c]:
                        self.logger.logMsg(
                            'no class key in connection declaration',
                            msgType='error')
                        continue
#                    if self.logic[logicmodule].connector['in'][c]['class'] is not str:
#                        self.logger.logMsg(
#                            'value for class key is not a string',
#                            msgType='error')
#                        continue
                    if 'object' not in self.logic[logicmodule].connector['in'][c]:
                        self.logger.logMsg(
                            'no object key in connection declaration',
                            msgType='error')
                        continue
                    if self.logic[logicmodule].connector['in'][c]['object'] is not None:
                        self.logger.logMsg(
                            'object is not None, i.e. is already connected',
                            msgType='error')
                        continue
#                    if connections[c] is not str:
#                        self.logger.logMsg(
#                            'Logic module %s (%s) connection configuration is broken, value for key %s is not a string.' % (logicmodule, thismodule['module'], c ),
#                            msgType='error')
#                        continue
                    if '.' not in connections[c]:
                        self.logger.logMsg(
                            'Logic module %s (%s) connection configuration is broken, value %s for key %s does not contain a dot.' % (logicmodule, thismodule[module], connections[c], c ),
                            msgType='error')
                        continue
                    destmod = connections[c].split('.')[0]
                    destcon = connections[c].split('.')[1]
                    if destmod in self.hardware and destmod in self.logic:
                        self.logger.logMsg(
                            'Unique name %s is in both hardware and logic module list. Connection is not well defined, cannot connect %s (%s) to  it.' % (destmod, logicmodule, thismodule[module]),
                            msgType='error')
                        continue
                    ## connect to hardware module
                    elif destmod in self.hardware:
                        if 'out' not in  self.hardware[destmod].connector:
                            self.logger.logMsg(
                                'Module %s loaded as %s is supposed to get connected to module loaded as %s but that does not declare any OUT connectors.' % (thismodule['module'], logicmodule, destmod),
                                msgType='error')
                            continue
                        outputs = self.hardware[destmod].connector['out']
                        if destcon not in outputs:
                            self.logger.logMsg(
                                'OUT connector not declared',
                                msgType='error')
                            continue
#                        if outputs[destcon] is not OrderedDict:
#                            self.logger.logMsg(
#                                'not a dict',
#                                msgType='error')
#                            continue
                        if 'class' not in outputs[destcon]:
                            self.logger.logMsg(
                                'no class key in dict',
                                msgType='error')
                            continue
#                        if outputs[destcon]['class'] is not str:
#                            self.logger.logMsg(
#                                'class value no string',
#                                msgType='error')
#                            continue
#                        if not issubclass(self.hardware[destmod].__class__, outputs[destcon]['class']):
#                            self.logger.logMsg(
#                                'not the correct class for declared interface',
#                                msgType='error')
#                            continue

                        ## Finally set the connection object
                        self.logger.logMsg(
                                'Connecting %s.IN.%s to hardware %s.%s'%(logicmodule, c, destmod, destcon),
                                msgType='status')
                        self.logic[logicmodule].connector['in'][c]['object'] = self.hardware[destmod]
                                
                    ## connect to logic module
                    elif destmod in self.logic:
                        if 'out' not in  self.logic[destmod].connector:
                            self.logger.logMsg(
                                'Module %s loaded as %s is supposed to get connected to module loaded as %s but that does not declare any OUT connectors.' % (thismodule['module'], logicmodule, destmod),
                                msgType='error')
                            continue
                        outputs = self.logic[destmod].connector['out']
                        if destcon not in outputs:
                            self.logger.logMsg(
                                'OUT connector not declared',
                                msgType='error')
                            continue
#                        if outputs[destcon] is not OrderedDict:
#                            self.logger.logMsg(
#                                'not a dict',
#                                msgType='error')
#                            continue
#                        if 'class' not in outputs[destcon]:
#                            self.logger.logMsg(
#                                'no class key in dict',
#                                msgType='error')
#                            continue
                        if outputs[destcon]['class'] is not str:
                            self.logger.logMsg(
                                'class value no string',
                                msgType='error')
                            continue
#                        if not issubclass(self.logic[destmod].__class__, outputs[destcon]['class']):
#                            self.logger.logMsg(
#                                'not the correct class for declared interface',
#                                msgType='error')
#                            continue

                        ## Finally set the connection object
                        self.logger.logMsg(
                                'Connecting %s.IN.%s to logic %s.%s'%(logicmodule, c, destmod, destcon),
                                msgType='status')
                        self.logic[logicmodule].connector['in'][c]['object'] = self.logic[destmod]

                    else:
                        self.logger.logMsg(
                            'Unique name %s is neither in hardware or logic module list. Cannot connect %s (%s) to it.' % (connections[c], logicmodule, thismodule['module']),
                            msgType='error')
        ## FIXME Check for any disconnected modules and add their dummies
        ## FIXME Call Activate on all deactivated modules
        print('Activation starting!')
        for key in self.hardware:
            if self.hardware[key].getState() != 'deactivated':
                self.logger.logMsg(
                    'module %s not deactivated anymore' % key,
                    msgType='error')
                continue
            try:
                self.hardware[key].activate()
            except:
                self.logger.logExc(
                    '%s: error during activation:' % key,
                    msgType='error')
                        
        for key in self.logic:
            if self.logic[key].getState() != 'deactivated':
                self.logger.logMsg(
                    'module %s not deactivated anymore' % key,
                    msgType='error')
                continue
            try:
                self.logic[key].activate()
            except:
                self.logger.logExc(
                    '%s: error during activation:' % key,
                    msgType='error')
        for key in self.gui:
            if self.gui[key].getState() != 'deactivated':
                self.logger.logMsg(
                    'module %s not deactivated anymore' % key,
                    msgType='error')
                continue
            try:
                self.gui[key].activate()
            except:
                self.logger.logExc(
                    '%s: error during activation:' % key,
                    msgType='error')

    def reloadAll(self):
        """Reload all python code"""
        #path = os.path.split(os.path.abspath(__file__))[0]
        #path = os.path.abspath(os.path.join(path, '..'))
        path = '.'
        self.logger.print_logMsg("\n---- Reloading all libraries under %s ----" % path)
        reload.reloadAll(prefix=path, debug=True)
        self.logger.print_logMsg("Reloaded all libraries under %s." %path, msgType='status')
        
    def quit(self):
        """Nicely request that all modules shut down"""
        #QtCore.QObject.connect(app, QtCore.SIGNAL('lastWindowClosed()'), q)
        if not self.alreadyQuit:  ## Need this because multiple triggers can call this function during quit
            self.alreadyQuit = True
            print("Closing windows..")
            QtGui.QApplication.instance().closeAllWindows()
            QtGui.QApplication.instance().processEvents()
            print("\n    ciao.")
        QtGui.QApplication.quit()


 
    @staticmethod
    def toposort(deps, cost=None):
        """Topological sort. Arguments are:
        deps       Dictionary describing dependencies where a:[b,c] means "a 
                    depends on b and c"
        cost       Optional dictionary of per-node cost values. This will be used
                    to sort independent graph branches by total cost. 
                
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
            
            # This example is underspecified; there are several orders
            # that correctly satisfy the graph. However, we may use the
            # 'cost' argument to impose more constraints on the sort order.
            
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
            order = Task.toposort(deps)
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
                print(deps)
                raise Exception("Cannot resolve requested device configure/start order.")
            
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
        
