"""
Interface file for a PID arduino device.

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
import time

from interface.pid_controller_interface import PIDControllerInterface
import visa
from core.module import Base
from core.configoption import ConfigOption
from core.statusvariable import StatusVar
from core.util.mutex import Mutex


class PIDarduino(Base, PIDControllerInterface):
    """ This interface is used to control a PID device.

    From Wikipedia : https://en.wikipedia.org/wiki/PID_controller
    A proportional–integral–derivative controller (PID controller or three-term controller) is a control loop mechanism
    employing feedback that is widely used in industrial control systems and a variety of other applications requiring
    continuously modulated control. A PID controller continuously calculates an error value e(t) as the difference
    between a desired setpoint (SP) and a measured process variable (PV) and applies a correction based on proportional,
    integral, and derivative terms (denoted P, I, and D respectively), hence the name.

    If the device is enabled, the control value is computed by the the PID system of the hardware. If the device is
    disabled, the control value is set by the manual value.

    """

    """
    arduinopid:
        module.Class: 'pid_arduino.PIDarduino'
        interface: 'ASRL4::INSTR'
        baudrate: 115200
    """

    _serial_interface = ConfigOption('interface', missing='error')
    _serial_baudrate = ConfigOption(name='baudrate', default=9600, missing='nothing')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock = Mutex()
        self._resource_manager = None
        self._instrument = None

    def on_activate(self):
        """ Prepare module, connect to hardware.
        """
        try:
            self._resource_manager = visa.ResourceManager()
            self._instrument = self._resource_manager.open_resource(
                self._serial_interface,
                baud_rate=self._serial_baudrate,
                write_termination='\n',
                read_termination='\r\n',
                timeout=500
            )
            time.sleep(1)
        except visa.VisaIOError as e:
            self.log.exception("PID Controller nicht connected")
            return False
        else:
            return True


    def on_deactivate(self):
        """ Disconnect from hardware on deactivation.
        """
        self._instrument.write("stop")
        self._instrument.close()
        self._resource_manager.close()
        time.sleep(1)

    def get_params(self):
        try:
            response = self._instrument.query('params').strip()
        except visa.VisaIOError:
            self.log.debug('Hardware query raised VisaIOError, trying again...')
        else:
            response = response.split(' ')
            dict = {'kp': float(response[1]), 'ki': float(response[3]), 'kd': float(response[5]), 'setpoint': float(response[7])}
            return dict
        raise Exception('Hardware did not respond after 3 attempts. Visa error')

    def get_values(self):
        try:
            response = self._instrument.query('values').strip()
        except visa.VisaIOError:
            self.log.debug('Hardware query raised VisaIOError, trying again...')
        else:
            response = response.split(' ')
            dict = {'setpoint': float(response[1]), 'feedback': float(response[3]), 'output': float(response[5])}
            return dict
        raise Exception('Hardware did not respond after 3 attempts. Visa error')


    def get_kp(self):
        """ Get the coefficient associated with the proportional term

         @return (float): The current kp coefficient associated with the proportional term
         """
        return self.get_params()['kp']

    def set_kp(self, kp):
        """ Set the coefficient associated with the proportional term

         @param (float) kp: The new kp coefficient associated with the proportional term
         """
        try:
            self._instrument.write("kp"+str(kp))
            time.sleep(0.1)
        except visa.VisaIOError:
            self.log.debug('Hardware query raised VisaIOError')

    def get_ki(self):
        """ Get the coefficient associated with the integral term

         @return (float): The current ki coefficient associated with the integral term
         """
        return self.get_params()['ki']

    def set_ki(self, ki):
        """ Set the coefficient associated with the integral term

         @param (float) ki: The new ki coefficient associated with the integral term
         """
        try:
            self._instrument.write("i"+str(ki))
            time.sleep(0.1)
        except visa.VisaIOError:
            self.log.debug('Hardware query raised VisaIOError')

    def get_kd(self):
        """ Get the coefficient associated with the derivative term

         @return (float): The current kd coefficient associated with the derivative term
         """
        return self.get_params()['kd']

    def set_kd(self, kd):
        """ Set the coefficient associated with the derivative term

         @param (float) kd: The new kd coefficient associated with the derivative term
         """
        try:
            self._instrument.write("d"+str(kd))
            time.sleep(0.1)
        except visa.VisaIOError:
            self.log.debug('Hardware query raised VisaIOError')

    def get_setpoint(self):
        """ Get the setpoint value of the hardware device

         @return (float): The current setpoint value
         """
        return self.get_params()['setpoint']

    def set_setpoint(self, setpoint):
        """ Set the setpoint value of the hardware device

        @param (float) setpoint: The new setpoint value
        """
        try:
            self._instrument.write("setpoint"+str(setpoint))
            time.sleep(0.1)
        except visa.VisaIOError:
            self.log.debug('Hardware query raised VisaIOError')

    def get_manual_value(self):
        """ Get the manual value, used if the device is disabled

        @return (float): The current manual value
        """
        return 0

    def set_manual_value(self, manualvalue):
        """ Set the manual value, used if the device is disabled

        @param (float) manualvalue: The new manual value
        """
        try:
            self._instrument.write("manual"+str(int(manualvalue)))
            time.sleep(0.1)
        except visa.VisaIOError:
            self.log.debug('Hardware query raised VisaIOError')

    def get_enabled(self):
        """ Get if the PID is enabled (True) or if it is disabled (False) and the manual value is used

        @return (bool): True if enabled, False otherwise
        """
        try:
            response = self._instrument.query('status').strip()
        except visa.VisaIOError:
            self.log.debug('Hardware query raised VisaIOError, trying again...')
        else:
            response = int(response)
            if response == 1:
                return True
            else:
                return False
        raise Exception('Hardware did not respond after 3 attempts. Visa error')

    def set_enabled(self, enabled):
        """ Set if the PID is enabled (True) or if it is disabled (False) and the manual value is used

        @param (bool) enabled: True to enabled, False otherwise
        """
        if enabled:
            try:
                self._instrument.write("start")
                time.sleep(0.1)
            except visa.VisaIOError:
                self.log.debug('Hardware query raised VisaIOError')
        else:
            try:
                self._instrument.write("stop")
                time.sleep(0.1)
            except visa.VisaIOError:
                self.log.debug('Hardware query raised VisaIOError')

    def get_control_limits(self):
        """ Get the current limits of the control value as a tuple

        @return (tuple(float, float)): The current control limits
        """
        limits = (0, 5)
        return limits

    def set_control_limits(self, limits):
        """ Set the current limits of the control value as a tuple

        @param (tuple(float, float)) limits: The new control limits

        The hardware should check if these limits are within the maximum limits set by a config option.
        """
        pass

    def get_process_value(self):
        """ Get the current process value read

        @return (float): The current process value
        """
        return self.get_values()['feedback']

    def get_control_value(self):
        """ Get the current control value read

        @return (float): The current control value
        """
        return self.get_values()['output']

    def get_extra(self):
        """ Get the P, I and D terms computed bu the hardware if available

         @return dict(): A dict with keys 'P', 'I', 'D' if available, an empty dict otherwise
         """
        return {}
