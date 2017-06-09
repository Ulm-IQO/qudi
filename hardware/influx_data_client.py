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

from influxdb import InfluxDBClient

from core.base import Base
from interface.process_interface import ProcessInterface


class InfluxDataClient(Base, ProcessInterface):
    """ Retrieve live data from InfluxDB as if the measurement device was connected directly.
    """

    _modclass = 'InfluxDataClient'
    _modtype = 'hardware'

    def on_activate(self):
        """ Activate module.
        """
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

    def on_deactivate(self):
        """ Deactivate module.
        """
        del self.conn

    def connect_db(self):
        """ Connect to Influx database """
        self.conn = InfluxDBClient(self.host, self.port, self.user, self.pw, self.dbname)

    def getProcessValue(self):
        """ Return a measured value """
        q = 'SELECT last({0}) FROM {1} WHERE (time > now() - 10m AND {2})'.format(self.field, self.series, self.cr)
        #print(q)
        res = self.conn.query(q)
        return list(res[('{0}'.format(self.series), None)])[0]['last']

    def getProcessUnit(self):
        """ Return the unit that the value is measured in

            @return (str, str): a tuple of ('abreviation', 'full unit name')
        """
        return '°C', ' degrees Celsius'

