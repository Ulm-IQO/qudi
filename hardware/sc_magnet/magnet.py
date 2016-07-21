# -*- coding: utf-8 -*-
"""
Hardware file for the Superconducting Magnet (SCM)

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


import socket
from core.base import Base
import numpy as np
import time
from interface.magnet_interface import MagnetInterface


class Magnet(Base, MagnetInterface):
    """Magnet positioning software for superconducting magnet.
    Enables precise positioning of the magnetic field in spherical coordinates
    with the angle theta, phi and the radius rho.
    The superconducting magnet has three coils, one in x, y and z direction respectively.
    The current through these coils is used to compute theta, phi and rho.
    The alignment can be done manually as well as automatically via fluorescence alignment.
    """

    _modtype = 'Magnet'
    _modclass = 'hardware'

    _out = {'magnetstage': 'magnet_interface'}


    def __init__(self, manager, name, config, **kwargs):
        """Here the connections to the power supplies and to the counter are established"""
        # declare actions for state transitions

        # apparently not needed anymore
        c_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}

        Base.__init__(self, manager, name, config, c_dict)
        self.soc_x = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.soc_y = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.soc_z = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# default waiting time of the pc after a message was sent to the magnet
# should be set in the config file
        self.waitingtime = 0.01

# this is a new thing. "normal_mode"
# allows one to set magnetic fields up to 1 T along each axis
# and the magnetic field vector can't be larger than 1.2 T
# In z_mode you are allowed to move in a 5° solid angle along the z-axis
# with a maximum field of 3 T.
# For more documentation or how to change the mode look into
# the function switch_mode
        self.mode = "normal_mode"

# constraints of the superconducting magnet in kG
# should be set in the config file
# Normally you should get and set constraints in the
# function get_constraints(). The problem is here that
# the constraint rho is no constant and is dependent on the
# current theta and phi value.
        self.x_constr = 1.0
        self.y_constr = 1.0
        self.z_constr = 3.0
        self.rho_constr = 1.2

    def activation(self, e):
        """
        loads the config file and extracts the necessary configurations for the
        superconducting magnet

        @return int: (0: Ok, -1:error)
        """

# get necessary information from the config file
        config = self.getConfiguration()

        if 'magnet_port' in config.keys():
            port = config['magnet_port']
        else:
            self.logMsg('No port hs been defined in the config file!',
                        msgType='error')
            return -1

        if 'magnet_IP_address_x' in config.keys():
            self.soc_x.connect((config['magnet_IP_address_x'], port))
        else:
            self.logMsg('No ip-address for connection to x-coil defined!',
                        msgType='error')
            return -1

        if 'magnet_IP_address_y' in config.keys():
            self.soc_y.connect((config['magnet_IP_address_y'], port))
        else:
            self.logMsg('No ip-address for connection to y-coil defined!',
                        msgType='error')
            return -1

        if 'magnet_IP_address_z' in config.keys():
            self.soc_z.connect((config['magnet_IP_address_z'], port))
        else:
            self.logMsg('No ip-address for connection to z-coil defined!',
                        msgType='error')
            return -1

        if 'magnet_waitingtime' in config.keys():
            self.waitingtime = config['magnet_waitingtime']

        if 'magnet_x_constr' in config.keys():
            self.x_constr = config['magnet_x_constr']

        if 'magnet_y_constr' in config.keys():
            self.y_constr = config['magnet_y_constr']

        if 'magnet_z_constr' in config.keys():
            self.z_constr = config['magnet_z_constr']

        if 'magnet_rho_constr' in config.keys():
            self.rho_constr = config['magnet_rho_constr']

#       sending a signal to all coils to receive an answer to cut off the
#       useless welcome message.
        ask_dict = {'x': "STATE?\n", 'y': "STATE?\n", 'z': "STATE?\n"}
        answ_dict = self.ask(ask_dict)
        print(answ_dict['x'])
        print(answ_dict['y'])
        print(answ_dict['z'])
#       sending a command to the magnet to turn into SI units regarding
#       field units.
        tell_dict = {'x': 'CONF:FIELD:UNITS 1', 'y': 'CONF:FIELD:UNITS 1', 'z': 'CONF:FIELD:UNITS 1'}
        self.tell(tell_dict)

    def deactivation(self, e):
        pass

    def utf8_to_byte(self, myutf8):
        """
        Convenience function for code refactoring
        @param string myutf8 the message to be encoded
        @return the encoded message in bytes
        """
        return myutf8.encode('utf-8')

    def byte_to_utf8(self, mybytes):
        """
        Convenience function for code refactoring
        @param bytes mybytes the byte message to be decoded
        @return the decoded string in uni code
        """
        return mybytes.decode()

# =========================== Magnet Functionality Core ====================================

    def get_constraints(self):
        """ Retrieve the hardware constraints from the magnet driving device.

        @return dict: dict with constraints for the magnet hardware. These
                      constraints will be passed via the logic to the GUI so
                      that proper display elements with boundary conditions
                      could be made.

        Provides all the constraints for each axis of a motorized stage
        (like total travel distance, velocity, ...)
        Each axis has its own dictionary, where the label is used as the
        identifier throughout the whole module. The dictionaries for each axis
        are again grouped together in a constraints dictionary in the form

            {'<label_axis0>': axis0 }

        where axis0 is again a dict with the possible values defined below. The
        possible keys in the constraint are defined in the interface file.
        If the hardware does not support the values for the constraints, then
        insert just None. If you are not sure about the meaning, look in other
        hardware files to get an impression.
        """
        constraints = {}

        # get the constraints for the x axis:
        axis0 = {}
        axis0['label'] = 'rho'       # name is just as a sanity included
        axis0['unit'] = 'T'        # the SI units
        axis0['pos_min'] = 0
        axis0['pos_max'] = self._rho_max_pos()
        axis0['pos_step'] = 300000
        axis0['vel_min'] = 0
        axis0['vel_max'] = 0.0404*0.01799  # unit is T/s
        axis0['vel_step'] = 10**4

# In fact position constraints for rho is dependent on theta and phi, which would need
# the use of an additional function to calculate
# going to change the return value to a function rho_max_pos which needs the current theta and
# phi position
        # get the constraints for the x axis:
        axis1 = {}
        axis1['label'] = 'theta'       # name is just as a sanity included
        axis1['unit'] = 'rad'        # the SI units
        axis1['pos_min'] = 0
        axis1['pos_max'] = np.pi  # that is basically the traveling range
        axis1['pos_step'] = 36000
        axis1['vel_min'] = 0
        axis1['vel_max'] = 0.0404*0.01799  #unit is T/s
        axis1['vel_step'] = 10**4

        # get the constraints for the x axis:
        axis2 = {}
        axis2['label'] = 'phi'       # name is just as a sanity included
        axis2['unit'] = 'rad'        # the SI units
        axis2['pos_min'] = 0
        axis2['pos_max'] = 2*np.pi  # that is basically the traveling range
        axis2['pos_step'] = 92000
        axis2['vel_min'] = 0
        axis2['vel_max'] = 0.0380*0.07028 #unit is T/s
        axis2['vel_step'] = 10**4

        # assign the parameter container for x to a name which will identify it
        constraints[axis0['label']] = axis0
        constraints[axis1['label']] = axis1
        constraints[axis2['label']] = axis2

        return constraints

    def tell(self, param_dict):
        """Send a command string to the magnet.
        @param dict param_dict: has to have one of the following keys: 'x', 'y' or 'z'
                                      with an appropriate command for the magnet
        """
        internal_counter = 0
        if param_dict.get('x') is not None:
            if not param_dict['x'].endswith('\n'):
                param_dict['x'] += '\n'
            self.soc_x.send(self.utf8_to_byte(param_dict['x']))
            internal_counter += 1
        if param_dict.get('y') is not None:
            if not param_dict['y'].endswith('\n'):
                param_dict['y'] += '\n'
            self.soc_y.send(self.utf8_to_byte(param_dict['y']))
            internal_counter += 1
        if param_dict.get('z') is not None:
            if not param_dict['z'].endswith('\n'):
                param_dict['z'] += '\n'
            self.soc_z.send(self.utf8_to_byte(param_dict['z']))
            internal_counter += 1

        if internal_counter == 0:
            self.logMsg('no parameter_dict was given therefore the function tell() call was useless',
                        msgType='warning')

    def ask(self, param_dict):
        """Asks the magnet a 'question' and returns an answer from it.
        @param dictionary param_dict: has to have one of the following keys: 'x', 'y' or 'z'
                                      the items have to be valid questions for the magnet.

        @return answer_dict: contains the same labels as the param_dict if it was set correct and the
                             corresponding items are the answers of the magnet (format is string), else
                             an empty dictionary is returned


        """

        answer_dict = {}
        if param_dict.get('x') is not None:
            if not param_dict['x'].endswith('\n'):
                param_dict['x'] += '\n'
# repeat this block to get out crappy messages.
            self.soc_x.send(self.utf8_to_byte(param_dict['x']))
            time.sleep(self.waitingtime)                   # you need to wait until magnet generating
                                        # an answer.
            answer_dict['x'] = self.byte_to_utf8(self.soc_x.recv(1024))  # receive an answer
            self.soc_x.send(self.utf8_to_byte(param_dict['x']))
            time.sleep(self.waitingtime)                   # you need to wait until magnet generating
                                        # an answer.
            answer_dict['x'] = self.byte_to_utf8(self.soc_x.recv(1024))  # receive an answer

            answer_dict['x'] = answer_dict['x'].replace('\r', '')
            answer_dict['x'] = answer_dict['x'].replace('\n', '')
        if param_dict.get('y') is not None:
            if not param_dict['y'].endswith('\n'):
                param_dict['y'] += '\n'
            self.soc_y.send(self.utf8_to_byte(param_dict['y']))
            time.sleep(self.waitingtime)                   # you need to wait until magnet generating
                                        # an answer.
            answer_dict['y'] = self.byte_to_utf8(self.soc_y.recv(1024))   # receive an answer
            self.soc_y.send(self.utf8_to_byte(param_dict['y']))
            time.sleep(self.waitingtime)                   # you need to wait until magnet generating
                                        # an answer.
            answer_dict['y'] = self.byte_to_utf8(self.soc_y.recv(1024))   # receive an answer
            answer_dict['y'] = answer_dict['y'].replace('\r', '')
            answer_dict['y'] = answer_dict['y'].replace('\n', '')
        if param_dict.get('z') is not None:
            if not param_dict['z'].endswith('\n'):
                param_dict['z'] += '\n'
            self.soc_z.send(self.utf8_to_byte(param_dict['z']))
            time.sleep(self.waitingtime)                   # you need to wait until magnet generating
                                        # an answer.
            answer_dict['z'] = self.byte_to_utf8(self.soc_z.recv(1024))   # receive an answer
            self.soc_z.send(self.utf8_to_byte(param_dict['z']))
            time.sleep(self.waitingtime)                   # you need to wait until magnet generating
                                        # an answer.
            answer_dict['z'] = self.byte_to_utf8(self.soc_z.recv(1024))   # receive an answer
            answer_dict['z'] = answer_dict['z'].replace('\r', '')
            answer_dict['z'] = answer_dict['z'].replace('\n', '')

        if len(answer_dict) == 0:
            self.logMsg('no parameter_dict was given therefore the function call ask() was useless',
                        msgType='warning')

        return answer_dict

    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return dict: with the axis label as key and the status number as item.
                      Possible states are { -1 : Error, 1: SCM doing something, 0: SCM doing nothing }
        """
