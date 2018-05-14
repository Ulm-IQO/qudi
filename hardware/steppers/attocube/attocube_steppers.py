# -*- coding: utf-8 -*-

"""
This module contains the Qudi Hardware module attocube ANC300 .

---

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

import telnetlib
import time
import re

from core.module import Base, ConfigOption
from interface.steppers_interface import SteppersInterface


class AttoCubeStepper(Base, SteppersInterface):
    """
    """

    _modtype = 'AttoCubeStepper'
    _modclass = 'hardware'

    _interface_type = ConfigOption('interface_type', missing='error')  # 'usb'|'ethernet'

    _host = ConfigOption('host', None)
    _password = ConfigOption('password', b"123456")
    _port = ConfigOption('port', 7230)

    _interface = ConfigOption('interface', None)

    _default_axis = {
        'voltage_range': [0, 60],
        'frequency_range': [0, 10000],
        'position_range': [0, 5],
        'feedback': False,
        'frequency': 20,
        'voltage': 30,
        'capacitance': None,
        'busy': False
    }
    _connected = False

    _axis_config = ConfigOption('axis', {}, missing='error')
    #   axis:
    #       x:
    #            id:   1
    #            position_range: [0, 5]
    #            voltage_range: [0,10]
    #            frequency_range: [0,20]
    #            feedback: False
    #            'frequency': 20,
    #            'voltage': 30
    #       y:
    #            id: 2
    #            ...

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        self._check_axis()
        self._check_connection()
        self._connect()

        if self.connected:
            self._initalize_axis()

    def _check_axis(self):
        for name, axis in self._axis_config:
            if 'id' not in axis:
                self.log.error('id of axis {} is not defined in config file.'.format(name))
            # check _axis_config and set default value if not defined
            for key, default_value in self._default_axis:
                if key not in axis:
                    axis[key] = default_value

    def _check_connection(self):
        if self._interface_type == 'ethernet':
            if self._host is None:
                self.log.error('Ethernet connection required but no host have been specified')
        elif self._interface_type == 'usb':
            if self._interface is None:
                self.log.error('Usb connection required but interface have been specified. (ex: COM2)')
        else:
            self.log.error("Wrong interface type, option are 'ethernet' or 'usb'")

    def _initalize_axis(self):
        for name, axis in self._axis_config:
            self.capacitance(name)  # capacitance leaves axis in step mode
            self.frequency(name, axis['frequency'])
            self.voltage(name, axis['voltage'])

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._disconnect()

    def _connect(self, attempt=7):
        """
        Try to connect to the ANC300
        """
        self.connected = False

        if self._interface_type == 'ethernet':

            self.tn = telnetlib.Telnet(self._host, self._port)
            self.tn.open(self._host, self._port)
            password = str(self._password).encode('ascii')
            counter = 0
            while not self.connected:
                if counter > attempt:
                    self.log.error('Connection to ANC300 could not be established.\n'
                                   'Check password, physical connection, host etc. and try again.')
                    break
                self.tn.read_until(b"Authorization code: ")
                self.tn.write(password + b"\n")
                time.sleep(0.1)  # the ANC300 needs time to answer
                value_binary = self.tn.read_very_eager()
                value = value_binary.decode().split()
                if value[2] == 'success':
                    self.connected = True
                    self.log.info("Connection to ANC300 was established")
                else:
                    counter += 1
            self.tn.read_very_eager()  # clear the buffer

        elif self._interface_type == 'usb':
            pass  # TODO

    def _disconnect(self, keep_active=False):
        # Put eve
        if not keep_active:
            for name, axis_config in self._axis_config:
                self._send_cmd("setm {} gnd".format(self._axis_config[name]['id']))

        if self._interface_type == 'ethernet':
            self.tn.close()
        elif self._interface_type == 'usb':
            pass  # TODO

    def _send_cmd(self, cmd, read=True, regex=None, timeout=1):
        """Sends a command to the attocube steppers and parse the response

        @param str cmd: command to send
        @param bool read: if True, try reading the message, otherwise do not read (saves at least 30ms per call)
        @param str regex: regular expression used to parse expected response

        @return int: return None for silent, False for error, true if OK and array or match for regular expression
        """
        full_cmd = cmd.encode('ascii') + b"\r\n"  # converting to binary

        if self._interface_type == 'ethernet':
            self.tn.read_eager()  # disregard old print outs
            self.tn.write(full_cmd)  # send command
            # any response ends with ">" from the attocube. Therefore connection waits until this happened
            if not read:
                return None  # stop here and do not read
            else:
                try:
                    value_binary = self.tn.read_until(b">", timeout=timeout)
                    response = value_binary.decode()
                except:
                    self.log.error("Piezo steppers controller telnet timed out ({} second)".format(timeout))
                    return False
        elif self._interface_type == 'usb':
            pass
            return None

        # check for error
        error_search = re.search("ERROR", response)
        if error_search:
            self.log.error('Piezo steppers controller returned an error message : {}'.format(response))
            return False

        if regex is None:
            if bool(re.search("OK", response)):
                return True
            else:
                self.log.error('Piezo steppers controller did not return "OK" : {}'.format(response))
        else:
            return re.findall(regex, response)

    def _parse_axis(self, axis):
        """
        Take an valid axis or list/tuple of axis and return a list with valid axis name.
        By doing this we have the same universal axis input for all module functions
        'x' -> ['x']
        1 -> ['x']
        ['x', 2] -> ['x', 'y']
        """
        if type(axis) == int or type(axis) == str:
            return [self._get_axis_name(axis)]
        if type(axis)==list or type(axis)==tuple:
            result = []
            for a in axis:
                result.append(self._get_axis_name(a))
            return result
        else:
            self.log.error('Can not parse axis : {}'.format(axis))

    def _get_axis_name(self, axis):
        """
        Get an axis identifier (integer or name), and return axis name after checking axis is valid
        """
        if type(axis) == str:
            if axis in self._axis_config:
                return axis
        if type(axis) == int:
            for name, axis_config in self._axis_config:
                if axis_config['id'] == axis:
                    return name
        # if still not found, we error
        self.log.error('Axis {} is not defined in config file'.format(axis))

    def _parse_result(self, axis, result):
        """
        Take a valid axis input and list result and convert result to original format
        'x' [1000] -> 10000
        ['x', 3] [0.5, 1.2] -> [0.5, 1.2]
        """
        if type(axis) == int or type(axis) == str:
            return result[0]
        if type(axis) == tuple:
            return tuple(result)
        else:
            return result

    def _get_config(self, axis, key):
        """
        Get a value in axis config for a key for a given axis input and return with same format
        """
        parsed_axis = self._parse_axis(axis)
        result = []
        for ax in parsed_axis:
            value = self._axis_config[ax][key]
            if type == list:  # protect mutable shallow array (ranges)
                result.append(tuple(value))
            else:
                result.append(value)
        return self._parse_result(axis, result)

    def _parse_value(self, axis, ax, value):
        """
        For a given axis input and a given ax, return the value that make the most sense
        """
        if type(value) == float or type(value) == int:  # a single number : we return it
            return value
        elif type(value) == list or type(value) == tuple:  # an array
            if len(value) == 1:  # a single object in array : we return it
                return value[0]
            elif len(value) == len(axis):  # one to one correspondence with axis
                return value[axis.index(ax)]
            else:
                self.log.error('Could not set value for axis {}, value list length is incorrect')

    def _in_range(self, value, value_range, error_message=None):
        mini, maxi = value_range
        ok = mini <= value <= maxi
        if not ok and error_message is not None:
            self.log.error('{} - Value {} in not in range [{}, {}'.format(error_message, value, mini, maxi))
        return ok

    def voltage_range(self, axis):
        return self._get_config(axis, 'voltage_range')

    def frequency_range(self, axis):
        return self._get_config(axis, 'frequency_range')

    def position_range(self, axis):
        return self._get_config(axis, 'position_range')

    def voltage(self, axis, value=None, buffered=False):
        """
        Function that get or set the voltage of one ore multiple axis
        :param axis: axis input : 'x', 2, ['z', 3]...
        :param value: value for axis : 1.0, [1.0], [2.5, 2.8]...
        :param buffered: if set to True, just return the last read voltage without asking the controller
        :return: return the voltage of the axis with the same format than axis input
        """
        parsed_axis = self._parse_axis(axis)
        if value is not None:
            for ax in parsed_axis:
                new_value = self._parse_value(axis, ax, value)
                if self._in_range(new_value, self.voltage_range(ax), 'Voltage out of range'):
                    command = "setv {} {}".format(self._axis_config[ax]['id'], new_value)
                    self._send_cmd(command)

        if not buffered:
            for ax in parsed_axis:
                commmand = "getv {}".format(self._axis_config[ax]['id'])
                regex = 'voltage = ([-+]?\d*\.\d+) V'  # voltage = 0.000000 V
                result = self._send_cmd(commmand, True, regex)
                if len(result) == 0:
                    self.log.error('Voltage of axis {} could not be read : {}'.format(ax, result))
                self._axis_config[ax]['voltage'] = float(result[0])
                if not self._in_range(self._axis_config[ax]['voltage'], self._axis_config[ax]['voltage_range']):
                    self.log.warning('Current voltage of axis {} is out of range.'.format(ax))

        return self._get_config(axis, 'voltage')

    def frequency(self, axis, value=None, buffered=False):
        """
        Function that get or set the frequency of one ore multiple axis
        :param axis: axis input : 'x', 2, ['z', 3]...
        :param value: value for axis : 100, [200], [500, 1000]...
        :param buffered: if set to True, just return the last read voltage without asking the controller
        :return: return the frequency of the axis with the same format than axis input
        """
        parsed_axis = self._parse_axis(axis)
        if value is not None:
            for ax in parsed_axis:
                new_value = int(self._parse_value(axis, ax, value))
                if self._in_range(new_value, self.frequency_range(ax), 'Frequency out of range'):
                    command = "setf {} {}".format(self._axis_config[ax]['id'], new_value)
                    self._send_cmd(command)

        if not buffered:
            for ax in parsed_axis:
                commmand = "getf {}".format(self._axis_config[ax]['id'])
                regex = 'frequency = (\d+) Hz'  # frequency = 1000 Hz
                result = self._send_cmd(commmand, True, regex)
                if len(result) == 0:
                    self.log.error('Frequency of axis {} could not be read : {}'.format(ax, result))
                self._axis_config[ax]['frequency'] = int(result[0])
                if not self._in_range(self._axis_config[ax]['frequency'], self._axis_config[ax]['frequency_range']):
                    self.log.warning('Current frequency of axis {} is out of range.'.format(ax))

        return self._get_config(axis, 'frequency')

    def capacitance(self, axis, buffered=False):
        """

        :param axis:
        :param buffered:
        :return:
        """
        parsed_axis = self._parse_axis(axis)
        if not buffered:
            for ax in parsed_axis:
                self._axis_config[ax]['busy'] = True
                self._send_cmd("setm {} cap".format(self._axis_config[ax]['id']))
                self._send_cmd("capw {}".format(self._axis_config[ax]['id']))
                commmand = "getc {}".format(self._axis_config[ax]['id'])
                regex = 'capacitance = (\d+) (mF|µF|nF)'
                result = self._send_cmd(commmand, True, regex)
                self._send_cmd("setm {} stp".format(self._axis_config[ax]['id']))
                self._axis_config[ax]['busy'] = False
                if len(result) < 2:
                    self.log.error('Capacitance of axis {} could not be read : {}'.format(ax, result))
                factor = {'mF': 1e-3, 'µF': 1e-6, 'nF': 1e-9}
                self._axis_config[ax]['capacitance'] = float(result[0])*factor[result[1]]

        return self._get_config(axis, 'capacitance')

    def steps(self, axis, number):
        parsed_axis = self._parse_axis(axis)
        for ax in parsed_axis:
            if self._axis_config[ax]['busy']:
                self.warning('Stepping might not work while axis {} in capacitance measurement'.format(ax))
            number_step_axis = int(self._parse_value(axis, ax, number))
            if number_step_axis > 0:
                self._send_cmd("stpu {} {}".format(self._axis_config[ax]['id'], number_step_axis))
            elif number_step_axis < 0:
                self._send_cmd("stpd {} {}".format(self._axis_config[ax]['id'], -number_step_axis))
