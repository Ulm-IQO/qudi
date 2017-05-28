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

import abc
import telnetlib

from core.base import Base
from interface.confocal_scanner_interface import ConfocalScannerInterface
import numpy as np

_mode_list = ["gnd", "inp", "cap", "stp", "off", "stp+", "stp-"]


class AttoCubeStepper(Base, ConfocalScannerInterface):
    """ This is the Interface class to define the controls for the simple
    microwave hardware.
    """

    _modtype = 'AttoCubeStepper'
    _modclass = 'hardware'

    # connectors
    # _out = {'confocalscanner': 'ConfocalScannerInterface'
    #     }

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
        self._voltage_range_coarse = [0., 60.]
        self._voltage_range_fine = [0., 100.]
        self._voltage_range_res = [0., 2.]
        self._position_range = [[0., 5000.], [0., 5000.], [0., 5000.], [0., 5000.]]
        self._frequency_range = [0, 10000]
        # Todo get rid of all fine/coarse deifnition stuff, only stepvoltage will remain

        self._password = b"1234765356"
        self._port = "7230"
        self._host = "134.60.31.214"

        if 'attocube_axis' in config.keys():
            self._attocube_axis = config['attocube_axis']
        else:
            self.log.error(
                'No parameter "attocube_axis" found in configuration!\n'
                'Assign to that parameter an appropriated channel sorting!')

        if 'x_range' in config.keys():
            if float(config['x_range'][0]) < float(config['x_range'][1]):
                self._position_range[0] = [float(config['x_range'][0]),
                                           float(config['x_range'][1])]
            else:
                self.log.warning(
                    'Configuration ({}) of x_range incorrect, taking [0,5000] instead.'
                    ''.format(config['x_range']))
        else:
            self.log.warning('No x_range configured taking [0,5000] instead.')

        if 'y_range' in config.keys():
            if float(config['y_range'][0]) < float(config['y_range'][1]):
                self._position_range[1] = [float(config['y_range'][0]),
                                           float(config['y_range'][1])]
            else:
                self.log.warning(
                    'Configuration ({}) of y_range incorrect, taking [0,5000] instead.'
                    ''.format(config['y_range']))
        else:
            self.log.warning('No y_range configured taking [0,5000] instead.')

        if 'z_range' in config.keys():
            if float(config['z_range'][0]) < float(config['z_range'][1]):
                self._position_range[2] = [float(config['z_range'][0]),
                                           float(config['z_range'][1])]
            else:
                self.log.warning(
                    'Configuration ({}) of z_range incorrect, taking [0,5000] instead.'
                    ''.format(config['z_range']))
        else:
            self.log.warning('No z_range configured taking [0,7000] instead.')

        if 'voltage_range_coarse' in config.keys():
            if float(config['voltage_range_coarse'][0]) < float(config['voltage_range_coarse'][1]):
                self._voltage_range_coarse = [float(config['voltage_range_coarse'][0]),
                                              float(config['voltage_range_coarse'][1])]
            else:
                self.log.warning(
                    'Configuration ({}) of voltage_range incorrect, taking [0,60] instead.'
                    ''.format(config['voltage_range_coarse']))
        else:
            self.log.warning('No voltage_range_coarse configured taking [0,60] instead.')

        if 'voltage_range_fine' in config.keys():
            if float(config['voltage_range_fine'][0]) < float(config['voltage_range_fine'][1]):
                self._voltage_range_fine = [float(config['voltage_range_fine'][0]),
                                            float(config['voltage_range_fine'][1])]
            else:
                self.log.warning(
                    'Configuration ({}) of voltage_range_fine incorrect, taking [0,60] instead.'
                    ''.format(config['voltage_range_fine']))
        else:
            self.log.warning('No voltage_range_fine configured taking [0,60] instead.')

        if 'frequency_range' in config.keys():
            if int(config['frequency_range'][0]) < int(config['frequency_range'][1]):
                self._frequency_range = [int(config['frequency_range'][0]),
                                         int(config['frequency_range'][1])]
            else:
                self.log.warning(
                    'Configuration ({}) of frequency_range incorrect, taking [0,60] instead.'
                    ''.format(config['frequency_range']))
        else:
            self.log.warning('No frequency_range configured taking [0,60] instead.')

        if 'password' in config.keys():
            self._password = str(config['password']).encode('ascii')
        else:
            self.log.warning('No password configured taking standard instead.')

        if 'host' in config.keys():
            self._password = str(config['host'])
        else:
            self.log.warning('No host configured taking standard instead.')

        # connect ethernet socket and FTP
        self.tn = telnetlib.Telnet(self._host, self._port)
        self.tn.open(self._host, self._port)
        self.tn.read_until(b"Authorization code: ")
        self.tn.write(self._password + b"\n")
        value = self.tn.read_until(b'success')
        # Todo check readout value (need binary split for this)


        self.tn.read_eager()
        self.connected = True

    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        self.tn.close()
        self.connected = False

    # =================== Attocube Communication ========================

    def _send_cmd(self, cmd, read = False, expected_response=b"\r\nOK\r\n"):
        """Sends a command to the attocube steppers and checks repsonse value

        @param str cmd: Attocube ANC300 command
        @param str expected_response: expected attocube response to command

        @return int: error code (0: OK, -1:error)
        """
        #Todo change return, this is too flat
        full_cmd = cmd.encode('ascii') + b"\r\n"  # converting to binary
        junk = self.tn.read_eager()  # diregard old print outs
        self.tn.write(full_cmd)  # send command
        # self.tn.read_until(full_cmd + b" = ") #read answer
        value = self.tn.read_eager()
        # TODO: here needs to be an error check, if not working, return 1, if -1 return
        # attocube response
        #this needs to return 0 if only ok recieved and was to be expected (set commands)
        # or -1 if wrong command, or the response -OK if a get was used
        if read:
            return value
        return 0

    def _send_cmd_silent(self, cmd):
        """Sends a command to the attocube steppers and without checking the response. +
        Only use, when quick execution is necessary. Always returns 0

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
        # Todo this need to have a check added if voltage is inside voltage range
        # Todo I need to add decide how to save the voltages for the three axis and if decided update the current voltage


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
            result = self._send_cmd(command, read = True)
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
            result =  self._send_cmd(command, read =  True)
            #Todo write new freq into variable
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

    def set_voltage_range_coarse(self, myrange=None):
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

        self._voltage_range_coarse = myrange
        return 0

    def get_scanner_position(self):
        pass

    def set_voltage_range(self, myrange=None):
        pass

    def get_scanner_axes(self):
        # Todo check if this is possivle with attocubes
        pass
