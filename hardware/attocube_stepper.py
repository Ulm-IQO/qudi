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

_mode_list = ["gnd", "inp", "stp", "off", "stp+", "stp-"]


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
        self._axis_amplitude = {"x": 0.0, "y": 0.0, "z": 0.0}
        # Todo this needs to be update with checking every time it is started.

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

    # =================== General Methods ==========================================

    def set_axis_mode(self, axis, mode):
        """Changes Attocube axis mode

        @param str axis: axis to be changed, can only be part of dictionary axes
        @param str mode: mode to be set
        @return int: error code (0: OK, -1:error)
        """
        if mode in _mode_list:
            if axis in self._attocube_axis.keys():
                command = "setm " + self._attocube_axis[axis] + mode
                result = self._send_cmd(command)
                if result == 0:
                    self._axis_mode[axis] = mode
                return 0
            else:
                self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
                return -1
        else:
            self.log.error("mode {} not in list of possible modes".format(mode))
            return -1

    def _temperature_change(self, new_temp):
        """
        Changes parameters in attocubes to keep requirements like stepsize and scan speed
        constant for different temperatures
        :param float new_temp: the new temperature of the setup
        :return: error code (0: OK, -1:error)
        """
        # if a temperature change happened the capacitance of the attocubes changed and need to be
        # remeasured
        axis = self.get_stepper_axes()
        for i in self._attocube_axis.keys():  # get all axis names
            if axis[self._attocube_axis[i]]:  # check it the axis actually exists
                self._measure_capacitance(i)
        pass
        # Todo: This needs to make a certain kind of change, as this then depends on
        # temperature. also maybe method name is not appropriate

    def change_step_size(self, axis, stepsize, temp):
        """Changes the step size of the attocubes according to a list give in the config file
        @param str  axis: axis  for which steps size is to be changed
        @param float stepsize: The wanted stepsize in nm
        @param float temp: The estimated temperature of the attocubes

        @return: float, float : Actual stepsize and used temperature"""
        voltage = stepsize
        # Todo here needs to be a conversion done
        self.set_step_amplitude(axis, voltage)
        pass

    def set_step_amplitude(self, axis=None, voltage=None):
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
            if axis in self._attocube_axis.keys():
                command = "setv " + self._attocube_axis[axis] + " " + str(voltage)
                return self._send_cmd(command)
            self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
            return -1

    def get_step_amplitude(self, axis):
        """ Checks the amplitude of a step for a specific axis

        @param str axis: the axis for which the step amplitude is to be checked
        @return float: the step amplitude of the axis
        """
        if axis in self._attocube_axis.keys():
            command = "getv " + self._attocube_axis[axis]
            result = self._send_cmd(command, read=True)
            if result[0] == -1:
                return -1
            voltage_line = result[1][-3].split()
            self._axis_amplitude[axis] = voltage_line[-2]
            return self._axis_amplitude[axis]
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
            if axis in self._attocube_axis.keys():
                command = "setf " + self._attocube_axis[axis] + " " + str(freq)
                return self._send_cmd(command)
            self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
            return -1

    def get_step_freq(self, axis):
        """ Checks the step frequency for a specific axis

        @param str axis: the axis for which the frequency is to be checked
        @return float: the step amplitude of the axis
        """
        if axis in self._attocube_axis.keys():
            command = "getf " + self._attocube_axis[axis]
            result = self._send_cmd(command, read=True)
            if result[0] == -1:
                return -1
            frequency_line = result[1][-3].split()
            self._axis_frequency[axis] = frequency_line[-2]
            return self._axis_frequency[axis]
        self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
        return -1

    def set_axis_mode(self, axis, mode):
        """Changes Attocube axis mode

        @param str axis: axis to be changed, can only be part of dictionary axes
        @param str mode: mode to be set
        @return int: error code (0: OK, -1:error)
        """
        if mode in _mode_list:
            if axis in self._attocube_axis.keys():
                command = "setm " + self._attocube_axis[axis] + " " + mode
                result = self._send_cmd(command)
                if result == 0:
                    self._axis_mode[axis] = mode
                    if mode == "gnd":  # this automatically turns the inputs off
                        self._axis_dci = "off"
                        self._axis_aci = "off"
                return 0
            else:
                self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
                return -1
        else:
            self.log.error("mode {} not in list of possible modes".format(mode))
            return -1

    def _measure_capacitance(self, axis):
        """ Measures the attocube capacitance for a given axis

        @param str axis: the axis for which the frequency is to be checked
        @return float: the capacitance of the axis in F, -1 for error
        """
        if axis in self._attocube_axis.key():
            result = self.set_axis_mode(axis, "gnd")  # for any capacitance mesaurement the mode
            # needs
            #  to be set to gnd before
            if result == -1:
                return -1
            command = "setm " + self._attocube_axis[axis] + " cap"
            result = self._send_cmd(command)  # measure
            if result == -1:
                return -1
            command = "capw " + self._attocube_axis[axis]
            result = self._send_cmd(command, read=True)
            if result[0] == -1:
                return -1
            if len(result[1]) < 2:
                wait = True
            elif len(result[1]) > 3:
                wait = False
            elif "nF" in result[1][3]:
                wait = False
            else:
                try:
                    answer = self.tn.read_until("nF", timeout=4)
                    wait = False
                except:
                    # Todo something sensible needs to come here
                    self.log.warning("capacitance measurement was off, timeouts did not act as "
                                     "expected. Program will pause for 10 seconds for attocubes to recover")
                    time.sleep(10)
                    wait = True
            if wait:
                self.tn.read_until("nF", timeout=4)
            # now read out the capactitance from the hardware
            return self._get_capacitance(axis)
        self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
        return -1

    def _get_capacitance(self, axis):
        """ Reads the  saved attocube capacitance for a given axis from the hardware

        @param str axis: the axis for which the frequency is to be checked
        @return float: the capacitance of the axis in F, -1 for error
        """
        if axis in self._attocube_axis.key():
            command = "getc " + self._attocube_axis[axis]
            result = self._send_cmd(command, read=True)
            if result[0] == -1:
                return -1
            cap_line = result[1][-3].split()
            if cap_line[-1] == "nF":
                power = 1e-9
            elif cap_line[-1] == "uF":
                # TODO check if this is really called like this in the attocube response when
                # possible
                power = 1e-6
            elif cap_line[-1] == "mF":
                power = 1e-3
                self.log.warning("Something is wrong with the attocubes.\n The saved "
                                 "capacitance value is {}, which is out of a normal range.\n "
                                 "Check the setup, redo the capacitance measurement!".format(
                    cap_line[-2:]))
            else:
                self.log.error("Something is wrong with the attocubes.\n The saved "
                               "capacitance value is {}, which is out of a normal range.\n "
                               "Check the setup, redo the capacitance measurement!".format(
                    cap_line[-2:]))
                return -1
            self._axis_capacitance[axis] = cap_line[-2] * power
            return self._axis_capacitance[axis]
        self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
        return -1

    def get_axis_mode(self, axis):
        """ Checks the mode for a specific axis

        @param str axis: the axis for which the frequency is to be checked
        @return float: the step amplitude of the axis, -1 for error
        """
        if axis in self._attocube_axis.key():
            command = "getm " + self._attocube_axis[axis]
            result = self._send_cmd(command, read=True)
            if result[0] == -1:
                return -1
            mode_line = result[1][-3].split()
            self._axis_mode[axis] = mode_line[-1]
            return self._axis_mode[axis]
        self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
        return -1

    def set_DC_in(self, axis, on):
        """Changes Attocube axis DC input status

        @param str axis: axis to be changed, can only be part of dictionary axes
        @param bool on: if True is turned on, False is turned off
        @return int: error code (0: OK, -1:error)
        """
        if axis in self._attocube_axis.key():
            if on:
                dci = "on"
            else:
                dci = "off"
            command = "setdci " + self._attocube_axis[axis] + " " + dci
            result = self._send_cmd(command)
            if result == 0:
                self._axis_dci[axis] = dci
                return 0
            else:
                return -1
        self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
        return -1

    def get_DC_in(self, axis):
        """ Checks the status of the DC input for a specific axis

        @param str axis: the axis for which the input is to be checked
        @return bool: True for on, False for off, -1 for error
        """
        if axis in self._attocube_axis.key():
            command = "getdci " + self._attocube_axis[axis]
            result = self._send_cmd(command, read=True)
            if result[0] == -1:
                return -1
            dci_result = result[1][-3].split()
            self._axis_dci[axis] = dci_result
            if dci_result[-1] == "off":
                return False
            return True
        self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
        return -1

    def set_AC_in(self, axis, on):
        """Changes Attocube axis DC input status

        @param str axis: axis to be changed, can only be part of dictionary axes
        @param bool on: if True is turned on, False is turned off
        @return int: error code (0: OK, -1:error)
        """
        if axis in self._attocube_axis.key():
            if on:
                aci = "on"
            else:
                aci = "off"
            command = "setdci " + self._attocube_axis[axis] + " " + aci
            result = self._send_cmd(command)
            if result == 0:
                self._axis_aci[axis] = aci
                return 0
            else:
                return -1
        self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
        return -1

    def get_AC_in(self, axis):
        """ Checks the status of the AC input for a specific axis

        @param str axis: the axis for which the input is to be checked
        @return bool: True for on, False for off, -1 for error
        """
        if axis in self._attocube_axis.key():
            command = "getaci " + self._attocube_axis[axis]
            result = self._send_cmd(command, read=True)
            if result[0] == -1:
                return -1
            aci_result = result[1][-3].split()
            self._axis_aci[axis] = aci_result
            if aci_result[-1] == "off":
                return False
            return True
        self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
        return -1

    def _get_all_hardwaresettings(self):
        axis = self.get_stepper_axes()
        for i in self._attocube_axis.keys():  # get all axis names
            if axis[self._attocube_axis[i]]:  # check it the axis actually exists
                self.get_step_amplitude(i)
                self.get_step_freq(i)
                self.get_axis_mode(i)
                self.get_DC_in(i)
                self.get_AC_in(i)

            else:
                self.log.error("axis {} was specified as number {} on ANC300\n  but this axis "
                               "doesn´t exist in the ANC300".format(i, self._attocube_axis[i]))
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

    def get_stepper_axes(self):
        """"
        Checks for the at most 5 possible axis of the ANC which ones exists
         
         @return list: list of 5 bools for each axis, if true axis exists
        """
        axis = {}
        for i in range(5):
            command = "getm "
            result = self._send_cmd(command + str(i), read)
            if result[0] == -1:
                if result[1].split()[-3] == "Wrong axis type":
                    axis.append(False)
                else:
                    self.log.error('The command {} did the expected axis response, '
                                   'but{}'.format(command + str(i), result[1].split()[-3]))
            else:
                axis.append(True)
        return axis
