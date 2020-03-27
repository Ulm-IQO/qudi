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
import errno

from qudi.core.config import Configuration
from qudi.core.util.paths import get_main_dir
from qudi.core.parentpoller import ParentPollerUnix, ParentPollerWindows

rpyc.core.protocol.DEFAULT_CONFIG['allow_pickle'] = True


class QudiInterface:
    """
    """
    def __init__(self):
        config = Configuration()
        config.load_config(set_default=False)
        server_config = config.module_server
        print(server_config)
        if not server_config:
            raise Exception('No module_server config found in configuration file {0}'
                            ''.format(config.config_file))
        if 'address' not in server_config or 'port' not in server_config:
            raise Exception(
                'module_server configuration must contain mandatory entries "address" and "port".')
        self.host = server_config['address']
        self.port = server_config['port']
        self.certfile = server_config.get('certfile', None)
        self.keyfile = server_config.get('keyfile', None)
        self.conn_config = {'allow_all_attrs': True}

        self.parent_handle = int(os.environ.get('JPY_PARENT_PID', 0))
        # self.interrupt = int(os.environ.get('JPY_INTERRUPT_EVENT', 0))
        self.kernel_id = None
        self.connection = None
        self.parent_poller = None

    def connect(self, *args, **kwargs):
        logging.info('Connecting to {}:{}'.format(self.host, self.port))
        self.connection = rpyc.connect(self.host, self.port, config=self.conn_config)

    def get_kernel_manager(self):
        return self.connection.root.get_kernel_manager()

    def start_kernel(self, connfile):
        kernel_manager = self.get_kernel_manager()
        if kernel_manager is None:
            raise Exception('Unable to retrieve kernel manager from Qudi remote server')
        cfg = json.loads(''.join(open(connfile).readlines()))
        self.kernel_id = kernel_manager.start_kernel(cfg, self)
        print('======================== KERNEL ID:', self.kernel_id)

    def stop_kernel(self):
        logging.info('Shutting down: {}'.format(self.kernel_id))
        sys.stdout.flush()
        kernel_manager = self.get_kernel_manager()
        if kernel_manager is None:
            raise Exception('Unable to retrieve kernel manager from Qudi remote server')
        if self.kernel_id is not None:
            kernel_manager.stop_kernel(self.kernel_id, blocking=True)
            sys.stdout.flush()

    def init_signal(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    def init_poller(self):
        if self.parent_handle:
            if sys.platform == 'win32':
                self.parent_poller = ParentPollerWindows(self.parent_handle)
            else:
                self.parent_poller = ParentPollerUnix()

    def exit(self):
        sys.exit()


def install_kernel():
    from jupyter_client.kernelspec import KernelSpecManager
    print('Installing Qudi kernel.')

    try:
        # prepare temporary kernelspec folder
        tempdir = tempfile.mkdtemp(suffix='_kernels')
        path = os.path.join(tempdir, 'qudi')
        resource_path = os.path.join(path, 'resources')
        kernel_path = os.path.abspath(__file__)
        os.mkdir(path)
        os.mkdir(resource_path)

        kernel_dict = {'argv': [sys.executable, kernel_path, '{connection_file}'],
                       'display_name': 'Qudi',
                       'language': 'python'
                       }
        # write the kernelspec file
        with open(os.path.join(path, 'kernel.json'), 'w') as f:
            json.dump(kernel_dict, f, indent=1)

        # copy logo
        logo_path = os.path.join(get_main_dir(), 'core', 'artwork', 'logo')
        shutil.copy(os.path.join(logo_path, 'logo-qudi-32x32.png'),
                    os.path.join(resource_path, 'logo-32x32.png'))
        shutil.copy(os.path.join(logo_path, 'logo-qudi-32x32.png'),
                    os.path.join(resource_path, 'logo-32x32.png'))

        # install kernelspec folder
        kernel_spec_manager = KernelSpecManager()
        dest = kernel_spec_manager.install_kernel_spec(path, kernel_name='qudi', user=True)
        print('Installed kernelspec qudi in {}'.format(dest))
    except OSError as e:
        if e.errno == errno.EACCES:
            print(e, file=sys.stderr)
            sys.exit(1)
    finally:
        if os.path.isdir(tempdir):
            shutil.rmtree(tempdir)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='[%(levelname)1.1s %(asctime)s.%(msecs).03d %(name)s] %(message)s')
    if len(sys.argv) > 1:
        if sys.argv[1] == 'install':
            install_kernel()
        else:
            q = QudiInterface()
            q.init_signal()
            q.init_poller()
            q.connect()
            q.start_kernel(sys.argv[1])
            atexit.register(q.stop_kernel)
            logging.info('Sleeping.')
            q.parent_poller.run()
            logging.info('Quitting.')
            sys.stdout.flush()
    else:
        print('qudikernel usage is {0} <connectionfile> or {0} install'.format(sys.argv[0]),
              file=sys.stderr)
