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

from core.module import Base, ConfigOption
from interface.confocal_stepper_interface import ConfocalStepperInterface
import numpy as np


class AttoCubeStepper(Base, ConfocalStepperInterface):
    """ 
    """

    _modtype = 'AttoCubeStepper'
    _modclass = 'hardware'

    _host = ConfigOption('host', missing='error')
    tmp = ConfigOption('password', b"123456", missing='warn')
    _port = ConfigOption('port', 7230, missing='warn')
    _position_feedback = ConfigOption('position_feedback', False, missing='warn')

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
        # Todo: This needs to be calculated by a more complicated formula depnding on the measured capacitance.
        # Todo: voltage range should be defined for each axis, the same for frequency
        self._voltage_range_stepper_default = [0, 60]
        self._frequency_range_default = [0, 10000]

        # Todo this needs to be update with checking every time it is started.

        # Todo get rid of all fine/coarse definition stuff, only step voltage will remain


        self._attocube_modes = {"stepping": "stp", "ground": "gnd", "Input": "inp", "off": "off"}
        # Todo finish attocube modes with sensible names
        # mode_list = ["gnd", "inp", "stp", "off", "stp+", "stp-"]

        # handle all the parameters given by the config
        self._attocube_axis = {}  # dictionary contains the axes and the specific controller
        self._attocube_axis_range = {}  # dictionary contains the axes stepping range
        default_range = [0, 5]

        if 'x' in config.keys():
            self._attocube_axis["x"] = config['x']
            if 'x_range' in config.keys():
                if float(config['x_range'][0]) < float(config['x_range'][1]):
                    self._attocube_axis_range["x"] = [float(config['x_range'][0]),
                                                      float(config['x_range'][1])]
                else:
                    self.log.warning(
                        'Configuration ({}) of x_range incorrect, taking [0,5] instead.'
                        ''.format(config['x_range']))
                    self._attocube_axis_range["x"] = default_range
            else:
                self.log.warning('No x_range configured taking [0,5] instead.')
                self._attocube_axis_range["x"] = default_range
        else:
            self.log.error(
                'No axis "x" found in configuration!\n'
                'The "x" axis it not accessible this way!')

        if 'y' in config.keys():
            self._attocube_axis["y"] = config['y']
            if 'y_range' in config.keys():
                if float(config['y_range'][0]) < float(config['y_range'][1]):
                    self._attocube_axis_range["y"] = [float(config['y_range'][0]),
                                                      float(config['y_range'][1])]
                else:
                    self.log.warning(
                        'Configuration ({}) of y_range incorrect, taking [0,5] instead.'
                        ''.format(config['y_range']))
                    self._attocube_axis_range["y"] = default_range
            else:
                self.log.warning('No y_range configured taking [0,5] instead.')
                self._attocube_axis_range["y"] = default_range
        else:
            self.log.error(
                'No axis "y" found in configuration!\n'
                'Assign to that parameter an appropriated channel sorting!')

        if 'z' in config.keys():
            self._attocube_axis["z"] = config['z']
            if 'z_range' in config.keys():
                if float(config['z_range'][0]) < float(config['z_range'][1]):
                    self._attocube_axis_range["z"] = [float(config['z_range'][0]),
                                                      float(config['z_range'][1])]
                else:
                    self.log.warning(
                        'Configuration ({}) of z_range incorrect, taking [0,5] instead.'
                        ''.format(config['z_range']))
                    self._attocube_axis_range["z"] = default_range
            else:
                self.log.warning('No z_range configured taking [0,5] instead.')
                self._attocube_axis_range["z"] = default_range
        else:
            self.log.error(
                'No axis "z" found in configuration!\n'
                'Assign to that parameter an appropriated channel sorting!')

        # Todo: This needs to be updated to a dictionary for each axis
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
            self._voltage_range_stepper = [float(config['voltage_range_stepper'][0]),
                                           float(config['voltage_range_stepper'][1])]

        # Todo: this needs to be read from a specifically still to be made text file depending on
        #  the capacitance
        self._frequency_range = dict()
        if 'frequency_range' in config.keys():
            if int(config['frequency_range'][0]) < int(config['frequency_range'][1]):
                for axis in self._attocube_axis.keys():
                    self._frequency_range[axis] = [int(config['frequency_range'][0]),
                                                   int(config['frequency_range'][1])]
            else:
                for axis in self._attocube_axis.keys():
                    self._frequency_range[axis] = [int(config['frequency_range'][0]),
                                                   int(config['frequency_range'][1])]
                self.log.warning(
                    'Configuration ({}) of frequency_range incorrect, taking [0,60] instead.'
                    ''.format(config['frequency_range']))
        else:
            self.log.warning('No frequency_range configured taking [0,60] instead.')
            for axis in self._attocube_axis.keys():
                self._frequency_range[axis] = [int(config['frequency_range'][0]),
                                               int(config['frequency_range'][1])]

        # connect Ethernet socket and FTP
        # Todo: Add a loop here which tries connecting several times and only throws error after failing x times.
        counter = 0
        self.connected = False
        self.tn = telnetlib.Telnet(self._host, self._port)
        self.tn.open(self._host, self._port)
        self._password = str(self.tmp).encode('ascii')
        del self.tmp
        while not self.connected:
            if counter > 7:
                self.log.error('Connection to attocube could not be established.\n'
                               'Check password, physical connection, host etc. and try again.')
                break
            self.tn.read_until(b"Authorization code: ")
            self.tn.write(self._password + b"\n")
            time.sleep(0.1)  # the ANC300 needs time to answer
            value_binary = self.tn.read_very_eager()
            value = value_binary.decode().split()
            if value[2] == 'success':  # Checks if connection was successful
                self.connected = True
                # Todo: Check how to do correct log messages
                self.log.info("Connection to Attocube was established")
            else:
                counter += 1

        self.tn.read_very_eager()
        self._initalize_axis()
        # This reads all the values from the hardware and checks if values ly inside defined boundaries
        self._get_all_hardwaresettings()

    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        self.tn.close()
        self.connected = False

    # =================== Attocube Communication ========================
    # Todo: make two send cmd, one with reutn value, one without
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
        # any response ends with ">" from the attocube. Therefore connection waits until this happened
        try:
            value_binary = self.tn.read_until(b">", timeout=1)
        except:
            self.log.error("time out of telnet connection attocube did not respond")
            return -1
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
        return -1, value

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

    def change_step_size(self, axis, step_size, temp):
        """Changes the step size of the attocubes according to a list give in the config file
        @param str  axis: axis  for which steps size is to be changed
        @param float step_size: The wanted step size in nm
        @param float temp: The estimated temperature of the attocubes

        @return: float, float : Actual step size and used temperature"""
        voltage = step_size
        # Todo here needs to be a conversion done
        self.set_step_amplitude(axis, voltage)
        pass

    def set_step_amplitude(self, axis, voltage=None):
        """Sets the step voltage/amplitude for axis for the ANC300

        @param str axis: key of the dictionary self._attocube_axis for the axis to be changed
        @param float voltage: the stepping amplitude/voltage the axis should be set to
        @return int: error code (0:OK, -1:error)
        """

        # Todo: probably is would be more clever to if voltage is none before testing it against the range
        if voltage < self._voltage_range_stepper[0] or voltage > self._voltage_range_stepper[1]:
            self.log.error(
                'Voltages {0} exceed the limit, the positions have to '
                'be adjusted to stay in the given range.'.format(voltage))
            return -1

        if voltage is not None:
            if axis in self._attocube_axis.keys():
                command = "setv {} {}".format(self._attocube_axis[axis], voltage)
                self._axis_amplitude[axis] = voltage
                return self._send_cmd(command)
            self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
            return -1

    def get_step_amplitude(self, axis):
        """ Checks the amplitude of a step for a specific axis

        @param str axis: the axis for which the step amplitude is to be checked
        @return float: the step amplitude of the axis
        """
        if axis in self._attocube_axis.keys():
            command = "getv {}".format(self._attocube_axis[axis])
            result = self._send_cmd(command, read=True)
            if result[0] == -1:
                return -1
            voltage_line = result[1][-3].split()
            self._axis_amplitude[axis] = float(voltage_line[-2])
            if (self._voltage_range_stepper[0] > self._axis_amplitude[axis] or
                        self._axis_amplitude[axis] >
                        self._voltage_range_stepper[1]):
                self.log.error(
                    "The voltage of {} V of axis {} in the ANC300 lies outside the defined range{},{]".format(
                        self._axis_amplitde[axis], axis, self._voltage_range_stepper[0],
                        self._voltage_range_stepper[1]))
            return self._axis_amplitude[axis]
        self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
        return -1
        # Todo: Do better error handling

    def set_step_freq(self, axis, freq=None):
        """Sets the step frequency for axis for the ANC300

        @param str axis: key of the dictionary self._attocube_axis for the axis to be changed
        @param float freq: the stepping frequency the axis should be set to
        @return int: error code (0:OK, -1:error)
        """
        # Todo this need to have a check added if freq is inside freq range
        # Todo I need to add decide how to save the freq for the three axis and if decided update the current freq

        if freq is not None:
            if axis in self._attocube_axis.keys():
                command = "setf {} {}".format(self._attocube_axis[axis], freq)
                # command = "setf " + self._attocube_axis[axis] + " " + str(freq)
                self._axis_frequency[axis] = freq
                return self._send_cmd(command)
            self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
            return -1
        self.log.info("No frequency was given so the step frequency was not changed.")
        return 0

    def get_step_freq(self, axis):
        """ Checks the step frequency for a specific axis

        @param str axis: the axis for which the frequency is to be checked
        @return float: the step amplitude of the axis
        """
        if axis in self._attocube_axis.keys():
            command = "getf {}".format(self._attocube_axis[axis])
            result = self._send_cmd(command, read=True)
            if result[0] == -1:
                # TodO: clean as soon as the attocube starts returning expected results
                # This is only here, because for some reason attocube does not does a correct line feed when
                #  returning the freq value
                res = result[1][-2].split("\n")  # transform into string and split at linefeed
                if res[-1] == "ERROR":
                    self.log.warning(
                        'The command {} did not work but produced an {}'.format(command,
                                                                                res[-1]))
                    return -1
                elif res[-1] == "OK":
                    frequency_line = res[-2].split()
                else:
                    self.log.warning(
                        'The command {} did not work but threw error {}'.format(command,
                                                                                res[-2]))
                    return -1
            else:
                frequency_line = result[1][-3].split()
            self._axis_frequency[axis] = float(frequency_line[-2])
            if (self._frequency_range[axis][0] > self._axis_frequency[axis] or self._axis_frequency[axis] >
                self._frequency_range[axis][1]):
                self.log.error(
                    "The value of {} V of axis {} in the ANC300 lies outside the defined range{},{]".format(
                        self._axis_frequency[axis], axis, self._frequency_range[axis][0],
                        self._frequency_range[axis][1]))
            return self._axis_frequency[axis]
        self.log.error("axis {} not in list of possible axes {}".format(axis, self._attocube_axis))
        return -1

    def set_axis_mode(self, axis, mode):
        """Changes Attocube axis mode

        @param str axis: axis to be changed, can only be part of dictionary axes
        @param str mode: mode to be set
        @return int: error code (0: OK, -1:error)
        """
        if mode in self._attocube_modes.keys():
            if axis in self._attocube_axis.keys():
                command = "setm {} {}".format(self._attocube_axis[axis],
                                              self._attocube_modes[mode])
                result = self._send_cmd(command)
                if result == 0:
                    self._axis_mode[axis] = mode
                    return 0
                else:
                    self.log.error(
                        "Setting axis {} to mode {} failed".format(self._attocube_axis[axis],
                                                                   mode))
            else:
                self.log.error(
                    "axis {} not in list of possible axes {}".format(axis, self._attocube_axis))
                return -1
        else:
            self.log.error("mode {} not in list of possible modes".format(mode))
            return -1

    def get_axis_mode(self, axis):
        """ Checks the mode for a specific axis

        @param str axis: the axis for which the frequency is to be checked
        @return float: the mode of the axis, -1 for error
        """
        if axis in self._attocube_axis.keys():
            command = "getm {}".format(self._attocube_axis[axis])
            result = self._send_cmd(command, read=True)
            if result[0] == -1:
                return -1
            mode_line = result[1][-3].split()
            for mode in self._attocube_modes:
                if self._attocube_modes[mode] == mode_line[-1]:
                    self._axis_mode[axis] = mode
                    return self._axis_mode[axis]
            else:
                self.log.error(
                    "Current mode of controller {} not in list of modes{}".format(
                        mode_line[-1]._attocube_modes))
                return -1
        self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
        return -1

    def set_DC_in(self, axis, on):
        """Changes Attocube axis DC input status

        @param str axis: axis to be changed, can only be part of dictionary axes
        @param bool on: if True is turned on, False is turned off
        @return int: error code (0: OK, -1:error)
        """
        if axis in self._attocube_axis.keys():
            if on:
                dci = "on"
            else:
                dci = "off"
            command = "setdci {} ".format(self._attocube_axis[axis]) + dci
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
        if axis in self._attocube_axis.keys():
            command = "getdci {}".format(self._attocube_axis[axis])
            result = self._send_cmd(command, read=True)
            if result[0] == -1:
                return -1
            dci_result = result[1][-3].split()
            self._axis_dci[axis] = dci_result[-1]
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
        if axis in self._attocube_axis.keys():
            if on:
                aci = "on"
            else:
                aci = "off"
            command = "setdci {} ".format(self._attocube_axis[axis]) + aci
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
        if axis in self._attocube_axis.keys():
            command = "getaci {}".format(self._attocube_axis[axis])
            result = self._send_cmd(command, read=True)
            if result[0] == -1:
                return -1
            aci_result = result[1][-3].split()
            self._axis_aci[axis] = aci_result[-1]
            if aci_result[-1] == "off":
                return False
            return True
        self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
        return -1

    def _temperature_change(self, new_temp):
        """
        Changes parameters in attocubes to keep requirements like step size and scan speed
        constant for different temperatures
        @param float new_temp: the new temperature of the setup
        @return int: error code (0: OK, -1:error)
        """
        # if a temperature change happened the capacitance of the attocubes changed and need to be
        # remeasured
        axis = self.get_stepper_axes()
        for i in self._attocube_axis.keys():  # get all axis names
            if axis[self._attocube_axis[i]]:  # check it the axis actually exists
                self._measure_capacitance(i)
        self.update_freq_range()
        pass
        # Todo: This needs to make a certain kind of change, as this then depends on
        # temperature. also maybe method name is not appropriate

    def _measure_capacitance(self, axis):
        """ Measures the attocube capacitance for a given axis

        @param str axis: the axis for which the frequency is to be checked
        @return float: the capacitance of the axis in F, -1 for error
        """
        if axis in self._attocube_axis.keys():
            result = self.set_axis_mode(axis, "ground")  # for any capacitance measurement the mode
            # needs to be set to gnd before
            if result == -1:
                return -1
            command = "setm {} ".format(self._attocube_axis[axis]) + "cap"
            result = self._send_cmd(command)  # measure
            if result == -1:
                return -1
            command = "capw {}".format(self._attocube_axis[axis])
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
                    self.log.warning("capacitance measurement was off, time-outs did not act as "
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
        if axis in self._attocube_axis.keys():
            command = "getc {}".format(self._attocube_axis[axis])
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
            self._axis_capacitance[axis] = float(cap_line[-2]) * power
            return self._axis_capacitance[axis]
        self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
        return -1

    def _get_all_hardwaresettings(self):
        axis = self.get_stepper_axes()
        for i in self._attocube_axis.keys():  # get all axis names
            if axis[self._attocube_axis[i] - 1]:  # check it the axis actually exists
                self.get_step_amplitude(i)
                self.get_step_freq(i)
                self.get_axis_mode(i)
                self.get_DC_in(i)
                self.get_AC_in(i)
                self._get_capacitance(i)

            else:
                self.log.error("axis {} was specified as number {} on ANC300\n  but this axis "
                               "doesn't exist in the ANC300".format(i, self._attocube_axis[i]))
                return -1
        else:
            return 0

    def _initalize_axis(self):
        """ Initialises all axes values, setting them to 0.
        This should only be called when making a new instance.
        """
        axis = self.get_stepper_axes()
        self._axis_amplitude = {}
        self._axis_frequency = {}
        self._axis_mode = {}
        self._axis_dci = {}
        self._axis_aci = {}
        self._axis_capacitance = {}

        for i in self._attocube_axis.keys():  # get all axis names
            if axis[self._attocube_axis[i] - 1]:  # check it the axis actually exists
                self._axis_amplitude[i] = 0
                self._axis_frequency[i] = 0
                self._axis_mode[i] = ""
                self._axis_dci[i] = ""
                self._axis_aci[i] = ""
                self._axis_capacitance[i] = 0
            else:
                self.log.error("axis {} was specified as number {} on ANC300\n  but this axis "
                               "doesn't exist in the ANC300".format(i, self._attocube_axis[i]))

    # =================== ConfocalStepperInterface Commands ========================
    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs
            can access it.

        @return int: error code (0:OK, -1:error)
        """
        self.log.warning('Attocube Device does not need to be reset.')
        pass

    def get_position_feedback(self):
        """Checks if the hardware is a closed loop hardware with position feedback
        return bool: if True the hardware has a position feedback"""
        # Todo: This needs to be programmed axis specific and done in the nidaq when a concept for differentiating
        # between different controllers has been established
        return self._position_feedback

    def get_position_range_stepper(self, axis_name):
        """ Returns the physical range of the stepper.

        @param str axis_name: the axis for which the range is to be checked

        @return dict: key: axis name as sting (e.g. "x"), value the stepper range in mm
        """
        if axis_name not in self._attocube_axis.keys():
            self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
            return -1
        return self._attocube_axis_range[axis_name]

    def set_position_range_stepper(self, axis, my_range=None):
        """ Sets the physical range of the stepper.

        @param str axis: the axis for which the range is to be changed
        @param float [2] my_range: 2 value float array containing the new lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        if axis not in self._attocube_axis.keys():
            self.log.error("axis {} not in list of possible axes".format(self._attocube_axis))
            return -1
        if my_range is None:
            my_range = [0, 5]

        if not isinstance(my_range, (frozenset, list, set, tuple, np.ndarray,)):
            self.log.error('Given range is no array type.')
            return -1

        if len(my_range) != 2:
            self.log.error(
                'Given range should have dimension 2, but has {0:d} instead.'
                ''.format(len(my_range)))
            return -1

        if my_range[0] > my_range[1]:
            self.log.error(
                'Given range limit {0:d} has the wrong order.'.format(my_range))
            return -1

        self._attocube_axis_range[axis] = my_range
        return 0

    def set_amplitude_range_stepper(self, my_range=None):
        """ Sets the voltage range of the attocubes.

        @param float [2] my_range: array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        if my_range is None:
            my_range = [0, 60.]

        if not isinstance(my_range, (frozenset, list, set, tuple, np.ndarray,)):
            self.log.error('Given range is no array type.')
            return -1

        if len(my_range) != 2:
            self.log.error(
                'Given range should have dimension 2, but has {0:d} instead.'
                ''.format(len(my_range)))
            return -1

        if my_range[0] > my_range[1]:
            self.log.error('Given range limit {} has the wrong order.'.format(my_range))
            return -1

        self._voltage_range_stepper = my_range
        self._update_freq_range()
        return 0

    def get_amplitude_range_stepper(self):
        """Returns the current possible stepping voltage range of the stepping device for all axes

        @return list: voltage range of scanner
        """
        return self._voltage_range_stepper

    def update_freq_range(self):
        """"Updates the constraints on the frequency range

        @return int: error code (0:OK, -1:error)
        """
        # Todo:Write after text file was written
        pass

    def get_freq_range_stepper(self):
        """Returns the current possible stepping voltage range of the stepping device for all axes
        @return list: voltage range of scanner
        """
        return self._frequency_range

    def get_scanner_position(self):
        self.log.warning("this method isnt defined yet")
        pass

    # Todo: It might make sense to return a libary of axis ("x", "y", "z" etc. against booleans) check.
    def get_stepper_axes(self):
        """"
        Checks which axes of the hardware have a reaction by the hardware

         @return list: list of booleans for each possible axis, if true axis exists

         On error, return empty list
        """
        # TOdo: Check if I did the same split list problem more then once
        axis = []
        for i in range(5):
            command = "getm {}".format(i + 1)
            result = self._send_cmd(command, read=True)
            if result[0] == -1:
                res = result[1]
                if result[1][1] == "Wrong axis type":
                    axis.append(False)
                else:
                    self.log.error('The command {} did the expected axis response, '
                                   'but{}'.format(command, result[1][1].split()[-3]))
            else:

                axis.append(True)
        return axis

    def get_stepper_axes_use(self):
        """ Find out how the axes of the stepping device are used for confocal and their names.

        @return list(str): list of axis dictionary

        Example:
          For 3D confocal microscopy in Cartesian coordinates, ['x':1, 'y':2, 'z':3] is a sensible 
          value.
          If you only care about the number of axes and not the assignment and names 
          use get_stepper_axes
        """
        return self._attocube_axis

    # Todo: make two options for silent or not for fast usage
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

        if axis in self._attocube_axis.keys():
            if self._axis_mode[axis] == 'ground':
                self.log.warning("Set mode to stepping. Current mode is ground.")
                # Todo: this needs to check actually if it is in allowed mode. Figure out which modes are allowed.
                return -1
            if direction:
                command = "stepu {} ".format(self._attocube_axis[axis])
            else:
                command = "stepd {} ".format(self._attocube_axis[axis])

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
        if axis in self._attocube_axis.keys():
            command = "stop {}".format(self._attocube_axis[axis])
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
