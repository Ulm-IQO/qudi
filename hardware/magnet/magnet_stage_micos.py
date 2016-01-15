# -*- coding: utf-8 -*-
# unstable: Jochen Scheuer

from core.base import Base
from hardware.magnet.magnet_stage_interface import MagnetStageInterface
from collections import OrderedDict

import visa
import time

class MagnetStageMicos(Base, MagnetStageInterface):
    """unstable: Jochen Scheuer. This is the hardware class to define the controls for the Micos stage of PI.
    """
    _modclass = 'MagnetStageInterface'
    _modtype = 'hardware'
    # connectors
    _out = {'magnet': 'MagnetStageInterface'}

#Questions:
#    Are values put in the right way in config????
#    change return values to sensible values??? - not so important
#    After moving files what has to be changed, where?

#Christoph:
#     make on activate method which asks for values with get_pos()
#    checks for sensible values???
#    default parameters should be none
#    introduce dead-times while waiting?
#     check if sensible value and check for float!!!! in interface
#    put together everything to one step???

#Things to be changed in logic:
#    Name of modules for steps
#    getpos
#    kill strgc method

#changes:
#    change time for waiting until next command is sent
#     change prints to log messages
#    wait in calibrate or implement get_cal
#    make subfolder with __init__ for subfolder check GUI
#    change format string to new convention

    def __init__(self, manager, name, config, **kwargs):
        cb_dict = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        Base.__init__(self, manager, name, config, cb_dict)

        self.logMsg('The following configuration was found.', 
                    msgType='status')
                    
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')
    def activation(self, e):
        self.x_store=-1
        self.y_store=-1
        self.z_store=-1
        self.phi_store=-1
 
        self.x_min=0
        self.x_max=95
        self.y_min=0
        self.y_max=95
        self.z_min=0
        self.z_max=60
        self.phi_min=0
        self.phi_max=330

        self.rm = visa.ResourceManager()
        
        # here the COM port is read from the config file
        if 'magnet_connection_micos_xy' in config.keys():
            self.MICOSA = self.rm.open_resource(config['magnet_connection_micos_xy']) # x, y
        else:
            self.MICOSA = self.rm.open_resource('COM8') # x, y
            self.logMsg('No magent_connection_micos_xy configured taking COM8 instead.', msgType='warning')
        if 'magnet_connection_micos_zphi' in config.keys():
            self.MICOSB = self.rm.open_resource(config['magent_connection_micos_zphi']) # z, phi
        else:
            self.MICOSB = self.rm.open_resource('COM5') # z, phi
            self.logMsg('No magent_connection_micos_zphi configured taking COM5 instead.', msgType='warning')

        # here the variables for the term are read in
        if 'magnet_term_chars_xy' in config.keys():
            self.MICOSA.term_chars = config['magnet_term_chars_xy']
        else:
            self.MICOSA.term_chars = '\n'
            self.logMsg('No magnet_term_chars_xy configured taking LF instead.', msgType='warning')
        if 'magnet_term_chars_zphi' in config.keys():
            self.MICOSA.term_chars = config['magnet_term_chars_zphi']
        else:
            self.MICOSB.term_chars = '\n'
            self.logMsg('No magnet_term_chars_zphi configured taking LF instead.', msgType='warning')
            
        # here the variables for the baud rate are read in
        if 'magnet_baud_rate_xy' in config.keys():
            MICOSA.baud_rate = config['magnet_baud_rate_xy']
        else:
            self.MICOSA.baud_rate = 57600
            self.logMsg('No magnet_baud_rate_xy configured, taking 57600 instead.', msgType='warning')
        if 'magnet_baud_rate_zphi' in config.keys():
            self.MICOSB.baud_rate = config['magnet_baud_rate_zphi']
        else:
            self.MICOSB.baud_rate = 57600
            self.logMsg('No magnet_baud_rate_zphi configured, taking 57600 instead.', msgType='warning')

    def deactivation(self, e):
        self.MICOSA.close()
        self.MICOSB.close()
        self.rm.close()

    def step(self, x = None, y = None, z = None, phi = None):
        """Moves stage in given direction (relative movement)
        
        @param float x: amount of realtive movement in x direction
        @param float y: amount of realtive movement in y direction
        @param float z: amount of realtive movement in z direction
        @param float phi: amount of realtive movement in phi direction
        
        @return int: error code (0:OK, -1:error)
        """
        error =0
        if x !=None:
            current_x=self.get_pos()[0]
            if (current_x+x)>self.x_max or (current_x+x)<x_min:
                self.logMsg('Magnet movement out of range in x. No movement possible', msgType='error')
                error=-1
            else:
               self.MICOSA.write('%f 0 0 r'%x)
        if y !=None:
            current_y=self.get_pos()[1]
            if (current_y+y)>self.y_max or (current_y+y)<y_min:
                self.logMsg('Magnet movement out of range in y. No movement possible', msgType='error')
                error=-1
            else:
               self.MICOSA.write('0 %f 0 r'%y)
        if z !=None:            
            current_z=self.get_pos()[2]
            if (current_z+z)>self.z_max or (current_z+z)<z_min:
                self.logMsg('Magnet movement out of range in z. No movement possible', msgType='error')
                error=-1
            else:
               self.MICOSB.write('%f 0 0 r'%z)
        if phi !=None:            
            current_phi=self.get_pos()[3]
            if (current_phi+phi)>self.phi_max or (current_phi+phi)<phi_min:
                self.logMsg('Magnet movement out of range in phi. No movement possible', msgType='error')
                error=-1
            else:
               self.MICOSB.write('0 %f 0 r'%phi)
        return error      
    
    def abort(self):
        """Stops movement of the stage
        
        @return int: error code (0:OK, -1:error)
        """
        self.MICOSA.write(chr(3))
        self.MICOSB.write(chr(3))
