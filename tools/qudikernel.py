# -*- coding: utf-8 -*-
"""
Jupyter notebook kernel executable file for QuDi.

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
"""

import os
import sys
import rpyc
import time
import json
import logging
import signal
import atexit
import shutil
import tempfile

from parentpoller import ParentPollerUnix, ParentPollerWindows

rpyc.core.protocol.DEFAULT_CONFIG['allow_pickle'] = True

class QuDi:

    def __init__(self):
        self.host = 'localhost'
        self.port = 12345
        self.conn_config = {'allow_all_attrs': True}
        self.parent_handle = int(os.environ.get('JPY_PARENT_PID') or 0)
        self.interrupt = int(os.environ.get('JPY_INTERRUPT_EVENT') or 0)
        self.kernelid = None

    def connect(self, **kwargs):
        self.connection = rpyc.connect(self.host, self.port, config=self.conn_config)

    def getModule(self, name):
        return self.connection.root.getModule(name)

    def startKernel(self, connfile):
        m = self.getModule('kernellogic')
        config = json.loads("".join(open(connfile).readlines()))
        self.kernelid = m.startKernel(config, self)
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


def install_kernel():
        from jupyter_client.kernelspec import KernelSpecManager
        logging.info('Installing QuDi kernel.')

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
                'display_name': 'QuDi',
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
            q = QuDi()
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
