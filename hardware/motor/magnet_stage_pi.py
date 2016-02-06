# -*- coding: utf-8 -*-
# unstable: Christoph Müller

from core.base import Base
from hardware.magnet.magnet_stage_interface import MagnetStageInterface
import visa


# calibrate x,y,z,    get status   und ask_rot   fehlen noch



class MagnetStagePI(Base, MagnetStageInterface):
    """unstable: Christoph Müller
    This is the Interface class to define the controls for the simple 
    microwave hardware.
    """
    
    def __init__(self, manager, name, config, **kwargs):
        cb_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, cb_dict)

        #axis definition:
        self._x_axis = '1'
        slef._y_axis = '3'
        self._z_axis = '2'
        
        #ranges of axis:
        self._min_x = -100. * 10000.
        self._max_x = 100. * 10000.
        self._min_y = -100. * 10000.
        self._max_y = 100. * 10000.
        self._min_z = -100. * 10000.
        self._max_z = 100. * 10000.
        
        #Translationfactor
        self.MicroStepSize = 0.000234375
        
        #!!!!NOTE:  vielleicht sollte überall .ask anstatt .write genommen werden, das die stage glaube ich immer was zurückgibt....
   
    def activation(self, e):
        self.rm = visa.ResourceManager()
        self._serial_connection_xyz = self.rm.open_resource('COM1', baud_rate=9600, timeout=1)            #magnet xyz-stage
        self._serial_connection_rot = self.rm.open_resource("COM6", baud_rate=9600, timeout=5)            #magnet rot-stage   TIMEOUT shorter?
        self._serial_connection_xyz.term_chars = '\n'
        self._serial_connection_rot.term_chars = '\n'
    
    def deactivation(self, e):
        self._serial_connection_xyz.close()
        self._serial_connection_rot.close()
        self.rm.close()

    def step(self, x = None, y = None, z = None, phi = None):
        """Moves stage in given direction (relative movement)
        
        @param float x: amount of realtive movement in x direction
        @param float y: amount of realtive movement in y direction
        @param float z: amount of realtive movement in z direction
        @param float phi: amount of realtive movement in phi direction
        
        @return int: error code (0:OK, -1:error)
        """
        if x != None:
            a = int(x*10000)
            current_pos = int(self._serial_connection_xyz.ask(self._x_axis+'TT')[8:])   # das gibt '1TT\n'
            move = current_pos + a
            if move > self._max_x or move < self._min_x:
                print('out of range, choose smaller step')
            else:
                self._go_to_pos(self._x_axis, move)
        if y != None:
            a = int(y*10000)
            current_pos = int(self._serial_connection_xyz.ask(self._y_axis+'TT')[8:])   # das gibt '3TT\n'
            move = current_pos + a
            if move > self._max_y or move < self._min_y:
                print('out of range, choose smaller step')
            else:
                self._go_to_pos(self._x_axis, move)
        if z != None:
            a = int(z*10000)
            current_pos = int(self._serial_connection_xyz.ask(self._z_axis+'TT')[8:])   # das gibt '2TT\n'
            move = current_pos + a
            if move > self._max_z or move < self._min_z:
                print('out of range, choose smaller step')
            else:
                self._go_to_pos(self._x_axis, move)
        if phi != None:
            self._move_relative_rot(step)
        
        return 0
       
    

    def abort(self):
        """Stops movement of the stage
        
        @return int: error code (0:OK, -1:error)
        """
        self._serial_connection_xyz.write(self._x_axis+'AB\n')
        self._serial_connection_xyz.write(self._y_axis+'AB\n')
        self._serial_connection_xyz.write(self._z_axis+'AB\n')
        self._write_rot([1,23,0])
        return 0 
        
    
    def get_pos(self):
        """Gets current position of the stage arms
        
        @return float x: current x stage position
        @return float y: current y stage position
        @return float z: current z stage position
        @return float phi: current phi stage position
        """
        x = int(self._serial_connection_xyz.ask(self._x_axis+'TT')[8:])/100000.
        y = int(self._serial_connection_xyz.ask(self._y_axis+'TT')[8:])/100000.
        z = int(self._serial_connection_xyz.ask(self._z_axis+'TT')[8:])/100000.         
        phi_temp = self._ask_rot([1,60,0])
        phi = phi_temp * self.MicroStepSize           
        return x, y, z, phi
        
     
    def get_status(self):
        """Get the status of the position
        
        @return int status: status of the stage      
        """
        raise InterfaceImplementationError('MWInterface>get_status')
        return -1
        
    
    def move(self, x = None, y = None, z = None, phi = None):
        """Moves stage to absolute position
        
        @param float x: move to absolute position in x-direction
        @param float y: move to absolute position in y-direction
        @param float z: move to absolute position in z-direction
        @param float phi: move to absolute position in phi-direction
        
        @return int: error code (0:OK, -1:error)
        """
        if x != None:
            move = int(x*10000)
            if move > self._max_x or move < self._min_x:
                print('out of range, choose smaller step')
            else:
                self._go_to_pos(self._x_axis, move)
        if y != None:
            move = int(y*10000)
            if move > self._max_y or move < self._min_y:
                print('out of range, choose smaller step')
            else:
                self._go_to_pos(self._x_axis, move)
        if z != None:
            move = int(z*10000)
            if move > self._max_z or move < self._min_z:
                print('out of range, choose smaller step')
            else:
                self._go_to_pos(self._x_axis, move)
            
        [a,b,c] = self._in_movement_xyz()
        while a != 0 or b != 0 or c != 0:
            print ('xyz-stage moving...')
            [a,b,c] = self._in_movement_xyz()
            time.sleep(0.2)
            
        if phi != None:                
            movephi = phi
            self._move_absolute_rot(movephi)
            
        print ('stage ready')
        return 0
        
        
    def calibrate_x(self):
        """Calibrates the x-direction of the stage. 
        For this it moves to the point zero in x.
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MagnetStageInterface>calibrate_x')
        return -1
            
    
    def calibrate_y(self):
        """Calibrates the y-direction of the stage. 
        For this it moves to the point zero in y.
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MagnetStageInterface>calibrate_y')
        return -1
            
    
    def calibrate_z(self):
        """Calibrates the z-direction of the stage. 
        For this it moves to the point zero in z.
        
        @return int: error code (0:OK, -1:error)
        """
        raise InterfaceImplementationError('MagnetStageInterface>calibrate_z')
        return -1
    
            
    def calibrate_phi(self):
        """Calibrates the phi-direction of the stage. 
        For this it turns to the point zero in phi.
        
        @return int: error code (0:OK, -1:error)
        
        moving the rotation stage to its home position; per default 0 degree
        """        
        self._write_rot([1,1,0])
        self._in_movement_rot()       # waits until rot_stage finished its move        
        return 0
    
    
    def get_velocity(self, dimension = 'x'):
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
            vel = data_to_speed_phi(data)
        return vel
        
        
    def set_velocity(self, dimension = 'x', vel = 0.):
        """Write new value for velocity in chosen dimension
        
        @param str dimension: name of chosen dimension
        @param float vel: velocity for chosen dimension
        
        @return int: error code (0:OK, -1:error)
        """
        if dimension == 'x':
            self._serial_connection_xyz.write(self._x_axis+'SV%i\n'%(int(vel*10000)))
        if dimension == 'y':
            self._serial_connection_xyz.write(self._y_axis+'SV%i\n'%(int(vel*10000)))
        if dimension == 'z':
            self._serial_connection_xyz.write(self._z_axis+'SV%i\n'%(int(vel*10000)))
        if dimension == 'phi':
            data = speed_to_data_phi(vel)
            self._write_rot([1,42,data])
        return 0        

    