#   Should we use this not recommended abort or the normal abort which
#    does not stop the Stage if there is more then one command in the
#    queue
#        self.MICOSA.write('abort')
#        self.MICOSB.write('abort')
        print('stage stopped')
        return 0 
        
    def get_pos(self):
        """Gets current position of the stage arms
        
        @return float x: current x stage position
        @return float y: current y stage position
        @return float z: current z stage position
        @return float phi: current phi stage position
        """
        try:
            x = float(self.MICOSA.ask('pos').split()[0])
            y = float(self.MICOSA.ask('pos').split()[1])
            z  = float(self.MICOSB.ask('pos').split()[0])
            phi  = float(self.MICOSB.ask('pos').split()[1])  
            self.x_store = x
            self.y_store = y
            self.z_store = z
            self.phi_store = phi
        except:
            print('It was not possible to get the position of the magnet!')
            pass
        return self.x_store, self.y_store, self.z_store, self.phi_store
        
    def get_status(self):
        """Get the status of the position
        
        @return int status: status of the stage      
        """
        try:
            statusA = int(self.MICOSA.ask('st'))
            statusB = int(self.MICOSB.ask('st'))
        except:
            statusA =-1
            statusB = -1
            return (statusA,statusB)
        return 0
            
    def move(self, x = 0., y = 0., z = 0., phi = 0.):
        """Moves stage to absolute position
        
        @param float x: move to absolute position in x-direction
        @param float y: move to absolute position in y-direction
        @param float z: move to absolute position in z-direction
        @param float phi: move to absolute position in phi-direction
        
        @return int: error code (0:OK, -1:error)
        """
        MICOSA.write('%f %f 0.0 move'%(x, y))
        MICOSB.write('%f %f 0.0 move'%(z, phi))
        while True:
            try: 
                statusA = int(self.MICOSA.ask('st'))
                statusB = int(self.MICOSB.ask('st'))
            except:
                statusA = 0
                statusA = 0
            
            if statusA ==0 or statusB == 0:
                time.sleep(0.2)
                GetPos()
                break
            time.sleep(0.2)
        return 0
        
    def calibrate_x(self):
        """Calibrates the x-direction of the stage. 
        For this it moves to the point zero in x.
        
        @return int: error code (0:OK, -1:error)
        """
        self.MICOSA.write('1 1 setaxis')
        self.MICOSA.write('4 2 setaxis')
        self.MICOSA.write('cal')
        return 0
            
    def calibrate_y(self):
        """Calibrates the y-direction of the stage. 
        For this it moves to the point zero in y.
        
        @return int: error code (0:OK, -1:error)
        """
        self.MICOSA.write('4 1 setaxis')
        self.MICOSA.write('1 2 setaxis')
        self.MICOSA.write('cal')
        return 0
            
    def calibrate_z(self):
        """Calibrates the z-direction of the stage. 
        For this it moves to the point zero in z.
        
        @return int: error code (0:OK, -1:error)
        """
        self.MICOSB.write('1 1 setaxis')
        self.MICOSB.write('4 2 setaxis')
        self.MICOSB.write('cal')
        return 0
    
    def calibrate_phi(self):
        """Calibrates the phi-direction of the stage. 
        For this it turns to the point zero in phi.
        
        @return int: error code (0:OK, -1:error)
        """
        self.MICOSB.write('4 1 setaxis')
        self.MICOSB.write('1 2 setaxis')
        self.MICOSB.write('cal')
        return 0
    
    def get_velocity(self, dimension = 'x'):
        """ Gets the velocity of the given dimension
        
        @param str dimension: name of chosen dimension
        
        @return float velocity: velocity of chosen dimension
        """
        if dimension == 'x':
            vel=float(self.MICOSA.ask('getvel').split()[0])  
            print("The velocity of the magnet in dimension x and y is set on ", vel) 
        elif dimension == 'y':
            vel=float(self.MICOSA.ask('getvel').split()[0]) 
            print("The velocity of the magnet in dimension x and y is set on ", vel)   
        elif dimension == 'z':
            vel=float(self.MICOSB.ask('getvel').split()[0]) 
            print("The velocity of the magnet in dimension z and phi is set on ", vel)        
        elif dimension == 'phi':
            vel=float(self.MICOSB.ask('getvel').split()[0])
            print("The velocity of the magnet in dimension z and phi is set on ", vel)           
        return vel
        
    def set_velocity(self, dimension = 'x', vel = 0.):
        """Write new value for velocity in chosen dimension
        
        @param str dimension: name of chosen dimension
        @param float vel: velocity for chosen dimension
        
        @return int: error code (0:OK, -1:error)
        """
        if dimension == 'x':
            MICOSA.write('%f sv'%val)
        elif dimension == 'y':
            MICOSA.write('%f sv'%val)
        elif dimension == 'z':
            MICOSB.write('%f sv'%val)
        elif dimension == 'phi':
            MICOSB.write('%f sv'%val)
        return 0 
    
