# -*- coding: utf-8 -*-
"""
A module to control the QO Raspberry Pi based H-Bridge hardware.

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

from core.base import Base
from interface.data_logger_interface import DataLoggerInterface

from pyqtgraph.Qt import QtCore
from influxdb import InfluxDBClient

class InfluxLogger(Base, DataLoggerInterface):
    _modclass = 'InfluxLogger'
    _modtype = 'hardware'

    ## declare connectors
    _out = {'data': 'ProcessInterface'}
    
    def __init__(self, manager, name, config = {}, **kwargs):
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, configuration=config, callbacks = c_dict, **kwargs)
        self.log_channels = {}
        
    def activation(self, e):
        config = self.getConfiguration()

        if 'user' in config:
            self.user = config['user']

        if 'password' in config:
            self.pw = config['password']

        if 'dbname' in config:
            self.dbname = config['dbname']

        if 'host' in config:
            self.host = config['host']
           
        if 'port' in config:
            self.port = config['port']
        else:
            self.port = 8086

        if 'dataseries' in config:
            self.series = config['dataseries']

        if 'field' in config:
            self.field = config['field']

        if 'criterion' in config:
            self.cr = config['criterion']

        self.connect_db()

    def deactivation(self, e):
        del self.conn

    def connect_db(self):
        self.conn = InfluxDBClient(self.host, self.port, self.user, self.pw, self.dbname)

    def get_log_channels(self):
        return self.log_channels

    def set_log_channels(self, channelspec):
        for name, spec in channelspec.items():
            if spec is None and name in self.log_channels:
                self.log_channels.pop(name)
            elif name in self.log_channels:
            else:
                if :

            

    def log_to_channel(self, channel, values):
        if channel in self.log_channels.keys() and len(values) == len(self.log_channels[channel][values]):
            conn.write_points(format_data(channel, values, channeltags))

    def format_data(self, channel_name, values, tags):
        return [{
             'measurement': channel_name,
             'fields': values,
             'tags': tags
            }]

