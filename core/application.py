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

import sys
import os
import faulthandler
import weakref

from qtpy import QtCore, QtWidgets, API_NAME

from .logger import init_rotating_file_handler, get_logger
from .util.paths import get_main_dir, get_default_log_dir
from .util.helpers import import_check
from .util.mutex import RecursiveMutex, Mutex
from .config import Configuration
from .watchdog import AppWatchdog
from .modulemanager import ModuleManager
from .threadmanager import ThreadManager
from .gui.gui import Gui
from . import remotemodules

try:
    from zmq.eventloop import ioloop
except ImportError:
    pass


class Qudi(QtCore.QObject):
    """

    """
    _instance = None
    _run_lock = RecursiveMutex()
    _quit_lock = Mutex()

    def __new__(cls, *args, **kwargs):
        with cls._run_lock:
            if cls._instance is None or cls._instance() is None:
                obj = super().__new__(cls, *args, **kwargs)
                cls._instance = weakref.ref(obj)
                return obj
            raise Exception('Only one Qudi instance per process possible (Singleton). Please use '
                            'Qudi.instance() to get a reference to the already created instance.')

    def __init__(self, no_gui=False, log_dir='', config_file=None):
        # CLI arguments
        self.no_gui = bool(no_gui)
        self.log_dir = str(log_dir) if os.path.isdir(log_dir) else get_default_log_dir(
            create_missing=True)

        self.log = get_logger(__name__)
        self.thread_manager = ThreadManager()
        self.module_manager = ModuleManager(qudi_main=self)
        self.configuration = Configuration(config_file)
        self.watchdog = None
        self.gui = None

        self._configured_extension_paths = list()
        self._is_running = False
        self._shutting_down = False

    @classmethod
    def instance(cls):
        if cls._instance is None:
            return None
        return cls._instance()

    @property
    def is_running(self):
        return self._is_running

    def _remove_extensions_from_path(self):
        with self._run_lock:
            # Clean up previously configured expansion paths
            for ext_path in self._configured_extension_paths:
                if ext_path in sys.path:
                    sys.path.remove(ext_path)

    def _add_extensions_to_path(self):
        with self._run_lock:
            extensions = self.configuration.extension_paths
            # Add qudi extension paths to sys.path
            for ext_path in reversed(extensions):
                sys.path.insert(1, ext_path)
            self._configured_extension_paths = extensions

    @QtCore.Slot()
    def _configure_qudi(self):
        """
        """
        with self._run_lock:
            print('\n================= Starting Qudi configuration from "{0}" ================='
                  '\n'.format(self.configuration.config_file))
            self.log.info(
                'Starting Qudi configuration from "{0}"...'.format(self.configuration.config_file))

            # Clear all qudi modules
            self.module_manager.clear()

            # Configure extension paths
            self._remove_extensions_from_path()
            self._add_extensions_to_path()

            # Configure Qudi modules
            for base in ('gui', 'logic', 'hardware'):
                # Create ManagedModule instance by adding each module to ModuleManager
                for module_name, module_cfg in self.configuration.module_config[base].items():
                    try:
                        self.module_manager.add_module(name=module_name,
                                                       base=base,
                                                       configuration=module_cfg)
                    except:
                        self.module_manager.remove_module(module_name, ignore_missing=True)
                        self.log.exception('Unable to create ManagedModule instance for module '
                                           '"{0}.{1}"'.format(base, module_name))

            print("================= Qudi configuration complete =================\n")
            self.log.info('Qudi configuration complete.')

    def _start_gui(self):
        if self.no_gui:
            return
        self.gui = Gui(qudi_instance=self,
                       artwork_dir=os.path.join(get_main_dir(), 'artwork'),
                       stylesheet_path=self.configuration.stylesheet)
        self.gui.activate_main_gui()

    def run(self):
        """

        @return:
        """
        with self._run_lock:
            if self._is_running:
                raise Exception('Qudi is already running!')

            # add qudi to PATH
            qudi_path = get_main_dir()
            if qudi_path not in sys.path:
                sys.path.insert(1, qudi_path)

            # Enable stack trace output for SIGSEGV, SIGFPE, SIGABRT, SIGBUS and SIGILL signals
            # -> e.g. for segmentation faults
            faulthandler.disable()
            faulthandler.enable(all_threads=True)

            # install logging facility
            init_rotating_file_handler(path=self.log_dir)
            self.log.info('Loading Qudi...')
            print('Loading Qudi...')

            # Check Qt API
            self.log.info('Used Qt API: {0}'.format(API_NAME))
            print('Used Qt API: {0}'.format(API_NAME))

            # Check vital packages for qudi, otherwise qudi will not even start.
            err_code = import_check()
            if err_code != 0:
                sys.exit(err_code)

            # Get QApplication instance
            if self.no_gui:
                app = QtCore.QCoreApplication.instance()
            else:
                app = QtWidgets.QApplication.instance()
            if app is None:
                if self.no_gui:
                    app = QtCore.QCoreApplication(sys.argv)
                else:
                    app = QtWidgets.QApplication(sys.argv)

            # configure qudi
            self.configuration.load_config()
            self._configure_qudi()

            # Install the pyzmq ioloop.
            # This has to be done before anything else from tornado is imported.
            try:
                ioloop.install()
            except:
                self.log.error('Preparing ZMQ failed, probably no IPython possible!')

            # manhole for debugging stuff inside the app from outside
            # if args.manhole:
            #     import manhole
            #     manhole.install()

            # first disable our pyqtgraph's cleanup function; won't be needing it.
            # try:
            #     import pyqtgraph
            #     pyqtgraph.setConfigOptions(exitCleanup=False)
            # except ImportError:
            #     pass

            # Install app watchdog
            self.watchdog = AppWatchdog()

            # Start GUI if needed
            self._start_gui()

            # Start Qt event loop unless running in interactive mode
            self._is_running = True
            exit_code = app.exec_()
            self._shutting_down = False
            self._is_running = False

            # ToDo: Is the following issue still a thing with qudi?
            # in this subprocess we redefine the stdout, therefore on Unix systems we need to handle
            # the opened file descriptors, see PEP 446: https://www.python.org/dev/peps/pep-0446/
            if sys.platform in ('linux', 'darwin'):
                fd_min, fd_max = 3, 4096
                fd_set = set(range(fd_min, fd_max))

                if sys.platform == 'darwin':
                    # trying to close 7 produces an illegal instruction on the Mac.
                    fd_set.remove(7)

                # remove specified file descriptor
                for fd in fd_set:
                    try:
                        os.close(fd)
                    except OSError:
                        pass

            self.log.info('Shutdown complete! Ciao')
            print('\nShutdown complete! Ciao.')

            # Exit application
            sys.exit(exit_code)

    def exit(self, prompt=True, restart=False):
        """ Shutdown Qudi. Nicely request that all modules shut down if prompt is True.
        Signal restart to parent process (if present) via exitcode 42 if restart is True.
        """
        with self._quit_lock:
            if not self.is_running or self._shutting_down:
                return
            self._shutting_down = True
            if prompt:
                locked_modules = False
                broken_modules = False
                for module in self.module_manager.values():
                    if module.is_busy:
                        locked_modules = True
                    elif module.state == 'BROKEN':
                        broken_modules = True
                    if broken_modules and locked_modules:
                        break

                if self.no_gui:
                    # command line prompt
                    question = '\nSome modules are still locked. ' if locked_modules else '\n'
                    if restart:
                        question += 'Do you really want to restart Qudi (y/N)?: '
                    else:
                        question += 'Do you really want to quit Qudi (y/N)?: '
                    while True:
                        response = input(question).lower()
                        if response in ('y', 'yes'):
                            break
                        elif response in ('', 'n', 'no'):
                            return
                else:
                    # GUI prompt
                    if restart:
                        if not self.gui.prompt_restart(locked_modules):
                            return
                    else:
                        if not self.gui.prompt_shutdown(locked_modules):
                            return

            QtCore.QCoreApplication.instance().processEvents()
            self.log.info('Qudi shutting down...')
            print('Qudi shutting down...')
            self.log.info('Stopping remote modules...')
            print('Stopping remote modules...')
            remotemodules.stop_remote_server()
            QtCore.QCoreApplication.instance().processEvents()
            self.log.info('Stopping local modules...')
            print('Stopping local modules...')
            self.module_manager.clear()
            QtCore.QCoreApplication.instance().processEvents()
            if not self.no_gui:
                self.log.info('Closing windows...')
                print('Closing windows...')
                self.gui.close_windows()
                self.gui.close_system_tray_icon()
            QtCore.QCoreApplication.instance().processEvents()
            self.log.info('Stopping threads...')
            print('Stopping threads...')
            self.thread_manager.quit_all_threads()
            QtCore.QCoreApplication.instance().processEvents()
            if restart:
                QtCore.QCoreApplication.exit(42)
            else:
                QtCore.QCoreApplication.quit()

    @QtCore.Slot()
    def quit(self):
        self.exit(prompt=False, restart=False)

    @QtCore.Slot()
    def prompt_quit(self):
        self.exit(prompt=True, restart=False)

    @QtCore.Slot()
    def restart(self):
        self.exit(prompt=False, restart=True)

    @QtCore.Slot()
    def prompt_restart(self):
        self.exit(prompt=True, restart=True)

