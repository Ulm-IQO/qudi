# -*- coding: utf-8 -*-

"""
This module controls the AMI Model 430 Power Supply Programmer.

Config for copy paste:


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


import socket

from core.module import Base

class AMI430(Base):

    def __init__(self, ip, port=7180):
        self._ip = ip
        self._port = port
        super().__init__(ip,port)

    def on_activate(self):
        self.connect()
        self.remote()

    def on_deactivate(self):
        self.local()
        self.disconnect()

    def connect(self, ip=None, port=None):
        if not ip:
            ip = self._ip
        if not port:
            port = self._port
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.connect((ip, port))
            greeting = self._read()
            print(greeting)
            if not "American Magnetics Model 430 IP Interface" in greeting:
                raise RuntimeError(f"Device does not answer with correct greeting message.\nRecieved message:\n{greeting}")
        except Exception as err:
            self.disconnect()
            raise               

    def disconnect(self):
        try:
            self._socket.close()
        except Exception as err:
            raise

    def _read(self, length=1024):
        """Reads the feedback from the device."""
        return self._socket.recv(length).decode("ascii").strip().split("\r\n")

    def _write(self, cmd):
        """Writes the specified command to the decive without waiting for a response."""
        return self._socket.send( (cmd+"\r\n").encode("ascii"))

    def _query(self, cmd):
        """Writes the specified command to the device and waits for a response. 
        
        Will take forever, if no response is given. In this case use _write."""
        self._write(cmd)
        return self._read()

    def idn(self):
        """ Returns the identification string of the Model 430 Programmer.
        
        The identification string contains the AMI model number and firmware revision code.
        
        """

        return self._query("*IDN?")
    
    def local(self):
        """Enables the front panel.
        
        Local acess is now possible. """
        self._write('SYST:LOC')

    def remote(self):
        """Disables the front control panel to prevent accidental operation"""
        self._write('SYST:REM')
        
    def read_error(self):
        """Reads out the error buffer.
        
        From manual:
        Up to 10 errors are stored in the error buffer.
        Errors are retrieved in first-in-first-out (FIFO) order.
        The error buffer is cleared by the *CLS (clear status) command or when the power is cycled.
        Errors are also cleared as they are read.
        
        """
        self._query('SYST:ERR?')
    
    def reset(self):
        """ Resets the Model 430 Programmer.
        
        From manual:
        This is equivalent to cycling the power to the Model 430 Programmer using the power switch. 
        All non-volatile calibration data and battery-backed memory is restored. 
        Status is cleared according to the *PSC setting.
        
        """

        self._write('RST')

    def get_coil_constant(self):
        """Returns the coil constant setting in kG/A or T/A per the selected field units."""
        ans = self._query('COIL?')
        return ans
    
    def set_coil_constant(self, constant):
        """Sets the coil constant (field to current ratio) setting in kG/A or T/A per the selected field units.
        
        The coil constant needs to be a non zero positive value."""
        if not float(constant) > 0:
            raise Exception('Value needs to be a nonzero positive value.')
        else:
            self._write('CONF:COIL ' + str(constant))

    def get_current_limit(self):
        """Returns the Current Limit in Amperes."""
        ans = self._query('CURR:LIM?')
        return ans

    def set_current_limit(self,limit):
        """Sets the Current limit in amperes."""
        self._write('CONF:CURR:LIM ' + str(limit))

    def check_for_PS(self):
        """Checks if a persistent switch is installed on the connected superconducting magnet.
        
        Returns 1 if one is connected, 0 if not."""
        ans = self._query('PS:INST?')
        return ans

    def get_ramp_rate_units(self):
        """Returns the unit for the ramp rate.
        "0" means 1/s, "1" means 1/min.
        """
        ans = self._query('RAMP:RATE:UNITS?')
        return ans
    
    def set_ramp_rate_units(self, unit='0'):
        """Sets the unit for the ramp rate.
        
        '0', 's' or 'sek' sets it to seconds (default).

        '1' or 'min' sets it to minutes.
        """
        unit = str(unit)
        alias_seconds = ['0', 's', 'sek']
        alias_minutes = ['1', 'min']
        if unit in alias_seconds:
            # set ramp rate in terms of seconds
            self._write('CONF:RAMP:RATE:UNITS 0')
        elif unit in alias_minutes:
            # set ramp rate in terms of minutes
            self._write('CONF:RAMP:RATE:UNITS 1')
        else:
            raise Exception('Unknown unit entered.')

    def get_field_units(self):
        """Returns the unit for the field.
        "0" means kilogauss, "1" means tesla.
        """
        ans = self._query('FIELD:UNITS?')
        return ans
    
    def set_field_units(self, unit='0'):
        """Sets the unit for the field.
        
        '0', 'kG' or 'kGs' sets it to kilogauss (default).

        '1' or 'T' sets it to tesla.
        """
        unit = str(unit)
        alias_seconds = ['0', 'kG', 'kGs']
        alias_minutes = ['1', 'T']
        if unit in alias_seconds:
            # set field unit to kilogauss
            self._write('CONF:FIELD:UNITS 0')
        elif unit in alias_minutes:
            # set field unit to tesla
            self._write('CONF:FIELD:UNITS 1')
        else:
            raise Exception('Unknown unit entered.')
        
    def get_voltage_limit(self):
        """Returns the voltage limit for ramping in volts.
        
        It must not exceed the voltage limit if the power supply.
        """
        ans = self._query('VOLT:LIM?')
        return ans

    def set_voltage_limit(self, limit):
        """Sets the voltage limit for ramping in volts.
        
        It must not exceed the voltage limit if the power supply.
        """
        self._write('CONF:VOLT:LIM ' + str(limit))

    def get_target_current(self):
        """Returns the target current in amperes."""
        ans = self._query('CURR:TARG?')
        return ans

    def set_target_current(self, target):
        """Sets the target current in amperes."""
        self._write('CONF:CURR:TARG ' + str(target))
    
    def get_target_field(self):
        """Returns the target field in kilogauss or tesla, depending on the selected field units.
        
        A coil constant needs to be defined for this command.
        """
        ans = self._query('FIELD:TARG?')
        return ans

    def set_target_field(self,target,unit=None):
        """Sets the target field in kilogauss or tesla, depending on the selected field units.
        
        A coil constant needs to be defined for this command.

        @param target: target field

        @param unit: unit for the field. See set_field_units() for details. Skip if units should not be changed.
        """
        if not unit == None:
            self.set_field_units(unit)
        self._write('CONF:FIELD:TARG ' + str(target))

    def get_number_ramp_rate_segments(self):
        """Returns the number of ramp segments."""
        ans = self._write('AMP:RATE:SEG?')
        return ans
    
    def set_number_ramp_rate_segments(self, number):
        """Sets the number of ramp segments"""
        self._write('CONF:RAMP:RATE:SEG ' + str(number))
    
    def get_ramp_rate_current(self,segment):
        """Returns the ramp rate (in ramp rate units) for the specified segment.
        
        Segment numbering starts at 1.

        Return is tuple of ramp rate and upper bound for the segment.
        """
        ans = self._query('RAMP:RATE:CURRENT:' + str(segment) + '?')
        return ans

    def set_ramp_rate_current(self, segment, rate, upper_bound):
        """Sets the ramp rate (in ramp rate units) for the specified segment.
        
        @param segment: number (starting with 1) of the segment that one want s to modify.
        
        @param rate: ramp rate for the segment in ramp rate units (A/s or A/min).
        
        @param upper_bound: upper bound for the curent segment.
            E.g. putting 55 for segment 1 will result in a segment that runs from 0 to 55
            and putting 58 for segment 2 will result in a segment that runs from 55 to 58.
        """
        self._write('CONF:RAMP:RATE:CURR ' + str(segment) , + ',' + str(rate) + ',' + str(upper_bound))
    
    def get_ramp_rate_field(self,segment):
        """Returns the ramp rate (in ramp rate units) for the specified segment.
        
        Segment numbering starts at 1.

        Return is tuple of ramp rate and upper bound for the segment.
        """
        ans = self._query('RAMP:RATE:FIELD:' + str(segment) + '?')
        return ans

    def set_ramp_rate_field(self, segment, rate, upper_bound):
        """Sets the ramp rate (in ramp rate units) for the specified segment.

        A coil constant needs to be defined for this command to work.
        
        @param segment: number (starting with 1) of the segment that one want s to modify.
        
        @param rate: ramp rate for the segment in ramp rate units (T/s or T/min or kG/s or kG/min).
        
        @param upper_bound: upper bound for the curent segment.
            E.g. putting 55 for segment 1 will result in a segment that runs from 0 to 55
            and putting 58 for segment 2 will result in a segment that runs from 55 to 58.
        """
        self._write('CONF:RAMP:RATE:FIELD ' + str(segment) , + ',' + str(rate) + ',' + str(upper_bound))


    def get_magnet_current(self):
        """Returns the current flowing in the magnet.
        
        Returns the current flowing in the magnet in amperes, 
        expressed as a number with four significant digits past the decimal point, such as 5.2320. 
        If the magnet is in persistent mode, the command returns the current that was flowing in the magnet when persistent mode was entered.
        """
        ans = self._query('CURR:MAG?')
        return ans
    
    def get_supply_current(self):
        """Returns the measured power supply current in amperes."""
        ans = self._query('CURR:SUPP?')
        return ans

    def get_field(self):
        """Returns the calculated field in kG or T (depending on selected field units).
        
        This query requires that a coil constant be defined; otherwise, an error is generated.
        The field is calculated by multiplying the measured magnet current by the coil constant.
        If the magnet is in persistent mode, the command returns the field that was present when persistent mode was entered.
        """
        ans = self._query('FIELD:MAG?')
        return ans

    def ext_rampdown(self):
        """For rampdown see page 147. Sth with external trigger (e.g. Helium failure) for rampdown."""
        #TODO: DO we need this one?
        pass

    def ramp(self):
        pass

    def ramp_to_zero(self):
        pass