# what kind of status messages should I provide think I have to see in Alex files.
# I have no clue how to make this right. Alex assumes of course that we only have one set
# of axes, but this doesn't really hold. I have the axes 'x', 'y' and 'z' for the
# hardware stuff and constraints statuses and so on and all the spherical things are
# for the user. How do I handle this ? I think the status isn't all that important in our case
# so I just will give the user labels with the numbers of the hardware labels.
# Alex told me that I basically need to return 3 status messages. -1 for error
# 1 for moving and 0 for idle. Now I need to think which status I categorize as what.


        return_dict = {}
        if param_list is None:
            answ_dict = self.ask_status()
            return_dict['rho'] = [self.translator_for_get_status(answ_dict['x'])]
            return_dict['theta'] = [self.translator_for_get_status(answ_dict['y'])]
            return_dict['phi'] = [self.translator_for_get_status(answ_dict['z'])]
        else:
            if 'rho' in param_list:
                answ_dict = self.ask_status(["x"])
                return_dict['rho'] = [self.translator_for_get_status(answ_dict['x'])]
            if 'theta' in param_list:
                answ_dict = self.ask_status(["y"])
                return_dict['theta'] = [self.translator_for_get_status(answ_dict['y'])]
            if 'phi' in param_list:
                answ_dict = self.ask_status(["z"])
                return_dict['phi'] = [self.translator_for_get_status(answ_dict['z'])]

        return return_dict

    def heat_switch(self, axis):
        """ This function enables heating of the PJSwitch,  which is a necessary
            step to conduct current to the coils.
            @param string axis: desired axis (x, y, z)
            """
        if axis == "x":
            self.soc_x.send(self.utf8_to_byte("PS 1\n"))
        elif axis == "y":
            self.soc_y.send(self.utf8_to_byte("PS 1\n"))
        elif axis == "z":
            self.soc_z.send(self.utf8_to_byte("PS 1\n"))
        else:
            print("Only x, y, z possible")

    def heat_all_switches(self):
        """ Just a convenience function to heat all switches at once,  as it is unusual
            to only apply a magnetic field in one direction"""
        self.heat_switch("x")
        self.heat_switch("y")
        self.heat_switch("z")

    def cool_switch(self, axis):
        """ Turns off the heating of the PJSwitch,  axis depending on user input
            @param string axis: desired axis (x, y, z)
            """
        if axis == "x":
            self.soc_x.send(self.utf8_to_byte("PS 0\n"))
        elif axis == "y":
            self.soc_y.send(self.utf8_to_byte("PS 0\n"))
        elif axis == "z":
            self.soc_z.send(self.utf8_to_byte("PS 0\n"))
        else:
            print("Only x, y, z possible")

    def cool_all_switches(self):
        """ Just a convenience function to cool all switches at once This will take 600s."""

        self.cool_switch("x")
        self.cool_switch("y")
        self.cool_switch("z")

    def initialize(self):
        """
        Acts as a switch. When all coils of the superconducting magnet are heated it cools them, else
        the coils get heated.
        @return int: (0: Ok, -1:error)
        """
        # need to ask if the PJSwitch is on
        answ_dict = {}
        answ_dict = self.ask({'x': "PS?", 'y': "PS?", 'z': "PS?"})
        if answ_dict['x'] == answ_dict['y'] == answ_dict['z']:
            if answ_dict['x'] == '0':
                self.heat_all_switches()
            else:
                self.cool_all_switches()
        else:
            self.logMsg("can not correctly turn on/ turn off magnet, because not all coils" +
                        "are in the same state in function initialize", msgType="warning")
            return -1

        return 0

