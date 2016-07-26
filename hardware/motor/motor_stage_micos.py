# -*- coding: utf-8 -*-

"""
This file contains the hardware control of the motorized stage for PI Micos.

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

import visa
import time

from core.base import Base
from interface.motor_interface import MotorInterface

class MotorStageMicos(Base, MotorInterface):
    """unstable: Jochen Scheuer.
    Hardware class to define the controls for the Micos stage of PI.
    """
    _modclass = 'MotorStageMicos'
    _modtype = 'hardware'
    # connectors
    _out = {'motorstage': 'MotorInterface'}

#Questions:
#    Are values put in the right way in config????
#    change return values to sensible values??? - not so important
#    After moving files what has to be changed, where?

#Christoph:
#    make on activate method which asks for values with get_pos()
#    checks for sensible values???
#    default parameters should be none
#    introduce dead-times while waiting?
#    check if sensible value and check for float!!!! in interface
#    put together everything to one step???

#Things to be changed in logic:
#    Name of modules for steps
#    getpos
#    kill strgc method

#changes:
#    change time for waiting until next command is sent
#    change prints to log messages
#    wait in calibrate or implement get_cal
#    make subfolder with __init__ for subfolder check GUI
#    change format string to new convention

    def __init__(self, manager, name, config, **kwargs):
        state_actions = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, state_actions, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{}: {}'.format(key,config[key]))
    def activation(self, e):


        # ALEX COMMENT: Why are the values stored? In general that is not a
        #               good idea.

#        self.x_store=-1
#        self.y_store=-1
#        self.z_store=-1
#        self.phi_store=-1



        self.rm = visa.ResourceManager()

        # Read HW from config
        config = self.getConfiguration()

        # here the COM port is read from the config file
        if 'com_port_micos_xy' in config.keys():
            self._com_port_xy, label_x, label_y  = config['com_port_micos_xy']
        else:
            self.log.error('No parameter "com_port_micos_xy" found in '
                    'config.\n'
                    'Cannot connect to motorized stage! Enter the '
                    'parameter with the following scheme:/n'
                    '("<COM-PORT>","<lable_x_axis>","label_y_axis")')


        if 'com_port_micos_zphi' in config.keys():
            self._com_port_zphi, label_z, label_phi  = config['com_port_micos_zphi']
        else:
            self.log.error('No parameter "com_port_micos_zphi" found in '
                    'config.\nCannot connect to motorized stage! Enter the '
                    'parameter with the following scheme:/n'
                    '("<COM-PORT>","<lable_x_axis>","label_y_axis")')

        # here the variables for the terminal character are read in
        if 'micos_term_chars_xy' in config.keys():
            self._term_chars_xy = config['micos_term_chars_xy']
        else:
            self._term_chars_xy = '\n'
            self.log.warning('No parameter "micos_term_chars_xy" found in '
                    'config!\nTaking LF character "\\n" instead.')

        if 'micos_term_chars_zphi' in config.keys():
            self._term_chars_zphi = config['micos_term_chars_zphi']
        else:
            self._term_chars_zphi = '\n'
            self.log.warning('No parameter "micos_term_chars_zphi" found in '
                    'config!\nTaking LF character "\\n" instead.')

        # here the variables for the baud rate are read in
        if 'micos_baud_rate_xy' in config.keys():
            self._baud_rate_xy = config['micos_baud_rate_xy']
        else:
            self._baud_rate_xy = 57600
            self.log.warning('No parameter "micos_baud_rate_xy" found in '
                    'config!\nTaking the baud rate {0} '
                    'instead.'.format(self._baud_rate_xy))

        if 'micos_baud_rate_zphi' in config.keys():
            self._baud_rate_zphi = config['micos_baud_rate_zphi']
        else:
            self._baud_rate_zphi = 57600
            self.log.warning('No parameter "micos_baud_rate_zphi" found in '
                    'config!\nTaking the baud rate {0} '
                    'instead.'.format(self._baud_rate_zphi))

        self._micos_a = self.rm.open_resource(self._com_port_xy) # x, y
        self._micos_a.label_x = label_x     # attach a label attribute
        self._micos_a.label_y = label_y     # attach a label attribute
        self._micos_b = self.rm.open_resource(self._com_port_zphi) # z, phi
        self._micos_b.label_z = label_z     # attach a label attribute
        self._micos_b.label_phi = label_phi # attach a label attribute

        self._micos_a.term_chars = self._term_chars_xy
        self._micos_a.term_chars = self._term_chars_zphi
        self._micos_a.baud_rate = self._baud_rate_xy
        self._micos_b.baud_rate = self._baud_rate_zphi


    def deactivation(self, e):
        """ Disconnect from hardware and clean up """
        self._micos_a.close()
        self._micos_b.close()
        self.rm.close()

    def get_constraints(self):
        """ Retrieve the hardware constrains from the motor device.

        @return dict: dict with constraints for the sequence generation and GUI

        Provides all the constraints for the motorized stage (like total
        movement, velocity, ...)
        Each constraint is a tuple of the form
            (min_value, max_value, stepsize)

        The possible keys in the constraint are defined here in the interface
        file. If the hardware does not support the values for the constraints,
        then insert just None.
        If you are not sure about the meaning, look in other hardware files
        to get an impression.
        """
        constraints = {}

        # ALEX COMMENT: Please find all the needed parameter in the manual.
        #               In principle, all should be available. If still not
        #               available use None as an assignment.

        axis0 = {}
        axis0['label'] = self._micos_a.label_x # name is just as a sanity included
        axis0['unit'] = 'm'                 # the SI units
        axis0['ramp'] = ['Sinus','Linear'] # a possible list of ramps
        axis0['pos_min'] = 0
        axis0['pos_max'] = 95  # that is basically the traveling range
        axis0['pos_step'] = 0.01
        axis0['vel_min'] = 0
        axis0['vel_max'] = 10
        axis0['vel_step'] = 0.01
        axis0['acc_min'] = 0.1
        axis0['acc_max'] = 100.0
        axis0['acc_step'] = 0.0

        axis1 = {}
        axis1['label'] = self._micos_a.label_y        # that axis label should be obtained from config
        axis1['unit'] = 'm'        # the SI units
        axis1['ramp'] = ['Sinus','Linear'] # a possible list of ramps
        axis1['pos_min'] = 0
        axis1['pos_max'] = 95  # that is basically the traveling range
        axis1['pos_step'] = 0.01
        axis1['vel_min'] = 0
        axis1['vel_max'] = 10
        axis1['vel_step'] = 0.01
        axis1['acc_min'] = 0.1
        axis1['acc_max'] = 0.0
        axis1['acc_step'] = 0.0

        axis2 = {}
        axis2['label'] = self._micos_b.label_z        # that axis label should be obtained from config
        axis2['unit'] = 'm'        # the SI units
        axis2['ramp'] = ['Sinus','Linear'] # a possible list of ramps
        axis2['pos_min'] = 0
        axis2['pos_max'] = 60  # that is basically the traveling range
        axis2['pos_step'] = 0.01
        axis2['vel_min'] = 0
        axis2['vel_max'] = 100
        axis2['vel_step'] = 0.01
        axis2['acc_min'] = 0.1
        axis2['acc_max'] = 0.0
        axis2['acc_step'] = 0.0

        axis3 = {}
        axis3['label'] = self._micos_b.label_phi      # that axis label should be obtained from config
        axis3['unit'] = '°'        # the SI units
        axis3['ramp'] = ['Sinus','Trapez'] # a possible list of ramps
        axis3['pos_min'] = 0
        axis3['pos_max'] = 330  # that is basically the traveling range
        axis3['pos_step'] = 0.01
        axis3['vel_min'] = 1
        axis3['vel_max'] = 20
        axis3['vel_step'] = 0.1
        axis3['acc_min'] = None
        axis3['acc_max'] = None
        axis3['acc_step'] = None

        # assign the parameter container for x to a name which will identify it
        constraints[axis0['label']] = axis0
        constraints[axis1['label']] = axis1
        constraints[axis2['label']] = axis2
        constraints[axis3['label']] = axis3

        return constraints

    def move_rel(self,  param_dict):
        """ Moves stage in given direction (relative movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed.
                                With get_constraints() you can obtain all
                                possible parameters of that stage. According to
                                this parameter set you have to pass a dictionary
                                with keys that are called like the parameters
                                from get_constraints() and assign a SI value to
                                that. For a movement in x the param_dict should
                                e.g. have the form:
                                    dict = { 'x' : 23 }
                                where the label 'x' corresponds to the chosen
                                axis label.

        A smart idea would be to ask the position after the movement.
        """
        curr_pos_dict = self.get_pos()
        constraints = self.get_constraints()

        # Check if value for the new x position is valid and move to the new x position, else return an error msg

        if param_dict.get(self._micos_a.label_x) is not None:
            move_x = param_dict[self._micos_a.label_x]
            curr_pos_x = curr_pos_dict[self._micos_a.label_x]

            if  (curr_pos_x + move_x > constraints[self._micos_a.label_x]['pos_max'] ) or\
                (curr_pos_x + move_x < constraints[self._micos_a.label_x]['pos_min']):

                self.log.warning('Cannot make further movement of the axis '
                        '"{0}" with the step {1}, since the border [{2},{3}] '
                        'was reached! Ignore command!'.format(
                            self._micos_a.label_x, move_x,
                            constraints[self._micos_a.label_x]['pos_min'],
                            constraints[self._micos_a.label_x]['pos_max']))
            else:
                self._micos_a.write('{:f} 0.0 0.0 r'.format(move_x))

        # Check if value for the new y position is valid and move to the new y position, else return an error msg

        if param_dict.get(self._micos_a.label_y) is not None:
            move_y = param_dict[self._micos_a.label_y]
            curr_pos_y = curr_pos_dict[self._micos_a.label_y]

            if  (curr_pos_y + move_y > constraints[self._micos_a.label_y]['pos_max'] ) or\
                (curr_pos_y + move_y < constraints[self._micos_a.label_y]['pos_min']):

                self.log.warning('Cannot make further movement of the axis '
                        '"{0}" with the step {1}, since the border [{2},{3}] '
                        'was reached! Ignore command!'.format(
                            self._micos_a.label_y, move_y,
                            constraints[self._micos_a.label_y]['pos_min'],
                            constraints[self._micos_a.label_y]['pos_max']))
            else:
                self._micos_a.write('0.0 {:f} 0.0 r'.format(move_y))

        # Check if value for the new z position is valid and move to the new z position, else return an error msg

        if param_dict.get(self._micos_b.label_z) is not None:
            move_z = param_dict[self._micos_b.label_z]
            curr_pos_z = curr_pos_dict[self._micos_b.label_z]

            if  (curr_pos_z + move_z > constraints[self._micos_b.label_z]['pos_max'] ) or\
                (curr_pos_z + move_z < constraints[self._micos_b.label_z]['pos_min']):

                self.log.warning('Cannot make further movement of the axis '
                        '"{0}" with the step {1}, since the border [{2},{3}] '
                        'was reached! Ignore command!'.format(
                            self._micos_b.label_z, move_z,
                            constraints[self._micos_b.label_z]['pos_min'],
                            constraints[self._micos_b.label_z]['pos_max']))
            else:
                self._micos_b.write('{:f} 0.0 0.0 r'.format(move_z))

        # Check if value for the new phi position is valid and move to the new phi position, else return an error msg

        if param_dict.get(self._micos_b.label_phi) is not None:
            move_phi = param_dict[self._micos_b.label_phi]
            curr_pos_phi = curr_pos_dict[self._micos_b.label_phi]

            if  (curr_pos_phi + move_phi > constraints[self._micos_b.label_phi]['pos_max'] ) or\
                (curr_pos_phi + move_phi < constraints[self._micos_b.label_phi]['pos_min']):

                self.log.warning('Cannot make further movement of the axis '
                        '"{0}" with the step {1}, since the border [{2},{3}] '
                        'was reached! Ignore command!'.format(
                            self._micos_b.label_phi, move_phi,
                            constraints[self._micos_b.label_phi]['pos_min'],
                            constraints[self._micos_b.label_phi]['pos_max']))
            else:
                self._micos_b.write('0.0 {:f} 0.0 r'.format(move_phi))

    def move_abs(self, param_dict):
        """ Moves stage to absolute position (absolute movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <a-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
        A smart idea would be to ask the position after the movement.
        """
        constraints = self.get_constraints()

        # ALEX COMMENT: I am not quite sure whether one has to call each
        #               axis, i.e. _micos_a and _micos_b only once, and then
        #               wait until they are finished.
        #               You have either to restructure the axis call and find
        #               out how to block any signal until the stage is not
        #               finished with the movement. Maybe you have also to
        #               increase the visa timeout number, because if the device
        #               does not react on a command after the timeout an error
        #               will be raised by the visa protocol itself!

        if param_dict.get(self._micos_a.label_x) is not None:
            desired_pos = param_dict[self._micos_a.label_x]

            if  (desired_pos > constraints[self._micos_a.label_x]['pos_max'] ) or\
                (desired_pos < constraints[self._micos_a.label_x]['pos_min']):

                self.log.warning('Cannot make absolute movement of the axis '
                        '"{0}" to possition {1}, since it exceeds the limts '
                        '[{2},{3}] ! Command is ignored!'.format(
                            self._micos_a.label_x, desired_pos,
                            constraints[self._micos_a.label_x]['pos_min'],
                            constraints[self._micos_a.label_x]['pos_max']))
            else:
                self._micos_a.write('{:f} 0.0 0.0 move'.format(desired_pos) )
                self._micos_a.write('0.0 0.0 0.0 r')    # This should block further commands until the movement is finished
            try:
                statusA = int(self._micos_a.ask('st'))
            except:
                statusA = 0


        if param_dict.get(self._micos_a.label_y) is not None:
            desired_pos = param_dict[self._micos_a.label_y]

            if  (desired_pos > constraints[self._micos_a.label_y]['pos_max'] ) or\
                (desired_pos < constraints[self._micos_a.label_y]['pos_min']):

                self.log.warning('Cannot make absolute movement of the axis '
                        '"{0}" to possition {1}, since it exceeds the limts '
                        '[{2},{3}] ! Command is ignored!'.format(
                            self._micos_a.label_y, desired_pos,
                            constraints[self._micos_a.label_y]['pos_min'],
                            constraints[self._micos_a.label_y]['pos_max']))
            else:
                self._micos_a.write('0.0 {:f} 0.0 move'.format(desired_pos) )
                self._micos_a.write('0.0 0.0 0.0 r')    # This should block further commands until the movement is finished
            try:
                statusA = int(self._micos_a.ask('st'))
            except:
                statusA = 0

        if param_dict.get(self._micos_b.label_z) is not None:
            desired_pos = param_dict[self._micos_b.label_z]

            if  (desired_pos > constraints[self._micos_b.label_z]['pos_max'] ) or\
                (desired_pos < constraints[self._micos_b.label_z]['pos_min']):

                self.log.warning('Cannot make absolute movement of the axis '
                        '"{0}" to possition {1}, since it exceeds the limts '
                        '[{2},{3}] ! Command is ignored!'.format(
                            self._micos_b.label_z, desired_pos,
                            constraints[self._micos_b.label_z]['pos_min'],
                            constraints[self._micos_b.label_z]['pos_max']))
            else:
                self._micos_b.write('{:f} 0.0 0.0 move'.format(desired_pos) )
                self._micos_b.write('0.0 0.0 0.0 r')    # This should block further commands until the movement is finished
            try:
                statusB = int(self._micos_a.ask('st'))
            except:
                statusB = 0

        if param_dict.get(self._micos_b.label_phi) is not None:
            desired_pos = param_dict[self._micos_b.label_phi]

            if  (desired_pos > constraints[self._micos_b.label_phi]['pos_max'] ) or\
                (desired_pos < constraints[self._micos_b.label_phi]['pos_min']):

                self.log.warning('Cannot make absolute movement of the axis '
                        '"{0}" to possition {1}, since it exceeds the limts '
                        '[{2},{3}] ! Command is ignored!'.format(
                            self._micos_b.label_phi, desired_pos,
                            constraints[self._micos_b.label_phi]['pos_min'],
                            constraints[self._micos_b.label_phi]['pos_max']))
            else:
                self._micos_b.write('0.0 {:f} 0.0 move'.format(desired_pos) )
                self._micos_b.write('0.0 0.0 0.0 r')    # This should block further commands until the movement is finished
            try:
                statusB = int(self._micos_a.ask('st'))
            except:
                statusB = 0


        # ALEX COMMENT: Is there not a nicer way for that? If the axis does not
        #               reply during the movement, then it is not good to ask
        #               all the time the status. Because then the visa timeout
        #               would kill your connection to the axis.
        #               If the axis replies during movement, then think about
        #               a nicer way in waiting until the movement is done,
        #               because it will block the whole program.
        # while True:
        #     try:
        #         statusA = int(self._micos_a.ask('st'))
        #         statusB = int(self._micos_b.ask('st'))
        #     except:
        #         statusA = 0
        #         statusA = 0
        #
        #     if statusA ==0 or statusB == 0:
        #         time.sleep(0.2)
        #
        #         break
        #     time.sleep(0.2)
        # return 0



    def abort(self):
        """Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        self._micos_a.write(chr(3))
        self._micos_b.write(chr(3))
#        self._micos_a.write('abort')
#        self._micos_b.write('abort')
        self.log.warning('Movement of all the axis aborted! Stage stopped.')
        return 0

    def get_pos(self, param_list=None):
        """ Gets current position of the stage arms

        @param list param_list: optional, if a specific position of an axis
                                is desired, then the labels of the needed
                                axis should be passed as the param_list.
                                If nothing is passed, then from each axis the
                                position is asked.

        @return dict: with keys being the axis labels and item the current
                      position.
        """

        pos = {}

        # ALEX COMMENT: Is here the try statement necessary?

        try:
            if param_list is not None:
                if self._micos_a.label_x in param_list:
                    pos[self._micos_a.label_x] = float(self._micos_a.ask('pos').split()[0])

                if self._micos_a.label_y in param_list:
                    pos[self._micos_a.label_y] = float(self._micos_a.ask('pos').split()[1])

                if self._micos_b.label_z in param_list:
                    pos[self._micos_b.label_z] = float(self._micos_b.ask('pos').split()[0])

                if self._micos_b.label_phi in param_list:
                    pos[self._micos_b.label_phi] = float(self._micos_b.ask('pos').split()[1])

            else:
                xy_pos = self._micos_a.ask('pos')
                pos[self._micos_a.label_x] = float(xy_pos.split()[0])
                pos[self._micos_a.label_y] = float(xy_pos.split()[1])

                zphi_pos = self._micos_b.ask('pos')
                pos[self._micos_b.label_z] = float(zphi_pos.split()[0])
                pos[self._micos_b.label_phi] = float(zphi_pos.split()[1])

        except:
            self.log.error('Get pos routine has failed!')

        return pos

    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return dict: with the axis label as key and the status number as item.
        """

        status = {}

        # ALEX COMMENT: Is the try statement really necessary?
        #               Is is possible to get the status of each axis and not
        #                only of the stage objects _micos_a and _micos_b ?

        try:
            if param_list is not None:
                if self._micos_a.label_x in param_list:
                    status[self._micos_a.label_x] = self._micos_a.ask('st')

                if self._micos_a.label_y in param_list:
                    status[self._micos_a.label_y] = self._micos_a.ask('st')

                if self._micos_b.label_z in param_list:
                    status[self._micos_b.label_z] = self._micos_b.ask('st')

                if self._micos_b.label_phi in param_list:
                    status[self._micos_b.label_phi] = self._micos_b.ask('st')

            else:
                message_xy = self._micos_a.ask('st')
                status[self._micos_a.label_x] = message_xy
                status[self._micos_a.label_y] = message_xy

                message_zphi = self._micos_b.ask('st')
                status[self._micos_b.label_z] = message_zphi
                status[self._micos_b.label_phi] = message_zphi

        except:
            self.log.error('Get_status routine has failed!')

        return status



    def calibrate(self, param_list=None):
        """ Calibrates the stage.

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

        if param_list is not None:
            if self._micos_a.label_x in param_list:
                # self._micos_a.write('1 1 setaxis')
                # self._micos_a.write('4 2 setaxis')
                # self._micos_a.write('cal')
                self._micos_a.write('1 ncal')

            if self._micos_a.label_y in param_list:
                # self._micos_a.write('4 1 setaxis')
                # self._micos_a.write('1 2 setaxis')
                # self._micos_a.write('cal')
                self._micos_a.write('2 ncal')

            if self._micos_b.label_z in param_list:
                # self._micos_b.write('1 1 setaxis')
                # self._micos_b.write('4 2 setaxis')
                # self._micos_b.write('cal')
                self._micos_b.write('1 ncal')

            if self._micos_b.label_phi in param_list:
                # self._micos_b.write('4 1 setaxis')
                # self._micos_b.write('1 2 setaxis')
                # self._micos_b.write('cal')
                self._micos_b.write('2 ncal')

        else:

            # ALEX COMMENT: Is that a valid way of calibrating both axis at once?

            self._micos_a.write('1 1 setaxis')
            self._micos_a.write('1 2 setaxis')
            self._micos_a.write('cal')

            self._micos_b.write('1 1 setaxis')
            self._micos_b.write('1 2 setaxis')
            self._micos_b.write('cal')

    def get_velocity(self, param_list=None):
        """ Gets the current velocity for all connected axes.

        @param dict param_list: optional, if a specific velocity of an axis
                                is desired, then the labels of the needed
                                axis should be passed as the param_list.
                                If nothing is passed, then from each axis the
                                velocity is asked.

        @return dict : with the axis label as key and the velocity as item.
        """
        vel = {}

        if param_list is not None:
            if self._micos_a.label_x in param_list:
                vel[self._micos_a.label_x] = float(self._micos_a.ask('getvel').split()[0])

            if self._micos_a.label_y in param_list:
                vel[self._micos_a.label_y] = float(self._micos_a.ask('getvel').split()[1])

            if self._micos_b.label_z in param_list:
                vel[self._micos_b.label_z] = float(self._micos_b.ask('getvel').split()[0])

            if self._micos_b.label_phi in param_list:
                vel[self._micos_b.label_phi] = float(self._micos_b.ask('getvel').split()[1])

        else:
            vel_xy = self._micos_a.ask('getvel')
            vel[self._micos_a.label_x] = float(vel_xy.split()[0])
            vel[self._micos_a.label_y] = float(vel_xy.split()[1])

            vel_zphi = self._micos_b.ask('getvel')
            vel[self._micos_b.label_z] = float(vel_zphi.split()[0])
            vel[self._micos_b.label_phi] = float(vel_zphi.split()[1])

        return vel

    def set_velocity(self, param_dict):
        """ Write new value for velocity.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-velocity-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
        """
        constraints = self.get_constraints()

        if param_dict.get(self._micos_a.label_x) is not None:
            desired_vel = param_dict[self._micos_a.label_x]

            if  (desired_vel > constraints[self._micos_a.label_x]['vel_max'] ) or\
                (desired_vel < constraints[self._micos_a.label_x]['vel_min']):

                self.log.warning('Cannot make absolute movement of the axis '
                        '"{0}" to possition {1}, since it exceeds the limts '
                        '[{2},{3}] ! Command is ignored!'.format(
                            self._micos_a.label_x, desired_vel,
                            constraints[self._micos_a.label_x]['vel_min'],
                            constraints[self._micos_a.label_x]['vel_max']))
            else:
                self._micos_a.write('{:f} 0.0 0.0 sv'.format(desired_vel))

        if param_dict.get(self._micos_a.label_y) is not None:
            desired_vel = param_dict[self._micos_a.label_y]

            if  (desired_vel > constraints[self._micos_a.label_y]['vel_max'] ) or\
                (desired_vel < constraints[self._micos_a.label_y]['vel_min']):

                self.log.warning('Cannot make absolute movement of the axis '
                        '"{0}" to possition {1}, since it exceeds the limts '
                        '[{2},{3}] ! Command is ignored!'.format(
                            self._micos_a.label_y, desired_vel,
                            constraints[self._micos_a.label_y]['vel_min'],
                            constraints[self._micos_a.label_y]['vel_max']))
            else:
                self._micos_a.write('0.0 {:f} 0.0 sv'.format(desired_vel))

        if param_dict.get(self._micos_b.label_z) is not None:
            desired_vel = param_dict[self._micos_b.label_z]

            if  (desired_vel > constraints[self._micos_b.label_z]['vel_max'] ) or\
                (desired_vel < constraints[self._micos_b.label_z]['vel_min']):

                self.log.warning('Cannot make absolute movement of the axis '
                        '"{0}" to possition {1}, since it exceeds the limts '
                        '[{2},{3}] ! Command is ignored!'.format(
                            self._micos_b.label_z, desired_vel,
                            constraints[self._micos_b.label_z]['pos_min'],
                            constraints[self._micos_b.label_z]['pos_max']))
            else:
                self._micos_b.write('{:f} 0.0 0.0 sv'.format(desired_vel))

        if param_dict.get(self._micos_b.label_phi) is not None:
            desired_vel = param_dict[self._micos_b.label_phi]

            if  (desired_vel > constraints[self._micos_b.label_phi]['vel_max'] ) or\
                (desired_vel < constraints[self._micos_b.label_phi]['vel_min']):

                self.log.warning('Cannot make absolute movement of the axis '
                        '"{0}" to possition {1}, since it exceeds the limts '
                        '[{2},{3}] ! Command is ignored!'.format(
                            self._micos_b.label_phi, desired_vel,
                            constraints[self._micos_b.label_phi]['pos_min'],
                            constraints[self._micos_b.label_phi]['pos_max']))
            else:
                self._micos_b.write('0.0 {:f} 0.0 sv'.format(desired_vel))


