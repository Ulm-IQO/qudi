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
import numpy
import sys
import rpyc
import json
import shutil
import logging
import tempfile
from ipykernel.ipkernel import IPythonKernel

from qudi.core.config import Configuration

__all__ = ('install_kernel', 'uninstall_kernel', 'QudiIPythonKernel', 'QudiKernelClient',
           'QudiKernelService')


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
            'argv': [sys.executable, kernel_path, '-f', '{connection_file}'],
            'display_name': 'Qudi',
            'language': 'python'
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


class QudiKernelService(rpyc.Service):
    """
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._background_server = None

    def on_connect(self, conn):
        logging.warning(f'Qudi IPython kernel connected to local module service.')
        self._background_server = rpyc.BgServingThread(conn)

    def on_disconnect(self, conn):
        logging.warning(f'Qudi IPython kernel disconnected from local module service.')
        try:
            self._background_server.stop()
        except:
            pass
        finally:
            self._background_server = None

    # Implement methods starting with 'exposed_' here in order to provide services to qudi module
    # server.


class QudiKernelClient:
    """
    """

    def __init__(self):
        self.service_instance = QudiKernelService()
        self.connection = None

    def get_active_modules(self):
        if self.connection is None or self.connection.closed:
            return dict()
        try:
            return self.connection.root.get_namespace_dict()
        except (ConnectionError, EOFError):
            self.disconnect()
            return dict()

    def connect(self):
        config = Configuration()
        config_path = Configuration.get_saved_config()
        if config_path is None:
            config_path = Configuration.get_default_config()
        config.load_config(file_path=config_path, set_default=False)
        port = config.namespace_server_port
        self.connection = rpyc.connect(host='localhost',
                                       config={'allow_all_attrs': True,
                                               'allow_setattr': True,
                                               'allow_delattr': True,
                                               'allow_pickle': True,
                                               'sync_request_timeout': 3600},
                                       port=port,
                                       service=self.service_instance)

    def disconnect(self):
        if self.connection is not None:
            try:
                self.connection.close()
            except:
                pass
            finally:
                self.connection = None


class QudiIPythonKernel(IPythonKernel):
    """
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._qudi_client = QudiKernelClient()
        self._qudi_client.connect()
        self._namespace_qudi_modules = set()
        self.update_module_namespace()

    def update_module_namespace(self):
        modules = self._qudi_client.get_active_modules()
        removed = self._namespace_qudi_modules.difference(modules)
        for mod in removed:
            self.shell.user_ns.pop(mod, None)
        self.shell.push(modules)
        self._namespace_qudi_modules = set(modules)

    # Update module namespace each time right before a cell is executed
    def do_execute(self, *args, **kwargs):
        self.update_module_namespace()
        return super().do_execute(*args, **kwargs)

    # Disconnect qudi remote module service before shutting down
    def do_shutdown(self, restart):
        self._qudi_client.disconnect()
        return super().do_shutdown(restart)


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'install':
        install_kernel()
    elif len(sys.argv) == 2 and sys.argv[1] == 'uninstall':
        uninstall_kernel()
    else:
        from ipykernel.kernelapp import IPKernelApp

        IPKernelApp.launch_instance(kernel_class=QudiIPythonKernel)
