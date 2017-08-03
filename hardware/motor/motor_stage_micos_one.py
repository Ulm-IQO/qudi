# -*- coding: utf-8 -*-

"""
This file contains the hardware control of the motorized stage for PI Micos.

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

import visa
import time

from core.base import Base
from interface.motor_interface import MotorInterface

class MotorStageMicosOne(Base, MotorInterface):
    """unstable: Jochen Scheuer.
    Hardware class to define the controls for the Micos stage of PI.
    """
    _modclass = 'MotorStageMicosOne'
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

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))


    def on_activate(self):


        # ALEX COMMENT: Why are the values stored? In general that is not a
        #               good idea.

        self.rm = visa.ResourceManager()

        # Read HW from config
        config = self.getConfiguration()

        # here the COM port is read from the config file
        if 'com_port_micos' in config.keys():
            self._com_port, label = config['com_port_micos']
        else:
            self.log.error('No parameter "com_port_micos" found in '
                    'config.\n'
                    'Cannot connect to motorized stage! Enter the '
                    'parameter with the following scheme:/r/n'
                    '[\'<COM-PORT>\',\'<label_axis>\']')


        # here the variables for the terminal character are read in
        if 'micos_term_chars' in config.keys():
            self._term_chars = config['micos_term_chars']
        else:
            self._term_chars = '\n'
            self.log.warning('No parameter "micos_term_chars" found in '
                    'config!\nTaking LF character "\\n" instead.')

        # here the variables for the baud rate are read in
        if 'micos_baud_rate' in config.keys():
            self._baud_rate = config['micos_baud_rate']
        else:
            self._baud_rate = 57600
            self.log.warning('No parameter "micos_baud_rate" found in '
                    'config!\nTaking the baud rate {0} '
                    'instead.'.format(self._baud_rate))

        self._micos = self.rm.open_resource(self._com_port)  # x, y
        self._micos.read_termination = '\n' #self._term_chars
        self._micos.write_termination = '\n'
        self._micos.baud_rate = self._baud_rate
        self._micos.label = label     # attach a label attribute
        self._micos.write("1 setdim")

        # import logging
        # visa.logger.setLevel(logging.DEBUG)
        # ch = logging.StreamHandler()
        # ch.setLevel(logging.DEBUG)
        # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        # ch.setFormatter(formatter)
        # visa.logger.addHandler(ch)

        # try:
        #     pos_str = self._micos.ask('pos')
        #     self.pos = float(pos_str) / 1000 - 24e-3
        #
        # except visa.VisaIOError:
        #     self.log.error(visa.VisaIOERROR)
        #     self.pos = 0

        pos_str = self._micos.ask('pos')
        self.pos = float(pos_str) / 1000 - 24e-3

    def on_deactivate(self, e):
        """ Disconnect from hardware and clean up """
        self._micos.close()
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
        axis0['label'] = self._micos.label  # name is just as a sanity included
        axis0['unit'] = 'm'                 # the SI units
        axis0['ramp'] = ['Sinus','Linear']  # a possible list of ramps
        axis0['pos_min'] = -24e-3
        axis0['pos_max'] = 5e-3  # that is basically the traveling range
        axis0['scan_min'] = -10e-3
        axis0['scan_max'] = 6e-3
        axis0['pos_step'] = 1e-6
        axis0['vel_min'] = 0
        axis0['vel_max'] = 10
        axis0['vel_step'] = 0.01
        axis0['acc_min'] = 0.1
        axis0['acc_max'] = 100.0
        axis0['acc_step'] = 0.0

        # assign the parameter container for x to a name which will identify it
        constraints[axis0['label']] = axis0

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

        if param_dict.get(self._micos.label) is not None:
            move_x = param_dict[self._micos.label]
            curr_pos_x = curr_pos_dict[self._micos.label]
            if(curr_pos_x + move_x > constraints[self._micos.label]['pos_max']) or\
                (curr_pos_x + move_x < constraints[self._micos.label]['pos_min']):
                self.log.warning('Cannot make further movement of the axis '
                        '"{0}" with the step {1}, since the border [{2},{3}] '
                        'was reached! Ignore command!'.format(
                            self._micos.label, move_x,
                            constraints[self._micos.label]['pos_min'],
                            constraints[self._micos.label]['pos_max']))
            else:
                move_x = move_x *1000
                self._micos.write('{0:f} r'.format(move_x))  # r is command to move relative

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
        #               axis, i.e. _micos and _micos_b only once, and then
        #               wait until they are finished.
        #               You have either to restructure the axis call and find
        #               out how to block any signal until the stage is not
        #               finished with the movement. Maybe you have also to
        #               increase the visa timeout number, because if the device
        #               increase the visa timeout number, because if the device
        #               does not react on a command after the timeout an error
        #               will be raised by the visa protocol itself!

        if param_dict.get(self._micos.label) is not None:
            desired_pos = param_dict[self._micos.label]
            constr = constraints[self._micos.label]

            if not(constr['pos_min'] <= desired_pos <= constr['pos_max']):
                self.log.warning('Cannot make absolute movement of the axis '
                    '"{0}" to position {1}, since it exceeds the limits '
                    '[{2},{3}] ! Command is ignored!'
                    ''.format(self._micos.label, desired_pos,
                         constr['pos_min'], constr['pos_max']))
            else:
                desired_pos = (desired_pos +24e-3)*1000
                self._micos.write('{0:f} move'.format(desired_pos))
                self._micos.write('0.0 r')    # This should block further commands until the movement is finished
            try:
                status = int(self._micos.ask('st'))
            except:
                status = 0


        # ALEX COMMENT: Is there not a nicer way for that? If the axis does not
        #               reply during the movement, then it is not good to ask
        #               all the time the status. Because then the visa timeout
        #               would kill your connection to the axis.
        #               If the axis replies during movement, then think about
        #               a nicer way in waiting until the movement is done,
        #               because it will block the whole program.
        # while True:
        #     try:
        #         statusA = int(self._micos.ask('st'))
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
        self._micos.write(chr(3))
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
        try:
            pos_str = self._micos.query('pos')
            self.pos = float(pos_str) / 1000 - 24e-3

        except visa.VisaIOError:
            self.log.error(visa.VisaIOError)

        pos[self._micos.label] = self.pos

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
        status[self._micos.label] = self._micos.ask('st')

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

        self._micos.write('1 setdim')
        self._micos.write('cal') # takes too long... TODO wait for movement to finish


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
        vel[self._micos.label] = float(self._micos.ask('getvel'))/1000
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

        desired_vel = param_dict[self._micos.label]
        constr = constraints[self._micos.label]

        if not(constr['vel_min'] <= desired_vel <= constr['vel_max']):
            self.log.warning('Cannot make absolute movement of the axis '
                    '"{0}" to possition {1}, since it exceeds the limts '
                    '[{2},{3}] ! Command is ignored!'.format(
                        self._micos.label, desired_vel,
                        constr['vel_min'],
                        constr['vel_max']))
        else:
            desired_vel = desired_vel *1000
            self.log.info('{0:f} sv'.format(desired_vel))
            self._micos.write('{0:f} sv'.format(desired_vel))




