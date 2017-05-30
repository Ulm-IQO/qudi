# -*- coding: utf-8 -*-

"""
This module contains the Qudi Hardware module attocube ANC300 .

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

from core.base import Base
from interface.confocal_stepper_interface import ConfocalStepperInterface
import numpy as np

_mode_list = ["gnd", "inp", "cap", "stp", "off", "stp+", "stp-"]


class AttoCubeStepper(Base, ConfocalStepperInterface):
    """ 
    """

    _modtype = 'AttoCubeStepper'
    _modclass = 'hardware'

    def on_activate(self):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """
        config = self.getConfiguration()

        # some default values for the hardware:
        self._voltage_range_stepper_default = [0, 60]
        self._frequency_range_default = [0, 10000]
        self._password_default = b"123456"
        self._port_default = 7230

        self._voltage_range_res = [0., 2.]
        # Todo get rid of all fine/coarse definition stuff, only step voltage will remain


        # handle all the parameters given by the config

        self._attocube_axis = {}  # dictionary contains the axes and the specific controller
        if 'x' in config.keys():
            self._attocube_axis["x"] = config['x']
        else:
            self.log.error(
                'No axis "x" found in configuration!\n'
                'Assign to that parameter an appropriated channel sorting!')

        if 'y' in config.keys():
            self._attocube_axis["y"] = config['y']
        else:
            self.log.error(
                'No axis "y" found in configuration!\n'
                'Assign to that parameter an appropriated channel sorting!')

        if 'z' in config.keys():
            self._attocube_axis["z"] = config['z']
        else:
            self.log.error(
                'No axis "z" found in configuration!\n'
                'Assign to that parameter an appropriated channel sorting!')

        if 'voltage_range_stepper' in config.keys():
            if float(config['voltage_range_stepper'][0]) < float(
                    config['voltage_range_stepper'][1]):
                self._voltage_range_stepper = [float(config['voltage_range_stepper'][0]),
                                               float(config['voltage_range_stepper'][1])]
            else:
                self._voltage_range_stepper = self._voltage_range_stepper_default
                self.log.warning(
                    'Configuration ({}) of voltage_range_stepper incorrect, taking [0,60] instead.'
                    ''.format(config['voltage_range_stepper']))
        else:
            self.log.warning('No voltage_range_stepper configured taking [0,60] instead.')

        if 'frequency_range' in config.keys():
            if int(config['frequency_range'][0]) < int(config['frequency_range'][1]):
                self._frequency_range = [int(config['frequency_range'][0]),
                                         int(config['frequency_range'][1])]
            else:
                self._frequency_range = self._frequency_range_default
                self.log.warning(
                    'Configuration ({}) of frequency_range incorrect, taking [0,60] instead.'
                    ''.format(config['frequency_range']))
        else:
            self.log.warning('No frequency_range configured taking [0,60] instead.')

        if 'password' in config.keys():
            self._password = str(config['password']).encode('ascii')
        else:
            self._password = self._password_default
            self.log.warning('No password configured taking standard instead.')

        if 'host' in config.keys():
            self._host = str(config['host'])
        else:
            self.log.error('No IP address configured taking standard instead.\n'
                           'Assign to that parameter an appropriated IP address!')

        if 'port' in config.keys():
            self._port = config['port']
        else:
            self._port = self._port_default
            self.log.warning('No port configured taking standard instead.')

        # connect ethernet socket and FTP
        self.tn = telnetlib.Telnet(self._host, self._port)
        self.tn.open(self._host, self._port)
        self.tn.read_until(b"Authorization code: ")
        self.tn.write(self._password + b"\n")
        time.sleep(0.1)  # the ANC300 needs time to answer
        value_binary = self.tn.read_very_eager()
        value = value_binary.decode().split()
        if value[1] == 'Authorization success':  # Checks if connection was successful
            self.connected = True
        else:
            self.log.error('Connection to attocube could not be established.\n'
                           'Check password, physical connection, host etc. and try again.')

        self.tn.read_very_eager()

    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        self.tn.close()
        self.connected = False

    # =================== Attocube Communication ========================

    def _send_cmd(self, cmd, expected_response="OK", read=False):
        """Sends a command to the attocube steppers and checks response value

        @param str cmd: Attocube ANC300 command
        @param list(str) expected_response: expected attocube response to command as list per 
        expected line
        @param bool read: if True actually checks for expected result, else only checks for "OK"
        
        @return int: error code (0: OK, -1:error)
        """
        full_cmd = cmd.encode('ascii') + b"\r\n"  # converting to binary
        self.tn.read_eager()  # disregard old print outs
        self.tn.write(full_cmd)  # send command
        time.sleep(0.03)  # this exists because the ANC has response time of 30ms
        # self.tn.read_until(full_cmd + b" = ") #read answer
        value_binary = self.tn.read_very_eager()
        value = value_binary.decode().split("\r\n")  # transform into string and split at linefeed
        if value[-2] == "ERROR":
            if read:
                return -1, value
            self.log.warning('The command {} did not work but produced an {}'.format(value[-3],
                                                                                     value[-2]))
            return -1
        elif value == expected_response and read:
            return 0, value
        elif value[-2] == "OK":
            if read:
                return 0, value
            return 0
        return -1

    def _send_cmd_silent(self, cmd):
        """Sends a command to the attocube steppers and without checking the response. +
        Only use, when quick execution is necessary. Always returns 0. It saves at least 30ms (
        response time ANC300) per call

        @param str cmd: Attocube ANC300 command
        """
        full_cmd = cmd.encode('ascii') + b"\r\n"  # converting to binary
        self.tn.read_eager()  # disregard old print outs
        self.tn.write(full_cmd)  # send command
        self.tn.read_eager()
        return 0

    def change_attocube_mode(self, axis, mode):
        """Changes Attocube axis mode

        @param str axis: axis to be changed, can only be part of dictionary axes
        @param str mode: mode to be set
        @return int: error code (0: OK, -1:error)
        """
        if mode in _mode_list:
            if axis in ["x", "y", "z"]:
                command = "setm " + self._attocube_axis[axis] + mode
                return self._send_cmd(command)
            else:
                self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
                return -1
        else:
            self.log.error("mode {} not in list of possible modes".format(mode))
            return -1

    def move_attocube(self, axis, mode=True, direction=True, steps=1):
        """Moves attocubes either continuously or by a number of steps
        in the up or down direction.

        @param str axis: axis to be moved, can only be part of dictionary axes
        @param bool mode: Set if attocubes steps an amount of steps (True) or moves continuously until stopped (False)
        @param bool direction: True for up or out, False for down or "in" movement direction
        @param int steps: number of steps to be moved, ignore for continuous mode
        @return int:  error code (0: OK, -1:error)
        """
        # TODO still needs to decide if necessary to use send_cmd or if silent_cmd is sufficient,
        #  or if option in call. Also needs to check response from attocube if moved.
        if axis in ["x", "y", "z"]:
            if direction:
                command = "stepu " + self._attocube_axis[axis] + " "
            else:
                command = "stepd " + self._attocube_axis[axis] + " "

            if not mode:
                command += "c"
            else:
                command += str(steps)
            return self._send_cmd(command)
        else:
            self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
            return -1

    def stop_attocube_movement(self, axis):
        """Stops attocube motion on specified axis,
        only necessary if attocubes are stepping in continuous mode

        @param str axis: axis to be moved, can only be part of dictionary axes
        @return int: error code (0: OK, -1:error)
        """
        if axis in ["x", "y", "z"]:
            command = "stop" + self._attocube_axis[axis]
            return self._send_cmd(command)
        else:
            self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
            return -1

    def stop_all_attocube_motion(self):
        """Stops any attocube motion

        @return 0
        """
        self._send_cmd_silent("stop 1")
        self._send_cmd_silent("stop 2")
        self._send_cmd_silent("stop 3")
        self._send_cmd_silent("stop 4")
        self._send_cmd_silent("stop 5")
        # There are at maximum 5 stepper axis per ANC300 module.
        # If existing any motion on the axis is stopped
        self.log.info("any attocube stepper motion has been stopped")
        return 0

    # =================== General Methods ==========================================

    def _temperature_change(self, new_temp):
        """
        Changes parameters in attocubes to keep requirements like stepsize and scan speed
        constant for different temperatures
        :param float new_temp: the new temperature of the setup
        :return: error code (0: OK, -1:error)
        """
        pass
        # Todo: This needs to get a certain kind of change, as this then depends on
        # temperature. also maybe method name is not appropriate

    def change_step_size(self, axis, stepsize, temp):
        """Changes the step size of the attocubes according to a list give in the config file
        @param str  axis: axis  for which steps size is to be changed
        @param float stepsize: The wanted stepsize in nm
        @param float temp: The estimated temperature of the attocubes

        @return: float, float : Actual stepsize and used temperature"""
        voltage = stepsize
        # Todo here needs to be a conversion done
        self.change_step_amplitude(axis, voltage)
        pass

    def change_step_amplitude(self, axis=None, voltage=None):
        """

        @param str axis:
        @param float voltage:
        @return int: error code (0:OK, -1:error)
        """

        # Todo I need to add decide how to save the voltages for the three axis and if decided
        # update the current voltage

        if voltage < self._voltage_range_stepper[0] or voltage > self._voltage_range_stepper[1]:
            self.log.error(
                'Voltages {0} exceed the limit, the positions have to '
                'be adjusted to stay in the given range.'.format(voltage))
            return -1

        if voltage is not None:
            if axis in ["x", "y", "z"]:
                command = "setv " + self._attocube_axis[axis] + " " + str(voltage)
                return self._send_cmd(command)
            self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
            return -1

    def get_step_amplitude(self, axis):
        """

        @param str axis:
        @return int: error code (0:OK, -1:error)
        """
        if axis in ["x", "y", "z"]:
            command = "getv " + self._attocube_axis[axis]
            result = self._send_cmd(command, read=True)
            result[-3]
        self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
        return -1

    def set_step_freq(self, axis, freq):
        """

        @param str axis:
        @param int freq:
        @return int: error code (0:OK, -1:error)
        """
        # Todo this need to have a check added if freq is inside freq range
        # Todo I need to add decide how to save the freq for the three axis and if decided update the current freq

        if freq is not None:
            if axis in ["x", "y", "z"]:
                command = "setf " + self._attocube_axis[axis] + " " + str(freq)
                return self._send_cmd(command)
            self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
            return -1

    def get_step_amplitude(self, axis):
        """

        @param str axis:
        @return int: error code (0:OK, -1:error)
        """
        if axis in ["x", "y", "z"]:
            command = "getv " + self._attocube_axis[axis]
            result = self._send_cmd(command, read=True)
            if result[0] == -1:
                return -1
            voltage_line = result[1][-3].split()
            voltage = voltage_line[-2]
            # Todo the now read voltage now needs to be written in current voltage value
            return 0
        self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
        return -1

    # =================== ConfocalStepperInterface Commands ========================
    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs
            can access it.

        @return int: error code (0:OK, -1:error)
        """
        self.log.warning('Attocube Device does not need to be reset.')
        pass

    def set_position_range(self, myrange=None):
        """ Sets the physical range of the scanner.

        @param float [3][2] myrange: array of 3 ranges with an array containing
                                     lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        if myrange is None:
            myrange = [[0, 5000], [0, 5000], [0, 5000]]

        if not isinstance(myrange, (frozenset, list, set, tuple, np.ndarray,)):
            self.log.error('Given range is no array type.')
            return -1

        if len(myrange) != 3:
            self.log.error(
                'Given range should have dimension 3, but has {0:d} instead.'
                ''.format(len(myrange)))
            return -1

        for pos in myrange:
            if len(pos) != 2:
                self.log.error(
                    'Given range limit {1:d} should have dimension 2, but has {0:d} instead.'
                    ''.format(len(pos), pos))
                return -1
            if pos[0] > pos[1]:
                self.log.error(
                    'Given range limit {0:d} has the wrong order.'.format(pos))
                return -1

        self._position_range = myrange
        return 0

    def set_voltage_range_stepper(self, myrange=None):
        """ Sets the voltage range of the attocubes.

        @param float [2] myrange: array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        if myrange is None:
            myrange = [0, 60.]

        if not isinstance(myrange, (frozenset, list, set, tuple, np.ndarray,)):
            self.log.error('Given range is no array type.')
            return -1

        if len(myrange) != 2:
            self.log.error(
                'Given range should have dimension 2, but has {0:d} instead.'
                ''.format(len(myrange)))
            return -1

        if myrange[0] > myrange[1]:
            self.log.error('Given range limit {0:d} has the wrong order.'.format(myrange))
            return -1

        self._voltage_range_stepper = myrange
        return 0

    def get_scanner_position(self):
        pass

    def get_scanner_axes(self):
        # Todo check if this is possible with
        # This should be possible by asking for modes of the axis, if no error is returned, it
        # normally means the axis exists, if it doesnt an error is returned by ANC 300
        axis = {}
        for i in range(5):
            command = "getm "
            result = self._send_cmd(command + str(i), read)
            if result[0] == -1:
                if result[1].split()[-3] == "Wrong axis type":
                    axis.append(False)
                else:
                    self.log.error('The command {} did the expected axis response, '
                                   'but{}'.format(command+str(i),result[1].split()[-3]))
        #TODO not finished yet
        pass