# how to realize this function ?
    def idle_magnet(self):
        """
        Cool all coils of the superconducting magnet to achieve maximum accuracy after aligning.
        @return int: (0: Ok, -1:error)
        """
        self.cool_all_switches()
        return 0

    def wake_up_magnet(self):
        """
        Heat all coils of the superconducting magnet to get back to the working state.
        @return int: (0: Ok, -1:error)
        """
        self.heat_all_switches()
        return 0

    def switch_mode(self, bool_var):
        """
        This function is special for this Super Conducting Magnet (SCM). It stems from the
        constraints on the coils. There is one mode (so called "normal_mode" which allows a field strength of up to 1 T
        in each direction and a combined field strength of 1.2 T. The z_mode is special as the z-coil can
        conduct more current and therefore exert higher field values. In this mode the combined field strength
        is allowed to be as high as 3 T but only within a cone of 5° to the z-axis.

        @param bool_var: True sets mode to "normal_mode", and False to "z_mode"
        @return int: (0: 0k, -1:error)
        """

        if bool_var:
            if self.mode != "normal_mode":
                self.calibrate()
                self.mode = "normal_mode"
        else:
            if self.mode != "z_mode":
                self.calibrate()
                self.mode = "z_mode"

    def target_field_setpoint(self, param_dict):
        """ Function to set the target field (in kG), which will be reached through the
            function ramp(self, param_list).

            @param dict param_dict: Contains as keys the axes to be set e.g. 'x' or 'y'
            and the items are the float values for the new field generated by the coil of
            that axis.
            @return int: error code (0:OK, -1:error)
            """

        field_dict = self.get_current_field()
        mode = self.mode

        if param_dict.get('x') is not None:
            field_dict['x'] = param_dict['x']
        elif param_dict.get('y') is not None:
            field_dict['y'] = param_dict['y']
        elif param_dict.get('z') is not None:
            field_dict['z'] = param_dict['z']
        else:
            self.logMsg('no valid axis was supplied in target_field_setpoint',
                        msgType='warning')
            return -1

        new_coord = [field_dict['x'], field_dict['y'], field_dict['z']]
        check_var = self.check_constraints({mode: {'cart': new_coord}})
        if check_var:
            if param_dict.get('x') is not None:
                self.soc_x.send(self.utf8_to_byte("CONF:FIELD:TARG " + str(param_dict['x']) + "\n"))
            if param_dict.get('y') is not None:
                self.soc_y.send(self.utf8_to_byte("CONF:FIELD:TARG " + str(param_dict['y']) + "\n"))
            if param_dict.get('z') is not None:
                self.soc_z.send(self.utf8_to_byte("CONF:FIELD:TARG " + str(param_dict['z']) + "\n"))

        else:
            self.logMsg('resulting field would be too high in target_field_setpoint',
                        msgType='warning')
            return -1

        return 0

    def ramp(self, param_list=None):
        """ function to ramp the magnetic field in the direction(s)  to the target field values

            @param list param_list: This param is optional. If supplied it has to
            contain the labels for the axes, which should be ramped (only cartesian makes sense here),
            else all axes will be ramped.
            @return int: error code (0:OK, -1:error)
            """
        if param_list is None:
            self.soc_x.send(self.utf8_to_byte("RAMP\n"))
            self.soc_y.send(self.utf8_to_byte("RAMP\n"))
            self.soc_z.send(self.utf8_to_byte("RAMP\n"))
        else:
            if 'x' in param_list:
                self.soc_x.send(self.utf8_to_byte("RAMP\n"))
            elif 'y' in param_list:
                self.soc_y.send(self.utf8_to_byte("RAMP\n"))
            elif 'z' in param_list:
                self.soc_z.send(self.utf8_to_byte("RAMP\n"))
            else:
                self.logMsg("in function ramp your definition of param_list was incorrect",
                            msgType='warning')
                return -1
        return 0

    def ramp_to_zero(self, axis):
        """ Function to ramp down a specific coil to zero current

            @param axis: string axis: (allowed inputs 'x', 'y' and 'z')
            """

        if axis == "x":
            self.soc_x.send(self.utf8_to_byte("ZERO\n"))
        elif axis == "y":
            self.soc_y.send(self.utf8_to_byte("ZERO\n"))
        elif axis == "z":
            self.soc_z.send(self.utf8_to_byte("ZERO\n"))
        else:
            print("Only x, y, z possible")

    def calibrate(self, param_list=None):
        """ Calibrates the stage. In the case of the super conducting magnet
            this just means moving all or a user specified coil to zero magnetic field.

        @param dict param_list: param_list: optional, if a specific calibration
                                of an axis is desired, then the labels of the
                                needed axis should be passed in the param_list.
                                If nothing is passed, then all connected axis
                                will be calibrated.

        @return int: error code (0:OK, -1:error)

        After calibration the stage moves to home position which will be the
        zero point for the passed axis. The calibration procedure will be
        different for each stage.
        """
        if not param_list:
            self.ramp_to_zero("x")
            self.ramp_to_zero("y")
            self.ramp_to_zero("z")
        else:
            if 'x' in param_list:
                self.ramp_to_zero("x")
            elif 'y' in param_list:
                self.ramp_to_zero("y")
            elif 'z' in param_list:
                self.ramp_to_zero("z")
            else:
                self.logMsg('no valid axis was supplied',
                            msgType='warning')
                return -1

        return 0

    def set_coordinates(self, param_dict):
        """
        Function to set spherical coordinates ( keep in mind all is in radians)
        This function is intended to replace the old set functions ( set_magnitude,
        set_theta, set_phi ).

        @param dict param_dict: dictionary, which passes all the relevant
                                field values, that should be passed. Usage:
                                {'axis_label': <the-abs-pos-value>}.
                                'axis_label' must correspond to a label given
                                to one of the axis. In this case the axes are
                                labeled 'rho', 'theta' and 'phi'

        @return int: error code (0:OK, -1:error)
        """

        answ_dict = {}
        coord_list = []
        transform_dict = {'cart': {'rad': coord_list}}

        answ_dict = self.get_current_field()
        coord_list.append(answ_dict['x'])
        coord_list.append(answ_dict['y'])
        coord_list.append(answ_dict['z'])

        coord_list = self.transform_coordinates(transform_dict)

        label_list = ['rho', 'theta', 'phi']

        if param_dict.get('rho') is not None:
            coord_list[0] = param_dict['rho']
        if param_dict.get('theta') is not None:
            coord_list[1] = param_dict['theta']
        if param_dict.get('phi') is not None:
            coord_list[2] = param_dict['phi']

        for key in param_dict.keys():
                if key not in label_list:
                    self.logMsg("The key "+key+" provided is no valid key in set_coordinates.",
                                msgType='warning')
                    return -1

        transform_dict = {'rad': {'cart': coord_list}}
        coord_list = self.transform_coordinates(transform_dict)

        set_point_dict = {'x': coord_list[0], 'y': coord_list[1],
                          'z': coord_list[2]}

        check_val = self.target_field_setpoint(set_point_dict)

        return check_val

    def move_abs(self, param_dict):
        """ Moves stage to absolute position (absolute movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, that should be changed. Usage:
                                {'axis_label': <the-abs-pos-value>}.
                                'axis_label' must correspond to a label given
                                to one of the axis. In this case the axes are
                                labeled 'rho', 'theta' and 'phi'.

        @return int: error code (0:OK, -1:error)
        """

        # the problem here is, that check_coordinates needs a complete dictionary with all
        # labels while move_abs doesn't need it. I think it is better to extend this flexibility to
        # check_constraints than changing move_abs.
