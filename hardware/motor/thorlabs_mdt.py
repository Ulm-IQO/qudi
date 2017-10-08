import serial
import sys
import re
from numpy import arange
from time import sleep


# Set default port (COM6 for windows locally with USB converter)
# if sys.platform.startswith('win'):
#     DEFAULT_PORT = 'COM6'
# else:
#     DEFAULT_PORT = '/dev/ttyUSB0'
import logging

class PiezoController(serial.Serial):
    '''
    Python class for controlling voltages to 3-axis ThorLabs MDT693A
    '''
    
    # Note 75V is the maximum voltage the Nanomax can handle!
    def __init__(self, MAX_VOLTAGE = 75.0, port='COM4', baudrate=115200):
        
        self.MAX_VOLTAGE = MAX_VOLTAGE
        
        # Initialise the class using super class of (py)serial
        self.serial.Serial(self, port, baudrate)
        
        # Initialise the class x,y,z axes
        for axis in ['x', 'y', 'z']:
            self.get_voltage(axis)
        
        # Close any open connections and open a serial connection
        # self.close()
        # self.open()
    
    def cmd(self, command, verbose = False):
        '''
        Send a command to the MDT693A
        '''
        self.write( (str(command)+'\r').encode('utf-8'))
        # Have a timeout so that writing successive strings does not interrupt
        # the last command
        if verbose:
            print ('did command:', str(command))
        sleep(0.03)
    
    def response(self):
        '''
        Get response and convert to a float if there's a match
        '''
        resp = self.read()
        if resp == b'':
            return
        
        # Loop until we hit the end line character
        while resp[-1] != '\r':
            r = self.read()
            resp = resp + r
            if r == b'':
                break
        
        # Search the response to extract the number
        match = re.search('\[(.*)\]', str(resp))
        if match:
            # If the match has square brackets then we convert this to a float
            result = float(match.group(1))
            return result
        else:
            return
    
    def get_voltage(self, axis):
        '''
        get the voltage for the x,y,z axes
        --------
        axis - (str) x y or z axis to set the voltage        
        '''
        if axis not in ["x", "y", "z"]:
            self.close_connection()
            self.logging.error("%s axis is not in (x,y,z)" % axis)
        self.cmd("{}voltage?".format(axis))
        voltage = self.response()
        setattr(self, axis, voltage)
        return voltage
    
    def set_voltage(self, axis, voltage, step=2.5):
        '''
        set the voltage on the piezo controller
        #=======================================================================
        # PLEASE USE Z-AXIS WITH CAUTION WHEN THE VGA IS NEAR THE SURFACE OF THE
        # CHIP
        #=======================================================================
        ---------
        axis - (str) x y or z axis to set the voltage
        voltage - (float) voltage to set on the piezo controller
        '''
        if axis not in ["x", "y", "z"]:
            self.close_connection()
            self.logging.error("%s axis is not in (x,y,z)" % axis)
        if not 0.0 <= voltage <= self.MAX_VOLTAGE:
            self.close_connection()
            self.logging.error("The current voltage (%s V) must be between 0V and %s V" % (voltage, self.MAX_VOLTAGE))
        if step > 5.0:
            self.logging.error('Step size %s V must be less than %s V'%(voltage, step))
        
        # Break down into smaller steps if the change is too large
        current_voltage = getattr(self, axis)

        if abs(current_voltage - voltage) > step:
            if (current_voltage - voltage) < 0:
                intermediate = arange(current_voltage, voltage, step)
            else:
                intermediate = arange(voltage, current_voltage, step)[::-1]
            
            for i in intermediate:
                self.cmd("{}v0{}".format(axis, i))
