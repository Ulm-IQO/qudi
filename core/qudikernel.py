# -*- coding: utf-8 -*-
"""
Jupyter notebook kernel executable file for Qudi.

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
import sys
import rpyc
import json
import logging
import signal
import atexit
import shutil
import tempfile

import config

try:
    from .parentpoller import ParentPollerUnix, ParentPollerWindows
except ImportError:
    from parentpoller import ParentPollerUnix, ParentPollerWindows

rpyc.core.protocol.DEFAULT_CONFIG['allow_pickle'] = True


class Qudi:

    def __init__(self):
        conf = self.getConfigFromFile(self.getConfigFile())
        self.host, self.port, self.certfile, self.keyfile = conf
        self.conn_config = {'allow_all_attrs': True}
        self.parent_handle = int(os.environ.get('JPY_PARENT_PID') or 0)
        self.interrupt = int(os.environ.get('JPY_INTERRUPT_EVENT') or 0)
        self.kernelid = None

    def connect(self, **kwargs):
        logging.info('Connecting to {}:{}'.format(self.host, self.port))
        self.connection = rpyc.connect(self.host, self.port, config=self.conn_config)

    def getModule(self, name):
        return self.connection.root.getModule(name)

    def startKernel(self, connfile):
        m = self.getModule('kernellogic')
        cfg = json.loads("".join(open(connfile).readlines()))
        self.kernelid = m.startKernel(cfg, self)
        logging.info('Kernel up: {}'.format(self.kernelid))

    def stopKernel(self):
        logging.info('Shutting down: {}'.format(self.kernelid))
        sys.stdout.flush()
        m = self.getModule('kernellogic')
        if self.kernelid is not None:
            m.stopKernel(self.kernelid)
            logging.info('Down!')
            sys.stdout.flush()

    def initSignal(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    def initPoller(self):
        if sys.platform == 'win32':
            if self.interrupt or self.parent_handle:
                self.poller = ParentPollerWindows(self.interrupt, self.parent_handle)
        elif self.parent_handle:
            self.poller = ParentPollerUnix()

    def exit(self):
        sys.exit()

    def getMainDir(self):
        """Returns the absolut path to the directory of the main software.

             @return string: path to the main tree of the software

        """
        return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def getConfigFile(self):
        """ Search all the default locations to find a configuration file.

          @return sting: path to configuration file
        """
        path = self.getMainDir()
        # we first look for config/load.cfg which can point to another
        # config file using the "configfile" key
        loadConfigFile = os.path.join(path, 'config', 'load.cfg')
        if os.path.isfile(loadConfigFile):
            logging.info('load.cfg config file found at {0}'.format(loadConfigFile))
            try:
                confDict = config.load(loadConfigFile)
                if 'configfile' in confDict and isinstance(confDict['configfile'], str):
                    # check if this config file is existing
                    # try relative filenames
                    configFile = os.path.join(path, 'config', confDict['configfile'])
                    if os.path.isfile(configFile):
                        logging.info('Config file found at {0}'.format(configFile))
                        return configFile
                    # try absolute filename or relative to pwd
                    if os.path.isfile(confDict['configfile']):
                        logging.info('Config file found at {0}'.format(confDict['configfile']))
                        return confDict['configfile']
                    else:
                        logging.critical('Couldn\'t find config file specified in load.cfg: {0}'
                                         ''.format(confDict['configfile']))
            except Exception:
                logging.exception('Error while handling load.cfg.')
        # try config/example/custom.cfg next
        cf = os.path.join(path, 'config', 'example', 'custom.cfg')
        if os.path.isfile(cf):
            return cf
        # try config/example/default.cfg
        cf = os.path.join(path, 'config', 'example', 'default.cfg')
        if os.path.isfile(cf):
            return cf
        raise Exception('Could not find any config file.')

    def getConfigFromFile(self, configfile):
        cfg = config.load(configfile)
        if 'module_server' in cfg['global']:
            if not isinstance(cfg['global']['module_server'], dict):
                raise Exception('"module_server" entry in "global" section of configuration'
                                ' file is not a dictionary.')
            else:
                # new style
                server_address = cfg['global']['module_server'].get('address', 'localhost')
                server_port = cfg['global']['module_server'].get('port', 12345)
                certfile = cfg['global']['module_server'].get('certfile', None)
                keyfile = cfg['global']['module_server'].get('keyfile', None)

        elif 'serveraddress' in cfg['global']:
            logging.warning('Deprecated remote server settings. Please update to new style.'
                            ' See documentation.')
            server_address = cfg['global'].get('serveraddress', 'localhost')
            server_port = cfg['global'].get('serverport', 12345)
            certfile = cfg['global'].get('certfile', None)
            keyfile = cfg['global'].get('keyfile', None)

        return server_address, server_port, certfile, keyfile


def install_kernel():
    from jupyter_client.kernelspec import KernelSpecManager
    logging.info('Installing Qudi kernel.')

    try:
        # prepare temporary kernelspec folder
        tempdir = tempfile.mkdtemp(suffix='_kernels')
        path = os.path.join(tempdir, 'qudi')
        resourcepath = os.path.join(path, 'resources')
        kernelpath = os.path.abspath(__file__)
        os.mkdir(path)
        os.mkdir(resourcepath)

        kernel_dict = {
            'argv': [sys.executable, kernelpath, '{connection_file}'],
            'display_name': 'Qudi',
            'language': 'python',
        }
        # write the kernelspe file
        with open(os.path.join(path, 'kernel.json'), 'w') as f:
            json.dump(kernel_dict, f, indent=1)

        # copy logo
        logopath = os.path.abspath(os.path.join(os.path.dirname(kernelpath), '..', 'artwork', 'logo'))
        shutil.copy(os.path.join(logopath, 'logo-qudi-32x32.png'), os.path.join(resourcepath, 'logo-32x32.png'))
        shutil.copy(os.path.join(logopath, 'logo-qudi-32x32.png'), os.path.join(resourcepath, 'logo-32x32.png'))

        # install kernelspec folder
        kernel_spec_manager = KernelSpecManager()
        dest = kernel_spec_manager.install_kernel_spec(path, kernel_name='qudi', user=True)
        logging.info('Installed kernelspec qudi in {}'.format(dest))
    except OSError as e:
        if e.errno == errno.EACCES:
            print(e, file=sys.stderr)
            sys.exit(1)
    finally:
        if os.path.isdir(tempdir):
            shutil.rmtree(tempdir)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)1.1s %(asctime)s.%(msecs).03d %(name)s] %(message)s"
    )
    if len(sys.argv) > 1:
        if sys.argv[1] == 'install':
            install_kernel()
        else:
            q = Qudi()
            q.initSignal()
            q.initPoller()
            q.connect()
            q.startKernel(sys.argv[1])
            atexit.register(q.stopKernel)
            logging.info('Sleeping.')
            q.poller.run()
            logging.info('Quitting.')
            sys.stdout.flush()
    else:
        print('qudikernel usage is {0} <connectionfile> or {0} install'.format(sys.argv[0]), file=sys.stderr)
