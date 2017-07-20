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

from core.module import Base, ConfigOption
from interface.process_interface import ProcessInterface


class InfluxDataClient(Base, ProcessInterface):
    """ Retrieve live data from InfluxDB as if the measurement device was connected directly.
    """

    _modclass = 'InfluxDataClient'
    _modtype = 'hardware'

    user = ConfigOption('user', missing='error')
    pw = ConfigOption('password', missing='error')
    dbname = ConfigOption('dbname', missing='error')
    host = ConfigOption('host', missing='error')
    port = ConfigOption('port', 8086)
    series = ConfigOption('dataseries', missing='error')
    field = ConfigOption('field', missing='error')
    cr = ConfigOption('criterion', missing='error')

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

