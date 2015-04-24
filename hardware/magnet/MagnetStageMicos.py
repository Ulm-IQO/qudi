# -*- coding: utf-8 -*-
# unstable: Jochen Scheuer

from core.Base import Base
from hardware.MagnetStageInterface import MagnetStageInterface
from collections import OrderedDict

from visa import instrument
import time

class MagnetStageMicos(Base,MagnetStageInterface):
    """unstable: Jochen Scheuer. This is the hardware class to define the controls for the Micos stage of PI.
    """

# 	Creating class variables to store the current value of the position.
	x_store=-1
	y_store=-1
	z_store=-1
	phi_store=-1

#Questions:
#	Are values put in the right way in config????
#	change return values to sensible values??? - not so important
#	After moving files what has to be changed, where?

#Christoph:
# 	make on activate method which asks for values with get_pos()
#	checks for sensible values???
#	default parameters should be none
#	introduce dead-times while waiting?
# 	check if sensible value and check for float!!!! in interface
#	put together everything to one step???


#Things to be changed in logic:
#	Name of modules for steps
#	getpos
#	kill strgc method

#changes:
#	change time for waiting until next command is sent
# 	change prints to log messages
#	wait in calibrate or implement get_cal
#	make subfolder with __init__ for subfolder check GUI
#	change format string to new convention

    def __init__(self, manager, name, config, **kwargs):
        Base.__init__(self, manager, name, configuation=config)
        self._modclass = 'magnetinterface'
        self._modtype = 'hardware'

        self.connector['out']['magnet'] = OrderedDict()
        self.connector['out']['magnet']['class'] = 'magnetinterface'
        
        self.logMsg('The following configuration was found.', 
                    msgType='status')
                    
        # checking for the right configuration
        for key in config.keys():
            self.logMsg('{}: {}'.format(key,config[key]), 
                        msgType='status')

#		here the COM port is read from the config file
        if 'magnet_connection_micos_xy' in config.keys():
			MICOSA = instrument(config['magnet_connection_micos_xy']) # x, y
		else:
			MICOSA = instrument('COM8') # x, y
            self.logMsg('No magent_connection_micos_xy configured taking COM8 instead.', \
            msgType='warning')
		if 'magnet_connection_micos_zphi' in config.keys():		 
			MICOSB = instrument(config['magent_connection_micos_zphi']) # z, phi
		else:
			MICOSB = instrument('COM5') # z, phi
            self.logMsg('No magent_connection_micos_zphi configured taking COM5 instead.', \
            msgType='warning')

#		here the variables for the term are read in
        if 'magnet_term_chars_xy' in config.keys():
			MICOSA.term_chars = config['magnet_term_chars_xy']
		else:
			MICOSA.term_chars = '\n'
            self.logMsg('No magnet_term_chars_xy configured taking '\\n' instead.', \
            msgType='warning')
        if 'magnet_term_chars_zphi' in config.keys():
			MICOSA.term_chars = config['magnet_term_chars_zphi']
		else:
			MICOSB.term_chars = '\n'
            self.logMsg('No magnet_term_chars_zphi configured taking '\\n' instead.', \
            msgType='warning')

#		here the variables for the baud rate are read in
        if 'magnet_baud_rate_xy' in config.keys():
			MICOSA.baud_rate = config['magnet_baud_rate_xy']
		else:
			MICOSA.baud_rate = 57600
            self.logMsg('No magnet_baud_rate_xy configured taking '57600' instead.', \
            msgType='warning')
        if 'magnet_baud_rate_zphi' in config.keys():
			MICOSB.baud_rate = config['magnet_baud_rate_zphi']
		else:
			MICOSB.baud_rate = 57600
            self.logMsg('No magnet_baud_rate_zphi configured taking '57600' instead.', \
            msgType='warning')

            
    def step_x(self, step = 0.):
        """Moves stage in x-direction
        
        @param float step: amount of realtive movement
        
        @return int: error code (0:OK, -1:error)
        """
		MICOSA.write('%f 0 0 r'%step)
        return 0
    
    
    def step_y(self, step = 0.):
        """Moves stage in y-direction
        
        @param float step: amount of realtive movement
        
        @return int: error code (0:OK, -1:error)
        """
