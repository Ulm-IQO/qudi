import serial
import sys
import re
from time import sleep


# Set default port (COM6 for windows locally with USB converter)
if sys.platform.startswith('win'):
    DEFAULT_PORT = 'COM6'
else:
    DEFAULT_PORT = '/dev/ttyUSB0'


class PiezoController(serial.Serial):
    '''
    Python class for controlling voltages to 3-axis ThorLabs MDT693A
    '''
    
    MAX_VOLTAGE = 75.0 # This is the maximum voltage the Nanomax can handle!
    
    def __init__(self, port=DEFAULT_PORT, baudrate=115200):
        # Initialise the class using super class of (py)serial
        serial.Serial.__init__(self, port, baudrate, timeout=0.1)

        # Close any open connections and open a serial connection
        self.close()
        self.open()
    
    def cmd(self, command):
        '''
        Send a command to the MDT693A
        '''
        self.write( (str(command)+'\r').encode('utf-8'))
        # Have a timeout so that writing successive strings does not interrupt
        # the last command
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
            raise RuntimeError("%s axis is not in (x,y,z)" % axis)
        self.cmd("{}r?".format(axis))
        voltage = self.response()
        return voltage
    
    def set_voltage(self, axis, voltage):
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
            raise RuntimeError("%s axis is not in (x,y,z)" % axis)
        if not 0.0 <= voltage <= self.MAX_VOLTAGE:
            self.close_connection()
            raise RuntimeError("The current voltage (%s V) must be between 0V and 75V" % voltage)
        
        # This is the string that we send over serial to MDT693A
        self.cmd("{}v0{}".format(axis, voltage))
    
    
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
            raise RuntimeError("The current voltage (%s V) must be between 0V and 75V" % new_voltage)
        
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
            raise RuntimeError("%s axis is not in (x,y,z)" % axis)
        if not 0.0 <= r <= 1.0:
            self.close_connection()
            raise RuntimeError("The relative voltage must be between 0 and 1")
        self.set_voltage(axis, r*self.MAX_VOLTAGE)
    
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
    
    def __del__(self):
        self.close()


if __name__ == "__main__":
    
    # COM1 for bench A2, COM17 for SWIR bench ethernet connection
    pc = PiezoController(port='COM17')
    

    # set y-voltage to half of max value
#     pc.set_voltage_rel('y', 0.5)
    
    # print x, y, z voltages
    print ('x',pc.get_voltage("x"))
    print ('y',pc.get_voltage("y"))
    print ('z',pc.get_voltage("z"))
    
    # Set the x,y,z voltages
#     pc.set_voltage("z", 0.0)
#     pc.set_voltage("y", 40.2)
#     pc.set_voltage("z", 0.0)
    
    # Increment the x-y axis by a few volts
#     pc.jog("y", -5.0)
#     pc.jog("x", 5.0) # increment x-voltage by 1 volt

    # Set xy to half of max voltage
#     pc.half_xy_axes()

    # print x, y, z voltages
#     print ('x',pc.get_voltage("x"))
#     print ('y',pc.get_voltage("y"))
#     print ('z',pc.get_voltage("z"))

    pc.close_connection()