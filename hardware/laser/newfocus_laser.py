from core.module import Base
from core.configoption import ConfigOption
from interface.newfocus_laser_interface import NewfocusLaserInterface
from enum import Enum
import clr
clr.AddReference(r'mscorlib')
clr.AddReference('System.Reflection')
from System.Text import StringBuilder
from System import Int32
from System.Reflection import Assembly

class Models(Enum):
    """ Model numbers for Millennia lasers
    """
    NEWFOCUS6700 = 0


class NewfocusDiodeLaser(Base, NewfocusLaserInterface):
    """ Spectra Physics Millennia diode pumped solid state laser.

    Example config for copy-paste:

    millennia_laser:
        module.Class: 'laser.millennia_ev_laser.MillenniaeVLaser'
        interface: 'ASRL1::INSTR'
        maxpower: 25 # in Watt

    """
    _modclass = 'newfocusdiodelaser'
    _modtype = 'hardware'
    _DeviceKey = ConfigOption('devicekey', None)
    _Laserid = ConfigOption('laserid', None)
    _Buff=StringBuilder(64)
    _control_mode = 3
    _output_state = 3

    _idn=''
    #serial_interface = ConfigOption('interface', 'ASRL1::INSTR', missing='warn')
    _maxpower = ConfigOption('maxpower', 4.5)# missing='warn: please first run get_power_range to get available power range ')
    _maxcurrent = ConfigOption('maxcurrent', 0)#, missing='warn: please first run get_current_range to get available current range ')

    def Query(self, word):
        self._Buff.Clear()
        self._dev.Query(self._DeviceKey, word, self._Buff)
        return self._Buff.ToString()

    def on_activate(self):
        """ Activate Module.
        """
        self.connect_laser()

    def on_deactivate(self):
        """ Deactivate module
        """
        self.disconnect_laser()

    def connect_laser(self):
        """ Connect to Instrument.

            @return bool: connection success
        """
        try:
            dllpath = 'C:\\Program Files\\Newport\\Newport USB Driver\\Bin\\'
            Assembly.LoadFile(dllpath + 'UsbDllWrap.dll')
            clr.AddReference(r'UsbDllWrap')
            import Newport
            self._dev = Newport.USBComm.USB()
            self._dev.OpenDevices(self._Laserid, True)
            out = self._dev.Read(self._DeviceKey, self._Buff)
            timer=0
            while timer <= 100:
                while not out == -1:
                    out = self._dev.Read(self._DeviceKey, self._Buff)
                    print('Empyting the buffer: {}'.format(out))
                    time.sleep(0.5)
                self._idn = self.Query('*IDN?')
                if not self._idn == '':
                    self.log.info("\nLaser connected: {}".format(self._idn))
                    self._control_mode= self.Query('SOURce:CPOWer?')
                    self._output_state=self.Query('OUTPut:STATe?')
                    timer = 101
                    pass
                else:
                    self.log.info('reconnecting try:'+str(timer))
                    self._dev.CloseDevices()
                    time.sleep(0.2)
                    timer+=1
            if not self._idn == '':
                return True
            else:
                self.log.info('Time out')
                self.log.exception('time out')
                return False
        except:
            self._dev = None
            self.log.exception('Communication Failure:')
            return False

    def disconnect_laser(self):
        """ Close the connection to the instrument.
        """
        self._dev.CloseDevices()

    def allowed_control_modes(self):
        """ Control modes for this laser

            @return ControlMode: available control modes
        """
        return ['Constant Current','Constant Power']

    def get_control_mode(self):
        """ Get active control mode

        @return ControlMode: active control mode
        """
        if float(self.Query('SOURce:CPOWer?')) == 0:
            self._control_mode=0
            return ['Constant Current']
        elif float(self.Query('SOURce:CPOWer?')) == 1:
            self._control_mode=1
            return ['Constant Power']
        else:
            self.log.exception('Error while calling function:')

    def set_control_mode(self, mode):
        """ Set actve control mode

        @param ControlMode mode: desired control mode
        @return ControlMode: actual control mode
        """
        if mode == 'Constant Current':
            self.Query('SOURce:CPOWer 0')
            return self.get_control_mode()
        elif mode == 'Constant Power':
            self.Query('SOURce:CPOWer 1')
            return self.get_control_mode()
        else:
            self.log.exception('Mode not available: please use Constant Current or Constant Power')

    def get_power(self):
        """ Current laser power

        @return float: laser power in watts
        """
        return float(self.Query('SENSe:POWer:DIODe'))


    def get_power_setpoint(self):
        """ Current laser power setpoint

        @return float: power setpoint in watts
        """
        if self.get_control_mode() == 'Constant Power':
            return float(self.Query('SOURce:POWer:DIODe?'))
        else:
            self.log.exception('Not in Constant Power mode! Please use get_power instead')

    def get_power_range(self):
        """ Laser power range

        @return (float, float): laser power range
        """
        output=0
        if self._output_state== 1:
            print('Disabling output!')
            output=1
            self.output_disable()
        power= self.get_power()
        self.set_power('MAX')
        self._maxpower= self.get_power()
        self.set_power(power)
        if output == 1:
            print('power range detection finished, re-enabling output')
            self.output_enable()
        return [0, self._maxpower]

    def set_power(self, power):
        """ Set laser power setpoint

        @param float power: desired laser power

        @return float: actual laser power setpoint
        """
        if float(power) <= self._maxpower:
            self.Query('SOURce:POWer:DIODe {}'.format(power))
            return self.get_power()
        else:
            self.log.exception('Set value exceeding maxpower!')

    def get_current(self):
        """ Current laser power

        @return float: laser power in watts
        """
        return float(self.Query('SENSe:CURRent:DIODe'))

    def get_current_setpoint(self):
        """ Current laser power setpoint

        @return float: power setpoint in watts
        """
        if self.get_control_mode() == 'Constant Current':
            return float(self.Query('SOURce:CURRent:DIODe?'))
        else:
            self.log.exception('Not in Constant Current mode! Please use get_current instead')

    def get_current_range(self):
        """ Laser power range

        @return (float, float): laser power range
        """
        output = 0
        if self._output_state == 1:
            output = 1
            print('Disabling output!')
            self.output_disable()
        current = self.get_current()
        self.set_current('MAX')
        self._maxcurrent = self.get_current()
        self.set_current(current)
        if output == 1:
            print('current range detection finished, re-enabling output')
            self.output_enable()
        return [0, self._maxcurrent]

    def set_current(self, power):
        """ Set laser power setpoint

        @param float power: desired laser power

        @return float: actual laser power setpoint
        """
        if power <= self.maxcurrent:
            self.Query('SOURce:POWer:DIODe'.format(current))
            return self.get_current()
        else:
            self.log.exception('Set value exceeding maxcurrent!')

    def get_output_state(self):
        """ Get laser shutter state

        @return ShutterState: current laser shutter state
        """
        if self.Query('OUTPut:STATe?')=='0':
            #self._output_state = 0
            self.log.info('OFF')
            return True
        if self.Query('OUTPut:STATe?')=='1':
            #self._output_state = 1
            self.log.info('ON')
            return True

    def output_enable(self):
        """ Set laser shutter state.

        @param ShuterState state: desired laser shutter state
        @return ShutterState: actual laser shutter state
        """

        try:
            self.Query('OUTPut:STATe {}'.format('ON'))
            self._output_state = self.Query('OUTPut:STATe?')
            return True
        except:
            self.log.exception('error while enabling output')
            return False


    def output_disable(self):
        """ Set laser shutter state.

        @param ShuterState state: desired laser shutter state
        @return ShutterState: actual laser shutter state
        """

        try:
            self.Query('OUTPut:STATe {}'.format('OFF'))
            self._output_state = self.Query('OUTPut:STATe?')
            return self.get_output_state()
        except:
            self.log.exception('error while disabling output')
            return False

    def get_wavelength(self):
        """ Get SHG crystal temerpature.

            @return float: SHG crystal temperature in degrees Celsius
        """
        return float(self.Query('SENse:WAVElength'))

    def set_wavelength(self,wavelength):
        """ Get laser diode temperature.

            @return float: laser diode temperature in degrees Celsius
        """
        if wavelength <=638.9 and wavelength>=635:
            self.Query('SOURce:WAVE:START {}'.format(wavelength))
            self.Query('SOURce:WAVE:STOP {}'.format(wavelength + 0.1))
            self.Query('SOURce:WAVE:SLEW:FORW {}'.format(0.1))
            self.Query('SOURce:WAVE:SLEW:RET {}'.format(0.1))
            self.Query('SOURce:WAVE:DESSCANS 1')
            self.Query('OUTPut:SCAN:START')
            #self.Query('SOURce:WAVE {}'.format(wavelength))
            return float(self.Query('SENse:WAVElength'))
        else:
            self.log.exception('out of range: please enter a value between 635 and 638.9')
            return False

    def get_piezo_percentage(self):
        """ Get SHG tower temperature

            @return float: SHG tower temperature in degrees Celsius
        """
        if self.Query('SOURce:VOLTage:PIEZo?') == 'MAX':
            return 1
        else:
            return float(self.Query('SOURce:VOLTage:PIEZo?'))/100

    def set_piezo_percentage(self, percentage):
        """ Get cabinet temperature

            @return float: get laser cabinet temperature in degrees Celsius
        """
        if percentage<=100:
            self.Query('SOURce:VOLTage:PIEZo {}'.format(percentage))
        else:
            self.log.exception('Please input a value between 0,100')
        return self.get_piezo_percentage()

    def get_wavelength_tracking_state(self):
        """ Get all available temperatures

            @return dict: tict of temperature names and values
        """
        if self.Query('OUTPut:TRACk?') == 0:
            return 'OFF'
        elif  self.Query('OUTPut:TRACk?') == 1:
            return 'ON'



    def set_wavelength_tracking_state(self,status):
        """ Set temperatures for lasers wth tunable temperatures

        """
        self.Query('OUTPut:TRACk {}'.format(status))
        return self.get_wavelength_tracking_state()


