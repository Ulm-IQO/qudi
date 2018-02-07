# -*- coding: utf-8 -*-
"""
This module controls the Coherent OBIS laser.

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

from core.module import Base, ConfigOption
from interface.simple_laser_interface import SimpleLaserInterface
from interface.simple_laser_interface import ControlMode
from interface.simple_laser_interface import ShutterState
from interface.simple_laser_interface import LaserState
from enum import Enum
import visa

import serial
import time

class PSUTypes(Enum):
    """ LaserQuantum power supply types.
    """
    FPU = 0
    MPC6000 = 1
    MPC3000 = 2
    SMD12 = 3
    SMD6000 = 4

"""
import serial
import time

obis = serial.Serial('COM3', 
                     timeout=1
                    )
                    
# On deactivate
obis.close()

eol = '\r'

def send(message):
    new_message = message + eol
    obis.write(new_message.encode())
    

def communicate(message):
    send(message)
    time.sleep(0.1)
    response_len = obis.inWaiting()
    response = []
    while response_len > 0:
        response.append(obis.readline().decode().strip())
        response_len = obis.inWaiting()
        
    # TODO: check for "ok" and if so then just return the response
    return response
    
communicate('*IDN?')
communicate('SYSTem:INFormation:POWer?')
communicate('SOURce:POWer:NOMinal?')
communicate('SOURce:POWer:LIMit:HIGH?')
communicate('SOURce:POWer:LEVel?')
communicate('SOURce:POWer:LEVel:IMMediate:AMPLitude 0.001'
communicate('SOURce:POWer:LIMit:LOW?')

"""

class OBISLaser(Base, SimpleLaserInterface):
    """
    This module implements communication with the Edwards turbopump and
    vacuum equipment.
    """
    _modclass = 'lqlaser'
    _modtype = 'hardware'

    # serial_interface = ConfigOption('interface', 'ASRL1::INSTR', missing='warn')
    # maxpower = ConfigOption('maxpower', 0.250, missing='warn')
    # psu_type = ConfigOption('psu', 'SMD6000', missing='warn')

        
    eol = '\r'

    def on_activate(self):
        """ Activate module.
        """
        self.obis = serial.Serial('COM3', timeout=1)
        
        # self.psu = PSUTypes[self.psu_type]
        # self.connect_laser()
        

    def on_deactivate(self):
        """ Deactivate module.
        """

        self.disconnect_laser()

    def connect_laser(self):
        """ Connect to Instrument.

            @param str interface: visa interface identifier

            @return bool: connection success
        """
        # try:
        #     self.rm = visa.ResourceManager()
        #     rate = 9600 if self.psu == PSUTypes.SMD6000 else 19200
        #     self.inst = self.rm.open_resource(
        #         interface,
        #         baud_rate=rate,
        #         write_termination='\r\n',
        #         read_termination='\r\n',
        #         send_end=True)
        #     # give laser 2 seconds maximum to reply
        #     self.inst.timeout = 2000
        # except visa.VisaIOError:
        #     self.log.exception('Communication Failure:')
        #     return False
        # else:
        #     return True
        self.on_activate

        response = self._communicate('*IDN?')[0]

        if response.startswith('ERR-100'):
            return False
        else:
            return True

    def disconnect_laser(self):
        """ Close the connection to the instrument.
        """
        self.off()
        self.obis.close()
        """self.inst.close()
        self.rm.close()"""


    def allowed_control_modes(self):
        """ Control modes for this laser
        """
        """if self.psu == PSUTypes.FPU:
            return [ControlMode.MIXED]
        elif self.psu == PSUTypes.SMD6000:
            return [ControlMode.POWER]
        else:
            return [ControlMode.POWER, ControlMode.CURRENT]"""

    def get_control_mode(self):
        """ Get current laser control mode.

        @return ControlMode: current laser control mode
        """
    """ if self.psu == PSUTypes.FPU:
        return ControlMode.MIXED
    elif self.psu == PSUTypes.SMD6000:
        return ControlMode.POWER
    else:
        return ControlMode[self.inst.query('CONTROL?')]"""

    def set_control_mode(self, mode):
        """ Set laser control mode.

        @param ControlMode mode: desired control mode
        @return ControlMode: actual control mode
        """
        """if self.psu == PSUTypes.FPU:
            return ControlMode.MIXED
        elif self.psu == PSUTypes.SMD6000:
            return ControlMode.POWER
        else:
            if mode == ControlMode.POWER:
                reply1 = self.inst.query('PFB=OFF')
                reply2 = self.inst.query('CONTROL=POWER')
                self.log.debug("Set POWER control mode {0}, {1}.".format(reply1, reply2))
            else:
                reply1 = self.inst.query('PFB=ON')
                reply2 = self.inst.query('CONTROL=CURRENT')
                self.log.debug("Set CURRENT control mode {0}, {1}.".format(reply1, reply2))
        return self.get_control_mode()"""

    def get_power(self):
        """ Get laser power.

            @return float: laser power in watts
        """
        response = self._communicate('SOUR:POW:LEV:IMM:AMPL?')
        
        # return float(response.split('W')[0])
        return float(response[0])
        
    #    """ 
    #     try:
    #         if "mW" in response:
    #             return float(response.split('mW')[0])/1000
    #         elif 'W' in response:
    #             return float(response.split('W')[0])
    #         else:
    #             return float(response[0])
    #     except ValueError:
    #         self.log.exception("Answer was {0}.".format(response))
    #         return -1"""

    def get_power_setpoint(self):
        """ Get the laser power setpoint.

        @return float: laser power setpoint in watts
        """
        #   """if self.psu == PSUTypes.FPU:
        #     answer = self.inst.query('SETPOWER?')
        #     try:
        #         if "mW" in answer:
        #             return float(answer.split('mW')[0]) / 1000
        #         elif 'W' in answer:
        #             return float(answer.split('W')[0])
        #         else:
        #             return float(answer)
        #     except ValueError:
        #         self.log.exception("Answer was {0}.".format(answer))
        #         return -1
        # else:
        #     return self.get_power()"""

    def get_power_range(self):
        """ Get laser power range.

        @return tuple(float, float): laser power range
        """
        
        minpower = float(self._communicate('SOUR:POW:LIM:LOW?')[0])
        maxpower = float(self._communicate('SOUR:POW:LIM:HIGH?')[0])
        return (minpower, maxpower)
        # """direct insert vs inquiry - what is upper power limit. """

    def set_power(self, power):
        """ Set laser power

        @param float power: desired laser power in watts
        """
        self._communicate('SOUR:POW:LEV:IMM:AMPL {}'.format(power))
        
        # '''if self.psu == PSUTypes.FPU:
        #     self.inst.query('POWER={0:f}'.format(power))
        # else:
        #     self.inst.query('POWER={0:f}'.format(power*1000))'''

    def get_current_unit(self):
        """ Get unit for laser current.

            @return str: unit for laser current
        """
        return '%'

    def get_current_range(self):
        """ Get range for laser current.

            @return tuple(flaot, float): range for laser current
        """
        return (0, 100)

    def get_current(self):
        """ Cet current laser current

        @return float: current laser current
        """
        
        return float(self._communicate('SOUR:POW:CURR?')[0])


        # """if self.psu == PSUTypes.MPC3000 or self.psu == PSUTypes.MPC6000:
        #     return float(self.inst.query('SETCURRENT1?').split('%')[0])
        # else:
        #     return float(self.inst.query('CURRENT?').split('%')[0])"""

    def get_current_setpoint(self):
        """ Current laser current setpoint.

        @return float: laser current setpoint
        """
        # """if self.psu == PSUTypes.MPC3000 or self.psu == PSUTypes.MPC6000:
        #     return float(self.inst.query('SETCURRENT1?').split('%')[0])
        # elif self.psu == PSUTypes.SMD6000:
        #     return float(self.inst.query('CURRENT?').split('%')[0])
        # else:
        #     return float(self.inst.query('SETCURRENT?').split('%')[0])"""

    def set_current(self, current_percent):
        """ Set laser current setpoint.

        @param float current_percent: laser current setpoint
        """
        # """self._communicate('SOUR:POW:CURR{current_percent}')"""
        return self.get_current()
        # """self.inst.query('CURRENT={0}'.format(current_percent))
        # return self.get_current()"""

    def get_shutter_state(self):
        """ Get laser shutter state.

        @return ShutterState: laser shutter state
        """
        return ShutterState.NOSHUTTER
        # """if self.psu == PSUTypes.FPU:
        #     state = self.inst.query('SHUTTER?')
        #     if 'OPEN' in state:
        #         return ShutterState.OPEN
        #     elif 'CLOSED' in state:
        #         return ShutterState.CLOSED
        #     else:
        #         return ShutterState.UNKNOWN
        # else:
        #     return ShutterState.NOSHUTTER"""

    def set_shutter_state(self, state):
        """ Set the desired laser shutter state.

        @param ShutterState state: desired laser shutter state
        @return ShutterState: actual laser shutter state
        """
        return self.get_shutter_state()
        
        # """if self.psu == PSUTypes.FPU:
        #     actstate = self.get_shutter_state()
        #     if state != actstate:
        #         if state == ShutterState.OPEN:
        #             self.inst.query('SHUTTER OPEN')
        #         elif state == ShutterState.CLOSED:
        #             self.inst.query('SHUTTER CLOSE')
        # return self.get_shutter_state()"""

    def get_psu_temperature(self):
        """ Get power supply temperature

        @return float: power supply temperature
        """
        self._communicate('SOUR:TEMP:DIOD?')
        return response[0]
        # """return float(self.inst.query('PSUTEMP?').split('C')[0])"""
        

    def get_laser_temperature(self):
        """ Get laser head temperature

        @return float: laser head temperature
        """
        return float(self._communicate('SOUR:TEMP:INT?').split('C')[0])

        # """return float(self.inst.query('LASTEMP?').split('C')[0])"""


    def get_temperatures(self):
        """ Get all available temperatures.

            @return dict: dict of temperature names and value
        """
        return {
            'Diode': self.get_PSU_temperature(),
            'Internal': self.get_laser_temperature()
            }

        # """return {
        #     'psu': self.get_psu_temperature(),
        #     'laser': self.get_laser_temperature()
        #     }"""

    def set_temperatures(self, temps):
        """ Set temperature for lasers with adjustable temperature for tuning

            @return dict: dict with new temperature setpoints
        """
        return {}

    def get_temperature_setpoints(self):
        """ Get temperature setpints.

            @return dict: dict of temperature name and setpoint value
        """
        return {}

    def get_lcd(self):
        """ Get the text displayed on the PSU display.

            @return str: text on power supply display
        """
    #    """ if self.psu == PSUTypes.SMD12 or self.psu == PSUTypes.SMD6000:
    #         return ''
    #     else:
    #         return self.inst.query('STATUSLCD?')"""

    def get_laser_state(self):
        """ Get laser operation state

        @return LaserState: laser state
        """
        state = self._communicate('SOUR:AM:STAT?')
        # """if self.psu == PSUTypes.SMD6000:
        #     state = self.inst.query('STAT?')
        # else:
        #     state = self.inst.query('STATUS?')"""
        if 'ON' in state:
            return LaserState.ON
        elif 'OFF' in state:
            return LaserState.OFF
        else:
            return LaserState.UNKNOWN

    def set_laser_state(self, status):
        """ Set desited laser state.

        @param LaserState status: desired laser state
        @return LaserState: actual laser state
        """
        actstat = self.get_laser_state()
        if actstat != status:
        
            if status == 'LaserState.ON':
                self._communicate('SOUR:AM:STAT ON')
                return self.get_laser_state()
            elif status == 'LaserState.OFF':
                self._communicate('SOUR:AM:STAT OFF')
                return self.get_laser_state()
            else:
                return 'LaserState.Unknown'

    def on(self):
        """ Turn laser on.

            @return LaserState: actual laser state
        """
        status = self.get_laser_state()
        if status == LaserState.OFF :
            self._communicate('SOUR:AM:STAT ON')
            return self.get_laser_state()
        else: 
            return self.get_laser_state()
        
        # """return self.set_laser_state(LaserState.ON)"""

    def off(self):
        """ Turn laser off.

            @return LaserState: actual laser state
        """
        self.set_laser_state('LaserState.OFF')
        return self.get_laser_state()

    def get_firmware_version(self):
        """ Ask the laser for ID.

        @return str: what the laser tells you about itself
        """
        """if self.psu == PSUTypes.SMD6000:
            self.inst.write('VERSION')
        else:
            self.inst.write('SOFTVER?')"""
        self._communicate('SYST:INF:FVER')
        return response
        
        # """lines = []
        # try:
        #     while True:
        #         lines.append(self.inst.read())
        # except:
        #     pass
        # return lines"""

    def dump(self):
        """ Return LaserQuantum information dump

        @return str: diagnostic information dump from laser
        """
        # """self.inst.write('DUMP ')
        # lines = []
        # try:
        #     while True:
        #         lines.append(self.inst.read())
        # except:
        #     pass
        # return lines"""
        return {}

    def timers(self):
        """ Return information about component runtimes.

            @return str: runtimes of components
        """
        self.inst.write('TIMERS')
        lines = []
        try:
            while True:
                lines.append(self.inst.read())
        except:
            pass
        return lines

    def get_extra_info(self):
        """ Extra information from laser.

            @return str: multiple lines of text with information about laser

            For LaserQuantum devices, this is the firmware version, dump and timers information
        """
        extra = ''
        extra += '\n'.join(self.get_firmware_version())
        extra += '\n'
        if self.psu == PSUTypes.FPU:
            extra += '\n'.join(self.dump())
            extra += '\n'
        extra += '\n'.join(self.timers())
        extra += '\n'
        return extra

    def _send(self, message):
        new_message = message + self.eol
        self.obis.write(new_message.encode())

    def _communicate(self, message):
        self._send(message)
        time.sleep(0.1)
        response_len = self.obis.inWaiting()
        response = []

        while response_len > 0:
            if (response_len == 4) and (response == 'OK'):
                response.append('')                     
            else:
                response.append(self.obis.readline().decode().strip())
            response_len = self.obis.inWaiting()

        return response

    def _set_laser_to_11(self):
        self.set_power(0.165)
            