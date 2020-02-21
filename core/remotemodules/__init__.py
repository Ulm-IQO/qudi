# -*- coding: utf-8 -*-
"""
This file contains the Qudi remotemodules object manager class.

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

from urllib.parse import urlparse
import rpyc

from core.threadmanager import thread_manager
from ._config import config
from .remote import share_module, remove_shared_module
from .remote import _RemoteServer, _RemoteModulesService, SharedModulesModel

__all__ = ('config', 'get_remote_module_instance', 'remote_server', 'remove_shared_module',
           'share_module', 'start_remote_server', 'stop_remote_server', 'SharedModulesModel')

remote_server = None


def get_remote_module_instance(url, certfile=None, keyfile=None, protocol_config=None):
    parsed = urlparse(url)
    name = parsed.path.replace('/', '')
    if protocol_config is None:
        protocol_config = config.protocol_config
    connection = rpyc.ssl_connect(host=parsed.hostname,
                                  port=parsed.port,
                                  config=protocol_config,
                                  certfile=certfile,
                                  keyfile=keyfile)
    return connection.root.get_module_instance(name)


def start_remote_server(**kwargs):
    global remote_server
    if kwargs:
        config.configure(**kwargs)
    server_thread = thread_manager.get_new_thread('remote-server')
    remote_server = _RemoteServer(_RemoteModulesService(), config=config.configuration)
    remote_server.moveToThread(server_thread)
    server_thread.started.connect(remote_server.run)
    server_thread.start()


def stop_remote_server():
    global remote_server
    if remote_server is not None:
        try:
            remote_server.stop()
            thread_manager.quit_thread('remote-server')
            thread_manager.join_thread('remote-server', time=5)
        except Exception:
            raise
        finally:
            remote_server = None
