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
from ipykernel.ipkernel import IPythonKernel

from qudi.core.config import Configuration
from qudi.core.paths import get_artwork_dir
from qudi.core.parentpoller import ParentPollerUnix, ParentPollerWindows


class QudiInterface:
    """
    """
    def __init__(self):
        config = Configuration()
        config_path = Configuration.get_saved_config()
        if config_path is None:
            config_path = Configuration.get_default_config()
        config.load_config(file_path=config_path, set_default=False)
        self.port = config.local_module_server_port
        self.connection = None

    @property
    def active_module_names(self):
        try:
            return self.connection.root.get_active_module_names()
        except:
            return tuple()

    @property
    def active_modules(self):
        try:
            return self.connection.root.get_active_module_instances()
        except:
            return dict()

    def get_module_instance(self, module_name):
        try:
            return self.connection.root.get_module_instance(module_name)
        except:
            return None

    def connect(self):
        logging.info(f'Connecting to local module service on [127.0.0.1]:{self.port:d}')
        self.connection = rpyc.connect('127.0.0.1', self.port, config={'allow_all_attrs': True})

    def disconnect(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None


def install_kernel():
    from jupyter_client.kernelspec import KernelSpecManager

    print('> Installing Qudi kernel...')
    try:
        # prepare temporary kernelspec folder
        tempdir = tempfile.mkdtemp(suffix='_kernels')
        path = os.path.join(tempdir, 'qudi')
        kernel_path = os.path.abspath(__file__)
        os.mkdir(path)

        kernel_dict = {
            'argv'        : [sys.executable, kernel_path, '-f', '{connection_file}'],
            'display_name': 'Qudi',
            'language'    : 'python'
        }
        # write the kernelspec file
        with open(os.path.join(path, 'kernel.json'), 'w') as f:
            json.dump(kernel_dict, f, indent=1)

        # install kernelspec folder
        kernel_spec_manager = KernelSpecManager()
        dest = kernel_spec_manager.install_kernel_spec(path, kernel_name='qudi', user=True)
        print(f'> Successfully installed kernelspec "qudi" in {dest}')
    finally:
        if os.path.isdir(tempdir):
            shutil.rmtree(tempdir)


def uninstall_kernel():
    from jupyter_client.kernelspec import KernelSpecManager

    print('> Uninstalling Qudi kernel...')
    try:
        KernelSpecManager().remove_kernel_spec('qudi')
    except KeyError:
        print('> No kernelspec "qudi" found')
    else:
        print('> Successfully uninstalled kernelspec "qudi"')


class QudiIPythonKernel(IPythonKernel):
    """

    """
    def __init__(self, *args, **kwargs):
        self._qudi_remote = QudiInterface()
        self._qudi_remote.connect()
        super().__init__(*args, **kwargs)
        self._namespace_qudi_modules = set()
        self._update_module_namespace()

    def _update_module_namespace(self):
        modules = self._qudi_remote.active_modules
        removed = self._namespace_qudi_modules.difference(modules)
        for mod in removed:
            self.shell.user_ns.pop(mod, None)
        self.shell.push(modules)
        self._namespace_qudi_modules = set(modules)

    # Update module namespace each time right before a cell is excecuted
    def do_execute(self, *args, **kwargs):
        self._update_module_namespace()
        return super().do_execute(*args, **kwargs)

    # Disconnect qudi remote module service before shutting down
    def do_shutdown(self, restart):
        self._qudi_remote.disconnect()
        return super().do_shutdown(restart)


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'install':
        install_kernel()
    elif len(sys.argv) == 2 and sys.argv[1] == 'uninstall':
        uninstall_kernel()
    else:
        from ipykernel.kernelapp import IPKernelApp
        IPKernelApp.launch_instance(kernel_class=QudiIPythonKernel)