#        check_bool = self.check_constraints({self.mode: param_dict})
        check_bool = True
        constr_dict = {}
        coord_list = []
        mode = self.mode

        param_dict = self.update_coordinates(param_dict)
        coord_list.append(param_dict['rho'])
        coord_list.append(param_dict['theta'])
        coord_list.append(param_dict['phi'])

        constr_dict = {mode: {'rad': coord_list}}
        check_bool = self.check_constraints(constr_dict)
        if check_bool:
            # first set, then ramp
            check_1 = self.set_coordinates(param_dict)
            check_2 = self.ramp()
        else:
            self.logMsg("move_abs hasn't done anything, see check_constraints message why", msgType="warning")
            return -1

        check_1 = self.set_coordinates(param_dict)
        check_2 = self.ramp()
        if check_1 == check_2:
            if check_1 == 0:
                return 0
        else:
            return -1

    def move_rel(self, param_dict):
        """ Moves stage in given direction (in spheric coordinates with theta and
            phi in radian)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                {'axis_label': <the-abs-pos-value>}.
                                'axis_label' must correspond to a label given
                                to one of the axis.

        @return int: error code (0:OK, -1:error)
        """
        answ_dict = {}
        coord_list = []
        transform_dict = {}
        new_coord_dict = {}

        answ_dict = self.get_current_field()

        coord_list.append(answ_dict['x'])
        coord_list.append(answ_dict['y'])
        coord_list.append(answ_dict['z'])

        transform_dict = {'cart': {'rad': coord_list}}

        coord_list = self.transform_coordinates(transform_dict)
        label_list = ['rho', 'theta', 'phi']
        if param_dict.get('rho') is not None:
            coord_list[0] += param_dict['rho']
        if param_dict.get('theta') is not None:
            coord_list[1] += param_dict['theta']
        if param_dict.get('phi') is not None:
            coord_list[2] += param_dict['phi']

        for key in param_dict.keys():
            if key not in label_list:
                self.logMsg("The key "+key+" provided is no valid key in set_coordinates.",
                            msgType='warning')
                return -1
        new_coord_dict = {'rho': coord_list[0], 'theta': coord_list[1],
                          'phi': coord_list[2]}
        check_val = self.move_abs(new_coord_dict)
        return check_val

    def transform_coordinates(self, param_dict):
        """ Function for generic coordinate transformation.
            This is a refactoring to the old functions (4) to be
            replaced by just one function
            @param dict param_dict: contains a param_dict, which contains
            a list of values to be transformed. The transformation depends
            on the keys of the first and the second dictionary.
            Possible keys are: "deg", "rad", "cart"
            for example if the first key is deg and the second is cartesian
            then the values in the list will be transformed from deg to
            cartesian.

            Ordering of the values should be [x,y,z] (cartesian)
            or [rho, theta, phi] for deg or rad
            @return list containing the transformed values
        """
        return_list = []
        # here all the possible cases for transformations
        # are checked
        if param_dict.get('deg') is not None:
            if param_dict['deg'].get('rad') is not None:
                try:
                    rho, theta, phi = param_dict['deg'].get('rad')
                except ValueError:
                    self.logMsg('Supplied input list for transform_coordinates has to be of length 3: returning initial values',
                                msgType='error')
                    return [-1, -1, -1]

                theta = theta*np.pi/180
                phi = phi*np.pi/180
                return_list = [rho, theta, phi]
                return return_list

            if param_dict['deg'].get('cart') is not None:
                cartesian_list = []
                try:
                    rho, theta, phi = param_dict['deg'].get('cart')
                except ValueError:
                    self.logMsg('Supplied input list for transform_coordinates has to be of length 3: returning [-1,-1,-1]',
                            msgType='error')
                    return [-1, -1, -1]
            # transformations that should probably be revisited.
            # They are there in case the theta and phi values
            # are not in the correct range.
                while theta >= 180:
                    phi += 180
                    theta = 360 - theta

                while theta < 0:
                    theta = -theta
                    phi += 180

                while phi >= 360:
                    phi += 360

                while phi < 0:
                    phi += 360

                cartesian_list.append(rho * np.sin(theta * 2 * np.pi / 360)
                                  * np.cos(phi * 2 * np.pi / 360))
                cartesian_list.append(rho * np.sin(theta * 2 * np.pi / 360)
                                  * np.sin(phi * 2 * np.pi / 360))
                cartesian_list.append(rho * np.cos(theta * 2 * np.pi / 360))

                return cartesian_list
        if param_dict.get('rad') is not None:
            if param_dict['rad'].get('deg') is not None:
                try:
                    rho, theta, phi  = param_dict['rad']['deg']
                except ValueError:
                    self.logMsg("Supplied input list for transform_coordinates has to be of length 3: returning [-1, -1, -1]", msgType="error")
                    return [-1,-1,-1]
                theta = 180*theta/np.pi
                phi = 180*phi/np.pi
                return_list = [rho, theta, phi]
                return return_list
            if param_dict['rad'].get('cart') is not None:
                try:
                    rho, theta, phi  = param_dict['rad']['cart']
                except ValueError:
                    self.logMsg("Supplied input list for transf has to be of length 3: returning [-1, -1, -1]", msgType="error")
                    return [-1,-1,-1]
                x_val = rho * np.sin(theta) * np.cos(phi)
                y_val = rho * np.sin(theta) * np.sin(phi)
                z_val = rho * np.cos(theta)
                return_list = [x_val, y_val, z_val]
                return return_list

        if param_dict.get('cart') is not None:
            if param_dict['cart'].get('deg') is not None:
                try:
                    x_val, y_val, z_val  = param_dict['cart']['deg']
                except ValueError:
                    self.logMsg("Supplied input list for transform_coordinates has to be of length 3: returning [-1, -1, -1]", msgType="error")
                    return [-1,-1,-1]
                rho = np.sqrt(x_val ** 2 + y_val ** 2 + z_val ** 2)
                if rho == 0:
                    theta = 0
                else:
                    theta = np.arccos(z_val/rho) * 360/(2 * np.pi)
                if x_val == 0 and y_val == 0:
                    phi = 0
                else:
                    phi = np.arctan2(y_val, x_val) * 360/(2 * np.pi)
                if phi < 0:
                    phi += 360
                return_list = [rho, theta, phi]
                return return_list

            if param_dict['cart'].get('rad') is not None:
                try:
                    x_val, y_val, z_val  = param_dict['cart']['rad']
                except ValueError:
                    self.logMsg("Supplied input list for transform_coordinates has to be of length 3: returning [-1, -1, -1]", msgType="error")
                    return [-1,-1,-1]
                rho = np.sqrt(x_val ** 2 + y_val ** 2 + z_val ** 2)
                if rho == 0:
                    theta = 0
                else:
                    theta = np.arccos(z_val/rho)

                if x_val == 0 and y_val == 0:
                    phi = 0
                else:
                    phi = np.arctan2(y_val, x_val)
                if phi < 0:
                    phi += 2 * np.pi
                return_list = [rho, theta, phi]
                return return_list

    def get_current_field(self):
        """ Function that asks the magnet for the current field strength in each direction

            @param:

            @param x : representing the field strength in x direction
            @param y : representing the field strength in y direction
                          float z : representing the field strength in z direction

            """
        ask_dict = {}
        answ_dict = {}
        ask_dict['x'] = "FIELD:MAG?\n"
        ask_dict['y'] = "FIELD:MAG?\n"
        ask_dict['z'] = "FIELD:MAG?\n"
        answ_dict = self.ask(ask_dict)

        answ_dict['x'] = float(answ_dict['x'])
        answ_dict['y'] = float(answ_dict['y'])
        answ_dict['z'] = float(answ_dict['z'])
        #print(x, y, z)
        return answ_dict

    def get_pos(self, param_list=None):
        """ Gets current position of the stage

        @param list param_list: optional, if a specific position of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                position is asked.

        @return dict mypos: with keys being the axis labels and item the current
                      position. Given in spheric coordinates with Units T, rad , rad.
        """




        mypos = {}
        mypos1 = {}
        ask_dict = {}
        answ_dict = {}

        answ_dict = self.get_current_field()
        coord_list = [answ_dict['x'], answ_dict['y'], answ_dict['z']]
        rho, theta, phi = self.transform_coordinates({'cart': {'rad': coord_list}})
        mypos1['rho'] = rho
        mypos1['theta'] = theta
        mypos1['phi'] = phi

        if param_list is None:
            return mypos1

        else:
            if "rho" in param_list:
                mypos['rho'] = mypos1['rho']
            elif "theta" in param_list:
                mypos['theta'] = mypos1['theta']
            elif "phi" in param_list:
                mypos['phi'] = mypos1['phi']

        return mypos


    def stop_hard(self, param_list = None):
        """ function that pauses the heating of a specific coil depending on
            the elements in param_list.

            @param list param_list: Can contain elements 'x', 'y' or 'z'. In the case no list is supplied the heating
            of all coils is stopped
            @return integer: 0 everything is ok and -1 an error occured.
            """
        if not param_list:
            self.soc_x.send(self.utf8_to_byte("PAUSE\n"))
            self.soc_y.send(self.utf8_to_byte("PAUSE\n"))
            self.soc_z.send(self.utf8_to_byte("PAUSE\n"))
        elif len(param_list) > 0:
            self.logMsg('Some useless parameters were passed.',
            msgType='warning')
            return -1
        else:
            if 'x' in param_list:
                self.soc_x.send(self.utf8_to_byte("PAUSE\n"))
                param_list.remove('x')
            if 'y' in param_list:
                self.soc_y.send(self.utf8_to_byte("PAUSE\n"))
                param_list.remove('y')
            if 'z' in param_list:
                self.soc_z.send(self.utf8_to_byte("PAUSE\n"))
                param_list.remove('z')

        return 0

    def abort(self):
        """ Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
# could think about possible exceptions here and
# catch them and return -1 in case
        ab = self.stop_hard()

        return ab

    def ask_status(self, param_list = None):
        """ Function that returns the status of the coils ('x','y' and 'z') given in the
            param_dict

            @param list param_list: string (elements allowed  'x', 'y' and 'z')
            for which the status should be returned. Can be None, then
            the answer is the same as for the list ['x','y','z'].

            @return state: returns a string, which contains the number '1' to '10' representing
            the state, the magnet is in.

            For further information on the meaning of the numbers see
            translated_get_status()
            """
        ask_dict = {}

# lets do this twice, because the magnet gives me for the first request often
# quiet the non sense.
        for i_dea in range(2):
            if not param_list:
                ask_dict['x'] = "STATE?\n"
                ask_dict['y'] = "STATE?\n"
                ask_dict['z'] = "STATE?\n"
            else:
                for axis in param_list:
                    ask_dict[axis] = "STATE?\n"
            if i_dea == 0:
# wait some time not sure if this is necessary.
                time.sleep(self.waitingtime)

        answer_dict = self.ask(ask_dict)

        return answer_dict

    def translator_for_get_status(self, status):
        """

        @param status: The status coming from ask_status
        @return: -1, 0, 1. Depending on the translation
        """

        translated_status = -1
        if status == '1':
            translated_status = 1
        elif status == '2':
            translated_status = 0
        elif status == '3':
            translated_status = 0
        elif status == '4':
            translated_status = 1
        elif status == '5':
            translated_status = 0
        elif status == '6':
            translated_status = 1
        elif status == '7':
            translated_status = -1
        elif status == '8':
            translated_status = 0
        elif status == '9':
            translated_status = 1
        elif status == '10':
            translated_status = 1

        return translated_status

    def translated_get_status(self, param_list = None):
        """ Just a translation of the numbers according to the
            manual supplied by American Magnets, Inc.

            @param list param_list: string (elements allowed  'x', 'y' and 'z')
            for which the translated status should be returned. Can be None, then
            the answer is the same as for the list ['x','y','z']

            @return dictionary status_dict: keys are the elements of param_list and the items contain the
            message for the user.
            """
        status_dict = self.ask_status(param_list)

        for myiter in status_dict.keys():
            stateval = status_dict[myiter]

            try:
                if int(stateval) > 10:
                    stateval = int(stateval)
                    while (stateval > 10):
                        stateval //= 10
                    stateval = str(stateval)

                if stateval == '1':
                    translated_status = 'RAMPING to target field/current'
                elif stateval == '2':
                    translated_status = 'HOLDING at the target field/current'
                elif stateval == '3':
                    translated_status = 'PAUSED'
                elif stateval == '4':
                    translated_status = 'Ramping in MANUAL UP mode'
                elif stateval == '5':
                    translated_status = 'Ramping in MANUAL DOWN mode'
                elif stateval == '6':
                    translated_status = 'ZEROING CURRENT (in progress)'
                elif stateval == '7':
                    translated_status = 'Quench detected'
                elif stateval == '8':
                    translated_status = 'At ZERO current'
                elif stateval == '9':
                    translated_status = 'Heating persistent switch'
                elif stateval == '10':
                    translated_status = 'Cooling persistent switch'
                else:
                    self.logMsg('Something went wrong in ask_status as the statevalue was not between 1 and 10!',
                            msgType='warning')
                    return -1
            except ValueError:
                self.logMsg("Sometimes the magnet returns nonsense after a request", msgType="warning")
                return -1
            status_dict[myiter] = translated_status

        return status_dict

# This first version of set and get velocity will be very simple
# Normally one can set up several ramping rates for different field
# regions and so on. I also leave it to the user to find out how many
# segments he has and so on. If nothing is changed the magnet should have
# 1 segment and max_val should be the max_val that can be reached in that
# direction.
    def set_velocity(self, param_dict):
        """ Function to change the ramp rate  in kG/s (ampere per second)
            @param dict: contains as keys the different cartesian axes ('x', 'y', 'z')
                         and the dict contains list of parameters, that have to be supplied.
                         In this case this is segment, ramp_rate and maxval.
                         How does this work? The maxval for the current marks the endpoint
                         and in between you have several segments with differen ramp_rates.

            @return int: error code (0:OK, -1:error)

            """
        tell_dict = {}
        return_val = 0
        internal_counter = 0
        constraint_dict = self.get_constraints()

        if param_dict.get('x') is not None:
            param_list = param_dict['x']
            constraint_x = constraint_dict['rho']['vel_max']
            if constraint_x > param_list[1]:
                tell_dict['x'] = 'CONF:RAMP:RATE:FIELD:' + str(param_list[0]) + ", " + str(param_list[1]) + ", " + str(param_list[0])
            else:
                self.logMsg("constraint vel_max was violated in set_velocity with axis = 'x'", msgType='warning')

            internal_counter += 1
        if param_dict.get('y') is not None:
            param_list = param_dict['y']
            constraint_y = constraint_dict['theta']['vel_max']
            if constraint_y > param_list[1]:
                tell_dict['y'] = 'CONF:RAMP:RATE:FIELD:' + str(param_list[0]) + ", " + str(param_list[1]) + ", " + str(param_list[0])
            else:
                self.logMsg("constraint vel_max was violated in set_velocity with axis = 'y'", msgType='warning')
            internal_counter += 1
        if param_dict.get('z') is not None:
            param_list = param_dict['z']
            constraint_z = constraint_dict['phi']['vel_max']
            print(constraint_z)
            if constraint_z > param_list[1]:
                tell_dict['z'] = 'CONF:RAMP:RATE:FIELD:' + str(param_list[0]) + ", " + str(param_list[1]) + ", " + str(param_list[0])
            else:
                self.logMsg("constraint vel_max was violated in set_velocity with axis = 'z'", msgType='warning')
            internal_counter += 1

        if internal_counter > 0:
            self.tell(tell_dict)
        else:
            self.logMsg('There was no statement supplied in change_ramp_rate',
                        msgType='warning')
            return_val = -1

        return return_val

    def get_velocity(self, param_list=None):
        """ Gets the current velocity for all connected axes.

        @param dict param_list: optional, if a specific velocity of an axis
                                is desired, then the labels of the needed
                                axis should be passed as the param_list.
                                If nothing is passed, then from each axis the
                                velocity is asked.

        @return dict: with the axis label as key and the velocity as item.
        """
        ask_dict = {}
        answ_dict = {}
        return_dict = {}

        if param_list is None:
            ask_dict['x'] = "RAMP:RATE:FIELD:1?"
            ask_dict['y'] = "RAMP:RATE:FIELD:1?"
            ask_dict['z'] = "RAMP:RATE:FIELD:1?"
            answ_dict = self.ask(ask_dict)
            return_dict['x'] = float(answ_dict['x'].split(',')[0])
            return_dict['y'] = float(answ_dict['y'].split(',')[0])
            return_dict['z'] = float(answ_dict['z'].split(',')[0])
        else:
            for axis in param_list:
                ask_dict[axis] = "RAMP:RATE:FIELD:1?"
            answ_dict = self.ask(ask_dict)
            for axis in param_list:
                return_dict[axis] = float(answ_dict[axis].split(',')[0])

        return return_dict

    def check_constraints(self, param_dict):
        """
        Function that verifies if for a given configuration of field strength exerted through the coils
        the constraints of the magnet are violated.

        @param dictionary param_dict: the structure of the dictionary is as follows {'z_mode': {'cart': [a,b,c]}}
        with available keys 'z_mode' and 'normal_mode'. The dictionary inside the dictionary can contain the label
        'deg', 'cart' and 'rad'. The list contains then the new values and checks the
        constraints for them. z_mode means you can reach fields of 3 T in z-direction as long as the field vector
        is directed in z-direction within an accuracy of 5°. In this mode you should still be careful and the
        5° restriction is kind of arbitrary and not experimented with.
        @return: boolean check_var: True if the constraints are fulfilled and False otherwise
        """
        # First going to include a local function to check the constraints for cartesian coordinates
        # This helps to just reuse this function for the check of 'deg' and 'rad' cases.

        def check_cart_constraints(coord_list, mode):

            my_boolean = True
            try:
                x_val, y_val, z_val = coord_list
            except ValueError:
                self.logMsg("In check_constraints list has not the right amount of elements (3).", msgType="error")
                return [-1, -1, -1]
            if mode == "normal_mode":
                if np.abs(x_val) > self.x_constr:
                    my_boolean = False
                    self.logMsg("In check_constraints the field constraint in x-direction would be violated"
                                " with your settings.",
                                msgType="error")
                if np.abs(y_val) > self.y_constr:
                    my_boolean = False
                    self.logMsg("In check_constraints the field constraint in y-direction would be violated"
                                " with your settings.",
                                msgType="error")
                #the x here is intentional, as the normal_mode constraints are cubic.
                if np.abs(z_val) > self.x_constr:
                    my_boolean = False
                    self.logMsg("In check_constraints the field constraint in z-direction would be violated"
                                " with your settings.",
                                msgType="error")
                field_magnitude = np.sqrt(x_val**2 + y_val**2 + z_val**2)
                if field_magnitude > self.rho_constr:
                    my_boolean = False
                    self.logMsg("In check_constraints your settings would surpass the allowed length"
                                " of the magnetic field vector.",
                                msgType="error")
            elif mode == "z_mode":
                # Either in sphere on top of the cone
                # or in cone itself.
                my_boolean = False
                # angle 5° cone
                hight_cone = 28.744967610261352

                if (np.abs(z_val) <= hight_cone) and ((x_val**2 + y_val**2) <= z_val**2):
                    my_boolean = True
                elif x_val**2 + y_val**2 + (z_val-hight_cone)**2 <= self.rho_constr:
                    my_boolean = True
                elif x_val**2 + y_val**2 + (z_val+hight_cone)**2 <= self.rho_constr:
                    my_boolean = True

                if not my_boolean:
                    self.logMsg("In check_constraints your settings don't lie in the allowed cone. See the "
                                "function for move information", msgType="warning")
            return my_boolean

        return_val = False

        constr = self.get_constraints()

        if param_dict.get('normal_mode') is not None:
            if param_dict['normal_mode'].get("cart") is not None:
                return_val = check_cart_constraints(param_dict['normal_mode']["cart"], 'normal_mode')
            if param_dict['normal_mode'].get("rad") is not None:
                transform_dict = {'rad': {'cart': param_dict['normal_mode']["rad"]}}
                cart_coord = self.transform_coordinates(transform_dict)
                return_val = check_cart_constraints(cart_coord, 'normal_mode')
                theta = param_dict['normal_mode']['rad'][1]
                phi = param_dict['normal_mode']['rad'][2]
                if not (constr['theta']['pos_min'] <= theta <= constr['theta']['pos_max']):
                    print("now here")
                    return_val = False
                    self.logMsg("In check_constraints your theta values don't lie between 0 and pi. Can lead to "
                                "erroneous behavior", msgType="warning")
                if not (constr['phi']['pos_min'] <= phi <= constr['phi']['pos_max']):
                    return_val = False
                    self.logMsg("In check_constraints your phi values don't lie between 0 and 2 pi."
                                " Can lead to erroneous behavior", msgType="warning")
# ok degree mode here won't work properly, because I don't check the move constraints
            if param_dict['normal_mode'].get("deg") is not None:
                transform_dict = {'deg': {'cart': param_dict['normal_mode']["deg"]}}
                cart_coord = self.transform_coordinates(transform_dict)
                return_val = check_cart_constraints(cart_coord, 'normal_mode')

        elif param_dict.get('z_mode') is not None:
            if param_dict['z_mode'].get("cart") is not None:
                return_val = check_cart_constraints(param_dict['z_mode']["cart"], 'z_mode')

            if param_dict['z_mode'].get("rad") is not None:
                transform_dict = {'rad':{'cart': param_dict['z_mode']["rad"]}}
                cart_coord = self.transform_coordinates(transform_dict)
                return_val = check_cart_constraints(cart_coord, 'z_mode')
                theta = param_dict['z_mode']['rad'][1]
                phi = param_dict['z_mode']['rad'][2]
                if not (0 <= theta <= 5*np.pi/180):
                    return_val = False
                    self.logMsg("In check_constraints your theta values don't lie between 0 and  5 pi / 180."
                                , msgType="warning")
                if not (constr['phi']['pos_min'] <= phi <= constr['phi']['pos_max']):
                    return_val = False
                    self.logMsg("In check_constraints your phi values don't lie between 0 and 2 pi."
                                "Can lead to erroneous behavior", msgType="warning")
            if param_dict['z_mode'].get("deg") is not None:
                transform_dict = {'deg': {'cart': param_dict['z_mode']["deg"]}}
                cart_coord = self.transform_coordinates(transform_dict)
                return_val = check_cart_constraints(cart_coord, 'z_mode')
        else:
            self.logMsg("no valid key was provided, therefore nothing happened in function check_constraints."
                        , msgType="warning")
        return return_val

    def rho_max_pos(self, param_dict):
        """
        Function that calculates the constraint for rho either given theta and phi values in degree
        or x, y and z in cartesian coordinates.

        @param dictionary param_dict: Has to be of the form {'normal_mode': {'rad': [rho, theta, phi]}} supports also 'deg' and 'cart option.

        @return float max_pos: the max position for given theta and phi values. Returns -1 in case of failure.
        """
        # so I'm going to rework this function. The answer in the case
        # of z_mode is easy. (Max value for r is constant 30 True)
        # For the "normal_mode" I decided to come up with a new
        # algorithm.
        # That algorithm can be summarized as follows:
        # Check if the vector  (r,theta,phi)
        # with length so that it is on the surface conflicts with the
        # rectangular constraints given by the coils itself (x<=10, y<=10, z<=10)
        # If not, we have found max rho. Else we need to find the
        # intersection between the vector and the rectangular (Sadly this will need
        # 6 cases).

        max_pos = -1

        if param_dict.get("z_mode") is not None:
            if self.check_constraints(param_dict):
                max_pos = self.z_constr
            else:
                max_pos = 0.0
        elif param_dict.get("normal_mode") is not None:
            if param_dict["normal_mode"].get("cart") is not None:
                transform_dict = {'cart': {'rad': param_dict["normal_mode"].get("cart")}}
                coord_dict_rad = self.transform_coordinates(transform_dict)
                coord_dict_rad = {'rad': coord_dict_rad}
                coord_dict_rad['rad'][0] = self.rho_constr
                transform_dict = {'rad': {'cart': coord_dict_rad['rad']}}
                coord_dict_cart = self.transform_coordinates(transform_dict)
                coord_dict_cart = {'normal_mode': {'cart': coord_dict_cart}}


            elif param_dict["normal_mode"].get("rad") is not None:
                coord_list = param_dict["normal_mode"]["rad"]
                coord_dict_rad = param_dict["normal_mode"]
                coord_dict_rad['rad'][0] = self.rho_constr
                transform_dict = {'rad': {'cart': coord_dict_rad['rad']}}
                coord_dict_cart = self.transform_coordinates(transform_dict)
                coord_dict_cart = {'normal_mode': {'cart': coord_dict_cart}}

            elif param_dict["normal_mode"].get("deg") is not None:
                coord_list = param_dict["normal_mode"]["deg"]
                coord_dict_deg = param_dict["normal_mode"]
                coord_dict_deg['deg'][0] = self.rho_constr
                coord_dict_rad = self.transform_coordinates({'deg': {'rad': coord_dict_deg['deg']}})
                coord_dict_rad = {'rad': coord_dict_rad}
                transform_dict = {'rad': {'cart': coord_dict_rad['rad']}}
                coord_dict_cart = self.transform_coordinates(transform_dict)
                coord_dict_cart = {'normal_mode': {'cart': coord_dict_cart}}

            my_boolean = True
            my_boolean = self.check_constraints(coord_dict_cart)

            if my_boolean:
                max_pos = self.rho_constr
            else:
                    # now I need to find out, which plane I need to check
                phi = coord_dict_rad['rad'][2]
                theta = coord_dict_rad['rad'][1]
                # Sides of the rectangular intersecting with position vector
                if (0.9553166181245093 <= theta) and (theta < np.pi - 0.9553166181245093):
                    if (7*np.pi/4 < phi < 0) or (0 <= phi <= np.pi/4):
                        max_pos = self.x_constr/(np.cos(phi)*np.sin(theta))
                    elif (np.pi/4 < phi) and (phi <= 3*np.pi/4):
                        max_pos = self.y_constr / (np.sin(phi)*np.sin(theta))
                    elif (3*np.pi/4 < phi) and (phi <= 5*np.pi/4):
                        max_pos = -self.x_constr/(np.cos(phi)*np.sin(theta))
                    elif (5*np.pi/4 < phi) and (phi <= 7*np.pi/4):
                        max_pos = -self.y_constr / (np.sin(phi)*np.sin(theta))
                    # Top and bottom of the rectangular
                elif (0 <= theta) and ( theta < 0.9553166181245093):
                    max_pos = self.x_constr / np.cos(theta)
                elif (np.pi - 0.9553166181245093 <= theta) and (theta <= np.pi):
                    max_pos = - self.x_constr / np.cos(theta)
        return max_pos

    def update_coordinates(self, param_dict):
        """
        A small helper function that does make the functions set_coordinates, transform_coordinates compatible
        with the interface defined functions. The problem is, that in the interface functions each coordinate
        is item to an key which represents the axes of the current coordinate system. This function only
        makes the set of coordinates complete. E.g {'rho': 1.3} to {'rho': 1.3, 'theta': np.pi/2, 'phi': 0 }

        @param param_dict:  Contains the incomplete dictionary
        @return: the complete dictionary
        """
        current_coord_dict = self.get_pos()

        for key in current_coord_dict.keys():
            if param_dict.get(key) is None:
                param_dict[key] = current_coord_dict[key]

        return param_dict