########################## internal methods ##################################
    
    def _write_rot(self, inst):  # requires [1, commandnumber, value]
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
                z4 = int(z/base**3)   #since  int(8.9999)=8  !
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
        # return 6 bytes from the receive buffer
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
        st = self._ask_rot([1,54,0])
        while st != 0:
            print ('rotation stage moving...')
            st = self._ask_rot([1,54,0])
            time.sleep(0.1)
        print ('rotation stage stopped. ready')
        
        
    def _in_movement_xyz(self):
        '''this method checks if the magnet is still in movement and returns
        a list which of the axis are moving. Ex: return is [1,1,0]-> x and y ax are in movement and z axis is imobile.            
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
        data = int(value/self.MicroStepSize)
        self.write_rot([1,20,data])
        self._in_movement_rot()         # waits until rot_stage finished its move
    
    
    def _move_relative_rot(self, value):
        '''moves the rotation stage by a relative value in degrees'''
        data = int(value/self.MicroStepSize)
        self.write_rot([1,21,data])
        self._in_movement_rot()         # waits until rot_stage finished its move 
    
    
    def _data_to_speed_rot(self, data):
        speed = data * 9.375 * self.MicroStepSize
        return speed
        
        
    def _speed_to_data_rot(self, speed):
        data = int(speed / 9.375 / self.MicroStepSize)
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
            
    
    
    def get_status():
        """Get the status of the position"""
        try:
            x,z,y=in_movement()
            phi=get_status_phi()
            if x==0 and y==0:
                statusA=0
            else:
                statusA=1
            if z==0 and phi==0:
                statusB=0
            else:
                statusB=1
    
        except:
            statusA =-1
            statusB = -1
        return (statusA,statusB)
        
    def get_status_phi():
        ser_rot.open()
        send_rot([1,54,0])
        time.sleep(0.1)
        st = receive_rot()
        ser_rot.close()
        return st