#                 sleep(0.03)
            
        
        # This is the string that we send over serial to MDT693A
        self.cmd("{}v0{}".format(axis, voltage))
        setattr(self, axis, voltage)
    
    
    def jog(self, axis, voltage_increment):
        '''
        Increment/decrement the voltages on a given axis by a voltage
        --------
        axis - (str) x y or z axis to set the voltage
        voltage - (float) voltage to set on the piezo controller
        '''
        if axis not in ["x", "y", "z"]:
            self.close_connection()
            raise RuntimeError("%s axis is not in (x,y,z)" % axis)
        
        v = pc.get_voltage(axis)
        new_voltage = v + voltage_increment
        
        if not 0.0 <= new_voltage <= self.MAX_VOLTAGE:
            self.close_connection()
            raise RuntimeError("The current voltage (%s V) must be between 0V and %s V" % (new_voltage, self.MAX_VOLTAGE))
        
        self.set_voltage(axis, new_voltage)
    
    
    def set_voltage_rel(self, axis, r):
        '''
        set relative voltage on the piezo controller (i.e. between 0 and
        MAX_VOLTAGE.
        #=======================================================================
        # PLEASE USE Z-AXIS WITH CAUTION WHEN THE VGA IS NEAR THE SURFACE OF THE
        # CHIP
        #=======================================================================
        -------
        axis - (str) x y or z axis to set the voltage
        voltage - (float) number between 0 and 1 for piezo controller where
                0 is zero voltage and 1 is MAX_VOLTAGE
        '''
        if axis not in ["x", "y", "z"]:
            self.close_connection()
            self.log.error("%s axis is not in (x,y,z)" % axis)
        if not 0.0 <= r <= 1.0:
            self.close_connection()
            self.log.error("The relative voltage must be between 0 and 1")
        self.set_voltage(axis, r*self.MAX_VOLTAGE)
        setattr(self, axis, r*self.MAX_VOLTAGE)
    
    def half_xy_axes(self):
        '''
        set the voltages on the x, y piezos to half of the max voltage
        '''
        self.set_voltage_rel('x', 0.5)
        self.set_voltage_rel('y', 0.5)
        
    def zero_all_axes(self):
        '''
        Set all the axis to zero
        #############################################################
        WARNING DO NOT EXECUTE THIS COMMAND WHEN VGA IS NEAR THE CHIP
        #############################################################
        '''
        self.set_voltage("x", 0.0)
        self.set_voltage("y", 0.0)
        self.set_voltage("z", 0.0)
    
    
    def close_connection(self):
        self.close()

    def vol2dist(self, voltage):

        self.dist = (20/75)*1e-6*voltage + 0.1e-6

        return self.dist

    def dist2volt(self,dist):

        self.volt = (dist-0.1e-6)/((20/75)*1e-6)

        return self.volt

    
    def __del__(self):
        self.close()


if __name__ == "__main__":
    
    pc = PiezoController(port='COM22')
    

    # set y-voltage to half of max value
#     pc.set_voltage_rel('y', 0.5)
    
    if True:
        # Test that we can zero and set the Voltages for x,y,z
        
        # Set the x,y,z voltages
        print ('Setting x,y,z axes to 0V')
        pc.set_voltage("x", 0.)
        pc.set_voltage("y", 0.)
        pc.set_voltage("z", 0.)
        
         
        # print x, y, z voltages
        print ('x',pc.get_voltage("x"))
        print ('y',pc.get_voltage("y"))
        print ('z',pc.get_voltage("z"))
        
        print('\nSleeping for 2s \n')
        sleep(2.0)
        
        pc.set_voltage("x", 75.)
        pc.set_voltage("y", 75.)
        pc.set_voltage("z", 0.)
     
        print ('Setting x, y, z axes to 10V, 20V, 30V')
        print ('x',pc.get_voltage("x"))
        print ('y',pc.get_voltage("y"))
        print ('z',pc.get_voltage("z"))
    else:
        # Zero all the axes
        pc.zero_all_axes()
    
    # Increment the x-y axis by a few volts
#     pc.jog("y", -5.0)
#     pc.jog("x", 5.0) # increment x-voltage by 1 volt

    # Set xy to half of max voltage
#     pc.half_xy_axes()

    pc.close_connection()
    
    