# -*- coding: utf-8 -*-
"""
A module to control the QO Raspberry Pi based H-Bridge hardware.

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

from core.module import Base, ConfigOption
from interface.data_logger_interface import DataLoggerInterface

from influxdb import InfluxDBClient

class InfluxLogger(Base, DataLoggerInterface):
    """ Log instrument values to InfluxDB.
    """
    _modclass = 'InfluxLogger'
    _modtype = 'hardware'

    user = ConfigOption('user', missing='error')
    pw = ConfigOption('password', missing='error')
    dbname = ConfigOption('dbname', missing='error')
    host = ConfigOption('host', missing='error')
    port = ConfigOption('port', 8086)
    series = ConfigOption('dataseries', missing='error')
    field = ConfigOption('field', missing='error')
    cr = ConfigOption('criterion', missing='error')


    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.log_channels = {}

    def on_activate(self):
        """ Activate module.
        """
        self.connect_db()

    def on_deactivate(self):
        """ Deactivate module.
        """
        del self.conn

    def connect_db(self):
        """ Connect to Influx database """
        self.conn = InfluxDBClient(self.host, self.port, self.user, self.pw, self.dbname)

    def get_log_channels(self):
        """ Get number of logging channels

            @return int: number of channels
        """
        return self.log_channels

    def set_log_channels(self, channelspec):
        """ Set number of logging channels.

            @param channelspec dict: name, spec
        """
        for name, spec in channelspec.items():
            if spec is None and name in self.log_channels:
                self.log_channels.pop(name)
            elif name in self.log_channels:
                pass
            else:
                pass
                if True:
                    pass

    def log_to_channel(self, channel, values):
        """ Log values to a specific channel.

            @param channel str: channel name
            @param values list: data to be logged
        """
        if channel in self.log_channels.keys() and len(values) == len(self.log_channels[channel][values]):
            conn.write_points(format_data(channel, values, channeltags))

    def format_data(self, channel_name, values, tags):
        """ Format data according to InfluxDB JSON API.

            @param channel_name str: channel name
            @param values list: data
            @param tags list(str): list of tags
        """
        return [{
             'measurement': channel_name,
             'fields': values,
             'tags': tags
            }]

