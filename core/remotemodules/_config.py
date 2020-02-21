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

import ssl
import rpyc


class Config:
    _protocol_config = {'allow_all_attrs': True}
    _ssl_version = ssl.PROTOCOL_TLSv1_2
    _cert_reqs = ssl.CERT_REQUIRED
    _ciphers = 'EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH'
    _port = 12345
    _host = 'localhost'
    _certfile = None
    _keyfile = None
    _allow_pickle = True

    def __init__(self):
        self.configure(**self.configuration)

    @property
    def configuration(self):
        return {'protocol_config': self.protocol_config,
                'ssl_version': self.ssl_version,
                'cert_reqs': self.cert_reqs,
                'ciphers': self.ciphers,
                'port': self.port,
                'host': self.host,
                'certfile': self.certfile,
                'keyfile': self.keyfile,
                'allow_pickle': self.allow_pickle}

    @property
    def protocol_config(self):
        return Config._protocol_config.copy()

    @property
    def ssl_version(self):
        return Config._ssl_version

    @property
    def cert_reqs(self):
        return Config._cert_reqs

    @property
    def ciphers(self):
        return Config._ciphers

    @property
    def port(self):
        return Config._port

    @property
    def host(self):
        return Config._host

    @property
    def allow_pickle(self):
        return Config._allow_pickle

    @property
    def certfile(self):
        return Config._certfile

    @property
    def keyfile(self):
        return Config._keyfile

    @classmethod
    def configure(cls, **kwargs):
        for key, value in kwargs.items():
            attr_name = '_' + key
            if hasattr(cls, attr_name):
                setattr(cls, attr_name, value)
        rpyc.core.protocol.DEFAULT_CONFIG['allow_pickle'] = cls._allow_pickle


config = Config()
