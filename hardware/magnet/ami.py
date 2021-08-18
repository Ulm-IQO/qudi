# -*- coding: utf-8 -*-

"""
This module controls the AMI Model 430 Power Supply Programmer.

Config for copy paste:
    magnet_x:
        module.Class: 'magnet.ami.AMI430'
        ip: '192.168.202.102'
        port: 7180

    magnet_y:
        module.Class: 'magnet.ami.AMI430'
        ip: '192.168.202.101'
        port: 7180

    magnet_z:
        module.Class: 'magnet.ami.AMI430'
        ip: '192.168.202.100'
        port: 7180


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
from core.configoption import ConfigOption

from interface.magnet_1d_interface import Magnet1DInterface

class AMI430(Base, Magnet1DInterface):
    #If you do not give the interface here, you will get an error.
    _ip = ConfigOption(name='ip', missing='warn')
    _port = ConfigOption(name='port', missing='warn')

    def __init__(self, ip=None, port=None,**kwargs):
        if ip:
            self._ip = ip
        if port:
            self._port = port
        super().__init__(**kwargs)

    def on_activate(self):
        self.connect()
        self.remote()
        self.set_field_units('T')
        self.set_ramp_rate_units('s')

    def on_deactivate(self):
        print('deactivating 1D magnet "' + str(self) + '"')
        self.ramp_to_zero()
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
        
        FOr explanation of individual erroes see manual  section 4.6 (page 153).
        """

        self._write('RST')

    def get_coil_constant(self):
        """Returns the coil constant setting in kG/A or T/A per the selected field units."""
        ans = self._query('COIL?')
        ans=float(ans[0])
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
        ans=float(ans[0])
        return ans

    def set_current_limit(self,limit):
        """Sets the Current limit in amperes."""
        self._write('CONF:CURR:LIM ' + str(limit))

    def check_for_PS(self):
        """Checks if a persistent switch is installed on the connected superconducting magnet.
        
        Returns 1 if one is connected, 0 if not."""
        ans = self._query('PS:INST?')
        ans=int(ans[0])
        return ans

    def get_ramp_rate_units(self):
        """Returns the unit for the ramp rate.
        "0" means 1/s, "1" means 1/min.
        """
        ans = self._query('RAMP:RATE:UNITS?')
        ans=int(ans[0])
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
        ans=int(ans[0])
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
        ans=float(ans[0])
        return ans

    def set_voltage_limit(self, limit):
        """Sets the voltage limit for ramping in volts.
        
        It must not exceed the voltage limit if the power supply.
        """
        self._write('CONF:VOLT:LIM ' + str(limit))

    def get_target_current(self):
        """Returns the target current in amperes."""
        ans = self._query('CURR:TARG?')
        ans=float(ans[0])
        return ans

    def set_target_current(self, target):
        """Sets the target current in amperes."""
        self._write('CONF:CURR:TARG ' + str(target))
    
    def get_target_field(self):
        """Returns the target field in kilogauss or tesla, depending on the selected field units.
        
        A coil constant needs to be defined for this command. 
        This is because field gets calculated from current via coil constant.
        """
        ans = self._query('FIELD:TARG?')
        ans=float(ans[0])
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
        ans = self._query('AMP:RATE:SEG?')
        ans=int(ans[0])
        return ans
    
    def set_number_ramp_rate_segments(self, number):
        """Sets the number of ramp segments"""
        self._write('CONF:RAMP:RATE:SEG ' + str(number))
    
    def get_ramp_rate_segment_current(self,segment):
        """Returns the ramp rate (in ramp rate units) for the specified segment.
        
        Segment numbering starts at 1.

        Return is tuple of ramp rate and upper bound for the segment.
        """
        ans = self._query('RAMP:RATE:CURRENT:' + str(segment) + '?')
        ans=float(ans[0])
        return ans

    def set_ramp_rate_segment_current(self, segment, rate, upper_bound):
        """Sets the ramp rate (in ramp rate units) for the specified segment.
        
        @param segment: number (starting with 1) of the segment that one want s to modify.
        
        @param rate: ramp rate for the segment in ramp rate units (A/s or A/min).
        
        @param upper_bound: upper bound for the curent segment.
            E.g. putting 55 for segment 1 will result in a segment that runs from 0 to 55
            and putting 58 for segment 2 will result in a segment that runs from 55 to 58.
        """
        self._write('CONF:RAMP:RATE:CURR ' + str(segment) + ',' + ',' + str(rate) + ',' + str(upper_bound))
    
    def set_ramp_rates_current(self, ramp_rates):
        """Specifies the ramp rates according to ramp_rates.
        
        @param ramp_rates: iterable of tupels. Each tuple consists of the ramp rate and the upper bound for the segent.
        """
        n_segments_old = self.get_number_ramp_rate_segments()
        n_segments = len(ramp_rates)
        if not n_segments_old == n_segments:
            print('Number of elements in new segment does not match old number of segments. Overwriting old length.')
            self.set_number_ramp_rate_segments(n_segments)
        for i in range(n_segments):
            rate,upper_bound = ramp_rates[i]
            segment = i+1
            self.set_ramp_rate_segment_current(segment, rate, upper_bound)

    def get_ramp_rate_segment_field(self,segment):
        """Returns the ramp rate (in ramp rate units) for the specified segment.
        
        Segment numbering starts at 1.

        Return is tuple of ramp rate and upper bound for the segment.
        """
        ans = self._query('RAMP:RATE:FIELD:' + str(segment) + '?')
        ans=float(ans[0])
        return ans

    def set_ramp_rate_segment_field(self, segment, rate, upper_bound):
        """Sets the ramp rate (in ramp rate units) for the specified segment.

        A coil constant needs to be defined for this command to work.
        
        @param segment: number (starting with 1) of the segment that one want s to modify.
        
        @param rate: ramp rate for the segment in ramp rate units (T/s or T/min or kG/s or kG/min).
        
        @param upper_bound: upper bound for the curent segment.
            E.g. putting 55 for segment 1 will result in a segment that runs from 0 to 55
            and putting 58 for segment 2 will result in a segment that runs from 55 to 58.
        """
        self._write('CONF:RAMP:RATE:FIELD ' + str(segment) + ',' + ',' + str(rate) + ',' + str(upper_bound))

    def set_ramp_rates_field(self, ramp_rates):
        """Specifies the ramp rates according to ramp_rates.
        
        @param ramp_rates: iterable of tupels. Each tuple consists of the ramp rate and the upper bound for the segent.
        """
        n_segments_old = self.get_number_ramp_rate_segments()
        n_segments = len(ramp_rates)
        if not n_segments_old == n_segments:
            print('Number of elements in new segment does not match old number of segments. Overwriting old length.')
            self.set_number_ramp_rate_segments(n_segments)
        for i in range(n_segments):
            rate,upper_bound = ramp_rates[i]
            segment = i+1
            self.set_ramp_rate_segment_field(segment, rate, upper_bound)

    def get_magnet_current(self):
        """Returns the current flowing in the magnet.
        
        Returns the current flowing in the magnet in amperes, 
        expressed as a number with four significant digits past the decimal point, such as 5.2320. 
        If the magnet is in persistent mode, the command returns the current that was flowing in the magnet when persistent mode was entered.
        """
        ans = self._query('CURR:MAG?')
        ans=float(ans[0])
        return ans
    
    def get_supply_current(self):
        """Returns the measured power supply current in amperes."""
        ans = self._query('CURR:SUPP?')
        ans=float(ans[0])
        return ans

    def get_field(self):
        """Returns the calculated field in kG or T (depending on selected field units).
        
        This query requires that a coil constant be defined; otherwise, an error is generated.
        The field is calculated by multiplying the measured magnet current by the coil constant.
        If the magnet is in persistent mode, the command returns the field that was present when persistent mode was entered.
        """
        ans = self._query('FIELD:MAG?')
        ans=float(ans[0])
        return ans

    def ext_rampdown(self):
        """For rampdown see page 147. Sth with external trigger (e.g. Helium failure) for rampdown."""
        #TODO: DO we need this one? Commands are on page 147 of the manual.
        pass

    def continue_ramp(self):
        """Resumes ramping.
        
        Puts the power supply in automatic ramping mode. Ramping resumes until target field/current is reached.
        """
        self._write('RAMP')
    
    def pause_ramp(self):
        """Pauses the ramping process.
        
        The current/field will stay at the level it has now.
        """
        self._write('PAUSE')

    def ramp_to_zero(self):
        """Places the Model 430 Programmer in ZEROING CURRENT mode:
        
        Ramping automatically initiates and continues at the ramp rate until the power supply output current is less than 0.1% of Imax,
        at which point the AT ZERO status becomes active.
        """
        self._write('ZERO')

    def get_ramping_state(self):
        """Returns the integer value of the current ramping state.

        integers mean the following:
            1:  RAMPING to target field/current
            2:  HOLDING at the target field/current
            3:  PAUSED
            4:  Ramping in MANUAL UP mode
            5:  Ramping in MANUAL DOWN mode
            6:  ZEROING CURRENT (in progress)
            7:  Quench detected
            8:  At ZERO current
            9:  Heating persistent switch
            10: Cooling persistent switch
        """
        ans = self._query('STATE?')
        ans=int(ans[0])
        return ans

    #TODO: add PSwitch functionality (manual page 149).

    #TODO: add Quench State functionality (manual page 150).

    def ramp(self, field_target=None, current_target=None):
        """ Starts ramping towards the voltage/current limit.

        The ramp needs to be set up beforehand (ramp rate, limits ,etc.).

        You can only choose a voltage ramp or a current ramp.
        """
        
        #make sure that only one parameter is specified
        if field_target==None and not current_target==None:
            self.set_target_current(current_target)
        elif current_target==None and not field_target==None:
            self.set_target_field(field_target)
        else:
            raise RuntimeError('You need to give either field or current target.')
        
        self.continue_ramp()


    def get_constraints(self):
        """ Retrieve the hardware constrains from the magnet controller.

        @return dict: dict with constraints for the magnet hardware. 
        """

        coil_constant = self.get_coil_constant()
        current_limit = self.get_current_limit()
        voltage_limit = self.get_voltage_limit()
        field_limit = coil_constant * current_limit

        constraints = {
            'current_limit' : current_limit,
            'voltage_limit' : voltage_limit,
            'field_limit' : field_limit
            }

        return constraints