#		command is wrong same as step_y
    	MICOSA.write('%f 0 0 r'%step)
        return 0
    
    
    def step_z(self, step = 0.):
        """Moves stage in z-direction
        
        @param float step: amount of realtive movement
        
        @return int: error code (0:OK, -1:error)
        """
    	MICOSB.write('%f 0 0 r'%step)
        return 0
        
    
    def step_phi(self, step = 0.):
        """Turns stage around angle phi
        
        @param float step: amount of realtive movement
        
        @return int: error code (0:OK, -1:error)
        """
    	MICOSB.write('0 %f 0 r'%a)
        return 0         
    

    def abort(self):
        """Stops movement of the stage
        
        @return int: error code (0:OK, -1:error)
        """
    	MICOSA.write(chr(3))
    	MICOSB.write(chr(3))
#	Should we use this not recommended abort or the normal abort which
#	does not stop the Stage if there is more then one command in the
#	queue
#    	MICOSA.write('abort')
#    	MICOSB.write('abort')
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
            x = float(MICOSA.ask('pos').split()[0])
            y = float(MICOSA.ask('pos').split()[1])
       	    z  = float(MICOSB.ask('pos').split()[0])
       	    phi  = float(MICOSB.ask('pos').split()[1])  
        	self.x_store = x
        	self.y_store = y
        	self.z_store = z
        	self.phi_store = phi
    	except:
        	print 'It was not possible to get the position of the magnet!'
        	pass
    	return self.x_store, self.y_store, self.z_store, self.phi_store
        
     
    def get_status(self):
        """Get the status of the position
        
        @return int status: status of the stage      
        """
		try:
		    statusA = int(MICOSA.ask('st'))
		    statusB = int(MICOSB.ask('st'))
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
		        statusA = int(MICOSA.ask('st'))
		        statusB = int(MICOSB.ask('st'))
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
		MICOSA.write('1 1 setaxis')
		MICOSA.write('4 2 setaxis')
		MICOSA.write('cal')
        return 0
            
    
    def calibrate_y(self):
        """Calibrates the y-direction of the stage. 
        For this it moves to the point zero in y.
        
        @return int: error code (0:OK, -1:error)
        """
		MICOSA.write('4 1 setaxis')
		MICOSA.write('1 2 setaxis')
		MICOSA.write('cal')
        return 0
            
    
    def calibrate_z(self):
        """Calibrates the z-direction of the stage. 
        For this it moves to the point zero in z.
        
        @return int: error code (0:OK, -1:error)
        """
		MICOSB.write('1 1 setaxis')
		MICOSB.write('4 2 setaxis')
		MICOSB.write('cal')
        return 0
    
            
    def calibrate_phi(self):
        """Calibrates the phi-direction of the stage. 
        For this it turns to the point zero in phi.
        
        @return int: error code (0:OK, -1:error)
        """
		MICOSB.write('4 1 setaxis')
		MICOSB.write('1 2 setaxis')
		MICOSB.write('cal')
        return 0
    
    
    def get_velocity(self, dimension = 'x'):
        """ Gets the velocity of the given dimension
        
        @param str dimension: name of chosen dimension
        
        @return float velocity: velocity of chosen dimension
        """
        if dimension == 'x':
        	vel=float(MICOSA.ask('getvel').split()[0])  
			print("The velocity of the magnet in dimension x and y is set on ",vel) 
        elif dimension == 'y':
        	vel=float(MICOSA.ask('getvel').split()[0]) 
			print("The velocity of the magnet in dimension x and y is set on ",vel)   
        elif dimension == 'z':
    		vel=float(MICOSB.ask('getvel').split()[0]) 
			print("The velocity of the magnet in dimension z and phi is set on ",vel)        
        elif dimension == 'phi':
    		vel=float(MICOSB.ask('getvel').split()[0])
			print("The velocity of the magnet in dimension z and phi is set on ",vel)           
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
    
    
    
