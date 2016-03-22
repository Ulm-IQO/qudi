# -*- coding: utf-8 -*-

"""
This file contains the hardware control of the motorized stage for PI.

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

Copyright (C) 2015 Christoph Mueller christoph-1.mueller@uni-ulm.de
Copyright (C) 2016 Alexander Stark alexander.stark@uni-ulm.de
"""

import visa
import time

from core.base import Base
from interface.motor_interface import MotorInterface

class MotorStagePI(Base, MotorInterface):
    """unstable: Christoph Müller
    This is the Interface class to define the controls for the simple
    microwave hardware.
    """
    _modclass = 'MotorStagePI'
    _modtype = 'hardware'
    # connectors
    _out = {'magnet': 'MotorInterface'}

    def __init__(self, manager, name, config, **kwargs):
        cb_dict = {'onactivate': self.activation,
                   'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, cb_dict)

        #axis definition:
        self._x_axis = '1'
        self._y_axis = '3'
        self._z_axis = '2'        

        #!!!!NOTE:  vielleicht sollte überall .ask anstatt .write genommen werden, das die stage glaube ich immer was zurückgibt....


    def activation(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """
        # Read configs from config-file
        config = self.getConfiguration()
        
        # get the right com-ports from config
        if 'com_port_pi_xyz' in config.keys():
            self._com_port_pi_xyz = config['com_port_pi_xyz']
        else:
            self.logMsg('No parameter "com_port_pi_xyz" found in config.\n'
                        'Cannot connect to motorized stage!',
                        msgType='error')
        if 'com_port_rot' in config.keys():
            self._com_port_rot = config['com_port_rot']
        else:
            self.logMsg('No parameter "com_port_rot" found in config.\n'
                        'Cannot connect to motorized stage!',
                        msgType='error')
                        
        # get the the right baud rates from config
        if 'pi_xyz_baud_rate' in config.keys():
            self._pi_xyz_baud_rate = config['pi_xyz_baud_rate']
        else:
            self._pi_xyz_baud_rate = 9600
            self.logMsg('No parameter "pi_xyz_baud_rate" found in config!\n'
                        'Taking the baud rate {0} '
                        'instead.'.format(self._pi_xyz_baud_rate),
                        msgType='warning')
        if 'rot_baud_rate' in config.keys():
            self._rot_baud_rate = config['rot_baud_rate']
        else:
            self._rot_baud_rate = 9600
            self.logMsg('No parameter "rot_baud_rate" found in config!\n'
                        'Taking the baud rate {0} '
                        'instead.'.format(self._rot_baud_rate),
                        msgType='warning')
                        
        # get the the right timeouts from config
        if 'pi_xyz_timeout' in config.keys():
            self._pi_xyz_timeout = config['pi_xyz_timeout']
        else:
            self._pi_xyz_timeout = 1000    # timeouts are given in millisecond in new pyvisa version
            self.logMsg('No parameter "pi_xyz_timeout" found in config!\n'
                        'Setting the timeout to {0} '
                        'instead.'.format(self._pi_xyz_timeout),
                        msgType='warning')
        if 'rot_timeout' in config.keys():
            self._rot_timeout = config['rot_timeout']
        else:
            self._rot_timeout = 5000     #TIMEOUT shorter?
            self.logMsg('No parameter "rot_timeout" found in config!\n'
                        'Setting the timeout to {0} '
                        'instead.'.format(self._rot_timeout),
                        msgType='warning')
                        
        # get the the right term_chars from config
        if 'pi_xyz_timeout' in config.keys():
            self._pi_xyz_term_char = config['pi_xyz_term_char']
        else:
            self._pi_xyz_term_char = '\n'
            self.logMsg('No parameter "pi_xyz_term_char" found in config!\n'
                        'Taking the term_char {0} '
                        'instead.'.format(self._pi_xyz_term_char),
                        msgType='warning')
        if 'rot_term_char' in config.keys():
            self._rot_term_char = config['rot_term_char']
        else:
            self._rot_term_char = '\n'     #TIMEOUT shorter?
            self.logMsg('No parameter "rot_term_char" found in config!\n'
                        'Taking the term_char {0} '
                        'instead.'.format(self._rot_term_char),
                        msgType='warning')        
        
        self.rm = visa.ResourceManager()
        self._serial_connection_xyz = self.rm.open_resource(self._com_port_pi_xyz, self._pi_xyz_baud_rate, self._pi_xyz_timeout)
        self._serial_connection_rot = self.rm.open_resource(self._com_port_rot, self._rot_baud_rate, self._rot_timeout)
        self._serial_connection_xyz.term_chars = self._pi_xyz_term_char
        self._serial_connection_rot.term_chars = self._rot_term_char

        # setting the ranges of the axes - factor 10000. needed to have everything in millimeters
        if 'pi_x_min' in config.keys():
            self._min_x = config['pi_x_min'] * 10000. 
        else:
            self._min_x = -100. * 10000.
            self.logMsg('No parameter "pi_x_min" found in config!\n'
                        'Taking -100mm instead.',
                        msgType='warning')
        if 'pi_x_max' in config.keys():
            self._max_x = config['pi_x_max'] * 10000.
        else:
            self._max_x = 100. * 10000.
            self.logMsg('No parameter "pi_x_max" found in config!\n'
                        'Taking 100mm instead.',
                        msgType='warning')
        if 'pi_y_min' in config.keys():
            self._min_y = config['pi_y_min'] * 10000.
        else:
            self._min_y = -100. * 10000.
            self.logMsg('No parameter "pi_y_min" found in config!\n'
                        'Taking -100mm instead.',
                        msgType='warning')
        if 'pi_y_max' in config.keys():
            self._max_y = config['pi_y_max'] * 10000.
        else:
            self._max_y = 100. * 10000.
            self.logMsg('No parameter "pi_y_max" found in config!\n'
                        'Taking 100mm instead.',
                        msgType='warning')
        if 'pi_z_min' in config.keys():
            self._min_z = config['pi_z_min'] * 10000.
        else:
            self._min_z = -100. * 10000.
            self.logMsg('No parameter "pi_z_min" found in config!\n'
                        'Taking -100mm instead.',
                        msgType='warning')
        if 'pi_z_max' in config.keys():
            self._max_z = config['pi_z_max'] * 10000.
        else:
            self._max_z = 100. * 10000.
            self.logMsg('No parameter "pi_z_max" found in config!\n'
                        'Taking 100mm instead.',
                        msgType='warning')
                        
        # get the MicroStepSize value for the rotation stage
        if 'rot_microstepsize' in config.keys():
            self._MicroStepSize = config['rot_microstepsize']
        else:
            self._MicroStepSize = 0.000234375
            self.logMsg('No parameter "rot_microstepsize" found in config!\n'
                        'Taking the MicroStepSize {0} '
                        'instead.'.format(self._MicroStepSize),
                        msgType='warning') 
                        

    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        self._serial_connection_xyz.close()
        self._serial_connection_rot.close()
        self.rm.close()


    def move_rel(self, param_dict):
        """Moves stage in given direction (relative movement)
        
        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-abs-pos-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
                                The values for the axes are in millimeter,
                                the value for the rotation is in degrees.

        @return int: error code (0:OK, -1:error)
        """
        try:
            if 'x' in param_dict:
                a = int(param_dict['x']*10000)
                current_pos = int(self._serial_connection_xyz.ask(self._x_axis+'TT')[8:])   # '1TT\n'
                move = current_pos + a
                if move > self._max_x or move < self._min_x:
                    self.logMsg('x out of range, choose smaller step',
                                msgType='warning')
                else:
                    self._go_to_pos(self._x_axis, move)                
            if 'y' in param_dict:
                a = int(param_dict['y']*10000)
                current_pos = int(self._serial_connection_xyz.ask(self._y_axis+'TT')[8:])   # '3TT\n'
                move = current_pos + a
                if move > self._max_y or move < self._min_y:
                    self.logMsg('y out of range, choose smaller step',
                                msgType='warning')
                else:
                    self._go_to_pos(self._x_axis, move)                
            if 'z' in param_dict:
                a = int(param_dict['z']*10000)
                current_pos = int(self._serial_connection_xyz.ask(self._z_axis+'TT')[8:])   # '2TT\n'
                move = current_pos + a
                if move > self._max_z or move < self._min_z:
                    self.logMsg('z out of range, choose smaller step',
                                msgType='warning')
                else:
                    self._go_to_pos(self._x_axis, move)                
            if 'phi' in param_dict:
                movephi = param_dict['phi']
                self._move_relative_rot(movephi)
            return 0
        except:
            return -1


    def move_abs(self, param_dict):
        """Moves stage to absolute position
        
        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-abs-pos-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
                                The values for the axes are in millimeter,
                                the value for the rotation is in degrees.

        @return int: error code (0:OK, -1:error)
        """
        try:
            if 'x' in param_dict:
                move = int(param_dict['x']*10000)
                if move > self._max_x or move < self._min_x:
                    self.logMsg('x out of range, choose smaller step',
                                msgType='warning')
                else:
                    self._go_to_pos(self._x_axis, move)
            if 'y' in param_dict:
                move = int(param_dict['y']*10000)
                if move > self._max_y or move < self._min_y:
                    self.logMsg('y out of range, choose smaller step',
                                msgType='warning')
                else:
                    self._go_to_pos(self._x_axis, move)
            if 'z' in param_dict:
                move = int(param_dict['z']*10000)
                if move > self._max_z or move < self._min_z:
                    self.logMsg('z out of range, choose smaller step',
                                msgType='warning')
                else:
                    self._go_to_pos(self._x_axis, move)
    
            [a,b,c] = self._in_movement_xyz()
            while a != 0 or b != 0 or c != 0:
                print ('xyz-stage moving...')
                [a,b,c] = self._in_movement_xyz()
                time.sleep(0.2)
    
            if 'phi' in param_dict:
                movephi = param_dict['phi']
                self._move_absolute_rot(movephi)
    
            print ('stage ready')
            return 0
        except:
            return -1


    def abort(self):
        """Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        try:
            self._serial_connection_xyz.write(self._x_axis+'AB\n')
            self._serial_connection_xyz.write(self._y_axis+'AB\n')
            self._serial_connection_xyz.write(self._z_axis+'AB\n')
            self._write_rot([1,23,0])  # abortion command for the rot stage
            return 0
        except:
            return -1


    def get_pos(self, param_list=None):
        """ Gets current position of the stage arms

        @param list param_list: optional, if a specific position of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                position is asked.

        @return dict: with keys being the axis labels and item the current
                      position.
        """
        param_dict = {}
        try:
            if param_list != None and 'x' in param_list or param_list==None:
                x_value = int(self._serial_connection_xyz.ask(self._x_axis+'TT')[8:])/100000.
                param_dict['x'] = x_value
            if param_list != None and 'y' in param_list or param_list==None:
                y_value = int(self._serial_connection_xyz.ask(self._y_axis+'TT')[8:])/100000.
                param_dict['y'] = y_value
            if param_list != None and 'z' in param_list or param_list==None:
                z_value = int(self._serial_connection_xyz.ask(self._z_axis+'TT')[8:])/100000.
                param_dict['z'] = z_value
            if param_list != None and 'phi' in param_list or param_list==None:
                phi_temp = self._ask_rot([1,60,0])
                phi_value = phi_temp * self._MicroStepSize
                param_dict['phi'] = phi_value
            return param_dict
        except:
            return -1


    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return dict: with the axis label as key and the status number as item.
        """
        param_dict = {}
        try:
            if param_list != None and 'x' in param_list or param_list==None:
                x_status = self._serial_connection_xyz.ask(self._x_axis+'TS')[8:]
                time.sleep(0.1)
                param_dict['x'] = x_status
            if param_list != None and 'y' in param_list or param_list==None:
                y_status = self._serial_connection_xyz.ask(self._y_axis+'TS')[8:]
                time.sleep(0.1)
                param_dict['y'] = y_status
            if param_list != None and 'z' in param_list or param_list==None:
                z_status = self._serial_connection_xyz.ask(self._z_axis+'TS')[8:]
                time.sleep(0.1)
                param_dict['z'] = z_status
            if param_list != None and 'phi' in param_list or param_list==None:
                phi_status = self._ask_rot([1,54,0])
                param_dict['phi'] = phi_status
            return param_dict
        except:
            return -1
            
               




    def calibrate(self, param_list=None):
        """ Calibrates the stage.

        @param dict param_list: param_list: optional, if a specific calibration
                                of an axis is desired, then the labels of the
                                needed axis should be passed in the param_list.
                                If nothing is passed, then all connected axis
                                will be calibrated.

        @return int: error code (0:OK, -1:error)

        After calibration the stage moves to home position which will be the
        zero point for the passed axis. 
        """


    def calibrate_phi(self):
        """Calibrates the phi-direction of the stage.
        For this it turns to the point zero in phi.

        @return int: error code (0:OK, -1:error)

        moving the rotation stage to its home position; per default 0 degree
        """
        self._write_rot([1,1,0])      # moves the rot stage to its home position
        self._in_movement_rot()       # waits until rot_stage finished its move
        return 0


    def get_velocity(self, dimension=None):
        """ Gets the velocity of the given dimension

        @param str dimension: name of chosen dimension

        @return float velocity: velocity of chosen dimension
        """
        """Get the velocity of x and y"""
        if dimension == 'x':
            vel = int(self._serial_connection_xyz.ask(self._x_axis+'TY')[8:])/100000.
        elif dimension == 'y':
            vel = int(self._serial_connection_xyz.ask(self._y_axis+'TY')[8:])/100000.
        elif dimension == 'z':
            vel = int(self._serial_connection_xyz.ask(self._z_axis+'TY')[8:])/100000.
        elif dimension == 'phi':
            data = self._ask_rot([1,53,42])
            vel = self._data_to_speed_rot(data)
        else:
            return -1
        return vel


    def set_velocity(self, dimension=None, vel=None):
        """Write new value for velocity in chosen dimension

        @param str dimension: name of chosen dimension
        @param float vel: velocity for chosen dimension

        @return int: error code (0:OK, -1:error)
        """
        if vel != None:
            if dimension == 'x':
                self._serial_connection_xyz.write(self._x_axis+'SV%i\n'%(int(vel*10000)))
            elif dimension == 'y':
                self._serial_connection_xyz.write(self._y_axis+'SV%i\n'%(int(vel*10000)))
            elif dimension == 'z':
                self._serial_connection_xyz.write(self._z_axis+'SV%i\n'%(int(vel*10000)))
            elif dimension == 'phi':
                data = self._speed_to_data_rot(vel)
                self._write_rot([1,42,data])
            else:
                return -1
            return 0
        else:
            return -1


########################## internal methods ##################################

    def _write_rot(self, inst):
        ''' sending a command to the rotation stage,
        requires [1, commandnumber, value]'''
        x = inst[0]
        y = inst[1]
        z = inst[2]
        z4 = 0
        z3 = 0
        z2 = 0
        z1 = 0
        base = 256

        if z >= 0:
            if z/base**3 >= 1:
                z4 = int(z/base**3)   #since  int(8.9999)=8
                z -= z4*base**3
            if z/base**2 >= 1:
                z3 = int(z/base**2)
                z -= z3*base**2
            if z/base >= 1:
                z2 = int(z/base)
                z -= z2*base
            z1 = z
        else:
            z4 = 255
            z += base**3
            if z/base**2 >= 1:
                z3 =int(z/base**2)
                z -= z3*base**2
            if z/base >= 1:
                z2 = int(z/base)
                z -= z2*base
            z1 = z

        sends = [x,y,z1,z2,z3,z4]
            # send instruction
            # inst must be a list of 6 bytes (no error checking)
        for i in range (6):
            self._serial_connection_rot.write(chr(sends[i]))
        return


    def _ask_rot(self):
        '''receiving an answer from the rotation stage'''
        # returns 6 bytes from the receive buffer
        # there must be 6 bytes to receive (no error checking)
        r = [0,0,0,0,0,0]
        for i in range (6):
            r[i] = ord(ser_rot.read(1))
        #x=r[0]
        y = r[1]
        z1 = r[2]
        z2 = r[3]
        z3 = r[4]
        z4 = r[5]
        q = z1+z2*256+z3*256**2+z4*256**3

        if y == 255:
            print(('error nr. ' + str(q)))
        return q


    def _in_movement_rot(self):
        '''checks if the rotation stage is still moving'''
        st = self._ask_rot([1,54,0])
        while st != 0:
            print ('rotation stage moving...')
            st = self._ask_rot([1,54,0])
            time.sleep(0.1)
        print ('rotation stage stopped. ready')


    def _in_movement_xyz(self):
        '''this method checks if the magnet is still moving and returns
        a list which of the axis are moving. Ex: return is [1,1,0]-> x and y ax are moving and z axis is imobile.
        '''
        tmpx = self._serial_connection_xyz.ask(self._x_axis+'TS')[8:]
        time.sleep(0.1)
        tmpy = self._serial_connection_xyz.ask(self._y_axis+'TS')[8:]
        time.sleep(0.1)
        tmpz = self._serial_connection_xyz.ask(self._z_axis+'TS')[8:]
        time.sleep(0.1)
        return [tmpx%2,tmpy%2,tmpz%2]
        del tmpx,tmpy,tmpz


    def _move_absolute_rot(self, value):
        '''moves the rotation stage to an absolut position; value in degrees'''
        data = int(value/self._MicroStepSize)
        self._write_rot([1,20,data])
        self._in_movement_rot()         # waits until rot_stage finished its move


    def _move_relative_rot(self, value):
        '''moves the rotation stage by a relative value in degrees'''
        data = int(value/self._MicroStepSize)
        self._write_rot([1,21,data])
        self._in_movement_rot()         # waits until rot_stage finished its move


    def _data_to_speed_rot(self, data):
        speed = data * 9.375 * self._MicroStepSize
        return speed


    def _speed_to_data_rot(self, speed):
        data = int(speed / 9.375 / self._MicroStepSize)
        return data

    def _go_to_pos(self, axis = None, move = None):
        """moves one axis to an absolute position

        @param string axis: ID of the axis, '1', '2' or '3'
        @param int move: absolute position
        """
        self._serial_connection_xyz.write(self._x_axis+'SP%s'%move)
        self._serial_connection_xyz.write(self._x_axis+'MP')




##################################################################################################################################################
##################################################################################################################################################
##################################################################################################################################################


    def CalibrateXYZ():
        test_open()
        ser.write('123MA-2500000\n')
        time.sleep(1)
        ser.close()

        [a,b,c] = in_movement()
        while a != 0 or b != 0 or c !=0 :
            print('moving to the corner...')
            [a,b,c] = in_movement()
            print('moving on x-Axis: ', a)
            print('moving on y-Axis: ', b)
            print('moving on z-Axis: ', c,'\n')
            time.sleep(0.5)
        ##############################################
        print('in edge')
        test_open()
        ser.write('123DH\n')
        ser.write('123MA900000\n')
        time.sleep(.1)
        print(str(ser.read(17)))
        print('define the tmps')
        ser.close()
        ###############################################
        [a,b,c] = in_movement()
        while a != 0 or b != 0 or c != 0:
            print('moving next to the centerposition...')
            [a,b,c] = in_movement()
            print('moving on x-Axis: ', a)
            print('moving on y-Axis: ', b)
            print('moving on z-Axis: ', c,'\n')
            time.sleep(.5)
        ####################################################
        print('fast movement finished')

        time.sleep(0.1)
        test_open()
        ser.write('13FE1\n')
        print(ser.read(6))
        ser.close()
        [a,b,c] = in_movement()
        while a != 0 or b != 0 or c != 0:
            print('find centerposition...')
            [a,b,c] = in_movement()
            print('moving on x-Axis: ', a)
            print('moving on y-Axis: ', b)
            print('moving on z-Axis: ', c,'\n')
            time.sleep(.5)
        test_open()
        ser.write('123DH\n')
        ser.close()
        del [a,b,c]
        #######################################################
        print('calibration finished')
        GetPos()
